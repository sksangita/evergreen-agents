"""One real call to OpenAI. Skipped unless explicitly enabled, so `make test` and CI stay offline.

Run it with:
RUN_LIVE_LLM=1 OPENAI_API_KEY=... LLM_MODEL_SMALL=gpt-5-mini \\
  uv run pytest tests/test_openai_live.py
"""

import os

import pytest

from core.llm import OpenAIProvider

pytestmark = pytest.mark.skipif(
    not (os.environ.get("RUN_LIVE_LLM") == "1" and os.environ.get("OPENAI_API_KEY")),
    reason="live check: set RUN_LIVE_LLM=1 and OPENAI_API_KEY to run",
)


def test_live_call_returns_text() -> None:
    provider = OpenAIProvider(
        os.environ["OPENAI_API_KEY"], os.environ.get("LLM_MODEL_SMALL", "gpt-5-mini")
    )
    reply = provider.complete("Reply with the single word: ready", timeout=30.0)
    assert reply.strip()
