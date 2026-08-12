#!/usr/bin/env python3
"""Prove admission-chain validation/reconciliation load boundaries and transactional rollback."""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-admission-chain.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-admission-chain.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CONTRACT = ROOT / "contracts/operations/backup-restore-admission-chain-contract.v1.json"
DRILL_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
TYPED_REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"


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


def write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def corrupt_and_expect_rollback(
    reconciler: object,
    *,
    name: str,
    registry_path: Path,
    mutate: Callable[[dict[str, object]], None],
    contract_copy: Path,
) -> None:
    canonical = json.loads(registry_path.read_text(encoding="utf-8"))
    require(isinstance(canonical, dict), f"{name} canonical registry root invalid")
    bad = json.loads(json.dumps(canonical))
    mutate(bad)
    write_json(registry_path, bad)
    original_registry = registry_path.read_bytes()
    original_contract = contract_copy.read_bytes()
    expect_domain_fail(name, reconciler.main, reconciler.Fail)
    require(registry_path.read_bytes() == original_registry, f"{name} registry was healed/mutated")
    require(contract_copy.read_bytes() == original_contract, f"{name} contract changed before failure")
    write_json(registry_path, canonical)


def main() -> int:
    require(VALIDATOR.is_file(), "admission-chain validator missing")
    require(RECONCILER.is_file(), "admission-chain reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    validator = load_module(VALIDATOR, "memory_os_admission_chain_validator_negative")
    reconciler = load_module(RECONCILER, "memory_os_admission_chain_reconcile_negative")

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

        contract_copy = tmp / CONTRACT.name
        drill_copy = tmp / DRILL_REGISTRY.name
        gen_copy = tmp / GEN_REGISTRY.name
        typed_copy = tmp / TYPED_REGISTRY.name
        shutil.copyfile(CONTRACT, contract_copy)
        shutil.copyfile(DRILL_REGISTRY, drill_copy)
        shutil.copyfile(GEN_REGISTRY, gen_copy)
        shutil.copyfile(TYPED_REGISTRY, typed_copy)
        reconciler.CONTRACT = contract_copy
        reconciler.DRILL_REGISTRY = drill_copy
        reconciler.GEN_REGISTRY = gen_copy
        reconciler.TYPED_REGISTRY = typed_copy

        corrupt_and_expect_rollback(
            reconciler,
            name="drill registry boolean registeredRequestCount",
            registry_path=drill_copy,
            mutate=lambda value: value.__setitem__("registeredRequestCount", False),
            contract_copy=contract_copy,
        )
        corrupt_and_expect_rollback(
            reconciler,
            name="drill registry productionEvidence promotion",
            registry_path=drill_copy,
            mutate=lambda value: value.__setitem__("productionEvidence", True),
            contract_copy=contract_copy,
        )
        corrupt_and_expect_rollback(
            reconciler,
            name="generation registry boolean productionEquivalentRecoveryCandidateCount",
            registry_path=gen_copy,
            mutate=lambda value: value.__setitem__("productionEquivalentRecoveryCandidateCount", False),
            contract_copy=contract_copy,
        )
        corrupt_and_expect_rollback(
            reconciler,
            name="generation registry productionReady promotion",
            registry_path=gen_copy,
            mutate=lambda value: value.__setitem__("productionReady", True),
            contract_copy=contract_copy,
        )
        corrupt_and_expect_rollback(
            reconciler,
            name="typed registry boolean candidateCoveredCount",
            registry_path=typed_copy,
            mutate=lambda value: value.__setitem__("candidateCoveredCount", False),
            contract_copy=contract_copy,
        )
        corrupt_and_expect_rollback(
            reconciler,
            name="typed registry appendOnly corruption",
            registry_path=typed_copy,
            mutate=lambda value: value.__setitem__("appendOnly", False),
            contract_copy=contract_copy,
        )

        original_contract = contract_copy.read_bytes()
        failing_validator = tmp / "forced-validator-failure.py"
        failing_validator.write_text("#!/usr/bin/env python3\nraise SystemExit(41)\n", encoding="utf-8")
        reconciler.VALIDATOR = failing_validator

        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require("post-reconcile admission-chain validator failed" in str(exc), f"unexpected reconcile failure: {exc}")
        else:
            raise Fail("forced admission-chain post-validation failure unexpectedly accepted")

        require(contract_copy.read_bytes() == original_contract, "admission-chain contract rollback drift")

    print("PASS rollback: admission-chain registries remain byte-for-byte corrupt until explicit repair")
    print("PASS rollback: admission-chain contract restored byte-for-byte after post-validation failure")
    print("Admission-chain validator/reconcile negative suite PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ADMISSION CHAIN RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
