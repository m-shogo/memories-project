#!/usr/bin/env python3
"""Fail closed on post-baseline edits to supplemental OPS learning history."""
from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
import tempfile
from unittest.mock import patch
from pathlib import Path

BASELINE = "1a2eeab517d8744df42de984fca921aebd747ff8"
SCOPES = (
    "docs/operations/autonomous-learning-records/",
    "docs/operations/autonomous-learning-addenda/",
    "docs/operations/learning/",
)
PASS = "Supplemental learning all-parent append-only history PASS (34 fixtures)"


class GuardFailure(RuntimeError):
    pass


def git(root: Path, *args: str, allow_failure: bool = False) -> subprocess.CompletedProcess[bytes]:
    # An inherited GIT_DIR or GIT_WORK_TREE can redirect -C to an unrelated
    # repository. Reject every inherited Git override before inspecting history.
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("GIT_")}
    env.update(GIT_NO_REPLACE_OBJECTS="1", GIT_CONFIG_NOSYSTEM="1",
               GIT_CONFIG_GLOBAL=os.devnull)
    try:
        result = subprocess.run(["git", "-C", str(root), *args], env=env,
                                capture_output=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise GuardFailure("Git history inspection unavailable") from None
    if result.returncode and not allow_failure:
        raise GuardFailure("Git history inspection failed closed")
    if result.returncode == 0 and result.stderr:
        raise GuardFailure("Git history inspection emitted unexpected diagnostics")
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
                      parent, commit, "--", *(scope.rstrip("/") for scope in SCOPES)).stdout
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



def prove_delimiter_literals(source: str) -> None:
    """Require parsed NUL/tab bytes, not doubly escaped source spellings."""
    tree = ast.parse(source)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == "check_history"]
    if len(functions) != 1:
        raise GuardFailure("supplemental history delimiter function missing")
    values = [node.value for node in ast.walk(functions[0])
              if isinstance(node, ast.Constant) and isinstance(node.value, bytes)]
    if values.count(bytes([0])) != 3 or values.count(bytes([9])) != 2:
        raise GuardFailure("supplemental history delimiter literal drift")


def expect_guard_failure(action, expected: str, label: str) -> None:
    """A negative is valid only when it fails for its reviewed cause."""
    try:
        action()
    except GuardFailure as exc:
        if str(exc) != expected:
            raise GuardFailure("negative fixture failed for unrelated reason: " + label) from exc
    else:
        raise GuardFailure("negative fixture accepted: " + label)


