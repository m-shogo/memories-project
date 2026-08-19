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
STANDALONE_VALIDATOR = ROOT / "scripts/validate-memory-os-operability-admission-inventory.py"
GENERATOR = ROOT / "scripts/generate-memory-os-operability-admission-inventory.py"
TABLETOP_LEDGER = ROOT / "docs/evidence/incident-tabletops"
ROGUE_TABLETOP = TABLETOP_LEDGER / "IR-DRILL-ROGUE.json"
PATH_ALIAS_TARGET = ROOT / "contracts/operations/.inventory-authority-negative-target.json"
PATH_ALIAS = ROOT / "contracts/operations/.inventory-authority-negative-alias.json"
AUTHORITIES = {
    "migration production-shaped admission": ROOT / "contracts/operations/migration-production-shaped-admission-registry.v1.json",
    "incident contact routing": ROOT / "contracts/operations/incident-contact-routing-admission-registry.v1.json",
    "observability stack": ROOT / "contracts/operations/observability-stack-deployment-registry.v1.json",
    "rate-limit distributed runtime": ROOT / "contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json",
    "sustained soak independent review": ROOT / "contracts/operations/sustained-soak-independent-review-registry.v1.json",
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


def expect_standalone_source_rejected(
    standalone: Any,
    path: Path,
    name: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    original = path.read_bytes()
    bad = copy.deepcopy(load(path))
    mutate(bad)
    path.write_text(json.dumps(bad, indent=2) + "\n", encoding="utf-8")
    rejected = False
    try:
        try:
            standalone.main()
        except RuntimeError as exc:
            require(exc.__class__.__name__ in DOMAIN_REJECTIONS, f"unexpected standalone RuntimeError for {name}: {exc}")
            rejected = True
    finally:
        path.write_bytes(original)
    require(rejected, f"corrupt source authority unexpectedly accepted by standalone inventory validator: {name}")
    print(f"PASS standalone validator reject: {name}")


def expect_standalone_source_wrapper_boundaries(standalone: Any) -> None:
    original = VALIDATOR.read_bytes()
    try:
        VALIDATOR.write_text("def main():\n    return False\n", encoding="utf-8")
        try:
            standalone.validate_source_authorities()
        except standalone.Fail as exc:
            require("returned nonzero result" in str(exc), f"unexpected false-result rejection: {exc}")
        else:
            raise Fail("boolean false source-validator result unexpectedly accepted as exit zero")

        VALIDATOR.write_text(
            "class Fail(RuntimeError):\n    pass\n\ndef main():\n    raise Fail('synthetic source authority rejection')\n",
            encoding="utf-8",
        )
        try:
            standalone.validate_source_authorities()
        except standalone.Fail as exc:
            require("inventory source authority invalid" in str(exc), f"domain rejection was not normalized: {exc}")
        else:
            raise Fail("domain source-authority rejection unexpectedly accepted")

        VALIDATOR.write_text(
            "def main():\n    raise RuntimeError('synthetic standalone source implementation bug')\n",
            encoding="utf-8",
        )
        propagated = False
        try:
            standalone.validate_source_authorities()
        except standalone.Fail as exc:
            raise Fail(f"implementation RuntimeError was normalized as standalone authority rejection: {exc}") from exc
        except RuntimeError as exc:
            require(exc.__class__ is RuntimeError, f"unexpected standalone implementation error type: {exc.__class__.__name__}")
            require("synthetic standalone source implementation bug" in str(exc), "standalone implementation RuntimeError detail lost")
            propagated = True
        require(propagated, "standalone source-validator implementation RuntimeError did not propagate")
    finally:
        VALIDATOR.write_bytes(original)
    require(VALIDATOR.read_bytes() == original, "standalone wrapper boundary test did not restore source validator bytes")
    print("PASS standalone validator: source wrapper result/error boundaries are fail-closed")


def expect_standalone_path_alias_rejected(standalone: Any) -> None:
    require(not PATH_ALIAS_TARGET.exists() and not PATH_ALIAS.exists(), "standalone path alias fixture already exists")
    PATH_ALIAS_TARGET.write_text("{}\n", encoding="utf-8")
    PATH_ALIAS.symlink_to(PATH_ALIAS_TARGET.name)
    try:
        try:
            standalone.load(PATH_ALIAS)
        except standalone.Fail as exc:
            require("canonical authority path drift" in str(exc), f"unexpected path alias rejection: {exc}")
        else:
            raise Fail("repository-internal authority symlink alias unexpectedly accepted")
    finally:
        PATH_ALIAS.unlink(missing_ok=True)
        PATH_ALIAS_TARGET.unlink(missing_ok=True)
    require(not PATH_ALIAS.exists() and not PATH_ALIAS_TARGET.exists(), "standalone path alias fixture cleanup failed")
    print("PASS standalone validator: repository-internal authority symlink alias rejected")


def expect_untracked_tabletop_rejected(validator: Any, generator: Any) -> None:
    require(not ROGUE_TABLETOP.exists(), "rogue tabletop fixture path already exists")
    inventory_before = generator.OUTPUT.read_bytes()
    TABLETOP_LEDGER.mkdir(parents=True, exist_ok=True)
    ROGUE_TABLETOP.write_text(
        json.dumps(
            {
                "schemaVersion": "memory-os-incident-human-tabletop-record.v1",
                "scenarioId": "IR-DRILL-ROGUE",
                "productionEvidence": False,
                "productionReady": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        try:
            validator.main()
        except validator.Fail as exc:
            require(
                "must be committed" in str(exc) or "human incident tabletop ledger invalid" in str(exc),
                f"unexpected human tabletop source rejection reason: {exc}",
            )
            print("PASS validator reject: untracked human tabletop filename cannot inflate inventory source authority")
        else:
            raise Fail("untracked human tabletop filename unexpectedly accepted by inventory source authority")

        generator_rejected = False
        try:
            generator.main()
        except SystemExit as exc:
            require(exc.code not in (None, 0), "inventory generator exited successfully for rogue tabletop authority")
            generator_rejected = True
        except RuntimeError as exc:
            require(exc.__class__.__name__ in DOMAIN_REJECTIONS, f"unexpected generator RuntimeError for rogue tabletop authority: {exc}")
            generator_rejected = True
        require(generator_rejected, "untracked human tabletop filename unexpectedly accepted by inventory generator")
        require(generator.OUTPUT.read_bytes() == inventory_before, "generator mutated inventory after rejecting rogue tabletop authority")
        print("PASS generator reject: untracked human tabletop filename cannot inflate generated inventory")
    finally:
        ROGUE_TABLETOP.unlink(missing_ok=True)
    require(generator.OUTPUT.read_bytes() == inventory_before, "human tabletop source rejection mutated canonical inventory")


def expect_generator_load_authority_rejected(generator: Any) -> None:
    inventory_before = generator.OUTPUT.read_bytes()
    original = generator.require_canonical_load_authority

    def reject_load_authority() -> None:
        raise SystemExit("synthetic canonical load authority rejection")

    generator.require_canonical_load_authority = reject_load_authority
    rejected = False
    try:
        generator.main()
    except SystemExit as exc:
        require(exc.code not in (None, 0), "inventory generator exited successfully after canonical load authority rejection")
        rejected = True
    finally:
        generator.require_canonical_load_authority = original
    require(rejected, "inventory generator bypassed canonical load authority validation")
    require(generator.OUTPUT.read_bytes() == inventory_before, "load authority rejection mutated canonical inventory")
    print("PASS generator reject: canonical load authority validation cannot be bypassed")


def expect_generator_backup_derived_authority_rejected(generator: Any) -> None:
    inventory_before = generator.OUTPUT.read_bytes()
    original = generator.require_canonical_command_authority
    calls: list[str] = []

    def reject_backup_authority(script_name: str, module_name: str, label: str) -> None:
        calls.append(script_name)
        raise SystemExit(f"synthetic canonical backup derived authority rejection: {label}")

    generator.require_canonical_command_authority = reject_backup_authority
    rejected = False
    try:
        generator.main()
    except SystemExit as exc:
        require(exc.code not in (None, 0), "inventory generator exited successfully after backup derived authority rejection")
        rejected = True
    finally:
        generator.require_canonical_command_authority = original
    require(rejected, "inventory generator bypassed canonical backup derived authority validation")
    require(
        calls == ["validate-memory-os-backup-restore-generation-binding.py"],
        "inventory generator did not enter backup derived authority validation at the first canonical boundary",
    )
    require(generator.OUTPUT.read_bytes() == inventory_before, "backup derived authority rejection mutated canonical inventory")
    print("PASS generator reject: canonical backup derived authority validation cannot be bypassed")


def expect_source_validator_implementation_error_propagates(validator: Any) -> None:
    original = validator.load_validator

    def patched_load_validator(relative: str, module_name: str, function_name: str):
        def synthetic_bug(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("synthetic source validator implementation bug")

        return synthetic_bug

    validator.load_validator = patched_load_validator
    propagated = False
    try:
        try:
            validator.validate_source(
                "contracts/operations/migration-production-shaped-admission-registry.v1.json",
                "scripts/register-memory-os-migration-production-shaped-admission.py",
                "memory_os_inventory_source_runtime_error_negative",
                "validate_registry_for_append",
                "synthetic source authority",
            )
        except validator.Fail as exc:
            raise Fail(f"implementation RuntimeError was normalized as authority rejection: {exc}") from exc
        except RuntimeError as exc:
            require(exc.__class__ is RuntimeError, f"unexpected implementation error type: {exc.__class__.__name__}")
            require("synthetic source validator implementation bug" in str(exc), "implementation RuntimeError detail lost")
            propagated = True
    finally:
        validator.load_validator = original
    require(propagated, "source validator implementation RuntimeError did not propagate")
    print("PASS source validator: implementation RuntimeError propagates unchanged")


def main() -> int:
    require(VALIDATOR.is_file(), "inventory source-authority validator missing")
    require(STANDALONE_VALIDATOR.is_file(), "standalone inventory validator missing")
    require(GENERATOR.is_file(), "inventory generator missing")
    require(all(path.is_file() for path in AUTHORITIES.values()), "canonical append-only authority missing")
    validator = load_module(VALIDATOR, "memory_os_inventory_registry_negative_validator")
    standalone = load_module(STANDALONE_VALIDATOR, "memory_os_inventory_registry_negative_standalone")
    generator = load_module(GENERATOR, "memory_os_inventory_registry_negative_generator")
    before = {path: path.read_bytes() for path in AUTHORITIES.values()}
    inventory_before = generator.OUTPUT.read_bytes()

    validator.main()
    standalone.main()
    generator.main()
    require(generator.OUTPUT.read_bytes() == inventory_before, "canonical inventory generator is not byte-deterministic")
    print("PASS baseline: canonical append-only authorities accepted without inventory drift")
    expect_untracked_tabletop_rejected(validator, generator)
    expect_generator_load_authority_rejected(generator)
    expect_generator_backup_derived_authority_rejected(generator)
    expect_source_validator_implementation_error_propagates(validator)
    expect_standalone_source_wrapper_boundaries(standalone)
    expect_standalone_path_alias_rejected(standalone)
    expect_standalone_source_rejected(
        standalone,
        AUTHORITIES["rate-limit distributed runtime"],
        "rate-limit distributed runtime append-only disabled through full source-authority delegation",
        lambda value: value.__setitem__("appendOnly", False),
    )

    source_only_cases: list[tuple[Path, str, Callable[[dict[str, Any]], None]]] = [
        (
            AUTHORITIES["sustained soak independent review"],
            "sustained soak independent review append-only disabled",
            lambda value: value.__setitem__("appendOnly", False),
        ),
        (
            AUTHORITIES["sustained soak independent review"],
            "sustained soak independent review boolean criteria count",
            lambda value: value.__setitem__("approvedLeakStabilityCriteriaCount", True),
        ),
        (
            AUTHORITIES["sustained soak independent review"],
            "sustained soak independent review registry class drift",
            lambda value: value.__setitem__("registryClass", "NOT_SUSTAINED_SOAK_INDEPENDENT_REVIEW"),
        ),
        (
            AUTHORITIES["sustained soak independent review"],
            "sustained soak independent review unknown field",
            lambda value: value.__setitem__("automaticPromotionAuthorized", True),
        ),
        (
            AUTHORITIES["sustained soak independent review"],
            "sustained soak independent review production readiness manufactured",
            lambda value: value.__setitem__("productionReady", True),
        ),
    ]
    for path, name, mutate in source_only_cases:
        expect_validator_rejected(validator, path, name, mutate)
        expect_generator_rejected(generator, path, name, mutate)

    cases: list[tuple[Path, str, Callable[[dict[str, Any]], None]]] = [
        (AUTHORITIES["migration production-shaped admission"], "migration production-shaped admission append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
        (AUTHORITIES["incident contact routing"], "incident contact routing append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
        (AUTHORITIES["observability stack"], "observability stack append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
        (AUTHORITIES["rate-limit distributed runtime"], "rate-limit distributed runtime append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
        (AUTHORITIES["environment generation"], "environment generation registryClass drift", lambda value: value.__setitem__("registryClass", "NOT_PRODUCTION_EQUIVALENT_GENERATIONS")),
        (AUTHORITIES["environment generation"], "environment generation boolean count", lambda value: value.__setitem__("registeredGenerationCount", True)),
        (AUTHORITIES["environment generation"], "environment generation empty current pointer manufactured", lambda value: value.__setitem__("currentGenerationId", "pegen_manufactured_current")),
        (AUTHORITIES["recovery objective"], "recovery objective schema drift", lambda value: value.__setitem__("schemaVersion", "invalid")),
        (AUTHORITIES["recovery objective"], "recovery objective boolean count", lambda value: value.__setitem__("approvedObjectiveCount", True)),
        (AUTHORITIES["recovery objective"], "recovery objective empty current pointer manufactured", lambda value: value.__setitem__("currentObjectiveId", "bro_manufactured_current")),
        (AUTHORITIES["drill request"], "drill request append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
        (AUTHORITIES["drill request"], "drill request boolean executable count", lambda value: value.__setitem__("currentExecutableRequestCount", True)),
        (AUTHORITIES["drill request"], "drill request executable count manufactured without history", lambda value: value.__setitem__("currentExecutableRequestCount", 1)),
        (AUTHORITIES["generation recovery evidence"], "generation recovery evidence schema drift", lambda value: value.__setitem__("schemaVersion", "invalid")),
        (AUTHORITIES["generation recovery evidence"], "generation recovery evidence boolean count", lambda value: value.__setitem__("registeredEvidenceCount", True)),
        (AUTHORITIES["generation recovery evidence"], "generation recovery final candidate manufactured without evidence", lambda value: value.__setitem__("productionEquivalentRecoveryCandidateCount", 1)),
        (AUTHORITIES["typed non-resurrection"], "typed non-resurrection production readiness manufactured", lambda value: value.__setitem__("productionReady", True)),
        (AUTHORITIES["typed non-resurrection"], "typed non-resurrection boolean count", lambda value: value.__setitem__("registeredRecordCount", True)),
        (AUTHORITIES["typed non-resurrection"], "typed non-resurrection candidate coverage manufactured without records", lambda value: value.__setitem__("candidateCoveredCount", 1)),
        (AUTHORITIES["human promotion review"], "human promotion latest decision manufactured", lambda value: value.__setitem__("latestDecisionId", "brpr_manufactured_authority")),
        (AUTHORITIES["human promotion review"], "human promotion current decision manufactured", lambda value: value.__setitem__("currentDecisionId", "brpr_manufactured_current_authority")),
        (AUTHORITIES["human promotion review"], "human promotion boolean count", lambda value: value.__setitem__("registeredReviewCount", True)),
        (AUTHORITIES["human promotion review"], "human promotion production traffic manufactured", lambda value: value.__setitem__("productionTrafficChanged", True)),
        (AUTHORITIES["release baseline"], "release baseline append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
        (AUTHORITIES["release compatibility pair"], "release compatibility pair append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
        (AUTHORITIES["client baseline"], "client baseline append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
        (AUTHORITIES["parser artifact"], "parser artifact append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
        (AUTHORITIES["production-shaped failure drill"], "production-shaped failure drill append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
    ]
    for path, name, mutate in cases:
        expect_validator_rejected(validator, path, name, mutate)
        expect_generator_rejected(generator, path, name, mutate)

    after = {path: path.read_bytes() for path in AUTHORITIES.values()}
    require(after == before, "negative suite mutated canonical append-only authority")
    require(generator.OUTPUT.read_bytes() == inventory_before, "negative suite mutated canonical inventory")
    require(not ROGUE_TABLETOP.exists(), "negative suite left rogue tabletop fixture behind")
    require(not PATH_ALIAS.exists() and not PATH_ALIAS_TARGET.exists(), "negative suite left standalone path alias fixture behind")
    print("Memory OS operability inventory append-only authority negative suite PASS")
    print("canonical registry corruption accepted by source-authority validator: false")
    print("non-OPS source corruption accepted by standalone inventory validator: false")
    print("boolean false source-validator success accepted by standalone inventory validator: false")
    print("source-validator domain rejection hidden by standalone inventory validator: false")
    print("source-validator implementation RuntimeError normalized by standalone inventory validator: false")
    print("repository-internal symlink alias accepted by standalone inventory validator: false")
    print("sustained-soak source corruption accepted by source-authority validator: false")
    print("sustained-soak source corruption accepted by inventory generator: false")
    print("canonical registry corruption accepted by inventory generator: false")
    print("untracked human tabletop filename accepted as inventory source authority: false")
    print("untracked human tabletop filename accepted by inventory generator: false")
    print("canonical load authority rejection bypassed by inventory generator: false")
    print("canonical backup derived authority rejection bypassed by inventory generator: false")
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
