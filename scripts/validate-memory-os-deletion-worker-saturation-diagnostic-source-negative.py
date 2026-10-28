#!/usr/bin/env python3
"""Exact-source, read-only runtime negatives for SIGKILL failure diagnostics."""
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/deletion-worker-saturation.yml"
INDEPENDENT = ".github/workflows/deletion-worker-saturation-diagnostic-source-negative.yml"
SCRIPT = "scripts/validate-memory-os-deletion-worker-saturation-diagnostic-source-negative.py"
RECONCILER = "scripts/reconcile-memory-os-deletion-worker-saturation.py"
RECONCILE_NEGATIVE = "scripts/validate-memory-os-deletion-worker-saturation-reconcile-negative.py"
RECONCILE_VALIDATOR = "scripts/validate-memory-os-deletion-worker-saturation.py"
RECONCILE_CONTRACT = "contracts/operations/deletion-worker-saturation-contract.v1.json"
RECONCILE_RESULT = "docs/fixtures/memory-os-operability/deletion-worker-saturation-results.sample.v1.json"
REVIEWED_RECONCILER = "646faa0b0b2aac595255d8645dead25c38708864"
REVIEWED_RECONCILE_NEGATIVE = "f5889d7009f9c0c383df44620d75ba0d33bf5ecb"
REVIEWED_RECONCILE_VALIDATOR = "3f8ae2cc972ef5b5565d794e644c73f64dc9c872"
REVIEWED = "a671ebaddffe34d27b9b152044e2f510befe3f61"
REVIEWED_INDEPENDENT = "717e9b93b3e1c80c85da76780fe57512e2e262ff"
TARGET = "docs/fixtures/memory-os-operability/deletion-worker-saturation-diagnostic.last.json"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
SETUP_GO = "uses: actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5"


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
    '"output": "Worker saturation proof failed; raw validator output withheld."',
    '"containsSecrets": False',
    '"productionEvidence": False',
    '"productionEquivalentDependencies": False',
    '"sourceCommitSha": os.environ["SOURCE_SHA"]',
    '"capacityBoundaryEstablished": False',
    '"operationalThresholdApproved": False',
    "candidate.is_symlink()",
    "path.parent.resolve(strict=True).relative_to(repo)",
    "path.exists() and not path.is_file()",
    "os.fchmod(fd, mode)",
    "os.fsync(handle.fileno())",
    "os.replace(tmp, path)",
    "tmp.unlink()",
)


SATURATION_PUBLISHER_PUSH = (
    ".github/workflows/deletion-worker-saturation.yml",
    "contracts/operations/deletion-worker-saturation-contract.v1.json",
    "scripts/validate-memory-os-deletion-worker-saturation.py",
    "scripts/reconcile-memory-os-deletion-worker-saturation.py",
    "scripts/validate-memory-os-deletion-worker-saturation-reconcile-negative.py",
    "services/import-api/internal/httpserver/**",
    "services/import-api/internal/accountdelete/**",
    "services/import-api/internal/pgrepo/**",
    "services/import-api/internal/dbscope/**",
    "services/import-api/internal/pgscope/**",
    "services/import-api/internal/objectstore/**",
    "infra/postgresql/security/**",
    "services/import-api/go.mod",
    "services/import-api/go.sum",
)

SATURATION_INDEPENDENT_PR = (
    ".github/workflows/deletion-worker-saturation.yml",
    ".github/workflows/deletion-worker-saturation-diagnostic-source-negative.yml",
    "scripts/validate-memory-os-deletion-worker-saturation-diagnostic-source-negative.py",
    "scripts/reconcile-memory-os-deletion-worker-saturation.py",
    "scripts/validate-memory-os-deletion-worker-saturation-reconcile-negative.py",
    "scripts/validate-memory-os-deletion-worker-saturation.py",
    "contracts/operations/deletion-worker-saturation-contract.v1.json",
    "docs/fixtures/memory-os-operability/deletion-worker-saturation-results.sample.v1.json",
)

