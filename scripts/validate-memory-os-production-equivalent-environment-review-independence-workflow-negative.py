#!/usr/bin/env python3
"""Fail-closed executable-source and event/ref negatives for review independence CI."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/production-equivalent-environment-review-independence.yml"
REVIEWED_WORKFLOW_GIT_BLOB_SHA = "56d15ffd78c816ccecd0ff27c9e159f78c913bf4"

TRIGGER_PATHS = (
    ".github/workflows/production-equivalent-environment-review-independence.yml",
    "scripts/validate-memory-os-production-equivalent-environment-review-independence-workflow-negative.py",
    "contracts/operations/production-equivalent-environment-review-independence-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/production-operability-status.json",
    "contracts/operations/production-equivalent-environment-record.v1.schema.json",
    "contracts/operations/production-equivalent-environment-generation-record.v1.schema.json",
    "scripts/register-memory-os-production-equivalent-environment-generation.py",
    "scripts/validate-memory-os-production-equivalent-environment-record.py",
    "scripts/memory_os_environment_generation_eligibility.py",
    "scripts/validate-memory-os-production-equivalent-environment-review-independence.py",
    "scripts/validate-memory-os-production-equivalent-environment-review-independence-negative.py",
    "scripts/validate-memory-os-production-equivalent-environment-review-independence-reconcile-negative.py",
    "scripts/reconcile-memory-os-production-equivalent-environment-review-independence.py",
    "scripts/validate-memory-os-operability.py",
)
REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("self trigger", '      - "scripts/validate-memory-os-production-equivalent-environment-review-independence-workflow-negative.py"\n', 2),
    ("checkout SHA", "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262", 2),
    ("setup SHA", "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", 2),
    ("PR no credentials", "          persist-credentials: false\n", 1),
    ("publisher credentials", "          persist-credentials: true\n", 1),
    ("PR base", '          test "${GITHUB_BASE_REF:-}" = "so"\n', 1),
    ("PR SHA format", '          [[ "$expected" =~ ^[0-9a-f]{40}$ ]]\n', 2),
    ("publisher branch", '          test "${GITHUB_REF:-}" = "refs/heads/so"\n', 1),
    ("publisher event", '          [[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]\n', 1),
    ("publisher scope", "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n", 1),
    ("self execution", "\n          python scripts/validate-memory-os-production-equivalent-environment-review-independence-workflow-negative.py\n", 2),
    ("retry self execution", "            python scripts/validate-memory-os-production-equivalent-environment-review-independence-workflow-negative.py\n", 1),
    ("writer SHA", '          expected="${GITHUB_SHA:-}"\n', 1),
    ("PR SHA", '          expected="${{ github.event.pull_request.head.sha }}"\n', 1),
    ("HEAD check", '          test "$(git rev-parse HEAD)" = "$expected"\n', 2),
    ("write scope", "      contents: write\n", 1),
    ("retry latest", "            git reset --hard origin/so\n", 1),
    ("redacted diagnostic", "              'output': 'REDACTED: environment review-independence validation failed; raw output withheld',\n", 1),
    ("suppressed CI log", '          printf "Environment review-independence validation exit code: %s (raw validator log suppressed)\\n" "$code"\n', 1),
    ("no raw diagnostic tail", "text[-12000:]", 0),
    ("no raw CI log", '          cat "$log"\n', 0),
)



def validate_trigger_reachability(
    source: str, *, trigger_paths: tuple[str, ...] = TRIGGER_PATHS
) -> None:
    """Pin the complete reviewed PR/push independent-review trigger inventory."""
    if len(trigger_paths) != 16 or len(set(trigger_paths)) != 16:
        raise SystemExit("review independence CI trigger inventory shortened or duplicated")
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    dispatch_marker = "  workflow_dispatch:\n"
    for marker in (pr_marker, push_marker, dispatch_marker):
        if source.count(marker) != 1:
            raise SystemExit("review independence CI event marker drift")
    pr = source.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push = source.split(push_marker, 1)[1].split(dispatch_marker, 1)[0]
    approved = tuple('      - "' + path + '"' for path in trigger_paths)
    for event, block in (("pull_request", pr), ("push", push)):
        actual = tuple(
            line for line in block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        if actual != approved:
            raise SystemExit("review independence CI " + event + " exact trigger inventory drift")


def validate_yaml_authority(source: str) -> None:
    """Bind reviewed YAML event, root and read-only permission semantics independently of blob SHA."""
    expected_header = (
        "name: Production Equivalent Environment Review Independence\n\non:\n"
        + "  pull_request:\n    branches:\n      - so\n    paths:\n"
        + "".join('      - "' + path + '"\n' for path in TRIGGER_PATHS)
        + "  push:\n    branches:\n      - so\n    paths:\n"
        + "".join('      - "' + path + '"\n' for path in TRIGGER_PATHS)
        + "  workflow_dispatch:\n"
    )
    if (source.count("\npermissions:\n") != 1
            or source.split("\npermissions:\n", 1)[0] != expected_header):
        raise SystemExit("review independence CI exact event header drift")
    roots = [
        line for line in source.splitlines()
        if line.strip() and not line[0].isspace()
        and not line.lstrip().startswith("#")
    ]
    if roots != [
        "name: Production Equivalent Environment Review Independence",
        "on:", "permissions:", "concurrency:", "jobs:",
    ]:
        raise SystemExit("review independence CI root YAML key shadow drift")
    permission_rows = []
    for line in source.split("\npermissions:\n", 1)[1].splitlines():
        if line.strip() and not line[0].isspace():
            break
        if line.strip() and not line.lstrip().startswith("#"):
            permission_rows.append(line)
    if permission_rows != ["  contents: read"]:
        raise SystemExit("review independence CI permission leaf shadow drift")
    body = source.split("\n" + "jobs:\n", 1)[1]
    job_headers = [
        row for row in body.splitlines()
        if row.startswith("  ") and not row.startswith("   ")
        and row.strip() and not row.lstrip().startswith("#")
    ]
    if job_headers != ["  validate-pr:", "  validate-and-publish:"]:
        raise SystemExit("review independence CI job mapping shadow drift")
    pr = body.split("  validate-pr:\n", 1)[1].split("  validate-and-publish:\n", 1)[0]
    publisher = body.split("  validate-and-publish:\n", 1)[1]
    for section, expected_if, expected_scope in (
        (pr, "    if: github.event_name == 'pull_request'", "read"),
        (publisher, "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'", "write"),
    ):
        keys = [
            row for row in section.splitlines()
            if row.startswith("    ") and not row.startswith("     ")
            and row.strip() and not row.lstrip().startswith("#")
        ]
        if keys != [
            expected_if, "    permissions:", "    runs-on: ubuntu-latest",
            "    timeout-minutes: 8", "    steps:",
        ]:
            raise SystemExit("review independence CI job key/permission shadow drift")
        marker = "    permissions:\n"
        if (section.count(marker) != 1
                or section.split(marker, 1)[1].split("    runs-on: ubuntu-latest\n", 1)[0]
                != "      contents: " + expected_scope + "\n"):
            raise SystemExit("review independence CI job permission scope drift")


def prove_yaml_authority_negatives(source: str) -> None:
    """Check intended semantic diagnostics for each bypass, not only a blob mismatch."""
    validate_yaml_authority(source)
    event = source.replace("on:\n", "on:\n  issues:\n", 1)
    if event == source:
        raise SystemExit("review independence CI YAML event mutation anchor drift")
    cases = [("extra event", event, "exact event header drift")]
    for label, suffix in (
        ("spaced on", "on :\n  issues:\n"),
        ("quoted on", "'on':\n  issues:\n"),
        ("spaced permissions", "permissions :\n  contents: write\n"),
        ("quoted permissions", "'permissions':\n  contents: write\n"),
        ("spaced jobs", "jobs : {}\n"),
        ("quoted jobs", "'jobs': {}\n"),
    ):
        cases.append((label, source.rstrip("\n") + "\n" + suffix,
                      "root YAML key shadow drift"))
    marker = "\npermissions:\n  contents: read\n"
    if source.count(marker) != 1:
        raise SystemExit("review independence CI permission mutation anchor drift")
    for label, leaf in (
        ("spaced contents", "  contents : write\n"),
        ("quoted contents", "  'contents': write\n"),
    ):
        cases.append((label, source.replace(marker, marker + leaf, 1),
                      "permission leaf shadow drift"))
    for job in ("validate-pr", "validate-and-publish"):
        for label, suffix in (
            ("duplicate job", "  " + job + ": {}\n"),
            ("spaced job", "  " + job + " : {}\n"),
            ("quoted job", "  '" + job + "': {}\n"),
        ):
            cases.append((job + " " + label, source.rstrip("\n") + "\n" + suffix,
                          "job mapping shadow drift"))
        job_anchor = "  " + job + ":\n"
        if source.count(job_anchor) != 1:
            raise SystemExit("review independence CI job fixture anchor drift: " + job)
        prefix, section = source.split(job_anchor, 1)
        runs_on = "    runs-on: ubuntu-latest\n"
        if runs_on not in section:
            raise SystemExit("review independence CI job runs-on fixture anchor drift: " + job)
        for label, leaf in (
            ("job permission", "    permissions:\n      contents: write\n"),
            ("spaced job permission", "    permissions :\n      contents: write\n"),
            ("quoted job permission", "    'permissions':\n      contents: write\n"),
        ):
            cases.append((job + " " + label,
                          prefix + job_anchor + section.replace(runs_on, runs_on + leaf, 1),
                          "job key/permission shadow drift"))
    for label, anchor, replacement in (
        ("PR scope escalation",
         "  validate-pr:\n    if: github.event_name == 'pull_request'\n    permissions:\n      contents: read\n",
         "  validate-pr:\n    if: github.event_name == 'pull_request'\n    permissions:\n      contents: write\n"),
        ("publisher scope removal",
         "  validate-and-publish:\n    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n    permissions:\n      contents: write\n",
         "  validate-and-publish:\n    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n    permissions:\n      contents: read\n"),
    ):
        if source.count(anchor) != 1:
            raise SystemExit("review independence CI scoped permission fixture anchor drift: " + label)
        cases.append((label, source.replace(anchor, replacement, 1),
                      "job permission scope drift"))
    for job, scope in (("validate-pr", "read"), ("validate-and-publish", "write")):
        marker = "    permissions:\n      contents: " + scope + "\n"
        prefix, section = source.split("  " + job + ":\n", 1)
        if section.count(marker) < 1:
            raise SystemExit("review independence CI job permission leaf fixture anchor drift: " + job)
        for label, leaf in (
            ("spaced contents", "      contents : write\n"),
            ("quoted contents", "      'contents': write\n"),
        ):
            cases.append((job + " " + label,
                          prefix + "  " + job + ":\n" + section.replace(marker, marker + leaf, 1),
                          "job permission scope drift"))
    for label, anchor in (
        ("PR event bypass", "    if: github.event_name == 'pull_request'\n"),
        ("publisher event bypass", "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n"),
    ):
        if source.count(anchor) != 1:
            raise SystemExit("review independence CI job event fixture anchor drift: " + label)
        cases.append((label, source.replace(anchor, "    if: true\n", 1),
                      "job key/permission shadow drift"))
    if len(cases) != 29:
        raise SystemExit("review independence CI YAML negative inventory drift")
    for label, mutated, diagnostic in cases:
        if mutated == source:
            raise SystemExit("review independence CI unchanged YAML mutation: " + label)
        try:
            validate_yaml_authority(mutated)
        except SystemExit as exc:
            expected = "review independence CI " + diagnostic
            if str(exc) != expected:
                raise SystemExit("review independence CI wrong YAML diagnostic: "
                                 + label + ": " + str(exc)) from exc
        else:
            raise SystemExit("review independence CI accepted YAML mutation: " + label)
    print("PASS: review independence CI YAML event/root/job/permission authority (29 exact-diagnostic negatives)")


def prove_trigger_reachability_negatives(source: str) -> None:
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    for event in ("pull_request", "push"):
        for path in TRIGGER_PATHS:
            token = '      - "' + path + '"\n'
            if source.count(token) != 2:
                raise SystemExit("review independence CI mutation anchor drift: " + path)
            if event == "pull_request":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(push_marker, 1)
                mutated = prefix + push_marker + suffix.replace(token, "", 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("review independence CI accepted missing " + event + " trigger: " + path)
        marker = pr_marker if event == "pull_request" else push_marker
        for label, injected in (
            ("quoted extra", '      - "unreviewed/**"\n'),
            ("quoted duplicate", '      - "' + TRIGGER_PATHS[0] + '"\n'),
            ("unquoted extra", "      - unreviewed/**\n"),
            ("unquoted duplicate", "      - " + TRIGGER_PATHS[0] + "\n"),
        ):
            if source.count(marker) != 1:
                raise SystemExit("review independence CI addition marker drift: " + event)
            mutated = source.replace(marker, marker + injected, 1)
            if mutated == source:
                raise SystemExit("review independence CI addition fixture unchanged")
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("review independence CI accepted " + event + " addition: " + label)
    try:
        validate_trigger_reachability(source, trigger_paths=TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("review independence CI shortened trigger inventory accepted")
    print("PASS: review independence CI event-specific triggers (32 removals; 8 additions; 1 shortened inventory negative)")



def validate_concurrency_authority(source: str) -> None:
    """Pin independent-review publisher noncancellation independently of blob SHA."""
    marker = "\nconcurrency:\n"
    end = "\njobs:\n"
    expected = (
        "  group: production-equivalent-environment-review-independence-" + chr(36)
        + "{{ github.event.pull_request.number || 'so' }}\n"
        + "  cancel-in-progress: false\n"
    )
    if (source.count(marker) != 1 or source.count(end) != 1
            or source.split(marker, 1)[1].split(end, 1)[0] != expected):
        raise SystemExit("review independence CI concurrency scope drift")


def prove_concurrency_authority_negatives(source: str) -> None:
    """Require the intended diagnostic for ten group/cancellation regressions."""
    validate_concurrency_authority(source)
    original = (
        "  group: production-equivalent-environment-review-independence-" + chr(36)
        + "{{ github.event.pull_request.number || 'so' }}\n"
        + "  cancel-in-progress: false\n"
    )
    cases = (
        ("global group", "  group: production-equivalent-environment-review-independence-global\n"
         "  cancel-in-progress: false\n"),
        ("cancellation enabled", original.replace("false", "true")),
        ("duplicate group", original + "  group: unreviewed-global\n"),
        ("duplicate cancellation", original + "  cancel-in-progress: true\n"),
        ("spaced group", original + "  group : unreviewed-global\n"),
        ("quoted group", original + "  'group': unreviewed-global\n"),
        ("spaced cancellation", original + "  cancel-in-progress : true\n"),
        ("quoted cancellation", original + "  'cancel-in-progress': true\n"),
        ("unreviewed leaf", original + "  max-parallel: 100\n"),
        ("removed cancellation", original.replace("  cancel-in-progress: false\n", "")),
    )
    if source.count(original) != 1:
        raise SystemExit("review independence CI concurrency fixture anchor drift")
    for name, replacement in cases:
        changed = source.replace(original, replacement, 1)
        if changed == source:
            raise SystemExit("review independence CI unchanged concurrency fixture: " + name)
        try:
            validate_concurrency_authority(changed)
        except SystemExit as exc:
            if str(exc) != "review independence CI concurrency scope drift":
                raise SystemExit(
                    "review independence CI wrong concurrency diagnostic: " + name + ": " + str(exc)
                ) from exc
        else:
            raise SystemExit("review independence CI accepted concurrency mutation: " + name)
    print("PASS: review independence CI concurrency (10 exact-diagnostic negatives)")


def validate(source: str, *, check_blob: bool = True) -> None:
    validate_trigger_reachability(source)
    validate_yaml_authority(source)
    validate_concurrency_authority(source)
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit("review independence CI workflow source drift: " + label)
    if check_blob:
        payload = source.encode("utf-8")
        git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(git_blob).hexdigest() != REVIEWED_WORKFLOW_GIT_BLOB_SHA:
            raise SystemExit("review independence CI complete workflow source drift")


def prove_branch_guards_runtime() -> None:
    pr = REQUIRED[6][1].strip()
    push = REQUIRED[8][1].strip()
    cases = (
        ("PR so", pr, "GITHUB_BASE_REF", "so", True),
        ("PR main", pr, "GITHUB_BASE_REF", "main", False),
        ("PR missing", pr, "GITHUB_BASE_REF", "", False),
        ("push so", push, "GITHUB_REF", "refs/heads/so", True),
        ("push main", push, "GITHUB_REF", "refs/heads/main", False),
        ("push tag", push, "GITHUB_REF", "refs/tags/v1", False),
    )
    for label, command, key, value, expected in cases:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}
        result = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
        if (result.returncode == 0) != expected:
            raise SystemExit("review independence CI runtime branch guard drift: " + label)
    print("PASS: review independence CI PR/push branch guard runtime (6 cases)")



def prove_diagnostic_redaction_runtime(source: str) -> None:
    """Run the actual inline diagnostic writer in an isolated temporary directory."""
    start, end = "          python - <<'PY'\n", "          PY\n"
    if source.count(start) != 1 or source.count(end) != 1:
        raise SystemExit("review independence diagnostic writer is not uniquely reachable")
    inline = source.split(start, 1)[1].split(end, 1)[0]
    script = "\n".join(line[10:] for line in inline.splitlines()) + "\n"
    with tempfile.TemporaryDirectory(prefix="semantic-eligibility-diagnostic-") as directory:
        env = os.environ.copy()
        env.update({"SOURCE_SHA": "e" * 40, "VALIDATION_EXIT_CODE": "23",
                    "SENSITIVE_CANARY": "CANARY_DO_NOT_PERSIST_REVIEW"})
        result = subprocess.run([sys.executable, "-c", script], cwd=directory, env=env,
                                capture_output=True, text=True, check=False)
        if result.returncode:
            raise SystemExit("review independence isolated diagnostic failed: " + result.stderr[:500])
        output = Path(directory) / "docs/fixtures/memory-os-operability/production-equivalent-environment-review-independence-diagnostic.last.json"
        raw = output.read_text(encoding="utf-8")
        value = json.loads(raw)
        if value.get("output") != "REDACTED: environment review-independence validation failed; raw output withheld":
            raise SystemExit("review independence diagnostic persisted raw validator output")
        if value.get("sourceCommitSha") != "e" * 40 or value.get("exitCode") != 23:
            raise SystemExit("review independence diagnostic source/exit binding drift")
        for field in ("containsSecrets", "generationCreated", "reviewEvidenceCreated", "productionEvidence", "productionReady"):
            if value.get(field) is not False:
                raise SystemExit("review independence diagnostic evidence/readiness drift: " + field)
        if "CANARY_DO_NOT_PERSIST_REVIEW" in raw:
            raise SystemExit("review independence diagnostic persisted synthetic canary")
    print("PASS: review independence isolated diagnostic redaction (1 runtime case)")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_trigger_reachability_negatives(source)
    prove_yaml_authority_negatives(source)
    prove_concurrency_authority_negatives(source)
    prove_branch_guards_runtime()
    prove_diagnostic_redaction_runtime(source)
    cases = (
        ("PR target", REQUIRED[0][1], "  pull_request:\n    paths:\n"),
        ("self trigger", REQUIRED[1][1], ""),
        ("checkout floating", REQUIRED[2][1], "uses: actions/checkout@v4"),
        ("setup floating", REQUIRED[3][1], "uses: actions/setup-python@v5"),
        ("PR credentials", REQUIRED[4][1], "          persist-credentials: true\n"),
        ("writer credentials", REQUIRED[5][1], ""),
        ("PR base", REQUIRED[6][1], ""),
        ("SHA format", REQUIRED[7][1], '          test -n "$expected"\n'),
        ("publisher branch", REQUIRED[8][1], ""),
        ("publisher event", REQUIRED[9][1], ""),
        ("publisher scope", REQUIRED[10][1], "    if: github.event_name != 'pull_request'\n"),
        ("self execution", REQUIRED[11][1], ""),
        ("retry self execution", REQUIRED[12][1], ""),
        ("writer SHA", REQUIRED[13][1], '          expected="${{ github.sha }}"\n'),
        ("PR SHA", REQUIRED[14][1], '          expected="${GITHUB_SHA:-}"\n'),
        ("HEAD check", REQUIRED[15][1], ""),
        ("write scope", REQUIRED[16][1], "      contents: read\n"),
        ("retry latest", REQUIRED[17][1], ""),
        ("raw diagnostic", REQUIRED[18][1], "              'output': Path('/tmp/production-equivalent-environment-review-independence.log').read_text(),\n"),
        ("raw CI log", REQUIRED[19][1], '          cat "$log"\n'),
        ("missing redaction", REQUIRED[18][1], ""),
        ("inserted Action", "      - name: Capture exact review-independence authority source\n", "      - uses: unreviewed/action@v1\n      - name: Capture exact review-independence authority source\n"),
        ("inserted shell", "      - name: Capture exact review-independence authority source\n", "      - run: echo unreviewed\n      - name: Capture exact review-independence authority source\n"),
    )
    blob_only = {"inserted Action", "inserted shell"}
    if len(cases) != 23 or sum(label in blob_only for label, _, _ in cases) != 2:
        raise SystemExit("review independence CI workflow negative inventory drift")
    for label, old, new in cases:
        if old not in source:
            raise SystemExit("review independence CI negative fixture missing: " + label)
        mutated = source.replace(old, new, 1)
        if mutated == source:
            raise SystemExit("review independence CI negative fixture unchanged: " + label)
        try:
            validate(mutated, check_blob=label in blob_only)
        except SystemExit:
            continue
        raise SystemExit("review independence CI accepted unreviewed mutation: " + label)
    print(f"PASS: review independence CI workflow source admission ({len(cases) - 2} semantic anchor + 2 blob-only negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
