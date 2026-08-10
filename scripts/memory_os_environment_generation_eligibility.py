#!/usr/bin/env python3
"""Shared fail-closed derivation of restore-preflight-eligible environment generations."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
GEN_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def load_generation_writer():
    spec = importlib.util.spec_from_file_location("memory_os_generation_writer_for_eligibility", GEN_WRITER)
    require(spec is not None and spec.loader is not None, "cannot load generation writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def derive_registry(registry: dict[str, Any]) -> dict[str, Any]:
    """Derive semantic preflight authority from an already loaded registry object."""
    require(isinstance(registry, dict), "generation registry root must be object")
    rows = registry.get("generations")
    count = registry.get("registeredGenerationCount")
    require(registry.get("appendOnly") is True and registry.get("productionEvidence") is False, "generation registry boundary drift")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "generation registry rows invalid")
    require(isinstance(count, int) and not isinstance(count, bool) and count == len(rows), "generation registry count drift")
    generation_ids = [row.get("generationId") for row in rows]
    require(all(isinstance(value, str) and value for value in generation_ids), "generationId invalid")
    require(len(generation_ids) == len(set(generation_ids)), "generationId duplicate")
    superseded_ids = {row.get("supersedesGenerationId") for row in rows if isinstance(row.get("supersedesGenerationId"), str)}
    unsuperseded_rows = [row for row in rows if row.get("generationId") not in superseded_ids]

    writer = load_generation_writer()
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
    print("boolean registered-generation counts accepted: false")
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
