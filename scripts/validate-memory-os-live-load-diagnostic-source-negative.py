#!/usr/bin/env python3
"""Independent exact-source negative and runtime checks for live load diagnostics."""
from __future__ import annotations
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-live-load-authority-v2.yml"
INDEPENDENT = ".github/workflows/live-load-authority-diagnostic-source-negative.yml"
PR = ".github/workflows/reconcile-live-load-authority-v2-pr.yml"
SELF = "scripts/validate-memory-os-live-load-diagnostic-source-negative.py"
TARGET = "docs/fixtures/memory-os-operability/live-load-authority-diagnostic.last.json"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
REVIEWED_PUBLISHER = "e83eb41e981e42499cba5c30861c67320d3e804b"
REVIEWED_PR = "2a02dd661662a1ed60676c7b20f2b3e53e2f8cdf"
REVIEWED_INDEPENDENT = "dc50ba77b412001552410c2ec1e1f1a5f0b401de"

def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def require_reviewed_source(content: str, expected: str, label: str) -> None:
    if blob(content) != expected:
        raise AssertionError("live load " + label + " complete Git blob drift")

def reviewed_blob_negatives(publisher: str, pr: str, independent: str) -> None:
    require_reviewed_source(publisher, REVIEWED_PUBLISHER, "publisher")
    require_reviewed_source(pr, REVIEWED_PR, "PR")
    require_reviewed_source(independent, REVIEWED_INDEPENDENT, "independent CI")
    for label, original, expected in (
        ("publisher", publisher, REVIEWED_PUBLISHER),
        ("PR", pr, REVIEWED_PR),
        ("independent CI", independent, REVIEWED_INDEPENDENT),
    ):
        try:
            require_reviewed_source(original + "\n# synthetic source drift\n", expected, label)
        except AssertionError:
            continue
        raise AssertionError("live load reviewed Git blob accepted synthetic source drift: " + label)
    print("PASS: live load publisher, PR and independent CI complete Git blob source negatives (3 cases)")

def read(path: str) -> str:
    target = ROOT / path
    if target.is_symlink() or not target.is_file() or target.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise AssertionError("live load source substituted: " + path)
    return target.read_text(encoding="utf-8")

def step(text: str, name: str) -> str:
    marker = "      - name: " + name + "\n"
    if text.count(marker) != 1:
        raise AssertionError("live load step missing/duplicated: " + name)
    begin = text.index("        run: |\n", text.index(marker)) + len("        run: |\n")
    end = text.find("\n      - name:", begin)
    lines = text[begin:end if end >= 0 else len(text)].splitlines()
    if any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("live load shell indentation drift")
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"

REQUIRED = (
    "trap 'rm -f \"$log\"' EXIT",
    'python scripts/validate-memory-os-live-load.py >"$log" 2>&1 || postgres_code=$?',
    'python scripts/validate-memory-os-live-object-load.py >>"$log" 2>&1 || object_code=$?',
    'if [ "$code" -eq 0 ]; then',
    'echo "exit_code=$code" >> "$GITHUB_OUTPUT"',
    "'output': 'Live load validation completed; raw validator output withheld.'",
    "'containsSecrets': False",
    "'productionDecision': 'NO_GO'",
    "candidate.is_symlink()",
    "path.parent.resolve(strict=True).relative_to(repo)",
    "path.exists() and not path.is_file()",
    "os.fchmod(fd, mode)",
    "os.fsync(handle.fileno())",
    "os.replace(temp_path, path)",
    "temp_path.unlink()",
    "git fetch origin so",
)

LIVE_LOAD_WRITER_PUSH = (
    ".github/workflows/reconcile-live-load-authority-v2.yml",
    ".github/workflows/reconcile-live-load-authority-v2-pr.yml",
    "contracts/operations/live-postgres-load-scenario-contract.v1.json",
    "contracts/operations/live-object-load-scenario-contract.v1.json",
    "docs/fixtures/memory-os-operability/live-postgres-load-results.sample.v1.json",
    "docs/fixtures/memory-os-operability/live-object-load-results.sample.v1.json",
    "scripts/validate-memory-os-live-load.py",
    "scripts/validate-memory-os-live-object-load.py",
    "scripts/validate-memory-os-load.py",
    "scripts/validate-memory-os-operability.py",
    "scripts/reconcile-memory-os-live-load-status.py",
    "scripts/validate-memory-os-live-load-reconcile-rollback-negative.py",
)

