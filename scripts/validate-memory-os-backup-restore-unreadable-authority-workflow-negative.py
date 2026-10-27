#!/usr/bin/env python3
"""Fail-closed source-admission negatives for unreadable-authority negative CI."""

from __future__ import annotations

import ast
import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-unreadable-authority-negative.yml"
LOAD_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence-load-negative.py"
REVIEWED_WORKFLOW_BLOB_SHA = "f1a8c3d7b2503c5192ca3de57892ae31ab521ba7"
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
    ("unreviewed event", '          else\n            echo "Unreviewed unreadable-authority negative event" >&2\n            exit 1\n          fi\n', 1),
    ("source HEAD", '          test "$(git rev-parse HEAD)" = "$expected"\n', 1),
    ("clean source", '          test -z "$(git status --porcelain)"\n', 2),
    ("self-trigger", '      - "scripts/validate-memory-os-backup-restore-unreadable-authority-workflow-negative.py"\n', 2),
    ("self-execution", '          python scripts/validate-memory-os-backup-restore-unreadable-authority-workflow-negative.py\n', 1),
    ("PR target", "  pull_request:\n    branches: [so]\n    paths:\n", 1),
    ("PR base environment", "          PR_BASE_REF: ${{ github.base_ref }}\n", 1),
    ("PR base assertion", '            test "${PR_BASE_REF:-}" = "so"\n', 1),
)


def validate(source: str) -> None:
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit(f"unreadable-authority negative workflow source boundary drift: {label}")
    payload = source.encode("utf-8")
    blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    if hashlib.sha1(blob).hexdigest() != REVIEWED_WORKFLOW_BLOB_SHA:
        raise SystemExit("unreadable-authority negative complete workflow source drift")


def prove_branch_guards_runtime() -> None:
    """Execute reviewed PR and push branch guards with disposable refs."""
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
            raise SystemExit("unreadable-authority negative runtime branch guard drift: " + label)
    print("PASS: unreadable-authority negative PR/push branch guard runtime (6 cases)")



