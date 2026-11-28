# Day 14 evidence: the quality gate as a Qodo workflow

Challenge: turn the saved gate into a Qodo workflow that adds the "Qodo approved" label, protect one path with
an approval guard, and compare two PRs (one outside the guarded path, one inside) with predictions written
before review. Predictions: [`evidence/day14-predictions.md`](evidence/day14-predictions.md).

**Result: INCOMPLETE.** The outside PR had three complete, clean reviews and never got the label. The cause is
unresolved. The inside PR was not opened.

## Setup in the Qodo portal (2026-11-27)

| Item | Setting |
|---|---|
| Gate it implements | AGENTS.md "Quality gate for review loops": no valid High or Medium finding of any type or category, review complete on the PR head, Low left to a person |
| Workflow | `evergreen-medium-gate-workflow`, scope **Repository** `sksangita/evergreen-agents`, Active |
| When / If / Then | Qodo finishes reviewing a PR / no findings of medium severity or higher (no category or type filter) / add "Qodo approved" label |
| Not used | Auto approve. Approval and merging stay with a person |
| Approval guard | `sksangita/evergreen-agents`, "Only these paths", `core/rules/**` (the rule engine and `thresholds.yaml`, AGENTS.md rule 4). No guards existed before. No author guards |
| Other workflows | "Auto-approve low-risk PRs" and "Label clean PRs" stay Inactive |

Setup mistakes, fixed before any PR existed: the first save was Workspace scope with Auto approve and Active
on. It was turned off and deleted. The second save, at repository scope, still had Auto approve and was changed
to the label action. The guard panel's **+ Add** offers only organizations and repositories, not a bare path.

## PR A, outside the guard: [#40](https://github.com/sksangita/evergreen-agents/pull/40)

`--json` output for the CLI. Paths: `agents/health_sentinel/__main__.py`, `tests/test_cli.py`, `README.md`,
`docs/evidence/day14-predictions.md`. Head `54c72d5`. CI `test` passed. `make lint` passes, `make test` 213
passed, 1 skipped. Prediction: label added.

| Run | Started (UTC) | Trigger | Guard at the time | Complete | Findings | Label |
|---|---|---|---|---|---|---|
| 2192536 | 11:52 | automatic on open | repo + `core/rules/**` | yes, on head | 0 | none |
| 2193362 | 12:46 | `/agentic_review` | repo + `core/rules/**` | yes, on head | 0 | none |
| 2193514 | 12:59 | `/agentic_review` | removed | yes, on head | 0 | none |

Evidence: `qodo read pr-review-session findings --extended --json` (runs, `review_complete: true`,
`commit_sha` = head); `gh pr view 40 --json labels,reviews` (`[]`, `[]`); `gh api
repos/sksangita/evergreen-agents/issues/40/events` (no `labeled` event); no "Qodo approved" label in the repo.
PR Triage: "Qodo review completed: No new findings", merge risk "Not assessed", no workflow, label or guard
entry. The Qodo comment: Bugs 0, Rule violations 0, Requirement gaps 0, Merge Risk Low.

### Investigation

| Possible cause | Check | Result |
|---|---|---|
| Medium or higher finding | three runs | 0 findings, ruled out |
| Skipped or stale review | `review_complete`, `commit_sha` | complete on the head every time, ruled out |
| Guard saved as "Whole repository" | reopened the panel | reads "Only these paths, `core/rules/**`", ruled out |
| Repo-plus-path guard blocks the whole repo (reported by another participant: stored as `deny_repos` + `deny_paths`) | removed the guard, run 2193514 | still no label, so not the cause here |
| GitHub app cannot add labels | app installation settings | Issues and Pull requests read/write, repo selected, ruled out |
| Merge automation in `native_vote` mode, which skips the label action (another participant's finding) | not checked | open. Not visible in the panel |
| Research-preview workflow not running on this trial or plan | not checked | open |

The guard was added back in its original form after run 2193514.

## PR B, inside the guard: not opened

Planned: reject duplicate rule `id`s when `thresholds.yaml` loads (`core/rules/engine.py` and `tests/`).
Prediction: clean review, no label because of the guard. Not run, because the outside PR could not get the label
even with no guard, so a missing label on PR B would show nothing about the guard.

## Limits

One PR, three runs on one head. The stored workflow and merge-automation settings were not inspected. PR
Triage shows no workflow or guard activity, so the only label evidence is GitHub's PR events.
