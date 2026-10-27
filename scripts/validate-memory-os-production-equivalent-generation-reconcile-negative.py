#!/usr/bin/env python3
"""Prove environment-generation reconciliation authority identity, ordering and rollback."""

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
from typing import Any, Callable, Iterator

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-production-equivalent-generation-status.py"
WORKFLOW = ROOT / ".github/workflows/production-equivalent-environment-generation.yml"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_reconcile_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load environment generation reconciler")
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
    registry_bytes: bytes,
    status_bytes: bytes,
    label: str,
    contract_mode: int | None = None,
    status_mode: int | None = None,
) -> None:
    require(CONTRACT.read_bytes() == contract_bytes, f"{label} changed canonical generation contract")
    require(REGISTRY.read_bytes() == registry_bytes, f"{label} changed canonical generation registry")
    require(STATUS.read_bytes() == status_bytes, f"{label} changed canonical production status")
    if contract_mode is not None:
        require(file_mode(CONTRACT) == contract_mode, f"{label} changed canonical generation contract mode")
    if status_mode is not None:
        require(file_mode(STATUS) == status_mode, f"{label} changed canonical production status mode")


@contextmanager
def isolated_authorities(reconciler: object) -> Iterator[None]:
    original_names = (
        "ROOT",
        "CONTRACT",
        "REGISTRY",
        "GEN_SCHEMA",
        "ENV_VALIDATOR",
        "WRITER",
        "VALIDATOR",
        "OPERABILITY_VALIDATOR",
        "NEGATIVE",
        "STATUS",
    )
    originals = {name: getattr(reconciler, name) for name in original_names}
    relative_paths = set(Path(ref) for ref in reconciler.REFS)
    relative_paths.add(reconciler.OPERABILITY_VALIDATOR_REL)
    relative_paths.add(reconciler.STATUS_REL)

    with tempfile.TemporaryDirectory(prefix=".tmp-environment-generation-authorities-", dir=TMP_PARENT) as tmpdir:
        fixture_root = Path(tmpdir)
        for relative in sorted(relative_paths, key=lambda value: value.as_posix()):
            source = ROOT / relative
            destination = fixture_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        reconciler.ROOT = fixture_root
        for name, relative_name in (
            ("CONTRACT", "CONTRACT_REL"),
            ("REGISTRY", "REGISTRY_REL"),
            ("GEN_SCHEMA", "GEN_SCHEMA_REL"),
            ("ENV_VALIDATOR", "ENV_VALIDATOR_REL"),
            ("WRITER", "WRITER_REL"),
            ("VALIDATOR", "VALIDATOR_REL"),
            ("OPERABILITY_VALIDATOR", "OPERABILITY_VALIDATOR_REL"),
            ("NEGATIVE", "NEGATIVE_REL"),
            ("STATUS", "STATUS_REL"),
        ):
            setattr(reconciler, name, fixture_root / getattr(reconciler, relative_name))

        contract_bytes = reconciler.CONTRACT.read_bytes()
        registry_bytes = reconciler.REGISTRY.read_bytes()
        status_bytes = reconciler.STATUS.read_bytes()
        contract_mode = file_mode(reconciler.CONTRACT)
        registry_mode = file_mode(reconciler.REGISTRY)
        status_mode = file_mode(reconciler.STATUS)
        try:
            yield
            require(reconciler.CONTRACT.read_bytes() == contract_bytes, "fixture generation contract did not roll back byte-for-byte")
            require(reconciler.REGISTRY.read_bytes() == registry_bytes, "fixture generation registry changed unexpectedly")
            require(reconciler.STATUS.read_bytes() == status_bytes, "fixture production status did not roll back byte-for-byte")
            require(file_mode(reconciler.CONTRACT) == contract_mode, "fixture generation contract mode did not roll back")
            require(file_mode(reconciler.REGISTRY) == registry_mode, "fixture generation registry mode changed unexpectedly")
            require(file_mode(reconciler.STATUS) == status_mode, "fixture production status mode did not roll back")
            leftovers = list(reconciler.CONTRACT.parent.glob(".*.tmp"))
            require(not leftovers, f"fixture generation transaction left temporary files: {leftovers}")
        finally:
            for name, value in originals.items():
                setattr(reconciler, name, value)


