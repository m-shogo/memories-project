#!/usr/bin/env python3
"""Exact-source, read-only runtime negatives for SIGKILL failure diagnostics."""
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-deletion-sigkill-authority.yml"
INDEPENDENT = ".github/workflows/deletion-sigkill-diagnostic-source-negative.yml"
SCRIPT = "scripts/validate-memory-os-deletion-sigkill-diagnostic-source-negative.py"
REVIEWED = "0906a248b52297e836738d0c6ff00daaf49fed7d"
REVIEWED_INDEPENDENT = "18e047a7bbc8f5e7335eefa5f8931610f8522306"
TARGET = "docs/fixtures/memory-os-operability/deletion-sigkill-authority-diagnostic.last.json"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"


def source(name):
    p = ROOT / name
    if p.is_symlink() or not p.is_file() or p.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != name:
        raise SystemExit("SIGKILL source missing, symlinked or escaped: " + name)
    return p.read_text(encoding="utf-8")


def blob(value):
    raw = value.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


REQUIRED = (
    "  pull_request:\n    branches:\n      - so\n",
    "  push:\n    branches:\n      - so\n",
    "github.base_ref == 'so'",
    "github.ref == 'refs/heads/so'",
    "persist-credentials: false",
    "persist-credentials: true",
    '[[ "$PR_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]',
    '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'log="$(mktemp)"',
    "trap 'rm -f \"$log\"' EXIT",
    'python scripts/reconcile-memory-os-deletion-sigkill-authority.py >"$log" 2>&1 || code=$?',
    '"output": "SIGKILL reconcile failed; raw validator output withheld."',
    '"containsSecrets": False',
    '"productionDecision": "NO_GO"',
    "candidate.is_symlink()",
    "path.parent.resolve(strict=True).relative_to(repo)",
    "path.exists() and not path.is_file()",
    "os.fchmod(fd, mode)",
    "os.fsync(handle.fileno())",
    "os.replace(tmp, path)",
    "tmp.unlink()",
    "git fetch origin so",
)


SIGKILL_PUBLISHER_PR_PATHS = (
    ".github/workflows/reconcile-deletion-sigkill-authority.yml",
    "scripts/reconcile-memory-os-deletion-sigkill-authority.py",
    "scripts/validate-memory-os-deletion-sigkill-authority-reconcile-negative.py",
    "scripts/reconcile-memory-os-load-readiness-note.py",
    "scripts/reconcile-memory-os-load-missing-evidence.py",
    "scripts/validate-memory-os-load.py",
    "scripts/validate-memory-os-operability.py",
    "contracts/operations/deletion-worker-sigkill-recovery-contract.v1.json",
    "docs/fixtures/memory-os-operability/deletion-worker-sigkill-recovery-results.sample.v1.json",
    "contracts/operations/load-test-scenario-contract.v1.json",
    "contracts/operations/production-operability-status.json",
)

SIGKILL_PUBLISHER_PUSH_PATHS = (
    ".github/workflows/reconcile-deletion-sigkill-authority.yml",
    "scripts/reconcile-memory-os-deletion-sigkill-authority.py",
    "scripts/validate-memory-os-deletion-sigkill-authority-reconcile-negative.py",
    "scripts/reconcile-memory-os-load-readiness-note.py",
    "scripts/reconcile-memory-os-load-missing-evidence.py",
    "scripts/validate-memory-os-load.py",
    "scripts/validate-memory-os-operability.py",
    "contracts/operations/deletion-worker-sigkill-recovery-contract.v1.json",
    "docs/fixtures/memory-os-operability/deletion-worker-sigkill-recovery-results.sample.v1.json",
)

SIGKILL_INDEPENDENT_PR_PATHS = (
    ".github/workflows/reconcile-deletion-sigkill-authority.yml",
    ".github/workflows/deletion-sigkill-diagnostic-source-negative.yml",
    "scripts/validate-memory-os-deletion-sigkill-diagnostic-source-negative.py",
)

SIGKILL_INDEPENDENT_PUSH_PATHS = (
    ".github/workflows/reconcile-deletion-sigkill-authority.yml",
    ".github/workflows/deletion-sigkill-diagnostic-source-negative.yml",
    "scripts/validate-memory-os-deletion-sigkill-diagnostic-source-negative.py",
)

