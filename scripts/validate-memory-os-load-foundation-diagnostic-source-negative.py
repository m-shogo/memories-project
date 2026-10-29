#!/usr/bin/env python3
"""Independent exact-source negative tests for load foundation diagnostic trust boundaries."""
from __future__ import annotations
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-load-foundation-authorities.yml"
INDEPENDENT = ".github/workflows/load-foundation-diagnostic-source-negative.yml"
SELF = "scripts/validate-memory-os-load-foundation-diagnostic-source-negative.py"
TARGET = "docs/fixtures/memory-os-operability/load-foundation-authority-diagnostic.last.json"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
REVIEWED_PUBLISHER = "f6f9b97957a09cd01174a0e020d2471c345ac721"
REVIEWED_INDEPENDENT = "367464494df85aebc4f5468eb7223569edc847c1"

def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def require_reviewed_source(content: str, expected: str, label: str) -> None:
    if blob(content) != expected:
        raise AssertionError("load foundation " + label + " complete Git blob drift")

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
        raise AssertionError("load foundation reviewed Git blob accepted synthetic source drift: " + label)
    print("PASS: load foundation publisher and independent CI complete Git blob source negatives (2 cases)")

def read(path: str) -> str:
    p = ROOT / path
    if p.is_symlink() or not p.is_file() or p.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise AssertionError("load foundation source missing/substituted: " + path)
    return p.read_text(encoding="utf-8")

def step(text: str, title: str) -> str:
    marker = "      - name: " + title + "\n"
    if text.count(marker) != 1:
        raise AssertionError("load foundation step missing/duplicated: " + title)
    start = text.index("        run: |\n", text.index(marker)) + len("        run: |\n")
    end = text.find("\n      - name:", start)
    lines = text[start:end if end >= 0 else len(text)].splitlines()
    if any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("load foundation step indentation drift")
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"

REQUIRED = (
    "  pull_request:\n    branches:\n      - so\n",
    "if: github.event_name == 'pull_request' && github.base_ref == 'so'",
    "github.ref == 'refs/heads/so'",
    "persist-credentials: false",
    "persist-credentials: true",
    '[[ "$PR_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]',
    '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"',
    'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
    'trap \'rm -f "$log"\' EXIT',
    'echo "Bounded load foundation validation completed; raw validator output withheld."',
    'echo "FOUNDATION_FAILURE_STAGE=$stage" >> "$GITHUB_ENV"',
    "'failureStage': stage",
    "if stage not in allowed_stages:",
    "'output': 'Bounded load foundation validation failed; raw validator output withheld.'",
    "'containsSecrets': False",
    "'productionDecision': 'NO_GO'",
    "candidate.is_symlink()",
    "path.parent.resolve(strict=True).relative_to(repo)",
    "path.exists() and not path.is_file()",
    "os.fchmod(fd, mode)",
    "os.fsync(handle.fileno())",
    "os.replace(tmp, path)",
    "tmp.unlink()",
)
LOAD_FOUNDATION_PUBLISHER_PR_PATHS = (
    ".github/workflows/reconcile-load-foundation-authorities.yml",
    "docs/fixtures/memory-os-operability/capacity-ramp-results.sample.v1.json",
    "docs/fixtures/memory-os-operability/short-stability-sample-results.sample.v1.json",
    "docs/fixtures/memory-os-operability/deletion-under-load-results.sample.v1.json",
    "contracts/operations/capacity-ramp-contract.v1.json",
    "contracts/operations/short-stability-sample-contract.v1.json",
    "contracts/operations/deletion-under-load-contract.v1.json",
    "contracts/operations/load-test-scenario-contract.v1.json",
    "contracts/operations/production-operability-status.json",
    "scripts/validate-memory-os-capacity-ramp.py",
    "scripts/validate-memory-os-capacity-ramp-authority-negative.py",
    "scripts/reconcile-memory-os-capacity-ramp-status.py",
    "scripts/validate-memory-os-short-stability-sample.py",
    "scripts/validate-memory-os-short-stability-authority-negative.py",
    "scripts/validate-memory-os-short-stability-reconcile-negative.py",
    "scripts/reconcile-memory-os-short-stability-status.py",
    "scripts/reconcile-memory-os-sustained-local-soak-status.py",
    "scripts/validate-memory-os-deletion-under-load.py",
    "scripts/validate-memory-os-deletion-under-load-authority-negative.py",
    "scripts/reconcile-memory-os-deletion-under-load-status.py",
    "scripts/validate-memory-os-load.py",
    "scripts/validate-memory-os-operability.py",
)

