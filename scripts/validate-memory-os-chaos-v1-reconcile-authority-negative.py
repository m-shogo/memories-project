#!/usr/bin/env python3
"""Reject repo-contained executable and data substitutions in chaos scenario reconcilers."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V1_RECONCILER = ROOT / "scripts/reconcile-memory-os-chaos-failure-drills.py"
V2_RECONCILER = ROOT / "scripts/reconcile-memory-os-chaos-failure-drills-v2.py"
PARSER_RECONCILER = ROOT / "scripts/reconcile-memory-os-parser-restart-matrix.py"
INFLIGHT_RECONCILER = ROOT / "scripts/reconcile-memory-os-parser-inflight-cancellation.py"
PROCESS_GROUP_RECONCILER = ROOT / "scripts/reconcile-memory-os-parser-process-group-reaping.py"
V1_VALIDATOR = ROOT / "scripts/validate-memory-os-chaos-failure-drills.py"
V2_VALIDATOR = ROOT / "scripts/validate-memory-os-chaos-failure-drills-v2.py"
PARSER_VALIDATOR = ROOT / "scripts/validate-memory-os-parser-restart-matrix.py"
INFLIGHT_VALIDATOR = ROOT / "scripts/validate-memory-os-parser-inflight-cancellation.py"
PROCESS_GROUP_VALIDATOR = ROOT / "scripts/validate-memory-os-parser-process-group-reaping.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load chaos reconciler: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejection(callback, expected: str) -> None:
    try:
        callback()
    except Exception as exc:
        if expected not in str(exc):
            raise RuntimeError(f"unexpected authority rejection: {exc}") from exc
    else:
        raise RuntimeError(f"chaos reconciler accepted substituted authority: {expected}")


def validate_data_authority(module) -> None:
    guard = getattr(module, "enforce_data_authorities", None)
    if not callable(guard):
        return
    original_result = module.RESULT_PATH
    original_status = module.STATUS_PATH
    try:
        module.RESULT_PATH = ROOT / "README.md"
        module.STATUS_PATH = ROOT / "SECURITY.md"
        expect_rejection(guard, "fixture must remain outside repository")
    finally:
        module.RESULT_PATH = original_result
        module.STATUS_PATH = original_status


def validate_module(
    module,
    *,
    validator_attr: str,
    validator_substitute: Path,
    validator_error: str,
    reconciler_substitute: Path,
) -> None:
    source_sha = "0" * 40

    original_validator = getattr(module, validator_attr)
    try:
        setattr(module, validator_attr, validator_substitute)
        expect_rejection(
            lambda: module.validate_authority_chain(source_sha),
            validator_error,
        )
    finally:
        setattr(module, validator_attr, original_validator)

    original_operability = module.OPERABILITY_VALIDATOR
    try:
        module.OPERABILITY_VALIDATOR = validator_substitute
        expect_rejection(
            lambda: module.validate_authority_chain(source_sha),
            "operability validator authority drift",
        )
    finally:
        module.OPERABILITY_VALIDATOR = original_operability

    original_reconciler = module.CANONICAL_RECONCILER
    try:
        module.CANONICAL_RECONCILER = reconciler_substitute
        expect_rejection(
            module.load_canonical_normalizer,
            "chaos authority reconciler authority drift",
        )
    finally:
        module.CANONICAL_RECONCILER = original_reconciler

    validate_data_authority(module)


def validate_inflight(module) -> None:
    substitutions = (
        ("INFLIGHT_VALIDATOR", V1_VALIDATOR, "in-flight validator authority drift"),
        ("OPERABILITY_VALIDATOR", V1_VALIDATOR, "operability validator authority drift"),
        ("CANONICAL_RECONCILER", V1_VALIDATOR, "chaos authority reconciler authority drift"),
        ("CANONICAL_OVERLAY", V1_VALIDATOR, "chaos in-flight overlay authority drift"),
    )
    for attr, substitute, expected in substitutions:
        original = getattr(module, attr)
        try:
            setattr(module, attr, substitute)
            expect_rejection(module.validate_executable_authorities, expected)
        finally:
            setattr(module, attr, original)
    validate_data_authority(module)


def validate_process_group(module) -> None:
    source_sha = "0" * 40
    for attr, substitute, expected in (
        ("PROCESS_GROUP_VALIDATOR", V1_VALIDATOR, "process-group validator authority drift"),
        ("OPERABILITY_VALIDATOR", V1_VALIDATOR, "operability validator authority drift"),
    ):
        original = getattr(module, attr)
        try:
            setattr(module, attr, substitute)
            expect_rejection(lambda: module.run_authority_validators(source_sha), expected)
        finally:
            setattr(module, attr, original)


def main() -> int:
    fixtures = (
        V1_RECONCILER,
        V2_RECONCILER,
        PARSER_RECONCILER,
        INFLIGHT_RECONCILER,
        PROCESS_GROUP_RECONCILER,
        V1_VALIDATOR,
        V2_VALIDATOR,
        PARSER_VALIDATOR,
        INFLIGHT_VALIDATOR,
        PROCESS_GROUP_VALIDATOR,
    )
    for path in fixtures:
        if not path.is_file():
            raise RuntimeError(f"authority fixture missing: {path.name}")

    v1 = load_module(V1_RECONCILER, "memory_os_chaos_v1_authority_negative")
    validate_module(
        v1,
        validator_attr="V1_VALIDATOR",
        validator_substitute=V2_VALIDATOR,
        validator_error="v1 failure-drill validator authority drift",
        reconciler_substitute=V2_VALIDATOR,
    )
    v2 = load_module(V2_RECONCILER, "memory_os_chaos_v2_authority_negative")
    validate_module(
        v2,
        validator_attr="V2_VALIDATOR",
        validator_substitute=V1_VALIDATOR,
        validator_error="v2 failure-drill validator authority drift",
        reconciler_substitute=V1_VALIDATOR,
    )
    parser = load_module(PARSER_RECONCILER, "memory_os_parser_restart_authority_negative")
    validate_module(
        parser,
        validator_attr="PARSER_VALIDATOR",
        validator_substitute=V1_VALIDATOR,
        validator_error="parser restart validator authority drift",
        reconciler_substitute=V1_VALIDATOR,
    )
    validate_inflight(
        load_module(INFLIGHT_RECONCILER, "memory_os_parser_inflight_authority_negative")
    )
    validate_process_group(
        load_module(PROCESS_GROUP_RECONCILER, "memory_os_process_group_authority_negative")
    )

    print("PASS: chaos scenario reconcile executable/data substitutions are rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
