#!/usr/bin/env python3
"""Prove restore-drill preflight authority loading and reconcile rollback fail closed."""

from __future__ import annotations

import ast
import importlib.util
import os
import stat
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-preflight.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-preflight.py"
CANONICAL_CONTRACT = ROOT / "contracts/operations/backup-restore-drill-preflight-contract.v1.json"
CANONICAL_STATUS = ROOT / "contracts/operations/production-operability-status.json"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
DRILL_REQUEST_LOAD_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-drill-request-load-negative.py"
DRILL_REQUEST_RECONCILE_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-drill-request-reconcile-negative.py"
PREFLIGHT_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-drill-preflight-negative.py"
PREFLIGHT_AUTHORITY = ROOT / "scripts/validate-memory-os-backup-restore-drill-preflight-authority.py"
PREFLIGHT_RECONCILE_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pin_checked_helper_parent(path: Path) -> int:
    """Walk from a trusted repository/temp anchor, never through a symlinked ancestor."""
    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY"),
            "preflight load fixture guard no-follow directory open unsupported")
    anchor = ROOT if path.is_relative_to(ROOT) else Path(tempfile.gettempdir())
    try:
        relative = path.parent.relative_to(anchor)
    except ValueError as exc:
        raise Fail("preflight load fixture guard parent outside trusted roots") from exc
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    require(anchor.is_dir() and not anchor.is_symlink(),
            "preflight load fixture guard trusted anchor missing or symlinked")
    try:
        fd = os.open(anchor, flags)
    except OSError as exc:
        raise Fail("preflight load fixture guard anchor open failed") from exc
    try:
        opened = os.fstat(fd)
        entry = anchor.lstat()
        require(
            stat.S_ISDIR(entry.st_mode)
            and (entry.st_dev, entry.st_ino) == (opened.st_dev, opened.st_ino),
            "preflight load fixture guard trusted anchor identity drift",
        )
        cursor = anchor
        for part in relative.parts:
            cursor = cursor / part
            require(cursor.is_dir() and not cursor.is_symlink(),
                    "preflight load fixture guard ancestor missing or symlinked")
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
            opened = os.fstat(fd)
            entry = cursor.lstat()
            require(
                stat.S_ISDIR(entry.st_mode)
                and (entry.st_dev, entry.st_ino) == (opened.st_dev, opened.st_ino),
                "preflight load fixture guard ancestor identity drift",
            )
        return fd
    except OSError as exc:
        os.close(fd)
        raise Fail("preflight load fixture guard parent open failed") from exc
    except BaseException:
        os.close(fd)
        raise


def load_pinned_fixture_guard(path: Path, name: str):
    """Bind each checked ancestor and the leaf FD before executing helper source."""
    parent_fd = pin_checked_helper_parent(path)
    try:
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        except OSError as exc:
            raise Fail("preflight load fixture guard source open failed") from exc
        try:
            opened = os.fstat(fd)
            entry = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
            require(
                stat.S_ISREG(opened.st_mode) and stat.S_ISREG(entry.st_mode)
                and (opened.st_dev, opened.st_ino) == (entry.st_dev, entry.st_ino),
                "preflight load fixture guard source identity drift",
            )
            with os.fdopen(os.dup(fd), "rb") as stream:
                source = stream.read()
            spec = importlib.util.spec_from_file_location(name, path)
            require(spec is not None and spec.loader is not None,
                    "preflight load fixture guard cannot load")
            module = importlib.util.module_from_spec(spec)
            exec(compile(source, str(path), "exec"), module.__dict__)
            return module
        except OSError as exc:
            raise Fail("preflight load fixture guard pinned source read failed") from exc
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)


def guarded_temporary_directory(prefix: str, parent: Path):
    require(DRILL_REQUEST_LOAD_NEGATIVE.is_file() and not DRILL_REQUEST_LOAD_NEGATIVE.is_symlink(),
            "drill request fixture parent guard source missing or symlinked")
    module = load_pinned_fixture_guard(DRILL_REQUEST_LOAD_NEGATIVE, "memory_os_drill_fixture_guard_preflight_load")
    require(callable(getattr(module, "guarded_temporary_directory", None)),
            "drill request fixture parent guard callable missing")
    try:
        return module.guarded_temporary_directory(prefix, parent)
    except module.Fail as exc:
        raise Fail(str(exc)) from exc



def prove_helper_source_symlink_rejected() -> None:
    # Test the import boundary independently of the symlink-parent fixture.
    global DRILL_REQUEST_LOAD_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="preflight-fixture-helper-source-") as raw:
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
                        f"preflight helper source rejected at wrong boundary: {exc}")
            else:
                raise Fail("preflight symlinked fixture helper accepted")
        finally:
            DRILL_REQUEST_LOAD_NEGATIVE = original
    print("PASS: preflight fixture helper symlink rejected before import")



def prove_helper_source_swap_during_import_is_pinned() -> None:
    # A positive helper must survive replacement after its source FD is opened.
    global DRILL_REQUEST_LOAD_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="preflight-load-helper-import-race-") as raw:
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
                "preflight load helper pinned import positive control failed",
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
                "preflight load helper import executed substituted source",
            )
            require(swapped and trusted.is_symlink() and parked.is_file(),
                    "preflight load helper race probe did not substitute checked source")
        finally:
            importlib.util.spec_from_file_location = original_spec
            DRILL_REQUEST_LOAD_NEGATIVE = original_path
    print("PASS: preflight load helper import uses pinned source after pathname substitution")


def prove_helper_parent_swap_after_pin_uses_original_source() -> None:
    global DRILL_REQUEST_LOAD_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="preflight-load-helper-parent-race-") as raw:
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
                "preflight load parent-pinned helper positive control failed",
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
                "preflight load helper import followed substituted parent",
            )
            require(swapped and trusted_parent.is_symlink() and (parked_parent / "helper.py").is_file(),
                    "preflight load helper parent race did not substitute checked parent")
        finally:
            os.open = original_open
            DRILL_REQUEST_LOAD_NEGATIVE = original_path
    print("PASS: preflight load helper parent swap preserves pinned source")


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
                    str(exc) == "preflight load fixture guard ancestor identity drift",
                    f"preflight helper ancestor swap rejected at wrong boundary: {exc}",
                )
            else:
                raise Fail("preflight load helper ancestor swap accepted")
            require(swapped and checked_ancestor.is_symlink()
                    and (parked_ancestor / "nested/helper.py").is_file(),
                    "preflight helper ancestor swap did not preserve pinned original")
            require((redirect_parent / "helper.py").read_text(encoding="utf-8")
                    == "raise RuntimeError('untrusted ancestor helper executed')\n",
                    "preflight helper ancestor swap modified untrusted source")
        finally:
            os.open = original_open
            DRILL_REQUEST_LOAD_NEGATIVE = original_path
    print("PASS: preflight load helper ancestor swap fails closed during FD walk")


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
    name: str,
    field: str,
    attribute: str,
    replacement: Path,
    contract_before: bytes,
    status_before: bytes,
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
        require(CANONICAL_CONTRACT.read_bytes() == contract_before, f"canonical contract mutated while rejecting {name}")
        require(CANONICAL_STATUS.read_bytes() == status_before, f"canonical status mutated while rejecting {name}")
    finally:
        setattr(reconciler, attribute, original)


def prove_data_and_executable_authority_rejection(reconciler: object) -> None:
    contract_before = CANONICAL_CONTRACT.read_bytes()
    status_before = CANONICAL_STATUS.read_bytes()
    cases = (
        ("preflight contract substitution", "preflight contract", "CONTRACT", reconciler.STATUS),
        ("environment generation registry substitution", "environment generation registry", "GEN_REGISTRY", reconciler.OBJECTIVES),
        ("recovery objectives registry substitution", "recovery objectives registry", "OBJECTIVES", reconciler.DRILL_REGISTRY),
        ("drill request registry substitution", "drill request registry", "DRILL_REGISTRY", reconciler.GEN_REGISTRY),
        ("preflight validator substitution", "preflight validator", "VALIDATOR_MODULE", reconciler.OPERABILITY_VALIDATOR),
        ("operability validator substitution", "operability validator", "OPERABILITY_VALIDATOR", reconciler.VALIDATOR_MODULE),
        ("production operability status substitution", "production operability status", "STATUS", reconciler.CONTRACT),
    )
    for name, field, attribute, replacement in cases:
        expect_direct_authority_rejected(reconciler, name, field, attribute, replacement, contract_before, status_before)
    print(f"PASS boundary: direct preflight data/executable substitutions rejected: {len(cases)}")


