#!/usr/bin/env python3
"""Independent read-only exact-source admission for the backup authority reconciler."""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-backup-authority.yml"
INDEPENDENT = ".github/workflows/reconcile-backup-authority-source-negative.yml"
SELF = "scripts/validate-memory-os-reconcile-backup-authority-workflow-source-negative.py"

PUBLISHER_TRIGGER_PATHS = (
    ".github/workflows/reconcile-backup-authority.yml",
    "contracts/operations/backup-local-foundation-evidence.v1.json",
    "contracts/operations/backup-restore-contract.v1.json",
    "contracts/operations/local-apple-replay-restore-contract.v1.json",
    "contracts/operations/local-coherent-recovery-set-contract.v1.json",
    "contracts/operations/local-logical-restore-contract.v1.json",
    "contracts/operations/local-object-version-restore-contract.v1.json",
    "contracts/operations/migration-lifecycle-contract.v1.json",
    "contracts/operations/production-operability-status.json",
    "docs/fixtures/memory-os-operability/local-apple-replay-restore-results.sample.v1.json",
    "docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json",
    "docs/fixtures/memory-os-operability/local-object-version-restore-results.sample.v1.json",
    "docs/fixtures/memory-os-operability/local-coherent-recovery-set-results.sample.v1.json",
    "scripts/memory_os_backup_restore_blockers.py",
    "scripts/validate-memory-os-backup-local-foundations.py",
    "scripts/validate-memory-os-backup-restore.py",
    "scripts/validate-memory-os-backup-restore-blockers-negative.py",
    "scripts/validate-memory-os-backup-authority-atomic-negative.py",
    "scripts/validate-memory-os-local-apple-replay-restore.py",
    "scripts/validate-memory-os-local-logical-restore.py",
    "scripts/validate-memory-os-local-object-version-restore.py",
    "scripts/validate-memory-os-local-coherent-recovery-set.py",
    "scripts/validate-memory-os-operability.py",
    "scripts/reconcile-memory-os-backup-authority.py",
    "scripts/reconcile-memory-os-backup-coherent-authority.py",
    "scripts/reconcile-memory-os-backup-semantic-overlay.py",
)
INDEPENDENT_TRIGGER_PATHS = (
    ".github/workflows/reconcile-backup-authority.yml",
    ".github/workflows/reconcile-backup-authority-source-negative.yml",
    "scripts/validate-memory-os-reconcile-backup-authority-workflow-source-negative.py",
)
REVIEWED_PUBLISHER = "0f899f534dbf5b8ed20514b714a307a3d15d85bf"
REVIEWED_INDEPENDENT = "dda019a86d19590da03ff12a6c05586da4c054e5"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
PR_BASE = 'test "${GITHUB_BASE_REF:-}" = "so"'
PUSH_REF = 'test "${GITHUB_REF:-}" = "refs/heads/so"'
SHA_FORMAT = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
WRITER_EVENT = '[[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" || "${GITHUB_EVENT_NAME:-}" == "schedule" ]]'
PR_SCOPE = "    if: github.event_name == 'pull_request' && github.base_ref == 'so'"
WRITER_SCOPE = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch' || github.event_name == 'schedule') && github.ref == 'refs/heads/so'"


def source(relative: str) -> str:
    path = ROOT / relative
    try:
        if path.is_symlink() or not path.is_file():
            raise ValueError("not regular")
        if path.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != relative:
            raise ValueError("escaped root")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        raise SystemExit("backup authority CI source missing/substituted: " + relative) from exc


def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()



