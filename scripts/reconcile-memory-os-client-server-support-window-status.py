#!/usr/bin/env python3
"""Reconcile client/server support-window inventory without claiming any supported skew pair."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/client-server-support-window-contract.v1.json")
RELEASES_REL = Path("contracts/operations/release-baseline-registry.v1.json")
CLIENTS_REL = Path("contracts/operations/client-baseline-registry.v1.json")
SKEW_REL = Path("contracts/operations/client-server-skew-registry.v1.json")
VALIDATOR_REL = Path("scripts/validate-memory-os-client-server-support-window.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
WORKFLOW_REL = Path(".github/workflows/client-server-support-window.yml")
CONTRACT = ROOT / CONTRACT_REL
RELEASES = ROOT / RELEASES_REL
CLIENTS = ROOT / CLIENTS_REL
SKEW = ROOT / SKEW_REL
VALIDATOR = ROOT / VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
STATUS = ROOT / STATUS_REL
WORKFLOW = ROOT / WORKFLOW_REL

EVIDENCE_PREFIX = "client/server support-window admission foundation is machine-readable and fail-closed:"
EVIDENCE = (
    "client/server support-window admission foundation is machine-readable and fail-closed: approved backend release and approved client artifact "
    "digests are both mandatory, candidate/branch/CI evidence cannot manufacture support, and approved inventory may accumulate without creating "
    "a support window; admissibleSkewPairCount remains 0 while explicit old-client/new-server, new-client/old-server, session, Apply, deletion-fence, "
    "offline, minimum-version, rollback and retirement evidence remain required before any support window can exist"
)

REFS = (
    "contracts/operations/client-server-support-window-contract.v1.json",
    "contracts/operations/client-baseline-registry-contract.v1.json",
    "contracts/operations/client-server-skew-registry.v1.json",
    "scripts/validate-memory-os-client-server-support-window.py",
    ".github/workflows/client-server-support-window.yml",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_exact_repo_file(
    path: Path,
    expected_relative: Path,
    field: str,
    *,
    _root: Path = ROOT,
) -> Path:
    try:
        lexical = path.relative_to(_root)
        resolved = path.resolve(strict=True).relative_to(_root.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file() and not path.is_symlink(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities(
    *,
    _root: Path = ROOT,
    _contract: Path = CONTRACT,
    _releases: Path = RELEASES,
    _clients: Path = CLIENTS,
    _skew: Path = SKEW,
    _validator: Path = VALIDATOR,
    _operability_validator: Path = OPERABILITY_VALIDATOR,
    _status: Path = STATUS,
    _workflow: Path = WORKFLOW,
    _require: Any = require,
    _require_exact_repo_file: Any = require_exact_repo_file,
) -> None:
    _require(ROOT == _root, "repository root authority drift")
    _require(require is _require, "require helper authority drift")
    _require(
        require_exact_repo_file is _require_exact_repo_file,
        "repository file authority helper drift",
    )
    for current, expected, relative, field in (
        (CONTRACT, _contract, CONTRACT_REL, "support-window contract"),
        (RELEASES, _releases, RELEASES_REL, "release baseline registry"),
        (CLIENTS, _clients, CLIENTS_REL, "client baseline registry"),
        (SKEW, _skew, SKEW_REL, "client/server skew registry"),
        (VALIDATOR, _validator, VALIDATOR_REL, "support-window validator"),
        (OPERABILITY_VALIDATOR, _operability_validator, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (STATUS, _status, STATUS_REL, "production operability status"),
        (WORKFLOW, _workflow, WORKFLOW_REL, "support-window workflow"),
    ):
        _require(current == expected, f"{field} runtime authority drift")
        _require_exact_repo_file(current, relative, field, _root=_root)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    atomic_write_bytes(path, payload)


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def replace_prefixed_once(values: list[Any], prefix: str, value: str) -> None:
    indexes = [
        index
        for index, item in enumerate(values)
        if isinstance(item, str) and item.startswith(prefix)
    ]
    require(len(indexes) <= 1, f"duplicate evidence authority for prefix: {prefix}")
    if indexes:
        values[indexes[0]] = value
    else:
        values.append(value)


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("memory_os_support_window_reconcile_validator", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load support-window validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_validator(path: Path, label: str) -> None:
    completed = subprocess.run(
        [sys.executable, str(path)], cwd=ROOT, text=True, capture_output=True, check=False
    )
    require(
        completed.returncode == 0,
        f"{label} failed:\n{completed.stdout[-4000:]}{completed.stderr[-4000:]}",
    )


def write_and_validate_transactionally(
    contract: dict[str, Any],
    status: dict[str, Any],
    *,
    _guard: Any = enforce_runtime_authorities,
) -> None:
    require(enforce_runtime_authorities is _guard, "runtime authority guard drift")
    _guard()
    originals = {CONTRACT: CONTRACT.read_bytes(), STATUS: STATUS.read_bytes()}
    try:
        write(CONTRACT, contract)
        write(STATUS, status)
        run_validator(VALIDATOR, "post-write support-window validator")
        run_validator(OPERABILITY_VALIDATOR, "post-write operability validator")
    except Exception:
        rollback_error: Exception | None = None
        for path, payload in originals.items():
            try:
                atomic_write_bytes(path, payload)
            except Exception as exc:
                if rollback_error is None:
                    rollback_error = exc
        if rollback_error is not None:
            raise Fail(f"support-window authority rollback failed: {rollback_error}") from rollback_error
        raise


def main(*, _guard: Any = enforce_runtime_authorities) -> int:
    require(enforce_runtime_authorities is _guard, "runtime authority guard drift")
    _guard()
    validator = load_validator()
    releases = load(RELEASES)
    clients = load(CLIENTS)
    skew = load(SKEW)
    try:
        validator.validate_upstream_registries(releases, clients)
        pair_count = validator.validate_skew_registry(skew)
    except Exception as exc:
        raise Fail(f"support-window upstream authority invalid: {exc}") from exc

    release_count = releases.get("approvedReleaseCount")
    client_count = clients.get("approvedClientBaselineCount")
    require(isinstance(release_count, int) and not isinstance(release_count, bool) and release_count >= 0,
            "approved release count invalid")
    require(isinstance(client_count, int) and not isinstance(client_count, bool) and client_count >= 0,
            "approved client count invalid")
    require(pair_count == 0, "support-window reconcile cannot create or normalize skew pair authority")

    contract = load(CONTRACT)
    boundary = contract.get("currentBoundary")
    readiness = contract.get("readiness")
    require(isinstance(boundary, dict) and isinstance(readiness, dict), "support-window boundary/readiness missing")
    boundary["approvedBackendReleaseCount"] = release_count
    boundary["approvedClientBaselineCount"] = client_count
    boundary["admissibleSkewPairCount"] = 0
    boundary["implementedClientSupportWindow"] = False
    boundary["clientServerSkewEvidence"] = False
    boundary["releaseCompatibilityEvidence"] = False
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"
    readiness["approvedBackendReleaseAvailable"] = release_count > 0
    readiness["approvedClientBaselineAvailable"] = client_count > 0
    readiness["supportWindowImplemented"] = False
    readiness["skewPairExecuted"] = False
    readiness["independentReviewCompleted"] = False
    readiness["productionReady"] = False

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict), "OPS-P0-008 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True, "OPS-P0-008 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    missing = gate.get("missingEvidence")
    require(isinstance(existing, list) and isinstance(refs, list) and isinstance(missing, list), "OPS-P0-008 authority arrays missing")
    replace_prefixed_once(existing, EVIDENCE_PREFIX, EVIDENCE)
    for ref in REFS:
        require((ROOT / ref).is_file(), f"support-window evidence ref missing: {ref}")
        append_once(refs, ref)

    joined = "\n".join(str(item).lower() for item in missing)
    for term in ("client/server support windows", "old-client/new-server", "new-client/old-server"):
        require(term in joined, f"runtime client-skew blocker must remain: {term}")

    write_and_validate_transactionally(contract, status)
    print("Memory OS client/server support-window status reconciliation PASS")
    print(f"approved backend releases: {release_count}")
    print(f"approved client baselines: {client_count}")
    print("admissible skew pairs: 0")
    print("runtime support window: false")
    print("OPS-P0-008: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"CLIENT SERVER SUPPORT STATUS FAILED: {exc}")
        raise SystemExit(1)
