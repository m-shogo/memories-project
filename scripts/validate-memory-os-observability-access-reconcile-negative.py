#!/usr/bin/env python3
"""Prove observability access reconcile authority and rollback boundaries fail closed."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "contracts/operations/observability-event-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-observability-access.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-observability-access.py"
MARKER = Path("/tmp/memory-os-observability-access-post-write-negative.count")


def load_reconciler():
    spec = importlib.util.spec_from_file_location("observability_access_reconciler", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load observability access reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_authority_identity(module) -> None:
    module.enforce_runtime_authorities()
    substitutions = (
        ("EVENT_PATH", ROOT / "contracts/operations/observability-retention-access-contract.v1.json"),
        ("ACCESS_PATH", ROOT / "contracts/operations/observability-event-contract.v1.json"),
        ("OBSERVABILITY_VALIDATOR", ROOT / "scripts/validate-memory-os-observability-access.py"),
        ("VALIDATOR", ROOT / "scripts/validate-memory-os-observability.py"),
        ("OPERABILITY_VALIDATOR", ROOT / "scripts/validate-memory-os-entry-docs.py"),
        ("ENTRY_DOCS_VALIDATOR", ROOT / "scripts/validate-memory-os-operability.py"),
        ("WORKFLOW", ROOT / ".github/workflows/observability-stack-deployment.yml"),
    )
    for field, substitute in substitutions:
        original = getattr(module, field)
        try:
            setattr(module, field, substitute)
            rejected = False
            try:
                module.enforce_runtime_authorities()
            except module.ReconcileFailure:
                rejected = True
            if not rejected:
                raise RuntimeError(f"reconciler accepted {field} authority substitution")
        finally:
            setattr(module, field, original)
    module.enforce_runtime_authorities()


def expect_access_post_write_rollback() -> None:
    canonical_event = EVENT.read_bytes()
    canonical_status = STATUS.read_bytes()
    validator_bytes = VALIDATOR.read_bytes()

    event = json.loads(canonical_event.decode("utf-8"))
    retention = event.get("retention")
    if not isinstance(retention, dict):
        raise RuntimeError("observability event retention authority missing")
    retention["note"] = "negative fixture: force deterministic reconcile"
    EVENT.write_text(json.dumps(event, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    input_event = EVENT.read_bytes()
    input_status = STATUS.read_bytes()

    wrapper = f'''#!/usr/bin/env python3
from pathlib import Path
marker = Path({str(MARKER)!r})
count = int(marker.read_text(encoding="utf-8")) if marker.exists() else 0
marker.write_text(str(count + 1), encoding="utf-8")
raise SystemExit(0 if count == 0 else 1)
'''

    try:
        MARKER.unlink(missing_ok=True)
        VALIDATOR.write_text(wrapper, encoding="utf-8")
        completed = subprocess.run(
            ["python", str(RECONCILER)],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if completed.returncode == 0:
            raise RuntimeError("reconciler accepted injected access post-write validator failure")
        if EVENT.read_bytes() != input_event:
            raise RuntimeError("access post-write failure left observability event authority mutated")
        if STATUS.read_bytes() != input_status:
            raise RuntimeError("access post-write failure left production operability status mutated")
    finally:
        VALIDATOR.write_bytes(validator_bytes)
        EVENT.write_bytes(canonical_event)
        STATUS.write_bytes(canonical_status)
        MARKER.unlink(missing_ok=True)


def expect_aggregate_post_write_rollback(module) -> None:
    canonical_event = EVENT.read_bytes()
    canonical_status = STATUS.read_bytes()
    event = json.loads(canonical_event.decode("utf-8"))
    status = json.loads(canonical_status.decode("utf-8"))
    event["rollbackProbe"] = "must-not-persist"
    status["rollbackProbe"] = "must-not-persist"

    original_validators = module.POST_WRITE_VALIDATORS
    with tempfile.TemporaryDirectory(prefix="observability-access-negative-") as tmp:
        tmp_path = Path(tmp)
        pass_validator = tmp_path / "pass.py"
        fail_validator = tmp_path / "fail.py"
        pass_validator.write_text("raise SystemExit(0)\n", encoding="utf-8")
        fail_validator.write_text("raise SystemExit(1)\n", encoding="utf-8")
        module.POST_WRITE_VALIDATORS = (pass_validator, pass_validator, fail_validator)
        rejected = False
        try:
            module.commit_validated_pair(event, status)
        except module.ReconcileFailure as exc:
            if "failed validation" not in str(exc):
                raise RuntimeError(f"unexpected aggregate rejection: {exc}") from exc
            rejected = True
        finally:
            module.POST_WRITE_VALIDATORS = original_validators
    if not rejected:
        raise RuntimeError("reconciler accepted injected aggregate post-write validator failure")
    if EVENT.read_bytes() != canonical_event:
        raise RuntimeError("aggregate failure left observability event authority mutated")
    if STATUS.read_bytes() != canonical_status:
        raise RuntimeError("aggregate failure left production operability status mutated")


def main() -> int:
    module = load_reconciler()
    expect_authority_identity(module)
    expect_access_post_write_rollback()
    expect_aggregate_post_write_rollback(module)
    print("PASS: observability access reconcile executable authorities reject substitution")
    print("PASS: observability access post-write and aggregate validation failures roll back event and status")
    print("productionDecision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
