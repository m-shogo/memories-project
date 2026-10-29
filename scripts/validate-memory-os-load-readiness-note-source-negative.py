#!/usr/bin/env python3
"""Read-only source and actual PR/writer identity negatives for load readiness load."""
from __future__ import annotations
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-load-readiness-note.yml"
INDEPENDENT = ".github/workflows/load-readiness-note-source-negative.yml"
SELF = "scripts/validate-memory-os-load-readiness-note-source-negative.py"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
REVIEWED_PUBLISHER = "c8fc9e7d7c3ebb6f8d45b376e82f2e268a0272a7"
REVIEWED_INDEPENDENT = "096a142eba3027a2c01e343996739741fac479b0"

def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def require_reviewed_source(content: str, expected: str, label: str) -> None:
    if blob(content) != expected:
        raise AssertionError("load readiness " + label + " complete Git blob drift")

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
        raise AssertionError("load readiness reviewed Git blob accepted synthetic source drift: " + label)
    print("PASS: load readiness publisher and independent CI complete Git blob source negatives (2 cases)")

def read(path: str) -> str:
    p = ROOT / path
    if p.is_symlink() or not p.is_file() or p.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise AssertionError("load readiness source missing/substituted: " + path)
    return p.read_text(encoding="utf-8")

def step(source: str, title: str) -> str:
    marker = "      - name: " + title + "\n"
    if source.count(marker) != 1:
        raise AssertionError("load readiness step missing: " + title)
    start = source.index("        run: |\n", source.index(marker)) + len("        run: |\n")
    boundaries = [source.find(marker, start) for marker in ("\n      - name:", "\n  reconcile:", "\n  validate-pr:")]
    end = min((index for index in boundaries if index >= 0), default=len(source))
    lines = source[start:end].splitlines()
    if any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("load readiness indentation drift")
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
LOAD_READINESS_PUBLISHER_PR_PATHS = (
    ".github/workflows/reconcile-load-readiness-note.yml",
    "scripts/reconcile-memory-os-load-readiness-note.py",
    "scripts/validate-memory-os-load-readiness-note-reconcile-negative.py",
    "scripts/validate-memory-os-load.py",
    "scripts/validate-memory-os-operability.py",
    "contracts/operations/load-test-scenario-contract.v1.json",
    "contracts/operations/production-operability-status.json",
)

LOAD_READINESS_PUBLISHER_PUSH_PATHS = (
    ".github/workflows/reconcile-load-readiness-note.yml",
    "scripts/reconcile-memory-os-load-readiness-note.py",
    "scripts/validate-memory-os-load-readiness-note-reconcile-negative.py",
    "scripts/validate-memory-os-load.py",
    "scripts/validate-memory-os-operability.py",
    "contracts/operations/load-test-scenario-contract.v1.json",
    "contracts/operations/production-operability-status.json",
)

LOAD_READINESS_INDEPENDENT_PR_PATHS = (
    ".github/workflows/reconcile-load-readiness-note.yml",
    ".github/workflows/load-readiness-note-source-negative.yml",
    "scripts/validate-memory-os-load-readiness-note-source-negative.py",
)

LOAD_READINESS_INDEPENDENT_PUSH_PATHS = (
    ".github/workflows/reconcile-load-readiness-note.yml",
    ".github/workflows/load-readiness-note-source-negative.yml",
    "scripts/validate-memory-os-load-readiness-note-source-negative.py",
)

def load_readiness_trigger_event(event: str, paths: tuple[str, ...]) -> str:
    return ("  " + event + ":\n    branches:\n      - so\n    paths:\n"
            + "".join('      - "' + path + '"\n' for path in paths))


def load_readiness_trigger_header(content: str) -> str:
    # Exact, ordered event header: reject unknown, unquoted, duplicate and
    # unexpected event paths instead of depending only on a Git blob digest.
    if content.count("\non:\n") != 1 or content.count("\npermissions:\n") != 1:
        raise SystemExit("load-readiness trigger section ambiguous")
    return content.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]


