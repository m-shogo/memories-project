#!/usr/bin/env python3
"""Prove generation-evidence authority loading and append admission fail closed."""

from __future__ import annotations

import copy
import errno
import importlib.machinery
import importlib.util
import os
import stat
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-generation-evidence.py"
RECONCILE_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence-reconcile-negative.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


MAX_MODULE_BYTES = 1024 * 1024


def load_module(path: Path, name: str):
    """Load bounded source bytes from a checked repository descriptor chain."""
    try:
        relative = path.relative_to(ROOT)
        require(path.resolve(strict=True) == ROOT.resolve() / relative,
                "cannot load generation evidence authority")
        checked = path.lstat()
        require(stat.S_ISREG(checked.st_mode), "cannot load generation evidence authority")
        require(all(type(getattr(os, flag, None)) is int and getattr(os, flag) > 0
                    for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY")),
                "cannot load generation evidence authority")
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
                    "cannot load generation evidence authority")
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
            require(not cleanup_failed, "cannot load generation evidence authority")
        require(len(source) <= MAX_MODULE_BYTES, "cannot load generation evidence authority")

        class PinnedSourceLoader(importlib.machinery.SourceFileLoader):
            def get_code(self, fullname):
                require(fullname == name, "cannot load generation evidence authority")
                return compile(source, str(path), "exec")

        spec = importlib.util.spec_from_file_location(
            name, path, loader=PinnedSourceLoader(name, str(path)))
        require(spec is not None and spec.loader is not None,
                "cannot load generation evidence authority")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:
        raise Fail("cannot load generation evidence authority") from None
    return module


def prove_pinned_module_import() -> None:
    """A swapped ancestor after capture cannot select redirected source."""
    original_spec = importlib.util.spec_from_file_location
    with tempfile.TemporaryDirectory(prefix=".generation-evidence-import-", dir=ROOT) as raw:
        sandbox = Path(raw)
        parent = sandbox / "trusted"
        parent.mkdir()
        source = parent / "module.py"
        parked = sandbox / "parked"
        redirected = sandbox / "redirected"
        redirected.mkdir()
        canary = redirected / "module.py"
        source.write_text("VALUE = 'pinned'\n", encoding="utf-8")
        canary.write_text("raise RuntimeError('PRIVATE_GENERATION_IMPORT_CANARY')\n",
                          encoding="utf-8")
        swapped = False
        try:
            require(load_module(source, "generation_import_positive").VALUE == "pinned",
                    "generation evidence pinned import positive failed")

            def swap_after_read(name, location, *args, **kwargs):
                nonlocal swapped
                if not swapped and Path(location) == source:
                    swapped = True
                    parent.rename(parked)
                    parent.symlink_to(redirected, target_is_directory=True)
                return original_spec(name, location, *args, **kwargs)

            importlib.util.spec_from_file_location = swap_after_read
            loaded = load_module(source, "generation_import_parent_swap")
            require(swapped and loaded.VALUE == "pinned",
                    "generation evidence import executed redirected source")
            require(canary.read_text(encoding="utf-8") ==
                    "raise RuntimeError('PRIVATE_GENERATION_IMPORT_CANARY')\n",
                    "generation evidence import changed redirected canary")
        finally:
            importlib.util.spec_from_file_location = original_spec
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)
    require(callable(getattr(load_module(VALIDATOR, "generation_import_restored"), "main", None)),
            "generation evidence pinned import canonical restoration failed")
    print("PASS: generation evidence load negative executes pinned source after parent swap")


def prove_pinned_module_unsafe_sources() -> None:
    """Reject oversized source, symlink, FIFO, and unavailable safety flags."""
    with tempfile.TemporaryDirectory(prefix=".generation-evidence-unsafe-", dir=ROOT) as raw:
        sandbox = Path(raw)
        good = sandbox / "good.py"
        good.write_text("VALUE = 'safe'\n", encoding="utf-8")
        oversized = sandbox / "oversized.py"
        oversized.write_bytes(b"x" * (MAX_MODULE_BYTES + 1))
        link = sandbox / "linked.py"
        link.symlink_to(good)
        fifo = sandbox / "fifo.py"
        os.mkfifo(fifo)

        def rejected(label: str, candidate: Path) -> None:
            try:
                load_module(candidate, "generation_import_unsafe")
            except Fail as exc:
                require(str(exc) == "cannot load generation evidence authority"
                        and exc.__suppress_context__ and exc.__cause__ is None,
                        "generation import unsafe " + label + " leaked private error")
            else:
                raise Fail("generation import unsafe " + label + " accepted")

        for label, candidate in (("oversized", oversized), ("symlink", link), ("FIFO", fifo)):
            rejected(label, candidate)
        for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY"):
            original = getattr(os, flag)
            try:
                for invalid in (None, 0):
                    setattr(os, flag, invalid)
                    rejected(flag + " unsupported", good)
            finally:
                setattr(os, flag, original)
        require(load_module(good, "generation_import_unsafe_restored").VALUE == "safe",
                "generation import unsafe canonical restoration failed")
    print("PASS: generation evidence pinned loader rejects oversized/symlink/FIFO/unsafe flags")


def prove_pinned_module_fd_cleanup() -> None:
    """Injected fdopen/close errors must release every owned descriptor."""
    for fault in ("fdopen", "close"):
        original_open, original_fdopen, original_close = os.open, os.fdopen, os.close
        opened = []
        injected = False

        def tracked_open(*args, **kwargs):
            descriptor = original_open(*args, **kwargs)
            opened.append(descriptor)
            return descriptor

        def broken_fdopen(descriptor, *args, **kwargs):
            nonlocal injected
            if fault == "fdopen" and not injected:
                injected = True
                raise OSError(errno.EIO, "PRIVATE_GENERATION_FDOPEN_CANARY")
            return original_fdopen(descriptor, *args, **kwargs)

        def broken_close(descriptor):
            nonlocal injected
            if fault == "close" and descriptor in opened and not injected:
                injected = True
                original_close(descriptor)
                raise OSError(errno.EIO, "PRIVATE_GENERATION_CLOSE_CANARY")
            return original_close(descriptor)

        try:
            os.open, os.fdopen, os.close = tracked_open, broken_fdopen, broken_close
            try:
                load_module(VALIDATOR, "generation_import_fd_fault")
            except Fail as exc:
                require(str(exc) == "cannot load generation evidence authority"
                        and exc.__suppress_context__ and exc.__cause__ is None,
                        "generation import " + fault + " leaked private exception")
            else:
                raise Fail("generation import " + fault + " fault accepted")
        finally:
            os.open, os.fdopen, os.close = original_open, original_fdopen, original_close
        require(injected and len(opened) >= 3,
                "generation import " + fault + " injection not reached")
        for descriptor in opened:
            try:
                os.fstat(descriptor)
            except OSError as exc:
                require(exc.errno == errno.EBADF,
                        "generation import " + fault + " unexpected descriptor error")
            else:
                raise Fail("generation import " + fault + " leaked descriptor")
    require(callable(getattr(load_module(VALIDATOR, "generation_import_fd_restored"), "main", None)),
            "generation import FD fault canonical restoration failed")
    print("PASS: generation evidence pinned loader fdopen/close faults clean owned descriptors")


