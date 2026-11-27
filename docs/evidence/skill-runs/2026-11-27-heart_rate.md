# check-new-vital: heart_rate (audit only)

- Date: 2026-11-27
- Commit (`git rev-parse --short HEAD`): 6de7dbd, **plus uncommitted changes** (see "Working tree")
- Source: ticket #22 (https://github.com/sksangita/evergreen-agents/issues/22), issue body
- Command: `uv run python .claude/skills/check-new-vital/scripts/check_vital.py heart_rate hr main`
  (run here with `uv run --offline`)
- Result: `PASS: 0 failing item(s), 2 for a person, 0 unchecked`

## Working tree

This result is for the working tree, not for commit 6de7dbd. `git status --short` before this file was written:

```
 M .claude/skills/check-new-vital/scripts/check_vital.py
 M evals/heart_rate_cases.yaml
?? docs/evidence/skill-runs/
```

- `evals/heart_rate_cases.yaml` adds `just_below_upper_amber_edge` (129.99, amber).
- `check_vital.py` changes the empty-values coverage case and tightens the two CLI subcommand checks.

The earlier run in `2026-11-27-heart_rate-before-fix.md` failed on the missing case below 130.

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
OK        evals/heart_rate_cases.yaml                                     9 case(s)
OK        a test reads the eval file                                      test_heart_rate.py
OK        edges at 40 (hr.low_or_high)                                    exact=True above=True below=True
OK        edges at 130 (hr.low_or_high)                                   exact=True above=True below=True
OK        edges at 100 (hr.high)                                          exact=True above=True below=True
OK        CLI subcommand 'hr' listed in --help                            
OK        'hr' is a real subcommand and exits 2 with no value             exit 2
OK        tests/test_cli.py mentions "hr"                                 
OK        README.md mentions health_sentinel hr                           
OK        agents/health_sentinel/__main__.py mentions health_sentinel hr  

PASS: 0 failing item(s), 2 for a person, 0 unchecked
```

## Step 2: failures

None.

## Step 3: thresholds against ticket #22

No differences.

| Item | Ticket #22 | `core/rules/thresholds.yaml` |
| --- | --- | --- |
| Amber | `bpm > 100` | `hr.high`, line 29: `bpm > 100`, amber |
| Red | `bpm < 40 or bpm > 130` | `hr.low_or_high`, line 23: same, red |
| Source | spec section 6, "General clinical reference ranges" | lines 25 and 31: same, marked demo, unverified |
| id, version, source | required on each rule | present on both (lines 20-31) |
| File version | 1 to 2 | 2 (line 4) |
| Header names the value | `bpm` | line 3 |

## Step 4: checks the script cannot make

- (a) Elder text, `agents/health_sentinel/templates.py:17-27`: amber and red name heart rate. Green (line 18)
  reuses the generic text, which names no vital. OK.
- (b) `agents/health_sentinel/agent.py:47`: `Heart rate {bpm:g} bpm`, value with unit. OK.
- (c) `tests/test_heart_rate.py:40-61`: wrong unit, missing, extra, zero, negative, NaN, +inf and -inf are
  rejected at creation and at triage. `tests/test_cli.py:50-55` covers 0, -5, nan and inf at the CLI. OK.

## Also run

`uv run --offline pytest -q -p no:cacheprovider tests/test_heart_rate.py tests/test_cli.py tests/test_rules.py`:
93 passed.

## Not checked

- `make lint` and the full `make test` were not run.
- The thresholds were compared with the ticket only, not with the spec document or a clinical guideline.
