#!/usr/bin/env python3
"""Focused fail-closed checks for deletion-under-load authority reconciliation."""

from __future__ import annotations

import copy
import importlib.util
import os
import tempfile
import os
import stat
import tempfile
from pathlib import Path
from types import SimpleNamespace
from types import ModuleType
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts/reconcile-memory-os-deletion-under-load-status.py"


def load_target() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_deletion_under_load_reconcile", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load deletion-under-load reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def canonical_snapshots(module: ModuleType) -> dict[Path, bytes]:
    return {
        module.CANONICAL_CONTRACT_PATH: module.CANONICAL_CONTRACT_PATH.read_bytes(),
        module.CANONICAL_LOAD_PATH: module.CANONICAL_LOAD_PATH.read_bytes(),
        module.CANONICAL_STATUS_PATH: module.CANONICAL_STATUS_PATH.read_bytes(),
    }


def canonical_modes(module: ModuleType) -> dict[Path, int]:
    return {
        path: stat.S_IMODE(path.stat().st_mode)
        for path in (
            module.CANONICAL_CONTRACT_PATH,
            module.CANONICAL_LOAD_PATH,
            module.CANONICAL_STATUS_PATH,
        )
    }


def require_snapshots_unchanged(snapshots: dict[Path, bytes]) -> None:
    for path, payload in snapshots.items():
        require(path.read_bytes() == payload, f"canonical authority mutated after rejection: {path.relative_to(ROOT)}")


def require_modes_unchanged(modes: dict[Path, int]) -> None:
    for path, mode in modes.items():
        require(
            stat.S_IMODE(path.stat().st_mode) == mode,
            f"canonical authority mode changed after rejection: {path.relative_to(ROOT)}",
        )


def expect_rejection(
    module: ModuleType,
    label: str,
    mutate: Callable[[], Callable[[], None]],
    check: Callable[[], None] | None = None,
) -> None:
    snapshots = canonical_snapshots(module)
    modes = canonical_modes(module)
    restore = mutate()
    try:
        try:
            (check or module.enforce_runtime_authorities)()
        except module.ReconcileFailure:
            pass
        else:
            raise RuntimeError(f"authority substitution was accepted: {label}")
    finally:
        restore()
    require_snapshots_unchanged(snapshots)
    require_modes_unchanged(modes)


def swap_attr(target: object, name: str, value: object) -> Callable[[], None]:
    original = getattr(target, name)
    setattr(target, name, value)
    return lambda: setattr(target, name, original)


def swap_many(*changes: tuple[object, str, object]) -> Callable[[], None]:
    originals = [(target, name, getattr(target, name)) for target, name, _ in changes]
    for target, name, value in changes:
        setattr(target, name, value)

    def restore() -> None:
        for target, name, value in reversed(originals):
            setattr(target, name, value)

    return restore


