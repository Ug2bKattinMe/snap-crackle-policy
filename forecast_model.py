"""Combined 2027 impact forecast: people losing Medicaid, SNAP, Medicare (immigrant rule), Marketplace help, or jobs,
de-duplicated, plus financial and economic effects at 6 months (end of June 2027) and 12 months (end of Dec 2027).

Monte Carlo over uncertain national parameters (N draws). States get each draw's national components allocated by
state shares, so state intervals move together. Intervals are 95% (2.5th-97.5th percentile).
All dollar figures are 2027 dollars, not discounted.
"""
import json
import numpy as np
import pandas as pd

from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
H = str(ROOT / 'data' / 'inputs') + '/'   # model inputs
OUT = str(ROOT / 'data') + '/'             # files the dashboard reads
N = 20000
rng = np.random.default_rng(20261101)
MONTHS = np.arange(0, 13)  # 0 = Jan 1, 2027 (start), 6 = end of June, 12 = end of December

# ---------------- state inputs ----------------
imp = pd.read_csv(H + 'impact_2027.csv')
snap = pd.read_csv(H + 'snap_fy2025_raw.txt', sep='|', names=['state', 'snap_fy2025'])
ov = pd.read_csv(H + 'snap_overlap_2027.csv')[['state', 'total_mid']].rename(columns={'total_mid': 'snap_med_overlap'})
med = pd.read_csv(H + 'medicaid_chip_enrollment_jun2026.csv')[['abbr', 'medicaid_chip_enrollees']]
mcr = pd.read_csv(H + 'medicare_enrollment_2024.csv')[['abbr', 'medicare_enrollees']]
d = (imp[['state', 'abbr', 'population_2025', 'exp_scaled', 'total_duals', 'pdp', 'partd_total', 'ma']]
     .merge(snap, on='state').merge(ov, on='state').merge(med, on='abbr').merge(mcr, on='abbr'))
assert len(d) == 51
d['exp_scaled'] = d.exp_scaled.fillna(0)
w = lambda col: (d[col] / d[col].sum()).to_numpy()
W = dict(exp=w('exp_scaled'), snap=w('snap_fy2025'), pop=w('population_2025'), med=w('medicaid_chip_enrollees'),
         pdp=w('pdp'), partd=w('partd_total'), mcr=w('medicare_enrollees'), ovl=w('snap_med_overlap'))
EXP_TOTAL = d.exp_scaled.sum()          # 20.4M expansion adults (scaled to CMS June 2025)
MEDICARE_TOTAL = d.medicare_enrollees.sum()
PDP_TOTAL = d.pdp.sum()

