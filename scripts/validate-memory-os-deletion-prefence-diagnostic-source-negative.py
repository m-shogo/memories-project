#!/usr/bin/env python3
"""Exact-source, read-only runtime negatives for SIGKILL failure diagnostics."""
import copy
import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/deletion-prefence-linearization.yml"
INDEPENDENT = ".github/workflows/deletion-prefence-diagnostic-source-negative.yml"
SCRIPT = "scripts/validate-memory-os-deletion-prefence-diagnostic-source-negative.py"
RECONCILER = "scripts/reconcile-memory-os-deletion-prefence-linearization.py"
RECONCILE_NEGATIVE = "scripts/validate-memory-os-deletion-prefence-linearization-reconcile-negative.py"
VALIDATOR = "scripts/validate-memory-os-deletion-prefence-linearization.py"
REVIEWED_VALIDATOR = "9b1cbb8aed09a9b519073ab6eff437630c30965c"
REVIEWED_RECONCILER = "75c848b6d45f0fa1f51a187ac67344339bcc05d9"
REVIEWED_RECONCILE_NEGATIVE = "623c4b0bd3ceffbc034de9ae0639013327b2b252"
REVIEWED = "fdcc951be6c589518f1f48bcb363b5dcd0b88602"
REVIEWED_INDEPENDENT = "7245af8ba2a4433f3b4283c7dceaa9123ff522fd"
TARGET = "docs/fixtures/memory-os-operability/deletion-prefence-linearization-diagnostic.last.json"
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
    '"output": "Pre-fence proof failed; raw validator output withheld."',
    '"containsSecrets": False',
    '"productionEvidence": False',
    '"productionEquivalentDependencies": False',
    '"sourceCommitSha": os.environ["SOURCE_SHA"]',
    "candidate.is_symlink()",
    "path.parent.resolve(strict=True).relative_to(repo)",
    "path.exists() and not path.is_file()",
    "os.fchmod(fd, mode)",
    "os.fsync(handle.fileno())",
    "os.replace(tmp, path)",
    "tmp.unlink()",
    'if git diff --cached --quiet; then',
    'echo "RESULT_COMMIT_SHA=$SOURCE_SHA" >> "$GITHUB_ENV"',
    'Branch advanced before pre-fence result push; refusing stale evidence.',
    'if [[ "$(git rev-parse origin/so)" != "$SOURCE_SHA" ]]; then',
)


def policy(value):
    for marker in REQUIRED:
        if marker not in value:
            raise AssertionError("Pre-fence diagnostic source policy missing: " + marker[:70])
    if value.count("git fetch origin so") != 7:
        raise AssertionError("Pre-fence CAS fetch multiplicity drift")
    if value.count('if [[ "$(git rev-parse origin/so)" != "$SOURCE_SHA" ]]; then') != 2:
        raise AssertionError("Pre-fence post-commit CAS guard multiplicity drift")
    if value.count("git diff --cached --quiet") != 3:
        raise AssertionError("Pre-fence staged no-op guard multiplicity drift")
    if value.count(CHECKOUT) != 1 or value.count(SETUP) != 1 or value.count(SETUP_GO) != 1:
        raise AssertionError("Pre-fence immutable Actions source drift")
    if any(marker in value for marker in ("checkout@v4", "setup-go@v5", "setup-python@v5",
                                         "docker logs memory-os-prefence-minio", "text[-12000:]",
                                         "path.write_text(", "path.parent.mkdir(")):
        raise AssertionError("Pre-fence raw output/unsafe writer regression")


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
    print(f"PASS: pre-fence diagnostic policy source negatives ({len(REQUIRED) + 2} cases)")


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
                                    env=dict(os.environ, SOURCE_SHA="a" * 40, PREFENCE_PROOF_EXIT_CODE="23"),
                                    capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != (case in ("existing", "new")):
                raise AssertionError("SIGKILL inline writer acceptance drift: " + case)
            if canary.read_bytes() != b"SYNTHETIC_SECRET_CANARY":
                raise AssertionError("SIGKILL inline writer changed outside canary")
            if case in ("existing", "new"):
                value = json.loads(target.read_text(encoding="utf-8"))
                if (value["output"] != "Pre-fence proof failed; raw validator output withheld." or value["containsSecrets"] or value["productionEvidence"] or value["productionEquivalentDependencies"] or value["sourceCommitSha"] != "a" * 40 or value["result"] != "FAIL" or value["exitCode"] != 23):
                    raise AssertionError("SIGKILL diagnostic redaction/authority drift")
                if stat.S_IMODE(target.stat().st_mode) != (0o640 if case == "existing" else 0o600):
                    raise AssertionError("SIGKILL diagnostic mode drift")
            if case in ("replace", "fsync"):
                if target.read_bytes() != b"before\n" or stat.S_IMODE(target.stat().st_mode) != 0o640:
                    raise AssertionError("SIGKILL atomic rollback drift")
            if list(parent.glob(".*.tmp")):
                raise AssertionError("SIGKILL temp residue")
    print("PASS: pre-fence actual inline diagnostic writer redaction/atomic/symlink runtime (7 cases)")


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