def exercise_rollback_failure(module: ModuleType) -> None:
    snapshots = canonical_snapshots(module)
    modes = canonical_modes(module)
    real_writer = module.CANONICAL_ATOMIC_WRITE_BYTES
    real_run_validator = module.run_validator
    real_enforce_writer = module.enforce_atomic_writer_authority
    writer_calls: list[Path] = []

    def synthetic_primary_failure(*args: object, **kwargs: object) -> None:
        raise module.ReconcileFailure("SYNTHETIC_PRIMARY_SECRET_DO_NOT_LOG")

    def writer_with_first_rollback_failure(path: Path, payload: bytes) -> None:
        writer_calls.append(path)
        real_writer(path, payload)
        if len(writer_calls) == 4:
            raise RuntimeError("synthetic rollback writer failure")

    contract = module.load(module.CANONICAL_CONTRACT_PATH)
    load_contract = module.load(module.CANONICAL_LOAD_PATH)
    status = module.load(module.CANONICAL_STATUS_PATH)
    contract["__negativeRollbackTest"] = True
    load_contract["__negativeRollbackTest"] = True
    status["__negativeRollbackTest"] = True

    module.CANONICAL_ATOMIC_WRITE_BYTES = writer_with_first_rollback_failure
    module.atomic_write_bytes = writer_with_first_rollback_failure
    module.enforce_atomic_writer_authority = lambda: None
    module.run_validator = synthetic_primary_failure
    try:
        try:
            module.write_and_validate_transactionally(contract, load_contract, status)
        except module.ReconcileFailure as exc:
            diagnostic = str(exc)
            require("ReconcileFailure" in diagnostic,
                    "rollback failure lost primary exception class")
            require("SYNTHETIC_PRIMARY_SECRET_DO_NOT_LOG" not in diagnostic,
                    "rollback failure exposed primary secret")
            require("rollback incomplete" in diagnostic,
                    "rollback failure did not report incomplete rollback")
            require("RuntimeError" in diagnostic,
                    "rollback failure exception class missing")
            require("synthetic rollback writer failure" not in diagnostic,
                    "rollback failure exposed raw exception text")
        else:
            raise RuntimeError("synthetic rollback failure was accepted")
    finally:
        module.run_validator = real_run_validator
        module.enforce_atomic_writer_authority = real_enforce_writer
        module.atomic_write_bytes = real_writer
        module.CANONICAL_ATOMIC_WRITE_BYTES = real_writer

    require(len(writer_calls) == 6, "rollback did not continue across all three canonical authorities")
    require(
        writer_calls[3:] == [
            module.CANONICAL_CONTRACT_PATH,
            module.CANONICAL_LOAD_PATH,
            module.CANONICAL_STATUS_PATH,
        ],
        "rollback authority order or exhaustiveness drifted",
    )
    require_snapshots_unchanged(snapshots)
    require_modes_unchanged(modes)



def exercise_atomic_path_substitution_rejection(module: ModuleType) -> None:
    # Direct helper invocation must not depend on a separate main-path identity guard.
    with tempfile.TemporaryDirectory(prefix="memory-os-deletion-load-atomic-path-") as tmp:
        root = Path(tmp)
        external = root / "external"
        external.mkdir()
        canary = external / "canary.json"
        canary.write_bytes(b"external-canary\\n")
        direct = root / "direct.json"
        direct.symlink_to(canary)
        ancestor = root / "ancestor"
        ancestor.symlink_to(external, target_is_directory=True)
        directory = root / "directory.json"
        directory.mkdir()
        missing = root / "missing-parent" / "authority.json"
        for label, target in (
            ("direct symlink", direct),
            ("symlink ancestor", ancestor / "canary.json"),
            ("directory target", directory),
            ("missing parent", missing),
        ):
            try:
                module.atomic_write_bytes(target, b"unsafe\\n")
            except module.ReconcileFailure as exc:
                require("atomic target" in str(exc), f"{label}: unexpected rejection")
            else:
                raise RuntimeError(f"{label}: atomic writer accepted substituted authority")
            require(canary.read_bytes() == b"external-canary\\n",
                    f"{label}: external canary changed")
            require(not missing.parent.exists(), f"{label}: unreviewed parent created")
            require(not list(root.rglob("*.tmp")), f"{label}: temporary residue")
        regular = root / "regular.json"
        regular.write_bytes(b"before\\n")
        os.chmod(regular, 0o640)
        module.atomic_write_bytes(regular, b"after\\n")
        require(regular.read_bytes() == b"after\\n", "regular target write failed")
        require(stat.S_IMODE(regular.stat().st_mode) == 0o640,
                "regular target mode was not preserved")
        require(canary.read_bytes() == b"external-canary\\n",
                "regular target write changed external canary")
        require(not list(root.rglob("*.tmp")), "positive write left temporary residue")



def exercise_validator_output_redaction(module: ModuleType) -> None:
    original_run = module.CANONICAL_SUBPROCESS_RUN
    original_guard = module.enforce_runtime_authorities

    def synthetic_run(*args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=17, stdout="SYNTHETIC_VALIDATOR_SECRET_DO_NOT_LOG")

    module.CANONICAL_SUBPROCESS_RUN = synthetic_run
    module.enforce_runtime_authorities = lambda: None
    try:
        try:
            module.run_validator(module.DELETION_VALIDATOR, "synthetic")
        except module.ReconcileFailure as exc:
            require("exit code 17" in str(exc), "validator exit code was lost")
            require("SYNTHETIC_VALIDATOR_SECRET_DO_NOT_LOG" not in str(exc),
                    "raw validator stdout escaped into diagnostic")
        else:
            raise RuntimeError("failing synthetic validator was accepted")
    finally:
        module.CANONICAL_SUBPROCESS_RUN = original_run
        module.enforce_runtime_authorities = original_guard



