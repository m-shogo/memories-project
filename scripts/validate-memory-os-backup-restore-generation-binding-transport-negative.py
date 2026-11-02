#!/usr/bin/env python3
"""Fail closed if generation-binding loader transport is substituted."""

from __future__ import annotations

import importlib.util
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-binding.py"
VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-generation-binding.py")
MAX_VALIDATOR_SOURCE_BYTES = 1024 * 1024


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_validator_identity() -> None:
    require(VALIDATOR == ROOT / VALIDATOR_REL
            and VALIDATOR.is_file() and not VALIDATOR.is_symlink()
            and VALIDATOR.resolve(strict=True) == VALIDATOR,
            "generation-binding transport validator source authority drift")


def pinned_validator_source() -> bytes:
    """Read reviewed generation-binding validator bytes from owned no-follow FDs."""
    require_validator_identity()
    require(all(type(getattr(os, flag, None)) is int and getattr(os, flag) > 0
                for flag in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")),
            "generation-binding transport pinned import unavailable")
    owned: list[int] = []
    try:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        parent_fd = os.open(ROOT, flags)
        require(type(parent_fd) is int and parent_fd >= 0,
                "generation-binding transport parent descriptor invalid")
        owned.append(parent_fd)
        for part in VALIDATOR_REL.parts[:-1]:
            parent_fd = os.open(part, flags, dir_fd=parent_fd)
            require(type(parent_fd) is int and parent_fd >= 0,
                    "generation-binding transport parent descriptor invalid")
            owned.append(parent_fd)
        parents_before = [os.fstat(fd) for fd in owned]
        parent_identity = lambda item: (
            item.st_dev, item.st_ino, item.st_mode, item.st_ctime_ns
        )
        require(all(stat.S_ISDIR(item.st_mode) and not (item.st_mode & 0o022)
                    for item in parents_before),
                "generation-binding transport parent unsafe")
        source_fd = os.open(
            VALIDATOR_REL.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=parent_fd,
        )
        require(type(source_fd) is int and source_fd >= 0,
                "generation-binding transport source descriptor invalid")
        owned.append(source_fd)
        before = os.fstat(source_fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and not (before.st_mode & 0o022)
                and 0 < before.st_size <= MAX_VALIDATOR_SOURCE_BYTES,
                "generation-binding transport source metadata unsafe")
        chunks: list[bytes] = []
        remaining = MAX_VALIDATOR_SOURCE_BYTES + 1
        while remaining:
            chunk = os.read(source_fd, remaining)
            require(type(chunk) is bytes,
                    "generation-binding transport source read type invalid")
            if not chunk:
                break
            # Reject a faulty over-budget read before the remaining counter
            # can become negative and keep the loop alive indefinitely.
            require(len(chunk) <= remaining,
                    "generation-binding transport source changed during read")
            chunks.append(chunk)
            remaining -= len(chunk)
        source = b"".join(chunks)
        after = os.fstat(source_fd)
        leaf = os.stat(VALIDATOR_REL.name, dir_fd=parent_fd, follow_symlinks=False)
        identity = lambda item: (
            item.st_dev, item.st_ino, item.st_mode, item.st_size,
            item.st_mtime_ns, item.st_ctime_ns
        )
        require(len(source) == before.st_size
                and len(source) <= MAX_VALIDATOR_SOURCE_BYTES
                and identity(before) == identity(after) == identity(leaf),
                "generation-binding transport source changed during read")
        for index, fd in enumerate(owned[:-1]):
            current = os.fstat(fd)
            lexical = ROOT if index == 0 else ROOT.joinpath(*VALIDATOR_REL.parts[:index])
            visible = os.lstat(lexical)
            require(stat.S_ISDIR(visible.st_mode)
                    and parent_identity(parents_before[index])
                    == parent_identity(current) == parent_identity(visible),
                    "generation-binding transport parent changed during read")
        require_validator_identity()
        require(identity(VALIDATOR.stat()) == identity(after),
                "generation-binding transport pathname changed during read")
        return source
    except OSError:
        raise Fail("generation-binding transport pinned source unreadable") from None
    finally:
        primary = sys.exc_info()[0] is not None
        failed = False
        for fd in reversed(owned):
            try:
                os.close(fd)
            except Exception:
                failed = True
        if failed and not primary:
            raise Fail("generation-binding transport descriptor cleanup failed") from None


def load_validator() -> Any:
    source = pinned_validator_source()
    spec = importlib.util.spec_from_file_location(
        "memory_os_generation_binding_transport_negative", VALIDATOR,
    )
    require(spec is not None and spec.loader is not None,
            "cannot load generation-binding validator")
    module = importlib.util.module_from_spec(spec)
    exec(compile(source, str(VALIDATOR), "exec"), module.__dict__)
    return module


def prove_pinned_validator_import() -> None:
    """A real parent swap after capture cannot execute redirected source."""
    global ROOT, VALIDATOR
    original_root, original_validator = ROOT, VALIDATOR
    original_spec = importlib.util.spec_from_file_location
    with tempfile.TemporaryDirectory(prefix="memory-os-generation-binding-transport-pin-") as raw:
        fixture = Path(raw)
        parent = fixture / "scripts"
        parent.mkdir()
        source = parent / VALIDATOR_REL.name
        source.write_text("SOURCE_MARKER = 'reviewed'\n", encoding="utf-8")
        redirected = fixture / "redirected"
        redirected.mkdir()
        canary = redirected / source.name
        canary_bytes = b"raise RuntimeError('PRIVATE_BINDING_TRANSPORT_SWAP_CANARY')\n"
        canary.write_bytes(canary_bytes)
        parked = fixture / "parked-scripts"
        ROOT, VALIDATOR = fixture, source
        try:
            require(load_validator().SOURCE_MARKER == "reviewed",
                    "generation-binding transport pinned import positive control failed")
            # Actual acquisition order: ROOT, scripts ancestor, validator leaf.
            # Absolute path depth is not the os.open call count.
            for ordinal in (1, 2, 3):
                for invalid in (None, True, -1, "7"):
                    original_open, original_close = os.open, os.close
                    acquired: list[int] = []
                    closed: list[int] = []
                    call_count = 0

                    def invalid_acquisition(path, flags, *args, **kwargs):
                        nonlocal call_count
                        call_count += 1
                        if call_count == ordinal:
                            return invalid
                        descriptor = original_open(path, flags, *args, **kwargs)
                        acquired.append(descriptor)
                        return descriptor

                    def observe_close(descriptor: int) -> None:
                        closed.append(descriptor)
                        original_close(descriptor)

                    os.open, os.close = invalid_acquisition, observe_close
                    try:
                        try:
                            load_validator()
                        except Fail as exc:
                            require("descriptor invalid" in str(exc),
                                    "generation-binding transport invalid acquired FD wrong rejection")
                        else:
                            raise Fail("generation-binding transport accepted invalid acquired FD")
                    finally:
                        os.open, os.close = original_open, original_close
                    require(call_count == ordinal,
                            "generation-binding transport invalid FD fixture acquisition order drift")
                    require(closed == list(reversed(acquired)),
                            "generation-binding transport invalid FD ownership/cleanup drift")
            # An owned descriptor may close successfully yet report a
            # secondary failure. Prove private classification and that the
            # original pinned-read failure wins a double-fault race.
            for with_primary in (False, True):
                original_close, original_read = os.close, os.read
                close_count = 0
                private_marker = "PRIVATE_BINDING_TRANSPORT_CLOSE_CANARY"

                def injected_close(descriptor: int) -> None:
                    nonlocal close_count
                    close_count += 1
                    original_close(descriptor)
                    if close_count == 1:
                        raise ValueError(private_marker)

                os.close = injected_close
                if with_primary:
                    os.read = lambda *_args: b""
                try:
                    try:
                        load_validator()
                    except Fail as exc:
                        expected = (
                            "generation-binding transport source changed during read"
                            if with_primary else
                            "generation-binding transport descriptor cleanup failed"
                        )
                        require(str(exc) == expected and private_marker not in str(exc),
                                "generation-binding descriptor cleanup failure precedence drift")
                        if not with_primary:
                            require(exc.__suppress_context__,
                                    "generation-binding descriptor cleanup context exposed")
                    else:
                        raise Fail("generation-binding descriptor close fault accepted")
                finally:
                    os.close, os.read = original_close, original_read
                require(close_count == len(VALIDATOR_REL.parts) + 1,
                        "generation-binding descriptor close ownership drift")

            original_read = os.read
            fragments = 0

            def fragmented_read(fd: int, count: int) -> bytes:
                nonlocal fragments
                fragments += 1
                return original_read(fd, min(count, 3))

            os.read = fragmented_read
            try:
                require(load_validator().SOURCE_MARKER == "reviewed",
                        "generation-binding transport fragmented source positive failed")
            finally:
                os.read = original_read
            require(fragments > 2, "generation-binding fragmented read fixture was inert")

            def private_read_failure(*_args: Any) -> bytes:
                raise OSError("PRIVATE_BINDING_READ_CANARY")

            for label, injected, expected in (
                ("premature EOF", lambda *_args: b"",
                 "generation-binding transport source changed during read"),
                ("nonbytes read", lambda *_args: "PRIVATE_BINDING_READ_CANARY",
                 "generation-binding transport source read type invalid"),
                ("oversized response",
                 lambda *_args: b"x" * (MAX_VALIDATOR_SOURCE_BYTES + 2),
                 "generation-binding transport source changed during read"),
                ("private read OSError", private_read_failure,
                 "generation-binding transport pinned source unreadable"),
            ):
                os.read = injected
                try:
                    try:
                        load_validator()
                    except Fail as exc:
                        require(str(exc) == expected,
                                "generation-binding transport " + label + " wrong rejection")
                        require("PRIVATE_BINDING_READ_CANARY" not in str(exc),
                                "generation-binding transport private read error leaked")
                        if label == "private read OSError":
                            require(exc.__suppress_context__,
                                    "generation-binding transport private read context exposed")
                    else:
                        raise Fail("generation-binding transport accepted " + label)
                finally:
                    os.read = original_read
            for flag in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK"):
                original_flag = getattr(os, flag)
                for invalid in (0, False, "inert"):
                    setattr(os, flag, invalid)
                    try:
                        try:
                            load_validator()
                        except Fail as exc:
                            require(str(exc) == "generation-binding transport pinned import unavailable",
                                    "generation-binding transport invalid " + flag + " wrong rejection")
                        else:
                            raise Fail("generation-binding transport accepted invalid " + flag)
                    finally:
                        setattr(os, flag, original_flag)
            source.chmod(0o666)
            try:
                load_validator()
            except Fail as exc:
                require(str(exc) == "generation-binding transport source metadata unsafe",
                        "writable generation-binding validator wrong rejection")
            else:
                raise Fail("writable generation-binding transport validator accepted")
            source.chmod(0o644)
            alias = fixture / "hardlink-binding-validator.py"
            os.link(source, alias)
            try:
                try:
                    load_validator()
                except Fail as exc:
                    require(str(exc) == "generation-binding transport source metadata unsafe",
                            "hardlinked generation-binding validator wrong rejection")
                else:
                    raise Fail("hardlinked generation-binding transport validator accepted")
            finally:
                alias.unlink()

            original_read = os.read
            parent_changed = False

            def chmod_parent_during_read(fd: int, count: int) -> bytes:
                nonlocal parent_changed
                chunk = original_read(fd, count)
                if not parent_changed:
                    parent.chmod(0o777)
                    parent_changed = True
                return chunk

            os.read = chmod_parent_during_read
            try:
                try:
                    load_validator()
                except Fail as exc:
                    require(str(exc) == "generation-binding transport parent changed during read",
                            "mid-read writable generation-binding parent wrong rejection")
                else:
                    raise Fail("mid-read writable generation-binding parent accepted")
            finally:
                os.read = original_read
                parent.chmod(0o755)
            require(parent_changed, "generation-binding parent-mode race fixture was inert")
            swapped = False

            def swap_after_capture(name, location, *args, **kwargs):
                nonlocal swapped
                if not swapped and Path(location) == source:
                    swapped = True
                    parent.rename(parked)
                    parent.symlink_to(redirected, target_is_directory=True)
                return original_spec(name, location, *args, **kwargs)

            importlib.util.spec_from_file_location = swap_after_capture
            loaded = load_validator()
            require(swapped and loaded.SOURCE_MARKER == "reviewed",
                    "generation-binding transport imported redirected source")
            require(canary.read_bytes() == canary_bytes,
                    "generation-binding transport canary changed")
        finally:
            importlib.util.spec_from_file_location = original_spec
            ROOT, VALIDATOR = original_root, original_validator
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)
    print("PASS: generation-binding transport pinned importer rejects EOF, nonbytes and private read failures; fragmented read works")



