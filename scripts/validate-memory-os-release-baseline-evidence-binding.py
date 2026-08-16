#!/usr/bin/env python3
"""Fail-closed source binding for approved release baseline evidence refs."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/release-baseline-registry-contract.v1.json"
REGISTRY_PATH = ROOT / "contracts/operations/release-baseline-registry.v1.json"
WRITER_PATH = ROOT / "scripts/register-memory-os-release-baseline.py"
EVIDENCE_FIELDS = (
    "compatibilityEvidenceRefs",
    "restoreEvidenceRefs",
    "securityEvidenceRefs",
)


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(completed.returncode == 0, f"git {' '.join(arguments)} failed")
    return completed.stdout.strip()


def load_writer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_release_baseline_writer_binding", WRITER_PATH)
    require(spec is not None and spec.loader is not None, "cannot load release baseline writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_evidence_ref_binding(commit_sha: str, ref: str) -> None:
    writer = load_writer()
    try:
        writer.validate_evidence_ref_binding(commit_sha, ref)
    except Exception as exc:
        raise ValidationFailure(str(exc)) from exc


def main() -> int:
    contract = load(CONTRACT_PATH)
    binding = contract.get("evidenceBinding")
    require(isinstance(binding, dict), "release evidenceBinding authority missing")
    require(binding == {
        "sourceCommitField": "commitSha",
        "repositoryTrackedRequired": True,
        "repositoryContainmentRequired": True,
        "symlinkForbidden": True,
        "parentDirectorySymlinkForbidden": True,
        "sourceCommitBlobRequired": True,
        "currentBytesMustMatchSourceCommit": True,
    }, "release evidenceBinding authority drift")

    registry = load(REGISTRY_PATH)
    writer = load_writer()
    try:
        writer.validate_registry_for_append(registry, contract)
    except Exception as exc:
        raise ValidationFailure(str(exc)) from exc

    releases = registry.get("releases")
    require(isinstance(releases, list), "release registry releases must be a list")
    head = git("rev-parse", "HEAD")
    for record in releases:
        require(isinstance(record, dict), "release record must be an object")
        commit_sha = record.get("commitSha")
        require(isinstance(commit_sha, str), "release commitSha missing")
        completed = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit_sha, head],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        require(completed.returncode == 0,
                f"release commit is not an ancestor of current HEAD: {commit_sha}")
        for field in EVIDENCE_FIELDS:
            refs = record.get(field)
            require(isinstance(refs, list) and refs, f"{field} must contain evidence refs")
            for ref in refs:
                require(isinstance(ref, str) and ref.strip(), f"{field} contains invalid ref")
                try:
                    writer.validate_evidence_ref_binding(commit_sha, ref)
                except Exception as exc:
                    raise ValidationFailure(str(exc)) from exc

    print("Memory OS release baseline evidence source binding PASS")
    print(f"approved releases checked: {len(releases)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"RELEASE BASELINE EVIDENCE BINDING FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
