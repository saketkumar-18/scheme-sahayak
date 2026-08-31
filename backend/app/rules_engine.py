"""Scheme Sahayak — rules engine.

Deterministic eligibility evaluation over a small rules DSL:
  {"field": <profile_field>, "op": <op>, "value": <value>, "note": <text>}
Supported ops: eq, ne, lte, gte, lt, gt, in, range, between_ages.
Groups: {"any_of": [rule, ...], "logic": "at_least_one"}.
Unknown profile fields are treated as None → rule fails as "not_provided".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class RuleOutcome:
    field: Optional[str]
    op: Optional[str]
    expected: Any
    actual: Any
    passed: bool
    note: str = ""
    reason_code: str = "pass"          # pass | fail_value | not_provided | group
    missing: bool = False


@dataclass
class SchemeResult:
    scheme_id: str
    name: str
    category: str
    benefit: str
    matched: bool
    confidence: str                    # full | partial | missing_info
    passed_rules: list[RuleOutcome] = field(default_factory=list)
    failed_rules: list[RuleOutcome] = field(default_factory=list)
    missing_rules: list[RuleOutcome] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        total = len(self.passed_rules) + len(self.failed_rules) + len(self.missing_rules)
        if total == 0:
            return 0.0
        return len(self.passed_rules) / total


def _get(profile: dict[str, Any], key: str) -> Any:
    return profile.get(key)


def _eval_single(profile: dict[str, Any], rule: dict[str, Any]) -> RuleOutcome:
    key = rule.get("field")
    op = rule.get("op")
    expected = rule.get("value")
    actual = _get(profile, key)
    note = rule.get("note", "")

    if key is None or op is None:
        return RuleOutcome(key, op, expected, actual, False, note, "fail_value")

    if actual is None:
        return RuleOutcome(key, op, expected, None, False, note, "not_provided", missing=True)

    try:
        if op == "eq":
            passed = actual == expected
        elif op == "ne":
            passed = actual != expected
        elif op == "lte":
            passed = float(actual) <= float(expected)
        elif op == "lt":
            passed = float(actual) < float(expected)
        elif op == "gte":
            passed = float(actual) >= float(expected)
        elif op == "gt":
            passed = float(actual) > float(expected)
        elif op == "in":
            passed = actual in expected
        elif op == "range":
            lo, hi = expected
            passed = lo <= float(actual) <= hi
        else:
            passed = False
    except (TypeError, ValueError):
        return RuleOutcome(key, op, expected, actual, False, note, "fail_value")

    return RuleOutcome(key, op, expected, actual, passed, note, "pass" if passed else "fail_value")


def _eval_group(profile: dict[str, Any], group: dict[str, Any]) -> RuleOutcome:
    """Evaluate {"any_of": [...]} group: passes when at least one member passes."""
    members = group.get("any_of", [])
    outcomes = [_eval_rule(profile, m) for m in members]
    passed = any(o.passed for o in outcomes)
    missing = all(o.missing for o in outcomes) and bool(outcomes)
    note = " | ".join(o.note for o in outcomes if o.note)
    return RuleOutcome(
        field="+".join(str(o.field) for o in outcomes),
        op="any_of",
        expected="at_least_one",
        actual=any(o.passed for o in outcomes),
        passed=passed,
        note=note,
        reason_code="group",
        missing=missing,
    )


def _eval_rule(profile: dict[str, Any], rule: dict[str, Any]) -> RuleOutcome:
    if "any_of" in rule:
        return _eval_group(profile, rule)
    return _eval_single(profile, rule)


def evaluate_scheme(profile: dict[str, Any], scheme: dict[str, Any]) -> SchemeResult:
    rules = scheme.get("rules", [])
    result = SchemeResult(
        scheme_id=scheme["id"],
        name=scheme.get("name", scheme["id"]),
        category=scheme.get("category", "general"),
        benefit=scheme.get("benefit", ""),
        matched=False,
        confidence="missing_info",
    )
    for rule in rules:
        outcome = _eval_rule(profile, rule)
        if outcome.passed:
            result.passed_rules.append(outcome)
        elif outcome.missing:
            result.missing_rules.append(outcome)
        else:
            result.failed_rules.append(outcome)

    if result.failed_rules:
        result.confidence = "excluded"
        result.blockers = [o.note or f"{o.field} not satisfied" for o in result.failed_rules]
    elif result.missing_rules:
        result.confidence = "missing_info"
        result.reasons = [o.note for o in result.passed_rules if o.note]
        result.blockers = [
            f"Please provide: {o.field}" + (f" — {o.note}" if o.note else "")
            for o in result.missing_rules
        ]
    else:
        result.matched = True
        result.confidence = "full"
        result.reasons = [o.note for o in result.passed_rules if o.note]
    return result


def match_all(profile: dict[str, Any], schemes: list[dict[str, Any]]) -> list[SchemeResult]:
    results = [evaluate_scheme(profile, s) for s in schemes]
    # Sort: matched first, then by score desc
    def sort_key(r: SchemeResult):
        order = {"full": 0, "missing_info": 1, "excluded": 2}
        return (order.get(r.confidence, 3), -r.score, r.name)
    results.sort(key=sort_key)
    return results


def result_to_dict(r: SchemeResult) -> dict[str, Any]:
    def outcome_dict(o: RuleOutcome) -> dict[str, Any]:
        return {
            "field": o.field,
            "op": o.op,
            "expected": o.expected,
            "actual": o.actual,
            "note": o.note,
        }
    return {
        "scheme_id": r.scheme_id,
        "name": r.name,
        "category": r.category,
        "benefit": r.benefit,
        "matched": r.matched,
        "confidence": r.confidence,
        "score": round(r.score, 3),
        "matched_criteria": [outcome_dict(o) for o in r.passed_rules],
        "missing_info": [outcome_dict(o) for o in r.missing_rules],
        "blockers": r.blockers,
    }
