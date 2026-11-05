"""Shared schemas. Agents exchange these types, never free-form strings."""

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


class VitalReading(BaseModel):
    model_config = ConfigDict(frozen=True)

    elder_id: str
    kind: VitalKind
    values: dict[str, float]
    unit: str
    measured_at: datetime
    source: str = "manual"

    @model_validator(mode="after")
    def _has_required_values(self) -> Self:
        missing = REQUIRED_VALUES[self.kind] - self.values.keys()
        if missing:
            raise ValueError(f"{self.kind} reading is missing {sorted(missing)}")
        return self


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
