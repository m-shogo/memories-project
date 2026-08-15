#!/usr/bin/env python3
"""Prove admitted drill approvals stay byte-bound to append-only planning authority."""

from __future__ import annotations

import copy
import importlib.util
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
FIXTURE_ROOT = ROOT / "docs/fixtures/memory-os-operability"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_restore_drill_digest_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load drill request writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(writer: Any, name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except writer.Fail:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")


def main() -> int:
    writer = load_writer()
    original_validate = writer.validate_request
    original_executable = writer.request_currently_executable
    writer.validate_request = lambda record, require_current=False: None
    writer.request_currently_executable = lambda record: False

    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="drill-approval-digest-", dir=FIXTURE_ROOT) as temp_dir:
            temp = Path(temp_dir)
            refs: dict[str, str] = {}
            for key in writer.APPROVAL_ROLES:
                path = temp / f"{key}.json"
                path.write_text(f'{{"fixture":"{key}"}}\n', encoding="utf-8")
                refs[key] = path.relative_to(ROOT).as_posix()

            request_id = "brrq_digest_negative"
            row = {
                "requestId": request_id,
                "sourceEnvironmentGenerationId": "pegen_digest_source",
                "restoreTargetEnvironmentGenerationId": "pegen_digest_target",
                "recoveryObjectivesId": "ro_digest_objective",
                "approvalRefs": refs,
            }
            digests = {ref: writer.approval_sha256(ref) for ref in refs.values()}
            baseline = {
                "schemaVersion": "memory-os-backup-restore-drill-request-registry.v1",
                "registryClass": "PRODUCTION_EQUIVALENT_BACKUP_RESTORE_DRILL_REQUESTS",
                "appendOnly": True,
                "registeredRequestCount": 1,
                "currentExecutableRequestCount": 0,
                "requests": [row],
                "approvalEvidenceDigestsByRequestId": {request_id: digests},
                "productionEvidence": False,
                "productionReady": False,
                "limitations": ["synthetic drill approval digest fixture only"],
            }
            writer.validate_registry_for_append(copy.deepcopy(baseline))
            print("PASS accept: exact drill approval bytes match append-only digest authority")

            missing = copy.deepcopy(baseline)
            missing.pop("approvalEvidenceDigestsByRequestId")
            expect_rejected(writer, "missing drill approval digest map", lambda: writer.validate_registry_for_append(missing))

            unknown = copy.deepcopy(baseline)
            unknown["approvalEvidenceDigestsByRequestId"]["brrq_unknown_digest"] = dict(digests)
            expect_rejected(writer, "unknown request in drill approval digest map", lambda: writer.validate_registry_for_append(unknown))

            stale = copy.deepcopy(baseline)
            first_ref = next(iter(digests))
            stale["approvalEvidenceDigestsByRequestId"][request_id][first_ref] = "0" * 64
            expect_rejected(writer, "stale drill approval digest", lambda: writer.validate_registry_for_append(stale))

            approval_path = ROOT / first_ref
            original_bytes = approval_path.read_bytes()
            try:
                approval_path.write_bytes(original_bytes + b" ")
                expect_rejected(writer, "drill approval bytes changed after registration", lambda: writer.validate_registry_for_append(copy.deepcopy(baseline)))
            finally:
                approval_path.write_bytes(original_bytes)

            writer.validate_registry_for_append(copy.deepcopy(baseline))
            print("PASS restore: drill approval fixture restored byte-for-byte")
    finally:
        writer.validate_request = original_validate
        writer.request_currently_executable = original_executable

    print("canonical drill request registry mutated: false")
    print("planning request created: false")
    print("production evidence: false")
    print("production readiness: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DRILL REQUEST DIGEST NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
