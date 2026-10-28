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
REVIEWED_INDEPENDENT = "67cad76cab58313a92bf4993b707a9123c4150a6"

PUBLISHER_PR_TRIGGER_PATHS = (
    ".github/workflows/reconcile-deletion-lease-recovery-authority.yml",
    "scripts/reconcile-memory-os-deletion-lease-recovery-authority.py",
    "scripts/validate-memory-os-deletion-lease-recovery-authority-reconcile-negative.py",
    "scripts/reconcile-memory-os-load-readiness-note.py",
    "scripts/reconcile-memory-os-load-missing-evidence.py",
    "scripts/validate-memory-os-load.py",
    "scripts/validate-memory-os-operability.py",
    "contracts/operations/deletion-lease-recovery-contract.v1.json",
    "docs/fixtures/memory-os-operability/deletion-lease-recovery-results.sample.v1.json",
    "contracts/operations/load-test-scenario-contract.v1.json",
    "contracts/operations/production-operability-status.json",
)
PUBLISHER_PUSH_TRIGGER_PATHS = (
    ".github/workflows/reconcile-deletion-lease-recovery-authority.yml",
    "scripts/reconcile-memory-os-deletion-lease-recovery-authority.py",
    "scripts/validate-memory-os-deletion-lease-recovery-authority-reconcile-negative.py",
    "scripts/reconcile-memory-os-load-readiness-note.py",
    "scripts/reconcile-memory-os-load-missing-evidence.py",
    "scripts/validate-memory-os-load.py",
    "scripts/validate-memory-os-operability.py",
    "contracts/operations/deletion-lease-recovery-contract.v1.json",
    "docs/fixtures/memory-os-operability/deletion-lease-recovery-results.sample.v1.json",
)
INDEPENDENT_PR_TRIGGER_PATHS = (
    ".github/workflows/reconcile-deletion-lease-recovery-authority.yml",
    ".github/workflows/deletion-lease-recovery-authority-source-negative.yml",
    "scripts/validate-memory-os-deletion-lease-recovery-authority-source-negative.py",
    "scripts/reconcile-memory-os-deletion-lease-recovery-authority.py",
    "scripts/validate-memory-os-deletion-lease-recovery-authority-reconcile-negative.py",
    "scripts/validate-memory-os-deletion-deferred-reason-cross-publisher-negative.py",
)
INDEPENDENT_PUSH_TRIGGER_PATHS = (
    ".github/workflows/reconcile-deletion-lease-recovery-authority.yml",
    ".github/workflows/deletion-lease-recovery-authority-source-negative.yml",
    "scripts/validate-memory-os-deletion-lease-recovery-authority-source-negative.py",
    "scripts/reconcile-memory-os-deletion-lease-recovery-authority.py",
    "scripts/validate-memory-os-deletion-lease-recovery-authority-reconcile-negative.py",
    "scripts/validate-memory-os-deletion-deferred-reason-cross-publisher-negative.py",
)
RECONCILER = "scripts/reconcile-memory-os-deletion-lease-recovery-authority.py"
RECONCILE_NEGATIVE = "scripts/validate-memory-os-deletion-lease-recovery-authority-reconcile-negative.py"
CROSS_NEGATIVE = "scripts/validate-memory-os-deletion-deferred-reason-cross-publisher-negative.py"
REVIEWED_RECONCILER = "0d04c6728c0d208d9334cb57ca8e5539f93e74a2"
REVIEWED_RECONCILE_NEGATIVE = "45274a621d1964f7ece7a203a857daa71972fbdf"
REVIEWED_CROSS_NEGATIVE = "0a6217af102ab01273df28516d856ba2b87d8654"


def validate_trigger_reachability(
    source: str, *, publisher: bool,
    pr_paths: tuple[str, ...] | None = None,
    push_paths: tuple[str, ...] | None = None,
) -> None:
    """Keep distinct reviewed PR/push path authorities, including intentional asymmetry."""
    expected_pr = PUBLISHER_PR_TRIGGER_PATHS if publisher else INDEPENDENT_PR_TRIGGER_PATHS
    expected_push = PUBLISHER_PUSH_TRIGGER_PATHS if publisher else INDEPENDENT_PUSH_TRIGGER_PATHS
    pr_inventory = expected_pr if pr_paths is None else pr_paths
    push_inventory = expected_push if push_paths is None else push_paths
    for label, actual, expected in (
        ("PR", pr_inventory, expected_pr), ("push", push_inventory, expected_push)
    ):
        if len(actual) != len(expected) or len(set(actual)) != len(expected):
            raise AssertionError("lease authority CI " + label + " trigger inventory shortened or duplicated")
    pr = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    end = "  workflow_dispatch:\n" if publisher else "\npermissions:\n"
    if any(source.count(marker) != 1 for marker in (pr, push, end)):
        raise AssertionError("lease authority CI trigger marker drift")
    if not (source.index(pr) < source.index(push) < source.index(end)):
        raise AssertionError("lease authority CI trigger ordering drift")
    for event, start, stop, approved_paths in (
        ("PR", pr, push, pr_inventory), ("push", push, end, push_inventory)
    ):
        block = source.split(start, 1)[1].split(stop, 1)[0]
        actual = tuple(line for line in block.splitlines()
                       if line.strip() and not line.lstrip().startswith("#"))
        approved = tuple('      - "' + path + '"' for path in approved_paths)
        if actual != approved:
            raise AssertionError("lease authority CI " + event + " exact trigger path drift")


