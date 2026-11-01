#!/usr/bin/env python3
"""Prove generation-binding/status reconcile keeps canonical authority and rollback boundaries."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import shutil
import stat
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BINDING_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-binding.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-generation-status.py"
WORKFLOW = ROOT / ".github/workflows/backup-restore-generation-binding.yml"
CONTRACT = ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_target(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_reconciler():
    return load_target(RECONCILER, "memory_os_generation_status_authority_negative")


def load_binding_validator():
    return load_target(BINDING_VALIDATOR, "memory_os_generation_binding_authority_negative")


def expect_direct_authority_rejected(reconciler, name: str, field: str, attribute: str, replacement: Path) -> None:
    contract_before = CONTRACT.read_bytes()
    status_before = STATUS.read_bytes()
    contract_mode_before = stat.S_IMODE(CONTRACT.stat().st_mode)
    status_mode_before = stat.S_IMODE(STATUS.stat().st_mode)
    original = getattr(reconciler, attribute)
    setattr(reconciler, attribute, replacement)
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require(f"{field} authority drift" in str(exc), f"{name} rejected at wrong boundary: {exc}")
        else:
            raise Fail(f"direct generation status reconciler unexpectedly accepted: {name}")
        require(CONTRACT.read_bytes() == contract_before, f"canonical contract mutated while rejecting {name}")
        require(STATUS.read_bytes() == status_before, f"canonical status mutated while rejecting {name}")
        require(stat.S_IMODE(CONTRACT.stat().st_mode) == contract_mode_before, f"canonical contract mode mutated while rejecting {name}")
        require(stat.S_IMODE(STATUS.stat().st_mode) == status_mode_before, f"canonical status mode mutated while rejecting {name}")
    finally:
        setattr(reconciler, attribute, original)


def expect_binding_authority_rejected(binding, name: str, field: str, attribute: str, replacement: Path) -> None:
    contract_before = CONTRACT.read_bytes()
    status_before = STATUS.read_bytes()
    contract_mode_before = stat.S_IMODE(CONTRACT.stat().st_mode)
    status_mode_before = stat.S_IMODE(STATUS.stat().st_mode)
    original = getattr(binding, attribute)
    setattr(binding, attribute, replacement)
    try:
        try:
            binding.main()
        except binding.Fail as exc:
            require(f"{field} authority drift" in str(exc), f"{name} rejected at wrong boundary: {exc}")
        else:
            raise Fail(f"direct generation binding validator unexpectedly accepted: {name}")
        require(CONTRACT.read_bytes() == contract_before, f"canonical contract mutated while rejecting {name}")
        require(STATUS.read_bytes() == status_before, f"canonical status mutated while rejecting {name}")
        require(stat.S_IMODE(CONTRACT.stat().st_mode) == contract_mode_before, f"canonical contract mode mutated while rejecting {name}")
        require(stat.S_IMODE(STATUS.stat().st_mode) == status_mode_before, f"canonical status mode mutated while rejecting {name}")
    finally:
        setattr(binding, attribute, original)


def prove_binding_validator_authorities() -> None:
    binding = load_binding_validator()
    cases = (
        ("generation binding contract substitution", "generation binding contract", "CONTRACT", binding.BACKUP_POLICY),
        ("backup restore policy substitution", "backup restore policy contract", "BACKUP_POLICY", binding.LOCAL_FOUNDATIONS),
        ("local restore foundation substitution", "local restore foundation evidence", "LOCAL_FOUNDATIONS", binding.GENERATION),
        ("environment generation contract substitution", "environment generation contract", "GENERATION", binding.EVIDENCE_CONTRACT),
        ("environment generation registry substitution", "environment generation registry", "GEN_REGISTRY", binding.EVIDENCE_REGISTRY),
        ("generation evidence contract substitution", "generation evidence contract", "EVIDENCE_CONTRACT", binding.GENERATION),
        ("generation evidence registry substitution", "generation evidence registry", "EVIDENCE_REGISTRY", binding.GEN_REGISTRY),
        ("generation evidence writer substitution", "generation evidence writer", "EVIDENCE_WRITER", BINDING_VALIDATOR),
    )
    for name, field, attribute, replacement in cases:
        expect_binding_authority_rejected(binding, name, field, attribute, replacement)
    try:
        binding.enforce_runtime_authorities()
    except binding.Fail as exc:
        raise Fail(f"canonical generation binding authorities rejected: {exc}") from exc
    print(f"PASS boundary: generation binding direct data/writer substitutions rejected: {len(cases)}")


def validate_atomic_diagnostic_publication() -> None:
    require(WORKFLOW.is_file(), "generation binding workflow missing")
    text = WORKFLOW.read_text(encoding="utf-8")
    required = (
        "tempfile.mkstemp(",
        "dir=path.parent",
        "handle.flush()",
        "os.fsync(handle.fileno())",
        "os.replace(tmp_name, path)",
        "os.unlink(tmp_name)",
    )
    missing = [fragment for fragment in required if fragment not in text]
    require(not missing, f"generation binding diagnostic publication is not crash-safe: missing {missing}")
    require(
        "path.write_text(json.dumps(value" not in text,
        "generation binding diagnostic publication regressed to direct write_text",
    )



def prove_generation_status_private_validator_transport(reconciler) -> None:
    """Pre-write and post-write validators must share isolated bounded transport."""
    original_run = reconciler.subprocess.run
    marker = "synthetic-private-generation-status-validator-output"
    poisoned = {
        "PYTHONPATH": "SYNTHETIC_UNTRUSTED_IMPORT",
        "PYTHONHOME": "SYNTHETIC_UNTRUSTED_HOME",
        "PYTHONWARNINGS": "SYNTHETIC_UNTRUSTED_WARNINGS",
        "LD_PRELOAD": "SYNTHETIC_UNTRUSTED_LOADER",
        "DYLD_INSERT_LIBRARIES": "SYNTHETIC_UNTRUSTED_DYLD",
        "GIT_CONFIG_GLOBAL": "SYNTHETIC_UNTRUSTED_GIT_CONFIG",
        "SAFE_GENERATION_STATUS_VALIDATOR_ENV": "preserved",
    }
    targets = (
        (reconciler.VALIDATOR, reconciler.VALIDATOR_REL, "generation binding validator"),
        (reconciler.BACKUP_VALIDATOR, reconciler.BACKUP_VALIDATOR_REL, "backup validator"),
        (reconciler.OPERABILITY_VALIDATOR, reconciler.OPERABILITY_VALIDATOR_REL, "operability validator"),
    )
    seen: list[int | bool | None] = []

    def fake_run(exit_code):
        def run(argv, **kwargs):
            require(argv[0] == reconciler.sys.executable
                    and argv[1] in [str(path) for path, _, _ in targets],
                    "generation status validator child target drift")
            require(kwargs.get("cwd") == reconciler.ROOT,
                    "generation status validator cwd drift")
            require(kwargs.get("stdout") == reconciler.subprocess.DEVNULL
                    and kwargs.get("stderr") == reconciler.subprocess.DEVNULL,
                    "generation status validator raw diagnostics captured")
            require(kwargs.get("timeout") == 120 and kwargs.get("check") is False,
                    "generation status validator runtime budget drift")
            child_env = kwargs.get("env")
            require(isinstance(child_env, dict), "generation status child environment missing")
            require(child_env.get("SAFE_GENERATION_STATUS_VALIDATOR_ENV") == "preserved",
                    "generation status benign environment lost")
            for key in ("PYTHONPATH", "PYTHONHOME", "PYTHONWARNINGS",
                        "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "GIT_CONFIG_GLOBAL"):
                require(key not in child_env, "generation status inherited override: " + key)
            require(child_env == {
                key: value for key, value in reconciler.os.environ.items()
                if not key.startswith(("PYTHON", "LD_", "DYLD_", "GIT_"))
            }, "generation status child environment drift")
            seen.append(exit_code)
            return subprocess.CompletedProcess(argv, exit_code, stdout=marker, stderr=marker)
        return run

    with patch.dict(reconciler.os.environ, poisoned):
        try:
            for path, relative, label in targets:
                reconciler.subprocess.run = fake_run(0)
                reconciler.run_validator(path, relative, label)
                for code in (1, False, None):
                    reconciler.subprocess.run = fake_run(code)
                    try:
                        reconciler.run_validator(path, relative, label)
                    except reconciler.Fail as exc:
                        require(str(exc) == f"{label} failed (raw output withheld)",
                                "generation status validator failure class drift")
                        require(marker not in str(exc), "generation status private output leaked")
                    else:
                        raise Fail("generation status validator invalid return accepted")
                for failure in (OSError(marker), ValueError(marker), TypeError(marker),
                                subprocess.TimeoutExpired(["synthetic"], 120, output=marker, stderr=marker)):
                    def raise_failure(*_args, **_kwargs):
                        raise failure
                    reconciler.subprocess.run = raise_failure
                    try:
                        reconciler.run_validator(path, relative, label)
                    except reconciler.Fail as exc:
                        require(str(exc) == f"{label} unavailable or timed out (raw output withheld)",
                                "generation status unavailable class drift")
                        require(marker not in str(exc), "generation status exception details leaked")
                    else:
                        raise Fail("generation status validator unavailable accepted")
        finally:
            reconciler.subprocess.run = original_run
    require(seen == [0, 1, False, None] * 3,
            "generation status validator positive/negative controls incomplete")
    try:
        reconciler.run_validator(reconciler.CONTRACT, reconciler.CONTRACT_REL, "synthetic unreviewed validator")
    except reconciler.Fail as exc:
        require(str(exc) == "unreviewed generation-status validator",
                "generation status unreviewed validator rejected at wrong boundary")
    else:
        raise Fail("generation status unreviewed repository validator accepted")
    print("PASS: generation status validators use isolated bounded private transport and closed targets")


def prove_generation_status_fdopen_ownership(reconciler) -> None:
    """CI-reached negative: fdopen failure must close the untransferred mkstemp FD."""
    with tempfile.TemporaryDirectory(prefix=".tmp-generation-status-fdopen-", dir=TMP_PARENT) as tmpdir:
        target = Path(tmpdir) / "fdopen-failure.json"
        target.write_text("{}\\n", encoding="utf-8")
        target.chmod(0o640)
        original_bytes = target.read_bytes()
        original_mode = stat.S_IMODE(target.stat().st_mode)
        status_before, contract_before = STATUS.read_bytes(), CONTRACT.read_bytes()
        original_fdopen = reconciler.os.fdopen
        captured = []

        def reject_fdopen(fd, *_args, **_kwargs):
            captured.append(fd)
            raise OSError("synthetic generation-status fdopen failure")

        reconciler.os.fdopen = reject_fdopen
        try:
            try:
                reconciler.write_text(target, original_bytes.decode("utf-8") + " ")
            except reconciler.Fail as exc:
                require("cannot atomically write" in str(exc),
                        f"generation-status fdopen rejected at wrong boundary: {exc}")
            else:
                raise Fail("generation-status fdopen failure unexpectedly accepted")
        finally:
            reconciler.os.fdopen = original_fdopen

        require(len(captured) == 1, "generation-status fdopen injection not reached")
        try:
            os.fstat(captured[0])
        except OSError:
            pass
        else:
            os.close(captured[0])
            raise Fail("generation-status fdopen failure leaked a descriptor")
        require(target.read_bytes() == original_bytes
                and stat.S_IMODE(target.stat().st_mode) == original_mode,
                "generation-status fdopen failure changed fixture bytes or mode")
        require(not list(target.parent.glob(f".{target.name}.*.tmp")),
                "generation-status fdopen failure left a temporary authority")
        require(STATUS.read_bytes() == status_before and CONTRACT.read_bytes() == contract_before,
                "generation-status fdopen failure changed protected canonical authority")
    print("PASS boundary: generation-status fdopen failure closes untransferred descriptor")


def main() -> int:
    require(BINDING_VALIDATOR.is_file(), "generation binding validator missing")
    require(RECONCILER.is_file(), "generation status reconciler missing")
    require(CONTRACT.is_file() and STATUS.is_file(), "canonical generation status authority missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    prove_binding_validator_authorities()
    reconciler = load_reconciler()
    prove_generation_status_private_validator_transport(reconciler)
    validate_atomic_diagnostic_publication()
    prove_generation_status_fdopen_ownership(reconciler)

    cases = (
        ("generation binding contract substitution", "generation binding contract", "CONTRACT", reconciler.STATUS),
        ("generation binding validator substitution", "generation binding validator", "VALIDATOR", reconciler.BACKUP_VALIDATOR),
        ("backup validator substitution", "backup validator", "BACKUP_VALIDATOR", reconciler.OPERABILITY_VALIDATOR),
        ("operability validator substitution", "operability validator", "OPERABILITY_VALIDATOR", reconciler.BACKUP_VALIDATOR),
        ("production status substitution", "production operability status", "STATUS", reconciler.CONTRACT),
    )
    for name, field, attribute, replacement in cases:
        expect_direct_authority_rejected(reconciler, name, field, attribute, replacement)
    print(f"PASS boundary: generation status direct authority substitutions rejected: {len(cases)}")

    original_enforcer = reconciler.enforce_runtime_authorities
    original_contract = reconciler.CONTRACT
    original_status = reconciler.STATUS
    original_runner = reconciler.run_validator
    original_write = reconciler.write_text
    original_replace = reconciler.os.replace
    try:
        with tempfile.TemporaryDirectory(prefix=".tmp-generation-status-authority-", dir=TMP_PARENT) as tmpdir:
            tmp = Path(tmpdir)
            contract_copy = tmp / CONTRACT.name
            status_copy = tmp / STATUS.name
            shutil.copyfile(CONTRACT, contract_copy)
            shutil.copyfile(STATUS, status_copy)
            os.chmod(status_copy, 0o640)
            status_before = status_copy.read_bytes()
            status_mode_before = stat.S_IMODE(status_copy.stat().st_mode)
            observed: list[str] = []
            status_write_observed = False
            observed_write_modes: list[int] = []

            def track_write(path: Path, text: str) -> None:
                nonlocal status_write_observed
                if path == status_copy:
                    status_write_observed = True
                original_write(path, text)
                if path == status_copy:
                    observed_write_modes.append(stat.S_IMODE(path.stat().st_mode))

            def fail_only_aggregate(path: Path, expected_relative: Path, label: str) -> None:
                observed.append(label)
                if label == "generation binding validator":
                    require(not status_write_observed, "generation binding validator ran after status write")
                    return
                require(status_write_observed, f"{label} ran before status write")
                if label == "backup validator":
                    return
                require(label == "operability validator", f"unexpected generation status validator: {label}")
                raise reconciler.Fail("synthetic generation status operability rejection")

            reconciler.enforce_runtime_authorities = lambda: None
            reconciler.CONTRACT = contract_copy
            reconciler.STATUS = status_copy
            reconciler.run_validator = fail_only_aggregate
            reconciler.write_text = track_write
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                require("synthetic generation status operability rejection" in str(exc), f"rollback rejected at wrong boundary: {exc}")
            else:
                raise Fail("forced generation status operability rejection unexpectedly accepted")

            require(
                observed == ["generation binding validator", "backup validator", "operability validator"],
                "generation status validator order drift",
            )
            require(status_write_observed, "generation status transaction did not invoke atomic status writer")
            require(status_copy.read_bytes() == status_before, "failed aggregate validation left production status mutation behind")
            require(
                observed_write_modes == [status_mode_before, status_mode_before],
                f"generation status candidate/rollback mode drift: {observed_write_modes}",
            )
            require(
                stat.S_IMODE(status_copy.stat().st_mode) == status_mode_before,
                "failed aggregate validation changed production status mode",
            )

            replace_copy = tmp / "replace-rejection-status.json"
            shutil.copyfile(STATUS, replace_copy)
            os.chmod(replace_copy, 0o640)
            replace_before = replace_copy.read_bytes()
            replace_mode_before = stat.S_IMODE(replace_copy.stat().st_mode)

            def reject_replace(src, dst) -> None:
                if Path(dst) == replace_copy:
                    raise OSError("synthetic generation status replace rejection")
                original_replace(src, dst)

            reconciler.os.replace = reject_replace
            try:
                reconciler.write_text = original_write
                reconciler.write_text(replace_copy, replace_before.decode("utf-8"))
            except reconciler.Fail as exc:
                require("cannot atomically write" in str(exc), f"replace rejection surfaced at wrong boundary: {exc}")
            else:
                raise Fail("forced generation status replace rejection unexpectedly accepted")
            finally:
                reconciler.os.replace = original_replace

            require(replace_copy.read_bytes() == replace_before, "replace rejection changed canonical status bytes")
            require(
                stat.S_IMODE(replace_copy.stat().st_mode) == replace_mode_before,
                "replace rejection changed canonical status mode",
            )
            residue = list(tmp.glob(f".{replace_copy.name}.*.tmp"))
            require(not residue, f"replace rejection left temporary residue: {[path.name for path in residue]}")
    finally:
        reconciler.enforce_runtime_authorities = original_enforcer
        reconciler.CONTRACT = original_contract
        reconciler.STATUS = original_status
        reconciler.run_validator = original_runner
        reconciler.write_text = original_write
        reconciler.os.replace = original_replace

    print("PASS rollback: generation status restored byte-for-byte and mode-for-mode after aggregate operability rejection")
    print("PASS atomic rejection: generation status replace failure preserves bytes/mode and leaves no temp residue")
    print("generation binding canonical data/writer substitutions accepted: false")
    print("generation binding validator remains pre-write: true")
    print("backup and operability validators remain post-write: true")
    print("byte-current status still exercises atomic write boundary: true")
    print("crash-safe generation-binding failure diagnostic required: true")
    print("canonical blockers rewritten: false")
    print("production evidence created: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION STATUS AUTHORITY NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
