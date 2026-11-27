"""Run expected edge readings through the demo CLI and compare. Exit 1 on any mismatch.

Usage (from the repo root):
  uv run python .claude/skills/check-threshold-edges/scripts/run_edges.py heart_rate EXPECTED.yaml
"""

import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
CLI = {"heart_rate": ("hr", ["bpm"])}  # single-value vitals only; others: stop and ask
THRESHOLDS = ROOT / "core/rules/thresholds.yaml"


def run_cli(sub: str, args: list[str]) -> tuple[int, str, str]:
    cmd = ["uv", "run", "python", "-m", "agents.health_sentinel", sub, *args]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    out = p.stdout
    triage = re.search(r"Triage:\s+(\w+)", out)
    esc = re.search(r"Escalate:\s+(\w+)", out)
    return p.returncode, (triage.group(1).lower() if triage else ""), (esc.group(1) if esc else "")


def main() -> int:
    vital, expected_path = sys.argv[1], Path(sys.argv[2])
    if vital not in CLI:
        print(f"STOP: vital {vital!r} not supported by this script; ask the user.")
        return 3
    sub, names = CLI[vital]
    cases = yaml.safe_load(expected_path.read_text())
    rules = [r for r in yaml.safe_load(THRESHOLDS.read_text())["rules"] if r["vital"] == vital]
    failures = 0

    print(f"Rule metadata ({THRESHOLDS.relative_to(ROOT)}, file version "
          f"{yaml.safe_load(THRESHOLDS.read_text())['version']}):")
    for r in rules:
        ok = all(r.get(k) for k in ("id", "version", "source"))
        failures += not ok
        print(f"  {'OK  ' if ok else 'FAIL'} {r['id']} v{r.get('version')} when: {r['when']}")

    print("\nCLI results (expected vs actual):")
    for c in cases:
        value = c[names[0]]
        code, triage, esc = run_cli(sub, [str(value)])
        want_exit = c.get("exit", 0)
        same = want_exit != 0 or (triage == c["triage"] and esc == c["escalate"])
        ok = code == want_exit and same
        failures += not ok
        want = f"exit {want_exit}" if want_exit else f"{c['triage']}/escalate {c['escalate']}"
        got = f"exit {code}" if code else f"{triage}/escalate {esc}"
        print(f"  {'OK  ' if ok else 'FAIL'} {names[0]}={value}: expected {want}, got {got}")

    print("\nThreshold coverage in the expected file (exact, just above, just below):")
    values = [float(c[names[0]]) for c in cases if "exit" not in c]
    for r in rules:
        for _op, num in re.findall(r"(>=|<=|>|<)\s*([0-9.]+)", r["when"]):
            n = float(num)
            exact = n in values
            above = any(n < v <= n + 1 for v in values)
            below = any(n - 1 <= v < n for v in values)
            ok = exact and above and below
            failures += not ok
            mark = "OK  " if ok else "FAIL"
            print(f"  {mark} {r['id']} threshold {n:g}: exact={exact} above={above} below={below}")

    print(f"\n{'PASS' if not failures else 'FAIL'}: {failures} problem(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
