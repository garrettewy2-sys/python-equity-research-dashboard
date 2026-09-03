"""Pure discounted-cash-flow calculations used by the dashboard."""

from __future__ import annotations

from statistics import median


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, float(value)))


def run_dcf(
    *,
    base_revenue: float,
    starting_fcff_margin: float,
    year_one_growth: float,
    final_year_growth: float,
    target_fcff_margin: float,
    wacc: float,
    terminal_growth: float,
    forecast_years: int,
    net_debt: float,
    shares_outstanding: float,
) -> dict:
    """Run a two-stage FCFF DCF and return the valuation and forecast schedule."""
    if base_revenue <= 0:
        raise ValueError("Base revenue must be positive.")
    if shares_outstanding <= 0:
        raise ValueError("Shares outstanding must be positive.")
    if forecast_years < 2:
        raise ValueError("Forecast period must be at least two years.")
    if wacc <= terminal_growth:
        raise ValueError("WACC must be greater than terminal growth.")

    revenue = float(base_revenue)
    schedule = []
    present_value_fcff = 0.0

    for year in range(1, forecast_years + 1):
        growth_weight = (year - 1) / (forecast_years - 1)
        growth = year_one_growth + (final_year_growth - year_one_growth) * growth_weight
        margin_weight = year / forecast_years
        margin = starting_fcff_margin + (
            target_fcff_margin - starting_fcff_margin
        ) * margin_weight
        revenue *= 1.0 + growth
        fcff = revenue * margin
        discount_factor = (1.0 + wacc) ** year
        pv_fcff = fcff / discount_factor
        present_value_fcff += pv_fcff
        schedule.append(
            {
                "year": year,
                "growth": growth,
                "fcff_margin": margin,
                "revenue": revenue,
                "fcff": fcff,
                "pv_fcff": pv_fcff,
            }
        )

    terminal_fcff = schedule[-1]["fcff"] * (1.0 + terminal_growth)
    terminal_value = terminal_fcff / (wacc - terminal_growth)
    present_value_terminal = terminal_value / ((1.0 + wacc) ** forecast_years)
    enterprise_value = present_value_fcff + present_value_terminal
    equity_value = enterprise_value - net_debt
    value_per_share = equity_value / shares_outstanding
    terminal_value_share = (
        present_value_terminal / enterprise_value if enterprise_value else 0.0
    )

    return {
        "schedule": schedule,
        "present_value_fcff": present_value_fcff,
        "terminal_value": terminal_value,
        "present_value_terminal": present_value_terminal,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "value_per_share": value_per_share,
        "terminal_value_share": terminal_value_share,
    }


def estimate_defaults(history: list[dict], info: dict) -> dict:
    """Create transparent starting assumptions from reported annual data."""
    usable_revenue = [
        float(row["revenue"])
        for row in history
        if row.get("revenue") is not None and row["revenue"] > 0
    ]
    growth_rates = [
        current / previous - 1.0
        for previous, current in zip(usable_revenue, usable_revenue[1:])
        if previous > 0
    ]
    recent_growth = median(growth_rates[-3:]) if growth_rates else 0.06
    year_one_growth = clamp(recent_growth, -0.10, 0.35)
    final_year_growth = clamp(
        max(0.035, year_one_growth * 0.55),
        -0.02,
        0.18,
    )

    margins = [
        float(row["fcff"]) / float(row["revenue"])
        for row in history[-3:]
        if row.get("fcff") is not None
        and row.get("revenue") is not None
        and row["revenue"] > 0
    ]
    starting_margin = margins[-1] if margins else 0.08
    normalized_margin = median(margins) if margins else 0.08
    target_margin = (
        clamp(normalized_margin, 0.03, 0.35)
        if normalized_margin > 0
        else 0.08
    )

    beta = clamp(info.get("beta") or 1.0, 0.5, 2.0)
    risk_free_rate = float(info.get("_risk_free_rate") or 0.0425)
    equity_risk_premium = 0.045
    cost_of_equity = risk_free_rate + beta * equity_risk_premium

    market_cap = float(info.get("marketCap") or 0.0)
    debt = float(info.get("totalDebt") or 0.0)
    latest_interest = abs(float(history[-1].get("interest") or 0.0)) if history else 0.0
    tax_rate = float(history[-1].get("tax_rate") or 0.21) if history else 0.21
    cost_of_debt = clamp(latest_interest / debt, 0.02, 0.10) if debt > 0 else 0.05
    capital = market_cap + debt
    if capital > 0:
        wacc = (
            market_cap / capital * cost_of_equity
            + debt / capital * cost_of_debt * (1.0 - tax_rate)
        )
    else:
        wacc = cost_of_equity

    return {
        "starting_fcff_margin": clamp(starting_margin, -0.50, 0.50),
        "year_one_growth": year_one_growth,
        "final_year_growth": final_year_growth,
        "target_fcff_margin": target_margin,
        "wacc": clamp(wacc, 0.06, 0.14),
        "terminal_growth": 0.025,
        "forecast_years": 5,
        "risk_free_rate": risk_free_rate,
        "equity_risk_premium": equity_risk_premium,
        "cost_of_equity": cost_of_equity,
    }


