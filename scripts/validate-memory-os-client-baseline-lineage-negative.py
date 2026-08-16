#!/usr/bin/env python3
"""Prove reviewed client baselines reject side-commit and corrupt registry authority."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "scripts/register-memory-os-client-baseline.py"
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-client-baseline-registry.py"
REGISTRY_PATH = ROOT / "contracts/operations/client-baseline-registry.v1.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args: str, input_text: str | None = None,
        env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, input=input_text, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    require(completed.returncode == 0,
            f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def expect_registry_rejection(writer: Any, base: dict[str, Any],
                              label: str, mutate: Callable[[dict[str, Any]], None]) -> None:
    candidate = copy.deepcopy(base)
    mutate(candidate)
    try:
        writer.validate_registry_for_append(candidate)
    except writer.Failure:
        return
    raise NegativeFailure(f"writer accepted corrupt client registry: {label}")


def main() -> int:
    require(git("status", "--porcelain") == "", "working tree must start clean")
    head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    commit_env = os.environ.copy()
    commit_env.update({
        "GIT_AUTHOR_NAME": "memory-os-ci",
        "GIT_AUTHOR_EMAIL": "memory-os-ci@example.invalid",
        "GIT_COMMITTER_NAME": "memory-os-ci",
        "GIT_COMMITTER_EMAIL": "memory-os-ci@example.invalid",
    })
    side_commit = git(
        "commit-tree", tree, "-p", head,
        input_text="synthetic client baseline side commit\n",
        env=commit_env,
    )
    require(side_commit != head, "side commit was not created")

    writer = load_module(WRITER_PATH, "client_baseline_writer_lineage_negative")
    try:
        writer.validate_source_commit_lineage(side_commit)
    except writer.Failure:
        pass
    else:
        raise NegativeFailure("writer accepted a non-ancestor source commit")

    base_registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    require(isinstance(base_registry, dict), "client registry fixture must be object")
    writer.validate_registry_for_append(copy.deepcopy(base_registry))
    cases: tuple[tuple[str, Callable[[dict[str, Any]], None]], ...] = (
        ("boolean count", lambda value: value.__setitem__("approvedClientBaselineCount", True)),
        ("count drift", lambda value: value.__setitem__("approvedClientBaselineCount", 1)),
        ("appendOnly false", lambda value: value.__setitem__("appendOnly", False)),
        ("production evidence promotion", lambda value: value.__setitem__("productionEvidence", True)),
        ("latest pointer drift", lambda value: value["latestApprovedClientByClass"].__setitem__("IOS_APP", "clb_20990101_fake")),
        ("unknown registry field", lambda value: value.__setitem__("unexpectedAuthority", True)),
    )
    for label, mutate in cases:
        expect_registry_rejection(writer, base_registry, label, mutate)

    validator = load_module(VALIDATOR_PATH, "client_baseline_validator_lineage_negative")
    require(validator.commit_is_ancestor(side_commit) is False,
            "standalone validator accepted a non-ancestor source commit")
    require(validator.commit_is_ancestor(head) is True,
            "standalone validator rejected current HEAD lineage")
    require(git("status", "--porcelain") == "", "negative test mutated working tree")

    print("Client baseline lineage and registry corruption negative PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"CLIENT BASELINE AUTHORITY NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
