#!/usr/bin/env python3
"""Prove recovery-objective registry append rollback and CLI authority are fail-closed."""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import tempfile
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
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
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


def main() -> int:
    require(WRITER.is_file() and CONTRACT.is_file(), "recovery-objective append authority missing")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    require(
        contract.get("rules", {}).get("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure") is True,
        "transactional append contract guard missing",
    )

    writer = load_writer()
    require(callable(getattr(writer, "write_registry_transactionally", None)), "transactional registry writer missing")
    require(callable(getattr(writer, "require_actual_cli_authorities", None)), "recovery-objective CLI authority guard missing")
    writer.require_actual_cli_authorities()

    with tempfile.TemporaryDirectory(prefix="memory-os-objective-append-rollback-") as tmp:
        root = Path(tmp)
        registry = root / "recovery-objectives-registry.v1.json"
        original = b'{"sentinel":"before"}\n'
        registry.write_bytes(original)
        registry.chmod(0o640)

        original_registry = writer.REGISTRY
        original_validate = writer.validate_registry_for_append
        original_replace = writer.os.replace
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
            except OSError as exc:
                require("synthetic candidate replace" in str(exc), "unexpected candidate replace rejection")
            else:
                raise Fail("candidate objective registry replace rejection was accepted")
            finally:
                writer.os.replace = original_replace
            require(registry.read_bytes() == before_bytes, "candidate replace rejection changed canonical registry bytes")
            require(mode(registry) == before_mode == 0o640, "candidate replace rejection changed canonical registry mode")
            require(not residue(root), "candidate replace rejection left temporary residue")

            def reject_after_write(_value):
                raise writer.Fail("synthetic post-append registry validation failure")

            writer.validate_registry_for_append = reject_after_write
            try:
                writer.write_registry_transactionally({"sentinel": "after"})
            except writer.Fail as exc:
                require("synthetic post-append" in str(exc), "unexpected transactional append failure")
            else:
                raise Fail("post-append registry validation failure was accepted")
            require(registry.read_bytes() == original, "failed objective append did not restore original registry bytes")
            require(mode(registry) == 0o640, "failed objective append did not restore original registry mode")
            require(not residue(root), "objective append rollback left temporary residue")
        finally:
            writer.REGISTRY = original_registry
            writer.validate_registry_for_append = original_validate
            writer.os.replace = original_replace

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
    print("candidate replace rejection preserves canonical bytes/mode: enforced")
    print("failed append registry rollback: exact bytes and mode")
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
