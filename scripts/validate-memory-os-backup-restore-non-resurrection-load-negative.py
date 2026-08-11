#!/usr/bin/env python3
"""Prove typed non-resurrection authority loading fails closed on unreadable or escaped inputs."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py"
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


def main() -> int:
    require(WRITER.is_file(), "typed evidence writer missing")
    require(VALIDATOR.is_file(), "typed admission validator missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    writer = load_module(WRITER, "memory_os_typed_non_resurrection_writer_load_negative")
    validator = load_module(VALIDATOR, "memory_os_typed_non_resurrection_load_negative")
    require(writer.canonical_repo_file(WRITER, "typed evidence writer") == WRITER, "canonical typed writer path rejected")

    with tempfile.TemporaryDirectory(prefix=".tmp-typed-load-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)

        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_domain_fail("invalid UTF-8 typed authority JSON", lambda: validator.load(invalid_utf8), validator.Fail)
        expect_domain_fail("invalid UTF-8 typed writer input", lambda: writer.load(invalid_utf8), writer.Fail)

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_domain_fail("typed authority path is unreadable directory", lambda: validator.load(directory_authority), validator.Fail)
        expect_domain_fail("typed writer input path is unreadable directory", lambda: writer.load(directory_authority), writer.Fail)

        with tempfile.TemporaryDirectory(prefix="memory-os-typed-writer-outside-") as outside_dirname:
            outside_dir = Path(outside_dirname)
            outside_writer = outside_dir / "outside-generation-writer.py"
            outside_writer.write_text("VALUE = 1\n", encoding="utf-8")
            escaped_link = tmp / "escaped-generation-writer.py"
            escaped_link.symlink_to(outside_writer)
            loop_link = tmp / "loop-generation-writer.py"
            loop_link.symlink_to(loop_link.name)

            original_generation_writer = writer.GEN_WRITER
            try:
                writer.GEN_WRITER = outside_writer
                expect_domain_fail("generation writer absolute path escapes repository", writer.load_generation_writer, writer.Fail)
                writer.GEN_WRITER = escaped_link
                expect_domain_fail("generation writer repository symlink escapes repository", writer.load_generation_writer, writer.Fail)
                writer.GEN_WRITER = loop_link
                expect_domain_fail("generation writer repository symlink loop", writer.load_generation_writer, writer.Fail)
            finally:
                writer.GEN_WRITER = original_generation_writer

    print("Typed unreadable/escaped-authority negative suite PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"TYPED LOAD NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
