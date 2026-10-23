#!/usr/bin/env python3
"""Prove OPS-P0-007 snapshot generation and validation reject corrupt authorities."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable
from unittest import mock

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


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def require_material_mutation(before: dict[str, Any], after: dict[str, Any], label: str) -> None:
    # Python equality equates False/0 and True/1; JSON preserves those types.
    if json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True):
        raise Fail(f"{label}: negative fixture mutation was a no-op")


def load_generator_module():
    spec = importlib.util.spec_from_file_location("memory_os_ops_p0_007_snapshot_negative_generator", GENERATOR)
    if spec is None or spec.loader is None:
        raise Fail("cannot load strict snapshot generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_bounded_python(path: Path, label: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [sys.executable, str(path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=90,
        )
    except subprocess.TimeoutExpired as exc:
        raise Fail(f"{label}: canonical Python validation timed out after 90s") from exc


def prove_subprocess_timeout_guard() -> None:
    # An injected timeout must become a controlled failure, not a hang or a
    # generic interpreter traceback that masquerades as an admission rejection.
    with mock.patch.object(
        subprocess,
        "run",
        side_effect=subprocess.TimeoutExpired(cmd=["synthetic"], timeout=90),
    ):
        for path in (VALIDATOR, GENERATOR):
            try:
                run_bounded_python(path, "synthetic timeout")
            except Fail as exc:
                if str(exc) != "synthetic timeout: canonical Python validation timed out after 90s":
                    raise Fail(f"timeout rejected outside intended bounded subprocess guard: {exc}") from exc
            else:
                raise Fail("synthetic subprocess timeout unexpectedly accepted")


# Exact case binding prevents an unrelated canonical failure from satisfying
# the targeted snapshot/production-decision corruption negatives.
CASE_SPECIFIC_VALIDATOR_REJECTIONS = {
    "snapshot unknown production authority field": "snapshot field set drift",
    "snapshot missing production readiness field": "snapshot field set drift",
    "snapshot boolean registered generation count": "snapshot count invalid: registeredEnvironmentGenerationCount",
    "snapshot downstream requirement projection": "snapshot downstream requirement projection drift",
    "snapshot next action projection": "snapshot nextAction projection drift",
    "production decision promotion": "status production decision drift",
    "objective boolean aggregate count": "recovery objective canonical registry authority invalid: approvedObjectiveCount must be a non-boolean integer",
    "objective append-only boundary": "recovery objective canonical registry authority invalid: objectives registry must remain append-only",
    "objective schema boundary": "recovery objective canonical registry authority invalid: registry schema drift",
    "objective production evidence boundary": "recovery objective canonical registry authority invalid: objectives registry productionEvidence must remain false",
    "objective production readiness boundary": "recovery objective canonical registry authority invalid: objectives registry productionReady must remain false",
    "drill boolean aggregate count": "restore drill request canonical registry authority invalid: registeredRequestCount must be a non-boolean integer",
    "drill append-only boundary": "restore drill request canonical registry authority invalid: request registry must remain append-only",
    "drill production evidence boundary": "restore drill request canonical registry authority invalid: request registry productionEvidence must remain false",
}


def require_case_specific_validator_rejection(stderr: str, expected: str, label: str) -> None:
    diagnostic = f"OPS-P0-007 ADMISSION SNAPSHOT FAILED: {expected}"
    if stderr.splitlines() != [diagnostic]:
        raise Fail(f"{label}: rejected outside intended canonical snapshot diagnostic: {stderr!r}")


def prove_case_specific_validator_classifier() -> None:
    expected = "snapshot field set drift"
    diagnostic = f"OPS-P0-007 ADMISSION SNAPSHOT FAILED: {expected}"
    require_case_specific_validator_rejection(diagnostic + "\n", expected, "synthetic positive")
    for stderr in (
        "OPS-P0-007 ADMISSION SNAPSHOT FAILED: unrelated failure\n",
        "OPS-P0-007 ADMISSION SNAPSHOT FAILED: unrelated failure\n" + diagnostic + "\n",
        diagnostic + "\nOPS-P0-007 ADMISSION SNAPSHOT FAILED: unrelated failure\n",
    ):
        try:
            require_case_specific_validator_rejection(stderr, expected, "synthetic wrong diagnostic")
        except Fail as exc:
            if "rejected outside intended canonical snapshot diagnostic" not in str(exc):
                raise Fail(f"classifier rejected outside intended diagnostic guard: {exc}") from exc
        else:
            raise Fail("snapshot classifier accepted unrelated or multiline rejection")


def run_validator(expect_success: bool, label: str) -> None:
    proc = run_bounded_python(VALIDATOR, label)
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
    expected = CASE_SPECIFIC_VALIDATOR_REJECTIONS.get(label)
    if expected is not None:
        require_case_specific_validator_rejection(proc.stderr, expected, label)


# Canonical typed admission can return a two-line nested local-restore
# diagnostic. Bind its second line to the exact mutation rather than accepting
# arbitrary multiline errors or requiring an incorrect one-line format.
NESTED_GENERATOR_REJECTIONS = {
    "generator canonical blocker replacement": "LOCAL APPLE REPLAY RESTORE VALIDATION FAILED: OPS-P0-007 missingEvidence must equal the ordered canonical six production blockers",
    "generator canonical blocker ordering drift": "LOCAL APPLE REPLAY RESTORE VALIDATION FAILED: OPS-P0-007 missingEvidence must equal the ordered canonical six production blockers",
    "generator production decision promotion": "LOCAL APPLE REPLAY RESTORE VALIDATION FAILED: local replay restore cannot change production decision",
}


def require_expected_generator_diagnostic(output: str, allowed: tuple[str, ...], label: str) -> None:
    lines = output.strip().splitlines()
    prefixes = tuple(
        prefix
        for message in allowed
        for prefix in (message, f"generated strict snapshot invalid: {message}")
    )
    valid_single = len(lines) == 1 and lines[0].startswith(prefixes)
    nested = NESTED_GENERATOR_REJECTIONS.get(label)
    valid_nested = (
        len(lines) == 2
        and nested is not None
        and lines[0].startswith("typed non-resurrection canonical admission authority invalid: local Apple replay restore validator failed:")
        and lines[0].startswith(prefixes)
        and lines[1] == nested
    )
    if not (valid_single or valid_nested):
        raise Fail(f"{label}: generator rejection did not use one intended authority diagnostic: {output!r}")


def prove_generator_diagnostic_classifier() -> None:
    expected = ("canonical OPS-P0-007 blocker authority invalid",)
    valid = "canonical OPS-P0-007 blocker authority invalid: synthetic detail"
    require_expected_generator_diagnostic(valid + "\n", expected, "synthetic positive")
    nested_prefix = "typed non-resurrection canonical admission authority invalid: local Apple replay restore validator failed:"
    nested_label = "generator canonical blocker replacement"
    nested_line = NESTED_GENERATOR_REJECTIONS[nested_label]
    require_expected_generator_diagnostic(
        nested_prefix + "\n" + nested_line + "\n",
        ("typed non-resurrection canonical admission authority invalid",),
        nested_label,
    )
    for output in (
        "unrelated failure: " + valid + "\n",
        "unrelated failure\n" + valid + "\n",
        valid + "\nunrelated failure\n",
        nested_prefix + "\nunrelated failure\n",
        nested_prefix + "\n" + nested_line + "\nunrelated failure\n",
    ):
        try:
            require_expected_generator_diagnostic(output, expected, "synthetic unrelated diagnostic")
        except Fail as exc:
            if "one intended authority diagnostic" not in str(exc):
                raise Fail(f"generator classifier rejected outside intended guard: {exc}") from exc
        else:
            raise Fail("generator classifier accepted unrelated or multiline rejection")


def run_generator_rejects(label: str, expected_messages: str | tuple[str, ...]) -> None:
    before = SNAPSHOT.read_bytes()
    proc = run_bounded_python(GENERATOR, label)
    if proc.returncode != 1:
        raise Fail(f"{label}: expected generator fail-closed exit 1, got {proc.returncode}: {proc.stderr or proc.stdout}")
    output = proc.stderr or proc.stdout
    allowed = (expected_messages,) if isinstance(expected_messages, str) else expected_messages
    require_expected_generator_diagnostic(output, allowed, label)
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


def run_generator_atomic_write_mode_preservation() -> None:
    snapshot_before = SNAPSHOT.read_bytes()
    original_mode = mode(SNAPSHOT)
    module = load_generator_module()
    try:
        SNAPSHOT.chmod(0o640)
        module.atomic_write_text(SNAPSHOT, snapshot_before.decode("utf-8"))
        if SNAPSHOT.read_bytes() != snapshot_before:
            raise Fail("successful atomic strict snapshot rewrite changed canonical bytes")
        if mode(SNAPSHOT) != 0o640:
            raise Fail(f"successful atomic strict snapshot rewrite changed mode: {oct(mode(SNAPSHOT))}")
    finally:
        SNAPSHOT.chmod(original_mode)


def run_generator_atomic_write_failure() -> None:
    snapshot_before = SNAPSHOT.read_bytes()
    status_before = STATUS.read_bytes()
    original_mode = mode(SNAPSHOT)
    module = load_generator_module()
    original_replace = module.os.replace

    def reject_replace(source: str | Path, destination: str | Path) -> None:
        raise OSError("synthetic strict snapshot atomic replace rejection")

    try:
        SNAPSHOT.chmod(0o640)
        module.os.replace = reject_replace
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
        SNAPSHOT.chmod(original_mode)
        raise Fail("atomic replace rejection mutated canonical strict snapshot")
    if mode(SNAPSHOT) != 0o640:
        SNAPSHOT.chmod(original_mode)
        raise Fail(f"atomic replace rejection changed canonical strict snapshot mode: {oct(mode(SNAPSHOT))}")
    SNAPSHOT.chmod(original_mode)
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
    # Never overwrite a fixed /tmp pathname: another process may own it or
    # replace it with a symlink to an unrelated file.
    with tempfile.TemporaryDirectory(prefix="memory-os-ops-p0-007-objective-negative-") as tmp:
        external = Path(tmp) / "objective-authority.json"
        external.write_bytes(originals[OBJECTIVES])
        original_mode = mode(OBJECTIVES)
        restore_all(originals)
        OBJECTIVES.unlink()
        try:
            OBJECTIVES.symlink_to(external)
            run_validator(False, "objective source symlink escape")
            run_generator_rejects("generator objective source symlink escape", "strict snapshot authority")
        finally:
            if OBJECTIVES.is_symlink():
                OBJECTIVES.unlink()
            OBJECTIVES.write_bytes(originals[OBJECTIVES])
            OBJECTIVES.chmod(original_mode)


def run_module_symlink_escape(originals: dict[Path, bytes]) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-ops-p0-007-writer-negative-") as tmp:
        external = Path(tmp) / "objective-writer.py"
        external.write_bytes(originals[OBJECTIVE_WRITER])
        original_mode = mode(OBJECTIVE_WRITER)
        restore_all(originals)
        OBJECTIVE_WRITER.unlink()
        try:
            OBJECTIVE_WRITER.symlink_to(external)
            run_validator(False, "objective writer module symlink escape")
            run_generator_rejects(
                "generator objective writer module symlink escape",
                "strict snapshot authority",
            )
        finally:
            if OBJECTIVE_WRITER.is_symlink():
                OBJECTIVE_WRITER.unlink()
            OBJECTIVE_WRITER.write_bytes(originals[OBJECTIVE_WRITER])
            OBJECTIVE_WRITER.chmod(original_mode)


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
    original_modes = {path: mode(path) for path in originals}
    require_material_mutation({"count": 0}, {"count": False}, "boolean/zero mutation guard")
    require_material_mutation({"count": 1}, {"count": True}, "boolean/one mutation guard")
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
        prove_case_specific_validator_classifier()
        prove_generator_diagnostic_classifier()
        prove_subprocess_timeout_guard()
        run_validator(True, "clean baseline")
        run_generator_atomic_write_mode_preservation()
        run_generator_atomic_write_failure()
        run_generator_full_admission_chain_required()
        run_generator_post_write_validator_substitution_rejected()
        run_generator_authority_substitution()
        run_source_symlink_escape(originals)
        run_module_symlink_escape(originals)
        for label, path, mutate in cases:
            restore_all(originals)
            canonical = load(path)
            authority = copy.deepcopy(canonical)
            mutate(authority)
            require_material_mutation(canonical, authority, label)
            write(path, authority)
            run_validator(False, label)

        for label, mutate, expected_messages in generator_cases:
            restore_all(originals)
            canonical = load(STATUS)
            status = copy.deepcopy(canonical)
            mutate(status)
            require_material_mutation(canonical, status, label)
            write(STATUS, status)
            run_generator_rejects(label, expected_messages)

        restore_all(originals)
        run_validator(True, "restored baseline")
    finally:
        restore_all(originals)

    for path, payload in originals.items():
        if path.read_bytes() != payload:
            raise Fail(f"negative suite mutated canonical authority: {path.relative_to(ROOT)}")
        if mode(path) != original_modes[path]:
            raise Fail(f"negative suite changed canonical authority file mode: {path.relative_to(ROOT)}")

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
    print("successful atomic snapshot rewrite preserves canonical mode: true")
    print("failed atomic snapshot replace preserves canonical bytes/mode and removes temporary files: true")
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
