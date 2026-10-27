#!/usr/bin/env python3
"""Prove admitted drill approvals stay byte-bound to append-only planning authority."""

from __future__ import annotations

import copy
import importlib.util
import os
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
FIXTURE_ROOT = ROOT / "docs/fixtures/memory-os-operability"
DRILL_REQUEST_LOAD_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-drill-request-load-negative.py"


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


def guarded_temporary_directory(prefix: str, parent: Path):
    require(DRILL_REQUEST_LOAD_NEGATIVE.is_file() and not DRILL_REQUEST_LOAD_NEGATIVE.is_symlink(),
            "drill request fixture parent guard source missing or symlinked")
    spec = importlib.util.spec_from_file_location(
        "memory_os_drill_fixture_guard_digest", DRILL_REQUEST_LOAD_NEGATIVE)
    require(spec is not None and spec.loader is not None,
            "drill request fixture parent guard cannot load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(callable(getattr(module, "guarded_temporary_directory", None)),
            "drill request fixture parent guard callable missing")
    try:
        return module.guarded_temporary_directory(prefix, parent)
    except module.Fail as exc:
        raise Fail(str(exc)) from exc


def expect_rejected(writer: Any, name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except writer.Fail:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")


def main() -> int:
    require(FIXTURE_ROOT.is_dir(), "drill approval digest fixture parent missing")
    with guarded_temporary_directory(".tmp-drill-digest-parent-negative-", FIXTURE_ROOT) as raw:
        sandbox = Path(raw)
        link = sandbox / "redirect"
        link.symlink_to(sandbox, target_is_directory=True)
        before = sorted(p.name for p in sandbox.iterdir())
        try:
            with guarded_temporary_directory(".tmp-must-not-create-", link):
                raise Fail("drill digest symlinked temp parent accepted")
        except Fail as exc:
            require(str(exc) == "drill request temp ancestor missing or symlinked",
                    f"drill digest temp parent rejected at wrong boundary: {exc}")
        else:
            raise Fail("drill digest symlinked temp parent accepted")
        require(sorted(p.name for p in sandbox.iterdir()) == before,
                "drill digest symlinked temp parent published a child")
    print("PASS: drill approval digest fixture reuses checked parent guard")
    writer = load_writer()
    original_validate = writer.validate_request
    original_executable = writer.request_currently_executable
    writer.validate_request = lambda record, require_current=False: None
    writer.request_currently_executable = lambda record: False

    try:
        with guarded_temporary_directory("drill-approval-digest-", FIXTURE_ROOT) as temp_dir:
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
            first_approval = ROOT / next(iter(refs.values()))
            original_approval = first_approval.read_bytes()
            oversized = temp / "oversized.json"
            oversized.write_bytes(b"x" * (writer.MAX_APPROVAL_DIGEST_BYTES + 1))
            alias = temp / "alias.json"
            alias.symlink_to(first_approval)
            directory = temp / "directory"
            directory.mkdir()
            fifo = temp / "fifo.json"
            os.mkfifo(fifo)
            for label, candidate in (
                ("oversized approval", oversized),
                ("symlink approval", alias),
                ("directory approval", directory),
                ("fifo approval", fifo),
            ):
                ref = candidate.relative_to(ROOT).as_posix()
                expect_rejected(writer, label, lambda ref=ref: writer.approval_sha256(ref))
            require(first_approval.read_bytes() == original_approval and alias.is_symlink(),
                    "unsafe drill approval digest changed canonical canary or symlink")
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
