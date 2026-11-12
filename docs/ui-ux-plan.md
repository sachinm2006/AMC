# Peak-Aware Load Forecasting Copilot — UI/UX Plan

## 1. Product experience goal

Help a Delhi power-system operator move from **“What might demand look like?”** to **“What should I schedule, and what is the risk if I am wrong?”** The experience should make forecast uncertainty, peak timing, and the cost assumptions behind a recommendation visible at a glance.

### Primary users

- **Load forecaster / control-room operator:** needs to spot a likely peak early, understand its timing and severity, and check whether the forecast is trustworthy.
- **Power procurement / risk analyst:** needs to compare schedule choices and understand the modeled cost of shortfall versus surplus.
- **Reviewer / judge:** needs to understand the problem, see a working forecast workflow, and inspect how results were evaluated.

### Product promise

**See the peak. Understand the range. Plan the response.**

Position this as decision support. Do not claim that the system automatically procures energy, prevents blackouts, guarantees savings, or uses an officially validated penalty unless those capabilities and assumptions are confirmed.

## 2. Brand and visual direction

Use the two shared references as one earthy, confident system: emerald and champagne are the main pairing; desert sand and olive drab soften and extend it.

### Palette tokens

| Token | Color | Use |
|---|---|---|
| Emerald Ink | `#064E3B` | Brand anchor, primary buttons, navigation, strong chart series |
| Champagne | `#F8E7C9` | Warm page canvas, selected states, hero fields |
| Olive Drab | `#5B5E3C` | Secondary labels, muted controls, tertiary chart series |
| Desert Sand | `#D8C5BC` | Supporting cards, dividers, charts and quiet backgrounds; sample from reference and tune in final implementation |
| Paper | `#FFFDF7` | Raised content surfaces and dashboard panels |
| Ink | `#1E2924` | Body copy and high-contrast text on light surfaces |
| Peak Alert | `#B84F38` | Critical peak and risk states only, always paired with an icon or text label |
| Advisory | `#9A6B1B` | Caution states and approaching thresholds, paired with a label |

### Proportion and contrast

Use the reference’s 60/30/10 balance as a guide: mostly light warm surfaces, a strong emerald frame, and restrained olive/sand accents. Reserve red-orange for genuinely critical events. Keep alert colors semantically consistent so an attractive palette never obscures risk.

Use champagne or paper text on emerald; use ink or emerald text on champagne, sand, and paper. Avoid small olive text on sand. Every chart series must have a legend, a distinct line style or marker, and a textual value so color is never the only differentiator.

### Typography and shape

- Use a clear sans-serif for operational data and controls; use a restrained editorial display face for the landing-page headline only.
- Prefer short labels, tabular numerals for MW and ₹ values, generous spacing, and sentence case.
- Use softly rounded surfaces, thin borders, and subtle shadows. Avoid glass effects, neon gradients, and decorative dashboard clutter.
- Favor warm, calm, high-trust visual character over a generic blue enterprise dashboard.

## 3. Information architecture

```text
Public landing page
├── Hero and interactive forecast preview
├── Operational problem and product workflow
├── Forecast, peak alerts, and procurement scenarios
├── Validation and data provenance
└── Open dashboard / project details

Operator workspace
├── Overview — next 24 hours, peak alert, schedule decision
├── Forecast — hourly 24-hour and 7-day probability bands
├── Peak events — event list, timing, magnitude, likelihood
├── Procurement — scenario controls and cost comparison
└── Model & data — freshness, coverage, backtest and caveats
```

For the first deliverable, build the public landing page and a single responsive operator dashboard. Keep the navigation model compact; the remaining sections can be dashboard panels or tabs until the data and user workflows are validated.

## 4. Landing page plan

### Header

- Product wordmark and “Delhi Load Forecasting” descriptor.
- Links: How it works, Forecasting, Methodology.
- Primary action: **Open dashboard**.
- On small screens, use a single menu button and retain the dashboard action.

### Hero

