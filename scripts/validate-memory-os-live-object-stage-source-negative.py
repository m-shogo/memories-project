#!/usr/bin/env python3
"""Independent exact-source event/branch/SHA runtime proof for live object diagnostics."""
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-live-object-stage-diagnostics.yml"
INDEPENDENT = ".github/workflows/live-object-stage-source-negative.yml"
SELF = "scripts/validate-memory-os-live-object-stage-source-negative.py"
REVIEWED_PUBLISHER = "7df80744055bd48c4dd7e87137109178d1c1f185"
REVIEWED_INDEPENDENT = "a87b554aaf9c2c011601d1f0d0d6a7390d4a614f"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP_PY = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
SETUP_GO = "uses: actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5"

def source(path):
    p = ROOT / path
    if p.is_symlink() or not p.is_file() or p.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise SystemExit("live object stage source missing or substituted: " + path)
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
    'test "${GITHUB_BASE_REF:-}" = "so"',
    'test "${GITHUB_REF:-}" = "refs/heads/so"',
    '[[ "$PR_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]',
    '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"',
    'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
    "git ls-remote origin refs/heads/so",
    'if [[ "$remote_sha" != "$SOURCE_SHA" ]]',
    "git push origin HEAD:so",
    "if git diff --cached --quiet; then",
    "git diff --cached --check",
    'git commit -m "test(load): classify MinIO lifecycle failures"',
)

def policy(text):
    for marker in REQUIRED:
        if marker not in text:
            raise AssertionError("live object stage policy missing: " + marker[:65])
    if any(text.count(action) != 2 for action in (CHECKOUT, SETUP_PY, SETUP_GO)):
        raise AssertionError("live object stage immutable Actions drift")
    if any(marker in text for marker in ("checkout@v4", "setup-python@v5", "setup-go@v5")):
        raise AssertionError("live object stage floating Actions regression")

def negatives(text):
    for index, marker in enumerate(REQUIRED):
        if text.count(marker) != 1:
            raise AssertionError("live object stage mutation marker multiplicity drift: " + str(index))
        changed = text.replace(marker, "REMOVED_NEGATIVE", 1)
        try:
            policy(changed)
        except AssertionError:
            continue
        raise AssertionError("live object stage source accepted mutation " + str(index))
    for action in (CHECKOUT, SETUP_PY, SETUP_GO):
        try:
            policy(text.replace(action, "uses: actions/checkout@v4", 1))
        except AssertionError:
            continue
        raise AssertionError("live object stage floating Action accepted")
    print("PASS: live object stage source negative mutations (21 cases)")

def step(text, title):
    marker = "      - name: " + title + "\n"
    if text.count(marker) != 1:
        raise AssertionError("live object stage source step ambiguous")
    start = text.index("        run: |\n", text.index(marker)) + len("        run: |\n")
    boundaries = [i for marker in ("\n      - name:", "\n  reconcile:", "\n  validate-pr:")
                  if (i := text.find(marker, start)) >= 0]
    end = min(boundaries) if boundaries else len(text)
    lines = text[start:end].splitlines()
    if not lines or any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("live object stage step indentation drift")
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"

