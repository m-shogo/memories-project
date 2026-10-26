#!/usr/bin/env python3
"""Negative suite for typed, append-only generation candidate reviews."""

from __future__ import annotations

import ast
import copy
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-independent-review.py"
SUBSTITUTE = ROOT / "scripts/validate-memory-os-operability.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_generation_independent_review_validator_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load independent review validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def head_sha() -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, "cannot resolve HEAD")
    value = completed.stdout.strip()
    require(len(value) == 40, "HEAD sha invalid")
    return value


def with_virtual_registry(module, registry: dict, action) -> None:
    canonical = module.REGISTRY.read_bytes()
    canonical_mode = module.REGISTRY.stat().st_mode & 0o777
    payload = json.dumps(registry, indent=2) + "\n"
    original_open = Path.open

    def virtual_open(path: Path, *args, **kwargs):
        mode = args[0] if args else kwargs.get("mode", "r")
        if path == module.REGISTRY and mode == "rb":
            return io.BytesIO(payload.encode("utf-8"))
        return original_open(path, *args, **kwargs)

    Path.open = virtual_open
    try:
        action()
    finally:
        Path.open = original_open
    require(module.REGISTRY.read_bytes() == canonical, "canonical generation evidence registry mutated during negative exercise")
    require((module.REGISTRY.stat().st_mode & 0o777) == canonical_mode, "canonical generation evidence registry mode mutated during negative exercise")


def expect_fail(module, registry: dict, label: str, expected: str | None = None) -> None:
    def action() -> None:
        try:
            module.main()
        except module.Fail as exc:
            if expected is not None:
                require(expected in str(exc), f"negative case rejected at wrong boundary ({label}): {exc}")
            return
        raise Fail(f"negative case unexpectedly passed: {label}")

    with_virtual_registry(module, registry, action)


def expect_pass(module, registry: dict, label: str) -> None:
    def action() -> None:
        try:
            result = module.main()
        except module.Fail as exc:
            raise Fail(f"positive case unexpectedly failed ({label}): {exc}") from exc
        require(result == 0, f"positive case returned non-zero: {label}")

    with_virtual_registry(module, registry, action)


def expect_authority_substitution_fail(module, field: str, substitute: Path) -> None:
    module.enforce_execution_authority()
    module.enforce_runtime_authorities()
    canonical_contract = (ROOT / module.CONTRACT_REL).read_bytes()
    canonical_registry = (ROOT / module.REGISTRY_REL).read_bytes()
    expected = {
        "CONTRACT": "generation evidence contract authority drift",
        "REGISTRY": "generation evidence registry authority drift",
        "MATERIAL_DELTA_VALIDATOR": "candidate material-delta review validator authority drift",
        "REVIEW_SOURCE_ORDER_VALIDATOR": "candidate review source-order validator authority drift",
        "VALIDATOR": "generation independent-review validator authority drift",
    }[field]
    original = getattr(module, field)
    setattr(module, field, substitute)
    try:
        try:
            module.main()
        except module.Fail as exc:
            require(str(exc) == expected,
                    f"independent-review runtime authority substitution wrong diagnostic ({field}): {exc}")
        else:
            raise Fail(f"runtime authority substitution unexpectedly passed: {field}")
        require((ROOT / module.CONTRACT_REL).read_bytes() == canonical_contract,
                f"canonical contract mutated while rejecting {field}")
        require((ROOT / module.REGISTRY_REL).read_bytes() == canonical_registry,
                f"canonical registry mutated while rejecting {field}")
    finally:
        setattr(module, field, original)
    module.enforce_execution_authority()
    module.enforce_runtime_authorities()


def expect_execution_substitution_fail(module, field: str, replacement) -> None:
    original = getattr(module, field)
    setattr(module, field, replacement)
    try:
        try:
            module.candidate_reviews_approved(base_row())
        except module.Fail:
            return
        raise Fail(f"independent-review execution helper substitution unexpectedly passed: {field}")
    finally:
        setattr(module, field, original)


def expect_main_candidate_substitution_fail(module) -> None:
    original = module.candidate_reviews_approved
    module.candidate_reviews_approved = lambda _row: True
    try:
        try:
            module.main()
        except module.Fail as exc:
            require("candidate authority drift" in str(exc), f"candidate substitution rejected at wrong boundary: {exc}")
            return
        raise Fail("main accepted substituted independent-review candidate authority")
    finally:
        module.candidate_reviews_approved = original


def base_row() -> dict:
    return {
        "evidenceId": "brge_negative_review_authority",
        "sourceCommitSha": head_sha(),
        "drillRequestId": "brrq_negative_review_authority",
        "recoveryObjectivesId": "ro_negative_review_authority",
        "sourceEnvironmentGenerationId": "pegen_negative_source",
        "restoreTargetGenerationId": "pegen_negative_target",
        "materialDeltaReviewRef": "docs/evidence/backup-restore/material-delta/synthetic-review.json",
        "securityReviewRef": "README.md",
        "operabilityReviewRef": "SECURITY.md",
    }


def registry(row: dict) -> dict:
    return {
        "schemaVersion": "memory-os-backup-restore-generation-evidence-registry.v1",
        "appendOnly": True,
        "registeredEvidenceCount": 1,
        "drillRequestBoundEvidenceCount": 1,
        "completeGenerationBoundBackupCount": 0,
        "completeGenerationBoundRestoreCount": 0,
        "productionEquivalentRecoveryCandidateCount": 0,
        "records": [row],
        "productionEvidence": False,
        "productionReady": False,
    }


def typed_payload(row: dict, role: str) -> dict:
    return {
        "schemaVersion": "memory-os-backup-restore-generation-review-evidence.v1",
        "evidenceId": row["evidenceId"],
        "drillRequestId": row["drillRequestId"],
        "recoveryObjectivesId": row["recoveryObjectivesId"],
        "sourceEnvironmentGenerationId": row["sourceEnvironmentGenerationId"],
        "restoreTargetGenerationId": row["restoreTargetGenerationId"],
        "reviewRole": role,
        "reviewResult": "APPROVED",
        "reviewedAt": "2026-08-15T00:00:00Z",
        "reviewerPseudonym": "reviewer-security" if role == "SECURITY" else "reviewer-operability",
        "productionTrafficChanged": False,
        "productionCredentialsUsed": False,
        "automaticPromotion": False,
    }


def with_virtual_review_payload(module, payload: dict, role: str, action) -> None:
    require(role in ("SECURITY", "OPERABILITY"), "synthetic review role invalid")
    row = base_row()
    ref_field = "securityReviewRef" if role == "SECURITY" else "operabilityReviewRef"
    original_canonical_ref = module.canonical_ref
    original_append_only = module.require_append_only_review
    original_load_json = module.load_json
    try:
        module.canonical_ref = lambda _value, _field: (
            "docs/evidence/backup-restore/synthetic-review.json",
            Path("/tmp/synthetic-generation-review.json"),
        )
        module.require_append_only_review = lambda _ref, _path, _field: None
        module.load_json = lambda _path, _field: payload
        action(row, ref_field, role)
    finally:
        module.canonical_ref = original_canonical_ref
        module.require_append_only_review = original_append_only
        module.load_json = original_load_json


def expect_review_payload_pass(module, role: str) -> None:
    payload = typed_payload(base_row(), role)

    def action(row, ref_field, expected_role) -> None:
        try:
            ref, reviewer = module.validate_review(row, ref_field, expected_role)
        except module.Fail as exc:
            raise Fail(f"synthetic independent-review positive control failed ({role}): {exc}") from exc
        require(ref == "docs/evidence/backup-restore/synthetic-review.json",
                f"synthetic independent-review positive ref drift: {role}")
        require(reviewer == payload["reviewerPseudonym"],
                f"synthetic independent-review positive reviewer drift: {role}")

    with_virtual_review_payload(module, payload, role, action)


