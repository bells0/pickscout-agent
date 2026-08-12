#!/usr/bin/env python3
"""Calculate deterministic three-scenario unit economics from sourced inputs."""

import argparse
import json
import re
import sys
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple


FORMULA_VERSION = "pickscout-unit-economics-v1"
REQUIRED_SCENARIOS: Tuple[str, ...] = (
    "pessimistic",
    "base",
    "optimistic",
)
SELLING_PRICE_FIELD = "selling_price"
COST_FIELDS: Tuple[str, ...] = (
    "referral_fee",
    "fba_fulfillment_fee",
    "inbound_shipping",
    "storage",
    "landed_product_cost",
    "advertising",
    "returns_and_losses",
    "taxes_and_fx",
)
REQUIRED_FIELDS: Tuple[str, ...] = (SELLING_PRICE_FIELD,) + COST_FIELDS
MONEY_QUANTUM = Decimal("0.01")
PERCENT_QUANTUM = Decimal("0.01")
DECIMAL_STRING = re.compile(r"^-?(?:\d+(?:\.\d+)?|\.\d+)$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ValidationError(ValueError):
    """Raised when a unit-economics input does not satisfy the contract."""


def _missing_keys(value: Mapping[str, Any], required: Iterable[str]) -> Tuple[str, ...]:
    return tuple(key for key in required if key not in value)


def _require_non_empty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{path} must be a non-empty string")
    return value


def _parse_amount(value: Any, path: str) -> Decimal:
    if not isinstance(value, str) or DECIMAL_STRING.fullmatch(value) is None:
        raise ValidationError(
            f"{path} must be a decimal string, for example \"12.34\""
        )

    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValidationError(f"{path} must be a finite decimal string") from exc

    if not amount.is_finite():
        raise ValidationError(f"{path} must be a finite decimal string")
    return amount


def _parse_iso_date(value: Any, path: str) -> date:
    if not isinstance(value, str) or ISO_DATE.fullmatch(value) is None:
        raise ValidationError(f"{path} must be an ISO 8601 date in YYYY-MM-DD format")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(
            f"{path} must be a valid ISO 8601 date in YYYY-MM-DD format"
        ) from exc


def _validate_freshness_days(value: Any) -> Dict[str, int]:
    if not isinstance(value, Mapping):
        raise ValidationError("freshness_days must be an object")

    missing = _missing_keys(value, REQUIRED_FIELDS)
    if missing:
        raise ValidationError(
            "freshness_days is missing required field(s): " + ", ".join(missing)
        )

    unexpected = tuple(field for field in value if field not in REQUIRED_FIELDS)
    if unexpected:
        raise ValidationError(
            "freshness_days contains unexpected field(s): "
            + ", ".join(str(field) for field in unexpected)
        )

    freshness_days: Dict[str, int] = {}
    for field_name in REQUIRED_FIELDS:
        max_age_days = value[field_name]
        if isinstance(max_age_days, bool) or not isinstance(max_age_days, int):
            raise ValidationError(
                f"freshness_days.{field_name} must be a non-negative integer"
            )
        if max_age_days < 0:
            raise ValidationError(
                f"freshness_days.{field_name} must be a non-negative integer"
            )
        freshness_days[field_name] = max_age_days
    return freshness_days


def _working_precision(values: Iterable[Decimal]) -> int:
    values = tuple(values)
    maximum_digits = max(len(value.as_tuple().digits) for value in values)
    maximum_magnitude = max(
        abs(value.adjusted()) if not value.is_zero() else 0 for value in values
    )
    return max(50, maximum_digits + (2 * maximum_magnitude) + 32)


def _format_fixed(value: Decimal, quantum: Decimal) -> str:
    digits = len(value.as_tuple().digits)
    magnitude = abs(value.adjusted()) if not value.is_zero() else 0
    with localcontext() as context:
        context.prec = max(50, digits + magnitude + 32)
        rounded = value.quantize(quantum, rounding=ROUND_HALF_UP)
    if rounded.is_zero():
        rounded = abs(rounded)
    return format(rounded, ".2f")


def _validate_scenario(
    scenario_name: str,
    scenario: Any,
    research_as_of: date,
    freshness_days: Mapping[str, int],
) -> Tuple[Dict[str, Decimal], Dict[str, Dict[str, Any]]]:
    path = f"scenarios.{scenario_name}"
    if not isinstance(scenario, Mapping):
        raise ValidationError(f"{path} must be an object")

    missing = _missing_keys(scenario, REQUIRED_FIELDS)
    if missing:
        raise ValidationError(f"{path} is missing required field(s): {', '.join(missing)}")

    amounts: Dict[str, Decimal] = {}
    provenance: Dict[str, Dict[str, Any]] = {}

    for field_name in REQUIRED_FIELDS:
        field_path = f"{path}.{field_name}"
        field_value = scenario[field_name]
        if not isinstance(field_value, Mapping):
            raise ValidationError(
                f"{field_path} must be an object with amount, source, and as_of"
            )

        field_missing = _missing_keys(field_value, ("amount", "source", "as_of"))
        if field_missing:
            raise ValidationError(
                f"{field_path} is missing required field(s): "
                f"{', '.join(field_missing)}"
            )

        amount = _parse_amount(field_value["amount"], f"{field_path}.amount")
        source = _require_non_empty_string(
            field_value["source"], f"{field_path}.source"
        )
        source_as_of = _parse_iso_date(field_value["as_of"], f"{field_path}.as_of")
        age_days = (research_as_of - source_as_of).days
        max_age_days = freshness_days[field_name]

        if age_days < 0:
            raise ValidationError(
                f"{field_path}.as_of must not be after research as_of "
                f"{research_as_of.isoformat()}"
            )
        if age_days > max_age_days:
            raise ValidationError(
                f"{field_path}.as_of is stale: age_days {age_days} exceeds "
                f"max_age_days {max_age_days}"
            )

        if field_name == SELLING_PRICE_FIELD:
            if amount <= 0:
                raise ValidationError(f"{field_path}.amount must be greater than zero")
        elif amount < 0:
            raise ValidationError(f"{field_path}.amount must not be negative")

        amounts[field_name] = amount
        provenance[field_name] = {
            # Preserve the exact sourced input string. Calculated money fields are
            # rounded below, but rewriting an input here could make the output
            # impossible to reproduce when a sourced amount has sub-cent precision.
            "amount": field_value["amount"],
            "source": source,
            "as_of": field_value["as_of"],
            "age_days": age_days,
            "max_age_days": max_age_days,
        }

    return amounts, provenance


def calculate_unit_economics(document: Any) -> Dict[str, Any]:
    """Validate an input document and return deterministic scenario results."""

    if not isinstance(document, Mapping):
        raise ValidationError("input must be a JSON object")

    missing = _missing_keys(
        document,
        ("market", "currency", "as_of", "freshness_days", "scenarios"),
    )
    if missing:
        raise ValidationError(
            f"input is missing required top-level field(s): {', '.join(missing)}"
        )

    market = _require_non_empty_string(document["market"], "market")
    currency = _require_non_empty_string(document["currency"], "currency")
    research_as_of = _parse_iso_date(document["as_of"], "as_of")
    freshness_days = _validate_freshness_days(document["freshness_days"])

    scenarios = document["scenarios"]
    if not isinstance(scenarios, Mapping):
        raise ValidationError("scenarios must be an object")

    missing_scenarios = _missing_keys(scenarios, REQUIRED_SCENARIOS)
    if missing_scenarios:
        raise ValidationError(
            "scenarios is missing required scenario(s): "
            + ", ".join(missing_scenarios)
        )

    unexpected_scenarios = tuple(
        scenario_name
        for scenario_name in scenarios
        if scenario_name not in REQUIRED_SCENARIOS
    )
    if unexpected_scenarios:
        raise ValidationError(
            "scenarios contains unexpected scenario(s): "
            + ", ".join(unexpected_scenarios)
        )

    scenario_results: Dict[str, Dict[str, Any]] = {}
    for scenario_name in REQUIRED_SCENARIOS:
        amounts, provenance = _validate_scenario(
            scenario_name,
            scenarios[scenario_name],
            research_as_of,
            freshness_days,
        )
        with localcontext() as context:
            context.prec = _working_precision(amounts.values())
            total_variable_cost = sum(
                (amounts[field_name] for field_name in COST_FIELDS),
                Decimal("0"),
            )
            contribution_profit = (
                amounts[SELLING_PRICE_FIELD] - total_variable_cost
            )
            contribution_margin_percent = (
                contribution_profit / amounts[SELLING_PRICE_FIELD]
            ) * Decimal("100")

            scenario_results[scenario_name] = {
                "inputs": provenance,
                "total_variable_cost": _format_fixed(
                    total_variable_cost, MONEY_QUANTUM
                ),
                "contribution_profit": _format_fixed(
                    contribution_profit, MONEY_QUANTUM
                ),
                "contribution_margin_percent": _format_fixed(
                    contribution_margin_percent, PERCENT_QUANTUM
                ),
            }

    return {
        "market": market,
        "currency": currency,
        "as_of": document["as_of"],
        "freshness_days": freshness_days,
        "formula_version": FORMULA_VERSION,
        "scenarios": scenario_results,
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
            "Calculate sourced Amazon FBA unit economics for pessimistic, "
            "base, and optimistic scenarios."
        )
    )
    parser.add_argument("input", type=Path, help="path to a UTF-8 JSON input file")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = calculate_unit_economics(_load_json(args.input))
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
