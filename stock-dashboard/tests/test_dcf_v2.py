import unittest

from dcf_v2 import (
    FRAMEWORKS,
    build_v2_defaults,
    calculate_wacc,
    run_v2_case,
    scenario_inputs,
    solve_v2_assumption,
    three_anchor_path,
)


class DcfV2Tests(unittest.TestCase):
    def setUp(self):
        self.standard_history = [
            {
                "revenue": 80.0,
                "fcff": 12.0,
                "interest": 2.0,
                "tax_rate": 0.21,
                "operating_income": 16.0,
            },
            {
                "revenue": 90.0,
                "fcff": 14.0,
                "interest": 2.0,
                "tax_rate": 0.21,
                "operating_income": 18.0,
            },
            {
                "revenue": 100.0,
                "fcff": 17.0,
                "interest": 2.0,
                "tax_rate": 0.21,
                "operating_income": 21.0,
            },
        ]
        self.info = {
            "beta": 1.0,
            "marketCap": 900.0,
            "totalDebt": 100.0,
            "_risk_free_rate": 0.04,
            "_equity_risk_premium": 0.05,
        }

    def test_every_supported_company_has_a_framework(self):
        expected = {
            "AAPL", "PLTR", "NVDA", "TSLA", "MSFT", "AMZN", "GOOGL",
            "META", "AMD", "AVGO", "JPM", "GS", "V", "BRK-B", "LMT",
            "RKLB", "SOFI", "UBER", "ASTS",
        }
        self.assertEqual(set(FRAMEWORKS), expected)

    def test_three_anchor_growth_path_hits_all_anchors(self):
        self.assertAlmostEqual(three_anchor_path(1, 8, 0.20, 0.10, 0.03, 4), 0.20)
        self.assertAlmostEqual(three_anchor_path(4, 8, 0.20, 0.10, 0.03, 4), 0.10)
        self.assertAlmostEqual(three_anchor_path(8, 8, 0.20, 0.10, 0.03, 4), 0.03)

    def test_wacc_exposes_exact_components(self):
        result = calculate_wacc(self.standard_history, self.info)
        self.assertAlmostEqual(result["cost_of_equity"], 0.09)
        self.assertAlmostEqual(result["pre_tax_cost_of_debt"], 0.02)
        self.assertAlmostEqual(result["equity_weight"], 0.90)
        self.assertAlmostEqual(result["debt_weight"], 0.10)
        expected = 0.9 * 0.09 + 0.1 * 0.02 * (1 - 0.21)
        self.assertAlmostEqual(result["wacc"], expected)

    def test_wacc_discloses_and_applies_beta_guardrail(self):
        result = calculate_wacc(self.standard_history, {**self.info, "beta": 0.10})
        self.assertAlmostEqual(result["raw_beta"], 0.10)
        self.assertAlmostEqual(result["beta"], 0.50)
        self.assertTrue(any("beta" in warning.lower() for warning in result["warnings"]))

    def test_standard_dcf_reconciles_enterprise_and_equity_values(self):
        defaults = build_v2_defaults("AAPL", self.standard_history, self.info, 10.0, 25.0)
        result, inputs = run_v2_case(defaults)
        self.assertEqual(len(result["schedule"]), inputs["horizon"])
        self.assertAlmostEqual(result["equity_value"], result["enterprise_value"] - 25.0)
        self.assertAlmostEqual(result["value_per_share"], result["equity_value"] / 10.0)

    def test_scenarios_move_value_in_the_expected_direction(self):
        defaults = build_v2_defaults("AAPL", self.standard_history, self.info, 10.0, 25.0)
        bear = run_v2_case(defaults, "Bear")[0]["value_per_share"]
        base = run_v2_case(defaults, "Base")[0]["value_per_share"]
        bull = run_v2_case(defaults, "Bull")[0]["value_per_share"]
        self.assertLess(bear, base)
        self.assertLess(base, bull)

    def test_preprofit_terminal_value_requires_positive_mature_fcff(self):
        history = [
            {"revenue": 10.0, "operating_income": -30.0, "interest": 0.0, "tax_rate": 0.21},
            {"revenue": 12.0, "operating_income": -30.0, "interest": 0.0, "tax_rate": 0.21},
        ]
        defaults = build_v2_defaults("RKLB", history, self.info, 10.0, -5.0)
        with self.assertRaisesRegex(ValueError, "terminal value is disabled"):
            run_v2_case(defaults, overrides={"target_operating_margin": -0.05})

    def test_financial_framework_values_equity_directly(self):
        history = [
            {"net_income": 10.0, "book_equity": 100.0, "interest": 0.0, "tax_rate": 0.21},
            {"net_income": 12.0, "book_equity": 110.0, "interest": 0.0, "tax_rate": 0.21},
            {"net_income": 13.0, "book_equity": 120.0, "interest": 0.0, "tax_rate": 0.21},
        ]
        defaults = build_v2_defaults("JPM", history, self.info, 10.0, 50.0)
        result, _ = run_v2_case(defaults)
        self.assertAlmostEqual(result["enterprise_value"], result["equity_value"])
        self.assertIn("present_value_fcfe", result)

    def test_special_case_is_explicitly_unsuitable(self):
        defaults = build_v2_defaults("BRK-B", self.standard_history, self.info, 10.0, 0.0)
        self.assertFalse(defaults["suitable"])
        with self.assertRaisesRegex(ValueError, "not an appropriate"):
            run_v2_case(defaults)

    def test_reverse_solver_recovers_base_growth(self):
        defaults = build_v2_defaults("AAPL", self.standard_history, self.info, 10.0, 25.0)
        target = run_v2_case(defaults)[0]["value_per_share"]
        solved = solve_v2_assumption(defaults, target, "year_one_growth", -0.25, 0.75)
        self.assertIsNotNone(solved)
        self.assertAlmostEqual(solved, defaults["year_one_growth"], places=6)

    def test_scenario_inputs_are_transparently_exposed(self):
        defaults = build_v2_defaults("AAPL", self.standard_history, self.info, 10.0, 25.0)
        self.assertGreater(scenario_inputs(defaults, "Bull")["mature_fcff_margin"], defaults["mature_fcff_margin"])


if __name__ == "__main__":
    unittest.main()
