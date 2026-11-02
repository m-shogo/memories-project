#!/usr/bin/env python3
"""Fail closed if generation-evidence validation transport is substituted."""

from __future__ import annotations

import importlib.util
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence.py"
VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-generation-evidence.py")
MAX_VALIDATOR_SOURCE_BYTES = 1024 * 1024


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_validator_identity() -> None:
    # The first path identity probe precedes the pinned-FD reader's try block.
    # Private filesystem diagnostics must not escape read-only CI.
    try:
        valid = (VALIDATOR == ROOT / VALIDATOR_REL
                 and VALIDATOR.is_file() and not VALIDATOR.is_symlink()
                 and VALIDATOR.resolve(strict=True) == VALIDATOR)
    except (OSError, ValueError, TypeError, RuntimeError):
        raise Fail("generation evidence transport validator source authority unreadable") from None
    require(valid, "canonical generation-evidence validator source authority drift")


def pinned_validator_source() -> bytes:
    """Bind executable validator bytes to owned no-follow directory/file descriptors."""
    require_validator_identity()
    require(all(type(getattr(os, name, None)) is int and getattr(os, name) > 0
                for name in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")),
            "generation evidence transport pinned validator import unavailable")
    owned: list[int] = []
    try:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        parent_fd = os.open(ROOT, flags)
        require(type(parent_fd) is int and parent_fd >= 0,
                "generation evidence transport validator parent descriptor invalid")
        owned.append(parent_fd)
        for part in VALIDATOR_REL.parts[:-1]:
            parent_fd = os.open(part, flags, dir_fd=parent_fd)
            require(type(parent_fd) is int and parent_fd >= 0,
                    "generation evidence transport validator parent descriptor invalid")
            owned.append(parent_fd)
        parents_before = [os.fstat(fd) for fd in owned]
        parent_identity = lambda item: (
            item.st_dev, item.st_ino, item.st_mode, item.st_ctime_ns
        )
        require(all(stat.S_ISDIR(item.st_mode) and not (item.st_mode & 0o022)
                    for item in parents_before),
                "generation evidence transport validator parent unsafe")
        source_fd = os.open(
            VALIDATOR_REL.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=parent_fd,
        )
        require(type(source_fd) is int and source_fd >= 0,
                "generation evidence transport validator source descriptor invalid")
        owned.append(source_fd)
        before = os.fstat(source_fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and not (before.st_mode & 0o022)
                and 0 < before.st_size <= MAX_VALIDATOR_SOURCE_BYTES,
                "generation evidence transport validator source metadata unsafe")
        chunks: list[bytes] = []
        remaining = MAX_VALIDATOR_SOURCE_BYTES + 1
        while remaining:
            chunk = os.read(source_fd, remaining)
            require(type(chunk) is bytes,
                    "generation evidence transport validator read type invalid")
            if not chunk:
                break
            # A faulty read returning more than requested must fail before
            # remaining becomes negative and the loop can no longer terminate.
            require(len(chunk) <= remaining,
                    "generation evidence transport validator source changed during read")
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
                "generation evidence transport validator source changed during read")
        for index, fd in enumerate(owned[:-1]):
            current = os.fstat(fd)
            lexical = ROOT if index == 0 else ROOT.joinpath(*VALIDATOR_REL.parts[:index])
            visible = os.lstat(lexical)
            require(stat.S_ISDIR(visible.st_mode)
                    and parent_identity(parents_before[index])
                    == parent_identity(current) == parent_identity(visible),
                    "generation evidence transport validator parent changed during read")
        require_validator_identity()
        require(identity(VALIDATOR.stat()) == identity(after),
                "generation evidence transport validator pathname changed during read")
        return source
    except (OSError, ValueError, TypeError):
        raise Fail("generation evidence transport validator pinned source unreadable") from None
    finally:
        primary = sys.exc_info()[0] is not None
        failed = False
        for fd in reversed(owned):
            try:
                os.close(fd)
            except Exception:
                failed = True
        if failed and not primary:
            raise Fail("generation evidence transport validator descriptor cleanup failed") from None


