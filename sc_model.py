"""South Carolina 2027 forecast, built from South Carolina's own data instead of national shares.

What is South Carolina-specific:
  * SNAP: the observed fall in SC recipients from July 2025 (564,900) to July 2026 (481,856), SC DSS county reports,
    with the share caused by the 2025 law as a range, plus further 2027 losses at SC's share of national SNAP.
  * Marketplace: national 2027 losses (verification rules, immigrant tax-credit ban) at SC's share of 2026
    Marketplace enrollment (about 390,000 of 19.2 million), not its population share. The 2026 drop of about
    160,000 after enhanced tax credits expired happened before 2027 and is reported as context, not counted.
  * Medicaid: SC did not expand Medicaid, so the 2027 work requirement and six-month renewals do not apply.
    Only the immigrant eligibility rule reaches SC Medicaid (at SC's share of national Medicaid enrollment).
  * State budget: SNAP administrative cost share rises from 50% to 75% (Oct 2026), and from Oct 2027 SC pays a
    share of SNAP benefits set by its error rate (FY2025: 8.8%, the 10% tier).
  * Counties: SNAP losses go to counties in proportion to each county's own observed drop; groups without county
    data (Marketplace, immigrants, jobs, hospital care) go by county population.

Same structure and ranges as model/coupled_model.py where SC has no data of its own. 20,000 scenarios, fixed seed.
95% intervals = 2.5th to 97.5th percentile. Dollars are 2027 dollars.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
H = ROOT / 'data' / 'inputs'
OUT = ROOT / 'data' / 'sc'
N = 20000
rng = np.random.default_rng(20261103)
U, T = rng.uniform, rng.triangular

county = pd.read_csv(OUT / 'sc_snap_county.csv')
med = pd.read_csv(H / 'medicaid_chip_enrollment_jul2026.csv')
mcr = pd.read_csv(H / 'medicare_enrollment_2024.csv')
SC_MED_SHARE = float(med.loc[med.abbr == 'SC', 'medicaid_chip_enrollees'].iloc[0] / med.medicaid_chip_enrollees.sum())
SC_MCR_SHARE = float(mcr.loc[mcr.abbr == 'SC', 'medicare_enrollees'].iloc[0] / mcr.medicare_enrollees.sum())
SNAP_JUL25, SNAP_JUL26 = county.persons_jul2025.sum(), county.persons_jul2026.sum()   # 564,900 -> 481,856
SNAP_DROP = SNAP_JUL25 - SNAP_JUL26
SC_SNAP_SHARE = SNAP_JUL26 / 36_087_667                                               # USDA national, July 2026
BEN_MONTH = county.benefits_jul2026.sum()                                             # $89.3M issued, July 2026
POP = county.population_2025.sum()

P = dict(
    snap_policy_share=U(0.45, 0.85, N),        # share of SC's observed drop caused by the 2025 law (as national model)
    snap_add27_nat=U(0.1e6, 0.6e6, N),         # further national 2027 SNAP losses
    snap_benefit=np.full(N, BEN_MONTH / SNAP_JUL26),  # SC average benefit per person per month (~$185)
    mkt_loss12_nat=T(0.6e6, 1.4e6, 2.6e6, N),  # national 2027 Marketplace losses
    sc_mkt_share=U(0.019, 0.022, N),           # SC share of 2026 Marketplace enrollment (~390k of 19.2M)
    mkt_front=U(0.70, 0.90, N),
    imm_mcd_nat=U(70e3, 130e3, N), imm_mcr_nat=U(70e3, 130e3, N),
    mcd_cost_imm=U(4000, 6500, N),             # federal Medicaid spending per adult immigrant enrollee in SC (~70% FMAP)
    ptc_per_person=U(4000, 6500, N),
    mult_snap=U(1.20, 1.60, N), mult_mcd=U(1.10, 1.25, N), mult_ptc=U(1.00, 1.20, N), tax_share=U(0.065, 0.095, N),
    jobs_per_bn=U(7000, 11500, N), ov_jobs=U(0.05, 0.15, N),
    u12=np.clip(T(4.0, 4.1, 4.5, N) + rng.normal(0, 0.3, N), 3.6, 6.5),  # national Q4 2027 (Fed Sept 2026, widened)
    unins_share=U(0.70, 0.95, N),
    ed_ins=U(0.85, 1.10, N), ed_unins_ratio=U(0.55, 0.90, N), ip_ins=U(0.07, 0.11, N), ip_unins_ratio=U(0.50, 0.80, N),
    ed_cost=U(700, 950, N), ip_cost=U(12000, 16000, N), unpaid_share=U(0.75, 0.90, N), oop_per_uninsured=U(500, 1300, N),
    or_part=U(1.00, 1.075, N), or_per10=T(1.000, 1.010, 1.015, N), price_ratio=U(1.38, 1.46, N), snap_ip_base=U(0.06, 0.12, N),
    # Medicare 2027 cost changes, national totals (as forecast_model.py) scaled by SC's Medicare share
    partb_payers=U(54e6, 58e6, N), partb_rise=U(5.5, 8.0, N), partd_ded_payers=U(10e6, 18e6, N),
    partd_cap_hitters=U(1.3e6, 2.4e6, N), pdp_prem_rise=U(3, 10, N), pdp_payers=U(17e6, 21e6, N),
    # state budget: SNAP admin share 50% -> 75% (~$23M/yr, SC DSS); benefit share from Oct 2027 by error-rate tier
    admin_extra=U(20e6, 26e6, N),
    benefit_tier=rng.choice([0.05, 0.10, 0.10, 0.10, 0.15], N),  # FY2025 rate 8.8% = 10% tier; FY2026 rate could move it
)
P['partb_rise'] = np.full(N, 6.50)  # CMS final 2027 Part B premium $209.40 (+$6.50), Nov 17, 2026
LF_SHARE = POP / 342_000_000  # SC share of national labor force, approximated by population share

k_ = {6: 6, 12: 12}
res = {}
for k in (6, 12):
    f = k / 12
    snap_off = SNAP_DROP * P['snap_policy_share'] + P['snap_add27_nat'] * SC_SNAP_SHARE * f
    mkt = P['mkt_loss12_nat'] * P['sc_mkt_share'] * (P['mkt_front'] + (1 - P['mkt_front']) * f)
    imm_mcd = P['imm_mcd_nat'] * SC_MED_SHARE
    imm_mcr = P['imm_mcr_nat'] * SC_MCR_SHARE
    imm = imm_mcd + imm_mcr
    # dollars over the period (SNAP in place all period; Marketplace mostly from Jan 1; average of start and end)
    mkt_avg = P['mkt_loss12_nat'] * P['sc_mkt_share'] * (P['mkt_front'] + (1 - P['mkt_front']) * f / 2)
    fed_snap = snap_off * P['snap_benefit'] * k
    fed_ptc = mkt_avg * P['ptc_per_person'] * f
    fed_mcd = imm_mcd * P['mcd_cost_imm'] * f
    fed = fed_snap + fed_ptc + fed_mcd
    gdp = fed_snap * P['mult_snap'] + fed_ptc * P['mult_ptc'] + fed_mcd * P['mult_mcd']
    jobs_cut = (fed / f) / 1e9 * P['jobs_per_bn']
    u_k = 4.2 + (P['u12'] - 4.2) * f
    jobs_econ = np.maximum((u_k - 4.2) / 100 * (7.1e6 / 0.042) * LF_SHARE, 0)
    job_losers = np.maximum(jobs_cut, jobs_econ)
    people = snap_off + mkt + imm + job_losers * (1 - P['ov_jobs'])
    # hospital and ER care for the newly uninsured (Marketplace and immigrant coverage losers)
    unins = (mkt_avg + imm) * P['unins_share']
    er = unins * P['ed_ins'] * P['ed_unins_ratio'] * f
    ip = unins * P['ip_ins'] * P['ip_unins_ratio'] * f
    hosp = er * P['ed_cost'] + ip * P['ip_cost']
    uncomp = hosp * P['unpaid_share']
    # extra hospital stays linked to losing SNAP (logistic odds ratio, as the coupled model)
    lnor = np.log(P['or_part']) + np.log(P['or_per10']) * P['snap_benefit'] / P['price_ratio'] / 10
    pm = 1 - (1 - P['snap_ip_base']) ** (1 / 12)
    extra_stays = snap_off * (1 / (1 + np.exp(-(np.log(pm / (1 - pm)) + lnor))) - pm) * k
    medicare = SC_MCR_SHARE * (f * (P['partb_payers'] * P['partb_rise'] * 12 + P['pdp_payers'] * P['pdp_prem_rise'] * 12)
                               + min(1.0, f * 1.6) * P['partd_ded_payers'] * 85 + max(0.0, f * 2 - 1) * P['partd_cap_hitters'] * 300)
    household = fed_snap + unins * P['oop_per_uninsured'] * f + medicare
    # state budget in the period: admin share all of 2027; benefit share Oct-Dec 2027 only (12-month horizon)
    benefits_after = (SNAP_JUL26 - P['snap_add27_nat'] * SC_SNAP_SHARE) * P['snap_benefit'] * 12
    state_admin = P['admin_extra'] * f
    state_benefit = benefits_after * P['benefit_tier'] * (3 / 12 if k == 12 else 0)
    res[k] = dict(people=people, snap_off=snap_off, mkt=mkt, imm=imm, job_losers=job_losers, jobs_cut=jobs_cut,
                  fed_cut=fed, gdp_loss=gdp, tax_loss=gdp * P['tax_share'], newly_uninsured=unins, er_visits=er,
                  ip_stays=ip, hosp_er_cost=hosp, uncomp_care=uncomp, snap_extra_stays=extra_stays,
                  snap_extra_cost=extra_stays * P['ip_cost'], household_cost=household, medicare_cost=medicare,
                  lost_snap=fed_snap, state_admin=state_admin, state_benefit=state_benefit,
                  state_total=state_admin + state_benefit, state_benefit_fy28=benefits_after * P['benefit_tier'])

q = lambda x: (float(np.percentile(x, 2.5)), float(np.median(x)), float(np.percentile(x, 97.5)))
labels = dict(
    people='South Carolinians affected, counted once', snap_off='Off SNAP because of the law',
    mkt='Lost Marketplace coverage or subsidy (2027 rules)', imm='Immigrants losing Medicaid or Medicare',
    job_losers='Job losers counted', jobs_cut='Jobs lost from the cuts', fed_cut='Federal money no longer reaching SC ($)',
    gdp_loss='Lost economic output in SC ($)', tax_loss='State and local tax revenue lost ($)',
    newly_uninsured='Newly uninsured South Carolinians', er_visits='ER visits by the newly uninsured',
    ip_stays='Hospital stays by the newly uninsured', hosp_er_cost='Hospital and ER care for the newly uninsured ($)',
    uncomp_care='Unpaid: uncompensated hospital care ($)', snap_extra_stays='Extra hospital stays linked to losing SNAP',
    snap_extra_cost='Cost of extra hospital stays linked to losing SNAP ($)', household_cost='Added household costs ($)',
    lost_snap='Lost SNAP benefits ($)', medicare_cost='Added Medicare premiums and drug costs ($)',
    state_admin='New state cost: SNAP administration ($)', state_benefit='New state cost: share of SNAP benefits ($)',
    state_total='New state SNAP costs, total ($)', state_benefit_fy28='State share of SNAP benefits, full year from Oct 2027 ($)')
rows = []
for key, lab in labels.items():
    for k in (6, 12):
        if key == 'state_benefit_fy28' and k == 6:
            continue
        lo, mid, hi = q(res[k][key])
        rows.append(dict(metric_id=key, metric=lab, horizon=f'{k} months', months=k, low=lo, median=mid, high=hi,
                         unit='dollars' if '($)' in lab else 'people'))
nat = pd.DataFrame(rows)
nat.to_csv(OUT / 'sc_forecast.csv', index=False)

# context figures (observed, not modeled)
ctx = pd.DataFrame([
    dict(metric_id='snap_jul2025', metric='SNAP recipients, July 2025', value=int(SNAP_JUL25), source='SC DSS'),
    dict(metric_id='snap_jul2026', metric='SNAP recipients, July 2026', value=int(SNAP_JUL26), source='SC DSS'),
    dict(metric_id='snap_drop', metric='Fall in SNAP recipients, July 2025 to July 2026', value=int(SNAP_DROP), source='SC DSS'),
    dict(metric_id='snap_drop_pct', metric='Fall in SNAP recipients (%)', value=round(SNAP_DROP / SNAP_JUL25 * 100, 1), source='SC DSS'),
    dict(metric_id='us_drop_pct', metric='Fall in SNAP recipients nationally (%)', value=13.3, source='USDA via FRAC'),
    dict(metric_id='snap_benefits_month', metric='SNAP benefits issued, July 2026 ($)', value=int(BEN_MONTH), source='SC DSS'),
    dict(metric_id='mkt_drop_2026', metric='Marketplace enrollees lost in early 2026 (tax credits expired)', value=160000, source='KFF; Here Columbia'),
    dict(metric_id='mkt_drop_2026_pct', metric='Marketplace effectuated enrollment change, 2025 to 2026 (%)', value=-29, source='KFF'),
    dict(metric_id='mkt_rate_2027', metric='Average 2027 Marketplace rate increase (%)', value=22.1, source='SC Department of Insurance via Here Columbia'),
    dict(metric_id='error_rate_fy25', metric='SNAP payment error rate, FY2025 (%)', value=8.8, source='USDA FY2025 rates'),
    dict(metric_id='coverage_gap', metric='Adults in the coverage gap (2024 estimate)', value=83000, source='CBPP via SC Daily Gazette'),
    dict(metric_id='palmetto_cap', metric='Parents Palmetto Pathways would cover (cap, pending)', value=11400, source='SC DHHS via SC Daily Gazette'),
])
ctx.to_csv(OUT / 'sc_context.csv', index=False)

# counties
drop = (county.persons_jul2025 - county.persons_jul2026).clip(lower=0)
w_drop = (drop / drop.sum()).to_numpy()
w_pop = (county.population_2025 / POP).to_numpy()
r12 = res[12]
snap_c = np.outer(w_drop, r12['snap_off'])
other_c = np.outer(w_pop, r12['mkt'] + r12['imm'] + r12['job_losers'] * (1 - P['ov_jobs']))
ppl_c = snap_c + other_c
hosp_c = np.outer(w_pop, r12['hosp_er_cost'])
cty = county[['county', 'fips', 'population_2025', 'persons_jul2025', 'persons_jul2026']].copy()
cty['snap_change'] = cty.persons_jul2026 - cty.persons_jul2025
cty['snap_change_pct'] = (cty.snap_change / cty.persons_jul2025 * 100).round(1)
cty['snap_per_1000'] = (cty.persons_jul2026 / cty.population_2025 * 1000).round(1)
for name, arr, rnd in (('snap_off_12m', snap_c, -1), ('people_12m', ppl_c, -1)):
    lo, mid, hi = np.percentile(arr, [2.5, 50, 97.5], axis=1)
    cty[name] = mid.round(rnd); cty[name + '_low'] = lo.round(rnd); cty[name + '_high'] = hi.round(rnd)
cty['people_per_1000'] = (cty.people_12m / cty.population_2025 * 1000).round(1)
cty['hosp_er_12m'] = (np.median(hosp_c, axis=1) / 1e6).round(2)
cty.to_csv(OUT / 'sc_counties.csv', index=False)

pd.set_option('display.width', 220)
show = nat.copy()
for c in ('low', 'median', 'high'):
    show[c] = np.where(show.unit == 'dollars', (show[c] / 1e6).round(1), show[c].round(-1))
print(show[['metric_id', 'horizon', 'low', 'median', 'high']].to_string())
print(cty.sort_values('snap_change_pct')[['county', 'snap_change', 'snap_change_pct', 'snap_per_1000', 'people_12m', 'people_per_1000']].head(6).to_string())
print(cty.sort_values('people_per_1000', ascending=False)[['county', 'people_12m', 'people_per_1000', 'snap_per_1000']].head(6).to_string())
print('shares', SC_MED_SHARE, SC_MCR_SHARE, SC_SNAP_SHARE, 'pop', POP)