def validate_atomic_diagnostic_publication() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    required_fragments = (
        "tempfile.mkstemp(",
        "dir=path.parent",
        "mode = path.stat().st_mode & 0o7777 if path.exists() else None",
        "os.fchmod(fd, mode)",
        "handle.flush()",
        "os.fsync(handle.fileno())",
        "os.replace(tmp_name, path)",
        "os.unlink(tmp_name)",
    )
    missing = [fragment for fragment in required_fragments if fragment not in text]
    require(not missing, f"environment generation diagnostic publication is not crash-safe or mode-preserving: missing {missing}")
    require(
        "path.write_text(json.dumps(value" not in text,
        "environment generation diagnostic publication regressed to direct write_text",
    )
    print("PASS boundary: environment generation failure diagnostic publication is crash-safe and mode-preserving")


def prove_atomic_write_mode_preservation(reconciler: object) -> None:
    with tempfile.TemporaryDirectory(prefix=".tmp-generation-mode-", dir=TMP_PARENT) as tmpdir:
        path = Path(tmpdir) / "authority.json"
        path.write_text('{"before":true}\n', encoding="utf-8")
        os.chmod(path, 0o640)
        reconciler.write_text(path, '{"after":true}\n')
        require(path.read_text(encoding="utf-8") == '{"after":true}\n', "mode-preservation fixture payload drift")
        require(file_mode(path) == 0o640, "atomic generation authority replace changed existing file mode")
        leftovers = list(path.parent.glob(f".{path.name}.*.tmp"))
        require(not leftovers, "mode-preserving generation authority write left temporary files")
    print("PASS boundary: atomic environment-generation authority replace preserves existing file mode")


def prove_atomic_write_failure(reconciler: object) -> None:
    contract_bytes = reconciler.CONTRACT.read_bytes()
    original_replace = reconciler.os.replace

    def reject_replace(source: str | Path, destination: str | Path) -> None:
        raise OSError("synthetic atomic replace rejection")

    reconciler.os.replace = reject_replace
    try:
        expect_domain_fail(
            "environment generation atomic replace rejection",
            lambda: reconciler.write_text(reconciler.CONTRACT, contract_bytes.decode("utf-8") + " "),
            reconciler.Fail,
            "cannot atomically write",
        )
    finally:
        reconciler.os.replace = original_replace

    require(reconciler.CONTRACT.read_bytes() == contract_bytes, "atomic replace rejection changed fixture generation contract")
    contract_leftovers = list(reconciler.CONTRACT.parent.glob(f".{reconciler.CONTRACT.name}.*.tmp"))
    status_leftovers = list(reconciler.STATUS.parent.glob(f".{reconciler.STATUS.name}.*.tmp"))
    require(not contract_leftovers and not status_leftovers, "atomic write rejection left temporary generation authority files")
    print("PASS boundary: failed atomic environment-generation write preserves fixture bytes/mode and cleans temporary files")


def prove_second_authority_replace_rollback(reconciler: object) -> None:
    original_replace = reconciler.os.replace
    replace_count = 0

    def reject_second_replace(source: str | Path, destination: str | Path) -> None:
        nonlocal replace_count
        replace_count += 1
        if replace_count == 2:
            raise OSError("synthetic second-authority replace rejection")
        original_replace(source, destination)

    reconciler.os.replace = reject_second_replace
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require(str(exc) == "environment generation status reconcile failed; rollback completed"
                    and exc.__suppress_context__
                    and "synthetic" not in str(exc),
                    "second-authority rollback completed class or privacy drift")
        else:
            raise Fail("second-authority replace rejection unexpectedly accepted")
    finally:
        reconciler.os.replace = original_replace

    require(replace_count == 4, f"second-authority failure did not execute full two-authority rollback: replace_count={replace_count}")
    contract_leftovers = list(reconciler.CONTRACT.parent.glob(f".{reconciler.CONTRACT.name}.*.tmp"))
    status_leftovers = list(reconciler.STATUS.parent.glob(f".{reconciler.STATUS.name}.*.tmp"))
    require(
        not contract_leftovers and not status_leftovers,
        "second-authority replace rollback left temporary generation authority files",
    )
    print("PASS rollback: second-authority replace failure restores fixture authorities byte-for-byte and mode-for-mode")