def self_test() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    prove_delimiter_literals(source)
    for digit in ("0", "t"):
        slash = chr(92)
        original = 'b"' + slash + digit + '"'
        doubled = 'b"' + slash + slash + digit + '"'
        if original not in source:
            raise GuardFailure("supplemental history literal negative fixture missing")
        try:
            prove_delimiter_literals(source.replace(original, doubled, 1))
        except GuardFailure:
            pass
        else:
            raise GuardFailure("supplemental history double-escape accepted")
    # An unrelated Git failure must never count as proof of a rejected
    # mutation. This deliberately fails the negative-assertion helper.
    def unrelated_failure() -> None:
        raise GuardFailure("Git history inspection unavailable")

    try:
        expect_guard_failure(unrelated_failure, "supplemental history is not append-only",
                             "wrong-reason-control")
    except GuardFailure as exc:
        if str(exc) != "negative fixture failed for unrelated reason: wrong-reason-control":
            raise
    else:
        raise GuardFailure("unrelated negative failure accepted")

    # Successful Git commands must not silently ignore corruption warnings or
    # other unexpected diagnostics on stderr.
    with patch.object(subprocess, "run", return_value=subprocess.CompletedProcess(
        args=["git"], returncode=0, stdout=b"safe\n", stderr=b"unexpected\n"
    )):
        try:
            git(Path("."), "rev-parse", "HEAD")
        except GuardFailure as exc:
            if str(exc) != "Git history inspection emitted unexpected diagnostics":
                raise
        else:
            raise GuardFailure("Git success with unexpected stderr accepted")

    # Prove the Git wrapper ignores hostile inherited repository selectors.
    # Both selectors redirect a naive git -C invocation to the decoy worktree.
    with tempfile.TemporaryDirectory(prefix="supplemental-git-env-negative-") as temp:
        trusted = Path(temp) / "trusted"
        decoy = Path(temp) / "decoy"
        for repo in (trusted, decoy):
            repo.mkdir()
            git(repo, "init", "-q")
        expected = git(trusted, "rev-parse", "--show-toplevel").stdout.strip()
        for variable, value in (("GIT_DIR", str(decoy / ".git")),
                                ("GIT_WORK_TREE", str(decoy))):
            previous = os.environ.get(variable)
            try:
                os.environ[variable] = value
                actual = git(trusted, "rev-parse", "--show-toplevel").stdout.strip()
                if actual != expected:
                    raise GuardFailure("supplemental history inherited Git repository override")
            finally:
                if previous is None:
                    os.environ.pop(variable, None)
                else:
                    os.environ[variable] = previous

    # A caller can also inject Git configuration without touching GIT_DIR.
    # Prove that a synthetic hooksPath override is visible to naive Git but
    # absent from the trusted history wrapper.
    with tempfile.TemporaryDirectory(prefix="supplemental-git-config-negative-") as temp:
        trusted = Path(temp) / "trusted"
        trusted.mkdir()
        git(trusted, "init", "-q")
        overrides = {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.hooksPath",
            "GIT_CONFIG_VALUE_0": str(Path(temp) / "untrusted-hooks"),
        }
        previous = {key: os.environ.get(key) for key in overrides}
        try:
            os.environ.update(overrides)
            untrusted = subprocess.run(
                ["git", "-C", str(trusted), "config", "--get", "core.hooksPath"],
                env=dict(os.environ), capture_output=True, timeout=20, check=False,
            )
            if (untrusted.returncode != 0 or
                    untrusted.stdout.strip() != overrides["GIT_CONFIG_VALUE_0"].encode()):
                raise GuardFailure("supplemental history Git config negative control invalid")
            sanitized = git(trusted, "config", "--get", "core.hooksPath",
                            allow_failure=True)
            if sanitized.returncode != 1 or sanitized.stdout:
                raise GuardFailure("supplemental history inherited Git configuration")
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

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
        elif change == "scope-root-symlink":
            # A pathspec ending in / misses a symlink at the scope root.
            # The parent path must be part of the diff authority too.
            (root / SCOPES[1].rstrip("/")).symlink_to(
                Path(SCOPES[0]).name, target_is_directory=True
            )
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
                    expect_guard_failure(
                        lambda: check_history(root, baseline),
                        ("supplemental history added nonregular authority"
                         if kind == "symlink" else "supplemental history is not append-only"),
                        scope + kind,
                    )
            finally:
                temp.cleanup()


    # An added symlink exactly at a protected scope root is not a record,
    # but it must not disappear behind a trailing-slash Git pathspec.
    root, baseline, temp = fixture("scope-root-symlink", SCOPES[0])
    try:
        expect_guard_failure(
            lambda: check_history(root, baseline),
            "supplemental history is not append-only", "scope-root-symlink",
        )
    finally:
        temp.cleanup()


    # First-parent-only history would miss a side-branch rewrite that is
    # restored before merge; inspect every reachable parent edge instead.
    for kind in ("merge-add", "merge-rewrite-old", "merge-rewrite-new",
                 "merge-delete-restore", "merge-mode-restore"):
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
            elif kind == "merge-delete-restore":
                old.unlink()
                git(root, "add", "-A")
                git(root, "commit", "-qm", "delete existing")
                old.write_text("immutable\n", encoding="utf-8")
                git(root, "add", "-A")
                git(root, "commit", "-qm", "restore existing")
            elif kind == "merge-mode-restore":
                relative = old.relative_to(root).as_posix()
                git(root, "update-index", "--chmod=+x", relative)
                git(root, "commit", "-qm", "make existing executable")
                git(root, "update-index", "--chmod=-x", relative)
                git(root, "commit", "-qm", "restore existing mode")
            git(root, "checkout", "-q", base_branch)
            git(root, "merge", "-q", "--no-ff", "-m", "merge feature", "feature")
            if kind == "merge-add":
                check_history(root, baseline)
            else:
                expect_guard_failure(
                    lambda: check_history(root, baseline),
                    "supplemental history is not append-only", kind,
                )



    # A local refs/replace graft can rewrite apparent commit parentage.
    # Trusted history inspection must ignore it and reject the real mutation.
    root, baseline, temp = fixture("modify", SCOPES[0])
    try:
        git(root, "replace", "--graft", "HEAD")
        untrusted_env = {key: value for key, value in os.environ.items()
                         if not key.startswith("GIT_")}
        untrusted_env.update(GIT_CONFIG_NOSYSTEM="1",
                             GIT_CONFIG_GLOBAL=os.devnull)
        untrusted = subprocess.run(
            ["git", "-C", str(root), "rev-list", "--parents", "-n", "1", "HEAD"],
            env=untrusted_env, capture_output=True, timeout=20, check=False,
        )
        trusted = git(root, "rev-list", "--parents", "-n", "1", "HEAD")
        if (untrusted.returncode != 0 or untrusted.stderr
                or untrusted.stdout == trusted.stdout):
            raise GuardFailure("Git replacement negative control ineffective")
        expect_guard_failure(
            lambda: check_history(root, baseline),
            "supplemental history is not append-only", "git-replace-graft",
        )
    finally:
        temp.cleanup()


    # An octopus merge has three parent edges. A restored mutation on the
    # third side branch must not disappear behind a clean merge result.
    for corrupt in (False, True):
        with tempfile.TemporaryDirectory(prefix="supplemental-octopus-negative-") as temp:
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
            git(root, "checkout", "-qb", "feature-add")
            (old.parent / "new.md").write_text("new\n", encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-qm", "add record")
            git(root, "checkout", "-qb", "feature-third", baseline)
            if corrupt:
                old.write_text("mutated\n", encoding="utf-8")
                git(root, "commit", "-qam", "mutate old record")
                old.write_text("immutable\n", encoding="utf-8")
                git(root, "commit", "-qam", "restore old record")
            else:
                (root / "README.md").write_text("safe\n", encoding="utf-8")
                git(root, "add", ".")
                git(root, "commit", "-qm", "safe outside scope")
            git(root, "checkout", "-q", base_branch)
            git(root, "merge", "-q", "--no-ff", "-m", "octopus merge",
                "feature-add", "feature-third")
            parents = git(root, "rev-list", "--parents", "-n", "1", "HEAD").stdout.decode(
                "ascii").split()
            if len(parents) != 4:
                raise GuardFailure("octopus fixture did not create three parents")
            if corrupt:
                expect_guard_failure(
                    lambda: check_history(root, baseline),
                    "supplemental history is not append-only",
                    "octopus-third-parent-restore",
                )
            else:
                check_history(root, baseline)


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