def pin_checked_helper_parent(path: Path) -> int:
    """Walk from a trusted repository/temp anchor, never through a symlinked ancestor."""
    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY"),
            "generation-evidence fixture guard no-follow directory open unsupported")
    anchor = ROOT if path.is_relative_to(ROOT) else Path(tempfile.gettempdir())
    try:
        relative = path.parent.relative_to(anchor)
    except ValueError as exc:
        raise Fail("generation-evidence fixture guard parent outside trusted roots") from exc
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    require(anchor.is_dir() and not anchor.is_symlink(),
            "generation-evidence fixture guard trusted anchor missing or symlinked")
    try:
        fd = os.open(anchor, flags)
    except OSError as exc:
        raise Fail("generation-evidence fixture guard anchor open failed") from exc
    try:
        opened = os.fstat(fd)
        entry = anchor.lstat()
        require(
            stat.S_ISDIR(entry.st_mode)
            and (entry.st_dev, entry.st_ino) == (opened.st_dev, opened.st_ino),
            "generation-evidence fixture guard trusted anchor identity drift",
        )
        cursor = anchor
        for part in relative.parts:
            cursor = cursor / part
            require(cursor.is_dir() and not cursor.is_symlink(),
                    "generation-evidence fixture guard ancestor missing or symlinked")
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
            opened = os.fstat(fd)
            entry = cursor.lstat()
            require(
                stat.S_ISDIR(entry.st_mode)
                and (entry.st_dev, entry.st_ino) == (opened.st_dev, opened.st_ino),
                "generation-evidence fixture guard ancestor identity drift",
            )
        return fd
    except OSError as exc:
        os.close(fd)
        raise Fail("generation-evidence fixture guard parent open failed") from exc
    except BaseException:
        os.close(fd)
        raise


MAX_HELPER_SOURCE_BYTES = 1024 * 1024


def load_pinned_fixture_guard(path: Path, name: str):
    """Bind every checked ancestor and the helper leaf to pinned FDs."""
    parent_fd = pin_checked_helper_parent(path)
    try:
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        except OSError as exc:
            raise Fail("generation-evidence fixture guard source open failed") from exc
        try:
            opened = os.fstat(fd)
            entry = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
            require(
                stat.S_ISREG(opened.st_mode) and stat.S_ISREG(entry.st_mode)
                and (opened.st_dev, opened.st_ino) == (entry.st_dev, entry.st_ino),
                "generation-evidence fixture guard source identity drift",
            )
            with os.fdopen(os.dup(fd), "rb") as stream:
                source = stream.read(MAX_HELPER_SOURCE_BYTES + 1)
            require(len(source) <= MAX_HELPER_SOURCE_BYTES,
                    "fixture guard pinned source oversized")
            spec = importlib.util.spec_from_file_location(name, path)
            require(spec is not None and spec.loader is not None,
                    "generation-evidence fixture guard cannot load")
            module = importlib.util.module_from_spec(spec)
            exec(compile(source, str(path), "exec"), module.__dict__)
            return module
        except OSError as exc:
            raise Fail("generation-evidence fixture guard pinned source read failed") from exc
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)


def guarded_temporary_directory(*, prefix: str, parent: Path):
    # Reuse the tested sibling negative-harness parent guard; never create
    # repository-local fixtures through an unchecked symlinked ancestor.
    require(RECONCILE_NEGATIVE.is_file() and not RECONCILE_NEGATIVE.is_symlink(),
            "generation reconcile fixture guard source missing or symlinked")
    module = load_pinned_fixture_guard(
        RECONCILE_NEGATIVE, "memory_os_generation_reconcile_fixture_guard_load")
    require(callable(getattr(module, "guarded_temporary_directory", None)),
            "generation reconcile fixture guard callable missing")
    try:
        return module.guarded_temporary_directory(prefix=prefix, parent=parent)
    except module.Fail as exc:
        raise Fail(str(exc)) from exc


def prove_helper_source_symlink_rejected() -> None:
    global RECONCILE_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="generation-evidence-helper-source-") as raw:
        sandbox = Path(raw)
        real = sandbox / "real-helper.py"
        real.touch()
        link = sandbox / "helper.py"
        link.symlink_to(real)
        original = RECONCILE_NEGATIVE
        try:
            RECONCILE_NEGATIVE = link
            try:
                with guarded_temporary_directory(prefix=".tmp-must-not-create-", parent=TMP_PARENT):
                    raise Fail("generation-evidence symlinked fixture helper accepted")
            except Fail as exc:
                require(str(exc) == "generation reconcile fixture guard source missing or symlinked",
                        f"generation-evidence fixture helper rejected at wrong boundary: {exc}")
            else:
                raise Fail("generation-evidence symlinked fixture helper accepted")
        finally:
            RECONCILE_NEGATIVE = original
    print("PASS: generation-evidence fixture helper symlink rejected before import")