LOAD_FOUNDATION_PUBLISHER_PUSH_PATHS = (
    ".github/workflows/reconcile-load-foundation-authorities.yml",
    "docs/fixtures/memory-os-operability/capacity-ramp-results.sample.v1.json",
    "docs/fixtures/memory-os-operability/short-stability-sample-results.sample.v1.json",
    "docs/fixtures/memory-os-operability/deletion-under-load-results.sample.v1.json",
    "contracts/operations/capacity-ramp-contract.v1.json",
    "contracts/operations/short-stability-sample-contract.v1.json",
    "contracts/operations/deletion-under-load-contract.v1.json",
    "contracts/operations/load-test-scenario-contract.v1.json",
    "contracts/operations/production-operability-status.json",
    "scripts/validate-memory-os-capacity-ramp.py",
    "scripts/validate-memory-os-capacity-ramp-authority-negative.py",
    "scripts/reconcile-memory-os-capacity-ramp-status.py",
    "scripts/validate-memory-os-short-stability-sample.py",
    "scripts/validate-memory-os-short-stability-authority-negative.py",
    "scripts/validate-memory-os-short-stability-reconcile-negative.py",
    "scripts/reconcile-memory-os-short-stability-status.py",
    "scripts/reconcile-memory-os-sustained-local-soak-status.py",
    "scripts/validate-memory-os-deletion-under-load.py",
    "scripts/validate-memory-os-deletion-under-load-authority-negative.py",
    "scripts/reconcile-memory-os-deletion-under-load-status.py",
    "scripts/validate-memory-os-load.py",
    "scripts/validate-memory-os-operability.py",
)

LOAD_FOUNDATION_INDEPENDENT_PR_PATHS = (
    ".github/workflows/reconcile-load-foundation-authorities.yml",
    ".github/workflows/load-foundation-diagnostic-source-negative.yml",
    "scripts/validate-memory-os-load-foundation-diagnostic-source-negative.py",
)

LOAD_FOUNDATION_INDEPENDENT_PUSH_PATHS = (
    ".github/workflows/reconcile-load-foundation-authorities.yml",
    ".github/workflows/load-foundation-diagnostic-source-negative.yml",
    "scripts/validate-memory-os-load-foundation-diagnostic-source-negative.py",
)

def load_foundation_trigger_event(event: str, paths: tuple[str, ...]) -> str:
    return ("  " + event + ":\n    branches:\n      - so\n    paths:\n"
            + "".join('      - "' + path + '"\n' for path in paths))


def load_foundation_trigger_header(content: str) -> str:
    # Exact, ordered event header: reject unknown, unquoted, duplicate and
    # unexpected event paths instead of depending only on a Git blob digest.
    if content.count("\non:\n") != 1 or content.count("\npermissions:\n") != 1:
        raise SystemExit("load-foundation trigger section ambiguous")
    return content.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]