def result_commit_runtime(publisher):
    """Execute the real result publisher in a disposable fake-Git CAS/no-op sandbox."""
    command = step(publisher, "Commit exact-source result")
    source_sha, new_sha, stale_sha = "a" * 40, "c" * 40, "b" * 40
    fake_git = """#!/usr/bin/env python3
import os
import sys
from pathlib import Path
args = sys.argv[1:]
root = Path(os.environ["FAKE_GIT_STATE"])
with (root / "calls").open("a", encoding="utf-8") as log:
    log.write(" ".join(args) + "\\n")
if args == ["fetch", "origin", "so"]:
    count = int((root / "fetches").read_text()) + 1
    (root / "fetches").write_text(str(count))
    if count == 2 and os.environ["FAKE_RACE"] == "1":
        (root / "remote").write_text("b" * 40)
elif args == ["rev-parse", "HEAD"]:
    print((root / "head").read_text())
elif args == ["rev-parse", "origin/so"]:
    print((root / "remote").read_text())
elif args == ["diff", "--cached", "--quiet"]:
    sys.exit(0 if os.environ["FAKE_NOOP"] == "1" else 1)
elif args[:2] == ["commit", "-m"]:
    (root / "head").write_text("c" * 40)
elif args[0] in ("config", "add", "push"):
    pass
else:
    sys.exit(92)
"""
    cases = (
        ("noop", source_sha, source_sha, True, False, 0, 0, 0, source_sha),
        ("success", source_sha, source_sha, False, False, 0, 1, 1, new_sha),
        ("stale-remote", stale_sha, source_sha, False, False, 75, 0, 0, None),
        ("missing-remote", "", source_sha, False, False, 75, 0, 0, None),
        ("stale-local", source_sha, stale_sha, False, False, 75, 0, 0, None),
        ("race-after-commit", source_sha, source_sha, False, True, 75, 0, 1, new_sha),
    )
    for label, remote, local, noop, race, expected_exit, expected_push, expected_commit, expected_result in cases:
        with tempfile.TemporaryDirectory(prefix="prefence-result-cas-") as temp:
            root = Path(temp)
            git = root / "git"
            git.write_text(fake_git, encoding="utf-8")
            git.chmod(0o755)
            for name, value in (("head", local), ("remote", remote), ("fetches", "0"), ("calls", "")):
                (root / name).write_text(value, encoding="utf-8")
            env_file = root / "github-env"
            env_file.write_text("", encoding="utf-8")
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       SOURCE_SHA=source_sha, GITHUB_ENV=str(env_file), FAKE_GIT_STATE=str(root),
                       FAKE_NOOP="1" if noop else "0", FAKE_RACE="1" if race else "0")
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", command],
                                    cwd=root, env=env, capture_output=True, text=True,
                                    timeout=10, check=False)
            calls = (root / "calls").read_text(encoding="utf-8").splitlines()
            pushes = sum(call == "push origin HEAD:so" for call in calls)
            commits = sum(call.startswith("commit -m ") for call in calls)
            if (result.returncode != expected_exit or pushes != expected_push or
                    commits != expected_commit):
                raise AssertionError(f"pre-fence result {label} CAS/no-op drift: "
                                     f"exit={result.returncode}, pushes={pushes}, commits={commits}")
            expected_env = "" if expected_result is None else "RESULT_COMMIT_SHA=" + expected_result + "\n"
            if env_file.read_text(encoding="utf-8") != expected_env:
                raise AssertionError("pre-fence result source-binding environment drift: " + label)
    print(f"PASS: pre-fence actual result publisher CAS/no-op shell ({len(cases)} cases)")