SATURATION_INDEPENDENT_PUSH = (
    ".github/workflows/deletion-worker-saturation.yml",
    ".github/workflows/deletion-worker-saturation-diagnostic-source-negative.yml",
    "scripts/validate-memory-os-deletion-worker-saturation-diagnostic-source-negative.py",
    "scripts/reconcile-memory-os-deletion-worker-saturation.py",
    "scripts/validate-memory-os-deletion-worker-saturation-reconcile-negative.py",
    "scripts/validate-memory-os-deletion-worker-saturation.py",
    "contracts/operations/deletion-worker-saturation-contract.v1.json",
    "docs/fixtures/memory-os-operability/deletion-worker-saturation-results.sample.v1.json",
)

def saturation_trigger_event(event, paths):
    return ("  " + event + ":\n    branches:\n      - so\n    paths:\n"
            + "".join('      - "' + path + '"\n' for path in paths))


def saturation_trigger_header(content):
    if content.count("\non:\n") != 1 or content.count("\npermissions:\n") != 1:
        raise AssertionError("worker-saturation workflow event header ambiguous")
    return content.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]


def saturation_trigger_matrix(
    publisher, independent,
    publisher_push=SATURATION_PUBLISHER_PUSH,
    independent_pr=SATURATION_INDEPENDENT_PR,
    independent_push=SATURATION_INDEPENDENT_PUSH,
):
    expected_publisher = (saturation_trigger_event("push", publisher_push)
                          + "  workflow_dispatch:\n")
    expected_independent = (saturation_trigger_event("pull_request", independent_pr)
                            + saturation_trigger_event("push", independent_push))
    for label, content, expected in (
        ("publisher", publisher, expected_publisher),
        ("independent", independent, expected_independent),
    ):
        if saturation_trigger_header(content) != expected:
            raise AssertionError("worker-saturation " + label + " exact trigger matrix drift")


def saturation_trigger_replace(content, old, new):
    anchor = "\non:\n" + old + "\npermissions:\n"
    if content.count(anchor) != 1 or old == new:
        raise AssertionError("worker-saturation trigger mutation fixture unreachable")
    return content.replace(anchor, "\non:\n" + new + "\npermissions:\n", 1)


def saturation_trigger_negatives(publisher, independent):
    def reject(p, i):
        try:
            saturation_trigger_matrix(p, i)
        except AssertionError:
            return
        raise AssertionError("worker-saturation accepted event trigger mutation")

    omissions = additions = 0
    for label, event, paths in (
        ("publisher", "push", SATURATION_PUBLISHER_PUSH),
        ("independent", "pull_request", SATURATION_INDEPENDENT_PR),
        ("independent", "push", SATURATION_INDEPENDENT_PUSH),
    ):
        original = publisher if label == "publisher" else independent
        header = saturation_trigger_header(original)
        block = saturation_trigger_event(event, paths)
        if header.count(block) != 1:
            raise AssertionError("worker-saturation event fixture ambiguous")
        for index in range(len(paths)):
            changed = saturation_trigger_replace(
                original, header,
                header.replace(block, saturation_trigger_event(
                    event, paths[:index] + paths[index + 1:]), 1))
            reject(changed, independent) if label == "publisher" else reject(publisher, changed)
            omissions += 1
        first = '      - "' + paths[0] + '"\n'
        for extra in (
            '      - "unreviewed/**"\n', '      - unreviewed/**\n',
            first, '      - ' + paths[0] + '\n',
        ):
            changed = saturation_trigger_replace(
                original, header,
                header.replace(block, block.replace(first, first + extra, 1), 1))
            reject(changed, independent) if label == "publisher" else reject(publisher, changed)
            additions += 1

    shortened = 0
    for field, paths in (
        ("publisher_push", SATURATION_PUBLISHER_PUSH),
        ("independent_pr", SATURATION_INDEPENDENT_PR),
        ("independent_push", SATURATION_INDEPENDENT_PUSH),
    ):
        try:
            saturation_trigger_matrix(publisher, independent, **{field: paths[:-1]})
        except AssertionError:
            shortened += 1
        else:
            raise AssertionError("worker-saturation accepted shortened trigger inventory")

    ph, ih = saturation_trigger_header(publisher), saturation_trigger_header(independent)
    topology = (
        (saturation_trigger_replace(
            publisher, ph, "  pull_request:\n    branches:\n      - so\n" + ph), independent),
        (saturation_trigger_replace(
            publisher, ph, ph.replace("  workflow_dispatch:\n", "", 1)), independent),
        (publisher, saturation_trigger_replace(
            independent, ih, ih + "  workflow_dispatch:\n")),
    )
    for p, i in topology:
        reject(p, i)
    print("PASS: worker-saturation exact trigger matrix: " + str(omissions)
          + " omissions, " + str(additions) + " additions/duplicates, "
          + str(shortened) + " shortened inventories, "
          + str(len(topology)) + " event topology negatives")



