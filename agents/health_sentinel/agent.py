"""Health Sentinel: rules decide the triage, the LLM only explains it."""

from collections.abc import Callable
from datetime import datetime

from agents.health_sentinel.templates import ELDER_FALLBACK_BY_KIND
from core.contracts import AgentResult, Triage, VitalKind, VitalReading, to_utc
from core.llm import LLMClient
from core.llm.prompts import explain_triage_prompt
from core.rules.engine import RuleSet, triage_reading

AGENT_NAME = "health_sentinel"


class HealthSentinel:
    def __init__(self, rules: RuleSet, llm: LLMClient) -> None:
        self._rules = rules
        self._llm = llm

    def assess(self, reading: VitalReading, trace_id: str) -> AgentResult:
        # 1. Triage is fixed here, before any model call. Nothing below can change it.
        decision = triage_reading(reading, self._rules)

        # 2. The LLM only words the explanation. On any failure the template is used.
        response = self._llm.complete(
            explain_triage_prompt(decision.triage.value, decision.reasons),
            fallback=ELDER_FALLBACK_BY_KIND[reading.kind][decision.triage],
            trace_id=trace_id,
        )

        return AgentResult(
            agent=AGENT_NAME,
            elder_id=reading.elder_id,
            trace_id=trace_id,
            triage=decision.triage,
            reasons=decision.reasons,
            message_for_elder=response.text,
            message_for_caregiver=_caregiver_message(reading, decision.triage),
            requires_escalation=decision.triage == Triage.RED,
            rule_version=decision.rule_version,
        )


# One entry per VitalKind (a test enforces it), so no vital reuses another vital's format.
_MEASUREMENT_TEXT: dict[VitalKind, Callable[[VitalReading], str]] = {
    VitalKind.BLOOD_PRESSURE: lambda r: f"BP {r.values['systolic']:g}/{r.values['diastolic']:g}",
    VitalKind.HEART_RATE: lambda r: f"Heart rate {r.values['bpm']:g} bpm",
}


def _caregiver_message(reading: VitalReading, triage: Triage) -> str | None:
    """Built from the reading, not the LLM, so it is always accurate."""
    if triage == Triage.GREEN:
        return None
    measurement = _MEASUREMENT_TEXT[reading.kind](reading)
    return f"{measurement} at {_utc_text(reading.measured_at)} ({triage.value.upper()})."


def _utc_text(moment: datetime) -> str:
    """Date, time and zone, always in UTC so the zone is never blank or ambiguous (rule 6)."""
    return f"{to_utc(moment):%Y-%m-%d %H:%M} UTC"
