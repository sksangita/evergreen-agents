# Hackathon log

A day-by-day reference for the Qodo Hackathon (2 Nov to 2 Dec 2026): what each challenge asked, what was built, and what was posted in that day's Discussion thread.

"Worked on" is the date the work was done, which can differ from the challenge's scheduled day.

Where to submit: [Start here thread](https://github.com/orgs/qodo-hackathon/discussions/1). All daily threads: https://github.com/orgs/qodo-hackathon/discussions

## Index

| Day | Theme | Worked on | Main PRs and tickets | Discussion post |
|---|---|---|---|---|
| 1 | First delivery | 2 Nov | PR #1 | [my post](https://github.com/qodo-hackathon/software-factory-hackathon/discussions/2#discussioncomment-19357597) |
| 2 | Project rules (`AGENTS.md`) | 5 Nov | PR #2 | [my post](https://github.com/qodo-hackathon/software-factory-hackathon/discussions/4#discussioncomment-19423524) |
| 3 | Connect the backlog | 6 Nov | Tickets #3, #4; PRs #7, #8 | [my post](https://github.com/qodo-hackathon/software-factory-hackathon/discussions/5#discussioncomment-19431917) |
| 4 | Pick up work automatically | 6 Nov | Ticket #5; PRs #9 to #12 | [my post](https://github.com/qodo-hackathon/software-factory-hackathon/discussions/6#discussioncomment-19435163) |
| 5 | Self-improving rules | 7 Nov | PR #14 | [my post](https://github.com/qodo-hackathon/software-factory-hackathon/discussions/7#discussioncomment-19458164) |
| 6 | Ask your codebase before you build | 10 Nov | Ticket #16; PR #18 | posted |
| 7 | Resolve Qodo's PR review findings | 11 Nov | Tickets #15, #16; PR #19 | posted |
| 8 | Review local changes before commit | 13 Nov | Ticket #13; PR #21 | posted |
| 9 | Quality gate for review loops | 13 Nov | PR #20 | posted |
| 10 | Ticket to main, with a factory diagram | 17 to 20 Nov | Ticket #22; PRs #23, #24 | posted |
| 11 | Make the reviewer yours | 20 to 21 Nov | PRs #26 to #35 | posted |
| 12 | Give your factory the full picture | 21 to 27 Nov | Ticket #22; PRs #36, #37, #38 | posted |
| 13 | Teach your factory a new skill | 27 Nov | PR #39 | posted |
| 14 | Turn your quality gate into a workflow | 27 Nov | PR #40 | posted (INCOMPLETE) |

---

## Day 1: First delivery

**Challenge:** describe the project (what it builds, who it helps, one small capability for today), deliver a first PR or repository, and bring one lesson or decision from the Qodo review.

**What was built:** a blood pressure triage slice. A reading goes through deterministic rules (green, amber, red), then an LLM client explains the result, with a template fallback if the model fails. Includes contracts, rules engine, fake LLM client, Health Sentinel agent, demo CLI, CI.

**Links:** [PR #1](https://github.com/sksangita/evergreen-agents/pull/1)

**Posted:**
- Screenshots of the demo CLI output, and the plan: a multi-agent system (Health Sentinel, Companion, Interests, Peer Circles) where fixed rules decide triage and the LLM only explains it.
- Lesson from Qodo's review: its one high-severity finding was that a blood pressure in kPa (about 180/120 mmHg) was triaged green, and NaN, zero and negative readings were also green. Rule: "no rule matched" must never be the default answer for data the rules don't understand.

**Discussion thread:** [Day 1 thread](https://github.com/orgs/qodo-hackathon/discussions/2), [my post](https://github.com/qodo-hackathon/software-factory-hackathon/discussions/2#discussioncomment-19357597)

---

## Day 2: Project rules

**Challenge:** write an `AGENTS.md` at the repo root with a short project description, setup and verification commands, and three to five rules (where each applies and why). Commit and push it, check Qodo's Review Standards, and nominate the most opinionated rule with its story.

**What was built:** `AGENTS.md` with five rules and a Known gaps list.

**Links:** [PR #2](https://github.com/sksangita/evergreen-agents/pull/2), [AGENTS.md](https://github.com/sksangita/evergreen-agents/blob/main/AGENTS.md)

**Posted:**
- The five rules: No Model Verdicts, No Silent Green, no personal data in logs or prompts, safety changes carry tests/sources/review, new vitals need rules.
- Nominated rule: **"The No Silent Green Rule"**. Story: Qodo's Day 1 finding that a kPa reading was triaged green.

**Discussion thread:** [Day 2 thread](https://github.com/orgs/qodo-hackathon/discussions/4), [my post](https://github.com/qodo-hackathon/software-factory-hackathon/discussions/4#discussioncomment-19423524)

---

## Day 3: Connect the backlog

**Challenge:** connect a ticketing system to the coding agent (MCP or CLI), have it list and read tickets, then work tickets one at a time, each on its own branch and PR. Review each with Qodo, check the behaviour against every acceptance criterion, and feed the findings back into rules, skills or review setup.

**What was built:** GitHub Issues through the `gh` CLI. Two tickets delivered:
- #3: reject blood pressure readings that are not in mmHg.
- #4: reject NaN, infinite, zero and negative values, and re-check every reading inside `triage_reading`.

**Links:** tickets [#3](https://github.com/sksangita/evergreen-agents/issues/3), [#4](https://github.com/sksangita/evergreen-agents/issues/4); PRs [#7](https://github.com/sksangita/evergreen-agents/pull/7), [#8](https://github.com/sksangita/evergreen-agents/pull/8)

**Posted:**
- Connection: `gh issue list` and `gh issue view` to list and read tickets.
- PR #7: Qodo found nothing, but my own check found that `model_construct` skips validation, so a kPa reading built that way was still green.
- PR #8: Qodo found three real problems (unexpected keys accepted, `KeyError` on an unknown kind, `TypeError` on a text value). All fixed, and Qodo's re-review was clean.
- Rule update: `AGENTS.md` rule 2 now says unjudgeable input always raises `InvalidReadingError`.
- Lesson: a review of the diff alone found less than a review checked against the project's own rules.

**Discussion thread:** [Day 3 thread](https://github.com/orgs/qodo-hackathon/discussions/5), [my post](https://github.com/qodo-hackathon/software-factory-hackathon/discussions/5#discussioncomment-19431917)

---

## Day 4: Pick up work automatically

**Challenge:** set up a trigger (schedule or a ticket label) so the agent starts without a session. It reads the ticket and rules, implements, checks acceptance criteria, opens a PR for Qodo, fixes confirmed findings with a retry limit, and stops for help if stuck. A person decides whether to merge.

**What was built:** two GitHub Actions workflows running OpenAI Codex:
- `agent.yml`: adding the label `ready-for-agent` to an issue produces a patch (read-only token), then a second job opens the PR.
- `agent-fix.yml`: Qodo's findings on an `agent/` PR trigger fixes, with a limit of 2 rounds, then `agent-blocked`.

**Result:** ticket #5 (rule conditions must be comparisons) was delivered automatically as PR #12, with 91 tests passing. It took three runs: the first two failed on the Codex safety strategy and a folder permission (fixed in PRs #10 and #11). Qodo reviewed PR #12 only after a manual `/review`, because the PR was opened by a bot. The fix loop was never exercised, since Qodo found nothing.

**Links:** [workflow](https://github.com/sksangita/evergreen-agents/blob/main/.github/workflows/agent.yml), ticket [#5](https://github.com/sksangita/evergreen-agents/issues/5); PRs [#9](https://github.com/sksangita/evergreen-agents/pull/9), [#10](https://github.com/sksangita/evergreen-agents/pull/10), [#11](https://github.com/sksangita/evergreen-agents/pull/11), [#12](https://github.com/sksangita/evergreen-agents/pull/12); [successful run](https://github.com/sksangita/evergreen-agents/actions/runs/42181299787)

**Posted:** the format of trigger and workflow link, ticket and PR, what happened (checks, Qodo review, retries), and what still needed a person.

**Discussion thread:** [Day 4 thread](https://github.com/orgs/qodo-hackathon/discussions/6), [my post](https://github.com/qodo-hackathon/software-factory-hackathon/discussions/6#discussioncomment-19435163)

---

## Day 5: Self-improving rules

**Challenge:** have Qodo or the coding agent look back at the code and review feedback, propose a rule with source evidence, refine it, save it in a PR, and share the decision.

**Path:** coding-agent proposal. Qodo's Review Standards had nothing under Pending rules.

**What was built:**
- New rule 6: times carry a date and a timezone (from Qodo's PR #1 finding about a caregiver seeing a UTC clock time with no date or zone).
- Rule 1 amended: the provider call must enforce its own timeout, and a test must show a stalled call does not delay process exit (reproduced: a call that timed out in 0.20s kept the process alive for 8.06s).
- Qodo's review of the rules PR found that listing the rule 6 gap under "do not flag" told reviewers to skip it. Fixed by adding a separate "Open rule gaps" section.
- Rejected: "findings answered before merge" (Qodo can't check merge behaviour).

**Links:** [PR #14](https://github.com/sksangita/evergreen-agents/pull/14); follow-up tickets [#13](https://github.com/sksangita/evergreen-agents/issues/13) (timezone-aware times), [#15](https://github.com/sksangita/evergreen-agents/issues/15) (enforced timeouts)

**Posted:** path taken, the rule and its evidence, what was accepted, changed or rejected, and the PR. The rules were imported into Qodo and the PR is merged.

**Discussion thread:** [Day 5 thread](https://github.com/orgs/qodo-hackathon/discussions/7), [my post](https://github.com/qodo-hackathon/software-factory-hackathon/discussions/7#discussioncomment-19458164)

---

## Day 6: Ask your codebase before you build

**What was built:** an investigation of ticket #16 (OpenAI provider) with Qodo Codebase Wisdom before writing
code. It found that #15 and #16 conflict on the provider interface, that `httpx` was missing, and that the
ticket's timeout test did not meet rule 1. Every claim is cited to `file:line` or marked unverified.

**Links:** [PR #18](https://github.com/sksangita/evergreen-agents/pull/18),
[`day6-ticket-16-investigation.md`](day6-ticket-16-investigation.md)

---

## Day 7: Resolve Qodo's PR review findings

**What was built:** enforced LLM timeouts (#15) and the opt-in OpenAI provider (#16) in one PR, because the Day
6 investigation showed they conflict if built separately. Qodo's finding was reproduced, fixed with a failing
test, and the final review on the head was clean.

**Links:** [PR #19](https://github.com/sksangita/evergreen-agents/pull/19)

---

## Day 8: Review local changes before commit

**What was built:** timezone-aware `measured_at` with date and zone shown to caregivers (#13, rule 6), reviewed
with the Qodo Reviewer on uncommitted changes over 3 rounds before the PR.

**Links:** [PR #21](https://github.com/sksangita/evergreen-agents/pull/21)

---

## Day 9: Quality gate for review loops

**What was built:** the gate in `AGENTS.md`: fix every valid High and Medium finding with a failing-first
test, report Low findings to a person, the final review must be complete and cover the head, at most 3 rounds,
NOT DONE otherwise.

**Links:** [PR #20](https://github.com/sksangita/evergreen-agents/pull/20)

---

## Day 10: Ticket to main

**What was built:** ticket #22 (resting heart rate as a second vital) taken from ticket to `main` through the
automated dev agent, CI, Qodo review and a manual Review Resolver fix, plus the factory diagram with its gates
and the gaps found (the fix agent could not start, `/review` was manual on bot PRs).

**Links:** [PR #23](https://github.com/sksangita/evergreen-agents/pull/23),
[PR #24](https://github.com/sksangita/evergreen-agents/pull/24), [`factory-diagram.md`](factory-diagram.md)

---

## Day 11: Make the reviewer yours

**What was built:** the same planted deviations reviewed under three rule setups. Only with a dedicated
`AGENTS.md` rule did Qodo flag the loosened test assertion and cite that rule, so rule 7 (existing tests are not
weakened) was added. `REVIEW.md` and the guideline text were removed. `.pr_agent.toml` keeps `override_effort`
and `show_context_used`.

**Links:** [PR #34](https://github.com/sksangita/evergreen-agents/pull/34),
[PR #31](https://github.com/sksangita/evergreen-agents/pull/31),
[`day11-12-evidence.md`](day11-12-evidence.md)

---

## Day 12: Give your factory the full picture

**What was built:** a test of ticket #22 as a review source. A planted change that broke the ticket's CLI
expectation got a High finding citing the ticket, and Context sources listed it. The first attempt (PR #36) was
confounded by carried-over findings, so a fresh single-commit PR (#37) was used.

**Links:** [PR #37](https://github.com/sksangita/evergreen-agents/pull/37),
[PR #38](https://github.com/sksangita/evergreen-agents/pull/38) (saved evidence),
[`day11-12-evidence.md`](day11-12-evidence.md)

---

## Day 13: Teach your factory a new skill

**What was built:** the `check-new-vital` Claude Code skill. A script audits a vital for everything rule 5
needs (contracts, thresholds and version, eval edges, elder and caregiver text, CLI, README) and reports PASS,
FAIL or INCOMPLETE. Tested in fresh `claude -p` sessions (heart rate PASS, a half-added glucose vital FAIL, a
stop for missing inputs). Qodo found 7 Medium issues in the skill in round 1 and 1 in round 3, all fixed. Round
4 was clean.

**Links:** [PR #39](https://github.com/sksangita/evergreen-agents/pull/39),
[`.claude/skills/check-new-vital/`](../.claude/skills/check-new-vital/SKILL.md),
[`evidence/skill-runs/`](evidence/skill-runs/)

---

## Day 14: Turn your quality gate into a workflow

**What was built:** Qodo workflow `evergreen-medium-gate-workflow` (repository scope, no Medium or higher
finding, add the "Qodo approved" label) and an approval guard on `core/rules/**`. PR A (#40, `--json` CLI
output, outside the guard) had three complete, clean reviews but never got the label, even with the guard
removed. The cause is unresolved. PR B (inside the guard) was not opened. Posted as INCOMPLETE.

**Links:** [PR #40](https://github.com/sksangita/evergreen-agents/pull/40),
[`day14-evidence.md`](day14-evidence.md), [predictions at `54c72d5`](https://github.com/sksangita/evergreen-agents/blob/54c72d588e1f6e52e70d3a36aa904660f1046850/docs/evidence/day14-predictions.md)

---

## Backlog after Day 14

| Ticket | What | State |
|---|---|---|
| [#6](https://github.com/sksangita/evergreen-agents/issues/6) | Guardrail v1: block unsafe model text before it reaches the elder | open |
| [#13](https://github.com/sksangita/evergreen-agents/issues/13) | Timezone-aware `measured_at` | closed |
| [#15](https://github.com/sksangita/evergreen-agents/issues/15) | Enforced LLM timeouts | closed |
| [#16](https://github.com/sksangita/evergreen-agents/issues/16) | OpenAI provider in `core/llm` | closed |
| [#22](https://github.com/sksangita/evergreen-agents/issues/22) | Resting heart rate as a second vital | closed |
