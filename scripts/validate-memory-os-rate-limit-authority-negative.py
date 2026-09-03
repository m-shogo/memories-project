#!/usr/bin/env python3
"""Prove the aggregate rate-limit validator cannot substitute its canonical authorities."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-rate-limit.py"
POLICY_PATH = ROOT / "contracts/operations/rate-limit-policy-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "memory_os_rate_limit_authority_negative", VALIDATOR_PATH
    )
    require(spec is not None and spec.loader is not None, "cannot load aggregate rate-limit validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_main_rejection(module: Any, label: str) -> None:
    before_policy = POLICY_PATH.read_bytes()
    before_status = STATUS_PATH.read_bytes()
    rc = module.main()
    require(rc != 0, f"aggregate rate-limit validator accepted authority substitution: {label}")
    require(POLICY_PATH.read_bytes() == before_policy,
            f"canonical rate-limit policy mutated after rejected substitution: {label}")
    require(STATUS_PATH.read_bytes() == before_status,
            f"canonical Production Status mutated after rejected substitution: {label}")


def expect_main_call_rejection(module: Any, label: str, **kwargs: Any) -> None:
    before_policy = POLICY_PATH.read_bytes()
    before_status = STATUS_PATH.read_bytes()
    rc = module.main(**kwargs)
    require(rc != 0, f"aggregate rate-limit validator accepted direct call substitution: {label}")
    require(POLICY_PATH.read_bytes() == before_policy,
            f"canonical rate-limit policy mutated after rejected direct call substitution: {label}")
    require(STATUS_PATH.read_bytes() == before_status,
            f"canonical Production Status mutated after rejected direct call substitution: {label}")


def prove_path_authorities(module: Any) -> None:
    cases = (
        ("REPO", ROOT / "contracts", "repository root"),
        ("CONTRACT", module.STATUS, "rate-limit contract"),
        ("NEGATIVE", module.STATUS, "negative fixture"),
        ("STATUS", module.CONTRACT, "Production Status"),
        ("ENFORCE_GO", module.OBSLOG_CODES, "rate-limit Go source"),
        ("OBSLOG_CODES", module.ENFORCE_GO, "observability code source"),
    )
    for attribute, substitute, label in cases:
        original = getattr(module, attribute)
        setattr(module, attribute, substitute)
        try:
            expect_main_rejection(module, label)
        finally:
            setattr(module, attribute, original)


def prove_paired_default_substitution(module: Any) -> None:
    cases = (
        ("CONTRACT", "DEFAULT_CONTRACT", module.STATUS, "paired contract/default contract"),
        ("NEGATIVE", "DEFAULT_NEGATIVE", module.STATUS, "paired negative/default negative"),
        ("STATUS", "DEFAULT_STATUS", module.CONTRACT, "paired status/default status"),
        ("ENFORCE_GO", "DEFAULT_ENFORCE_GO", module.OBSLOG_CODES, "paired Go source/default Go source"),
        ("OBSLOG_CODES", "DEFAULT_OBSLOG_CODES", module.ENFORCE_GO, "paired obslog/default obslog"),
    )
    for current_attr, default_attr, substitute, label in cases:
        original_current = getattr(module, current_attr)
        original_default = getattr(module, default_attr)
        setattr(module, current_attr, substitute)
        setattr(module, default_attr, substitute)
        try:
            expect_main_rejection(module, label)
        finally:
            setattr(module, current_attr, original_current)
            setattr(module, default_attr, original_default)


def prove_execution_authorities(module: Any) -> None:
    cases = (
        ("load", lambda _path: {}, "JSON loader"),
        ("go_consts", lambda *_args: set(), "Go constant parser"),
        ("check_policy_set", lambda *_args: [], "policy-set checker"),
        ("canonical_repo_file", lambda path, *_args, **_kwargs: path, "path checker"),
        ("enforce_runtime_authorities", lambda: None, "runtime guard"),
    )
    for attribute, substitute, label in cases:
        original = getattr(module, attribute)
        setattr(module, attribute, substitute)
        try:
            expect_main_rejection(module, label)
        finally:
            setattr(module, attribute, original)


def prove_direct_call_authorities(module: Any) -> None:
    expect_main_call_rejection(module, "runtime guard argument", _runtime_guard=lambda: None)
    expect_main_call_rejection(module, "JSON loader argument", _load=lambda _path: {})
    expect_main_call_rejection(module, "Go constant parser argument", _go_consts=lambda *_args: set())
    expect_main_call_rejection(module, "policy-set checker argument", _check_policy_set=lambda *_args: [])


def prove_policy_bound_authorities(module: Any) -> None:
    cases = (
        ("MAX_CAPACITY", "DEFAULT_MAX_CAPACITY", 10**18, "paired maximum capacity"),
        ("MAX_REFILL", "DEFAULT_MAX_REFILL", 10**18, "paired maximum refill"),
    )
    for current_attr, default_attr, substitute, label in cases:
        original_current = getattr(module, current_attr)
        original_default = getattr(module, default_attr)
        setattr(module, current_attr, substitute)
        setattr(module, default_attr, substitute)
        try:
            expect_main_rejection(module, label)
        finally:
            setattr(module, current_attr, original_current)
            setattr(module, default_attr, original_default)


def main() -> int:
    module = load_module()
    require(module.main() == 0, "canonical aggregate rate-limit validator does not pass before negatives")
    prove_path_authorities(module)
    prove_paired_default_substitution(module)
    prove_execution_authorities(module)
    prove_direct_call_authorities(module)
    prove_policy_bound_authorities(module)
    require(module.main() == 0, "canonical aggregate rate-limit validator does not pass after negatives")

    print("PASS: aggregate rate-limit validator data, helper, direct-call, policy-bound and paired default authorities are fail-closed")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
