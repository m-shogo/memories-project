#!/usr/bin/env python3
"""Prove registered environment evidence remains byte-bound to sourceCommitSha."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
EVIDENCE = ROOT / "README.md"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_source_binding_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load generation writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def head_sha() -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(completed.returncode == 0, "cannot resolve HEAD")
    value = completed.stdout.strip()
    require(len(value) == 40, "HEAD must be full SHA")
    return value


def expect_rejected(writer: Any, name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except writer.Fail:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name}: leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"{name}: source-bound evidence drift unexpectedly accepted")


def evidence_env(ref: str) -> dict[str, Any]:
    return {
        "postgresql": {"restoreEvidenceRef": ref},
        "objectStorage": {"restoreEvidenceRef": ref},
        "network": {"latencyProfileRef": ref, "failureInjectionRef": ref},
        "identityAndSecrets": {"credentialScopeRef": ref},
        "backupRestore": {"evidenceRef": ref},
        "materialDeltas": [{"independentReviewRef": ref}],
        "evidenceBoundary": {"independentReviewRef": ref},
    }


def main() -> int:
    require(WRITER.is_file() and EVIDENCE.is_file(), "generation source-binding fixture missing")
    writer = load_writer()
    source = head_sha()
    ref = EVIDENCE.relative_to(ROOT).as_posix()
    env = evidence_env(ref)

    writer.require_environment_evidence_bound_to_source(source, env)
    print("PASS accept: unchanged repository evidence matches sourceCommitSha")

    original = EVIDENCE.read_bytes()
    try:
        EVIDENCE.write_bytes(original + b"\nsource-binding-negative-mutation\n")
        expect_rejected(
            writer,
            "environment evidence changed after sourceCommitSha",
            lambda: writer.require_environment_evidence_bound_to_source(source, env),
        )
    finally:
        EVIDENCE.write_bytes(original)

    require(EVIDENCE.read_bytes() == original, "source-binding negative suite failed to restore evidence fixture")
    print("Environment generation source-binding negative suite PASS")
    print("source-bound evidence mutation accepted: false")
    print("canonical evidence left mutated: false")
    print("generation created: false")
    print("production evidence: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT GENERATION SOURCE-BINDING NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
