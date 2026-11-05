import logging
import time

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
