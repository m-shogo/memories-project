#!/usr/bin/env python3
"""Prove support-window admission rejects corrupt upstream and skew authorities."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-client-server-support-window.py"
CLIENT_RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-client-baseline-registry.py"
CONTRACT = ROOT / "contracts/operations/client-server-support-window-contract.v1.json"
RELEASES = ROOT / "contracts/operations/release-baseline-registry.v1.json"
CLIENTS = ROOT / "contracts/operations/client-baseline-registry.v1.json"
SKEW = ROOT / "contracts/operations/client-server-skew-registry.v1.json"


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


def main() -> int:
    validator = load_validator()
    release_base = load(RELEASES)
    client_base = load(CLIENTS)
    skew_base = load(SKEW)
    validator.main()
    verify_inventory_only_intermediate_state(validator)
    verify_client_reconcile_preserves_admitted_skew()

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