def load_foundation_validate_trigger_matrix(
    publisher: str, independent: str,
    publisher_pr: tuple[str, ...] = LOAD_FOUNDATION_PUBLISHER_PR_PATHS,
    publisher_push: tuple[str, ...] = LOAD_FOUNDATION_PUBLISHER_PUSH_PATHS,
    independent_pr: tuple[str, ...] = LOAD_FOUNDATION_INDEPENDENT_PR_PATHS,
    independent_push: tuple[str, ...] = LOAD_FOUNDATION_INDEPENDENT_PUSH_PATHS,
) -> None:
    expected_publisher = (load_foundation_trigger_event("pull_request", publisher_pr)
                          + load_foundation_trigger_event("push", publisher_push)
                          + '  schedule:\n    - cron: "7 19 * * *"\n'
                          + "  workflow_dispatch:\n")
    expected_independent = (load_foundation_trigger_event("pull_request", independent_pr)
                            + load_foundation_trigger_event("push", independent_push))
    for label, content, expected in (
        ("publisher", publisher, expected_publisher),
        ("independent", independent, expected_independent),
    ):
        if load_foundation_trigger_header(content) != expected:
            raise SystemExit("load-foundation " + label
                             + " exact event trigger inventory drift")


def replace_load_foundation_trigger_header(content: str, original: str, replacement: str) -> str:
    old = "\non:\n" + original + "\npermissions:\n"
    if content.count(old) != 1 or original == replacement:
        raise SystemExit("load-foundation trigger negative fixture unreachable")
    return content.replace(old, "\non:\n" + replacement + "\npermissions:\n", 1)


