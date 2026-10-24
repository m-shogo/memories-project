#!/usr/bin/env python3
"""Prove end-to-end admission-chain authority loading fails closed on unreadable repo-local inputs."""

from __future__ import annotations

import importlib.util
import os
import secrets
import shutil
import stat
import tempfile
import weakref
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-admission-chain.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


@contextmanager
def _pinned_temporary_directory(prefix: str, parent: Path):
    # Pin every ancestor by descriptor: the checked pathname may be swapped
    # before mkdir, but the new child must stay beneath the opened directory.
    try:
        relative = parent.relative_to(ROOT)
    except ValueError as exc:
        raise Fail("admission-chain load temp parent escapes repository") from exc
    require(ROOT.is_dir() and not ROOT.is_symlink(),
            "admission-chain load repository root missing or symlinked")
    require(
        hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY")
        and shutil.rmtree.avoids_symlink_attacks,
        "admission-chain load pinned fixture directory unsupported",
    )
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        fd = os.open(ROOT, flags)
    except OSError as exc:
        raise Fail(f"admission-chain load cannot pin repository root: {exc}") from exc
    try:
        root_entry = ROOT.lstat()
        root_open = os.fstat(fd)
        require(
            stat.S_ISDIR(root_entry.st_mode)
            and (root_entry.st_dev, root_entry.st_ino) == (root_open.st_dev, root_open.st_ino),
            "admission-chain load repository root identity drift",
        )
        cursor = ROOT
        for part in relative.parts:
            cursor = cursor / part
            require(cursor.is_dir() and not cursor.is_symlink(),
                    "admission-chain load temp ancestor missing or symlinked")
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
            entry = cursor.lstat()
            opened = os.fstat(fd)
            require(
                stat.S_ISDIR(entry.st_mode)
                and (entry.st_dev, entry.st_ino) == (opened.st_dev, opened.st_ino),
                "admission-chain load temp ancestor identity drift",
            )
        require(
            parent.resolve(strict=True) == ROOT.resolve(strict=True) / relative,
            "admission-chain load temp parent canonical resolution drift",
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
            raise Fail("admission-chain load temp child exclusive creation exhausted")
        created = os.stat(name, dir_fd=fd, follow_symlinks=False)
        try:
            current = parent.lstat()
            require(
                stat.S_ISDIR(current.st_mode)
                and (current.st_dev, current.st_ino) == (pinned.st_dev, pinned.st_ino),
                "admission-chain load temp parent identity drift after creation",
            )
            require(stat.S_ISDIR(created.st_mode),
                    "admission-chain load temp child is not a directory")
            yield str(parent / name)
        finally:
            current_child = os.stat(name, dir_fd=fd, follow_symlinks=False)
            require(
                stat.S_ISDIR(current_child.st_mode)
                and (current_child.st_dev, current_child.st_ino) == (created.st_dev, created.st_ino),
                "admission-chain load temp child identity drift before cleanup",
            )
            # Descriptor-relative, symlink-resistant cleanup cannot traverse a
            # substituted parent pathname. Child inode drift fails closed.
            shutil.rmtree(name, dir_fd=fd)
    except OSError as exc:
        raise Fail(f"admission-chain load pinned fixture operation failed: {exc}") from exc
    finally:
        os.close(fd)


class _EagerFixtureDirectory:
    """Retain TemporaryDirectory's call-time creation/error and cleanup contract."""

    def __init__(self, manager):
        self._manager = manager
        self.name = manager.__enter__()
        self._finalizer = weakref.finalize(self, manager.__exit__, None, None, None)

    def __enter__(self):
        require(self._finalizer.alive, "admission-chain load pinned fixture already closed")
        return self.name

    def __exit__(self, exc_type, exc, traceback):
        if self._finalizer.alive:
            self._finalizer.detach()
            return self._manager.__exit__(exc_type, exc, traceback)
        return False

    def cleanup(self):
        if self._finalizer.alive:
            self._finalizer()


def guarded_temporary_directory(prefix: str, parent: Path):
    # Dependent negative wrappers translate domain Fail at call time.
    return _EagerFixtureDirectory(_pinned_temporary_directory(prefix, parent))


def prove_parent_swap_during_mkdir_rejected() -> None:
    # Deterministically substitute only an exclusively owned sandbox parent
    # after descriptor pinning and before the actual mkdir operation.
    with guarded_temporary_directory(prefix=".tmp-admission-chain-race-control-", parent=TMP_PARENT) as raw:
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
            if not switched and str(name).startswith(".tmp-admission-chain-race-") and dir_fd is not None:
                switched = True
                checked.rename(parked)
                checked.symlink_to(escaped, target_is_directory=True)
            original_mkdir(name, mode=mode, dir_fd=dir_fd)

        os.mkdir = swap_before_mkdir
        try:
            try:
                with guarded_temporary_directory(prefix=".tmp-admission-chain-race-", parent=checked):
                    raise Fail("admission-chain load parent swap accepted")
            except Fail as exc:
                require(str(exc) == "admission-chain load temp parent identity drift after creation",
                        f"admission-chain load parent swap rejected at wrong boundary: {exc}")
            else:
                raise Fail("admission-chain load parent swap accepted")
        finally:
            os.mkdir = original_mkdir

        require(switched, "admission-chain load parent swap probe did not reach pinned mkdir")
        require(checked.is_symlink() and checked.resolve() == escaped.resolve(),
                "admission-chain load parent swap did not install isolated redirect")
        require((parked.stat().st_dev, parked.stat().st_ino) == original_identity,
                "admission-chain load parent swap changed pinned directory identity")
        require(not list(escaped.iterdir()), "admission-chain load parent swap published through redirect")
        require(not list(parked.iterdir()), "admission-chain load parent swap left pinned child")
        # The enclosing owned context removes all synthetic children; no
        # unconditional unlink or rename of mutable fixture paths is needed.
    print("PASS: admission-chain load parent swap during mkdir stays pinned and fails closed")


def prove_symlink_parent_rejected() -> None:
    with guarded_temporary_directory(".tmp-admission-chain-load-parent-", TMP_PARENT) as raw:
        sandbox = Path(raw)
        link = sandbox / "redirect"
        link.symlink_to(sandbox, target_is_directory=True)
        before = sorted(path.name for path in sandbox.iterdir())
        try:
            # Constructor-time domain failure is required by reconcile wrappers.
            guarded_temporary_directory(".tmp-must-not-create-", link)
        except Fail as exc:
            require(str(exc) == "admission-chain load temp ancestor missing or symlinked",
                    f"admission-chain load parent rejected at wrong boundary: {exc}")
        else:
            raise Fail("admission-chain load symlink parent accepted")
        require(sorted(path.name for path in sandbox.iterdir()) == before,
                "admission-chain load symlink parent published a child")
    print("PASS: admission-chain load fixture symlink parent rejected before creation")


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_admission_chain_load_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load admission-chain validator")
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
    require(VALIDATOR.is_file(), "admission-chain validator missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    prove_symlink_parent_rejected()
    prove_parent_swap_during_mkdir_rejected()
    validator = load_validator()

    with guarded_temporary_directory(".tmp-admission-chain-load-", TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)

        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_domain_fail("invalid UTF-8 chain authority JSON", lambda: validator.load(invalid_utf8), validator.Fail)

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_domain_fail("chain authority path is unreadable directory", lambda: validator.load(directory_authority), validator.Fail)

    print("Admission-chain unreadable-authority negative suite PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ADMISSION CHAIN LOAD NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
