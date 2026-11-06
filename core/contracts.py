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
    problems: list[str] = []
    required_unit = REQUIRED_UNIT[reading.kind]
    if reading.unit != required_unit:
        problems.append(f"{reading.kind} reading must be in {required_unit}, got {reading.unit!r}")
    missing = REQUIRED_VALUES[reading.kind] - reading.values.keys()
    if missing:
        problems.append(f"{reading.kind} reading is missing {sorted(missing)}")
    for name, value in sorted(reading.values.items()):
        if not math.isfinite(value) or value <= 0:
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