def prove_post_reconcile_output_suppression(reconciler: object) -> None:
    """Bound and suppress all raw post-validation subprocess diagnostics."""
    original_run = reconciler.subprocess.run
    calls: list[list[str]] = []

    def reviewed_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append(command)
        require(command == [reconciler.sys.executable, str(reconciler.VALIDATOR_MODULE)],
                "preflight post-validator command drift")
        require(kwargs.get("cwd") == reconciler.ROOT and
                kwargs.get("stdout") == reconciler.subprocess.DEVNULL and
                kwargs.get("stderr") == reconciler.subprocess.DEVNULL and
                kwargs.get("check") is False and kwargs.get("timeout") == 180,
                "preflight post-validator output/timeout boundary drift")
        return SimpleNamespace(returncode=0)

    try:
        reconciler.subprocess.run = reviewed_run
        reconciler.run_post_reconcile_validator(reconciler.VALIDATOR_MODULE, "preflight")
        require(len(calls) == 1, "preflight post-validator positive was not invoked")

        reconciler.subprocess.run = lambda *args, **kwargs: SimpleNamespace(
            returncode=1, stdout="SYNTHETIC_SECRET_STDOUT_DO_NOT_LOG",
            stderr="SYNTHETIC_SECRET_STDERR_DO_NOT_LOG",
        )
        try:
            reconciler.run_post_reconcile_validator(reconciler.VALIDATOR_MODULE, "preflight")
        except reconciler.Fail as exc:
            require("post-reconcile preflight validator failed" in str(exc) and
                    "SYNTHETIC_SECRET" not in str(exc),
                    "preflight post-validator exposed raw output")
        else:
            raise Fail("preflight post-validator failed exit accepted")

        reconciler.subprocess.run = lambda *args, **kwargs: SimpleNamespace(returncode=True)
        try:
            reconciler.run_post_reconcile_validator(reconciler.VALIDATOR_MODULE, "preflight")
        except reconciler.Fail:
            pass
        else:
            raise Fail("preflight post-validator boolean exit accepted")

        def timeout(*args: object, **kwargs: object) -> None:
            raise reconciler.subprocess.TimeoutExpired("SYNTHETIC_SECRET_COMMAND", 180)
        reconciler.subprocess.run = timeout
        try:
            reconciler.run_post_reconcile_validator(reconciler.VALIDATOR_MODULE, "preflight")
        except reconciler.Fail as exc:
            require("TimeoutExpired" in str(exc) and "SYNTHETIC_SECRET" not in str(exc),
                    "preflight post-validator timeout leaked command")
        else:
            raise Fail("preflight post-validator timeout accepted")

        def os_failure(*args: object, **kwargs: object) -> None:
            raise OSError("SYNTHETIC_SECRET_OSERROR_DO_NOT_LOG")
        reconciler.subprocess.run = os_failure
        try:
            reconciler.run_post_reconcile_validator(reconciler.VALIDATOR_MODULE, "preflight")
        except reconciler.Fail as exc:
            require("OSError" in str(exc) and "SYNTHETIC_SECRET" not in str(exc),
                    "preflight post-validator OS failure leaked secret")
        else:
            raise Fail("preflight post-validator OS failure accepted")
    finally:
        reconciler.subprocess.run = original_run
    print("PASS: preflight post-reconcile bounded output-suppressed positive and 4 negatives")