def load_validator() -> Any:
    source = pinned_validator_source()
    spec = importlib.util.spec_from_file_location(
        "memory_os_generation_evidence_transport_negative", VALIDATOR,
    )
    require(spec is not None and spec.loader is not None,
            "cannot load generation-evidence validator")
    module = importlib.util.module_from_spec(spec)
    exec(compile(source, str(VALIDATOR), "exec"), module.__dict__)
    return module


def prove_pinned_validator_import() -> None:
    """Prove after-capture parent swap cannot redirect the negative harness."""
    global ROOT, VALIDATOR
    original_root, original_validator = ROOT, VALIDATOR
    original_spec = importlib.util.spec_from_file_location
    with tempfile.TemporaryDirectory(prefix="memory-os-generation-transport-pin-") as raw:
        fixture = Path(raw)
        parent = fixture / "scripts"
        parent.mkdir()
        source = parent / VALIDATOR_REL.name
        source.write_text("SOURCE_MARKER = 'reviewed'\n", encoding="utf-8")
        redirected = fixture / "redirected"
        redirected.mkdir()
        canary = redirected / source.name
        canary_bytes = b"raise RuntimeError('PRIVATE_GENERATION_VALIDATOR_SWAP_CANARY')\n"
        canary.write_bytes(canary_bytes)
        parked = fixture / "parked-scripts"
        ROOT, VALIDATOR = fixture, source
        try:
            require(load_validator().SOURCE_MARKER == "reviewed",
                    "generation transport pinned validator positive control failed")
            # Before acquiring any owned FD, a path probe can raise a private
            # filesystem exception. It must produce only a fixed-domain Fail.
            original_resolve = Path.resolve
            # Path.resolve can raise RuntimeError for a resolution loop.
            # It is not a trusted diagnostic merely because it is non-OS.
            for failure_type in (OSError, ValueError, TypeError, RuntimeError):
                marker = "PRIVATE_GENERATION_SOURCE_IDENTITY_CANARY"

                def private_identity_probe(self, *args, **kwargs):
                    if self == source:
                        raise failure_type(marker)
                    return original_resolve(self, *args, **kwargs)

                Path.resolve = private_identity_probe
                try:
                    try:
                        load_validator()
                    except Fail as exc:
                        require(str(exc) == "generation evidence transport validator source authority unreadable"
                                and exc.__suppress_context__ and marker not in str(exc),
                                "generation evidence transport private identity probe diagnostic drift")
                    else:
                        raise Fail("generation evidence transport accepted private identity probe failure")
                finally:
                    Path.resolve = original_resolve
            # The real open sequence is ROOT, scripts ancestor, validator leaf.
            # Never use absolute path depth as an acquisition ordinal.
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
                                    "generation transport invalid acquired FD wrong rejection")
                        else:
                            raise Fail("generation transport accepted invalid acquired FD")
                    finally:
                        os.open, os.close = original_open, original_close
                    require(call_count == ordinal,
                            "generation transport invalid FD fixture acquisition order drift")
                    require(closed == list(reversed(acquired)),
                            "generation transport invalid FD ownership/cleanup drift")

            # Preserve the primary pinned-read rejection when a secondary
            # descriptor close faults. With no primary, close failures must
            # be private, deterministic and must not strand owned FDs.
            for with_primary in (False, True):
                original_close, original_read = os.close, os.read
                close_count = 0
                private_marker = "PRIVATE_GENERATION_TRANSPORT_CLOSE_CANARY"

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
                            "generation evidence transport validator source changed during read"
                            if with_primary else
                            "generation evidence transport validator descriptor cleanup failed"
                        )
                        require(str(exc) == expected and private_marker not in str(exc),
                                "generation transport descriptor cleanup failure precedence drift")
                        if not with_primary:
                            require(exc.__suppress_context__,
                                    "generation transport descriptor cleanup context exposed")
                    else:
                        raise Fail("generation transport descriptor close fault accepted")
                finally:
                    os.close, os.read = original_close, original_read
                require(close_count == len(VALIDATOR_REL.parts) + 1,
                        "generation transport descriptor close ownership drift")

            original_read = os.read
            for failure_type in (OSError, ValueError, TypeError):
                def private_read_failure(*_args):
                    raise failure_type("PRIVATE_GENERATION_TRANSPORT_READ_CANARY")

                os.read = private_read_failure
                try:
                    try:
                        load_validator()
                    except Fail as exc:
                        require(str(exc) == "generation evidence transport validator pinned source unreadable"
                                and exc.__suppress_context__
                                and "PRIVATE_GENERATION_TRANSPORT_READ_CANARY" not in str(exc),
                                "generation transport private read diagnostic drift")
                    else:
                        raise Fail("generation transport accepted private read failure")
                finally:
                    os.read = original_read
            fragments = 0

            def fragmented_read(fd: int, count: int) -> bytes:
                nonlocal fragments
                fragments += 1
                return original_read(fd, min(count, 3))

            os.read = fragmented_read
            try:
                require(load_validator().SOURCE_MARKER == "reviewed",
                        "generation transport fragmented pinned source positive failed")
            finally:
                os.read = original_read
            require(fragments > 2, "generation transport fragmented read fixture was inert")

            for label, injected, expected in (
                ("premature EOF", lambda *_args: b"",
                 "generation evidence transport validator source changed during read"),
                ("nonbytes read", lambda *_args: "PRIVATE_GENERATION_READ_CANARY",
                 "generation evidence transport validator read type invalid"),
                ("oversized response",
                 lambda *_args: b"x" * (MAX_VALIDATOR_SOURCE_BYTES + 2),
                 "generation evidence transport validator source changed during read"),
            ):
                os.read = injected
                try:
                    try:
                        load_validator()
                    except Fail as exc:
                        require(str(exc) == expected,
                                "generation transport " + label + " wrong rejection")
                        require("PRIVATE_GENERATION_READ_CANARY" not in str(exc),
                                "generation transport private read canary leaked")
                    else:
                        raise Fail("generation transport accepted " + label)
                finally:
                    os.read = original_read
            for flag in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK"):
                original_flag = getattr(os, flag)
                setattr(os, flag, 0)
                try:
                    try:
                        load_validator()
                    except Fail as exc:
                        require(str(exc) == "generation evidence transport pinned validator import unavailable",
                                "generation transport zeroed " + flag + " wrong rejection")
                    else:
                        raise Fail("generation transport accepted zeroed " + flag)
                finally:
                    setattr(os, flag, original_flag)
            source.chmod(0o666)
            try:
                load_validator()
            except Fail as exc:
                require(str(exc) == "generation evidence transport validator source metadata unsafe",
                        "writable generation transport validator wrong rejection")
            else:
                raise Fail("writable generation transport validator accepted")
            source.chmod(0o644)
            alias = fixture / "hardlink-validator.py"
            os.link(source, alias)
            try:
                load_validator()
            except Fail as exc:
                require(str(exc) == "generation evidence transport validator source metadata unsafe",
                        "hardlinked generation transport validator wrong rejection")
            else:
                raise Fail("hardlinked generation transport validator accepted")
            alias.unlink()
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
                    "generation transport imported redirected validator source")
            require(canary.read_bytes() == canary_bytes,
                    "generation transport redirected validator canary changed")
        finally:
            importlib.util.spec_from_file_location = original_spec
            ROOT, VALIDATOR = original_root, original_validator
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)
    print("PASS: generation transport pinned importer rejects invalid FDs, EOF, nonbytes, hardlink and swap; fragmented read works")



