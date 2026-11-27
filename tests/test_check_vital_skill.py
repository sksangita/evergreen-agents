"""Tests for .claude/skills/check-new-vital/scripts/check_vital.py (Qodo findings on PR #39)."""

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).parent.parent / ".claude/skills/check-new-vital/scripts/check_vital.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_vital", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False
    )


@pytest.mark.parametrize(
    "when",
    ["bpm == 60", "100 < bpm", "bpm != 70", "bpm < 40 or 130 < bpm"],
)
def test_edge_coverage_sees_equality_and_constant_first_rules(when: str) -> None:
    mod = _load()
    mod.RESULTS.clear()
    mod.coverage("heart_rate", [{"id": "r", "when": when}], [{"bpm": 500}], ["bpm"])
    assert any(item.startswith("edges at") for _, item, _ in mod.RESULTS)
    assert not any(s == "OK" for s, _, _ in mod.RESULTS)


def test_rule_without_a_number_is_unchecked_not_silently_skipped() -> None:
    mod = _load()
    mod.RESULTS.clear()
    mod.coverage("heart_rate", [{"id": "r", "when": "bpm < other"}], [], ["bpm"])
    assert [s for s, _, _ in mod.RESULTS] == ["UNCHECKED"]


def test_unchecked_items_do_not_report_pass() -> None:
    mod = _load()
    mod.RESULTS.clear()
    mod.add("OK", "a", "")
    mod.add("UNCHECKED", "b", "")
    assert mod.report(0) == 4  # incomplete, not 0


def test_failures_report_exit_1_and_clean_runs_exit_0() -> None:
    mod = _load()
    mod.RESULTS.clear()
    mod.add("OK", "a", "")
    assert mod.report(0) == 0
    mod.RESULTS.clear()
    mod.add("FAIL", "a", "")
    assert mod.report(0) == 1


def test_rule_with_no_id_and_unverified_source_does_not_crash(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    mod = _load()
    mod.RESULTS.clear()
    broken = (
        "version: 2\nrules:\n  - {vital: heart_rate, when: 'bpm > 100', source: 'x unverified'}\n"
    )
    real_read = mod.read
    monkeypatch.setattr(mod, "read", lambda p: broken if p == mod.THRESHOLDS else real_read(p))
    monkeypatch.setattr(sys, "argv", ["check_vital.py", "heart_rate", "hr", "main"])
    mod.main()
    out = capsys.readouterr().out
    assert "metadata" in out and "FAIL" in out


def test_blood_pressure_uses_its_real_eval_file() -> None:
    mod = _load()
    assert mod.eval_path("blood_pressure") == "evals/triage_cases.yaml"
    assert mod.eval_path("heart_rate") == "evals/heart_rate_cases.yaml"


def test_wrong_subcommand_for_the_vital_fails() -> None:
    result = _run_script("heart_rate", "bp", "main")
    assert result.returncode == 1
    assert "FAIL" in result.stdout and "bp" in result.stdout
    assert "PASS:" not in result.stdout


def test_correct_pair_passes_with_no_failures() -> None:
    # HEAD always exists, even in CI where there is no local `main` branch.
    result = _run_script("heart_rate", "hr", "HEAD")
    assert result.returncode == 0, result.stdout
    assert "FAIL " not in result.stdout.replace("FAIL:", "")


def test_unreadable_base_ref_is_incomplete_not_pass() -> None:
    result = _run_script("heart_rate", "hr", "no-such-ref")
    assert result.returncode == 4
    assert "INCOMPLETE" in result.stdout


def _version_status(
    mod: ModuleType, monkeypatch: pytest.MonkeyPatch, old: str, new: dict[str, object]
) -> str:
    """Run the version guard against a fake base file; return the status it recorded."""
    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout=old, stderr="")
    monkeypatch.setattr(mod, "run", lambda cmd: fake)
    mod.RESULTS.clear()
    mod.check_version("fake-base", new)
    assert len(mod.RESULTS) == 1
    return str(mod.RESULTS[0][0])


_OLD = "version: 2\nrules:\n  - {id: a, vital: heart_rate, when: 'bpm > 100'}\n"
_SAME = [{"id": "a", "vital": "heart_rate", "when": "bpm > 100"}]
_CHANGED = [{"id": "a", "vital": "heart_rate", "when": "bpm > 101"}]


@pytest.mark.parametrize(
    ("version", "rules", "expected"),
    [
        (2, _CHANGED, "FAIL"),  # rule changed, version not raised: the case Qodo asked about
        (3, _CHANGED, "OK"),  # rule changed, version raised
        (2, _SAME, "OK"),  # nothing changed
    ],
)
def test_version_guard_against_a_fake_base(
    monkeypatch: pytest.MonkeyPatch, version: int, rules: list[dict[str, str]], expected: str
) -> None:
    mod = _load()
    status = _version_status(mod, monkeypatch, _OLD, {"version": version, "rules": rules})
    assert status == expected
