#!/usr/bin/env python3
"""Reconcile drill-request binding to semantic environment-generation eligibility."""

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

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/backup-restore-drill-generation-eligibility-binding-contract.v1.json")
DRILL_REGISTRY_REL = Path("contracts/operations/backup-restore-drill-request-registry.v1.json")
DRILL_WRITER_REL = Path("scripts/request-memory-os-backup-restore-drill.py")
ELIGIBILITY_HELPER_REL = Path("scripts/memory_os_environment_generation_eligibility.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-drill-generation-eligibility-binding.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
CONTRACT = ROOT / CONTRACT_REL
DRILL_REGISTRY = ROOT / DRILL_REGISTRY_REL
DRILL_WRITER = ROOT / DRILL_WRITER_REL
ELIGIBILITY_HELPER = ROOT / ELIGIBILITY_HELPER_REL
VALIDATOR = ROOT / VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
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
        (CONTRACT, CONTRACT_REL, "drill generation binding contract"),
        (DRILL_REGISTRY, DRILL_REGISTRY_REL, "drill request registry"),
        (DRILL_WRITER, DRILL_WRITER_REL, "drill request writer"),
        (ELIGIBILITY_HELPER, ELIGIBILITY_HELPER_REL, "semantic generation eligibility helper"),
        (VALIDATOR, VALIDATOR_REL, "drill generation binding validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
    ):
        require_exact_repo_file(path, expected, field)


MAX_BINDING_AUTHORITY_BYTES = 1024 * 1024


def load(path: Path) -> dict[str, Any]:
    """Reject ambiguous or oversized planning authority before reconciliation."""
    def unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            require(key not in result, "drill generation binding JSON duplicate key refused")
            result[key] = value
        return result

    def reject_nonfinite(_value: str) -> None:
        raise Fail("drill generation binding JSON nonfinite number refused")

    def finite_float(value: str) -> float:
        number = float(value)
        require(math.isfinite(number), "drill generation binding JSON nonfinite number refused")
        return number

    def bounded_int(value: str) -> int:
        require(len(value.lstrip("-")) <= 128,
                "drill generation binding JSON oversized integer refused")
        return int(value)

    try:
        with path.open("rb") as source:
            raw = source.read(MAX_BINDING_AUTHORITY_BYTES + 1)
        require(len(raw) <= MAX_BINDING_AUTHORITY_BYTES,
                "drill generation binding JSON oversized authority refused")
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique_keys,
            parse_constant=reject_nonfinite,
            parse_float=finite_float,
            parse_int=bounded_int,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError,
            OverflowError, RecursionError):
        raise Fail("drill generation binding JSON unreadable or invalid") from None
    require(isinstance(value, dict), "drill generation binding JSON root must be object")
    return value


def load_module(path: Path, expected_relative: Path, name: str, field: str):
    """Execute only a bounded source snapshot opened beneath pinned no-follow directories."""
    require_exact_repo_file(path, expected_relative, field)
    owned: list[int] = []
    source: bytes
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        file_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        parent_fd = os.open(ROOT, directory_flags)
        owned.append(parent_fd)
        for component in expected_relative.parts[:-1]:
            parent_fd = os.open(component, directory_flags, dir_fd=parent_fd)
            owned.append(parent_fd)
        source_fd = os.open(expected_relative.name, file_flags, dir_fd=parent_fd)
        owned.append(source_fd)
        before = os.fstat(source_fd)
        require(
            stat.S_ISREG(before.st_mode) and before.st_nlink == 1
            and 0 <= before.st_size <= MAX_BINDING_AUTHORITY_BYTES,
            f"{field} module source type/size drift",
        )
        with os.fdopen(os.dup(source_fd), "rb") as stream:
            source = stream.read(MAX_BINDING_AUTHORITY_BYTES + 1)
        after = os.fstat(source_fd)
        leaf = os.stat(expected_relative.name, dir_fd=parent_fd, follow_symlinks=False)
        identity = lambda item: (
            item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns
        )
        require(
            len(source) <= MAX_BINDING_AUTHORITY_BYTES
            and len(source) == before.st_size
            and identity(before) == identity(after) == identity(leaf),
            f"{field} module source changed during read",
        )
        require_exact_repo_file(path, expected_relative, field)
        require(
            identity(path.stat()) == identity(after),
            f"{field} module pathname changed during read",
        )
    except (OSError, ValueError, TypeError, OverflowError) as exc:
        raise Fail(f"{field} module source unavailable or unsafe") from exc
    finally:
        for owned_fd in reversed(owned):
            try:
                os.close(owned_fd)
            except OSError:
                # Do not retry a potentially recycled descriptor.
                pass

    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    # Never ask SourceFileLoader to re-open a mutable pathname after validation.
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module

