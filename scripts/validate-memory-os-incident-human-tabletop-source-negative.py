#!/usr/bin/env python3
"""Pin human-tabletop sourceCommitSha, reconcile authority identity and rollback."""

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


def file_mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_writer():
    return load_module("incident_human_tabletop_writer", WRITER)


def load_reconciler():
    return load_module("incident_human_tabletop_reconciler", RECONCILER)


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


def expect_reconcile_authority_identity() -> None:
    module = load_reconciler()
    module.enforce_runtime_authorities()
    substitutions = (
        ("WRITER", ROOT / "README.md"),
        ("VALIDATOR", ROOT / "scripts/validate-memory-os-operability.py"),
        ("INCIDENT_TABLETOP_VALIDATOR", ROOT / "scripts/validate-memory-os-incident-response.py"),
        ("INCIDENT_RESPONSE_VALIDATOR", ROOT / "scripts/validate-memory-os-incident-tabletop.py"),
        ("OPERABILITY_VALIDATOR", ROOT / "scripts/validate-memory-os-incident-response.py"),
        ("WORKFLOW", ROOT / ".github/workflows/incident-control-exercise.yml"),
        ("LEDGER", ROOT / "docs/evidence"),
    )
    for field, substitute in substitutions:
        original = getattr(module, field)
        try:
            setattr(module, field, substitute)
            try:
                module.enforce_runtime_authorities()
            except module.Fail:
                pass
            else:
                raise RuntimeError(f"human tabletop reconciler accepted {field} authority substitution")
        finally:
            setattr(module, field, original)
    module.enforce_runtime_authorities()


def expect_second_replace_rollback() -> None:
    module = load_reconciler()
    contract_bytes = CONTRACT.read_bytes()
    status_bytes = STATUS.read_bytes()
    contract_mode = file_mode(CONTRACT)
    status_mode = file_mode(STATUS)
    original_replace = module.os.replace
    calls = 0

    def fail_second_replace(source, target):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic second authority replace rejection")
        return original_replace(source, target)

    try:
        module.os.replace = fail_second_replace
        try:
            module.commit_validated_pair(module.load(CONTRACT), module.load(STATUS))
        except OSError:
            pass
        else:
            raise RuntimeError("human tabletop reconciler accepted second authority replace rejection")
    finally:
        module.os.replace = original_replace

    if CONTRACT.read_bytes() != contract_bytes or STATUS.read_bytes() != status_bytes:
        raise RuntimeError("second authority replace rejection did not restore human tabletop authority bytes")
    if file_mode(CONTRACT) != contract_mode or file_mode(STATUS) != status_mode:
        raise RuntimeError("second authority replace rejection did not restore human tabletop authority modes")
    if list(CONTRACT.parent.glob(f".{CONTRACT.name}.*.tmp")):
        raise RuntimeError("second authority replace rejection left contract temp residue")
    if list(STATUS.parent.glob(f".{STATUS.name}.*.tmp")):
        raise RuntimeError("second authority replace rejection left status temp residue")


def expect_post_write_rollback() -> None:
    validator_bytes = VALIDATOR.read_bytes()
    validator_mode = file_mode(VALIDATOR)
    contract_bytes = CONTRACT.read_bytes()
    status_bytes = STATUS.read_bytes()
    contract_mode = file_mode(CONTRACT)
    status_mode = file_mode(STATUS)
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
        if file_mode(CONTRACT) != contract_mode or file_mode(STATUS) != status_mode:
            raise RuntimeError("post-write failure changed human tabletop authority modes")
    finally:
        VALIDATOR.write_bytes(validator_bytes)
        os.chmod(VALIDATOR, validator_mode)
        POST_WRITE_MARKER.unlink(missing_ok=True)
        CONTRACT.write_bytes(contract_bytes)
        STATUS.write_bytes(status_bytes)
        os.chmod(CONTRACT, contract_mode)
        os.chmod(STATUS, status_mode)


def expect_aggregate_post_write_rollback() -> None:
    operability_bytes = OPERABILITY_VALIDATOR.read_bytes()
    operability_mode = file_mode(OPERABILITY_VALIDATOR)
    contract_bytes = CONTRACT.read_bytes()
    status_bytes = STATUS.read_bytes()
    contract_mode = file_mode(CONTRACT)
    status_mode = file_mode(STATUS)
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
        if file_mode(CONTRACT) != contract_mode or file_mode(STATUS) != status_mode:
            raise RuntimeError("aggregate failure changed human tabletop authority modes")
    finally:
        OPERABILITY_VALIDATOR.write_bytes(operability_bytes)
        os.chmod(OPERABILITY_VALIDATOR, operability_mode)
        CONTRACT.write_bytes(contract_bytes)
        STATUS.write_bytes(status_bytes)
        os.chmod(CONTRACT, contract_mode)
        os.chmod(STATUS, status_mode)


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
    expect_reconcile_authority_identity()
    expect_second_replace_rollback()
    expect_post_write_rollback()
    expect_aggregate_post_write_rollback()
    print("PASS: human tabletop source authority is ancestor-only without creating human evidence")
    print("PASS: human tabletop reconcile executable authorities reject substitution")
    print("PASS: human tabletop second replace rejection rolls back contract/status bytes and modes")
    print("PASS: human tabletop post-write and aggregate validation failures roll back contract and status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
