#!/usr/bin/env python3
"""Reconcile read-only production-equivalent restore drill preflight authority."""

from __future__ import annotations

import importlib.util
import json
import math
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/backup-restore-drill-preflight-contract.v1.json")
GEN_REGISTRY_REL = Path("contracts/operations/production-equivalent-environment-generation-registry.v1.json")
OBJECTIVES_REL = Path("contracts/operations/recovery-objectives-registry.v1.json")
DRILL_REGISTRY_REL = Path("contracts/operations/backup-restore-drill-request-registry.v1.json")
VALIDATOR_MODULE_REL = Path("scripts/validate-memory-os-backup-restore-drill-preflight.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
CONTRACT = ROOT / CONTRACT_REL
GEN_REGISTRY = ROOT / GEN_REGISTRY_REL
OBJECTIVES = ROOT / OBJECTIVES_REL
DRILL_REGISTRY = ROOT / DRILL_REGISTRY_REL
VALIDATOR_MODULE = ROOT / VALIDATOR_MODULE_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
STATUS = ROOT / STATUS_REL
REFS = (
    "contracts/operations/backup-restore-drill-preflight-contract.v1.json",
    "scripts/validate-memory-os-backup-restore-drill-preflight.py",
    "scripts/validate-memory-os-backup-restore-drill-preflight-negative.py",
    "scripts/reconcile-memory-os-backup-restore-drill-preflight.py",
    ".github/workflows/backup-restore-drill-preflight.yml",
)
EVIDENCE_PREFIX = "production-equivalent restore drill preflight is read-only and fail-closed:"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def repo_relative(path: Path) -> Path:
    try:
        return path.resolve(strict=False).relative_to(ROOT.resolve())
    except (OSError, RuntimeError, ValueError):
        raise Fail("preflight reconcile authority path unsafe") from None


def require_repo_file(path: Path, message: str) -> Path:
    require(isinstance(path, Path) and path.is_absolute(),
            "preflight reconcile repository file unsafe")
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (OSError, RuntimeError, ValueError):
        raise Fail("preflight reconcile repository file unsafe") from None
    require(lexical == resolved and path.is_file() and not path.is_symlink(), message)
    return lexical


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        raise Fail(f"{field} missing or escapes repository") from None
    require(
        lexical == expected_relative
        and resolved == expected_relative
        and path.is_file()
        and not path.is_symlink(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    for path, expected, field in (
        (CONTRACT, CONTRACT_REL, "preflight contract"),
        (GEN_REGISTRY, GEN_REGISTRY_REL, "environment generation registry"),
        (OBJECTIVES, OBJECTIVES_REL, "recovery objectives registry"),
        (DRILL_REGISTRY, DRILL_REGISTRY_REL, "drill request registry"),
        (VALIDATOR_MODULE, VALIDATOR_MODULE_REL, "preflight validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (STATUS, STATUS_REL, "production operability status"),
    ):
        require_exact_repo_file(path, expected, field)


MAX_AUTHORITY_BYTES = 1024 * 1024


def read_text(path: Path) -> str:
    """Read bounded UTF-8 authority from root-pinned nofollow descriptors."""
    require(isinstance(path, Path) and path.is_absolute(),
            "preflight reconcile authority path unsafe")
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (OSError, RuntimeError, ValueError):
        raise Fail("preflight reconcile authority path unsafe") from None
    require(lexical == resolved and path.is_file() and not path.is_symlink(),
            "preflight reconcile authority path unsafe")
    if not all(
        type(getattr(os, flag, None)) is int and getattr(os, flag) > 0
        for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY")
    ):
        raise Fail("preflight reconcile authority nofollow support required") from None

    directories: list[int] = []
    fd = -1
    try:
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        parent_fd = os.open(ROOT, flags | os.O_DIRECTORY)
        directories.append(parent_fd)
        for component in lexical.parts[:-1]:
            parent_fd = os.open(component, flags | os.O_DIRECTORY, dir_fd=parent_fd)
            directories.append(parent_fd)
        fd = os.open(lexical.name, flags, dir_fd=parent_fd)
        require(stat.S_ISREG(os.fstat(fd).st_mode),
                "preflight reconcile authority not regular")
        with os.fdopen(fd, "rb") as source:
            fd = -1
            raw = source.read(MAX_AUTHORITY_BYTES + 1)
    except (OSError, ValueError):
        raise Fail("preflight reconcile authority unreadable") from None
    finally:
        cleanup_failed = False
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                cleanup_failed = True
        for directory_fd in reversed(directories):
            try:
                os.close(directory_fd)
            except OSError:
                cleanup_failed = True
        if cleanup_failed:
            raise Fail("preflight reconcile authority cleanup failed") from None
    require(len(raw) <= MAX_AUTHORITY_BYTES,
            "preflight reconcile authority exceeds 1 MiB")
    try:
        return raw.decode("utf-8")
    except UnicodeError:
        raise Fail("preflight reconcile authority invalid UTF-8") from None


def load(path: Path) -> dict[str, Any]:
    """Reject duplicate, nonfinite and oversized-integer authority JSON."""
    def unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            require(key not in result, "preflight reconcile JSON duplicate key refused")
            result[key] = item
        return result

    def reject_nonfinite(_value: str) -> None:
        raise Fail("preflight reconcile JSON nonfinite number refused")

    def finite_float(value: str) -> float:
        number = float(value)
        require(math.isfinite(number), "preflight reconcile JSON nonfinite number refused")
        return number

    def bounded_int(value: str) -> int:
        require(len(value.lstrip("-")) <= 128, "preflight reconcile JSON integer too large")
        return int(value)

    try:
        value = json.loads(
            read_text(path),
            object_pairs_hook=unique_keys,
            parse_constant=reject_nonfinite,
            parse_float=finite_float,
            parse_int=bounded_int,
        )
    except (json.JSONDecodeError, UnicodeError, ValueError, OverflowError, RecursionError):
        raise Fail("preflight reconcile JSON unreadable or invalid") from None
    require(isinstance(value, dict), "preflight reconcile JSON root must be object")
    return value


def write_text(path: Path, text: str) -> None:
    """Bounded atomic authority replacement with explicit FD/temp ownership."""
    require(isinstance(path, Path) and path.is_absolute(),
            "preflight reconcile write path unsafe")
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (OSError, RuntimeError, ValueError):
        raise Fail("preflight reconcile write path unsafe") from None
    require(lexical == resolved and path.is_file() and not path.is_symlink(),
            "preflight reconcile write path unsafe")
    require(isinstance(text, str), "preflight reconcile write payload invalid")
    try:
        payload = text.encode("utf-8")
    except UnicodeError:
        raise Fail("preflight reconcile write payload invalid") from None
    require(len(payload) <= MAX_AUTHORITY_BYTES,
            "preflight reconcile write size limit exceeded")

    fd: int | None = None
    temp_name: str | None = None
    try:
        existing_mode = path.stat().st_mode & 0o7777
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, text=True,
        )
        os.fchmod(fd, existing_mode)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            fd = None
            written = handle.write(text)
            require(type(written) is int and written == len(text),
                    "preflight reconcile write short buffered write refused")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
    except (OSError, UnicodeError, ValueError, TypeError):
        raise Fail("preflight reconcile atomic write failed") from None
    finally:
        cleanup_failed = False
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                cleanup_failed = True
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            except OSError:
                cleanup_failed = True
        if cleanup_failed:
            raise Fail("preflight reconcile atomic cleanup failed") from None


def load_validator_module():
    require_exact_repo_file(VALIDATOR_MODULE, VALIDATOR_MODULE_REL, "preflight validator")
    spec = importlib.util.spec_from_file_location("memory_os_restore_drill_preflight_validator_for_reconcile", VALIDATOR_MODULE)
    require(spec is not None and spec.loader is not None, "cannot load preflight validator")
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:
        raise Fail("preflight reconcile validator import unavailable") from None
    return module


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def replace_single_prefixed(values: list[Any], prefix: str, value: str) -> None:
    matches = [index for index, item in enumerate(values) if isinstance(item, str) and item.startswith(prefix)]
    require(len(matches) <= 1, f"duplicate authority evidence prefix: {prefix}")
    if matches:
        values[matches[0]] = value
    else:
        values.append(value)


def run_post_reconcile_validator(path: Path, label: str) -> None:
    if path == VALIDATOR_MODULE:
        relative = require_exact_repo_file(path, VALIDATOR_MODULE_REL, f"{label} validator")
    elif path == OPERABILITY_VALIDATOR:
        relative = require_exact_repo_file(path, OPERABILITY_VALIDATOR_REL, f"{label} validator")
    else:
        relative = require_repo_file(path, f"{label} validator missing")
    try:
        completed = subprocess.run(
            [sys.executable, str(ROOT / relative)],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Fail(f"post-reconcile {label} validator unavailable ({type(exc).__name__})") from None
    require(type(completed.returncode) is int and completed.returncode == 0,
            f"post-reconcile {label} validator failed without exposing subprocess output")


def restore_authorities(authorities: tuple[tuple[Path, str], ...], reconcile_error: Exception) -> None:
    rollback_failures: list[str] = []
    for path, original_text in authorities:
        try:
            write_text(path, original_text)
        except Exception as rollback_exc:
            rollback_failures.append(f"{path.name}: {type(rollback_exc).__name__}")
    if rollback_failures:
        raise Fail(
            f"preflight reconcile transaction failed ({type(reconcile_error).__name__}); "
            "rollback incomplete: " + "; ".join(rollback_failures)
        ) from None


CANONICAL_REQUIRE = require
CANONICAL_RUNTIME_ENFORCER = enforce_runtime_authorities
CANONICAL_EXECUTION_HELPERS = (
    repo_relative,
    require_repo_file,
    require_exact_repo_file,
    read_text,
    load,
    write_text,
    load_validator_module,
    append_once,
    replace_single_prefixed,
    run_post_reconcile_validator,
    restore_authorities,
)


def enforce_execution_identity(
    canonical_enforcer=CANONICAL_RUNTIME_ENFORCER,
    canonical_require=CANONICAL_REQUIRE,
    canonical_helpers=CANONICAL_EXECUTION_HELPERS,
) -> None:
    if enforce_runtime_authorities is not canonical_enforcer:
        raise Fail("restore drill preflight reconcile runtime authority enforcer drift")
    if require is not canonical_require:
        raise Fail("restore drill preflight reconcile require helper drift")
    current_helpers = (
        repo_relative,
        require_repo_file,
        require_exact_repo_file,
        read_text,
        load,
        write_text,
        load_validator_module,
        append_once,
        replace_single_prefixed,
        run_post_reconcile_validator,
        restore_authorities,
    )
    if current_helpers != canonical_helpers:
        raise Fail("restore drill preflight reconcile execution helper drift")


def _reconcile() -> int:
    original_contract_text = read_text(CONTRACT)
    original_status_text = read_text(STATUS)
    contract = load(CONTRACT)
    generations = load(GEN_REGISTRY)
    objectives = load(OBJECTIVES)
    drill_registry = load(DRILL_REGISTRY)
    status = load(STATUS)
    validator = load_validator_module()

    validator.run_validator(validator.GEN_VALIDATOR, "environment generation")
    validator.run_validator(validator.OBJECTIVE_VALIDATOR, "recovery objectives")
    validator.run_validator(validator.DRILL_VALIDATOR, "restore drill request")
    state = validator.derive_state(generations, objectives, drill_registry)

    pair_available = state["eligibleDirectedSourceTargetPairCount"] > 0
    objective_available = state["currentObjectiveId"] is not None
    canonical = {
        **state,
        "requestCreated": False,
        "backupExecuted": False,
        "restoreExecuted": False,
        "productionTrafficChanged": False,
        "productionEvidence": False,
        "productionReady": False,
        "productionDecision": "NO_GO",
    }
    readiness = {
        "contractDefined": True,
        "validatorImplemented": True,
        "reconcileImplemented": True,
        "automaticWorkflowImplemented": True,
        "twoDistinctUnsupersededPreflightEligibleEnvironmentsAvailable": pair_available,
        "currentRecoveryObjectiveAvailable": objective_available,
        "eligibleSourceTargetPairAvailable": pair_available,
        "reviewedDrillRequestSubmissionEligible": state["eligibleToSubmitReviewedDrillRequest"],
        "currentExecutableDrillRequestAvailable": state["currentExecutableDrillRequestCount"] > 0,
        "drillExecuted": False,
        "productionReady": False,
    }
    require(set(canonical) == validator.STATE_FIELDS, "reconciled preflight currentState field drift")
    require(set(readiness) == validator.READINESS_FIELDS, "reconciled preflight readiness field drift")
    contract["currentState"] = canonical
    contract["readiness"] = readiness

    require(status.get("productionDecision") == "NO_GO", "preflight reconcile cannot change production decision")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") == "PARTIAL_FOUNDATIONS_ONLY" and gate.get("blocking") is True, "OPS-P0-007 must remain blocking foundation-only")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    missing = gate.get("missingEvidence")
    require(isinstance(existing, list) and isinstance(refs, list) and isinstance(missing, list), "OPS-P0-007 authority arrays missing")
    require_canonical_gaps(missing, Fail)
    blockers = state["blockingPrerequisites"]
    blocker_text = ",".join(blockers) if blockers else "none"
    evidence = f"{EVIDENCE_PREFIX} registered/preflight-eligible generations={state['registeredGenerationCount']}/{state['preflightEligibleGenerationCount']}, unsuperseded/preflight-eligible unsuperseded generations={state['unsupersededGenerationCount']}/{state['unsupersededPreflightEligibleGenerationCount']}, distinct semantic preflight-eligible unsuperseded environments={state['distinctUnsupersededPreflightEligibleEnvironmentCount']}, eligible directed source-target pairs={state['eligibleDirectedSourceTargetPairCount']}, approved recovery objectives={state['approvedRecoveryObjectiveCount']}, reviewed/current drill requests={state['reviewedDrillRequestCount']}/{state['currentExecutableDrillRequestCount']}, blocking prerequisites={state['blockingPrerequisiteCount']}[{blocker_text}], decision={state['preflightDecision']}; registered generation inventory alone never creates restore-planning authority; READY authorizes only external reviewed request submission, never prerequisite/request creation, backup/restore execution, production traffic or promotion"
    replace_single_prefixed(existing, EVIDENCE_PREFIX, evidence)
    for ref in REFS:
        require_repo_file(ROOT / ref, f"preflight evidence ref missing: {ref}")
        append_once(refs, ref)

    contract_text = json.dumps(contract, indent=2, ensure_ascii=False) + "\n"
    status_text = json.dumps(status, indent=2, ensure_ascii=False) + "\n"
    try:
        write_text(CONTRACT, contract_text)
        write_text(STATUS, status_text)
        run_post_reconcile_validator(VALIDATOR_MODULE, "preflight")
        run_post_reconcile_validator(OPERABILITY_VALIDATOR, "operability")
    except Exception as reconcile_error:
        restore_authorities(
            (
                (CONTRACT, original_contract_text),
                (STATUS, original_status_text),
            ),
            reconcile_error,
        )
        raise Fail(f"preflight reconcile transaction failed ({type(reconcile_error).__name__})") from None

    print("Memory OS production-equivalent restore drill preflight reconciliation PASS")
    print(f"registered/preflight-eligible generations: {state['registeredGenerationCount']}/{state['preflightEligibleGenerationCount']}")
    print(f"unsuperseded/preflight-eligible unsuperseded generations: {state['unsupersededGenerationCount']}/{state['unsupersededPreflightEligibleGenerationCount']}")
    print(f"distinct semantic preflight-eligible unsuperseded environments: {state['distinctUnsupersededPreflightEligibleEnvironmentCount']}")
    print(f"preflight decision: {state['preflightDecision']}")
    print(f"blocking prerequisites ({state['blockingPrerequisiteCount']}): {blocker_text}")
    print(f"eligible directed source-target pairs: {state['eligibleDirectedSourceTargetPairCount']}")
    print(f"reviewed/current drill requests: {state['reviewedDrillRequestCount']}/{state['currentExecutableDrillRequestCount']}")
    print("preflight authority state canonicalized: true")
    print("upstream authority validated before reconcile mutation: true")
    print("canonical reconciler data/executable authorities enforced: true")
    print("canonical reconciler execution helpers enforced: true")
    print("preflight/status writes use mode-preserving atomic same-directory replace: true")
    print("preflight and aggregate operability validated inside transaction: true")
    print("failed post-validation leaves derived preflight/status mutation behind: false")
    print("rollback attempts every preflight authority even after an earlier restore failure: true")
    print("registered generation inventory alone creates restore-planning authority: false")
    print("automatic prerequisite/request creation: false")
    print("restore executed: false")
    print("canonical OPS-P0-007 blockers preserved: 6")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


def main(canonical_execution_guard=enforce_execution_identity) -> int:
    if enforce_execution_identity is not canonical_execution_guard:
        raise Fail("restore drill preflight reconcile execution guard drift")
    enforce_execution_identity()
    enforce_runtime_authorities()
    return _reconcile()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE DRILL PREFLIGHT RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
