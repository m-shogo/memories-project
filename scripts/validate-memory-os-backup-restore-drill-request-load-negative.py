#!/usr/bin/env python3
"""Prove drill-request authority loading fails closed on unreadable or escaped inputs."""

from __future__ import annotations

import copy
import importlib.util
import os
import secrets
import shutil
import stat
import tempfile
from contextlib import contextmanager
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


@contextmanager
def guarded_temporary_directory(prefix: str, parent: Path):
    # Pin every ancestor by descriptor: the checked pathname may be swapped
    # before mkdir, but the new child must stay beneath the opened directory.
    try:
        relative = parent.relative_to(ROOT)
    except ValueError as exc:
        raise Fail("drill request temp parent escapes repository") from exc
    require(ROOT.is_dir() and not ROOT.is_symlink(),
            "drill request repository root missing or symlinked")
    require(
        hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY")
        and shutil.rmtree.avoids_symlink_attacks,
        "drill request pinned fixture directory unsupported",
    )
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        fd = os.open(ROOT, flags)
    except OSError as exc:
        raise Fail(f"drill request cannot pin repository root: {exc}") from exc
    try:
        root_entry = ROOT.lstat()
        root_open = os.fstat(fd)
        require(
            stat.S_ISDIR(root_entry.st_mode)
            and (root_entry.st_dev, root_entry.st_ino) == (root_open.st_dev, root_open.st_ino),
            "drill request repository root identity drift",
        )
        cursor = ROOT
        for part in relative.parts:
            cursor = cursor / part
            require(cursor.is_dir() and not cursor.is_symlink(),
                    "drill request temp ancestor missing or symlinked")
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
            entry = cursor.lstat()
            opened = os.fstat(fd)
            require(
                stat.S_ISDIR(entry.st_mode)
                and (entry.st_dev, entry.st_ino) == (opened.st_dev, opened.st_ino),
                "drill request temp ancestor identity drift",
            )
        require(
            parent.resolve(strict=True) == ROOT.resolve(strict=True) / relative,
            "drill request temp parent canonical resolution drift",
        )
        pinned = os.fstat(fd)
        for _ in range(8):
            name = prefix + secrets.token_hex(8)
            try:
                os.mkdir(name, mode=0o700, dir_fd=fd)
            except FileExistsError:
                continue
            break
        else:
            raise Fail("drill request temp child exclusive creation exhausted")
        created = os.stat(name, dir_fd=fd, follow_symlinks=False)
        try:
            current = parent.lstat()
            require(
                stat.S_ISDIR(current.st_mode)
                and (current.st_dev, current.st_ino) == (pinned.st_dev, pinned.st_ino),
                "drill request temp parent identity drift after creation",
            )
            require(stat.S_ISDIR(created.st_mode),
                    "drill request temp child is not a directory")
            yield str(parent / name)
        finally:
            current_child = os.stat(name, dir_fd=fd, follow_symlinks=False)
            require(
                stat.S_ISDIR(current_child.st_mode)
                and (current_child.st_dev, current_child.st_ino) == (created.st_dev, created.st_ino),
                "drill request temp child identity drift before cleanup",
            )
            # Descriptor-relative, symlink-resistant cleanup cannot traverse a
            # substituted parent pathname. Child inode drift fails closed.
            shutil.rmtree(name, dir_fd=fd)
    except OSError as exc:
        raise Fail(f"drill request pinned fixture operation failed: {exc}") from exc
    finally:
        os.close(fd)


