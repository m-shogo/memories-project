#!/usr/bin/env python3
"""Prove restore drill preflight reconciliation rolls back partial publication."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import shutil
import stat
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-preflight.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
DRILL_REQUEST_LOAD_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-drill-request-load-negative.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


MAX_MODULE_BYTES = 1024 * 1024


def load_module():
    try:
        relative = RECONCILER.relative_to(ROOT)
        require(RECONCILER.resolve(strict=True) == ROOT.resolve() / relative,
                "cannot load restore drill preflight reconciler")
        checked = RECONCILER.lstat()
        require(stat.S_ISREG(checked.st_mode), "cannot load restore drill preflight reconciler")
        require(all(type(getattr(os, flag, None)) is int and getattr(os, flag) > 0
                    for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY")),
                "cannot load restore drill preflight reconciler")
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
                    "cannot load restore drill preflight reconciler")
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
            require(not cleanup_failed, "cannot load restore drill preflight reconciler")
        require(len(source) <= MAX_MODULE_BYTES, "cannot load restore drill preflight reconciler")

        class PinnedSourceLoader(importlib.machinery.SourceFileLoader):
            def get_code(self, fullname):
                require(fullname == "memory_os_backup_restore_drill_preflight_reconcile_negative",
                        "cannot load restore drill preflight reconciler")
                return compile(source, str(RECONCILER), "exec")

        name = "memory_os_backup_restore_drill_preflight_reconcile_negative"
        spec = importlib.util.spec_from_file_location(
            name, RECONCILER, loader=PinnedSourceLoader(name, str(RECONCILER)))
        require(spec is not None and spec.loader is not None, "cannot load restore drill preflight reconciler")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:
        raise Fail("cannot load restore drill preflight reconciler") from None
    return module


def prove_pinned_reconciler_import() -> None:
    """The reconcile negative harness never executes a swapped parent source."""
    global RECONCILER
    original_path = RECONCILER
    original_spec = importlib.util.spec_from_file_location
    with tempfile.TemporaryDirectory(prefix=".preflight-reconcile-import-", dir=ROOT) as raw:
        sandbox = Path(raw)
        parent = sandbox / "trusted"
        parent.mkdir()
        source = parent / "module.py"
        parked = sandbox / "parked"
        redirected = sandbox / "redirected"
        redirected.mkdir()
        canary = redirected / "module.py"
        source.write_text("VALUE = 'pinned'\n", encoding="utf-8")
        canary.write_text("raise RuntimeError('PRIVATE_PREFLIGHT_RECONCILE_CANARY')\n", encoding="utf-8")
        try:
            RECONCILER = source
            require(load_module().VALUE == "pinned", "preflight reconcile pinned import positive failed")
            swapped = False

            def swap_after_read(name, location, *args, **kwargs):
                nonlocal swapped
                if not swapped and Path(location) == source:
                    swapped = True
                    parent.rename(parked)
                    parent.symlink_to(redirected, target_is_directory=True)
                return original_spec(name, location, *args, **kwargs)

            importlib.util.spec_from_file_location = swap_after_read
            loaded = load_module()
            require(swapped and loaded.VALUE == "pinned",
                    "preflight reconcile negative executed redirected parent source")
            require(canary.read_text(encoding="utf-8") ==
                    "raise RuntimeError('PRIVATE_PREFLIGHT_RECONCILE_CANARY')\n",
                    "preflight reconcile import changed redirected canary")
        finally:
            RECONCILER = original_path
            importlib.util.spec_from_file_location = original_spec
    require(callable(getattr(load_module(), "main", None)),
            "preflight reconcile pinned import canonical restoration failed")
    print("PASS: preflight reconcile negative loader uses pinned source after parent swap")





def pin_checked_helper_parent(path: Path) -> int:
    """Walk from a trusted repository/temp anchor, never through a symlinked ancestor."""
    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY"),
            "preflight fixture guard no-follow directory open unsupported")
    try:
        anchor = ROOT if path.is_relative_to(ROOT) else Path(tempfile.gettempdir())
    except (OSError, RuntimeError):
        raise Fail("fixture guard parent classification failed") from None
    try:
        relative = path.parent.relative_to(anchor)
    except ValueError:
        raise Fail("preflight fixture guard parent outside trusted roots") from None
    except (OSError, RuntimeError):
        raise Fail("fixture guard parent classification failed") from None
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        anchor_ok = anchor.is_dir() and not anchor.is_symlink()
    except (OSError, RuntimeError):
        raise Fail("fixture guard trusted anchor check failed") from None
    require(anchor_ok,
            "preflight fixture guard trusted anchor missing or symlinked")
    try:
        fd = os.open(anchor, flags)
    except (OSError, RuntimeError):
        raise Fail("preflight fixture guard anchor open failed") from None
    try:
        try:
            opened = os.fstat(fd)
            entry = anchor.lstat()
        except (OSError, RuntimeError):
            raise Fail("fixture guard parent metadata read failed") from None
        require(
            stat.S_ISDIR(entry.st_mode)
            and (entry.st_dev, entry.st_ino) == (opened.st_dev, opened.st_ino),
            "preflight fixture guard trusted anchor identity drift",
        )
        cursor = anchor
        for part in relative.parts:
            cursor = cursor / part
            try:
                cursor_ok = cursor.is_dir() and not cursor.is_symlink()
            except (OSError, RuntimeError):
                raise Fail("fixture guard ancestor predicate check failed") from None
            require(cursor_ok,
                    "preflight fixture guard ancestor missing or symlinked")
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
                "preflight fixture guard ancestor identity drift",
            )
        return fd
    except OSError:
        try:
            os.close(fd)
        except (Exception, SystemExit):
            raise Fail("fixture guard pinned descriptor cleanup failed") from None
        raise Fail("preflight fixture guard parent open failed") from None
    except BaseException as exc:
        try:
            os.close(fd)
        except (Exception, SystemExit):
            raise Fail("fixture guard pinned descriptor cleanup failed") from None
        if isinstance(exc, RuntimeError) and not isinstance(exc, Fail):
            raise Fail("fixture guard parent runtime open failed") from None
        raise


MAX_HELPER_SOURCE_BYTES = 1024 * 1024


def load_pinned_fixture_guard(path: Path, name: str):
    """Bind each checked ancestor and the leaf FD before executing helper source."""
    parent_fd = pin_checked_helper_parent(path)
    try:
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        except OSError:
            raise Fail("preflight fixture guard source open failed") from None
        try:
            opened = os.fstat(fd)
            entry = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
            require(
                stat.S_ISREG(opened.st_mode) and stat.S_ISREG(entry.st_mode)
                and (opened.st_dev, opened.st_ino) == (entry.st_dev, entry.st_ino),
                "preflight fixture guard source identity drift",
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
                        "preflight fixture guard cannot load")
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
            raise Fail("preflight fixture guard pinned source read failed") from None
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
        DRILL_REQUEST_LOAD_NEGATIVE, "memory_os_drill_fixture_guard_preflight_reconcile")
    require(callable(getattr(module, "guarded_temporary_directory", None)),
            "drill request fixture parent guard callable missing")
    try:
        return module.guarded_temporary_directory(prefix, parent)
    except module.Fail as exc:
        raise Fail(str(exc)) from exc



def prove_helper_source_symlink_rejected() -> None:
    # Test the helper import authority separately from its parent-path guard.
    global DRILL_REQUEST_LOAD_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="preflight-reconcile-helper-source-") as raw:
        sandbox = Path(raw)
        real = sandbox / "real-helper.py"
        real.touch()
        link = sandbox / "helper.py"
        link.symlink_to(real)
        original = DRILL_REQUEST_LOAD_NEGATIVE
        try:
            DRILL_REQUEST_LOAD_NEGATIVE = link
            try:
                guarded_temporary_directory(".tmp-must-not-create-", TMP_PARENT)
            except Fail as exc:
                require(str(exc) == "drill request fixture parent guard source missing or symlinked",
                        f"preflight reconcile helper rejected at wrong boundary: {exc}")
            else:
                raise Fail("preflight reconcile symlinked helper accepted")
        finally:
            DRILL_REQUEST_LOAD_NEGATIVE = original
    print("PASS: preflight reconcile fixture helper symlink rejected before import")


def prove_helper_source_swap_during_import_is_pinned() -> None:
    # The helper may be renamed after its non-symlink check but before import.
    global DRILL_REQUEST_LOAD_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="preflight-reconcile-helper-import-race-") as raw:
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
                guarded_temporary_directory(".tmp-positive-", TMP_PARENT)
                == ("pinned-source", ".tmp-positive-"),
                "preflight helper pinned import positive control failed",
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
                guarded_temporary_directory(".tmp-race-", TMP_PARENT)
                == ("pinned-source", ".tmp-race-"),
                "preflight helper import executed substituted source",
            )
            require(swapped and trusted.is_symlink() and parked.is_file(),
                    "preflight helper race probe did not substitute checked source")
        finally:
            importlib.util.spec_from_file_location = original_spec
            DRILL_REQUEST_LOAD_NEGATIVE = original_path
    print("PASS: preflight reconcile helper import uses pinned source after pathname substitution")


def prove_helper_parent_swap_after_pin_uses_original_source() -> None:
    global DRILL_REQUEST_LOAD_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="preflight-reconcile-helper-parent-race-") as raw:
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
                guarded_temporary_directory(".tmp-positive-", TMP_PARENT)
                == ("pinned-parent", ".tmp-positive-"),
                "preflight-reconcile parent-pinned helper positive control failed",
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
                guarded_temporary_directory(".tmp-parent-race-", TMP_PARENT)
                == ("pinned-parent", ".tmp-parent-race-"),
                "preflight-reconcile helper import followed substituted parent",
            )
            require(swapped and trusted_parent.is_symlink() and (parked_parent / "helper.py").is_file(),
                    "preflight-reconcile helper parent race did not substitute checked parent")
        finally:
            os.open = original_open
            DRILL_REQUEST_LOAD_NEGATIVE = original_path
    print("PASS: preflight-reconcile helper parent swap preserves pinned source")


def prove_helper_ancestor_swap_during_fd_walk_rejected() -> None:
    # A leaf/parent O_NOFOLLOW alone cannot protect a mutable higher ancestor.
    # Swap an owned nonterminal directory after it was pinned, before descent.
    global DRILL_REQUEST_LOAD_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="preflight-load-helper-ancestor-race-") as raw:
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
                guarded_temporary_directory(".tmp-positive-", TMP_PARENT)
                == ("pinned-ancestor", ".tmp-positive-"),
                "preflight load ancestor helper positive control failed",
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
                guarded_temporary_directory(".tmp-ancestor-race-", TMP_PARENT)
            except Fail as exc:
                require(
                    str(exc) == "preflight fixture guard ancestor identity drift",
                    f"preflight reconcile helper ancestor swap rejected at wrong boundary: {exc}",
                )
            else:
                raise Fail("preflight reconcile helper ancestor swap accepted")
            require(swapped and checked_ancestor.is_symlink()
                    and (parked_ancestor / "nested/helper.py").is_file(),
                    "preflight reconcile helper ancestor swap did not preserve pinned original")
            require((redirect_parent / "helper.py").read_text(encoding="utf-8")
                    == "raise RuntimeError('untrusted ancestor helper executed')\n",
                    "preflight reconcile helper ancestor swap modified untrusted source")
        finally:
            os.open = original_open
            DRILL_REQUEST_LOAD_NEGATIVE = original_path
    print("PASS: preflight reconcile helper ancestor swap fails closed during FD walk")


def fixture_authorities(module, tmp: Path, label: str) -> tuple[Path, Path]:
    contract = tmp / f"{label}-{module.CONTRACT.name}"
    status = tmp / f"{label}-{module.STATUS.name}"
    shutil.copy2(module.CONTRACT, contract)
    shutil.copy2(module.STATUS, status)
    return contract, status


def assert_authorities_restored(
    contract: Path,
    status: Path,
    contract_before: bytes,
    status_before: bytes,
    contract_mode_before: int,
    status_mode_before: int,
    boundary: str,
) -> None:
    require(contract.read_bytes() == contract_before, f"preflight contract was not restored byte-for-byte after {boundary}")
    require(status.read_bytes() == status_before, f"production status was not restored byte-for-byte after {boundary}")
    require(mode(contract) == contract_mode_before, f"preflight contract mode changed after {boundary}")
    require(mode(status) == status_mode_before, f"production status mode changed after {boundary}")
    require(
        not list(contract.parent.glob(f".{contract.name}.*.tmp")),
        f"preflight contract left a temporary authority file after {boundary}",
    )
    require(
        not list(status.parent.glob(f".{status.name}.*.tmp")),
        f"production status left a temporary authority file after {boundary}",
    )


def prove_second_replace_rollback(module, tmp: Path) -> None:
    contract, status = fixture_authorities(module, tmp, "second-replace")
    contract_before = contract.read_bytes()
    status_before = status.read_bytes()
    contract_mode_before = mode(contract)
    status_mode_before = mode(status)
    original_contract = module.CONTRACT
    original_status = module.STATUS
    real_replace = module.os.replace
    replace_calls = 0

    def fail_second_replace(source: str | Path, destination: str | Path) -> None:
        nonlocal replace_calls
        replace_calls += 1
        if replace_calls == 2:
            raise OSError("synthetic preflight second atomic replacement failure")
        real_replace(source, destination)

    module.CONTRACT = contract
    module.STATUS = status
    module.os.replace = fail_second_replace
    try:
        try:
            module._reconcile()
        except module.Fail as exc:
            require(
                "preflight reconcile transaction failed (Fail)" in str(exc)
                and "synthetic preflight second atomic replacement failure" not in str(exc),
                f"preflight second replace rejected at wrong boundary: {exc}",
            )
        else:
            raise Fail("preflight second atomic replacement failure unexpectedly accepted")
    finally:
        module.os.replace = real_replace
        module.CONTRACT = original_contract
        module.STATUS = original_status

    require(replace_calls == 4, f"unexpected preflight replace/rollback call count: {replace_calls}")
    assert_authorities_restored(
        contract,
        status,
        contract_before,
        status_before,
        contract_mode_before,
        status_mode_before,
        "partial publication rollback",
    )
    print("PASS rollback: preflight second replace failure restores fixture contract/status bytes and modes")
    print("PASS boundary: preflight second replace failure leaves no temporary authority files")


def prove_rollback_attempts_all_authorities(module) -> None:
    real_write_text = module.write_text
    real_repo_relative = module.repo_relative
    first = Path("/synthetic/preflight-contract.json")
    second = Path("/synthetic/production-status.json")
    attempts: list[Path] = []

    def fail_first_restore(path: Path, _text: str) -> None:
        attempts.append(path)
        if path == first:
            raise module.Fail("synthetic first preflight rollback restore rejection")

    module.write_text = fail_first_restore
    module.repo_relative = lambda path: Path(path.name)
    try:
        try:
            module.restore_authorities(
                ((first, "contract-original"), (second, "status-original")),
                module.Fail("synthetic forward preflight rejection"),
            )
        except module.Fail as exc:
            require(
                "rollback incomplete" in str(exc)
                and "preflight-contract.json" in str(exc),
                f"preflight rollback aggregation rejected at wrong boundary: {exc}",
            )
        else:
            raise Fail("synthetic first preflight rollback restore failure unexpectedly accepted")
        require(attempts == [first, second], f"preflight rollback did not attempt every authority: {attempts}")
    finally:
        module.write_text = real_write_text
        module.repo_relative = real_repo_relative
    print("PASS rollback: failure restoring first preflight authority does not skip later authority restore attempts")


def prove_post_validator_rollback(module, tmp: Path) -> None:
    contract, status = fixture_authorities(module, tmp, "post-validator")
    contract_before = contract.read_bytes()
    status_before = status.read_bytes()
    contract_mode_before = mode(contract)
    status_mode_before = mode(status)
    original_contract = module.CONTRACT
    original_status = module.STATUS
    real_validator = module.run_post_reconcile_validator
    real_replace = module.os.replace
    validator_calls: list[str] = []
    publication_destinations: list[Path] = []

    def record_replace(source: str | Path, destination: str | Path) -> None:
        publication_destinations.append(Path(destination))
        real_replace(source, destination)

    def fail_after_preflight_validator(_path: Path, label: str) -> None:
        validator_calls.append(label)
        if label == "preflight":
            return
        require(label == "operability", f"unexpected post-reconcile validator label: {label}")
        raise module.Fail("synthetic post-publication operability validator failure")

    module.CONTRACT = contract
    module.STATUS = status
    module.os.replace = record_replace
    module.run_post_reconcile_validator = fail_after_preflight_validator
    try:
        try:
            module._reconcile()
        except module.Fail as exc:
            require(
                "preflight reconcile transaction failed (Fail)" in str(exc)
                and "synthetic post-publication operability validator failure" not in str(exc),
                f"post-publication validator failure rejected at wrong boundary: {exc}",
            )
        else:
            raise Fail("post-publication validator failure unexpectedly accepted")
    finally:
        module.run_post_reconcile_validator = real_validator
        module.os.replace = real_replace
        module.CONTRACT = original_contract
        module.STATUS = original_status

    require(validator_calls == ["preflight", "operability"], f"unexpected post-reconcile validator sequence: {validator_calls}")
    require(len(publication_destinations) == 4, f"unexpected publish/rollback replacement count after validator failure: {len(publication_destinations)}")
    require(
        publication_destinations[:2] == [contract, status],
        f"validators ran before both fixture authorities were published: {publication_destinations}",
    )
    require(
        publication_destinations[2:] == [contract, status],
        f"post-validator rollback did not restore both fixture authorities: {publication_destinations}",
    )
    assert_authorities_restored(
        contract,
        status,
        contract_before,
        status_before,
        contract_mode_before,
        status_mode_before,
        "post-publication validator rollback",
    )
    print("PASS rollback: failed aggregate validator restores both fixture authorities byte-for-byte with original modes")
    print("PASS boundary: synthetic post-validation rollback leaves canonical authorities untouched")


def main() -> int:
    prove_pinned_reconciler_import()
    require(RECONCILER.is_file(), "restore drill preflight reconciler missing")
    require(TMP_PARENT.is_dir(), "preflight negative fixture parent missing")
    with guarded_temporary_directory(".tmp-preflight-reconcile-parent-negative-", TMP_PARENT) as raw:
        sandbox = Path(raw)
        link = sandbox / "redirect"
        link.symlink_to(sandbox, target_is_directory=True)
        before = sorted(p.name for p in sandbox.iterdir())
        try:
            with guarded_temporary_directory(".tmp-must-not-create-", link):
                raise Fail("preflight reconcile symlinked temp parent accepted")
        except Fail as exc:
            require(str(exc) == "drill request temp ancestor missing or symlinked",
                    f"preflight reconcile temp parent rejected at wrong boundary: {exc}")
        else:
            raise Fail("preflight reconcile symlinked temp parent accepted")
        require(sorted(p.name for p in sandbox.iterdir()) == before,
                "preflight reconcile symlinked temp parent published a child")
    print("PASS: preflight reconcile fixture reuses checked drill parent guard")

    prove_helper_source_symlink_rejected()
    prove_helper_source_swap_during_import_is_pinned()
    prove_helper_parent_swap_after_pin_uses_original_source()
    prove_helper_ancestor_swap_during_fd_walk_rejected()
    module = load_module()
    module.enforce_execution_identity()
    module.enforce_runtime_authorities()
    canonical_before = {
        module.CONTRACT: module.CONTRACT.read_bytes(),
        module.STATUS: module.STATUS.read_bytes(),
    }
    # Validate the real upstream source chain before synthetic repository-local
    # fixtures make the checkout intentionally dirty. Inside the fault-injection
    # fixture, preserve and verify the same three upstream call sites without
    # rerunning unrelated clean-worktree source-binding checks.
    original_loader = module.load_validator_module
    canonical_validator = original_loader()
    expected_upstream = (
        (canonical_validator.GEN_VALIDATOR, "environment generation"),
        (canonical_validator.OBJECTIVE_VALIDATOR, "recovery objectives"),
        (canonical_validator.DRILL_VALIDATOR, "restore drill request"),
    )
    for path, label in expected_upstream:
        canonical_validator.run_validator(path, label)
    upstream_calls: list[tuple[Path, str]] = []

    def isolated_fixture_validator():
        validator = original_loader()

        def record_prevalidated(path: Path, label: str) -> None:
            require(
                (path, label) in expected_upstream,
                f"preflight fixture attempted unreviewed upstream validator: {label}",
            )
            upstream_calls.append((path, label))

        validator.run_validator = record_prevalidated
        return validator

    module.load_validator_module = isolated_fixture_validator
    try:
        with guarded_temporary_directory(".tmp-preflight-reconcile-negative-", TMP_PARENT) as tmpdir:
            tmp = Path(tmpdir)
            prove_second_replace_rollback(module, tmp)
            prove_rollback_attempts_all_authorities(module)
            prove_post_validator_rollback(module, tmp)
    finally:
        module.load_validator_module = original_loader
    require(
        upstream_calls == list(expected_upstream) * 2,
        f"preflight fixture upstream validation call order drift: {upstream_calls}",
    )
    module.enforce_execution_identity()
    print("PASS boundary: real upstream validators executed before fixture; two ordered synthetic call chains preserved")
    for path, payload in canonical_before.items():
        require(path.read_bytes() == payload, f"canonical authority mutated by rollback negative: {path.name}")
    print("Restore drill preflight reconcile negative suite PASS")
    print("partial preflight/status publication accepted: false")
    print("rollback skips later authority after earlier restore failure: false")
    print("failed post-publication validation retained authority mutation: false")
    print("canonical preflight/status mutation during negative proof: false")
    print("production evidence created: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE DRILL PREFLIGHT RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
