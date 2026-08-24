#!/usr/bin/env python3
"""Prove generation validator/writer authority refs cannot escape the repository."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-generation.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(name: str, action: Callable[[], object], failure_type: type[BaseException]) -> None:
    try:
        action()
    except failure_type:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def prove_validator_runtime_authorities(validator) -> None:
    cases = (
        ("CONTRACT", validator.REGISTRY),
        ("REGISTRY", validator.CONTRACT),
        ("ENV_SCHEMA", validator.GEN_SCHEMA),
        ("GEN_SCHEMA", validator.ENV_SCHEMA),
        ("ENV_VALIDATOR", validator.WRITER),
        ("WRITER", validator.ENV_VALIDATOR),
        ("NEGATIVE", validator.SOURCE_BINDING_NEGATIVE),
        ("SOURCE_BINDING_NEGATIVE", validator.LINEAGE_NEGATIVE),
        ("LINEAGE_NEGATIVE", validator.NEGATIVE),
        ("EXPECTED_LOCK", validator.ROOT / "contracts/operations/.recovery-objectives.lock"),
    )
    for attribute, replacement in cases:
        original = getattr(validator, attribute)
        try:
            setattr(validator, attribute, replacement)
            expect_rejected(
                f"generation validator {attribute} substitution",
                validator.enforce_runtime_authorities,
                validator.Fail,
            )
        finally:
            setattr(validator, attribute, original)
    validator.enforce_runtime_authorities()
    print(f"PASS boundary: generation validator exact authority substitutions rejected: {len(cases)}")


def main() -> int:
    require(WRITER.is_file(), "generation writer missing")
    require(VALIDATOR.is_file(), "generation validator missing")
    writer = load_module(WRITER, "memory_os_generation_writer_authority_path_negative")
    validator = load_module(VALIDATOR, "memory_os_generation_validator_authority_path_negative")
    require(writer.canonical_repo_file(writer.ENV_VALIDATOR, "environment record semantic validator") == writer.ENV_VALIDATOR, "canonical environment validator rejected")
    writer.require_canonical_runtime_authorities()
    writer.require_actual_cli_authorities()
    prove_validator_runtime_authorities(validator)

    original_root = validator.ROOT
    with tempfile.TemporaryDirectory(prefix="memory-os-generation-validator-root-") as root_tmp, tempfile.TemporaryDirectory(prefix="memory-os-generation-validator-external-") as external_tmp:
        root = Path(root_tmp)
        external_dir = Path(external_tmp)
        external = external_dir / "external.yml"
        local = root / "workflow.yml"
        local.write_text("name: local\n", encoding="utf-8")
        external.write_text("name: external\n", encoding="utf-8")
        escape = root / "escaped.yml"
        escape.symlink_to(external)
        validator.ROOT = root
        try:
            resolved = validator.repo_file("workflow.yml", "workflow")
            require(resolved == local.resolve(), "canonical repository authority ref rejected")
            expect_rejected(
                "absolute generation validator authority ref",
                lambda: validator.repo_file(str(local.resolve()), "workflow"),
                validator.Fail,
            )
            expect_rejected(
                "parent-traversal generation validator authority ref",
                lambda: validator.repo_file("nested/../workflow.yml", "workflow"),
                validator.Fail,
            )
            expect_rejected(
                "generation validator authority symlink escapes repository",
                lambda: validator.repo_file("escaped.yml", "workflow"),
                validator.Fail,
            )
        finally:
            validator.ROOT = original_root

        invalid_utf8 = root / "invalid-writer-input.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_rejected("generation writer invalid UTF-8 input", lambda: writer.load(invalid_utf8), writer.Fail)
        unreadable = root / "writer-directory-input.json"
        unreadable.mkdir()
        expect_rejected("generation writer unreadable directory input", lambda: writer.load(unreadable), writer.Fail)

        outside_validator = external_dir / "outside-environment-validator.py"
        outside_validator.write_text("VALUE = 1\n", encoding="utf-8")
        writer_escape = ROOT / ".tmp-generation-writer-validator-escape.py"
        original_env_validator = writer.ENV_VALIDATOR
        try:
            writer.ENV_VALIDATOR = outside_validator
            expect_rejected("generation writer semantic validator absolute path escapes repository", writer.load_environment_validator, writer.Fail)
            writer_escape.symlink_to(outside_validator)
            writer.ENV_VALIDATOR = writer_escape
            expect_rejected("generation writer semantic validator symlink escapes repository", writer.load_environment_validator, writer.Fail)
        finally:
            writer.ENV_VALIDATOR = original_env_validator
            try:
                writer_escape.unlink()
            except FileNotFoundError:
                pass

        outside_authority = external_dir / "outside-runtime-authority.json"
        outside_authority.write_text("{}\n", encoding="utf-8")
        escaped_authority = ROOT / ".tmp-generation-runtime-authority-escape.json"
        loop_authority = ROOT / ".tmp-generation-runtime-authority-loop.json"
        try:
            escaped_authority.symlink_to(outside_authority)
            loop_authority.symlink_to(loop_authority.name)
            for field in (
                "environment generation contract",
                "environment generation registry",
                "environment record schema",
                "generation record schema",
            ):
                expect_rejected(
                    f"{field} repository symlink escapes repository",
                    lambda field=field: writer.require_canonical_runtime_authority(escaped_authority, escaped_authority, field),
                    writer.Fail,
                )
                expect_rejected(
                    f"{field} repository symlink loop",
                    lambda field=field: writer.require_canonical_runtime_authority(loop_authority, loop_authority, field),
                    writer.Fail,
                )
        finally:
            escaped_authority.unlink(missing_ok=True)
            loop_authority.unlink(missing_ok=True)

        canonical_cli_authorities = (
            ("CONTRACT", writer.CANONICAL_CONTRACT),
            ("REGISTRY", writer.CANONICAL_REGISTRY),
            ("ENV_SCHEMA", writer.CANONICAL_ENV_SCHEMA),
            ("GEN_SCHEMA", writer.CANONICAL_GEN_SCHEMA),
            ("ENV_VALIDATOR", writer.CANONICAL_ENV_VALIDATOR),
            ("LOCK", writer.CANONICAL_LOCK),
        )
        for attribute, canonical in canonical_cli_authorities:
            original = getattr(writer, attribute)
            try:
                setattr(writer, attribute, outside_authority)
                expect_rejected(
                    f"generation writer CLI {attribute} substitution",
                    writer.require_actual_cli_authorities,
                    writer.Fail,
                )
            finally:
                setattr(writer, attribute, original)
            require(getattr(writer, attribute) == canonical, f"generation writer CLI {attribute} canonical authority not restored")
        writer.require_actual_cli_authorities()

    print("Memory OS production-equivalent generation authority-path negative suite PASS")
    print("absolute authority refs accepted: false")
    print("parent-traversal authority refs accepted: false")
    print("repo-local symlink to external authority accepted: false")
    print("validator exact data/schema/executable/lock substitutions accepted: false")
    print("writer invalid UTF-8/I/O accepted: false")
    print("writer executable semantic validator escape accepted: false")
    print("writer CLI data/executable/lock substitution accepted: false")
    print("canonical generation contract/registry/schema containment: enforced")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT GENERATION AUTHORITY-PATH NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
