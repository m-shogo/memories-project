#!/usr/bin/env python3
"""Prove drill-request reconciliation rejects corrupt authority and rolls back post-validation failures."""

from __future__ import annotations

import copy
import importlib.machinery
import importlib.util
import io
import json
import os
import sys
import types
import shutil
import stat
import subprocess
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
DRILL_REQUEST_LOAD_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-drill-request-load-negative.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-request.py"
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
OBJECTIVES = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def load_reconciler() -> Any:
    """Reuse the CI-proven pinned loader instead of executing a mutable path."""
    try:
        require(DRILL_REQUEST_LOAD_NEGATIVE.is_file()
                and not DRILL_REQUEST_LOAD_NEGATIVE.is_symlink(),
                "cannot load drill request reconciler")
        helper = load_pinned_fixture_guard(
            DRILL_REQUEST_LOAD_NEGATIVE, "memory_os_drill_reconcile_pinned_loader")
        module = helper.load_module(
            RECONCILER, "memory_os_restore_drill_request_reconcile_negative")
    except Exception:
        raise Fail("cannot load drill request reconciler") from None
    return module


def prove_reconciler_pinned_import() -> None:
    """An after-capture parent substitution cannot select a different reconciler."""
    global RECONCILER
    original_path = RECONCILER
    original_spec = importlib.util.spec_from_file_location
    with tempfile.TemporaryDirectory(prefix=".drill-reconcile-import-", dir=ROOT) as raw:
        sandbox = Path(raw)
        parent = sandbox / "trusted"
        parent.mkdir()
        source = parent / "module.py"
        parked = sandbox / "parked"
        redirected = sandbox / "redirected"
        redirected.mkdir()
        canary = redirected / "module.py"
        source.write_text("VALUE = 'pinned'\n", encoding="utf-8")
        canary.write_text("raise RuntimeError('PRIVATE_DRILL_RECONCILE_IMPORT_CANARY')\n",
                          encoding="utf-8")
        swapped = False
        try:
            RECONCILER = source
            require(load_reconciler().VALUE == "pinned",
                    "drill reconcile pinned import positive failed")

            def swap_after_read(name, location, *args, **kwargs):
                nonlocal swapped
                if not swapped and Path(location) == source:
                    swapped = True
                    parent.rename(parked)
                    parent.symlink_to(redirected, target_is_directory=True)
                return original_spec(name, location, *args, **kwargs)

            importlib.util.spec_from_file_location = swap_after_read
            loaded = load_reconciler()
            require(swapped and loaded.VALUE == "pinned",
                    "drill reconcile import executed redirected source")
            require(canary.read_text(encoding="utf-8") ==
                    "raise RuntimeError('PRIVATE_DRILL_RECONCILE_IMPORT_CANARY')\n",
                    "drill reconcile import changed redirected canary")
        finally:
            importlib.util.spec_from_file_location = original_spec
            RECONCILER = original_path
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)
    require(callable(getattr(load_reconciler(), "main", None)),
            "drill reconcile pinned import canonical restoration failed")
    print("PASS: drill request reconcile negative loader uses pinned source after parent swap")


def pin_checked_helper_parent(path: Path) -> int:
    """Walk from a trusted repository/temp anchor, never through a symlinked ancestor."""
    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY"),
            "drill request fixture guard no-follow directory open unsupported")
    try:
        anchor = ROOT if path.is_relative_to(ROOT) else Path(tempfile.gettempdir())
    except (OSError, RuntimeError):
        raise Fail("fixture guard parent classification failed") from None
    try:
        relative = path.parent.relative_to(anchor)
    except ValueError:
        raise Fail("drill request fixture guard parent outside trusted roots") from None
    except (OSError, RuntimeError):
        raise Fail("fixture guard parent classification failed") from None
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        anchor_ok = anchor.is_dir() and not anchor.is_symlink()
    except (OSError, RuntimeError):
        raise Fail("fixture guard trusted anchor check failed") from None
    require(anchor_ok,
            "drill request fixture guard trusted anchor missing or symlinked")
    try:
        fd = os.open(anchor, flags)
    except (OSError, RuntimeError):
        raise Fail("drill request fixture guard anchor open failed") from None
    try:
        try:
            opened = os.fstat(fd)
            entry = anchor.lstat()
        except (OSError, RuntimeError):
            raise Fail("fixture guard parent metadata read failed") from None
        require(
            stat.S_ISDIR(entry.st_mode)
            and (entry.st_dev, entry.st_ino) == (opened.st_dev, opened.st_ino),
            "drill request fixture guard trusted anchor identity drift",
        )
        cursor = anchor
        for part in relative.parts:
            cursor = cursor / part
            try:
                cursor_ok = cursor.is_dir() and not cursor.is_symlink()
            except (OSError, RuntimeError):
                raise Fail("fixture guard ancestor predicate check failed") from None
            require(cursor_ok,
                    "drill request fixture guard ancestor missing or symlinked")
            next_fd = os.open(part, flags, dir_fd=fd)
            previous_fd = fd
            fd = next_fd
            try:
                os.close(previous_fd)
            except (Exception, SystemExit):
                raise Fail("fixture guard pinned descriptor cleanup failed") from None
            try:
                opened = os.fstat(fd)
                entry = cursor.lstat()
            except (OSError, RuntimeError):
                raise Fail("fixture guard parent metadata read failed") from None
            require(
                stat.S_ISDIR(entry.st_mode)
                and (entry.st_dev, entry.st_ino) == (opened.st_dev, opened.st_ino),
                "drill request fixture guard ancestor identity drift",
            )
        return fd
    except OSError:
        try:
            os.close(fd)
        except (Exception, SystemExit):
            raise Fail("fixture guard pinned descriptor cleanup failed") from None
        raise Fail("drill request fixture guard parent open failed") from None
    except BaseException:
        try:
            os.close(fd)
        except (Exception, SystemExit):
            raise Fail("fixture guard pinned descriptor cleanup failed") from None
        raise


