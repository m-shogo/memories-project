#!/usr/bin/env python3
"""Independent read-only source and executable event/ref/SHA negatives for rate-limit operations."""
from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-rate-limit-operations.yml"
INDEPENDENT = ".github/workflows/rate-limit-operations-source-negative.yml"
SELF = "scripts/validate-memory-os-rate-limit-operations-source-negative.py"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
REVIEWED_PUBLISHER = "6226842e17488c98e74325c927abbe8769d134ca"
REVIEWED_INDEPENDENT = "1c0af3345ce2122e02f68dd58205886569d9eecb"

def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def read(path: str) -> str:
    file = ROOT / path
    if file.is_symlink() or not file.is_file() or file.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise AssertionError("rate-limit source missing/substituted: " + path)
    return file.read_text(encoding="utf-8")

def reviewed_source(content: str, expected: str, label: str) -> None:
    if blob(content) != expected:
        raise AssertionError("rate-limit complete Git blob drift: " + label)

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
        raise AssertionError("rate-limit accepted synthetic full-source drift: " + label)
    print("PASS: rate-limit reviewed Git blob negatives (2 cases)")

def step(source: str, title: str) -> str:
    marker = "      - name: " + title + "\n"
    if source.count(marker) != 1:
        raise AssertionError("rate-limit source step missing/duplicate: " + title)
    start = source.index("        run: |\n", source.index(marker)) + len("        run: |\n")
    boundaries = [source.find(boundary, start) for boundary in (
        "\n      - name:", "\n  reconcile:", "\n  validate-pr:",
    )]
    end = min((position for position in boundaries if position >= 0), default=len(source))
    lines = source[start:end].splitlines()
    if any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("rate-limit shell indentation drift: " + title)
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

RATE_OPS_PUBLISHER_PR_PATHS = (
    ".github/workflows/reconcile-rate-limit-operations.yml",
    "contracts/operations/rate-limit-operations-contract.v1.json",
    "contracts/operations/rate-limit-policy-contract.v1.json",
    "contracts/operations/production-operability-status.json",
    "docs/runbooks/memory-os-rate-limit-operations.md",
    "scripts/validate-memory-os-rate-limit-operations.py",
    "scripts/validate-memory-os-rate-limit-operations-reconcile-negative.py",
    "scripts/validate-memory-os-rate-limit-operation-evidence-reconcile-negative.py",
    "scripts/validate-memory-os-rate-limit-authority-negative.py",
    "scripts/reconcile-memory-os-rate-limit-operations.py",
    "scripts/reconcile-memory-os-rate-limit-operation-evidence.py",
    "scripts/validate-memory-os-rate-limit.py",
    "scripts/validate-memory-os-operability.py",
    "scripts/validate-memory-os-entry-docs.py",
)

RATE_OPS_PUBLISHER_PUSH_PATHS = (
    ".github/workflows/reconcile-rate-limit-operations.yml",
    "contracts/operations/rate-limit-operations-contract.v1.json",
    "contracts/operations/rate-limit-policy-contract.v1.json",
    "contracts/operations/production-operability-status.json",
    "docs/runbooks/memory-os-rate-limit-operations.md",
    "scripts/validate-memory-os-rate-limit-operations.py",
    "scripts/validate-memory-os-rate-limit-operations-reconcile-negative.py",
    "scripts/validate-memory-os-rate-limit-operation-evidence-reconcile-negative.py",
    "scripts/validate-memory-os-rate-limit-authority-negative.py",
    "scripts/reconcile-memory-os-rate-limit-operations.py",
    "scripts/reconcile-memory-os-rate-limit-operation-evidence.py",
    "scripts/validate-memory-os-rate-limit.py",
    "scripts/validate-memory-os-operability.py",
    "scripts/validate-memory-os-entry-docs.py",
)

RATE_OPS_INDEPENDENT_PR_PATHS = (
    ".github/workflows/reconcile-rate-limit-operations.yml",
    ".github/workflows/rate-limit-operations-source-negative.yml",
    "scripts/validate-memory-os-rate-limit-operations-source-negative.py",
)

RATE_OPS_INDEPENDENT_PUSH_PATHS = (
    ".github/workflows/reconcile-rate-limit-operations.yml",
    ".github/workflows/rate-limit-operations-source-negative.yml",
    "scripts/validate-memory-os-rate-limit-operations-source-negative.py",
)

