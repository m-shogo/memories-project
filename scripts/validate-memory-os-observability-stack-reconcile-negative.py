#!/usr/bin/env python3
"""Reject corrupt observability-stack authority before reconcile mutation."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts/operations/observability-stack-deployment-registry.v1.json"
CONTRACT = ROOT / "contracts/operations/observability-stack-deployment-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
WRITER = ROOT / "scripts/register-memory-os-observability-stack-deployment.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-observability-stack-deployment.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-observability-stack-deployment.py"
TEMP_POST_SOURCE = ROOT / "docs/fixtures/memory-os-operability/.observability-stack-post-source-negative.tmp"
TEMP_SYMLINK = ROOT / "docs/fixtures/memory-os-operability/.observability-stack-symlink-negative.tmp"
POST_WRITE_MARKER = Path("/tmp/memory-os-observability-stack-post-write-negative.count")


def load_writer():
    spec = importlib.util.spec_from_file_location("observability_stack_writer", WRITER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load observability stack writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_writer_rejected(writer, registry, label: str) -> None:
    try:
        writer.validate_registry_for_append(registry, validate_rows=False)
    except writer.Fail:
        return
    raise RuntimeError(f"writer accepted corrupt observability stack registry: {label}")


def expect_writer_append_rollback(writer, registry, registry_bytes: bytes) -> None:
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
        writer.validate_registry_for_append = injected_validator
        try:
            writer.commit_registry_candidate(registry, candidate)
        except writer.Fail:
            pass
        else:
            raise RuntimeError("writer accepted injected post-append registry validation failure")
        if REGISTRY.read_bytes() != registry_bytes:
            raise RuntimeError("post-append validation failure left observability stack registry mutated")
    finally:
        writer.validate_registry_for_append = original_validator
        REGISTRY.write_bytes(registry_bytes)


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


def expect_validator_rejected(label: str) -> None:
    completed = subprocess.run(
        ["python", str(VALIDATOR)],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode != 0:
        return
    raise RuntimeError(f"validator accepted corrupt observability stack authority: {label}")


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


def expect_post_write_rollback(contract_bytes: bytes, status_bytes: bytes) -> None:
    validator_bytes = VALIDATOR.read_bytes()
    wrapper = f'''#!/usr/bin/env python3
from pathlib import Path
marker = Path({str(POST_WRITE_MARKER)!r})
count = int(marker.read_text(encoding="utf-8")) if marker.exists() else 0
marker.write_text(str(count + 1), encoding="utf-8")
raise SystemExit(0 if count == 0 else 1)
'''
    try:
        POST_WRITE_MARKER.unlink(missing_ok=True)
        VALIDATOR.write_text(wrapper, encoding="utf-8")
        completed = subprocess.run(
            ["python", str(RECONCILER)],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if completed.returncode == 0:
            raise RuntimeError("reconciler accepted injected post-write validator failure")
        if CONTRACT.read_bytes() != contract_bytes:
            raise RuntimeError("post-write validator failure left observability stack contract mutated")
        if STATUS.read_bytes() != status_bytes:
            raise RuntimeError("post-write validator failure left production operability status mutated")
    finally:
        VALIDATOR.write_bytes(validator_bytes)
        POST_WRITE_MARKER.unlink(missing_ok=True)
        CONTRACT.write_bytes(contract_bytes)
        STATUS.write_bytes(status_bytes)


def main() -> int:
    writer = load_writer()
    registry_bytes = REGISTRY.read_bytes()
    contract_bytes = CONTRACT.read_bytes()
    status_bytes = STATUS.read_bytes()
    registry = json.loads(registry_bytes.decode("utf-8"))

    cases = []
    candidate = copy.deepcopy(registry)
    candidate["admittedStackCount"] = True
    cases.append(("boolean admitted count", candidate))
    candidate = copy.deepcopy(registry)
    candidate["appendOnly"] = False
    cases.append(("append-only disabled", candidate))
    candidate = copy.deepcopy(registry)
    candidate["productionReady"] = True
    cases.append(("production ready escalation", candidate))
    candidate = copy.deepcopy(registry)
    candidate["schemaVersion"] = "memory-os-observability-stack-deployment-registry.v999"
    cases.append(("registry schema drift", candidate))

    for label, candidate in cases:
        expect_writer_rejected(writer, candidate, label)

    expect_writer_append_rollback(writer, registry, registry_bytes)

    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if not writer.source_is_ancestor(source):
        raise RuntimeError("current HEAD must be accepted as source ancestor")
    descendant = create_descendant_commit()
    if writer.source_is_ancestor(descendant):
        raise RuntimeError("future descendant commit was accepted as source ancestor")
    expect_generic_reviews_rejected(writer, source)

    try:
        contract = json.loads(contract_bytes.decode("utf-8"))
        contract["appendLockPath"] = "contracts/operations/.observability-stack-deployment-alternate.lock"
        CONTRACT.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
        expect_validator_rejected("append lock binding drift")
    finally:
        CONTRACT.write_bytes(contract_bytes)

    try:
        TEMP_POST_SOURCE.write_text("created after source commit\n", encoding="utf-8")
        expect_ref_rejected(
            writer,
            str(TEMP_POST_SOURCE.relative_to(ROOT)),
            source,
            "post-source evidence",
        )
        try:
            TEMP_SYMLINK.symlink_to(ROOT / "README.md")
        except (OSError, NotImplementedError):
            pass
        else:
            expect_ref_rejected(
                writer,
                str(TEMP_SYMLINK.relative_to(ROOT)),
                source,
                "symlink evidence",
            )
    finally:
        TEMP_POST_SOURCE.unlink(missing_ok=True)
        TEMP_SYMLINK.unlink(missing_ok=True)

    try:
        corrupted = copy.deepcopy(registry)
        corrupted["admittedStackCount"] = True
        REGISTRY.write_text(json.dumps(corrupted, indent=2) + "\n", encoding="utf-8")
        completed = subprocess.run(
            ["python", str(RECONCILER)],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if completed.returncode == 0:
            raise RuntimeError("reconciler accepted corrupt observability stack registry")
        if CONTRACT.read_bytes() != contract_bytes:
            raise RuntimeError("rejected reconcile mutated observability stack contract")
        if STATUS.read_bytes() != status_bytes:
            raise RuntimeError("rejected reconcile mutated production operability status")
    finally:
        REGISTRY.write_bytes(registry_bytes)
        CONTRACT.write_bytes(contract_bytes)
        STATUS.write_bytes(status_bytes)

    expect_post_write_rollback(contract_bytes, status_bytes)

    print("PASS: observability stack registry/source-binding/review/lock corruption is rejected without mutation")
    print("PASS: observability stack direct append rolls back on post-append validation failure")
    print("PASS: observability stack post-write validation failure rolls back contract and status")
    print("generic repository JSON accepted as independent review: false")
    print("automatic production promotion authorized: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
