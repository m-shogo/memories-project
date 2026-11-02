#!/usr/bin/env python3
"""Prove generation-evidence reconcile fails closed and rolls back derived authority."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import secrets
import shutil
import stat
import sys
import tempfile
import weakref
from contextlib import contextmanager
from pathlib import Path
from typing import Callable
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_REL = Path("scripts/reconcile-memory-os-backup-restore-generation-evidence.py")
RECONCILER = ROOT / RECONCILER_REL
MAX_RECONCILER_SOURCE_BYTES = 1024 * 1024
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CANONICAL = {
    "CONTRACT": ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
    "REGISTRY": ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "GEN_REGISTRY": ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "OBJECTIVES_REGISTRY": ROOT / "contracts/operations/recovery-objectives-registry.v1.json",
    "DRILL_REGISTRY": ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json",
    "BINDING": ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json",
    "STATUS": ROOT / "contracts/operations/production-operability-status.json",
}
MUTATED = ("CONTRACT", "REGISTRY", "BINDING", "STATUS")


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


@contextmanager
def _pinned_temporary_directory(*, prefix: str, parent: Path):
    # Pin every ancestor by descriptor: the checked pathname may be swapped
    # before mkdir, but the new child must stay beneath the opened directory.
    try:
        relative = parent.relative_to(ROOT)
    except ValueError as exc:
        raise Fail("reconcile negative temp parent escapes repository") from exc
    require(ROOT.is_dir() and not ROOT.is_symlink(),
            "reconcile negative repository root missing or symlinked")
    require(
        hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY")
        and shutil.rmtree.avoids_symlink_attacks,
        "reconcile negative pinned fixture directory unsupported",
    )
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        fd = os.open(ROOT, flags)
    except OSError as exc:
        raise Fail(f"reconcile negative cannot pin repository root: {exc}") from exc
    try:
        root_entry = ROOT.lstat()
        root_open = os.fstat(fd)
        require(
            stat.S_ISDIR(root_entry.st_mode)
            and (root_entry.st_dev, root_entry.st_ino) == (root_open.st_dev, root_open.st_ino),
            "reconcile negative repository root identity drift",
        )
        cursor = ROOT
        for part in relative.parts:
            cursor = cursor / part
            require(cursor.is_dir() and not cursor.is_symlink(),
                    "reconcile negative temp ancestor missing or symlinked")
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
            entry = cursor.lstat()
            opened = os.fstat(fd)
            require(
                stat.S_ISDIR(entry.st_mode)
                and (entry.st_dev, entry.st_ino) == (opened.st_dev, opened.st_ino),
                "reconcile negative temp ancestor identity drift",
            )
        require(
            parent.resolve(strict=True) == ROOT.resolve(strict=True) / relative,
            "reconcile negative temp parent canonical resolution drift",
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
            raise Fail("reconcile negative temp child exclusive creation exhausted")
        created = os.stat(name, dir_fd=fd, follow_symlinks=False)
        try:
            current = parent.lstat()
            require(
                stat.S_ISDIR(current.st_mode)
                and (current.st_dev, current.st_ino) == (pinned.st_dev, pinned.st_ino),
                "reconcile negative temp parent identity drift after creation",
            )
            require(stat.S_ISDIR(created.st_mode),
                    "reconcile negative temp child is not a directory")
            yield str(parent / name)
        finally:
            current_child = os.stat(name, dir_fd=fd, follow_symlinks=False)
            require(
                stat.S_ISDIR(current_child.st_mode)
                and (current_child.st_dev, current_child.st_ino) == (created.st_dev, created.st_ino),
                "reconcile negative temp child identity drift before cleanup",
            )
            # Descriptor-relative, symlink-resistant cleanup cannot traverse a
            # substituted parent pathname. Child inode drift fails closed.
            shutil.rmtree(name, dir_fd=fd)
    except OSError as exc:
        raise Fail(f"reconcile negative pinned fixture operation failed: {exc}") from exc
    finally:
        os.close(fd)


class _EagerFixtureDirectory:
    """Retain TemporaryDirectory's call-time creation/error and cleanup contract."""

    def __init__(self, manager):
        self._manager = manager
        self.name = manager.__enter__()
        self._finalizer = weakref.finalize(self, manager.__exit__, None, None, None)

    def __enter__(self):
        require(self._finalizer.alive, "reconcile negative pinned fixture already closed")
        return self.name

    def __exit__(self, exc_type, exc, traceback):
        if self._finalizer.alive:
            self._finalizer.detach()
            return self._manager.__exit__(exc_type, exc, traceback)
        return False

    def cleanup(self):
        if self._finalizer.alive:
            self._finalizer()


def guarded_temporary_directory(*, prefix: str, parent: Path):
    # Dependent negative wrappers translate domain Fail at call time.
    return _EagerFixtureDirectory(_pinned_temporary_directory(prefix=prefix, parent=parent))


def prove_parent_swap_during_mkdir_rejected() -> None:
    # Deterministically substitute only an exclusively owned sandbox parent
    # after descriptor pinning and before the actual mkdir operation.
    with guarded_temporary_directory(prefix=".tmp-generation-evidence-race-control-", parent=TMP_PARENT) as raw:
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
            if not switched and str(name).startswith(".tmp-generation-evidence-race-") and dir_fd is not None:
                switched = True
                checked.rename(parked)
                checked.symlink_to(escaped, target_is_directory=True)
            original_mkdir(name, mode=mode, dir_fd=dir_fd)

        os.mkdir = swap_before_mkdir
        try:
            try:
                with guarded_temporary_directory(prefix=".tmp-generation-evidence-race-", parent=checked):
                    raise Fail("reconcile negative parent swap accepted")
            except Fail as exc:
                require(str(exc) == "reconcile negative temp parent identity drift after creation",
                        f"reconcile negative parent swap rejected at wrong boundary: {exc}")
            else:
                raise Fail("reconcile negative parent swap accepted")
        finally:
            os.mkdir = original_mkdir

        require(switched, "reconcile negative parent swap probe did not reach pinned mkdir")
        require(checked.is_symlink() and checked.resolve() == escaped.resolve(),
                "reconcile negative parent swap did not install isolated redirect")
        require((parked.stat().st_dev, parked.stat().st_ino) == original_identity,
                "reconcile negative parent swap changed pinned directory identity")
        require(not list(escaped.iterdir()), "reconcile negative parent swap published through redirect")
        require(not list(parked.iterdir()), "reconcile negative parent swap left pinned child")
        # The enclosing owned context removes all synthetic children; no
        # unconditional unlink or rename of mutable fixture paths is needed.
    print("PASS: reconcile negative parent swap during mkdir stays pinned and fails closed")