def expect_review_payload_fail(module, payload: dict, label: str, expected: str, role: str) -> None:
    def action(row, ref_field, expected_role) -> None:
        try:
            module.validate_review(row, ref_field, expected_role)
        except module.Fail as exc:
            require(str(exc) == f"{ref_field} {expected}",
                    f"review payload rejected at wrong authority ({label}): {exc}")
            return
        raise Fail(f"review payload negative unexpectedly passed: {label}")

    with_virtual_review_payload(module, payload, role, action)


def expect_bound_field_fail(module, field: str, role: str) -> None:
    row = base_row()
    payload = typed_payload(row, role)
    payload[field] = "mismatched-authority"
    expect_review_payload_fail(module, payload, f"{role} authority mismatch: {field}", f"{field} mismatch", role)


def expect_contract_fail(module, mutate, label: str, expected: str) -> None:
    # A valid canonical contract must pass before and after every isolated mutation.
    module.validate_contract_authority()
    canonical = json.loads(module.CONTRACT.read_text(encoding="utf-8"))
    mutated = json.loads(json.dumps(canonical))
    mutate(mutated)
    original_load_json = module.load_json
    try:
        module.load_json = lambda path, field: mutated if path == module.CONTRACT else original_load_json(path, field)
        try:
            module.validate_contract_authority()
        except module.Fail as exc:
            require(str(exc) == expected,
                    f"contract authority negative rejected at wrong boundary ({label}): {exc}")
        else:
            raise Fail(f"contract authority negative unexpectedly passed: {label}")
    finally:
        module.load_json = original_load_json
    module.validate_contract_authority()


def expect_source_order_execution(module) -> None:
    # The source-order validator's own synthetic chronology self-test is not
    # invoked by the workflow's ordinary empty-registry validation command.
    source_order = module.load_review_source_order_validator()
    require(callable(getattr(source_order, "self_test", None)),
            "review source-order synthetic chronology self-test missing")
    source_order.self_test()

    row = base_row()
    source_sha = row["sourceCommitSha"]
    fixture_path = ROOT / "README.md"
    require(fixture_path.is_file() and not fixture_path.is_symlink(),
            "read-only review source-order fixture missing")
    original = {
        name: getattr(source_order, name)
        for name in (
            "commit_exists", "commit_time", "canonical_review_ref",
            "first_commit_for_path", "require_source_precedes_review",
            "creation_blob", "load_json",
        )
    }
    seen_refs: list[tuple[str, bool]] = []
    seen_chronology: list[str] = []
    reject_field: str | None = None
    from datetime import datetime, timezone

    def fixture_ref(value, field, material_delta=False):
        source_order.require(isinstance(value, str) and bool(value), f"{field} required")
        seen_refs.append((field, material_delta))
        return value, fixture_path

    def fixture_chronology(_source, _review, field):
        seen_chronology.append(field)
        if field == reject_field:
            raise source_order.Fail(f"{field} review predates or is not descended from sourceCommitSha")

    def check(row_to_check, expected_refs, expected_chronology, label):
        seen_refs.clear()
        seen_chronology.clear()
        source_order.validate_row(row_to_check, 0)
        require(seen_refs == expected_refs, f"{label} review reference reachability drift: {seen_refs}")
        require(seen_chronology == expected_chronology,
                f"{label} review chronology reachability drift: {seen_chronology}")

    expected_cross = [
        ("records[0].securityReviewRef", False),
        ("records[0].operabilityReviewRef", False),
        ("records[0].materialDeltaReviewRef", True),
    ]
    try:
        source_order.commit_exists = lambda *_args: None
        source_order.commit_time = lambda sha, _field: datetime(
            2026, 9, 12, 9, 0 if sha == source_sha else 10, tzinfo=timezone.utc
        )
        source_order.canonical_review_ref = fixture_ref
        source_order.first_commit_for_path = lambda *_args: "b" * 40
        source_order.require_source_precedes_review = fixture_chronology
        source_order.creation_blob = lambda *_args: fixture_path.read_bytes()
        source_order.load_json = lambda *_args: {"reviewedAt": "2026-09-12T09:05:00Z"}

        check(row, expected_cross, [field for field, _ in expected_cross],
              "cross-generation independent and material-delta reviews")

        for field, _material_delta in expected_cross:
            reject_field = field
            seen_chronology.clear()
            try:
                source_order.validate_row(row, 0)
            except source_order.Fail as exc:
                require(str(exc) == f"{field} review predates or is not descended from sourceCommitSha",
                        f"{field} chronology rejected at wrong boundary: {exc}")
                require(field in seen_chronology,
                        f"{field} chronology rejection occurred before guard execution")
            else:
                raise Fail(f"{field} chronology guard bypassed by candidate review")
        reject_field = None

        same_generation = dict(row)
        same_generation["restoreTargetGenerationId"] = same_generation["sourceEnvironmentGenerationId"]
        same_generation.pop("materialDeltaReviewRef")
        check(same_generation, expected_cross[:2],
              [field for field, _ in expected_cross[:2]], "same-generation independent reviews")

        forbidden_delta = dict(same_generation)
        forbidden_delta["materialDeltaReviewRef"] = row["materialDeltaReviewRef"]
        try:
            source_order.validate_row(forbidden_delta, 0)
        except source_order.Fail as exc:
            require(str(exc) == "records[0].materialDeltaReviewRef must remain null for same-generation restore",
                    f"same-generation material-delta rejected at wrong boundary: {exc}")
        else:
            raise Fail("same-generation restore accepted a material-delta review")

        missing_delta = dict(row)
        missing_delta.pop("materialDeltaReviewRef")
        try:
            source_order.validate_row(missing_delta, 0)
        except source_order.Fail as exc:
            require(str(exc) == "records[0].materialDeltaReviewRef required",
                    f"cross-generation missing material-delta rejected at wrong boundary: {exc}")
        else:
            raise Fail("cross-generation restore accepted missing material-delta review")
    finally:
        for name, original_value in original.items():
            setattr(source_order, name, original_value)


EXECUTION_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-generation-independent-review-execution-negative.py"


def require_external_source_order_guard(tree: ast.Module) -> None:
    guards = [node for node in tree.body
              if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
              and node.name == "require_source_order_main_negative_proof"]
    require(len(guards) == 1 and isinstance(guards[0], ast.FunctionDef),
            "external source-order AST guard definition drift")
    guard_calls = [node for node in ast.walk(guards[0])
                   if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                   and node.func.id == "require_source_order_main_binding"]
    require(len(guard_calls) >= 2 and any(isinstance(node, ast.For) for node in guards[0].body),
            "external source-order AST guard mutation proof drift")
    mains = [node for node in tree.body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main"]
    require(len(mains) == 1 and isinstance(mains[0], ast.FunctionDef),
            "external source-order AST negative main definition drift")
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "main" for target in node.targets
        ):
            raise Fail("external source-order AST negative main shadowed")
    body = mains[0].body
    calls = [
        node for node in body
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "require_source_order_main_negative_proof"
        and not node.value.args and not node.value.keywords
    ]
    require(len(calls) == 1 and body[0] is calls[0],
            "external source-order AST guard not first direct main step")


