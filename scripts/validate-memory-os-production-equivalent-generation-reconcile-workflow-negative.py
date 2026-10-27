#!/usr/bin/env python3
"""Fail-closed source-admission negatives for environment generation reconcile CI."""

from __future__ import annotations

import ast
import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/production-equivalent-environment-generation-reconcile-negative.yml"
REVIEWED_WORKFLOW_BLOB_SHA = "b9a8cbca80fb3068b975f1394bb581193a5dd851"
REQUIRED = (
    ("checkout SHA", "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", 1),
    ("setup-python SHA", "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n", 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("PR checkout", "          ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n", 1),
    ("PR event", '          if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" ]]; then\n', 1),
    ("PR head", '            expected="${{ github.event.pull_request.head.sha }}"\n', 1),
    ("SHA format", '            [[ "$expected" =~ ^[0-9a-f]{40}$ ]]\n', 2),
    ("event whitelist", '          elif [[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]; then\n', 1),
    ("branch", '            test "${GITHUB_REF:-}" = "refs/heads/so"\n', 1),
    ("unreviewed event", '          else\n            echo "Unreviewed environment generation reconcile negative event" >&2\n            exit 1\n          fi\n', 1),
    ("source HEAD", '          test "$(git rev-parse HEAD)" = "$expected"\n', 1),
    ("clean source", '          test -z "$(git status --porcelain)"\n', 2),
    ("self-trigger", '      - "scripts/validate-memory-os-production-equivalent-generation-reconcile-workflow-negative.py"\n', 2),
    ("self-execution", '          python scripts/validate-memory-os-production-equivalent-generation-reconcile-workflow-negative.py\n', 1),
    ("PR target", "  pull_request:\n    branches: [so]\n    paths:\n", 1),
    ("PR base environment", "          PR_BASE_REF: ${{ github.base_ref }}\n", 1),
    ("PR base assertion", '            test "${PR_BASE_REF:-}" = "so"\n', 1),
)


def validate(source: str) -> None:
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit(f"reconcile workflow source boundary drift: {label}")
    payload = source.encode("utf-8")
    blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    if hashlib.sha1(blob).hexdigest() != REVIEWED_WORKFLOW_BLOB_SHA:
        raise SystemExit("environment generation reconcile complete workflow source drift")


def prove_branch_guards_runtime() -> None:
    """Execute exact reviewed PR and push predicates under synthetic refs."""
    cases = (
        ("PR so", REQUIRED[16][1].strip(), "PR_BASE_REF", "so", True),
        ("PR main", REQUIRED[16][1].strip(), "PR_BASE_REF", "main", False),
        ("PR missing", REQUIRED[16][1].strip(), "PR_BASE_REF", "", False),
        ("push so", REQUIRED[8][1].strip(), "GITHUB_REF", "refs/heads/so", True),
        ("push main", REQUIRED[8][1].strip(), "GITHUB_REF", "refs/heads/main", False),
        ("push tag", REQUIRED[8][1].strip(), "GITHUB_REF", "refs/tags/v1", False),
    )
    for label, command, key, value, expected in cases:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}
        result = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
        if (result.returncode == 0) != expected:
            raise SystemExit("environment generation reconcile runtime branch guard drift: " + label)
    print("PASS: environment generation reconcile PR/push branch guard runtime (6 cases)")


RECONCILE_NEGATIVE = ROOT / "scripts/validate-memory-os-production-equivalent-generation-reconcile-negative.py"
REAL_WRITER_NEGATIVES = (
    "prove_private_child_validator",
    "prove_private_atomic_authority_writer",
    "prove_private_bounded_authority_reader",
    "prove_strict_authority_json",
)


def check_reconcile_negative_reachability(tree: ast.Module) -> None:
    mains = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name == "main"]
    if len(mains) != 1:
        raise SystemExit("generation reconcile negative main authority drift")
    for function in REAL_WRITER_NEGATIVES:
        definitions = [node for node in tree.body
                       if isinstance(node, ast.FunctionDef) and node.name == function]
        calls = [node for node in mains[0].body
                 if isinstance(node, ast.Expr)
                 and isinstance(node.value, ast.Call)
                 and isinstance(node.value.func, ast.Name)
                 and node.value.func.id == function
                 and node.value.args
                 and isinstance(node.value.args[0], ast.Name)
                 and node.value.args[0].id == "reconciler"
                 and not node.value.keywords]
        if len(definitions) != 1 or len(calls) != 1:
            raise SystemExit("generation reconcile real-writer negative invocation missing: " + function)