def prove_atomic_write_failure(reconciler: object) -> None:
    canonical_contract_before = CANONICAL_CONTRACT.read_bytes()
    canonical_status_before = CANONICAL_STATUS.read_bytes()
    canonical_contract_mode = mode(CANONICAL_CONTRACT)
    canonical_status_mode = mode(CANONICAL_STATUS)

    with guarded_temporary_directory(".tmp-preflight-atomic-write-", TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        contract = tmp / CANONICAL_CONTRACT.name
        shutil.copyfile(CANONICAL_CONTRACT, contract)
        contract.chmod(canonical_contract_mode)
        contract_before = contract.read_bytes()
        contract_mode = mode(contract)
        original_replace = reconciler.os.replace

        def reject_replace(source: str | Path, destination: str | Path) -> None:
            raise OSError("synthetic atomic replace rejection")

        reconciler.os.replace = reject_replace
        try:
            expect_domain_fail(
                "preflight atomic replace rejection",
                lambda: reconciler.write_text(contract, contract_before.decode("utf-8") + " "),
                reconciler.Fail,
            )
        finally:
            reconciler.os.replace = original_replace

        require(contract.read_bytes() == contract_before, "atomic replace rejection mutated fixture preflight contract")
        require(mode(contract) == contract_mode, "atomic replace rejection changed fixture preflight contract mode")
        leftovers = list(contract.parent.glob(f".{contract.name}.*.tmp"))
        require(not leftovers, f"atomic replace rejection left temporary fixture authority files: {leftovers}")

    require(CANONICAL_CONTRACT.read_bytes() == canonical_contract_before, "atomic replace proof mutated canonical preflight contract")
    require(CANONICAL_STATUS.read_bytes() == canonical_status_before, "atomic replace proof mutated canonical production status")
    require(mode(CANONICAL_CONTRACT) == canonical_contract_mode, "atomic replace proof changed canonical preflight contract mode")
    require(mode(CANONICAL_STATUS) == canonical_status_mode, "atomic replace proof changed canonical production status mode")
    print("PASS boundary: failed atomic preflight fixture write preserves exact bytes+mode and cleans temporary files")
    print("PASS boundary: canonical preflight/status authorities remain read-only during atomic write negative proof")


def prove_transactional_rollback(reconciler: object, tmp: Path) -> None:
    contract = tmp / "preflight-contract.json"
    status = tmp / "production-operability-status.json"
    shutil.copyfile(CANONICAL_CONTRACT, contract)
    shutil.copyfile(CANONICAL_STATUS, status)
    before_contract = contract.read_bytes()
    before_status = status.read_bytes()

    original_contract = reconciler.CONTRACT
    original_status = reconciler.STATUS
    original_run = reconciler.subprocess.run
    observed_commands: list[list[str]] = []

    expected_paths = [
        str(reconciler.load_validator_module().GEN_VALIDATOR),
        str(reconciler.load_validator_module().OBJECTIVE_VALIDATOR),
        str(reconciler.load_validator_module().DRILL_VALIDATOR),
        str(reconciler.VALIDATOR_MODULE),
        str(reconciler.OPERABILITY_VALIDATOR),
    ]

    def fail_only_aggregate_post_reconcile(*args, **kwargs):
        command = [str(item) for item in (args[0] if args else [])]
        observed_commands.append(command)
        call_index = len(observed_commands) - 1
        require(call_index < len(expected_paths), "unexpected extra preflight validator invocation")
        require(command[-1] == expected_paths[call_index], f"preflight validator order drift at call {call_index + 1}: {command}")
        if call_index < 4:
            return SimpleNamespace(returncode=0, stdout="upstream/preflight authority validator pass", stderr="")
        return SimpleNamespace(returncode=1, stdout="SYNTHETIC_SECRET_POST_VALIDATION_DO_NOT_LOG", stderr="")

    reconciler.CONTRACT = contract
    reconciler.STATUS = status
    reconciler.subprocess.run = fail_only_aggregate_post_reconcile
    try:
        expect_domain_fail("forced aggregate operability validation failure", reconciler._reconcile, reconciler.Fail)
    finally:
        reconciler.CONTRACT = original_contract
        reconciler.STATUS = original_status
        reconciler.subprocess.run = original_run

    require(len(observed_commands) == 5, "expected exact five-stage preflight validation chain")
    require(contract.read_bytes() == before_contract, "preflight contract was not rolled back byte-for-byte")
    require(status.read_bytes() == before_status, "production status was not rolled back byte-for-byte")
    print("PASS boundary: validator order is environment generation -> recovery objectives -> drill request -> preflight -> aggregate Operability")
    print("PASS boundary: preflight validator passed before aggregate operability rejection")
    print("PASS rollback: preflight contract restored byte-for-byte after aggregate rejection")
    print("PASS rollback: production status restored byte-for-byte after aggregate rejection")


def prove_rollback_failure_diagnostics(reconciler: object, tmp: Path) -> None:
    contract = tmp / "preflight-contract-rollback-failure.json"
    status = tmp / "production-operability-status-rollback-failure.json"
    shutil.copyfile(CANONICAL_CONTRACT, contract)
    shutil.copyfile(CANONICAL_STATUS, status)
    before_status = status.read_bytes()

    original_contract = reconciler.CONTRACT
    original_status = reconciler.STATUS
    original_run = reconciler.subprocess.run
    original_write = reconciler.write_text
    observed_commands: list[list[str]] = []
    write_count = 0

    expected_paths = [
        str(reconciler.load_validator_module().GEN_VALIDATOR),
        str(reconciler.load_validator_module().OBJECTIVE_VALIDATOR),
        str(reconciler.load_validator_module().DRILL_VALIDATOR),
        str(reconciler.VALIDATOR_MODULE),
        str(reconciler.OPERABILITY_VALIDATOR),
    ]

    def fail_only_aggregate_post_reconcile(*args, **kwargs):
        command = [str(item) for item in (args[0] if args else [])]
        observed_commands.append(command)
        call_index = len(observed_commands) - 1
        require(call_index < len(expected_paths), "unexpected extra preflight validator invocation during rollback-failure proof")
        require(command[-1] == expected_paths[call_index], f"preflight rollback-failure validator order drift at call {call_index + 1}: {command}")
        if call_index < 4:
            return SimpleNamespace(returncode=0, stdout="upstream/preflight authority validator pass", stderr="")
        return SimpleNamespace(returncode=1, stdout="SYNTHETIC_SECRET_POST_VALIDATION_DO_NOT_LOG", stderr="")

    def fail_first_rollback_write(path: Path, text: str) -> None:
        nonlocal write_count
        write_count += 1
        if write_count == 3:
            raise reconciler.Fail("SYNTHETIC_SECRET_ROLLBACK_DO_NOT_LOG")
        original_write(path, text)

    reconciler.CONTRACT = contract
    reconciler.STATUS = status
    reconciler.subprocess.run = fail_only_aggregate_post_reconcile
    reconciler.write_text = fail_first_rollback_write
    try:
        try:
            reconciler._reconcile()
        except reconciler.Fail as exc:
            diagnostic = str(exc)
            require("preflight reconcile transaction failed (Fail)" in diagnostic,
                    f"primary preflight exception class lost: {diagnostic}")
            require("rollback incomplete" in diagnostic and "Fail" in diagnostic,
                    f"rollback incompleteness/class diagnostic missing: {diagnostic}")
            require("SYNTHETIC_SECRET" not in diagnostic,
                    "preflight rollback diagnostic leaked synthetic secret")
        else:
            raise Fail("rollback-failure transaction unexpectedly succeeded")
    finally:
        reconciler.CONTRACT = original_contract
        reconciler.STATUS = original_status
        reconciler.subprocess.run = original_run
        reconciler.write_text = original_write

    require(len(observed_commands) == 5, "expected exact five-stage validation chain during rollback-failure proof")
    require(write_count == 4, f"rollback failure stopped later authority restoration: write_count={write_count}")
    require(status.read_bytes() == before_status, "production status was not restored after earlier rollback failure")
    print("PASS rollback: later preflight authorities are still restored after the first rollback write fails")
    print("PASS diagnostic: primary post-validation failure preserved alongside rollback incomplete failure")


def prove_preflight_reconcile_pinned_reader(reconciler: object) -> None:
    """Actual reconciler snapshot reads are bounded and cannot follow swapped parents."""
    protected = (CANONICAL_CONTRACT.read_bytes(), CANONICAL_STATUS.read_bytes())
    with guarded_temporary_directory(".tmp-preflight-reconcile-fd-race-", TMP_PARENT) as raw:
        sandbox = Path(raw)
        oversized = sandbox / "oversized.json"
        oversized.write_bytes(b"x" * (reconciler.MAX_AUTHORITY_BYTES + 1))
        try:
            reconciler.read_text(oversized)
        except reconciler.Fail as exc:
            require(str(exc) == "preflight reconcile authority exceeds 1 MiB",
                    "preflight reconciler oversized read rejected at wrong boundary")
        else:
            raise Fail("preflight reconciler accepted oversized snapshot")
        for case in ("parent", "ancestor"):
            checked = sandbox / (case + "-checked")
            parked = sandbox / (case + "-parked")
            redirect = sandbox / (case + "-redirect")
            checked.mkdir()
            redirect.mkdir()
            if case == "ancestor":
                (checked / "nested").mkdir()
                (redirect / "nested").mkdir()
                checked_leaf = checked / "nested/candidate.json"
                redirect_leaf = redirect / "nested/candidate.json"
                trigger = "nested"
            else:
                checked_leaf = checked / "candidate.json"
                redirect_leaf = redirect / "candidate.json"
                trigger = "candidate.json"
            checked_leaf.write_bytes(b'{"source":"pinned"}')
            redirect_leaf.write_bytes(b'{"source":"redirected","secret":"SYNTHETIC_PRIVATE_CANARY"}')
            original_open = os.open
            swapped = False

            def swap_during_walk(target, flags, *args, **kwargs):
                nonlocal swapped
                if not swapped and target == trigger and kwargs.get("dir_fd") is not None:
                    swapped = True
                    checked.rename(parked)
                    checked.symlink_to(redirect, target_is_directory=True)
                return original_open(target, flags, *args, **kwargs)

            try:
                require(reconciler.read_text(checked_leaf) == '{"source":"pinned"}',
                        f"preflight reconciler {case} positive control failed")
                os.open = swap_during_walk
                value = reconciler.read_text(checked_leaf)
                require(swapped and value == '{"source":"pinned"}',
                        f"preflight reconciler {case} read substituted authority")
                require(redirect_leaf.read_bytes() == b'{"source":"redirected","secret":"SYNTHETIC_PRIVATE_CANARY"}',
                        f"preflight reconciler {case} modified canary")
            finally:
                os.open = original_open
    require((CANONICAL_CONTRACT.read_bytes(), CANONICAL_STATUS.read_bytes()) == protected,
            "preflight reconciler pinned reader changed protected authorities")
    print("PASS: preflight reconciler bounded JSON snapshot and parent/ancestor FD race negatives")


def prove_preflight_reconcile_strict_json(reconciler: object) -> None:
    protected = (CANONICAL_CONTRACT.read_bytes(), CANONICAL_STATUS.read_bytes())
    with guarded_temporary_directory(".tmp-preflight-reconcile-json-", TMP_PARENT) as raw:
        path = Path(raw) / "candidate.json"
        path.write_bytes(b'{"nested":{"count":1}}')
        require(reconciler.load(path) == {"nested": {"count": 1}},
                "preflight reconcile JSON positive failed")
        for label, payload, expected in (
            ("duplicate", b'{"nested":{"key":1,"key":2}}',
             "preflight reconcile JSON duplicate key refused"),
            ("NaN", b'{"value":NaN}', "preflight reconcile JSON nonfinite number refused"),
            ("Infinity", b'{"value":Infinity}', "preflight reconcile JSON nonfinite number refused"),
            ("float overflow", b'{"value":1e999}', "preflight reconcile JSON nonfinite number refused"),
            ("129 digit integer", b'{"value":' + b"9" * 129 + b"}",
             "preflight reconcile JSON integer too large"),
            ("invalid UTF-8", b'{"value":"\xff"}', "preflight reconcile authority invalid UTF-8"),
            ("nonobject root", b"[]", "preflight reconcile JSON root must be object"),
        ):
            path.write_bytes(payload)
            try:
                reconciler.load(path)
            except reconciler.Fail as exc:
                require(str(exc) == expected and "SYNTHETIC_PRIVATE_" not in str(exc),
                        f"preflight reconcile JSON {label} wrong rejection")
            else:
                raise Fail(f"preflight reconcile JSON {label} accepted")
    require((CANONICAL_CONTRACT.read_bytes(), CANONICAL_STATUS.read_bytes()) == protected,
            "preflight reconcile strict JSON changed protected authorities")
    print("PASS: preflight reconciler strict JSON positive and seven ambiguity negatives")


def prove_preflight_reconcile_descriptor_faults(reconciler: object) -> None:
    with guarded_temporary_directory(".tmp-preflight-reconcile-fd-fault-", TMP_PARENT) as raw:
        path = Path(raw) / "positive.json"
        path.write_bytes(b'{"safe":true}')
        for fault, expected in (
            ("close", "preflight reconcile authority cleanup failed"),
            ("fdopen", "preflight reconcile authority unreadable"),
        ):
            original_open, original_close, original_fdopen = os.open, os.close, os.fdopen
            opened: list[int] = []
            faulted = False

            def capture_open(*args, **kwargs):
                descriptor = original_open(*args, **kwargs)
                opened.append(descriptor)
                return descriptor

            def close_then_fail(descriptor):
                nonlocal faulted
                original_close(descriptor)
                if not faulted:
                    faulted = True
                    raise OSError("SYNTHETIC_PRIVATE_CLOSE_CANARY")

            def fdopen_then_fail(descriptor, *args, **kwargs):
                nonlocal faulted
                faulted = True
                raise OSError("SYNTHETIC_PRIVATE_FDOPEN_CANARY")

            try:
                os.open = capture_open
                if fault == "close":
                    os.close = close_then_fail
                else:
                    os.fdopen = fdopen_then_fail
                try:
                    reconciler.read_text(path)
                except reconciler.Fail as exc:
                    require(str(exc) == expected and exc.__suppress_context__ and exc.__cause__ is None,
                            f"preflight reconcile {fault} leaked private descriptor fault")
                else:
                    raise Fail(f"preflight reconcile {fault} fault unexpectedly accepted")
            finally:
                os.open, os.close, os.fdopen = original_open, original_close, original_fdopen
            require(faulted and opened, f"preflight reconcile {fault} fault injection not reached")
            for descriptor in opened:
                try:
                    os.fstat(descriptor)
                except OSError:
                    pass
                else:
                    raise Fail(f"preflight reconcile {fault} leaked descriptor")
            require(reconciler.read_text(path) == '{"safe":true}',
                    f"preflight reconcile {fault} recovery positive failed")
    print("PASS: preflight reconcile close/fdopen private faults close all descriptors")


def prove_preflight_reconcile_platform_flags(reconciler: object) -> None:
    with guarded_temporary_directory(".tmp-preflight-reconcile-flags-", TMP_PARENT) as raw:
        path = Path(raw) / "positive.json"
        path.write_bytes(b'{"safe":true}')
        for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY"):
            original = getattr(os, flag)
            try:
                for invalid in (None, 0):
                    setattr(os, flag, invalid)
                    try:
                        reconciler.read_text(path)
                    except reconciler.Fail as exc:
                        require(str(exc) == "preflight reconcile authority nofollow support required"
                                and exc.__suppress_context__ and exc.__cause__ is None,
                                f"preflight reconcile {flag} unsafe platform class drift")
                    else:
                        raise Fail(f"preflight reconcile accepted unsafe {flag}")
            finally:
                setattr(os, flag, original)
        require(reconciler.read_text(path) == '{"safe":true}',
                "preflight reconcile platform flag restoration positive failed")
    print("PASS: preflight reconcile None/zero safety flags rejected")


def prove_preflight_reconcile_writer_ownership(reconciler: object) -> None:
    protected = (CANONICAL_CONTRACT.read_bytes(), CANONICAL_STATUS.read_bytes())
    with guarded_temporary_directory(".tmp-preflight-write-ownership-", TMP_PARENT) as raw:
        sandbox = Path(raw)
        path = sandbox / "candidate.json"
        positive = b'{"safe":true}'
        path.write_bytes(positive)
        path.chmod(0o640)
        for label, value, expected in (
            ("oversized", "x" * (reconciler.MAX_AUTHORITY_BYTES + 1),
             "preflight reconcile write size limit exceeded"),
            ("nonstring", None, "preflight reconcile write payload invalid"),
        ):
            try:
                reconciler.write_text(path, value)
            except reconciler.Fail as exc:
                require(str(exc) == expected, f"preflight write {label} wrong rejection")
            else:
                raise Fail(f"preflight write {label} accepted")
        with tempfile.TemporaryDirectory(prefix="preflight-write-outside-") as outside:
            canary = Path(outside) / "canary.json"
            canary.write_bytes(positive)
            link = sandbox / "alias.json"
            link.symlink_to(canary)
            try:
                reconciler.write_text(link, '{"unsafe":true}')
            except reconciler.Fail as exc:
                require(str(exc) == "preflight reconcile write path unsafe",
                        "preflight write symlink rejected at wrong boundary")
            else:
                raise Fail("preflight write followed symlink")
            require(canary.read_bytes() == positive, "preflight write changed external canary")

        original_fdopen = os.fdopen
        original_mkstemp = tempfile.mkstemp
        opened: list[int] = []

        def capture_mkstemp(*args, **kwargs):
            descriptor, name = original_mkstemp(*args, **kwargs)
            opened.append(descriptor)
            return descriptor, name

        class ShortStream:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return self.stream.__exit__(*args)

            def write(self, value):
                return len(value) - 1

            def flush(self):
                self.stream.flush()

            def fileno(self):
                return self.stream.fileno()

        for fault, expected in (
            ("fdopen", "preflight reconcile atomic write failed"),
            ("short", "preflight reconcile write short buffered write refused"),
        ):
            opened.clear()

            def fault_fdopen(descriptor, *args, **kwargs):
                if fault == "fdopen":
                    raise OSError("SYNTHETIC_PRIVATE_FDOPEN_CANARY")
                return ShortStream(original_fdopen(descriptor, *args, **kwargs))

            try:
                tempfile.mkstemp = capture_mkstemp
                os.fdopen = fault_fdopen
                try:
                    reconciler.write_text(path, '{"safe":false}')
                except reconciler.Fail as exc:
                    require(str(exc) == expected and "SYNTHETIC_PRIVATE_" not in str(exc),
                            f"preflight write {fault} leaked or misclassified")
                else:
                    raise Fail(f"preflight write {fault} fault accepted")
            finally:
                os.fdopen = original_fdopen
                tempfile.mkstemp = original_mkstemp
            require(len(opened) == 1, f"preflight write {fault} descriptor injection not reached")
            try:
                os.fstat(opened[0])
            except OSError:
                pass
            else:
                raise Fail(f"preflight write {fault} leaked descriptor")
            require(path.read_bytes() == positive and mode(path) == 0o640,
                    f"preflight write {fault} changed fixture bytes or mode")
            require(not list(sandbox.glob(".candidate.json.*.tmp")),
                    f"preflight write {fault} left temporary file")
    require((CANONICAL_CONTRACT.read_bytes(), CANONICAL_STATUS.read_bytes()) == protected,
            "preflight writer negative mutated protected authorities")
    print("PASS: preflight writer oversized/symlink/fdopen/short-write private ownership negatives")


def prove_preflight_reconcile_private_path_diagnostics(reconciler: object) -> None:
    original_resolve = Path.resolve
    original_module_from_spec = reconciler.importlib.util.module_from_spec
    private = "SYNTHETIC_PRIVATE_PATH_CANARY"

    def fail_private_resolve(self, *args, **kwargs):
        if self == CANONICAL_CONTRACT:
            raise OSError(private)
        return original_resolve(self, *args, **kwargs)

    def require_private_fail(action, expected):
        try:
            action()
        except reconciler.Fail as exc:
            require(str(exc) == expected and exc.__suppress_context__ and exc.__cause__ is None
                    and private not in str(exc),
                    "preflight reconcile path/import leaked private exception")
        else:
            raise Fail("preflight reconcile private path/import exception accepted")

    try:
        Path.resolve = fail_private_resolve
        require_private_fail(lambda: reconciler.repo_relative(CANONICAL_CONTRACT),
                             "preflight reconcile authority path unsafe")
        require_private_fail(
            lambda: reconciler.require_exact_repo_file(
                CANONICAL_CONTRACT, reconciler.CONTRACT_REL, "preflight contract"),
            "preflight contract missing or escapes repository")
    finally:
        Path.resolve = original_resolve

    def fail_private_import(_spec):
        raise OSError(private)

    def fail_private_runtime(_spec):
        raise RuntimeError(private)

    try:
        reconciler.importlib.util.module_from_spec = fail_private_import
        require_private_fail(reconciler.load_validator_module,
                             "preflight reconcile validator import unavailable")
        reconciler.importlib.util.module_from_spec = fail_private_runtime
        require_private_fail(reconciler.load_validator_module,
                             "preflight reconcile validator import unavailable")
    finally:
        reconciler.importlib.util.module_from_spec = original_module_from_spec
    print("PASS: preflight reconcile private path and validator import errors suppressed")


def prove_preflight_reconcile_repo_refs(reconciler: object) -> None:
    protected = (CANONICAL_CONTRACT.read_bytes(), CANONICAL_STATUS.read_bytes())
    with guarded_temporary_directory(".tmp-preflight-ref-alias-", TMP_PARENT) as raw:
        sandbox = Path(raw)
        real = sandbox / "real"
        real.mkdir()
        file = real / "evidence.json"
        file.write_bytes(b'{"safe":true}')
        require(reconciler.require_repo_file(file, "synthetic ref unsafe") == file.relative_to(ROOT),
                "preflight reconcile canonical evidence ref rejected")
        alias = sandbox / "alias.json"
        alias.symlink_to(file)
        parent_alias = sandbox / "parent-alias"
        parent_alias.symlink_to(real, target_is_directory=True)
        loop = sandbox / "loop.json"
        loop.symlink_to(loop.name)
        for label, candidate, expected in (
            ("leaf alias", alias, "synthetic ref unsafe"),
            ("ancestor alias", parent_alias / file.name, "synthetic ref unsafe"),
            ("symlink loop", loop, "preflight reconcile repository file unsafe"),
            ("missing", sandbox / "missing.json", "preflight reconcile repository file unsafe"),
        ):
            try:
                reconciler.require_repo_file(candidate, "synthetic ref unsafe")
            except reconciler.Fail as exc:
                require(str(exc) == expected, f"preflight reconcile {label} wrong ref rejection")
            else:
                raise Fail(f"preflight reconcile {label} ref accepted")
        with tempfile.TemporaryDirectory(prefix="preflight-ref-outside-") as outside:
            canary = Path(outside) / "canary.json"
            canary.write_bytes(b'{"private":"SYNTHETIC_PRIVATE_CANARY"}')
            escaped = sandbox / "escaped.json"
            escaped.symlink_to(canary)
            try:
                reconciler.require_repo_file(escaped, "synthetic ref unsafe")
            except reconciler.Fail as exc:
                require(str(exc) == "preflight reconcile repository file unsafe",
                        "preflight reconcile escaped ref leaked private path")
            else:
                raise Fail("preflight reconcile escaped ref accepted")
            require(canary.read_bytes() == b'{"private":"SYNTHETIC_PRIVATE_CANARY"}',
                    "preflight reconcile ref negative changed external canary")
    require((CANONICAL_CONTRACT.read_bytes(), CANONICAL_STATUS.read_bytes()) == protected,
            "preflight reconcile ref negative changed protected authorities")
    print("PASS: preflight reconcile canonical evidence ref and five symlink/alias negatives")


def prove_preflight_reconcile_writer_preopen_faults(reconciler: object) -> None:
    with guarded_temporary_directory(".tmp-preflight-write-preopen-", TMP_PARENT) as raw:
        path = Path(raw) / "candidate.json"
        positive = b'{"safe":true}'
        path.write_bytes(positive)
        path.chmod(0o640)
        original_mkstemp, original_fchmod = tempfile.mkstemp, os.fchmod
        for fault in ("mkstemp", "fchmod"):
            opened: list[int] = []
            injected = False

            def fault_mkstemp(*args, **kwargs):
                nonlocal injected
                if fault == "mkstemp":
                    injected = True
                    raise OSError("SYNTHETIC_PRIVATE_MKSTEMP_CANARY")
                descriptor, name = original_mkstemp(*args, **kwargs)
                opened.append(descriptor)
                return descriptor, name

            def fault_fchmod(descriptor, value):
                nonlocal injected
                injected = True
                raise OSError("SYNTHETIC_PRIVATE_FCHMOD_CANARY")

            try:
                tempfile.mkstemp = fault_mkstemp
                if fault == "fchmod":
                    os.fchmod = fault_fchmod
                try:
                    reconciler.write_text(path, '{"safe":false}')
                except reconciler.Fail as exc:
                    require(str(exc) == "preflight reconcile atomic write failed"
                            and exc.__suppress_context__ and exc.__cause__ is None,
                            f"preflight writer {fault} leaked private preopen exception")
                else:
                    raise Fail(f"preflight writer {fault} preopen fault accepted")
            finally:
                tempfile.mkstemp, os.fchmod = original_mkstemp, original_fchmod
            require(injected and len(opened) == (1 if fault == "fchmod" else 0),
                    f"preflight writer {fault} fault injection not reached")
            for descriptor in opened:
                try:
                    os.fstat(descriptor)
                except OSError:
                    pass
                else:
                    raise Fail(f"preflight writer {fault} leaked descriptor")
            require(path.read_bytes() == positive and mode(path) == 0o640,
                    f"preflight writer {fault} changed fixture bytes/mode")
            require(not list(path.parent.glob(".candidate.json.*.tmp")),
                    f"preflight writer {fault} left temporary file")
    print("PASS: preflight reconcile mkstemp/fchmod private preopen faults clean FD/temp")



def prove_preflight_private_path_negative_reachability() -> None:
    """Independently reject removal of the real private-path fault injection."""
    source = PREFLIGHT_NEGATIVE.read_text(encoding="utf-8")

    def verify(candidate: str) -> None:
        try:
            tree = ast.parse(candidate)
        except SyntaxError:
            raise Fail("preflight private path negative syntax invalid") from None
        functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
        target = functions.get("prove_private_preflight_path_errors")
        main = functions.get("main")
        require(target is not None and main is not None,
                "preflight private path negative function/main missing")
        calls = [node for node in ast.walk(main) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == "prove_private_preflight_path_errors"]
        require(len(calls) == 1, "preflight private path negative not executed exactly once")
        body = ast.get_source_segment(candidate, target)
        require(isinstance(body, str), "preflight private path negative body unavailable")
        for token in ['SYNTHETIC_PRIVATE_PREFLIGHT_PATH_CANARY','validator.repo_relative','validator.require_exact_executable','Path.resolve = private_resolve','Path.is_file = private_is_file','exc.__suppress_context__']:
            require(token in body, "preflight private path negative guard removed")

        import_target = functions.get("prove_private_preflight_import_errors")
        require(import_target is not None, "preflight private import negative missing")
        import_calls = [node for node in ast.walk(main) if isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name) and node.func.id == "prove_private_preflight_import_errors"]
        require(len(import_calls) == 1, "preflight private import negative not executed exactly once")
        import_body = ast.get_source_segment(candidate, import_target)
        require(isinstance(import_body, str), "preflight private import negative body unavailable")
        for token in ("SYNTHETIC_PRIVATE_PREFLIGHT_IMPORT_CANARY", "importlib.util.module_from_spec = private_import",
                      "exc.__suppress_context__", "preflight eligibility helper import unavailable"):
            require(token in import_body, "preflight private import negative guard removed")

        pinned_target = functions.get("prove_pinned_preflight_helper_import")
        require(pinned_target is not None, "preflight pinned helper race negative missing")
        pinned_calls = [node for node in ast.walk(main) if isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id == "prove_pinned_preflight_helper_import"]
        require(len(pinned_calls) == 1, "preflight pinned helper race negative not executed exactly once")
        pinned_body = ast.get_source_segment(candidate, pinned_target)
        require(isinstance(pinned_body, str), "preflight pinned helper race body unavailable")
        for token in ("validator.load_eligibility_helper()", "parent.rename(parked)",
                      "parent.symlink_to(redirected", "importlib.util.spec_from_file_location = swap_after_read",
                      "loaded.derive_registry({}) == {\"origin\": \"pinned\"}",
                      "PRIVATE_HELPER_SWAP_CANARY", 'require(canary.read_text(encoding="utf-8") ==',
                      "validator.ELIGIBILITY_HELPER = original_path"):
            require(token in pinned_body, "preflight pinned helper race guard removed")

        unsafe_target = functions.get("prove_preflight_pinned_helper_fail_closed")
        require(unsafe_target is not None, "preflight pinned helper unsafe negative missing")
        unsafe_calls = [node for node in ast.walk(main) if isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id == "prove_preflight_pinned_helper_fail_closed"]
        require(len(unsafe_calls) == 1, "preflight pinned helper unsafe negative not executed exactly once")
        unsafe_body = ast.get_source_segment(candidate, unsafe_target)
        require(isinstance(unsafe_body, str), "preflight pinned helper unsafe body unavailable")
        for token in ("oversized.write_bytes", "for invalid in (None, 0):",
                      "exc.__suppress_context__", "validator.ELIGIBILITY_HELPER = original_path",
                      "validator.load_eligibility_helper().derive_registry({})"):
            require(token in unsafe_body, "preflight pinned helper unsafe guard removed")

        fd_target = functions.get("prove_preflight_pinned_helper_fd_cleanup")
        require(fd_target is not None, "preflight pinned helper FD negative missing")
        fd_calls = [node for node in ast.walk(main) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "prove_preflight_pinned_helper_fd_cleanup"]
        require(len(fd_calls) == 1, "preflight pinned helper FD negative not executed exactly once")
        fd_body = ast.get_source_segment(candidate, fd_target)
        require(isinstance(fd_body, str), "preflight pinned helper FD body unavailable")
        for token in ("os.fdopen = broken_fdopen", "os.close = broken_close",
                      "exc.__suppress_context__", "errno.EBADF",
                      "os.open, os.fdopen, os.close = original_open, original_fdopen, original_close",
                      "validator.ELIGIBILITY_HELPER = original_path"):
            require(token in fd_body, "preflight pinned helper FD negative guard removed")

        semantic_target = functions.get("prove_private_semantic_helper_domain_failure")
        require(semantic_target is not None, "preflight semantic helper private negative missing")
        semantic_calls = [node for node in ast.walk(main) if isinstance(node, ast.Call)
                          and isinstance(node.func, ast.Name)
                          and node.func.id == "prove_private_semantic_helper_domain_failure"]
        require(len(semantic_calls) == 1, "preflight semantic helper private negative not executed")
        semantic_body = ast.get_source_segment(candidate, semantic_target)
        require(isinstance(semantic_body, str), "preflight semantic helper private negative body unavailable")
        for token in ("SYNTHETIC_PRIVATE_SEMANTIC_HELPER_CANARY",
                      "raise SyntheticHelper.Fail(private)", "exc.__suppress_context__",
                      "shared generation semantic derivation failed"):
            require(token in semantic_body, "preflight semantic helper private negative guard removed")

    verify(source)
    for label, scope, old, replacement in (
        ("invocation", "main", "    prove_private_preflight_path_errors(validator)\n", "    pass\n"),
        ("fault injection", "prove_private_preflight_path_errors", "        Path.resolve = private_resolve\n", "        pass\n"),
        ("context assertion", "prove_private_preflight_path_errors", "exc.__suppress_context__", "False"),
        ("stat fault injection", "prove_private_preflight_path_errors", "        Path.is_file = private_is_file\n", "        pass\n"),
        ("import invocation", "main", "    prove_private_preflight_import_errors(validator)\n", "    pass\n"),
        ("import fault injection", "prove_private_preflight_import_errors", "            importlib.util.module_from_spec = private_import\n", "            pass\n"),
        ("import context assertion", "prove_private_preflight_import_errors", "exc.__suppress_context__", "False"),
        ("pinned helper invocation", "main", "    prove_pinned_preflight_helper_import(validator)\n", "    pass\n"),
        ("pinned helper swap", "prove_pinned_preflight_helper_import",
         "            importlib.util.spec_from_file_location = swap_after_read\n", "            pass\n"),
        ("pinned helper parent replacement", "prove_pinned_preflight_helper_import",
         "                    parent.symlink_to(redirected, target_is_directory=True)\n", "                    pass\n"),
        ("pinned helper source assertion", "prove_pinned_preflight_helper_import",
         'loaded.derive_registry({}) == {"origin": "pinned"}', "False"),
        ("pinned helper canary", "prove_pinned_preflight_helper_import",
         '            require(canary.read_text(encoding="utf-8") ==\n',
         '            require(False and\n'),
        ("pinned unsafe invocation", "main",
         "    prove_preflight_pinned_helper_fail_closed(validator)\n", "    pass\n"),
        ("pinned unsafe size", "prove_preflight_pinned_helper_fail_closed",
         '        oversized.write_bytes(b"x" * (validator.MAX_JSON_BYTES + 1))\n', "        pass\n"),
        ("pinned unsafe flags", "prove_preflight_pinned_helper_fail_closed",
         "                    for invalid in (None, 0):\n", "                    for invalid in ():\n"),
        ("pinned unsafe context", "prove_preflight_pinned_helper_fail_closed",
         "exc.__suppress_context__", "False"),
        ("pinned unsafe restore", "prove_preflight_pinned_helper_fail_closed",
         "            validator.ELIGIBILITY_HELPER = original_path\n", "            pass\n"),
        ("pinned FD invocation", "main",
         "    prove_preflight_pinned_helper_fd_cleanup(validator)\n", "    pass\n"),
        ("pinned FD fdopen fault", "prove_preflight_pinned_helper_fd_cleanup",
         "                        os.fdopen = broken_fdopen\n", "                        pass\n"),
        ("pinned FD close fault", "prove_preflight_pinned_helper_fd_cleanup",
         "                        os.close = broken_close\n", "                        pass\n"),
        ("pinned FD leak check", "prove_preflight_pinned_helper_fd_cleanup",
         "errno.EBADF", "None"),
        ("pinned FD context", "prove_preflight_pinned_helper_fd_cleanup",
         "exc.__suppress_context__", "False"),
        ("semantic invocation", "main", "    prove_private_semantic_helper_domain_failure(validator)\n", "    pass\n"),
        ("semantic failure injection", "prove_private_semantic_helper_domain_failure", "            raise SyntheticHelper.Fail(private)\n", "            return {}\n"),
        ("semantic context assertion", "prove_private_semantic_helper_domain_failure", "exc.__suppress_context__", "False"),
    ):
        # A source-wide anchor can repeat in unrelated tests; mutate only the named AST function.
        parsed = ast.parse(source)
        functions = {node.name: node for node in parsed.body if isinstance(node, ast.FunctionDef)}
        function = functions.get(scope)
        require(function is not None, "preflight private path mutation scope missing")
        lines = source.splitlines(keepends=True)
        span = "".join(lines[function.lineno - 1:function.end_lineno])
        require(span.count(old) == 1, "preflight private path scoped deletion anchor drift: " + label)
        lines[function.lineno - 1:function.end_lineno] = [span.replace(old, replacement, 1)]
        try:
            verify("".join(lines))
        except Fail:
            continue
        raise Fail("preflight private path negative deletion accepted: " + label)
    validator_source = VALIDATOR.read_text(encoding="utf-8")

    def verify_pinned_loader(candidate: str) -> None:
        try:
            tree = ast.parse(candidate)
        except SyntaxError:
            raise Fail("preflight pinned loader source syntax invalid") from None
        helpers = [node for node in tree.body
                   if isinstance(node, ast.FunctionDef) and node.name == "load_eligibility_helper"]
        require(len(helpers) == 1, "preflight pinned loader function missing")
        helper = helpers[0]
        body = ast.get_source_segment(candidate, helper)
        require(isinstance(body, str), "preflight pinned loader source unavailable")
        for token in ("class PinnedSourceLoader(importlib.machinery.SourceFileLoader):",
                      'return compile(source, str(ELIGIBILITY_HELPER), "exec")',
                      "loader=PinnedSourceLoader(name, str(ELIGIBILITY_HELPER))",
                      "spec.loader.exec_module(module)",
                      "source = stream.read(MAX_JSON_BYTES + 1)",
                      "os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)"):
            require(token in body, "preflight pinned loader source binding removed")
        require(not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id in {"exec", "eval"} for node in ast.walk(helper)),
                "preflight pinned loader direct dynamic execution refused")

    verify_pinned_loader(validator_source)
    for label, old, replacement in (
        ("loader binding", "loader=PinnedSourceLoader(name, str(ELIGIBILITY_HELPER))", "loader=None"),
        ("pinned source code", 'return compile(source, str(ELIGIBILITY_HELPER), "exec")', "return None"),
        ("stdlib module execution", "spec.loader.exec_module(module)", "pass"),
        ("descriptor-relative leaf", "os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)",
         "os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)"),
    ):
        parsed = ast.parse(validator_source)
        helpers = [node for node in parsed.body
                   if isinstance(node, ast.FunctionDef) and node.name == "load_eligibility_helper"]
        require(len(helpers) == 1, "preflight pinned loader mutation scope missing")
        lines = validator_source.splitlines(keepends=True)
        helper = helpers[0]
        span = "".join(lines[helper.lineno - 1:helper.end_lineno])
        require(span.count(old) == 1,
                "preflight pinned loader scoped mutation anchor drift: " + label)
        lines[helper.lineno - 1:helper.end_lineno] = [span.replace(old, replacement, 1)]
        try:
            verify_pinned_loader("".join(lines))
        except Fail:
            continue
        raise Fail("preflight pinned loader source weakening accepted: " + label)
    authority_source = PREFLIGHT_AUTHORITY.read_text(encoding="utf-8")

    def verify_authority_loader(candidate: str) -> None:
        try:
            tree = ast.parse(candidate)
        except SyntaxError:
            raise Fail("preflight authority pinned loader syntax invalid") from None
        functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
        loader = functions.get("load_module")
        proof = functions.get("prove_pinned_authority_import")
        main = functions.get("main")
        require(loader is not None and proof is not None and main is not None,
                "preflight authority pinned loader/proof/main missing")
        first = main.body[0] if main.body else None
        require(isinstance(first, ast.Expr) and isinstance(first.value, ast.Call)
                and isinstance(first.value.func, ast.Name)
                and first.value.func.id == "prove_pinned_authority_import",
                "preflight authority pinned proof must precede canonical validation")
        second = main.body[1] if len(main.body) > 1 else None
        require(isinstance(second, ast.Expr) and isinstance(second.value, ast.Call)
                and isinstance(second.value.func, ast.Name)
                and second.value.func.id == "prove_private_authority_path_errors",
                "preflight authority private path proof must precede canonical validation")
        path_proof = functions.get("prove_private_authority_path_errors")
        canonical_path = functions.get("canonical_repo_file")
        require(path_proof is not None and canonical_path is not None,
                "preflight authority private path proof or canonical guard missing")
        path_body = ast.get_source_segment(candidate, path_proof)
        canonical_body = ast.get_source_segment(candidate, canonical_path)
        require(isinstance(path_body, str) and isinstance(canonical_body, str),
                "preflight authority private path source unavailable")
        for token in ("Path.resolve = fault_resolve", "Path.is_file = fault_is_file",
                      "exc.__suppress_context__", "private not in str(exc)",
                      "Path.resolve, Path.is_file = original_resolve, original_is_file"):
            require(token in path_body, "preflight authority private path proof removed")
        require('raise Fail(f"{field} missing or escapes repository") from None' in canonical_body
                and "safe = lexical == resolved and path.is_file() and not path.is_symlink()" in canonical_body,
                "preflight authority private canonical path guard removed")
        third = main.body[2] if len(main.body) > 2 else None
        require(isinstance(third, ast.Expr) and isinstance(third.value, ast.Call)
                and isinstance(third.value.func, ast.Name)
                and third.value.func.id == "prove_pinned_authority_fd_cleanup",
                "preflight authority FD proof must precede canonical validation")
        fd_proof = functions.get("prove_pinned_authority_fd_cleanup")
        require(fd_proof is not None, "preflight authority pinned FD proof missing")
        fd_body = ast.get_source_segment(candidate, fd_proof)
        require(isinstance(fd_body, str), "preflight authority pinned FD source unavailable")
        for token in ("os.fdopen = broken_fdopen", "os.close = broken_close",
                      "exc.__suppress_context__", "errno.EBADF",
                      "os.open, os.fdopen, os.close = original_open, original_fdopen, original_close",
                      'load_module(source, "preflight_authority_fd_restored"'):
            require(token in fd_body, "preflight authority pinned FD proof removed")
        fourth = main.body[3] if len(main.body) > 3 else None
        require(isinstance(fourth, ast.Expr) and isinstance(fourth.value, ast.Call)
                and isinstance(fourth.value.func, ast.Name)
                and fourth.value.func.id == "prove_pinned_authority_unsafe_sources",
                "preflight authority unsafe proof must precede canonical validation")
        unsafe_proof = functions.get("prove_pinned_authority_unsafe_sources")
        require(unsafe_proof is not None, "preflight authority unsafe source proof missing")
        unsafe_body = ast.get_source_segment(candidate, unsafe_proof)
        require(isinstance(unsafe_body, str), "preflight authority unsafe source proof unavailable")
        for token in ("oversized.write_bytes", "link.symlink_to(good)", "os.mkfifo(fifo)",
                      "for invalid in (None, 0):", "exc.__suppress_context__",
                      'load_module(good, "preflight_authority_unsafe_restored"'):
            require(token in unsafe_body, "preflight authority unsafe source proof removed")
        loader_body = ast.get_source_segment(candidate, loader)
        proof_body = ast.get_source_segment(candidate, proof)
        require(isinstance(loader_body, str) and isinstance(proof_body, str),
                "preflight authority pinned loader source unavailable")
        for token in ("class PinnedSourceLoader(importlib.machinery.SourceFileLoader):",
                      'return compile(source, str(path), "exec")',
                      "loader=PinnedSourceLoader(name, str(path))",
                      "spec.loader.exec_module(module)",
                      "source = stream.read(MAX_MODULE_BYTES + 1)",
                      "os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)"):
            require(token in loader_body, "preflight authority pinned source binding removed")
        for token in ("parent.rename(parked)", "parent.symlink_to(redirected",
                      "importlib.util.spec_from_file_location = swap_after_read",
                      'loaded.VALUE == "pinned"', 'require(canary.read_text(encoding="utf-8") ==',
                      "importlib.util.spec_from_file_location = original_spec"):
            require(token in proof_body, "preflight authority pinned race proof removed")
        require(not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id in {"exec", "eval"} for node in ast.walk(loader)),
                "preflight authority direct dynamic execution refused")

    verify_authority_loader(authority_source)
    for label, scope, old, replacement in (
        ("proof invocation", "main", "    prove_pinned_authority_import()\n", "    pass\n"),
        ("source loader", "load_module", "loader=PinnedSourceLoader(name, str(path))", "loader=None"),
        ("pinned code", "load_module", 'return compile(source, str(path), "exec")', "return None"),
        ("parent substitution", "prove_pinned_authority_import",
         "                parent.symlink_to(redirected, target_is_directory=True)\n",
         "                pass\n"),
        ("pinned value assertion", "prove_pinned_authority_import",
         'loaded.VALUE == "pinned"', "False"),
        ("private path invocation", "main",
         "    prove_private_authority_path_errors()\n", "    pass\n"),
        ("private resolve fault", "prove_private_authority_path_errors",
         "                Path.resolve = fault_resolve\n", "                pass\n"),
        ("private stat fault", "prove_private_authority_path_errors",
         "                Path.is_file = fault_is_file\n", "                pass\n"),
        ("private context", "prove_private_authority_path_errors",
         "exc.__suppress_context__", "False"),
        ("private canonical suppression", "canonical_repo_file",
         'raise Fail(f"{field} missing or escapes repository") from None',
         'raise Fail(f"{field} missing or escapes repository") from exc'),
        ("FD proof invocation", "main",
         "    prove_pinned_authority_fd_cleanup()\n", "    pass\n"),
        ("FD proof fdopen fault", "prove_pinned_authority_fd_cleanup",
         "                    os.fdopen = broken_fdopen\n", "                    pass\n"),
        ("FD proof close fault", "prove_pinned_authority_fd_cleanup",
         "                    os.close = broken_close\n", "                    pass\n"),
        ("FD proof leak check", "prove_pinned_authority_fd_cleanup",
         "errno.EBADF", "None"),
        ("FD proof context", "prove_pinned_authority_fd_cleanup",
         "exc.__suppress_context__", "False"),
        ("unsafe proof invocation", "main",
         "    prove_pinned_authority_unsafe_sources()\n", "    pass\n"),
        ("unsafe source size", "prove_pinned_authority_unsafe_sources",
         '        oversized.write_bytes(b"x" * (MAX_MODULE_BYTES + 1))\n', "        pass\n"),
        ("unsafe source symlink", "prove_pinned_authority_unsafe_sources",
         "        link.symlink_to(good)\n", "        pass\n"),
        ("unsafe source fifo", "prove_pinned_authority_unsafe_sources",
         "        os.mkfifo(fifo)\n", "        pass\n"),
        ("unsafe source flags", "prove_pinned_authority_unsafe_sources",
         "                for invalid in (None, 0):\n", "                for invalid in ():\n"),
        ("unsafe source context", "prove_pinned_authority_unsafe_sources",
         "exc.__suppress_context__", "False"),
    ):
        parsed = ast.parse(authority_source)
        functions = {node.name: node for node in parsed.body if isinstance(node, ast.FunctionDef)}
        function = functions.get(scope)
        require(function is not None, "preflight authority pinned mutation scope missing")
        lines = authority_source.splitlines(keepends=True)
        span = "".join(lines[function.lineno - 1:function.end_lineno])
        require(span.count(old) == 1, "preflight authority pinned mutation anchor drift: " + label)
        lines[function.lineno - 1:function.end_lineno] = [span.replace(old, replacement, 1)]
        try:
            verify_authority_loader("".join(lines))
        except Fail:
            continue
        raise Fail("preflight authority pinned loader weakening accepted: " + label)
    reconcile_negative_source = PREFLIGHT_RECONCILE_NEGATIVE.read_text(encoding="utf-8")

    def verify_reconcile_negative_loader(candidate: str) -> None:
        try:
            tree = ast.parse(candidate)
        except SyntaxError:
            raise Fail("preflight reconcile negative pinned import syntax invalid") from None
        functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
        loader = functions.get("load_module")
        proof = functions.get("prove_pinned_reconciler_import")
        main = functions.get("main")
        require(loader is not None and proof is not None and main is not None,
                "preflight reconcile negative pinned loader/proof/main missing")
        first = main.body[0] if main.body else None
        require(isinstance(first, ast.Expr) and isinstance(first.value, ast.Call)
                and isinstance(first.value.func, ast.Name)
                and first.value.func.id == "prove_pinned_reconciler_import",
                "preflight reconcile negative pinned proof not executed before canonical work")
        loader_body = ast.get_source_segment(candidate, loader)
        proof_body = ast.get_source_segment(candidate, proof)
        require(isinstance(loader_body, str) and isinstance(proof_body, str),
                "preflight reconcile negative pinned source unavailable")
        for token in ("class PinnedSourceLoader(importlib.machinery.SourceFileLoader):",
                      'return compile(source, str(RECONCILER), "exec")',
                      "loader=PinnedSourceLoader(name, str(RECONCILER))",
                      "spec.loader.exec_module(module)",
                      "source = stream.read(MAX_MODULE_BYTES + 1)",
                      "os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)"):
            require(token in loader_body, "preflight reconcile negative pinned loader weakened")
        for token in ("parent.rename(parked)", "parent.symlink_to(redirected",
                      "importlib.util.spec_from_file_location = swap_after_read",
                      'loaded.VALUE == "pinned"', 'require(canary.read_text(encoding="utf-8") ==',
                      "RECONCILER = original_path"):
            require(token in proof_body, "preflight reconcile negative pinned proof removed")
        require(not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id in {"exec", "eval"} for node in ast.walk(loader)),
                "preflight reconcile negative direct dynamic execution refused")

    verify_reconcile_negative_loader(reconcile_negative_source)
    for label, scope, old, replacement in (
        ("proof invocation", "main", "    prove_pinned_reconciler_import()\n", "    pass\n"),
        ("source loader", "load_module", "loader=PinnedSourceLoader(name, str(RECONCILER))", "loader=None"),
        ("pinned code", "load_module", 'return compile(source, str(RECONCILER), "exec")', "return None"),
        ("parent substitution", "prove_pinned_reconciler_import",
         "                    parent.symlink_to(redirected, target_is_directory=True)\n",
         "                    pass\n"),
        ("pinned value assertion", "prove_pinned_reconciler_import",
         'loaded.VALUE == "pinned"', "False"),
    ):
        parsed = ast.parse(reconcile_negative_source)
        functions = {node.name: node for node in parsed.body if isinstance(node, ast.FunctionDef)}
        function = functions.get(scope)
        require(function is not None, "preflight reconcile negative mutation scope missing")
        lines = reconcile_negative_source.splitlines(keepends=True)
        span = "".join(lines[function.lineno - 1:function.end_lineno])
        require(span.count(old) == 1,
                "preflight reconcile negative scoped mutation anchor drift: " + label)
        lines[function.lineno - 1:function.end_lineno] = [span.replace(old, replacement, 1)]
        try:
            verify_reconcile_negative_loader("".join(lines))
        except Fail:
            continue
        raise Fail("preflight reconcile negative pinned loader weakening accepted: " + label)
    drill_source = DRILL_REQUEST_LOAD_NEGATIVE.read_text(encoding="utf-8")

    def verify_drill_pinned_loader(candidate: str) -> None:
        try:
            parsed = ast.parse(candidate)
        except SyntaxError:
            raise Fail("drill request pinned loader source syntax invalid") from None
        functions = {node.name: node for node in parsed.body if isinstance(node, ast.FunctionDef)}
        loader = functions.get("load_module")
        proof = functions.get("prove_pinned_module_import")
        main = functions.get("main")
        require(loader is not None and proof is not None and main is not None,
                "drill request pinned loader/proof/main missing")
        main_body = ast.get_source_segment(candidate, main)
        loader_body = ast.get_source_segment(candidate, loader)
        proof_body = ast.get_source_segment(candidate, proof)
        require(all(isinstance(body, str) for body in (main_body, loader_body, proof_body)),
                "drill request pinned loader source unavailable")
        require(main_body.count("prove_pinned_module_import()") == 1
                and main_body.index("prove_pinned_module_import()") <
                    main_body.index("writer = load_module(WRITER"),
                "drill request pinned proof must run before canonical imports")
        for token in ("class PinnedSourceLoader(importlib.machinery.SourceFileLoader):",
                      'return compile(source, str(path), "exec")',
                      "loader=PinnedSourceLoader(name, str(path))",
                      "spec.loader.exec_module(module)",
                      "source = stream.read(MAX_MODULE_BYTES + 1)",
                      "os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)",
                      'for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY")',
                      'raise Fail("cannot load drill request authority") from None'):
            require(token in loader_body, "drill request pinned source binding removed")
        for token in ("parent.rename(parked)", "parent.symlink_to(redirected",
                      "importlib.util.spec_from_file_location = swap_after_read",
                      'loaded.VALUE == "pinned"', 'require(canary.read_text(encoding="utf-8") ==',
                      "importlib.util.spec_from_file_location = original_spec"):
            require(token in proof_body, "drill request pinned race proof removed")
        unsafe = functions.get("prove_pinned_module_unsafe_sources")
        require(unsafe is not None, "drill request unsafe pinned proof missing")
        unsafe_body = ast.get_source_segment(candidate, unsafe)
        require(isinstance(unsafe_body, str), "drill request unsafe pinned proof unavailable")
        require(main_body.count("prove_pinned_module_unsafe_sources()") == 1
                and main_body.index("prove_pinned_module_unsafe_sources()") <
                    main_body.index("writer = load_module(WRITER"),
                "drill request unsafe pinned proof must run before canonical imports")
        for token in ("oversized.write_bytes", "link.symlink_to(good)",
                      "os.mkfifo(fifo)", "for invalid in (None, 0):",
                      "exc.__suppress_context__",
                      'load_module(good, "drill_import_unsafe_restored")'):
            require(token in unsafe_body, "drill request unsafe pinned proof removed")
        fd_proof = functions.get("prove_pinned_module_fd_cleanup")
        require(fd_proof is not None, "drill request pinned FD proof missing")
        fd_body = ast.get_source_segment(candidate, fd_proof)
        require(isinstance(fd_body, str), "drill request pinned FD proof unavailable")
        require(main_body.count("prove_pinned_module_fd_cleanup()") == 1
                and main_body.index("prove_pinned_module_fd_cleanup()") <
                    main_body.index("writer = load_module(WRITER"),
                "drill request pinned FD proof must run before canonical imports")
        for token in ('raise OSError(errno.EIO, "PRIVATE_DRILL_FDOPEN_CANARY")',
                      'raise OSError(errno.EIO, "PRIVATE_DRILL_CLOSE_CANARY")',
                      "os.open, os.fdopen, os.close = tracked_open, broken_fdopen, broken_close",
                      "os.open, os.fdopen, os.close = original_open, original_fdopen, original_close",
                      "exc.__suppress_context__", "errno.EBADF",
                      'load_module(VALIDATOR, "drill_import_fd_restored")'):
            require(token in fd_body, "drill request pinned FD proof removed")
        require(not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id in {"exec", "eval"} for node in ast.walk(loader)),
                "drill request direct dynamic execution refused")

    verify_drill_pinned_loader(drill_source)
    for label, scope, old, replacement in (
        ("proof invocation", "main", "    prove_pinned_module_import()\n", "    pass\n"),
        ("source loader", "load_module", "loader=PinnedSourceLoader(name, str(path))", "loader=None"),
        ("pinned code", "load_module", 'return compile(source, str(path), "exec")', "return None"),
        ("stdlib execution", "load_module", "spec.loader.exec_module(module)", "pass"),
        ("descriptor leaf", "load_module",
         "os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)",
         "os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)"),
        ("bounded read", "load_module", "source = stream.read(MAX_MODULE_BYTES + 1)",
         "source = stream.read()"),
        ("platform flags", "load_module",
         'for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY")',
         'for flag in ()'),
        ("private suppression", "load_module",
         'raise Fail("cannot load drill request authority") from None',
         'raise Fail("cannot load drill request authority") from exc'),
        ("parent substitution", "prove_pinned_module_import",
         "parent.symlink_to(redirected, target_is_directory=True)", "pass"),
        ("pinned value", "prove_pinned_module_import", 'loaded.VALUE == "pinned"', "False"),
        ("canary", "prove_pinned_module_import",
         'require(canary.read_text(encoding="utf-8") ==',
         'require(False and'),
        ("unsafe invocation", "main", "    prove_pinned_module_unsafe_sources()\n", "    pass\n"),
        ("unsafe size", "prove_pinned_module_unsafe_sources",
         'oversized.write_bytes(b"x" * (MAX_MODULE_BYTES + 1))', "pass"),
        ("unsafe symlink", "prove_pinned_module_unsafe_sources", "link.symlink_to(good)", "pass"),
        ("unsafe FIFO", "prove_pinned_module_unsafe_sources", "os.mkfifo(fifo)", "pass"),
        ("unsafe flags", "prove_pinned_module_unsafe_sources",
         "for invalid in (None, 0):", "for invalid in ():"),
        ("unsafe context", "prove_pinned_module_unsafe_sources", "exc.__suppress_context__", "False"),
        ("unsafe positive", "prove_pinned_module_unsafe_sources",
         'load_module(good, "drill_import_unsafe_restored")',
         'load_module(good, "drill_import_unsafe")'),
        ("FD invocation", "main", "    prove_pinned_module_fd_cleanup()\n", "    pass\n"),
        ("FD fdopen fault", "prove_pinned_module_fd_cleanup",
         'raise OSError(errno.EIO, "PRIVATE_DRILL_FDOPEN_CANARY")', "pass"),
        ("FD close fault", "prove_pinned_module_fd_cleanup",
         'raise OSError(errno.EIO, "PRIVATE_DRILL_CLOSE_CANARY")', "pass"),
        ("FD EBADF", "prove_pinned_module_fd_cleanup", "errno.EBADF", "None"),
        ("FD context", "prove_pinned_module_fd_cleanup", "exc.__suppress_context__", "False"),
        ("FD restore patch", "prove_pinned_module_fd_cleanup",
         "os.open, os.fdopen, os.close = original_open, original_fdopen, original_close",
         "pass"),
        ("FD positive", "prove_pinned_module_fd_cleanup",
         'load_module(VALIDATOR, "drill_import_fd_restored")',
         'load_module(VALIDATOR, "drill_import_fd_fault")'),
    ):
        parsed = ast.parse(drill_source)
        functions = {node.name: node for node in parsed.body if isinstance(node, ast.FunctionDef)}
        function = functions.get(scope)
        require(function is not None, "drill request pinned mutation scope missing")
        lines = drill_source.splitlines(keepends=True)
        span = "".join(lines[function.lineno - 1:function.end_lineno])
        require(span.count(old) == 1,
                "drill request pinned scoped mutation anchor drift: " + label)
        lines[function.lineno - 1:function.end_lineno] = [span.replace(old, replacement, 1)]
        try:
            verify_drill_pinned_loader("".join(lines))
        except Fail:
            continue
        raise Fail("drill request pinned loader weakening accepted: " + label)
    reconcile_source = DRILL_REQUEST_RECONCILE_NEGATIVE.read_text(encoding="utf-8")

    def verify_drill_reconcile_loader(candidate: str) -> None:
        try:
            parsed = ast.parse(candidate)
        except SyntaxError:
            raise Fail("drill reconcile pinned loader source syntax invalid") from None
        functions = {node.name: node for node in parsed.body if isinstance(node, ast.FunctionDef)}
        loader = functions.get("load_reconciler")
        proof = functions.get("prove_reconciler_pinned_import")
        main = functions.get("main")
        require(loader is not None and proof is not None and main is not None,
                "drill reconcile pinned loader/proof/main missing")
        loader_body = ast.get_source_segment(candidate, loader)
        proof_body = ast.get_source_segment(candidate, proof)
        main_body = ast.get_source_segment(candidate, main)
        require(all(isinstance(body, str) for body in (loader_body, proof_body, main_body)),
                "drill reconcile pinned source unavailable")
        require(main_body.count("prove_reconciler_pinned_import()") == 1
                and main_body.index("prove_reconciler_pinned_import()") <
                    main_body.index("reconciler = load_reconciler()"),
                "drill reconcile pinned proof not run before canonical import")
        for token in ("load_pinned_fixture_guard(", "helper.load_module(",
                      'raise Fail("cannot load drill request reconciler") from None'):
            require(token in loader_body, "drill reconcile pinned loader binding removed")
        for token in ("parent.rename(parked)", "parent.symlink_to(redirected",
                      "importlib.util.spec_from_file_location = swap_after_read",
                      'loaded.VALUE == "pinned"', 'require(canary.read_text(encoding="utf-8") ==',
                      "importlib.util.spec_from_file_location = original_spec",
                      'getattr(load_reconciler(), "main", None)'):
            require(token in proof_body, "drill reconcile pinned race proof removed")

    verify_drill_reconcile_loader(reconcile_source)
    for label, scope, old, replacement in (
        ("proof invocation", "main", "    prove_reconciler_pinned_import()\n", "    pass\n"),
        ("shared pinned loader", "load_reconciler", "helper.load_module(", "helper.load_unpinned("),
        ("pinned helper", "load_reconciler", "load_pinned_fixture_guard(", "load_module("),
        ("private suppression", "load_reconciler",
         'raise Fail("cannot load drill request reconciler") from None',
         'raise Fail("cannot load drill request reconciler") from exc'),
        ("parent substitution", "prove_reconciler_pinned_import",
         "parent.symlink_to(redirected, target_is_directory=True)", "pass"),
        ("pinned value", "prove_reconciler_pinned_import", 'loaded.VALUE == "pinned"', "False"),
        ("canary", "prove_reconciler_pinned_import",
         'require(canary.read_text(encoding="utf-8") ==', 'require(False and'),
        ("canonical restoration", "prove_reconciler_pinned_import",
         'getattr(load_reconciler(), "main", None)', 'getattr(load_reconciler(), "missing", None)'),
    ):
        parsed = ast.parse(reconcile_source)
        functions = {node.name: node for node in parsed.body if isinstance(node, ast.FunctionDef)}
        function = functions.get(scope)
        require(function is not None, "drill reconcile pinned mutation scope missing")
        lines = reconcile_source.splitlines(keepends=True)
        span = "".join(lines[function.lineno - 1:function.end_lineno])
        require(span.count(old) == 1,
                "drill reconcile pinned scoped mutation anchor drift: " + label)
        lines[function.lineno - 1:function.end_lineno] = [span.replace(old, replacement, 1)]
        try:
            verify_drill_reconcile_loader("".join(lines))
        except Fail:
            continue
        raise Fail("drill reconcile pinned source weakening accepted: " + label)
    print("PASS: drill reconcile pinned loader and eight source mutations rejected")
    print("PASS: drill request pinned loader and twenty-five source mutations rejected")
    print("PASS: preflight reconcile negative pinned loader and five source mutations rejected")
    print("PASS: preflight authority pinned loader/private path/FD/unsafe source and 21 mutations rejected")
    print("PASS: preflight pinned source loader and four weakening mutations rejected")
    print("PASS: preflight private path/import fault, context and invocation deletion rejected")


