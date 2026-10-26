#!/usr/bin/env python3
"""Prove fail-closed negative cases for recovery-objective approval admission."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-recovery-objectives.py"
CONTRACT = ROOT / "contracts/operations/recovery-objectives-admission-contract.v1.json"
APPROVAL_FIXTURE_DIR = ROOT / "docs/fixtures/memory-os-operability/recovery-objectives-approval"
APPROVAL_FIXTURE_REF = "docs/fixtures/memory-os-operability/recovery-objectives-approval"


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


def load_writer():
    module = load_module(WRITER, "memory_os_recovery_objectives_writer_negative")
    module.APPROVAL_DIR = APPROVAL_FIXTURE_DIR
    return module


def expect_rejected(writer: Any, name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except writer.Fail:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")


def expect_validator_rejected(validator: Any, name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except validator.Fail:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"validator negative case unexpectedly accepted: {name}")


def base_record() -> dict[str, Any]:
    return {
        "schemaVersion": "memory-os-recovery-objectives-record.v1",
        "objectiveId": "ro_negative_base",
        "scope": "PRODUCTION_RECOVERY_OBJECTIVES",
        "rpoSeconds": 60,
        "rtoSeconds": 120,
        "maximumObjectDatabaseSkewSeconds": 10,
        "rpoMeasurementMethod": "measure backup watermark to selected restore point",
        "rtoMeasurementMethod": "measure drill start to validated recovery completion",
        "skewMeasurementMethod": "compare restored database and object recovery point timestamps",
        "ownerRef": "contracts/operations/recovery-objectives-admission-contract.v1.json",
        "approvalEvidenceRefs": [
            f"{APPROVAL_FIXTURE_REF}/recovery-owner.valid.json",
            f"{APPROVAL_FIXTURE_REF}/operability.valid.json",
        ],
        "approvedAt": "2026-08-08T00:00:00Z",
        "supersedesObjectiveId": None,
        "productionEvidence": False,
        "productionReady": False,
    }


def exercise_registry_corruption(writer: Any) -> None:
    baseline = writer.load(writer.REGISTRY)
    writer.validate_registry_for_append(copy.deepcopy(baseline))
    cases = (
        ("objective registry schema drift", "schemaVersion", "memory-os-recovery-objectives-registry.corrupt"),
        ("objective registry append-only disabled", "appendOnly", False),
        ("objective registry production evidence forged", "productionEvidence", True),
        ("objective registry production ready forged", "productionReady", True),
        ("approved objective count boolean", "approvedObjectiveCount", True),
        ("approved objective count drift", "approvedObjectiveCount", baseline.get("approvedObjectiveCount", 0) + 1),
        ("current objective pointer drift", "currentObjectiveId", "ro_negative_unknown"),
    )
    for name, field, value in cases:
        mutated = copy.deepcopy(baseline)
        mutated[field] = value
        expect_rejected(writer, name, lambda mutated=mutated: writer.validate_registry_for_append(mutated))


def prove_recovery_objective_json_reader(validator) -> None:
    """Exercise the real objective reader without creating human approval evidence."""
    before = (validator.CONTRACT.read_bytes(), validator.REGISTRY.read_bytes())
    with tempfile.TemporaryDirectory(prefix="memory-os-recovery-objective-json-", dir=ROOT) as directory:
        path = Path(directory) / "candidate.json"
        positive = b'{"safe":true,"nested":{"count":1}}'
        path.write_bytes(positive)
        require(validator.load(path) == {"safe": True, "nested": {"count": 1}}, "recovery objective JSON positive control failed")
        cases = (
            ("duplicate root", b'{"safe":true,"safe":false}', "recovery objective JSON duplicate key refused"),
            ("duplicate nested", b'{"nested":{"a":1,"a":2}}', "recovery objective JSON duplicate key refused"),
            ("NaN", b'{"number":NaN}', "recovery objective JSON nonfinite number refused"),
            ("Infinity", b'{"number":Infinity}', "recovery objective JSON nonfinite number refused"),
            ("negative Infinity", b'{"number":-Infinity}', "recovery objective JSON nonfinite number refused"),
            ("float overflow", b'{"number":1e999}', "recovery objective JSON nonfinite number refused"),
            ("large integer", b'{"number":' + b"9" * 5000 + b"}", "recovery objective JSON integer too large"),
            ("oversized JSON", b'{"data":"' + b"x" * validator.MAX_JSON_BYTES + b'"}', "recovery objective JSON size limit exceeded"),
            ("invalid UTF-8", b'{"private":"\xff"}', "recovery objective JSON unreadable or invalid"),
            ("malformed private", b'{"private":"synthetic-secret",', "recovery objective JSON unreadable or invalid"),
            ("nonobject root", b"[]", "recovery objective JSON root must be object"),
        )
        def rejected(candidate, expected: str, label: str) -> None:
            try:
                validator.load(candidate)
            except validator.Fail as exc:
                require(str(exc) == expected, f"{label}: wrong recovery objective JSON rejection boundary")
                require("synthetic-secret" not in str(exc), f"{label}: private marker disclosed")
            else:
                raise Fail(f"{label}: unsafe recovery objective JSON accepted")
        for label, payload, expected in cases:
            path.write_bytes(payload)
            rejected(path, expected, label)
        path.write_bytes(positive)
        alias = Path(directory) / "alias.json"
        alias.symlink_to(path)
        rejected(alias, "recovery objective JSON path unsafe", "symlink")
        rejected(Path(directory), "recovery objective JSON path unsafe", "directory")
        rejected(Path(directory) / "missing.json", "recovery objective JSON path missing or outside repository", "missing")
        rejected("candidate.json", "recovery objective JSON path invalid", "non-Path")
        with tempfile.TemporaryDirectory(prefix="memory-os-objective-json-canary-") as outside:
            canary = Path(outside) / "canary.json"
            canary.write_bytes(positive)
            escaped = Path(directory) / "escaped.json"
            escaped.symlink_to(canary)
            rejected(escaped, "recovery objective JSON path missing or outside repository", "external symlink")
            require(canary.read_bytes() == positive, "recovery objective JSON modified external canary")
        require(path.read_bytes() == positive, "recovery objective JSON mutated positive fixture")
    require((validator.CONTRACT.read_bytes(), validator.REGISTRY.read_bytes()) == before, "recovery objective JSON mutated protected authorities")
    print("PASS: actual recovery objective JSON reader positive and 16 fail-closed negatives")


def prove_negative_subprocess_redaction(validator) -> None:
    """Prove failure classes remain fixed without exposing private subprocess output."""
    original_run = validator.subprocess.run
    calls = []
    marker = "synthetic-secret-in-private-negative-log"

    def make_runner(exit_code: int):
        def fake_run(argv, **kwargs):
            require(argv == [validator.sys.executable, str(validator.NEGATIVE)], "objective negative subprocess target drift")
            require(kwargs.get("cwd") == validator.ROOT, "objective negative subprocess cwd drift")
            require(kwargs.get("stdout") == validator.subprocess.DEVNULL
                    and kwargs.get("stderr") == validator.subprocess.DEVNULL,
                    "objective negative subprocess captured private output")
            require(kwargs.get("check") is False and kwargs.get("timeout") == 120,
                    "objective negative subprocess execution budget drift")
            calls.append(exit_code)
            return validator.subprocess.CompletedProcess(argv, exit_code, stdout=marker, stderr=marker)
        return fake_run

    try:
        validator.subprocess.run = make_runner(0)
        validator.run_negative()
        validator.subprocess.run = make_runner(1)
        try:
            validator.run_negative()
        except validator.Fail as exc:
            require(str(exc) == "recovery objective negative admission suite failed (raw output withheld)",
                    "objective negative failure disclosed private output or lost fixed class")
            require(marker not in str(exc), "objective negative failure disclosed private marker")
        else:
            raise Fail("objective negative subprocess failure was accepted")
        for exception in (OSError(marker), validator.subprocess.TimeoutExpired(cmd=["synthetic"], timeout=120)):
            def raise_failure(*_args, **_kwargs):
                raise exception
            validator.subprocess.run = raise_failure
            try:
                validator.run_negative()
            except validator.Fail as exc:
                require(str(exc) == "recovery objective negative admission unavailable or timed out (raw output withheld)",
                        "objective negative unavailable/timeout disclosed private output")
                require(marker not in str(exc), "objective negative exception disclosed private marker")
            else:
                raise Fail("objective negative subprocess unavailable/timeout accepted")
    finally:
        validator.subprocess.run = original_run
    require(calls == [0, 1], "objective negative subprocess positive/failure controls not executed")
    print("PASS: objective negative subprocess fail-closed redaction and bounded execution")


def main() -> int:
    require(WRITER.is_file() and VALIDATOR.is_file() and CONTRACT.is_file(), "recovery objective foundation missing")
    require(APPROVAL_FIXTURE_DIR.is_dir(), "typed objective approval fixtures missing")
    writer = load_writer()
    validator = load_module(VALIDATOR, "memory_os_recovery_objectives_validator_negative")
    prove_recovery_objective_json_reader(validator)
    prove_negative_subprocess_redaction(validator)

    canonical_lock = writer.LOCK
    writer.LOCK = ROOT / "contracts/operations/.backup-restore-generation-evidence.lock"
    try:
        expect_rejected(
            writer,
            "recovery objective runtime lock substitution",
            writer.require_canonical_runtime_authorities,
        )
    finally:
        writer.LOCK = canonical_lock

    canonical_validator_lock = validator.EXPECTED_LOCK
    validator.EXPECTED_LOCK = ROOT / "contracts/operations/.production-equivalent-environment-generation.lock"
    try:
        expect_validator_rejected(
            validator,
            "recovery objective validator append lock substitution",
            validator.enforce_runtime_authorities,
        )
    finally:
        validator.EXPECTED_LOCK = canonical_validator_lock
    validator.enforce_runtime_authorities()

    valid = base_record()
    writer.validate_record(valid)
    print("PASS accept: explicit typed reviewed recovery objective")
    exercise_registry_corruption(writer)

    real_root = writer.ROOT
    with tempfile.TemporaryDirectory(prefix="memory-os-objective-ref-root-") as root_tmp, tempfile.TemporaryDirectory(prefix="memory-os-objective-ref-external-") as external_tmp:
        root_path = Path(root_tmp)
        external_path = Path(external_tmp) / "external-owner.json"
        (root_path / "owner.json").write_text("{}\n", encoding="utf-8")
        external_path.write_text("{}\n", encoding="utf-8")
        writer.ROOT = root_path
        try:
            expect_rejected(writer, "absolute objective authority ref", lambda: writer.repo_ref(str((root_path / "owner.json").resolve()), "ownerRef"))
            expect_rejected(writer, "parent-traversal objective authority ref", lambda: writer.repo_ref("nested/../owner.json", "ownerRef"))
            escape_link = root_path / "escaped-owner.json"
            escape_link.symlink_to(external_path)
            expect_rejected(writer, "objective authority symlink escapes repository root", lambda: writer.repo_ref("escaped-owner.json", "ownerRef"))
            loop_link = root_path / "loop-owner.json"
            loop_link.symlink_to(loop_link.name)
            expect_rejected(writer, "objective authority symlink loop", lambda: writer.repo_ref("loop-owner.json", "ownerRef"))
        finally:
            writer.ROOT = real_root

    real_validator_root = validator.ROOT
    with tempfile.TemporaryDirectory(prefix="memory-os-objective-validator-root-") as root_tmp, tempfile.TemporaryDirectory(prefix="memory-os-objective-validator-external-") as external_tmp:
        root_path = Path(root_tmp)
        external_path = Path(external_tmp) / "external-authority.py"
        (root_path / "authority.py").write_text("# canonical\n", encoding="utf-8")
        external_path.write_text("# external\n", encoding="utf-8")
        validator.ROOT = root_path
        try:
            require(validator.repo_file("authority.py", "validator") == root_path / "authority.py", "canonical validator authority rejected")
            expect_validator_rejected(validator, "absolute validator authority ref", lambda: validator.repo_file(str((root_path / "authority.py").resolve()), "validator"))
            expect_validator_rejected(validator, "parent-traversal validator authority ref", lambda: validator.repo_file("nested/../authority.py", "validator"))
            escape_link = root_path / "escaped-authority.py"
            escape_link.symlink_to(external_path)
            expect_validator_rejected(validator, "validator authority symlink escapes repository root", lambda: validator.repo_file("escaped-authority.py", "validator"))
            loop_link = root_path / "loop-authority.py"
            loop_link.symlink_to(loop_link.name)
            expect_validator_rejected(validator, "validator authority symlink loop", lambda: validator.repo_file("loop-authority.py", "validator"))
        finally:
            validator.ROOT = real_validator_root

    arbitrary_repo_files = copy.deepcopy(valid)
    arbitrary_repo_files["approvalEvidenceRefs"] = ["SECURITY.md", "README.md"]
    expect_rejected(writer, "arbitrary repository files cannot satisfy objective approval", lambda: writer.validate_record(arbitrary_repo_files))

    objective_binding = copy.deepcopy(valid)
    objective_binding["objectiveId"] = "ro_negative_other_objective"
    expect_rejected(writer, "typed approval bound to different objectiveId", lambda: writer.validate_record(objective_binding))

    value_binding = copy.deepcopy(valid)
    value_binding["rpoSeconds"] = 61
    expect_rejected(writer, "typed approval bound to different RPO value", lambda: writer.validate_record(value_binding))

    rpo_zero = copy.deepcopy(valid)
    rpo_zero["rpoSeconds"] = 0
    expect_rejected(writer, "zero RPO", lambda: writer.validate_record(rpo_zero))

    rpo_boolean = copy.deepcopy(valid)
    rpo_boolean["rpoSeconds"] = True
    expect_rejected(writer, "boolean RPO", lambda: writer.validate_record(rpo_boolean))

    rto_negative = copy.deepcopy(valid)
    rto_negative["rtoSeconds"] = -1
    expect_rejected(writer, "negative RTO", lambda: writer.validate_record(rto_negative))

    rto_boolean = copy.deepcopy(valid)
    rto_boolean["rtoSeconds"] = True
    expect_rejected(writer, "boolean RTO", lambda: writer.validate_record(rto_boolean))

    skew_negative = copy.deepcopy(valid)
    skew_negative["maximumObjectDatabaseSkewSeconds"] = -1
    expect_rejected(writer, "negative object-database skew", lambda: writer.validate_record(skew_negative))

    skew_boolean = copy.deepcopy(valid)
    skew_boolean["maximumObjectDatabaseSkewSeconds"] = False
    expect_rejected(writer, "boolean object-database skew", lambda: writer.validate_record(skew_boolean))

    placeholder = copy.deepcopy(valid)
    placeholder["rpoMeasurementMethod"] = "TBD"
    expect_rejected(writer, "placeholder measurement method", lambda: writer.validate_record(placeholder))

    missing_owner = copy.deepcopy(valid)
    missing_owner["ownerRef"] = "docs/evidence/does-not-exist-owner.json"
    expect_rejected(writer, "missing owner evidence path", lambda: writer.validate_record(missing_owner))

    reused_owner = copy.deepcopy(valid)
    reused_owner["ownerRef"] = reused_owner["approvalEvidenceRefs"][0]
    expect_rejected(writer, "owner reused as independent approval evidence", lambda: writer.validate_record(reused_owner))

    duplicate_approval = copy.deepcopy(valid)
    duplicate_approval["approvalEvidenceRefs"] = [
        f"{APPROVAL_FIXTURE_REF}/recovery-owner.valid.json",
        f"{APPROVAL_FIXTURE_REF}/recovery-owner.valid.json",
    ]
    expect_rejected(writer, "duplicate approval evidence refs", lambda: writer.validate_record(duplicate_approval))

    missing_approval = copy.deepcopy(valid)
    missing_approval["approvalEvidenceRefs"] = [
        f"{APPROVAL_FIXTURE_REF}/recovery-owner.valid.json",
        f"{APPROVAL_FIXTURE_REF}/does-not-exist-approval.json",
    ]
    expect_rejected(writer, "missing approval evidence path", lambda: writer.validate_record(missing_approval))

    malformed_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", prefix="malformed-objective-approval-", suffix=".json", dir=APPROVAL_FIXTURE_DIR, delete=False, encoding="utf-8") as handle:
            handle.write("{not-json\n")
            malformed_path = Path(handle.name)
        malformed_approval = copy.deepcopy(valid)
        malformed_approval["approvalEvidenceRefs"] = [
            f"{APPROVAL_FIXTURE_REF}/recovery-owner.valid.json",
            malformed_path.relative_to(ROOT).as_posix(),
        ]
        expect_rejected(writer, "malformed typed approval authority JSON", lambda: writer.validate_record(malformed_approval))
    finally:
        if malformed_path is not None:
            malformed_path.unlink(missing_ok=True)

    invalid_utf8_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", prefix="invalid-utf8-objective-approval-", suffix=".json", dir=APPROVAL_FIXTURE_DIR, delete=False) as handle:
            handle.write(b"{\xff}\n")
            invalid_utf8_path = Path(handle.name)
        invalid_utf8_approval = copy.deepcopy(valid)
        invalid_utf8_approval["approvalEvidenceRefs"] = [
            f"{APPROVAL_FIXTURE_REF}/recovery-owner.valid.json",
            invalid_utf8_path.relative_to(ROOT).as_posix(),
        ]
        expect_rejected(writer, "invalid UTF-8 typed approval authority", lambda: writer.validate_record(invalid_utf8_approval))
    finally:
        if invalid_utf8_path is not None:
            invalid_utf8_path.unlink(missing_ok=True)

    reviewer_alias_path: Path | None = None
    try:
        reviewer_alias_document = {
            "schemaVersion": "memory-os-recovery-objectives-approval.v1",
            "objectiveId": "ro_negative_base",
            "reviewRole": "OPERABILITY",
            "decision": "APPROVED",
            "scope": "PRODUCTION_RECOVERY_OBJECTIVES",
            "rpoSeconds": 60,
            "rtoSeconds": 120,
            "maximumObjectDatabaseSkewSeconds": 10,
            "reviewedAt": "2026-08-08T00:00:00Z",
            "reviewerPseudonym": " fixture_recovery_owner ",
            "productionTraffic": False,
            "productionCredentials": False,
            "automaticPromotion": False,
        }
        with tempfile.NamedTemporaryFile(mode="w", prefix="aliased-objective-reviewer-", suffix=".json", dir=APPROVAL_FIXTURE_DIR, delete=False, encoding="utf-8") as handle:
            json.dump(reviewer_alias_document, handle, indent=2)
            handle.write("\n")
            reviewer_alias_path = Path(handle.name)
        reviewer_alias = copy.deepcopy(valid)
        reviewer_alias["approvalEvidenceRefs"] = [
            f"{APPROVAL_FIXTURE_REF}/recovery-owner.valid.json",
            reviewer_alias_path.relative_to(ROOT).as_posix(),
        ]
        expect_rejected(writer, "whitespace-aliased reviewer pseudonym", lambda: writer.validate_record(reviewer_alias))
    finally:
        if reviewer_alias_path is not None:
            reviewer_alias_path.unlink(missing_ok=True)

    non_utc = copy.deepcopy(valid)
    non_utc["approvedAt"] = "2026-08-08T09:00:00+09:00"
    expect_rejected(writer, "approvedAt without UTC Z", lambda: writer.validate_record(non_utc))

    mutable_alias = copy.deepcopy(valid)
    mutable_alias["rtoMeasurementMethod"] = "measure against latest recovery result"
    expect_rejected(writer, "mutable latest alias", lambda: writer.validate_record(mutable_alias))

    production_flag = copy.deepcopy(valid)
    production_flag["productionEvidence"] = True
    expect_rejected(writer, "production evidence relabel", lambda: writer.validate_record(production_flag))

    print("Memory OS recovery objectives negative admission suite PASS")
    print("canonical registry mutated: false")
    print("objective registry append corruption rejection: enforced")
    print("runtime lock substitution accepted: false")
    print("validator append lock substitution accepted: false")
    print("objective values invented/defaulted: false")
    print("arbitrary repository file approval accepted: false")
    print("objective authority refs escape repository: false")
    print("objective authority ref symlink loops accepted: false")
    print("validator contract refs escape repository: false")
    print("validator contract ref symlink loops accepted: false")
    print("malformed typed approval authority accepted: false")
    print("invalid UTF-8 typed approval authority accepted: false")
    print("whitespace-aliased reviewer identity accepted: false")
    print("typed approval objective/value binding enforced: true")
    print("unexpected implementation exceptions accepted as rejection: false")
    print("boolean objective values accepted: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RECOVERY OBJECTIVES NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
