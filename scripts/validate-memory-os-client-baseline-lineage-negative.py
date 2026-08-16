#!/usr/bin/env python3
"""Prove reviewed client baselines cannot cite a non-ancestor source commit."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "scripts/register-memory-os-client-baseline.py"
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-client-baseline-registry.py"


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


def git(*args: str, input_text: str | None = None) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, input=input_text,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    require(completed.returncode == 0,
            f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def main() -> int:
    require(git("status", "--porcelain") == "", "working tree must start clean")
    head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    side_commit = git(
        "commit-tree", tree, "-p", head,
        input_text="synthetic client baseline side commit\n",
    )
    require(side_commit != head, "side commit was not created")

    writer = load_module(WRITER_PATH, "client_baseline_writer_lineage_negative")
    try:
        writer.validate_source_commit_lineage(side_commit)
    except writer.Failure:
        pass
    else:
        raise NegativeFailure("writer accepted a non-ancestor source commit")

    validator = load_module(VALIDATOR_PATH, "client_baseline_validator_lineage_negative")
    require(validator.commit_is_ancestor(side_commit) is False,
            "standalone validator accepted a non-ancestor source commit")
    require(validator.commit_is_ancestor(head) is True,
            "standalone validator rejected current HEAD lineage")
    require(git("status", "--porcelain") == "", "negative test mutated working tree")

    print("Client baseline source lineage negative PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"CLIENT BASELINE LINEAGE NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
