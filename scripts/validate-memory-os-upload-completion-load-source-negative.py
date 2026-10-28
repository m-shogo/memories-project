#!/usr/bin/env python3
"""Read-only source and actual PR/writer identity negatives for upload completion load."""
from __future__ import annotations
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-upload-completion-load-authority.yml"
INDEPENDENT = ".github/workflows/upload-completion-load-source-negative.yml"
SELF = "scripts/validate-memory-os-upload-completion-load-source-negative.py"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
REVIEWED_PUBLISHER = "d8bc882a59eb452d4fdeebfb1dad77fe1cac2adf"
REVIEWED_INDEPENDENT = "2973a31b37ada2455f92a04736612b9484a6a422"

def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def require_reviewed_source(content: str, expected: str, label: str) -> None:
    if blob(content) != expected:
        raise AssertionError("upload completion " + label + " complete Git blob drift")

def reviewed_blob_negatives(publisher: str, independent: str) -> None:
    require_reviewed_source(publisher, REVIEWED_PUBLISHER, "publisher")
    require_reviewed_source(independent, REVIEWED_INDEPENDENT, "independent CI")
    for label, original, expected in (
        ("publisher", publisher, REVIEWED_PUBLISHER),
        ("independent CI", independent, REVIEWED_INDEPENDENT),
    ):
        try:
            require_reviewed_source(original + "\n# synthetic source drift\n", expected, label)
        except AssertionError:
            continue
        raise AssertionError("upload completion reviewed Git blob accepted synthetic source drift: " + label)
    print("PASS: upload completion publisher and independent CI complete Git blob source negatives (2 cases)")

def read(path: str) -> str:
    p = ROOT / path
    if p.is_symlink() or not p.is_file() or p.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise AssertionError("upload completion source missing/substituted: " + path)
    return p.read_text(encoding="utf-8")

def step(source: str, title: str) -> str:
    marker = "      - name: " + title + "\n"
    if source.count(marker) != 1:
        raise AssertionError("upload completion step missing: " + title)
    start = source.index("        run: |\n", source.index(marker)) + len("        run: |\n")
    boundaries = [source.find(marker, start) for marker in ("\n      - name:", "\n  reconcile:", "\n  validate-pr:")]
    end = min((index for index in boundaries if index >= 0), default=len(source))
    lines = source[start:end].splitlines()
    if any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("upload completion indentation drift")
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"

REQUIRED = (
    "if: github.event_name == 'pull_request' && github.base_ref == 'so'",
    "github.ref == 'refs/heads/so'",
    "persist-credentials: false",
    "persist-credentials: true",
    'test "${GITHUB_EVENT_NAME:-}" = "pull_request"',
    'test "${GITHUB_BASE_REF:-}" = "so"',
    '[[ "$PR_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]',
    'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"',
    'test "${GITHUB_REF:-}" = "refs/heads/so"',
    '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
    'git fetch origin so',
    'git push origin HEAD:so',
)
UPLOAD_COMPLETION_PUBLISHER_PR_PATHS = (
    ".github/workflows/reconcile-upload-completion-load-authority.yml",
    "scripts/reconcile-memory-os-deletion-prefence-upload-completion.py",
    "scripts/validate-memory-os-deletion-prefence-upload-completion-reconcile-negative.py",
    "scripts/validate-memory-os-deletion-prefence-upload-completion.py",
    "scripts/reconcile-memory-os-upload-completion-load-authority.py",
    "scripts/validate-memory-os-upload-completion-load-reconcile-negative.py",
    "scripts/validate-memory-os-load.py",
    "scripts/validate-memory-os-operability.py",
    "contracts/operations/deletion-prefence-upload-completion-contract.v1.json",
    "docs/fixtures/memory-os-operability/deletion-prefence-upload-completion-results.sample.v1.json",
)

UPLOAD_COMPLETION_PUBLISHER_PUSH_PATHS = (
    ".github/workflows/reconcile-upload-completion-load-authority.yml",
    "scripts/reconcile-memory-os-deletion-prefence-upload-completion.py",
    "scripts/validate-memory-os-deletion-prefence-upload-completion-reconcile-negative.py",
    "scripts/validate-memory-os-deletion-prefence-upload-completion.py",
    "scripts/reconcile-memory-os-upload-completion-load-authority.py",
    "scripts/validate-memory-os-upload-completion-load-reconcile-negative.py",
    "scripts/validate-memory-os-load.py",
    "scripts/validate-memory-os-operability.py",
    "contracts/operations/deletion-prefence-upload-completion-contract.v1.json",
    "docs/fixtures/memory-os-operability/deletion-prefence-upload-completion-results.sample.v1.json",
)

