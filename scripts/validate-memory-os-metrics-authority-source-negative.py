#!/usr/bin/env python3
"""Independent reviewed metrics writer/PR source and executable negative proof."""
from __future__ import annotations
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ".github/workflows/reconcile-metrics-scrape-status.yml"
PR = ".github/workflows/reconcile-metrics-scrape-status-pr.yml"
INDEPENDENT = ".github/workflows/metrics-authority-source-negative.yml"
SELF = "scripts/validate-memory-os-metrics-authority-source-negative.py"
CHECKOUT = "uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683"
SETUP_GO = "uses: actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5"
SETUP_PY = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
REVIEWED_WRITER = "bf2be5f5c50f2193b91e3f46be86ac7d783e58bd"
REVIEWED_PR = "6977ffa544aa2c2df762e76fd7c7e8c263b4795e"
REVIEWED_INDEPENDENT = "dbef991d6c20a405c05ad65e1d64e7dde9b04b96"

def read(path: str) -> str:
    target = ROOT / path
    if target.is_symlink() or not target.is_file():
        raise AssertionError("metrics source substituted: " + path)
    if target.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise AssertionError("metrics source escaped root: " + path)
    return target.read_text(encoding="utf-8")

def blob(s: str) -> str:
    data = s.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

WRITER_REQUIRED = (
    "if: (github.event_name == 'push' || github.event_name == 'schedule' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'",
    "persist-credentials: true",
    'test "$' + '{GITHUB_REF:-}" = "refs/heads/so"',
    '[[ "$' + '{GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'test "$EVENT_SHA" = "$' + '{GITHUB_SHA:-}"',
    'test "$(git rev-parse HEAD)" = "$EVENT_SHA"',
    "git ls-remote origin refs/heads/so",
    "git push origin HEAD:so",
)
PR_REQUIRED = (
    "if: github.event_name == 'pull_request' && github.base_ref == 'so'",
    "persist-credentials: false",
    'test "$' + '{GITHUB_EVENT_NAME:-}" = "pull_request"',
    'test "$' + '{GITHUB_BASE_REF:-}" = "so"',
    '[[ "$' + '{PR_HEAD_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"',
)

METRICS_WRITER_PUSH = (
    ".github/workflows/reconcile-metrics-scrape-status.yml",
    ".github/workflows/reconcile-metrics-scrape-status-pr.yml",
    "contracts/operations/metrics-scrape-contract.v1.json",
    "contracts/operations/metrics-dashboard-contract.v1.json",
    "contracts/operations/metrics-retention-error-budget-contract.v1.json",
    "contracts/operations/metrics-alerting-contract.v1.json",
    "infra/observability/prometheus/memory-os-alerts.yml",
    "docs/runbooks/memory-os-metrics-alerts.md",
    "services/import-api/internal/metrics/prometheus.go",
    "services/import-api/internal/metrics/scrape.go",
    "services/import-api/internal/metrics/prometheus_test.go",
    "services/import-api/internal/httpserver/server.go",
    "services/import-api/internal/httpserver/observability.go",
    "services/import-api/internal/httpserver/metrics_scrape_test.go",
    "scripts/validate-memory-os-metrics.py",
    "scripts/validate-memory-os-metrics-scrape.py",
    "scripts/validate-memory-os-metrics-operations.py",
    "scripts/validate-memory-os-metrics-alerting.py",
    "scripts/validate-memory-os-metrics-reconcile-rollback-negative.py",
    "scripts/reconcile-memory-os-metrics-contract.py",
    "scripts/reconcile-memory-os-metrics-scrape-status.py",
    "scripts/reconcile-memory-os-metrics-operations.py",
    "scripts/reconcile-memory-os-metrics-alerting.py",
    "scripts/validate-memory-os-operability.py",
    "scripts/validate-memory-os-entry-docs.py",
    "contracts/operations/metrics-contract.v1.json",
    "contracts/operations/production-operability-status.json",
)

