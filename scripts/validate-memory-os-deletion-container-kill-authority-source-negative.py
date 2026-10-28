#!/usr/bin/env python3
"""Independent read-only source and executable event/ref/SHA negatives for container-kill authority."""
from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-deletion-container-kill-authority.yml"
INDEPENDENT = ".github/workflows/deletion-container-kill-authority-source-negative.yml"
SELF = "scripts/validate-memory-os-deletion-container-kill-authority-source-negative.py"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
REVIEWED_PUBLISHER = "3284fc4bd9626bcac46a88b6c571d9db01dd3cf2"
REVIEWED_INDEPENDENT = "3a3549fce360edc9a72c558a02a13db7cdf09d60"
RECONCILER = "scripts/reconcile-memory-os-deletion-container-kill-authority.py"
RECONCILE_NEGATIVE = "scripts/validate-memory-os-deletion-container-kill-authority-reconcile-negative.py"
CROSS_NEGATIVE = "scripts/validate-memory-os-deletion-deferred-reason-cross-publisher-negative.py"
REVIEWED_RECONCILER = "8ebb43ea9b39bfbb5c287d0e61b87e2334ab6867"
REVIEWED_RECONCILE_NEGATIVE = "2b05b1757ee2563a3e436b8d83cd74c069ba3cbe"

def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def read(path: str) -> str:
    file = ROOT / path
    if file.is_symlink() or not file.is_file() or file.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise AssertionError("container-kill source missing/substituted: " + path)
    return file.read_text(encoding="utf-8")

def reviewed_source(content: str, expected: str, label: str) -> None:
    if blob(content) != expected:
        raise AssertionError("container-kill complete Git blob drift: " + label)

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
        raise AssertionError("container-kill accepted synthetic full-source drift: " + label)
    print("PASS: container-kill reviewed Git blob negatives (2 cases)")

def step(source: str, title: str) -> str:
    marker = "      - name: " + title + "\n"
    if source.count(marker) != 1:
        raise AssertionError("container-kill source step missing/duplicate: " + title)
    start = source.index("        run: |\n", source.index(marker)) + len("        run: |\n")
    boundaries = [source.find(boundary, start) for boundary in (
        "\n      - name:", "\n  reconcile:", "\n  validate-pr:",
    )]
    end = min((position for position in boundaries if position >= 0), default=len(source))
    lines = source[start:end].splitlines()
    if any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("container-kill shell indentation drift: " + title)
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

CONTAINER_KILL_PUBLISHER_PR_PATHS = (
    ".github/workflows/reconcile-deletion-container-kill-authority.yml",
    "scripts/reconcile-memory-os-deletion-worker-container-kill-recovery.py",
    "scripts/validate-memory-os-deletion-worker-container-kill-recovery-reconcile-negative.py",
    "scripts/reconcile-memory-os-deletion-container-kill-authority.py",
    "scripts/validate-memory-os-deletion-container-kill-authority-reconcile-negative.py",
    "scripts/validate-memory-os-deletion-worker-container-kill-recovery.py",
    "scripts/reconcile-memory-os-load-readiness-note.py",
    "scripts/reconcile-memory-os-load-missing-evidence.py",
    "scripts/validate-memory-os-load.py",
    "scripts/validate-memory-os-operability.py",
    "contracts/operations/deletion-worker-container-kill-recovery-contract.v1.json",
    "docs/fixtures/memory-os-operability/deletion-worker-container-kill-recovery-results.sample.v1.json",
    "contracts/operations/load-test-scenario-contract.v1.json",
    "contracts/operations/production-operability-status.json",
)

CONTAINER_KILL_PUBLISHER_PUSH_PATHS = (
    ".github/workflows/reconcile-deletion-container-kill-authority.yml",
    "scripts/reconcile-memory-os-deletion-worker-container-kill-recovery.py",
    "scripts/validate-memory-os-deletion-worker-container-kill-recovery-reconcile-negative.py",
    "scripts/reconcile-memory-os-deletion-container-kill-authority.py",
    "scripts/validate-memory-os-deletion-container-kill-authority-reconcile-negative.py",
    "scripts/validate-memory-os-deletion-worker-container-kill-recovery.py",
    "scripts/reconcile-memory-os-load-readiness-note.py",
    "scripts/reconcile-memory-os-load-missing-evidence.py",
    "scripts/validate-memory-os-load.py",
    "scripts/validate-memory-os-operability.py",
    "contracts/operations/deletion-worker-container-kill-recovery-contract.v1.json",
    "docs/fixtures/memory-os-operability/deletion-worker-container-kill-recovery-results.sample.v1.json",
)

