#!/usr/bin/env python3
"""Sourced unit-cost ledger and piecewise price solver. No live fee/tax defaults."""
import argparse
import copy
import json
import sys
from decimal import Decimal, ROUND_CEILING, localcontext
from pathlib import Path

try:
    from .unit_economics import (ValidationError, _parse_amount, _parse_iso_date,
                                 _format_fixed, _load_json, summarize_cost_amounts)
except ImportError:
    from unit_economics import (ValidationError, _parse_amount, _parse_iso_date,
                                _format_fixed, _load_json, summarize_cost_amounts)

VERSION = "pickscout-cost-pricing-v1"
ZERO, CENT, ONE = Decimal("0"), Decimal("0.01"), Decimal("1")
CATEGORIES = ("product", "packaging", "inbound", "import_duty", "placement",
              "fulfillment", "storage", "referral", "advertising", "losses", "fx",
              "overhead", "launch", "income_tax")
STATUSES = {"actual", "quoted", "rule", "budget", "unknown", "not_applicable"}


def text(value, path):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(path + " must be a non-empty string")
    return value


def number(value, path, positive=False):
    n = _parse_amount(value, path)
    if n < 0 or (positive and n == 0):
        raise ValidationError(path + " must be " + ("positive" if positive else "non-negative"))
    return n


def provenance(item, path, as_of):
    text(item.get("source"), path + ".source")
    if _parse_iso_date(item.get("as_of"), path + ".as_of") > as_of:
        raise ValidationError(path + ".as_of is after the model date")


def money(n):
    return _format_fixed(n, CENT)


def normalize(costs, currency, exchange, as_of):
    if not isinstance(costs, list) or not costs:
        raise ValidationError("costs must be a non-empty list")
    result, ids, covered = [], set(), {}
    for i, raw in enumerate(costs):
        path = "costs[" + str(i) + "]"
        if not isinstance(raw, dict):
            raise ValidationError(path + " must be an object")
        r = copy.deepcopy(raw)
        cid = text(r.get("id"), path + ".id")
        if cid in ids:
            raise ValidationError("duplicate cost id: " + cid)
        ids.add(cid)
        text(r.get("label"), path + ".label")
        text(r.get("category"), path + ".category")
        if r.get("kind") not in {"amount", "rate"} or r.get("status") not in STATUSES:
            raise ValidationError(path + " has invalid kind/status")
        provenance(r, path, as_of)
        covers = r.get("covers", [cid])
        if not isinstance(covers, list) or not covers or len(set(covers)) != len(covers):
            raise ValidationError(path + ".covers must contain unique strings")
        for token in covers:
            text(token, path + ".covers")
        r["covers"] = covers
        if r["status"] in {"unknown", "not_applicable"}:
            text(r.get("reason"), path + ".reason")
            if r.get("value") is not None:
                raise ValidationError(path + ".value must be null for unknown/not_applicable")
            r["normalized"] = None if r["status"] == "unknown" else ZERO
        else:
            value = number(r.get("value"), path + ".value")
            for token in covers:
                if token in covered:
                    raise ValidationError("overlapping cost coverage: " + token + " in " + covered[token] + "/" + cid)
                covered[token] = cid
            if r["kind"] == "amount":
                cur = text(r.get("currency", currency), path + ".currency")
                if cur not in exchange:
                    raise ValidationError("missing currency conversion: " + cur)
                quantity = number(r.get("quantity", "1"), path + ".quantity", True)
                units = number(r.get("allocation_units", "1"), path + ".allocation_units", True)
                r["normalized"] = value * quantity / units / exchange[cur]
            else:
                if r["category"] == "income_tax":
                    raise ValidationError("income_tax accepts an explicit amount allocation, not a revenue tax rate")
                if value >= 1:
                    raise ValidationError(path + ".value rate must be below 1")
                r["normalized"] = value
                r["minimum"] = number(r.get("minimum_amount", "0"), path + ".minimum_amount")
        result.append(r)
    return result


def amount_at(row, price):
    if row["normalized"] is None:
        return None
    if row["status"] == "not_applicable":
        return ZERO
    if row["kind"] == "rate":
        return max(row["normalized"] * price, row["minimum"])
    return row["normalized"]


def scope_of(rows):
    addressed, unknown = set(), set()
    for r in rows:
        cats = {r["category"]} | (set(r["covers"]) & set(CATEGORIES))
        if r["status"] == "unknown":
            unknown |= cats
        else:
            addressed |= cats
    return {"unassessed_categories": sorted(set(CATEGORIES) - addressed | unknown),
            "unpriced_items": [r["id"] for r in rows if r["status"] == "unknown"],
            "budget_items": [r["id"] for r in rows if r["status"] == "budget"],
            "meaning": "列示成本口径；未计项不是零，不声明全部实际成本或最终净利"}


