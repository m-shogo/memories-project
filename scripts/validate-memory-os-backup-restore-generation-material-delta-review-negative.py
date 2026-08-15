#!/usr/bin/env python3
"""Negative suite for generation material-delta review authority."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-material-delta-review.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_generation_material_delta_review_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load material-delta validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_registry_fail(module, row: dict, label: str) -> None:
    registry = {
        "schemaVersion": "memory-os-backup-restore-generation-evidence-registry.v1",
        "appendOnly": True,
        "records": [row],
        "productionEvidence": False,
        "productionReady": False,
    }
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as handle:
        path = Path(handle.name)
        json.dump(registry, handle)
        handle.write("\n")
    original = module.REGISTRY
    try:
        module.REGISTRY = path
        try:
            module.main()
        except module.Fail:
            return
        raise Fail(f"negative case unexpectedly passed: {label}")
    finally:
        module.REGISTRY = original
        path.unlink(missing_ok=True)


def expect_contract_fail(module, mutate, label: str) -> None:
    canonical = json.loads(module.CONTRACT.read_text(encoding="utf-8"))
    mutated = json.loads(json.dumps(canonical))
    mutate(mutated)
    original_load_json = module.load_json
    try:
        module.load_json = lambda path, field: mutated if path == module.CONTRACT else original_load_json(path, field)
        try:
            module.validate_contract_authority()
        except module.Fail:
            return
        raise Fail(f"contract authority negative unexpectedly passed: {label}")
    finally:
        module.load_json = original_load_json


def main() -> int:
    module = load_validator()

    expect_registry_fail(
        module,
        {
            "sourceEnvironmentGenerationId": "pegen_source_negative",
            "restoreTargetGenerationId": "pegen_target_negative",
            "materialDeltaReviewRef": "SECURITY.md",
        },
        "generic repository file",
    )
    expect_registry_fail(
        module,
        {
            "sourceEnvironmentGenerationId": "pegen_same_negative",
            "restoreTargetGenerationId": "pegen_same_negative",
            "materialDeltaReviewRef": "docs/evidence/backup-restore/material-delta/review.json",
        },
        "same-generation material delta review",
    )
    expect_registry_fail(
        module,
        {
            "sourceEnvironmentGenerationId": "pegen_source_negative",
            "restoreTargetGenerationId": "pegen_target_negative",
            "materialDeltaReviewRef": "docs/evidence/backup-restore/../outside.json",
        },
        "path traversal",
    )

    expect_contract_fail(
        module,
        lambda contract: contract.__setitem__("materialDeltaReviewEvidenceRoot", "docs/evidence/backup-restore"),
        "material-delta evidence root widened",
    )
    expect_contract_fail(
        module,
        lambda contract: contract["recordRules"].__setitem__("crossGenerationMaterialDeltaReviewMustRemainInsideMonitoredNamespace", False),
        "material-delta namespace rule disabled",
    )
    expect_contract_fail(
        module,
        lambda contract: contract["recordRules"].__setitem__("crossGenerationMaterialDeltaReviewMustRemainAppendOnlyAfterFirstCommit", False),
        "material-delta append-only rule disabled",
    )
    expect_contract_fail(
        module,
        lambda contract: contract.__setitem__("materialDeltaReviewValidator", "scripts/validate-memory-os-backup-restore-generation-evidence.py"),
        "material-delta validator substituted",
    )

    original_history = module.git_history
    try:
        module.git_history = lambda _ref, _field: ["a" * 40, "b" * 40]
        try:
            module.require_append_only_review(
                "docs/evidence/backup-restore/material-delta/synthetic.json",
                Path("/tmp/not-read-after-history-rejection"),
                "materialDeltaReviewRef",
            )
        except module.Fail:
            pass
        else:
            raise Fail("post-commit material-delta review edit was accepted")
    finally:
        module.git_history = original_history

    print("PASS: material-delta review negatives reject generic refs, same-generation refs, traversal, contract drift, and post-commit edits")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
