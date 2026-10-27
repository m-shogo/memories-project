#!/usr/bin/env python3
"""Prove promotion-review reconcile pins authorities, rolls back rejection, and cleans writer locks."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-promotion-review.py"
WRITER = ROOT / "scripts/register-memory-os-backup-restore-promotion-review.py"
WORKFLOW = ROOT / ".github/workflows/backup-restore-promotion-review.yml"
CANONICAL_CONTRACT = ROOT / "contracts/operations/backup-restore-promotion-review-contract.v1.json"
CANONICAL_REGISTRY = ROOT / "contracts/operations/backup-restore-promotion-review-registry.v1.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(reconciler: Any, name: str, expected: str) -> None:
    try:
        reconciler.main()
    except reconciler.Fail as exc:
        require(expected in str(exc), f"{name} rejected at wrong boundary: {exc}")
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"{name} unexpectedly accepted")


def assert_canonical_unchanged(
    original_contract: bytes,
    original_registry: bytes,
    name: str,
    expected_contract_mode: int | None = None,
    expected_registry_mode: int | None = None,
) -> None:
    require(CANONICAL_CONTRACT.read_bytes() == original_contract, f"{name} changed promotion review contract")
    require(CANONICAL_REGISTRY.read_bytes() == original_registry, f"{name} changed promotion review registry")
    if expected_contract_mode is not None:
        require(CANONICAL_CONTRACT.stat().st_mode & 0o777 == expected_contract_mode, f"{name} changed promotion review contract mode")
    if expected_registry_mode is not None:
        require(CANONICAL_REGISTRY.stat().st_mode & 0o777 == expected_registry_mode, f"{name} changed promotion review registry mode")


def assert_fixture_unchanged(
    reconciler: Any,
    original_contract: bytes,
    original_registry: bytes,
    name: str,
    expected_contract_mode: int,
    expected_registry_mode: int,
) -> None:
    require(reconciler.CONTRACT.read_bytes() == original_contract, f"{name} changed isolated promotion review contract bytes")
    require(reconciler.REGISTRY.read_bytes() == original_registry, f"{name} changed isolated promotion review registry bytes")
    require(reconciler.CONTRACT.stat().st_mode & 0o777 == expected_contract_mode, f"{name} changed isolated promotion review contract mode")
    require(reconciler.REGISTRY.stat().st_mode & 0o777 == expected_registry_mode, f"{name} changed isolated promotion review registry mode")


@contextmanager
def isolated_reconcile_authorities(reconciler: Any):
    path_fields = (
        "ROOT", "CONTRACT", "REGISTRY", "GEN_REGISTRY", "WRITER", "VALIDATOR",
        "OPERABILITY_VALIDATOR", "STATUS",
    )
    original_paths = {field: getattr(reconciler, field) for field in path_fields}
    original_load_writer = reconciler.load_writer
    original_validate_generation_registry = reconciler.validate_generation_registry
    original_run_validator = reconciler.run_validator

    class FixturePromotionWriter:
        @staticmethod
        def reconcile_current_decision(registry: dict[str, Any]) -> tuple[list[dict[str, Any]], Any]:
            rows = registry.get("records")
            require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "isolated promotion review rows invalid")
            return rows, registry.get("currentDecisionId")

    class FixtureGenerationWriter:
        @staticmethod
        def candidate(_row: dict[str, Any]) -> bool:
            return False

    with tempfile.TemporaryDirectory(prefix="memory-os-promotion-review-reconcile-negative-") as tmp:
        fixture_root = Path(tmp)
        sources = (
            (CANONICAL_CONTRACT, reconciler.CONTRACT_REL),
            (CANONICAL_REGISTRY, reconciler.REGISTRY_REL),
            (ROOT / reconciler.GEN_REGISTRY_REL, reconciler.GEN_REGISTRY_REL),
            (ROOT / reconciler.WRITER_REL, reconciler.WRITER_REL),
            (ROOT / reconciler.VALIDATOR_REL, reconciler.VALIDATOR_REL),
            (ROOT / reconciler.OPERABILITY_VALIDATOR_REL, reconciler.OPERABILITY_VALIDATOR_REL),
            (ROOT / reconciler.STATUS_REL, reconciler.STATUS_REL),
        )
        for source, relative in sources:
            destination = fixture_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        reconciler.ROOT = fixture_root
        reconciler.CONTRACT = fixture_root / reconciler.CONTRACT_REL
        reconciler.REGISTRY = fixture_root / reconciler.REGISTRY_REL
        reconciler.GEN_REGISTRY = fixture_root / reconciler.GEN_REGISTRY_REL
        reconciler.WRITER = fixture_root / reconciler.WRITER_REL
        reconciler.VALIDATOR = fixture_root / reconciler.VALIDATOR_REL
        reconciler.OPERABILITY_VALIDATOR = fixture_root / reconciler.OPERABILITY_VALIDATOR_REL
        reconciler.STATUS = fixture_root / reconciler.STATUS_REL
        reconciler.load_writer = lambda: FixturePromotionWriter()

        def isolated_generation_registry(_writer: Any, registry: dict[str, Any]):
            rows = registry.get("records")
            require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "isolated generation evidence rows invalid")
            return FixtureGenerationWriter(), rows

        reconciler.validate_generation_registry = isolated_generation_registry
        reconciler.run_validator = lambda _path, _label: None
        try:
            yield reconciler
        finally:
            reconciler.load_writer = original_load_writer
            reconciler.validate_generation_registry = original_validate_generation_registry
            reconciler.run_validator = original_run_validator
            for field, value in original_paths.items():
                setattr(reconciler, field, value)


def expect_authority_substitution_rejected(
    reconciler: Any,
    attribute: str,
    substitute: Path,
    name: str,
    expected: str,
    original_contract: bytes,
    original_registry: bytes,
) -> None:
    original = getattr(reconciler, attribute)
    setattr(reconciler, attribute, substitute)
    try:
        expect_rejected(reconciler, name, expected)
        assert_canonical_unchanged(original_contract, original_registry, name)
    finally:
        setattr(reconciler, attribute, original)


def validate_atomic_diagnostic_publication() -> None:
    require(WORKFLOW.is_file(), "promotion review workflow missing")
    text = WORKFLOW.read_text(encoding="utf-8")
    required = (
        "tempfile.mkstemp(",
        "dir=path.parent",
        "handle.flush()",
        "os.fsync(handle.fileno())",
        "os.replace(tmp_name, path)",
        "os.unlink(tmp_name)",
        "mode = path.stat().st_mode & 0o777 if path.exists() else None",
        "os.fchmod(fd, mode)",
    )
    missing = [fragment for fragment in required if fragment not in text]
    require(not missing, f"promotion review diagnostic publication is not crash-safe and mode-preserving: missing {missing}")
    require(
        "path.write_text(json.dumps(value" not in text,
        "promotion review diagnostic publication regressed to direct write_text",
    )


def prove_mode_preserving_atomic_write(reconciler: Any, original_contract: bytes, original_registry: bytes) -> None:
    canonical_contract_mode = CANONICAL_CONTRACT.stat().st_mode & 0o777
    canonical_registry_mode = CANONICAL_REGISTRY.stat().st_mode & 0o777
    with isolated_reconcile_authorities(reconciler):
        fixture_contract = reconciler.CONTRACT.read_bytes()
        fixture_registry = reconciler.REGISTRY.read_bytes()
        reconciler.CONTRACT.chmod(0o640)
        reconciler.REGISTRY.chmod(0o640)
        reconciler.write_text(reconciler.CONTRACT, fixture_contract.decode("utf-8"))
        reconciler.write_text(reconciler.REGISTRY, fixture_registry.decode("utf-8"))
        assert_fixture_unchanged(reconciler, fixture_contract, fixture_registry, "mode-preserving atomic write", 0o640, 0o640)
    assert_canonical_unchanged(original_contract, original_registry, "isolated mode-preserving atomic write", canonical_contract_mode, canonical_registry_mode)
    print("PASS boundary: successful atomic promotion-review writes preserve isolated authority modes without mutating canonical authorities")


def prove_atomic_write_failure(reconciler: Any, original_contract: bytes, original_registry: bytes) -> None:
    original_replace = reconciler.os.replace
    canonical_contract_mode = CANONICAL_CONTRACT.stat().st_mode & 0o777
    canonical_registry_mode = CANONICAL_REGISTRY.stat().st_mode & 0o777

    def reject_replace(source: str | Path, destination: str | Path) -> None:
        raise OSError("PRIVATE_PROMOTION_RECONCILE_ATOMIC_CANARY")

    with isolated_reconcile_authorities(reconciler):
        fixture_contract = reconciler.CONTRACT.read_bytes()
        fixture_registry = reconciler.REGISTRY.read_bytes()
        reconciler.CONTRACT.chmod(0o640)
        reconciler.REGISTRY.chmod(0o640)
        reconciler.os.replace = reject_replace
        try:
            try:
                reconciler.write_text(reconciler.CONTRACT, fixture_contract.decode("utf-8") + " ")
            except reconciler.Fail as exc:
                require(str(exc) == "promotion reconcile authority atomic write failed"
                        and exc.__suppress_context__
                        and "PRIVATE_PROMOTION_RECONCILE_ATOMIC_CANARY" not in str(exc),
                        "atomic write rejected at wrong/private boundary")
            else:
                raise Fail("synthetic promotion-review atomic replace failure unexpectedly accepted")

            assert_fixture_unchanged(reconciler, fixture_contract, fixture_registry, "atomic replace rejection", 0o640, 0o640)
            leftovers = (
                list(reconciler.CONTRACT.parent.glob(f".{reconciler.CONTRACT.name}.*.tmp"))
                + list(reconciler.REGISTRY.parent.glob(f".{reconciler.REGISTRY.name}.*.tmp"))
            )
            require(not leftovers, f"atomic replace rejection left temporary isolated promotion-review authority files: {leftovers}")
        finally:
            reconciler.os.replace = original_replace
    assert_canonical_unchanged(original_contract, original_registry, "isolated atomic replace rejection", canonical_contract_mode, canonical_registry_mode)
    print("PASS boundary: failed atomic promotion-review write preserves isolated bytes/modes and canonical authorities")


def prove_second_replace_failure_rolls_back_transaction(
    reconciler: Any,
    original_contract: bytes,
    original_registry: bytes,
) -> None:
    original_replace = reconciler.os.replace
    canonical_contract_mode = CANONICAL_CONTRACT.stat().st_mode & 0o777
    canonical_registry_mode = CANONICAL_REGISTRY.stat().st_mode & 0o777
    replace_calls = 0

    def reject_second_replace(source: str | Path, destination: str | Path) -> None:
        nonlocal replace_calls
        replace_calls += 1
        if replace_calls == 2:
            raise OSError("PRIVATE_PROMOTION_RECONCILE_REPLACE_CANARY")
        original_replace(source, destination)

    with isolated_reconcile_authorities(reconciler):
        fixture_contract = reconciler.CONTRACT.read_bytes()
        fixture_registry = reconciler.REGISTRY.read_bytes()
        reconciler.CONTRACT.chmod(0o640)
        reconciler.REGISTRY.chmod(0o640)
        reconciler.os.replace = reject_second_replace
        try:
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                require(str(exc) == "promotion review reconcile transaction failed (Fail); rollback completed"
                        and exc.__suppress_context__
                        and "PRIVATE_PROMOTION_RECONCILE_REPLACE_CANARY" not in str(exc),
                        "second replace rejected at wrong/private boundary")
            else:
                raise Fail("synthetic second promotion-review replace failure unexpectedly accepted")

            require(replace_calls == 4, f"second replace failure did not execute complete two-authority rollback: {replace_calls} replace calls")
            assert_fixture_unchanged(
                reconciler,
                fixture_contract,
                fixture_registry,
                "second replace transaction rejection",
                0o640,
                0o640,
            )
            leftovers = (
                list(reconciler.CONTRACT.parent.glob(f".{reconciler.CONTRACT.name}.*.tmp"))
                + list(reconciler.REGISTRY.parent.glob(f".{reconciler.REGISTRY.name}.*.tmp"))
            )
            require(not leftovers, f"second replace rejection left temporary isolated promotion-review authority files: {leftovers}")
        finally:
            reconciler.os.replace = original_replace
    assert_canonical_unchanged(original_contract, original_registry, "isolated second replace transaction rejection", canonical_contract_mode, canonical_registry_mode)
    print("PASS boundary: second promotion-review replace failure rolls back isolated authorities with exact bytes/modes")


def prove_rollback_attempts_all_authorities(reconciler: Any) -> None:
    original_write_text = reconciler.write_text
    original_repo_relative = reconciler.repo_relative
    first = Path("/synthetic/promotion-registry.json")
    second = Path("/synthetic/promotion-contract.json")
    attempts: list[Path] = []

    def fail_first_restore(path: Path, _text: str) -> None:
        attempts.append(path)
        if path == first:
            raise reconciler.Fail("PRIVATE_PROMOTION_RECONCILE_ROLLBACK_CANARY")

    reconciler.write_text = fail_first_restore
    reconciler.repo_relative = lambda path: Path(path.name)
    try:
        try:
            reconciler.restore_authorities(
                ((first, "registry-original"), (second, "contract-original")),
                reconciler.Fail("PRIVATE_PROMOTION_RECONCILE_PRIMARY_CANARY"),
            )
        except reconciler.Fail as exc:
            require(
                str(exc) == "promotion review reconcile transaction failed (Fail); rollback incomplete"
                and exc.__suppress_context__
                and "PRIVATE_PROMOTION_RECONCILE_PRIMARY_CANARY" not in str(exc)
                and "PRIVATE_PROMOTION_RECONCILE_ROLLBACK_CANARY" not in str(exc),
                "rollback aggregation rejected at wrong/private boundary",
            )
        else:
            raise Fail("synthetic first rollback restore failure unexpectedly accepted")
        require(attempts == [first, second], f"rollback did not attempt every promotion authority: {attempts}")
    finally:
        reconciler.write_text = original_write_text
        reconciler.repo_relative = original_repo_relative
    print("PASS rollback: failure restoring first promotion authority does not skip later authority restore attempts")


def prove_writer_close_failure_releases_lock() -> None:
    writer = load_module(WRITER, "memory_os_promotion_review_writer_lock_negative")
    original_lock = writer.LOCK
    original_require_cli_authorities = writer.require_cli_authorities
    original_load = writer.load
    original_validate_record = writer.validate_record
    original_write = writer.os.write
    original_close = writer.os.close
    original_argv = sys.argv[:]

    with tempfile.TemporaryDirectory(prefix="memory-os-promotion-review-lock-") as tmp:
        lock = Path(tmp) / ".backup-restore-promotion-review.lock"
        input_path = Path(tempfile.gettempdir()) / "memory-os-promotion-review-lock-close-failure.json"
        writer.LOCK = lock
        writer.require_cli_authorities = lambda: None
        writer.load = lambda _: {"decisionId": "brpr_lock_cleanup_negative"}
        writer.validate_record = lambda *_args, **_kwargs: None

        def reject_body_write(*_args) -> int:
            raise RuntimeError("synthetic promotion review body failure")

        def close_then_fail(fd: int) -> None:
            original_close(fd)
            raise OSError("synthetic promotion review lock close failure")

        writer.os.write = reject_body_write
        writer.os.close = close_then_fail
        sys.argv = [str(WRITER), "--record", str(input_path)]
        try:
            try:
                writer.main()
            except OSError as exc:
                require("synthetic promotion review lock close failure" in str(exc), f"unexpected promotion close failure: {exc}")
            else:
                raise Fail("synthetic promotion review lock close failure unexpectedly accepted")
            require(not lock.exists(), "promotion review lock stranded after close failure")

            writer.os.close = original_close
            retry_fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(retry_fd)
            lock.unlink()
            require(not lock.exists(), "promotion review lock retry cleanup failed")
            print("PASS cleanup: close failure still unlinks promotion review lock and permits immediate reacquisition")
        finally:
            writer.LOCK = original_lock
            writer.require_cli_authorities = original_require_cli_authorities
            writer.load = original_load
            writer.validate_record = original_validate_record
            writer.os.write = original_write
            writer.os.close = original_close
            sys.argv = original_argv


def prove_aggregate_validator_rejection_rolls_back_transaction(
    reconciler: Any,
    original_contract: bytes,
    original_registry: bytes,
) -> None:
    canonical_contract_mode = CANONICAL_CONTRACT.stat().st_mode & 0o777
    canonical_registry_mode = CANONICAL_REGISTRY.stat().st_mode & 0o777
    with isolated_reconcile_authorities(reconciler):
        fixture_contract = reconciler.CONTRACT.read_bytes()
        fixture_registry = reconciler.REGISTRY.read_bytes()
        reconciler.CONTRACT.chmod(0o640)
        reconciler.REGISTRY.chmod(0o640)
        original_run_validator = reconciler.run_validator
        original_write_text = reconciler.write_text
        labels: list[str] = []
        injected_contract_write = False

        def fake_run_validator(path: Path, label: str) -> None:
            labels.append(label)
            if path == reconciler.OPERABILITY_VALIDATOR:
                raise reconciler.Fail("PRIVATE_PROMOTION_RECONCILE_VALIDATOR_CANARY")
            require(path == reconciler.VALIDATOR, f"unexpected validator path: {path}")

        def tracked_write_text(path: Path, text: str) -> None:
            nonlocal injected_contract_write
            if path == reconciler.CONTRACT and not injected_contract_write:
                injected_contract_write = True
                original_write_text(path, text + "\n")
                return
            original_write_text(path, text)

        reconciler.run_validator = fake_run_validator
        reconciler.write_text = tracked_write_text
        try:
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                require(str(exc) == "promotion review reconcile transaction failed (Fail); rollback completed"
                        and exc.__suppress_context__
                        and "PRIVATE_PROMOTION_RECONCILE_VALIDATOR_CANARY" not in str(exc),
                        "aggregate validator rejected at wrong/private boundary")
            else:
                raise Fail("aggregate operability rejection unexpectedly accepted")

            require(injected_contract_write, "transaction did not reach contract write before aggregate rejection")
            require(labels == ["promotion review validator", "aggregate operability validator"], f"unexpected validator order: {labels}")
            assert_fixture_unchanged(reconciler, fixture_contract, fixture_registry, "aggregate operability rejection", 0o640, 0o640)
        finally:
            reconciler.run_validator = original_run_validator
            reconciler.write_text = original_write_text
    assert_canonical_unchanged(original_contract, original_registry, "isolated aggregate operability rejection", canonical_contract_mode, canonical_registry_mode)
    print("PASS boundary: aggregate operability rejection rolls back isolated promotion authorities without mutating canonical state")


def prove_private_post_reconcile_transport(reconciler: Any) -> None:
    """Test the actual bounded, private post-reconcile subprocess boundary."""
    original_run = reconciler.subprocess.run
    marker = "PRIVATE_PROMOTION_RECONCILE_SUBPROCESS_CANARY"
    state: dict[str, Any] = {"returncode": 0, "error": None}
    calls: list[tuple[str, ...]] = []

    def fake_run(args, **kwargs):
        require(args in ([sys.executable, str(reconciler.VALIDATOR)],
                         [sys.executable, str(reconciler.OPERABILITY_VALIDATOR)]),
                "promotion reconcile subprocess command drift")
        require(kwargs.get("cwd") == reconciler.ROOT
                and kwargs.get("stdout") is subprocess.DEVNULL
                and kwargs.get("stderr") is subprocess.DEVNULL
                and kwargs.get("check") is False
                and kwargs.get("timeout") == 180
                and "text" not in kwargs,
                "promotion reconcile subprocess privacy/timeout drift")
        calls.append(tuple(args))
        if state["error"] is not None:
            raise state["error"]
        return subprocess.CompletedProcess(args, state["returncode"], stdout=marker, stderr=marker)

    reconciler.subprocess.run = fake_run
    try:
        reconciler.run_validator(reconciler.VALIDATOR, "promotion review validator")
        reconciler.run_validator(reconciler.OPERABILITY_VALIDATOR, "aggregate operability validator")
        cases = (
            ("nonzero", {"returncode": 1}, "post-reconcile promotion review validator failed without exposing subprocess output"),
            ("boolean", {"returncode": True}, "post-reconcile promotion review validator failed without exposing subprocess output"),
            ("timeout", {"error": subprocess.TimeoutExpired(["python"], 180, stderr=marker)},
             "post-reconcile promotion review validator unavailable"),
            ("unavailable", {"error": OSError(marker)}, "post-reconcile promotion review validator unavailable"),
        )
        for label, change, expected in cases:
            state.update({"returncode": 0, "error": None})
            state.update(change)
            try:
                reconciler.run_validator(reconciler.VALIDATOR, "promotion review validator")
            except reconciler.Fail as exc:
                require(str(exc) == expected and marker not in str(exc)
                        and (label not in ("timeout", "unavailable") or exc.__suppress_context__),
                        "promotion reconcile subprocess private failure drift")
            else:
                raise Fail("promotion reconcile subprocess unexpectedly accepted: " + label)
        try:
            reconciler.run_validator(reconciler.VALIDATOR, "aggregate operability validator")
        except reconciler.Fail as exc:
            require(str(exc) == "unreviewed promotion review post-reconcile validator",
                    "promotion reconcile validator label mismatch accepted")
        else:
            raise Fail("promotion reconcile validator label mismatch unexpectedly accepted")
        require(len(calls) == len(cases) + 2,
                "promotion reconcile subprocess case multiplicity drift")
    finally:
        reconciler.subprocess.run = original_run
    print("PASS: promotion reconcile post-validation transport private, bounded and source-pinned (5 negatives)")



def prove_strict_reconcile_json(reconciler: Any) -> None:
    """Exercise the actual reconciler authority reader against disposable nodes."""
    with isolated_reconcile_authorities(reconciler):
        path = reconciler.REGISTRY
        original = path.read_bytes()
        expected = json.loads(original)
        require(reconciler.load(path) == expected, "promotion reconcile JSON positive failed")
        marker = "PRIVATE_PROMOTION_RECONCILE_JSON_CANARY"
        cases = (
            ("duplicate", b'{"x":1,"x":2}', "promotion reconcile JSON duplicate key refused"),
            ("nested-duplicate", b'{"x":{"y":1,"y":2}}', "promotion reconcile JSON duplicate key refused"),
            ("nan", b'{"x":NaN}', "promotion reconcile JSON nonfinite number refused"),
            ("infinity", b'{"x":Infinity}', "promotion reconcile JSON nonfinite number refused"),
            ("float-overflow", b'{"x":1e309}', "promotion reconcile JSON nonfinite number refused"),
            ("huge-integer", b'{"x":' + b"9" * 129 + b'}', "promotion reconcile JSON integer too large"),
            ("invalid-utf8", b'{"x":"' + bytes([255]) + b'"}',
             "promotion reconcile authority invalid UTF-8"),
            ("malformed", b'{"x":', "promotion reconcile JSON unreadable or invalid"),
            ("nonobject", b'[1,2]', "promotion reconcile JSON root must be object"),
            ("oversized", b"x" * (reconciler.MAX_AUTHORITY_BYTES + 1),
             "promotion reconcile authority size limit exceeded"),
        )
        for label, payload, failure in cases:
            path.write_bytes(payload)
            try:
                reconciler.load(path)
            except reconciler.Fail as exc:
                require(str(exc) == failure and marker not in str(exc),
                        f"promotion reconcile JSON {label} wrong/private rejection")
            else:
                raise Fail(f"promotion reconcile JSON {label} unexpectedly accepted")
        path.unlink()
        with tempfile.TemporaryDirectory(prefix="promotion-reconcile-external-") as tmp:
            external = Path(tmp) / "private.json"
            external.write_text(marker, encoding="utf-8")
            path.symlink_to(external)
            try:
                reconciler.load(path)
            except reconciler.Fail as exc:
                require(str(exc) == "promotion reconcile authority path unsafe",
                        "promotion reconcile JSON symlink wrong rejection")
            else:
                raise Fail("promotion reconcile JSON symlink accepted")
            path.unlink()
            require(external.read_text(encoding="utf-8") == marker,
                    "promotion reconcile JSON external canary changed")
        path.mkdir()
        try:
            reconciler.load(path)
        except reconciler.Fail as exc:
            require(str(exc) == "promotion reconcile authority path unsafe",
                    "promotion reconcile JSON directory wrong rejection")
        else:
            raise Fail("promotion reconcile JSON directory accepted")
        path.rmdir()
        path.write_bytes(original)
        require(reconciler.load(path) == expected,
                "promotion reconcile JSON restored positive failed")
    print("PASS: actual promotion reconcile JSON reader positive and 12 fail-closed negatives")



def prove_private_atomic_write_path_guards(
    reconciler: Any, original_contract: bytes, original_registry: bytes,
) -> None:
    """Reject unreviewed and external targets without touching protected files."""
    canonical_contract_mode = CANONICAL_CONTRACT.stat().st_mode & 0o777
    canonical_registry_mode = CANONICAL_REGISTRY.stat().st_mode & 0o777
    with isolated_reconcile_authorities(reconciler):
        original = reconciler.REGISTRY.read_bytes()
        marker = "PRIVATE_PROMOTION_RECONCILE_WRITE_CANARY"
        with tempfile.TemporaryDirectory(prefix="promotion-reconcile-write-external-") as tmp:
            outside = Path(tmp) / "private.json"
            outside.write_text(marker, encoding="utf-8")
            alias = reconciler.ROOT / "promotion-write-alias.json"
            alias.symlink_to(outside)
            unreviewed = reconciler.ROOT / "unreviewed.json"
            unreviewed.write_text(marker, encoding="utf-8")
            directory = reconciler.ROOT / "unreviewed-directory"
            directory.mkdir()
            cases = (
                ("external", outside, "promotion reconcile write path unsafe"),
                ("symlink", alias, "promotion reconcile write path unsafe"),
                ("directory", directory, "promotion reconcile write path unsafe"),
                ("unreviewed", unreviewed, "promotion reconcile write target unreviewed"),
            )
            for label, path, expected in cases:
                try:
                    reconciler.write_text(path, "changed")
                except reconciler.Fail as exc:
                    require(str(exc) == expected and marker not in str(exc),
                            f"promotion reconcile write {label} wrong/private rejection")
                else:
                    raise Fail(f"promotion reconcile write {label} unexpectedly accepted")
            require(outside.read_text(encoding="utf-8") == marker
                    and unreviewed.read_text(encoding="utf-8") == marker,
                    "promotion reconcile write canary changed")
        try:
            reconciler.write_text(reconciler.REGISTRY, "x" * (reconciler.MAX_AUTHORITY_BYTES + 1))
        except reconciler.Fail as exc:
            require(str(exc) == "promotion reconcile write size limit exceeded",
                    "promotion reconcile write oversized input wrong rejection")
        else:
            raise Fail("promotion reconcile write oversized input accepted")
        require(reconciler.REGISTRY.read_bytes() == original,
                "promotion reconcile write negatives mutated isolated registry")
    assert_canonical_unchanged(original_contract, original_registry,
                               "promotion reconcile write path negatives",
                               canonical_contract_mode, canonical_registry_mode)
    print("PASS: promotion reconcile atomic write path and size guards (5 negatives)")


def main() -> int:
    reconciler = load_module(RECONCILER, "memory_os_promotion_review_reconcile_negative")
    original_contract = CANONICAL_CONTRACT.read_bytes()
    original_registry = CANONICAL_REGISTRY.read_bytes()
    validate_atomic_diagnostic_publication()
    prove_strict_reconcile_json(reconciler)
    prove_private_post_reconcile_transport(reconciler)

    expect_authority_substitution_rejected(reconciler, "CONTRACT", reconciler.REGISTRY, "promotion review contract substitution", "promotion review contract authority drift", original_contract, original_registry)
    expect_authority_substitution_rejected(reconciler, "REGISTRY", reconciler.GEN_REGISTRY, "promotion review registry substitution", "promotion review registry authority drift", original_contract, original_registry)
    expect_authority_substitution_rejected(reconciler, "GEN_REGISTRY", reconciler.REGISTRY, "generation evidence registry substitution", "generation evidence registry authority drift", original_contract, original_registry)
    expect_authority_substitution_rejected(reconciler, "WRITER", reconciler.VALIDATOR, "promotion review writer executable substitution", "promotion review writer authority drift", original_contract, original_registry)
    expect_authority_substitution_rejected(reconciler, "VALIDATOR", reconciler.OPERABILITY_VALIDATOR, "promotion review validator executable substitution", "promotion review validator authority drift", original_contract, original_registry)
    expect_authority_substitution_rejected(reconciler, "OPERABILITY_VALIDATOR", reconciler.VALIDATOR, "operability validator executable substitution", "operability validator authority drift", original_contract, original_registry)
    expect_authority_substitution_rejected(reconciler, "STATUS", reconciler.CONTRACT, "production operability status substitution", "production operability status authority drift", original_contract, original_registry)

    prove_mode_preserving_atomic_write(reconciler, original_contract, original_registry)
    prove_private_atomic_write_path_guards(reconciler, original_contract, original_registry)
    prove_atomic_write_failure(reconciler, original_contract, original_registry)
    prove_second_replace_failure_rolls_back_transaction(reconciler, original_contract, original_registry)
    prove_rollback_attempts_all_authorities(reconciler)
    prove_writer_close_failure_releases_lock()
    prove_aggregate_validator_rejection_rolls_back_transaction(reconciler, original_contract, original_registry)

    print("Memory OS backup/restore promotion review reconcile negative PASS")
    print("promotion contract substitution accepted: false")
    print("promotion registry substitution accepted: false")
    print("generation evidence registry substitution accepted: false")
    print("promotion writer executable substitution accepted: false")
    print("promotion validator executable substitution accepted: false")
    print("operability validator executable substitution accepted: false")
    print("production operability status substitution accepted: false")
    print("successful atomic promotion-review authority mode drift accepted: false")
    print("failed atomic promotion-review authority mode drift accepted: false")
    print("second promotion-review replace transaction rollback verified: true")
    print("rollback attempts every promotion authority after an earlier restore failure: true")
    print("promotion review lock close-failure cleanup verified: true")
    print("non-atomic promotion-review authority write accepted: false")
    print("non-atomic or mode-drifting promotion-review diagnostic write accepted: false")
    print("promotion validator ran before aggregate operability validator: true")
    print("aggregate operability rejection rolled back isolated promotion registry/contract bytes and modes: true")
    print("canonical promotion registry/contract mutated by transaction negatives: false")
    print("automatic human promotion authorization created: false")
    print("production evidence created: false")
    print("production traffic changed: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE PROMOTION REVIEW RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