METRICS_PR_PATHS = (
    ".github/workflows/reconcile-metrics-scrape-status.yml",
    ".github/workflows/reconcile-metrics-scrape-status-pr.yml",
    "contracts/operations/metrics-scrape-contract.v1.json",
    "contracts/operations/metrics-dashboard-contract.v1.json",
    "contracts/operations/metrics-retention-error-budget-contract.v1.json",
    "contracts/operations/metrics-alerting-contract.v1.json",
    "infra/observability/prometheus/memory-os-alerts.yml",
    "docs/runbooks/memory-os-metrics-alerts.md",
    "services/import-api/internal/metrics/prometheus.go",
    "services/import-api/internal/metrics/scrape.go",
    "services/import-api/internal/metrics/prometheus_test.go",
    "services/import-api/internal/httpserver/server.go",
    "services/import-api/internal/httpserver/observability.go",
    "services/import-api/internal/httpserver/metrics_scrape_test.go",
    "scripts/validate-memory-os-metrics.py",
    "scripts/validate-memory-os-metrics-scrape.py",
    "scripts/validate-memory-os-metrics-operations.py",
    "scripts/validate-memory-os-metrics-alerting.py",
    "scripts/validate-memory-os-metrics-reconcile-rollback-negative.py",
    "scripts/reconcile-memory-os-metrics-contract.py",
    "scripts/reconcile-memory-os-metrics-scrape-status.py",
    "scripts/reconcile-memory-os-metrics-operations.py",
    "scripts/reconcile-memory-os-metrics-alerting.py",
    "scripts/validate-memory-os-operability.py",
    "scripts/validate-memory-os-entry-docs.py",
    "contracts/operations/metrics-contract.v1.json",
    "contracts/operations/production-operability-status.json",
)

METRICS_INDEPENDENT_PR = (
    ".github/workflows/reconcile-metrics-scrape-status.yml",
    ".github/workflows/reconcile-metrics-scrape-status-pr.yml",
    ".github/workflows/metrics-authority-source-negative.yml",
    "scripts/validate-memory-os-metrics-authority-source-negative.py",
)

METRICS_INDEPENDENT_PUSH = (
    ".github/workflows/reconcile-metrics-scrape-status.yml",
    ".github/workflows/reconcile-metrics-scrape-status-pr.yml",
    ".github/workflows/metrics-authority-source-negative.yml",
    "scripts/validate-memory-os-metrics-authority-source-negative.py",
)


def metrics_trigger_event(event: str, paths: tuple[str, ...]) -> str:
    return ("  " + event + ":\n    branches:\n      - so\n    paths:\n"
            + "".join('      - "' + path + '"\n' for path in paths))


def metrics_trigger_header(content: str) -> str:
    if content.count("\non:\n") != 1 or content.count("\npermissions:\n") != 1:
        raise AssertionError("metrics event trigger header ambiguous")
    return content.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]


def metrics_trigger_matrix(
    writer: str, pr: str, independent: str,
    writer_push: tuple[str, ...] = METRICS_WRITER_PUSH,
    pr_paths: tuple[str, ...] = METRICS_PR_PATHS,
    independent_pr: tuple[str, ...] = METRICS_INDEPENDENT_PR,
    independent_push: tuple[str, ...] = METRICS_INDEPENDENT_PUSH,
) -> None:
    expected_writer = (metrics_trigger_event("push", writer_push)
                       + '  schedule:\n    - cron: "23 18 * * *"\n'
                       + "  workflow_dispatch:\n")
    expected_pr = metrics_trigger_event("pull_request", pr_paths)
    expected_independent = (metrics_trigger_event("pull_request", independent_pr)
                            + metrics_trigger_event("push", independent_push))
    for label, content, expected in (
        ("writer", writer, expected_writer),
        ("PR", pr, expected_pr),
        ("independent", independent, expected_independent),
    ):
        if metrics_trigger_header(content) != expected:
            raise AssertionError("metrics " + label + " exact trigger matrix drift")
        # A later valid YAML root mapping may shadow on, permissions or
        # jobs even though the canonical event header remains unchanged.
        expected_roots = {
            "writer": ["name: Reconcile Metrics Authority", "on:",
                       "permissions:", "concurrency:", "jobs:"],
            "PR": ["name: Validate Metrics Authority on Pull Requests", "on:",
                   "permissions:", "concurrency:", "jobs:"],
            "independent": ["name: Metrics Authority Source Negative", "on:",
                            "permissions:", "jobs:"],
        }[label]
        observed_roots = [
            row for row in content.splitlines()
            if row.strip() and not row[0].isspace()
            and not row.lstrip().startswith("#")
        ]
        if observed_roots != expected_roots:
            raise AssertionError("metrics " + label + " root YAML key shadow drift")
        # The publisher legitimately requires write; PR and independent CI
        # require read. Reject quoted/whitespace-colon YAML leaf shadows at
        # every scope without weakening the publisher's reviewed authority.
        permission_lines = content.split("\npermissions:\n", 1)[1].splitlines()
        permission_rows = []
        for row in permission_lines:
            if row.strip() and not row[0].isspace():
                break
            if row.strip() and not row.lstrip().startswith("#"):
                permission_rows.append(row)
        expected_permission = "  contents: write" if label == "writer" else "  contents: read"
        if permission_rows != [expected_permission]:
            raise AssertionError("metrics " + label + " workflow permission leaf shadow drift")


