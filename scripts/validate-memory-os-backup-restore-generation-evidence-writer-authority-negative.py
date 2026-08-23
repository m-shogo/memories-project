#!/usr/bin/env python3
"""Pin fail-closed rejection of generation-evidence executable/data authority substitution."""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence-writer-authority.py"
EXPECTED_CONTRACT = ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json"
EXPECTED_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
EXPECTED_GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
EXPECTED_GEN_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
EXPECTED_OBJECTIVES_REGISTRY = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
EXPECTED_OBJECTIVES_WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"
EXPECTED_DRILL_REQUEST_CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
EXPECTED_DRILL_REQUEST_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
EXPECTED_DRILL_REQUEST_WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
EXPECTED_NON_RESURRECTION_CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
EXPECTED_NON_RESURRECTION_REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
EXPECTED_NON_RESURRECTION_WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
EXPECTED_INDEPENDENT_REVIEW_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-independent-review.py"
EXPECTED_LOCK = ROOT / "contracts/operations/.backup-restore-generation-evidence.lock"


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


def expect_writer_cli_rejection(writer, label: str, name: str, alternate: Path) -> None:
    original = getattr(writer, name)
    setattr(writer, name, alternate)
    try:
        try:
            writer.require_cli_authorities()
        except writer.Fail:
            return
        raise Fail(f"{label}: generation-evidence writer CLI substitution was accepted")
    finally:
        setattr(writer, name, original)


def reject_writer_cli_substitutions() -> None:
    module = load_authority_validator("generation_evidence_writer_cli_boundary")
    writer = module.load_writer()
    main_source = inspect.getsource(writer.main)
    guard_index = main_source.find("require_cli_authorities()")
    parser_index = main_source.find("argparse.ArgumentParser")
    require(guard_index >= 0, "generation-evidence writer CLI canonical authority guard missing")
    require(parser_index >= 0 and guard_index < parser_index, "generation-evidence writer CLI authority guard must run before argument parsing")

    expected = {
        "CONTRACT": EXPECTED_CONTRACT,
        "REGISTRY": EXPECTED_REGISTRY,
        "GEN_REGISTRY": EXPECTED_GEN_REGISTRY,
        "GEN_WRITER": EXPECTED_GEN_WRITER,
        "OBJECTIVES_REGISTRY": EXPECTED_OBJECTIVES_REGISTRY,
        "OBJECTIVES_WRITER": EXPECTED_OBJECTIVES_WRITER,
        "DRILL_REQUEST_CONTRACT": EXPECTED_DRILL_REQUEST_CONTRACT,
        "DRILL_REQUEST_REGISTRY": EXPECTED_DRILL_REQUEST_REGISTRY,
        "DRILL_REQUEST_WRITER": EXPECTED_DRILL_REQUEST_WRITER,
        "NON_RESURRECTION_CONTRACT": EXPECTED_NON_RESURRECTION_CONTRACT,
        "NON_RESURRECTION_REGISTRY": EXPECTED_NON_RESURRECTION_REGISTRY,
        "NON_RESURRECTION_WRITER": EXPECTED_NON_RESURRECTION_WRITER,
        "INDEPENDENT_REVIEW_VALIDATOR": EXPECTED_INDEPENDENT_REVIEW_VALIDATOR,
        "LOCK": EXPECTED_LOCK,
    }
    for name, canonical in expected.items():
        require(getattr(writer, name) == canonical, f"generation-evidence writer canonical {name} authority drift")

    substitutions = {
        "CONTRACT": EXPECTED_DRILL_REQUEST_CONTRACT,
        "REGISTRY": EXPECTED_DRILL_REQUEST_REGISTRY,
        "GEN_REGISTRY": EXPECTED_REGISTRY,
        "GEN_WRITER": ROOT / "scripts/validate-memory-os-production-equivalent-environment-generation.py",
        "OBJECTIVES_REGISTRY": EXPECTED_GEN_REGISTRY,
        "OBJECTIVES_WRITER": ROOT / "scripts/validate-memory-os-recovery-objectives.py",
        "DRILL_REQUEST_CONTRACT": EXPECTED_CONTRACT,
        "DRILL_REQUEST_REGISTRY": EXPECTED_OBJECTIVES_REGISTRY,
        "DRILL_REQUEST_WRITER": ROOT / "scripts/validate-memory-os-backup-restore-drill-request.py",
        "NON_RESURRECTION_CONTRACT": EXPECTED_CONTRACT,
        "NON_RESURRECTION_REGISTRY": EXPECTED_REGISTRY,
        "NON_RESURRECTION_WRITER": ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py",
        "INDEPENDENT_REVIEW_VALIDATOR": ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence.py",
        "LOCK": ROOT / "contracts/operations/.backup-restore-drill-request.lock",
    }
    for name, alternate in substitutions.items():
        expect_writer_cli_rejection(writer, name.lower(), name, alternate)

    try:
        writer.require_cli_authorities()
    except writer.Fail as exc:
        raise Fail(f"canonical generation-evidence writer CLI authority rejected: {exc}") from exc


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
        "INDEPENDENT_REVIEW_VALIDATOR": "scripts/validate-memory-os-backup-restore-generation-independent-review.py",
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


