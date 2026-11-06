from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from core.contracts import AgentResult, Triage, VitalKind, VitalReading


def _reading(values: dict[str, float], unit: str = "mmHg") -> VitalReading:
    return VitalReading(
        elder_id="e_001",
        kind=VitalKind.BLOOD_PRESSURE,
        values=values,
        unit=unit,
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


def test_blood_pressure_in_mmhg_is_accepted() -> None:
    assert _reading({"systolic": 120, "diastolic": 80}, unit="mmHg").unit == "mmHg"


@pytest.mark.parametrize("unit", ["kPa", "mmhg", "", "mm Hg"])
def test_blood_pressure_in_another_unit_is_rejected(unit: str) -> None:
    # 24/16 kPa is about 180/120 mmHg. It must raise, never reach triage as green.
    with pytest.raises(ValidationError, match="must be in mmHg"):
        _reading({"systolic": 24, "diastolic": 16}, unit=unit)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"), 0.0, -5.0])
@pytest.mark.parametrize("field", ["systolic", "diastolic"])
def test_non_finite_zero_or_negative_value_is_rejected(field: str, bad: float) -> None:
    values = {"systolic": 120.0, "diastolic": 80.0, field: bad}
    with pytest.raises(ValidationError, match="must be a positive number"):
        _reading(values)


def test_normal_reading_is_still_accepted() -> None:
    assert _reading({"systolic": 120, "diastolic": 80}).values["diastolic"] == 80


def test_unexpected_measurement_is_rejected() -> None:
    with pytest.raises(ValidationError, match="unexpected measurements"):
        _reading({"systolic": 120, "diastolic": 80, "untrusted_note": 1})
