import logging
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

import pytest

from core.llm import FakeProvider, LLMClient, LLMResponse, get_client

FALLBACK = "template text"


def _complete(provider: FakeProvider, timeout: float = 1.0) -> LLMResponse:
    client = LLMClient(provider, timeout_seconds=timeout)
    return client.complete("a prompt", fallback=FALLBACK, trace_id="tr_1")


def test_fake_provider_reply_is_returned() -> None:
    response = _complete(FakeProvider(reply="hello"))
    assert response.text == "hello"
    assert not response.used_fallback


def test_timeout_falls_back_without_waiting_for_the_model() -> None:
    started = time.monotonic()
    response = _complete(FakeProvider(delay_seconds=1.0), timeout=0.05)
    assert response.text == FALLBACK
    assert response.used_fallback
    assert time.monotonic() - started < 0.5


def test_provider_error_falls_back() -> None:
    response = _complete(FakeProvider(error=RuntimeError("boom")))
    assert response.text == FALLBACK
    assert response.used_fallback


def test_empty_reply_falls_back() -> None:
    response = _complete(FakeProvider(reply="   "))
    assert response.text == FALLBACK
    assert response.used_fallback


def test_log_has_trace_id_but_not_prompt_or_reply(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="core.llm.client"):
        _complete(FakeProvider(reply="secret reply"))
    assert "tr_1" in caplog.text
    assert "a prompt" not in caplog.text
    assert "secret reply" not in caplog.text


def test_default_client_uses_the_fake_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    response = get_client().complete("p", fallback=FALLBACK, trace_id="tr_2")
    assert not response.used_fallback


def test_unknown_provider_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    with pytest.raises(ValueError, match="unsupported LLM_PROVIDER"):
        get_client()


def test_provider_receives_a_timeout_shorter_than_the_client_timeout() -> None:
    seen: list[float] = []

    class Recording:
        def complete(self, prompt: str, *, timeout: float) -> str:
            seen.append(timeout)
            return "ok"

    LLMClient(Recording(), timeout_seconds=2.0).complete("p", fallback=FALLBACK, trace_id="tr_3")
    assert seen == [pytest.approx(1.6)]


def test_stalled_calls_do_not_pile_up_threads() -> None:
    calls = 0
    lock = threading.Lock()

    class StallsTwice:
        def complete(self, prompt: str, *, timeout: float) -> str:
            nonlocal calls
            with lock:
                calls += 1
                stall = calls <= 2
            if stall:
                time.sleep(0.5)
            return "fine"

    before = threading.active_count()
    client = LLMClient(StallsTwice(), timeout_seconds=0.05, max_in_flight=2)
    responses = [client.complete("p", fallback=FALLBACK, trace_id=f"tr_{n}") for n in range(6)]
    assert all(r.used_fallback for r in responses)
    assert calls == 2  # the other four were refused, not started
    assert threading.active_count() - before <= 2
    time.sleep(0.7)  # the stalled calls end and free their slots
    assert client.complete("p", fallback=FALLBACK, trace_id="tr_after").text == "fine"


def test_stalled_provider_does_not_delay_process_exit() -> None:
    """Rule 1: a call that outlives its timeout must not keep the process alive."""
    stall_seconds = 8.0
    script = textwrap.dedent(
        f"""
        from core.llm import FakeProvider, LLMClient
        client = LLMClient(FakeProvider(delay_seconds={stall_seconds}), timeout_seconds=0.2)
        response = client.complete("p", fallback="template", trace_id="tr_exit")
        assert response.used_fallback
        """
    )
    repo_root = Path(__file__).resolve().parent.parent
    started = time.monotonic()
    subprocess.run([sys.executable, "-c", script], cwd=repo_root, check=True, timeout=30)
    assert time.monotonic() - started < stall_seconds / 2