def validate_yaml_root_permission(publisher: str, independent: str) -> None:
    """Pin distinct reviewed publisher-write and independent-read YAML authority."""
    for label, value, roots, leaf in (
        ("publisher", publisher, ["name: Deletion Worker Saturation",
                                  "on:", "permissions:", "concurrency:", "jobs:"], "  contents: write"),
        ("independent", independent, ["name: Deletion Worker Saturation Diagnostic Source Negative",
                                      "on:", "permissions:", "jobs:"], "  contents: read"),
    ):
        actual = [line for line in value.splitlines()
                  if line.strip() and not line[0].isspace()
                  and not line.lstrip().startswith("#")]
        if actual != roots:
            raise AssertionError("worker-saturation " + label + " root YAML key shadow drift")
        if value.count("\npermissions:\n") != 1:
            raise AssertionError("worker-saturation " + label + " permission boundary drift")
        leaves = []
        for line in value.split("\npermissions:\n", 1)[1].splitlines():
            if line.strip() and not line[0].isspace():
                break
            if line.strip() and not line.lstrip().startswith("#"):
                leaves.append(line)
        if leaves != [leaf]:
            raise AssertionError("worker-saturation " + label + " permission leaf shadow drift")


def yaml_root_permission_negatives(publisher: str, independent: str) -> None:
    """Prove fourteen exact-diagnostic YAML root and permission mutations."""
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
        reviewed = "write" if is_publisher else "read"
        opposite = "read" if is_publisher else "write"
        marker = "\npermissions:\n  contents: " + reviewed + "\n"
        if value.count(marker) != 1:
            raise AssertionError("worker-saturation " + label + " permission fixture anchor drift")
        for mutation, leaf in (
            ("spaced contents", "  contents : " + opposite + "\n"),
            ("quoted contents", "  'contents': " + opposite + "\n"),
        ):
            cases.append((mutation, value.replace(marker, marker + leaf, 1),
                          "permission leaf shadow drift"))
        cases.append(("changed contents",
                      value.replace(marker, "\npermissions:\n  contents: " + opposite + "\n", 1),
                      "permission leaf shadow drift"))
        for mutation, changed, diagnostic in cases:
            if changed == value:
                raise AssertionError("worker-saturation unchanged YAML fixture: " + mutation)
            try:
                if is_publisher:
                    validate_yaml_root_permission(changed, other)
                else:
                    validate_yaml_root_permission(other, changed)
            except AssertionError as exc:
                expected = "worker-saturation " + label + " " + diagnostic
                if str(exc) != expected:
                    raise AssertionError("worker-saturation wrong YAML diagnostic: "
                                         + label + " " + mutation + ": " + str(exc)) from exc
            else:
                raise AssertionError("worker-saturation accepted YAML shadow: " + label + " " + mutation)
            count += 1
    if count != 14:
        raise AssertionError("worker-saturation YAML negative inventory drift")
    print("PASS: worker-saturation root/permission YAML authority (14 exact-diagnostic negatives)")


