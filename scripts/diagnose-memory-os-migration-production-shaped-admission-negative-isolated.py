#!/usr/bin/env python3
"""Read-only isolated migration-negative diagnosis with bounded, non-secret stage output."""

from __future__ import annotations

import hashlib
import json
import os
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/migration-production-shaped-negative-isolation.yml"
NEGATIVE = "scripts/validate-memory-os-migration-production-shaped-admission-negative.py"
SELF = "scripts/diagnose-memory-os-migration-production-shaped-admission-negative-isolated.py"
WORKFLOW_BLOB_SHA = "a469a2a75bb86a044728f8f1642b2d47848043f4"
CHECKOUT = "actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
STAGES = frozenset((
    "load_writer",
    "expect_actual_cli_authority_substitution_rejected",
    "expect_rejected",
    "expect_reconcile_rejected_without_mutation",
    "expect_contract_append_rollback_guard_rejected",
    "expect_append_rollback",
    "expect_upstream_reconcile_rejected_without_mutation",
    "expect_noncanonical_ledger_rows_rejected",
    "expect_canonical_writer_delegation",
    "expect_release_registry_delegation",
    "expect_release_pair_registry_delegation",
    "expect_generic_review_refs_rejected",
    "expect_external_evidence_containment_rejected",
    "expect_mutated_review_history_rejected",
    "expect_append_lock_contract_drift_rejected",
))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("migration isolation source guard: " + message)


def git_blob_sha(value: str) -> str:
    data = value.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def validate_workflow(source: str) -> None:
    required = (
        "  pull_request:\n    branches:\n      - so\n",
        "  push:\n    branches:\n      - so\n",
        "  workflow_dispatch:\n",
        "permissions:\n  contents: read\n",
        "      contents: read\n",
        "persist-credentials: false",
        "fetch-depth: 0",
        CHECKOUT,
        SETUP,
        'test "${GITHUB_BASE_REF:-}" = "so"',
        'test "${GITHUB_REF:-}" = "refs/heads/so"',
        '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]',
        'test "$(git rev-parse HEAD)" = "$expected"',
        'test -z "$(git status --porcelain)"',
        "python " + SELF + " --verify-source",
        "python " + SELF + "\n",
    )
    for token in required:
        require(source.count(token) >= 1, "missing reviewed workflow guard")
    for forbidden in ("contents: write", "persist-credentials: true", "pull_request_target:", 'cat "$log"', "secrets."):
        require(forbidden not in source, "unreviewed write/secret/log source")
    require(git_blob_sha(source) == WORKFLOW_BLOB_SHA, "complete workflow blob changed")


def verify_source() -> int:
    require(WORKFLOW.is_file() and not WORKFLOW.is_symlink(), "workflow missing or symlink")
    source = WORKFLOW.read_text(encoding="utf-8")
    validate_workflow(source)
    for original, replacement in (
        (CHECKOUT, "actions/checkout@v4"),
        ("persist-credentials: false", "persist-credentials: true"),
        ('test "${GITHUB_REF:-}" = "refs/heads/so"', "true"),
        ("contents: read", "contents: write"),
        ("python " + SELF + "\n", "echo skip\n"),
    ):
        require(original in source, "negative mutation anchor missing")
        changed = source.replace(original, replacement, 1)
        try:
            validate_workflow(changed)
        except SystemExit:
            continue
        raise SystemExit("migration isolation source guard accepted weakened mutation")
    print("PASS: isolated migration-negative workflow source and five fail-closed mutations")
    return 0


def inner(stage_path: Path) -> int:
    negative = (ROOT / NEGATIVE).resolve(strict=True)
    stage_path.write_text("bootstrap", encoding="ascii")
    sys.path.insert(0, str(negative.parent))

    def trace(frame, event, arg):
        if (event == "call" and Path(frame.f_code.co_filename) == negative
                and frame.f_back is not None and frame.f_back.f_code.co_name == "main"
                and frame.f_code.co_name in STAGES):
            stage_path.write_text(frame.f_code.co_name, encoding="ascii")
        return trace

    sys.settrace(trace)
    try:
        runpy.run_path(str(negative), run_name="__main__")
    except SystemExit as exc:
        return 0 if exc.code is None or exc.code == 0 else 1
    except BaseException:
        return 1
    finally:
        sys.settrace(None)
    return 0