LIVE_LOAD_PR_PATHS = (
    ".github/workflows/reconcile-live-load-authority-v2.yml",
    ".github/workflows/reconcile-live-load-authority-v2-pr.yml",
    "contracts/operations/live-postgres-load-scenario-contract.v1.json",
    "contracts/operations/live-object-load-scenario-contract.v1.json",
    "docs/fixtures/memory-os-operability/live-postgres-load-results.sample.v1.json",
    "docs/fixtures/memory-os-operability/live-object-load-results.sample.v1.json",
    "scripts/validate-memory-os-live-load.py",
    "scripts/validate-memory-os-live-object-load.py",
    "scripts/validate-memory-os-load.py",
    "scripts/validate-memory-os-operability.py",
    "scripts/reconcile-memory-os-live-load-status.py",
    "scripts/validate-memory-os-live-load-reconcile-rollback-negative.py",
)

LIVE_LOAD_INDEPENDENT_PR = (
    ".github/workflows/reconcile-live-load-authority-v2.yml",
    ".github/workflows/reconcile-live-load-authority-v2-pr.yml",
    ".github/workflows/live-load-authority-diagnostic-source-negative.yml",
    "scripts/validate-memory-os-live-load-diagnostic-source-negative.py",
)

LIVE_LOAD_INDEPENDENT_PUSH = (
    ".github/workflows/reconcile-live-load-authority-v2.yml",
    ".github/workflows/reconcile-live-load-authority-v2-pr.yml",
    ".github/workflows/live-load-authority-diagnostic-source-negative.yml",
    "scripts/validate-memory-os-live-load-diagnostic-source-negative.py",
)

def live_load_trigger_event(event: str, paths: tuple[str, ...]) -> str:
    return ("  " + event + ":\n    branches:\n      - so\n    paths:\n"
            + "".join('      - "' + path + '"\n' for path in paths))


def live_load_trigger_header(content: str) -> str:
    if content.count("\non:\n") != 1 or content.count("\npermissions:\n") != 1:
        raise AssertionError("live-load event trigger header ambiguous")
    return content.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]


def live_load_trigger_matrix(
    writer: str, pr: str, independent: str,
    writer_push: tuple[str, ...] = LIVE_LOAD_WRITER_PUSH,
    pr_paths: tuple[str, ...] = LIVE_LOAD_PR_PATHS,
    independent_pr: tuple[str, ...] = LIVE_LOAD_INDEPENDENT_PR,
    independent_push: tuple[str, ...] = LIVE_LOAD_INDEPENDENT_PUSH,
) -> None:
    expected_writer = (live_load_trigger_event("push", writer_push)
                       + '  schedule:\n    - cron: "7 6 * * *"\n'
                       + "  workflow_dispatch:\n")
    expected_pr = live_load_trigger_event("pull_request", pr_paths)
    expected_independent = (live_load_trigger_event("pull_request", independent_pr)
                            + live_load_trigger_event("push", independent_push))
    for label, content, expected in (
        ("writer", writer, expected_writer),
        ("PR", pr, expected_pr),
        ("independent", independent, expected_independent),
    ):
        if live_load_trigger_header(content) != expected:
            raise AssertionError("live-load " + label + " exact trigger matrix drift")
    live_load_validate_yaml_root_permissions(writer, pr, independent)



def live_load_validate_yaml_root_permissions(
    writer: str, pr: str, independent: str
) -> None:
    """Pin distinct writer/PR/independent effective YAML permission authorities."""
    for label, content, expected_roots, permission in (
        ("writer", writer, [
            "name: Reconcile Live Load Authority V2", "on:", "permissions:",
            "concurrency:", "jobs:",
        ], "write"),
        ("PR", pr, [
            "name: Validate Live Load Authority V2 PR", "on:", "permissions:",
            "concurrency:", "jobs:",
        ], "read"),
        ("independent", independent, [
            "name: Live Load Authority Diagnostic Source Negative", "on:",
            "permissions:", "jobs:",
        ], "read"),
    ):
        roots = [
            line for line in content.splitlines()
            if line.strip() and not line[0].isspace()
            and not line.lstrip().startswith("#")
        ]
        if roots != expected_roots:
            raise AssertionError("live-load " + label + " root YAML key shadow drift")
        if content.count("\npermissions:\n") != 1:
            raise AssertionError("live-load " + label + " permission leaf shadow drift")
        permission_rows = []
        for line in content.split("\npermissions:\n", 1)[1].splitlines():
            if line.strip() and not line[0].isspace():
                break
            if line.strip() and not line.lstrip().startswith("#"):
                permission_rows.append(line)
        if permission_rows != ["  contents: " + permission]:
            raise AssertionError("live-load " + label + " permission leaf shadow drift")


