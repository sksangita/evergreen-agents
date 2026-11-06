"""Shared schemas. Agents exchange these types, never free-form strings."""

import math
from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator


class Triage(StrEnum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"
    NONE = "none"  # non-health agents


class VitalKind(StrEnum):
    BLOOD_PRESSURE = "blood_pressure"


# Value names each kind must carry, referenced by name in thresholds.yaml rules.
REQUIRED_VALUES: dict[VitalKind, frozenset[str]] = {
    VitalKind.BLOOD_PRESSURE: frozenset({"systolic", "diastolic"}),
}


# The only unit each kind's thresholds are written in. Other units are rejected, not converted.
REQUIRED_UNIT: dict[VitalKind, str] = {
    VitalKind.BLOOD_PRESSURE: "mmHg",
}


class VitalReading(BaseModel):
    model_config = ConfigDict(frozen=True)

    elder_id: str
    kind: VitalKind
    values: dict[str, float]
    unit: str
    measured_at: datetime
    source: str = "manual"

    @model_validator(mode="after")
    def _can_be_judged(self) -> Self:
        problems = reading_problems(self)
        if problems:
            raise ValueError("; ".join(problems))
        return self


class InvalidReadingError(ValueError):
    """A reading the rules cannot judge. Raised instead of returning a triage."""


def reading_problems(reading: VitalReading) -> list[str]:
    """Why a reading cannot be judged, or an empty list if it can.

    Used when a reading is created and again before triage, because a reading built
    with `model_construct` skips creation checks.
    """
    # model_construct can leave any field unset or wrongly typed, so read defensively.
    # Whatever the input, report problems; never raise anything but InvalidReadingError.
    kind = getattr(reading, "kind", None)
    if kind not in REQUIRED_UNIT:
        return [f"unsupported vital kind {str(kind)!r}"]
    values = getattr(reading, "values", None)
    if not isinstance(values, dict):
        return [f"{kind} reading has no measurements"]

    problems: list[str] = []
    required_unit = REQUIRED_UNIT[kind]
    unit = getattr(reading, "unit", None)
    if unit != required_unit:
        problems.append(f"{kind} reading must be in {required_unit}, got {unit!r}")
    names = {str(name) for name in values}
    missing = REQUIRED_VALUES[kind] - names
    if missing:
        problems.append(f"{kind} reading is missing {sorted(missing)}")
    unexpected = names - REQUIRED_VALUES[kind]
    if unexpected:
        problems.append(f"{kind} reading has unexpected measurements {sorted(unexpected)}")
    for name, value in sorted(values.items(), key=lambda item: str(item[0])):
        if isinstance(value, bool) or not isinstance(value, int | float):
            problems.append(f"{name} must be a number, got {type(value).__name__}")
        elif not math.isfinite(value) or value <= 0:
            problems.append(f"{name} must be a positive number, got {value}")
    return problems


class AgentResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent: str
    elder_id: str
    trace_id: str
    triage: Triage
    reasons: list[str]
    message_for_elder: str
    message_for_caregiver: str | None = None
    requires_escalation: bool
    rule_version: str | None = None
    signals: dict[str, float] | None = None  # Companion wellbeing scores
