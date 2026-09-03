#!/usr/bin/env python3
"""Prove observability access reconcile authority and rollback boundaries fail closed."""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
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


def expect_rejected(module, field: str, substitute) -> None:
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


def expect_authority_identity(module, original_event: bytes, original_status: bytes) -> None:
    module.enforce_runtime_authorities()
    substitutions = (
        ("EVENT_PATH", ROOT / "contracts/operations/observability-retention-access-contract.v1.json"),
        ("ACCESS_PATH", ROOT / "contracts/operations/observability-event-contract.v1.json"),
        ("STATUS_PATH", EVENT),
        ("OBSERVABILITY_VALIDATOR", ROOT / "scripts/validate-memory-os-observability-access.py"),
        ("VALIDATOR", ROOT / "scripts/validate-memory-os-observability.py"),
        ("OPERABILITY_VALIDATOR", ROOT / "scripts/validate-memory-os-entry-docs.py"),
        ("ENTRY_DOCS_VALIDATOR", ROOT / "scripts/validate-memory-os-operability.py"),
        ("WORKFLOW", ROOT / ".github/workflows/observability-stack-deployment.yml"),
    )
    for field, substitute in substitutions:
        expect_rejected(module, field, substitute)

    original_chain = module.POST_WRITE_VALIDATORS
    try:
        module.POST_WRITE_VALIDATORS = (module.VALIDATOR,)
        rejected = False
        try:
            module.enforce_runtime_authorities()
        except module.ReconcileFailure:
            rejected = True
        if not rejected:
            raise RuntimeError("reconciler accepted post-write validator-chain substitution")
    finally:
        module.POST_WRITE_VALIDATORS = original_chain

    original_run = module.subprocess.run
    try:
        module.subprocess.run = lambda *args, **kwargs: None
        rejected = False
        try:
            module.enforce_runtime_authorities()
        except module.ReconcileFailure:
            rejected = True
        if not rejected:
            raise RuntimeError("reconciler accepted subprocess transport substitution")
    finally:
        module.subprocess.run = original_run

    original_replace = module.os.replace
    try:
        module.os.replace = lambda *args, **kwargs: None
        rejected = False
        try:
            module.enforce_runtime_authorities()
        except module.ReconcileFailure:
            rejected = True
        if not rejected:
            raise RuntimeError("reconciler accepted atomic replacement transport substitution")
    finally:
        module.os.replace = original_replace

    original_atomic_writer = module.atomic_write_bytes
    try:
        module.atomic_write_bytes = lambda *args, **kwargs: None
        rejected = False
        try:
            module.enforce_runtime_authorities()
        except module.ReconcileFailure:
            rejected = True
        if not rejected:
            raise RuntimeError("reconciler accepted atomic writer substitution")
    finally:
        module.atomic_write_bytes = original_atomic_writer

    module.enforce_runtime_authorities()
    if EVENT.read_bytes() != original_event:
        raise RuntimeError("authority substitution mutated observability event contract")
    if STATUS.read_bytes() != original_status:
        raise RuntimeError("authority substitution mutated production operability status")


def expect_atomic_replace_failure(module, original_event: bytes) -> None:
    original_mode = stat.S_IMODE(EVENT.stat().st_mode)
    before_temps = set(EVENT.parent.glob(f".{EVENT.name}.*.tmp"))
    original_replace = module.os.replace

    def fail_replace(*_args, **_kwargs):
        raise OSError("synthetic observability access replacement failure")

    try:
        module.os.replace = fail_replace
        rejected = False
        try:
            module.CANONICAL_ATOMIC_WRITE_BYTES(EVENT, original_event + b" ")
        except OSError:
            rejected = True
        if not rejected:
            raise RuntimeError("atomic writer accepted synthetic replacement failure")
    finally:
        module.os.replace = original_replace

    if EVENT.read_bytes() != original_event:
        raise RuntimeError("atomic replacement failure mutated observability event contract")
    if stat.S_IMODE(EVENT.stat().st_mode) != original_mode:
        raise RuntimeError("atomic replacement failure changed observability event mode")
    after_temps = set(EVENT.parent.glob(f".{EVENT.name}.*.tmp"))
    if after_temps != before_temps:
        raise RuntimeError("atomic replacement failure left observability temporary residue")