def prove_parent_swap_during_mkdir_rejected() -> None:
    # Deterministically substitute only an exclusively owned sandbox parent
    # after descriptor pinning and before the actual mkdir operation.
    with guarded_temporary_directory(prefix=".tmp-drill-request-race-control-", parent=TMP_PARENT) as raw:
        sandbox = Path(raw)
        checked = sandbox / "checked"
        escaped = sandbox / "escaped"
        parked = sandbox / "parked"
        checked.mkdir()
        escaped.mkdir()
        original_identity = (checked.stat().st_dev, checked.stat().st_ino)
        original_mkdir = os.mkdir
        switched = False

        def swap_before_mkdir(name: str, mode: int = 0o777, *, dir_fd: int | None = None) -> None:
            nonlocal switched
            if not switched and str(name).startswith(".tmp-drill-request-race-") and dir_fd is not None:
                switched = True
                checked.rename(parked)
                checked.symlink_to(escaped, target_is_directory=True)
            original_mkdir(name, mode=mode, dir_fd=dir_fd)

        os.mkdir = swap_before_mkdir
        try:
            try:
                with guarded_temporary_directory(prefix=".tmp-drill-request-race-", parent=checked):
                    raise Fail("drill request parent swap accepted")
            except Fail as exc:
                require(str(exc) == "drill request temp parent identity drift after creation",
                        f"drill request parent swap rejected at wrong boundary: {exc}")
            else:
                raise Fail("drill request parent swap accepted")
        finally:
            os.mkdir = original_mkdir

        require(switched, "drill request parent swap probe did not reach pinned mkdir")
        require(checked.is_symlink() and checked.resolve() == escaped.resolve(),
                "drill request parent swap did not install isolated redirect")
        require((parked.stat().st_dev, parked.stat().st_ino) == original_identity,
                "drill request parent swap changed pinned directory identity")
        require(not list(escaped.iterdir()), "drill request parent swap published through redirect")
        require(not list(parked.iterdir()), "drill request parent swap left pinned child")
        # The enclosing owned context removes all synthetic children; no
        # unconditional unlink or rename of mutable fixture paths is needed.
    print("PASS: drill request parent swap during mkdir stays pinned and fails closed")


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


def exercise_registry_corruption(writer) -> None:
    baseline = writer.load(writer.REGISTRY)
    writer.validate_registry_for_append(copy.deepcopy(baseline))
    cases = (
        ("registry schema drift", "schemaVersion", "memory-os-backup-restore-drill-request-registry.corrupt"),
        ("registry class drift", "registryClass", "CORRUPT"),
        ("append-only disabled", "appendOnly", False),
        ("production evidence forged", "productionEvidence", True),
        ("production ready forged", "productionReady", True),
        ("registered request count boolean", "registeredRequestCount", True),
        ("registered request count drift", "registeredRequestCount", baseline.get("registeredRequestCount", 0) + 1),
        ("current executable count boolean", "currentExecutableRequestCount", True),
        ("current executable count drift", "currentExecutableRequestCount", baseline.get("currentExecutableRequestCount", 0) + 1),
    )
    for name, field, value in cases:
        mutated = copy.deepcopy(baseline)
        mutated[field] = value
        expect_domain_fail(name, lambda mutated=mutated: writer.validate_registry_for_append(mutated), writer.Fail)


def exercise_validator_execution_transport(validator) -> None:
    original_subprocess_run = validator.subprocess.run
    original_spec_from_file_location = validator.importlib.util.spec_from_file_location
    original_module_from_spec = validator.importlib.util.module_from_spec
    original_guard = validator.enforce_execution_transport
    try:
        validator.subprocess.run = lambda *args, **kwargs: None
        expect_domain_fail("drill request subprocess transport substitution", validator.main, validator.Fail)
    finally:
        validator.subprocess.run = original_subprocess_run

    try:
        validator.importlib.util.spec_from_file_location = lambda *args, **kwargs: None
        expect_domain_fail("drill request import spec transport substitution", validator.main, validator.Fail)
    finally:
        validator.importlib.util.spec_from_file_location = original_spec_from_file_location

    try:
        validator.importlib.util.module_from_spec = lambda *args, **kwargs: None
        expect_domain_fail("drill request module loader transport substitution", validator.main, validator.Fail)
    finally:
        validator.importlib.util.module_from_spec = original_module_from_spec

    try:
        validator.enforce_execution_transport = lambda: None
        expect_domain_fail("drill request execution guard substitution", validator.main, validator.Fail)
    finally:
        validator.enforce_execution_transport = original_guard


