#!/usr/bin/env python3
"""Fail-closed chronology validation for human backup/restore promotion reviews.

Human Recovery Owner, Security, and Operability review evidence must be created strictly
after the source commit of the final recovery evidence it reviews. Review timestamps
must also not claim a time later than the commit that first introduced the review
payload. The committed review payload must remain byte-identical to its creation blob
so review evidence cannot be rewritten in place after admission. This validator is
read-only and cannot create promotion authority, production evidence, credentials,
recovery objectives, or traffic.
"""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch
import re
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
TRUSTED_GIT = "/usr/bin/git"
MAX_JSON_BYTES = 1024 * 1024
CONTRACT_REL = Path("contracts/operations/backup-restore-promotion-review-contract.v1.json")
PROMOTION_REGISTRY_REL = Path("contracts/operations/backup-restore-promotion-review-registry.v1.json")
GENERATION_REGISTRY_REL = Path("contracts/operations/backup-restore-generation-evidence-registry.v1.json")
SELF_REL = Path("scripts/validate-memory-os-backup-restore-promotion-review-source-order.py")
CONTRACT = ROOT / CONTRACT_REL
PROMOTION_REGISTRY = ROOT / PROMOTION_REGISTRY_REL
GENERATION_REGISTRY = ROOT / GENERATION_REGISTRY_REL
EVIDENCE_ROOT = Path("docs/evidence/backup-restore")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
REVIEW_REFS = (
    "recoveryOwnerReviewRef",
    "securityReviewRef",
    "operabilityReviewRef",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def read_bounded_bytes(path: Path, field: str) -> bytes:
    require(isinstance(path, Path), f"{field} file unsafe")
    require(type(getattr(os, "O_NOFOLLOW", None)) is int and os.O_NOFOLLOW > 0,
            f"{field} file unsafe")
    try:
        preflight = path.lstat()
    except (OSError, ValueError):
        raise Fail(f"{field} file unsafe") from None
    require(stat.S_ISREG(preflight.st_mode) and preflight.st_nlink == 1,
            f"{field} file unsafe")
    require(preflight.st_size >= 0, f"{field} file unsafe")
    require(preflight.st_size <= MAX_JSON_BYTES,
            f"{field} bytes invalid or oversized")
    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except (OSError, ValueError):
        raise Fail(f"{field} unreadable") from None
    if type(fd) is not int or fd < 0:
        raise Fail(f"{field} unreadable")
    try:
        opened = os.fstat(fd)
        identity = lambda st: (st.st_dev, st.st_ino, st.st_size,
                               st.st_mtime_ns, st.st_ctime_ns)
        require(stat.S_ISREG(opened.st_mode) and opened.st_nlink == 1
                and identity(opened) == identity(preflight),
                f"{field} file unsafe")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            require(type(stream.fileno()) is int and stream.fileno() == fd,
                    f"{field} unreadable")
            raw = stream.read(MAX_JSON_BYTES + 1)
            require(type(stream.fileno()) is int and stream.fileno() == fd,
                    f"{field} unreadable")
        after = os.fstat(fd)
        live = path.lstat()
        require(stat.S_ISREG(after.st_mode) and stat.S_ISREG(live.st_mode)
                and after.st_nlink == 1 and live.st_nlink == 1
                and identity(opened) == identity(after) == identity(live),
                f"{field} file unsafe")
    except (OSError, ValueError, TypeError, AttributeError):
        raise Fail(f"{field} unreadable") from None
    finally:
        try:
            os.close(fd)
        except OSError:
            raise Fail(f"{field} unreadable") from None
    require(type(raw) is bytes and len(raw) <= MAX_JSON_BYTES
            and len(raw) == opened.st_size,
            f"{field} bytes invalid or oversized")
    return raw


def load_json(path: Path, field: str) -> dict[str, Any]:
    try:
        value = json.loads(read_bounded_bytes(path, field).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        raise Fail(f"{field} unreadable or invalid JSON") from None
    require(isinstance(value, dict), f"{field} root must be object")
    return value


def validate_contract(contract: dict[str, Any]) -> None:
    require(
        contract.get("schemaVersion") == "memory-os-backup-restore-promotion-review-contract.v1",
        "promotion review contract schema drift",
    )
    require(contract.get("sourceOrderValidator") == SELF_REL.as_posix(), "promotion review source-order validator authority drift")
    rules = contract.get("rules")
    require(isinstance(rules, dict), "promotion review contract rules missing")
    require(
        rules.get("humanReviewMustBeCreatedStrictlyAfterRecoverySourceCommit") is True,
        "promotion review contract must require post-source human reviews",
    )
    require(
        rules.get("humanReviewPayloadMustRemainAppendOnlyAfterFirstCommit") is True,
        "promotion review contract must require immutable committed human review payloads",
    )


def canonical_review_ref(value: Any, field: str) -> tuple[str, Path]:
    require(isinstance(value, str) and value, f"{field} required")
    relative = Path(value)
    require(
        not relative.is_absolute() and ".." not in relative.parts and relative.as_posix() == value,
        f"{field} must be canonical repository-relative path",
    )
    require(
        relative.parts[: len(EVIDENCE_ROOT.parts)] == EVIDENCE_ROOT.parts
        and len(relative.parts) > len(EVIDENCE_ROOT.parts),
        f"{field} must remain inside {EVIDENCE_ROOT.as_posix()}/",
    )
    path = ROOT / relative
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        resolved == relative and path.is_file() and not path.is_symlink(),
        f"{field} must resolve to canonical repository file",
    )
    return value, path


def trusted_git_env() -> dict[str, str]:
    """Do not inherit Git or dynamic-loader overrides for human review chronology."""
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("GIT_", "LD_", "DYLD_"))}
    env.update(GIT_NO_REPLACE_OBJECTS="1", GIT_CONFIG_NOSYSTEM="1",
               GIT_CONFIG_GLOBAL=os.devnull)
    return env


