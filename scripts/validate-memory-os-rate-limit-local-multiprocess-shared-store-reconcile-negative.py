#!/usr/bin/env python3
"""Negative checks for local multi-process shared-store reconciliation authority."""

from __future__ import annotations

import copy
import importlib.util
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-rate-limit-local-multiprocess-shared-store.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-rate-limit-local-multiprocess-shared-store.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(name: str, action) -> None:
    try:
        action()
    except Exception as exc:
        if exc.__class__.__module__.startswith("memory_os_rate_limit_local_shared_store_") and exc.__class__.__name__ == "Fail":
            print(f"PASS reject: {name}")
            return
        raise Fail(f"unexpected rejection for {name}: {exc.__class__.__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def expect_any_failure(name: str, action) -> None:
    try:
        action()
    except Exception:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")


def authority_identity_negative(module) -> None:
    real_operability = module.OPERABILITY_VALIDATOR
    module.OPERABILITY_VALIDATOR = module.RATE_LIMIT_VALIDATOR
    try:
        expect_rejected(
            "repository-contained operability validator substitution",
            module.validate_runtime_authority,
        )
    finally:
        module.OPERABILITY_VALIDATOR = real_operability


def execution_authority_negative(module) -> None:
    cases = (
        ("validate_runtime_authority", lambda: None, "runtime guard substitution"),
        ("run_validator", lambda _path: None, "validator execution helper substitution"),
        ("atomic_write_json", lambda _path, _value: None, "JSON atomic writer substitution"),
        ("atomic_write_bytes", lambda _path, _value: None, "byte atomic writer substitution"),
    )
    original_contract = module.CONTRACT.read_bytes()
    original_status = module.STATUS.read_bytes()
    for attribute, substitute, label in cases:
        original = getattr(module, attribute)
        setattr(module, attribute, substitute)
        try:
            expect_rejected(label, module.main)
            require(module.CONTRACT.read_bytes() == original_contract,
                    f"canonical contract mutated after rejected {label}")
            require(module.STATUS.read_bytes() == original_status,
                    f"Production Status mutated after rejected {label}")
        finally:
            setattr(module, attribute, original)


def transaction_binding_negative(module) -> None:
    original_contract = module.CONTRACT.read_bytes()
    original_status = module.STATUS.read_bytes()
    real_guard = module.validate_runtime_authority
    real_runner = module.run_validator
    real_json_writer = module.atomic_write_json
    real_byte_writer = module.atomic_write_bytes

    module.validate_runtime_authority = lambda: None
    module.run_validator = lambda _path: None
    module.atomic_write_json = lambda _path, _value: None
    module.atomic_write_bytes = lambda _path, _value: None
    try:
        expect_rejected("paired reconcile transaction helper substitution", module.main)
        require(module.CONTRACT.read_bytes() == original_contract,
                "canonical contract mutated after paired transaction substitution")
        require(module.STATUS.read_bytes() == original_status,
                "Production Status mutated after paired transaction substitution")
    finally:
        module.validate_runtime_authority = real_guard
        module.run_validator = real_runner
        module.atomic_write_json = real_json_writer
        module.atomic_write_bytes = real_byte_writer

    default_cases = (
        (real_guard, real_guard.__defaults__, (module.ROOT / "contracts", real_guard.__defaults__[1]), "runtime guard defaults"),
        (real_runner, real_runner.__defaults__, (lambda *args, **kwargs: None,), "validator subprocess defaults"),
        (real_json_writer, real_json_writer.__defaults__, (lambda _path, _payload: None,), "JSON writer defaults"),
        (real_byte_writer, real_byte_writer.__defaults__, (lambda _src, _dst: None,), "byte writer defaults"),
    )
    for function, original_defaults, substitute_defaults, label in default_cases:
        require(original_defaults is not None, f"{label} missing")
        function.__defaults__ = substitute_defaults
        try:
            expect_rejected(f"{label} mutation", module.main)
            require(module.CONTRACT.read_bytes() == original_contract,
                    f"canonical contract mutated after rejected {label}")
            require(module.STATUS.read_bytes() == original_status,
                    f"Production Status mutated after rejected {label}")
        finally:
            function.__defaults__ = original_defaults


def ordering_negative(module) -> None:
    values = ["before", module.EVIDENCE_PREFIX + " old", "after"]
    module.replace_prefixed_once(values, module.EVIDENCE_PREFIX, module.EVIDENCE_PREFIX + " new")
    require(values == ["before", module.EVIDENCE_PREFIX + " new", "after"],
            "existing evidence replacement must preserve list position")

    duplicate = [module.EVIDENCE_PREFIX + " one", module.EVIDENCE_PREFIX + " two"]
    expect_rejected(
        "duplicate local shared-store evidence prefixes",
        lambda: module.replace_prefixed_once(duplicate, module.EVIDENCE_PREFIX, module.EVIDENCE_PREFIX + " new"),
    )


def atomic_writer_negative(module) -> None:
    original_contract = module.CONTRACT.read_bytes()
    original_status = module.STATUS.read_bytes()
    original_mode = stat.S_IMODE(module.CONTRACT.stat().st_mode)
    real_replace = module.os.replace

    module.atomic_write_bytes(module.CONTRACT, original_contract)
    require(module.CONTRACT.read_bytes() == original_contract,
            "atomic no-op write changed canonical contract bytes")
    require(stat.S_IMODE(module.CONTRACT.stat().st_mode) == original_mode,
            "atomic no-op write changed canonical contract mode")

    def fail_contract_replace(src, dst):
        if Path(dst) == module.CONTRACT:
            raise OSError("synthetic atomic replacement rejection")
        return real_replace(src, dst)

    module.os.replace = fail_contract_replace
    try:
        expect_any_failure(
            "atomic replacement failure preserves canonical authority",
            lambda: module.atomic_write_bytes(module.CONTRACT, b"synthetic mutation\n"),
        )
        require(module.CONTRACT.read_bytes() == original_contract,
                "canonical contract changed after atomic replacement failure")
        require(not list(module.CONTRACT.parent.glob(f".{module.CONTRACT.name}.*.tmp")),
                "atomic replacement failure left temporary contract authority")
    finally:
        module.os.replace = real_replace
        if module.CONTRACT.read_bytes() != original_contract:
            module.atomic_write_bytes(module.CONTRACT, original_contract)
        if module.STATUS.read_bytes() != original_status:
            module.atomic_write_bytes(module.STATUS, original_status)


def validator_semantic_negatives(module) -> None:
    real_load = module.load
    contract = copy.deepcopy(real_load(module.CONTRACT))
    result = copy.deepcopy(real_load(module.RESULT))

    substituted_contract = copy.deepcopy(contract)
    substituted_contract["validator"] = "scripts/validate-memory-os-rate-limit.py"

    def load_substituted_contract(path: Path):
        if path == module.CONTRACT:
            return copy.deepcopy(substituted_contract)
        return real_load(path)

    module.load = load_substituted_contract
    try:
        expect_rejected(
            "contract cannot substitute a repository-contained validator",
            module.main,
        )
    finally:
        module.load = real_load

    detached_result = copy.deepcopy(result)
    detached_result["sourceCommitSha"] = "0" * 40

    def load_detached_result(path: Path):
        if path == module.RESULT:
            return copy.deepcopy(detached_result)
        return real_load(path)

    module.load = load_detached_result
    try:
        expect_rejected(
            "local rehearsal source commit must belong to current HEAD ancestry",
            module.main,
        )
    finally:
        module.load = real_load


def rollback_negative(module) -> None:
    original_contract = module.CONTRACT.read_bytes()
    original_status = module.STATUS.read_bytes()
    original_operability = module.OPERABILITY_VALIDATOR.read_bytes()
    real_normalized_status = module.normalized_status

    def fake_status(current, result_present):
        candidate = copy.deepcopy(current)
        gate = next(
            row for row in candidate.get("areas", [])
            if isinstance(row, dict) and row.get("id") == "OPS-P0-005"
        )
        evidence = gate.get("existingEvidence")
        require(isinstance(evidence, list), "OPS-P0-005 existingEvidence missing in rollback fixture")
        evidence.append("synthetic local shared-store rollback sentinel")
        return candidate

    module.normalized_status = fake_status
    module.atomic_write_bytes(
        module.OPERABILITY_VALIDATOR,
        b"#!/usr/bin/env python3\nraise SystemExit(1)\n",
    )
    try:
        expect_rejected(
            "post-write canonical operability rejection rolls back local shared-store authority",
            module.main,
        )
        require(module.CONTRACT.read_bytes() == original_contract,
                "local shared-store contract was not rolled back byte-for-byte")
        require(module.STATUS.read_bytes() == original_status,
                "production status was not rolled back byte-for-byte")
    finally:
        module.normalized_status = real_normalized_status
        module.atomic_write_bytes(module.OPERABILITY_VALIDATOR, original_operability)
        if module.CONTRACT.read_bytes() != original_contract:
            module.atomic_write_bytes(module.CONTRACT, original_contract)
        if module.STATUS.read_bytes() != original_status:
            module.atomic_write_bytes(module.STATUS, original_status)
    require(not list(module.CONTRACT.parent.glob(f".{module.CONTRACT.name}.*.tmp")),
            "rollback left temporary contract authority")
    require(not list(module.STATUS.parent.glob(f".{module.STATUS.name}.*.tmp")),
            "rollback left temporary Production Status authority")


def main() -> int:
    reconciler = load_module(
        RECONCILER,
        "memory_os_rate_limit_local_shared_store_reconcile_negative_target",
    )
    validator = load_module(
        VALIDATOR,
        "memory_os_rate_limit_local_shared_store_validator_negative_target",
    )
    reconciler.validate_runtime_authority()
    require(validator.main() == 0, "canonical local shared-store validator baseline failed")
    authority_identity_negative(reconciler)
    execution_authority_negative(reconciler)
    transaction_binding_negative(reconciler)
    ordering_negative(reconciler)
    atomic_writer_negative(reconciler)
    validator_semantic_negatives(validator)
    rollback_negative(reconciler)
    require(reconciler.main() == 0, "canonical local shared-store reconciler failed after negatives")
    print("Memory OS local multi-process shared-store reconcile negative suite PASS")
    print("canonical validator identity: enforced")
    print("contract executable identity: enforced")
    print("source commit ancestry: enforced")
    print("same-index evidence replacement: enforced")
    print("duplicate evidence prefix rejection: enforced")
    print("atomic replacement and mode preservation: enforced")
    print("runtime guard and validator transport: enforced")
    print("definition-time transaction bindings: enforced")
    print("post-write aggregate rollback: enforced")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RATE LIMIT LOCAL SHARED-STORE RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