def runtime(text, title, writer):
    shell = step(text, title)
    if writer:
        shell = shell.split("python -m py_compile", 1)[0]
    else:
        shell = shell.split("python -m py_compile", 1)[0]
    head = "a" * 40
    cases = (
        ("pull_request", "so", "", head, "", not writer),
        ("pull_request", "main", "", head, "", False),
        ("pull_request", "so", "", "A" * 40, "", False),
        ("pull_request", "so", "", "b" * 40, "", False),
        ("push", "", "refs/heads/so", "", head, writer),
        ("push", "", "refs/heads/main", "", head, False),
        ("push", "", "refs/heads/so", "", "A" * 40, False),
        ("push", "", "refs/heads/so", "", "b" * 40, False),
        ("schedule", "", "refs/heads/so", "", head, False),
        ("workflow_dispatch", "", "refs/heads/so", "", head, writer),
    )
    with tempfile.TemporaryDirectory(prefix="live-object-source-") as tmp:
        root = Path(tmp)
        git = root / "git"
        git.write_text("#!/bin/sh\n"
                       "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"HEAD\" ]; then printf '" + head + "\\n'; exit 0; fi\n"
                       "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then exit 0; fi\n"
                       "exit 1\n", encoding="utf-8")
        git.chmod(0o755)
        envfile = root / "github-env"
        for event, base, ref, pr_sha, sha, allowed in cases:
            envfile.write_text("", encoding="utf-8")
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_EVENT_NAME=event, GITHUB_BASE_REF=base, GITHUB_REF=ref,
                       PR_HEAD_SHA=pr_sha, GITHUB_SHA=sha, GITHUB_ENV=str(envfile))
            r = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell], cwd=root,
                               env=env, capture_output=True, text=True, timeout=10, check=False)
            if (r.returncode == 0) != allowed:
                raise AssertionError("live object stage source shell event/base/ref/SHA drift: " + title + "/" + event)
    print("PASS: live object stage actual " + ("writer" if writer else "PR") + " source shell runtime (10 cases)")


