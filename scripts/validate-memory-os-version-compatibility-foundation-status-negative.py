#!/usr/bin/env python3
"""Pin fail-closed numeric and source-authority boundaries for compatibility foundations."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_RECONCILER = ROOT / "scripts/reconcile-memory-os-version-compatibility-canonical.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-version-compatibility-foundation-status.py"
FOUNDATION_VALIDATOR = ROOT / "scripts/validate-memory-os-version-compatibility-foundations.py"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejection(module, value, field: str) -> None:
    rejected = False
    try:
        module.require_zero_count({field: value}, field)
    except module.ReconcileFailure as exc:
        require(field in str(exc), f"unexpected rejection for {field}: {exc}")
        rejected = True
    require(rejected, f"invalid zero-count authority accepted for {field}: {value!r}")


def expect_runtime_authority_identity(module, substitutions, label: str) -> None:
    module.enforce_runtime_authorities()
    for field, substitute in substitutions:
        original = getattr(module, field)
        try:
            setattr(module, field, substitute)
            rejected = False
            try:
                module.enforce_runtime_authorities()
            except module.ReconcileFailure:
                rejected = True
            require(rejected, f"{label} accepted {field} authority substitution")
        finally:
            setattr(module, field, original)
    module.enforce_runtime_authorities()


def expect_source_authority_rejection(reconciler, validator, path: Path, field: str,
                                      replacement, label: str) -> None:
    original = path.read_bytes()
    try:
        registry = json.loads(original.decode("utf-8"))
        registry[field] = replacement
        path.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        rejected = False
        try:
            reconciler.validate_source_registries()
        except reconciler.ReconcileFailure as exc:
            require("compatibility source authority invalid" in str(exc),
                    f"unexpected reconciler rejection for {label}: {exc}")
            rejected = True
        require(rejected, f"corrupt canonical {label} authority was accepted before reconcile")

        rejected = False
        try:
            validator.validate_source_authorities()
        except validator.ValidationFailure as exc:
            require("compatibility source authority invalid" in str(exc),
                    f"unexpected standalone validator rejection for {label}: {exc}")
            rejected = True
        require(rejected, f"corrupt canonical {label} authority was accepted by standalone validator")
    finally:
        path.write_bytes(original)
    require(path.read_bytes() == original,
            f"canonical {label} authority changed after source-authority rejection")


def expect_foundation_boolean_count_rejection(validator, field: str) -> None:
    path = validator.FOUNDATION_PATH
    original = path.read_bytes()
    try:
        contract = json.loads(original.decode("utf-8"))
        contract["aggregateBoundaries"][field] = False
        path.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        rejected = False
        try:
            validator.validate_foundation_contract()
        except validator.ValidationFailure as exc:
            require(field in str(exc), f"unexpected foundation count rejection for {field}: {exc}")
            rejected = True
        require(rejected, f"boolean foundation count accepted for {field}")
    finally:
        path.write_bytes(original)
    require(path.read_bytes() == original,
            f"foundation contract changed after boolean-count rejection for {field}")


def expect_nonempty_source_inventory_allowed(module, validator_mode: bool) -> None:
    releases = {"approvedReleaseCount": 2, "releases": [{"id": "rel_a"}, {"id": "rel_b"}]}
    rollback = {"rehearsalRequestCount": 1, "requests": [{"id": "rr_a"}]}
    parsers = {"reviewedArtifactCount": 1, "artifacts": [{"id": "pa_a"}]}
    pair_row = {"id": "pair_a"}
    pairs = {"approvedPairCount": 1, "pairs": [pair_row]}
    release_contract = {"contract": "release"}
    rollback_contract = {"contract": "rollback"}
    values = {
        module.RELEASE_REGISTRY_PATH: releases,
        module.ROLLBACK_REGISTRY_PATH: rollback,
        module.PARSER_REGISTRY_PATH: parsers,
        module.PAIR_REGISTRY_PATH: pairs,
        module.RELEASE_CONTRACT_PATH: release_contract,
        module.ROLLBACK_CONTRACT_PATH: rollback_contract,
    }

    class ReleaseWriter:
        @staticmethod
        def validate_registry_for_append(registry, contract):
            require(registry is releases and contract is release_contract,
                    "release shared validator did not receive synthetic authority")

    class RollbackWriter:
        @staticmethod
        def validate_registry_for_append(registry, contract, release_registry):
            require(registry is rollback and contract is rollback_contract and release_registry is releases,
                    "rollback shared validator did not receive synthetic authority")

    class ParserWriter:
        @staticmethod
        def validate_registry_for_append(registry):
            require(registry is parsers,
                    "parser shared validator did not receive synthetic authority")

    pair_guard_calls: list[dict] = []

    class PairWriter:
        @staticmethod
        def validate_registry_for_append(registry):
            require(registry is pairs,
                    "pair shared validator did not receive synthetic authority")
            pair_guard_calls.append(registry)

    writers = {
        module.RELEASE_WRITER_PATH: ReleaseWriter,
        module.ROLLBACK_WRITER_PATH: RollbackWriter,
        module.PARSER_WRITER_PATH: ParserWriter,
        module.PAIR_WRITER_PATH: PairWriter,
    }
    original_load = module.load
    original_load_module = module.load_module
    original_enforce = getattr(module, "enforce_runtime_authorities", None)
    try:
        module.load = lambda path: values[path]
        module.load_module = lambda path, _name: writers[path]
        if original_enforce is not None:
            module.enforce_runtime_authorities = lambda: None
        if validator_mode:
            counts = module.validate_source_authorities()
        else:
            counts = module.validate_source_registries()
    finally:
        module.load = original_load
        module.load_module = original_load_module
        if original_enforce is not None:
            module.enforce_runtime_authorities = original_enforce
    require(counts["approvedReleases"] == 2, "approved release source inventory was not preserved")
    require(counts["rollbackRequests"] == 1, "rollback request source inventory was not preserved")
    require(counts["reviewedParserArtifacts"] == 1, "parser source inventory was not preserved")
    require(counts["approvedReleasePairs"] == 1, "release pair source inventory was not preserved")
    require(pair_guard_calls == [pairs],
            "compatibility foundation did not delegate pair authority to the shared pair writer guard")


def expect_stale_empty_evidence_cleanup(reconciler) -> None:
    existing = [reconciler.LEGACY_EMPTY_SOURCE_EVIDENCE]
    source_counts = {
        "approvedReleases": 1,
        "rollbackRequests": 0,
        "reviewedParserArtifacts": 0,
        "approvedReleasePairs": 0,
    }
    changed = reconciler.reconcile_existing_evidence(existing, source_counts)
    require(changed, "nonempty source inventory did not reconcile existingEvidence")
    require(reconciler.LEGACY_EMPTY_SOURCE_EVIDENCE not in existing,
            "stale empty-inventory evidence survived legitimate source progression")
    for item in reconciler.EXISTING:
        require(item in existing, "canonical compatibility foundation evidence missing after progression")

    empty_existing = [reconciler.LEGACY_EMPTY_SOURCE_EVIDENCE]
    empty_counts = {field: 0 for field in source_counts}
    reconciler.reconcile_existing_evidence(empty_existing, empty_counts)
    require(reconciler.LEGACY_EMPTY_SOURCE_EVIDENCE in empty_existing,
            "empty-inventory evidence was removed before any source authority existed")


def expect_aggregate_validator_chain(reconciler) -> None:
    expected = [reconciler.FOUNDATION_VALIDATOR_PATH, reconciler.OPERABILITY_VALIDATOR_PATH]
    observed: list[Path] = []
    original = reconciler.run_validator

    def fake_run(path: Path, _label: str) -> None:
        observed.append(path)

    reconciler.run_validator = fake_run
    try:
        reconciler.run_canonical_validators()
    finally:
        reconciler.run_validator = original
    require(observed == expected,
            "foundation reconciler does not enforce foundation/operability validators in order")


def expect_canonical_transaction_rollback(reconciler) -> None:
    path = reconciler.PATH
    original = path.read_bytes()
    candidate = json.loads(original.decode("utf-8"))
    candidate["supplementalCompatibilityEvidence"] = ["synthetic canonical rollback probe"]

    def fail_post_write() -> None:
        raise RuntimeError("synthetic canonical compatibility validator failure")

    try:
        reconciler.commit_transaction(candidate, validator_runner=fail_post_write)
    except RuntimeError as exc:
        require("synthetic canonical compatibility validator failure" in str(exc),
                f"unexpected canonical rollback failure reason: {exc}")
    else:
        raise NegativeFailure("canonical compatibility reconcile accepted synthetic post-write failure")
    require(path.read_bytes() == original,
            "canonical compatibility reconcile left partial authority after validator failure")


def expect_aggregate_transaction_rollback(reconciler) -> None:
    path = reconciler.STATUS_PATH
    original = path.read_bytes()
    status = json.loads(original.decode("utf-8"))
    gate = next(
        (item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-008"),
        None,
    )
    require(isinstance(gate, dict), "OPS-P0-008 missing for foundation rollback probe")
    existing = gate.get("existingEvidence")
    require(isinstance(existing, list), "OPS-P0-008 existingEvidence missing for foundation rollback probe")
    existing.append("synthetic foundation aggregate rollback probe")

    def fail_post_write() -> None:
        raise RuntimeError("synthetic foundation aggregate validator failure")

    try:
        reconciler.commit_status_transaction(status, validator_runner=fail_post_write)
    except RuntimeError as exc:
        require("synthetic foundation aggregate validator failure" in str(exc),
                f"unexpected foundation rollback failure reason: {exc}")
    else:
        raise NegativeFailure("foundation reconcile accepted synthetic post-write aggregate failure")
    require(path.read_bytes() == original,
            "foundation reconcile left partial production status after aggregate failure")


def main() -> int:
    canonical_reconciler = load_module(CANONICAL_RECONCILER, "canonical_compatibility_reconciler")
    reconciler = load_module(RECONCILER, "compatibility_foundation_status_reconciler")
    validator = load_module(FOUNDATION_VALIDATOR, "compatibility_foundation_validator")

    expect_runtime_authority_identity(
        canonical_reconciler,
        (
            ("VALIDATOR_PATH", ROOT / "scripts/validate-memory-os-operability.py"),
            ("WORKFLOW_PATH", ROOT / ".github/workflows/client-server-support-window.yml"),
        ),
        "canonical compatibility reconciler",
    )
    expect_runtime_authority_identity(
        reconciler,
        (
            ("RELEASE_WRITER_PATH", ROOT / "scripts/request-memory-os-rollback-rehearsal.py"),
            ("ROLLBACK_WRITER_PATH", ROOT / "scripts/register-memory-os-release-baseline.py"),
            ("PARSER_WRITER_PATH", ROOT / "scripts/register-memory-os-release-compatibility-pair.py"),
            ("PAIR_WRITER_PATH", ROOT / "scripts/register-memory-os-parser-artifact.py"),
            ("FOUNDATION_VALIDATOR_PATH", ROOT / "scripts/validate-memory-os-operability.py"),
            ("OPERABILITY_VALIDATOR_PATH", ROOT / "scripts/validate-memory-os-version-compatibility-foundations.py"),
            ("WORKFLOW_PATH", ROOT / ".github/workflows/client-server-support-window.yml"),
        ),
        "compatibility foundation reconciler",
    )

    for field in reconciler.ZERO_COUNT_FIELDS:
        expect_rejection(reconciler, False, field)
        expect_rejection(reconciler, True, field)
        expect_rejection(reconciler, -1, field)
        reconciler.require_zero_count({field: 0}, field)
        expect_foundation_boolean_count_rejection(validator, field)

    expect_nonempty_source_inventory_allowed(reconciler, validator_mode=False)
    expect_nonempty_source_inventory_allowed(validator, validator_mode=True)
    expect_stale_empty_evidence_cleanup(reconciler)
    expect_aggregate_validator_chain(reconciler)
    expect_canonical_transaction_rollback(canonical_reconciler)
    expect_aggregate_transaction_rollback(reconciler)

    expect_source_authority_rejection(
        reconciler, validator, reconciler.RELEASE_REGISTRY_PATH, "registryClass",
        "CORRUPTED_RELEASE_AUTHORITY", "release",
    )
    expect_source_authority_rejection(
        reconciler, validator, reconciler.ROLLBACK_REGISTRY_PATH, "appendOnly",
        False, "rollback rehearsal",
    )
    expect_source_authority_rejection(
        reconciler, validator, reconciler.PARSER_REGISTRY_PATH, "productionEvidence",
        True, "parser artifact",
    )
    expect_source_authority_rejection(
        reconciler, validator, reconciler.PAIR_REGISTRY_PATH, "appendOnly",
        False, "release compatibility pair",
    )

    print("PASS: compatibility foundations preserve source progression, exact executable authority and rollback")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
