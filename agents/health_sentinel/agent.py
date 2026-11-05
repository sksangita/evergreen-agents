"""Health Sentinel: rules decide the triage, the LLM only explains it."""

from agents.health_sentinel.templates import ELDER_FALLBACK
from core.contracts import AgentResult, Triage, VitalReading
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
            fallback=ELDER_FALLBACK[decision.triage],
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


def _caregiver_message(reading: VitalReading, triage: Triage) -> str | None:
    """Built from the reading, not the LLM, so it is always accurate."""
    if triage == Triage.GREEN:
        return None
    systolic = reading.values["systolic"]
    diastolic = reading.values["diastolic"]
    return (
        f"BP {systolic:g}/{diastolic:g} at {reading.measured_at:%H:%M} "
        f"({triage.value.upper()})."
    )