def ledger(rows, price):
    lines, operating, tax, ad, product = [], [], [], ZERO, ZERO
    income_rows = [r for r in rows if r["category"] == "income_tax"]
    for r in rows:
        v = amount_at(r, price)
        lines.append({"id": r["id"], "label": r["label"], "category": r["category"],
                      "status": r["status"], "kind": r["kind"], "covers": r["covers"],
                      "amount": None if v is None else money(v),
                      "amount_unrounded": None if v is None else str(v),
                      "source": r["source"], "as_of": r["as_of"]})
        if v is None:
            continue
        if r["category"] == "income_tax":
            tax.append(v)
        else:
            operating.append(v)
        if r["category"] == "advertising":
            ad += v
        if r["category"] == "product":
            product += v
    total = summarize_cost_amounts(price, operating)
    tax_known = bool(income_rows) and all(r["status"] != "unknown" for r in income_rows)
    tax_amount = sum(tax, ZERO) if tax_known else None
    return {"price": money(price), "lines": lines, "included_operating_cost": money(total["cost"]),
            "operating_remainder": money(total["profit"]),
            "operating_margin_percent": money(total["margin"] * 100),
            "income_tax_allocation": None if tax_amount is None else money(tax_amount),
            "after_income_tax_subtotal": None if tax_amount is None else money(total["profit"] - tax_amount),
            "income_tax_note": "有分摊时仅为列示成本税后小计；没有完整成本与税务确认，不叫净利",
            "before_advertising_remainder": money(total["profit"] + ad),
            "maximum_tacos_at_model_break_even": str((total["profit"] + ad) / price),
            "maximum_product_cost_at_model_break_even": money(total["profit"] + product),
            "headroom_note": "上限为当前列示口径、所得税前；负数表示即使广告/货款为零仍未保本，不是可用预算",
            "scope": scope_of(rows)}


def bands_for(case, currency, exchange, as_of):
    raw_bands = case.get("price_bands", [{"id": "static-cost-model", "min_price": "0.01", "max_price_exclusive": None}])
    if not isinstance(raw_bands, list) or not raw_bands:
        raise ValidationError("price_bands must be a non-empty list")
    bands, ids = [], set()
    for b in raw_bands:
        bid = text(b.get("id"), "price_band.id")
        if bid in ids:
            raise ValidationError("duplicate price band id")
        ids.add(bid)
        lower = number(b.get("min_price"), "min_price", True)
        upper = None if b.get("max_price_exclusive") is None else number(b["max_price_exclusive"], "max_price_exclusive", True)
        if upper is not None and upper <= lower:
            raise ValidationError("empty price band")
        costs = copy.deepcopy(case["costs"])
        byid = {c["id"]: c for c in costs}
        for cid, patch in b.get("overrides", {}).items():
            if cid not in byid:
                raise ValidationError("unknown override cost id: " + cid)
            if not isinstance(patch, dict) or set(patch) - {"value", "status", "source", "as_of", "currency", "quantity", "allocation_units", "minimum_amount", "reason"}:
                raise ValidationError("invalid band override fields")
            provenance(patch, "override." + cid, as_of)
            if "status" not in patch:
                raise ValidationError("band override must declare status")
            byid[cid].update(patch)
        bands.append({"id": bid, "lower": lower, "upper": upper,
                      "rows": normalize(costs, currency, exchange, as_of)})
    bands.sort(key=lambda b: b["lower"])
    for prev, cur in zip(bands, bands[1:]):
        if prev["upper"] is None or cur["lower"] < prev["upper"]:
            raise ValidationError("overlapping price bands")
    return bands