def load_foundation_trigger_matrix_negatives(publisher: str, independent: str) -> None:
    def must_reject(p: str, i: str) -> None:
        try:
            load_foundation_validate_trigger_matrix(p, i)
        except SystemExit:
            return
        raise SystemExit("load-foundation accepted event trigger mutation")

    omissions = additions = 0
    cases = (
        ("publisher", "pull_request", LOAD_FOUNDATION_PUBLISHER_PR_PATHS),
        ("publisher", "push", LOAD_FOUNDATION_PUBLISHER_PUSH_PATHS),
        ("independent", "pull_request", LOAD_FOUNDATION_INDEPENDENT_PR_PATHS),
        ("independent", "push", LOAD_FOUNDATION_INDEPENDENT_PUSH_PATHS),
    )
    for label, event, paths in cases:
        original = publisher if label == "publisher" else independent
        header = load_foundation_trigger_header(original)
        block = load_foundation_trigger_event(event, paths)
        if header.count(block) != 1:
            raise SystemExit("load-foundation trigger event fixture ambiguous")
        for index in range(len(paths)):
            shorter = paths[:index] + paths[index + 1:]
            mutated = replace_load_foundation_trigger_header(
                original, header, header.replace(block, load_foundation_trigger_event(event, shorter), 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            omissions += 1
        first = '      - "' + paths[0] + '"\n'
        for addition in (
            '      - "unreviewed/**"\n', '      - unreviewed/**\n',
            first, '      - ' + paths[0] + '\n',
        ):
            mutated_block = block.replace(first, first + addition, 1)
            mutated = replace_load_foundation_trigger_header(
                original, header, header.replace(block, mutated_block, 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            additions += 1

    shortened = 0
    for field, paths in (
        ("publisher_pr", LOAD_FOUNDATION_PUBLISHER_PR_PATHS),
        ("publisher_push", LOAD_FOUNDATION_PUBLISHER_PUSH_PATHS),
        ("independent_pr", LOAD_FOUNDATION_INDEPENDENT_PR_PATHS),
        ("independent_push", LOAD_FOUNDATION_INDEPENDENT_PUSH_PATHS),
    ):
        try:
            load_foundation_validate_trigger_matrix(publisher, independent, **{field: paths[:-1]})
        except SystemExit:
            shortened += 1
        else:
            raise SystemExit("load-foundation accepted shortened trigger inventory")

    p_header, i_header = load_foundation_trigger_header(publisher), load_foundation_trigger_header(independent)
    topology = (
        (replace_load_foundation_trigger_header(
            publisher, p_header, p_header.replace("7 19 * * *", "0 0 * * *", 1)), independent),
        (replace_load_foundation_trigger_header(
            publisher, p_header, p_header.replace("  workflow_dispatch:\n", "", 1)), independent),
        (replace_load_foundation_trigger_header(
            publisher, p_header, p_header.replace(
                "  workflow_dispatch:\n",
                "  schedule:\n    - cron: '0 0 * * *'\n  workflow_dispatch:\n", 1)), independent),
        (publisher, replace_load_foundation_trigger_header(
            independent, i_header, i_header + "  workflow_dispatch:\n")),
    )
    for p, i in topology:
        must_reject(p, i)
    print("PASS: load-foundation exact trigger matrix: "
          + str(omissions) + " omissions, " + str(additions)
          + " additions/duplicates, " + str(shortened)
          + " shortened inventories, " + str(len(topology)) + " event topology negatives")



def validate_yaml_root_permission(publisher: str, independent: str) -> None:
    """Pin reviewed YAML root mapping and read-only permission leaves."""
    for label, value, roots in (
        ("publisher", publisher, ["name: Reconcile Load Foundation Authorities",
                                  "on:", "permissions:", "concurrency:", "jobs:"]),
        ("independent", independent, ["name: Load Foundation Diagnostic Source Negative",
                                      "on:", "permissions:", "jobs:"]),
    ):
        actual = [line for line in value.splitlines()
                  if line.strip() and not line[0].isspace()
                  and not line.lstrip().startswith("#")]
        if actual != roots:
            raise AssertionError("load-foundation " + label + " root YAML key shadow drift")
        if value.count("\npermissions:\n") != 1:
            raise AssertionError("load-foundation " + label + " permission boundary drift")
        leaves = []
        for line in value.split("\npermissions:\n", 1)[1].splitlines():
            if line.strip() and not line[0].isspace():
                break
            if line.strip() and not line.lstrip().startswith("#"):
                leaves.append(line)
        if leaves != ["  contents: read"]:
            raise AssertionError("load-foundation " + label + " permission leaf shadow drift")


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
            raise AssertionError("load-foundation " + label + " permission fixture anchor drift")
        for mutation, leaf in (
            ("spaced contents", "  contents : write\n"),
            ("quoted contents", "  'contents': write\n"),
        ):
            cases.append((mutation, value.replace(marker, marker + leaf, 1),
                          "permission leaf shadow drift"))
        for mutation, changed, diagnostic in cases:
            if changed == value:
                raise AssertionError("load-foundation unchanged YAML fixture: " + mutation)
            try:
                if is_publisher:
                    validate_yaml_root_permission(changed, other)
                else:
                    validate_yaml_root_permission(other, changed)
            except AssertionError as exc:
                expected = "load-foundation " + label + " " + diagnostic
                if str(exc) != expected:
                    raise AssertionError("load-foundation wrong YAML diagnostic: "
                                         + label + " " + mutation + ": " + str(exc)) from exc
            else:
                raise AssertionError("load-foundation accepted YAML shadow: " + label + " " + mutation)
            count += 1
    if count != 12:
        raise AssertionError("load-foundation YAML negative inventory drift")
    print("PASS: load-foundation root/permission YAML authority (12 exact-diagnostic negatives)")



def load_foundation_concurrency_authority(publisher: str) -> None:
    """Pin reviewed per-PR cancellable publisher serialization."""
    marker = "\nconcurrency:\n"
    if publisher.count(marker) != 1 or publisher.count("\njobs:\n") != 1:
        raise SystemExit("load-foundation publisher concurrency authority drift")
    observed = publisher.split(marker, 1)[1].split("\njobs:\n", 1)[0]
    expected = ("  group: reconcile-load-foundation-authorities-" + chr(36)
                + "{{ github.event.pull_request.number || 'so' }}\n"
                + "  cancel-in-progress: true\n")
    if observed != expected:
        raise SystemExit("load-foundation publisher concurrency authority drift")


def load_foundation_concurrency_negatives(publisher: str) -> None:
    """Prove twelve exact-diagnostic YAML concurrency overrides."""
    marker = "\nconcurrency:\n"
    original = ("  group: reconcile-load-foundation-authorities-" + chr(36)
                + "{{ github.event.pull_request.number || 'so' }}\n"
                + "  cancel-in-progress: true\n")
    anchor = marker + original + "\njobs:\n"
    if publisher.count(anchor) != 1:
        raise SystemExit("load-foundation concurrency fixture anchor drift")
    group = original.splitlines(keepends=True)[0]
    cancel = "  cancel-in-progress: true\n"
    cases = (
        ("changed group", original.replace(group, "  group: unreviewed\n", 1)),
        ("missing group", original.replace(group, "", 1)),
        ("duplicate group", original.replace(group, group + "  group: unreviewed\n", 1)),
        ("quoted group", original.replace(group, group + "  'group': unreviewed\n", 1)),
        ("spaced group", original.replace(group, group + "  group : unreviewed\n", 1)),
        ("extra group leaf", original.replace(group, group + "  unreviewed: true\n", 1)),
        ("disabled cancellation", original.replace(cancel, "  cancel-in-progress: false\n", 1)),
        ("missing cancellation", original.replace(cancel, "", 1)),
        ("duplicate cancellation", original.replace(cancel, cancel + "  cancel-in-progress: false\n", 1)),
        ("quoted cancellation", original.replace(cancel, cancel + "  'cancel-in-progress': false\n", 1)),
        ("spaced cancellation", original.replace(cancel, cancel + "  cancel-in-progress : false\n", 1)),
        ("extra cancellation leaf", original.replace(cancel, cancel + "  unreviewed: true\n", 1)),
    )
    if len(cases) != 12:
        raise SystemExit("load-foundation concurrency negative inventory drift")
    load_foundation_concurrency_authority(publisher)
    for name, replacement in cases:
        altered = publisher.replace(anchor, marker + replacement + "\njobs:\n", 1)
        if altered == publisher:
            raise SystemExit("load-foundation unchanged concurrency fixture: " + name)
        try:
            load_foundation_concurrency_authority(altered)
        except SystemExit as exc:
            if str(exc) != "load-foundation publisher concurrency authority drift":
                raise SystemExit("load-foundation wrong concurrency diagnostic: "
                                 + name + ": " + str(exc)) from exc
        else:
            raise SystemExit("load-foundation accepted concurrency mutation: " + name)
    print("PASS: load-foundation publisher concurrency (12 exact-diagnostic negatives)")

def policy(source: str) -> None:
    for marker in REQUIRED:
        if marker not in source:
            raise AssertionError("load foundation policy missing: " + marker[:70])
    if source.count(CHECKOUT) != 2 or source.count(SETUP) != 2:
        raise AssertionError("load foundation immutable Actions count drift")
    if source.count("trap 'rm -f \"$log\"' EXIT") != 2:
        raise AssertionError("load foundation two log cleanup boundaries drift")
    for forbidden in ("actions/checkout@v4", "actions/setup-python@v5",
                      'cat "$log"', 'text[-12000:]', 'Path("/tmp/memory-os-load-foundation-authorities.log")'):
        if forbidden in source:
            raise AssertionError("load foundation raw log/floating Action regression")

def mutations(source: str) -> None:
    for index, marker in enumerate(REQUIRED):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE_TEST", 1)
        if changed == source:
            raise AssertionError("load foundation mutation unreachable: " + str(index))
        try:
            policy(changed)
        except AssertionError:
            continue
        raise AssertionError("load foundation mutation accepted: " + str(index))
    print(f"PASS: load foundation source negatives ({len(REQUIRED)} cases)")

def writer_runtime(source: str) -> None:
    shell = step(source, "Record privacy-safe diagnostic")
    if shell.count("python - <<'PY'\n") != 1 or shell.count("\nPY\n") != 1:
        raise AssertionError("load foundation diagnostic heredoc missing")
    code = shell.split("python - <<'PY'\n", 1)[1].split("\nPY\n", 1)[0] + "\n"
    for case in ("existing", "new", "bad_stage", "replace", "fsync", "symlink", "parent", "directory", "bad_sha", "bad_exit"):
        with tempfile.TemporaryDirectory(prefix="load-foundation-diagnostic-") as temp:
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
                op = "replace" if case == "replace" else "fsync"
                inject = "import os\ndef deny(*args): raise OSError('synthetic failure')\nos." + op + " = deny\n"
            env = dict(os.environ, SOURCE_SHA="a" * (39 if case == "bad_sha" else 40),
                       FOUNDATION_EXIT_CODE="999" if case == "bad_exit" else "17",
                       FOUNDATION_FAILURE_STAGE="SYNTHETIC_SECRET_CANARY" if case == "bad_stage" else "compile")
            result = subprocess.run([sys.executable, "-c", inject + code], cwd=root,
                                    env=env, capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != (case in ("existing", "new", "bad_stage")):
                raise AssertionError("load foundation diagnostic writer acceptance drift: " + case + " " + result.stderr[-100:])
            if canary.read_bytes() != b"SYNTHETIC_SECRET_CANARY":
                raise AssertionError("load foundation diagnostic escaped root")
            if case in ("existing", "new", "bad_stage"):
                value = json.loads(target.read_text(encoding="utf-8"))
                if value["output"] != "Bounded load foundation validation failed; raw validator output withheld." or value["containsSecrets"] or value["productionEvidence"] or value["productionReady"] or value["productionDecision"] != "NO_GO" or value["exitCode"] != 17 or value["failureStage"] != ("unknown" if case == "bad_stage" else "compile") or "SYNTHETIC_SECRET_CANARY" in target.read_text(encoding="utf-8"):
                    raise AssertionError("load foundation diagnostic privacy/authority drift")
                if stat.S_IMODE(target.stat().st_mode) != (0o640 if case == "existing" else 0o600):
                    raise AssertionError("load foundation diagnostic mode drift")
            if case in ("replace", "fsync"):
                if target.read_bytes() != b"before\n" or stat.S_IMODE(target.stat().st_mode) != 0o640:
                    raise AssertionError("load foundation diagnostic atomic rollback drift")
            if list(parent.glob(".*.tmp")):
                raise AssertionError("load foundation diagnostic temp residue")
    print("PASS: actual load foundation diagnostic atomic/symlink/privacy/stage runtime (10 cases)")

def capture_shell_runtime(source: str) -> None:
    for title, output_name, expected_line in (
        ("Reconcile available bounded results read-only", "GITHUB_OUTPUT", "exit_code=17\n"),
        ("Reconcile available bounded results with stage capture", "GITHUB_ENV", "FOUNDATION_EXIT_CODE=17\nFOUNDATION_FAILURE_STAGE=compile\n"),
    ):
        shell = step(source, title)
        with tempfile.TemporaryDirectory(prefix="load-foundation-capture-") as temp:
            root = Path(temp)
            stub = root / "python"
            stub.write_text("#!/bin/sh\necho SYNTHETIC_SECRET_CANARY\nexit 17\n", encoding="utf-8")
            stub.chmod(0o755)
            output = root / "result"
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       TMPDIR=str(root), GITHUB_OUTPUT=str(output), GITHUB_ENV=str(output))
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
            if result.returncode != 0 or output.read_text(encoding="utf-8") != expected_line:
                raise AssertionError("load foundation validator capture swallowed failure: " + title + " " + result.stderr[-150:])
            if "SYNTHETIC_SECRET_CANARY" in result.stdout + result.stderr:
                raise AssertionError("load foundation validator raw log leaked: " + title)
            if list(root.glob("tmp.*")):
                raise AssertionError("load foundation validator raw log temp residue: " + title)
    print("PASS: load foundation PR/writer actual validator failure capture and raw-log suppression (2 cases)")

def pr_identity_runtime(source: str) -> None:
    shell = step(source, "Confirm exact clean PR authority source")
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
                raise AssertionError("load foundation PR identity shell drift: " + str((event, base, sha, result.returncode)))
    print("PASS: load foundation PR event/base/head SHA shell runtime (6 cases)")

def independent_identity_runtime(source: str) -> None:
    shell = step(source, "Require exact clean load foundation diagnostic source")
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
                raise AssertionError("load foundation independent CI event/base/ref/SHA drift: " + str((event, base, ref, result.returncode)))
    print("PASS: load foundation independent CI event/base/ref/SHA shell runtime (12 cases)")

def writer_identity_runtime(authority: str) -> None:
    code = step(authority, "Confirm exact clean authority source")
    if 'echo "SOURCE_SHA=' not in code:
        raise SystemExit("load foundation writer source capture drift")
    code = code.split('echo "SOURCE_SHA=', 1)[0]
    head = "a" * 40
    cases = (
        ("push", "refs/heads/so", head, True),
        ("workflow_dispatch", "refs/heads/so", head, True),
        ("schedule", "refs/heads/so", head, True),
        ("pull_request", "refs/heads/so", head, False),
        ("push", "refs/heads/main", head, False),
        ("push", "refs/tags/v1", head, False),
        ("push", "refs/heads/so", "A" * 40, False),
        ("push", "refs/heads/so", "a" * 39, False),
        ("push", "refs/heads/so", "b" * 40, False),
        ("schedule", "", head, False),
    )
    with tempfile.TemporaryDirectory(prefix="load-foundation-writer-source-") as tmp:
        root = Path(tmp)
        git = root / "git"
        git.write_text(
            '''#!/bin/sh
if [ "$1" = "status" ]; then exit 0; fi
if [ "$1" = "rev-parse" ]; then printf '%s' "$STUB_HEAD"; exit 0; fi
exit 1
''', encoding="utf-8"
        )
        git.chmod(0o755)
        for event, ref, sha, accepted in cases:
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_EVENT_NAME=event, GITHUB_REF=ref, GITHUB_SHA=sha, STUB_HEAD=head)
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", code],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != accepted:
                raise SystemExit("load foundation writer actual writer source shell drift: " + event + "/" + ref)
    print("PASS: load foundation writer actual writer event/ref/SHA shell (10 cases)")


def main() -> None:
    publisher = read(PUBLISHER)
    independent = read(INDEPENDENT)
    for marker in (PUBLISHER, INDEPENDENT, SELF, CHECKOUT, SETUP,
                   "persist-credentials: false", "contents: read",
                   'test "$(git rev-parse HEAD)" = "$expected"',
                   'test -z "$(git status --porcelain)"'):
        if marker not in independent:
            raise AssertionError("load foundation independent CI reachability drift: " + marker)
    reviewed_blob_negatives(publisher, independent)
    pr_identity_runtime(publisher)
    writer_identity_runtime(publisher)
    independent_identity_runtime(independent)
    policy(publisher)
    load_foundation_validate_trigger_matrix(publisher, independent)
    load_foundation_trigger_matrix_negatives(publisher, independent)
    validate_yaml_root_permission(publisher, independent)
    yaml_root_permission_negatives(publisher, independent)
    load_foundation_concurrency_authority(publisher)
    load_foundation_concurrency_negatives(publisher)
    mutations(publisher)
    writer_runtime(publisher)
    capture_shell_runtime(publisher)
    print("PASS: load foundation exact-source read-only proof; production evidence generated: false")

if __name__ == "__main__":
    main()
