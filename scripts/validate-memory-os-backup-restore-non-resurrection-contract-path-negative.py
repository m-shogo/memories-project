#!/usr/bin/env python3
"""Reject non-canonical or repository-escaping typed admission authority refs."""
from __future__ import annotations

import importlib.util
import inspect
import os
import secrets
import shutil
import stat
import tempfile
import weakref
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py"
EXPECTED_CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
EXPECTED_REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
EXPECTED_GEN_EVIDENCE_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
EXPECTED_GEN_WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
EXPECTED_LOCK = ROOT / "contracts/operations/.backup-restore-non-resurrection-admission.lock"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"

class Fail(RuntimeError):
    pass

def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)

def _remove_pinned_entries(directory_fd: int, flags: int) -> None:
    # Never recursively open a nested directory through a name that may have
    # changed after stat. Open each child with no-follow and traverse its FD.
    for entry_name in os.listdir(directory_fd):
        before = os.stat(entry_name, dir_fd=directory_fd, follow_symlinks=False)
        if stat.S_ISDIR(before.st_mode):
            nested_fd = os.open(entry_name, flags, dir_fd=directory_fd)
            try:
                opened = os.fstat(nested_fd)
                require(
                    (opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino),
                    "typed contract path nested directory identity drift before traversal",
                )
                _remove_pinned_entries(nested_fd, flags)
                after = os.stat(entry_name, dir_fd=directory_fd, follow_symlinks=False)
                require(
                    stat.S_ISDIR(after.st_mode)
                    and (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino),
                    "typed contract path nested directory identity drift before removal",
                )
                os.rmdir(entry_name, dir_fd=directory_fd)
            finally:
                os.close(nested_fd)
        else:
            after = os.stat(entry_name, dir_fd=directory_fd, follow_symlinks=False)
            require(
                (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino),
                "typed contract path nested entry identity drift before unlink",
            )
            os.unlink(entry_name, dir_fd=directory_fd)


