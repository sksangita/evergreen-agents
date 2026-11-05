from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from core.contracts import Triage, VitalKind, VitalReading
from core.rules.engine import load_rules, triage_reading

CASES = yaml.safe_load((Path(__file__).parent.parent / "evals" / "triage_cases.yaml").read_text())


def _bp(systolic: float, diastolic: float) -> VitalReading:
    return VitalReading(
        elder_id="e_001",
        kind=VitalKind.BLOOD_PRESSURE,
        values={"systolic": systolic, "diastolic": diastolic},
        unit="mmHg",
        measured_at=datetime(2026, 11, 2, 8, 12, tzinfo=UTC),
    )


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_blood_pressure_triage(case: dict[str, Any]) -> None:
    decision = triage_reading(_bp(case["systolic"], case["diastolic"]), load_rules())
    assert decision.triage == Triage(case["expected"])
    assert decision.rule_version == "thresholds@v1"


def test_red_reason_names_the_rule_and_values() -> None:
    decision = triage_reading(_bp(186, 104), load_rules())
    assert decision.reasons == [
        "systolic 186, diastolic 104: systolic >= 180 or diastolic >= 120 (bp.crisis v1)"
    ]


def _write(tmp_path: Path, rule: str) -> Path:
    path = tmp_path / "thresholds.yaml"
    path.write_text(f"version: 1\nrules:\n  - {rule}\n")
    return path


def test_rule_without_source_is_rejected(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        '{id: x, version: 1, vital: blood_pressure, when: "systolic > 1", triage: red}',
    )
    with pytest.raises(ValueError, match="invalid rule 'x'"):
        load_rules(path)


@pytest.mark.parametrize(
    "when", ["__import__('os').system('ls')", "systolic.real > 1", "pulse > 1", "'a' == 'a'"]
)
def test_unsafe_or_unknown_condition_is_rejected(tmp_path: Path, when: str) -> None:
    path = _write(
        tmp_path,
        f'{{id: x, version: 1, vital: blood_pressure, when: "{when}", triage: red, source: s}}',
    )
    with pytest.raises(ValueError, match="invalid rule 'x'"):
        load_rules(path)


def test_shipped_thresholds_load_and_every_rule_is_documented() -> None:
    rules = load_rules()
    assert rules.rules
    for rule, _ in rules.rules:
        assert rule.id and rule.source and rule.version >= 1


def test_triage_code_does_not_depend_on_the_llm() -> None:
    rules_dir = Path(__file__).parent.parent / "core" / "rules"
    for source in rules_dir.glob("*.py"):
        assert "llm" not in source.read_text().lower(), source.name
