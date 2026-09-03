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