def exercise_stronger_readiness_prewrite_rejection(module: ModuleType) -> None:
    original_load = module.load
    original_run_validator = module.run_validator
    original_transaction = module.write_and_validate_transactionally
    previous_expected = os.environ.get("EXPECTED_COMMIT_SHA")
    snapshots = canonical_snapshots(module)
    os.environ["EXPECTED_COMMIT_SHA"] = "1" * 40
    try:
        for field in (
            "preFenceInFlightLinearizationProven",
            "productionDependenciesTested",
            "independentReviewCompleted",
            "productionReady",
        ):
            for injected in (True, None, 0):
                def synthetic_load(path: Path):
                    document = original_load(path)
                    if path == module.CONTRACT_PATH:
                        document["readiness"][field] = injected
                    return document

                def forbidden_transaction(*args: object, **kwargs: object) -> None:
                    raise RuntimeError("prewrite readiness rejection was bypassed")

                module.load = synthetic_load
                module.run_validator = lambda *args, **kwargs: None
                module.write_and_validate_transactionally = forbidden_transaction
                try:
                    module.main()
                except module.ReconcileFailure as exc:
                    require(f"cannot downgrade stronger readiness: {field}" in str(exc),
                            f"{field}={injected!r}: wrong rejection")
                else:
                    raise RuntimeError(f"{field}={injected!r}: stronger readiness accepted")
                require_snapshots_unchanged(snapshots)
    finally:
        module.load = original_load
        module.run_validator = original_run_validator
        module.write_and_validate_transactionally = original_transaction
        if previous_expected is None:
            os.environ.pop("EXPECTED_COMMIT_SHA", None)
        else:
            os.environ["EXPECTED_COMMIT_SHA"] = previous_expected
    require_snapshots_unchanged(snapshots)



def exercise_existing_scenario_prewrite_rejection(module: ModuleType) -> None:
    original_load = module.load
    original_run_validator = module.run_validator
    original_transaction = module.write_and_validate_transactionally
    previous_expected = os.environ.get("EXPECTED_COMMIT_SHA")
    snapshots = canonical_snapshots(module)
    os.environ["EXPECTED_COMMIT_SHA"] = "1" * 40
    try:
        for field, injected in (
            ("productionEvidence", True),
            ("requestsStartedBeforeFenceCovered", True),
            ("dependencyMode", "PRODUCTION_EQUIVALENT"),
            ("contractRef", "contracts/operations/production-operability-status.json"),
        ):
            def synthetic_load(path: Path):
                document = original_load(path)
                if path == module.LOAD_PATH:
                    items = document["externalExecutedScenarios"]
                    matches = [item for item in items
                               if isinstance(item, dict) and item.get("scenarioId") ==
                               "account-deletion-post-fence-load-local-dependencies"]
                    require(len(matches) == 1, "canonical local scenario fixture drift")
                    matches[0][field] = injected
                return document

            def forbidden_transaction(*args: object, **kwargs: object) -> None:
                raise RuntimeError("local scenario prewrite rejection was bypassed")

            module.load = synthetic_load
            module.run_validator = lambda *args, **kwargs: None
            module.write_and_validate_transactionally = forbidden_transaction
            try:
                module.main()
            except module.ReconcileFailure as exc:
                require("local scenario authority drift; refusing overwrite" in str(exc),
                        f"{field}: unexpected rejection")
            else:
                raise RuntimeError(f"{field}: stronger scenario was silently overwritten")
            require_snapshots_unchanged(snapshots)
    finally:
        module.load = original_load
        module.run_validator = original_run_validator
        module.write_and_validate_transactionally = original_transaction
        if previous_expected is None:
            os.environ.pop("EXPECTED_COMMIT_SHA", None)
        else:
            os.environ["EXPECTED_COMMIT_SHA"] = previous_expected
    require_snapshots_unchanged(snapshots)


