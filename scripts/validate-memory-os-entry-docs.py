#!/usr/bin/env python3
"""Validate current Memory OS entrypoint documents against repository authority."""

from __future__ import annotations

import ast
import re
import subprocess
import sys
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
MIN_LEARNING_NEGATIVE_CASES = 128


def learning_guard_passed(relative: str, completed: subprocess.CompletedProcess[str]) -> bool:
    """An exit-zero child without its actual PASS proof is not an executed guard."""
    if completed.returncode != 0 or completed.stderr:
        return False
    output = completed.stdout.strip()
    if relative == LEARNING_GUARDS[0]:
        return output == "Autonomous improvement/learning contract validation PASS"
    if relative == LEARNING_GUARDS[1]:
        prefix = "Autonomous learning negative validation PASS ("
        suffix = " fail-closed cases)"
        if not output.startswith(prefix) or not output.endswith(suffix):
            return False
        count = output[len(prefix):-len(suffix)]
        return count.isascii() and count.isdecimal() and int(count) >= MIN_LEARNING_NEGATIVE_CASES
    return False


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
        ("stderr with success text", LEARNING_GUARDS[0], 0, positive, "injected", False),
        ("truncated negative", LEARNING_GUARDS[1], 0,
         f"Autonomous learning negative validation PASS ({MIN_LEARNING_NEGATIVE_CASES - 1} fail-closed cases)\n", "", False),
        ("nonnumeric count", LEARNING_GUARDS[1], 0,
         "Autonomous learning negative validation PASS (False fail-closed cases)\n", "", False),
        ("extra output", LEARNING_GUARDS[1], 0, negative + "ignored", "", False),
        ("unbound guard", "scripts/unbound-guard.py", 0, positive, "", False),
    )
    for name, relative, code, stdout, stderr, expected in cases:
        completed = subprocess.CompletedProcess([], code, stdout, stderr)
        if learning_guard_passed(relative, completed) is not expected:
            failures.append(f"learning guard success classifier misclassified: {name}")


def validate_learning_guards(failures: list[str]) -> None:
    """Keep autonomous-learning guards reachable from the existing operability CI path."""
    if len(LEARNING_GUARDS) != len(set(LEARNING_GUARDS)):
        failures.append("duplicate autonomous-learning guard binding")
        return
    if not 1 <= LEARNING_GUARD_TIMEOUT_SECONDS <= 300:
        failures.append("autonomous-learning guard timeout must remain bounded to 1..300 seconds")
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
            failures.append(
                f"autonomous-learning guard missing verified PASS: {relative} "
                f"(exit {completed.returncode})"
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
        if not paths or len(paths) != len(set(paths)):
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
    jobs = source.split("\njobs:\n")
    if (len(jobs) != 2 or
            len(re.findall(r"(?m)^  [A-Za-z0-9_-]+:\s*$", jobs[1])) != 1):
        issues.append("missing or duplicate source-negative CI job")
    # GitHub Actions metadata can change the execution source even when the
    # pinned actions and a visible Python command remain unchanged.
    root_keys = re.findall(r"(?m)^([A-Za-z][A-Za-z0-9_-]*):", source)
    if root_keys != ["name", "on", "permissions", "jobs"]:
        issues.append("unreviewed workflow-level execution metadata")
    job_keys = (re.findall(r"(?m)^ {4}([A-Za-z][A-Za-z0-9_-]*):", jobs[1])
                if len(jobs) == 2 else [])
    if job_keys != ["if", "permissions", "runs-on", "timeout-minutes", "steps"]:
        issues.append("unreviewed job runner, timeout or execution metadata")
    if len(jobs) == 2 and (
            "    runs-on: ubuntu-latest" not in jobs[1].splitlines() or
            "    timeout-minutes: 5" not in jobs[1].splitlines()):
        issues.append("unreviewed job runner or timeout value")
    step_keys = (re.findall(r"(?m)^ {8}([A-Za-z][A-Za-z0-9_-]*):", jobs[1])
                 if len(jobs) == 2 else [])
    if any(key not in {"with", "name", "env", "run"} for key in step_keys):
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


EXPECTED_SOURCE_NEGATIVE_FIXTURE_COUNT = 166


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


def prove_source_negative_reachability_negatives(failures: list[str]) -> None:
    """Positive control plus independent mutations; no digest-only success."""
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
    exists = lambda script: script in {"scripts/check.py", migration_script}
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
    go_fixture += (
        "      - name: Prove reviewed Go checks\n"
        "        run: |\n"
        "          set -euo pipefail\n"
        "          (cd services/import-api && go test ./internal/httpserver -run '^(TestLiveObjectStageLabelClosedVocabulary|TestAtomicLocalLoadResultWriter)$' -count=1)\n"
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
    for name, mutation in cases.items():
        if name.startswith("setup-go "):
            case_relative, baseline = go_relative, go_fixture
        elif name.startswith("migration-clone "):
            case_relative, baseline = migration_relative, migration_fixture
        else:
            case_relative, baseline = relative, fixture
        if mutation == baseline or not source_negative_reachability_issues(
                case_relative, mutation, exists):
            failures.append(f"source-negative reachability negative escaped: {name}")


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
    validate_source_negative_ci_reachability(failures)

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