**Headline:** “See the peak before it arrives.”

**Supporting copy:** “Explore a range of possible Delhi demand outcomes, spot high-risk hours, and compare schedule choices against clearly stated cost assumptions.”

Show a compact forecast illustration with P10–P50–P90 lines, one highlighted peak window, and a small “Illustrative forecast” label. Pair it with two concrete facts only when their source and time period are visible. Avoid unverified savings or a fixed DSM multiplier in marketing copy.

### Story sections

1. **Why the range matters:** point forecast versus uncertainty band, explained in plain language.
2. **From forecast to response:** forecast → peak alert → compare schedules → export a planning memo.
3. **Built for peak-aware planning:** day-ahead and week-ahead horizons, timing, magnitude, and event probability.
4. **Evidence and limitations:** backtest dates, baseline comparisons, coverage, interval width, data source, missing-data treatment, and explicit prototype limitations.
5. **Closing action:** open the dashboard or inspect the methodology.

### Landing-page success criteria

- A new visitor can state what the product does after reading the hero.
- The hero communicates uncertainty, not a single guaranteed number.
- A visible route leads to the working dashboard.
- Every quantitative claim is either sourced or marked as illustrative.

## 5. Operator dashboard plan

### Default desktop composition

```text
┌──────────────────────────────────────────────────────────────────┐
│ Peakwise   Delhi system · Demo data     Updated time   Profile   │
├───────────────┬──────────────────────────────────────────────────┤
│ Overview      │ Good morning / forecast date / 24h | 7d toggle   │
│ Forecast      │                                                  │
│ Peak events   │ [Expected peak] [Peak probability] [Range width] │
│ Procurement   │                                                  │
│ Model & data  │ [Hourly P10/P50/P90 chart + actual + peak band]   │
│               │                                                  │
│               │ [Peak alert detail]       [Schedule decision]    │
│               │                                                  │
│               │ [Cost assumptions / confidence / data quality]   │
└───────────────┴──────────────────────────────────────────────────┘
```

### Top bar and context

- Identify the selected geography and series (Delhi total or a named DISCOM); never imply a feeder-level forecast unless feeder data is actually available.
- Display forecast issue time, target window, timezone, and data freshness.
- Label synthetic, historical, modeled, or live data distinctly.
- Provide a visible demo-data badge whenever displayed values are illustrative.

### Summary cards

1. **Forecast peak:** expected MW and local time, with the selected quantile stated.
2. **Peak likelihood:** probability of exceeding the chosen threshold, plus threshold definition.
3. **Uncertainty:** P10–P90 width in MW and whether recent backtests show nominal coverage.

Avoid success-colored green for a high-risk metric. Use neutral styling for forecast values and explicit advisory/critical labels for risk.

### Forecast chart

- Main view: hourly actuals where available, P50 line, and shaded P10–P90 interval.
- Show peak-hour marker and threshold line; allow hover/focus to read timestamp, quantiles, actual, peak probability, and weather input status.
- Range switch: **Next 24 hours / Next 7 days**. Clearly label reduced certainty at longer horizons.
- Include a compact chart legend, units (MW), local time, and an accessible table or data download alternative.
- Prevent quantile crossing in the displayed series or mark invalid predictions visibly.

### Peak alert panel

Show the next likely event with:

- Expected time window and peak magnitude (P50 with P10/P90 range).
- Probability of crossing the displayed operational threshold.
- Lead time and key drivers available to the model (e.g., forecast temperature, recent load trend, calendar marker).
- A status label such as **Watch**, **Elevated**, or **Critical**, with a short reason.

Do not label top-decile historical demand as a regulatory or operational threshold. Keep learned peak labels separate from operator-configured limits.

### Procurement decision panel