def exercise_deletion_load_json_reader() -> None:
    validator_path = ROOT / "scripts/validate-memory-os-deletion-under-load.py"
    spec = importlib.util.spec_from_file_location("deletion_load_json_negative", validator_path)
    require(spec is not None and spec.loader is not None, "deletion load JSON validator loader missing")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    with tempfile.TemporaryDirectory(prefix="deletion-load-json-outside-") as outside_tmp, \
         tempfile.TemporaryDirectory(prefix=".deletion-load-json-negative-", dir=ROOT) as inside_tmp:
        outside, inside = Path(outside_tmp), Path(inside_tmp)
        canary = outside / "canary.json"
        canary.write_bytes(b'{"synthetic":true}')
        good = inside / "good.json"
        good.write_text('{"safe":true}', encoding="utf-8")
        require(validator.load(good) == {"safe": True}, "deletion load JSON positive failed")
        boundary = inside / "boundary.json"
        boundary.write_bytes(b'{"padding":"' + b"x" * (validator.MAX_JSON_BYTES - 14) + b'"}')
        require(len(boundary.read_bytes()) <= validator.MAX_JSON_BYTES and validator.load(boundary)["padding"],
                "deletion load bounded JSON positive failed")
        oversized = inside / "oversized.json"
        oversized.write_bytes(b'{"padding":"' + b"x" * validator.MAX_JSON_BYTES + b'"}')
        bad = (
            ("oversized", oversized, "exceeds reviewed read limit"),
            ("outside", canary, "escaped repository"),
        )
        nested = inside / "duplicate.json"
        nested.write_text('{"outer":{"key":1,"key":2}}', encoding="utf-8")
        bad += (("duplicate", nested, "duplicate deletion load JSON key"),)
        invalid = inside / "invalid.json"
        invalid.write_bytes(b'{"value":"' + bytes([255]) + b'"}')
        bad += (("invalid UTF-8", invalid, "unreadable or invalid"),)
        huge = inside / "huge.json"
        huge.write_text('{"value":' + "9" * 5000 + "}", encoding="utf-8")
        bad += (("huge integer", huge, "unreadable or invalid"),)
        linked = inside / "linked.json"
        linked.symlink_to(canary)
        parent_link = inside / "linked-parent"
        parent_link.symlink_to(outside, target_is_directory=True)
        directory = inside / "directory.json"
        directory.mkdir()
        bad += (
            ("direct symlink", linked, "symlink rejected"),
            ("ancestor symlink", parent_link / "canary.json", "symlink rejected"),
            ("directory", directory, "missing or unsafe"),
            ("missing", inside / "missing.json", "missing or unsafe"),
        )
        for label, path, expected in bad:
            try:
                validator.load(path)
            except validator.ValidationFailure as exc:
                require(expected in str(exc) and "SYNTHETIC_SECRET" not in str(exc),
                        "deletion load JSON wrong rejection: " + label)
            else:
                raise RuntimeError("deletion load JSON accepted " + label)
        require(canary.read_bytes() == b'{"synthetic":true}', "deletion load JSON changed outside canary")
    print("PASS: deletion-under-load bounded strict JSON and path negatives")



