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
import weakref
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
                    "drill request nested directory identity drift before traversal",
                )
                _remove_pinned_entries(nested_fd, flags)
                after = os.stat(entry_name, dir_fd=directory_fd, follow_symlinks=False)
                require(
                    stat.S_ISDIR(after.st_mode)
                    and (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino),
                    "drill request nested directory identity drift before removal",
                )
                os.rmdir(entry_name, dir_fd=directory_fd)
            finally:
                os.close(nested_fd)
        else:
            after = os.stat(entry_name, dir_fd=directory_fd, follow_symlinks=False)
            require(
                (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino),
                "drill request nested entry identity drift before unlink",
            )
            os.unlink(entry_name, dir_fd=directory_fd)


@contextmanager
def _pinned_temporary_directory(prefix: str, parent: Path):
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
            # Pin the owned child before recursive deletion. A replacement of
            # its name after the identity check must never redirect rmtree
            # into an unowned directory with data.
            child_fd = os.open(name, flags, dir_fd=fd)
            try:
                pinned_child = os.fstat(child_fd)
                require(
                    (pinned_child.st_dev, pinned_child.st_ino) == (created.st_dev, created.st_ino),
                    "drill request temp child identity drift before traversal",
                )
                _remove_pinned_entries(child_fd, flags)
                final_child = os.stat(name, dir_fd=fd, follow_symlinks=False)
                require(
                    stat.S_ISDIR(final_child.st_mode)
                    and (final_child.st_dev, final_child.st_ino) == (created.st_dev, created.st_ino),
                    "drill request temp child identity drift before final removal",
                )
                os.rmdir(name, dir_fd=fd)
            finally:
                os.close(child_fd)
    except OSError as exc:
        raise Fail(f"drill request pinned fixture operation failed: {exc}") from exc
    finally:
        os.close(fd)


class _EagerFixtureDirectory:
    """Retain TemporaryDirectory's call-time creation/error and cleanup contract."""

    def __init__(self, manager):
        self._manager = manager
        self.name = manager.__enter__()
        self._finalizer = weakref.finalize(self, manager.__exit__, None, None, None)

    def __enter__(self):
        require(self._finalizer.alive, "drill request pinned fixture already closed")
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


def prove_child_substitution_before_cleanup_rejected() -> None:
    # An owned temporary child must not be removed after its name is
    # substituted, even if the replacement points at another directory.
    with guarded_temporary_directory(prefix=".tmp-drill-request-child-control-", parent=TMP_PARENT) as raw:
        sandbox = Path(raw)
        replacement = sandbox / "unowned-replacement"
        replacement.mkdir()
        parked = sandbox / "original-owned-child"
        try:
            with guarded_temporary_directory(prefix=".tmp-drill-request-child-identity-", parent=sandbox) as inner:
                child = Path(inner)
                child.rename(parked)
                child.symlink_to(replacement, target_is_directory=True)
        except Fail as exc:
            require(str(exc) == "drill request temp child identity drift before cleanup",
                    f"drill request substituted child rejected at wrong boundary: {exc}")
        else:
            raise Fail("drill request substituted child cleanup accepted")
        require(child.is_symlink() and parked.is_dir() and replacement.is_dir(),
                "drill request substituted child proof did not preserve isolated fixtures")
        require(not list(replacement.iterdir()),
                "drill request substituted child cleanup touched unowned replacement")
        # The outer pinned fixture owns the whole sandbox and safely removes
        # the intentionally retained substituted link and original child.
    print("PASS: drill request substituted child inode rejects cleanup without deleting replacement")