def metrics_trigger_replace(content: str, old: str, new: str) -> str:
    anchor = "\non:\n" + old + "\npermissions:\n"
    if content.count(anchor) != 1 or old == new:
        raise AssertionError("metrics trigger mutation fixture unreachable")
    return content.replace(anchor, "\non:\n" + new + "\npermissions:\n", 1)


def metrics_trigger_negatives(writer: str, pr: str, independent: str) -> None:
    def reject(index: int, altered: str) -> None:
        sources = [writer, pr, independent]
        sources[index] = altered
        try:
            metrics_trigger_matrix(*sources)
        except AssertionError:
            return
        raise AssertionError("metrics accepted event trigger mutation")

    omissions = additions = 0
    for index, event, paths in (
        (0, "push", METRICS_WRITER_PUSH),
        (1, "pull_request", METRICS_PR_PATHS),
        (2, "pull_request", METRICS_INDEPENDENT_PR),
        (2, "push", METRICS_INDEPENDENT_PUSH),
    ):
        original = (writer, pr, independent)[index]
        header = metrics_trigger_header(original)
        block = metrics_trigger_event(event, paths)
        if header.count(block) != 1:
            raise AssertionError("metrics event trigger fixture ambiguous")
        for position in range(len(paths)):
            changed = metrics_trigger_replace(
                original, header,
                header.replace(block, metrics_trigger_event(
                    event, paths[:position] + paths[position + 1:]), 1))
            reject(index, changed)
            omissions += 1
        first = '      - "' + paths[0] + '"\n'
        for extra in (
            '      - "unreviewed/**"\n', '      - unreviewed/**\n',
            first, '      - ' + paths[0] + '\n',
        ):
            changed = metrics_trigger_replace(
                original, header,
                header.replace(block, block.replace(first, first + extra, 1), 1))
            reject(index, changed)
            additions += 1

    shortened = 0
    for field, paths in (
        ("writer_push", METRICS_WRITER_PUSH),
        ("pr_paths", METRICS_PR_PATHS),
        ("independent_pr", METRICS_INDEPENDENT_PR),
        ("independent_push", METRICS_INDEPENDENT_PUSH),
    ):
        try:
            metrics_trigger_matrix(writer, pr, independent, **{field: paths[:-1]})
        except AssertionError:
            shortened += 1
        else:
            raise AssertionError("metrics accepted shortened trigger inventory")

    wh, ph, ih = map(metrics_trigger_header, (writer, pr, independent))
    topology = (
        (0, metrics_trigger_replace(writer, wh, "  pull_request:\n    branches:\n      - so\n" + wh)),
        (0, metrics_trigger_replace(writer, wh, wh.replace('  schedule:\n    - cron: "23 18 * * *"\n', "", 1))),
        (0, metrics_trigger_replace(writer, wh, wh.replace('23 18 * * *', '0 0 * * *', 1))),
        (1, metrics_trigger_replace(pr, ph, ph + "  push:\n    branches:\n      - so\n")),
        (2, metrics_trigger_replace(independent, ih, ih + "  workflow_dispatch:\n")),
    )
    for index, changed in topology:
        reject(index, changed)
    # Preserve the exact reviewed event header while injecting a later
    # effective YAML root key. Require the root guard's own diagnostic.
    root_shadows = (
        ("spaced on", "on :\n  issues:\n"),
        ("quoted on", "'on':\n  issues:\n"),
        ("spaced permissions", "permissions :\n  contents: write\n"),
        ("spaced jobs", "jobs : {}\n"),
    )
    root_negative_count = 0
    for index, label, original in (
        (0, "writer", writer), (1, "PR", pr), (2, "independent", independent)
    ):
        for name, suffix in root_shadows:
            sources = [writer, pr, independent]
            sources[index] = original + suffix
            try:
                metrics_trigger_matrix(*sources)
            except AssertionError as exc:
                expected = "metrics " + label + " root YAML key shadow drift"
                if str(exc) != expected:
                    raise AssertionError(
                        "metrics root shadow rejected for wrong reason: "
                        + label + " " + name + ": " + str(exc)
                    ) from exc
            else:
                raise AssertionError("metrics accepted root YAML shadow: " + label + " " + name)
            root_negative_count += 1
    if root_negative_count != 12:
        raise AssertionError("metrics root shadow fixture count drift")
    permission_negative_count = 0
    for index, label, original in (
        (0, "writer", writer), (1, "PR", pr), (2, "independent", independent)
    ):
        reviewed_leaf = "write" if label == "writer" else "read"
        shadow_leaf = "read" if label == "writer" else "write"
        anchor = "permissions:\n  contents: " + reviewed_leaf + "\n"
        if original.count(anchor) != 1:
            raise AssertionError("metrics permission negative anchor drift: " + label)
        for name, extra in (
            ("spaced", "  contents : " + shadow_leaf + "\n"),
            ("quoted", "  'contents': " + shadow_leaf + "\n"),
        ):
            sources = [writer, pr, independent]
            sources[index] = original.replace(anchor, anchor + extra, 1)
            try:
                metrics_trigger_matrix(*sources)
            except AssertionError as exc:
                expected = "metrics " + label + " workflow permission leaf shadow drift"
                if str(exc) != expected:
                    raise AssertionError(
                        "metrics permission shadow rejected for wrong reason: "
                        + label + " " + name + ": " + str(exc)
                    ) from exc
            else:
                raise AssertionError("metrics accepted permission leaf shadow: " + label + " " + name)
            permission_negative_count += 1
    if permission_negative_count != 6:
        raise AssertionError("metrics permission leaf fixture count drift")
    print("PASS: metrics permission leaf shadows (6 exact-diagnostic negatives)")
    print("PASS: metrics exact event trigger matrix: " + str(omissions)
          + " omissions, " + str(additions) + " additions/duplicates, "
          + str(shortened) + " shortened inventories, "
          + str(len(topology)) + " event topology/schedule negatives")