- Let the user select **P50**, **Cost-optimized**, or **Conservative** schedule policy.
- Make under-supply cost, over-supply cost, base tariff, and units editable and visible.
- Compare the selected schedule to the alternatives in MW and ₹ for the target window.
- Show the formula and indicate whether costs are supplied, user-entered, or illustrative.
- Default to **Scenario only** until validated market and contract assumptions exist. Do not call a scenario “recommended” without a clear decision rule.
- Export a short planning memo containing the forecast window, selected policy, schedule, risk range, assumptions, model/data timestamp, and disclaimer.

### Model and data trust panel

Make provenance inspectable without dominating the main screen:

- Source and series, temporal resolution, last successful update, missing intervals, and imputation flags.
- Model version and forecast issue time.
- Walk-forward test period, number of test origins, naive and linear baseline comparison.
- Pinball loss, PICP, interval width, peak recall, and peak timing/magnitude errors.
- Show coverage by horizon, season, and peak/non-peak periods; do not rely on one aggregate PICP value.

## 6. Primary user flow

1. Open the dashboard and confirm geography, forecast issue time, and data status.
2. Review the next-day load range and identify the highlighted peak window.
3. Open the alert to see exceedance probability, threshold, lead time, and available drivers.
4. Compare P50, cost-optimized, and conservative schedule options.
5. Adjust the cost assumptions and see exposure update immediately.
6. Export or share a memo with the chosen scenario and its assumptions.

If input data are stale or incomplete, preserve the last forecast but label its age and affected hours; never display it as current without qualification.

## 7. Responsive behavior

- **Desktop:** persistent compact side navigation; chart and decision panels can sit side by side.
- **Tablet:** collapse side navigation; place chart first, then alert and procurement cards in a two-column grid.
- **Mobile:** single-column reading order: context → peak summary → chart → alert → schedule options → assumptions. Keep chart pan/zoom optional and provide a readable hourly list.
- Sticky controls must not cover chart labels or keyboard focus. Use large touch targets and avoid hover-only explanations.

## 8. Accessibility and content rules

- Meet WCAG AA contrast for text and controls; verify final token pairings rather than relying on palette appearance.
- Support keyboard navigation, visible focus, reduced motion, and screen-reader labels for chart controls.
- Pair color with words, icons, line styles, and values.
- Use consistent units: MW for instantaneous demand, MWh for energy over a period, and ₹ with tariff units stated.
- Expand specialized terms on first use: P10/P50/P90, DSM, and walk-forward backtest.
- Use “forecast,” “scenario,” and “estimated exposure” carefully; distinguish these from measured values and realized settlement charges.

## 9. Prototype data and interaction scope

For the first UI pass, use a clearly marked sample dataset and implement meaningful front-end interactions:

- Landing-page **Open dashboard** action.
- 24-hour / 7-day switch.
- Quantile/series toggles and peak-alert detail.
- Schedule-policy selection and adjustable cost assumptions that recalculate illustrative cost comparisons.
- Expandable model/data provenance and downloadable scenario memo.

The prototype should make no external API calls and should not imply that a live Delhi SLDC integration or validated procurement cost model already exists. Connect the interface to the forecasting pipeline after the data contract and model output schema are confirmed.

## 10. Build sequence

1. Confirm product name, forecast scope (Delhi total vs DISCOM), and which sample values may be shown.
2. Create palette/type/spacing tokens and shared layout components.
3. Build landing page and responsive dashboard shell with illustrative data.
4. Add interactive chart, alert detail, and procurement scenario controls.
5. Review desktop, tablet, and mobile layouts; check keyboard navigation and contrast.
6. Connect backtest/model outputs and source metadata after the frontend schema is agreed.
7. Replace illustrative copy with evidence-backed claims only.

## 11. Open decisions to resolve during implementation

- Product name and whether the app should target Delhi total load, a specific DISCOM, or both.
- Operational peak threshold: fixed configured threshold, rolling threshold, or a separate top-decile event label.
- Source and refresh cadence for historical and forecast inputs, including weather forecasts.
- Applicable shortfall/surplus cost inputs, units, and who may edit or approve them.
- Whether forecast recommendations are informational, require operator approval, or integrate with a scheduling workflow.

