"""Check that one vital has every piece AGENTS.md rule 5 asks for.

Exit codes: 0 all checked and OK, 1 a FAIL, 3 unknown vital, 4 incomplete (an item is UNCHECKED).

Usage (from the repo root):
  uv run python .claude/skills/check-new-vital/scripts/check_vital.py KIND CLI_NAME [BASE_REF]
Example: ... check_vital.py heart_rate hr main
"""

import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
THRESHOLDS = "core/rules/thresholds.yaml"
RESULTS: list[tuple[str, str, str]] = []
# Blood pressure's eval cases predate the one-file-per-vital naming.
EVAL_FILES = {"blood_pressure": "evals/triage_cases.yaml"}
CLI = ["uv", "run", "python", "-m", "agents.health_sentinel"]


def add(status: str, item: str, detail: str) -> None:
    RESULTS.append((status, item, detail))


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)


def read(path: str) -> str:
    file = ROOT / path
    return file.read_text() if file.exists() else ""


def eval_path(kind: str) -> str:
    return EVAL_FILES.get(kind, f"evals/{kind}_cases.yaml")


def coverage(kind: str, rules: list[dict], cases: list[dict], names: list[str]) -> None:
    """Every number in a rule needs a case exactly at it, within 1 above and within 1 below."""
    if len(names) != 1:
        why = "has no values defined yet" if not names else "has several values; check by hand"
        add("UNCHECKED", "edge coverage", f"{kind} {why}")
        return
    values = [float(c[names[0]]) for c in cases if names[0] in c]
    for rule in rules:
        rid = rule.get("id", "<no id>")
        numbers = re.findall(r"(?<![\w.])\d+(?:\.\d+)?", rule["when"])
        if not numbers:
            add("UNCHECKED", f"edges ({rid})", f"no number found in: {rule['when']}")
        for num in numbers:
            n = float(num)
            exact, above, below = (
                n in values,
                any(n < v <= n + 1 for v in values),
                any(n - 1 <= v < n for v in values),
            )
            status = "OK" if exact and above and below else "FAIL"
            detail = f"exact={exact} above={above} below={below}"
            add(status, f"edges at {n:g} ({rid})", detail)


def check_eval_expectations(vk, names: list[str], cases: list[dict]) -> None:  # noqa: ANN001
    """Run every eval case through the real rules and compare with its `expected` level."""
    from core.contracts import REQUIRED_UNIT, VitalReading
    from core.rules.engine import load_rules, triage_reading

    rules = load_rules()
    bad: list[str] = []
    checked = 0
    for case in cases:
        if "expected" not in case or not all(n in case for n in names):
            continue
        checked += 1
        try:
            reading = VitalReading(
                elder_id="skill-check",
                kind=vk,
                values={n: float(case[n]) for n in names},
                unit=REQUIRED_UNIT[vk],
                measured_at=datetime.now(UTC),
                source="skill",
            )
            got = triage_reading(reading, rules).triage.value
        except Exception as error:  # noqa: BLE001 - report any failure as a finding
            got = f"error: {error}"
        if got != str(case["expected"]):
            bad.append(f"{case.get('name', case)}: expected {case['expected']}, got {got}")
    status = "OK" if checked and not bad else "FAIL"
    add(status, "eval cases agree with the rules", f"{checked} checked; {'; '.join(bad)}")


def check_cli(vk, cli: str, names: list[str]) -> None:  # noqa: ANN001
    helped = run([*CLI, "--help"])
    listed = re.search(rf"[{{,]{re.escape(cli)}[,}}]", helped.stdout) is not None
    add("OK" if listed else "FAIL", f"CLI subcommand '{cli}' listed in --help", "")
    probe = ["150"] * max(len(names), 1)
    good = run([*CLI, cli, *probe])
    reasons = next((ln for ln in good.stdout.splitlines() if ln.startswith("Reasons:")), "")
    named = bool(names) and all(n in reasons for n in names)
    ok = good.returncode == 0 and named
    add(
        "OK" if ok else "FAIL",
        f"'{cli}' builds a {vk.value} reading",
        f"exit {good.returncode}; reasons line {'names' if named else 'does not name'} {names}",
    )
    extra = run([*CLI, cli, *probe, "150"])
    ok = extra.returncode == 2 and "usage:" in extra.stderr
    add("OK" if ok else "FAIL", f"'{cli}' rejects one value too many", f"exit {extra.returncode}")
    for path, needle in (
        ("tests/test_cli.py", f'"{cli}"'),
        ("README.md", f"health_sentinel {cli}"),
        ("agents/health_sentinel/__main__.py", f"health_sentinel {cli}"),
    ):
        add("OK" if needle in read(path) else "FAIL", f"{path} mentions {needle}", "")


