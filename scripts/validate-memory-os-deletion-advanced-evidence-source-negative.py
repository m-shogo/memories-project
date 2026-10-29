#!/usr/bin/env python3
"""Independent read-only source and executable event/ref/SHA negatives for advanced deletion evidence."""
from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-deletion-advanced-evidence.yml"
INDEPENDENT = ".github/workflows/deletion-advanced-evidence-source-negative.yml"
SELF = "scripts/validate-memory-os-deletion-advanced-evidence-source-negative.py"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
REVIEWED_PUBLISHER = "307b11562fe84e580bc988c5167befa5c5d1e87c"
REVIEWED_INDEPENDENT = "5923f001321ad4c2dfd264b0b92000335dd0ac53"
RECONCILER = "scripts/reconcile-memory-os-deletion-advanced-evidence.py"
RECONCILE_NEGATIVE = "scripts/validate-memory-os-deletion-advanced-evidence-reconcile-negative.py"
CROSS_NEGATIVE = "scripts/validate-memory-os-deletion-deferred-reason-cross-publisher-negative.py"
REVIEWED_RECONCILER = "4a1358636f0b4e199d37155dfd2ee1c47fba03cd"
REVIEWED_RECONCILE_NEGATIVE = "44819f1750fb162dd39b1461e19b1618aef35fe8"
REVIEWED_CROSS_NEGATIVE = "0a6217af102ab01273df28516d856ba2b87d8654"

PUBLISHER_TRIGGER_PATHS = tuple([".github/workflows/reconcile-deletion-advanced-evidence.yml","scripts/reconcile-memory-os-deletion-prefence-linearization.py","scripts/validate-memory-os-deletion-prefence-linearization-reconcile-negative.py","scripts/reconcile-memory-os-deletion-advanced-evidence.py","scripts/validate-memory-os-deletion-advanced-evidence-reconcile-negative.py","scripts/validate-memory-os-deletion-prefence-linearization.py","scripts/validate-memory-os-deletion-worker-saturation.py","scripts/validate-memory-os-load-evidence-index.py","scripts/validate-memory-os-load.py","scripts/validate-memory-os-operability.py","contracts/operations/deletion-prefence-linearization-contract.v1.json","contracts/operations/deletion-worker-saturation-contract.v1.json","docs/fixtures/memory-os-operability/deletion-prefence-linearization-results.sample.v1.json","docs/fixtures/memory-os-operability/deletion-worker-saturation-results.sample.v1.json"])
INDEPENDENT_TRIGGER_PATHS = tuple([".github/workflows/reconcile-deletion-advanced-evidence.yml",".github/workflows/deletion-advanced-evidence-source-negative.yml","scripts/validate-memory-os-deletion-advanced-evidence-source-negative.py","scripts/reconcile-memory-os-deletion-advanced-evidence.py","scripts/validate-memory-os-deletion-advanced-evidence-reconcile-negative.py","scripts/validate-memory-os-deletion-deferred-reason-cross-publisher-negative.py"])



def validate_trigger_reachability(
    publisher: str, independent: str, *,
    publisher_paths: tuple[str, ...] | None = None,
    independent_paths: tuple[str, ...] | None = None,
) -> None:
    """Pin reviewed publisher push/PR/dispatch and independent PR/push path order."""
    pub = PUBLISHER_TRIGGER_PATHS if publisher_paths is None else publisher_paths
    ind = INDEPENDENT_TRIGGER_PATHS if independent_paths is None else independent_paths
    if (len(pub) != len(PUBLISHER_TRIGGER_PATHS) or
        len(ind) != len(INDEPENDENT_TRIGGER_PATHS) or
        len(set(pub)) != len(pub) or len(set(ind)) != len(ind)):
        raise AssertionError("advanced deletion shortened/duplicated event trigger inventory")
    pub_lines = "".join('      - "' + path + '"\n' for path in pub)
    ind_lines = "".join('      - "' + path + '"\n' for path in ind)
    expected_pub = (
        "name: Reconcile Advanced Deletion Evidence\n\non:\n"
        "  push:\n    branches:\n      - so\n    paths:\n" + pub_lines +
        "  pull_request:\n    branches:\n      - so\n    paths:\n" + pub_lines +
        "  workflow_dispatch:\n"
    )
    expected_ind = (
        "name: Advanced Deletion Evidence Source Negative\n\non:\n"
        "  pull_request:\n    branches:\n      - so\n    paths:\n" + ind_lines +
        "  push:\n    branches:\n      - so\n    paths:\n" + ind_lines
    )
    for label, value, expected in (
        ("publisher", publisher, expected_pub), ("independent", independent, expected_ind)
    ):
        if value.count("\npermissions:\n") != 1:
            raise AssertionError("advanced deletion " + label + " permissions boundary drift")
        if value.split("\npermissions:\n", 1)[0] != expected:
            raise AssertionError("advanced deletion " + label + " exact event trigger drift")



