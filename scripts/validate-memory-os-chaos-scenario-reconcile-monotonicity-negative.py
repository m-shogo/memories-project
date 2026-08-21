#!/usr/bin/env python3
"""Prevent scenario-specific chaos reconcilers from restoring superseded coarse gaps."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL = ROOT / "scripts/reconcile-memory-os-chaos-authority.py"
INFLIGHT_OVERLAY = ROOT / "scripts/reconcile-memory-os-chaos-inflight-overlay.py"
V1_RECONCILER = ROOT / "scripts/reconcile-memory-os-chaos-failure-drills.py"
INFLIGHT_RECONCILER = ROOT / "scripts/reconcile-memory-os-parser-inflight-cancellation.py"
SCENARIOS = (
    V1_RECONCILER,
    ROOT / "scripts/reconcile-memory-os-chaos-failure-drills-v2.py",
    ROOT / "scripts/reconcile-memory-os-parser-restart-matrix.py",
    INFLIGHT_RECONCILER,
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_result_fixture(module, root: Path) -> tuple[Path | None, Path | None]:
    result_path = getattr(module, "RESULT_PATH", None)
    if not isinstance(result_path, Path):
        return None, None
    if not result_path.is_file():
        return result_path, None
    temp_result = root / "result.json"
    temp_result.write_bytes(result_path.read_bytes())
    module.RESULT_PATH = temp_result
    return result_path, temp_result


def restore_result_fixture(module, original: Path | None) -> None:
    if original is not None:
        module.RESULT_PATH = original


def validate_canonical_source_delegation(canonical, current: dict) -> None:
    original_runner = canonical.run_canonical_validator
    calls: list[str] = []
    try:
        canonical.run_canonical_validator = lambda script_name: calls.append(script_name)
        canonical.validate_canonical_source_authorities()
    finally:
        canonical.run_canonical_validator = original_runner

    database_result = json.loads(canonical.DATABASE_RESULT.read_text(encoding="utf-8"))
    assertions = database_result.get("assertions", {})
    expected = [canonical.OBJECT_VALIDATOR, canonical.PARSER_VALIDATOR]
    if isinstance(assertions, dict) and assertions.get("sameSpoolIdReused") is True:
        expected.append(canonical.DATABASE_VALIDATOR)
    if calls != expected:
        raise RuntimeError(f"canonical chaos source-validator delegation drift: {calls} != {expected}")

    original_runner = canonical.run_canonical_validator
    try:
        def reject_source(_script_name: str) -> None:
            raise canonical.ReconcileFailure("synthetic canonical source rejection")

        canonical.run_canonical_validator = reject_source
        try:
            canonical.normalized_status(copy.deepcopy(current))
        except canonical.ReconcileFailure as exc:
            if "synthetic canonical source rejection" not in str(exc):
                raise RuntimeError(f"unexpected canonical source rejection: {exc}") from exc
        else:
            raise RuntimeError("canonical chaos reconcile accepted rejected source authority")
    finally:
        canonical.run_canonical_validator = original_runner


def validate_inflight_source_delegation(current: dict) -> None:
    overlay = load_module(INFLIGHT_OVERLAY, "memory_os_chaos_inflight_delegation")
    if not overlay.RESULT_PATH.is_file():
        return
    result = overlay.load(overlay.RESULT_PATH)
    original_loader = overlay.load_result_validator
    calls: list[Path] = []
    try:
        def accept_loader(path: Path, _module_name: str):
            calls.append(path)
            return lambda _result, _expected_sha: None

        overlay.load_result_validator = accept_loader
        overlay.validate_inflight_result(result)
    finally:
        overlay.load_result_validator = original_loader
    if calls != [overlay.INFLIGHT_VALIDATOR]:
        raise RuntimeError(f"in-flight overlay validator delegation drift: {calls}")

    try:
        def reject_loader(_path: Path, _module_name: str):
            def reject(_result, _expected_sha) -> None:
                raise overlay.ReconcileFailure("synthetic in-flight source rejection")
            return reject

        overlay.load_result_validator = reject_loader
        try:
            overlay.validate_inflight_result(result)
        except overlay.ReconcileFailure as exc:
            if "synthetic in-flight source rejection" not in str(exc):
                raise RuntimeError(f"unexpected in-flight source rejection: {exc}") from exc
        else:
            raise RuntimeError("in-flight overlay accepted rejected canonical source authority")
    finally:
        overlay.load_result_validator = original_loader

    original_full_runner = overlay.run_full_validator
    full_calls: list[Path] = []
    try:
        def reject_full(path: Path) -> None:
            full_calls.append(path)
            raise overlay.ReconcileFailure("synthetic full in-flight source rejection")

        overlay.run_full_validator = reject_full
        try:
            overlay.normalize(copy.deepcopy(current))
        except overlay.ReconcileFailure as exc:
            if "synthetic full in-flight source rejection" not in str(exc):
                raise RuntimeError(f"unexpected full in-flight source rejection: {exc}") from exc
        else:
            raise RuntimeError("in-flight overlay accepted rejected full canonical source authority")
    finally:
        overlay.run_full_validator = original_full_runner
    if full_calls != [overlay.INFLIGHT_VALIDATOR]:
        raise RuntimeError(f"full in-flight source validation did not precede mutation: {full_calls}")


def validate_inflight_overlay_transaction(current: dict) -> None:
    overlay = load_module(INFLIGHT_OVERLAY, "memory_os_chaos_inflight_transaction")
    original_status = overlay.STATUS_PATH
    try:
        overlay.STATUS_PATH = ROOT / "README.md"
        try:
            overlay.enforce_status_authority()
        except overlay.ReconcileFailure as exc:
            if "fixture must remain outside repository" not in str(exc):
                raise RuntimeError(f"unexpected in-flight overlay status rejection: {exc}") from exc
        else:
            raise RuntimeError("in-flight overlay accepted repository-contained status substitution")
    finally:
        overlay.STATUS_PATH = original_status

    with tempfile.TemporaryDirectory(prefix="memory-os-inflight-overlay-transaction-") as tmp:
        root = Path(tmp)
        temp_status = root / "status.json"
        candidate = copy.deepcopy(current)
        gate = next(
            item for item in candidate["areas"]
            if isinstance(item, dict) and item.get("id") == "OPS-P0-009"
        )
        existing = gate.get("existingEvidence")
        if not isinstance(existing, list):
            raise RuntimeError("OPS-P0-009 existingEvidence missing for overlay transaction proof")
        marker = "synthetic in-flight overlay transaction marker"
        while marker in existing:
            existing.remove(marker)
        original_bytes = json.dumps(candidate, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
        temp_status.write_bytes(original_bytes)

        original_status = overlay.STATUS_PATH
        original_normalize = overlay.normalize
        original_post = overlay.run_post_write_validators
        try:
            overlay.STATUS_PATH = temp_status

            def force_change(value: dict) -> dict:
                updated = copy.deepcopy(value)
                updated_gate = next(
                    item for item in updated["areas"]
                    if isinstance(item, dict) and item.get("id") == "OPS-P0-009"
                )
                updated_gate["existingEvidence"].append(marker)
                return updated

            overlay.normalize = force_change

            def reject_post() -> None:
                raise overlay.ReconcileFailure("synthetic overlay post-write rejection")

            overlay.run_post_write_validators = reject_post
            try:
                overlay.main()
            except overlay.ReconcileFailure as exc:
                if "synthetic overlay post-write rejection" not in str(exc):
                    raise RuntimeError(f"unexpected overlay transaction rejection: {exc}") from exc
            else:
                raise RuntimeError("in-flight overlay accepted post-write aggregate rejection")
        finally:
            overlay.STATUS_PATH = original_status
            overlay.normalize = original_normalize
            overlay.run_post_write_validators = original_post

        if temp_status.read_bytes() != original_bytes:
            raise RuntimeError("in-flight overlay did not roll back Production Status")


def validate_direct_v1_transaction(current: dict) -> None:
    module = load_module(V1_RECONCILER, "memory_os_direct_v1_transaction")
    result = module.load(module.RESULT_PATH)
    source_sha = result.get("commitSha")
    if not isinstance(source_sha, str):
        raise RuntimeError("v1 result source SHA missing")

    candidate = copy.deepcopy(current)
    gate = next(
        item for item in candidate["areas"]
        if isinstance(item, dict) and item.get("id") == "OPS-P0-009"
    )
    missing = gate.get("missingEvidence")
    existing = gate.get("existingEvidence")
    if not isinstance(missing, list) or not isinstance(existing, list):
        raise RuntimeError("OPS-P0-009 arrays missing for v1 transaction proof")
    marker = module.REMOVE_MISSING[0]
    if marker not in missing:
        missing.append(marker)
    for item in module.NEW_EXISTING:
        while item in existing:
            existing.remove(item)

    with tempfile.TemporaryDirectory(prefix="memory-os-v1-chaos-transaction-") as tmp:
        root = Path(tmp)
        temp_status = root / "status.json"
        original_bytes = json.dumps(candidate, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
        temp_status.write_bytes(original_bytes)

        original_status = module.STATUS_PATH
        original_result, _ = copy_result_fixture(module, root)
        original_ancestor = module.source_is_ancestor
        original_normalizer = module.load_canonical_normalizer
        original_chain = module.validate_authority_chain
        calls: list[str] = []
        try:
            module.STATUS_PATH = temp_status
            module.source_is_ancestor = lambda _sha: True
            module.load_canonical_normalizer = lambda: (lambda value: value)

            def reject_post(validated_sha: str) -> None:
                calls.append(validated_sha)
                if len(calls) == 2:
                    raise module.ReconcileFailure("synthetic v1 post-write rejection")

            module.validate_authority_chain = reject_post
            try:
                module.main()
            except module.ReconcileFailure as exc:
                if "synthetic v1 post-write rejection" not in str(exc):
                    raise RuntimeError(f"unexpected direct v1 rejection: {exc}") from exc
            else:
                raise RuntimeError("direct v1 reconcile accepted post-write authority rejection")
        finally:
            module.STATUS_PATH = original_status
            restore_result_fixture(module, original_result)
            module.source_is_ancestor = original_ancestor
            module.load_canonical_normalizer = original_normalizer
            module.validate_authority_chain = original_chain

        if calls != [source_sha, source_sha]:
            raise RuntimeError(f"direct v1 authority validation order drift: {calls}")
        if temp_status.read_bytes() != original_bytes:
            raise RuntimeError("direct v1 reconcile did not roll back Production Status")


def validate_direct_inflight_transaction(current: dict) -> None:
    module = load_module(INFLIGHT_RECONCILER, "memory_os_direct_inflight_transaction")
    canonical_result = module.RESULT_PATH
    canonical_status = module.STATUS_PATH
    try:
        module.RESULT_PATH = ROOT / "README.md"
        module.STATUS_PATH = ROOT / "SECURITY.md"
        try:
            module.main()
        except module.ReconcileFailure as exc:
            if "fixture must remain outside repository" not in str(exc):
                raise RuntimeError(f"unexpected direct in-flight data rejection: {exc}") from exc
        else:
            raise RuntimeError("direct in-flight reconcile accepted repository-contained data substitution")
    finally:
        module.RESULT_PATH = canonical_result
        module.STATUS_PATH = canonical_status

    result = module.load(module.RESULT_PATH)
    source_sha = result.get("commitSha")
    if not isinstance(source_sha, str):
        raise RuntimeError("in-flight result source SHA missing")

    candidate = copy.deepcopy(current)
    gate = next(
        item for item in candidate["areas"]
        if isinstance(item, dict) and item.get("id") == "OPS-P0-009"
    )
    missing = gate.get("missingEvidence")
    existing = gate.get("existingEvidence")
    if not isinstance(missing, list) or not isinstance(existing, list):
        raise RuntimeError("OPS-P0-009 arrays missing for in-flight transaction proof")
    if module.OLD_MISSING not in missing:
        missing.append(module.OLD_MISSING)
    for item in module.NEW_EXISTING:
        while item in existing:
            existing.remove(item)

    with tempfile.TemporaryDirectory(prefix="memory-os-inflight-transaction-") as tmp:
        root = Path(tmp)
        temp_status = root / "status.json"
        original_bytes = json.dumps(candidate, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
        temp_status.write_bytes(original_bytes)

        original_status = module.STATUS_PATH
        original_result, _ = copy_result_fixture(module, root)
        original_ancestor = module.source_is_ancestor
        original_normalizer = module.load_normalizer
        original_chain = module.validate_authority_chain
        calls: list[str] = []
        try:
            module.STATUS_PATH = temp_status
            module.source_is_ancestor = lambda _sha: True
            module.load_normalizer = lambda _path, _name, _attribute: (lambda value: value)

            def reject_post(validated_sha: str) -> None:
                calls.append(validated_sha)
                if len(calls) == 2:
                    raise module.ReconcileFailure("synthetic in-flight post-write rejection")

            module.validate_authority_chain = reject_post
            try:
                module.main()
            except module.ReconcileFailure as exc:
                if "synthetic in-flight post-write rejection" not in str(exc):
                    raise RuntimeError(f"unexpected direct in-flight rejection: {exc}") from exc
            else:
                raise RuntimeError("direct in-flight reconcile accepted post-write authority rejection")
        finally:
            module.STATUS_PATH = original_status
            restore_result_fixture(module, original_result)
            module.source_is_ancestor = original_ancestor
            module.load_normalizer = original_normalizer
            module.validate_authority_chain = original_chain

        if calls != [source_sha, source_sha]:
            raise RuntimeError(f"direct in-flight authority validation order drift: {calls}")
        if temp_status.read_bytes() != original_bytes:
            raise RuntimeError("direct in-flight reconcile did not roll back Production Status")


def main() -> int:
    canonical = load_module(CANONICAL, "memory_os_chaos_monotonicity_canonical")
    current = json.loads(STATUS.read_text(encoding="utf-8"))
    validate_canonical_source_delegation(canonical, current)
    validate_inflight_source_delegation(current)
    validate_inflight_overlay_transaction(current)
    validate_direct_v1_transaction(current)
    validate_direct_inflight_transaction(current)

    gate = next(
        item for item in current["areas"]
        if isinstance(item, dict) and item.get("id") == "OPS-P0-009"
    )
    missing = gate.get("missingEvidence")
    if not isinstance(missing, list):
        raise RuntimeError("OPS-P0-009 missingEvidence is not a list")
    for coarse in canonical.COARSE_GAPS:
        if coarse not in missing:
            missing.append(coarse)

    for index, path in enumerate(SCENARIOS):
        module = load_module(path, f"memory_os_chaos_scenario_{index}")
        with tempfile.TemporaryDirectory(prefix="memory-os-chaos-monotonicity-") as tmp:
            root = Path(tmp)
            temp_status = root / "status.json"
            temp_status.write_text(
                json.dumps(copy.deepcopy(current), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            original_status = module.STATUS_PATH
            original_result, _ = copy_result_fixture(module, root)
            module.STATUS_PATH = temp_status
            try:
                result = module.main()
            finally:
                module.STATUS_PATH = original_status
                restore_result_fixture(module, original_result)
            if result != 0:
                raise RuntimeError(f"scenario reconcile returned nonzero: {path.name}")
            reconciled = json.loads(temp_status.read_text(encoding="utf-8"))
            reconciled_gate = next(
                item for item in reconciled["areas"]
                if isinstance(item, dict) and item.get("id") == "OPS-P0-009"
            )
            reconciled_missing = reconciled_gate.get("missingEvidence")
            if not isinstance(reconciled_missing, list):
                raise RuntimeError(f"scenario reconcile lost missingEvidence list: {path.name}")
            restored = [item for item in canonical.COARSE_GAPS if item in reconciled_missing]
            if restored:
                raise RuntimeError(f"scenario reconcile restored coarse gaps in {path.name}: {restored}")
            if reconciled.get("productionDecision") != "NO_GO":
                raise RuntimeError(f"scenario reconcile changed production decision: {path.name}")

    print("PASS: chaos reconcile pins data/source authority, rolls back overlay/direct projections and preserves stronger missing-evidence authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
