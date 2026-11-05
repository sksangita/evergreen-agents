import logging
from datetime import UTC, datetime

import pytest

from agents.health_sentinel import HealthSentinel
from agents.health_sentinel.templates import ELDER_FALLBACK
from core.contracts import Triage, VitalKind, VitalReading
from core.llm import FakeProvider, LLMClient
from core.llm.prompts import explain_triage_prompt
from core.rules.engine import load_rules


def _bp(systolic: float, diastolic: float) -> VitalReading:
    return VitalReading(
        elder_id="e_001",
        kind=VitalKind.BLOOD_PRESSURE,
        values={"systolic": systolic, "diastolic": diastolic},
        unit="mmHg",
        measured_at=datetime(2026, 11, 2, 8, 12, tzinfo=UTC),
    )


def _agent(provider: FakeProvider, timeout: float = 1.0) -> HealthSentinel:
    return HealthSentinel(load_rules(), LLMClient(provider, timeout_seconds=timeout))


def test_red_reading_gives_full_result_with_llm_explanation() -> None:
    result = _agent(FakeProvider(reply="Please sit and rest.")).assess(_bp(186, 104), "tr_1")
    assert result.agent == "health_sentinel"
    assert result.elder_id == "e_001"
    assert result.trace_id == "tr_1"
    assert result.triage == Triage.RED
    assert result.requires_escalation
    assert result.rule_version == "thresholds@v1"
    assert result.reasons
    assert result.message_for_elder == "Please sit and rest."
    assert result.message_for_caregiver == "BP 186/104 at 08:12 (RED)."


@pytest.mark.parametrize(
    "provider",
    [
        FakeProvider(error=RuntimeError("model down")),
        FakeProvider(delay_seconds=1.0),
        FakeProvider(reply=""),
    ],
    ids=["error", "timeout", "empty"],
)
def test_red_reading_still_gives_full_result_when_llm_fails(provider: FakeProvider) -> None:
    result = _agent(provider, timeout=0.05).assess(_bp(186, 104), "tr_1")
    assert result.triage == Triage.RED
    assert result.requires_escalation
    assert result.message_for_elder == ELDER_FALLBACK[Triage.RED]
    assert result.message_for_caregiver == "BP 186/104 at 08:12 (RED)."


def test_llm_text_cannot_change_triage() -> None:
    result = _agent(FakeProvider(reply="Everything is fine, no need to worry!")).assess(
        _bp(186, 104), "tr_1"
    )
    assert result.triage == Triage.RED
    assert result.requires_escalation


def test_amber_does_not_escalate_now() -> None:
    result = _agent(FakeProvider()).assess(_bp(150, 85), "tr_1")
    assert result.triage == Triage.AMBER
    assert not result.requires_escalation
    assert result.message_for_caregiver == "BP 150/85 at 08:12 (AMBER)."


def test_green_has_no_caregiver_message() -> None:
    result = _agent(FakeProvider()).assess(_bp(120, 80), "tr_1")
    assert result.triage == Triage.GREEN
    assert not result.requires_escalation
    assert result.message_for_caregiver is None


def test_prompt_carries_the_rule_reasons_and_the_safety_instructions() -> None:
    prompt = explain_triage_prompt("red", ["bp.crisis matched"])
    assert "red" in prompt
    assert "bp.crisis matched" in prompt
    assert "Do not name any medical condition" in prompt
    assert "e_001" not in prompt


@pytest.mark.parametrize(
    ("systolic", "diastolic", "expected"),
    [(120, 80, Triage.GREEN), (150, 85, Triage.AMBER), (186, 104, Triage.RED)],
)
def test_every_level_uses_its_template_when_llm_fails(
    systolic: float, diastolic: float, expected: Triage
) -> None:
    result = _agent(FakeProvider(error=RuntimeError("down"))).assess(
        _bp(systolic, diastolic), "tr_1"
    )
    assert result.triage == expected
    assert result.message_for_elder == ELDER_FALLBACK[expected]


def test_no_health_values_in_logs(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        _agent(FakeProvider()).assess(_bp(186, 104), "tr_1")
    assert "186" not in caplog.text
    assert "104" not in caplog.text
    assert "e_001" not in caplog.text
