#!/usr/bin/env python3
"""Reconcile repeatable local degradation evidence without approving capacity thresholds."""

from __future__ import annotations

import json
import math
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MAX_JSON_BYTES = 1024 * 1024
CANONICAL_CONTRACT = ROOT / "contracts/operations/controlled-saturation-repeatability-contract.v1.json"
CANONICAL_RESULT = ROOT / "docs/fixtures/memory-os-operability/controlled-saturation-repeatability-results.v1.json"
CANONICAL_VALIDATOR = ROOT / "scripts/validate-memory-os-controlled-saturation-repeatability.py"
CANONICAL_LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
CANONICAL_LOAD = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
CANONICAL_STATUS = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_WORKFLOW = ROOT / ".github/workflows/controlled-saturation-repeatability.yml"
CONTRACT = CANONICAL_CONTRACT
RESULT = CANONICAL_RESULT
VALIDATOR = CANONICAL_VALIDATOR
LOAD_VALIDATOR = CANONICAL_LOAD_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
LOAD = CANONICAL_LOAD
STATUS = CANONICAL_STATUS
WORKFLOW = CANONICAL_WORKFLOW
TRANSACTION_PATHS = (CONTRACT, LOAD, STATUS)

EVIDENCE = (
    "two-run local controlled-saturation repeatability authority classifies a throughput/latency degradation knee or actual failure signal on independent PostgreSQL+MinIO runners; even a repeatable local signal remains non-production and cannot itself establish a capacity boundary or approve an operating threshold"
)
REFS = (
    "contracts/operations/controlled-saturation-repeatability-contract.v1.json",
    "scripts/analyze-memory-os-controlled-saturation-repeatability.py",
    "scripts/validate-memory-os-controlled-saturation-repeatability.py",
    "scripts/reconcile-memory-os-controlled-saturation-repeatability.py",
    ".github/workflows/controlled-saturation-repeatability.yml",
    "docs/fixtures/memory-os-operability/controlled-saturation-repeatability-results.v1.json",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_exact_authority(path: Path, canonical: Path, label: str) -> None:
    require(path == canonical, f"{label} authority drift")
    for candidate in (canonical, *canonical.parents):
        require(not candidate.is_symlink(), f"canonical {label} symlink path rejected")
    require(canonical.is_file(), f"canonical {label} missing")
    try:
        canonical.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except ValueError:
        raise Fail(f"canonical {label} escaped repository") from None


def enforce_runtime_authorities() -> None:
    for path, canonical, label in (
        (CONTRACT, CANONICAL_CONTRACT, "repeatability contract"),
        (RESULT, CANONICAL_RESULT, "repeatability result"),
        (VALIDATOR, CANONICAL_VALIDATOR, "repeatability validator"),
        (LOAD_VALIDATOR, CANONICAL_LOAD_VALIDATOR, "load validator"),
        (OPERABILITY_VALIDATOR, CANONICAL_OPERABILITY_VALIDATOR, "operability validator"),
        (LOAD, CANONICAL_LOAD, "load contract"),
        (STATUS, CANONICAL_STATUS, "production status"),
        (WORKFLOW, CANONICAL_WORKFLOW, "repeatability workflow"),
    ):
        require_exact_authority(path, canonical, label)


def reject_nonfinite_constant(value: str) -> None:
    raise Fail("non-finite repeatability JSON constant rejected")


def parse_finite_float(value: str) -> float:
    parsed = float(value)
    require(math.isfinite(parsed), "non-finite repeatability JSON number rejected")
    return parsed


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in document, "duplicate repeatability JSON key rejected")
        document[key] = value
    return document


def load(path: Path) -> dict[str, Any]:
    require(isinstance(path, Path), "repeatability JSON path must be Path")
    require(path.is_file(), "repeatability JSON file missing")
    for candidate in (path, *path.parents):
        require(not candidate.is_symlink(), "repeatability JSON symlink path rejected")
    try:
        path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except ValueError:
        raise Fail("repeatability JSON path escaped repository") from None
    try:
        with path.open("rb") as source:
            raw = source.read(MAX_JSON_BYTES + 1)
        require(len(raw) <= MAX_JSON_BYTES, "repeatability JSON exceeds reviewed read limit")
        value = json.loads(raw.decode("utf-8"),
                           parse_constant=reject_nonfinite_constant,
                           parse_float=parse_finite_float,
                           object_pairs_hook=reject_duplicate_json_keys)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, OverflowError, RecursionError):
        raise Fail("invalid repeatability JSON") from None
    require(isinstance(value, dict), "repeatability JSON root must be object")
    return value


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    # This helper must reject unsafe paths even when called outside main().
    require(path.parent.is_dir(), "repeatability authority parent missing")
    for candidate in (path, *path.parents):
        require(not candidate.is_symlink(), "repeatability authority symlink path rejected")
    require(not path.is_dir(), "repeatability authority directory target rejected")
    try:
        path.parent.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except ValueError:
        raise Fail("repeatability authority path escaped repository") from None
    require(not path.exists() or path.is_file(), "repeatability authority target is not a file")
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            tmp_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fchmod(handle.fileno(), mode)
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        tmp_path = None
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass


