"""Generate the repeatable 19-company DCF V1/V2 validation report."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

from dashboard_utils import statement_value, valuation_share_count_details
from dcf_model import (
    estimate_defaults,
    estimate_equity_dcf_defaults,
    run_dcf,
    run_equity_dcf,
)
from dcf_v2 import build_v2_defaults, run_v2_case


COMPANIES = {
    "Apple": "AAPL", "Palantir": "PLTR", "Nvidia": "NVDA", "Tesla": "TSLA",
    "Microsoft": "MSFT", "Amazon": "AMZN", "Alphabet / Google": "GOOGL",
    "Meta": "META", "AMD": "AMD", "Broadcom": "AVGO", "JPMorgan Chase": "JPM",
    "Goldman Sachs": "GS", "Visa": "V", "Berkshire Hathaway": "BRK-B",
    "Lockheed Martin": "LMT", "Rocket Lab": "RKLB", "SoFi": "SOFI",
    "Uber": "UBER", "AST SpaceMobile": "ASTS",
}


def load_statements(ticker: yf.Ticker) -> dict:
    income = getattr(ticker, "income_stmt", None)
    if income is None or income.empty:
        income = ticker.financials
    cash_flow = getattr(ticker, "cashflow", None)
    balance = getattr(ticker, "balance_sheet", None)
    out = {"history": [], "cash": None, "debt": None}
    if income is None or income.empty:
        return out

    for period in list(income.columns)[:4][::-1]:
        revenue = statement_value(income, ["Total Revenue", "Operating Revenue"], period)
        net_income = statement_value(income, ["Net Income", "Net Income Common Stockholders"], period)
        operating_income = statement_value(income, ["Operating Income", "EBIT"], period)
        diluted_average_shares = statement_value(income, ["Diluted Average Shares", "Basic Average Shares"], period)
        book_equity = statement_value(balance, ["Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"], period)
        pretax_income = statement_value(income, ["Pretax Income", "Income Before Tax"], period)
        tax_provision = statement_value(income, ["Tax Provision"], period)
        interest = statement_value(income, ["Interest Expense", "Interest Expense Non Operating"], period)
        operating_cash_flow = statement_value(cash_flow, ["Operating Cash Flow", "Total Cash From Operating Activities"], period)
        capital_expenditure = statement_value(cash_flow, ["Capital Expenditure", "Capital Expenditures"], period)
        reported_fcf = statement_value(cash_flow, ["Free Cash Flow"], period)
        tax_rate = max(0.0, min(0.35, tax_provision / pretax_income)) if pretax_income and pretax_income > 0 and tax_provision is not None else 0.21
        levered_fcf = reported_fcf
        if levered_fcf is None and operating_cash_flow is not None:
            levered_fcf = operating_cash_flow - abs(capital_expenditure or 0.0)
        fcff = levered_fcf + abs(interest or 0.0) * (1.0 - tax_rate) if levered_fcf is not None else None
        if revenue is None and fcff is None and net_income is None:
            continue
        out["history"].append({
            "year": str(period.year if hasattr(period, "year") else period),
            "revenue": revenue,
            "fcff": fcff,
            "net_income": net_income,
            "operating_income": operating_income,
            "operating_cash_flow": operating_cash_flow,
            "capital_expenditure": capital_expenditure,
            "diluted_average_shares": diluted_average_shares,
            "book_equity": book_equity,
            "interest": interest,
            "tax_rate": tax_rate,
        })
    if balance is not None and not balance.empty:
        latest = balance.columns[0]
        out["cash"] = statement_value(balance, ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents", "Cash Financial"], latest)
        out["debt"] = statement_value(balance, ["Total Debt", "Total Non Current Liabilities Net Minority Interest"], latest)
    return out


def v1_base(symbol: str, history: list[dict], info: dict, shares: float, net_debt: float) -> float | None:
    try:
        if symbol in {"JPM", "GS", "SOFI"}:
            usable = [row for row in history if row.get("net_income") is not None and row.get("book_equity") is not None]
            defaults = estimate_equity_dcf_defaults(usable, info)
            return run_equity_dcf(
                base_net_income=float(usable[-1]["net_income"]),
                starting_roe=defaults["starting_roe"],
                year_one_growth=defaults["year_one_growth"],
                final_year_growth=defaults["final_year_growth"],
                target_roe=defaults["target_roe"],
                cost_of_equity=defaults["cost_of_equity"],
                terminal_growth=defaults["terminal_growth"],
                forecast_years=defaults["forecast_years"],
                shares_outstanding=shares,
            )["value_per_share"]
        usable = [row for row in history if row.get("revenue") is not None and row.get("fcff") is not None]
        defaults = estimate_defaults(usable, info)
        return run_dcf(
            base_revenue=float(usable[-1]["revenue"]),
            starting_fcff_margin=defaults["starting_fcff_margin"],
            year_one_growth=defaults["year_one_growth"],
            final_year_growth=defaults["final_year_growth"],
            target_fcff_margin=defaults["target_fcff_margin"],
            wacc=defaults["wacc"],
            terminal_growth=defaults["terminal_growth"],
            forecast_years=defaults["forecast_years"],
            net_debt=net_debt,
            shares_outstanding=shares,
        )["value_per_share"]
    except (IndexError, TypeError, ValueError):
        return None


def pct_difference(value: float | None, market: float | None) -> float | None:
    return value / market - 1.0 if value is not None and market else None


def run_validation() -> pd.DataFrame:
    try:
        risk_free = float(yf.Ticker("^TNX").history(period="5d")["Close"].dropna().iloc[-1]) / 100.0
    except Exception:
        risk_free = 0.0425
    rows = []
    for company, symbol in COMPANIES.items():
        print(f"Validating {symbol}...", flush=True)
        ticker = yf.Ticker(symbol)
        warnings = []
        try:
            info = dict(ticker.info or {})
            statements = load_statements(ticker)
            history = statements["history"]
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")
            share_details = valuation_share_count_details(info)
            shares = share_details["value"]
            if not shares:
                raise ValueError("Aggregate share count unavailable.")
            cash = info.get("totalCash")
            debt = info.get("totalDebt")
            cash = float(cash if cash is not None else statements["cash"] or 0.0)
            debt = float(debt if debt is not None else statements["debt"] or 0.0)
            net_debt = debt - cash
            model_info = {**info, "_risk_free_rate": risk_free}
            v1_value = v1_base(symbol, history, model_info, float(shares), net_debt)
            defaults = build_v2_defaults(symbol, history, model_info, float(shares), net_debt)
            warnings.extend(defaults.get("warnings", []))
            v2_value = None
            terminal_share = None
            scenario_order = None
            bridge_check = None
            requires_review = False
            if defaults.get("suitable"):
                try:
                    cases = {name: run_v2_case(defaults, name)[0] for name in ("Bear", "Base", "Bull")}
                    result = cases["Base"]
                    v2_value = result["value_per_share"]
                    terminal_share = result["terminal_value_share"]
                    scenario_order = cases["Bear"]["value_per_share"] < v2_value < cases["Bull"]["value_per_share"]
                    if defaults["framework"] == "Financial institution / FCFE":
                        bridge_check = abs(result["enterprise_value"] - result["equity_value"]) < max(1.0, abs(result["equity_value"]) * 1e-9)
                    else:
                        bridge_check = abs((result["enterprise_value"] - net_debt) - result["equity_value"]) < max(1.0, abs(result["equity_value"]) * 1e-9)
                    if terminal_share is not None and terminal_share > 0.85:
                        warnings.append(f"Terminal value is {terminal_share:.1%} of enterprise/equity value.")
                        requires_review = True
                    if not scenario_order:
                        warnings.append("Bear/Base/Bull valuation order failed.")
                        requires_review = True
                    if not bridge_check:
                        warnings.append("Enterprise-to-equity bridge failed.")
                        requires_review = True
                except ValueError as exc:
                    warnings.append(str(exc))
                    requires_review = True
            latest_diluted = next((row.get("diluted_average_shares") for row in reversed(history) if row.get("diluted_average_shares")), None)
            share_gap = float(shares) / latest_diluted - 1.0 if latest_diluted else None
            if share_gap is not None and abs(share_gap) > 0.05:
                warnings.append(f"Current aggregate shares differ from latest annual diluted weighted-average shares by {share_gap:+.1%}.")
                requires_review = requires_review or abs(share_gap) > 0.20
            if not defaults.get("suitable"):
                status = "Not suitable"
            elif v2_value is None or not scenario_order or not bridge_check or requires_review:
                status = "Review"
            else:
                status = "Pass with warning" if warnings else "Pass"
            rows.append({
                "Company": company,
                "Ticker": symbol,
                "Primary Valuation Framework": defaults["framework"],
                "Modifiers": "; ".join(defaults["modifiers"]),
                "Forecast Horizon": defaults.get("horizon"),
                "WACC": defaults.get("wacc"),
                "Applied Discount Rate": defaults.get("cost_of_equity") if defaults["framework"] == "Financial institution / FCFE" else defaults.get("wacc"),
                "Year 1 Growth": defaults.get("year_one_growth"),
                "Intermediate Growth": defaults.get("intermediate_growth"),
                "Mature Growth": defaults.get("mature_growth"),
                "Starting FCFF Margin": defaults.get("starting_fcff_margin"),
                "Mature FCFF Margin": defaults.get("mature_fcff_margin"),
                "V1 Base DCF": v1_value,
                "V2 Base DCF": v2_value,
                "Market Price": current_price,
                "V1 Difference %": pct_difference(v1_value, current_price),
                "V2 Difference %": pct_difference(v2_value, current_price),
                "Terminal Value Share": terminal_share,
                "Share Measure": share_details["source"],
                "Status": status,
                "Warnings": " | ".join(dict.fromkeys(warnings)) or "None",
            })
        except Exception as exc:
            rows.append({"Company": company, "Ticker": symbol, "Status": "Data error", "Warnings": str(exc)})
    return pd.DataFrame(rows)


def write_reports(frame: pd.DataFrame) -> None:
    root = Path(__file__).resolve().parent
    frame.to_csv(root / "DCF_V2_VALIDATION.csv", index=False)
    display = frame.copy()
    money_columns = ["V1 Base DCF", "V2 Base DCF", "Market Price"]
    percent_columns = ["WACC", "Applied Discount Rate", "Year 1 Growth", "Intermediate Growth", "Mature Growth", "Starting FCFF Margin", "Mature FCFF Margin", "V1 Difference %", "V2 Difference %", "Terminal Value Share"]
    for column in money_columns:
        if column in display:
            display[column] = display[column].map(lambda value: "—" if pd.isna(value) else f"${value:,.2f}")
    for column in percent_columns:
        if column in display:
            display[column] = display[column].map(lambda value: "—" if pd.isna(value) else f"{value:.1%}")
    summary_columns = ["Ticker", "Primary Valuation Framework", "Forecast Horizon", "WACC", "Year 1 Growth", "Mature Growth", "Starting FCFF Margin", "Mature FCFF Margin", "V1 Base DCF", "V2 Base DCF", "Market Price", "V2 Difference %", "Status"]
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    table_frame = display[summary_columns].fillna("—")
    header = "| " + " | ".join(summary_columns) + " |"
    divider = "| " + " | ".join("---" for _ in summary_columns) + " |"
    table_rows = [
        "| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |"
        for row in table_frame.itertuples(index=False, name=None)
    ]
    text = [
        "# DCF V2 validation report",
        "",
        f"Generated {generated} from the same Yahoo Finance statement fields and valuation functions used by the dashboard.",
        "",
        "V2 is the public default. V1 remains a frozen legacy baseline. A market-price difference is an output, not a calibration target.",
        "",
        header,
        divider,
        *table_rows,
        "",
        "## Warnings and model limitations",
        "",
    ]
    for _, row in display.iterrows():
        text.append(f"- **{row['Ticker']} — {row['Status']}:** {row['Warnings']}")
    (root / "DCF_V2_VALIDATION.md").write_text("\n".join(text) + "\n", encoding="utf-8")


if __name__ == "__main__":
    report = run_validation()
    write_reports(report)
    print(report[["Ticker", "V1 Base DCF", "V2 Base DCF", "Market Price", "Status"]].to_string(index=False))
