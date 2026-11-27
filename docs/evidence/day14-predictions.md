# Day 14 predictions (written before either PR exists)

Written 2026-11-27, before any review ran. Observed results are added below the line later, never by editing
this section.

## Setup

- Saved gate: AGENTS.md "Quality gate for review loops". Zero valid High and Medium findings, every type and
  category. The review must be complete and cover the PR head. Low findings are listed and left to a person.
  CI, tests and acceptance checks are separate requirements.
- Approval guard (whole workspace, one entry): `sksangita/evergreen-agents`, path `core/rules/**`. It holds
  `thresholds.yaml` and the rule engine, which AGENTS.md rule 4 puts under human review. No author guards. No
  guards existed before.
- Workflow `evergreen-medium-gate-workflow`, scope: this repository only. WHEN Qodo finishes reviewing a PR,
  IF no findings of medium severity or higher (no category or type filter), THEN add the "Qodo approved" label.
  Not Auto approve, so approval and merging stay with a person.
- Other workflows in the list (Auto-approve low-risk PRs, Label clean PRs, a workspace copy of this one) are
  Inactive.

## PR A, outside the guard: `--json` output for the CLI

Touches `agents/health_sentinel/__main__.py` and `tests/test_cli.py`. No path under `core/rules/`.

Prediction: complete review of the head, no Medium or higher finding after at most the usual fix rounds, no
guard applies, so the workflow adds **Qodo approved**. If Qodo finds a Medium, I fix it, the head changes,
and the label should appear only after a clean review of the new head. Low findings may remain, and I decide
on them.

## PR B, inside the guard: reject duplicate rule ids when `thresholds.yaml` loads

Touches `core/rules/engine.py` and `tests/`. It matches `core/rules/**`.

Prediction: complete review, no Medium or higher finding, but **no Qodo approved label**, because the guard
applies even to a clean PR. A person (me, as reviewer) decides on merging.

## What would count as a different result

- PR B gets the label: the guard did not block the label, only auto approval.
- PR A gets no label with a clean complete review: check PR Triage for the reason.
- Either review is skipped or incomplete: record it as incomplete evidence.