def probe_append_lock(clone: Path, env: dict[str, str]) -> tuple[str, str]:
    """Classify a known negative failure using fixed labels; never print validator output."""
    validator = clone / "scripts/validate-memory-os-migration-production-shaped-admission.py"
    contract = clone / "contracts/operations/migration-production-shaped-admission-contract.v1.json"
    original = contract.read_bytes()
    try:
        baseline = subprocess.run([sys.executable, str(validator)], cwd=clone, env=env,
                                  capture_output=True, text=True, timeout=120, check=False)
        baseline_label = "PASS" if baseline.returncode == 0 else "FAIL"
        data = json.loads(original.decode("utf-8"))
        data["appendLockPath"] = "contracts/operations/.migration-production-shaped-admission-negative.lock"
        contract.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        result = subprocess.run([sys.executable, str(validator)], cwd=clone, env=env,
                                capture_output=True, text=True, timeout=120, check=False)
        output = result.stdout + result.stderr
        if result.returncode == 0:
            label = "UNEXPECTED_ACCEPTANCE"
        elif "append lock binding drift" in output:
            label = "EXPECTED_LOCK_REJECTION"
        elif "canonical release baseline authority validation failed" in output:
            label = "UPSTREAM_RELEASE_VALIDATION"
        elif "canonical environment generation authority validation failed" in output:
            label = "UPSTREAM_GENERATION_VALIDATION"
        elif "working tree must be clean" in output:
            label = "WORKTREE_PRECONDITION"
        else:
            label = "OTHER_FAILURE"
        return baseline_label, label
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return "UNKNOWN", "PROBE_ERROR"
    finally:
        contract.write_bytes(original)


def run_isolated() -> int:
    original = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    require(len(original) == 40, "source commit unavailable")
    with tempfile.TemporaryDirectory(prefix="migration-negative-isolated-") as temp:
        sandbox = Path(temp)
        clone = sandbox / "repo"
        home = sandbox / "home"
        home.mkdir()
        subprocess.run(["git", "clone", "--local", "--no-hardlinks", "--quiet", str(ROOT), str(clone)],
                       check=True, capture_output=True)
        subprocess.run(["git", "checkout", "--detach", "--quiet", original], cwd=clone, check=True, capture_output=True)
        checked = subprocess.run(["git", "rev-parse", "HEAD"], cwd=clone, capture_output=True, text=True, check=True).stdout.strip()
        require(checked == original, "disposable clone source drift")
        stage_path = sandbox / "stage"
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(home),
               "PYTHONDONTWRITEBYTECODE": "1", "GIT_TERMINAL_PROMPT": "0"}
        completed = subprocess.run([sys.executable, str(clone / SELF), "--inner", str(stage_path)],
                                   cwd=clone, env=env, capture_output=True, text=True, timeout=240, check=False)
        stage = stage_path.read_text(encoding="ascii").strip() if stage_path.is_file() else "bootstrap"
        require(stage == "bootstrap" or stage in STAGES, "unreviewed diagnostic stage")
        if completed.returncode != 0:
            if stage == "expect_append_lock_contract_drift_rejected":
                baseline, classification = probe_append_lock(clone, env)
                print("Migration append-lock probe: baseline=" + baseline + " mutated=" + classification)
            print("FAIL: migration negative isolated stage=" + stage + " (raw validator output suppressed)")
            return 1
        print("PASS: migration negative in disposable clone; last_stage=" + stage)
        return 0


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--verify-source":
        raise SystemExit(verify_source())
    if len(sys.argv) == 3 and sys.argv[1] == "--inner":
        raise SystemExit(inner(Path(sys.argv[2])))
    if len(sys.argv) == 1:
        raise SystemExit(run_isolated())
    raise SystemExit("migration isolation: invalid invocation")
