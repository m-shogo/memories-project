#!/usr/bin/env python3
"""Focused negatives for the rate-limit operation evidence writer guard."""

from __future__ import annotations

import importlib.util
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

        @staticmethod
        def main() -> int:
            raise FakeValidationFailure("synthetic canonical validation rejection")

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        ledger = root / "ledger"
        input_path = root / "record.json"
        operation_id = "RLOP-20260101T000000Z-postappend"
        input_path.write_text(f'{{"operationId":"{operation_id}"}}\n', encoding="utf-8")

        # Fixture paths exercise the pure append helper. Actual CLI authority is
        # separately pinned by validate-memory-os-rate-limit-operation-writer-authority-negative.py.
        target = ledger / f"{operation_id}.json"
        writer.append_record(input_path, ledger, RejectAfterAppend)
        if not target.exists():
            raise AssertionError("alternate fixture append did not create the expected record")
        target.unlink()


def digest_binding_negative(validator) -> None:
    contract, policy_ids = validator.load_contract_context()
    required_checks = contract["record"]["requiredVerificationChecks"]
    record = {
        "schemaVersion": contract["recordSchemaVersion"],
        "operationId": "RLOP-20260101T000000Z-digesttest",
        "incidentReference": "DRILL-DIGEST_BINDING",
        "sourceCommitSha": "HEAD",
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
    # Writer inputs cannot self-claim digests. Stored records must match current bytes.
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
    print("PASS: append rollback authority is separated from CLI authority fixtures")
    print("PASS: rate-limit operation reconcile delegates to append authority")
    print("PASS: operation evidence digests remain writer-computed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
