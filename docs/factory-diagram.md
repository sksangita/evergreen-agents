# The factory: from ticket to main

Everything built in Days 6 to 10, in one picture. Two ways to build (by hand with a coding agent, or by the
GitHub automation), one shared path to `main`. Rules and the definition of done are in `AGENTS.md`
("Quality gate for review loops"), which every agent reads.

```mermaid
flowchart TD
  classDef tool fill:#d9f2d9,stroke:#2e7d32,color:#111
  classDef gate fill:#fff3cd,stroke:#b58900,color:#111
  classDef human fill:#d6e6ff,stroke:#1f5fbf,color:#111
  classDef stop fill:#ffd6d6,stroke:#c62828,color:#111

  T["TICKET<br/>GitHub issue: problem, acceptance criteria,<br/>edge case, rules that apply"]:::human

  subgraph S1["STAGE 1 - BEFORE WORK (Day 6)"]
    W["Qodo Codebase Wisdom skill<br/>qodo read codebase grep / read-file<br/>reuse, impact, hidden dependencies"]:::tool
    G1{"GATE 1: ticket vs code<br/>every claim cited file:line<br/>or marked unverified"}:::gate
  end

  subgraph LA["STAGE 2, LANE A - BUILD BY HAND, code uncommitted (Day 8)"]
      IMP["Coding agent implements<br/>reads AGENTS.md, tests with the change"]:::tool
      G2A{"GATE 2A: make lint + make test"}:::gate
      QL["Qodo Reviewer skill<br/>qodo review --repo owner/repo"]:::tool
      G2B{"GATE 2B: High / Medium gate<br/>no valid High or Medium open<br/>Low listed, code unchanged<br/>review complete, covers final tree"}:::gate
  end

  subgraph LB["STAGE 2, LANE B - BUILD BY AUTOMATION (Day 10)"]
      DEV["DEV AGENT: agent.yml<br/>label ready-for-agent (owner only)<br/>Codex + implement.md, read-only token<br/>second job pushes agent/ticket-n"]:::tool
  end

  subgraph S3["STAGE 3 - PULL REQUEST (Days 7, 9, 10)"]
    PR["Pull request<br/>Closes #ticket"]:::tool
    G3{"GATE 3: CI<br/>ci.yml: make install, lint, test<br/>on the PR head"}:::gate
    QP["Qodo PR review<br/>posted on the head<br/>comment /review to trigger"]:::tool
    G4{"GATE 4: High / Medium gate<br/>review complete, commit_sha = PR head<br/>no valid High (action_required)<br/>or Medium (remediation_recommended) open<br/>Low (informational) listed for a human"}:::gate
    RR["Qodo Review Resolver skill<br/>qodo read pr-review-session findings<br/>reproduce, fix with a failing test, push"]:::tool
    FIX["FIX AGENT: agent-fix.yml<br/>on Qodo comment, Codex + fix.md<br/>2 rounds: fix-round-1, fix-round-2"]:::tool
  end

  subgraph S4["STAGE 4 - MERGE"]
    G5{"GATE 5: pre-merge checklist<br/>CI and review both on the same head<br/>Low findings acknowledged<br/>rule 4 paths human-reviewed<br/>PR text matches what shipped"}:::gate
    D5(["HUMAN: approve and merge<br/>no agent merges"]):::human
    MAIN["main<br/>ci.yml runs again"]:::tool
  end

  STOP["NOT DONE / agent-blocked<br/>High or Medium open or contested,<br/>checks fail, review incomplete, stalled,<br/>or 3 rounds used"]:::stop

  T --> W --> G1
  G1 -- "fail: revise ticket, keep original in a comment" --> W
  G1 -- "pass: manual" --> IMP
  G1 -- "pass: add label" --> DEV

  IMP --> G2A
  G2A -- "fail" --> IMP
  G2A -- "pass" --> QL --> G2B
  G2B -- "valid High or Medium open" --> IMP
  G2B -- "met" --> PR
  G2B -- "stalled or incomplete" --> STOP

  DEV -- "patch ok" --> PR
  DEV -- "empty patch or .github change" --> STOP

  PR --> G3
  G3 -- "fail" --> RR
  G3 -- "pass" --> QP --> G4
  G4 -- "valid High or Medium open" --> RR
  G4 -- "valid High or Medium open, automated" --> FIX
  RR -- "push, new head" --> G3
  FIX -- "push, new head" --> G3
  FIX -- "open after round 2" --> STOP
  G4 -- "stalled or contested" --> STOP
  G4 -- "met" --> G5
  G5 -- "item missing" --> RR
  G5 -- "all hold" --> D5 --> MAIN
```

Colours: green = a tool or agent does the work, yellow = a gate, blue = a human, red = stop.

## What each name is

