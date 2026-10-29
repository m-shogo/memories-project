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
PUBLISHER = ".github/workflows/deletion-lease-recovery.yml"
INDEPENDENT = ".github/workflows/deletion-lease-recovery-diagnostic-source-negative.yml"
SCRIPT = "scripts/validate-memory-os-deletion-lease-recovery-diagnostic-source-negative.py"
RECONCILER = "scripts/reconcile-memory-os-deletion-lease-recovery.py"
RECONCILE_NEGATIVE = "scripts/validate-memory-os-deletion-lease-recovery-reconcile-negative.py"
RESULT_VALIDATOR = "scripts/validate-memory-os-deletion-lease-recovery.py"
RESULT_NEGATIVE = "scripts/validate-memory-os-deletion-lease-recovery-result-negative.py"
REVIEWED_RECONCILER = "a6c6e35e113db4909c1dfbd1b931eb087f8ad010"
REVIEWED_RECONCILE_NEGATIVE = "8800f7ddec39606f9529c109bb9c62a2210f53c1"
REVIEWED = "12129252904c15d5a9c335fd0b529319d1f0b71a"
REVIEWED_RESULT_VALIDATOR = "a903aae123256e0c4a55f8b7b59a5f968141aa12"
REVIEWED_RESULT_NEGATIVE = "a4838d5b0c9388c2b1558b2e27e1192b23939ff8"
REVIEWED_INDEPENDENT = "f76d9a92924355358d005d5b49c73d30c4be4b3b"

PUBLISHER_PUSH_TRIGGER_PATHS = (
    ".github/workflows/deletion-lease-recovery.yml",
    "contracts/operations/deletion-lease-recovery-contract.v1.json",
    "scripts/validate-memory-os-deletion-lease-recovery.py",
    "scripts/reconcile-memory-os-deletion-lease-recovery.py",
    "scripts/validate-memory-os-deletion-lease-recovery-reconcile-negative.py",
    "services/import-api/internal/httpserver/deletion_lease_recovery_test.go",
    "services/import-api/internal/httpserver/deletion_prefence_upload_completion_test.go",
    "services/import-api/internal/httpserver/server_live_test.go",
    "services/import-api/internal/httpserver/server.go",
    "services/import-api/internal/accountdelete/**",
    "services/import-api/internal/pgrepo/**",
    "services/import-api/internal/objectstore/**",
    "services/import-api/internal/authstore/**",
    "services/import-api/internal/dbscope/**",
    "services/import-api/internal/pgscope/**",
    "services/import-api/internal/upload/**",
    "infra/postgresql/security/**",
    "services/import-api/go.mod",
    "services/import-api/go.sum",
)
INDEPENDENT_PR_TRIGGER_PATHS = (
    ".github/workflows/deletion-lease-recovery.yml",
    ".github/workflows/deletion-lease-recovery-diagnostic-source-negative.yml",
    "scripts/validate-memory-os-deletion-lease-recovery-diagnostic-source-negative.py",
    "scripts/reconcile-memory-os-deletion-lease-recovery.py",
    "scripts/validate-memory-os-deletion-lease-recovery-reconcile-negative.py",
    "scripts/validate-memory-os-deletion-lease-recovery.py",
    "scripts/validate-memory-os-deletion-lease-recovery-result-negative.py",
)
INDEPENDENT_PUSH_TRIGGER_PATHS = (
    ".github/workflows/deletion-lease-recovery.yml",
    ".github/workflows/deletion-lease-recovery-diagnostic-source-negative.yml",
    "scripts/validate-memory-os-deletion-lease-recovery-diagnostic-source-negative.py",
    "scripts/reconcile-memory-os-deletion-lease-recovery.py",
    "scripts/validate-memory-os-deletion-lease-recovery-reconcile-negative.py",
    "scripts/validate-memory-os-deletion-lease-recovery.py",
    "scripts/validate-memory-os-deletion-lease-recovery-result-negative.py",
)
TARGET = "docs/fixtures/memory-os-operability/deletion-lease-recovery-diagnostic.last.json"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
SETUP_GO = "uses: actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5"



