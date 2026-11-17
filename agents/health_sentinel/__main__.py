"""Demo CLI: python -m agents.health_sentinel bp 186 104; python -m agents.health_sentinel hr 128"""

import argparse
import sys
import uuid
from datetime import UTC, datetime

from agents.health_sentinel.agent import HealthSentinel
from core.contracts import InvalidReadingError, VitalKind, VitalReading
from core.llm import get_client
from core.rules.engine import load_rules


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m agents.health_sentinel",
        description=(
            "Triage one blood pressure or resting heart rate reading. "
            "Demo only, not a medical device."
        ),
    )
    subparsers = parser.add_subparsers(dest="vital", required=True)
    bp = subparsers.add_parser("bp", help="blood pressure in mmHg")
    bp.add_argument("systolic", type=float)
    bp.add_argument("diastolic", type=float)
    hr = subparsers.add_parser("hr", help="resting heart rate in bpm")
    hr.add_argument("bpm", type=float)
    args = parser.parse_args(argv)

    try:
        reading = VitalReading(
            elder_id="demo",
            kind=VitalKind.BLOOD_PRESSURE if args.vital == "bp" else VitalKind.HEART_RATE,
            values=(
                {"systolic": args.systolic, "diastolic": args.diastolic}
                if args.vital == "bp" else {"bpm": args.bpm}
            ),
            unit="mmHg" if args.vital == "bp" else "bpm",
            measured_at=datetime.now(UTC),
            source="cli",
        )
    except InvalidReadingError as error:
        print(f"Invalid reading, no triage given: {error}", file=sys.stderr)
        return 2
    trace_id = f"tr_{uuid.uuid4().hex[:8]}"
    result = HealthSentinel(load_rules(), get_client()).assess(reading, trace_id)

    print(f"Triage:     {result.triage.value.upper()}")
    print(f"Escalate:   {'yes' if result.requires_escalation else 'no'}")
    print(f"Reasons:    {'; '.join(result.reasons)}")
    print(f"To elder:   {result.message_for_elder}")
    print(f"To carer:   {result.message_for_caregiver or '-'}")
    print(f"Rules:      {result.rule_version}   Trace: {result.trace_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