def require_external_source_order_guard_negative_proof() -> None:
    require(EXECUTION_NEGATIVE.is_file() and not EXECUTION_NEGATIVE.is_symlink(),
            "external source-order AST negative executable missing or symlinked")
    require(EXECUTION_NEGATIVE.resolve(strict=True) ==
            ROOT.resolve(strict=True) / "scripts/validate-memory-os-backup-restore-generation-independent-review-execution-negative.py",
            "external source-order AST negative executable path drift")
    tree = ast.parse(EXECUTION_NEGATIVE.read_text(encoding="utf-8"))
    require_external_source_order_guard(tree)
    cases = (
        ("omit main guard call", "external source-order AST guard not first direct main step"),
        ("move guard after loader", "external source-order AST guard not first direct main step"),
        ("dead-branch guard", "external source-order AST guard not first direct main step"),
        ("duplicate main guard", "external source-order AST guard not first direct main step"),
        ("remove guard definition", "external source-order AST guard definition drift"),
        ("remove mutation loop", "external source-order AST guard mutation proof drift"),
        ("shadow main", "external source-order AST negative main shadowed"),
    )
    for label, expected in cases:
        mutant = copy.deepcopy(tree)
        main = next(node for node in mutant.body
                    if isinstance(node, ast.FunctionDef) and node.name == "main")
        guard = next(node for node in mutant.body
                     if isinstance(node, ast.FunctionDef)
                     and node.name == "require_source_order_main_negative_proof")
        if label == "omit main guard call":
            main.body.pop(0)
        elif label == "move guard after loader":
            main.body.insert(1, main.body.pop(0))
        elif label == "dead-branch guard":
            main.body[0] = ast.If(test=ast.Constant(False), body=[main.body[0]], orelse=[])
        elif label == "duplicate main guard":
            main.body.insert(1, copy.deepcopy(main.body[0]))
        elif label == "remove guard definition":
            mutant.body.remove(guard)
        elif label == "remove mutation loop":
            guard.body[:] = [node for node in guard.body if not isinstance(node, ast.For)]
        elif label == "shadow main":
            mutant.body.append(ast.Assign(targets=[ast.Name(id="main", ctx=ast.Store())],
                                          value=ast.Constant(None)))
        try:
            require_external_source_order_guard(mutant)
        except Fail as exc:
            require(str(exc) == expected,
                    f"external source-order guard mutation rejected at wrong boundary ({label}): {exc}")
        else:
            raise Fail(f"external source-order guard accepted mutation: {label}")
    print(f"PASS: external source-order AST guard reachability rejects {len(cases)} mutations")



def require_candidate_pair_source_binding(tree: ast.Module) -> None:
    """Verify the real candidate path binds two validated, distinct review authorities."""
    candidates = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                  and node.name == "candidate_reviews_approved"]
    require(len(candidates) == 1, "candidate pair source function authority drift")
    body = candidates[0].body

    def direct_index(statement: str, label: str) -> int:
        expected = ast.parse(statement).body[0]
        indices = [index for index, node in enumerate(body)
                   if ast.dump(node, include_attributes=False) ==
                   ast.dump(expected, include_attributes=False)]
        require(len(indices) == 1, f"candidate pair {label} direct execution authority drift")
        return indices[0]

    security = direct_index(
        'security_ref, security_reviewer = validate_review(row, "securityReviewRef", ROLE_BY_REF["securityReviewRef"])',
        "security review validation",
    )
    operability = direct_index(
        'operability_ref, operability_reviewer = validate_review(row, "operabilityReviewRef", ROLE_BY_REF["operabilityReviewRef"])',
        "operability review validation",
    )
    distinct_refs = direct_index(
        'require(security_ref != operability_ref, "Security and Operability review refs must remain distinct")',
        "distinct review refs",
    )
    distinct_reviewers = direct_index(
        'require(security_reviewer != operability_reviewer, "Security and Operability reviewers must remain distinct")',
        "distinct reviewer identities",
    )
    approved = direct_index("return True", "positive candidate return")
    require(security < operability < distinct_refs < distinct_reviewers < approved,
            "candidate pair validation and distinctness execution order drift")


def prove_candidate_pair_source_binding() -> None:
    tree = ast.parse(VALIDATOR.read_text(encoding="utf-8"))
    require_candidate_pair_source_binding(tree)

    def candidate(mutant):
        return next(node for node in mutant.body
                    if isinstance(node, ast.FunctionDef) and node.name == "candidate_reviews_approved")

    mutations = (
        ("remove security validation", 0, "remove", "candidate pair security review validation direct execution authority drift"),
        ("remove operability validation", 1, "remove", "candidate pair operability review validation direct execution authority drift"),
        ("remove distinct refs", 2, "remove", "candidate pair distinct review refs direct execution authority drift"),
        ("remove distinct reviewers", 3, "remove", "candidate pair distinct reviewer identities direct execution authority drift"),
        ("weaken distinct refs", 2, "weaken", "candidate pair distinct review refs direct execution authority drift"),
        ("weaken distinct reviewers", 3, "weaken", "candidate pair distinct reviewer identities direct execution authority drift"),
        ("hide distinct refs in dead branch", 2, "dead", "candidate pair distinct review refs direct execution authority drift"),
        ("hide distinct reviewers in dead branch", 3, "dead", "candidate pair distinct reviewer identities direct execution authority drift"),
        ("premature distinct refs", 2, "early", "candidate pair validation and distinctness execution order drift"),
        ("remove candidate return", 4, "remove", "candidate pair positive candidate return direct execution authority drift"),
    )
    statements = (
        'security_ref, security_reviewer = validate_review(row, "securityReviewRef", ROLE_BY_REF["securityReviewRef"])',
        'operability_ref, operability_reviewer = validate_review(row, "operabilityReviewRef", ROLE_BY_REF["operabilityReviewRef"])',
        'require(security_ref != operability_ref, "Security and Operability review refs must remain distinct")',
        'require(security_reviewer != operability_reviewer, "Security and Operability reviewers must remain distinct")',
        "return True",
    )
    for label, index, operation, expected in mutations:
        mutant = copy.deepcopy(tree)
        body = candidate(mutant).body
        expected_node = ast.parse(statements[index]).body[0]
        matching = [i for i, node in enumerate(body)
                    if ast.dump(node, include_attributes=False) ==
                    ast.dump(expected_node, include_attributes=False)]
        require(len(matching) == 1, f"candidate pair mutation fixture missing: {label}")
        at = matching[0]
        if operation == "remove":
            body.pop(at)
        elif operation == "weaken":
            body[at].value.args[0].ops[0] = ast.Eq()
        elif operation == "dead":
            body[at] = ast.If(test=ast.Constant(value=False), body=[body[at]], orelse=[])
        elif operation == "early":
            statement = body.pop(at)
            body.insert(0, statement)
        try:
            require_candidate_pair_source_binding(mutant)
        except Fail as exc:
            require(str(exc) == expected, f"candidate pair mutation wrong diagnostic ({label}): {exc}")
        else:
            raise Fail(f"candidate pair mutation accepted: {label}")
    print(f"PASS: candidate pair direct source binding rejects {len(mutations)} validation/distinctness bypasses")



