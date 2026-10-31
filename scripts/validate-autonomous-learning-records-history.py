#!/usr/bin/env python3
"""Fail closed on post-baseline edits to supplemental OPS learning history."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

BASELINE = "1a2eeab517d8744df42de984fca921aebd747ff8"
SCOPES = (
    "docs/operations/autonomous-learning-records/",
    "docs/operations/autonomous-learning-addenda/",
    "docs/operations/learning/",
)
PASS = "Supplemental learning all-parent append-only history PASS"


class GuardFailure(RuntimeError):
    pass


def git(root: Path, *args: str, allow_failure: bool = False) -> subprocess.CompletedProcess[bytes]:
    env = dict(os.environ, GIT_NO_REPLACE_OBJECTS="1", GIT_CONFIG_NOSYSTEM="1",
               GIT_CONFIG_GLOBAL=os.devnull)
    try:
        result = subprocess.run(["git", "-C", str(root), *args], env=env,
                                capture_output=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise GuardFailure("Git history inspection unavailable") from None
    if result.returncode and not allow_failure:
        raise GuardFailure("Git history inspection failed closed")
    return result


def check_history(root: Path, baseline: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", baseline):
        raise GuardFailure("invalid immutable history baseline")
    head = git(root, "rev-parse", "--verify", "HEAD^{commit}").stdout.strip().decode("ascii")
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise GuardFailure("invalid checked-out commit")
    if git(root, "merge-base", "--is-ancestor", baseline, head, allow_failure=True).returncode:
        raise GuardFailure("immutable learning baseline is not an ancestor")
    commits = git(root, "rev-list", "--reverse", f"{baseline}..{head}").stdout.decode("ascii").splitlines()
    seen: dict[bytes, bytes] = {}
    for commit in commits:
        parents = git(root, "rev-list", "--parents", "-n", "1", commit).stdout.decode("ascii").split()
        if not parents or parents[0] != commit or not parents[1:]:
            raise GuardFailure("ambiguous supplemental history parentage")
        for parent in parents[1:]:
            raw = git(root, "diff-tree", "-r", "--no-renames", "--name-status", "-z",
                      parent, commit, "--", *SCOPES).stdout
            if not raw:
                continue
            fields = raw.split(b"\0")
            if fields[-1] != b"" or (len(fields) - 1) % 2:
                raise GuardFailure("ambiguous supplemental history diff")
            for i in range(0, len(fields) - 1, 2):
                status, path = fields[i:i + 2]
                if status != b"A" or not any(
                    path.startswith(prefix.encode("ascii")) for prefix in SCOPES
                ):
                    raise GuardFailure("supplemental history is not append-only")
                tree = git(root, "ls-tree", "-z", commit, "--", os.fsdecode(path)).stdout
                if not tree.startswith(b"100644 blob ") or tree.count(b"\0") != 1:
                    raise GuardFailure("supplemental history added nonregular authority")
                metadata, separator, found = tree[:-1].partition(b"\t")
                if not separator or found != path or not re.fullmatch(
                    rb"100644 blob [0-9a-f]{40}", metadata
                ):
                    raise GuardFailure("supplemental history added ambiguous authority")
                blob = metadata.split(b" ")[-1]
                if path in seen and seen[path] != blob:
                    raise GuardFailure("supplemental history changed an added record")
                seen[path] = blob
    for path, blob in seen.items():
        final = git(root, "ls-tree", "-z", head, "--", os.fsdecode(path)).stdout
        if final != b"100644 blob " + blob + b"\t" + path + b"\0":
            raise GuardFailure("supplemental history lost an added record")


def self_test() -> None:
    def fixture(change: str, scope: str) -> tuple[Path, str, tempfile.TemporaryDirectory[str]]:
        temp = tempfile.TemporaryDirectory(prefix="supplemental-history-negative-")
        root = Path(temp.name)
        git(root, "init", "-q")
        git(root, "config", "user.name", "Fixture")
        git(root, "config", "user.email", "fixture@example.invalid")
        original = root / scope / "original.md"
        original.parent.mkdir(parents=True)
        original.write_text("immutable\n", encoding="utf-8")
        git(root, "add", ".")
        git(root, "commit", "-qm", "baseline")
        baseline = git(root, "rev-parse", "HEAD").stdout.decode("ascii").strip()
        if change == "add":
            (original.parent / "new.md").write_text("new\n", encoding="utf-8")
        elif change == "modify":
            original.write_text("changed\n", encoding="utf-8")
        elif change == "delete":
            original.unlink()
        elif change == "rename":
            original.rename(original.parent / "renamed.md")
        elif change == "symlink":
            (original.parent / "new.md").symlink_to("original.md")
        elif change == "add-then-modify":
            added = original.parent / "new.md"
            added.write_text("new\n", encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-qm", "first addition")
            added.write_text("rewritten\n", encoding="utf-8")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "candidate")
        return root, baseline, temp

    for scope in SCOPES:
        for kind in ("add", "modify", "delete", "rename", "symlink", "add-then-modify"):
            root, baseline, temp = fixture(kind, scope)
            try:
                if kind == "add":
                    check_history(root, baseline)
                else:
                    try:
                        check_history(root, baseline)
                    except GuardFailure:
                        pass
                    else:
                        raise GuardFailure("negative history fixture accepted: " + scope + kind)
            finally:
                temp.cleanup()


    # First-parent-only history would miss a side-branch rewrite that is
    # restored before merge; inspect every reachable parent edge instead.
    for kind in ("merge-add", "merge-rewrite-old", "merge-rewrite-new"):
        with tempfile.TemporaryDirectory(prefix="supplemental-merge-negative-") as temp:
            root = Path(temp)
            git(root, "init", "-q")
            git(root, "config", "user.name", "Fixture")
            git(root, "config", "user.email", "fixture@example.invalid")
            old = root / SCOPES[0] / "original.md"
            old.parent.mkdir(parents=True)
            old.write_text("immutable\n", encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-qm", "baseline")
            baseline = git(root, "rev-parse", "HEAD").stdout.decode("ascii").strip()
            base_branch = git(root, "branch", "--show-current").stdout.decode("ascii").strip()
            git(root, "checkout", "-qb", "feature")
            new = old.parent / "new.md"
            new.write_text("new\n", encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-qm", "add new record")
            if kind == "merge-rewrite-old":
                old.write_text("mutated\n", encoding="utf-8")
                git(root, "commit", "-qam", "mutate existing")
                old.write_text("immutable\n", encoding="utf-8")
                git(root, "commit", "-qam", "restore existing")
            elif kind == "merge-rewrite-new":
                new.write_text("mutated\n", encoding="utf-8")
                git(root, "commit", "-qam", "mutate new")
            git(root, "checkout", "-q", base_branch)
            git(root, "merge", "-q", "--no-ff", "-m", "merge feature", "feature")
            if kind == "merge-add":
                check_history(root, baseline)
            else:
                try:
                    check_history(root, baseline)
                except GuardFailure:
                    pass
                else:
                    raise GuardFailure("merged history negative accepted: " + kind)



def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
        check_history(args.repo_root, BASELINE)
    except GuardFailure as exc:
        print("SUPPLEMENTAL LEARNING HISTORY FAILED: " + str(exc), file=sys.stderr)
        return 1
    print(PASS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
