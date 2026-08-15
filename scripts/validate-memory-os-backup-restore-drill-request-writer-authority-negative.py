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


def repo_temp_module(prefix: str, content: str) -> Path:
    fd, raw_path = tempfile.mkstemp(prefix=prefix, suffix=".py", dir=ROOT / "scripts")
    os.close(fd)
    path = Path(raw_path)
    path.write_text(content, encoding="utf-8")
    return path


def expect_rejection(label: str, configure, expected_message: str) -> None:
    module = load_authority_validator(f"drill_writer_authority_negative_{label}")
    cleanup: list[Path] = []
    try:
        configure(module, cleanup)
        try:
            module.main()
        except module.Fail as exc:
            require(expected_message in str(exc), f"{label}: unexpected rejection: {exc}")
        else:
            raise Fail(f"{label}: substituted authority was accepted")
    finally:
        for path in cleanup:
            path.unlink(missing_ok=True)


def canonical_writer_module(*, eligibility: str = "memory_os_environment_generation_eligibility.py", registry: str = "contracts/operations/backup-restore-drill-request-registry.v1.json") -> str:
    return (
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parents[1]\n"
        "CONTRACT = ROOT / 'contracts/operations/backup-restore-drill-request-contract.v1.json'\n"
        f"REGISTRY = ROOT / '{registry}'\n"
        "GEN_REGISTRY = ROOT / 'contracts/operations/production-equivalent-environment-generation-registry.v1.json'\n"
        "OBJECTIVES_REGISTRY = ROOT / 'contracts/operations/recovery-objectives-registry.v1.json'\n"
        f"ELIGIBILITY_HELPER = ROOT / 'scripts/{eligibility}'\n"
        "OBJECTIVES_WRITER = ROOT / 'scripts/register-memory-os-recovery-objectives.py'\n"
    )


def canonical_reconciler_module(*, objectives_writer: str = "register-memory-os-recovery-objectives.py", status: str = "contracts/operations/production-operability-status.json") -> str:
    return (
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parents[1]\n"
        "CONTRACT = ROOT / 'contracts/operations/backup-restore-drill-request-contract.v1.json'\n"
        "REGISTRY = ROOT / 'contracts/operations/backup-restore-drill-request-registry.v1.json'\n"
        "GEN_REGISTRY = ROOT / 'contracts/operations/production-equivalent-environment-generation-registry.v1.json'\n"
        "OBJECTIVES_REGISTRY = ROOT / 'contracts/operations/recovery-objectives-registry.v1.json'\n"
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


def substitute_writer_registry(module, cleanup: list[Path]) -> None:
    fake = repo_temp_module(
        ".drill-writer-data-authority-negative-",
        canonical_writer_module(registry="contracts/operations/recovery-objectives-registry.v1.json"),
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

    expect_rejection(
        "writer-eligibility-substitution",
        substitute_writer_eligibility,
        "drill request writer authority drift: ELIGIBILITY_HELPER",
    )
    expect_rejection(
        "writer-registry-substitution",
        substitute_writer_registry,
        "drill request writer authority drift: REGISTRY",
    )
    expect_rejection(
        "reconciler-objective-substitution",
        substitute_reconciler_objective,
        "drill request reconciler authority drift: OBJECTIVES_WRITER",
    )
    expect_rejection(
        "reconciler-status-substitution",
        substitute_reconciler_status,
        "drill request reconciler authority drift: STATUS",
    )

    print("PASS: drill request executable/data authority substitutions are rejected")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
