#!/usr/bin/env python3
"""Prove support-window admission rejects corrupt upstream and skew authorities."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-client-server-support-window.py"
SUPPORT_RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-client-server-support-window-status.py"
CLIENT_RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-client-baseline-registry.py"
CONTRACT = ROOT / "contracts/operations/client-server-support-window-contract.v1.json"
RELEASES = ROOT / "contracts/operations/release-baseline-registry.v1.json"
RELEASE_PAIRS = ROOT / "contracts/operations/release-compatibility-pair-registry.v1.json"
CLIENTS = ROOT / "contracts/operations/client-baseline-registry.v1.json"
SKEW = ROOT / "contracts/operations/client-server-skew-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_validator() -> Any:
    return load_module(VALIDATOR_PATH, "memory_os_support_window_negative_validator")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def verify_support_reconcile_authority_identity() -> None:
    reconciler = load_module(SUPPORT_RECONCILER_PATH, "memory_os_support_window_reconcile_authority_negative")
    reconciler.enforce_runtime_authorities()
    contract_before = CONTRACT.read_bytes()
    status_before = STATUS.read_bytes()
    substitutions = (
        ("CONTRACT", ROOT / "contracts/operations/client-baseline-registry-contract.v1.json"),
        ("VALIDATOR", ROOT / "scripts/validate-memory-os-operability.py"),
        ("OPERABILITY_VALIDATOR", ROOT / "scripts/validate-memory-os-client-server-support-window.py"),
        ("WORKFLOW", ROOT / ".github/workflows/version-compatibility-foundations.yml"),
        ("RELEASES", ROOT / "contracts/operations/client-baseline-registry.v1.json"),
        ("CLIENTS", ROOT / "contracts/operations/release-baseline-registry.v1.json"),
        ("SKEW", ROOT / "contracts/operations/release-compatibility-pair-registry.v1.json"),
        ("STATUS", ROOT / "contracts/operations/client-server-support-window-contract.v1.json"),
    )
    for field, substitute in substitutions:
        original = getattr(reconciler, field)
        try:
            setattr(reconciler, field, substitute)
            rejected = False
            try:
                reconciler.enforce_runtime_authorities()
            except reconciler.Fail:
                rejected = True
            require(rejected, f"support-window reconciler accepted {field} authority substitution")
            require(CONTRACT.read_bytes() == contract_before,
                    f"rejected {field} substitution mutated canonical support-window contract")
            require(STATUS.read_bytes() == status_before,
                    f"rejected {field} substitution mutated canonical production status")
        finally:
            setattr(reconciler, field, original)
    reconciler.enforce_runtime_authorities()


def verify_support_reconcile_rollback() -> None:
    reconciler = load_module(SUPPORT_RECONCILER_PATH, "memory_os_support_window_reconcile_rollback_negative")
    originals = {
        reconciler.CONTRACT: reconciler.CONTRACT.read_bytes(),
        reconciler.STATUS: reconciler.STATUS.read_bytes(),
    }
    observed_operability_failure = False
    original_run_validator = reconciler.run_validator

    def controlled_validator(path: Path, label: str) -> None:
        nonlocal observed_operability_failure
        if label == "post-write operability validator":
            observed_operability_failure = True
            raise reconciler.Fail("synthetic post-write operability validation failure")

    reconciler.run_validator = controlled_validator
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require(
                "synthetic post-write operability validation failure" in str(exc),
                f"unexpected support-window reconcile rollback failure: {exc}",
            )
        else:
            raise NegativeFailure(
                "support-window reconcile unexpectedly succeeded after synthetic post-write aggregate failure"
            )
        require(observed_operability_failure, "synthetic post-write operability failure was not reached")
        for path, payload in originals.items():
            require(
                path.read_bytes() == payload,
                f"support-window reconcile rollback changed canonical authority: {path.relative_to(ROOT)}",
            )
    finally:
        reconciler.run_validator = original_run_validator
        for path, payload in originals.items():
            if path.read_bytes() != payload:
                path.write_bytes(payload)


def verify_client_reconcile_authority_identity() -> None:
    reconciler = load_module(CLIENT_RECONCILER_PATH, "memory_os_client_reconcile_authority_negative")
    reconciler.enforce_runtime_authorities()
    substitutions = (
        ("WRITER", ROOT / "scripts/register-memory-os-parser-artifact.py"),
        ("PAIR_WRITER", ROOT / "scripts/register-memory-os-client-baseline.py"),
        ("VALIDATOR", ROOT / "scripts/validate-memory-os-operability.py"),
        ("SUPPORT_VALIDATOR", ROOT / "scripts/validate-memory-os-client-baseline-registry.py"),
        ("OPERABILITY_VALIDATOR", ROOT / "scripts/validate-memory-os-client-server-support-window.py"),
        ("WORKFLOW", ROOT / ".github/workflows/client-server-support-window.yml"),
        ("RELEASES", ROOT / "contracts/operations/client-baseline-registry.v1.json"),
        ("RELEASE_PAIRS", ROOT / "contracts/operations/release-baseline-registry.v1.json"),
        ("SKEW", ROOT / "contracts/operations/release-compatibility-pair-registry.v1.json"),
    )
    for field, substitute in substitutions:
        original = getattr(reconciler, field)
        try:
            setattr(reconciler, field, substitute)
            rejected = False
            try:
                reconciler.enforce_runtime_authorities()
            except reconciler.Fail:
                rejected = True
            require(rejected, f"client baseline reconciler accepted {field} authority substitution")
        finally:
            setattr(reconciler, field, original)
    reconciler.enforce_runtime_authorities()


def expect_rejection(validator: Any, path: Path, base: dict[str, Any], label: str,
                     mutate: Callable[[dict[str, Any]], None]) -> None:
    originals = {item: item.read_bytes() for item in (RELEASES, CLIENTS, SKEW)}
    candidate = copy.deepcopy(base)
    mutate(candidate)
    try:
        path.write_text(json.dumps(candidate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        try:
            validator.main()
        except validator.Fail:
            pass
        else:
            raise NegativeFailure(f"support-window validator accepted corrupt authority: {label}")
    finally:
        for item, data in originals.items():
            item.write_bytes(data)
    require(all(item.read_bytes() == data for item, data in originals.items()),
            f"canonical authority was not restored after negative case: {label}")


def verify_inventory_only_intermediate_state(validator: Any) -> None:
    contract = copy.deepcopy(load(CONTRACT))
    boundary = contract.get("currentBoundary")
    readiness = contract.get("readiness")
    require(isinstance(boundary, dict) and isinstance(readiness, dict), "support boundary/readiness missing")
    boundary["approvedBackendReleaseCount"] = 2
    boundary["approvedClientBaselineCount"] = 1
    boundary["admissibleSkewPairCount"] = 0
    boundary["implementedClientSupportWindow"] = False
    boundary["clientServerSkewEvidence"] = False
    boundary["releaseCompatibilityEvidence"] = False
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"
    readiness["approvedBackendReleaseAvailable"] = True
    readiness["approvedClientBaselineAvailable"] = True
    readiness["supportWindowImplemented"] = False
    readiness["skewPairExecuted"] = False
    readiness["independentReviewCompleted"] = False
    readiness["productionReady"] = False

    validator.validate_intermediate_boundary(contract, 2, 1, 0)

    promoted = copy.deepcopy(contract)
    promoted["currentBoundary"]["clientServerSkewEvidence"] = True
    try:
        validator.validate_intermediate_boundary(promoted, 2, 1, 0)
    except validator.Fail:
        pass
    else:
        raise NegativeFailure("inventory-only intermediate state promoted client/server skew evidence")

    try:
        validator.validate_intermediate_boundary(contract, 2, 1, 1)
    except validator.Fail:
        pass
    else:
        raise NegativeFailure("inventory-only intermediate state admitted a skew pair without pair authority")


def verify_client_reconcile_preserves_admitted_skew() -> None:
    reconciler = load_module(CLIENT_RECONCILER_PATH, "memory_os_client_reconcile_skew_negative")
    protected = (reconciler.CONTRACT, reconciler.SUPPORT, reconciler.STATUS)
    originals = {path: path.read_bytes() for path in (*protected, SKEW)}
    skew = load(SKEW)
    skew["admissibleSkewPairCount"] = 1
    skew["pairs"] = [{"syntheticPairAuthority": True}]
    try:
        SKEW.write_text(json.dumps(skew, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require(
                "cannot overwrite admitted client/server skew authority" in str(exc),
                f"unexpected client reconcile rejection: {exc}",
            )
        else:
            raise NegativeFailure("client baseline reconcile overwrote admitted skew authority")
        for path in protected:
            require(
                path.read_bytes() == originals[path],
                f"client baseline reconcile mutated stronger authority: {path.relative_to(ROOT)}",
            )
    finally:
        for path, data in originals.items():
            if path.read_bytes() != data:
                path.write_bytes(data)


def verify_client_reconcile_allows_approved_pair_progression() -> None:
    reconciler = load_module(CLIENT_RECONCILER_PATH, "memory_os_client_reconcile_pair_progression_negative")
    originals = {
        RELEASE_PAIRS: RELEASE_PAIRS.read_bytes(),
        reconciler.STATUS: reconciler.STATUS.read_bytes(),
    }
    pair_registry = load(RELEASE_PAIRS)
    pair_registry["approvedPairCount"] = 1
    pair_registry["rollbackEligiblePairCount"] = 1
    pair_registry["latestPairId"] = "rcp_synthetic_progression"
    pair_registry["pairs"] = [{"syntheticPairAuthority": True}]
    status = load(reconciler.STATUS)
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict), "OPS-P0-008 missing in synthetic pair progression")
    missing = gate.get("missingEvidence")
    require(isinstance(missing, list), "OPS-P0-008 missingEvidence absent in synthetic pair progression")
    gate["missingEvidence"] = [
        item for item in missing
        if not (
            isinstance(item, str)
            and "approved predecessor" in item.lower()
            and "successor" in item.lower()
        )
    ]

    captured: dict[str, Any] = {}
    original_loader = reconciler.load_module

    def controlled_loader(path: Path, name: str) -> Any:
        if path.resolve() == reconciler.PAIR_WRITER.resolve():
            return SimpleNamespace(validate_registry_for_append=lambda value: None)
        return original_loader(path, name)

    def capture_write(contract: dict[str, Any], support: dict[str, Any], candidate_status: dict[str, Any]) -> None:
        captured["contract"] = copy.deepcopy(contract)
        captured["support"] = copy.deepcopy(support)
        captured["status"] = copy.deepcopy(candidate_status)

    reconciler.load_module = controlled_loader
    reconciler.write_and_validate_transactionally = capture_write
    original_enforce = reconciler.enforce_runtime_authorities
    reconciler.enforce_runtime_authorities = lambda: None
    try:
        RELEASE_PAIRS.write_text(json.dumps(pair_registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        reconciler.STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        reconciler.main()
        require(captured, "client reconcile did not reach synthetic approved-pair progression write boundary")
        support = captured["support"].get("currentBoundary")
        require(isinstance(support, dict), "captured support boundary missing")
        require(support.get("clientServerSkewEvidence") is False, "approved pair progression manufactured skew evidence")
        require(support.get("productionReady") is False, "approved pair progression manufactured production readiness")
        captured_gate = next(
            (
                row for row in captured["status"].get("areas", [])
                if isinstance(row, dict) and row.get("id") == "OPS-P0-008"
            ),
            None,
        )
        require(isinstance(captured_gate, dict), "captured OPS-P0-008 missing")
        captured_missing = captured_gate.get("missingEvidence")
        require(isinstance(captured_missing, list), "captured OPS-P0-008 missingEvidence absent")
        captured_joined = "\n".join(str(item).lower() for item in captured_missing)
        require(
            not ("approved predecessor" in captured_joined and "successor" in captured_joined),
            "approved pair progression reintroduced the satisfied release-pair blocker",
        )
        require(captured["status"].get("productionDecision") == "NO_GO", "approved pair progression changed production decision")
    finally:
        reconciler.enforce_runtime_authorities = original_enforce
        for path, data in originals.items():
            if path.read_bytes() != data:
                path.write_bytes(data)


def main() -> int:
    validator = load_validator()
    release_base = load(RELEASES)
    client_base = load(CLIENTS)
    skew_base = load(SKEW)
    validator.main()
    verify_support_reconcile_authority_identity()
    verify_support_reconcile_rollback()
    verify_client_reconcile_authority_identity()
    verify_inventory_only_intermediate_state(validator)
    verify_client_reconcile_preserves_admitted_skew()
    verify_client_reconcile_allows_approved_pair_progression()

    for label, path, base, mutate in (
        ("boolean release count", RELEASES, release_base,
         lambda value: value.__setitem__("approvedReleaseCount", True)),
        ("release append-only disabled", RELEASES, release_base,
         lambda value: value.__setitem__("appendOnly", False)),
        ("boolean client count", CLIENTS, client_base,
         lambda value: value.__setitem__("approvedClientBaselineCount", True)),
        ("client production promotion", CLIENTS, client_base,
         lambda value: value.__setitem__("productionEvidence", True)),
        ("boolean skew count", SKEW, skew_base,
         lambda value: value.__setitem__("admissibleSkewPairCount", True)),
        ("skew class drift", SKEW, skew_base,
         lambda value: value.__setitem__("registryClass", "UNTRUSTED_SKEW_AUTHORITY")),
        ("skew production promotion", SKEW, skew_base,
         lambda value: value.__setitem__("productionEvidence", True)),
        ("unknown skew field", SKEW, skew_base,
         lambda value: value.__setitem__("unexpectedAuthority", True)),
    ):
        expect_rejection(validator, path, base, label, mutate)

    validator.main()
    print("Client/server support-window authority negative PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"CLIENT SERVER SUPPORT WINDOW NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
