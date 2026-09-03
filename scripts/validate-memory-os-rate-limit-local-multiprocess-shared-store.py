#!/usr/bin/env python3
"""Validate local multi-process rate-limit shared-store rehearsal evidence."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/rate-limit-local-multiprocess-shared-store-contract.v1.json"
RESULT = ROOT / "docs/fixtures/memory-os-operability/rate-limit-local-multiprocess-shared-store-results.v1.json"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_REFS = {
    "runner": "services/import-api/internal/ratelimit/shared_store_multiprocess_test.go",
    "validator": "scripts/validate-memory-os-rate-limit-local-multiprocess-shared-store.py",
    "reconcile": "scripts/reconcile-memory-os-rate-limit-local-multiprocess-shared-store.py",
    "workflow": ".github/workflows/rate-limit-local-multiprocess-shared-store.yml",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def require_canonical_ref(contract: dict[str, Any], field: str) -> Path:
    expected_ref = EXPECTED_REFS[field]
    ref = contract.get(field)
    require(ref == expected_ref, f"canonical contract artifact identity drift: {field}")
    path = ROOT / expected_ref
    require(path.is_file(), f"canonical contract artifact missing: {field}")
    require(not path.is_symlink(), f"canonical contract artifact must not be symlink: {field}")
    try:
        require(path.resolve(strict=True) == path, f"canonical contract artifact path drift: {field}")
    except OSError as exc:
        raise Fail(f"cannot resolve canonical contract artifact: {field}") from exc
    return path


def source_is_ancestor(source: str, _run=subprocess.run) -> bool:
    if subprocess.run is not _run:
        raise Fail("git ancestry execution transport drift")
    return _run(
        ["git", "merge-base", "--is-ancestor", source, "HEAD"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def require_runtime_authorities(
    _root: Path = ROOT,
    _contract: Path = CONTRACT,
    _result: Path = RESULT,
    _expected_refs: tuple[tuple[str, str], ...] = tuple(EXPECTED_REFS.items()),
    _helpers: tuple[tuple[str, object], ...] = (
        ("require", require),
        ("load", load),
        ("require_canonical_ref", require_canonical_ref),
        ("source_is_ancestor", source_is_ancestor),
    ),
) -> None:
    if ROOT != _root or ROOT.resolve() != _root.resolve():
        raise Fail("local shared-store validator repository root authority drift")
    for current, canonical, label, optional in (
        (CONTRACT, _contract, "CONTRACT", False),
        (RESULT, _result, "RESULT", True),
    ):
        if current != canonical:
            raise Fail(f"local shared-store validator {label} authority drift")
        if optional and not canonical.exists():
            continue
        if not canonical.is_file() or canonical.is_symlink() or canonical.resolve() != current.resolve():
            raise Fail(f"local shared-store validator {label} canonical file authority invalid")
    if tuple(EXPECTED_REFS.items()) != _expected_refs:
        raise Fail("local shared-store validator EXPECTED_REFS semantic authority drift")
    for name, canonical in _helpers:
        if globals().get(name) is not canonical:
            raise Fail(f"local shared-store validator {name} execution authority drift")


def _build_main(
    _canonical_guard=require_runtime_authorities,
    _canonical_require=require,
    _canonical_load=load,
    _canonical_ref=require_canonical_ref,
    _canonical_source_is_ancestor=source_is_ancestor,
    _canonical_guard_defaults=require_runtime_authorities.__defaults__,
    _canonical_source_defaults=source_is_ancestor.__defaults__,
):
    def _main() -> int:
        if require_runtime_authorities is not _canonical_guard:
            raise Fail("local shared-store validator runtime guard execution authority drift")
        if require is not _canonical_require:
            raise Fail("local shared-store validator require execution authority drift")
        if load is not _canonical_load:
            raise Fail("local shared-store validator load execution authority drift")
        if require_canonical_ref is not _canonical_ref:
            raise Fail("local shared-store validator canonical-ref execution authority drift")
        if source_is_ancestor is not _canonical_source_is_ancestor:
            raise Fail("local shared-store validator ancestry helper execution authority drift")
        if _canonical_guard.__defaults__ != _canonical_guard_defaults:
            raise Fail("local shared-store validator runtime guard default authority drift")
        if _canonical_source_is_ancestor.__defaults__ != _canonical_source_defaults:
            raise Fail("local shared-store validator ancestry helper default authority drift")

        _canonical_guard()
        contract = _canonical_load(CONTRACT)
        _canonical_require(contract.get("contractId") == "memory-os.operability.rate-limit-local-multiprocess-shared-store.v1", "contract id drift")
        _canonical_require(contract.get("schemaVersion") == "memory-os-rate-limit-local-multiprocess-shared-store.v1", "contract schema drift")
        resolved_refs = {field: _canonical_ref(contract, field) for field in EXPECTED_REFS}
        _canonical_require(contract.get("result") == str(RESULT.relative_to(ROOT)), "result path drift")
        _canonical_require(contract.get("test") == "TestLocalSharedStoreCrossProcessBudgetRestartAndOutage", "test binding drift")
        assertions = contract.get("requiredAssertions")
        _canonical_require(isinstance(assertions, dict), "requiredAssertions missing")
        for key in (
            "independentOsClientProcesses", "sharedBudgetAtomicAcrossProcesses",
            "freshClientProcessDoesNotResetBudget", "storeOutageFailsClosed",
        ):
            _canonical_require(assertions.get(key) is True, f"required local assertion missing: {key}")
        for key in (
            "productionStoreImplementationExercised", "productionEquivalentRuntimeExercised",
            "productionTlsExercised", "deploymentTrustedProxyConfigurationExercised",
            "productionCredentialsUsed", "productionTrafficUsed",
        ):
            _canonical_require(assertions.get(key) is False, f"local rehearsal cannot enable: {key}")
        promotion = contract.get("promotionRules")
        _canonical_require(isinstance(promotion, dict) and promotion and all(value is False for value in promotion.values()), "local rehearsal promotion must remain forbidden")

        runner = resolved_refs["runner"].read_text(encoding="utf-8")
        for token in (
            "exec.Command(os.Args[0]",
            "MEMORY_OS_RATE_LIMIT_CHILD=1",
            "cross-process shared budget allowed",
            "client restart reset shared state",
            "shared-store outage did not fail closed",
            "ReasonStoreUnavailable",
            "httptest.NewServer",
        ):
            _canonical_require(token in runner, f"runner safety binding missing: {token}")

        readiness = contract.get("readiness")
        _canonical_require(isinstance(readiness, dict), "readiness missing")
        for field in ("contractDefined", "runnerImplemented", "validatorImplemented", "automaticWorkflowImplemented"):
            _canonical_require(readiness.get(field) is True, f"foundation readiness missing: {field}")
        for field in ("distributedSharedStoreImplemented", "productionEquivalentRuntimeEvidence", "productionReady"):
            _canonical_require(readiness.get(field) is False, f"local rehearsal cannot promote readiness.{field}")

        if not RESULT.exists():
            _canonical_require(readiness.get("exactSourcePassCommitted") is False, "missing result cannot be committed PASS")
            _canonical_require(readiness.get("localCrossProcessStoreSemanticsProven") is False, "missing result cannot prove local semantics")
            print("Memory OS local multi-process shared-store validation PASS (foundation only)")
            print("exact-source result: absent")
            print("production-equivalent evidence: false")
            return 0

        result = _canonical_load(RESULT)
        _canonical_require(result.get("schemaVersion") == contract.get("resultsSchemaVersion"), "result schema drift")
        source = result.get("sourceCommitSha")
        _canonical_require(isinstance(source, str) and SHA40.fullmatch(source), "sourceCommitSha invalid")
        _canonical_require(_canonical_source_is_ancestor(source), "sourceCommitSha must be an ancestor of current HEAD")
        _canonical_require(result.get("classification") == "LOCAL_MULTI_PROCESS_SHARED_STORE_REHEARSAL", "result classification drift")
        _canonical_require(result.get("dependencyMode") == "TEST_ONLY_LOOPBACK_HTTP_BROKER_MEMORY_STORE", "result dependency mode drift")
        _canonical_require(result.get("result") == "PASS", "result must be PASS")
        result_assertions = result.get("assertions")
        _canonical_require(isinstance(result_assertions, dict), "result assertions missing")
        for key, expected in assertions.items():
            _canonical_require(result_assertions.get(key) is expected, f"result assertion drift: {key}")
        _canonical_require(result.get("productionEvidence") is False, "local result cannot be production evidence")
        _canonical_require(result.get("productionEquivalentRuntimeEvidence") is False, "local result cannot be production-equivalent evidence")
        _canonical_require(result.get("productionReady") is False, "local result cannot make production ready")
        _canonical_require(readiness.get("exactSourcePassCommitted") is True, "result exists but readiness.exactSourcePassCommitted is false")
        _canonical_require(readiness.get("localCrossProcessStoreSemanticsProven") is True, "result exists but local semantics readiness is false")

        print("Memory OS local multi-process shared-store validation PASS")
        print(f"source commit: {source}")
        print("cross-process local store semantics: proven")
        print("distributed shared store implemented: false")
        print("production-equivalent evidence: false")
        print("production decision: NO_GO")
        return 0

    return _main


main = _build_main()
del _build_main


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RATE LIMIT LOCAL MULTIPROCESS SHARED STORE VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
