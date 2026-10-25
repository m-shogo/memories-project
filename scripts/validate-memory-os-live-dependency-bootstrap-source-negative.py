#!/usr/bin/env python3
"""Read-only exact-source and synthetic Docker bootstrap failure proof for live dependencies."""
from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ".github/workflows/regenerate-live-postgres-load-results.yml"
UPLOAD = ".github/workflows/reconcile-upload-route-authority.yml"
SIGKILL = ".github/workflows/deletion-worker-sigkill-recovery.yml"
INDEPENDENT = ".github/workflows/live-dependency-bootstrap-source-negative.yml"
SELF = "scripts/validate-memory-os-live-dependency-bootstrap-source-negative.py"
REVIEWED_LIVE = "fd501a86a6e2f3ed3cb68c29d0d9ffb39162dc57"
REVIEWED_UPLOAD = "3997403c3d93983470942909a8673aa961fc099a"
REVIEWED_SIGKILL = "564f8dae50222dc9025ee31449c116d7f3b8345d"
REVIEWED_INDEPENDENT = "ff92e4a807def62fefe1ad2df90f16fd9ba23aee"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
PR_BASE = 'test "${GITHUB_BASE_REF:-}" = "so"'
PUSH_REF = 'test "${GITHUB_REF:-}" = "refs/heads/so"'
SHA_FORMAT = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'


def source(relative: str) -> str:
    path = ROOT / relative
    try:
        if path.is_symlink() or not path.is_file():
            raise ValueError("not regular")
        if path.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != relative:
            raise ValueError("escaped root")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        raise SystemExit("live dependency source missing/substituted: " + relative) from exc


def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def step_script(workflow: str, title: str) -> str:
    marker = "      - name: " + title + "\n        run: |\n"
    if workflow.count(marker) != 1:
        raise SystemExit("live dependency bootstrap step missing/ambiguous: " + title)
    start = workflow.index(marker) + len(marker)
    end = workflow.find("\n      - name:", start)
    if end < 0:
        raise SystemExit("live dependency bootstrap step has no following boundary")
    lines = workflow[start:end].splitlines()
    if not lines or any(line and not line.startswith("          ") for line in lines):
        raise SystemExit("live dependency bootstrap indentation drift")
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"