def prove_child_substitution_before_cleanup_rejected() -> None:
    # An owned temporary child must not be removed after its name is
    # substituted, even if the replacement points at another directory.
    with guarded_temporary_directory(prefix=".tmp-generation-evidence-child-control-", parent=TMP_PARENT) as raw:
        sandbox = Path(raw)
        replacement = sandbox / "unowned-replacement"
        replacement.mkdir()
        parked = sandbox / "original-owned-child"
        try:
            with guarded_temporary_directory(prefix=".tmp-generation-evidence-child-identity-", parent=sandbox) as inner:
                child = Path(inner)
                child.rename(parked)
                child.symlink_to(replacement, target_is_directory=True)
        except Fail as exc:
            require(str(exc) == "reconcile negative temp child identity drift before cleanup",
                    f"reconcile negative substituted child rejected at wrong boundary: {exc}")
        else:
            raise Fail("reconcile negative substituted child cleanup accepted")
        require(child.is_symlink() and parked.is_dir() and replacement.is_dir(),
                "reconcile negative substituted child proof did not preserve isolated fixtures")
        require(not list(replacement.iterdir()),
                "reconcile negative substituted child cleanup touched unowned replacement")
        # The outer pinned fixture owns the whole sandbox and safely removes
        # the intentionally retained substituted link and original child.
    print("PASS: reconcile negative substituted child inode rejects cleanup without deleting replacement")


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def require_reconciler_identity() -> None:
    require(RECONCILER == ROOT / RECONCILER_REL and RECONCILER.is_file()
            and not RECONCILER.is_symlink()
            and RECONCILER.resolve(strict=True) == RECONCILER,
            "generation evidence reconciler source authority drift")


def pinned_reconciler_source() -> bytes:
    """Bind reviewed reconciler bytes to owned directory/file descriptors, not a mutable path."""
    require_reconciler_identity()
    require(all(type(getattr(os, name, None)) is int and getattr(os, name) > 0
                for name in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")),
            "generation evidence reconciler pinned import platform unsafe")
    owned: list[int] = []
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        parent_fd = os.open(ROOT, directory_flags)
        require(type(parent_fd) is int and parent_fd >= 0, "reconciler directory descriptor invalid")
        owned.append(parent_fd)
        for part in RECONCILER_REL.parts[:-1]:
            parent_fd = os.open(part, directory_flags, dir_fd=parent_fd)
            require(type(parent_fd) is int and parent_fd >= 0, "reconciler directory descriptor invalid")
            owned.append(parent_fd)
        before_parents = [os.fstat(fd) for fd in owned]
        parent_identity = lambda value: (
            value.st_dev, value.st_ino, value.st_mode, value.st_ctime_ns
        )
        require(all(stat.S_ISDIR(item.st_mode) and not (item.st_mode & 0o022)
                    for item in before_parents), "reconciler parent directory unsafe")
        source_fd = os.open(
            RECONCILER_REL.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=parent_fd,
        )
        require(type(source_fd) is int and source_fd >= 0, "reconciler source descriptor invalid")
        owned.append(source_fd)
        before = os.fstat(source_fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and not (before.st_mode & 0o022)
                and 0 < before.st_size <= MAX_RECONCILER_SOURCE_BYTES,
                "reconciler source type/size unsafe")
        chunks: list[bytes] = []
        remaining = MAX_RECONCILER_SOURCE_BYTES + 1
        while remaining:
            chunk = os.read(source_fd, remaining)
            require(type(chunk) is bytes, "reconciler source read type invalid")
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        source = b"".join(chunks)
        after = os.fstat(source_fd)
        leaf = os.stat(RECONCILER_REL.name, dir_fd=parent_fd, follow_symlinks=False)
        identity = lambda item: (
            item.st_dev, item.st_ino, item.st_mode, item.st_size,
            item.st_mtime_ns, item.st_ctime_ns
        )
        require(len(source) <= MAX_RECONCILER_SOURCE_BYTES
                and len(source) == before.st_size
                and identity(before) == identity(after) == identity(leaf),
                "reconciler source changed during read")
        for index, fd in enumerate(owned[:-1]):
            current = os.fstat(fd)
            lexical = ROOT if index == 0 else ROOT.joinpath(*RECONCILER_REL.parts[:index])
            visible = os.lstat(lexical)
            require(stat.S_ISDIR(visible.st_mode)
                    and parent_identity(before_parents[index])
                    == parent_identity(current) == parent_identity(visible),
                    "reconciler parent changed during read")
        require_reconciler_identity()
        require(identity(RECONCILER.stat()) == identity(after),
                "reconciler pathname changed during read")
        return source
    finally:
        primary = sys.exc_info()[0] is not None
        failed = False
        for fd in reversed(owned):
            try:
                os.close(fd)
            except Exception:
                failed = True
        if failed and not primary:
            raise Fail("reconciler descriptor cleanup failed") from None


def load_reconciler():
    source = pinned_reconciler_source()
    spec = importlib.util.spec_from_file_location(
        "memory_os_generation_evidence_reconcile_negative", RECONCILER,
    )
    require(spec is not None and spec.loader is not None,
            "cannot load generation evidence reconciler")
    module = importlib.util.module_from_spec(spec)
    # Execute only the pinned snapshot, never a loader pathname re-open.
    exec(compile(source, str(RECONCILER), "exec"), module.__dict__)
    return module


def prove_pinned_reconciler_import() -> None:
    """A post-capture parent swap cannot redirect the negative harness importer."""
    global ROOT, RECONCILER
    original_root, original_reconciler = ROOT, RECONCILER
    original_spec = importlib.util.spec_from_file_location
    with guarded_temporary_directory(prefix=".tmp-generation-reconciler-pin-", parent=TMP_PARENT) as tmpdir:
        fixture = Path(tmpdir)
        parent = fixture / "scripts"
        parent.mkdir()
        source = parent / RECONCILER_REL.name
        source.write_text("SOURCE_MARKER = 'reviewed'\n", encoding="utf-8")
        redirected = fixture / "redirected"
        redirected.mkdir()
        canary = redirected / source.name
        canary.write_text("raise RuntimeError('PRIVATE_RECONCILER_IMPORT_SWAP_CANARY')\n",
                          encoding="utf-8")
        parked = fixture / "parked-scripts"
        ROOT, RECONCILER = fixture, source
        try:
            require(load_reconciler().SOURCE_MARKER == "reviewed",
                    "generation reconciler pinned import positive control failed")
            source.write_bytes(b"")
            try:
                try:
                    load_reconciler()
                except Fail as exc:
                    require(str(exc) == "reconciler source type/size unsafe",
                            "empty generation reconciler source wrong rejection")
                else:
                    raise Fail("empty generation reconciler source accepted")
            finally:
                source.write_text("SOURCE_MARKER = 'reviewed'\n", encoding="utf-8")
            require(load_reconciler().SOURCE_MARKER == "reviewed",
                    "generation reconciler source not restored after empty-file negative")
            for flag in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK"):
                original_flag = getattr(os, flag)
                for invalid in (0, False, "inert"):
                    setattr(os, flag, invalid)
                    try:
                        try:
                            load_reconciler()
                        except Fail as exc:
                            require(str(exc) == "generation evidence reconciler pinned import platform unsafe",
                                    "generation reconciler inert " + flag + " wrong rejection")
                        else:
                            raise Fail("generation reconciler accepted inert " + flag)
                    finally:
                        setattr(os, flag, original_flag)
            source.chmod(0o666)
            expect_domain_fail("writable generation reconciler source",
                               load_reconciler, Fail)
            source.chmod(0o644)
            swapped = False

            def swap_after_capture(name, location, *args, **kwargs):
                nonlocal swapped
                if not swapped and Path(location) == source:
                    swapped = True
                    parent.rename(parked)
                    parent.symlink_to(redirected, target_is_directory=True)
                return original_spec(name, location, *args, **kwargs)

            importlib.util.spec_from_file_location = swap_after_capture
            loaded = load_reconciler()
            require(swapped and loaded.SOURCE_MARKER == "reviewed",
                    "generation reconciler imported redirected source")
            require(canary.read_text(encoding="utf-8").startswith("raise RuntimeError"),
                    "generation reconciler redirected canary mutated")
        finally:
            importlib.util.spec_from_file_location = original_spec
            ROOT, RECONCILER = original_root, original_reconciler
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)
    print("PASS: generation evidence negative reconciler importer pinned after parent swap")