def exercise_deletion_load_reviewed_schema() -> None:
    validator_path = ROOT / "scripts/validate-memory-os-deletion-under-load.py"
    spec = importlib.util.spec_from_file_location("deletion_load_reviewed_schema", validator_path)
    require(spec is not None and spec.loader is not None, "reviewed schema import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    contract = validator.load(ROOT / "contracts/operations/deletion-under-load-contract.v1.json")
    result = validator.load(ROOT / validator.REVIEWED_RESULT_PATH)
    validator.validate_reviewed_contract(copy.deepcopy(contract))
    validator.validate_result_shape(copy.deepcopy(result))
    contract_cases = (
        ("result redirect", lambda d: d.__setitem__("resultPath", "contracts/operations/production-operability-status.json")),
        ("result traversal", lambda d: d.__setitem__("resultPath", "../outside.json")),
        ("runner redirect", lambda d: d.__setitem__("runner", "scripts/validate-memory-os-load.py")),
        ("missing validator", lambda d: d.pop("validator")),
        ("contract identity", lambda d: d.__setitem__("contractId", "unreviewed")),
        ("criteria overclaim", lambda d: d["successCriteria"].__setitem__("productionEvidence", True)),
        ("criteria boolean alias", lambda d: d["successCriteria"].__setitem__("productionEvidence", 0)),
        ("criteria float alias", lambda d: d["successCriteria"].__setitem__("deletionEpoch", 2.0)),
        ("criteria missing", lambda d: d["successCriteria"].pop("workerCompleted")),
        ("criteria extra", lambda d: d["successCriteria"].__setitem__("productionReady", True)),
    )
    result_cases = (
        ("root readiness injection", lambda d: d.__setitem__("productionReady", True)),
        ("missing root field", lambda d: d.pop("limitations")),
        ("environment readiness injection", lambda d: d["environment"].__setitem__("productionReady", True)),
        ("environment missing boundary", lambda d: d["environment"].pop("productionCredentials")),
        ("environment cpu boolean", lambda d: d["environment"].__setitem__("numCpu", True)),
        ("scenario readiness injection", lambda d: d["scenario"].__setitem__("productionReady", True)),
        ("scenario missing field", lambda d: d["scenario"].pop("workerReceiptCount")),
        ("pre summary injection", lambda d: d["scenario"]["preFence"]["summary"].__setitem__("productionEvidence", True)),
        ("post batch injection", lambda d: d["scenario"]["postFence"].__setitem__("productionReady", True)),
        ("assertion extra", lambda d: d["scenario"]["assertions"].__setitem__("productionReady", True)),
        ("assertion missing", lambda d: d["scenario"]["assertions"].pop("workerCompleted")),
        ("assertion boolean alias", lambda d: d["scenario"]["assertions"].__setitem__("finalOwnedRowCount", False)),
        ("assertion float alias", lambda d: d["scenario"]["assertions"].__setitem__("deletionEpoch", 2.0)),
        ("assertion overclaim", lambda d: d["scenario"]["assertions"].__setitem__("productionEvidence", True)),
        ("limitations object", lambda d: d.__setitem__("limitations", {"productionReady": True})),
        ("scenario status float alias", lambda d: d["scenario"].__setitem__("deletionRequestStatus", 202.0)),
        ("scenario epoch float alias", lambda d: d["scenario"].__setitem__("deletionEpoch", 2.0)),
        ("scenario receipt boolean alias", lambda d: d["scenario"].__setitem__("workerReceiptCount", True)),
        ("scenario row boolean alias", lambda d: d["scenario"].__setitem__("finalOwnedRowCount", False)),
        ("scenario final epoch float alias", lambda d: d["scenario"].__setitem__("finalAccountEpoch", 2.0)),
        ("pre concurrency drift", lambda d: d["scenario"]["preFence"]["summary"].__setitem__("concurrency", 32)),
        ("post concurrency float alias", lambda d: d["scenario"]["postFence"]["summary"].__setitem__("concurrency", 32.0)),
    )
    for label, mutate in contract_cases:
        altered = copy.deepcopy(contract)
        mutate(altered)
        try:
            validator.validate_reviewed_contract(altered)
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"deletion load contract accepted {label}")
    for label, mutate in result_cases:
        altered = copy.deepcopy(result)
        mutate(altered)
        try:
            validator.validate_result_shape(altered)
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"deletion load result accepted {label}")
    print("PASS: deletion-under-load reviewed schema positive and 32 negative cases")



