#!/usr/bin/env python3
"""Independent read-only missing-evidence authority source and runtime negatives."""
from __future__ import annotations
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-load-missing-evidence.yml"
INDEPENDENT = ".github/workflows/load-missing-evidence-source-negative.yml"
SELF = "scripts/validate-memory-os-load-missing-source-negative.py"
RECONCILER = "scripts/reconcile-memory-os-load-missing-evidence.py"
CHECKOUT = "uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
REVIEWED_PUBLISHER = "f51a30f3e51fe695dfb77da808a9e2afb8f980b1"
REVIEWED_INDEPENDENT = "5b6273fac014e4308d207acb2633297af04f229d"
REVIEWED_RECONCILER = "90e412225203ea431d14ef306418a3a8c6b504f6"

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
    'echo "SOURCE_SHA=$(git rev-parse HEAD)" >> "$GITHUB_ENV"',
    "git push origin HEAD:so",
)

LOAD_MISSING_PUBLISHER_PR_PATHS = (
    ".github/workflows/reconcile-load-missing-evidence.yml",
    "scripts/reconcile-memory-os-load-missing-evidence.py",
    "scripts/validate-memory-os-load-missing-evidence-reconcile-negative.py",
    "scripts/validate-memory-os-load.py",
    "scripts/validate-memory-os-operability.py",
    "contracts/operations/load-test-scenario-contract.v1.json",
    "contracts/operations/production-operability-status.json",
)

LOAD_MISSING_PUBLISHER_PUSH_PATHS = (
    ".github/workflows/reconcile-load-missing-evidence.yml",
    "scripts/reconcile-memory-os-load-missing-evidence.py",
    "scripts/validate-memory-os-load-missing-evidence-reconcile-negative.py",
    "scripts/validate-memory-os-load.py",
    "scripts/validate-memory-os-operability.py",
    "contracts/operations/load-test-scenario-contract.v1.json",
    "contracts/operations/production-operability-status.json",
)

LOAD_MISSING_INDEPENDENT_PR_PATHS = (
    ".github/workflows/reconcile-load-missing-evidence.yml",
    ".github/workflows/load-missing-evidence-source-negative.yml",
    "scripts/validate-memory-os-load-missing-source-negative.py",
)

LOAD_MISSING_INDEPENDENT_PUSH_PATHS = (
    ".github/workflows/reconcile-load-missing-evidence.yml",
    ".github/workflows/load-missing-evidence-source-negative.yml",
    "scripts/validate-memory-os-load-missing-source-negative.py",
)

def load_missing_trigger_event(event: str, paths: tuple[str, ...]) -> str:
    return ("  " + event + ":\n    branches:\n      - so\n    paths:\n"
            + "".join('      - "' + path + '"\n' for path in paths))


def load_missing_trigger_header(content: str) -> str:
    # Exact, ordered event header: reject unknown, unquoted, duplicate and
    # unexpected event paths instead of depending only on a Git blob digest.
    if content.count("\non:\n") != 1 or content.count("\npermissions:\n") != 1:
        raise SystemExit("load-missing-evidence trigger section ambiguous")
    return content.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]


def load_missing_validate_trigger_matrix(
    publisher: str, independent: str,
    publisher_pr: tuple[str, ...] = LOAD_MISSING_PUBLISHER_PR_PATHS,
    publisher_push: tuple[str, ...] = LOAD_MISSING_PUBLISHER_PUSH_PATHS,
    independent_pr: tuple[str, ...] = LOAD_MISSING_INDEPENDENT_PR_PATHS,
    independent_push: tuple[str, ...] = LOAD_MISSING_INDEPENDENT_PUSH_PATHS,
) -> None:
    expected_publisher = (load_missing_trigger_event("pull_request", publisher_pr)
                          + load_missing_trigger_event("push", publisher_push)
                          + "  workflow_dispatch:\n")
    expected_independent = (load_missing_trigger_event("pull_request", independent_pr)
                            + load_missing_trigger_event("push", independent_push))
    for label, content, expected in (
        ("publisher", publisher, expected_publisher),
        ("independent", independent, expected_independent),
    ):
        if load_missing_trigger_header(content) != expected:
            raise SystemExit("load-missing-evidence " + label
                             + " exact event trigger inventory drift")


