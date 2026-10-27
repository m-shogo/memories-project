#!/usr/bin/env python3
"""Prove recovery-objective reconciliation authority identity, ordering and transactional rollback."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Callable, Iterator

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-recovery-objectives.py"
WORKFLOW = ROOT / ".github/workflows/recovery-objectives-admission.yml"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CONTRACT = ROOT / "contracts/operations/recovery-objectives-admission-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_recovery_objectives_reconcile_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load recovery objective reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_domain_fail(name: str, action: Callable[[], object], fail_type: type[BaseException], expected: str | None = None) -> None:
    try:
        action()
    except fail_type as exc:
        if expected is not None:
            require(expected in str(exc), f"{name} rejected at wrong boundary: {exc}")
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def file_mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def assert_canonical_unchanged(
    contract_bytes: bytes,
    status_bytes: bytes,
    label: str,
    contract_mode: int | None = None,
    status_mode: int | None = None,
) -> None:
    require(CONTRACT.read_bytes() == contract_bytes, f"{label} changed canonical recovery objective contract")
    require(STATUS.read_bytes() == status_bytes, f"{label} changed canonical production status")
    if contract_mode is not None:
        require(file_mode(CONTRACT) == contract_mode, f"{label} changed canonical recovery objective contract mode")
    if status_mode is not None:
        require(file_mode(STATUS) == status_mode, f"{label} changed canonical production status mode")


@contextmanager
def isolated_authorities(reconciler: object) -> Iterator[None]:
    relative_paths = (
        reconciler.CONTRACT_REL,
        reconciler.REGISTRY_REL,
        reconciler.WRITER_REL,
        reconciler.VALIDATOR_REL,
        reconciler.OPERABILITY_VALIDATOR_REL,
        reconciler.STATUS_REL,
        Path("scripts/reconcile-memory-os-recovery-objectives.py"),
        Path(".github/workflows/recovery-objectives-admission.yml"),
    )
    originals = {
        name: getattr(reconciler, name)
        for name in ("ROOT", "CONTRACT", "REGISTRY", "WRITER", "VALIDATOR", "OPERABILITY_VALIDATOR", "STATUS")
    }
    with tempfile.TemporaryDirectory(prefix=".tmp-recovery-objective-authorities-", dir=TMP_PARENT) as tmpdir:
        fixture_root = Path(tmpdir)
        for relative in relative_paths:
            source = ROOT / relative
            destination = fixture_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        reconciler.ROOT = fixture_root
        reconciler.CONTRACT = fixture_root / reconciler.CONTRACT_REL
        reconciler.REGISTRY = fixture_root / reconciler.REGISTRY_REL
        reconciler.WRITER = fixture_root / reconciler.WRITER_REL
        reconciler.VALIDATOR = fixture_root / reconciler.VALIDATOR_REL
        reconciler.OPERABILITY_VALIDATOR = fixture_root / reconciler.OPERABILITY_VALIDATOR_REL
        reconciler.STATUS = fixture_root / reconciler.STATUS_REL

        contract_bytes = reconciler.CONTRACT.read_bytes()
        status_bytes = reconciler.STATUS.read_bytes()
        contract_mode = file_mode(reconciler.CONTRACT)
        status_mode = file_mode(reconciler.STATUS)
        try:
            yield
            require(reconciler.CONTRACT.read_bytes() == contract_bytes, "fixture recovery objective contract did not roll back byte-for-byte")
            require(reconciler.STATUS.read_bytes() == status_bytes, "fixture production status did not roll back byte-for-byte")
            require(file_mode(reconciler.CONTRACT) == contract_mode, "fixture recovery objective contract mode did not roll back")
            require(file_mode(reconciler.STATUS) == status_mode, "fixture production status mode did not roll back")
            leftovers = list(reconciler.CONTRACT.parent.glob(".*.tmp"))
            require(not leftovers, f"fixture recovery objective transaction left temporary files: {leftovers}")
        finally:
            for name, value in originals.items():
                setattr(reconciler, name, value)


def validate_atomic_diagnostic_publication() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    required_fragments = (
        "tempfile.mkstemp(",
        "dir=path.parent",
        "existing_mode = path.stat().st_mode & 0o7777 if path.exists() else None",
        "os.fchmod(fd, existing_mode)",
        "handle.flush()",
        "os.fsync(handle.fileno())",
        "os.replace(tmp_name, path)",
        "os.unlink(tmp_name)",
    )
    missing = [fragment for fragment in required_fragments if fragment not in text]
    require(not missing, f"recovery objective diagnostic publication is not crash-safe or mode-preserving: missing {missing}")
    require(
        "path.write_text(json.dumps(value" not in text,
        "recovery objective diagnostic publication regressed to direct write_text",
    )
    print("PASS boundary: recovery objective failure diagnostic publication is crash-safe and mode-preserving")


def prove_atomic_write_mode_preservation(reconciler: object) -> None:
    with tempfile.TemporaryDirectory(prefix=".tmp-objective-mode-", dir=TMP_PARENT) as tmpdir:
        path = Path(tmpdir) / "authority.json"
        path.write_text('{"before":true}\n', encoding="utf-8")
        os.chmod(path, 0o640)
        reconciler.write_text(path, '{"after":true}\n')
        require(path.read_text(encoding="utf-8") == '{"after":true}\n', "objective mode-preservation fixture payload drift")
        require(file_mode(path) == 0o640, "atomic recovery objective authority replace changed existing file mode")
        leftovers = list(path.parent.glob(f".{path.name}.*.tmp"))
        require(not leftovers, "mode-preserving recovery objective write left temporary files")
    print("PASS boundary: atomic recovery objective authority replace preserves existing file mode")


def prove_atomic_write_failure(reconciler: object) -> None:
    contract_bytes = reconciler.CONTRACT.read_bytes()
    original_replace = reconciler.os.replace

    def reject_replace(source: str | Path, destination: str | Path) -> None:
        raise OSError("synthetic atomic replace rejection")

    reconciler.os.replace = reject_replace
    try:
        expect_domain_fail(
            "recovery objective atomic replace rejection",
            lambda: reconciler.write_text(reconciler.CONTRACT, contract_bytes.decode("utf-8") + " "),
            reconciler.Fail,
            "cannot atomically write",
        )
    finally:
        reconciler.os.replace = original_replace

    require(reconciler.CONTRACT.read_bytes() == contract_bytes, "atomic replace rejection changed fixture contract")
    contract_leftovers = list(reconciler.CONTRACT.parent.glob(f".{reconciler.CONTRACT.name}.*.tmp"))
    status_leftovers = list(reconciler.STATUS.parent.glob(f".{reconciler.STATUS.name}.*.tmp"))
    require(not contract_leftovers and not status_leftovers, "atomic write rejection left temporary recovery objective authority files")
    print("PASS boundary: failed atomic recovery objective write preserves fixture bytes/mode and cleans temporary files")


def prove_rollback_attempts_all_restores(reconciler: object) -> None:
    originals = {
        CONTRACT: "contract\n",
        STATUS: "status\n",
    }
    observed: list[Path] = []
    original_write = reconciler.write_text

    def reject_first_restore(path: Path, text: str) -> None:
        observed.append(path)
        if len(observed) == 1:
            raise reconciler.Fail("PRIVATE_OBJECTIVE_ROLLBACK_RESTORE_CANARY")

    reconciler.write_text = reject_first_restore
    try:
        expect_domain_fail(
            "first recovery objective rollback restore rejection",
            lambda: reconciler.restore_original_text(originals),
            reconciler.Fail,
            "recovery objective rollback incomplete",
        )
    finally:
        reconciler.write_text = original_write

    require(observed == [CONTRACT, STATUS], f"objective rollback restore failure skipped later authority: {observed}")
    print("PASS rollback: recovery objective restore failure still attempts contract and status")


def prove_primary_and_rollback_failures_are_preserved(reconciler: object) -> None:
    original_run_validator = reconciler.run_validator
    original_restore = reconciler.restore_original_text

    def fail_primary(path: Path, label: str) -> None:
        raise reconciler.Fail("PRIVATE_OBJECTIVE_PRIMARY_CANARY")

    def fail_rollback(original_text: dict[Path, str]) -> None:
        raise reconciler.Fail("PRIVATE_OBJECTIVE_ROLLBACK_CANARY")

    reconciler.run_validator = fail_primary
    reconciler.restore_original_text = fail_rollback
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            text = str(exc)
            require(
                text == "recovery objective reconcile transaction failed (Fail); rollback incomplete"
                and exc.__suppress_context__
                and "PRIVATE_OBJECTIVE_PRIMARY_CANARY" not in text
                and "PRIVATE_OBJECTIVE_ROLLBACK_CANARY" not in text,
                "recovery objective primary/rollback diagnostic wrong or private",
            )
        else:
            raise Fail("synthetic recovery objective primary+rollback failure unexpectedly accepted")
    finally:
        reconciler.run_validator = original_run_validator
        reconciler.restore_original_text = original_restore
    print("PASS rollback: recovery objective reconcile primary/rollback diagnostics private and incomplete marker preserved")


def prove_second_replace_transaction_rollback(reconciler: object) -> None:
    original_replace = reconciler.os.replace
    replace_destinations: list[Path] = []

    def fail_second_replace(source: str | Path, destination: str | Path) -> None:
        replace_destinations.append(Path(destination))
        if len(replace_destinations) == 2:
            raise OSError("synthetic second authority replace rejection")
        original_replace(source, destination)

    reconciler.os.replace = fail_second_replace
    try:
        expect_domain_fail(
            "recovery objective second authority replace rejection",
            reconciler.main,
            reconciler.Fail,
            "recovery objective reconcile transaction failed (Fail); rollback completed",
        )
    finally:
        reconciler.os.replace = original_replace

    require(
        replace_destinations == [reconciler.CONTRACT, reconciler.STATUS, reconciler.CONTRACT, reconciler.STATUS],
        f"recovery objective second-replace rollback order drift: {replace_destinations}",
    )
    contract_leftovers = list(reconciler.CONTRACT.parent.glob(f".{reconciler.CONTRACT.name}.*.tmp"))
    status_leftovers = list(reconciler.STATUS.parent.glob(f".{reconciler.STATUS.name}.*.tmp"))
    require(
        not contract_leftovers and not status_leftovers,
        "second authority replace rejection left temporary recovery objective authority files",
    )
    print("PASS rollback: second authority replace rejection restores fixture contract/status byte-for-byte and mode-for-mode")


def prove_aggregate_validator_rollback(reconciler: object) -> None:
    original_run_validator = reconciler.run_validator
    validator_calls: list[tuple[Path, str]] = []

    def fail_aggregate_validator(path: Path, label: str) -> None:
        validator_calls.append((path, label))
        if path == reconciler.OPERABILITY_VALIDATOR:
            raise reconciler.Fail("post-reconcile aggregate operability validator failed: forced negative")
        return None

    reconciler.run_validator = fail_aggregate_validator
    try:
        expect_domain_fail(
            "post-write aggregate operability rejection",
            reconciler.main,
            reconciler.Fail,
            "recovery objective reconcile transaction failed (Fail); rollback completed",
        )
    finally:
        reconciler.run_validator = original_run_validator

    require(
        validator_calls
        == [
            (reconciler.VALIDATOR, "recovery objective validator"),
            (reconciler.OPERABILITY_VALIDATOR, "aggregate operability validator"),
        ],
        f"recovery objective post-write validator order drift: {validator_calls}",
    )
    print("PASS rollback: aggregate operability rejection restores fixture recovery objective contract/status byte-for-byte and mode-for-mode")
    print("PASS boundary: post-write validator order is recovery objective then aggregate Operability")



def prove_private_writer_import(reconciler: object) -> None:
    """The actual canonical import must hide synthetic output and error details."""
    actual = reconciler.load_writer()
    require(Path(actual.__file__).resolve() == reconciler.WRITER.resolve(),
            "recovery objective writer import positive identity drift")
    original_spec = reconciler.importlib.util.spec_from_file_location
    spec = original_spec("memory_os_objective_reconcile_import_negative", reconciler.WRITER)
    require(spec is not None and spec.loader is not None,
            "recovery objective writer import negative spec missing")
    marker = "PRIVATE_RECOVERY_OBJECTIVE_RECONCILE_IMPORT_CANARY"

    class FailingLoader:
        def create_module(self, _spec):
            return None

        def exec_module(self, _module):
            print(marker)
            print(marker, file=sys.stderr)
            raise OSError(marker)

    spec.loader = FailingLoader()
    reconciler.importlib.util.spec_from_file_location = lambda *_args, **_kwargs: spec
    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                reconciler.load_writer()
            except reconciler.Fail as exc:
                require(str(exc) == "recovery objective canonical writer import failed"
                        and exc.__suppress_context__ and marker not in str(exc),
                        "recovery objective writer import private failure drift")
            else:
                raise Fail("recovery objective writer import failure accepted")
    finally:
        reconciler.importlib.util.spec_from_file_location = original_spec
    require(not stdout.getvalue() and not stderr.getvalue(),
            "recovery objective writer import leaked Python-level output")
    print("PASS: recovery objective writer import output and errors private")


def prove_private_post_reconcile_transport(reconciler: object) -> None:
    """Exercise the actual subprocess boundary with private synthetic canaries."""
    original_run = reconciler.subprocess.run
    marker = "PRIVATE_RECOVERY_OBJECTIVE_RECONCILE_SUBPROCESS_CANARY"
    state: dict[str, object] = {"returncode": 0, "error": None}
    calls: list[tuple[str, ...]] = []

    def fake_run(args, **kwargs):
        require(args in ([sys.executable, str(reconciler.VALIDATOR)],
                         [sys.executable, str(reconciler.OPERABILITY_VALIDATOR)]),
                "recovery objective reconcile subprocess command drift")
        require(kwargs.get("cwd") == reconciler.ROOT
                and kwargs.get("stdout") is subprocess.DEVNULL
                and kwargs.get("stderr") is subprocess.DEVNULL
                and kwargs.get("check") is False
                and kwargs.get("timeout") == 180
                and "text" not in kwargs,
                "recovery objective reconcile subprocess privacy/timeout drift")
        calls.append(tuple(args))
        if state["error"] is not None:
            raise state["error"]
        return subprocess.CompletedProcess(args, state["returncode"],
                                           stdout=marker, stderr=marker)

    reconciler.subprocess.run = fake_run
    try:
        reconciler.run_validator(reconciler.VALIDATOR, "recovery objective validator")
        reconciler.run_validator(reconciler.OPERABILITY_VALIDATOR, "aggregate operability validator")
        cases = (
            ("nonzero", {"returncode": 1},
             "post-reconcile recovery objective validator failed without exposing subprocess output"),
            ("boolean", {"returncode": True},
             "post-reconcile recovery objective validator failed without exposing subprocess output"),
            ("timeout", {"error": subprocess.TimeoutExpired(["python"], 180, stderr=marker)},
             "post-reconcile recovery objective validator unavailable"),
            ("unavailable", {"error": OSError(marker)},
             "post-reconcile recovery objective validator unavailable"),
        )
        for label, change, expected in cases:
            state.update({"returncode": 0, "error": None})
            state.update(change)
            try:
                reconciler.run_validator(reconciler.VALIDATOR, "recovery objective validator")
            except reconciler.Fail as exc:
                require(str(exc) == expected and marker not in str(exc)
                        and (label not in ("timeout", "unavailable") or exc.__suppress_context__),
                        f"recovery objective reconcile {label} private failure drift")
            else:
                raise Fail(f"recovery objective reconcile {label} unexpectedly accepted")
        try:
            reconciler.run_validator(reconciler.VALIDATOR, "aggregate operability validator")
        except reconciler.Fail as exc:
            require(str(exc) == "unreviewed recovery objective post-reconcile validator",
                    "recovery objective reconcile label mismatch accepted")
        else:
            raise Fail("recovery objective reconcile label mismatch unexpectedly accepted")
        require(len(calls) == len(cases) + 2,
                "recovery objective reconcile subprocess multiplicity drift")
    finally:
        reconciler.subprocess.run = original_run
    print("PASS: recovery objective reconcile post-validation transport private, bounded and source-pinned (5 negatives)")



def prove_strict_objective_json(reconciler: object) -> None:
    """Exercise the actual objective reconciler reader in disposable fixtures."""
    with isolated_authorities(reconciler):
        path = reconciler.REGISTRY
        original = path.read_bytes()
        expected = json.loads(original)
        require(reconciler.load(path) == expected, "objective reconcile JSON positive failed")
        marker = "PRIVATE_OBJECTIVE_RECONCILE_JSON_CANARY"
        cases = (
            ("duplicate", b'{"x":1,"x":2}', "recovery objective reconcile JSON duplicate key refused"),
            ("nested-duplicate", b'{"x":{"y":1,"y":2}}',
             "recovery objective reconcile JSON duplicate key refused"),
            ("nan", b'{"x":NaN}', "recovery objective reconcile JSON nonfinite number refused"),
            ("infinity", b'{"x":Infinity}', "recovery objective reconcile JSON nonfinite number refused"),
            ("float-overflow", b'{"x":1e309}', "recovery objective reconcile JSON nonfinite number refused"),
            ("huge-integer", b'{"x":' + b"9" * 129 + b'}',
             "recovery objective reconcile JSON integer too large"),
            ("invalid-utf8", b'{"x":"' + bytes([255]) + b'"}',
             "recovery objective reconcile authority invalid UTF-8"),
            ("malformed", b'{"x":', "recovery objective reconcile JSON unreadable or invalid"),
            ("nonobject", b'[1,2]', "recovery objective reconcile JSON root must be object"),
            ("oversized", b"x" * (reconciler.MAX_AUTHORITY_BYTES + 1),
             "recovery objective reconcile authority size limit exceeded"),
        )
        for label, payload, failure in cases:
            path.write_bytes(payload)
            try:
                reconciler.load(path)
            except reconciler.Fail as exc:
                require(str(exc) == failure and marker not in str(exc),
                        f"objective reconcile JSON {label} wrong/private rejection")
            else:
                raise Fail(f"objective reconcile JSON {label} unexpectedly accepted")
        path.unlink()
        with tempfile.TemporaryDirectory(prefix="objective-reconcile-external-") as tmp:
            external = Path(tmp) / "private.json"
            external.write_text(marker, encoding="utf-8")
            path.symlink_to(external)
            try:
                reconciler.load(path)
            except reconciler.Fail as exc:
                require(str(exc) == "recovery objective reconcile authority path unsafe",
                        "objective reconcile JSON symlink wrong rejection")
            else:
                raise Fail("objective reconcile JSON symlink accepted")
            path.unlink()
            require(external.read_text(encoding="utf-8") == marker,
                    "objective reconcile JSON external canary changed")
        path.mkdir()
        try:
            reconciler.load(path)
        except reconciler.Fail as exc:
            require(str(exc) == "recovery objective reconcile authority path unsafe",
                    "objective reconcile JSON directory wrong rejection")
        else:
            raise Fail("objective reconcile JSON directory accepted")
        path.rmdir()
        path.write_bytes(original)
        require(reconciler.load(path) == expected,
                "objective reconcile JSON restored positive failed")
    print("PASS: actual recovery objective reconcile JSON reader positive and 12 fail-closed negatives")


def main() -> int:
    require(RECONCILER.is_file(), "recovery objective reconciler missing")
    require(WORKFLOW.is_file(), "recovery objective workflow missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    reconciler = load_reconciler()

    canonical_contract = CONTRACT.read_bytes()
    canonical_status = STATUS.read_bytes()
    canonical_contract_mode = file_mode(CONTRACT)
    canonical_status_mode = file_mode(STATUS)
    validate_atomic_diagnostic_publication()

    substitutions = (
        ("CONTRACT", reconciler.REGISTRY, "recovery objective contract authority drift"),
        ("REGISTRY", reconciler.CONTRACT, "recovery objective registry authority drift"),
        ("WRITER", reconciler.VALIDATOR, "recovery objective writer authority drift"),
        ("VALIDATOR", reconciler.OPERABILITY_VALIDATOR, "recovery objective validator authority drift"),
        ("OPERABILITY_VALIDATOR", reconciler.VALIDATOR, "operability validator authority drift"),
        ("STATUS", reconciler.CONTRACT, "production operability status authority drift"),
    )
    for attribute, replacement, expected in substitutions:
        original = getattr(reconciler, attribute)
        setattr(reconciler, attribute, replacement)
        try:
            expect_domain_fail(f"{attribute.lower()} substitution", reconciler.main, reconciler.Fail, expected)
            assert_canonical_unchanged(
                canonical_contract,
                canonical_status,
                attribute.lower(),
                canonical_contract_mode,
                canonical_status_mode,
            )
        finally:
            setattr(reconciler, attribute, original)

    original_contract_path = reconciler.CONTRACT
    original_status_path = reconciler.STATUS
    reconciler.CONTRACT = reconciler.REGISTRY
    reconciler.STATUS = reconciler.REGISTRY
    try:
        expect_domain_fail(
            "paired contract/status fixture substitution",
            reconciler.main,
            reconciler.Fail,
            "recovery objective contract authority drift",
        )
        assert_canonical_unchanged(
            canonical_contract,
            canonical_status,
            "paired fixture substitution",
            canonical_contract_mode,
            canonical_status_mode,
        )
    finally:
        reconciler.CONTRACT = original_contract_path
        reconciler.STATUS = original_status_path

    prefix = reconciler.EVIDENCE_PREFIX
    old = prefix + " old"
    new = prefix + " new"
    values = ["before", old, "after"]
    reconciler.replace_single_prefixed(values, prefix, new)
    require(values == ["before", new, "after"], "recovery objective evidence moved during replacement")
    values = [old, prefix + " duplicate"]
    expect_domain_fail(
        "duplicate recovery objective status evidence",
        lambda: reconciler.replace_single_prefixed(values, prefix, new),
        reconciler.Fail,
        "duplicate authority evidence prefix",
    )
    require(values == [old, prefix + " duplicate"], "duplicate evidence rejection mutated status ordering")
    print("PASS preserve: recovery objective evidence ordering is deterministic")

    with tempfile.TemporaryDirectory(prefix=".tmp-recovery-objective-reconcile-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_domain_fail("invalid UTF-8 objective authority", lambda: reconciler.load(invalid_utf8), reconciler.Fail)

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_domain_fail("unreadable objective authority directory", lambda: reconciler.load(directory_authority), reconciler.Fail)

        with tempfile.TemporaryDirectory(prefix="memory-os-objective-outside-") as outside_dir:
            outside = Path(outside_dir) / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            expect_domain_fail("objective authority escapes repository", lambda: reconciler.load(outside), reconciler.Fail)

    prove_strict_objective_json(reconciler)
    prove_private_writer_import(reconciler)
    prove_private_post_reconcile_transport(reconciler)
    prove_atomic_write_mode_preservation(reconciler)
    with isolated_authorities(reconciler):
        prove_atomic_write_failure(reconciler)
    prove_rollback_attempts_all_restores(reconciler)
    with isolated_authorities(reconciler):
        prove_primary_and_rollback_failures_are_preserved(reconciler)
    with isolated_authorities(reconciler):
        prove_second_replace_transaction_rollback(reconciler)
    with isolated_authorities(reconciler):
        prove_aggregate_validator_rollback(reconciler)

    assert_canonical_unchanged(
        canonical_contract,
        canonical_status,
        "isolated transactional negatives",
        canonical_contract_mode,
        canonical_status_mode,
    )
    print("PASS boundary: transactional recovery objective negatives keep canonical authorities read-only")
    print("paired recovery objective fixture substitution accepted: false")
    print("recovery objective data/executable substitution accepted: false")
    print("recovery objective evidence reordering accepted: false")
    print("non-atomic recovery objective authority write accepted: false")
    print("recovery objective authority mode drift accepted: false")
    print("non-atomic recovery objective diagnostic write accepted: false")
    print("Recovery objective reconcile negative suite PASS")
    print("objective created or defaulted: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RECOVERY OBJECTIVE RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