def load_readiness_validate_trigger_matrix(
    publisher: str, independent: str,
    publisher_pr: tuple[str, ...] = LOAD_READINESS_PUBLISHER_PR_PATHS,
    publisher_push: tuple[str, ...] = LOAD_READINESS_PUBLISHER_PUSH_PATHS,
    independent_pr: tuple[str, ...] = LOAD_READINESS_INDEPENDENT_PR_PATHS,
    independent_push: tuple[str, ...] = LOAD_READINESS_INDEPENDENT_PUSH_PATHS,
) -> None:
    expected_publisher = (load_readiness_trigger_event("pull_request", publisher_pr)
                          + load_readiness_trigger_event("push", publisher_push)
                          + "  workflow_dispatch:\n")
    expected_independent = (load_readiness_trigger_event("pull_request", independent_pr)
                            + load_readiness_trigger_event("push", independent_push))
    for label, content, expected in (
        ("publisher", publisher, expected_publisher),
        ("independent", independent, expected_independent),
    ):
        if load_readiness_trigger_header(content) != expected:
            raise SystemExit("load-readiness " + label
                             + " exact event trigger inventory drift")


def replace_load_readiness_trigger_header(content: str, original: str, replacement: str) -> str:
    old = "\non:\n" + original + "\npermissions:\n"
    if content.count(old) != 1 or original == replacement:
        raise SystemExit("load-readiness trigger negative fixture unreachable")
    return content.replace(old, "\non:\n" + replacement + "\npermissions:\n", 1)


