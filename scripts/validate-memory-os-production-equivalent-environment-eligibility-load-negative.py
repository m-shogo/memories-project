#!/usr/bin/env python3
"""Prove semantic environment-generation eligibility authority fails closed on unreadable inputs."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import stat
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-eligibility.py"
HELPER_SUBSTITUTE = ROOT / "scripts/validate-memory-os-operability.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


MAX_MODULE_BYTES = 1024 * 1024


def load_validator():
    """Execute bounded semantic-eligibility source captured from checked FDs."""
    try:
        relative = VALIDATOR.relative_to(ROOT)
        require(VALIDATOR.resolve(strict=True) == ROOT.resolve() / relative,
                "cannot load environment eligibility validator")
        checked = VALIDATOR.lstat()
        require(stat.S_ISREG(checked.st_mode), "cannot load environment eligibility validator")
        require(all(type(getattr(os, flag, None)) is int and getattr(os, flag) > 0
                    for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY")),
                "cannot load environment eligibility validator")
        directory_fds = []
        source_fd = -1
        try:
            directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK
            parent_fd = os.open(ROOT, directory_flags)
            directory_fds.append(parent_fd)
            for component in relative.parts[:-1]:
                parent_fd = os.open(component, directory_flags, dir_fd=parent_fd)
                directory_fds.append(parent_fd)
            source_fd = os.open(relative.name,
                                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
            opened = os.fstat(source_fd)
            require(stat.S_ISREG(opened.st_mode)
                    and (opened.st_dev, opened.st_ino) == (checked.st_dev, checked.st_ino),
                    "cannot load environment eligibility validator")
            with os.fdopen(source_fd, "rb") as stream:
                source_fd = -1
                source = stream.read(MAX_MODULE_BYTES + 1)
        finally:
            cleanup_failed = False
            if source_fd >= 0:
                try:
                    os.close(source_fd)
                except OSError:
                    cleanup_failed = True
            for directory_fd in reversed(directory_fds):
                try:
                    os.close(directory_fd)
                except OSError:
                    cleanup_failed = True
            require(not cleanup_failed, "cannot load environment eligibility validator")
        require(len(source) <= MAX_MODULE_BYTES, "cannot load environment eligibility validator")

        class PinnedSourceLoader(importlib.machinery.SourceFileLoader):
            def get_code(self, fullname):
                require(fullname == "memory_os_environment_eligibility_load_negative",
                        "cannot load environment eligibility validator")
                return compile(source, str(VALIDATOR), "exec")

        name = "memory_os_environment_eligibility_load_negative"
        spec = importlib.util.spec_from_file_location(
            name, VALIDATOR, loader=PinnedSourceLoader(name, str(VALIDATOR)))
        require(spec is not None and spec.loader is not None,
                "cannot load environment eligibility validator")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:
        raise Fail("cannot load environment eligibility validator") from None
    return module


def prove_pinned_eligibility_import() -> None:
    """After-capture parent substitution must not redirect eligibility source."""
    global VALIDATOR
    original_path = VALIDATOR
    original_spec = importlib.util.spec_from_file_location
    with tempfile.TemporaryDirectory(prefix=".eligibility-import-", dir=ROOT) as raw:
        sandbox = Path(raw)
        parent = sandbox / "trusted"
        parent.mkdir()
        source = parent / "module.py"
        parked = sandbox / "parked"
        redirected = sandbox / "redirected"
        redirected.mkdir()
        canary = redirected / "module.py"
        source.write_text("VALUE = 'pinned'\n", encoding="utf-8")
        canary.write_text("raise RuntimeError('PRIVATE_ELIGIBILITY_CANARY')\n",
                          encoding="utf-8")
        swapped = False
        try:
            VALIDATOR = source
            require(load_validator().VALUE == "pinned",
                    "eligibility pinned import positive failed")

            def swap_after_read(name, location, *args, **kwargs):
                nonlocal swapped
                if not swapped and Path(location) == source:
                    swapped = True
                    parent.rename(parked)
                    parent.symlink_to(redirected, target_is_directory=True)
                return original_spec(name, location, *args, **kwargs)

            importlib.util.spec_from_file_location = swap_after_read
            loaded = load_validator()
            require(swapped and loaded.VALUE == "pinned",
                    "eligibility import executed redirected source")
            require(canary.read_text(encoding="utf-8") ==
                    "raise RuntimeError('PRIVATE_ELIGIBILITY_CANARY')\n",
                    "eligibility import changed redirected canary")
        finally:
            importlib.util.spec_from_file_location = original_spec
            VALIDATOR = original_path
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)
    require(callable(getattr(load_validator(), "main", None)),
            "eligibility pinned import canonical restoration failed")
    print("PASS: semantic eligibility load negative executes pinned source after parent swap")


def expect_rejected(name: str, action: Callable[[], Any], failure_type: type[BaseException]) -> None:
    try:
        action()
    except failure_type:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def main() -> int:
    require(VALIDATOR.is_file(), "environment eligibility validator missing")
    require(HELPER_SUBSTITUTE.is_file(), "repo-contained helper substitute missing")
    prove_pinned_eligibility_import()
    validator = load_validator()

    with tempfile.TemporaryDirectory(prefix="memory-os-environment-eligibility-load-negative-") as tmp:
        root = Path(tmp)
        malformed = root / "invalid-utf8.json"
        malformed.write_bytes(b"{\xff}")
        expect_rejected("invalid UTF-8 eligibility authority", lambda: validator.load(malformed), validator.Fail)
        expect_rejected("missing eligibility authority", lambda: validator.load(root / "missing.json"), validator.Fail)

    original_helper = validator.HELPER
    try:
        validator.HELPER = HELPER_SUBSTITUTE
        expect_rejected("repo-contained eligibility helper substitution", validator.load_helper, validator.Fail)
    finally:
        validator.HELPER = original_helper

    print("Memory OS production-equivalent environment eligibility load negative PASS")
    print("invalid UTF-8 authority accepted: false")
    print("missing authority accepted: false")
    print("repo-contained helper substitution accepted: false")
    print("canonical authority mutated: false")
    print("production evidence: false")
    print("production ready: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT ELIGIBILITY LOAD NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
