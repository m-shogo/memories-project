#!/usr/bin/env python3
"""Validate current Memory OS entrypoint documents against repository authority."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

ENTRYPOINTS = {
    "README.md": {
        "required": [
            "docs/memory-os-current-authority-order-round-10-operability.md",
            "contracts/operations/production-operability-status.json",
            "productionDecision: `NO_GO`",
            "Operations hardening before feature breadth",
        ],
        "forbidden": [
            "Round 9 Security Authority](docs/memory-os-current-authority-order-round-9-security.md)\n2.",
            "Immediate next checkpoint:\n\n```txt\nHTTP server main",
            "the missing layers are the executable server, Apply/Memory persistence and the clients",
        ],
    },
    "SECURITY.md": {
        "required": [
            "docs/memory-os-current-authority-order-round-10-operability.md",
            "contracts/operations/production-operability-status.json",
            "Production remains `NO_GO`",
            "Apple code exchange is implemented",
        ],
        "forbidden": [
            "there is no executable server yet",
            "Apple code exchange/secret rotation and concrete replay/session stores",
            "the sole remaining Apple gate",
            "every push since has run green",
        ],
    },
    "services/import-api/README.md": {
        "required": [
            "The executable HTTP server exists",
            "Apple code exchange, replay protection, account binding and session issuance exist",
            "Production remains `NO_GO`",
            "docs/memory-os-current-authority-order-round-10-operability.md",
        ],
        "forbidden": [
            "does not expose a production server",
            "Apple code exchange/secret rotation and concrete replay/session stores",
            "complete deletion fencing",
            "the branch has run green since",
        ],
    },
    "docs/memory-os-current-authority-order-round-10-operability.md": {
        "required": [
            "Implementation truth:",
            "Readiness judgement:",
            "current code, migrations and executable tests for implementation facts",
            "scripts/validate-memory-os-entry-docs.py",
            "a checkpoint statement is not stronger than current code and tests",
        ],
        "forbidden": [
            "newest applicable implementation checkpoint\n7. current code",
        ],
    },
    "docs/memory-os-current-authority-order-round-9-security.md": {
        "required": [
            "SUBORDINATE TO ROUND 10",
            "memory-os-current-authority-order-round-10-operability.md",
            "executable HTTP server exists",
            "Production-readiness judgement is governed by",
        ],
        "forbidden": [
            "# Memory OS Current Authority Order — Round 9 Security",
            "there is no executable server yet",
            "Apple code exchange/secret rotation/replay/session persistence",
        ],
    },
}

LEARNING_GUARDS = (
    "scripts/validate-autonomous-learning-system.py",
    "scripts/validate-autonomous-learning-system-negative.py",
)
LEARNING_GUARD_TIMEOUT_SECONDS = 120
MIN_LEARNING_NEGATIVE_CASES = 601


def learning_guard_timeout_reviewed(seconds: object) -> bool:
    """A longer nested deadline would conceal a measured regression."""
    return type(seconds) is int and seconds == 120


def learning_guard_passed(relative: str, completed: subprocess.CompletedProcess[str]) -> bool:
    """An exit-zero child without its actual PASS proof is not an executed guard."""
    if (type(completed.returncode) is not int or completed.returncode != 0
            or type(completed.stdout) is not str
            or type(completed.stderr) is not str or completed.stderr):
        return False
    # A validated child prints exactly one LF-terminated proof line. Do not
    # normalize away extra blank lines, CRLF, padding, or missing terminators.
    if not completed.stdout.endswith("\n") or completed.stdout.endswith("\r\n"):
        return False
    output = completed.stdout[:-1]
    if relative == LEARNING_GUARDS[0]:
        return output == "Autonomous improvement/learning contract validation PASS"
    if relative == LEARNING_GUARDS[1]:
        prefix = "Autonomous learning negative validation PASS ("
        suffix = " fail-closed cases)"
        if not output.startswith(prefix) or not output.endswith(suffix):
            return False
        count = output[len(prefix):-len(suffix)]
        # An untrusted child must not trigger Python's oversized-int limit or
        # use zero-padding to disguise a noncanonical case count.
        if (not count or len(count) > 9 or count[0] == "0"
                or not count.isascii() or not count.isdecimal()):
            return False
        return int(count) >= MIN_LEARNING_NEGATIVE_CASES
    return False


def bounded_learning_guard_failure_detail(completed: subprocess.CompletedProcess[str]) -> str:
    """Keep child failure evidence bounded and on one CI log line."""
    # An unexpected capture type is a diagnostic failure, never an excuse
    # to stringify arbitrary objects or leak unbounded byte representations.
    if type(completed.stderr) is not str or type(completed.stdout) is not str:
        return "unreviewed captured stream type"
    raw = (completed.stderr or completed.stdout).strip()
    if not raw:
        return "empty"
    # Reject every Unicode nonprintable, including soft hyphen, joiners and
    # surrogate code points that an enumerated control regex can overlook.
    return "".join(char if char.isprintable() else " " for char in raw[-800:])


def prove_learning_guard_classifier(failures: list[str]) -> None:
    """Prove that a no-op, truncated suite or spurious success cannot pass."""
    positive = "Autonomous improvement/learning contract validation PASS\n"
    negative = f"Autonomous learning negative validation PASS ({MIN_LEARNING_NEGATIVE_CASES} fail-closed cases)\n"
    cases = (
        ("positive", LEARNING_GUARDS[0], 0, positive, "", True),
        ("negative", LEARNING_GUARDS[1], 0, negative, "", True),
        ("expanded negative", LEARNING_GUARDS[1], 0,
         f"Autonomous learning negative validation PASS ({MIN_LEARNING_NEGATIVE_CASES + 1} fail-closed cases)\n", "", True),
        ("missing output", LEARNING_GUARDS[0], 0, "", "", False),
        ("nonzero with success text", LEARNING_GUARDS[0], 1, positive, "", False),
        ("boolean zero exit", LEARNING_GUARDS[0], False, positive, "", False),
        ("floating zero exit", LEARNING_GUARDS[0], 0.0, positive, "", False),
        ("nonstring stdout", LEARNING_GUARDS[0], 0, None, "", False),
        ("nonstring stderr", LEARNING_GUARDS[0], 0, positive, None, False),
        ("stderr with success text", LEARNING_GUARDS[0], 0, positive, "injected", False),
        ("truncated negative", LEARNING_GUARDS[1], 0,
         f"Autonomous learning negative validation PASS ({MIN_LEARNING_NEGATIVE_CASES - 1} fail-closed cases)\n", "", False),
        ("nonnumeric count", LEARNING_GUARDS[1], 0,
         "Autonomous learning negative validation PASS (False fail-closed cases)\n", "", False),
        ("zero-padded count", LEARNING_GUARDS[1], 0,
         f"Autonomous learning negative validation PASS (0{MIN_LEARNING_NEGATIVE_CASES} fail-closed cases)\n", "", False),
        ("oversized count", LEARNING_GUARDS[1], 0,
         "Autonomous learning negative validation PASS (" + "9" * 5000 + " fail-closed cases)\n", "", False),
        ("non-ASCII decimal count", LEARNING_GUARDS[1], 0,
         "Autonomous learning negative validation PASS (６０１ fail-closed cases)\n", "", False),
        ("empty count", LEARNING_GUARDS[1], 0,
         "Autonomous learning negative validation PASS ( fail-closed cases)\n", "", False),
        ("extra output", LEARNING_GUARDS[1], 0, negative + "ignored", "", False),
        ("extra blank line", LEARNING_GUARDS[1], 0, negative + "\n", "", False),
        ("missing terminator", LEARNING_GUARDS[0], 0, positive[:-1], "", False),
        ("CRLF terminator", LEARNING_GUARDS[0], 0, positive.replace("\n", "\r\n"), "", False),
        ("leading whitespace", LEARNING_GUARDS[0], 0, " " + positive, "", False),
        ("unbound guard", "scripts/unbound-guard.py", 0, positive, "", False),
    )
    if not learning_guard_timeout_reviewed(120):
        failures.append("learning guard reviewed timeout positive rejected")
    for candidate in (0, 119, 121, 300, True, 120.0, "120"):
        if learning_guard_timeout_reviewed(candidate):
            failures.append("learning guard reviewed timeout negative accepted")
    for name, relative, code, stdout, stderr, expected in cases:
        completed = subprocess.CompletedProcess([], code, stdout, stderr)
        if learning_guard_passed(relative, completed) is not expected:
            failures.append(f"learning guard success classifier misclassified: {name}")
    for name, stdout, stderr, expected in (
        ("empty", "", "", "empty"),
        ("multiline", "", "first\nsecond\rthird", "first second third"),
        ("stderr preferred", "stdout", "stderr", "stderr"),
        ("bounded", "", "x" * 900, "x" * 800),
        ("control", "", "a\x1bb\x7fc", "a b c"),
        ("Unicode line separators", "", "a\u0085b\u2028c\u2029d", "a b c d"),
        ("bidi direction controls", "", "a\u061cb\u202ec\u2066d\u2069e", "a b c d e"),
        ("zero-width and BOM", "", "a\u200bb\u200fc\ufeffd", "a b c d"),
        ("soft hyphen", "", "a\u00adb", "a b"),
        ("zero-width joiner", "", "a\u200db", "a b"),
        ("nonbreaking space", "", "a\u00a0b", "a b"),
        ("lone surrogate", "", "a\ud800b", "a b"),
        ("visible Japanese", "", "失敗理由", "失敗理由"),
        ("missing stdout", None, "", "unreviewed captured stream type"),
        ("missing stderr", "", None, "unreviewed captured stream type"),
        ("byte stdout", b"bytes", "", "unreviewed captured stream type"),
        ("byte stderr", "", b"bytes", "unreviewed captured stream type"),
        ("object stdout", object(), "", "unreviewed captured stream type"),
        ("object stderr", "", object(), "unreviewed captured stream type"),
    ):
        completed = subprocess.CompletedProcess([], 1, stdout, stderr)
        if bounded_learning_guard_failure_detail(completed) != expected:
            failures.append(f"learning guard failure detail misclassified: {name}")


def validate_learning_guards(failures: list[str]) -> None:
    """Keep autonomous-learning guards reachable from the existing operability CI path."""
    if len(LEARNING_GUARDS) != len(set(LEARNING_GUARDS)):
        failures.append("duplicate autonomous-learning guard binding")
        return
    if not learning_guard_timeout_reviewed(LEARNING_GUARD_TIMEOUT_SECONDS):
        failures.append("autonomous-learning guard timeout must remain reviewed 120 seconds")
        return
    prove_learning_guard_classifier(failures)
    if failures:
        return
    for relative in LEARNING_GUARDS:
        path = REPO_ROOT / relative
        if not path.is_file():
            failures.append(f"missing autonomous-learning guard: {relative}")
            continue
        try:
            completed = subprocess.run(
                [sys.executable, str(path), "--repo-root", str(REPO_ROOT)],
                cwd=REPO_ROOT,
                check=False,
                text=True,
                capture_output=True,
                timeout=LEARNING_GUARD_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            failures.append(
                f"autonomous-learning guard timed out after {LEARNING_GUARD_TIMEOUT_SECONDS}s: {relative}"
            )
            continue
        if not learning_guard_passed(relative, completed):
            # Preserve the actual bounded child diagnostic on CI failure.
            # A first direct PASS cannot establish this independent invocation.
            # Never emit unbounded child output or treat diagnostics as proof.
            child_diagnostic = bounded_learning_guard_failure_detail(completed)
            failures.append(
                f"autonomous-learning guard missing verified PASS: {relative} "
                f"(exit {completed.returncode}; "
                f"child diagnostic: {child_diagnostic})"
            )
        else:
            # Emit only a previously validated, single-line success marker.
            # This is CI execution evidence, never production readiness.
            print(f"autonomous-learning guard verified: {completed.stdout.strip()}")



# Reviewed inventory: a removed or renamed independent source-negative workflow
# must not silently disappear from the CI execution-path audit.
SOURCE_NEGATIVE_WORKFLOW_NAMES = (
    ".github/workflows/backup-restore-drill-preflight-reconcile-source-negative.yml",
    ".github/workflows/backup-restore-drill-preflight-source-negative.yml",
    ".github/workflows/backup-restore-generation-binding-source-negative.yml",
    ".github/workflows/backup-restore-non-resurrection-admission-source-negative.yml",
    ".github/workflows/backup-restore-promotion-review-source-negative.yml",
    ".github/workflows/compatibility-diagnostic-source-negative.yml",
    ".github/workflows/deletion-advanced-evidence-source-negative.yml",
    ".github/workflows/deletion-container-kill-authority-source-negative.yml",
    ".github/workflows/deletion-lease-recovery-authority-source-negative.yml",
    ".github/workflows/deletion-lease-recovery-diagnostic-source-negative.yml",
    ".github/workflows/deletion-mutation-evidence-source-negative.yml",
    ".github/workflows/deletion-prefence-diagnostic-source-negative.yml",
    ".github/workflows/deletion-prefence-mutation-diagnostic-source-negative.yml",
    ".github/workflows/deletion-prefence-upload-diagnostic-source-negative.yml",
    ".github/workflows/deletion-sigkill-diagnostic-source-negative.yml",
    ".github/workflows/deletion-worker-container-kill-recovery-diagnostic-source-negative.yml",
    ".github/workflows/deletion-worker-host-failure-source-negative.yml",
    ".github/workflows/deletion-worker-saturation-diagnostic-source-negative.yml",
    ".github/workflows/deletion-worker-sigkill-recovery-diagnostic-source-negative.yml",
    ".github/workflows/incident-contact-routing-source-negative.yml",
    ".github/workflows/incident-control-authority-source-negative.yml",
    ".github/workflows/incident-control-exercise-diagnostic-source-negative.yml",
    ".github/workflows/incident-human-tabletop-workflow-source-negative.yml",
    ".github/workflows/live-dependency-bootstrap-source-negative.yml",
    ".github/workflows/live-load-authority-diagnostic-source-negative.yml",
    ".github/workflows/live-load-gofmt-source-negative.yml",
    ".github/workflows/live-object-stage-source-negative.yml",
    ".github/workflows/load-foundation-diagnostic-source-negative.yml",
    ".github/workflows/load-missing-evidence-source-negative.yml",
    ".github/workflows/load-readiness-note-source-negative.yml",
    ".github/workflows/local-migration-recovery-source-negative.yml",
    ".github/workflows/metrics-authority-source-negative.yml",
    ".github/workflows/migration-evidence-registry-source-negative.yml",
    ".github/workflows/migration-operation-evidence-source-negative.yml",
    ".github/workflows/migration-production-shaped-admission-source-negative.yml",
    ".github/workflows/observability-access-source-negative.yml",
    ".github/workflows/operability-admission-inventory-atomic-write-source-negative.yml",
    ".github/workflows/operability-admission-inventory-pr-source-negative.yml",
    ".github/workflows/operability-admission-inventory-source-negative.yml",
    ".github/workflows/operability-admission-inventory-transactional-source-negative.yml",
    ".github/workflows/operability-evidence-ownership-source-negative.yml",
    ".github/workflows/production-equivalent-dependency-source-negative.yml",
    ".github/workflows/production-equivalent-environment-generation-source-negative.yml",
    ".github/workflows/production-shaped-failure-drills-source-negative.yml",
    ".github/workflows/rate-limit-distributed-runtime-source-negative.yml",
    ".github/workflows/rate-limit-operations-source-negative.yml",
    ".github/workflows/reconcile-backup-authority-source-negative.yml",
    ".github/workflows/reconcile-backup-restore-source-negative.yml",
    ".github/workflows/recovery-objectives-admission-source-negative.yml",
    ".github/workflows/release-baseline-registry-source-negative.yml",
    ".github/workflows/release-compatibility-pair-source-negative.yml",
    ".github/workflows/upload-completion-load-source-negative.yml",
)
SOURCE_NEGATIVE_JOB_CONDITION = (
    "if: github.event_name == 'pull_request' || "
    "(github.event_name == 'push' && github.ref == 'refs/heads/so')"
)


def source_negative_event_paths(source: str) -> dict[str, tuple[str, ...]] | None:
    """Fail closed on duplicate YAML event authority and unreviewed event filters.

    The reviewed source-negative workflows use only an exact so branch filter
    followed by paths on both PR and push. Additional valid YAML keys must
    not silently shadow or narrow the required CI execution path.
    """
    if len(re.findall(r"""(?m)^(?:on:|["']on["']:)""", source)) != 1:
        return None
    lines = source.splitlines()
    try:
        start = lines.index("on:")
    except ValueError:
        return None
    event_lines: list[str] = []
    for line in lines[start + 1:]:
        if line.strip() and not line.startswith((" ", "\t", "#")):
            break
        event_lines.append(line)
    markers = [(index, line[2:-1]) for index, line in enumerate(event_lines)
               if re.fullmatch(r"  [a-z_]+:", line)]
    if len(markers) != 2 or {name for _, name in markers} != {"pull_request", "push"}:
        return None
    result: dict[str, tuple[str, ...]] = {}
    for position, (index, name) in enumerate(markers):
        end = markers[position + 1][0] if position + 1 < len(markers) else len(event_lines)
        block = [
            line for line in event_lines[index + 1:end]
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if block[:1] == ["    branches: [so]"]:
            path_index = 1
        elif block[:2] == ["    branches:", "      - so"]:
            path_index = 2
        else:
            return None
        if block[path_index:path_index + 1] != ["    paths:"]:
            return None
        paths: list[str] = []
        for line in block[path_index + 1:]:
            match = re.fullmatch(
                r"""      - (?:"([^"]+)"|'([^']+)'|([^\s#]+))""", line
            )
            if match is None:
                return None
            paths.append(next(value for value in match.groups() if value is not None))
        # GitHub path filters apply ordered ! exclusions: a later negative
        # pattern can remove a required validator/self trigger even though
        # its positive path still appears in the inventory.
        if (not paths or len(paths) != len(set(paths))
                or any(path.startswith("!") for path in paths)):
            return None
        result[name] = tuple(paths)
    return result


def source_negative_reachability_issues(relative: str, source: str, script_exists) -> list[str]:
    """Check that each independent CI path actually invokes its bound scripts."""
    issues: list[str] = []
    paths = source_negative_event_paths(source)
    if paths is None:
        return ["missing/ambiguous PR and push path-filter authority"]
    for event in ("pull_request", "push"):
        if relative not in paths[event]:
            issues.append(f"{event}: source-negative workflow not self-triggered")
    # A reviewed third-step executable must also be reachable when its own
    # validator/test sources change; checking the workflow self-trigger and
    # second-step Python commands alone is insufficient.
    if relative == ".github/workflows/local-migration-recovery-source-negative.yml":
        independent = "scripts/validate-memory-os-local-migration-recovery-artifact-reconcile-negative.py"
        for event in ("pull_request", "push"):
            if independent not in paths[event]:
                issues.append(f"{event}: local recovery third-step validator trigger missing")
    if relative == ".github/workflows/live-object-stage-source-negative.yml":
        go_test_sources = (
            "services/import-api/internal/httpserver/live_object_load_test.go",
            "services/import-api/internal/httpserver/live_load_test.go",
            "services/import-api/internal/httpserver/live_result_atomic_test.go",
        )
        for event in ("pull_request", "push"):
            for test_source in go_test_sources:
                if test_source not in paths[event]:
                    issues.append(f"{event}: reviewed Go test source trigger missing: {test_source}")
    if len(re.findall(r"(?m)^    if:", source)) != 1:
        issues.append("duplicate or missing job-level event condition")
    if len(re.findall(r"(?m)^permissions:$", source)) != 1:
        issues.append("duplicate or missing workflow permissions key")
    if len(re.findall(r"(?m)^  contents:", source)) != 1:
        issues.append("duplicate or missing workflow contents permission")
    if (len(re.findall(r"(?m)^    permissions:$", source)) != 1
            or len(re.findall(r"(?m)^      contents:", source)) != 1
            or not re.search(r"(?m)^    permissions:\n      contents: read$", source)):
        issues.append("duplicate, missing or elevated job permissions")
    # A visible contents: read does not prove the effective YAML permission:
    # quoted and whitespace-before-colon keys can shadow the same leaf.
    workflow_permission_sections = source.split("\npermissions:\n")
    if len(workflow_permission_sections) == 2:
        workflow_permission_rows = [
            row for row in workflow_permission_sections[1].split("\njobs:\n", 1)[0].splitlines()
            if re.match(r"^ {2}\S", row) and not row.lstrip().startswith("#")
        ]
        if workflow_permission_rows != ["  contents: read"]:
            issues.append("duplicate or missing workflow contents permission")
    jobs = source.split("\njobs:\n")
    if len(jobs) == 2:
        job_permission_sections = jobs[1].split("    permissions:\n")
        if len(job_permission_sections) == 2:
            job_permission_rows = [
                row for row in job_permission_sections[1].split("    runs-on:", 1)[0].splitlines()
                if re.match(r"^ {6}\S", row) and not row.lstrip().startswith("#")
            ]
            if job_permission_rows != ["      contents: read"]:
                issues.append("duplicate, missing or elevated job permissions")
    if (len(jobs) != 2 or
            len(re.findall(r"(?m)^  [A-Za-z0-9_-]+:\s*$", jobs[1])) != 1):
        issues.append("missing or duplicate source-negative CI job")
    # YAML accepts whitespace before the mapping colon and quoted keys.
    # Either can shadow a reviewed job ID without matching the count above.
    job_header_rows = ([
        row for row in jobs[1].splitlines()
        if re.match(r"^ {2}\S", row) and not row.lstrip().startswith("#")
    ] if len(jobs) == 2 else [])
    if (len(job_header_rows) != 1 or not re.fullmatch(
            r"  (?:source-admission|source-negative):", job_header_rows[0]
    )):
        issues.append("missing or duplicate source-negative CI job")
    # GitHub Actions metadata can change the execution source even when the
    # pinned actions and a visible Python command remain unchanged.
    root_keys = re.findall(r"(?m)^([A-Za-z][A-Za-z0-9_-]*):", source)
    if root_keys != ["name", "on", "permissions", "jobs"]:
        issues.append("unreviewed workflow-level execution metadata")
    # YAML permits whitespace before a mapping colon. A second root-level
    # "on :" or "jobs :" key can shadow the reviewed key while escaping
    # the exact-colon regex above. Pin all live root-level mapping rows.
    top_level_rows = [
        row for row in source.splitlines()
        if row.strip() and not row[0].isspace()
        and not row.lstrip().startswith("#")
    ]
    if (len(top_level_rows) != 4
            or not re.fullmatch(r"name: [^\n]+", top_level_rows[0])
            or top_level_rows[1:] != ["on:", "permissions:", "jobs:"]):
        issues.append("unreviewed workflow-level execution metadata")
    job_keys = (re.findall(r"(?m)^ {4}([A-Za-z][A-Za-z0-9_-]*):", jobs[1])
                if len(jobs) == 2 else [])
    if job_keys != ["if", "permissions", "runs-on", "timeout-minutes", "steps"]:
        issues.append("unreviewed job runner, timeout or execution metadata")
    # A whitespace-before-colon YAML key (e.g. "if : false") can shadow
    # the reviewed job key without matching the adjacent-colon inventory.
    job_rows = ([
        row for row in jobs[1].splitlines()
        if re.match(r"^ {4}\S", row) and not row.lstrip().startswith("#")
    ] if len(jobs) == 2 else [])
    if any(not re.match(
            r"^ {4}(?:if|permissions|runs-on|timeout-minutes|steps):", row
    ) for row in job_rows):
        issues.append("unreviewed job runner, timeout or execution metadata")
    if len(jobs) == 2 and (
            "    runs-on: ubuntu-latest" not in jobs[1].splitlines() or
            "    timeout-minutes: 5" not in jobs[1].splitlines()):
        issues.append("unreviewed job runner or timeout value")
    step_keys = (re.findall(r"(?m)^ {8}([A-Za-z][A-Za-z0-9_-]*):", jobs[1])
                 if len(jobs) == 2 else [])
    if any(key not in {"with", "name", "env", "run"} for key in step_keys):
        issues.append("unreviewed step execution metadata")
    # GitHub parses "if : false", "continue-on-error : true" and "run :"
    # as live step metadata, although the exact-colon key regex misses them.
    step_rows = ([
        row for row in jobs[1].splitlines()
        if re.match(r"^ {8}\S", row) and not row.lstrip().startswith("#")
    ] if len(jobs) == 2 else [])
    if any(not re.match(r"^ {8}(?:with|name|env|run):", row)
           for row in step_rows):
        issues.append("unreviewed step execution metadata")
    if f"    {SOURCE_NEGATIVE_JOB_CONDITION}" not in source.splitlines():
        issues.append("missing reviewed live PR/push job condition")
    if not re.search(r"(?m)^permissions:\n  contents: read$", source):
        issues.append("missing read-only workflow permissions")
    if re.search(r"(?m)^ {8}if:\s*\S+", source):
        issues.append("conditional CI step may skip source-negative validator")
    if re.search(r"(?m)^\s+continue-on-error:\s*(?!false\s*$)\S+", source):
        issues.append("CI validator failure may be suppressed by continue-on-error")
    if "persist-credentials: false" not in source:
        issues.append("checkout may retain credentials")
    if "git rev-parse HEAD" not in source or "git status --porcelain" not in source:
        issues.append("missing exact clean source verification")
    # GITHUB_ENV/GITHUB_PATH persist across steps; a later literal Python line
    # does not prove interpreter identity if an earlier step changed its env.
    if re.search(r"\bGITHUB_(?:PATH|ENV)\b", source):
        issues.append("cross-step CI command resolution may be overridden")
    if re.search(r"(?m)^ {2,10}(?:PATH|PYTHONPATH|BASH_ENV|ENV):\s*\S+", source):
        issues.append("CI interpreter environment may be overridden")
    # A custom shell can exit zero without running the reviewed run block;
    # defaults may silently override even steps without an explicit shell key.
    if re.search(r"(?m)^ {0,8}defaults:\s*$", source):
        issues.append("unreviewed workflow/job shell defaults")
    if re.search(r"(?m)^ {4,10}shell:\s*\S+", source):
        issues.append("unreviewed CI step shell override")
    # Pin every executable action step, including the four legacy checkout
    # pins and the single reviewed setup-go exception.
    alternate_checkout_workflows = {
        ".github/workflows/live-load-gofmt-source-negative.yml",
        ".github/workflows/load-missing-evidence-source-negative.yml",
        ".github/workflows/metrics-authority-source-negative.yml",
        ".github/workflows/observability-access-source-negative.yml",
    }
    checkout_sha = (
        "11bd71901bbe5b1630ceea73d27597364c9af683"
        if relative in alternate_checkout_workflows
        else "11d5960a326750d5838078e36cf38b85af677262"
    )
    expected_actions = [
        f"actions/checkout@{checkout_sha}",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
    ]
    if relative == ".github/workflows/live-object-stage-source-negative.yml":
        expected_actions.append(
            "actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5"
        )
    actual_actions = re.findall(r"(?m)^ {6}- uses: (\S+)\s*$", source)
    all_action_keys = re.findall(r"(?m)^\s*(?:-\s*)?uses:\s*\S+", source)
    if len(actual_actions) != len(all_action_keys) or actual_actions != expected_actions:
        issues.append("unreviewed or shadowed CI action invocation")
    # A pinned checkout action still needs the exact PR-head/push-source ref
    # and no credential/token/duplicate-key overrides in its with block.
    source_lines = source.splitlines()
    # Extra or folded run steps can execute outside the reviewed source
    # verification and validator steps, after all visible checks have passed.
    # Three workflows have a separately reviewed third Go/migration step.
    reviewed_third_run = {
        ".github/workflows/live-object-stage-source-negative.yml",
        ".github/workflows/local-migration-recovery-source-negative.yml",
        ".github/workflows/migration-evidence-registry-source-negative.yml",
    }
    expected_run_count = 3 if relative in reviewed_third_run else 2
    actual_run_rows = [
        row for row in source_lines if re.match(r"^ {8}run:", row)
    ]
    if actual_run_rows != ["        run: |"] * expected_run_count:
        issues.append("unreviewed, missing or folded source-negative CI run step")
    # The only reviewed environment mapping is the PR-head binding in the
    # exact-source verification step. Extra env blocks or shadowed keys can
    # replace Python command resolution or the checked-out source identity.
    env_indices = [i for i, row in enumerate(source_lines) if row == "        env:"]
    if (len(env_indices) != 1 or
            source_lines[env_indices[0] + 1:env_indices[0] + 3] != [
                "          PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}",
                "        run: |",
            ]):
        issues.append("unreviewed step environment or PR-head SHA binding")
    if sum(bool(re.match(r"^\s*env:", row)) for row in source_lines) != 1:
        issues.append("shadowed workflow, job or step environment")
    # A textual git rev-parse substring is not proof that the checked-out
    # PR-head/push SHA is actually compared before the validator runs.
    head_test = '          test "$(git rev-parse HEAD)" = "$expected"'
    clean_test = '          test -z "$(git status --porcelain)"'
    head_positions = [i for i, row in enumerate(source_lines) if row == head_test]
    # The reviewed source-verification shell must run first. A later
    # verification step cannot establish the source already used by Python.
    run_positions = [
        i for i, row in enumerate(source_lines) if row == "        run: |"
    ]
    python_positions = [
        i for i, row in enumerate(source_lines)
        if re.fullmatch(
            r" {10,}python(?:3)?(?: -B)? scripts/[A-Za-z0-9_./-]+\.py\s*", row
        )
    ]
    if len(run_positions) >= 2 and len(head_positions) == 1:
        if not (run_positions[0] < head_positions[0] < run_positions[1]):
            issues.append("exact-source verification must precede validator execution")
        second_run_end = (
            run_positions[2] if len(run_positions) > 2 else len(source_lines)
        )
        # The migration-evidence workflow alone runs an additional negative
        # validator inside a disposable exact-source clone in its third step.
        # Still require at least one direct validator in the reviewed second.
        third_python_allowed = (
            relative == ".github/workflows/migration-evidence-registry-source-negative.yml"
            and len(run_positions) == 3
        )
        if (not any(run_positions[1] < i < second_run_end
                    for i in python_positions)
                or any(not (
                    run_positions[1] < i < second_run_end
                    or (third_python_allowed and run_positions[2] < i)
                ) for i in python_positions)):
            issues.append("direct Python validators escaped reviewed run-step order")
    # The sole reviewed third-step Python exception executes inside a
    # disposable clone checked out at the already verified source HEAD.
    # Bind the complete clone shell, not just the presence of a Python line.
    migration_relative = ".github/workflows/migration-evidence-registry-source-negative.yml"
    if relative == migration_relative:
        if len(run_positions) != 3:
            issues.append("missing reviewed migration clone run step")
        else:
            clone_lines = [
                row for row in source_lines[run_positions[2] + 1:] if row.strip()
            ]
            expected_clone_lines = [
                "          set -euo pipefail",
                '          sandbox="$(mktemp -d)"',
                '          trap \'rm -rf "$sandbox"\' EXIT',
                '          git clone --quiet --no-hardlinks --no-checkout . "$sandbox/repo"',
                '          git -C "$sandbox/repo" checkout --quiet --detach "$(git rev-parse HEAD)"',
                "          (",
                '            cd "$sandbox/repo"',
                "            python scripts/validate-memory-os-migration-evidence-registry-reconcile-authority-negative.py",
                "            git diff --check",
                "            git diff --exit-code",
                '            test -z "$(git status --porcelain)"',
                "          )",
                '          test -z "$(git status --porcelain)"',
            ]
            if clone_lines != expected_clone_lines:
                issues.append("unreviewed migration disposable clone source or shell")
    # Bind the reviewed Go-only third step to actual tests and clean checks.
    if relative == ".github/workflows/live-object-stage-source-negative.yml":
        expected_go_shell = [
            "          set -euo pipefail",
            "          (cd services/import-api && go test ./internal/httpserver -run '^(TestLiveObjectStageLabelClosedVocabulary|TestAtomicLocalLoadResultWriter)$' -count=1)",
            "          git diff --check",
            "          git diff --exit-code",
            '          test -z "$(git status --porcelain)"',
        ]
        if (len(run_positions) != 3 or
                [row for row in source_lines[run_positions[2] + 1:] if row.strip()]
                != expected_go_shell):
            issues.append("unreviewed Go third-step test or clean-source shell")
    # Bind the reviewed local recovery clone to an exact source and shell.
    if relative == ".github/workflows/local-migration-recovery-source-negative.yml":
        expected_local_shell = [
            "          set -euo pipefail",
            '          temp="$(mktemp -d)"',
            '          trap \'rm -rf "$temp"\' EXIT',
            '          git clone --no-hardlinks --no-checkout . "$temp/repo"',
            '          git -C "$temp/repo" checkout --detach "$(git rev-parse HEAD)"',
            '          test -z "$(git -C "$temp/repo" status --porcelain)"',
            '          (cd "$temp/repo" && python scripts/validate-memory-os-local-migration-recovery-artifact-reconcile-negative.py)',
            '          test -z "$(git -C "$temp/repo" status --porcelain)"',
            '          test -z "$(git status --porcelain)"',
        ]
        if (len(run_positions) != 3 or
                [row for row in source_lines[run_positions[2] + 1:] if row.strip()]
                != expected_local_shell):
            issues.append("unreviewed local migration disposable clone source or shell")
    # Every reviewed second run step is a closed sequence of direct Python
    # validators followed by read-only clean-source checks. A new command
    # before, between or after those checks must not execute unnoticed.
    # The example fixture also exercises a deliberately nested positive shell;
    # use a separate real-path positive fixture below for this strict rule.
    if len(run_positions) >= 2 and relative != ".github/workflows/example-source-negative.yml":
        step_end = next(
            (i for i in range(run_positions[1] + 1, len(source_lines))
             if source_lines[i].startswith("      - ")),
            len(source_lines),
        )
        second_shell = [
            row for row in source_lines[run_positions[1] + 1:step_end]
            if row.strip() and not row.lstrip().startswith("#")
        ]
        second_python = [
            row for row in second_shell
            if re.fullmatch(
                r" {10,}python(?:3)?(?: -B)? scripts/[A-Za-z0-9_./-]+\.py\s*",
                row,
            )
        ]
        reviewed_shell = ["          set -euo pipefail", *second_python]
        if "          git diff --check" in second_shell:
            reviewed_shell.append("          git diff --check")
        reviewed_shell.extend([
            "          git diff --exit-code",
            '          test -z "$(git status --porcelain)"',
        ])
        if second_shell != reviewed_shell:
            issues.append("unreviewed second-step shell command or execution order")
    if len(head_positions) != 1:
        issues.append("missing, shadowed or duplicated exact-source HEAD comparison")
    else:
        head_position = head_positions[0]
        guard_start = max(
            (i for i, row in enumerate(source_lines[:head_position])
             if row == "        run: |"), default=-1
        )
        if guard_start < 0:
            issues.append("exact-source verification has no executable shell block")
        else:
            guard_end = next(
                (i for i in range(guard_start + 1, len(source_lines))
                 if source_lines[i].startswith("      - ")),
                len(source_lines),
            )
            guard_lines = [
                row for row in source_lines[guard_start + 1:guard_end] if row.strip()
            ]
            no_echo = relative in {
                ".github/workflows/operability-admission-inventory-atomic-write-source-negative.yml",
                ".github/workflows/operability-admission-inventory-transactional-source-negative.yml",
            }
            expected_pr = ('            expected="${PR_HEAD_SHA:-}"'
                           if relative.endswith("atomic-write-source-negative.yml")
                           else '            expected="$PR_HEAD_SHA"')
            expected_guard = [
                "          set -euo pipefail",
                '          if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" ]]; then',
                '            test "${GITHUB_BASE_REF:-}" = "so"',
                expected_pr,
                '          elif [[ "${GITHUB_EVENT_NAME:-}" == "push" ]]; then',
                '            test "${GITHUB_REF:-}" = "refs/heads/so"',
                '            expected="${GITHUB_SHA:-}"',
                "          else",
            ]
            if not no_echo:
                expected_guard.append('            echo "Unreviewed EVENT" >&2')
            expected_guard.extend([
                "            exit 1",
                "          fi",
                '          [[ "$expected" =~ ^[0-9a-f]{40}$ ]]',
                head_test,
                clean_test,
            ])
            normalized = [
                ('            echo "Unreviewed EVENT" >&2'
                 if re.fullmatch(
                     r'            echo "Unreviewed [A-Za-z0-9 _-]+" >&2', row
                 ) else row)
                for row in guard_lines
            ]
            if normalized != expected_guard:
                issues.append("unreviewed or bypassed PR-head/push exact-source shell")
    checkout_indices = [
        index for index, row in enumerate(source_lines)
        if row.startswith("      - uses: actions/checkout@")
    ]
    if len(checkout_indices) != 1:
        issues.append("missing or duplicate checkout settings authority")
    else:
        checkout_settings = []
        for row in source_lines[checkout_indices[0] + 1:]:
            if row.startswith("      - "):
                break
            if row.strip():
                checkout_settings.append(row)
        expected_checkout_settings = [
            "        with:",
            "          ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}",
            "          fetch-depth: 1",
            "          persist-credentials: false",
        ]
        if checkout_settings != expected_checkout_settings:
            issues.append("checkout ref, depth or credential authority drift")
    # setup-python's pinned Action is insufficient if its with mapping is
    # changed, duplicated or shadowed by another version-selection input.
    python_indices = [
        index for index, row in enumerate(source_lines)
        if row.startswith("      - uses: actions/setup-python@")
    ]
    if len(python_indices) != 1:
        issues.append("missing or duplicate setup-python settings authority")
    else:
        python_settings = []
        for row in source_lines[python_indices[0] + 1:]:
            if row.startswith("      - "):
                break
            if row.strip():
                python_settings.append(row)
        if python_settings != [
            "        with:",
            '          python-version: "3.12"',
        ]:
            issues.append("setup-python interpreter version/input authority drift")
    if relative == ".github/workflows/live-object-stage-source-negative.yml":
        go_indices = [
            index for index, row in enumerate(source_lines)
            if row.startswith("      - uses: actions/setup-go@")
        ]
        if len(go_indices) != 1:
            issues.append("missing or duplicate setup-go settings authority")
        else:
            go_settings = []
            for row in source_lines[go_indices[0] + 1:]:
                if row.startswith("      - "):
                    break
                if row.strip():
                    go_settings.append(row)
            if go_settings != [
                "        with:",
                '          go-version: "1.23.x"',
                "          cache: false",
            ]:
                issues.append("setup-go version/cache input authority drift")

    commands: list[str] = []
    lines = source.splitlines()
    for index, line in enumerate(lines):
        if line != "        run: |":
            continue
        block: list[str] = []
        for child in lines[index + 1:]:
            if child.strip() and not child.startswith("          "):
                break
            block.append(child)
        last_python = -1
        for offset, command in enumerate(block):
            stripped = command.strip()
            if not stripped.startswith(("python ", "python3 ")):
                continue
            # CLI suffixes such as --help/-h can return zero without validation.
            # Bind the complete command, not merely its executable prefix.
            match = re.fullmatch(
                r" {10,}python(?:3)?(?: -B)? (scripts/[A-Za-z0-9_./-]+\.py)\s*",
                command,
            )
            if match is None:
                issues.append("unreviewed/bypassed direct Python command")
                continue
            if "          set -euo pipefail" not in block[:offset]:
                issues.append("Python command lacks preceding fail-closed shell")
            if any(re.fullmatch(r" {10,}(?:exit(?: +0)?|set +\+e)\s*", previous)
                   for previous in block[:offset]):
                issues.append("Python validator unreachable or shell errexit disabled")
            if any(re.match(r" {10,}(?:if|elif|case|while|until|for)\b", previous)
                   for previous in block[:offset]):
                issues.append("Python validator may be conditionally skipped by shell control flow")
            # Shell AND/OR lists may skip a syntactically present validator
            # while the subsequent clean-source checks still exit successfully.
            prior = [row.strip() for row in block[:offset]
                     if row.strip() and not row.lstrip().startswith("#")]
            if (prior and prior[-1].rstrip().removesuffix("\\").rstrip().endswith(("&&", "||"))):
                issues.append("Python validator short-circuited by preceding shell list")
            # A syntactically present command in a heredoc is data, not execution.
            if any(re.search(r"<<-?\s*['\"]?[A-Za-z_][A-Za-z0-9_]*", row)
                   for row in prior):
                issues.append("Python validator may be inert heredoc content")
            # An uninvoked shell function can contain a visible but inert command.
            if any(re.match(
                    r"(?:function\s+)?[A-Za-z_][A-Za-z0-9_]*(?:\s*\(\s*\))?\s*\{",
                    row,
                ) or re.fullmatch(
                    r"(?:function\s+)?[A-Za-z_][A-Za-z0-9_]*\s*\(\s*\)",
                    row,
                ) for row in prior):
                issues.append("Python validator may be trapped in shell function")
            # A visible command can resolve to a shell alias, hash pin or
            # sourced executable instead of the reviewed Python interpreter.
            if any(re.match(
                    r"(?:alias|unalias|hash|source|eval|exec|command|builtin)\b|"
                    r"\.\s|(?:export\s+)?(?:PATH|PYTHONPATH|BASH_ENV|ENV)=",
                    row,
                ) for row in prior):
                issues.append("Python validator command resolution may be overridden")
            # Only the two reviewed temporary-directory EXIT cleanup traps are
            # admitted. Other traps can turn validator failures into exit zero.
            safe_cleanup_traps = (
                "trap 'rm -rf \"$temp\"' EXIT",
                "trap 'rm -rf \"$sandbox\"' EXIT",
            )
            if any(row.startswith("trap ") and row not in safe_cleanup_traps
                   for row in prior):
                issues.append("unreviewed shell trap may mask validator failure")
            commands.append(match.group(1))
            last_python = offset
        if last_python >= 0:
            after = block[last_python + 1:]
            tracked_positions = [
                index for index, row in enumerate(after)
                if re.fullmatch(r" {10,}git diff --exit-code\s*", row)
            ]
            status_positions = [
                index for index, row in enumerate(after)
                if re.match(r" {10,}(?:test -z|\[\[).*git status --porcelain", row)
                and not any(token in row for token in ("||", ";", "&"))
            ]
            if not tracked_positions:
                issues.append("missing post-validator tracked-source clean check")
            if not status_positions:
                issues.append("missing post-validator untracked-source clean check")
            if tracked_positions and status_positions:
                before_clean = after[:max(tracked_positions[0], status_positions[0]) + 1]
                if any(re.fullmatch(
                        r" {10,}(?:exit(?: +0)?|set +\+e)\s*", row)
                        or re.match(r" {10,}(?:if|elif|case|while|until|for)\b", row)
                        for row in before_clean):
                    issues.append("post-validator clean checks unreachable or conditional")
                # A syntactically present git clean-source check can be inert
                # when a preceding shell list skips it or it is only heredoc
                # data, an uninvoked function body, or a trap-masked failure.
                for position in (tracked_positions[0], status_positions[0]):
                    prior = [
                        row.strip() for row in after[:position]
                        if row.strip() and not row.lstrip().startswith("#")
                    ]
                    if prior and prior[-1].rstrip("\\").rstrip().endswith(("&&", "||")):
                        issues.append("post-validator clean check short-circuited")
                        break
                if any(re.search(r"""<<-?\s*['"]?[A-Za-z_][A-Za-z0-9_]*""", row)
                       for row in before_clean):
                    issues.append("post-validator clean check may be inert heredoc data")
                if any(re.match(
                    r" {10,}(?:function\s+)?[A-Za-z_][A-Za-z0-9_]*"
                    r"(?:\s*\(\s*\))?\s*\{", row,
                ) for row in before_clean):
                    issues.append("post-validator clean check may be trapped in shell function")
                if any(row.strip().startswith("trap ") and row.strip() not in (
                    'trap \'rm -rf "$temp"\' EXIT',
                    'trap \'rm -rf "$sandbox"\' EXIT',
                ) for row in before_clean):
                    issues.append("post-validator clean check failure may be trap-masked")
                if any(re.match(
                    r" {10,}(?:alias|unalias|hash|source|eval|exec|command|builtin)\b|"
                    r" {10,}\.\s|"
                    r" {10,}(?:export\s+)?(?:PATH|PYTHONPATH|BASH_ENV|ENV)=",
                    row,
                ) for row in before_clean):
                    issues.append("post-validator clean check shell may be overridden")
    if not commands:
        issues.append("no directly executed Python validator")
    if len(commands) != len(set(commands)):
        issues.append("duplicate direct Python validator invocation")
    for script in commands:
        if not script_exists(script):
            issues.append(f"missing invoked validator: {script}")
        for event in ("pull_request", "push"):
            if script not in paths[event]:
                issues.append(f"{event}: invoked validator not in trigger paths: {script}")
    return issues


EXPECTED_SOURCE_NEGATIVE_FIXTURE_COUNT = 204


def source_negative_fixture_literal_names(source: str) -> tuple[str, ...] | None:
    """Reject shadowed dictionary keys before Python silently overwrites them."""
    try:
        module = ast.parse(source)
    except SyntaxError:
        return None
    functions = [
        node for node in module.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "prove_source_negative_reachability_negatives"
    ]
    if len(functions) != 1:
        return None
    assignments = [
        node.value for node in functions[0].body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "cases"
                for target in node.targets)
    ]
    if len(assignments) != 1 or not isinstance(assignments[0], ast.Dict):
        return None
    keys = assignments[0].keys
    if any(not isinstance(key, ast.Constant) or not isinstance(key.value, str)
           for key in keys):
        return None
    names = tuple(key.value for key in keys)
    return names if len(names) == len(set(names)) else None


def exact_source_negative_diagnostic(expected: str, issues: list[str]) -> bool:
    """Only a complete intended issue is proof; substrings are not evidence."""
    return expected in issues


def prove_source_negative_diagnostic_classifier(failures: list[str]) -> None:
    expected = "intended source-negative guard"
    cases = (
        ("exact", [expected], True),
        ("exact with unrelated", ["unrelated failure", expected], True),
        ("empty", [], False),
        ("unrelated", ["unrelated failure"], False),
        ("prefix collision", [expected + " injected"], False),
        ("suffix collision", ["unrelated " + expected], False),
        ("nested collision", ["unrelated " + expected + " injected"], False),
        ("multiple misleading", [expected + " injected", "unrelated failure"], False),
    )
    for name, issues, accepted in cases:
        if exact_source_negative_diagnostic(expected, issues) is not accepted:
            failures.append(f"source-negative exact diagnostic classifier misclassified: {name}")


def prove_source_negative_reachability_negatives(failures: list[str]) -> None:
    """Positive control plus independent mutations; no digest-only success."""
    prove_source_negative_diagnostic_classifier(failures)
    if failures:
        return
    relative = ".github/workflows/example-source-negative.yml"
    fixture = (
        "name: Example\n"
        "on:\n"
        "  pull_request:\n"
        "    branches: [so]\n"
        "    paths:\n"
        f'      - "{relative}"\n'
        '      - "scripts/check.py"\n'
        "  push:\n"
        "    branches: [so]\n"
        "    paths:\n"
        f'      - "{relative}"\n'
        '      - "scripts/check.py"\n'
        "permissions:\n"
        "  contents: read\n"
        "jobs:\n"
        "  source-admission:\n"
        f"    {SOURCE_NEGATIVE_JOB_CONDITION}\n"
        "    permissions:\n"
        "      contents: read\n"
        "    runs-on: ubuntu-latest\n"
        "    timeout-minutes: 5\n"
        "    steps:\n"
        "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n"
        "        with:\n"
        "          ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n"
        "          fetch-depth: 1\n"
        "          persist-credentials: false\n"
        "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n"
        "        with:\n"
        '          python-version: "3.12"\n'
        "      - name: Verify source\n"
        "        env:\n"
        "          PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}\n"
        "        run: |\n"
        "          set -euo pipefail\n"
        '          if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" ]]; then\n'
        '            test "${GITHUB_BASE_REF:-}" = "so"\n'
        '            expected="$PR_HEAD_SHA"\n'
        '          elif [[ "${GITHUB_EVENT_NAME:-}" == "push" ]]; then\n'
        '            test "${GITHUB_REF:-}" = "refs/heads/so"\n'
        '            expected="${GITHUB_SHA:-}"\n'
        "          else\n"
        '            echo "Unreviewed example source event" >&2\n'
        "            exit 1\n"
        "          fi\n"
        '          [[ "$expected" =~ ^[0-9a-f]{40}$ ]]\n'
        '          test "$(git rev-parse HEAD)" = "$expected"\n'
        '          test -z "$(git status --porcelain)"\n'
        "      - name: Execute negative validator\n"
        "        run: |\n"
        "          set -euo pipefail\n"
        "          python scripts/check.py\n"
        "          git diff --exit-code\n"
        '          test -z "$(git status --porcelain)"\n'
    )
    migration_script = "scripts/validate-memory-os-migration-evidence-registry-reconcile-authority-negative.py"
    local_script = "scripts/validate-memory-os-local-migration-recovery-artifact-reconcile-negative.py"
    exists = lambda script: script in {"scripts/check.py", migration_script, local_script}
    if source_negative_reachability_issues(relative, fixture, exists):
        failures.append("source-negative reachability positive control failed")
        return
    go_relative = ".github/workflows/live-object-stage-source-negative.yml"
    go_fixture = fixture.replace(relative, go_relative).replace(
        "      - name: Verify source\n",
        "      - uses: actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5\n"
        "        with:\n"
        '          go-version: "1.23.x"\n'
        "          cache: false\n"
        "      - name: Verify source\n",
    )
    go_test_sources = (
        "services/import-api/internal/httpserver/live_object_load_test.go",
        "services/import-api/internal/httpserver/live_load_test.go",
        "services/import-api/internal/httpserver/live_result_atomic_test.go",
    )
    go_fixture = go_fixture.replace(
        '      - "scripts/check.py"\n',
        '      - "scripts/check.py"\n'
        + "".join(f'      - "{source}"\n' for source in go_test_sources),
    )
    go_fixture += (
        "      - name: Prove reviewed Go checks\n"
        "        run: |\n"
        "          set -euo pipefail\n"
        "          (cd services/import-api && go test ./internal/httpserver -run '^(TestLiveObjectStageLabelClosedVocabulary|TestAtomicLocalLoadResultWriter)$' -count=1)\n"
        "          git diff --check\n"
        "          git diff --exit-code\n"
        '          test -z "$(git status --porcelain)"\n'
    )
    if source_negative_reachability_issues(go_relative, go_fixture, exists):
        failures.append("source-negative setup-go positive control failed")
        return
    migration_relative = ".github/workflows/migration-evidence-registry-source-negative.yml"
    migration_fixture = fixture.replace(relative, migration_relative).replace(
        '      - "scripts/check.py"\n',
        '      - "scripts/check.py"\n'
        f'      - "{migration_script}"\n',
    )
    migration_fixture += (
        "      - name: Prove lifecycle authority in disposable exact-source clone\n"
        "        run: |\n"
        "          set -euo pipefail\n"
        '          sandbox="$(mktemp -d)"\n'
        '          trap \'rm -rf "$sandbox"\' EXIT\n'
        '          git clone --quiet --no-hardlinks --no-checkout . "$sandbox/repo"\n'
        '          git -C "$sandbox/repo" checkout --quiet --detach "$(git rev-parse HEAD)"\n'
        "          (\n"
        '            cd "$sandbox/repo"\n'
        f"            python {migration_script}\n"
        "            git diff --check\n"
        "            git diff --exit-code\n"
        '            test -z "$(git status --porcelain)"\n'
        "          )\n"
        '          test -z "$(git status --porcelain)"\n'
    )
    if source_negative_reachability_issues(
            migration_relative, migration_fixture, exists):
        failures.append("source-negative migration clone positive control failed")
        return
    local_relative = ".github/workflows/local-migration-recovery-source-negative.yml"
    local_fixture = fixture.replace(relative, local_relative).replace(
        '      - "scripts/check.py"\n',
        '      - "scripts/check.py"\n'
        f'      - "{local_script}"\n',
    )
    local_fixture += (
        "      - name: Prove local recovery in disposable exact-source clone\n"
        "        run: |\n"
        "          set -euo pipefail\n"
        '          temp="$(mktemp -d)"\n'
        '          trap \'rm -rf "$temp"\' EXIT\n'
        '          git clone --no-hardlinks --no-checkout . "$temp/repo"\n'
        '          git -C "$temp/repo" checkout --detach "$(git rev-parse HEAD)"\n'
        '          test -z "$(git -C "$temp/repo" status --porcelain)"\n'
        f'          (cd "$temp/repo" && python {local_script})\n'
        '          test -z "$(git -C "$temp/repo" status --porcelain)"\n'
        '          test -z "$(git status --porcelain)"\n'
    )
    if source_negative_reachability_issues(local_relative, local_fixture, exists):
        failures.append("source-negative local recovery clone positive control failed")
        return
    strict_relative = ".github/workflows/backup-restore-drill-preflight-source-negative.yml"
    strict_fixture = fixture.replace(relative, strict_relative)
    if source_negative_reachability_issues(strict_relative, strict_fixture, exists):
        failures.append("source-negative closed second-step shell positive control failed")
        return
    # An unrelated permission failure must not satisfy a second-step shell
    # negative merely because the overall fixture was rejected.
    unrelated_failure = strict_fixture.replace(
        "permissions:\n  contents: read\n",
        "permissions:\n  contents: write\n", 1,
    )
    unrelated_issues = source_negative_reachability_issues(
        strict_relative, unrelated_failure, exists)
    if (not unrelated_issues or
            "unreviewed second-step shell command or execution order"
            in unrelated_issues):
        failures.append("source-negative diagnostic classifier accepted unrelated failure")
    nested = fixture.replace(
        "          python scripts/check.py",
        "          (\n            python scripts/check.py\n          )",
    )
    if source_negative_reachability_issues(relative, nested, exists):
        failures.append("source-negative nested subshell validator positive control failed")
        return
    # Swapping the two reviewed shell steps must not preserve CI admission.
    def reversed_shell_steps(text: str) -> str:
        before, tail = text.split("      - name: Verify source\n", 1)
        verification, validator = tail.split(
            "      - name: Execute negative validator\n", 1
        )
        post = ""
        marker = "      - name: Prove reviewed Go checks\n"
        if marker in validator:
            validator, post = validator.split(marker, 1)
            post = marker + post
        return (before + "      - name: Execute negative validator\n"
                + validator + "      - name: Verify source\n"
                + verification + post)

    reversed_fixture = reversed_shell_steps(fixture)
    reversed_go_fixture = reversed_shell_steps(go_fixture)
    cases = {
        "setup-go third-step command replaced": go_fixture.replace(
            "(cd services/import-api && go test ./internal/httpserver -run '^(TestLiveObjectStageLabelClosedVocabulary|TestAtomicLocalLoadResultWriter)$' -count=1)",
            "echo skipped-go-tests"),
        "setup-go third-step count removed": go_fixture.replace(
            "-count=1)", ")"),
        "setup-go third-step directory changed": go_fixture.replace(
            "(cd services/import-api && go test", "(cd /tmp && go test"),
        "migration-clone unreviewed remote source": migration_fixture.replace(
            'git clone --quiet --no-hardlinks --no-checkout . "$sandbox/repo"',
            'git clone --quiet --no-hardlinks --no-checkout https://example.invalid/repo "$sandbox/repo"'),
        "migration-clone wrong checkout ref": migration_fixture.replace(
            'checkout --quiet --detach "$(git rev-parse HEAD)"',
            'checkout --quiet --detach main'),
        "migration-clone missing no-hardlinks": migration_fixture.replace(
            "git clone --quiet --no-hardlinks --no-checkout",
            "git clone --quiet --no-checkout"),
        "migration-clone missing source checkout": migration_fixture.replace(
            '          git -C "$sandbox/repo" checkout --quiet --detach "$(git rev-parse HEAD)"\n',
            ""),
        "migration-clone missing sandbox cd": migration_fixture.replace(
            '            cd "$sandbox/repo"\n',
            ""),
        "migration-clone masked clone failure": migration_fixture.replace(
            '          git clone --quiet --no-hardlinks --no-checkout . "$sandbox/repo"\n',
            '          true ||\n'
            '          git clone --quiet --no-hardlinks --no-checkout . "$sandbox/repo"\n'),
        "migration-clone malicious cleanup trap": migration_fixture.replace(
            '          trap \'rm -rf "$sandbox"\' EXIT\n',
            "          trap 'exit 0' ERR\n"),
        "migration-clone missing nested clean check": migration_fixture.replace(
            '            git diff --exit-code\n'
            '            test -z "$(git status --porcelain)"\n',
            '            git diff --exit-code\n'),
        "local-clone unreviewed remote source": local_fixture.replace(
            'git clone --no-hardlinks --no-checkout . "$temp/repo"',
            'git clone --no-hardlinks --no-checkout https://example.invalid/repo "$temp/repo"'),
        "local-clone wrong checkout ref": local_fixture.replace(
            'checkout --detach "$(git rev-parse HEAD)"',
            'checkout --detach main'),
        "local-clone missing no-hardlinks": local_fixture.replace(
            'git clone --no-hardlinks --no-checkout',
            'git clone --no-checkout'),
        "local-clone missing checkout": local_fixture.replace(
            '          git -C "$temp/repo" checkout --detach "$(git rev-parse HEAD)"\n',
            ""),
        "local-clone missing pre-validator clean check": local_fixture.replace(
            '          test -z "$(git -C "$temp/repo" status --porcelain)"\n'
            '          (cd "$temp/repo" && python',
            '          (cd "$temp/repo" && python'),
        "local-clone wrong execution directory": local_fixture.replace(
            '(cd "$temp/repo" && python',
            '(cd /tmp && python'),
        "local-clone validator replaced by echo": local_fixture.replace(
            f'(cd "$temp/repo" && python {local_script})',
            'echo skipped-local-recovery-validator'),
        "local-clone malicious cleanup trap": local_fixture.replace(
            '          trap \'rm -rf "$temp"\' EXIT\n',
            "          trap 'exit 0' ERR\n"),
        "local-clone missing post-validator clean check": local_fixture.replace(
            f'          (cd "$temp/repo" && python {local_script})\n'
            '          test -z "$(git -C "$temp/repo" status --porcelain)"\n',
            f'          (cd "$temp/repo" && python {local_script})\n'),
        "local-clone missing parent clean check": local_fixture.replace(
            '          test -z "$(git -C "$temp/repo" status --porcelain)"\n'
            '          test -z "$(git status --porcelain)"\n',
            '          test -z "$(git -C "$temp/repo" status --porcelain)"\n'),
        "strict-shell post-clean arbitrary command": strict_fixture + (
            "          echo unreviewed-after-clean\n"),
        "strict-shell pre-validator arbitrary command": strict_fixture.replace(
            "          python scripts/check.py\n",
            "          echo unreviewed-before-validator\n"
            "          python scripts/check.py\n"),
        "strict-shell post-validator arbitrary command": strict_fixture.replace(
            "          python scripts/check.py\n"
            "          git diff --exit-code\n",
            "          python scripts/check.py\n"
            "          touch /tmp/unreviewed\n"
            "          git diff --exit-code\n"),
        "strict-shell duplicate tracked clean check": strict_fixture.replace(
            "          git diff --exit-code\n",
            "          git diff --exit-code\n"
            "          git diff --exit-code\n"),
        "strict-shell reversed clean checks": strict_fixture.replace(
            '          git diff --exit-code\n'
            '          test -z "$(git status --porcelain)"\n',
            '          test -z "$(git status --porcelain)"\n'
            '          git diff --exit-code\n'),
        "strict-shell function after clean check": strict_fixture + (
            "          bypass() { echo unreviewed; }\n"),
        "strict-shell unreviewed check after clean": strict_fixture + (
            "          git diff --check\n"),
        "setup-go PR missing first test source trigger": go_fixture.replace(
            f'      - "{go_test_sources[0]}"\n', "", 1),
        "setup-go push missing first test source trigger": "".join(
            go_fixture.rsplit(f'      - "{go_test_sources[0]}"\n', 1)),
        "setup-go missing second test source trigger": go_fixture.replace(
            f'      - "{go_test_sources[1]}"\n', ""),
        "local-clone PR missing independent validator trigger": local_fixture.replace(
            f'      - "{local_script}"\n', "", 1),
        "local-clone push missing independent validator trigger": "".join(
            local_fixture.rsplit(f'      - "{local_script}"\n', 1)),
        "validator precedes source verification": reversed_fixture,
        "setup-go validator precedes source verification": reversed_go_fixture,
        "extra shell run step after validator": fixture + (
            "      - name: Unreviewed extra shell\n"
            "        run: |\n"
            "          echo unreviewed\n"),
        "folded extra shell run step": fixture + (
            "      - name: Unreviewed folded shell\n"
            "        run: >\n"
            "          echo unreviewed\n"),
        "extra shell run step before validator": fixture.replace(
            "      - name: Execute negative validator\n",
            "      - name: Unreviewed early shell\n"
            "        run: |\n"
            "          echo unreviewed\n"
            "      - name: Execute negative validator\n"),
        "duplicate validator run metadata": fixture.replace(
            "      - name: Execute negative validator\n"
            "        run: |\n",
            "      - name: Execute negative validator\n"
            "        run: |\n"
            "        run: |\n"),
        "folded validator run scalar": fixture.replace(
            "      - name: Execute negative validator\n"
            "        run: |\n",
            "      - name: Execute negative validator\n"
            "        run: >\n"),
        "folded source verification run scalar": fixture.replace(
            "      - name: Verify source\n"
            "        env:\n"
            "          PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}\n"
            "        run: |\n",
            "      - name: Verify source\n"
            "        env:\n"
            "          PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}\n"
            "        run: >\n"),
        "setup-go extra shell run step": go_fixture + (
            "      - name: Unreviewed Go shell\n"
            "        run: |\n"
            "          echo unreviewed\n"),
        "setup-go folded third run scalar": go_fixture.replace(
            "      - name: Prove reviewed Go checks\n"
            "        run: |\n",
            "      - name: Prove reviewed Go checks\n"
            "        run: >\n"),
        "tracked clean check skipped by true-or": fixture.replace(
            "          git diff --exit-code\n",
            "          true ||\n          git diff --exit-code\n"),
        "tracked clean check skipped by false-and": fixture.replace(
            "          git diff --exit-code\n",
            "          false &&\n          git diff --exit-code\n"),
        "untracked clean check skipped by true-or": fixture.replace(
            '          test -z "$(git status --porcelain)"\n'
            '      - name: Execute negative validator\n',
            '          test -z "$(git status --porcelain)"\n'
            '      - name: Execute negative validator\n').replace(
            '          git diff --exit-code\n'
            '          test -z "$(git status --porcelain)"\n',
            '          git diff --exit-code\n'
            '          true ||\n'
            '          test -z "$(git status --porcelain)"\n'),
        "untracked clean check skipped by false-and": fixture.replace(
            '          git diff --exit-code\n'
            '          test -z "$(git status --porcelain)"\n',
            '          git diff --exit-code\n'
            '          false &&\n'
            '          test -z "$(git status --porcelain)"\n'),
        "tracked clean check inert in heredoc": fixture.replace(
            "          git diff --exit-code\n",
            "          cat <<'CLEAN_CHECK'\n"
            "          git diff --exit-code\n"
            "          CLEAN_CHECK\n"),
        "untracked clean check inert in heredoc": fixture.replace(
            '          git diff --exit-code\n'
            '          test -z "$(git status --porcelain)"\n',
            '          git diff --exit-code\n'
            "          cat <<'CLEAN_CHECK'\n"
            '          test -z "$(git status --porcelain)"\n'
            "          CLEAN_CHECK\n"),
        "tracked clean check trapped in function": fixture.replace(
            "          git diff --exit-code\n",
            "          clean_check() {\n"
            "          git diff --exit-code\n"
            "          }\n"),
        "untracked clean check trapped in function": fixture.replace(
            '          git diff --exit-code\n'
            '          test -z "$(git status --porcelain)"\n',
            '          git diff --exit-code\n'
            '          clean_check() {\n'
            '          test -z "$(git status --porcelain)"\n'
            '          }\n'),
        "post-validator failure masked by ERR trap": fixture.replace(
            "          git diff --exit-code\n",
            "          trap 'exit 0' ERR\n"
            "          git diff --exit-code\n"),
        "post-validator shell overridden by eval": fixture.replace(
            "          git diff --exit-code\n",
            '          eval "set +e"\n'
            "          git diff --exit-code\n"),
        "comment-only source HEAD comparison": fixture.replace(
            '          test "$(git rev-parse HEAD)" = "$expected"\n',
            '          # test "$(git rev-parse HEAD)" = "$expected"\n'),
        "echo-only source HEAD comparison": fixture.replace(
            '          test "$(git rev-parse HEAD)" = "$expected"\n',
            '          echo test "$(git rev-parse HEAD)" = "$expected"\n'),
        "inverted source HEAD comparison": fixture.replace(
            '          test "$(git rev-parse HEAD)" = "$expected"\n',
            '          test "$(git rev-parse HEAD)" != "$expected"\n'),
        "source HEAD comparison short-circuited": fixture.replace(
            '          test "$(git rev-parse HEAD)" = "$expected"\n',
            '          true ||\n          test "$(git rev-parse HEAD)" = "$expected"\n'),
        "source HEAD comparison under false branch": fixture.replace(
            '          test "$(git rev-parse HEAD)" = "$expected"\n',
            '          if false; then\n'
            '          test "$(git rev-parse HEAD)" = "$expected"\n'
            '          fi\n'),
        "source verification early exit": fixture.replace(
            '          test "$(git rev-parse HEAD)" = "$expected"\n',
            '          exit 0\n          test "$(git rev-parse HEAD)" = "$expected"\n'),
        "source verification disabled errexit": fixture.replace(
            '          test "$(git rev-parse HEAD)" = "$expected"\n',
            '          set +e\n          test "$(git rev-parse HEAD)" = "$expected"\n'),
        "source verification wrong PR expected": fixture.replace(
            '            expected="$PR_HEAD_SHA"\n',
            '            expected="${GITHUB_SHA:-}"\n'),
        "source verification wrong push expected": fixture.replace(
            '            expected="${GITHUB_SHA:-}"\n',
            '            expected="$PR_HEAD_SHA"\n'),
        "source verification disabled event rejection": fixture.replace(
            '            echo "Unreviewed example source event" >&2\n'
            '            exit 1\n',
            '            echo "Unreviewed example source event" >&2\n'
            '            exit 0\n'),
        "source verification extra shell command": fixture.replace(
            '          test "$(git rev-parse HEAD)" = "$expected"\n',
            '          eval "true"\n          test "$(git rev-parse HEAD)" = "$expected"\n'),
        "source verification missing clean check": fixture.replace(
            '          test -z "$(git status --porcelain)"\n'
            '      - name: Execute negative validator\n',
            '      - name: Execute negative validator\n'),
        "source verification duplicate HEAD comparison": fixture.replace(
            '          test "$(git rev-parse HEAD)" = "$expected"\n',
            '          test "$(git rev-parse HEAD)" = "$expected"\n'
            '          test "$(git rev-parse HEAD)" = "$expected"\n'),
        "source verification unreviewed echo substitution": fixture.replace(
            '            echo "Unreviewed example source event" >&2\n',
            '            echo "Unreviewed $(true) source event" >&2\n'),
        "workflow concurrency cancellation": fixture.replace(
            "permissions:\n", "concurrency:\n  group: unreviewed\npermissions:\n", 1),
        "workflow environment override": fixture.replace(
            "permissions:\n", "env:\n  PYTHONPATH: /tmp\npermissions:\n", 1),
        "job runner override": fixture.replace(
            "    runs-on: ubuntu-latest\n", "    runs-on: self-hosted\n"),
        "job timeout override": fixture.replace(
            "    timeout-minutes: 5\n", "    timeout-minutes: 1\n"),
        "job container override": fixture.replace(
            "    timeout-minutes: 5\n",
            "    timeout-minutes: 5\n    container: unreviewed/image\n"),
        "job environment override": fixture.replace(
            "    runs-on: ubuntu-latest\n",
            "    env:\n      PYTHONPATH: /tmp\n    runs-on: ubuntu-latest\n"),
        "job strategy override": fixture.replace(
            "    runs-on: ubuntu-latest\n",
            "    strategy:\n      matrix:\n        os: [ubuntu-latest]\n    runs-on: ubuntu-latest\n"),
        "step working directory override": fixture.replace(
            "      - name: Execute negative validator\n",
            "      - name: Execute negative validator\n        working-directory: /tmp\n"),
        "step id override": fixture.replace(
            "      - name: Execute negative validator\n",
            "      - name: Execute negative validator\n        id: unreviewed\n"),
        "step environment override": fixture.replace(
            "      - name: Execute negative validator\n",
            "      - name: Execute negative validator\n        env:\n          PYTHONPATH: /tmp\n"),
        "duplicate PR-head environment binding": fixture.replace(
            "          PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}\n",
            "          PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}\n"
            "          PR_HEAD_SHA: ${{ github.sha }}\n"),
        "altered PR-head environment binding": fixture.replace(
            "          PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}\n",
            "          PR_HEAD_SHA: ${{ github.sha }}\n"),
        "step false continue-on-error override": fixture.replace(
            "      - name: Execute negative validator\n",
            "      - name: Execute negative validator\n        continue-on-error: false\n"),
        "step timeout override": fixture.replace(
            "      - name: Execute negative validator\n",
            "      - name: Execute negative validator\n        timeout-minutes: 1\n"),
        "workflow defaults override": fixture.replace(
            "permissions:\n", "defaults:\n  run:\n    shell: bash\npermissions:\n", 1),
        "duplicate top-level on authority": fixture + "on:\n  workflow_dispatch:\n",
        "quoted shadow on authority": fixture + "'on':\n  workflow_dispatch:\n",
        "spaced shadow on authority": fixture + "on :\n  workflow_dispatch:\n",
        "spaced shadow jobs authority": fixture + "jobs : {}\n",
        "spaced shadow job condition": fixture.replace(
            "    runs-on: ubuntu-latest\n",
            "    if : false\n    runs-on: ubuntu-latest\n"),
        "spaced shadow job permissions": fixture.replace(
            "    permissions:\n      contents: read\n",
            "    permissions:\n      contents: read\n"
            "    permissions : {contents: write}\n"),
        "spaced shadow validator condition": fixture.replace(
            "      - name: Execute negative validator\n",
            "      - name: Execute negative validator\n        if : false\n"),
        "spaced shadow validator continue-on-error": fixture.replace(
            "      - name: Execute negative validator\n",
            "      - name: Execute negative validator\n"
            "        continue-on-error : true\n"),
        "spaced shadow validator run": fixture + "        run : echo skipped\n",
        "spaced shadow source-negative job": fixture + "  source-admission : {}\n",
        "quoted shadow source-negative job": fixture + "  'source-admission': {}\n",
        "spaced unreviewed extra job": fixture + "  unreviewed : {}\n",
        "spaced shadow workflow contents permission": fixture.replace(
            "permissions:\n  contents: read\n",
            "permissions:\n  contents: read\n  contents : write\n", 1),
        "quoted shadow workflow contents permission": fixture.replace(
            "permissions:\n  contents: read\n",
            "permissions:\n  contents: read\n  'contents': write\n", 1),
        "spaced shadow job contents permission": fixture.replace(
            "    permissions:\n      contents: read\n",
            "    permissions:\n      contents: read\n      contents : write\n", 1),
        "quoted shadow job contents permission": fixture.replace(
            "    permissions:\n      contents: read\n",
            "    permissions:\n      contents: read\n      'contents': write\n", 1),
        "unreviewed PR paths-ignore filter": fixture.replace(
            "    paths:\n", "    paths-ignore:\n      - 'scripts/**'\n    paths:\n", 1),
        "unreviewed push branches-ignore filter": fixture.replace(
            "  push:\n    branches: [so]\n",
            "  push:\n    branches: [so]\n    branches-ignore:\n      - so\n"),
        "extra PR branch": fixture.replace(
            "  pull_request:\n    branches: [so]\n",
            "  pull_request:\n    branches: [so, main]\n"),
        "duplicate push branch filter": fixture.replace(
            "  push:\n    branches: [so]\n",
            "  push:\n    branches: [so]\n    branches: [main]\n"),
        "conditional validator with true shell branch": fixture.replace(
            "          python scripts/check.py\n",
            "          if true; then\n          python scripts/check.py\n          fi\n"),
        "conditional validator with event shell branch": fixture.replace(
            "          python scripts/check.py\n",
            '          if [[ "$GITHUB_EVENT_NAME" == "workflow_dispatch" ]]; then\n'
            "          python scripts/check.py\n          fi\n"),
        "validator skipped by true-or shell list": fixture.replace(
            "          python scripts/check.py\n",
            "          true ||\n          python scripts/check.py\n"),
        "validator skipped by false-and shell list": fixture.replace(
            "          python scripts/check.py\n",
            "          false &&\n          python scripts/check.py\n"),
        "validator inert in cat heredoc": fixture.replace(
            "          python scripts/check.py\n",
            "          cat <<'VALIDATOR_TEXT'\n"
            "          python scripts/check.py\n"
            "          VALIDATOR_TEXT\n"),
        "validator inert in noop heredoc": fixture.replace(
            "          python scripts/check.py\n",
            "          : <<'VALIDATOR_TEXT'\n"
            "          python scripts/check.py\n"
            "          VALIDATOR_TEXT\n"),
        "validator trapped in shell function": fixture.replace(
            "          python scripts/check.py\n",
            "          validate() {\n"
            "          python scripts/check.py\n"
            "          }\n"),
        "validator trapped in function keyword": fixture.replace(
            "          python scripts/check.py\n",
            "          function validate {\n"
            "          python scripts/check.py\n"
            "          }\n"),
        "validator trapped in multiline function": fixture.replace(
            "          python scripts/check.py\n",
            "          validate()\n"
            "          {\n"
            "          python scripts/check.py\n"
            "          }\n"),
        "validator shadowed by python alias": fixture.replace(
            "          python scripts/check.py\n",
            "          alias python=true\n"
            "          python scripts/check.py\n"),
        "validator shadowed by hash pin": fixture.replace(
            "          python scripts/check.py\n",
            "          hash -p /bin/true python\n"
            "          python scripts/check.py\n"),
        "validator shadowed by sourced shell": fixture.replace(
            "          python scripts/check.py\n",
            "          source ./unreviewed.sh\n"
            "          python scripts/check.py\n"),
        "validator shadowed by PATH assignment": fixture.replace(
            "          python scripts/check.py\n",
            "          PATH=/tmp/unreviewed\n"
            "          python scripts/check.py\n"),
        "validator shadowed by exported PYTHONPATH": fixture.replace(
            "          python scripts/check.py\n",
            "          export PYTHONPATH=/tmp/unreviewed\n"
            "          python scripts/check.py\n"),
        "validator shadowed by eval": fixture.replace(
            "          python scripts/check.py\n",
            '          eval "alias python=true"\n'
            "          python scripts/check.py\n"),
        "workflow interpreter env override": fixture.replace(
            "permissions:\n",
            "env:\n  PYTHONPATH: /tmp/unreviewed\npermissions:\n", 1),
        "job interpreter env override": fixture.replace(
            "    permissions:\n      contents: read\n",
            "    env:\n      PATH: /tmp/unreviewed\n    permissions:\n      contents: read\n", 1),
        "validator step interpreter env override": fixture.replace(
            "      - name: Execute negative validator\n",
            "      - name: Execute negative validator\n"
            "        env:\n          BASH_ENV: /tmp/unreviewed\n"),
        "earlier step writes GITHUB_PATH": fixture.replace(
            "      - name: Execute negative validator\n",
            '          echo "/tmp/unreviewed" >> "$GITHUB_PATH"\n'
            "      - name: Execute negative validator\n"),
        "earlier step writes GITHUB_ENV": fixture.replace(
            "      - name: Execute negative validator\n",
            '          echo "PYTHONPATH=/tmp/unreviewed" >> "$GITHUB_ENV"\n'
            "      - name: Execute negative validator\n"),
        "ERR trap masks validator failure": fixture.replace(
            "          python scripts/check.py\n",
            "          trap 'exit 0' ERR\n"
            "          python scripts/check.py\n"),
        "EXIT trap masks validator failure": fixture.replace(
            "          python scripts/check.py\n",
            "          trap 'exit 0' EXIT\n"
            "          python scripts/check.py\n"),
        "DEBUG trap masks validator failure": fixture.replace(
            "          python scripts/check.py\n",
            "          trap 'exit 0' DEBUG\n"
            "          python scripts/check.py\n"),
        "RETURN trap masks validator failure": fixture.replace(
            "          python scripts/check.py\n",
            "          trap 'exit 0' RETURN\n"
            "          python scripts/check.py\n"),
        "unreviewed EXIT cleanup trap": fixture.replace(
            "          python scripts/check.py\n",
            "          trap 'rm -rf /tmp/unreviewed' EXIT\n"
            "          python scripts/check.py\n"),
        "validator step shell override": fixture.replace(
            "      - name: Execute negative validator\n",
            "      - name: Execute negative validator\n"
            "        shell: /bin/true {0}\n"),
        "post-run validator shell override": fixture + "        shell: /bin/true {0}\n",
        "source verification step shell override": fixture.replace(
            "      - name: Verify source\n",
            "      - name: Verify source\n"
            "        shell: /bin/true {0}\n"),
        "workflow default shell override": fixture.replace(
            "permissions:\n",
            "defaults:\n  run:\n    shell: /bin/true {0}\npermissions:\n", 1),
        "job default shell override": fixture.replace(
            "    permissions:\n      contents: read\n",
            "    defaults:\n      run:\n        shell: /bin/true {0}\n"
            "    permissions:\n      contents: read\n", 1),
        "floating checkout action": fixture.replace(
            "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
            "actions/checkout@v4", 1),
        "substituted checkout action pin": fixture.replace(
            "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
            "actions/checkout@0000000000000000000000000000000000000000", 1),
        "floating setup-python action": fixture.replace(
            "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
            "actions/setup-python@v5", 1),
        "extra unreviewed action step": fixture.replace(
            "      - name: Execute negative validator\n",
            "      - uses: unreviewed/action@main\n"
            "      - name: Execute negative validator\n"),
        "duplicate setup-python action": fixture.replace(
            "      - name: Execute negative validator\n",
            "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n"
            "      - name: Execute negative validator\n"),
        "unreviewed setup-go action": fixture.replace(
            "      - name: Execute negative validator\n",
            "      - uses: actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5\n"
            "      - name: Execute negative validator\n"),
        "alternate checkout in wrong workflow": fixture.replace(
            "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
            "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683", 1),
        "shadowed action uses key": fixture.replace(
            "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n",
            "        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n", 1),
        "checkout ref switched to branch": fixture.replace(
            "          ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n",
            "          ref: main\n", 1),
        "duplicate checkout ref key": fixture.replace(
            "          ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n",
            "          ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n"
            "          ref: main\n", 1),
        "missing checkout ref key": fixture.replace(
            "          ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n", "", 1),
        "checkout fetch-depth widened": fixture.replace(
            "          fetch-depth: 1\n",
            "          fetch-depth: 0\n", 1),
        "checkout credentials retained": fixture.replace(
            "          persist-credentials: false\n",
            "          persist-credentials: true\n", 1),
        "duplicate checkout credential key": fixture.replace(
            "          persist-credentials: false\n",
            "          persist-credentials: false\n"
            "          persist-credentials: true\n", 1),
        "checkout token override": fixture.replace(
            "          persist-credentials: false\n",
            "          persist-credentials: false\n"
            "          token: unreviewed\n", 1),
        "setup-python version changed": fixture.replace(
            '          python-version: "3.12"\n',
            '          python-version: "2.7"\n', 1),
        "duplicate setup-python version": fixture.replace(
            '          python-version: "3.12"\n',
            '          python-version: "3.12"\n'
            '          python-version: "2.7"\n', 1),
        "missing setup-python version": fixture.replace(
            '          python-version: "3.12"\n', "", 1),
        "setup-python cache override": fixture.replace(
            '          python-version: "3.12"\n',
            '          python-version: "3.12"\n'
            "          cache: pip\n", 1),
        "setup-python version file override": fixture.replace(
            '          python-version: "3.12"\n',
            '          python-version: "3.12"\n'
            "          python-version-file: .python-version\n", 1),
        "missing setup-python with block": fixture.replace(
            "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n"
            "        with:\n",
            "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n", 1),
        "setup-go version changed": go_fixture.replace(
            '          go-version: "1.23.x"\n',
            '          go-version: "1.22.x"\n', 1),
        "setup-go duplicate version": go_fixture.replace(
            '          go-version: "1.23.x"\n',
            '          go-version: "1.23.x"\n'
            '          go-version: "1.22.x"\n', 1),
        "setup-go missing version": go_fixture.replace(
            '          go-version: "1.23.x"\n', "", 1),
        "setup-go cache enabled": go_fixture.replace(
            "          cache: false\n",
            "          cache: true\n", 1),
        "setup-go missing cache authority": go_fixture.replace(
            "          cache: false\n", "", 1),
        "setup-go extra input": go_fixture.replace(
            "          cache: false\n",
            "          cache: false\n"
            "          token: unreviewed\n", 1),
        "validator inside shell loop": fixture.replace(
            "          python scripts/check.py\n",
            "          for attempt in 1; do\n          python scripts/check.py\n          done\n"),
        "validator inside shell case": fixture.replace(
            "          python scripts/check.py\n",
            '          case "$GITHUB_EVENT_NAME" in\n'
            "          push)\n          python scripts/check.py\n          ;;\n          esac\n"),
        "conditional tracked clean check": fixture.replace(
            "          python scripts/check.py\n          git diff --exit-code\n",
            '          python scripts/check.py\n          if [[ "$GITHUB_EVENT_NAME" == "push" ]]; then\n'
            "          git diff --exit-code\n          fi\n"),
        "masked post-validator untracked check": fixture.replace(
            '          git diff --exit-code\n          test -z "$(git status --porcelain)"\n',
            '          git diff --exit-code\n          test -z "$(git status --porcelain)" || true\n'),
        "masked post-validator tracked check": fixture.replace(
            "          git diff --exit-code\n", "          git diff --exit-code || true\n"),
        "exit before post-validator clean check": fixture.replace(
            "          python scripts/check.py\n          git diff --exit-code\n",
            "          python scripts/check.py\n          exit 0\n          git diff --exit-code\n"),
        "errexit disabled after validator": fixture.replace(
            "          python scripts/check.py\n          git diff --exit-code\n",
            "          python scripts/check.py\n          set +e\n          git diff --exit-code\n"),
        "conditional post-validator clean checks": fixture.replace(
            '          python scripts/check.py\n          git diff --exit-code\n'
            '          test -z "$(git status --porcelain)"\n',
            '          python scripts/check.py\n          if false; then\n'
            '          git diff --exit-code\n          test -z "$(git status --porcelain)"\n'
            '          fi\n'),
        "duplicate job-level condition": fixture.replace(
            f"    {SOURCE_NEGATIVE_JOB_CONDITION}\n",
            f"    {SOURCE_NEGATIVE_JOB_CONDITION}\n    if: false\n"),
        "duplicate workflow permissions": fixture + "\npermissions:\n  contents: write\n",
        "duplicate workflow contents permission": fixture.replace(
            "permissions:\n  contents: read\n",
            "permissions:\n  contents: read\n  contents: write\n"),
        "elevated job permissions": fixture.replace(
            "    permissions:\n      contents: read\n",
            "    permissions:\n      contents: write\n"),
        "duplicate job permissions": fixture.replace(
            "    permissions:\n      contents: read\n",
            "    permissions:\n      contents: read\n    permissions:\n      contents: write\n"),
        "shadow source-negative CI job": fixture + "  unreviewed-job:\n    if: false\n",
        "missing post-validator tracked check": fixture.replace(
            "          git diff --exit-code\n", ""),
        "missing post-validator untracked check": fixture.replace(
            '          git diff --exit-code\n          test -z "$(git status --porcelain)"\n',
            "          git diff --exit-code\n"),
        "commented post-validator tracked check": fixture.replace(
            "          git diff --exit-code\n", "          # git diff --exit-code\n"),
        "post-validator checks moved before execution": fixture.replace(
            '          python scripts/check.py\n          git diff --exit-code\n'
            '          test -z "$(git status --porcelain)"\n',
            '          git diff --exit-code\n          test -z "$(git status --porcelain)"\n'
            '          python scripts/check.py\n'),
        "disabled validator step": fixture.replace(
            "      - name: Execute negative validator\n",
            "      - name: Execute negative validator\n        if: false\n"),
        "unreviewed event conditional step": fixture.replace(
            "      - name: Execute negative validator\n",
            "      - name: Execute negative validator\n        if: github.event_name == 'workflow_dispatch'\n"),
        "unconditional early exit": fixture.replace(
            "          python scripts/check.py",
            "          exit 0\n          python scripts/check.py"),
        "errexit disabled before validator": fixture.replace(
            "          python scripts/check.py",
            "          set +e\n          python scripts/check.py"),
        "step continue-on-error": fixture.replace(
            "      - name: Execute negative validator\n",
            "      - name: Execute negative validator\n        continue-on-error: true\n"),
        "disabled shell branch": fixture.replace(
            "          python scripts/check.py",
            "          if false; then\n          python scripts/check.py\n          fi"),
        "nested masked validator failure": nested.replace(
            "            python scripts/check.py",
            "            python scripts/check.py || true"),
        "PR missing validator trigger": fixture.replace(
            '      - "scripts/check.py"', '      - "scripts/other.py"', 1),
        "push missing workflow self-trigger": fixture.replace(
            '  push:\n    branches: [so]\n    paths:\n'
            f'      - "{relative}"',
            '  push:\n    branches: [so]\n    paths:\n'
            '      - "unreviewed/workflow.yml"'),
        "commented validator": fixture.replace(
            "          python scripts/check.py", "          # python scripts/check.py"),
        "echo-only validator": fixture.replace(
            "          python scripts/check.py", "          echo python scripts/check.py"),
        "missing validator": fixture.replace(
            "          python scripts/check.py", "          python scripts/missing.py"),
        "disabled job": fixture.replace(
            f"    {SOURCE_NEGATIVE_JOB_CONDITION}", "    if: false"),
        "write permission": fixture.replace(
            "permissions:\n  contents: read", "permissions:\n  contents: write"),
        "retained checkout credentials": fixture.replace(
            "          persist-credentials: false", "          persist-credentials: true"),
        "missing exact HEAD check": fixture.replace(
            '          test "$(git rev-parse HEAD)" = "$expected"\n', ""),
        "missing shell fail closed": fixture.replace(
            "          set -euo pipefail\n          python scripts/check.py",
            "          python scripts/check.py"),
        "unreviewed extra script": fixture.replace(
            "          python scripts/check.py",
            "          python scripts/check.py\n          python scripts/unreviewed.py"),
        "help-only validator execution": fixture.replace(
            "          python scripts/check.py\n",
            "          python scripts/check.py --help\n"),
        "short-help validator execution": fixture.replace(
            "          python scripts/check.py\n",
            "          python scripts/check.py -h\n"),
        "validator with unreviewed repo root": fixture.replace(
            "          python scripts/check.py\n",
            "          python scripts/check.py --repo-root /tmp\n"),
        "validator output redirected": fixture.replace(
            "          python scripts/check.py\n",
            "          python scripts/check.py > /dev/null\n"),
        "masked validator failure": fixture.replace(
            "          python scripts/check.py", "          python scripts/check.py || true"),
        "missing push event": fixture.replace("  push:\n", "  workflow_dispatch:\n"),
        "duplicate trigger path": fixture.replace(
            '      - "scripts/check.py"\n  push:',
            '      - "scripts/check.py"\n      - "scripts/check.py"\n  push:'),
        "PR negative path excludes validator": fixture.replace(
            '      - "scripts/check.py"\n  push:',
            '      - "scripts/check.py"\n      - "!scripts/check.py"\n  push:'),
        "push negative path excludes validator": fixture.replace(
            '      - "scripts/check.py"\npermissions:',
            '      - "scripts/check.py"\n      - "!scripts/check.py"\npermissions:'),
    }
    own_source = Path(__file__).read_text(encoding="utf-8")
    literal_names = source_negative_fixture_literal_names(own_source)
    if literal_names is None or len(literal_names) != len(cases):
        failures.append("source-negative fixture literal names are shadowed or missing")
    # A duplicate source-level dict key must fail even if the resulting dict
    # happens to have the expected number of entries.
    duplicate_probe = own_source.replace(
        '"validator inside shell loop":',
        '"validator inert in cat heredoc":', 1,
    )
    if (duplicate_probe == own_source
            or source_negative_fixture_literal_names(duplicate_probe) is not None):
        failures.append("source-negative duplicate literal-key negative escaped")
    if len(cases) != EXPECTED_SOURCE_NEGATIVE_FIXTURE_COUNT:
        failures.append(f"source-negative fixture inventory drift: expected {EXPECTED_SOURCE_NEGATIVE_FIXTURE_COUNT}, got {len(cases)}")
    # Reviewed action and toolchain inputs are source authority too. Bind
    # their negatives to the exact failing invariant, not an unrelated error.
    checkout_input_cases = {
        "checkout ref switched to branch",
        "duplicate checkout ref key",
        "missing checkout ref key",
        "checkout fetch-depth widened",
        "checkout credentials retained",
        "duplicate checkout credential key",
        "checkout token override",
        "retained checkout credentials",
    }
    python_input_cases = {
        "setup-python version changed",
        "duplicate setup-python version",
        "missing setup-python version",
        "setup-python cache override",
        "setup-python version file override",
        "missing setup-python with block",
    }
    go_input_cases = {
        "setup-go version changed",
        "setup-go duplicate version",
        "setup-go missing version",
        "setup-go cache enabled",
        "setup-go missing cache authority",
        "setup-go extra input",
    }
    action_invocation_cases = {
        "floating checkout action",
        "substituted checkout action pin",
        "floating setup-python action",
        "extra unreviewed action step",
        "duplicate setup-python action",
        "unreviewed setup-go action",
        "alternate checkout in wrong workflow",
        "shadowed action uses key",
    }
    workflow_metadata_cases = {
        "workflow concurrency cancellation",
        "workflow environment override",
        "workflow defaults override",
        "workflow default shell override",
        "spaced shadow on authority",
        "spaced shadow jobs authority",
    }
    job_header_cases = {
        "spaced shadow source-negative job",
        "quoted shadow source-negative job",
        "spaced unreviewed extra job",
    }
    job_metadata_cases = {
        "job container override",
        "job environment override",
        "job strategy override",
        "job default shell override",
        "spaced shadow job condition",
        "spaced shadow job permissions",
    }
    job_runner_cases = {"job runner override", "job timeout override"}
    step_metadata_cases = {
        "step working directory override",
        "step id override",
        "step false continue-on-error override",
        "step timeout override",
        "spaced shadow validator condition",
        "spaced shadow validator continue-on-error",
        "spaced shadow validator run",
        "validator step shell override",
        "source verification step shell override",
    }
    workflow_permission_cases = {"duplicate workflow permissions"}
    workflow_contents_cases = {
        "duplicate workflow contents permission",
        "spaced shadow workflow contents permission",
        "quoted shadow workflow contents permission",
    }
    readonly_permission_cases = {"write permission"}
    job_permission_cases = {
        "elevated job permissions",
        "duplicate job permissions",
        "spaced shadow job contents permission",
        "quoted shadow job contents permission",
    }
    # A malformed event filter or a skipped source-negative job must fail for
    # its intended CI-reachability invariant, not an unrelated metadata check.
    event_filter_cases = {
        "duplicate top-level on authority",
        "quoted shadow on authority",
        "unreviewed PR paths-ignore filter",
        "unreviewed push branches-ignore filter",
        "extra PR branch",
        "duplicate push branch filter",
        "missing push event",
        "duplicate trigger path",
        "PR negative path excludes validator",
        "push negative path excludes validator",
    }
    source_trigger_cases = {
        "PR missing validator trigger":
            "pull_request: invoked validator not in trigger paths: scripts/check.py",
        "push missing workflow self-trigger":
            "push: source-negative workflow not self-triggered",
    }
    conditional_step_cases = {
        "disabled validator step",
        "unreviewed event conditional step",
    }
    job_condition_cases = {
        "duplicate job-level condition":
            "duplicate or missing job-level event condition",
        "disabled job": "missing reviewed live PR/push job condition",
    }
    direct_command_cases = {
        "help-only validator execution",
        "short-help validator execution",
        "validator with unreviewed repo root",
        "validator output redirected",
    }
    heredoc_cases = {
        "validator inert in cat heredoc",
        "validator inert in noop heredoc",
    }
    function_cases = {
        "validator trapped in shell function",
        "validator trapped in function keyword",
        "validator trapped in multiline function",
    }
    resolution_cases = {
        "validator shadowed by python alias",
        "validator shadowed by hash pin",
        "validator shadowed by sourced shell",
        "validator shadowed by PATH assignment",
        "validator shadowed by exported PYTHONPATH",
        "validator shadowed by eval",
    }
    trap_cases = {
        "ERR trap masks validator failure",
        "EXIT trap masks validator failure",
        "DEBUG trap masks validator failure",
        "RETURN trap masks validator failure",
        "unreviewed EXIT cleanup trap",
    }
    short_circuit_cases = {
        "validator skipped by true-or shell list",
        "validator skipped by false-and shell list",
    }
    conditional_shell_cases = {
        "conditional validator with true shell branch",
        "conditional validator with event shell branch",
        "validator inside shell loop",
        "validator inside shell case",
    }
    clean_short_circuit_cases = {
        "tracked clean check skipped by true-or",
        "tracked clean check skipped by false-and",
        "untracked clean check skipped by true-or",
        "untracked clean check skipped by false-and",
    }
    clean_heredoc_cases = {
        "tracked clean check inert in heredoc",
        "untracked clean check inert in heredoc",
    }
    clean_function_cases = {
        "tracked clean check trapped in function",
        "untracked clean check trapped in function",
    }
    head_cardinality_cases = {
        "comment-only source HEAD comparison",
        "echo-only source HEAD comparison",
        "inverted source HEAD comparison",
        "source verification duplicate HEAD comparison",
    }
    source_guard_cases = {
        "source HEAD comparison short-circuited",
        "source HEAD comparison under false branch",
        "source verification early exit",
        "source verification disabled errexit",
        "source verification wrong PR expected",
        "source verification wrong push expected",
        "source verification disabled event rejection",
        "source verification extra shell command",
        "source verification missing clean check",
        "source verification unreviewed echo substitution",
    }
    run_step_cases = {
        "extra shell run step after validator",
        "folded extra shell run step",
        "extra shell run step before validator",
        "duplicate validator run metadata",
        "folded validator run scalar",
        "folded source verification run scalar",
        "setup-go extra shell run step",
        "setup-go folded third run scalar",
    }
    step_environment_cases = {
        "step environment override",
        "duplicate PR-head environment binding",
        "altered PR-head environment binding",
    }
    interpreter_environment_cases = {
        "workflow interpreter env override",
        "job interpreter env override",
        "validator step interpreter env override",
    }
    cross_step_environment_cases = {
        "earlier step writes GITHUB_PATH",
        "earlier step writes GITHUB_ENV",
    }
    remaining_clean_conditional_cases = {
        "conditional tracked clean check",
        "exit before post-validator clean check",
        "errexit disabled after validator",
        "conditional post-validator clean checks",
    }
    remaining_missing_tracked_cases = {
        "masked post-validator tracked check",
        "missing post-validator tracked check",
        "commented post-validator tracked check",
        "post-validator checks moved before execution",
    }
    remaining_missing_untracked_cases = {
        "masked post-validator untracked check",
        "missing post-validator untracked check",
    }
    remaining_unreachable_validator_cases = {
        "unconditional early exit",
        "errexit disabled before validator",
    }
    remaining_inert_validator_cases = {
        "commented validator",
        "echo-only validator",
    }
    remaining_masked_command_cases = {
        "nested masked validator failure",
        "masked validator failure",
    }
    remaining_missing_invocation_cases = {
        "missing validator",
        "unreviewed extra script",
    }
    diagnostic_bound = 0
    for name, mutation in cases.items():
        if name.startswith("setup-go "):
            case_relative, baseline = go_relative, go_fixture
        elif name.startswith("migration-clone "):
            case_relative, baseline = migration_relative, migration_fixture
        elif name.startswith("local-clone "):
            case_relative, baseline = local_relative, local_fixture
        elif name.startswith("strict-shell "):
            case_relative, baseline = strict_relative, strict_fixture
        else:
            case_relative, baseline = relative, fixture
        issues = source_negative_reachability_issues(case_relative, mutation, exists)
        if mutation == baseline or not issues:
            failures.append(f"source-negative reachability negative escaped: {name}")
            continue
        expected_issue = None
        if name.startswith("strict-shell "):
            expected_issue = "unreviewed second-step shell command or execution order"
        elif name.startswith("migration-clone "):
            expected_issue = "unreviewed migration disposable clone source or shell"
        elif name.startswith("local-clone "):
            if name == "local-clone PR missing independent validator trigger":
                expected_issue = "pull_request: local recovery third-step validator trigger missing"
            elif name == "local-clone push missing independent validator trigger":
                expected_issue = "push: local recovery third-step validator trigger missing"
            else:
                expected_issue = "unreviewed local migration disposable clone source or shell"
        elif name.startswith("setup-go third-step "):
            expected_issue = "unreviewed Go third-step test or clean-source shell"
        elif name.startswith("setup-go ") and "test source trigger" in name:
            event = "push" if "push" in name else "pull_request"
            source_name = "live_load_test.go" if "second" in name else "live_object_load_test.go"
            expected_issue = (
                f"{event}: reviewed Go test source trigger missing: "
                f"services/import-api/internal/httpserver/{source_name}"
            )
        if name in checkout_input_cases:
            expected_issue = "checkout ref, depth or credential authority drift"
        elif name in python_input_cases:
            expected_issue = "setup-python interpreter version/input authority drift"
        elif name in go_input_cases:
            expected_issue = "setup-go version/cache input authority drift"
        elif name in action_invocation_cases:
            expected_issue = "unreviewed or shadowed CI action invocation"
        elif name in workflow_metadata_cases:
            expected_issue = "unreviewed workflow-level execution metadata"
        elif name in job_header_cases:
            expected_issue = "missing or duplicate source-negative CI job"
        elif name in job_metadata_cases:
            expected_issue = "unreviewed job runner, timeout or execution metadata"
        elif name in job_runner_cases:
            expected_issue = "unreviewed job runner or timeout value"
        elif name in step_metadata_cases:
            expected_issue = "unreviewed step execution metadata"
        elif name in workflow_permission_cases:
            expected_issue = "duplicate or missing workflow permissions key"
        elif name in workflow_contents_cases:
            expected_issue = "duplicate or missing workflow contents permission"
        elif name in readonly_permission_cases:
            expected_issue = "missing read-only workflow permissions"
        elif name in job_permission_cases:
            expected_issue = "duplicate, missing or elevated job permissions"
        elif name in event_filter_cases:
            expected_issue = "missing/ambiguous PR and push path-filter authority"
        elif name in source_trigger_cases:
            expected_issue = source_trigger_cases[name]
        elif name in conditional_step_cases:
            expected_issue = "conditional CI step may skip source-negative validator"
        elif name in job_condition_cases:
            expected_issue = job_condition_cases[name]
        elif name == "missing exact HEAD check":
            expected_issue = "missing, shadowed or duplicated exact-source HEAD comparison"
        elif name in direct_command_cases:
            expected_issue = "unreviewed/bypassed direct Python command"
        elif name in heredoc_cases:
            expected_issue = "Python validator may be inert heredoc content"
        elif name in function_cases:
            expected_issue = "Python validator may be trapped in shell function"
        elif name in resolution_cases:
            expected_issue = "Python validator command resolution may be overridden"
        elif name in trap_cases:
            expected_issue = "unreviewed shell trap may mask validator failure"
        elif name in short_circuit_cases:
            expected_issue = "Python validator short-circuited by preceding shell list"
        elif name in conditional_shell_cases:
            expected_issue = "Python validator may be conditionally skipped by shell control flow"
        elif name in clean_short_circuit_cases:
            expected_issue = "post-validator clean check short-circuited"
        elif name in clean_heredoc_cases:
            expected_issue = "post-validator clean check may be inert heredoc data"
        elif name in clean_function_cases:
            expected_issue = "post-validator clean check may be trapped in shell function"
        elif name == "post-validator failure masked by ERR trap":
            expected_issue = "post-validator clean check failure may be trap-masked"
        elif name == "post-validator shell overridden by eval":
            expected_issue = "post-validator clean check shell may be overridden"
        elif name in head_cardinality_cases:
            expected_issue = "missing, shadowed or duplicated exact-source HEAD comparison"
        elif name in source_guard_cases:
            expected_issue = "unreviewed or bypassed PR-head/push exact-source shell"
        elif name == "validator precedes source verification":
            expected_issue = "exact-source verification must precede validator execution"
        elif name in run_step_cases:
            expected_issue = "unreviewed, missing or folded source-negative CI run step"
        elif name in step_environment_cases:
            expected_issue = "unreviewed step environment or PR-head SHA binding"
        elif name in interpreter_environment_cases:
            expected_issue = "CI interpreter environment may be overridden"
        elif name in cross_step_environment_cases:
            expected_issue = "cross-step CI command resolution may be overridden"
        elif name == "post-run validator shell override":
            expected_issue = "unreviewed step execution metadata"
        elif name == "shadow source-negative CI job":
            expected_issue = "missing or duplicate source-negative CI job"
        elif name == "step continue-on-error":
            expected_issue = "CI validator failure may be suppressed by continue-on-error"
        elif name in remaining_clean_conditional_cases:
            expected_issue = "post-validator clean checks unreachable or conditional"
        elif name in remaining_missing_tracked_cases:
            expected_issue = "missing post-validator tracked-source clean check"
        elif name in remaining_missing_untracked_cases:
            expected_issue = "missing post-validator untracked-source clean check"
        elif name in remaining_unreachable_validator_cases:
            expected_issue = "Python validator unreachable or shell errexit disabled"
        elif name in remaining_inert_validator_cases:
            expected_issue = "no directly executed Python validator"
        elif name in remaining_masked_command_cases:
            expected_issue = "unreviewed/bypassed direct Python command"
        elif name in remaining_missing_invocation_cases:
            missing_script = ("scripts/missing.py" if name == "missing validator"
                              else "scripts/unreviewed.py")
            expected_issue = f"missing invoked validator: {missing_script}"
        elif name == "disabled shell branch":
            expected_issue = "Python validator may be conditionally skipped by shell control flow"
        elif name == "missing shell fail closed":
            expected_issue = "Python command lacks preceding fail-closed shell"
        elif name == "setup-go validator precedes source verification":
            expected_issue = "exact-source verification must precede validator execution"
        if expected_issue is not None:
            diagnostic_bound += 1
            # A prefix, suffix or unrelated diagnostic containing the
            # expected words is not proof of the intended rejection.
            if not exact_source_negative_diagnostic(expected_issue, issues):
                failures.append(
                    f"source-negative negative rejected for wrong reason: {name}: {issues}"
                )
    if diagnostic_bound != 204:
        failures.append(
            f"source-negative diagnostic-bound fixture inventory drift: {diagnostic_bound}"
        )


def validate_source_negative_ci_reachability(failures: list[str]) -> None:
    """Independent inventory and live CI command checks, not production evidence."""
    workflows = REPO_ROOT / ".github/workflows"
    observed = tuple(sorted(
        path.relative_to(REPO_ROOT).as_posix()
        for path in workflows.glob("*-source-negative.yml")
    ))
    if observed != SOURCE_NEGATIVE_WORKFLOW_NAMES:
        missing = sorted(set(SOURCE_NEGATIVE_WORKFLOW_NAMES) - set(observed))
        extra = sorted(set(observed) - set(SOURCE_NEGATIVE_WORKFLOW_NAMES))
        failures.append(f"source-negative CI workflow inventory drift: missing={missing} extra={extra}")
        return
    prove_source_negative_reachability_negatives(failures)
    if failures:
        return
    invocation_count = 0
    for relative in observed:
        path = REPO_ROOT / relative
        if path.is_symlink() or not path.is_file():
            failures.append(f"source-negative workflow is missing/symlink: {relative}")
            continue
        source = path.read_text(encoding="utf-8")
        issues = source_negative_reachability_issues(
            relative, source,
            lambda script: (REPO_ROOT / script).is_file()
            and not (REPO_ROOT / script).is_symlink(),
        )
        failures.extend(f"{relative}: {issue}" for issue in issues)
        invocation_count += len(re.findall(
            r"(?m)^ {10,}python(?:3)?(?: -B)? scripts/[A-Za-z0-9_./-]+\.py",
            source,
        ))
    if not failures:
        print(f"source-negative CI reachability verified: {len(observed)} workflows, "
              f"{invocation_count} direct Python commands, "
              f"{EXPECTED_SOURCE_NEGATIVE_FIXTURE_COUNT} negative fixtures")



# The autonomous learning workflow is itself a CI authority. Unlike the 52
# source-negative workflows, it has a dispatch event and an append-only step.
# Bind that reviewed execution path separately so its guard cannot disappear.
LEARNING_WORKFLOW_SOURCE = REPO_ROOT / ".github/workflows/autonomous-learning-guard.yml"
LEARNING_WORKFLOW_REVIEWED_BLOB = "732d664fb157cbe2d25309d2030906d6386cc97c"


def validate_learning_workflow_source(source: str, *, check_blob: bool = True) -> None:
    """Require the reviewed read-only learning/append-only CI path."""
    roots = [
        line for line in source.splitlines()
        if line.strip() and not line[0].isspace()
        and not line.lstrip().startswith("#")
    ]
    if roots != [
        "name: Autonomous Learning Guard", "on:", "permissions:",
        "concurrency:", "jobs:",
    ]:
        raise ValueError("learning workflow root authority drift")
    if not source.startswith("name: Autonomous Learning Guard\n\non:\n"):
        raise ValueError("learning workflow event authority drift")
    events = source.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]
    event_rows = [
        line for line in events.splitlines()
        if line.startswith("  ") and not line.startswith("   ")
        and line.strip() and not line.lstrip().startswith("#")
    ]
    if event_rows != ["  push:", "  pull_request:", "  workflow_dispatch:"]:
        raise ValueError("learning workflow event authority drift")
    for marker in (
        "  push:\n    branches: [so]\n    paths:\n",
        "  pull_request:\n    branches: [so]\n    paths:\n",
        "  workflow_dispatch:\n",
    ):
        if source.count(marker) != 1:
            raise ValueError("learning workflow event authority drift")
    for trigger in (
        "scripts/validate-memory-os-entry-docs.py",
        "scripts/" + "validate-autonomous-learning-system.py",
        "scripts/" + "validate-autonomous-learning-system-negative.py",
        ".github/workflows/autonomous-learning-guard.yml",
    ):
        if source.count('      - "' + trigger + '"\n') != 2:
            raise ValueError("learning workflow self-trigger authority drift")
    permission = source.split("\npermissions:\n", 1)[1].split("\nconcurrency:\n", 1)[0]
    if permission != "  contents: read\n":
        raise ValueError("learning workflow read-only permission drift")
    concurrency = source.split("\nconcurrency:\n", 1)[1].split("\njobs:\n", 1)[0]
    group = "  group: autonomous-learning-guard-" + chr(36) + "{{ github.sha }}\n"
    if concurrency != group + "  cancel-in-progress: false\n":
        raise ValueError("learning workflow concurrency authority drift")
    jobs = source.split("\njobs:\n", 1)[1]
    job_rows = [
        line for line in jobs.splitlines()
        if line.startswith("  ") and not line.startswith("   ")
        and line.strip() and not line.lstrip().startswith("#")
    ]
    job_keys = [
        line for line in jobs.splitlines()
        if line.startswith("    ") and not line.startswith("     ")
        and line.strip() and not line.lstrip().startswith("#")
    ]
    if job_rows != ["  validate:"] or job_keys != [
        "    runs-on: ubuntu-latest", "    timeout-minutes: 10", "    steps:",
    ]:
        raise ValueError("learning workflow job execution authority drift")
    for required, count in (
        ("      - name: Enforce append-only learning authority against parent\n", 1),
        ("      - name: Validate learning contract and executable negatives\n", 1),
        ("      - name: Confirm read-only execution\n", 1),
        ("          python -B scripts/" + "validate-autonomous-learning-system.py\n", 1),
        ("          python -B scripts/" + "validate-autonomous-learning-system-negative.py\n", 1),
        ("          python -B scripts/" + "validate-memory-os-entry-docs.py\n", 1),
        ("          git diff --exit-code\n", 1),
        ('          test -z "$(git status --porcelain)"\n', 2),
    ):
        if source.count(required) != count:
            raise ValueError("learning workflow executable guard reachability drift")
    if check_blob:
        payload = source.encode("utf-8")
        digest = hashlib.sha1(
            b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        ).hexdigest()
        if digest != LEARNING_WORKFLOW_REVIEWED_BLOB:
            raise ValueError("learning workflow complete reviewed source drift")


def validate_learning_workflow_reachability(failures: list[str]) -> None:
    """Exercise distinct semantic negatives before accepting the reviewed blob."""
    try:
        source = LEARNING_WORKFLOW_SOURCE.read_text(encoding="utf-8")
        validate_learning_workflow_source(source)
        cases = (
            ("extra event", "on:\n", "on:\n  issues:\n",
             "learning workflow event authority drift"),
            ("missing push self-trigger",
             '      - "scripts/validate-memory-os-entry-docs.py"\n', "",
             "learning workflow self-trigger authority drift"),
            ("permission escalation", "permissions:\n  contents: read\n",
             "permissions:\n  contents: write\n",
             "learning workflow read-only permission drift"),
            ("cancel active run", "  cancel-in-progress: false\n",
             "  cancel-in-progress: true\n",
             "learning workflow concurrency authority drift"),
            ("job permission shadow", "    runs-on: ubuntu-latest\n",
             "    permissions:\n      contents: write\n    runs-on: ubuntu-latest\n",
             "learning workflow job execution authority drift"),
            ("append-only step removed",
             "      - name: Enforce append-only learning authority against parent\n", "",
             "learning workflow executable guard reachability drift"),
            ("negative guard removed",
             "          python -B scripts/" + "validate-autonomous-learning-system-negative.py\n", "",
             "learning workflow executable guard reachability drift"),
            ("post-validator diff removed", "          git diff --exit-code\n", "",
             "learning workflow executable guard reachability drift"),
            ("unreviewed executable step",
             "      - name: Confirm read-only execution\n",
             "      - run: echo unreviewed\n      - name: Confirm read-only execution\n",
             "learning workflow complete reviewed source drift"),
        )
        for label, old, replacement, diagnostic in cases:
            if source.count(old) != (2 if label == "missing push self-trigger" else 1):
                raise ValueError("learning workflow fixture anchor drift: " + label)
            changed = source.replace(old, replacement, 1)
            if changed == source:
                raise ValueError("learning workflow unchanged negative: " + label)
            try:
                validate_learning_workflow_source(
                    changed, check_blob=label == "unreviewed executable step"
                )
            except ValueError as exc:
                if str(exc) != diagnostic:
                    raise ValueError(
                        "learning workflow wrong negative diagnostic: "
                        + label + ": " + str(exc)
                    ) from exc
            else:
                raise ValueError("learning workflow mutation accepted: " + label)
    except (OSError, UnicodeError, ValueError) as exc:
        failures.append("autonomous learning workflow guard failed: " + str(exc))
    else:
        print("autonomous learning workflow source verified: 9 exact-diagnostic negatives")




# The upload-route publisher/PR still have an overbroad rate-limit trigger.
# This is a bounded, read-only regression guard, not permission to edit their
# reviewed workflows or to retry the unchanged external MinIO image blocker.
UPLOAD_ROUTE_RATE_LIMIT_CORE = "scripts/validate-memory-os-rate-limit.py"
UPLOAD_ROUTE_RATE_LIMIT_WILDCARD = "scripts/validate-memory-os-rate-limit*.py"
UPLOAD_ROUTE_REVIEWED_WILDCARD_MATCHES = frozenset((
    "scripts/validate-memory-os-rate-limit-authority-negative.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime-evidence-binding-negative.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime-generation-authority-negative.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime-reconcile-negative.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime-registry-negative.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime-validator-authority-negative.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime-workflow-source-negative.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime-writer-authority-negative.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime.py",
    "scripts/validate-memory-os-rate-limit-emergency-drill-reconcile-negative.py",
    "scripts/validate-memory-os-rate-limit-emergency-drill.py",
    "scripts/validate-memory-os-rate-limit-local-multiprocess-shared-store-authority-negative.py",
    "scripts/validate-memory-os-rate-limit-local-multiprocess-shared-store-reconcile-negative.py",
    "scripts/validate-memory-os-rate-limit-local-multiprocess-shared-store-transport-negative.py",
    "scripts/validate-memory-os-rate-limit-local-multiprocess-shared-store.py",
    "scripts/validate-memory-os-rate-limit-operation-evidence-authority-negative.py",
    "scripts/validate-memory-os-rate-limit-operation-evidence-reconcile-negative.py",
    "scripts/validate-memory-os-rate-limit-operation-evidence.py",
    "scripts/validate-memory-os-rate-limit-operation-reconcile-authority-negative.py",
    "scripts/validate-memory-os-rate-limit-operation-writer-authority-negative.py",
    "scripts/validate-memory-os-rate-limit-operation-writer-negative.py",
    "scripts/validate-memory-os-rate-limit-operations-reconcile-negative.py",
    "scripts/validate-memory-os-rate-limit-operations-source-negative.py",
    "scripts/validate-memory-os-rate-limit-operations.py",
    "scripts/validate-memory-os-rate-limit.py",
))
UPLOAD_ROUTE_WORKFLOWS = (
    ".github/workflows/reconcile-upload-route-authority.yml",
    ".github/workflows/reconcile-upload-route-authority-pr.yml",
)
# Confirmed direct inputs of scripts/validate-memory-os-rate-limit.py.
# This is a lower bound, NOT a proven Python/Go transitive closure.
UPLOAD_ROUTE_RATE_LIMIT_DIRECT_INPUTS = (
    "docs/fixtures/memory-os-operability/rate-limit-policies.negative.v1.json",
    "contracts/operations/production-operability-status.json",
    "services/import-api/internal/ratelimit/enforce.go",
    "services/import-api/internal/obslog/codes.go",
)


def upload_route_rate_limit_scope_issue(source: str, matches: set[str]) -> str | None:
    """Allow a reviewed narrowing, but fail on newly coupled rate-limit scripts."""
    path_rows = [
        row for row in source.splitlines() if row.startswith("      - ")
    ]
    script_globs = [
        row for row in path_rows
        if (lambda value: value.startswith("scripts/") and
            ("rate-limit" in value or any(char in value for char in "*?[")))(
                row[8:].strip().strip("\\\"'")
            )
    ]
    # An exact-core trigger is NOT yet proven safe: the canonical validator
    # reads additional Go, fixture and production-status authorities, and the
    # workflow path inventory does not cover them. Reject premature narrowing.
    if script_globs == ['      - "' + UPLOAD_ROUTE_RATE_LIMIT_CORE + '"']:
        return "upload-route exact-core narrowing lacks dependency closure"
    allowed = {'      - "' + UPLOAD_ROUTE_RATE_LIMIT_WILDCARD + '"'}
    if len(script_globs) != 1 or script_globs[0] not in allowed:
        return "upload-route rate-limit trigger pattern drift"
    if source.count("    paths:\n") != 1:
        return "upload-route rate-limit trigger pattern drift"
    if UPLOAD_ROUTE_RATE_LIMIT_CORE not in matches:
        return "upload-route rate-limit core source missing"
    if script_globs[0] == '      - "' + UPLOAD_ROUTE_RATE_LIMIT_WILDCARD + '"':
        if not matches.issubset(UPLOAD_ROUTE_REVIEWED_WILDCARD_MATCHES):
            return "upload-route new wildcard-coupled rate-limit source"
    return None


def validate_upload_route_rate_limit_trigger_scope(failures: list[str]) -> None:
    """Bound known CI over-trigger without treating MinIO failure as readiness."""
    directory = REPO_ROOT / "scripts"
    paths = list(directory.glob("validate-memory-os-rate-limit*.py"))
    if any(path.is_symlink() or not path.is_file() for path in paths):
        failures.append("upload-route rate-limit script path is missing or symlinked")
        return
    matches = {path.relative_to(REPO_ROOT).as_posix() for path in paths}
    if len(matches) != len(paths):
        failures.append("upload-route rate-limit script path inventory ambiguous")
        return
    original = '      - "' + UPLOAD_ROUTE_RATE_LIMIT_WILDCARD + '"\n'
    narrowed = '      - "' + UPLOAD_ROUTE_RATE_LIMIT_CORE + '"\n'
    # Keep the known direct-input gap visible while the broad reviewed
    # workflow remains unchanged. An unreviewed core narrowing must fail.
    core_source = (REPO_ROOT / UPLOAD_ROUTE_RATE_LIMIT_CORE).read_text(encoding="utf-8")
    for dependency in UPLOAD_ROUTE_RATE_LIMIT_DIRECT_INPUTS:
        if '"' + dependency + '"' not in core_source:
            failures.append("upload-route rate-limit direct dependency authority drift: " + dependency)
    for relative in UPLOAD_ROUTE_WORKFLOWS:
        workflow = REPO_ROOT / relative
        if workflow.is_symlink() or not workflow.is_file():
            failures.append("upload-route workflow missing or symlinked: " + relative)
            continue
        source = workflow.read_text(encoding="utf-8")
        trigger_rows = {row.strip()[2:].strip().strip('"') for row in source.splitlines()
                        if row.startswith("      - ")}
        uncovered = sorted(set(UPLOAD_ROUTE_RATE_LIMIT_DIRECT_INPUTS) - trigger_rows)
        if uncovered:
            print(relative + ": upload-route direct dependency trigger gaps (not full closure): "
                  + ", ".join(uncovered))
        issue = upload_route_rate_limit_scope_issue(source, matches)
        if issue:
            failures.append(relative + ": " + issue)
            continue
        if source.count(original) != 1:
            failures.append(relative + ": upload-route trigger fixture anchor drift")
            continue
        # Every mutation is rejected for its intended semantic reason, not
        # merely because the whole workflow source digest changed.
        cases = (
            ("removed", source.replace(original, "", 1), matches,
             "upload-route rate-limit trigger pattern drift"),
            ("duplicate", source.replace(original, original + original, 1), matches,
             "upload-route rate-limit trigger pattern drift"),
            ("unquoted", source.replace(original,
             "      - " + UPLOAD_ROUTE_RATE_LIMIT_WILDCARD + "\n", 1), matches,
             "upload-route rate-limit trigger pattern drift"),
            ("broadened", source.replace(original, '      - "scripts/**"\n', 1),
             matches, "upload-route rate-limit trigger pattern drift"),
            ("extra broad", source.replace(original,
             original + '      - "scripts/**"\n', 1), matches,
             "upload-route rate-limit trigger pattern drift"),
            ("new matching script", source,
             matches | {"scripts/validate-memory-os-rate-limit-unreviewed.py"},
             "upload-route new wildcard-coupled rate-limit source"),
            ("core missing", source,
             matches - {UPLOAD_ROUTE_RATE_LIMIT_CORE},
             "upload-route rate-limit core source missing"),
        )
        for name, changed, observed, expected in cases:
            if upload_route_rate_limit_scope_issue(changed, observed) != expected:
                failures.append(relative + ": upload-route scope negative failed: " + name)
        if upload_route_rate_limit_scope_issue(
                source.replace(original, narrowed, 1), matches) != (
                    "upload-route exact-core narrowing lacks dependency closure"):
            failures.append(relative + ": premature exact-core narrowing was accepted")
    if not any("upload-route" in failure for failure in failures):
        print("upload-route rate-limit wildcard scope bounded: "
              + str(len(matches)) + " current matches, "
              + str(7 * len(UPLOAD_ROUTE_WORKFLOWS))
              + " exact-diagnostic negatives; no MinIO retry")




# A second independent upload-route over-trigger is the rate-limit contract
# glob. Bound it separately: a new contract must not silently pull in the
# unrelated MinIO-dependent workflow merely by sharing the filename prefix.
UPLOAD_ROUTE_RATE_LIMIT_CONTRACT_CORE = "contracts/operations/rate-limit-policy-contract.v1.json"
UPLOAD_ROUTE_RATE_LIMIT_CONTRACT_WILDCARD = "contracts/operations/rate-limit*.json"
UPLOAD_ROUTE_REVIEWED_CONTRACT_MATCHES = frozenset((
    "contracts/operations/rate-limit-distributed-runtime-admission-contract.v1.json",
    "contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json",
    "contracts/operations/rate-limit-emergency-drill-contract.v1.json",
    "contracts/operations/rate-limit-local-multiprocess-shared-store-contract.v1.json",
    "contracts/operations/rate-limit-operation-evidence-contract.v1.json",
    "contracts/operations/rate-limit-operations-contract.v1.json",
    "contracts/operations/rate-limit-policy-contract.v1.json",
))


def upload_route_rate_limit_contract_scope_issue(source: str, matches: set[str]) -> str | None:
    rows = [row for row in source.splitlines() if row.startswith("      - ")]
    contract_rows = [
        row for row in rows
        if (lambda value: value.startswith("contracts/operations/") and
            ("rate-limit" in value or any(char in value for char in "*?[")))(
                row[8:].strip().strip(chr(34) + chr(39))
            )
    ]
    # The core policy is only one direct input of the validator chain; do
    # not narrow a reviewed trigger without a separately proven closure.
    if contract_rows == ['      - "' + UPLOAD_ROUTE_RATE_LIMIT_CONTRACT_CORE + '"']:
        return "upload-route exact-contract narrowing lacks dependency closure"
    allowed = {'      - "' + UPLOAD_ROUTE_RATE_LIMIT_CONTRACT_WILDCARD + '"'}
    if len(contract_rows) != 1 or contract_rows[0] not in allowed:
        return "upload-route rate-limit contract trigger drift"
    if source.count("    paths:\n") != 1:
        return "upload-route rate-limit contract trigger drift"
    if UPLOAD_ROUTE_RATE_LIMIT_CONTRACT_CORE not in matches:
        return "upload-route core rate-limit contract missing"
    if contract_rows[0] == '      - "' + UPLOAD_ROUTE_RATE_LIMIT_CONTRACT_WILDCARD + '"':
        if not matches.issubset(UPLOAD_ROUTE_REVIEWED_CONTRACT_MATCHES):
            return "upload-route new wildcard-coupled rate-limit contract"
    return None


def validate_upload_route_rate_limit_contract_scope(failures: list[str]) -> None:
    directory = REPO_ROOT / "contracts/operations"
    paths = list(directory.glob("rate-limit*.json"))
    if any(path.is_symlink() or not path.is_file() for path in paths):
        failures.append("upload-route rate-limit contract path missing or symlinked")
        return
    matches = {path.relative_to(REPO_ROOT).as_posix() for path in paths}
    original = '      - "' + UPLOAD_ROUTE_RATE_LIMIT_CONTRACT_WILDCARD + '"\n'
    narrowed = '      - "' + UPLOAD_ROUTE_RATE_LIMIT_CONTRACT_CORE + '"\n'
    for relative in UPLOAD_ROUTE_WORKFLOWS:
        workflow = REPO_ROOT / relative
        if workflow.is_symlink() or not workflow.is_file():
            failures.append("upload-route contract workflow missing or symlinked: " + relative)
            continue
        source = workflow.read_text(encoding="utf-8")
        issue = upload_route_rate_limit_contract_scope_issue(source, matches)
        if issue:
            failures.append(relative + ": " + issue)
            continue
        if source.count(original) != 1:
            failures.append(relative + ": upload-route contract fixture anchor drift")
            continue
        cases = (
            ("removed", source.replace(original, "", 1), matches,
             "upload-route rate-limit contract trigger drift"),
            ("duplicate", source.replace(original, original + original, 1), matches,
             "upload-route rate-limit contract trigger drift"),
            ("unquoted", source.replace(original,
             "      - " + UPLOAD_ROUTE_RATE_LIMIT_CONTRACT_WILDCARD + "\n", 1), matches,
             "upload-route rate-limit contract trigger drift"),
            ("broadened", source.replace(original,
             '      - "contracts/operations/**"\n', 1), matches,
             "upload-route rate-limit contract trigger drift"),
            ("extra broad", source.replace(original,
             original + '      - "contracts/operations/**"\n', 1), matches,
             "upload-route rate-limit contract trigger drift"),
            ("new matching contract", source,
             matches | {"contracts/operations/rate-limit-unreviewed.json"},
             "upload-route new wildcard-coupled rate-limit contract"),
            ("core missing", source,
             matches - {UPLOAD_ROUTE_RATE_LIMIT_CONTRACT_CORE},
             "upload-route core rate-limit contract missing"),
        )
        for name, changed, observed, expected in cases:
            if upload_route_rate_limit_contract_scope_issue(changed, observed) != expected:
                failures.append(relative + ": upload-route contract negative failed: " + name)
        if upload_route_rate_limit_contract_scope_issue(
                source.replace(original, narrowed, 1), matches) != (
                    "upload-route exact-contract narrowing lacks dependency closure"):
            failures.append(relative + ": premature exact-contract narrowing was accepted")
    if not any("upload-route" in failure for failure in failures):
        print("upload-route rate-limit contract wildcard bounded: "
              + str(len(matches)) + " current matches, 14 exact-diagnostic negatives")




SUPPLEMENTAL_HISTORY_IMMUTABLE_BASELINE = "1a2eeab517d8744df42de984fca921aebd747ff8"


def supplemental_history_baseline_bound(source: str) -> bool:
    """Independently pin the history epoch and live main-call binding."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    assignments = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
            targets = [node.target]
        else:
            continue
        if any(isinstance(name, ast.Name) and name.id == "BASELINE"
               for target in targets for name in ast.walk(target)):
            assignments.append(node)
    if (len(assignments) != 1 or assignments[0] not in tree.body
            or not isinstance(assignments[0], ast.Assign)
            or len(assignments[0].targets) != 1
            or not isinstance(assignments[0].targets[0], ast.Name)
            or not isinstance(assignments[0].value, ast.Constant)
            or type(assignments[0].value.value) is not str
            or assignments[0].value.value != SUPPLEMENTAL_HISTORY_IMMUTABLE_BASELINE):
        return False
    # An immutable literal is not enough if a later statement can delete or
    # indirectly rebind the epoch or the live history checker. This is a
    # conservative source guard, not a claim of complete Python alias closure.
    guarded_names = {"BASELINE", "check_history", "main"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in guarded_names and isinstance(
                node.ctx, (ast.Store, ast.Del)):
            if node is not assignments[0].targets[0]:
                return False
        if isinstance(node, ast.ExceptHandler) and node.name in guarded_names:
            return False
        if isinstance(node, ast.arg) and node.arg in guarded_names:
            return False
        if isinstance(node, ast.ClassDef) and node.name in guarded_names:
            return False
        if (isinstance(node, ast.Subscript)
                and isinstance(node.ctx, (ast.Store, ast.Del))
                and isinstance(node.slice, ast.Constant)
                and node.slice.value in guarded_names):
            return False
        if (isinstance(node, ast.Attribute)
                and isinstance(node.ctx, (ast.Store, ast.Del))
                and node.attr in guarded_names):
            return False
        if isinstance(node, ast.Call):
            if (isinstance(node.func, ast.Name)
                    and node.func.id in {"globals", "vars", "locals", "exec", "eval",
                                         "setattr", "delattr", "__import__"}):
                return False
            if (isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"__setitem__", "__delitem__", "exec",
                                           "eval", "setattr", "delattr",
                                           "__import__", "import_module", "run_path"}):
                return False
            if (isinstance(node.func, ast.Subscript)
                    and ((isinstance(node.func.value, ast.Name)
                          and node.func.value.id == "__builtins__")
                         or (isinstance(node.func.value, ast.Attribute)
                             and node.func.value.attr == "__dict__"))):
                return False
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if any(alias.asname in guarded_names
                   or alias.name.split(".")[-1] in guarded_names
                   for alias in node.names):
                return False
    checkers = [node for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "check_history"]
    if len(checkers) != 1 or checkers[0] not in tree.body:
        return False
    mains = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name == "main"]
    if len(mains) != 1:
        return False
    tries = [node for node in mains[0].body if isinstance(node, ast.Try)]
    if len(tries) != 1:
        return False
    calls = [node.value for node in tries[0].body
             if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
             and isinstance(node.value.func, ast.Name)
             and node.value.func.id == "check_history"]
    if len(calls) != 1 or len(calls[0].args) != 2 or calls[0].keywords:
        return False
    first, second = calls[0].args
    return (isinstance(first, ast.Attribute) and first.attr == "repo_root"
            and isinstance(first.value, ast.Name) and first.value.id == "args"
            and isinstance(second, ast.Name) and second.id == "BASELINE")


def prove_supplemental_history_baseline_negatives(failures: list[str]) -> None:
    """Reject baseline reset, shadow and a dead or redirected history call."""
    good = ('BASELINE = "' + SUPPLEMENTAL_HISTORY_IMMUTABLE_BASELINE + '"\n'
            'def check_history(root, baseline):\n'
            '    return None\n'
            'def main():\n'
            '    try:\n'
            '        check_history(args.repo_root, BASELINE)\n'
            '    except RuntimeError:\n'
            '        return 1\n')
    if not supplemental_history_baseline_bound(good):
        failures.append("supplemental history immutable baseline positive rejected")
    bad = (
        ("reset", good.replace(SUPPLEMENTAL_HISTORY_IMMUTABLE_BASELINE, "0" * 40)),
        ("removed", good.replace('BASELINE = "' + SUPPLEMENTAL_HISTORY_IMMUTABLE_BASELINE + '"\n', "")),
        ("shadowed", good + 'BASELINE = "0" * 40\n'),
        ("redirected", good.replace("check_history(args.repo_root, BASELINE)",
                                    'check_history(args.repo_root, "0" * 40)')),
        ("unreachable", good.replace("        check_history(args.repo_root, BASELINE)",
                                     "        if False:\n            check_history(args.repo_root, BASELINE)")),
        ("global-store", good + 'globals()["BASELINE"] = "0" * 40\n'),
        ("delete-epoch", good + "del BASELINE\n"),
        ("rebind-checker", good + 'globals()["check_history"] = lambda *args: None\n'),
        ("dynamic-exec", good + 'exec("BASELINE = 0")\n'),
        ("duplicate-checker", good + 'def check_history(*args): pass\n'),
        ("loop-rebind", good + 'for BASELINE in ["0" * 40]: pass\n'),
        ("attribute-rebind", good + 'module.BASELINE = "0" * 40\n'),
        ("setattr-rebind", good + 'setattr(module, "BASELINE", "0" * 40)\n'),
        ("indirect-subscript", good + 'registry["BASELINE"] = "0" * 40\n'),
        ("rebind-main", good + 'main = lambda: 0\n'),
    )
    for label, candidate in bad:
        if supplemental_history_baseline_bound(candidate):
            failures.append("supplemental history baseline negative accepted: " + label)


def validate_supplemental_learning_history(failures: list[str]) -> None:
    """Run additive-history proof and destructive Git negatives before admission."""
    relative = "scripts/validate-autonomous-learning-records-history.py"
    guard = REPO_ROOT / relative
    if guard.is_symlink() or not guard.is_file():
        failures.append("supplemental learning history guard missing or symlinked")
        return
    try:
        guard_source = guard.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        failures.append("supplemental history immutable baseline source unavailable")
        return
    if not supplemental_history_baseline_bound(guard_source):
        failures.append("supplemental history immutable baseline or live call drift")
        return
    prove_supplemental_history_baseline_negatives(failures)
    try:
        result = subprocess.run(
            [sys.executable, "-B", str(guard), "--self-test",
             "--repo-root", str(REPO_ROOT)],
            cwd=REPO_ROOT, capture_output=True, text=True,
            timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        failures.append("supplemental learning history guard unavailable")
        return
    if (type(result.returncode) is not int or result.returncode != 0
            or result.stdout != "Supplemental learning all-parent append-only history PASS (39 fixtures)\n"
            or type(result.stderr) is not str or result.stderr):
        failures.append("supplemental learning history guard missing verified PASS")
    else:
        print("supplemental learning all-parent history and 39 scoped/merge/octopus/shallow/literal/Git-environment/ancestry/diagnostic/wrong-reason negatives verified")



def has_upload_route_symlink_negative_binding(source: str) -> bool:
    """Require live direct calls to both symlink and ownership negatives."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    names = ("main", "prove_rollback_symlink_boundaries",
             "prove_rollback_write_ownership", "prove_atomic_mode_preservation",
             "prove_atomic_mode_failure_cleanup",
             "prove_atomic_fdopen_failure_cleanup",
             "prove_atomic_poststage_drift_rejection",
             "prove_atomic_short_write_rejection")
    definitions = {
        name: [node for node in tree.body
               if isinstance(node, ast.FunctionDef) and node.name == name]
        for name in names
    }
    if any(len(nodes) != 1 for nodes in definitions.values()):
        return False
    main = definitions["main"][0]
    for name in names[1:]:
        proof = definitions[name][0]
        direct = [
            node for node in main.body
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == name
        ]
        transports = {
            node.func.attr for node in ast.walk(proof)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "module"
        }
        required = ({"atomic_write_bytes"} if name in (
                        "prove_atomic_mode_preservation", "prove_atomic_mode_failure_cleanup",
                        "prove_atomic_fdopen_failure_cleanup",
                        "prove_atomic_poststage_drift_rejection",
                        "prove_atomic_short_write_rejection")
                    else {"rollback_authority_files", "atomic_write_bytes"})
        if len(direct) != 1 or not required.issubset(transports):
            return False
    return True