CONTAINER_KILL_INDEPENDENT_PR_PATHS = (
    ".github/workflows/reconcile-deletion-container-kill-authority.yml",
    ".github/workflows/deletion-container-kill-authority-source-negative.yml",
    "scripts/validate-memory-os-deletion-container-kill-authority-source-negative.py",
    "scripts/reconcile-memory-os-deletion-container-kill-authority.py",
    "scripts/validate-memory-os-deletion-container-kill-authority-reconcile-negative.py",
    "scripts/validate-memory-os-deletion-deferred-reason-cross-publisher-negative.py",
)

CONTAINER_KILL_INDEPENDENT_PUSH_PATHS = (
    ".github/workflows/reconcile-deletion-container-kill-authority.yml",
    ".github/workflows/deletion-container-kill-authority-source-negative.yml",
    "scripts/validate-memory-os-deletion-container-kill-authority-source-negative.py",
    "scripts/reconcile-memory-os-deletion-container-kill-authority.py",
    "scripts/validate-memory-os-deletion-container-kill-authority-reconcile-negative.py",
    "scripts/validate-memory-os-deletion-deferred-reason-cross-publisher-negative.py",
)

def container_kill_trigger_event(event: str, paths: tuple[str, ...]) -> str:
    return ("  " + event + ":\n    branches:\n      - so\n    paths:\n"
            + "".join('      - "' + path + '"\n' for path in paths))


def container_kill_trigger_header(content: str) -> str:
    # Exact, ordered event header: reject unknown, unquoted, duplicate and
    # unexpected event paths instead of depending only on a Git blob digest.
    if content.count("\non:\n") != 1 or content.count("\npermissions:\n") != 1:
        raise SystemExit("container-kill trigger section ambiguous")
    return content.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]


def container_kill_validate_trigger_matrix(
    publisher: str, independent: str,
    publisher_pr: tuple[str, ...] = CONTAINER_KILL_PUBLISHER_PR_PATHS,
    publisher_push: tuple[str, ...] = CONTAINER_KILL_PUBLISHER_PUSH_PATHS,
    independent_pr: tuple[str, ...] = CONTAINER_KILL_INDEPENDENT_PR_PATHS,
    independent_push: tuple[str, ...] = CONTAINER_KILL_INDEPENDENT_PUSH_PATHS,
) -> None:
    expected_publisher = (container_kill_trigger_event("pull_request", publisher_pr)
                          + container_kill_trigger_event("push", publisher_push)
                          + "  workflow_dispatch:\n")
    expected_independent = (container_kill_trigger_event("pull_request", independent_pr)
                            + container_kill_trigger_event("push", independent_push))
    for label, content, expected in (
        ("publisher", publisher, expected_publisher),
        ("independent", independent, expected_independent),
    ):
        if container_kill_trigger_header(content) != expected:
            raise SystemExit("container-kill " + label
                             + " exact event trigger inventory drift")


def replace_container_kill_trigger_header(content: str, original: str, replacement: str) -> str:
    old = "\non:\n" + original + "\npermissions:\n"
    if content.count(old) != 1 or original == replacement:
        raise SystemExit("container-kill trigger negative fixture unreachable")
    return content.replace(old, "\non:\n" + replacement + "\npermissions:\n", 1)