def expect_domain_fail(name: str, action: Callable[[], object], fail_type: type[BaseException]) -> None:
    try:
        action()
    except fail_type:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def expect_direct_authority_rejected(
    reconciler: object,
    *,
    name: str,
    field: str,
    attribute: str,
    replacement: Path,
    before: dict[Path, bytes],
) -> None:
    original = getattr(reconciler, attribute)
    setattr(reconciler, attribute, replacement)
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require(f"{field} authority drift" in str(exc), f"{name} rejected at wrong boundary: {exc}")
        else:
            raise Fail(f"direct reconciler unexpectedly accepted: {name}")
        for path, expected in before.items():
            require(path.read_bytes() == expected, f"canonical authority mutated while rejecting {name}: {path.name}")
    finally:
        setattr(reconciler, attribute, original)


def prove_strict_generation_json_authority(reconciler: object) -> None:
    """Ambiguous JSON and unsafe inode aliases must never enter reconciliation."""
    canonical_before = {path: (path.read_bytes(), mode(path)) for path in CANONICAL.values()}
    with guarded_temporary_directory(
        prefix=".tmp-generation-evidence-json-strict-", parent=TMP_PARENT,
    ) as tmpdir:
        authority = Path(tmpdir) / "reviewed.json"
        invalid = (
            ("duplicate JSON key", b'{"x":1,"x":2}'),
            ("nested duplicate JSON key", b'{"x":{"a":1,"a":2}}'),
            ("NaN", b'{"x":NaN}'),
            ("Infinity", b'{"x":Infinity}'),
            ("float overflow", b'{"x":1e999}'),
            ("oversized integer", b'{"x":' + b"9" * 129 + b"}"),
            ("oversized JSON authority", b'{"padding":"' + b"x" * reconciler.MAX_REVIEWED_SOURCE_BYTES + b'"}'),
            ("invalid UTF-8", b'{"x":"\\xff"}'.replace(b"\\xff", bytes([255]))),
            ("nonobject JSON", b'[1,2]'),
        )
        for label, payload in invalid:
            authority.write_bytes(payload)
            expect_domain_fail(
                f"generation evidence {label}", lambda: reconciler.load(authority),
                reconciler.Fail,
            )
        authority.write_bytes(b'{"reviewed":true,"count":12}')
        require(reconciler.load(authority) == {"reviewed": True, "count": 12},
                "generation evidence strict JSON positive control rejected")

        hardlink = Path(tmpdir) / "unreviewed-hardlink.json"
        os.link(authority, hardlink)
        try:
            expect_domain_fail("hardlinked JSON authority",
                               lambda: reconciler.load(authority), reconciler.Fail)
        finally:
            hardlink.unlink()
        original_mode = mode(authority)
        authority.chmod(0o666)
        try:
            expect_domain_fail("writable JSON authority",
                               lambda: reconciler.load(authority), reconciler.Fail)
        finally:
            authority.chmod(original_mode)
        require(reconciler.load(authority) == {"reviewed": True, "count": 12},
                "generation evidence JSON positive control drifted after negatives")
    for path, (expected, expected_mode) in canonical_before.items():
        require(path.read_bytes() == expected and mode(path) == expected_mode,
                "strict JSON negatives changed protected generation authority")
    print("PASS: generation evidence pinned JSON, strict parser, bounds and inode guards (11 negatives)")