def sigkill_trigger_event(event: str, paths: tuple[str, ...]) -> str:
    return ("  " + event + ":\n    branches:\n      - so\n    paths:\n"
            + "".join('      - "' + path + '"\n' for path in paths))


def sigkill_trigger_header(content: str) -> str:
    # Exact, ordered event header: reject unknown, unquoted, duplicate and
    # unexpected event paths instead of depending only on a Git blob digest.
    if content.count("\non:\n") != 1 or content.count("\npermissions:\n") != 1:
        raise SystemExit("SIGKILL trigger section ambiguous")
    return content.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]


def sigkill_validate_trigger_matrix(
    publisher: str, independent: str,
    publisher_pr: tuple[str, ...] = SIGKILL_PUBLISHER_PR_PATHS,
    publisher_push: tuple[str, ...] = SIGKILL_PUBLISHER_PUSH_PATHS,
    independent_pr: tuple[str, ...] = SIGKILL_INDEPENDENT_PR_PATHS,
    independent_push: tuple[str, ...] = SIGKILL_INDEPENDENT_PUSH_PATHS,
) -> None:
    expected_publisher = (sigkill_trigger_event("pull_request", publisher_pr)
                          + sigkill_trigger_event("push", publisher_push)
                          + "  workflow_dispatch:\n")
    expected_independent = (sigkill_trigger_event("pull_request", independent_pr)
                            + sigkill_trigger_event("push", independent_push))
    for label, content, expected in (
        ("publisher", publisher, expected_publisher),
        ("independent", independent, expected_independent),
    ):
        if sigkill_trigger_header(content) != expected:
            raise SystemExit("SIGKILL " + label
                             + " exact event trigger inventory drift")


def replace_sigkill_trigger_header(content: str, original: str, replacement: str) -> str:
    old = "\non:\n" + original + "\npermissions:\n"
    if content.count(old) != 1 or original == replacement:
        raise SystemExit("SIGKILL trigger negative fixture unreachable")
    return content.replace(old, "\non:\n" + replacement + "\npermissions:\n", 1)


