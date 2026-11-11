"""OpenAIProvider, tested offline with httpx.MockTransport and one local socket server."""

import json
import logging
import re
import socket
import threading
import time
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from core.llm import LLMClient, LLMResponse, OpenAIProvider, get_client

FALLBACK = "template text"
KEY = "sk-test-SECRET-key-123"


def _provider(handler: Callable[[httpx.Request], httpx.Response]) -> OpenAIProvider:
    return OpenAIProvider(KEY, "test-model", transport=httpx.MockTransport(handler))


def _ok(text: object) -> Callable[[httpx.Request], httpx.Response]:
    body = {"choices": [{"message": {"content": text}}]}
    return lambda request: httpx.Response(200, json=body)


def _complete(provider: OpenAIProvider, timeout: float = 2.0) -> LLMResponse:
    return LLMClient(provider, timeout_seconds=timeout).complete(
        "a prompt", fallback=FALLBACK, trace_id="tr_1"
    )


def test_success_returns_the_model_text() -> None:
    response = _complete(_provider(_ok("Please sit and rest.")))
    assert response.text == "Please sit and rest."
    assert not response.used_fallback


def test_request_shape_and_auth() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]})

    _complete(_provider(handler))
    request = seen[0]
    body = json.loads(request.content)
    assert str(request.url) == "https://api.openai.com/v1/chat/completions"
    assert request.headers["Authorization"] == f"Bearer {KEY}"
    assert body["model"] == "test-model"
    assert body["messages"] == [{"role": "user", "content": "a prompt"}]


def test_http_500_falls_back() -> None:
    response = _complete(_provider(lambda request: httpx.Response(500, text="boom")))
    assert response.text == FALLBACK
    assert response.used_fallback


def test_read_timeout_falls_back() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    response = _complete(_provider(handler))
    assert response.text == FALLBACK
    assert response.used_fallback


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(200, text="not json {"),
        lambda request: httpx.Response(200, json={"choices": []}),
        lambda request: httpx.Response(200, json={"error": "nope"}),
        _ok(None),  # no text in the reply
        _ok(["a", "list"]),
    ],
    ids=["not-json", "no-choices", "no-choices-key", "null-content", "non-string-content"],
)
def test_malformed_response_falls_back(handler: Callable[[httpx.Request], httpx.Response]) -> None:
    response = _complete(_provider(handler))
    assert response.text == FALLBACK
    assert response.used_fallback


@pytest.mark.parametrize("empty", ["", "   \n"])
def test_empty_content_falls_back(empty: str) -> None:
    response = _complete(_provider(_ok(empty)))
    assert response.text == FALLBACK
    assert response.used_fallback


def test_timeout_reaches_the_http_call() -> None:
    seen: list[dict[str, float | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.extensions["timeout"])
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]})

    _provider(handler).complete("p", timeout=1.5)
    assert seen[0]["connect"] == 1.5
    assert seen[0]["read"] == 1.5


def test_client_gives_the_provider_a_shorter_timeout_than_its_own() -> None:
    seen: list[dict[str, float | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.extensions["timeout"])
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]})

    _complete(_provider(handler), timeout=5.0)
    read_timeout = seen[0]["read"]
    assert read_timeout is not None and read_timeout < 5.0


def test_provider_enforces_its_own_timeout_on_a_real_socket() -> None:
    """A server that accepts and never answers: the HTTP call itself must end, not just the
    thread the client abandoned."""
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    accepted: list[socket.socket] = []
    threading.Thread(target=lambda: accepted.append(server.accept()[0]), daemon=True).start()
    provider = OpenAIProvider(KEY, "m", base_url=f"http://127.0.0.1:{server.getsockname()[1]}")
    started = time.monotonic()
    try:
        with pytest.raises(httpx.TimeoutException):
            provider.complete("p", timeout=0.3)
    finally:
        server.close()
        for connection in accepted:
            connection.close()
    assert time.monotonic() - started < 3.0


def test_key_is_not_in_logs_or_error_messages(caplog: pytest.LogCaptureFixture) -> None:
    def failing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="bad key")

    with caplog.at_level(logging.DEBUG):
        _complete(_provider(_ok("a secret reply")))
        _complete(_provider(failing))
        with pytest.raises(httpx.HTTPStatusError) as error:
            _provider(failing).complete("a prompt", timeout=1.0)
    assert KEY not in caplog.text
    assert KEY not in str(error.value)
    assert "a prompt" not in caplog.text
    assert "a secret reply" not in caplog.text
    assert "tr_1" in caplog.text


def test_empty_key_or_model_is_rejected() -> None:
    with pytest.raises(ValueError):
        OpenAIProvider("", "m")
    with pytest.raises(ValueError):
        OpenAIProvider("k", "")


# --- get_client wiring -------------------------------------------------------------------


def test_get_client_builds_the_openai_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", KEY)
    monkeypatch.setenv("LLM_MODEL_SMALL", "test-model")
    assert isinstance(get_client()._provider, OpenAIProvider)


@pytest.mark.parametrize(
    ("key", "model", "named"),
    [(None, "m", "OPENAI_API_KEY"), ("k", None, "LLM_MODEL_SMALL"), ("", "", "OPENAI_API_KEY")],
)
def test_missing_config_fails_when_the_client_is_built(
    monkeypatch: pytest.MonkeyPatch, key: str | None, model: str | None, named: str
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    for name, value in (("OPENAI_API_KEY", key), ("LLM_MODEL_SMALL", model)):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=named):
        get_client()


def test_missing_config_never_falls_back_to_the_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError):
        get_client()


def test_error_never_contains_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", KEY)
    monkeypatch.delenv("LLM_MODEL_SMALL", raising=False)
    with pytest.raises(ValueError) as error:
        get_client()
    assert KEY not in str(error.value)


# --- rule 1: httpx only inside core/llm --------------------------------------------------


def test_httpx_is_only_imported_inside_core_llm() -> None:
    root = Path(__file__).resolve().parent.parent
    pattern = re.compile(r"^\s*(import|from)\s+httpx\b", re.MULTILINE)
    offenders = [
        str(path.relative_to(root))
        for folder in ("core", "agents")
        for path in (root / folder).rglob("*.py")
        if "llm" not in path.relative_to(root).parts and pattern.search(path.read_text())
    ]
    assert offenders == []
