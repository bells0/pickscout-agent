import copy
import json
import unittest
from decimal import Decimal
from pathlib import Path

from scripts.cost_pricing import calculate_pricing, ValidationError


ROOT = Path(__file__).resolve().parents[1]


def example():
    return json.loads((ROOT / "templates/cost-pricing-input.json").read_text())


class CostPricingTests(unittest.TestCase):
    def test_forward_inverse_and_unknown_income_tax(self):
        case = calculate_pricing(example())["cases"][0]
        self.assertEqual(case["prices"][0]["operating_remainder"], "5.00")
        self.assertIsNone(case["prices"][0]["after_income_tax_subtotal"])
        self.assertIn("income_tax", case["prices"][0]["scope"]["unassessed_categories"])
        self.assertEqual(case["target_prices"]["break_even"]["price"], "12.31")
        self.assertEqual(case["target_prices"]["unit_profit"]["price"], "16.93")
        self.assertEqual(case["target_prices"]["margin"]["price"], "17.78")

    def test_bundle_fx_and_shared_allocation(self):
        d = example()
        costs = d["cases"][0]["costs"]
        costs[0]["quantity"] = "2"
        result = calculate_pricing(d)["cases"][0]["prices"][0]
        self.assertEqual(result["operating_remainder"], "4.00")
        lines = {r["id"]: r for r in result["lines"]}
        self.assertEqual(lines["goods"]["amount"], "2.00")
        self.assertEqual(lines["monthly"]["amount"], "0.80")

    def test_missing_cost_is_not_zero_or_reported_as_known(self):
        d = example()
        row = d["cases"][0]["costs"][2]
        row.update(value=None, status="unknown", reason="无报价")
        r = calculate_pricing(d)["cases"][0]["prices"][0]
        self.assertIsNone(r["lines"][2]["amount"])
        self.assertEqual(r["operating_remainder"], "6.00")
        self.assertIn("inbound", r["scope"]["unassessed_categories"])
        self.assertIn("import_duty", r["scope"]["unassessed_categories"])

    def test_explicit_tax_allocation_and_scope_still_visible(self):
        d = example()
        d["cases"][0]["costs"][-1].update(value="1", status="budget")
        r = calculate_pricing(d)["cases"][0]["prices"][0]
        self.assertEqual(r["operating_remainder"], "5.00")
        self.assertEqual(r["after_income_tax_subtotal"], "4.00")
        self.assertEqual(r["income_tax_allocation"], "1.00")

    def test_rejects_income_tax_as_revenue_rate(self):
        d = example()
        d["cases"][0]["costs"][-1].update(value="0.25", status="budget", kind="rate")
        with self.assertRaisesRegex(ValidationError, "income_tax"):
            calculate_pricing(d)

    def test_does_not_charge_tube_twice(self):
        d = example()
        row = copy.deepcopy(d["cases"][0]["costs"][0])
        row.update(id="tube-extra", covers=["tube"], value="1")
        d["cases"][0]["costs"].append(row)
        with self.assertRaisesRegex(ValidationError, "overlapping cost coverage: tube"):
            calculate_pricing(d)

    def test_distinct_components_can_share_category(self):
        d = example()
        row = copy.deepcopy(d["cases"][0]["costs"][0])
        row.update(id="second-part", covers=["second-part"], value="7")
        d["cases"][0]["costs"].append(row)
        self.assertEqual(calculate_pricing(d)["cases"][0]["prices"][0]["operating_remainder"], "4.00")

    def test_minimum_commission_is_applied_in_inverse(self):
        d = example()
        base = copy.deepcopy(d["cases"][0]["costs"][0])
        base.update(value="1", currency="USD", covers=["product"])
        fee = copy.deepcopy(d["cases"][0]["costs"][8])
        fee.update(value="0.15", minimum_amount="2")
        d["cases"][0]["costs"] = [base, fee]
        d["cases"][0].pop("price_bands")
        self.assertEqual(calculate_pricing(d)["cases"][0]["target_prices"]["break_even"]["price"], "3.00")

    def test_fee_jump_cannot_use_low_band_solution_above_threshold(self):
        d = example()
        c = d["cases"][0]
        c["costs"] = [copy.deepcopy(c["costs"][4])]
        c["costs"][0]["value"] = "12"
        c["price_bands"][0]["overrides"]["fba"]["value"] = "9.999"
        # A cent-rounded low-band solution becomes 10.00, outside [0.01,10).
        r = calculate_pricing(d)["cases"][0]["target_prices"]["break_even"]
        self.assertEqual((r["price"], r["band"]), ("12.00", "synthetic-regular"))

    def test_overlapping_bands_rejected(self):
        d = example()
        d["cases"][0]["price_bands"][1]["min_price"] = "9.99"
        with self.assertRaisesRegex(ValidationError, "overlapping price bands"):
            calculate_pricing(d)

    def test_sub_cent_price_cannot_hide_which_fee_band_applies(self):
        d = example()
        d["cases"][0]["prices"][0]["value"] = "9.999"
        with self.assertRaisesRegex(ValidationError, "0.01 increments"):
            calculate_pricing(d)

    def test_all_rates_consuming_revenue_have_no_positive_target(self):
        d = example()
        next(r for r in d["cases"][0]["costs"] if r["id"] == "ads")["value"] = "0.90"
        result = calculate_pricing(d)["cases"][0]
        self.assertIsNone(result["target_prices"]["unit_profit"]["price"])
        self.assertLess(Decimal(result["prices"][0]["operating_remainder"]), 0)

    def test_multiple_cases_preserve_independent_units_and_inputs(self):
        d = example()
        second = copy.deepcopy(d["cases"][0])
        second["id"] = "two-pack"
        second["costs"][0]["quantity"] = "2"
        d["cases"].append(second)
        before = copy.deepcopy(d)
        r = calculate_pricing(d)
        self.assertEqual([x["prices"][0]["operating_remainder"] for x in r["cases"]], ["5.00", "4.00"])
        self.assertEqual(d, before)

    def test_unaddressed_categories_are_listed(self):
        d = example()
        d["cases"][0]["costs"] = d["cases"][0]["costs"][:1]
        d["cases"][0].pop("price_bands")
        r = calculate_pricing(d)["cases"][0]["prices"][0]
        self.assertIn("fulfillment", r["scope"]["unassessed_categories"])
        self.assertIn("income_tax", r["scope"]["unassessed_categories"])

    def test_only_unknown_costs_do_not_produce_a_zero_cost_price(self):
        d = example()
        c = d["cases"][0]
        c["costs"] = [c["costs"][-1]]
        c.pop("price_bands")
        self.assertIsNone(calculate_pricing(d)["cases"][0]["target_prices"]["break_even"]["price"])


if __name__ == "__main__":
    unittest.main()