def prove_reconcile_negative_reachability() -> None:
    """Remove each real-writer negative call in-memory and require rejection."""
    if RECONCILE_NEGATIVE.is_symlink() or not RECONCILE_NEGATIVE.is_file():
        raise SystemExit("generation reconcile negative source substituted")
    source = RECONCILE_NEGATIVE.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(RECONCILE_NEGATIVE))
    except SyntaxError:
        raise SystemExit("generation reconcile negative source syntax invalid") from None
    check_reconcile_negative_reachability(tree)
    for function in REAL_WRITER_NEGATIVES:
        mutated = ast.parse(source, filename=str(RECONCILE_NEGATIVE))
        main = next(node for node in mutated.body
                    if isinstance(node, ast.FunctionDef) and node.name == "main")
        main.body = [node for node in main.body
                     if not (isinstance(node, ast.Expr)
                             and isinstance(node.value, ast.Call)
                             and isinstance(node.value.func, ast.Name)
                             and node.value.func.id == function)]
        try:
            check_reconcile_negative_reachability(mutated)
        except SystemExit:
            continue
        raise SystemExit("generation reconcile negative removal mutation accepted: " + function)
    print("PASS: generation reconcile real-writer negative AST reachability (4 removals)")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_branch_guards_runtime()
    prove_reconcile_negative_reachability()
    cases = (
        ("checkout SHA", REQUIRED[0][1], "      - uses: actions/checkout@v4\n"),
        ("setup-python SHA", REQUIRED[1][1], "      - uses: actions/setup-python@v5\n"),
        ("persist credentials", REQUIRED[2][1], ""),
        ("PR source checkout", REQUIRED[3][1], "          ref: ${{ github.sha }}\n"),
        ("PR event admission", REQUIRED[4][1], ""),
        ("PR head SHA", REQUIRED[5][1], '            expected="${GITHUB_SHA:-}"\n'),
        ("SHA format", REQUIRED[6][1], '            test -n "$expected"\n'),
        ("event whitelist", REQUIRED[7][1], ""),
        ("push/dispatch branch", REQUIRED[8][1], ""),
        ("unreviewed event rejection", REQUIRED[9][1], ""),
        ("source HEAD", REQUIRED[10][1], ""),
        ("clean source", REQUIRED[11][1], ""),
        ("self-trigger", REQUIRED[12][1], ""),
        ("self-execution", REQUIRED[13][1], ""),
        ("PR target", REQUIRED[14][1], "  pull_request:\n    branches: [main]\n    paths:\n"),
        ("PR base environment", REQUIRED[15][1], ""),
        ("PR base assertion", REQUIRED[16][1], '            test -n "${PR_BASE_REF:-}"\n'),
        ("injected shell", "          python scripts/validate-memory-os-production-equivalent-generation-reconcile-workflow-negative.py\n", "          echo UNREVIEWED\n          python scripts/validate-memory-os-production-equivalent-generation-reconcile-workflow-negative.py\n"),
        ("injected action", "      - name: Prove transactional environment-generation reconciliation\n", "      - uses: unreviewed/action@v1\n      - name: Prove transactional environment-generation reconciliation\n"),
        ("removed PR self-trigger", '      - "scripts/validate-memory-os-production-equivalent-generation-reconcile-workflow-negative.py"\n', ""),
    )
    if len(cases) != 20:
        raise SystemExit("environment generation reconcile negative inventory drift")
    for label, old, replacement in cases:
        if old not in source:
            raise SystemExit(f"reconcile workflow negative anchor missing: {label}")
        mutated = source.replace(old, replacement, 1)
        try:
            validate(mutated)
        except SystemExit:
            continue
        raise SystemExit(f"reconcile workflow accepted forbidden mutation: {label}")
    print(f"PASS: environment generation reconcile workflow source admission ({len(cases)} negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
