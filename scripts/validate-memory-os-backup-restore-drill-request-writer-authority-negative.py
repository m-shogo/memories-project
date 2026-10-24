#!/usr/bin/env python3
"""Pin fail-closed rejection of drill-request executable/data authority substitution."""

from __future__ import annotations

import importlib.util
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-request-writer-authority.py"
CANONICAL_WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
CANONICAL_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-request.py"
CANONICAL_ELIGIBILITY = ROOT / "scripts/memory_os_environment_generation_eligibility.py"
CANONICAL_OBJECTIVES = ROOT / "scripts/register-memory-os-recovery-objectives.py"
SUBSTITUTE = ROOT / "scripts/validate-memory-os-backup-restore-drill-request.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_authority_validator(name: str):
    spec = importlib.util.spec_from_file_location(name, AUTHORITY_VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load drill writer authority validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


OWNED_TEMP_MODULES: dict[Path, tuple[tuple[int, int], tuple[int, int]]] = {}


def require_temp_parent_canonical() -> tuple[int, int]:
    require(ROOT.is_dir() and not ROOT.is_symlink(),
            "drill writer temp root missing or symlinked")
    cursor = ROOT
    for part in ("docs", "fixtures", "memory-os-operability"):
        cursor = cursor / part
        require(cursor.is_dir() and not cursor.is_symlink(),
                "drill writer temp parent missing or symlinked")
    require(TMP_PARENT == cursor and TMP_PARENT.resolve(strict=True) ==
            ROOT.resolve(strict=True) / "docs/fixtures/memory-os-operability",
            "drill writer temp parent canonical path drift")
    stat = TMP_PARENT.stat()
    return stat.st_dev, stat.st_ino


def require_owned_temp_cleanup(path: Path) -> None:
    identities = OWNED_TEMP_MODULES.get(path)
    require(identities is not None, "drill writer temp module not owned by this negative run")
    parent_identity, created_identity = identities
    require(require_temp_parent_canonical() == parent_identity,
            "drill writer temp parent inode drift before cleanup")
    require(path.is_file() and not path.is_symlink(),
            "drill writer temp module substituted before cleanup")
    current = path.stat()
    require((current.st_dev, current.st_ino) == created_identity,
            "drill writer temp module inode drift before cleanup")
    path.unlink()
    del OWNED_TEMP_MODULES[path]


def repo_temp_module(prefix: str, content: str) -> Path:
    parent_identity = require_temp_parent_canonical()
    fd, raw_path = tempfile.mkstemp(prefix=prefix, suffix=".py", dir=TMP_PARENT)
    path = Path(raw_path)
    created_stat = os.fstat(fd)
    created_identity = (created_stat.st_dev, created_stat.st_ino)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as owned:
            owned.write(content)
    except BaseException:
        if path.is_file() and not path.is_symlink():
            current = path.stat()
            if (current.st_dev, current.st_ino) == created_identity:
                path.unlink()
        raise
    OWNED_TEMP_MODULES[path] = (parent_identity, created_identity)
    return path


def expect_rejection(label: str, configure, expected_message: str) -> None:
    module = load_authority_validator(f"drill_writer_authority_negative_{label}")
    cleanup: list[Path] = []
    owned_before = set(OWNED_TEMP_MODULES)
    try:
        configure(module, cleanup)
        try:
            module.main()
        except module.Fail as exc:
            require(expected_message in str(exc), f"{label}: unexpected rejection: {exc}")
        else:
            raise Fail(f"{label}: substituted authority was accepted")
    finally:
        created_paths = set(OWNED_TEMP_MODULES) - owned_before
        for path in sorted(created_paths):
            require_owned_temp_cleanup(path)
        require(set(cleanup) == created_paths,
                f"{label}: drill writer temp cleanup registration drift")


def canonical_writer_module(
    *,
    contract: str = "contracts/operations/backup-restore-drill-request-contract.v1.json",
    registry: str = "contracts/operations/backup-restore-drill-request-registry.v1.json",
    gen_registry: str = "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    objectives_registry: str = "contracts/operations/recovery-objectives-registry.v1.json",
    eligibility: str = "memory_os_environment_generation_eligibility.py",
    lock: str = "contracts/operations/.backup-restore-drill-request.lock",
) -> str:
    return (
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parents[3]\n"
        f"CONTRACT = ROOT / '{contract}'\n"
        f"REGISTRY = ROOT / '{registry}'\n"
        f"GEN_REGISTRY = ROOT / '{gen_registry}'\n"
        f"OBJECTIVES_REGISTRY = ROOT / '{objectives_registry}'\n"
        f"ELIGIBILITY_HELPER = ROOT / 'scripts/{eligibility}'\n"
        "OBJECTIVES_WRITER = ROOT / 'scripts/register-memory-os-recovery-objectives.py'\n"
        f"LOCK = ROOT / '{lock}'\n"
    )


def canonical_reconciler_module(
    *,
    contract: str = "contracts/operations/backup-restore-drill-request-contract.v1.json",
    gen_registry: str = "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    objectives_registry: str = "contracts/operations/recovery-objectives-registry.v1.json",
    objectives_writer: str = "register-memory-os-recovery-objectives.py",
    status: str = "contracts/operations/production-operability-status.json",
) -> str:
    return (
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parents[3]\n"
        f"CONTRACT = ROOT / '{contract}'\n"
        "REGISTRY = ROOT / 'contracts/operations/backup-restore-drill-request-registry.v1.json'\n"
        f"GEN_REGISTRY = ROOT / '{gen_registry}'\n"
        f"OBJECTIVES_REGISTRY = ROOT / '{objectives_registry}'\n"
        f"STATUS = ROOT / '{status}'\n"
        "WRITER = ROOT / 'scripts/request-memory-os-backup-restore-drill.py'\n"
        "VALIDATOR = ROOT / 'scripts/validate-memory-os-backup-restore-drill-request.py'\n"
        "ELIGIBILITY_HELPER = ROOT / 'scripts/memory_os_environment_generation_eligibility.py'\n"
        f"OBJECTIVES_WRITER = ROOT / 'scripts/{objectives_writer}'\n"
    )


def substitute_writer_eligibility(module, cleanup: list[Path]) -> None:
    fake = repo_temp_module(
        ".drill-writer-authority-negative-",
        canonical_writer_module(eligibility="validate-memory-os-backup-restore-drill-request.py"),
    )
    cleanup.append(fake)
    module.WRITER = fake


def substitute_writer_contract(module, cleanup: list[Path]) -> None:
    fake = repo_temp_module(
        ".drill-writer-data-authority-negative-",
        canonical_writer_module(contract="contracts/operations/recovery-objectives-admission-contract.v1.json"),
    )
    cleanup.append(fake)
    module.WRITER = fake


def substitute_writer_registry(module, cleanup: list[Path]) -> None:
    fake = repo_temp_module(
        ".drill-writer-data-authority-negative-",
        canonical_writer_module(registry="contracts/operations/recovery-objectives-registry.v1.json"),
    )
    cleanup.append(fake)
    module.WRITER = fake


def substitute_writer_gen_registry(module, cleanup: list[Path]) -> None:
    fake = repo_temp_module(
        ".drill-writer-data-authority-negative-",
        canonical_writer_module(gen_registry="contracts/operations/backup-restore-drill-request-registry.v1.json"),
    )
    cleanup.append(fake)
    module.WRITER = fake


def substitute_writer_objectives_registry(module, cleanup: list[Path]) -> None:
    fake = repo_temp_module(
        ".drill-writer-data-authority-negative-",
        canonical_writer_module(objectives_registry="contracts/operations/production-equivalent-environment-generation-registry.v1.json"),
    )
    cleanup.append(fake)
    module.WRITER = fake


def substitute_writer_lock(module, cleanup: list[Path]) -> None:
    fake = repo_temp_module(
        ".drill-writer-lock-authority-negative-",
        canonical_writer_module(lock="contracts/operations/.backup-restore-generation-evidence.lock"),
    )
    cleanup.append(fake)
    module.WRITER = fake


def substitute_reconciler_objective(module, cleanup: list[Path]) -> None:
    fake = repo_temp_module(
        ".drill-reconcile-authority-negative-",
        canonical_reconciler_module(objectives_writer="validate-memory-os-backup-restore-drill-request.py"),
    )
    cleanup.append(fake)
    module.RECONCILER = fake


def substitute_reconciler_contract(module, cleanup: list[Path]) -> None:
    fake = repo_temp_module(
        ".drill-reconcile-data-authority-negative-",
        canonical_reconciler_module(contract="contracts/operations/recovery-objectives-admission-contract.v1.json"),
    )
    cleanup.append(fake)
    module.RECONCILER = fake


def substitute_reconciler_gen_registry(module, cleanup: list[Path]) -> None:
    fake = repo_temp_module(
        ".drill-reconcile-data-authority-negative-",
        canonical_reconciler_module(gen_registry="contracts/operations/backup-restore-drill-request-registry.v1.json"),
    )
    cleanup.append(fake)
    module.RECONCILER = fake


def substitute_reconciler_objectives_registry(module, cleanup: list[Path]) -> None:
    fake = repo_temp_module(
        ".drill-reconcile-data-authority-negative-",
        canonical_reconciler_module(objectives_registry="contracts/operations/production-equivalent-environment-generation-registry.v1.json"),
    )
    cleanup.append(fake)
    module.RECONCILER = fake


def substitute_reconciler_status(module, cleanup: list[Path]) -> None:
    fake = repo_temp_module(
        ".drill-reconcile-data-authority-negative-",
        canonical_reconciler_module(status="contracts/operations/backup-restore-drill-request-contract.v1.json"),
    )
    cleanup.append(fake)
    module.RECONCILER = fake


def main() -> int:
    for path, field in (
        (AUTHORITY_VALIDATOR, "authority validator"),
        (CANONICAL_WRITER, "canonical writer"),
        (CANONICAL_VALIDATOR, "canonical validator"),
        (CANONICAL_ELIGIBILITY, "canonical eligibility helper"),
        (CANONICAL_OBJECTIVES, "canonical objectives writer"),
        (SUBSTITUTE, "repository-contained substitute"),
    ):
        require(path.is_file(), f"missing {field}: {path}")
    require(TMP_PARENT.is_dir(), "isolated operability fixture parent missing")

    expect_rejection(
        "writer-eligibility-substitution",
        substitute_writer_eligibility,
        "drill request writer authority drift: ELIGIBILITY_HELPER",
    )
    expect_rejection(
        "writer-contract-substitution",
        substitute_writer_contract,
        "drill request writer authority drift: CONTRACT",
    )
    expect_rejection(
        "writer-registry-substitution",
        substitute_writer_registry,
        "drill request writer authority drift: REGISTRY",
    )
    expect_rejection(
        "writer-generation-registry-substitution",
        substitute_writer_gen_registry,
        "drill request writer authority drift: GEN_REGISTRY",
    )
    expect_rejection(
        "writer-objectives-registry-substitution",
        substitute_writer_objectives_registry,
        "drill request writer authority drift: OBJECTIVES_REGISTRY",
    )
    expect_rejection(
        "writer-lock-substitution",
        substitute_writer_lock,
        "drill request writer authority drift: LOCK",
    )
    expect_rejection(
        "reconciler-objective-substitution",
        substitute_reconciler_objective,
        "drill request reconciler authority drift: OBJECTIVES_WRITER",
    )
    expect_rejection(
        "reconciler-contract-substitution",
        substitute_reconciler_contract,
        "drill request reconciler authority drift: CONTRACT",
    )
    expect_rejection(
        "reconciler-generation-registry-substitution",
        substitute_reconciler_gen_registry,
        "drill request reconciler authority drift: GEN_REGISTRY",
    )
    expect_rejection(
        "reconciler-objectives-registry-substitution",
        substitute_reconciler_objectives_registry,
        "drill request reconciler authority drift: OBJECTIVES_REGISTRY",
    )
    expect_rejection(
        "reconciler-status-substitution",
        substitute_reconciler_status,
        "drill request reconciler authority drift: STATUS",
    )

    print("PASS: drill request executable/data/lock authority substitutions are rejected")
    print("PASS: substitution modules are isolated under operability fixtures, not canonical scripts")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