def solve_price(bands, target_profit=ZERO, target_margin=ZERO):
    """Split explicit fee bands further at minimum-percentage-fee breakpoints."""
    answers = []
    for b in bands:
        rows = [r for r in b["rows"] if r["category"] != "income_tax" and r["status"] not in {"unknown", "not_applicable"}]
        if not rows:
            continue
        cuts = {b["lower"]}
        for r in rows:
            if r["kind"] == "rate" and r["normalized"] > 0:
                edge = r["minimum"] / r["normalized"]
                if edge > b["lower"] and (b["upper"] is None or edge < b["upper"]):
                    cuts.add(edge)
        cuts = sorted(cuts)
        for i, lower in enumerate(cuts):
            upper = cuts[i+1] if i+1 < len(cuts) else b["upper"]
            c, rate = ZERO, ZERO
            for r in rows:
                if r["kind"] == "amount":
                    c += r["normalized"]
                elif lower * r["normalized"] < r["minimum"]:
                    c += r["minimum"]
                else:
                    rate += r["normalized"]
            denominator = ONE - rate - target_margin
            if denominator < 0 or (denominator == 0 and c + target_profit > 0):
                continue
            raw = lower if denominator == 0 else max(lower, (c + target_profit) / denominator)
            candidate = raw.quantize(CENT, rounding=ROUND_CEILING)
            if upper is not None and candidate >= upper:
                continue
            subtotal = summarize_cost_amounts(candidate, (amount_at(r, candidate) for r in rows))
            if subtotal["profit"] + Decimal("1e-40") < target_profit + target_margin * candidate:
                candidate += CENT
            if upper is not None and candidate >= upper:
                continue
            answers.append((candidate, b["id"], c, rate))
    if not answers:
        return {"price": None, "reason": "声明费档内没有可行解", "scope": "列示成本、所得税前"}
    p, bid, c, rate = min(answers)
    return {"price": money(p), "band": bid, "amount_cost_in_segment": str(c),
            "active_revenue_rate_in_segment": str(rate), "scope": "列示成本、所得税前；按成本覆盖清单解释",
            "cost_coverage": scope_of(next(b["rows"] for b in bands if b["id"] == bid))}


def calculate_pricing(document):
    if not isinstance(document, dict):
        raise ValidationError("input must be an object")
    for key in ("market", "currency", "selling_unit"):
        text(document.get(key), key)
    as_of = _parse_iso_date(document.get("as_of"), "as_of")
    currency = document["currency"]
    cases = document.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValidationError("cases must be a non-empty list")
    output, ids = [], set()
    with localcontext() as context:
        context.prec = 50
        exchange = {currency: ONE}
        for cur, entry in document.get("currency_per_reporting_unit", {}).items():
            provenance(entry, "exchange." + cur, as_of)
            exchange[cur] = number(entry.get("value"), "exchange." + cur, True)
            if cur == currency and exchange[cur] != 1:
                raise ValidationError("reporting currency exchange must equal 1")
        for case in cases:
            if not isinstance(case, dict):
                raise ValidationError("each case must be an object")
            cid = text(case.get("id"), "case.id")
            if cid in ids:
                raise ValidationError("duplicate case id")
            ids.add(cid)
            normalize(case.get("costs"), currency, exchange, as_of)
            bands = bands_for(case, currency, exchange, as_of)
            prices = case.get("prices")
            if not isinstance(prices, list) or not prices:
                raise ValidationError("prices must be a non-empty list")
            ledgers = []
            for entry in prices:
                provenance(entry, "price", as_of)
                if entry.get("status") not in STATUSES - {"unknown", "not_applicable"}:
                    raise ValidationError("price status must specify an actual/quoted/rule/budget value")
                price = number(entry.get("value"), "price.value", True)
                if price != price.quantize(CENT):
                    raise ValidationError("selling prices must use 0.01 increments; costs may retain sub-cent precision")
                b = next((b for b in bands if b["lower"] <= price and (b["upper"] is None or price < b["upper"])), None)
                if b is None:
                    raise ValidationError("price has no declared cost band: " + str(price))
                item = ledger(b["rows"], price)
                item.update(band=b["id"], price_input=entry)
                ledgers.append(item)
            targets = case.get("targets", {})
            solutions = {"break_even": solve_price(bands)}
            if "unit_profit" in targets:
                solutions["unit_profit"] = solve_price(bands, target_profit=number(targets["unit_profit"], "targets.unit_profit"))
            if "margin" in targets:
                m = number(targets["margin"], "targets.margin")
                if m >= 1:
                    raise ValidationError("target margin must be below 1")
                solutions["margin"] = solve_price(bands, target_margin=m)
            output.append({"id": cid, "inputs": case, "prices": ledgers, "target_prices": solutions})
    return {"formula_version": VERSION, "market": document["market"], "currency": currency,
            "as_of": document["as_of"], "selling_unit": document["selling_unit"],
            "currency_inputs": document.get("currency_per_reporting_unit", {}), "cases": output,
            "notice": "税费和成本范围由列示输入决定；本工具不认定税率、市场可成交价或交易授权。"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        result = calculate_pricing(_load_json(args.input))
    except (ValidationError, KeyError, TypeError) as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
