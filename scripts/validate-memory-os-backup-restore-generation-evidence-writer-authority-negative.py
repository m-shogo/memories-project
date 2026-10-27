#!/usr/bin/env python3
"""Pin fail-closed rejection of generation-evidence executable/data authority substitution."""

from __future__ import annotations

import ast
import importlib.util
import inspect
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence-writer-authority.py"
EXPECTED_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence.py"
EXPECTED_NEGATIVE_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence-negative.py"
EXPECTED_SEMANTIC_NEGATIVE_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-semantic-generation-negative.py"
EXPECTED_CONTRACT = ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json"
EXPECTED_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
EXPECTED_GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
EXPECTED_GEN_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
EXPECTED_OBJECTIVES_REGISTRY = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
EXPECTED_OBJECTIVES_WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"
EXPECTED_DRILL_REQUEST_CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
EXPECTED_DRILL_REQUEST_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
EXPECTED_DRILL_REQUEST_WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
EXPECTED_GENERATION_BINDING = ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json"
EXPECTED_NON_RESURRECTION_CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
EXPECTED_NON_RESURRECTION_REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
EXPECTED_NON_RESURRECTION_WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
EXPECTED_INDEPENDENT_REVIEW_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-independent-review.py"
EXPECTED_LOCK = ROOT / "contracts/operations/.backup-restore-generation-evidence.lock"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"


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


def reject_generation_validator_substitutions() -> None:
    module = load_authority_validator("generation_evidence_validator_boundary")
    validator = module.load_generation_validator()
    require(EXPECTED_VALIDATOR.is_file(), "generation-evidence validator missing")
    expected = {
        "CONTRACT": EXPECTED_CONTRACT,
        "REGISTRY": EXPECTED_REGISTRY,
        "GEN_REGISTRY": EXPECTED_GEN_REGISTRY,
        "OBJECTIVES_REGISTRY": EXPECTED_OBJECTIVES_REGISTRY,
        "DRILL_CONTRACT": EXPECTED_DRILL_REQUEST_CONTRACT,
        "DRILL_REGISTRY": EXPECTED_DRILL_REQUEST_REGISTRY,
        "GEN_BINDING": EXPECTED_GENERATION_BINDING,
        "WRITER": ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py",
        "NEGATIVE_VALIDATOR": EXPECTED_NEGATIVE_VALIDATOR,
        "SEMANTIC_NEGATIVE_VALIDATOR": EXPECTED_SEMANTIC_NEGATIVE_VALIDATOR,
    }
    for name, canonical in expected.items():
        require(getattr(validator, name, None) == canonical, f"canonical generation-evidence validator {name} authority drift")
    substitutions = {
        "CONTRACT": EXPECTED_DRILL_REQUEST_CONTRACT,
        "REGISTRY": EXPECTED_DRILL_REQUEST_REGISTRY,
        "GEN_REGISTRY": EXPECTED_REGISTRY,
        "OBJECTIVES_REGISTRY": EXPECTED_GEN_REGISTRY,
        "DRILL_CONTRACT": EXPECTED_CONTRACT,
        "DRILL_REGISTRY": EXPECTED_OBJECTIVES_REGISTRY,
        "GEN_BINDING": EXPECTED_CONTRACT,
        "WRITER": EXPECTED_VALIDATOR,
        "NEGATIVE_VALIDATOR": EXPECTED_SEMANTIC_NEGATIVE_VALIDATOR,
        "SEMANTIC_NEGATIVE_VALIDATOR": EXPECTED_NEGATIVE_VALIDATOR,
    }
    for name, alternate in substitutions.items():
        original = getattr(validator, name)
        setattr(validator, name, alternate)
        try:
            try:
                module.require_generation_validator_authorities(validator)
            except module.Fail:
                print(f"PASS reject: generation-evidence validator {name} substitution")
            else:
                raise Fail(f"generation-evidence validator {name} substitution was accepted")
        finally:
            setattr(validator, name, original)
    try:
        module.require_generation_validator_authorities(validator)
    except module.Fail as exc:
        raise Fail(f"canonical generation-evidence validator authority rejected: {exc}") from exc


def repo_temp_module(prefix: str, overrides: dict[str, str]) -> tuple[Path, tuple[int, int], tuple[int, int]]:
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
        "import argparse",
        "from pathlib import Path",
        "ROOT = Path(__file__).resolve().parents[3]",
    ]
    for name, relative in values.items():
        lines.append(f"{name} = ROOT / {relative!r}")
    lines.extend(
        [
            "def canonical_repo_file(path, field):",
            "    path.resolve(strict=True).relative_to(ROOT.resolve())",
            "    return path",
            "def require_cli_authorities():",
            "    return None",
            "def main():",
            "    require_cli_authorities()",
            "    argparse.ArgumentParser()",
            "    return 0",
        ]
    )
    require(ROOT.is_dir() and not ROOT.is_symlink(), "generation-evidence temp root missing or symlinked")
    cursor = ROOT
    for part in ("docs", "fixtures", "memory-os-operability"):
        cursor = cursor / part
        require(cursor.is_dir() and not cursor.is_symlink(),
                "generation-evidence temp parent missing or symlinked")
    require(TMP_PARENT == cursor and TMP_PARENT.resolve(strict=True) == ROOT.resolve(strict=True) / "docs/fixtures/memory-os-operability",
            "generation-evidence temp parent canonical path drift")
    parent_stat = TMP_PARENT.stat()
    parent_identity = (parent_stat.st_dev, parent_stat.st_ino)
    fd, raw_path = tempfile.mkstemp(prefix=prefix, suffix=".py", dir=TMP_PARENT)
    path = Path(raw_path)
    created_stat = os.fstat(fd)
    created_identity = (created_stat.st_dev, created_stat.st_ino)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as owned:
            owned.write("\n".join(lines) + "\n")
    except BaseException:
        # Never delete a replacement if writing the exclusively created fixture fails.
        if path.is_file() and not path.is_symlink():
            current = path.stat()
            if (current.st_dev, current.st_ino) == created_identity:
                path.unlink()
        raise
    return path, parent_identity, created_identity