def validate(live: str, upload: str, sigkill: str, independent: str) -> None:
    live_required = (
        "      - name: Start local MinIO harness\n",
        "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch' || github.event_name == 'schedule') && github.ref == 'refs/heads/so'",
        "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "uses: actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5",
        "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "persist-credentials: true",
        'test "${GITHUB_REF:-}" = "refs/heads/so"',
        '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
        'test "$(git rev-parse HEAD)" = "${GITHUB_SHA:-}"',
        "          set -euo pipefail\n",
        "quay.io/minio/minio server /data",
        "      - name: Publish exact-source result documents\n        if: env.PUBLISH_RESULTS == 'true'",
        "      - name: Reconcile published evidence into current status\n        if: env.PUBLISH_RESULTS == 'true'",
        "      - name: Restore committed evidence after unchanged scheduled verification\n        if: env.PUBLISH_RESULTS == 'false'",
        'git diff --quiet "${SOURCE_SHA}"',
        "git reset --hard origin/so",
    )
    upload_required = (
        "      - name: Start local MinIO\n",
        "quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z server /data",
        "      - name: Confirm exact clean source\n",
        "      - name: Validate reconcile rollback boundary\n",
        "      - name: Commit reconciled route authority\n",
        'test "$(git rev-parse origin/so)" = "$SOURCE_SHA"',
    )
    sigkill_required = (
        "      - name: Start local MinIO\n",
        "minio/minio server /data",
        "      - name: Execute exact-source SIGKILL proof\n",
        "      - name: Commit exact-source result\n",
        "      - name: Reconcile local-only authority\n",
        "      - name: Record privacy-safe failure diagnostic\n",
        'if [[ "$(git rev-parse origin/so)" != "$SOURCE_SHA" ]]',
    )
    independent_required = (
        "  pull_request:\n    branches:\n      - so\n",
        "  push:\n    branches:\n      - so\n",
        '      - "' + LIVE + '"', '      - "' + UPLOAD + '"',
        '      - "' + SIGKILL + '"', '      - "' + INDEPENDENT + '"', '      - "' + SELF + '"',
        '      - "scripts/validate-memory-os-live-load.py"',
        '      - "contracts/operations/live-postgres-load-scenario-contract.v1.json"',
        CHECKOUT, SETUP, "          persist-credentials: false\n",
        PR_BASE, PUSH_REF, SHA_FORMAT, "          python " + SELF,
        "permissions:\n  contents: read\n",
        "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')",
        'test "$(git rev-parse HEAD)" = "$expected"',
        'test -z "$(git status --porcelain)"',
    )
    for label, text, required, digest in (
        ("live", live, live_required, REVIEWED_LIVE),
        ("upload", upload, upload_required, REVIEWED_UPLOAD),
        ("sigkill", sigkill, sigkill_required, REVIEWED_SIGKILL),
        ("independent", independent, independent_required, REVIEWED_INDEPENDENT),
    ):
        for token in required:
            if token not in text:
                raise SystemExit("live dependency " + label + " source drift: " + token)
        if blob(text) != digest:
            raise SystemExit("live dependency " + label + " complete Git blob drift")
    evidence_validator = source("scripts/validate-memory-os-live-load.py")
    for marker in ("object_pairs_hook=reject_duplicate_json_keys", "resultPath authority drift", "path.is_symlink()"):
        if marker not in evidence_validator:
            raise SystemExit("live PostgreSQL evidence validator authority drift: " + marker)
    if live.index("      - name: Start local MinIO harness") > live.index("      - name: Publish exact-source result documents"):
        raise SystemExit("live load publication may precede dependency startup")
    if upload.index("      - name: Start local MinIO") > upload.index("      - name: Commit reconciled route authority"):
        raise SystemExit("upload route authority publication may precede dependency startup")
    if sigkill.index("      - name: Start local MinIO") > sigkill.index("      - name: Commit exact-source result"):
        raise SystemExit("SIGKILL publication may precede dependency startup")
    for label, workflow, title in (("live", live, "Start local MinIO harness"), ("upload", upload, "Start local MinIO"), ("sigkill", sigkill, "Start local MinIO")):
        script = step_script(workflow, title)
        if "docker run -d" not in script or "continue-on-error: true" in workflow:
            raise SystemExit("live dependency " + label + " bootstrap fail-closed drift")


def synthetic_bootstrap_failure(live: str, upload: str, sigkill: str) -> None:
    if sigkill.index("      - name: Start local MinIO") > sigkill.index("      - name: Commit exact-source result"):
        raise SystemExit("SIGKILL publication may precede dependency startup")
    for label, workflow, title in (("live", live, "Start local MinIO harness"), ("upload", upload, "Start local MinIO"), ("sigkill", sigkill, "Start local MinIO")):
        code = step_script(workflow, title)
        with tempfile.TemporaryDirectory(prefix="live-dependency-bootstrap-") as tmp:
            root = Path(tmp)
            bindir = root / "bin"
            bindir.mkdir()
            docker = bindir / "docker"
            docker.write_text('#!/bin/sh\nprintf "docker" > "$DOCKER_MARKER"\nexit 125\n', encoding="utf-8")
            docker.chmod(0o755)
            curl = bindir / "curl"
            curl.write_text('#!/bin/sh\nprintf "curl" > "$CURL_MARKER"\nexit 0\n', encoding="utf-8")
            curl.chmod(0o755)
            docker_marker = root / "docker.marker"
            curl_marker = root / "curl.marker"
            env = dict(os.environ, PATH=str(bindir) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       DOCKER_MARKER=str(docker_marker), CURL_MARKER=str(curl_marker))
            result = subprocess.run(["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", code],
                                    cwd=root, env=env, capture_output=True, text=True,
                                    timeout=10, check=False)
            if result.returncode != 125 or not docker_marker.is_file() or curl_marker.exists():
                raise SystemExit("live dependency " + label + " accepted synthetic image pull denial")
            if list(root.rglob("*.json")):
                raise SystemExit("live dependency " + label + " generated evidence on bootstrap failure")
    print("PASS: live PostgreSQL/object, upload-route and deletion SIGKILL MinIO bootstrap denial exits 125 before publication (3 cases)")



