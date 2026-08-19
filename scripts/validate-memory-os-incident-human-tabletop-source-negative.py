#!/usr/bin/env python3
"""Pin human-tabletop sourceCommitSha and reconcile rollback authority."""

from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-incident-human-tabletop.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-incident-human-tabletops.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-incident-human-tabletops.py"
CONTRACT = ROOT / "contracts/operations/incident-human-tabletop-evidence-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
POST_WRITE_MARKER = Path("/tmp/memory-os-incident-human-tabletop-post-write-negative.count")


def load_writer():
    spec = importlib.util.spec_from_file_location("incident_human_tabletop_writer", WRITER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load human tabletop writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def descendant_commit() -> str:
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip()
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "tabletop-negative",
        "GIT_AUTHOR_EMAIL": "tabletop-negative@example.invalid",
        "GIT_COMMITTER_NAME": "tabletop-negative",
        "GIT_COMMITTER_EMAIL": "tabletop-negative@example.invalid",
    })
    return subprocess.check_output(
        ["git", "commit-tree", tree, "-p", "HEAD", "-m", "human tabletop non-ancestor fixture"],
        cwd=ROOT,
        env=env,
        text=True,
    ).strip()


def expect_post_write_rollback() -> None:
    validator_bytes = VALIDATOR.read_bytes()
    contract_bytes = CONTRACT.read_bytes()
    status_bytes = STATUS.read_bytes()
    wrapper = f'''#!/usr/bin/env python3
from pathlib import Path
marker = Path({str(POST_WRITE_MARKER)!r})
count = int(marker.read_text(encoding="utf-8")) if marker.exists() else 0
marker.write_text(str(count + 1), encoding="utf-8")
raise SystemExit(0 if count == 0 else 1)
'''
    try:
        POST_WRITE_MARKER.unlink(missing_ok=True)
        VALIDATOR.write_text(wrapper, encoding="utf-8")
        completed = subprocess.run(
            ["python", str(RECONCILER)],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if completed.returncode == 0:
            raise RuntimeError("human tabletop reconciler accepted injected post-write validator failure")
        if CONTRACT.read_bytes() != contract_bytes:
            raise RuntimeError("post-write failure left human tabletop contract mutated")
        if STATUS.read_bytes() != status_bytes:
            raise RuntimeError("post-write failure left production operability status mutated")
    finally:
        VALIDATOR.write_bytes(validator_bytes)
        POST_WRITE_MARKER.unlink(missing_ok=True)
        CONTRACT.write_bytes(contract_bytes)
        STATUS.write_bytes(status_bytes)


def expect_aggregate_post_write_rollback() -> None:
    operability_bytes = OPERABILITY_VALIDATOR.read_bytes()
    contract_bytes = CONTRACT.read_bytes()
    status_bytes = STATUS.read_bytes()
    try:
        OPERABILITY_VALIDATOR.write_text("raise SystemExit(1)\n", encoding="utf-8")
        completed = subprocess.run(
            ["python", str(RECONCILER)],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if completed.returncode == 0:
            raise RuntimeError("human tabletop reconciler accepted aggregate operability failure")
        if CONTRACT.read_bytes() != contract_bytes:
            raise RuntimeError("aggregate failure left human tabletop contract mutated")
        if STATUS.read_bytes() != status_bytes:
            raise RuntimeError("aggregate failure left production operability status mutated")
    finally:
        OPERABILITY_VALIDATOR.write_bytes(operability_bytes)
        CONTRACT.write_bytes(contract_bytes)
        STATUS.write_bytes(status_bytes)


def main() -> int:
    writer = load_writer()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if not writer.commit_exists(head) or not writer.source_is_ancestor(head):
        raise RuntimeError("current HEAD must be a valid tabletop source authority")
    future = descendant_commit()
    if not writer.commit_exists(future):
        raise RuntimeError("negative descendant commit was not created")
    if writer.source_is_ancestor(future):
        raise RuntimeError("future/side commit was accepted as human tabletop source authority")
    expect_post_write_rollback()
    expect_aggregate_post_write_rollback()
    print("PASS: human tabletop source authority is ancestor-only without creating human evidence")
    print("PASS: human tabletop post-write and aggregate validation failures roll back contract and status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