def prove_rollback_restore_failure_attempts_all(reconciler: object) -> None:
    with tempfile.TemporaryDirectory(prefix=".tmp-generation-rollback-all-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        first = tmp / "first.json"
        second = tmp / "second.json"
        first.write_text('{"mutated":1}\n', encoding="utf-8")
        second.write_text('{"mutated":2}\n', encoding="utf-8")
        os.chmod(first, 0o640)
        os.chmod(second, 0o640)
        original_write_text = reconciler.write_text
        attempts: list[Path] = []

        def fail_first_restore(path: Path, text: str) -> None:
            attempts.append(path)
            if path == first:
                raise reconciler.Fail("synthetic first rollback restore failure")
            original_write_text(path, text)

        reconciler.write_text = fail_first_restore
        try:
            try:
                reconciler.restore_authorities(
                    (
                        (first, '{"original":1}\n'),
                        (second, '{"original":2}\n'),
                    )
                )
            except reconciler.Fail as exc:
                require(str(exc) == "environment generation authority rollback incomplete"
                        and exc.__suppress_context__
                        and "synthetic" not in str(exc),
                        "restore-all rollback failure class or privacy drift")
            else:
                raise Fail("first rollback restore failure unexpectedly accepted")
        finally:
            reconciler.write_text = original_write_text

        require(attempts == [first, second], f"rollback restore failure skipped later authority: attempts={attempts}")
        require(first.read_text(encoding="utf-8") == '{"mutated":1}\n', "failed first rollback unexpectedly rewrote fixture")
        require(second.read_text(encoding="utf-8") == '{"original":2}\n', "later rollback authority was not restored")
        require(file_mode(second) == 0o640, "later rollback authority mode drifted")
        leftovers = list(tmp.glob(".*.tmp"))
        require(not leftovers, "rollback-all fixture left temporary files")
    print("PASS rollback: first restore failure does not skip later environment-generation authority restores")


def prove_primary_and_rollback_diagnostics_preserved(
    reconciler: object,
    canonical_contract: bytes,
    canonical_registry: bytes,
    canonical_status: bytes,
    canonical_contract_mode: int,
    canonical_status_mode: int,
) -> None:
    original_write_text = reconciler.write_text
    original_run_validator = reconciler.run_validator
    original_restore_authorities = reconciler.restore_authorities

    reconciler.write_text = lambda path, text: None

    def fail_primary_validator(path: Path, expected_relative: Path, label: str) -> None:
        if path == reconciler.OPERABILITY_VALIDATOR:
            raise reconciler.Fail("synthetic primary post-validator failure")

    def fail_rollback(authorities: tuple[tuple[Path, str], ...]) -> None:
        raise reconciler.Fail("synthetic rollback restore failure")

    reconciler.run_validator = fail_primary_validator
    reconciler.restore_authorities = fail_rollback
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            text = str(exc)
            require(text == "environment generation status reconcile failed; rollback incomplete"
                    and exc.__suppress_context__,
                    "generation reconcile rollback incomplete class or privacy drift")
            require("synthetic" not in text,
                    "generation reconcile leaked private primary or rollback exception")
        else:
            raise Fail("combined primary/rollback failure unexpectedly succeeded")
    finally:
        reconciler.write_text = original_write_text
        reconciler.run_validator = original_run_validator
        reconciler.restore_authorities = original_restore_authorities

    assert_canonical_unchanged(
        canonical_contract,
        canonical_registry,
        canonical_status,
        "combined primary/rollback diagnostic failure",
        canonical_contract_mode,
        canonical_status_mode,
    )
    print("PASS diagnostics: generation reconcile rollback incomplete is class-only and private")


def prove_aggregate_validator_rollback(reconciler: object) -> None:
    observed: list[str] = []
    original_run_validator = reconciler.run_validator

    def fail_after_generation_validator(path: Path, expected_relative: Path, label: str) -> None:
        observed.append(label)
        if path == reconciler.OPERABILITY_VALIDATOR:
            raise reconciler.Fail("operability validator failed: synthetic aggregate failure")
        return None

    reconciler.run_validator = fail_after_generation_validator
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require(str(exc) == "environment generation status reconcile failed; rollback completed"
                    and exc.__suppress_context__
                    and "synthetic" not in str(exc),
                    "aggregate rollback completed class or privacy drift")
        else:
            raise Fail("aggregate operability validation failure unexpectedly accepted")
    finally:
        reconciler.run_validator = original_run_validator

    require(observed == ["generation validator", "operability validator"], f"post-write validator order drift: {observed}")
    print("PASS rollback: aggregate operability failure restores fixture generation authorities")


def prove_private_child_validator(reconciler: object) -> None:
    """Real child invocation refuses private output, timeout and failed exit."""
    original_run = reconciler.subprocess.run
    private_canary = "PRIVATE_GENERATION_CHILD_VALIDATOR_CANARY"
    try:
        for scenario in ("positive", "exit", "timeout", "os-error", "wrong-type"):
            def fake_run(args, **kwargs):
                require(args == [sys.executable, str(reconciler.VALIDATOR)]
                        and kwargs.get("cwd") == reconciler.ROOT
                        and kwargs.get("stdout") == subprocess.DEVNULL
                        and kwargs.get("stderr") == subprocess.DEVNULL
                        and kwargs.get("timeout") == reconciler.VALIDATOR_TIMEOUT_SECONDS
                        and kwargs.get("check") is False,
                        "environment generation child validator output/timeout boundary drift")
                if scenario == "timeout":
                    raise subprocess.TimeoutExpired(args, reconciler.VALIDATOR_TIMEOUT_SECONDS)
                if scenario == "os-error":
                    raise OSError(private_canary)
                if scenario == "wrong-type":
                    return subprocess.CompletedProcess(args, True)
                return subprocess.CompletedProcess(args, 0 if scenario == "positive" else 23)
            reconciler.subprocess.run = fake_run
            if scenario == "positive":
                reconciler.run_validator(
                    reconciler.VALIDATOR, reconciler.VALIDATOR_REL, "generation validator")
                continue
            try:
                reconciler.run_validator(
                    reconciler.VALIDATOR, reconciler.VALIDATOR_REL, "generation validator")
            except reconciler.Fail as exc:
                require(str(exc) == "environment generation child validator failed"
                        and private_canary not in str(exc),
                        f"generation child {scenario} leaked private diagnostics")
                if scenario in ("timeout", "os-error"):
                    require(exc.__suppress_context__,
                            f"generation child {scenario} leaked exception context")
            else:
                raise Fail(f"generation child {scenario} unexpectedly accepted")
    finally:
        reconciler.subprocess.run = original_run
    print("PASS reject: environment generation child validator timeout/output/exit classes remain private")


def prove_private_atomic_authority_writer(reconciler: object) -> None:
    """Fault-inject the real authority writer without touching canonical files."""
    with tempfile.TemporaryDirectory(prefix=".tmp-generation-private-atomic-", dir=TMP_PARENT) as tmp:
        parent = Path(tmp)
        path = parent / "authority.json"
        original = b'{"sentinel":"before"}\n'
        path.write_bytes(original)
        path.chmod(0o640)
        outside = parent / "outside-canary.json"
        outside.write_bytes(b"PRIVATE_GENERATION_AUTHORITY_CANARY")
        alias = parent / "authority-alias.json"
        alias.symlink_to(outside)
        try:
            reconciler.write_text(alias, '{"sentinel":"after"}\n')
        except reconciler.Fail as exc:
            require(str(exc) == "environment generation authority target symlink refused",
                    "generation authority symlink rejected at wrong boundary")
        else:
            raise Fail("generation authority writer accepted symlink target")
        require(outside.read_bytes() == b"PRIVATE_GENERATION_AUTHORITY_CANARY",
                "generation authority writer modified external canary")
        try:
            reconciler.write_text(path, "x" * (reconciler.MAX_AUTHORITY_BYTES + 1))
        except reconciler.Fail as exc:
            require(str(exc) == "environment generation authority payload size limit exceeded",
                    "generation authority oversized payload wrong failure class")
        else:
            raise Fail("generation authority oversized payload accepted")

        original_mkstemp = reconciler.tempfile.mkstemp
        original_fdopen = reconciler.os.fdopen
        original_fchmod = reconciler.os.fchmod
        original_replace = reconciler.os.replace
        try:
            for stage in ("mkstemp", "fdopen", "fchmod", "replace"):
                opened: list[int] = []

                def reject(*_args, **_kwargs):
                    raise OSError("PRIVATE_GENERATION_ATOMIC_CANARY")

                def reject_fdopen(fd, *_args, **_kwargs):
                    opened.append(fd)
                    raise OSError("PRIVATE_GENERATION_ATOMIC_CANARY")

                owner, attribute, replacement = {
                    "mkstemp": (reconciler.tempfile, "mkstemp", reject),
                    "fdopen": (reconciler.os, "fdopen", reject_fdopen),
                    "fchmod": (reconciler.os, "fchmod", reject),
                    "replace": (reconciler.os, "replace", reject),
                }[stage]
                setattr(owner, attribute, replacement)
                try:
                    try:
                        reconciler.write_text(path, '{"sentinel":"after"}\n')
                    except reconciler.Fail as exc:
                        require(str(exc) == "cannot atomically write environment generation authority"
                                and exc.__suppress_context__,
                                f"generation authority {stage} leaked private failure details")
                    else:
                        raise Fail(f"generation authority {stage} unexpectedly accepted")
                finally:
                    setattr(owner, attribute, {
                        "mkstemp": original_mkstemp,
                        "fdopen": original_fdopen,
                        "fchmod": original_fchmod,
                        "replace": original_replace,
                    }[stage])
                for fd in opened:
                    try:
                        os.fstat(fd)
                    except OSError:
                        pass
                    else:
                        raise Fail("generation authority fdopen failure leaked descriptor")
                require(path.read_bytes() == original and file_mode(path) == 0o640,
                        f"generation authority {stage} changed original bytes/mode")
                require(not list(parent.glob(".authority.json.*.tmp")),
                        f"generation authority {stage} left temporary residue")

            class ShortTextHandle:
                def __init__(self, descriptor: int):
                    self.source = original_fdopen(descriptor, "w", encoding="utf-8", newline="")

                def __enter__(self):
                    self.source.__enter__()
                    return self

                def __exit__(self, *args):
                    return self.source.__exit__(*args)

                def fileno(self):
                    return self.source.fileno()

                def write(self, payload: str) -> int:
                    count = max(1, len(payload) // 2)
                    self.source.write(payload[:count])
                    return count

                def flush(self) -> None:
                    self.source.flush()

            def short_fdopen(descriptor, mode, *args, **kwargs):
                if mode == "w":
                    return ShortTextHandle(descriptor)
                return original_fdopen(descriptor, mode, *args, **kwargs)

            reconciler.os.fdopen = short_fdopen
            try:
                try:
                    reconciler.write_text(path, '{"sentinel":"after"}\n')
                except reconciler.Fail as exc:
                    require(str(exc) == "cannot atomically write environment generation authority"
                            and exc.__suppress_context__,
                            "generation authority short text write leaked diagnostics")
                else:
                    raise Fail("generation authority short text write unexpectedly accepted")
            finally:
                reconciler.os.fdopen = original_fdopen
            require(path.read_bytes() == original and file_mode(path) == 0o640,
                    "generation authority short text write changed bytes/mode")
            require(not list(parent.glob(".authority.json.*.tmp")),
                    "generation authority short text write left residue")
        finally:
            reconciler.tempfile.mkstemp = original_mkstemp
            reconciler.os.fdopen = original_fdopen
            reconciler.os.fchmod = original_fchmod
            reconciler.os.replace = original_replace
    print("PASS reject: generation reconciler atomic writer private faults, short writes and symlinks")


def prove_private_bounded_authority_reader(reconciler: object) -> None:
    """Read-only inode, size and descriptor negatives against the real reconciler."""
    with tempfile.TemporaryDirectory(prefix=".tmp-generation-private-read-", dir=TMP_PARENT) as tmp:
        parent = Path(tmp)
        source = parent / "authority.json"
        payload = b'{"sentinel":"before"}\n'
        source.write_bytes(payload)
        require(reconciler.read_text(source) == payload.decode("utf-8"),
                "generation authority reader positive control failed")
        source.write_bytes(b"x" * (reconciler.MAX_AUTHORITY_BYTES + 1))
        try:
            reconciler.read_text(source)
        except reconciler.Fail as exc:
            require(str(exc) == "environment generation authority source size limit exceeded",
                    "oversized generation authority read wrong failure class")
        else:
            raise Fail("oversized generation authority read accepted")
        source.write_bytes(bytes([255]))
        try:
            reconciler.read_text(source)
        except reconciler.Fail as exc:
            require(str(exc) == "environment generation authority source UTF-8 invalid",
                    "invalid UTF-8 generation authority wrong failure class")
        else:
            raise Fail("invalid UTF-8 generation authority accepted")
        source.write_bytes(payload)

        external = parent / "external-canary.json"
        external.write_bytes(b"PRIVATE_GENERATION_READ_CANARY")
        alias = parent / "authority-alias.json"
        alias.symlink_to(external)
        try:
            reconciler.read_text(alias)
        except reconciler.Fail as exc:
            require(str(exc) == "cannot read environment generation authority"
                    and exc.__suppress_context__,
                    "generation authority symlink read leaked private diagnostics")
        else:
            raise Fail("generation authority reader followed symlink")
        require(external.read_bytes() == b"PRIVATE_GENERATION_READ_CANARY",
                "generation authority reader mutated external canary")
        fifo = parent / "authority-fifo.json"
        os.mkfifo(fifo)
        for unsafe in (fifo, parent):
            try:
                reconciler.read_text(unsafe)
            except reconciler.Fail as exc:
                require(str(exc) == "environment generation authority source is not a regular file",
                        "generation authority special node wrong failure class")
            else:
                raise Fail("generation authority reader accepted special node")

        original_fdopen = reconciler.os.fdopen
        opened: list[int] = []

        def reject_fdopen(fd, *_args, **_kwargs):
            opened.append(fd)
            raise OSError("PRIVATE_GENERATION_READ_FDOPEN_CANARY")

        reconciler.os.fdopen = reject_fdopen
        try:
            try:
                reconciler.read_text(source)
            except reconciler.Fail as exc:
                require(str(exc) == "cannot read environment generation authority"
                        and exc.__suppress_context__,
                        "generation authority reader fdopen error leaked private details")
            else:
                raise Fail("generation authority reader fdopen failure accepted")
        finally:
            reconciler.os.fdopen = original_fdopen
        require(len(opened) == 1, "generation authority fdopen negative not reached")
        for fd in opened:
            try:
                os.fstat(fd)
            except OSError:
                pass
            else:
                raise Fail("generation authority reader fdopen failure leaked descriptor")
        require(source.read_bytes() == payload,
                "generation authority read negative modified source bytes")
    print("PASS reject: generation authority bounded reader symlink/FIFO/UTF-8/FD cleanup")


def prove_strict_authority_json(reconciler: object) -> None:
    """Reject ambiguous authority JSON using the real reconciler loader."""
    with tempfile.TemporaryDirectory(prefix=".tmp-generation-json-strict-", dir=TMP_PARENT) as tmp:
        path = Path(tmp) / "authority.json"
        path.write_bytes(b'{"sentinel":"safe"}\n')
        require(reconciler.load(path) == {"sentinel": "safe"},
                "generation strict authority JSON positive control failed")
        cases = (
            ("duplicate", b'{"a":1,"a":2}',
             "environment generation authority JSON duplicate key refused"),
            ("nonfinite", b'{"a":NaN}',
             "environment generation authority JSON nonfinite number refused"),
            ("overflow-float", b'{"a":1e999}',
             "environment generation authority JSON nonfinite number refused"),
            ("huge-int", b'{"a":' + b"9" * 129 + b"}",
             "environment generation authority JSON integer too large"),
            ("invalid-json", b'{"a":',
             "environment generation authority JSON invalid"),
            ("array-root", b"[]",
             "environment generation authority JSON root must be object"),
        )
        for label, payload, expected in cases:
            path.write_bytes(payload)
            try:
                reconciler.load(path)
            except reconciler.Fail as exc:
                require(str(exc) == expected,
                        f"generation strict JSON {label} wrong rejection class")
            else:
                raise Fail(f"generation strict JSON {label} unexpectedly accepted")
    print("PASS reject: generation authority duplicate/nonfinite/huge JSON and nonobject roots")


def prove_private_generation_writer_import(reconciler: object) -> None:
    """Keep filesystem import failures private without hiding implementation faults."""
    original_spec = reconciler.importlib.util.spec_from_file_location
    original_module = reconciler.importlib.util.module_from_spec
    private_canary = "PRIVATE_GENERATION_WRITER_IMPORT_CANARY"
    try:
        for scenario in ("module", "loader"):
            class RejectLoader:
                def exec_module(self, _module):
                    raise OSError(private_canary)

            class FakeSpec:
                loader = RejectLoader()

            def reject_module(_spec):
                raise OSError(private_canary)

            reconciler.importlib.util.spec_from_file_location = (
                (lambda *_args, **_kwargs: FakeSpec())
                if scenario == "loader" else original_spec)
            reconciler.importlib.util.module_from_spec = (
                reject_module if scenario == "module" else (lambda _spec: object()))
            try:
                reconciler.load_writer()
            except reconciler.Fail as exc:
                require(str(exc) == "cannot load environment generation writer"
                        and exc.__suppress_context__
                        and private_canary not in str(exc),
                        f"generation writer import {scenario} leaked private details")
            else:
                raise Fail(f"generation writer import {scenario} unexpectedly accepted")
    finally:
        reconciler.importlib.util.spec_from_file_location = original_spec
        reconciler.importlib.util.module_from_spec = original_module
    module = reconciler.load_writer()
    require(callable(getattr(module, "validate_record", None)),
            "generation writer import positive control failed")
    print("PASS reject: generation reconciler writer import errors are private")


def main() -> int:
    require(RECONCILER.is_file(), "environment generation reconciler missing")
    require(WORKFLOW.is_file(), "environment generation workflow missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    reconciler = load_reconciler()

    canonical_contract = CONTRACT.read_bytes()
    canonical_registry = REGISTRY.read_bytes()
    canonical_status = STATUS.read_bytes()
    canonical_contract_mode = file_mode(CONTRACT)
    canonical_status_mode = file_mode(STATUS)
    validate_atomic_diagnostic_publication()

    substitutions = (
        ("CONTRACT", reconciler.REGISTRY, "environment generation contract authority drift"),
        ("REGISTRY", reconciler.CONTRACT, "environment generation registry authority drift"),
        ("GEN_SCHEMA", reconciler.CONTRACT, "environment generation record schema authority drift"),
        ("ENV_VALIDATOR", reconciler.VALIDATOR, "environment semantic validator authority drift"),
        ("WRITER", reconciler.VALIDATOR, "environment generation writer authority drift"),
        ("VALIDATOR", reconciler.OPERABILITY_VALIDATOR, "environment generation validator authority drift"),
        ("OPERABILITY_VALIDATOR", reconciler.VALIDATOR, "operability validator authority drift"),
        ("NEGATIVE", reconciler.VALIDATOR, "environment generation negative suite authority drift"),
        ("STATUS", reconciler.CONTRACT, "production operability status authority drift"),
    )
    for attribute, replacement, expected in substitutions:
        original = getattr(reconciler, attribute)
        setattr(reconciler, attribute, replacement)
        try:
            expect_domain_fail(f"{attribute.lower()} substitution", reconciler.main, reconciler.Fail, expected)
            assert_canonical_unchanged(
                canonical_contract,
                canonical_registry,
                canonical_status,
                attribute.lower(),
                canonical_contract_mode,
                canonical_status_mode,
            )
        finally:
            setattr(reconciler, attribute, original)

    with tempfile.TemporaryDirectory(prefix=".tmp-environment-generation-reconcile-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_domain_fail("invalid UTF-8 generation authority", lambda: reconciler.load(invalid_utf8), reconciler.Fail)

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_domain_fail("unreadable generation authority directory", lambda: reconciler.load(directory_authority), reconciler.Fail)

        with tempfile.TemporaryDirectory(prefix="memory-os-environment-generation-outside-") as outside_dir:
            outside = Path(outside_dir) / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            expect_domain_fail("generation authority escapes repository", lambda: reconciler.load(outside), reconciler.Fail)

        absolute_ref = str((ROOT / "README.md").resolve())
        expect_domain_fail("absolute current environment ref", lambda: reconciler.canonical_repo_ref(absolute_ref, "invalid ref"), reconciler.Fail)
        expect_domain_fail("parent traversal current environment ref", lambda: reconciler.canonical_repo_ref("scripts/../README.md", "invalid ref"), reconciler.Fail)

    writer = reconciler.load_writer()
    canonical_registry_obj: dict[str, Any] = json.loads(canonical_registry.decode("utf-8"))
    corruption_cases: tuple[tuple[str, Callable[[dict[str, Any]], None]], ...] = (
        ("registry schema drift", lambda value: value.__setitem__("schemaVersion", "broken")),
        ("registry class drift", lambda value: value.__setitem__("registryClass", "BROKEN")),
        ("append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
        ("production evidence promoted", lambda value: value.__setitem__("productionEvidence", True)),
        ("registered generation boolean count", lambda value: value.__setitem__("registeredGenerationCount", True)),
        ("registered generation count drift", lambda value: value.__setitem__("registeredGenerationCount", 1)),
        ("empty registry current pointer drift", lambda value: value.__setitem__("currentGenerationId", "pegen_invalid_current")),
    )
    for name, mutate in corruption_cases:
        corrupted = json.loads(json.dumps(canonical_registry_obj))
        mutate(corrupted)
        try:
            writer.validate_registry_for_append(corrupted)
        except Exception:
            print(f"PASS reject before reconcile: {name}")
        else:
            raise Fail(f"corrupt generation registry unexpectedly accepted: {name}")
        assert_canonical_unchanged(
            canonical_contract,
            canonical_registry,
            canonical_status,
            name,
            canonical_contract_mode,
            canonical_status_mode,
        )

    prefix = reconciler.EVIDENCE_PREFIX
    old = prefix + " old"
    new = prefix + " new"
    values = ["before", old, "after"]
    reconciler.replace_single_prefixed(values, prefix, new)
    require(values == ["before", new, "after"], "environment generation evidence moved during replacement")
    values = [old, prefix + " duplicate"]
    expect_domain_fail(
        "duplicate environment generation evidence prefix",
        lambda: reconciler.replace_single_prefixed(values, prefix, new),
        reconciler.Fail,
        "duplicate authority evidence prefix",
    )
    require(values == [old, prefix + " duplicate"], "duplicate generation evidence rejection mutated ordering")
    print("PASS preserve: environment generation evidence ordering is deterministic")

    prove_private_generation_writer_import(reconciler)
    prove_private_child_validator(reconciler)
    prove_private_bounded_authority_reader(reconciler)
    prove_strict_authority_json(reconciler)
    prove_atomic_write_mode_preservation(reconciler)
    prove_private_atomic_authority_writer(reconciler)
    with isolated_authorities(reconciler):
        prove_atomic_write_failure(reconciler)
    with isolated_authorities(reconciler):
        prove_second_authority_replace_rollback(reconciler)
    prove_rollback_restore_failure_attempts_all(reconciler)
    prove_primary_and_rollback_diagnostics_preserved(
        reconciler,
        canonical_contract,
        canonical_registry,
        canonical_status,
        canonical_contract_mode,
        canonical_status_mode,
    )
    with isolated_authorities(reconciler):
        prove_aggregate_validator_rollback(reconciler)

    assert_canonical_unchanged(
        canonical_contract,
        canonical_registry,
        canonical_status,
        "isolated transactional negatives",
        canonical_contract_mode,
        canonical_status_mode,
    )
    print("PASS boundary: transactional environment-generation negatives keep canonical authorities read-only")
    print("PASS rollback: environment generation contract/registry/status preserved byte-for-byte and mode-for-mode")
    print("canonical generation data/executable substitutions accepted: false")
    print("generation evidence reordering accepted: false")
    print("non-atomic environment generation authority write accepted: false")
    print("environment generation authority mode drift accepted: false")
    print("non-atomic environment generation diagnostic write accepted: false")
    print("second-authority replace failure triggers full rollback: true")
    print("rollback restore failure skips later authority restores: false")
    print("primary reconcile diagnostic lost on rollback failure: false")
    print("aggregate operability failure triggers rollback: true")
    print("Environment generation reconcile negative suite PASS")
    print("production generation created: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT GENERATION RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
