import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.hard_gates import (
    FORMULA_VERSION,
    ValidationError,
    evaluate_hard_gates,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPOSITORY_ROOT / "scripts" / "hard_gates.py"
TEMPLATE_PATH = REPOSITORY_ROOT / "templates" / "hard-gates-input.json"


def sourced(value, as_of="2026-07-30"):
    return {
        "value": value,
        "source": "test fixture",
        "as_of": as_of,
    }


def valid_document():
    return {
        "market": "Amazon US",
        "currency": "USD",
        "as_of": "2026-07-30",
        "seller_constraints": {
            "max_initial_cash_exposure": sourced("3000.00"),
            "max_lead_time_days": sourced(45),
        },
        "candidate": {
            "supplier_moq_units": sourced(200),
            "planned_order_quantity": sourced(300),
            "lead_time_days": sourced(30),
            "landed_product_cost_per_unit": sourced("6.50"),
            "other_initial_cash_cost": sourced("200.00"),
        },
    }


class EvaluateHardGatesTests(unittest.TestCase):
    def test_all_gates_pass_and_cash_formula_is_exact(self):
        result = evaluate_hard_gates(valid_document())

        self.assertEqual(result["formula_version"], FORMULA_VERSION)
        self.assertEqual(result["overall_status"], "pass")
        self.assertEqual(
            {
                gate_name: gate["status"]
                for gate_name, gate in result["gates"].items()
            },
            {
                "moq_feasibility": "pass",
                "lead_time": "pass",
                "initial_cash_exposure": "pass",
            },
        )
        self.assertEqual(
            result["gates"]["initial_cash_exposure"][
                "calculated_initial_cash_exposure"
            ],
            {"value": "2150.00", "currency": "USD"},
        )

    def test_cash_exposure_over_limit_fails(self):
        document = valid_document()
        document["seller_constraints"]["max_initial_cash_exposure"] = sourced(
            "2000.00"
        )

        result = evaluate_hard_gates(document)

        self.assertEqual(
            result["gates"]["initial_cash_exposure"]["status"], "fail"
        )
        self.assertEqual(result["overall_status"], "fail")

    def test_lead_time_over_limit_fails(self):
        document = valid_document()
        document["candidate"]["lead_time_days"] = sourced(46)

        result = evaluate_hard_gates(document)

        self.assertEqual(result["gates"]["lead_time"]["status"], "fail")
        self.assertEqual(result["overall_status"], "fail")

    def test_planned_order_below_supplier_moq_fails(self):
        document = valid_document()
        document["candidate"]["planned_order_quantity"] = sourced(199)

        result = evaluate_hard_gates(document)

        self.assertEqual(result["gates"]["moq_feasibility"]["status"], "fail")
        self.assertEqual(result["overall_status"], "fail")

    def test_missing_moq_and_null_lead_time_are_unknown(self):
        document = valid_document()
        del document["candidate"]["supplier_moq_units"]
        document["candidate"]["lead_time_days"] = None

        result = evaluate_hard_gates(document)

        self.assertEqual(result["gates"]["moq_feasibility"]["status"], "unknown")
        self.assertEqual(result["gates"]["lead_time"]["status"], "unknown")
        self.assertEqual(
            result["gates"]["moq_feasibility"]["missing_inputs"],
            ["supplier_moq_units"],
        )
        self.assertEqual(
            result["gates"]["lead_time"]["missing_inputs"],
            ["lead_time_days"],
        )
        self.assertEqual(result["overall_status"], "unknown")

    def test_missing_cash_input_is_unknown_without_a_default(self):
        document = valid_document()
        del document["candidate"]["other_initial_cash_cost"]

        result = evaluate_hard_gates(document)
        cash_gate = result["gates"]["initial_cash_exposure"]

        self.assertEqual(cash_gate["status"], "unknown")
        self.assertEqual(cash_gate["calculated_initial_cash_exposure"], None)
        self.assertEqual(cash_gate["missing_inputs"], ["other_initial_cash_cost"])
        self.assertEqual(result["overall_status"], "unknown")

    def test_object_with_explicit_null_value_is_unknown(self):
        document = valid_document()
        document["candidate"]["supplier_moq_units"] = {"value": None}

        result = evaluate_hard_gates(document)

        self.assertEqual(result["gates"]["moq_feasibility"]["status"], "unknown")
        self.assertEqual(
            result["gates"]["moq_feasibility"]["used_values"][
                "supplier_moq_units"
            ],
            None,
        )

    def test_fail_takes_precedence_over_unknown_in_overall_status(self):
        document = valid_document()
        document["candidate"]["supplier_moq_units"] = None
        document["candidate"]["lead_time_days"] = sourced(46)

        result = evaluate_hard_gates(document)

        self.assertEqual(result["gates"]["moq_feasibility"]["status"], "unknown")
        self.assertEqual(result["gates"]["lead_time"]["status"], "fail")
        self.assertEqual(result["overall_status"], "fail")

    def test_preserves_sources_dates_and_exact_sourced_values(self):
        document = valid_document()
        document["candidate"]["landed_product_cost_per_unit"] = {
            "value": "6.505",
            "source": "supplier quote Q-123",
            "as_of": "2026-07-29",
        }

        result = evaluate_hard_gates(document)
        used = result["gates"]["initial_cash_exposure"]["used_values"]

        self.assertEqual(
            used["landed_product_cost_per_unit"],
            {
                "value": "6.505",
                "source": "supplier quote Q-123",
                "as_of": "2026-07-29",
            },
        )
        self.assertEqual(
            result["gates"]["initial_cash_exposure"][
                "calculated_initial_cash_exposure"
            ]["value"],
            "2151.50",
        )

    def test_rejects_illegal_numeric_types_and_negative_values(self):
        cases = (
            (
                ("seller_constraints", "max_initial_cash_exposure"),
                3000.0,
                r"must be a non-negative decimal string",
            ),
            (
                ("candidate", "planned_order_quantity"),
                "300",
                r"must be a non-negative integer",
            ),
            (
                ("candidate", "lead_time_days"),
                -1,
                r"must be a non-negative integer",
            ),
            (
                ("candidate", "supplier_moq_units"),
                True,
                r"must be a non-negative integer",
            ),
            (
                ("candidate", "other_initial_cash_cost"),
                "-0.01",
                r"must not be negative",
            ),
        )
        for field_path, invalid_value, expected_error in cases:
            with self.subTest(field_path=field_path, invalid_value=invalid_value):
                document = valid_document()
                document[field_path[0]][field_path[1]]["value"] = invalid_value
                with self.assertRaisesRegex(ValidationError, expected_error):
                    evaluate_hard_gates(document)

    def test_rejects_invalid_dates_and_values_after_research_cutoff(self):
        cases = (
            (
                lambda document: document.__setitem__("as_of", "2026-02-30"),
                r"as_of must be a valid date",
            ),
            (
                lambda document: document["candidate"][
                    "lead_time_days"
                ].__setitem__("as_of", "2026/07/30"),
                r"lead_time_days\.as_of must be a valid date",
            ),
            (
                lambda document: document["candidate"][
                    "lead_time_days"
                ].__setitem__("as_of", "2026-07-31"),
                r"lead_time_days\.as_of must not be after the research cutoff",
            ),
        )
        for mutate, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                document = valid_document()
                mutate(document)
                with self.assertRaisesRegex(ValidationError, expected_error):
                    evaluate_hard_gates(document)

    def test_requires_source_and_as_of_for_every_real_value(self):
        for required_field in ("source", "as_of"):
            with self.subTest(required_field=required_field):
                document = valid_document()
                del document["candidate"]["lead_time_days"][required_field]
                with self.assertRaisesRegex(
                    ValidationError,
                    rf"lead_time_days is missing required field\(s\): "
                    rf"{required_field}",
                ):
                    evaluate_hard_gates(document)

    def test_rejects_malformed_sections_and_sourced_values(self):
        cases = (
            (
                lambda document: document.__setitem__("candidate", []),
                r"candidate must be an object or null",
            ),
            (
                lambda document: document["candidate"].__setitem__(
                    "lead_time_days", 30
                ),
                r"lead_time_days must be an object",
            ),
            (
                lambda document: document["candidate"].__setitem__(
                    "lead_time_days", {}
                ),
                r"lead_time_days is missing required field: value",
            ),
        )
        for mutate, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                document = valid_document()
                mutate(document)
                with self.assertRaisesRegex(ValidationError, expected_error):
                    evaluate_hard_gates(document)

    def test_does_not_mutate_input(self):
        document = valid_document()
        original = copy.deepcopy(document)

        evaluate_hard_gates(document)

        self.assertEqual(document, original)


class HardGatesCliTests(unittest.TestCase):
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
        self.assertEqual(parsed["overall_status"], "pass")
        self.assertEqual(
            set(parsed["gates"]),
            {"moq_feasibility", "lead_time", "initial_cash_exposure"},
        )
        self.assertEqual(
            parsed["gates"]["initial_cash_exposure"][
                "calculated_initial_cash_exposure"
            ]["value"],
            "4250.00",
        )

    def test_template_marks_every_sourced_value_as_illustrative(self):
        document = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))

        for section_name in ("seller_constraints", "candidate"):
            for field_name, sourced_value in document[section_name].items():
                with self.subTest(
                    section_name=section_name, field_name=field_name
                ):
                    self.assertIn("Illustrative", sourced_value["source"])

    def test_validation_failure_uses_stderr_and_exit_two(self):
        document = valid_document()
        document["candidate"]["lead_time_days"]["value"] = -1
        with tempfile.TemporaryDirectory() as temporary_directory:
            input_path = Path(temporary_directory) / "invalid.json"
            input_path.write_text(json.dumps(document), encoding="utf-8")

            completed = self.run_cli(input_path)

        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertIn(
            "error: candidate.lead_time_days.value must be a non-negative integer",
            completed.stderr,
        )

    def test_invalid_json_and_non_utf8_input_fail_cleanly(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            invalid_json_path = Path(temporary_directory) / "invalid.json"
            invalid_json_path.write_text("{", encoding="utf-8")
            invalid_json = self.run_cli(invalid_json_path)

            non_utf8_path = Path(temporary_directory) / "non-utf8.json"
            non_utf8_path.write_bytes(b"\xff")
            non_utf8 = self.run_cli(non_utf8_path)

        self.assertEqual(invalid_json.returncode, 2)
        self.assertEqual(invalid_json.stdout, "")
        self.assertIn("error: input file contains invalid JSON", invalid_json.stderr)
        self.assertEqual(non_utf8.returncode, 2)
        self.assertEqual(non_utf8.stdout, "")
        self.assertIn("error: input file must be UTF-8", non_utf8.stderr)


if __name__ == "__main__":
    unittest.main()
