#!/usr/bin/env python3
"""Pin fail-closed rejection of generation-evidence executable/data authority substitution."""

from __future__ import annotations

import importlib.util
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence-writer-authority.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_authority_validator(name: str):
    spec = importlib.util.spec_from_file_location(name, AUTHORITY_VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load generation-evidence authority validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def repo_temp_module(prefix: str, overrides: dict[str, str]) -> Path:
    values = {
        "CONTRACT": "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
        "REGISTRY": "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
        "GEN_REGISTRY": "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
        "GEN_WRITER": "scripts/register-memory-os-production-equivalent-environment-generation.py",
        "OBJECTIVES_REGISTRY": "contracts/operations/recovery-objectives-registry.v1.json",
        "OBJECTIVES_WRITER": "scripts/register-memory-os-recovery-objectives.py",
        "DRILL_REQUEST_CONTRACT": "contracts/operations/backup-restore-drill-request-contract.v1.json",
        "DRILL_REQUEST_REGISTRY": "contracts/operations/backup-restore-drill-request-registry.v1.json",
        "DRILL_REQUEST_WRITER": "scripts/request-memory-os-backup-restore-drill.py",
        "NON_RESURRECTION_CONTRACT": "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json",
        "NON_RESURRECTION_REGISTRY": "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
        "NON_RESURRECTION_WRITER": "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py",
        "LOCK": "contracts/operations/.backup-restore-generation-evidence.lock",
    }
    values.update(overrides)
    lines = [
        "from pathlib import Path",
        "ROOT = Path(__file__).resolve().parents[1]",
    ]
    for name, relative in values.items():
        lines.append(f"{name} = ROOT / {relative!r}")
    lines.extend(
        [
            "def canonical_repo_file(path, field):",
            "    path.resolve(strict=True).relative_to(ROOT.resolve())",
            "    return path",
        ]
    )
    fd, raw_path = tempfile.mkstemp(prefix=prefix, suffix=".py", dir=ROOT / "scripts")
    os.close(fd)
    path = Path(raw_path)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def expect_rejection(label: str, overrides: dict[str, str], expected_message: str) -> None:
    module = load_authority_validator(f"generation_evidence_writer_authority_negative_{label}")
    fake = repo_temp_module(f".generation-evidence-authority-negative-{label}-", overrides)
    try:
        module.WRITER = fake
        try:
            module.main()
        except module.Fail as exc:
            require(expected_message in str(exc), f"{label}: unexpected rejection: {exc}")
        else:
            raise Fail(f"{label}: substituted authority was accepted")
    finally:
        fake.unlink(missing_ok=True)


def main() -> int:
    require(AUTHORITY_VALIDATOR.is_file(), "authority validator missing")
    cases = (
        (
            "contract",
            {"CONTRACT": "contracts/operations/backup-restore-drill-request-contract.v1.json"},
            "generation-evidence contract authority drift",
        ),
        (
            "registry",
            {"REGISTRY": "contracts/operations/backup-restore-drill-request-registry.v1.json"},
            "generation-evidence registry authority drift",
        ),
        (
            "generation-registry",
            {"GEN_REGISTRY": "contracts/operations/backup-restore-drill-request-registry.v1.json"},
            "generation-evidence environment-generation registry authority drift",
        ),
        (
            "generation-writer",
            {"GEN_WRITER": "scripts/validate-memory-os-production-equivalent-environment-generation.py"},
            "generation-evidence environment-generation writer authority drift",
        ),
        (
            "objectives-registry",
            {"OBJECTIVES_REGISTRY": "contracts/operations/production-equivalent-environment-generation-registry.v1.json"},
            "generation-evidence recovery-objectives registry authority drift",
        ),
        (
            "objectives-writer",
            {"OBJECTIVES_WRITER": "scripts/validate-memory-os-recovery-objectives.py"},
            "generation-evidence recovery-objectives writer authority drift",
        ),
        (
            "drill-request-contract",
            {"DRILL_REQUEST_CONTRACT": "contracts/operations/backup-restore-generation-evidence-contract.v1.json"},
            "generation-evidence drill-request contract authority drift",
        ),
        (
            "drill-request-registry",
            {"DRILL_REQUEST_REGISTRY": "contracts/operations/recovery-objectives-registry.v1.json"},
            "generation-evidence drill-request registry authority drift",
        ),
        (
            "drill-request-writer",
            {"DRILL_REQUEST_WRITER": "scripts/validate-memory-os-backup-restore-drill-request.py"},
            "generation-evidence drill-request writer authority drift",
        ),
        (
            "typed-contract",
            {"NON_RESURRECTION_CONTRACT": "contracts/operations/backup-restore-generation-evidence-contract.v1.json"},
            "generation-evidence typed non-resurrection contract authority drift",
        ),
        (
            "typed-registry",
            {"NON_RESURRECTION_REGISTRY": "contracts/operations/backup-restore-generation-evidence-registry.v1.json"},
            "generation-evidence typed non-resurrection registry authority drift",
        ),
        (
            "typed-writer",
            {"NON_RESURRECTION_WRITER": "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py"},
            "generation-evidence typed non-resurrection writer authority drift",
        ),
        (
            "append-lock",
            {"LOCK": "contracts/operations/.backup-restore-drill-request.lock"},
            "generation-evidence append lock authority drift",
        ),
    )
    for label, overrides, expected in cases:
        expect_rejection(label, overrides, expected)

    print("PASS: complete generation-evidence executable/data/lock authority substitution matrix is rejected")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