def live_load_yaml_shadow_negatives(writer: str, pr: str, independent: str) -> None:
    total = 0
    sources = (writer, pr, independent)
    for index, (label, content, permission) in enumerate((
        ("writer", writer, "write"),
        ("PR", pr, "read"),
        ("independent", independent, "read"),
    )):
        cases = []
        for name, suffix in (
            ("spaced on", "on :\n  issues:\n"),
            ("quoted on", "'on':\n  issues:\n"),
            ("spaced permissions", "permissions :\n  contents: write\n"),
            ("spaced jobs", "jobs : {}\n"),
        ):
            cases.append((name, content + "\n" + suffix, "root YAML key shadow drift"))
        anchor = "permissions:\n  contents: " + permission + "\n"
        if content.count(anchor) != 1:
            raise AssertionError("live-load " + label + " permission mutation anchor drift")
        shadow_value = "read" if permission == "write" else "write"
        for name, extra in (
            ("spaced contents", "  contents : " + shadow_value + "\n"),
            ("quoted contents", "  'contents': " + shadow_value + "\n"),
        ):
            cases.append((name, content.replace(anchor, anchor + extra, 1),
                          "permission leaf shadow drift"))
        for name, altered, diagnostic in cases:
            if altered == content:
                raise AssertionError("live-load YAML fixture unchanged: " + label + "/" + name)
            mutated = list(sources)
            mutated[index] = altered
            try:
                live_load_trigger_matrix(*mutated)
            except AssertionError as exc:
                expected = "live-load " + label + " " + diagnostic
                if str(exc) != expected:
                    raise AssertionError(
                        "live-load YAML wrong diagnostic: " + label + "/" + name
                        + ": " + str(exc)
                    ) from exc
            else:
                raise AssertionError("live-load accepted YAML shadow: " + label + "/" + name)
            total += 1
    if total != 18:
        raise AssertionError("live-load YAML fixture count drift")
    print("PASS: live-load writer/PR/independent YAML root/permission (18 exact-diagnostic negatives)")


def live_load_trigger_replace(content: str, old: str, new: str) -> str:
    anchor = "\non:\n" + old + "\npermissions:\n"
    if content.count(anchor) != 1 or old == new:
        raise AssertionError("live-load trigger mutation fixture unreachable")
    return content.replace(anchor, "\non:\n" + new + "\npermissions:\n", 1)


def live_load_trigger_negatives(writer: str, pr: str, independent: str) -> None:
    def reject(index: int, altered: str) -> None:
        sources = [writer, pr, independent]
        sources[index] = altered
        try:
            live_load_trigger_matrix(*sources)
        except AssertionError:
            return
        raise AssertionError("live-load accepted event trigger mutation")

    omissions = additions = 0
    for index, event, paths in (
        (0, "push", LIVE_LOAD_WRITER_PUSH),
        (1, "pull_request", LIVE_LOAD_PR_PATHS),
        (2, "pull_request", LIVE_LOAD_INDEPENDENT_PR),
        (2, "push", LIVE_LOAD_INDEPENDENT_PUSH),
    ):
        original = (writer, pr, independent)[index]
        header = live_load_trigger_header(original)
        block = live_load_trigger_event(event, paths)
        if header.count(block) != 1:
            raise AssertionError("live-load event trigger fixture ambiguous")
        for position in range(len(paths)):
            changed = live_load_trigger_replace(
                original, header,
                header.replace(block, live_load_trigger_event(
                    event, paths[:position] + paths[position + 1:]), 1))
            reject(index, changed)
            omissions += 1
        first = '      - "' + paths[0] + '"\n'
        for extra in (
            '      - "unreviewed/**"\n', '      - unreviewed/**\n',
            first, '      - ' + paths[0] + '\n',
        ):
            changed = live_load_trigger_replace(
                original, header,
                header.replace(block, block.replace(first, first + extra, 1), 1))
            reject(index, changed)
            additions += 1

    shortened = 0
    for field, paths in (
        ("writer_push", LIVE_LOAD_WRITER_PUSH),
        ("pr_paths", LIVE_LOAD_PR_PATHS),
        ("independent_pr", LIVE_LOAD_INDEPENDENT_PR),
        ("independent_push", LIVE_LOAD_INDEPENDENT_PUSH),
    ):
        try:
            live_load_trigger_matrix(writer, pr, independent, **{field: paths[:-1]})
        except AssertionError:
            shortened += 1
        else:
            raise AssertionError("live-load accepted shortened trigger inventory")

    wh, ph, ih = map(live_load_trigger_header, (writer, pr, independent))
    topology = (
        (0, live_load_trigger_replace(writer, wh, "  pull_request:\n    branches:\n      - so\n" + wh)),
        (0, live_load_trigger_replace(writer, wh, wh.replace('  schedule:\n    - cron: "7 6 * * *"\n', "", 1))),
        (0, live_load_trigger_replace(writer, wh, wh.replace('7 6 * * *', '0 0 * * *', 1))),
        (1, live_load_trigger_replace(pr, ph, ph + "  push:\n    branches:\n      - so\n")),
        (2, live_load_trigger_replace(independent, ih, ih + "  workflow_dispatch:\n")),
    )
    for index, changed in topology:
        reject(index, changed)
    print("PASS: live-load exact event trigger matrix: " + str(omissions)
          + " omissions, " + str(additions) + " additions/duplicates, "
          + str(shortened) + " shortened inventories, "
          + str(len(topology)) + " event topology/schedule negatives")


