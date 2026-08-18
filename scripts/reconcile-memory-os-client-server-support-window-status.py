#!/usr/bin/env python3
"""Reconcile client/server support-window inventory without claiming any supported skew pair."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/client-server-support-window-contract.v1.json"
RELEASES = ROOT / "contracts/operations/release-baseline-registry.v1.json"
CLIENTS = ROOT / "contracts/operations/client-baseline-registry.v1.json"
SKEW = ROOT / "contracts/operations/client-server-skew-registry.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-client-server-support-window.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"

EVIDENCE = (
    "client/server support-window admission foundation is machine-readable and fail-closed: approved backend release and approved client artifact "
    "digests are both mandatory, candidate/branch/CI evidence cannot manufacture support, and approved inventory may accumulate without creating "
    "a support window; admissibleSkewPairCount remains 0 while explicit old-client/new-server, new-client/old-server, session, Apply, deletion-fence, "
    "offline, minimum-version, rollback and retirement evidence remain required before any support window can exist"
)

REFS = (
    "contracts/operations/client-server-support-window-contract.v1.json",
    "contracts/operations/client-baseline-registry.v1.json",
    "contracts/operations/client-server-skew-registry.v1.json",
    "scripts/validate-memory-os-client-server-support-window.py",
    ".github/workflows/client-server-support-window.yml",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
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


def write_and_validate_transactionally(contract: dict[str, Any], status: dict[str, Any]) -> None:
    originals = {CONTRACT: CONTRACT.read_bytes(), STATUS: STATUS.read_bytes()}
    try:
        write(CONTRACT, contract)
        write(STATUS, status)
        run_validator(VALIDATOR, "post-write support-window validator")
        run_validator(OPERABILITY_VALIDATOR, "post-write operability validator")
    except Exception:
        for path, payload in originals.items():
            path.write_bytes(payload)
        raise


def main() -> int:
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
    existing[:] = [item for item in existing if not (isinstance(item, str) and item.startswith("client/server support-window admission foundation is machine-readable and fail-closed:"))]
    append_once(existing, EVIDENCE)
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
