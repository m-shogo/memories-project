#!/usr/bin/env python3
"""Reject non-canonical or repository-escaping typed admission authority refs."""
from __future__ import annotations

import importlib.util
import inspect
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py"
EXPECTED_CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
EXPECTED_REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
EXPECTED_GEN_EVIDENCE_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
EXPECTED_GEN_WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
EXPECTED_LOCK = ROOT / "contracts/operations/.backup-restore-non-resurrection-admission.lock"

class Fail(RuntimeError):
    pass

def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)

def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_non_resurrection_admission_path_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load typed admission validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def expect_rejected(module: Any, name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except module.Fail:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")

def load_typed_writer(validator: Any):
    return validator.load_module(validator.WRITER, "memory_os_non_resurrection_writer_negative")

def reject_typed_writer_cli_substitutions(validator: Any) -> None:
    typed_writer = load_typed_writer(validator)
    main_source = inspect.getsource(typed_writer.main)
    guard_index = main_source.find("require_cli_authorities()")
    parser_index = main_source.find("argparse.ArgumentParser")
    require(guard_index >= 0, "typed writer CLI does not enforce canonical authority guard")
    require(parser_index >= 0 and guard_index < parser_index, "typed writer CLI authority guard must run before argument parsing")

    require(typed_writer.CONTRACT == EXPECTED_CONTRACT, "typed writer contract authority drift")
    require(typed_writer.REGISTRY == EXPECTED_REGISTRY, "typed writer registry authority drift")
    require(typed_writer.GEN_EVIDENCE_REGISTRY == EXPECTED_GEN_EVIDENCE_REGISTRY, "typed writer generation evidence authority drift")
    require(typed_writer.GEN_WRITER == EXPECTED_GEN_WRITER, "typed writer generation writer authority drift")
    require(typed_writer.LOCK == EXPECTED_LOCK, "typed writer lock authority drift")

    substitutions = {
        "CONTRACT": ROOT / "contracts/operations/production-operability-status.json",
        "REGISTRY": EXPECTED_GEN_EVIDENCE_REGISTRY,
        "GEN_EVIDENCE_REGISTRY": EXPECTED_REGISTRY,
        "GEN_WRITER": ROOT / "scripts/register-memory-os-recovery-objectives.py",
        "LOCK": EXPECTED_CONTRACT,
    }
    for name, alternate in substitutions.items():
        original = getattr(typed_writer, name)
        setattr(typed_writer, name, alternate)
        try:
            expect_rejected(
                typed_writer,
                f"typed writer CLI {name} substitution",
                typed_writer.require_cli_authorities,
            )
        finally:
            setattr(typed_writer, name, original)

    try:
        typed_writer.require_cli_authorities()
    except typed_writer.Fail as exc:
        raise Fail(f"canonical typed writer CLI authority rejected: {exc}") from exc

def reject_typed_writer_substitution(validator: Any) -> None:
    original_loader = validator.load_module
    typed_writer = original_loader(validator.WRITER, "memory_os_non_resurrection_writer_negative")
    original_generation_writer = typed_writer.GEN_WRITER
    typed_writer.GEN_WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"

    def substituted_loader(path: Path, name: str):
        if path == validator.WRITER:
            return typed_writer
        return original_loader(path, name)

    validator.load_module = substituted_loader
    try:
        expect_rejected(
            validator,
            "repository-contained generation recovery writer substitution",
            validator.main,
        )
    finally:
        validator.load_module = original_loader
        typed_writer.GEN_WRITER = original_generation_writer

def main() -> int:
    validator = load_validator()
    canonical = "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py"
    accepted = validator.canonical_repo_file_ref(canonical, "negative.canonical")
    require(accepted == ROOT / canonical, "canonical in-repository authority ref did not resolve exactly")
    print("PASS accept: canonical repository-relative authority ref")

    expect_rejected(validator, "absolute in-repository authority ref", lambda: validator.canonical_repo_file_ref(str(ROOT / canonical), "negative.absolute"))
    expect_rejected(validator, "parent traversal authority ref", lambda: validator.canonical_repo_file_ref("scripts/../scripts/validate-memory-os-backup-restore-non-resurrection-admission.py", "negative.parent"))

    with tempfile.TemporaryDirectory(prefix="memory-os-non-resurrection-path-negative-") as tmp:
        outside = Path(tmp) / "outside.json"
        outside.write_text("{}\n", encoding="utf-8")
        link = ROOT / "docs/fixtures/memory-os-operability/.non-resurrection-path-negative-link.json"
        loop = ROOT / "docs/fixtures/memory-os-operability/.non-resurrection-path-negative-loop.json"
        require(not link.exists() and not link.is_symlink(), "temporary negative symlink path already exists")
        require(not loop.exists() and not loop.is_symlink(), "temporary negative symlink-loop path already exists")
        try:
            link.symlink_to(outside)
            ref = link.relative_to(ROOT).as_posix()
            expect_rejected(validator, "repo-local symlink escaping repository", lambda: validator.canonical_repo_file_ref(ref, "negative.symlink"))

            loop.symlink_to(loop.name)
            loop_ref = loop.relative_to(ROOT).as_posix()
            expect_rejected(validator, "repo-local authority symlink loop", lambda: validator.canonical_repo_file_ref(loop_ref, "negative.symlinkLoop"))
        finally:
            link.unlink(missing_ok=True)
            loop.unlink(missing_ok=True)

    reject_typed_writer_cli_substitutions(validator)
    reject_typed_writer_substitution(validator)

    print("Memory OS backup/restore non-resurrection contract path negative suite PASS")
    print("absolute authority aliases accepted: false")
    print("parent traversal authority aliases accepted: false")
    print("repository-escaping authority symlinks accepted: false")
    print("authority symlink loops accepted: false")
    print("typed writer CLI authority substitutions accepted: false")
    print("repository-contained generation recovery writer substitution accepted: false")
    print("non-domain authority resolution exceptions leaked: false")
    print("canonical authorities mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE NON-RESURRECTION CONTRACT PATH NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
