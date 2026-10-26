#!/usr/bin/env python3
"""Focused fail-closed checks for deletion-under-load authority reconciliation."""

from __future__ import annotations

import contextlib
import hashlib
import copy
import importlib.util
import io
import json
import sys
import subprocess
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
    calls: list[object] = []

    def synthetic_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append(command)
        require(command == [module.sys.executable, str(module.DELETION_VALIDATOR), "--require-reconciled"],
                "validator subprocess command drift")
        require(kwargs.get("cwd") == module.CANONICAL_ROOT and
                kwargs.get("stdout") == module.subprocess.DEVNULL and
                kwargs.get("stderr") == module.subprocess.DEVNULL and
                kwargs.get("timeout") == 60 and kwargs.get("check") is False,
                "validator subprocess output/timeout boundary drift")
        return SimpleNamespace(returncode=17, stdout="SYNTHETIC_VALIDATOR_SECRET_DO_NOT_LOG")

    module.CANONICAL_SUBPROCESS_RUN = synthetic_run
    module.enforce_runtime_authorities = lambda: None
    try:
        try:
            module.run_validator(module.DELETION_VALIDATOR, "deletion-under-load", "--require-reconciled")
        except module.ReconcileFailure as exc:
            require("exit code 17" in str(exc), "validator exit code was lost")
            require("SYNTHETIC_VALIDATOR_SECRET_DO_NOT_LOG" not in str(exc),
                    "raw validator stdout escaped into diagnostic")
        else:
            raise RuntimeError("failing synthetic validator was accepted")
        require(len(calls) == 1, "validator subprocess was not invoked")
        module.CANONICAL_SUBPROCESS_RUN = lambda *args, **kwargs: SimpleNamespace(
            returncode="SYNTHETIC_EXIT_CODE_SECRET_DO_NOT_LOG")
        try:
            module.run_validator(module.DELETION_VALIDATOR, "deletion-under-load", "--require-reconciled")
        except module.ReconcileFailure as exc:
            require("invalid exit code" in str(exc) and
                    "SYNTHETIC_EXIT_CODE_SECRET_DO_NOT_LOG" not in str(exc),
                    "invalid validator exit code leaked raw text")
        else:
            raise RuntimeError("noninteger validator exit code accepted")

        def synthetic_timeout(*args: object, **kwargs: object) -> None:
            raise module.subprocess.TimeoutExpired("SYNTHETIC_TIMEOUT_SECRET_DO_NOT_LOG", 60)

        module.CANONICAL_SUBPROCESS_RUN = synthetic_timeout
        try:
            module.run_validator(module.DELETION_VALIDATOR, "deletion-under-load", "--require-reconciled")
        except module.ReconcileFailure as exc:
            require("TimeoutExpired" in str(exc) and
                    "SYNTHETIC_TIMEOUT_SECRET_DO_NOT_LOG" not in str(exc),
                    "validator timeout diagnostic leaked raw text")
        else:
            raise RuntimeError("validator timeout was accepted")

        def synthetic_missing(*args: object, **kwargs: object) -> None:
            raise OSError("SYNTHETIC_OS_ERROR_SECRET_DO_NOT_LOG")

        module.CANONICAL_SUBPROCESS_RUN = synthetic_missing
        try:
            module.run_validator(module.DELETION_VALIDATOR, "deletion-under-load", "--require-reconciled")
        except module.ReconcileFailure as exc:
            require("OSError" in str(exc) and
                    "SYNTHETIC_OS_ERROR_SECRET_DO_NOT_LOG" not in str(exc),
                    "validator OS error diagnostic leaked raw text")
        else:
            raise RuntimeError("validator OS error was accepted")
        module.CANONICAL_SUBPROCESS_RUN = lambda *args, **kwargs: SimpleNamespace(returncode=0)
        module.run_validator(module.DELETION_VALIDATOR, "deletion-under-load", "--require-reconciled")
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



