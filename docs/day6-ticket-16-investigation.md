# Day 6: investigating ticket #16 before building it

Ticket: [#16 Add an OpenAI provider to core/llm (opt-in, offline-tested)](https://github.com/sksangita/evergreen-agents/issues/16)
Original wording is kept verbatim in the issue body (unchanged so far).
Revision investigated: `main` @ `a12f363` (Qodo's indexed revision matches local HEAD).

## Method

Qodo Agentic Toolbox CLI 2.2.0, Codebase Wisdom skill 1.1.8 (`qodo read codebase grep|read-file`,
`qodo read cross-repo relations`), with the important claims re-checked against local files and by
running code. Qodo's pull-request tools (`stats`, `similar`, `by-file`) returned
`MT-UPSTREAM-DOWN` on every attempt (3 retries), so PR history is **not** covered. `git log` was
used instead.

## Questions and answers

| # | Question | Answer | Evidence | Status |
|---|---|---|---|---|
| 1 | What can we reuse? | `LLMClient` already turns any provider exception, timeout or empty reply into the template and logs only trace id, outcome and latency. A provider only has to **raise** on bad status or malformed JSON. It does not need its own catch-all. | `core/llm/client.py:44-52` (empty -> `outcome="empty"`, `except Exception` -> `"error"`), `:55-56` (logging) | Verified |
| 2 | What else is affected? | Only one production caller of `get_client()`, and `HealthSentinel` takes an `LLMClient`, so the agent needs no change. `get_client()`'s error message says "only 'fake' exists so far", and `tests/test_llm.py:57-59` matches `unsupported LLM_PROVIDER`, so that prefix must stay. | grep: `agents/health_sentinel/__main__.py:12,39`, `agents/health_sentinel/agent.py:13`, `core/llm/client.py:58-63`, `tests/test_llm.py:57-59` | Verified |
| 3 | Is "Dependencies: None" true? | **No.** #15 changes the provider interface to `complete(prompt, timeout=...)`, and #16 says to leave the interface alone and put the timeout in the constructor. Whichever lands second reworks the other (`OpenAIProvider`, `FakeProvider`, and the `FakeProvider(delay_seconds=...)` tests in `tests/test_llm.py:24` and `tests/test_health_sentinel.py:45`). | Ticket #15 AC 1 vs ticket #16 AC 3-4; `core/llm/providers.py:8` (`complete(self, prompt)`) | Verified (conflict is in the tickets and code, not a guess) |
| 4 | Is `httpx` available? | **No.** It is not in `pyproject.toml` dependencies and not in `uv.lock`, and `import httpx` fails. The ticket's tests need `httpx.MockTransport`, and the provider needs it at runtime, so it must be a runtime dependency (plus a lockfile update). | `pyproject.toml:6-9`; `grep httpx uv.lock` empty; `uv run python -c "import httpx"` -> `ModuleNotFoundError` | Verified |
| 5 | Does the ticket's timeout test satisfy rule 1? | Partly. Rule 1 requires a test showing a stalled call does not delay process exit. The ticket only asks for a test that the timeout reaches the HTTP call. Also, httpx timeouts apply per phase (connect/read), not as one overall deadline, so a server that drips bytes could outlast it. | `AGENTS.md` rule 1; ticket #16 AC 3 and AC 7 | Rule text verified; httpx per-phase behaviour is **assumed** from httpx docs, not checked here |
| 6 | Does the env var naming fit the spec? | `LLM_MODEL_SMALL` comes from the spec ("e.g. a Claude Haiku model id") and `LLM_PROVIDER` is listed as `anthropic \| bedrock \| fake`. Using it for an OpenAI model name works but stretches the meaning, and `openai` must be added to the documented provider list. The README has no env docs yet (11 lines). | `~/Downloads/evergreen_agents.md:229-235`; `README.md` | Verified |
| 7 | Could the "optional live check" run in an automated run? | `ci.yml` runs `make test` with no key. `agent.yml` and `agent-fix.yml` pass `secrets.OPENAI_API_KEY` to `codex-action`, which then runs `make test` for the agent. If that action exposes the key to the process running tests, a test that is "skipped unless `OPENAI_API_KEY` is set" would make a live network call. | `.github/workflows/ci.yml:14-16`; `agent.yml:49-51`; `agent-fix.yml:89-91` | **Unverified.** Whether the key reaches the test process is not established |
| 8 | Does the prompt-privacy note hold? | Yes. Reasons contain reading values, rule `when` text, rule ids and versions (`systolic 186, diastolic 104: ...(id vN)`). | `core/rules/engine.py:155-158` | Verified |

Cross-repo coupling: `qodo read cross-repo relations` returned no relations. This is a single-repo
project, so that only says nothing else is indexed, not that nothing else depends on it.

## What changed in the ticket and why

1. **Dependencies: "None" becomes "Sequence after #15".** Land #15 first. Then `OpenAIProvider.complete(prompt, timeout)` builds the `httpx.Timeout` per call and there is a single timeout path. The alternative (constructor timeout now, rework in #15) costs two passes over the same files. Fallback if #15 is delayed: keep the constructor timeout and record the follow-up in #15.
2. **Add `httpx` as a runtime dependency**, with `uv.lock` updated. Nothing else in the repo imports it.
3. **Drop "never raise" from the provider's AC.** `LLMClient` already guarantees it (`client.py:44-52`). The provider should raise on HTTP error, malformed JSON or missing content, and the tests assert `used_fallback` through `LLMClient`.
4. **Add the rule 1 exit test** (stalled provider, subprocess, process exits early), or explicitly assign it to #15 and say so.
5. **Live check needs an explicit opt-in**, for example `RUN_LIVE_LLM=1` in addition to the key, so an exposed key in an automated run cannot trigger a network call.
6. **Docs:** README lists the three variables, and `openai` is added to the provider list. Keep the `unsupported LLM_PROVIDER` error prefix.
7. **Unchanged:** opt-in `LLM_PROVIDER=openai`, default `fake`, no changes to `HealthSentinel`, httpx confined to `core/llm`, the log-privacy tests, and the out-of-scope list.

## Still open

- Is #15 first acceptable, or must #16 ship independently? (decision)
- Keep `LLM_MODEL_SMALL` for an OpenAI model, or use a provider-specific name? (decision)
- Does `codex-action` pass `OPENAI_API_KEY` to the process that runs tests? (unverified)
- Does httpx log request lines at INFO such that the key-not-in-logs test needs to capture the `httpx` logger? (assumed, not checked)
- PR history and similar-PR lookups through Qodo were unavailable (`MT-UPSTREAM-DOWN`). Re-run when the service is back.
