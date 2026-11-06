"""Deterministic triage. This module and core/baseline are the only places triage is decided."""

import ast
import operator
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from core.contracts import (
    REQUIRED_VALUES,
    InvalidReadingError,
    Triage,
    VitalKind,
    VitalReading,
    reading_problems,
)

DEFAULT_THRESHOLDS = Path(__file__).parent / "thresholds.yaml"

_SEVERITY = {Triage.GREEN: 0, Triage.AMBER: 1, Triage.RED: 2}

_COMPARE: dict[type[ast.cmpop], Callable[[Any, Any], bool]] = {
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
}

_ALLOWED_NODES = (
    ast.BoolOp, ast.And, ast.Or, ast.Compare, ast.Name, ast.Load, ast.Constant,
    *_COMPARE,
)  # fmt: skip


class Rule(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    version: int
    vital: VitalKind
    when: str = Field(min_length=1)
    triage: Triage
    source: str = Field(min_length=1)

    @field_validator("triage")
    @classmethod
    def _is_a_level(cls, value: Triage) -> Triage:
        if value not in _SEVERITY:
            raise ValueError("a rule must set green, amber or red")
        return value


class TriageDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    triage: Triage
    reasons: list[str]
    rule_version: str


def _parse_condition(expression: str, allowed_names: frozenset[str]) -> ast.expr:
    """Parse comparisons or and/or combinations of comparisons over known values."""
    body = ast.parse(expression, mode="eval").body
    if not isinstance(body, ast.Compare | ast.BoolOp):
        raise ValueError("a condition must be a comparison or and/or of comparisons")
    for node in ast.walk(body):
        if isinstance(node, ast.BoolOp) and any(
            not isinstance(operand, ast.Compare | ast.BoolOp) for operand in node.values
        ):
            raise ValueError("and/or operands must be comparisons or and/or of comparisons")
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"{type(node).__name__} is not allowed in a condition")
        if isinstance(node, ast.Name) and node.id not in allowed_names:
            raise ValueError(f"unknown value {node.id!r}")
        if isinstance(node, ast.Constant) and (
            isinstance(node.value, bool) or not isinstance(node.value, int | float)
        ):
            raise ValueError("only numbers are allowed as constants")
    return body


def _evaluate(node: ast.expr, values: Mapping[str, float]) -> Any:
    match node:
        case ast.BoolOp(op=ast.Or(), values=operands):
            return any(_evaluate(operand, values) for operand in operands)
        case ast.BoolOp(op=ast.And(), values=operands):
            return all(_evaluate(operand, values) for operand in operands)
        case ast.Compare(left=left, ops=ops, comparators=comparators):
            lhs = _evaluate(left, values)
            for op, comparator in zip(ops, comparators, strict=True):
                rhs = _evaluate(comparator, values)
                if not _COMPARE[type(op)](lhs, rhs):
                    return False
                lhs = rhs
            return True
        case ast.Name(id=name):
            return values[name]
        case ast.Constant(value=constant):
            return constant
    raise ValueError(f"cannot evaluate {type(node).__name__}")  # unreachable after parsing


@dataclass(frozen=True)
class RuleSet:
    version: int
    rules: tuple[tuple[Rule, ast.expr], ...]  # each rule with its parsed condition

    @property
    def label(self) -> str:
        return f"thresholds@v{self.version}"


def load_rules(path: Path = DEFAULT_THRESHOLDS) -> RuleSet:
    document = yaml.safe_load(path.read_text())
    compiled: list[tuple[Rule, ast.expr]] = []
    for raw in document["rules"]:
        try:
            rule = Rule.model_validate(raw)
            condition = _parse_condition(rule.when, REQUIRED_VALUES[rule.vital])
        except (ValidationError, ValueError, SyntaxError) as error:
            raise ValueError(f"invalid rule {raw.get('id', '?')!r}: {error}") from error
        compiled.append((rule, condition))
    return RuleSet(version=int(document["version"]), rules=tuple(compiled))


def triage_reading(reading: VitalReading, rules: RuleSet) -> TriageDecision:
    """Return the most severe level among matching rules, or green if none match.

    Raises InvalidReadingError for a reading the rules cannot judge, so "no rule matched"
    never means green for bad data, however the reading was built.
    """
    problems = reading_problems(reading)
    if problems:
        raise InvalidReadingError("; ".join(problems))
    matched = [
        rule
        for rule, condition in rules.rules
        if rule.vital == reading.kind and _evaluate(condition, reading.values)
    ]
    if not matched:
        return TriageDecision(
            triage=Triage.GREEN,
            reasons=["no threshold crossed"],
            rule_version=rules.label,
        )
    worst = max(_SEVERITY[rule.triage] for rule in matched)
    top = [rule for rule in matched if _SEVERITY[rule.triage] == worst]
    shown = ", ".join(f"{name} {value:g}" for name, value in reading.values.items())
    return TriageDecision(
        triage=top[0].triage,
        reasons=[f"{shown}: {rule.when} ({rule.id} v{rule.version})" for rule in top],
        rule_version=rules.label,
    )