def validate_trigger_reachability(
    value: str, *, publisher: bool,
    pr_paths: tuple[str, ...] | None = None,
    push_paths: tuple[str, ...] | None = None,
) -> None:
    """Keep push-only publisher and PR/push independent source CI distinct."""
    expected_push = PUBLISHER_PUSH_TRIGGER_PATHS if publisher else INDEPENDENT_PUSH_TRIGGER_PATHS
    expected_pr = () if publisher else INDEPENDENT_PR_TRIGGER_PATHS
    approved_push = expected_push if push_paths is None else push_paths
    approved_pr = expected_pr if pr_paths is None else pr_paths
    for label, actual, expected in (("PR", approved_pr, expected_pr), ("push", approved_push, expected_push)):
        if len(actual) != len(expected) or len(set(actual)) != len(expected):
            raise AssertionError("lease diagnostic CI " + label + " trigger inventory shortened or duplicated")
    pr = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    end = "  workflow_dispatch:\n" if publisher else "\npermissions:\n"
    if value.count(push) != 1 or value.count(end) != 1:
        raise AssertionError("lease diagnostic CI trigger marker drift")
    if publisher:
        if "  pull_request:" in value or not (value.index(push) < value.index(end)):
            raise AssertionError("lease diagnostic publisher must remain push-only")
        events = (("push", push, end, approved_push),)
    else:
        if value.count(pr) != 1 or not (value.index(pr) < value.index(push) < value.index(end)):
            raise AssertionError("lease diagnostic independent CI event marker/order drift")
        events = (("PR", pr, push, approved_pr), ("push", push, end, approved_push))
    for label, start, stop, approved_paths in events:
        block = value.split(start, 1)[1].split(stop, 1)[0]
        actual = tuple(line for line in block.splitlines()
                       if line.strip() and not line.lstrip().startswith("#"))
        approved = tuple('      - "' + path + '"' for path in approved_paths)
        if actual != approved:
            raise AssertionError("lease diagnostic CI " + label + " exact trigger path drift")


def prove_trigger_reachability_negatives(publisher: str, independent: str) -> None:
    """Prove all single-event omissions, additions and shortened inventories."""
    pr = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    for label, value, is_publisher, events in (
        ("publisher", publisher, True, (("push", push, "  workflow_dispatch:\n", PUBLISHER_PUSH_TRIGGER_PATHS),)),
        ("independent", independent, False, (
            ("PR", pr, push, INDEPENDENT_PR_TRIGGER_PATHS),
            ("push", push, "\npermissions:\n", INDEPENDENT_PUSH_TRIGGER_PATHS),
        )),
    ):
        for event, start, stop, paths in events:
            start_index = value.index(start) + len(start)
            end_index = value.index(stop, start_index)
            block = value[start_index:end_index]
            for path in paths:
                token = '      - "' + path + '"\n'
                if block.count(token) != 1:
                    raise AssertionError("lease diagnostic CI mutation anchor drift: " + path)
                mutated = value[:start_index] + block.replace(token, "", 1) + value[end_index:]
                try:
                    validate_trigger_reachability(mutated, publisher=is_publisher)
                except AssertionError:
                    pass
                else:
                    raise AssertionError("lease diagnostic CI accepted missing " + label + " " + event + " trigger: " + path)
            for name, injection in (
                ("quoted extra", '      - "unreviewed/**"\n'),
                ("quoted duplicate", '      - "' + paths[0] + '"\n'),
                ("unquoted extra", "      - unreviewed/**\n"),
                ("unquoted duplicate", "      - " + paths[0] + "\n"),
            ):
                mutated = value[:start_index] + injection + value[start_index:]
                try:
                    validate_trigger_reachability(mutated, publisher=is_publisher)
                except AssertionError:
                    pass
                else:
                    raise AssertionError("lease diagnostic CI accepted " + label + " " + event + " " + name)
            try:
                validate_trigger_reachability(
                    value, publisher=is_publisher,
                    pr_paths=paths[:-1] if event == "PR" else None,
                    push_paths=paths[:-1] if event == "push" else None,
                )
            except AssertionError:
                pass
            else:
                raise AssertionError("lease diagnostic CI accepted shortened " + label + " " + event + " inventory")
    print("PASS: lease diagnostic CI event triggers (33 removals; 12 additions; 3 shortened inventory negatives)")


def source(name):
    p = ROOT / name
    if p.is_symlink() or not p.is_file() or p.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != name:
        raise SystemExit("SIGKILL source missing, symlinked or escaped: " + name)
    return p.read_text(encoding="utf-8")


def blob(value):
    raw = value.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


