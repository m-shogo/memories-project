#!/usr/bin/env python3
"""Prove operability inventory validation/generation rejects corrupt append-only authorities."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-operability-admission-inventory-source-authorities.py"
GENERATOR = ROOT / "scripts/generate-memory-os-operability-admission-inventory.py"
AUTHORITIES = {
    "migration production-shaped admission": ROOT / "contracts/operations/migration-production-shaped-admission-registry.v1.json",
    "incident contact routing": ROOT / "contracts/operations/incident-contact-routing-admission-registry.v1.json",
    "observability stack": ROOT / "contracts/operations/observability-stack-deployment-registry.v1.json",
    "rate-limit distributed runtime": ROOT / "contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json",
    "environment generation": ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "recovery objective": ROOT / "contracts/operations/recovery-objectives-registry.v1.json",
    "drill request": ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json",
    "generation recovery evidence": ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "typed non-resurrection": ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
    "human promotion review": ROOT / "contracts/operations/backup-restore-promotion-review-registry.v1.json",
    "release baseline": ROOT / "contracts/operations/release-baseline-registry.v1.json",
    "release compatibility pair": ROOT / "contracts/operations/release-compatibility-pair-registry.v1.json",
    "client baseline": ROOT / "contracts/operations/client-baseline-registry.v1.json",
    "parser artifact": ROOT / "contracts/operations/parser-artifact-registry.v1.json",
    "production-shaped failure drill": ROOT / "contracts/operations/production-shaped-failure-drill-registry.v1.json",
}
DOMAIN_REJECTIONS = {"Fail", "Failure", "RegistrationFailure"}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    require(spec is not None and spec.loader is not None, f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_validator_rejected(
    validator: Any,
    path: Path,
    name: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    bad = copy.deepcopy(load(path))
    mutate(bad)
    original_load = validator.load

    def patched_load(candidate: str) -> dict[str, Any]:
        relative = path.relative_to(ROOT).as_posix()
        if candidate == relative:
            return copy.deepcopy(bad)
        return original_load(candidate)

    validator.load = patched_load
    try:
        validator.main()
    except validator.Fail:
        print(f"PASS validator reject: {name}")
        return
    finally:
        validator.load = original_load
    raise Fail(f"corrupt append-only authority unexpectedly accepted by validator: {name}")


def expect_generator_rejected(
    generator: Any,
    path: Path,
    name: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    bad = copy.deepcopy(load(path))
    mutate(bad)
    original_load = generator.load
    relative = path.relative_to(ROOT).as_posix()
    output_before = generator.OUTPUT.read_bytes()

    def patched_load(candidate: str) -> dict[str, Any]:
        if candidate == relative:
            return copy.deepcopy(bad)
        return original_load(candidate)

    generator.load = patched_load
    rejected = False
    try:
        generator.main()
    except SystemExit:
        rejected = True
    except RuntimeError as exc:
        require(exc.__class__.__name__ in DOMAIN_REJECTIONS, f"unexpected generator RuntimeError for {name}: {exc}")
        rejected = True
    finally:
        generator.load = original_load
    require(rejected, f"corrupt append-only authority unexpectedly accepted by generator: {name}")
    require(generator.OUTPUT.read_bytes() == output_before, f"generator mutated inventory after rejecting corrupt authority: {name}")
    print(f"PASS generator reject: {name}")


def main() -> int:
    require(VALIDATOR.is_file(), "inventory source-authority validator missing")
    require(GENERATOR.is_file(), "inventory generator missing")
    require(all(path.is_file() for path in AUTHORITIES.values()), "canonical append-only authority missing")
    validator = load_module(VALIDATOR, "memory_os_inventory_registry_negative_validator")
    generator = load_module(GENERATOR, "memory_os_inventory_registry_negative_generator")
    before = {path: path.read_bytes() for path in AUTHORITIES.values()}
    inventory_before = generator.OUTPUT.read_bytes()

    validator.main()
    generator.main()
    require(generator.OUTPUT.read_bytes() == inventory_before, "canonical inventory generator is not byte-deterministic")
    print("PASS baseline: canonical append-only authorities accepted without inventory drift")

    cases: list[tuple[Path, str, Callable[[dict[str, Any]], None]]] = [
        (
            AUTHORITIES["migration production-shaped admission"],
            "migration production-shaped admission append-only disabled",
            lambda value: value.__setitem__("appendOnly", False),
        ),
        (
            AUTHORITIES["incident contact routing"],
            "incident contact routing append-only disabled",
            lambda value: value.__setitem__("appendOnly", False),
        ),
        (
            AUTHORITIES["observability stack"],
            "observability stack append-only disabled",
            lambda value: value.__setitem__("appendOnly", False),
        ),
        (
            AUTHORITIES["rate-limit distributed runtime"],
            "rate-limit distributed runtime append-only disabled",
            lambda value: value.__setitem__("appendOnly", False),
        ),
        (
            AUTHORITIES["environment generation"],
            "environment generation registryClass drift",
            lambda value: value.__setitem__("registryClass", "NOT_PRODUCTION_EQUIVALENT_GENERATIONS"),
        ),
        (
            AUTHORITIES["environment generation"],
            "environment generation boolean count",
            lambda value: value.__setitem__("registeredGenerationCount", True),
        ),
        (
            AUTHORITIES["environment generation"],
            "environment generation empty current pointer manufactured",
            lambda value: value.__setitem__("currentGenerationId", "pegen_manufactured_current"),
        ),
        (
            AUTHORITIES["recovery objective"],
            "recovery objective schema drift",
            lambda value: value.__setitem__("schemaVersion", "invalid"),
        ),
        (
            AUTHORITIES["recovery objective"],
            "recovery objective boolean count",
            lambda value: value.__setitem__("approvedObjectiveCount", True),
        ),
        (
            AUTHORITIES["recovery objective"],
            "recovery objective empty current pointer manufactured",
            lambda value: value.__setitem__("currentObjectiveId", "bro_manufactured_current"),
        ),
        (
            AUTHORITIES["drill request"],
            "drill request append-only disabled",
            lambda value: value.__setitem__("appendOnly", False),
        ),
        (
            AUTHORITIES["drill request"],
            "drill request boolean executable count",
            lambda value: value.__setitem__("currentExecutableRequestCount", True),
        ),
        (
            AUTHORITIES["drill request"],
            "drill request executable count manufactured without history",
            lambda value: value.__setitem__("currentExecutableRequestCount", 1),
        ),
        (
            AUTHORITIES["generation recovery evidence"],
            "generation recovery evidence schema drift",
            lambda value: value.__setitem__("schemaVersion", "invalid"),
        ),
        (
            AUTHORITIES["generation recovery evidence"],
            "generation recovery evidence boolean count",
            lambda value: value.__setitem__("registeredEvidenceCount", True),
        ),
        (
            AUTHORITIES["generation recovery evidence"],
            "generation recovery final candidate manufactured without evidence",
            lambda value: value.__setitem__("productionEquivalentRecoveryCandidateCount", 1),
        ),
        (
            AUTHORITIES["typed non-resurrection"],
            "typed non-resurrection production readiness manufactured",
            lambda value: value.__setitem__("productionReady", True),
        ),
        (
            AUTHORITIES["typed non-resurrection"],
            "typed non-resurrection boolean count",
            lambda value: value.__setitem__("registeredRecordCount", True),
        ),
        (
            AUTHORITIES["typed non-resurrection"],
            "typed non-resurrection candidate coverage manufactured without records",
            lambda value: value.__setitem__("candidateCoveredCount", 1),
        ),
        (
            AUTHORITIES["human promotion review"],
            "human promotion latest decision manufactured",
            lambda value: value.__setitem__("latestDecisionId", "brpr_manufactured_authority"),
        ),
        (
            AUTHORITIES["human promotion review"],
            "human promotion current decision manufactured",
            lambda value: value.__setitem__("currentDecisionId", "brpr_manufactured_current_authority"),
        ),
        (
            AUTHORITIES["human promotion review"],
            "human promotion boolean count",
            lambda value: value.__setitem__("registeredReviewCount", True),
        ),
        (
            AUTHORITIES["human promotion review"],
            "human promotion production traffic manufactured",
            lambda value: value.__setitem__("productionTrafficChanged", True),
        ),
        (
            AUTHORITIES["release baseline"],
            "release baseline append-only disabled",
            lambda value: value.__setitem__("appendOnly", False),
        ),
        (
            AUTHORITIES["release compatibility pair"],
            "release compatibility pair append-only disabled",
            lambda value: value.__setitem__("appendOnly", False),
        ),
        (
            AUTHORITIES["client baseline"],
            "client baseline append-only disabled",
            lambda value: value.__setitem__("appendOnly", False),
        ),
        (
            AUTHORITIES["parser artifact"],
            "parser artifact append-only disabled",
            lambda value: value.__setitem__("appendOnly", False),
        ),
        (
            AUTHORITIES["production-shaped failure drill"],
            "production-shaped failure drill append-only disabled",
            lambda value: value.__setitem__("appendOnly", False),
        ),
    ]
    for path, name, mutate in cases:
        expect_validator_rejected(validator, path, name, mutate)
        expect_generator_rejected(generator, path, name, mutate)

    after = {path: path.read_bytes() for path in AUTHORITIES.values()}
    require(after == before, "negative suite mutated canonical append-only authority")
    require(generator.OUTPUT.read_bytes() == inventory_before, "negative suite mutated canonical inventory")
    print("Memory OS operability inventory append-only authority negative suite PASS")
    print("canonical registry corruption accepted by source-authority validator: false")
    print("canonical registry corruption accepted by inventory generator: false")
    print("unexpected implementation RuntimeError normalized as domain rejection: false")
    print("rejected generator run mutated inventory: false")
    print("canonical append-only authority mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OPERABILITY INVENTORY REGISTRY NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
