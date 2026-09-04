#!/usr/bin/env python3
"""Prove sustained-soak authority identity and multi-authority rollback are fail-closed."""

from __future__ import annotations

import importlib.util
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-sustained-local-soak-status.py"
AGGREGATE_UPDATER = ROOT / "scripts/update-memory-os-sustained-local-soak-aggregate.py"
TREND_REVIEWER = ROOT / "scripts/review-memory-os-sustained-local-soak-trends.py"
WORKFLOW = ROOT / ".github/workflows/reconcile-sustained-local-soak-authority.yml"
MAIN_WORKFLOW = ROOT / ".github/workflows/sustained-local-soak.yml"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_reconciler():
    return load_module(RECONCILER, "memory_os_sustained_local_soak_reconciler")


def load_aggregate_updater():
    return load_module(AGGREGATE_UPDATER, "memory_os_sustained_local_soak_aggregate_updater")


def load_trend_reviewer():
    return load_module(TREND_REVIEWER, "memory_os_sustained_local_soak_trend_reviewer")


def file_mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def expect_authority_rejection(module, attr: str, replacement: Path) -> None:
    original = getattr(module, attr)
    setattr(module, attr, replacement)
    try:
        try:
            module.enforce_runtime_authorities()
        except module.Fail:
            pass
        else:
            raise AssertionError(f"{attr} substitution must be rejected")
    finally:
        setattr(module, attr, original)


def validate_atomic_diagnostic_workflow(path: Path, label: str) -> None:
    if not path.is_file():
        raise AssertionError(f"{label} workflow missing")
    text = path.read_text(encoding="utf-8")
    required = (
        "tempfile.mkstemp(",
        "dir=path.parent",
        "handle.flush()",
        "os.fsync(handle.fileno())",
        "os.replace(tmp_name, path)",
        "os.unlink(tmp_name)",
    )
    missing = [fragment for fragment in required if fragment not in text]
    if missing:
        raise AssertionError(f"{label} diagnostic is not crash-safe: missing {missing}")
    if "path.write_text(json.dumps(value" in text:
        raise AssertionError(f"{label} diagnostic regressed to direct write_text")


def validate_atomic_writer(module, path: Path, label: str) -> None:
    original = path.read_bytes()
    original_mode = file_mode(path)
    temp_glob = f".{path.name}.*.tmp"
    before = {candidate.name for candidate in path.parent.glob(temp_glob)}
    real_replace = module.os.replace

    def fail_replace(_source, _destination) -> None:
        raise OSError("synthetic atomic replace failure")

    module.os.replace = fail_replace
    try:
        try:
            module.atomic_replace_bytes(path, original + b"\n")
        except OSError as exc:
            if "synthetic atomic replace failure" not in str(exc):
                raise AssertionError(f"unexpected atomic write failure: {exc}") from exc
        else:
            raise AssertionError(f"{label} atomic writer unexpectedly succeeded after replace failure")
    finally:
        module.os.replace = real_replace

    if path.read_bytes() != original:
        raise AssertionError(f"atomic replace failure changed canonical {label}")
    if file_mode(path) != original_mode:
        raise AssertionError(f"atomic replace failure changed canonical {label} mode")
    after = {candidate.name for candidate in path.parent.glob(temp_glob)}
    if after != before:
        raise AssertionError(f"atomic replace failure leaked temporary {label} authority")


def validate_mode_preserving_success(module, path: Path, label: str) -> None:
    original = path.read_bytes()
    original_mode = file_mode(path)
    test_mode = 0o640
    path.chmod(test_mode)
    try:
        module.atomic_replace_bytes(path, original)
        if path.read_bytes() != original:
            raise AssertionError(f"successful atomic replacement changed canonical {label} bytes")
        if file_mode(path) != test_mode:
            raise AssertionError(f"successful atomic replacement changed canonical {label} mode")
    finally:
        path.chmod(original_mode)
        if path.read_bytes() != original:
            module.atomic_replace_bytes(path, original, original_mode)