def authority_reconcile_runtime(publisher):
    """Execute the actual derived-authority publisher in a disposable fake-Git sandbox."""
    command = step(publisher, "Reconcile local-only authority")
    source_sha, result_sha, new_sha, stale_sha = "a" * 40, "c" * 40, "d" * 40, "b" * 40
    fake_git = """#!/usr/bin/env python3
import os
import sys
from pathlib import Path
args = sys.argv[1:]
root = Path(os.environ["FAKE_GIT_STATE"])
with (root / "calls").open("a", encoding="utf-8") as log:
    log.write(" ".join(args) + "\\n")
if args == ["fetch", "origin", "so"]:
    count = int((root / "fetches").read_text()) + 1
    (root / "fetches").write_text(str(count))
    if count == 2 and os.environ["FAKE_RACE"] == "1":
        (root / "remote").write_text("b" * 40)
elif args == ["rev-parse", "HEAD"]:
    print((root / "head").read_text())
elif args == ["rev-parse", "origin/so"]:
    print((root / "remote").read_text())
elif args == ["diff", "--cached", "--quiet"]:
    sys.exit(0 if os.environ["FAKE_NOOP"] == "1" else 1)
elif args[:2] == ["commit", "-m"]:
    (root / "head").write_text("d" * 40)
elif args[0] in ("config", "add", "rm", "push"):
    pass
else:
    sys.exit(92)
"""
    fake_python = """#!/bin/sh
printf '%s\\n' "$*" >> "$FAKE_PYTHON_LOG"
if [ "$FAKE_PYTHON_FAIL" = "1" ]; then exit 23; fi
exit 0
"""
    cases = (
        ("noop", result_sha, result_sha, True, False, False, 0, 0, 0, 2),
        ("success", result_sha, result_sha, False, False, False, 0, 1, 1, 2),
        ("stale-remote", stale_sha, result_sha, False, False, False, 75, 0, 0, 0),
        ("missing-remote", "", result_sha, False, False, False, 75, 0, 0, 0),
        ("stale-local", result_sha, stale_sha, False, False, False, 75, 0, 0, 0),
        ("race-after-commit", result_sha, result_sha, False, True, False, 75, 0, 1, 2),
        ("validator-failure", result_sha, result_sha, False, False, True, 23, 0, 0, 1),
    )
    for label, remote, local, noop, race, fail_python, expected_exit, expected_push, expected_commit, expected_python in cases:
        with tempfile.TemporaryDirectory(prefix="prefence-authority-cas-") as temp:
            root = Path(temp)
            for name, contents in (("git", fake_git), ("python", fake_python)):
                command_path = root / name
                command_path.write_text(contents, encoding="utf-8")
                command_path.chmod(0o755)
            for name, value in (("head", local), ("remote", remote), ("fetches", "0"), ("calls", ""), ("python.log", "")):
                (root / name).write_text(value, encoding="utf-8")
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       SOURCE_SHA=source_sha, RESULT_COMMIT_SHA=result_sha, FAKE_GIT_STATE=str(root),
                       FAKE_NOOP="1" if noop else "0", FAKE_RACE="1" if race else "0",
                       FAKE_PYTHON_FAIL="1" if fail_python else "0", FAKE_PYTHON_LOG=str(root / "python.log"))
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", command],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
            calls = (root / "calls").read_text(encoding="utf-8").splitlines()
            pushes = sum(call == "push origin HEAD:so" for call in calls)
            commits = sum(call.startswith("commit -m ") for call in calls)
            python_calls = len((root / "python.log").read_text(encoding="utf-8").splitlines())
            if (result.returncode != expected_exit or pushes != expected_push or
                    commits != expected_commit or python_calls != expected_python):
                raise AssertionError(f"pre-fence authority {label} CAS/no-op drift: "
                                     f"exit={result.returncode}, pushes={pushes}, "
                                     f"commits={commits}, validator calls={python_calls}")
    print(f"PASS: pre-fence actual authority reconcile CAS/no-op/validator shell ({len(cases)} cases)")