def prove_child_swap_during_cleanup_preserves_unowned_data() -> None:
    # Replace the child name only after the owned inode has been opened.
    # Traversal must stay on the pinned FD; final name drift must fail closed.
    with guarded_temporary_directory(prefix=".tmp-drill-request-cleanup-control-", parent=TMP_PARENT) as raw:
        sandbox = Path(raw)
        replacement = sandbox / "unowned-replacement"
        replacement.mkdir()
        sentinel = replacement / "important.txt"
        sentinel.write_text("preserve me", encoding="utf-8")
        parked = sandbox / "parked-owned-child"
        original_listdir = os.listdir
        switched = False
        try:
            with guarded_temporary_directory(prefix=".tmp-drill-request-cleanup-race-", parent=sandbox) as inner:
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
            require(str(exc) == "drill request temp child identity drift before final removal",
                    f"drill request cleanup race rejected at wrong boundary: {exc}")
        else:
            raise Fail("drill request cleanup race unexpectedly accepted")
        finally:
            os.listdir = original_listdir
        require(switched, "drill request cleanup race never reached pinned child traversal")
        require(child.is_dir() and (child / "important.txt").read_text(encoding="utf-8") == "preserve me",
                "drill request cleanup race deleted unowned replacement data")
        require(parked.is_dir() and not (parked / "owned.txt").exists(),
                "drill request cleanup race did not traverse the pinned owned child")
    print("PASS: drill request cleanup race preserves unowned replacement data")

def prove_nested_swap_during_cleanup_preserves_unowned_data() -> None:
    # A nested directory may be replaced after its FD is opened, just like
    # the fixture root. Recursive traversal must remain pinned to that FD.
    with guarded_temporary_directory(prefix=".tmp-drill-request-nested-control-", parent=TMP_PARENT) as raw:
        sandbox = Path(raw)
        replacement = sandbox / "unowned-nested-replacement"
        replacement.mkdir()
        (replacement / "important.txt").write_text("preserve nested", encoding="utf-8")
        original_listdir = os.listdir
        switched = False
        try:
            with guarded_temporary_directory(prefix=".tmp-drill-request-nested-race-", parent=sandbox) as inner:
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
            require(str(exc) == "drill request nested directory identity drift before removal",
                    f"drill request nested cleanup race rejected at wrong boundary: {exc}")
        else:
            raise Fail("drill request nested cleanup race unexpectedly accepted")
        finally:
            os.listdir = original_listdir
        require(switched, "drill request nested cleanup race never reached pinned nested traversal")
        require((nested / "important.txt").read_text(encoding="utf-8") == "preserve nested",
                "drill request nested cleanup race deleted unowned nested replacement data")
        require(parked.is_dir() and not (parked / "owned.txt").exists(),
                "drill request nested cleanup race did not traverse pinned owned directory")
    print("PASS: drill request nested cleanup race preserves unowned replacement data")

def prove_file_swap_before_unlink_rejected() -> None:
    # A non-directory entry may change between inode checks. Reject the
    # substituted unowned file before unlink and preserve both contents.
    with guarded_temporary_directory(prefix=".tmp-drill-request-unlink-control-", parent=TMP_PARENT) as raw:
        sandbox = Path(raw)
        replacement = sandbox / "unowned-file.txt"
        replacement.write_text("preserve unowned", encoding="utf-8")
        original_stat = os.stat
        checks = 0
        swapped = False
        try:
            with guarded_temporary_directory(prefix=".tmp-drill-request-unlink-race-", parent=sandbox) as inner:
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
            require(str(exc) == "drill request nested entry identity drift before unlink",
                    f"drill request file cleanup race rejected at wrong boundary: {exc}")
        else:
            raise Fail("drill request file cleanup race unexpectedly accepted")
        finally:
            os.stat = original_stat
        require(swapped and checks == 2, "drill request file cleanup race never reached second inode check")
        require(owned.read_text(encoding="utf-8") == "preserve unowned",
                "drill request file cleanup race deleted unowned replacement")
        require(parked.read_text(encoding="utf-8") == "owned fixture",
                "drill request file cleanup race deleted original owned file")
    print("PASS: drill request file unlink race rejects unowned replacement")


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


