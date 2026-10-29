#!/usr/bin/env python3
"""Independent read-only observability-access authority source and runtime negatives."""
from __future__ import annotations
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-observability-access.yml"
INDEPENDENT = ".github/workflows/observability-access-source-negative.yml"
SELF = "scripts/validate-memory-os-observability-access-source-negative.py"
CHECKOUT = "uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
REVIEWED_PUBLISHER = "21753278254d4152e29519125f19db03eef6f5cf"
REVIEWED_INDEPENDENT = "fba513e1a0a8fe10d20fa5b08c589b70f43c38e8"

def read(path: str) -> str:
    p = ROOT / path
    if p.is_symlink() or not p.is_file():
        raise AssertionError("load missing source substituted: " + path)
    if p.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise AssertionError("load missing source escaped root")
    return p.read_text(encoding="utf-8")

def blob(s: str) -> str:
    data = s.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

REQUIRED = (
    "if: github.event_name == 'pull_request' && github.base_ref == 'so'",
    "if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'",
    "persist-credentials: false",
    "persist-credentials: true",
    'test "$' + '{GITHUB_EVENT_NAME:-}" = "pull_request"',
    'test "$' + '{GITHUB_BASE_REF:-}" = "so"',
    '[[ "$' + '{PR_HEAD_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"',
    'test "$' + '{GITHUB_REF:-}" = "refs/heads/so"',
    '[[ "$' + '{GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'test "$(git rev-parse HEAD)" = "$' + '{GITHUB_SHA:-}"',
    "git push origin HEAD:so",
)

OBSERVABILITY_PUBLISHER_PR_PATHS = (
    ".github/workflows/reconcile-observability-access.yml",
    "contracts/operations/observability-retention-access-contract.v1.json",
    "contracts/operations/observability-event-contract.v1.json",
    "contracts/operations/production-operability-status.json",
    "docs/runbooks/memory-os-observability-access.md",
    "scripts/validate-memory-os-observability.py",
    "scripts/validate-memory-os-observability-access.py",
    "scripts/validate-memory-os-observability-access-reconcile-negative.py",
    "scripts/validate-memory-os-operability.py",
    "scripts/validate-memory-os-entry-docs.py",
    "scripts/reconcile-memory-os-observability-access.py",
)

OBSERVABILITY_PUBLISHER_PUSH_PATHS = (
    ".github/workflows/reconcile-observability-access.yml",
    "contracts/operations/observability-retention-access-contract.v1.json",
    "contracts/operations/observability-event-contract.v1.json",
    "contracts/operations/production-operability-status.json",
    "docs/runbooks/memory-os-observability-access.md",
    "scripts/validate-memory-os-observability.py",
    "scripts/validate-memory-os-observability-access.py",
    "scripts/validate-memory-os-observability-access-reconcile-negative.py",
    "scripts/validate-memory-os-operability.py",
    "scripts/validate-memory-os-entry-docs.py",
    "scripts/reconcile-memory-os-observability-access.py",
)

OBSERVABILITY_INDEPENDENT_PR_PATHS = (
    ".github/workflows/reconcile-observability-access.yml",
    ".github/workflows/observability-access-source-negative.yml",
    "scripts/validate-memory-os-observability-access-source-negative.py",
)

OBSERVABILITY_INDEPENDENT_PUSH_PATHS = (
    ".github/workflows/reconcile-observability-access.yml",
    ".github/workflows/observability-access-source-negative.yml",
    "scripts/validate-memory-os-observability-access-source-negative.py",
)

def observability_trigger_event(event: str, paths: tuple[str, ...]) -> str:
    return ("  " + event + ":\n    branches:\n      - so\n    paths:\n"
            + "".join('      - "' + path + '"\n' for path in paths))