def main() -> int:
    module = load_reconciler()
    updater = load_aggregate_updater()
    reviewer = load_trend_reviewer()
    validate_atomic_diagnostic_workflow(WORKFLOW, "sustained soak authority")
    validate_atomic_diagnostic_workflow(MAIN_WORKFLOW, "sustained soak execution")
    validate_atomic_writer(module, module.CONTRACT_PATH, "sustained-soak contract")
    validate_mode_preserving_success(module, module.CONTRACT_PATH, "sustained-soak contract")
    validate_atomic_writer(updater, updater.AGGREGATE_PATH, "sustained-soak aggregate")
    validate_mode_preserving_success(updater, updater.AGGREGATE_PATH, "sustained-soak aggregate")
    validate_atomic_writer(reviewer, reviewer.REVIEW_PATH, "sustained-soak trend review")
    validate_mode_preserving_success(reviewer, reviewer.REVIEW_PATH, "sustained-soak trend review")

    expect_authority_rejection(updater, "RESULT_DIR", updater.ROOT / "docs")
    expect_authority_rejection(updater, "AGGREGATE_PATH", updater.CONTRACT_PATH)
    expect_authority_rejection(updater, "REVIEW_PATH", updater.CONTRACT_PATH)
    expect_authority_rejection(updater, "CONTRACT_PATH", updater.AGGREGATE_PATH)
    expect_authority_rejection(updater, "RESULT_VALIDATOR", updater.REVIEW_VALIDATOR)
    expect_authority_rejection(updater, "REVIEW_VALIDATOR", updater.RESULT_VALIDATOR)

    expect_authority_rejection(reviewer, "RESULT_DIR", reviewer.ROOT / "docs")
    expect_authority_rejection(reviewer, "CONTRACT_PATH", reviewer.REVIEW_PATH)
    expect_authority_rejection(reviewer, "RESULT_VALIDATOR", reviewer.CONTRACT_PATH)
    expect_authority_rejection(reviewer, "REVIEW_PATH", reviewer.CONTRACT_PATH)

    paths = (module.CONTRACT_PATH, module.LOAD_PATH, module.STATUS_PATH)
    original = {
        path: (path.read_bytes(), file_mode(path))
        for path in paths
    }

    expect_authority_rejection(module, "CONTRACT_PATH", module.LOAD_PATH)
    expect_authority_rejection(module, "LOAD_PATH", module.STATUS_PATH)
    expect_authority_rejection(module, "STATUS_PATH", module.CONTRACT_PATH)
    expect_authority_rejection(module, "RESULT_DIR", module.ROOT / "docs")
    expect_authority_rejection(module, "AGGREGATE_PATH", module.CONTRACT_PATH)
    expect_authority_rejection(module, "REVIEW_PATH", module.LOAD_PATH)
    expect_authority_rejection(module, "AGGREGATE_VALIDATOR", module.SOAK_VALIDATOR)
    expect_authority_rejection(module, "INDEPENDENT_REVIEW_VALIDATOR", module.LOAD_VALIDATOR)
    expect_authority_rejection(module, "SOAK_VALIDATOR", module.LOAD_VALIDATOR)
    expect_authority_rejection(module, "LOAD_VALIDATOR", module.SOAK_VALIDATOR)
    expect_authority_rejection(module, "OPERABILITY_VALIDATOR", module.SOAK_VALIDATOR)

    for path in paths:
        original_bytes, original_mode = original[path]
        if path.read_bytes() != original_bytes:
            raise AssertionError(f"authority substitution changed canonical bytes: {path.relative_to(ROOT)}")
        if file_mode(path) != original_mode:
            raise AssertionError(f"authority substitution changed canonical mode: {path.relative_to(ROOT)}")

    observed_post_write_failure = False
    real_run_validator = module.run_validator

    def controlled_validator(path: Path, label: str, *args: str) -> None:
        nonlocal observed_post_write_failure
        if label == "post-write operability validator":
            observed_post_write_failure = True
            raise module.Fail("synthetic post-write operability validation failure")
        real_run_validator(path, label, *args)

    module.run_validator = controlled_validator
    try:
        try:
            module.main()
        except module.Fail as exc:
            if "synthetic post-write operability validation failure" not in str(exc):
                raise AssertionError(f"unexpected reconcile failure: {exc}") from exc
        else:
            raise AssertionError("reconcile unexpectedly succeeded after synthetic post-write failure")

        if not observed_post_write_failure:
            raise AssertionError("synthetic post-write validator was not reached")
        for path in paths:
            original_bytes, original_mode = original[path]
            if path.read_bytes() != original_bytes:
                raise AssertionError(f"reconcile rollback changed canonical authority: {path.relative_to(ROOT)}")
            if file_mode(path) != original_mode:
                raise AssertionError(f"reconcile rollback changed canonical authority mode: {path.relative_to(ROOT)}")
    finally:
        module.run_validator = real_run_validator
        for path in paths:
            original_bytes, original_mode = original[path]
            if path.read_bytes() != original_bytes or file_mode(path) != original_mode:
                module.atomic_replace_bytes(path, original_bytes, original_mode)

    print("PASS: sustained local soak execution and authority diagnostics are atomic and crash-safe")
    print("PASS: sustained local soak reconciler, aggregate updater and trend reviewer reject authority substitution")
    print("PASS: sustained local soak atomic replacement failure preserves canonical authority bytes and mode")
    print("PASS: sustained local soak derived authority writers preserve existing mode")
    print("PASS: sustained local soak reconcile rollback preserves canonical authority bytes and mode")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
