#!/usr/bin/env python3
"""Reconcile explicitly approved recovery objectives without inventing values."""

from __future__ import annotations

import importlib.util
import json
import math
import os
import subprocess
import sys
import stat
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/recovery-objectives-admission-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/recovery-objectives-registry.v1.json")
WRITER_REL = Path("scripts/register-memory-os-recovery-objectives.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-recovery-objectives.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
WRITER = ROOT / WRITER_REL
VALIDATOR = ROOT / VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
STATUS = ROOT / STATUS_REL
EVIDENCE_PREFIX = "recovery objectives approval is append-only:"
REFS = (
    "contracts/operations/recovery-objectives-admission-contract.v1.json",
    "contracts/operations/recovery-objectives-registry.v1.json",
    "scripts/register-memory-os-recovery-objectives.py",
    "scripts/validate-memory-os-recovery-objectives.py",
    "scripts/reconcile-memory-os-recovery-objectives.py",
    ".github/workflows/recovery-objectives-admission.yml",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def repo_relative(path: Path) -> Path:
    """Reject aliases and traversal rather than silently normalizing evidence refs."""
    if not isinstance(path, Path) or not path.is_absolute():
        raise Fail("recovery objective authority reference path unsafe") from None
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=False).relative_to(ROOT.resolve())
    except (OSError, RuntimeError, ValueError):
        raise Fail("recovery objective authority reference path unsafe") from None
    require(lexical == resolved and lexical != Path("."),
            "recovery objective authority reference path unsafe")
    return lexical


def require_repo_file(path: Path, message: str) -> Path:
    relative = repo_relative(path)
    require((ROOT / relative).is_file(), message)
    return relative


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        raise Fail(f"{field} missing or escapes repository") from None
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    for path, expected, field in (
        (CONTRACT, CONTRACT_REL, "recovery objective contract"),
        (REGISTRY, REGISTRY_REL, "recovery objective registry"),
        (WRITER, WRITER_REL, "recovery objective writer"),
        (VALIDATOR, VALIDATOR_REL, "recovery objective validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (STATUS, STATUS_REL, "production operability status"),
    ):
        require_exact_repo_file(path, expected, field)


MAX_AUTHORITY_BYTES = 1024 * 1024


def read_text(path: Path) -> str:
    """Read reviewed JSON authority from owned, stable no-follow descriptors."""
    require(isinstance(path, Path) and path.is_absolute(),
            "recovery objective reconcile authority path unsafe")
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (OSError, RuntimeError, ValueError):
        raise Fail("recovery objective reconcile authority path unsafe") from None
    require(lexical == resolved and path.is_file() and not path.is_symlink(),
            "recovery objective reconcile authority path unsafe")
    try:
        size = path.stat().st_size
    except (OSError, ValueError, TypeError):
        raise Fail("recovery objective reconcile authority unreadable") from None
    require(size <= MAX_AUTHORITY_BYTES,
            "recovery objective reconcile authority size limit exceeded")
    try:
        # The same reviewed FD-pinning primitive used for executable source
        # prevents a parent-directory swap between path review and file open.
        raw = pinned_reviewed_source(path, lexical, "recovery objective reconcile authority")
    except (Fail, OSError, ValueError, TypeError):
        raise Fail("recovery objective reconcile authority unreadable") from None
    try:
        return raw.decode("utf-8")
    except UnicodeError:
        raise Fail("recovery objective reconcile authority invalid UTF-8") from None

def write_text(path: Path, text: str) -> None:
    """Atomically replace only reviewed, bounded recovery objective authorities."""
    require(isinstance(path, Path) and path.is_absolute(),
            "recovery objective reconcile write path unsafe")
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (OSError, RuntimeError, ValueError):
        raise Fail("recovery objective reconcile write path unsafe") from None
    require(lexical == resolved and path.is_file() and not path.is_symlink(),
            "recovery objective reconcile write path unsafe")
    require(lexical in {CONTRACT_REL, STATUS_REL},
            "recovery objective reconcile write target unreviewed")
    require(isinstance(text, str), "recovery objective reconcile write payload invalid")
    try:
        payload = text.encode("utf-8")
    except UnicodeError:
        raise Fail("recovery objective reconcile write payload invalid") from None
    require(len(payload) <= MAX_AUTHORITY_BYTES,
            "recovery objective reconcile write size limit exceeded")
    descriptor: int | None = None
    temp_name: str | None = None
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
        descriptor, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent,
        )
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
    except (OSError, ValueError, TypeError):
        raise Fail("recovery objective reconcile authority atomic write failed") from None
    finally:
        # A secondary cleanup fault must not replace the primary atomic-write
        # failure class; still attempt every cleanup operation.
        primary_failed = sys.exc_info()[0] is not None
        cleanup_failed = False
        if descriptor is not None:
            try:
                os.close(descriptor)
            except (OSError, ValueError, TypeError):
                cleanup_failed = True
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            except (OSError, ValueError, TypeError):
                cleanup_failed = True
        if cleanup_failed and not primary_failed:
            raise Fail("recovery objective reconcile authority temporary cleanup failed") from None


def restore_original_text(original_text: dict[Path, str]) -> None:
    rollback_incomplete = False
    for path, text in original_text.items():
        try:
            write_text(path, text)
        except Exception:
            rollback_incomplete = True
    if rollback_incomplete:
        raise Fail("recovery objective rollback incomplete") from None


def load(path: Path) -> dict[str, Any]:
    def unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            require(key not in result, "recovery objective reconcile JSON duplicate key refused")
            result[key] = value
        return result

    def reject_constant(_value: str) -> None:
        raise Fail("recovery objective reconcile JSON nonfinite number refused")

    def finite_float(value: str) -> float:
        number = float(value)
        require(math.isfinite(number), "recovery objective reconcile JSON nonfinite number refused")
        return number

    def bounded_int(value: str) -> int:
        require(len(value.lstrip("-")) <= 128, "recovery objective reconcile JSON integer too large")
        return int(value)

    try:
        value = json.loads(read_text(path), object_pairs_hook=unique_keys,
                           parse_constant=reject_constant, parse_float=finite_float,
                           parse_int=bounded_int)
    except (json.JSONDecodeError, ValueError, OverflowError, RecursionError):
        raise Fail("recovery objective reconcile JSON unreadable or invalid") from None
    require(isinstance(value, dict), "recovery objective reconcile JSON root must be object")
    return value


def pinned_reviewed_source(path: Path, relative: Path, field: str) -> bytes:
    """Bind reviewed writer bytes to owned directory/file descriptors, not a mutable path."""
    require_exact_repo_file(path, relative, field)
    require(all(hasattr(os, name) for name in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")),
            "recovery objective writer pinned import platform unsafe")
    owned: list[int] = []
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        parent_fd = os.open(ROOT, directory_flags)
        require(type(parent_fd) is int and parent_fd >= 0, "writer directory descriptor invalid")
        owned.append(parent_fd)
        for part in relative.parts[:-1]:
            parent_fd = os.open(part, directory_flags, dir_fd=parent_fd)
            require(type(parent_fd) is int and parent_fd >= 0, "writer directory descriptor invalid")
            owned.append(parent_fd)
        before_parents = [os.fstat(fd) for fd in owned]
        parent_identity = lambda value: (
            value.st_dev, value.st_ino, value.st_mode, value.st_ctime_ns
        )
        require(all(stat.S_ISDIR(item.st_mode) and not (item.st_mode & 0o022)
                    for item in before_parents), "writer parent directory unsafe")
        source_fd = os.open(
            relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=parent_fd,
        )
        require(type(source_fd) is int and source_fd >= 0, "writer source descriptor invalid")
        owned.append(source_fd)
        before = os.fstat(source_fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and not (before.st_mode & 0o022)
                and 0 <= before.st_size <= MAX_AUTHORITY_BYTES,
                "writer source type/size unsafe")
        chunks: list[bytes] = []
        remaining = MAX_AUTHORITY_BYTES + 1
        while remaining:
            chunk = os.read(source_fd, remaining)
            require(type(chunk) is bytes, "writer source read type invalid")
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        source = b"".join(chunks)
        after = os.fstat(source_fd)
        leaf = os.stat(relative.name, dir_fd=parent_fd, follow_symlinks=False)
        identity = lambda item: (
            item.st_dev, item.st_ino, item.st_mode, item.st_size,
            item.st_mtime_ns, item.st_ctime_ns
        )
        require(len(source) <= MAX_AUTHORITY_BYTES
                and len(source) == before.st_size
                and identity(before) == identity(after) == identity(leaf),
                "writer source changed during read")
        for index, fd in enumerate(owned[:-1]):
            current = os.fstat(fd)
            lexical = ROOT if index == 0 else ROOT.joinpath(*relative.parts[:index])
            visible = os.lstat(lexical)
            require(stat.S_ISDIR(visible.st_mode)
                    and parent_identity(before_parents[index])
                    == parent_identity(current) == parent_identity(visible),
                    "writer parent changed during read")
        require_exact_repo_file(path, relative, field)
        require(identity(path.stat()) == identity(after),
                "writer pathname changed during read")
        return source
    finally:
        primary = sys.exc_info()[0] is not None
        failed = False
        for fd in reversed(owned):
            try:
                os.close(fd)
            except Exception:
                failed = True
        if failed and not primary:
            raise Fail("writer descriptor cleanup failed") from None



def pinned_writer_source() -> bytes:
    return pinned_reviewed_source(WRITER, WRITER_REL, "recovery objective writer")

def load_writer():
    """Execute only the canonical writer's pinned bytes with private diagnostics."""
    try:
        source = pinned_writer_source()
        with open(os.devnull, "w", encoding="utf-8") as sink:
            with redirect_stdout(sink), redirect_stderr(sink):
                spec = importlib.util.spec_from_file_location(
                    "memory_os_recovery_objectives_reconcile_writer", WRITER,
                )
                require(spec is not None and spec.loader is not None,
                        "recovery objective canonical writer import failed")
                module = importlib.util.module_from_spec(spec)
                # SourceFileLoader must not reopen the pathname after capture.
                exec(compile(source, str(WRITER), "exec"), module.__dict__)
    except Exception:
        raise Fail("recovery objective canonical writer import failed") from None
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


def run_validator(path: Path, label: str) -> None:
    """Run only reviewed validators with bounded, private failure classes."""
    if path == VALIDATOR and label == "recovery objective validator":
        relative = VALIDATOR_REL
    elif path == OPERABILITY_VALIDATOR and label == "aggregate operability validator":
        relative = OPERABILITY_VALIDATOR_REL
    else:
        raise Fail("unreviewed recovery objective post-reconcile validator")
    # Bind executed child bytes to the reviewed source, not a second path open.
    source = pinned_reviewed_source(path, relative, label)
    bootstrap = (
        "import os, sys\n"
        "path = sys.argv[1]\n"
        "sys.path.insert(0, os.path.dirname(path))\n"
        "sys.argv[:] = [path]\n"
        "scope = {'__name__': '__main__', '__file__': path, '__package__': None, '__spec__': None}\n"
        "exec(compile(sys.stdin.buffer.read(), path, 'exec'), scope)\n"
    )
    # Child validators must not inherit interpreter, loader or Git overrides.
    # Preserve ordinary environment variables for expected CI/runtime behavior.
    child_env = {
        key: value for key, value in os.environ.items()
        if not key.startswith(("PYTHON", "LD_", "DYLD_", "GIT_"))
    }
    try:
        completed = subprocess.run(
            [sys.executable, "-c", bootstrap, str(path)],
            input=source,
            cwd=ROOT,
            env=child_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=180,
        )
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        raise Fail(f"post-reconcile {label} unavailable") from None
    require(isinstance(completed, subprocess.CompletedProcess)
            and type(completed.returncode) is int and completed.returncode == 0,
            f"post-reconcile {label} failed without exposing subprocess output")


def main() -> int:
    enforce_runtime_authorities()
    original_text = {
        CONTRACT: read_text(CONTRACT),
        STATUS: read_text(STATUS),
    }
    registry = load(REGISTRY)
    contract = load(CONTRACT)
    status = load(STATUS)
    writer = load_writer()

    try:
        rows = writer.validate_registry_for_append(registry)
    except RuntimeError as exc:
        if exc.__class__.__name__ != "Fail":
            raise
        raise Fail("append-only recovery objective authority invalid before reconcile") from None

    count = registry.get("approvedObjectiveCount")
    current_id = registry.get("currentObjectiveId")
    require(isinstance(count, int) and not isinstance(count, bool) and count >= 0 and len(rows) == count, "recovery objective registry count drift")
    require(current_id == (rows[-1].get("objectiveId") if rows else None), "current objective drift")
    if count == 0:
        require(current_id is None, "empty objective registry requires null currentObjectiveId")

    authority = contract.get("currentAuthority")
    require(isinstance(authority, dict), "currentAuthority missing")
    authority["approvedObjectiveCount"] = count
    authority["currentObjectiveId"] = current_id
    authority["rpoDefined"] = count > 0
    authority["rtoDefined"] = count > 0
    authority["objectDatabaseSkewDefined"] = count > 0
    authority["productionEvidence"] = False
    authority["productionReady"] = False
    authority["productionDecision"] = "NO_GO"

    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") == "PARTIAL_FOUNDATIONS_ONLY" and gate.get("blocking") is True,
            "recovery objectives cannot advance OPS-P0-007 readiness")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list), "OPS-P0-007 evidence arrays missing")
    require_canonical_gaps(missing, Fail)
    if count == 0:
        evidence = f"{EVIDENCE_PREFIX} approval registry exists but contains 0 records, so RPO/RTO/object-database skew remain intentionally undefined and restore evidence is forbidden from inventing targets"
    else:
        evidence = f"{EVIDENCE_PREFIX} {count} reviewed objective record(s) exist and current objectiveId={current_id}; measured restore evidence must bind this exact objective and satisfy its RPO/RTO/skew targets, while objective approval itself is not production evidence"
    replace_single_prefixed(existing, EVIDENCE_PREFIX, evidence)
    for ref in REFS:
        require_repo_file(ROOT / ref, f"recovery objective authority ref missing: {ref}")
        append_once(refs, ref)
    require_canonical_gaps(gate.get("missingEvidence"), Fail)
    require(status.get("productionDecision") == "NO_GO", "productionDecision changed unexpectedly")

    contract_text = json.dumps(contract, indent=2, ensure_ascii=False) + "\n"
    status_text = json.dumps(status, indent=2, ensure_ascii=False) + "\n"
    try:
        write_text(CONTRACT, contract_text)
        write_text(STATUS, status_text)
        run_validator(VALIDATOR, "recovery objective validator")
        run_validator(OPERABILITY_VALIDATOR, "aggregate operability validator")
    except Exception as exc:
        try:
            restore_original_text(original_text)
        except Exception:
            raise Fail(
                f"recovery objective reconcile transaction failed ({type(exc).__name__}); rollback incomplete"
            ) from None
        raise Fail(
            f"recovery objective reconcile transaction failed ({type(exc).__name__}); rollback completed"
        ) from None

    print("Memory OS recovery objectives reconciliation PASS")
    print(f"approved objective records: {count}")
    print(f"current objective: {current_id or 'none'}")
    print("canonical recovery objective data/executable authorities enforced: true")
    print("corrupt append-only objective registry auto-healed by reconcile: false")
    print("recovery objective contract/status writes use atomic same-directory replace with mode preservation: true")
    print("failed post-validation leaves objective/status mutation behind: false")
    print("aggregate operability validated inside transaction: true")
    print("canonical OPS-P0-007 blockers preserved: 6")
    print("production evidence: false")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RECOVERY OBJECTIVES RECONCILE FAILED: {exc}")
        raise SystemExit(1)