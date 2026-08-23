#!/usr/bin/env python3
"""Negative checks for fail-closed local long-soak load projection boundaries."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/reconcile-memory-os-local-long-soak-load-projection.py"
CANONICAL_SOAK = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
CANONICAL_LOAD = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
SOAK_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak.py"
LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
SPEC = importlib.util.spec_from_file_location("local_long_soak_projection", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("LOCAL LONG SOAK LOAD PROJECTION NEGATIVE FAILED: cannot load projection module")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def expect_reject(label: str, mutate) -> None:
    row = module.derived_row(local_evidence=True)
    mutate(row)
    try:
        module.assert_local_only_boundary(row)
    except module.Fail:
        print(f"PASS reject: {label}")
        return
    raise AssertionError(f"corruption accepted: {label}")


def expect_legacy_reject(label: str, mutate) -> None:
    row = {
        "scenarioId": module.LEGACY_ALIAS_ID,
        "productionEvidence": False,
        "productionSustainedSoakEvidence": False,
        "leakProof": False,
        "capacityApproved": False,
        "thresholdsApproved": False,
        "runMetadata": {
            "productionEquivalent": False,
            "productionTraffic": False,
            "productionCredentials": False,
            "productionEvidence": False,
            "approvalAuthority": "NONE",
        },
    }
    mutate(row)
    try:
        module.assert_legacy_alias_safe_to_remove(row)
    except module.Fail:
        print(f"PASS reject legacy alias removal: {label}")
        return
    raise AssertionError(f"corrupt legacy alias accepted for removal: {label}")


def expect_projection_input_reject(label: str, rows) -> None:
    try:
        module.assert_projection_input_safe(rows)
    except module.Fail:
        print(f"PASS reject projection input: {label}")
        return
    raise AssertionError(f"corrupt projection input accepted: {label}")


def authority_substitution_rejected() -> None:
    load_bytes = CANONICAL_LOAD.read_bytes()
    substitutions = (
        ("SOAK_PATH", CANONICAL_LOAD, "sustained-soak contract authority drift"),
        ("LOAD_PATH", CANONICAL_SOAK, "load contract authority drift"),
        ("SOAK_VALIDATOR", LOAD_VALIDATOR, "sustained-soak validator authority drift"),
        ("LOAD_VALIDATOR", SOAK_VALIDATOR, "load validator authority drift"),
    )
    for attr, substitute, expected in substitutions:
        original = getattr(module, attr)
        try:
            setattr(module, attr, substitute)
            try:
                module.validate_authorities()
            except module.Fail as exc:
                if expected not in str(exc):
                    raise AssertionError(f"unexpected {attr} authority rejection: {exc}") from exc
            else:
                raise AssertionError(f"substituted projection authority accepted: {attr}")
            if CANONICAL_LOAD.read_bytes() != load_bytes:
                raise AssertionError(f"canonical load authority changed after rejected substitution: {attr}")
        finally:
            setattr(module, attr, original)


def atomic_replacement_failure_rejected() -> None:
    original_bytes = CANONICAL_LOAD.read_bytes()
    temp_glob = f".{CANONICAL_LOAD.name}.*.tmp"
    before = {path.name for path in CANONICAL_LOAD.parent.glob(temp_glob)}
    real_replace = module.os.replace

    def reject_replace(_source, _destination) -> None:
        raise OSError("synthetic load projection atomic replace failure")

    module.os.replace = reject_replace
    try:
        try:
            module.atomic_replace_bytes(CANONICAL_LOAD, original_bytes + b"\n")
        except OSError as exc:
            if "synthetic load projection atomic replace failure" not in str(exc):
                raise AssertionError(f"unexpected atomic replacement rejection: {exc}") from exc
        else:
            raise AssertionError("load projection atomic replacement unexpectedly succeeded")
    finally:
        module.os.replace = real_replace

    if CANONICAL_LOAD.read_bytes() != original_bytes:
        raise AssertionError("atomic replacement failure changed canonical load authority")
    after = {path.name for path in CANONICAL_LOAD.parent.glob(temp_glob)}
    if after != before:
        raise AssertionError("atomic replacement failure leaked temporary load authority")


def transaction_rollback_rejected() -> None:
    original_bytes = CANONICAL_LOAD.read_bytes()
    original_source_validator = module.validate_source_authority
    original_load_validator = module.validate_projected_load_authority
    module.validate_source_authority = lambda: None

    def reject_after_write() -> None:
        raise module.Fail("synthetic post-write load projection rejection")

    module.validate_projected_load_authority = reject_after_write
    try:
        try:
            module.main()
        except module.Fail as exc:
            if "synthetic post-write load projection rejection" not in str(exc):
                raise AssertionError(f"unexpected transactional rejection: {exc}") from exc
        else:
            raise AssertionError("post-write load projection validator failure was accepted")
        if CANONICAL_LOAD.read_bytes() != original_bytes:
            raise AssertionError("canonical load authority was not restored after rejected projection")
    finally:
        module.validate_source_authority = original_source_validator
        module.validate_projected_load_authority = original_load_validator
        if CANONICAL_LOAD.read_bytes() != original_bytes:
            module.atomic_replace_bytes(CANONICAL_LOAD, original_bytes)


def main() -> int:
    valid = copy.deepcopy(module.derived_row(local_evidence=True))
    module.assert_local_only_boundary(valid)
    module.assert_projection_input_safe([valid])

    for key in (
        "productionEvidence",
        "productionSustainedSoakEvidence",
        "leakProof",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
    ):
        expect_reject(f"{key} manufactured", lambda row, key=key: row.__setitem__(key, True))

    expect_reject("duplicate alias scenario identity", lambda row: row.__setitem__("scenarioId", module.LEGACY_ALIAS_ID))
    expect_reject("contract authority drift", lambda row: row.__setitem__("contractRef", "README.md"))
    expect_reject("validator authority drift", lambda row: row.__setitem__("validatorRef", "README.md"))
    expect_reject("dependency mode drift", lambda row: row.__setitem__("dependencyMode", "PRODUCTION_EQUIVALENT"))
    expect_reject("classification drift", lambda row: row.__setitem__("classification", "PRODUCTION_LONG_SOAK"))
    expect_reject("local evidence flag non-boolean", lambda row: row.__setitem__("localSustainedSoakEvidence", 1))

    duplicate_rows = [copy.deepcopy(valid), copy.deepcopy(valid)]
    expect_projection_input_reject("duplicate external scenario ID", duplicate_rows)
    expect_projection_input_reject("non-object external row", [copy.deepcopy(valid), "bad-row"])
    production_row = copy.deepcopy(valid)
    production_row["scenarioId"] = "unrelated-local-scenario"
    production_row["productionEvidence"] = True
    expect_projection_input_reject("unrelated production evidence promotion", [production_row])
    production_dependency_row = copy.deepcopy(valid)
    production_dependency_row["scenarioId"] = "unrelated-local-dependency-scenario"
    production_dependency_row["productionEquivalentDependencies"] = True
    expect_projection_input_reject("unrelated production-equivalent dependency promotion", [production_dependency_row])

    for key in (
        "productionEvidence",
        "productionSustainedSoakEvidence",
        "leakProof",
        "capacityApproved",
        "thresholdsApproved",
    ):
        expect_legacy_reject(f"{key} manufactured", lambda row, key=key: row.__setitem__(key, True))
    for key in ("productionEquivalent", "productionTraffic", "productionCredentials", "productionEvidence"):
        expect_legacy_reject(
            f"runMetadata.{key} manufactured",
            lambda row, key=key: row["runMetadata"].__setitem__(key, True),
        )
    expect_legacy_reject(
        "approval authority manufactured",
        lambda row: row["runMetadata"].__setitem__("approvalAuthority", "HUMAN_APPROVED"),
    )
    expect_legacy_reject("run metadata removed", lambda row: row.pop("runMetadata"))

    authority_substitution_rejected()
    atomic_replacement_failure_rejected()
    transaction_rollback_rejected()

    print("Memory OS local long-soak load projection negative suite PASS")
    print("canonical scenario ID binding enforced: true")
    print("canonical source/load authority identity enforced: true")
    print("crash-safe atomic load replacement enforced: true")
    print("post-write load validation rollback enforced: true")
    print("aggregate external scenario corruption accepted: false")
    print("legacy LOCAL_LONG_SOAK alias may be removed only when non-production: true")
    print("production evidence promotion accepted: false")
    print("production traffic promotion accepted: false")
    print("production credentials promotion accepted: false")
    print("automatic approval authority accepted: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
