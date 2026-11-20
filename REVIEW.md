# REVIEW.md

Instructions for Qodo's code review of evergreen-agents. The full rules are in `AGENTS.md`; this
file says what a reviewer should flag, and what it should leave alone.

evergreen-agents triages elders' vital signs (blood pressure, heart rate) as green, amber or red,
and tells the elder and a caregiver. It is a prototype and **not a medical device**; all data is
synthetic. A missed alert is worse than a noisy one.

## Product decisions to respect
- **Rules decide triage, the LLM only explains it.** Only `core/rules` sets `triage` or
  `requires_escalation`. Code in `agents/` reads the decision and never changes it.
- **A model outage must never hide an alert.** Every model call has a timeout, a template
  fallback, and a test for the fallback. Text for an elder names the vital that was measured.
- **Bad input is rejected, never green.** A reading with the wrong unit, NaN, zero, a negative
  value or an unexpected key must raise when it is created.
- **Tests run offline** against the fake model, with no network and no API key.

## Flag as High or Medium
- Code outside `core/rules` that sets `triage` or `requires_escalation`.
- Model text shown to an elder or caregiver with no template fallback.
- Any path where an unjudgeable reading could be triaged green.
- Health values, names or phone numbers in a log call or an LLM prompt.
- A time shown to a person without a date and a timezone.
- A test that needs the network or an API key.
- A new `VitalKind` without its rules, allowed unit, edge-case tests and caregiver message format.
- An existing test assertion that is rewritten or loosened when the change did not need it. Say
  which assertions changed.

## Say plainly when it happens
- The change edits `core/rules/`, `thresholds.yaml`, `core/baseline/`, `core/guardrail/` or
  `core/escalation/`. These need human review before merge, and every threshold needs an `id`,
  `version` and `source`.

## Do not flag
- Anything listed under "Known gaps" in `AGENTS.md` (the default fake provider, the single-reading
  amber rule, unverified demo thresholds, the guardrail and escalation service not being built).
- Style that `ruff` and `mypy --strict` already enforce.

## How to present
- Put High and Medium findings first. Keep Low findings short.
- Begin the review summary with the line `REVIEW.md applied`, so it is clear this file was read.