def prove_generation_json_parent_swap(reconciler: object) -> None:
    """A parent swapped at JSON leaf open must not redirect reviewed bytes."""
    with guarded_temporary_directory(
        prefix=".tmp-generation-evidence-json-parent-", parent=TMP_PARENT,
    ) as tmpdir:
        root = Path(tmpdir)
        parent = root / "reviewed"
        parent.mkdir()
        authority = parent / "authority.json"
        authority.write_bytes(b'{"reviewed":true}')
        redirected = root / "redirected"
        redirected.mkdir()
        canary = redirected / authority.name
        canary.write_bytes(b'{"reviewed":false,"private":"CANARY"}')
        parked = root / "reviewed-held"
        original_open = reconciler.os.open
        swapped: list[bool] = []

        def swap_at_leaf(candidate, flags, *args, **kwargs):
            if (candidate == authority.name and kwargs.get("dir_fd") is not None
                    and not swapped):
                parent.rename(parked)
                parent.symlink_to(redirected, target_is_directory=True)
                swapped.append(True)
            return original_open(candidate, flags, *args, **kwargs)

        reconciler.os.open = swap_at_leaf
        try:
            expect_domain_fail(
                "generation evidence JSON parent swap",
                lambda: reconciler.load(authority), reconciler.Fail,
            )
        finally:
            reconciler.os.open = original_open
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)
        require(swapped == [True], "generation JSON parent-swap boundary not reached")
        require(authority.read_bytes() == b'{"reviewed":true}'
                and canary.read_bytes() == b'{"reviewed":false,"private":"CANARY"}',
                "generation JSON parent-swap mutated reviewed or redirected bytes")
        require(reconciler.load(authority) == {"reviewed": True},
                "generation JSON parent-swap positive control not restored")
    print("PASS: generation evidence JSON parent swap rejected at pinned leaf open")


def prove_direct_authority_identity(reconciler: object) -> None:
    before = {path: path.read_bytes() for path in CANONICAL.values()}
    cases = (
        ("generation evidence contract substitution", "generation evidence contract", "CONTRACT", reconciler.STATUS),
        ("generation evidence registry substitution", "generation evidence registry", "REGISTRY", reconciler.BINDING),
        ("environment generation registry substitution", "environment generation registry", "GEN_REGISTRY", reconciler.REGISTRY),
        ("recovery objectives registry substitution", "recovery objectives registry", "OBJECTIVES_REGISTRY", reconciler.DRILL_REGISTRY),
        ("drill request registry substitution", "drill request registry", "DRILL_REGISTRY", reconciler.OBJECTIVES_REGISTRY),
        ("generation binding contract substitution", "generation binding contract", "BINDING", reconciler.CONTRACT),
        ("generation writer substitution", "generation evidence writer", "WRITER", reconciler.VALIDATOR),
        ("generation validator substitution", "generation evidence validator", "VALIDATOR", reconciler.OPERABILITY_VALIDATOR),
        ("generation binding validator substitution", "generation binding validator", "BINDING_VALIDATOR", reconciler.VALIDATOR),
        ("operability validator substitution", "operability validator", "OPERABILITY_VALIDATOR", reconciler.BINDING_VALIDATOR),
        ("production status substitution", "production operability status", "STATUS", reconciler.CONTRACT),
    )
    for name, field, attribute, replacement in cases:
        expect_direct_authority_rejected(
            reconciler,
            name=name,
            field=field,
            attribute=attribute,
            replacement=replacement,
            before=before,
        )
    print(f"PASS boundary: direct generation-evidence data/writer/validator substitutions rejected: {len(cases)}")


def prove_pinned_generation_writer_import(reconciler: object) -> None:
    """A writer path swap after byte capture must not execute redirected code."""
    original_root, original_writer = reconciler.ROOT, reconciler.WRITER
    original_spec = reconciler.importlib.util.spec_from_file_location
    with guarded_temporary_directory(prefix=".tmp-generation-writer-pin-", parent=TMP_PARENT) as tmpdir:
        root = Path(tmpdir)
        parent = root / "scripts"
        parent.mkdir()
        writer = parent / reconciler.WRITER_REL.name
        writer.write_text("SOURCE_MARKER = 'reviewed'\n", encoding="utf-8")
        redirected = root / "redirected"
        redirected.mkdir()
        canary = redirected / writer.name
        canary.write_text("raise RuntimeError('PRIVATE_GENERATION_WRITER_SWAP_CANARY')\n",
                          encoding="utf-8")
        parked = root / "parked-scripts"
        reconciler.ROOT, reconciler.WRITER = root, writer
        try:
            require(reconciler.load_writer().SOURCE_MARKER == "reviewed",
                    "generation writer pinned import positive control failed")
            writer.chmod(0o666)
            expect_domain_fail("writable generation writer", reconciler.load_writer, reconciler.Fail)
            writer.chmod(0o644)
            parent.chmod(0o777)
            try:
                expect_domain_fail("writable generation writer parent", reconciler.load_writer,
                                   reconciler.Fail)
            finally:
                parent.chmod(0o755)
            original_read = reconciler.os.read
            raced = False

            def swap_during_read(fd, remaining):
                nonlocal raced
                if not raced:
                    raced = True
                    parent.rename(parked)
                    parent.symlink_to(redirected, target_is_directory=True)
                return original_read(fd, remaining)

            reconciler.os.read = swap_during_read
            try:
                expect_domain_fail("mid-read generation writer parent swap",
                                   reconciler.load_writer, reconciler.Fail)
                require(raced, "generation writer mid-read swap negative not exercised")
            finally:
                reconciler.os.read = original_read
                if parent.is_symlink():
                    parent.unlink()
                if parked.exists():
                    parked.rename(parent)
            require(reconciler.load_writer().SOURCE_MARKER == "reviewed",
                    "generation writer positive control failed after parent restore")
            swapped = False

            def swap_after_capture(name, location, *args, **kwargs):
                nonlocal swapped
                if not swapped and Path(location) == writer:
                    swapped = True
                    parent.rename(parked)
                    parent.symlink_to(redirected, target_is_directory=True)
                return original_spec(name, location, *args, **kwargs)

            reconciler.importlib.util.spec_from_file_location = swap_after_capture
            loaded = reconciler.load_writer()
            require(swapped and loaded.SOURCE_MARKER == "reviewed",
                    "generation writer executed redirected pathname")
            require(canary.read_text(encoding="utf-8").startswith("raise RuntimeError"),
                    "generation writer redirected canary mutated")
        finally:
            reconciler.importlib.util.spec_from_file_location = original_spec
            reconciler.ROOT, reconciler.WRITER = original_root, original_writer
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)
    print("PASS: generation evidence writer pinned bytes resist after-capture parent swap")