def metrics_concurrency_authority(writer: str, pr: str) -> None:
    """Pin writer serialization separately from cancellable PR validation."""
    for label, content, group, cancel in (
        ("writer", writer, "reconcile-metrics-authority-so", "false"),
        ("PR", pr, "validate-metrics-authority-pr-${{ github.event.pull_request.number }}", "true"),
    ):
        marker = "\nconcurrency:\n"
        if content.count(marker) != 1 or content.count("\njobs:\n") != 1:
            raise AssertionError("metrics " + label + " concurrency authority drift")
        actual = content.split(marker, 1)[1].split("\njobs:\n", 1)[0]
        expected = "  group: " + group + "\n  cancel-in-progress: " + cancel + "\n"
        if actual != expected:
            raise AssertionError("metrics " + label + " concurrency authority drift")


def metrics_concurrency_negatives(writer: str, pr: str) -> None:
    """Require the intended diagnostic for each semantic YAML mutation."""
    count = 0
    for index, label, original, group, cancel in (
        (0, "writer", writer, "reconcile-metrics-authority-so", "false"),
        (1, "PR", pr, "validate-metrics-authority-pr-${{ github.event.pull_request.number }}", "true"),
    ):
        group_row = "  group: " + group + "\n"
        cancel_row = "  cancel-in-progress: " + cancel + "\n"
        cases = (
            ("changed group", group_row, "  group: unreviewed\n"),
            ("missing group", group_row, ""),
            ("duplicate group", group_row, group_row + group_row),
            ("quoted group", group_row, "  'group': " + group + "\n"),
            ("spaced group", group_row, "  group : " + group + "\n"),
            ("shadow group", group_row, group_row + "  group : unreviewed\n"),
            ("changed cancellation", cancel_row,
             "  cancel-in-progress: " + ("true" if cancel == "false" else "false") + "\n"),
            ("missing cancellation", cancel_row, ""),
            ("duplicate cancellation", cancel_row, cancel_row + cancel_row),
            ("quoted cancellation", cancel_row, "  'cancel-in-progress': " + cancel + "\n"),
            ("spaced cancellation", cancel_row, "  cancel-in-progress : " + cancel + "\n"),
            ("unreviewed leaf", cancel_row, cancel_row + "  unexpected: true\n"),
        )
        for name, old, replacement in cases:
            if original.count(old) != 1:
                raise AssertionError("metrics concurrency fixture anchor drift: " + label + " " + name)
            changed = original.replace(old, replacement, 1)
            sources = [writer, pr]
            sources[index] = changed
            try:
                metrics_concurrency_authority(*sources)
            except AssertionError as exc:
                expected = "metrics " + label + " concurrency authority drift"
                if str(exc) != expected:
                    raise AssertionError(
                        "metrics concurrency wrong negative diagnostic: "
                        + label + " " + name + ": " + str(exc)
                    ) from exc
            else:
                raise AssertionError("metrics accepted concurrency mutation: " + label + " " + name)
            count += 1
    if count != 24:
        raise AssertionError("metrics concurrency negative inventory drift")
    print("PASS: metrics writer/PR concurrency authority (24 exact-diagnostic negatives)")



