# Model Card — Delhi DISCOM Probabilistic Load Forecaster

## Model Overview
- **Task:** Multi-horizon probabilistic load forecasting (P10/P50/P90) + peak-event classification
- **Target Grid:** Delhi DISCOM (2,000 MW winter → 8,300 MW summer swing)
- **Horizons:** 24-hour (day-ahead) and 168-hour (week-ahead)

## Training Data Assumptions
- **Source:** Delhi SLDC hourly load data + IMD weather data (temperature, humidity)
- **Date Range:** 2021–2023 (3 years recommended minimum for seasonal coverage)
- **Frequency:** Hourly (8,760 rows/year)
- **Known gaps:** DST transitions (IST has no DST — handled via `tz_localize`)

## Thermal Inertia Constraints
- CDH calculated above 24°C comfort baseline
- Thermal lag modeled as 24h/48h/72h rolling mean temperature
- Building heat absorption is especially important during multi-day heatwaves (45°C+)
- **Failure mode:** Model underestimates peak load during first day of sudden temperature spike (lag features haven't captured event yet)

## Festival Calendar Limitations
- Diwali dates must be manually updated each year (varies by Hindu calendar)
- Model has not been tested on newly introduced government holidays
- Ramadan fasting period affects evening load profile (less AC in residential, more mosque lighting)

## Known Failure Modes
1. **Heatwave Day 1:** Rolling thermal inertia lags behind — P90 may underestimate peak by ~300 MW
2. **New Holidays:** Unlabeled holidays treated as regular days → load overestimation
3. **Extreme Events:** Grid restoration after major outage creates anomalous load ramp that confuses lag features
4. **Week-Ahead (168h):** PICP degrades from ~80% to ~65% at 7-day horizon during monsoon breaks
5. **COVID Lockdown Generalization:** Lockdown features were added manually — future lockdown-like events won't be flagged automatically

## Evaluation Protocol
- **Method:** Rolling-origin walk-forward cross-validation
- **Windows:** 52 (one per week of test data)
- **Leakage prevention:** Strictly chronological — no future data visible during training

## Fairness & Bias Notes
- Festival flags encode Hindu, Muslim, and Christian holidays
- Lower-income residential zones have different temperature sensitivity profiles not captured in aggregate DISCOM data
- Model trained on aggregate Delhi DISCOM data — sub-zone accuracy not guaranteed

## Domain Write-Up: Why Peak Complexity Matters
Delhi's summer load ramps from ~4,000 MW at 6 AM to ~8,300 MW by 2 PM — a 4,300 MW swing in 8 hours. The evening peak (7–11 PM) is driven by residential AC, lighting, and commercial cooling. Missing the peak timing by even 2 hours results in emergency DSM grid purchases at 3.5× tariff. The P90 buffer strategy ensures the DISCOM never under-procures during these critical windows.

---
*Authors: Varun Kumar, Akshitha, Member 3 · AMC Engineering College · CodeSpark 2026*
