#!/usr/bin/env python3
"""Prove deletion mutation evidence reconcile preserves independent authority and rolls back aggregate rejection."""

from __future__ import annotations

import importlib.util
import json
import stat
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-deletion-mutation-evidence.py"


def load_module():
    spec = importlib.util.spec_from_file_location("deletion_mutation_evidence_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load deletion mutation evidence reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def expect_authority_rejection(module, attr: str, replacement: Path) -> None:
    original = getattr(module, attr)
    setattr(module, attr, replacement)
    try:
        try:
            module.enforce_runtime_authorities()
        except module.Fail:
            pass
        else:
            raise AssertionError(f"{attr} substitution must be rejected")
    finally:
        setattr(module, attr, original)


def expect_atomic_replace_failure(module) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-mutation-atomic-") as tmp:
        root = Path(tmp)
        authority = root / "authority.json"
        authority.write_bytes(b"before\n")
        authority.chmod(0o640)
        original_mode = stat.S_IMODE(authority.stat().st_mode)
        original_replace = module.os.replace

        def reject_replace(_source, _target):
            raise OSError("synthetic atomic replacement failure")

        module.os.replace = reject_replace
        try:
            try:
                module.atomic_write_bytes(authority, b"after\n")
            except OSError as exc:
                if "synthetic atomic replacement failure" not in str(exc):
                    raise
            else:
                raise AssertionError("atomic replacement failure was accepted")
        finally:
            module.os.replace = original_replace

        if authority.read_bytes() != b"before\n":
            raise AssertionError("failed atomic replacement changed authority bytes")
        if stat.S_IMODE(authority.stat().st_mode) != original_mode:
            raise AssertionError("failed atomic replacement changed authority mode")
        residue = list(root.glob(f".{authority.name}.*.tmp"))
        if residue:
            raise AssertionError(f"failed atomic replacement left temp residue: {residue!r}")

        module.atomic_write_bytes(authority, b"after\n")
        if authority.read_bytes() != b"after\n":
            raise AssertionError("successful atomic replacement did not update authority")
        if stat.S_IMODE(authority.stat().st_mode) != original_mode:
            raise AssertionError("successful atomic replacement changed authority mode")


def expect_substituted_atomic_paths_rejected(module) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-mutation-atomic-symlink-") as temp_dir:
        root = Path(temp_dir)
        outside = root / "outside"
        outside.mkdir()
        canary = outside / "authority.json"
        canary.write_bytes(b"SYNTHETIC_MUTATION_CANARY")
        direct = root / "direct.json"
        direct.symlink_to(canary)
        ancestor = root / "linked"
        ancestor.symlink_to(outside, target_is_directory=True)
        directory = root / "directory.json"
        directory.mkdir()
        for target, expected in (
            (direct, "deletion mutation atomic symlink target/ancestor refused"),
            (ancestor / "authority.json", "deletion mutation atomic symlink target/ancestor refused"),
            (directory, "deletion mutation atomic target must be a regular file"),
        ):
            try:
                module.atomic_write_bytes(target, b"synthetic overwrite")
            except module.Fail as exc:
                if expected not in str(exc):
                    raise AssertionError(f"mutation atomic unexpected target rejection: {exc}") from exc
            else:
                raise AssertionError(f"mutation atomic accepted substituted target: {target}")
            if canary.read_bytes() != b"SYNTHETIC_MUTATION_CANARY":
                raise AssertionError("mutation atomic writer escaped to external canary")
        if not direct.is_symlink() or not ancestor.is_symlink() or not directory.is_dir():
            raise AssertionError("mutation atomic writer replaced substituted target")
        if list(root.rglob(".*.tmp")):
            raise AssertionError("mutation substituted atomic target left temp residue")


def main() -> int:
    module = load_module()
    substitutions = {
        "MUTATION_CONTRACT": module.LOAD_PATH,
        "MUTATION_RESULT": module.MUTATION_CONTRACT,
        "LOAD_PATH": module.MUTATION_CONTRACT,
        "STATUS_PATH": module.LOAD_PATH,
        "MUTATION_VALIDATOR": module.LOAD_VALIDATOR,
        "LOAD_INDEX_VALIDATOR": module.LOAD_VALIDATOR,
        "LOAD_VALIDATOR": module.MUTATION_VALIDATOR,
        "OPERABILITY_VALIDATOR": module.LOAD_VALIDATOR,
    }
    for attr, replacement in substitutions.items():
        expect_authority_rejection(module, attr, replacement)
    module.enforce_runtime_authorities()
    expect_atomic_replace_failure(module)
    expect_substituted_atomic_paths_rejected(module)

    with tempfile.TemporaryDirectory(prefix="memory-os-mutation-reconcile-") as tmp:
        root = Path(tmp)
        proof_contract = root / "proof-contract.json"
        proof_result = root / "proof-result.json"
        load_contract = root / "load-contract.json"
        status = root / "status.json"
        proof_validator = root / "proof-validator.py"
        load_index_validator = root / "load-index-validator.py"
        load_validator = root / "load-validator.py"
        operability_validator = root / "operability-validator.py"

        write_json(
            proof_contract,
            {"readiness": {"exactSourceResultCommitted": True, "preFenceMutationLinearizationProven": True}},
        )
        write_json(
            proof_result,
            {
                "scenario": {
                    "result": "PASS",
                    "integrityResult": "PASS",
                    "authenticatedBeforeFence": 32,
                    "applyUnauthorizedAfterFence": 16,
                    "uploadAuthorizationUnauthorizedAfterFence": 16,
                    "unexpectedStatusCount": 0,
                    "transportErrors": 0,
                    "preWorkerApplyConfirmationRows": 0,
                    "preWorkerMemoryItemRows": 0,
                    "preWorkerUploadAuthorizationRows": 0,
                    "preWorkerQuarantineRows": 0,
                    "finalOwnedRowCount": 0,
                }
            },
        )
        write_json(
            load_contract,
            {
                "readiness": {
                    "productionEquivalentDependencies": False,
                    "capacityBoundaryEstablished": False,
                    "sustainedSoakEvidence": False,
                    "uploadCompletionPreFenceInFlightLinearizationProven": True,
                    "note": "synthetic local authority",
                },
                "evidenceRefs": [],
                "deferredScenarios": [{"scenarioId": "deletion-under-load", "reason": "synthetic"}],
            },
        )
        write_json(
            status,
            {
                "productionDecision": "NO_GO",
                "areas": [
                    {
                        "id": "OPS-P0-006",
                        "status": "PARTIAL",
                        "blocking": True,
                        "existingEvidence": [],
                        "missingEvidence": [module.UPLOAD_COMPLETION_BLOCKER],
                        "evidenceRefs": [],
                    }
                ],
            },
        )
        load_contract.chmod(0o640)
        status.chmod(0o600)
        load_mode = stat.S_IMODE(load_contract.stat().st_mode)
        status_mode = stat.S_IMODE(status.stat().st_mode)

        module.ROOT = root
        module.MUTATION_CONTRACT = proof_contract
        module.MUTATION_RESULT = proof_result
        module.LOAD_PATH = load_contract
        module.STATUS_PATH = status
        module.MUTATION_VALIDATOR = proof_validator
        module.LOAD_INDEX_VALIDATOR = load_index_validator
        module.LOAD_VALIDATOR = load_validator
        module.OPERABILITY_VALIDATOR = operability_validator
        module.enforce_runtime_authorities = lambda: None

        calls: list[str] = []

        def successful_run(command, *, cwd, check):
            if cwd != root or check is not True:
                raise AssertionError("validator invocation lost fail-closed execution options")
            calls.append(str(command[1]))
            return subprocess.CompletedProcess(command, 0)

        module.subprocess.run = successful_run
        before_load = load_contract.read_bytes()
        before_status = status.read_bytes()
        module.main()
        after_success = json.loads(load_contract.read_text(encoding="utf-8"))
        after_status = json.loads(status.read_text(encoding="utf-8"))
        if after_success["readiness"].get("uploadCompletionPreFenceInFlightLinearizationProven") is not True:
            raise AssertionError("mutation reconcile demoted independently proven upload completion authority")
        if any(
            isinstance(item, str) and item.startswith("pre-fence in-flight linearization for upload-completion requests")
            for item in after_status["areas"][0]["missingEvidence"]
        ):
            raise AssertionError("mutation reconcile reintroduced an independently satisfied upload-completion blocker")
        if stat.S_IMODE(load_contract.stat().st_mode) != load_mode:
            raise AssertionError("successful mutation reconcile changed load authority mode")
        if stat.S_IMODE(status.stat().st_mode) != status_mode:
            raise AssertionError("successful mutation reconcile changed production status mode")
        expected_success = [
            str(proof_validator),
            str(load_index_validator),
            str(load_validator),
            str(operability_validator),
        ]
        if calls != expected_success:
            raise AssertionError(f"successful validator order drift: {calls!r} != {expected_success!r}")

        # Stronger independently published local recovery authority must survive
        # this narrower mutation-evidence reconciler. No production gate changes.
        strong_load = json.loads(before_load)
        strong_load["readiness"].update({
            "deletionContainerKillRecoveryProven": True,
            "deletionReplacementContainerRecoveryProven": True,
            "deletionLeaseExpiryRecoverySimulationProven": True,
            "deletionPartialObjectErasureRecoveryProven": True,
            "primaryAccountBoundPreFenceLinearizationAggregateProven": True,
        })
        strong_load["deferredScenarios"][0]["reason"] = module.CONTAINER_KILL_CANONICAL_REASON
        write_json(load_contract, strong_load)
        module.main()
        after_strong = json.loads(load_contract.read_text(encoding="utf-8"))
        if after_strong["deferredScenarios"][0]["reason"] != module.CONTAINER_KILL_CANONICAL_REASON:
            raise AssertionError("mutation reconcile downgraded independently proven container-kill deferred authority")
        strong_load["readiness"]["deletionContainerKillRecoveryProven"] = False
        write_json(load_contract, strong_load)
        rejected_bytes = load_contract.read_bytes()
        try:
            module.main()
        except module.Fail as exc:
            if "container-kill deferred authority lacks" not in str(exc):
                raise
        else:
            raise AssertionError("mutation reconcile accepted unsupported strong container-kill reason")
        if load_contract.read_bytes() != rejected_bytes:
            raise AssertionError("unsupported strong deferred authority mutated load contract")

        normalized_load = json.loads(before_load)
        normalized_load["readiness"].update({key: True for key in module.NORMALIZED_REQUIRED_TRUE})
        normalized_load["deferredScenarios"][0]["reason"] = module.NORMALIZED_CANONICAL_REASON
        write_json(load_contract, normalized_load)
        module.main()
        after_normalized = json.loads(load_contract.read_text(encoding="utf-8"))
        if after_normalized["deferredScenarios"][0]["reason"] != module.NORMALIZED_CANONICAL_REASON:
            raise AssertionError("mutation reconcile downgraded canonical normalized local coverage")
        normalized_load["readiness"]["deletionReplacementContainerRecoveryProven"] = False
        write_json(load_contract, normalized_load)
        normalized_before = load_contract.read_bytes()
        try:
            module.main()
        except module.Fail as exc:
            if "normalized deferred authority lacks" not in str(exc):
                raise
        else:
            raise AssertionError("mutation reconcile accepted unsupported normalized local coverage")
        if load_contract.read_bytes() != normalized_before:
            raise AssertionError("unsupported normalized reason changed load authority")

        load_contract.write_bytes(before_load)
        status.write_bytes(before_status)
        calls.clear()

        def failing_run(command, *, cwd, check):
            if cwd != root or check is not True:
                raise AssertionError("validator invocation lost fail-closed execution options")
            validator = str(command[1])
            calls.append(validator)
            if validator == str(operability_validator):
                raise subprocess.CalledProcessError(1, command)
            return subprocess.CompletedProcess(command, 0)

        module.subprocess.run = failing_run
        try:
            module.main()
        except module.Fail as exc:
            if ("mutation evidence post-write validation failed: CalledProcessError" not in str(exc)
                    or "returned non-zero exit status" in str(exc)
                    or not exc.__suppress_context__):
                raise AssertionError("mutation reconcile leaked primary validator exception") from exc
        else:
            raise AssertionError("aggregate operability rejection must fail mutation reconcile")

        if load_contract.read_bytes() != before_load:
            raise AssertionError("load authority changed after rejected mutation reconcile")
        if status.read_bytes() != before_status:
            raise AssertionError("production status changed after rejected mutation reconcile")
        if stat.S_IMODE(load_contract.stat().st_mode) != load_mode:
            raise AssertionError("rejected mutation reconcile changed load authority mode")
        if stat.S_IMODE(status.stat().st_mode) != status_mode:
            raise AssertionError("rejected mutation reconcile changed production status mode")
        residue = list(root.glob(".*.tmp"))
        if residue:
            raise AssertionError(f"aggregate rollback left atomic temp residue: {residue!r}")
        expected_failure = [
            str(proof_validator),
            str(load_index_validator),
            str(load_validator),
            str(operability_validator),
        ]
        if calls != expected_failure:
            raise AssertionError(f"failure validator order drift: {calls!r} != {expected_failure!r}")

        load_contract.write_bytes(before_load)
        status.write_bytes(before_status)
        calls.clear()
        original_replace = module.os.replace
        rollback_replace_calls = 0

        def rollback_failure_run(command, *, cwd, check):
            nonlocal rollback_replace_calls
            if cwd != root or check is not True:
                raise AssertionError("validator invocation lost fail-closed execution options")
            validator = str(command[1])
            calls.append(validator)
            if validator == str(operability_validator):
                def fail_first_rollback_replace(source, target):
                    nonlocal rollback_replace_calls
                    rollback_replace_calls += 1
                    if rollback_replace_calls == 1:
                        raise OSError("synthetic mutation rollback replacement failure")
                    return original_replace(source, target)

                module.os.replace = fail_first_rollback_replace
                raise subprocess.CalledProcessError(17, command)
            return subprocess.CompletedProcess(command, 0)

        module.subprocess.run = rollback_failure_run
        caught: BaseException | None = None
        try:
            try:
                module.main()
            except BaseException as exc:
                caught = exc
        finally:
            module.os.replace = original_replace
        if caught is None:
            raise AssertionError("mutation reconcile accepted rollback writer failure")
        text = str(caught)
        if not isinstance(caught, module.Fail):
            raise AssertionError("mutation rollback did not raise canonical domain failure")
        if "mutation evidence post-write validation failed: CalledProcessError" not in text:
            raise AssertionError("mutation rollback lost primary validator exception class")
        if "rollback incomplete" not in text or "load authority: OSError" not in text:
            raise AssertionError("mutation rollback lost incomplete status/class")
        if "synthetic" in text or "returned non-zero exit status" in text or not caught.__suppress_context__:
            raise AssertionError("mutation rollback leaked untrusted exception text")
        if rollback_replace_calls != 2:
            raise AssertionError(
                f"mutation rollback stopped before restoring every authority: replace calls={rollback_replace_calls}"
            )
        if status.read_bytes() != before_status:
            raise AssertionError("mutation rollback failure prevented later production-status restore")
        if stat.S_IMODE(status.stat().st_mode) != status_mode:
            raise AssertionError("mutation rollback failure changed later production-status mode")
        module.atomic_write_bytes(load_contract, before_load)
        module.atomic_write_bytes(status, before_status)
        if list(root.glob(".*.tmp")):
            raise AssertionError("mutation rollback failure left atomic temp residue")

    print("PASS: deletion mutation authority preserves independent upload completion, atomic mode, secret-free diagnostics, and exhaustive rollback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
