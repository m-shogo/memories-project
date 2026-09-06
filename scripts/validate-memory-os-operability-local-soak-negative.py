#!/usr/bin/env python3
"""Negative checks for semantic local sustained-soak operability admission."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/validate-memory-os-operability.py"
REVIEW_REGISTER_PATH = ROOT / "scripts/register-memory-os-sustained-soak-independent-review.py"
REVIEW_REGISTRY = ROOT / "contracts/operations/sustained-soak-independent-review-registry.v1.json"
SOAK_PATH = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
POSTGRES_PATH = ROOT / "contracts/operations/live-postgres-load-scenario-contract.v1.json"
OBJECT_PATH = ROOT / "contracts/operations/live-object-load-scenario-contract.v1.json"

SPEC = importlib.util.spec_from_file_location("memory_os_operability", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("OPERABILITY LOCAL SOAK NEGATIVE FAILED: cannot load operability validator")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path.name}")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def file_mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def copy_authority(source: Path, repo_root: Path, relative: Path) -> None:
    target = repo_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def pending_soak_contract() -> dict:
    contract = json.loads(SOAK_PATH.read_text(encoding="utf-8"))
    readiness = contract["readiness"]
    readiness["trendReviewCompleted"] = False
    readiness["localSustainedSoakEvidence"] = False
    for claim in (
        "productionSustainedSoakEvidence",
        "leakProofAvailable",
        "productionReady",
    ):
        readiness[claim] = False
    return contract


def validate_pending(repo_root: Path, contract: dict) -> None:
    copy_authority(
        POSTGRES_PATH,
        repo_root,
        module.LIVE_POSTGRES_CONTRACT_PATH,
    )
    copy_authority(
        OBJECT_PATH,
        repo_root,
        module.LIVE_OBJECT_CONTRACT_PATH,
    )
    write_json(repo_root / module.LONG_SOAK_CONTRACT_PATH, contract)

    refs = sorted(
        module.LIVE_LOAD_FOUNDATION_REFS
        | {module.LONG_SOAK_CONTRACT_PATH.as_posix()}
    )
    existing = [
        "live PostgreSQL local checkpoint",
        "live MinIO local checkpoint",
    ]
    # Deliberately omit any wording such as "sustained soak". Pending admission
    # must be derived from the typed readiness authority, not prose matching.
    missing = [
        "capacity boundary remains unproven",
        "production-equivalent dependencies remain unproven",
        "additional local stability evidence remains under review",
    ]
    area = {"status": "PARTIAL"}
    module.validate_load_gate(repo_root, area, existing, missing, refs)


def expect_semantic_reject(label: str, mutate) -> None:
    contract = pending_soak_contract()
    mutate(contract["readiness"])
    with tempfile.TemporaryDirectory(prefix="memory-os-operability-soak-negative-") as tmp:
        try:
            validate_pending(Path(tmp), contract)
        except module.ValidationFailure as exc:
            expected = "incomplete local sustained-soak authority must remain semantically pending"
            if expected not in str(exc):
                raise AssertionError(f"unexpected rejection for {label}: {exc}") from exc
        else:
            raise AssertionError(f"semantic corruption accepted: {label}")
    print(f"PASS reject: {label}")


def review_registry_transport_fails_closed() -> None:
    register = load_module(REVIEW_REGISTER_PATH, "memory_os_soak_review_register_transport_negative")
    original = REVIEW_REGISTRY.read_bytes()
    original_mode = file_mode(REVIEW_REGISTRY)
    test_mode = 0o640
    temp_patterns = (
        ".sustained-soak-independent-review-registry-candidate-*",
        ".sustained-soak-independent-review-rollback-*.tmp",
        ".sustained-soak-postappend-mode-negative-*.tmp",
    )

    def temp_names() -> set[str]:
        names: set[str] = set()
        for pattern in temp_patterns:
            names.update(path.name for path in REVIEW_REGISTRY.parent.glob(pattern))
        return names

    before = temp_names()
    candidate_path: Path | None = None
    invalid_path: Path | None = None
    real_replace = register.os.replace
    try:
        REVIEW_REGISTRY.chmod(test_mode)

        candidate_path = register.validate_candidate(register.load(REVIEW_REGISTRY))
        if file_mode(candidate_path) != test_mode:
            raise AssertionError("validated sustained-soak review candidate did not preserve registry mode")

        calls = 0

        def reject_first_replace(source, destination) -> None:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError("synthetic sustained-soak review registry replace failure")
            real_replace(source, destination)

        register.os.replace = reject_first_replace
        try:
            register.replace_registry_transactionally(candidate_path)
        except OSError as exc:
            if "synthetic sustained-soak review registry replace failure" not in str(exc):
                raise AssertionError(f"unexpected review registry replace rejection: {exc}") from exc
        else:
            raise AssertionError("sustained-soak review registry replace failure was accepted")
        finally:
            register.os.replace = real_replace

        candidate_path.unlink(missing_ok=True)
        candidate_path = None
        if REVIEW_REGISTRY.read_bytes() != original:
            raise AssertionError("review registry replace rejection changed canonical bytes")
        if file_mode(REVIEW_REGISTRY) != test_mode:
            raise AssertionError("review registry replace rejection changed canonical mode")

        invalid = json.loads(original.decode("utf-8"))
        invalid["unexpectedAuthority"] = True
        descriptor, temp_name = tempfile.mkstemp(
            prefix=".sustained-soak-postappend-mode-negative-",
            suffix=".tmp",
            dir=REVIEW_REGISTRY.parent,
        )
        invalid_path = Path(temp_name)
        with os.fdopen(descriptor, "wb") as handle:
            os.fchmod(handle.fileno(), test_mode)
            handle.write((json.dumps(invalid, indent=2) + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        try:
            register.replace_registry_transactionally(invalid_path)
        except register.Fail:
            pass
        else:
            raise AssertionError("post-append invalid sustained-soak review registry was accepted")
        invalid_path.unlink(missing_ok=True)
        invalid_path = None
        if REVIEW_REGISTRY.read_bytes() != original:
            raise AssertionError("post-append review validation rollback did not restore canonical bytes")
        if file_mode(REVIEW_REGISTRY) != test_mode:
            raise AssertionError("post-append review validation rollback did not restore canonical mode")
        if temp_names() != before:
            raise AssertionError("sustained-soak review registry transaction leaked temporary files")
    finally:
        register.os.replace = real_replace
        if candidate_path is not None:
            candidate_path.unlink(missing_ok=True)
        if invalid_path is not None:
            invalid_path.unlink(missing_ok=True)
        if REVIEW_REGISTRY.read_bytes() != original or file_mode(REVIEW_REGISTRY) != original_mode:
            register.atomic_restore(original, original_mode)

    print("PASS sustained-soak review registry bytes/mode rollback and temp cleanup")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="memory-os-operability-soak-pending-") as tmp:
        validate_pending(Path(tmp), pending_soak_contract())
    print("PASS semantic pending state without prose coupling")

    expect_semantic_reject(
        "production sustained-soak evidence manufactured",
        lambda readiness: readiness.__setitem__("productionSustainedSoakEvidence", True),
    )
    expect_semantic_reject(
        "leak proof manufactured",
        lambda readiness: readiness.__setitem__("leakProofAvailable", True),
    )
    expect_semantic_reject(
        "production readiness manufactured",
        lambda readiness: readiness.__setitem__("productionReady", True),
    )
    expect_semantic_reject(
        "production readiness omitted",
        lambda readiness: readiness.pop("productionReady"),
    )
    review_registry_transport_fails_closed()

    print("Memory OS operability local-soak semantic negative suite PASS")
    print("pending state depends on typed readiness authority: true")
    print("pending state depends on missingEvidence prose: false")
    print("sustained-soak independent review registry mode preserved: true")
    print("sustained-soak independent review replace rejection rolls back: true")
    print("sustained-soak independent review post-validation rollback preserves bytes and mode: true")
    print("production sustained-soak promotion accepted: false")
    print("leak-proof promotion accepted: false")
    print("production readiness promotion accepted: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
