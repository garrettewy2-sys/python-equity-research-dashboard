# DCF validation record

Validation date: 2026-09-03  
Coverage: the dashboard's 19-company research universe

## Result

The model is not uniformly producing low values because of a single arithmetic or
unit-conversion error. In the validation snapshot, 14 of 19 default Base cases were
below market and the median price-to-DCF gap was approximately -66%. Five Base cases
were above market: JPMorgan Chase, Meta, Berkshire Hathaway, Lockheed Martin and Uber.

That pattern is a warning about default assumptions, not evidence that the market is
wrong. The median discount rate was approximately 10.5%, and the median share of value
coming from the terminal value was approximately 76%. Growth companies were especially
sensitive to high beta/WACC, the five-year fade period and normalized FCFF margins.
Bank equity DCFs were particularly terminal-value dependent.

## Checks performed

- Confirmed the 10-year Treasury proxy is converted from percentage points to a decimal.
- Confirmed FCFF and enterprise-value inputs use consistent currency units.
- Confirmed terminal value uses the Gordon Growth formula and is discounted to present.
- Confirmed net debt is debt less cash and is subtracted from enterprise value.
- Confirmed the bank path uses an equity DCF rather than treating deposits as industrial debt.
- Identified a share-count problem: `sharesOutstanding` can represent only one listed
  share class while `impliedSharesOutstanding` is aggregate. Per-share valuation now
  prefers aggregate implied shares, then market cap divided by price, then reported
  shares outstanding. Unit tests cover that selection order.

## Interpretation

The remaining low valuations primarily reflect intentionally conservative, generic
defaults applied across very different businesses. They should be treated as editable
starting points, not calibrated price targets. The application therefore shows Bear,
Base and Bull values together, exposes WACC construction, displays the enterprise-to-
equity bridge, and avoids categorical labels such as “severely overvalued.”

## Method references

- CFA Institute, FCFF and FCFE formula reference:
  https://www.cfainstitute.org/sites/default/files/-/media/documents/support/programs/cfa/cfa_program_level_ii_financial_ratio_list.pdf
- Aswath Damodaran, stable-growth and terminal-value guidance:
  https://pages.stern.nyu.edu/~adamodar/New_Home_Page/AppldCF/derivn/ch12deriv.html