def validate_yaml_root_permission(publisher: str, independent: str) -> None:
    """Pin effective root YAML mapping and read-only permission leaves independently of blob SHA."""
    for label, source, roots in (
        ("publisher", publisher, ["name: Reconcile Advanced Deletion Evidence",
                                  "on:", "permissions:", "concurrency:", "jobs:"]),
        ("independent", independent, ["name: Advanced Deletion Evidence Source Negative",
                                      "on:", "permissions:", "jobs:"]),
    ):
        actual = [
            line for line in source.splitlines()
            if line.strip() and not line[0].isspace()
            and not line.lstrip().startswith("#")
        ]
        if actual != roots:
            raise AssertionError("advanced deletion " + label + " root YAML key shadow drift")
        if source.count("\npermissions:\n") != 1:
            raise AssertionError("advanced deletion " + label + " permission boundary drift")
        leaves = []
        for line in source.split("\npermissions:\n", 1)[1].splitlines():
            if line.strip() and not line[0].isspace():
                break
            if line.strip() and not line.lstrip().startswith("#"):
                leaves.append(line)
        if leaves != ["  contents: read"]:
            raise AssertionError("advanced deletion " + label + " permission leaf shadow drift")


def yaml_root_permission_negatives(publisher: str, independent: str) -> None:
    """Require exact diagnostics for twelve effective YAML root/permission mutations."""
    validate_yaml_root_permission(publisher, independent)
    count = 0
    for label, source, other, is_publisher in (
        ("publisher", publisher, independent, True),
        ("independent", independent, publisher, False),
    ):
        cases = []
        for mutation, suffix in (
            ("spaced on", "on :\n  issues:\n"),
            ("quoted on", "'on':\n  issues:\n"),
            ("spaced jobs", "jobs : {}\n"),
            ("quoted jobs", "'jobs': {}\n"),
        ):
            cases.append((mutation, source + "\n" + suffix, "root YAML key shadow drift"))
        marker = "\npermissions:\n  contents: read\n"
        if source.count(marker) != 1:
            raise AssertionError("advanced deletion " + label + " permission fixture anchor drift")
        for mutation, leaf in (
            ("spaced contents", "  contents : write\n"),
            ("quoted contents", "  'contents': write\n"),
        ):
            cases.append((mutation, source.replace(marker, marker + leaf, 1),
                          "permission leaf shadow drift"))
        for mutation, changed, diagnostic in cases:
            if changed == source:
                raise AssertionError("advanced deletion unchanged YAML fixture: " + mutation)
            try:
                if is_publisher:
                    validate_yaml_root_permission(changed, other)
                else:
                    validate_yaml_root_permission(other, changed)
            except AssertionError as exc:
                expected = "advanced deletion " + label + " " + diagnostic
                if str(exc) != expected:
                    raise AssertionError("advanced deletion wrong YAML diagnostic: "
                                         + label + " " + mutation + ": " + str(exc)) from exc
            else:
                raise AssertionError("advanced deletion accepted YAML shadow: " + label + " " + mutation)
            count += 1
    if count != 12:
        raise AssertionError("advanced deletion YAML negative inventory drift")
    print("PASS: advanced deletion root/permission YAML authority (12 exact-diagnostic negatives)")


