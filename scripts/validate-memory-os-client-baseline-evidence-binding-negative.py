#!/usr/bin/env python3
"""Focused negative coverage for reviewed client evidence source binding and transactional authority rollback."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-client-baseline.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-client-baseline-registry.py"
CONTRACT = ROOT / "contracts/operations/client-baseline-registry-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/client-baseline-registry.v1.json"
EVIDENCE = ROOT / "docs/evidence/clients/README.md"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_writer() -> Any:
    return load_module(WRITER, "memory_os_client_baseline_writer_negative")


def head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    require(completed.returncode == 0, "cannot resolve HEAD")
    return completed.stdout.strip()


def expect_rejected(writer: Any, ref: str, source: str, expected: str) -> None:
    try:
        writer.validate_evidence_ref_at_source(ref, source, "negative")
    except writer.Failure as exc:
        require(expected in str(exc), f"unexpected rejection: {exc}")
        return
    raise RuntimeError(f"client evidence corruption was accepted: {expected}")


def expect_registry_rejected(writer: Any, base: dict[str, Any], label: str,
                             mutate: Callable[[dict[str, Any]], None]) -> None:
    candidate = copy.deepcopy(base)
    mutate(candidate)
    try:
        writer.validate_registry_for_append(candidate)
    except writer.Failure:
        return
    raise RuntimeError(f"historical client semantic corruption was accepted: {label}")


def synthetic_registry(writer: Any, source: str, evidence_ref: str) -> dict[str, Any]:
    base = json.loads(REGISTRY.read_text(encoding="utf-8"))
    record = {
        "schemaVersion": "memory-os-client-baseline-record.v1",
        "clientBaselineId": "clb_20260818_synthetic",
        "clientClass": "IOS_APP",
        "marketingVersion": "1.0.0",
        "buildNumber": "1",
        "sourceCommitSha": source,
        "artifactKind": "IOS_IPA",
        "artifactSha256": "0" * 64,
        "artifactByteLength": 1,
        "approvedAt": "2026-08-18T00:00:00Z",
        "approvalClass": "REVIEWED_CLIENT_BASELINE",
        "approvers": [
            {"role": "CLIENT_OWNER", "approverRef": "apr_client001"},
            {"role": "SECURITY_REVIEWER", "approverRef": "apr_security02"},
            {"role": "COMPATIBILITY_REVIEWER", "approverRef": "apr_compat003"},
        ],
        "apiMajor": "v1",
        "apiContractSha256": "1" * 64,
        "signedUploadContract": "memory-os-signed-upload.v1",
        "clientBehaviorContractSha256": "2" * 64,
        "buildProvenanceEvidenceRefs": [evidence_ref],
        "securityEvidenceRefs": [evidence_ref],
        "compatibilityEvidenceRefs": [evidence_ref],
        "artifactRetentionEvidenceRefs": [evidence_ref],
        "evidenceComplete": True,
        "approvedForPairing": True,
        "productionEvidence": False,
        "productionReady": False,
    }
    base["clients"] = [record]
    base["approvedClientBaselineCount"] = 1
    base["latestApprovedClientByClass"] = {
        "IOS_APP": record["clientBaselineId"],
        "PORTAL": None,
    }
    writer.validate_registry_for_append(copy.deepcopy(base))
    return base


def prove_historical_semantics(writer: Any, source: str, evidence_ref: str) -> None:
    base = synthetic_registry(writer, source, evidence_ref)
    expect_registry_rejected(
        writer, base, "duplicate approver",
        lambda value: value["clients"][0]["approvers"].__setitem__(
            1, copy.deepcopy(value["clients"][0]["approvers"][0])
        ),
    )
    expect_registry_rejected(
        writer, base, "approvedForPairing false",
        lambda value: value["clients"][0].__setitem__("approvedForPairing", False),
    )
    expect_registry_rejected(
        writer, base, "evidenceComplete false",
        lambda value: value["clients"][0].__setitem__("evidenceComplete", False),
    )
    expect_registry_rejected(
        writer, base, "API major drift",
        lambda value: value["clients"][0].__setitem__("apiMajor", "v2"),
    )
    expect_registry_rejected(
        writer, base, "client artifact kind mismatch",
        lambda value: value["clients"][0].__setitem__("artifactKind", "PORTAL_BUNDLE"),
    )
    expect_registry_rejected(
        writer, base, "production readiness promotion",
        lambda value: value["clients"][0].__setitem__("productionReady", True),
    )


def prove_contract_rollback_guard(writer: Any) -> None:
    original = CONTRACT.read_bytes()
    candidate = json.loads(original.decode("utf-8"))
    candidate["appendMustRevalidateCanonicalRegistryAndRollbackOnFailure"] = False
    try:
        CONTRACT.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
        try:
            writer.validate_contract_authority()
        except writer.Failure as exc:
            require("append rollback authority drift" in str(exc),
                    f"unexpected contract guard rejection: {exc}")
        else:
            raise RuntimeError("client append rollback contract guard weakening was accepted")
    finally:
        CONTRACT.write_bytes(original)


def prove_append_rollback(writer: Any) -> None:
    original = REGISTRY.read_bytes()
    original_mode = stat.S_IMODE(REGISTRY.stat().st_mode)
    candidate = json.loads(original.decode("utf-8"))
    candidate["approvedClientBaselineCount"] = 999
    original_validator = writer.validate_registry_for_append

    def controlled_validator(_value: dict[str, Any]) -> None:
        raise writer.Failure("synthetic post-append client registry validation failure")

    try:
        os.chmod(REGISTRY, 0o640)
        test_mode = stat.S_IMODE(REGISTRY.stat().st_mode)
        writer.validate_registry_for_append = controlled_validator
        try:
            writer.append_registry_transactionally(candidate, original, test_mode)
        except writer.Failure as exc:
            require("synthetic post-append client registry validation failure" in str(exc),
                    f"unexpected append rollback failure: {exc}")
        else:
            raise RuntimeError("client registry append unexpectedly succeeded after synthetic post-write failure")
        require(REGISTRY.read_bytes() == original,
                "client registry append rollback did not restore original bytes")
        require(stat.S_IMODE(REGISTRY.stat().st_mode) == test_mode,
                "client registry append rollback did not restore original mode")
        require(not list(REGISTRY.parent.glob(".client-baseline-registry.*.tmp")),
                "client registry append rollback left temporary residue")
    finally:
        writer.validate_registry_for_append = original_validator
        REGISTRY.write_bytes(original)
        os.chmod(REGISTRY, original_mode)


def prove_replace_rejection(writer: Any) -> None:
    original = REGISTRY.read_bytes()
    original_mode = stat.S_IMODE(REGISTRY.stat().st_mode)
    candidate = json.loads(original.decode("utf-8"))
    candidate["approvedClientBaselineCount"] = 999
    original_replace = writer.os.replace

    def reject_replace(source: str | os.PathLike[str], destination: str | os.PathLike[str]) -> None:
        raise OSError("synthetic client registry replace rejection")

    try:
        os.chmod(REGISTRY, 0o640)
        test_mode = stat.S_IMODE(REGISTRY.stat().st_mode)
        writer.os.replace = reject_replace
        try:
            writer.append_registry_transactionally(candidate, original, test_mode)
        except OSError as exc:
            require("synthetic client registry replace rejection" in str(exc),
                    f"unexpected client replace rejection: {exc}")
        else:
            raise RuntimeError("client registry replace rejection was ignored")
        require(REGISTRY.read_bytes() == original,
                "client registry replace rejection mutated canonical bytes")
        require(stat.S_IMODE(REGISTRY.stat().st_mode) == test_mode,
                "client registry replace rejection mutated canonical mode")
        require(not list(REGISTRY.parent.glob(".client-baseline-registry.*.tmp")),
                "client registry replace rejection left temporary residue")
    finally:
        writer.os.replace = original_replace
        REGISTRY.write_bytes(original)
        os.chmod(REGISTRY, original_mode)


def prove_reconcile_authority_substitution() -> None:
    reconciler = load_module(RECONCILER, "memory_os_client_baseline_reconciler_authority_negative")
    authority_names = (
        "CONTRACT",
        "REGISTRY",
        "SUPPORT",
        "RELEASES",
        "RELEASE_PAIRS",
        "SKEW",
        "STATUS",
        "WRITER",
        "PAIR_WRITER",
        "VALIDATOR",
        "SUPPORT_VALIDATOR",
        "OPERABILITY_VALIDATOR",
        "WORKFLOW",
        "RUNBOOK",
    )
    originals = {name: getattr(reconciler, name) for name in authority_names}
    replacements = {
        "CONTRACT": originals["REGISTRY"],
        "REGISTRY": originals["CONTRACT"],
        "SUPPORT": originals["CONTRACT"],
        "RELEASES": originals["RELEASE_PAIRS"],
        "RELEASE_PAIRS": originals["RELEASES"],
        "SKEW": originals["REGISTRY"],
        "STATUS": originals["CONTRACT"],
        "WRITER": originals["PAIR_WRITER"],
        "PAIR_WRITER": originals["WRITER"],
        "VALIDATOR": originals["SUPPORT_VALIDATOR"],
        "SUPPORT_VALIDATOR": originals["VALIDATOR"],
        "OPERABILITY_VALIDATOR": originals["VALIDATOR"],
        "WORKFLOW": originals["RUNBOOK"],
        "RUNBOOK": originals["WORKFLOW"],
    }
    canonical_contract = originals["CONTRACT"]
    canonical_status = originals["STATUS"]
    contract_before = canonical_contract.read_bytes()
    status_before = canonical_status.read_bytes()

    for name in authority_names:
        setattr(reconciler, name, replacements[name])
        try:
            try:
                reconciler.enforce_runtime_authorities()
            except reconciler.Fail as exc:
                require("authority drift" in str(exc),
                        f"unexpected {name} authority rejection: {exc}")
            else:
                raise RuntimeError(f"client baseline reconciler accepted substituted authority: {name}")
            require(canonical_contract.read_bytes() == contract_before,
                    f"rejected {name} substitution mutated canonical client baseline contract")
            require(canonical_status.read_bytes() == status_before,
                    f"rejected {name} substitution mutated canonical production status")
        finally:
            setattr(reconciler, name, originals[name])


def prove_reconcile_rollback() -> None:
    reconciler = load_module(RECONCILER, "memory_os_client_baseline_reconciler_negative")
    paths = (reconciler.CONTRACT, reconciler.SUPPORT, reconciler.STATUS)
    original = {path: path.read_bytes() for path in paths}
    observed_post_write_failure = False

    def controlled_validator(path: Path, label: str) -> None:
        nonlocal observed_post_write_failure
        if label == "post-write operability validator":
            observed_post_write_failure = True
            raise reconciler.Fail("synthetic post-write operability validation failure")

    reconciler.run_validator = controlled_validator
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require(
                "synthetic post-write operability validation failure" in str(exc),
                f"unexpected reconcile failure: {exc}",
            )
        else:
            raise RuntimeError("client baseline reconcile unexpectedly succeeded after synthetic post-write failure")
        require(observed_post_write_failure, "synthetic post-write validator was not reached")
        for path in paths:
            require(
                path.read_bytes() == original[path],
                f"client reconcile rollback changed canonical authority: {path.relative_to(ROOT)}",
            )
    finally:
        for path in paths:
            if path.read_bytes() != original[path]:
                path.write_bytes(original[path])


def main() -> int:
    writer = load_writer()
    source = head()
    ref = str(EVIDENCE.relative_to(ROOT))
    original = EVIDENCE.read_bytes()

    writer.validate_evidence_ref_at_source(ref, source, "positive")
    prove_historical_semantics(writer, source, ref)

    try:
        EVIDENCE.write_bytes(original + b"\nsource-binding-negative\n")
        expect_rejected(writer, ref, source, "changed after source commit")
    finally:
        EVIDENCE.write_bytes(original)

    temporary = ROOT / "docs/evidence/clients/.client-evidence-post-source-negative.json"
    try:
        temporary.write_text("{}\n", encoding="utf-8")
        expect_rejected(
            writer,
            str(temporary.relative_to(ROOT)),
            source,
            "must be tracked",
        )
    finally:
        temporary.unlink(missing_ok=True)

    prove_contract_rollback_guard(writer)
    prove_append_rollback(writer)
    prove_replace_rejection(writer)
    prove_reconcile_authority_substitution()
    prove_reconcile_rollback()

    require(EVIDENCE.read_bytes() == original, "client evidence fixture was not restored")
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    require(status.returncode == 0 and status.stdout.strip() == "",
            "negative suite left working-tree changes")
    print("PASS: client baseline historical semantics, evidence binding, authority identity, mode-safe append rollback/replace rejection and reconcile rollback are fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
