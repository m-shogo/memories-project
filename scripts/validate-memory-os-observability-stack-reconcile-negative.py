#!/usr/bin/env python3
"""Reject corrupt observability-stack authority without mutating canonical authority."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts/operations/observability-stack-deployment-registry.v1.json"
CONTRACT = ROOT / "contracts/operations/observability-stack-deployment-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
WRITER = ROOT / "scripts/register-memory-os-observability-stack-deployment.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-observability-stack-deployment.py"
TEMP_POST_SOURCE = ROOT / "docs/fixtures/memory-os-operability/.observability-stack-post-source-negative.tmp"
TEMP_SYMLINK = ROOT / "docs/fixtures/memory-os-operability/.observability-stack-symlink-negative.tmp"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def authority_snapshot(path: Path) -> tuple[bytes, int]:
    return path.read_bytes(), path.stat().st_mode & 0o7777


def require_canonical_unchanged(snapshots: dict[Path, tuple[bytes, int]], label: str) -> None:
    for path, (payload, mode) in snapshots.items():
        if path.read_bytes() != payload:
            raise RuntimeError(f"{label} mutated canonical bytes: {path.relative_to(ROOT)}")
        if path.stat().st_mode & 0o7777 != mode:
            raise RuntimeError(f"{label} mutated canonical mode: {path.relative_to(ROOT)}")


def expect_writer_rejected(writer, registry: dict, label: str) -> None:
    try:
        writer.validate_registry_for_append(registry, validate_rows=False)
    except writer.Fail:
        return
    raise RuntimeError(f"writer accepted corrupt observability stack registry: {label}")


def expect_writer_append_rollback(writer, registry: dict, snapshots: dict[Path, tuple[bytes, int]]) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-observability-writer-negative-") as temp_dir:
        run_registry = Path(temp_dir) / REGISTRY.name
        run_registry.write_bytes(REGISTRY.read_bytes())
        original_registry = writer.REGISTRY
        original_validator = writer.validate_registry_for_append
        calls = 0

        def injected_validator(value, *, validate_rows=True):
            nonlocal calls
            calls += 1
            if calls == 1:
                return None
            raise writer.Fail("injected post-append registry validation failure")

        candidate = copy.deepcopy(registry)
        candidate["appendOnly"] = False
        try:
            writer.REGISTRY = run_registry
            writer.validate_registry_for_append = injected_validator
            try:
                writer.commit_registry_candidate(registry, candidate)
            except writer.Fail:
                pass
            else:
                raise RuntimeError("writer accepted injected post-append registry validation failure")
            if run_registry.read_bytes() != REGISTRY.read_bytes():
                raise RuntimeError("post-append validation failure did not roll back run-local registry")
        finally:
            writer.REGISTRY = original_registry
            writer.validate_registry_for_append = original_validator
    require_canonical_unchanged(snapshots, "writer rollback negative")


def expect_ref_rejected(writer, ref: str, source: str, label: str) -> None:
    try:
        writer.source_bound_ref(ref, source, "negativeEvidenceRef")
    except writer.Fail:
        return
    raise RuntimeError(f"writer accepted invalid source-bound stack evidence: {label}")


def expect_generic_reviews_rejected(writer, source: str) -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    record = {
        "stackId": "obsstack_negative_review",
        "environmentIdentityDigest": "0" * 64,
        "securityReviewRef": "contracts/operations/production-operability-status.json",
        "operabilityReviewRef": "contracts/operations/observability-stack-deployment-contract.v1.json",
    }
    try:
        writer.validate_independent_reviews(record, source, contract)
    except writer.Fail:
        return
    raise RuntimeError("generic repository JSON files were accepted as typed observability independent reviews")


def expect_reconciler_authority_rejected(reconciler, snapshots: dict[Path, tuple[bytes, int]]) -> None:
    substitutions = (
        ("CONTRACT", reconciler.STATUS, "observability stack contract authority drift"),
        ("REGISTRY", reconciler.STATUS, "observability stack registry authority drift"),
        ("WRITER", reconciler.VALIDATOR, "observability stack writer authority drift"),
        ("VALIDATOR", reconciler.OPERABILITY_VALIDATOR, "observability stack validator authority drift"),
        ("OBSERVABILITY_VALIDATOR", reconciler.ACCESS_VALIDATOR, "observability validator authority drift"),
        ("ACCESS_VALIDATOR", reconciler.METRICS_VALIDATOR, "observability access validator authority drift"),
        ("METRICS_VALIDATOR", reconciler.METRICS_OPERATIONS_VALIDATOR, "metrics validator authority drift"),
        ("METRICS_OPERATIONS_VALIDATOR", reconciler.METRICS_ALERTING_VALIDATOR, "metrics operations validator authority drift"),
        ("METRICS_ALERTING_VALIDATOR", reconciler.METRICS_VALIDATOR, "metrics alerting validator authority drift"),
        ("OPERABILITY_VALIDATOR", reconciler.METRICS_VALIDATOR, "operability validator authority drift"),
        ("WORKFLOW", ROOT / ".github/workflows/incident-contact-routing-admission.yml", "observability stack workflow authority drift"),
        ("STATUS", reconciler.CONTRACT, "production operability status authority drift"),
    )
    for field, substitute, expected_message in substitutions:
        original = getattr(reconciler, field)
        try:
            setattr(reconciler, field, substitute)
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                if expected_message not in str(exc):
                    raise RuntimeError(f"{field} substitution rejected at wrong boundary: {exc}") from exc
            else:
                raise RuntimeError(f"reconciler accepted {field} authority substitution")
            require_canonical_unchanged(snapshots, f"{field} substitution")
        finally:
            setattr(reconciler, field, original)
    reconciler.enforce_runtime_authorities()


def expect_run_local_transaction_rollback(reconciler, snapshots: dict[Path, tuple[bytes, int]]) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-observability-pair-negative-") as temp_dir:
        temp = Path(temp_dir)
        run_contract = temp / CONTRACT.name
        run_status = temp / STATUS.name
        run_contract.write_bytes(CONTRACT.read_bytes())
        run_status.write_bytes(STATUS.read_bytes())
        run_contract.chmod(0o640)
        run_status.chmod(0o640)
        originals = (reconciler.CONTRACT, reconciler.STATUS, reconciler.POST_WRITE_VALIDATORS)
        original_replace = reconciler.os.replace
        try:
            reconciler.CONTRACT = run_contract
            reconciler.STATUS = run_status
            reconciler.POST_WRITE_VALIDATORS = ()
            reconciler.atomic_replace_bytes(run_contract, run_contract.read_bytes())
            reconciler.atomic_replace_bytes(run_status, run_status.read_bytes())
            if (run_contract.stat().st_mode & 0o7777, run_status.stat().st_mode & 0o7777) != (0o640, 0o640):
                raise RuntimeError("run-local successful atomic publication changed authority modes")

            before_contract = run_contract.read_bytes()
            before_status = run_status.read_bytes()
            replace_calls = 0

            def reject_second_replace(source, destination):
                nonlocal replace_calls
                replace_calls += 1
                if replace_calls == 2:
                    raise OSError("synthetic second authority replace rejection")
                return original_replace(source, destination)

            reconciler.os.replace = reject_second_replace
            try:
                reconciler.commit_validated_pair(
                    json.loads(before_contract.decode("utf-8")),
                    json.loads(before_status.decode("utf-8")),
                )
            except OSError as exc:
                if "synthetic second authority replace rejection" not in str(exc):
                    raise
            else:
                raise RuntimeError("observability pair publication accepted rejected second atomic replace")
            if run_contract.read_bytes() != before_contract or run_status.read_bytes() != before_status:
                raise RuntimeError("run-local second-replace failure did not roll back authority pair")
            leftovers = list(temp.glob(".*.tmp"))
            if leftovers:
                raise RuntimeError(f"run-local pair publication left temporary files: {leftovers}")
        finally:
            reconciler.os.replace = original_replace
            reconciler.CONTRACT, reconciler.STATUS, reconciler.POST_WRITE_VALIDATORS = originals
    require_canonical_unchanged(snapshots, "run-local transaction rollback negative")


def expect_run_local_post_validation_rollback(reconciler, snapshots: dict[Path, tuple[bytes, int]]) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-observability-validator-negative-") as temp_dir:
        temp = Path(temp_dir)
        run_contract = temp / CONTRACT.name
        run_status = temp / STATUS.name
        run_contract.write_bytes(CONTRACT.read_bytes())
        run_status.write_bytes(STATUS.read_bytes())
        failing_validator = temp / "failing-validator.py"
        failing_validator.write_text("raise SystemExit(1)\n", encoding="utf-8")
        originals = (reconciler.CONTRACT, reconciler.STATUS, reconciler.POST_WRITE_VALIDATORS)
        try:
            reconciler.CONTRACT = run_contract
            reconciler.STATUS = run_status
            reconciler.POST_WRITE_VALIDATORS = (failing_validator,)
            before_contract = run_contract.read_bytes()
            before_status = run_status.read_bytes()
            contract = json.loads(before_contract.decode("utf-8"))
            status = json.loads(before_status.decode("utf-8"))
            contract["currentAuthority"]["admittedStackCount"] = 987654
            try:
                reconciler.commit_validated_pair(contract, status)
            except reconciler.Fail as exc:
                if "failed validation" not in str(exc):
                    raise
            else:
                raise RuntimeError("run-local pair publication accepted post-write validator failure")
            if run_contract.read_bytes() != before_contract or run_status.read_bytes() != before_status:
                raise RuntimeError("run-local post-write validator failure did not roll back authority pair")
        finally:
            reconciler.CONTRACT, reconciler.STATUS, reconciler.POST_WRITE_VALIDATORS = originals
    require_canonical_unchanged(snapshots, "run-local post-validation rollback negative")


def create_descendant_commit() -> str:
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip()
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "observability-negative",
        "GIT_AUTHOR_EMAIL": "observability-negative@example.invalid",
        "GIT_COMMITTER_NAME": "observability-negative",
        "GIT_COMMITTER_EMAIL": "observability-negative@example.invalid",
    })
    return subprocess.check_output(
        ["git", "commit-tree", tree, "-p", "HEAD", "-m", "observability stack non-ancestor fixture"],
        cwd=ROOT,
        env=env,
        text=True,
    ).strip()


def main() -> int:
    writer = load_module("observability_stack_writer", WRITER)
    reconciler = load_module("observability_stack_reconcile_negative", RECONCILER)
    snapshots = {path: authority_snapshot(path) for path in (REGISTRY, CONTRACT, STATUS, WRITER, RECONCILER)}
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    cases = []
    for label, key, value in (
        ("boolean admitted count", "admittedStackCount", True),
        ("append-only disabled", "appendOnly", False),
        ("production ready escalation", "productionReady", True),
        ("registry schema drift", "schemaVersion", "memory-os-observability-stack-deployment-registry.v999"),
    ):
        candidate = copy.deepcopy(registry)
        candidate[key] = value
        cases.append((label, candidate))
    for label, candidate in cases:
        expect_writer_rejected(writer, candidate, label)

    expect_writer_append_rollback(writer, registry, snapshots)
    expect_reconciler_authority_rejected(reconciler, snapshots)
    expect_run_local_transaction_rollback(reconciler, snapshots)
    expect_run_local_post_validation_rollback(reconciler, snapshots)

    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if not writer.source_is_ancestor(source):
        raise RuntimeError("current HEAD must be accepted as source ancestor")
    descendant = create_descendant_commit()
    if writer.source_is_ancestor(descendant):
        raise RuntimeError("future descendant commit was accepted as source ancestor")
    expect_generic_reviews_rejected(writer, source)

    try:
        TEMP_POST_SOURCE.write_text("created after source commit\n", encoding="utf-8")
        expect_ref_rejected(writer, str(TEMP_POST_SOURCE.relative_to(ROOT)), source, "post-source evidence")
        try:
            TEMP_SYMLINK.symlink_to(ROOT / "README.md")
        except (OSError, NotImplementedError):
            pass
        else:
            expect_ref_rejected(writer, str(TEMP_SYMLINK.relative_to(ROOT)), source, "symlink evidence")
    finally:
        TEMP_POST_SOURCE.unlink(missing_ok=True)
        TEMP_SYMLINK.unlink(missing_ok=True)

    require_canonical_unchanged(snapshots, "complete observability reconcile negative suite")
    print("PASS: observability stack corrupt registry/source/review inputs are rejected read-only")
    print("PASS: observability reconciler rejects canonical authority substitutions without mutation")
    print("PASS: writer and pair rollback negatives mutate run-local copies only")
    print("PASS: second-replace and post-write validator failures roll back run-local authority bytes/modes")
    print("automatic production promotion authorized: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
