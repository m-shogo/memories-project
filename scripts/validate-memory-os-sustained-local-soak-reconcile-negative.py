#!/usr/bin/env python3
"""Prove sustained-soak authority identity and multi-authority rollback are fail-closed."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-sustained-local-soak-status.py"
WORKFLOW = ROOT / ".github/workflows/reconcile-sustained-local-soak-authority.yml"


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_sustained_local_soak_reconciler", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load sustained local soak reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def validate_atomic_authority_diagnostic() -> None:
    if not WORKFLOW.is_file():
        raise AssertionError("sustained soak authority workflow missing")
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
    if missing:
        raise AssertionError(f"sustained soak authority diagnostic is not crash-safe: missing {missing}")
    if "path.write_text(json.dumps(value" in text:
        raise AssertionError("sustained soak authority diagnostic regressed to direct write_text")


def main() -> int:
    module = load_reconciler()
    validate_atomic_authority_diagnostic()
    paths = (module.CONTRACT_PATH, module.LOAD_PATH, module.STATUS_PATH)
    original = {path: path.read_bytes() for path in paths}

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
        if path.read_bytes() != original[path]:
            raise AssertionError(f"authority substitution changed canonical bytes: {path.relative_to(ROOT)}")

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
            if path.read_bytes() != original[path]:
                raise AssertionError(f"reconcile rollback changed canonical authority: {path.relative_to(ROOT)}")
    finally:
        module.run_validator = real_run_validator
        for path in paths:
            if path.read_bytes() != original[path]:
                path.write_bytes(original[path])

    print("PASS: sustained local soak authority diagnostic is atomic and crash-safe")
    print("PASS: sustained local soak authority identity and reconcile rollback are fail-closed")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