MAX_HELPER_SOURCE_BYTES = 1024 * 1024


def load_pinned_fixture_guard(path: Path, name: str):
    """Pin each checked helper ancestor and source leaf to FDs."""
    parent_fd = pin_checked_helper_parent(path)
    try:
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        except OSError:
            raise Fail("drill request fixture guard source open failed") from None
        try:
            opened = os.fstat(fd)
            entry = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
            require(
                stat.S_ISREG(opened.st_mode) and stat.S_ISREG(entry.st_mode)
                and (opened.st_dev, opened.st_ino) == (entry.st_dev, entry.st_ino),
                "drill request fixture guard source identity drift",
            )
            with os.fdopen(os.dup(fd), "rb") as stream:
                source = stream.read(MAX_HELPER_SOURCE_BYTES + 1)
            require(len(source) <= MAX_HELPER_SOURCE_BYTES,
                    "fixture guard pinned source oversized")
            class PinnedSourceLoader(importlib.machinery.SourceFileLoader):
                def get_code(self, fullname):
                    require(fullname == name, "fixture guard module identity drift")
                    try:
                        return compile(source, str(path), "exec")
                    except Exception:
                        raise Fail("fixture guard pinned source compilation failed") from None
            try:
                spec = importlib.util.spec_from_file_location(name, path, loader=PinnedSourceLoader(name, str(path)))
                require(spec is not None and spec.loader is not None,
                        "drill request fixture guard cannot load")
                module = importlib.util.module_from_spec(spec)
            except Fail:
                raise
            except (Exception, SystemExit):
                raise Fail("fixture guard pinned module setup failed") from None
            try:
                spec.loader.exec_module(module)
            except Fail:
                raise
            except (Exception, SystemExit):
                raise Fail("fixture guard pinned module execution failed") from None
            return module
        except OSError:
            raise Fail("drill request fixture guard pinned source read failed") from None
        finally:
            try:
                os.close(fd)
            except (Exception, SystemExit):
                raise Fail("fixture guard pinned descriptor cleanup failed") from None
    finally:
        try:
            os.close(parent_fd)
        except (Exception, SystemExit):
            raise Fail("fixture guard pinned descriptor cleanup failed") from None


def guarded_temporary_directory(prefix: str, parent: Path):
    require(DRILL_REQUEST_LOAD_NEGATIVE.is_file() and not DRILL_REQUEST_LOAD_NEGATIVE.is_symlink(),
            "drill request fixture parent guard source missing or symlinked")
    module = load_pinned_fixture_guard(
        DRILL_REQUEST_LOAD_NEGATIVE, "memory_os_drill_fixture_guard_reconcile")
    require(callable(getattr(module, "guarded_temporary_directory", None)),
            "drill request fixture parent guard callable missing")
    try:
        return module.guarded_temporary_directory(prefix, parent)
    except module.Fail as exc:
        raise Fail(str(exc)) from exc



def prove_helper_source_symlink_rejected() -> None:
    # Import-source integrity must be exercised independently of parent-path safety.
    global DRILL_REQUEST_LOAD_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="drill-reconcile-helper-source-") as raw:
        sandbox = Path(raw)
        real = sandbox / "real-helper.py"
        real.touch()
        link = sandbox / "helper.py"
        link.symlink_to(real)
        original = DRILL_REQUEST_LOAD_NEGATIVE
        try:
            DRILL_REQUEST_LOAD_NEGATIVE = link
            try:
                guarded_temporary_directory(".tmp-must-not-create-", ROOT)
            except Fail as exc:
                require(str(exc) == "drill request fixture parent guard source missing or symlinked",
                        f"drill reconcile helper rejected at wrong boundary: {exc}")
            else:
                raise Fail("drill reconcile symlinked fixture helper accepted")
        finally:
            DRILL_REQUEST_LOAD_NEGATIVE = original
    print("PASS: drill reconcile fixture helper symlink rejected before import")


