#!/usr/bin/env python3
"""Focused negatives for the rate-limit operation evidence writer guard."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "scripts/create-memory-os-rate-limit-operation-evidence.py"
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-rate-limit-operation-evidence.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load rate-limit operation module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f"git rev-parse HEAD failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def expect_failure(call, error_type, expected: str) -> None:
    try:
        call()
    except error_type as exc:
        if expected not in str(exc):
            raise AssertionError(f"unexpected rejection: {exc}") from exc
    else:
        raise AssertionError(f"expected rejection containing {expected!r}")


def contract_guard_negative(writer, validator) -> None:
    contract, _ = validator.load_contract_context()
    writer.validate_contract_append_guards(contract)
    for guard in sorted(writer.REQUIRED_APPEND_GUARDS):
        mutated = dict(contract)
        guards = dict(contract["appendOnlyGuards"])
        guards[guard] = False
        mutated["appendOnlyGuards"] = guards
        expect_failure(
            lambda mutated=mutated: writer.validate_contract_append_guards(mutated),
            writer.WriterFailure,
            f"appendOnlyGuards.{guard} must be true",
        )

    mutated = dict(contract)
    guards = dict(contract["appendOnlyGuards"])
    guards["unexpectedGuard"] = True
    mutated["appendOnlyGuards"] = guards
    expect_failure(
        lambda: writer.validate_contract_append_guards(mutated),
        writer.WriterFailure,
        "appendOnlyGuards authority field set drift",
    )


def reconcile_contract_guard_negative(writer, validator) -> None:
    reconciler = load_module(RECONCILER_PATH, "memory_os_rate_limit_operation_reconciler")
    contract, _ = validator.load_contract_context()
    mutated = dict(contract)
    guards = dict(contract["appendOnlyGuards"])
    guards["postAppendValidationFailureMustRemoveNewRecord"] = False
    mutated["appendOnlyGuards"] = guards
    expect_failure(
        lambda: reconciler.validate_evidence_authority(mutated),
        reconciler.ReconcileFailure,
        "append authority invalid",
    )


def post_append_rollback_negative(writer) -> None:
    class FakeValidationFailure(RuntimeError):
        pass

    valid_guards = {guard: True for guard in writer.REQUIRED_APPEND_GUARDS}

    class RejectAfterAppend:
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

        expect_failure(
            lambda: writer.append_record(
                input_path,
                ledger,
                RejectAfterAppend,
                _canonical_default_ledger=ledger,
            ),
            writer.WriterFailure,
            "failed validation after append",
        )
        target = ledger / f"{operation_id}.json"
        if target.exists():
            raise AssertionError("invalid operation append was not rolled back")
        if RejectAfterAppend.calls != 2:
            raise AssertionError("fixture canonical authority was not checked before and after append")


def digest_binding_negative(validator) -> None:
    contract, policy_ids = validator.load_contract_context()
    required_checks = contract["record"]["requiredVerificationChecks"]
    record = {
        "schemaVersion": contract["recordSchemaVersion"],
        "operationId": "RLOP-20260101T000000Z-digesttest",
        "incidentReference": "DRILL-DIGEST_BINDING",
        "sourceCommitSha": git_head(),
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
        "evidenceRefs": ["contracts/operations/rate-limit-operation-evidence-contract.v1.json"],
        "evidenceDigestsByRef": {},
    }
    validator.validate_record(record, contract, policy_ids, writer_input=True)
    computed = validator.expected_evidence_digests(record)
    if not computed:
        raise AssertionError("writer-computed evidence digest set unexpectedly empty")
    claimed = dict(record)
    claimed["evidenceDigestsByRef"] = dict(computed)
    expect_failure(
        lambda: validator.validate_record(claimed, contract, policy_ids, writer_input=True),
        validator.ValidationFailure,
        "writer input evidenceDigestsByRef must be empty",
    )

    stored = dict(record)
    stored["evidenceDigestsByRef"] = dict(computed)
    validator.validate_record(stored, contract, policy_ids)
    first_ref = sorted(computed)[0]
    tampered = dict(stored)
    tampered_digests = dict(computed)
    tampered_digests[first_ref] = "0" * 64
    tampered["evidenceDigestsByRef"] = tampered_digests
    expect_failure(
        lambda: validator.validate_record(tampered, contract, policy_ids),
        validator.ValidationFailure,
        "does not match current evidence bytes",
    )


def main() -> int:
    writer = load_module(WRITER_PATH, "memory_os_rate_limit_operation_writer")
    validator = writer.load_validator()

    class FakeValidationFailure(RuntimeError):
        pass

    class RejectingValidator:
        ValidationFailure = FakeValidationFailure

        @staticmethod
        def main() -> int:
            raise FakeValidationFailure("synthetic canonical ledger corruption")

    expect_failure(
        lambda: writer.validate_existing_canonical_authority(
            RejectingValidator(), writer.DEFAULT_LEDGER.resolve()
        ),
        writer.WriterFailure,
        "failed validation before append",
    )

    class NonZeroValidator:
        ValidationFailure = FakeValidationFailure

        @staticmethod
        def main() -> int:
            return 7

    expect_failure(
        lambda: writer.validate_existing_canonical_authority(
            NonZeroValidator(), writer.DEFAULT_LEDGER.resolve()
        ),
        writer.WriterFailure,
        "returned non-zero before append: 7",
    )

    contract_guard_negative(writer, validator)
    reconcile_contract_guard_negative(writer, validator)
    post_append_rollback_negative(writer)
    digest_binding_negative(validator)

    if any(ROOT.glob("docs/evidence/rate-limit-operations/.rate-limit-operation-*-negative.json")):
        raise AssertionError("rate-limit operation negatives left residue")

    print("PASS: canonical rate-limit operation ledger is validated before append")
    print("PASS: post-append validation rejection removes the new record")
    print("PASS: rate-limit operation reconcile delegates to append authority")
    print("PASS: operation evidence digests remain writer-computed and tamper-evident")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
