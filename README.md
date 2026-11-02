# 2027 Coverage, SNAP and Jobs Impact Forecast

A scenario forecast of how many people lose Medicaid, SNAP, Medicare or Marketplace help, or a job tied to those cuts, in 2027, and what that costs the economy, households and hospitals at 6 months (January–June 2027) and 12 months (calendar 2027). Results are national and by state, with 95% intervals.

> This is a modeled forecast, not an official projection. Every uncertain input and its basis is listed in `data/forecast_assumptions.csv` and on the page.

## Headline results (medians, 95% intervals)

| | 6 months | 12 months |
|---|---|---|
| People affected, counted once | 5.9M (4.9M – 7.1M) | 7.3M (6.0M – 8.8M) |
| Lost economic output (GDP) | $11.5B | $29.5B ($22.6B – $37.7B) |
| Jobs lost from the cuts | 218K | 327K (217K – 471K) |
| Hospital and ER care for the newly uninsured | $1.0B | $2.8B ($1.8B – $4.2B) |

## View the dashboard

The dashboard is a static page: `index.html` plus the CSV and JSON files in `data/`. It loads d3 v7 from cdnjs and fonts from Google Fonts.

Run it locally (browsers block `fetch` from `file://`, so use a small web server):

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

Publish it with GitHub Pages: push this repository, then in **Settings → Pages** choose **Deploy from a branch**, branch `main`, folder `/ (root)`.

## Rerun the model

```bash
pip install -r requirements.txt
python3 model/snap_overlap_model.py   # SNAP x Medicaid/Medicare overlap by state -> data/inputs/snap_overlap_2027.csv
python3 model/forecast_model.py       # forecast -> data/forecast_national.csv, forecast_timeline.csv, forecast_states.csv
python3 model/coupled_model.py        # coupled monthly model -> data/coupled_national.csv, coupled_timeline.csv, coupled_states.csv
```

Both scripts use a fixed random seed, so a rerun reproduces the published numbers exactly. Change an input range in `model/forecast_model.py` (the `P = dict(...)` block) and rerun to see a different scenario; update `data/forecast_assumptions.csv` to match so the page's input table stays accurate.

`model/project_states.py` rebuilds `data/us_state_shapes.json` from a US states GeoJSON file (Albers USA layout with Alaska and Hawaii insets):

```bash
python3 model/project_states.py us-states.json data/inputs/state_data.csv data/us_state_shapes.json
```

## How the forecast works

