#!/usr/bin/env python3
"""Prove admission-chain authority identity, fail-closed validation, and rollback."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-admission-chain.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-admission-chain.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CONTRACT = ROOT / "contracts/operations/backup-restore-admission-chain-contract.v1.json"
PREFLIGHT = ROOT / "contracts/operations/backup-restore-drill-preflight-contract.v1.json"
DRILL_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
BINDING_CONTRACT = ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json"
TYPED_REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_domain_fail(name: str, action: Callable[[], object], fail_type: type[BaseException]) -> None:
    try:
        action()
    except fail_type:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def expect_direct_authority_rejected(
    reconciler: object,
    *,
    name: str,
    field: str,
    attribute: str,
    replacement: Path,
    contract_before: bytes,
    status_before: bytes,
) -> None:
    original = getattr(reconciler, attribute)
    setattr(reconciler, attribute, replacement)
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require(f"{field} authority drift" in str(exc), f"{name} rejected at wrong boundary: {exc}")
        else:
            raise Fail(f"direct reconciler unexpectedly accepted: {name}")
        require(CONTRACT.read_bytes() == contract_before, f"canonical admission-chain contract mutated while rejecting {name}")
        require(STATUS.read_bytes() == status_before, f"canonical production status mutated while rejecting {name}")
    finally:
        setattr(reconciler, attribute, original)


def prove_direct_authority_identity(reconciler: object) -> None:
    contract_before = CONTRACT.read_bytes()
    status_before = STATUS.read_bytes()
    cases = (
        ("admission-chain contract substitution", "admission-chain contract", "CONTRACT", PREFLIGHT),
        ("preflight contract substitution", "preflight contract", "PREFLIGHT", CONTRACT),
        ("drill registry substitution", "drill request registry", "DRILL_REGISTRY", GEN_REGISTRY),
        ("generation registry substitution", "generation evidence registry", "GEN_REGISTRY", DRILL_REGISTRY),
        ("generation binding substitution", "generation binding contract", "BINDING_CONTRACT", CONTRACT),
        ("typed registry substitution", "typed non-resurrection registry", "TYPED_REGISTRY", GEN_REGISTRY),
        ("drill writer substitution", "drill request writer", "DRILL_WRITER", reconciler.GEN_WRITER),
        ("generation writer substitution", "generation evidence writer", "GEN_WRITER", reconciler.DRILL_WRITER),
        ("typed writer substitution", "typed non-resurrection writer", "TYPED_WRITER", reconciler.GEN_WRITER),
        ("admission-chain validator substitution", "admission-chain validator", "VALIDATOR", reconciler.OPERABILITY_VALIDATOR),
        ("operability validator substitution", "operability validator", "OPERABILITY_VALIDATOR", reconciler.VALIDATOR),
        ("production status substitution", "production operability status", "STATUS", CONTRACT),
    )
    for name, field, attribute, replacement in cases:
        expect_direct_authority_rejected(
            reconciler,
            name=name,
            field=field,
            attribute=attribute,
            replacement=replacement,
            contract_before=contract_before,
            status_before=status_before,
        )
    print(f"PASS boundary: direct admission-chain data/executable substitutions rejected: {len(cases)}")


def mutate_copy(value: dict[str, object], field: str, replacement: object) -> dict[str, object]:
    copied = json.loads(json.dumps(value))
    require(isinstance(copied, dict), "copied registry root invalid")
    copied[field] = replacement
    return copied


def prove_shared_registry_fail_closed(reconciler: object) -> None:
    drill_writer = reconciler.load_writer(
        reconciler.DRILL_WRITER,
        "memory_os_drill_writer_admission_chain_negative",
        "drill request",
    )
    gen_writer = reconciler.load_writer(
        reconciler.GEN_WRITER,
        "memory_os_generation_writer_admission_chain_negative",
        "generation evidence",
    )
    typed_writer = reconciler.load_writer(
        reconciler.TYPED_WRITER,
        "memory_os_typed_writer_admission_chain_negative",
        "typed non-resurrection",
    )

    drill = json.loads(DRILL_REGISTRY.read_text(encoding="utf-8"))
    generation = json.loads(GEN_REGISTRY.read_text(encoding="utf-8"))
    typed = json.loads(TYPED_REGISTRY.read_text(encoding="utf-8"))
    require(all(isinstance(value, dict) for value in (drill, generation, typed)), "canonical registry root invalid")

    cases = (
        ("drill registry boolean registeredRequestCount", drill_writer, mutate_copy(drill, "registeredRequestCount", False), "drill request"),
        ("drill registry productionEvidence promotion", drill_writer, mutate_copy(drill, "productionEvidence", True), "drill request"),
        ("generation registry boolean registeredEvidenceCount", gen_writer, mutate_copy(generation, "registeredEvidenceCount", False), "generation evidence"),
        ("generation registry productionReady promotion", gen_writer, mutate_copy(generation, "productionReady", True), "generation evidence"),
        ("typed registry boolean registeredRecordCount", typed_writer, mutate_copy(typed, "registeredRecordCount", False), "typed non-resurrection"),
        ("typed registry appendOnly corruption", typed_writer, mutate_copy(typed, "appendOnly", False), "typed non-resurrection"),
        ("typed registry productionEvidence promotion", typed_writer, mutate_copy(typed, "productionEvidence", True), "typed non-resurrection"),
    )
    for name, module, value, label in cases:
        expect_domain_fail(
            name,
            lambda module=module, value=value, label=label: reconciler.validate_shared_registry(module, value, label),
            reconciler.Fail,
        )
    print(f"PASS boundary: shared append-only registry corruption rejected without canonical mutation: {len(cases)}")


def prove_atomic_write_failure(reconciler: object) -> None:
    contract_before = CONTRACT.read_bytes()
    original_replace = reconciler.os.replace

    def reject_replace(source: str | Path, destination: str | Path) -> None:
        raise OSError("synthetic atomic replace rejection")

    reconciler.os.replace = reject_replace
    try:
        try:
            reconciler.write_text(CONTRACT, contract_before.decode("utf-8") + " ")
        except reconciler.Fail as exc:
            require("cannot atomically write" in str(exc), f"atomic write rejected at wrong boundary: {exc}")
        else:
            raise Fail("synthetic atomic replace failure unexpectedly accepted")
    finally:
        reconciler.os.replace = original_replace

    require(CONTRACT.read_bytes() == contract_before, "atomic replace failure mutated canonical admission-chain contract")
    leftovers = list(CONTRACT.parent.glob(f".{CONTRACT.name}.*.tmp"))
    require(not leftovers, f"atomic replace failure left temporary authority files: {leftovers}")
    print("PASS boundary: atomic replace failure preserves canonical admission-chain contract")
    print("PASS boundary: failed atomic write leaves no temporary authority file")


def prove_post_validation_rollback(reconciler: object) -> None:
    contract_before = CONTRACT.read_bytes()
    status_before = STATUS.read_bytes()
    original_run_validator = reconciler.run_validator
    calls: list[tuple[Path, str]] = []

    def fail_at_aggregate(path: Path, label: str) -> None:
        calls.append((path, label))
        if path == reconciler.OPERABILITY_VALIDATOR:
            raise reconciler.Fail(f"post-reconcile {label} failed: synthetic aggregate rejection")

    reconciler.run_validator = fail_at_aggregate
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require("synthetic aggregate rejection" in str(exc), f"unexpected reconcile failure: {exc}")
        else:
            raise Fail("forced admission-chain aggregate post-validation failure unexpectedly accepted")
    finally:
        reconciler.run_validator = original_run_validator

    require(
        calls
        == [
            (reconciler.VALIDATOR, "admission-chain validator"),
            (reconciler.OPERABILITY_VALIDATOR, "operability validator"),
        ],
        f"admission-chain post-write validator order drift: {calls}",
    )
    require(CONTRACT.read_bytes() == contract_before, "admission-chain contract rollback drift")
    require(STATUS.read_bytes() == status_before, "production status mutated during admission-chain rollback test")
    print("PASS rollback: aggregate Operability rejection restores admission-chain contract byte-for-byte")
    print("PASS boundary: post-write validator order is admission-chain then aggregate Operability")


def main() -> int:
    require(VALIDATOR.is_file(), "admission-chain validator missing")
    require(RECONCILER.is_file(), "admission-chain reconciler missing")
    require(STATUS.is_file(), "production operability status missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    validator = load_module(VALIDATOR, "memory_os_admission_chain_validator_negative")
    reconciler = load_module(RECONCILER, "memory_os_admission_chain_reconcile_negative")

    prove_direct_authority_identity(reconciler)
    prove_shared_registry_fail_closed(reconciler)

    with tempfile.TemporaryDirectory(prefix=".tmp-admission-chain-reconcile-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_domain_fail("admission-chain invalid UTF-8 authority", lambda: reconciler.load(invalid_utf8), reconciler.Fail)

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_domain_fail("admission-chain unreadable authority directory", lambda: reconciler.load(directory_authority), reconciler.Fail)

        loop_authority = tmp / "loop-authority.json"
        loop_authority.symlink_to(loop_authority.name)
        expect_domain_fail("admission-chain validator authority symlink loop", lambda: validator.load(loop_authority), validator.Fail)
        expect_domain_fail("admission-chain reconciler authority symlink loop", lambda: reconciler.load(loop_authority), reconciler.Fail)

        with tempfile.TemporaryDirectory(prefix="memory-os-chain-outside-") as outside_dir:
            outside = Path(outside_dir) / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            expect_domain_fail("admission-chain validator authority escapes repository", lambda: validator.load(outside), validator.Fail)
            expect_domain_fail("admission-chain reconciler authority escapes repository", lambda: reconciler.load(outside), reconciler.Fail)

    prove_atomic_write_failure(reconciler)
    prove_post_validation_rollback(reconciler)

    print("direct admission-chain data/executable substitutions accepted: false")
    print("shared append-only registry corruption auto-healed by reconciler: false")
    print("non-atomic derived admission-chain contract write accepted: false")
    print("Admission-chain validator/reconcile negative suite PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ADMISSION CHAIN RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