def publisher_runtime(text):
    """Execute the actual publisher commit step against disposable local Git remotes."""
    import shlex
    import shutil

    shell = step(text, "Commit diagnostic authority")
    target = "services/import-api/internal/httpserver/live_object_load_test.go"
    real_git = shutil.which("git")
    if not real_git:
        raise AssertionError("git executable missing")

    def git(cwd, *args):
        result = subprocess.run([real_git, *args], cwd=cwd, capture_output=True,
                                text=True, timeout=20, check=False)
        if result.returncode:
            raise AssertionError("disposable git setup failed: " + result.stderr[-400:])
        return result.stdout.strip()

    def publish(work, source_sha, extra_env=None):
        env = dict(os.environ, SOURCE_SHA=source_sha)
        if extra_env:
            env.update(extra_env)
        return subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                              cwd=work, env=env, capture_output=True, text=True,
                              timeout=20, check=False)

    def mutate(work, comment):
        dest = work / target
        dest.write_text("package httpserver\n// " + comment + "\n", encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="live-object-publisher-") as tmp:
        root = Path(tmp)
        remote, seed = root / "origin.git", root / "seed"
        git(root, "init", "--bare", "-q", str(remote))
        git(root, "init", "-q", "-b", "so", str(seed))
        git(seed, "config", "user.name", "Synthetic Fixture")
        git(seed, "config", "user.email", "fixture@example.invalid")
        original = seed / target
        original.parent.mkdir(parents=True)
        original.write_text("package httpserver\n", encoding="utf-8")
        git(seed, "add", target)
        git(seed, "commit", "-qm", "fixture: initial")
        git(seed, "remote", "add", "origin", str(remote))
        git(seed, "push", "-q", "origin", "HEAD:so")
        initial = git(seed, "rev-parse", "HEAD")

        work = root / "work"
        git(root, "clone", "-q", "-b", "so", str(remote), str(work))
        result = publish(work, initial)
        if result.returncode != 0 or git(work, "rev-parse", "HEAD") != initial:
            raise AssertionError("publisher no-op changed commit or failed")
        if git(root, "--git-dir=" + str(remote), "rev-parse", "refs/heads/so") != initial:
            raise AssertionError("publisher no-op advanced remote")

        mutate(work, "stale candidate")
        mutate(seed, "concurrent publisher")
        git(seed, "add", target)
        git(seed, "commit", "-qm", "fixture: concurrent")
        git(seed, "push", "-q", "origin", "HEAD:so")
        concurrent = git(seed, "rev-parse", "HEAD")
        result = publish(work, initial)
        if result.returncode != 75 or "source is stale" not in result.stderr:
            raise AssertionError("publisher did not reject stale source with exit 75")
        if git(root, "--git-dir=" + str(remote), "rev-parse", "refs/heads/so") != concurrent:
            raise AssertionError("stale publisher overwrote concurrent remote")

        fresh = root / "fresh"
        git(root, "clone", "-q", "-b", "so", str(remote), str(fresh))
        mutate(fresh, "accepted publisher")
        result = publish(fresh, concurrent)
        if result.returncode != 0:
            raise AssertionError("publisher valid commit failed: " + result.stderr[-400:])
        accepted = git(fresh, "rev-parse", "HEAD")
        if accepted == concurrent or git(root, "--git-dir=" + str(remote), "rev-parse", "refs/heads/so") != accepted:
            raise AssertionError("publisher valid commit did not advance remote")

        invalid = root / "invalid"
        git(root, "clone", "-q", "-b", "so", str(remote), str(invalid))
        mutate(invalid, "trailing whitespace  ")
        result = publish(invalid, accepted)
        if result.returncode == 0 or git(invalid, "rev-parse", "HEAD") != accepted:
            raise AssertionError("publisher whitespace pre-commit rejection failed")
        if git(root, "--git-dir=" + str(remote), "rev-parse", "refs/heads/so") != accepted:
            raise AssertionError("invalid publisher changed remote")

        racer, competing = root / "racer", root / "competing"
        git(root, "clone", "-q", "-b", "so", str(remote), str(racer))
        git(root, "clone", "-q", "-b", "so", str(remote), str(competing))
        git(competing, "config", "user.name", "Synthetic Fixture")
        git(competing, "config", "user.email", "fixture@example.invalid")
        mutate(racer, "racing publisher")
        mutate(competing, "concurrent race winner")
        git(competing, "add", target)
        git(competing, "commit", "-qm", "fixture: race winner")
        wrapper = root / "bin"
        wrapper.mkdir()
        shim = wrapper / "git"
        shim.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = \"ls-remote\" ]; then\n"
            "  output=$(" + shlex.quote(real_git) + " \"$@\") || exit $?\n"
            "  " + shlex.quote(real_git) + " -C \"$RACE_WORK\" push -q origin HEAD:so || exit 98\n"
            "  printf '%s\\n' \"$output\"\n"
            "  exit 0\n"
            "fi\n"
            "exec " + shlex.quote(real_git) + " \"$@\"\n",
            encoding="utf-8",
        )
        shim.chmod(0o755)
        result = publish(racer, accepted, {
            "PATH": str(wrapper) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
            "RACE_WORK": str(competing),
        })
        winner = git(competing, "rev-parse", "HEAD")
        if result.returncode == 0 or result.returncode == 75:
            raise AssertionError("publisher post-CAS non-fast-forward race was not rejected")
        if git(root, "--git-dir=" + str(remote), "rev-parse", "refs/heads/so") != winner:
            raise AssertionError("racing publisher overwrote winner")
        if git(racer, "rev-parse", "HEAD") == winner:
            raise AssertionError("race fixture did not create divergent commits")
    print("PASS: live object stage actual publisher no-op, stale CAS, valid push, pre-commit rejection, and post-CAS race (5 cases)")


