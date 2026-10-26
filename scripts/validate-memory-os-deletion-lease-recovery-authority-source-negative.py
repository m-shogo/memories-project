#!/usr/bin/env python3
"""Independent read-only source and executable event/ref/SHA negatives for lease recovery authority."""
from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-deletion-lease-recovery-authority.yml"
INDEPENDENT = ".github/workflows/deletion-lease-recovery-authority-source-negative.yml"
SELF = "scripts/validate-memory-os-deletion-lease-recovery-authority-source-negative.py"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
REVIEWED_PUBLISHER = "ecb7b9858fdb3b203f07205454836c0a6c6af149"
REVIEWED_INDEPENDENT = "ee47cf61046b716b2357f28c50befdb114d3d832"

def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def read(path: str) -> str:
    file = ROOT / path
    if file.is_symlink() or not file.is_file() or file.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise AssertionError("lease-recovery source missing/substituted: " + path)
    return file.read_text(encoding="utf-8")

def reviewed_source(content: str, expected: str, label: str) -> None:
    if blob(content) != expected:
        raise AssertionError("lease-recovery complete Git blob drift: " + label)

def reviewed_negatives(publisher: str, independent: str) -> None:
    for label, content, expected in (
        ("publisher", publisher, REVIEWED_PUBLISHER),
        ("independent CI", independent, REVIEWED_INDEPENDENT),
    ):
        reviewed_source(content, expected, label)
        try:
            reviewed_source(content + "\n# synthetic source drift\n", expected, label)
        except AssertionError:
            continue
        raise AssertionError("lease-recovery accepted synthetic full-source drift: " + label)
    print("PASS: lease-recovery reviewed Git blob negatives (2 cases)")

def step(source: str, title: str) -> str:
    marker = "      - name: " + title + "\n"
    if source.count(marker) != 1:
        raise AssertionError("lease-recovery source step missing/duplicate: " + title)
    start = source.index("        run: |\n", source.index(marker)) + len("        run: |\n")
    boundaries = [source.find(boundary, start) for boundary in (
        "\n      - name:", "\n  reconcile:", "\n  validate-pr:",
    )]
    end = min((position for position in boundaries if position >= 0), default=len(source))
    lines = source[start:end].splitlines()
    if any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("lease-recovery shell indentation drift: " + title)
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"

REQUIRED = (
    "if: github.event_name == 'pull_request' && github.base_ref == 'so'",
    "github.ref == 'refs/heads/so'",
    "persist-credentials: false",
    "persist-credentials: true",
    'test "${GITHUB_EVENT_NAME:-}" = "pull_request"',
    'test "${GITHUB_BASE_REF:-}" = "so"',
    '[[ "${PR_HEAD_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"',
    '[[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]',
    'test "${GITHUB_REF:-}" = "refs/heads/so"',
    '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
    'git fetch origin so',
    'git push origin HEAD:so',
)

def policy(source: str) -> None:
    for marker in REQUIRED:
        if marker not in source:
            raise AssertionError("lease-recovery publisher policy missing: " + marker[:70])
    if source.count(CHECKOUT) != 2 or source.count(SETUP) != 2:
        raise AssertionError("lease-recovery immutable Action count drift")
    if source.count('test -z "$(git status --porcelain)"') != 3:
        raise AssertionError("lease-recovery clean worktree boundary count drift")
    if "actions/checkout@v4" in source or "actions/setup-python@v5" in source:
        raise AssertionError("lease-recovery floating Action regression")

def mutations(source: str) -> None:
    for index, marker in enumerate(REQUIRED):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE_TEST", 1)
        if changed == source:
            raise AssertionError("lease-recovery mutation unreachable: " + str(index))
        try:
            policy(changed)
        except AssertionError:
            continue
        raise AssertionError("lease-recovery accepted source mutation: " + str(index))
    print(f"PASS: lease-recovery publisher source mutations ({len(REQUIRED)} cases)")

