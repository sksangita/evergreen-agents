from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from agents.health_sentinel import HealthSentinel
from agents.health_sentinel.templates import ELDER_FALLBACK_BY_KIND
from core.contracts import InvalidReadingError, Triage, VitalKind, VitalReading
from core.llm import FakeProvider, LLMClient
from core.rules.engine import load_rules, triage_reading

CASES = yaml.safe_load((Path(__file__).parent.parent / "evals/heart_rate_cases.yaml").read_text())


def _hr(bpm: float) -> VitalReading:
    return VitalReading(
        elder_id="demo",
        kind=VitalKind.HEART_RATE,
        values={"bpm": bpm},
        unit="bpm",
        measured_at=datetime(2026, 11, 17, 8, 12, tzinfo=UTC),
    )


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_heart_rate_triage(case: dict[str, Any]) -> None:
    decision = triage_reading(_hr(case["bpm"]), load_rules())
    assert decision.triage == Triage(case["expected"])
    assert decision.rule_version == "thresholds@v2"


def test_every_vital_kind_has_rules() -> None:
    assert {rule.vital for rule, _ in load_rules().rules} == set(VitalKind)


@pytest.mark.parametrize(
    ("values", "unit", "reason"),
    [
        ({"bpm": 80}, "Hz", "must be in bpm"),
        ({}, "bpm", "missing"),
        ({"bpm": 80, "extra": 1}, "bpm", "unexpected"),
        *[
            ({"bpm": bad}, "bpm", "positive number")
            for bad in [0, -5, float("nan"), float("inf"), float("-inf")]
        ],
    ],
)
def test_invalid_heart_rate_is_rejected_at_creation_and_triage(
    values: dict[str, float], unit: str, reason: str
) -> None:
    data = {**_hr(80).model_dump(), "values": values, "unit": unit}
    with pytest.raises(ValidationError, match=reason):
        VitalReading.model_validate(data)
    with pytest.raises(ValidationError, match=reason):
        VitalReading(**data)
    with pytest.raises(InvalidReadingError, match=reason):
        triage_reading(VitalReading.model_construct(**data), load_rules())


@pytest.mark.parametrize(
    ("bpm", "expected"),
    [(80, Triage.GREEN), (128, Triage.AMBER), (140, Triage.RED), (35, Triage.RED)],
)
@pytest.mark.parametrize("model_down", [False, True])
def test_heart_rate_full_result(bpm: float, expected: Triage, model_down: bool) -> None:
    provider = FakeProvider(error=RuntimeError("down") if model_down else None)
    result = HealthSentinel(load_rules(), LLMClient(provider)).assess(_hr(bpm), "tr_hr")
    assert result.triage == expected
    assert result.requires_escalation == (expected == Triage.RED)
    assert result.message_for_caregiver == (
        None
        if expected == Triage.GREEN
        else f"Heart rate {bpm:g} bpm at 2026-11-17 08:12 UTC ({expected.value.upper()})."
    )
    if model_down:
        assert result.message_for_elder == ELDER_FALLBACK_BY_KIND[VitalKind.HEART_RATE][expected]
        if expected != Triage.GREEN:
            # Qodo High on PR #23: the fallback must name the vital that was measured.
            assert "heart rate" in result.message_for_elder.lower()
            assert "blood pressure" not in result.message_for_elder.lower()


def test_every_vital_kind_has_an_elder_fallback_for_every_level() -> None:
    for kind in VitalKind:
        assert set(ELDER_FALLBACK_BY_KIND[kind]) == {Triage.GREEN, Triage.AMBER, Triage.RED}


def test_heart_rate_requires_aware_time() -> None:
    data = _hr(128).model_dump()
    assert VitalReading.model_validate(data).measured_at.tzinfo == UTC
    data["measured_at"] = datetime(2026, 11, 17, 8, 12)
    with pytest.raises(ValidationError, match="timezone"):
        VitalReading.model_validate(data)