1. **Start from the people each 2027 rule reaches:** Medicaid expansion adults by state (20.4M, scaled to CMS's June 2025 count), SNAP recipients (FY2025), immigrants losing Medicaid or Medicare (CBO), Marketplace enrollees and Medicare enrollees.
2. **Apply loss rates and timing.** Medicaid losses build through 2027 as states check work hours and run six-month renewals; SNAP losses are in place from the November 2025 rule change; Marketplace losses land mostly at the January 1 plan-year start.
3. **Add job losses.** Jobs lost from the cuts = lost federal dollars × jobs per $1 billion (Commonwealth Fund/GWU, IMPLAN). The economy-wide change is the Federal Reserve's September 2026 unemployment projection applied to the labor force. The larger of the two is counted, since the Fed outlook already reflects these laws.
4. **Remove double counting** of adults who lose both Medicaid and SNAP under the same work rules, and of job losers already in another group.
5. **Turn people into dollars:** federal spending reduction, GDP loss (spending multipliers), state and local tax loss, household costs (lost SNAP, new medical bills, higher Medicare premiums and drug costs), and hospital and ER care for the newly uninsured (visit and stay rates × HCUP hospital costs, with the unpaid share as uncompensated care).
6. **Simulate 20,000 scenarios,** drawing every input from its range. The headline is the median; the 95% interval is the 2.5th to 97.5th percentile. States get each scenario's national totals in proportion to their enrollment, SNAP, population or Medicare shares.

### Limits

- The 95% interval covers uncertainty in the listed inputs only, not a recession, new legislation, court rulings, or states delaying work rules under good-faith exemptions.
- Job and GDP multipliers come from a study of the House-passed bill applied to this forecast's smaller 2027 dollar amounts. Most of the law's cuts fall after 2027.
- State results are allocations of national scenarios, not separate state models.
- Hospital figures are costs, not billed charges.

## Coupled model (`model/coupled_model.py`)

A second model that treats the groups as one linked system instead of independent counts. Its levels are set from 2026 data; older studies supply only relative effects.

- **Monthly Markov chain** for the 20.4M Medicaid expansion adults over 48 joint states: coverage (Medicaid, uninsured, other) × SNAP (never on, on, recently cut, cut) × work (employed, not) × work-rule status (subject, exempt). Losses happen at checks (first at each person's next renewal, then every six months), with failure rates from Nebraska's 2026 results; people can re-enroll; a no-new-rules run is subtracted.
- **SNAP** is anchored to the observed fall of about 5M from July 2025 to mid-2026 (USDA, CBPP), with the share caused by the law as a range.
- **Health cascade:** losing SNAP raises the odds of a hospital stay on a logistic scale (odds ratio for participation × odds ratio per $10 of benefit, converted from September 2026 food prices to the study's prices).
- **Jobs and coverage are linked:** job loss and hiring follow the unemployment path (Fed September 2026, widened for forecast error and the 2026 oil shock); a hospital stay can lead to job loss; not working raises the chance of failing the Medicaid check; in non-expansion states a job loss can push low-income Marketplace enrollees into the coverage gap.
- **Hospital costs** use ER and stay rates for the newly uninsured from 2023–2026 payer data (Epic Research, HCA), at 2027 hospital costs, with an optional pass-through to commercial premiums.
- **Correlated inputs:** an administrative-friction factor links Medicaid, SNAP and Marketplace losses; an economy factor links unemployment, job loss and hiring (Gaussian copula). The script also reruns with the links removed (`low_unlinked`, `high_unlinked`).

12-month medians (95% interval): 7.6M people affected (5.3M – 10.0M); 2.42M off Medicaid at year end, 2.62M ever lost; 3.58M off SNAP; $3.4B of hospital and ER care for the newly uninsured ($2.0B – $5.4B), $2.8B unpaid; about 46K extra hospital stays linked to losing SNAP. Inputs and their basis: `data/coupled_assumptions.csv`.

## Repository layout

```
index.html                 the dashboard
css/theme.css              colors, type and spacing tokens (light and dark)
css/dashboard.css          dashboard layout and components
js/dash-shim.js            loads the data files and runs the chart code
js/charts.js               charts, map and tables (d3 v7)
data/                      files the dashboard reads (model outputs, inputs table, state shapes)
data/inputs/               inputs the model reads
model/                     Python models (independent forecast, coupled model) and map projection script
```

## Data sources

- Federal Reserve, [Summary of Economic Projections, September 16, 2026](https://federalreserve.gov/monetarypolicy/fomcprojtabl20260916.htm)
- Commonwealth Fund/GWU, [How Medicaid and SNAP cutbacks could trigger job losses in states](https://www.commonwealthfund.org/publications/issue-briefs/2025/jun/how-medicaid-snap-cutbacks-one-big-beautiful-bill-trigger-job-losses-states)
- CBO, [Estimated effects of P.L. 119-21 on SNAP participation](https://cbo.gov/system/files/2025-08/61367-SNAP.pdf)
- CBPP, [state estimates of adults newly subject to SNAP work rules](https://www.cbpp.org/sites/default/files/4-30-25fa.pdf)
- AEI, [Understanding the recent declines in SNAP participation](https://cosm.aei.org/understanding-the-recent-declines-in-snap-participation/)
- CMS, [Medicaid community engagement interim final rule](https://www.cms.gov/newsroom/fact-sheets/medicaid-community-engagement-requirement-certain-individuals-interim-final-rule-comment-period-cms)
- Georgetown CCF, [six-month renewals guidance](https://ccf.georgetown.edu/2026/03/06/cms-releases-guidance-on-6-month-medicaid-renewals-for-expansion-adults/) and [immigrant eligibility restrictions](https://ccf.georgetown.edu/2025/10/01/new-immigrant-eligibility-restrictions-coming-to-federally-funded-health-coverage/)
- KFF State Health Facts: [Medicaid and CHIP enrollment](https://www.kff.org/medicaid/state-indicator/medicaid-and-chip-monthly-enrollment/), [Medicaid enrollees by group](https://www.kff.org/medicaid/state-indicator/distribution-of-medicaid-enrollees-by-enrollment-group/), [dual-eligible individuals](https://www.kff.org/state-health-policy-data/state-indicator/number-of-dual-eligible-individuals/), [Medicare beneficiaries](https://www.kff.org/medicare/state-indicator/total-medicare-beneficiaries/), [SNAP participants](https://www.kff.org/state-health-policy-data/state-indicator/avg-monthly-participation/)
- AHRQ HCUP, [ER visit costs, 2021](https://hcup-us.ahrq.gov/reports/statbriefs/sb311-ED-visit-costs-2021.pdf) and [uninsured hospital stays](https://www.hcup-us.ahrq.gov/reports/statbriefs/sb182-Medicaid-Uninsured-Hospitalizations-2012.jsp)
- KFF Health News, [Arkansas Medicaid work requirement study](https://kffhealthnews.org/news/study-arkansas-medicaid-work-requirements-hit-those-already-employed/)
- U.S. Census Bureau, [state population estimates, July 2025](https://www.census.gov/data/tables/time-series/demo/popest/2020s-state-total.html)
- PublicaMundi, [MappingAPI US states GeoJSON](https://github.com/PublicaMundi/MappingAPI)

The page's Sources section lists every link used.
