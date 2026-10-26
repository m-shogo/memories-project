#!/usr/bin/env python3
"""Read-only actual-validator negatives for local Linux SIGKILL recovery evidence."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-deletion-worker-sigkill-recovery.py"


def main() -> int:
    spec = importlib.util.spec_from_file_location("sigkill_strict_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("SIGKILL validator loader missing")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    contract = validator.load(validator.CONTRACT_PATH)
    validator.validate_contract(contract)
    validator.validate_result(contract, None)
    canonical = validator.load(validator.RESULT_PATH)
    if not validator.read_runner(validator.RUNNER_PATH):
        raise RuntimeError("SIGKILL canonical runner positive failed")

    with tempfile.TemporaryDirectory(prefix="sigkill-reader-outside-") as outside_temp, \
         tempfile.TemporaryDirectory(prefix=".sigkill-reader-", dir=ROOT) as inside_temp:
        outside = Path(outside_temp)
        inside = Path(inside_temp)
        canary = outside / "canary.json"
        canary.write_bytes(b'{"synthetic":true}')
        good = inside / "good.json"
        good.write_text('{"safe":true}', encoding="utf-8")
        if validator.load(good) != {"safe": True}:
            raise RuntimeError("SIGKILL JSON positive control failed")

        boundary = inside / "boundary.json"
        boundary.write_bytes(b'{"padding":"' + b"x" * (validator.MAX_JSON_BYTES - 14) + b'"}')
        if len(boundary.read_bytes()) > validator.MAX_JSON_BYTES or not validator.load(boundary)["padding"]:
            raise RuntimeError("SIGKILL bounded JSON positive failed")
        oversized = inside / "oversized.json"
        oversized.write_bytes(b'{"padding":"' + b"x" * validator.MAX_JSON_BYTES + b'"}')
        try:
            validator.load(oversized)
        except validator.Fail as exc:
            if "exceeds reviewed read limit" not in str(exc):
                raise RuntimeError("SIGKILL oversized JSON wrong rejection") from None
        else:
            raise RuntimeError("SIGKILL accepted oversized JSON")

        for label, raw in (
            ("nested duplicate", '{"outer":{"key":1,"key":2}}'),
            ("NaN", '{"value":NaN}'),
            ("infinite exponent", '{"value":1e999}'),
            ("huge integer", '{"value":' + "9" * 5000 + '}'),
            ("nonobject root", '["safe"]'),
            ("synthetic secret malformed", '{"SYNTHETIC_SIGKILL_SECRET":'),
        ):
            path = inside / (label.replace(" ", "-") + ".json")
            path.write_text(raw, encoding="utf-8")
            try:
                validator.load(path)
            except validator.Fail as exc:
                if "SYNTHETIC_SIGKILL_SECRET" in str(exc):
                    raise RuntimeError("SIGKILL JSON error reflected untrusted material") from None
            else:
                raise RuntimeError(f"SIGKILL JSON accepted {label}")

        invalid_utf8 = inside / "invalid-utf8.json"
        invalid_utf8.write_bytes(b'{"value":"' + bytes([255]) + b'"}')
        try:
            validator.load(invalid_utf8)
        except validator.Fail:
            pass
        else:
            raise RuntimeError("SIGKILL JSON accepted invalid UTF-8")

        linked = inside / "linked.json"
        linked.symlink_to(canary)
        linked_parent = inside / "linked-parent"
        linked_parent.symlink_to(outside, target_is_directory=True)
        directory = inside / "directory.json"
        directory.mkdir()
        for label, unsafe in (
            ("outside", canary),
            ("symlink", linked),
            ("ancestor symlink", linked_parent / "canary.json"),
            ("directory", directory),
            ("missing", inside / "missing.json"),
        ):
            try:
                validator.load(unsafe)
            except validator.Fail:
                pass
            else:
                raise RuntimeError(f"SIGKILL JSON accepted {label}")

        runner_good = inside / "good.go"
        runner_good.write_text("package main\n", encoding="utf-8")
        if validator.read_runner(runner_good) != "package main\n":
            raise RuntimeError("SIGKILL runner positive failed")
        runner_oversized = inside / "oversized.go"
        runner_oversized.write_bytes(b"x" * (validator.MAX_RUNNER_BYTES + 1))
        runner_invalid = inside / "invalid.go"
        runner_invalid.write_bytes(b"package main\n" + bytes([255]))
        runner_directory = inside / "directory.go"
        runner_directory.mkdir()
        runner_link = inside / "linked.go"
        runner_link.symlink_to(canary)
        runner_parent = inside / "linked-runner-parent"
        runner_parent.symlink_to(outside, target_is_directory=True)
        runner_cases = (
            ("oversized", runner_oversized, "exceeds reviewed read limit"),
            ("invalid UTF-8", runner_invalid, "unreadable or invalid"),
            ("external", canary, "escaped repository"),
            ("symlink", runner_link, "symlink rejected"),
            ("symlink ancestor", runner_parent / "canary.json", "symlink rejected"),
            ("directory", runner_directory, "missing or unsafe"),
            ("missing", inside / "missing.go", "missing or unsafe"),
        )
        for label, unsafe, expected_message in runner_cases:
            try:
                validator.read_runner(unsafe)
            except validator.Fail as exc:
                if expected_message not in str(exc) or "SYNTHETIC_SECRET" in str(exc):
                    raise RuntimeError("SIGKILL runner " + label + " wrong rejection") from None
            else:
                raise RuntimeError("SIGKILL runner accepted " + label)
        old_runner = validator.RUNNER_PATH
        validator.RUNNER_PATH = runner_oversized
        try:
            try:
                validator.validate_contract(contract)
            except validator.Fail as exc:
                if "exceeds reviewed read limit" not in str(exc):
                    raise RuntimeError("SIGKILL contract wrong runner gate") from None
            else:
                raise RuntimeError("SIGKILL contract accepted oversized runner")
        finally:
            validator.RUNNER_PATH = old_runner

        original_result = validator.RESULT_PATH
        synthetic = inside / "synthetic-result.json"
        validator.RESULT_PATH = synthetic
        try:
            for label, marker in (
                ("postgres", "PoStGrEs://synthetic.invalid"),
                ("minio", "MiNiOaDmIn"),
                ("bearer", "bEaReR SYNTHETIC_NON_CREDENTIAL"),
                ("presigned", "x-AmZ-CrEdEnTiAl=SYNTHETIC"),
                ("credential", "MEMORY_OS_SIGKILL_HELPER_DATABASE_URL=SYNTHETIC"),
                ("account", "AcCt_SYNTHETIC"),
            ):
                mutated = copy.deepcopy(canonical)
                mutated["environment"]["syntheticNegativeMarker"] = marker
                synthetic.write_text(json.dumps(mutated), encoding="utf-8")
                try:
                    validator.validate_result(contract, None)
                except validator.Fail as exc:
                    if "forbidden runtime material" not in str(exc) or marker in str(exc):
                        raise RuntimeError(f"SIGKILL marker {label} wrong rejection") from None
                else:
                    raise RuntimeError(f"SIGKILL accepted mixed-case {label}")

            dangling = inside / "dangling-result.json"
            dangling.symlink_to(outside / "absent.json")
            validator.RESULT_PATH = dangling
            old_argv = sys.argv
            sys.argv = [old_argv[0]]
            try:
                try:
                    validator.main()
                except validator.Fail as exc:
                    if "result symlink rejected" not in str(exc):
                        raise RuntimeError("SIGKILL optional symlink wrong rejection") from None
                else:
                    raise RuntimeError("SIGKILL optional dangling result symlink accepted")
            finally:
                sys.argv = old_argv
        finally:
            validator.RESULT_PATH = original_result

        if canary.read_bytes() != b'{"synthetic":true}':
            raise RuntimeError("SIGKILL reader mutated external canary")
    print("PASS: SIGKILL strict JSON/path, optional-result symlink and mixed-case marker negatives")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