def policy(source: str) -> None:
    for marker in REQUIRED:
        if marker not in source:
            raise AssertionError("live load policy missing: " + marker[:70])
    if source.count(CHECKOUT) != 1 or source.count(SETUP) != 1:
        raise AssertionError("live load immutable Actions drift")
    if source.count("git fetch origin so") != 4:
        raise AssertionError("live load CAS fetch multiplicity drift")
    for forbidden in ("read_text(\n              encoding='utf-8', errors='replace'", "output = re.sub(", "[-10000:]", "actions/checkout@v4", "actions/setup-python@v5"):
        if forbidden in source:
            raise AssertionError("live load raw diagnostic/floating Action regression")
    if "permissions:\n  contents: write" not in source:
        raise AssertionError("live load writer permission drift")

def mutations(source: str) -> None:
    for index, marker in enumerate(REQUIRED):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE_TEST", 1)
        if changed == source:
            raise AssertionError("unreachable live load mutation " + str(index))
        try:
            policy(changed)
        except AssertionError:
            continue
        raise AssertionError("live load policy accepted mutation " + str(index))
    print(f"PASS: live load diagnostic source mutations ({len(REQUIRED)} cases)")

def writer_runtime(source: str) -> None:
    shell = step(source, "Validate committed live evidence")
    if shell.count("python - <<'PY'\n") != 1 or shell.count("\nPY\n") != 1:
        raise AssertionError("live load writer heredoc missing")
    code = shell.split("python - <<'PY'\n", 1)[1].split("\nPY\n", 1)[0] + "\n"
    for case in ("existing", "new", "replace", "fsync", "symlink", "parent", "directory", "bad_sha", "bad_exit"):
        with tempfile.TemporaryDirectory(prefix="live-load-diagnostic-") as temp:
            root = Path(temp)
            parent = root / Path(TARGET).parent
            parent.mkdir(parents=True)
            target = root / TARGET
            outside = root / "outside"
            outside.mkdir()
            canary = outside / "canary"
            canary.write_bytes(b"SYNTHETIC_SECRET_CANARY")
            if case in ("existing", "replace", "fsync"):
                target.write_bytes(b"before\n")
                target.chmod(0o640)
            if case == "symlink":
                target.symlink_to(canary)
            if case == "parent":
                parent.rmdir()
                parent.symlink_to(outside, target_is_directory=True)
            if case == "directory":
                target.mkdir()
            inject = ""
            if case in ("replace", "fsync"):
                operation = "replace" if case == "replace" else "fsync"
                inject = "import os\ndef deny(*args): raise OSError('synthetic failure')\nos." + operation + " = deny\n"
            env = dict(os.environ, SOURCE_SHA="a" * (39 if case == "bad_sha" else 40),
                       VALIDATION_EXIT_CODE="999" if case == "bad_exit" else "17")
            result = subprocess.run([sys.executable, "-c", inject + code], cwd=root,
                                    env=env, capture_output=True, text=True, timeout=10, check=False)
            accepted = case in ("existing", "new")
            if (result.returncode == 0) != accepted:
                raise AssertionError("live load diagnostic writer acceptance drift: " + case + " " + result.stderr[-200:])
            if canary.read_bytes() != b"SYNTHETIC_SECRET_CANARY":
                raise AssertionError("live load diagnostic escaped target")
            if accepted:
                value = json.loads(target.read_text(encoding="utf-8"))
                if value["output"] != "Live load validation completed; raw validator output withheld." or value["containsSecrets"] or value["productionDecision"] != "NO_GO" or value["productionEvidence"] or value["productionReady"] or value["exitCode"] != 17:
                    raise AssertionError("live load diagnostic redaction/authority drift")
                if stat.S_IMODE(target.stat().st_mode) != (0o640 if case == "existing" else 0o600):
                    raise AssertionError("live load diagnostic mode drift")
            if case in ("replace", "fsync"):
                if target.read_bytes() != b"before\n" or stat.S_IMODE(target.stat().st_mode) != 0o640:
                    raise AssertionError("live load diagnostic rollback drift")
            if list(parent.glob(".*.tmp")):
                raise AssertionError("live load diagnostic temp residue")
    print("PASS: actual live load diagnostic writer atomic/symlink/privacy runtime (9 cases)")