def main() -> int:
    require(WRITER.is_file(), "drill-request writer missing")
    require(VALIDATOR.is_file(), "drill-request validator missing")
    require(RECONCILER.is_file(), "drill-request reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    prove_parent_swap_during_mkdir_rejected()
    writer = load_module(WRITER, "memory_os_restore_drill_request_writer_load_negative")
    validator = load_module(VALIDATOR, "memory_os_restore_drill_request_load_negative")
    reconciler = load_module(RECONCILER, "memory_os_restore_drill_request_reconcile_load_negative")
    require(writer.canonical_repo_file(writer.ELIGIBILITY_HELPER, "environment generation eligibility helper") == writer.ELIGIBILITY_HELPER, "canonical eligibility helper rejected")
    exercise_registry_corruption(writer)
    exercise_validator_execution_transport(validator)

    with guarded_temporary_directory(".tmp-drill-request-load-", TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        with tempfile.TemporaryDirectory(prefix="memory-os-drill-request-outside-") as outside_dirname:
            outside_dir = Path(outside_dirname)
            outside = outside_dir / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            exercise("validator", validator, tmp, outside)
            exercise("reconciler", reconciler, tmp, outside)

            ref_loop = tmp / "loop-authority-ref.json"
            ref_loop.symlink_to(ref_loop.name)
            ref_loop_relative = ref_loop.relative_to(ROOT).as_posix()
            expect_domain_fail(
                "drill request repository ref symlink loop",
                lambda: writer.repo_ref(ref_loop_relative, "negativeAuthorityRef"),
                writer.Fail,
            )

            outside_helper = outside_dir / "outside-eligibility-helper.py"
            outside_helper.write_text("VALUE = 1\n", encoding="utf-8")
            escaped_link = tmp / "escaped-eligibility-helper.py"
            escaped_link.symlink_to(outside_helper)
            loop_link = tmp / "loop-eligibility-helper.py"
            loop_link.symlink_to(loop_link.name)
            original_helper = writer.ELIGIBILITY_HELPER
            try:
                writer.ELIGIBILITY_HELPER = outside_helper
                expect_domain_fail("eligibility helper absolute path escapes repository", writer.load_eligibility_helper, writer.Fail)
                writer.ELIGIBILITY_HELPER = escaped_link
                expect_domain_fail("eligibility helper repository symlink escapes repository", writer.load_eligibility_helper, writer.Fail)
                writer.ELIGIBILITY_HELPER = loop_link
                expect_domain_fail("eligibility helper repository symlink loop", writer.load_eligibility_helper, writer.Fail)
            finally:
                writer.ELIGIBILITY_HELPER = original_helper

            outside_authority = outside_dir / "outside-runtime-authority.json"
            outside_authority.write_text("{}\n", encoding="utf-8")
            escaped_authority = tmp / "escaped-runtime-authority.json"
            escaped_authority.symlink_to(outside_authority)
            loop_authority = tmp / "loop-runtime-authority.json"
            loop_authority.symlink_to(loop_authority.name)
            for field in (
                "restore drill request contract",
                "restore drill request registry",
                "environment generation registry",
                "recovery objectives registry",
            ):
                expect_domain_fail(
                    f"{field} repository symlink escapes repository",
                    lambda field=field: writer.require_canonical_runtime_authority(escaped_authority, escaped_authority, field),
                    writer.Fail,
                )
                expect_domain_fail(
                    f"{field} repository symlink loop",
                    lambda field=field: writer.require_canonical_runtime_authority(loop_authority, loop_authority, field),
                    writer.Fail,
                )

    with guarded_temporary_directory(".tmp-drill-request-parent-negative-", TMP_PARENT) as raw:
        sandbox = Path(raw)
        link = sandbox / "redirect"
        link.symlink_to(sandbox, target_is_directory=True)
        before = sorted(p.name for p in sandbox.iterdir())
        try:
            with guarded_temporary_directory(".tmp-must-not-create-", link):
                raise Fail("drill request symlinked temp parent accepted")
        except Fail as exc:
            require(str(exc) == "drill request temp ancestor missing or symlinked",
                    f"drill request temp parent rejected at wrong boundary: {exc}")
        else:
            raise Fail("drill request symlinked temp parent accepted")
        require(sorted(p.name for p in sandbox.iterdir()) == before,
                "drill request symlinked temp parent published a child")
    print("PASS: drill request fixture temp symlink parent rejected before creation")

    print("Drill-request unreadable/escaped-authority negative suite PASS")
    print("drill-request append registry corruption rejection: enforced")
    print("canonical drill contract/registry/generation/objective containment: enforced")
    print("drill-request execution transport substitution accepted: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DRILL REQUEST LOAD NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