def load_readiness_trigger_matrix_negatives(publisher: str, independent: str) -> None:
    def must_reject(p: str, i: str) -> None:
        try:
            load_readiness_validate_trigger_matrix(p, i)
        except SystemExit:
            return
        raise SystemExit("load-readiness accepted event trigger mutation")

    omissions = additions = 0
    cases = (
        ("publisher", "pull_request", LOAD_READINESS_PUBLISHER_PR_PATHS),
        ("publisher", "push", LOAD_READINESS_PUBLISHER_PUSH_PATHS),
        ("independent", "pull_request", LOAD_READINESS_INDEPENDENT_PR_PATHS),
        ("independent", "push", LOAD_READINESS_INDEPENDENT_PUSH_PATHS),
    )
    for label, event, paths in cases:
        original = publisher if label == "publisher" else independent
        header = load_readiness_trigger_header(original)
        block = load_readiness_trigger_event(event, paths)
        if header.count(block) != 1:
            raise SystemExit("load-readiness trigger event fixture ambiguous")
        for index in range(len(paths)):
            shorter = paths[:index] + paths[index + 1:]
            mutated = replace_load_readiness_trigger_header(
                original, header, header.replace(block, load_readiness_trigger_event(event, shorter), 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            omissions += 1
        first = '      - "' + paths[0] + '"\n'
        for addition in (
            '      - "unreviewed/**"\n', '      - unreviewed/**\n',
            first, '      - ' + paths[0] + '\n',
        ):
            mutated_block = block.replace(first, first + addition, 1)
            mutated = replace_load_readiness_trigger_header(
                original, header, header.replace(block, mutated_block, 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            additions += 1

    shortened = 0
    for field, paths in (
        ("publisher_pr", LOAD_READINESS_PUBLISHER_PR_PATHS),
        ("publisher_push", LOAD_READINESS_PUBLISHER_PUSH_PATHS),
        ("independent_pr", LOAD_READINESS_INDEPENDENT_PR_PATHS),
        ("independent_push", LOAD_READINESS_INDEPENDENT_PUSH_PATHS),
    ):
        try:
            load_readiness_validate_trigger_matrix(publisher, independent, **{field: paths[:-1]})
        except SystemExit:
            shortened += 1
        else:
            raise SystemExit("load-readiness accepted shortened trigger inventory")

    p_header, i_header = load_readiness_trigger_header(publisher), load_readiness_trigger_header(independent)
    topology = (
        (replace_load_readiness_trigger_header(
            publisher, p_header, p_header.replace("  workflow_dispatch:\n", "", 1)), independent),
        (replace_load_readiness_trigger_header(
            publisher, p_header, p_header.replace(
                "  workflow_dispatch:\n",
                "  schedule:\n    - cron: '0 0 * * *'\n  workflow_dispatch:\n", 1)), independent),
        (publisher, replace_load_readiness_trigger_header(
            independent, i_header, i_header + "  workflow_dispatch:\n")),
    )
    for p, i in topology:
        must_reject(p, i)
    print("PASS: load-readiness exact trigger matrix: "
          + str(omissions) + " omissions, " + str(additions)
          + " additions/duplicates, " + str(shortened)
          + " shortened inventories, " + str(len(topology)) + " event topology negatives")



def validate_yaml_root_permission(publisher: str, independent: str) -> None:
    """Pin reviewed YAML root mapping and read-only permission leaves."""
    for label, value, roots in (
        ("publisher", publisher, ["name: Reconcile Load Readiness Note",
                                  "on:", "permissions:", "concurrency:", "jobs:"]),
        ("independent", independent, ["name: Load Readiness Note Source Negative",
                                      "on:", "permissions:", "jobs:"]),
    ):
        actual = [line for line in value.splitlines()
                  if line.strip() and not line[0].isspace()
                  and not line.lstrip().startswith("#")]
        if actual != roots:
            raise AssertionError("load-readiness " + label + " root YAML key shadow drift")
        if value.count("\npermissions:\n") != 1:
            raise AssertionError("load-readiness " + label + " permission boundary drift")
        leaves = []
        for line in value.split("\npermissions:\n", 1)[1].splitlines():
            if line.strip() and not line[0].isspace():
                break
            if line.strip() and not line.lstrip().startswith("#"):
                leaves.append(line)
        if leaves != ["  contents: read"]:
            raise AssertionError("load-readiness " + label + " permission leaf shadow drift")


def yaml_root_permission_negatives(publisher: str, independent: str) -> None:
    """Prove twelve exact-diagnostic YAML root and permission shadow mutations."""
    validate_yaml_root_permission(publisher, independent)
    count = 0
    for label, value, other, is_publisher in (
        ("publisher", publisher, independent, True),
        ("independent", independent, publisher, False),
    ):
        cases = [
            (mutation, value + "\n" + suffix, "root YAML key shadow drift")
            for mutation, suffix in (
                ("spaced on", "on :\n  issues:\n"),
                ("quoted on", "'on':\n  issues:\n"),
                ("spaced jobs", "jobs : {}\n"),
                ("quoted jobs", "'jobs': {}\n"),
            )
        ]
        marker = "\npermissions:\n  contents: read\n"
        if value.count(marker) != 1:
            raise AssertionError("load-readiness " + label + " permission fixture anchor drift")
        for mutation, leaf in (
            ("spaced contents", "  contents : write\n"),
            ("quoted contents", "  'contents': write\n"),
        ):
            cases.append((mutation, value.replace(marker, marker + leaf, 1),
                          "permission leaf shadow drift"))
        for mutation, changed, diagnostic in cases:
            if changed == value:
                raise AssertionError("load-readiness unchanged YAML fixture: " + mutation)
            try:
                if is_publisher:
                    validate_yaml_root_permission(changed, other)
                else:
                    validate_yaml_root_permission(other, changed)
            except AssertionError as exc:
                expected = "load-readiness " + label + " " + diagnostic
                if str(exc) != expected:
                    raise AssertionError("load-readiness wrong YAML diagnostic: "
                                         + label + " " + mutation + ": " + str(exc)) from exc
            else:
                raise AssertionError("load-readiness accepted YAML shadow: " + label + " " + mutation)
            count += 1
    if count != 12:
        raise AssertionError("load-readiness YAML negative inventory drift")
    print("PASS: load-readiness root/permission YAML authority (12 exact-diagnostic negatives)")



def load_readiness_concurrency_authority(publisher: str) -> None:
    """Pin reviewed event-scoped noncancelling publisher serialization."""
    marker = "\nconcurrency:\n"
    if publisher.count(marker) != 1 or publisher.count("\njobs:\n") != 1:
        raise SystemExit("load-readiness publisher concurrency authority drift")
    observed = publisher.split(marker, 1)[1].split("\njobs:\n", 1)[0]
    expected = ("  group: reconcile-load-readiness-note-" + chr(36)
                + "{{ github.event_name }}-" + chr(36)
                + "{{ github.event.pull_request.number || 'so' }}\n"
                + "  cancel-in-progress: false\n")
    if observed != expected:
        raise SystemExit("load-readiness publisher concurrency authority drift")


def load_readiness_concurrency_negatives(publisher: str) -> None:
    """Reject twelve effective YAML concurrency override mutations."""
    marker = "\nconcurrency:\n"
    original = ("  group: reconcile-load-readiness-note-" + chr(36)
                + "{{ github.event_name }}-" + chr(36)
                + "{{ github.event.pull_request.number || 'so' }}\n"
                + "  cancel-in-progress: false\n")
    anchor = marker + original + "\njobs:\n"
    if publisher.count(anchor) != 1:
        raise SystemExit("load-readiness concurrency fixture anchor drift")
    group = original.splitlines(keepends=True)[0]
    cancel = "  cancel-in-progress: false\n"
    cases = (
        ("changed group", original.replace(group, "  group: unreviewed\n", 1)),
        ("missing group", original.replace(group, "", 1)),
        ("duplicate group", original.replace(group, group + "  group: unreviewed\n", 1)),
        ("quoted group", original.replace(group, group + "  'group': unreviewed\n", 1)),
        ("spaced group", original.replace(group, group + "  group : unreviewed\n", 1)),
        ("extra group leaf", original.replace(group, group + "  unreviewed: true\n", 1)),
        ("enabled cancellation", original.replace(cancel, "  cancel-in-progress: true\n", 1)),
        ("missing cancellation", original.replace(cancel, "", 1)),
        ("duplicate cancellation", original.replace(cancel, cancel + "  cancel-in-progress: true\n", 1)),
        ("quoted cancellation", original.replace(cancel, cancel + "  'cancel-in-progress': true\n", 1)),
        ("spaced cancellation", original.replace(cancel, cancel + "  cancel-in-progress : true\n", 1)),
        ("extra cancellation leaf", original.replace(cancel, cancel + "  unreviewed: true\n", 1)),
    )
    if len(cases) != 12:
        raise SystemExit("load-readiness concurrency negative inventory drift")
    load_readiness_concurrency_authority(publisher)
    for name, replacement in cases:
        altered = publisher.replace(anchor, marker + replacement + "\njobs:\n", 1)
        if altered == publisher:
            raise SystemExit("load-readiness unchanged concurrency fixture: " + name)
        try:
            load_readiness_concurrency_authority(altered)
        except SystemExit as exc:
            if str(exc) != "load-readiness publisher concurrency authority drift":
                raise SystemExit("load-readiness wrong concurrency diagnostic: "
                                 + name + ": " + str(exc)) from exc
        else:
            raise SystemExit("load-readiness accepted concurrency mutation: " + name)
    print("PASS: load-readiness publisher concurrency (12 exact-diagnostic negatives)")

def policy(source: str) -> None:
    for marker in REQUIRED:
        if marker not in source:
            raise AssertionError("load readiness policy missing: " + marker[:60])
    if source.count(CHECKOUT) != 2 or source.count(SETUP) != 2:
        raise AssertionError("load readiness immutable Actions drift")
    if source.count('test -z "$(git status --porcelain)"') != 3:
        raise AssertionError("load readiness three clean worktree boundaries drift")
    if "actions/checkout@v4" in source or "actions/setup-python@v5" in source:
        raise AssertionError("load readiness floating Action regression")

def mutations(source: str) -> None:
    for index, marker in enumerate(REQUIRED):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE_TEST", 1)
        if changed == source:
            raise AssertionError("load readiness mutation unreachable: " + str(index))
        try:
            policy(changed)
        except AssertionError:
            continue
        raise AssertionError("load readiness accepted source mutation: " + str(index))
    print(f"PASS: load readiness source mutations ({len(REQUIRED)} cases)")

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
                raise AssertionError("load readiness event/base/ref/SHA drift: " + str((title, event, ref, result.returncode)))
    print(f"PASS: load readiness {title} identity shell runtime ({len(cases)} cases)")

def main() -> None:
    publisher = read(PUBLISHER)
    independent = read(INDEPENDENT)
    for marker in (PUBLISHER, INDEPENDENT, SELF, CHECKOUT, SETUP,
                   "persist-credentials: false", "contents: read",
                   'test "$(git rev-parse HEAD)" = "$expected"',
                   'test -z "$(git status --porcelain)"'):
        if marker not in independent:
            raise AssertionError("load readiness independent CI reachability drift: " + marker)
    reviewed_blob_negatives(publisher, independent)
    policy(publisher)
    load_readiness_validate_trigger_matrix(publisher, independent)
    load_readiness_trigger_matrix_negatives(publisher, independent)
    validate_yaml_root_permission(publisher, independent)
    yaml_root_permission_negatives(publisher, independent)
    load_readiness_concurrency_authority(publisher)
    load_readiness_concurrency_negatives(publisher)
    mutations(publisher)
    identity(publisher, "Reconcile read-only PR authority", False)
    identity(publisher, "Capture exact clean source", True)
    print("PASS: load readiness exact-source read-only proof; production evidence generated: false")

if __name__ == "__main__":
    main()
