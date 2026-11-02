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