def live_source_identity_runtime(live: str) -> None:
    """Execute the actual live dependency writer event/ref/SHA shell before bootstrap."""
    code = step_script(live, "Capture exact source and previous evidence state")
    if 'source_sha="$(git rev-parse HEAD)"' not in code:
        raise SystemExit("live dependency source identity shell drift")
    code = code.split('source_sha="$(git rev-parse HEAD)"', 1)[0]
    head = "a" * 40
    cases = (
        ("push", "refs/heads/so", head, head, True),
        ("workflow_dispatch", "refs/heads/so", head, head, True),
        ("schedule", "refs/heads/so", head, head, True),
        ("pull_request", "refs/heads/so", head, head, False),
        ("push", "refs/heads/main", head, head, False),
        ("push", "refs/tags/v1", head, head, False),
        ("push", "refs/heads/so", "A" * 40, head, False),
        ("push", "refs/heads/so", "a" * 39, head, False),
        ("push", "refs/heads/so", "b" * 40, head, False),
        ("workflow_dispatch", "", head, head, False),
    )
    with tempfile.TemporaryDirectory(prefix="live-dependency-source-") as tmp:
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
        for event, ref, sha, stub_head, accepted in cases:
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_EVENT_NAME=event, GITHUB_REF=ref, GITHUB_SHA=sha,
                       STUB_HEAD=stub_head)
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", code],
                                    cwd=root, env=env, capture_output=True, text=True,
                                    timeout=10, check=False)
            if (result.returncode == 0) != accepted:
                raise SystemExit("live dependency writer source identity runtime drift: " + event + "/" + ref)
    print("PASS: live dependency actual writer event/ref/SHA shell (10 cases)")

def predicate_runtime(independent: str) -> None:
    for command in (PR_BASE, PUSH_REF, SHA_FORMAT):
        if independent.count(command) != 1:
            raise SystemExit("live dependency independent runtime predicate drift")
    for cmd, key, val, allow in (
        (PR_BASE, "GITHUB_BASE_REF", "so", True),
        (PR_BASE, "GITHUB_BASE_REF", "main", False),
        (PR_BASE, "GITHUB_BASE_REF", "", False),
        (PUSH_REF, "GITHUB_REF", "refs/heads/so", True),
        (PUSH_REF, "GITHUB_REF", "refs/heads/main", False),
        (PUSH_REF, "GITHUB_REF", "refs/tags/v1", False),
    ):
        r = subprocess.run(["bash", "-e", "-c", cmd],
                           env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: val},
                           capture_output=True, check=False)
        if (r.returncode == 0) != allow:
            raise SystemExit("live dependency independent branch/base runtime drift")
    for val, allow in (("a" * 40, True), ("0" * 40, True), ("a" * 39, False),
                       ("A" * 40, False), ("g" * 40, False), ("", False)):
        r = subprocess.run(["bash", "-e", "-c", SHA_FORMAT],
                           env=dict(os.environ, expected=val), capture_output=True, check=False)
        if (r.returncode == 0) != allow:
            raise SystemExit("live dependency independent SHA runtime drift")
    print("PASS: live dependency independent branch/base (6) and SHA (6) runtime cases")


