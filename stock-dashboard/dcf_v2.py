"""Company-aware DCF V2 calculations.

V1 remains in dcf_model.py as the frozen public baseline.  This module adds a
separate comparison framework with issuer-specific horizons and economic
guardrails; it never calibrates assumptions to the current share price.
"""

from __future__ import annotations

from statistics import median


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, float(value)))


FRAMEWORKS = {
    "AAPL": dict(framework="Standard mature-company DCF", modifiers=("Consumer platform", "Hardware/services mix", "Cash generative"), horizon=6, mature_growth=0.025, margin_bounds=(0.16, 0.34)),
    "PLTR": dict(framework="High-growth profitable DCF", modifiers=("High growth", "Asset light", "Government exposure"), horizon=8, mature_growth=0.030, margin_bounds=(0.16, 0.42)),
    "NVDA": dict(framework="High-growth profitable DCF", modifiers=("High growth", "Cyclical", "Fabless semiconductor"), horizon=8, mature_growth=0.030, margin_bounds=(0.18, 0.48)),
    "TSLA": dict(framework="High-growth profitable DCF", modifiers=("Capital intensive", "Cyclical", "Margin uncertainty"), horizon=10, mature_growth=0.025, margin_bounds=(0.04, 0.18)),
    "MSFT": dict(framework="Standard mature-company DCF", modifiers=("Asset light", "Recurring revenue", "High growth"), horizon=7, mature_growth=0.025, margin_bounds=(0.22, 0.42)),
    "AMZN": dict(framework="High-growth profitable DCF", modifiers=("Capital intensive", "Mixed-margin segments"), horizon=8, mature_growth=0.025, margin_bounds=(0.06, 0.24)),
    "GOOGL": dict(framework="Standard mature-company DCF", modifiers=("Asset light", "Advertising sensitive", "High growth"), horizon=7, mature_growth=0.025, margin_bounds=(0.18, 0.36)),
    "META": dict(framework="Standard mature-company DCF", modifiers=("Asset light", "Advertising sensitive", "High reinvestment"), horizon=7, mature_growth=0.025, margin_bounds=(0.18, 0.40)),
    "AMD": dict(framework="High-growth profitable DCF", modifiers=("Cyclical", "Fabless semiconductor", "High growth"), horizon=8, mature_growth=0.030, margin_bounds=(0.08, 0.30)),
    "AVGO": dict(framework="Standard mature-company DCF", modifiers=("Cyclical", "Software/semiconductor mix", "Leveraged integration"), horizon=7, mature_growth=0.025, margin_bounds=(0.20, 0.46)),
    "JPM": dict(framework="Financial institution / FCFE", modifiers=("Credit sensitive", "Cyclical", "Regulated"), horizon=5, mature_growth=0.025),
    "GS": dict(framework="Financial institution / FCFE", modifiers=("Capital-markets sensitive", "Cyclical", "Regulated"), horizon=5, mature_growth=0.025),
    "V": dict(framework="Standard mature-company DCF", modifiers=("Asset light", "Network economics", "Regulated"), horizon=6, mature_growth=0.025, margin_bounds=(0.35, 0.58)),
    "BRK-B": dict(framework="Special-case valuation", modifiers=("Conglomerate", "Insurance", "Capital intensive"), horizon=None, mature_growth=None),
    "LMT": dict(framework="Standard mature-company DCF", modifiers=("Capital intensive", "Government exposed", "Backlog driven"), horizon=5, mature_growth=0.020, margin_bounds=(0.07, 0.16)),
    "RKLB": dict(framework="Pre-profit / emerging-company DCF", modifiers=("Capital intensive", "High growth", "Execution sensitive"), horizon=12, mature_growth=0.030, operating_margin_target=0.16, sales_to_capital=1.35),
    "SOFI": dict(framework="Financial institution / FCFE", modifiers=("High growth", "Credit sensitive", "Regulated"), horizon=8, mature_growth=0.025),
    "UBER": dict(framework="High-growth profitable DCF", modifiers=("Asset light", "High growth", "Regulatory exposure"), horizon=8, mature_growth=0.025, margin_bounds=(0.08, 0.25)),
    "ASTS": dict(framework="Pre-profit / emerging-company DCF", modifiers=("Capital intensive", "Pre-scale", "Financing and execution risk"), horizon=15, mature_growth=0.030, operating_margin_target=0.18, sales_to_capital=0.85),
}