REQUIRED = (
    "  push:\n    branches:\n      - so\n",
    "  workflow_dispatch:",
    '[[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]',
    'test "${GITHUB_REF:-}" = "refs/heads/so"',
    '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'trap \'rm -f "$log"\' EXIT',
    'echo "Local MinIO health failed; raw container logs withheld."',
    '"output": "Lease recovery proof failed; raw validator output withheld."',
    '"containsSecrets": False',
    '"productionEvidence": False',
    '"productionEquivalentDependencies": False',
    '"sourceCommitSha": os.environ["SOURCE_SHA"]',
    '"actualProcessKillCovered": False',
    '"actualHostFailureCovered": False',
    "candidate.is_symlink()",
    "path.parent.resolve(strict=True).relative_to(repo)",
    "path.exists() and not path.is_file()",
    "os.fchmod(fd, mode)",
    "os.fsync(handle.fileno())",
    "os.replace(tmp, path)",
    "tmp.unlink()",
)



def validate_yaml_root_permission(publisher: str, independent: str) -> None:
    """Pin YAML root mapping and permission leaves independently of full-source SHA."""
    for label, value, roots, expected_leaf in (
        ("publisher", publisher, ["name: Deletion Lease Recovery",
                                  "on:", "permissions:", "concurrency:", "jobs:"], "  contents: write"),
        ("independent", independent, ["name: Deletion Lease Recovery Diagnostic Source Negative",
                                      "on:", "permissions:", "jobs:"], "  contents: read"),
    ):
        actual = [line for line in value.splitlines()
                  if line.strip() and not line[0].isspace()
                  and not line.lstrip().startswith("#")]
        if actual != roots:
            raise AssertionError("lease-diagnostic " + label + " root YAML key shadow drift")
        if value.count("\npermissions:\n") != 1:
            raise AssertionError("lease-diagnostic " + label + " permission boundary drift")
        leaves = []
        for line in value.split("\npermissions:\n", 1)[1].splitlines():
            if line.strip() and not line[0].isspace():
                break
            if line.strip() and not line.lstrip().startswith("#"):
                leaves.append(line)
        if leaves != [expected_leaf]:
            raise AssertionError("lease-diagnostic " + label + " permission leaf shadow drift")


def yaml_root_permission_negatives(publisher: str, independent: str) -> None:
    """Demand twelve mutation-specific root/permission shadow diagnostics."""
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
        marker = "\npermissions:\n" + ("  contents: write\n" if is_publisher else "  contents: read\n")
        if value.count(marker) != 1:
            raise AssertionError("lease-diagnostic " + label + " permission fixture anchor drift")
        override = "read" if is_publisher else "write"
        for mutation, leaf in (
            ("spaced contents", "  contents : " + override + "\n"),
            ("quoted contents", "  'contents': " + override + "\n"),
        ):
            cases.append((mutation, value.replace(marker, marker + leaf, 1),
                          "permission leaf shadow drift"))
        cases.append(("changed contents", value.replace(marker, "\npermissions:\n  contents: " + override + "\n", 1),
                      "permission leaf shadow drift"))
        for mutation, changed, diagnostic in cases:
            if changed == value:
                raise AssertionError("lease-diagnostic unchanged YAML fixture: " + mutation)
            try:
                if is_publisher:
                    validate_yaml_root_permission(changed, other)
                else:
                    validate_yaml_root_permission(other, changed)
            except AssertionError as exc:
                expected = "lease-diagnostic " + label + " " + diagnostic
                if str(exc) != expected:
                    raise AssertionError("lease-diagnostic wrong YAML diagnostic: "
                                         + label + " " + mutation + ": " + str(exc)) from exc
            else:
                raise AssertionError("lease-diagnostic accepted YAML shadow: " + label + " " + mutation)
            count += 1
    if count != 14:
        raise AssertionError("lease-diagnostic YAML negative inventory drift")
    print("PASS: lease-diagnostic root/permission YAML authority (14 exact-diagnostic negatives)")


