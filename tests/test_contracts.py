from datetime import UTC, datetime, timedelta, timezone, tzinfo

import pytest
from pydantic import ValidationError

from core.contracts import AgentResult, Triage, VitalKind, VitalReading, reading_problems, to_utc


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


def _at(moment: object) -> VitalReading:
    return VitalReading.model_validate(
        {
            "elder_id": "e_001",
            "kind": VitalKind.BLOOD_PRESSURE,
            "values": {"systolic": 120, "diastolic": 80},
            "unit": "mmHg",
            "measured_at": moment,
        }
    )


def test_naive_measured_at_is_rejected() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        _at(datetime(2026, 11, 6, 8, 12))


def test_naive_measured_at_given_as_text_is_rejected() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        _at("2026-11-06T08:12:00")


def test_aware_measured_at_is_accepted() -> None:
    assert _at(datetime(2026, 11, 6, 8, 12, tzinfo=UTC)).measured_at.utcoffset() == timedelta(0)


def test_aware_measured_at_in_another_zone_is_accepted() -> None:
    zone = timezone(timedelta(hours=5, minutes=30))
    assert _at(datetime(2026, 11, 6, 8, 12, tzinfo=zone)).measured_at.utcoffset() == timedelta(
        hours=5, minutes=30
    )


def test_aware_measured_at_given_as_text_is_accepted() -> None:
    assert _at("2026-11-06T08:12:00Z").measured_at.utcoffset() == timedelta(0)


class _NoOffset(tzinfo):
    """A tzinfo that reports no offset: Python treats such a datetime as naive."""

    def utcoffset(self, dt: datetime | None) -> timedelta | None:
        return None


class _BrokenOffset(tzinfo):
    def utcoffset(self, dt: datetime | None) -> timedelta | None:
        raise RuntimeError("cannot compute offset")


@pytest.mark.parametrize(
    "moment",
    [
        datetime(2026, 11, 6, 8, 12, tzinfo=_NoOffset()),
        datetime(2026, 11, 6, 8, 12, tzinfo=_BrokenOffset()),
        None,
        "not a time",
        1_762_416_720,
    ],
    ids=["tzinfo_without_offset", "tzinfo_that_raises", "none", "text", "number"],
)
def test_a_time_that_is_not_a_known_moment_is_reported_never_raised(moment: object) -> None:
    reading = VitalReading.model_construct(
        elder_id="e_001",
        kind=VitalKind.BLOOD_PRESSURE,
        values={"systolic": 120.0, "diastolic": 80.0},
        unit="mmHg",
        measured_at=moment,
    )
    assert any("measured_at" in problem for problem in reading_problems(reading))


_EXTREME_TIMES = [
    datetime(9999, 12, 31, 23, 59, tzinfo=timezone(timedelta(hours=-1))),  # UTC date is year 10000
    datetime(1, 1, 1, 0, 0, tzinfo=timezone(timedelta(hours=1))),  # UTC date is year 0
]
_EXTREME_IDS = ["max_date_west_of_utc", "min_date_east_of_utc"]


@pytest.mark.parametrize("moment", _EXTREME_TIMES, ids=_EXTREME_IDS)
def test_a_time_that_cannot_be_shown_in_utc_is_rejected_at_creation(moment: datetime) -> None:
    with pytest.raises(ValidationError, match="supported date range"):
        _at(moment)


@pytest.mark.parametrize("moment", _EXTREME_TIMES, ids=_EXTREME_IDS)
def test_an_unshowable_time_is_reported_never_raised(moment: datetime) -> None:
    reading = VitalReading.model_construct(
        elder_id="e_001",
        kind=VitalKind.BLOOD_PRESSURE,
        values={"systolic": 120.0, "diastolic": 80.0},
        unit="mmHg",
        measured_at=moment,
    )
    assert any("supported date range" in problem for problem in reading_problems(reading))


@pytest.mark.parametrize(
    "moment",
    [
        datetime(9999, 12, 31, 22, 59, tzinfo=timezone(timedelta(hours=-1))),  # last UTC minute
        datetime(1, 1, 1, 1, 0, tzinfo=timezone(timedelta(hours=1))),  # first UTC hour
        datetime(9999, 12, 31, 23, 59, tzinfo=UTC),
        datetime(1, 1, 1, 0, 0, tzinfo=UTC),
    ],
    ids=["last_minute_west", "first_hour_east", "max_utc", "min_utc"],
)
def test_the_edge_of_the_supported_range_is_still_accepted(moment: datetime) -> None:
    assert _at(moment).measured_at == moment


def test_measured_at_left_unset_is_reported_never_raised() -> None:
    reading = VitalReading.model_construct(
        elder_id="e_001",
        kind=VitalKind.BLOOD_PRESSURE,
        values={"systolic": 120.0, "diastolic": 80.0},
        unit="mmHg",
    )
    assert any("measured_at" in problem for problem in reading_problems(reading))


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


class LyingDatetime(datetime):
    """A datetime subclass whose astimezone() ignores the target zone and returns itself."""

    def astimezone(self, tz: tzinfo | None = None) -> "LyingDatetime":  # type: ignore[override]
        return self


_PLUS_0530 = timezone(timedelta(hours=5, minutes=30))


def test_to_utc_converts_another_zone() -> None:
    converted = to_utc(datetime(2026, 11, 6, 8, 12, tzinfo=_PLUS_0530))
    assert (converted.year, converted.month, converted.day) == (2026, 11, 6)
    assert (converted.hour, converted.minute) == (2, 42)
    assert converted.utcoffset() == timedelta(0)


def test_to_utc_ignores_a_subclass_that_overrides_astimezone() -> None:
    """Qodo finding on PR #21: an override returning self must not skip the conversion."""
    lying = LyingDatetime(2026, 11, 6, 8, 12, tzinfo=_PLUS_0530)
    assert lying.astimezone(UTC) is lying  # the override really does lie
    converted = to_utc(lying)
    assert (converted.hour, converted.minute) == (2, 42)
    assert converted.utcoffset() == timedelta(0)
