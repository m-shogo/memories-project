#!/usr/bin/env python3
"""Prove end-to-end admission-chain authority loading fails closed on unreadable repo-local inputs."""

from __future__ import annotations

import importlib.machinery
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


def prove_ancestor_swap_during_fd_walk_rejected() -> None:
    # The immediate parent can remain a real directory while a higher
    # ancestor is substituted between the checked walk and descriptor open.
    # A pinned walk must compare the opened inode with the current path.
    with guarded_temporary_directory(
        prefix=".tmp-admission-chain-ancestor-control-", parent=TMP_PARENT
    ) as raw:
        sandbox = Path(raw)
        checked_ancestor = sandbox / "checked-ancestor"
        parked_ancestor = sandbox / "parked-ancestor"
        redirected_ancestor = sandbox / "redirected-ancestor"
        checked_ancestor.mkdir()
        redirected_ancestor.mkdir()
        checked_parent = checked_ancestor / "nested"
        redirected_parent = redirected_ancestor / "nested"
        checked_parent.mkdir()
        redirected_parent.mkdir()
        with guarded_temporary_directory(
            prefix=".tmp-admission-chain-ancestor-positive-", parent=checked_parent
        ):
            pass

        original_open = os.open
        swapped = False

        def swap_before_descend(target, flags, *args, **kwargs):
            nonlocal swapped
            if not swapped and target == "nested" and kwargs.get("dir_fd") is not None:
                swapped = True
                checked_ancestor.rename(parked_ancestor)
                checked_ancestor.symlink_to(redirected_ancestor, target_is_directory=True)
            return original_open(target, flags, *args, **kwargs)

        os.open = swap_before_descend
        try:
            try:
                guarded_temporary_directory(
                    prefix=".tmp-admission-chain-ancestor-race-", parent=checked_parent
                )
            except Fail as exc:
                require(
                    str(exc) == "admission-chain load temp ancestor identity drift",
                    f"admission-chain load ancestor swap rejected at wrong boundary: {exc}",
                )
            else:
                raise Fail("admission-chain load ancestor swap accepted")
        finally:
            os.open = original_open

        require(swapped, "admission-chain load ancestor swap did not reach FD walk")
        require(checked_ancestor.is_symlink()
                and checked_ancestor.resolve() == redirected_ancestor.resolve(),
                "admission-chain load ancestor swap did not install isolated redirect")
        require(parked_ancestor.is_dir() and (parked_ancestor / "nested").is_dir(),
                "admission-chain load ancestor swap lost pinned original")
        require(not list((parked_ancestor / "nested").iterdir()),
                "admission-chain load ancestor swap created a child under original")
        require(not list(redirected_parent.iterdir()),
                "admission-chain load ancestor swap created a child through redirect")
        # The outer owned pinned fixture removes both isolated directories and
        # the substituted symlink; no unconditional cleanup of mutable names.
    print("PASS: admission-chain load ancestor swap during FD walk fails closed")


def prove_child_substitution_before_cleanup_rejected() -> None:
    # An owned temporary child must not be removed after its name is
    # substituted, even if the replacement points at another directory.
    with guarded_temporary_directory(prefix=".tmp-admission-chain-child-control-", parent=TMP_PARENT) as raw:
        sandbox = Path(raw)
        replacement = sandbox / "unowned-replacement"
        replacement.mkdir()
        parked = sandbox / "original-owned-child"
        try:
            with guarded_temporary_directory(prefix=".tmp-admission-chain-child-identity-", parent=sandbox) as inner:
                child = Path(inner)
                child.rename(parked)
                child.symlink_to(replacement, target_is_directory=True)
        except Fail as exc:
            require(str(exc) == "admission-chain load temp child identity drift before cleanup",
                    f"admission-chain load substituted child rejected at wrong boundary: {exc}")
        else:
            raise Fail("admission-chain load substituted child cleanup accepted")
        require(child.is_symlink() and parked.is_dir() and replacement.is_dir(),
                "admission-chain load substituted child proof did not preserve isolated fixtures")
        require(not list(replacement.iterdir()),
                "admission-chain load substituted child cleanup touched unowned replacement")
        # The outer pinned fixture owns the whole sandbox and safely removes
        # the intentionally retained substituted link and original child.
    print("PASS: admission-chain load substituted child inode rejects cleanup without deleting replacement")


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


MAX_MODULE_BYTES = 1024 * 1024


def load_validator():
    """Execute only bounded canonical validator source captured by descriptor."""
    try:
        relative = VALIDATOR.relative_to(ROOT)
        require(VALIDATOR.resolve(strict=True) == ROOT.resolve() / relative,
                "cannot load admission-chain validator")
        checked = VALIDATOR.lstat()
        require(stat.S_ISREG(checked.st_mode), "cannot load admission-chain validator")
        require(all(type(getattr(os, flag, None)) is int and getattr(os, flag) > 0
                    for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY")),
                "cannot load admission-chain validator")
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
                    "cannot load admission-chain validator")
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
            require(not cleanup_failed, "cannot load admission-chain validator")
        require(len(source) <= MAX_MODULE_BYTES, "cannot load admission-chain validator")

        class PinnedSourceLoader(importlib.machinery.SourceFileLoader):
            def get_code(self, fullname):
                require(fullname == "memory_os_admission_chain_load_negative",
                        "cannot load admission-chain validator")
                return compile(source, str(VALIDATOR), "exec")

        name = "memory_os_admission_chain_load_negative"
        spec = importlib.util.spec_from_file_location(
            name, VALIDATOR, loader=PinnedSourceLoader(name, str(VALIDATOR)))
        require(spec is not None and spec.loader is not None,
                "cannot load admission-chain validator")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:
        raise Fail("cannot load admission-chain validator") from None
    return module


def prove_pinned_validator_import() -> None:
    """A swapped parent after capture cannot select a different validator."""
    global VALIDATOR
    original_path = VALIDATOR
    original_spec = importlib.util.spec_from_file_location
    with tempfile.TemporaryDirectory(prefix=".admission-chain-import-", dir=ROOT) as raw:
        sandbox = Path(raw)
        parent = sandbox / "trusted"
        parent.mkdir()
        source = parent / "module.py"
        parked = sandbox / "parked"
        redirected = sandbox / "redirected"
        redirected.mkdir()
        canary = redirected / "module.py"
        source.write_text("VALUE = 'pinned'\n", encoding="utf-8")
        canary.write_text("raise RuntimeError('PRIVATE_ADMISSION_CHAIN_CANARY')\n",
                          encoding="utf-8")
        swapped = False
        try:
            VALIDATOR = source
            require(load_validator().VALUE == "pinned",
                    "admission-chain pinned import positive failed")

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
                    "admission-chain import executed redirected source")
            require(canary.read_text(encoding="utf-8") ==
                    "raise RuntimeError('PRIVATE_ADMISSION_CHAIN_CANARY')\n",
                    "admission-chain import changed redirected canary")
        finally:
            importlib.util.spec_from_file_location = original_spec
            VALIDATOR = original_path
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)
    require(callable(getattr(load_validator(), "main", None)),
            "admission-chain pinned import canonical restoration failed")
    print("PASS: admission-chain load negative executes pinned source after parent swap")


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
    prove_ancestor_swap_during_fd_walk_rejected()
    prove_child_substitution_before_cleanup_rejected()
    prove_pinned_validator_import()
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