def policy(value):
    for marker in REQUIRED:
        if marker not in value:
            raise AssertionError("Lease recovery diagnostic source policy missing: " + marker[:70])
    if value.count("git fetch origin so") != 6:
        raise AssertionError("Pre-fence CAS fetch multiplicity drift")
    if value.count(CHECKOUT) != 1 or value.count(SETUP) != 1 or value.count(SETUP_GO) != 1:
        raise AssertionError("Pre-fence mutation immutable Actions source drift")
    if any(marker in value for marker in ("checkout@v4", "setup-go@v5", "setup-python@v5",
                                         "docker logs memory-os-deletion-lease-recovery-minio", "text[-12000:]",
                                         "path.write_text(", "path.parent.mkdir(")):
        raise AssertionError("Pre-fence mutation raw output/unsafe writer regression")


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
    print(f"PASS: lease recovery diagnostic policy source negatives ({len(REQUIRED) + 2} cases)")


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
    code = step(text, "Record privacy-safe failure diagnostic")
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
                                    env=dict(os.environ, SOURCE_SHA="a" * 40, PROOF_EXIT_CODE="23"),
                                    capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != (case in ("existing", "new")):
                raise AssertionError("SIGKILL inline writer acceptance drift: " + case)
            if canary.read_bytes() != b"SYNTHETIC_SECRET_CANARY":
                raise AssertionError("SIGKILL inline writer changed outside canary")
            if case in ("existing", "new"):
                value = json.loads(target.read_text(encoding="utf-8"))
                if (value["output"] != "Lease recovery proof failed; raw validator output withheld." or value["containsSecrets"] or value["productionEvidence"] or value["productionEquivalentDependencies"] or value["sourceCommitSha"] != "a" * 40 or value["result"] != "FAIL" or value["actualProcessKillCovered"] is not False or value["actualHostFailureCovered"] is not False or value["exitCode"] != 23):
                    raise AssertionError("SIGKILL diagnostic redaction/authority drift")
                if stat.S_IMODE(target.stat().st_mode) != (0o640 if case == "existing" else 0o600):
                    raise AssertionError("SIGKILL diagnostic mode drift")
            if case in ("replace", "fsync"):
                if target.read_bytes() != b"before\n" or stat.S_IMODE(target.stat().st_mode) != 0o640:
                    raise AssertionError("SIGKILL atomic rollback drift")
            if list(parent.glob(".*.tmp")):
                raise AssertionError("SIGKILL temp residue")
    print(f"PASS: {Path(PUBLISHER).stem} actual inline diagnostic writer redaction/atomic/symlink runtime (7 cases)")


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
    """Pin publisher inherited-write and independent explicit-read job YAML."""
    for label, content, name, condition, scope, timeout, keys in (
        ("publisher", publisher, "prove", None, None, 25,
         ("runs-on", "timeout-minutes", "services", "steps")),
        ("independent", independent, "source-negative",
         "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n",
         "read", 5, ("if", "permissions", "runs-on", "timeout-minutes", "steps")),
    ):
        prefix = "lease-recovery " + label + " "
        if content.count("\njobs:\n") != 1:
            raise SystemExit(prefix + "job mapping shadow drift")
        body = content.split("\njobs:\n", 1)[1]
        headers = [line for line in body.splitlines()
                   if line.startswith("  ") and len(line) > 2 and line[2] != " "
                   and not line.lstrip().startswith("#")]
        if headers != ["  " + name + ":"]:
            raise SystemExit(prefix + "job mapping shadow drift")
        section = body.split("  " + name + ":\n", 1)[1]
        actual = [line for line in section.splitlines()
                  if line.startswith("    ") and len(line) > 4 and line[4] != " "
                  and not line.lstrip().startswith("#")]
        expected = [
            condition.rstrip("\n") if key == "if" else
            "    runs-on: ubuntu-latest" if key == "runs-on" else
            "    timeout-minutes: " + str(timeout) if key == "timeout-minutes" else
            "    " + key + ":" for key in keys
        ]
        if actual != expected:
            raise SystemExit(prefix + name + " job key shadow drift")
        if condition is not None and section.split("    permissions:\n", 1)[0] != condition:
            raise SystemExit(prefix + name + " job condition drift")
        if scope is not None:
            leaves = []
            for line in section.split("    permissions:\n", 1)[1].splitlines():
                if line.startswith("    ") and len(line) > 4 and line[4] != " ":
                    break
                if line.strip() and not line.lstrip().startswith("#"):
                    leaves.append(line)
            if leaves != ["      contents: " + scope]:
                raise SystemExit(prefix + name + " job permission leaf shadow drift")