def expect_rejected(module: Any, label: str, mutate: Callable[[], None], restore: Callable[[], None], expected: str) -> None:
    mutate()
    try:
        try:
            module.main()
        except module.Fail as exc:
            require(expected in str(exc), f"{label} rejected at wrong boundary: {exc}")
            return
        raise Fail(f"generation-evidence transport substitution unexpectedly passed: {label}")
    finally:
        restore()



def prove_private_bounded_child_execution(module: Any) -> None:
    """Exercise the real child runner with synthetic secret-bearing failures."""
    original_run = module.subprocess.run
    canary = "private-generation-evidence-child-canary"
    cases = ("success", "nonzero", "timeout", "oserror", "valueerror", "typeerror",
             "missing-result", "boolean-code", "forged-zero")
    poisoned = {
        "PYTHONPATH": "SYNTHETIC_UNTRUSTED_IMPORT_PATH",
        "PYTHONHOME": "SYNTHETIC_UNTRUSTED_HOME",
        "PYTHONWARNINGS": "SYNTHETIC_UNTRUSTED_WARNINGS",
        "LD_PRELOAD": "SYNTHETIC_UNTRUSTED_LOADER",
        "DYLD_INSERT_LIBRARIES": "SYNTHETIC_UNTRUSTED_DYLD",
        "GIT_CONFIG_GLOBAL": "SYNTHETIC_UNTRUSTED_GIT_CONFIG",
        "SAFE_GENERATION_CHILD_ENV": "preserved",
    }
    patcher = patch.dict(module.os.environ, poisoned)
    patcher.start()
    try:
        for case in cases:
            def fake_run(argv: list[str], **kwargs: Any) -> Any:
                expected_bootstrap = (
                    "import os, sys\n"
                    "path = sys.argv[1]\n"
                    "sys.path.insert(0, os.path.dirname(path))\n"
                    "sys.argv[:] = [path]\n"
                    "scope = {'__name__': '__main__', '__file__': path, '__package__': None, '__spec__': None}\n"
                    "exec(compile(sys.stdin.buffer.read(), path, 'exec'), scope)\n"
                )
                require(argv == [
                    module.sys.executable, "-c", expected_bootstrap,
                    str(module.INDEPENDENT_REVIEW_VALIDATOR),
                ], "generation evidence child source identity drift")
                require(type(kwargs.get("input")) is bytes
                        and kwargs["input"] == module.INDEPENDENT_REVIEW_VALIDATOR.read_bytes(),
                        "generation evidence child pinned source bytes drift")
                require(kwargs.get("cwd") == module.ROOT, "generation evidence child cwd drift")
                require(kwargs.get("stdout") == module.subprocess.DEVNULL and
                        kwargs.get("stderr") == module.subprocess.DEVNULL,
                        "generation evidence child output not private")
                require(kwargs.get("timeout") == 90 and kwargs.get("check") is False,
                        "generation evidence child execution not bounded")
                child_env = kwargs.get("env")
                require(isinstance(child_env, dict), "generation evidence child environment missing")
                require(child_env.get("SAFE_GENERATION_CHILD_ENV") == "preserved",
                        "generation evidence child benign environment lost")
                for key in ("PYTHONPATH", "PYTHONHOME", "PYTHONWARNINGS",
                            "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "GIT_CONFIG_GLOBAL"):
                    require(key not in child_env, "generation evidence child inherited override: " + key)
                require(child_env == {
                    key: value for key, value in module.os.environ.items()
                    if not key.startswith(("PYTHON", "LD_", "DYLD_", "GIT_"))
                }, "generation evidence child environment authority drift")
                if case == "timeout":
                    raise module.subprocess.TimeoutExpired(argv, 90, output=canary, stderr=canary)
                if case == "oserror":
                    raise OSError(canary)
                if case == "valueerror":
                    raise ValueError(canary)
                if case == "typeerror":
                    raise TypeError(canary)
                if case == "forged-zero":
                    return type("ForgedResult", (), {"returncode": 0})()
                if case == "missing-result":
                    return None
                if case == "boolean-code":
                    return module.subprocess.CompletedProcess(argv, False)
                return module.subprocess.CompletedProcess(argv, 0 if case == "success" else 1,
                                                          stdout=canary, stderr=canary)

            module.subprocess.run = fake_run
            if case == "success":
                module.run_validator(module.INDEPENDENT_REVIEW_VALIDATOR,
                                     module.INDEPENDENT_REVIEW_VALIDATOR_REL, "generation independent-review validator")
                continue
            try:
                module.run_validator(module.INDEPENDENT_REVIEW_VALIDATOR,
                                     module.INDEPENDENT_REVIEW_VALIDATOR_REL, "generation independent-review validator")
            except module.Fail as exc:
                require(str(exc) == "generation evidence child validator failed",
                        "generation evidence child exposed non-private diagnostic")
                require(canary not in str(exc), "generation evidence child leaked canary")
                require(exc.__suppress_context__, "generation evidence child exception context exposed")
            else:
                raise Fail("generation evidence child accepted invalid outcome: " + case)
    finally:
        module.subprocess.run = original_run
        patcher.stop()




def prove_private_writer_import_failures(module: Any) -> None:
    """Reject private filesystem errors in the actual generation evidence writer loader."""
    original_spec = module.importlib.util.spec_from_file_location
    original_module = module.importlib.util.module_from_spec
    canary = "private-generation-evidence-writer-import-canary"

    def fail_private(*_args: Any, **_kwargs: Any) -> Any:
        raise OSError(canary)

    try:
        for target in ("spec", "module"):
            if target == "spec":
                module.importlib.util.spec_from_file_location = fail_private
            else:
                module.importlib.util.spec_from_file_location = original_spec
                module.importlib.util.module_from_spec = fail_private
            try:
                module.load_writer()
            except module.Fail as exc:
                require(str(exc) == "generation evidence writer import unavailable",
                        "generation evidence writer import disclosed private error")
                require(canary not in str(exc) and exc.__suppress_context__,
                        "generation evidence writer import exposed exception context")
            else:
                raise Fail("generation evidence writer import accepted private failure: " + target)
    finally:
        module.importlib.util.spec_from_file_location = original_spec
        module.importlib.util.module_from_spec = original_module
    require(callable(getattr(module.load_writer(), "validate_record", None)),
            "generation evidence writer import positive control failed")
    print("PASS: generation evidence writer import private failures and real positive")




def prove_private_escaped_path_diagnostic(module: Any) -> None:
    canary = "private-generation-evidence-path-canary"
    outside = Path(tempfile.gettempdir()) / canary
    try:
        module.repo_relative(outside)
    except module.Fail as exc:
        require(str(exc) == "artifact path escapes repository root",
                "generation evidence escaped-path diagnostic disclosed private path")
        require(canary not in str(exc) and exc.__suppress_context__,
                "generation evidence escaped-path exception context exposed")
    else:
        raise Fail("generation evidence accepted outside private path")
    print("PASS: generation evidence escaped-path diagnostic is private")



def main() -> int:
    prove_pinned_validator_import()
    module = load_validator()
    prove_private_bounded_child_execution(module)
    prove_private_writer_import_failures(module)
    prove_private_escaped_path_diagnostic(module)

    original_guard = module.enforce_execution_transport
    expect_rejected(
        module,
        "execution guard",
        lambda: setattr(module, "enforce_execution_transport", lambda: None),
        lambda: setattr(module, "enforce_execution_transport", original_guard),
        "execution guard drift",
    )

    original_run = module.subprocess.run
    expect_rejected(
        module,
        "subprocess.run",
        lambda: setattr(module.subprocess, "run", lambda *_args, **_kwargs: None),
        lambda: setattr(module.subprocess, "run", original_run),
        "subprocess execution transport drift",
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

    original_run_validator = module.run_validator
    invoked: list[Path] = []

    def observe_validator(path: Path, expected_relative: Path, label: str) -> None:
        invoked.append(expected_relative)
        original_run_validator(path, expected_relative, label)

    module.run_validator = observe_validator
    try:
        module.main()
    finally:
        module.run_validator = original_run_validator
    require(
        module.INDEPENDENT_REVIEW_VALIDATOR_REL in invoked,
        "canonical generation-evidence validation did not execute independent-review authority",
    )

    print("Memory OS generation-evidence execution transport negative PASS")
    print("execution guard substitution accepted: false")
    print("subprocess validation transport substitution accepted: false")
    print("import spec transport substitution accepted: false")
    print("module loader transport substitution accepted: false")
    print("central independent-review execution observed: true")
    print("generation evidence created: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION EVIDENCE TRANSPORT NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
