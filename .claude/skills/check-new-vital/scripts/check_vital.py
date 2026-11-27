"""Check that one vital has every piece AGENTS.md rule 5 asks for. Exit 1 if any item FAILs.

Usage (from the repo root):
  uv run python .claude/skills/check-new-vital/scripts/check_vital.py KIND CLI_NAME [BASE_REF]
Example: ... check_vital.py heart_rate hr main
"""

import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
THRESHOLDS = "core/rules/thresholds.yaml"
RESULTS: list[tuple[str, str, str]] = []


def add(status: str, item: str, detail: str) -> None:
    RESULTS.append((status, item, detail))


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)


def read(path: str) -> str:
    file = ROOT / path
    return file.read_text() if file.exists() else ""


def coverage(kind: str, rules: list[dict], cases: list[dict], names: list[str]) -> None:
    if not names:
        add("UNCHECKED", "edge coverage", f"{kind} has no values defined yet")
        return
    if len(names) != 1:
        add("UNCHECKED", "edge coverage", f"{kind} has several values; check edges by hand")
        return
    values = [float(c[names[0]]) for c in cases if names[0] in c]
    for rule in rules:
        for _op, num in re.findall(r"(>=|<=|>|<)\s*([0-9.]+)", rule["when"]):
            n = float(num)
            exact, above, below = (
                n in values,
                any(n < v <= n + 1 for v in values),
                any(n - 1 <= v < n for v in values),
            )
            status = "OK" if exact and above and below else "FAIL"
            add(
                status,
                f"edges at {n:g} ({rule['id']})",
                f"exact={exact} above={above} below={below}",
            )


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
    add(
        "OK" if vk in REQUIRED_UNIT else "FAIL",
        "REQUIRED_UNIT (core/contracts.py)",
        REQUIRED_UNIT.get(vk, "missing"),
    )

    document = yaml.safe_load(read(THRESHOLDS))
    rules = [r for r in document["rules"] if r["vital"] == kind]
    add("OK" if rules else "FAIL", f"rules in {THRESHOLDS}", f"{len(rules)} rule(s)")
    for r in rules:
        missing = [k for k in ("id", "version", "source") if not r.get(k)]
        add("FAIL" if missing else "OK", f"rule {r.get('id')} metadata", f"missing {missing}")
        if "unverified" in str(r.get("source", "")).lower():
            add(
                "HUMAN",
                f"rule {r['id']} source",
                "marked unverified: a person must review (rule 4)",
            )
    shown = run(["git", "show", f"{base}:{THRESHOLDS}"])
    if shown.returncode == 0:
        old = yaml.safe_load(shown.stdout)
        same = old["rules"] == document["rules"]
        bumped = int(document["version"]) > int(old["version"])
        status = "OK" if same or bumped else "FAIL"
        add(
            status,
            f"file version vs {base}",
            f"{old['version']} -> {document['version']}, "
            f"rules {'unchanged' if same else 'changed'}",
        )
    else:
        add("UNCHECKED", f"file version vs {base}", "base ref not readable")
    header = "\n".join(line for line in read(THRESHOLDS).splitlines() if line.startswith("#"))
    named = kind in header and all(n in header for n in names)
    add("OK" if named else "FAIL", f"{THRESHOLDS} header comment names the value", f"{names}")

    levels = templates.ELDER_FALLBACK_BY_KIND.get(vk, {})
    ok = all(levels.get(t) for t in (Triage.GREEN, Triage.AMBER, Triage.RED))
    add("OK" if ok else "FAIL", "elder fallback x3 levels (templates.py)", "")
    add("OK" if vk in agent._MEASUREMENT_TEXT else "FAIL", "caregiver message (agent.py)", "")

    evals = f"evals/{kind}_cases.yaml"
    cases = yaml.safe_load(read(evals)) or []
    add("OK" if cases else "FAIL", evals, f"{len(cases)} case(s)")
    used = [p.name for p in (ROOT / "tests").glob("test_*.py") if Path(evals).name in p.read_text()]
    add("OK" if used else "FAIL", "a test reads the eval file", ", ".join(used) or "none")
    coverage(kind, rules, cases, names)

    helped = run(["uv", "run", "python", "-m", "agents.health_sentinel", "--help"])
    listed = re.search(rf"[{{,]{re.escape(cli)}[,}}]", helped.stdout) is not None
    add("OK" if listed else "FAIL", f"CLI subcommand '{cli}' listed in --help", "")
    bare = run(["uv", "run", "python", "-m", "agents.health_sentinel", cli])
    add(
        "OK" if bare.returncode == 2 and "invalid choice" not in bare.stderr else "FAIL",
        f"'{cli}' is a real subcommand and exits 2 with no value",
        f"exit {bare.returncode}" + (", invalid choice" if "invalid choice" in bare.stderr else ""),
    )
    for path, needle in (
        ("tests/test_cli.py", f'"{cli}"'),
        ("README.md", f"health_sentinel {cli}"),
        ("agents/health_sentinel/__main__.py", f"health_sentinel {cli}"),
    ):
        add("OK" if needle in read(path) else "FAIL", f"{path} mentions {needle}", "")
    return report(0)


def report(code: int) -> int:
    width = max(len(i) for _, i, _ in RESULTS)
    for status, item, detail in RESULTS:
        print(f"{status:9} {item.ljust(width)}  {detail}")
    fails = sum(1 for s, _, _ in RESULTS if s == "FAIL")
    print(
        f"\n{'PASS' if not fails and not code else 'FAIL'}: {fails} failing item(s), "
        f"{sum(1 for s, _, _ in RESULTS if s == 'HUMAN')} for a person, "
        f"{sum(1 for s, _, _ in RESULTS if s == 'UNCHECKED')} unchecked"
    )
    return code or (1 if fails else 0)


if __name__ == "__main__":
    raise SystemExit(main())