def validate_upload_route_learning_scan(failures: list[str]) -> None:
    """Exercise the real route reconciler's append-only exclusion before MinIO."""
    relative = "scripts/validate-memory-os-upload-route-reconcile-rollback.py"
    guard = REPO_ROOT / relative
    if guard.is_symlink() or not guard.is_file():
        failures.append("upload-route learning scan guard missing or symlinked")
        return
    try:
        if not has_upload_route_symlink_negative_binding(
                guard.read_text(encoding="utf-8")):
            failures.append("upload-route symlink rollback negative is not CI-bound")
            return
    except OSError:
        failures.append("upload-route symlink rollback negative unavailable")
        return
    try:
        result = subprocess.run(
            [sys.executable, "-B", str(guard)],
            cwd=REPO_ROOT, capture_output=True, text=True,
            timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        failures.append("upload-route learning scan guard unavailable")
        return
    expected = (
        "PASS: upload-route reconcile atomic publication, rollback, execution "
        "authority and canonical validator delegation are fail-closed" + chr(10)
    )
    if (type(result.returncode) is not int or result.returncode != 0
            or result.stdout != expected or type(result.stderr) is not str
            or result.stderr):
        failures.append("upload-route learning scan guard missing verified PASS")
    else:
        print("upload-route append-only scan and symlink negatives verified")

def main() -> int:
    failures: list[str] = []
    for relative, rules in ENTRYPOINTS.items():
        path = REPO_ROOT / relative
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            failures.append(f"missing entrypoint: {relative}")
            continue

        for phrase in rules["required"]:
            if phrase not in text:
                failures.append(f"{relative}: missing required current-authority phrase: {phrase!r}")
        for phrase in rules["forbidden"]:
            if phrase in text:
                failures.append(f"{relative}: contains stale or unsafe completion claim: {phrase!r}")

        lowered = text.lower()
        if "production ready" in lowered and "not production ready" not in lowered:
            failures.append(f"{relative}: unqualified production-ready wording")

    validate_learning_guards(failures)
    validate_supplemental_learning_history(failures)
    validate_upload_route_learning_scan(failures)
    validate_learning_workflow_reachability(failures)
    validate_source_negative_ci_reachability(failures)
    validate_upload_route_rate_limit_trigger_scope(failures)
    validate_upload_route_rate_limit_contract_scope(failures)
    # A pre-write fanout audit is CI-bound so high-risk trigger topology
    # cannot silently lose its executable diagnostic. It never runs MinIO.
    fanout_guard = REPO_ROOT / "scripts/audit-memory-os-workflow-trigger-fanout.py"
    if fanout_guard.is_symlink() or not fanout_guard.is_file():
        failures.append("missing or symlinked prewrite workflow trigger fanout guard")
    else:
        try:
            fanout_result = subprocess.run(
                [sys.executable, str(fanout_guard), "--self-test",
                 "--repo-root", str(REPO_ROOT)],
                cwd=REPO_ROOT, capture_output=True, text=True,
                timeout=30, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            failures.append("prewrite workflow trigger fanout guard unavailable")
        else:
            if fanout_result.returncode != 0:
                failures.append("prewrite workflow trigger fanout guard failed: "
                                + fanout_result.stderr[:300])
            else:
                print(fanout_result.stdout.strip())
                # Verify real CLI path matching for valid quoted and scalar
                # GitHub event forms, not only an in-process helper fixture.
                for label, event_source, expected_count in (
                    ("quoted-on", "'on':\n  push:\n    paths:\n      - 'scripts/synthetic.py'\n", 1),
                    ("scalar-push", "on: push\n", 1),
                    ("quoted-push-event",
                     "on:\n  'push':\n    paths:\n      - 'scripts/synthetic.py'\n", 1),
                    ("quoted-pr-event",
                     'on:\n  "pull_request":\n    paths:\n      - "scripts/synthetic.py"\n', 1),
                    ("dispatch-only", "on: workflow_dispatch\n", 0),
                ):
                    with tempfile.TemporaryDirectory(prefix="ops-fanout-") as temporary:
                        fixture_root = Path(temporary)
                        fixture_dir = fixture_root / ".github/workflows"
                        fixture_dir.mkdir(parents=True)
                        (fixture_dir / "synthetic.yml").write_text(
                            event_source, encoding="utf-8"
                        )
                        try:
                            fixture_result = subprocess.run(
                                [sys.executable, str(fanout_guard), "--path",
                                 "scripts/synthetic.py", "--repo-root",
                                 str(fixture_root)],
                                cwd=REPO_ROOT, capture_output=True, text=True,
                                timeout=30, check=False,
                            )
                        except (OSError, subprocess.TimeoutExpired):
                            failures.append("prewrite fanout event CLI unavailable: " + label)
                        else:
                            expected = "matched workflow count: " + str(expected_count)
                            if (fixture_result.returncode != 0
                                    or expected not in fixture_result.stdout):
                                failures.append(
                                    "prewrite fanout event CLI undercount: " + label
                                )
                # Verify the actual CLI fails closed for both known risk
                # classes; a passing self-test alone cannot prove its exit code.
                for candidate in (
                    "scripts/validate-memory-os-operability.py",
                    "scripts/validate-memory-os-rate-limit-operations-source-negative.py",
                ):
                    try:
                        cli_result = subprocess.run(
                            [sys.executable, str(fanout_guard), "--path", candidate,
                             "--repo-root", str(REPO_ROOT)],
                            cwd=REPO_ROOT, capture_output=True, text=True,
                            timeout=30, check=False,
                        )
                    except (OSError, subprocess.TimeoutExpired):
                        failures.append("prewrite workflow fanout CLI unavailable: " + candidate)
                    else:
                        if (cli_result.returncode != 2
                                or "risk: BLOCKED_" not in cli_result.stdout):
                            failures.append("prewrite workflow fanout CLI failed closed: "
                                            + candidate)

    # Independently exercise the actual production-operability JSON loader
    # with raw invalid UTF-8, without editing its 79-workflow-fanout source.
    # A backslash-x JSON escape is not an invalid UTF-8 byte sequence.
    operability_reader = REPO_ROOT / "scripts/validate-memory-os-operability.py"
    if operability_reader.is_symlink() or not operability_reader.is_file():
        failures.append("operability UTF-8 actual-loader source missing or symlinked")
    else:
        try:
            spec = importlib.util.spec_from_file_location(
                "memory_os_operability_utf8_probe", operability_reader
            )
            if spec is None or spec.loader is None:
                raise RuntimeError("operability module loader unavailable")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with tempfile.TemporaryDirectory(prefix="ops-utf8-negative-") as temporary:
                candidate = Path(temporary) / "authority.json"
                candidate.write_bytes(b'{"valid":true}')
                if module.load_json(candidate) != {"valid": True}:
                    failures.append("operability UTF-8 positive control failed")
                raw_invalid = b'{"invalid":"' + bytes([0xff]) + b'"}'
                try:
                    raw_invalid.decode("utf-8")
                except UnicodeDecodeError:
                    pass
                else:
                    failures.append("operability UTF-8 fixture is not invalid")
                candidate.write_bytes(raw_invalid)
                try:
                    module.load_json(candidate)
                except module.ValidationFailure:
                    print("operability actual-loader raw invalid UTF-8 negative PASS")
                else:
                    failures.append("operability actual-loader accepted raw invalid UTF-8")
        except Exception as exc:
            failures.append(
                "operability actual-loader UTF-8 probe failed: " + type(exc).__name__
            )

    if failures:
        print("ENTRYPOINT DOCUMENT VALIDATION FAILED", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("Memory OS entrypoint document validation PASS")
    print(f"entrypoints: {len(ENTRYPOINTS)}")
    print(f"autonomous-learning guards: {len(LEARNING_GUARDS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