# ---------------- uncertain parameters (one row per draw) ----------------
U, T = rng.uniform, rng.triangular
P = dict(
    # Medicaid: share of all expansion adults off Medicaid by month 12 from work rules (Arkansas 2018 ~18% of those
    # subject within 7 months; CBO long run ~26% of expansion adults), share of that reached by month 6 (most states
    # start at each person's next renewal), and extra procedural losses from six-month renewals by month 12.
    mcd_loss12=T(0.06, 0.12, 0.20, N), mcd_ramp6=U(0.35, 0.60, N), renew_loss12=U(0.01, 0.04, N),
    # Immigrant rules (CBO): Medicaid/CHIP since Oct 2026 and Medicare from Jan 4, 2027, ~100k uninsured each.
    imm_mcd=U(70e3, 130e3, N), imm_mcr=U(70e3, 130e3, N),
    # SNAP: people off SNAP because of the law at any point in 2027 (CBO 2.4M average month; observed caseload fall
    # 4.3-4.5M since Jan 2025, only partly due to the law).
    snap_off=T(2.4e6, 3.0e6, 4.0e6, N),
    # Marketplace 2027 rule: fewer enrollees from verification (HHS up to 2M) and immigrant tax-credit ban (CBO ~0.9M
    # uninsured). Combined people losing Marketplace coverage by month 12; 70-90% of it from Jan 1 (plan-year start).
    mkt_loss12=T(0.6e6, 1.4e6, 2.6e6, N), mkt_front=U(0.70, 0.90, N),
    # Overlaps for de-duplication.
    ov_mcd_snap=U(0.25, 0.45, N),   # share of Medicaid work-rule losers also off SNAP (same people, same rules)
    ov_jobs=U(0.05, 0.15, N),       # share of job losers already counted in another group
    # Jobs. Fed Sept 2026 SEP: Q4 2027 unemployment median 4.1%, range 4.0-4.5%; Sept 2026 actual 4.2%, 7.1M unemployed.
    u12=T(4.0, 4.1, 4.5, N), jobs_per_bn=U(7000, 11500, N),  # CWF/GWU IMPLAN: 1.22M jobs per $131B (~9,300 per $1B)
    # Dollars.
    mcd_fed_per_adult=U(5600, 7700, N),  # federal Medicaid spending per expansion adult per year (90% of ~$6.5-8.5k)
    snap_benefit=U(185, 195, N),          # average SNAP benefit per person per month, FY2025-26
    ptc_per_person=U(4000, 6500, N),      # average annual premium tax credit per Marketplace enrollee lost
    mult_mcd=U(1.10, 1.25, N), mult_snap=U(1.20, 1.60, N), mult_ptc=U(1.00, 1.20, N),  # GDP per $ of lost spending
    tax_share=U(0.065, 0.095, N),         # state+local tax revenue as share of GDP loss (CWF: $12.2B / $154.3B = 7.9%)
    # Hospital and ER care for the newly uninsured (people who lose Medicaid, Medicare or Marketplace coverage).
    unins_share=U(0.70, 0.95, N),         # share of coverage losers who stay uninsured (Arkansas: no rise in other coverage)
    ed_rate=U(0.40, 0.70, N),             # ER visits per uninsured person per year (Medicaid adults ~0.99 in T-MSIS 2022; uninsured use less)
    ed_cost=U(700, 950, N),               # hospital cost per treat-and-release ER visit, 2027$ (HCUP 2021 self-pay $610, inflated)
    ip_rate=U(0.035, 0.060, N),           # inpatient stays per uninsured person per year (HCUP 2012: ~2.0M stays / ~47M uninsured)
    ip_cost=U(12000, 16000, N),           # hospital cost per inpatient stay, 2027$ (HCUP 2012 uninsured $8,800, inflated)
    unpaid_share=U(0.75, 0.90, N),        # share of that hospital cost never paid (becomes uncompensated care)
    oop_per_uninsured=U(500, 1300, N),      # new out-of-pocket medical spending per newly uninsured person per year
    # Medicare cost increases for 2027 (people keep coverage but pay more).
    partb_payers=U(54e6, 58e6, N), partb_rise=U(5.5, 8.0, N),          # $/month; Trustees: $202.90 -> $209.50
    partd_ded_payers=U(10e6, 18e6, N),                                  # pay the higher $700 standard deductible (+$85)
    partd_cap_hitters=U(1.3e6, 2.4e6, N),                               # reach the cap: +$300
    pdp_prem_rise=U(3, 10, N), pdp_payers=U(17e6, 21e6, N),            # stand-alone plan premiums after demo ends
)
LF = 7.1e6 / 0.042  # labor force implied by Sept 2026 report (~169M)


def path(m, total12, ramp6):
    """Cumulative share reached by month m: piecewise-linear 0 -> ramp6 at month 6 -> 1 at month 12."""
    m = np.asarray(m, dtype=float)[:, None]
    return np.where(m <= 6, ramp6 * m / 6, ramp6 + (1 - ramp6) * (m - 6) / 6) * total12