def prove_negative_subprocess_redaction(validator) -> None:
    """Exercise the actual negative runner without leaking private subprocess data."""
    original_run = validator.subprocess.run
    marker = "synthetic-secret-in-drill-request-negative-log"
    observed = []

    def fake_run(exit_code):
        def run(argv, **kwargs):
            require(argv == [validator.sys.executable, str(validator.NEGATIVE)],
                    "drill request negative runner target drift")
            require(kwargs.get("cwd") == validator.ROOT,
                    "drill request negative runner cwd drift")
            require(kwargs.get("stdout") == validator.subprocess.DEVNULL
                    and kwargs.get("stderr") == validator.subprocess.DEVNULL,
                    "drill request negative runner captured private output")
            require(kwargs.get("timeout") == 120 and kwargs.get("check") is False,
                    "drill request negative runner budget drift")
            observed.append(exit_code)
            return validator.subprocess.CompletedProcess(argv, exit_code, marker, marker)
        return run

    try:
        validator.subprocess.run = fake_run(0)
        validator.run_negative()
        validator.subprocess.run = fake_run(1)
        try:
            validator.run_negative()
        except validator.Fail as exc:
            require(str(exc) == "drill request negative suite failed (raw output withheld)",
                    "drill request negative runner leaked output or lost fixed failure class")
            require(marker not in str(exc), "drill request private marker disclosed")
        else:
            raise Fail("drill request negative subprocess failure accepted")

        for failure in (OSError(marker), validator.subprocess.TimeoutExpired(["synthetic"], 120)):
            def raise_failure(*_args, **_kwargs):
                raise failure
            validator.subprocess.run = raise_failure
            try:
                validator.run_negative()
            except validator.Fail as exc:
                require(str(exc) == "drill request negative suite unavailable or timed out (raw output withheld)",
                        "drill request negative runner leaked exception or lost fixed unavailable class")
                require(marker not in str(exc), "drill request private exception disclosed")
            else:
                raise Fail("drill request negative subprocess unavailable/timeout accepted")
    finally:
        validator.subprocess.run = original_run

    require(observed == [0, 1], "drill request negative runner positive/failure controls missing")
    print("PASS: drill request negative subprocess bounded execution and fixed private failure classes")


def prove_drill_request_json_reader(validator) -> None:
    """Exercise the actual drill planning reader with no protected-authority writes."""
    protected_paths = (validator.CONTRACT, validator.REGISTRY, validator.GEN_REGISTRY, validator.OBJECTIVES_REGISTRY)
    before = tuple(path.read_bytes() for path in protected_paths)
    with guarded_temporary_directory(".tmp-drill-request-json-reader-", TMP_PARENT) as directory:
        path = Path(directory) / "candidate.json"
        positive = b'{"safe":true,"nested":{"count":1}}'
        path.write_bytes(positive)
        require(validator.load(path) == {"safe": True, "nested": {"count": 1}}, "drill request JSON positive control failed")
        cases = (
            ("duplicate root", b'{"safe":true,"safe":false}', "drill request JSON duplicate key refused"),
            ("duplicate nested", b'{"nested":{"a":1,"a":2}}', "drill request JSON duplicate key refused"),
            ("NaN", b'{"number":NaN}', "drill request JSON nonfinite number refused"),
            ("Infinity", b'{"number":Infinity}', "drill request JSON nonfinite number refused"),
            ("negative Infinity", b'{"number":-Infinity}', "drill request JSON nonfinite number refused"),
            ("float overflow", b'{"number":1e999}', "drill request JSON nonfinite number refused"),
            ("large integer", b'{"number":' + b"9" * 5000 + b"}", "drill request JSON integer too large"),
            ("oversized JSON", b'{"data":"' + b"x" * validator.MAX_JSON_BYTES + b'"}', "drill request JSON size limit exceeded"),
            ("invalid UTF-8", b'{"private":"\xff"}', "drill request JSON unreadable or invalid"),
            ("malformed private", b'{"private":"synthetic-secret",', "drill request JSON unreadable or invalid"),
            ("nonobject root", b"[]", "drill request JSON root must be object"),
        )
        def rejected(candidate, expected: str, label: str) -> None:
            try:
                validator.load(candidate)
            except validator.Fail as exc:
                require(str(exc) == expected, f"{label}: wrong drill request JSON rejection boundary")
                require("synthetic-secret" not in str(exc), f"{label}: private marker disclosed")
            else:
                raise Fail(f"{label}: unsafe drill request JSON accepted")
        for label, payload, expected in cases:
            path.write_bytes(payload)
            rejected(path, expected, label)
        path.write_bytes(positive)
        alias = Path(directory) / "alias.json"
        alias.symlink_to(path)
        rejected(alias, "drill request JSON path unsafe", "symlink")
        rejected(Path(directory), "drill request JSON path unsafe", "directory")
        rejected(Path(directory) / "missing.json", "drill request JSON path missing or outside repository", "missing")
        rejected("candidate.json", "drill request JSON path invalid", "non-Path")
        with tempfile.TemporaryDirectory(prefix="memory-os-drill-request-json-canary-") as outside:
            canary = Path(outside) / "canary.json"
            canary.write_bytes(positive)
            escaped = Path(directory) / "escaped.json"
            escaped.symlink_to(canary)
            rejected(escaped, "drill request JSON path missing or outside repository", "external symlink")
            require(canary.read_bytes() == positive, "drill request JSON modified external canary")
        require(path.read_bytes() == positive, "drill request JSON modified positive fixture")
    require(tuple(path.read_bytes() for path in protected_paths) == before, "drill request JSON mutated protected authorities")
    print("PASS: actual drill request JSON reader positive and 16 fail-closed negatives")


