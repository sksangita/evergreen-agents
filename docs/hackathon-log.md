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
| 6 | Ask your codebase before you build | not started | - | - |

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

Not started. Challenge thread: [Day 6 thread](https://github.com/orgs/qodo-hackathon/discussions/8)

---

## Backlog after Day 5

| Ticket | What | State |
|---|---|---|
| [#6](https://github.com/sksangita/evergreen-agents/issues/6) | Guardrail v1: block unsafe model text before it reaches the elder | open |
| [#13](https://github.com/sksangita/evergreen-agents/issues/13) | Timezone-aware `measured_at` | open |
| [#15](https://github.com/sksangita/evergreen-agents/issues/15) | Enforced LLM timeouts | open |
| [#16](https://github.com/sksangita/evergreen-agents/issues/16) | OpenAI provider in `core/llm` | open |