def expect_rejected(module: Any, label: str, mutate: Callable[[], None], restore: Callable[[], None], expected: str) -> None:
    mutate()
    try:
        try:
            module.main()
        except module.Fail as exc:
            require(expected in str(exc), f"{label} rejected at wrong boundary: {exc}")
            return
        raise Fail(f"generation-binding transport substitution unexpectedly passed: {label}")
    finally:
        restore()


def main() -> int:
    prove_pinned_validator_import()
    module = load_validator()

    original_guard = module.enforce_execution_transport
    expect_rejected(
        module,
        "execution guard",
        lambda: setattr(module, "enforce_execution_transport", lambda: None),
        lambda: setattr(module, "enforce_execution_transport", original_guard),
        "execution guard drift",
    )

    original_spec = module.importlib.util.spec_from_file_location
    expect_rejected(
        module,
        "importlib spec loader",
        lambda: setattr(module.importlib.util, "spec_from_file_location", lambda *_args, **_kwargs: None),
        lambda: setattr(module.importlib.util, "spec_from_file_location", original_spec),
        "import spec transport drift",
    )

    original_module_from_spec = module.importlib.util.module_from_spec
    expect_rejected(
        module,
        "importlib module loader",
        lambda: setattr(module.importlib.util, "module_from_spec", lambda *_args, **_kwargs: None),
        lambda: setattr(module.importlib.util, "module_from_spec", original_module_from_spec),
        "module loader transport drift",
    )

    print("Memory OS generation-binding loader transport negative PASS")
    print("execution guard substitution accepted: false")
    print("import spec transport substitution accepted: false")
    print("module loader transport substitution accepted: false")
    print("production-equivalent recovery candidate created: false")
    print("human promotion authority created: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION BINDING TRANSPORT NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
