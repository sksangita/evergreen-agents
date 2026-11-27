---
name: check-new-vital
description: Check that a vital (heart rate, glucose, SpO2, blood pressure) has every piece AGENTS.md rule 5 requires, by running a script that inspects the contracts, thresholds, eval cases, elder and caregiver text, CLI subcommand and README, then listing each missing piece with its file. Use when a change adds or edits a VitalKind, before opening the PR, when reviewing such a PR, or when asked whether a vital is complete.
---

# Check a new vital is complete

AGENTS.md rule 5: a new vital arrives with its rules, units and tests, or it silently triages green. Several
pieces live in different files and a test cannot see all of them. In Day 10 the agent missed a hard-coded
caregiver message and the existing evals read `systolic` from every case. This skill finds the missing pieces
before review.

## Inputs (stop and ask if any is missing)

1. **Kind**: the `VitalKind` value, for example `heart_rate` (see `core/contracts.py`).
2. **CLI subcommand name** for that vital, for example `hr`. If the task adds a vital and no subcommand was
   chosen, ask. Never guess one.
3. **Base ref** to compare the thresholds version with. Default `main`.
4. **Source ticket or spec** for the thresholds (URL or text). Needed for step 3.

Work from the repository root. Needs `uv` and `git`. Offline, no API key. Read-only except the evidence file.

## Steps

1. Run the script and keep the full output:
   ```bash
   uv run python .claude/skills/check-new-vital/scripts/check_vital.py heart_rate hr main
   ```
   Replace the three arguments with your inputs. The script prints one line per item: `OK`, `FAIL`, `HUMAN`
   (needs a person), or `UNCHECKED`, and ends with a `PASS` or `FAIL` summary and an exit code.
2. For every `FAIL`, open the named file and write down what is missing, with `file:line`. Do not fix it unless
   the task says to build the vital. If the task is an audit, only report.
3. Compare the thresholds with the source from input 4: open `core/rules/thresholds.yaml`, and for each rule of
   the vital check the number and direction against the ticket or spec wording (for example `bpm > 100`).
   Report any difference as a finding. Do not edit the thresholds.
4. Check three things the script cannot: (a) the elder text in `agents/health_sentinel/templates.py` names this
   vital and not another; (b) `agent.py` `_MEASUREMENT_TEXT` shows the value with its unit; (c) a test in
   `tests/` covers rejection of bad input (zero, negative, NaN, infinity, wrong unit) for this vital.
5. Save the evidence (below), then give the final report.

## Expected result

For a complete vital: every item `OK` except `HUMAN` lines for sources marked unverified, and the last line
`PASS: 0 failing item(s)`. For a vital that is half added, one `FAIL` line per missing piece.

## Evidence to save

Write `docs/evidence/skill-runs/<YYYY-MM-DD>-<kind>.md` with: date, `git rev-parse --short HEAD`, the exact
command, the **full script output**, and your notes from steps 2 to 4. Do not replace the output with a summary.

## Stop and ask instead of continuing when

- an input is missing, the kind is not in `VitalKind`, or the script exits 3 or crashes;
- the work would change `core/rules/` or `thresholds.yaml` (rule 4: a person reviews these);
- fixing a `FAIL` would need a threshold value, a source, or clinical wording you do not have;
- the check needs network access or an API key.

## Final report

Status PASS or FAIL, the command, each `FAIL` with `file:line`, each `HUMAN` line, what step 3 found, what you
could not check, and the evidence file path.