def prove_runtime_review_pair_controls() -> None:
    """Use a disposable Git repository to reach real source-order and pair validators."""
    paths = (
        "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
        "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
        "scripts/validate-memory-os-backup-restore-generation-independent-review.py",
        "scripts/validate-memory-os-backup-restore-generation-material-delta-review.py",
        "scripts/validate-memory-os-backup-restore-generation-material-delta-review-negative.py",
        "scripts/validate-memory-os-backup-restore-review-source-order.py",
    )
    with tempfile.TemporaryDirectory(prefix="generation-review-pair-runtime-negative-") as tmp:
        root = Path(tmp)
        for relative in paths:
            source = ROOT / relative
            require(source.is_file() and not source.is_symlink(),
                    f"synthetic review pair source missing or substituted: {relative}")
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

        def git(*args: str, commit_time: str | None = None) -> str:
            env = os.environ.copy()
            if commit_time is not None:
                env["GIT_AUTHOR_DATE"] = commit_time
                env["GIT_COMMITTER_DATE"] = commit_time
            result = subprocess.run(["git", *args], cwd=root, env=env,
                                    text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            require(result.returncode == 0,
                    f"synthetic review pair Git command failed: {args}: {result.stderr.strip()}")
            return result.stdout.strip()

        git("init", "-q")
        git("add", "--", *paths)
        git("-c", "user.name=CI Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "synthetic source authority", commit_time="2026-08-01T00:00:00+00:00")
        source_sha = git("rev-parse", "HEAD")
        row = base_row()
        row["sourceCommitSha"] = source_sha
        row["restoreTargetGenerationId"] = row["sourceEnvironmentGenerationId"]
        row["materialDeltaReviewRef"] = None

        security_ref = "docs/evidence/backup-restore/security/negative-pair-security.json"
        operability_ref = "docs/evidence/backup-restore/operability/negative-pair-operability.json"
        reused_reviewer_ref = "docs/evidence/backup-restore/operability/negative-pair-reused-reviewer.json"
        stale_timestamp_ref = "docs/evidence/backup-restore/operability/negative-pair-stale-timestamp.json"
        future_timestamp_ref = "docs/evidence/backup-restore/operability/negative-pair-future-timestamp.json"
        row["securityReviewRef"] = security_ref
        row["operabilityReviewRef"] = operability_ref
        review_fixtures = (
            (security_ref, "SECURITY", "reviewer-security", "2026-08-01T00:01:00Z"),
            (operability_ref, "OPERABILITY", "reviewer-operability", "2026-08-01T00:01:00Z"),
            (reused_reviewer_ref, "OPERABILITY", "reviewer-security", "2026-08-01T00:01:00Z"),
            (stale_timestamp_ref, "OPERABILITY", "reviewer-operability", "2026-07-31T23:59:00Z"),
            (future_timestamp_ref, "OPERABILITY", "reviewer-operability", "2026-08-01T00:03:00Z"),
        )
        for relative, role, reviewer, reviewed_at in review_fixtures:
            payload = typed_payload(row, role)
            payload["reviewedAt"] = reviewed_at
            payload["reviewerPseudonym"] = reviewer
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
        cross_row = base_row()
        cross_row["sourceCommitSha"] = source_sha
        cross_security_ref = "docs/evidence/backup-restore/security/negative-cross-security.json"
        cross_operability_ref = "docs/evidence/backup-restore/operability/negative-cross-operability.json"
        cross_delta_ref = "docs/evidence/backup-restore/material-delta/negative-cross-delta.json"
        cross_bad_delta_ref = "docs/evidence/backup-restore/material-delta/negative-cross-wrong-target.json"
        cross_row["securityReviewRef"] = cross_security_ref
        cross_row["operabilityReviewRef"] = cross_operability_ref
        cross_row["materialDeltaReviewRef"] = cross_delta_ref
        for relative, role in ((cross_security_ref, "SECURITY"), (cross_operability_ref, "OPERABILITY")):
            payload = typed_payload(cross_row, role)
            payload["reviewedAt"] = "2026-08-01T00:01:00Z"
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

        delta_payload = {
            "schemaVersion": "memory-os-backup-restore-material-delta-review.v1",
            "evidenceId": cross_row["evidenceId"],
            "drillRequestId": cross_row["drillRequestId"],
            "recoveryObjectivesId": cross_row["recoveryObjectivesId"],
            "sourceEnvironmentGenerationId": cross_row["sourceEnvironmentGenerationId"],
            "restoreTargetGenerationId": cross_row["restoreTargetGenerationId"],
            "reviewResult": "APPROVED",
            "reviewedAt": "2026-08-01T00:01:00Z",
            "reviewerPseudonym": "reviewer-delta",
            "productionTrafficChanged": False,
            "productionCredentialsUsed": False,
            "automaticPromotion": False,
        }
        for relative, wrong_target in ((cross_delta_ref, False), (cross_bad_delta_ref, True)):
            payload = dict(delta_payload)
            if wrong_target:
                payload["restoreTargetGenerationId"] = "pegen_unrelated_target"
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
        git("add", "--", *(relative for relative, *_ in review_fixtures),
            cross_security_ref, cross_operability_ref, cross_delta_ref, cross_bad_delta_ref)
        git("-c", "user.name=CI Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "synthetic post-source reviews", commit_time="2026-08-01T00:02:00+00:00")

        validator_path = root / "scripts/validate-memory-os-backup-restore-generation-independent-review.py"
        spec = importlib.util.spec_from_file_location("isolated_generation_review_pair_runtime", validator_path)
        require(spec is not None and spec.loader is not None,
                "cannot load isolated generation review pair validator")
        isolated = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(isolated)
        require(isolated.candidate_reviews_approved(row) is True,
                "valid synthetic independent Security/Operability review pair not approved")

        same_reviewer = dict(row)
        same_reviewer["operabilityReviewRef"] = reused_reviewer_ref
        try:
            isolated.candidate_reviews_approved(same_reviewer)
        except isolated.Fail as exc:
            require(str(exc) == "Security and Operability reviewers must remain distinct",
                    f"reused reviewer rejected before canonical distinctness guard: {exc}")
        else:
            raise Fail("candidate accepted a reused independent reviewer")

        same_ref = dict(row)
        same_ref["operabilityReviewRef"] = security_ref
        try:
            isolated.candidate_reviews_approved(same_ref)
        except isolated.Fail as exc:
            require(str(exc) == "operabilityReviewRef reviewRole mismatch",
                    f"reused review ref rejected at wrong typed-role guard: {exc}")
        else:
            raise Fail("candidate accepted a reused Security review as Operability evidence")
        same_commit = dict(row)
        same_commit["sourceCommitSha"] = git("rev-parse", "HEAD")
        for label, mutated, expected in (
            ("same-commit review", same_commit,
             "review source-order authority invalid: records[-1].securityReviewRef review must be created strictly after sourceCommitSha"),
            ("reviewedAt before source", {**row, "operabilityReviewRef": stale_timestamp_ref},
             "review source-order authority invalid: records[-1].operabilityReviewRef.reviewedAt predates sourceCommitSha"),
            ("reviewedAt after creation", {**row, "operabilityReviewRef": future_timestamp_ref},
             "review source-order authority invalid: records[-1].operabilityReviewRef.reviewedAt is later than review evidence commit"),
        ):
            try:
                isolated.candidate_reviews_approved(mutated)
            except isolated.Fail as exc:
                require(str(exc) == expected, f"real Git chronology negative wrong boundary ({label}): {exc}")
            else:
                raise Fail(f"real Git chronology negative unexpectedly accepted: {label}")
        require(isolated.candidate_reviews_approved(cross_row) is True,
                "valid synthetic cross-generation material-delta and independent review pair not approved")
        for label, mutated, expected in (
            ("cross-generation missing material delta", {**cross_row, "materialDeltaReviewRef": None},
             "review source-order authority invalid: records[-1].materialDeltaReviewRef required"),
            ("same-generation forbidden material delta", {**row, "materialDeltaReviewRef": cross_delta_ref},
             "review source-order authority invalid: records[-1].materialDeltaReviewRef must remain null for same-generation restore"),
            ("cross-generation wrong target binding", {**cross_row, "materialDeltaReviewRef": cross_bad_delta_ref},
             "material-delta review authority invalid: records[0].materialDeltaReviewRef restoreTargetGenerationId mismatch"),
        ):
            try:
                isolated.candidate_reviews_approved(mutated)
            except isolated.Fail as exc:
                require(str(exc) == expected, f"real Git material-delta negative wrong boundary ({label}): {exc}")
            else:
                raise Fail(f"real Git material-delta negative unexpectedly accepted: {label}")
        require(isolated.candidate_reviews_approved(row) is True,
                "valid same-generation review pair drifted after rejected reuse/chronology/delta cases")
        require(isolated.candidate_reviews_approved(cross_row) is True,
                "valid cross-generation review pair drifted after rejected material-delta cases")
    print("PASS: isolated Git same/cross-generation positive pairs and exact reviewer/ref, chronology and material-delta runtime negatives")


def prove_independent_review_json_reader(module) -> None:
    """Exercise the actual independent-review reader without producing approval evidence."""
    before = (module.CONTRACT.read_bytes(), module.REGISTRY.read_bytes())
    with tempfile.TemporaryDirectory(prefix="memory-os-independent-review-json-", dir=ROOT) as directory:
        path = Path(directory) / "candidate.json"
        positive = b'{"safe":true,"nested":{"count":1}}'
        path.write_bytes(positive)
        require(module.load_json(path, "synthetic") == {"safe": True, "nested": {"count": 1}}, "independent review JSON positive control failed")
        cases = (
            ("duplicate root", b'{"safe":true,"safe":false}', "independent review JSON duplicate key refused"),
            ("duplicate nested", b'{"nested":{"a":1,"a":2}}', "independent review JSON duplicate key refused"),
            ("NaN", b'{"number":NaN}', "independent review JSON nonfinite number refused"),
            ("Infinity", b'{"number":Infinity}', "independent review JSON nonfinite number refused"),
            ("negative Infinity", b'{"number":-Infinity}', "independent review JSON nonfinite number refused"),
            ("float overflow", b'{"number":1e999}', "independent review JSON nonfinite number refused"),
            ("large integer", b'{"number":' + b"9" * 5000 + b"}", "independent review JSON integer too large"),
            ("oversized JSON", b'{"data":"' + b"x" * module.MAX_JSON_BYTES + b'"}', "independent review JSON size limit exceeded"),
            ("invalid UTF-8", b'{"private":"\xff"}', "independent review JSON unreadable or invalid"),
            ("malformed private", b'{"private":"synthetic-secret",', "independent review JSON unreadable or invalid"),
            ("nonobject root", b"[]", "independent review JSON root must be object"),
        )
        def rejected(candidate, expected: str, label: str) -> None:
            try:
                module.load_json(candidate, "synthetic-secret")
            except module.Fail as exc:
                require(str(exc) == expected, f"{label}: wrong independent review JSON rejection boundary")
                require("synthetic-secret" not in str(exc), f"{label}: private marker disclosed")
            else:
                raise Fail(f"{label}: unsafe independent review JSON accepted")
        for label, payload, expected in cases:
            path.write_bytes(payload)
            rejected(path, expected, label)
        path.write_bytes(positive)
        alias = Path(directory) / "alias.json"
        alias.symlink_to(path)
        rejected(alias, "independent review JSON path missing or unsafe", "symlink")
        rejected(Path(directory), "independent review JSON path missing or unsafe", "directory")
        rejected(Path(directory) / "missing.json", "independent review JSON path missing or unsafe", "missing")
        rejected("candidate.json", "independent review JSON path invalid", "non-Path")
        with tempfile.TemporaryDirectory(prefix="memory-os-independent-review-canary-") as outside:
            canary = Path(outside) / "canary.json"
            canary.write_bytes(positive)
            escaped = Path(directory) / "escaped.json"
            escaped.symlink_to(canary)
            rejected(escaped, "independent review JSON path missing or unsafe", "external symlink")
            require(canary.read_bytes() == positive, "independent review JSON modified external canary")
        require(path.read_bytes() == positive, "independent review JSON modified positive fixture")
    require((module.CONTRACT.read_bytes(), module.REGISTRY.read_bytes()) == before, "independent review JSON mutated protected authorities")
    print("PASS: actual independent review JSON reader positive and 16 fail-closed negatives")



def exercise_bounded_review_git_history(module) -> None:
    """Exercise the real history consumer with private-output and timeout negatives."""
    original_run = module.subprocess.run
    ref = "docs/evidence/backup-restore/synthetic-review.json"
    marker = "PRIVATE_REVIEW_MARKER_DO_NOT_LOG"
    state = {"stdout": "a" * 40 + "\n", "returncode": 0, "error": None}
    calls = []

    def fake_git(args, **kwargs):
        require(args == ["git", "log", "--format=%H", "--max-count=2", "--follow", "--", ref],
                "independent review Git history must use bounded canonical pathspec")
        require(kwargs.get("cwd") == module.ROOT and kwargs.get("text") is True,
                "independent review Git history execution context drift")
        require(kwargs.get("stdout") is subprocess.PIPE and kwargs.get("stderr") is subprocess.DEVNULL,
                "independent review Git history output privacy drift")
        require(kwargs.get("timeout") == 20 and kwargs.get("check") is False,
                "independent review Git history timeout/check drift")
        calls.append(args)
        if state["error"] is not None:
            raise state["error"]
        return subprocess.CompletedProcess(args, state["returncode"],
                                           stdout=state["stdout"], stderr=marker)

    module.subprocess.run = fake_git
    try:
        require(module.git_history(ref, "securityReviewRef") == ["a" * 40],
                "bounded Git history positive control failed")
        state["stdout"] = "a" * 40 + "\n" + "b" * 40 + "\n"
        require(module.git_history(ref, "securityReviewRef") == ["a" * 40, "b" * 40],
                "bounded two-change Git history control failed")
        cases = [
            ("nonzero", {"returncode": 1}, "cannot inspect securityReviewRef Git history"),
            ("bool-exit", {"returncode": True}, "cannot inspect securityReviewRef Git history"),
            ("nonstring", {"stdout": b"a" * 40}, "securityReviewRef Git history output invalid"),
            ("malformed", {"stdout": "PRIVATE_REVIEW_MARKER_DO_NOT_LOG\n"}, "securityReviewRef Git history output invalid"),
            ("oversized", {"stdout": ("a" * 40 + "\n") * 3}, "securityReviewRef Git history output invalid"),
            ("empty", {"stdout": ""}, "securityReviewRef must be committed review evidence"),
            ("timeout", {"error": subprocess.TimeoutExpired(["git", "log"], 20, stderr=marker)},
             "cannot inspect securityReviewRef Git history"),
            ("unavailable", {"error": OSError(marker)}, "cannot inspect securityReviewRef Git history"),
        ]
        for label, changes, expected in cases:
            state.update({"stdout": "a" * 40 + "\n", "returncode": 0, "error": None})
            state.update(changes)
            try:
                module.git_history(ref, "securityReviewRef")
            except module.Fail as exc:
                require(str(exc) == expected and marker not in str(exc),
                        f"bounded Git history {label} rejected at wrong private diagnostic")
            else:
                raise Fail(f"bounded Git history {label} unexpectedly accepted")
        require(len(calls) == 10, "bounded Git history negative multiplicity drift")
    finally:
        module.subprocess.run = original_run
    print("PASS: independent review Git history bounded, private and fail-closed with eight negatives")



def prove_source_order_bounded_git_output(module) -> None:
    """Exercise actual source-order Git transport without production evidence."""
    source_order = module.load_review_source_order_validator()
    original_run = source_order.subprocess.run
    ref = "docs/evidence/backup-restore/security/synthetic.json"
    field = "syntheticSecurityReview"
    marker = "PRIVATE_GIT_DIAGNOSTIC_DO_NOT_LOG"
    state = {"stdout": "a" * 40 + "\n", "returncode": 0, "error": None}
    calls = []

    def fake_git(args, **kwargs):
        require(args == ["git", "log", "--diff-filter=A", "--max-count=2",
                         "--follow", "--format=%H", "--", ref],
                "source-order Git creation history pathspec/count drift")
        require(kwargs.get("cwd") == source_order.ROOT and kwargs.get("text") is True,
                "source-order Git execution context drift")
        require(kwargs.get("stdout") is subprocess.PIPE and kwargs.get("stderr") is subprocess.DEVNULL,
                "source-order Git diagnostic privacy drift")
        require(kwargs.get("check") is False and kwargs.get("timeout") == 20,
                "source-order Git timeout drift")
        calls.append(args)
        if state["error"] is not None:
            raise state["error"]
        return subprocess.CompletedProcess(args, state["returncode"],
                                           stdout=state["stdout"], stderr=marker)

    source_order.subprocess.run = fake_git
    try:
        require(source_order.first_commit_for_path(ref, field) == "a" * 40,
                "source-order bounded Git positive control failed")
        cases = [
            ("multiple", {"stdout": "a" * 40 + "\n" + "b" * 40 + "\n"},
             f"{field} must have exactly one committed creation point"),
            ("nonzero", {"returncode": 1}, f"cannot inspect {field}"),
            ("bool-exit", {"returncode": True}, f"cannot inspect {field}"),
            ("malformed", {"stdout": marker + "\n"},
             f"{field} must have exactly one committed creation point"),
            ("nonstring", {"stdout": b"a" * 40}, f"cannot inspect {field} output"),
            ("oversized", {"stdout": "a" * 257}, f"cannot inspect {field} output"),
            ("timeout", {"error": subprocess.TimeoutExpired(["git", "log"], 20, stderr=marker)},
             f"cannot inspect {field}"),
            ("unavailable", {"error": OSError(marker)}, f"cannot inspect {field}"),
        ]
        for label, changes, expected in cases:
            state.update({"stdout": "a" * 40 + "\n", "returncode": 0, "error": None})
            state.update(changes)
            try:
                source_order.first_commit_for_path(ref, field)
            except source_order.Fail as exc:
                require(str(exc) == expected and marker not in str(exc),
                        f"source-order Git {label} wrong/private diagnostic")
            else:
                raise Fail(f"source-order Git {label} unexpectedly accepted")
        require(len(calls) == 9, "source-order Git negative multiplicity drift")
    finally:
        source_order.subprocess.run = original_run
    print("PASS: source-order Git creation history bounded/private with eight real-reader negatives")



def prove_source_order_bounded_creation_blob(module) -> None:
    """Verify actual creation-blob Git transport with disposable private canaries."""
    source_order = module.load_review_source_order_validator()
    original_run = source_order.subprocess.run
    field = "syntheticSecurityReview"
    object_ref = "a" * 40 + ":docs/evidence/backup-restore/security/synthetic.json"
    marker = "PRIVATE_CREATION_BLOB_MARKER_DO_NOT_LOG"
    payload = b'{"reviewResult":"APPROVED"}\n'
    state = {"size": str(len(payload)) + "\n", "size_exit": 0, "size_error": None,
             "show": payload, "show_exit": 0, "show_error": None}
    calls = []

    def fake_git(args, **kwargs):
        phase = args[1]
        require(phase in ("cat-file", "show"), "creation blob unexpected Git command")
        require(kwargs.get("cwd") == source_order.ROOT and kwargs.get("timeout") == 20
                and kwargs.get("check") is False, "creation blob Git timeout/context drift")
        require(kwargs.get("stdout") is subprocess.PIPE and kwargs.get("stderr") is subprocess.DEVNULL,
                "creation blob Git stderr privacy drift")
        calls.append(phase)
        if phase == "cat-file":
            require(args == ["git", "cat-file", "-s", object_ref] and kwargs.get("text") is True,
                    "creation blob size preflight drift")
            if state["size_error"] is not None:
                raise state["size_error"]
            return subprocess.CompletedProcess(args, state["size_exit"],
                                               stdout=state["size"], stderr=marker)
        require(args == ["git", "show", object_ref] and kwargs.get("text") is None,
                "creation blob byte-exact Git show drift")
        if state["show_error"] is not None:
            raise state["show_error"]
        return subprocess.CompletedProcess(args, state["show_exit"],
                                           stdout=state["show"], stderr=marker)

    source_order.subprocess.run = fake_git
    try:
        require(source_order.creation_blob("a" * 40, object_ref.split(":", 1)[1], field) == payload,
                "creation blob bounded positive control failed")
        cases = [
            ("oversized", {"size": str(source_order.MAX_JSON_BYTES + 1) + "\n"},
             f"{field} creation blob size limit exceeded", 1),
            ("zero", {"size": "0\n"}, f"{field} creation blob size limit exceeded", 1),
            ("invalid-size", {"size": marker + "\n"}, f"cannot inspect {field} creation blob", 1),
            ("nonzero-size", {"size_exit": 1}, f"cannot inspect {field} creation blob", 1),
            ("timeout-size", {"size_error": subprocess.TimeoutExpired(["git", "cat-file"], 20, stderr=marker)},
             f"cannot inspect {field} creation blob", 1),
            ("unavailable-size", {"size_error": OSError(marker)}, f"cannot inspect {field} creation blob", 1),
            ("mismatch", {"show": b"changed"}, f"{field} creation blob size mismatch", 2),
            ("nonzero-show", {"show_exit": 1}, f"cannot inspect {field} creation blob", 2),
            ("nonbytes-show", {"show": marker}, f"cannot inspect {field} creation blob", 2),
            ("timeout-show", {"show_error": subprocess.TimeoutExpired(["git", "show"], 20, stderr=marker)},
             f"cannot inspect {field} creation blob", 2),
            ("unavailable-show", {"show_error": OSError(marker)}, f"cannot inspect {field} creation blob", 2),
        ]
        for label, changes, expected, expected_calls in cases:
            state.update({"size": str(len(payload)) + "\n", "size_exit": 0, "size_error": None,
                          "show": payload, "show_exit": 0, "show_error": None})
            state.update(changes)
            before = len(calls)
            try:
                source_order.creation_blob("a" * 40, object_ref.split(":", 1)[1], field)
            except source_order.Fail as exc:
                require(str(exc) == expected and marker not in str(exc),
                        f"creation blob {label} wrong/private failure class")
            else:
                raise Fail(f"creation blob {label} unexpectedly accepted")
            require(len(calls) - before == expected_calls,
                    f"creation blob {label} failed to stop at the intended Git phase")
        require(len(calls) == 2 + sum(case[3] for case in cases),
                "creation blob Git transport negative multiplicity drift")
    finally:
        source_order.subprocess.run = original_run
    print("PASS: source-order creation blob bounded/private with eleven real-reader negatives")



def prove_source_order_bounded_current_blob(module) -> None:
    """Exercise the actual row consumer with isolated oversized/unreadable review files."""
    from datetime import datetime, timezone

    source_order = module.load_review_source_order_validator()
    original = {name: getattr(source_order, name) for name in (
        "commit_exists", "commit_time", "canonical_review_ref",
        "first_commit_for_path", "require_source_precedes_review",
        "creation_blob", "load_json",
    )}
    row = base_row()
    payload = b'{"reviewedAt":"2026-09-12T09:05:00Z"}' + bytes([10])
    with tempfile.TemporaryDirectory(prefix="source-order-current-blob-negative-") as tmp:
        path = Path(tmp) / "review.json"
        path.write_bytes(payload)
        observed = {"created": 0}

        def fake_creation(*_args):
            observed["created"] += 1
            return payload

        try:
            source_order.commit_exists = lambda *_args: None
            source_order.commit_time = lambda sha, _field: datetime(
                2026, 9, 12, 9, 0 if sha == row["sourceCommitSha"] else 10,
                tzinfo=timezone.utc,
            )
            source_order.canonical_review_ref = lambda ref, _field, material_delta=False: (ref, path)
            source_order.first_commit_for_path = lambda *_args: "b" * 40
            source_order.require_source_precedes_review = lambda *_args: None
            source_order.creation_blob = fake_creation
            source_order.load_json = lambda *_args: {"reviewedAt": "2026-09-12T09:05:00Z"}
            source_order.validate_row(row, 0)
            require(observed["created"] == 3, "current blob positive did not inspect all three reviews")
            for label, fixture, expected in (
                ("oversized", b"x" * (source_order.MAX_JSON_BYTES + 1),
                 "records[0].securityReviewRef current blob size limit exceeded"),
            ):
                path.write_bytes(fixture)
                before = observed["created"]
                try:
                    source_order.validate_row(row, 0)
                except source_order.Fail as exc:
                    require(str(exc) == expected,
                            f"current blob {label} rejected at wrong boundary")
                else:
                    raise Fail(f"current blob {label} unexpectedly accepted")
                require(observed["created"] == before,
                        f"current blob {label} reached creation Git before size refusal")
                require(path.read_bytes() == fixture, "current blob negative mutated fixture")
            path.unlink()
            path.mkdir()
            before = observed["created"]
            try:
                source_order.validate_row(row, 0)
            except source_order.Fail as exc:
                require(str(exc) == "cannot read records[0].securityReviewRef current blob",
                        "current blob directory failure leaked path details")
            else:
                raise Fail("current blob directory unexpectedly accepted")
            require(observed["created"] == before,
                    "unreadable current blob reached creation Git")
            path.rmdir()
            path.write_bytes(payload)
            source_order.validate_row(row, 0)
            require(observed["created"] == 6,
                    "current blob restored positive did not inspect all three reviews")
        finally:
            for name, value in original.items():
                setattr(source_order, name, value)
    print("PASS: source-order current review bytes bounded and private with oversized/directory negatives")



def prove_source_order_bounded_commit_checks(module) -> None:
    """Exercise actual source-order commit/ancestry subprocess failure classes."""
    source_order = module.load_review_source_order_validator()
    original_run = source_order.subprocess.run
    ancestor, descendant = "a" * 40, "b" * 40
    field = "syntheticReview"
    marker = "PRIVATE_COMMIT_GIT_MARKER_DO_NOT_LOG"
    state = {"returncode": 0, "error": None}
    calls = []

    def fake_git(args, **kwargs):
        require(args in (
            ["git", "cat-file", "-e", ancestor + "^{commit}"],
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        ), "source-order commit Git command drift")
        require(kwargs.get("cwd") == source_order.ROOT
                and kwargs.get("stdout") is subprocess.DEVNULL
                and kwargs.get("stderr") is subprocess.DEVNULL
                and kwargs.get("timeout") == 20 and kwargs.get("check") is False,
                "source-order commit Git privacy/timeout drift")
        calls.append(args[1])
        if state["error"] is not None:
            raise state["error"]
        return subprocess.CompletedProcess(args, state["returncode"],
                                           stdout=marker, stderr=marker)

    source_order.subprocess.run = fake_git
    try:
        source_order.commit_exists(ancestor, field)
        require(source_order.is_ancestor(ancestor, descendant) is True,
                "source-order ancestor positive control failed")
        state["returncode"] = 1
        require(source_order.is_ancestor(ancestor, descendant) is False,
                "source-order non-ancestor positive control failed")
        for label, changes, expected in (
            ("commit-nonzero", {"returncode": 1}, f"{field} sourceCommitSha must resolve to a commit"),
            ("commit-bool", {"returncode": True}, f"{field} sourceCommitSha must resolve to a commit"),
            ("commit-timeout", {"error": subprocess.TimeoutExpired(["git", "cat-file"], 20, stderr=marker)},
             f"{field} sourceCommitSha must resolve to a commit"),
            ("commit-unavailable", {"error": OSError(marker)}, f"{field} sourceCommitSha must resolve to a commit"),
            ("ancestor-other", {"returncode": 2}, "cannot compare review/source commit ancestry"),
            ("ancestor-bool", {"returncode": True}, "cannot compare review/source commit ancestry"),
            ("ancestor-timeout", {"error": subprocess.TimeoutExpired(["git", "merge-base"], 20, stderr=marker)},
             "cannot compare review/source commit ancestry"),
            ("ancestor-unavailable", {"error": OSError(marker)}, "cannot compare review/source commit ancestry"),
        ):
            state.update({"returncode": 0, "error": None})
            state.update(changes)
            try:
                if label.startswith("commit-"):
                    source_order.commit_exists(ancestor, field)
                else:
                    source_order.is_ancestor(ancestor, descendant)
            except source_order.Fail as exc:
                require(str(exc) == expected and marker not in str(exc),
                        f"source-order {label} wrong/private diagnostic")
            else:
                raise Fail(f"source-order {label} unexpectedly accepted")
        require(len(calls) == 11, "source-order commit Git transport multiplicity drift")
        before = len(calls)
        try:
            source_order.commit_exists("INVALID_SHA", field)
        except source_order.Fail as exc:
            require(str(exc) == f"{field} sourceCommitSha invalid",
                    "source-order invalid SHA wrong boundary")
        else:
            raise Fail("source-order invalid SHA unexpectedly accepted")
        require(len(calls) == before, "source-order invalid SHA reached Git")
    finally:
        source_order.subprocess.run = original_run
    print("PASS: source-order commit existence and ancestry bounded/private with nine negatives")


def main() -> int:
    require_external_source_order_guard_negative_proof()
    prove_candidate_pair_source_binding()
    module = load_validator()
    prove_runtime_review_pair_controls()
    prove_source_order_bounded_git_output(module)
    prove_source_order_bounded_creation_blob(module)
    prove_source_order_bounded_current_blob(module)
    prove_source_order_bounded_commit_checks(module)
    prove_independent_review_json_reader(module)
    expect_source_order_execution(module)

    for field, substitute in (
        ("CONTRACT", module.REGISTRY),
        ("REGISTRY", module.CONTRACT),
        ("MATERIAL_DELTA_VALIDATOR", SUBSTITUTE),
        ("REVIEW_SOURCE_ORDER_VALIDATOR", SUBSTITUTE),
        ("VALIDATOR", SUBSTITUTE),
    ):
        expect_authority_substitution_fail(module, field, substitute)

    for field, replacement in (
        ("enforce_execution_authority", lambda: None),
        ("enforce_runtime_authorities", lambda: None),
        ("require", lambda *_args: None),
        ("require_exact_repo_file", lambda path, *_args: path),
        ("load_json", lambda *_args: {}),
        ("validate_contract_authority", lambda: None),
        ("canonical_ref", lambda *_args: ("docs/evidence/backup-restore/fake.json", Path("/tmp/fake-review.json"))),
        ("git_history", lambda *_args: ["a" * 40]),
        ("require_append_only_review", lambda *_args: None),
        ("require_utc_rfc3339", lambda value, _field: value),
        ("validate_review", lambda *_args: ("docs/evidence/backup-restore/fake.json", "reviewer-fake")),
        ("load_material_delta_validator", lambda: object()),
        ("load_review_source_order_validator", lambda: object()),
    ):
        expect_execution_substitution_fail(module, field, replacement)
    expect_main_candidate_substitution_fail(module)

    unreviewed = base_row()
    unreviewed.pop("securityReviewRef")
    unreviewed.pop("operabilityReviewRef")
    unreviewed.pop("materialDeltaReviewRef")
    expect_pass(module, registry(unreviewed), "unreviewed non-candidate generation evidence")

    security_only = dict(unreviewed)
    security_only["securityReviewRef"] = "docs/evidence/backup-restore/security/synthetic-review.json"
    expect_fail(module, registry(security_only), "security-only partial review pair", "must provide Security and Operability reviews together")

    operability_only = dict(unreviewed)
    operability_only["operabilityReviewRef"] = "docs/evidence/backup-restore/operability/synthetic-review.json"
    expect_fail(module, registry(operability_only), "operability-only partial review pair", "must provide Security and Operability reviews together")

    expect_fail(module, registry(base_row()), "generic repository review refs",
                "review source-order authority invalid: records[-1].securityReviewRef must remain inside docs/evidence/backup-restore/")

    missing_ref = base_row()
    missing_ref["securityReviewRef"] = "docs/evidence/backup-restore/README.md"
    missing_ref["operabilityReviewRef"] = "docs/evidence/backup-restore/README.md"
    expect_fail(module, registry(missing_ref), "missing in-namespace review evidence",
                "review source-order authority invalid: records[-1].securityReviewRef missing or escapes repository")

    for field in ("productionEvidence", "productionReady"):
        production_boundary = registry(base_row())
        production_boundary[field] = True
        expect_fail(module, production_boundary, f"{field} promotion")

    # Each review role has an independently passing canonical synthetic control.
    # Every mutation must fail at its own typed-review boundary, not merely throw Fail.
    for role in ("SECURITY", "OPERABILITY"):
        expect_review_payload_pass(module, role)
        for field in module.BOUND_FIELDS:
            expect_bound_field_fail(module, field, role)

        for field in ("productionTrafficChanged", "productionCredentialsUsed", "automaticPromotion"):
            payload = typed_payload(base_row(), role)
            payload[field] = True
            diagnostic = {
                "productionTrafficChanged": "cannot change production traffic",
                "productionCredentialsUsed": "cannot use production credentials",
                "automaticPromotion": "cannot authorize automatic promotion",
            }[field]
            expect_review_payload_fail(module, payload, f"{role} unsafe production boundary: {field}", diagnostic, role)

        payload = typed_payload(base_row(), role)
        payload["reviewRole"] = "OPERABILITY" if role == "SECURITY" else "SECURITY"
        expect_review_payload_fail(module, payload, f"{role} review role mismatch", "reviewRole mismatch", role)

        payload = typed_payload(base_row(), role)
        payload["reviewResult"] = "REJECTED"
        expect_review_payload_fail(module, payload, f"{role} review not approved", "review must be APPROVED", role)

        for invalid_reviewed_at in (
            "2026-08-15",
            "2026-08-15T00:00:00+00:00",
            "2026-08-15T00:00:00.000Z",
            "2026-13-15T00:00:00Z",
        ):
            payload = typed_payload(base_row(), role)
            payload["reviewedAt"] = invalid_reviewed_at
            expect_review_payload_fail(module, payload, f"{role} non-canonical reviewedAt: {invalid_reviewed_at}",
                                       "reviewedAt must be canonical UTC RFC3339 seconds", role)

        for invalid_reviewer in (
            "ab", "Security Reviewer", "security@example.com", "../security",
            "SECURITY_REVIEWER", " reviewer-security",
        ):
            payload = typed_payload(base_row(), role)
            payload["reviewerPseudonym"] = invalid_reviewer
            expect_review_payload_fail(module, payload, f"{role} unsafe reviewer pseudonym: {invalid_reviewer}",
                                       "reviewerPseudonym invalid", role)

        for field_set_mutation in ("MISSING", "EXTRA"):
            payload = typed_payload(base_row(), role)
            if field_set_mutation == "MISSING":
                del payload["reviewedAt"]
            else:
                payload["unexpectedField"] = False
            expect_review_payload_fail(module, payload, f"{role} review field set {field_set_mutation}",
                                       "typed review fields drift", role)

        payload = typed_payload(base_row(), role)
        payload["schemaVersion"] = "memory-os-backup-restore-generation-review-evidence.v0"
        expect_review_payload_fail(module, payload, f"{role} obsolete review schema",
                                   "schemaVersion drift", role)
        expect_review_payload_pass(module, role)

    expect_contract_fail(
        module, lambda contract: contract["requiredIndependentReviewEvidenceFields"].remove("drillRequestId"),
        "required review field removed", "independent review required field authority drift",
    )
    expect_contract_fail(
        module, lambda contract: contract["requiredIndependentReviewEvidenceFields"].append("drillRequestId"),
        "duplicate required review field", "independent review required field authority drift",
    )
    expect_contract_fail(
        module, lambda contract: contract["requiredIndependentReviewEvidenceFields"].append("unexpectedField"),
        "unexpected required review field", "independent review required field authority drift",
    )
    expect_contract_fail(
        module, lambda contract: contract.__setitem__("independentReviewEvidenceSchemaVersion", "memory-os-backup-restore-generation-review-evidence.v0"),
        "review schema authority downgraded", "independent review evidence schema authority drift",
    )
    expect_contract_fail(
        module, lambda contract: contract.__setitem__("independentReviewEvidenceRoot", "docs/evidence"),
        "review namespace widened", "independent review evidence root authority drift",
    )
    expect_contract_fail(
        module, lambda contract: contract.__setitem__("materialDeltaReviewValidator", "scripts/validate-memory-os-backup-restore-generation-evidence.py"),
        "candidate material-delta validator substituted", "candidate material-delta review validator authority drift",
    )
    expect_contract_fail(
        module, lambda contract: contract.__setitem__("reviewSourceOrderValidator", "scripts/validate-memory-os-backup-restore-generation-evidence.py"),
        "candidate review source-order validator substituted", "candidate review source-order validator authority drift",
    )
    expect_contract_fail(
        module, lambda contract: contract["independentReviewRoles"].__setitem__("securityReviewRef", "OPERABILITY"),
        "review role map substituted", "independent review role authority drift",
    )
    required_rules = (
        "independentSecurityAndOperabilityReviewsRequired",
        "typedIndependentReviewEvidenceRequired",
        "candidateDerivationMustUseTypedIndependentReviewAuthority",
        "independentReviewEvidenceMustRemainInsideMonitoredNamespace",
        "independentReviewRoleMustMatchReference",
        "independentReviewMustBeApproved",
        "independentReviewReviewerPseudonymsMustBeDistinct",
        "independentReviewPayloadMustRemainAppendOnlyAfterFirstCommit",
        "independentReviewMustBeCreatedStrictlyAfterSourceCommit",
        "crossGenerationMaterialDeltaReviewMustBeCreatedStrictlyAfterSourceCommit",
        "independentReviewCannotAuthorizeAutomaticPromotion",
    )
    for rule in required_rules:
        expect_contract_fail(
            module, lambda contract, rule=rule: contract["recordRules"].__setitem__(rule, False),
            f"mandatory independent review rule disabled: {rule}",
            f"independent review contract rule drift: {rule}",
        )
    for field, rule in module.BOUND_RULE_BY_FIELD.items():
        expect_contract_fail(
            module, lambda contract, rule=rule: contract["recordRules"].__setitem__(rule, False),
            f"mandatory independent review binding disabled: {field}",
            f"independent review binding rule drift: {field}",
        )
    expect_contract_fail(
        module, lambda contract: contract["promotionBoundary"].__setitem__(
            "completeReviewedRecordAlsoRequiresTypedAppendOnlyIndependentReviews", False
        ),
        "independent review promotion boundary disabled", "independent review promotion boundary drift",
    )

    exercise_bounded_review_git_history(module)

    original_history = module.git_history
    original_transport = module.subprocess.run
    try:
        review_ref = "docs/evidence/backup-restore/synthetic-review.json"
        module.git_history = lambda _ref, _field: ["a" * 40, "b" * 40]
        try:
            module.require_append_only_review(
                review_ref, Path("/tmp/not-read-after-history-rejection"), "securityReviewRef",
            )
        except module.Fail as exc:
            require(str(exc) == "securityReviewRef must remain append-only after its first committed version",
                    f"review history mutation rejected at wrong boundary: {exc}")
        else:
            raise Fail("review evidence with multiple committed versions was accepted")

        with tempfile.TemporaryDirectory(prefix="generation-review-immutability-negative-") as tmp:
            path = Path(tmp) / "synthetic-review.json"
            creation_bytes = b'{"reviewResult":"APPROVED"}\n'
            path.write_bytes(creation_bytes)
            module.git_history = lambda _ref, _field: ["a" * 40]

            def synthetic_git_show(args, **_kwargs):
                require(args == ["git", "show", f"{'a' * 40}:{review_ref}"],
                        f"unexpected synthetic review history transport: {args}")
                return subprocess.CompletedProcess(args, 0, stdout=creation_bytes, stderr=b"")

            module.subprocess.run = synthetic_git_show
            module.require_append_only_review(review_ref, path, "securityReviewRef")
            path.write_bytes(b'{"reviewResult":"REJECTED"}\n')
            try:
                module.require_append_only_review(review_ref, path, "securityReviewRef")
            except module.Fail as exc:
                require(str(exc) == "securityReviewRef bytes drift from initial committed review evidence",
                        f"review byte mutation rejected at wrong boundary: {exc}")
            else:
                raise Fail("review evidence byte mutation after initial commit was accepted")
            path.write_bytes(creation_bytes)
            module.require_append_only_review(review_ref, path, "securityReviewRef")
    finally:
        module.git_history = original_history
        module.subprocess.run = original_transport
    print("PASS: review append-only history and initial-blob immutability positive/negative controls")

    print("PASS: generation candidate review negatives reject runtime data/executable/helper substitution, source-order authority substitution, partial review pairs, generic refs, missing review evidence, candidate pair source binding, authority mismatch, malformed timestamps, unsafe reviewer identities, unsafe production boundaries, wrong roles, non-approved reviews, chronology/candidate/promotion contract drift, post-commit edits, and production promotion while preserving unreviewed non-candidate evidence")
    print("runtime data/executable authority substitution accepted: false")
    print("runtime execution helper substitution accepted: false")
    print("review source-order authority substitution accepted: false")
    print("main candidate authority substitution accepted: false")
    print("unreviewed non-candidate generation evidence accepted: true")
    print("partial independent review pairs accepted: false")
    print("canonical generation evidence authority mutated during negative exercises: false")
    print("human production promotion remains separate: true")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
