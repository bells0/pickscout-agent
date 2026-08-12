import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.unit_economics import (
    FORMULA_VERSION,
    ValidationError,
    calculate_unit_economics,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPOSITORY_ROOT / "scripts" / "unit_economics.py"
TEMPLATE_PATH = REPOSITORY_ROOT / "templates" / "unit-economics-input.json"


def sourced(amount, as_of="2026-07-30"):
    return {"amount": amount, "source": "test fixture", "as_of": as_of}


def scenario(selling_price="20.00"):
    return {
        "selling_price": sourced(selling_price),
        "referral_fee": sourced("2.00"),
        "fba_fulfillment_fee": sourced("3.00"),
        "inbound_shipping": sourced("0.50"),
        "storage": sourced("0.25"),
        "landed_product_cost": sourced("4.00"),
        "advertising": sourced("1.50"),
        "returns_and_losses": sourced("0.50"),
        "taxes_and_fx": sourced("0.25"),
    }


def valid_document():
    return {
        "market": "Amazon US",
        "currency": "USD",
        "as_of": "2026-07-30",
        "freshness_days": {
            "selling_price": 30,
            "referral_fee": 30,
            "fba_fulfillment_fee": 30,
            "inbound_shipping": 30,
            "storage": 30,
            "landed_product_cost": 30,
            "advertising": 30,
            "returns_and_losses": 30,
            "taxes_and_fx": 30,
        },
        "scenarios": {
            "pessimistic": scenario("18.00"),
            "base": scenario("20.00"),
            "optimistic": scenario("22.00"),
        },
    }


class CalculateUnitEconomicsTests(unittest.TestCase):
    def test_calculates_all_three_scenarios_with_exact_decimal_output(self):
        result = calculate_unit_economics(valid_document())

        self.assertEqual(result["formula_version"], FORMULA_VERSION)
        self.assertEqual(
            list(result["scenarios"]),
            ["pessimistic", "base", "optimistic"],
        )
        self.assertEqual(
            result["scenarios"]["base"]["total_variable_cost"], "12.00"
        )
        self.assertEqual(
            result["scenarios"]["base"]["contribution_profit"], "8.00"
        )
        self.assertEqual(
            result["scenarios"]["base"]["contribution_margin_percent"], "40.00"
        )

    def test_preserves_metadata_and_each_input_source(self):
        document = valid_document()
        document["scenarios"]["base"]["advertising"]["source"] = (
            "user quote captured 2026-07-30"
        )

        result = calculate_unit_economics(document)

        self.assertEqual(result["market"], document["market"])
        self.assertEqual(result["currency"], document["currency"])
        self.assertEqual(result["as_of"], document["as_of"])
        self.assertEqual(result["freshness_days"], document["freshness_days"])
        self.assertEqual(
            result["scenarios"]["base"]["inputs"]["advertising"],
            {
                "amount": "1.50",
                "source": "user quote captured 2026-07-30",
                "as_of": "2026-07-30",
                "age_days": 0,
                "max_age_days": 30,
            },
        )

    def test_preserves_sub_cent_input_used_by_the_calculation(self):
        document = valid_document()
        document["scenarios"]["base"]["advertising"]["amount"] = "1.504"

        result = calculate_unit_economics(document)
        base = result["scenarios"]["base"]

        self.assertEqual(base["inputs"]["advertising"]["amount"], "1.504")
        self.assertEqual(base["total_variable_cost"], "12.00")
        self.assertEqual(base["contribution_profit"], "8.00")
        self.assertEqual(base["contribution_margin_percent"], "39.98")

    def test_rounds_percent_half_up_to_two_decimal_places(self):
        document = valid_document()
        document["scenarios"]["base"] = scenario("18.00")

        result = calculate_unit_economics(document)

        self.assertEqual(
            result["scenarios"]["base"]["contribution_margin_percent"], "33.33"
        )

    def test_allows_negative_contribution_profit_without_making_recommendation(self):
        document = valid_document()
        document["scenarios"]["pessimistic"] = scenario("10.00")

        result = calculate_unit_economics(document)
        pessimistic = result["scenarios"]["pessimistic"]

        self.assertEqual(pessimistic["contribution_profit"], "-2.00")
        self.assertEqual(pessimistic["contribution_margin_percent"], "-20.00")
        self.assertNotIn("recommendation", pessimistic)
        self.assertNotIn("recommendation", result)

    def test_rejects_incomplete_scenario_set(self):
        document = valid_document()
        del document["scenarios"]["optimistic"]

        with self.assertRaisesRegex(
            ValidationError, r"missing required scenario\(s\): optimistic"
        ):
            calculate_unit_economics(document)

    def test_rejects_missing_cost_field(self):
        document = valid_document()
        del document["scenarios"]["base"]["advertising"]

        with self.assertRaisesRegex(
            ValidationError,
            r"scenarios\.base is missing required field\(s\): advertising",
        ):
            calculate_unit_economics(document)

    def test_rejects_json_number_instead_of_decimal_string(self):
        document = valid_document()
        document["scenarios"]["base"]["storage"]["amount"] = 0.25

        with self.assertRaisesRegex(
            ValidationError,
            r"scenarios\.base\.storage\.amount must be a decimal string",
        ):
            calculate_unit_economics(document)

    def test_rejects_non_decimal_string(self):
        document = valid_document()
        document["scenarios"]["base"]["storage"]["amount"] = "not-a-number"

        with self.assertRaisesRegex(
            ValidationError,
            r"scenarios\.base\.storage\.amount must be a decimal string",
        ):
            calculate_unit_economics(document)

    def test_rejects_zero_or_negative_selling_price(self):
        for invalid_price in ("0.00", "-0.01"):
            with self.subTest(invalid_price=invalid_price):
                document = valid_document()
                document["scenarios"]["base"]["selling_price"]["amount"] = (
                    invalid_price
                )
                with self.assertRaisesRegex(
                    ValidationError,
                    r"selling_price\.amount must be greater than zero",
                ):
                    calculate_unit_economics(document)

    def test_rejects_negative_cost(self):
        document = valid_document()
        document["scenarios"]["base"]["advertising"]["amount"] = "-0.01"

        with self.assertRaisesRegex(
            ValidationError, r"advertising\.amount must not be negative"
        ):
            calculate_unit_economics(document)

    def test_rejects_empty_source(self):
        document = valid_document()
        document["scenarios"]["base"]["advertising"]["source"] = "  "

        with self.assertRaisesRegex(
            ValidationError,
            r"scenarios\.base\.advertising\.source must be a non-empty string",
        ):
            calculate_unit_economics(document)

    def test_rejects_invalid_top_level_as_of(self):
        for invalid_as_of in ("2026/07/30", "2026-02-30"):
            with self.subTest(invalid_as_of=invalid_as_of):
                document = valid_document()
                document["as_of"] = invalid_as_of
                with self.assertRaisesRegex(
                    ValidationError,
                    r"as_of must be .*ISO 8601 date",
                ):
                    calculate_unit_economics(document)

    def test_rejects_missing_per_item_as_of(self):
        document = valid_document()
        del document["scenarios"]["base"]["advertising"]["as_of"]

        with self.assertRaisesRegex(
            ValidationError,
            r"scenarios\.base\.advertising is missing required field\(s\): as_of",
        ):
            calculate_unit_economics(document)

    def test_rejects_invalid_per_item_as_of(self):
        document = valid_document()
        document["scenarios"]["base"]["advertising"]["as_of"] = "2026-06-31"

        with self.assertRaisesRegex(
            ValidationError,
            r"scenarios\.base\.advertising\.as_of must be a valid ISO 8601 date",
        ):
            calculate_unit_economics(document)

    def test_rejects_per_item_as_of_after_research_cutoff(self):
        document = valid_document()
        document["scenarios"]["base"]["advertising"]["as_of"] = "2026-07-31"

        with self.assertRaisesRegex(
            ValidationError,
            r"scenarios\.base\.advertising\.as_of must not be after research "
            r"as_of 2026-07-30",
        ):
            calculate_unit_economics(document)

    def test_rejects_stale_per_item_as_of(self):
        document = valid_document()
        document["freshness_days"]["advertising"] = 5
        document["scenarios"]["base"]["advertising"]["as_of"] = "2026-07-24"

        with self.assertRaisesRegex(
            ValidationError,
            r"scenarios\.base\.advertising\.as_of is stale: age_days 6 exceeds "
            r"max_age_days 5",
        ):
            calculate_unit_economics(document)

    def test_accepts_mixed_dates_and_emits_exact_freshness_provenance(self):
        document = valid_document()
        dates = {
            "selling_price": "2026-07-30",
            "referral_fee": "2026-07-29",
            "fba_fulfillment_fee": "2026-07-28",
            "inbound_shipping": "2026-07-27",
            "storage": "2026-07-26",
            "landed_product_cost": "2026-07-25",
            "advertising": "2026-07-20",
            "returns_and_losses": "2026-07-10",
            "taxes_and_fx": "2026-06-30",
        }
        for field_name, field_as_of in dates.items():
            document["scenarios"]["base"][field_name]["as_of"] = field_as_of
        document["scenarios"]["base"]["taxes_and_fx"]["source"] = (
            "dated test fixture"
        )

        result = calculate_unit_economics(document)
        base_inputs = result["scenarios"]["base"]["inputs"]

        self.assertEqual(base_inputs["selling_price"]["age_days"], 0)
        self.assertEqual(base_inputs["advertising"]["age_days"], 10)
        self.assertEqual(
            base_inputs["taxes_and_fx"],
            {
                "amount": "0.25",
                "source": "dated test fixture",
                "as_of": "2026-06-30",
                "age_days": 30,
                "max_age_days": 30,
            },
        )

    def test_rejects_missing_or_invalid_freshness_threshold(self):
        document = valid_document()
        del document["freshness_days"]
        with self.assertRaisesRegex(
            ValidationError,
            r"missing required top-level field\(s\): freshness_days",
        ):
            calculate_unit_economics(document)

        document = valid_document()
        del document["freshness_days"]["advertising"]
        with self.assertRaisesRegex(
            ValidationError,
            r"freshness_days is missing required field\(s\): advertising",
        ):
            calculate_unit_economics(document)

        for invalid_threshold in (-1, 1.5, True):
            with self.subTest(invalid_threshold=invalid_threshold):
                document = valid_document()
                document["freshness_days"]["advertising"] = invalid_threshold
                with self.assertRaisesRegex(
                    ValidationError,
                    r"freshness_days\.advertising must be a non-negative integer",
                ):
                    calculate_unit_economics(document)

    def test_does_not_mutate_input(self):
        document = valid_document()
        original = copy.deepcopy(document)

        calculate_unit_economics(document)

        self.assertEqual(document, original)


class UnitEconomicsCliTests(unittest.TestCase):
    def run_cli(self, path):
        return subprocess.run(
            [sys.executable, str(SCRIPT_PATH), str(path)],
            cwd=str(REPOSITORY_ROOT),
            check=False,
            capture_output=True,
            text=True,
        )

    def test_template_runs_and_stdout_is_deterministic_json(self):
        first = self.run_cli(TEMPLATE_PATH)
        second = self.run_cli(TEMPLATE_PATH)

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(first.stderr, "")
        parsed = json.loads(first.stdout)
        self.assertEqual(
            set(parsed["scenarios"]),
            {"pessimistic", "base", "optimistic"},
        )
        self.assertEqual(
            parsed["scenarios"]["base"]["inputs"]["advertising"]["age_days"], 0
        )
        self.assertEqual(
            parsed["scenarios"]["base"]["inputs"]["advertising"]["max_age_days"],
            30,
        )

    def test_template_marks_every_sourced_value_as_illustrative(self):
        template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))

        for scenario_name, scenario_inputs in template["scenarios"].items():
            for field_name, field_value in scenario_inputs.items():
                with self.subTest(
                    scenario_name=scenario_name,
                    field_name=field_name,
                ):
                    self.assertIn("Illustrative", field_value["source"])
                    self.assertRegex(field_value["as_of"], r"^\d{4}-\d{2}-\d{2}$")

    def test_validation_failure_uses_stderr_and_nonzero_exit(self):
        document = valid_document()
        document["scenarios"]["base"]["storage"]["amount"] = "unknown"
        with tempfile.TemporaryDirectory() as temporary_directory:
            input_path = Path(temporary_directory) / "invalid.json"
            input_path.write_text(json.dumps(document), encoding="utf-8")

            completed = self.run_cli(input_path)

        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "")
        self.assertIn(
            "error: scenarios.base.storage.amount must be a decimal string",
            completed.stderr,
        )

    def test_invalid_json_uses_stderr_and_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            input_path = Path(temporary_directory) / "invalid.json"
            input_path.write_text("{", encoding="utf-8")

            completed = self.run_cli(input_path)

        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "")
        self.assertIn("error: input file contains invalid JSON", completed.stderr)


if __name__ == "__main__":
    unittest.main()
