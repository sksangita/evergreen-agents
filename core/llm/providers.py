"""LLM providers. Real providers (anthropic, bedrock) are added next to the fake one later."""

import time
from typing import Protocol


class LLMProvider(Protocol):
    def complete(self, prompt: str) -> str: ...


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

    def complete(self, prompt: str) -> str:
        if self._delay_seconds:
            time.sleep(self._delay_seconds)
        if self._error is not None:
            raise self._error
        return self._reply
