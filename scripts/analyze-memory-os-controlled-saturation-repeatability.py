#!/usr/bin/env python3
"""Analyze two exact-source controlled-saturation runs without promoting capacity readiness."""

from __future__ import annotations

import argparse
import json
import math
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/controlled-saturation-repeatability-contract.v1.json"
OUTPUT = ROOT / "docs/fixtures/memory-os-operability/controlled-saturation-repeatability-results.v1.json"
CANONICAL_OUTPUT = OUTPUT
STEPS = [4, 8, 16, 24, 32, 48]


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def reject_nonfinite_constant(value: str) -> None:
    raise Fail("non-finite JSON constant rejected")


def parse_finite_float(value: str) -> float:
    parsed = float(value)
    require(math.isfinite(parsed), "non-finite JSON number rejected")
    return parsed


def finite_nonnegative(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value)) and value >= 0
    except (OverflowError, ValueError):
        return False


def load(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject_nonfinite_constant,
        parse_float=parse_finite_float,
    )
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def safe_run_path(value: str) -> Path:
    require(isinstance(value, str) and value, "run path missing")
    relative = Path(value)
    require(not relative.is_absolute() and ".." not in relative.parts, "run path must be repository-relative")
    path = ROOT / relative
    for candidate in (path, *path.parents):
        require(not candidate.is_symlink(), "run path symlink rejected")
    require(path.is_file(), "run path missing")
    try:
        path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except ValueError:
        raise Fail("run path escaped repository") from None
    return path


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    require(path.parent.is_dir(), "repeatability result parent missing")
    for candidate in (path, *path.parents):
        require(not candidate.is_symlink(), "repeatability result symlink rejected")
    require(not path.is_dir(), "repeatability result directory target rejected")
    try:
        path.parent.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except ValueError:
        raise Fail("repeatability result escaped repository") from None
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            tmp_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fchmod(handle.fileno(), mode)
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        tmp_path = None
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass


def signal_for(result: dict[str, Any]) -> dict[str, Any]:
    env = result.get("environment")
    scenario = result.get("scenario")
    require(isinstance(env, dict) and isinstance(scenario, dict), "result environment/scenario missing")
    require(result.get("schemaVersion") == "memory-os-controlled-saturation-ramp-results.v1", "source result schema drift")
    require(env.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "source dependency mode drift")
    require(env.get("syntheticDataOnly") is True and env.get("loopbackDependenciesOnly") is True, "source must remain loopback synthetic")
    for key in ("productionTraffic", "productionCredentials", "productionEvidence", "productionEquivalentDependencies", "containsSecrets"):
        require(env.get(key) is False, f"unsafe source environment flag: {key}")
    require(scenario.get("scenarioId") == "signed-upload-controlled-saturation-ramp-local-dependencies", "source scenario drift")
    require(scenario.get("result") == "PASS" and scenario.get("integrityResult") == "PASS",
            "source ramp result and integrity must both PASS")
    require(scenario.get("requestsPerStep") == 64, "source requestsPerStep drift")
    rows = scenario.get("steps")
    require(isinstance(rows, list) and len(rows) == len(STEPS), "source steps incomplete")
    for index, concurrency in enumerate(STEPS):
        row = rows[index]
        require(isinstance(row, dict) and row.get("concurrency") == concurrency, f"source step {index} drift")
        batch = row.get("batch")
        delta = row.get("poolDelta")
        require(isinstance(batch, dict) and isinstance(delta, dict), f"source step {index} measurements missing")
        require(batch.get("requests") == 64, f"source step {index} request count drift")
        require(finite_nonnegative(batch.get("throughput")), f"source step {index} throughput invalid")
        require(finite_nonnegative(batch.get("latencyP95Ms")), f"source step {index} p95 invalid")
        require(type(delta.get("emptyAcquireCount")) is int and delta["emptyAcquireCount"] >= 0, f"source step {index} contention invalid")
    actual = scenario.get("firstSaturationSignal")
    if actual is not None:
        require(actual in STEPS, "actual saturation signal outside configured steps")
        return {"concurrency": actual, "kind": "ACTUAL_FAILURE_SIGNAL"}
    for index in range(1, len(rows)):
        previous = rows[index - 1]
        current = rows[index]
        prev_batch = previous["batch"]
        batch = current["batch"]
        prev_tp = float(prev_batch["throughput"])
        current_tp = float(batch["throughput"])
        prev_p95 = float(prev_batch["latencyP95Ms"])
        current_p95 = float(batch["latencyP95Ms"])
        if prev_tp <= 0 or prev_p95 <= 0:
            continue
        gain = (current_tp - prev_tp) / prev_tp
        p95_ratio = current_p95 / prev_p95
        contention = current["poolDelta"]["emptyAcquireCount"] > 0
        if contention and gain <= 0.05 and p95_ratio >= 1.25:
            return {
                "concurrency": current["concurrency"],
                "kind": "THROUGHPUT_LATENCY_KNEE",
                "throughputGainFromPrevious": gain,
                "p95LatencyRatioFromPrevious": p95_ratio,
            }
    return {"concurrency": None, "kind": "NO_SIGNAL"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-a", required=True)
    parser.add_argument("--run-b", required=True)
    args = parser.parse_args()
    contract = load(CONTRACT)
    require(contract.get("schemaVersion") == "memory-os-controlled-saturation-repeatability.v1", "contract schema drift")
    a_path = safe_run_path(args.run_a)
    b_path = safe_run_path(args.run_b)
    require(a_path != b_path, "two distinct run files are required")
    a = load(a_path)
    b = load(b_path)
    sha_a = a.get("commitSha")
    sha_b = b.get("commitSha")
    require(isinstance(sha_a, str) and len(sha_a) == 40 and sha_a == sha_b, "two runs must bind the same exact source commit")
    signal_a = signal_for(a)
    signal_b = signal_for(b)
    ca = signal_a["concurrency"]
    cb = signal_b["concurrency"]
    repeatable = False
    step_distance = None
    if ca is not None and cb is not None:
        step_distance = abs(STEPS.index(ca) - STEPS.index(cb))
        repeatable = step_distance <= 1
    document = {
        "schemaVersion": "memory-os-controlled-saturation-repeatability-results.v1",
        "sourceCommitSha": sha_a,
        "runRefs": [str(a_path.relative_to(ROOT)), str(b_path.relative_to(ROOT))],
        "independentRunCount": 2,
        "signals": {"a": signal_a, "b": signal_b},
        "signalStepDistance": step_distance,
        "repeatableLocalDegradationSignalObserved": repeatable,
        "capacityBoundaryEstablished": False,
        "operationalThresholdApproved": False,
        "independentReviewCompleted": False,
        "productionEquivalentEvidence": False,
        "productionEvidence": False,
        "productionReady": False,
        "productionDecision": "NO_GO",
        "result": "PASS" if repeatable else "INCONCLUSIVE",
        "limitations": contract.get("limitations", []),
    }
    require(OUTPUT == CANONICAL_OUTPUT, "repeatability output authority drift")
    atomic_write_bytes(OUTPUT, (json.dumps(document, indent=2) + "\n").encode("utf-8"))
    print("Memory OS controlled saturation repeatability analysis complete")
    print(f"signal a: {signal_a}")
    print(f"signal b: {signal_b}")
    print(f"repeatable local degradation: {repeatable}")
    print("capacity boundary established: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"CONTROLLED SATURATION REPEATABILITY ANALYSIS FAILED: {exc}")
        raise SystemExit(1)