def strict_validator_runtime():
    """Execute the real pre-fence evidence consumer against disposable JSON/path mutations."""
    spec = importlib.util.spec_from_file_location("prefence_strict_validator", ROOT / VALIDATOR)
    if spec is None or spec.loader is None:
        raise AssertionError("pre-fence validator loader missing")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    contract = validator.load(validator.CONTRACT_PATH)
    validator.validate_contract(contract)
    validator.validate_result(contract, None)
    canonical = validator.load(validator.RESULT_PATH)
    cases = 0

    with tempfile.TemporaryDirectory(prefix="prefence-reader-outside-") as outside_temp, \
         tempfile.TemporaryDirectory(prefix=".prefence-reader-", dir=ROOT) as inside_temp:
        outside, inside = Path(outside_temp), Path(inside_temp)
        canary = outside / "canary.json"
        canary.write_bytes(b'{"synthetic":true}')
        good = inside / "good.json"
        good.write_text('{"safe":true}', encoding="utf-8")
        if validator.load(good) != {"safe": True}:
            raise AssertionError("pre-fence JSON positive control failed")

        for label, raw in (
            ("nested duplicate", '{"outer":{"key":1,"key":2}}'),
            ("NaN", '{"value":NaN}'),
            ("infinite exponent", '{"value":1e999}'),
            ("huge integer", '{"value":' + "9" * 5000 + '}'),
            ("nonobject root", '["safe"]'),
            ("synthetic secret malformed", '{"SYNTHETIC_PREFENCE_SECRET":'),
        ):
            path = inside / (label.replace(" ", "-") + ".json")
            path.write_text(raw, encoding="utf-8")
            try:
                validator.load(path)
            except validator.Fail as exc:
                if "SYNTHETIC_PREFENCE_SECRET" in str(exc):
                    raise AssertionError("pre-fence JSON diagnostic reflected untrusted material") from None
            else:
                raise AssertionError("pre-fence JSON accepted " + label)
            cases += 1

        invalid_utf8 = inside / "invalid-utf8.json"
        invalid_utf8.write_bytes(b'{"value":"' + bytes([255]) + b'"}')
        try:
            validator.load(invalid_utf8)
        except validator.Fail:
            pass
        else:
            raise AssertionError("pre-fence JSON accepted invalid UTF-8")
        cases += 1

        linked = inside / "linked.json"
        linked.symlink_to(canary)
        linked_parent = inside / "linked-parent"
        linked_parent.symlink_to(outside, target_is_directory=True)
        directory = inside / "directory.json"
        directory.mkdir()
        for label, unsafe in (
            ("outside", canary),
            ("symlink", linked),
            ("ancestor symlink", linked_parent / "canary.json"),
            ("directory", directory),
            ("missing", inside / "missing.json"),
        ):
            try:
                validator.load(unsafe)
            except validator.Fail:
                pass
            else:
                raise AssertionError("pre-fence JSON accepted " + label)
            cases += 1

        original_result = validator.RESULT_PATH
        synthetic = inside / "synthetic-result.json"
        validator.RESULT_PATH = synthetic
        try:
            for label, marker in (
                ("postgres", "PoStGrEs://synthetic.invalid"),
                ("minio", "MiNiOaDmIn"),
                ("bearer", "bEaReR SYNTHETIC"),
                ("amz credential", "x-aMz-cRedenTial=SYNTHETIC"),
                ("account", "AcCt_SYNTHETIC"),
                ("job", "JoB_SYNTHETIC"),
            ):
                mutated = copy.deepcopy(canonical)
                mutated["environment"]["syntheticNegativeMarker"] = marker
                synthetic.write_text(json.dumps(mutated), encoding="utf-8")
                try:
                    validator.validate_result(contract, None)
                except validator.Fail as exc:
                    if "forbidden runtime material" not in str(exc) or marker in str(exc):
                        raise AssertionError("pre-fence marker wrong rejection: " + label) from None
                else:
                    raise AssertionError("pre-fence accepted mixed-case marker: " + label)
                cases += 1

            dangling = inside / "dangling-result.json"
            dangling.symlink_to(outside / "absent.json")
            validator.RESULT_PATH = dangling
            old_argv = sys.argv
            sys.argv = [old_argv[0]]
            try:
                try:
                    validator.main()
                except validator.Fail as exc:
                    if "result symlink rejected" not in str(exc):
                        raise AssertionError("pre-fence optional symlink wrong rejection") from None
                else:
                    raise AssertionError("pre-fence optional dangling symlink accepted")
            finally:
                sys.argv = old_argv
            cases += 1
        finally:
            validator.RESULT_PATH = original_result

        if canary.read_bytes() != b'{"synthetic":true}':
            raise AssertionError("pre-fence JSON consumer mutated outside canary")
    print(f"PASS: pre-fence actual strict JSON/path/mixed-case runtime ({cases} negative cases)")


