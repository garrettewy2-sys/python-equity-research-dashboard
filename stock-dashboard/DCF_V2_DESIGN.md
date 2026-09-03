# DCF V2 design proposal

Status: **Implemented, validated and promoted to public default**
Baseline: DCF V1 remains unchanged and available as a legacy comparison.

Validation output: `DCF_V2_VALIDATION.md` and `DCF_V2_VALIDATION.csv`.

## Objective and guardrails

DCF V2 should improve financial appropriateness, internal consistency and
transparency. It must not optimize assumptions to reproduce the current market
price. Every displayed input must be traceable to reported data, a documented
calculation or an explicitly editable analyst assumption. When the available data
cannot support a defensible path to mature cash flow, the model should say so rather
than return a falsely precise per-share value.

## Proposed primary frameworks

1. **Standard mature-company DCF** — profitable, established non-financial companies
   whose cash-flow economics can reasonably converge over about five to seven years.
2. **High-growth profitable DCF** — positive cash-generating companies that require a
   longer explicit transition before mature growth and margins are credible.
3. **Pre-profit / emerging-company DCF** — companies that need an explicit operating-
   scale, profitability and reinvestment path before terminal value is permitted.
4. **Financial institution / FCFE** — banks and lenders valued directly on cash flow
   to equity because deposits and borrowings are operating inputs.
5. **Special-case valuation** — businesses for which a consolidated DCF is structurally
   weak, such as a multi-industry insurance conglomerate. V2 should prefer an
   appropriate alternative such as sum-of-the-parts or adjusted net asset value.

Modifiers describe economics without replacing the primary framework. Proposed
modifiers include cyclical, conglomerate, capital intensive, high growth, asset light,
credit sensitive, advertising sensitive and regulated/government exposed.

## Proposed classification of the 19-security universe

| Company | Primary framework | Modifiers | Initial explicit horizon guideline |
|---|---|---|---|
| Apple | Standard mature-company DCF | Consumer platform; hardware/services mix; cash generative | 6 years |
| Palantir | High-growth profitable DCF | High growth; asset light; government exposure | 8 years |
| Nvidia | High-growth profitable DCF | High growth; cyclical; fabless semiconductor | 8 years |
| Tesla | High-growth profitable DCF | Capital intensive; cyclical; margin uncertainty | 10 years |
| Microsoft | Standard mature-company DCF | Asset light; recurring revenue; high growth modifier | 7 years |
| Amazon | High-growth profitable DCF | Capital intensive; mixed-margin segments | 8 years |
| Alphabet / Google | Standard mature-company DCF | Asset light; advertising sensitive; high growth modifier | 7 years |
| Meta | Standard mature-company DCF | Asset light; advertising sensitive; high reinvestment | 7 years |
| AMD | High-growth profitable DCF | Cyclical; fabless semiconductor; high growth | 8 years |
| Broadcom | Standard mature-company DCF | Cyclical; software/semiconductor mix; leveraged integration | 7 years |
| JPMorgan Chase | Financial institution / FCFE | Credit sensitive; cyclical; regulated | 5 years |
| Goldman Sachs | Financial institution / FCFE | Capital-markets sensitive; cyclical; regulated | 5 years |
| Visa | Standard mature-company DCF | Asset light; network economics; regulated | 6 years |
| Berkshire Hathaway | Special-case valuation | Conglomerate; insurance; capital intensive | N/A for V2 default; retain 5-year V1 baseline |
| Lockheed Martin | Standard mature-company DCF | Capital intensive; government exposed; backlog driven | 5 years |
| Rocket Lab | Pre-profit / emerging-company DCF | Capital intensive; high growth; execution sensitive | 12 years, only if evidence supports maturity |
| SoFi | Financial institution / FCFE | High growth; credit sensitive; regulated | 8 years |
| Uber | High-growth profitable DCF | Asset light; high growth; regulatory exposure | 8 years |
| AST SpaceMobile | Pre-profit / emerging-company DCF | Capital intensive; pre-scale; financing and execution risk | Up to 15 years, or unsuitable if evidence is insufficient |

These horizons are starting recommendations, not category-driven constants. The
implementation should shorten or extend the explicit period only when the issuer’s
reported growth, profitability and reinvestment path justifies it. The user must be
able to edit the final horizon.

## Forecast-horizon decision logic

The model should determine whether the company has reached a credible steady state,
not merely count a fixed number of years. A mature profitable company can normally
use about five years when growth and margins are already stable. A profitable growth
company should use seven to ten years when excess growth or margin transition remains
material. An emerging company may need ten or more years, but a longer spreadsheet is
not evidence: if positive mature cash flow cannot be supported by reported economics
and explicit assumptions, V2 should decline to calculate a terminal value.

## Revenue-growth fade

V2 should expose three anchors:

- **Year 1 growth** — grounded in recent reported growth, with the source period shown.
- **Intermediate growth** — an editable midpoint rate at a displayed midpoint year.
- **Mature growth** — the rate reached at the end of the explicit forecast.

Growth should move piecewise-linearly from Year 1 to the intermediate anchor and then
to mature growth. Each forecast row will display the resulting rate. This avoids a
single abrupt fade and makes the transition auditable. Defaults should consider the
median and dispersion of available annual growth; they should not import unavailable
consensus estimates or infer growth from the market price.

## FCFF-margin methodology

For mature and profitable companies, V2 should anchor the starting FCFF margin to the
latest reported value and show the three-year median and observed range. The mature
margin guardrail should be issuer-specific and combine:

- the company’s own reported FCFF-margin history;
- current operating margin and cash conversion;
- asset-light versus capital-intensive modifier;
- demonstrated reinvestment requirements; and
- segment or comparable economics only when those data are actually available.

