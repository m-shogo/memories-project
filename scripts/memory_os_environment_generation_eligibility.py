#!/usr/bin/env python3
"""Shared fail-closed derivation of restore-preflight-eligible environment generations."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
GEN_REGISTRY = CANONICAL_GEN_REGISTRY
GEN_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def canonical_repo_file(path: Path, field: str) -> Path:
    try:
        relative = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(relative.parts and ".." not in relative.parts, f"{field} must be repository-contained")
    require(relative == resolved and path.is_file(), f"{field} must resolve to its canonical repository file")
    return path


def require_canonical_registry(path: Path) -> None:
    require(path == CANONICAL_GEN_REGISTRY, "environment generation registry authority drift")
    canonical_repo_file(path, "canonical environment generation registry")


def load_generation_writer():
    writer = canonical_repo_file(GEN_WRITER, "generation writer")
    expected = (ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py").resolve(strict=True)
    require(writer.resolve(strict=True) == expected, "generation writer executable authority drift")
    spec = importlib.util.spec_from_file_location("memory_os_generation_writer_for_eligibility", writer)
    require(spec is not None and spec.loader is not None, "cannot load generation writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def independent_review_ref_for_row(writer: Any, row: dict[str, Any]) -> str:
    try:
        env_path = writer.repo_ref(row.get("environmentRecordRef"), "environmentRecordRef")
        env = writer.load(env_path)
    except writer.Fail as exc:
        raise Fail(f"cannot resolve eligible generation environment review authority: {exc}") from exc
    boundary = env.get("evidenceBoundary")
    require(isinstance(boundary, dict), "eligible generation evidenceBoundary missing")
    require(boundary.get("independentReviewCompleted") is True, "eligible generation independent review not completed")
    review_ref = boundary.get("independentReviewRef")
    require(isinstance(review_ref, str) and review_ref, "eligible generation independent review ref missing")
    return review_ref


def derive_registry(registry: dict[str, Any]) -> dict[str, Any]:
    """Derive semantic preflight authority from an already loaded registry object."""
    require(isinstance(registry, dict), "generation registry root must be object")

    writer = load_generation_writer()
    try:
        rows = writer.validate_registry_for_append(registry)
    except writer.Fail as exc:
        raise Fail(f"generation registry authority validation failed: {exc}") from exc

    count = registry.get("registeredGenerationCount")
    superseded_ids = {
        row.get("supersedesGenerationId")
        for row in rows
        if isinstance(row.get("supersedesGenerationId"), str)
    }
    unsuperseded_rows = [row for row in rows if row.get("generationId") not in superseded_ids]

    eligible_by_id: dict[str, bool] = {}
    for row in rows:
        generation_id = row["generationId"]
        try:
            value = writer.validate_record(row)
        except writer.Fail as exc:
            raise Fail(f"generation semantic validation failed for {generation_id}: {exc}") from exc
        require(isinstance(value, bool), "generation eligibility predicate invalid")
        eligible_by_id[generation_id] = value

    eligible_rows = [row for row in rows if eligible_by_id.get(row["generationId"]) is True]
    eligible_review_refs = [independent_review_ref_for_row(writer, row) for row in eligible_rows]
    require(
        len(eligible_review_refs) == len(set(eligible_review_refs)),
        "eligible generations reuse environment independent review evidence",
    )

    unsuperseded_eligible_rows = [row for row in unsuperseded_rows if eligible_by_id.get(row["generationId"]) is True]
    distinct_unsuperseded_environments = {
        row.get("environmentId")
        for row in unsuperseded_rows
        if isinstance(row.get("environmentId"), str) and row.get("environmentId")
    }
    distinct_eligible_environments = {
        row.get("environmentId")
        for row in unsuperseded_eligible_rows
        if isinstance(row.get("environmentId"), str) and row.get("environmentId")
    }
    eligible_directed_pairs = [
        (source, target)
        for source in unsuperseded_eligible_rows
        for target in unsuperseded_eligible_rows
        if source.get("generationId") != target.get("generationId")
        and source.get("environmentId") != target.get("environmentId")
    ]
    return {
        "registeredRows": rows,
        "registeredGenerationCount": count,
        "unsupersededRows": unsuperseded_rows,
        "unsupersededGenerationCount": len(unsuperseded_rows),
        "distinctUnsupersededEnvironmentCount": len(distinct_unsuperseded_environments),
        "preflightEligibleRows": eligible_rows,
        "preflightEligibleGenerationCount": len(eligible_rows),
        "unsupersededPreflightEligibleRows": unsuperseded_eligible_rows,
        "unsupersededPreflightEligibleGenerationCount": len(unsuperseded_eligible_rows),
        "distinctPreflightEligibleEnvironmentCount": len(distinct_eligible_environments),
        "eligibleDirectedPairs": eligible_directed_pairs,
        "eligibleDirectedPairCount": len(eligible_directed_pairs),
    }


def derive(registry_path: Path = GEN_REGISTRY) -> dict[str, Any]:
    require_canonical_registry(registry_path)
    return derive_registry(load(registry_path))


def eligible_generation_by_id(generation_id: Any, *, registry_path: Path = GEN_REGISTRY) -> dict[str, Any]:
    require(isinstance(generation_id, str) and generation_id, "generationId required")
    state = derive(registry_path)
    matches = [row for row in state["unsupersededPreflightEligibleRows"] if row.get("generationId") == generation_id]
    require(len(matches) == 1, "generation is not uniquely unsuperseded and restore-preflight-eligible")
    return matches[0]


def main() -> int:
    state = derive()
    print("Memory OS environment generation eligibility derivation PASS")
    print(f"registered generations: {state['registeredGenerationCount']}")
    print(f"unsuperseded generations: {state['unsupersededGenerationCount']}")
    print(f"preflight-eligible generations: {state['preflightEligibleGenerationCount']}")
    print(f"unsuperseded preflight-eligible generations: {state['unsupersededPreflightEligibleGenerationCount']}")
    print(f"distinct preflight-eligible environments: {state['distinctPreflightEligibleEnvironmentCount']}")
    print(f"eligible directed restore pairs: {state['eligibleDirectedPairCount']}")
    print("canonical generation registry identity required for path-based derivation: true")
    print("fixture derivation remains available through derive_registry: true")
    print("generation writer executable authority pinned: true")
    print("generation registry validation delegated to canonical writer: true")
    print("eligible environment independent review reuse accepted: false")
    print("generation registry schema drift accepted: false")
    print("generation registry class drift accepted: false")
    print("cross-environment supersedes accepted: false")
    print("out-of-order same-environment supersedes accepted: false")
    print("current generation pointer drift accepted: false")
    print("boolean registered-generation counts accepted: false")
    print("malformed or unreadable generation registry accepted: false")
    print("unexpected generation-validator exceptions normalized as semantic rejection: false")
    print("production evidence: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT GENERATION ELIGIBILITY FAILED: {exc}")
        raise SystemExit(1)