def prove_job_authority_negatives(publisher: str, independent: str) -> None:
    """Require exact diagnostics for 24 in-memory nested job shadows."""
    validate_job_authority(publisher, independent)
    total = 0
    for label, content, other, name, timeout, is_publisher in (
        ("publisher", publisher, independent, "prove", 25, True),
        ("independent", independent, publisher, "source-negative", 5, False),
    ):
        header = "  " + name + ":\n"
        if content.count(header) != 1:
            raise SystemExit("lease-recovery job mutation header drift: " + label)

        def mutate(old: str, new: str) -> str:
            start, rest = content.split(header, 1)
            if old not in rest:
                raise SystemExit("lease-recovery job mutation anchor drift: " + label)
            return start + header + rest.replace(old, new, 1)

        runner = "    runs-on: ubuntu-latest\n"
        limit = "    timeout-minutes: " + str(timeout) + "\n"
        steps = "    steps:\n"
        cases = [
            ("duplicate mapping", content + "\n" + header + runner, "job mapping shadow drift"),
            ("quoted mapping", content.replace(header, "  '" + name + "':\n", 1), "job mapping shadow drift"),
            ("spaced mapping", content.replace(header, "  " + name + " :\n", 1), "job mapping shadow drift"),
            ("runner shadow", mutate(runner, runner + "    runs-on : ubuntu-latest\n"), name + " job key shadow drift"),
            ("timeout shadow", mutate(limit, limit + "    timeout-minutes : 1\n"), name + " job key shadow drift"),
            ("steps shadow", mutate(steps, "    steps : []\n" + steps), name + " job key shadow drift"),
            ("continuation override", mutate(steps, "    continue-on-error: true\n" + steps), name + " job key shadow drift"),
        ]
        if is_publisher:
            cases += [
                ("job permission", mutate(runner, "    permissions:\n      contents: read\n" + runner), name + " job key shadow drift"),
                ("spaced permission", mutate(runner, "    permissions :\n      contents: write\n" + runner), name + " job key shadow drift"),
                ("quoted permission", mutate(runner, "    'permissions':\n      contents: write\n" + runner), name + " job key shadow drift"),
                ("services shadow", mutate("    services:\n", "    services : {}\n    services:\n"), name + " job key shadow drift"),
                ("unreviewed condition", mutate(runner, "    if: always()\n" + runner), name + " job key shadow drift"),
            ]
        else:
            condition = ("    if: github.event_name == 'pull_request' || "
                         "(github.event_name == 'push' && github.ref == 'refs/heads/so')\n")
            permission = "    permissions:\n      contents: read\n"
            cases += [
                ("condition shadow", mutate(condition, condition + "    if : true\n"), name + " job key shadow drift"),
                ("permission shadow", mutate(permission, permission + "    permissions :\n      contents: write\n"), name + " job key shadow drift"),
                ("direct permission", mutate(permission, permission.replace("contents: read", "contents: write")), name + " job permission leaf shadow drift"),
                ("spaced leaf", mutate(permission, permission + "      contents : write\n"), name + " job permission leaf shadow drift"),
                ("quoted leaf", mutate(permission, permission + "      'contents': write\n"), name + " job permission leaf shadow drift"),
            ]
        for mutation, changed, diagnostic in cases:
            if changed == content:
                raise SystemExit("lease-recovery unchanged job fixture: " + label + "/" + mutation)
            try:
                validate_job_authority(changed, other) if is_publisher else validate_job_authority(other, changed)
            except SystemExit as exc:
                expected = "lease-recovery " + label + " " + diagnostic
                if str(exc) != expected:
                    raise SystemExit("lease-recovery wrong job diagnostic: "
                                     + label + "/" + mutation + ": " + str(exc)) from exc
            else:
                raise SystemExit("lease-recovery accepted job shadow: " + label + "/" + mutation)
            total += 1
    if total != 24:
        raise SystemExit("lease-recovery job negative inventory drift")
    print("PASS: lease-recovery publisher/independent nested job authority (24 exact-diagnostic negatives)")


def validate_concurrency_authority(publisher: str) -> None:
    """Pin the reviewed lease-recovery diagnostic noncancelling serialization."""
    marker = "\nconcurrency:\n"
    end = "\njobs:\n"
    expected = "  group: deletion-lease-recovery-so\n  cancel-in-progress: false\n"
    if publisher.count(marker) != 1 or publisher.count(end) != 1:
        raise SystemExit("lease-diagnostic publisher concurrency scope drift")
    actual = publisher.split(marker, 1)[1].split(end, 1)[0]
    if actual != expected:
        raise SystemExit("lease-diagnostic publisher concurrency scope drift")


