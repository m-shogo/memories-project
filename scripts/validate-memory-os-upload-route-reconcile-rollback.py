#!/usr/bin/env python3
"""Prove upload-route reconcile rollback and canonical validator delegation."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-upload-route-authority.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module():
    spec = importlib.util.spec_from_file_location("memory_os_upload_route_reconciler", RECONCILER)
    require(spec is not None and spec.loader is not None, "unable to load upload-route reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prove_atomic_replace_failure(module) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-atomic-") as temp_dir:
        target = Path(temp_dir) / "authority.txt"
        original = b"exact-original-bytes\n"
        target.write_bytes(original)
        original_replace = module.os.replace
        pattern = f".{target.name}.*.tmp"
        before = {item.name for item in target.parent.glob(pattern)}

        def reject_replace(source, destination) -> None:
            if Path(destination) == target:
                raise OSError("synthetic atomic replace rejection")
            original_replace(source, destination)

        module.os.replace = reject_replace
        try:
            try:
                module.atomic_write_bytes(target, b"partial-mutation\n")
            except OSError as exc:
                require("synthetic atomic replace rejection" in str(exc),
                        "atomic replacement failed for unrelated reason")
            else:
                raise Fail("upload-route atomic writer accepted replacement failure")
            require(target.read_bytes() == original,
                    "upload-route canonical bytes changed after failed atomic replacement")
            after = {item.name for item in target.parent.glob(pattern)}
            require(after == before,
                    f"upload-route atomic writer left temporary residue: {sorted(after - before)}")
        finally:
            module.os.replace = original_replace


def expect_guard_rejection(module, attribute: str, substitute, expected: str) -> None:
    original = getattr(module, attribute)
    setattr(module, attribute, substitute)
    try:
        try:
            module.enforce_execution_authorities()
        except module.ReconcileFailure as exc:
            require(expected in str(exc), f"{attribute} rejected for unrelated reason: {exc}")
        else:
            raise Fail(f"upload-route reconciler accepted execution substitution: {attribute}")
    finally:
        setattr(module, attribute, original)


def prove_execution_authority(module) -> None:
    module.enforce_execution_authorities()
    cases = (
        ("OBSERVABILITY", module.SERVER, "observability source authority drift"),
        ("SERVER", module.OBSERVABILITY, "server source authority drift"),
        ("LIVE_TEST", module.ROUTE_TEST, "live test source authority drift"),
        ("ROUTE_TEST", module.LIVE_TEST, "route test source authority drift"),
        ("METRICS_VALIDATOR", module.RATE_LIMIT_VALIDATOR, "metrics validator authority drift"),
        ("RATE_LIMIT_VALIDATOR", module.METRICS_VALIDATOR, "rate-limit validator authority drift"),
        ("OBSERVABILITY_VALIDATOR", module.OPERABILITY_VALIDATOR, "observability validator authority drift"),
        ("OPERABILITY_VALIDATOR", module.OBSERVABILITY_VALIDATOR, "operability validator authority drift"),
        ("OLD_LABEL", module.NEW_LABEL, "old label semantic authority drift"),
        ("require", lambda *_args, **_kwargs: None, "require execution authority drift"),
        ("read", lambda _path: "", "reader execution authority drift"),
        ("atomic_write_bytes", lambda *_args: None, "atomic byte writer execution authority drift"),
        ("atomic_write_text", lambda *_args: None, "atomic text writer execution authority drift"),
        ("write_if_changed", lambda *_args: False, "conditional writer execution authority drift"),
        ("replace_once", lambda value, *_args: (value, False), "replacement helper execution authority drift"),
        ("current_authority_files", lambda: [], "authority scanner execution authority drift"),
        ("snapshot_authority_files", lambda: None, "snapshot helper execution authority drift"),
        ("rollback_authority_files", lambda: None, "rollback helper execution authority drift"),
        ("validate_canonical_authorities", lambda: None, "validator chain execution authority drift"),
    )
    for attribute, substitute, expected in cases:
        expect_guard_rejection(module, attribute, substitute, expected)

    original_run = module.subprocess.run
    module.subprocess.run = lambda *_args, **_kwargs: None
    try:
        try:
            module.enforce_execution_authorities()
        except module.ReconcileFailure as exc:
            require("subprocess transport execution authority drift" in str(exc),
                    f"subprocess transport rejected for unrelated reason: {exc}")
        else:
            raise Fail("upload-route reconciler accepted subprocess transport substitution")
    finally:
        module.subprocess.run = original_run

    original_guard = module.enforce_execution_authorities
    module.enforce_execution_authorities = lambda: None
    try:
        try:
            module.main()
        except module.ReconcileFailure as exc:
            require("execution guard authority drift" in str(exc),
                    f"runtime guard rejected for unrelated reason: {exc}")
        else:
            raise Fail("upload-route reconciler accepted runtime guard substitution")
    finally:
        module.enforce_execution_authorities = original_guard


def prove_validator_delegation(module) -> None:
    expected = [
        module.METRICS_VALIDATOR,
        module.RATE_LIMIT_VALIDATOR,
        module.OBSERVABILITY_VALIDATOR,
        module.OPERABILITY_VALIDATOR,
    ]
    calls: list[Path] = []

    class Result:
        def __init__(self, returncode):
            self.returncode = returncode

    original_run = module.subprocess.run

    def passing_run(command, *, cwd, check):
        require(cwd == module.ROOT, "validator did not run from repository root")
        require(check is False, "validator subprocess must return its explicit status")
        calls.append(Path(command[1]))
        return Result(0)

    try:
        module.subprocess.run = passing_run
        module.validate_canonical_authorities()
    finally:
        module.subprocess.run = original_run
    require(calls == expected, "canonical aggregate validators ran in the wrong order")

    calls.clear()

    def failing_run(command, *, cwd, check):
        calls.append(Path(command[1]))
        return Result(1 if len(calls) == 2 else 0)

    try:
        module.subprocess.run = failing_run
        try:
            module.validate_canonical_authorities()
        except module.ReconcileFailure as exc:
            require("validate-memory-os-rate-limit.py" in str(exc), "wrong validator failure was reported")
        else:
            raise Fail("canonical validator rejection was accepted")
    finally:
        module.subprocess.run = original_run
    require(calls == expected[:2], "validator chain continued after fail-closed rejection")

    def boolean_run(command, *, cwd, check):
        return Result(False)

    try:
        module.subprocess.run = boolean_run
        try:
            module.validate_canonical_authorities()
        except module.ReconcileFailure:
            pass
        else:
            raise Fail("boolean validator exit status was accepted as integer zero")
    finally:
        module.subprocess.run = original_run


def main() -> int:
    module = load_module()
    prove_atomic_replace_failure(module)

    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-rollback-") as temp_dir:
        root = Path(temp_dir)
        existing = root / "existing.txt"
        created = root / "created.txt"
        original = b"exact-original-bytes\x00\n"
        existing.write_bytes(original)

        module.ROLLBACK_SNAPSHOT = {
            existing: original,
            created: None,
        }

        existing.write_bytes(b"partial-mutation\n")
        created.write_bytes(b"partial-created-file\n")
        module.rollback_authority_files()

        require(existing.read_bytes() == original, "existing authority was not restored byte-for-byte")
        require(not created.exists(), "new partial authority was not removed during rollback")

    prove_validator_delegation(module)
    prove_execution_authority(module)

    print("PASS: upload-route reconcile atomic publication, rollback, execution authority and canonical validator delegation are fail-closed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"UPLOAD ROUTE RECONCILE ROLLBACK NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
