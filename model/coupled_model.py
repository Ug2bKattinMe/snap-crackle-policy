"""Coupled monthly model of 2027: Medicaid, SNAP, jobs, health events and hospital costs move together.

What is different from model/forecast_model.py (the "independent" model):
  1. Medicaid expansion adults are followed month by month as a Markov chain over 48 joint states:
       coverage {Medicaid, uninsured, other coverage} x SNAP {never on, on, recently cut (<=3 months), cut}
       x work {employed, not employed} x exemption {subject to work rules, exempt}.
     Losses happen at renewal and work checks (the first check at each person's next renewal, then every six months),
     people can re-enroll, and the result is compared with a no-new-rules chain (annual renewals, normal churn).
     The Medicaid-SNAP overlap and the 6-month timing come out of the chain instead of being set.
  2. Losing SNAP raises the odds of a hospital stay (logistic: odds ratio for losing participation x odds ratio per $10
     of monthly benefit, with the benefit converted to the study's prices), building up over three months.
  3. Hospital stays raise the chance of losing a job; losing a job raises the chance of failing the Medicaid work
     check and, in the 10 non-expansion states, can push Marketplace enrollees below 100% of poverty, where they lose
     their premium tax credit (the coverage gap).
  4. Uninsured hospital and ER care is costed with 2026 levels (Epic Research 2023 unwinding shift, CPI hospital
     services), and part of the unpaid cost can be passed on to commercial premiums.
  5. Uncertain inputs move together: an "administrative friction" factor links Medicaid, SNAP and Marketplace losses,
     and an "economy" factor links unemployment, job loss and job finding (Gaussian copula). A second run with the
     links removed shows how much wider the 95% intervals get because of them.

Levels come from 2026 data (SNAP caseload through mid-2026, Nebraska's first work-requirement results, Fed September
2026 projections, CPI September 2026, 2026 Marketplace enrollment). Older studies supply only relative effects.
All dollars are 2027 dollars. Intervals are 95% (2.5th-97.5th percentile). Fixed seed: reruns reproduce the outputs.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent.parent
H = str(ROOT / 'data' / 'inputs') + '/'
OUT = str(ROOT / 'data') + '/'
N = 10000
SEED = 20261102
MONTHS = 12

# ---------------- state inputs (same as the independent model) ----------------
imp = pd.read_csv(H + 'impact_2027.csv')
snap_st = pd.read_csv(H + 'snap_fy2025_raw.txt', sep='|', names=['state', 'snap_fy2025'])
med = pd.read_csv(H + 'medicaid_chip_enrollment_jun2026.csv')[['abbr', 'medicaid_chip_enrollees']]
mcr = pd.read_csv(H + 'medicare_enrollment_2024.csv')[['abbr', 'medicare_enrollees']]
d = (imp[['state', 'abbr', 'population_2025', 'exp_scaled']].merge(snap_st, on='state')
     .merge(med, on='abbr').merge(mcr, on='abbr'))
assert len(d) == 51
d['exp_scaled'] = d.exp_scaled.fillna(0)
d['nonexp'] = (d.exp_scaled == 0).astype(float)
w = lambda s: (s / s.sum()).to_numpy()
W = dict(exp=w(d.exp_scaled), snap=w(d.snap_fy2025), pop=w(d.population_2025), med=w(d.medicaid_chip_enrollees),
         mcr=w(d.medicare_enrollees), nonexp_pop=w(d.population_2025 * d.nonexp))
EXP_TOTAL = d.exp_scaled.sum()  # 20.4M expansion adults


# ---------------- uncertain inputs ----------------
def tri_inv(u, a, c, b):
    """Inverse CDF of a triangular(a, mode c, b) distribution."""
    fc = (c - a) / (b - a)
    return np.where(u < fc, a + np.sqrt(u * (b - a) * (c - a)), b - np.sqrt((1 - u) * (b - a) * (b - c)))


def draw(rho_friction=0.6, rho_economy=0.7, seed=SEED):
    rng = np.random.default_rng(seed)
    zF, zE = rng.standard_normal(N), rng.standard_normal(N)

    def cu(z, rho, sign=1):  # uniform linked to a shared factor
        return norm.cdf(sign * rho * z + np.sqrt(1 - rho ** 2) * rng.standard_normal(N))

    U = lambda a, b, u=None: a + (b - a) * (rng.random(N) if u is None else u)
    T = lambda a, c, b, u=None: tri_inv(rng.random(N) if u is None else u, a, c, b)
    P = dict(
        # --- Medicaid chain (expansion adults) ---
        exempt0=U(0.40, 0.60),                 # exempt: parents of children <=13, medically frail, students, etc.
        emp_ne=U(0.70, 0.85), emp_ex=U(0.35, 0.55),  # employed share, subject vs exempt adults
        snap0=U(0.35, 0.45),                   # share of expansion adults on SNAP before the law (KFF: 40% of Medicaid enrollees)
        snap_cut0=U(0.12, 0.30, cu(zF, rho_friction)),  # of subject SNAP recipients, share already cut by Jan 2027
        # failure at a check, subject + employed (mostly paperwork). Nebraska 2026: about 27% of subject adults and
        # 15% of all adults checked lost coverage at renewal, 92% for missing paperwork; centered lower because
        # Nebraska ran before CMS's June 2026 rule and most states will match data ex parte.
        proc_ne=T(0.06, 0.14, 0.26, cu(zF, rho_friction)),
        true_fail=U(0.30, 0.70),               # extra failure for subject adults not employed (cannot show 80 hours)
        ex_ratio=U(0.15, 0.40),                # exempt adults fail at this fraction of the subject rate (proving exemption)
        snap_link=U(1.2, 2.0),                 # failure multiplier for people already cut from SNAP (same paperwork)
        other_cov=U(0.05, 0.25),               # share of people losing Medicaid who find other coverage (Arkansas: ~none)
        reenroll_cf=U(0.08, 0.15),             # monthly re-enrollment after a normal procedural loss (unwinding: ~1/3 in 90 days)
        reenroll_pol=U(0.25, 0.60),            # ... multiplied by this under work rules (must first show a compliant month)
        base_churn=U(0.03, 0.06),              # loss per annual renewal without the new rules
        # --- SNAP inside the chain ---
        snap_tl=U(0.25, 0.34),                 # monthly cut for subject, not-employed recipients (3-month time limit)
        waiver=U(0.05, 0.20),                  # share living in areas still waived
        snap_proc=U(0.003, 0.012, cu(zF, rho_friction)),  # monthly paperwork cuts, employed recipients
        snap_back=U(0.03, 0.08),               # monthly return to SNAP for employed people who were cut
        # --- SNAP nationwide (anchored to 2026 data) ---
        snap_drop_obs=U(4.6e6, 5.4e6),         # observed fall July 2025 -> mid-2026 (USDA 42.0M -> 37.0M Apr; CBPP >5M by June)
        snap_policy_share=U(0.45, 0.85, cu(zF, rho_friction)),  # share of that fall caused by the law (rest: economy, chilling, other)
        snap_add27=U(0.1e6, 0.6e6, cu(zE, rho_economy)),        # further 2027 losses (state cost shift from Oct 2026, waivers ending)
        snap_benefit=U(185, 195),              # $ per person per month
        # --- health effects of losing SNAP (relative effects from studies; levels from 2026 data) ---
        or_part=U(1.00, 1.075),                # odds of a hospital stay when off SNAP vs on (Samuel/Szanton 2018: aOR 0.96, CI 0.93-0.99)
        or_per10=T(1.000, 1.010, 1.015),       # per $10 of monthly benefit lost, in study prices (aOR 0.99 per $10)
        price_ratio=U(1.38, 1.46),             # food-at-home prices Sept 2026 vs 2009-12 study years (CPI 321.8 vs ~226)
        or_ed=T(1.00, 1.02, 1.06),             # ER visits: study found no significant effect, so centered near none
        ip_ins=U(0.07, 0.11), ed_ins=U(0.85, 1.10),  # yearly stays and ER visits, insured low-income adults (T-MSIS ER 0.99)
        ip_unins_ratio=U(0.50, 0.80),          # uninsured stays relative to insured
        ed_unins_ratio=U(0.55, 0.90),          # Epic 2023 unwinding: Medicaid ER share -2.8 pts, self-pay +2.4 pts
        outside_ip=U(0.06, 0.12), outside_ed=U(0.45, 0.75),  # people cut from SNAP outside the chain (older, children, non-expansion)
        outside_unins=U(0.15, 0.30),           # ... share of them uninsured
        # --- jobs ---
        u12=np.clip(T(4.0, 4.1, 4.5, cu(zE, rho_economy)) + 0.5 * norm.ppf(cu(zE, rho_economy)) * 0.6, 3.6, 6.5),
        # Fed Sept 2026 median 4.1 (range 4.0-4.5) widened for the Fed's own forecast errors and oil-shock risk
        sep0=U(0.020, 0.035, cu(zE, rho_economy)),     # monthly job loss, low-wage workers, at 4.2% unemployment
        find0=U(0.15, 0.30, cu(zE, rho_economy, -1)),  # monthly job finding (hiring weak: +29k payrolls Sept 2026)
        health_job=U(0.02, 0.08),              # chance a hospital stay leads to job loss (Dobkin et al.: -11 pts employment in 3 yrs)
        jobs_per_bn=U(7000, 11500), ov_jobs=U(0.05, 0.15),
        # --- coverage gap, non-expansion states ---
        mkt_enroll=U(17.5e6, 19.2e6),          # 2026 Marketplace (KFF: 19.2M Feb, ~17.5M by year end)
        mkt_nonexp=U(0.50, 0.62),              # share in the 10 non-expansion states (FL, TX, GA are the largest)
        mkt_lowinc=U(0.35, 0.50),              # share of those at 100-150% of poverty
        gap_given_jobloss=U(0.15, 0.45),       # chance a job loss there drops yearly income below 100% and the credit is lost
        # --- other groups (same as independent model, Marketplace linked to friction) ---
        imm_mcd=U(70e3, 130e3), imm_mcr=U(70e3, 130e3),
        mkt_loss12=T(0.6e6, 1.4e6, 2.6e6, cu(zF, rho_friction)), mkt_front=U(0.70, 0.90),
        # --- dollars ---
        mcd_fed_per_adult=U(5600, 7700), ptc_per_person=U(4000, 6500),
        mult_mcd=U(1.10, 1.25), mult_snap=U(1.20, 1.60), mult_ptc=U(1.00, 1.20), tax_share=U(0.065, 0.095),
        unins_share=U(0.70, 0.95),             # Marketplace and immigrant coverage losers who stay uninsured
        ed_cost=U(700, 950), ip_cost=U(12000, 16000),  # 2027$; CPI hospital services +5.6% in the year to Sept 2026
        unpaid_share=U(0.75, 0.90), oop_per_uninsured=U(500, 1300),
        pass_through=T(0.0, 0.10, 0.35),       # share of uncompensated care hospitals pass on to commercial prices
        commercial_lives=U(160e6, 170e6),
        partb_payers=U(54e6, 58e6), partb_rise=U(5.5, 8.0), partd_ded_payers=U(10e6, 18e6),
        partd_cap_hitters=U(1.3e6, 2.4e6), pdp_prem_rise=U(3, 10), pdp_payers=U(17e6, 21e6),
    )
    return P


# ---------------- the Medicaid-SNAP-jobs chain ----------------
# axes: cov (0 Medicaid, 1 uninsured, 2 other) x snap (0 never, 1 on, 2 recently cut, 3 cut) x work (0 employed, 1 not)
#       x exempt (0 subject, 1 exempt) x draw
def logit(p):
    return np.log(p / (1 - p))


def expit(x):
    return 1 / (1 + np.exp(-x))


def run_chain(P, policy=True):
    X = np.zeros((3, 4, 2, 2, N))
    for ex, share in ((0, 1 - P['exempt0']), (1, P['exempt0'])):
        emp = P['emp_ne'] if ex == 0 else P['emp_ex']
        for wk, ws in ((0, emp), (1, 1 - emp)):
            base = EXP_TOTAL * share * ws
            on = base * P['snap0']
            cut = np.zeros(N)
            if policy and ex == 0:  # people not employed were cut first
                cut = on * np.minimum(0.9, P['snap_cut0'] * (1.8 if wk == 1 else 0.75))
            X[0, 0, wk, ex] = base - on
            X[0, 1, wk, ex] = on - cut
            X[0, 3, wk, ex] = cut
    u_path = 4.2 + (P['u12'] - 4.2) * np.arange(1, MONTHS + 1)[:, None] / 12
    # benefit lost, in study-period dollars -> log odds of a hospital stay when cut from SNAP
    lnor_ip = np.log(P['or_part']) + np.log(P['or_per10']) * P['snap_benefit'] / P['price_ratio'] / 10
    lnor_ed = np.log(P['or_ed'])
    m_ip = lambda r: 1 - (1 - r) ** (1 / 12)  # yearly rate -> monthly probability
    ip_m = {0: m_ip(P['ip_ins']), 1: m_ip(P['ip_ins'] * P['ip_unins_ratio']), 2: m_ip(P['ip_ins'])}
    ed_m = {0: P['ed_ins'] / 12, 1: P['ed_ins'] * P['ed_unins_ratio'] / 12, 2: P['ed_ins'] / 12}
    snap_eff = np.array([0.0, 0.0, 0.5, 1.0])  # recently cut: half the effect (builds over ~3 months)
    hist = {k: [] for k in ('mcd_off', 'unins', 'other', 'overlap', 'ever_lost', 'reenrolled', 'stays_unins',
                            'ed_unins', 'stays_ins', 'ed_ins', 'jobless', 'health_jobloss', 'snap_cut',
                            'snap_stays_ins', 'snap_stays_unins', 'snap_ed_ins', 'snap_ed_unins')}
    ever = np.zeros(N); reen = np.zeros(N); prev_stays_emp = np.zeros((3, 4, 2, N))
    for t in range(MONTHS):
        u = u_path[t]
        # 1. jobs: separations scale with unemployment; hospital stays last month add job losses
        sep = P['sep0'] * u / 4.2
        find = P['find0'] * 4.2 / u
        E, J = X[:, :, 0].copy(), X[:, :, 1].copy()
        health_loss = P['health_job'] * prev_stays_emp
        lose = E * sep + health_loss
        lose = np.minimum(lose, E)
        gain = J * find
        X[:, :, 0] = E - lose + gain
        X[:, :, 1] = J + lose - gain
        hist['health_jobloss'].append(health_loss.sum(axis=(0, 1, 2)))
        # 2. SNAP
        if policy:
            on = X[:, 1].copy(); rec = X[:, 2].copy(); cut = X[:, 3].copy()
            to_rec = np.zeros_like(on)
            to_rec[:, 1, 0] = on[:, 1, 0] * P['snap_tl'] * (1 - P['waiver'])  # subject, not employed
            to_rec[:, 0] += on[:, 0] * P['snap_proc']                            # employed: paperwork
            back = np.zeros_like(cut)
            back[:, 0] = cut[:, 0] * P['snap_back']
            X[:, 1] = on - to_rec + back
            X[:, 2] = rec + to_rec - rec / 3
            X[:, 3] = cut + rec / 3 - back
        # 3. Medicaid checks and re-enrollment
        Mx = X[0].copy()
        if policy:
            c = 1 / 12 if t < 6 else 1 / 6   # first checks at next annual renewal, then every six months
            pf = np.zeros((4, 2, 2, N))
            pf[:, 0, 0] = P['proc_ne']
            pf[:, 1, 0] = P['proc_ne'] + (1 - P['proc_ne']) * P['true_fail']
            pf[:, :, 1] = P['proc_ne'] * P['ex_ratio']
            pf[2:] = np.minimum(0.95, pf[2:] * P['snap_link'])
            r = np.zeros((4, 2, 2, N))
            r[:, 0] = P['reenroll_cf'] * P['reenroll_pol']            # employed can show 80 hours
            r[:, 1, 0] = P['reenroll_cf'] * P['reenroll_pol'] * 0.25  # subject and not employed: hard
            r[:, 1, 1] = P['reenroll_cf'] * P['reenroll_pol']         # exempt
        else:
            c = 1 / 12
            pf = np.broadcast_to(P['base_churn'], (4, 2, 2, N)).copy()
            r = np.broadcast_to(P['reenroll_cf'], (4, 2, 2, N)).copy()
        fail = Mx * c * pf
        back_in = X[1] * r
        X[0] = Mx - fail + back_in
        X[1] = X[1] + fail * (1 - P['other_cov']) - back_in
        X[2] = X[2] + fail * P['other_cov']
        ever += fail.sum(axis=(0, 1, 2)); reen += back_in.sum(axis=(0, 1, 2))
        # 4. health events this month
        stays = np.zeros((3, 4, 2, 2, N)); eds = np.zeros((3, 4, 2, 2, N))
        xs = np.zeros((3, N)); xe = np.zeros((3, N))  # extra stays / ER visits caused by SNAP cuts, by coverage
        for cv in range(3):
            for s in range(4):
                p_ip = expit(logit(ip_m[cv]) + snap_eff[s] * lnor_ip)
                stays[cv, s] = X[cv, s] * p_ip
                eds[cv, s] = X[cv, s] * ed_m[cv] * np.exp(snap_eff[s] * lnor_ed)
                xs[cv] += (X[cv, s] * (p_ip - ip_m[cv])).sum(axis=(0, 1))
                xe[cv] += (X[cv, s] * ed_m[cv] * (np.exp(snap_eff[s] * lnor_ed) - 1)).sum(axis=(0, 1))
        hist['snap_stays_ins'].append(xs[0] + xs[2]); hist['snap_stays_unins'].append(xs[1])
        hist['snap_ed_ins'].append(xe[0] + xe[2]); hist['snap_ed_unins'].append(xe[1])
        prev_stays_emp = stays[:, :, 0].sum(axis=2)  # stays among employed people (both exemption groups)
        prev_stays_emp = np.repeat(prev_stays_emp[:, :, None] / 2, 2, axis=2)  # spread back over exemption groups
        hist['mcd_off'].append(X[1:].sum(axis=(0, 1, 2, 3)))
        hist['unins'].append(X[1].sum(axis=(0, 1, 2)))
        hist['other'].append(X[2].sum(axis=(0, 1, 2)))
        hist['overlap'].append(X[1:, 2:].sum(axis=(0, 1, 2, 3)))
        hist['ever_lost'].append(ever.copy()); hist['reenrolled'].append(reen.copy())
        hist['stays_unins'].append(stays[1].sum(axis=(0, 1, 2))); hist['ed_unins'].append(eds[1].sum(axis=(0, 1, 2)))
        hist['stays_ins'].append(stays[[0, 2]].sum(axis=(0, 1, 2, 3))); hist['ed_ins'].append(eds[[0, 2]].sum(axis=(0, 1, 2, 3)))
        hist['jobless'].append(X[:, :, 1].sum(axis=(0, 1, 2)))
        hist['snap_cut'].append(X[:, 2:].sum(axis=(0, 1, 2, 3)))
    return {k: np.array(v) for k, v in hist.items()}, u_path


def simulate(P):
    pol, u_path = run_chain(P, True)
    cf, _ = run_chain(P, False)
    mo = np.arange(1, MONTHS + 1)[:, None]
    net = {k: pol[k] - cf[k] for k in pol}
    mcd_net = net['mcd_off']                       # Medicaid losses caused by the rules, people off at month end
    overlap = pol['overlap'] - cf['overlap']      # of those, cut from SNAP too
    unins_chain = net['unins']
    # SNAP nationwide: anchored to the observed 2025-26 fall plus 2027 additions (in place all year)
    snap_total = P['snap_drop_obs'] * P['snap_policy_share'] + P['snap_add27'] * mo / 12
    chain_snap_cut = pol['snap_cut']               # SNAP-cut people inside the chain (part of snap_total)
    outside_cut = np.maximum(snap_total - chain_snap_cut, 0)
    imm = np.tile(P['imm_mcd'] + P['imm_mcr'], (MONTHS, 1))
    mkt = P['mkt_loss12'] * (P['mkt_front'] + (1 - P['mkt_front']) * mo / 12)
    # jobs: cut-related vs economy-wide (take the larger), plus health-related losses from the chain
    LF = 7.1e6 / 0.042
    econ_rise = np.maximum((u_path - 4.2) / 100 * LF, 0)
    # coverage gap: excess job losses among low-income Marketplace workers in non-expansion states
    pool = P['mkt_enroll'] * P['mkt_nonexp'] * P['mkt_lowinc'] * 0.75
    excess_sep = np.maximum(P['sep0'] * (u_path / 4.2 - 1), 0)
    gap = np.cumsum(pool * excess_sep * P['gap_given_jobloss'], axis=0)
    # federal spending reduction (annualized rate at each month end)
    rate_mcd = mcd_net * P['mcd_fed_per_adult']
    rate_snap = snap_total * P['snap_benefit'] * 12
    rate_ptc = (mkt + gap) * P['ptc_per_person']
    # health cascade outside the chain (SNAP cuts among older adults, children, non-expansion states)
    lnor_ip = np.log(P['or_part']) + np.log(P['or_per10']) * P['snap_benefit'] / P['price_ratio'] / 10
    out_ip_base = 1 - (1 - P['outside_ip']) ** (1 / 12)
    out_extra_stays = outside_cut * (expit(logit(out_ip_base) + lnor_ip) - out_ip_base)
    out_extra_ed = outside_cut * P['outside_ed'] / 12 * (P['or_ed'] - 1)
    chain_extra_stays = pol['snap_stays_ins'] + pol['snap_stays_unins']
    # uninsured hospital and ER costs (month by month)
    other_unins = (imm + mkt + gap) * P['unins_share']
    ed_unins_other = other_unins * P['ed_ins'] * P['ed_unins_ratio'] / 12
    ip_unins_other = other_unins * (1 - (1 - P['ip_ins'] * P['ip_unins_ratio']) ** (1 / 12))
    unins_ed = net['ed_unins'] + ed_unins_other + out_extra_ed * P['outside_unins']
    unins_ip = net['stays_unins'] + ip_unins_other + out_extra_stays * P['outside_unins']
    hosp_unins = unins_ed * P['ed_cost'] + unins_ip * P['ip_cost']
    # extra care for people who are still insured but were cut from SNAP (paid by Medicaid, Medicare or insurers)
    extra_ins_cost = ((pol['snap_stays_ins'] + out_extra_stays * (1 - P['outside_unins'])) * P['ip_cost']
                      + (pol['snap_ed_ins'] + out_extra_ed * (1 - P['outside_unins'])) * P['ed_cost'])
    rate_total = rate_mcd + rate_snap + rate_ptc
    # job losses after hospital stays caused by SNAP cuts (about 75% of the chain and half of others are working)
    health_jobs = np.cumsum((chain_extra_stays * 0.75 + out_extra_stays * 0.5) * P['health_job'], axis=0)
    out = {}
    for k in (6, 12):
        s = slice(0, k)
        fed_mcd = rate_mcd[s].sum(0) / 12 - 0.9 * extra_ins_cost[s].sum(0) * 0.5  # about half of insured extra care is Medicaid
        fed_snap = rate_snap[s].sum(0) / 12
        fed_ptc = rate_ptc[s].sum(0) / 12
        fed = fed_mcd + fed_snap + fed_ptc
        gdp = fed_mcd * P['mult_mcd'] + fed_snap * P['mult_snap'] + fed_ptc * P['mult_ptc']
        cut_jobs = rate_total[k - 1] / 1e9 * P['jobs_per_bn'] + health_jobs[k - 1]
        job_losers = np.maximum(cut_jobs, econ_rise[k - 1])
        people = (mcd_net[k - 1] + imm[k - 1] + snap_total[k - 1] + mkt[k - 1] + gap[k - 1] + job_losers
                  - overlap[k - 1] - P['ov_jobs'] * job_losers)
        hosp = hosp_unins[s].sum(0)
        uncomp = hosp * P['unpaid_share']
        frac = k / 12
        medicare = frac * (P['partb_payers'] * P['partb_rise'] * 12 + P['pdp_payers'] * P['pdp_prem_rise'] * 12) \
            + min(1.0, frac * 1.6) * P['partd_ded_payers'] * 85 + max(0.0, frac * 2 - 1) * P['partd_cap_hitters'] * 300
        unins_people = unins_chain + other_unins
        oop = (unins_people[s] * P['oop_per_uninsured']).sum(0) / 12
        out[k] = dict(
            people=people, mcd_net=mcd_net[k - 1], mcd_ever=net['ever_lost'][k - 1],
            mcd_overlap=overlap[k - 1], snap_total=snap_total[k - 1], mkt=mkt[k - 1], gap=gap[k - 1], imm=imm[k - 1],
            job_losers=job_losers, jobs_cut=cut_jobs, jobs_econ=econ_rise[k - 1], health_jobs=health_jobs[k - 1],
            newly_uninsured=unins_people[k - 1], unins_person_months=unins_people[s].sum(0),
            fed_cut=fed, gdp_loss=gdp, tax_loss=gdp * P['tax_share'],
            er_visits=unins_ed[s].sum(0), ip_stays=unins_ip[s].sum(0), hosp_er_cost=hosp, uncomp_care=uncomp,
            cascade_stays=(out_extra_stays[s].sum(0) + chain_extra_stays[s].sum(0)),
            cascade_cost=(extra_ins_cost[s].sum(0) + (pol['snap_stays_unins'][s].sum(0)
                          + out_extra_stays[s].sum(0) * P['outside_unins']) * P['ip_cost']
                          + (pol['snap_ed_unins'][s].sum(0) + out_extra_ed[s].sum(0) * P['outside_unins']) * P['ed_cost']),
            cost_shift=uncomp * P['pass_through'], cost_shift_per_person=uncomp * P['pass_through'] / P['commercial_lives'] * 12 / k,
            household_cost=fed_snap + oop + medicare, medicare_cost=medicare)
    timeline = dict(mcd_net=mcd_net, mcd_ever=net['ever_lost'], overlap=overlap,
                    snap_total=snap_total, mkt=mkt, gap=gap, unins=unins_chain + other_unins)
    return out, timeline


q = lambda x: (float(np.percentile(x, 2.5)), float(np.median(x)), float(np.percentile(x, 97.5)))

if __name__ == '__main__':
    P = draw()
    res, tl = simulate(P)
    P0 = draw(0.0, 0.0)
    res0, _ = simulate(P0)
    labels = dict(
        people='Combined people affected (counted once)', mcd_net='Off Medicaid because of the new rules (month end)',
        mcd_ever='Ever lost Medicaid because of the new rules',
        mcd_overlap='Off Medicaid and cut from SNAP (overlap from the chain)', snap_total='Off SNAP because of the law',
        mkt='Lost Marketplace coverage or subsidy', gap='Fell into the coverage gap after losing a job (non-expansion states)',
        imm='Immigrants losing Medicaid or Medicare', job_losers='Job losers counted', jobs_cut='Jobs lost from the cuts',
        jobs_econ='Change in unemployed, economy-wide', health_jobs='Jobs lost after a hospital stay',
        newly_uninsured='Newly uninsured people (month end)', unins_person_months='Uninsured person-months',
        fed_cut='Federal spending reduction ($)', gdp_loss='GDP loss ($)', tax_loss='State and local tax revenue loss ($)',
        er_visits='ER visits by the newly uninsured', ip_stays='Hospital stays by the newly uninsured',
        hosp_er_cost='Cost of hospital and ER care for the newly uninsured ($)',
        uncomp_care='Unpaid by patients: uncompensated hospital care ($)',
        cascade_stays='Extra hospital stays linked to losing SNAP', cascade_cost='Cost of extra care linked to losing SNAP ($)',
        cost_shift='Uncompensated care passed on to commercial premiums ($)',
        cost_shift_per_person='Passed on per commercially insured person, yearly rate ($/person)',
        household_cost='Added household costs ($)', medicare_cost='Added Medicare premiums and drug costs ($)')
    rows = []
    for key, lab in labels.items():
        for k in (6, 12):
            lo, mid, hi = q(res[k][key]); lo0, _, hi0 = q(res0[k][key])
            rows.append(dict(metric_id=key, metric=lab, horizon=f'{k} months', months=k, low=lo, median=mid, high=hi,
                             low_unlinked=lo0, high_unlinked=hi0,
                             unit='dollars per person' if '/person' in lab else 'dollars' if '($)' in lab else 'people'))
    nat = pd.DataFrame(rows)
    nat.to_csv(OUT + 'coupled_national.csv', index=False)
    t_rows = []
    for i in range(MONTHS):
        r = dict(month=i + 1, date=(pd.Timestamp('2027-01-01') + pd.DateOffset(months=i + 1) - pd.DateOffset(days=1)).strftime('%Y-%m-%d'))
        for k2, v in tl.items():
            lo, mid, hi = q(v[i]); r[k2] = mid
            if k2 in ('mcd_net', 'unins'):
                r[k2 + '_low'], r[k2 + '_high'] = lo, hi
        t_rows.append(r)
    pd.DataFrame(t_rows).to_csv(OUT + 'coupled_timeline.csv', index=False)
    # states: allocate each draw's national pieces by state shares
    r12 = res[12]
    people_st = (np.outer(W['exp'], r12['mcd_net'] - r12['mcd_overlap']) + np.outer(W['snap'], r12['snap_total'])
                 + np.outer(W['med'], r12['imm']) + np.outer(W['pop'], r12['mkt']) + np.outer(W['nonexp_pop'], r12['gap'])
                 + np.outer(W['pop'], r12['job_losers'] * (1 - P['ov_jobs'])))
    unins_w = (np.outer(W['exp'], tl['unins'][-1] - (r12['mkt'] + r12['gap'] + r12['imm']) * P['unins_share'])
               + np.outer(W['pop'], (r12['mkt']) * P['unins_share']) + np.outer(W['med'], r12['imm'] * P['unins_share'])
               + np.outer(W['nonexp_pop'], r12['gap'] * P['unins_share']))
    unins_w = unins_w / unins_w.sum(axis=0)
    hosp_st = unins_w * r12['hosp_er_cost']
    st_rows = []
    for i, s in d.reset_index(drop=True).iterrows():
        lo, mid, hi = q(people_st[i]); hlo, hmid, hhi = q(hosp_st[i])
        st_rows.append(dict(state=s.state, abbr=s.abbr, expansion=int(s.nonexp == 0), people_12m_low=round(lo, -2),
                            people_12m=round(mid, -2), people_12m_high=round(hi, -2),
                            per10k_12m=round(mid / s.population_2025 * 1e4, 1),
                            hosp_er_12m=round(hmid / 1e6, 1), hosp_er_12m_low=round(hlo / 1e6, 1), hosp_er_12m_high=round(hhi / 1e6, 1),
                            uncomp_12m=round(float(np.median(hosp_st[i] * P['unpaid_share'])) / 1e6, 1)))
    pd.DataFrame(st_rows).to_csv(OUT + 'coupled_states.csv', index=False)
    pd.set_option('display.width', 250)
    show = nat.copy()
    for c in ('low', 'median', 'high', 'low_unlinked', 'high_unlinked'):
        show[c] = np.where(show.unit == 'dollars', (show[c] / 1e9).round(2), (show[c] / 1e3).round(0))
    print(show[['metric_id', 'horizon', 'low', 'median', 'high', 'low_unlinked', 'high_unlinked']].to_string())
    print(pd.DataFrame(t_rows)[['month', 'mcd_net', 'mcd_ever', 'overlap', 'unins']].astype(float).round(-3).to_string())
    print('Medicaid share of 12-month losses reached by June:', round(np.median(tl['mcd_net'][5] / tl['mcd_net'][11]), 3))