| Name | What it is | Where |
|---|---|---|
| Qodo Codebase Wisdom skill | Questions about the code: reuse, impact, history. Cited answers. | Local, `qodo read codebase ...` |
| Qodo Reviewer skill | Reviews staged and unstaged changes before commit. Needs `--repo owner/repo` when `origin` is an SSH alias. | Local, `qodo review` |
| Qodo PR review | Posts "Code Review by Qodo" on the PR head. Starts on a `/review` comment. | Qodo bot on GitHub |
| Qodo Review Resolver skill | Reads the PR's findings as JSON (`action_level`, `commit_sha`), fixes valid ones, never records outcomes without an instruction. | Local, `qodo read pr-review-session findings` |
| DEV AGENT, `agent.yml` | `ready-for-agent` label starts Codex on one ticket. Read-only token makes a patch, a second job pushes `agent/ticket-<n>` and opens the PR. Refuses an empty patch or a `.github/` change. | GitHub Actions |
| FIX AGENT, `agent-fix.yml` | Qodo's comment starts Codex on the findings. Max 2 rounds, then `agent-blocked`. | GitHub Actions |
| `ci.yml` | `make install`, `make lint`, `make test` on every PR and on `main`. | GitHub Actions |
| `AGENTS.md` | The 7 rules, the High/Medium/Low gate, and the final report format. | Repo root |
| `.github/agent/implement.md`, `fix.md` | The prompts the two agents run. | Repo |

## The gates

| Gate | Must hold | Evidence | If it fails | Decides |
|---|---|---|---|---|
| 1. Ticket vs code | Every claim cited to code or marked unverified. No conflict with another ticket or rule. | Wisdom results with `file:line` | Revise the ticket, keep the original in a comment | You: go, revise or stop |
| 2A. Local checks | `make lint` and `make test` pass | Command output | Fix and rerun | The agent |
| 2B. Local High/Medium gate | No valid High or Medium open. Every Low listed with the code unchanged. Review complete and covering the final tree. | `qodo review` result; each finding reproduced; a test that fails without the fix | Fix, run 2A, review again. Contested finding: report evidence. Stalled or 3 rounds: stop. | You, for disagreements and Low |
| 3. CI | `test` check passes on the PR head | GitHub Actions run | Back to a fix | The agent |
| 4. PR High/Medium gate | Review complete, `commit_sha` equals the PR head, no valid High or Medium open. Low listed for a human. | `qodo read pr-review-session findings`, `gh pr view --json headRefOid` | Resolver or Fix agent fixes and pushes; wait for a review of the new head. Stalled or contested: stop. | You, for disagreements |
| 5. Pre-merge | Everything above holds on the current head. Rule 4 paths human-reviewed. PR text matches the diff. | Checklist | Back to the failing gate | You: approve and merge |

**High/Medium gate in one line:** fix every valid High and Medium (with a test that fails without the fix),
only report Low, never close a contested finding yourself, and the final review must be complete and cover the
final code. Severity map: High = `action_required`, Medium = `remediation_recommended`, Low = `informational`.

`main` is deliberately unprotected, so Gate 5 is the human decision plus the checklist, not a GitHub setting.

## What the Day 10 run showed (ticket #22, heart rate, PR #23)

Result: **reached `main`** (merge commit `f9e031a`), every gate held on the final head `d97a1aa`.

| Step | What happened | Worked? |
|---|---|---|
| Gate 1 | Wisdom found 5 issues; the ticket was revised before labelling | Yes |
| Dev agent (`agent.yml`) | The label started it; Codex opened PR #23 | Yes, but it added an unrequested change (a new error type, 8 test assertions rewritten). It was reverted. |
| Local review (Lane A) | Not run. Lane B has no local review step. | Gap |
| Gate 3 CI | Passed on the head | Yes, after a person approved the first run (GitHub holds CI on bot-opened PRs). The later push ran without approval. |
| Qodo PR review | Did not start on its own. `/review` was commented; the first try hit "trial ended". After that: 1 High and 2 Low. | Partly |
| Fix agent (`agent-fix.yml`) | Failed on both Qodo comments: `Actor 'qodo-code-review[bot]' ... Detected permission: 'none'`. No fix attempted. | **No** |
| Review Resolver skill | Run by a person with the agent: reproduced the High, fixed it with a failing-first test, pushed | Yes, manual |
| Gate 4 re-review | Complete on `d97a1aa`: High implemented, no Medium, one Low still open, one outdated | Yes |
| Gate 5 | CI and review on the same head, Low acknowledged, thresholds accepted by a person, PR text rewritten | Held; merged by a person |

### Where a person stepped in
Revised the ticket, added the label, posted `/review`, approved the first CI run, had the unrequested change
reverted, accepted the heart-rate thresholds (rule 4), acknowledged the Low finding and merged.

### Gaps and improvements
1. **Fix agent cannot start.** The Codex action rejects the Qodo bot as an actor. The workflow must allow that bot (a `.github/` change a person makes).
2. **`/review` is manual on bot-opened PRs.** Qodo reviewed the owner's PRs #19 and #21 within about 80 seconds, and needed `/review` on the automation's PRs #12 and #23. Probably Qodo skipping bot-authored PRs (inferred from the comment history, not documented).
3. **Review Resolver is not in the workflows.** `fix.md` reads Qodo's comment and ignores severity, so the High/Medium/Low gate is applied only by the local agent.
4. **Lane B skips Gate 1 and the local review.** Gate 1 ran only because a person did it before labelling.
5. **Dev agent scope:** Codex changed more than the ticket asked. A reviewer checks the diff against the acceptance criteria.
6. **CI needs approval** on PRs opened by automation.
7. **PR text goes stale:** the agent's report said NOT DONE after the fixes. Gate 5 includes "PR text matches what shipped" for this reason.
