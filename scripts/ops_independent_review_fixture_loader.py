#!/usr/bin/env python3
"""Descriptor-pinned, disposable independent-review workflow fixture imports.

This is test infrastructure only, not production recovery evidence.
"""
from __future__ import annotations

import builtins
import importlib.machinery
import importlib.util
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

MAX_MODULE_BYTES = 1024 * 1024
DIAGNOSTIC = "cannot load independent-review fixture validator"


class FixtureImportFail(RuntimeError):
    pass


def require(condition: bool) -> None:
    if not condition:
        raise FixtureImportFail(DIAGNOSTIC)


def load_pinned_module(root: Path, path: Path, name: str) -> Any:
    """Read checked regular source through anchored directory FDs, then execute those bytes."""
    try:
        require(root.is_absolute() and path.is_absolute() and not root.is_symlink())
        relative = path.relative_to(root)
        require(bool(relative.parts) and all(part not in ("", ".", "..") for part in relative.parts))
        require(path.resolve(strict=True) == root.resolve(strict=True) / relative)
        checked = path.lstat()
        require(stat.S_ISREG(checked.st_mode))
        require(all(type(getattr(os, flag, None)) is int and getattr(os, flag) > 0
                    for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY")))
        directory_fds: list[int] = []
        source_fd = -1
        try:
            directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK
            parent_fd = os.open(root, directory_flags)
            directory_fds.append(parent_fd)
            for component in relative.parts[:-1]:
                parent_fd = os.open(component, directory_flags, dir_fd=parent_fd)
                directory_fds.append(parent_fd)
            source_fd = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                dir_fd=parent_fd)
            opened = os.fstat(source_fd)
            require(stat.S_ISREG(opened.st_mode) and
                    (opened.st_dev, opened.st_ino) == (checked.st_dev, checked.st_ino))
            with os.fdopen(source_fd, "rb") as stream:
                source_fd = -1
                source = stream.read(MAX_MODULE_BYTES + 1)
        finally:
            cleanup_failed = False
            if source_fd >= 0:
                try:
                    os.close(source_fd)
                except (Exception, SystemExit):
                    cleanup_failed = True
            for fd in reversed(directory_fds):
                try:
                    os.close(fd)
                except (Exception, SystemExit):
                    cleanup_failed = True
            require(not cleanup_failed)
        require(len(source) <= MAX_MODULE_BYTES)

        class PinnedLoader(importlib.machinery.SourceFileLoader):
            def get_code(self, fullname: str):
                require(fullname == name)
                try:
                    return compile(source, str(path), "exec")
                except (Exception, SystemExit):
                    raise FixtureImportFail(DIAGNOSTIC) from None

        spec = importlib.util.spec_from_file_location(
            name, path, loader=PinnedLoader(name, str(path)))
        require(spec is not None and spec.loader is not None)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except FixtureImportFail:
        raise FixtureImportFail(DIAGNOSTIC) from None
    except (Exception, SystemExit):
        raise FixtureImportFail(DIAGNOSTIC) from None


def expect_rejected(root: Path, path: Path, name: str) -> None:
    try:
        load_pinned_module(root, path, name)
    except FixtureImportFail as exc:
        require(str(exc) == DIAGNOSTIC and exc.__suppress_context__)
        return
    raise AssertionError("unsafe independent-review fixture module accepted")


def prove_pinned_import() -> None:
    """Positive, ancestor swap, symlink, FIFO, size and fdopen ownership negatives."""
    with tempfile.TemporaryDirectory(prefix="independent-review-fixture-") as raw:
        root = Path(raw)
        parent = root / "scripts"
        parent.mkdir()
        source = parent / "validator.py"
        source.write_text("VALUE = 7\n", encoding="utf-8")
        require(load_pinned_module(root, source, "independent_fixture_positive").VALUE == 7)

        parked = root / "parked"
        external = root / "external"
        external.mkdir()
        canary = external / "validator.py"
        canary.write_text("raise RuntimeError('PRIVATE_EXTERNAL_CANARY')\n", encoding="utf-8")
        original_spec = importlib.util.spec_from_file_location
        swapped = False

        def swap_after_read(name: str, location: str, *args: Any, **kwargs: Any):
            nonlocal swapped
            if not swapped and Path(location) == source:
                swapped = True
                parent.rename(parked)
                parent.symlink_to(external, target_is_directory=True)
            return original_spec(name, location, *args, **kwargs)

        importlib.util.spec_from_file_location = swap_after_read
        try:
            module = load_pinned_module(root, source, "independent_fixture_swap")
            require(swapped and module.VALUE == 7)
            require(canary.read_text(encoding="utf-8") ==
                    "raise RuntimeError('PRIVATE_EXTERNAL_CANARY')\n")
        finally:
            importlib.util.spec_from_file_location = original_spec
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)

        require(load_pinned_module(root, source, "independent_fixture_restored").VALUE == 7)
        link = parent / "symlink.py"
        link.symlink_to(source)
        expect_rejected(root, link, "independent_fixture_symlink")
        fifo = parent / "fifo.py"
        os.mkfifo(fifo)
        expect_rejected(root, fifo, "independent_fixture_fifo")
        oversized = parent / "oversized.py"
        oversized.write_bytes(b"x" * (MAX_MODULE_BYTES + 1))
        expect_rejected(root, oversized, "independent_fixture_oversized")
        invalid = parent / "invalid.py"
        invalid.write_text("def invalid(:\n", encoding="utf-8")
        expect_rejected(root, invalid, "independent_fixture_compile")

        for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY"):
            original_flag = getattr(os, flag)
            for unsupported in (None, 0):
                try:
                    setattr(os, flag, unsupported)
                    expect_rejected(root, source, "independent_fixture_unsupported_" + flag)
                finally:
                    setattr(os, flag, original_flag)

        original_compile = builtins.compile
        def compile_exit(payload: bytes, filename: str, mode: str, *args: Any, **kwargs: Any):
            if filename == str(source):
                raise SystemExit("PRIVATE_INDEPENDENT_COMPILE_CANARY")
            return original_compile(payload, filename, mode, *args, **kwargs)
        builtins.compile = compile_exit
        try:
            expect_rejected(root, source, "independent_fixture_compile_exit")
        finally:
            builtins.compile = original_compile

        before = len(os.listdir("/proc/self/fd"))
        original_fdopen = os.fdopen
        def fail_fdopen(*_args: Any, **_kwargs: Any):
            raise OSError("PRIVATE_FDOPEN_CANARY")
        os.fdopen = fail_fdopen
        try:
            expect_rejected(root, source, "independent_fixture_fdopen")
        finally:
            os.fdopen = original_fdopen
        require(len(os.listdir("/proc/self/fd")) == before)
        original_close = os.close
        close_fired = False

        def close_then_fail(fd: int) -> None:
            nonlocal close_fired
            original_close(fd)
            if not close_fired:
                close_fired = True
                raise OSError("PRIVATE_CLOSE_CANARY")

        os.close = close_then_fail
        try:
            expect_rejected(root, source, "independent_fixture_close_after_close")
        finally:
            os.close = original_close
        require(close_fired and len(os.listdir("/proc/self/fd")) == before)
        require(load_pinned_module(root, source, "independent_fixture_final").VALUE == 7)
    print("PASS independent-review pinned fixture import: swap, symlink, FIFO, size, platform flags, compile/SystemExit, fdopen, close-after-close")


if __name__ == "__main__":
    try:
        prove_pinned_import()
    except (Exception, SystemExit):
        raise SystemExit("independent-review pinned fixture import negative FAILED") from None