def policy(s: str, required: tuple, label: str) -> None:
    if any(s.count(action) != 1 for action in (CHECKOUT, SETUP_GO, SETUP_PY)):
        raise AssertionError("metrics " + label + " immutable Actions drift")
    if "actions/checkout@v4" in s or "actions/setup-go@v5" in s or "actions/setup-python@v5" in s:
        raise AssertionError("metrics floating Action regression")
    for marker in required:
        if marker not in s:
            raise AssertionError("metrics " + label + " required marker missing: " + marker)
    if s.count('test -z "$(git status --porcelain)"') != (2 if label == "PR" else 1):
        raise AssertionError("metrics " + label + " clean source/final multiplicity drift")

def negatives(source: str, required: tuple, label: str) -> None:
    for index, marker in enumerate(required):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE", 1)
        if changed == source:
            raise AssertionError("metrics negative unreachable: " + label + str(index))
        try:
            policy(changed, required, label)
        except AssertionError:
            continue
        raise AssertionError("metrics " + label + " source mutation accepted: " + str(index))
    print(f"PASS: metrics {label} source negatives ({len(required)} cases)")

def step(source: str, name: str) -> str:
    marker = "      - name: " + name + "\n"
    if source.count(marker) != 1:
        raise AssertionError("metrics step missing/duplicated: " + name)
    start = source.index("        run: |\n", source.index(marker)) + len("        run: |\n")
    boundaries = [p for p in (source.find("\n      - name:", start),
                             source.find("\n  reconcile:", start),
                             source.find("\n  validate:", start)) if p >= 0]
    end = min(boundaries) if boundaries else len(source)
    lines = source[start:end].splitlines()
    if any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("metrics shell crossed job boundary")
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"

def identity_runtime(source: str, name: str, cases: tuple) -> None:
    shell = step(source, name)
    head = "a" * 40
    with tempfile.TemporaryDirectory(prefix="metrics-source-") as tmp:
        root = Path(tmp)
        git = root / "git"
        git.write_text("#!/bin/sh\n"
                       "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"HEAD\" ]; then echo " + head + "; exit 0; fi\n"
                       "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then exit 0; fi\n"
                       "exit 1\n", encoding="utf-8")
        git.chmod(0o755)
        for event, base, ref, sha, accepted in cases:
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_EVENT_NAME=event, GITHUB_BASE_REF=base, GITHUB_REF=ref,
                       GITHUB_SHA=sha, EVENT_SHA=sha, PR_HEAD_SHA=sha)
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                    cwd=root, env=env, capture_output=True, text=True,
                                    timeout=10, check=False)
            if (result.returncode == 0) != accepted:
                raise AssertionError(f"metrics {name} event/base/ref/SHA drift: {(event, base, ref, sha, result.returncode)}")
    print(f"PASS: metrics {name} actual source shell ({len(cases)} cases)")

