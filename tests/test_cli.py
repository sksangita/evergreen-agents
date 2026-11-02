import pytest

from agents.health_sentinel.__main__ import main


def test_red_reading_prints_triage_and_escalation(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["186", "104"]) == 0
    out = capsys.readouterr().out
    assert "Triage:     RED" in out
    assert "Escalate:   yes" in out
    assert "bp.crisis" in out


def test_green_reading_does_not_escalate(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["120", "80"]) == 0
    out = capsys.readouterr().out
    assert "Triage:     GREEN" in out
    assert "Escalate:   no" in out


def test_non_numeric_input_is_rejected() -> None:
    with pytest.raises(SystemExit):
        main(["high", "low"])