def framework_for(symbol: str) -> dict:
    if symbol not in FRAMEWORKS:
        raise ValueError(f"No DCF V2 framework is configured for {symbol}.")
    return dict(FRAMEWORKS[symbol])


def three_anchor_path(year: int, horizon: int, year_one: float, intermediate: float, mature: float, midpoint_year: int | None = None) -> float:
    """Piecewise-linear path through Year 1, a midpoint, and the mature year."""
    midpoint = midpoint_year or max(2, (horizon + 1) // 2)
    midpoint = max(2, min(horizon - 1, midpoint))
    if year <= midpoint:
        weight = (year - 1) / (midpoint - 1)
        return year_one + (intermediate - year_one) * weight
    weight = (year - midpoint) / (horizon - midpoint)
    return intermediate + (mature - intermediate) * weight


def calculate_wacc(history: list[dict], info: dict) -> dict:
    warnings = []
    risk_free_rate = float(info.get("_risk_free_rate") or 0.0425)
    beta_raw = info.get("beta")
    raw_beta = float(beta_raw) if beta_raw is not None and float(beta_raw) > 0 else None
    beta = clamp(raw_beta, 0.5, 2.0) if raw_beta is not None else 1.0
    if beta_raw is None:
        warnings.append("Beta unavailable; 1.00 is used as a disclosed fallback.")
    elif abs(beta - raw_beta) > 1e-9:
        warnings.append(f"Raw beta of {raw_beta:.2f} is outside the 0.50–2.00 economic guardrail; {beta:.2f} is applied to cost of equity.")
    equity_risk_premium = float(info.get("_equity_risk_premium") or 0.045)
    cost_of_equity = risk_free_rate + beta * equity_risk_premium

    market_cap = max(0.0, float(info.get("marketCap") or 0.0))
    debt = max(0.0, float(info.get("totalDebt") or 0.0))
    latest_interest = abs(float(history[-1].get("interest") or 0.0)) if history else 0.0
    raw_cost_of_debt = latest_interest / debt if debt > 0 and latest_interest > 0 else None
    if debt <= 0:
        pre_tax_cost_of_debt = 0.0
    elif raw_cost_of_debt is None:
        pre_tax_cost_of_debt = 0.05
        warnings.append("Interest expense unavailable; a disclosed 5.0% pre-tax debt-cost fallback is used.")
    else:
        pre_tax_cost_of_debt = clamp(raw_cost_of_debt, 0.02, 0.12)
        if abs(pre_tax_cost_of_debt - raw_cost_of_debt) > 1e-9:
            warnings.append(f"Raw interest/debt cost of {raw_cost_of_debt:.1%} is outside the 2%–12% economic guardrail; {pre_tax_cost_of_debt:.1%} is applied.")

    tax_rate = float(history[-1].get("tax_rate") or 0.21) if history else 0.21
    tax_rate = clamp(tax_rate, 0.0, 0.35)
    capital = market_cap + debt
    equity_weight = market_cap / capital if capital > 0 else 1.0
    debt_weight = debt / capital if capital > 0 else 0.0
    wacc = equity_weight * cost_of_equity + debt_weight * pre_tax_cost_of_debt * (1.0 - tax_rate)
    return {
        "risk_free_rate": risk_free_rate,
        "raw_beta": raw_beta,
        "beta": beta,
        "equity_risk_premium": equity_risk_premium,
        "cost_of_equity": cost_of_equity,
        "raw_cost_of_debt": raw_cost_of_debt,
        "pre_tax_cost_of_debt": pre_tax_cost_of_debt,
        "tax_rate": tax_rate,
        "debt_weight": debt_weight,
        "equity_weight": equity_weight,
        "wacc": wacc,
        "warnings": warnings,
    }


def _reported_growth(history: list[dict], field: str) -> list[float]:
    values = [float(row[field]) for row in history if row.get(field) is not None and float(row[field]) > 0]
    return [current / previous - 1.0 for previous, current in zip(values, values[1:]) if previous > 0]


def build_v2_defaults(symbol: str, history: list[dict], info: dict, shares: float, net_debt: float) -> dict:
    config = framework_for(symbol)
    framework = config["framework"]
    base = {
        **config,
        "symbol": symbol,
        "modifiers": list(config["modifiers"]),
        "shares_outstanding": float(shares),
        "net_debt": float(net_debt),
        "warnings": [],
        "suitable": True,
    }
    if framework == "Special-case valuation":
        return {
            **base,
            "suitable": False,
            "warnings": ["A consolidated DCF is not an appropriate V2 default. Berkshire requires a sum-of-the-parts or adjusted-NAV framework."],
        }

    growth = _reported_growth(history, "net_income" if framework == "Financial institution / FCFE" else "revenue")
    recent_growth = median(growth[-3:]) if growth else 0.06
    year_one_growth = clamp(recent_growth, -0.15, 0.50 if framework.startswith("Pre-profit") else 0.35)
    mature_growth = float(config["mature_growth"])
    intermediate_growth = (year_one_growth + mature_growth) / 2.0
    if framework in {"High-growth profitable DCF", "Pre-profit / emerging-company DCF"}:
        intermediate_growth = max(mature_growth + 0.01, year_one_growth * 0.55)

    wacc = calculate_wacc(history, info)
    base.update({
        "year_one_growth": year_one_growth,
        "intermediate_growth": intermediate_growth,
        "midpoint_year": max(2, (int(config["horizon"]) + 1) // 2),
        "wacc_breakdown": wacc,
        "wacc": wacc["wacc"],
        "cost_of_equity": wacc["cost_of_equity"],
    })
    base["warnings"].extend(wacc["warnings"])

    if framework == "Financial institution / FCFE":
        usable = [row for row in history if row.get("net_income") is not None and row.get("book_equity") is not None and row["book_equity"] > 0]
        if not usable or usable[-1]["net_income"] <= 0:
            base.update(suitable=False)
            base["warnings"].append("Positive earnings and common-equity history are required for an FCFE valuation.")
            return base
        roes = [row["net_income"] / row["book_equity"] for row in usable[-3:] if row["net_income"] > 0]
        base.update(
            base_net_income=float(usable[-1]["net_income"]),
            starting_roe=clamp(roes[-1] if roes else 0.12, 0.03, 0.40),
            target_roe=clamp(median(roes) if roes else 0.12, 0.06, 0.35),
        )
        return base

    usable = [row for row in history if row.get("revenue") is not None and row["revenue"] > 0]
    if len(usable) < 2:
        base.update(suitable=False)
        base["warnings"].append("At least two reported revenue periods are required for a defensible growth path.")
        return base
    base["base_revenue"] = float(usable[-1]["revenue"])

    if framework == "Pre-profit / emerging-company DCF":
        operating_margins = [row["operating_income"] / row["revenue"] for row in usable if row.get("operating_income") is not None]
        if not operating_margins:
            base.update(suitable=False)
            base["warnings"].append("Operating-income history is unavailable, so a profitability inflection cannot be modeled defensibly.")
            return base
        base.update(
            starting_operating_margin=float(operating_margins[-1]),
            target_operating_margin=float(config["operating_margin_target"]),
            sales_to_capital=float(config["sales_to_capital"]),
            tax_rate=wacc["tax_rate"],
        )
        base["warnings"].append("Emerging-company output is highly speculative and depends on explicit scale, margin and reinvestment assumptions.")
        return base

    margins = [row["fcff"] / row["revenue"] for row in usable[-4:] if row.get("fcff") is not None]
    if not margins:
        base.update(suitable=False)
        base["warnings"].append("Reported cash-flow history is unavailable, so FCFF margins cannot be anchored.")
        return base
    lower, upper = config["margin_bounds"]
    historical_median = median(margins)
    mature_margin = clamp(0.6 * historical_median + 0.4 * margins[-1], lower, upper)
    base.update(
        starting_fcff_margin=float(margins[-1]),
        historical_fcff_margin_median=float(historical_median),
        historical_fcff_margin_low=float(min(margins)),
        historical_fcff_margin_high=float(max(margins)),
        mature_fcff_margin=float(mature_margin),
        margin_guardrail_low=float(lower),
        margin_guardrail_high=float(upper),
    )
    return base


def _scenario(defaults: dict, name: str) -> dict:
    if name not in {"Bear", "Base", "Bull"}:
        raise ValueError("Scenario must be Bear, Base, or Bull.")
    if name == "Base":
        return dict(defaults)
    direction = -1.0 if name == "Bear" else 1.0
    out = dict(defaults)
    out["year_one_growth"] += direction * 0.025
    out["intermediate_growth"] += direction * 0.015
    out["mature_growth"] += direction * 0.003
    out["wacc"] -= direction * 0.0075
    if defaults["framework"] == "Financial institution / FCFE":
        out["target_roe"] += direction * 0.02
        out["cost_of_equity"] -= direction * 0.0075
    elif defaults["framework"] == "Pre-profit / emerging-company DCF":
        out["target_operating_margin"] += direction * 0.03
    else:
        out["mature_fcff_margin"] += direction * 0.02
    return out


def scenario_inputs(defaults: dict, name: str) -> dict:
    """Expose the transparent scenario inputs for UI and validation reporting."""
    return _scenario(defaults, name)


def _validate_terminal(discount_rate: float, mature_growth: float) -> None:
    if discount_rate <= mature_growth:
        raise ValueError("Discount rate must be greater than mature growth.")


def run_standard_dcf_v2(inputs: dict) -> dict:
    _validate_terminal(inputs["wacc"], inputs["mature_growth"])
    revenue = float(inputs["base_revenue"])
    schedule, pv_fcff = [], 0.0
    horizon = int(inputs["horizon"])
    for year in range(1, horizon + 1):
        growth = three_anchor_path(year, horizon, inputs["year_one_growth"], inputs["intermediate_growth"], inputs["mature_growth"], inputs["midpoint_year"])
        margin = inputs["starting_fcff_margin"] + (inputs["mature_fcff_margin"] - inputs["starting_fcff_margin"]) * (year / horizon)
        revenue *= 1.0 + growth
        fcff = revenue * margin
        pv = fcff / ((1.0 + inputs["wacc"]) ** year)
        pv_fcff += pv
        schedule.append(dict(year=year, growth=growth, revenue=revenue, fcff_margin=margin, fcff=fcff, pv_fcff=pv))
    terminal_fcff = schedule[-1]["fcff"] * (1.0 + inputs["mature_growth"])
    terminal_value = terminal_fcff / (inputs["wacc"] - inputs["mature_growth"])
    pv_terminal = terminal_value / ((1.0 + inputs["wacc"]) ** horizon)
    enterprise_value = pv_fcff + pv_terminal
    equity_value = enterprise_value - inputs["net_debt"]
    return _result(schedule, pv_fcff, pv_terminal, enterprise_value, equity_value, inputs["shares_outstanding"])


def run_preprofit_dcf_v2(inputs: dict) -> dict:
    _validate_terminal(inputs["wacc"], inputs["mature_growth"])
    revenue = float(inputs["base_revenue"])
    schedule, pv_fcff = [], 0.0
    horizon = int(inputs["horizon"])
    for year in range(1, horizon + 1):
        growth = three_anchor_path(year, horizon, inputs["year_one_growth"], inputs["intermediate_growth"], inputs["mature_growth"], inputs["midpoint_year"])
        prior_revenue = revenue
        revenue *= 1.0 + growth
        operating_margin = inputs["starting_operating_margin"] + (inputs["target_operating_margin"] - inputs["starting_operating_margin"]) * (year / horizon)
        nopat = revenue * operating_margin * (1.0 - inputs["tax_rate"])
        reinvestment = max(0.0, revenue - prior_revenue) / inputs["sales_to_capital"]
        fcff = nopat - reinvestment
        pv = fcff / ((1.0 + inputs["wacc"]) ** year)
        pv_fcff += pv
        schedule.append(dict(year=year, growth=growth, revenue=revenue, operating_margin=operating_margin, nopat=nopat, reinvestment=reinvestment, fcff=fcff, pv_fcff=pv))
    if schedule[-1]["operating_margin"] <= 0 or schedule[-1]["fcff"] <= 0:
        raise ValueError("The explicit forecast does not reach positive mature cash flow; terminal value is disabled.")
    terminal_fcff = schedule[-1]["fcff"] * (1.0 + inputs["mature_growth"])
    terminal_value = terminal_fcff / (inputs["wacc"] - inputs["mature_growth"])
    pv_terminal = terminal_value / ((1.0 + inputs["wacc"]) ** horizon)
    enterprise_value = pv_fcff + pv_terminal
    equity_value = enterprise_value - inputs["net_debt"]
    if equity_value <= 0:
        raise ValueError("The explicit forecast does not support a positive equity value; no per-share estimate is presented.")
    return _result(schedule, pv_fcff, pv_terminal, enterprise_value, equity_value, inputs["shares_outstanding"])


def run_financial_dcf_v2(inputs: dict) -> dict:
    _validate_terminal(inputs["cost_of_equity"], inputs["mature_growth"])
    earnings = float(inputs["base_net_income"])
    schedule, pv_fcfe = [], 0.0
    horizon = int(inputs["horizon"])
    for year in range(1, horizon + 1):
        growth = three_anchor_path(year, horizon, inputs["year_one_growth"], inputs["intermediate_growth"], inputs["mature_growth"], inputs["midpoint_year"])
        roe = inputs["starting_roe"] + (inputs["target_roe"] - inputs["starting_roe"]) * (year / horizon)
        earnings *= 1.0 + growth
        retention = clamp(growth / max(roe, 0.01), 0.0, 0.95)
        fcfe = earnings * (1.0 - retention)
        pv = fcfe / ((1.0 + inputs["cost_of_equity"]) ** year)
        pv_fcfe += pv
        schedule.append(dict(year=year, growth=growth, roe=roe, payout=1.0-retention, earnings=earnings, fcfe=fcfe, pv_fcfe=pv))
    terminal_payout = 1.0 - clamp(inputs["mature_growth"] / max(inputs["target_roe"], 0.01), 0.0, 0.95)
    terminal_fcfe = schedule[-1]["earnings"] * (1.0 + inputs["mature_growth"]) * terminal_payout
    terminal_value = terminal_fcfe / (inputs["cost_of_equity"] - inputs["mature_growth"])
    pv_terminal = terminal_value / ((1.0 + inputs["cost_of_equity"]) ** horizon)
    equity_value = pv_fcfe + pv_terminal
    result = _result(schedule, pv_fcfe, pv_terminal, equity_value, equity_value, inputs["shares_outstanding"])
    result["present_value_fcfe"] = result.pop("present_value_fcff")
    return result


def _result(schedule: list[dict], pv_explicit: float, pv_terminal: float, enterprise_value: float, equity_value: float, shares: float) -> dict:
    if shares <= 0:
        raise ValueError("Aggregate share count must be positive.")
    return {
        "schedule": schedule,
        "present_value_fcff": pv_explicit,
        "present_value_terminal": pv_terminal,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "value_per_share": equity_value / shares,
        "terminal_value_share": pv_terminal / enterprise_value if enterprise_value else 0.0,
    }


def run_v2_case(defaults: dict, scenario: str = "Base", overrides: dict | None = None) -> tuple[dict, dict]:
    if not defaults.get("suitable"):
        raise ValueError(defaults.get("warnings", ["DCF V2 is unsuitable for this company."])[0])
    inputs = _scenario(defaults, scenario)
    if overrides:
        inputs.update(overrides)
    framework = inputs["framework"]
    if framework == "Financial institution / FCFE":
        result = run_financial_dcf_v2(inputs)
    elif framework == "Pre-profit / emerging-company DCF":
        result = run_preprofit_dcf_v2(inputs)
    else:
        result = run_standard_dcf_v2(inputs)
    return result, inputs


def solve_v2_assumption(defaults: dict, target_price: float, field: str, lower: float, upper: float, iterations: int = 70) -> float | None:
    """Solve one V2 Base input while all other Base assumptions stay fixed."""
    def price(value: float) -> float | None:
        try:
            return run_v2_case(defaults, "Base", {field: value})[0]["value_per_share"]
        except ValueError:
            return None

    low_price, high_price = price(lower), price(upper)
    if low_price is None or high_price is None or target_price < min(low_price, high_price) or target_price > max(low_price, high_price):
        return None
    increasing = high_price >= low_price
    for _ in range(iterations):
        midpoint = (lower + upper) / 2.0
        midpoint_price = price(midpoint)
        if midpoint_price is None:
            return None
        if (midpoint_price < target_price) == increasing:
            lower = midpoint
        else:
            upper = midpoint
    return (lower + upper) / 2.0