UPLOAD_COMPLETION_INDEPENDENT_PR_PATHS = (
    ".github/workflows/reconcile-upload-completion-load-authority.yml",
    ".github/workflows/upload-completion-load-source-negative.yml",
    "scripts/validate-memory-os-upload-completion-load-source-negative.py",
)

UPLOAD_COMPLETION_INDEPENDENT_PUSH_PATHS = (
    ".github/workflows/reconcile-upload-completion-load-authority.yml",
    ".github/workflows/upload-completion-load-source-negative.yml",
    "scripts/validate-memory-os-upload-completion-load-source-negative.py",
)

def upload_completion_trigger_event(event: str, paths: tuple[str, ...]) -> str:
    return ("  " + event + ":\n    branches:\n      - so\n    paths:\n"
            + "".join('      - "' + path + '"\n' for path in paths))


def upload_completion_trigger_header(content: str) -> str:
    # Exact, ordered event header: reject unknown, unquoted, duplicate and
    # unexpected event paths instead of depending only on a Git blob digest.
    if content.count("\non:\n") != 1 or content.count("\npermissions:\n") != 1:
        raise SystemExit("upload-completion-load trigger section ambiguous")
    return content.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]


def upload_completion_validate_trigger_matrix(
    publisher: str, independent: str,
    publisher_pr: tuple[str, ...] = UPLOAD_COMPLETION_PUBLISHER_PR_PATHS,
    publisher_push: tuple[str, ...] = UPLOAD_COMPLETION_PUBLISHER_PUSH_PATHS,
    independent_pr: tuple[str, ...] = UPLOAD_COMPLETION_INDEPENDENT_PR_PATHS,
    independent_push: tuple[str, ...] = UPLOAD_COMPLETION_INDEPENDENT_PUSH_PATHS,
) -> None:
    expected_publisher = (upload_completion_trigger_event("push", publisher_push)
                          + upload_completion_trigger_event("pull_request", publisher_pr)
                          + "  workflow_dispatch:\n")
    expected_independent = (upload_completion_trigger_event("pull_request", independent_pr)
                            + upload_completion_trigger_event("push", independent_push))
    for label, content, expected in (
        ("publisher", publisher, expected_publisher),
        ("independent", independent, expected_independent),
    ):
        if upload_completion_trigger_header(content) != expected:
            raise SystemExit("upload-completion-load " + label
                             + " exact event trigger inventory drift")
    upload_completion_validate_yaml_root_permissions(publisher, independent)



def upload_completion_validate_yaml_root_permissions(
    publisher: str, independent: str
) -> None:
    """Pin effective CI root and read-only permission mapping."""
    for label, content, expected_roots in (
        ("publisher", publisher, [
            "name: Reconcile Upload Completion Load Authority", "on:",
            "permissions:", "concurrency:", "jobs:",
        ]),
        ("independent", independent, [
            "name: Upload Completion Load Source Negative", "on:",
            "permissions:", "jobs:",
        ]),
    ):
        roots = [
            line for line in content.splitlines()
            if line.strip() and not line[0].isspace()
            and not line.lstrip().startswith("#")
        ]
        if roots != expected_roots:
            raise SystemExit("upload-completion-load " + label + " root YAML key shadow drift")
        if content.count("\npermissions:\n") != 1:
            raise SystemExit("upload-completion-load " + label + " permission leaf shadow drift")
        permission_rows = []
        for line in content.split("\npermissions:\n", 1)[1].splitlines():
            if line.strip() and not line[0].isspace():
                break
            if line.strip() and not line.lstrip().startswith("#"):
                permission_rows.append(line)
        if permission_rows != ["  contents: read"]:
            raise SystemExit("upload-completion-load " + label + " permission leaf shadow drift")


