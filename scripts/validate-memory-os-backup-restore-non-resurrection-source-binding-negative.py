#!/usr/bin/env python3
"""Reject typed non-resurrection evidence created after its claimed source commit."""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
POST_SOURCE_REF = "docs/evidence/backup-restore/non-resurrection/source-binding-negative.json"
POST_SOURCE_PATH = ROOT / POST_SOURCE_REF


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_non_resurrection_source_binding_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load typed non-resurrection writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(writer, source_commit: str, ref: str, field: str) -> None:
    try:
        writer.require_ref_bound_to_source(source_commit, ref, field)
    except writer.Fail:
        print(f"PASS reject: {field}")
        return
    raise Fail(f"post-source evidence unexpectedly accepted: {field}")


def main() -> int:
    writer = load_writer()
    source_commit = git("rev-parse", "HEAD")
    writer_ref = WRITER.relative_to(ROOT).as_posix()

    writer.require_ref_bound_to_source(source_commit, writer_ref, "tracked control evidence")
    print("PASS accept: tracked control evidence exists unchanged at sourceCommitSha")

    POST_SOURCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        POST_SOURCE_PATH.unlink(missing_ok=True)
        POST_SOURCE_PATH.write_text("{}\n", encoding="utf-8")
        expect_rejected(writer, source_commit, POST_SOURCE_REF, "post-source typed evidence")
    finally:
        POST_SOURCE_PATH.unlink(missing_ok=True)

    print("Memory OS backup/restore non-resurrection source-binding negative suite PASS")
    print("post-source typed evidence accepted: false")
    print("canonical registries mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE NON-RESURRECTION SOURCE-BINDING NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