@contextmanager
def _pinned_temporary_directory(prefix: str, parent: Path):
    # Pin every ancestor by descriptor: the checked pathname may be swapped
    # before mkdir, but the new child must stay beneath the opened directory.
    try:
        relative = parent.relative_to(ROOT)
    except ValueError as exc:
        raise Fail("typed contract path temp parent escapes repository") from exc
    require(ROOT.is_dir() and not ROOT.is_symlink(),
            "typed contract path repository root missing or symlinked")
    require(
        hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY")
        and shutil.rmtree.avoids_symlink_attacks,
        "typed contract path pinned fixture directory unsupported",
    )
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        fd = os.open(ROOT, flags)
    except OSError as exc:
        raise Fail(f"typed contract path cannot pin repository root: {exc}") from exc
    try:
        root_entry = ROOT.lstat()
        root_open = os.fstat(fd)
        require(
            stat.S_ISDIR(root_entry.st_mode)
            and (root_entry.st_dev, root_entry.st_ino) == (root_open.st_dev, root_open.st_ino),
            "typed contract path repository root identity drift",
        )
        cursor = ROOT
        for part in relative.parts:
            cursor = cursor / part
            require(cursor.is_dir() and not cursor.is_symlink(),
                    "typed contract path temp ancestor missing or symlinked")
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
            entry = cursor.lstat()
            opened = os.fstat(fd)
            require(
                stat.S_ISDIR(entry.st_mode)
                and (entry.st_dev, entry.st_ino) == (opened.st_dev, opened.st_ino),
                "typed contract path temp ancestor identity drift",
            )
        require(
            parent.resolve(strict=True) == ROOT.resolve(strict=True) / relative,
            "typed contract path temp parent canonical resolution drift",
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
            raise Fail("typed contract path temp child exclusive creation exhausted")
        created = os.stat(name, dir_fd=fd, follow_symlinks=False)
        try:
            current = parent.lstat()
            require(
                stat.S_ISDIR(current.st_mode)
                and (current.st_dev, current.st_ino) == (pinned.st_dev, pinned.st_ino),
                "typed contract path temp parent identity drift after creation",
            )
            require(stat.S_ISDIR(created.st_mode),
                    "typed contract path temp child is not a directory")
            yield str(parent / name)
        finally:
            current_child = os.stat(name, dir_fd=fd, follow_symlinks=False)
            require(
                stat.S_ISDIR(current_child.st_mode)
                and (current_child.st_dev, current_child.st_ino) == (created.st_dev, created.st_ino),
                "typed contract path temp child identity drift before cleanup",
            )
            # Pin the owned child before recursive deletion. A replacement of
            # its name after the identity check must never redirect rmtree
            # into an unowned directory with data.
            child_fd = os.open(name, flags, dir_fd=fd)
            try:
                pinned_child = os.fstat(child_fd)
                require(
                    (pinned_child.st_dev, pinned_child.st_ino) == (created.st_dev, created.st_ino),
                    "typed contract path temp child identity drift before traversal",
                )
                _remove_pinned_entries(child_fd, flags)
                final_child = os.stat(name, dir_fd=fd, follow_symlinks=False)
                require(
                    stat.S_ISDIR(final_child.st_mode)
                    and (final_child.st_dev, final_child.st_ino) == (created.st_dev, created.st_ino),
                    "typed contract path temp child identity drift before final removal",
                )
                os.rmdir(name, dir_fd=fd)
            finally:
                os.close(child_fd)
    except OSError as exc:
        raise Fail(f"typed contract path pinned fixture operation failed: {exc}") from exc
    finally:
        os.close(fd)


class _EagerFixtureDirectory:
    """Retain TemporaryDirectory's call-time creation/error and cleanup contract."""

    def __init__(self, manager):
        self._manager = manager
        self.name = manager.__enter__()
        self._finalizer = weakref.finalize(self, manager.__exit__, None, None, None)

    def __enter__(self):
        require(self._finalizer.alive, "typed contract path pinned fixture already closed")
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
    with guarded_temporary_directory(prefix=".tmp-typed-path-race-control-", parent=TMP_PARENT) as raw:
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
            if not switched and str(name).startswith(".tmp-typed-path-race-") and dir_fd is not None:
                switched = True
                checked.rename(parked)
                checked.symlink_to(escaped, target_is_directory=True)
            original_mkdir(name, mode=mode, dir_fd=dir_fd)

        os.mkdir = swap_before_mkdir
        try:
            try:
                with guarded_temporary_directory(prefix=".tmp-typed-path-race-", parent=checked):
                    raise Fail("typed contract path parent swap accepted")
            except Fail as exc:
                require(str(exc) == "typed contract path temp parent identity drift after creation",
                        f"typed contract path parent swap rejected at wrong boundary: {exc}")
            else:
                raise Fail("typed contract path parent swap accepted")
        finally:
            os.mkdir = original_mkdir

        require(switched, "typed contract path parent swap probe did not reach pinned mkdir")
        require(checked.is_symlink() and checked.resolve() == escaped.resolve(),
                "typed contract path parent swap did not install isolated redirect")
        require((parked.stat().st_dev, parked.stat().st_ino) == original_identity,
                "typed contract path parent swap changed pinned directory identity")
        require(not list(escaped.iterdir()), "typed contract path parent swap published through redirect")
        require(not list(parked.iterdir()), "typed contract path parent swap left pinned child")
        # The enclosing owned context removes all synthetic children; no
        # unconditional unlink or rename of mutable fixture paths is needed.
    print("PASS: typed contract path parent swap during mkdir stays pinned and fails closed")


def prove_child_substitution_before_cleanup_rejected() -> None:
    # An owned temporary child must not be removed after its name is
    # substituted, even if the replacement points at another directory.
    with guarded_temporary_directory(prefix=".tmp-typed-path-child-control-", parent=TMP_PARENT) as raw:
        sandbox = Path(raw)
        replacement = sandbox / "unowned-replacement"
        replacement.mkdir()
        parked = sandbox / "original-owned-child"
        try:
            with guarded_temporary_directory(prefix=".tmp-typed-path-child-identity-", parent=sandbox) as inner:
                child = Path(inner)
                child.rename(parked)
                child.symlink_to(replacement, target_is_directory=True)
        except Fail as exc:
            require(str(exc) == "typed contract path temp child identity drift before cleanup",
                    f"typed contract path substituted child rejected at wrong boundary: {exc}")
        else:
            raise Fail("typed contract path substituted child cleanup accepted")
        require(child.is_symlink() and parked.is_dir() and replacement.is_dir(),
                "typed contract path substituted child proof did not preserve isolated fixtures")
        require(not list(replacement.iterdir()),
                "typed contract path substituted child cleanup touched unowned replacement")
        # The outer pinned fixture owns the whole sandbox and safely removes
        # the intentionally retained substituted link and original child.
    print("PASS: typed contract path substituted child inode rejects cleanup without deleting replacement")


def prove_child_swap_during_cleanup_preserves_unowned_data() -> None:
    # Replace the child name only after the owned inode has been opened.
    # Traversal must stay on the pinned FD; final name drift must fail closed.
    with guarded_temporary_directory(prefix=".tmp-typed-path-cleanup-control-", parent=TMP_PARENT) as raw:
        sandbox = Path(raw)
        replacement = sandbox / "unowned-replacement"
        replacement.mkdir()
        sentinel = replacement / "important.txt"
        sentinel.write_text("preserve me", encoding="utf-8")
        parked = sandbox / "parked-owned-child"
        original_listdir = os.listdir
        switched = False
        try:
            with guarded_temporary_directory(prefix=".tmp-typed-path-cleanup-race-", parent=sandbox) as inner:
                child = Path(inner)
                (child / "owned.txt").write_text("owned fixture", encoding="utf-8")

                def swap_before_traversal(target):
                    nonlocal switched
                    if not switched and isinstance(target, int):
                        switched = True
                        child.rename(parked)
                        replacement.rename(child)
                    return original_listdir(target)

                os.listdir = swap_before_traversal
        except Fail as exc:
            require(str(exc) == "typed contract path temp child identity drift before final removal",
                    f"typed path cleanup race rejected at wrong boundary: {exc}")
        else:
            raise Fail("typed path cleanup race unexpectedly accepted")
        finally:
            os.listdir = original_listdir
        require(switched, "typed path cleanup race never reached pinned child traversal")
        require(child.is_dir() and (child / "important.txt").read_text(encoding="utf-8") == "preserve me",
                "typed path cleanup race deleted unowned replacement data")
        require(parked.is_dir() and not (parked / "owned.txt").exists(),
                "typed path cleanup race did not traverse the pinned owned child")
    print("PASS: typed contract path cleanup race preserves unowned replacement data")


def prove_nested_swap_during_cleanup_preserves_unowned_data() -> None:
    # A nested directory may be replaced after its FD is opened, just like
    # the fixture root. Recursive traversal must remain pinned to that FD.
    with guarded_temporary_directory(prefix=".tmp-typed-path-nested-control-", parent=TMP_PARENT) as raw:
        sandbox = Path(raw)
        replacement = sandbox / "unowned-nested-replacement"
        replacement.mkdir()
        (replacement / "important.txt").write_text("preserve nested", encoding="utf-8")
        original_listdir = os.listdir
        switched = False
        try:
            with guarded_temporary_directory(prefix=".tmp-typed-path-nested-race-", parent=sandbox) as inner:
                child = Path(inner)
                nested = child / "nested"
                nested.mkdir()
                (nested / "owned.txt").write_text("owned nested", encoding="utf-8")
                parked = child / "parked-owned-nested"
                nested_stat = nested.stat()
                nested_identity = (nested_stat.st_dev, nested_stat.st_ino)

                def swap_before_nested_traversal(target):
                    nonlocal switched
                    if (not switched and isinstance(target, int)
                            and (os.fstat(target).st_dev, os.fstat(target).st_ino) == nested_identity):
                        switched = True
                        nested.rename(parked)
                        replacement.rename(nested)
                    return original_listdir(target)

                os.listdir = swap_before_nested_traversal
        except Fail as exc:
            require(str(exc) == "typed contract path nested directory identity drift before removal",
                    f"typed nested cleanup race rejected at wrong boundary: {exc}")
        else:
            raise Fail("typed nested cleanup race unexpectedly accepted")
        finally:
            os.listdir = original_listdir
        require(switched, "typed nested cleanup race never reached pinned nested traversal")
        require((nested / "important.txt").read_text(encoding="utf-8") == "preserve nested",
                "typed nested cleanup race deleted unowned nested replacement data")
        require(parked.is_dir() and not (parked / "owned.txt").exists(),
                "typed nested cleanup race did not traverse pinned owned directory")
    print("PASS: typed contract path nested cleanup race preserves unowned replacement data")


def prove_file_swap_before_unlink_rejected() -> None:
    # A regular-file name can change between the two inode checks. The
    # replacement must survive; the owned original must not be unlinked.
    with guarded_temporary_directory(prefix=".tmp-typed-path-unlink-control-", parent=TMP_PARENT) as raw:
        sandbox = Path(raw)
        replacement = sandbox / "unowned-file.txt"
        replacement.write_text("preserve unowned", encoding="utf-8")
        original_stat = os.stat
        checks = 0
        swapped = False
        try:
            with guarded_temporary_directory(prefix=".tmp-typed-path-unlink-race-", parent=sandbox) as inner:
                child = Path(inner)
                owned = child / "owned.txt"
                parked = child / "parked-owned.txt"
                owned.write_text("owned fixture", encoding="utf-8")

                def swap_before_second_stat(path, *args, **kwargs):
                    nonlocal checks, swapped
                    if (path == "owned.txt" and kwargs.get("dir_fd") is not None
                            and kwargs.get("follow_symlinks") is False):
                        checks += 1
                        if checks == 2:
                            owned.rename(parked)
                            replacement.rename(owned)
                            swapped = True
                    return original_stat(path, *args, **kwargs)

                os.stat = swap_before_second_stat
        except Fail as exc:
            require(str(exc) == "typed contract path nested entry identity drift before unlink",
                    f"typed file cleanup race rejected at wrong boundary: {exc}")
        else:
            raise Fail("typed file cleanup race unexpectedly accepted")
        finally:
            os.stat = original_stat
        require(swapped and checks == 2, "typed file cleanup race never reached second inode check")
        require(owned.read_text(encoding="utf-8") == "preserve unowned",
                "typed file cleanup race deleted unowned replacement")
        require(parked.read_text(encoding="utf-8") == "owned fixture",
                "typed file cleanup race deleted original owned file")
    print("PASS: typed contract path file unlink race rejects unowned replacement")


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_non_resurrection_admission_path_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load typed admission validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def expect_rejected(module: Any, name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except module.Fail:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")

def load_typed_writer(validator: Any):
    return validator.load_module(validator.WRITER, "memory_os_non_resurrection_writer_negative")

def reject_typed_writer_cli_substitutions(validator: Any) -> None:
    typed_writer = load_typed_writer(validator)
    main_source = inspect.getsource(typed_writer.main)
    guard_index = main_source.find("require_cli_authorities()")
    parser_index = main_source.find("argparse.ArgumentParser")
    require(guard_index >= 0, "typed writer CLI does not enforce canonical authority guard")
    require(parser_index >= 0 and guard_index < parser_index, "typed writer CLI authority guard must run before argument parsing")

    require(typed_writer.CONTRACT == EXPECTED_CONTRACT, "typed writer contract authority drift")
    require(typed_writer.REGISTRY == EXPECTED_REGISTRY, "typed writer registry authority drift")
    require(typed_writer.GEN_EVIDENCE_REGISTRY == EXPECTED_GEN_EVIDENCE_REGISTRY, "typed writer generation evidence authority drift")
    require(typed_writer.GEN_WRITER == EXPECTED_GEN_WRITER, "typed writer generation writer authority drift")
    require(typed_writer.LOCK == EXPECTED_LOCK, "typed writer lock authority drift")

    substitutions = {
        "CONTRACT": ROOT / "contracts/operations/production-operability-status.json",
        "REGISTRY": EXPECTED_GEN_EVIDENCE_REGISTRY,
        "GEN_EVIDENCE_REGISTRY": EXPECTED_REGISTRY,
        "GEN_WRITER": ROOT / "scripts/register-memory-os-recovery-objectives.py",
        "LOCK": EXPECTED_CONTRACT,
    }
    for name, alternate in substitutions.items():
        original = getattr(typed_writer, name)
        setattr(typed_writer, name, alternate)
        try:
            expect_rejected(
                typed_writer,
                f"typed writer CLI {name} substitution",
                typed_writer.require_cli_authorities,
            )
        finally:
            setattr(typed_writer, name, original)

    try:
        typed_writer.require_cli_authorities()
    except typed_writer.Fail as exc:
        raise Fail(f"canonical typed writer CLI authority rejected: {exc}") from exc

def reject_typed_writer_substitution(validator: Any) -> None:
    original_loader = validator.load_module
    typed_writer = original_loader(validator.WRITER, "memory_os_non_resurrection_writer_negative")
    original_generation_writer = typed_writer.GEN_WRITER
    typed_writer.GEN_WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"

    def substituted_loader(path: Path, name: str):
        if path == validator.WRITER:
            return typed_writer
        return original_loader(path, name)

    validator.load_module = substituted_loader
    try:
        expect_rejected(
            validator,
            "repository-contained generation recovery writer substitution",
            validator.main,
        )
    finally:
        validator.load_module = original_loader
        typed_writer.GEN_WRITER = original_generation_writer


def prove_private_typed_admission_paths(validator: object) -> None:
    """Actual admission path helpers must suppress private paths and exception chains."""
    private = "SYNTHETIC_PRIVATE_TYPED_ADMISSION_CANARY"
    original_resolve = Path.resolve

    def private_resolve(_path, *args, **kwargs):
        raise OSError(private)

    def reject(label: str, operation, expected: str) -> None:
        try:
            operation()
        except validator.Fail as exc:
            require(str(exc) == expected and exc.__cause__ is None
                    and (exc.__suppress_context__ or exc.__context__ is None),
                    f"typed admission {label} leaked private exception context")
            require(private not in str(exc), f"typed admission {label} leaked private path")
        else:
            raise Fail(f"typed admission {label} accepted private path")

    try:
        Path.resolve = private_resolve
        reject("repo_relative fault", lambda: validator.repo_relative(validator.CONTRACT),
               "typed admission artifact path missing, unreadable, or escapes repository")
    finally:
        Path.resolve = original_resolve

    reject("external path", lambda: validator.repo_relative(Path(tempfile.gettempdir()) / private),
           "typed admission artifact path missing, unreadable, or escapes repository")
    with guarded_temporary_directory(".tmp-typed-private-ref-", TMP_PARENT) as raw:
        missing = Path(raw) / (private + ".json")
        ref = missing.relative_to(ROOT).as_posix()
        reject("missing canonical ref", lambda: validator.canonical_repo_file_ref(ref, "negative.private"),
               "negative.private artifact missing or escapes repository")
    original_is_file = Path.is_file

    def private_is_file(_path):
        raise OSError(private)

    try:
        Path.is_file = private_is_file
        reject("canonical ref stat", lambda: validator.canonical_repo_file_ref(
            VALIDATOR.relative_to(ROOT).as_posix(), "negative.private"),
            "negative.private artifact missing or escapes repository")
    finally:
        Path.is_file = original_is_file
    require(validator.repo_relative(validator.CONTRACT) == validator.CONTRACT.relative_to(ROOT),
            "typed admission repo_relative positive failed after private fault")
    print("PASS: typed admission private path/ref errors and exception contexts suppressed")



def prove_private_typed_admission_import_errors(validator: object) -> None:
    """Real typed module loader hides private implementation errors."""
    original = importlib.util.module_from_spec
    private = "SYNTHETIC_PRIVATE_TYPED_IMPORT_CANARY"
    for error_type in (OSError, RuntimeError, TypeError):
        def private_import(_spec):
            raise error_type(private)

        try:
            importlib.util.module_from_spec = private_import
            try:
                validator.load_module(VALIDATOR, "memory_os_typed_private_import_probe")
            except validator.Fail as exc:
                require(str(exc) == "typed admission module import unavailable"
                        and exc.__suppress_context__ and exc.__cause__ is None
                        and private not in str(exc),
                        "typed admission import leaked private exception")
            else:
                raise Fail("typed admission private module import fault accepted")
        finally:
            importlib.util.module_from_spec = original
    module = validator.load_module(VALIDATOR, "memory_os_typed_private_import_positive")
    require(callable(getattr(module, "main", None)),
            "typed admission canonical module import positive failed")
    print("PASS: typed admission private module import faults and canonical positive")



def prove_pinned_typed_admission_module_import(validator: object) -> None:
    """A replaced parent cannot redirect a module after its source FD was checked."""
    original_spec = importlib.util.spec_from_file_location
    with tempfile.TemporaryDirectory(prefix=".typed-admission-import-", dir=ROOT) as raw:
        sandbox = Path(raw)
        parent = sandbox / "trusted"
        parent.mkdir()
        source = parent / "module.py"
        parked = sandbox / "parked"
        redirected = sandbox / "redirected"
        redirected.mkdir()
        canary = redirected / "module.py"
        source.write_text("VALUE = 'pinned'\n", encoding="utf-8")
        canary.write_text("raise RuntimeError('PRIVATE_TYPED_MODULE_SWAP_CANARY')\n", encoding="utf-8")
        require(validator.load_module(source, "typed_pinned_positive").VALUE == "pinned",
                "typed module pinned import positive failed")
        swapped = False

        def swap_after_read(name, location, *args, **kwargs):
            nonlocal swapped
            if not swapped and Path(location) == source:
                swapped = True
                parent.rename(parked)
                parent.symlink_to(redirected, target_is_directory=True)
            return original_spec(name, location, *args, **kwargs)

        try:
            importlib.util.spec_from_file_location = swap_after_read
            loaded = validator.load_module(source, "typed_pinned_swap")
            require(swapped and loaded.VALUE == "pinned",
                    "typed module import executed redirected parent source")
            require(canary.read_text(encoding="utf-8") ==
                    "raise RuntimeError('PRIVATE_TYPED_MODULE_SWAP_CANARY')\n",
                    "typed module import changed redirected canary")
        finally:
            importlib.util.spec_from_file_location = original_spec
    require(callable(getattr(validator.load_module(VALIDATOR, "typed_pinned_restored"),
                             "main", None)), "typed module import canonical restoration failed")
    print("PASS: typed admission module import executes descriptor-pinned source after parent swap")


def prove_private_typed_append_lock_metadata(validator: object) -> None:
    """Materialized lock metadata errors cannot disclose filesystem exception details."""
    private = "SYNTHETIC_PRIVATE_TYPED_LOCK_CANARY"
    original_symlink, original_exists = Path.is_symlink, Path.exists
    original_file, original_resolve = Path.is_file, Path.resolve

    def fault(_path, *args, **kwargs):
        raise OSError(private)

    for mode, expected in (
        ("symlink", "typed non-resurrection append lock metadata unavailable"),
        ("exists", "typed non-resurrection append lock metadata unavailable"),
        ("is_file", "typed non-resurrection materialized append lock is unreadable"),
        ("resolve", "typed non-resurrection materialized append lock is unreadable"),
    ):
        try:
            if mode == "symlink":
                Path.is_symlink = fault
            elif mode == "exists":
                Path.exists = fault
            elif mode == "is_file":
                Path.exists = lambda _path: True
                Path.is_file = fault
            else:
                Path.exists = lambda _path: True
                Path.is_file = lambda _path: True
                Path.resolve = fault
            try:
                validator.enforce_runtime_authorities()
            except validator.Fail as exc:
                require(str(exc) == expected and exc.__suppress_context__
                        and exc.__cause__ is None and private not in str(exc),
                        "typed admission lock " + mode + " leaked private metadata")
            else:
                raise Fail("typed admission lock " + mode + " metadata fault accepted")
        finally:
            Path.is_symlink, Path.exists = original_symlink, original_exists
            Path.is_file, Path.resolve = original_file, original_resolve
    validator.enforce_runtime_authorities()
    print("PASS: typed append lock four private metadata faults and canonical positive")


def main() -> int:
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    with guarded_temporary_directory(".tmp-typed-path-parent-negative-", TMP_PARENT) as raw:
        sandbox = Path(raw)
        link = sandbox / "redirect"
        link.symlink_to(sandbox, target_is_directory=True)
        before = sorted(p.name for p in sandbox.iterdir())
        try:
            with guarded_temporary_directory(".tmp-must-not-create-", link):
                raise Fail("typed contract path symlinked temp parent accepted")
        except Fail as exc:
            require(str(exc) == "typed contract path temp ancestor missing or symlinked",
                    f"typed contract path parent rejected at wrong boundary: {exc}")
        else:
            raise Fail("typed contract path symlinked temp parent accepted")
        require(sorted(p.name for p in sandbox.iterdir()) == before,
                "typed contract path symlinked temp parent published a child")
    print("PASS: typed contract path fixture parent symlink rejected before creation")
    prove_parent_swap_during_mkdir_rejected()
    prove_child_substitution_before_cleanup_rejected()
    prove_child_swap_during_cleanup_preserves_unowned_data()
    prove_nested_swap_during_cleanup_preserves_unowned_data()
    prove_file_swap_before_unlink_rejected()
    validator = load_validator()
    prove_private_typed_admission_paths(validator)
    prove_private_typed_admission_import_errors(validator)
    prove_pinned_typed_admission_module_import(validator)
    prove_private_typed_append_lock_metadata(validator)
    canonical = "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py"
    accepted = validator.canonical_repo_file_ref(canonical, "negative.canonical")
    require(accepted == ROOT / canonical, "canonical in-repository authority ref did not resolve exactly")
    print("PASS accept: canonical repository-relative authority ref")

    expect_rejected(validator, "absolute in-repository authority ref", lambda: validator.canonical_repo_file_ref(str(ROOT / canonical), "negative.absolute"))
    expect_rejected(validator, "parent traversal authority ref", lambda: validator.canonical_repo_file_ref("scripts/../scripts/validate-memory-os-backup-restore-non-resurrection-admission.py", "negative.parent"))

    with guarded_temporary_directory(".tmp-non-resurrection-path-negative-", TMP_PARENT) as fixture_tmp:
        fixture_dir = Path(fixture_tmp)
        with tempfile.TemporaryDirectory(prefix="memory-os-non-resurrection-path-negative-") as outside_tmp:
            outside = Path(outside_tmp) / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            link = fixture_dir / "escaped-authority.json"
            loop = fixture_dir / "loop-authority.json"

            link.symlink_to(outside)
            ref = link.relative_to(ROOT).as_posix()
            expect_rejected(validator, "repo-local symlink escaping repository", lambda: validator.canonical_repo_file_ref(ref, "negative.symlink"))

            loop.symlink_to(loop.name)
            loop_ref = loop.relative_to(ROOT).as_posix()
            expect_rejected(validator, "repo-local authority symlink loop", lambda: validator.canonical_repo_file_ref(loop_ref, "negative.symlinkLoop"))

    reject_typed_writer_cli_substitutions(validator)
    reject_typed_writer_substitution(validator)

    print("Memory OS backup/restore non-resurrection contract path negative suite PASS")
    print("absolute authority aliases accepted: false")
    print("parent traversal authority aliases accepted: false")
    print("repository-escaping authority symlinks accepted: false")
    print("authority symlink loops accepted: false")
    print("typed writer CLI authority substitutions accepted: false")
    print("repository-contained generation recovery writer substitution accepted: false")
    print("non-domain authority resolution exceptions leaked: false")
    print("canonical authorities mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE NON-RESURRECTION CONTRACT PATH NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