def source_negatives(live: str, upload: str, sigkill: str, independent: str) -> None:
    live_cases = (
        ("bootstrap shell", "          set -euo pipefail\n", "          set +e\n"),
        ("image", "quay.io/minio/minio server /data", "quay.io/minio/minio:latest server /data"),
        ("ignore docker", "          docker run -d --name memory-os-live-load-minio", "          docker run -d --name memory-os-live-load-minio || true"),
        ("publish gate", "if: env.PUBLISH_RESULTS == 'true'", "if: always()"),
        ("source guard", 'git diff --quiet "${SOURCE_SHA}"', "true"),
        ("retry", "git reset --hard origin/so", "true"),
        ("checkout SHA", "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262", "uses: actions/checkout@v4"),
        ("setup Go SHA", "uses: actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5", "uses: actions/setup-go@v5"),
        ("setup Python SHA", "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", "uses: actions/setup-python@v5"),
        ("writer event scope", "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch' || github.event_name == 'schedule') && github.ref == 'refs/heads/so'", "    if: always()"),
        ("writer ref", "test \"${GITHUB_REF:-}\" = \"refs/heads/so\"", "true"),
        ("writer SHA", "[[ \"${GITHUB_SHA:-}\" =~ ^[0-9a-f]{40}$ ]]", "test -n \"${GITHUB_SHA:-}\""),
        ("writer HEAD", "test \"$(git rev-parse HEAD)\" = \"${GITHUB_SHA:-}\"", "true"),
        ("writer credentials", "persist-credentials: true", "persist-credentials: false"),
    )
    upload_cases = (
        ("image", "quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z server /data", "quay.io/minio/minio:latest server /data"),
        ("ignore docker", "          docker run -d --name memory-os-upload-route-minio", "          docker run -d --name memory-os-upload-route-minio || true"),
        ("source identity", 'test "$(git rev-parse origin/so)" = "$SOURCE_SHA"', "true"),
        ("bootstrap", "      - name: Start local MinIO\n", "      - name: Disabled MinIO\n"),
        ("publication", "      - name: Commit reconciled route authority\n", "      - name: Unsafe commit\n"),
        ("rollback", "      - name: Validate reconcile rollback boundary\n", "      - name: Skip rollback\n"),
    )
    sigkill_cases = (
        ("image", "minio/minio server /data", "minio/minio:latest server /data"),
        ("ignore docker", "          docker run -d --name memory-os-deletion-sigkill-minio", "          docker run -d --name memory-os-deletion-sigkill-minio || true"),
        ("bootstrap", "      - name: Start local MinIO\n", "      - name: Disabled MinIO\n"),
        ("publication", "      - name: Commit exact-source result\n", "      - name: Unsafe commit\n"),
    )
    independent_cases = (
        ("PR base", PR_BASE, "true"), ("push branch", PUSH_REF, "true"),
        ("SHA format", SHA_FORMAT, 'test -n "$expected"'),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("self trigger", '      - "' + SELF + '"', ""),
        ("live trigger", '      - "' + LIVE + '"', ""),
        ("upload trigger", '      - "' + UPLOAD + '"', ""),
        ("SIGKILL trigger", '      - "' + SIGKILL + '"', ""),
        ("root write", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
    )
    for label, original, cases in (("live", live, live_cases), ("upload", upload, upload_cases), ("sigkill", sigkill, sigkill_cases), ("independent", independent, independent_cases)):
        for name, old, new in cases:
            if old not in original:
                raise SystemExit("live dependency negative fixture missing: " + label + "/" + name)
            altered = original.replace(old, new, 1)
            if altered == original:
                raise SystemExit("live dependency negative fixture unchanged: " + label + "/" + name)
            try:
                if label == "live":
                    validate(altered, upload, sigkill, independent)
                elif label == "upload":
                    validate(live, altered, sigkill, independent)
                elif label == "sigkill":
                    validate(live, upload, altered, independent)
                else:
                    validate(live, upload, sigkill, altered)
            except SystemExit:
                continue
            raise SystemExit("live dependency accepted mutation: " + label + "/" + name)
    print("PASS: live dependency source negatives (14 live + 6 upload + 4 SIGKILL + 11 independent)")



def postgres_evidence_validator_runtime() -> None:
    """Prove the canonical local PostgreSQL evidence validator rejects ambiguous JSON."""
    import importlib.util
    import json

    module_path = ROOT / "scripts/validate-memory-os-live-load.py"
    spec = importlib.util.spec_from_file_location("live_postgres_evidence_validator", module_path)
    if spec is None or spec.loader is None:
        raise SystemExit("live PostgreSQL evidence validator import failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    contract_text = source("contracts/operations/live-postgres-load-scenario-contract.v1.json")
    result_text = source("docs/fixtures/memory-os-operability/live-postgres-load-results.sample.v1.json")
    with tempfile.TemporaryDirectory(prefix="live-postgres-evidence-negative-") as tmp:
        root = Path(tmp)
        contract_path = root / "contracts/operations/live-postgres-load-scenario-contract.v1.json"
        result_path = root / "docs/fixtures/memory-os-operability/live-postgres-load-results.sample.v1.json"
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
                        raise SystemExit("live PostgreSQL wrong rejection for " + label + ": " + str(exc)) from exc
                else:
                    raise SystemExit("live PostgreSQL accepted " + label)

            reset()
            module.validate()
            reset()
            result_path.write_text('{"schemaVersion":"synthetic-duplicate",' + result_text.lstrip()[1:], encoding="utf-8")
            reject("duplicate top-level JSON", "duplicate JSON key")
            reset()
            result_path.write_text(result_text.replace('"productionEvidence": false',
                                '"productionEvidence": true, "productionEvidence": false', 1), encoding="utf-8")
            reject("duplicate nested JSON", "duplicate JSON key")
            reset()
            contract = json.loads(contract_text)
            contract["resultPath"] = "../../outside.json"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            reject("path traversal", "resultPath authority drift")
            reset()
            outside = root / "outside.json"
            outside.write_text(result_text, encoding="utf-8")
            result_path.unlink()
            result_path.symlink_to(outside)
            reject("symlink evidence", "symlink")
            if outside.read_text(encoding="utf-8") != result_text:
                raise SystemExit("live PostgreSQL symlink changed external sentinel")
            reset()
            document = json.loads(result_text)
            document["scenarios"][0]["batch"]["statusClassCounts"]["transport_error_credential"] = 0
            result_path.write_text(json.dumps(document), encoding="utf-8")
            reject("unbounded status label", "invalid status class")
            reset()
            document = json.loads(result_text)
            document["environment"]["productionEvidence"] = True
            result_path.write_text(json.dumps(document), encoding="utf-8")
            reject("false production evidence", "ephemeral live-load results must not claim production evidence")
            reset()
            contract = json.loads(contract_text)
            contract["readiness"]["capacityBoundaryEstablished"] = True
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            reject("false capacity readiness", "capacityBoundaryEstablished cannot be true")
        finally:
            if previous_expected is not None:
                os.environ["EXPECTED_COMMIT_SHA"] = previous_expected
    print("PASS: live PostgreSQL actual evidence validator baseline and seven duplicate/path/symlink/privacy/readiness negatives")


def main() -> int:
    live, upload, sigkill, independent = source(LIVE), source(UPLOAD), source(SIGKILL), source(INDEPENDENT)
    validate(live, upload, sigkill, independent)
    predicate_runtime(independent)
    source_negatives(live, upload, sigkill, independent)
    synthetic_bootstrap_failure(live, upload, sigkill)
    live_source_identity_runtime(live)
    postgres_evidence_validator_runtime()
    print("capacity evidence generated: false")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