def prove_helper_source_swap_during_import_is_pinned() -> None:
    # Establish valid helper behavior before swapping its name after FD pinning.
    global RECONCILE_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="generation-evidence-helper-import-race-") as raw:
        sandbox = Path(raw)
        trusted = sandbox / "helper.py"
        parked = sandbox / "original-helper.py"
        untrusted = sandbox / "untrusted.py"
        trusted.write_text(
            "class Fail(RuntimeError):\n    pass\n\n"
            "def guarded_temporary_directory(*, prefix, parent):\n"
            "    return ('pinned-source', prefix)\n",
            encoding="utf-8",
        )
        untrusted.write_text("raise RuntimeError('untrusted helper executed')\n", encoding="utf-8")
        original_path = RECONCILE_NEGATIVE
        original_spec = importlib.util.spec_from_file_location
        swapped = False
        try:
            RECONCILE_NEGATIVE = trusted
            require(
                guarded_temporary_directory(prefix=".tmp-positive-", parent=TMP_PARENT)
                == ("pinned-source", ".tmp-positive-"),
                "generation-evidence helper pinned import positive control failed",
            )

            def swap_before_spec(name, location, *args, **kwargs):
                nonlocal swapped
                if not swapped and Path(location) == trusted:
                    swapped = True
                    trusted.rename(parked)
                    trusted.symlink_to(untrusted)
                return original_spec(name, location, *args, **kwargs)

            importlib.util.spec_from_file_location = swap_before_spec
            require(
                guarded_temporary_directory(prefix=".tmp-race-", parent=TMP_PARENT)
                == ("pinned-source", ".tmp-race-"),
                "generation-evidence helper import executed substituted source",
            )
            require(swapped and trusted.is_symlink() and parked.is_file(),
                    "generation-evidence helper race probe did not substitute checked source")
        finally:
            importlib.util.spec_from_file_location = original_spec
            RECONCILE_NEGATIVE = original_path
    print("PASS: generation-evidence load helper import uses pinned source after pathname substitution")


def prove_helper_parent_swap_after_pin_uses_original_source() -> None:
    global RECONCILE_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="generation-evidence-helper-parent-race-") as raw:
        sandbox = Path(raw)
        trusted_parent = sandbox / "trusted"
        parked_parent = sandbox / "parked"
        untrusted_parent = sandbox / "untrusted"
        trusted_parent.mkdir()
        untrusted_parent.mkdir()
        (trusted_parent / "helper.py").write_text(
            "class Fail(RuntimeError):\n    pass\n\n"
            "def guarded_temporary_directory(*, prefix, parent):\n"
            "    return ('pinned-parent', prefix)\n",
            encoding="utf-8",
        )
        (untrusted_parent / "helper.py").write_text(
            "raise RuntimeError('untrusted parent helper executed')\n", encoding="utf-8")
        original_path = RECONCILE_NEGATIVE
        original_open = os.open
        swapped = False
        try:
            RECONCILE_NEGATIVE = trusted_parent / "helper.py"
            require(
                guarded_temporary_directory(prefix=".tmp-positive-", parent=TMP_PARENT)
                == ("pinned-parent", ".tmp-positive-"),
                "generation-evidence parent-pinned helper positive control failed",
            )

            def swap_before_leaf_open(target, flags, *args, **kwargs):
                nonlocal swapped
                if not swapped and target == "helper.py" and kwargs.get("dir_fd") is not None:
                    swapped = True
                    trusted_parent.rename(parked_parent)
                    trusted_parent.symlink_to(untrusted_parent, target_is_directory=True)
                return original_open(target, flags, *args, **kwargs)

            os.open = swap_before_leaf_open
            require(
                guarded_temporary_directory(prefix=".tmp-parent-race-", parent=TMP_PARENT)
                == ("pinned-parent", ".tmp-parent-race-"),
                "generation-evidence helper import followed substituted parent",
            )
            require(swapped and trusted_parent.is_symlink() and (parked_parent / "helper.py").is_file(),
                    "generation-evidence helper parent race did not substitute checked parent")
        finally:
            os.open = original_open
            RECONCILE_NEGATIVE = original_path
    print("PASS: generation-evidence load helper parent swap preserves pinned source")


def prove_helper_ancestor_swap_during_fd_walk_rejected() -> None:
    # A leaf/parent O_NOFOLLOW alone cannot protect a mutable higher ancestor.
    # Swap an owned nonterminal directory after it was pinned, before descent.
    global RECONCILE_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="generation-evidence-helper-ancestor-race-") as raw:
        sandbox = Path(raw)
        checked_ancestor = sandbox / "checked"
        parked_ancestor = sandbox / "parked"
        redirect_ancestor = sandbox / "redirect"
        checked_parent = checked_ancestor / "nested"
        redirect_parent = redirect_ancestor / "nested"
        checked_parent.mkdir(parents=True)
        redirect_parent.mkdir(parents=True)
        (checked_parent / "helper.py").write_text(
            "class Fail(RuntimeError):\n    pass\n\n"
            "def guarded_temporary_directory(prefix, parent):\n"
            "    return ('pinned-ancestor', prefix)\n",
            encoding="utf-8",
        )
        (redirect_parent / "helper.py").write_text(
            "raise RuntimeError('untrusted ancestor helper executed')\n", encoding="utf-8"
        )
        original_path = RECONCILE_NEGATIVE
        original_open = os.open
        swapped = False
        try:
            RECONCILE_NEGATIVE = checked_parent / "helper.py"
            require(
                guarded_temporary_directory(prefix=".tmp-positive-", parent=TMP_PARENT)
                == ("pinned-ancestor", ".tmp-positive-"),
                "generation-evidence load ancestor helper positive control failed",
            )

            def swap_before_descend(target, flags, *args, **kwargs):
                nonlocal swapped
                if not swapped and target == "nested" and kwargs.get("dir_fd") is not None:
                    swapped = True
                    checked_ancestor.rename(parked_ancestor)
                    checked_ancestor.symlink_to(redirect_ancestor, target_is_directory=True)
                return original_open(target, flags, *args, **kwargs)

            os.open = swap_before_descend
            try:
                guarded_temporary_directory(prefix=".tmp-ancestor-race-", parent=TMP_PARENT)
            except Fail as exc:
                require(
                    str(exc) == "generation-evidence fixture guard ancestor identity drift",
                    f"generation-evidence helper ancestor swap rejected at wrong boundary: {exc}",
                )
            else:
                raise Fail("generation-evidence load helper ancestor swap accepted")
            require(swapped and checked_ancestor.is_symlink()
                    and (parked_ancestor / "nested/helper.py").is_file(),
                    "generation-evidence helper ancestor swap did not preserve pinned original")
            require((redirect_parent / "helper.py").read_text(encoding="utf-8")
                    == "raise RuntimeError('untrusted ancestor helper executed')\n",
                    "generation-evidence helper ancestor swap modified untrusted source")
        finally:
            os.open = original_open
            RECONCILE_NEGATIVE = original_path
    print("PASS: generation-evidence load helper ancestor swap fails closed during FD walk")