def policy(value):
    for marker in REQUIRED:
        if marker not in value:
            raise AssertionError("Worker saturation diagnostic source policy missing: " + marker[:70])
    if value.count("git fetch origin so") != 6:
        raise AssertionError("Pre-fence CAS fetch multiplicity drift")
    if value.count(CHECKOUT) != 1 or value.count(SETUP) != 1 or value.count(SETUP_GO) != 1:
        raise AssertionError("Pre-fence mutation immutable Actions source drift")
    if any(marker in value for marker in ("checkout@v4", "setup-go@v5", "setup-python@v5",
                                         "docker logs memory-os-worker-saturation-minio", "text[-12000:]",
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
    print(f"PASS: worker saturation diagnostic policy source negatives ({len(REQUIRED) + 2} cases)")


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
                                    env=dict(os.environ, SOURCE_SHA="a" * 40, WORKER_SATURATION_EXIT_CODE="23"),
                                    capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != (case in ("existing", "new")):
                raise AssertionError("SIGKILL inline writer acceptance drift: " + case)
            if canary.read_bytes() != b"SYNTHETIC_SECRET_CANARY":
                raise AssertionError("SIGKILL inline writer changed outside canary")
            if case in ("existing", "new"):
                value = json.loads(target.read_text(encoding="utf-8"))
                if (value["output"] != "Worker saturation proof failed; raw validator output withheld." or value["containsSecrets"] or value["productionEvidence"] or value["productionEquivalentDependencies"] or value["sourceCommitSha"] != "a" * 40 or value["result"] != "FAIL" or value["capacityBoundaryEstablished"] is not False or value["operationalThresholdApproved"] is not False or value["exitCode"] != 23):
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



def reconcile_runtime():
    # The reconciler negative mutates its canonical fixtures; execute only in a disposable copy.
    for path, reviewed in ((RECONCILER, REVIEWED_RECONCILER),
                           (RECONCILE_NEGATIVE, REVIEWED_RECONCILE_NEGATIVE),
                           (RECONCILE_VALIDATOR, REVIEWED_RECONCILE_VALIDATOR)):
        if blob(source(path)) != reviewed:
            raise AssertionError("unreviewed saturation reconcile source: " + path)
    with tempfile.TemporaryDirectory(prefix="worker-saturation-reconcile-negative-") as tmp:
        root = Path(tmp)
        for path in (RECONCILER, RECONCILE_NEGATIVE, RECONCILE_VALIDATOR,
                     RECONCILE_CONTRACT, RECONCILE_RESULT):
            original = ROOT / path
            if original.is_symlink() or not original.is_file():
                raise AssertionError("saturation reconcile fixture missing or symlinked: " + path)
            destination = root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, destination)
        result = subprocess.run([sys.executable, str(root / RECONCILE_NEGATIVE)],
                                cwd=root, capture_output=True, text=True, timeout=45, check=False)
        if result.returncode != 0 or "secret-free validator output/import/rollback diagnostics" not in result.stdout:
            raise AssertionError("disposable saturation reconcile negative failed: "
                                 + result.stdout[-500:] + result.stderr[-500:])
    print("PASS: source-bound disposable saturation reconcile validator/rollback negatives")


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
    for path in (RECONCILER, RECONCILE_NEGATIVE, RECONCILE_VALIDATOR, RECONCILE_CONTRACT, RECONCILE_RESULT):
        if independent.count('      - "' + path + '"') != 2:
            raise AssertionError("saturation reconcile CI path trigger missing: " + path)
    if blob(independent) != REVIEWED_INDEPENDENT:
        raise SystemExit("SIGKILL independent workflow complete Git blob drift")
    identity_runtime(independent, "Require exact clean worker saturation diagnostic source")
    policy(publisher)
    saturation_trigger_matrix(publisher, independent)
    saturation_trigger_negatives(publisher, independent)
    validate_yaml_root_permission(publisher, independent)
    yaml_root_permission_negatives(publisher, independent)
    mutations(publisher)
    writer_runtime(publisher)
    reconcile_runtime()
    print("PASS: worker saturation exact-source read-only diagnostic proof; production evidence generated: false; production decision changed: false")


if __name__ == "__main__":
    main()