def prove_atomic_target_metadata_rejection(reconciler: object) -> None:
    """Aliases, hardlinks and writable targets cannot receive staged bytes."""
    canonical_before = {path: (path.read_bytes(), mode(path)) for path in CANONICAL.values()}
    with guarded_temporary_directory(prefix=".tmp-generation-evidence-target-guard-", parent=TMP_PARENT) as tmpdir:
        root = Path(tmpdir)
        target = root / "reviewed.json"
        target.write_text('{"reviewed":true}\\n', encoding="utf-8")
        target.chmod(0o640)
        before, before_mode = target.read_bytes(), mode(target)
        hardlink = root / "hardlink.json"
        os.link(target, hardlink)
        try:
            expect_domain_fail("hardlinked generation evidence authority",
                               lambda: reconciler.write_text(target, '{"synthetic":true}'),
                               reconciler.Fail)
        finally:
            hardlink.unlink()
        alias = root / "alias.json"
        alias.symlink_to(target)
        try:
            expect_domain_fail("symlinked generation evidence authority",
                               lambda: reconciler.write_text(alias, '{"synthetic":true}'),
                               reconciler.Fail)
        finally:
            alias.unlink()
        target.chmod(0o666)
        try:
            expect_domain_fail("writable generation evidence authority",
                               lambda: reconciler.write_text(target, '{"synthetic":true}'),
                               reconciler.Fail)
        finally:
            target.chmod(before_mode)
        redirect = root / "redirect"
        redirect.symlink_to(root, target_is_directory=True)
        try:
            expect_domain_fail("symlinked generation evidence parent",
                               lambda: reconciler.write_text(redirect / target.name, '{"synthetic":true}'),
                               reconciler.Fail)
        finally:
            redirect.unlink()
        require(target.read_bytes() == before and mode(target) == before_mode
                and not list(root.glob(".*.tmp")),
                "generation evidence atomic metadata negatives mutated fixture or staged residue")
    for path, (expected, expected_mode) in canonical_before.items():
        require(path.read_bytes() == expected and mode(path) == expected_mode,
                "generation evidence atomic metadata negatives mutated canonical authority")
    print("PASS: generation evidence atomic target hardlink/symlink/writable-parent guards")



def prove_atomic_write_failure(reconciler: object) -> None:
    canonical_before = {path: (path.read_bytes(), mode(path)) for path in CANONICAL.values()}
    original_replace = reconciler.os.replace

    def reject_replace(source: str | Path, destination: str | Path) -> None:
        raise OSError("synthetic atomic replace rejection")

    with guarded_temporary_directory(prefix=".tmp-generation-evidence-atomic-write-", parent=TMP_PARENT) as tmpdir:
        target = Path(tmpdir) / "generation-evidence-contract.json"
        source = CANONICAL["CONTRACT"]
        shutil.copyfile(source, target)
        target.chmod(0o640)
        fixture_before = target.read_bytes()
        fixture_mode = mode(target)

        reconciler.os.replace = reject_replace
        try:
            try:
                reconciler.write_text(target, fixture_before.decode("utf-8") + " ")
            except reconciler.Fail as exc:
                require("cannot atomically write" in str(exc), f"atomic write rejected at wrong boundary: {exc}")
            else:
                raise Fail("synthetic generation-evidence atomic replace failure unexpectedly accepted")
        finally:
            reconciler.os.replace = original_replace

        require(target.read_bytes() == fixture_before, "atomic replace rejection mutated fixture authority bytes")
        require(mode(target) == fixture_mode, "atomic replace rejection mutated fixture authority mode")
        leftovers = list(target.parent.glob(f".{target.name}.*.tmp"))
        require(not leftovers, f"atomic replace rejection left temporary fixture files: {leftovers}")

    for path, (expected_bytes, expected_mode) in canonical_before.items():
        require(path.read_bytes() == expected_bytes, f"atomic replace rejection mutated canonical authority: {path.name}")
        require(mode(path) == expected_mode, f"atomic replace rejection changed canonical authority mode: {path.name}")
    print("PASS boundary: failed atomic generation-evidence write is fixture-isolated and preserves canonical bytes and modes")


def prove_atomic_cleanup_failure_precedence(reconciler: object) -> None:
    canonical_before = {path: (path.read_bytes(), mode(path)) for path in CANONICAL.values()}
    original_replace = reconciler.os.replace
    original_unlink = reconciler.os.unlink
    with guarded_temporary_directory(prefix=".tmp-generation-evidence-cleanup-", parent=TMP_PARENT) as tmpdir:
        target = Path(tmpdir) / "generation-evidence-cleanup.json"
        target.write_text("{}\\n", encoding="utf-8")
        target.chmod(0o640)
        before_bytes, before_mode = target.read_bytes(), mode(target)
        original_temps = set(target.parent.glob(f".{target.name}.*.tmp"))
        attempted_cleanup = []

        def reject_replace(_source, _destination):
            raise OSError("synthetic primary generation-evidence replace rejection")

        def reject_cleanup(path, *args, **kwargs):
            require(Path(path).parent == target.parent and Path(path).name.startswith(f".{target.name}."),
                    "generation-evidence cleanup targeted an unexpected path")
            attempted_cleanup.append(Path(path))
            raise ValueError("synthetic secondary generation-evidence cleanup rejection")

        try:
            reconciler.os.replace = reject_replace
            reconciler.os.unlink = reject_cleanup
            try:
                reconciler.write_text(target, '{"notPublished": true}\\n')
            except reconciler.Fail as exc:
                require("cannot atomically write" in str(exc),
                        f"generation-evidence cleanup masked primary write failure: {exc}")
                require("synthetic primary generation-evidence replace rejection" in str(exc),
                        "generation-evidence cleanup lost primary diagnostic")
                require("secondary" not in str(exc),
                        "generation-evidence cleanup leaked secondary diagnostic")
            else:
                raise Fail("generation-evidence double-fault write unexpectedly accepted")
        finally:
            reconciler.os.replace = original_replace
            reconciler.os.unlink = original_unlink
            created = set(target.parent.glob(f".{target.name}.*.tmp")) - original_temps
            for path in created:
                original_unlink(path)

        require(len(attempted_cleanup) == 1 and attempted_cleanup[0] in created,
                "generation-evidence secondary cleanup rejection not exercised")
        require(target.read_bytes() == before_bytes and mode(target) == before_mode,
                "generation-evidence cleanup double fault mutated fixture authority")
        require(set(target.parent.glob(f".{target.name}.*.tmp")) == original_temps,
                "generation-evidence cleanup double fault left synthetic temporary authority")

    for path, (expected_bytes, expected_mode) in canonical_before.items():
        require(path.read_bytes() == expected_bytes and mode(path) == expected_mode,
                f"generation-evidence cleanup double fault mutated canonical authority: {path.name}")
    print("PASS boundary: generation-evidence primary atomic failure survives secondary cleanup exception")


