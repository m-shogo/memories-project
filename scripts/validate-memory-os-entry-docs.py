#!/usr/bin/env python3
"""Validate current Memory OS entrypoint documents against repository authority."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

ENTRYPOINTS = {
    "README.md": {
        "required": [
            "docs/memory-os-current-authority-order-round-10-operability.md",
            "contracts/operations/production-operability-status.json",
            "productionDecision: `NO_GO`",
            "Operations hardening before feature breadth",
        ],
        "forbidden": [
            "Round 9 Security Authority](docs/memory-os-current-authority-order-round-9-security.md)\n2.",
            "Immediate next checkpoint:\n\n```txt\nHTTP server main",
            "the missing layers are the executable server, Apply/Memory persistence and the clients",
        ],
    },
    "SECURITY.md": {
        "required": [
            "docs/memory-os-current-authority-order-round-10-operability.md",
            "contracts/operations/production-operability-status.json",
            "Production remains `NO_GO`",
            "Apple code exchange is implemented",
        ],
        "forbidden": [
            "there is no executable server yet",
            "Apple code exchange/secret rotation and concrete replay/session stores",
            "the sole remaining Apple gate",
            "every push since has run green",
        ],
    },
    "services/import-api/README.md": {
        "required": [
            "The executable HTTP server exists",
            "Apple code exchange, replay protection, account binding and session issuance exist",
            "Production remains `NO_GO`",
            "docs/memory-os-current-authority-order-round-10-operability.md",
        ],
        "forbidden": [
            "does not expose a production server",
            "Apple code exchange/secret rotation and concrete replay/session stores",
            "complete deletion fencing",
            "the branch has run green since",
        ],
    },
    "docs/memory-os-current-authority-order-round-10-operability.md": {
        "required": [
            "Implementation truth:",
            "Readiness judgement:",
            "current code, migrations and executable tests for implementation facts",
            "scripts/validate-memory-os-entry-docs.py",
            "a checkpoint statement is not stronger than current code and tests",
        ],
        "forbidden": [
            "newest applicable implementation checkpoint\n7. current code",
        ],
    },
    "docs/memory-os-current-authority-order-round-9-security.md": {
        "required": [
            "SUBORDINATE TO ROUND 10",
            "memory-os-current-authority-order-round-10-operability.md",
            "executable HTTP server exists",
            "Production-readiness judgement is governed by",
        ],
        "forbidden": [
            "# Memory OS Current Authority Order — Round 9 Security",
            "there is no executable server yet",
            "Apple code exchange/secret rotation/replay/session persistence",
        ],
    },
}

LEARNING_GUARDS = (
    "scripts/validate-autonomous-learning-system.py",
    "scripts/validate-autonomous-learning-system-negative.py",
)
LEARNING_GUARD_TIMEOUT_SECONDS = 120
MIN_LEARNING_NEGATIVE_CASES = 69


def learning_guard_passed(relative: str, completed: subprocess.CompletedProcess[str]) -> bool:
    """An exit-zero child without its actual PASS proof is not an executed guard."""
    if completed.returncode != 0 or completed.stderr:
        return False
    output = completed.stdout.strip()
    if relative == LEARNING_GUARDS[0]:
        return output == "Autonomous improvement/learning contract validation PASS"
    if relative == LEARNING_GUARDS[1]:
        prefix = "Autonomous learning negative validation PASS ("
        suffix = " fail-closed cases)"
        if not output.startswith(prefix) or not output.endswith(suffix):
            return False
        count = output[len(prefix):-len(suffix)]
        return count.isascii() and count.isdecimal() and int(count) >= MIN_LEARNING_NEGATIVE_CASES
    return False


def prove_learning_guard_classifier(failures: list[str]) -> None:
    """Prove that a no-op, truncated suite or spurious success cannot pass."""
    positive = "Autonomous improvement/learning contract validation PASS\n"
    negative = f"Autonomous learning negative validation PASS ({MIN_LEARNING_NEGATIVE_CASES} fail-closed cases)\n"
    cases = (
        ("positive", LEARNING_GUARDS[0], 0, positive, "", True),
        ("negative", LEARNING_GUARDS[1], 0, negative, "", True),
        ("expanded negative", LEARNING_GUARDS[1], 0,
         f"Autonomous learning negative validation PASS ({MIN_LEARNING_NEGATIVE_CASES + 1} fail-closed cases)\n", "", True),
        ("missing output", LEARNING_GUARDS[0], 0, "", "", False),
        ("nonzero with success text", LEARNING_GUARDS[0], 1, positive, "", False),
        ("stderr with success text", LEARNING_GUARDS[0], 0, positive, "injected", False),
        ("truncated negative", LEARNING_GUARDS[1], 0,
         f"Autonomous learning negative validation PASS ({MIN_LEARNING_NEGATIVE_CASES - 1} fail-closed cases)\n", "", False),
        ("nonnumeric count", LEARNING_GUARDS[1], 0,
         "Autonomous learning negative validation PASS (False fail-closed cases)\n", "", False),
        ("extra output", LEARNING_GUARDS[1], 0, negative + "ignored", "", False),
        ("unbound guard", "scripts/unbound-guard.py", 0, positive, "", False),
    )
    for name, relative, code, stdout, stderr, expected in cases:
        completed = subprocess.CompletedProcess([], code, stdout, stderr)
        if learning_guard_passed(relative, completed) is not expected:
            failures.append(f"learning guard success classifier misclassified: {name}")


def validate_learning_guards(failures: list[str]) -> None:
    """Keep autonomous-learning guards reachable from the existing operability CI path."""
    if len(LEARNING_GUARDS) != len(set(LEARNING_GUARDS)):
        failures.append("duplicate autonomous-learning guard binding")
        return
    if not 1 <= LEARNING_GUARD_TIMEOUT_SECONDS <= 300:
        failures.append("autonomous-learning guard timeout must remain bounded to 1..300 seconds")
        return
    prove_learning_guard_classifier(failures)
    if failures:
        return
    for relative in LEARNING_GUARDS:
        path = REPO_ROOT / relative
        if not path.is_file():
            failures.append(f"missing autonomous-learning guard: {relative}")
            continue
        try:
            completed = subprocess.run(
                [sys.executable, str(path), "--repo-root", str(REPO_ROOT)],
                cwd=REPO_ROOT,
                check=False,
                text=True,
                capture_output=True,
                timeout=LEARNING_GUARD_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            failures.append(
                f"autonomous-learning guard timed out after {LEARNING_GUARD_TIMEOUT_SECONDS}s: {relative}"
            )
            continue
        if not learning_guard_passed(relative, completed):
            failures.append(
                f"autonomous-learning guard missing verified PASS: {relative} "
                f"(exit {completed.returncode})"
            )
        else:
            # Emit only a previously validated, single-line success marker.
            # This is CI execution evidence, never production readiness.
            print(f"autonomous-learning guard verified: {completed.stdout.strip()}")


def main() -> int:
    failures: list[str] = []
    for relative, rules in ENTRYPOINTS.items():
        path = REPO_ROOT / relative
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            failures.append(f"missing entrypoint: {relative}")
            continue

        for phrase in rules["required"]:
            if phrase not in text:
                failures.append(f"{relative}: missing required current-authority phrase: {phrase!r}")
        for phrase in rules["forbidden"]:
            if phrase in text:
                failures.append(f"{relative}: contains stale or unsafe completion claim: {phrase!r}")

        lowered = text.lower()
        if "production ready" in lowered and "not production ready" not in lowered:
            failures.append(f"{relative}: unqualified production-ready wording")

    validate_learning_guards(failures)

    if failures:
        print("ENTRYPOINT DOCUMENT VALIDATION FAILED", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("Memory OS entrypoint document validation PASS")
    print(f"entrypoints: {len(ENTRYPOINTS)}")
    print(f"autonomous-learning guards: {len(LEARNING_GUARDS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