def git_output(args: list[str], field: str) -> str:
    try:
        completed = subprocess.run(
            [TRUSTED_GIT, *args],
            cwd=ROOT, env=trusted_git_env(), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=False, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Fail(f"cannot inspect {field}") from None
    require(type(completed.returncode) is int and completed.returncode == 0,
            f"cannot inspect {field}")
    require(type(completed.stdout) is str and len(completed.stdout) <= 256,
            f"cannot inspect {field} output")
    return completed.stdout.strip()


def first_commit_for_path(ref: str, field: str) -> str:
    output = git_output(["log", "--diff-filter=A", "--max-count=2", "--follow", "--format=%H", "--", ref], field)
    commits = [line.strip() for line in output.splitlines() if line.strip()]
    require(
        len(commits) == 1 and SHA40.fullmatch(commits[0]) is not None,
        f"{field} must have exactly one committed creation point",
    )
    return commits[0]


def creation_blob(commit_sha: str, ref: str, field: str) -> bytes:
    require(isinstance(commit_sha, str) and SHA40.fullmatch(commit_sha) is not None,
            f"{field} creation commit invalid")
    object_ref = f"{commit_sha}:{ref}"
    try:
        size_result = subprocess.run(
            [TRUSTED_GIT, "cat-file", "-s", object_ref],
            cwd=ROOT, env=trusted_git_env(), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=False, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Fail(f"cannot inspect {field} creation blob") from None
    require(type(size_result.returncode) is int and size_result.returncode == 0
            and type(size_result.stdout) is str
            and re.fullmatch(r"[0-9]{1,7}\n?", size_result.stdout) is not None,
            f"cannot inspect {field} creation blob")
    expected_bytes = int(size_result.stdout.strip())
    require(0 < expected_bytes <= MAX_JSON_BYTES,
            f"{field} creation blob size limit exceeded")
    try:
        completed = subprocess.run(
            [TRUSTED_GIT, "show", object_ref],
            cwd=ROOT, env=trusted_git_env(),
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=False, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Fail(f"cannot inspect {field} creation blob") from None
    require(type(completed.returncode) is int and completed.returncode == 0
            and type(completed.stdout) is bytes,
            f"cannot inspect {field} creation blob")
    require(len(completed.stdout) == expected_bytes,
            f"{field} creation blob size mismatch")
    return completed.stdout


def require_creation_blob_immutable(current: bytes, created: bytes, field: str) -> None:
    require(current == created, f"{field} review evidence changed after its creation commit")


def commit_exists(commit_sha: str, field: str) -> None:
    try:
        completed = subprocess.run(
            [TRUSTED_GIT, "cat-file", "-e", f"{commit_sha}^{{commit}}"],
            cwd=ROOT, env=trusted_git_env(),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Fail(f"{field} sourceCommitSha must resolve to a commit") from None
    require(type(completed.returncode) is int and completed.returncode == 0,
            f"{field} sourceCommitSha must resolve to a commit")


def commit_time(commit_sha: str, field: str) -> datetime:
    value = git_output(["show", "-s", "--format=%cI", commit_sha], field)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise Fail(f"cannot parse {field} commit timestamp") from exc
    require(parsed.tzinfo is not None, f"{field} commit timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def review_time(value: Any, field: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), f"{field}.reviewedAt must be UTC RFC3339 ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise Fail(f"{field}.reviewedAt invalid") from exc
    require(parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0, f"{field}.reviewedAt must be UTC")
    return parsed.astimezone(timezone.utc)


def is_ancestor(ancestor: str, descendant: str) -> bool:
    try:
        completed = subprocess.run(
            [TRUSTED_GIT, "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=ROOT, env=trusted_git_env(),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Fail("cannot compare promotion review/source commit ancestry") from None
    if type(completed.returncode) is int and completed.returncode == 0:
        return True
    if type(completed.returncode) is int and completed.returncode == 1:
        return False
    raise Fail("cannot compare promotion review/source commit ancestry")


def require_source_precedes_review(
    source_commit: str,
    review_commit: str,
    field: str,
    ancestor_check: Callable[[str, str], bool] = is_ancestor,
) -> None:
    require(SHA40.fullmatch(source_commit) is not None, f"{field} sourceCommitSha invalid")
    require(SHA40.fullmatch(review_commit) is not None, f"{field} review commit invalid")
    require(source_commit != review_commit, f"{field} human promotion review must be created strictly after recovery sourceCommitSha")
    require(
        ancestor_check(source_commit, review_commit),
        f"{field} human promotion review predates or is not descended from recovery sourceCommitSha",
    )


def require_review_time_window(
    reviewed_at: datetime,
    source_time: datetime,
    review_commit_time: datetime,
    field: str,
) -> None:
    require(source_time <= reviewed_at, f"{field}.reviewedAt predates recovery sourceCommitSha")
    require(reviewed_at <= review_commit_time, f"{field}.reviewedAt is later than committed review evidence")


def generation_by_id(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    require(
        registry.get("schemaVersion") == "memory-os-backup-restore-generation-evidence-registry.v1",
        "generation evidence registry schema drift",
    )
    require(registry.get("appendOnly") is True, "generation evidence registry must remain append-only")
    require(
        registry.get("productionEvidence") is False and registry.get("productionReady") is False,
        "generation evidence registry production boundary drift",
    )
    rows = registry.get("records")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "generation evidence registry records invalid")
    mapping: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        evidence_id = row.get("evidenceId")
        require(isinstance(evidence_id, str) and evidence_id and evidence_id not in mapping, f"generation records[{index}].evidenceId invalid/duplicate")
        mapping[evidence_id] = row
    return mapping


def validate_row(row: dict[str, Any], index: int, generations: dict[str, dict[str, Any]]) -> None:
    evidence_id = row.get("recoveryEvidenceId")
    require(isinstance(evidence_id, str) and evidence_id in generations, f"records[{index}].recoveryEvidenceId not registered")
    generation = generations[evidence_id]
    source_commit = generation.get("sourceCommitSha")
    require(isinstance(source_commit, str) and SHA40.fullmatch(source_commit) is not None, f"records[{index}] recovery sourceCommitSha invalid")
    commit_exists(source_commit, f"records[{index}]")
    source_time = commit_time(source_commit, f"records[{index}].sourceCommitSha")

    for name in REVIEW_REFS:
        field = f"records[{index}].{name}"
        ref, path = canonical_review_ref(row.get(name), field)
        review_commit = first_commit_for_path(ref, field)
        require_source_precedes_review(source_commit, review_commit, field)
        current_blob = read_bounded_bytes(path, field)
        require_creation_blob_immutable(current_blob, creation_blob(review_commit, ref, field), field)
        payload = load_json(path, field)
        require(payload.get("recoveryEvidenceId") == evidence_id, f"{field} recoveryEvidenceId binding mismatch")
        reviewed_at = review_time(payload.get("reviewedAt"), field)
        require_review_time_window(reviewed_at, source_time, commit_time(review_commit, field), field)


def git_transport_self_test() -> None:
    ref = "docs/evidence/backup-restore/promotion/synthetic-git-path-decoy.json"
    with tempfile.TemporaryDirectory(prefix="promotion-source-order-git-decoy-") as temp:
        fake = Path(temp) / "git"
        fake.write_text("#!/bin/sh\necho " + "a" * 40 + "\n", encoding="utf-8")
        fake.chmod(0o755)
        with patch.dict(os.environ, {"PATH": temp + os.pathsep + os.environ.get("PATH", "")}):
            decoy = subprocess.run(
                ["git", "log", "--diff-filter=A", "--follow",
                 "--format=%H", "--", ref],
                cwd=ROOT, capture_output=True, text=True, check=False, timeout=10,
            )
            require(decoy.returncode == 0 and decoy.stdout == "a" * 40 + "\n",
                    "promotion source-order Git PATH decoy positive control ineffective")
            try:
                first_commit_for_path(ref, "self-test")
            except Fail as exc:
                require(str(exc) == "self-test must have exactly one committed creation point",
                        "promotion source-order Git PATH decoy rejected for unrelated reason")
            else:
                raise Fail("promotion source-order Git PATH decoy admitted forged review")
    with patch.dict(os.environ, {
        "GIT_DIR": "/tmp/unreviewed-git-dir",
        "LD_PRELOAD": "/tmp/unreviewed-git-loader.so",
        "DYLD_INSERT_LIBRARIES": "/tmp/unreviewed-git-loader.dylib",
    }):
        with patch.object(subprocess, "run", return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout="a" * 40 + "\n", stderr="",
        )) as observed:
            require(first_commit_for_path(ref, "self-test") == "a" * 40,
                    "promotion source-order Git sanitized positive control invalid")
            args, kwargs = observed.call_args
            env = kwargs.get("env")
            require(args[0][0] == TRUSTED_GIT == "/usr/bin/git"
                    and type(env) is dict
                    and all(key not in env for key in (
                        "GIT_DIR", "LD_PRELOAD", "DYLD_INSERT_LIBRARIES"
                    ))
                    and env.get("GIT_NO_REPLACE_OBJECTS") == "1"
                    and env.get("GIT_CONFIG_GLOBAL") == os.devnull,
                    "promotion source-order Git executable/environment authority drift")


def git_output_transport_self_test() -> None:
    ref = "docs/evidence/backup-restore/promotion/synthetic-transport.json"
    field = "self-test"
    marker = "PRIVATE_PROMOTION_GIT_DIAGNOSTIC_DO_NOT_LOG"
    state = {"stdout": "a" * 40 + "\n", "returncode": 0, "error": None}
    calls = []
    def fake_git(args, **kwargs):
        require(args == [TRUSTED_GIT, "log", "--diff-filter=A",
                         "--max-count=2", "--follow", "--format=%H", "--", ref],
                "promotion Git history bounded command drift")
        require(kwargs.get("cwd") == ROOT and kwargs.get("text") is True
                and kwargs.get("stdout") is subprocess.PIPE
                and kwargs.get("stderr") is subprocess.DEVNULL
                and kwargs.get("check") is False and kwargs.get("timeout") == 20,
                "promotion Git history private/timeout transport drift")
        env = kwargs.get("env")
        require(type(env) is dict and env.get("GIT_NO_REPLACE_OBJECTS") == "1"
                and env.get("GIT_CONFIG_GLOBAL") == os.devnull,
                "promotion Git history environment drift")
        calls.append(args)
        if state["error"] is not None:
            raise state["error"]
        return subprocess.CompletedProcess(
            args, state["returncode"], stdout=state["stdout"], stderr=marker
        )
    with patch.object(subprocess, "run", side_effect=fake_git):
        require(first_commit_for_path(ref, field) == "a" * 40,
                "promotion Git bounded history positive control invalid")
        cases = (
            ("two-commits", {"stdout": "a" * 40 + "\n" + "b" * 40 + "\n"},
             f"{field} must have exactly one committed creation point"),
            ("nonzero", {"returncode": 1}, f"cannot inspect {field}"),
            ("bool-exit", {"returncode": True}, f"cannot inspect {field}"),
            ("bytes-output", {"stdout": b"a" * 40}, f"cannot inspect {field} output"),
            ("oversized", {"stdout": "a" * 257}, f"cannot inspect {field} output"),
            ("timeout", {"error": subprocess.TimeoutExpired(
                [TRUSTED_GIT, "log"], 20, stderr=marker
            )}, f"cannot inspect {field}"),
            ("unavailable", {"error": OSError(marker)}, f"cannot inspect {field}"),
        )
        for label, changes, expected in cases:
            state.update({"stdout": "a" * 40 + "\n", "returncode": 0, "error": None})
            state.update(changes)
            try:
                first_commit_for_path(ref, field)
            except Fail as exc:
                require(str(exc) == expected and marker not in str(exc),
                        f"promotion Git history {label} wrong/private failure")
            else:
                raise Fail(f"promotion Git history {label} unexpectedly accepted")
        require(len(calls) == 8, "promotion Git history negative call count drift")


def commit_ancestry_transport_self_test() -> None:
    ancestor, descendant = "a" * 40, "b" * 40
    field = "self-test"
    marker = "PRIVATE_PROMOTION_COMMIT_DIAGNOSTIC_DO_NOT_LOG"
    state = {"returncode": 0, "error": None}
    calls = []
    def fake_git(args, **kwargs):
        require(args in (
            [TRUSTED_GIT, "cat-file", "-e", ancestor + "^{commit}"],
            [TRUSTED_GIT, "merge-base", "--is-ancestor", ancestor, descendant],
        ), "promotion commit/ancestry Git command drift")
        require(kwargs.get("cwd") == ROOT
                and kwargs.get("stdout") is subprocess.DEVNULL
                and kwargs.get("stderr") is subprocess.DEVNULL
                and kwargs.get("check") is False and kwargs.get("timeout") == 20,
                "promotion commit/ancestry Git privacy/timeout drift")
        env = kwargs.get("env")
        require(type(env) is dict and env.get("GIT_NO_REPLACE_OBJECTS") == "1"
                and env.get("GIT_CONFIG_GLOBAL") == os.devnull,
                "promotion commit/ancestry Git environment drift")
        calls.append(args)
        if state["error"] is not None:
            raise state["error"]
        return subprocess.CompletedProcess(
            args, state["returncode"], stdout=marker, stderr=marker
        )
    with patch.object(subprocess, "run", side_effect=fake_git):
        commit_exists(ancestor, field)
        require(is_ancestor(ancestor, descendant) is True,
                "promotion Git ancestor positive control invalid")
        state["returncode"] = 1
        require(is_ancestor(ancestor, descendant) is False,
                "promotion Git non-ancestor positive control invalid")
        cases = (
            ("commit-nonzero", {"returncode": 1},
             f"{field} sourceCommitSha must resolve to a commit"),
            ("commit-bool", {"returncode": True},
             f"{field} sourceCommitSha must resolve to a commit"),
            ("commit-timeout", {"error": subprocess.TimeoutExpired(
                [TRUSTED_GIT, "cat-file"], 20, stderr=marker
            )}, f"{field} sourceCommitSha must resolve to a commit"),
            ("commit-unavailable", {"error": OSError(marker)},
             f"{field} sourceCommitSha must resolve to a commit"),
            ("ancestor-other", {"returncode": 2},
             "cannot compare promotion review/source commit ancestry"),
            ("ancestor-bool", {"returncode": True},
             "cannot compare promotion review/source commit ancestry"),
            ("ancestor-timeout", {"error": subprocess.TimeoutExpired(
                [TRUSTED_GIT, "merge-base"], 20, stderr=marker
            )}, "cannot compare promotion review/source commit ancestry"),
            ("ancestor-unavailable", {"error": OSError(marker)},
             "cannot compare promotion review/source commit ancestry"),
        )
        for label, changes, expected in cases:
            state.update({"returncode": 0, "error": None})
            state.update(changes)
            try:
                if label.startswith("commit-"):
                    commit_exists(ancestor, field)
                else:
                    is_ancestor(ancestor, descendant)
            except Fail as exc:
                require(str(exc) == expected and marker not in str(exc),
                        f"promotion Git {label} wrong/private diagnostic")
            else:
                raise Fail(f"promotion Git {label} unexpectedly accepted")
        require(len(calls) == 11, "promotion commit/ancestry negative count drift")


def creation_blob_transport_self_test() -> None:
    field = "self-test"
    ref = "docs/evidence/backup-restore/promotion/synthetic-creation.json"
    object_ref = "a" * 40 + ":" + ref
    payload = b'{"reviewResult":"APPROVED"}\n'
    marker = "PRIVATE_PROMOTION_BLOB_DIAGNOSTIC_DO_NOT_LOG"
    state = {
        "size": str(len(payload)) + "\n", "size_exit": 0, "size_error": None,
        "show": payload, "show_exit": 0, "show_error": None,
    }
    calls = []
    def fake_git(args, **kwargs):
        phase = args[1]
        require(phase in ("cat-file", "show")
                and kwargs.get("cwd") == ROOT
                and kwargs.get("stdout") is subprocess.PIPE
                and kwargs.get("stderr") is subprocess.DEVNULL
                and kwargs.get("check") is False and kwargs.get("timeout") == 20,
                "promotion creation blob Git bounded/private transport drift")
        env = kwargs.get("env")
        require(type(env) is dict and env.get("GIT_NO_REPLACE_OBJECTS") == "1"
                and env.get("GIT_CONFIG_GLOBAL") == os.devnull,
                "promotion creation blob Git environment drift")
        calls.append(phase)
        if phase == "cat-file":
            require(args == [TRUSTED_GIT, "cat-file", "-s", object_ref]
                    and kwargs.get("text") is True,
                    "promotion creation blob size preflight command drift")
            if state["size_error"] is not None:
                raise state["size_error"]
            return subprocess.CompletedProcess(
                args, state["size_exit"], stdout=state["size"], stderr=marker
            )
        require(args == [TRUSTED_GIT, "show", object_ref]
                and kwargs.get("text") is None,
                "promotion creation blob byte read command drift")
        if state["show_error"] is not None:
            raise state["show_error"]
        return subprocess.CompletedProcess(
            args, state["show_exit"], stdout=state["show"], stderr=marker
        )
    with patch.object(subprocess, "run", side_effect=fake_git):
        require(creation_blob("a" * 40, ref, field) == payload,
                "promotion creation blob positive control invalid")
        cases = (
            ("zero", {"size": "0\n"}, f"{field} creation blob size limit exceeded", 1),
            ("oversized", {"size": str(MAX_JSON_BYTES + 1) + "\n"},
             f"{field} creation blob size limit exceeded", 1),
            ("malformed", {"size": marker}, f"cannot inspect {field} creation blob", 1),
            ("nonzero-size", {"size_exit": 1}, f"cannot inspect {field} creation blob", 1),
            ("bool-size", {"size_exit": True}, f"cannot inspect {field} creation blob", 1),
            ("timeout-size", {"size_error": subprocess.TimeoutExpired(
                [TRUSTED_GIT, "cat-file"], 20, stderr=marker
            )}, f"cannot inspect {field} creation blob", 1),
            ("unavailable-size", {"size_error": OSError(marker)},
             f"cannot inspect {field} creation blob", 1),
            ("mismatch", {"show": b"changed"}, f"{field} creation blob size mismatch", 2),
            ("nonbytes-show", {"show": marker}, f"cannot inspect {field} creation blob", 2),
            ("nonzero-show", {"show_exit": 1}, f"cannot inspect {field} creation blob", 2),
            ("timeout-show", {"show_error": subprocess.TimeoutExpired(
                [TRUSTED_GIT, "show"], 20, stderr=marker
            )}, f"cannot inspect {field} creation blob", 2),
            ("unavailable-show", {"show_error": OSError(marker)},
             f"cannot inspect {field} creation blob", 2),
        )
        for label, changes, expected, expected_calls in cases:
            state.update({
                "size": str(len(payload)) + "\n", "size_exit": 0, "size_error": None,
                "show": payload, "show_exit": 0, "show_error": None,
            })
            state.update(changes)
            before = len(calls)
            try:
                creation_blob("a" * 40, ref, field)
            except Fail as exc:
                require(str(exc) == expected and marker not in str(exc),
                        f"promotion creation blob {label} wrong/private diagnostic")
            else:
                raise Fail(f"promotion creation blob {label} unexpectedly accepted")
            require(len(calls) - before == expected_calls,
                    f"promotion creation blob {label} wrong Git phase")
        require(len(calls) == 19, "promotion creation blob negative count drift")


def bounded_review_bytes_self_test() -> None:
    field = "self-test"
    with tempfile.TemporaryDirectory(prefix="promotion-review-bytes-negative-") as temp:
        root = Path(temp)
        path = root / "review.json"
        positive = b'{"reviewResult":"APPROVED"}\n'
        path.write_bytes(positive)
        require(read_bounded_bytes(path, field) == positive,
                "promotion bounded review bytes positive invalid")
        require(load_json(path, field).get("reviewResult") == "APPROVED",
                "promotion bounded review JSON positive invalid")
        for label, fixture, expected, loader in (
            ("oversized", b"x" * (MAX_JSON_BYTES + 1),
             f"{field} bytes invalid or oversized", read_bounded_bytes),
            ("invalid-utf8", b"\xff",
             f"{field} unreadable or invalid JSON", load_json),
            ("invalid-json", b"{broken",
             f"{field} unreadable or invalid JSON", load_json),
        ):
            path.write_bytes(fixture)
            try:
                loader(path, field)
            except Fail as exc:
                require(str(exc) == expected,
                        f"promotion review {label} rejected at wrong boundary")
            else:
                raise Fail(f"promotion review {label} unexpectedly accepted")
            require(path.read_bytes() == fixture,
                    f"promotion review {label} mutated source fixture")
        path.write_bytes(positive)
        link = root / "linked.json"
        link.symlink_to(path)
        try:
            read_bounded_bytes(link, field)
        except Fail as exc:
            require(str(exc) == f"{field} file unsafe",
                    "promotion review symlink rejected at wrong boundary")
        else:
            raise Fail("promotion review symlink unexpectedly accepted")
        directory = root / "directory"
        directory.mkdir()
        try:
            read_bounded_bytes(directory, field)
        except Fail as exc:
            require(str(exc) == f"{field} file unsafe",
                    "promotion review directory rejected at wrong boundary")
        else:
            raise Fail("promotion review directory unexpectedly accepted")
        require(read_bounded_bytes(path, field) == positive
                and load_json(path, field).get("reviewResult") == "APPROVED",
                "promotion review bounded bytes recovery positive invalid")


def fd_identity_self_test() -> None:
    field = "self-test"
    positive = b'{"reviewResult":"APPROVED"}\n'
    with tempfile.TemporaryDirectory(prefix="promotion-fd-identity-negative-") as temp:
        root = Path(temp)
        path = root / "review.json"
        moved = root / "moved.json"
        alternate = root / "alternate.json"
        path.write_bytes(positive)
        alternate.write_bytes(b'{"reviewResult":"REJECTED"}\n')
        real_open = os.open
        def swap_before_open(target, flags, *args, **kwargs):
            require(Path(target) == path, "promotion FD swap targeted wrong path")
            path.rename(moved)
            path.symlink_to(alternate)
            return real_open(target, flags, *args, **kwargs)
        with patch.object(os, "open", side_effect=swap_before_open):
            try:
                read_bounded_bytes(path, field)
            except Fail as exc:
                require(str(exc) == f"{field} unreadable",
                        "promotion FD symlink swap rejected at wrong boundary")
            else:
                raise Fail("promotion FD symlink swap unexpectedly accepted")
        path.unlink()
        moved.rename(path)
        require(read_bounded_bytes(path, field) == positive,
                "promotion FD swap recovery positive invalid")
        hardlink = root / "hardlink.json"
        os.link(path, hardlink)
        try:
            read_bounded_bytes(path, field)
        except Fail as exc:
            require(str(exc) == f"{field} file unsafe",
                    "promotion FD hardlink rejected at wrong boundary")
        else:
            raise Fail("promotion FD hardlink unexpectedly accepted")
        hardlink.unlink()
        require(read_bounded_bytes(path, field) == positive,
                "promotion FD hardlink recovery positive invalid")


def self_test() -> None:
    fd_identity_self_test()
    bounded_review_bytes_self_test()
    creation_blob_transport_self_test()
    commit_ancestry_transport_self_test()
    git_output_transport_self_test()
    git_transport_self_test()
    source = "1" * 40
    review = "2" * 40
    require_source_precedes_review(source, review, "self-test", ancestor_check=lambda _a, _b: True)
    try:
        require_source_precedes_review(source, source, "self-test", ancestor_check=lambda _a, _b: True)
    except Fail as exc:
        require("strictly after" in str(exc), "self-test rejected same-commit promotion review at wrong boundary")
    else:
        raise Fail("self-test accepted human promotion review created in recovery source commit")
    try:
        require_source_precedes_review(source, review, "self-test", ancestor_check=lambda _a, _b: False)
    except Fail as exc:
        require("predates" in str(exc), "self-test rejected stale promotion review at wrong boundary")
    else:
        raise Fail("self-test accepted promotion review that predates recovery source commit")

    require_creation_blob_immutable(b"review-payload\n", b"review-payload\n", "self-test")
    try:
        require_creation_blob_immutable(b"rewritten-review\n", b"review-payload\n", "self-test")
    except Fail as exc:
        require("changed after its creation commit" in str(exc), "self-test rejected rewritten review at wrong boundary")
    else:
        raise Fail("self-test accepted promotion review evidence rewritten after creation")

    source_time = datetime(2026, 9, 12, 9, 0, 0, tzinfo=timezone.utc)
    review_time_ok = datetime(2026, 9, 12, 9, 5, 0, tzinfo=timezone.utc)
    commit_time_ok = datetime(2026, 9, 12, 9, 10, 0, tzinfo=timezone.utc)
    require_review_time_window(review_time_ok, source_time, commit_time_ok, "self-test")
    for invalid, label in (
        (datetime(2026, 9, 12, 8, 59, 59, tzinfo=timezone.utc), "predates recovery sourceCommitSha"),
        (datetime(2026, 9, 12, 9, 10, 1, tzinfo=timezone.utc), "later than committed review evidence"),
    ):
        try:
            require_review_time_window(invalid, source_time, commit_time_ok, "self-test")
        except Fail as exc:
            require(label in str(exc), f"self-test rejected promotion timestamp at wrong boundary: {exc}")
        else:
            raise Fail("self-test accepted promotion review timestamp outside recovery-source/review-commit window")

    for invalid in ("", "x" * 40, "1" * 39, "1" * 41):
        try:
            require_source_precedes_review(invalid, review, "self-test", ancestor_check=lambda _a, _b: True)
        except Fail:
            pass
        else:
            raise Fail("self-test accepted invalid recovery sourceCommitSha")
    print("PASS: promotion review chronology negative rejects same-commit/stale/non-descendant commits, rewritten creation blobs, malformed source SHAs, and out-of-window review timestamps")


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        self_test()
        return 0
    require(len(sys.argv) == 1, "usage: validate-memory-os-backup-restore-promotion-review-source-order.py [--self-test]")

    contract = load_json(CONTRACT, "promotion review contract")
    validate_contract(contract)
    promotion = load_json(PROMOTION_REGISTRY, "promotion review registry")
    generation = load_json(GENERATION_REGISTRY, "generation evidence registry")
    require(
        promotion.get("schemaVersion") == "memory-os-backup-restore-promotion-review-registry.v1",
        "promotion review registry schema drift",
    )
    require(promotion.get("appendOnly") is True, "promotion review registry must remain append-only")
    require(
        promotion.get("productionTrafficChanged") is False
        and promotion.get("productionEvidence") is False
        and promotion.get("productionReady") is False,
        "promotion review registry production boundary drift",
    )
    rows = promotion.get("records")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "promotion review registry records invalid")
    generations = generation_by_id(generation)
    for index, row in enumerate(rows):
        validate_row(row, index, generations)

    print(f"PASS: human promotion review source-order binding records={len(rows)} productionEvidence=false productionReady=false")
    print("promotion review contract source-order authority: enforced")
    print("promotion review created in recovery sourceCommitSha accepted: false")
    print("promotion review predating recovery sourceCommitSha accepted: false")
    print("promotion review rewritten after creation accepted: false")
    print("promotion review timestamp later than committed review evidence accepted: false")
    print("human promotion remains separate non-automatic authority: true")
    print("production authority created: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