def check_version(base: str, document: dict) -> None:
    """Rules that differ from the base ref need a higher file `version`."""
    shown = run(["git", "show", f"{base}:{THRESHOLDS}"])
    if shown.returncode != 0:
        add("UNCHECKED", f"file version vs {base}", "base ref not readable")
        return
    old = yaml.safe_load(shown.stdout)
    same = old["rules"] == document["rules"]
    bumped = int(document["version"]) > int(old["version"])
    detail = f"{old['version']} -> {document['version']}, rules "
    detail += "unchanged" if same else "changed"
    add("OK" if same or bumped else "FAIL", f"file version vs {base}", detail)


def main() -> int:
    kind, cli = sys.argv[1], sys.argv[2]
    base = sys.argv[3] if len(sys.argv) > 3 else "main"
    from agents.health_sentinel import agent, templates
    from core.contracts import REQUIRED_UNIT, REQUIRED_VALUES, Triage, VitalKind

    if kind not in {k.value for k in VitalKind}:
        add("FAIL", "VitalKind member", f"{kind!r} is not in core/contracts.py VitalKind")
        return report(3)
    vk = VitalKind(kind)
    names = sorted(REQUIRED_VALUES.get(vk, []))
    add("OK" if names else "FAIL", "REQUIRED_VALUES (core/contracts.py)", f"{names}")
    unit = REQUIRED_UNIT.get(vk, "missing")
    add("OK" if vk in REQUIRED_UNIT else "FAIL", "REQUIRED_UNIT (core/contracts.py)", unit)

    document = yaml.safe_load(read(THRESHOLDS))
    rules = [r for r in document["rules"] if r["vital"] == kind]
    add("OK" if rules else "FAIL", f"rules in {THRESHOLDS}", f"{len(rules)} rule(s)")
    for r in rules:
        rid = r.get("id", "<no id>")
        missing = [k for k in ("id", "version", "source") if not r.get(k)]
        add("FAIL" if missing else "OK", f"rule {rid} metadata", f"missing {missing}")
        if "unverified" in str(r.get("source", "")).lower():
            add("HUMAN", f"rule {rid} source", "marked unverified: a person must review (rule 4)")
    check_version(base, document)
    header = "\n".join(line for line in read(THRESHOLDS).splitlines() if line.startswith("#"))
    named = kind in header and all(n in header for n in names)
    add("OK" if named else "FAIL", f"{THRESHOLDS} header comment names the value", f"{names}")

    levels = templates.ELDER_FALLBACK_BY_KIND.get(vk, {})
    ok = all(levels.get(t) for t in (Triage.GREEN, Triage.AMBER, Triage.RED))
    add("OK" if ok else "FAIL", "elder fallback x3 levels (templates.py)", "")
    add("OK" if vk in agent._MEASUREMENT_TEXT else "FAIL", "caregiver message (agent.py)", "")

    evals = eval_path(kind)
    cases = yaml.safe_load(read(evals)) or []
    add("OK" if cases else "FAIL", evals, f"{len(cases)} case(s)")
    check_eval_expectations(vk, names, cases) if cases and names else None
    users = [
        p
        for p in (ROOT / "tests").glob("test_*.py")
        if Path(evals).name in p.read_text() and p.name != "test_check_vital_skill.py"
    ]
    if users:
        done = run(["uv", "run", "pytest", "-q", *[str(p) for p in users]])
        tail = done.stdout.strip().splitlines()[-1] if done.stdout.strip() else ""
        add("OK" if done.returncode == 0 else "FAIL", "tests that read the eval file pass", tail)
    else:
        add("FAIL", "a test reads the eval file", "none")
    coverage(kind, rules, cases, names)
    check_cli(vk, cli, names)
    return report(0)


def report(code: int) -> int:
    width = max(len(i) for _, i, _ in RESULTS)
    for status, item, detail in RESULTS:
        print(f"{status:9} {item.ljust(width)}  {detail}")
    count = {s: sum(1 for r in RESULTS if r[0] == s) for s in ("FAIL", "HUMAN", "UNCHECKED")}
    if code or count["FAIL"]:
        verdict, exit_code = "FAIL", code or 1
    elif count["UNCHECKED"]:
        verdict, exit_code = "INCOMPLETE", 4
    else:
        verdict, exit_code = "PASS", 0
    print(
        f"\n{verdict}: {count['FAIL']} failing item(s), {count['HUMAN']} for a person, "
        f"{count['UNCHECKED']} unchecked"
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
