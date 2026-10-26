#!/usr/bin/env python3
"""Read-only actual-validator negatives for synthetic worker saturation evidence."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-deletion-worker-saturation.py"


def main() -> int:
    spec = importlib.util.spec_from_file_location("worker_saturation_strict_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("worker saturation validator loader missing")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    contract = validator.load(validator.CONTRACT_PATH)
    validator.validate_contract(contract)
    canonical = validator.load(validator.RESULT_PATH)
    validator.validate_result(contract, None)
    with tempfile.TemporaryDirectory(prefix="worker-saturation-reader-outside-") as outside_temp:
        outside = Path(outside_temp)
        canary = outside / "canary.json"
        canary.write_text('{"synthetic":true}', encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix=".worker-saturation-reader-", dir=ROOT) as inside_temp:
            inside = Path(inside_temp)
            good = inside / "good.json"
            good.write_text('{"safe":true}', encoding="utf-8")
            if validator.load(good) != {"safe": True}:
                raise RuntimeError("worker saturation reader positive failed")
            malformed = (
                ("nested duplicate", '{"a":{"key":1,"key":2}}'),
                ("NaN", '{"value":NaN}'),
                ("nonfinite exponent", '{"value":1e999}'),
                ("huge integer", '{"value":' + "9" * 5000 + '}'),
                ("nonobject root", '["safe"]'),
                ("synthetic secret malformed", '{"SYNTHETIC_WORKER_SECRET":'),
            )
            for label, raw in malformed:
                path = inside / (label.replace(" ", "-") + ".json")
                path.write_text(raw, encoding="utf-8")
                try:
                    validator.load(path)
                except validator.Fail as exc:
                    if "SYNTHETIC_WORKER_SECRET" in str(exc):
                        raise RuntimeError("worker saturation reader reflected synthetic secret") from None
                else:
                    raise RuntimeError(f"worker saturation reader accepted {label}")
            invalid_utf8 = inside / "invalid-utf8.json"
            invalid_utf8.write_bytes(b'{"value":"\\xff"}'.replace(b'\\xff', bytes([255])))
            try:
                validator.load(invalid_utf8)
            except validator.Fail:
                pass
            else:
                raise RuntimeError("worker saturation reader accepted invalid UTF-8")
            linked = inside / "linked.json"
            linked.symlink_to(canary)
            linked_parent = inside / "linked-parent"
            linked_parent.symlink_to(outside, target_is_directory=True)
            directory = inside / "directory.json"
            directory.mkdir()
            for label, unsafe in (
                ("external file", canary), ("direct symlink", linked),
                ("symlink ancestor", linked_parent / "canary.json"),
                ("directory", directory), ("missing", inside / "missing.json"),
            ):
                try:
                    validator.load(unsafe)
                except validator.Fail:
                    pass
                else:
                    raise RuntimeError(f"worker saturation reader accepted {label}")
            source_result = validator.RESULT_PATH
            path = inside / "synthetic-result.json"
            validator.RESULT_PATH = path
            try:
                def check(label, mutated, expected):
                    path.write_text(json.dumps(mutated), encoding="utf-8")
                    try:
                        validator.validate_result(contract, None)
                    except validator.Fail as exc:
                        if expected not in str(exc):
                            raise RuntimeError(f"worker saturation {label} rejected by wrong gate") from None
                    else:
                        raise RuntimeError(f"worker saturation accepted {label}")
                for key in ("workerErrors", "controlPreview5xx", "finalDeletionPending"):
                    mutated = copy.deepcopy(canonical)
                    mutated["scenario"][key] = False
                    check("boolean " + key, mutated, "result criterion mismatch")
                for key in ("deletingAccounts", "workerCount", "controlPreviewRequests"):
                    mutated = copy.deepcopy(canonical)
                    mutated["scenario"][key] = True
                    check("boolean " + key, mutated, "count mismatch")
                for label, marker in (
                    ("bearer", "bEaReR SYNTHETIC_NON_CREDENTIAL"),
                    ("presigned", "x-AmZ-CrEdEnTiAl=SYNTHETIC"),
                    ("postgres", "PoStGrEs://synthetic.invalid"),
                ):
                    mutated = copy.deepcopy(canonical)
                    mutated["environment"]["syntheticNegativeMarker"] = marker
                    check("sensitive " + label, mutated, "forbidden sensitive/runtime material")
                for label, timestamp in (
                    ("calendar", "2026-02-30T12:30:00Z"),
                    ("offset", "2026-09-11T02:22:34+00:00"),
                    ("missing seconds", "2026-09-11T02:22Z"),
                    ("nonstring", None),
                ):
                    mutated = copy.deepcopy(canonical)
                    mutated["generatedAt"] = timestamp
                    check("timestamp " + label, mutated, "generatedAt")
            finally:
                validator.RESULT_PATH = source_result
        if canary.read_text(encoding="utf-8") != '{"synthetic":true}':
            raise RuntimeError("worker saturation reader changed external canary")
    print("PASS: worker saturation strict JSON/path, typed accounting, UTC and sensitive marker negatives")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