def require_generation_json_negative_reachable(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        raise SystemExit("generation evidence load negative syntax invalid") from None
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    if "prove_generation_evidence_json_reader" not in functions or "main" not in functions:
        raise SystemExit("generation evidence JSON reader negative missing")
    calls = [
        node for node in ast.walk(functions["main"])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "prove_generation_evidence_json_reader"
    ]
    if len(calls) != 1:
        raise SystemExit("generation evidence JSON reader negative invocation drift")
    if "prove_generation_private_authority_path_diagnostics" not in functions:
        raise SystemExit("generation recovery private missing-authority negative missing")
    private_calls = [node for node in ast.walk(functions["main"])
                     if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                     and node.func.id == "prove_generation_private_authority_path_diagnostics"]
    if len(private_calls) != 1:
        raise SystemExit("generation recovery private missing-authority negative invocation drift")


def prove_generation_json_negative_removal_rejected() -> None:
    code = LOAD_NEGATIVE.read_text(encoding="utf-8")
    require_generation_json_negative_reachable(code)
    anchor = "    prove_generation_evidence_json_reader(validator)\n"
    if code.count(anchor) != 1:
        raise SystemExit("generation evidence JSON reader negative removal anchor drift")
    mutated = code.replace(anchor, "    pass\n", 1)
    try:
        require_generation_json_negative_reachable(mutated)
    except SystemExit:
        pass
    else:
        raise SystemExit("generation evidence JSON reader negative deletion accepted")
    print("PASS: generation evidence JSON reader negative execution deletion rejected")
    private_anchor = "    prove_generation_private_authority_path_diagnostics(validator)\n"
    if code.count(private_anchor) != 1:
        raise SystemExit("generation recovery private missing-authority removal anchor drift")
    mutated_private = code.replace(private_anchor, "    pass\n", 1)
    try:
        require_generation_json_negative_reachable(mutated_private)
    except SystemExit:
        pass
    else:
        raise SystemExit("generation recovery private missing-authority negative deletion accepted")
    print("PASS: generation recovery private missing-authority negative deletion rejected")



def require_generation_json_parent_swap_negative_reachable(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        raise SystemExit("generation recovery JSON parent swap negative syntax invalid") from None
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    target = functions.get("prove_generation_evidence_json_reader")
    if target is None:
        raise SystemExit("generation recovery JSON parent swap negative missing")
    nested = {node.name for node in ast.walk(target) if isinstance(node, ast.FunctionDef)}
    if not {"swap_before_descent", "swap_after_pin"}.issubset(nested):
        raise SystemExit("generation recovery JSON parent swap negative removed")
    assignments = [node.value.id for node in ast.walk(target) if isinstance(node, ast.Assign)
                   and isinstance(node.value, ast.Name)
                   and any(isinstance(entry, ast.Attribute) and entry.attr == "open"
                           for entry in node.targets)]
    if not {"swap_before_descent", "swap_after_pin"}.issubset(assignments):
        raise SystemExit("generation recovery JSON parent swap negative unreachable")


def prove_generation_json_parent_swap_negative_removal_rejected() -> None:
    code = LOAD_NEGATIVE.read_text(encoding="utf-8")
    require_generation_json_parent_swap_negative_reachable(code)
    start = '        with tempfile.TemporaryDirectory(prefix="memory-os-recovery-json-parent-canary-") as outside:\n'
    end = '        require(path.read_bytes() == positive, "generation recovery JSON mutated positive fixture")\n'
    if code.count(start) != 1 or code.count(end) != 1:
        raise SystemExit("generation recovery JSON parent swap negative removal anchor drift")
    left = code.index(start)
    right = code.index(end, left)
    mutated = code[:left] + code[right:]
    try:
        require_generation_json_parent_swap_negative_reachable(mutated)
    except SystemExit:
        pass
    else:
        raise SystemExit("generation recovery JSON parent swap negative deletion accepted")
    print("PASS: generation recovery JSON ancestor swap negative deletion rejected")


def require_generation_json_descriptor_fault_negative_reachable(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        raise SystemExit("generation recovery JSON descriptor fault negative syntax invalid") from None
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    target = functions.get("prove_generation_evidence_json_reader")
    if target is None:
        raise SystemExit("generation recovery JSON descriptor fault negative missing")
    nested = {node.name for node in ast.walk(target) if isinstance(node, ast.FunctionDef)}
    if not {"close_then_fail", "fdopen_then_fail"}.issubset(nested):
        raise SystemExit("generation recovery JSON descriptor fault injection missing")
    injections = {node.value.id for node in ast.walk(target)
                  if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name)
                  and any(isinstance(entry, ast.Attribute) and entry.attr in {"close", "fdopen"}
                          for entry in node.targets)}
    if not {"close_then_fail", "fdopen_then_fail"}.issubset(injections):
        raise SystemExit("generation recovery JSON descriptor fault injection unreachable")
    messages = {node.value for node in ast.walk(target)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    if not {"generation recovery JSON cleanup failed", "generation recovery JSON unreadable or invalid"}.issubset(messages):
        raise SystemExit("generation recovery JSON descriptor fault classifications missing")


def prove_generation_json_descriptor_fault_negative_deletion_rejected() -> None:
    code = LOAD_NEGATIVE.read_text(encoding="utf-8")
    require_generation_json_descriptor_fault_negative_reachable(code)
    start = '        # A directory close error must not silently certify an unsafe read.\n'
    end = '        for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY"):\n'
    if code.count(start) != 1 or code.count(end) != 1:
        raise SystemExit("generation recovery JSON descriptor fault deletion anchor drift")
    mutated = code[:code.index(start)] + code[code.index(end, code.index(start)):]
    try:
        require_generation_json_descriptor_fault_negative_reachable(mutated)
    except SystemExit:
        pass
    else:
        raise SystemExit("generation recovery JSON descriptor fault negative deletion accepted")
    print("PASS: generation recovery JSON descriptor fault negative deletion rejected")


def require_pinned_json_race_negative_reachable(source: str, function_name: str) -> None:
    """Independent AST proof that both real-reader races are executed."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        raise SystemExit("pinned JSON race negative syntax invalid") from None
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    target = functions.get(function_name)
    main = functions.get("main")
    if target is None or main is None:
        raise SystemExit("pinned JSON race negative function missing")
    calls = [node for node in ast.walk(main)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
             and node.func.id == function_name]
    if len(calls) != 1:
        raise SystemExit("pinned JSON race negative main invocation drift")
    nested = {node.name for node in ast.walk(target) if isinstance(node, ast.FunctionDef)}
    if "swap_during_walk" not in nested:
        raise SystemExit("pinned JSON race injection function missing")
    assignments = [
        node for node in ast.walk(target)
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name)
        and node.value.id == "swap_during_walk"
        and any(isinstance(item, ast.Attribute) and isinstance(item.value, ast.Name)
                and item.value.id == "os" and item.attr == "open" for item in node.targets)
    ]
    if len(assignments) != 1:
        raise SystemExit("pinned JSON race injection not applied")
    strings = {node.value for node in ast.walk(target)
               if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    byte_literals = [node.value for node in ast.walk(target)
                     if isinstance(node, ast.Constant) and isinstance(node.value, bytes)]
    if not {"parent", "ancestor", "pinned"}.issubset(strings) or not any(
        b"SYNTHETIC_EXTERNAL_CANARY" in value for value in byte_literals
    ):
        raise SystemExit("pinned JSON race positive/canary coverage missing")


def mutate_named_function(source: str, function_name: str, anchor: str, replacement: str) -> str:
    """Limit repeated fixture tokens to the intended AST function's source span."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        raise SystemExit("named negative mutation source syntax invalid") from None
    targets = [node for node in tree.body
               if isinstance(node, ast.FunctionDef) and node.name == function_name]
    if len(targets) != 1:
        raise SystemExit("named negative mutation target missing")
    lines = source.splitlines(keepends=True)
    start, end = targets[0].lineno - 1, targets[0].end_lineno
    segment = "".join(lines[start:end])
    if segment.count(anchor) != 1:
        raise SystemExit("named negative mutation anchor missing or duplicated")
    lines[start:end] = [segment.replace(anchor, replacement, 1)]
    return "".join(lines)


def prove_pinned_json_race_negative_removal_rejected() -> None:
    for relative, function_name in (
        ("scripts/validate-memory-os-backup-restore-drill-preflight-negative.py",
         "expect_pinned_preflight_json_reader"),
        ("scripts/validate-memory-os-backup-restore-non-resurrection-load-negative.py",
         "prove_typed_json_reader_fd_races"),
    ):
        code = (ROOT / relative).read_text(encoding="utf-8")
        require_pinned_json_race_negative_reachable(code, function_name)
        for label, anchor in (
            ("invocation", f"    {function_name}(validator)\n"),
            ("race injection", "                os.open = swap_during_walk\n"),
        ):
            if label == "invocation":
                if code.count(anchor) != 1:
                    raise SystemExit("pinned JSON race deletion anchor drift: " + label)
                mutated = code.replace(anchor, "    pass\n", 1)
            else:
                mutated = mutate_named_function(code, function_name, anchor, "                pass\n")
            try:
                require_pinned_json_race_negative_reachable(mutated, function_name)
            except SystemExit:
                pass
            else:
                raise SystemExit("pinned JSON race deletion accepted: " + label)
    print("PASS: preflight and typed JSON race negative invocation/injection deletion rejected")


def require_json_descriptor_fault_negative_reachable(source: str, function_name: str) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        raise SystemExit("JSON descriptor fault negative syntax invalid") from None
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    target, main = functions.get(function_name), functions.get("main")
    if target is None or main is None:
        raise SystemExit("JSON descriptor fault negative missing")
    calls = [node for node in ast.walk(main)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
             and node.func.id == function_name]
    if len(calls) != 1:
        raise SystemExit("JSON descriptor fault negative invocation drift")
    nested = {node.name for node in ast.walk(target) if isinstance(node, ast.FunctionDef)}
    if not {"capture_open", "close_then_fail", "fdopen_then_fail"}.issubset(nested):
        raise SystemExit("JSON descriptor fault injection function missing")
    assignments = {(item.attr, node.value.id)
                   for node in ast.walk(target) if isinstance(node, ast.Assign)
                   and isinstance(node.value, ast.Name)
                   for item in node.targets if isinstance(item, ast.Attribute)
                   and isinstance(item.value, ast.Name) and item.value.id == "os"}
    if not {("open", "capture_open"), ("close", "close_then_fail"),
            ("fdopen", "fdopen_then_fail")}.issubset(assignments):
        raise SystemExit("JSON descriptor fault injection not applied")
    strings = {node.value for node in ast.walk(target)
               if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    if not {"close", "fdopen"}.issubset(strings):
        raise SystemExit("JSON descriptor fault matrix missing")


def prove_json_descriptor_fault_negative_removal_rejected() -> None:
    for relative, function_name in (
        ("scripts/validate-memory-os-backup-restore-drill-preflight-negative.py",
         "expect_preflight_json_descriptor_faults"),
        ("scripts/validate-memory-os-backup-restore-non-resurrection-load-negative.py",
         "prove_typed_json_reader_descriptor_faults"),
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        require_json_descriptor_fault_negative_reachable(source, function_name)
        for label, anchor, replacement in (
            ("invocation", f"    {function_name}(validator)\n", "    pass\n"),
            ("close injection", "                    os.close = close_then_fail\n", "                    pass\n"),
            ("fdopen injection", "                    os.fdopen = fdopen_then_fail\n", "                    pass\n"),
        ):
            if source.count(anchor) != 1:
                raise SystemExit("JSON descriptor fault deletion anchor drift: " + label)
            mutated = source.replace(anchor, replacement, 1)
            try:
                require_json_descriptor_fault_negative_reachable(mutated, function_name)
            except SystemExit:
                pass
            else:
                raise SystemExit("JSON descriptor fault negative deletion accepted: " + label)
    print("PASS: preflight and typed JSON descriptor fault invocation/injection deletion rejected")


def require_json_platform_flag_negative_reachable(source: str, function_name: str) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        raise SystemExit("JSON platform flag negative syntax invalid") from None
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    target, main = functions.get(function_name), functions.get("main")
    if target is None or main is None:
        raise SystemExit("JSON platform flag negative missing")
    calls = [node for node in ast.walk(main)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
             and node.func.id == function_name]
    if len(calls) != 1:
        raise SystemExit("JSON platform flag negative invocation drift")
    strings = {node.value for node in ast.walk(target)
               if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    if not {"O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY"}.issubset(strings):
        raise SystemExit("JSON platform flag matrix incomplete")
    mutations = [node for node in ast.walk(target)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                 and node.func.id == "setattr" and len(node.args) == 3
                 and isinstance(node.args[2], ast.Name) and node.args[2].id == "invalid"]
    restorations = [node for node in ast.walk(target)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "setattr" and len(node.args) == 3
                    and isinstance(node.args[2], ast.Name) and node.args[2].id == "original"]
    if len(mutations) != 1 or len(restorations) != 1:
        raise SystemExit("JSON platform flag mutation/restoration missing")
    invalid_values = {node.value for node in ast.walk(target)
                      if isinstance(node, ast.Constant) and node.value in (None, 0)}
    if None not in invalid_values or 0 not in invalid_values:
        raise SystemExit("JSON platform flag None/zero cases missing")


def prove_json_platform_flag_negative_removal_rejected() -> None:
    for relative, function_name in (
        ("scripts/validate-memory-os-backup-restore-drill-preflight-negative.py",
         "expect_preflight_json_platform_flags"),
        ("scripts/validate-memory-os-backup-restore-non-resurrection-load-negative.py",
         "prove_typed_json_reader_platform_flags"),
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        require_json_platform_flag_negative_reachable(source, function_name)
        for label, anchor, replacement in (
            ("invocation", f"    {function_name}(validator)\n", "    pass\n"),
            ("invalid flag injection", "                    setattr(os, flag, invalid)\n", "                    pass\n"),
            ("flag restoration", "                setattr(os, flag, original)\n", "                pass\n"),
        ):
            if source.count(anchor) != 1:
                raise SystemExit("JSON platform flag deletion anchor drift: " + label)
            mutated = source.replace(anchor, replacement, 1)
            try:
                require_json_platform_flag_negative_reachable(mutated, function_name)
            except SystemExit:
                pass
            else:
                raise SystemExit("JSON platform flag negative deletion accepted: " + label)
    print("PASS: preflight and typed JSON platform flag matrix/invocation deletion rejected")


def require_reconcile_reader_race_negative_reachable(source: str, function_name: str) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        raise SystemExit("reconcile reader race negative syntax invalid") from None
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    target, main = functions.get(function_name), functions.get("main")
    if target is None or main is None:
        raise SystemExit("reconcile reader race negative missing")
    calls = [node for node in ast.walk(main)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
             and node.func.id == function_name]
    if len(calls) != 1:
        raise SystemExit("reconcile reader race negative invocation drift")
    nested = {node.name for node in ast.walk(target) if isinstance(node, ast.FunctionDef)}
    if "swap_during_walk" not in nested:
        raise SystemExit("reconcile reader race injection missing")
    assignments = [node for node in ast.walk(target)
                   if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name)
                   and node.value.id == "swap_during_walk"
                   and any(isinstance(item, ast.Attribute) and isinstance(item.value, ast.Name)
                           and item.value.id == "os" and item.attr == "open" for item in node.targets)]
    if len(assignments) != 1:
        raise SystemExit("reconcile reader race injection not applied")
    strings = {node.value for node in ast.walk(target)
               if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    byte_literals = [node.value for node in ast.walk(target)
                     if isinstance(node, ast.Constant) and isinstance(node.value, bytes)]
    if not {"parent", "ancestor"}.issubset(strings) or not any(
        b'"source":"pinned"' in value for value in byte_literals
    ) or not any(b"SYNTHETIC_PRIVATE_CANARY" in value for value in byte_literals):
        raise SystemExit("reconcile reader race positive/canary coverage missing")
    if not any(isinstance(node, ast.Attribute) and node.attr == "MAX_AUTHORITY_BYTES"
               for node in ast.walk(target)):
        raise SystemExit("reconcile reader bounded negative missing")


def prove_reconcile_reader_race_negative_removal_rejected() -> None:
    for relative, function_name, invocation in (
        ("scripts/validate-memory-os-backup-restore-drill-preflight-load-negative.py",
         "prove_preflight_reconcile_pinned_reader",
         "    prove_preflight_reconcile_pinned_reader(reconciler)\n"),
        ("scripts/validate-memory-os-backup-restore-non-resurrection-load-negative.py",
         "prove_typed_reconcile_pinned_reader",
         "    prove_typed_reconcile_pinned_reader()\n"),
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        require_reconcile_reader_race_negative_reachable(source, function_name)
        for label, anchor, replacement in (
            ("invocation", invocation, "    pass\n"),
            ("race injection", "                os.open = swap_during_walk\n", "                pass\n"),
        ):
            if label == "invocation":
                if source.count(anchor) != 1:
                    raise SystemExit("reconcile reader race deletion anchor drift: " + label)
                mutated = source.replace(anchor, replacement, 1)
            else:
                mutated = mutate_named_function(source, function_name, anchor, replacement)
            try:
                require_reconcile_reader_race_negative_reachable(mutated, function_name)
            except SystemExit:
                pass
            else:
                raise SystemExit("reconcile reader race negative deletion accepted: " + label)
    print("PASS: preflight and typed reconcile bounded FD race negative deletion rejected")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_branch_guards_runtime()
    prove_generation_json_negative_removal_rejected()
    prove_generation_json_parent_swap_negative_removal_rejected()
    prove_generation_json_descriptor_fault_negative_deletion_rejected()
    prove_pinned_json_race_negative_removal_rejected()
    prove_json_descriptor_fault_negative_removal_rejected()
    prove_json_platform_flag_negative_removal_rejected()
    prove_reconcile_reader_race_negative_removal_rejected()
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
        ("injected shell", "          python scripts/validate-memory-os-backup-restore-unreadable-authority-workflow-negative.py\n", "          echo UNREVIEWED\n          python scripts/validate-memory-os-backup-restore-unreadable-authority-workflow-negative.py\n"),
        ("injected action", "      - name: Compile unreadable-authority boundaries\n", "      - uses: unreviewed/action@v1\n      - name: Compile unreadable-authority boundaries\n"),
        ("removed PR self-trigger", '      - "scripts/validate-memory-os-backup-restore-unreadable-authority-workflow-negative.py"\n', ""),
    )
    for label, old, replacement in cases:
        if old not in source:
            raise SystemExit(f"unreadable-authority negative anchor missing: {label}")
        mutated = source.replace(old, replacement, 1)
        try:
            validate(mutated)
        except SystemExit:
            continue
        raise SystemExit(f"unreadable-authority negative accepted forbidden mutation: {label}")
    print(f"PASS: unreadable-authority negative workflow source admission ({len(cases)} negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
