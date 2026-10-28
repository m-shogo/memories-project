#!/usr/bin/env python3
"""Authenticate typed eight-domain non-resurrection admission CI source and permissions."""

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
PUBLISHER = ".github/workflows/backup-restore-non-resurrection-admission.yml"
INDEPENDENT = ".github/workflows/backup-restore-non-resurrection-admission-source-negative.yml"
SELF = "scripts/validate-memory-os-backup-restore-non-resurrection-admission-workflow-negative.py"
REVIEWED_PUBLISHER = "22d2e65556f21f01f6ce3bffbd5e1f874a0f2c88"
REVIEWED_INDEPENDENT = "0a4853c3adf951c4873f5f6fc1ec16d9f1854ce4"

PUBLISHER_TRIGGER_PATHS = (
    ".github/workflows/backup-restore-non-resurrection-admission.yml",
    "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json",
    "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
    "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
    "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "contracts/operations/backup-restore-generation-binding-contract.v1.json",
    "contracts/operations/backup-restore-drill-request-contract.v1.json",
    "contracts/operations/backup-restore-drill-request-registry.v1.json",
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/recovery-objectives-admission-contract.v1.json",
    "contracts/operations/recovery-objectives-registry.v1.json",
    "contracts/operations/local-apple-replay-restore-contract.v1.json",
    "contracts/operations/local-coherent-recovery-set-contract.v1.json",
    "contracts/operations/backup-local-foundation-evidence.v1.json",
    "contracts/operations/production-operability-status.json",
    "docs/fixtures/memory-os-operability/local-apple-replay-restore-results.sample.v1.json",
    "docs/fixtures/memory-os-operability/local-coherent-recovery-set-results.sample.v1.json",
    "docs/evidence/backup-restore/**",
    "docs/evidence/recovery-objectives/approvals/**",
    "docs/fixtures/memory-os-operability/backup-restore-generation-evidence/**",
    "docs/fixtures/memory-os-operability/recovery-objectives-approval/**",
    "scripts/memory_os_backup_restore_blockers.py",
    "scripts/memory_os_environment_generation_eligibility.py",
    "scripts/register-memory-os-production-equivalent-environment-generation.py",
    "scripts/validate-memory-os-production-equivalent-environment-generation.py",
    "scripts/register-memory-os-recovery-objectives.py",
    "scripts/validate-memory-os-recovery-objectives.py",
    "scripts/validate-memory-os-recovery-objectives-negative.py",
    "scripts/request-memory-os-backup-restore-drill.py",
    "scripts/validate-memory-os-backup-restore-drill-request.py",
    "scripts/validate-memory-os-backup-restore-drill-request-negative.py",
    "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-negative.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-source-binding-negative.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-load-negative.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-transport-negative.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-contract-path-negative.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-registry-aggregate-negative.py",
    "scripts/reconcile-memory-os-backup-non-resurrection-authority.py",
    "scripts/register-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-review-source-order.py",
    "scripts/validate-memory-os-backup-restore-generation-independent-review.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence-negative.py",
    "scripts/validate-memory-os-backup-restore-semantic-generation-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-candidate-mutation-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-candidate-registry-row-mutation-negative.py",
    "scripts/reconcile-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-generation-binding.py",
    "scripts/validate-memory-os-backup-restore-generation-binding-negative.py",
    "scripts/validate-memory-os-local-apple-replay-restore.py",
    "scripts/validate-memory-os-local-coherent-recovery-set.py",
    "scripts/validate-memory-os-operability.py",
    ".github/workflows/backup-restore-non-resurrection-admission-source-negative.yml",
    "scripts/validate-memory-os-backup-restore-non-resurrection-admission-workflow-negative.py",
)
INDEPENDENT_TRIGGER_PATHS = (
    ".github/workflows/backup-restore-non-resurrection-admission.yml",
    ".github/workflows/backup-restore-non-resurrection-admission-source-negative.yml",
    "scripts/validate-memory-os-backup-restore-non-resurrection-admission-workflow-negative.py",
)
D = chr(36)
PR_BASE = 'test "' + D + '{GITHUB_BASE_REF:-}" = "so"'
PUSH_REF = 'test "' + D + '{GITHUB_REF:-}" = "refs/heads/so"'
EVENT = '[[ "' + D + '{GITHUB_EVENT_NAME:-}" == "push" || "' + D + '{GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]'
PR_SHA_FORMAT = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
WRITER_SHA_FORMAT = '[[ "$EXPECTED_SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]'
PUBLISHER_SCOPE = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
CAPTURE = "      - name: Capture exact typed recovery authority source\n"
MAIN_REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("script trigger", '      - "' + SELF + '"\n', 2),
    ("independent trigger", '      - "' + INDEPENDENT + '"\n', 2),
    ("checkout SHA", CHECKOUT, 2),
    ("setup SHA", SETUP, 2),
    ("PR no credentials", "          persist-credentials: false\n", 1),
    ("writer credentials", "          persist-credentials: true\n", 1),
    ("PR base", PR_BASE, 1),
    ("writer branch", PUSH_REF, 1),
    ("writer event", EVENT, 1),
    ("PR SHA format", PR_SHA_FORMAT, 1),
    ("writer SHA format", WRITER_SHA_FORMAT, 1),
    ("publisher scope", PUBLISHER_SCOPE, 1),
    ("PR/writer self execution", "\n          python " + SELF + "\n", 2),
    ("retry self execution", "\n            python " + SELF + "\n", 1),
    ("PR HEAD", 'test "$(git rev-parse HEAD)" = "$expected"', 1),
    ("writer HEAD", 'test "$(git rev-parse HEAD)" = "$EXPECTED_SOURCE_SHA"', 1),
    ("writer SHA source", 'EXPECTED_SOURCE_SHA="' + D + '{GITHUB_SHA:-}"', 1),
    ("PR checkout source", 'ref: ' + D + '{{ github.event.pull_request.head.sha }}', 1),
    ("writer checkout source", 'ref: ' + D + '{{ github.sha }}', 1),
    ("latest reset", "            git reset --hard origin/so\n", 1),
    ("capture step", CAPTURE, 1),
    ("root read token", "permissions:\n  contents: read\n", 1),
    ("PR read token", "      contents: read\n", 1),
    ("writer write token", "      contents: write\n", 1),
    ("diagnostic fixed redaction", "              'output': 'REDACTED: typed non-resurrection validation failed; consult CI job logs',\n", 1),
    ("raw CI log suppression", '          printf "Typed non-resurrection validation exit code: %s (raw validator log suppressed)\\n" "$code"\n', 1),
    ("no raw diagnostic tail", "text[-12000:]", 0),
    ("no raw CI log echo", '          cat "$log"\n', 0),
    ("diagnostic symlink rejection", "          if path.is_symlink():\n              raise SystemExit('typed non-resurrection diagnostic target must not be a symlink')\n", 1),
)
INDEPENDENT_REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("publisher trigger", '      - "' + PUBLISHER + '"\n', 2),
    ("self trigger", '      - "' + INDEPENDENT + '"\n', 2),
    ("script trigger", '      - "' + SELF + '"\n', 2),
    ("checkout SHA", CHECKOUT, 1),
    ("setup SHA", SETUP, 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("PR base", PR_BASE, 1),
    ("push branch", PUSH_REF, 1),
    ("SHA format", PR_SHA_FORMAT, 1),
    ("self execution", "          python " + SELF + "\n", 1),
    ("read token", "  contents: read\n", 2),
    ("event scope", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", 1),
    ("clean source", '          test -z "$(git status --porcelain)"\n', 2),
)


def source(relative: str) -> str:
    path = ROOT / relative
    try:
        if not path.is_file() or path.is_symlink():
            raise ValueError("not regular")
        if path.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != relative:
            raise ValueError("escaped root")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
        raise SystemExit("typed non-resurrection CI source missing or substituted: " + relative) from exc



def validate_trigger_reachability(
    source: str, trigger_paths: tuple[str, ...], *, expected: int,
    end_marker: str, label: str
) -> None:
    """Require every reviewed path in each event, independent of Git blob SHA."""
    if len(trigger_paths) != expected or len(set(trigger_paths)) != expected:
        raise SystemExit("typed non-resurrection " + label + " CI trigger inventory shortened or duplicated")
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    for marker in (pr_marker, push_marker, end_marker):
        if source.count(marker) != 1:
            raise SystemExit("typed non-resurrection " + label + " CI trigger marker drift")
    pr = source.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push = source.split(push_marker, 1)[1].split(end_marker, 1)[0]
    for event, block in (("pull_request", pr), ("push", push)):
        # Reject every unexpected YAML line, including unquoted additions.
        # The negative fixtures exercise this independently of the Git blob SHA.
        actual = tuple(
            line for line in block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        approved = tuple('      - "' + item + '"' for item in trigger_paths)
        if actual != approved:
            raise SystemExit("typed non-resurrection " + label + " " + event + " exact trigger inventory drift")


def validate_all_trigger_reachability(publisher: str, independent: str) -> None:
    validate_trigger_reachability(
        publisher, PUBLISHER_TRIGGER_PATHS, expected=57,
        end_marker="  workflow_dispatch:\n", label="publisher"
    )
    validate_trigger_reachability(
        independent, INDEPENDENT_TRIGGER_PATHS, expected=3,
        end_marker="\npermissions:\n", label="independent"
    )


def prove_trigger_reachability_negatives(publisher: str, independent: str) -> None:
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    for label, source, paths, expected, end_marker in (
        ("publisher", publisher, PUBLISHER_TRIGGER_PATHS, 57, "  workflow_dispatch:\n"),
        ("independent", independent, INDEPENDENT_TRIGGER_PATHS, 3, "\npermissions:\n"),
    ):
        for event in ("pull_request", "push"):
            for item in paths:
                token = '      - "' + item + '"' + chr(10)
                if source.count(token) != 2:
                    raise SystemExit("typed non-resurrection " + label + " trigger mutation anchor drift: " + item)
                if event == "pull_request":
                    mutated = source.replace(token, "", 1)
                else:
                    prefix, suffix = source.split(push_marker, 1)
                    mutated = prefix + push_marker + suffix.replace(token, "", 1)
                try:
                    validate_trigger_reachability(
                        mutated, paths, expected=expected, end_marker=end_marker, label=label
                    )
                except SystemExit:
                    continue
                raise SystemExit("typed non-resurrection " + label + " accepted missing " + event + " trigger: " + item)
        try:
            validate_trigger_reachability(
                source, paths[:-1], expected=expected, end_marker=end_marker, label=label
            )
        except SystemExit:
            pass
        else:
            raise SystemExit("typed non-resurrection " + label + " shortened trigger inventory accepted")
        for event in ("pull_request", "push"):
            marker = (
                "  pull_request:\n    branches:\n      - so\n    paths:\n"
                if event == "pull_request" else push_marker
            )
            for case, injected in (
                ("quoted extra", '      - "unreviewed/**"\n'),
                ("quoted duplicate", '      - "' + paths[0] + '"\n'),
                ("unquoted extra", "      - unreviewed/**\n"),
                ("unquoted duplicate", "      - " + paths[0] + "\n"),
            ):
                if source.count(marker) != 1:
                    raise SystemExit("typed non-resurrection " + label + " addition marker drift")
                mutated = source.replace(marker, marker + injected, 1)
                if mutated == source:
                    raise SystemExit("typed non-resurrection " + label + " addition fixture unchanged")
                try:
                    validate_trigger_reachability(
                        mutated, paths, expected=expected, end_marker=end_marker, label=label
                    )
                except SystemExit:
                    continue
                raise SystemExit(
                    "typed non-resurrection " + label + " accepted " + event + " addition: " + case
                )
    print("PASS: typed non-resurrection admission CI event-specific triggers (120 removals; 16 additions; 2 shortened inventory negatives)")




def validate_yaml_authority(source: str, kind: str) -> None:
    """Pin typed eight-domain admission CI event/root/permission YAML semantics."""
    if kind == "publisher":
        name = "name: Backup Restore Non-Resurrection Admission"
        paths = PUBLISHER_TRIGGER_PATHS
        roots = [name, "on:", "permissions:", "concurrency:", "jobs:"]
        dispatch = "  workflow_dispatch:\n"
    elif kind == "independent":
        name = "name: Backup Restore Non-Resurrection Admission Source Negative"
        paths = INDEPENDENT_TRIGGER_PATHS
        roots = [name, "on:", "permissions:", "jobs:"]
        dispatch = ""
    else:
        raise SystemExit("typed non-resurrection unknown YAML authority kind")
    path_lines = "".join('      - "' + item + '"\n' for item in paths)
    pr = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    header = name + "\n\non:\n" + pr + path_lines + push + path_lines + dispatch
    if (source.count("\npermissions:\n") != 1
            or source.split("\npermissions:\n", 1)[0] != header):
        raise SystemExit("typed non-resurrection " + kind + " exact event header drift")
    actual_roots = [
        line for line in source.splitlines()
        if line.strip() and not line[0].isspace()
        and not line.lstrip().startswith("#")
    ]
    if actual_roots != roots:
        raise SystemExit("typed non-resurrection " + kind + " root YAML key shadow drift")
    leaves = []
    for line in source.split("\npermissions:\n", 1)[1].splitlines():
        if line.strip() and not line[0].isspace():
            break
        if line.strip() and not line.lstrip().startswith("#"):
            leaves.append(line)
    if leaves != ["  contents: read"]:
        raise SystemExit("typed non-resurrection " + kind + " permission leaf shadow drift")
    jobs = (
        (("  validate-pr:", "read"), ("  validate:", "write"))
        if kind == "publisher" else (("  source-admission:", "read"),)
    )
    body = source.split("\njobs:\n", 1)[1]
    headers = [
        line for line in body.splitlines()
        if line.startswith("  ") and not line.startswith("   ")
        and line.strip() and not line.lstrip().startswith("#")
    ]
    if headers != [job for job, _ in jobs]:
        raise SystemExit("typed non-resurrection " + kind + " job mapping shadow drift")
    for index, (job, access) in enumerate(jobs):
        block = body.split(job + "\n", 1)[1]
        if index + 1 < len(jobs):
            block = block.split(jobs[index + 1][0] + "\n", 1)[0]
        if block.count("    permissions:\n") != 1 or block.count("    runs-on:") != 1:
            raise SystemExit("typed non-resurrection " + kind + " job permission leaf shadow drift")
        section = block.split("    permissions:\n", 1)[1].split("    runs-on:", 1)[0]
        job_leaves = [
            line for line in section.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if job_leaves != ["      contents: " + access]:
            raise SystemExit("typed non-resurrection " + kind + " job permission leaf shadow drift")


def prove_yaml_authority_negatives(publisher: str, independent: str) -> None:
    """Prove 30 exact-diagnostic YAML shadow rejections without blob fallback."""
    count = 0
    for kind, source in (("publisher", publisher), ("independent", independent)):
        validate_yaml_authority(source, kind)
        event = source.replace("on:\n", "on:\n  issues:\n", 1)
        if event == source:
            raise SystemExit("typed non-resurrection " + kind + " YAML event fixture anchor drift")
        cases = [("extra event", event, "exact event header drift")]
        for label, suffix in (
            ("spaced on", "on :\n  issues:\n"),
            ("quoted on", "'on':\n  issues:\n"),
            ("spaced permissions", "permissions :\n  contents: write\n"),
            ("quoted permissions", "'permissions':\n  contents: write\n"),
            ("spaced jobs", "jobs : {}\n"),
            ("quoted jobs", "'jobs': {}\n"),
        ):
            cases.append((label, source + "\n" + suffix, "root YAML key shadow drift"))
        marker = "\npermissions:\n  contents: read\n"
        if source.count(marker) != 1:
            raise SystemExit("typed non-resurrection " + kind + " YAML permission fixture anchor drift")
        for label, leaf in (
            ("spaced contents", "  contents : write\n"),
            ("quoted contents", "  'contents': write\n"),
        ):
            cases.append((label, source.replace(marker, marker + leaf, 1),
                          "permission leaf shadow drift"))
        jobs = (
            (("validate-pr", "read"), ("validate", "write"))
            if kind == "publisher" else (("source-admission", "read"),)
        )
        for job, access in jobs:
            for label, key in (("spaced job", job + " "), ("quoted job", "'" + job + "'")):
                cases.append((label + " " + job,
                              source.rstrip("\n") + "\n  " + key + ": {}\n",
                              "job mapping shadow drift"))
            marker = "    permissions:\n      contents: " + access + "\n"
            if source.count(marker) != 1:
                raise SystemExit("typed non-resurrection " + kind + " job permission fixture anchor drift: " + job)
            for label, leaf in (("spaced", "      contents : write\n"),
                                ("quoted", "      'contents': write\n")):
                cases.append((label + " " + job,
                              source.replace(marker, marker + leaf, 1),
                              "job permission leaf shadow drift"))
        for label, mutated, diagnostic in cases:
            if mutated == source:
                raise SystemExit("typed non-resurrection " + kind + " unchanged YAML fixture: " + label)
            try:
                validate_yaml_authority(mutated, kind)
            except SystemExit as exc:
                expected = "typed non-resurrection " + kind + " " + diagnostic
                if str(exc) != expected:
                    raise SystemExit("typed non-resurrection " + kind + " wrong YAML diagnostic: "
                                     + label + ": " + str(exc)) from exc
            else:
                raise SystemExit("typed non-resurrection " + kind + " accepted YAML mutation: " + label)
            count += 1
    if count != 30:
        raise SystemExit("typed non-resurrection YAML negative inventory drift")
    print("PASS: typed non-resurrection publisher/independent YAML event/root/job/permission authority (30 exact-diagnostic negatives)")


def validate(publisher: str, independent: str, *, check_blob: bool = True) -> None:
    validate_yaml_authority(publisher, "publisher")
    validate_yaml_authority(independent, "independent")
    validate_all_trigger_reachability(publisher, independent)
    for name, content, required, digest in (
        ("publisher", publisher, MAIN_REQUIRED, REVIEWED_PUBLISHER),
        ("independent", independent, INDEPENDENT_REQUIRED, REVIEWED_INDEPENDENT),
    ):
        for label, token, count in required:
            if content.count(token) != count:
                raise SystemExit("typed non-resurrection " + name + " source drift: " + label)
        data = content.encode("utf-8")
        blob = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        if check_blob and hashlib.sha1(blob).hexdigest() != digest:
            raise SystemExit("typed non-resurrection " + name + " complete source drift")


def runtime(publisher: str, independent: str) -> None:
    for name, content in (("publisher", publisher), ("independent", independent)):
        for label, command, key, value, allow in (
            ("PR so", PR_BASE, "GITHUB_BASE_REF", "so", True),
            ("PR main", PR_BASE, "GITHUB_BASE_REF", "main", False),
            ("PR absent", PR_BASE, "GITHUB_BASE_REF", "", False),
            ("push so", PUSH_REF, "GITHUB_REF", "refs/heads/so", True),
            ("push main", PUSH_REF, "GITHUB_REF", "refs/heads/main", False),
            ("push tag", PUSH_REF, "GITHUB_REF", "refs/tags/v1", False),
        ):
            if content.count(command) != 1:
                raise SystemExit("typed non-resurrection " + name + " runtime command missing: " + label)
            result = subprocess.run(["bash", "-e", "-c", command],
                                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value},
                                    capture_output=True, check=False)
            if (result.returncode == 0) != allow:
                raise SystemExit("typed non-resurrection " + name + " runtime branch drift: " + label)
    for event, allow in (("push", True), ("workflow_dispatch", True), ("pull_request", False), ("", False)):
        result = subprocess.run(["bash", "-e", "-c", EVENT],
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GITHUB_EVENT_NAME": event},
                                capture_output=True, check=False)
        if (result.returncode == 0) != allow:
            raise SystemExit("typed non-resurrection writer event runtime drift: " + event)
    print("PASS: typed non-resurrection publisher/independent PR-push branch runtime (12 cases), writer event runtime (4 cases)")


def runtime_sha_proof(publisher: str, independent: str) -> None:
    """Exercise typed non-resurrection PR and writer SHA admission predicates."""
    cases = (
        ("lowercase hex", "a" * 40, True),
        ("numeric hex", "0" * 40, True),
        ("short SHA", "a" * 39, False),
        ("long SHA", "a" * 41, False),
        ("uppercase SHA", "A" * 40, False),
        ("nonhex SHA", "g" * 40, False),
        ("empty SHA", "", False),
        ("literal shell substitution", "$(echo unexpected)", False),
    )
    for source_label, source_text, predicate_label, command in (
        ("publisher", publisher, "PR", PR_SHA_FORMAT),
        ("publisher", publisher, "writer", WRITER_SHA_FORMAT),
        ("independent", independent, "source", PR_SHA_FORMAT),
    ):
        if source_text.count(command) != 1:
            raise SystemExit("typed non-resurrection SHA predicate unreachable: " + source_label + " " + predicate_label)
        prefix = 'EXPECTED_SOURCE_SHA="${PROBE_SHA:-}"\n' if predicate_label == "writer" else 'expected="${PROBE_SHA:-}"\n'
        for label, value, allowed in cases:
            env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PROBE_SHA": value}
            result = subprocess.run(["bash", "-e", "-c", prefix + command], env=env, capture_output=True, check=False)
            if (result.returncode == 0) != allowed:
                raise SystemExit("typed non-resurrection SHA predicate drift: " + source_label + " " + predicate_label + " " + label)
    print(f"PASS: typed non-resurrection publisher/independent SHA runtime ({len(cases) * 3} cases)")

def runtime_diagnostic_redaction(publisher: str) -> None:
    """Execute the exact typed admission diagnostic writer without repo writes."""
    start = "          python - <<'PY'\n"
    end = "          PY\n"
    if publisher.count(start) != 1 or publisher.count(end) != 1:
        raise SystemExit("typed admission diagnostic writer not uniquely reachable")
    inline = publisher.split(start, 1)[1].split(end, 1)[0]
    script = "\n".join(line[10:] for line in inline.splitlines()) + "\n"
    with tempfile.TemporaryDirectory(prefix="typed-admission-diagnostic-") as tmpdir:
        env = os.environ.copy()
        env.update({
            "SOURCE_SHA": "e" * 40,
            "ADMISSION_EXIT_CODE": "23",
            "SENSITIVE_CANARY": "CANARY_DO_NOT_PERSIST_DEF",
        })
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=tmpdir, env=env,
            capture_output=True, text=True, check=False,
        )
        if result.returncode:
            raise SystemExit("typed admission isolated diagnostic failed: " + result.stderr[:500])
        output = Path(tmpdir) / "docs/fixtures/memory-os-operability/backup-restore-non-resurrection-admission-diagnostic.last.json"
        payload = json.loads(output.read_text(encoding="utf-8"))
        if payload.get("output") != "REDACTED: typed non-resurrection validation failed; consult CI job logs":
            raise SystemExit("typed admission diagnostic persisted raw validator output")
        if payload.get("sourceCommitSha") != "e" * 40 or payload.get("exitCode") != 23:
            raise SystemExit("typed admission diagnostic source/exit binding drift")
        if payload.get("containsSecrets") is not False or payload.get("productionEvidence") is not False:
            raise SystemExit("typed admission diagnostic secret/evidence flags drift")
        if payload.get("productionReady") is not False:
            raise SystemExit("typed admission diagnostic readiness drift")
        if "CANARY_DO_NOT_PERSIST_DEF" in output.read_text(encoding="utf-8"):
            raise SystemExit("typed admission diagnostic persisted synthetic canary")
        output.chmod(0o640)
        positive = subprocess.run([sys.executable, "-c", script], cwd=tmpdir, env=env,
                                  capture_output=True, text=True, timeout=15, check=False)
        if positive.returncode or stat.S_IMODE(output.stat().st_mode) != 0o640:
            raise SystemExit("typed admission diagnostic failed to preserve existing mode")
        previous = output.read_bytes()
        for label, before in (("replace", "os.replace(tmp_name, path)"),
                              ("fsync", "os.fsync(handle.fileno())")):
            if script.count(before) != 1:
                raise SystemExit("typed admission diagnostic fault anchor drift: " + label)
            failure = subprocess.run([sys.executable, "-c", script.replace(
                before, "raise OSError('synthetic typed admission diagnostic " + label + " failure')", 1)],
                cwd=tmpdir, env=env, capture_output=True, text=True, timeout=15, check=False)
            if failure.returncode == 0 or "synthetic typed admission diagnostic " + label + " failure" not in failure.stderr:
                raise SystemExit("typed admission diagnostic intended fault not reached: " + label)
            if output.read_bytes() != previous or stat.S_IMODE(output.stat().st_mode) != 0o640:
                raise SystemExit("typed admission diagnostic fault altered prior bytes/mode: " + label)
            if list(output.parent.glob(".backup-restore-non-resurrection-admission-diagnostic.last.json.*.tmp")):
                raise SystemExit("typed admission diagnostic fault left temporary file: " + label)
        outside = Path(tmpdir) / "external-typed-admission-canary"
        outside.write_bytes(previous)
        output.unlink()
        output.symlink_to(outside)
        symlink = subprocess.run([sys.executable, "-c", script], cwd=tmpdir, env=env,
                                 capture_output=True, text=True, timeout=15, check=False)
        if symlink.returncode == 0 or "target must not be a symlink" not in symlink.stderr:
            raise SystemExit("typed admission diagnostic accepted symlink destination")
        if not output.is_symlink() or outside.read_bytes() != previous:
            raise SystemExit("typed admission diagnostic altered external symlink canary")
        if list(output.parent.glob(".backup-restore-non-resurrection-admission-diagnostic.last.json.*.tmp")):
            raise SystemExit("typed admission diagnostic symlink rejection left temporary file")
    print("PASS: typed non-resurrection diagnostic redaction/atomic runtime (5 cases)")


def negatives(publisher: str, independent: str) -> None:
    publisher_cases = (
        ("PR target", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("script trigger", '      - "' + SELF + '"\n', ""),
        ("independent trigger", '      - "' + INDEPENDENT + '"\n', ""),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("PR credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("writer credentials", "          persist-credentials: true\n", ""),
        ("PR base", PR_BASE, ""),
        ("writer branch", PUSH_REF, ""),
        ("writer event", EVENT, ""),
        ("PR SHA format", PR_SHA_FORMAT, 'test -n "$expected"'),
        ("writer SHA format", WRITER_SHA_FORMAT, 'test -n "$EXPECTED_SOURCE_SHA"'),
        ("broad publisher scope", PUBLISHER_SCOPE, "    if: github.event_name != 'pull_request'\n"),
        ("PR self guard", "\n          python " + SELF + "\n", ""),
        ("retry self guard", "\n            python " + SELF + "\n", ""),
        ("PR HEAD identity", 'test "$(git rev-parse HEAD)" = "$expected"', "true"),
        ("writer HEAD identity", 'test "$(git rev-parse HEAD)" = "$EXPECTED_SOURCE_SHA"', "true"),
        ("writer SHA source", 'EXPECTED_SOURCE_SHA="' + D + '{GITHUB_SHA:-}"', 'EXPECTED_SOURCE_SHA="$PR_HEAD_SHA"'),
        ("PR checkout source", 'ref: ' + D + '{{ github.event.pull_request.head.sha }}', 'ref: ' + D + '{{ github.sha }}'),
        ("writer checkout source", 'ref: ' + D + '{{ github.sha }}', 'ref: ' + D + '{{ github.ref }}'),
        ("latest reset", "            git reset --hard origin/so\n", ""),
        ("root write token", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("PR write token", "      contents: read\n", "      contents: write\n"),
        ("writer token removed", "      contents: write\n", "      contents: read\n"),
        ("capture step removed", CAPTURE, ""),
        ("unreviewed Action", CAPTURE, "      - uses: unreviewed/action@v1\n" + CAPTURE),
        ("unreviewed shell", CAPTURE, "      - run: echo unreviewed\n" + CAPTURE),
        ("raw diagnostic", "              'output': 'REDACTED: typed non-resurrection validation failed; consult CI job logs',\n", "              'output': Path('/tmp/backup-restore-non-resurrection-admission.log').read_text(),\n"),
        ("raw CI log", '          printf "Typed non-resurrection validation exit code: %s (raw validator log suppressed)\\n" "$code"\n', '          cat "$log"\n'),
        ("missing redaction", "              'output': 'REDACTED: typed non-resurrection validation failed; consult CI job logs',\n", ""),
        ("symlink guard", "          if path.is_symlink():\n              raise SystemExit('typed non-resurrection diagnostic target must not be a symlink')\n", ""),
    )
    independent_cases = (
        ("PR target", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("publisher trigger", '      - "' + PUBLISHER + '"\n', ""),
        ("self trigger", '      - "' + INDEPENDENT + '"\n', ""),
        ("script trigger", '      - "' + SELF + '"\n', ""),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("persist credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("PR base", PR_BASE, ""),
        ("push branch", PUSH_REF, ""),
        ("event scope", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", "    if: always()\n"),
        ("self execution", "          python " + SELF + "\n", ""),
        ("injected Action", "      - name: Prove typed non-resurrection source admission\n", "      - uses: unreviewed/action@v1\n      - name: Prove typed non-resurrection source admission\n"),
        ("injected shell", "      - name: Prove typed non-resurrection source admission\n", "      - run: echo unreviewed\n      - name: Prove typed non-resurrection source admission\n"),
    )
    # A semantic guard deletion cannot be reclassified as a digest-only proof.
    digest_only = {
        "publisher": frozenset({"unreviewed Action", "unreviewed shell"}),
        "independent": frozenset({"injected Action", "injected shell"}),
    }
    if len(publisher_cases) != 31 or len(independent_cases) != 13:
        raise SystemExit("typed non-resurrection mutation inventory drift")
    semantic_counts = {"publisher": 0, "independent": 0}
    blob_counts = {"publisher": 0, "independent": 0}
    for target, cases in (("publisher", publisher_cases), ("independent", independent_cases)):
        for label, old, new in cases:
            original = publisher if target == "publisher" else independent
            if old not in original:
                raise SystemExit("typed non-resurrection negative fixture missing: " + target + " " + label)
            mutated = original.replace(old, new, 1)
            if mutated == original:
                raise SystemExit("typed non-resurrection negative fixture unchanged: " + target + " " + label)
            required = MAIN_REQUIRED if target == "publisher" else INDEPENDENT_REQUIRED
            semantic = any(mutated.count(token) != original.count(token)
                           for _, token, _ in required)
            if semantic == (label in digest_only[target]):
                raise SystemExit("typed non-resurrection mutation classification drift: " + target + " " + label)
            counts = semantic_counts if semantic else blob_counts
            counts[target] += 1
            try:
                validate(mutated, independent, check_blob=not semantic) if target == "publisher" else validate(publisher, mutated, check_blob=not semantic)
            except SystemExit:
                continue
            raise SystemExit("typed non-resurrection accepted source mutation: " + target + " " + label)
    if (semantic_counts, blob_counts) != (
        {"publisher": 29, "independent": 11},
        {"publisher": 2, "independent": 2},
    ):
        raise SystemExit("typed non-resurrection semantic/blob mutation coverage drift")
    print(f"PASS: typed non-resurrection source mutations: publisher {semantic_counts['publisher']} semantic + {blob_counts['publisher']} blob-only; independent {semantic_counts['independent']} semantic + {blob_counts['independent']} blob-only")


def main() -> int:
    publisher = source(PUBLISHER)
    independent = source(INDEPENDENT)
    validate(publisher, independent)
    prove_trigger_reachability_negatives(publisher, independent)
    prove_yaml_authority_negatives(publisher, independent)
    runtime(publisher, independent)
    runtime_sha_proof(publisher, independent)
    runtime_diagnostic_redaction(publisher)
    negatives(publisher, independent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
