#!/usr/bin/env python3
"""Validate current Memory OS entrypoint documents against repository authority."""

from __future__ import annotations

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
        "    steps:\n"
        "      - uses: actions/checkout@reviewed\n"
        "        with:\n"
        "          persist-credentials: false\n"
        "      - name: Verify source\n"
        "        run: |\n"
        "          set -euo pipefail\n"
        '          test "$(git rev-parse HEAD)" = "$expected"\n'
        '          test -z "$(git status --porcelain)"\n'
        "      - name: Execute negative validator\n"
        "        run: |\n"
        "          set -euo pipefail\n"
        "          python scripts/check.py\n"
        "          git diff --exit-code\n"
        '          test -z "$(git status --porcelain)"\n'
    )
    exists = lambda script: script == "scripts/check.py"
    if source_negative_reachability_issues(relative, fixture, exists):
        failures.append("source-negative reachability positive control failed")
        return
    nested = fixture.replace(
        "          python scripts/check.py",
        "          (\n            python scripts/check.py\n          )",
    )
    if source_negative_reachability_issues(relative, nested, exists):
        failures.append("source-negative nested subshell validator positive control failed")
        return
    cases = {
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
        "validator inside shell loop": fixture.replace(
            "          python scripts/check.py\n",
            "          for attempt in 1; do\n          python scripts/check.py\n          done\n"),
        "validator inside shell case": fixture.replace(
            "          python scripts/check.py\n",
            '          case "$GITHUB_EVENT_NAME" in\n'
            "          push)\n          python scripts/check.py\n          ;;\n          esac\n"),
        "conditional post-validator clean checks": fixture.replace(
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
    for name, mutation in cases.items():
        if mutation == fixture or not source_negative_reachability_issues(relative, mutation, exists):
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
              f"{invocation_count} direct Python commands, 53 negative fixtures")


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
