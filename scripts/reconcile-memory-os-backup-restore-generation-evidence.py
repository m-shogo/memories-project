#!/usr/bin/env python3
"""Reconcile drill-bound generation recovery evidence without promoting production readiness."""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/backup-restore-generation-evidence-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/backup-restore-generation-evidence-registry.v1.json")
GEN_REGISTRY_REL = Path("contracts/operations/production-equivalent-environment-generation-registry.v1.json")
OBJECTIVES_REGISTRY_REL = Path("contracts/operations/recovery-objectives-registry.v1.json")
DRILL_REGISTRY_REL = Path("contracts/operations/backup-restore-drill-request-registry.v1.json")
BINDING_REL = Path("contracts/operations/backup-restore-generation-binding-contract.v1.json")
WRITER_REL = Path("scripts/register-memory-os-backup-restore-generation-evidence.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-generation-evidence.py")
BINDING_VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-generation-binding.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
GEN_REGISTRY = ROOT / GEN_REGISTRY_REL
OBJECTIVES_REGISTRY = ROOT / OBJECTIVES_REGISTRY_REL
DRILL_REGISTRY = ROOT / DRILL_REGISTRY_REL
BINDING = ROOT / BINDING_REL
WRITER = ROOT / WRITER_REL
VALIDATOR = ROOT / VALIDATOR_REL
BINDING_VALIDATOR = ROOT / BINDING_VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
STATUS = ROOT / STATUS_REL
REFS = (
    "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
    "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "contracts/operations/backup-restore-drill-request-contract.v1.json",
    "contracts/operations/backup-restore-drill-request-registry.v1.json",
    "contracts/operations/recovery-objectives-admission-contract.v1.json",
    "contracts/operations/recovery-objectives-registry.v1.json",
    "scripts/request-memory-os-backup-restore-drill.py",
    "scripts/validate-memory-os-backup-restore-drill-request.py",
    "scripts/register-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence-negative.py",
    "scripts/reconcile-memory-os-backup-restore-generation-evidence.py",
    ".github/workflows/backup-restore-generation-evidence.yml",
)
MAX_REVIEWED_SOURCE_BYTES = 1024 * 1024
EVIDENCE_PREFIX = "generation-bound backup/restore evidence admission is append-only and fail-closed:"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def repo_relative(path: Path) -> Path:
    try:
        return path.resolve(strict=False).relative_to(ROOT.resolve())
    except (OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"authority path escapes repository: {path}") from exc


def require_repo_file(path: Path, message: str) -> Path:
    relative = repo_relative(path)
    require((ROOT / relative).is_file(), message)
    return relative


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    for path, expected, field in (
        (CONTRACT, CONTRACT_REL, "generation evidence contract"),
        (REGISTRY, REGISTRY_REL, "generation evidence registry"),
        (GEN_REGISTRY, GEN_REGISTRY_REL, "environment generation registry"),
        (OBJECTIVES_REGISTRY, OBJECTIVES_REGISTRY_REL, "recovery objectives registry"),
        (DRILL_REGISTRY, DRILL_REGISTRY_REL, "drill request registry"),
        (BINDING, BINDING_REL, "generation binding contract"),
        (WRITER, WRITER_REL, "generation evidence writer"),
        (VALIDATOR, VALIDATOR_REL, "generation evidence validator"),
        (BINDING_VALIDATOR, BINDING_VALIDATOR_REL, "generation binding validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (STATUS, STATUS_REL, "production operability status"),
    ):
        require_exact_repo_file(path, expected, field)


def read_text(path: Path) -> str:
    relative = repo_relative(path)
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Fail(f"cannot read {relative}: {exc}") from exc


def write_text(path: Path, text: str) -> None:
    relative = repo_relative(path)
    require(path.parent.is_dir(), f"authority parent missing: {relative.parent}")
    existing_mode = path.stat().st_mode & 0o7777 if path.exists() else None
    temp_name: str | None = None
    fd: int | None = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            text=True,
        )
        if existing_mode is not None:
            os.fchmod(fd, existing_mode)
        # Retain raw-FD ownership across stream use, including fdopen failure.
        with os.fdopen(fd, "w", encoding="utf-8", newline="", closefd=False) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        owned_fd = fd
        fd = None  # Do not retry a possibly post-effect numeric close.
        os.close(owned_fd)
        os.replace(temp_name, path)
        temp_name = None
    except OSError as exc:
        raise Fail(f"cannot atomically write {relative}: {exc}") from exc
    finally:
        if fd is not None:
            owned_fd = fd
            fd = None
            try:
                os.close(owned_fd)
            except OSError:
                pass  # Preserve the primary failure without a second close.
        if temp_name is not None:
            # A cleanup exception must not override the primary write failure.
            primary_failure = sys.exc_info()[0] is not None
            try:
                os.unlink(temp_name)
            except Exception as cleanup_exc:
                if not primary_failure:
                    raise Fail(f"cannot clean temporary authority for {relative}") from cleanup_exc