# ---------------- people over time (stock at end of each month) ----------------
mcd_work = path(MONTHS, EXP_TOTAL * P['mcd_loss12'], P['mcd_ramp6'])            # (13, N)
mcd_renew = path(MONTHS, EXP_TOTAL * P['renew_loss12'], np.full(N, 0.4))
mcd_loss = mcd_work + mcd_renew
imm = np.vstack([P['imm_mcd'] + P['imm_mcr'] * (MONTHS[i] >= 0) for i in range(len(MONTHS))])
snap_off = np.tile(P['snap_off'], (len(MONTHS), 1))
# front-loaded at the Jan 1 plan-year start, the rest spread evenly over the year
mkt = P['mkt_loss12'] * (P['mkt_front'] + (1 - P['mkt_front']) * MONTHS[:, None] / 12)
cut_dollars_rate = None  # filled below

# Annualized federal spending reduction rate at month m ($): Medicaid losers x per-adult cost + SNAP off x benefit x12
# + Marketplace losers x PTC.
rate_mcd = mcd_loss * P['mcd_fed_per_adult']
rate_snap = snap_off * P['snap_benefit'] * 12
rate_ptc = mkt * P['ptc_per_person']
rate_total = rate_mcd + rate_snap + rate_ptc
cut_jobs = rate_total / 1e9 * P['jobs_per_bn']
# Economy-wide: change in unemployed vs Sept 2026, linear to Q4 2027.
u_m = 4.2 + (P['u12'] - 4.2) * (MONTHS[:, None] / 12)
econ_rise = (u_m - 4.2) / 100 * LF
job_losers = np.maximum(cut_jobs, econ_rise)  # Fed outlook already includes policy effects -> take the larger, not sum

combined = (mcd_loss + imm + snap_off + mkt + job_losers
            - P['ov_mcd_snap'] * mcd_work - P['ov_jobs'] * job_losers)

# ---------------- dollars over a window (cumulative months 0..k) ----------------
def window(rate, k):
    # integrate annualized rate over months 0..k (trapezoid on monthly grid) -> dollars
    r = rate[:k + 1]
    return (r[:-1] + r[1:]).sum(axis=0) / 2 / 12


def money(k):
    fed_mcd, fed_snap, fed_ptc = window(rate_mcd, k), window(rate_snap, k), window(rate_ptc, k)
    fed = fed_mcd + fed_snap + fed_ptc
    gdp = fed_mcd * P['mult_mcd'] + fed_snap * P['mult_snap'] + fed_ptc * P['mult_ptc']
    tax = gdp * P['tax_share']
    newly_uninsured = mcd_loss + imm + mkt
    uninsured = newly_uninsured * P['unins_share']
    er_cost = window(uninsured * P['ed_rate'] * P['ed_cost'], k)
    ip_cost = window(uninsured * P['ip_rate'] * P['ip_cost'], k)
    hosp = er_cost + ip_cost
    uncomp = hosp * P['unpaid_share']
    oop = window(uninsured * P['oop_per_uninsured'], k)
    frac = k / 12
    medicare = frac * (P['partb_payers'] * P['partb_rise'] * 12 + P['pdp_payers'] * P['pdp_prem_rise'] * 12) \
        + min(1.0, frac * 1.6) * P['partd_ded_payers'] * 85 + max(0.0, frac * 2 - 1) * P['partd_cap_hitters'] * 300
    household = fed_snap + oop + medicare  # lost SNAP benefits + new medical bills + Medicare cost increases
    return dict(fed_cut=fed, fed_mcd=fed_mcd, fed_snap=fed_snap, fed_ptc=fed_ptc, gdp_loss=gdp, tax_loss=tax,
                uncomp_care=uncomp, hosp_er_cost=hosp, er_cost=er_cost, ip_cost=ip_cost,
                er_visits=window(uninsured * P['ed_rate'], k) * 12 / 12, ip_stays=window(uninsured * P['ip_rate'], k),
                newly_uninsured=uninsured[k], household_cost=household, medicare_cost=medicare, lost_snap=fed_snap,
                new_oop=oop, jobs_cut=cut_jobs[k], jobs_econ=econ_rise[k], job_losers=job_losers[k],
                people=combined[k], mcd_loss=mcd_loss[k], snap_off=snap_off[k], mkt=mkt[k], imm=imm[k])