def expect_access_post_write_rollback() -> None:
    canonical_event = EVENT.read_bytes()
    canonical_status = STATUS.read_bytes()
    event_mode = stat.S_IMODE(EVENT.stat().st_mode)
    status_mode = stat.S_IMODE(STATUS.stat().st_mode)
    validator_bytes = VALIDATOR.read_bytes()
    validator_mode = stat.S_IMODE(VALIDATOR.stat().st_mode)

    event = json.loads(canonical_event.decode("utf-8"))
    retention = event.get("retention")
    if not isinstance(retention, dict):
        raise RuntimeError("observability event retention authority missing")
    retention["note"] = "negative fixture: force deterministic reconcile"
    EVENT.write_text(json.dumps(event, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.chmod(EVENT, event_mode)
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
        os.chmod(VALIDATOR, validator_mode)
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
        if stat.S_IMODE(EVENT.stat().st_mode) != event_mode:
            raise RuntimeError("access rollback changed observability event mode")
        if stat.S_IMODE(STATUS.stat().st_mode) != status_mode:
            raise RuntimeError("access rollback changed production status mode")
    finally:
        VALIDATOR.write_bytes(validator_bytes)
        os.chmod(VALIDATOR, validator_mode)
        EVENT.write_bytes(canonical_event)
        os.chmod(EVENT, event_mode)
        STATUS.write_bytes(canonical_status)
        os.chmod(STATUS, status_mode)
        MARKER.unlink(missing_ok=True)


def expect_aggregate_post_write_rollback(module) -> None:
    canonical_event = EVENT.read_bytes()
    canonical_status = STATUS.read_bytes()
    event_mode = stat.S_IMODE(EVENT.stat().st_mode)
    status_mode = stat.S_IMODE(STATUS.stat().st_mode)
    event = json.loads(canonical_event.decode("utf-8"))
    status = json.loads(canonical_status.decode("utf-8"))
    event["rollbackProbe"] = "must-not-persist"
    status["rollbackProbe"] = "must-not-persist"

    validator_path = module.OPERABILITY_VALIDATOR
    validator_bytes = validator_path.read_bytes()
    validator_mode = stat.S_IMODE(validator_path.stat().st_mode)
    try:
        validator_path.write_text("raise SystemExit(1)\n", encoding="utf-8")
        os.chmod(validator_path, validator_mode)
        rejected = False
        try:
            module.commit_validated_pair(event, status)
        except module.ReconcileFailure as exc:
            if "failed validation" not in str(exc):
                raise RuntimeError(f"unexpected aggregate rejection: {exc}") from exc
            rejected = True
        if not rejected:
            raise RuntimeError("reconciler accepted injected aggregate post-write validator failure")
    finally:
        validator_path.write_bytes(validator_bytes)
        os.chmod(validator_path, validator_mode)

    if EVENT.read_bytes() != canonical_event:
        raise RuntimeError("aggregate failure left observability event authority mutated")
    if STATUS.read_bytes() != canonical_status:
        raise RuntimeError("aggregate failure left production operability status mutated")
    if stat.S_IMODE(EVENT.stat().st_mode) != event_mode:
        raise RuntimeError("aggregate rollback changed observability event mode")
    if stat.S_IMODE(STATUS.stat().st_mode) != status_mode:
        raise RuntimeError("aggregate rollback changed production status mode")
    if list(EVENT.parent.glob(f".{EVENT.name}.*.tmp")):
        raise RuntimeError("aggregate rollback left observability event temporary residue")
    if list(STATUS.parent.glob(f".{STATUS.name}.*.tmp")):
        raise RuntimeError("aggregate rollback left production status temporary residue")


def main() -> int:
    module = load_reconciler()
    canonical_event = EVENT.read_bytes()
    canonical_status = STATUS.read_bytes()
    expect_authority_identity(module, canonical_event, canonical_status)
    expect_atomic_replace_failure(module, canonical_event)
    expect_access_post_write_rollback()
    expect_aggregate_post_write_rollback(module)
    print("PASS: observability access reconcile data/executable, chain and transport authorities reject substitution")
    print("PASS: observability access atomic replacement failure preserves bytes, mode and temp cleanliness")
    print("PASS: observability access post-write and aggregate validation failures atomically roll back event and status")
    print("productionDecision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