def rate_ops_trigger_event(event: str, paths: tuple[str, ...]) -> str:
    return ("  " + event + ":\n    branches:\n      - so\n    paths:\n"
            + "".join('      - "' + path + '"\n' for path in paths))


def rate_ops_trigger_header(content: str) -> str:
    # Exact, ordered event header: reject unknown, unquoted, duplicate and
    # unexpected event paths instead of depending only on a Git blob digest.
    if content.count("\non:\n") != 1 or content.count("\npermissions:\n") != 1:
        raise SystemExit("rate-limit-operations trigger section ambiguous")
    return content.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]


def rate_ops_validate_trigger_matrix(
    publisher: str, independent: str,
    publisher_pr: tuple[str, ...] = RATE_OPS_PUBLISHER_PR_PATHS,
    publisher_push: tuple[str, ...] = RATE_OPS_PUBLISHER_PUSH_PATHS,
    independent_pr: tuple[str, ...] = RATE_OPS_INDEPENDENT_PR_PATHS,
    independent_push: tuple[str, ...] = RATE_OPS_INDEPENDENT_PUSH_PATHS,
) -> None:
    expected_publisher = (rate_ops_trigger_event("pull_request", publisher_pr)
                          + rate_ops_trigger_event("push", publisher_push)
                          + "  workflow_dispatch:\n")
    expected_independent = (rate_ops_trigger_event("pull_request", independent_pr)
                            + rate_ops_trigger_event("push", independent_push))
    for label, content, expected in (
        ("publisher", publisher, expected_publisher),
        ("independent", independent, expected_independent),
    ):
        if rate_ops_trigger_header(content) != expected:
            raise SystemExit("rate-limit-operations " + label
                             + " exact event trigger inventory drift")


def replace_rate_ops_trigger_header(content: str, original: str, replacement: str) -> str:
    old = "\non:\n" + original + "\npermissions:\n"
    if content.count(old) != 1 or original == replacement:
        raise SystemExit("rate-limit-operations trigger negative fixture unreachable")
    return content.replace(old, "\non:\n" + replacement + "\npermissions:\n", 1)