def upload_completion_yaml_shadow_negatives(publisher: str, independent: str) -> None:
    total = 0
    for label, content in (("publisher", publisher), ("independent", independent)):
        cases = []
        for name, suffix in (
            ("spaced on", "on :\n  issues:\n"),
            ("quoted on", "'on':\n  issues:\n"),
            ("spaced permissions", "permissions :\n  contents: write\n"),
            ("spaced jobs", "jobs : {}\n"),
        ):
            cases.append((name, content + "\n" + suffix, "root YAML key shadow drift"))
        anchor = "permissions:\n  contents: read\n"
        if content.count(anchor) != 1:
            raise SystemExit("upload-completion-load " + label
                             + " permission mutation anchor drift")
        for name, extra in (
            ("spaced contents", "  contents : write\n"),
            ("quoted contents", "  'contents': write\n"),
        ):
            cases.append((name, content.replace(anchor, anchor + extra, 1),
                          "permission leaf shadow drift"))
        for name, altered, diagnostic in cases:
            if altered == content:
                raise SystemExit("upload-completion-load YAML fixture unchanged: " + name)
            try:
                if label == "publisher":
                    upload_completion_validate_trigger_matrix(altered, independent)
                else:
                    upload_completion_validate_trigger_matrix(publisher, altered)
            except SystemExit as exc:
                expected = "upload-completion-load " + label + " " + diagnostic
                if str(exc) != expected:
                    raise SystemExit(
                        "upload-completion-load YAML wrong diagnostic: "
                        + label + "/" + name + ": " + str(exc)
                    ) from exc
            else:
                raise SystemExit("upload-completion-load accepted YAML shadow: "
                                 + label + "/" + name)
            total += 1
    if total != 12:
        raise SystemExit("upload-completion-load YAML fixture count drift")
    print("PASS: upload completion publisher/independent YAML root/permission (12 exact-diagnostic negatives)")


def replace_upload_completion_trigger_header(content: str, original: str, replacement: str) -> str:
    old = "\non:\n" + original + "\npermissions:\n"
    if content.count(old) != 1 or original == replacement:
        raise SystemExit("upload-completion-load trigger negative fixture unreachable")
    return content.replace(old, "\non:\n" + replacement + "\npermissions:\n", 1)


