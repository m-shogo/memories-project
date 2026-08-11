#!/usr/bin/env python3
"""Prove drill-request authority loading fails closed on unreadable or escaped inputs."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-request.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-request.py"
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


def exercise(label: str, module, tmp: Path, outside: Path) -> None:
    invalid_utf8 = tmp / f"{label}-invalid-utf8.json"
    invalid_utf8.write_bytes(b"{\xff}")
    expect_domain_fail(f"{label} invalid UTF-8 authority JSON", lambda: module.load(invalid_utf8), module.Fail)

    directory_authority = tmp / f"{label}-directory-authority.json"
    directory_authority.mkdir()
    expect_domain_fail(f"{label} authority path is unreadable directory", lambda: module.load(directory_authority), module.Fail)

    expect_domain_fail(f"{label} authority path escapes repository", lambda: module.load(outside), module.Fail)


def main() -> int:
    require(WRITER.is_file(), "drill-request writer missing")
    require(VALIDATOR.is_file(), "drill-request validator missing")
    require(RECONCILER.is_file(), "drill-request reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    writer = load_module(WRITER, "memory_os_restore_drill_request_writer_load_negative")
    validator = load_module(VALIDATOR, "memory_os_restore_drill_request_load_negative")
    reconciler = load_module(RECONCILER, "memory_os_restore_drill_request_reconcile_load_negative")
    require(writer.canonical_repo_file(writer.ELIGIBILITY_HELPER, "environment generation eligibility helper") == writer.ELIGIBILITY_HELPER, "canonical eligibility helper rejected")

    with tempfile.TemporaryDirectory(prefix=".tmp-drill-request-load-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        with tempfile.TemporaryDirectory(prefix="memory-os-drill-request-outside-") as outside_dirname:
            outside_dir = Path(outside_dirname)
            outside = outside_dir / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            exercise("validator", validator, tmp, outside)
            exercise("reconciler", reconciler, tmp, outside)

            outside_helper = outside_dir / "outside-eligibility-helper.py"
            outside_helper.write_text("VALUE = 1\n", encoding="utf-8")
            escaped_link = tmp / "escaped-eligibility-helper.py"
            escaped_link.symlink_to(outside_helper)
            original_helper = writer.ELIGIBILITY_HELPER
            try:
                writer.ELIGIBILITY_HELPER = outside_helper
                expect_domain_fail("eligibility helper absolute path escapes repository", writer.load_eligibility_helper, writer.Fail)
                writer.ELIGIBILITY_HELPER = escaped_link
                expect_domain_fail("eligibility helper repository symlink escapes repository", writer.load_eligibility_helper, writer.Fail)
            finally:
                writer.ELIGIBILITY_HELPER = original_helper

    print("Drill-request unreadable/escaped-authority negative suite PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DRILL REQUEST LOAD NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
