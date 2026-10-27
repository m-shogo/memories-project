#!/usr/bin/env python3
"""Prove recovery-objective registry append rollback and CLI authority are fail-closed."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import stat
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"
CONTRACT = ROOT / "contracts/operations/recovery-objectives-admission-contract.v1.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_recovery_objectives_append_rollback_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load recovery-objective writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(name: str, action, failure_type: type[BaseException]) -> None:
    try:
        action()
    except failure_type:
        print(f"PASS reject: {name}")
        return
    except Exception:
        raise Fail(f"{name} leaked non-domain exception") from None
    raise Fail(f"negative case unexpectedly accepted: {name}")


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def residue(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.iterdir()
        if path.name.startswith(".recovery-objectives.")
        or path.name.startswith(".recovery-objectives-rollback.")
    )


def prove_private_negative_classifier(writer) -> None:
    """Unexpected fixture errors must never expose private exception text."""
    marker = "PRIVATE_OBJECTIVE_APPEND_NEGATIVE_CANARY"

    def raise_fault(fault):
        raise fault

    for label, fault, expected_output in (
        ("unexpected", TypeError(marker), ""),
        ("expected", writer.Fail(marker), "PASS reject: private classifier\\n"),
    ):
        captured = io.StringIO()
        with redirect_stdout(captured):
            if label == "expected":
                expect_rejected("private classifier", lambda: raise_fault(fault), writer.Fail)
            else:
                try:
                    expect_rejected("private classifier", lambda: raise_fault(fault), writer.Fail)
                except Fail as exc:
                    require(str(exc) == "private classifier leaked non-domain exception"
                            and exc.__suppress_context__ and marker not in str(exc),
                            "objective append negative classifier disclosed private exception")
                else:
                    raise Fail("objective append negative classifier accepted unexpected fault")
        require(captured.getvalue() == expected_output and marker not in captured.getvalue(),
                f"objective append negative classifier {label} output drift")
    print("PASS: objective append negative classifier private failure redaction")


def prove_bounded_registry_snapshot(writer) -> None:
    """Exercise actual pre-append snapshot without changing canonical authorities."""
    original_registry = writer.REGISTRY
    private_marker = "PRIVATE_OBJECTIVE_SNAPSHOT_CANARY"
    with tempfile.TemporaryDirectory(prefix="memory-os-objective-snapshot-") as tmp:
        root = Path(tmp)
        registry = root / "registry.json"
        baseline = b'{"safe":true}\\n'
        registry.write_bytes(baseline)
        registry.chmod(0o640)
        outside = root / "outside-canary.json"
        outside.write_text(private_marker, encoding="utf-8")
        alias = root / "registry-alias.json"
        alias.symlink_to(outside)
        fifo = root / "registry-fifo"
        os.mkfifo(fifo)

        def reject(path, label: str, expected: str) -> None:
            writer.REGISTRY = path
            try:
                writer.snapshot_registry_for_append()
            except writer.Fail as exc:
                require(str(exc) == expected and private_marker not in str(exc),
                        f"registry snapshot {label} rejection drift")
            else:
                raise Fail(f"registry snapshot {label} unexpectedly accepted")

        try:
            writer.REGISTRY = registry
            require(writer.snapshot_registry_for_append() == (baseline, 0o640),
                    "registry snapshot positive bytes/mode control failed")
            registry.write_bytes(b"x" * (writer.MAX_JSON_BYTES + 1))
            reject(registry, "oversize",
                   "recovery objective registry snapshot size limit exceeded")
            registry.write_bytes(baseline)
            reject(alias, "symlink",
                   "recovery objective registry snapshot unreadable or unsafe")
            reject(fifo, "FIFO",
                   "recovery objective registry snapshot unsafe file type")
            reject(root, "directory",
                   "recovery objective registry snapshot unsafe file type")
            reject(root / "missing-private-canary", "missing",
                   "recovery objective registry snapshot unreadable or unsafe")
            reject(Path("relative.json"), "relative",
                   "recovery objective registry snapshot path invalid")
            reject("not-a-path", "non-Path",
                   "recovery objective registry snapshot path invalid")
            require(registry.read_bytes() == baseline
                    and outside.read_text(encoding="utf-8") == private_marker,
                    "registry snapshot negative mutated fixture or outside canary")
        finally:
            writer.REGISTRY = original_registry
    print("PASS: bounded registry snapshot positive and seven fail-closed negatives")


def main() -> int:
    require(WRITER.is_file() and CONTRACT.is_file(), "recovery-objective append authority missing")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    require(
        contract.get("rules", {}).get("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure") is True,
        "transactional append contract guard missing",
    )

    writer = load_writer()
    prove_private_negative_classifier(writer)
    require(callable(getattr(writer, "write_registry_transactionally", None)), "transactional registry writer missing")
    require(callable(getattr(writer, "require_actual_cli_authorities", None)), "recovery-objective CLI authority guard missing")
    writer.require_actual_cli_authorities()
    prove_bounded_registry_snapshot(writer)

    with tempfile.TemporaryDirectory(prefix="memory-os-objective-append-rollback-") as tmp:
        root = Path(tmp)
        registry = root / "recovery-objectives-registry.v1.json"
        original = b'{"sentinel":"before"}\n'
        registry.write_bytes(original)
        registry.chmod(0o640)

        original_registry = writer.REGISTRY
        original_validate = writer.validate_registry_for_append
        original_replace = writer.os.replace
        original_atomic_restore = writer.atomic_restore
        writer.REGISTRY = registry

        try:
            writer.validate_registry_for_append = lambda _value: []
            writer.write_registry_transactionally({"sentinel": "success"})
            require(mode(registry) == 0o640, "successful objective append changed registry permission mode")
            require(not residue(root), "successful objective append left temporary residue")

            registry.write_bytes(original)
            registry.chmod(0o640)
            before_bytes = registry.read_bytes()
            before_mode = mode(registry)
            replace_calls = 0

            def reject_candidate_replace(source, destination):
                nonlocal replace_calls
                replace_calls += 1
                if replace_calls == 1:
                    raise OSError("synthetic candidate replace rejection")
                return original_replace(source, destination)

            writer.os.replace = reject_candidate_replace
            try:
                writer.write_registry_transactionally({"sentinel": "candidate-rejected"})
            except writer.Fail as exc:
                require(str(exc) == "recovery objective registry atomic write failed"
                        and exc.__suppress_context__
                        and "synthetic candidate replace" not in str(exc),
                        "candidate atomic replace rejection wrong or private")
            else:
                raise Fail("candidate objective registry replace rejection was accepted")
            finally:
                writer.os.replace = original_replace
            require(registry.read_bytes() == before_bytes, "candidate replace rejection changed canonical registry bytes")
            require(mode(registry) == before_mode == 0o640, "candidate replace rejection changed canonical registry mode")
            require(not residue(root), "candidate replace rejection left temporary residue")

            marker = "PRIVATE_OBJECTIVE_ATOMIC_IO_CANARY"
            original_mkstemp = writer.tempfile.mkstemp

            def reject_mkstemp(*_args, **_kwargs):
                raise OSError(marker)

            writer.tempfile.mkstemp = reject_mkstemp
            try:
                try:
                    writer.atomic_write({"sentinel": "not-written"}, before_mode)
                except writer.Fail as exc:
                    require(str(exc) == "recovery objective registry atomic write failed"
                            and exc.__suppress_context__ and marker not in str(exc),
                            "atomic mkstemp failure disclosed private detail")
                else:
                    raise Fail("atomic mkstemp failure was accepted")
            finally:
                writer.tempfile.mkstemp = original_mkstemp
            require(registry.read_bytes() == before_bytes and not residue(root),
                    "atomic mkstemp rejection changed fixture or left residue")

            original_fdopen = writer.os.fdopen

            def reject_fdopen(*_args, **_kwargs):
                raise OSError(marker)

            writer.os.fdopen = reject_fdopen
            try:
                try:
                    writer.atomic_write({"sentinel": "not-written"}, before_mode)
                except writer.Fail as exc:
                    require(str(exc) == "recovery objective registry atomic write failed"
                            and exc.__suppress_context__ and marker not in str(exc),
                            "atomic fdopen failure disclosed private detail")
                else:
                    raise Fail("atomic fdopen failure was accepted")
            finally:
                writer.os.fdopen = original_fdopen
            require(registry.read_bytes() == before_bytes and not residue(root),
                    "atomic fdopen rejection changed fixture or left residue")

            original_close = writer.os.close

            def close_then_fail(fd):
                original_close(fd)
                raise OSError(marker)

            writer.os.fdopen = reject_fdopen
            writer.os.close = close_then_fail
            try:
                for label, action in (
                    ("write", lambda: writer.atomic_write({"sentinel": "not-written"}, before_mode)),
                    ("restore", lambda: writer.atomic_restore(before_bytes, before_mode)),
                ):
                    try:
                        action()
                    except writer.Fail as exc:
                        require(str(exc) == "recovery objective registry temporary cleanup failed"
                                and exc.__suppress_context__ and marker not in str(exc),
                                f"atomic {label} close failure diagnostic wrong or private")
                    else:
                        raise Fail(f"atomic {label} close failure was accepted")
                    require(registry.read_bytes() == before_bytes and not residue(root),
                            f"atomic {label} close failure skipped temporary unlink")
            finally:
                writer.os.fdopen = original_fdopen
                writer.os.close = original_close

            def reject_restore_replace(_source, _destination):
                raise OSError(marker)

            writer.os.replace = reject_restore_replace
            try:
                try:
                    writer.atomic_restore(before_bytes, before_mode)
                except writer.Fail as exc:
                    require(str(exc) == "recovery objective registry atomic restore failed"
                            and exc.__suppress_context__ and marker not in str(exc),
                            "atomic restore replace failure disclosed private detail")
                else:
                    raise Fail("atomic restore replace failure was accepted")
            finally:
                writer.os.replace = original_replace
            require(registry.read_bytes() == before_bytes and mode(registry) == before_mode
                    and not residue(root), "atomic restore rejection changed fixture or left residue")

            primary_marker = "PRIVATE_OBJECTIVE_POST_APPEND_CANARY"
            rollback_marker = "PRIVATE_OBJECTIVE_ROLLBACK_CANARY"

            def reject_after_write(_value):
                raise writer.Fail(primary_marker)

            writer.validate_registry_for_append = reject_after_write
            try:
                writer.write_registry_transactionally({"sentinel": "after"})
            except writer.Fail as exc:
                require(str(exc) == "recovery objectives append failed; rollback completed"
                        and exc.__suppress_context__ and primary_marker not in str(exc),
                        "post-append rollback-completed diagnostic wrong or private")
            else:
                raise Fail("post-append registry validation failure was accepted")
            require(registry.read_bytes() == original, "failed objective append did not restore original registry bytes")
            require(mode(registry) == 0o640, "failed objective append did not restore original registry mode")
            require(not residue(root), "objective append rollback left temporary residue")

            def reject_unexpected_after_write(_value):
                raise TypeError("PRIVATE_OBJECTIVE_UNEXPECTED_POST_APPEND_CANARY")

            writer.validate_registry_for_append = reject_unexpected_after_write
            try:
                writer.write_registry_transactionally({"sentinel": "unexpected-after"})
            except writer.Fail as exc:
                require(str(exc) == "recovery objectives append failed; rollback completed"
                        and exc.__suppress_context__
                        and "PRIVATE_OBJECTIVE_UNEXPECTED" not in str(exc),
                        "unexpected post-append fault disclosed private detail")
            else:
                raise Fail("unexpected post-append failure was accepted")
            require(registry.read_bytes() == original and mode(registry) == 0o640
                    and not residue(root), "unexpected post-append rollback left mutation")
            writer.validate_registry_for_append = reject_after_write

            def reject_rollback_restore(_payload, _mode):
                raise writer.Fail(rollback_marker)

            writer.atomic_restore = reject_rollback_restore
            try:
                writer.write_registry_transactionally({"sentinel": "rollback-failure"})
            except writer.Fail as exc:
                require(str(exc) == "recovery objectives append failed; rollback incomplete"
                        and exc.__suppress_context__
                        and primary_marker not in str(exc)
                        and rollback_marker not in str(exc),
                        "rollback-incomplete diagnostic wrong or private")
            else:
                raise Fail("objective append rollback restore failure was accepted")
            finally:
                writer.atomic_restore = original_atomic_restore
                registry.write_bytes(original)
                registry.chmod(0o640)
            require(not residue(root), "rollback diagnostic negative left temporary residue")
        finally:
            writer.REGISTRY = original_registry
            writer.validate_registry_for_append = original_validate
            writer.os.replace = original_replace
            writer.atomic_restore = original_atomic_restore

        outside_file = root / "outside-authority.json"
        outside_file.write_text("{}\n", encoding="utf-8")
        outside_dir = root / "outside-approvals"
        outside_dir.mkdir()
        for attribute in ("CONTRACT", "REGISTRY", "LOCK"):
            original_authority = getattr(writer, attribute)
            try:
                setattr(writer, attribute, outside_file)
                expect_rejected(
                    f"recovery objective CLI {attribute} substitution",
                    writer.require_actual_cli_authorities,
                    writer.Fail,
                )
            finally:
                setattr(writer, attribute, original_authority)
        original_approval_dir = writer.APPROVAL_DIR
        try:
            writer.APPROVAL_DIR = outside_dir
            expect_rejected(
                "recovery objective CLI APPROVAL_DIR substitution",
                writer.require_actual_cli_authorities,
                writer.Fail,
            )
        finally:
            writer.APPROVAL_DIR = original_approval_dir
        writer.require_actual_cli_authorities()

    print("Memory OS recovery objectives append rollback negative PASS")
    print("post-append canonical registry revalidation: enforced")
    print("successful append registry mode preservation: enforced")
    print("candidate/restore atomic IO failures private and residue-free: enforced")
    print("failed append registry rollback: exact bytes and mode")
    print("rollback completion/incomplete classes private and preserved: enforced")
    print("candidate/rollback temporary residue: none")
    print("CLI contract/registry/approval-directory/lock substitution accepted: false")
    print("objective created: false")
    print("objective value chosen/defaulted: false")
    print("production evidence: false")
    print("production readiness: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RECOVERY OBJECTIVES APPEND ROLLBACK NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