def sigkill_trigger_matrix_negatives(publisher: str, independent: str) -> None:
    def must_reject(p: str, i: str) -> None:
        try:
            sigkill_validate_trigger_matrix(p, i)
        except SystemExit:
            return
        raise SystemExit("SIGKILL accepted event trigger mutation")

    omissions = additions = 0
    cases = (
        ("publisher", "pull_request", SIGKILL_PUBLISHER_PR_PATHS),
        ("publisher", "push", SIGKILL_PUBLISHER_PUSH_PATHS),
        ("independent", "pull_request", SIGKILL_INDEPENDENT_PR_PATHS),
        ("independent", "push", SIGKILL_INDEPENDENT_PUSH_PATHS),
    )
    for label, event, paths in cases:
        original = publisher if label == "publisher" else independent
        header = sigkill_trigger_header(original)
        block = sigkill_trigger_event(event, paths)
        if header.count(block) != 1:
            raise SystemExit("SIGKILL trigger event fixture ambiguous")
        for index in range(len(paths)):
            shorter = paths[:index] + paths[index + 1:]
            mutated = replace_sigkill_trigger_header(
                original, header, header.replace(block, sigkill_trigger_event(event, shorter), 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            omissions += 1
        first = '      - "' + paths[0] + '"\n'
        for addition in (
            '      - "unreviewed/**"\n', '      - unreviewed/**\n',
            first, '      - ' + paths[0] + '\n',
        ):
            mutated_block = block.replace(first, first + addition, 1)
            mutated = replace_sigkill_trigger_header(
                original, header, header.replace(block, mutated_block, 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            additions += 1

    shortened = 0
    for field, paths in (
        ("publisher_pr", SIGKILL_PUBLISHER_PR_PATHS),
        ("publisher_push", SIGKILL_PUBLISHER_PUSH_PATHS),
        ("independent_pr", SIGKILL_INDEPENDENT_PR_PATHS),
        ("independent_push", SIGKILL_INDEPENDENT_PUSH_PATHS),
    ):
        try:
            sigkill_validate_trigger_matrix(publisher, independent, **{field: paths[:-1]})
        except SystemExit:
            shortened += 1
        else:
            raise SystemExit("SIGKILL accepted shortened trigger inventory")

    p_header, i_header = sigkill_trigger_header(publisher), sigkill_trigger_header(independent)
    topology = (
        (replace_sigkill_trigger_header(
            publisher, p_header, p_header.replace("  workflow_dispatch:\n", "", 1)), independent),
        (replace_sigkill_trigger_header(
            publisher, p_header, p_header.replace(
                "  workflow_dispatch:\n",
                "  schedule:\n    - cron: '0 0 * * *'\n  workflow_dispatch:\n", 1)), independent),
        (publisher, replace_sigkill_trigger_header(
            independent, i_header, i_header + "  workflow_dispatch:\n")),
    )
    for p, i in topology:
        must_reject(p, i)
    print("PASS: SIGKILL exact trigger matrix: "
          + str(omissions) + " omissions, " + str(additions)
          + " additions/duplicates, " + str(shortened)
          + " shortened inventories, " + str(len(topology)) + " event topology negatives")



def validate_yaml_root_permission(publisher: str, independent: str) -> None:
    """Pin effective root YAML mapping and root read-only permission leaves."""
    for label, value, roots in (
        ("publisher", publisher, ["name: Reconcile Deletion SIGKILL Authority",
                                  "on:", "permissions:", "concurrency:", "jobs:"]),
        ("independent", independent, ["name: Deletion SIGKILL Diagnostic Source Negative",
                                      "on:", "permissions:", "jobs:"]),
    ):
        actual = [line for line in value.splitlines()
                  if line.strip() and not line[0].isspace()
                  and not line.lstrip().startswith("#")]
        if actual != roots:
            raise AssertionError("sigkill-diagnostic " + label + " root YAML key shadow drift")
        if value.count("\npermissions:\n") != 1:
            raise AssertionError("sigkill-diagnostic " + label + " permission boundary drift")
        leaves = []
        for line in value.split("\npermissions:\n", 1)[1].splitlines():
            if line.strip() and not line[0].isspace():
                break
            if line.strip() and not line.lstrip().startswith("#"):
                leaves.append(line)
        if leaves != ["  contents: read"]:
            raise AssertionError("sigkill-diagnostic " + label + " permission leaf shadow drift")


def yaml_root_permission_negatives(publisher: str, independent: str) -> None:
    """Prove twelve exact-diagnostic YAML root and permission shadow rejections."""
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
            raise AssertionError("sigkill-diagnostic " + label + " permission fixture anchor drift")
        for mutation, leaf in (
            ("spaced contents", "  contents : write\n"),
            ("quoted contents", "  'contents': write\n"),
        ):
            cases.append((mutation, value.replace(marker, marker + leaf, 1),
                          "permission leaf shadow drift"))
        for mutation, changed, diagnostic in cases:
            if changed == value:
                raise AssertionError("sigkill-diagnostic unchanged YAML fixture: " + mutation)
            try:
                if is_publisher:
                    validate_yaml_root_permission(changed, other)
                else:
                    validate_yaml_root_permission(other, changed)
            except AssertionError as exc:
                expected = "sigkill-diagnostic " + label + " " + diagnostic
                if str(exc) != expected:
                    raise AssertionError("sigkill-diagnostic wrong YAML diagnostic: "
                                         + label + " " + mutation + ": " + str(exc)) from exc
            else:
                raise AssertionError("sigkill-diagnostic accepted YAML shadow: " + label + " " + mutation)
            count += 1
    if count != 12:
        raise AssertionError("sigkill-diagnostic YAML negative inventory drift")
    print("PASS: sigkill-diagnostic root/permission YAML authority (12 exact-diagnostic negatives)")


def policy(text):
    for item in REQUIRED:
        if item not in text:
            raise AssertionError("SIGKILL source policy missing: " + item[:70])
    if text.count(CHECKOUT) != 2 or text.count(SETUP) != 2:
        raise AssertionError("SIGKILL Actions source drift")
    if text.count("git fetch origin so") != 2:
        raise AssertionError("SIGKILL both success/failure CAS fetch boundaries required")
    if any(x in text for x in ("checkout@v4", "setup-python@v5", "tee /tmp/sigkill",
                               "sigkill-reconcile-output.txt", "[-16000:]")):
        raise AssertionError("SIGKILL raw output/floating Actions regression")


def mutations(text):
    for i, marker in enumerate(REQUIRED):
        mutated = text.replace(marker, "REMOVED_BY_NEGATIVE_TEST", 1)
        if mutated == text:
            raise AssertionError("SIGKILL negative unreachable: " + str(i))
        try:
            policy(mutated)
        except AssertionError:
            continue
        raise AssertionError("SIGKILL accepted source mutation: " + str(i))
    for marker in (CHECKOUT, SETUP):
        try:
            policy(text.replace(marker, "uses: actions/checkout@v4", 1))
        except AssertionError:
            continue
        raise AssertionError("SIGKILL accepted floating Action")
    print("PASS: SIGKILL diagnostic policy source negatives (24 cases)")


def step(text, name):
    marker = "      - name: " + name + "\n"
    if text.count(marker) != 1:
        raise AssertionError("SIGKILL step not unique: " + name)
    start = text.index("        run: |\n", text.index(marker)) + len("        run: |\n")
    end = text.find("\n      - name:", start)
    lines = text[start:end if end >= 0 else len(text)].splitlines()
    if not lines or any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("SIGKILL inline indentation drift: " + name)
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"


def writer_runtime(text):
    code = step(text, "Publish exact-source SIGKILL reconcile failure diagnostic")
    if code.count("python - <<'PY'\n") != 1 or code.count("\nPY\n") != 1:
        raise AssertionError("SIGKILL inline writer missing")
    code = code.split("python - <<'PY'\n", 1)[1].split("\nPY\n", 1)[0] + "\n"
    cases = ("existing", "new", "replace", "fsync", "symlink", "parent", "directory")
    for case in cases:
        with tempfile.TemporaryDirectory(prefix="sigkill-diagnostic-") as tmp:
            root = Path(tmp)
            parent = root / "docs/fixtures/memory-os-operability"
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
                func = "replace" if case == "replace" else "fsync"
                inject = "import os\n" + "def deny(*args): raise OSError('synthetic failure')\n" + "os." + func + " = deny\n"
            result = subprocess.run([sys.executable, "-c", inject + code], cwd=root,
                                    env=dict(os.environ, SOURCE_SHA="a" * 40),
                                    capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != (case in ("existing", "new")):
                raise AssertionError("SIGKILL inline writer acceptance drift: " + case)
            if canary.read_bytes() != b"SYNTHETIC_SECRET_CANARY":
                raise AssertionError("SIGKILL inline writer changed outside canary")
            if case in ("existing", "new"):
                value = json.loads(target.read_text(encoding="utf-8"))
                if value["output"] != "SIGKILL reconcile failed; raw validator output withheld." or value["containsSecrets"] or value["productionDecision"] != "NO_GO":
                    raise AssertionError("SIGKILL diagnostic redaction/authority drift")
                if stat.S_IMODE(target.stat().st_mode) != (0o640 if case == "existing" else 0o600):
                    raise AssertionError("SIGKILL diagnostic mode drift")
            if case in ("replace", "fsync"):
                if target.read_bytes() != b"before\n" or stat.S_IMODE(target.stat().st_mode) != 0o640:
                    raise AssertionError("SIGKILL atomic rollback drift")
            if list(parent.glob(".*.tmp")):
                raise AssertionError("SIGKILL temp residue")
    print("PASS: SIGKILL actual inline writer redaction/atomic/symlink runtime (7 cases)")


def log_runtime(text):
    shell = step(text, "Reconcile actual process-kill evidence")
    with tempfile.TemporaryDirectory(prefix="sigkill-log-") as tmp:
        root = Path(tmp)
        stub = root / "python"
        stub.write_text("#!/bin/sh\nprintf 'SYNTHETIC_SECRET_CANARY\\n'\nexit 23\n", encoding="utf-8")
        stub.chmod(0o755)
        env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"), TMPDIR=str(root))
        result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
        if result.returncode != 23 or "SYNTHETIC_SECRET_CANARY" in result.stdout + result.stderr:
            raise AssertionError("SIGKILL reconcile log exposed or exit code swallowed")
        if list(root.glob("tmp.*")):
            raise AssertionError("SIGKILL raw log temp residue")
    print("PASS: SIGKILL actual shell withholds synthetic secret and returns exit 23")



def identity_runtime(ci, title):
    command = step(ci, title)
    head = "a" * 40
    cases = (
        ("pull_request", "so", "", head, "", True),
        ("pull_request", "main", "", head, "", False),
        ("pull_request", "so", "", "A" * 40, "", False),
        ("pull_request", "so", "", "b" * 40, "", False),
        ("pull_request", "so", "", "", "", False),
        ("push", "", "refs/heads/so", "", head, True),
        ("push", "", "refs/heads/main", "", head, False),
        ("push", "", "refs/heads/so", "", "A" * 40, False),
        ("push", "", "refs/heads/so", "", "b" * 40, False),
        ("push", "", "refs/heads/so", "", "a" * 39, False),
        ("schedule", "", "refs/heads/so", "", head, False),
        ("workflow_dispatch", "", "refs/heads/so", "", head, False),
    )
    with tempfile.TemporaryDirectory(prefix="diagnostic-source-identity-") as temp:
        root = Path(temp)
        git = root / "git"
        git.write_text("#!/bin/sh\n"
                       "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"HEAD\" ]; then printf '" + head + "\\n'; exit 0; fi\n"
                       "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then exit 0; fi\n"
                       "exit 1\n", encoding="utf-8")
        git.chmod(0o755)
        for event, base, ref, pr_sha, sha, allowed in cases:
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_EVENT_NAME=event, GITHUB_BASE_REF=base, GITHUB_REF=ref,
                       PR_HEAD_SHA=pr_sha, GITHUB_SHA=sha)
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", command],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != allowed:
                raise AssertionError("diagnostic independent event/base/ref/SHA runtime drift: " + event)
    print("PASS: diagnostic independent exact-source event/base/ref/SHA shell runtime (12 cases)")




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
        prefix = "sigkill-authority " + label + " "
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
                raise SystemExit("sigkill-authority job fixture header drift: " + label + " " + name)

            def in_job(before: str, after: str) -> str:
                prefix, suffix = content.split(header, 1)
                if before not in suffix:
                    raise SystemExit("sigkill-authority job fixture anchor drift: " + name)
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
                    raise SystemExit("sigkill-authority unchanged job fixture: " + mutation)
                try:
                    if is_publisher:
                        validate_job_authority(changed, other)
                    else:
                        validate_job_authority(other, changed)
                except SystemExit as exc:
                    expected = "sigkill-authority " + label + " " + diagnostic
                    if str(exc) != expected:
                        raise SystemExit("sigkill-authority wrong job diagnostic: "
                                         + label + " " + name + " " + mutation + ": " + str(exc)) from exc
                else:
                    raise SystemExit("sigkill-authority accepted job shadow: "
                                     + label + " " + name + " " + mutation)
                count += 1
    if count != 36:
        raise SystemExit("sigkill-authority job negative inventory drift")
    print("PASS: sigkill-authority publisher/independent job authority (36 exact-diagnostic negatives)")


def main():
    publisher = source(PUBLISHER)
    if blob(publisher) != REVIEWED:
        raise SystemExit("SIGKILL publisher complete Git blob unreviewed")
    independent = source(INDEPENDENT)
    for marker in (PUBLISHER, INDEPENDENT, SCRIPT, CHECKOUT, SETUP,
                   "persist-credentials: false", "contents: read",
                   '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'):
        if marker not in independent:
            raise AssertionError("SIGKILL independent CI reachability/source drift: " + marker)
    if blob(independent) != REVIEWED_INDEPENDENT:
        raise SystemExit("SIGKILL independent workflow complete Git blob drift")
    identity_runtime(independent, "Require exact clean SIGKILL diagnostic source")
    policy(publisher)
    sigkill_validate_trigger_matrix(publisher, independent)
    sigkill_trigger_matrix_negatives(publisher, independent)
    validate_yaml_root_permission(publisher, independent)
    yaml_root_permission_negatives(publisher, independent)
    validate_job_authority(publisher, independent)
    prove_job_authority_negatives(publisher, independent)
    mutations(publisher)
    writer_runtime(publisher)
    log_runtime(publisher)
    print("PASS: SIGKILL exact-source read-only proof; production evidence generated: false; production decision changed: false")


if __name__ == "__main__":
    main()
