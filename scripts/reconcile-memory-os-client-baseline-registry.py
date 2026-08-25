#!/usr/bin/env python3
"""Reconcile reviewed client baseline authority without creating skew or production claims."""

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
CONTRACT_REL = Path("contracts/operations/client-baseline-registry-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/client-baseline-registry.v1.json")
SUPPORT_REL = Path("contracts/operations/client-server-support-window-contract.v1.json")
RELEASES_REL = Path("contracts/operations/release-baseline-registry.v1.json")
RELEASE_PAIRS_REL = Path("contracts/operations/release-compatibility-pair-registry.v1.json")
SKEW_REL = Path("contracts/operations/client-server-skew-registry.v1.json")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
WRITER_REL = Path("scripts/register-memory-os-client-baseline.py")
PAIR_WRITER_REL = Path("scripts/register-memory-os-release-compatibility-pair.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-client-baseline-registry.py")
SUPPORT_VALIDATOR_REL = Path("scripts/validate-memory-os-client-server-support-window.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
WORKFLOW_REL = Path(".github/workflows/client-baseline-registry.yml")
RUNBOOK_REL = Path("docs/evidence/clients/README.md")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
SUPPORT = ROOT / SUPPORT_REL
RELEASES = ROOT / RELEASES_REL
RELEASE_PAIRS = ROOT / RELEASE_PAIRS_REL
SKEW = ROOT / SKEW_REL
STATUS = ROOT / STATUS_REL
WRITER = ROOT / WRITER_REL
PAIR_WRITER = ROOT / PAIR_WRITER_REL
VALIDATOR = ROOT / VALIDATOR_REL
SUPPORT_VALIDATOR = ROOT / SUPPORT_VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
WORKFLOW = ROOT / WORKFLOW_REL
RUNBOOK = ROOT / RUNBOOK_REL

EVIDENCE = (
    "append-only reviewed client baseline authority now has an external-byte-verifying writer, fail-closed validator and operator runbook: exact iOS/Portal artifact SHA-256 and byte length are recomputed, source provenance and repository evidence are bound, CLIENT_OWNER/Security/Compatibility approvals must be distinct, and baseline approval remains explicitly separate from client/server skew and Production readiness"
)
REFS = (
    "contracts/operations/client-baseline-registry-contract.v1.json",
    "contracts/operations/client-baseline-registry.v1.json",
    "scripts/register-memory-os-client-baseline.py",
    "scripts/validate-memory-os-client-baseline-registry.py",
    "scripts/reconcile-memory-os-client-baseline-registry.py",
    "docs/evidence/clients/README.md",
    ".github/workflows/client-baseline-registry.yml",
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
    _registry: Path = REGISTRY,
    _support: Path = SUPPORT,
    _releases: Path = RELEASES,
    _release_pairs: Path = RELEASE_PAIRS,
    _skew: Path = SKEW,
    _status: Path = STATUS,
    _writer: Path = WRITER,
    _pair_writer: Path = PAIR_WRITER,
    _validator: Path = VALIDATOR,
    _support_validator: Path = SUPPORT_VALIDATOR,
    _operability_validator: Path = OPERABILITY_VALIDATOR,
    _workflow: Path = WORKFLOW,
    _runbook: Path = RUNBOOK,
    _require: Any = require,
    _require_exact_repo_file: Any = require_exact_repo_file,
) -> None:
    _require(ROOT == _root, "repository root authority drift")
    _require(require is _require, "require helper authority drift")
    _require(require_exact_repo_file is _require_exact_repo_file, "repository file authority helper drift")
    for current, expected, relative, field in (
        (CONTRACT, _contract, CONTRACT_REL, "client baseline contract"),
        (REGISTRY, _registry, REGISTRY_REL, "client baseline registry"),
        (SUPPORT, _support, SUPPORT_REL, "client/server support contract"),
        (RELEASES, _releases, RELEASES_REL, "release baseline registry"),
        (RELEASE_PAIRS, _release_pairs, RELEASE_PAIRS_REL, "release compatibility pair registry"),
        (SKEW, _skew, SKEW_REL, "client/server skew registry"),
        (STATUS, _status, STATUS_REL, "production operability status"),
        (WRITER, _writer, WRITER_REL, "client baseline writer"),
        (PAIR_WRITER, _pair_writer, PAIR_WRITER_REL, "release pair writer"),
        (VALIDATOR, _validator, VALIDATOR_REL, "client baseline validator"),
        (SUPPORT_VALIDATOR, _support_validator, SUPPORT_VALIDATOR_REL, "support-window validator"),
        (OPERABILITY_VALIDATOR, _operability_validator, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (WORKFLOW, _workflow, WORKFLOW_REL, "client baseline workflow"),
        (RUNBOOK, _runbook, RUNBOOK_REL, "client baseline runbook"),
    ):
        _require(current == expected, f"{field} runtime authority drift")
        _require_exact_repo_file(current, relative, field, _root=_root)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_module(path: Path, name: str) -> Any:
    require(path.is_file(), f"canonical authority missing: {path.relative_to(ROOT)}")
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load canonical authority: {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def run_validator(path: Path, label: str) -> None:
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    require(
        completed.returncode == 0,
        f"{label} failed:\n{completed.stdout[-4000:]}{completed.stderr[-4000:]}",
    )


def write_and_validate_transactionally(
    contract: dict[str, Any],
    support: dict[str, Any],
    status: dict[str, Any],
    *,
    _guard: Any = enforce_runtime_authorities,
) -> None:
    require(enforce_runtime_authorities is _guard, "runtime authority guard drift")
    _guard()
    paths = (CONTRACT, SUPPORT, STATUS)
    originals = {path: path.read_bytes() for path in paths}
    try:
        write(CONTRACT, contract)
        write(SUPPORT, support)
        write(STATUS, status)
        run_validator(VALIDATOR, "post-write client registry validator")
        run_validator(SUPPORT_VALIDATOR, "post-write support-window validator")
        run_validator(OPERABILITY_VALIDATOR, "post-write operability validator")
    except Exception:
        rollback_error: Exception | None = None
        for path in paths:
            try:
                atomic_write_bytes(path, originals[path])
            except Exception as exc:
                if rollback_error is None:
                    rollback_error = exc
        if rollback_error is not None:
            raise Fail(f"client baseline authority rollback failed: {rollback_error}") from rollback_error
        raise


def main(*, _guard: Any = enforce_runtime_authorities) -> int:
    require(enforce_runtime_authorities is _guard, "runtime authority guard drift")
    _guard()

    registry = load(REGISTRY)
    releases = load(RELEASES)
    release_pairs = load(RELEASE_PAIRS)
    skew = load(SKEW)
    support_validator = load_module(SUPPORT_VALIDATOR, "memory_os_support_window_for_client_reconcile")
    pair_writer = load_module(PAIR_WRITER, "memory_os_release_pair_for_client_reconcile")
    try:
        support_validator.validate_upstream_registries(releases, registry)
        skew_pair_count = support_validator.validate_skew_registry(skew)
        pair_writer.validate_registry_for_append(release_pairs)
    except Exception as exc:
        raise Fail(f"client baseline upstream authority invalid: {exc}") from exc
    require(
        skew_pair_count == 0,
        "client baseline foundation cannot overwrite admitted client/server skew authority",
    )
    approved_pair_count = release_pairs.get("approvedPairCount")
    require(
        isinstance(approved_pair_count, int) and not isinstance(approved_pair_count, bool) and approved_pair_count >= 0,
        "approved release pair count invalid",
    )

    clients = registry.get("clients")
    count = registry.get("approvedClientBaselineCount")
    latest = registry.get("latestApprovedClientByClass")
    require(
        isinstance(clients, list)
        and isinstance(count, int)
        and not isinstance(count, bool)
        and count == len(clients),
        "client registry count drift",
    )
    require(isinstance(latest, dict) and set(latest) == {"IOS_APP", "PORTAL"}, "client latest map drift")

    contract = load(CONTRACT)
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "client baseline readiness missing")
    readiness["writerImplemented"] = True
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["approvedClientBaselineCount"] = count
    readiness["approvedIOSBaselineAvailable"] = latest["IOS_APP"] is not None
    readiness["approvedPortalBaselineAvailable"] = latest["PORTAL"] is not None
    readiness["clientServerSkewEvidence"] = False
    readiness["productionReady"] = False
    contract["productionDecision"] = "NO_GO"

    release_count = releases.get("approvedReleaseCount")
    require(
        isinstance(release_count, int) and not isinstance(release_count, bool) and release_count >= 0,
        "release registry count invalid",
    )

    support = load(SUPPORT)
    boundary = support.get("currentBoundary")
    support_readiness = support.get("readiness")
    require(isinstance(boundary, dict) and isinstance(support_readiness, dict), "support window boundary/readiness missing")
    boundary["approvedBackendReleaseCount"] = release_count
    boundary["approvedClientBaselineCount"] = count
    boundary["admissibleSkewPairCount"] = 0
    boundary["implementedClientSupportWindow"] = False
    boundary["clientServerSkewEvidence"] = False
    boundary["releaseCompatibilityEvidence"] = False
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"
    support_readiness["approvedBackendReleaseAvailable"] = release_count > 0
    support_readiness["approvedClientBaselineAvailable"] = count > 0
    support_readiness["supportWindowImplemented"] = False
    support_readiness["skewPairExecuted"] = False
    support_readiness["independentReviewCompleted"] = False
    support_readiness["productionReady"] = False

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "client baseline authority cannot change production decision")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict), "OPS-P0-008 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True, "OPS-P0-008 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list), "OPS-P0-008 authority arrays missing")
    append_once(existing, EVIDENCE)
    for ref in REFS:
        require((ROOT / ref).is_file(), f"client baseline evidence ref missing: {ref}")
        append_once(refs, ref)
    joined = "\n".join(str(item).lower() for item in missing)
    require("client/server" in joined and "skew" in joined, "runtime client/server skew blocker must remain")
    pair_blocker_present = "approved predecessor" in joined and "successor" in joined
    if approved_pair_count == 0:
        require(pair_blocker_present, "approved release-pair blocker must remain")
    else:
        require(not pair_blocker_present, "approved release-pair blocker must stay cleared after pair admission")

    write_and_validate_transactionally(contract, support, status)

    print("Memory OS client baseline authority reconciliation PASS")
    print(f"approved client baselines: {count}")
    print(f"approved release pairs: {approved_pair_count}")
    print("external artifact writer: implemented")
    print("client/server skew evidence: false")
    print("OPS-P0-008: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"CLIENT BASELINE AUTHORITY RECONCILE FAILED: {exc}")
        raise SystemExit(1)
