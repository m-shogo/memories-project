#!/usr/bin/env python3
"""Prove OPS-P0-007 snapshot generation and validation reject corrupt authorities."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate-memory-os-ops-p0-007-admission-snapshot.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-ops-p0-007-admission-snapshot.py"
SNAPSHOT = ROOT / "contracts/operations/ops-p0-007-admission-snapshot.v1.json"
OBJECTIVES = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
REQUESTS = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
GENERATION = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
TYPED = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
OBJECTIVE_WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"


class Fail(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Fail(f"expected object: {path.relative_to(ROOT)}")
    return value


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def load_generator_module():
    spec = importlib.util.spec_from_file_location("memory_os_ops_p0_007_snapshot_negative_generator", GENERATOR)
    if spec is None or spec.loader is None:
        raise Fail("cannot load strict snapshot generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_validator(expect_success: bool, label: str) -> None:
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if expect_success:
        if proc.returncode != 0:
            raise Fail(f"{label}: baseline validator failed: {proc.stderr or proc.stdout}")
        return
    if proc.returncode != 1:
        raise Fail(f"{label}: expected fail-closed exit 1, got {proc.returncode}: {proc.stderr or proc.stdout}")
    if "OPS-P0-007 ADMISSION SNAPSHOT FAILED:" not in proc.stderr:
        raise Fail(f"{label}: rejection did not come from canonical fail-closed boundary: {proc.stderr or proc.stdout}")
    if "Traceback (most recent call last)" in proc.stderr:
        raise Fail(f"{label}: rejection surfaced an implementation exception instead of a controlled failure")


def run_generator_rejects(label: str, expected_messages: str | tuple[str, ...]) -> None:
    before = SNAPSHOT.read_bytes()
    proc = subprocess.run(
        [sys.executable, str(GENERATOR)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 1:
        raise Fail(f"{label}: expected generator fail-closed exit 1, got {proc.returncode}: {proc.stderr or proc.stdout}")
    output = proc.stderr or proc.stdout
    allowed = (expected_messages,) if isinstance(expected_messages, str) else expected_messages
    if not any(message in output for message in allowed):
        raise Fail(f"{label}: generator rejection did not use expected authority boundary: {output}")
    if "Traceback (most recent call last)" in output:
        raise Fail(f"{label}: generator rejection surfaced an implementation exception")
    if SNAPSHOT.read_bytes() != before:
        raise Fail(f"{label}: rejected generator attempt mutated deterministic snapshot")


def run_generator_post_write_validator_substitution_rejected() -> None:
    before = SNAPSHOT.read_bytes()
    module = load_generator_module()
    original_validator = module.validate_generated_snapshot

    def reject_after_write() -> None:
        raise RuntimeError("synthetic post-write snapshot validation failure")

    module.validate_generated_snapshot = reject_after_write
    try:
        try:
            module.main()
        except SystemExit as exc:
            if "strict snapshot generator execution helper drift" not in str(exc):
                raise Fail(f"post-write validator substitution rejected at unexpected boundary: {exc}") from exc
        else:
            raise Fail("post-write validator substitution unexpectedly bypassed execution authority")
    finally:
        module.validate_generated_snapshot = original_validator

    if SNAPSHOT.read_bytes() != before:
        raise Fail("post-write validator substitution mutated deterministic snapshot")


def run_generator_full_admission_chain_required() -> None:
    before = SNAPSHOT.read_bytes()
    module = load_generator_module()
    original_validators = module.run_full_admission_validators

    def reject_full_admission() -> None:
        raise RuntimeError("synthetic full admission validation rejection")

    module.run_full_admission_validators = reject_full_admission
    try:
        try:
            module.main()
        except SystemExit as exc:
            if "strict snapshot generator execution helper drift" not in str(exc):
                raise Fail(f"full admission helper substitution rejected at unexpected boundary: {exc}") from exc
        else:
            raise Fail("strict snapshot generator accepted substituted full admission validator chain")
    finally:
        module.run_full_admission_validators = original_validators

    if SNAPSHOT.read_bytes() != before:
        raise Fail("full admission helper substitution mutated deterministic snapshot")


def run_generator_atomic_write_failure() -> None:
    snapshot_before = SNAPSHOT.read_bytes()
    status_before = STATUS.read_bytes()
    module = load_generator_module()
    original_replace = module.os.replace

    def reject_replace(source: str | Path, destination: str | Path) -> None:
        raise OSError("synthetic strict snapshot atomic replace rejection")

    module.os.replace = reject_replace
    try:
        try:
            module.atomic_write_text(SNAPSHOT, snapshot_before.decode("utf-8") + " ")
        except SystemExit as exc:
            if "cannot atomically write contracts/operations/ops-p0-007-admission-snapshot.v1.json" not in str(exc):
                raise Fail(f"atomic strict snapshot write rejected at wrong boundary: {exc}") from exc
        else:
            raise Fail("synthetic strict snapshot atomic replace failure unexpectedly accepted")
    finally:
        module.os.replace = original_replace

    if SNAPSHOT.read_bytes() != snapshot_before:
        raise Fail("atomic replace rejection mutated canonical strict snapshot")
    if STATUS.read_bytes() != status_before:
        raise Fail("atomic replace rejection mutated canonical production status")
    leftovers = list(SNAPSHOT.parent.glob(f".{SNAPSHOT.name}.*.tmp"))
    if leftovers:
        raise Fail(f"atomic replace rejection left temporary strict snapshot authority files: {leftovers}")


def run_generator_authority_substitution() -> None:
    before = SNAPSHOT.read_bytes()
    module = load_generator_module()
    substitutions = (
        ("OUTPUT", module.OBJECTIVES),
        ("ELIGIBILITY_HELPER", module.OBJECTIVE_WRITER),
        ("BLOCKER_HELPER", module.OBJECTIVE_WRITER),
        ("SNAPSHOT_VALIDATOR", module.OBJECTIVE_WRITER),
        ("RECOVERY_OBJECTIVE_VALIDATOR", module.OBJECTIVE_WRITER),
        ("DRILL_REQUEST_VALIDATOR", module.OBJECTIVE_WRITER),
        ("GEN_EVIDENCE_VALIDATOR", module.OBJECTIVE_WRITER),
        ("TYPED_VALIDATOR", module.OBJECTIVE_WRITER),
        ("OBJECTIVES", module.DRILL_REQUESTS),
        ("DRILL_REQUESTS", module.OBJECTIVES),
        ("GEN_EVIDENCE", module.TYPED),
        ("TYPED", module.GEN_EVIDENCE),
        ("STATUS", module.OBJECTIVES),
        ("OBJECTIVE_WRITER", module.DRILL_REQUEST_WRITER),
        ("DRILL_REQUEST_WRITER", module.OBJECTIVE_WRITER),
        ("GEN_EVIDENCE_WRITER", module.TYPED_WRITER),
        ("TYPED_WRITER", module.GEN_EVIDENCE_WRITER),
    )
    for field, substitute in substitutions:
        original = getattr(module, field)
        try:
            setattr(module, field, substitute)
            try:
                module.enforce_runtime_authorities()
            except SystemExit as exc:
                if "strict snapshot authority" not in str(exc):
                    raise Fail(f"{field} substitution rejected outside authority boundary: {exc}") from exc
            else:
                raise Fail(f"strict snapshot generator accepted {field} authority substitution")
        finally:
            setattr(module, field, original)
    module.enforce_runtime_authorities()
    if SNAPSHOT.read_bytes() != before:
        raise Fail("strict snapshot authority substitution mutated deterministic snapshot")


def mutate_field(field: str, value: Any) -> Callable[[dict[str, Any]], None]:
    def apply(registry: dict[str, Any]) -> None:
        registry[field] = value
    return apply


def remove_field(field: str) -> Callable[[dict[str, Any]], None]:
    def apply(registry: dict[str, Any]) -> None:
        registry.pop(field, None)
    return apply


def mutate_snapshot_requirement(snapshot: dict[str, Any]) -> None:
    requirements = snapshot.get("downstreamRequirements")
    if not isinstance(requirements, list) or not requirements:
        raise Fail("snapshot downstreamRequirements missing")
    replacement = list(requirements)
    replacement[0] = "automatically promote production after local restore validation"
    snapshot["downstreamRequirements"] = replacement


def mutate_ops7_missing(reorder: bool) -> Callable[[dict[str, Any]], None]:
    def apply(status: dict[str, Any]) -> None:
        areas = status.get("areas")
        if not isinstance(areas, list):
            raise Fail("status areas missing")
        ops7 = next((row for row in areas if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
        if not isinstance(ops7, dict) or not isinstance(ops7.get("missingEvidence"), list):
            raise Fail("OPS-P0-007 missingEvidence missing")
        if reorder:
            ops7["missingEvidence"] = list(reversed(ops7["missingEvidence"]))
        else:
            replacement = list(ops7["missingEvidence"])
            replacement[0] = "fabricated replacement blocker with unchanged list length"
            ops7["missingEvidence"] = replacement
    return apply


def restore_all(originals: dict[Path, bytes]) -> None:
    for path, payload in originals.items():
        if path.is_symlink():
            path.unlink()
        path.write_bytes(payload)


def run_source_symlink_escape(originals: dict[Path, bytes]) -> None:
    external = Path("/tmp/memory-os-ops-p0-007-objective-authority.json")
    external.write_bytes(originals[OBJECTIVES])
    restore_all(originals)
    OBJECTIVES.unlink()
    OBJECTIVES.symlink_to(external)
    try:
        run_validator(False, "objective source symlink escape")
        run_generator_rejects("generator objective source symlink escape", "strict snapshot authority")
    finally:
        if OBJECTIVES.is_symlink():
            OBJECTIVES.unlink()
        OBJECTIVES.write_bytes(originals[OBJECTIVES])
        external.unlink(missing_ok=True)


def run_module_symlink_escape(originals: dict[Path, bytes]) -> None:
    external = Path("/tmp/memory-os-ops-p0-007-objective-writer.py")
    external.write_bytes(originals[OBJECTIVE_WRITER])
    restore_all(originals)
    OBJECTIVE_WRITER.unlink()
    OBJECTIVE_WRITER.symlink_to(external)
    try:
        run_validator(False, "objective writer module symlink escape")
        run_generator_rejects(
            "generator objective writer module symlink escape",
            "strict snapshot authority",
        )
    finally:
        if OBJECTIVE_WRITER.is_symlink():
            OBJECTIVE_WRITER.unlink()
        OBJECTIVE_WRITER.write_bytes(originals[OBJECTIVE_WRITER])
        external.unlink(missing_ok=True)


def main() -> int:
    originals = {
        SNAPSHOT: SNAPSHOT.read_bytes(),
        OBJECTIVES: OBJECTIVES.read_bytes(),
        REQUESTS: REQUESTS.read_bytes(),
        GENERATION: GENERATION.read_bytes(),
        TYPED: TYPED.read_bytes(),
        STATUS: STATUS.read_bytes(),
        OBJECTIVE_WRITER: OBJECTIVE_WRITER.read_bytes(),
    }
    cases: list[tuple[str, Path, Callable[[dict[str, Any]], None]]] = [
        ("snapshot unknown production authority field", SNAPSHOT, mutate_field("productionAuthorization", True)),
        ("snapshot missing production readiness field", SNAPSHOT, remove_field("productionReady")),
        ("snapshot boolean registered generation count", SNAPSHOT, mutate_field("registeredEnvironmentGenerationCount", False)),
        ("snapshot downstream requirement projection", SNAPSHOT, mutate_snapshot_requirement),
        ("snapshot next action projection", SNAPSHOT, mutate_field("nextAction", "automatically promote production")),
        ("objective boolean aggregate count", OBJECTIVES, mutate_field("approvedObjectiveCount", True)),
        ("objective append-only boundary", OBJECTIVES, mutate_field("appendOnly", False)),
        ("objective schema boundary", OBJECTIVES, mutate_field("schemaVersion", "memory-os-recovery-objectives-registry.corrupt")),
        ("objective production evidence boundary", OBJECTIVES, mutate_field("productionEvidence", True)),
        ("objective production readiness boundary", OBJECTIVES, mutate_field("productionReady", True)),
        ("drill boolean aggregate count", REQUESTS, mutate_field("registeredRequestCount", True)),
        ("drill append-only boundary", REQUESTS, mutate_field("appendOnly", False)),
        ("drill production evidence boundary", REQUESTS, mutate_field("productionEvidence", True)),
        ("generation boolean aggregate count", GENERATION, mutate_field("registeredEvidenceCount", True)),
        ("generation append-only boundary", GENERATION, mutate_field("appendOnly", False)),
        ("generation production readiness boundary", GENERATION, mutate_field("productionReady", True)),
        ("typed boolean aggregate count", TYPED, mutate_field("completeRecordCount", True)),
        ("typed append-only boundary", TYPED, mutate_field("appendOnly", False)),
        ("typed production evidence boundary", TYPED, mutate_field("productionEvidence", True)),
        ("canonical blocker replacement with unchanged count", STATUS, mutate_ops7_missing(False)),
        ("canonical blocker ordering drift", STATUS, mutate_ops7_missing(True)),
        ("production decision promotion", STATUS, mutate_field("productionDecision", "GO")),
    ]
    generator_cases: list[tuple[str, Callable[[dict[str, Any]], None], str | tuple[str, ...]]] = [
        (
            "generator canonical blocker replacement",
            mutate_ops7_missing(False),
            (
                "typed non-resurrection canonical admission authority invalid",
                "canonical OPS-P0-007 blocker authority invalid",
            ),
        ),
        (
            "generator canonical blocker ordering drift",
            mutate_ops7_missing(True),
            (
                "typed non-resurrection canonical admission authority invalid",
                "canonical OPS-P0-007 blocker authority invalid",
            ),
        ),
        (
            "generator production decision promotion",
            mutate_field("productionDecision", "GO"),
            (
                "typed non-resurrection canonical admission authority invalid",
                "production decision must remain NO_GO",
            ),
        ),
    ]

    try:
        run_validator(True, "clean baseline")
        run_generator_atomic_write_failure()
        run_generator_full_admission_chain_required()
        run_generator_post_write_validator_substitution_rejected()
        run_generator_authority_substitution()
        run_source_symlink_escape(originals)
        run_module_symlink_escape(originals)
        for label, path, mutate in cases:
            restore_all(originals)
            authority = copy.deepcopy(load(path))
            mutate(authority)
            write(path, authority)
            run_validator(False, label)

        for label, mutate, expected_messages in generator_cases:
            restore_all(originals)
            status = copy.deepcopy(load(STATUS))
            mutate(status)
            write(STATUS, status)
            run_generator_rejects(label, expected_messages)

        restore_all(originals)
        run_validator(True, "restored baseline")
    finally:
        restore_all(originals)

    for path, payload in originals.items():
        if path.read_bytes() != payload:
            raise Fail(f"negative suite mutated canonical authority: {path.relative_to(ROOT)}")

    print("Memory OS OPS-P0-007 strict admission snapshot negative validation PASS")
    print(f"controlled validator corruption cases rejected: {len(cases)}")
    print(f"controlled generator corruption cases rejected: {len(generator_cases)}")
    print("strict snapshot generator data/executable authority substitutions rejected: true")
    print("strict snapshot generator full admission helper substitution rejected before publication: true")
    print("strict snapshot generator post-write validator substitution rejected before publication: true")
    print("snapshot source symlink escape rejected by validator and generator: true")
    print("snapshot executable module symlink escape rejected by validator and generator: true")
    print("snapshot unknown/missing field drift rejected: true")
    print("snapshot boolean count drift rejected: true")
    print("snapshot downstream requirement/next-action drift rejected: true")
    print("failed atomic snapshot replace preserves canonical bytes and removes temporary files: true")
    print("canonical authority files preserved byte-for-byte: true")
    print("rejected generator attempts leave snapshot byte-for-byte unchanged: true")
    print("canonical six-blocker content and ordering preserved: true")
    print("production evidence/readiness/decision promotion rejected: true")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, json.JSONDecodeError, OSError) as exc:
        print(f"OPS-P0-007 ADMISSION SNAPSHOT NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
