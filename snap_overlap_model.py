"""SNAP loss x Medicare/Medicaid 2027 impact overlap, by state, with a 95% interval (2.5th-97.5th percentile).

Inputs (all in data/inputs/):
  cbpp_snap_risk_raw.txt   CBPP (Apr 30, 2025) state counts, FY2022 SNAP QC: adults 55-64 no kids/no disability,
                           adults 18-64 with school-age (7+) children no disability, and people in those households.
  snap_fy2025_raw.txt      USDA FNS avg monthly SNAP participants FY2025 (via KFF) - used to scale CBPP FY2022 counts.
  dual_eligible_2026.csv   total duals by state (KFF/CMS, early 2026).
  state_data.csv           population, abbreviations.
Uncertain parameters are drawn jointly (national) N times; each state's counts are deterministic given a draw.
"""
import numpy as np, pandas as pd

rng = np.random.default_rng(20261101)
N = 20000
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
H = str(ROOT / 'data' / 'inputs') + '/'   # model inputs
OUT = str(ROOT / 'data') + '/'             # files the dashboard reads

cb = pd.read_csv(H + 'cbpp_snap_risk_raw.txt', sep='|', names=['state', 'old_adults', 'parents7', 'old_hh', 'parents7_hh'])
snap = pd.read_csv(H + 'snap_fy2025_raw.txt', sep='|', names=['state', 'snap_fy2025'])
base = pd.read_csv(H + 'state_data.csv')[['state', 'abbr', 'population_2025']]
duals = pd.read_csv(H + 'dual_eligible_2026.csv')[['abbr', 'total_duals']]
d = base.merge(cb, on='state').merge(snap, on='state').merge(duals, on='abbr')
assert len(d) == 51

nonexp = {'Alabama', 'Florida', 'Georgia', 'Kansas', 'Mississippi', 'South Carolina', 'Tennessee', 'Texas', 'Wisconsin', 'Wyoming'}
d['expansion'] = ~d.state.isin(nonexp)

# Scale CBPP FY2022 counts by each state's share of FY2025 SNAP relative to the national FY2022->FY2025 change.
# CBPP's national total participants in its FY2022 base is not given by state, so scale uniformly by the national ratio
# FY2025 42.13M / FY2022 41.21M (USDA national averages) = 1.022.
SCALE = 1.0  # no rescale: CBPP's FY2022 counts are used as-is (noted on the page)

# ---- uncertain parameters (one draw = one national scenario) ----
# f: share of CBPP's "parents with children 7+" whose youngest child is 14+ (enacted law exempts parents of children under 14).
#    Calibrated so newly-subject adults ~ 2.6M (AEI estimate): 1.4M older adults + 3.1M*f => f ~ 0.39.
f = rng.uniform(0.30, 0.48, N)
# p: share of newly subject adults who lose SNAP. Arkansas 2018 Medicaid work rule: ~18% of those subject lost coverage
#    within months; CBO's 2.4M average-month SNAP reduction vs ~2.6M newly subject implies a much higher ceiling
#    (CBO also counts adults 18-54 losing area waivers). Triangular 0.18 / 0.30 / 0.50.
p = rng.triangular(0.18, 0.30, 0.50, N)
# c: share of a teen parent's household (other members, mostly the teens) that leaves SNAP with them, vs. staying on with
#    a reduced benefit. Uniform 0.15-0.40.
c = rng.uniform(0.15, 0.40, N)
# Medicaid overlap - expansion states.
#   older adults 55-64 on SNAP who are Medicaid expansion adults (and so also face Medicaid work rules + 6-month renewals)
m_old_exp = rng.uniform(0.65, 0.85, N)
#   parents of teens on SNAP who are in the expansion group (not the lower-income parent/caretaker group)
m_par_exp = rng.uniform(0.35, 0.65, N)
# Non-expansion states: Medicaid work rules do not apply; Georgia Pathways / Wisconsin waiver adults are a small exception.
m_old_non = rng.uniform(0.00, 0.10, N)
m_par_non = rng.uniform(0.00, 0.10, N)
# Duals: share receiving SNAP (Maryland linked data, 47% in 2012) and chance of losing SNAP (they are exempt from work
#    rules; losses come from churn, cost-shift-driven state cuts, immigrant rules) - the low-probability tier.
s_dual = rng.uniform(0.40, 0.55, N)
q_dual = rng.uniform(0.01, 0.05, N)

rows = []
for r in d.itertuples():
    old = r.old_adults * SCALE
    par = r.parents7 * SCALE
    kids_hh = max(r.parents7_hh - r.parents7, 0) * SCALE  # other people in those households (mostly children)
    if r.expansion:
        mo, mp = m_old_exp, m_par_exp
    else:
        mo, mp = m_old_non, m_par_non
    a_old = old * p * mo                 # older adults losing SNAP AND facing Medicaid work rules
    a_par = par * f * p * mp             # parents of teens losing SNAP AND facing Medicaid work rules
    a_kid = kids_hh * f * p * c * mp     # children whose household leaves SNAP and whose parent faces Medicaid rules
    a_dual = r.total_duals * s_dual * q_dual  # duals losing SNAP; all face 2027 Medicare cost changes
    tot = a_old + a_par + a_kid + a_dual
    q = lambda x: (np.percentile(x, 2.5), np.median(x), np.percentile(x, 97.5))
    lo, mid, hi = q(tot)
    rows.append(dict(state=r.state, abbr=r.abbr, population=r.population_2025, expansion=r.expansion,
                     snap_fy2025=round(r.snap_fy2025),
                     older_adults=round(np.median(a_old), -1), parents=round(np.median(a_par), -1),
                     children=round(np.median(a_kid), -1), duals=round(np.median(a_dual), -1),
                     total_mid=round(mid, -1), total_low=round(lo, -1), total_high=round(hi, -1),
                     share_mid=mid / r.population_2025, share_low=lo / r.population_2025, share_high=hi / r.population_2025))
    rows[-1]['_draws'] = tot

out = pd.DataFrame(rows)
nat = sum(r['_draws'] for r in rows)
print('national 2.5/50/97.5:', [round(x) for x in np.percentile(nat, [2.5, 50, 97.5])])
print('sum of state medians:', out.total_mid.sum())
print('group medians national: old', out.older_adults.sum(), 'par', out.parents.sum(), 'kids', out.children.sum(), 'duals', out.duals.sum())
out = out.drop(columns=['_draws'])
out['share_mid_pct'] = (out.share_mid * 100).round(2)
out['share_low_pct'] = (out.share_low * 100).round(2)
out['share_high_pct'] = (out.share_high * 100).round(2)
out[['state', 'abbr', 'population', 'snap_fy2025', 'older_adults', 'parents', 'children', 'duals',
     'total_low', 'total_mid', 'total_high', 'share_low_pct', 'share_mid_pct', 'share_high_pct']].to_csv(H + 'snap_overlap_2027.csv', index=False)
print(out.sort_values('share_mid', ascending=False)[['state', 'total_low', 'total_mid', 'total_high', 'share_mid_pct']].head(8).to_string())
print(out.sort_values('share_mid')[['state', 'total_mid', 'share_mid_pct']].head(5).to_string())
