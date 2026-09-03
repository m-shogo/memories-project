#!/usr/bin/env python3
"""Prove rate-limit operations reconcile pins exact authorities and rolls back post-write failure."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-rate-limit-operations.py"
OPERATIONS_VALIDATOR_SCRIPT = ROOT / "scripts/validate-memory-os-rate-limit-operations.py"
CANONICAL_POLICY_PATH = ROOT / "contracts/operations/rate-limit-policy-contract.v1.json"
CANONICAL_STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "memory_os_rate_limit_operations_reconcile_negative", RECONCILER_PATH
    )
    require(spec is not None and spec.loader is not None,
            "cannot load rate-limit operations reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_operations_validator() -> Any:
    spec = importlib.util.spec_from_file_location(
        "memory_os_rate_limit_operations_validator_negative", OPERATIONS_VALIDATOR_SCRIPT
    )
    require(spec is not None and spec.loader is not None,
            "cannot load rate-limit operations validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def prove_atomic_transport_and_mode(reconciler: Any) -> None:
    original = CANONICAL_POLICY_PATH.read_bytes()
    original_mode = CANONICAL_POLICY_PATH.stat().st_mode & 0o7777
    pattern = f".{CANONICAL_POLICY_PATH.name}.*.tmp"
    before = {path.name for path in CANONICAL_POLICY_PATH.parent.glob(pattern)}
    original_replace = reconciler.os.replace
    original_canonical_replace = reconciler.CANONICAL_OS_REPLACE

    def fake_replace(_source: Any, _destination: Any) -> None:
        return None

    reconciler.os.replace = fake_replace
    reconciler.CANONICAL_OS_REPLACE = fake_replace
    try:
        try:
            reconciler.atomic_write_bytes(CANONICAL_POLICY_PATH, original)
        except reconciler.ReconcileFailure as exc:
            require("os.replace transport execution authority drift" in str(exc),
                    f"paired os.replace substitution rejected for unrelated reason: {exc}")
        else:
            raise NegativeFailure("atomic writer accepted paired os.replace transport substitution")
    finally:
        reconciler.os.replace = original_replace
        reconciler.CANONICAL_OS_REPLACE = original_canonical_replace

    require(CANONICAL_POLICY_PATH.read_bytes() == original,
            "canonical policy changed after rejected os.replace substitution")
    require((CANONICAL_POLICY_PATH.stat().st_mode & 0o7777) == original_mode,
            "canonical policy mode changed after rejected os.replace substitution")
    after = {path.name for path in CANONICAL_POLICY_PATH.parent.glob(pattern)}
    require(after == before,
            f"rejected transport substitution left temporary residue: {sorted(after - before)}")

    reconciler.atomic_write_bytes(CANONICAL_POLICY_PATH, original)
    require(CANONICAL_POLICY_PATH.read_bytes() == original,
            "canonical policy bytes changed after canonical atomic rewrite")
    require((CANONICAL_POLICY_PATH.stat().st_mode & 0o7777) == original_mode,
            "canonical policy mode changed after canonical atomic rewrite")
    require({path.name for path in CANONICAL_POLICY_PATH.parent.glob(pattern)} == before,
            "canonical atomic rewrite left temporary residue")


def prove_transaction_rollback(reconciler: Any) -> None:
    originals = {
        CANONICAL_POLICY_PATH: CANONICAL_POLICY_PATH.read_bytes(),
        CANONICAL_STATUS_PATH: CANONICAL_STATUS_PATH.read_bytes(),
    }
    modes = {
        CANONICAL_POLICY_PATH: CANONICAL_POLICY_PATH.stat().st_mode & 0o7777,
        CANONICAL_STATUS_PATH: CANONICAL_STATUS_PATH.stat().st_mode & 0o7777,
    }
    policy = copy.deepcopy(load_json(CANONICAL_POLICY_PATH))
    status = copy.deepcopy(load_json(CANONICAL_STATUS_PATH))
    policy["operations"]["drillCompleted"] = False
    status["asOf"] = "2099-01-01"

    original_validator = reconciler.validate_written_authority
    reconciler.validate_written_authority = lambda: (_ for _ in ()).throw(
        reconciler.ReconcileFailure("synthetic post-write validation failure")
    )
    try:
        try:
            reconciler.transactional_write(policy, status)
        except reconciler.ReconcileFailure as exc:
            require("synthetic post-write validation failure" in str(exc),
                    "transaction rollback failed for unrelated reason")
        else:
            raise NegativeFailure(
                "transactional write accepted synthetic post-write validation failure"
            )

        for path, original in originals.items():
            require(path.read_bytes() == original,
                    f"rollback failed for {path.relative_to(ROOT)}")
            require((path.stat().st_mode & 0o7777) == modes[path],
                    f"rollback changed mode for {path.relative_to(ROOT)}")
            require(not list(path.parent.glob(f".{path.name}.*.tmp")),
                    f"rollback left temp residue for {path.relative_to(ROOT)}")
    finally:
        reconciler.validate_written_authority = original_validator
        for path, original in originals.items():
            if path.read_bytes() != original:
                reconciler.atomic_write_bytes(path, original)


def prove_validator_chain(reconciler: Any) -> None:
    expected = [
        reconciler.OPERATIONS_VALIDATOR_PATH.resolve(),
        reconciler.RATE_LIMIT_VALIDATOR_PATH.resolve(),
        reconciler.OPERABILITY_VALIDATOR_PATH.resolve(),
        reconciler.ENTRY_DOCS_VALIDATOR_PATH.resolve(),
    ]
    observed: list[Path] = []
    original_run = reconciler.run_validator

    def capture(path: Path, _label: str) -> None:
        observed.append(path.resolve())

    try:
        reconciler.run_validator = capture
        reconciler.validate_written_authority()
    finally:
        reconciler.run_validator = original_run
    require(observed == expected,
            f"post-write validator chain drift: {observed!r} != {expected!r}")


def expect_substitution_rejection(
    reconciler: Any, attribute: str, substitute: Path, label: str
) -> None:
    original_attribute = getattr(reconciler, attribute)
    original_policy = CANONICAL_POLICY_PATH.read_bytes()
    original_status = CANONICAL_STATUS_PATH.read_bytes()
    setattr(reconciler, attribute, substitute)
    try:
        try:
            reconciler.main()
        except reconciler.ReconcileFailure as exc:
            message = str(exc)
            require(
                "authority drift" in message or "missing or escapes repository" in message,
                f"{label} rejected for unrelated reason: {message}",
            )
        else:
            raise NegativeFailure(
                f"rate-limit operations reconciler accepted authority substitution: {label}"
            )
        require(CANONICAL_POLICY_PATH.read_bytes() == original_policy,
                f"canonical policy mutated after authority substitution: {label}")
        require(CANONICAL_STATUS_PATH.read_bytes() == original_status,
                f"canonical status mutated after authority substitution: {label}")
    finally:
        setattr(reconciler, attribute, original_attribute)
        if CANONICAL_POLICY_PATH.read_bytes() != original_policy:
            reconciler.atomic_write_bytes(CANONICAL_POLICY_PATH, original_policy)
        if CANONICAL_STATUS_PATH.read_bytes() != original_status:
            reconciler.atomic_write_bytes(CANONICAL_STATUS_PATH, original_status)


def expect_execution_substitution_rejection(
    reconciler: Any, attribute: str, substitute: Any, expected: str
) -> None:
    original_attribute = getattr(reconciler, attribute)
    original_policy = CANONICAL_POLICY_PATH.read_bytes()
    original_status = CANONICAL_STATUS_PATH.read_bytes()
    setattr(reconciler, attribute, substitute)
    try:
        try:
            reconciler.main()
        except reconciler.ReconcileFailure as exc:
            require(expected in str(exc),
                    f"{attribute} rejected for unrelated reason: {exc}")
        else:
            raise NegativeFailure(
                f"rate-limit operations reconciler accepted execution substitution: {attribute}"
            )
        require(CANONICAL_POLICY_PATH.read_bytes() == original_policy,
                f"canonical policy mutated after execution substitution: {attribute}")
        require(CANONICAL_STATUS_PATH.read_bytes() == original_status,
                f"canonical status mutated after execution substitution: {attribute}")
    finally:
        setattr(reconciler, attribute, original_attribute)
        if CANONICAL_POLICY_PATH.read_bytes() != original_policy:
            reconciler.atomic_write_bytes(CANONICAL_POLICY_PATH, original_policy)
        if CANONICAL_STATUS_PATH.read_bytes() != original_status:
            reconciler.atomic_write_bytes(CANONICAL_STATUS_PATH, original_status)


def prove_execution_authority_identity(reconciler: Any) -> None:
    cases = (
        ("require", lambda *_args, **_kwargs: None, "require execution authority drift"),
        ("require_exact_repo_file", lambda path, *_args: path, "path checker execution authority drift"),
        ("enforce_runtime_authorities", lambda: None, "runtime guard execution authority drift"),
        ("load", lambda _path: {}, "loader execution authority drift"),
        ("append_once", lambda *_args: False, "append helper execution authority drift"),
        ("run_validator", lambda *_args: None, "validator runner execution authority drift"),
        ("validate_source_authority", lambda: None, "source validator execution authority drift"),
        ("validate_written_authority", lambda: None, "post-write validator execution authority drift"),
        ("atomic_write_bytes", lambda *_args: None, "atomic byte writer execution authority drift"),
        ("atomic_write_json", lambda *_args: None, "atomic JSON writer execution authority drift"),
        ("transactional_write", lambda *_args: None, "transaction writer execution authority drift"),
        ("enforce_execution_authorities", lambda: None, "execution guard authority drift"),
    )
    for attribute, substitute, expected in cases:
        expect_execution_substitution_rejection(reconciler, attribute, substitute, expected)

    original_run = reconciler.subprocess.run
    reconciler.subprocess.run = lambda *_args, **_kwargs: None
    try:
        try:
            reconciler.main()
        except reconciler.ReconcileFailure as exc:
            require("subprocess transport execution authority drift" in str(exc),
                    f"subprocess transport rejected for unrelated reason: {exc}")
        else:
            raise NegativeFailure("rate-limit operations reconciler accepted subprocess transport substitution")
    finally:
        reconciler.subprocess.run = original_run

    original_replace = reconciler.os.replace
    original_canonical_replace = reconciler.CANONICAL_OS_REPLACE
    fake_replace = lambda *_args, **_kwargs: None
    reconciler.os.replace = fake_replace
    reconciler.CANONICAL_OS_REPLACE = fake_replace
    try:
        try:
            reconciler.main()
        except reconciler.ReconcileFailure as exc:
            require("os.replace transport execution authority drift" in str(exc),
                    f"paired os.replace transport rejected for unrelated reason: {exc}")
        else:
            raise NegativeFailure("rate-limit operations reconciler accepted paired os.replace transport substitution")
    finally:
        reconciler.os.replace = original_replace
        reconciler.CANONICAL_OS_REPLACE = original_canonical_replace


def expect_operations_validator_rejection(
    validator: Any, attribute: str, substitute: Any, label: str
) -> None:
    original = getattr(validator, attribute)
    policy_before = CANONICAL_POLICY_PATH.read_bytes()
    status_before = CANONICAL_STATUS_PATH.read_bytes()
    setattr(validator, attribute, substitute)
    try:
        try:
            validator.main()
        except validator.ValidationFailure:
            pass
        else:
            raise NegativeFailure(
                f"rate-limit operations validator accepted authority substitution: {label}"
            )
        require(CANONICAL_POLICY_PATH.read_bytes() == policy_before,
                f"canonical policy mutated after validator substitution: {label}")
        require(CANONICAL_STATUS_PATH.read_bytes() == status_before,
                f"canonical status mutated after validator substitution: {label}")
    finally:
        setattr(validator, attribute, original)


def prove_operations_validator_runtime_authority() -> None:
    validator = load_operations_validator()
    require(validator.main() == 0,
            "canonical rate-limit operations validator does not pass before negatives")
    path_cases = (
        ("ROOT", ROOT / "contracts", "repository root"),
        ("POLICY_PATH", validator.STATUS_PATH, "policy contract"),
        ("OPERATIONS_PATH", validator.STATUS_PATH, "operations contract"),
        ("EVIDENCE_CONTRACT_PATH", validator.STATUS_PATH, "evidence contract"),
        ("STATUS_PATH", validator.POLICY_PATH, "Production Status"),
    )
    for attribute, substitute, label in path_cases:
        expect_operations_validator_rejection(validator, attribute, substitute, label)

    helper_cases = (
        ("require", lambda *_args, **_kwargs: None, "require helper"),
        ("load", lambda _path: {}, "JSON loader"),
        ("object_map", lambda *_args, **_kwargs: {}, "object-map helper"),
        ("unique_strings", lambda *_args, **_kwargs: ["x"] * 20, "unique-string helper"),
        ("canonical_repo_file", lambda path, *_args, **_kwargs: path, "path checker"),
        ("enforce_runtime_authorities", lambda: None, "runtime guard"),
        ("_main_impl", lambda: 0, "main implementation"),
    )
    for attribute, substitute, label in helper_cases:
        expect_operations_validator_rejection(validator, attribute, substitute, label)

    semantic_cases = (
        ("EXPECTED_MODES", {"NORMAL_CONFIGURED": True}, "operational modes"),
        ("EXPECTED_PROXY_MODES", {"TRUSTED_PROXY_CONFIGURED": True}, "proxy modes"),
        ("EXPECTED_TRANSITIONS", set(), "transition set"),
        ("BASE_EVIDENCE", set(), "base evidence set"),
        ("LEDGER_EVIDENCE", set(), "ledger evidence set"),
        ("REQUIRED_RUNBOOK_HEADINGS", tuple(), "runbook headings"),
    )
    for attribute, substitute, label in semantic_cases:
        expect_operations_validator_rejection(validator, attribute, substitute, label)

    original_defaults = validator.enforce_runtime_authorities.__defaults__
    validator.enforce_runtime_authorities.__defaults__ = tuple(original_defaults[:-1]) + (tuple(),)
    try:
        try:
            validator.main()
        except validator.ValidationFailure as exc:
            require("runtime guard default authority drift" in str(exc),
                    f"validator defaults rejected for unrelated reason: {exc}")
        else:
            raise NegativeFailure("rate-limit operations validator accepted runtime guard defaults drift")
    finally:
        validator.enforce_runtime_authorities.__defaults__ = original_defaults

    require(validator.main() == 0,
            "canonical rate-limit operations validator does not pass after negatives")


def main() -> int:
    reconciler = load_module()
    reconciler.enforce_runtime_authorities()
    reconciler.enforce_execution_authorities()
    prove_atomic_transport_and_mode(reconciler)
    prove_transaction_rollback(reconciler)
    prove_validator_chain(reconciler)
    cases = (
        ("OPERATIONS_VALIDATOR_PATH", reconciler.RATE_LIMIT_VALIDATOR_PATH, "operations validator"),
        ("RATE_LIMIT_VALIDATOR_PATH", reconciler.OPERABILITY_VALIDATOR_PATH, "rate-limit validator"),
        ("OPERABILITY_VALIDATOR_PATH", reconciler.RATE_LIMIT_VALIDATOR_PATH, "operability validator"),
        ("ENTRY_DOCS_VALIDATOR_PATH", reconciler.OPERABILITY_VALIDATOR_PATH, "entry docs validator"),
        ("POLICY_PATH", reconciler.STATUS_PATH, "policy contract path"),
        ("STATUS_PATH", reconciler.POLICY_PATH, "production status path"),
    )
    for attribute, substitute, label in cases:
        expect_substitution_rejection(reconciler, attribute, substitute, label)
    prove_execution_authority_identity(reconciler)
    prove_operations_validator_runtime_authority()

    print("PASS: rate-limit operations reconciler and standalone validator exact authorities, immutable transport, semantics, atomic publication and rollback are fail-closed")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