def run_post_validator(path: Path, expected_relative: Path, field: str) -> None:
    reviewed = {
        "drill generation binding validator": (VALIDATOR, VALIDATOR_REL),
        "operability validator": (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL),
    }
    require(reviewed.get(field) == (path, expected_relative),
            "unreviewed drill generation binding post-validator")
    require_exact_repo_file(path, expected_relative, field)
    child_env = {
        key: value for key, value in os.environ.items()
        if not key.startswith(("PYTHON", "LD_", "DYLD_", "GIT_"))
    }
    try:
        completed = subprocess.run(
            [sys.executable, str(path)],
            cwd=ROOT,
            env=child_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=120,
        )
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        raise Fail(f"post-reconcile {field} unavailable or timed out (raw output withheld)") from None
    require(
        isinstance(completed, subprocess.CompletedProcess)
        and type(completed.returncode) is int and completed.returncode == 0,
        f"post-reconcile {field} failed (raw output withheld)",
    )


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        original_mode = stat.S_IMODE(path.stat().st_mode)
    except OSError as exc:
        raise Fail(f"cannot stat {path.relative_to(ROOT)} before atomic replacement: {exc}") from exc
    fd: int | None = None
    temp_name: str | None = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        os.fchmod(fd, original_mode)
        # The raw FD remains ours if fdopen, stream write, flush or close fails.
        with os.fdopen(fd, "w", encoding="utf-8", closefd=False) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        owned_fd = fd
        fd = None  # Do not retry a possibly post-effect numeric close.
        os.close(owned_fd)
        os.replace(temp_name, path)
        temp_name = None
    except (OSError, ValueError, TypeError):
        raise Fail("drill generation binding atomic write failed") from None
    finally:
        primary_failure = sys.exc_info()[0] is not None
        cleanup_failed = False
        if fd is not None:
            owned_fd = fd
            fd = None
            try:
                os.close(owned_fd)
            except Exception:
                cleanup_failed = True
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            except Exception:
                cleanup_failed = True
        if cleanup_failed and not primary_failure:
            raise Fail("drill generation binding atomic cleanup failed") from None


CANONICAL_REQUIRE = require
CANONICAL_RUNTIME_ENFORCER = enforce_runtime_authorities
CANONICAL_EXECUTION_HELPERS = (
    require_exact_repo_file,
    load,
    load_module,
    run_post_validator,
    atomic_write_text,
)


def enforce_execution_identity(
    canonical_enforcer=CANONICAL_RUNTIME_ENFORCER,
    canonical_require=CANONICAL_REQUIRE,
    canonical_helpers=CANONICAL_EXECUTION_HELPERS,
) -> None:
    if enforce_runtime_authorities is not canonical_enforcer:
        raise Fail("drill generation binding reconcile runtime authority enforcer drift")
    if require is not canonical_require:
        raise Fail("drill generation binding reconcile require helper drift")
    current_helpers = (
        require_exact_repo_file,
        load,
        load_module,
        run_post_validator,
        atomic_write_text,
    )
    if current_helpers != canonical_helpers:
        raise Fail("drill generation binding reconcile execution helper drift")


def _reconcile() -> int:
    try:
        original_contract_text = CONTRACT.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Fail(f"cannot read {CONTRACT.relative_to(ROOT)}: {exc}") from exc
    contract = load(CONTRACT)
    registry = load(DRILL_REGISTRY)
    writer = load_module(
        DRILL_WRITER,
        DRILL_WRITER_REL,
        "memory_os_drill_writer_binding_reconcile",
        "drill request writer",
    )
    helper = load_module(
        ELIGIBILITY_HELPER,
        ELIGIBILITY_HELPER_REL,
        "memory_os_generation_eligibility_binding_reconcile",
        "semantic generation eligibility helper",
    )
    try:
        requests = writer.validate_registry_for_append(registry)
    except Exception as exc:
        raise Fail(f"drill request append-only authority invalid: {exc}") from exc
    eligibility = helper.derive()
    pair_count = eligibility["eligibleDirectedPairCount"]
    request_count = registry["registeredRequestCount"]
    current_count = registry["currentExecutableRequestCount"]
    historical_count = len(requests)

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "binding currentBoundary missing")
    boundary["eligibleDirectedRestorePairCount"] = pair_count
    boundary["reviewedDrillRequestCount"] = request_count
    boundary["currentExecutableDrillRequestCount"] = current_count
    boundary["historicalAuditableRequestCount"] = historical_count
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"

    updated_contract_text = json.dumps(contract, indent=2, ensure_ascii=False) + "\n"
    try:
        atomic_write_text(CONTRACT, updated_contract_text)
        run_post_validator(VALIDATOR, VALIDATOR_REL, "drill generation binding validator")
        run_post_validator(OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator")
    except Exception as primary_exc:
        try:
            atomic_write_text(CONTRACT, original_contract_text)
        except Exception as restore_exc:
            # A failed rollback must be explicit without hiding the original
            # rejection or leaking either private exception message.
            raise Fail(
                "drill generation binding reconcile failed "
                f"({type(primary_exc).__name__}); rollback incomplete "
                f"({type(restore_exc).__name__})"
            ) from primary_exc
        raise

    print("Memory OS drill request semantic generation binding reconciliation PASS")
    print(f"eligible directed restore pairs: {pair_count}")
    print(f"reviewed/current drill requests: {request_count}/{current_count}")
    print(f"historical auditable requests: {historical_count}")
    print("canonical data/executable authorities enforced: true")
    print("canonical execution helpers enforced: true")
    print("atomic contract replacement: true")
    print("aggregate operability validation inside transaction: true")
    print("failed post-validation leaves semantic binding authority mutation behind: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


def main(canonical_execution_guard=enforce_execution_identity) -> int:
    if enforce_execution_identity is not canonical_execution_guard:
        raise Fail("drill generation binding reconcile execution guard drift")
    enforce_execution_identity()
    enforce_runtime_authorities()
    return _reconcile()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DRILL REQUEST GENERATION ELIGIBILITY BINDING RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
