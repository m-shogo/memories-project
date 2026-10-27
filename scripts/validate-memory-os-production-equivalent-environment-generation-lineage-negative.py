#!/usr/bin/env python3
"""Reject generation source commits that are not ancestors of the current HEAD."""

from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_generation_writer_lineage_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load generation writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args: str, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(completed.returncode == 0, f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def make_side_commit() -> str:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Memory OS Negative Suite",
            "GIT_AUTHOR_EMAIL": "memory-os-negative@example.invalid",
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
            "GIT_COMMITTER_NAME": "Memory OS Negative Suite",
            "GIT_COMMITTER_EMAIL": "memory-os-negative@example.invalid",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
        }
    )
    tree = git("rev-parse", "HEAD^{tree}")
    completed = subprocess.run(
        ["git", "commit-tree", tree],
        cwd=ROOT,
        env=env,
        input="synthetic non-ancestor generation source\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(completed.returncode == 0, f"cannot create side commit object: {completed.stderr.strip()}")
    value = completed.stdout.strip()
    require(len(value) == 40, "side commit SHA invalid")
    return value


def minimal_record(source_commit: str) -> dict[str, Any]:
    return {
        "schemaVersion": "memory-os-production-equivalent-environment-generation-record.v1",
        "environmentId": "pe-lineage-negative",
        "generationId": "pegen-lineage-negative-v1",
        "registeredAt": "2026-08-15T00:00:00Z",
        "sourceCommitSha": source_commit,
        "environmentManifestSha256": "a" * 64,
        "dependencyInventorySha256": "b" * 64,
        "evidenceBundleManifestSha256": "c" * 64,
        "materialDeltaLedgerSha256": "d" * 64,
        "environmentRecordRef": "unused-by-lineage-negative.json",
        "environmentRecordSha256": "e" * 64,
        "supersedesGenerationId": None,
        "productionTraffic": False,
        "productionCredentials": False,
        "productionEvidence": False,
        "productionReady": False,
    }


def prove_bounded_writer_git_authority(writer) -> None:
    """Fault-inject real writer Git/ancestry helpers without mutating refs."""
    original_run = writer.subprocess.run
    private_canary = "PRIVATE_ENVIRONMENT_GENERATION_GIT_CANARY"
    try:
        for scenario in ("positive", "timeout", "os-error", "exit", "oversize", "wrong-type"):
            def fake_run(args, **kwargs):
                require(args == ["git", "status", "--porcelain"]
                        and kwargs.get("cwd") == ROOT
                        and kwargs.get("text") is True
                        and kwargs.get("stdout") == subprocess.PIPE
                        and kwargs.get("stderr") == subprocess.DEVNULL
                        and kwargs.get("timeout") == writer.SOURCE_GIT_TIMEOUT
                        and kwargs.get("check") is False,
                        "generation Git helper privacy/timeout drift")
                if scenario == "timeout":
                    raise subprocess.TimeoutExpired(args, writer.SOURCE_GIT_TIMEOUT)
                if scenario == "os-error":
                    raise OSError(private_canary)
                if scenario == "exit":
                    return subprocess.CompletedProcess(args, 128, stdout="")
                if scenario == "oversize":
                    return subprocess.CompletedProcess(args, 0, stdout="x" * (writer.MAX_SOURCE_BYTES + 1))
                if scenario == "wrong-type":
                    return subprocess.CompletedProcess(args, 0, stdout=b"bytes-not-text")
                return subprocess.CompletedProcess(args, 0, stdout="  \n")
            writer.subprocess.run = fake_run
            if scenario == "positive":
                require(writer.git("status", "--porcelain") == "",
                        "generation Git positive control failed")
                continue
            expected = ("environment generation Git output size limit exceeded"
                        if scenario == "oversize"
                        else "environment generation Git authority unavailable")
            try:
                writer.git("status", "--porcelain")
            except writer.Fail as exc:
                require(str(exc) == expected and private_canary not in str(exc),
                        f"generation Git {scenario} exposed private diagnostics")
                if scenario in ("timeout", "os-error"):
                    require(exc.__suppress_context__,
                            f"generation Git {scenario} leaked exception context")
            else:
                raise Fail(f"generation Git {scenario} unexpectedly accepted")

        for scenario in ("positive", "non-ancestor", "error", "timeout", "os-error"):
            def fake_ancestry(args, **kwargs):
                require(args == ["git", "merge-base", "--is-ancestor", "a" * 40, "HEAD"]
                        and kwargs.get("cwd") == ROOT
                        and kwargs.get("stdout") == subprocess.DEVNULL
                        and kwargs.get("stderr") == subprocess.DEVNULL
                        and kwargs.get("timeout") == writer.SOURCE_GIT_TIMEOUT
                        and kwargs.get("check") is False,
                        "generation ancestry Git privacy/timeout drift")
                if scenario == "timeout":
                    raise subprocess.TimeoutExpired(args, writer.SOURCE_GIT_TIMEOUT)
                if scenario == "os-error":
                    raise OSError(private_canary)
                return subprocess.CompletedProcess(args, {
                    "positive": 0, "non-ancestor": 1, "error": 128
                }[scenario])
            writer.subprocess.run = fake_ancestry
            if scenario == "positive":
                writer.require_source_commit_ancestor("a" * 40)
                continue
            expected = ("sourceCommitSha must be an ancestor of current HEAD"
                        if scenario == "non-ancestor"
                        else "cannot verify sourceCommitSha ancestry")
            try:
                writer.require_source_commit_ancestor("a" * 40)
            except writer.Fail as exc:
                require(str(exc) == expected and private_canary not in str(exc),
                        f"generation ancestry {scenario} exposed private diagnostics")
                if scenario in ("timeout", "os-error"):
                    require(exc.__suppress_context__,
                            f"generation ancestry {scenario} leaked exception context")
            else:
                raise Fail(f"generation ancestry {scenario} unexpectedly accepted")
    finally:
        writer.subprocess.run = original_run
    print("PASS reject: generation Git and ancestry timeouts, oversized output and private failures")


def main() -> int:
    workspace_before = git("status", "--porcelain")
    refs_before = git("for-each-ref", "--format=%(refname) %(objectname)", "refs/heads")
    writer = load_writer()
    prove_bounded_writer_git_authority(writer)
    head = git("rev-parse", "HEAD")
    writer.require_source_commit_ancestor(head)
    print("PASS lineage authority: current HEAD is accepted")

    side_commit = make_side_commit()
    require(side_commit != head, "side commit unexpectedly equals HEAD")
    try:
        writer.require_source_commit_ancestor(side_commit)
    except writer.Fail:
        print("PASS lineage authority: existing non-ancestor commit rejected")
    else:
        raise Fail("non-ancestor sourceCommitSha was accepted")

    class LineageSentinel(RuntimeError):
        pass

    original = writer.require_source_commit_ancestor
    writer.require_source_commit_ancestor = lambda source_commit: (_ for _ in ()).throw(LineageSentinel(source_commit))
    try:
        try:
            writer.validate_record(minimal_record(head))
        except LineageSentinel:
            print("PASS integration: validate_record enforces source ancestry before evidence admission")
        except writer.Fail as exc:
            raise Fail(f"validate_record bypassed source ancestry hook: {exc}") from exc
        else:
            raise Fail("validate_record did not invoke source ancestry authority")
    finally:
        writer.require_source_commit_ancestor = original

    require(git("status", "--porcelain") == workspace_before, "negative suite changed preexisting workspace state")
    require(
        git("for-each-ref", "--format=%(refname) %(objectname)", "refs/heads") == refs_before,
        "negative suite mutated branch refs",
    )
    print("Memory OS environment generation lineage negative suite PASS")
    print("preexisting workspace state preserved: true")
    print("git refs mutated: false")
    print("production generation created: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT GENERATION LINEAGE NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)