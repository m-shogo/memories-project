#!/usr/bin/env python3
"""Register exact-source parser process-group reaping evidence conservatively."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CONTRACT_PATH = ROOT / "contracts/operations/parser-process-group-reaping-contract.v1.json"
CANONICAL_RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/parser-process-group-reaping-results.sample.v1.json"
CANONICAL_STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_PROCESS_GROUP_VALIDATOR = ROOT / "scripts/validate-memory-os-parser-process-group-reaping.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
CONTRACT_PATH = CANONICAL_CONTRACT_PATH
RESULT_PATH = CANONICAL_RESULT_PATH
STATUS_PATH = CANONICAL_STATUS_PATH
PROCESS_GROUP_VALIDATOR = CANONICAL_PROCESS_GROUP_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

SATISFIED_MISSING = "independent child-process orphan/reaping scan after parser process-group termination"
EXISTING = (
    "exact-source Linux parser process-group reaping drill starts a synthetic child in the supervised worker group, independently observes at least two marked /proc members before cancellation, returns context.Canceled promptly, then proves every captured worker/child /proc entry disappears after Parse returns with zero spool residue; raw process identifiers are never persisted and this remains local CI evidence",
)
REFS = (
    "contracts/operations/parser-process-group-reaping-contract.v1.json",
    "docs/fixtures/memory-os-operability/parser-process-group-reaping-results.sample.v1.json",
    "services/import-api/internal/parsersup/supervisor_linux.go",
    "services/import-api/internal/parsersup/worker.go",
    "services/import-api/internal/parsersup/process_group_reaping_drill_linux_test.go",
    "scripts/validate-memory-os-parser-process-group-reaping.py",
    "scripts/reconcile-memory-os-parser-process-group-reaping.py",
    ".github/workflows/parser-process-group-reaping.yml",
)


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def _build_loader(
    require_impl: Callable[[bool, str], None],
    root: Path,
) -> Callable[[Path], dict[str, Any]]:
    def load(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ReconcileFailure(f"missing file: {path.relative_to(root)}") from exc
        except json.JSONDecodeError as exc:
            raise ReconcileFailure(f"invalid JSON in {path.relative_to(root)}: {exc}") from exc
        require_impl(isinstance(value, dict), f"root must be object: {path.relative_to(root)}")
        return value

    return load


load = _build_loader(require, ROOT)
del _build_loader


def _build_source_is_ancestor(
    run_impl: Callable[..., Any],
    root: Path,
) -> Callable[[str], bool]:
    def source_is_ancestor(source_sha: str) -> bool:
        try:
            return run_impl(
                ["git", "merge-base", "--is-ancestor", source_sha, "HEAD"],
                cwd=root,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode == 0
        except OSError:
            return False

    return source_is_ancestor


source_is_ancestor = _build_source_is_ancestor(subprocess.run, ROOT)
del _build_source_is_ancestor


def append_once(values: list[Any], value: str) -> bool:
    if value in values:
        return False
    values.append(value)
    return True


def _build_atomic_write_bytes(
    mkstemp_impl: Callable[..., tuple[int, str]],
    fdopen_impl: Callable[..., Any],
    fsync_impl: Callable[[int], None],
    chmod_impl: Callable[[Path, int], None],
    replace_impl: Callable[[Path, Path], None],
    require_impl: Callable[[bool, str], None],
    root: Path,
) -> Callable[[Path, bytes], None]:
    def atomic_write_bytes(path: Path, payload: bytes) -> None:
        require_impl(path.parent.is_dir(), f"authority parent missing: {path.parent}")
        mode = path.stat().st_mode & 0o7777
        temp_path: Path | None = None
        try:
            fd, temp_name = mkstemp_impl(
                prefix=f".{path.name}.",
                suffix=".tmp",
                dir=path.parent,
            )
            temp_path = Path(temp_name)
            with fdopen_impl(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                fsync_impl(handle.fileno())
            chmod_impl(temp_path, mode)
            replace_impl(temp_path, path)
            temp_path = None
        except OSError as exc:
            try:
                relative = path.relative_to(root)
            except ValueError:
                relative = path
            raise ReconcileFailure(f"cannot atomically write authority: {relative}: {exc}") from exc
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink()
                except FileNotFoundError:
                    pass
                except OSError:
                    pass

    return atomic_write_bytes


atomic_write_bytes = _build_atomic_write_bytes(
    tempfile.mkstemp,
    os.fdopen,
    os.fsync,
    os.chmod,
    os.replace,
    require,
    ROOT,
)
del _build_atomic_write_bytes


def _build_json_writer(
    atomic_writer: Callable[[Path, bytes], None],
) -> Callable[[Path, dict[str, Any]], None]:
    def write_json(path: Path, value: dict[str, Any]) -> None:
        payload = json.dumps(value, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
        atomic_writer(path, payload)

    return write_json


write_json = _build_json_writer(atomic_write_bytes)
del _build_json_writer


def _build_require_exact_authority(
    require_impl: Callable[[bool, str], None],
) -> Callable[[Path, Path, str], None]:
    def require_exact_authority(path: Path, canonical: Path, label: str) -> None:
        require_impl(path == canonical, f"{label} authority drift")
        require_impl(canonical.is_file(), f"canonical {label} missing")
        require_impl(not canonical.is_symlink(), f"canonical {label} cannot be a symlink")

    return require_exact_authority


require_exact_authority = _build_require_exact_authority(require)
del _build_require_exact_authority


def _build_data_authority_guard(
    require_exact_impl: Callable[[Path, Path, str], None],
    contract_authority: Path,
    result_authority: Path,
    status_authority: Path,
) -> Callable[[], None]:
    def enforce_data_authorities() -> None:
        require_exact_impl(CONTRACT_PATH, contract_authority, "process-group contract")
        require_exact_impl(RESULT_PATH, result_authority, "process-group result")
        require_exact_impl(STATUS_PATH, status_authority, "production operability status")

    return enforce_data_authorities


enforce_data_authorities = _build_data_authority_guard(
    require_exact_authority,
    CANONICAL_CONTRACT_PATH,
    CANONICAL_RESULT_PATH,
    CANONICAL_STATUS_PATH,
)
del _build_data_authority_guard


def _build_validator_runner(
    run_impl: Callable[..., Any],
    require_impl: Callable[[bool, str], None],
    executable: str,
    root: Path,
) -> Callable[..., None]:
    def run_validator(path: Path, *, expected_sha: str | None = None) -> None:
        require_impl(path.is_file(), f"canonical validator missing: {path.relative_to(root)}")
        require_impl(not path.is_symlink(), f"canonical validator cannot be a symlink: {path.relative_to(root)}")
        env = os.environ.copy()
        if expected_sha is not None:
            env["EXPECTED_COMMIT_SHA"] = expected_sha
        completed = run_impl(
            [executable, str(path)],
            cwd=root,
            env=env,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        require_impl(type(completed.returncode) is int and completed.returncode == 0,
                     f"canonical validator failed: {path.relative_to(root)}\n{completed.stdout}")

    return run_validator


run_validator = _build_validator_runner(subprocess.run, require, sys.executable, ROOT)
del _build_validator_runner


def _build_authority_validator_runner(
    data_guard: Callable[[], None],
    require_exact_impl: Callable[[Path, Path, str], None],
    validator_runner: Callable[..., None],
    process_group_validator_authority: Path,
    operability_validator_authority: Path,
) -> Callable[[str], None]:
    def run_authority_validators(source_sha: str) -> None:
        data_guard()
        require_exact_impl(
            PROCESS_GROUP_VALIDATOR,
            process_group_validator_authority,
            "process-group validator",
        )
        require_exact_impl(
            OPERABILITY_VALIDATOR,
            operability_validator_authority,
            "operability validator",
        )
        validator_runner(PROCESS_GROUP_VALIDATOR, expected_sha=source_sha)
        validator_runner(OPERABILITY_VALIDATOR)

    return run_authority_validators


run_authority_validators = _build_authority_validator_runner(
    enforce_data_authorities,
    require_exact_authority,
    run_validator,
    CANONICAL_PROCESS_GROUP_VALIDATOR,
    CANONICAL_OPERABILITY_VALIDATOR,
)
del _build_authority_validator_runner


def _build_commit_candidate(
    data_guard: Callable[[], None],
    json_writer: Callable[[Path, dict[str, Any]], None],
    atomic_writer: Callable[[Path, bytes], None],
    default_validator_runner: Callable[[str], None],
) -> Callable[..., None]:
    def commit_candidate(
        contract: dict[str, Any],
        status: dict[str, Any],
        source_sha: str,
        *,
        validator_runner: Callable[[str], None] | None = None,
    ) -> None:
        data_guard()
        original_contract = CONTRACT_PATH.read_bytes()
        original_status = STATUS_PATH.read_bytes()
        try:
            json_writer(CONTRACT_PATH, contract)
            json_writer(STATUS_PATH, status)
            if validator_runner is None:
                default_validator_runner(source_sha)
            else:
                validator_runner(source_sha)
        except BaseException:
            atomic_writer(CONTRACT_PATH, original_contract)
            atomic_writer(STATUS_PATH, original_status)
            raise

    return commit_candidate


commit_candidate = _build_commit_candidate(
    enforce_data_authorities,
    write_json,
    atomic_write_bytes,
    run_authority_validators,
)
del _build_commit_candidate


def _build_main(
    data_guard: Callable[[], None],
    load_impl: Callable[[Path], dict[str, Any]],
    require_impl: Callable[[bool, str], None],
    source_ancestor_impl: Callable[[str], bool],
    validator_runner: Callable[[str], None],
    append_once_impl: Callable[[list[Any], str], bool],
    commit_impl: Callable[..., None],
    sha_fullmatch: Callable[[str], Any],
    root: Path,
    contract_path: Path,
    result_path: Path,
    status_path: Path,
    satisfied_missing: str,
    existing_items: tuple[str, ...],
    evidence_refs: tuple[str, ...],
) -> Callable[[], int]:
    def main() -> int:
        data_guard()
        result = load_impl(result_path)
        source_sha = result.get("commitSha")
        require_impl(isinstance(source_sha, str) and sha_fullmatch(source_sha) is not None,
                     "process-group reaping result source SHA invalid")
        require_impl(source_ancestor_impl(source_sha),
                     "process-group reaping result source SHA is not an ancestor of HEAD")

        # The canonical validator owns contract/result semantics. Validate the exact
        # source before interpreting any derived fields or mutating canonical state.
        validator_runner(source_sha)

        contract = load_impl(contract_path)
        readiness = contract.get("readiness")
        refs = contract.get("evidenceRefs")
        require_impl(isinstance(readiness, dict) and isinstance(refs, list),
                     "process-group reaping contract readiness/refs missing")
        changed = False
        for key in ("exactSourcePassResultCommitted", "childProcessOrphanScanCompleted"):
            if readiness.get(key) is not True:
                readiness[key] = True
                changed = True
        if append_once_impl(refs, str(result_path.relative_to(root))):
            changed = True
        require_impl(readiness.get("hostRestartExecuted") is False and
                     readiness.get("productionArtifactExecuted") is False and
                     readiness.get("productionReady") is False,
                     "local reaping evidence cannot promote production boundaries")

        status = load_impl(status_path)
        require_impl(status.get("productionDecision") == "NO_GO",
                     "process-group reaping evidence cannot change production decision")
        gate = next((item for item in status.get("areas", [])
                     if isinstance(item, dict) and item.get("id") == "OPS-P0-009"), None)
        require_impl(isinstance(gate, dict) and gate.get("status") == "PARTIAL" and
                     gate.get("blocking") is True,
                     "OPS-P0-009 must remain blocking PARTIAL")
        existing = gate.get("existingEvidence")
        missing = gate.get("missingEvidence")
        status_evidence_refs = gate.get("evidenceRefs")
        require_impl(isinstance(existing, list) and isinstance(missing, list) and
                     isinstance(status_evidence_refs, list),
                     "OPS-P0-009 authority arrays missing")

        while satisfied_missing in missing:
            missing.remove(satisfied_missing)
            changed = True
        for item in existing_items:
            if append_once_impl(existing, item):
                changed = True
        for ref in evidence_refs:
            require_impl((root / ref).is_file(), f"process-group reaping evidence path missing: {ref}")
            if append_once_impl(status_evidence_refs, ref):
                changed = True

        joined = "\n".join(missing)
        for phrase in (
            "production multi-instance",
            "production-shaped object-store",
            "production-shaped PostgreSQL",
            "parser host or container restart",
            "host or container restart",
            "mixed-version failure",
        ):
            require_impl(phrase in joined, f"required production-shaped failure gap disappeared: {phrase}")
        require_impl(satisfied_missing not in missing,
                     "completed child-process orphan/reaping gap remained stale")

        if not changed:
            validator_runner(source_sha)
            print("Parser process-group reaping authority already reconciled")
            return 0

        status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
        commit_impl(contract, status, source_sha)
        print("Registered exact-source parser process-group reaping evidence")
        print("child-process orphan/reaping gap: satisfied locally")
        print("OPS-P0-009: PARTIAL")
        print("production decision: NO_GO")
        return 0

    return main


main = _build_main(
    enforce_data_authorities,
    load,
    require,
    source_is_ancestor,
    run_authority_validators,
    append_once,
    commit_candidate,
    SHA_RE.fullmatch,
    ROOT,
    CANONICAL_CONTRACT_PATH,
    CANONICAL_RESULT_PATH,
    CANONICAL_STATUS_PATH,
    SATISFIED_MISSING,
    tuple(EXISTING),
    tuple(REFS),
)
del _build_main


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"PARSER PROCESS-GROUP REAPING RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
