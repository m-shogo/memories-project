#!/usr/bin/env python3
"""Prove migration evidence reconciliation cannot substitute canonical authorities."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-migration-evidence-registry.py"
ORPHAN_RECONCILER = ROOT / "scripts/reconcile-memory-os-migration-recovery-result-orphans.py"
CANONICAL_REGISTRY = ROOT / "contracts/operations/migration-evidence-registry.v1.json"
CANONICAL_CONTRACT = ROOT / "contracts/operations/migration-evidence-registry-contract.v1.json"
CANONICAL_LIFECYCLE = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
CANONICAL_LOCAL_CONTRACT = ROOT / "contracts/operations/local-migration-recovery-artifact-contract.v1.json"
CANONICAL_STATUS = ROOT / "contracts/operations/production-operability-status.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_canonical_bytes_unchanged(before: dict[Path, bytes], label: str) -> None:
    for path, payload in before.items():
        require(path.read_bytes() == payload, f"{label} substitution mutated {path.relative_to(ROOT)}")


def expect_path_substitution_rejected(
    module: Any,
    attribute: str,
    replacement: Path,
    label: str,
    before: dict[Path, bytes],
) -> None:
    original = getattr(module, attribute)
    setattr(module, attribute, replacement)
    try:
        rejected = False
        try:
            module.main()
        except module.Fail as exc:
            require("authority drift" in str(exc) or "missing or escapes repository" in str(exc),
                    f"unexpected {label} rejection: {exc}")
            rejected = True
        require(rejected, f"reconciler accepted non-canonical {label}")
    finally:
        setattr(module, attribute, original)
    require_canonical_bytes_unchanged(before, label)


def expect_validator_chain_substitution_rejected(module: Any, before: dict[Path, bytes]) -> None:
    original = module.POST_WRITE_VALIDATORS
    module.POST_WRITE_VALIDATORS = ()
    try:
        rejected = False
        try:
            module.main()
        except module.Fail as exc:
            require("validator chain authority drift" in str(exc),
                    f"unexpected validator-chain rejection: {exc}")
            rejected = True
        require(rejected, "migration evidence reconciler accepted validator-chain substitution")
    finally:
        module.POST_WRITE_VALIDATORS = original
    require_canonical_bytes_unchanged(before, "validator-chain")


def expect_atomic_replace_failure_rolls_back(module: Any, before: dict[Path, bytes]) -> None:
    paths = (CANONICAL_CONTRACT, CANONICAL_LIFECYCLE, CANONICAL_STATUS)
    before_modes = {path: path.stat().st_mode & 0o7777 for path in paths}
    outputs = {path: module.load(path) for path in paths}
    for value in outputs.values():
        value["atomicRollbackProbe"] = "must-not-persist"

    original_replace = module.os.replace
    calls = 0

    def fail_second_replace(source, destination) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic migration evidence atomic replace failure")
        original_replace(source, destination)

    module.os.replace = fail_second_replace
    try:
        rejected = False
        try:
            module.commit_outputs_transactionally(outputs)
        except module.Fail as exc:
            require("restored prior authority" in str(exc), f"unexpected atomic rollback rejection: {exc}")
            rejected = True
        require(rejected, "migration evidence reconciler accepted synthetic atomic replace failure")
    finally:
        module.os.replace = original_replace

    require(calls >= 5, "migration evidence rollback did not atomically restore all canonical authorities")
    for path in paths:
        require(path.read_bytes() == before[path], f"atomic replace failure mutated {path.relative_to(ROOT)}")
        require((path.stat().st_mode & 0o7777) == before_modes[path],
                f"atomic replace failure changed mode for {path.relative_to(ROOT)}")
        leftovers = list(path.parent.glob(f".{path.name}.*.tmp"))
        require(not leftovers, f"temporary migration evidence authority remained after replace failure: {leftovers}")


def expect_rollback_failure_preserves_primary_and_continues(module: Any, before: dict[Path, bytes]) -> None:
    paths = (CANONICAL_CONTRACT, CANONICAL_LIFECYCLE, CANONICAL_STATUS)
    outputs = {path: module.load(path) for path in paths}
    for value in outputs.values():
        value["rollbackDiagnosticProbe"] = "must-not-persist"

    original_run = module.subprocess.run
    original_atomic_replace = module.atomic_replace_bytes
    validator_failed = False
    first_restore_failure_injected = False
    rollback_attempts: list[Path] = []

    def fail_validator(args, *pargs, **kwargs):
        nonlocal validator_failed
        if isinstance(args, list) and len(args) >= 2 and args[0] == "python" and args[1] == str(module.REGISTRY_VALIDATOR):
            validator_failed = True
            raise subprocess.CalledProcessError(73, args)
        return original_run(args, *pargs, **kwargs)

    def fail_first_restore_after_restoring(path: Path, payload: bytes) -> None:
        nonlocal first_restore_failure_injected
        if validator_failed and path in paths and payload == before[path]:
            rollback_attempts.append(path)
            original_atomic_replace(path, payload)
            if path == CANONICAL_CONTRACT and not first_restore_failure_injected:
                first_restore_failure_injected = True
                raise OSError("synthetic migration evidence rollback restore rejection")
            return
        original_atomic_replace(path, payload)

    module.subprocess.run = fail_validator
    module.atomic_replace_bytes = fail_first_restore_after_restoring
    try:
        rejected = False
        try:
            module.commit_outputs_transactionally(outputs)
        except module.Fail as exc:
            text = str(exc)
            require("returned non-zero exit status 73" in text, f"primary validator failure was lost: {exc}")
            require("rollback incomplete" in text, f"rollback incompleteness was not reported: {exc}")
            require("synthetic migration evidence rollback restore rejection" in text,
                    f"rollback restore failure was lost: {exc}")
            rejected = True
        require(rejected, "migration evidence reconciler accepted validator plus rollback restore failure")
    finally:
        module.subprocess.run = original_run
        module.atomic_replace_bytes = original_atomic_replace

    require(rollback_attempts == list(paths),
            f"migration evidence rollback did not continue after first restore failure: {rollback_attempts}")
    for path in paths:
        require(path.read_bytes() == before[path], f"rollback diagnostic failure mutated {path.relative_to(ROOT)}")
        leftovers = list(path.parent.glob(f".{path.name}.*.tmp"))
        require(not leftovers, f"temporary migration evidence authority remained after rollback diagnostic failure: {leftovers}")


def expect_orphan_atomic_replace_failure_preserves_authority(module: Any, before: dict[Path, bytes]) -> None:
    original_replace = module.os.replace
    before_mode = CANONICAL_STATUS.stat().st_mode & 0o7777
    calls = 0

    def fail_replace(source, destination) -> None:
        nonlocal calls
        calls += 1
        raise OSError("synthetic orphan rescue atomic replace failure")

    module.os.replace = fail_replace
    try:
        rejected = False
        try:
            module.atomic_write_bytes(CANONICAL_STATUS, before[CANONICAL_STATUS])
        except OSError as exc:
            require("synthetic orphan rescue atomic replace failure" in str(exc),
                    f"unexpected orphan atomic rejection: {exc}")
            rejected = True
        require(rejected, "orphan rescue atomic writer accepted synthetic replace failure")
    finally:
        module.os.replace = original_replace

    require(calls == 1, "orphan rescue atomic writer did not reach os.replace exactly once")
    require(CANONICAL_STATUS.read_bytes() == before[CANONICAL_STATUS],
            "orphan rescue replace failure mutated production operability status")
    require((CANONICAL_STATUS.stat().st_mode & 0o7777) == before_mode,
            "orphan rescue replace failure changed production operability status mode")
    leftovers = list(CANONICAL_STATUS.parent.glob(f".{CANONICAL_STATUS.name}.*.tmp"))
    require(not leftovers, f"temporary orphan rescue authority remained after replace failure: {leftovers}")


def expect_orphan_restore_routes_through_atomic_writer(module: Any, before: dict[Path, bytes]) -> None:
    paths = (
        CANONICAL_REGISTRY,
        CANONICAL_CONTRACT,
        CANONICAL_LIFECYCLE,
        CANONICAL_LOCAL_CONTRACT,
        CANONICAL_STATUS,
    )
    originals = {path: before[path] for path in paths}
    original_writer = module.atomic_write_bytes
    calls: list[tuple[Path, bytes]] = []

    def spy_atomic_write(path: Path, payload: bytes) -> None:
        calls.append((path, payload))

    module.atomic_write_bytes = spy_atomic_write
    try:
        module.restore_originals_atomically(originals)
    finally:
        module.atomic_write_bytes = original_writer

    require([path for path, _ in calls] == list(paths),
            "orphan rescue rollback did not route every canonical authority through atomic writer")
    for path, payload in calls:
        require(payload == before[path], f"orphan rescue rollback payload drifted for {path.relative_to(ROOT)}")
    source = ORPHAN_RECONCILER.read_text(encoding="utf-8")
    require("restore_originals_atomically(originals)" in source,
            "orphan rescue failure path does not invoke atomic restore helper")
    require("path.write_bytes(payload)" not in source,
            "orphan rescue failure path regressed to direct rollback write_bytes")
    require_canonical_bytes_unchanged(before, "orphan atomic rollback routing")


def expect_orphan_restore_failure_continues(module: Any, before: dict[Path, bytes]) -> None:
    paths = (
        CANONICAL_REGISTRY,
        CANONICAL_CONTRACT,
        CANONICAL_LIFECYCLE,
        CANONICAL_LOCAL_CONTRACT,
        CANONICAL_STATUS,
    )
    originals = {path: before[path] for path in paths}
    before_modes = {path: path.stat().st_mode & 0o7777 for path in paths}
    original_writer = module.atomic_write_bytes
    attempts: list[Path] = []
    first_failure_injected = False

    def fail_first_after_restore(path: Path, payload: bytes) -> None:
        nonlocal first_failure_injected
        attempts.append(path)
        original_writer(path, payload)
        if not first_failure_injected:
            first_failure_injected = True
            raise OSError("synthetic orphan rollback restore rejection")

    module.atomic_write_bytes = fail_first_after_restore
    try:
        rejected = False
        try:
            module.restore_originals_atomically(originals)
        except module.Fail as exc:
            text = str(exc)
            require("rollback incomplete" in text, f"orphan rollback incompleteness was not reported: {exc}")
            require("synthetic orphan rollback restore rejection" in text,
                    f"orphan rollback restore failure was lost: {exc}")
            rejected = True
        require(rejected, "orphan rescue rollback accepted a restore failure")
    finally:
        module.atomic_write_bytes = original_writer

    require(attempts == list(paths),
            f"orphan rollback did not continue after first restore failure: {attempts}")
    for path in paths:
        require(path.read_bytes() == before[path], f"orphan rollback failure mutated {path.relative_to(ROOT)}")
        require((path.stat().st_mode & 0o7777) == before_modes[path],
                f"orphan rollback failure changed mode for {path.relative_to(ROOT)}")
        leftovers = list(path.parent.glob(f".{path.name}.*.tmp"))
        require(not leftovers, f"temporary orphan rollback authority remained: {leftovers}")


def prove_registry_reconcile_authorities(before: dict[Path, bytes]) -> None:
    module = load_module(RECONCILER, "migration_evidence_registry_reconcile_authority_negative")
    replacement_file = ROOT / "README.md"
    replacement_directory = ROOT / "scripts"
    cases = (
        ("REGISTRY_CONTRACT", replacement_file, "registry contract"),
        ("REGISTRY", replacement_file, "registry"),
        ("WRITER", replacement_file, "writer"),
        ("REGISTRY_VALIDATOR", replacement_file, "registry validator"),
        ("RECOVERY_VALIDATOR", replacement_file, "recovery-point validator"),
        ("ARTIFACT_CONTRACT", replacement_file, "artifact contract"),
        ("ARTIFACT_RUNNER", replacement_file, "artifact runner"),
        ("ARTIFACT_VALIDATOR", replacement_file, "artifact validator"),
        ("ARTIFACT_EVIDENCE_ROOT", replacement_directory, "artifact evidence root"),
        ("LOCAL_RESTORE", replacement_file, "local restore result"),
        ("WORKFLOW", replacement_file, "workflow"),
        ("LIFECYCLE", replacement_file, "lifecycle contract"),
        ("LIFECYCLE_VALIDATOR", replacement_file, "lifecycle validator"),
        ("OPERABILITY_VALIDATOR", replacement_file, "operability validator"),
        ("STATUS", replacement_file, "production status"),
    )
    for attribute, replacement, label in cases:
        expect_path_substitution_rejected(module, attribute, replacement, f"registry {label}", before)
        print(f"PASS authority reject: registry {label}")
    expect_validator_chain_substitution_rejected(module, before)
    print("PASS authority reject: registry post-write validator chain")
    expect_atomic_replace_failure_rolls_back(module, before)
    print("PASS atomic rollback and mode preservation: registry derived authority")
    expect_rollback_failure_preserves_primary_and_continues(module, before)
    print("PASS rollback diagnostics: registry primary failure preserved and all authorities attempted")


def prove_orphan_rescue_authorities(before: dict[Path, bytes]) -> None:
    module = load_module(ORPHAN_RECONCILER, "migration_recovery_orphan_reconcile_authority_negative")
    replacement_file = ROOT / "README.md"
    replacement_directory = ROOT / "scripts"
    cases = (
        ("RESULT_ROOT", replacement_directory, "orphan result root"),
        ("REGISTRY", replacement_file, "orphan registry"),
        ("REGISTRY_CONTRACT", replacement_file, "orphan registry contract"),
        ("LIFECYCLE", replacement_file, "orphan lifecycle contract"),
        ("STATUS", replacement_file, "orphan production status"),
        ("LOCAL_CONTRACT", replacement_file, "orphan local recovery contract"),
        ("WRITER", replacement_file, "orphan writer"),
        ("RESULT_VALIDATOR", replacement_file, "orphan result validator"),
        ("LOCAL_RECONCILER", replacement_file, "orphan local reconciler"),
        ("GLOBAL_RECONCILER", replacement_file, "orphan global reconciler"),
    )
    for attribute, replacement, label in cases:
        expect_path_substitution_rejected(module, attribute, replacement, label, before)
        print(f"PASS authority reject: {label}")
    expect_orphan_atomic_replace_failure_preserves_authority(module, before)
    print("PASS atomic replace failure and mode preservation: orphan rescue authority")
    expect_orphan_restore_routes_through_atomic_writer(module, before)
    print("PASS atomic rollback routing: orphan rescue authorities")
    expect_orphan_restore_failure_continues(module, before)
    print("PASS exhaustive rollback: orphan rescue attempts all authorities after restore failure")


def main() -> int:
    before = {
        CANONICAL_REGISTRY: CANONICAL_REGISTRY.read_bytes(),
        CANONICAL_CONTRACT: CANONICAL_CONTRACT.read_bytes(),
        CANONICAL_LIFECYCLE: CANONICAL_LIFECYCLE.read_bytes(),
        CANONICAL_LOCAL_CONTRACT: CANONICAL_LOCAL_CONTRACT.read_bytes(),
        CANONICAL_STATUS: CANONICAL_STATUS.read_bytes(),
    }
    prove_registry_reconcile_authorities(before)
    prove_orphan_rescue_authorities(before)
    print("Memory OS migration evidence reconcile authority negative PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"MIGRATION EVIDENCE RECONCILE AUTHORITY NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