def exercise_deletion_load_optional_result_path() -> None:
    """Missing evidence is optional, but unsafe nodes must never become absence."""
    validator_path = ROOT / "scripts/validate-memory-os-deletion-under-load.py"
    spec = importlib.util.spec_from_file_location("deletion_load_optional_result", validator_path)
    require(spec is not None and spec.loader is not None, "optional-result validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    contract = validator.load(ROOT / "contracts/operations/deletion-under-load-contract.v1.json")
    contract["readiness"]["exactSourceResultCommitted"] = False
    contract["readiness"]["postFenceLoadExecuted"] = False

    with tempfile.TemporaryDirectory(prefix=".deletion-load-optional-negative-", dir=ROOT) as tmp:
        fixture_root = Path(tmp)
        result_path = fixture_root / validator.REVIEWED_RESULT_PATH
        result_path.parent.mkdir(parents=True)
        contract_path = fixture_root / "contracts/operations/deletion-under-load-contract.v1.json"
        contract_path.parent.mkdir(parents=True)
        contract_path.write_text(json.dumps(contract), encoding="utf-8")
        outside_canary = fixture_root / "outside-canary.txt"
        outside_canary.write_text("SYNTHETIC_OUTSIDE_CANARY", encoding="utf-8")
        original_root, original_contract, original_argv = validator.ROOT, validator.CONTRACT_PATH, sys.argv
        validator.ROOT, validator.CONTRACT_PATH = fixture_root, contract_path
        sys.argv = ["deletion-load-negative", "--expected-commit-sha", ""]
        try:
            require(validator.optional_result_present(result_path) is False,
                    "missing canonical result must remain optional")
            with contextlib.redirect_stdout(io.StringIO()):
                require(validator.main() == 0, "missing-result static positive failed")
            result_path.write_text("{}", encoding="utf-8")
            require(validator.optional_result_present(result_path) is True,
                    "regular canonical result was not detected")
            result_path.unlink()

            def reject(label: str) -> None:
                try:
                    validator.optional_result_present(result_path)
                except validator.ValidationFailure:
                    pass
                else:
                    raise RuntimeError(f"unsafe optional deletion result accepted: {label}")

            result_path.symlink_to(outside_canary)
            reject("direct existing symlink")
            result_path.unlink()
            result_path.symlink_to(fixture_root / "missing-target")
            reject("dangling symlink")
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    validator.main()
            except validator.ValidationFailure:
                pass
            else:
                raise RuntimeError("main accepted dangling optional result as missing")
            result_path.unlink()
            result_path.mkdir()
            reject("directory")
            result_path.rmdir()
            os.mkfifo(result_path)
            reject("FIFO")
            result_path.unlink()
            result_path.parent.rmdir()
            reject("missing parent")
            (fixture_root / "docs/fixtures").rmdir()
            alternate = fixture_root / "alternate-fixtures/memory-os-operability"
            alternate.mkdir(parents=True)
            (fixture_root / "docs/fixtures").symlink_to(alternate.parent, target_is_directory=True)
            reject("symlinked ancestor")
            (fixture_root / "docs/fixtures").unlink()
            try:
                validator.optional_result_present(fixture_root / "unreviewed-result.json")
            except validator.ValidationFailure:
                pass
            else:
                raise RuntimeError("optional deletion result accepted unreviewed path")
            require(outside_canary.read_text(encoding="utf-8") == "SYNTHETIC_OUTSIDE_CANARY",
                    "external synthetic canary changed")
        finally:
            validator.ROOT, validator.CONTRACT_PATH, sys.argv = (
                original_root, original_contract, original_argv
            )
    print("PASS: deletion-under-load optional-result 2 positives and 7 unsafe-path negatives")


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
    validator.validate_forbidden_result_markers(copy.deepcopy(result))
    for label, marker in (
        ("postgres", "PoStGrEs://synthetic"),
        ("postgresql", "POSTGRESQL://synthetic"),
        ("bearer", "bEaReR SYNTHETIC_SECRET_DO_NOT_LOG"),
        ("password", "PASSWORD=SYNTHETIC_SECRET_DO_NOT_LOG"),
        ("minio", "MiNiOaDmIn"),
        ("object key", "OBJECT_KEY"),
        ("account prefix", "AcCt_"),
        ("idempotency", "IdEm-synthetic"),
    ):
        altered = copy.deepcopy(result)
        altered["limitations"].append(marker)
        try:
            validator.validate_forbidden_result_markers(altered)
        except validator.ValidationFailure as exc:
            require("SYNTHETIC_SECRET_DO_NOT_LOG" not in str(exc),
                    f"forbidden marker leaked raw synthetic secret: {label}")
        else:
            raise RuntimeError(f"deletion load accepted mixed-case forbidden marker: {label}")
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
        ("contract top-level injection", lambda d: d.__setitem__("humanPromotionApproved", True)),
        ("contract missing description", lambda d: d.pop("description")),
        ("workload float alias", lambda d: d.__setitem__("preFenceRequests", 120.0)),
        ("scenario redirect", lambda d: d.__setitem__("scenarioId", "unreviewed")),
        ("boundary extra", lambda d: d["evidenceBoundary"].__setitem__("humanPromotionApproved", True)),
        ("boundary boolean alias", lambda d: d["evidenceBoundary"].__setitem__("productionEvidence", 0)),
        ("sequence altered", lambda d: d["requiredSequence"].__setitem__(0, "skip account creation")),
        ("abort missing", lambda d: d["abortCriteria"].pop()),
        ("limitations extra", lambda d: d["limitations"].append("production ready")),
        ("readiness extra", lambda d: d["readiness"].__setitem__("humanPromotionApproved", True)),
        ("readiness boolean alias", lambda d: d["readiness"].__setitem__("postFenceLoadExecuted", 1)),
        ("readiness promotion", lambda d: d["readiness"].__setitem__("productionReady", True)),
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
        ("result limitations missing scope", lambda d: d["limitations"].pop()),
        ("result limitations unreviewed claim", lambda d: d["limitations"].append("production ready")),
        ("result limitations reordered", lambda d: d["limitations"].reverse()),
        ("result limitations worker drift", lambda d: d["limitations"].__setitem__(1, "one account and many workers")),
        ("result limitations empty", lambda d: d.__setitem__("limitations", [])),
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
    print("PASS: deletion-under-load reviewed schema positive, 49 schema negatives and 8 mixed-case marker negatives")



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



def exercise_evidence_reference_path_admission(module: ModuleType) -> None:
    """Run the actual source-reference guard against disposable filesystem nodes."""
    with tempfile.TemporaryDirectory(prefix=".deletion-load-evidence-negative-", dir=ROOT) as tmp:
        fixture = Path(tmp)
        regular = fixture / "regular.json"
        regular.write_text("SYNTHETIC_CANARY", encoding="utf-8")
        relative = lambda path: str(path.relative_to(ROOT))
        module.require_reviewed_evidence_file(relative(regular))

        def reject(label: str, ref: object) -> None:
            try:
                module.require_reviewed_evidence_file(ref)
            except module.ReconcileFailure as exc:
                require("SYNTHETIC_CANARY" not in str(exc),
                        f"evidence reference leaked canary: {label}")
            else:
                raise RuntimeError(f"unsafe deletion-load evidence reference accepted: {label}")

        direct = fixture / "direct-link"
        direct.symlink_to(regular)
        reject("direct symlink", relative(direct))
        direct.unlink()
        dangling = fixture / "dangling-link"
        dangling.symlink_to(fixture / "missing-target")
        reject("dangling symlink", relative(dangling))
        dangling.unlink()
        actual = fixture / "actual"
        actual.mkdir()
        (actual / "file").write_text("synthetic", encoding="utf-8")
        alias = fixture / "alias"
        alias.symlink_to(actual, target_is_directory=True)
        reject("ancestor symlink", relative(alias / "file"))
        alias.unlink()
        directory = fixture / "directory"
        directory.mkdir()
        reject("directory", relative(directory))
        fifo = fixture / "fifo"
        os.mkfifo(fifo)
        reject("FIFO", relative(fifo))
        reject("missing", relative(fixture / "missing"))
        reject("absolute", str(regular))
        reject("traversal", "../outside.json")
        reject("dot segment", relative(regular).replace("/regular.json", "/./regular.json"))
        reject("duplicate separator", relative(regular).replace("/regular.json", "//regular.json"))
        reject("trailing separator", relative(regular) + "/")
        reject("backslash alias", relative(regular).replace("/", "\\"))
        reject("empty", "")
        reject("non-string", 42)
        require(regular.read_text(encoding="utf-8") == "SYNTHETIC_CANARY",
                "synthetic evidence canary was changed")
    print("PASS: deletion-under-load evidence reference positive and 14 unsafe-path negatives")


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



def exercise_deletion_load_numeric_boundary() -> None:
    """Run the standalone numeric protections through the actual CI-reachable validator."""
    path = ROOT / "scripts/validate-memory-os-deletion-under-load.py"
    spec = importlib.util.spec_from_file_location("deletion_load_numeric_reachable", path)
    require(spec is not None and spec.loader is not None, "numeric validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    require(validator.positive_number(1.25, "synthetic-positive") == 1.25,
            "deletion-load positive numeric control failed")
    for label, value in (
        ("positive infinity", float("inf")),
        ("negative infinity", float("-inf")),
        ("NaN", float("nan")),
        ("huge integer", 10 ** 500),
        ("boolean", True),
        ("zero", 0),
        ("negative", -1),
    ):
        try:
            validator.positive_number(value, "synthetic-negative")
        except validator.ValidationFailure as exc:
            require("SYNTHETIC_SECRET_DO_NOT_LOG" not in str(exc),
                    f"numeric rejection leaked synthetic secret: {label}")
        else:
            raise RuntimeError(f"deletion-load numeric accepted {label}")
    with tempfile.TemporaryDirectory(prefix=".deletion-load-numeric-reachable-", dir=ROOT) as tmp:
        fixture = Path(tmp) / "synthetic.json"
        for label, raw in (
            ("NaN", '{"value": NaN}'),
            ("Infinity", '{"value": Infinity}'),
            ("negative Infinity", '{"value": -Infinity}'),
            ("float overflow", '{"value": 1e999}'),
        ):
            fixture.write_text(raw, encoding="utf-8")
            try:
                validator.load(fixture)
            except validator.ValidationFailure as exc:
                require("SYNTHETIC_SECRET_DO_NOT_LOG" not in str(exc),
                        f"JSON numeric rejection leaked synthetic secret: {label}")
            else:
                raise RuntimeError(f"deletion-load JSON accepted {label}")
    print("PASS: deletion-under-load numeric positive, 7 typed and 4 JSON nonfinite negatives")


def exercise_deletion_load_utc_seconds_boundary() -> None:
    """Reject fractional result timestamps through the actual CI-reachable validator."""
    validator_path = ROOT / "scripts/validate-memory-os-deletion-under-load.py"
    spec = importlib.util.spec_from_file_location("deletion_load_utc_seconds_negative", validator_path)
    require(spec is not None and spec.loader is not None, "deletion load timestamp validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    canonical = validator.load(ROOT / validator.REVIEWED_RESULT_PATH)
    validator.validate_deletion_timestamps(copy.deepcopy(canonical))
    cases = (
        ("impossible date", ("scenario", "startedAt"), "2026-02-30T22:17:18Z"),
        ("timezone offset", ("scenario", "startedAt"), "2026-09-23T22:17:18+00:00"),
        ("missing seconds", ("scenario", "startedAt"), "2026-09-23T22:17Z"),
        ("fraction without digits", ("scenario", "startedAt"), "2026-09-23T22:17:18.Z"),
        ("fractional startedAt", ("scenario", "startedAt"), "2026-09-23T22:17:18.123Z"),
        ("fractional completedAt", ("scenario", "completedAt"), "2026-09-23T22:17:18.500Z"),
        ("fractional generatedAt", ("generatedAt",), "2026-09-23T22:17:19.123Z"),
        ("nonstring", ("scenario", "startedAt"), None),
        ("completion before start", ("scenario", "completedAt"), "2026-09-23T22:17:17Z"),
        ("generation before completion", ("generatedAt",), "2026-09-23T22:17:18Z"),
    )
    for label, keys, value in cases:
        altered = copy.deepcopy(canonical)
        cursor = altered
        for key in keys[:-1]:
            cursor = cursor[key]
        cursor[keys[-1]] = value
        try:
            validator.validate_deletion_timestamps(altered)
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"deletion load accepted invalid timestamp: {label}")
    print("PASS: deletion-under-load UTC positive and 10 timestamp negatives")


def exercise_deletion_load_batch_accounting() -> None:
    """Exercise exact status, typed counts and throughput in the CI-reachable suite."""
    validator_path = ROOT / "scripts/validate-memory-os-deletion-under-load.py"
    spec = importlib.util.spec_from_file_location("deletion_load_batch_reachable", validator_path)
    require(spec is not None and spec.loader is not None, "deletion load batch validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    canonical = validator.load(ROOT / validator.REVIEWED_RESULT_PATH)
    pre = canonical["scenario"]["preFence"]
    post = canonical["scenario"]["postFence"]
    validator.validate_batch(copy.deepcopy(pre), "synthetic-pre-positive", 120, 200, 120, 0)
    validator.validate_batch(copy.deepcopy(post), "synthetic-post-positive", 400, 401, 0, 400)
    cases = (
        ("float requests", ("summary", "requests"), 120.0),
        ("float successes", ("summary", "successes"), 120.0),
        ("float exact status count", ("statusCodeCounts", "200"), 120.0),
        ("float 2xx class", ("summary", "statusClassCounts", "2xx"), 120.0),
        ("boolean 5xx class", ("summary", "statusClassCounts", "5xx"), False),
        ("unknown class", ("summary", "statusClassCounts", "6xx"), 1),
        ("unreported 3xx", ("summary", "statusClassCounts", "3xx"), 1),
        ("invented low throughput", ("summary", "throughput"), 0.001),
        ("derived throughput overflow", ("summary", "durationSeconds"), 5e-324),
    )
    for label, keys, value in cases:
        altered = copy.deepcopy(pre)
        cursor = altered
        for key in keys[:-1]:
            cursor = cursor[key]
        cursor[keys[-1]] = value
        try:
            validator.validate_batch(altered, "synthetic-negative", 120, 200, 120, 0)
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"deletion load accepted invalid batch accounting: {label}")
    print("PASS: deletion-under-load batch 2 positives and 9 accounting negatives")


def exercise_deletion_load_source_io_boundary() -> None:
    """The source reconciler must not follow aliases or truncate authority on failed writes."""
    path = ROOT / "scripts/reconcile-memory-os-deletion-under-load-source.py"
    spec = importlib.util.spec_from_file_location("deletion_load_source_io_negative", path)
    require(spec is not None and spec.loader is not None, "source I/O guard import failed")
    source = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    with (
        tempfile.TemporaryDirectory(prefix="deletion-source-outside-") as outside_tmp,
        tempfile.TemporaryDirectory(prefix=".deletion-source-io-negative-", dir=ROOT) as inside_tmp,
    ):
        outside, inside = Path(outside_tmp), Path(inside_tmp)
        canary = outside / "canary.go"
        canary.write_text("SYNTHETIC_EXTERNAL_CANARY", encoding="utf-8")
        regular = inside / "source.go"
        regular.write_text("BEFORE", encoding="utf-8")
        os.chmod(regular, 0o640)
        require(source.read_source(regular) == "BEFORE", "source read positive failed")
        source.write_source(regular, "AFTER", "BEFORE")
        require(regular.read_text(encoding="utf-8") == "AFTER", "source atomic write positive failed")
        require(stat.S_IMODE(regular.stat().st_mode) == 0o640, "source write mode changed")
        require(not list(inside.glob("*.tmp")), "source positive left temporary residue")

        def reject(label: str, target: Path) -> None:
            for operation in (source.read_source, lambda p: source.write_source(p, "UNSAFE", "AFTER")):
                try:
                    operation(target)
                except RuntimeError as exc:
                    require("SYNTHETIC_EXTERNAL_CANARY" not in str(exc),
                            f"source I/O leaked external canary: {label}")
                else:
                    raise RuntimeError(f"source I/O accepted {label}")

        reject("outside", canary)
        direct = inside / "direct.go"
        direct.symlink_to(canary)
        reject("direct symlink", direct)
        dangling = inside / "dangling.go"
        dangling.symlink_to(inside / "missing-target")
        reject("dangling symlink", dangling)
        alias = inside / "alias"
        alias.symlink_to(outside, target_is_directory=True)
        reject("ancestor symlink", alias / "canary.go")
        directory = inside / "directory.go"
        directory.mkdir()
        reject("directory", directory)
        fifo = inside / "fifo.go"
        os.mkfifo(fifo)
        reject("FIFO", fifo)
        reject("missing", inside / "missing.go")
        oversized = inside / "oversized.go"
        oversized.write_bytes(b"x" * (source.MAX_SOURCE_BYTES + 1))
        try:
            source.read_source(oversized)
        except RuntimeError as exc:
            require("exceeds reviewed read limit" in str(exc), "oversized source wrong rejection")
        else:
            raise RuntimeError("oversized source accepted")
        invalid = inside / "invalid.go"
        invalid.write_bytes(bytes([255]))
        try:
            source.read_source(invalid)
        except RuntimeError:
            pass
        else:
            raise RuntimeError("invalid UTF-8 source accepted")
        try:
            source.write_source(regular, b"NOT_TEXT", "AFTER")
        except RuntimeError:
            pass
        else:
            raise RuntimeError("non-text source payload accepted")
        for label, invalid_payload, expected in (
            ("oversized write", "X" * (source.MAX_SOURCE_BYTES + 1), "exceeds reviewed write limit"),
            ("invalid Unicode", chr(0xD800), "invalid UTF-8"),
        ):
            try:
                source.write_source(regular, invalid_payload, "AFTER")
            except RuntimeError as exc:
                require(expected in str(exc), f"source {label} wrong rejection")
            else:
                raise RuntimeError(f"source {label} accepted")
            require(regular.read_text(encoding="utf-8") == "AFTER",
                    f"source {label} changed prior bytes")
        original_target = source.PATH
        source.PATH = regular
        try:
            try:
                source.main()
            except RuntimeError as exc:
                require("unreviewed deletion load source target" in str(exc),
                        "source main wrong target rejection")
            else:
                raise RuntimeError("source main accepted substituted target")
        finally:
            source.PATH = original_target
        try:
            source.write_source(regular, "STALE_OVERWRITE", "STALE_EXPECTATION")
        except RuntimeError as exc:
            require("changed since reviewed read" in str(exc), "stale source CAS wrong rejection")
        else:
            raise RuntimeError("source writer accepted stale original content")
        require(regular.read_text(encoding="utf-8") == "AFTER", "stale CAS changed bytes")
        original_chmod = source.os.chmod
        def synthetic_race_chmod(path: object, mode: int) -> None:
            original_chmod(path, mode)
            regular.write_text("RACED", encoding="utf-8")
        source.os.chmod = synthetic_race_chmod
        try:
            try:
                source.write_source(regular, "STALE_OVERWRITE", "AFTER")
            except RuntimeError as exc:
                require("changed before atomic replacement" in str(exc),
                        "pre-replace source CAS wrong rejection")
            else:
                raise RuntimeError("source writer overwrote concurrent local change")
        finally:
            source.os.chmod = original_chmod
        require(regular.read_text(encoding="utf-8") == "RACED",
                "source CAS overwrote concurrent fixture update")
        regular.write_text("AFTER", encoding="utf-8")
        require(not list(inside.glob("*.tmp")), "source CAS left temporary residue")
        original_replace = source.os.replace
        def failed_replace(*args: object, **kwargs: object) -> None:
            raise OSError("SYNTHETIC_REPLACE_SECRET_DO_NOT_LOG")
        source.os.replace = failed_replace
        try:
            try:
                source.write_source(regular, "NEW", "AFTER")
            except RuntimeError as exc:
                require("atomic write failed (OSError)" in str(exc) and
                        "SYNTHETIC_REPLACE_SECRET_DO_NOT_LOG" not in str(exc),
                        "source replace failure leaked or misclassified")
            else:
                raise RuntimeError("source replace failure was accepted")
        finally:
            source.os.replace = original_replace
        require(regular.read_text(encoding="utf-8") == "AFTER", "source rollback changed bytes")
        require(stat.S_IMODE(regular.stat().st_mode) == 0o640, "source rollback changed mode")
        require(canary.read_text(encoding="utf-8") == "SYNTHETIC_EXTERNAL_CANARY",
                "source I/O changed external canary")
        require(not list(inside.glob("*.tmp")), "source I/O left temporary residue")
    print("PASS: deletion-load source bounded atomic I/O, 7 unsafe nodes, CAS race and rollback negatives")


def exercise_deletion_load_source_replace_once() -> None:
    """The source reconciler must not mistake mixed stale and reviewed code for success."""
    path = ROOT / "scripts/reconcile-memory-os-deletion-under-load-source.py"
    spec = importlib.util.spec_from_file_location("deletion_load_source_replace_negative", path)
    require(spec is not None and spec.loader is not None, "source reconcile import failed")
    source = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    updated, changed = source.replace_once("BEFORE", "BEFORE", "AFTER", "synthetic")
    require((updated, changed) == ("AFTER", True), "source replacement positive failed")
    updated, changed = source.replace_once("AFTER", "BEFORE", "AFTER", "synthetic")
    require((updated, changed) == ("AFTER", False), "source idempotent positive failed")
    anchor = "type X struct {}\\n"
    helper = anchor + "func helper() {}\\n"
    updated, changed = source.replace_once(helper, anchor, helper, "synthetic-overlap")
    require((updated, changed) == (helper, False), "source overlap idempotent positive failed")
    for label, text_value, old, new in (
        ("mixed stale and reviewed", "BEFORE AFTER", "BEFORE", "AFTER"),
        ("duplicate reviewed", "AFTER AFTER", "BEFORE", "AFTER"),
        ("duplicate stale", "BEFORE BEFORE", "BEFORE", "AFTER"),
        ("missing anchor", "UNRELATED", "BEFORE", "AFTER"),
        ("overlap plus stale", helper + anchor, anchor, helper),
        ("duplicate overlapping helper", helper + helper, anchor, helper),
    ):
        try:
            source.replace_once(text_value, old, new, "synthetic-negative")
        except RuntimeError as exc:
            require("authority drift" in str(exc), f"source replacement wrong rejection: {label}")
        else:
            raise RuntimeError(f"source replacement accepted {label}")
    print("PASS: deletion-load source reconcile 3 positives and 6 mixed/duplicate negatives")


def exercise_deletion_load_git_ancestry_boundary() -> None:
    validator_path = ROOT / "scripts/validate-memory-os-deletion-under-load.py"
    spec = importlib.util.spec_from_file_location("deletion_load_git_ancestry_negative", validator_path)
    require(spec is not None and spec.loader is not None, "deletion load ancestry validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    original_run = validator.subprocess.run
    valid_sha = "a" * 40
    calls: list[object] = []

    def synthetic_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append(command)
        require(command == ["git", "merge-base", "--is-ancestor", valid_sha, "HEAD"],
                "deletion load ancestry command drift")
        require(kwargs.get("cwd") == validator.ROOT and kwargs.get("timeout") == 10 and
                kwargs.get("check") is False and
                kwargs.get("stdout") == validator.subprocess.DEVNULL and
                kwargs.get("stderr") == validator.subprocess.DEVNULL,
                "deletion load ancestry subprocess boundary drift")
        return SimpleNamespace(returncode=0)

    try:
        validator.subprocess.run = synthetic_run
        require(validator.is_ancestor(valid_sha), "valid ancestor control rejected")
        require(len(calls) == 1, "valid ancestor control not executed")
        for bad in ("", "unreviewed", "g" * 40, None, 1):
            require(not validator.is_ancestor(bad), "malformed ancestry SHA accepted")
        require(len(calls) == 1, "malformed SHA reached git subprocess")
        validator.subprocess.run = lambda *args, **kwargs: SimpleNamespace(returncode=128)
        require(not validator.is_ancestor(valid_sha), "failed ancestry command accepted")
        validator.subprocess.run = lambda *args, **kwargs: SimpleNamespace(returncode=True)
        require(not validator.is_ancestor(valid_sha), "boolean ancestry exit code accepted")

        def timed_out(*args: object, **kwargs: object) -> None:
            raise validator.subprocess.TimeoutExpired("git", 10)

        validator.subprocess.run = timed_out
        require(not validator.is_ancestor(valid_sha), "timed-out ancestry command accepted")

        def missing_git(*args: object, **kwargs: object) -> None:
            raise OSError("SYNTHETIC_ANCESTRY_SECRET_DO_NOT_LOG")

        validator.subprocess.run = missing_git
        require(not validator.is_ancestor(valid_sha), "failed git execution accepted")
    finally:
        validator.subprocess.run = original_run
    print("PASS: deletion-under-load bounded Git ancestry positive and 9 negatives")



def exercise_validator_command_authority(module: ModuleType) -> None:
    original_run = module.CANONICAL_SUBPROCESS_RUN
    original_guard = module.enforce_runtime_authorities
    calls: list[object] = []

    def successful_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append(command)
        return SimpleNamespace(returncode=0)

    module.CANONICAL_SUBPROCESS_RUN = successful_run
    module.enforce_runtime_authorities = lambda: None
    try:
        for label, path, name, args in (
            ("unreviewed script", ROOT / "scripts/validate-memory-os-capacity-ramp.py", "load", ()),
            ("mismatched label", module.DELETION_VALIDATOR, "load", ("--require-reconciled",)),
            ("missing deletion arguments", module.DELETION_VALIDATOR, "deletion-under-load", ()),
            ("load unexpected arguments", module.LOAD_VALIDATOR, "load", ("--require-reconciled",)),
            ("operability unexpected arguments", module.OPERABILITY_VALIDATOR, "operability", ("--require-reconciled",)),
            ("malformed SHA", module.DELETION_VALIDATOR, "deletion-under-load", ("--expected-commit-sha", "not-sha")),
            ("uppercase SHA", module.DELETION_VALIDATOR, "deletion-under-load", ("--expected-commit-sha", "A" * 40)),
            ("extra arguments", module.DELETION_VALIDATOR, "deletion-under-load", ("--expected-commit-sha", "a" * 40, "--require-reconciled")),
            ("secret label", module.DELETION_VALIDATOR, "SYNTHETIC_SECRET_DO_NOT_LOG", ("--require-reconciled",)),
        ):
            try:
                module.run_validator(path, name, *args)
            except module.ReconcileFailure as exc:
                require("unreviewed deletion-load validator" in str(exc) and
                        "SYNTHETIC_SECRET_DO_NOT_LOG" not in str(exc),
                        f"validator command wrong rejection: {label}")
            else:
                raise RuntimeError(f"validator command accepted {label}")
        require(not calls, "unreviewed validator command reached subprocess")
        module.run_validator(module.DELETION_VALIDATOR, "deletion-under-load", "--expected-commit-sha", "a" * 40)
        module.run_validator(module.LOAD_VALIDATOR, "load")
        module.run_validator(module.OPERABILITY_VALIDATOR, "operability")
        require(len(calls) == 3, "reviewed validator commands did not execute")
    finally:
        module.CANONICAL_SUBPROCESS_RUN = original_run
        module.enforce_runtime_authorities = original_guard
    print("PASS: deletion-under-load validator command authority 3 positives and 9 negatives")



def exercise_deletion_load_workflow_diagnostic() -> None:
    """Prove the actual publisher inline diagnostic is redacted and path-safe."""
    workflow = (ROOT / ".github/workflows/deletion-under-load.yml").read_text(encoding="utf-8")
    required = (
        "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "uses: actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5",
        "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        'test "$GITHUB_REF" = "refs/heads/so"',
        '"output": "Deletion-under-load local proof failed; raw validator output withheld."',
        '"containsSecrets": False', '"productionEvidence": False',
        '"requestsStartedBeforeFenceCovered": False',
        "candidate.is_symlink()", "os.fchmod(handle.fileno(), mode)",
        "os.fsync(handle.fileno())", "os.replace(tmp_path, path)",
        "tmp_path.unlink(missing_ok=True)",
    )
    for marker in required:
        require(marker in workflow, "deletion-load diagnostic source guard missing: " + marker[:70])
    for forbidden in ("docker logs memory-os-deletion-load-minio", "text[-12000:]",
                      "checkout@v4", "setup-go@v5", "setup-python@v5",
                      'errors="replace"', 'text = re.sub('):
        require(forbidden not in workflow, "unsafe deletion-load diagnostic: " + forbidden)
    marker = "          python - <<'PY'" + chr(10)
    require(workflow.count(marker) == 1, "deletion-load inline diagnostic entrypoint drift")
    code = workflow.split(marker, 1)[1].split(chr(10) + "          PY", 1)[0]
    code = chr(10).join(line[10:] if line.startswith("          ") else line
                        for line in code.splitlines())
    with tempfile.TemporaryDirectory(prefix="deletion-load-diagnostic-negative-") as tmp:
        root = Path(tmp)
        target = root / "docs/fixtures/memory-os-operability/deletion-under-load-diagnostic.last.json"
        canary = root / "external-canary"
        canary.write_text("UNCHANGED", encoding="utf-8")
        env = dict(os.environ, SOURCE_SHA="a" * 40, DELETION_LOAD_EXIT_CODE="17")
        def run() -> subprocess.CompletedProcess[bytes]:
            return subprocess.run([sys.executable, "-c", code], cwd=root, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  timeout=10, check=False)
        require(run().returncode != 0, "diagnostic accepted missing parent")
        target.parent.mkdir(parents=True)
        require(run().returncode == 0, "diagnostic positive writer failed")
        value = json.loads(target.read_text(encoding="utf-8"))
        require(value["output"] == "Deletion-under-load local proof failed; raw validator output withheld."
                and value["sourceCommitSha"] == "a" * 40 and value["exitCode"] == 17,
                "diagnostic fixed output/source/exit binding drift")
        require(value["containsSecrets"] is False and value["productionEvidence"] is False
                and value["requestsStartedBeforeFenceCovered"] is False,
                "diagnostic crossed local evidence boundary")
        os.chmod(target, 0o640)
        require(run().returncode == 0 and stat.S_IMODE(target.stat().st_mode) == 0o640,
                "diagnostic writer changed existing mode")
        target.unlink()
        target.symlink_to(canary)
        require(run().returncode != 0, "diagnostic accepted symlink target")
        require(canary.read_text(encoding="utf-8") == "UNCHANGED",
                "diagnostic overwrote external canary")
        target.unlink()
        target.mkdir()
        require(run().returncode != 0, "diagnostic accepted directory target")
        target.rmdir()
        if hasattr(os, "mkfifo"):
            os.mkfifo(target)
            require(run().returncode != 0, "diagnostic accepted FIFO target")
            target.unlink()
        target.parent.rmdir()
        target.parent.symlink_to(root)
        require(run().returncode != 0, "diagnostic accepted symlink parent")
        require(canary.read_text(encoding="utf-8") == "UNCHANGED",
                "diagnostic changed external canary")
        require(not list(root.rglob("*.tmp")), "diagnostic writer left temporary residue")
    print("PASS: deletion-load fixed diagnostic, atomic mode, unsafe nodes and canary")




def exercise_deletion_load_authority_gate_source() -> None:
    """Guard read-only CI checkout identity, immutable actions and runner reachability."""
    path = ROOT / ".github/workflows/deletion-under-load-authority-pr.yml"
    source = path.read_text(encoding="utf-8")
    required = (
        "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "permissions:" + chr(10) + "  contents: read",
        "ref: " + chr(36) + "{{ github.event.pull_request.head.sha || github.sha }}",
        'test "$(git rev-parse HEAD)" = "$EXPECTED_SOURCE_SHA"',
        'test -z "$(git status --porcelain)"',
        '      - "services/import-api/internal/httpserver/deletion_under_load_test.go"',
        "python scripts/validate-memory-os-deletion-under-load-reconcile-negative.py",
        '      - "scripts/reconcile-memory-os-deletion-under-load-source.py"',
        '      - ".github/workflows/reconcile-deletion-under-load-source.yml"',
    )
    def policy(value: str) -> None:
        for marker in required:
            require(marker in value, "deletion-load read-only gate source drift: " + marker[:70])
        require(value.count("uses: actions/checkout@") == 1 and
                value.count("uses: actions/setup-python@") == 1,
                "deletion-load read-only gate has duplicate or substituted Actions")
        require(value.count(required[5]) == 2,
                "deletion-load clean-worktree source checks must run before and after")
        require(value.count(required[6]) == 2,
                "deletion-load Go runner not in both CI path filters")
        require(value.count(required[8]) == 2,
                "deletion-load source reconciler not in both CI path filters")
        require(value.count(required[9]) == 2,
                "deletion-load source publisher not in both CI path filters")
        require(value.count("    branches:" + chr(10) + "      - so") == 2,
                "deletion-load CI branch scope drift")
        require("checkout@v4" not in value and "setup-python@v5" not in value,
                "deletion-load read-only gate uses floating Actions")
    policy(source)
    for marker in required:
        mutated = source.replace(marker, "SYNTHETIC_UNREVIEWED", 1)
        require(mutated != source, "deletion-load gate negative mutation unreachable")
        try:
            policy(mutated)
        except RuntimeError:
            pass
        else:
            raise RuntimeError("deletion-load gate accepted missing authority")
    for addition in ("uses: actions/checkout@v4", "uses: actions/setup-python@v5"):
        try:
            policy(source + chr(10) + addition)
        except RuntimeError:
            pass
        else:
            raise RuntimeError("deletion-load gate accepted duplicate Action")
    print("PASS: deletion-load read-only gate immutable Actions and 10 source negatives")


def exercise_deletion_load_runner_source_binding() -> None:
    """Bind the complete Go proof runner to a reviewed Git blob and CI path."""
    reviewed_path = "services/import-api/internal/httpserver/deletion_under_load_test.go"
    reviewed_blob = "d2ce5f95921a0723c0d61e9c44573c507babd66d"
    runner = ROOT / reviewed_path
    require(runner.is_file() and all(not candidate.is_symlink()
                                    for candidate in (runner, *runner.parents)),
            "deletion-load Go runner missing, unsafe or symlinked")
    try:
        require(runner.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix()
                == reviewed_path, "deletion-load Go runner source path drift")
    except (OSError, ValueError):
        raise RuntimeError("deletion-load Go runner escaped canonical root") from None
    raw = runner.read_bytes()
    require(0 < len(raw) <= 1024 * 1024, "deletion-load Go runner size drift")
    def git_blob(payload: bytes) -> str:
        return hashlib.sha1(b"blob " + str(len(payload)).encode("ascii")
                            + bytes([0]) + payload).hexdigest()
    require(git_blob(raw) == reviewed_blob, "deletion-load Go runner unreviewed Git blob")
    for label, mutation in (
        ("appended bypass", raw + bytes([10]) + b"// SYNTHETIC_BYPASS"),
        ("truncated runner", raw[:-1]),
        ("changed request count", raw.replace(b"400", b"401", 1)),
    ):
        require(mutation != raw and git_blob(mutation) != reviewed_blob,
                "deletion-load runner source negative ineffective: " + label)
    gate = (ROOT / ".github/workflows/deletion-under-load-authority-pr.yml").read_text(encoding="utf-8")
    require(gate.count('      - "' + reviewed_path + '"') == 2,
            "deletion-load Go runner changes do not trigger both read-only authority gates")
    publisher = (ROOT / ".github/workflows/deletion-under-load.yml").read_text(encoding="utf-8")
    require("-run '^TestAccountDeletionPostFenceLoadLocalDependencies$'" in publisher,
            "deletion-load publisher no longer invokes reviewed Go test")
    print("PASS: deletion-load complete Go runner Git blob and CI reachability")



def exercise_deletion_load_proof_log_cleanup() -> None:
    """Run the exact publisher EXIT trap with a synthetic private log."""
    workflow = (ROOT / ".github/workflows/deletion-under-load.yml").read_text(encoding="utf-8")
    marker = 'trap \'rm -f "$log"\' EXIT'
    require(workflow.count(marker) == 1, "deletion-load proof log cleanup trap missing or duplicated")
    require('"/tmp/memory-os-deletion-under-load.log").read_text' not in workflow,
            "deletion-load diagnostic unexpectedly rereads private proof log")
    line = next(value.strip() for value in workflow.splitlines() if marker in value)
    with tempfile.TemporaryDirectory(prefix="deletion-load-log-negative-") as tmp:
        path = Path(tmp) / "synthetic-proof.log"
        script = 'log="$1"; : > "$log"; ' + line + '; printf "SYNTHETIC_SECRET" >> "$log"; exit 17'
        result = subprocess.run(["bash", "-c", script, "bash", str(path)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=10, check=False)
        require(result.returncode == 17 and not path.exists(),
                "deletion-load proof log cleanup did not run on failed test")
        require(b"SYNTHETIC_SECRET" not in result.stdout + result.stderr,
                "deletion-load proof log cleanup leaked synthetic log")
    print("PASS: deletion-load exact publisher trap removes private log on failure")



def exercise_deletion_load_source_reconcile_workflow() -> None:
    """Pin the source-writing workflow and require branch/CAS authority."""
    workflow = (ROOT / ".github/workflows/reconcile-deletion-under-load-source.yml").read_text(encoding="utf-8")
    required = (
        "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "uses: actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5",
        'test "$GITHUB_REF" = "refs/heads/so"',
        'test "$(git rev-parse HEAD)" = "' + chr(36) + '{{ github.sha }}"',
        'if [[ "$(git rev-parse origin/so)" != "$SOURCE_SHA" ]]; then',
        "permissions:" + chr(10) + "  contents: read",
        "    permissions:" + chr(10) + "      contents: write",
    )
    def policy(value: str) -> None:
        for marker in required:
            require(marker in value, "deletion-load source publisher authority drift: " + marker[:65])
        for marker in required[:3]:
            require(value.count(marker) == 2,
                    "deletion-load source publisher Actions count drift")
        require(value.count("uses: actions/checkout@") == 2 and
                value.count("uses: actions/setup-python@") == 2 and
                value.count("uses: actions/setup-go@") == 2,
                "deletion-load source publisher floating or duplicate Action")
        require(value.count("    branches:" + chr(10) + "      - so") == 2,
                "deletion-load source publisher branch scope drift")
        require(value.count("git push origin HEAD:so") == 1,
                "deletion-load source publisher push target drift")
    policy(workflow)
    for marker in required:
        mutated = workflow.replace(marker, "SYNTHETIC_UNREVIEWED", 1)
        require(mutated != workflow, "deletion-load source publisher mutation unreachable")
        try:
            policy(mutated)
        except RuntimeError:
            pass
        else:
            raise RuntimeError("deletion-load source publisher accepted removed authority")
    print("PASS: deletion-load source publisher immutable Actions, branch and CAS negatives")


def main() -> int:
    exercise_deletion_load_source_reconcile_workflow()
    exercise_deletion_load_proof_log_cleanup()
    exercise_deletion_load_authority_gate_source()
    exercise_deletion_load_runner_source_binding()
    exercise_deletion_load_workflow_diagnostic()
    exercise_deletion_load_json_reader()
    exercise_deletion_load_numeric_boundary()
    exercise_deletion_load_optional_result_path()
    exercise_deletion_load_utc_seconds_boundary()
    exercise_deletion_load_batch_accounting()
    exercise_deletion_load_git_ancestry_boundary()
    exercise_deletion_load_source_replace_once()
    exercise_deletion_load_source_io_boundary()
    exercise_deletion_load_reviewed_schema()
    module = load_target()
    exercise_reconciler_json_reader(module)
    module.enforce_runtime_authorities()
    module.enforce_atomic_writer_authority()
    exercise_evidence_reference_path_admission(module)

    expect_rejection(module, "repository root", lambda: swap_attr(module, "ROOT", module.CANONICAL_ROOT / "scripts"))
    expect_rejection(module, "deletion contract", lambda: swap_attr(module, "CONTRACT_PATH", module.CANONICAL_LOAD_PATH))
    expect_rejection(module, "load contract", lambda: swap_attr(module, "LOAD_PATH", module.CANONICAL_CONTRACT_PATH))
    expect_rejection(module, "production status", lambda: swap_attr(module, "STATUS_PATH", module.CANONICAL_LOAD_PATH))
    expect_rejection(module, "result path", lambda: swap_attr(module, "RESULT_PATH", module.CANONICAL_CONTRACT_PATH))
    expect_rejection(module, "deletion validator", lambda: swap_attr(module, "DELETION_VALIDATOR", module.CANONICAL_LOAD_VALIDATOR))
    expect_rejection(module, "load validator", lambda: swap_attr(module, "LOAD_VALIDATOR", module.CANONICAL_DELETION_VALIDATOR))
    expect_rejection(module, "operability validator", lambda: swap_attr(module, "OPERABILITY_VALIDATOR", module.CANONICAL_LOAD_VALIDATOR))

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
    exercise_validator_command_authority(module)
    exercise_atomic_path_substitution_rejection(module)
    exercise_rollback_failure(module)
    exercise_transaction_primary_failure_redaction(module)
    require_snapshots_unchanged(canonical_snapshots(module))
    require_modes_unchanged(canonical_modes(module))
    print("Deletion-under-load reconcile negative checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
