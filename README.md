# evergreen-agents

Agent-based support for elders. Built for the Qodo Hackathon (Nov 2 – Dec 2, 2026).

**Not a medical device. All data is synthetic.**

```bash
make install   # set up the environment
make test      # run tests
make lint      # ruff + mypy
```

## Choosing the LLM provider

The model only words the explanation. Rules decide triage, and any model failure falls back to a
fixed template.

| Variable | Meaning |
|---|---|
| `LLM_PROVIDER` | `fake` (default, offline) or `openai` |
| `OPENAI_API_KEY` | required when `LLM_PROVIDER=openai` |
| `LLM_MODEL_SMALL` | model name for the explanation, for example `gpt-5-mini` |
| `LLM_REASONING_EFFORT` | optional: `none`, `minimal`, `low`, `medium`, `high`, `xhigh` or `max`. Sent only when set. Lower effort uses fewer hidden tokens and answers faster. A model that does not accept the value gets a 400 and the template is shown. |

```bash
LLM_PROVIDER=openai OPENAI_API_KEY=... LLM_MODEL_SMALL=gpt-5-mini \
  uv run python -m agents.health_sentinel 186 104
```

The token limit (`max_completion_tokens`) is 4000 because reasoning models such as `gpt-5-mini`
spend part of it on hidden thinking. If a model still returns no text, the template is shown.

The `openai` provider is **demo-only until the Safety guardrail (#6) exists**: without it, model
text reaches the elder unchecked. The prompt contains the reading values, so use synthetic data only.