def container_kill_trigger_matrix_negatives(publisher: str, independent: str) -> None:
    def must_reject(p: str, i: str) -> None:
        try:
            container_kill_validate_trigger_matrix(p, i)
        except SystemExit:
            return
        raise SystemExit("container-kill accepted event trigger mutation")

    omissions = additions = 0
    cases = (
        ("publisher", "pull_request", CONTAINER_KILL_PUBLISHER_PR_PATHS),
        ("publisher", "push", CONTAINER_KILL_PUBLISHER_PUSH_PATHS),
        ("independent", "pull_request", CONTAINER_KILL_INDEPENDENT_PR_PATHS),
        ("independent", "push", CONTAINER_KILL_INDEPENDENT_PUSH_PATHS),
    )
    for label, event, paths in cases:
        original = publisher if label == "publisher" else independent
        header = container_kill_trigger_header(original)
        block = container_kill_trigger_event(event, paths)
        if header.count(block) != 1:
            raise SystemExit("container-kill trigger event fixture ambiguous")
        for index in range(len(paths)):
            shorter = paths[:index] + paths[index + 1:]
            mutated = replace_container_kill_trigger_header(
                original, header, header.replace(block, container_kill_trigger_event(event, shorter), 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            omissions += 1
        first = '      - "' + paths[0] + '"\n'
        for addition in (
            '      - "unreviewed/**"\n', '      - unreviewed/**\n',
            first, '      - ' + paths[0] + '\n',
        ):
            mutated_block = block.replace(first, first + addition, 1)
            mutated = replace_container_kill_trigger_header(
                original, header, header.replace(block, mutated_block, 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            additions += 1

    shortened = 0
    for field, paths in (
        ("publisher_pr", CONTAINER_KILL_PUBLISHER_PR_PATHS),
        ("publisher_push", CONTAINER_KILL_PUBLISHER_PUSH_PATHS),
        ("independent_pr", CONTAINER_KILL_INDEPENDENT_PR_PATHS),
        ("independent_push", CONTAINER_KILL_INDEPENDENT_PUSH_PATHS),
    ):
        try:
            container_kill_validate_trigger_matrix(publisher, independent, **{field: paths[:-1]})
        except SystemExit:
            shortened += 1
        else:
            raise SystemExit("container-kill accepted shortened trigger inventory")

    p_header, i_header = container_kill_trigger_header(publisher), container_kill_trigger_header(independent)
    topology = (
        (replace_container_kill_trigger_header(
            publisher, p_header, p_header.replace("  workflow_dispatch:\n", "", 1)), independent),
        (replace_container_kill_trigger_header(
            publisher, p_header, p_header.replace(
                "  workflow_dispatch:\n",
                "  schedule:\n    - cron: '0 0 * * *'\n  workflow_dispatch:\n", 1)), independent),
        (publisher, replace_container_kill_trigger_header(
            independent, i_header, i_header + "  workflow_dispatch:\n")),
    )
    for p, i in topology:
        must_reject(p, i)
    print("PASS: container-kill exact trigger matrix: "
          + str(omissions) + " omissions, " + str(additions)
          + " additions/duplicates, " + str(shortened)
          + " shortened inventories, " + str(len(topology)) + " event topology negatives")


def policy(source: str) -> None:
    for marker in REQUIRED:
        if marker not in source:
            raise AssertionError("container-kill publisher policy missing: " + marker[:70])
    if source.count(CHECKOUT) != 2 or source.count(SETUP) != 2:
        raise AssertionError("container-kill immutable Action count drift")
    if source.count('test -z "$(git status --porcelain)"') != 3:
        raise AssertionError("container-kill clean worktree boundary count drift")
    if "actions/checkout@v4" in source or "actions/setup-python@v5" in source:
        raise AssertionError("container-kill floating Action regression")

def mutations(source: str) -> None:
    for index, marker in enumerate(REQUIRED):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE_TEST", 1)
        if changed == source:
            raise AssertionError("container-kill mutation unreachable: " + str(index))
        try:
            policy(changed)
        except AssertionError:
            continue
        raise AssertionError("container-kill accepted source mutation: " + str(index))
    print(f"PASS: container-kill publisher source mutations ({len(REQUIRED)} cases)")

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
    with tempfile.TemporaryDirectory(prefix="container-kill-operations-identity-") as temp:
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
                raise AssertionError("container-kill event/base/ref/SHA runtime drift: " +
                                     str((title, event, ref, result.returncode)))
    print(f"PASS: container-kill {title} identity shell runtime ({len(cases)} cases)")

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
                raise AssertionError(f"container-kill CAS {label}: unexpected exit {result.returncode}: {result.stderr[-100:]}")
            if sum(line == "push origin HEAD:so" for line in calls) != pushes:
                raise AssertionError("container-kill CAS pushed on stale/no-op/invalid source: " + label)
            if label == "noop" and any(line.startswith("commit ") for line in calls):
                raise AssertionError("container-kill no-op committed")
    print(f"PASS: container-kill actual publisher CAS/no-op shell ({len(cases)} cases)")


def main() -> None:
    publisher, independent = read(PUBLISHER), read(INDEPENDENT)
    for marker in (PUBLISHER, INDEPENDENT, SELF, RECONCILER, RECONCILE_NEGATIVE, CROSS_NEGATIVE, CHECKOUT, SETUP,
                   "persist-credentials: false", "contents: read",
                   'test "$(git rev-parse HEAD)" = "$expected"',
                   'test -z "$(git status --porcelain)"'):
        if marker not in independent:
            raise AssertionError("container-kill independent CI reachability drift: " + marker)
    if independent.count(CROSS_NEGATIVE) != 2:
        raise AssertionError("cross-publisher negative must trigger on PR and push")
    reviewed_source(read(RECONCILER), REVIEWED_RECONCILER, "container-kill reconciler")
    reviewed_source(read(RECONCILE_NEGATIVE), REVIEWED_RECONCILE_NEGATIVE, "container-kill reconcile negative")
    reviewed_negatives(publisher, independent)
    container_kill_validate_trigger_matrix(publisher, independent)
    container_kill_trigger_matrix_negatives(publisher, independent)
    policy(publisher)
    mutations(publisher)
    identity(publisher, "Capture exact PR source", False)
    identity(publisher, "Capture exact source", True)
    cas_runtime(publisher)
    print("PASS: container-kill exact-source read-only proof; production evidence generated: false")

if __name__ == "__main__":
    main()