def prove_pre_fdopen_fault_releases_retained_descriptor(reconciler: object) -> None:
    canonical_before = {path: (path.read_bytes(), mode(path)) for path in CANONICAL.values()}
    with guarded_temporary_directory(prefix=".tmp-generation-evidence-fd-ownership-", parent=TMP_PARENT) as tmpdir:
        target = Path(tmpdir) / "generation-evidence-fd-ownership.json"
        target.write_text("{}\\n", encoding="utf-8")
        target.chmod(0o640)
        before_bytes, before_mode = target.read_bytes(), mode(target)
        for operation in ("fchmod", "fdopen"):
            original_operation = getattr(reconciler.os, operation)
            captured = []

            def reject(fd, *_args, **kwargs):
                if operation == "fdopen":
                    require(kwargs.get("closefd") is False,
                            "generation-evidence fdopen must retain explicit raw-FD ownership")
                captured.append(fd)
                raise OSError("synthetic generation-evidence " + operation + " rejection")

            setattr(reconciler.os, operation, reject)
            try:
                try:
                    reconciler.write_text(target, before_bytes.decode("utf-8") + " ")
                except reconciler.Fail as exc:
                    require("cannot atomically write" in str(exc),
                            f"generation-evidence {operation} failure wrong class: {exc}")
                else:
                    raise Fail(f"generation-evidence {operation} failure unexpectedly accepted")
            finally:
                setattr(reconciler.os, operation, original_operation)

            require(len(captured) == 1, f"generation-evidence {operation} injection not reached")
            try:
                os.fstat(captured[0])
            except OSError:
                pass
            else:
                os.close(captured[0])
                raise Fail(f"generation-evidence {operation} failure leaked raw descriptor")
            require(target.read_bytes() == before_bytes and mode(target) == before_mode,
                    f"generation-evidence {operation} failure mutated fixture")
            require(not list(target.parent.glob(f".{target.name}.*.tmp")),
                    f"generation-evidence {operation} failure left temp residue")
    for path, (expected_bytes, expected_mode) in canonical_before.items():
        require(path.read_bytes() == expected_bytes and mode(path) == expected_mode,
                f"generation-evidence fd ownership negative changed canonical authority: {path.name}")
    print("PASS boundary: generation-evidence fchmod/fdopen faults close retained raw descriptors")


def prove_mode_preserving_write(reconciler: object) -> None:
    with guarded_temporary_directory(prefix=".tmp-generation-evidence-mode-", parent=TMP_PARENT) as tmpdir:
        target = Path(tmpdir) / "mode-preservation.json"
        target.write_text("{}\n", encoding="utf-8")
        target.chmod(0o640)
        reconciler.write_text(target, '{"preserved": true}\n')
        require(mode(target) == 0o640, f"atomic generation-evidence write changed file mode: {oct(mode(target))}")
        leftovers = list(target.parent.glob(f".{target.name}.*.tmp"))
        require(not leftovers, f"mode-preserving generation-evidence write left temporary files: {leftovers}")
    print("PASS boundary: atomic generation-evidence write preserves existing file mode")