def scenario_assumptions(defaults: dict, scenario: str) -> dict:
    """Apply consistent bear/base/bull spreads to a company's defaults."""
    adjustments = {
        "Bear": (-0.03, -0.015, -0.025, 0.010, -0.005),
        "Base": (0.0, 0.0, 0.0, 0.0, 0.0),
        "Bull": (0.03, 0.015, 0.025, -0.0075, 0.005),
    }
    growth_one, growth_final, margin, wacc, terminal = adjustments[scenario]
    return {
        **defaults,
        "year_one_growth": clamp(defaults["year_one_growth"] + growth_one, -0.30, 0.80),
        "final_year_growth": clamp(defaults["final_year_growth"] + growth_final, -0.10, 0.30),
        "target_fcff_margin": clamp(defaults["target_fcff_margin"] + margin, -0.20, 0.50),
        "wacc": clamp(defaults["wacc"] + wacc, 0.05, 0.20),
        "terminal_growth": clamp(defaults["terminal_growth"] + terminal, 0.0, 0.05),
    }


def run_equity_dcf(
    *,
    base_net_income: float,
    starting_roe: float,
    year_one_growth: float,
    final_year_growth: float,
    target_roe: float,
    cost_of_equity: float,
    terminal_growth: float,
    forecast_years: int,
    shares_outstanding: float,
) -> dict:
    """Discount bank FCFE, using growth/ROE to estimate required retention."""
    if base_net_income <= 0:
        raise ValueError("Positive base net income is required for the bank equity DCF.")
    if shares_outstanding <= 0:
        raise ValueError("Shares outstanding must be positive.")
    if forecast_years < 2:
        raise ValueError("Forecast period must be at least two years.")
    if cost_of_equity <= terminal_growth:
        raise ValueError("Cost of equity must be greater than terminal growth.")

    earnings = float(base_net_income)
    present_value_fcfe = 0.0
    schedule = []
    for year in range(1, forecast_years + 1):
        growth_weight = (year - 1) / (forecast_years - 1)
        growth = year_one_growth + (final_year_growth - year_one_growth) * growth_weight
        roe = starting_roe + (target_roe - starting_roe) * (year / forecast_years)
        earnings *= 1.0 + growth
        retention = clamp(growth / max(roe, 0.01), 0.0, 0.95)
        fcfe = earnings * (1.0 - retention)
        pv_fcfe = fcfe / ((1.0 + cost_of_equity) ** year)
        present_value_fcfe += pv_fcfe
        schedule.append(
            {
                "year": year,
                "growth": growth,
                "roe": roe,
                "earnings": earnings,
                "payout": 1.0 - retention,
                "fcfe": fcfe,
                "pv_fcfe": pv_fcfe,
            }
        )

    terminal_payout = 1.0 - clamp(terminal_growth / max(target_roe, 0.01), 0.0, 0.95)
    terminal_fcfe = schedule[-1]["earnings"] * (1.0 + terminal_growth) * terminal_payout
    terminal_value = terminal_fcfe / (cost_of_equity - terminal_growth)
    present_value_terminal = terminal_value / ((1.0 + cost_of_equity) ** forecast_years)
    equity_value = present_value_fcfe + present_value_terminal
    return {
        "schedule": schedule,
        "present_value_fcfe": present_value_fcfe,
        "present_value_terminal": present_value_terminal,
        "equity_value": equity_value,
        "value_per_share": equity_value / shares_outstanding,
        "terminal_value_share": present_value_terminal / equity_value if equity_value else 0.0,
    }