def observability_trigger_header(content: str) -> str:
    # Exact, ordered event header: reject unknown, unquoted, duplicate and
    # unexpected event paths instead of depending only on a Git blob digest.
    if content.count("\non:\n") != 1 or content.count("\npermissions:\n") != 1:
        raise SystemExit("observability-access trigger section ambiguous")
    return content.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]


def observability_validate_trigger_matrix(
    publisher: str, independent: str,
    publisher_pr: tuple[str, ...] = OBSERVABILITY_PUBLISHER_PR_PATHS,
    publisher_push: tuple[str, ...] = OBSERVABILITY_PUBLISHER_PUSH_PATHS,
    independent_pr: tuple[str, ...] = OBSERVABILITY_INDEPENDENT_PR_PATHS,
    independent_push: tuple[str, ...] = OBSERVABILITY_INDEPENDENT_PUSH_PATHS,
) -> None:
    expected_publisher = (observability_trigger_event("pull_request", publisher_pr)
                          + observability_trigger_event("push", publisher_push)
                          + "  workflow_dispatch:\n")
    expected_independent = (observability_trigger_event("pull_request", independent_pr)
                            + observability_trigger_event("push", independent_push))
    for label, content, expected in (
        ("publisher", publisher, expected_publisher),
        ("independent", independent, expected_independent),
    ):
        if observability_trigger_header(content) != expected:
            raise SystemExit("observability-access " + label
                             + " exact event trigger inventory drift")
    observability_validate_yaml_root_permissions(publisher, independent)



def observability_validate_yaml_root_permissions(
    publisher: str, independent: str
) -> None:
    """Pin effective CI root and read-only permission mapping."""
    for label, content, expected_roots in (
        ("publisher", publisher, [
            "name: Reconcile Observability Access Policy", "on:",
            "permissions:", "concurrency:", "jobs:",
        ]),
        ("independent", independent, [
            "name: Observability Access Source Negative", "on:",
            "permissions:", "jobs:",
        ]),
    ):
        roots = [
            line for line in content.splitlines()
            if line.strip() and not line[0].isspace()
            and not line.lstrip().startswith("#")
        ]
        if roots != expected_roots:
            raise SystemExit("observability-access " + label + " root YAML key shadow drift")
        if content.count("\npermissions:\n") != 1:
            raise SystemExit("observability-access " + label + " permission leaf shadow drift")
        permission_rows = []
        for line in content.split("\npermissions:\n", 1)[1].splitlines():
            if line.strip() and not line[0].isspace():
                break
            if line.strip() and not line.lstrip().startswith("#"):
                permission_rows.append(line)
        if permission_rows != ["  contents: read"]:
            raise SystemExit("observability-access " + label + " permission leaf shadow drift")


def observability_yaml_shadow_negatives(publisher: str, independent: str) -> None:
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
            raise SystemExit("observability-access " + label
                             + " permission mutation anchor drift")
        for name, extra in (
            ("spaced contents", "  contents : write\n"),
            ("quoted contents", "  'contents': write\n"),
        ):
            cases.append((name, content.replace(anchor, anchor + extra, 1),
                          "permission leaf shadow drift"))
        for name, altered, diagnostic in cases:
            if altered == content:
                raise SystemExit("observability-access YAML fixture unchanged: " + name)
            try:
                if label == "publisher":
                    observability_validate_trigger_matrix(altered, independent)
                else:
                    observability_validate_trigger_matrix(publisher, altered)
            except SystemExit as exc:
                expected = "observability-access " + label + " " + diagnostic
                if str(exc) != expected:
                    raise SystemExit(
                        "observability-access YAML wrong diagnostic: "
                        + label + "/" + name + ": " + str(exc)
                    ) from exc
            else:
                raise SystemExit("observability-access accepted YAML shadow: "
                                 + label + "/" + name)
            total += 1
    if total != 12:
        raise SystemExit("observability-access YAML fixture count drift")
    print("PASS: observability publisher/independent YAML root/permission (12 exact-diagnostic negatives)")