def prove_helper_source_swap_during_import_is_pinned() -> None:
    # Check-to-import substitution is exercised after a valid helper positive control.
    global DRILL_REQUEST_LOAD_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="drill-reconcile-helper-import-race-") as raw:
        sandbox = Path(raw)
        trusted = sandbox / "helper.py"
        parked = sandbox / "original-helper.py"
        untrusted = sandbox / "untrusted.py"
        trusted.write_text(
            "class Fail(RuntimeError):\n    pass\n\n"
            "def guarded_temporary_directory(prefix, parent):\n"
            "    return ('pinned-source', prefix)\n",
            encoding="utf-8",
        )
        untrusted.write_text("raise RuntimeError('untrusted helper executed')\n", encoding="utf-8")
        original_path = DRILL_REQUEST_LOAD_NEGATIVE
        original_spec = importlib.util.spec_from_file_location
        swapped = False
        try:
            DRILL_REQUEST_LOAD_NEGATIVE = trusted
            require(
                guarded_temporary_directory(".tmp-positive-", ROOT)
                == ("pinned-source", ".tmp-positive-"),
                "drill reconcile helper pinned import positive control failed",
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
                guarded_temporary_directory(".tmp-race-", ROOT)
                == ("pinned-source", ".tmp-race-"),
                "drill reconcile helper import executed substituted source",
            )
            require(swapped and trusted.is_symlink() and parked.is_file(),
                    "drill reconcile helper race probe did not substitute checked source")
        finally:
            importlib.util.spec_from_file_location = original_spec
            DRILL_REQUEST_LOAD_NEGATIVE = original_path
    print("PASS: drill reconcile helper import uses pinned source after pathname substitution")


def prove_helper_parent_swap_after_pin_uses_original_source() -> None:
    global DRILL_REQUEST_LOAD_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="drill-reconcile-helper-parent-race-") as raw:
        sandbox = Path(raw)
        trusted_parent = sandbox / "trusted"
        parked_parent = sandbox / "parked"
        untrusted_parent = sandbox / "untrusted"
        trusted_parent.mkdir()
        untrusted_parent.mkdir()
        (trusted_parent / "helper.py").write_text(
            "class Fail(RuntimeError):\n    pass\n\n"
            "def guarded_temporary_directory(prefix, parent):\n"
            "    return ('pinned-parent', prefix)\n",
            encoding="utf-8",
        )
        (untrusted_parent / "helper.py").write_text(
            "raise RuntimeError('untrusted parent helper executed')\n", encoding="utf-8")
        original_path = DRILL_REQUEST_LOAD_NEGATIVE
        original_open = os.open
        swapped = False
        try:
            DRILL_REQUEST_LOAD_NEGATIVE = trusted_parent / "helper.py"
            require(
                guarded_temporary_directory(".tmp-positive-", ROOT)
                == ("pinned-parent", ".tmp-positive-"),
                "drill-reconcile parent-pinned helper positive control failed",
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
                guarded_temporary_directory(".tmp-parent-race-", ROOT)
                == ("pinned-parent", ".tmp-parent-race-"),
                "drill-reconcile helper import followed substituted parent",
            )
            require(swapped and trusted_parent.is_symlink() and (parked_parent / "helper.py").is_file(),
                    "drill-reconcile helper parent race did not substitute checked parent")
        finally:
            os.open = original_open
            DRILL_REQUEST_LOAD_NEGATIVE = original_path
    print("PASS: drill-reconcile helper parent swap preserves pinned source")