def typed_criteria_runtime():
    """Reject coordinated contract weakening and Python bool/float numeric equality."""
    spec = importlib.util.spec_from_file_location("prefence_typed_validator", ROOT / VALIDATOR)
    if spec is None or spec.loader is None:
        raise AssertionError("pre-fence typed validator loader missing")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    contract = validator.load(validator.CONTRACT_PATH)
    validator.validate_contract(contract)
    validator.validate_result(contract, None)
    canonical = validator.load(validator.RESULT_PATH)
    cases = 0

    for key, expected in validator.EXPECTED_CRITERIA.items():
        candidate = copy.deepcopy(contract)
        candidate["successCriteria"][key] = (
            float(expected) if type(expected) is int else
            0 if type(expected) is bool else expected.upper()
        )
        try:
            validator.validate_contract(candidate)
        except validator.Fail:
            pass
        else:
            raise AssertionError("pre-fence accepted contract criterion mutation: " + key)
        cases += 1

    for label, mutate in (
        ("missing criterion", lambda c: c["successCriteria"].pop("unexpectedStatusCount")),
        ("extra criterion", lambda c: c["successCriteria"].update({"synthetic": True})),
        ("float in-flight", lambda c: c.update({"inFlightRequests": 32.0})),
        ("bool in-flight", lambda c: c.update({"inFlightRequests": True})),
    ):
        candidate = copy.deepcopy(contract)
        mutate(candidate)
        try:
            validator.validate_contract(candidate)
        except validator.Fail:
            pass
        else:
            raise AssertionError("pre-fence accepted " + label)
        cases += 1

    with tempfile.TemporaryDirectory(prefix=".prefence-typed-", dir=ROOT) as temp:
        synthetic = Path(temp) / "result.json"
        original = validator.RESULT_PATH
        validator.RESULT_PATH = synthetic
        try:
            for label, key, value in (
                ("float authenticated", "authenticatedBeforeFence", 32.0),
                ("bool zero", "unexpectedStatusCount", False),
                ("float epoch", "deletionEpoch", 2.0),
                ("float in-flight", "inFlightRequests", 32.0),
                ("changed state", "finalAccountState", "DELETED"),
                ("missing criterion", "workerReceiptCount", None),
            ):
                candidate = copy.deepcopy(canonical)
                if value is None:
                    candidate["scenario"].pop(key)
                else:
                    candidate["scenario"][key] = value
                synthetic.write_text(json.dumps(candidate), encoding="utf-8")
                try:
                    validator.validate_result(contract, None)
                except validator.Fail:
                    pass
                else:
                    raise AssertionError("pre-fence accepted typed result mutation: " + label)
                cases += 1
        finally:
            validator.RESULT_PATH = original
    print(f"PASS: pre-fence actual typed contract/result criteria runtime ({cases} negative cases)")


def main():
    publisher = source(PUBLISHER)
    if blob(publisher) != REVIEWED:
        raise SystemExit("SIGKILL publisher complete Git blob unreviewed")
    if blob(source(VALIDATOR)) != REVIEWED_VALIDATOR:
        raise SystemExit("pre-fence validator complete Git blob unreviewed")
    independent = source(INDEPENDENT)
    if independent.count('      - "scripts/validate-memory-os-deletion-prefence-linearization.py"') != 2:
        raise AssertionError("pre-fence validator CI trigger reachability drift")
    for marker in (PUBLISHER, INDEPENDENT, SCRIPT, RECONCILER, RECONCILE_NEGATIVE, CHECKOUT, SETUP,
                   "persist-credentials: false", "contents: read",
                   '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'):
        if marker not in independent:
            raise AssertionError("SIGKILL independent CI reachability/source drift: " + marker)
    if blob(independent) != REVIEWED_INDEPENDENT:
        raise SystemExit("SIGKILL independent workflow complete Git blob drift")
    if blob(source(RECONCILER)) != REVIEWED_RECONCILER:
        raise SystemExit("pre-fence reconciler complete Git blob unreviewed")
    if blob(source(RECONCILE_NEGATIVE)) != REVIEWED_RECONCILE_NEGATIVE:
        raise SystemExit("pre-fence reconciler negative complete Git blob unreviewed")
    identity_runtime(independent, "Require exact clean pre-fence diagnostic source")
    policy(publisher)
    mutations(publisher)
    writer_runtime(publisher)
    result_commit_runtime(publisher)
    authority_reconcile_runtime(publisher)
    strict_validator_runtime()
    typed_criteria_runtime()
    subprocess.run([sys.executable, str(ROOT / RECONCILE_NEGATIVE)],
                   cwd=ROOT, check=True, timeout=30)
    print("PASS: pre-fence exact-source read-only diagnostic proof; production evidence generated: false; production decision changed: false")


if __name__ == "__main__":
    main()