def expect_contract_ref_rejection(field: str, replacement: str, expected_message: str) -> None:
    module = load_authority_validator(f"generation_evidence_contract_ref_negative_{field}")
    canonical = module.load_contract()
    mutated = json.loads(json.dumps(canonical))
    mutated[field] = replacement
    original = module.load_contract
    try:
        module.load_contract = lambda: mutated
        try:
            module.main()
        except module.Fail as exc:
            require(expected_message in str(exc), f"{field}: unexpected rejection: {exc}")
        else:
            raise Fail(f"{field}: substituted contract review authority was accepted")
    finally:
        module.load_contract = original


def main() -> int:
    require(AUTHORITY_VALIDATOR.is_file(), "authority validator missing")
    reject_writer_cli_substitutions()

    cases = (
        ("contract", {"CONTRACT": "contracts/operations/backup-restore-drill-request-contract.v1.json"}, "generation-evidence contract authority drift"),
        ("registry", {"REGISTRY": "contracts/operations/backup-restore-drill-request-registry.v1.json"}, "generation-evidence registry authority drift"),
        ("generation-registry", {"GEN_REGISTRY": "contracts/operations/backup-restore-drill-request-registry.v1.json"}, "generation-evidence environment-generation registry authority drift"),
        ("generation-writer", {"GEN_WRITER": "scripts/validate-memory-os-production-equivalent-environment-generation.py"}, "generation-evidence environment-generation writer authority drift"),
        ("objectives-registry", {"OBJECTIVES_REGISTRY": "contracts/operations/production-equivalent-environment-generation-registry.v1.json"}, "generation-evidence recovery-objectives registry authority drift"),
        ("objectives-writer", {"OBJECTIVES_WRITER": "scripts/validate-memory-os-recovery-objectives.py"}, "generation-evidence recovery-objectives writer authority drift"),
        ("drill-request-contract", {"DRILL_REQUEST_CONTRACT": "contracts/operations/backup-restore-generation-evidence-contract.v1.json"}, "generation-evidence drill-request contract authority drift"),
        ("drill-request-registry", {"DRILL_REQUEST_REGISTRY": "contracts/operations/recovery-objectives-registry.v1.json"}, "generation-evidence drill-request registry authority drift"),
        ("drill-request-writer", {"DRILL_REQUEST_WRITER": "scripts/validate-memory-os-backup-restore-drill-request.py"}, "generation-evidence drill-request writer authority drift"),
        ("typed-contract", {"NON_RESURRECTION_CONTRACT": "contracts/operations/backup-restore-generation-evidence-contract.v1.json"}, "generation-evidence typed non-resurrection contract authority drift"),
        ("typed-registry", {"NON_RESURRECTION_REGISTRY": "contracts/operations/backup-restore-generation-evidence-registry.v1.json"}, "generation-evidence typed non-resurrection registry authority drift"),
        ("typed-writer", {"NON_RESURRECTION_WRITER": "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py"}, "generation-evidence typed non-resurrection writer authority drift"),
        ("independent-review-validator", {"INDEPENDENT_REVIEW_VALIDATOR": "scripts/validate-memory-os-backup-restore-generation-evidence.py"}, "generation-evidence independent-review validator authority drift"),
        ("append-lock", {"LOCK": "contracts/operations/.backup-restore-drill-request.lock"}, "generation-evidence append lock authority drift"),
    )
    for label, overrides, expected in cases:
        expect_rejection(label, overrides, expected)

    for field, replacement, expected in (
        (
            "independentReviewValidator",
            "scripts/validate-memory-os-backup-restore-generation-evidence.py",
            "contract independent-review validator ref drift",
        ),
        (
            "independentReviewNegativeValidator",
            "scripts/validate-memory-os-backup-restore-generation-evidence-negative.py",
            "contract independent-review negative validator ref drift",
        ),
        (
            "materialDeltaReviewValidator",
            "scripts/validate-memory-os-backup-restore-generation-evidence.py",
            "contract material-delta review validator ref drift",
        ),
        (
            "materialDeltaReviewNegativeValidator",
            "scripts/validate-memory-os-backup-restore-generation-evidence-negative.py",
            "contract material-delta review negative validator ref drift",
        ),
    ):
        expect_contract_ref_rejection(field, replacement, expected)

    print("PASS: complete generation-evidence executable/data/lock/review authority substitution matrix is rejected")
    print("generation-evidence writer CLI authority substitutions accepted: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
