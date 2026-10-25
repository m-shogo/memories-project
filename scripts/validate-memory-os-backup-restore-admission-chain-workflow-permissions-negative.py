#!/usr/bin/env python3
"""Negative coverage for backup/restore admission-chain workflow permissions."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-backup-restore-admission-chain-workflow-permissions.py"
RUNNER_NEGATIVE_PATH = ROOT / "scripts/validate-memory-os-backup-restore-admission-chain-full-negative.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_backup_restore_admission_chain_workflow_permissions", VALIDATOR_PATH)
    require(spec is not None and spec.loader is not None, "cannot load admission-chain permission validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_reject(module, label: str, mutated: str) -> None:
    original = module.exact_workflow
    module.exact_workflow = lambda: mutated
    try:
        try:
            module.main()
        except module.Fail:
            return
        raise Fail(f"permission validator accepted forbidden mutation: {label}")
    finally:
        module.exact_workflow = original


def replace_once(text: str, old: str, new: str, label: str) -> str:
    require(text.count(old) == 1, f"negative fixture boundary drift for {label}: expected exactly one match")
    return text.replace(old, new, 1)


def replace_all(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    require(count > 0, f"negative fixture boundary drift for {label}: expected at least one match")
    return text.replace(old, new)


def run_runner_negative() -> None:
    require(RUNNER_NEGATIVE_PATH.is_file() and not RUNNER_NEGATIVE_PATH.is_symlink(), "admission-chain full runner negative authority missing or substituted")
    completed = subprocess.run(
        [sys.executable, str(RUNNER_NEGATIVE_PATH)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    output = f"{completed.stdout}{completed.stderr}"
    if output:
        print(output, end="" if output.endswith("\n") else "\n")
    require(completed.returncode == 0, "admission-chain full runner negative proof failed")


def main() -> int:
    module = load_validator()
    canonical = module.exact_workflow()

    cases = (
        (
            "pull_request_target trigger",
            canonical.replace("  pull_request:\n", "  pull_request_target:\n", 1),
        ),
        (
            "workflow-level write permission",
            replace_once(canonical, "permissions:\n  contents: read\n", "permissions:\n  contents: write\n", "workflow-level permission"),
        ),
        (
            "PR write permission",
            replace_once(canonical, "permissions:\n      contents: read\n", "permissions:\n      contents: write\n", "PR job permission"),
        ),
        (
            "PR runtime event checkout",
            replace_once(canonical, "ref: ${{ github.event.pull_request.head.sha }}", "ref: ${{ github.sha }}", "PR exact-head checkout"),
        ),
        (
            "PR clean-worktree assertion removed",
            replace_once(
                canonical,
                'test -z "$(git status --porcelain --untracked-files=all)"',
                'echo "PR workspace cleanliness check removed"',
                "PR clean-worktree assertion",
            ),
        ),
        (
            "publication allowed on pull requests",
            replace_once(canonical, "if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'", "if: github.event_name == 'pull_request'", "publication PR exclusion"),
        ),
        (
            "publication source identity check removed",
            replace_once(canonical, "test \"$(git rev-parse HEAD)\" = \"$GITHUB_SHA\"", "echo \"source identity check removed\"", "publication source identity"),
        ),
        (
            "bounded stale-authority refusal removed",
            replace_all(canonical, "refusing stale derived authority", "allowing stale derived authority", "stale authority refusal"),
        ),
        (
            "stale diagnostic refusal removed",
            replace_all(canonical, "refusing stale failure diagnostic", "allowing stale failure diagnostic", "stale diagnostic refusal"),
        ),
        (
            "atomic diagnostic replacement removed",
            replace_once(canonical, "os.replace(tmp_name, path)", "path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')", "atomic diagnostic replacement"),
        ),
    )

    # Exercise additional existing fail-closed boundaries without mutating the
    # canonical workflow or widening production/publication authority.
    cases += (
        (
            "PR-only validation condition removed",
            replace_once(canonical, "if: github.event_name == 'pull_request'", "if: github.event_name != 'pull_request'", "PR-only condition"),
        ),
        (
            "PR explicit read-only grant removed",
            replace_once(canonical, "permissions:\n      contents: read\n", "", "PR read-only grant"),
        ),
        (
            "PR deterministic drift rejection removed",
            replace_once(canonical, "git diff --exit-code", "echo 'skip PR drift check'", "PR deterministic drift check"),
        ),
        (
            "canonical chain runner skipped",
            replace_all(canonical, "python scripts/validate-memory-os-backup-restore-admission-chain-full.py", "echo 'skip canonical chain'", "canonical full-chain runner"),
        ),
        (
            "bounded latest-so reset removed",
            replace_once(canonical, "git reset --hard origin/so", "echo 'skip latest-so reset'", "bounded latest-so reset"),
        ),
        (
            "publication derived-only mutation guard removed",
            replace_all(canonical, "assert_only_derived_chain_changes", "skip_derived_chain_check", "derived-only publication guard"),
        ),
        (
            "publication write grant removed",
            replace_once(canonical, "permissions:\n      contents: write\n", "permissions:\n      contents: read\n", "publication-only write grant"),
        ),
        (
            "failure diagnostic fsync removed",
            replace_once(canonical, "os.fsync(handle.fileno())", "pass  # no fsync", "atomic diagnostic fsync"),
        ),
    )

    # Fail closed on mutable or substituted bootstrap actions and PR credential leakage.
    cases += (
        (
            "PR checkout floating tag",
            replace_once(canonical, "      - name: Checkout exact PR source\n        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", "      - name: Checkout exact PR source\n        uses: actions/checkout@v4\n", "PR checkout floating tag"),
        ),
        (
            "PR checkout substituted SHA",
            replace_once(canonical, "      - name: Checkout exact PR source\n        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", "      - name: Checkout exact PR source\n        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677263\n", "PR checkout substituted SHA"),
        ),
        (
            "publication checkout floating tag",
            replace_once(canonical, "      - name: Checkout exact publication source\n        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", "      - name: Checkout exact publication source\n        uses: actions/checkout@v4\n", "publication checkout floating tag"),
        ),
        (
            "publication checkout substituted SHA",
            replace_once(canonical, "      - name: Checkout exact publication source\n        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", "      - name: Checkout exact publication source\n        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677263\n", "publication checkout substituted SHA"),
        ),
        (
            "PR setup floating tag",
            replace_once(canonical, "        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n        with:\n          python-version: \"3.12\"\n\n      - name: Verify exact clean PR authority source\n", "        uses: actions/setup-python@v5\n        with:\n          python-version: \"3.12\"\n\n      - name: Verify exact clean PR authority source\n", "PR setup floating tag"),
        ),
        (
            "PR setup substituted SHA",
            replace_once(canonical, "        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n        with:\n          python-version: \"3.12\"\n\n      - name: Verify exact clean PR authority source\n", "        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87064\n        with:\n          python-version: \"3.12\"\n\n      - name: Verify exact clean PR authority source\n", "PR setup substituted SHA"),
        ),
        (
            "publication setup floating tag",
            replace_once(canonical, "        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n        with:\n          python-version: \"3.12\"\n\n      - name: Capture exact chain authority source\n", "        uses: actions/setup-python@v5\n        with:\n          python-version: \"3.12\"\n\n      - name: Capture exact chain authority source\n", "publication setup floating tag"),
        ),
        (
            "publication setup substituted SHA",
            replace_once(canonical, "        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n        with:\n          python-version: \"3.12\"\n\n      - name: Capture exact chain authority source\n", "        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87064\n        with:\n          python-version: \"3.12\"\n\n      - name: Capture exact chain authority source\n", "publication setup substituted SHA"),
        ),
        (
            "PR checkout credential persistence enabled",
            replace_once(canonical, "          persist-credentials: false\n\n      - name: Set up Python", "          persist-credentials: true\n\n      - name: Set up Python", "PR checkout credential persistence enabled"),
        ),
        (
            "PR checkout credential persistence removed",
            replace_once(canonical, "          persist-credentials: false\n\n      - name: Set up Python", "\n      - name: Set up Python", "PR checkout credential persistence removed"),
        ),
        (
            "publication checkout credentials disabled",
            replace_once(canonical, "          persist-credentials: true\n\n      - name: Set up Python", "          persist-credentials: false\n\n      - name: Set up Python", "publication checkout credentials disabled"),
        ),
        (
            "publication checkout credential intent removed",
            replace_once(canonical, "          persist-credentials: true\n\n      - name: Set up Python", "\n      - name: Set up Python", "publication checkout credential intent removed"),
        ),
    )

    # Write-capable publication is admitted only for reviewed so push/dispatch.
    cases += (
        (
            "publication unscoped non-PR event",
            replace_once(canonical, "if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'", "if: github.event_name != 'pull_request'", "publication unscoped non-PR event"),
        ),
        (
            "publication redirected to main",
            replace_once(canonical, "if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'", "if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/main'", "publication redirected to main"),
        ),
        (
            "publication allows PR target",
            replace_once(canonical, "if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'", "if: (github.event_name == 'pull_request_target' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'", "publication allows PR target"),
        ),
        (
            "publication dispatch without branch scope",
            replace_once(canonical, "if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'", "if: github.event_name == 'workflow_dispatch'", "publication dispatch without branch scope"),
        ),
        (
            "publication push without branch scope",
            replace_once(canonical, "if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'", "if: github.event_name == 'push'", "publication push without branch scope"),
        ),
        (
            "publication unconditional write job",
            replace_once(canonical, "if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'", "if: true", "publication unconditional write job"),
        ),
        (
            "publication duplicate job if override",
            replace_once(canonical, "  validate-and-publish:\n    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n", "  validate-and-publish:\n    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n    if: true\n", "publication duplicate job if override"),
        ),
        (
            "publication dispatch path substituted",
            replace_once(canonical, "if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'", "if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.event.pull_request.base.ref == 'refs/heads/so'", "publication dispatch path substituted"),
        ),
    )

    # Reject quoted/duplicate YAML job keys that can override reviewed authority.
    cases += (
        (
            "publisher quoted if override",
            replace_once(canonical, "  validate-and-publish:\n", "  validate-and-publish:\n    \"if\": true\n", "publisher quoted if override"),
        ),
        (
            "publisher single-quoted if override",
            replace_once(canonical, "  validate-and-publish:\n", "  validate-and-publish:\n    'if': true\n", "publisher single-quoted if override"),
        ),
        (
            "publisher quoted permission override",
            replace_once(canonical, "  validate-and-publish:\n", "  validate-and-publish:\n    \"permissions\":\n      contents: write\n", "publisher quoted permission override"),
        ),
        (
            "publisher quoted steps override",
            replace_once(canonical, "  validate-and-publish:\n", "  validate-and-publish:\n    \"steps\": []\n", "publisher quoted steps override"),
        ),
        (
            "publisher extra environment",
            replace_once(canonical, "  validate-and-publish:\n", "  validate-and-publish:\n    environment: production\n", "publisher extra environment"),
        ),
        (
            "PR quoted permissions override",
            replace_once(canonical, "  validate-pr:\n", "  validate-pr:\n    \"permissions\":\n      contents: write\n", "PR quoted permissions override"),
        ),
        (
            "PR quoted steps override",
            replace_once(canonical, "  validate-pr:\n", "  validate-pr:\n    'steps': []\n", "PR quoted steps override"),
        ),
        (
            "PR duplicate job if",
            replace_once(canonical, "  validate-pr:\n", "  validate-pr:\n    if: true\n", "PR duplicate job if"),
        ),
    )

    for label, mutated in cases:
        require(mutated != canonical, f"negative mutation did not change workflow: {label}")
        expect_reject(module, label, mutated)

    # Independently mutate the permission-check workflow bootstrap and PR identity.
    independent = module.independent_permission_workflow()
    module.validate_independent_permission_workflow(independent)
    independent_cases = (
        ("independent floating checkout", replace_once(independent, "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262", "uses: actions/checkout@v4", "independent floating checkout")),
        ("independent substituted checkout SHA", replace_once(independent, "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262", "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677263", "independent substituted checkout SHA")),
        ("independent floating setup-python", replace_once(independent, "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", "uses: actions/setup-python@v5", "independent floating setup-python")),
        ("independent substituted setup-python SHA", replace_once(independent, "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87064", "independent substituted setup-python SHA")),
        ("independent persisted PR credentials", replace_once(independent, "          persist-credentials: false\n", "          persist-credentials: true\n", "independent persisted PR credentials")),
        ("independent missing credential isolation", replace_once(independent, "          persist-credentials: false\n", "", "independent missing credential isolation")),
        ("independent missing PR SHA format check", replace_once(independent, "            [[ \"$PR_HEAD_SHA\" =~ ^[0-9a-f]{40}$ ]]\n", "", "independent missing PR SHA format check")),
        ("independent PR HEAD check bypass", replace_once(independent, "            test \"$(git rev-parse HEAD)\" = \"$PR_HEAD_SHA\"\n", "            test \"$(git rev-parse HEAD)\" = \"$GITHUB_SHA\"\n", "independent PR HEAD check bypass")),
        ("independent extra action step", replace_once(independent, "      - name: Require exact clean source\n", "      - uses: synthetic/unreviewed@v1\n      - name: Require exact clean source\n", "independent extra action step")),
        ("independent token write elevation", replace_once(independent, "permissions:\n  contents: read\n", "permissions:\n  contents: write\n", "independent token write elevation")),
        ("independent PR target event", replace_once(independent, "  pull_request:\n", "  pull_request_target:\n", "independent PR target event")),
    )
    independent_cases += (
        ("independent extra named action step",
         replace_once(independent, "      - name: Require exact clean source\n",
                      "      - name: Unreviewed action\n        uses: synthetic/unreviewed@v1\n      - name: Require exact clean source\n",
                      "independent extra named action step")),
        ("independent quoted step header",
         replace_once(independent, "      - name: Require exact clean source\n",
                      "      - 'name': Require exact clean source\n",
                      "independent quoted step header")),
    )
    for label, mutated in independent_cases:
        require(mutated != independent, f"independent mutation unchanged: {label}")
        try:
            module.validate_independent_permission_workflow(mutated)
        except module.Fail:
            pass
        else:
            raise Fail(f"independent permission workflow mutation accepted: {label}")

    # Independent complete-source binding catches shell-body and trigger changes
    # even when the approved step/header inventory remains intact.
    independent_blob_cases = (
        ("independent injected shell command",
         replace_once(independent,
                      "          python -m py_compile",
                      "          echo UNREVIEWED\n          python -m py_compile",
                      "independent injected shell command")),
        ("independent relaxed shell",
         replace_once(independent,
                      "          set -euo pipefail\n          python -m py_compile",
                      "          set +e\n          python -m py_compile",
                      "independent relaxed shell")),
        ("independent dropped PR trigger path",
         independent.replace(
             '      - ".github/workflows/backup-restore-permission-boundary-negative.yml"\n',
             "", 1)),
        ("independent skipped generation guard",
         replace_once(independent,
                      "        run: python scripts/validate-memory-os-backup-restore-generation-evidence-permission-negative.py\n",
                      "        run: echo UNREVIEWED\n",
                      "independent skipped generation guard")),
        ("independent injected workflow environment",
         replace_once(independent,
                      "permissions:\n  contents: read\n",
                      "permissions:\n  contents: read\nenv:\n  UNREVIEWED: true\n",
                      "independent injected workflow environment")),
    )
    require(independent.count(
        '      - ".github/workflows/backup-restore-admission-chain-negative.yml"\n'
    ) == 2, "independent permission trigger fixture inventory drift")
    independent_trigger_cases = (
        ("independent removed negative CI PR trigger",
         independent.replace(
             '      - ".github/workflows/backup-restore-admission-chain-negative.yml"\n',
             "", 1)),
        ("independent removed negative CI push trigger",
         independent.split("  push:\n", 1)[0] + "  push:\n" +
         independent.split("  push:\n", 1)[1].replace(
             '      - ".github/workflows/backup-restore-admission-chain-negative.yml"\n',
             "", 1)),
    )
    independent_blob_cases += independent_trigger_cases
    for label, mutated in independent_blob_cases:
        require(mutated != independent, f"independent blob mutation unchanged: {label}")
        try:
            module.require_reviewed_independent_permission_workflow_blob(mutated)
        except module.Fail:
            pass
        else:
            raise Fail(f"independent permission workflow complete-source mutation accepted: {label}")

    require(module.exact_workflow() == canonical, "negative suite mutated canonical workflow authority")
    run_runner_negative()
    print("Backup/restore admission-chain workflow permission negative PASS")
    print(f"forbidden workflow mutations rejected: {len(cases)}")
    print(f"independent permission workflow source mutations rejected: {len(independent_cases)}")
    print(f"independent complete-source mutations rejected: {len(independent_blob_cases)}")
    print("full runner fail-closed negative proof executed: true")
    print("PR tracked/untracked workspace mutation accepted: false")
    print("crash-safe failure diagnostic publication required: true")
    print("production evidence created: false")
    print("production traffic changed: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ADMISSION CHAIN WORKFLOW PERMISSION NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
