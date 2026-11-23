"""Fail on code-convention violations that are not in the baseline.

Usage, from the repository root:
    python scripts/lint/check_conventions.py                    # check
    python scripts/lint/check_conventions.py --update-baseline  # record the current counts
"""

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from custom_checks import run_custom_checks
from violation import Violation

ROOT = Path(__file__).resolve().parents[2]
LINT_DIR = ROOT / "scripts" / "lint"
BASELINE = LINT_DIR / "baseline.json"
SUITE_DOCSTRINGS = "plugins/suvereo-common/"


def run_ruff() -> list[Violation]:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--config",
            str(LINT_DIR / "ruff-conventions.toml"),
            "--output-format",
            "json",
            "--exit-zero",
            "server",
            "plugins",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    violations = []
    for item in json.loads(result.stdout):
        path = Path(item["filename"]).relative_to(ROOT)
        code = item["code"]
        # Docstrings are required only on the public interfaces in suvereo-common.
        if code.startswith("D1") and not path.as_posix().startswith(SUITE_DOCSTRINGS):
            continue
        violations.append(Violation(path, item["location"]["row"], code, item["message"]))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args()

    violations = run_ruff() + run_custom_checks(ROOT)
    counts = Counter(violation.key for violation in violations)

    if args.update_baseline:
        BASELINE.write_text(json.dumps(dict(sorted(counts.items())), indent=2) + "\n")
        print(f"Baseline updated: {sum(counts.values())} existing violations.")
        return 0

    baseline = json.loads(BASELINE.read_text())
    new = [v for v in violations if counts[v.key] > baseline.get(v.key, 0)]
    if new:
        print("New code-convention violations (only the ones beyond the baseline fail):\n")
        print("\n".join(str(violation) for violation in sorted(new, key=str)))
        return 1

    fixed = sum(baseline.values()) - sum(counts.values())
    if fixed > 0:
        print(f"{fixed} baseline violations are fixed; run with --update-baseline to lock that in.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