def replace_load_missing_trigger_header(content: str, original: str, replacement: str) -> str:
    old = "\non:\n" + original + "\npermissions:\n"
    if content.count(old) != 1 or original == replacement:
        raise SystemExit("load-missing-evidence trigger negative fixture unreachable")
    return content.replace(old, "\non:\n" + replacement + "\npermissions:\n", 1)


def load_missing_trigger_matrix_negatives(publisher: str, independent: str) -> None:
    def must_reject(p: str, i: str) -> None:
        try:
            load_missing_validate_trigger_matrix(p, i)
        except SystemExit:
            return
        raise SystemExit("load-missing-evidence accepted event trigger mutation")

    omissions = additions = 0
    cases = (
        ("publisher", "pull_request", LOAD_MISSING_PUBLISHER_PR_PATHS),
        ("publisher", "push", LOAD_MISSING_PUBLISHER_PUSH_PATHS),
        ("independent", "pull_request", LOAD_MISSING_INDEPENDENT_PR_PATHS),
        ("independent", "push", LOAD_MISSING_INDEPENDENT_PUSH_PATHS),
    )
    for label, event, paths in cases:
        original = publisher if label == "publisher" else independent
        header = load_missing_trigger_header(original)
        block = load_missing_trigger_event(event, paths)
        if header.count(block) != 1:
            raise SystemExit("load-missing-evidence trigger event fixture ambiguous")
        for index in range(len(paths)):
            shorter = paths[:index] + paths[index + 1:]
            mutated = replace_load_missing_trigger_header(
                original, header, header.replace(block, load_missing_trigger_event(event, shorter), 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            omissions += 1
        first = '      - "' + paths[0] + '"\n'
        for addition in (
            '      - "unreviewed/**"\n', '      - unreviewed/**\n',
            first, '      - ' + paths[0] + '\n',
        ):
            mutated_block = block.replace(first, first + addition, 1)
            mutated = replace_load_missing_trigger_header(
                original, header, header.replace(block, mutated_block, 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            additions += 1

    shortened = 0
    for field, paths in (
        ("publisher_pr", LOAD_MISSING_PUBLISHER_PR_PATHS),
        ("publisher_push", LOAD_MISSING_PUBLISHER_PUSH_PATHS),
        ("independent_pr", LOAD_MISSING_INDEPENDENT_PR_PATHS),
        ("independent_push", LOAD_MISSING_INDEPENDENT_PUSH_PATHS),
    ):
        try:
            load_missing_validate_trigger_matrix(publisher, independent, **{field: paths[:-1]})
        except SystemExit:
            shortened += 1
        else:
            raise SystemExit("load-missing-evidence accepted shortened trigger inventory")

    p_header, i_header = load_missing_trigger_header(publisher), load_missing_trigger_header(independent)
    topology = (
        (replace_load_missing_trigger_header(
            publisher, p_header, p_header.replace("  workflow_dispatch:\n", "", 1)), independent),
        (replace_load_missing_trigger_header(
            publisher, p_header, p_header.replace(
                "  workflow_dispatch:\n",
                "  schedule:\n    - cron: '0 0 * * *'\n  workflow_dispatch:\n", 1)), independent),
        (publisher, replace_load_missing_trigger_header(
            independent, i_header, i_header + "  workflow_dispatch:\n")),
    )
    for p, i in topology:
        must_reject(p, i)
    print("PASS: load-missing-evidence exact trigger matrix: "
          + str(omissions) + " omissions, " + str(additions)
          + " additions/duplicates, " + str(shortened)
          + " shortened inventories, " + str(len(topology)) + " event topology negatives")



def validate_yaml_root_permission(publisher: str, independent: str) -> None:
    """Pin reviewed root YAML mapping and read-only permission leaves."""
    for label, value, roots in (
        ("publisher", publisher, ["name: Reconcile Load Missing Evidence",
                                  "on:", "permissions:", "concurrency:", "jobs:"]),
        ("independent", independent, ["name: Load Missing Evidence Source Negative",
                                      "on:", "permissions:", "jobs:"]),
    ):
        actual = [line for line in value.splitlines()
                  if line.strip() and not line[0].isspace()
                  and not line.lstrip().startswith("#")]
        if actual != roots:
            raise AssertionError("load-missing " + label + " root YAML key shadow drift")
        if value.count("\npermissions:\n") != 1:
            raise AssertionError("load-missing " + label + " permission boundary drift")
        leaves = []
        for line in value.split("\npermissions:\n", 1)[1].splitlines():
            if line.strip() and not line[0].isspace():
                break
            if line.strip() and not line.lstrip().startswith("#"):
                leaves.append(line)
        if leaves != ["  contents: read"]:
            raise AssertionError("load-missing " + label + " permission leaf shadow drift")


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
            raise AssertionError("load-missing " + label + " permission fixture anchor drift")
        for mutation, leaf in (
            ("spaced contents", "  contents : write\n"),
            ("quoted contents", "  'contents': write\n"),
        ):
            cases.append((mutation, value.replace(marker, marker + leaf, 1),
                          "permission leaf shadow drift"))
        for mutation, changed, diagnostic in cases:
            if changed == value:
                raise AssertionError("load-missing unchanged YAML fixture: " + mutation)
            try:
                if is_publisher:
                    validate_yaml_root_permission(changed, other)
                else:
                    validate_yaml_root_permission(other, changed)
            except AssertionError as exc:
                expected = "load-missing " + label + " " + diagnostic
                if str(exc) != expected:
                    raise AssertionError("load-missing wrong YAML diagnostic: "
                                         + label + " " + mutation + ": " + str(exc)) from exc
            else:
                raise AssertionError("load-missing accepted YAML shadow: " + label + " " + mutation)
            count += 1
    if count != 12:
        raise AssertionError("load-missing YAML negative inventory drift")
    print("PASS: load-missing root/permission YAML authority (12 exact-diagnostic negatives)")


def load_missing_concurrency_authority(publisher: str) -> None:
    """Pin reviewed event-scoped noncancelling publisher serialization."""
    marker = "\nconcurrency:\n"
    if publisher.count(marker) != 1 or publisher.count("\njobs:\n") != 1:
        raise SystemExit("load-missing publisher concurrency authority drift")
    observed = publisher.split(marker, 1)[1].split("\njobs:\n", 1)[0]
    expected = ("  group: reconcile-load-missing-evidence-" + chr(36)
                + "{{ github.event_name }}-" + chr(36)
                + "{{ github.event.pull_request.number || 'so' }}\n"
                + "  cancel-in-progress: false\n")
    if observed != expected:
        raise SystemExit("load-missing publisher concurrency authority drift")


def load_missing_concurrency_negatives(publisher: str) -> None:
    """Prove twelve exact-diagnostic effective YAML concurrency mutations."""
    marker = "\nconcurrency:\n"
    original = ("  group: reconcile-load-missing-evidence-" + chr(36)
                + "{{ github.event_name }}-" + chr(36)
                + "{{ github.event.pull_request.number || 'so' }}\n"
                + "  cancel-in-progress: false\n")
    anchor = marker + original + "\njobs:\n"
    if publisher.count(anchor) != 1:
        raise SystemExit("load-missing concurrency fixture anchor drift")
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
        raise SystemExit("load-missing concurrency fixture inventory drift")
    load_missing_concurrency_authority(publisher)
    for name, replacement in cases:
        altered = publisher.replace(anchor, marker + replacement + "\njobs:\n", 1)
        if altered == publisher:
            raise SystemExit("load-missing unchanged concurrency fixture: " + name)
        try:
            load_missing_concurrency_authority(altered)
        except SystemExit as exc:
            if str(exc) != "load-missing publisher concurrency authority drift":
                raise SystemExit("load-missing wrong concurrency diagnostic: "
                                 + name + ": " + str(exc)) from exc
        else:
            raise SystemExit("load-missing accepted concurrency mutation: " + name)
    print("PASS: load-missing publisher concurrency (12 exact-diagnostic negatives)")


LOAD_MISSING_JOB_HEADERS = [{"label":"publisher","name":"validate-pr","header":"    if: github.event_name == 'pull_request' && github.base_ref == 'so'\n    permissions:\n      contents: read\n    runs-on: ubuntu-latest\n    timeout-minutes: 5"},{"label":"publisher","name":"reconcile","header":"    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n    permissions:\n      contents: write\n    runs-on: ubuntu-latest\n    timeout-minutes: 5"},{"label":"independent","name":"source-negative","header":"    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n    permissions:\n      contents: read\n    runs-on: ubuntu-latest\n    timeout-minutes: 5"}]


def load_missing_job_authority(publisher: str, independent: str) -> None:
    """Pin reviewed effective job mapping and pre-step permission/execution authority."""
    for label, content, names in (
        ("publisher", publisher, ("validate-pr", "reconcile")),
        ("independent", independent, ("source-negative",)),
    ):
        diagnostic = "load-missing " + label + " job authority drift"
        if content.count("\njobs:\n") != 1:
            raise SystemExit(diagnostic)
        section = content.split("\njobs:\n", 1)[1]
        mappings = [line for line in section.splitlines()
                    if line.startswith("  ") and not line.startswith("    ")
                    and line.strip() and not line.lstrip().startswith("#")]
        if mappings != ["  " + name + ":" for name in names]:
            raise SystemExit(diagnostic)
        for item in LOAD_MISSING_JOB_HEADERS:
            if item["label"] != label:
                continue
            anchor = "\n  " + item["name"] + ":\n"
            if content.count(anchor) != 1:
                raise SystemExit(diagnostic)
            actual = content.split(anchor, 1)[1].split("\n    steps:\n", 1)[0]
            if actual != item["header"]:
                raise SystemExit(diagnostic)


def load_missing_job_negatives(publisher: str, independent: str) -> None:
    """Prove 40 exact-diagnostic job mapping, condition and permission negatives."""
    load_missing_job_authority(publisher, independent)
    total = 0
    for item in LOAD_MISSING_JOB_HEADERS:
        label, name, original = item["label"], item["name"], item["header"]
        content = publisher if label == "publisher" else independent
        anchor = "\n  " + name + ":\n" + original + "\n    steps:\n"
        if content.count(anchor) != 1:
            raise SystemExit("load-missing job fixture anchor drift: " + name)
        leaf = "write" if name == "reconcile" else "read"
        opposite = "read" if leaf == "write" else "write"
        first_if = original.splitlines(keepends=True)[0]
        cases = (
            ("condition bypass", original.replace(first_if, "    if: always()\n", 1)),
            ("permission change", original.replace("      contents: " + leaf,
                                                    "      contents: " + opposite, 1)),
            ("runner change", original.replace("    runs-on: ubuntu-latest",
                                               "    runs-on: ubuntu-24.04", 1)),
            ("timeout change", original.replace("    timeout-minutes: ",
                                                "    timeout-minutes: 1 # ", 1)),
            ("continuation override", original + "\n    continue-on-error: true"),
            ("duplicate permission", original + "\n    permissions:\n      contents: write"),
            ("quoted permission", original.replace("      contents: " + leaf,
                                                  "      'contents': " + opposite, 1)),
            ("spaced permission", original.replace("      contents: " + leaf,
                                                  "      contents : " + opposite, 1)),
            ("duplicate condition", original + "\n    if: always()"),
            ("spaced condition", original.replace(first_if, "    if : always()\n", 1)),
        )
        for name_case, changed in cases:
            altered = content.replace(anchor, "\n  " + name + ":\n"
                                      + changed + "\n    steps:\n", 1)
            if altered == content:
                raise SystemExit("load-missing unchanged job fixture: " + name + "/" + name_case)
            try:
                if label == "publisher":
                    load_missing_job_authority(altered, independent)
                else:
                    load_missing_job_authority(publisher, altered)
            except SystemExit as exc:
                expected = "load-missing " + label + " job authority drift"
                if str(exc) != expected:
                    raise SystemExit("load-missing wrong job diagnostic: "
                                     + name + "/" + name_case + ": " + str(exc)) from exc
            else:
                raise SystemExit("load-missing accepted job mutation: " + name + "/" + name_case)
            total += 1
    for label, content, name in (
        ("publisher", publisher, "validate-pr"),
        ("independent", independent, "source-negative"),
    ):
        for name_case, changed in (
            ("duplicate mapping", content + "\n  " + name + ":\n"),
            ("quoted mapping", content + "\n  '" + name + "':\n"),
            ("spaced mapping", content + "\n  " + name + " :\n"),
            ("extra mapping", content + "\n  unreviewed:\n"),
            ("missing mapping", content.replace("\n  " + name + ":\n",
                                                "\n  missing-job:\n", 1)),
        ):
            if changed == content:
                raise SystemExit("load-missing unchanged mapping fixture: " + name_case)
            try:
                if label == "publisher":
                    load_missing_job_authority(changed, independent)
                else:
                    load_missing_job_authority(publisher, changed)
            except SystemExit as exc:
                if str(exc) != "load-missing " + label + " job authority drift":
                    raise SystemExit("load-missing wrong mapping diagnostic: " + name_case) from exc
            else:
                raise SystemExit("load-missing accepted job mapping: " + name_case)
            total += 1
    if total != 40:
        raise SystemExit("load-missing job negative inventory drift")
    print("PASS: load-missing publisher/independent job authority (40 exact-diagnostic negatives)")

def policy(s: str) -> None:
    if s.count(CHECKOUT) != 2 or s.count(SETUP) != 2:
        raise AssertionError("missing-evidence immutable Actions drift")
    if s.count("persist-credentials: false") != 1 or s.count("persist-credentials: true") != 1:
        raise AssertionError("missing-evidence credential separation drift")
    if "actions/checkout@v4" in s or "actions/setup-python@v5" in s:
        raise AssertionError("missing-evidence floating Action regression")
    for marker in REQUIRED:
        if marker not in s:
            raise AssertionError("missing-evidence required source marker absent: " + marker)
    if s.count('test -z "$(git status --porcelain)"') != 3:
        raise AssertionError("missing-evidence source/final clean multiplicity drift")

def step(source: str, name: str) -> str:
    marker = "      - name: " + name + "\n"
    if source.count(marker) != 1:
        raise AssertionError("missing-evidence step missing/duplicated: " + name)
    start = source.index("        run: |\n", source.index(marker)) + len("        run: |\n")
    boundaries = [p for p in (source.find("\n      - name:", start),
                             source.find("\n  reconcile:", start),
                             source.find("\n  validate-pr:", start)) if p >= 0]
    end = min(boundaries) if boundaries else len(source)
    lines = source[start:end].splitlines()
    if any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("missing-evidence shell crossed job boundary")
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"

def runtime(source: str, name: str, cases: tuple, prefix_only: bool) -> None:
    shell = step(source, name)
    if prefix_only:
        if shell.count("python -m py_compile") != 1:
            raise AssertionError("missing-evidence PR validator boundary drift")
        shell = shell.split("python -m py_compile", 1)[0]
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
                raise AssertionError(f"missing-evidence actual shell source drift: {name} {(event, base, ref, sha, result.returncode)}")
            if accepted and not prefix_only and envfile.read_text() != "SOURCE_SHA=" + head + "\n":
                raise AssertionError("missing-evidence writer source SHA capture drift")
    print(f"PASS: missing-evidence {name} actual event/base/ref/SHA shell ({len(cases)} cases)")

def cas_runtime(source: str) -> None:
    """Execute the real blocker publisher commit/CAS shell in a disposable fake-Git sandbox."""
    shell = step(source, "Commit canonical blocker cleanup")
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
if args[:2] == ["rev-parse", "origin/so"]:
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
                raise AssertionError(f"missing-evidence CAS {label}: unexpected exit {result.returncode}: {result.stderr[-100:]}")
            if sum(line == "push origin HEAD:so" for line in calls) != pushes:
                raise AssertionError("missing-evidence CAS pushed on stale/no-op/invalid source: " + label)
            if label == "noop" and any(line.startswith("commit ") for line in calls):
                raise AssertionError("missing-evidence no-op committed")
    print(f"PASS: missing-evidence actual publisher CAS/no-op shell ({len(cases)} cases)")

def main() -> None:
    source = read(PUBLISHER)
    independent = read(INDEPENDENT)
    reconciler = read(RECONCILER)
    for marker in (PUBLISHER, SELF, CHECKOUT, SETUP, "persist-credentials: false",
                   "contents: read", 'test -z "$(git status --porcelain)"'):
        if marker not in independent:
            raise AssertionError("missing-evidence independent CI reachability missing: " + marker)
    if RECONCILER not in source:
        raise AssertionError("missing-evidence canonical reconciler not reached from publisher")
    if blob(reconciler) != REVIEWED_RECONCILER:
        raise AssertionError("missing-evidence complete reconciler Git blob drift")
    if blob(reconciler + "\n# synthetic whole-source drift\n") == REVIEWED_RECONCILER:
        raise AssertionError("missing-evidence reconciler source mutation accepted")
    if blob(source) != REVIEWED_PUBLISHER:
        raise AssertionError("missing-evidence complete publisher Git blob drift")
    if blob(independent) != REVIEWED_INDEPENDENT:
        raise AssertionError("missing-evidence complete independent CI Git blob drift")
    if blob(independent + "\n# synthetic whole-source drift\n") == REVIEWED_INDEPENDENT:
        raise AssertionError("missing-evidence independent CI mutation accepted")
    if blob(source + "\n# synthetic whole-source drift\n") == REVIEWED_PUBLISHER:
        raise AssertionError("missing-evidence whole-source mutation accepted")
    policy(source)
    load_missing_validate_trigger_matrix(source, independent)
    load_missing_trigger_matrix_negatives(source, independent)
    validate_yaml_root_permission(source, independent)
    yaml_root_permission_negatives(source, independent)
    load_missing_concurrency_authority(source)
    load_missing_concurrency_negatives(source)
    load_missing_job_authority(source, independent)
    load_missing_job_negatives(source, independent)
    for index, marker in enumerate(REQUIRED):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE", 1)
        if changed == source:
            raise AssertionError("missing-evidence negative unreachable: " + str(index))
        try:
            policy(changed)
        except AssertionError:
            continue
        raise AssertionError("missing-evidence source mutation accepted: " + str(index))
    print(f"PASS: missing-evidence publisher/reconciler reviewed blobs and {len(REQUIRED)} source negatives")
    head = "a" * 40
    runtime(source, "Normalize read-only PR blocker authority", (
        ("pull_request", "so", "", head, True),
        ("pull_request", "main", "", head, False),
        ("push", "so", "", head, False),
        ("pull_request", "so", "", "b" * 40, False),
        ("pull_request", "so", "", "A" * 40, False),
        ("pull_request", "so", "", "a" * 39, False),
    ), True)
    runtime(source, "Capture exact clean source", (
        ("push", "", "refs/heads/so", head, True),
        ("workflow_dispatch", "", "refs/heads/so", head, True),
        ("schedule", "", "refs/heads/so", head, False),
        ("pull_request", "", "refs/heads/so", head, False),
        ("push", "", "refs/heads/main", head, False),
        ("push", "", "refs/heads/so", "b" * 40, False),
        ("push", "", "refs/heads/so", "A" * 40, False),
        ("push", "", "refs/heads/so", "a" * 39, False),
    ), False)
    cas_runtime(source)
    print("PASS: independent read-only missing-evidence source guard; production evidence generated: false")

if __name__ == "__main__":
    main()