def exercise_transaction_primary_failure_redaction(module: ModuleType) -> None:
    snapshots = canonical_snapshots(module)
    modes = canonical_modes(module)
    original_run = module.run_validator

    def synthetic_secret_failure(*args: object, **kwargs: object) -> None:
        raise RuntimeError("SYNTHETIC_TRANSACTION_SECRET_DO_NOT_LOG")

    contract = module.load(module.CANONICAL_CONTRACT_PATH)
    load_contract = module.load(module.CANONICAL_LOAD_PATH)
    status = module.load(module.CANONICAL_STATUS_PATH)
    module.run_validator = synthetic_secret_failure
    try:
        try:
            module.write_and_validate_transactionally(contract, load_contract, status)
        except module.ReconcileFailure as exc:
            diagnostic = str(exc)
            require("transaction failed (RuntimeError)" in diagnostic,
                    "transaction failure lost primary exception class")
            require("SYNTHETIC_TRANSACTION_SECRET_DO_NOT_LOG" not in diagnostic,
                    "transaction failure exposed raw primary exception")
            require("rollback incomplete" not in diagnostic,
                    "complete rollback was incorrectly marked incomplete")
        else:
            raise RuntimeError("synthetic transaction failure was accepted")
    finally:
        module.run_validator = original_run
    require_snapshots_unchanged(snapshots)
    require_modes_unchanged(modes)



def exercise_reconciler_json_reader(module: ModuleType) -> None:
    require(isinstance(module.load(module.CANONICAL_CONTRACT_PATH), dict),
            "canonical deletion load contract reader positive failed")
    require(isinstance(module.load(module.CANONICAL_STATUS_PATH), dict),
            "canonical deletion load status reader positive failed")
    with (
        tempfile.TemporaryDirectory(prefix="deletion-reconcile-outside-") as outside_tmp,
        tempfile.TemporaryDirectory(prefix=".deletion-reconcile-json-negative-", dir=ROOT) as inside_tmp,
    ):
        outside, inside = Path(outside_tmp), Path(inside_tmp)
        canary = outside / "canary.json"
        canary.write_bytes(b'{"external":true}')
        good = inside / "good.json"
        good.write_text('{"safe":true}', encoding="utf-8")
        require(module.load(good) == {"safe": True}, "reconciler JSON positive failed")
        boundary = inside / "boundary.json"
        boundary.write_bytes(b'{"padding":"' + b"x" * (module.MAX_JSON_BYTES - 14) + b'"}')
        require(module.load(boundary)["padding"], "reconciler bounded JSON positive failed")
        cases: list[tuple[str, Path, str]] = []
        oversized = inside / "oversized.json"
        oversized.write_bytes(b'{"padding":"' + b"x" * module.MAX_JSON_BYTES + b'"}')
        cases.append(("oversized", oversized, "exceeds reviewed read limit"))
        cases.append(("outside", canary, "escaped repository"))
        duplicate = inside / "duplicate.json"
        duplicate.write_text('{"outer":{"key":1,"key":2}}', encoding="utf-8")
        cases.append(("nested duplicate", duplicate, "duplicate"))
        for label, raw, expected in (
            ("NaN", b'{"value":NaN}', "non-finite"),
            ("float overflow", b'{"value":1e999}', "non-finite"),
            ("invalid UTF-8", b'{"value":"' + bytes([255]) + b'"}', "unreadable or invalid"),
            ("malformed secret", b'{"SYNTHETIC_SECRET_DO_NOT_LOG":', "unreadable or invalid"),
            ("huge integer", b'{"value":' + b"9" * 5000 + b"}", "unreadable or invalid"),
        ):
            path = inside / (label.replace(" ", "-") + ".json")
            path.write_bytes(raw)
            cases.append((label, path, expected))
        linked = inside / "linked.json"
        linked.symlink_to(canary)
        cases.append(("direct symlink", linked, "symlink rejected"))
        parent_link = inside / "linked-parent"
        parent_link.symlink_to(outside, target_is_directory=True)
        cases.append(("ancestor symlink", parent_link / "canary.json", "symlink rejected"))
        directory = inside / "directory.json"
        directory.mkdir()
        cases.append(("directory", directory, "missing or unsafe"))
        cases.append(("missing", inside / "missing.json", "missing or unsafe"))
        for label, path, expected in cases:
            try:
                module.load(path)
            except module.ReconcileFailure as exc:
                require(expected in str(exc) and "SYNTHETIC_SECRET_DO_NOT_LOG" not in str(exc),
                        f"reconciler JSON wrong rejection: {label}")
            else:
                raise RuntimeError(f"reconciler JSON accepted {label}")
        try:
            module.load("not-a-path")
        except module.ReconcileFailure:
            pass
        else:
            raise RuntimeError("reconciler JSON accepted non-Path input")
        require(canary.read_bytes() == b'{"external":true}',
                "reconciler JSON changed outside canary")
    print("PASS: deletion-under-load reconciler bounded strict JSON and path negatives")


