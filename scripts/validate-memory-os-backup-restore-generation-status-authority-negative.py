#!/usr/bin/env python3
"""Prove generation-binding/status reconcile keeps canonical authority and rollback boundaries."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINDING_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-binding.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-generation-status.py"
WORKFLOW = ROOT / ".github/workflows/backup-restore-generation-binding.yml"
CONTRACT = ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_target(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_reconciler():
    return load_target(RECONCILER, "memory_os_generation_status_authority_negative")


def load_binding_validator():
    return load_target(BINDING_VALIDATOR, "memory_os_generation_binding_authority_negative")


def expect_direct_authority_rejected(reconciler, name: str, field: str, attribute: str, replacement: Path) -> None:
    contract_before = CONTRACT.read_bytes()
    status_before = STATUS.read_bytes()
    original = getattr(reconciler, attribute)
    setattr(reconciler, attribute, replacement)
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require(f"{field} authority drift" in str(exc), f"{name} rejected at wrong boundary: {exc}")
        else:
            raise Fail(f"direct generation status reconciler unexpectedly accepted: {name}")
        require(CONTRACT.read_bytes() == contract_before, f"canonical contract mutated while rejecting {name}")
        require(STATUS.read_bytes() == status_before, f"canonical status mutated while rejecting {name}")
    finally:
        setattr(reconciler, attribute, original)


def expect_binding_authority_rejected(binding, name: str, field: str, attribute: str, replacement: Path) -> None:
    contract_before = CONTRACT.read_bytes()
    status_before = STATUS.read_bytes()
    original = getattr(binding, attribute)
    setattr(binding, attribute, replacement)
    try:
        try:
            binding.main()
        except binding.Fail as exc:
            require(f"{field} authority drift" in str(exc), f"{name} rejected at wrong boundary: {exc}")
        else:
            raise Fail(f"direct generation binding validator unexpectedly accepted: {name}")
        require(CONTRACT.read_bytes() == contract_before, f"canonical contract mutated while rejecting {name}")
        require(STATUS.read_bytes() == status_before, f"canonical status mutated while rejecting {name}")
    finally:
        setattr(binding, attribute, original)


def prove_binding_validator_authorities() -> None:
    binding = load_binding_validator()
    cases = (
        ("generation binding contract substitution", "generation binding contract", "CONTRACT", binding.BACKUP_POLICY),
        ("backup restore policy substitution", "backup restore policy contract", "BACKUP_POLICY", binding.LOCAL_FOUNDATIONS),
        ("local restore foundation substitution", "local restore foundation evidence", "LOCAL_FOUNDATIONS", binding.GENERATION),
        ("environment generation contract substitution", "environment generation contract", "GENERATION", binding.EVIDENCE_CONTRACT),
        ("environment generation registry substitution", "environment generation registry", "GEN_REGISTRY", binding.EVIDENCE_REGISTRY),
        ("generation evidence contract substitution", "generation evidence contract", "EVIDENCE_CONTRACT", binding.GENERATION),
        ("generation evidence registry substitution", "generation evidence registry", "EVIDENCE_REGISTRY", binding.GEN_REGISTRY),
        ("generation evidence writer substitution", "generation evidence writer", "EVIDENCE_WRITER", BINDING_VALIDATOR),
    )
    for name, field, attribute, replacement in cases:
        expect_binding_authority_rejected(binding, name, field, attribute, replacement)
    try:
        binding.enforce_runtime_authorities()
    except binding.Fail as exc:
        raise Fail(f"canonical generation binding authorities rejected: {exc}") from exc
    print(f"PASS boundary: generation binding direct data/writer substitutions rejected: {len(cases)}")


def validate_atomic_diagnostic_publication() -> None:
    require(WORKFLOW.is_file(), "generation binding workflow missing")
    text = WORKFLOW.read_text(encoding="utf-8")
    required = (
        "tempfile.mkstemp(",
        "dir=path.parent",
        "handle.flush()",
        "os.fsync(handle.fileno())",
        "os.replace(tmp_name, path)",
        "os.unlink(tmp_name)",
    )
    missing = [fragment for fragment in required if fragment not in text]
    require(not missing, f"generation binding diagnostic publication is not crash-safe: missing {missing}")
    require(
        "path.write_text(json.dumps(value" not in text,
        "generation binding diagnostic publication regressed to direct write_text",
    )


def main() -> int:
    require(BINDING_VALIDATOR.is_file(), "generation binding validator missing")
    require(RECONCILER.is_file(), "generation status reconciler missing")
    require(CONTRACT.is_file() and STATUS.is_file(), "canonical generation status authority missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    prove_binding_validator_authorities()
    reconciler = load_reconciler()
    validate_atomic_diagnostic_publication()

    cases = (
        ("generation binding contract substitution", "generation binding contract", "CONTRACT", reconciler.STATUS),
        ("generation binding validator substitution", "generation binding validator", "VALIDATOR", reconciler.BACKUP_VALIDATOR),
        ("backup validator substitution", "backup validator", "BACKUP_VALIDATOR", reconciler.OPERABILITY_VALIDATOR),
        ("operability validator substitution", "operability validator", "OPERABILITY_VALIDATOR", reconciler.BACKUP_VALIDATOR),
        ("production status substitution", "production operability status", "STATUS", reconciler.CONTRACT),
    )
    for name, field, attribute, replacement in cases:
        expect_direct_authority_rejected(reconciler, name, field, attribute, replacement)
    print(f"PASS boundary: generation status direct authority substitutions rejected: {len(cases)}")

    original_enforcer = reconciler.enforce_runtime_authorities
    original_contract = reconciler.CONTRACT
    original_status = reconciler.STATUS
    original_runner = reconciler.run_validator
    original_write = reconciler.write_text
    try:
        with tempfile.TemporaryDirectory(prefix=".tmp-generation-status-authority-", dir=TMP_PARENT) as tmpdir:
            tmp = Path(tmpdir)
            contract_copy = tmp / CONTRACT.name
            status_copy = tmp / STATUS.name
            shutil.copyfile(CONTRACT, contract_copy)
            shutil.copyfile(STATUS, status_copy)
            status_before = status_copy.read_bytes()
            observed: list[str] = []
            status_write_observed = False

            def track_write(path: Path, text: str) -> None:
                nonlocal status_write_observed
                if path == status_copy:
                    status_write_observed = True
                original_write(path, text)

            def fail_only_aggregate(path: Path, expected_relative: Path, label: str) -> None:
                observed.append(label)
                if label == "generation binding validator":
                    require(not status_write_observed, "generation binding validator ran after status write")
                    return
                require(status_write_observed, f"{label} ran before status write")
                if label == "backup validator":
                    return
                require(label == "operability validator", f"unexpected generation status validator: {label}")
                raise reconciler.Fail("synthetic generation status operability rejection")

            reconciler.enforce_runtime_authorities = lambda: None
            reconciler.CONTRACT = contract_copy
            reconciler.STATUS = status_copy
            reconciler.run_validator = fail_only_aggregate
            reconciler.write_text = track_write
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                require("synthetic generation status operability rejection" in str(exc), f"rollback rejected at wrong boundary: {exc}")
            else:
                raise Fail("forced generation status operability rejection unexpectedly accepted")

            require(
                observed == ["generation binding validator", "backup validator", "operability validator"],
                "generation status validator order drift",
            )
            require(status_write_observed, "generation status transaction did not invoke atomic status writer")
            require(status_copy.read_bytes() == status_before, "failed aggregate validation left production status mutation behind")
    finally:
        reconciler.enforce_runtime_authorities = original_enforcer
        reconciler.CONTRACT = original_contract
        reconciler.STATUS = original_status
        reconciler.run_validator = original_runner
        reconciler.write_text = original_write

    print("PASS rollback: generation status restored byte-for-byte after aggregate operability rejection")
    print("generation binding canonical data/writer substitutions accepted: false")
    print("generation binding validator remains pre-write: true")
    print("backup and operability validators remain post-write: true")
    print("byte-current status still exercises atomic write boundary: true")
    print("crash-safe generation-binding failure diagnostic required: true")
    print("canonical blockers rewritten: false")
    print("production evidence created: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION STATUS AUTHORITY NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
