#!/usr/bin/env python3
"""Prove generation-evidence authority loading fails closed on unreadable or escaped inputs."""

from __future__ import annotations

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

    expect_domain_fail(f"{label} authority path escapes repository", lambda: module.load(outside), module.Fail)


def exercise_writer_loads(writer, tmp: Path) -> None:
    invalid_utf8 = tmp / "writer-invalid-utf8.json"
    invalid_utf8.write_bytes(b"{\xff}")
    expect_domain_fail("writer invalid UTF-8 external record", lambda: writer.load(invalid_utf8), writer.Fail)

    directory_record = tmp / "writer-directory-record.json"
    directory_record.mkdir()
    expect_domain_fail("writer unreadable external record directory", lambda: writer.load(directory_record), writer.Fail)


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


def main() -> int:
    require(WRITER.is_file(), "generation evidence writer missing")
    require(VALIDATOR.is_file(), "generation evidence validator missing")
    require(RECONCILER.is_file(), "generation evidence reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    writer = load_module(WRITER, "memory_os_generation_evidence_writer_load_negative")
    validator = load_module(VALIDATOR, "memory_os_generation_evidence_validator_load_negative")
    reconciler = load_module(RECONCILER, "memory_os_generation_evidence_reconciler_load_negative")

    require(writer.canonical_repo_file(WRITER, "generation evidence writer") == WRITER, "canonical writer path rejected")

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
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION EVIDENCE LOAD NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