def cas_runtime(source: str) -> None:
    shell = step(source, "Commit reconciled authority files")
    head = "a" * 40
    cases = (
        ("noop", head, True, True, 0, 0),
        ("success", head, False, True, 0, 1),
        ("stale", "b" * 40, False, True, 75, 0),
        ("missing", "", False, True, 75, 0),
        ("diff-check", head, False, False, 1, 0),
    )
    fake_git = """#!/usr/bin/env python3
import os
import sys
from pathlib import Path
args = sys.argv[1:]
with Path(os.environ["FAKE_GIT_LOG"]).open("a", encoding="utf-8") as f:
    f.write(" ".join(args) + "\\n")
if args[:2] == ["rev-parse", "HEAD"]:
    print("a" * 40)
elif args[:2] == ["ls-remote", "origin"]:
    print(os.environ["FAKE_REMOTE"] + "\\trefs/heads/so")
elif args[:3] == ["diff", "--cached", "--quiet"]:
    sys.exit(0 if os.environ["FAKE_NOOP"] == "1" else 1)
elif args[:3] == ["diff", "--cached", "--check"]:
    sys.exit(0 if os.environ["FAKE_CHECK"] == "1" else 1)
elif args[0] in ("add", "config", "commit", "push"):
    pass
else:
    sys.exit(92)
"""
    for label, remote, noop, check, exit_code, pushes in cases:
        with tempfile.TemporaryDirectory(prefix="metrics-cas-") as tmp:
            root = Path(tmp)
            git = root / "git"
            git.write_text(fake_git, encoding="utf-8")
            git.chmod(0o755)
            log = root / "git.log"
            log.write_text("", encoding="utf-8")
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       FAKE_GIT_LOG=str(log), FAKE_REMOTE=remote,
                       FAKE_NOOP="1" if noop else "0", FAKE_CHECK="1" if check else "0")
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                    cwd=root, env=env, capture_output=True, text=True,
                                    timeout=10, check=False)
            calls = log.read_text(encoding="utf-8").splitlines()
            if result.returncode != exit_code:
                raise AssertionError(f"metrics CAS {label} unexpected exit {result.returncode}: {result.stderr[-100:]}")
            if sum(line == "push origin HEAD:so" for line in calls) != pushes:
                raise AssertionError("metrics CAS pushed on stale/no-op/invalid source: " + label)
    print(f"PASS: metrics actual publisher CAS/no-op shell ({len(cases)} cases)")

def main() -> None:
    writer = read(WRITER)
    pr = read(PR)
    independent = read(INDEPENDENT)
    for marker in (WRITER, PR, SELF, CHECKOUT, SETUP_PY,
                   "persist-credentials: false", "contents: read",
                   'test -z "$(git status --porcelain)"'):
        if marker not in independent:
            raise AssertionError("metrics independent CI reachability missing: " + marker)
    if blob(independent) != REVIEWED_INDEPENDENT:
        raise AssertionError("metrics complete independent CI Git blob drift")
    if blob(independent + "\n# synthetic whole-source drift\n") == REVIEWED_INDEPENDENT:
        raise AssertionError("metrics independent CI mutation accepted")
    for label, source, expected in (("writer", writer, REVIEWED_WRITER), ("PR", pr, REVIEWED_PR)):
        if blob(source) != expected:
            raise AssertionError("metrics " + label + " complete reviewed Git blob drift")
        if blob(source + "\n# synthetic whole-source drift\n") == expected:
            raise AssertionError("metrics " + label + " whole-source mutation accepted")
    policy(writer, WRITER_REQUIRED, "writer")
    policy(pr, PR_REQUIRED, "PR")
    metrics_trigger_matrix(writer, pr, independent)
    metrics_trigger_negatives(writer, pr, independent)
    metrics_concurrency_authority(writer, pr)
    metrics_concurrency_negatives(writer, pr)
    negatives(writer, WRITER_REQUIRED, "writer")
    negatives(pr, PR_REQUIRED, "PR")
    head = "a" * 40
    identity_runtime(writer, "Confirm exact source state", (
        ("push", "", "refs/heads/so", head, True),
        ("schedule", "", "refs/heads/so", head, True),
        ("workflow_dispatch", "", "refs/heads/so", head, True),
        ("pull_request", "", "refs/heads/so", head, False),
        ("push", "", "refs/heads/main", head, False),
        ("push", "", "refs/heads/so", "b" * 40, False),
        ("push", "", "refs/heads/so", "A" * 40, False),
        ("push", "", "refs/heads/so", "a" * 39, False),
    ))
    identity_runtime(pr, "Confirm exact clean PR source", (
        ("pull_request", "so", "", head, True),
        ("pull_request", "main", "", head, False),
        ("push", "so", "", head, False),
        ("pull_request", "so", "", "b" * 40, False),
        ("pull_request", "so", "", "A" * 40, False),
        ("pull_request", "so", "", "a" * 39, False),
    ))
    cas_runtime(writer)
    print("PASS: metrics independent source guard; production evidence generated: false")

if __name__ == "__main__":
    main()
