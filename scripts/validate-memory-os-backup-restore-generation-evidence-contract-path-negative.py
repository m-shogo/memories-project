#!/usr/bin/env python3
"""Negative proof for canonical generation-evidence contract artifact refs and writer authority."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("memory_os_generation_evidence_contract_path_negative_target", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load generation evidence validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(module: Any, name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except module.Fail:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")


def reject_writer_substitution(module: Any, attribute: str, replacement: Path, name: str) -> None:
    writer = module.load_writer()
    original = getattr(writer, attribute)
    setattr(writer, attribute, replacement)
    original_loader = module.load_writer
    module.load_writer = lambda: writer
    try:
        expect_rejected(module, name, module.main)
    finally:
        module.load_writer = original_loader
        setattr(writer, attribute, original)


def main() -> int:
    module = load_validator()
    canonical_ref = "scripts/validate-memory-os-backup-restore-generation-evidence.py"
    require(module.canonical_contract_ref(canonical_ref, "validator") == Path(canonical_ref), "canonical in-repository ref must validate")
    print("PASS baseline: canonical repository-relative contract artifact ref")

    expect_rejected(
        module,
        "absolute in-repository contract artifact ref",
        lambda: module.canonical_contract_ref(str((ROOT / canonical_ref).resolve()), "validator"),
    )
    expect_rejected(
        module,
        "parent-traversal contract artifact alias",
        lambda: module.canonical_contract_ref(f"scripts/../{canonical_ref}", "validator"),
    )

    with tempfile.TemporaryDirectory() as temporary_directory:
        escaped_target = Path(temporary_directory) / "outside-generation-evidence-contract-ref.py"
        escaped_target.write_text("# outside\n", encoding="utf-8")
        link_path = ROOT / ".memory-os-generation-evidence-contract-ref"
        require(ROOT.is_dir() and not ROOT.is_symlink(),
                "generation-evidence contract-ref fixture root missing or symlinked")
        parent_stat = ROOT.stat()
        parent_identity = (parent_stat.st_dev, parent_stat.st_ino)
        require(not link_path.exists() and not link_path.is_symlink(),
                "temporary contract-ref symlink path already exists")
        link_path.symlink_to(escaped_target)
        created_stat = link_path.lstat()
        created_identity = (created_stat.st_dev, created_stat.st_ino)
        try:
            expect_rejected(
                module,
                "repository-local symlink escaping generation-evidence authority root",
                lambda: module.canonical_contract_ref(str(link_path.relative_to(ROOT)), "validator"),
            )
        finally:
            require(ROOT.is_dir() and not ROOT.is_symlink(),
                    "generation-evidence contract-ref fixture parent substituted before cleanup")
            current_parent = ROOT.stat()
            require((current_parent.st_dev, current_parent.st_ino) == parent_identity,
                    "generation-evidence contract-ref fixture parent inode drift before cleanup")
            current_link = link_path.lstat()
            require((current_link.st_dev, current_link.st_ino) == created_identity,
                    "generation-evidence contract-ref fixture inode drift before cleanup")
            require(link_path.is_symlink() and link_path.resolve() == escaped_target.resolve(),
                    "generation-evidence contract-ref fixture target drift before cleanup")
            link_path.unlink()

    reject_writer_substitution(
        module,
        "GEN_WRITER",
        ROOT / "scripts/register-memory-os-recovery-objectives.py",
        "repository-contained environment generation writer substitution",
    )
    reject_writer_substitution(
        module,
        "OBJECTIVES_WRITER",
        ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py",
        "repository-contained recovery objectives writer substitution",
    )

    print("Memory OS generation evidence contract path negative suite PASS")
    print("absolute contract artifact ref accepted: false")
    print("parent-traversal contract artifact alias accepted: false")
    print("repo-local symlink to external artifact accepted: false")
    print("repository-contained upstream writer substitution accepted: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION EVIDENCE CONTRACT PATH NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
