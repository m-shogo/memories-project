#!/usr/bin/env python3
"""Register client/server support-window admission foundation without claiming any supported skew pair."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/client-server-support-window-contract.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-client-server-support-window.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"

EVIDENCE = (
    "client/server support-window admission foundation is machine-readable and fail-closed: approved backend release and approved client artifact "
    "digests are both mandatory, candidate/branch/CI evidence cannot manufacture support, and the current empty approved-backend plus approved-client "
    "registries force admissibleSkewPairCount=0 while explicit old-client/new-server, new-client/old-server, session, Apply, deletion-fence, offline, "
    "minimum-version, rollback and retirement evidence remain required before any support window can exist"
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


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def main() -> int:
    subprocess.run(["python", str(VALIDATOR)], cwd=ROOT, check=True)
    contract = load(CONTRACT)
    boundary = contract.get("currentBoundary", {})
    require(boundary.get("approvedBackendReleaseCount") == 0, "approved backend release unexpectedly available")
    require(boundary.get("approvedClientBaselineCount") == 0, "approved client baseline unexpectedly available")
    require(boundary.get("admissibleSkewPairCount") == 0, "skew pair unexpectedly admitted")
    for key in ("implementedClientSupportWindow", "clientServerSkewEvidence", "releaseCompatibilityEvidence", "productionEvidence", "productionReady"):
        require(boundary.get(key) is False, f"support foundation cannot enable {key}")
    require(boundary.get("productionDecision") == "NO_GO", "support foundation cannot change production decision")

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict), "OPS-P0-008 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True, "OPS-P0-008 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    missing = gate.get("missingEvidence")
    require(isinstance(existing, list) and isinstance(refs, list) and isinstance(missing, list), "OPS-P0-008 authority arrays missing")
    append_once(existing, EVIDENCE)
    for ref in REFS:
        require((ROOT / ref).is_file(), f"support-window evidence ref missing: {ref}")
        append_once(refs, ref)

    joined = "\n".join(str(item).lower() for item in missing)
    for term in ("client support windows", "old-client/new-server", "new-client/old-server"):
        require(term in joined, f"runtime client-skew blocker must remain: {term}")

    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Memory OS client/server support-window status reconciliation PASS")
    print("admission foundation: defined")
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
