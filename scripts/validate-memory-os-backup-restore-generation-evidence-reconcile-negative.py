#!/usr/bin/env python3
"""Prove generation-evidence reconcile fails closed and rolls back derived authority."""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-generation-evidence.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CANONICAL = {
    "CONTRACT": ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
    "REGISTRY": ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "GEN_REGISTRY": ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "OBJECTIVES_REGISTRY": ROOT / "contracts/operations/recovery-objectives-registry.v1.json",
    "DRILL_REGISTRY": ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json",
    "BINDING": ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json",
    "STATUS": ROOT / "contracts/operations/production-operability-status.json",
}
MUTATED = ("CONTRACT", "REGISTRY", "BINDING", "STATUS")


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_generation_evidence_reconcile_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load generation evidence reconciler")
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
    before: dict[Path, bytes],
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
        for path, expected in before.items():
            require(path.read_bytes() == expected, f"canonical authority mutated while rejecting {name}: {path.name}")
    finally:
        setattr(reconciler, attribute, original)


def prove_direct_authority_identity(reconciler: object) -> None:
    before = {path: path.read_bytes() for path in CANONICAL.values()}
    cases = (
        ("generation evidence contract substitution", "generation evidence contract", "CONTRACT", reconciler.STATUS),
        ("generation evidence registry substitution", "generation evidence registry", "REGISTRY", reconciler.BINDING),
        ("environment generation registry substitution", "environment generation registry", "GEN_REGISTRY", reconciler.REGISTRY),
        ("recovery objectives registry substitution", "recovery objectives registry", "OBJECTIVES_REGISTRY", reconciler.DRILL_REGISTRY),
        ("drill request registry substitution", "drill request registry", "DRILL_REGISTRY", reconciler.OBJECTIVES_REGISTRY),
        ("generation binding contract substitution", "generation binding contract", "BINDING", reconciler.CONTRACT),
        ("generation writer substitution", "generation evidence writer", "WRITER", reconciler.VALIDATOR),
        ("generation validator substitution", "generation evidence validator", "VALIDATOR", reconciler.OPERABILITY_VALIDATOR),
        ("generation binding validator substitution", "generation binding validator", "BINDING_VALIDATOR", reconciler.VALIDATOR),
        ("operability validator substitution", "operability validator", "OPERABILITY_VALIDATOR", reconciler.BINDING_VALIDATOR),
        ("production status substitution", "production operability status", "STATUS", reconciler.CONTRACT),
    )
    for name, field, attribute, replacement in cases:
        expect_direct_authority_rejected(
            reconciler,
            name=name,
            field=field,
            attribute=attribute,
            replacement=replacement,
            before=before,
        )
    print(f"PASS boundary: direct generation-evidence data/writer/validator substitutions rejected: {len(cases)}")


def main() -> int:
    require(RECONCILER.is_file(), "generation evidence reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    reconciler = load_reconciler()

    prove_direct_authority_identity(reconciler)

    original_enforcer = reconciler.enforce_runtime_authorities
    original_post_validator = reconciler.run_post_validator
    original_paths = {attr: getattr(reconciler, attr) for attr in CANONICAL}
    try:
        # Production direct invocation remains canonical-only. Repo-contained
        # fixtures are enabled solely inside this negative harness so append-only
        # corruption and rollback can be proved without weakening runtime identity.
        reconciler.enforce_runtime_authorities = lambda: None
        with tempfile.TemporaryDirectory(prefix=".tmp-generation-evidence-reconcile-", dir=TMP_PARENT) as tmpdir:
            tmp = Path(tmpdir)
            originals: dict[Path, bytes] = {}
            targets: dict[str, Path] = {}
            for attr, source in CANONICAL.items():
                target = tmp / source.name
                shutil.copyfile(source, target)
                setattr(reconciler, attr, target)
                originals[target] = target.read_bytes()
                targets[attr] = target

            corruption_cases = (
                ("registeredEvidenceCount drift", "registeredEvidenceCount", 1),
                ("boolean drillRequestBoundEvidenceCount", "drillRequestBoundEvidenceCount", True),
                ("completeGenerationBoundBackupCount drift", "completeGenerationBoundBackupCount", 1),
                ("completeGenerationBoundRestoreCount drift", "completeGenerationBoundRestoreCount", 1),
                ("boolean productionEquivalentRecoveryCandidateCount", "productionEquivalentRecoveryCandidateCount", True),
                ("productionEvidence boundary drift", "productionEvidence", True),
                ("productionReady boundary drift", "productionReady", True),
            )
            registry_path = targets["REGISTRY"]
            for name, field, invalid_value in corruption_cases:
                for path, expected in originals.items():
                    path.write_bytes(expected)
                payload = json.loads(registry_path.read_text(encoding="utf-8"))
                payload[field] = invalid_value
                registry_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                before = {path: path.read_bytes() for path in originals}
                expect_domain_fail(name, reconciler.main, reconciler.Fail)
                for path, expected in before.items():
                    require(path.read_bytes() == expected, f"reconcile auto-healed corrupt authority: {path.name} during {name}")

            for path, expected in originals.items():
                path.write_bytes(expected)

            observed: list[str] = []

            def fail_only_aggregate(path: Path, expected_relative: Path, label: str) -> None:
                observed.append(label)
                if len(observed) < 3:
                    return
                require(len(observed) == 3, "unexpected extra generation evidence post-validator invocation")
                require(label == "operability validator", "operability validator was not final generation evidence validator")
                raise reconciler.Fail("synthetic generation evidence aggregate operability rejection")

            reconciler.run_post_validator = fail_only_aggregate
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                require("synthetic generation evidence aggregate operability rejection" in str(exc), f"unexpected reconcile failure: {exc}")
            else:
                raise Fail("forced aggregate post-validation failure unexpectedly accepted")

            require(observed == ["generation binding validator", "generation evidence validator", "operability validator"], "generation evidence post-validator order drift")
            for attr in MUTATED:
                path = targets[attr]
                require(path.read_bytes() == originals[path], f"rollback drifted derived authority: {path.name}")
    finally:
        reconciler.enforce_runtime_authorities = original_enforcer
        reconciler.run_post_validator = original_post_validator
        for attr, value in original_paths.items():
            setattr(reconciler, attr, value)

    print("PASS reject: corrupt generation append-only authority is never auto-healed by reconcile")
    print("PASS rollback: generation evidence reconcile restores registry/contract/binding/status after aggregate validation failure")
    print("direct generation-evidence data/writer/validator substitutions accepted: false")
    print("Generation evidence reconcile negative suite PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION EVIDENCE RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
