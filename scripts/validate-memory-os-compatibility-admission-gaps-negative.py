#!/usr/bin/env python3
"""Pin fail-closed compatibility admission count and authority semantics."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/update-memory-os-compatibility-admission-gaps.py"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_generator():
    spec = importlib.util.spec_from_file_location("compatibility_admission_gap_generator", GENERATOR)
    require(spec is not None and spec.loader is not None, "cannot load compatibility gap generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_runtime_authority_identity(module) -> None:
    module.enforce_runtime_authorities()
    output_before = module.OUTPUT.read_bytes() if module.OUTPUT.exists() else None
    substitutions = (
        ("RELEASES", ROOT / "contracts/operations/client-baseline-registry.v1.json"),
        ("PAIRS", ROOT / "contracts/operations/release-baseline-registry.v1.json"),
        ("CLIENTS", ROOT / "contracts/operations/parser-artifact-registry.v1.json"),
        ("PARSERS", ROOT / "contracts/operations/client-baseline-registry.v1.json"),
        ("FOUNDATIONS", ROOT / "contracts/operations/version-compatibility-execution-evidence.v1.json"),
        ("EXECUTION", ROOT / "contracts/operations/version-compatibility-foundations.v1.json"),
        ("OUTPUT", ROOT / "contracts/operations/version-compatibility-foundations.v1.json"),
        ("RELEASE_WRITER", ROOT / "scripts/request-memory-os-rollback-rehearsal.py"),
        ("PAIR_WRITER", ROOT / "scripts/register-memory-os-client-baseline.py"),
        ("CLIENT_WRITER", ROOT / "scripts/register-memory-os-parser-artifact.py"),
        ("PARSER_WRITER", ROOT / "scripts/register-memory-os-release-baseline.py"),
        ("FOUNDATIONS_VALIDATOR", ROOT / "scripts/validate-memory-os-operability.py"),
        ("EXECUTION_VALIDATOR", ROOT / "scripts/validate-memory-os-version-compatibility-foundations.py"),
        ("OPERABILITY_VALIDATOR", ROOT / "scripts/validate-memory-os-client-server-support-window.py"),
        ("WORKFLOW", ROOT / ".github/workflows/version-compatibility-foundations.yml"),
    )
    for field, substitute in substitutions:
        original = getattr(module, field)
        try:
            setattr(module, field, substitute)
            rejected = False
            try:
                module.enforce_runtime_authorities()
            except SystemExit:
                rejected = True
            require(rejected, f"compatibility gap generator accepted {field} authority substitution")
            if output_before is None:
                require(not original.exists() if field == "OUTPUT" else True,
                        "rejected output substitution unexpectedly created canonical compatibility projection")
            else:
                require(module.OUTPUT_REL == Path("contracts/operations/compatibility-admission-gaps.v1.json"),
                        "canonical compatibility output relative authority drifted during substitution test")
                canonical_output = ROOT / module.OUTPUT_REL
                require(canonical_output.read_bytes() == output_before,
                        f"rejected {field} substitution mutated canonical compatibility projection")
        finally:
            setattr(module, field, original)
    module.enforce_runtime_authorities()


def expect_count_rejection(module, value, field: str) -> None:
    rejected = False
    try:
        module.non_negative_count(value, field)
    except SystemExit as exc:
        require(field in str(exc), f"unexpected count rejection for {field}: {exc}")
        rejected = True
    require(rejected, f"invalid compatibility count accepted for {field}: {value!r}")


def expect_pair_authority_rejection(module) -> None:
    path = module.PAIRS
    original = path.read_bytes()
    try:
        pair_registry = json.loads(original.decode("utf-8"))
        pair_registry["appendOnly"] = False
        path.write_text(json.dumps(pair_registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        rejected = False
        try:
            module.validate_registry_authorities(
                module.load(module.RELEASES),
                module.load(module.PAIRS),
                module.load(module.CLIENTS),
                module.load(module.PARSERS),
            )
        except SystemExit as exc:
            require("compatibility registry authority invalid" in str(exc),
                    f"unexpected rollback-pair authority rejection: {exc}")
            rejected = True
        require(rejected, "corrupt canonical rollback-pair authority was accepted")
    finally:
        path.write_bytes(original)
    require(path.read_bytes() == original,
            "canonical rollback-pair registry changed after negative validation")


def expect_projection_rollback(module) -> None:
    path = module.OUTPUT
    original = path.read_bytes() if path.exists() else None
    original_run_validator = module.run_validator
    calls: list[Path] = []

    def reject_operability(validator_path: Path) -> None:
        calls.append(validator_path)
        if validator_path == module.OPERABILITY_VALIDATOR:
            raise SystemExit("synthetic aggregate operability rejection")

    module.run_validator = reject_operability
    try:
        rejected = False
        try:
            module.write_validated_output({
                "schemaVersion": "synthetic-invalid-compatibility-admission-gaps",
                "productionEvidence": False,
                "productionReady": False,
                "productionDecision": "NO_GO",
            })
        except SystemExit as exc:
            require("synthetic aggregate operability rejection" in str(exc),
                    f"unexpected projection rollback rejection: {exc}")
            rejected = True
        require(rejected, "post-write aggregate rejection did not fail compatibility projection")
        require(calls == [module.OPERABILITY_VALIDATOR],
                f"compatibility projection did not invoke canonical operability validator exactly once: {calls}")
        if original is None:
            require(not path.exists(), "new compatibility projection remained after rejected post-write validation")
        else:
            require(path.read_bytes() == original,
                    "compatibility projection was not restored after rejected post-write validation")
    finally:
        module.run_validator = original_run_validator
        if original is None:
            path.unlink(missing_ok=True)
        else:
            module.atomic_replace_output_bytes(original)


def expect_atomic_replace_failure(module) -> None:
    path = module.OUTPUT
    original = path.read_bytes() if path.exists() else None
    original_replace = module.os.replace
    validator_called = False

    def fail_replace(source, target) -> None:
        raise OSError("synthetic compatibility admission atomic replace failure")

    def unexpected_validator(_validator_path: Path) -> None:
        nonlocal validator_called
        validator_called = True

    original_run_validator = module.run_validator
    module.os.replace = fail_replace
    module.run_validator = unexpected_validator
    try:
        rejected = False
        try:
            module.write_validated_output({
                "schemaVersion": "synthetic-atomic-replace-probe",
                "productionEvidence": False,
                "productionReady": False,
                "productionDecision": "NO_GO",
            })
        except OSError as exc:
            require("synthetic compatibility admission atomic replace failure" in str(exc),
                    f"unexpected atomic replacement rejection: {exc}")
            rejected = True
        require(rejected, "compatibility projection accepted synthetic atomic replace failure")
        require(not validator_called, "operability validator ran after failed atomic publication")
        if original is None:
            require(not path.exists(), "failed atomic replacement created compatibility projection")
        else:
            require(path.read_bytes() == original,
                    "failed atomic replacement changed canonical compatibility projection")
        leftovers = list(path.parent.glob(f".{path.name}.*.tmp"))
        require(not leftovers, f"failed atomic replacement left temporary authority files: {leftovers}")
    finally:
        module.os.replace = original_replace
        module.run_validator = original_run_validator
        if original is None:
            path.unlink(missing_ok=True)
        elif path.read_bytes() != original:
            module.atomic_replace_output_bytes(original)


def main() -> int:
    module = load_generator()
    expect_runtime_authority_identity(module)
    for field in (
        "approvedReleaseCount",
        "approvedClientBaselineCount",
        "reviewedArtifactCount",
        "rollbackEligiblePairCount",
    ):
        expect_count_rejection(module, True, field)
        expect_count_rejection(module, False, field)
        expect_count_rejection(module, -1, field)
    require(module.non_negative_count(0, "validZero") == 0, "zero count should remain valid")
    expect_pair_authority_rejection(module)
    expect_projection_rollback(module)
    expect_atomic_replace_failure(module)
    print("PASS: compatibility admission counts, exact authority, atomic publication and projection rollback fail closed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
