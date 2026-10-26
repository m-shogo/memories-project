#!/usr/bin/env python3
"""Prove repeatability reconciliation pins authorities and cannot leave partial writes."""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import os
import stat
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-controlled-saturation-repeatability.py"


def load_module():
    spec = importlib.util.spec_from_file_location("repeatability_reconciler", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load repeatability reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_unchanged(protected, before, label: str) -> None:
    for path in protected:
        if path.read_bytes() != before[path]:
            raise RuntimeError(f"partial authority write after {label}: {path.relative_to(ROOT)}")


def temp_residue(path: Path) -> list[Path]:
    return list(path.parent.glob(f".{path.name}.*.tmp"))


def expect_authority_rejection(module, attr: str, replacement: Path) -> None:
    original = getattr(module, attr)
    setattr(module, attr, replacement)
    try:
        try:
            module.enforce_runtime_authorities()
        except module.Fail:
            pass
        else:
            raise RuntimeError(f"{attr} substitution must be rejected")
    finally:
        setattr(module, attr, original)


def run_authority_substitutions(module) -> None:
    substitutions = {
        "CONTRACT": module.LOAD,
        "RESULT": module.CONTRACT,
        "VALIDATOR": module.LOAD_VALIDATOR,
        "LOAD_VALIDATOR": module.VALIDATOR,
        "OPERABILITY_VALIDATOR": module.LOAD_VALIDATOR,
        "LOAD": module.CONTRACT,
        "STATUS": module.LOAD,
        "WORKFLOW": module.VALIDATOR,
    }
    for attr, replacement in substitutions.items():
        expect_authority_rejection(module, attr, replacement)
    module.enforce_runtime_authorities()


def run_prewrite_failure(module) -> None:
    protected = (module.CONTRACT, module.LOAD, module.STATUS)
    before = {path: path.read_bytes() for path in protected}
    original_load = module.load

    def fail_on_status(path: Path):
        if path == module.STATUS:
            raise module.Fail("synthetic status read failure")
        return original_load(path)

    module.load = fail_on_status
    try:
        module.main()
    except module.Fail as exc:
        if str(exc) != "synthetic status read failure":
            raise
    else:
        raise RuntimeError("reconciler unexpectedly succeeded after synthetic status read failure")
    finally:
        module.load = original_load

    assert_unchanged(protected, before, "rejected pre-write reconcile")


def run_postwrite_failure(module) -> None:
    protected = (module.CONTRACT, module.LOAD, module.STATUS)
    before = {path: path.read_bytes() for path in protected}
    contract = module.load(module.CONTRACT)
    load_contract = module.load(module.LOAD)
    status = module.load(module.STATUS)
    contract["_rollbackNegativeMarker"] = True
    load_contract["_rollbackNegativeMarker"] = True
    status["_rollbackNegativeMarker"] = True
    original_validators = module.run_post_write_validators

    def fail_after_write() -> None:
        raise RuntimeError("synthetic post-write repeatability validation failure")

    module.run_post_write_validators = fail_after_write
    try:
        try:
            module.write_transactionally(contract, load_contract, status)
        except RuntimeError as exc:
            if str(exc) != "synthetic post-write repeatability validation failure":
                raise
        else:
            raise RuntimeError("reconciler unexpectedly accepted post-write validation failure")
    finally:
        module.run_post_write_validators = original_validators

    assert_unchanged(protected, before, "post-write validation rollback")


def run_atomic_replace_failure(module) -> None:
    protected = (module.CONTRACT, module.LOAD, module.STATUS)
    before = {path: path.read_bytes() for path in protected}
    residues_before = set(path for authority in protected for path in temp_residue(authority))
    original_replace = module.os.replace
    calls = 0

    def fail_first_replace(src, dst):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("synthetic repeatability atomic replacement failure")
        original_replace(src, dst)

    module.os.replace = fail_first_replace
    try:
        rejected = False
        try:
            module.write_transactionally(
                module.load(module.CONTRACT),
                module.load(module.LOAD),
                module.load(module.STATUS),
            )
        except BaseException as exc:
            rejected = True
            if "synthetic repeatability atomic replacement failure" not in str(exc):
                raise RuntimeError(f"unexpected atomic rejection: {exc}") from exc
        if not rejected:
            raise RuntimeError("repeatability reconciler accepted synthetic atomic replacement failure")
        assert_unchanged(protected, before, "atomic replacement failure")
        residues_after = set(path for authority in protected for path in temp_residue(authority))
        if residues_after != residues_before:
            raise RuntimeError("repeatability atomic failure left temporary authority residue")
    finally:
        module.os.replace = original_replace
        for path, payload in before.items():
            if path.read_bytes() != payload:
                module.atomic_write_bytes(path, payload)



def run_validator_output_negative(module) -> None:
    marker = "SYNTHETIC_REPEATABILITY_SECRET_MARKER"
    original_run = module.subprocess.run

    def noisy_validator(*args, **kwargs):
        if kwargs.get("stdout") != subprocess.DEVNULL or kwargs.get("stderr") != subprocess.DEVNULL:
            raise RuntimeError("validator streams must be suppressed")
        raise subprocess.CalledProcessError(17, args[0], output=marker, stderr=marker)

    module.subprocess.run = noisy_validator
    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                module.run_validator(module.VALIDATOR)
            except module.Fail as exc:
                if marker in str(exc) or not exc.__suppress_context__ or "exit 17" not in str(exc):
                    raise RuntimeError("validator failure disclosed raw output or lost exit code") from None
            else:
                raise RuntimeError("noisy validator unexpectedly accepted")
    finally:
        module.subprocess.run = original_run
    if marker in stdout.getvalue() + stderr.getvalue():
        raise RuntimeError("validator output reached CI streams")


def run_atomic_path_negative(module) -> None:
    with tempfile.TemporaryDirectory(prefix="repeatability-atomic-negative-") as temp:
        root = Path(temp)
        target = root / "authority.json"
        target.write_bytes(b"original")
        target.chmod(0o640)
        module.atomic_write_bytes(target, b"updated")
        if target.read_bytes() != b"updated" or stat.S_IMODE(target.stat().st_mode) != 0o640:
            raise RuntimeError("existing repeatability authority mode or bytes drifted")
        new = root / "new.json"
        module.atomic_write_bytes(new, b"new")
        if new.read_bytes() != b"new" or stat.S_IMODE(new.stat().st_mode) != 0o644:
            raise RuntimeError("new repeatability authority mode drifted")

        outside = root / "outside-canary"
        outside.write_bytes(b"outside")
        link = root / "link.json"
        link.symlink_to(outside)
        directory = root / "directory"
        directory.mkdir()
        linked_parent = root / "linked-parent"
        linked_parent.symlink_to(directory, target_is_directory=True)
        for unsafe in (link, linked_parent / "inside.json", directory, root / "missing" / "inside.json"):
            try:
                module.atomic_write_bytes(unsafe, b"forbidden")
            except module.Fail:
                pass
            else:
                raise RuntimeError(f"unsafe repeatability path accepted: {unsafe.name}")
        if outside.read_bytes() != b"outside" or list(directory.iterdir()):
            raise RuntimeError("unsafe path changed outside canary or linked directory")

        original_replace = module.os.replace
        def fail_replace(*args):
            raise OSError("SYNTHETIC_REPEATABILITY_REPLACE_SECRET")
        module.os.replace = fail_replace
        try:
            try:
                module.atomic_write_bytes(target, b"forbidden")
            except OSError:
                pass
            else:
                raise RuntimeError("atomic replace failure unexpectedly accepted")
        finally:
            module.os.replace = original_replace
        if target.read_bytes() != b"updated" or list(root.glob(".authority.json.*.tmp")):
            raise RuntimeError("atomic replace failure changed authority or left residue")


def run_rollback_secret_negative(module) -> None:
    marker = "SYNTHETIC_REPEATABILITY_ROLLBACK_SECRET"
    original_write = module.write
    original_atomic = module.atomic_write_bytes
    original_validators = module.run_post_write_validators
    module.write = lambda *args: None
    def noisy_rollback(*args):
        raise OSError(marker)
    def noisy_validation():
        raise RuntimeError(marker)
    module.atomic_write_bytes = noisy_rollback
    module.run_post_write_validators = noisy_validation
    try:
        try:
            module.write_transactionally(
                module.load(module.CONTRACT),
                module.load(module.LOAD),
                module.load(module.STATUS),
            )
        except module.Fail as exc:
            if marker in str(exc) or "OSError" not in str(exc) or not exc.__suppress_context__:
                raise RuntimeError("repeatability rollback disclosed secret or suppressed failure") from None
        else:
            raise RuntimeError("failed repeatability rollback unexpectedly accepted")
    finally:
        module.write = original_write
        module.atomic_write_bytes = original_atomic
        module.run_post_write_validators = original_validators



def run_stronger_readiness_negatives(module) -> None:
    protected = (module.CONTRACT, module.LOAD, module.STATUS)
    before = {path: path.read_bytes() for path in protected}
    originals = {path: module.load(path) for path in (module.CONTRACT, module.LOAD, module.STATUS, module.RESULT)}
    original_load = module.load
    original_validator = module.run_validator
    original_write = module.write_transactionally
    cases = [
        (module.CONTRACT, "capacityBoundaryEstablished"),
        (module.CONTRACT, "operationalThresholdApproved"),
        (module.CONTRACT, "independentReviewCompleted"),
        (module.CONTRACT, "productionReady"),
        (module.LOAD, "capacityBoundaryEstablished"),
        (module.LOAD, "operationalThresholds"),
        (module.LOAD, "productionReady"),
    ]
    for target, field in cases:
        fixture = {path: copy.deepcopy(value) for path, value in originals.items()}
        fixture[target]["readiness"][field] = True
        def fake_load(path):
            return fixture[path]
        def forbidden_write(*args):
            raise RuntimeError("stronger readiness reached write boundary")
        module.load = fake_load
        module.run_validator = lambda *args: None
        module.write_transactionally = forbidden_write
        try:
            try:
                module.main()
            except module.Fail as exc:
                if "refusing to downgrade stronger" not in str(exc):
                    raise RuntimeError(f"unexpected stronger readiness rejection: {field}") from None
            else:
                raise RuntimeError(f"stronger readiness was downgraded: {field}")
        finally:
            module.load = original_load
            module.run_validator = original_validator
            module.write_transactionally = original_write

    for prior in (module.CONTRACT, module.LOAD):
        fixture = {path: copy.deepcopy(value) for path, value in originals.items()}
        fixture[module.RESULT]["repeatableLocalDegradationSignalObserved"] = False
        fixture[module.CONTRACT]["readiness"]["repeatableLocalDegradationSignalObserved"] = prior == module.CONTRACT
        fixture[module.LOAD]["readiness"]["repeatableLocalDegradationSignalObserved"] = prior == module.LOAD
        module.load = lambda path: fixture[path]
        module.run_validator = lambda *args: None
        module.write_transactionally = lambda *args: (_ for _ in ()).throw(RuntimeError("signal downgrade reached write"))
        try:
            try:
                module.main()
            except module.Fail as exc:
                if "refusing to downgrade previously admitted" not in str(exc):
                    raise RuntimeError("unexpected signal regression rejection") from None
            else:
                raise RuntimeError("previously admitted repeatability signal was downgraded")
        finally:
            module.load = original_load
            module.run_validator = original_validator
            module.write_transactionally = original_write
    assert_unchanged(protected, before, "stronger readiness and signal downgrade negatives")


def main() -> int:
    module = load_module()
    run_authority_substitutions(module)
    run_prewrite_failure(module)
    run_postwrite_failure(module)
    run_atomic_replace_failure(module)
    run_validator_output_negative(module)
    run_atomic_path_negative(module)
    run_rollback_secret_negative(module)
    run_stronger_readiness_negatives(module)
    print("Memory OS controlled saturation repeatability reconcile negative PASS")
    print("authority substitution plus pre-write/post-write/atomic failures are fail-closed")
    print("temporary authority residue: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