def prove_trigger_reachability_negatives(publisher: str, independent: str) -> None:
    """Prove all event-specific omissions, quoted/unquoted additions and inventory truncations."""
    pr = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    for label, source, is_publisher, pr_paths, push_paths in (
        ("publisher", publisher, True, PUBLISHER_PR_TRIGGER_PATHS, PUBLISHER_PUSH_TRIGGER_PATHS),
        ("independent", independent, False, INDEPENDENT_PR_TRIGGER_PATHS, INDEPENDENT_PUSH_TRIGGER_PATHS),
    ):
        end = "  workflow_dispatch:\n" if is_publisher else "\npermissions:\n"
        for event, start, stop, paths in (
            ("PR", pr, push, pr_paths), ("push", push, end, push_paths)
        ):
            start_index = source.index(start) + len(start)
            end_index = source.index(stop, start_index)
            block = source[start_index:end_index]
            for path in paths:
                token = '      - "' + path + '"\n'
                if block.count(token) != 1:
                    raise AssertionError("lease authority CI mutation anchor drift: " + path)
                mutated = source[:start_index] + block.replace(token, "", 1) + source[end_index:]
                try:
                    validate_trigger_reachability(mutated, publisher=is_publisher)
                except AssertionError:
                    pass
                else:
                    raise AssertionError("lease authority CI accepted missing " + label + " " + event + " trigger: " + path)
            for name, injection in (
                ("quoted extra", '      - "unreviewed/**"\n'),
                ("quoted duplicate", '      - "' + paths[0] + '"\n'),
                ("unquoted extra", "      - unreviewed/**\n"),
                ("unquoted duplicate", "      - " + paths[0] + "\n"),
            ):
                mutated = source[:start_index] + injection + source[start_index:]
                try:
                    validate_trigger_reachability(mutated, publisher=is_publisher)
                except AssertionError:
                    pass
                else:
                    raise AssertionError("lease authority CI accepted " + label + " " + event + " " + name)
        for event in ("PR", "push"):
            try:
                validate_trigger_reachability(
                    source, publisher=is_publisher,
                    pr_paths=pr_paths[:-1] if event == "PR" else pr_paths,
                    push_paths=push_paths[:-1] if event == "push" else push_paths,
                )
            except AssertionError:
                pass
            else:
                raise AssertionError("lease authority CI accepted shortened " + label + " " + event + " inventory")
    print("PASS: lease authority CI event triggers (32 removals; 16 additions; 4 shortened inventory negatives)")


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
    for marker in (PUBLISHER, INDEPENDENT, SELF, RECONCILER, RECONCILE_NEGATIVE, CROSS_NEGATIVE, CHECKOUT, SETUP,
                   "persist-credentials: false", "contents: read",
                   'test "$(git rev-parse HEAD)" = "$expected"',
                   'test -z "$(git status --porcelain)"'):
        if marker not in independent:
            raise AssertionError("lease-recovery independent CI reachability drift: " + marker)
    for path, expected in ((RECONCILER, REVIEWED_RECONCILER),
                           (RECONCILE_NEGATIVE, REVIEWED_RECONCILE_NEGATIVE),
                           (CROSS_NEGATIVE, REVIEWED_CROSS_NEGATIVE)):
        reviewed_source(read(path), expected, path)
    if (independent.count(RECONCILER) != 2
            or independent.count(RECONCILE_NEGATIVE) != 3
            or independent.count(CROSS_NEGATIVE) != 2):
        raise AssertionError("lease authority transitive negative CI reachability drift")
    reviewed_negatives(publisher, independent)
    validate_trigger_reachability(publisher, publisher=True)
    validate_trigger_reachability(independent, publisher=False)
    prove_trigger_reachability_negatives(publisher, independent)
    policy(publisher)
    mutations(publisher)
    identity(publisher, "Capture exact PR source", False)
    identity(publisher, "Capture exact source", True)
    cas_runtime(publisher)
    print("PASS: lease-recovery exact-source read-only proof; production evidence generated: false")

if __name__ == "__main__":
    main()