def estimate_equity_dcf_defaults(history: list[dict], info: dict) -> dict:
    """Estimate bank equity-DCF inputs from net income and common equity history."""
    earnings = [
        float(row["net_income"])
        for row in history
        if row.get("net_income") is not None and row["net_income"] > 0
    ]
    earnings_growth = [
        current / previous - 1.0
        for previous, current in zip(earnings, earnings[1:])
        if previous > 0
    ]
    year_one_growth = clamp(median(earnings_growth[-3:]) if earnings_growth else 0.06, -0.10, 0.25)
    final_year_growth = clamp(max(0.035, year_one_growth * 0.55), 0.0, 0.15)

    roes = [
        float(row["net_income"]) / float(row["book_equity"])
        for row in history[-3:]
        if row.get("net_income") is not None
        and row.get("book_equity") is not None
        and row["book_equity"] > 0
    ]
    reported_roe = info.get("returnOnEquity")
    starting_roe = float(reported_roe) if reported_roe is not None else (roes[-1] if roes else 0.12)
    target_roe = median(roes) if roes else starting_roe

    beta = clamp(info.get("beta") or 1.0, 0.5, 2.0)
    risk_free_rate = float(info.get("_risk_free_rate") or 0.0425)
    equity_risk_premium = 0.045
    cost_of_equity = clamp(risk_free_rate + beta * equity_risk_premium, 0.07, 0.18)
    return {
        "starting_roe": clamp(starting_roe, 0.03, 0.40),
        "year_one_growth": year_one_growth,
        "final_year_growth": final_year_growth,
        "target_roe": clamp(target_roe, 0.06, 0.35),
        "cost_of_equity": cost_of_equity,
        "terminal_growth": 0.025,
        "forecast_years": 5,
        "risk_free_rate": risk_free_rate,
        "equity_risk_premium": equity_risk_premium,
    }


def equity_scenario_assumptions(defaults: dict, scenario: str) -> dict:
    adjustments = {
        "Bear": (-0.03, -0.015, -0.025, 0.010, -0.005),
        "Base": (0.0, 0.0, 0.0, 0.0, 0.0),
        "Bull": (0.03, 0.015, 0.025, -0.0075, 0.005),
    }
    growth_one, growth_final, roe, cost_equity, terminal = adjustments[scenario]
    return {
        **defaults,
        "year_one_growth": clamp(defaults["year_one_growth"] + growth_one, -0.30, 0.60),
        "final_year_growth": clamp(defaults["final_year_growth"] + growth_final, -0.10, 0.25),
        "target_roe": clamp(defaults["target_roe"] + roe, 0.03, 0.45),
        "cost_of_equity": clamp(defaults["cost_of_equity"] + cost_equity, 0.05, 0.22),
        "terminal_growth": clamp(defaults["terminal_growth"] + terminal, 0.0, 0.05),
    }


def solve_implied_year_one_growth(
    target_price: float,
    model_inputs: dict,
    lower: float = -0.50,
    upper: float = 1.50,
    iterations: int = 80,
) -> float | None:
    """Solve for year-one growth that makes DCF value equal the market price."""
    def price_at(growth: float) -> float:
        result = run_dcf(**{**model_inputs, "year_one_growth": growth})
        return result["value_per_share"]

    lower_price = price_at(lower)
    upper_price = price_at(upper)
    if target_price < min(lower_price, upper_price) or target_price > max(lower_price, upper_price):
        return None

    increasing = upper_price >= lower_price
    for _ in range(iterations):
        midpoint = (lower + upper) / 2.0
        midpoint_price = price_at(midpoint)
        if (midpoint_price < target_price) == increasing:
            lower = midpoint
        else:
            upper = midpoint
    return (lower + upper) / 2.0
