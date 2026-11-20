"""Fixed messages used when the LLM is unavailable. Safe to show without any model."""

from core.contracts import Triage, VitalKind

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

HEART_RATE_ELDER_FALLBACK: dict[Triage, str] = {
    Triage.GREEN: ELDER_FALLBACK[Triage.GREEN],
    Triage.AMBER: (
        "Your heart rate is a little higher than ideal. "
        "Please rest, and mention it to your caregiver or doctor."
    ),
    Triage.RED: (
        "Your heart rate reading is very high or very low. Please sit down and rest, and tell "
        "your caregiver or doctor right away. If you feel unwell, call 112."
    ),
}

# One entry per VitalKind, so a fallback never describes a different vital than the one measured.
ELDER_FALLBACK_BY_KIND: dict[VitalKind, dict[Triage, str]] = {
    VitalKind.BLOOD_PRESSURE: ELDER_FALLBACK,
    VitalKind.HEART_RATE: HEART_RATE_ELDER_FALLBACK,
}