def restore_original_text(original_text: dict[Path, str]) -> None:
    failures: list[str] = []
    for path, text in original_text.items():
        try:
            write_text(path, text)
        except Exception as exc:
            failures.append(f"{repo_relative(path)}: {type(exc).__name__}: {exc}")
    if failures:
        raise Fail("generation evidence rollback restore failures: " + "; ".join(failures))


def load(path: Path) -> dict[str, Any]:
    relative = repo_relative(path)
    try:
        value = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {relative}")
    return value


def pinned_reviewed_source(path: Path, relative: Path, field: str) -> bytes:
    """Bind reviewed reviewed source bytes to owned directory/file descriptors, not a mutable path."""
    require_exact_repo_file(path, relative, field)
    require(all(hasattr(os, name) for name in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")),
            "generation evidence reviewed source pinned import platform unsafe")
    owned: list[int] = []
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        parent_fd = os.open(ROOT, directory_flags)
        require(type(parent_fd) is int and parent_fd >= 0, "reviewed source directory descriptor invalid")
        owned.append(parent_fd)
        for part in relative.parts[:-1]:
            parent_fd = os.open(part, directory_flags, dir_fd=parent_fd)
            require(type(parent_fd) is int and parent_fd >= 0, "reviewed source directory descriptor invalid")
            owned.append(parent_fd)
        before_parents = [os.fstat(fd) for fd in owned]
        parent_identity = lambda value: (
            value.st_dev, value.st_ino, value.st_mode, value.st_ctime_ns
        )
        require(all(stat.S_ISDIR(item.st_mode) and not (item.st_mode & 0o022)
                    for item in before_parents), "reviewed source parent directory unsafe")
        source_fd = os.open(
            relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=parent_fd,
        )
        require(type(source_fd) is int and source_fd >= 0, "reviewed source source descriptor invalid")
        owned.append(source_fd)
        before = os.fstat(source_fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and not (before.st_mode & 0o022)
                and 0 <= before.st_size <= MAX_REVIEWED_SOURCE_BYTES,
                "reviewed source source type/size unsafe")
        chunks: list[bytes] = []
        remaining = MAX_REVIEWED_SOURCE_BYTES + 1
        while remaining:
            chunk = os.read(source_fd, remaining)
            require(type(chunk) is bytes, "reviewed source source read type invalid")
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
        require(len(source) <= MAX_REVIEWED_SOURCE_BYTES
                and len(source) == before.st_size
                and identity(before) == identity(after) == identity(leaf),
                "reviewed source source changed during read")
        for index, fd in enumerate(owned[:-1]):
            current = os.fstat(fd)
            lexical = ROOT if index == 0 else ROOT.joinpath(*relative.parts[:index])
            visible = os.lstat(lexical)
            require(stat.S_ISDIR(visible.st_mode)
                    and parent_identity(before_parents[index])
                    == parent_identity(current) == parent_identity(visible),
                    "reviewed source parent changed during read")
        require_exact_repo_file(path, relative, field)
        require(identity(path.stat()) == identity(after),
                "reviewed source pathname changed during read")
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
            raise Fail("reviewed source descriptor cleanup failed") from None


def pinned_writer_source() -> bytes:
    return pinned_reviewed_source(WRITER, WRITER_REL, "generation evidence writer")


def load_writer():
    """Execute the canonical generation writer from verified pinned source bytes."""
    try:
        source = pinned_writer_source()
        spec = importlib.util.spec_from_file_location(
            "memory_os_backup_restore_generation_reconcile_writer", WRITER,
        )
        require(spec is not None and spec.loader is not None,
                "generation evidence canonical writer import failed")
        module = importlib.util.module_from_spec(spec)
        # Never reopen the mutable pathname through SourceFileLoader.
        exec(compile(source, str(WRITER), "exec"), module.__dict__)
    except Exception:
        raise Fail("generation evidence canonical writer import failed") from None
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


def run_post_validator(path: Path, expected_relative: Path, label: str) -> None:
    reviewed = {
        "generation binding validator": (BINDING_VALIDATOR, BINDING_VALIDATOR_REL),
        "generation evidence validator": (VALIDATOR, VALIDATOR_REL),
        "operability validator": (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL),
    }
    require(reviewed.get(label) == (path, expected_relative),
            "unreviewed generation evidence post-validator")
    source = pinned_reviewed_source(path, expected_relative, label)
    bootstrap = (
        "import os, sys\n"
        "path = sys.argv[1]\n"
        "sys.path.insert(0, os.path.dirname(path))\n"
        "sys.argv[:] = [path]\n"
        "scope = {'__name__': '__main__', '__file__': path, '__package__': None, '__spec__': None}\n"
        "exec(compile(sys.stdin.buffer.read(), path, 'exec'), scope)\n"
    )
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
            timeout=90,
        )
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        raise Fail(f"{label} unavailable or timed out (raw output withheld)") from None
    require(
        isinstance(completed, subprocess.CompletedProcess)
        and type(completed.returncode) is int and completed.returncode == 0,
        f"{label} failed (raw output withheld)",
    )


