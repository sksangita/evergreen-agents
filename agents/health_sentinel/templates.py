"""Fixed messages used when the LLM is unavailable. Safe to show without any model."""

from core.contracts import Triage

ELDER_FALLBACK: dict[Triage, str] = {
    Triage.GREEN: "Thank you for checking. This reading did not cross any of our alert levels.",
    Triage.AMBER: (
        "Your blood pressure is a little higher than ideal. "
        "Please rest, and mention it to your caregiver or doctor."
    ),
    Triage.RED: (
        "Your blood pressure reading is very high. Please sit down and rest, and tell your "
        "caregiver or doctor right away. If you feel unwell, call 112."
    ),
}
