#!/usr/bin/env python3
"""Focused negatives for the rate-limit operation evidence writer guard."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "scripts/create-memory-os-rate-limit-operation-evidence.py"


def load_writer():
    spec = importlib.util.spec_from_file_location(
        "memory_os_rate_limit_operation_writer", WRITER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load rate-limit operation evidence writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args: str, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def detached_side_commit() -> str:
    tree = git("rev-parse", "HEAD^{tree}")
    parent = git("rev-parse", "HEAD^")
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "memory-os-lineage-test",
            "GIT_AUTHOR_EMAIL": "memory-os-lineage-test@example.invalid",
            "GIT_COMMITTER_NAME": "memory-os-lineage-test",
            "GIT_COMMITTER_EMAIL": "memory-os-lineage-test@example.invalid",
        }
    )
    return git("commit-tree", tree, "-p", parent, "-m", "synthetic side commit", env=env)


def expect_evidence_ref_rejection(validator, ref: str, expected: str) -> None:
    try:
        validator.canonical_evidence_path(ref, "syntheticEvidenceRefs")
    except validator.ValidationFailure as exc:
        if expected not in str(exc):
            raise AssertionError(f"unexpected evidence ref rejection: {exc}") from exc
    else:
        raise AssertionError(f"unsafe evidence ref was incorrectly accepted: {ref}")


def contract_guard_negative(writer, validator) -> None:
    contract, _ = validator.load_contract_context()
    writer.validate_contract_append_guards(contract)

    for guard in sorted(writer.REQUIRED_APPEND_GUARDS):
        mutated = dict(contract)
        mutated_guards = dict(contract["appendOnlyGuards"])
        mutated_guards[guard] = False
        mutated["appendOnlyGuards"] = mutated_guards
        try:
            writer.validate_contract_append_guards(mutated)
        except writer.WriterFailure as exc:
            if f"appendOnlyGuards.{guard} must be true" not in str(exc):
                raise AssertionError(f"unexpected append guard rejection: {exc}") from exc
        else:
            raise AssertionError(f"disabled append guard was incorrectly accepted: {guard}")

    mutated = dict(contract)
    mutated_guards = dict(contract["appendOnlyGuards"])
    mutated_guards["unexpectedGuard"] = True
    mutated["appendOnlyGuards"] = mutated_guards
    try:
        writer.validate_contract_append_guards(mutated)
    except writer.WriterFailure as exc:
        if "appendOnlyGuards authority field set drift" not in str(exc):
            raise AssertionError(f"unexpected append guard field-set rejection: {exc}") from exc
    else:
        raise AssertionError("unknown append guard field was incorrectly accepted")


def digest_binding_negative(writer, validator, current_head: str) -> None:
    contract, policy_ids = validator.load_contract_context()
    required_checks = contract["record"]["requiredVerificationChecks"]
    record = {
        "schemaVersion": contract["recordSchemaVersion"],
        "operationId": "RLOP-20260101T000000Z-digesttest",
        "incidentReference": "DRILL-DIGEST_BINDING",
        "sourceCommitSha": current_head,
        "environment": "CI",
        "operator": "ci_operator",
        "reviewer": "ci_reviewer",
        "previousMode": "NORMAL_CONFIGURED",
        "newMode": "STRICT_LOCAL_EMERGENCY",
        "proxyMode": "TRUSTED_PROXY_DISABLED",
        "affectedPolicyIds": [sorted(policy_ids)[0]],
        "startedAt": "2026-01-01T00:00:00Z",
        "expiresAt": "2026-01-01T00:30:00Z",
        "activationReason": "DRILL",
        "lifecycle": "ACTIVE",
        "productionConfirmation": None,
        "verificationResults": [
            {"checkId": check, "result": "NOT_RUN", "evidenceRefs": []}
            for check in required_checks
        ],
        "restoredAt": None,
        "openRisks": ["digest_binding_test"],
        "evidenceRefs": [
            "contracts/operations/rate-limit-operation-evidence-contract.v1.json"
        ],
        "evidenceDigestsByRef": {},
    }
    validator.validate_record(record, contract, policy_ids, writer_input=True)
    computed = validator.expected_evidence_digests(record)
    if not computed:
        raise AssertionError("writer-computed evidence digest set unexpectedly empty")

    self_claimed = dict(record)
    self_claimed["evidenceDigestsByRef"] = dict(computed)
    try:
        validator.validate_record(self_claimed, contract, policy_ids, writer_input=True)
    except validator.ValidationFailure as exc:
        if "writer input evidenceDigestsByRef must be empty" not in str(exc):
            raise AssertionError(f"unexpected self-claimed digest rejection: {exc}") from exc
    else:
        raise AssertionError("writer input was allowed to self-claim evidence digests")

    stored = dict(record)
    stored["evidenceDigestsByRef"] = dict(computed)
    validator.validate_record(stored, contract, policy_ids)

    tampered = dict(stored)
    tampered_digests = dict(computed)
    first_ref = sorted(tampered_digests)[0]
    tampered_digests[first_ref] = "0" * 64
    tampered["evidenceDigestsByRef"] = tampered_digests
    try:
        validator.validate_record(tampered, contract, policy_ids)
    except validator.ValidationFailure as exc:
        if "does not match current evidence bytes" not in str(exc):
            raise AssertionError(f"unexpected digest mismatch rejection: {exc}") from exc
    else:
        raise AssertionError("stale evidence digest was incorrectly accepted")


def post_append_rollback_negative(writer) -> None:
    class FakeValidationFailure(RuntimeError):
        pass

    valid_guards = {guard: True for guard in writer.REQUIRED_APPEND_GUARDS}

    class PostAppendRejectingValidator:
        ValidationFailure = FakeValidationFailure
        calls = 0

        @staticmethod
        def load_contract_context():
            return {"appendOnlyGuards": dict(valid_guards)}, set()

        @staticmethod
        def validate_record(record, contract, policy_ids, writer_input=False) -> None:
            if not isinstance(record.get("operationId"), str):
                raise AssertionError("synthetic writer input lost operationId")

        @staticmethod
        def expected_evidence_digests(record):
            return {}

        @classmethod
        def main(cls) -> int:
            cls.calls += 1
            if cls.calls == 1:
                return 0
            raise FakeValidationFailure("synthetic post-append authority rejection")

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        ledger = root / "ledger"
        input_path = root / "record.json"
        operation_id = "RLOP-20260101T000000Z-postappend"
        input_path.write_text(f'{{"operationId":"{operation_id}"}}\n', encoding="utf-8")

        original_default_ledger = writer.DEFAULT_LEDGER
        original_load_validator = writer.load_validator
        original_argv = sys.argv[:]
        try:
            writer.DEFAULT_LEDGER = ledger
            writer.load_validator = lambda: PostAppendRejectingValidator
            sys.argv = ["writer", "--input", str(input_path)]
            try:
                writer.main()
            except writer.WriterFailure as exc:
                if "failed validation after append" not in str(exc):
                    raise AssertionError(f"unexpected post-append rejection: {exc}") from exc
            else:
                raise AssertionError("post-append canonical validation failure was accepted")
        finally:
            writer.DEFAULT_LEDGER = original_default_ledger
            writer.load_validator = original_load_validator
            sys.argv = original_argv

        target = ledger / f"{operation_id}.json"
        if target.exists():
            raise AssertionError("invalid operation append was not rolled back")
        if PostAppendRejectingValidator.calls != 2:
            raise AssertionError(
                "canonical authority was not validated exactly before and after append"
            )


def main() -> int:
    writer = load_writer()

    class FakeValidationFailure(RuntimeError):
        pass

    class RejectingValidator:
        ValidationFailure = FakeValidationFailure

        @staticmethod
        def main() -> int:
            raise FakeValidationFailure("synthetic canonical ledger corruption")

    try:
        writer.validate_existing_canonical_authority(
            RejectingValidator(), writer.DEFAULT_LEDGER.resolve()
        )
    except writer.WriterFailure as exc:
        if "failed validation before append" not in str(exc):
            raise AssertionError(f"unexpected canonical rejection: {exc}") from exc
    else:
        raise AssertionError("canonical ledger corruption was incorrectly accepted")

    class NonZeroValidator:
        ValidationFailure = FakeValidationFailure

        @staticmethod
        def main() -> int:
            return 7

    try:
        writer.validate_existing_canonical_authority(
            NonZeroValidator(), writer.DEFAULT_LEDGER.resolve()
        )
    except writer.WriterFailure as exc:
        if "returned non-zero before append: 7" not in str(exc):
            raise AssertionError(f"unexpected non-zero rejection: {exc}") from exc
    else:
        raise AssertionError("non-zero canonical validation was incorrectly accepted")

    class AlternateLedgerValidator:
        ValidationFailure = FakeValidationFailure
        calls = 0

        @classmethod
        def main(cls) -> int:
            cls.calls += 1
            raise AssertionError("alternate CI ledger must not validate canonical authority")

    with tempfile.TemporaryDirectory() as tmpdir:
        writer.validate_existing_canonical_authority(
            AlternateLedgerValidator(), Path(tmpdir).resolve()
        )
    if AlternateLedgerValidator.calls != 0:
        raise AssertionError("alternate ledger unexpectedly invoked canonical validation")

    validator = writer.load_validator()
    contract_guard_negative(writer, validator)
    post_append_rollback_negative(writer)

    current_head = git("rev-parse", "HEAD")
    validator.require_source_ancestor(current_head)
    side_commit = detached_side_commit()
    try:
        validator.require_source_ancestor(side_commit)
    except validator.ValidationFailure as exc:
        if "ancestor of current HEAD" not in str(exc):
            raise AssertionError(f"unexpected lineage rejection: {exc}") from exc
    else:
        raise AssertionError("detached side commit was incorrectly accepted as source authority")
    if git("rev-parse", "HEAD") != current_head:
        raise AssertionError("lineage negative changed the current branch ref")

    ledger_root = writer.DEFAULT_LEDGER
    untracked = ledger_root / ".rate-limit-operation-untracked-negative.json"
    symlink = ledger_root / ".rate-limit-operation-symlink-negative.json"
    try:
        untracked.write_text("{}\n", encoding="utf-8")
        expect_evidence_ref_rejection(
            validator,
            untracked.relative_to(ROOT).as_posix(),
            "git ls-files",
        )
        symlink.symlink_to(ledger_root / "README.md")
        expect_evidence_ref_rejection(
            validator,
            symlink.relative_to(ROOT).as_posix(),
            "cannot traverse symlink",
        )
    finally:
        symlink.unlink(missing_ok=True)
        untracked.unlink(missing_ok=True)

    digest_binding_negative(writer, validator, current_head)

    if git("status", "--porcelain"):
        raise AssertionError("rate-limit operation negatives left the checkout dirty")

    print("PASS: canonical rate-limit operation ledger is validated before append")
    print("PASS: rate-limit operation append rollback contract is fail-closed")
    print("PASS: invalid canonical operation append is rolled back after validation")
    print("PASS: detached rate-limit operation source commits are rejected")
    print("PASS: untracked and symlinked operation evidence refs are rejected")
    print("PASS: operation evidence digests are writer-computed and tamper-evident")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
