#!/usr/bin/env python3
"""Prove the strict OPS-P0-007 snapshot validator cannot bypass canonical runtime authorities."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-ops-p0-007-admission-snapshot.py"
SNAPSHOT = ROOT / "contracts/operations/ops-p0-007-admission-snapshot.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module():
    require(VALIDATOR.is_file() and not VALIDATOR.is_symlink(), "canonical strict snapshot validator missing or symlinked")
    require(VALIDATOR.resolve(strict=True).relative_to(ROOT.resolve()) == VALIDATOR.relative_to(ROOT), "strict snapshot validator path drift")
    spec = importlib.util.spec_from_file_location("memory_os_ops_p0_007_snapshot_validator_authority_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load strict snapshot validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(module: Any, field: str, replacement: Any) -> None:
    # A failure at an unrelated validator must not count as the intended rejection.
    expected = {
        "enforce_runtime_authority": "strict snapshot validator execution guard drift",
        "require": "strict snapshot validator require helper drift",
        "valid_count": "strict snapshot validator execution helper drift",
        "load": "strict snapshot validator execution helper drift",
        "load_module": "strict snapshot validator execution helper drift",
        "validate_registry": "strict snapshot validator execution helper drift",
        "load_helper": "strict snapshot validator execution helper drift",
        "SNAPSHOT": "strict snapshot validator snapshot authority drift",
        "ELIGIBILITY_HELPER": "strict snapshot validator eligibility helper authority drift",
        "BLOCKER_HELPER": "strict snapshot validator blocker helper authority drift",
        "OBJECTIVES": "strict snapshot validator recovery objectives authority drift",
        "DRILL_REQUESTS": "strict snapshot validator drill requests authority drift",
        "GEN_EVIDENCE": "strict snapshot validator generation evidence authority drift",
        "TYPED": "strict snapshot validator typed non-resurrection authority drift",
        "STATUS": "strict snapshot validator production status authority drift",
        "OBJECTIVE_WRITER": "strict snapshot validator objective writer authority drift",
        "DRILL_REQUEST_WRITER": "strict snapshot validator drill request writer authority drift",
        "GEN_EVIDENCE_WRITER": "strict snapshot validator generation evidence writer authority drift",
        "TYPED_WRITER": "strict snapshot validator typed writer authority drift",
        "SNAPSHOT_FIELDS": "strict snapshot validator field authority drift",
        "DOWNSTREAM_REQUIREMENTS": "strict snapshot validator downstream requirement authority drift",
        "NEXT_ACTIONS": "strict snapshot validator next-action authority drift",
    }
    require(field in expected, f"unmapped strict snapshot authority negative: {field}")
    original = getattr(module, field)
    snapshot_before = SNAPSHOT.read_bytes()
    status_before = STATUS.read_bytes()
    snapshot_mode = SNAPSHOT.stat().st_mode & 0o7777
    status_mode = STATUS.stat().st_mode & 0o7777
    setattr(module, field, replacement)
    rejected = False
    try:
        module.main()
    except module.Fail as exc:
        require(str(exc) == expected[field], f"{field} rejected outside intended strict snapshot guard: {exc}")
        rejected = True
    finally:
        setattr(module, field, original)
    require(rejected, f"strict snapshot validator accepted substituted runtime authority: {field}")
    require(SNAPSHOT.read_bytes() == snapshot_before, f"{field} rejection mutated canonical strict snapshot")
    require(STATUS.read_bytes() == status_before, f"{field} rejection mutated canonical Production Status")
    require(SNAPSHOT.stat().st_mode & 0o7777 == snapshot_mode, f"{field} rejection changed strict snapshot file mode")
    require(STATUS.stat().st_mode & 0o7777 == status_mode, f"{field} rejection changed Production Status file mode")


def prove_json_reader_negative(module: Any) -> None:
    """Exercise the real strict snapshot JSON reader using disposable files only."""
    with tempfile.TemporaryDirectory(prefix="ops-p0-007-json-reader-", dir=ROOT) as directory:
        path = Path(directory) / "candidate.json"
        positive = b'{"safe":true,"nested":{"count":1}}'
        path.write_bytes(positive)
        require(
            module.load(path) == {"safe": True, "nested": {"count": 1}},
            "strict snapshot JSON reader positive control failed",
        )

        cases = (
            ("duplicate root", b'{"safe":true,"safe":false}', "strict snapshot JSON duplicate key refused"),
            ("duplicate nested", b'{"nested":{"a":1,"a":2}}', "strict snapshot JSON duplicate key refused"),
            ("NaN", b'{"number":NaN}', "strict snapshot JSON nonfinite number refused"),
            ("Infinity", b'{"number":Infinity}', "strict snapshot JSON nonfinite number refused"),
            ("negative Infinity", b'{"number":-Infinity}', "strict snapshot JSON nonfinite number refused"),
            ("float overflow", b'{"number":1e999}', "strict snapshot JSON nonfinite number refused"),
            ("oversized integer", b'{"number":' + b"9" * 5000 + b"}", "strict snapshot JSON integer too large"),
            ("oversized JSON", b'{"payload":"' + b"x" * module.MAX_JSON_BYTES + b'"}', "strict snapshot JSON size limit exceeded"),
            ("invalid UTF-8", b'{"private":"\\xff"}'.replace(b"\\xff", bytes([255])), "strict snapshot JSON unreadable or invalid"),
            ("malformed private input", b'{"private":"synthetic-secret",', "strict snapshot JSON unreadable or invalid"),
            ("non-object root", b"[]", "strict snapshot JSON root must be object"),
        )

        def rejected(candidate: Any, expected: str, label: str) -> None:
            try:
                module.load(candidate)
            except module.Fail as exc:
                require(str(exc) == expected, f"{label}: rejected outside exact JSON reader guard")
            else:
                raise Fail(f"{label}: unsafe JSON accepted")

        for label, payload, expected in cases:
            path.write_bytes(payload)
            rejected(path, expected, label)

        path.write_bytes(positive)
        alias = Path(directory) / "alias.json"
        alias.symlink_to(path)
        rejected(alias, "strict snapshot JSON path unsafe", "symlink")
        alias_dir = Path(directory) / "alias-dir"
        alias_dir.symlink_to(Path(directory), target_is_directory=True)
        rejected(alias_dir / path.name, "strict snapshot JSON path unsafe", "symlink ancestor")
        rejected(Path(directory), "strict snapshot JSON path unsafe", "directory")
        rejected("candidate.json", "strict snapshot JSON path invalid", "non-Path")
        with tempfile.TemporaryDirectory(prefix="ops-p0-007-external-canary-") as outside:
            canary = Path(outside) / "canary.json"
            canary.write_bytes(positive)
            rejected(canary, "strict snapshot JSON path missing or outside repository", "external path")
            require(canary.read_bytes() == positive, "external canary modified by JSON reader")
        path.unlink()
        rejected(path, "strict snapshot JSON path missing or outside repository", "missing path")


def main() -> int:
    module = load_module()
    baseline_snapshot = SNAPSHOT.read_bytes()
    baseline_status = STATUS.read_bytes()

    substitutions = (
        ("enforce_runtime_authority", lambda: None),
        ("require", lambda *_args: None),
        ("valid_count", lambda _value: True),
        ("load", lambda _path: {}),
        ("load_module", lambda *_args: object()),
        ("validate_registry", lambda *_args: []),
        ("load_helper", lambda: object()),
        ("SNAPSHOT", module.OBJECTIVES),
        ("ELIGIBILITY_HELPER", module.OBJECTIVE_WRITER),
        ("BLOCKER_HELPER", module.OBJECTIVE_WRITER),
        ("OBJECTIVES", module.DRILL_REQUESTS),
        ("DRILL_REQUESTS", module.OBJECTIVES),
        ("GEN_EVIDENCE", module.TYPED),
        ("TYPED", module.GEN_EVIDENCE),
        ("STATUS", module.OBJECTIVES),
        ("OBJECTIVE_WRITER", module.DRILL_REQUEST_WRITER),
        ("DRILL_REQUEST_WRITER", module.OBJECTIVE_WRITER),
        ("GEN_EVIDENCE_WRITER", module.TYPED_WRITER),
        ("TYPED_WRITER", module.GEN_EVIDENCE_WRITER),
        ("SNAPSHOT_FIELDS", set()),
        ("DOWNSTREAM_REQUIREMENTS", []),
        ("NEXT_ACTIONS", {}),
    )
    module.enforce_runtime_authority()
    prove_json_reader_negative(module)
    for field, replacement in substitutions:
        expect_rejected(module, field, replacement)

    module.enforce_runtime_authority()
    require(SNAPSHOT.read_bytes() == baseline_snapshot, "runtime authority probes mutated canonical strict snapshot")
    require(STATUS.read_bytes() == baseline_status, "runtime authority probes mutated canonical Production Status")
    json.loads(baseline_snapshot.decode("utf-8"))
    json.loads(baseline_status.decode("utf-8"))

    print("Memory OS OPS-P0-007 strict snapshot validator authority negative PASS")
    print(f"runtime authority substitutions rejected: {len(substitutions)}")
    print("validator execution guard substitution accepted: false")
    print("validator helper substitution accepted: false")
    print("validator data/executable authority substitution accepted: false")
    print("validator projection-shape substitution accepted: false")
    print("rejected probes mutated canonical snapshot/status: false")
    print("production evidence created: false")
    print("production ready: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, OSError, json.JSONDecodeError) as exc:
        print(f"OPS-P0-007 SNAPSHOT VALIDATOR AUTHORITY NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
