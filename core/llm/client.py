"""The one LLM client. Every call has a timeout and a template fallback."""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass

from core.llm.providers import FakeProvider, LLMProvider

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class LLMResponse:
    text: str
    used_fallback: bool


class LLMClient:
    def __init__(
        self, provider: LLMProvider, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    ) -> None:
        self._provider = provider
        self._timeout_seconds = timeout_seconds

    def complete(self, prompt: str, *, fallback: str, trace_id: str) -> LLMResponse:
        """Return the model's reply, or `fallback` if it times out, errors or replies empty.

        Only the trace id, outcome and latency are logged, never the prompt or reply.
        """
        started = time.monotonic()
        outcome = "ok"
        text = fallback
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            reply = executor.submit(self._provider.complete, prompt).result(
                timeout=self._timeout_seconds
            )
            if reply.strip():
                text = reply
            else:
                outcome = "empty"
        except FutureTimeout:
            outcome = "timeout"
        except Exception:  # any provider failure must fall back, never raise
            outcome = "error"
        finally:
            executor.shutdown(wait=False, cancel_futures=True)  # don't wait on a hung call
        latency_ms = round((time.monotonic() - started) * 1000)
        logger.info("llm_call trace_id=%s outcome=%s latency_ms=%d", trace_id, outcome, latency_ms)
        return LLMResponse(text=text, used_fallback=outcome != "ok")


def get_client() -> LLMClient:
    """Build the client from the LLM_PROVIDER environment variable (default: fake)."""
    name = os.environ.get("LLM_PROVIDER", "fake")
    if name == "fake":
        return LLMClient(FakeProvider())
    raise ValueError(f"unsupported LLM_PROVIDER {name!r} (only 'fake' exists so far)")
