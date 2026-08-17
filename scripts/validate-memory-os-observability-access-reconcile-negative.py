#!/usr/bin/env python3
"""Prove observability access reconcile rolls back on post-write validation failure."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "contracts/operations/observability-event-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-observability-access.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-observability-access.py"
MARKER = Path("/tmp/memory-os-observability-access-post-write-negative.count")


def main() -> int:
    canonical_event = EVENT.read_bytes()
    canonical_status = STATUS.read_bytes()
    validator_bytes = VALIDATOR.read_bytes()

    event = json.loads(canonical_event.decode("utf-8"))
    retention = event.get("retention")
    if not isinstance(retention, dict):
        raise RuntimeError("observability event retention authority missing")
    retention["note"] = "negative fixture: force deterministic reconcile"
    EVENT.write_text(json.dumps(event, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    input_event = EVENT.read_bytes()
    input_status = STATUS.read_bytes()

    wrapper = f'''#!/usr/bin/env python3
from pathlib import Path
marker = Path({str(MARKER)!r})
count = int(marker.read_text(encoding="utf-8")) if marker.exists() else 0
marker.write_text(str(count + 1), encoding="utf-8")
raise SystemExit(0 if count == 0 else 1)
'''

    try:
        MARKER.unlink(missing_ok=True)
        VALIDATOR.write_text(wrapper, encoding="utf-8")
        completed = subprocess.run(
            ["python", str(RECONCILER)],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if completed.returncode == 0:
            raise RuntimeError("reconciler accepted injected post-write validator failure")
        if EVENT.read_bytes() != input_event:
            raise RuntimeError("post-write failure left observability event authority mutated")
        if STATUS.read_bytes() != input_status:
            raise RuntimeError("post-write failure left production operability status mutated")
    finally:
        VALIDATOR.write_bytes(validator_bytes)
        EVENT.write_bytes(canonical_event)
        STATUS.write_bytes(canonical_status)
        MARKER.unlink(missing_ok=True)

    print("PASS: observability access post-write validation failure rolls back event and status")
    print("productionDecision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
