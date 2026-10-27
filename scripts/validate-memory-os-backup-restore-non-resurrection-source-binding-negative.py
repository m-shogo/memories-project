#!/usr/bin/env python3
"""Reject typed non-resurrection evidence created after its claimed source commit."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
WORKFLOW = ROOT / ".github/workflows/backup-restore-non-resurrection-admission.yml"
POST_SOURCE_REF = "docs/evidence/backup-restore/non-resurrection/source-binding-negative.json"
POST_SOURCE_PATH = ROOT / POST_SOURCE_REF


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_fixture_vacant(path: Path) -> None:
    require(not path.exists() and not path.is_symlink(),
            f"source-binding negative fixture already occupied: {path}")


def require_fixture_parent_canonical(parent: Path, root: Path = ROOT) -> tuple[int, int]:
    try:
        relative = parent.relative_to(root)
    except ValueError as exc:
        raise Fail("source-binding negative fixture parent escapes canonical root") from exc
    require(root.is_dir() and not root.is_symlink(),
            "source-binding negative fixture root missing or symlinked")
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        require(cursor.is_dir() and not cursor.is_symlink(),
                "source-binding negative fixture parent missing or symlinked")
    require(parent.resolve(strict=True) == root.resolve(strict=True) / relative,
            "source-binding negative fixture parent canonical resolution drift")
    stat = parent.stat()
    return stat.st_dev, stat.st_ino


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_non_resurrection_source_binding_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load typed non-resurrection writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(writer, source_commit: str, ref: str, field: str) -> None:
    try:
        writer.require_ref_bound_to_source(source_commit, ref, field)
    except writer.Fail as exc:
        require(str(exc) == f"{field} evidence missing from sourceCommitSha",
                f"{field} rejected at wrong source-binding authority: {exc}")
        print(f"PASS reject: {field}")
        return
    raise Fail(f"post-source evidence unexpectedly accepted: {field}")


def prove_bounded_source_binding(writer, source_commit: str) -> None:
    """Exercise real immutable-source binding with private synthetic Git faults."""
    field = "bounded typed source"
    original_run = writer.subprocess.run
    original_payload = POST_SOURCE_PATH.read_bytes()
    private_marker = "PRIVATE_TYPED_GIT_SOURCE_CANARY"
    try:
        POST_SOURCE_PATH.write_bytes(b"x" * (writer.MAX_SOURCE_BYTES + 1))
        try:
            writer.require_ref_bound_to_source(source_commit, POST_SOURCE_REF, field)
        except writer.Fail as exc:
            require(str(exc) == f"{field} source file size limit exceeded",
                    "oversized local typed source rejected at wrong boundary")
        else:
            raise Fail("oversized local typed source unexpectedly accepted")
        POST_SOURCE_PATH.write_bytes(original_payload)

        def fake_git(args, **kwargs):
            require(kwargs.get("cwd") == ROOT
                    and kwargs.get("stdout") == subprocess.PIPE
                    and kwargs.get("stderr") == subprocess.DEVNULL
                    and kwargs.get("timeout") == writer.SOURCE_GIT_TIMEOUT
                    and kwargs.get("check") is False,
                    "typed source Git privacy/timeout drift")
            require(args[:2] == ["git", "cat-file"] or args[:2] == ["git", "show"],
                    "typed source Git command drift")
            if fake_git.mode == "timeout":
                raise subprocess.TimeoutExpired(args, writer.SOURCE_GIT_TIMEOUT,
                                                output=private_marker.encode())
            if fake_git.mode == "oserror":
                raise OSError(private_marker)
            if fake_git.mode == "oversize":
                return subprocess.CompletedProcess(args, 0,
                                                   stdout=str(writer.MAX_SOURCE_BYTES + 1).encode() + b"\n")
            if fake_git.mode == "nonnumeric":
                return subprocess.CompletedProcess(args, 0, stdout=b"not-a-size\n")
            if args[1] == "cat-file":
                return subprocess.CompletedProcess(args, 0, stdout=b"3\n")
            return subprocess.CompletedProcess(args, 0, stdout=b"bad")

        for mode, expected in (
            ("timeout", f"{field} evidence missing from sourceCommitSha"),
            ("oserror", f"{field} evidence missing from sourceCommitSha"),
            ("oversize", f"{field} source blob size limit exceeded"),
            ("nonnumeric", f"{field} source blob size invalid"),
            ("mismatch", f"{field} evidence changed since sourceCommitSha"),
        ):
            fake_git.mode = mode
            writer.subprocess.run = fake_git
            try:
                writer.require_ref_bound_to_source(source_commit, POST_SOURCE_REF, field)
            except writer.Fail as exc:
                require(str(exc) == expected, f"{mode}: typed Git source failure class drift")
                require(private_marker not in str(exc), f"{mode}: private Git output disclosed")
            else:
                raise Fail(f"{mode}: unsafe typed source binding accepted")
    finally:
        writer.subprocess.run = original_run
        POST_SOURCE_PATH.write_bytes(original_payload)
    require(POST_SOURCE_PATH.read_bytes() == original_payload,
            "typed source binding negative changed its owned fixture")
    print("PASS reject: typed source Git timeout, oversized blobs, invalid sizes and private errors")


def validate_atomic_diagnostic_publication() -> None:
    require(WORKFLOW.is_file(), "typed admission workflow missing")
    text = WORKFLOW.read_text(encoding="utf-8")
    required = (
        "tempfile.mkstemp(",
        "dir=path.parent",
        "handle.flush()",
        "os.fsync(handle.fileno())",
        "os.replace(tmp_name, path)",
        "os.unlink(tmp_name)",
    )
    missing = [fragment for fragment in required if fragment not in text]
    require(not missing, f"typed admission diagnostic publication is not crash-safe: missing {missing}")
    require(
        "path.write_text(json.dumps(value" not in text,
        "typed admission diagnostic publication regressed to direct write_text",
    )


def validate_historical_generation_delegation(writer) -> None:
    """Pin canonical typed admission to historical generation row semantics without file writes."""
    canonical_registry = writer.CANONICAL_GEN_EVIDENCE_REGISTRY
    original_load = writer.load
    original_generation_loader = writer.load_generation_writer
    sentinel_row = {"evidenceId": "brge_history_sentinel"}
    sentinel_registry = {
        "schemaVersion": "memory-os-backup-restore-generation-evidence-registry.v1",
        "appendOnly": True,
        "registeredEvidenceCount": 1,
        "drillRequestBoundEvidenceCount": 1,
        "completeGenerationBoundBackupCount": 0,
        "completeGenerationBoundRestoreCount": 0,
        "productionEquivalentRecoveryCandidateCount": 0,
        "records": [sentinel_row],
        "productionEvidence": False,
        "productionReady": False,
    }

    class SentinelGenerationWriter:
        @staticmethod
        def validate_upstream_authorities_for_append() -> None:
            return None

        @staticmethod
        def validate_record(record, *, require_current_drill_request: bool = True) -> None:
            require(record is sentinel_row, "sentinel generation row identity drift")
            require(require_current_drill_request is False, "typed admission must validate generation history without current-request promotion")
            raise writer.Fail("sentinel historical generation semantic drift")

    def fake_load(path: Path):
        if path == canonical_registry:
            return sentinel_registry
        return original_load(path)

    try:
        writer.GEN_EVIDENCE_REGISTRY = canonical_registry
        writer.load = fake_load
        writer.load_generation_writer = lambda: SentinelGenerationWriter
        try:
            writer.generation_registry_rows()
        except writer.Fail as exc:
            require("historical authority invalid" in str(exc), "historical generation semantic failure was not preserved")
            require("sentinel historical generation semantic drift" in str(exc), "historical generation validator sentinel was not propagated")
            print("PASS reject: typed admission historical generation semantic drift")
        else:
            raise Fail("typed admission skipped historical generation row validation")
    finally:
        writer.GEN_EVIDENCE_REGISTRY = canonical_registry
        writer.load = original_load
        writer.load_generation_writer = original_generation_loader


def main() -> int:
    writer = load_writer()
    source_commit = git("rev-parse", "HEAD")
    writer_ref = WRITER.relative_to(ROOT).as_posix()

    writer.require_ref_bound_to_source(source_commit, writer_ref, "tracked control evidence")
    print("PASS accept: tracked control evidence exists unchanged at sourceCommitSha")

    # The negative fixture may not create repository directories or replace evidence.
    with tempfile.TemporaryDirectory(prefix="source-binding-ownership-") as temp_root:
        isolated = Path(temp_root)
        occupied = isolated / "occupied.json"
        occupied.write_bytes(b"sentinel")
        try:
            require_fixture_vacant(occupied)
        except Fail as exc:
            require(str(exc) == f"source-binding negative fixture already occupied: {occupied}",
                    "occupied source-binding fixture rejection diagnostic drift")
            require(occupied.read_bytes() == b"sentinel",
                    "occupied source-binding fixture was modified")
        else:
            raise Fail("occupied source-binding fixture unexpectedly accepted")
        dangling = isolated / "dangling"
        dangling.symlink_to(isolated / "missing")
        try:
            try:
                require_fixture_vacant(dangling)
            except Fail as exc:
                require(str(exc) == f"source-binding negative fixture already occupied: {dangling}",
                        "dangling source-binding fixture rejection diagnostic drift")
                require(dangling.is_symlink(), "dangling source-binding fixture was modified")
            else:
                raise Fail("dangling source-binding fixture unexpectedly accepted")
        finally:
            dangling.unlink()

        isolated_parent = isolated / "evidence"
        isolated_parent.mkdir()
        require_fixture_parent_canonical(isolated_parent, isolated)
        for unsafe_parent, expected in (
            (isolated / "missing-parent", "source-binding negative fixture parent missing or symlinked"),
            (ROOT, "source-binding negative fixture parent escapes canonical root"),
        ):
            try:
                require_fixture_parent_canonical(unsafe_parent, isolated)
            except Fail as exc:
                require(str(exc) == expected,
                        "source-binding fixture parent rejection diagnostic drift")
            else:
                raise Fail("unsafe source-binding fixture parent unexpectedly accepted")

    parent_identity = require_fixture_parent_canonical(POST_SOURCE_PATH.parent)
    require_fixture_vacant(POST_SOURCE_PATH)
    fd = os.open(POST_SOURCE_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    created_stat = os.fstat(fd)
    created_identity = (created_stat.st_dev, created_stat.st_ino)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as owned:
            owned.write("{}\n")
        expect_rejected(writer, source_commit, POST_SOURCE_REF, "post-source typed evidence")
        prove_bounded_source_binding(writer, source_commit)
    finally:
        require(require_fixture_parent_canonical(POST_SOURCE_PATH.parent) == parent_identity,
                "source-binding fixture parent inode drift before cleanup")
        current = POST_SOURCE_PATH.lstat()
        require((current.st_dev, current.st_ino) == created_identity
                and POST_SOURCE_PATH.is_file() and not POST_SOURCE_PATH.is_symlink(),
                "source-binding fixture file inode drift before cleanup")
        POST_SOURCE_PATH.unlink()

    validate_historical_generation_delegation(writer)
    validate_atomic_diagnostic_publication()

    print("Memory OS backup/restore non-resurrection source-binding negative suite PASS")
    print("post-source typed evidence accepted: false")
    print("historical generation semantic validation delegated: true")
    print("crash-safe typed-admission failure diagnostic required: true")
    print("canonical registries mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE NON-RESURRECTION SOURCE-BINDING NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
