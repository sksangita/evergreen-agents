---
name: check-threshold-edges
description: Verify that every triage threshold for one vital in core/rules/thresholds.yaml behaves correctly exactly at, just above and just below its edge, by running the demo CLI and comparing with an expected-edges file taken from the ticket or spec. Use when a change adds or edits a threshold or a vital (AGENTS.md rules 4 and 5), or when asked to check threshold edges or boundaries. Not for blood pressure yet.
---

# Check threshold edges

AGENTS.md rule 4 says every safety change needs edge cases: exactly at a threshold and just below it. This
skill runs that check against the real CLI and compares with what the **ticket or spec** says, not with what the
code does. A file that exists, or a test that passes on its own, is not this check.

## Inputs (stop and ask if any is missing)

1. **Vital**: `heart_rate` only. For any other vital, including `blood_pressure`, stop and say the script does
   not support it. Do not improvise a different comparison.
2. **Expected edges file**: a YAML list written from the ticket or spec text, with the source URL in a comment.
   For heart rate use `.claude/skills/check-threshold-edges/references/heart-rate-ticket-22.yaml`. If the task has
   a new or changed threshold and no expected file covers it, stop and ask for the ticket or spec wording. Never
   build the expected values by reading `thresholds.yaml` or the engine, because that makes the check circular.
3. **Output path for the evidence**: `docs/evidence/skill-runs/<YYYY-MM-DD>-<vital>.md`.

Work from the repository root. Needs `uv`. Runs offline, no API key.

## Steps

1. Read `core/rules/thresholds.yaml`. Note the file `version` and each rule for the vital (`id`, `version`,
   `when`, `source`). If a rule lacks `id`, `version` or `source`, report it. That is a failure.
2. Confirm the expected file against the live source. Read the ticket named in its header (read-only):
   ```bash
   gh issue view 22 --repo sksangita/evergreen-agents --json body -q .body
   ```
   For each value the file quotes from the ticket (thresholds, escalation, "100 is green", "just above 130 is
   red"), find the same wording in the body. Report any quote that is missing or different. If `gh` is not
   allowed or the ticket cannot be read, say "expected file not compared with the live ticket" in the report
   and in the evidence file, and continue. Do not treat the run as fully verified.
3. Run the script and keep the full output:
   ```bash
   uv run python .claude/skills/check-threshold-edges/scripts/run_edges.py heart_rate \
     .claude/skills/check-threshold-edges/references/heart-rate-ticket-22.yaml
   ```
   It runs `uv run python -m agents.health_sentinel hr <bpm>` for every case and compares triage level,
   escalation and exit code with the file. It also checks that each threshold has a case exactly at it, just
   above and just below.
4. Read the output line by line. Every line must say `OK`. The last line must be `PASS: 0 problem(s)` and the
   exit code 0. A line that says `FAIL`, a missing line, or exit 1 or 3 means the check failed.
5. Compare with the repo's own tests: open `evals/heart_rate_cases.yaml` and list any threshold edge in the
   expected file that has no matching case there. Report these; do not edit the eval file unless asked.
6. Save the evidence (see below), then give the final report.

## Expected result

All cases `OK`, all thresholds covered on both sides, `PASS: 0 problem(s)`. For heart rate at `thresholds@v2`:
100 green, 100.01 amber, 130 amber, 130.01 red, 40 green, 39.99 red, 0 and -5 rejected with exit 2.

## Evidence to save

Write one file at the output path with: the date and git commit (`git rev-parse --short HEAD`), the thresholds
file `version`, the result of step 2 (matched, or the differences, or "not compared"), the exact command, the **full script output**, and the list from step 5. Do not summarize in
place of the output.

## Stop and ask instead of continuing when

- the vital is not `heart_rate`, or the expected file is missing or has no source reference;
- the script exits 3, crashes, or the CLI cannot run (for example `uv` is missing);
- a result differs from the expected file. Report the mismatch with the numbers. Do not edit the expected file or
  `thresholds.yaml` to make it pass. A threshold change needs human review (rule 4);
- the task would need network access (other than the read-only `gh issue view` in step 2) or an API key.

## Final report

Status PASS or FAIL, the command, the result of the ticket comparison, the number of cases and thresholds checked, every mismatch, the evidence file
path, and anything you could not check.