def rate_ops_trigger_matrix_negatives(publisher: str, independent: str) -> None:
    def must_reject(p: str, i: str) -> None:
        try:
            rate_ops_validate_trigger_matrix(p, i)
        except SystemExit:
            return
        raise SystemExit("rate-limit-operations accepted event trigger mutation")

    omissions = additions = 0
    cases = (
        ("publisher", "pull_request", RATE_OPS_PUBLISHER_PR_PATHS),
        ("publisher", "push", RATE_OPS_PUBLISHER_PUSH_PATHS),
        ("independent", "pull_request", RATE_OPS_INDEPENDENT_PR_PATHS),
        ("independent", "push", RATE_OPS_INDEPENDENT_PUSH_PATHS),
    )
    for label, event, paths in cases:
        original = publisher if label == "publisher" else independent
        header = rate_ops_trigger_header(original)
        block = rate_ops_trigger_event(event, paths)
        if header.count(block) != 1:
            raise SystemExit("rate-limit-operations trigger event fixture ambiguous")
        for index in range(len(paths)):
            shorter = paths[:index] + paths[index + 1:]
            mutated = replace_rate_ops_trigger_header(
                original, header, header.replace(block, rate_ops_trigger_event(event, shorter), 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            omissions += 1
        first = '      - "' + paths[0] + '"\n'
        for addition in (
            '      - "unreviewed/**"\n', '      - unreviewed/**\n',
            first, '      - ' + paths[0] + '\n',
        ):
            mutated_block = block.replace(first, first + addition, 1)
            mutated = replace_rate_ops_trigger_header(
                original, header, header.replace(block, mutated_block, 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            additions += 1

    shortened = 0
    for field, paths in (
        ("publisher_pr", RATE_OPS_PUBLISHER_PR_PATHS),
        ("publisher_push", RATE_OPS_PUBLISHER_PUSH_PATHS),
        ("independent_pr", RATE_OPS_INDEPENDENT_PR_PATHS),
        ("independent_push", RATE_OPS_INDEPENDENT_PUSH_PATHS),
    ):
        try:
            rate_ops_validate_trigger_matrix(publisher, independent, **{field: paths[:-1]})
        except SystemExit:
            shortened += 1
        else:
            raise SystemExit("rate-limit-operations accepted shortened trigger inventory")

    p_header, i_header = rate_ops_trigger_header(publisher), rate_ops_trigger_header(independent)
    topology = (
        (replace_rate_ops_trigger_header(
            publisher, p_header, p_header.replace("  workflow_dispatch:\n", "", 1)), independent),
        (replace_rate_ops_trigger_header(
            publisher, p_header, p_header.replace(
                "  workflow_dispatch:\n",
                "  schedule:\n    - cron: '0 0 * * *'\n  workflow_dispatch:\n", 1)), independent),
        (publisher, replace_rate_ops_trigger_header(
            independent, i_header, i_header + "  workflow_dispatch:\n")),
    )
    for p, i in topology:
        must_reject(p, i)
    print("PASS: rate-limit-operations exact trigger matrix: "
          + str(omissions) + " omissions, " + str(additions)
          + " additions/duplicates, " + str(shortened)
          + " shortened inventories, " + str(len(topology)) + " event topology negatives")


def policy(source: str) -> None:
    for marker in REQUIRED:
        if marker not in source:
            raise AssertionError("rate-limit publisher policy missing: " + marker[:70])
    if source.count(CHECKOUT) != 2 or source.count(SETUP) != 2:
        raise AssertionError("rate-limit immutable Action count drift")
    if source.count('test -z "$(git status --porcelain)"') != 3:
        raise AssertionError("rate-limit clean worktree boundary count drift")
    if "actions/checkout@v4" in source or "actions/setup-python@v5" in source:
        raise AssertionError("rate-limit floating Action regression")

def mutations(source: str) -> None:
    for index, marker in enumerate(REQUIRED):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE_TEST", 1)
        if changed == source:
            raise AssertionError("rate-limit mutation unreachable: " + str(index))
        try:
            policy(changed)
        except AssertionError:
            continue
        raise AssertionError("rate-limit accepted source mutation: " + str(index))
    print(f"PASS: rate-limit publisher source mutations ({len(REQUIRED)} cases)")

def identity(source: str, title: str, writer: bool) -> None:
    shell = step(source, title)
    if writer:
        shell = shell.split("git fetch origin so", 1)[0]
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
    with tempfile.TemporaryDirectory(prefix="rate-limit-operations-identity-") as temp:
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
                raise AssertionError("rate-limit event/base/ref/SHA runtime drift: " +
                                     str((title, event, ref, result.returncode)))
    print(f"PASS: rate-limit {title} identity shell runtime ({len(cases)} cases)")

def cas_runtime(source: str) -> None:
    """Execute the real blocker publisher commit/CAS shell in a disposable fake-Git sandbox."""
    shell = step(source, "Commit reconciled authority files")
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
elif args[:2] == ["ls-remote", "origin"]:
    print(os.environ["FAKE_REMOTE"] + "\\trefs/heads/so")
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
        with tempfile.TemporaryDirectory(prefix="rate-limit-operations-cas-") as tmp:
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
                raise AssertionError(f"rate-limit operations CAS {label}: unexpected exit {result.returncode}: {result.stderr[-100:]}")
            if sum(line == "push origin HEAD:so" for line in calls) != pushes:
                raise AssertionError("rate-limit operations CAS pushed on stale/no-op/invalid source: " + label)
            if label == "noop" and any(line.startswith("commit ") for line in calls):
                raise AssertionError("rate-limit operations no-op committed")
    print(f"PASS: rate-limit operations actual publisher CAS/no-op shell ({len(cases)} cases)")


def main() -> None:
    publisher, independent = read(PUBLISHER), read(INDEPENDENT)
    for marker in (PUBLISHER, INDEPENDENT, SELF, CHECKOUT, SETUP,
                   "persist-credentials: false", "contents: read",
                   'test "$(git rev-parse HEAD)" = "$expected"',
                   'test -z "$(git status --porcelain)"'):
        if marker not in independent:
            raise AssertionError("rate-limit independent CI reachability drift: " + marker)
    reviewed_negatives(publisher, independent)
    rate_ops_validate_trigger_matrix(publisher, independent)
    rate_ops_trigger_matrix_negatives(publisher, independent)
    policy(publisher)
    mutations(publisher)
    identity(publisher, "Confirm exact clean PR authority source", False)
    identity(publisher, "Confirm exact clean authority source", True)
    cas_runtime(publisher)
    print("PASS: rate-limit exact-source read-only proof; production evidence generated: false")

if __name__ == "__main__":
    main()