def main() -> int:
    require(VALIDATOR.is_file(), "preflight validator missing")
    require(RECONCILER.is_file(), "preflight reconciler missing")
    require(CANONICAL_CONTRACT.is_file(), "preflight contract missing")
    require(CANONICAL_STATUS.is_file(), "production status missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    prove_helper_source_symlink_rejected()
    prove_helper_source_swap_during_import_is_pinned()
    prove_helper_parent_swap_after_pin_uses_original_source()
    prove_helper_ancestor_swap_during_fd_walk_rejected()
    prove_preflight_private_path_negative_reachability()
    validator = load_module(VALIDATOR, "memory_os_restore_drill_preflight_load_negative")
    reconciler = load_module(RECONCILER, "memory_os_restore_drill_preflight_reconcile_load_negative")
    prove_preflight_reconcile_pinned_reader(reconciler)
    prove_preflight_reconcile_strict_json(reconciler)
    prove_preflight_reconcile_descriptor_faults(reconciler)
    prove_preflight_reconcile_platform_flags(reconciler)

    prove_data_and_executable_authority_rejection(reconciler)
    prove_post_reconcile_output_suppression(reconciler)
    prove_atomic_write_failure(reconciler)
    prove_preflight_reconcile_writer_ownership(reconciler)
    prove_preflight_reconcile_private_path_diagnostics(reconciler)
    prove_preflight_reconcile_repo_refs(reconciler)
    prove_preflight_reconcile_writer_preopen_faults(reconciler)

    with guarded_temporary_directory(".tmp-preflight-load-", TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)

        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_domain_fail("invalid UTF-8 preflight authority JSON", lambda: validator.load(invalid_utf8), validator.Fail)
        expect_domain_fail("invalid UTF-8 preflight reconcile authority JSON", lambda: reconciler.load(invalid_utf8), reconciler.Fail)

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_domain_fail("preflight authority path is unreadable directory", lambda: validator.load(directory_authority), validator.Fail)
        expect_domain_fail("preflight reconcile authority path is unreadable directory", lambda: reconciler.load(directory_authority), reconciler.Fail)

        prove_transactional_rollback(reconciler, tmp)
        prove_rollback_failure_diagnostics(reconciler, tmp)

    escaped = Path("/tmp/memory-os-preflight-reconcile-escaped.json")
    expect_domain_fail("preflight reconcile authority path escapes repository", lambda: reconciler.load(escaped), reconciler.Fail)

    with guarded_temporary_directory(".tmp-preflight-parent-negative-", TMP_PARENT) as raw:
        sandbox = Path(raw)
        link = sandbox / "redirect"
        link.symlink_to(sandbox, target_is_directory=True)
        before = sorted(p.name for p in sandbox.iterdir())
        try:
            with guarded_temporary_directory(".tmp-must-not-create-", link):
                raise Fail("preflight symlinked temp parent accepted")
        except Fail as exc:
            require(str(exc) == "drill request temp ancestor missing or symlinked",
                    f"preflight temp parent rejected at wrong boundary: {exc}")
        else:
            raise Fail("preflight symlinked temp parent accepted")
        require(sorted(p.name for p in sandbox.iterdir()) == before,
                "preflight symlinked temp parent published a child")
    print("PASS: preflight load fixtures reuse checked drill parent guard")

    print("Preflight unreadable-authority and reconcile rollback negative suite PASS")
    print("direct reconciler data/executable authority substitutions accepted: false")
    print("production CLI authority weakened for transactional fixtures: false")
    print("reconciler invalid UTF-8 authority leaked raw exception: false")
    print("reconciler unreadable directory authority leaked raw exception: false")
    print("reconciler escaped authority accepted: false")
    print("upstream append-only authorities validated before derived mutation: true")
    print("preflight/status non-atomic writes accepted: false")
    print("preflight and operability validators execute inside reconcile transaction: true")
    print("failed aggregate post-validation leaves derived authority mutation behind: false")
    print("rollback failure masks primary post-validation diagnostic: false")
    print("earlier rollback failure stops later authority restoration: false")
    print("production evidence created: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PREFLIGHT LOAD NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
