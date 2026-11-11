"""LLM providers. The fake one is the default; `OpenAIProvider` is opt-in (demo only until the
guardrail exists). Anthropic and Bedrock providers come later."""

import time
from typing import Any, Protocol

import httpx


class LLMProvider(Protocol):
    def complete(self, prompt: str, *, timeout: float) -> str:
        """Return the model's reply. A real provider must enforce `timeout` itself
        (for example with an HTTP client timeout), so a stalled call ends by itself."""
        ...


class FakeProvider:
    """Offline and deterministic. Can be told to be slow or to fail, to test fallbacks."""

    def __init__(
        self,
        reply: str = "This is a calm explanation from the fake model.",
        delay_seconds: float = 0.0,
        error: Exception | None = None,
    ) -> None:
        self._reply = reply
        self._delay_seconds = delay_seconds
        self._error = error

    def complete(self, prompt: str, *, timeout: float) -> str:
        if self._delay_seconds:
            time.sleep(self._delay_seconds)
        if self._error is not None:
            raise self._error
        return self._reply


OPENAI_BASE_URL = "https://api.openai.com"
# Reasoning models count their hidden thinking against this limit, so it is kept generous.
OPENAI_MAX_COMPLETION_TOKENS = 1000


class OpenAIProvider:
    """OpenAI Chat Completions over httpx. It raises on any failure; `LLMClient` turns that
    into the template fallback. Nothing is logged here, and the key is never put in an error."""

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        base_url: str = OPENAI_BASE_URL,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key or not model:
            raise ValueError("OpenAIProvider needs a non-empty api_key and model")
        self._api_key = api_key
        self._model = model
        self._url = f"{base_url.rstrip('/')}/v1/chat/completions"
        self._http = httpx.Client(transport=transport)

    def complete(self, prompt: str, *, timeout: float) -> str:
        response = self._http.post(
            self._url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "max_completion_tokens": OPENAI_MAX_COMPLETION_TOKENS,
            },
            timeout=httpx.Timeout(timeout),  # connect, read, write and pool all end by themselves
        )
        response.raise_for_status()
        return _reply_text(response)


def _reply_text(response: httpx.Response) -> str:
    try:
        data: Any = response.json()
        content = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as error:
        raise ValueError("malformed response from the model") from error
    if not isinstance(content, str):
        raise ValueError("model reply has no text")
    return content
