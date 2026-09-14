#!/usr/bin/env python3
"""Reject corrupt contact-routing authority without mutating canonical checkout."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts/operations/incident-contact-routing-admission-registry.v1.json"
OBS_REGISTRY = ROOT / "contracts/operations/observability-stack-deployment-registry.v1.json"
CONTRACT = ROOT / "contracts/operations/incident-contact-routing-admission-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
WRITER = ROOT / "scripts/register-memory-os-incident-contact-routing.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-incident-contact-routing.py"
INCIDENT_RESPONSE_VALIDATOR = ROOT / "scripts/validate-memory-os-incident-response.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-incident-contact-routing.py"
WORKFLOW = ROOT / ".github/workflows/incident-contact-routing-admission.yml"
FIXTURE_ROOT = ROOT / "docs/fixtures/memory-os-operability"

CANONICALS = (
    REGISTRY,
    OBS_REGISTRY,
    CONTRACT,
    STATUS,
    WRITER,
    VALIDATOR,
    INCIDENT_RESPONSE_VALIDATOR,
    OPERABILITY_VALIDATOR,
    RECONCILER,
    WORKFLOW,
)


def file_mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def snapshot() -> dict[Path, tuple[bytes, int]]:
    return {path: (path.read_bytes(), file_mode(path)) for path in CANONICALS}


def assert_canonical_unchanged(before: dict[Path, tuple[bytes, int]], label: str) -> None:
    for path, (payload, mode) in before.items():
        if path.read_bytes() != payload:
            raise RuntimeError(f"{label} mutated canonical bytes: {path.relative_to(ROOT)}")
        if file_mode(path) != mode:
            raise RuntimeError(f"{label} changed canonical mode: {path.relative_to(ROOT)}")


def load_writer():
    spec = importlib.util.spec_from_file_location("incident_contact_routing_writer_negative", WRITER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load contact routing writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_reconciler():
    spec = importlib.util.spec_from_file_location("incident_contact_routing_reconcile_negative", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load contact routing reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_writer_rejected(writer, registry: dict, label: str) -> None:
    try:
        writer.validate_registry_for_append(registry, validate_rows=False)
    except writer.Fail:
        return
    raise RuntimeError(f"writer accepted corrupt contact routing registry: {label}")


def expect_writer_append_rollback(
    writer,
    registry: dict,
    canonical_before: dict[Path, tuple[bytes, int]],
) -> None:
    original_registry = writer.REGISTRY
    original_validator = writer.validate_registry_for_append
    calls = 0
    with tempfile.TemporaryDirectory(prefix="incident-contact-routing-writer-", dir=FIXTURE_ROOT) as tmp:
        fixture_registry = Path(tmp) / REGISTRY.name
        shutil.copy2(REGISTRY, fixture_registry)
        fixture_bytes = fixture_registry.read_bytes()
        fixture_mode = file_mode(fixture_registry)

        def injected_validator(value, *, validate_rows=True):
            nonlocal calls
            calls += 1
            if calls == 1:
                return None
            raise writer.Fail("injected post-append registry validation failure")

        candidate = copy.deepcopy(registry)
        candidate["appendOnly"] = False
        try:
            writer.REGISTRY = fixture_registry
            writer.validate_registry_for_append = injected_validator
            try:
                writer.commit_registry_candidate(registry, candidate)
            except writer.Fail:
                pass
            else:
                raise RuntimeError("writer accepted injected post-append registry validation failure")
        finally:
            writer.REGISTRY = original_registry
            writer.validate_registry_for_append = original_validator

        if fixture_registry.read_bytes() != fixture_bytes:
            raise RuntimeError("writer rollback did not restore isolated registry bytes")
        if file_mode(fixture_registry) != fixture_mode:
            raise RuntimeError("writer rollback did not restore isolated registry mode")
        if list(fixture_registry.parent.glob(".incident-contact-routing.*.tmp")):
            raise RuntimeError("writer rollback left isolated temp residue")

    assert_canonical_unchanged(canonical_before, "writer rollback negative")


def expect_reconciler_authority_rejected(
    canonical_before: dict[Path, tuple[bytes, int]],
) -> None:
    reconciler = load_reconciler()
    substitutions = (
        ("CONTRACT", reconciler.STATUS, "contact routing contract authority drift"),
        ("REGISTRY", reconciler.STATUS, "contact routing registry authority drift"),
        ("WRITER", reconciler.VALIDATOR, "contact routing writer authority drift"),
        ("VALIDATOR", reconciler.OPERABILITY_VALIDATOR, "contact routing validator authority drift"),
        ("INCIDENT_RESPONSE_VALIDATOR", reconciler.OPERABILITY_VALIDATOR, "incident response validator authority drift"),
        ("OPERABILITY_VALIDATOR", reconciler.INCIDENT_RESPONSE_VALIDATOR, "operability validator authority drift"),
        ("WORKFLOW", ROOT / ".github/workflows/incident-control-exercise.yml", "contact routing workflow authority drift"),
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
                raise RuntimeError(f"contact routing reconciler accepted {field} authority substitution")
        finally:
            setattr(reconciler, field, original)
        assert_canonical_unchanged(canonical_before, f"{field} authority substitution")
    reconciler.enforce_runtime_authorities()


def fixture_pair(prefix: str) -> tuple[tempfile.TemporaryDirectory, Path, Path]:
    temporary = tempfile.TemporaryDirectory(prefix=prefix, dir=FIXTURE_ROOT)
    root = Path(temporary.name)
    contract = root / CONTRACT.name
    status = root / STATUS.name
    shutil.copy2(CONTRACT, contract)
    shutil.copy2(STATUS, status)
    return temporary, contract, status


def assert_pair_restored(contract: Path, status: Path, expected: dict[Path, tuple[bytes, int]], label: str) -> None:
    for path in (contract, status):
        payload, mode = expected[path]
        if path.read_bytes() != payload:
            raise RuntimeError(f"{label} did not restore {path.name} bytes")
        if file_mode(path) != mode:
            raise RuntimeError(f"{label} did not restore {path.name} mode")
        if list(path.parent.glob(f".{path.name}.*.tmp")):
            raise RuntimeError(f"{label} left {path.name} temp residue")


def expect_second_replace_rollback(canonical_before: dict[Path, tuple[bytes, int]]) -> None:
    reconciler = load_reconciler()
    temporary, fixture_contract, fixture_status = fixture_pair("incident-contact-routing-pair-")
    try:
        expected = {
            fixture_contract: (fixture_contract.read_bytes(), file_mode(fixture_contract)),
            fixture_status: (fixture_status.read_bytes(), file_mode(fixture_status)),
        }
        original_contract = reconciler.CONTRACT
        original_status = reconciler.STATUS
        original_validators = reconciler.POST_WRITE_VALIDATORS
        original_replace = reconciler.os.replace
        calls = 0

        def fail_second_replace(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("synthetic second authority replace rejection")
            return original_replace(source, target)

        try:
            reconciler.CONTRACT = fixture_contract
            reconciler.STATUS = fixture_status
            reconciler.POST_WRITE_VALIDATORS = ()
            reconciler.os.replace = fail_second_replace
            try:
                reconciler.commit_validated_pair(
                    json.loads(expected[fixture_contract][0].decode("utf-8")),
                    json.loads(expected[fixture_status][0].decode("utf-8")),
                )
            except OSError:
                pass
            else:
                raise RuntimeError("reconciler accepted second authority replace rejection")
        finally:
            reconciler.os.replace = original_replace
            reconciler.CONTRACT = original_contract
            reconciler.STATUS = original_status
            reconciler.POST_WRITE_VALIDATORS = original_validators

        assert_pair_restored(fixture_contract, fixture_status, expected, "second replace rejection")
    finally:
        temporary.cleanup()
    assert_canonical_unchanged(canonical_before, "second replace rollback negative")


def expect_post_write_rollback(canonical_before: dict[Path, tuple[bytes, int]]) -> None:
    reconciler = load_reconciler()
    temporary, fixture_contract, fixture_status = fixture_pair("incident-contact-routing-post-write-")
    try:
        root = fixture_contract.parent
        pass_validator = root / "validate-pass.py"
        fail_validator = root / "validate-fail.py"
        pass_validator.write_text("raise SystemExit(0)\n", encoding="utf-8")
        fail_validator.write_text("raise SystemExit(1)\n", encoding="utf-8")
        expected = {
            fixture_contract: (fixture_contract.read_bytes(), file_mode(fixture_contract)),
            fixture_status: (fixture_status.read_bytes(), file_mode(fixture_status)),
        }
        original_contract = reconciler.CONTRACT
        original_status = reconciler.STATUS
        original_validators = reconciler.POST_WRITE_VALIDATORS
        try:
            reconciler.CONTRACT = fixture_contract
            reconciler.STATUS = fixture_status
            reconciler.POST_WRITE_VALIDATORS = (pass_validator, fail_validator)
            contract = json.loads(expected[fixture_contract][0].decode("utf-8"))
            status = json.loads(expected[fixture_status][0].decode("utf-8"))
            contract["currentAuthority"]["admittedRoutingCount"] = 999
            try:
                reconciler.commit_validated_pair(contract, status)
            except reconciler.Fail as exc:
                if fail_validator.name not in str(exc):
                    raise RuntimeError(f"post-write failure rejected at wrong boundary: {exc}") from exc
            else:
                raise RuntimeError("reconciler accepted injected post-write validator failure")
        finally:
            reconciler.CONTRACT = original_contract
            reconciler.STATUS = original_status
            reconciler.POST_WRITE_VALIDATORS = original_validators
        assert_pair_restored(fixture_contract, fixture_status, expected, "post-write validation rejection")
    finally:
        temporary.cleanup()
    assert_canonical_unchanged(canonical_before, "post-write rollback negative")


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


def expect_ref_rejected(writer, ref: str, source: str, label: str) -> None:
    try:
        writer.source_bound_ref(ref, source, "negativeEvidenceRef")
    except writer.Fail:
        return
    raise RuntimeError(f"writer accepted invalid source-bound evidence: {label}")


def expect_source_bound_ref_negatives(writer, source: str, canonical_before: dict[Path, tuple[bytes, int]]) -> None:
    with tempfile.TemporaryDirectory(prefix="incident-contact-routing-ref-", dir=FIXTURE_ROOT) as tmp:
        root = Path(tmp)
        post_source = root / "post-source.tmp"
        symlink = root / "symlink.tmp"
        post_source.write_text("created after source commit\n", encoding="utf-8")
        expect_ref_rejected(writer, str(post_source.relative_to(ROOT)), source, "post-source evidence")
        try:
            symlink.symlink_to(ROOT / "README.md")
        except (OSError, NotImplementedError):
            pass
        else:
            expect_ref_rejected(writer, str(symlink.relative_to(ROOT)), source, "symlink evidence")
    assert_canonical_unchanged(canonical_before, "source-bound ref negatives")


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


def main() -> int:
    if not FIXTURE_ROOT.is_dir():
        raise RuntimeError("canonical operability fixture directory missing")
    canonical_before = snapshot()
    writer = load_writer()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

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

    expect_writer_append_rollback(writer, registry, canonical_before)
    expect_reconciler_authority_rejected(canonical_before)
    expect_second_replace_rollback(canonical_before)
    expect_post_write_rollback(canonical_before)

    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if not writer.source_is_ancestor(source):
        raise RuntimeError("current HEAD must be accepted as source ancestor")
    descendant = create_descendant_commit()
    if writer.source_is_ancestor(descendant):
        raise RuntimeError("future descendant commit was accepted as source ancestor")
    expect_generic_reviews_rejected(writer, source)
    expect_source_bound_ref_negatives(writer, source, canonical_before)

    assert_canonical_unchanged(canonical_before, "contact routing negative suite")
    print("PASS: contact routing rejects corrupt registry, executable/data authority substitutions, and invalid source-bound evidence")
    print("PASS: contact routing writer rollback uses only isolated registry authority")
    print("PASS: contact routing second-replace and post-write failures roll back isolated contract/status bytes and modes")
    print("canonical contact-routing authority mutated by negative suite: false")
    print("generic repository JSON accepted as privacy/operability review: false")
    print("automatic production promotion authorized: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