def prove_reconciler_bounded_reader(reconciler) -> None:
    """Check no-follow, regular-file and byte limits on the actual reconciler."""
    protected = (reconciler.CONTRACT, reconciler.REGISTRY, reconciler.STATUS)
    before = tuple(path.read_bytes() for path in protected)
    with guarded_temporary_directory(".tmp-drill-reconcile-bounded-reader-", TMP_PARENT) as raw:
        directory = Path(raw)
        candidate = directory / "candidate.json"
        positive = b'{"safe":true}\n'
        candidate.write_bytes(positive)
        require(reconciler.read_text(candidate) == positive.decode("utf-8"),
                "drill reconcile reader positive control failed")

        def rejected(path, expected, label):
            try:
                reconciler.read_text(path)
            except reconciler.Fail as exc:
                require(str(exc) == expected, f"{label}: wrong drill reconcile reader rejection class")
                require("synthetic-secret" not in str(exc), f"{label}: private marker disclosed")
            else:
                raise Fail(f"{label}: unsafe drill reconcile authority accepted")

        candidate.write_bytes(b"x" * (reconciler.MAX_AUTHORITY_BYTES + 1))
        rejected(candidate, "drill request reconcile authority exceeds 1 MiB", "oversized authority")
        candidate.write_bytes(b"{\xff}")
        rejected(candidate, "drill request reconcile authority read invalid or unavailable", "invalid UTF-8")
        candidate.write_bytes(positive)

        alias = directory / "alias.json"
        alias.symlink_to(candidate)
        rejected(alias, "drill request reconcile authority read invalid or unavailable", "symlink")
        rejected(directory, "drill request reconcile authority not regular file", "directory")
        fifo = directory / "fifo.json"
        os.mkfifo(fifo)
        rejected(fifo, "drill request reconcile authority not regular file", "FIFO")

        original_open = reconciler.os.open
        marker = "synthetic-secret-raced-open"
        def raced_open(path, flags, *args, **kwargs):
            if Path(path) == candidate:
                require(flags & reconciler.os.O_NOFOLLOW and flags & reconciler.os.O_NONBLOCK,
                        "drill reconcile reader missing no-follow/nonblocking flags")
                raise OSError(marker)
            return original_open(path, flags, *args, **kwargs)
        try:
            reconciler.os.open = raced_open
            rejected(candidate, "drill request reconcile authority read invalid or unavailable", "raced open")
        finally:
            reconciler.os.open = original_open
        require(reconciler.read_text(candidate) == positive.decode("utf-8"),
                "drill reconcile reader post-race positive control failed")
        require(candidate.read_bytes() == positive, "drill reconcile reader mutated positive fixture")
    require(tuple(path.read_bytes() for path in protected) == before,
            "drill reconcile reader mutated protected authorities")
    print("PASS: drill reconcile reader positive, oversized, UTF-8, symlink, FIFO, directory and raced-open negatives")