def write(path: Path, value: dict[str, Any]) -> None:
    atomic_write_bytes(path, (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def refuse_stronger_readiness(readiness: dict[str, Any], label: str, fields: tuple[str, ...],
                              optional_absent: tuple[str, ...] = ()) -> None:
    for field in fields:
        if field in optional_absent and field not in readiness:
            continue
        require(readiness.get(field) is False, f"refusing to downgrade stronger {label}.{field}")


def run_validator(validator: Path) -> None:
    # Untrusted validator output must never enter CI logs or diagnostics.
    try:
        subprocess.run(
            [sys.executable, str(validator)],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as exc:
        raise Fail(f"repeatability validator failed: {validator.name} (exit {exc.returncode})") from None
    except OSError as exc:
        raise Fail(f"repeatability validator execution failed: {type(exc).__name__}") from None


def run_post_write_validators() -> None:
    enforce_runtime_authorities()
    for validator in (VALIDATOR, LOAD_VALIDATOR, OPERABILITY_VALIDATOR):
        run_validator(validator)


def write_transactionally(contract: dict[str, Any], load_contract: dict[str, Any], status: dict[str, Any]) -> None:
    enforce_runtime_authorities()
    originals = {path: path.read_bytes() for path in TRANSACTION_PATHS}
    try:
        write(CONTRACT, contract)
        write(LOAD, load_contract)
        write(STATUS, status)
        run_post_write_validators()
    except BaseException as primary_error:
        rollback_error: BaseException | None = None
        for path, content in originals.items():
            try:
                atomic_write_bytes(path, content)
            except BaseException as exc:
                if rollback_error is None:
                    rollback_error = exc
        if rollback_error is not None:
            raise Fail(
                "controlled saturation repeatability rollback incomplete: "
                f"{type(rollback_error).__name__}; primary {type(primary_error).__name__}"
            ) from None
        raise Fail(
            f"controlled saturation repeatability transaction failed: {type(primary_error).__name__}"
        ) from None


def main() -> int:
    enforce_runtime_authorities()
    run_validator(VALIDATOR)
    result = load(RESULT)
    repeatable = result.get("repeatableLocalDegradationSignalObserved") is True

    contract = load(CONTRACT)
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "repeatability readiness missing")
    refuse_stronger_readiness(
        readiness, "repeatability readiness",
        ("capacityBoundaryEstablished", "operationalThresholdApproved", "independentReviewCompleted", "productionReady"),
    )
    require(not (readiness.get("repeatableLocalDegradationSignalObserved") is True and not repeatable),
            "refusing to downgrade previously admitted repeatable local signal")
    readiness["analyzerImplemented"] = True
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = WORKFLOW.is_file()
    readiness["independentRunCount"] = 2
    readiness["repeatableLocalDegradationSignalObserved"] = repeatable
    readiness["capacityBoundaryEstablished"] = False
    readiness["operationalThresholdApproved"] = False
    readiness["independentReviewCompleted"] = False
    readiness["productionReady"] = False

    load_contract = load(LOAD)
    load_readiness = load_contract.get("readiness")
    require(isinstance(load_readiness, dict), "load readiness missing")
    refuse_stronger_readiness(
        load_readiness, "load readiness",
        ("capacityBoundaryEstablished", "operationalThresholds", "productionReady"),
        optional_absent=("productionReady",),
    )
    require(not (load_readiness.get("repeatableLocalDegradationSignalObserved") is True and not repeatable),
            "refusing to downgrade previously admitted load repeatability signal")
    load_readiness["repeatableLocalDegradationSignalObserved"] = repeatable
    load_readiness["capacityBoundaryEstablished"] = False
    load_readiness["operationalThresholds"] = False
    refs = load_contract.get("evidenceRefs")
    require(isinstance(refs, list), "load evidenceRefs missing")
    for ref in REFS:
        append_once(refs, ref)

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-006"), None)
    require(isinstance(gate, dict), "OPS-P0-006 missing")
    require(str(gate.get("status")).startswith("PARTIAL"), "OPS-P0-006 must remain PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    gate_refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(gate_refs, list), "OPS-P0-006 arrays missing")
    append_once(existing, EVIDENCE)
    for ref in REFS:
        append_once(gate_refs, ref)
    if repeatable:
        rewritten: list[Any] = []
        for item in missing:
            text = str(item)
            if "repeatable saturation transition" in text.lower():
                replacement = "production-shaped capacity boundary plus independently reviewed safe operating thresholds derived from admitted repeated evidence"
                if replacement not in rewritten:
                    rewritten.append(replacement)
            elif item not in rewritten:
                rewritten.append(item)
        gate["missingEvidence"] = rewritten

    write_transactionally(contract, load_contract, status)

    print("Memory OS controlled saturation repeatability reconciliation PASS")
    print(f"repeatable local degradation signal: {repeatable}")
    print("capacity boundary established: false")
    print("operational threshold approved: false")
    print("OPS-P0-006: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"CONTROLLED SATURATION REPEATABILITY RECONCILE FAILED: {exc}")
        raise SystemExit(1)