def expect_rejection(label: str, overrides: dict[str, str], expected_message: str) -> None:
    module = load_authority_validator(f"generation_evidence_writer_authority_negative_{label}")
    fake, parent_identity, created_identity = repo_temp_module(
        f".generation-evidence-authority-negative-{label}-", overrides
    )
    try:
        module.WRITER = fake
        try:
            module.main()
        except module.Fail as exc:
            require(expected_message in str(exc), f"{label}: unexpected rejection: {exc}")
        else:
            raise Fail(f"{label}: substituted authority was accepted")
    finally:
        require(TMP_PARENT.is_dir() and not TMP_PARENT.is_symlink(),
                "generation-evidence temp parent substituted before cleanup")
        current_parent = TMP_PARENT.stat()
        require((current_parent.st_dev, current_parent.st_ino) == parent_identity,
                "generation-evidence temp parent inode drift before cleanup")
        require(fake.is_file() and not fake.is_symlink(),
                "generation-evidence temp module substituted before cleanup")
        current = fake.stat()
        require((current.st_dev, current.st_ino) == created_identity,
                "generation-evidence temp module inode drift before cleanup")
        fake.unlink()


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


def require_snapshot_transport_reachability(writer_source: str, suite_source: str) -> None:
    """Bind both the writer's pinned snapshot call and the executable negative probe."""
    writer_tree = ast.parse(writer_source)
    require(len(writer_tree.body) == 1 and isinstance(writer_tree.body[0], ast.FunctionDef),
            "generation writer transaction source invalid")
    first = writer_tree.body[0].body[0]
    require(
        isinstance(first, ast.Assign)
        and len(first.targets) == 1
        and isinstance(first.targets[0], ast.Tuple)
        and [x.id for x in first.targets[0].elts if isinstance(x, ast.Name)]
            == ["original", "original_mode"]
        and isinstance(first.value, ast.Call)
        and isinstance(first.value.func, ast.Name)
        and first.value.func.id == "snapshot_registry_for_append"
        and not first.value.args and not first.value.keywords,
        "generation writer must snapshot through pinned bounded helper before publication",
    )
    suite_tree = ast.parse(suite_source)
    mains = [node for node in suite_tree.body if isinstance(node, ast.FunctionDef)
             and node.name == "main"]
    require(len(mains) == 1, "generation registry transaction negative main missing")
    calls = [node for node in mains[0].body if isinstance(node, ast.Expr)
             and isinstance(node.value, ast.Call)
             and isinstance(node.value.func, ast.Name)
             and node.value.func.id == "prove_pinned_registry_snapshot"
             and len(node.value.args) == 1
             and isinstance(node.value.args[0], ast.Name)
             and node.value.args[0].id == "writer"
             and not node.value.keywords]
    require(len(calls) == 1, "generation snapshot negative must be invoked directly by CI suite")


def prove_snapshot_transport_reachability() -> None:
    module = load_authority_validator("generation_snapshot_source_binding")
    writer = module.load_writer()
    source = inspect.getsource(writer.write_registry_transactionally)
    suite_path = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence-registry-transaction-negative.py"
    require(suite_path.is_file() and not suite_path.is_symlink(),
            "generation snapshot negative source missing or symlinked")
    require(suite_path.stat().st_size <= 1024 * 1024,
            "generation snapshot negative source too large")
    suite = suite_path.read_text(encoding="utf-8")
    require_snapshot_transport_reachability(source, suite)
    mutated_writer = source.replace("snapshot_registry_for_append()", "unsafe_read_bytes()", 1)
    require(mutated_writer != source, "generation snapshot mutation did not apply")
    try:
        require_snapshot_transport_reachability(mutated_writer, suite)
    except Fail as exc:
        require(str(exc) == "generation writer must snapshot through pinned bounded helper before publication",
                "generation snapshot writer mutation rejected at wrong boundary")
    else:
        raise Fail("generation writer unbounded snapshot mutation accepted")
    mutated_suite = suite.replace("    prove_pinned_registry_snapshot(writer)\n", "", 1)
    require(mutated_suite != suite, "generation snapshot negative call mutation did not apply")
    try:
        require_snapshot_transport_reachability(source, mutated_suite)
    except Fail as exc:
        require(str(exc) == "generation snapshot negative must be invoked directly by CI suite",
                "generation snapshot negative removal rejected at wrong boundary")
    else:
        raise Fail("generation snapshot negative call removal accepted")
    print("PASS: generation snapshot bounded helper and direct CI negative call are source-bound")


def main() -> int:
    require(AUTHORITY_VALIDATOR.is_file(), "authority validator missing")
    require(TMP_PARENT.is_dir(), "isolated operability fixture parent missing")
    reject_writer_cli_substitutions()
    reject_generation_validator_substitutions()
    prove_snapshot_transport_reachability()

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
    print("generation-evidence validator data/writer substitutions accepted: false")
    print("generation-evidence validator negative authority substitutions accepted: false")
    print("generation-evidence substitution modules isolated under operability fixtures: true")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
