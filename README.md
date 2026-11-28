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
  uv run python -m agents.health_sentinel bp 186 104
```

The token limit (`max_completion_tokens`) is 4000 because reasoning models such as `gpt-5-mini`
spend part of it on hidden thinking. If a model still returns no text, the template is shown.

The `openai` provider is **demo-only until the Safety guardrail (#6) exists**: without it, model
text reaches the elder unchecked. The prompt contains the reading values, so use synthetic data only.

Check a synthetic resting heart rate (bpm):

```bash
uv run python -m agents.health_sentinel hr 128
```

## Adding a vital

AGENTS.md rule 5 says a new vital arrives with its rules, units and tests. Use the Claude Code skill
`check-new-vital` ([`SKILL.md`](.claude/skills/check-new-vital/SKILL.md)) to audit a vital. Its first step
runs a script that lists the missing pieces:

```bash
uv run python .claude/skills/check-new-vital/scripts/check_vital.py heart_rate hr main
```

The script's `PASS` is not the result on its own. The skill also compares thresholds with their source and
checks the elder and caregiver wording and the bad-input tests by hand, and reports PASS only if those find no
problem. Changes to `core/rules/` and `thresholds.yaml` still need human review (rule 4).

How the work flows from ticket to `main`, with every gate: [`docs/factory-diagram.md`](docs/factory-diagram.md).