def trigger_negatives(publisher: str, independent: str) -> None:
    """Prove event-specific path omissions, unquoted additions and event topology."""
    cases = (
        ("publisher push", publisher, "  push:\n    branches:\n      - so\n    paths:\n",
         "  pull_request:\n", PUBLISHER_TRIGGER_PATHS, True),
        ("publisher PR", publisher, "  pull_request:\n    branches:\n      - so\n    paths:\n",
         "  workflow_dispatch:\n", PUBLISHER_TRIGGER_PATHS, True),
        ("independent PR", independent, "  pull_request:\n    branches:\n      - so\n    paths:\n",
         "  push:\n", INDEPENDENT_TRIGGER_PATHS, False),
        ("independent push", independent, "  push:\n    branches:\n      - so\n    paths:\n",
         "\npermissions:\n", INDEPENDENT_TRIGGER_PATHS, False),
    )
    omitted = added = 0
    for label, value, start, stop, paths, is_publisher in cases:
        if value.count(start) != 1 or value.count(stop) != 1:
            raise AssertionError("advanced deletion trigger negative event anchor drift: " + label)
        begin = value.index(start) + len(start)
        end = value.index(stop, begin)
        block = value[begin:end]
        mutations = []
        for path in paths:
            token = '      - "' + path + '"\n'
            if block.count(token) != 1:
                raise AssertionError("advanced deletion trigger omission fixture drift: " + path)
            mutations.append(("omission " + path, block.replace(token, "", 1), True))
        mutations.extend((
            ("quoted extra", block + '      - "unreviewed/**"\n', False),
            ("quoted duplicate", block + '      - "' + paths[0] + '"\n', False),
            ("unquoted extra", block + "      - unreviewed/**\n", False),
            ("unquoted duplicate", block + "      - " + paths[0] + "\n", False),
        ))
        for name, changed, is_omission in mutations:
            mutated = value[:begin] + changed + value[end:]
            if mutated == value:
                raise AssertionError("advanced deletion unchanged trigger negative: " + name)
            try:
                if is_publisher:
                    validate_trigger_reachability(mutated, independent)
                else:
                    validate_trigger_reachability(publisher, mutated)
            except AssertionError:
                pass
            else:
                raise AssertionError("advanced deletion accepted " + label + " " + name)
            omitted += int(is_omission)
            added += int(not is_omission)
    for label, kwargs in (
        ("publisher", {"publisher_paths": PUBLISHER_TRIGGER_PATHS[:-1]}),
        ("independent", {"independent_paths": INDEPENDENT_TRIGGER_PATHS[:-1]}),
    ):
        try:
            validate_trigger_reachability(publisher, independent, **kwargs)
        except AssertionError:
            pass
        else:
            raise AssertionError("advanced deletion accepted shortened " + label + " inventory")
    for label, value, is_publisher in (
        ("publisher schedule introduction", publisher.replace(
            "  workflow_dispatch:\n", "  schedule:\n    - cron: '0 0 * * *'\n  workflow_dispatch:\n", 1), True),
        ("publisher dispatch deletion", publisher.replace("  workflow_dispatch:\n", "", 1), True),
        ("independent dispatch introduction", independent.replace(
            "\npermissions:\n", "  workflow_dispatch:\n\npermissions:\n", 1), False),
    ):
        try:
            if is_publisher:
                validate_trigger_reachability(value, independent)
            else:
                validate_trigger_reachability(publisher, value)
        except AssertionError:
            pass
        else:
            raise AssertionError("advanced deletion accepted event topology mutation: " + label)
    if (omitted, added) != (40, 16):
        raise AssertionError("advanced deletion trigger negative population drift")
    print("PASS: advanced deletion exact event triggers (40 omissions; 16 additions; "
          "2 shortened inventories; 3 event topology negatives)")


def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def read(path: str) -> str:
    file = ROOT / path
    if file.is_symlink() or not file.is_file() or file.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise AssertionError("advanced deletion source missing/substituted: " + path)
    return file.read_text(encoding="utf-8")

def reviewed_source(content: str, expected: str, label: str) -> None:
    if blob(content) != expected:
        raise AssertionError("advanced deletion complete Git blob drift: " + label)

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
        raise AssertionError("advanced deletion accepted synthetic full-source drift: " + label)
    print("PASS: advanced deletion reviewed Git blob negatives (2 cases)")

def step(source: str, title: str) -> str:
    marker = "      - name: " + title + "\n"
    if source.count(marker) != 1:
        raise AssertionError("advanced deletion source step missing/duplicate: " + title)
    start = source.index("        run: |\n", source.index(marker)) + len("        run: |\n")
    boundaries = [source.find(boundary, start) for boundary in (
        "\n      - name:", "\n  reconcile:", "\n  validate-pr:",
    )]
    end = min((position for position in boundaries if position >= 0), default=len(source))
    lines = source[start:end].splitlines()
    if any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("advanced deletion shell indentation drift: " + title)
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
            raise AssertionError("advanced deletion publisher policy missing: " + marker[:70])
    if source.count(CHECKOUT) != 2 or source.count(SETUP) != 2:
        raise AssertionError("advanced deletion immutable Action count drift")
    if source.count('test -z "$(git status --porcelain)"') != 3:
        raise AssertionError("advanced deletion clean worktree boundary count drift")
    if "actions/checkout@v4" in source or "actions/setup-python@v5" in source:
        raise AssertionError("advanced deletion floating Action regression")