q = lambda x: (float(np.percentile(x, 2.5)), float(np.median(x)), float(np.percentile(x, 97.5)))
res = {k: money(k) for k in (6, 12)}

# ---------------- national outputs ----------------
nat_rows = []
labels = dict(people='Combined people affected (de-duplicated)', mcd_loss='Off Medicaid (work rules + 6-month renewals)',
              snap_off='Off SNAP because of the law', mkt='Lost Marketplace coverage or subsidy', imm='Immigrants losing Medicaid or Medicare',
              job_losers='Job losers counted', jobs_cut='Jobs lost from the cuts', jobs_econ='Change in unemployed, economy-wide (Fed outlook)',
              fed_cut='Federal spending reduction ($)', gdp_loss='GDP loss ($)', tax_loss='State and local tax revenue loss ($)',
              newly_uninsured='Newly uninsured people', er_visits='ER visits by the newly uninsured', ip_stays='Hospital stays by the newly uninsured',
              hosp_er_cost='Cost of hospital and ER care for the newly uninsured ($)', er_cost='Emergency room visits ($)', ip_cost='Hospital inpatient stays ($)',
              uncomp_care='Unpaid by patients: uncompensated hospital care ($)', household_cost='Added household costs ($)',
              lost_snap='Lost SNAP benefits ($)', new_oop='New out-of-pocket medical costs, newly uninsured ($)',
              medicare_cost='Added Medicare premiums and drug costs ($)')
for key, lab in labels.items():
    for k in (6, 12):
        lo, mid, hi = q(res[k][key])
        nat_rows.append(dict(metric_id=key, metric=lab, horizon=f'{k} months', months=k, low=lo, median=mid, high=hi,
                             unit='dollars' if '($)' in lab else 'people'))
nat = pd.DataFrame(nat_rows)
nat.to_csv(OUT + 'forecast_national.csv', index=False)

# monthly timeline for the combined count and components (medians + 95% band for combined)
tl = []
for i, m in enumerate(MONTHS):
    lo, mid, hi = q(combined[i])
    tl.append(dict(month=int(m), label=pd.Timestamp('2027-01-01') + pd.DateOffset(months=int(m)) - pd.DateOffset(days=1) if m else pd.Timestamp('2027-01-01'),
                   combined_low=lo, combined_median=mid, combined_high=hi,
                   medicaid=float(np.median(mcd_loss[i] - P['ov_mcd_snap'] * mcd_work[i])), snap=float(np.median(snap_off[i])),
                   marketplace=float(np.median(mkt[i])), immigrants=float(np.median(imm[i])),
                   jobs=float(np.median(job_losers[i] * (1 - P['ov_jobs'])))))
tl = pd.DataFrame(tl)
tl['date'] = tl.label.dt.strftime('%Y-%m-%d')
tl.drop(columns=['label']).to_csv(OUT + 'forecast_timeline.csv', index=False)