def replace_observability_trigger_header(content: str, original: str, replacement: str) -> str:
    old = "\non:\n" + original + "\npermissions:\n"
    if content.count(old) != 1 or original == replacement:
        raise SystemExit("observability-access trigger negative fixture unreachable")
    return content.replace(old, "\non:\n" + replacement + "\npermissions:\n", 1)


def observability_trigger_matrix_negatives(publisher: str, independent: str) -> None:
    def must_reject(p: str, i: str) -> None:
        try:
            observability_validate_trigger_matrix(p, i)
        except SystemExit:
            return
        raise SystemExit("observability-access accepted event trigger mutation")

    omissions = additions = 0
    cases = (
        ("publisher", "pull_request", OBSERVABILITY_PUBLISHER_PR_PATHS),
        ("publisher", "push", OBSERVABILITY_PUBLISHER_PUSH_PATHS),
        ("independent", "pull_request", OBSERVABILITY_INDEPENDENT_PR_PATHS),
        ("independent", "push", OBSERVABILITY_INDEPENDENT_PUSH_PATHS),
    )
    for label, event, paths in cases:
        original = publisher if label == "publisher" else independent
        header = observability_trigger_header(original)
        block = observability_trigger_event(event, paths)
        if header.count(block) != 1:
            raise SystemExit("observability-access trigger event fixture ambiguous")
        for index in range(len(paths)):
            shorter = paths[:index] + paths[index + 1:]
            mutated = replace_observability_trigger_header(
                original, header, header.replace(block, observability_trigger_event(event, shorter), 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            omissions += 1
        first = '      - "' + paths[0] + '"\n'
        for addition in (
            '      - "unreviewed/**"\n', '      - unreviewed/**\n',
            first, '      - ' + paths[0] + '\n',
        ):
            mutated_block = block.replace(first, first + addition, 1)
            mutated = replace_observability_trigger_header(
                original, header, header.replace(block, mutated_block, 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            additions += 1

    shortened = 0
    for field, paths in (
        ("publisher_pr", OBSERVABILITY_PUBLISHER_PR_PATHS),
        ("publisher_push", OBSERVABILITY_PUBLISHER_PUSH_PATHS),
        ("independent_pr", OBSERVABILITY_INDEPENDENT_PR_PATHS),
        ("independent_push", OBSERVABILITY_INDEPENDENT_PUSH_PATHS),
    ):
        try:
            observability_validate_trigger_matrix(publisher, independent, **{field: paths[:-1]})
        except SystemExit:
            shortened += 1
        else:
            raise SystemExit("observability-access accepted shortened trigger inventory")

    p_header, i_header = observability_trigger_header(publisher), observability_trigger_header(independent)
    topology = (
        (replace_observability_trigger_header(
            publisher, p_header, p_header.replace("  workflow_dispatch:\n", "", 1)), independent),
        (replace_observability_trigger_header(
            publisher, p_header, p_header.replace(
                "  workflow_dispatch:\n",
                "  schedule:\n    - cron: '0 0 * * *'\n  workflow_dispatch:\n", 1)), independent),
        (publisher, replace_observability_trigger_header(
            independent, i_header, i_header + "  workflow_dispatch:\n")),
    )
    for p, i in topology:
        must_reject(p, i)
    print("PASS: observability-access exact trigger matrix: "
          + str(omissions) + " omissions, " + str(additions)
          + " additions/duplicates, " + str(shortened)
          + " shortened inventories, " + str(len(topology)) + " event topology negatives")



def observability_concurrency_authority(source: str) -> None:
    """Keep the reviewed noncancelling publisher serialization authority."""
    marker = "\nconcurrency:\n"
    if source.count(marker) != 1 or source.count("\njobs:\n") != 1:
        raise AssertionError("observability-access concurrency authority drift")
    actual = source.split(marker, 1)[1].split("\njobs:\n", 1)[0]
    expected = (
        "  group: reconcile-observability-access-${{ github.event.pull_request.number || 'so' }}\n"
        "  cancel-in-progress: false\n"
    )
    if actual != expected:
        raise AssertionError("observability-access concurrency authority drift")


def observability_concurrency_negatives(source: str) -> None:
    group = "  group: reconcile-observability-access-${{ github.event.pull_request.number || 'so' }}\n"
    cancel = "  cancel-in-progress: false\n"
    cases = (
        ("group changed", group, "  group: unreviewed\n"),
        ("group missing", group, ""),
        ("group duplicated", group, group + group),
        ("group quoted", group, "  'group': reconcile-observability-access\n"),
        ("group spaced", group, "  group : unreviewed\n"),
        ("group shadowed", group, group + "  group : unreviewed\n"),
        ("cancellation enabled", cancel, "  cancel-in-progress: true\n"),
        ("cancellation missing", cancel, ""),
        ("cancellation duplicated", cancel, cancel + cancel),
        ("cancellation quoted", cancel, "  'cancel-in-progress': false\n"),
        ("cancellation spaced", cancel, "  cancel-in-progress : false\n"),
        ("unreviewed leaf", cancel, cancel + "  unexpected: true\n"),
    )
    for name, old, replacement in cases:
        if source.count(old) != 1:
            raise AssertionError("observability-access concurrency fixture anchor drift: " + name)
        changed = source.replace(old, replacement, 1)
        try:
            observability_concurrency_authority(changed)
        except AssertionError as exc:
            if str(exc) != "observability-access concurrency authority drift":
                raise AssertionError("observability-access concurrency wrong diagnostic: "
                                     + name + ": " + str(exc)) from exc
        else:
            raise AssertionError("observability-access accepted concurrency mutation: " + name)
    if len(cases) != 12:
        raise AssertionError("observability-access concurrency fixture count drift")
    print("PASS: observability-access publisher concurrency (12 exact-diagnostic negatives)")



def policy(s: str) -> None:
    if s.count(CHECKOUT) != 2 or s.count(SETUP) != 2:
        raise AssertionError("observability-access immutable Actions drift")
    if s.count("persist-credentials: false") != 1 or s.count("persist-credentials: true") != 1:
        raise AssertionError("observability-access credential separation drift")
    if "actions/checkout@v4" in s or "actions/setup-python@v5" in s:
        raise AssertionError("observability-access floating Action regression")
    for marker in REQUIRED:
        if marker not in s:
            raise AssertionError("observability-access required source marker absent: " + marker)
    if s.count('test -z "$(git status --porcelain)"') != 3:
        raise AssertionError("observability-access source/final clean multiplicity drift")

def step(source: str, name: str) -> str:
    marker = "      - name: " + name + "\n"
    if source.count(marker) != 1:
        raise AssertionError("observability-access step missing/duplicated: " + name)
    start = source.index("        run: |\n", source.index(marker)) + len("        run: |\n")
    boundaries = [p for p in (source.find("\n      - name:", start),
                             source.find("\n  reconcile:", start),
                             source.find("\n  validate-pr:", start)) if p >= 0]
    end = min(boundaries) if boundaries else len(source)
    lines = source[start:end].splitlines()
    if any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("observability-access shell crossed job boundary")
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"

def runtime(source: str, name: str, cases: tuple) -> None:
    shell = step(source, name)
    head = "a" * 40
    with tempfile.TemporaryDirectory(prefix="load-missing-source-") as tmp:
        root = Path(tmp)
        git = root / "git"
        git.write_text("#!/bin/sh\n"
                       "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"HEAD\" ]; then echo " + head + "; exit 0; fi\n"
                       "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then exit 0; fi\n"
                       "exit 1\n", encoding="utf-8")
        git.chmod(0o755)
        envfile = root / "env"
        for event, base, ref, sha, accepted in cases:
            envfile.write_text("", encoding="utf-8")
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_ENV=str(envfile), GITHUB_EVENT_NAME=event,
                       GITHUB_BASE_REF=base, GITHUB_REF=ref, GITHUB_SHA=sha, PR_HEAD_SHA=sha)
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                    cwd=root, env=env, capture_output=True, text=True,
                                    timeout=10, check=False)
            if (result.returncode == 0) != accepted:
                raise AssertionError(f"observability-access actual shell source drift: {name} {(event, base, ref, sha, result.returncode)}")
    print(f"PASS: observability-access {name} actual event/base/ref/SHA shell ({len(cases)} cases)")

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
        with tempfile.TemporaryDirectory(prefix="load-missing-cas-") as tmp:
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
                raise AssertionError(f"observability-access CAS {label}: unexpected exit {result.returncode}: {result.stderr[-100:]}")
            if sum(line == "push origin HEAD:so" for line in calls) != pushes:
                raise AssertionError("observability-access CAS pushed on stale/no-op/invalid source: " + label)
            if label == "noop" and any(line.startswith("commit ") for line in calls):
                raise AssertionError("observability-access no-op committed")
    print(f"PASS: observability-access actual publisher CAS/no-op shell ({len(cases)} cases)")

def main() -> None:
    source = read(PUBLISHER)
    independent = read(INDEPENDENT)
    for marker in (PUBLISHER, SELF, CHECKOUT, SETUP, "persist-credentials: false",
                   "contents: read", 'test -z "$(git status --porcelain)"'):
        if marker not in independent:
            raise AssertionError("observability-access independent CI reachability missing: " + marker)
    if blob(source) != REVIEWED_PUBLISHER:
        raise AssertionError("observability-access complete publisher Git blob drift")
    if blob(independent) != REVIEWED_INDEPENDENT:
        raise AssertionError("observability-access complete independent CI Git blob drift")
    if blob(independent + "\n# synthetic whole-source drift\n") == REVIEWED_INDEPENDENT:
        raise AssertionError("observability-access independent CI mutation accepted")
    if blob(source + "\n# synthetic whole-source drift\n") == REVIEWED_PUBLISHER:
        raise AssertionError("observability-access whole-source mutation accepted")
    policy(source)
    observability_validate_trigger_matrix(source, independent)
    observability_trigger_matrix_negatives(source, independent)
    observability_yaml_shadow_negatives(source, independent)
    observability_concurrency_authority(source)
    observability_concurrency_negatives(source)
    for index, marker in enumerate(REQUIRED):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE", 1)
        if changed == source:
            raise AssertionError("observability-access negative unreachable: " + str(index))
        try:
            policy(changed)
        except AssertionError:
            continue
        raise AssertionError("observability-access source mutation accepted: " + str(index))
    print(f"PASS: observability-access publisher reviewed blob and {len(REQUIRED)} source negatives")
    head = "a" * 40
    runtime(source, "Confirm exact clean PR authority source", (
        ("pull_request", "so", "", head, True),
        ("pull_request", "main", "", head, False),
        ("push", "so", "", head, False),
        ("pull_request", "so", "", "b" * 40, False),
        ("pull_request", "so", "", "A" * 40, False),
        ("pull_request", "so", "", "a" * 39, False),
    ))
    runtime(source, "Confirm exact clean authority source", (
        ("push", "", "refs/heads/so", head, True),
        ("workflow_dispatch", "", "refs/heads/so", head, True),
        ("schedule", "", "refs/heads/so", head, False),
        ("pull_request", "", "refs/heads/so", head, False),
        ("push", "", "refs/heads/main", head, False),
        ("push", "", "refs/heads/so", "b" * 40, False),
        ("push", "", "refs/heads/so", "A" * 40, False),
        ("push", "", "refs/heads/so", "a" * 39, False),
    ))
    cas_runtime(source)
    print("PASS: independent read-only observability-access source guard; production evidence generated: false")

if __name__ == "__main__":
    main()