def prove_concurrency_authority_negatives(publisher: str) -> None:
    """Prove ten exact-diagnostic lease-recovery cancellation/group shadows."""
    validate_concurrency_authority(publisher)
    group = "  group: deletion-lease-recovery-so\n"
    original = group + "  cancel-in-progress: false\n"
    cases = (
        ("global group", "  group: deletion-lease-recovery-global\n  cancel-in-progress: false\n"),
        ("cancel enabled", original.replace("false", "true")),
        ("duplicate group", original + "  group: unreviewed-global\n"),
        ("duplicate cancellation", original + "  cancel-in-progress: true\n"),
        ("spaced group", original + "  group : unreviewed-global\n"),
        ("quoted group", original + "  'group': unreviewed-global\n"),
        ("spaced cancellation", original + "  cancel-in-progress : true\n"),
        ("quoted cancellation", original + "  'cancel-in-progress': true\n"),
        ("unreviewed leaf", original + "  max-parallel: 10\n"),
        ("removed cancellation", group),
    )
    if publisher.count(original) != 1:
        raise SystemExit("lease-diagnostic concurrency fixture anchor drift")
    for name, block in cases:
        changed = publisher.replace(original, block, 1)
        if changed == publisher:
            raise SystemExit("lease-diagnostic unchanged concurrency fixture: " + name)
        try:
            validate_concurrency_authority(changed)
        except SystemExit as exc:
            if str(exc) != "lease-diagnostic publisher concurrency scope drift":
                raise SystemExit(
                    "lease-diagnostic wrong concurrency diagnostic: " + name + ": " + str(exc)
                ) from exc
        else:
            raise SystemExit("lease-diagnostic accepted concurrency mutation: " + name)
    print("PASS: lease-diagnostic publisher concurrency serialization (10 exact-diagnostic negatives)")


def main():
    publisher = source(PUBLISHER)
    if blob(publisher) != REVIEWED:
        raise SystemExit("SIGKILL publisher complete Git blob unreviewed")
    independent = source(INDEPENDENT)
    for marker in (PUBLISHER, INDEPENDENT, SCRIPT, RECONCILER, RECONCILE_NEGATIVE, CHECKOUT, SETUP,
                   "persist-credentials: false", "contents: read",
                   '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'):
        if marker not in independent:
            raise AssertionError("SIGKILL independent CI reachability/source drift: " + marker)
    for path, reviewed in ((RESULT_VALIDATOR, REVIEWED_RESULT_VALIDATOR),
                           (RESULT_NEGATIVE, REVIEWED_RESULT_NEGATIVE)):
        if blob(source(path)) != reviewed:
            raise AssertionError("lease strict result source drift: " + path)
        if independent.count('      - "' + path + '"') != 2:
            raise AssertionError("lease strict result CI trigger drift: " + path)
    if "python -B " + RESULT_NEGATIVE not in independent:
        raise AssertionError("lease strict result negative not executed")
    if blob(independent) != REVIEWED_INDEPENDENT:
        raise SystemExit("SIGKILL independent workflow complete Git blob drift")
    if blob(source(RECONCILER)) != REVIEWED_RECONCILER:
        raise SystemExit("lease reconciler complete Git blob unreviewed")
    if blob(source(RECONCILE_NEGATIVE)) != REVIEWED_RECONCILE_NEGATIVE:
        raise SystemExit("lease reconcile negative complete Git blob unreviewed")
    validate_trigger_reachability(publisher, publisher=True)
    validate_trigger_reachability(independent, publisher=False)
    prove_trigger_reachability_negatives(publisher, independent)
    validate_yaml_root_permission(publisher, independent)
    yaml_root_permission_negatives(publisher, independent)
    prove_concurrency_authority_negatives(publisher)
    validate_job_authority(publisher, independent)
    prove_job_authority_negatives(publisher, independent)
    identity_runtime(independent, "Require exact clean lease recovery diagnostic source")
    policy(publisher)
    mutations(publisher)
    writer_runtime(publisher)
    print("PASS: lease recovery exact-source read-only diagnostic proof; production evidence generated: false; production decision changed: false")


if __name__ == "__main__":
    main()
