#!/usr/bin/env python3
"""Prove typed non-resurrection registry aggregate drift fails closed.

The canonical registry is never mutated. This harness imports the canonical
admission validator and writer, substitutes isolated generation/typed
registries, and proves both aggregate drift and in-place historical row
corruption are rejected before they can become append or candidate authority.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py"
WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
CANONICAL_REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
TEMP_PARENT = ROOT / "contracts/operations"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def expect_rejected(name: str, action: Callable[[], Any], expected_failure: type[BaseException]) -> None:
    try:
        action()
    except expected_failure:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"unexpected exception accepted as aggregate rejection for {name}: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"aggregate mutation unexpectedly accepted: {name}")


def main() -> int:
    require(VALIDATOR.is_file(), "typed non-resurrection admission validator missing")
    require(WRITER.is_file(), "typed non-resurrection admission writer missing")
    require(CONTRACT.is_file(), "typed non-resurrection admission contract missing")
    require(TEMP_PARENT.is_dir(), "repo-local aggregate negative temp parent missing")
    canonical = load_json(CANONICAL_REGISTRY)
    require(canonical.get("productionEvidence") is False, "canonical registry productionEvidence drift")
    require(canonical.get("productionReady") is False, "canonical registry productionReady drift")

    validator = load_module(VALIDATOR, "memory_os_non_resurrection_aggregate_negative")
    writer = load_module(WRITER, "memory_os_non_resurrection_writer_aggregate_negative")
    contract = load_json(CONTRACT)

    with tempfile.TemporaryDirectory(prefix=".memory-os-nonres-aggregate-negative-", dir=TEMP_PARENT) as tmp:
        tmp_path = Path(tmp)
        typed_registry = tmp_path / "typed-registry.json"
        generation_registry = tmp_path / "generation-registry.json"

        base_typed = {
            "schemaVersion": "memory-os-backup-restore-non-resurrection-admission-registry.v1",
            "appendOnly": True,
            "registeredRecordCount": 0,
            "completeRecordCount": 0,
            "candidateCoveredCount": 0,
            "records": [],
            "productionEvidence": False,
            "productionReady": False,
        }
        base_generation = {
            "schemaVersion": "memory-os-backup-restore-generation-evidence-registry.v1",
            "appendOnly": True,
            "registeredEvidenceCount": 0,
            "drillRequestBoundEvidenceCount": 0,
            "completeGenerationBoundBackupCount": 0,
            "completeGenerationBoundRestoreCount": 0,
            "productionEquivalentRecoveryCandidateCount": 0,
            "records": [],
            "productionEvidence": False,
            "productionReady": False,
        }
        write_json(generation_registry, base_generation)

        validator.REGISTRY = typed_registry
        validator.GEN_REGISTRY = generation_registry

        cases = (
            ("registeredRecordCount drift", "registeredRecordCount", 1),
            ("completeRecordCount drift", "completeRecordCount", 1),
            ("candidateCoveredCount drift", "candidateCoveredCount", 1),
            ("boolean registeredRecordCount", "registeredRecordCount", False),
            ("boolean completeRecordCount", "completeRecordCount", False),
            ("boolean candidateCoveredCount", "candidateCoveredCount", False),
        )
        for name, field, invalid_value in cases:
            mutated = copy.deepcopy(base_typed)
            mutated[field] = invalid_value
            write_json(typed_registry, mutated)
            write_json(generation_registry, base_generation)
            expect_rejected(name, validator.main, validator.Fail)

        write_json(typed_registry, base_typed)
        generation_mutated = copy.deepcopy(base_generation)
        generation_mutated["productionEquivalentRecoveryCandidateCount"] = False
        write_json(generation_registry, generation_mutated)
        expect_rejected("boolean generation final candidate count", validator.main, validator.Fail)

        # A historical typed row whose identity/counters still look internally
        # consistent must not be trusted merely because evidenceComplete=false
        # makes candidate derivation short-circuit. The append writer must
        # revalidate the row itself and reject an in-place schema mutation.
        generation_id = "brge_aggregate_negative"
        historical = {field: None for field in contract["requiredRecordFields"]}
        historical.update({
            "schemaVersion": "memory-os-backup-restore-non-resurrection-record.invalid",
            "recordId": "brnr_aggregate_negative",
            "generationEvidenceId": generation_id,
            "evidenceComplete": False,
            "productionTraffic": False,
            "productionCredentials": False,
            "productionEvidence": False,
            "productionReady": False,
        })
        historical_registry = copy.deepcopy(base_typed)
        historical_registry.update({
            "registeredRecordCount": 1,
            "completeRecordCount": 0,
            "candidateCoveredCount": 0,
            "records": [historical],
        })
        historical_generation_registry = copy.deepcopy(base_generation)
        historical_generation_registry.update({
            "registeredEvidenceCount": 1,
            "records": [{"evidenceId": generation_id}],
        })
        write_json(generation_registry, historical_generation_registry)
        writer.GEN_EVIDENCE_REGISTRY = generation_registry
        expect_rejected(
            "historical typed row schema mutation before append",
            lambda: writer.validate_registry_for_append(historical_registry),
            writer.Fail,
        )

        validator.REGISTRY = Path(tempfile.gettempdir()) / "memory-os-outside-root-registry.json"
        validator.GEN_REGISTRY = generation_registry
        expect_rejected("typed registry path escapes repository root", validator.main, validator.Fail)

    print("Memory OS typed non-resurrection registry aggregate negative suite PASS")
    print("aggregate counters may not override row-derived authority: true")
    print("historical typed row mutation accepted before append: false")
    print("boolean aggregate counters accepted: false")
    print("escaped registry path accepted: false")
    print("unexpected exception accepted as valid rejection: false")
    print("repo-local isolated mutation fixtures: true")
    print("canonical registries mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE NON-RESURRECTION AGGREGATE NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