def upload_completion_trigger_matrix_negatives(publisher: str, independent: str) -> None:
    def must_reject(p: str, i: str) -> None:
        try:
            upload_completion_validate_trigger_matrix(p, i)
        except SystemExit:
            return
        raise SystemExit("upload-completion-load accepted event trigger mutation")

    omissions = additions = 0
    cases = (
        ("publisher", "pull_request", UPLOAD_COMPLETION_PUBLISHER_PR_PATHS),
        ("publisher", "push", UPLOAD_COMPLETION_PUBLISHER_PUSH_PATHS),
        ("independent", "pull_request", UPLOAD_COMPLETION_INDEPENDENT_PR_PATHS),
        ("independent", "push", UPLOAD_COMPLETION_INDEPENDENT_PUSH_PATHS),
    )
    for label, event, paths in cases:
        original = publisher if label == "publisher" else independent
        header = upload_completion_trigger_header(original)
        block = upload_completion_trigger_event(event, paths)
        if header.count(block) != 1:
            raise SystemExit("upload-completion-load trigger event fixture ambiguous")
        for index in range(len(paths)):
            shorter = paths[:index] + paths[index + 1:]
            mutated = replace_upload_completion_trigger_header(
                original, header, header.replace(block, upload_completion_trigger_event(event, shorter), 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            omissions += 1
        first = '      - "' + paths[0] + '"\n'
        for addition in (
            '      - "unreviewed/**"\n', '      - unreviewed/**\n',
            first, '      - ' + paths[0] + '\n',
        ):
            mutated_block = block.replace(first, first + addition, 1)
            mutated = replace_upload_completion_trigger_header(
                original, header, header.replace(block, mutated_block, 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            additions += 1

    shortened = 0
    for field, paths in (
        ("publisher_pr", UPLOAD_COMPLETION_PUBLISHER_PR_PATHS),
        ("publisher_push", UPLOAD_COMPLETION_PUBLISHER_PUSH_PATHS),
        ("independent_pr", UPLOAD_COMPLETION_INDEPENDENT_PR_PATHS),
        ("independent_push", UPLOAD_COMPLETION_INDEPENDENT_PUSH_PATHS),
    ):
        try:
            upload_completion_validate_trigger_matrix(publisher, independent, **{field: paths[:-1]})
        except SystemExit:
            shortened += 1
        else:
            raise SystemExit("upload-completion-load accepted shortened trigger inventory")

    p_header, i_header = upload_completion_trigger_header(publisher), upload_completion_trigger_header(independent)
    topology = (
        (replace_upload_completion_trigger_header(
            publisher, p_header, p_header.replace("  workflow_dispatch:\n", "", 1)), independent),
        (replace_upload_completion_trigger_header(
            publisher, p_header, p_header.replace(
                "  workflow_dispatch:\n",
                "  schedule:\n    - cron: '0 0 * * *'\n  workflow_dispatch:\n", 1)), independent),
        (publisher, replace_upload_completion_trigger_header(
            independent, i_header, i_header + "  workflow_dispatch:\n")),
    )
    for p, i in topology:
        must_reject(p, i)
    print("PASS: upload-completion-load exact trigger matrix: "
          + str(omissions) + " omissions, " + str(additions)
          + " additions/duplicates, " + str(shortened)
          + " shortened inventories, " + str(len(topology)) + " event topology negatives")


def policy(source: str) -> None:
    for marker in REQUIRED:
        if marker not in source:
            raise AssertionError("upload completion policy missing: " + marker[:60])
    if source.count(CHECKOUT) != 2 or source.count(SETUP) != 2:
        raise AssertionError("upload completion immutable Actions drift")
    if source.count('test -z "$(git status --porcelain)"') != 3:
        raise AssertionError("upload completion three clean worktree boundaries drift")
    if "actions/checkout@v4" in source or "actions/setup-python@v5" in source:
        raise AssertionError("upload completion floating Action regression")

def mutations(source: str) -> None:
    for index, marker in enumerate(REQUIRED):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE_TEST", 1)
        if changed == source:
            raise AssertionError("upload completion mutation unreachable: " + str(index))
        try:
            policy(changed)
        except AssertionError:
            continue
        raise AssertionError("upload completion accepted source mutation: " + str(index))
    print(f"PASS: upload completion source mutations ({len(REQUIRED)} cases)")

def identity(source: str, title: str, writer: bool) -> None:
    shell = step(source, title)
    shell = shell.split('echo "SOURCE_SHA=', 1)[0] if writer else shell.split("python -m py_compile", 1)[0]
    head = "a" * 40
    if writer:
        cases = (("push", "", "refs/heads/so", "", head, True),
                 ("workflow_dispatch", "", "refs/heads/so", "", head, True),
                 ("schedule", "", "refs/heads/so", "", head, False),
                 ("pull_request", "", "refs/heads/so", "", head, False),
                 ("push", "", "refs/heads/main", "", head, False),
                 ("push", "", "refs/heads/so", "", "b" * 40, False),
                 ("push", "", "refs/heads/so", "", "A" * 40, False),
                 ("push", "", "refs/heads/so", "", "a" * 39, False))
    else:
        cases = (("pull_request", "so", "", head, "", True),
                 ("pull_request", "main", "", head, "", False),
                 ("push", "so", "", head, "", False),
                 ("pull_request", "so", "", "b" * 40, "", False),
                 ("pull_request", "so", "", "A" * 40, "", False),
                 ("pull_request", "so", "", "a" * 39, "", False))
    with tempfile.TemporaryDirectory(prefix="upload-completion-identity-") as temp:
        root = Path(temp)
        stub = root / "git"
        stub.write_text("#!/bin/sh\n"
                        "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"HEAD\" ]; then printf '" + head + "\\n'; exit 0; fi\n"
                        "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then exit 0; fi\n"
                        "exit 1\n", encoding="utf-8")
        stub.chmod(0o755)
        for event, base, ref, pr_sha, sha, allowed in cases:
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_EVENT_NAME=event, GITHUB_BASE_REF=base, GITHUB_REF=ref,
                       PR_HEAD_SHA=pr_sha, GITHUB_SHA=sha)
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != allowed:
                raise AssertionError("upload completion event/base/ref/SHA drift: " + str((title, event, ref, result.returncode)))
    print(f"PASS: upload completion {title} identity shell runtime ({len(cases)} cases)")

def main() -> None:
    publisher = read(PUBLISHER)
    independent = read(INDEPENDENT)
    for marker in (PUBLISHER, INDEPENDENT, SELF, CHECKOUT, SETUP,
                   "persist-credentials: false", "contents: read",
                   'test "$(git rev-parse HEAD)" = "$expected"',
                   'test -z "$(git status --porcelain)"'):
        if marker not in independent:
            raise AssertionError("upload completion independent CI reachability drift: " + marker)
    reviewed_blob_negatives(publisher, independent)
    policy(publisher)
    upload_completion_validate_trigger_matrix(publisher, independent)
    upload_completion_trigger_matrix_negatives(publisher, independent)
    upload_completion_yaml_shadow_negatives(publisher, independent)
    mutations(publisher)
    identity(publisher, "Validate exact PR-head upload completion authority", False)
    identity(publisher, "Capture exact source", True)
    print("PASS: upload completion exact-source read-only proof; production evidence generated: false")

if __name__ == "__main__":
    main()
