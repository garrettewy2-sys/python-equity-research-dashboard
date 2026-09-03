# DCF V2 validation report

Generated 2026-09-03 19:23 UTC from the same Yahoo Finance statement fields and valuation functions used by the dashboard.

V1 remains the public baseline. V2 is a separately labeled comparison model. A market-price difference is an output, not a calibration target.

| Ticker | Primary Valuation Framework | Forecast Horizon | WACC | Year 1 Growth | Mature Growth | Starting FCFF Margin | Mature FCFF Margin | V1 Base DCF | V2 Base DCF | Market Price | V2 Difference % | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AAPL | Standard mature-company DCF | 6.0 | 9.6% | 2.0% | 2.5% | 23.7% | 25.9% | $109.92 | $103.21 | $327.49 | -68.5% | Pass with warning |
| PLTR | High-growth profitable DCF | 8.0 | 11.8% | 28.8% | 3.0% | 46.9% | 40.2% | $20.15 | $23.18 | $183.97 | -87.4% | Pass with warning |
| NVDA | High-growth profitable DCF | 8.0 | 13.7% | 35.0% | 3.0% | 44.9% | 44.8% | $75.24 | $97.89 | $229.55 | -57.4% | Pass with warning |
| TSLA | High-growth profitable DCF | 10.0 | 12.9% | 0.9% | 2.5% | 6.8% | 6.2% | $18.68 | $22.02 | $380.82 | -94.2% | Pass with warning |
| MSFT | Standard mature-company DCF | 7.0 | 9.5% | 15.7% | 2.5% | 20.9% | 24.9% | $246.77 | $229.28 | $511.48 | -55.2% | Pass |
| AMZN | High-growth profitable DCF | 8.0 | 10.5% | 11.8% | 2.5% | 1.3% | 6.0% | $44.11 | $44.73 | $258.56 | -82.7% | Pass with warning |
| GOOGL | Standard mature-company DCF | 7.0 | 10.1% | 13.9% | 2.5% | 18.3% | 20.0% | $139.69 | $132.74 | $342.97 | -61.3% | Pass with warning |
| META | Standard mature-company DCF | 7.0 | 9.8% | 21.9% | 2.5% | 23.4% | 26.2% | $641.97 | $497.38 | $613.14 | -18.9% | Pass with warning |
| AMD | High-growth profitable DCF | 8.0 | 13.7% | 13.7% | 3.0% | 19.8% | 14.9% | $35.58 | $49.82 | $456.63 | -89.1% | Pass with warning |
| AVGO | Standard mature-company DCF | 7.0 | 11.1% | 23.9% | 2.5% | 47.2% | 46.0% | $101.23 | $126.00 | $357.68 | -64.8% | Pass |
| JPM | Financial institution / FCFE | 5.0 | 7.2% | 18.0% | 2.5% | — | — | $367.35 | $335.52 | $362.29 | -7.4% | Review |
| GS | Financial institution / FCFE | 5.0 | 7.0% | 20.3% | 2.5% | — | — | $758.19 | $696.50 | $1,036.16 | -32.8% | Review |
| V | Standard mature-company DCF | 6.0 | 8.0% | 11.3% | 2.5% | 55.2% | 57.2% | $186.13 | $278.29 | $379.18 | -26.6% | Pass with warning |
| BRK-B | Special-case valuation | — | — | — | — | — | — | $384.86 | — | $507.62 | — | Not suitable |
| LMT | Standard mature-company DCF | 5.0 | 6.7% | 5.1% | 2.0% | 10.5% | 10.3% | $829.55 | $717.85 | $531.35 | 35.1% | Pass with warning |
| RKLB | Pre-profit / emerging-company DCF | 12.0 | 13.7% | 38.0% | 3.0% | — | — | $3.63 | $1.46 | $63.41 | -97.7% | Review |
| SOFI | Financial institution / FCFE | 8.0 | 13.4% | -3.5% | 2.5% | — | — | $2.10 | $2.21 | $18.63 | -88.2% | Pass with warning |
| UBER | High-growth profitable DCF | 8.0 | 9.3% | 18.0% | 2.5% | 19.6% | 16.1% | $101.84 | $98.30 | $75.65 | 29.9% | Pass |
| ASTS | Pre-profit / emerging-company DCF | 15.0 | 12.4% | 50.0% | 3.0% | — | — | $-1.72 | — | $61.98 | — | Review |

## Warnings and model limitations

- **AAPL — Pass with warning:** Interest expense unavailable; a disclosed 5.0% pre-tax debt-cost fallback is used.
- **PLTR — Pass with warning:** Interest expense unavailable; a disclosed 5.0% pre-tax debt-cost fallback is used. | Current aggregate shares differ from latest annual diluted weighted-average shares by -6.3%.
- **NVDA — Pass with warning:** Raw beta of 2.21 is outside the 0.50–2.00 economic guardrail; 2.00 is applied to cost of equity. | Raw interest/debt cost of 0.7% is outside the 2%–12% economic guardrail; 2.0% is applied.
- **TSLA — Pass with warning:** Current aggregate shares differ from latest annual diluted weighted-average shares by +12.0%.
- **MSFT — Pass:** None
- **AMZN — Pass with warning:** Raw interest/debt cost of 0.9% is outside the 2%–12% economic guardrail; 2.0% is applied.
- **GOOGL — Pass with warning:** Raw interest/debt cost of 0.6% is outside the 2%–12% economic guardrail; 2.0% is applied.
- **META — Pass with warning:** Raw interest/debt cost of 1.0% is outside the 2%–12% economic guardrail; 2.0% is applied.
- **AMD — Pass with warning:** Raw beta of 2.49 is outside the 0.50–2.00 economic guardrail; 2.00 is applied to cost of equity.
- **AVGO — Pass:** None
- **JPM — Review:** Terminal value is 86.5% of enterprise/equity value.
- **GS — Review:** Terminal value is 87.3% of enterprise/equity value. | Current aggregate shares differ from latest annual diluted weighted-average shares by -8.3%.
- **V — Pass with warning:** Current aggregate shares differ from latest annual diluted weighted-average shares by -14.9%.
- **BRK-B — Not suitable:** A consolidated DCF is not an appropriate V2 default. Berkshire requires a sum-of-the-parts or adjusted-NAV framework.
- **LMT — Pass with warning:** Raw beta of 0.11 is outside the 0.50–2.00 economic guardrail; 0.50 is applied to cost of equity.
- **RKLB — Review:** Raw beta of 2.63 is outside the 0.50–2.00 economic guardrail; 2.00 is applied to cost of equity. | Raw interest/debt cost of 19.8% is outside the 2%–12% economic guardrail; 12.0% is applied. | Emerging-company output is highly speculative and depends on explicit scale, margin and reinvestment assumptions. | Current aggregate shares differ from latest annual diluted weighted-average shares by +20.5%.
- **SOFI — Pass with warning:** Raw beta of 2.20 is outside the 0.50–2.00 economic guardrail; 2.00 is applied to cost of equity. | Raw interest/debt cost of 33.9% is outside the 2%–12% economic guardrail; 12.0% is applied.
- **UBER — Pass:** None
- **ASTS — Review:** Raw beta of 2.75 is outside the 0.50–2.00 economic guardrail; 2.00 is applied to cost of equity. | Raw interest/debt cost of 1.2% is outside the 2%–12% economic guardrail; 2.0% is applied. | Emerging-company output is highly speculative and depends on explicit scale, margin and reinvestment assumptions. | The explicit forecast does not support a positive equity value; no per-share estimate is presented. | Current aggregate shares differ from latest annual diluted weighted-average shares by +52.0%.
