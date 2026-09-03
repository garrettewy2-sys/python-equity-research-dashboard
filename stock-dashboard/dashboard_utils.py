"""Pure helpers for dashboard calculations and display formatting."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


def numeric(value):
    """Return a finite float, or None for missing/non-numeric values."""
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if pd.notna(result) else None


def dividend_yield_percent(info: Mapping) -> float | None:
    """Normalize Yahoo dividend fields to percentage points."""
    trailing_yield = numeric(info.get("trailingAnnualDividendYield"))
    if trailing_yield is not None and trailing_yield >= 0:
        return trailing_yield * 100.0

    annual_dividend = numeric(
        info.get("trailingAnnualDividendRate", info.get("dividendRate"))
    )
    price = numeric(info.get("currentPrice", info.get("regularMarketPrice")))
    if annual_dividend is not None and price is not None and price > 0:
        return annual_dividend / price * 100.0

    quoted_yield = numeric(info.get("dividendYield"))
    return quoted_yield if quoted_yield is not None and quoted_yield >= 0 else None


def debt_to_equity_ratio(info: Mapping) -> float | None:
    """Return debt/equity as a ratio rather than Yahoo's percentage value."""
    debt = numeric(info.get("totalDebt"))
    book_value = numeric(info.get("bookValue"))
    shares = numeric(info.get("sharesOutstanding"))
    if debt is not None and book_value is not None and shares is not None:
        equity = book_value * shares
        if equity != 0:
            return debt / equity

    quoted_ratio = numeric(info.get("debtToEquity"))
    return quoted_ratio / 100.0 if quoted_ratio is not None else None


def equal_weight_index(closes: Mapping[str, pd.Series]) -> list[float]:
    """Build a daily rebalanced equal-weight index starting at 100."""
    usable = {}
    for name, series in closes.items():
        if not isinstance(series, pd.Series):
            continue
        cleaned = pd.to_numeric(series, errors="coerce").dropna()
        if len(cleaned) >= 2:
            usable[name] = cleaned

    if not usable:
        return []

    prices = pd.concat(usable, axis=1).sort_index()
    daily_returns = prices.pct_change(fill_method=None)
    portfolio_returns = daily_returns.mean(axis=1, skipna=True).dropna()
    if portfolio_returns.empty:
        return []

    index = (1.0 + portfolio_returns).cumprod() * 100.0
    return [100.0, *index.astype(float).tolist()]


def statement_value(statement, row_names, period):
    """Read a numeric statement value, matching fallback columns by year."""
    if statement is None or statement.empty:
        return None

    column = period if period in statement.columns else None
    if column is None and hasattr(period, "year"):
        column = next(
            (c for c in statement.columns if getattr(c, "year", None) == period.year),
            None,
        )
    if column is None:
        return None

    for row_name in row_names:
        if row_name in statement.index:
            value = numeric(statement.loc[row_name, column])
            if value is not None:
                return value
    return None


def format_price(value) -> str:
    value = numeric(value)
    return f"${value:,.2f}" if value is not None else "—"


def valuation_share_count(info: Mapping) -> float | None:
    """Return the best aggregate share count available for per-share valuation.

    Yahoo's ``sharesOutstanding`` can describe only one listed share class. Its
    ``impliedSharesOutstanding`` field is therefore preferred when it is valid;
    market capitalization divided by price is the next-best aggregate check.
    """
    return valuation_share_count_details(info)["value"]


def valuation_share_count_details(info: Mapping) -> dict:
    """Return the chosen aggregate share count together with its exact source."""
    implied = numeric(info.get("impliedSharesOutstanding"))
    if implied is not None and implied > 0:
        return {"value": implied, "source": "Yahoo impliedSharesOutstanding (current aggregate estimate)"}

    market_cap = numeric(info.get("marketCap"))
    price = numeric(info.get("currentPrice", info.get("regularMarketPrice")))
    if market_cap is not None and market_cap > 0 and price is not None and price > 0:
        return {"value": market_cap / price, "source": "Yahoo marketCap ÷ currentPrice (aggregate reconciliation)"}

    reported = numeric(info.get("sharesOutstanding"))
    if reported is not None and reported > 0:
        return {"value": reported, "source": "Yahoo sharesOutstanding (fallback; may be class-specific)"}
    return {"value": None, "source": "Data unavailable"}


def risk_statistics(close: pd.Series, annual_risk_free_rate: float = 0.0) -> dict:
    """Calculate transparent daily-return risk and performance statistics."""
    prices = pd.to_numeric(close, errors="coerce").dropna()
    if len(prices) < 2:
        return {
            "annualized_volatility": None,
            "downside_volatility": None,
            "maximum_drawdown": None,
            "sharpe_ratio": None,
            "return_1y": None,
            "return_3y": None,
        }

    returns = prices.pct_change(fill_method=None).dropna()
    annualized_volatility = returns.std() * (252 ** 0.5) if len(returns) > 1 else None
    downside = returns[returns < 0]
    downside_volatility = downside.std() * (252 ** 0.5) if len(downside) > 1 else None
    drawdown = prices / prices.cummax() - 1.0
    maximum_drawdown = float(drawdown.min())
    sharpe_ratio = None
    if annualized_volatility and annualized_volatility > 0:
        sharpe_ratio = (returns.mean() * 252 - annual_risk_free_rate) / annualized_volatility

    def trailing_return(days: int) -> float | None:
        if len(prices) < 2:
            return None
        window = prices.iloc[-min(len(prices), days + 1):]
        if len(window) < min(days, 20) or window.iloc[0] == 0:
            return None
        return float(window.iloc[-1] / window.iloc[0] - 1.0)

    return {
        "annualized_volatility": float(annualized_volatility) if annualized_volatility is not None else None,
        "downside_volatility": float(downside_volatility) if downside_volatility is not None else None,
        "maximum_drawdown": maximum_drawdown,
        "sharpe_ratio": float(sharpe_ratio) if sharpe_ratio is not None else None,
        "return_1y": trailing_return(252),
        "return_3y": trailing_return(756),
    }


def align_price_series(left: pd.Series, right: pd.Series, left_name: str, right_name: str) -> pd.DataFrame:
    """Return two numeric price series on identical, non-missing dates."""
    aligned = pd.concat(
        [
            pd.to_numeric(left, errors="coerce").rename(left_name),
            pd.to_numeric(right, errors="coerce").rename(right_name),
        ],
        axis=1,
        join="inner",
    )
    return aligned.dropna()