def identity(source: str, title: str, writer: bool) -> None:
    shell = step(source, title)
    if writer:
        shell = shell.split('echo "SOURCE_SHA=', 1)[0]
    head = "a" * 40
    if writer:
        cases = (
            ("push", "", "refs/heads/so", "", head, True),
            ("workflow_dispatch", "", "refs/heads/so", "", head, True),
            ("schedule", "", "refs/heads/so", "", head, False),
            ("pull_request", "", "refs/heads/so", "", head, False),
            ("push", "", "refs/heads/main", "", head, False),
            ("push", "", "refs/heads/so", "", "b" * 40, False),
            ("push", "", "refs/heads/so", "", "A" * 40, False),
            ("push", "", "refs/heads/so", "", "a" * 39, False),
        )
    else:
        cases = (
            ("pull_request", "so", "", head, "", True),
            ("pull_request", "main", "", head, "", False),
            ("push", "so", "", head, "", False),
            ("pull_request", "so", "", "b" * 40, "", False),
            ("pull_request", "so", "", "A" * 40, "", False),
            ("pull_request", "so", "", "a" * 39, "", False),
        )
    with tempfile.TemporaryDirectory(prefix="lease-recovery-operations-identity-") as temp:
        root = Path(temp)
        git = root / "git"
        git.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"HEAD\" ]; then printf '" + head + "\n'; exit 0; fi\n"
            "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then exit 0; fi\n"
            "exit 1\n", encoding="utf-8",
        )
        git.chmod(0o755)
        for event, base, ref, pr_sha, sha, allowed in cases:
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_EVENT_NAME=event, GITHUB_BASE_REF=base, GITHUB_REF=ref,
                       PR_HEAD_SHA=pr_sha, GITHUB_SHA=sha)
            result = subprocess.run(
                ["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False,
            )
            if (result.returncode == 0) != allowed:
                raise AssertionError("lease-recovery event/base/ref/SHA runtime drift: " +
                                     str((title, event, ref, result.returncode)))
    print(f"PASS: lease-recovery {title} identity shell runtime ({len(cases)} cases)")

def cas_runtime(source: str) -> None:
    """Execute the real blocker publisher commit/CAS shell in a disposable fake-Git sandbox."""
    shell = step(source, "Commit canonical authority update")
    head = "a" * 40
    other = "b" * 40
    cases = (
        ("noop", head, True, True, 0, 0),
        ("success", head, False, True, 0, 1),
        ("stale-remote", other, False, True, 75, 0),
        ("missing-remote", "", False, True, 75, 0),
        ("diff-check", head, False, False, 1, 0),
    )
    fake_git = """#!/usr/bin/env python3
import os
import sys
from pathlib import Path
args = sys.argv[1:]
with Path(os.environ["FAKE_GIT_LOG"]).open("a", encoding="utf-8") as f:
    f.write(" ".join(args) + "\\n")
if args[:2] == ["rev-parse", "HEAD"]:
    print("a" * 40)
elif args[:2] == ["rev-parse", "origin/so"]:
    print(os.environ["FAKE_REMOTE"])
elif args[:3] == ["diff", "--cached", "--quiet"]:
    sys.exit(0 if os.environ["FAKE_NOOP"] == "1" else 1)
elif args[:3] == ["diff", "--cached", "--check"]:
    sys.exit(0 if os.environ["FAKE_CHECK"] == "1" else 1)
elif args[0] in ("add", "config", "commit", "fetch", "push"):
    pass
else:
    sys.exit(92)
"""
    for label, remote, noop, check, exit_code, pushes in cases:
        with tempfile.TemporaryDirectory(prefix="advanced-deletion-cas-") as tmp:
            root = Path(tmp)
            git = root / "git"
            git.write_text(fake_git, encoding="utf-8")
            git.chmod(0o755)
            log = root / "git.log"
            log.write_text("", encoding="utf-8")
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       SOURCE_SHA=head, FAKE_GIT_LOG=str(log), FAKE_REMOTE=remote,
                       FAKE_NOOP="1" if noop else "0", FAKE_CHECK="1" if check else "0")
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                    cwd=root, env=env, capture_output=True, text=True,
                                    timeout=10, check=False)
            calls = log.read_text(encoding="utf-8").splitlines()
            if result.returncode != exit_code:
                raise AssertionError(f"lease-recovery CAS {label}: unexpected exit {result.returncode}: {result.stderr[-100:]}")
            if sum(line == "push origin HEAD:so" for line in calls) != pushes:
                raise AssertionError("lease-recovery CAS pushed on stale/no-op/invalid source: " + label)
            if label == "noop" and any(line.startswith("commit ") for line in calls):
                raise AssertionError("lease-recovery no-op committed")
    print(f"PASS: lease-recovery actual publisher CAS/no-op shell ({len(cases)} cases)")


def main() -> None:
    publisher, independent = read(PUBLISHER), read(INDEPENDENT)
    for marker in (PUBLISHER, INDEPENDENT, SELF, CHECKOUT, SETUP,
                   "persist-credentials: false", "contents: read",
                   'test "$(git rev-parse HEAD)" = "$expected"',
                   'test -z "$(git status --porcelain)"'):
        if marker not in independent:
            raise AssertionError("lease-recovery independent CI reachability drift: " + marker)
    reviewed_negatives(publisher, independent)
    policy(publisher)
    mutations(publisher)
    identity(publisher, "Capture exact PR source", False)
    identity(publisher, "Capture exact source", True)
    cas_runtime(publisher)
    print("PASS: lease-recovery exact-source read-only proof; production evidence generated: false")

if __name__ == "__main__":
    main()