# ---------------- state outputs ----------------
def alloc(k):
    r = res[k]
    st = {}
    # people components allocated by shares; overlap removal allocated with the components it reduces
    mw = mcd_work[k]
    st['mcd'] = np.outer(W['exp'], r['mcd_loss'] - P['ov_mcd_snap'] * mw)
    st['snap'] = np.outer(W['snap'], r['snap_off'])
    st['imm'] = np.outer(W['med'], r['imm'])
    st['mkt'] = np.outer(W['pop'], r['mkt'])
    # job losers: cut-related share by state's share of lost dollars, economy-wide residual by population
    fed_share = (np.outer(W['exp'], r['fed_mcd']) + np.outer(W['snap'], r['fed_snap']) + np.outer(W['pop'], r['fed_ptc'])) / r['fed_cut']
    cut_part = np.minimum(cut_jobs[k], job_losers[k])
    resid = job_losers[k] - cut_part
    st['jobs'] = (fed_share * cut_part + np.outer(W['pop'], resid)) * (1 - P['ov_jobs'])
    people = sum(st.values())
    gdp = (np.outer(W['exp'], r['fed_mcd']) * P['mult_mcd'] + np.outer(W['snap'], r['fed_snap']) * P['mult_snap']
           + np.outer(W['pop'], r['fed_ptc']) * P['mult_ptc'])
    fed = fed_share * r['fed_cut']
    medicare_cost = np.outer(W['mcr'], r['medicare_cost'])
    # newly uninsured by state: Medicaid losers by expansion share, immigrants by Medicaid share, Marketplace by population
    nu = np.outer(W['exp'], r['mcd_loss']) + np.outer(W['med'], r['imm']) + np.outer(W['pop'], r['mkt'])
    hosp_state = nu / nu.sum(axis=0) * r['hosp_er_cost']
    jobs_cut = fed_share * cut_jobs[k]
    return people, gdp, fed, medicare_cost, jobs_cut, st, hosp_state, hosp_state / r['hosp_er_cost'] * r['uncomp_care']


rows = []
A6, A12 = alloc(6), alloc(12)
for i, s in d.reset_index(drop=True).iterrows():
    row = dict(state=s.state, abbr=s.abbr, population=int(s.population_2025))
    for k, A in ((6, A6), (12, A12)):
        people, gdp, fed, mc, jc, st, hs, us = A
        lo, mid, hi = q(people[i])
        row.update({f'people_{k}m_low': round(lo, -2), f'people_{k}m': round(mid, -2), f'people_{k}m_high': round(hi, -2)})
        row[f'per10k_{k}m'] = round(mid / s.population_2025 * 1e4, 1)
        glo, gmid, ghi = q(gdp[i])
        row.update({f'gdp_loss_{k}m_low': round(glo / 1e6, 1), f'gdp_loss_{k}m': round(gmid / 1e6, 1), f'gdp_loss_{k}m_high': round(ghi / 1e6, 1)})
        row[f'fed_cut_{k}m'] = round(float(np.median(fed[i])) / 1e6, 1)
        row[f'jobs_cut_{k}m'] = round(float(np.median(jc[i])), -1)
        row[f'medicare_cost_{k}m'] = round(float(np.median(mc[i])) / 1e6, 1)
        hlo, hmid, hhi = q(hs[i])
        row.update({f'hosp_er_{k}m_low': round(hlo / 1e6, 1), f'hosp_er_{k}m': round(hmid / 1e6, 1), f'hosp_er_{k}m_high': round(hhi / 1e6, 1)})
        row[f'uncomp_{k}m'] = round(float(np.median(us[i])) / 1e6, 1)
        if k == 12:
            for c in ('mcd', 'snap', 'imm', 'mkt', 'jobs'):
                row[f'{c}_12m'] = round(float(np.median(st[c][i])), -2)
    rows.append(row)
st = pd.DataFrame(rows)
st.to_csv(OUT + 'forecast_states.csv', index=False)

pd.set_option('display.width', 220)
print(nat.assign(low=lambda x: x.low.round(-3), median=lambda x: x['median'].round(-3), high=lambda x: x.high.round(-3))
      [['metric', 'horizon', 'low', 'median', 'high']].to_string())
print(st.sort_values('per10k_12m', ascending=False)[['state', 'people_12m_low', 'people_12m', 'people_12m_high', 'per10k_12m', 'gdp_loss_12m']].head(8).to_string())
print('sum state people medians 12m', st.people_12m.sum(), 'sum gdp 12m ($M)', st.gdp_loss_12m.sum())
print(tl[['month', 'date', 'combined_low', 'combined_median', 'combined_high']].round(-3).to_string())
