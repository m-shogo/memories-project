#!/usr/bin/env python3
"""Prove generation-evidence authority loading and append admission fail closed."""

from __future__ import annotations

import copy
import importlib.util
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-generation-evidence.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_domain_fail(name: str, action: Callable[[], object], fail_type: type[BaseException]) -> None:
    try:
        action()
    except fail_type:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def exercise_loads(label: str, module, tmp: Path, outside: Path) -> None:
    invalid_utf8 = tmp / f"{label}-invalid-utf8.json"
    invalid_utf8.write_bytes(b"{\xff}")
    expect_domain_fail(f"{label} invalid UTF-8 authority JSON", lambda: module.load(invalid_utf8), module.Fail)

    directory_authority = tmp / f"{label}-directory-authority.json"
    directory_authority.mkdir()
    expect_domain_fail(f"{label} authority path is unreadable directory", lambda: module.load(directory_authority), module.Fail)

    loop_authority = tmp / f"{label}-loop-authority.json"
    loop_authority.symlink_to(loop_authority.name)
    expect_domain_fail(f"{label} authority symlink loop", lambda: module.load(loop_authority), module.Fail)

    expect_domain_fail(f"{label} authority path escapes repository", lambda: module.load(outside), module.Fail)


def exercise_writer_loads(writer, tmp: Path) -> None:
    invalid_utf8 = tmp / "writer-invalid-utf8.json"
    invalid_utf8.write_bytes(b"{\xff}")
    expect_domain_fail("writer invalid UTF-8 external record", lambda: writer.load(invalid_utf8), writer.Fail)

    directory_record = tmp / "writer-directory-record.json"
    directory_record.mkdir()
    expect_domain_fail("writer unreadable external record directory", lambda: writer.load(directory_record), writer.Fail)

    ref_loop = tmp / "loop-evidence-ref.json"
    ref_loop.symlink_to(ref_loop.name)
    ref_loop_relative = ref_loop.relative_to(ROOT).as_posix()
    expect_domain_fail(
        "generation evidence repository ref symlink loop",
        lambda: writer.repo_ref(ref_loop_relative, "negativeEvidenceRef"),
        writer.Fail,
    )


def exercise_writer_module_containment(writer, tmp: Path, outside_dir: Path) -> None:
    outside_module = outside_dir / "outside-writer.py"
    outside_module.write_text("VALUE = 1\n", encoding="utf-8")
    escaped_link = tmp / "escaped-writer.py"
    escaped_link.symlink_to(outside_module)
    loop_link = tmp / "loop-writer.py"
    loop_link.symlink_to(loop_link.name)

    original_drill_writer = writer.DRILL_REQUEST_WRITER
    original_non_resurrection_writer = writer.NON_RESURRECTION_WRITER
    try:
        writer.DRILL_REQUEST_WRITER = outside_module
        expect_domain_fail("drill writer absolute path escapes repository", writer.load_drill_writer, writer.Fail)
        writer.DRILL_REQUEST_WRITER = escaped_link
        expect_domain_fail("drill writer repository symlink escapes repository", writer.load_drill_writer, writer.Fail)
        writer.DRILL_REQUEST_WRITER = loop_link
        expect_domain_fail("drill writer repository symlink loop", writer.load_drill_writer, writer.Fail)

        writer.NON_RESURRECTION_WRITER = outside_module
        expect_domain_fail("typed writer absolute path escapes repository", writer.load_non_resurrection_writer, writer.Fail)
        writer.NON_RESURRECTION_WRITER = escaped_link
        expect_domain_fail("typed writer repository symlink escapes repository", writer.load_non_resurrection_writer, writer.Fail)
        writer.NON_RESURRECTION_WRITER = loop_link
        expect_domain_fail("typed writer repository symlink loop", writer.load_non_resurrection_writer, writer.Fail)
    finally:
        writer.DRILL_REQUEST_WRITER = original_drill_writer
        writer.NON_RESURRECTION_WRITER = original_non_resurrection_writer


def exercise_writer_registry_append_guard(writer) -> None:
    healthy = {
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
    require(writer.validate_registry_for_append(copy.deepcopy(healthy)) == [], "healthy empty generation registry append authority rejected")
    print("PASS accept: healthy empty generation registry append authority")

    def reject(name: str, mutate: Callable[[dict], None]) -> None:
        value = copy.deepcopy(healthy)
        mutate(value)
        expect_domain_fail(name, lambda: writer.validate_registry_for_append(value), writer.Fail)

    reject("generation writer registry schema drift before append", lambda value: value.update(schemaVersion="memory-os-backup-restore-generation-evidence-registry.v0"))
    reject("generation writer appendOnly disabled before append", lambda value: value.update(appendOnly=False))
    reject("generation writer registeredEvidenceCount drift before append", lambda value: value.update(registeredEvidenceCount=1))
    reject("generation writer boolean registeredEvidenceCount before append", lambda value: value.update(registeredEvidenceCount=True))
    reject("generation writer drillRequestBoundEvidenceCount drift before append", lambda value: value.update(drillRequestBoundEvidenceCount=1))
    reject("generation writer boolean backup count before append", lambda value: value.update(completeGenerationBoundBackupCount=True))
    reject("generation writer restore count drift before append", lambda value: value.update(completeGenerationBoundRestoreCount=1))
    reject("generation writer candidate count drift before append", lambda value: value.update(productionEquivalentRecoveryCandidateCount=1))
    reject("generation writer production evidence boundary drift before append", lambda value: value.update(productionEvidence=True))
    reject("generation writer production ready boundary drift before append", lambda value: value.update(productionReady=True))


def main() -> int:
    require(WRITER.is_file(), "generation evidence writer missing")
    require(VALIDATOR.is_file(), "generation evidence validator missing")
    require(RECONCILER.is_file(), "generation evidence reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    writer = load_module(WRITER, "memory_os_generation_evidence_writer_load_negative")
    validator = load_module(VALIDATOR, "memory_os_generation_evidence_validator_load_negative")
    reconciler = load_module(RECONCILER, "memory_os_generation_evidence_reconciler_load_negative")

    require(writer.canonical_repo_file(WRITER, "generation evidence writer") == WRITER, "canonical writer path rejected")
    require(callable(getattr(writer, "validate_registry_for_append", None)), "generation writer append authority guard missing")
    exercise_writer_registry_append_guard(writer)

    with tempfile.TemporaryDirectory(prefix=".tmp-generation-evidence-load-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        with tempfile.TemporaryDirectory(prefix="memory-os-generation-evidence-outside-") as outside_dirname:
            outside_dir = Path(outside_dirname)
            outside = outside_dir / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            exercise_writer_loads(writer, tmp)
            exercise_writer_module_containment(writer, tmp, outside_dir)
            exercise_loads("validator", validator, tmp, outside)
            exercise_loads("reconciler", reconciler, tmp, outside)

    print("Generation evidence unreadable/escaped-authority negative suite PASS")
    print("generation writer append authority drift accepted: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION EVIDENCE LOAD NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
