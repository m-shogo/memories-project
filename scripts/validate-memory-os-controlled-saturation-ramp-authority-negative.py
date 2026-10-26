#!/usr/bin/env python3
"""Prove controlled saturation direct reconcile pins canonical source authorities and atomic rollback."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-controlled-saturation-ramp-status.py"


def load_module():
    spec = importlib.util.spec_from_file_location("controlled_saturation_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load controlled saturation reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejection(module, attr: str, replacement: Path) -> None:
    original = getattr(module, attr)
    setattr(module, attr, replacement)
    try:
        try:
            module.enforce_runtime_authorities()
        except SystemExit:
            pass
        else:
            raise RuntimeError(f"{attr} substitution must be rejected")
    finally:
        setattr(module, attr, original)


def temp_residue(path: Path) -> list[Path]:
    return list(path.parent.glob(f".{path.name}.*.tmp"))


def verify_atomic_replace_failure(module) -> None:
    module.enforce_runtime_authorities()
    paths = module.TRANSACTION_PATHS
    originals = {path: path.read_bytes() for path in paths}
    residues_before = set(path for authority in paths for path in temp_residue(authority))
    original_replace = module.os.replace
    calls = 0

    def fail_first_replace(src, dst):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("synthetic controlled saturation atomic replacement failure")
        original_replace(src, dst)

    module.os.replace = fail_first_replace
    try:
        rejected = False
        try:
            module.write_transactionally(
                module.load(module.CONTROLLED_CONTRACT),
                module.load(module.LOAD_CONTRACT),
                module.load(module.STATUS_PATH),
                module.load(module.RESULT_PATH)["commitSha"],
            )
        except BaseException as exc:
            rejected = True
            if "synthetic controlled saturation atomic replacement failure" not in str(exc):
                raise RuntimeError(f"unexpected atomic rejection: {exc}") from exc
        if not rejected:
            raise RuntimeError("controlled saturation accepted synthetic atomic replacement failure")
        for path, payload in originals.items():
            if path.read_bytes() != payload:
                raise RuntimeError(f"atomic replacement failure mutated {path.relative_to(ROOT)}")
        residues_after = set(path for authority in paths for path in temp_residue(authority))
        if residues_after != residues_before:
            raise RuntimeError("controlled saturation atomic failure left temporary authority residue")
    finally:
        module.os.replace = original_replace
        for path, payload in originals.items():
            if path.read_bytes() != payload:
                module.atomic_write_bytes(path, payload)


def verify_atomic_path_negatives(module) -> None:
    with tempfile.TemporaryDirectory(prefix="controlled-saturation-outside-") as outside_temp:
        outside = Path(outside_temp)
        canary = outside / "canary.json"
        canary.write_bytes(b"SYNTHETIC_CONTROLLED_SATURATION_CANARY")
        with tempfile.TemporaryDirectory(prefix=".controlled-saturation-atomic-", dir=ROOT) as inside_temp:
            inside = Path(inside_temp)
            target = inside / "authority.json"
            target.write_bytes(b"original")
            target.chmod(0o640)
            module.atomic_write_bytes(target, b"updated")
            if target.read_bytes() != b"updated" or module.stat.S_IMODE(target.stat().st_mode) != 0o640:
                raise RuntimeError("controlled saturation atomic mode preservation failed")
            new = inside / "new.json"
            module.atomic_write_bytes(new, b"new")
            if new.read_bytes() != b"new" or module.stat.S_IMODE(new.stat().st_mode) != 0o644:
                raise RuntimeError("controlled saturation atomic new-file mode drift")
            linked_file = inside / "linked.json"
            linked_file.symlink_to(canary)
            linked_parent = inside / "linked-parent"
            linked_parent.symlink_to(outside, target_is_directory=True)
            directory = inside / "directory"
            directory.mkdir()
            for unsafe in (linked_file, linked_parent / "canary.json", directory,
                           inside / "missing-parent" / "file.json", canary):
                try:
                    module.atomic_write_bytes(unsafe, b"FORBIDDEN")
                except SystemExit:
                    pass
                else:
                    raise RuntimeError("controlled saturation atomic writer accepted unsafe path")
            for unsafe in (linked_file, linked_parent / "canary.json", canary):
                try:
                    module.require_exact_authority(unsafe, unsafe, "synthetic")
                except SystemExit:
                    pass
                else:
                    raise RuntimeError("controlled saturation authority reader accepted unsafe path")
            for operation in ("replace", "fsync"):
                original = getattr(module.os, operation)
                setattr(module.os, operation, lambda *args: (_ for _ in ()).throw(OSError("synthetic atomic failure")))
                try:
                    try:
                        module.atomic_write_bytes(target, b"FORBIDDEN")
                    except OSError:
                        pass
                    else:
                        raise RuntimeError("controlled saturation atomic failure unexpectedly accepted")
                finally:
                    setattr(module.os, operation, original)
                if target.read_bytes() != b"updated" or list(inside.glob(".authority.json.*.tmp")):
                    raise RuntimeError("controlled saturation atomic rollback or residue drift")
        if canary.read_bytes() != b"SYNTHETIC_CONTROLLED_SATURATION_CANARY":
            raise RuntimeError("controlled saturation atomic writer modified outside canary")
    print("PASS: controlled saturation atomic path, mode, rollback and canary negatives")


def verify_validator_output_negative(module) -> None:
    marker = "SYNTHETIC_CONTROLLED_SATURATION_SECRET_MARKER"
    original_run = module.subprocess.run
    calls = []

    def failed_validator(command, **kwargs):
        if kwargs.get("stdout") != module.subprocess.DEVNULL or kwargs.get("stderr") != module.subprocess.DEVNULL:
            raise RuntimeError("controlled saturation validator output must be suppressed")
        if kwargs.get("check") is not True:
            raise RuntimeError("controlled saturation validator must fail closed")
        calls.append(command)
        raise module.subprocess.CalledProcessError(17, command, output=marker, stderr=marker)

    try:
        module.subprocess.run = failed_validator
        for validate in (module.validate_source_authority, module.validate_post_write):
            try:
                validate("0" * 40)
            except SystemExit as exc:
                if marker in str(exc) or "exit 17" not in str(exc) or not exc.__suppress_context__:
                    raise RuntimeError("controlled saturation validator failure leaked output or lost exit code") from None
            else:
                raise RuntimeError("controlled saturation accepted failing validator")
        if len(calls) != 2:
            raise RuntimeError("controlled saturation validator test did not reach both call paths")

        def missing_validator(command, **kwargs):
            raise OSError(marker)

        module.subprocess.run = missing_validator
        for validate in (module.validate_source_authority, module.validate_post_write):
            try:
                validate("0" * 40)
            except SystemExit as exc:
                if marker in str(exc) or "OSError" not in str(exc) or not exc.__suppress_context__:
                    raise RuntimeError("controlled saturation validator execution error leaked raw exception") from None
            else:
                raise RuntimeError("controlled saturation accepted missing validator")
    finally:
        module.subprocess.run = original_run
    print("PASS: controlled saturation prewrite/postwrite validator output and exception redaction (4 cases)")


def verify_reconciler_json_parser_negatives(module) -> None:
    with tempfile.TemporaryDirectory(prefix="controlled-saturation-json-outside-") as outside_temp:
        outside = Path(outside_temp)
        canary = outside / "canary.json"
        canary.write_text('{"safe":true}', encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix=".controlled-saturation-json-", dir=ROOT) as inside_temp:
            inside = Path(inside_temp)
            path = inside / "input.json"
            path.write_text('{"outer":{"a":1,"b":2}}', encoding="utf-8")
            if module.load(path) != {"outer": {"a": 1, "b": 2}}:
                raise RuntimeError("controlled saturation JSON parser positive control failed")
            for raw in ('{"value": Infinity}', '{"value": 1e999}',
                        '{"a":1,"a":2}', '{"outer":{"a":1,"a":2}}',
                        '{"broken":', '[1,2]'):
                path.write_text(raw, encoding="utf-8")
                try:
                    module.load(path)
                except SystemExit:
                    pass
                else:
                    raise RuntimeError("controlled saturation JSON parser accepted malformed or ambiguous input")
            path.write_text('{"safe":true}', encoding="utf-8")
            original = path.read_bytes()
            try:
                module.write(path, {"unsafe": float("inf")})
            except ValueError:
                pass
            else:
                raise RuntimeError("controlled saturation JSON writer accepted nonfinite output")
            if path.read_bytes() != original:
                raise RuntimeError("controlled saturation nonfinite JSON write mutated existing file")
            linked_file = inside / "linked.json"
            linked_file.symlink_to(canary)
            linked_parent = inside / "linked-parent"
            linked_parent.symlink_to(outside, target_is_directory=True)
            for unsafe in (linked_file, linked_parent / "canary.json", canary, inside / "missing.json"):
                try:
                    module.load(unsafe)
                except SystemExit:
                    pass
                else:
                    raise RuntimeError("controlled saturation JSON parser accepted unsafe path")
        if canary.read_text(encoding="utf-8") != '{"safe":true}':
            raise RuntimeError("controlled saturation JSON parser changed external canary")
    print("PASS: controlled saturation JSON positive, malformed, duplicate, nonfinite and path negatives (11 cases)")


def verify_stronger_readiness_prewrite_negatives(module) -> None:
    paths = (module.CONTROLLED_CONTRACT, module.LOAD_CONTRACT, module.STATUS_PATH)
    before = {path: path.read_bytes() for path in paths}
    source_load = module.load
    source_validator = module.validate_source_authority
    source_write = module.write_transactionally
    previous_sha = module.os.environ.get("EXPECTED_COMMIT_SHA")
    fixture = {path: source_load(path) for path in (*paths, module.RESULT_PATH)}
    module.os.environ["EXPECTED_COMMIT_SHA"] = fixture[module.RESULT_PATH]["commitSha"]
    cases = []
    for field in ("repeatabilityEstablished", "capacityBoundaryEstablished",
                  "operationalThresholdApproved", "independentReviewCompleted", "productionReady"):
        for value in (True, None, 0, "false"):
            cases.append(("readiness", field, value))
    for field in ("productionEvidence", "capacityBoundaryEstablished",
                  "operationalThresholdApproved", "repeatabilityEstablished"):
        for value in (True, None, 0, "false"):
            cases.append(("scenario", field, value))
    cases.append(("scenario-extra", "independentReviewCompleted", True))
    writes = []
    try:
        module.validate_source_authority = lambda expected: None
        module.write_transactionally = lambda *args: writes.append(args)
        module.load = lambda path: copy.deepcopy(fixture[path])
        if module.main() != 0 or len(writes) != 1:
            raise RuntimeError("controlled saturation prewrite positive control failed")
        writes.clear()
        module.write_transactionally = lambda *args: (_ for _ in ()).throw(RuntimeError("forbidden stronger-authority write"))
        for section, field, value in cases:
            changed = copy.deepcopy(fixture)
            if section == "readiness":
                changed[module.CONTROLLED_CONTRACT]["readiness"][field] = value
            else:
                scenario = next(item for item in changed[module.LOAD_CONTRACT]["externalExecutedScenarios"]
                                if item.get("scenarioId") == module.SCENARIO_ID)
                scenario[field] = value
            module.load = lambda path, changed=changed: copy.deepcopy(changed[path])
            try:
                module.main()
            except SystemExit as exc:
                if "refusing" not in str(exc):
                    raise RuntimeError(f"controlled saturation stronger authority wrong rejection: {exc}") from None
            else:
                raise RuntimeError(f"controlled saturation accepted stronger {section}.{field}")
    finally:
        module.load = source_load
        module.validate_source_authority = source_validator
        module.write_transactionally = source_write
        if previous_sha is None:
            module.os.environ.pop("EXPECTED_COMMIT_SHA", None)
        else:
            module.os.environ["EXPECTED_COMMIT_SHA"] = previous_sha
    for path in paths:
        if path.read_bytes() != before[path]:
            raise RuntimeError("controlled saturation stronger readiness test changed canonical authority")
    print(f"PASS: controlled saturation stronger readiness/scenario prewrite negatives ({len(cases)} cases)")


def verify_nonfinite_ramp_measurements() -> None:
    validator_path = ROOT / "scripts/validate-memory-os-controlled-saturation-ramp.py"
    spec = importlib.util.spec_from_file_location("controlled_saturation_numeric_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("controlled saturation numeric validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    result = validator.load(validator.RESULT_PATH)
    batch = result["scenario"]["steps"][0]["batch"]
    if not validator.validate_batch(copy.deepcopy(batch), 4, 64, "synthetic-positive"):
        raise RuntimeError("controlled saturation numeric positive control failed")
    for label, field, bad in (
        ("infinite throughput", "throughput", float("inf")),
        ("infinite p95", "latencyP95Ms", float("inf")),
        ("nan p99", "latencyP99Ms", float("nan")),
        ("overflow duration", "durationSeconds", 10 ** 500),
    ):
        mutated = copy.deepcopy(batch)
        mutated[field] = bad
        try:
            validator.validate_batch(mutated, 4, 64, "synthetic-negative")
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"controlled saturation accepted {label}")
    for label, value in (("infinite pool duration", float("inf")),
                         ("overflow pool duration", 10 ** 500)):
        try:
            validator.number(value, "synthetic-pool-delta")
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"controlled saturation accepted {label}")
    with tempfile.TemporaryDirectory(prefix=".saturation-numeric-negative-", dir=ROOT) as temp:
        path = Path(temp) / "synthetic.json"
        for raw in ('{"value": Infinity}', '{"value": 1e999}', '{"value": 1, "value": 2}'):
            path.write_text(raw, encoding="utf-8")
            try:
                validator.load(path)
            except validator.ValidationFailure:
                pass
            else:
                raise RuntimeError("controlled saturation accepted nonfinite JSON")
    print("PASS: controlled saturation numeric parser and measurement negatives (9 cases)")



def verify_ramp_timestamp_semantics() -> None:
    """Exercise the actual ramp timestamp validator with a positive fixture and failures."""
    validator_path = ROOT / "scripts/validate-memory-os-controlled-saturation-ramp.py"
    spec = importlib.util.spec_from_file_location("controlled_saturation_timestamp_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("controlled saturation timestamp validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    canonical = validator.load(validator.RESULT_PATH)
    # A real positive control catches double-escaped raw regexes that reject every timestamp.
    validator.validate_ramp_timestamps(copy.deepcopy(canonical))
    negatives = (
        ("invalid calendar day", ("scenario", "startedAt"), "2026-02-30T23:00:44Z"),
        ("timezone offset", ("scenario", "startedAt"), "2026-09-23T23:00:44+00:00"),
        ("missing seconds", ("scenario", "startedAt"), "2026-09-23T23:00Z"),
        ("fraction without digits", ("scenario", "startedAt"), "2026-09-23T23:00:44.Z"),
        ("non-string timestamp", ("scenario", "startedAt"), None),
        ("completion before start", ("scenario", "completedAt"), "2026-09-23T23:00:43Z"),
        ("generation before completion", ("generatedAt",), "2026-09-23T23:00:46Z"),
    )
    for label, keys, value in negatives:
        mutated = copy.deepcopy(canonical)
        cursor = mutated
        for key in keys[:-1]:
            cursor = cursor[key]
        cursor[keys[-1]] = value
        try:
            validator.validate_ramp_timestamps(mutated)
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"controlled saturation accepted {label}")
    print("PASS: controlled saturation RFC3339 UTC positive and 7 timestamp negatives")



def verify_pool_snapshot_and_delta_accounting() -> None:
    """Use the canonical ramp validator on disposable full-result pool mutations."""
    validator_path = ROOT / "scripts/validate-memory-os-controlled-saturation-ramp.py"
    spec = importlib.util.spec_from_file_location("controlled_saturation_pool_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("controlled saturation pool validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    canonical = validator.load(validator.RESULT_PATH)
    cases = (
        ("negative total", ("poolBefore", "totalConns"), -1),
        ("negative acquired", ("poolBefore", "acquiredConns"), -1),
        ("negative canceled", ("poolAfter", "canceledAcquireCount"), -1),
        ("negative empty", ("poolBefore", "emptyAcquireCount"), -1),
        ("total exceeds max", ("poolBefore", "totalConns"), 100),
        ("acquired exceeds total", ("poolBefore", "acquiredConns"), 100),
        ("idle exceeds total", ("poolAfter", "idleConns"), 100),
        ("duration delta mismatch", ("poolDelta", "acquireDurationMs"), 999),
    )
    original_result_path = validator.RESULT_PATH
    with tempfile.TemporaryDirectory(prefix=".saturation-pool-negative-", dir=ROOT) as tmp:
        result_path = Path(tmp) / "synthetic-ramp.json"
        validator.RESULT_PATH = result_path
        try:
            result_path.write_text(json.dumps(canonical), encoding="utf-8")
            if validator.main() != 0:
                raise RuntimeError("controlled saturation pool positive control failed")
            for label, keys, value in cases:
                mutated = copy.deepcopy(canonical)
                mutated["scenario"]["steps"][0][keys[0]][keys[1]] = value
                result_path.write_text(json.dumps(mutated), encoding="utf-8")
                try:
                    validator.main()
                except validator.ValidationFailure:
                    pass
                else:
                    raise RuntimeError(f"controlled saturation accepted {label}")
        finally:
            validator.RESULT_PATH = original_result_path
    print("PASS: controlled saturation pool full-validator positive and 8 negatives")



def verify_batch_status_accounting() -> None:
    """Reject impossible signed-upload lifecycle counts using the actual validator."""
    validator_path = ROOT / "scripts/validate-memory-os-controlled-saturation-ramp.py"
    spec = importlib.util.spec_from_file_location("controlled_saturation_status_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("controlled saturation status validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    batch = validator.load(validator.RESULT_PATH)["scenario"]["steps"][0]["batch"]
    if not validator.validate_batch(copy.deepcopy(batch), 4, 64, "synthetic-positive"):
        raise RuntimeError("controlled saturation status positive control failed")
    cases = (
        ("negative 5xx offset", {"5xx": -1, "transport_error": 1}, 64, 0),
        ("negative transport offset", {"5xx": 1, "transport_error": -1}, 64, 0),
        ("negative successes", {"2xx": -1, "5xx": 65}, -1, 65),
        ("negative failures", {"2xx": 65, "5xx": -1}, 65, -1),
        ("unknown status class", {"6xx": 1}, 64, 0),
    )
    for label, classes, successes, failures in cases:
        mutated = copy.deepcopy(batch)
        mutated["statusClassCounts"].update(classes)
        mutated["successes"] = successes
        mutated["failures"] = failures
        try:
            validator.validate_batch(mutated, 4, 64, "synthetic-negative")
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"controlled saturation accepted {label}")
    print("PASS: controlled saturation status accounting positive and 5 negatives")



def verify_batch_metric_coherence() -> None:
    """Exercise canonical throughput and percentile checks with real validator calls."""
    validator_path = ROOT / "scripts/validate-memory-os-controlled-saturation-ramp.py"
    spec = importlib.util.spec_from_file_location("controlled_saturation_metric_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("controlled saturation metric validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    result = validator.load(validator.RESULT_PATH)
    for index, step in enumerate(result["scenario"]["steps"]):
        if not validator.validate_batch(copy.deepcopy(step["batch"]), step["concurrency"], 64,
                                        f"synthetic-positive-{index}"):
            raise RuntimeError("controlled saturation metric positive control failed")
    if not validator.validate_batch(copy.deepcopy(result["scenario"]["postRampRecoveryProbe"]),
                                    1, 1, "synthetic-recovery-positive"):
        raise RuntimeError("controlled saturation recovery metric positive control failed")
    batch = result["scenario"]["steps"][0]["batch"]
    cases = (
        ("zero duration", "durationSeconds", 0),
        ("zero throughput", "throughput", 0),
        ("invented throughput", "throughput", batch["throughput"] + 10),
        ("p50 greater than p95", "latencyP50Ms", batch["latencyP95Ms"] + 1),
        ("p95 greater than p99", "latencyP95Ms", batch["latencyP99Ms"] + 1),
        ("derived throughput overflow", "durationSeconds", 5e-324),
    )
    for label, key, value in cases:
        mutated = copy.deepcopy(batch)
        mutated[key] = value
        try:
            validator.validate_batch(mutated, 4, 64, "synthetic-negative")
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"controlled saturation accepted {label}")
    print("PASS: controlled saturation metric positives and 6 coherence negatives")


def main() -> int:
    module = load_module()
    verify_nonfinite_ramp_measurements()
    verify_ramp_timestamp_semantics()
    verify_pool_snapshot_and_delta_accounting()
    verify_batch_status_accounting()
    verify_batch_metric_coherence()
    substitutions = {
        "CONTROLLED_CONTRACT": module.LOAD_CONTRACT,
        "LOAD_CONTRACT": module.CONTROLLED_CONTRACT,
        "STATUS_PATH": module.LOAD_CONTRACT,
        "RESULT_PATH": module.CONTROLLED_CONTRACT,
        "CONTROLLED_VALIDATOR": module.LOAD_VALIDATOR,
        "LOAD_VALIDATOR": module.CONTROLLED_VALIDATOR,
        "LOAD_INDEX_VALIDATOR": module.LOAD_VALIDATOR,
        "OPERABILITY_VALIDATOR": module.LOAD_VALIDATOR,
        "WORKFLOW": module.CONTROLLED_VALIDATOR,
    }
    for attr, replacement in substitutions.items():
        expect_rejection(module, attr, replacement)
    module.enforce_runtime_authorities()
    verify_atomic_replace_failure(module)
    verify_atomic_path_negatives(module)
    verify_validator_output_negative(module)
    verify_reconciler_json_parser_negatives(module)
    verify_stronger_readiness_prewrite_negatives(module)
    print("PASS: controlled saturation direct reconcile source authorities are canonical and atomic")
    print("atomic replacement failure: rejected without authority mutation")
    print("temporary authority residue: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
