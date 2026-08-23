#!/usr/bin/env python3
"""Reject typed non-resurrection evidence created after its claimed source commit."""
from __future__ import annotations

import importlib.util
import subprocess
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
    except writer.Fail:
        print(f"PASS reject: {field}")
        return
    raise Fail(f"post-source evidence unexpectedly accepted: {field}")


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

    POST_SOURCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        POST_SOURCE_PATH.unlink(missing_ok=True)
        POST_SOURCE_PATH.write_text("{}\n", encoding="utf-8")
        expect_rejected(writer, source_commit, POST_SOURCE_REF, "post-source typed evidence")
    finally:
        POST_SOURCE_PATH.unlink(missing_ok=True)

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