There should be no universal 35% ceiling. Instead, V2 should warn when an assumption
is materially beyond the company’s historical range, implies cash conversion above
operating economics, or conflicts with a capital-intensive modifier. A warning should
not silently clamp the user’s input.

For pre-profit companies, a direct FCFF-margin fade is inadequate. The proposed path
is revenue growth → operating-margin development → reinvestment → FCFF. Reinvestment
should be tied to an explicit sales-to-capital or incremental-revenue assumption when
the required balance-sheet history is available. Terminal value is disabled until the
forecast reaches positive, economically plausible mature cash flow.

## WACC methodology and presentation

V2 should retain market-value weights and display every component:

- Risk-Free Rate — latest valid 10-year Treasury proxy (`^TNX`), converted to decimal.
- Beta — current Yahoo Finance beta, with a warning when missing or unstable.
- Equity Risk Premium — explicit model assumption, initially 4.5% to preserve V1.
- Cost of Equity — risk-free rate + beta × equity risk premium.
- Pre-Tax Cost of Debt — reported interest expense divided by debt, with the source
  period and any guardrail disclosed.
- Tax Rate — reported effective rate when meaningful; normalized fallback disclosed.
- Debt Weight and Equity Weight — debt and market capitalization divided by total
  market-value capital.
- Final WACC — weighted cost of equity plus after-tax weighted cost of debt.

Tooltips should distinguish reported fields, calculated fields and analyst assumptions.
WACC must never be lowered solely because intrinsic value is below market price.

## Share-count methodology

V2 should show the exact numerator and date used for per-share conversion. The proposed
validation hierarchy is:

1. current aggregate `impliedSharesOutstanding`, when present;
2. reconciliation against market capitalization divided by current price;
3. most recent diluted weighted-average shares from the income statement as a
   historical cross-check; and
4. `sharesOutstanding` only when aggregate alternatives are unavailable, with a
   warning for dual-class issuers.

Large differences between the aggregate current estimate and diluted weighted-average
shares should be flagged, not averaged away. Dual-class companies must use aggregate
economic shares rather than the listed class alone. The public model should label the
chosen measure, source and date beside the per-share bridge.

## Financial-institution treatment

JPMorgan, Goldman Sachs and SoFi should remain on FCFE/equity models. V2 should forecast
earnings, ROE, required retention and distributable cash flow to equity, discounted at
cost of equity. It should not subtract conventional net debt. The retained-capital
relationship, cost-of-equity inputs and terminal payout calculation must remain visible.

## Pre-profit / emerging-company treatment

Rocket Lab and AST SpaceMobile should receive an evidence gate before valuation. V2
should require enough reported history and explicit assumptions to show operating
scale, margin inflection, reinvestment and a positive mature cash-flow state. If that
gate fails, the output should be “DCF unsuitable / highly speculative with current
data,” accompanied by the missing evidence. A wide scenario range alone does not fix
an unsupported terminal value.

## Detailed issuer examples

### Apple

Apple fits a standard mature-company DCF, but its hardware/services mix argues for a
six-year rather than mechanical five-year transition. Year 1 should reflect recent
reported growth, the midpoint should make the services and installed-base transition
explicit, and the mature rate should be reached gradually. Its mature FCFF margin
should be judged against Apple’s own cash conversion and operating margin—not a global
ceiling. Aggregate shares are essential because per-share accuracy matters even when
the share structure is simpler than Alphabet’s.

### JPMorgan Chase

JPMorgan requires the financial-institution/FCFE framework. Deposits and wholesale
funding are operating resources, so enterprise value minus net debt is not meaningful
in the industrial-company sense. The explicit period can remain near five years because
the bank is mature, while earnings growth, normalized ROE, required retention, payout
and cost of equity drive value. Terminal-value dependence should be prominently warned.

### Rocket Lab

Rocket Lab requires a pre-profit/emerging framework and roughly a 12-year guideline
only if the data support it. The forecast must show revenue scale, operating-margin
inflection and the capital needed to produce incremental revenue. A positive target
FCFF margin cannot simply be imposed on today’s negative cash flow. If reported history
and explicit reinvestment assumptions do not support a plausible positive mature state,
V2 should withhold a per-share DCF rather than manufacture precision.

### Berkshire Hathaway

Berkshire should be a special case. A single consolidated revenue/FCFF margin obscures
insurance float, the investment portfolio, cash, controlled operating businesses,
BNSF and Berkshire Hathaway Energy. V2 should prefer a sum-of-the-parts or adjusted-NAV
framework. The existing consolidated DCF remains available only as a V1 validation
baseline with a strong limitation notice; it should not become Berkshire’s V2 default.

## Reverse DCF proposal

Reverse DCF should solve one selected variable at a time while holding all other Base
inputs constant: Year 1 growth, mature FCFF margin, WACC or terminal growth. The UI
should present several feasible one-variable reconciliations when mathematical solutions
exist and explicitly say that combinations are also possible. It must display:

> Reverse DCF does not predict future performance. It shows the assumptions that would
> make the current market price consistent with this valuation framework.

No single solved input should be described as “what the market believes.”

## C2 validation plan after approval

V1 was frozen as a baseline. V2 was implemented behind an explicit comparison
view, tested, and then promoted to public default. The 19-security report includes
company, framework, modifiers, horizon, WACC, Year 1 growth, mature growth, starting and
mature FCFF margins, Base value, market price and difference percentage for both V1 and
V2. Success will be judged by financial appropriateness, consistency, transparency and
removal of arbitrary universal assumptions—not by proximity to market prices.
