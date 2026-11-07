# AGENTS.md

Instructions for coding agents and reviewers working in this repository.

## Project

evergreen-agents is a multi-agent system that helps elders stay safe and connected. Today it triages one blood pressure reading as green, amber or red and explains the result in plain language. Later it adds a Companion (daily check-ins with memory), Interests, an Orchestrator, a Safety guardrail and an Escalation service.

It is a hackathon prototype and **not a medical device**. All data is synthetic. Never add real personal or health data.

## Setup and verification

```bash
make install   # uv sync
make lint      # ruff + mypy (strict)
make test      # pytest, runs offline against the fake LLM
uv run python -m agents.health_sentinel 186 104   # demo: expect RED, escalate yes
```

A change is done when `make lint` and `make test` both pass. Tests must never need network access or an API key.

## Layout

- `core/contracts.py`: shared schemas (`VitalReading`, `AgentResult`, `Triage`)
- `core/rules/`: `thresholds.yaml` and the engine that decides triage
- `core/llm/`: the only LLM client, with prompts, timeout and fallback
- `agents/health_sentinel/`: reading -> rules -> explanation -> `AgentResult`
- `evals/`, `tests/`: triage cases and tests

## Rules

### 1. Rules decide triage, the LLM only explains it (the "No Model Verdicts" rule)

- **Applies to:** anything that sets `triage` or `requires_escalation`. Only `core/rules` (and `core/baseline` when it exists) may do that. Code in `agents/` reads the decision and never changes it. All model access goes through `core/llm`, the only place allowed to import an LLM or embedding SDK. Every call has a timeout, a template fallback and a test for that fallback. Text for an elder must not be shown unless it passes the guardrail checks, once those exist.
- **Why:** triage must be reproducible and testable without a model, and a model outage must never hide an alert. Model text can be wrong or contradict the decision, as when a reply like "Everything is fine!" came back for a red reading.

### 2. Bad input is rejected, never green (the "No Silent Green" rule)

- **Applies to:** `core/contracts.py` and `core/rules/`. A reading that cannot be judged (wrong unit, NaN, zero, negative, unexpected keys) must raise an error when it is created. A rule condition must be a comparison, or `and`/`or` of comparisons, never a bare number or name, and anything else is rejected when the file loads. "No rule matched" is only valid for a reading that was validated first. A reading that cannot be judged always raises `InvalidReadingError`, and `reading_problems()` and `triage_reading` must never fail with any other error, whatever the input (including readings built with `model_construct`).
- **Why:** green is the answer that looks like good news. In a safety system, data the rules do not understand must fail loudly. Qodo's one high-severity finding on PR #1 was a kPa reading of about 180/120 mmHg being triaged green, and a rule such as `when: "1"` would match every reading.

### 3. No personal data in logs or prompts

- **Applies to:** every `logging` call, `core/llm/prompts.py` and the audit log. Log ids and `trace_id` only, never health values, names or phone numbers. Prompts contain only the triage level and the reasons built from known measurement names.
- **Why:** health data is sensitive and logs travel. Free-text keys or values copied into a prompt can also compete with the safety instructions.

### 4. Safety changes carry tests, sources and human review

- **Applies to:** `core/rules/`, `thresholds.yaml`, `core/baseline/`, `core/guardrail/` and `core/escalation/`. Every change adds or updates a case in `evals/` or `tests/`, including the edges (exactly at a threshold, just below it). Every threshold has an `id`, `version` and `source`. These paths need human review before merging.
- **Why:** a wrong threshold or a missed edge case is a missed alert, and any alert must be traceable to a specific rule and its source.

### 5. A new vital arrives with its rules, units and tests

- **Applies to:** adding anything to `VitalKind` (glucose, SpO2, heart rate).
- **Why:** a vital with no rules matches nothing and would silently triage green, which is the "No Silent Green" problem again. Add its allowed unit, its required values, its thresholds with sources, and edge-case tests in the same PR.

### 6. Times carry a date and a timezone

- **Applies to:** `VitalReading.measured_at` and any text shown to an elder or caregiver that says when something happened. `measured_at` must be timezone-aware, and a naive datetime is rejected when the reading is created. A displayed time includes the date and zone, for example `2026-11-06 08:12 UTC`. New code that compares or counts time, such as the escalation service's 15-minute acknowledgement window and the daily digest, uses timezone-aware values.
- **Why:** "08:12" does not say which day or which clock. A caregiver judging how urgent an alert is, and the escalation timers, both depend on knowing exactly when a reading was taken. Qodo's review of PR #1 flagged a caregiver message that showed a UTC clock time that looked like local time.

## Known gaps (please do not flag these)

- Only the fake LLM provider exists. The Anthropic provider comes later.
- The amber rule is a single reading at or above 140/90. The spec's "3 readings in 7 days" needs history and comes later.
- Thresholds are demo values and the cited sources are not yet verified.
- The Safety guardrail, escalation service, API and web app are not built yet.
- Rule 6 is not yet true of the code: `measured_at` accepts naive datetimes and caregiver messages show the clock time only. Tracked in #13.

## Automated runs

A ticket labelled `ready-for-agent` starts `.github/workflows/agent.yml`, which runs Codex on that one ticket. When Qodo reviews the resulting PR, `.github/workflows/agent-fix.yml` runs Codex on its findings.

- The agent takes one ticket per run, on a branch named `agent/ticket-<n>`, and opens a PR that links the ticket and quotes its acceptance criteria. The model runs with a read-only token and produces a patch. A separate job holds the write token and pushes it.
- It runs `make lint` and `make test`, then checks every acceptance criterion by hand, including the ticket's failure case, and reports the commands and results in the PR.
- It investigates Qodo's findings and fixes only confirmed problems. It gets at most 2 fix rounds, tracked with the `fix-round-1` and `fix-round-2` labels.
- If it is stuck, or the patch is empty or touches `.github/`, it adds the `agent-blocked` label and stops with a comment.
- It never merges, never pushes to `main`, and never edits `.github/`. A person decides whether to merge.
- Fallback: a local poller running `claude -p` can replace the GitHub trigger if the hosted run misbehaves.
