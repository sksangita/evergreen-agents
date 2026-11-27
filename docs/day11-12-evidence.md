# Day 11 and Day 12 evidence

Saved Qodo reviews and findings behind the Day 11 ("Make the reviewer yours") and Day 12 ("Give your
factory the full picture") posts. The PRs are closed, so the reviews are copied into `docs/evidence/`.

Qodo edits its review comment in place and carries findings across reviews of one PR, so each
`pr<N>-qodo-review.md` shows the **latest** state of that PR's comment. The runs and commits behind it are in
`pr<N>-findings.json` (`review_runs`). Re-fetched on 2026-11-27 with `gh pr view` and
`qodo read pr-review-session findings --extended --json`. The earlier working copies were lost when the
temporary folder was cleaned.

## Day 11: same planted deviations, three rule setups

The planted change (commit `2570aa5`, later rebased as `d0cd4e0`, then `f5477d8`) has six deviations: health
values in a log line, escalation set in agent code, a caregiver time with no date or zone, a test that needs the
network, a loosened existing assertion, and an edited `thresholds.yaml` source.

| Setup | PR, run, commit | Loosened assertion flagged? |
|---|---|---|
| `AGENTS.md` (24 rules) plus `REVIEW.md` and guidelines | [#30](evidence/pr30-qodo-review.md), run 2070085, `2570aa5` | Yes, Medium ("Message test no longer checks the time") |
| `AGENTS.md` only (24 rules) | [#33](evidence/pr33-qodo-review.md), run 2070901, `d0cd4e0` | No |
| `AGENTS.md` plus rule 7 (25 rules) | [#35](evidence/pr35-qodo-review.md), run 2083529, `f5477d8` | Yes, Medium, cites rule 4969698 ("Preserve existing test checks...") |

Other findings in each run: health values in logs, escalation outside the rules, time without date, a network
test, and the `thresholds.yaml` source edit. Those appeared in every setup.

Clean PRs before the change: [#25](evidence/pr25-qodo-review.md) and [#29](evidence/pr29-qodo-review.md)
(same branch, commit `c8973ad`, no findings). A clean PR cannot show whether the rules were checked, which is why
the planted PR was used.

Notes:
- Qodo reads `REVIEW.md` and `.pr_agent.toml` from the PR's own branch, not only from `main`.
- `--review_agent.enable_review_md=false` did not disable `REVIEW.md`.
- PR #33's runs 2076740 and 2076864 on the rebased head were `skipped` with no reason given.
- One run per setup, and Qodo varies between runs, so treat the comparison as suggestive.

Resulting setup on `main`: `AGENTS.md` rule 7 (PR #34), and `.pr_agent.toml` with only `override_effort` and
`show_context_used`. `REVIEW.md` and the guideline text were removed (PR #31).

## Day 12: the ticket as a source

Source: issue #22. Expectation: the old `186 104` CLI form prints usage and exits non-zero. Only the ticket says
this. The planted change makes the old form work again.

| PR | Commit | Result |
|---|---|---|
| [#36](evidence/pr36-qodo-review.md) | `736c415`, then `8795217` | High finding citing #22. On the second head it was carried over from the first (stored commit still `736c415`, text still mentions a test that no longer existed), so not a clean detection. A new Medium finding for the removed test came from rule 7. |
| [#37](evidence/pr37-qodo-review.md) | `215898d` (single commit) | High finding "Old positional CLI form still runs as blood pressure", citing ticket #22, `__main__.py:38-41` and rule 4969698. "Context sources" lists the ticket. |

Limits: one run, Qodo listed PR #36 as a linked PR on #37, rule 7 is also cited, and local
`qodo review --ticket <url>` was not run.

## Files

`evidence/pr{25,29,30,33,35,36,37}-qodo-review.md` (the Qodo comments) and
`evidence/pr{25,29,30,33,35,36,37}-findings.json` (findings, citations and review runs).
