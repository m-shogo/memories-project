#!/usr/bin/env python3
"""Pin human-tabletop sourceCommitSha to the current branch lineage."""

from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-incident-human-tabletop.py"


def load_writer():
    spec = importlib.util.spec_from_file_location("incident_human_tabletop_writer", WRITER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load human tabletop writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def descendant_commit() -> str:
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip()
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "tabletop-negative",
        "GIT_AUTHOR_EMAIL": "tabletop-negative@example.invalid",
        "GIT_COMMITTER_NAME": "tabletop-negative",
        "GIT_COMMITTER_EMAIL": "tabletop-negative@example.invalid",
    })
    return subprocess.check_output(
        ["git", "commit-tree", tree, "-p", "HEAD", "-m", "human tabletop non-ancestor fixture"],
        cwd=ROOT,
        env=env,
        text=True,
    ).strip()


def main() -> int:
    writer = load_writer()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if not writer.commit_exists(head) or not writer.source_is_ancestor(head):
        raise RuntimeError("current HEAD must be a valid tabletop source authority")
    future = descendant_commit()
    if not writer.commit_exists(future):
        raise RuntimeError("negative descendant commit was not created")
    if writer.source_is_ancestor(future):
        raise RuntimeError("future/side commit was accepted as human tabletop source authority")
    print("PASS: human tabletop source authority is ancestor-only without creating human evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
