#!/usr/bin/env python3
"""Pin fail-closed rejection of drill-request executable authority substitution."""

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
            raise Fail(f"{label}: substituted executable authority was accepted")
    finally:
        for path in cleanup:
            path.unlink(missing_ok=True)


def substitute_writer(module, cleanup: list[Path]) -> None:
    fake = repo_temp_module(
        ".drill-writer-authority-negative-",
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parents[1]\n"
        "ELIGIBILITY_HELPER = ROOT / 'scripts/validate-memory-os-backup-restore-drill-request.py'\n"
        "OBJECTIVES_WRITER = ROOT / 'scripts/register-memory-os-recovery-objectives.py'\n",
    )
    cleanup.append(fake)
    module.WRITER = fake


def substitute_reconciler_objective(module, cleanup: list[Path]) -> None:
    fake = repo_temp_module(
        ".drill-reconcile-authority-negative-",
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parents[1]\n"
        "WRITER = ROOT / 'scripts/request-memory-os-backup-restore-drill.py'\n"
        "VALIDATOR = ROOT / 'scripts/validate-memory-os-backup-restore-drill-request.py'\n"
        "ELIGIBILITY_HELPER = ROOT / 'scripts/memory_os_environment_generation_eligibility.py'\n"
        "OBJECTIVES_WRITER = ROOT / 'scripts/validate-memory-os-backup-restore-drill-request.py'\n",
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
        substitute_writer,
        "drill request eligibility helper authority drift",
    )
    expect_rejection(
        "reconciler-objective-substitution",
        substitute_reconciler_objective,
        "drill request reconciler authority drift: OBJECTIVES_WRITER",
    )

    print("PASS: drill request executable authority substitutions are rejected")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