def mutations(source: str) -> None:
    for index, marker in enumerate(REQUIRED):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE_TEST", 1)
        if changed == source:
            raise AssertionError("advanced deletion mutation unreachable: " + str(index))
        try:
            policy(changed)
        except AssertionError:
            continue
        raise AssertionError("advanced deletion accepted source mutation: " + str(index))
    print(f"PASS: advanced deletion publisher source mutations ({len(REQUIRED)} cases)")

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
    with tempfile.TemporaryDirectory(prefix="advanced deletion-operations-identity-") as temp:
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
                raise AssertionError("advanced deletion event/base/ref/SHA runtime drift: " +
                                     str((title, event, ref, result.returncode)))
    print(f"PASS: advanced deletion {title} identity shell runtime ({len(cases)} cases)")

def cas_runtime(source: str) -> None:
    """Execute the real blocker publisher commit/CAS shell in a disposable fake-Git sandbox."""
    shell = step(source, "Reconcile without production promotion")
    shell = "set -euo pipefail\n" + shell[shell.index("git add \\\n"):]
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
                raise AssertionError(f"advanced deletion CAS {label}: unexpected exit {result.returncode}: {result.stderr[-100:]}")
            if sum(line == "push origin HEAD:so" for line in calls) != pushes:
                raise AssertionError("advanced deletion CAS pushed on stale/no-op/invalid source: " + label)
            if label == "noop" and any(line.startswith("commit ") for line in calls):
                raise AssertionError("advanced deletion no-op committed")
    print(f"PASS: advanced deletion actual publisher CAS/no-op shell ({len(cases)} cases)")



def validate_job_authority(publisher: str, independent: str) -> None:
    """Pin effective job mappings, scope and job keys before blob-only checks."""
    reviewed = (
        ("publisher", publisher, (
            ("validate-pr", "github.event_name == 'pull_request' && github.base_ref == 'so'", "read", 10),
            ("reconcile",
             "(github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'",
             "write", 10),
        )),
        ("independent", independent, (
            ("source-negative",
             "github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')",
             "read", 5),
        )),
    )
    for label, content, jobs in reviewed:
        prefix = "advanced-evidence " + label + " "
        if content.count("\njobs:\n") != 1:
            raise SystemExit(prefix + "job mapping shadow drift")
        body = content.split("\njobs:\n", 1)[1]
        sections: dict[str, list[str]] = {}
        current: str | None = None
        actual: list[str] = []
        for line in body.splitlines():
            if (line.startswith("  ") and len(line) > 2 and line[2] != " "
                    and not line.lstrip().startswith("#")):
                current = line
                actual.append(line)
                sections[current] = []
            elif current is not None:
                sections[current].append(line)
        expected = ["  " + name + ":" for name, _, _, _ in jobs]
        if actual != expected:
            raise SystemExit(prefix + "job mapping shadow drift")
        for name, condition, scope, timeout in jobs:
            lines = sections["  " + name + ":"]
            keys = [
                line for line in lines
                if line.startswith("    ") and len(line) > 4 and line[4] != " "
                and not line.lstrip().startswith("#")
            ]
            if keys != [
                "    if: " + condition,
                "    permissions:",
                "    runs-on: ubuntu-latest",
                "    timeout-minutes: " + str(timeout),
                "    steps:",
            ]:
                raise SystemExit(prefix + name + " job key shadow drift")
            leaves: list[str] = []
            for line in lines[lines.index("    permissions:") + 1:]:
                if line.startswith("    ") and len(line) > 4 and line[4] != " ":
                    break
                if line.strip() and not line.lstrip().startswith("#"):
                    leaves.append(line)
            if leaves != ["      contents: " + scope]:
                raise SystemExit(prefix + name + " job permission leaf shadow drift")


