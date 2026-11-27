import json

import pytest

from agents.health_sentinel.__main__ import main


def test_red_reading_prints_triage_and_escalation(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["bp", "186", "104"]) == 0
    out = capsys.readouterr().out
    assert "Triage:     RED" in out
    assert "Escalate:   yes" in out
    assert "bp.crisis" in out


def test_green_reading_does_not_escalate(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["bp", "120", "80"]) == 0
    out = capsys.readouterr().out
    assert "Triage:     GREEN" in out
    assert "Escalate:   no" in out


def test_non_numeric_input_is_rejected() -> None:
    with pytest.raises(SystemExit):
        main(["bp", "high", "low"])


@pytest.mark.parametrize("args", [["nan", "80"], ["120", "inf"], ["0", "80"], ["-5", "80"]])
def test_invalid_reading_fails_loudly_and_gives_no_triage(
    args: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["bp", *args]) == 2
    captured = capsys.readouterr()
    assert "Invalid reading" in captured.err
    assert "Triage" not in captured.out
    assert "GREEN" not in captured.out


@pytest.mark.parametrize(("bpm", "triage", "escalate"),
                         [("128", "AMBER", "no"), ("140", "RED", "yes"),
                          ("35", "RED", "yes"), ("80", "GREEN", "no")])
def test_heart_rate_cli(
    bpm: str, triage: str, escalate: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["hr", bpm]) == 0
    out = capsys.readouterr().out
    assert f"Triage:     {triage}" in out
    assert f"Escalate:   {escalate}" in out
    assert "To carer:   -" in out if triage == "GREEN" else "Heart rate" in out


@pytest.mark.parametrize("bpm", ["0", "-5", "nan", "inf"])
def test_invalid_heart_rate_cli(bpm: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["hr", bpm]) == 2
    captured = capsys.readouterr()
    assert "bpm must be a positive number" in captured.err
    assert not captured.out


@pytest.mark.parametrize("args", [[], ["186", "104"]])
def test_cli_requires_subcommand(args: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    assert "usage:" in capsys.readouterr().err


def test_json_flag_prints_one_json_object_with_the_decision(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["--json", "bp", "186", "104"]) == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["triage"] == "red"
    assert data["requires_escalation"] is True
    assert data["rule_version"].startswith("thresholds@v")
    assert "Triage:" not in out


def test_json_flag_works_for_heart_rate(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--json", "hr", "80"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["triage"] == "green"
    assert data["requires_escalation"] is False


def test_json_flag_invalid_reading_gives_no_json_and_exit_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["--json", "bp", "0", "80"]) == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert "Invalid reading" in captured.err
