#!/usr/bin/env python3
"""Prove generation records and referenced evidence remain byte-bound to sourceCommitSha."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"
WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
ENVIRONMENT_RECORD_FIXTURE = ROOT / "scripts/memory_os_environment_generation_eligibility.py"
SOURCE_BINDING_RULE = "allNonNullEnvironmentEvidenceRefsMustMatchSourceCommitSha"
ENVIRONMENT_RECORD_BINDING_RULE = "environmentRecordMustMatchSourceCommitSha"
EVIDENCE_CASES: tuple[tuple[str, Path], ...] = (
    ("postgresql.restoreEvidenceRef", ROOT / "README.md"),
    ("objectStorage.restoreEvidenceRef", ROOT / "SECURITY.md"),
    ("network.latencyProfileRef", ROOT / "services/import-api/README.md"),
    ("network.failureInjectionRef", ROOT / "scripts/validate-memory-os-operability.py"),
    ("identityAndSecrets.credentialScopeRef", ROOT / "scripts/validate-memory-os-production-equivalent-environment-record.py"),
    ("backupRestore.evidenceRef", ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"),
    ("materialDeltas[0].independentReviewRef", ROOT / ".github/workflows/operability-contracts.yml"),
    ("evidenceBoundary.independentReviewRef", ROOT / "contracts/operations/production-equivalent-environment-generation-record.v1.schema.json"),
)


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


def load_contract() -> dict[str, Any]:
    try:
        value = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load generation contract: {exc}") from exc
    require(isinstance(value, dict), "generation contract root must be object")
    return value


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
    raise Fail(f"{name}: source-bound authority drift unexpectedly accepted")


def evidence_env(refs: tuple[str, ...]) -> dict[str, Any]:
    require(len(refs) == len(EVIDENCE_CASES), "source-binding evidence fixture count drift")
    return {
        "postgresql": {"restoreEvidenceRef": refs[0]},
        "objectStorage": {"restoreEvidenceRef": refs[1]},
        "network": {"latencyProfileRef": refs[2], "failureInjectionRef": refs[3]},
        "identityAndSecrets": {"credentialScopeRef": refs[4]},
        "backupRestore": {"evidenceRef": refs[5]},
        "materialDeltas": [{"independentReviewRef": refs[6]}],
        "evidenceBoundary": {"independentReviewRef": refs[7]},
    }


def run_in_isolated_worktree() -> int:
    """Keep destructive source-binding fixtures out of the canonical checkout."""
    protected = (
        CONTRACT,
        WRITER,
        ENVIRONMENT_RECORD_FIXTURE,
        ROOT / "contracts/operations/production-operability-status.json",
        ROOT / "docs/operations/AUTONOMOUS-OPS-LEARNING.md",
        *[path for _, path in EVIDENCE_CASES],
    )
    snapshots = {path: (path.read_bytes(), path.stat().st_mode & 0o7777) for path in set(protected)}

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(ROOT), *args],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )

    head = git("rev-parse", "HEAD")
    require(head.returncode == 0 and len(head.stdout.strip()) == 40, "cannot resolve canonical source HEAD")
    status = git("status", "--porcelain")
    require(status.returncode == 0, "cannot inspect canonical source worktree")
    require(not status.stdout.strip(), "source-binding negative requires clean canonical source worktree")

    with tempfile.TemporaryDirectory(prefix="memory-os-generation-source-binding-worktree-") as tmp:
        checkout = Path(tmp) / "checkout"
        added = False
        try:
            result = git("worktree", "add", "--detach", "--quiet", str(checkout), head.stdout.strip())
            require(result.returncode == 0, f"cannot create detached negative checkout: {result.stderr.strip()}")
            added = True
            isolated_script = checkout / "scripts" / Path(__file__).name
            require(isolated_script.is_file(), "detached negative script missing")
            result = subprocess.run(
                [sys.executable, str(isolated_script), "--isolated"],
                cwd=checkout, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=False,
            )
            print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, end="", file=sys.stderr)
            require(result.returncode == 0, f"isolated source-binding negative failed: exit={result.returncode}")
        finally:
            if added:
                removal = git("worktree", "remove", "--force", str(checkout))
                require(removal.returncode == 0, f"cannot remove detached negative checkout: {removal.stderr.strip()}")

    after_head = git("rev-parse", "HEAD")
    after_status = git("status", "--porcelain")
    require(after_head.returncode == 0 and after_head.stdout == head.stdout, "canonical source HEAD drift")
    require(after_status.returncode == 0 and after_status.stdout == status.stdout, "canonical source worktree drift")
    for path, (payload, mode) in snapshots.items():
        require(path.read_bytes() == payload, f"canonical authority bytes drift: {path}")
        require((path.stat().st_mode & 0o7777) == mode, f"canonical authority mode drift: {path}")
    print("PASS isolation: detached negative checkout removed; canonical source bytes, modes, HEAD and worktree unchanged")
    return 0


def prove_bounded_digest_reader(writer) -> None:
    """Exercise the real generation environment-record digest reader in isolation."""
    with tempfile.TemporaryDirectory(prefix="memory-os-generation-digest-") as tmp:
        parent = Path(tmp)
        source = parent / "environment-record.json"
        payload = b'{"sentinel":"bounded"}\n'
        source.write_bytes(payload)
        require(writer.sha256(source) == hashlib.sha256(payload).hexdigest(),
                "generation bounded digest positive control failed")
        source.write_bytes(b"x" * (writer.MAX_SOURCE_BYTES + 1))
        try:
            writer.sha256(source)
        except writer.Fail as exc:
            require(str(exc) == "environmentRecordRef source file size limit exceeded",
                    "oversized generation digest wrong rejection class")
        else:
            raise Fail("oversized generation digest accepted")
        source.write_bytes(payload)

        external = parent / "external-canary.json"
        external.write_bytes(b"PRIVATE_GENERATION_DIGEST_CANARY")
        alias = parent / "source-alias.json"
        alias.symlink_to(external)
        try:
            writer.sha256(alias)
        except writer.Fail as exc:
            require(str(exc) == "environmentRecordRef cannot be read for immutable source binding"
                    and exc.__suppress_context__,
                    "generation digest symlink leaked private diagnostics")
        else:
            raise Fail("generation digest followed symlink")
        require(external.read_bytes() == b"PRIVATE_GENERATION_DIGEST_CANARY",
                "generation digest mutated external canary")

        fifo = parent / "source-fifo.json"
        os.mkfifo(fifo)
        for unsafe in (fifo, parent):
            try:
                writer.sha256(unsafe)
            except writer.Fail as exc:
                require(str(exc) == "environmentRecordRef source is not a regular file",
                        "generation digest special file wrong rejection class")
            else:
                raise Fail("generation digest accepted special file")

        original_fdopen = writer.os.fdopen
        opened: list[int] = []

        def reject_fdopen(fd, *_args, **_kwargs):
            opened.append(fd)
            raise OSError("PRIVATE_GENERATION_DIGEST_FDOPEN_CANARY")

        writer.os.fdopen = reject_fdopen
        try:
            try:
                writer.sha256(source)
            except writer.Fail as exc:
                require(str(exc) == "environmentRecordRef cannot be read for immutable source binding"
                        and exc.__suppress_context__,
                        "generation digest fdopen failure leaked private diagnostics")
            else:
                raise Fail("generation digest fdopen failure unexpectedly accepted")
        finally:
            writer.os.fdopen = original_fdopen
        require(len(opened) == 1, "generation digest fdopen negative not reached")
        for fd in opened:
            try:
                os.fstat(fd)
            except OSError:
                pass
            else:
                raise Fail("generation digest fdopen failure leaked descriptor")
        require(source.read_bytes() == payload,
                "generation digest reader modified source bytes")
    print("PASS reject: bounded generation digest refuses oversized/special sources and closes failed descriptors")


def prove_bounded_source_binding(writer, source_commit: str) -> None:
    """Exercise bounded immutable Git blobs with real writer and private faults."""
    path = ENVIRONMENT_RECORD_FIXTURE
    original = path.read_bytes()
    field = "environmentRecordRef"
    try:
        path.write_bytes(b"x" * (writer.MAX_SOURCE_BYTES + 1))
        try:
            writer.require_repo_file_bound_to_source(source_commit, path, field)
        except writer.Fail as exc:
            require(str(exc) == f"{field} source file size limit exceeded",
                    "oversized environment generation source wrong rejection class")
        else:
            raise Fail("oversized environment generation source accepted")
    finally:
        path.write_bytes(original)

    original_run = writer.subprocess.run
    private_canary = "PRIVATE_GENERATION_SOURCE_GIT_CANARY"
    source_ref = f"{source_commit}:{path.relative_to(ROOT).as_posix()}"
    try:
        for scenario in ("positive", "timeout", "os-error", "invalid-size",
                         "oversized-blob", "length-mismatch", "missing-blob"):
            calls: list[str] = []

            def fake_git(args, **kwargs):
                require(kwargs.get("cwd") == ROOT
                        and kwargs.get("stdout") == subprocess.PIPE
                        and kwargs.get("stderr") == subprocess.DEVNULL
                        and kwargs.get("timeout") == writer.SOURCE_GIT_TIMEOUT
                        and kwargs.get("check") is False,
                        "generation source Git timeout/privacy controls drift")
                require(args in (["git", "cat-file", "-s", source_ref],
                                 ["git", "show", source_ref]),
                        "generation source Git immutable ref drift")
                calls.append(args[1])
                if scenario == "timeout":
                    raise subprocess.TimeoutExpired(args, writer.SOURCE_GIT_TIMEOUT)
                if scenario == "os-error":
                    raise OSError(private_canary)
                if args[1] == "cat-file":
                    size = {
                        "invalid-size": b"not-a-number\n",
                        "oversized-blob": str(writer.MAX_SOURCE_BYTES + 1).encode() + b"\n",
                        "length-mismatch": b"2\n",
                    }.get(scenario, str(len(original)).encode() + b"\n")
                    return subprocess.CompletedProcess(args, 0, stdout=size)
                if scenario == "missing-blob":
                    return subprocess.CompletedProcess(args, 1, stdout=b"")
                if scenario == "length-mismatch":
                    return subprocess.CompletedProcess(args, 0, stdout=b"abc")
                return subprocess.CompletedProcess(args, 0, stdout=original)

            writer.subprocess.run = fake_git
            if scenario == "positive":
                writer.require_repo_file_bound_to_source(source_commit, path, field)
                require(calls == ["cat-file", "show"], "generation source positive Git binding incomplete")
                continue
            expected = {
                "timeout": f"{field} evidence missing from sourceCommitSha",
                "os-error": f"{field} evidence missing from sourceCommitSha",
                "invalid-size": f"{field} source blob size invalid",
                "oversized-blob": f"{field} source blob size limit exceeded",
                "length-mismatch": f"{field} source blob length mismatch",
                "missing-blob": f"{field} evidence missing from sourceCommitSha",
            }[scenario]
            try:
                writer.require_repo_file_bound_to_source(source_commit, path, field)
            except writer.Fail as exc:
                require(str(exc) == expected and private_canary not in str(exc),
                        f"generation source {scenario} leaked private diagnostics")
                if scenario in ("timeout", "os-error"):
                    require(exc.__suppress_context__,
                            f"generation source {scenario} leaked exception context")
            else:
                raise Fail(f"generation source {scenario} unexpectedly accepted")
            if scenario in ("invalid-size", "oversized-blob"):
                require(calls == ["cat-file"], f"generation source {scenario} fetched unbounded blob")
    finally:
        writer.subprocess.run = original_run
    require(path.read_bytes() == original,
            "bounded generation source negatives changed fixture bytes")
    print("PASS reject: bounded generation source Git timeout, size, length and private failures")


def main() -> int:
    require(
        CONTRACT.is_file() and WRITER.is_file() and ENVIRONMENT_RECORD_FIXTURE.is_file(),
        "generation source-binding authority fixture missing",
    )
    require(all(path.is_file() for _, path in EVIDENCE_CASES), "generation source-binding evidence fixture missing")
    contract = load_contract()
    bindings = contract.get("bindingRules")
    require(isinstance(bindings, dict), "generation bindingRules required")
    require(bindings.get(SOURCE_BINDING_RULE) is True, f"generation contract must require {SOURCE_BINDING_RULE}")
    require(
        bindings.get(ENVIRONMENT_RECORD_BINDING_RULE) is True,
        f"generation contract must require {ENVIRONMENT_RECORD_BINDING_RULE}",
    )

    writer = load_writer()
    source = head_sha()
    prove_bounded_digest_reader(writer)
    prove_bounded_source_binding(writer, source)
    refs = tuple(path.relative_to(ROOT).as_posix() for _, path in EVIDENCE_CASES)
    require(len(set(refs)) == len(refs), "source-binding negative suite requires distinct evidence refs")
    env = evidence_env(refs)

    writer.require_repo_file_bound_to_source(source, ENVIRONMENT_RECORD_FIXTURE, "environmentRecordRef")
    print("PASS accept: unchanged environment record fixture matches sourceCommitSha")
    environment_original = ENVIRONMENT_RECORD_FIXTURE.read_bytes()
    try:
        ENVIRONMENT_RECORD_FIXTURE.write_bytes(environment_original + b"\nsource-binding-negative-environment-record-mutation\n")
        expect_rejected(
            writer,
            "environmentRecordRef changed after sourceCommitSha",
            lambda: writer.require_repo_file_bound_to_source(source, ENVIRONMENT_RECORD_FIXTURE, "environmentRecordRef"),
        )
    finally:
        ENVIRONMENT_RECORD_FIXTURE.write_bytes(environment_original)
    require(
        ENVIRONMENT_RECORD_FIXTURE.read_bytes() == environment_original,
        "source-binding negative suite failed to restore environment record fixture",
    )

    with tempfile.TemporaryDirectory(prefix=".source-binding-untracked-", dir=ROOT) as tmp:
        untracked = Path(tmp) / "environment-record-created-after-source.json"
        untracked.write_text("{}\n", encoding="utf-8")
        expect_rejected(
            writer,
            "environmentRecordRef did not exist at sourceCommitSha",
            lambda: writer.require_repo_file_bound_to_source(source, untracked, "environmentRecordRef"),
        )
    print("PASS reject: post-source untracked environment record cannot acquire historical authority")

    writer.require_environment_evidence_bound_to_source(source, env)
    print("PASS accept: all unchanged repository evidence fields match sourceCommitSha")

    with tempfile.TemporaryDirectory(prefix=".source-binding-untracked-evidence-", dir=ROOT) as tmp:
        for index, (field, _) in enumerate(EVIDENCE_CASES):
            untracked_evidence = Path(tmp) / f"evidence-created-after-source-{index}.json"
            untracked_evidence.write_text("{}\n", encoding="utf-8")
            post_source_refs = list(refs)
            post_source_refs[index] = untracked_evidence.relative_to(ROOT).as_posix()
            post_source_env = evidence_env(tuple(post_source_refs))
            expect_rejected(
                writer,
                f"{field} did not exist at sourceCommitSha",
                lambda env_case=post_source_env: writer.require_environment_evidence_bound_to_source(source, env_case),
            )
    print(f"PASS reject: post-source untracked evidence cannot acquire historical authority across {len(EVIDENCE_CASES)} fields")

    originals = {path: path.read_bytes() for _, path in EVIDENCE_CASES}
    for field, path in EVIDENCE_CASES:
        original = originals[path]
        try:
            path.write_bytes(original + b"\nsource-binding-negative-mutation\n")
            expect_rejected(
                writer,
                f"{field} changed after sourceCommitSha",
                lambda: writer.require_environment_evidence_bound_to_source(source, env),
            )
        finally:
            path.write_bytes(original)
        require(path.read_bytes() == original, f"source-binding negative suite failed to restore fixture: {field}")

    require(all(path.read_bytes() == original for path, original in originals.items()), "source-binding negative suite left a canonical evidence fixture mutated")
    print("Environment generation source-binding negative suite PASS")
    print("environment record independently source-bound: true")
    print(f"independently source-bound evidence fields tested: {len(EVIDENCE_CASES)}")
    print("post-source environment record accepted as historical authority: false")
    print(f"post-source evidence fields accepted as historical authority: 0/{len(EVIDENCE_CASES)}")
    print("source-binding fixtures are immutable validator/source files, not reconciled derived authority: true")
    print("source-bound environment record contract rule required: true")
    print("source-bound evidence contract rule required: true")
    print("source-bound authority mutation accepted: false")
    print("canonical evidence left mutated: false")
    print("generation created: false")
    print("production evidence: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        if len(sys.argv) == 1:
            raise SystemExit(run_in_isolated_worktree())
        require(
            sys.argv == [sys.argv[0], "--isolated"] and (ROOT / ".git").is_file(),
            "destructive source-binding negatives require a detached Git worktree",
        )
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT GENERATION SOURCE-BINDING NEGATIVE FAILED: {exc}")
        raise SystemExit(1)