def prove_rollback_attempts_all_restores(reconciler: object) -> None:
    with guarded_temporary_directory(prefix=".tmp-generation-evidence-rollback-", parent=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        originals = {
            tmp / "registry.json": "registry\n",
            tmp / "contract.json": "contract\n",
            tmp / "binding.json": "binding\n",
            tmp / "status.json": "status\n",
        }
        observed: list[Path] = []
        original_write = reconciler.write_text

        def fail_first_restore(path: Path, text: str) -> None:
            observed.append(path)
            if len(observed) == 1:
                raise reconciler.Fail("synthetic first generation-evidence rollback restore rejection")

        reconciler.write_text = fail_first_restore
        try:
            try:
                reconciler.restore_original_text(originals)
            except reconciler.Fail as exc:
                require(
                    "synthetic first generation-evidence rollback restore rejection" in str(exc),
                    f"rollback restore failure reported at wrong boundary: {exc}",
                )
            else:
                raise Fail("synthetic first generation-evidence rollback restore failure unexpectedly accepted")
        finally:
            reconciler.write_text = original_write

        require(observed == list(originals), f"rollback restore failure skipped later authorities: {observed}")
    print("PASS rollback: generation-evidence restore failure still attempts all four authorities")


def prove_post_validator_transport(reconciler) -> None:
    """Three canonical child validators must run bounded, isolated and without raw diagnostics."""
    original_run = reconciler.subprocess.run
    marker = "synthetic-private-generation-post-validator-output"
    seen: list[int | bool | None] = []
    poisoned = {
        "PYTHONPATH": "SYNTHETIC_UNTRUSTED_IMPORT_PATH",
        "PYTHONHOME": "SYNTHETIC_UNTRUSTED_HOME",
        "PYTHONWARNINGS": "SYNTHETIC_UNTRUSTED_WARNINGS",
        "LD_PRELOAD": "SYNTHETIC_UNTRUSTED_LOADER",
        "DYLD_INSERT_LIBRARIES": "SYNTHETIC_UNTRUSTED_DYLD",
        "GIT_CONFIG_GLOBAL": "SYNTHETIC_UNTRUSTED_GIT_CONFIG",
        "SAFE_GENERATION_POST_VALIDATOR_ENV": "preserved",
    }
    targets = (
        (reconciler.BINDING_VALIDATOR, reconciler.BINDING_VALIDATOR_REL, "generation binding validator"),
        (reconciler.VALIDATOR, reconciler.VALIDATOR_REL, "generation evidence validator"),
        (reconciler.OPERABILITY_VALIDATOR, reconciler.OPERABILITY_VALIDATOR_REL, "operability validator"),
    )

    def fake_run(exit_code):
        def run(argv, **kwargs):
            expected_bootstrap = (
                "import os, sys\n"
                "path = sys.argv[1]\n"
                "sys.path.insert(0, os.path.dirname(path))\n"
                "sys.argv[:] = [path]\n"
                "scope = {'__name__': '__main__', '__file__': path, '__package__': None, '__spec__': None}\n"
                "exec(compile(sys.stdin.buffer.read(), path, 'exec'), scope)\n"
            )
            require(argv in [
                [reconciler.sys.executable, "-c", expected_bootstrap, str(path)]
                for path, _, _ in targets
            ], "generation post-validator child target drift")
            require(type(kwargs.get("input")) is bytes
                    and kwargs["input"] == Path(argv[3]).read_bytes(),
                    "generation post-validator pinned source bytes drift")
            require(kwargs.get("cwd") == reconciler.ROOT,
                    "generation post-validator cwd drift")
            require(kwargs.get("stdout") == reconciler.subprocess.DEVNULL
                    and kwargs.get("stderr") == reconciler.subprocess.DEVNULL,
                    "generation post-validator raw diagnostics captured")
            require(kwargs.get("timeout") == 90 and kwargs.get("check") is False,
                    "generation post-validator runtime budget drift")
            child_env = kwargs.get("env")
            require(isinstance(child_env, dict), "generation post-validator child environment missing")
            require(child_env.get("SAFE_GENERATION_POST_VALIDATOR_ENV") == "preserved",
                    "generation post-validator benign environment lost")
            for key in ("PYTHONPATH", "PYTHONHOME", "PYTHONWARNINGS",
                        "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "GIT_CONFIG_GLOBAL"):
                require(key not in child_env, "generation post-validator inherited override: " + key)
            require(child_env == {
                key: value for key, value in reconciler.os.environ.items()
                if not key.startswith(("PYTHON", "LD_", "DYLD_", "GIT_"))
            }, "generation post-validator child environment authority drift")
            seen.append(exit_code)
            return subprocess.CompletedProcess(argv, exit_code, stdout=marker, stderr=marker)
        return run

    env_patch = patch.dict(reconciler.os.environ, poisoned)
    env_patch.start()
    try:
        for path, relative, label in targets:
            reconciler.subprocess.run = fake_run(0)
            reconciler.run_post_validator(path, relative, label)
            for code in (1, False, None):
                reconciler.subprocess.run = fake_run(code)
                try:
                    reconciler.run_post_validator(path, relative, label)
                except reconciler.Fail as exc:
                    require(str(exc) == f"{label} failed (raw output withheld)",
                            "generation post-validator failure class drift")
                    require(marker not in str(exc), "generation post-validator leaked private output")
                else:
                    raise Fail("generation post-validator invalid return accepted")
            for failure in (OSError(marker), ValueError(marker), TypeError(marker),
                            subprocess.TimeoutExpired(["synthetic"], 90, output=marker, stderr=marker)):
                def raise_failure(*_args, **_kwargs):
                    raise failure
                reconciler.subprocess.run = raise_failure
                try:
                    reconciler.run_post_validator(path, relative, label)
                except reconciler.Fail as exc:
                    require(str(exc) == f"{label} unavailable or timed out (raw output withheld)",
                            "generation post-validator unavailable class drift")
                    require(marker not in str(exc), "generation post-validator leaked exception details")
                else:
                    raise Fail("generation post-validator unavailable/timeout accepted")
    finally:
        reconciler.subprocess.run = original_run
        env_patch.stop()
    require(seen == [0, 1, False, None] * 3,
            "generation post-validator positive and negative controls incomplete")
    # Self-consistent repository paths are not sufficient execution authority.
    # Neither an unknown label nor a known label paired with an unreviewed file
    # may reach subprocess, even when the file is a valid canonical authority.
    with patch.object(reconciler.subprocess, "run", side_effect=Fail("unreviewed child process executed")):
        for label in ("synthetic unreviewed validator", "generation evidence validator"):
            try:
                reconciler.run_post_validator(reconciler.CONTRACT, reconciler.CONTRACT_REL, label)
            except reconciler.Fail as exc:
                require(str(exc) == "unreviewed generation evidence post-validator",
                        "generation post-validator unreviewed target rejected at wrong boundary")
            else:
                raise Fail("generation post-validator unreviewed repository target accepted")
    print("PASS: generation evidence post-validators use isolated bounded private transport and closed targets")


def main() -> int:
    require(RECONCILER.is_file(), "generation evidence reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    # Positive and symlink-negative controls run before any other fixture write.
    with guarded_temporary_directory(prefix=".tmp-generation-evidence-parent-negative-", parent=TMP_PARENT) as raw:
        sandbox = Path(raw)
        symlink_parent = sandbox / "redirect"
        symlink_parent.symlink_to(sandbox, target_is_directory=True)
        before = sorted(p.name for p in sandbox.iterdir())
        try:
            # Dependent wrappers require the domain error at constructor call time.
            guarded_temporary_directory(prefix=".tmp-must-not-create-", parent=symlink_parent)
        except Fail as exc:
            require(str(exc) == "reconcile negative temp ancestor missing or symlinked",
                    f"reconcile negative parent rejected at wrong boundary: {exc}")
        else:
            raise Fail("reconcile negative symlinked temp parent accepted")
        require(sorted(p.name for p in sandbox.iterdir()) == before,
                "reconcile negative symlinked parent created a child")
    print("PASS: reconcile negative temp parent symlink rejected before creation")
    prove_parent_swap_during_mkdir_rejected()
    prove_child_substitution_before_cleanup_rejected()
    prove_pinned_reconciler_import()
    reconciler = load_reconciler()
    prove_post_validator_transport(reconciler)
    prove_pinned_generation_writer_import(reconciler)

    prove_strict_generation_json_authority(reconciler)
    prove_generation_json_parent_swap(reconciler)
    prove_direct_authority_identity(reconciler)
    prove_atomic_target_metadata_rejection(reconciler)
    prove_atomic_write_failure(reconciler)
    prove_atomic_cleanup_failure_precedence(reconciler)
    prove_pre_fdopen_fault_releases_retained_descriptor(reconciler)
    prove_mode_preserving_write(reconciler)
    prove_rollback_attempts_all_restores(reconciler)

    original_enforcer = reconciler.enforce_runtime_authorities
    original_post_validator = reconciler.run_post_validator
    original_paths = {attr: getattr(reconciler, attr) for attr in CANONICAL}
    try:
        # Production direct invocation remains canonical-only. Repo-contained
        # fixtures are enabled solely inside this negative harness so append-only
        # corruption and rollback can be proved without weakening runtime identity.
        reconciler.enforce_runtime_authorities = lambda: None
        with guarded_temporary_directory(prefix=".tmp-generation-evidence-reconcile-", parent=TMP_PARENT) as tmpdir:
            tmp = Path(tmpdir)
            originals: dict[Path, bytes] = {}
            original_modes: dict[Path, int] = {}
            targets: dict[str, Path] = {}
            for attr, source in CANONICAL.items():
                target = tmp / source.name
                shutil.copyfile(source, target)
                if attr in MUTATED:
                    target.chmod(0o640)
                setattr(reconciler, attr, target)
                originals[target] = target.read_bytes()
                original_modes[target] = mode(target)
                targets[attr] = target

            original_replace = reconciler.os.replace
            replace_labels = {2: "second", 3: "third", 4: "fourth"}
            for reject_at in (2, 3, 4):
                for path, expected in originals.items():
                    path.write_bytes(expected)
                    path.chmod(original_modes[path])

                replace_calls = 0

                def fail_partial_replace(source: str | Path, destination: str | Path, *, _reject_at: int = reject_at) -> None:
                    nonlocal replace_calls
                    replace_calls += 1
                    if replace_calls == _reject_at:
                        raise OSError(f"synthetic {replace_labels[_reject_at]} generation-evidence authority replace rejection")
                    original_replace(source, destination)

                reconciler.os.replace = fail_partial_replace
                try:
                    try:
                        reconciler.main()
                    except reconciler.Fail as exc:
                        require(
                            f"synthetic {replace_labels[reject_at]} generation-evidence authority replace rejection" in str(exc),
                            f"{replace_labels[reject_at]}-replace failure rejected at wrong boundary: {exc}",
                        )
                    else:
                        raise Fail(
                            f"synthetic {replace_labels[reject_at]} generation-evidence authority replace failure unexpectedly accepted"
                        )
                finally:
                    reconciler.os.replace = original_replace

                require(
                    replace_calls >= reject_at + len(MUTATED),
                    f"{replace_labels[reject_at]}-replace rollback did not restore all four authorities: replace calls={replace_calls}",
                )
                for attr in MUTATED:
                    path = targets[attr]
                    require(
                        path.read_bytes() == originals[path],
                        f"{replace_labels[reject_at]}-replace rollback drifted authority bytes: {path.name}",
                    )
                    require(
                        mode(path) == original_modes[path],
                        f"{replace_labels[reject_at]}-replace rollback drifted authority mode: {path.name}",
                    )
                partial_replace_leftovers: list[Path] = []
                for attr in MUTATED:
                    path = targets[attr]
                    partial_replace_leftovers.extend(path.parent.glob(f".{path.name}.*.tmp"))
                require(
                    not partial_replace_leftovers,
                    f"{replace_labels[reject_at]}-replace rollback left temporary generation-evidence authority files: {partial_replace_leftovers}",
                )
                print(
                    f"PASS rollback: {replace_labels[reject_at]} generation-evidence authority replace failure restores all authority bytes and modes"
                )

            corruption_cases = (
                ("registeredEvidenceCount drift", "registeredEvidenceCount", 1),
                ("boolean drillRequestBoundEvidenceCount", "drillRequestBoundEvidenceCount", True),
                ("completeGenerationBoundBackupCount drift", "completeGenerationBoundBackupCount", 1),
                ("completeGenerationBoundRestoreCount drift", "completeGenerationBoundRestoreCount", 1),
                ("boolean productionEquivalentRecoveryCandidateCount", "productionEquivalentRecoveryCandidateCount", True),
                ("productionEvidence boundary drift", "productionEvidence", True),
                ("productionReady boundary drift", "productionReady", True),
            )
            registry_path = targets["REGISTRY"]
            for name, field, invalid_value in corruption_cases:
                for path, expected in originals.items():
                    path.write_bytes(expected)
                payload = json.loads(registry_path.read_text(encoding="utf-8"))
                payload[field] = invalid_value
                registry_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                before = {path: path.read_bytes() for path in originals}
                before_modes = {path: mode(path) for path in originals}
                expect_domain_fail(name, reconciler.main, reconciler.Fail)
                for path, expected in before.items():
                    require(path.read_bytes() == expected, f"reconcile auto-healed corrupt authority: {path.name} during {name}")
                    require(mode(path) == before_modes[path], f"reconcile changed authority mode while rejecting {name}: {path.name}")

            for path, expected in originals.items():
                path.write_bytes(expected)

            observed: list[str] = []

            def fail_only_aggregate(path: Path, expected_relative: Path, label: str) -> None:
                observed.append(label)
                if len(observed) < 3:
                    return
                require(len(observed) == 3, "unexpected extra generation evidence post-validator invocation")
                require(label == "operability validator", "operability validator was not final generation evidence validator")
                raise reconciler.Fail("synthetic generation evidence aggregate operability rejection")

            reconciler.run_post_validator = fail_only_aggregate
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                require("synthetic generation evidence aggregate operability rejection" in str(exc), f"unexpected reconcile failure: {exc}")
            else:
                raise Fail("forced aggregate post-validation failure unexpectedly accepted")

            require(observed == ["generation binding validator", "generation evidence validator", "operability validator"], "generation evidence post-validator order drift")
            for attr in MUTATED:
                path = targets[attr]
                require(path.read_bytes() == originals[path], f"rollback drifted derived authority: {path.name}")
                require(mode(path) == original_modes[path], f"rollback drifted derived authority mode: {path.name}")
            leftovers: list[Path] = []
            for attr in MUTATED:
                path = targets[attr]
                leftovers.extend(path.parent.glob(f".{path.name}.*.tmp"))
            require(not leftovers, f"rollback left temporary generation-evidence authority files: {leftovers}")
    finally:
        reconciler.enforce_runtime_authorities = original_enforcer
        reconciler.run_post_validator = original_post_validator
        for attr, value in original_paths.items():
            setattr(reconciler, attr, value)

    print("PASS reject: corrupt generation append-only authority is never auto-healed by reconcile")
    print("PASS rollback: generation evidence reconcile restores registry/contract/binding/status bytes and modes after aggregate validation failure")
    print("direct generation-evidence data/writer/validator substitutions accepted: false")
    print("non-atomic generation-evidence authority write accepted: false")
    print("generation-evidence authority mode loss accepted: false")
    print("Generation evidence reconcile negative suite PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION EVIDENCE RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
