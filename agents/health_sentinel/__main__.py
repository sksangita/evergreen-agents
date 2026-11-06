"""Demo CLI: python -m agents.health_sentinel 186 104"""

import argparse
import sys
import uuid
from datetime import UTC, datetime

from pydantic import ValidationError

from agents.health_sentinel.agent import HealthSentinel
from core.contracts import VitalKind, VitalReading
from core.llm import get_client
from core.rules.engine import load_rules


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m agents.health_sentinel",
        description="Triage one blood pressure reading. Demo only, not a medical device.",
    )
    parser.add_argument("systolic", type=float)
    parser.add_argument("diastolic", type=float)
    args = parser.parse_args(argv)

    try:
        reading = VitalReading(
            elder_id="demo",
            kind=VitalKind.BLOOD_PRESSURE,
            values={"systolic": args.systolic, "diastolic": args.diastolic},
            unit="mmHg",
            measured_at=datetime.now(UTC),
            source="cli",
        )
    except ValidationError as error:
        problems = "; ".join(e["msg"].removeprefix("Value error, ") for e in error.errors())
        print(f"Invalid reading, no triage given: {problems}", file=sys.stderr)
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
