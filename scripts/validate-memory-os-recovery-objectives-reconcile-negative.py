#!/usr/bin/env python3
"""Prove recovery-objective reconciliation authority identity, ordering and transactional rollback."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import stat
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Callable, Iterator

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_REL = Path("scripts/reconcile-memory-os-recovery-objectives.py")
RECONCILER = ROOT / RECONCILER_REL
MAX_RECONCILER_SOURCE_BYTES = 1024 * 1024
WORKFLOW = ROOT / ".github/workflows/recovery-objectives-admission.yml"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CONTRACT = ROOT / "contracts/operations/recovery-objectives-admission-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_reconciler_identity() -> None:
    require(RECONCILER == ROOT / RECONCILER_REL and RECONCILER.is_file()
            and not RECONCILER.is_symlink()
            and RECONCILER.resolve(strict=True) == RECONCILER,
            "recovery objective reconciler source authority drift")


def pinned_reconciler_source() -> bytes:
    """Bind reviewed reconciler bytes to owned directory/file descriptors, not a mutable path."""
    require_reconciler_identity()
    require(all(hasattr(os, name) for name in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")),
            "recovery objective reconciler pinned import platform unsafe")
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
                and 0 <= before.st_size <= MAX_RECONCILER_SOURCE_BYTES,
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
        "memory_os_recovery_objectives_reconcile_negative", RECONCILER,
    )
    require(spec is not None and spec.loader is not None,
            "cannot load recovery objective reconciler")
    module = importlib.util.module_from_spec(spec)
    # Execute only the pinned snapshot, never a loader pathname re-open.
    exec(compile(source, str(RECONCILER), "exec"), module.__dict__)
    return module



def prove_pinned_reconciler_import() -> None:
    """The negative harness must execute captured reconciler bytes after a parent swap."""
    global ROOT, RECONCILER
    original_root, original_reconciler = ROOT, RECONCILER
    original_spec = importlib.util.spec_from_file_location
    with tempfile.TemporaryDirectory(prefix=".tmp-objective-reconciler-pin-", dir=TMP_PARENT) as tmpdir:
        fixture = Path(tmpdir)
        parent = fixture / "scripts"
        parent.mkdir()
        source = parent / RECONCILER_REL.name
        source.write_text("SOURCE_MARKER = 'reviewed'\n", encoding="utf-8")
        redirected = fixture / "redirected"
        redirected.mkdir()
        canary = redirected / source.name
        canary.write_text("raise RuntimeError('PRIVATE_OBJECTIVE_RECONCILER_SWAP_CANARY')\n",
                          encoding="utf-8")
        parked = fixture / "parked-scripts"
        ROOT, RECONCILER = fixture, source
        try:
            require(load_reconciler().SOURCE_MARKER == "reviewed",
                    "objective reconciler pinned import positive control failed")
            source.chmod(0o666)
            expect_domain_fail("writable objective reconciler source", load_reconciler, Fail)
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
                    "objective reconciler imported redirected source")
            require(canary.read_text(encoding="utf-8").startswith("raise RuntimeError"),
                    "objective reconciler redirected canary mutated")
        finally:
            importlib.util.spec_from_file_location = original_spec
            ROOT, RECONCILER = original_root, original_reconciler
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)
    print("PASS: recovery objective negative reconciler importer pinned after parent swap")


def expect_domain_fail(name: str, action: Callable[[], object], fail_type: type[BaseException], expected: str | None = None) -> None:
    try:
        action()
    except fail_type as exc:
        if expected is not None and expected not in str(exc):
            raise Fail(f"{name} rejected at wrong boundary") from None
        print(f"PASS reject: {name}")
        return
    except Exception:
        raise Fail(f"{name} leaked non-domain exception") from None
    raise Fail(f"negative case unexpectedly accepted: {name}")


def prove_private_negative_failure_classifier() -> None:
    """Wrong-boundary and unexpected errors must never echo synthetic private data."""
    marker = "PRIVATE_OBJECTIVE_NEGATIVE_CLASSIFIER_CANARY"

    def raise_fault(fault: Exception) -> None:
        raise fault

    for label, fault, expected, diagnostic in (
        ("wrong boundary", Fail(marker), "expected canonical",
         "private classifier rejected at wrong boundary"),
        ("unexpected fault", TypeError(marker), None,
         "private classifier leaked non-domain exception"),
    ):
        captured = io.StringIO()
        with redirect_stdout(captured):
            try:
                expect_domain_fail("private classifier", lambda: raise_fault(fault), Fail, expected)
            except Fail as exc:
                require(str(exc) == diagnostic and exc.__suppress_context__
                        and marker not in str(exc),
                        f"private negative classifier {label} diagnostic drift")
            else:
                raise Fail(f"private negative classifier {label} unexpectedly accepted")
        require(not captured.getvalue(),
                f"private negative classifier {label} emitted public success")
    print("PASS: recovery objective negative classifier private wrong-boundary diagnostics")


def file_mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def assert_canonical_unchanged(
    contract_bytes: bytes,
    status_bytes: bytes,
    label: str,
    contract_mode: int | None = None,
    status_mode: int | None = None,
) -> None:
    require(CONTRACT.read_bytes() == contract_bytes, f"{label} changed canonical recovery objective contract")
    require(STATUS.read_bytes() == status_bytes, f"{label} changed canonical production status")
    if contract_mode is not None:
        require(file_mode(CONTRACT) == contract_mode, f"{label} changed canonical recovery objective contract mode")
    if status_mode is not None:
        require(file_mode(STATUS) == status_mode, f"{label} changed canonical production status mode")


@contextmanager
def isolated_authorities(reconciler: object) -> Iterator[None]:
    relative_paths = (
        reconciler.CONTRACT_REL,
        reconciler.REGISTRY_REL,
        reconciler.WRITER_REL,
        reconciler.VALIDATOR_REL,
        reconciler.OPERABILITY_VALIDATOR_REL,
        reconciler.STATUS_REL,
        Path("scripts/reconcile-memory-os-recovery-objectives.py"),
        Path(".github/workflows/recovery-objectives-admission.yml"),
    )
    originals = {
        name: getattr(reconciler, name)
        for name in ("ROOT", "CONTRACT", "REGISTRY", "WRITER", "VALIDATOR", "OPERABILITY_VALIDATOR", "STATUS")
    }
    with tempfile.TemporaryDirectory(prefix=".tmp-recovery-objective-authorities-", dir=TMP_PARENT) as tmpdir:
        fixture_root = Path(tmpdir)
        for relative in relative_paths:
            source = ROOT / relative
            destination = fixture_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        reconciler.ROOT = fixture_root
        reconciler.CONTRACT = fixture_root / reconciler.CONTRACT_REL
        reconciler.REGISTRY = fixture_root / reconciler.REGISTRY_REL
        reconciler.WRITER = fixture_root / reconciler.WRITER_REL
        reconciler.VALIDATOR = fixture_root / reconciler.VALIDATOR_REL
        reconciler.OPERABILITY_VALIDATOR = fixture_root / reconciler.OPERABILITY_VALIDATOR_REL
        reconciler.STATUS = fixture_root / reconciler.STATUS_REL

        contract_bytes = reconciler.CONTRACT.read_bytes()
        status_bytes = reconciler.STATUS.read_bytes()
        contract_mode = file_mode(reconciler.CONTRACT)
        status_mode = file_mode(reconciler.STATUS)
        try:
            yield
            require(reconciler.CONTRACT.read_bytes() == contract_bytes, "fixture recovery objective contract did not roll back byte-for-byte")
            require(reconciler.STATUS.read_bytes() == status_bytes, "fixture production status did not roll back byte-for-byte")
            require(file_mode(reconciler.CONTRACT) == contract_mode, "fixture recovery objective contract mode did not roll back")
            require(file_mode(reconciler.STATUS) == status_mode, "fixture production status mode did not roll back")
            leftovers = list(reconciler.CONTRACT.parent.glob(".*.tmp"))
            require(not leftovers, f"fixture recovery objective transaction left temporary files: {leftovers}")
        finally:
            for name, value in originals.items():
                setattr(reconciler, name, value)


def validate_atomic_diagnostic_publication() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    required_fragments = (
        "tempfile.mkstemp(",
        "dir=path.parent",
        "existing_mode = path.stat().st_mode & 0o7777 if path.exists() else None",
        "os.fchmod(fd, existing_mode)",
        "handle.flush()",
        "os.fsync(handle.fileno())",
        "os.replace(tmp_name, path)",
        "os.unlink(tmp_name)",
    )
    missing = [fragment for fragment in required_fragments if fragment not in text]
    require(not missing, f"recovery objective diagnostic publication is not crash-safe or mode-preserving: missing {missing}")
    require(
        "path.write_text(json.dumps(value" not in text,
        "recovery objective diagnostic publication regressed to direct write_text",
    )
    print("PASS boundary: recovery objective failure diagnostic publication is crash-safe and mode-preserving")


def prove_private_atomic_write_path_guards(reconciler: object) -> None:
    """Reject external, symlinked and unreviewed targets without touching canaries."""
    with isolated_authorities(reconciler):
        original = reconciler.CONTRACT.read_bytes()
        marker = "PRIVATE_RECOVERY_OBJECTIVE_RECONCILE_WRITE_CANARY"
        with tempfile.TemporaryDirectory(prefix="objective-reconcile-write-external-") as tmp:
            outside = Path(tmp) / "private.json"
            outside.write_text(marker, encoding="utf-8")
            alias = reconciler.ROOT / "objective-write-alias.json"
            alias.symlink_to(outside)
            unreviewed = reconciler.ROOT / "unreviewed.json"
            unreviewed.write_text(marker, encoding="utf-8")
            directory = reconciler.ROOT / "unreviewed-directory"
            directory.mkdir()
            cases = (
                ("external", outside, "recovery objective reconcile write path unsafe"),
                ("symlink", alias, "recovery objective reconcile write path unsafe"),
                ("directory", directory, "recovery objective reconcile write path unsafe"),
                ("unreviewed", unreviewed, "recovery objective reconcile write target unreviewed"),
            )
            for label, path, expected in cases:
                try:
                    reconciler.write_text(path, "changed")
                except reconciler.Fail as exc:
                    require(str(exc) == expected and marker not in str(exc),
                            f"recovery objective reconcile write {label} wrong/private rejection")
                else:
                    raise Fail(f"recovery objective reconcile write {label} unexpectedly accepted")
            require(outside.read_text(encoding="utf-8") == marker
                    and unreviewed.read_text(encoding="utf-8") == marker,
                    "recovery objective reconcile write canary changed")
        try:
            reconciler.write_text(reconciler.CONTRACT, "x" * (reconciler.MAX_AUTHORITY_BYTES + 1))
        except reconciler.Fail as exc:
            require(str(exc) == "recovery objective reconcile write size limit exceeded",
                    "recovery objective reconcile write oversized input wrong rejection")
        else:
            raise Fail("recovery objective reconcile write oversized input accepted")
        require(reconciler.CONTRACT.read_bytes() == original,
                "recovery objective reconcile write negatives mutated fixture contract")
    print("PASS: recovery objective reconcile atomic write path and size guards (5 negatives)")


def prove_atomic_target_identity_guards(reconciler: object) -> None:
    """Reject hardlinks, writable authority targets and in-stage target drift."""
    with isolated_authorities(reconciler):
        path = reconciler.CONTRACT
        before, before_mode = path.read_bytes(), file_mode(path)
        hardlink = path.parent / ".objective-reconcile-hardlink-canary"
        os.link(path, hardlink)
        try:
            expect_domain_fail(
                "hardlinked recovery objective write target",
                lambda: reconciler.write_text(path, '{"synthetic":true}'),
                reconciler.Fail,
                "recovery objective reconcile write target metadata unsafe",
            )
        finally:
            hardlink.unlink()

        os.chmod(path, 0o666)
        try:
            expect_domain_fail(
                "group/world-writable recovery objective write target",
                lambda: reconciler.write_text(path, '{"synthetic":true}'),
                reconciler.Fail,
                "recovery objective reconcile write target metadata unsafe",
            )
        finally:
            os.chmod(path, before_mode)

        original_fsync = reconciler.os.fsync
        altered_mode = 0o600 if before_mode != 0o600 else 0o640
        changed = []

        def change_target_during_stage(fd):
            original_fsync(fd)
            os.chmod(path, altered_mode)
            changed.append(True)

        reconciler.os.fsync = change_target_during_stage
        try:
            expect_domain_fail(
                "recovery objective target metadata changed before replace",
                lambda: reconciler.write_text(path, '{"synthetic":true}'),
                reconciler.Fail,
                "recovery objective reconcile write authority changed during stage",
            )
        finally:
            reconciler.os.fsync = original_fsync
            os.chmod(path, before_mode)

        require(changed == [True], "atomic target drift fixture did not reach staging")
        require(path.read_bytes() == before and file_mode(path) == before_mode,
                "atomic target identity negatives mutated authority fixture")
        require(not list(path.parent.glob(f".{path.name}.*.tmp")),
                "atomic target identity negatives left temporary files")
    print("PASS: recovery objective atomic hardlink/mode/precommit drift negatives")


def prove_atomic_parent_swap_before_commit(reconciler: object) -> None:
    """A parent swap during staging must not reach the replacement syscall."""
    with isolated_authorities(reconciler):
        path = reconciler.CONTRACT
        original = path.read_bytes()
        parent = path.parent
        moved = parent.with_name(parent.name + "-held")
        canary_parent = reconciler.ROOT / "objective-parent-swap-canary"
        canary_parent.mkdir()
        canary = canary_parent / path.name
        canary.write_bytes(b"PRIVATE_OBJECTIVE_PARENT_SWAP_CANARY")
        original_fsync = reconciler.os.fsync
        original_replace = reconciler.os.replace
        replace_calls = []
        swapped = []

        def swap_after_stage(fd):
            original_fsync(fd)
            parent.rename(moved)
            parent.symlink_to(canary_parent, target_is_directory=True)
            swapped.append(True)

        def forbid_replace(*_args, **_kwargs):
            replace_calls.append(True)
            raise OSError("PRIVATE_OBJECTIVE_REPLACE_CALLED_CANARY")

        reconciler.os.fsync = swap_after_stage
        reconciler.os.replace = forbid_replace
        try:
            expect_domain_fail(
                "recovery objective parent swapped before atomic commit",
                lambda: reconciler.write_text(path, '{"synthetic":true}'),
                reconciler.Fail,
                "recovery objective reconcile write authority changed during stage",
            )
        finally:
            reconciler.os.fsync = original_fsync
            reconciler.os.replace = original_replace
            if parent.is_symlink():
                parent.unlink()
            if moved.exists():
                moved.rename(parent)
            # Pinned-FD cleanup must have removed the staged inode even
            # while the reviewed parent was invisible at its old pathname.
            require(not list(parent.glob(f".{path.name}.*.tmp")),
                    "parent-swap negative left a staged temporary inode")

        require(swapped == [True] and not replace_calls,
                "parent-swap negative reached replacement or missed the race")
        require(path.read_bytes() == original
                and canary.read_bytes() == b"PRIVATE_OBJECTIVE_PARENT_SWAP_CANARY",
                "parent-swap negative changed reviewed/canary bytes")
        require(not list(parent.glob(f".{path.name}.*.tmp")),
                "parent-swap negative left temporary residue")
    print("PASS: recovery objective atomic parent swap before commit refuses replace")




def prove_atomic_parent_swap_during_stage(reconciler: object) -> None:
    """Stage creation must remain in the owned parent after its path is swapped."""
    with isolated_authorities(reconciler):
        path = reconciler.CONTRACT
        original = path.read_bytes()
        parent = path.parent
        moved = parent.with_name(parent.name + "-stage-held")
        canary_parent = reconciler.ROOT / "objective-stage-swap-canary"
        canary_parent.mkdir()
        canary = canary_parent / path.name
        canary.write_bytes(b"PRIVATE_OBJECTIVE_STAGE_SWAP_CANARY")
        original_stage = reconciler.stage_temporary_at
        reached = []

        def swap_then_stage(parent_fd, target):
            parent.rename(moved)
            parent.symlink_to(canary_parent, target_is_directory=True)
            reached.append(True)
            return original_stage(parent_fd, target)

        reconciler.stage_temporary_at = swap_then_stage
        try:
            expect_domain_fail(
                "recovery objective parent swapped at stage creation",
                lambda: reconciler.write_text(path, '{"synthetic":true}'),
                reconciler.Fail,
                "recovery objective reconcile write authority changed during stage",
            )
        finally:
            reconciler.stage_temporary_at = original_stage
            residue_during_swap = list(moved.glob(f".{path.name}.*.tmp"))
            if parent.is_symlink():
                parent.unlink()
            if moved.exists():
                moved.rename(parent)

        require(reached == [True] and not residue_during_swap,
                "stage-boundary parent swap left an inode or missed the race")
        require(path.read_bytes() == original
                and canary.read_bytes() == b"PRIVATE_OBJECTIVE_STAGE_SWAP_CANARY"
                and not list(parent.glob(f".{path.name}.*.tmp")),
                "stage-boundary parent swap mutated authority or left temporary bytes")
    print("PASS: recovery objective stage creation and cleanup pinned to parent FD")


def prove_atomic_parent_swap_cleanup_on_replace_error(reconciler: object) -> None:
    """A failed commit after a parent swap must clean the original parent FD."""
    with isolated_authorities(reconciler):
        path = reconciler.CONTRACT
        original = path.read_bytes()
        parent = path.parent
        moved = parent.with_name(parent.name + "-replace-held")
        canary_parent = reconciler.ROOT / "objective-replace-swap-canary"
        canary_parent.mkdir()
        canary = canary_parent / path.name
        canary.write_bytes(b"PRIVATE_OBJECTIVE_REPLACE_SWAP_CANARY")
        original_replace = reconciler.os.replace
        reached = []
        residue_during_swap = None

        def swap_then_fail(_source, _destination, **_kwargs):
            parent.rename(moved)
            parent.symlink_to(canary_parent, target_is_directory=True)
            reached.append(True)
            raise OSError("PRIVATE_OBJECTIVE_REPLACE_SWAP_CANARY")

        reconciler.os.replace = swap_then_fail
        try:
            expect_domain_fail(
                "recovery objective parent swap at failing replace",
                lambda: reconciler.write_text(path, '{"synthetic":true}'),
                reconciler.Fail,
                "recovery objective reconcile authority atomic write failed",
            )
        finally:
            reconciler.os.replace = original_replace
            residue_during_swap = list(moved.glob(f".{path.name}.*.tmp"))
            if parent.is_symlink():
                parent.unlink()
            if moved.exists():
                moved.rename(parent)

        require(reached == [True], "replacement-boundary parent swap was not exercised")
        require(not residue_during_swap
                and not list(parent.glob(f".{path.name}.*.tmp")),
                "replacement-boundary swap left temporary inode in reviewed parent")
        require(path.read_bytes() == original
                and canary.read_bytes() == b"PRIVATE_OBJECTIVE_REPLACE_SWAP_CANARY",
                "replacement-boundary swap mutated reviewed or canary bytes")
    print("PASS: recovery objective atomic parent-FD cleanup after replace-boundary swap")



def prove_atomic_parent_swap_inside_replace(reconciler: object) -> None:
    """A swap in the replace boundary cannot redirect bytes to the canary."""
    with isolated_authorities(reconciler):
        path = reconciler.CONTRACT
        original = path.read_bytes()
        parent = path.parent
        moved = parent.with_name(parent.name + "-commit-held")
        canary_parent = reconciler.ROOT / "objective-commit-swap-canary"
        canary_parent.mkdir()
        canary = canary_parent / path.name
        canary.write_bytes(b"PRIVATE_OBJECTIVE_COMMIT_SWAP_CANARY")
        original_replace = reconciler.os.replace
        reached = []

        def swap_inside_replace(source, destination, **kwargs):
            parent.rename(moved)
            parent.symlink_to(canary_parent, target_is_directory=True)
            reached.append(True)
            return original_replace(source, destination, **kwargs)

        reconciler.os.replace = swap_inside_replace
        try:
            expect_domain_fail(
                "recovery objective parent swapped inside atomic replace",
                lambda: reconciler.write_text(path, '{"synthetic":true}'),
                reconciler.Fail,
                "recovery objective reconcile write parent changed at commit",
            )
        finally:
            reconciler.os.replace = original_replace
            residue_during_swap = list(moved.glob(f".{path.name}.*.tmp"))
            if parent.is_symlink():
                parent.unlink()
            if moved.exists():
                moved.rename(parent)
            # The synthetic swap occurred *inside* the replacement syscall.
            # Restore the isolated original inode; never touch real authorities.
            path.write_bytes(original)

        require(reached == [True] and not residue_during_swap,
                "commit-boundary parent swap missed or left staged residue")
        require(canary.read_bytes() == b"PRIVATE_OBJECTIVE_COMMIT_SWAP_CANARY"
                and path.read_bytes() == original
                and not list(parent.glob(f".{path.name}.*.tmp")),
                "commit-boundary swap changed canary or failed fixture restoration")
    print("PASS: recovery objective FD replacement refuses detached parent success")


def prove_atomic_temp_descriptor_identity(reconciler: object) -> None:
    """Malformed mkstemp descriptors must not be used or closed as owned FDs."""
    with isolated_authorities(reconciler):
        path = reconciler.CONTRACT
        before, before_mode = path.read_bytes(), file_mode(path)
        original_stage = reconciler.stage_temporary_at
        canary = reconciler.ROOT / "objective-unowned-descriptor-canary"
        canary.write_bytes(b"PRIVATE_OBJECTIVE_UNOWNED_DESCRIPTOR_CANARY")
        wrong_fd = os.open(canary, os.O_RDONLY)
        try:
            for label, forged_fd in (("boolean", True), ("negative", -1),
                                      ("unrelated-regular", wrong_fd)):
                def forge_stage(*args, **kwargs):
                    real_fd, name = original_stage(*args, **kwargs)
                    os.close(real_fd)
                    return forged_fd, name

                reconciler.stage_temporary_at = forge_stage
                try:
                    expect_domain_fail(
                        f"recovery objective {label} temporary descriptor",
                        lambda: reconciler.write_text(path, '{"synthetic":true}'),
                        reconciler.Fail,
                        "recovery objective reconcile temporary descriptor unsafe",
                    )
                finally:
                    reconciler.stage_temporary_at = original_stage
                require(not list(path.parent.glob(f".{path.name}.*.tmp")),
                        f"{label} temporary descriptor left residue")
            require(os.fstat(wrong_fd).st_ino == canary.stat().st_ino,
                    "atomic writer closed an unowned unrelated descriptor")
        finally:
            reconciler.stage_temporary_at = original_stage
            os.close(wrong_fd)
        require(canary.read_bytes() == b"PRIVATE_OBJECTIVE_UNOWNED_DESCRIPTOR_CANARY",
                "atomic writer changed unowned descriptor canary")
        require(path.read_bytes() == before and file_mode(path) == before_mode,
                "atomic descriptor identity negatives mutated authority fixture")
    print("PASS: recovery objective atomic temporary FD ownership and inode identity")


def prove_atomic_write_mode_preservation(reconciler: object) -> None:
    with isolated_authorities(reconciler):
        path = reconciler.CONTRACT
        original = path.read_bytes()
        original_mode = file_mode(path)
        os.chmod(path, 0o640)
        reconciler.write_text(path, '{"synthetic":true}\n')
        require(path.read_text(encoding="utf-8") == '{"synthetic":true}\n',
                "objective mode-preservation fixture payload drift")
        require(file_mode(path) == 0o640,
                "atomic recovery objective authority replace changed existing file mode")
        reconciler.write_text(path, original.decode("utf-8"))
        os.chmod(path, original_mode)
        require(path.read_bytes() == original and file_mode(path) == original_mode,
                "objective mode-preservation fixture restoration drift")
        leftovers = list(path.parent.glob(f".{path.name}.*.tmp"))
        require(not leftovers, "mode-preserving recovery objective write left temporary files")
    print("PASS boundary: atomic recovery objective authority replace preserves existing file mode")


def prove_atomic_write_failure(reconciler: object) -> None:
    contract_bytes = reconciler.CONTRACT.read_bytes()
    original_replace = reconciler.os.replace

    def reject_replace(source: str | Path, destination: str | Path, **_kwargs) -> None:
        raise OSError("synthetic atomic replace rejection")

    reconciler.os.replace = reject_replace
    try:
        expect_domain_fail(
            "recovery objective atomic replace rejection",
            lambda: reconciler.write_text(reconciler.CONTRACT, contract_bytes.decode("utf-8") + " "),
            reconciler.Fail,
            "recovery objective reconcile authority atomic write failed",
        )
    finally:
        reconciler.os.replace = original_replace

    require(reconciler.CONTRACT.read_bytes() == contract_bytes, "atomic replace rejection changed fixture contract")
    contract_leftovers = list(reconciler.CONTRACT.parent.glob(f".{reconciler.CONTRACT.name}.*.tmp"))
    status_leftovers = list(reconciler.STATUS.parent.glob(f".{reconciler.STATUS.name}.*.tmp"))
    require(not contract_leftovers and not status_leftovers, "atomic write rejection left temporary recovery objective authority files")
    print("PASS boundary: failed atomic recovery objective write preserves fixture bytes/mode and cleans temporary files")


def prove_atomic_descriptor_cleanup(reconciler: object) -> None:
    """fchmod/fdopen faults must close descriptors and unlink temporary files."""
    with isolated_authorities(reconciler):
        path = reconciler.CONTRACT
        before = path.read_bytes()
        before_mode = file_mode(path)
        original_stage = reconciler.stage_temporary_at
        original_fchmod = reconciler.os.fchmod
        original_fdopen = reconciler.os.fdopen
        marker = "PRIVATE_OBJECTIVE_RECONCILE_DESCRIPTOR_CANARY"
        opened = []

        def track_stage(*args, **kwargs):
            descriptor, name = original_stage(*args, **kwargs)
            opened.append(descriptor)
            return descriptor, name

        def reject(*_args, **_kwargs):
            raise OSError(marker)

        reconciler.stage_temporary_at = track_stage
        try:
            for label in ("fchmod", "fdopen"):
                opened.clear()
                if label == "fchmod":
                    reconciler.os.fchmod = reject
                else:
                    reconciler.os.fdopen = reject
                try:
                    reconciler.write_text(path, '{"synthetic":true}')
                except reconciler.Fail as exc:
                    require(str(exc) == "recovery objective reconcile authority atomic write failed"
                            and exc.__suppress_context__ and marker not in str(exc),
                            f"atomic descriptor {label} private failure drift")
                else:
                    raise Fail(f"atomic descriptor {label} failure unexpectedly accepted")
                finally:
                    reconciler.os.fchmod = original_fchmod
                    reconciler.os.fdopen = original_fdopen
                require(len(opened) == 1, f"atomic descriptor {label} fixture did not open exactly once")
                for descriptor in opened:
                    try:
                        os.fstat(descriptor)
                    except OSError:
                        pass
                    else:
                        os.close(descriptor)
                        raise Fail(f"atomic descriptor {label} remained open")
                require(path.read_bytes() == before and file_mode(path) == before_mode,
                        f"atomic descriptor {label} mutated authority fixture")
                require(not list(path.parent.glob(f".{path.name}.*.tmp")),
                        f"atomic descriptor {label} left temporary residue")
        finally:
            reconciler.stage_temporary_at = original_stage
            reconciler.os.fchmod = original_fchmod
            reconciler.os.fdopen = original_fdopen
    print("PASS: recovery objective reconciler fchmod/fdopen descriptor cleanup (2 negatives)")



def prove_atomic_primary_cleanup_precedence(reconciler: object) -> None:
    """A failed temp unlink must not hide the original atomic-write failure."""
    with isolated_authorities(reconciler):
        path = reconciler.CONTRACT
        before = path.read_bytes()
        before_mode = file_mode(path)
        original_replace = reconciler.os.replace
        original_unlink = reconciler.os.unlink
        marker = "PRIVATE_OBJECTIVE_ATOMIC_DOUBLE_FAULT_CANARY"

        def reject_replace(_source, _destination, **_kwargs):
            raise OSError(marker)

        def reject_temp_unlink(candidate, *args, **kwargs):
            if str(candidate).endswith(".tmp"):
                raise OSError(marker)
            return original_unlink(candidate, *args, **kwargs)

        reconciler.os.replace = reject_replace
        reconciler.os.unlink = reject_temp_unlink
        try:
            try:
                reconciler.write_text(path, '{"synthetic":true}')
            except reconciler.Fail as exc:
                require(str(exc) == "recovery objective reconcile authority atomic write failed"
                        and exc.__suppress_context__ and marker not in str(exc),
                        "recovery objective atomic primary error hidden by cleanup failure")
            else:
                raise Fail("recovery objective atomic double fault unexpectedly accepted")
        finally:
            reconciler.os.replace = original_replace
            reconciler.os.unlink = original_unlink

        leftovers = list(path.parent.glob(f".{path.name}.*.tmp"))
        require(len(leftovers) == 1, "recovery objective atomic double fault fixture residue drift")
        for leftover in leftovers:
            leftover.unlink()
        require(path.read_bytes() == before and file_mode(path) == before_mode,
                "recovery objective atomic double fault changed canonical fixture")
        require(not list(path.parent.glob(f".{path.name}.*.tmp")),
                "recovery objective atomic double fault left cleanup residue")
    print("PASS: recovery objective atomic primary failure survives secondary cleanup fault")


def prove_atomic_non_oserror_cleanup_precedence(reconciler: object) -> None:
    """Malformed close/unlink exceptions must not mask the primary write error."""
    with isolated_authorities(reconciler):
        path = reconciler.CONTRACT
        before, before_mode = path.read_bytes(), file_mode(path)
        marker = "PRIVATE_OBJECTIVE_ATOMIC_NON_OSERROR_CLEANUP_CANARY"
        original_replace = reconciler.os.replace
        original_unlink = reconciler.os.unlink
        original_close = reconciler.os.close
        original_fchmod = reconciler.os.fchmod

        def reject_replace(_source, _destination, **_kwargs):
            raise OSError(marker)

        def reject_unlink(candidate, *args, **kwargs):
            if str(candidate).endswith(".tmp"):
                raise TypeError(marker)
            return original_unlink(candidate, *args, **kwargs)

        reconciler.os.replace = reject_replace
        reconciler.os.unlink = reject_unlink
        try:
            try:
                reconciler.write_text(path, '{"synthetic":true}')
            except reconciler.Fail as exc:
                require(str(exc) == "recovery objective reconcile authority atomic write failed"
                        and exc.__suppress_context__ and marker not in str(exc),
                        "atomic unlink TypeError masked primary write failure")
            else:
                raise Fail("atomic unlink TypeError was accepted")
        finally:
            reconciler.os.replace = original_replace
            reconciler.os.unlink = original_unlink

        leftovers = list(path.parent.glob(f".{path.name}.*.tmp"))
        require(len(leftovers) == 1, "atomic unlink TypeError fixture residue drift")
        for leftover in leftovers:
            leftover.unlink()

        def reject_fchmod(_fd, _mode):
            raise OSError(marker)

        def close_then_reject(fd):
            original_close(fd)
            raise ValueError(marker)

        reconciler.os.fchmod = reject_fchmod
        reconciler.os.close = close_then_reject
        try:
            try:
                reconciler.write_text(path, '{"synthetic":true}')
            except reconciler.Fail as exc:
                require(str(exc) == "recovery objective reconcile authority atomic write failed"
                        and exc.__suppress_context__ and marker not in str(exc),
                        "atomic close ValueError masked primary write failure")
            else:
                raise Fail("atomic close ValueError was accepted")
        finally:
            reconciler.os.fchmod = original_fchmod
            reconciler.os.close = original_close

        require(path.read_bytes() == before and file_mode(path) == before_mode,
                "non-OSError cleanup negatives mutated objective fixture authority")
        require(not list(path.parent.glob(f".{path.name}.*.tmp")),
                "non-OSError cleanup negatives left temporary files")
    print("PASS: recovery objective atomic TypeError/ValueError cleanup preserves primary error")


def prove_rollback_attempts_all_restores(reconciler: object) -> None:
    originals = {
        CONTRACT: "contract\n",
        STATUS: "status\n",
    }
    observed: list[Path] = []
    original_write = reconciler.write_text

    def reject_first_restore(path: Path, text: str) -> None:
        observed.append(path)
        if len(observed) == 1:
            raise reconciler.Fail("PRIVATE_OBJECTIVE_ROLLBACK_RESTORE_CANARY")

    reconciler.write_text = reject_first_restore
    try:
        expect_domain_fail(
            "first recovery objective rollback restore rejection",
            lambda: reconciler.restore_original_text(originals),
            reconciler.Fail,
            "recovery objective rollback incomplete",
        )
    finally:
        reconciler.write_text = original_write

    require(observed == [CONTRACT, STATUS], f"objective rollback restore failure skipped later authority: {observed}")
    print("PASS rollback: recovery objective restore failure still attempts contract and status")


def prove_primary_and_rollback_failures_are_preserved(reconciler: object) -> None:
    original_run_validator = reconciler.run_validator
    original_restore = reconciler.restore_original_text

    def fail_primary(path: Path, label: str) -> None:
        raise reconciler.Fail("PRIVATE_OBJECTIVE_PRIMARY_CANARY")

    def fail_rollback(original_text: dict[Path, str]) -> None:
        raise reconciler.Fail("PRIVATE_OBJECTIVE_ROLLBACK_CANARY")

    reconciler.run_validator = fail_primary
    reconciler.restore_original_text = fail_rollback
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            text = str(exc)
            require(
                text == "recovery objective reconcile transaction failed (Fail); rollback incomplete"
                and exc.__suppress_context__
                and "PRIVATE_OBJECTIVE_PRIMARY_CANARY" not in text
                and "PRIVATE_OBJECTIVE_ROLLBACK_CANARY" not in text,
                "recovery objective primary/rollback diagnostic wrong or private",
            )
        else:
            raise Fail("synthetic recovery objective primary+rollback failure unexpectedly accepted")
    finally:
        reconciler.run_validator = original_run_validator
        reconciler.restore_original_text = original_restore
    print("PASS rollback: recovery objective reconcile primary/rollback diagnostics private and incomplete marker preserved")


def prove_second_replace_transaction_rollback(reconciler: object) -> None:
    original_replace = reconciler.os.replace
    replace_destinations: list[Path] = []

    def fail_second_replace(source: str | Path, destination: str | Path, **kwargs) -> None:
        replace_destinations.append(reconciler.CONTRACT.parent / destination)
        if len(replace_destinations) == 2:
            raise OSError("synthetic second authority replace rejection")
        original_replace(source, destination, **kwargs)

    reconciler.os.replace = fail_second_replace
    try:
        expect_domain_fail(
            "recovery objective second authority replace rejection",
            reconciler.main,
            reconciler.Fail,
            "recovery objective reconcile transaction failed (Fail); rollback completed",
        )
    finally:
        reconciler.os.replace = original_replace

    require(
        replace_destinations == [reconciler.CONTRACT, reconciler.STATUS, reconciler.CONTRACT, reconciler.STATUS],
        f"recovery objective second-replace rollback order drift: {replace_destinations}",
    )
    contract_leftovers = list(reconciler.CONTRACT.parent.glob(f".{reconciler.CONTRACT.name}.*.tmp"))
    status_leftovers = list(reconciler.STATUS.parent.glob(f".{reconciler.STATUS.name}.*.tmp"))
    require(
        not contract_leftovers and not status_leftovers,
        "second authority replace rejection left temporary recovery objective authority files",
    )
    print("PASS rollback: second authority replace rejection restores fixture contract/status byte-for-byte and mode-for-mode")


def prove_aggregate_validator_rollback(reconciler: object) -> None:
    original_run_validator = reconciler.run_validator
    validator_calls: list[tuple[Path, str]] = []

    def fail_aggregate_validator(path: Path, label: str) -> None:
        validator_calls.append((path, label))
        if path == reconciler.OPERABILITY_VALIDATOR:
            raise reconciler.Fail("post-reconcile aggregate operability validator failed: forced negative")
        return None

    reconciler.run_validator = fail_aggregate_validator
    try:
        expect_domain_fail(
            "post-write aggregate operability rejection",
            reconciler.main,
            reconciler.Fail,
            "recovery objective reconcile transaction failed (Fail); rollback completed",
        )
    finally:
        reconciler.run_validator = original_run_validator

    require(
        validator_calls
        == [
            (reconciler.VALIDATOR, "recovery objective validator"),
            (reconciler.OPERABILITY_VALIDATOR, "aggregate operability validator"),
        ],
        f"recovery objective post-write validator order drift: {validator_calls}",
    )
    print("PASS rollback: aggregate operability rejection restores fixture recovery objective contract/status byte-for-byte and mode-for-mode")
    print("PASS boundary: post-write validator order is recovery objective then aggregate Operability")



def prove_private_writer_import(reconciler: object) -> None:
    """Pinned import must hide source/spec errors and execute the reviewed positive source."""
    actual = reconciler.load_writer()
    require(Path(actual.__file__).resolve() == reconciler.WRITER.resolve(),
            "recovery objective writer import positive identity drift")
    original_spec = reconciler.importlib.util.spec_from_file_location
    marker = "PRIVATE_RECOVERY_OBJECTIVE_RECONCILE_IMPORT_CANARY"

    def rejected_spec(*_args, **_kwargs):
        print(marker)
        print(marker, file=sys.stderr)
        raise OSError(marker)

    reconciler.importlib.util.spec_from_file_location = rejected_spec
    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                reconciler.load_writer()
            except reconciler.Fail as exc:
                require(str(exc) == "recovery objective canonical writer import failed"
                        and exc.__suppress_context__ and marker not in str(exc),
                        "recovery objective writer import private failure drift")
            else:
                raise Fail("recovery objective writer import failure accepted")
    finally:
        reconciler.importlib.util.spec_from_file_location = original_spec
    require(not stdout.getvalue() and not stderr.getvalue(),
            "recovery objective writer import leaked Python-level output")
    print("PASS: recovery objective writer import output and errors private")


def prove_pinned_writer_import(reconciler: object) -> None:
    """A parent swap after source capture cannot execute an unreviewed writer."""
    with isolated_authorities(reconciler):
        writer = reconciler.WRITER
        writer.write_text("SOURCE_MARKER = 'reviewed'\n", encoding="utf-8")
        require(reconciler.load_writer().SOURCE_MARKER == "reviewed",
                "recovery objective pinned writer positive control failed")
        parent = writer.parent
        parked = reconciler.ROOT / "parked-scripts"
        redirected = reconciler.ROOT / "redirected"
        redirected.mkdir()
        canary = redirected / writer.name
        canary.write_text("raise RuntimeError('PRIVATE_OBJECTIVE_WRITER_SWAP_CANARY')\n",
                          encoding="utf-8")
        writer.chmod(0o666)
        try:
            expect_domain_fail("writable objective writer", reconciler.load_writer,
                               reconciler.Fail)
        finally:
            writer.chmod(0o644)
        parent.chmod(0o777)
        try:
            expect_domain_fail("writable objective writer parent", reconciler.load_writer,
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
            expect_domain_fail("mid-read objective writer parent swap", reconciler.load_writer,
                               reconciler.Fail)
            require(raced, "objective writer mid-read swap negative not exercised")
        finally:
            reconciler.os.read = original_read
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)
        require(reconciler.load_writer().SOURCE_MARKER == "reviewed",
                "objective writer positive control failed after parent restore")
        original_spec = reconciler.importlib.util.spec_from_file_location
        swapped = False

        def swap_after_capture(name, location, *args, **kwargs):
            nonlocal swapped
            if not swapped and Path(location) == writer:
                swapped = True
                parent.rename(parked)
                parent.symlink_to(redirected, target_is_directory=True)
            return original_spec(name, location, *args, **kwargs)

        reconciler.importlib.util.spec_from_file_location = swap_after_capture
        try:
            loaded = reconciler.load_writer()
            require(swapped and loaded.SOURCE_MARKER == "reviewed",
                    "recovery objective writer import followed swapped pathname")
            require(canary.read_text(encoding="utf-8").startswith("raise RuntimeError"),
                    "recovery objective redirected writer canary mutated")
        finally:
            reconciler.importlib.util.spec_from_file_location = original_spec
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)
    print("PASS: recovery objective writer executes pinned bytes after parent swap")


def prove_reference_path_identity(reconciler: object) -> None:
    """Evidence references must name canonical files, never aliases or private paths."""
    with isolated_authorities(reconciler):
        relative = Path(".github/workflows/recovery-objectives-admission.yml")
        canonical = reconciler.ROOT / relative
        require(reconciler.require_repo_file(canonical, "missing canonical reference") == relative,
                "recovery objective canonical evidence reference positive control failed")
        marker = "PRIVATE_RECOVERY_OBJECTIVE_REFERENCE_PATH_CANARY"
        with tempfile.TemporaryDirectory(prefix="objective-reference-outside-") as tmp:
            outside = Path(tmp) / "private.json"
            outside.write_text(marker, encoding="utf-8")
            external_alias = reconciler.ROOT / "external-reference-alias.json"
            external_alias.symlink_to(outside)
            internal_alias = reconciler.ROOT / "internal-reference-alias.json"
            internal_alias.symlink_to(canonical)
            parent_alias = reconciler.ROOT / "parent-reference-alias"
            parent_alias.symlink_to(reconciler.ROOT / "contracts/operations",
                                    target_is_directory=True)
            registry_name = "recovery-objectives-registry.v1.json"
            cases = (
                ("external", outside, "recovery objective authority reference path unsafe"),
                ("external alias", external_alias, "recovery objective authority reference path unsafe"),
                ("internal alias", internal_alias, "recovery objective authority reference path unsafe"),
                ("parent alias", parent_alias / registry_name,
                 "recovery objective authority reference path unsafe"),
                ("traversal", reconciler.ROOT / "contracts/operations/../operations" / registry_name,
                 "recovery objective authority reference path unsafe"),
                ("relative", relative, "recovery objective authority reference path unsafe"),
                ("non-path", str(canonical), "recovery objective authority reference path unsafe"),
                ("missing", reconciler.ROOT / "missing-reference.json", "reference missing"),
                ("directory", reconciler.ROOT / "contracts/operations", "reference missing"),
            )
            for label, path, expected in cases:
                try:
                    reconciler.require_repo_file(path, "reference missing")
                except reconciler.Fail as exc:
                    require(str(exc) == expected and marker not in str(exc),
                            f"recovery objective reference {label} wrong/private rejection")
                    require(exc.__context__ is None or exc.__suppress_context__,
                            f"recovery objective reference {label} retained exception context")
                else:
                    raise Fail(f"recovery objective reference {label} unexpectedly accepted")
            require(outside.read_text(encoding="utf-8") == marker,
                    "recovery objective external reference canary changed")
    print("PASS: recovery objective evidence reference path identity (9 negatives)")


def prove_private_authority_path_diagnostics(reconciler: object) -> None:
    """Canonical path failures must not retain private filesystem context."""
    with isolated_authorities(reconciler):
        marker = "PRIVATE_RECOVERY_OBJECTIVE_AUTHORITY_PATH_CANARY"
        with tempfile.TemporaryDirectory(prefix="objective-reconcile-authority-external-") as tmp:
            external = Path(tmp) / "private.json"
            external.write_text(marker, encoding="utf-8")
            alias = reconciler.ROOT / "contracts/operations/objective-authority-alias.json"
            alias.symlink_to(external)
            missing = reconciler.ROOT / "contracts/operations/missing-objective-authority.json"
            for label, path in (("external-symlink", alias), ("missing", missing)):
                try:
                    reconciler.require_exact_repo_file(
                        path, reconciler.REGISTRY_REL, "recovery objective registry",
                    )
                except reconciler.Fail as exc:
                    require(str(exc) == "recovery objective registry missing or escapes repository"
                            and exc.__suppress_context__ and marker not in str(exc),
                            f"recovery objective reconcile {label} authority path diagnostic drift")
                else:
                    raise Fail(f"recovery objective reconcile {label} authority path accepted")
            require(external.read_text(encoding="utf-8") == marker,
                    "recovery objective authority path external canary changed")
        require(reconciler.require_exact_repo_file(
                    reconciler.REGISTRY, reconciler.REGISTRY_REL,
                    "recovery objective registry") == reconciler.REGISTRY,
                "recovery objective canonical authority path positive control failed")
    print("PASS: recovery objective canonical authority path private diagnostics (2 negatives)")


def prove_private_delegated_registry_errors(reconciler: object) -> None:
    """Recognized delegated domain errors must not echo private text or context."""
    with isolated_authorities(reconciler):
        original_loader = reconciler.load_writer
        canonical_writer = original_loader()
        require(isinstance(canonical_writer.validate_registry_for_append(
                    reconciler.load(reconciler.REGISTRY)), list),
                "recovery objective delegated registry positive control failed")
        marker = "PRIVATE_RECOVERY_OBJECTIVE_DELEGATED_REGISTRY_CANARY"

        class Fail(RuntimeError):
            pass

        class DelegatedWriter:
            def __init__(self, failure):
                self.failure = failure

            def validate_registry_for_append(self, _registry):
                raise self.failure

        try:
            reconciler.load_writer = lambda: DelegatedWriter(Fail(marker))
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                require(str(exc) == "append-only recovery objective authority invalid before reconcile"
                        and exc.__suppress_context__ and marker not in str(exc),
                        "recovery objective delegated domain error exposed private diagnostics")
            else:
                raise Fail("recovery objective delegated domain error unexpectedly accepted")

            reconciler.load_writer = lambda: DelegatedWriter(TypeError(marker))
            try:
                reconciler.main()
            except TypeError as exc:
                require(str(exc) == marker,
                        "recovery objective unexpected delegated fault was normalized")
            else:
                raise Fail("recovery objective unexpected delegated fault accepted")
        finally:
            reconciler.load_writer = original_loader
    print("PASS: recovery objective delegated registry private domain error and unexpected fault boundary")


def prove_private_post_reconcile_transport(reconciler: object) -> None:
    """Exercise the actual subprocess boundary with private synthetic canaries."""
    original_run = reconciler.subprocess.run
    marker = "PRIVATE_RECOVERY_OBJECTIVE_RECONCILE_SUBPROCESS_CANARY"
    # Canary overrides must not reach the child, while an ordinary variable must.
    injected = {
        "PYTHONPATH": marker, "PYTHONHOME": marker,
        "LD_PRELOAD": marker, "DYLD_INSERT_LIBRARIES": marker,
        "GIT_CONFIG_COUNT": "1", "MEMORY_OS_SAFE_CONTROL": marker,
    }
    prior_env = {key: os.environ.get(key) for key in injected}
    os.environ.update(injected)
    state: dict[str, object] = {"returncode": 0, "error": None, "result": None}
    calls: list[tuple[str, ...]] = []

    def fake_run(args, **kwargs):
        child_env = kwargs.get("env")
        require(isinstance(child_env, dict)
                and child_env.get("MEMORY_OS_SAFE_CONTROL") == marker
                and not any(key.startswith(("PYTHON", "LD_", "DYLD_", "GIT_"))
                            for key in child_env),
                "recovery objective reconcile subprocess environment isolation drift")
        expected_bootstrap = (
            "import os, sys\n"
            "path = sys.argv[1]\n"
            "sys.path.insert(0, os.path.dirname(path))\n"
            "sys.argv[:] = [path]\n"
            "scope = {'__name__': '__main__', '__file__': path, '__package__': None, '__spec__': None}\n"
            "exec(compile(sys.stdin.buffer.read(), path, 'exec'), scope)\n"
        )
        require(args in ([sys.executable, "-c", expected_bootstrap, str(reconciler.VALIDATOR)],
                         [sys.executable, "-c", expected_bootstrap, str(reconciler.OPERABILITY_VALIDATOR)]),
                "recovery objective reconcile subprocess command drift")
        require(type(kwargs.get("input")) is bytes
                and kwargs["input"] == Path(args[3]).read_bytes(),
                "recovery objective reconcile subprocess pinned source drift")
        require(kwargs.get("cwd") == reconciler.ROOT
                and kwargs.get("stdout") is subprocess.DEVNULL
                and kwargs.get("stderr") is subprocess.DEVNULL
                and kwargs.get("check") is False
                and kwargs.get("timeout") == 180
                and "text" not in kwargs,
                "recovery objective reconcile subprocess privacy/timeout drift")
        calls.append(tuple(args))
        if state["error"] is not None:
            raise state["error"]
        if state["result"] is not None:
            return state["result"]
        return subprocess.CompletedProcess(args, state["returncode"],
                                           stdout=marker, stderr=marker)

    reconciler.subprocess.run = fake_run
    try:
        reconciler.run_validator(reconciler.VALIDATOR, "recovery objective validator")
        reconciler.run_validator(reconciler.OPERABILITY_VALIDATOR, "aggregate operability validator")
        cases = (
            ("nonzero", {"returncode": 1},
             "post-reconcile recovery objective validator failed without exposing subprocess output"),
            ("boolean", {"returncode": True},
             "post-reconcile recovery objective validator failed without exposing subprocess output"),
            ("forged completion", {"result": type("ForgedResult", (), {"returncode": 0})()},
             "post-reconcile recovery objective validator failed without exposing subprocess output"),
            ("timeout", {"error": subprocess.TimeoutExpired(["python"], 180, stderr=marker)},
             "post-reconcile recovery objective validator unavailable"),
            ("unavailable", {"error": OSError(marker)},
             "post-reconcile recovery objective validator unavailable"),
            ("invalid argument", {"error": ValueError(marker)},
             "post-reconcile recovery objective validator unavailable"),
            ("invalid type", {"error": TypeError(marker)},
             "post-reconcile recovery objective validator unavailable"),
        )
        for label, change, expected in cases:
            state.update({"returncode": 0, "error": None, "result": None})
            state.update(change)
            try:
                reconciler.run_validator(reconciler.VALIDATOR, "recovery objective validator")
            except reconciler.Fail as exc:
                require(str(exc) == expected and marker not in str(exc)
                        and (label not in ("timeout", "unavailable") or exc.__suppress_context__),
                        f"recovery objective reconcile {label} private failure drift")
            else:
                raise Fail(f"recovery objective reconcile {label} unexpectedly accepted")
        try:
            reconciler.run_validator(reconciler.VALIDATOR, "aggregate operability validator")
        except reconciler.Fail as exc:
            require(str(exc) == "unreviewed recovery objective post-reconcile validator",
                    "recovery objective reconcile label mismatch accepted")
        else:
            raise Fail("recovery objective reconcile label mismatch unexpectedly accepted")
        require(len(calls) == len(cases) + 2,
                "recovery objective reconcile subprocess multiplicity drift")
    finally:
        reconciler.subprocess.run = original_run
        for key, previous in prior_env.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous
    print("PASS: recovery objective reconcile post-validation transport private, bounded and environment-isolated (8 negatives)")




def prove_pinned_post_validator_execution(reconciler: object) -> None:
    """A parent swap after capture must execute only reviewed child bytes."""
    original_root = reconciler.ROOT
    original_validator = reconciler.VALIDATOR
    original_run = reconciler.subprocess.run
    with tempfile.TemporaryDirectory(prefix=".tmp-objective-post-pin-", dir=TMP_PARENT) as tmpdir:
        root = Path(tmpdir)
        parent = root / "scripts"
        parent.mkdir()
        reviewed = parent / reconciler.VALIDATOR_REL.name
        reviewed.write_text(
            "from pathlib import Path\nPath('executed.txt').write_text('reviewed')\n",
            encoding="utf-8",
        )
        redirected = root / "redirected"
        redirected.mkdir()
        canary = redirected / reviewed.name
        canary.write_text(
            "from pathlib import Path\nPath('executed.txt').write_text('redirected')\n",
            encoding="utf-8",
        )
        parked = root / "parked-scripts"
        swapped = False

        def swap_before_child(argv, **kwargs):
            nonlocal swapped
            require(not swapped and kwargs.get("input") == reviewed_source,
                    "recovery objective pinned child bytes drift")
            swapped = True
            parent.rename(parked)
            parent.symlink_to(redirected, target_is_directory=True)
            return original_run(argv, **kwargs)

        reviewed_source = reviewed.read_bytes()
        reconciler.ROOT, reconciler.VALIDATOR = root, reviewed
        reconciler.subprocess.run = swap_before_child
        try:
            reconciler.run_validator(reviewed, "recovery objective validator")
            require(swapped and (root / "executed.txt").read_text(encoding="utf-8") == "reviewed",
                    "recovery objective post-validator executed swapped child source")
            require(canary.read_text(encoding="utf-8").startswith("from pathlib"),
                    "recovery objective post-validator redirected canary mutated")
        finally:
            reconciler.subprocess.run = original_run
            reconciler.ROOT, reconciler.VALIDATOR = original_root, original_validator
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)
    print("PASS: recovery objective post-validator executes pinned bytes after parent swap")


def prove_strict_objective_json(reconciler: object) -> None:
    """Exercise the actual objective reconciler reader in disposable fixtures."""
    with isolated_authorities(reconciler):
        path = reconciler.REGISTRY
        original = path.read_bytes()
        expected = json.loads(original)
        require(reconciler.load(path) == expected, "objective reconcile JSON positive failed")
        marker = "PRIVATE_OBJECTIVE_RECONCILE_JSON_CANARY"
        original_open = reconciler.os.open

        def raced_open(candidate, flags, *args, **kwargs):
            if candidate == path.name and kwargs.get("dir_fd") is not None:
                require(flags & reconciler.os.O_NOFOLLOW
                        and flags & reconciler.os.O_NONBLOCK,
                        "reconciler JSON reader lost no-follow/nonblocking descriptor flags")
                raise OSError(marker)
            return original_open(candidate, flags, *args, **kwargs)

        reconciler.os.open = raced_open
        try:
            try:
                reconciler.load(path)
            except reconciler.Fail as exc:
                require(str(exc) == "recovery objective reconcile authority unreadable"
                        and exc.__suppress_context__ and marker not in str(exc),
                        "reconciler JSON raced-open private failure drift")
            else:
                raise Fail("reconciler JSON raced-open failure unexpectedly accepted")
        finally:
            reconciler.os.open = original_open
        require(reconciler.load(path) == expected,
                "reconciler JSON descriptor race did not preserve positive fixture")
        cases = (
            ("duplicate", b'{"x":1,"x":2}', "recovery objective reconcile JSON duplicate key refused"),
            ("nested-duplicate", b'{"x":{"y":1,"y":2}}',
             "recovery objective reconcile JSON duplicate key refused"),
            ("nan", b'{"x":NaN}', "recovery objective reconcile JSON nonfinite number refused"),
            ("infinity", b'{"x":Infinity}', "recovery objective reconcile JSON nonfinite number refused"),
            ("float-overflow", b'{"x":1e309}', "recovery objective reconcile JSON nonfinite number refused"),
            ("huge-integer", b'{"x":' + b"9" * 129 + b'}',
             "recovery objective reconcile JSON integer too large"),
            ("invalid-utf8", b'{"x":"' + bytes([255]) + b'"}',
             "recovery objective reconcile authority invalid UTF-8"),
            ("malformed", b'{"x":', "recovery objective reconcile JSON unreadable or invalid"),
            ("nonobject", b'[1,2]', "recovery objective reconcile JSON root must be object"),
            ("oversized", b"x" * (reconciler.MAX_AUTHORITY_BYTES + 1),
             "recovery objective reconcile authority size limit exceeded"),
        )
        for label, payload, failure in cases:
            path.write_bytes(payload)
            try:
                reconciler.load(path)
            except reconciler.Fail as exc:
                require(str(exc) == failure and marker not in str(exc),
                        f"objective reconcile JSON {label} wrong/private rejection")
            else:
                raise Fail(f"objective reconcile JSON {label} unexpectedly accepted")
        path.unlink()
        with tempfile.TemporaryDirectory(prefix="objective-reconcile-external-") as tmp:
            external = Path(tmp) / "private.json"
            external.write_text(marker, encoding="utf-8")
            path.symlink_to(external)
            try:
                reconciler.load(path)
            except reconciler.Fail as exc:
                require(str(exc) == "recovery objective reconcile authority path unsafe",
                        "objective reconcile JSON symlink wrong rejection")
            else:
                raise Fail("objective reconcile JSON symlink accepted")
            path.unlink()
            require(external.read_text(encoding="utf-8") == marker,
                    "objective reconcile JSON external canary changed")
        path.mkdir()
        try:
            reconciler.load(path)
        except reconciler.Fail as exc:
            require(str(exc) == "recovery objective reconcile authority path unsafe",
                    "objective reconcile JSON directory wrong rejection")
        else:
            raise Fail("objective reconcile JSON directory accepted")
        path.rmdir()
        path.write_bytes(original)
        require(reconciler.load(path) == expected,
                "objective reconcile JSON restored positive failed")
    print("PASS: actual recovery objective reconcile JSON reader positive and 13 fail-closed negatives")



def prove_json_parent_swap_rejection(reconciler: object) -> None:
    """A swapped parent after directory-FD acquisition must fail closed."""
    original_root = reconciler.ROOT
    original_open = reconciler.os.open
    with tempfile.TemporaryDirectory(prefix=".tmp-objective-json-parent-", dir=TMP_PARENT) as tmpdir:
        root = Path(tmpdir)
        parent = root / "contracts" / "operations"
        parent.mkdir(parents=True)
        reviewed = parent / "authority.json"
        reviewed.write_text('{"safe":true}', encoding="utf-8")
        redirected = root / "redirected"
        redirected.mkdir()
        canary = redirected / reviewed.name
        canary.write_text('{"safe":false}', encoding="utf-8")
        parked = root / "parked-operations"
        swapped = False

        def swap_at_leaf(candidate, flags, *args, **kwargs):
            nonlocal swapped
            if candidate == reviewed.name and kwargs.get("dir_fd") is not None and not swapped:
                swapped = True
                parent.rename(parked)
                parent.symlink_to(redirected, target_is_directory=True)
            return original_open(candidate, flags, *args, **kwargs)

        reconciler.ROOT = root
        reconciler.os.open = swap_at_leaf
        try:
            try:
                reconciler.load(reviewed)
            except reconciler.Fail as exc:
                require(str(exc) == "recovery objective reconcile authority unreadable"
                        and exc.__suppress_context__,
                        "recovery objective JSON parent swap rejection drift")
            else:
                raise Fail("recovery objective JSON parent swap unexpectedly accepted")
            require(swapped and canary.read_text(encoding="utf-8") == '{"safe":false}',
                    "recovery objective JSON parent swap canary drift")
        finally:
            reconciler.os.open = original_open
            reconciler.ROOT = original_root
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)
        require(reviewed.read_text(encoding="utf-8") == '{"safe":true}',
                "recovery objective JSON parent swap mutated reviewed fixture")
    print("PASS: recovery objective JSON parent swap fails closed with pinned directory FDs")


def main() -> int:
    require(RECONCILER.is_file(), "recovery objective reconciler missing")
    require(WORKFLOW.is_file(), "recovery objective workflow missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    prove_private_negative_failure_classifier()
    prove_pinned_reconciler_import()
    reconciler = load_reconciler()

    canonical_contract = CONTRACT.read_bytes()
    canonical_status = STATUS.read_bytes()
    canonical_contract_mode = file_mode(CONTRACT)
    canonical_status_mode = file_mode(STATUS)
    validate_atomic_diagnostic_publication()

    substitutions = (
        ("CONTRACT", reconciler.REGISTRY, "recovery objective contract authority drift"),
        ("REGISTRY", reconciler.CONTRACT, "recovery objective registry authority drift"),
        ("WRITER", reconciler.VALIDATOR, "recovery objective writer authority drift"),
        ("VALIDATOR", reconciler.OPERABILITY_VALIDATOR, "recovery objective validator authority drift"),
        ("OPERABILITY_VALIDATOR", reconciler.VALIDATOR, "operability validator authority drift"),
        ("STATUS", reconciler.CONTRACT, "production operability status authority drift"),
    )
    for attribute, replacement, expected in substitutions:
        original = getattr(reconciler, attribute)
        setattr(reconciler, attribute, replacement)
        try:
            expect_domain_fail(f"{attribute.lower()} substitution", reconciler.main, reconciler.Fail, expected)
            assert_canonical_unchanged(
                canonical_contract,
                canonical_status,
                attribute.lower(),
                canonical_contract_mode,
                canonical_status_mode,
            )
        finally:
            setattr(reconciler, attribute, original)

    original_contract_path = reconciler.CONTRACT
    original_status_path = reconciler.STATUS
    reconciler.CONTRACT = reconciler.REGISTRY
    reconciler.STATUS = reconciler.REGISTRY
    try:
        expect_domain_fail(
            "paired contract/status fixture substitution",
            reconciler.main,
            reconciler.Fail,
            "recovery objective contract authority drift",
        )
        assert_canonical_unchanged(
            canonical_contract,
            canonical_status,
            "paired fixture substitution",
            canonical_contract_mode,
            canonical_status_mode,
        )
    finally:
        reconciler.CONTRACT = original_contract_path
        reconciler.STATUS = original_status_path

    prefix = reconciler.EVIDENCE_PREFIX
    old = prefix + " old"
    new = prefix + " new"
    values = ["before", old, "after"]
    reconciler.replace_single_prefixed(values, prefix, new)
    require(values == ["before", new, "after"], "recovery objective evidence moved during replacement")
    values = [old, prefix + " duplicate"]
    expect_domain_fail(
        "duplicate recovery objective status evidence",
        lambda: reconciler.replace_single_prefixed(values, prefix, new),
        reconciler.Fail,
        "duplicate authority evidence prefix",
    )
    require(values == [old, prefix + " duplicate"], "duplicate evidence rejection mutated status ordering")
    print("PASS preserve: recovery objective evidence ordering is deterministic")

    with tempfile.TemporaryDirectory(prefix=".tmp-recovery-objective-reconcile-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_domain_fail("invalid UTF-8 objective authority", lambda: reconciler.load(invalid_utf8), reconciler.Fail)

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_domain_fail("unreadable objective authority directory", lambda: reconciler.load(directory_authority), reconciler.Fail)

        with tempfile.TemporaryDirectory(prefix="memory-os-objective-outside-") as outside_dir:
            outside = Path(outside_dir) / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            expect_domain_fail("objective authority escapes repository", lambda: reconciler.load(outside), reconciler.Fail)

    prove_strict_objective_json(reconciler)
    prove_json_parent_swap_rejection(reconciler)
    prove_private_writer_import(reconciler)
    prove_pinned_writer_import(reconciler)
    prove_reference_path_identity(reconciler)
    prove_private_authority_path_diagnostics(reconciler)
    prove_private_delegated_registry_errors(reconciler)
    prove_private_post_reconcile_transport(reconciler)
    prove_pinned_post_validator_execution(reconciler)
    prove_private_atomic_write_path_guards(reconciler)
    prove_atomic_target_identity_guards(reconciler)
    prove_atomic_temp_descriptor_identity(reconciler)
    prove_atomic_parent_swap_before_commit(reconciler)
    prove_atomic_parent_swap_during_stage(reconciler)
    prove_atomic_parent_swap_cleanup_on_replace_error(reconciler)
    prove_atomic_parent_swap_inside_replace(reconciler)
    prove_atomic_write_mode_preservation(reconciler)
    prove_atomic_descriptor_cleanup(reconciler)
    prove_atomic_primary_cleanup_precedence(reconciler)
    prove_atomic_non_oserror_cleanup_precedence(reconciler)
    with isolated_authorities(reconciler):
        prove_atomic_write_failure(reconciler)
    prove_rollback_attempts_all_restores(reconciler)
    with isolated_authorities(reconciler):
        prove_primary_and_rollback_failures_are_preserved(reconciler)
    with isolated_authorities(reconciler):
        prove_second_replace_transaction_rollback(reconciler)
    with isolated_authorities(reconciler):
        prove_aggregate_validator_rollback(reconciler)

    assert_canonical_unchanged(
        canonical_contract,
        canonical_status,
        "isolated transactional negatives",
        canonical_contract_mode,
        canonical_status_mode,
    )
    print("PASS boundary: transactional recovery objective negatives keep canonical authorities read-only")
    print("paired recovery objective fixture substitution accepted: false")
    print("recovery objective data/executable substitution accepted: false")
    print("recovery objective evidence reordering accepted: false")
    print("non-atomic recovery objective authority write accepted: false")
    print("recovery objective authority mode drift accepted: false")
    print("non-atomic recovery objective diagnostic write accepted: false")
    print("Recovery objective reconcile negative suite PASS")
    print("objective created or defaulted: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RECOVERY OBJECTIVE RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