def prove_job_authority_negatives(publisher: str, independent: str) -> None:
    """Exercise 36 exact-diagnostic nested YAML mutations, not just blob mismatch."""
    validate_job_authority(publisher, independent)
    count = 0
    reviewed = (
        ("publisher", publisher, independent, (
            ("validate-pr", "github.event_name == 'pull_request' && github.base_ref == 'so'", "read", 10),
            ("reconcile",
             "(github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'",
             "write", 10),
        ), True),
        ("independent", independent, publisher, (
            ("source-negative",
             "github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')",
             "read", 5),
        ), False),
    )
    for label, content, other, jobs, is_publisher in reviewed:
        for name, condition, scope, timeout in jobs:
            header = "  " + name + ":\n"
            if content.count(header) != 1:
                raise SystemExit("advanced-evidence job fixture header drift: " + label + " " + name)

            def in_job(before: str, after: str) -> str:
                prefix, suffix = content.split(header, 1)
                if before not in suffix:
                    raise SystemExit("advanced-evidence job fixture anchor drift: " + name)
                return prefix + header + suffix.replace(before, after, 1)

            condition_anchor = "    if: " + condition + "\n"
            permission = "    permissions:\n      contents: " + scope + "\n"
            runner = "    runs-on: ubuntu-latest\n"
            timeout_anchor = "    timeout-minutes: " + str(timeout) + "\n"
            steps = "    steps:\n"
            cases = [
                ("duplicate mapping", content + "\n" + header + "    runs-on: ubuntu-latest\n",
                 "job mapping shadow drift"),
                ("quoted mapping", content.replace(header, "  '" + name + "':\n", 1),
                 "job mapping shadow drift"),
                ("spaced mapping", content.replace(header, "  " + name + " :\n", 1),
                 "job mapping shadow drift"),
                ("condition shadow", in_job(condition_anchor, condition_anchor + "    if : true\n"),
                 name + " job key shadow drift"),
                ("permission shadow", in_job(permission, permission + "    permissions :\n      contents: write\n"),
                 name + " job key shadow drift"),
                ("runner shadow", in_job(runner, runner + "    runs-on : ubuntu-latest\n"),
                 name + " job key shadow drift"),
                ("timeout shadow", in_job(timeout_anchor, timeout_anchor + "    timeout-minutes : 1\n"),
                 name + " job key shadow drift"),
                ("steps shadow", in_job(steps, "    steps : []\n" + steps),
                 name + " job key shadow drift"),
                ("continuation override", in_job(steps, "    continue-on-error: true\n" + steps),
                 name + " job key shadow drift"),
                ("direct permission change", in_job(permission, permission.replace(
                    "contents: " + scope, "contents: " + ("read" if scope == "write" else "write"))),
                 name + " job permission leaf shadow drift"),
                ("spaced permission leaf", in_job(permission, permission + "      contents : write\n"),
                 name + " job permission leaf shadow drift"),
                ("quoted permission leaf", in_job(permission, permission + "      'contents': write\n"),
                 name + " job permission leaf shadow drift"),
            ]
            for mutation, changed, diagnostic in cases:
                if changed == content:
                    raise SystemExit("advanced-evidence unchanged job fixture: " + mutation)
                try:
                    if is_publisher:
                        validate_job_authority(changed, other)
                    else:
                        validate_job_authority(other, changed)
                except SystemExit as exc:
                    expected = "advanced-evidence " + label + " " + diagnostic
                    if str(exc) != expected:
                        raise SystemExit("advanced-evidence wrong job diagnostic: "
                                         + label + " " + name + " " + mutation + ": " + str(exc)) from exc
                else:
                    raise SystemExit("advanced-evidence accepted job shadow: "
                                     + label + " " + name + " " + mutation)
                count += 1
    if count != 36:
        raise SystemExit("advanced-evidence job negative inventory drift")
    print("PASS: advanced-evidence publisher/independent job authority (36 exact-diagnostic negatives)")


def main() -> None:
    publisher, independent = read(PUBLISHER), read(INDEPENDENT)
    for marker in (PUBLISHER, INDEPENDENT, SELF, RECONCILER, RECONCILE_NEGATIVE, CROSS_NEGATIVE, CHECKOUT, SETUP,
                   "persist-credentials: false", "contents: read",
                   'test "$(git rev-parse HEAD)" = "$expected"',
                   'test -z "$(git status --porcelain)"'):
        if marker not in independent:
            raise AssertionError("advanced deletion independent CI reachability drift: " + marker)
    for path, expected in ((RECONCILER, REVIEWED_RECONCILER),
                           (RECONCILE_NEGATIVE, REVIEWED_RECONCILE_NEGATIVE),
                           (CROSS_NEGATIVE, REVIEWED_CROSS_NEGATIVE)):
        reviewed_source(read(path), expected, path)
    if (independent.count(RECONCILER) != 2
            or independent.count(RECONCILE_NEGATIVE) != 3
            or independent.count(CROSS_NEGATIVE) != 2):
        raise AssertionError("advanced deletion transitive negative CI reachability drift")
    reviewed_negatives(publisher, independent)
    validate_trigger_reachability(publisher, independent)
    trigger_negatives(publisher, independent)
    validate_yaml_root_permission(publisher, independent)
    yaml_root_permission_negatives(publisher, independent)
    validate_job_authority(publisher, independent)
    prove_job_authority_negatives(publisher, independent)
    policy(publisher)
    mutations(publisher)
    identity(publisher, "Capture exact pull request source", False)
    identity(publisher, "Capture exact source", True)
    cas_runtime(publisher)
    print("PASS: advanced deletion exact-source read-only proof; production evidence generated: false")

if __name__ == "__main__":
    main()
