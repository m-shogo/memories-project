#!/usr/bin/env python3
"""Fail-closed executable-source and event/ref negatives for semantic eligibility CI."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/production-equivalent-environment-eligibility.yml"
REVIEWED_WORKFLOW_GIT_BLOB_SHA = "cad837867ba560444e665636087d62279de7f60b"

TRIGGER_PATHS = (
    ".github/workflows/production-equivalent-environment-eligibility.yml",
    "scripts/validate-memory-os-production-equivalent-environment-eligibility-workflow-negative.py",
    "contracts/operations/production-equivalent-environment-eligibility-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/production-operability-status.json",
    "contracts/operations/production-equivalent-environment-record.v1.schema.json",
    "contracts/operations/production-equivalent-environment-generation-record.v1.schema.json",
    "scripts/validate-memory-os-production-equivalent-environment-record.py",
    "scripts/register-memory-os-production-equivalent-environment-generation.py",
    "scripts/memory_os_environment_generation_eligibility.py",
    "scripts/validate-memory-os-environment-generation-eligibility-negative.py",
    "scripts/validate-memory-os-production-equivalent-environment-eligibility-reconcile-negative.py",
    "scripts/validate-memory-os-production-equivalent-environment-eligibility.py",
    "scripts/reconcile-memory-os-production-equivalent-environment-eligibility.py",
    "scripts/validate-memory-os-operability.py",
)
REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("self trigger", '      - "scripts/validate-memory-os-production-equivalent-environment-eligibility-workflow-negative.py"\n', 2),
    ("checkout SHA", "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262", 2),
    ("setup SHA", "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", 2),
    ("PR no credentials", "          persist-credentials: false\n", 1),
    ("publisher credentials", "          persist-credentials: true\n", 1),
    ("PR base", '          test "${GITHUB_BASE_REF:-}" = "so"\n', 1),
    ("PR SHA format", '          [[ "$expected" =~ ^[0-9a-f]{40}$ ]]\n', 2),
    ("publisher branch", '          test "${GITHUB_REF:-}" = "refs/heads/so"\n', 1),
    ("publisher event", '          [[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]\n', 1),
    ("publisher scope", "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n", 1),
    ("self execution", "\n          python scripts/validate-memory-os-production-equivalent-environment-eligibility-workflow-negative.py\n", 2),
    ("retry self execution", "            python scripts/validate-memory-os-production-equivalent-environment-eligibility-workflow-negative.py\n", 1),
    ("writer SHA", '          expected="${GITHUB_SHA:-}"\n', 1),
    ("PR SHA", '          expected="${{ github.event.pull_request.head.sha }}"\n', 1),
    ("HEAD check", '          test "$(git rev-parse HEAD)" = "$expected"\n', 2),
    ("write scope", "      contents: write\n", 1),
    ("retry latest", "            git reset --hard origin/so\n", 1),
    ("redacted diagnostic", "              'output': 'REDACTED: environment eligibility validation failed; raw output withheld',\n", 1),
    ("suppressed CI log", '          printf "Environment eligibility validation exit code: %s (raw validator log suppressed)\\n" "$code"\n', 1),
    ("no raw diagnostic tail", "text[-12000:]", 0),
    ("no raw CI log", '          cat "$log"\n', 0),
)



def validate_trigger_reachability(
    source: str, *, trigger_paths: tuple[str, ...] = TRIGGER_PATHS
) -> None:
    """Pin the complete ordered PR/push eligibility trigger inventory independently of SHA."""
    if len(trigger_paths) != 16 or len(set(trigger_paths)) != 16:
        raise SystemExit("semantic eligibility CI trigger inventory shortened or duplicated")
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    dispatch_marker = "  workflow_dispatch:\n"
    for marker in (pr_marker, push_marker, dispatch_marker):
        if source.count(marker) != 1:
            raise SystemExit("semantic eligibility CI event marker drift")
    pr = source.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push = source.split(push_marker, 1)[1].split(dispatch_marker, 1)[0]
    approved = tuple('      - "' + path + '"' for path in trigger_paths)
    for event, block in (("pull_request", pr), ("push", push)):
        actual = tuple(
            line for line in block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        if actual != approved:
            raise SystemExit("semantic eligibility CI " + event + " exact trigger inventory drift")


def validate_yaml_authority(source: str) -> None:
    """Pin reviewed event, root and read-only permission YAML semantics without blob-only reliance."""
    expected_header = (
        "name: Production Equivalent Environment Eligibility\n\non:\n"
        + "  pull_request:\n    branches:\n      - so\n    paths:\n"
        + "".join('      - "' + path + '"\n' for path in TRIGGER_PATHS)
        + "  push:\n    branches:\n      - so\n    paths:\n"
        + "".join('      - "' + path + '"\n' for path in TRIGGER_PATHS)
        + "  workflow_dispatch:\n"
    )
    if (source.count("\npermissions:\n") != 1
            or source.split("\npermissions:\n", 1)[0] != expected_header):
        raise SystemExit("semantic eligibility CI exact event header drift")
    roots = [
        line for line in source.splitlines()
        if line.strip() and not line[0].isspace()
        and not line.lstrip().startswith("#")
    ]
    if roots != [
        "name: Production Equivalent Environment Eligibility",
        "on:", "permissions:", "concurrency:", "jobs:",
    ]:
        raise SystemExit("semantic eligibility CI root YAML key shadow drift")
    permission_rows = []
    for line in source.split("\npermissions:\n", 1)[1].splitlines():
        if line.strip() and not line[0].isspace():
            break
        if line.strip() and not line.lstrip().startswith("#"):
            permission_rows.append(line)
    if permission_rows != ["  contents: read"]:
        raise SystemExit("semantic eligibility CI permission leaf shadow drift")


def prove_yaml_authority_negatives(source: str) -> None:
    """Reject each YAML mapping shadow for the intended diagnostic."""
    validate_yaml_authority(source)
    event = source.replace("on:\n", "on:\n  issues:\n", 1)
    if event == source:
        raise SystemExit("semantic eligibility CI event fixture anchor drift")
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
        raise SystemExit("semantic eligibility CI permission fixture anchor drift")
    for label, leaf in (
        ("spaced contents", "  contents : write\n"),
        ("quoted contents", "  'contents': write\n"),
    ):
        cases.append((label, source.replace(marker, marker + leaf, 1),
                      "permission leaf shadow drift"))
    if len(cases) != 9:
        raise SystemExit("semantic eligibility CI YAML negative inventory drift")
    for label, mutated, diagnostic in cases:
        if mutated == source:
            raise SystemExit("semantic eligibility CI unchanged YAML negative: " + label)
        try:
            validate_yaml_authority(mutated)
        except SystemExit as exc:
            expected = "semantic eligibility CI " + diagnostic
            if str(exc) != expected:
                raise SystemExit("semantic eligibility CI wrong YAML diagnostic: "
                                 + label + ": " + str(exc)) from exc
        else:
            raise SystemExit("semantic eligibility CI accepted YAML mutation: " + label)
    print("PASS: semantic eligibility CI YAML event/root/permission authority (9 exact-diagnostic negatives)")


def prove_trigger_reachability_negatives(source: str) -> None:
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    for event in ("pull_request", "push"):
        for path in TRIGGER_PATHS:
            token = '      - "' + path + '"\n'
            if source.count(token) != 2:
                raise SystemExit("semantic eligibility CI trigger mutation anchor drift: " + path)
            if event == "pull_request":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(push_marker, 1)
                mutated = prefix + push_marker + suffix.replace(token, "", 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("semantic eligibility CI accepted missing " + event + " trigger: " + path)
        marker = pr_marker if event == "pull_request" else push_marker
        for label, injected in (
            ("quoted extra", '      - "unreviewed/**"\n'),
            ("quoted duplicate", '      - "' + TRIGGER_PATHS[0] + '"\n'),
            ("unquoted extra", "      - unreviewed/**\n"),
            ("unquoted duplicate", "      - " + TRIGGER_PATHS[0] + "\n"),
        ):
            if source.count(marker) != 1:
                raise SystemExit("semantic eligibility CI addition marker drift: " + event)
            mutated = source.replace(marker, marker + injected, 1)
            if mutated == source:
                raise SystemExit("semantic eligibility CI addition fixture unchanged")
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("semantic eligibility CI accepted " + event + " addition: " + label)
    try:
        validate_trigger_reachability(source, trigger_paths=TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("semantic eligibility CI shortened trigger inventory accepted")
    print("PASS: semantic eligibility CI event-specific triggers (32 removals; 8 additions; 1 shortened inventory negative)")



def validate_job_authority(source: str) -> None:
    """Pin reviewed PR read and publisher write job semantics independently of SHA."""
    jobs = (
        ("validate-pr", "github.event_name == 'pull_request'", "read", 8),
        ("validate",
         "(github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'",
         "write", 8),
    )
    prefix = "semantic eligibility CI "
    if source.count("\njobs:\n") != 1:
        raise SystemExit(prefix + "job mapping shadow drift")
    body = source.split("\njobs:\n", 1)[1]
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
    if actual != ["  " + name + ":" for name, _, _, _ in jobs]:
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


def prove_job_authority_negatives(source: str) -> None:
    """Prove 24 exact-diagnostic job mapping, execution and permission negatives."""
    validate_job_authority(source)
    jobs = (
        ("validate-pr", "github.event_name == 'pull_request'", "read", 8),
        ("validate",
         "(github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'",
         "write", 8),
    )
    count = 0
    for name, condition, scope, timeout in jobs:
        header = "  " + name + ":\n"
        if source.count(header) != 1:
            raise SystemExit("semantic eligibility CI job fixture header drift: " + name)

        def in_job(before: str, after: str) -> str:
            prefix, suffix = source.split(header, 1)
            if before not in suffix:
                raise SystemExit("semantic eligibility CI job fixture anchor drift: " + name)
            return prefix + header + suffix.replace(before, after, 1)

        condition_anchor = "    if: " + condition + "\n"
        permission = "    permissions:\n      contents: " + scope + "\n"
        runner = "    runs-on: ubuntu-latest\n"
        timeout_anchor = "    timeout-minutes: " + str(timeout) + "\n"
        steps = "    steps:\n"
        cases = [
            ("duplicate mapping", source + "\n" + header + "    runs-on: ubuntu-latest\n",
             "job mapping shadow drift"),
            ("quoted mapping", source.replace(header, "  '" + name + "':\n", 1),
             "job mapping shadow drift"),
            ("spaced mapping", source.replace(header, "  " + name + " :\n", 1),
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
            if changed == source:
                raise SystemExit("semantic eligibility CI unchanged job fixture: " + mutation)
            try:
                validate_job_authority(changed)
            except SystemExit as exc:
                expected = "semantic eligibility CI " + diagnostic
                if str(exc) != expected:
                    raise SystemExit("semantic eligibility CI wrong job diagnostic: "
                                     + name + " " + mutation + ": " + str(exc)) from exc
            else:
                raise SystemExit("semantic eligibility CI accepted job shadow: " + name + " " + mutation)
            count += 1
    if count != 24:
        raise SystemExit("semantic eligibility CI job negative inventory drift")
    print("PASS: semantic eligibility CI job authority (24 exact-diagnostic negatives)")


def validate(source: str, *, check_blob: bool = True) -> None:
    validate_trigger_reachability(source)
    validate_yaml_authority(source)
    validate_job_authority(source)
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit("semantic eligibility CI workflow source drift: " + label)
    if check_blob:
        payload = source.encode("utf-8")
        git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(git_blob).hexdigest() != REVIEWED_WORKFLOW_GIT_BLOB_SHA:
            raise SystemExit("semantic eligibility CI complete workflow source drift")


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
            raise SystemExit("semantic eligibility CI runtime branch guard drift: " + label)
    print("PASS: semantic eligibility CI PR/push branch guard runtime (6 cases)")



def prove_diagnostic_redaction_runtime(source: str) -> None:
    """Run the actual inline diagnostic writer in an isolated temporary directory."""
    start, end = "          python - <<'PY'\n", "          PY\n"
    if source.count(start) != 1 or source.count(end) != 1:
        raise SystemExit("semantic eligibility diagnostic writer is not uniquely reachable")
    inline = source.split(start, 1)[1].split(end, 1)[0]
    script = "\n".join(line[10:] for line in inline.splitlines()) + "\n"
    with tempfile.TemporaryDirectory(prefix="semantic-eligibility-diagnostic-") as directory:
        env = os.environ.copy()
        env.update({"SOURCE_SHA": "e" * 40, "ELIGIBILITY_EXIT_CODE": "23",
                    "SENSITIVE_CANARY": "CANARY_DO_NOT_PERSIST_ELIGIBILITY"})
        result = subprocess.run([sys.executable, "-c", script], cwd=directory, env=env,
                                capture_output=True, text=True, check=False)
        if result.returncode:
            raise SystemExit("semantic eligibility isolated diagnostic failed: " + result.stderr[:500])
        output = Path(directory) / "docs/fixtures/memory-os-operability/production-equivalent-environment-eligibility-diagnostic.last.json"
        raw = output.read_text(encoding="utf-8")
        value = json.loads(raw)
        if value.get("output") != "REDACTED: environment eligibility validation failed; raw output withheld":
            raise SystemExit("semantic eligibility diagnostic persisted raw validator output")
        if value.get("sourceCommitSha") != "e" * 40 or value.get("exitCode") != 23:
            raise SystemExit("semantic eligibility diagnostic source/exit binding drift")
        for field in ("containsSecrets", "generationCreated", "eligibilityFabricated", "productionEvidence", "productionReady"):
            if value.get(field) is not False:
                raise SystemExit("semantic eligibility diagnostic evidence/readiness drift: " + field)
        if "CANARY_DO_NOT_PERSIST_ELIGIBILITY" in raw:
            raise SystemExit("semantic eligibility diagnostic persisted synthetic canary")
    print("PASS: semantic eligibility isolated diagnostic redaction (1 runtime case)")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_trigger_reachability_negatives(source)
    prove_yaml_authority_negatives(source)
    prove_job_authority_negatives(source)
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
        ("raw diagnostic", REQUIRED[18][1], "              'output': Path('/tmp/production-equivalent-environment-eligibility.log').read_text(),\n"),
        ("raw CI log", REQUIRED[19][1], '          cat "$log"\n'),
        ("missing redaction", REQUIRED[18][1], ""),
        ("inserted Action", "      - name: Capture exact semantic eligibility source\n", "      - uses: unreviewed/action@v1\n      - name: Capture exact semantic eligibility source\n"),
        ("inserted shell", "      - name: Capture exact semantic eligibility source\n", "      - run: echo unreviewed\n      - name: Capture exact semantic eligibility source\n"),
    )
    blob_only = {"inserted Action", "inserted shell"}
    if len(cases) != 23 or sum(label in blob_only for label, _, _ in cases) != 2:
        raise SystemExit("semantic eligibility CI workflow negative inventory drift")
    for label, old, new in cases:
        if old not in source:
            raise SystemExit("semantic eligibility CI negative fixture missing: " + label)
        mutated = source.replace(old, new, 1)
        if mutated == source:
            raise SystemExit("semantic eligibility CI negative fixture unchanged: " + label)
        try:
            validate(mutated, check_blob=label in blob_only)
        except SystemExit:
            continue
        raise SystemExit("semantic eligibility CI accepted unreviewed mutation: " + label)
    print(f"PASS: semantic eligibility CI workflow source admission ({len(cases) - 2} semantic anchor + 2 blob-only negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
