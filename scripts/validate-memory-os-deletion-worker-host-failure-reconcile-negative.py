#!/usr/bin/env python3
"""Focused fail-closed checks for host-failure admission reconciliation."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts/reconcile-memory-os-deletion-worker-host-failure.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_target() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_host_failure_reconcile_negative", TARGET)
    require(spec is not None and spec.loader is not None, "cannot load host-failure reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def swap_attr(target: object, name: str, value: object) -> Callable[[], None]:
    original = getattr(target, name)
    setattr(target, name, value)
    return lambda: setattr(target, name, original)


def swap_many(*changes: tuple[object, str, object]) -> Callable[[], None]:
    originals = [(target, name, getattr(target, name)) for target, name, _ in changes]
    for target, name, value in changes:
        setattr(target, name, value)

    def restore() -> None:
        for target, name, value in reversed(originals):
            setattr(target, name, value)

    return restore


def snapshots(module: ModuleType) -> dict[Path, bytes]:
    return {
        module.CANONICAL_CONTRACT: module.CANONICAL_CONTRACT.read_bytes(),
        module.CANONICAL_STATUS: module.CANONICAL_STATUS.read_bytes(),
    }


def assert_unchanged(values: dict[Path, bytes]) -> None:
    for path, payload in values.items():
        require(path.read_bytes() == payload, f"canonical authority mutated: {path.relative_to(ROOT)}")


def expect_rejection(
    module: ModuleType,
    label: str,
    mutate: Callable[[], Callable[[], None]],
    check: Callable[[], None],
) -> None:
    before = snapshots(module)
    restore = mutate()
    try:
        try:
            check()
        except module.Fail:
            pass
        else:
            raise RuntimeError(f"authority substitution accepted: {label}")
    finally:
        restore()
    assert_unchanged(before)


def expect_rollback_failure_exhaustive(module: ModuleType) -> None:
    original_contract = module.CANONICAL_CONTRACT.read_bytes()
    original_status = module.CANONICAL_STATUS.read_bytes()
    original_contract_mode = stat.S_IMODE(module.CANONICAL_CONTRACT.stat().st_mode)
    original_status_mode = stat.S_IMODE(module.CANONICAL_STATUS.stat().st_mode)
    original_validate_writer = module.validate_atomic_writer_authority
    original_writer = module.CANONICAL_ATOMIC_WRITE_BYTES
    rollback_calls: list[Path] = []
    validation_calls = 0

    contract = json.loads(original_contract.decode("utf-8"))
    status = json.loads(original_status.decode("utf-8"))
    readiness = contract.setdefault("readiness", {})
    readiness["contractDefined"] = False

    def stateful_validate_writer() -> None:
        nonlocal validation_calls
        validation_calls += 1
        if validation_calls == 1:
            original_validate_writer()
            return
        if validation_calls == 2:
            def selective_restore(path: Path, payload: bytes) -> None:
                rollback_calls.append(path)
                if path == module.CANONICAL_CONTRACT:
                    raise OSError("synthetic host-failure contract rollback failure")
                original_writer(path, payload)

            module.CANONICAL_ATOMIC_WRITE_BYTES = selective_restore
            return
        raise AssertionError(f"unexpected atomic-writer validation call: {validation_calls}")

    module.validate_atomic_writer_authority = stateful_validate_writer
    try:
        try:
            module.write_transactionally(contract, status)
        except module.Fail as exc:
            diagnostic = str(exc)
            require("host-failure post-write authority validation failed" in diagnostic,
                    f"primary host-failure validation diagnostic was lost: {diagnostic}")
            require("rollback incomplete" in diagnostic,
                    f"host-failure rollback incompleteness was not diagnosed: {diagnostic}")
            require("host-failure contract: OSError" in diagnostic,
                    "host-failure rollback exception class was lost")
            require("synthetic" not in diagnostic and exc.__suppress_context__,
                    "host-failure leaked untrusted primary/rollback exception text")
        else:
            raise RuntimeError("host-failure rollback failure was accepted")

        require(rollback_calls[:2] == [module.CANONICAL_CONTRACT, module.CANONICAL_STATUS],
                f"host-failure rollback did not continue after first restore failure: {rollback_calls!r}")
        require(module.CANONICAL_STATUS.read_bytes() == original_status,
                "host-failure rollback did not restore production status after first restore failure")
        require(stat.S_IMODE(module.CANONICAL_STATUS.stat().st_mode) == original_status_mode,
                "host-failure rollback changed production status mode")
    finally:
        module.validate_atomic_writer_authority = original_validate_writer
        module.CANONICAL_ATOMIC_WRITE_BYTES = original_writer
        original_writer(module.CANONICAL_CONTRACT, original_contract)
        original_writer(module.CANONICAL_STATUS, original_status)
        module.CANONICAL_CONTRACT.chmod(original_contract_mode)
        module.CANONICAL_STATUS.chmod(original_status_mode)

    require(module.CANONICAL_CONTRACT.read_bytes() == original_contract,
            "host-failure rollback negative cleanup changed contract bytes")
    require(module.CANONICAL_STATUS.read_bytes() == original_status,
            "host-failure rollback negative cleanup changed status bytes")
    require(stat.S_IMODE(module.CANONICAL_CONTRACT.stat().st_mode) == original_contract_mode,
            "host-failure rollback negative cleanup changed contract mode")
    require(stat.S_IMODE(module.CANONICAL_STATUS.stat().st_mode) == original_status_mode,
            "host-failure rollback negative cleanup changed status mode")


def expect_secret_free_prewrite_and_validator_failures(module: ModuleType) -> None:
    class FailingGenerationCount:
        def canonical_generation_count(self):
            raise RuntimeError("SYNTHETIC_SECRET_GENERATION_COUNT")

    class FailingProjection:
        NO_GENERATION_LIMITATION = "synthetic generation limitation"

        def canonical_generation_count(self):
            return 0

        def validate_generation_projection(self, contract, registered):
            raise ValueError("SYNTHETIC_SECRET_GENERATION_PROJECTION")

    original_loader = module.load_host_validator
    try:
        for fake, expected in (
            (FailingGenerationCount(), "canonical generation authority validation failed: RuntimeError"),
            (FailingProjection(), "host-failure generation projection invalid: ValueError"),
        ):
            module.load_host_validator = lambda fake=fake: fake
            candidate = {"currentBoundary": {}, "readiness": {}, "limitations": []}
            try:
                module.reconcile_generation_projection(candidate)
            except module.Fail as exc:
                require(expected in str(exc) and "SYNTHETIC_SECRET" not in str(exc) and exc.__suppress_context__,
                        "host-failure generation prewrite leaked raw exception details")
            else:
                raise AssertionError("host-failure generation prewrite accepted synthetic failure")
    finally:
        module.load_host_validator = original_loader

    with tempfile.TemporaryDirectory(prefix="host-failure-secret-free-") as tmp:
        root = Path(tmp)
        target = root / "scripts/reconcile-memory-os-deletion-worker-host-failure.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(TARGET, target)
        paths = (
            "contracts/operations/deletion-worker-host-failure-contract.v1.json",
            ".github/workflows/deletion-worker-host-failure-admission.yml",
            "contracts/operations/production-operability-status.json",
            "contracts/operations/load-test-scenario-contract.v1.json",
            "scripts/validate-memory-os-deletion-worker-host-failure.py",
            "scripts/validate-memory-os-load.py",
            "scripts/validate-memory-os-operability.py",
        )
        for relative in paths:
            file = root / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("{}" + chr(10), encoding="utf-8")
        spec = importlib.util.spec_from_file_location("host_failure_disposable_prewrite", target)
        require(spec is not None and spec.loader is not None, "cannot load disposable host-failure module")
        isolated = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(isolated)

        host_validator = root / "scripts/validate-memory-os-deletion-worker-host-failure.py"
        host_validator.write_text(
            "raise RuntimeError('SYNTHETIC_SECRET_VALIDATOR_IMPORT')" + chr(10), encoding="utf-8"
        )
        try:
            isolated.load_host_validator()
        except isolated.Fail as exc:
            require("cannot load canonical host-failure validator: RuntimeError" in str(exc)
                    and "SYNTHETIC_SECRET" not in str(exc) and exc.__suppress_context__,
                    "host-failure validator import leaked raw exception")
        else:
            raise AssertionError("host-failure validator import accepted synthetic failure")

        load_validator = root / "scripts/validate-memory-os-load.py"
        load_validator.write_text(
            "import sys" + chr(10)
            + "sys.stderr.write('SYNTHETIC_SECRET_LOAD')" + chr(10)
            + "raise SystemExit(1)" + chr(10), encoding="utf-8"
        )
        try:
            isolated.validate_load_authority()
        except isolated.Fail as exc:
            require("canonical load authority validation failed: CalledProcessError" in str(exc)
                    and "SYNTHETIC_SECRET" not in str(exc) and exc.__suppress_context__,
                    "host-failure load validator leaked raw exception")
        else:
            raise AssertionError("host-failure load validator accepted synthetic failure")

        host_validator.write_text(
            "import sys" + chr(10)
            + "sys.stderr.write('SYNTHETIC_SECRET_POSTWRITE')" + chr(10)
            + "raise SystemExit(1)" + chr(10), encoding="utf-8"
        )
        before_contract = (root / paths[0]).read_bytes()
        before_status = (root / paths[2]).read_bytes()
        try:
            isolated.write_transactionally({"synthetic": "after"}, {"synthetic": "after"})
        except isolated.Fail as exc:
            require("host-failure post-write authority validation failed: CalledProcessError" in str(exc)
                    and "SYNTHETIC_SECRET" not in str(exc) and exc.__suppress_context__,
                    "host-failure post-write validator leaked raw exception")
        else:
            raise AssertionError("host-failure post-write validator accepted synthetic failure")
        require((root / paths[0]).read_bytes() == before_contract,
                "host-failure post-write negative changed disposable contract")
        require((root / paths[2]).read_bytes() == before_status,
                "host-failure post-write negative changed disposable status")
        require(not list(root.rglob(".*.tmp")), "host-failure post-write negative left temporary file")
    print("PASS: host-failure prewrite import/generation and validator subprocess diagnostics are secret-free")


def main() -> int:
    module = load_target()
    module.validate_executable_authorities()
    module.validate_atomic_writer_authority()

    alternate_root = module.CANONICAL_ROOT / "scripts"
    expect_rejection(
        module,
        "paired repository root",
        lambda: swap_many((module, "CANONICAL_ROOT", alternate_root), (module, "ROOT", alternate_root)),
        module.validate_data_authorities,
    )
    expect_rejection(
        module,
        "paired contract authority",
        lambda: swap_many((module, "CANONICAL_CONTRACT", module.CANONICAL_LOAD), (module, "CONTRACT", module.CANONICAL_LOAD)),
        module.validate_data_authorities,
    )

    fake_run = lambda *args, **kwargs: None
    expect_rejection(
        module,
        "paired subprocess transport",
        lambda: swap_many((module, "CANONICAL_SUBPROCESS_RUN", fake_run), (module.subprocess, "run", fake_run)),
        module.validate_executable_authorities,
    )

    fake_replace = lambda *args, **kwargs: None
    expect_rejection(
        module,
        "paired replacement transport",
        lambda: swap_many((module, "CANONICAL_OS_REPLACE", fake_replace), (module.os, "replace", fake_replace)),
        module.validate_executable_authorities,
    )

    fake_spec = lambda *args, **kwargs: None
    expect_rejection(
        module,
        "paired module spec loader",
        lambda: swap_many(
            (module, "CANONICAL_SPEC_FROM_FILE_LOCATION", fake_spec),
            (module.importlib.util, "spec_from_file_location", fake_spec),
        ),
        module.validate_executable_authorities,
    )

    fake_module = lambda *args, **kwargs: None
    expect_rejection(
        module,
        "paired module loader",
        lambda: swap_many(
            (module, "CANONICAL_MODULE_FROM_SPEC", fake_module),
            (module.importlib.util, "module_from_spec", fake_module),
        ),
        module.validate_executable_authorities,
    )

    fake_writer = lambda *args, **kwargs: None
    expect_rejection(
        module,
        "paired atomic writer",
        lambda: swap_many(
            (module, "CANONICAL_ATOMIC_WRITE_BYTES", fake_writer),
            (module, "atomic_write_bytes", fake_writer),
        ),
        module.validate_atomic_writer_authority,
    )

    with tempfile.TemporaryDirectory(prefix="memory-os-host-failure-mode-") as tmp:
        target = Path(tmp) / "authority.json"
        target.write_bytes(b"before\n")
        os.chmod(target, 0o640)
        module.atomic_write_bytes(target, b"after\n")
        require(target.read_bytes() == b"after\n", "atomic host-failure payload mismatch")
        require(stat.S_IMODE(target.stat().st_mode) == 0o640, "atomic host-failure writer changed file mode")
        require(not list(target.parent.glob(f".{target.name}.*.tmp")), "atomic host-failure writer left temp residue")

    expect_rollback_failure_exhaustive(module)
    expect_secret_free_prewrite_and_validator_failures(module)
    assert_unchanged(snapshots(module))
    print("PASS: host-failure reconcile authority transaction, mode preservation, and secret-free exhaustive rollback diagnostics are fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
