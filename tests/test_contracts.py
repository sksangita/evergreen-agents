from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from core.contracts import AgentResult, Triage, VitalKind, VitalReading


def _reading(values: dict[str, float]) -> VitalReading:
    return VitalReading(
        elder_id="e_001",
        kind=VitalKind.BLOOD_PRESSURE,
        values=values,
        unit="mmHg",
        measured_at=datetime(2026, 11, 2, 8, 12, tzinfo=UTC),
    )


def test_valid_blood_pressure_reading() -> None:
    reading = _reading({"systolic": 186, "diastolic": 104})
    assert reading.values["systolic"] == 186
    assert reading.source == "manual"


def test_blood_pressure_missing_diastolic_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _reading({"systolic": 186})


def test_agent_result_round_trips_and_is_immutable() -> None:
    result = AgentResult(
        agent="health_sentinel",
        elder_id="e_001",
        trace_id="tr_1",
        triage=Triage.RED,
        reasons=["systolic 186 >= 180 (bp.crisis v1)"],
        message_for_elder="Please sit and rest.",
        requires_escalation=True,
    )
    assert AgentResult.model_validate_json(result.model_dump_json()) == result
    with pytest.raises(ValidationError):
        result.triage = Triage.GREEN  # type: ignore[misc]
