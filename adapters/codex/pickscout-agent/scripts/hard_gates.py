#!/usr/bin/env python3
"""Evaluate deterministic supply and cash hard gates from sourced inputs."""

import argparse
import json
import re
import sys
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple


FORMULA_VERSION = "pickscout-hard-gates-v1"
GATE_NAMES: Tuple[str, ...] = (
    "moq_feasibility",
    "lead_time",
    "initial_cash_exposure",
)
DECIMAL_STRING = re.compile(r"^-?(?:\d+(?:\.\d+)?|\.\d+)$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ValidationError(ValueError):
    """Raised when a hard-gates input does not satisfy the contract."""


def _missing_keys(value: Mapping[str, Any], required: Iterable[str]) -> Tuple[str, ...]:
    return tuple(key for key in required if key not in value)


def _require_non_empty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{path} must be a non-empty string")
    return value


def _parse_date(value: Any, path: str) -> date:
    if not isinstance(value, str) or ISO_DATE.fullmatch(value) is None:
        raise ValidationError(f"{path} must be a valid date in YYYY-MM-DD format")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(
            f"{path} must be a valid date in YYYY-MM-DD format"
        ) from exc


def _parse_nonnegative_integer(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(f"{path} must be a non-negative integer")
    return value


def _parse_nonnegative_decimal(value: Any, path: str) -> Decimal:
    if not isinstance(value, str) or DECIMAL_STRING.fullmatch(value) is None:
        raise ValidationError(
            f'{path} must be a non-negative decimal string, for example "12.34"'
        )
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValidationError(f"{path} must be a finite decimal string") from exc
    if not amount.is_finite():
        raise ValidationError(f"{path} must be a finite decimal string")
    if amount < 0:
        raise ValidationError(f"{path} must not be negative")
    return amount


def _section(document: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    if name not in document or document[name] is None:
        return {}
    value = document[name]
    if not isinstance(value, Mapping):
        raise ValidationError(f"{name} must be an object or null")
    return value


def _sourced_value(
    section: Mapping[str, Any],
    section_name: str,
    field_name: str,
    value_kind: str,
    research_cutoff: date,
) -> Optional[Tuple[Any, Dict[str, Any]]]:
    if field_name not in section or section[field_name] is None:
        return None

    field_path = f"{section_name}.{field_name}"
    raw = section[field_name]
    if not isinstance(raw, Mapping):
        raise ValidationError(
            f"{field_path} must be an object with value, source, and as_of, or null"
        )
    if "value" not in raw:
        raise ValidationError(f"{field_path} is missing required field: value")
    if raw["value"] is None:
        return None

    missing = _missing_keys(raw, ("source", "as_of"))
    if missing:
        raise ValidationError(
            f"{field_path} is missing required field(s): {', '.join(missing)}"
        )

    if value_kind == "integer":
        parsed_value = _parse_nonnegative_integer(
            raw["value"], f"{field_path}.value"
        )
    elif value_kind == "decimal":
        parsed_value = _parse_nonnegative_decimal(
            raw["value"], f"{field_path}.value"
        )
    else:
        raise AssertionError(f"unsupported value kind: {value_kind}")

    source = _require_non_empty_string(raw["source"], f"{field_path}.source")
    value_as_of = _parse_date(raw["as_of"], f"{field_path}.as_of")
    if value_as_of > research_cutoff:
        raise ValidationError(
            f"{field_path}.as_of must not be after the research cutoff as_of"
        )

    return (
        parsed_value,
        {
            "value": raw["value"],
            "source": source,
            "as_of": raw["as_of"],
        },
    )


def _used_values(
    values: Mapping[str, Optional[Tuple[Any, Dict[str, Any]]]],
    fields: Sequence[str],
) -> Dict[str, Any]:
    return {
        field_name: (
            values[field_name][1] if values[field_name] is not None else None
        )
        for field_name in fields
    }


def _missing_inputs(
    values: Mapping[str, Optional[Tuple[Any, Dict[str, Any]]]],
    fields: Sequence[str],
) -> Tuple[str, ...]:
    return tuple(field_name for field_name in fields if values[field_name] is None)


def _unknown_basis(missing: Sequence[str]) -> str:
    return (
        "Cannot evaluate because input(s) are missing or null: "
        + ", ".join(missing)
        + "."
    )


def _format_money(value: Decimal) -> str:
    """Return an exact, non-exponent decimal string with at least two places."""

    rendered = format(value, "f")
    if "." not in rendered:
        return rendered + ".00"
    whole, fractional = rendered.split(".", 1)
    fractional = fractional.rstrip("0")
    if len(fractional) < 2:
        fractional += "0" * (2 - len(fractional))
    return whole + "." + fractional


def _cash_working_precision(
    quantity: int, unit_cost: Decimal, other_cost: Decimal
) -> int:
    product_digits_upper_bound = (
        len(unit_cost.as_tuple().digits) + len(str(quantity))
    )
    product_exponent = unit_cost.as_tuple().exponent
    other_exponent = other_cost.as_tuple().exponent
    highest_position = max(
        product_exponent + product_digits_upper_bound - 1,
        other_exponent + len(other_cost.as_tuple().digits) - 1,
    )
    lowest_position = min(product_exponent, other_exponent)
    return max(
        50,
        highest_position - lowest_position + 4,
    )


def evaluate_hard_gates(document: Any) -> Dict[str, Any]:
    """Validate an input document and return three deterministic gate results."""

    if not isinstance(document, Mapping):
        raise ValidationError("input must be a JSON object")

    missing = _missing_keys(document, ("market", "currency", "as_of"))
    if missing:
        raise ValidationError(
            f"input is missing required top-level field(s): {', '.join(missing)}"
        )

    market = _require_non_empty_string(document["market"], "market")
    currency = _require_non_empty_string(document["currency"], "currency")
    as_of = _require_non_empty_string(document["as_of"], "as_of")
    research_cutoff = _parse_date(as_of, "as_of")

    seller_constraints = _section(document, "seller_constraints")
    candidate = _section(document, "candidate")
    values: Dict[str, Optional[Tuple[Any, Dict[str, Any]]]] = {
        "max_initial_cash_exposure": _sourced_value(
            seller_constraints,
            "seller_constraints",
            "max_initial_cash_exposure",
            "decimal",
            research_cutoff,
        ),
        "max_lead_time_days": _sourced_value(
            seller_constraints,
            "seller_constraints",
            "max_lead_time_days",
            "integer",
            research_cutoff,
        ),
        "supplier_moq_units": _sourced_value(
            candidate,
            "candidate",
            "supplier_moq_units",
            "integer",
            research_cutoff,
        ),
        "planned_order_quantity": _sourced_value(
            candidate,
            "candidate",
            "planned_order_quantity",
            "integer",
            research_cutoff,
        ),
        "lead_time_days": _sourced_value(
            candidate,
            "candidate",
            "lead_time_days",
            "integer",
            research_cutoff,
        ),
        "landed_product_cost_per_unit": _sourced_value(
            candidate,
            "candidate",
            "landed_product_cost_per_unit",
            "decimal",
            research_cutoff,
        ),
        "other_initial_cash_cost": _sourced_value(
            candidate,
            "candidate",
            "other_initial_cash_cost",
            "decimal",
            research_cutoff,
        ),
    }

    moq_fields = ("planned_order_quantity", "supplier_moq_units")
    moq_missing = _missing_inputs(values, moq_fields)
    if moq_missing:
        moq_gate = {
            "status": "unknown",
            "rule": "planned_order_quantity >= supplier_moq_units",
            "basis": _unknown_basis(moq_missing),
            "missing_inputs": list(moq_missing),
            "used_values": _used_values(values, moq_fields),
        }
    else:
        planned_quantity = values["planned_order_quantity"][0]
        supplier_moq = values["supplier_moq_units"][0]
        moq_status = "pass" if planned_quantity >= supplier_moq else "fail"
        comparison = "is" if moq_status == "pass" else "is not"
        moq_gate = {
            "status": moq_status,
            "rule": "planned_order_quantity >= supplier_moq_units",
            "basis": (
                f"planned_order_quantity ({planned_quantity}) {comparison} "
                "greater than or equal to "
                f"supplier_moq_units ({supplier_moq})."
            ),
            "missing_inputs": [],
            "used_values": _used_values(values, moq_fields),
        }

    lead_time_fields = ("lead_time_days", "max_lead_time_days")
    lead_time_missing = _missing_inputs(values, lead_time_fields)
    if lead_time_missing:
        lead_time_gate = {
            "status": "unknown",
            "rule": "lead_time_days <= max_lead_time_days",
            "basis": _unknown_basis(lead_time_missing),
            "missing_inputs": list(lead_time_missing),
            "used_values": _used_values(values, lead_time_fields),
        }
    else:
        lead_time_days = values["lead_time_days"][0]
        max_lead_time_days = values["max_lead_time_days"][0]
        lead_time_status = (
            "pass" if lead_time_days <= max_lead_time_days else "fail"
        )
        comparison = "is" if lead_time_status == "pass" else "is not"
        lead_time_gate = {
            "status": lead_time_status,
            "rule": "lead_time_days <= max_lead_time_days",
            "basis": (
                f"lead_time_days ({lead_time_days}) {comparison} "
                "less than or equal to "
                f"max_lead_time_days ({max_lead_time_days})."
            ),
            "missing_inputs": [],
            "used_values": _used_values(values, lead_time_fields),
        }

    cash_fields = (
        "planned_order_quantity",
        "landed_product_cost_per_unit",
        "other_initial_cash_cost",
        "max_initial_cash_exposure",
    )
    cash_missing = _missing_inputs(values, cash_fields)
    cash_formula = (
        "planned_order_quantity * landed_product_cost_per_unit "
        "+ other_initial_cash_cost"
    )
    if cash_missing:
        cash_gate = {
            "status": "unknown",
            "rule": (
                "initial_cash_exposure <= max_initial_cash_exposure"
            ),
            "formula": cash_formula,
            "basis": _unknown_basis(cash_missing),
            "missing_inputs": list(cash_missing),
            "used_values": _used_values(values, cash_fields),
            "calculated_initial_cash_exposure": None,
        }
    else:
        planned_quantity = values["planned_order_quantity"][0]
        unit_cost = values["landed_product_cost_per_unit"][0]
        other_cost = values["other_initial_cash_cost"][0]
        max_cash = values["max_initial_cash_exposure"][0]
        with localcontext() as context:
            context.prec = _cash_working_precision(
                planned_quantity, unit_cost, other_cost
            )
            cash_exposure = (planned_quantity * unit_cost) + other_cost
        cash_status = "pass" if cash_exposure <= max_cash else "fail"
        comparison = "is" if cash_status == "pass" else "is not"
        formatted_exposure = _format_money(cash_exposure)
        formatted_max_cash = _format_money(max_cash)
        cash_gate = {
            "status": cash_status,
            "rule": (
                "initial_cash_exposure <= max_initial_cash_exposure"
            ),
            "formula": cash_formula,
            "basis": (
                f"initial_cash_exposure ({formatted_exposure} {currency}) "
                f"{comparison} less than or equal to "
                "max_initial_cash_exposure "
                f"({formatted_max_cash} {currency})."
            ),
            "missing_inputs": [],
            "used_values": _used_values(values, cash_fields),
            "calculated_initial_cash_exposure": {
                "value": formatted_exposure,
                "currency": currency,
            },
        }

    gates = {
        "moq_feasibility": moq_gate,
        "lead_time": lead_time_gate,
        "initial_cash_exposure": cash_gate,
    }
    statuses = tuple(gates[gate_name]["status"] for gate_name in GATE_NAMES)
    if "fail" in statuses:
        overall_status = "fail"
    elif "unknown" in statuses:
        overall_status = "unknown"
    else:
        overall_status = "pass"

    return {
        "market": market,
        "currency": currency,
        "as_of": as_of,
        "formula_version": FORMULA_VERSION,
        "gates": gates,
        "overall_status": overall_status,
    }


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as input_file:
            return json.load(input_file)
    except FileNotFoundError as exc:
        raise ValidationError(f"input file does not exist: {path}") from exc
    except PermissionError as exc:
        raise ValidationError(f"input file is not readable: {path}") from exc
    except UnicodeDecodeError as exc:
        raise ValidationError(f"input file must be UTF-8: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"input file contains invalid JSON at line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise ValidationError(f"could not read input file {path}: {exc}") from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate sourced MOQ, lead-time, and initial-cash hard gates."
        )
    )
    parser.add_argument("input", type=Path, help="path to a UTF-8 JSON input file")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = evaluate_hard_gates(_load_json(args.input))
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