def validator_shell_runtime(source: str) -> None:
    shell = step(source, "Validate committed live evidence")
    for pg, obj, expected in ((0, 0, 0), (17, 0, 17), (0, 23, 23), (17, 23, 17)):
        with tempfile.TemporaryDirectory(prefix="live-load-shell-") as temp:
            root = Path(temp)
            stub = root / "python"
            stub.write_text("#!/bin/sh\ncase \"$1\" in\n"
                            "  scripts/validate-memory-os-live-load.py) echo SYNTHETIC_SECRET_CANARY; exit \"$PG_EXIT\";;\n"
                            "  scripts/validate-memory-os-live-object-load.py) echo SYNTHETIC_SECRET_CANARY; exit \"$OBJECT_EXIT\";;\n"
                            "  -) cat >/dev/null; exit 0;;\n"
                            "  *) exit 91;;\nesac\n", encoding="utf-8")
            stub.chmod(0o755)
            output = root / "github-output"
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       TMPDIR=str(root), GITHUB_OUTPUT=str(output), PG_EXIT=str(pg),
                       OBJECT_EXIT=str(obj), SOURCE_SHA="a" * 40)
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
            if result.returncode != 0 or output.read_text(encoding="utf-8") != f"exit_code={expected}\n":
                raise AssertionError("live load first/second validator failure swallowed: " + str((pg, obj, result.returncode, result.stderr[-100:])))
            if "SYNTHETIC_SECRET_CANARY" in result.stdout + result.stderr:
                raise AssertionError("live load validator shell exposed raw log")
            if list(root.glob("tmp.*")):
                raise AssertionError("live load validator shell temp residue")
    print("PASS: live load first/second validator exit and secret-free shell runtime (4 cases)")

def pr_policy(source: str) -> None:
    required = (
        "if: github.event_name == 'pull_request' && github.base_ref == 'so'",
        "permissions:\\n      contents: read",
        "persist-credentials: false",
        'test "${GITHUB_EVENT_NAME:-}" = "pull_request"',
        'test "${GITHUB_BASE_REF:-}" = "so"',
        '[[ "$PR_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]',
        'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"',
        'test -z "$(git status --porcelain)"',
    )
    for marker in required:
        if marker.replace("\\n", "\n") not in source:
            raise AssertionError("live load PR source policy missing: " + marker)
    if source.count(CHECKOUT) != 1 or source.count(SETUP) != 1:
        raise AssertionError("live load PR immutable Actions drift")
    if source.count('test -z "$(git status --porcelain)"') != 2:
        raise AssertionError("live load PR clean worktree checks must remain at source and final boundary")
    if "actions/checkout@v4" in source or "actions/setup-python@v5" in source:
        raise AssertionError("live load PR floating Action regression")

def pr_mutations(source: str) -> None:
    required = (
        "if: github.event_name == 'pull_request' && github.base_ref == 'so'",
        "persist-credentials: false",
        'test "${GITHUB_EVENT_NAME:-}" = "pull_request"',
        'test "${GITHUB_BASE_REF:-}" = "so"',
        '[[ "$PR_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]',
        'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"',
        'test -z "$(git status --porcelain)"',
        CHECKOUT,
        SETUP,
    )
    for index, marker in enumerate(required):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE_TEST", 1)
        if changed == source:
            raise AssertionError("live load PR mutation unreachable: " + str(index))
        try:
            pr_policy(changed)
        except AssertionError:
            continue
        raise AssertionError("live load PR mutation accepted: " + str(index))
    print(f"PASS: live load PR source mutations ({len(required)} cases)")