def prove_reconciler_strict_json(reconciler) -> None:
    """The reconciler must reject ambiguity before deriving any planning state."""
    protected = (reconciler.CONTRACT, reconciler.REGISTRY, reconciler.STATUS)
    before = tuple(path.read_bytes() for path in protected)
    with guarded_temporary_directory(".tmp-drill-reconcile-strict-json-", TMP_PARENT) as raw:
        candidate = Path(raw) / "authority.json"
        positive = b'{"safe":true,"nested":{"count":1}}'
        candidate.write_bytes(positive)
        require(reconciler.load(candidate) == {"safe": True, "nested": {"count": 1}},
                "drill reconcile strict JSON positive control failed")
        cases = (
            ("duplicate root", b'{"safe":true,"safe":false}', "drill request reconcile JSON duplicate key refused"),
            ("duplicate nested", b'{"nested":{"x":1,"x":2}}', "drill request reconcile JSON duplicate key refused"),
            ("NaN", b'{"number":NaN}', "drill request reconcile JSON nonfinite number refused"),
            ("Infinity", b'{"number":Infinity}', "drill request reconcile JSON nonfinite number refused"),
            ("negative Infinity", b'{"number":-Infinity}', "drill request reconcile JSON nonfinite number refused"),
            ("float overflow", b'{"number":1e999}', "drill request reconcile JSON nonfinite number refused"),
            ("huge integer", b'{"number":' + b"9" * 5000 + b"}", "drill request reconcile JSON integer too large"),
            ("malformed private", b'{"private":"synthetic-secret",', "drill request reconcile JSON invalid or ambiguous"),
            ("nonobject root", b"[]", "drill request reconcile JSON root must be object"),
        )
        for label, payload, expected in cases:
            candidate.write_bytes(payload)
            try:
                reconciler.load(candidate)
            except reconciler.Fail as exc:
                require(str(exc) == expected, f"{label}: wrong drill reconcile JSON rejection")
                require("synthetic-secret" not in str(exc), f"{label}: private JSON leaked")
            else:
                raise Fail(f"{label}: ambiguous drill reconcile JSON accepted")
        candidate.write_bytes(positive)
        require(reconciler.load(candidate) == {"safe": True, "nested": {"count": 1}},
                "drill reconcile strict JSON post-negative positive failed")
        require(candidate.read_bytes() == positive, "drill reconcile JSON reader mutated positive fixture")
    require(tuple(path.read_bytes() for path in protected) == before,
            "drill reconcile strict JSON test mutated protected authorities")
    print("PASS: drill reconcile strict JSON positive and nine ambiguity negatives")


def main() -> int:
    require(WRITER.is_file(), "drill-request writer missing")
    require(VALIDATOR.is_file(), "drill-request validator missing")
    require(RECONCILER.is_file(), "drill-request reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    prove_parent_swap_during_mkdir_rejected()
    prove_child_substitution_before_cleanup_rejected()
    prove_child_swap_during_cleanup_preserves_unowned_data()
    prove_nested_swap_during_cleanup_preserves_unowned_data()
    prove_file_swap_before_unlink_rejected()
    writer = load_module(WRITER, "memory_os_restore_drill_request_writer_load_negative")
    validator = load_module(VALIDATOR, "memory_os_restore_drill_request_load_negative")
    prove_drill_request_json_reader(validator)
    prove_negative_subprocess_redaction(validator)
    reconciler = load_module(RECONCILER, "memory_os_restore_drill_request_reconcile_load_negative")
    prove_reconciler_bounded_reader(reconciler)
    prove_reconciler_strict_json(reconciler)
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
            # Call-time rejection is required by dependent domain wrappers.
            guarded_temporary_directory(".tmp-must-not-create-", link)
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
