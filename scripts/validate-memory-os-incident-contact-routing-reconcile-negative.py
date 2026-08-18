#!/usr/bin/env python3
"""Reject corrupt contact-routing authority before append/reconcile mutation."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts/operations/incident-contact-routing-admission-registry.v1.json"
OBS_REGISTRY = ROOT / "contracts/operations/observability-stack-deployment-registry.v1.json"
CONTRACT = ROOT / "contracts/operations/incident-contact-routing-admission-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
WRITER = ROOT / "scripts/register-memory-os-incident-contact-routing.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-incident-contact-routing.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-incident-contact-routing.py"
TEMP_POST_SOURCE = ROOT / "docs/fixtures/memory-os-operability/.incident-contact-routing-post-source-negative.tmp"
TEMP_SYMLINK = ROOT / "docs/fixtures/memory-os-operability/.incident-contact-routing-symlink-negative.tmp"
POST_WRITE_MARKER = Path("/tmp/memory-os-incident-contact-routing-post-write-negative.count")


def load_writer():
    spec = importlib.util.spec_from_file_location("incident_contact_routing_writer", WRITER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load contact routing writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_writer_rejected(writer, registry, label: str) -> None:
    try:
        writer.validate_registry_for_append(registry, validate_rows=False)
    except writer.Fail:
        return
    raise RuntimeError(f"writer accepted corrupt contact routing registry: {label}")


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
            raise RuntimeError("writer accepted injected post-append contact-routing registry validation failure")
        if REGISTRY.read_bytes() != registry_bytes:
            raise RuntimeError("post-append validation failure left contact-routing registry mutated")
    finally:
        writer.validate_registry_for_append = original_validator
        REGISTRY.write_bytes(registry_bytes)


def expect_ref_rejected(writer, ref: str, source: str, label: str) -> None:
    try:
        writer.source_bound_ref(ref, source, "negativeEvidenceRef")
    except writer.Fail:
        return
    raise RuntimeError(f"writer accepted invalid source-bound evidence: {label}")


def expect_generic_reviews_rejected(writer, source: str) -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    record = {
        "contactRoutingId": "icr_negative_review",
        "observabilityStackId": "obsstack_negative_review",
        "environmentIdentityDigest": "0" * 64,
        "privacyReviewRef": "contracts/operations/production-operability-status.json",
        "operabilityReviewRef": "contracts/operations/incident-contact-routing-admission-contract.v1.json",
    }
    try:
        writer.validate_independent_reviews(record, source, contract)
    except writer.Fail:
        return
    raise RuntimeError("generic repository JSON files were accepted as typed contact-routing independent reviews")


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
    raise RuntimeError(f"validator accepted corrupt contact-routing authority: {label}")


def create_descendant_commit() -> str:
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip()
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "incident-negative",
        "GIT_AUTHOR_EMAIL": "incident-negative@example.invalid",
        "GIT_COMMITTER_NAME": "incident-negative",
        "GIT_COMMITTER_EMAIL": "incident-negative@example.invalid",
    })
    return subprocess.check_output(
        ["git", "commit-tree", tree, "-p", "HEAD", "-m", "incident contact routing non-ancestor fixture"],
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
            raise RuntimeError("post-write validator failure left contact routing contract mutated")
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
    observability_registry_bytes = OBS_REGISTRY.read_bytes()
    contract_bytes = CONTRACT.read_bytes()
    status_bytes = STATUS.read_bytes()
    registry = json.loads(registry_bytes.decode("utf-8"))

    cases = []
    candidate = copy.deepcopy(registry)
    candidate["admittedRoutingCount"] = True
    cases.append(("boolean admitted count", candidate))
    candidate = copy.deepcopy(registry)
    candidate["appendOnly"] = False
    cases.append(("append-only disabled", candidate))
    candidate = copy.deepcopy(registry)
    candidate["productionReady"] = True
    cases.append(("production ready escalation", candidate))
    candidate = copy.deepcopy(registry)
    candidate["schemaVersion"] = "memory-os-incident-contact-routing-admission-registry.v999"
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
        contract["appendLockPath"] = "contracts/operations/.incident-contact-routing-alternate.lock"
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
        observability_registry = json.loads(observability_registry_bytes.decode("utf-8"))
        observability_registry["admittedStackCount"] = True
        OBS_REGISTRY.write_text(json.dumps(observability_registry, indent=2) + "\n", encoding="utf-8")
        try:
            writer.observability_stack("obsstack_missing_negative")
        except writer.Fail as exc:
            if "observability stack authority invalid" not in str(exc):
                raise RuntimeError(f"unexpected observability delegation failure: {exc}") from exc
        else:
            raise RuntimeError("contact routing accepted corrupt observability stack authority")
    finally:
        OBS_REGISTRY.write_bytes(observability_registry_bytes)

    try:
        corrupted = copy.deepcopy(registry)
        corrupted["admittedRoutingCount"] = True
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
            raise RuntimeError("reconciler accepted corrupt contact routing registry")
        if CONTRACT.read_bytes() != contract_bytes:
            raise RuntimeError("rejected reconcile mutated contact routing contract")
        if STATUS.read_bytes() != status_bytes:
            raise RuntimeError("rejected reconcile mutated production operability status")
    finally:
        REGISTRY.write_bytes(registry_bytes)
        CONTRACT.write_bytes(contract_bytes)
        STATUS.write_bytes(status_bytes)

    expect_post_write_rollback(contract_bytes, status_bytes)

    if REGISTRY.read_bytes() != registry_bytes:
        raise RuntimeError("negative validation failed to restore contact routing registry")
    if OBS_REGISTRY.read_bytes() != observability_registry_bytes:
        raise RuntimeError("negative validation failed to restore observability stack registry")
    print("PASS: contact routing rejects local/upstream/review/lock authority corruption without mutation")
    print("PASS: contact routing direct append rolls back on post-append validation failure")
    print("PASS: contact routing post-write validation failure rolls back contract and status")
    print("generic repository JSON accepted as privacy/operability review: false")
    print("automatic production promotion authorized: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
