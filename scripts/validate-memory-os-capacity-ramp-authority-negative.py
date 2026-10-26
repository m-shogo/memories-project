#!/usr/bin/env python3
"""Prove capacity ramp direct reconcile pins canonical authorities and atomic rollback."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-capacity-ramp-status.py"


def load_module():
    spec = importlib.util.spec_from_file_location("capacity_ramp_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load capacity ramp reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejection(module, attr: str, replacement: Path) -> None:
    original = getattr(module, attr)
    setattr(module, attr, replacement)
    try:
        try:
            module.enforce_runtime_authorities()
        except module.ReconcileFailure:
            pass
        else:
            raise RuntimeError(f"{attr} substitution must be rejected")
    finally:
        setattr(module, attr, original)


def temp_residue(path: Path) -> list[Path]:
    return list(path.parent.glob(f".{path.name}.*.tmp"))


def verify_atomic_replace_failure(module) -> None:
    module.enforce_runtime_authorities()
    paths = (module.CONTRACT_PATH, module.LOAD_PATH, module.STATUS_PATH)
    originals = {path: path.read_bytes() for path in paths}
    residues_before = set(path for authority in paths for path in temp_residue(authority))
    original_replace = module.os.replace
    calls = 0

    def fail_first_replace(src, dst):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("synthetic capacity atomic replacement failure")
        original_replace(src, dst)

    module.os.replace = fail_first_replace
    try:
        rejected = False
        try:
            module.write_and_validate_transactionally(
                module.load(module.CONTRACT_PATH),
                module.load(module.LOAD_PATH),
                module.load(module.STATUS_PATH),
            )
        except BaseException as exc:
            rejected = True
            if "synthetic capacity atomic replacement failure" not in str(exc):
                raise RuntimeError(f"unexpected atomic rejection: {exc}") from exc
        if not rejected:
            raise RuntimeError("capacity ramp accepted synthetic atomic replacement failure")
        for path, payload in originals.items():
            if path.read_bytes() != payload:
                raise RuntimeError(f"atomic replacement failure mutated {path.relative_to(ROOT)}")
        residues_after = set(path for authority in paths for path in temp_residue(authority))
        if residues_after != residues_before:
            raise RuntimeError("capacity ramp atomic failure left temporary authority residue")
    finally:
        module.os.replace = original_replace
        for path, payload in originals.items():
            if path.read_bytes() != payload:
                module.atomic_write_bytes(path, payload)




def verify_capacity_strict_json_and_paths() -> None:
    """Use the actual reader and CLI contract binding with disposable JSON canaries."""
    validator_path = ROOT / "scripts/validate-memory-os-capacity-ramp.py"
    spec = importlib.util.spec_from_file_location("capacity_strict_reader_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("capacity strict reader import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    contract = validator.load(validator.CONTRACT_PATH)
    if contract.get("schemaVersion") != "memory-os-capacity-ramp.v1":
        raise RuntimeError("capacity contract positive read failed")
    canonical = validator.load(ROOT / contract["resultPath"])
    if canonical.get("schemaVersion") != "memory-os-capacity-ramp-results.v1":
        raise RuntimeError("capacity result positive read failed")
    with tempfile.TemporaryDirectory(prefix="capacity-reader-outside-") as outside_temp:
        outside = Path(outside_temp)
        canary = outside / "canary.json"
        canary.write_text('{"synthetic":true}', encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix=".capacity-reader-", dir=ROOT) as inside_temp:
            inside = Path(inside_temp)
            good = inside / "good.json"
            good.write_text('{"safe":true}', encoding="utf-8")
            if validator.load(good) != {"safe": True}:
                raise RuntimeError("capacity reader synthetic positive failed")
            malformed = (
                ("nested duplicate", '{"a":{"key":1,"key":2}}'),
                ("nonfinite constant", '{"value":NaN}'),
                ("nonfinite exponent", '{"value":1e999}'),
                ("oversized integer", '{"value":' + "9" * 5000 + '}'),
                ("nonobject root", '["safe"]'),
                ("synthetic secret malformed", '{"SYNTHETIC_CAPACITY_SECRET":'),
            )
            for label, raw in malformed:
                path = inside / (label.replace(" ", "-") + ".json")
                path.write_text(raw, encoding="utf-8")
                try:
                    validator.load(path)
                except validator.ValidationFailure as exc:
                    if "SYNTHETIC_CAPACITY_SECRET" in str(exc):
                        raise RuntimeError("capacity reader reflected synthetic secret") from None
                else:
                    raise RuntimeError(f"capacity reader accepted {label}")
            invalid_utf8 = inside / "invalid-utf8.json"
            invalid_utf8.write_bytes(b'{"value":"\\xff"}'.replace(b'\\xff', bytes([255])))
            try:
                validator.load(invalid_utf8)
            except validator.ValidationFailure:
                pass
            else:
                raise RuntimeError("capacity reader accepted invalid UTF-8")
            linked_file = inside / "linked.json"
            linked_file.symlink_to(canary)
            linked_parent = inside / "linked-parent"
            linked_parent.symlink_to(outside, target_is_directory=True)
            directory = inside / "directory.json"
            directory.mkdir()
            for label, unsafe in (
                ("external file", canary),
                ("direct symlink", linked_file),
                ("symlinked ancestor", linked_parent / "canary.json"),
                ("directory target", directory),
                ("missing file", inside / "missing.json"),
            ):
                try:
                    validator.load(unsafe)
                except validator.ValidationFailure:
                    pass
                else:
                    raise RuntimeError(f"capacity reader accepted {label}")
            contract_path = inside / "altered-contract.json"
            altered = copy.deepcopy(contract)
            altered["resultPath"] = str(canary)
            contract_path.write_text(json.dumps(altered), encoding="utf-8")
            original_contract = validator.CONTRACT_PATH
            validator.CONTRACT_PATH = contract_path
            try:
                try:
                    validator.main()
                except validator.ValidationFailure as exc:
                    if str(exc) != "capacity ramp result path drift":
                        raise RuntimeError("capacity result path rejected by wrong gate") from None
                else:
                    raise RuntimeError("capacity validator accepted external resultPath")
            finally:
                validator.CONTRACT_PATH = original_contract
        if canary.read_text(encoding="utf-8") != '{"synthetic":true}':
            raise RuntimeError("capacity strict reader changed external canary")
    print("PASS: capacity strict JSON positive and 13 malformed/path negatives plus resultPath binding")


def verify_capacity_numeric_boundary() -> None:
    """Exercise the real capacity validator with finite positive and nonfinite negatives."""
    validator_path = ROOT / "scripts/validate-memory-os-capacity-ramp.py"
    spec = importlib.util.spec_from_file_location("capacity_numeric_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("capacity numeric validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    if validator.positive_number(1.25, "synthetic-positive") != 1.25:
        raise RuntimeError("capacity numeric positive control failed")
    for label, bad in (
        ("Infinity", float("inf")),
        ("NaN", float("nan")),
        ("overflow integer", 10 ** 500),
        ("zero", 0),
    ):
        try:
            validator.positive_number(bad, "synthetic-negative")
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"capacity numeric validator accepted {label}")
    with tempfile.TemporaryDirectory(prefix=".capacity-numeric-negative-", dir=ROOT) as temp:
        path = Path(temp) / "synthetic.json"
        for label, raw in (("JSON Infinity", '{"value": Infinity}'),
                           ("JSON float overflow", '{"value": 1e999}')):
            path.write_text(raw, encoding="utf-8")
            try:
                validator.load(path)
            except validator.ValidationFailure:
                pass
            else:
                raise RuntimeError(f"capacity JSON parser accepted {label}")
    print("PASS: capacity numeric positive and 6 nonfinite/invalid negatives")



def verify_capacity_timestamp_semantics() -> None:
    """Validate a canonical UTC positive and seven timestamp negatives."""
    validator_path = ROOT / "scripts/validate-memory-os-capacity-ramp.py"
    spec = importlib.util.spec_from_file_location("capacity_timestamp_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("capacity timestamp validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    result_path = ROOT / "docs/fixtures/memory-os-operability/capacity-ramp-results.sample.v1.json"
    canonical = validator.load(result_path)
    validator.validate_capacity_timestamps(copy.deepcopy(canonical))
    cases = (
        ("impossible day", ("scenario", "startedAt"), "2026-02-30T21:38:38Z"),
        ("timezone offset", ("scenario", "startedAt"), "2026-09-22T21:38:38+00:00"),
        ("missing seconds", ("scenario", "startedAt"), "2026-09-22T21:38Z"),
        ("invalid fraction", ("scenario", "startedAt"), "2026-09-22T21:38:38.Z"),
        ("nonstrings", ("scenario", "startedAt"), None),
        ("completion before start", ("scenario", "completedAt"), "2026-09-22T21:38:37Z"),
        ("generation before completion", ("generatedAt",), "2026-09-22T21:38:40Z"),
    )
    for label, keys, value in cases:
        mutated = copy.deepcopy(canonical)
        cursor = mutated
        for key in keys[:-1]:
            cursor = cursor[key]
        cursor[keys[-1]] = value
        try:
            validator.validate_capacity_timestamps(mutated)
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"capacity timestamp validator accepted {label}")
    print("PASS: capacity UTC timestamp positive and 7 negatives")



def verify_capacity_batch_accounting() -> None:
    """Exercise the canonical full validator on disposable status and throughput mutations."""
    validator_path = ROOT / "scripts/validate-memory-os-capacity-ramp.py"
    spec = importlib.util.spec_from_file_location("capacity_batch_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("capacity batch validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    canonical_contract = validator.load(validator.CONTRACT_PATH)
    canonical_result = validator.load(ROOT / canonical_contract["resultPath"])
    cases = (
        ("float 2xx count", ("statusClassCounts", "2xx"), 240.0),
        ("boolean 5xx count", ("statusClassCounts", "5xx"), False),
        ("negative transport count", ("statusClassCounts", "transport_error"), -1),
        ("unknown status class", ("statusClassCounts", "6xx"), 1),
        ("unreported 3xx", ("statusClassCounts", "3xx"), 1),
        ("invented low throughput", ("throughput",), 0.001),
        ("derived throughput overflow", ("durationSeconds",), 5e-324),
    )
    original_contract = validator.CONTRACT_PATH
    with tempfile.TemporaryDirectory(prefix=".capacity-accounting-negative-", dir=ROOT) as tmp:
        contract_path = Path(tmp) / "contract.json"
        result_path = Path(tmp) / "result.json"
        contract = copy.deepcopy(canonical_contract)
        contract["resultPath"] = str(result_path.relative_to(ROOT))
        contract_path.write_text(json.dumps(contract), encoding="utf-8")
        validator.CONTRACT_PATH = contract_path
        try:
            result_path.write_text(json.dumps(canonical_result), encoding="utf-8")
            if validator.main() != 0:
                raise RuntimeError("capacity batch positive control failed")
            for label, keys, value in cases:
                mutated = copy.deepcopy(canonical_result)
                cursor = mutated["scenario"]["steps"][0]["batch"]
                for key in keys[:-1]:
                    cursor = cursor[key]
                cursor[keys[-1]] = value
                result_path.write_text(json.dumps(mutated), encoding="utf-8")
                try:
                    validator.main()
                except validator.ValidationFailure:
                    pass
                else:
                    raise RuntimeError(f"capacity batch validator accepted {label}")
        finally:
            validator.CONTRACT_PATH = original_contract
    print("PASS: capacity batch positive and 7 status/throughput negatives")


def main() -> int:
    module = load_module()
    verify_capacity_strict_json_and_paths()
    verify_capacity_numeric_boundary()
    verify_capacity_timestamp_semantics()
    verify_capacity_batch_accounting()
    substitutions = {
        "CONTRACT_PATH": module.LOAD_PATH,
        "LOAD_PATH": module.CONTRACT_PATH,
        "STATUS_PATH": module.LOAD_PATH,
        "RESULT_PATH": module.CONTRACT_PATH,
        "CAPACITY_VALIDATOR": module.LOAD_VALIDATOR,
        "LOAD_VALIDATOR": module.CAPACITY_VALIDATOR,
        "OPERABILITY_VALIDATOR": module.LOAD_VALIDATOR,
    }
    for attr, replacement in substitutions.items():
        expect_rejection(module, attr, replacement)
    module.enforce_runtime_authorities()
    verify_atomic_replace_failure(module)
    print("PASS: capacity ramp direct reconcile authorities are canonical and atomic")
    print("atomic replacement failure: rejected without authority mutation")
    print("temporary authority residue: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