def reconciler_writer_runtime():
    """Prove actual reconciler symlink refusal, mode preservation and replace rollback."""
    import importlib.util
    import stat

    module_path = ROOT / "scripts/reconcile-memory-os-live-object-stage-diagnostics.py"
    spec = importlib.util.spec_from_file_location("live_object_stage_reconcile_test", module_path)
    if spec is None or spec.loader is None:
        raise AssertionError("live object stage reconciler import failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix="live-object-reconcile-") as tmp:
        root = Path(tmp)
        target = root / "target.go"
        target.write_text("before\\n", encoding="utf-8")
        target.chmod(0o640)
        module.atomic_write_text(target, "after\\n")
        if target.read_text(encoding="utf-8") != "after\\n":
            raise AssertionError("live object stage atomic write did not publish")
        if stat.S_IMODE(target.stat().st_mode) != 0o640:
            raise AssertionError("live object stage atomic write lost file mode")
        previous_replace = module.os.replace
        def fail_replace(source, destination):
            if Path(destination) == target:
                raise OSError("synthetic replace failure")
            return previous_replace(source, destination)
        module.os.replace = fail_replace
        try:
            try:
                module.atomic_write_text(target, "forbidden\\n")
            except OSError as exc:
                if "synthetic replace failure" not in str(exc):
                    raise AssertionError("unexpected atomic replace failure") from exc
            else:
                raise AssertionError("live object stage accepted failed atomic replacement")
        finally:
            module.os.replace = previous_replace
        if target.read_text(encoding="utf-8") != "after\\n":
            raise AssertionError("live object stage failed replacement changed target")
        if list(root.glob(".target.go.*.tmp")):
            raise AssertionError("live object stage atomic temp leaked")
        outside = root / "outside.go"
        outside.write_text("external sentinel\\n", encoding="utf-8")
        link = root / "link.go"
        link.symlink_to(outside)
        previous_path = module.PATH
        module.PATH = link
        try:
            try:
                module.main()
            except RuntimeError as exc:
                if "symlink refused" not in str(exc):
                    raise AssertionError("unexpected target refusal: " + str(exc)) from exc
            else:
                raise AssertionError("live object stage reconciler followed a symlink")
        finally:
            module.PATH = previous_path
        if outside.read_text(encoding="utf-8") != "external sentinel\\n":
            raise AssertionError("live object stage symlink modified external sentinel")
    print("PASS: live object stage actual reconciler symlink refusal, mode preservation, atomic replace rollback and temp cleanup (4 cases)")


def live_object_evidence_validator_runtime():
    """Exercise actual canonical local-evidence validator with disposable negative JSON."""
    import importlib.util
    import json

    module_path = ROOT / "scripts/validate-memory-os-live-object-load.py"
    spec = importlib.util.spec_from_file_location("live_object_evidence_validator", module_path)
    if spec is None or spec.loader is None:
        raise AssertionError("live object evidence validator import failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    contract_text = source("contracts/operations/live-object-load-scenario-contract.v1.json")
    result_text = source("docs/fixtures/memory-os-operability/live-object-load-results.sample.v1.json")
    with tempfile.TemporaryDirectory(prefix="live-object-evidence-negative-") as tmp:
        root = Path(tmp)
        contract_path = root / "contracts/operations/live-object-load-scenario-contract.v1.json"
        result_path = root / "docs/fixtures/memory-os-operability/live-object-load-results.sample.v1.json"
        contract_path.parent.mkdir(parents=True)
        result_path.parent.mkdir(parents=True)
        module.ROOT = root
        module.CONTRACT_PATH = contract_path
        previous_expected = os.environ.pop("EXPECTED_COMMIT_SHA", None)
        try:
            def reset():
                if result_path.is_symlink():
                    result_path.unlink()
                contract_path.write_text(contract_text, encoding="utf-8")
                result_path.write_text(result_text, encoding="utf-8")

            def reject(label, expected):
                try:
                    module.validate()
                except module.ValidationError as exc:
                    if expected not in str(exc):
                        raise AssertionError("live object evidence wrong rejection for " + label + ": " + str(exc)) from exc
                else:
                    raise AssertionError("live object evidence accepted " + label)

            reset()
            module.validate()
            reset()
            result_path.write_text('{"schemaVersion":"synthetic-duplicate",' + result_text.lstrip()[1:], encoding="utf-8")
            reject("duplicate top-level JSON key", "duplicate JSON key")
            reset()
            result_path.write_text(result_text.replace('"productionEvidence": false',
                                '"productionEvidence": true, "productionEvidence": false', 1), encoding="utf-8")
            reject("duplicate nested JSON key", "duplicate JSON key")
            reset()
            contract = json.loads(contract_text)
            contract["resultPath"] = "../../outside.json"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            reject("result path traversal", "resultPath authority drift")
            reset()
            outside = root / "outside.json"
            outside.write_text(result_text, encoding="utf-8")
            result_path.unlink()
            result_path.symlink_to(outside)
            reject("symlink evidence", "symlink")
            if outside.read_text(encoding="utf-8") != result_text:
                raise AssertionError("live object symlink modified outside sentinel")
            reset()
            document = json.loads(result_text)
            document["scenarios"][0]["batch"]["statusClassCounts"]["transport_error_credential"] = 0
            result_path.write_text(json.dumps(document), encoding="utf-8")
            reject("unbounded status label", "invalid status class")
            reset()
            document = json.loads(result_text)
            document["environment"]["productionEvidence"] = True
            result_path.write_text(json.dumps(document), encoding="utf-8")
            reject("false production evidence", "ephemeral MinIO results cannot claim production evidence")
            reset()
            contract = json.loads(contract_text)
            contract["readiness"]["productionTLS"] = True
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            reject("false production TLS readiness", "productionTLS cannot be true")
        finally:
            if previous_expected is not None:
                os.environ["EXPECTED_COMMIT_SHA"] = previous_expected
    print("PASS: live object evidence actual validator baseline and seven duplicate/path/symlink/privacy/readiness negatives")


def main():
    publisher, independent = source(PUBLISHER), source(INDEPENDENT)
    if blob(publisher) != REVIEWED_PUBLISHER or blob(independent) != REVIEWED_INDEPENDENT:
        raise SystemExit("live object stage complete source blob drift")
    for marker in (PUBLISHER, INDEPENDENT, SELF, CHECKOUT, SETUP_PY, SETUP_GO,
                   "scripts/reconcile-memory-os-live-object-stage-diagnostics.py",
                   "scripts/validate-memory-os-live-object-load.py",
                   "contracts/operations/live-object-load-scenario-contract.v1.json",
                   "services/import-api/internal/httpserver/live_object_load_test.go",
                   "TestLiveObjectStageLabelClosedVocabulary",
                   "persist-credentials: false", "contents: read",
                   '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'):
        if marker not in independent:
            raise AssertionError("live object stage independent source/reachability drift: " + marker)
    go_source = source("services/import-api/internal/httpserver/live_object_load_test.go")
    reconciler_source = source("scripts/reconcile-memory-os-live-object-stage-diagnostics.py")
    for marker in ("func liveObjectStageLabel(err error) string {",
                   "case \"issue\", \"issue_read\", \"issue_close\", \"issue_decode\", \"issue_contract\", \"put\", \"put_read\", \"put_close\", \"complete\", \"complete_read\", \"complete_close\":",
                   "stage := liveObjectStageLabel(sample.Err)",
                   "func TestLiveObjectStageLabelClosedVocabulary(t *testing.T) {"):
        if marker not in go_source:
            raise AssertionError("live object stage closed vocabulary source drift: " + marker)
    if 'stage = prefix' in go_source or '"transport_error_"+stage' not in go_source:
        raise AssertionError("live object stage unbounded stage label regression")
    if "closed stage labels" not in reconciler_source or "bounded stage accounting" not in reconciler_source:
        raise AssertionError("live object stage reconciler label policy drift")
    evidence_validator = source("scripts/validate-memory-os-live-object-load.py")
    for marker in ("object_pairs_hook=reject_duplicate_json_keys", "resultPath authority drift", "path.is_symlink()"):
        if marker not in evidence_validator:
            raise AssertionError("live object evidence validator authority drift: " + marker)
    for marker in ("def validate_target()", "PATH.is_symlink()", "def atomic_write_text(", "os.replace(temp_name, path)", "validate_target()"):
        if marker not in reconciler_source:
            raise AssertionError("live object stage reconciler write safety drift: " + marker)
    policy(publisher)
    negatives(publisher)
    runtime(publisher, "Validate diagnostic source read-only", False)
    runtime(publisher, "Reconcile stage diagnostics", True)
    publisher_runtime(publisher)
    reconciler_writer_runtime()
    live_object_evidence_validator_runtime()
    print("PASS: live object stage read-only source proof; production evidence generated: false; production decision changed: false")

if __name__ == "__main__":
    main()