def prove_helper_ancestor_swap_during_fd_walk_rejected() -> None:
    # A leaf/parent O_NOFOLLOW alone cannot protect a mutable higher ancestor.
    # Swap an owned nonterminal directory after it was pinned, before descent.
    global DRILL_REQUEST_LOAD_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="drill-reconcile-helper-ancestor-race-") as raw:
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
        original_path = DRILL_REQUEST_LOAD_NEGATIVE
        original_open = os.open
        swapped = False
        try:
            DRILL_REQUEST_LOAD_NEGATIVE = checked_parent / "helper.py"
            require(
                guarded_temporary_directory(".tmp-positive-", ROOT)
                == ("pinned-ancestor", ".tmp-positive-"),
                "drill reconcile ancestor helper positive control failed",
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
                guarded_temporary_directory(".tmp-ancestor-race-", ROOT)
            except Fail as exc:
                require(
                    str(exc) == "drill request fixture guard ancestor identity drift",
                    f"drill reconcile helper ancestor swap rejected at wrong boundary: {exc}",
                )
            else:
                raise Fail("drill reconcile helper ancestor swap accepted")
            require(swapped and checked_ancestor.is_symlink()
                    and (parked_ancestor / "nested/helper.py").is_file(),
                    "drill reconcile helper ancestor swap did not preserve pinned original")
            require((redirect_parent / "helper.py").read_text(encoding="utf-8")
                    == "raise RuntimeError('untrusted ancestor helper executed')\n",
                    "drill reconcile helper ancestor swap modified untrusted source")
        finally:
            os.open = original_open
            DRILL_REQUEST_LOAD_NEGATIVE = original_path
    print("PASS: drill reconcile helper ancestor swap fails closed during FD walk")


def minify_json(path: Path) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def expect_direct_authority_rejected(
    reconciler: Any,
    name: str,
    field: str,
    mutate: Callable[[], None],
    restore: Callable[[], None],
    contract_before: bytes,
    registry_before: bytes,
    status_before: bytes,
) -> None:
    mutate()
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require(f"{field} authority drift" in str(exc), f"{name} rejected at wrong boundary: {exc}")
        else:
            raise Fail(f"direct reconciler unexpectedly accepted: {name}")
        require(CONTRACT.read_bytes() == contract_before, f"canonical contract mutated while rejecting {name}")
        require(REGISTRY.read_bytes() == registry_before, f"canonical registry mutated while rejecting {name}")
        require(STATUS.read_bytes() == status_before, f"canonical status mutated while rejecting {name}")
    finally:
        restore()


def prove_atomic_write_failure(reconciler: Any, contract_before: bytes, registry_before: bytes, status_before: bytes) -> None:
    with guarded_temporary_directory(".memory-os-drill-request-atomic-", ROOT) as tmp:
        fixture = Path(tmp) / CONTRACT.name
        shutil.copy2(CONTRACT, fixture)
        fixture.chmod(0o640)
        fixture_before = fixture.read_bytes()
        reconciler.write_text(fixture, fixture_before.decode("utf-8") + " ")
        require(mode(fixture) == 0o640, "successful atomic drill-request write changed existing file mode")

        stable_bytes = fixture.read_bytes()
        stable_mode = mode(fixture)
        original_replace = reconciler.os.replace

        def reject_replace(source: str | Path, destination: str | Path) -> None:
            raise OSError("synthetic atomic replace rejection")

        reconciler.os.replace = reject_replace
        try:
            try:
                reconciler.write_text(fixture, stable_bytes.decode("utf-8") + " ")
            except reconciler.Fail as exc:
                require("cannot atomically write" in str(exc), f"atomic write rejected at wrong boundary: {exc}")
            else:
                raise Fail("synthetic atomic replace failure unexpectedly accepted")
        finally:
            reconciler.os.replace = original_replace

        require(fixture.read_bytes() == stable_bytes, "atomic replace rejection mutated drill-request fixture bytes")
        require(mode(fixture) == stable_mode == 0o640, "atomic replace rejection changed drill-request fixture mode")
        leftovers = list(fixture.parent.glob(f".{fixture.name}.*.tmp"))
        require(not leftovers, f"atomic replace rejection left temporary drill-request authority files: {leftovers}")

    require(CONTRACT.read_bytes() == contract_before, "atomic writer negative mutated canonical drill-request contract")
    require(REGISTRY.read_bytes() == registry_before, "atomic writer negative mutated canonical drill-request registry")
    require(STATUS.read_bytes() == status_before, "atomic writer negative mutated canonical production status")
    print("PASS boundary: drill-request atomic write preserves mode; failed replace preserves bytes/mode and cleans temporary files")


def prove_atomic_descriptor_cleanup(reconciler: Any) -> None:
    """Pre-fdopen errors must close descriptors and remove private temp files."""
    with guarded_temporary_directory(".memory-os-drill-request-atomic-fd-", ROOT) as tmp:
        fixture = Path(tmp) / CONTRACT.name
        shutil.copy2(CONTRACT, fixture)
        fixture.chmod(0o640)
        original_bytes = fixture.read_bytes()
        marker = "synthetic-secret-drill-request-atomic-fd"
        for operation in ("fchmod", "fdopen"):
            original_operation = getattr(reconciler.os, operation)
            captured: list[int] = []

            def reject(fd: int, *_args: Any, **_kwargs: Any) -> None:
                captured.append(fd)
                raise OSError(marker)

            setattr(reconciler.os, operation, reject)
            try:
                try:
                    reconciler.write_text(fixture, original_bytes.decode("utf-8") + " ")
                except reconciler.Fail as exc:
                    require(str(exc) == "cannot atomically write drill request authority (raw error withheld)",
                            f"{operation}: wrong fixed atomic failure class")
                    require(marker not in str(exc), f"{operation}: private atomic error leaked")
                else:
                    raise Fail(f"{operation}: pre-fdopen failure unexpectedly accepted")
            finally:
                setattr(reconciler.os, operation, original_operation)

            require(len(captured) == 1, f"{operation}: descriptor fault injection was not reached")
            try:
                os.fstat(captured[0])
            except OSError:
                pass
            else:
                raise Fail(f"{operation}: temporary descriptor leaked")
            require(fixture.read_bytes() == original_bytes,
                    f"{operation}: atomic descriptor failure changed fixture bytes")
            require(mode(fixture) == 0o640,
                    f"{operation}: atomic descriptor failure changed fixture mode")
            require(not list(fixture.parent.glob(f".{fixture.name}.*.tmp")),
                    f"{operation}: atomic descriptor failure left temp residue")
    print("PASS: drill request atomic fchmod/fdopen failure closes descriptor and removes temp without private output")


def prove_rollback_attempts_all_restores(reconciler: Any) -> None:
    with guarded_temporary_directory(".memory-os-drill-request-restore-failure-", ROOT) as tmp:
        tmp_path = Path(tmp)
        originals = {
            tmp_path / "registry.json": "registry\n",
            tmp_path / "contract.json": "contract\n",
            tmp_path / "status.json": "status\n",
        }
        observed: list[Path] = []
        original_write = reconciler.write_text

        def fail_first_restore(path: Path, text: str) -> None:
            observed.append(path)
            if len(observed) == 1:
                raise reconciler.Fail("synthetic first drill-request rollback restore rejection")

        reconciler.write_text = fail_first_restore
        try:
            try:
                reconciler.restore_original_text(originals)
            except reconciler.Fail as exc:
                require(str(exc) == "drill request rollback incomplete",
                        "rollback restore failure lost fixed private class")
                require("synthetic first drill-request rollback restore rejection" not in str(exc),
                        "rollback restore disclosed private error")
            else:
                raise Fail("synthetic first drill-request rollback restore failure unexpectedly accepted")
        finally:
            reconciler.write_text = original_write

        require(observed == list(originals), f"rollback restore failure skipped later drill-request authorities: {observed}")
    print("PASS rollback: drill-request restore failure still attempts all three authorities")


def prove_private_reconciler_helper_import(reconciler: Any) -> None:
    """Suppress Python import output and never chain private loader failures."""
    positive = reconciler.load_module(reconciler.WRITER, "memory_os_drill_reconcile_import_positive")
    require(callable(getattr(positive, "require_cli_authorities", None)),
            "drill reconcile canonical writer positive import failed")

    original_spec = reconciler.importlib.util.spec_from_file_location
    original_module = reconciler.importlib.util.module_from_spec
    marker = "synthetic-secret-drill-reconcile-import"

    class LoudLoader:
        def __init__(self, should_fail):
            self.should_fail = should_fail

        def exec_module(self, module):
            print(marker)
            print(marker, file=sys.stderr)
            module.positive = True
            if self.should_fail:
                raise OSError(marker)

    try:
        for should_fail in (False, True):
            spec = types.SimpleNamespace(loader=LoudLoader(should_fail))
            reconciler.importlib.util.spec_from_file_location = lambda *_args, **_kwargs: spec
            reconciler.importlib.util.module_from_spec = lambda _spec: types.SimpleNamespace()
            output, errors = io.StringIO(), io.StringIO()
            with redirect_stdout(output), redirect_stderr(errors):
                if should_fail:
                    try:
                        reconciler.load_module(reconciler.WRITER, "memory_os_drill_reconcile_import_negative")
                    except reconciler.Fail as exc:
                        require(str(exc) == "drill request reconciler helper import failed",
                                "drill reconcile import failure class drift")
                        require(exc.__cause__ is None, "drill reconcile import retained private context")
                    else:
                        raise Fail("drill reconcile noisy import failure accepted")
                else:
                    imported = reconciler.load_module(reconciler.WRITER, "memory_os_drill_reconcile_import_success")
                    require(imported.positive is True, "drill reconcile noisy positive import failed")
            require(marker not in output.getvalue() + errors.getvalue(),
                    "drill reconcile import disclosed private stdout/stderr")
    finally:
        reconciler.importlib.util.spec_from_file_location = original_spec
        reconciler.importlib.util.module_from_spec = original_module
    print("PASS: drill reconcile helper import suppresses Python output and private exceptions")


def prove_post_validator_transport(reconciler: Any) -> None:
    """Actual post-validator helper must be bounded, class-only and fail closed."""
    original_run = reconciler.subprocess.run
    marker = "synthetic-secret-post-reconcile-validator"
    seen = []

    def fake_run(exit_code):
        def run(argv, **kwargs):
            require(argv in ([reconciler.sys.executable, str(reconciler.VALIDATOR)],
                             [reconciler.sys.executable, str(reconciler.OPERABILITY_VALIDATOR)]),
                    "post-validator target drift")
            require(kwargs.get("cwd") == reconciler.ROOT,
                    "post-validator cwd drift")
            require(kwargs.get("stdout") == reconciler.subprocess.DEVNULL
                    and kwargs.get("stderr") == reconciler.subprocess.DEVNULL,
                    "post-validator captured private output")
            require(kwargs.get("timeout") == 120 and kwargs.get("check") is False,
                    "post-validator runtime budget drift")
            seen.append(exit_code)
            return subprocess.CompletedProcess(argv, exit_code, stdout=marker, stderr=marker)
        return run

    try:
        for path, label in ((reconciler.VALIDATOR, "drill request"),
                            (reconciler.OPERABILITY_VALIDATOR, "operability")):
            reconciler.subprocess.run = fake_run(0)
            reconciler.run_post_validator(path, label)
            for exit_code in (1, False):
                reconciler.subprocess.run = fake_run(exit_code)
                try:
                    reconciler.run_post_validator(path, label)
                except reconciler.Fail as exc:
                    require(str(exc) == f"post-reconcile {label} validator failed (raw output withheld)",
                            "post-validator failure class drift")
                    require(marker not in str(exc), "post-validator private output leaked")
                else:
                    raise Fail("post-validator nonzero/bool status accepted")
            for failure in (OSError(marker), subprocess.TimeoutExpired(["synthetic"], 120)):
                def raise_failure(*_args, **_kwargs):
                    raise failure
                reconciler.subprocess.run = raise_failure
                try:
                    reconciler.run_post_validator(path, label)
                except reconciler.Fail as exc:
                    require(str(exc) == f"post-reconcile {label} validator unavailable or timed out (raw output withheld)",
                            "post-validator unavailable/timeout class drift")
                    require(marker not in str(exc), "post-validator exception disclosed")
                else:
                    raise Fail("post-validator unavailable/timeout accepted")
    finally:
        reconciler.subprocess.run = original_run
    require(seen == [0, 1, False, 0, 1, False], "post-validator positive/failure controls incomplete")
    print("PASS: drill request post-validators use bounded class-only subprocess transport")


def prove_primary_and_rollback_diagnostics(reconciler: Any) -> None:
    original_write = reconciler.write_text
    original_restore = reconciler.restore_original_text
    original_run = reconciler.subprocess.run
    observed_writes: list[Path] = []

    def no_op_write(path: Path, text: str) -> None:
        observed_writes.append(path)

    def reject_post_validator(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        command = [str(item) for item in (args[0] if args else [])]
        require(command and command[-1] == str(reconciler.VALIDATOR), "unexpected validator before synthetic primary failure")
        return subprocess.CompletedProcess(
            args=command,
            returncode=29,
            stdout="synthetic drill-request validator rejection\n",
            stderr="",
        )

    def reject_rollback(originals: dict[Path, str]) -> None:
        require(list(originals) == [reconciler.REGISTRY, reconciler.CONTRACT, reconciler.STATUS], "rollback authority order drift")
        raise reconciler.Fail("synthetic drill-request rollback restore rejection")

    reconciler.write_text = no_op_write
    reconciler.restore_original_text = reject_rollback
    reconciler.subprocess.run = reject_post_validator
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            message = str(exc)
            require(message == "drill request reconcile transaction failed (Fail); rollback incomplete",
                    "transaction primary class or incomplete rollback status drift")
            require("synthetic drill-request validator rejection" not in message
                    and "synthetic drill-request rollback restore rejection" not in message,
                    "transaction disclosed private primary or rollback diagnostics")
        else:
            raise Fail("combined drill-request primary and rollback failure unexpectedly accepted")
    finally:
        reconciler.write_text = original_write
        reconciler.restore_original_text = original_restore
        reconciler.subprocess.run = original_run

    require(
        observed_writes == [reconciler.REGISTRY, reconciler.CONTRACT, reconciler.STATUS],
        f"synthetic primary failure did not reach all planned authority writes: {observed_writes}",
    )
    print("PASS diagnostics: drill-request primary validator and rollback failures are both preserved")


def main() -> int:
    require(RECONCILER.is_file(), "drill request reconciler missing")
    prove_helper_source_symlink_rejected()
    prove_helper_source_swap_during_import_is_pinned()
    prove_helper_parent_swap_after_pin_uses_original_source()
    prove_helper_ancestor_swap_during_fd_walk_rejected()
    prove_reconciler_pinned_import()
    with guarded_temporary_directory(".tmp-drill-reconcile-parent-negative-", ROOT) as raw:
        sandbox = Path(raw)
        link = sandbox / "redirect"
        link.symlink_to(sandbox, target_is_directory=True)
        before = sorted(p.name for p in sandbox.iterdir())
        try:
            with guarded_temporary_directory(".tmp-must-not-create-", link):
                raise Fail("drill reconcile symlinked temp parent accepted")
        except Fail as exc:
            require(str(exc) == "drill request temp ancestor missing or symlinked",
                    f"drill reconcile temp parent rejected at wrong boundary: {exc}")
        else:
            raise Fail("drill reconcile symlinked temp parent accepted")
        require(sorted(p.name for p in sandbox.iterdir()) == before,
                "drill reconcile symlinked temp parent published a child")
    print("PASS: drill request reconcile fixtures reuse checked parent guard")
    for path in (CONTRACT, REGISTRY, GEN_REGISTRY, OBJECTIVES, STATUS):
        require(path.is_file(), f"canonical authority missing: {path.name}")

    reconciler = load_reconciler()
    require(issubclass(reconciler.Fail, RuntimeError), "reconciler Fail must remain a runtime validation error")
    prove_post_validator_transport(reconciler)
    prove_private_reconciler_helper_import(reconciler)

    canonical_contract = CONTRACT.read_bytes()
    canonical_registry = REGISTRY.read_bytes()
    canonical_status = STATUS.read_bytes()
    original_contract_path = reconciler.CONTRACT
    original_registry_path = reconciler.REGISTRY
    original_gen_registry = reconciler.GEN_REGISTRY
    original_objectives_registry = reconciler.OBJECTIVES_REGISTRY
    original_status_path = reconciler.STATUS
    original_writer = reconciler.WRITER
    original_eligibility = reconciler.ELIGIBILITY_HELPER
    original_objectives_writer = reconciler.OBJECTIVES_WRITER
    original_validator = reconciler.VALIDATOR
    original_operability = reconciler.OPERABILITY_VALIDATOR

    authority_cases = (
        ("drill request contract substitution", "drill request contract", "CONTRACT", original_status_path),
        ("drill request registry substitution", "drill request registry", "REGISTRY", original_contract_path),
        ("environment generation registry substitution", "environment generation registry", "GEN_REGISTRY", original_registry_path),
        ("recovery objectives registry substitution", "recovery objectives registry", "OBJECTIVES_REGISTRY", original_registry_path),
        ("drill request writer substitution", "drill request writer", "WRITER", original_objectives_writer),
        ("semantic eligibility helper substitution", "semantic generation eligibility helper", "ELIGIBILITY_HELPER", original_writer),
        ("recovery objectives writer substitution", "recovery objectives writer", "OBJECTIVES_WRITER", original_writer),
        ("drill request validator substitution", "drill request validator", "VALIDATOR", original_operability),
        ("operability validator substitution", "operability validator", "OPERABILITY_VALIDATOR", original_validator),
        ("production status substitution", "production operability status", "STATUS", original_contract_path),
    )
    for name, field, attribute, replacement in authority_cases:
        original = getattr(reconciler, attribute)
        expect_direct_authority_rejected(
            reconciler,
            name,
            field,
            lambda attribute=attribute, replacement=replacement: setattr(reconciler, attribute, replacement),
            lambda attribute=attribute, original=original: setattr(reconciler, attribute, original),
            canonical_contract,
            canonical_registry,
            canonical_status,
        )

    prove_atomic_write_failure(reconciler, canonical_contract, canonical_registry, canonical_status)
    prove_atomic_descriptor_cleanup(reconciler)
    prove_rollback_attempts_all_restores(reconciler)
    prove_primary_and_rollback_diagnostics(reconciler)

    original_enforcer = reconciler.enforce_runtime_authorities
    try:
        # Production direct invocation is canonical-only. Repo-local copies are
        # allowed only inside this negative harness to prove corruption rejection
        # and byte-for-byte rollback independently of the runtime identity gate.
        reconciler.enforce_runtime_authorities = lambda: None

        # A corrupt recovery-objective authority must fail before any derived drill
        # contract, request registry or production status mutation can occur.
        with guarded_temporary_directory(".memory-os-drill-objective-corruption-", ROOT) as tmp:
            tmp_path = Path(tmp)
            contract = tmp_path / CONTRACT.name
            registry = tmp_path / REGISTRY.name
            objectives = tmp_path / OBJECTIVES.name
            status = tmp_path / STATUS.name
            shutil.copy2(CONTRACT, contract)
            shutil.copy2(REGISTRY, registry)
            shutil.copy2(OBJECTIVES, objectives)
            shutil.copy2(STATUS, status)

            original_contract = contract.read_bytes()
            original_registry = registry.read_bytes()
            original_status = status.read_bytes()
            valid_objectives = json.loads(objectives.read_text(encoding="utf-8"))
            require(isinstance(valid_objectives, dict), "objective registry fixture must be an object")

            reconciler.CONTRACT = contract
            reconciler.REGISTRY = registry
            reconciler.OBJECTIVES_REGISTRY = objectives
            reconciler.STATUS = status

            corruptions: dict[str, Callable[[dict[str, Any]], None]] = {
                "objective registry schema drift": lambda value: value.__setitem__("schemaVersion", "legacy-recovery-objectives"),
                "objective registry append-only disabled": lambda value: value.__setitem__("appendOnly", False),
                "objective registry boolean count": lambda value: value.__setitem__("approvedObjectiveCount", True),
                "objective registry current pointer drift": lambda value: value.__setitem__("currentObjectiveId", "ro_forged_current"),
                "objective registry production evidence forged": lambda value: value.__setitem__("productionEvidence", True),
                "objective registry production ready forged": lambda value: value.__setitem__("productionReady", True),
            }
            for name, mutate in corruptions.items():
                candidate = copy.deepcopy(valid_objectives)
                mutate(candidate)
                write_json(objectives, candidate)
                try:
                    reconciler.main()
                except reconciler.Fail as exc:
                    require("recovery objectives registry authority invalid" in str(exc), f"{name} was not rejected by shared objective authority")
                    print(f"PASS reject before write: {name}")
                else:
                    raise Fail(f"reconciler unexpectedly accepted: {name}")
                require(contract.read_bytes() == original_contract, f"contract mutated while rejecting {name}")
                require(registry.read_bytes() == original_registry, f"request registry mutated while rejecting {name}")
                require(status.read_bytes() == original_status, f"production status mutated while rejecting {name}")

        with guarded_temporary_directory(".memory-os-drill-request-rollback-", ROOT) as tmp:
            tmp_path = Path(tmp)
            contract = tmp_path / CONTRACT.name
            registry = tmp_path / REGISTRY.name
            objectives = tmp_path / OBJECTIVES.name
            status = tmp_path / STATUS.name
            shutil.copy2(CONTRACT, contract)
            shutil.copy2(REGISTRY, registry)
            shutil.copy2(OBJECTIVES, objectives)
            shutil.copy2(STATUS, status)

            # Preserve semantically identical but byte-distinct inputs so the synthetic
            # validators can prove reconciliation writes actually happened before the
            # aggregate operability failure forces rollback.
            for path in (contract, registry, status):
                minify_json(path)
                path.chmod(0o640)

            original_contract = contract.read_bytes()
            original_registry = registry.read_bytes()
            original_status = status.read_bytes()
            original_contract_mode = mode(contract)
            original_registry_mode = mode(registry)
            original_status_mode = mode(status)
            observed_commands: list[list[str]] = []

            def aggregate_failure_after_drill_success(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
                require(contract.read_bytes() != original_contract, "post-validator invoked before contract reconcile write")
                require(registry.read_bytes() != original_registry, "post-validator invoked before registry reconcile write")
                require(status.read_bytes() != original_status, "post-validator invoked before production status reconcile write")
                require(mode(contract) == original_contract_mode, "contract mode changed before post-validation")
                require(mode(registry) == original_registry_mode, "registry mode changed before post-validation")
                require(mode(status) == original_status_mode, "production status mode changed before post-validation")
                command = [str(item) for item in (args[0] if args else [])]
                observed_commands.append(command)
                if len(observed_commands) == 1:
                    require(command[-1] == str(reconciler.VALIDATOR), "drill request validator was not first post-write validator")
                    return subprocess.CompletedProcess(args=command, returncode=0, stdout="synthetic drill validator success\n", stderr="")
                require(len(observed_commands) == 2, "unexpected extra post-write validator invocation")
                require(command[-1] == str(reconciler.OPERABILITY_VALIDATOR), "operability validator was not second post-write validator")
                return subprocess.CompletedProcess(args=command, returncode=23, stdout="synthetic operability failure\n", stderr="")

            reconciler.CONTRACT = contract
            reconciler.REGISTRY = registry
            reconciler.OBJECTIVES_REGISTRY = objectives
            reconciler.STATUS = status
            real_run = reconciler.subprocess.run
            reconciler.subprocess.run = aggregate_failure_after_drill_success
            try:
                try:
                    reconciler.main()
                except reconciler.Fail as exc:
                    require(str(exc) == "drill request reconcile transaction failed (Fail); rollback completed",
                            "aggregate operability failure lost fixed transaction class")
                else:
                    raise Fail("reconciler unexpectedly accepted failed aggregate operability validation")
            finally:
                reconciler.subprocess.run = real_run

            require(len(observed_commands) == 2, "drill and operability validators were not both invoked after writes")
            require(contract.read_bytes() == original_contract, "contract mutation survived failed aggregate validation")
            require(registry.read_bytes() == original_registry, "registry mutation survived failed aggregate validation")
            require(status.read_bytes() == original_status, "production status mutation survived failed aggregate validation")
            require(mode(contract) == original_contract_mode == 0o640, "contract mode changed across rollback")
            require(mode(registry) == original_registry_mode == 0o640, "registry mode changed across rollback")
            require(mode(status) == original_status_mode == 0o640, "production status mode changed across rollback")
    finally:
        reconciler.enforce_runtime_authorities = original_enforcer
        reconciler.CONTRACT = original_contract_path
        reconciler.REGISTRY = original_registry_path
        reconciler.GEN_REGISTRY = original_gen_registry
        reconciler.OBJECTIVES_REGISTRY = original_objectives_registry
        reconciler.STATUS = original_status_path

    print("Memory OS backup/restore drill request reconcile rollback negative suite PASS")
    print(f"direct reconciler data/executable authority substitutions rejected: {len(authority_cases)}")
    print("corrupt recovery objective authority rejected before derived writes: true")
    print("shared objective authority corruption cases: 6")
    print("successful atomic drill-request authority write preserves existing mode: true")
    print("failed atomic drill-request replace preserves bytes and mode: true")
    print("rollback restore failure still attempts all three authorities: true")
    print("primary validator and rollback failure diagnostics both preserved: true")
    print("drill request validator succeeds before aggregate failure: true")
    print("aggregate operability failure observed after all authority writes: true")
    print("contract byte-for-byte and mode rollback: true")
    print("registry byte-for-byte and mode rollback: true")
    print("production status byte-for-byte and mode rollback: true")
    print("production evidence created: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE DRILL REQUEST RECONCILE NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
