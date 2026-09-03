import unittest

import pandas as pd

from dashboard_utils import (
    debt_to_equity_ratio,
    dividend_yield_percent,
    equal_weight_index,
    format_price,
    statement_value,
)


class DashboardUtilsTests(unittest.TestCase):
    def test_dividend_yield_uses_trailing_decimal_fraction(self):
        info = {
            "trailingAnnualDividendYield": 0.003229,
            "dividendYield": 0.33,
        }
        self.assertAlmostEqual(dividend_yield_percent(info), 0.3229, places=4)

    def test_dividend_yield_falls_back_to_rate_over_price(self):
        info = {"dividendRate": 1.08, "currentPrice": 324.96}
        self.assertAlmostEqual(dividend_yield_percent(info), 0.33235, places=4)

    def test_debt_to_equity_uses_balance_sheet_values(self):
        info = {"totalDebt": 80, "bookValue": 10, "sharesOutstanding": 10}
        self.assertEqual(debt_to_equity_ratio(info), 0.8)

    def test_debt_to_equity_normalizes_yahoo_percentage(self):
        self.assertEqual(debt_to_equity_ratio({"debtToEquity": 78.4}), 0.784)

    def test_equal_weight_index_compounds_average_daily_returns(self):
        dates = pd.date_range("2026-01-01", periods=3)
        closes = {
            "A": pd.Series([100.0, 110.0, 121.0], index=dates),
            "B": pd.Series([100.0, 90.0, 99.0], index=dates),
        }
        result = equal_weight_index(closes)
        self.assertEqual(len(result), 3)
        for actual, expected in zip(result, [100.0, 100.0, 110.0]):
            self.assertAlmostEqual(actual, expected)

    def test_statement_value_matches_cash_flow_column_by_year(self):
        statement = pd.DataFrame(
            {pd.Timestamp("2025-12-31"): [25.0]},
            index=["Operating Cash Flow"],
        )
        value = statement_value(
            statement,
            ["Operating Cash Flow"],
            pd.Timestamp("2025-09-30"),
        )
        self.assertEqual(value, 25.0)

    def test_format_price_is_consistent(self):
        self.assertEqual(format_price(345), "$345.00")
        self.assertEqual(format_price(None), "—")


if __name__ == "__main__":
    unittest.main()