def main() -> int:
    enforce_runtime_authorities()
    original_text = {
        REGISTRY: read_text(REGISTRY),
        CONTRACT: read_text(CONTRACT),
        BINDING: read_text(BINDING),
        STATUS: read_text(STATUS),
    }
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    gen_registry = load(GEN_REGISTRY)
    objectives_registry = load(OBJECTIVES_REGISTRY)
    drill_registry = load(DRILL_REGISTRY)
    binding = load(BINDING)
    status = load(STATUS)
    writer = load_writer()

    try:
        writer.validate_registry_for_append(registry)
    except RuntimeError as exc:
        if exc.__class__.__name__ != "Fail":
            raise
        raise Fail(f"append-only generation recovery authority invalid before reconcile: {exc}") from exc

    rows = registry.get("records")
    count = registry.get("registeredEvidenceCount")
    generation_count = gen_registry.get("registeredGenerationCount")
    objective_count = objectives_registry.get("approvedObjectiveCount")
    current_objective_id = objectives_registry.get("currentObjectiveId")
    drill_rows = drill_registry.get("requests")
    drill_count = drill_registry.get("registeredRequestCount")
    current_drill_count = drill_registry.get("currentExecutableRequestCount")
    require(isinstance(rows, list) and writer.valid_count(count) and len(rows) == count, "recovery evidence registry count drift")
    require(all(writer.valid_count(value) for value in (generation_count, objective_count, drill_count, current_drill_count)), "recovery dependency counts invalid")
    require(isinstance(drill_rows, list) and drill_count == len(drill_rows), "drill request registry count drift")
    require(current_drill_count <= drill_count, "current drill request count invalid")

    for row in rows:
        writer.validate_record(row, require_current_drill_request=False)
    bound_count = len(rows)
    backup_count = sum(1 for row in rows if row.get("evidenceComplete") is True)
    restore_count = sum(
        1 for row in rows
        if row.get("evidenceComplete") is True
        and row.get("isolatedRestoreVerified") is True
        and row.get("restoredBackupArtifactSha256") == row.get("backupArtifactSha256")
    )
    candidate_count = sum(1 for row in rows if writer.candidate(row))
    require(0 <= candidate_count <= restore_count <= backup_count <= bound_count <= count, "rederived recovery evidence count ordering invalid")
    if generation_count == 0 or drill_count == 0:
        require(count == 0, "recovery evidence cannot exist without registered generations and reviewed drill request")
    if objective_count == 0:
        require(current_objective_id is None, "empty objective registry requires null currentObjectiveId")
    if objective_count == 0 or current_drill_count == 0:
        require(candidate_count == 0, "current candidate cannot survive without current objective and executable drill request")

    registry["drillRequestBoundEvidenceCount"] = bound_count
    registry["completeGenerationBoundBackupCount"] = backup_count
    registry["completeGenerationBoundRestoreCount"] = restore_count
    registry["productionEquivalentRecoveryCandidateCount"] = candidate_count
    registry["productionEvidence"] = False
    registry["productionReady"] = False
    limitations = registry.get("limitations")
    require(isinstance(limitations, list), "recovery evidence limitations missing")
    for text in (
        "new generation evidence requires one currently executable reviewed restore drill request with matching source, target and recovery objective",
        "historical generation evidence remains auditable after its drill request becomes stale, but it immediately stops qualifying as a current recovery candidate",
    ):
        append_once(limitations, text)

    boundary = contract.get("currentBoundary")
    readiness = contract.get("readiness")
    require(isinstance(boundary, dict) and isinstance(readiness, dict), "generation recovery contract authority missing")
    boundary["registeredEvidenceCount"] = count
    boundary["drillRequestBoundEvidenceCount"] = bound_count
    boundary["completeGenerationBoundBackupCount"] = backup_count
    boundary["completeGenerationBoundRestoreCount"] = restore_count
    boundary["productionEquivalentRecoveryCandidateCount"] = candidate_count
    boundary["productionEquivalentRestoreEvidence"] = candidate_count > 0
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"
    readiness["contractDefined"] = True
    readiness["registryDefined"] = True
    readiness["writerImplemented"] = True
    readiness["validatorImplemented"] = True
    readiness["reconcileImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["environmentGenerationAvailable"] = generation_count > 0
    readiness["approvedRecoveryObjectivesAvailable"] = objective_count > 0
    readiness["drillRequestAvailable"] = drill_count > 0
    readiness["generationBoundBackupAvailable"] = backup_count > 0
    readiness["generationBoundRestoreAvailable"] = restore_count > 0
    readiness["productionEquivalentRecoveryCandidateAvailable"] = candidate_count > 0
    readiness["independentReviewCompleted"] = candidate_count > 0
    readiness["productionEquivalentRestoreEvidence"] = candidate_count > 0
    readiness["productionReady"] = False

    binding_boundary = binding.get("currentBoundary")
    binding_readiness = binding.get("readiness")
    require(isinstance(binding_boundary, dict) and isinstance(binding_readiness, dict), "generation binding authority missing")
    binding_boundary["registeredProductionEquivalentGenerationCount"] = generation_count
    binding_boundary["generationBoundBackupCount"] = backup_count
    binding_boundary["generationBoundRestoreCount"] = restore_count
    binding_boundary["productionEquivalentRecoveryCandidateCount"] = candidate_count
    binding_boundary["productionEquivalentRestoreEvidence"] = candidate_count > 0
    binding_boundary["independentReviewCompleted"] = candidate_count > 0
    binding_boundary["humanProductionPromotionReviewCompleted"] = False
    binding_boundary["humanProductionPromotionAuthorized"] = False
    binding_boundary["productionEvidence"] = False
    binding_boundary["productionReady"] = False
    binding_boundary["productionDecision"] = "NO_GO"
    binding_readiness["generationEvidenceRegistryImplemented"] = True
    binding_readiness["environmentGenerationAvailable"] = generation_count > 0
    binding_readiness["generationBoundBackupAvailable"] = backup_count > 0
    binding_readiness["generationBoundRestoreAvailable"] = restore_count > 0
    binding_readiness["productionEquivalentRecoveryCandidateAvailable"] = candidate_count > 0
    binding_readiness["independentReviewCompleted"] = candidate_count > 0
    binding_readiness["humanProductionPromotionReviewCompleted"] = False
    binding_readiness["humanProductionPromotionAuthorized"] = False
    binding_readiness["productionEquivalentRestoreEvidence"] = candidate_count > 0
    binding_readiness["productionReady"] = False
    if generation_count == 0:
        binding["limitations"] = [
            "the existing exact-source local PostgreSQL and MinIO restore proofs remain local-only",
            "no production-equivalent environment generation or generation-bound recovery evidence is currently registered",
            "recovery objectives and reviewed restore drill requests remain separately governed and cannot be invented by restore evidence",
            "candidate-level independent evidence review is not human production-promotion review",
            "a production-equivalent recovery candidate cannot complete or authorize the separate human production-promotion decision",
            "production traffic and production credentials remain unnecessary and forbidden as automatic promotion shortcuts"
        ]
    else:
        binding["limitations"] = [
            "registered environment generations and generation-bound recovery records remain non-production evidence",
            "new generation recovery evidence requires a currently executable reviewed restore drill request",
            "a production-equivalent recovery candidate also requires the current approved recovery objective ID, measured RPO/RTO/object-database skew within target and complete typed non-resurrection coverage with independent evidence review",
            "candidate-level independent evidence review does not complete human production-promotion review",
            "production promotion remains a separate human-reviewed decision and is never authorized by candidate derivation",
            "local restore foundations cannot be relabeled into generation-bound evidence"
        ]

    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") in {"PARTIAL_FOUNDATIONS_ONLY", "PARTIAL"} and gate.get("blocking") is True, "OPS-P0-007 must remain blocking and incomplete")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    missing = gate.get("missingEvidence")
    require(isinstance(existing, list) and isinstance(refs, list) and isinstance(missing, list), "OPS-P0-007 authority arrays missing")
    require_canonical_gaps(missing, Fail)
    evidence = (
        f"{EVIDENCE_PREFIX} registered environment generations={generation_count}, approved recovery objectives={objective_count}, reviewed/current restore drill requests={drill_count}/{current_drill_count}, recovery records={count}, drill-request-bound records={bound_count}, complete generation-bound restores={restore_count}, production-equivalent recovery candidates={candidate_count}; candidate-level independent evidence review={str(candidate_count > 0).lower()}, human production-promotion review/authorization=false/false; immutable history is preserved after request supersession but current candidate derivation is recomputed fail-closed from the current request/objective/typed-evidence state, while productionEvidence and productionReady remain false"
    )
    replace_single_prefixed(existing, EVIDENCE_PREFIX, evidence)
    for ref in REFS:
        require_repo_file(ROOT / ref, f"generation recovery evidence ref missing: {ref}")
        append_once(refs, ref)

    rendered = {
        REGISTRY: json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
        CONTRACT: json.dumps(contract, indent=2, ensure_ascii=False) + "\n",
        BINDING: json.dumps(binding, indent=2, ensure_ascii=False) + "\n",
        STATUS: json.dumps(status, indent=2, ensure_ascii=False) + "\n",
    }
    try:
        for path, text in rendered.items():
            write_text(path, text)
        run_post_validator(BINDING_VALIDATOR, BINDING_VALIDATOR_REL, "generation binding validator")
        run_post_validator(VALIDATOR, VALIDATOR_REL, "generation evidence validator")
        run_post_validator(OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator")
    except Exception as exc:
        try:
            restore_original_text(original_text)
        except Fail as rollback_exc:
            raise Fail(f"generation evidence reconcile failed: {exc}; rollback incomplete: {rollback_exc}") from exc
        raise

    print("Memory OS drill-bound generation recovery authority reconciliation PASS")
    print("canonical generation evidence data/writer/validator authorities enforced: true")
    print(f"registered/current drill requests: {drill_count}/{current_drill_count}")
    print(f"registered/drill-bound recovery evidence: {count}/{bound_count}")
    print(f"production-equivalent recovery candidates: {candidate_count}")
    print(f"candidate-level independent evidence review complete: {str(candidate_count > 0).lower()}")
    print("human production-promotion review completed: false")
    print("human production promotion authorized: false")
    print("candidate counters rederived from append-only records: true")
    print("corrupt append-only registry auto-healed by reconcile: false")
    print("generation registry/contract/binding/status writes use mode-preserving atomic same-directory replace: true")
    print("failed post-validation leaves derived generation/status mutation behind: false")
    print("production evidence: false")
    print("OPS-P0-007: incomplete")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE GENERATION EVIDENCE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