def expect_domain_fail(name: str, action: Callable[[], object], fail_type: type[BaseException]) -> None:
    try:
        action()
    except fail_type:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def exercise_loads(label: str, module, tmp: Path, outside: Path) -> None:
    invalid_utf8 = tmp / f"{label}-invalid-utf8.json"
    invalid_utf8.write_bytes(b"{\xff}")
    expect_domain_fail(f"{label} invalid UTF-8 authority JSON", lambda: module.load(invalid_utf8), module.Fail)

    directory_authority = tmp / f"{label}-directory-authority.json"
    directory_authority.mkdir()
    expect_domain_fail(f"{label} authority path is unreadable directory", lambda: module.load(directory_authority), module.Fail)

    loop_authority = tmp / f"{label}-loop-authority.json"
    loop_authority.symlink_to(loop_authority.name)
    expect_domain_fail(f"{label} authority symlink loop", lambda: module.load(loop_authority), module.Fail)

    expect_domain_fail(f"{label} authority path escapes repository", lambda: module.load(outside), module.Fail)


def exercise_writer_loads(writer, tmp: Path) -> None:
    invalid_utf8 = tmp / "writer-invalid-utf8.json"
    invalid_utf8.write_bytes(b"{\xff}")
    expect_domain_fail("writer invalid UTF-8 external record", lambda: writer.load(invalid_utf8), writer.Fail)

    directory_record = tmp / "writer-directory-record.json"
    directory_record.mkdir()
    expect_domain_fail("writer unreadable external record directory", lambda: writer.load(directory_record), writer.Fail)

    ref_loop = tmp / "loop-evidence-ref.json"
    ref_loop.symlink_to(ref_loop.name)
    ref_loop_relative = ref_loop.relative_to(ROOT).as_posix()
    expect_domain_fail(
        "generation evidence repository ref symlink loop",
        lambda: writer.repo_ref(ref_loop_relative, "negativeEvidenceRef"),
        writer.Fail,
    )


def exercise_writer_module_containment(writer, tmp: Path, outside_dir: Path) -> None:
    outside_module = outside_dir / "outside-writer.py"
    outside_module.write_text("VALUE = 1\n", encoding="utf-8")
    escaped_link = tmp / "escaped-writer.py"
    escaped_link.symlink_to(outside_module)
    loop_link = tmp / "loop-writer.py"
    loop_link.symlink_to(loop_link.name)

    original_drill_writer = writer.DRILL_REQUEST_WRITER
    original_non_resurrection_writer = writer.NON_RESURRECTION_WRITER
    try:
        writer.DRILL_REQUEST_WRITER = outside_module
        expect_domain_fail("drill writer absolute path escapes repository", writer.load_drill_writer, writer.Fail)
        writer.DRILL_REQUEST_WRITER = escaped_link
        expect_domain_fail("drill writer repository symlink escapes repository", writer.load_drill_writer, writer.Fail)
        writer.DRILL_REQUEST_WRITER = loop_link
        expect_domain_fail("drill writer repository symlink loop", writer.load_drill_writer, writer.Fail)

        writer.NON_RESURRECTION_WRITER = outside_module
        expect_domain_fail("typed writer absolute path escapes repository", writer.load_non_resurrection_writer, writer.Fail)
        writer.NON_RESURRECTION_WRITER = escaped_link
        expect_domain_fail("typed writer repository symlink escapes repository", writer.load_non_resurrection_writer, writer.Fail)
        writer.NON_RESURRECTION_WRITER = loop_link
        expect_domain_fail("typed writer repository symlink loop", writer.load_non_resurrection_writer, writer.Fail)
    finally:
        writer.DRILL_REQUEST_WRITER = original_drill_writer
        writer.NON_RESURRECTION_WRITER = original_non_resurrection_writer


def exercise_writer_registry_append_guard(writer) -> None:
    healthy = {
        "schemaVersion": "memory-os-backup-restore-generation-evidence-registry.v1",
        "appendOnly": True,
        "registeredEvidenceCount": 0,
        "drillRequestBoundEvidenceCount": 0,
        "completeGenerationBoundBackupCount": 0,
        "completeGenerationBoundRestoreCount": 0,
        "productionEquivalentRecoveryCandidateCount": 0,
        "records": [],
        "productionEvidence": False,
        "productionReady": False,
    }
    require(writer.validate_registry_for_append(copy.deepcopy(healthy)) == [], "healthy empty generation registry append authority rejected")
    print("PASS accept: healthy empty generation registry append authority")

    def reject(name: str, mutate: Callable[[dict], None]) -> None:
        value = copy.deepcopy(healthy)
        mutate(value)
        expect_domain_fail(name, lambda: writer.validate_registry_for_append(value), writer.Fail)

    reject("generation writer registry schema drift before append", lambda value: value.update(schemaVersion="memory-os-backup-restore-generation-evidence-registry.v0"))
    reject("generation writer appendOnly disabled before append", lambda value: value.update(appendOnly=False))
    reject("generation writer registeredEvidenceCount drift before append", lambda value: value.update(registeredEvidenceCount=1))
    reject("generation writer boolean registeredEvidenceCount before append", lambda value: value.update(registeredEvidenceCount=True))
    reject("generation writer drillRequestBoundEvidenceCount drift before append", lambda value: value.update(drillRequestBoundEvidenceCount=1))
    reject("generation writer boolean backup count before append", lambda value: value.update(completeGenerationBoundBackupCount=True))
    reject("generation writer restore count drift before append", lambda value: value.update(completeGenerationBoundRestoreCount=1))
    reject("generation writer candidate count drift before append", lambda value: value.update(productionEquivalentRecoveryCandidateCount=1))
    reject("generation writer production evidence boundary drift before append", lambda value: value.update(productionEvidence=True))
    reject("generation writer production ready boundary drift before append", lambda value: value.update(productionReady=True))