def pr_identity_runtime(source: str) -> None:
    shell = step(source, "Verify exact clean PR source")
    head = "a" * 40
    cases = (
        ("pull_request", "so", head, True),
        ("pull_request", "main", head, False),
        ("push", "so", head, False),
        ("pull_request", "so", "b" * 40, False),
        ("pull_request", "so", "A" * 40, False),
        ("pull_request", "so", "a" * 39, False),
    )
    with tempfile.TemporaryDirectory(prefix="live-load-pr-identity-") as temp:
        root = Path(temp)
        stub = root / "git"
        stub.write_text("#!/bin/sh\n"
                        "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"HEAD\" ]; then printf '" + head + "\\n'; exit 0; fi\n"
                        "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then exit 0; fi\n"
                        "exit 1\n", encoding="utf-8")
        stub.chmod(0o755)
        for event, base, sha, accepted in cases:
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_EVENT_NAME=event, GITHUB_BASE_REF=base, PR_HEAD_SHA=sha)
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != accepted:
                raise AssertionError("live load PR identity shell drift: " + str((event, base, sha, result.returncode)))
    print("PASS: live load PR event/base/head SHA shell runtime (6 cases)")

def independent_identity_runtime(source: str) -> None:
    shell = step(source, "Require exact clean live load diagnostic source")
    head = "a" * 40
    cases = (
        ("pull_request", "so", "", head, "", True),
        ("pull_request", "main", "", head, "", False),
        ("pull_request", "so", "", "b" * 40, "", False),
        ("pull_request", "so", "", "A" * 40, "", False),
        ("pull_request", "so", "", "", "", False),
        ("push", "", "refs/heads/so", "", head, True),
        ("push", "", "refs/heads/main", "", head, False),
        ("push", "", "refs/heads/so", "", "b" * 40, False),
        ("push", "", "refs/heads/so", "", "A" * 40, False),
        ("push", "", "refs/heads/so", "", "a" * 39, False),
        ("schedule", "", "refs/heads/so", "", head, False),
        ("workflow_dispatch", "", "refs/heads/so", "", head, False),
    )
    with tempfile.TemporaryDirectory(prefix="live-load-independent-identity-") as temp:
        root = Path(temp)
        stub = root / "git"
        stub.write_text("#!/bin/sh\n"
                        "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"HEAD\" ]; then printf '" + head + "\\n'; exit 0; fi\n"
                        "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then exit 0; fi\n"
                        "exit 1\n", encoding="utf-8")
        stub.chmod(0o755)
        for event, base, ref, pr_sha, sha, accepted in cases:
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_EVENT_NAME=event, GITHUB_BASE_REF=base, GITHUB_REF=ref,
                       PR_HEAD_SHA=pr_sha, GITHUB_SHA=sha)
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != accepted:
                raise AssertionError("live load independent CI event/base/ref/SHA drift: " + str((event, base, ref, result.returncode)))
    print("PASS: live load independent CI event/base/ref/SHA shell runtime (12 cases)")

def main() -> None:
    publisher = read(PUBLISHER)
    pr = read(PR)
    independent = read(INDEPENDENT)
    for marker in (PUBLISHER, PR, INDEPENDENT, SELF, CHECKOUT, SETUP,
                   "persist-credentials: false", "contents: read",
                   'test "$(git rev-parse HEAD)" = "$expected"',
                   'test -z "$(git status --porcelain)"'):
        if marker not in independent:
            raise AssertionError("independent live load source guard reachability missing: " + marker)
    reviewed_blob_negatives(publisher, pr, independent)
    independent_identity_runtime(independent)
    policy(publisher)
    live_load_trigger_matrix(publisher, pr, independent)
    live_load_trigger_negatives(publisher, pr, independent)
    live_load_yaml_shadow_negatives(publisher, pr, independent)
    mutations(publisher)
    writer_runtime(publisher)
    validator_shell_runtime(publisher)
    pr_policy(pr)
    pr_mutations(pr)
    pr_identity_runtime(pr)
    print("PASS: live load diagnostic exact-source read-only proof; production evidence generated: false")

if __name__ == "__main__":
    main()
