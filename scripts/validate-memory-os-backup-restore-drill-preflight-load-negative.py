#!/usr/bin/env python3
"""Prove restore-drill preflight authority loading and reconcile rollback fail closed."""

from __future__ import annotations

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

    try:
        reconciler.importlib.util.module_from_spec = fail_private_import
        require_private_fail(reconciler.load_validator_module,
                             "preflight reconcile validator import unavailable")
    finally:
        reconciler.importlib.util.module_from_spec = original_module_from_spec
    print("PASS: preflight reconcile private path and validator import errors suppressed")


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