def main() -> int:
    exercise_deletion_load_json_reader()
    exercise_deletion_load_reviewed_schema()
    module = load_target()
    exercise_reconciler_json_reader(module)
    module.enforce_runtime_authorities()
    module.enforce_atomic_writer_authority()

    expect_rejection(module, "repository root", lambda: swap_attr(module, "ROOT", module.CANONICAL_ROOT / "scripts"))
    expect_rejection(module, "deletion contract", lambda: swap_attr(module, "CONTRACT_PATH", module.CANONICAL_LOAD_PATH))
    expect_rejection(module, "production status", lambda: swap_attr(module, "STATUS_PATH", module.CANONICAL_LOAD_PATH))
    expect_rejection(module, "deletion validator", lambda: swap_attr(module, "DELETION_VALIDATOR", module.CANONICAL_LOAD_VALIDATOR))

    fake_run = lambda *args, **kwargs: None
    expect_rejection(module, "subprocess transport", lambda: swap_attr(module.subprocess, "run", fake_run))
    expect_rejection(
        module,
        "paired subprocess transport",
        lambda: swap_many(
            (module, "CANONICAL_SUBPROCESS_RUN", fake_run),
            (module.subprocess, "run", fake_run),
        ),
    )

    fake_replace = lambda *args, **kwargs: None
    expect_rejection(module, "atomic replacement transport", lambda: swap_attr(module.os, "replace", fake_replace))
    expect_rejection(
        module,
        "paired atomic replacement transport",
        lambda: swap_many(
            (module, "CANONICAL_OS_REPLACE", fake_replace),
            (module.os, "replace", fake_replace),
        ),
    )

    fake_writer = lambda *args, **kwargs: None
    expect_rejection(
        module,
        "atomic writer",
        lambda: swap_attr(module, "atomic_write_bytes", fake_writer),
        module.enforce_atomic_writer_authority,
    )
    expect_rejection(
        module,
        "paired atomic writer",
        lambda: swap_many(
            (module, "CANONICAL_ATOMIC_WRITE_BYTES", fake_writer),
            (module, "atomic_write_bytes", fake_writer),
        ),
        module.enforce_atomic_writer_authority,
    )

    alternate_root = module.CANONICAL_ROOT / "scripts"
    expect_rejection(
        module,
        "paired repository root",
        lambda: swap_many(
            (module, "CANONICAL_ROOT", alternate_root),
            (module, "ROOT", alternate_root),
        ),
    )
    expect_rejection(
        module,
        "paired contract authority",
        lambda: swap_many(
            (module, "CANONICAL_CONTRACT_PATH", module.CANONICAL_LOAD_PATH),
            (module, "CONTRACT_PATH", module.CANONICAL_LOAD_PATH),
        ),
    )

    with tempfile.TemporaryDirectory(prefix="memory-os-deletion-load-negative-") as tmp:
        path = Path(tmp) / "authority.json"
        path.write_bytes(b"before\n")
        os.chmod(path, 0o640)
        module.atomic_write_bytes(path, b"after\n")
        require(path.read_bytes() == b"after\n", "atomic writer payload mismatch")
        require(stat.S_IMODE(path.stat().st_mode) == 0o640, "atomic writer changed existing file mode")
        require(not list(path.parent.glob(f".{path.name}.*.tmp")), "atomic writer left temporary residue")

    exercise_existing_scenario_prewrite_rejection(module)
    exercise_stronger_readiness_prewrite_rejection(module)
    exercise_validator_output_redaction(module)
    exercise_atomic_path_substitution_rejection(module)
    exercise_rollback_failure(module)
    exercise_transaction_primary_failure_redaction(module)
    require_snapshots_unchanged(canonical_snapshots(module))
    require_modes_unchanged(canonical_modes(module))
    print("Deletion-under-load reconcile negative checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