def exercise_writer_rollback_diagnostics(writer) -> None:
    with guarded_temporary_directory(prefix=".tmp-generation-evidence-writer-rollback-diagnostics-", parent=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        registry = tmp / writer.CANONICAL_REGISTRY.name
        registry.write_bytes(writer.CANONICAL_REGISTRY.read_bytes())
        registry.chmod(0o640)
        value = writer.load(registry)

        original_registry = writer.REGISTRY
        original_validate = writer.validate_registry_for_append
        original_restore = writer.atomic_restore
        rollback_attempted = False

        def reject_post_append(_registry: dict) -> list[dict]:
            raise writer.Fail("synthetic generation evidence append post-validator rejection")

        def reject_rollback(_payload: bytes, _mode: int) -> None:
            nonlocal rollback_attempted
            rollback_attempted = True
            raise writer.Fail("synthetic generation evidence append rollback restore rejection")

        writer.REGISTRY = registry
        writer.validate_registry_for_append = reject_post_append
        writer.atomic_restore = reject_rollback
        try:
            try:
                writer.write_registry_transactionally(value)
            except writer.Fail as exc:
                message = str(exc)
                require(message == "generation evidence append failed; rollback incomplete"
                        and exc.__suppress_context__,
                        "generation evidence writer rollback failure class leaked private details")
                require("synthetic generation evidence" not in message,
                        "generation evidence writer rollback diagnostic leaked private canary")
            else:
                raise Fail("generation evidence writer rollback diagnostic failure unexpectedly accepted")
        finally:
            writer.atomic_restore = original_restore
            writer.validate_registry_for_append = original_validate
            writer.REGISTRY = original_registry

        require(rollback_attempted, "generation evidence writer rollback diagnostics did not attempt rollback")

    print("PASS diagnostics: generation evidence writer redacts primary and rollback failures")


def exercise_reconciler_transaction_rollback(reconciler) -> None:
    output_names = ("REGISTRY", "CONTRACT", "BINDING", "STATUS")
    for fail_index in (2, 3, 4):
        with guarded_temporary_directory(prefix=f".tmp-generation-evidence-transaction-{fail_index}-", parent=TMP_PARENT) as tmpdir:
            tmp = Path(tmpdir)
            originals = {name: getattr(reconciler, name) for name in output_names}
            copies: dict[str, Path] = {}
            expected: dict[str, bytes] = {}
            for name, source in originals.items():
                target = tmp / source.name
                payload = source.read_bytes()
                target.write_bytes(payload)
                target.chmod(0o640)
                copies[name] = target
                expected[name] = payload

            original_enforce = reconciler.enforce_runtime_authorities
            original_replace = reconciler.os.replace
            replace_calls = 0

            def fail_nth_replace(src: str | Path, dst: str | Path) -> None:
                nonlocal replace_calls
                replace_calls += 1
                if replace_calls == fail_index:
                    raise OSError(f"injected generation-evidence replace failure #{fail_index}")
                original_replace(src, dst)

            for name, target in copies.items():
                setattr(reconciler, name, target)
            reconciler.enforce_runtime_authorities = lambda: None
            reconciler.os.replace = fail_nth_replace
            try:
                expect_domain_fail(
                    f"generation evidence transaction replace #{fail_index}",
                    reconciler.main,
                    reconciler.Fail,
                )
            finally:
                reconciler.os.replace = original_replace
                reconciler.enforce_runtime_authorities = original_enforce
                for name, source in originals.items():
                    setattr(reconciler, name, source)

            require(replace_calls >= fail_index + 4, f"generation evidence rollback did not restore all authorities after replace #{fail_index}: {replace_calls}")
            for name, target in copies.items():
                require(target.read_bytes() == expected[name], f"generation evidence {name} bytes changed after replace #{fail_index} rollback")
                require((target.stat().st_mode & 0o7777) == 0o640, f"generation evidence {name} mode changed after replace #{fail_index} rollback")
            leftovers = list(tmp.glob(".*.tmp"))
            require(not leftovers, f"generation evidence replace #{fail_index} rollback left temporary files: {leftovers}")

    print("PASS rollback: generation evidence 4-authority transaction restored exact bytes+mode after middle/last replace failures")


def exercise_reconciler_rollback_diagnostics(reconciler) -> None:
    output_names = ("REGISTRY", "CONTRACT", "BINDING", "STATUS")
    with guarded_temporary_directory(prefix=".tmp-generation-evidence-rollback-diagnostics-", parent=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        originals = {name: getattr(reconciler, name) for name in output_names}
        copies: dict[str, Path] = {}
        for name, source in originals.items():
            target = tmp / source.name
            target.write_bytes(source.read_bytes())
            target.chmod(0o640)
            copies[name] = target

        original_enforce = reconciler.enforce_runtime_authorities
        original_post_validator = reconciler.run_post_validator
        original_restore = reconciler.restore_original_text
        rollback_attempted = False

        def reject_post_validator(_path: Path, _expected_relative: Path, _label: str) -> None:
            raise reconciler.Fail("synthetic generation evidence post-validator rejection")

        def reject_rollback(_original_text: dict[Path, str]) -> None:
            nonlocal rollback_attempted
            rollback_attempted = True
            raise reconciler.Fail("synthetic generation evidence rollback restore rejection")

        for name, target in copies.items():
            setattr(reconciler, name, target)
        reconciler.enforce_runtime_authorities = lambda: None
        reconciler.run_post_validator = reject_post_validator
        reconciler.restore_original_text = reject_rollback
        try:
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                message = str(exc)
                require("synthetic generation evidence post-validator rejection" in message, "generation evidence rollback diagnostics lost primary validator rejection")
                require("rollback incomplete" in message, "generation evidence rollback diagnostics missing incomplete marker")
                require("synthetic generation evidence rollback restore rejection" in message, "generation evidence rollback diagnostics lost rollback rejection")
            else:
                raise Fail("generation evidence rollback diagnostic failure unexpectedly accepted")
        finally:
            reconciler.restore_original_text = original_restore
            reconciler.run_post_validator = original_post_validator
            reconciler.enforce_runtime_authorities = original_enforce
            for name, source in originals.items():
                setattr(reconciler, name, source)

        require(rollback_attempted, "generation evidence rollback diagnostics did not attempt rollback")

    print("PASS diagnostics: generation evidence reconcile preserves primary validator + rollback failure")


def prove_generation_evidence_writer_json_reader(writer) -> None:
    """Prove the actual generation writer reader fails closed before admission."""
    protected_paths = (writer.CONTRACT, writer.REGISTRY, writer.GEN_REGISTRY,
                       writer.OBJECTIVES_REGISTRY, writer.DRILL_REQUEST_REGISTRY)
    before = tuple(path.read_bytes() for path in protected_paths)
    with guarded_temporary_directory(prefix=".tmp-generation-writer-json-", parent=TMP_PARENT) as directory:
        path = Path(directory) / "writer-candidate.json"
        positive = b'{"safe":true,"nested":{"count":1}}'
        path.write_bytes(positive)
        require(writer.load(path) == {"safe": True, "nested": {"count": 1}},
                "generation evidence writer JSON positive control failed")
        cases = (
            ("duplicate root", b'{"safe":true,"safe":false}', "generation evidence writer JSON duplicate key refused"),
            ("duplicate nested", b'{"nested":{"a":1,"a":2}}', "generation evidence writer JSON duplicate key refused"),
            ("NaN", b'{"number":NaN}', "generation evidence writer JSON nonfinite number refused"),
            ("Infinity", b'{"number":Infinity}', "generation evidence writer JSON nonfinite number refused"),
            ("negative Infinity", b'{"number":-Infinity}', "generation evidence writer JSON nonfinite number refused"),
            ("float overflow", b'{"number":1e999}', "generation evidence writer JSON nonfinite number refused"),
            ("huge integer", b'{"number":' + b"9" * 5000 + b"}", "generation evidence writer JSON integer too large"),
            ("oversized", b'{"data":"' + b"x" * writer.MAX_JSON_BYTES + b'"}',
             "generation evidence writer JSON size limit exceeded"),
            ("invalid UTF-8", b'{"private":"\xff"}', "generation evidence writer JSON unreadable or invalid"),
            ("malformed private", b'{"private":"synthetic-secret",',
             "generation evidence writer JSON unreadable or invalid"),
            ("nonobject root", b"[]", "generation evidence writer JSON root must be object"),
        )
        def rejected(candidate, expected: str, label: str) -> None:
            try:
                writer.load(candidate)
            except writer.Fail as exc:
                require(str(exc) == expected, f"{label}: wrong generation writer JSON rejection")
                require("synthetic-secret" not in str(exc), f"{label}: private marker disclosed")
            else:
                raise Fail(f"{label}: unsafe generation writer JSON accepted")
        for label, payload, expected in cases:
            path.write_bytes(payload)
            rejected(path, expected, label)
        path.write_bytes(positive)
        alias = Path(directory) / "alias.json"
        alias.symlink_to(path)
        rejected(alias, "generation evidence writer JSON unreadable or invalid", "symlink")
        fifo = Path(directory) / "fifo.json"
        os.mkfifo(fifo)
        rejected(fifo, "generation evidence writer JSON path unsafe", "FIFO")
        rejected(Path(directory), "generation evidence writer JSON path unsafe", "directory")
        rejected("writer-candidate.json", "generation evidence writer JSON path invalid", "non-Path")
        require(writer.load(path) == {"safe": True, "nested": {"count": 1}},
                "generation evidence writer JSON positive control changed")
        require(path.read_bytes() == positive, "generation evidence writer JSON fixture changed")
    require(tuple(path.read_bytes() for path in protected_paths) == before,
            "generation evidence writer JSON negatives changed protected authorities")
    print("PASS reject: generation evidence writer bounded strict JSON, FIFO, symlink and private diagnostics")


def prove_generation_evidence_json_reader(validator) -> None:
    """Exercise the real generation recovery reader with disposable evidence fixtures."""
    protected_paths = (validator.CONTRACT, validator.REGISTRY, validator.GEN_REGISTRY,
                       validator.OBJECTIVES_REGISTRY, validator.DRILL_REGISTRY)
    before = tuple(path.read_bytes() for path in protected_paths)
    with guarded_temporary_directory(prefix=".tmp-generation-json-reader-", parent=TMP_PARENT) as directory:
        path = Path(directory) / "candidate.json"
        positive = b'{"safe":true,"nested":{"count":1}}'
        path.write_bytes(positive)
        require(validator.load(path) == {"safe": True, "nested": {"count": 1}}, "generation recovery JSON positive control failed")
        # A directory close error must not silently certify an unsafe read.
        original_close = validator.os.close
        closed_descriptors = []

        def close_then_fail(descriptor):
            original_close(descriptor)
            closed_descriptors.append(descriptor)
            if len(closed_descriptors) == 1:
                raise OSError("synthetic-private-generation-recovery-close")

        validator.os.close = close_then_fail
        try:
            try:
                validator.load(path)
            except validator.Fail as exc:
                require(str(exc) == "generation recovery JSON cleanup failed",
                        "generation recovery JSON close fault escaped fixed cleanup classification")
                require(exc.__suppress_context__ and exc.__cause__ is None,
                        "generation recovery JSON close fault exposed private exception context")
            else:
                raise Fail("generation recovery JSON accepted failed descriptor cleanup")
        finally:
            validator.os.close = original_close
        require(closed_descriptors, "generation recovery JSON close fault was not exercised")
        for descriptor in closed_descriptors:
            try:
                os.fstat(descriptor)
            except OSError:
                pass
            else:
                raise Fail("generation recovery JSON directory descriptor remained open")

        # A failed fdopen must leave the leaf descriptor owned by finally.
        original_fdopen = validator.os.fdopen
        attempted_descriptors = []

        def fdopen_then_fail(descriptor, *args, **kwargs):
            attempted_descriptors.append(descriptor)
            raise OSError("synthetic-private-generation-recovery-fdopen")

        validator.os.fdopen = fdopen_then_fail
        try:
            try:
                validator.load(path)
            except validator.Fail as exc:
                require(str(exc) == "generation recovery JSON unreadable or invalid",
                        "generation recovery JSON fdopen fault escaped fixed unreadable classification")
                require(exc.__suppress_context__ and exc.__cause__ is None,
                        "generation recovery JSON fdopen fault exposed private exception context")
            else:
                raise Fail("generation recovery JSON accepted failed fdopen")
        finally:
            validator.os.fdopen = original_fdopen
        require(len(attempted_descriptors) == 1,
                "generation recovery JSON fdopen fault was not exercised exactly once")
        try:
            os.fstat(attempted_descriptors[0])
        except OSError:
            pass
        else:
            raise Fail("generation recovery JSON leaf descriptor leaked after fdopen fault")
        require(validator.load(path) == {"safe": True, "nested": {"count": 1}},
                "generation recovery JSON reader failed after descriptor fault restoration")
        print("PASS: generation recovery JSON close/fdopen faults private and descriptors released")
        for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY"):
            original = getattr(validator.os, flag)
            try:
                for invalid in (None, 0):
                    setattr(validator.os, flag, invalid)
                    try:
                        validator.load(path)
                    except validator.Fail as exc:
                        require(str(exc) == "generation recovery JSON nofollow support required",
                                "generation recovery JSON accepted missing or ineffective platform flag")
                        require(exc.__suppress_context__,
                                "generation recovery JSON unsupported flag exposed exception context")
                    else:
                        raise Fail("generation recovery JSON accepted unsafe platform flag: " + flag)
            finally:
                setattr(validator.os, flag, original)
        require(validator.load(path) == {"safe": True, "nested": {"count": 1}},
                "generation recovery JSON reader failed after flag restoration")
        print("PASS: generation recovery JSON missing and zero-valued nofollow flags rejected")
        cases = (
            ("duplicate root", b'{"safe":true,"safe":false}', "generation recovery JSON duplicate key refused"),
            ("duplicate nested", b'{"nested":{"a":1,"a":2}}', "generation recovery JSON duplicate key refused"),
            ("NaN", b'{"number":NaN}', "generation recovery JSON nonfinite number refused"),
            ("Infinity", b'{"number":Infinity}', "generation recovery JSON nonfinite number refused"),
            ("negative Infinity", b'{"number":-Infinity}', "generation recovery JSON nonfinite number refused"),
            ("float overflow", b'{"number":1e999}', "generation recovery JSON nonfinite number refused"),
            ("large integer", b'{"number":' + b"9" * 5000 + b"}", "generation recovery JSON integer too large"),
            ("oversized JSON", b'{"data":"' + b"x" * validator.MAX_JSON_BYTES + b'"}', "generation recovery JSON size limit exceeded"),
            ("invalid UTF-8", b'{"private":"\xff"}', "generation recovery JSON unreadable or invalid"),
            ("malformed private", b'{"private":"synthetic-secret",', "generation recovery JSON unreadable or invalid"),
            ("nonobject root", b"[]", "generation recovery JSON root must be object"),
        )
        def rejected(candidate, expected: str, label: str) -> None:
            try:
                validator.load(candidate)
            except validator.Fail as exc:
                require(str(exc) == expected, f"{label}: wrong generation recovery JSON rejection boundary")
                require("synthetic-secret" not in str(exc), f"{label}: private marker disclosed")
            else:
                raise Fail(f"{label}: unsafe generation recovery JSON accepted")
        for label, payload, expected in cases:
            path.write_bytes(payload)
            rejected(path, expected, label)
        path.write_bytes(positive)
        alias = Path(directory) / "alias.json"
        alias.symlink_to(path)
        rejected(alias, "generation recovery JSON path unsafe", "symlink")
        rejected(Path(directory), "generation recovery JSON path unsafe", "directory")
        rejected(Path(directory) / "missing.json", "generation recovery JSON path missing or outside repository", "missing")
        rejected("candidate.json", "generation recovery JSON path invalid", "non-Path")
        with tempfile.TemporaryDirectory(prefix="memory-os-generation-recovery-canary-") as outside:
            canary = Path(outside) / "canary.json"
            canary.write_bytes(positive)
            escaped = Path(directory) / "escaped.json"
            escaped.symlink_to(canary)
            rejected(escaped, "generation recovery JSON path missing or outside repository", "external symlink")
            require(canary.read_bytes() == positive, "generation recovery JSON modified external canary")
        fifo = Path(directory) / "fifo.json"
        os.mkfifo(fifo)
        rejected(fifo, "generation recovery JSON path unsafe", "FIFO")
        race = Path(directory) / "race.json"
        parked = Path(directory) / "parked-race.json"
        race_canary = Path(directory) / "race-canary.json"
        race.write_bytes(positive)
        race_canary.write_bytes(positive)
        original_open = validator.os.open
        swapped = False

        def swap_before_leaf_open(target, flags, *args, **kwargs):
            nonlocal swapped
            if not swapped and target == race.name and kwargs.get("dir_fd") is not None:
                swapped = True
                race.rename(parked)
                race.symlink_to(race_canary)
            return original_open(target, flags, *args, **kwargs)

        validator.os.open = swap_before_leaf_open
        try:
            rejected(race, "generation recovery JSON unreadable or invalid", "symlink leaf swap")
        finally:
            validator.os.open = original_open
        require(swapped and race.is_symlink() and parked.read_bytes() == positive,
                "generation recovery JSON leaf swap was not exercised")
        require(race_canary.read_bytes() == positive,
                "generation recovery JSON symlink swap changed canary")
        with tempfile.TemporaryDirectory(prefix="memory-os-recovery-json-parent-canary-") as outside:
            parent = Path(directory) / "pinned-parent"
            parked_parent = Path(directory) / "parked-parent"
            parent.mkdir()
            child = parent / "candidate.json"
            original = b'{"inside":true}'
            child.write_bytes(original)
            canary = Path(outside) / child.name
            canary.write_bytes(b'{"outside":true}')
            swapped_parent = False

            def swap_before_descent(target, flags, *args, **kwargs):
                nonlocal swapped_parent
                if not swapped_parent and target == parent.name and kwargs.get("dir_fd") is not None:
                    swapped_parent = True
                    parent.rename(parked_parent)
                    parent.symlink_to(Path(outside), target_is_directory=True)
                return original_open(target, flags, *args, **kwargs)

            validator.os.open = swap_before_descent
            try:
                rejected(child, "generation recovery JSON unreadable or invalid", "ancestor swap before descent")
            finally:
                validator.os.open = original_open
                if parent.is_symlink():
                    require(parent.resolve() == Path(outside), "generation recovery JSON parent canary changed")
                    parent.unlink()
                if parked_parent.exists():
                    parked_parent.rename(parent)
            require(swapped_parent and child.read_bytes() == original,
                    "generation recovery JSON ancestor substitution not exercised safely")
            swapped_parent = False

            def swap_after_pin(target, flags, *args, **kwargs):
                nonlocal swapped_parent
                if not swapped_parent and target == child.name and kwargs.get("dir_fd") is not None:
                    swapped_parent = True
                    parent.rename(parked_parent)
                    parent.symlink_to(Path(outside), target_is_directory=True)
                return original_open(target, flags, *args, **kwargs)

            validator.os.open = swap_after_pin
            try:
                require(validator.load(child) == {"inside": True},
                        "generation recovery JSON followed substituted parent after pin")
            finally:
                validator.os.open = original_open
                if parent.is_symlink():
                    require(parent.resolve() == Path(outside), "generation recovery JSON parent canary changed")
                    parent.unlink()
                if parked_parent.exists():
                    parked_parent.rename(parent)
            require(swapped_parent and child.read_bytes() == original and canary.read_bytes() == b'{"outside":true}',
                    "generation recovery JSON pinned ancestor test changed original or canary")
            print("PASS: generation recovery JSON ancestor swap rejected before descent and pinned after descent")
        require(path.read_bytes() == positive, "generation recovery JSON mutated positive fixture")
    require(tuple(path.read_bytes() for path in protected_paths) == before, "generation recovery JSON mutated protected authorities")
    print("PASS: actual generation recovery JSON reader positive and 18 fail-closed negatives")


def prove_generation_private_authority_path_diagnostics(validator) -> None:
    missing = TMP_PARENT / ".synthetic-private-generation-evidence-missing.json"
    missing_lock = TMP_PARENT / ".synthetic-private-generation-evidence-missing-parent" / "lock"
    require(not missing.exists() and not missing.is_symlink() and not missing_lock.parent.exists(),
            "generation evidence private missing-path fixture unexpectedly exists")
    for label, action, expected in (
        ("file", lambda: validator.require_exact_repo_file(missing, Path("unused.json"),
                                                           "generation evidence contract"),
         "generation evidence contract missing or escapes repository"),
        ("lock parent", lambda: validator.require_canonical_lock_path(missing_lock, Path("unused.lock"),
                                                                     "generation evidence append lock"),
         "generation evidence append lock parent missing or escapes repository"),
    ):
        try:
            action()
        except validator.Fail as exc:
            require(str(exc) == expected, "generation evidence private " + label + " diagnostic drift")
            require(exc.__suppress_context__ and exc.__cause__ is None,
                    "generation evidence private " + label + " filesystem exception context exposed")
            require("synthetic-private" not in str(exc),
                    "generation evidence private " + label + " path canary exposed")
        else:
            raise Fail("generation evidence private " + label + " missing authority accepted")
    print("PASS: generation evidence missing file/lock parent diagnostics suppress private context")


def main() -> int:
    require(WRITER.is_file(), "generation evidence writer missing")
    require(VALIDATOR.is_file(), "generation evidence validator missing")
    require(RECONCILER.is_file(), "generation evidence reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    prove_helper_source_symlink_rejected()
    with guarded_temporary_directory(prefix=".tmp-generation-load-parent-negative-", parent=TMP_PARENT) as raw:
        sandbox = Path(raw)
        link = sandbox / "redirect"
        link.symlink_to(sandbox, target_is_directory=True)
        before = sorted(p.name for p in sandbox.iterdir())
        try:
            with guarded_temporary_directory(prefix=".tmp-must-not-create-", parent=link):
                raise Fail("generation load symlinked temp parent accepted")
        except Fail as exc:
            require(str(exc) == "reconcile negative temp ancestor missing or symlinked",
                    f"generation load symlinked parent rejected at wrong boundary: {exc}")
        else:
            raise Fail("generation load symlinked temp parent accepted")
        require(sorted(p.name for p in sandbox.iterdir()) == before,
                "generation load symlinked temp parent published a child")
    print("PASS: generation load fixture reuses reconcile pre-publication parent guard")
    prove_helper_source_swap_during_import_is_pinned()
    prove_helper_parent_swap_after_pin_uses_original_source()
    prove_helper_ancestor_swap_during_fd_walk_rejected()
    prove_pinned_module_import()
    prove_pinned_module_unsafe_sources()
    prove_pinned_module_fd_cleanup()
    writer = load_module(WRITER, "memory_os_generation_evidence_writer_load_negative")
    validator = load_module(VALIDATOR, "memory_os_generation_evidence_validator_load_negative")
    prove_generation_evidence_writer_json_reader(writer)
    prove_generation_evidence_json_reader(validator)
    prove_generation_private_authority_path_diagnostics(validator)
    reconciler = load_module(RECONCILER, "memory_os_generation_evidence_reconciler_load_negative")

    require(writer.canonical_repo_file(WRITER, "generation evidence writer") == WRITER, "canonical writer path rejected")
    require(callable(getattr(writer, "validate_registry_for_append", None)), "generation writer append authority guard missing")
    exercise_writer_registry_append_guard(writer)
    exercise_writer_rollback_diagnostics(writer)

    with guarded_temporary_directory(prefix=".tmp-generation-evidence-load-", parent=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        with tempfile.TemporaryDirectory(prefix="memory-os-generation-evidence-outside-") as outside_dirname:
            outside_dir = Path(outside_dirname)
            outside = outside_dir / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            exercise_writer_loads(writer, tmp)
            exercise_writer_module_containment(writer, tmp, outside_dir)
            exercise_loads("validator", validator, tmp, outside)
            exercise_loads("reconciler", reconciler, tmp, outside)

    exercise_reconciler_transaction_rollback(reconciler)
    exercise_reconciler_rollback_diagnostics(reconciler)

    print("Generation evidence unreadable/escaped-authority negative suite PASS")
    print("generation writer append authority drift accepted: false")
    print("generation evidence writer rollback diagnostics use private failure classes: true")
    print("generation evidence partial multi-authority transaction accepted: false")
    print("generation evidence transaction rollback preserves exact bytes+mode: true")
    print("generation evidence rollback diagnostics preserve primary + rollback failures: true")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION EVIDENCE LOAD NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
