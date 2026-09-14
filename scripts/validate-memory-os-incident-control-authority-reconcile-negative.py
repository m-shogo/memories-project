#!/usr/bin/env python3
"""Reject unsafe incident authority normalization without mutating canonical authorities."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-incident-control-authority.py"
CONTRACT_PATH = ROOT / "contracts/operations/incident-control-exercise-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/incident-control-exercise-results.sample.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
UNPROVEN_READINESS = (
    "humanTabletopCompleted",
    "pagingAndAcknowledgementExercised",
    "externalContactTreeExercised",
    "productionRecoveryDrillCompleted",
    "independentReviewCompleted",
    "productionReady",
)


def load_module():
    spec = importlib.util.spec_from_file_location("incident_control_authority_reconciler", RECONCILER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load incident control authority reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_runtime_authority_rejected(reconciler, field: str, substitute) -> None:
    original = getattr(reconciler, field)
    try:
        setattr(reconciler, field, substitute)
        try:
            reconciler.enforce_runtime_authorities()
        except reconciler.ReconcileFailure:
            return
        raise RuntimeError(f"reconciler accepted {field} authority substitution")
    finally:
        setattr(reconciler, field, original)


def verify_runtime_authority_identity(reconciler, original_contract: bytes, original_result: bytes, original_status: bytes) -> None:
    reconciler.enforce_runtime_authorities()
    substitutions = (
        ("CONTRACT_PATH", ROOT / "README.md"),
        ("RESULT_PATH", ROOT / "README.md"),
        ("STATUS_PATH", CONTRACT_PATH),
        ("VALIDATOR_PATH", ROOT / "scripts/validate-memory-os-operability.py"),
        ("INCIDENT_RESPONSE_VALIDATOR", ROOT / "scripts/validate-memory-os-incident-tabletop.py"),
        ("TABLETOP_VALIDATOR", ROOT / "scripts/validate-memory-os-incident-response.py"),
        ("OPERABILITY_VALIDATOR", ROOT / "scripts/validate-memory-os-incident-response.py"),
        ("WORKFLOW_PATH", ROOT / ".github/workflows/incident-control-exercise.yml"),
    )
    for field, substitute in substitutions:
        expect_runtime_authority_rejected(reconciler, field, substitute)

    original_chain = reconciler.POST_WRITE_VALIDATORS
    try:
        reconciler.POST_WRITE_VALIDATORS = (reconciler.VALIDATOR_PATH,)
        try:
            reconciler.enforce_runtime_authorities()
        except reconciler.ReconcileFailure:
            pass
        else:
            raise RuntimeError("reconciler accepted validator-chain authority substitution")
    finally:
        reconciler.POST_WRITE_VALIDATORS = original_chain

    original_subprocess_run = reconciler.subprocess.run
    try:
        reconciler.subprocess.run = lambda *args, **kwargs: None
        try:
            reconciler.enforce_runtime_authorities()
        except reconciler.ReconcileFailure:
            pass
        else:
            raise RuntimeError("reconciler accepted subprocess transport substitution")
    finally:
        reconciler.subprocess.run = original_subprocess_run

    original_replace = reconciler.os.replace
    try:
        reconciler.os.replace = lambda *args, **kwargs: None
        try:
            reconciler.enforce_runtime_authorities()
        except reconciler.ReconcileFailure:
            pass
        else:
            raise RuntimeError("reconciler accepted atomic replacement transport substitution")
    finally:
        reconciler.os.replace = original_replace

    original_atomic_writer = reconciler.atomic_write_bytes
    try:
        reconciler.atomic_write_bytes = lambda *args, **kwargs: None
        try:
            reconciler.enforce_runtime_authorities()
        except reconciler.ReconcileFailure:
            pass
        else:
            raise RuntimeError("reconciler accepted atomic writer substitution")
    finally:
        reconciler.atomic_write_bytes = original_atomic_writer

    reconciler.enforce_runtime_authorities()
    if CONTRACT_PATH.read_bytes() != original_contract:
        raise RuntimeError("authority substitution mutated incident control contract")
    if RESULT_PATH.read_bytes() != original_result:
        raise RuntimeError("authority substitution mutated incident control result")
    if STATUS_PATH.read_bytes() != original_status:
        raise RuntimeError("authority substitution mutated production operability status")


@contextmanager
def isolated_write_authorities(reconciler):
    path_fields = (
        "ROOT",
        "CONTRACT_PATH",
        "RESULT_PATH",
        "STATUS_PATH",
        "VALIDATOR_PATH",
        "INCIDENT_RESPONSE_VALIDATOR",
        "TABLETOP_VALIDATOR",
        "OPERABILITY_VALIDATOR",
        "WORKFLOW_PATH",
        "POST_WRITE_VALIDATORS",
    )
    originals = {field: getattr(reconciler, field) for field in path_fields}

    with tempfile.TemporaryDirectory(prefix="memory-os-incident-control-reconcile-negative-") as tmp:
        fixture_root = Path(tmp)
        for source, relative in (
            (CONTRACT_PATH, reconciler.CONTRACT_REL),
            (RESULT_PATH, reconciler.RESULT_REL),
            (STATUS_PATH, reconciler.STATUS_REL),
            (ROOT / reconciler.WORKFLOW_REL, reconciler.WORKFLOW_REL),
        ):
            destination = fixture_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        validator_paths = (
            reconciler.VALIDATOR_REL,
            reconciler.INCIDENT_RESPONSE_VALIDATOR_REL,
            reconciler.TABLETOP_VALIDATOR_REL,
            reconciler.OPERABILITY_VALIDATOR_REL,
        )
        for relative in validator_paths:
            destination = fixture_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if relative == reconciler.VALIDATOR_REL:
                destination.write_text(
                    "import json\n"
                    "from pathlib import Path\n"
                    "root = Path(__file__).resolve().parents[1]\n"
                    "value = json.loads((root / 'contracts/operations/incident-control-exercise-contract.v1.json').read_text(encoding='utf-8'))\n"
                    "raise SystemExit(1 if value.get('readiness', {}).get('productionReady') is True else 0)\n",
                    encoding="utf-8",
                )
            else:
                destination.write_text("raise SystemExit(0)\n", encoding="utf-8")

        reconciler.ROOT = fixture_root
        reconciler.CONTRACT_PATH = fixture_root / reconciler.CONTRACT_REL
        reconciler.RESULT_PATH = fixture_root / reconciler.RESULT_REL
        reconciler.STATUS_PATH = fixture_root / reconciler.STATUS_REL
        reconciler.VALIDATOR_PATH = fixture_root / reconciler.VALIDATOR_REL
        reconciler.INCIDENT_RESPONSE_VALIDATOR = fixture_root / reconciler.INCIDENT_RESPONSE_VALIDATOR_REL
        reconciler.TABLETOP_VALIDATOR = fixture_root / reconciler.TABLETOP_VALIDATOR_REL
        reconciler.OPERABILITY_VALIDATOR = fixture_root / reconciler.OPERABILITY_VALIDATOR_REL
        reconciler.WORKFLOW_PATH = fixture_root / reconciler.WORKFLOW_REL
        reconciler.POST_WRITE_VALIDATORS = (
            reconciler.VALIDATOR_PATH,
            reconciler.INCIDENT_RESPONSE_VALIDATOR,
            reconciler.TABLETOP_VALIDATOR,
            reconciler.OPERABILITY_VALIDATOR,
        )
        try:
            reconciler.enforce_runtime_authorities()
            yield
        finally:
            for field, value in originals.items():
                setattr(reconciler, field, value)
            reconciler.enforce_runtime_authorities()


def assert_canonical_unchanged(
    original_contract: bytes,
    original_result: bytes,
    original_status: bytes,
    original_contract_mode: int,
    original_result_mode: int,
    original_status_mode: int,
    label: str,
) -> None:
    if CONTRACT_PATH.read_bytes() != original_contract:
        raise RuntimeError(f"{label} mutated canonical incident control contract")
    if RESULT_PATH.read_bytes() != original_result:
        raise RuntimeError(f"{label} mutated canonical incident control result")
    if STATUS_PATH.read_bytes() != original_status:
        raise RuntimeError(f"{label} mutated canonical production operability status")
    if stat.S_IMODE(CONTRACT_PATH.stat().st_mode) != original_contract_mode:
        raise RuntimeError(f"{label} changed canonical incident control contract mode")
    if stat.S_IMODE(RESULT_PATH.stat().st_mode) != original_result_mode:
        raise RuntimeError(f"{label} changed canonical incident control result mode")
    if stat.S_IMODE(STATUS_PATH.stat().st_mode) != original_status_mode:
        raise RuntimeError(f"{label} changed canonical production operability status mode")


def verify_atomic_replace_failure(reconciler) -> None:
    original_contract = reconciler.CONTRACT_PATH.read_bytes()
    original_mode = stat.S_IMODE(reconciler.CONTRACT_PATH.stat().st_mode)
    before_temps = set(reconciler.CONTRACT_PATH.parent.glob(f".{reconciler.CONTRACT_PATH.name}.*.tmp"))
    original_replace = reconciler.os.replace

    def fail_replace(*_args, **_kwargs):
        raise OSError("synthetic incident atomic replacement failure")

    try:
        reconciler.os.replace = fail_replace
        try:
            reconciler.CANONICAL_ATOMIC_WRITE_BYTES(reconciler.CONTRACT_PATH, original_contract + b" ")
        except OSError:
            pass
        else:
            raise RuntimeError("atomic writer accepted synthetic replacement failure")
    finally:
        reconciler.os.replace = original_replace

    if reconciler.CONTRACT_PATH.read_bytes() != original_contract:
        raise RuntimeError("atomic replacement failure mutated isolated incident control contract")
    if stat.S_IMODE(reconciler.CONTRACT_PATH.stat().st_mode) != original_mode:
        raise RuntimeError("atomic replacement failure changed isolated incident control contract mode")
    after_temps = set(reconciler.CONTRACT_PATH.parent.glob(f".{reconciler.CONTRACT_PATH.name}.*.tmp"))
    if after_temps != before_temps:
        raise RuntimeError("atomic replacement failure left temporary isolated incident authority residue")


def verify_second_replace_rollback(reconciler, contract, status) -> None:
    original_contract = reconciler.CONTRACT_PATH.read_bytes()
    original_status = reconciler.STATUS_PATH.read_bytes()
    original_contract_mode = stat.S_IMODE(reconciler.CONTRACT_PATH.stat().st_mode)
    original_status_mode = stat.S_IMODE(reconciler.STATUS_PATH.stat().st_mode)
    original_replace = reconciler.os.replace
    calls = 0

    def fail_second_replace(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic second incident authority replace failure")
        return original_replace(source, destination)

    reconciler.os.replace = fail_second_replace
    try:
        try:
            reconciler.commit_validated_pair(copy.deepcopy(contract), copy.deepcopy(status))
        except OSError:
            pass
        else:
            raise RuntimeError("reconciler accepted second incident authority replace failure")
    finally:
        reconciler.os.replace = original_replace

    if calls != 4:
        raise RuntimeError(f"second replace failure did not execute complete two-authority rollback: {calls} replace calls")
    if reconciler.CONTRACT_PATH.read_bytes() != original_contract:
        raise RuntimeError("second replace rollback changed isolated incident control contract")
    if reconciler.STATUS_PATH.read_bytes() != original_status:
        raise RuntimeError("second replace rollback changed isolated production operability status")
    if stat.S_IMODE(reconciler.CONTRACT_PATH.stat().st_mode) != original_contract_mode:
        raise RuntimeError("second replace rollback changed isolated incident contract mode")
    if stat.S_IMODE(reconciler.STATUS_PATH.stat().st_mode) != original_status_mode:
        raise RuntimeError("second replace rollback changed isolated production status mode")
    if list(reconciler.CONTRACT_PATH.parent.glob(f".{reconciler.CONTRACT_PATH.name}.*.tmp")):
        raise RuntimeError("second replace rollback left isolated incident contract temporary residue")
    if list(reconciler.STATUS_PATH.parent.glob(f".{reconciler.STATUS_PATH.name}.*.tmp")):
        raise RuntimeError("second replace rollback left isolated production status temporary residue")


def verify_post_write_rollback(reconciler, contract, status) -> None:
    original_contract = reconciler.CONTRACT_PATH.read_bytes()
    original_status = reconciler.STATUS_PATH.read_bytes()
    original_contract_mode = stat.S_IMODE(reconciler.CONTRACT_PATH.stat().st_mode)
    original_status_mode = stat.S_IMODE(reconciler.STATUS_PATH.stat().st_mode)

    rollback_contract = copy.deepcopy(contract)
    rollback_contract["readiness"]["productionReady"] = True
    try:
        reconciler.commit_validated_pair(rollback_contract, copy.deepcopy(status))
    except reconciler.ReconcileFailure:
        pass
    else:
        raise RuntimeError("reconciler accepted invalid post-write incident authority")

    if reconciler.CONTRACT_PATH.read_bytes() != original_contract:
        raise RuntimeError("post-write rollback changed isolated incident control contract")
    if reconciler.STATUS_PATH.read_bytes() != original_status:
        raise RuntimeError("post-write rollback changed isolated production operability status")
    if stat.S_IMODE(reconciler.CONTRACT_PATH.stat().st_mode) != original_contract_mode:
        raise RuntimeError("post-write rollback changed isolated incident contract mode")
    if stat.S_IMODE(reconciler.STATUS_PATH.stat().st_mode) != original_status_mode:
        raise RuntimeError("post-write rollback changed isolated production status mode")
    if list(reconciler.CONTRACT_PATH.parent.glob(f".{reconciler.CONTRACT_PATH.name}.*.tmp")):
        raise RuntimeError("post-write rollback left isolated incident contract temporary residue")
    if list(reconciler.STATUS_PATH.parent.glob(f".{reconciler.STATUS_PATH.name}.*.tmp")):
        raise RuntimeError("post-write rollback left isolated production status temporary residue")


def expect_result_rejected(reconciler, result, contract, label: str) -> None:
    try:
        reconciler.validate_result(result, contract)
    except reconciler.ReconcileFailure:
        return
    raise RuntimeError(f"reconciler accepted malformed incident result: {label}")


def main() -> int:
    reconciler = load_module()
    original_contract_bytes = CONTRACT_PATH.read_bytes()
    original_result_bytes = RESULT_PATH.read_bytes()
    original_status_bytes = STATUS_PATH.read_bytes()
    original_contract_mode = stat.S_IMODE(CONTRACT_PATH.stat().st_mode)
    original_result_mode = stat.S_IMODE(RESULT_PATH.stat().st_mode)
    original_status_mode = stat.S_IMODE(STATUS_PATH.stat().st_mode)
    contract = json.loads(original_contract_bytes.decode("utf-8"))
    status = json.loads(original_status_bytes.decode("utf-8"))
    result = json.loads(original_result_bytes.decode("utf-8"))

    verify_runtime_authority_identity(
        reconciler,
        original_contract_bytes,
        original_result_bytes,
        original_status_bytes,
    )

    for field in UNPROVEN_READINESS:
        candidate = copy.deepcopy(contract)
        candidate["readiness"][field] = True
        try:
            reconciler.normalize_contract(candidate)
        except reconciler.ReconcileFailure:
            pass
        else:
            raise RuntimeError(f"reconciler auto-healed unproven readiness: {field}")

    malformed = copy.deepcopy(result)
    malformed["exercise"]["scenarios"][0]["decisions"]["promotionDecision"] = "ALLOW"
    expect_result_rejected(reconciler, malformed, contract, "promotion decision bypass")

    malformed = copy.deepcopy(result)
    malformed["exercise"]["scenarios"][0]["decisions"]["stopConditions"] = []
    expect_result_rejected(reconciler, malformed, contract, "stop-condition removal")

    malformed = copy.deepcopy(result)
    malformed["exercise"]["scenarios"][0]["controls"][0]["outputSha256"] = "0" * 63
    expect_result_rejected(reconciler, malformed, contract, "invalid validator output digest")

    malformed = copy.deepcopy(result)
    malformed["environment"]["syntheticScenariosOnly"] = False
    expect_result_rejected(reconciler, malformed, contract, "synthetic scenario boundary")

    with isolated_write_authorities(reconciler):
        fixture_contract = json.loads(reconciler.CONTRACT_PATH.read_text(encoding="utf-8"))
        fixture_status = json.loads(reconciler.STATUS_PATH.read_text(encoding="utf-8"))
        verify_atomic_replace_failure(reconciler)
        verify_second_replace_rollback(reconciler, fixture_contract, fixture_status)
        verify_post_write_rollback(reconciler, fixture_contract, fixture_status)

    assert_canonical_unchanged(
        original_contract_bytes,
        original_result_bytes,
        original_status_bytes,
        original_contract_mode,
        original_result_mode,
        original_status_mode,
        "isolated incident reconcile negatives",
    )

    print("PASS: incident authority reconcile rejects data/executable authority substitution")
    print("PASS: incident authority reconcile rejects validator-chain and execution-transport substitution")
    print("PASS: incident authority atomic replacement failure preserves isolated bytes, mode and temp cleanliness")
    print("PASS: incident authority second replace failure rolls back both isolated authorities exactly")
    print("PASS: incident authority post-write rejection rolls back isolated authorities without mutating canonical authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
