"""The one LLM client. Every call has a timeout and a template fallback."""

import logging
import os
import queue
import threading
import time
from dataclasses import dataclass

from core.llm.providers import FakeProvider, LLMProvider, OpenAIProvider

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 5.0
# The provider gets a shorter timeout than the client waits for, so a real provider's own
# timeout ends its call before the client gives up.
PROVIDER_TIMEOUT_FRACTION = 0.8
# A stalled provider call cannot be killed, so the number running at once is capped. Past the
# cap `complete` returns the fallback immediately instead of starting another thread.
DEFAULT_MAX_IN_FLIGHT = 4


@dataclass(frozen=True)
class LLMResponse:
    text: str
    used_fallback: bool


class LLMClient:
    def __init__(
        self,
        provider: LLMProvider,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_in_flight: int = DEFAULT_MAX_IN_FLIGHT,
    ) -> None:
        self._provider = provider
        self._timeout_seconds = timeout_seconds
        self._slots = threading.BoundedSemaphore(max_in_flight)

    def complete(self, prompt: str, *, fallback: str, trace_id: str) -> LLMResponse:
        """Return the model's reply, or `fallback` if it times out, errors or replies empty.

        The provider call runs on a daemon thread, so a stalled call cannot keep the process
        from exiting. Only the trace id, outcome and latency are logged, never the prompt
        or reply.
        """
        started = time.monotonic()
        outcome = "ok"
        text = fallback
        try:
            reply = self._call_provider(prompt)
            if reply is None:
                outcome = "busy"
            elif reply.strip():
                text = reply
            else:
                outcome = "empty"
        except queue.Empty:
            outcome = "timeout"
        except Exception:  # any provider failure must fall back, never raise
            outcome = "error"
        latency_ms = round((time.monotonic() - started) * 1000)
        logger.info("llm_call trace_id=%s outcome=%s latency_ms=%d", trace_id, outcome, latency_ms)
        return LLMResponse(text=text, used_fallback=outcome != "ok")

    def _call_provider(self, prompt: str) -> str | None:
        """Run the provider on a daemon thread. None means no free slot (too many stalled)."""
        if not self._slots.acquire(blocking=False):
            return None
        results: queue.Queue[tuple[str | None, Exception | None]] = queue.Queue(maxsize=1)
        provider_timeout = self._timeout_seconds * PROVIDER_TIMEOUT_FRACTION

        def run() -> None:
            try:
                results.put((self._provider.complete(prompt, timeout=provider_timeout), None))
            except Exception as error:
                results.put((None, error))
            finally:
                self._slots.release()  # freed only when the call really ends

        try:
            threading.Thread(target=run, daemon=True, name="llm-call").start()
        except BaseException:
            self._slots.release()
            raise
        reply, error = results.get(timeout=self._timeout_seconds)
        if error is not None:
            raise error
        return reply or ""


def get_client() -> LLMClient:
    """Build the client from LLM_PROVIDER: `fake` (default) or `openai` (needs OPENAI_API_KEY
    and LLM_MODEL_SMALL; LLM_REASONING_EFFORT is optional). A missing or invalid setting fails
    here, never silently falls back to the fake."""
    name = os.environ.get("LLM_PROVIDER", "fake")
    if name == "fake":
        return LLMClient(FakeProvider())
    if name == "openai":
        missing = [v for v in ("OPENAI_API_KEY", "LLM_MODEL_SMALL") if not os.environ.get(v)]
        if missing:
            raise ValueError(f"LLM_PROVIDER=openai needs {' and '.join(missing)} to be set")
        return LLMClient(
            OpenAIProvider(
                os.environ["OPENAI_API_KEY"],
                os.environ["LLM_MODEL_SMALL"],
                reasoning_effort=os.environ.get("LLM_REASONING_EFFORT") or None,
            )
        )
    raise ValueError(f"unsupported LLM_PROVIDER {name!r} (expected 'fake' or 'openai')")
