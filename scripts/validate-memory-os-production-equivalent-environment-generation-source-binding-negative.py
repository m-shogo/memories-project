#!/usr/bin/env python3
"""Prove generation records and referenced evidence remain byte-bound to sourceCommitSha."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"
WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
ENVIRONMENT_RECORD_FIXTURE = ROOT / "scripts/memory_os_environment_generation_eligibility.py"
SOURCE_BINDING_RULE = "allNonNullEnvironmentEvidenceRefsMustMatchSourceCommitSha"
ENVIRONMENT_RECORD_BINDING_RULE = "environmentRecordMustMatchSourceCommitSha"
EVIDENCE_CASES: tuple[tuple[str, Path], ...] = (
    ("postgresql.restoreEvidenceRef", ROOT / "README.md"),
    ("objectStorage.restoreEvidenceRef", ROOT / "SECURITY.md"),
    ("network.latencyProfileRef", ROOT / "services/import-api/README.md"),
    ("network.failureInjectionRef", ROOT / "scripts/validate-memory-os-operability.py"),
    ("identityAndSecrets.credentialScopeRef", ROOT / "scripts/validate-memory-os-production-equivalent-environment-record.py"),
    ("backupRestore.evidenceRef", ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"),
    ("materialDeltas[0].independentReviewRef", ROOT / ".github/workflows/operability-contracts.yml"),
    ("evidenceBoundary.independentReviewRef", ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"),
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_source_binding_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load generation writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_contract() -> dict[str, Any]:
    try:
        value = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load generation contract: {exc}") from exc
    require(isinstance(value, dict), "generation contract root must be object")
    return value


def head_sha() -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(completed.returncode == 0, "cannot resolve HEAD")
    value = completed.stdout.strip()
    require(len(value) == 40, "HEAD must be full SHA")
    return value


def expect_rejected(writer: Any, name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except writer.Fail:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name}: leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"{name}: source-bound authority drift unexpectedly accepted")


def evidence_env(refs: tuple[str, ...]) -> dict[str, Any]:
    require(len(refs) == len(EVIDENCE_CASES), "source-binding evidence fixture count drift")
    return {
        "postgresql": {"restoreEvidenceRef": refs[0]},
        "objectStorage": {"restoreEvidenceRef": refs[1]},
        "network": {"latencyProfileRef": refs[2], "failureInjectionRef": refs[3]},
        "identityAndSecrets": {"credentialScopeRef": refs[4]},
        "backupRestore": {"evidenceRef": refs[5]},
        "materialDeltas": [{"independentReviewRef": refs[6]}],
        "evidenceBoundary": {"independentReviewRef": refs[7]},
    }


def main() -> int:
    require(
        CONTRACT.is_file() and WRITER.is_file() and ENVIRONMENT_RECORD_FIXTURE.is_file(),
        "generation source-binding authority fixture missing",
    )
    require(all(path.is_file() for _, path in EVIDENCE_CASES), "generation source-binding evidence fixture missing")
    contract = load_contract()
    bindings = contract.get("bindingRules")
    require(isinstance(bindings, dict), "generation bindingRules required")
    require(bindings.get(SOURCE_BINDING_RULE) is True, f"generation contract must require {SOURCE_BINDING_RULE}")
    require(
        bindings.get(ENVIRONMENT_RECORD_BINDING_RULE) is True,
        f"generation contract must require {ENVIRONMENT_RECORD_BINDING_RULE}",
    )

    writer = load_writer()
    source = head_sha()
    refs = tuple(path.relative_to(ROOT).as_posix() for _, path in EVIDENCE_CASES)
    require(len(set(refs)) == len(refs), "source-binding negative suite requires distinct evidence refs")
    env = evidence_env(refs)

    writer.require_repo_file_bound_to_source(source, ENVIRONMENT_RECORD_FIXTURE, "environmentRecordRef")
    print("PASS accept: unchanged environment record fixture matches sourceCommitSha")
    environment_original = ENVIRONMENT_RECORD_FIXTURE.read_bytes()
    try:
        ENVIRONMENT_RECORD_FIXTURE.write_bytes(environment_original + b"\nsource-binding-negative-environment-record-mutation\n")
        expect_rejected(
            writer,
            "environmentRecordRef changed after sourceCommitSha",
            lambda: writer.require_repo_file_bound_to_source(source, ENVIRONMENT_RECORD_FIXTURE, "environmentRecordRef"),
        )
    finally:
        ENVIRONMENT_RECORD_FIXTURE.write_bytes(environment_original)
    require(
        ENVIRONMENT_RECORD_FIXTURE.read_bytes() == environment_original,
        "source-binding negative suite failed to restore environment record fixture",
    )

    writer.require_environment_evidence_bound_to_source(source, env)
    print("PASS accept: all unchanged repository evidence fields match sourceCommitSha")

    originals = {path: path.read_bytes() for _, path in EVIDENCE_CASES}
    for field, path in EVIDENCE_CASES:
        original = originals[path]
        try:
            path.write_bytes(original + b"\nsource-binding-negative-mutation\n")
            expect_rejected(
                writer,
                f"{field} changed after sourceCommitSha",
                lambda: writer.require_environment_evidence_bound_to_source(source, env),
            )
        finally:
            path.write_bytes(original)
        require(path.read_bytes() == original, f"source-binding negative suite failed to restore fixture: {field}")

    require(all(path.read_bytes() == original for path, original in originals.items()), "source-binding negative suite left a canonical evidence fixture mutated")
    print("Environment generation source-binding negative suite PASS")
    print("environment record independently source-bound: true")
    print(f"independently source-bound evidence fields tested: {len(EVIDENCE_CASES)}")
    print("source-binding fixtures are immutable validator/source files, not reconciled derived authority: true")
    print("source-bound environment record contract rule required: true")
    print("source-bound evidence contract rule required: true")
    print("source-bound authority mutation accepted: false")
    print("canonical evidence left mutated: false")
    print("generation created: false")
    print("production evidence: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT GENERATION SOURCE-BINDING NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