def validate_trigger_reachability(
    content: str, kind: str, *, trigger_paths: tuple[str, ...] | None = None
) -> None:
    """Pin reviewed PR/push paths while preserving the separately authorized schedule."""
    if kind == "publisher":
        canonical = PUBLISHER_TRIGGER_PATHS
        end_marker = "  schedule:\n"
    elif kind == "independent":
        canonical = INDEPENDENT_TRIGGER_PATHS
        end_marker = "\npermissions:\n"
    else:
        raise SystemExit("backup authority unknown CI trigger kind")
    if trigger_paths is None:
        trigger_paths = canonical
    if len(trigger_paths) != len(canonical) or len(set(trigger_paths)) != len(canonical):
        raise SystemExit("backup authority " + kind + " trigger inventory shortened or duplicated")
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    for marker in (pr_marker, push_marker, end_marker):
        if content.count(marker) != 1:
            raise SystemExit("backup authority " + kind + " event marker drift")
    pr = content.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push = content.split(push_marker, 1)[1].split(end_marker, 1)[0]
    approved = tuple('      - "' + path + '"' for path in trigger_paths)
    for event, block in (("pull_request", pr), ("push", push)):
        actual = tuple(
            line for line in block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        if actual != approved:
            raise SystemExit("backup authority " + kind + " " + event + " exact trigger inventory drift")


def prove_trigger_reachability_negatives(publisher: str, independent: str) -> None:
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    for kind, content, paths in (
        ("publisher", publisher, PUBLISHER_TRIGGER_PATHS),
        ("independent", independent, INDEPENDENT_TRIGGER_PATHS),
    ):
        validate_trigger_reachability(content, kind)
        for event in ("pull_request", "push"):
            for path in paths:
                token = '      - "' + path + '"\n'
                if content.count(token) != 2:
                    raise SystemExit("backup authority " + kind + " mutation anchor drift: " + path)
                if event == "pull_request":
                    mutated = content.replace(token, "", 1)
                else:
                    prefix, suffix = content.split(push_marker, 1)
                    mutated = prefix + push_marker + suffix.replace(token, "", 1)
                try:
                    validate_trigger_reachability(mutated, kind)
                except SystemExit:
                    continue
                raise SystemExit("backup authority " + kind + " accepted missing " + event + " trigger: " + path)
            marker = pr_marker if event == "pull_request" else push_marker
            for label, injected in (
                ("quoted extra", '      - "unreviewed/**"\n'),
                ("quoted duplicate", '      - "' + paths[0] + '"\n'),
                ("unquoted extra", "      - unreviewed/**\n"),
                ("unquoted duplicate", "      - " + paths[0] + "\n"),
            ):
                if content.count(marker) != 1:
                    raise SystemExit("backup authority " + kind + " addition marker drift: " + event)
                mutated = content.replace(marker, marker + injected, 1)
                if mutated == content:
                    raise SystemExit("backup authority " + kind + " addition fixture unchanged")
                try:
                    validate_trigger_reachability(mutated, kind)
                except SystemExit:
                    continue
                raise SystemExit("backup authority " + kind + " accepted " + event + " addition: " + label)
        try:
            validate_trigger_reachability(content, kind, trigger_paths=paths[:-1])
        except SystemExit:
            pass
        else:
            raise SystemExit("backup authority " + kind + " shortened inventory accepted")
    print("PASS: backup authority publisher/independent CI event-specific triggers (58 removals; 16 additions; 2 shortened inventory negatives)")



def validate_yaml_authority(content: str, kind: str) -> None:
    """Pin effective event, root and permission YAML semantics, not just blob bytes."""
    if kind == "publisher":
        name = "Reconcile Backup Authority"
        paths = PUBLISHER_TRIGGER_PATHS
        tail = '  schedule:\n    - cron: "17 21 * * *"\n  workflow_dispatch:\n'
        roots = ["name: " + name, "on:", "permissions:", "concurrency:", "jobs:"]
    elif kind == "independent":
        name = "Reconcile Backup Authority Source Negative"
        paths = INDEPENDENT_TRIGGER_PATHS
        tail = ""
        roots = ["name: " + name, "on:", "permissions:", "jobs:"]
    else:
        raise SystemExit("backup authority unknown CI YAML kind")

    def event(key: str) -> str:
        return ("  " + key + ":\n    branches:\n      - so\n    paths:\n"
                + "".join('      - "' + item + '"\n' for item in paths))

    expected = "name: " + name + "\n\non:\n" + event("pull_request") + event("push") + tail
    if (content.count("\npermissions:\n") != 1
            or content.split("\npermissions:\n", 1)[0] != expected):
        raise SystemExit("backup authority " + kind + " exact event header drift")

    observed_roots = [
        line for line in content.splitlines()
        if line.strip() and not line[0].isspace()
        and not line.lstrip().startswith("#")
    ]
    if observed_roots != roots:
        raise SystemExit("backup authority " + kind + " root YAML key shadow drift")

    permission_rows = []
    for line in content.split("\npermissions:\n", 1)[1].splitlines():
        if line.strip() and not line[0].isspace():
            break
        if line.strip() and not line.lstrip().startswith("#"):
            permission_rows.append(line)
    if permission_rows != ["  contents: read"]:
        raise SystemExit("backup authority " + kind + " permission leaf shadow drift")


def prove_yaml_authority_negatives(publisher: str, independent: str) -> None:
    total = 0
    for kind, content in (("publisher", publisher), ("independent", independent)):
        validate_yaml_authority(content, kind)
        cases = [
            ("extra event", content.replace("on:\n", "on:\n  issues:\n", 1),
             "exact event header drift"),
        ]
        for label, suffix in (
            ("spaced on", "on :\n  issues:\n"),
            ("quoted on", "'on':\n  issues:\n"),
            ("spaced permissions", "permissions :\n  contents: write\n"),
            ("spaced jobs", "jobs : {}\n"),
        ):
            cases.append((label, content + "\n" + suffix, "root YAML key shadow drift"))
        anchor = "permissions:\n  contents: read\n"
        if content.count(anchor) != 1:
            raise SystemExit("backup authority " + kind + " permission mutation anchor drift")
        for label, extra in (
            ("spaced contents", "  contents : write\n"),
            ("quoted contents", "  'contents': write\n"),
        ):
            cases.append((label, content.replace(anchor, anchor + extra, 1),
                          "permission leaf shadow drift"))
        for label, altered, diagnostic in cases:
            if altered == content:
                raise SystemExit("backup authority " + kind + " YAML negative unchanged: " + label)
            try:
                validate_yaml_authority(altered, kind)
            except SystemExit as exc:
                expected = "backup authority " + kind + " " + diagnostic
                if str(exc) != expected:
                    raise SystemExit(
                        "backup authority " + kind + " YAML negative wrong diagnostic: "
                        + label + ": " + str(exc)
                    ) from exc
            else:
                raise SystemExit("backup authority " + kind + " accepted YAML mutation: " + label)
            total += 1
    if total != 14:
        raise SystemExit("backup authority YAML semantic negative count drift")
    print("PASS: backup authority publisher/independent YAML event/root/permission (14 exact-diagnostic negatives)")


def validate(publisher: str, independent: str) -> None:
    validate_trigger_reachability(publisher, "publisher")
    validate_trigger_reachability(independent, "independent")
    validate_yaml_authority(publisher, "publisher")
    validate_yaml_authority(independent, "independent")
    publisher_required = (
        ("  pull_request:\n    branches:\n      - so\n", 1),
        ("  push:\n    branches:\n      - so\n", 1),
        ("  schedule:\n", 1),
        ("  workflow_dispatch:\n", 1),
        ("permissions:\n  contents: read\n", 1),
        ("      contents: write\n", 1),
        (PR_SCOPE, 1), (WRITER_SCOPE, 1),
        (CHECKOUT, 2), (SETUP, 2),
        ("          persist-credentials: false\n", 1),
        ("          persist-credentials: true\n", 1),
        (PR_BASE, 1), (PUSH_REF, 1), (SHA_FORMAT, 2), (WRITER_EVENT, 1),
        ('test "$(git rev-parse HEAD)" = "$expected"', 2),
        ('echo "SOURCE_SHA=$expected" >> "$GITHUB_ENV"', 1),
        ("git reset --hard origin/so", 1),
        ("for reconcile_attempt in 1 2; do", 1),
    )
    independent_required = (
        "  pull_request:\n    branches:\n      - so\n",
        "  push:\n    branches:\n      - so\n",
        '      - "' + PUBLISHER + '"', '      - "' + INDEPENDENT + '"',
        '      - "' + SELF + '"', CHECKOUT, SETUP,
        "          persist-credentials: false\n", PR_BASE, PUSH_REF, SHA_FORMAT,
        "          python " + SELF, "permissions:\n  contents: read\n",
        "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')",
        'test "$(git rev-parse HEAD)" = "$expected"',
        'test -z "$(git status --porcelain)"',
    )
    for token, count in publisher_required:
        if publisher.count(token) != count:
            raise SystemExit("backup authority publisher source drift: " + token)
    for token in independent_required:
        if token not in independent:
            raise SystemExit("backup authority independent source drift: " + token)
    if blob(publisher) != REVIEWED_PUBLISHER or blob(independent) != REVIEWED_INDEPENDENT:
        raise SystemExit("backup authority complete Git blob source drift")


def predicate_runtime(publisher: str, independent: str) -> None:
    for name, content, cmd in (
        ("publisher PR", publisher, PR_BASE),
        ("publisher writer", publisher, PUSH_REF),
        ("publisher event", publisher, WRITER_EVENT),
        ("independent PR", independent, PR_BASE),
        ("independent push", independent, PUSH_REF),
    ):
        if content.count(cmd) != 1:
            raise SystemExit("backup authority runtime predicate missing/ambiguous: " + name)
    if publisher.count(SHA_FORMAT) != 2 or independent.count(SHA_FORMAT) != 1:
        raise SystemExit("backup authority SHA runtime predicate drift")
    for command, key, value, allow in (
        (PR_BASE, "GITHUB_BASE_REF", "so", True),
        (PR_BASE, "GITHUB_BASE_REF", "main", False),
        (PR_BASE, "GITHUB_BASE_REF", "", False),
        (PUSH_REF, "GITHUB_REF", "refs/heads/so", True),
        (PUSH_REF, "GITHUB_REF", "refs/heads/main", False),
        (PUSH_REF, "GITHUB_REF", "refs/tags/v1", False),
    ):
        r = subprocess.run(["bash", "-e", "-c", command],
                           env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value},
                           capture_output=True, check=False)
        if (r.returncode == 0) != allow:
            raise SystemExit("backup authority runtime branch/base predicate drift")
    for value, allow in (("a" * 40, True), ("0" * 40, True), ("a" * 39, False),
                         ("A" * 40, False), ("g" * 40, False), ("", False)):
        r = subprocess.run(["bash", "-e", "-c", SHA_FORMAT],
                           env=dict(os.environ, expected=value), capture_output=True, check=False)
        if (r.returncode == 0) != allow:
            raise SystemExit("backup authority runtime SHA predicate drift")
    for event, allow in (("push", True), ("workflow_dispatch", True), ("schedule", True),
                         ("pull_request", False), ("", False)):
        r = subprocess.run(["bash", "-e", "-c", WRITER_EVENT],
                           env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GITHUB_EVENT_NAME": event},
                           capture_output=True, check=False)
        if (r.returncode == 0) != allow:
            raise SystemExit("backup authority runtime writer event predicate drift")
    print("PASS: backup authority branch/base (6), SHA (6) and writer event (5) runtime cases")


