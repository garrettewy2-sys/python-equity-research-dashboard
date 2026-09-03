import unittest

from dcf_model import (
    equity_scenario_assumptions,
    estimate_defaults,
    estimate_equity_dcf_defaults,
    run_dcf,
    run_equity_dcf,
    scenario_assumptions,
    solve_implied_year_one_growth,
)


class DcfModelTests(unittest.TestCase):
    def setUp(self):
        self.inputs = {
            "base_revenue": 100.0,
            "starting_fcff_margin": 0.10,
            "year_one_growth": 0.10,
            "final_year_growth": 0.04,
            "target_fcff_margin": 0.15,
            "wacc": 0.09,
            "terminal_growth": 0.025,
            "forecast_years": 5,
            "net_debt": 10.0,
            "shares_outstanding": 10.0,
        }

    def test_run_dcf_builds_forecast_and_value(self):
        result = run_dcf(**self.inputs)
        self.assertEqual(len(result["schedule"]), 5)
        self.assertGreater(result["enterprise_value"], 0)
        self.assertGreater(result["value_per_share"], 0)

    def test_higher_wacc_reduces_value(self):
        low = run_dcf(**{**self.inputs, "wacc": 0.08})["value_per_share"]
        high = run_dcf(**{**self.inputs, "wacc": 0.11})["value_per_share"]
        self.assertGreater(low, high)

    def test_higher_terminal_growth_increases_value(self):
        low = run_dcf(**{**self.inputs, "terminal_growth": 0.015})["value_per_share"]
        high = run_dcf(**{**self.inputs, "terminal_growth": 0.035})["value_per_share"]
        self.assertGreater(high, low)

    def test_wacc_must_exceed_terminal_growth(self):
        with self.assertRaises(ValueError):
            run_dcf(**{**self.inputs, "wacc": 0.03, "terminal_growth": 0.03})

    def test_reverse_dcf_recovers_year_one_growth(self):
        target = run_dcf(**self.inputs)["value_per_share"]
        solved = solve_implied_year_one_growth(target, self.inputs)
        self.assertIsNotNone(solved)
        self.assertAlmostEqual(solved, self.inputs["year_one_growth"], places=6)

    def test_defaults_use_reported_history(self):
        history = [
            {"revenue": 80.0, "fcff": 8.0, "interest": 1.0, "tax_rate": 0.21},
            {"revenue": 90.0, "fcff": 10.0, "interest": 1.0, "tax_rate": 0.21},
            {"revenue": 100.0, "fcff": 12.0, "interest": 1.0, "tax_rate": 0.21},
        ]
        defaults = estimate_defaults(history, {"beta": 1.0, "marketCap": 900.0, "totalDebt": 100.0})
        self.assertAlmostEqual(defaults["year_one_growth"], 0.1180555, places=5)
        self.assertAlmostEqual(defaults["starting_fcff_margin"], 0.12)
        self.assertGreater(defaults["wacc"], 0.06)

    def test_scenarios_move_assumptions_consistently(self):
        defaults = estimate_defaults([], {})
        bear = scenario_assumptions(defaults, "Bear")
        bull = scenario_assumptions(defaults, "Bull")
        self.assertLess(bear["year_one_growth"], bull["year_one_growth"])
        self.assertGreater(bear["wacc"], bull["wacc"])
        self.assertLess(bear["terminal_growth"], bull["terminal_growth"])

    def test_bank_equity_dcf_returns_per_share_value(self):
        result = run_equity_dcf(
            base_net_income=20.0,
            starting_roe=0.15,
            year_one_growth=0.08,
            final_year_growth=0.04,
            target_roe=0.14,
            cost_of_equity=0.10,
            terminal_growth=0.025,
            forecast_years=5,
            shares_outstanding=10.0,
        )
        self.assertEqual(len(result["schedule"]), 5)
        self.assertGreater(result["value_per_share"], 0)

    def test_bank_defaults_and_scenarios(self):
        history = [
            {"net_income": 10.0, "book_equity": 100.0},
            {"net_income": 12.0, "book_equity": 108.0},
            {"net_income": 13.0, "book_equity": 116.0},
        ]
        defaults = estimate_equity_dcf_defaults(history, {"beta": 1.1})
        bear = equity_scenario_assumptions(defaults, "Bear")
        bull = equity_scenario_assumptions(defaults, "Bull")
        self.assertGreater(defaults["starting_roe"], 0)
        self.assertGreater(bear["cost_of_equity"], bull["cost_of_equity"])
        self.assertLess(bear["target_roe"], bull["target_roe"])


if __name__ == "__main__":
    unittest.main()
