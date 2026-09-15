#!/usr/bin/env python3
"""Pin human-tabletop sourceCommitSha and exercise reconcile rollback read-only."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-incident-human-tabletop.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-incident-human-tabletops.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-incident-human-tabletops.py"
CONTRACT = ROOT / "contracts/operations/incident-human-tabletop-evidence-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL = (CONTRACT, STATUS, VALIDATOR, OPERABILITY_VALIDATOR, RECONCILER)


def file_mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def snapshot(paths=CANONICAL):
    return {path: (path.read_bytes(), file_mode(path)) for path in paths}


def assert_unchanged(before, context: str) -> None:
    for path, (payload, mode) in before.items():
        if path.read_bytes() != payload:
            raise RuntimeError(f"{context} mutated canonical bytes: {path.relative_to(ROOT)}")
        if file_mode(path) != mode:
            raise RuntimeError(f"{context} mutated canonical mode: {path.relative_to(ROOT)}")


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
        cwd=ROOT, env=env, text=True,
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


def fixture_pair(module, directory: Path) -> tuple[Path, Path]:
    contract = directory / CONTRACT.name
    status = directory / STATUS.name
    shutil.copy2(CONTRACT, contract)
    shutil.copy2(STATUS, status)
    module.CONTRACT = contract
    module.STATUS = status
    return contract, status


def assert_fixture_restored(contract: Path, status: Path, before, context: str) -> None:
    for path in (contract, status):
        payload, mode = before[path]
        if path.read_bytes() != payload or file_mode(path) != mode:
            raise RuntimeError(f"{context} did not restore fixture authority: {path.name}")
        if list(path.parent.glob(f".{path.name}.*.tmp")):
            raise RuntimeError(f"{context} left fixture temp residue: {path.name}")


def expect_second_replace_rollback() -> None:
    canonical = snapshot()
    module = load_reconciler()
    with tempfile.TemporaryDirectory(prefix=".tabletop-reconcile-negative-", dir=ROOT) as raw:
        contract, status = fixture_pair(module, Path(raw))
        before = snapshot((contract, status))
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
                module.commit_validated_pair(module.load(contract), module.load(status))
            except OSError:
                pass
            else:
                raise RuntimeError("human tabletop reconciler accepted second authority replace rejection")
        finally:
            module.os.replace = original_replace
        assert_fixture_restored(contract, status, before, "second replace rejection")
    assert_unchanged(canonical, "second replace negative")


def expect_post_write_rollback(fail_validator_index: int, label: str) -> None:
    canonical = snapshot()
    module = load_reconciler()
    with tempfile.TemporaryDirectory(prefix=".tabletop-post-write-negative-", dir=ROOT) as raw:
        contract, status = fixture_pair(module, Path(raw))
        before = snapshot((contract, status))
        original_run = module.subprocess.run
        calls = 0

        def injected_run(*args, **kwargs):
            nonlocal calls
            calls += 1
            return subprocess.CompletedProcess(args=args[0] if args else None, returncode=1 if calls == fail_validator_index else 0)

        try:
            module.subprocess.run = injected_run
            try:
                module.commit_validated_pair(module.load(contract), module.load(status))
            except module.Fail:
                pass
            else:
                raise RuntimeError(f"human tabletop reconciler accepted injected {label} failure")
        finally:
            module.subprocess.run = original_run
        assert_fixture_restored(contract, status, before, label)
    assert_unchanged(canonical, f"{label} negative")


def main() -> int:
    canonical = snapshot()
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
    expect_post_write_rollback(1, "post-write tabletop validator failure")
    expect_post_write_rollback(4, "aggregate operability validator failure")
    assert_unchanged(canonical, "human tabletop source negative suite")
    print("PASS: human tabletop source authority is ancestor-only without creating human evidence")
    print("PASS: human tabletop reconcile executable authorities reject substitution")
    print("PASS: human tabletop second replace rejection rolls back run-local contract/status bytes and modes")
    print("PASS: human tabletop post-write failures roll back run-local authorities without canonical mutation")
    print("PASS: canonical tabletop authorities remain byte- and mode-identical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