def source_negatives(publisher: str, independent: str) -> None:
    p_cases = (
        ("PR target", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("push target", "  push:\n    branches:\n      - so\n", "  push:\n"),
        ("PR scope", PR_SCOPE, "    if: always()"),
        ("writer scope", WRITER_SCOPE, "    if: always()"),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("PR credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("writer credentials", "          persist-credentials: true\n", "          persist-credentials: false\n"),
        ("PR base", PR_BASE, "true"),
        ("writer branch", PUSH_REF, "true"),
        ("SHA format", SHA_FORMAT, 'test -n "$expected"'),
        ("writer event", WRITER_EVENT, "true"),
        ("latest reset", "git reset --hard origin/so", "true"),
        ("bounded retry", "for reconcile_attempt in 1 2; do", "for reconcile_attempt in 1; do"),
        ("root write", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
    )
    i_cases = (
        ("PR base", PR_BASE, "true"), ("push branch", PUSH_REF, "true"),
        ("SHA format", SHA_FORMAT, 'test -n "$expected"'),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("self trigger", '      - "' + SELF + '"', ""),
        ("publisher trigger", '      - "' + PUBLISHER + '"', ""),
        ("root write", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("job scope", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')", "    if: always()"),
    )
    for name, original, cases in (("publisher", publisher, p_cases), ("independent", independent, i_cases)):
        for label, old, new in cases:
            if old not in original:
                raise SystemExit("backup authority negative fixture missing: " + name + "/" + label)
            altered = original.replace(old, new, 1)
            if altered == original:
                raise SystemExit("backup authority negative fixture unchanged: " + name + "/" + label)
            try:
                validate(altered, independent) if name == "publisher" else validate(publisher, altered)
            except SystemExit:
                continue
            raise SystemExit("backup authority accepted source mutation: " + name + "/" + label)
    print("PASS: backup authority publisher (15) and independent (10) source mutations")


def main() -> int:
    publisher, independent = source(PUBLISHER), source(INDEPENDENT)
    validate(publisher, independent)
    prove_trigger_reachability_negatives(publisher, independent)
    prove_yaml_authority_negatives(publisher, independent)
    predicate_runtime(publisher, independent)
    source_negatives(publisher, independent)
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
