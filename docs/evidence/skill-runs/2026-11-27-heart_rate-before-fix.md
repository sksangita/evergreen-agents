# check-new-vital: heart_rate (audit only)

- Date: 2026-11-27
- Commit (`git rev-parse --short HEAD`): 6de7dbd
- Source: ticket #22 (https://github.com/sksangita/evergreen-agents/issues/22), issue body
- Command: `uv run python .claude/skills/check-new-vital/scripts/check_vital.py heart_rate hr main`
- Exit code: 1

## Full script output

```
OK        REQUIRED_VALUES (core/contracts.py)                             ['bpm']
OK        REQUIRED_UNIT (core/contracts.py)                               bpm
OK        rules in core/rules/thresholds.yaml                             2 rule(s)
OK        rule hr.low_or_high metadata                                    missing []
HUMAN     rule hr.low_or_high source                                      marked unverified: a person must review (rule 4)
OK        rule hr.high metadata                                           missing []
HUMAN     rule hr.high source                                             marked unverified: a person must review (rule 4)
OK        file version vs main                                            2 -> 2, rules unchanged
OK        core/rules/thresholds.yaml header comment names the value       ['bpm']
OK        elder fallback x3 levels (templates.py)                         
OK        caregiver message (agent.py)                                    
OK        evals/heart_rate_cases.yaml                                     8 case(s)
OK        a test reads the eval file                                      test_heart_rate.py
OK        edges at 40 (hr.low_or_high)                                    exact=True above=True below=True
FAIL      edges at 130 (hr.low_or_high)                                   exact=True above=True below=False
OK        edges at 100 (hr.high)                                          exact=True above=True below=True
OK        CLI subcommand 'hr' in --help                                   
OK        'hr' with no value exits 2                                      exit 2
OK        tests/test_cli.py mentions "hr"                                 
OK        README.md mentions health_sentinel hr                           
OK        agents/health_sentinel/__main__.py mentions health_sentinel hr  

FAIL: 1 failing item(s), 2 for a person, 0 unchecked
```

## Step 2: failures

- `evals/heart_rate_cases.yaml:4-5`: the 130 threshold has an exact case (130, amber) and an above case
  (130.01, red), but no case just below it. The script accepts a value in [129, 130); the file has none.
  AGENTS.md rule 4 asks for edges "exactly at a threshold, just below it". Ticket #22 lists only "130 is
  amber, just above 130 is red" for this edge, so its acceptance criteria are met. A case such as 129.99,
  expected amber, would close the gap. Not changed (audit only).

## Step 3: thresholds against ticket #22

No differences.

| Item | Ticket #22 | `core/rules/thresholds.yaml` |
| --- | --- | --- |
| Amber | `bpm > 100` | `hr.high`, line 29: `bpm > 100`, amber |
| Red | `bpm < 40 or bpm > 130` | `hr.low_or_high`, line 23: same, red |
| Source | spec section 6, "General clinical reference ranges" | lines 25 and 31: same, marked demo, unverified |
| id, version, source | required on each rule | present on both |
| File version | 1 to 2 | 2 (line 4) |
| Header names the value | `bpm` | line 3 |

## Step 4: checks the script cannot make

- (a) Elder text, `agents/health_sentinel/templates.py:17-27`: amber and red name heart rate. Green (line 18)
  reuses the generic text, which names no vital. OK.
- (b) `agents/health_sentinel/agent.py:47`: `Heart rate {bpm:g} bpm`, value with unit. OK.
- (c) `tests/test_heart_rate.py:40-61`: wrong unit, missing, extra, zero, negative, NaN, +inf and -inf are
  rejected at creation and at triage. `tests/test_cli.py:50-55` covers 0, -5, nan and inf at the CLI. OK.

## Not checked

- `make lint` and `make test` were not run. Step 4 (c) is from reading the tests.
- The thresholds were compared with the ticket only, not with the spec document or a clinical guideline.
