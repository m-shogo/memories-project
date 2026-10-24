#!/usr/bin/env python3
"""Read-only external reachability proof for helper ancestor race negatives."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "validate-memory-os-backup-restore-non-resurrection-load-negative.py":
        "typed contract path fixture guard ancestor identity drift",
    "validate-memory-os-backup-restore-generation-evidence-load-negative.py":
        "generation-evidence fixture guard ancestor identity drift",
    "validate-memory-os-backup-restore-non-resurrection-transport-negative.py":
        "typed contract path fixture guard ancestor identity drift",
    "validate-memory-os-backup-restore-generation-binding-negative.py":
        "generation-binding fixture guard ancestor identity drift",
    "validate-memory-os-backup-restore-drill-request-reconcile-negative.py":
        "drill request fixture guard ancestor identity drift",
    "validate-memory-os-backup-restore-admission-chain-reconcile-negative.py":
        "admission-chain fixture guard ancestor identity drift",
    "validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py":
        "preflight fixture guard ancestor identity drift",
}
PROOF = "prove_helper_ancestor_swap_during_fd_walk_rejected"
PIN = "pin_checked_helper_parent"
MIN_CANONICAL_TARGETS = 7


class GuardFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GuardFailure(message)


def named_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    matches = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    require(len(matches) == 1, f"missing or duplicate function: {name}")
    return matches[0]


def direct_call_count(fn: ast.FunctionDef, name: str) -> int:
    return sum(
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == name
        for node in fn.body
    )


def has_call(fn: ast.FunctionDef, name: str) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == name
        for node in ast.walk(fn)
    )


def has_method(fn: ast.FunctionDef, method: str) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == method
        for node in ast.walk(fn)
    )


def module_effect_nodes(node: ast.AST):
    """Inspect eager module expressions without treating function bodies as eager."""
    yield node
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        expressions = [
            *node.decorator_list,
            *node.args.defaults,
            *(value for value in node.args.kw_defaults if value is not None),
        ]
    elif isinstance(node, ast.Lambda):
        expressions = [
            *node.args.defaults,
            *(value for value in node.args.kw_defaults if value is not None),
            node.body,
        ]
    else:
        expressions = ast.iter_child_nodes(node)
    for child in expressions:
        yield from module_effect_nodes(child)


def is_module_namespace_mutation(node: ast.AST, names: tuple[str, ...]) -> bool:
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in {"exec", "eval"}:
            return True
        if (isinstance(node.func, ast.Name)
                and node.func.id in {"setattr", "delattr"}
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value in names):
            return True
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr in {
                    "update", "pop", "popitem", "clear", "setdefault",
                    "__setitem__", "__delitem__",
                }):
            receiver = node.func.value
            if (isinstance(receiver, ast.Call)
                    and isinstance(receiver.func, ast.Name)
                    and receiver.func.id in {"globals", "locals", "vars"}
                    and not receiver.args and not receiver.keywords):
                return True
            if isinstance(receiver, ast.Attribute) and receiver.attr == "__dict__":
                return True
    if isinstance(node, ast.Subscript) and isinstance(node.ctx, (ast.Store, ast.Del)):
        receiver = node.value
        if (isinstance(receiver, ast.Call)
                and isinstance(receiver.func, ast.Name)
                and receiver.func.id in {"globals", "locals", "vars"}
                and not receiver.args and not receiver.keywords):
            return True
        if isinstance(receiver, ast.Attribute) and receiver.attr == "__dict__":
            return True
    return False


def validate_step_key_inventory(
    source: str, expected: tuple[tuple[str, ...], ...], diagnostic: str
) -> None:
    """Bind executable step headers and step-level keys, including duplicates."""
    headers = re.findall(r"(?m)^      - ([a-z][a-z-]*):", source)
    require(headers == ["uses", "uses", *(["name"] * (len(expected) - 2))],
            diagnostic)
    blocks = re.split(r"(?m)(?=^      - (?:uses|name): )", source)
    step_blocks = [block for block in blocks if block.startswith("      - ")]
    actual = tuple(
        tuple(re.findall(r"(?m)^        ([a-z][a-z-]*):", block))
        for block in step_blocks
    )
    require(actual == expected, diagnostic)


def validate_target_matrix(targets: dict[str, str], workflow_source: str) -> None:
    """Reject silent loss of a canonical harness or its workflow trigger."""
    require(len(targets) >= MIN_CANONICAL_TARGETS,
            "ancestor target matrix below seven canonical harnesses")
    require(
        re.search(r"(?m)^on:\n  push:\n    branches: \[so\]\n", workflow_source)
        is not None,
        "ancestor workflow so push trigger drift",
    )
    for event in ("push", "pull_request"):
        section = re.search(
            r"(?m)^  " + event + r":\n(?P<body>(?:    [^\n]*\n)+)",
            workflow_source,
        )
        require(section is not None,
                "ancestor target matrix workflow trigger drift")
        triggered = set(re.findall(
            r'^      - "scripts/(validate-memory-os-backup-restore-[^"]+-negative\.py)"\s*$',
            section.group("body"),
            flags=re.MULTILINE,
        ))
        require(set(targets) == triggered,
                "ancestor target matrix workflow trigger drift")
        require(section.group("body").count(
            '      - ".github/workflows/autonomous-learning-guard.yml"\n'
        ) == 1, "ancestor independent learning workflow trigger drift")
        all_paths = set(re.findall(r'(?m)^      - "([^"]+)"$', section.group("body")))
        required_authority_paths = {
            ".github/workflows/backup-restore-helper-ancestor-reachability.yml",
            ".github/workflows/autonomous-learning-guard.yml",
            "scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py",
        }
        require(all_paths - {f"scripts/{filename}" for filename in targets}
                == required_authority_paths,
                "ancestor workflow authority trigger drift")
        event_options = re.findall(r"(?m)^    ([a-z][a-z-]*):", section.group("body"))
        require(event_options == (["branches", "paths"] if event == "push" else ["paths"]),
                "ancestor workflow event options drift")


def validate_workflow_runtime_reachability(workflow_source: str) -> None:
    """Bind the independent workflow to its real validator and runtime proofs."""
    require(not re.search(r"(?m)^\s*(?:if|continue-on-error):", workflow_source),
            "ancestor workflow conditional bypass")
    require(not re.search(r"(?m)^(?:env|defaults|strategy):|^    (?:env|defaults|strategy):", workflow_source),
            "ancestor workflow execution context override")
    require(not re.search(r"(?m)^concurrency:", workflow_source),
            "ancestor workflow concurrency drift")
    require(len(re.findall(r"(?m)^on:", workflow_source)) == 1
            and len(re.findall(r"(?m)^permissions:", workflow_source)) == 1,
            "ancestor workflow duplicate root authority")
    event_block = workflow_source.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]
    require(re.findall(r"(?m)^  ([a-z_]+):", event_block)
            == ["push", "pull_request", "workflow_dispatch"],
            "ancestor workflow event inventory drift")
    require(not event_block.split("  workflow_dispatch:\n", 1)[1].strip(),
            "ancestor workflow dispatch options drift")
    static_step = """      - name: Prove seven canonical ancestor negatives remain reachable
        run: |
          set -euo pipefail
          python -m py_compile scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py
          python scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py
          python scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py --negative
"""
    require(workflow_source.count(static_step) == 1,
            "ancestor validator workflow invocation drift")
    step_name = "Prove every canonical helper ancestor race from the validator target set"
    pattern = (
        r"(?m)^      - name: " + re.escape(step_name)
        + r"\n        run: \|\n(?P<body>(?:          [^\n]*\n)+)"
    )
    matches = list(re.finditer(pattern, workflow_source))
    require(len(matches) == 1, "ancestor runtime workflow step missing or duplicate")
    expected_body = """          set -euo pipefail
          python - <<'PY'
          import runpy
          targets = runpy.run_path(
              "scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py"
          )["TARGETS"]
          for filename in targets:
              proof = runpy.run_path(f"scripts/{filename}")
              proof["prove_helper_ancestor_swap_during_fd_walk_rejected"]()
          PY
"""
    require(matches[0].group("body") == expected_body,
            "ancestor runtime workflow proof invocation drift")
    require(
        workflow_source.index(static_step) < matches[0].start()
        < workflow_source.index("      - name: Verify read-only postcondition\n"),
        "ancestor runtime workflow step order drift",
    )

    # An otherwise valid proof can be bypassed by an unreviewed Actions step,
    # altered checkout/setup action, extra job, or elevated workflow token.
    job_sections = workflow_source.split("\n"+"jobs:\n")
    require(len(job_sections) == 2
            and re.findall(r"(?m)^  [A-Za-z][\w-]*:$", job_sections[1]) == ["  verify:"]
            and "\npermissions:\n  contents: read\n\njobs:\n" in workflow_source,
            "ancestor workflow job or permissions drift")
    require(not re.search(r"(?m)^    permissions:", workflow_source),
            "ancestor workflow job-level permissions override")
    require(not re.search(r"(?m)^    (?:container|services|uses|needs|environment|outputs|secrets|concurrency):", workflow_source)
            and "jobs:\n  verify:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n    steps:\n" in workflow_source,
            "ancestor workflow job execution drift")
    require(all(len(re.findall(r"(?m)^    " + key + ":", workflow_source)) == 1
                for key in ("runs-on", "timeout-minutes", "steps")),
            "ancestor workflow duplicate job authority")
    expected_actions = "      - uses: actions/checkout@v4\n        with:\n          ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n          fetch-depth: 0\n          persist-credentials: false\n      - uses: actions/setup-python@v5\n        with:\n          python-version: \"3.12\"\n"
    require(workflow_source.count(expected_actions) == 1,
            "ancestor workflow checkout/setup drift")
    expected_headers = ["      - uses: actions/checkout@v4","      - uses: actions/setup-python@v5","      - name: Confirm exact clean source","      - name: Prove seven canonical ancestor negatives remain reachable","      - name: Prove every canonical helper ancestor race from the validator target set","      - name: Prove preflight reconcile helper races without downstream source-binding dependency","      - name: Verify read-only postcondition"]
    actual_headers = re.findall(r"(?m)^      - (?:uses|name):[^\n]*", workflow_source)
    require(actual_headers == expected_headers,
            "ancestor workflow step allowlist drift")

    # Bind remaining preflight, exact-source and read-only run bodies, not just headers.
    require(workflow_source.count("      - name: Prove preflight reconcile helper races without downstream source-binding dependency\n        run: |\n          set -euo pipefail\n          python - <<'PY'\n          import runpy\n          proof = runpy.run_path(\"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py\")\n          for name in (\n              \"prove_helper_source_symlink_rejected\",\n              \"prove_helper_source_swap_during_import_is_pinned\",\n              \"prove_helper_parent_swap_after_pin_uses_original_source\",\n                        ):\n              proof[name]()\n          PY\n") == 1,
            "ancestor preflight runtime proof drift")
    require(workflow_source.count("      - name: Confirm exact clean source\n        run: |\n          set -euo pipefail\n          expected=\"${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\"\n          test -n \"$expected\"\n          test \"$(git rev-parse HEAD)\" = \"$expected\"\n          test -z \"$(git status --porcelain)\"\n") == 1,
            "ancestor exact-source workflow check drift")
    require(workflow_source.count("      - name: Verify read-only postcondition\n        run: |\n          git diff --check\n          git diff --exit-code\n          test -z \"$(git status --porcelain)\"\n") == 1,
            "ancestor read-only workflow postcondition drift")
    validate_step_key_inventory(
        workflow_source,
        (("with",), ("with",), ("run",), ("run",), ("run",), ("run",), ("run",)),
        "ancestor workflow step authority drift",
    )


def validate_independent_learning_workflow(source: str) -> None:
    """Guard independent learning CI from the ancestor validator."""
    require(not re.search(r"(?m)^\s*(?:if|continue-on-error):", source),
            "independent learning workflow conditional bypass")
    require(not re.search(r"(?m)^(?:env|defaults|strategy):|^    (?:env|defaults|strategy):", source),
            "independent learning workflow execution context override")
    require(len(re.findall(r"(?m)^concurrency:$", source)) == 1
            and source.count("concurrency:\n  group: autonomous-learning-guard-${{ github.sha }}\n  cancel-in-progress: false\n") == 1,
            "independent learning workflow concurrency drift")
    require(len(re.findall(r"(?m)^on:", source)) == 1
            and len(re.findall(r"(?m)^permissions:", source)) == 1,
            "independent learning workflow duplicate root authority")
    require(re.search(r"(?m)^on:\n  push:\n    branches: \[so\]\n    paths:\n", source)
            is not None and "\n  workflow_dispatch:\n" in source,
            "independent learning workflow trigger drift")
    event_block = source.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]
    require(re.findall(r"(?m)^  ([a-z_]+):", event_block)
            == ["push", "workflow_dispatch"],
            "independent learning workflow event inventory drift")
    push_body = event_block.split("  push:\n", 1)[1].split("  workflow_dispatch:\n", 1)[0]
    require(re.findall(r"(?m)^    ([a-z][a-z-]*):", push_body) == ["branches", "paths"],
            "independent learning workflow push options drift")
    require(not event_block.split("  workflow_dispatch:\n", 1)[1].strip(),
            "independent learning workflow dispatch options drift")
    match = re.search(r'(?m)^    paths:\n(?P<paths>(?:      - "[^"]+"\n)+)', source)
    require(match is not None, "independent learning workflow trigger drift")
    paths = set(re.findall(r'^      - "([^"]+)"$', match.group("paths"),
                           flags=re.MULTILINE))
    require({".github/workflows/autonomous-learning-guard.yml", ".github/workflows/backup-restore-helper-ancestor-reachability.yml", "scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py", "contracts/operations/autonomous-learning-system.json", "docs/operations/AUTONOMOUS-OPS-LEARNING.md"} <= paths,
            "independent learning workflow trigger drift")
    triggered_harnesses = {
        item for item in paths
        if item.startswith("scripts/validate-memory-os-backup-restore-")
        and item.endswith("-negative.py")
    }
    expected_harnesses = {f"scripts/{filename}" for filename in TARGETS}
    require(triggered_harnesses == expected_harnesses,
            "independent learning workflow target trigger drift")
    required_authority_paths = {
        ".github/workflows/autonomous-learning-guard.yml",
        ".github/workflows/backup-restore-helper-ancestor-reachability.yml",
        "scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py",
        "contracts/operations/autonomous-learning-system.json",
        "docs/operations/AUTONOMOUS-OPS-LEARNING.md",
        "scripts/validate-autonomous-learning-system.py",
        "scripts/validate-autonomous-learning-system-negative.py",
        "scripts/validate-memory-os-entry-docs.py",
    }
    require(paths - triggered_harnesses == required_authority_paths,
            "independent learning workflow source trigger drift")
    require(source.count("      - name: Validate learning contract and executable negatives\n        shell: bash\n        env:\n          PYTHONDONTWRITEBYTECODE: \"1\"\n        run: |\n          set -euo pipefail\n          python -B scripts/validate-autonomous-learning-system.py\n          python -B scripts/validate-autonomous-learning-system-negative.py\n          python -B scripts/validate-memory-os-entry-docs.py\n") == 1,
            "independent learning workflow learning validation drift")
    require(source.count("      - name: Independently enforce helper ancestor runtime workflow reachability\n        shell: bash\n        env:\n          PYTHONDONTWRITEBYTECODE: \"1\"\n        run: |\n          set -euo pipefail\n          python -B scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py\n          python -B scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py --negative\n") == 1,
            "independent learning workflow ancestor invocation drift")
    require(source.count("      - name: Enforce append-only learning authority against parent\n        shell: bash\n        run: |\n          set -euo pipefail\n          python - <<'PY'\n          from pathlib import Path\n          import subprocess\n\n          authority = \"docs/operations/AUTONOMOUS-OPS-LEARNING.md\"\n          previous = subprocess.check_output(\n              [\"git\", \"show\", f\"HEAD^:{authority}\"]\n          )\n          current = Path(authority).read_bytes()\n          if not current.startswith(previous):\n              raise SystemExit(\n                  \"AUTONOMOUS LEARNING APPEND-ONLY FAILED: previous authority bytes changed\"\n              )\n          print(\"Autonomous learning append-only PASS\")\n          PY\n") == 1,
            "independent learning workflow append-only drift")
    require(source.count("      - uses: actions/checkout@v4\n        with:\n          ref: ${{ github.sha }}\n          persist-credentials: false\n          fetch-depth: 2\n      - uses: actions/setup-python@v5\n        with:\n          python-version: \"3.12\"\n") == 1,
            "independent learning workflow checkout/setup drift")
    require(source.count("      - name: Confirm exact clean source\n        shell: bash\n        run: |\n          set -euo pipefail\n          test \"$(git rev-parse HEAD)\" = \"${{ github.sha }}\"\n          test -z \"$(git status --porcelain)\"\n") == 1,
            "independent learning workflow exact-source drift")
    require(source.count("      - name: Confirm read-only execution\n        shell: bash\n        run: |\n          set -euo pipefail\n          git diff --check\n          git diff --exit-code\n          test -z \"$(git status --porcelain)\"\n") == 1,
            "independent learning workflow read-only drift")
    jobs = source.split("\njobs:\n")
    require(len(jobs) == 2
            and re.findall(r"(?m)^  [A-Za-z][\w-]*:$", jobs[1]) == ["  validate:"]
            and "\npermissions:\n  contents: read\n" in source,
            "independent learning workflow job or permissions drift")
    require(not re.search(r"(?m)^    permissions:", source),
            "independent learning workflow job-level permissions override")
    require(not re.search(r"(?m)^    (?:container|services|uses|needs|environment|outputs|secrets|concurrency):", source)
            and "jobs:\n  validate:\n    runs-on: ubuntu-latest\n    timeout-minutes: 10\n    steps:\n" in source,
            "independent learning workflow job execution drift")
    require(all(len(re.findall(r"(?m)^    " + key + ":", source)) == 1
                for key in ("runs-on", "timeout-minutes", "steps")),
            "independent learning workflow duplicate job authority")
    require(re.findall(r"(?m)^      - (?:uses|name):[^\n]*", source) == [
        "      - uses: actions/checkout@v4",
        "      - uses: actions/setup-python@v5",
        "      - name: Confirm exact clean source",
        "      - name: Enforce append-only learning authority against parent",
        "      - name: Validate learning contract and executable negatives",
        "      - name: Independently enforce helper ancestor runtime workflow reachability",
        "      - name: Confirm read-only execution",
    ], "independent learning workflow step allowlist drift")    validate_step_key_inventory(
        source,
        (("with",), ("with",), ("shell", "run"), ("shell", "run"),
         ("shell", "env", "run"), ("shell", "env", "run"), ("shell", "run")),
        "independent learning workflow step authority drift",
    )


def validate_source(source: str, expected_diagnostic: str) -> None:
    tree = ast.parse(source)
    main = named_function(tree, "main")
    proof = named_function(tree, PROOF)
    pin = named_function(tree, PIN)
    loaders = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"load_pinned_fixture_helper", "load_pinned_fixture_guard"}
    ]
    require(len(loaders) == 1, "missing or duplicate pinned fixture loader")
    # Decorators execute while the module is initialized and may replace the
    # checked callable without a later assignment or explicit namespace write.
    for guarded_function in (main, proof, pin, loaders[0]):
        require(not guarded_function.decorator_list,
                f"decorated guarded function: {guarded_function.name}")
    # A later module-level assignment can replace an otherwise valid checked
    # function before the canonical __main__ dispatcher executes.
    for guarded_name in ("main", PROOF, PIN, loaders[0].name):
        shadowed = any(
            (isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
             and any(
                 isinstance(target, ast.Name) and target.id == guarded_name
                 for target in (
                     node.targets if isinstance(node, ast.Assign) else [node.target]
                 )
             ))
            or (isinstance(node, ast.Delete)
                and any(isinstance(target, ast.Name) and target.id == guarded_name
                        for target in node.targets))
            or (isinstance(node, ast.AsyncFunctionDef) and node.name == guarded_name)
            or (isinstance(node, (ast.Import, ast.ImportFrom))
                and any(
                    (alias.asname or
                     (alias.name.split(".")[0] if isinstance(node, ast.Import)
                      else alias.name)) == guarded_name
                    for alias in node.names
                ))
            for node in tree.body
        )
        require(not shadowed, f"module binding shadowed: {guarded_name}")
    # Module-scope control flow, decorators and default arguments execute before
    # the canonical dispatcher. Direct top-level assignment checks alone miss
    # nested stores, destructuring, and dynamic namespace replacement.
    guarded_names = ("main", PROOF, PIN, loaders[0].name)
    for statement in tree.body:
        for node in module_effect_nodes(statement):
            if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                require(node.id not in guarded_names,
                        f"module binding shadowed: {node.id}")
            if (isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef))
                    and node.name in guarded_names):
                raise GuardFailure(f"module binding shadowed: {node.name}")
            if (isinstance(node, ast.FunctionDef)
                    and node not in tree.body and node.name in guarded_names):
                raise GuardFailure(f"module binding shadowed: {node.name}")
            require(not is_module_namespace_mutation(node, guarded_names),
                    "module dynamic binding mutation")
    require(direct_call_count(main, PROOF) == 1, "main missing direct ancestor proof")
    proof_index = next(
        index for index, statement in enumerate(main.body)
        if isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Call)
        and isinstance(statement.value.func, ast.Name)
        and statement.value.func.id == PROOF
    )
    require(
        not any(
            isinstance(statement, (ast.Return, ast.Raise))
            or (
                isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Call)
                and (
                    (isinstance(statement.value.func, ast.Name)
                     and statement.value.func.id in {"exit", "quit"})
                    or (isinstance(statement.value.func, ast.Attribute)
                        and isinstance(statement.value.func.value, ast.Name)
                        and statement.value.func.value.id == "sys"
                        and statement.value.func.attr == "exit")
                )
            )
            for statement in main.body[:proof_index]
        ),
        "main exits before ancestor proof",
    )
    # The canonical proof call can still be shadowed from inside main()
    # before execution, even if its module-level binding was initially safe.
    for statement in main.body[:proof_index]:
        for node in ast.walk(statement):
            if (isinstance(node, ast.Name)
                    and isinstance(node.ctx, (ast.Store, ast.Del))
                    and node.id in guarded_names):
                raise GuardFailure("main pre-proof binding mutation")
            if is_module_namespace_mutation(node, guarded_names):
                raise GuardFailure("main pre-proof binding mutation")
    dispatches = [
        node for node in tree.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
        and len(node.test.ops) == 1
        and isinstance(node.test.ops[0], ast.Eq)
        and len(node.test.comparators) == 1
        and isinstance(node.test.comparators[0], ast.Constant)
        and node.test.comparators[0].value == "__main__"
    ]
    require(len(dispatches) == 1, "missing canonical __main__ dispatch")
    require(
        any(
            isinstance(statement, ast.Try)
            and any(
                isinstance(inner, ast.Raise)
                and isinstance(inner.exc, ast.Call)
                and isinstance(inner.exc.func, ast.Name)
                and inner.exc.func.id == "SystemExit"
                and len(inner.exc.args) == 1
                and isinstance(inner.exc.args[0], ast.Call)
                and isinstance(inner.exc.args[0].func, ast.Name)
                and inner.exc.args[0].func.id == "main"
                for inner in statement.body
            )
            for statement in dispatches[0].body
        ),
        "canonical __main__ dispatch does not execute main",
    )
    # A syntactically present main() call does not prove fail-closed dispatch
    # when a preceding statement or broad exception handler can swallow it.
    dispatch_body = dispatches[0].body
    require(
        len(dispatch_body) == 1
        and isinstance(dispatch_body[0], ast.Try)
        and len(dispatch_body[0].body) == 1,
        "canonical __main__ dispatch shape drift",
    )
    dispatch_try = dispatch_body[0]
    require(
        len(dispatch_try.handlers) == 1
        and isinstance(dispatch_try.handlers[0].type, ast.Name)
        and dispatch_try.handlers[0].type.id == "Fail"
        and not dispatch_try.orelse
        and not dispatch_try.finalbody
        and bool(dispatch_try.handlers[0].body)
        and isinstance(dispatch_try.handlers[0].body[-1], ast.Raise)
        and isinstance(dispatch_try.handlers[0].body[-1].exc, ast.Call)
        and isinstance(dispatch_try.handlers[0].body[-1].exc.func, ast.Name)
        and dispatch_try.handlers[0].body[-1].exc.func.id == "SystemExit"
        and len(dispatch_try.handlers[0].body[-1].exc.args) == 1
        and isinstance(dispatch_try.handlers[0].body[-1].exc.args[0], ast.Constant)
        and dispatch_try.handlers[0].body[-1].exc.args[0].value == 1,
        "canonical __main__ dispatch handler drift",
    )
    require(
        any(isinstance(node, ast.Constant) and node.value == expected_diagnostic for node in ast.walk(proof)),
        "ancestor proof missing exact diagnostic",
    )
    require(has_call(loaders[0], PIN), "loader missing pinned parent call")
    # A dead pin_checked_helper_parent() call must not authenticate an
    # unchecked full-path open. Bind the live first loader assignment and leaf.
    live_statements = [
        node for node in loaders[0].body
        if not (isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str))
    ]
    first = live_statements[0] if live_statements else None
    require(
        isinstance(first, ast.Assign)
        and len(first.targets) == 1
        and isinstance(first.targets[0], ast.Name)
        and first.targets[0].id == "parent_fd"
        and isinstance(first.value, ast.Call)
        and isinstance(first.value.func, ast.Name)
        and first.value.func.id == PIN
        and len(first.value.args) == 1
        and isinstance(first.value.args[0], ast.Name)
        and first.value.args[0].id == "path",
        "loader parent FD not bound to checked ancestors",
    )
    require(
        len(live_statements) >= 2
        and isinstance(live_statements[1], ast.Try)
        and live_statements[1].body
        and isinstance(live_statements[1].body[0], ast.Try)
        and live_statements[1].body[0].body
        and isinstance(live_statements[1].body[0].body[0], ast.Assign)
        and len(live_statements[1].body[0].body[0].targets) == 1
        and isinstance(live_statements[1].body[0].body[0].targets[0], ast.Name)
        and live_statements[1].body[0].body[0].targets[0].id == "fd"
        and isinstance(live_statements[1].body[0].body[0].value, ast.Call)
        and isinstance(live_statements[1].body[0].body[0].value.func, ast.Attribute)
        and isinstance(live_statements[1].body[0].body[0].value.func.value, ast.Name)
        and live_statements[1].body[0].body[0].value.func.value.id == "os"
        and live_statements[1].body[0].body[0].value.func.attr == "open"
        and live_statements[1].body[0].body[0].value.args
        and isinstance(live_statements[1].body[0].body[0].value.args[0], ast.Attribute)
        and isinstance(live_statements[1].body[0].body[0].value.args[0].value, ast.Name)
        and live_statements[1].body[0].body[0].value.args[0].value.id == "path"
        and live_statements[1].body[0].body[0].value.args[0].attr == "name"
        and any(
            keyword.arg == "dir_fd"
            and isinstance(keyword.value, ast.Name)
            and keyword.value.id == "parent_fd"
            for keyword in live_statements[1].body[0].body[0].value.keywords
        ),
        "loader leaf open not bound to checked parent FD",
    )
    descriptor_open = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "os"
        and node.func.attr == "open"
        and node.args
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "part"
        and any(key.arg == "dir_fd" for key in node.keywords)
        for node in ast.walk(pin)
    )
    require(descriptor_open, "ancestor walk missing descriptor-relative open")
    require(has_method(pin, "fstat") and has_method(pin, "lstat"), "ancestor walk missing identity check")
    require(has_method(pin, "close"), "ancestor walk missing FD cleanup")
    # AST presence of an os.open(part, dir_fd=fd) call is insufficient:
    # a preceding return or a dead branch can leave the walk unreachable.
    pin_body = [
        statement for statement in pin.body
        if not (isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str))
    ]
    require(
        bool(pin_body)
        and not any(isinstance(statement, (ast.Return, ast.Raise))
                    for statement in pin_body[:-1]),
        "ancestor pin exits before checked walk",
    )
    walk_try = pin_body[-1]
    require(
        isinstance(walk_try, ast.Try)
        and len(walk_try.body) >= 2
        and isinstance(walk_try.body[-2], ast.For)
        and isinstance(walk_try.body[-1], ast.Return)
        and isinstance(walk_try.body[-1].value, ast.Name)
        and walk_try.body[-1].value.id == "fd"
        and isinstance(walk_try.body[-2].iter, ast.Attribute)
        and isinstance(walk_try.body[-2].iter.value, ast.Name)
        and walk_try.body[-2].iter.value.id == "relative"
        and walk_try.body[-2].iter.attr == "parts",
        "ancestor pin missing live relative-parts walk",
    )
    require(
        not any(isinstance(statement, (ast.Return, ast.Raise))
                for statement in walk_try.body[:-2]),
        "ancestor pin exits before checked walk",
    )
    walk_loop = walk_try.body[-2]
    require(
        len(walk_loop.body) >= 3
        and isinstance(walk_loop.body[2], ast.Assign)
        and len(walk_loop.body[2].targets) == 1
        and isinstance(walk_loop.body[2].targets[0], ast.Name)
        and walk_loop.body[2].targets[0].id == "next_fd"
        and isinstance(walk_loop.body[2].value, ast.Call)
        and isinstance(walk_loop.body[2].value.func, ast.Attribute)
        and isinstance(walk_loop.body[2].value.func.value, ast.Name)
        and walk_loop.body[2].value.func.value.id == "os"
        and walk_loop.body[2].value.func.attr == "open"
        and walk_loop.body[2].value.args
        and isinstance(walk_loop.body[2].value.args[0], ast.Name)
        and walk_loop.body[2].value.args[0].id == "part"
        and any(keyword.arg == "dir_fd"
                and isinstance(keyword.value, ast.Name)
                and keyword.value.id == "fd"
                for keyword in walk_loop.body[2].value.keywords),
        "ancestor pin descriptor open not live",
    )
    # The checked leaf FD must supply the executed bytes; merely opening a
    # pinned FD before a later pathname read does not prevent import TOCTOU.
    loader_try = live_statements[1]
    read_try = loader_try.body[1] if len(loader_try.body) > 1 else None
    require(
        isinstance(read_try, ast.Try)
        and len(read_try.body) >= 5
        and ast.dump(read_try.body[3], include_attributes=False)
        == ast.dump(ast.parse(
            "with os.fdopen(os.dup(fd), 'rb') as stream:\n"
            "    source = stream.read()\n"
        ).body[0], include_attributes=False)
        and ast.dump(read_try.body[-2], include_attributes=False)
        == ast.dump(ast.parse(
            "exec(compile(source, str(path), 'exec'), module.__dict__)"
        ).body[0], include_attributes=False)
        and isinstance(read_try.body[-1], ast.Return)
        and isinstance(read_try.body[-1].value, ast.Name)
        and read_try.body[-1].value.id == "module",
        "loader source execution not pinned to FD",
    )
    require(
        len(read_try.finalbody) == 1
        and ast.dump(read_try.finalbody[0], include_attributes=False)
        == ast.dump(ast.parse("os.close(fd)").body[0], include_attributes=False)
        and len(loader_try.finalbody) == 1
        and ast.dump(loader_try.finalbody[0], include_attributes=False)
        == ast.dump(ast.parse("os.close(parent_fd)").body[0], include_attributes=False),
        "loader FD cleanup not guaranteed",
    )
    require(
        has_method(proof, "rename") and has_method(proof, "symlink_to"),
        "ancestor proof missing deterministic substitution",
    )


def negative_cases(source: str, diagnostic: str) -> int:
    replacements = (
        ("    prove_helper_ancestor_swap_during_fd_walk_rejected()\n",
         "    pass  # synthetic dropped proof\n", "main missing direct ancestor proof"),
        (f'"{diagnostic}"', '"synthetic wrong ancestor diagnostic"',
         "ancestor proof missing exact diagnostic"),
        ("    parent_fd = pin_checked_helper_parent(path)\n",
         "    parent_fd = -1\n", "loader missing pinned parent call"),
        ("            next_fd = os.open(part, flags, dir_fd=fd)\n",
         "            next_fd = os.open(cursor, flags)\n",
         "ancestor walk missing descriptor-relative open"),
    )
    replacements += (
        ("    prove_helper_ancestor_swap_during_fd_walk_rejected()\n",
         "    return 0  # synthetic early exit\n"
         "    prove_helper_ancestor_swap_during_fd_walk_rejected()\n",
         "main exits before ancestor proof"),
        ("    prove_helper_ancestor_swap_during_fd_walk_rejected()\n",
         "    raise SystemExit(0)  # synthetic early exit\n"
         "    prove_helper_ancestor_swap_during_fd_walk_rejected()\n",
         "main exits before ancestor proof"),
        ('if __name__ == "__main__":',
         'if False:  # synthetic disabled dispatch',
         "missing canonical __main__ dispatch"),
        ("        raise SystemExit(main())\n",
         "        raise SystemExit(0)  # synthetic skipped main\n",
         "canonical __main__ dispatch does not execute main"),
        ("    parent_fd = pin_checked_helper_parent(path)\n",
         "    if False: pin_checked_helper_parent(path)  # dead pin call\n"
         "    parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)\n",
         "loader parent FD not bound to checked ancestors"),
        ("            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)\n",
         "            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)\n",
         "loader leaf open not bound to checked parent FD"),
        ('if __name__ == "__main__":',
         'main = lambda: 0  # synthetic shadowed main\n\nif __name__ == "__main__":',
         "module binding shadowed: main"),
        ('if __name__ == "__main__":',
         'prove_helper_ancestor_swap_during_fd_walk_rejected = lambda: None\n\nif __name__ == "__main__":',
         "module binding shadowed: prove_helper_ancestor_swap_during_fd_walk_rejected"),
        ('if __name__ == "__main__":',
         'pin_checked_helper_parent = lambda path: -1\n\nif __name__ == "__main__":',
         "module binding shadowed: pin_checked_helper_parent"),
    )
    replacements += tuple(
        ('if __name__ == "__main__":',
         injection + '\n\nif __name__ == "__main__":', expected)
        for injection, expected in (
            ("if False: main = lambda: 0  # synthetic nested shadow",
             "module binding shadowed: main"),
            ("main, synthetic_unused = (lambda: 0), None",
             "module binding shadowed: main"),
            ('globals()["main"] = None', "module dynamic binding mutation"),
            ("globals().update(main=None)", "module dynamic binding mutation"),
            ('exec("main = None")', "module dynamic binding mutation"),
            ('setattr(sys.modules[__name__], "main", None)',
             "module dynamic binding mutation"),
            ("class main: pass", "module binding shadowed: main"),
            ('globals().pop("main")', "module dynamic binding mutation"),
        )
    )
    replacements += tuple(
        ("    prove_helper_ancestor_swap_during_fd_walk_rejected()\n",
         "    " + injection + "\n"
         "    prove_helper_ancestor_swap_during_fd_walk_rejected()\n",
         "main pre-proof binding mutation")
        for injection in (
            'globals()["prove_helper_ancestor_swap_during_fd_walk_rejected"] = lambda: None',
            'globals().update(prove_helper_ancestor_swap_during_fd_walk_rejected=lambda: None)',
            'exec("prove_helper_ancestor_swap_during_fd_walk_rejected = lambda: None")',
            'prove_helper_ancestor_swap_during_fd_walk_rejected = lambda: None',
            'setattr(sys.modules[__name__], "prove_helper_ancestor_swap_during_fd_walk_rejected", lambda: None)',
        )
    )
    loader_definition = (
        "def load_pinned_fixture_helper(path: Path, name: str):"
        if "def load_pinned_fixture_helper(path: Path, name: str):" in source
        else "def load_pinned_fixture_guard(path: Path, name: str):"
    )
    replacements += tuple(
        (definition, "@property\n" + definition,
         "decorated guarded function: " + name)
        for definition, name in (
            ("def main() -> int:", "main"),
            ("def prove_helper_ancestor_swap_during_fd_walk_rejected() -> None:", PROOF),
            ("def pin_checked_helper_parent(path: Path) -> int:", PIN),
            (loader_definition, loader_definition.split("(")[0].removeprefix("def ")),
        )
    )
    dispatch_anchor = (
        'if __name__ == "__main__":\n'
        '    try:\n'
        '        raise SystemExit(main())\n'
        '    except Fail as exc:\n'
    )
    replacements += (
        (dispatch_anchor,
         dispatch_anchor.replace('    try:\n', '    pass\n    try:\n'),
         "canonical __main__ dispatch shape drift"),
        (dispatch_anchor,
         dispatch_anchor.replace('    except Fail as exc:\n',
                                 '    except BaseException as exc:\n'),
         "canonical __main__ dispatch handler drift"),
        (dispatch_anchor,
         dispatch_anchor.replace('    except Fail as exc:\n',
                                 '    except BaseException:\n        pass\n    except Fail as exc:\n'),
         "canonical __main__ dispatch handler drift"),
        (dispatch_anchor,
         dispatch_anchor.replace('        raise SystemExit(main())\n',
                                 '        print("synthetic bypass")\n        raise SystemExit(main())\n'),
         "canonical __main__ dispatch shape drift"),
        ("        raise SystemExit(1)\n",
         "        pass  # synthetic swallowed failure\n",
         "canonical __main__ dispatch handler drift"),
    )
    replacements += (
        ('    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY"),\n',
         '    return os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)\n'
         '    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY"),\n',
         "ancestor pin exits before checked walk"),
        ("        for part in relative.parts:\n",
         "        return fd  # synthetic skipped ancestor walk\n"
         "        for part in relative.parts:\n",
         "ancestor pin exits before checked walk"),
        ("        for part in relative.parts:\n",
         "        for part in ():\n",
         "ancestor pin missing live relative-parts walk"),
        ("            next_fd = os.open(part, flags, dir_fd=fd)\n",
         "            if False:\n"
         "                next_fd = os.open(part, flags, dir_fd=fd)\n",
         "ancestor pin descriptor open not live"),
        ("        return fd\n",
         "        return -1  # synthetic unbound return\n",
         "ancestor pin missing live relative-parts walk"),
    )
    replacements += (
        ("                source = stream.read()\n",
         "                source = path.read_bytes()\n",
         "loader source execution not pinned to FD"),
        ('            with os.fdopen(os.dup(fd), "rb") as stream:\n',
         '            with open(path, "rb") as stream:\n',
         "loader source execution not pinned to FD"),
        ('            exec(compile(source, str(path), "exec"), module.__dict__)\n',
         '            exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)\n',
         "loader source execution not pinned to FD"),
        ('            exec(compile(source, str(path), "exec"), module.__dict__)\n',
         '            exec(compile(source, str(path), "exec"), globals())\n',
         "loader source execution not pinned to FD"),
        ("        finally:\n            os.close(fd)\n    finally:\n",
         "        finally:\n            pass  # synthetic leaked leaf FD\n    finally:\n",
         "loader FD cleanup not guaranteed"),
        ("    finally:\n        os.close(parent_fd)\n",
         "    finally:\n        pass  # synthetic leaked parent FD\n",
         "loader FD cleanup not guaranteed"),
    )
    count = 0
    for original, mutation, expected in replacements:
        require(original in source, f"negative mutation anchor absent: {expected}")
        if (expected == "canonical __main__ dispatch handler drift"
                and original == "        raise SystemExit(1)\n"):
            # A harness may contain earlier SystemExit(1) calls; mutate only
            # the final canonical dispatch handler.
            position = source.rfind(original)
            require(position >= 0, "dispatch handler mutation anchor absent")
            mutated = source[:position] + mutation + source[position + len(original):]
        elif expected == "ancestor proof missing exact diagnostic":
            # The loader guard also contains this diagnostic; mutate the proof,
            # not the earlier guard declaration, to test the intended boundary.
            position = source.rfind(original)
            require(position >= 0, "negative diagnostic mutation anchor absent")
            mutated = source[:position] + mutation + source[position + len(original):]
        else:
            mutated = source.replace(original, mutation, 1)
        try:
            validate_source(mutated, diagnostic)
        except GuardFailure as exc:
            require(str(exc) == expected, f"negative rejected at wrong boundary: {exc}")
        else:
            raise GuardFailure(f"negative unexpectedly accepted: {expected}")
        count += 1
    return count


def target_matrix_negative_cases(workflow_source: str) -> int:
    validate_target_matrix(TARGETS, workflow_source)
    first = next(iter(TARGETS))
    dropped = dict(TARGETS)
    dropped.pop(first)
    expanded = dict(TARGETS)
    expanded["synthetic-extra-negative.py"] = "synthetic ancestor identity drift"
    untriggered = workflow_source.replace(
        f'"scripts/{first}"', '"scripts/synthetic-untracked-negative.py"'
    )
    anchor = f'      - "scripts/{first}"'
    require(workflow_source.count(anchor) == 2,
            "ancestor trigger fixture must cover push and pull_request")
    position = workflow_source.rfind(anchor)
    untriggered_pr = (
        workflow_source[:position]
        + '      - "scripts/synthetic-untracked-negative.py"'
        + workflow_source[position + len(anchor):]
    )
    wrong_branch = workflow_source.replace(
        "    branches: [so]\n", "    branches: [main]\n", 1
    )
    learning_anchor = '      - ".github/workflows/autonomous-learning-guard.yml"\n'
    require(workflow_source.count(learning_anchor) == 2,
            "ancestor learning trigger fixture must cover push and pull_request")
    untriggered_learning_push = workflow_source.replace(learning_anchor, "", 1)
    last_learning_trigger = workflow_source.rfind(learning_anchor)
    untriggered_learning_pr = (
        workflow_source[:last_learning_trigger]
        + workflow_source[last_learning_trigger + len(learning_anchor):]
    )
    cases = (
        (dropped, workflow_source,
         "ancestor target matrix below seven canonical harnesses"),
        (expanded, workflow_source,
         "ancestor target matrix workflow trigger drift"),
        (TARGETS, untriggered,
         "ancestor target matrix workflow trigger drift"),
        (TARGETS, untriggered_pr,
         "ancestor target matrix workflow trigger drift"),
        (TARGETS, wrong_branch,
         "ancestor workflow so push trigger drift"),
        (TARGETS, untriggered_learning_push,
         "ancestor independent learning workflow trigger drift"),
        (TARGETS, untriggered_learning_pr,
         "ancestor independent learning workflow trigger drift"),
    )
    authority_path = '      - ".github/workflows/backup-restore-helper-ancestor-reachability.yml"\n'
    validator_path = '      - "scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py"\n'
    require(workflow_source.count(authority_path) == 2 and workflow_source.count(validator_path) == 2,
            "ancestor authority trigger negative anchor missing")
    cases += (
        (TARGETS, workflow_source.replace(authority_path, "", 1),
         "ancestor workflow authority trigger drift"),
        (TARGETS, workflow_source[:workflow_source.rfind(validator_path)]
         + workflow_source[workflow_source.rfind(validator_path) + len(validator_path):],
         "ancestor workflow authority trigger drift"),
        (TARGETS, workflow_source.replace(authority_path,
         authority_path + '      - "scripts/synthetic-unreviewed-trigger.py"\n', 1),
         "ancestor workflow authority trigger drift"),
    )
    cases += (
        (TARGETS, workflow_source.replace("    branches: [so]\n    paths:\n",
         "    branches: [so]\n    types: [created]\n    paths:\n", 1),
         "ancestor workflow event options drift"),
        (TARGETS, workflow_source.replace("  pull_request:\n    paths:\n",
         "  pull_request:\n    types: [opened]\n    paths:\n", 1),
         "ancestor workflow event options drift"),
        (TARGETS, workflow_source.replace("  pull_request:\n    paths:\n",
         "  pull_request:\n    paths: []\n    paths:\n", 1),
         "ancestor workflow event options drift"),
    )
    commented_validator = "    # " + validator_path.strip() + "\n"
    last_validator_position = workflow_source.rfind(validator_path)
    cases += (
        (TARGETS, workflow_source.replace(validator_path, commented_validator, 1),
         "ancestor workflow authority trigger drift"),
        (TARGETS, workflow_source[:last_validator_position] + commented_validator
         + workflow_source[last_validator_position + len(validator_path):],
         "ancestor workflow authority trigger drift"),
    )
    for targets, workflow, expected in cases:
        try:
            validate_target_matrix(targets, workflow)
        except GuardFailure as exc:
            require(str(exc) == expected,
                    f"ancestor matrix rejected at wrong boundary: {exc}")
        else:
            raise GuardFailure(f"ancestor matrix mutation accepted: {expected}")
    return len(cases)


def workflow_runtime_negative_cases(workflow_source: str) -> int:
    """Mutate workflow invocation, not just the Python harness AST."""
    validate_workflow_runtime_reachability(workflow_source)
    pattern = (
        r"(?m)^      - name: Prove every canonical helper ancestor race from the validator target set"
        r"\n        run: \|\n(?:          [^\n]*\n)+"
    )
    match = re.search(pattern, workflow_source)
    require(match is not None, "runtime workflow negative anchor absent")
    step = match.group(0)
    cases = (
        (step, "", "ancestor runtime workflow step missing or duplicate"),
        (step, step + step, "ancestor runtime workflow step missing or duplicate"),
        ("          for filename in targets:\n",
         "          for filename in ():\n",
         "ancestor runtime workflow proof invocation drift"),
        ("          targets = runpy.run_path(\n",
         "          targets = dict(\n",
         "ancestor runtime workflow proof invocation drift"),
        ('              "scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py"\n',
         '              "scripts/synthetic-wrong-targets.py"\n',
         "ancestor runtime workflow proof invocation drift"),
        ('          proof = runpy.run_path(f"scripts/{filename}")\n',
         '          proof = {}\n',
         "ancestor runtime workflow proof invocation drift"),
        ('          proof["prove_helper_ancestor_swap_during_fd_walk_rejected"]()\n',
         '          pass\n',
         "ancestor runtime workflow proof invocation drift"),
        ("          python scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py --negative\n",
         "          python scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py\n",
         "ancestor validator workflow invocation drift"),
        ("      - name: Prove seven canonical ancestor negatives remain reachable\n",
         "      - name: Disabled ancestor negatives\n",
         "ancestor validator workflow invocation drift"),
        ("  verify:\n    runs-on: ubuntu-latest\n",
         "  verify:\n    if: false\n    runs-on: ubuntu-latest\n",
         "ancestor workflow conditional bypass"),
        ("      - name: Verify read-only postcondition\n",
         "      - name: Verify read-only postcondition\n        continue-on-error: true\n",
         "ancestor workflow conditional bypass"),
    )
    cases += (
        ("      - uses: actions/checkout@v4\n",
         "      - uses: actions/upload-artifact@v4\n      - uses: actions/checkout@v4\n",
         "ancestor workflow step allowlist drift"),
        ("      - name: Verify read-only postcondition\n",
         "      - name: Synthetic unreviewed command\n        run: echo bypass\n      - name: Verify read-only postcondition\n",
         "ancestor workflow step allowlist drift"),
        ("      - uses: actions/setup-python@v5\n",
         "      - uses: actions/setup-python@v4\n",
         "ancestor workflow checkout/setup drift"),
        ("          python-version: \"3.12\"\n",
         "          python-version: \"3.11\"\n",
         "ancestor workflow checkout/setup drift"),
        ("          persist-credentials: false\n",
         "          persist-credentials: true\n",
         "ancestor workflow checkout/setup drift"),
        ("          fetch-depth: 0\n",
         "          fetch-depth: 1\n",
         "ancestor workflow checkout/setup drift"),
        ("permissions:\n  contents: read\n",
         "permissions:\n  contents: write\n",
         "ancestor workflow job or permissions drift"),
        ("jobs:\n  verify:\n",
         "jobs:\n  synthetic:\n    runs-on: ubuntu-latest\n    steps: []\n  verify:\n",
         "ancestor workflow job or permissions drift"),
    )
    cases += (
        ("      - name: Prove preflight reconcile helper races without downstream source-binding dependency\n        run: |\n          set -euo pipefail\n          python - <<'PY'\n          import runpy\n          proof = runpy.run_path(\"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py\")\n          for name in (\n              \"prove_helper_source_symlink_rejected\",\n              \"prove_helper_source_swap_during_import_is_pinned\",\n              \"prove_helper_parent_swap_after_pin_uses_original_source\",\n                        ):\n              proof[name]()\n          PY\n",
         "      - name: Prove preflight reconcile helper races without downstream source-binding dependency\n        run: |\n          set -euo pipefail\n          python - <<'PY'\n          import runpy\n          proof = runpy.run_path(\"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py\")\n          for name in (\n              \"synthetic_missing_proof\",\n              \"prove_helper_source_swap_during_import_is_pinned\",\n              \"prove_helper_parent_swap_after_pin_uses_original_source\",\n                        ):\n              proof[name]()\n          PY\n",
         "ancestor preflight runtime proof drift"),
        ("      - name: Prove preflight reconcile helper races without downstream source-binding dependency\n        run: |\n          set -euo pipefail\n          python - <<'PY'\n          import runpy\n          proof = runpy.run_path(\"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py\")\n          for name in (\n              \"prove_helper_source_symlink_rejected\",\n              \"prove_helper_source_swap_during_import_is_pinned\",\n              \"prove_helper_parent_swap_after_pin_uses_original_source\",\n                        ):\n              proof[name]()\n          PY\n",
         "      - name: Prove preflight reconcile helper races without downstream source-binding dependency\n        run: |\n          set -euo pipefail\n          python - <<'PY'\n          import runpy\n          proof = runpy.run_path(\"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py\")\n          for name in (\n              \"prove_helper_source_symlink_rejected\",\n              \"prove_helper_source_swap_during_import_is_pinned\",\n              \"prove_helper_parent_swap_after_pin_uses_original_source\",\n                        ):\n              pass  # synthetic skipped proof\n          PY\n",
         "ancestor preflight runtime proof drift"),
        ("      - name: Prove preflight reconcile helper races without downstream source-binding dependency\n        run: |\n          set -euo pipefail\n          python - <<'PY'\n          import runpy\n          proof = runpy.run_path(\"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py\")\n          for name in (\n              \"prove_helper_source_symlink_rejected\",\n              \"prove_helper_source_swap_during_import_is_pinned\",\n              \"prove_helper_parent_swap_after_pin_uses_original_source\",\n                        ):\n              proof[name]()\n          PY\n",
         "      - name: Prove preflight reconcile helper races without downstream source-binding dependency\n        run: |\n          set -euo pipefail\n          python - <<'PY'\n          import runpy\n          proof = runpy.run_path(\"scripts/synthetic.py\")\n          for name in (\n              \"prove_helper_source_symlink_rejected\",\n              \"prove_helper_source_swap_during_import_is_pinned\",\n              \"prove_helper_parent_swap_after_pin_uses_original_source\",\n                        ):\n              proof[name]()\n          PY\n",
         "ancestor preflight runtime proof drift"),
        ("      - name: Prove preflight reconcile helper races without downstream source-binding dependency\n        run: |\n          set -euo pipefail\n          python - <<'PY'\n          import runpy\n          proof = runpy.run_path(\"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py\")\n          for name in (\n              \"prove_helper_source_symlink_rejected\",\n              \"prove_helper_source_swap_during_import_is_pinned\",\n              \"prove_helper_parent_swap_after_pin_uses_original_source\",\n                        ):\n              proof[name]()\n          PY\n",
         "      - name: Prove preflight reconcile helper races without downstream source-binding dependency\n        run: |\n          set -euo pipefail\n          python - <<'PY'\n          import runpy\n          proof = runpy.run_path(\"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py\")\n          for name in (\n              \"prove_helper_source_symlink_rejected\",\n              \"prove_helper_source_swap_during_import_is_pinned\",\n              \"synthetic_wrong_parent_proof\",\n                        ):\n              proof[name]()\n          PY\n",
         "ancestor preflight runtime proof drift"),
        ("      - name: Confirm exact clean source\n        run: |\n          set -euo pipefail\n          expected=\"${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\"\n          test -n \"$expected\"\n          test \"$(git rev-parse HEAD)\" = \"$expected\"\n          test -z \"$(git status --porcelain)\"\n",
         "      - name: Confirm exact clean source\n        run: |\n          set -euo pipefail\n          expected=\"${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\"\n          test -n \"$expected\"\n          echo synthetic-source-bypass\n          test -z \"$(git status --porcelain)\"\n",
         "ancestor exact-source workflow check drift"),
        ("      - name: Confirm exact clean source\n        run: |\n          set -euo pipefail\n          expected=\"${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\"\n          test -n \"$expected\"\n          test \"$(git rev-parse HEAD)\" = \"$expected\"\n          test -z \"$(git status --porcelain)\"\n",
         "      - name: Confirm exact clean source\n        run: |\n          set -euo pipefail\n          expected=\"${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\"\n          test -n \"$expected\"\n          test \"$(git rev-parse HEAD)\" = \"$expected\"\n          echo synthetic-clean-bypass\n",
         "ancestor exact-source workflow check drift"),
        ("      - name: Verify read-only postcondition\n        run: |\n          git diff --check\n          git diff --exit-code\n          test -z \"$(git status --porcelain)\"\n",
         "      - name: Verify read-only postcondition\n        run: |\n          git diff --check\n          echo synthetic-readonly-bypass\n          test -z \"$(git status --porcelain)\"\n",
         "ancestor read-only workflow postcondition drift"),
        ("  verify:\n    runs-on: ubuntu-latest\n", "  verify:\n    permissions:\n      contents: write\n    runs-on: ubuntu-latest\n", "ancestor workflow job-level permissions override"),
    )
    cases += (
        ("permissions:\n", "env:\n  BASH_ENV: /tmp/synthetic-env\npermissions:\n", "ancestor workflow execution context override"),
        ("permissions:\n", "defaults:\n  run:\n    shell: sh\npermissions:\n", "ancestor workflow execution context override"),
        ("permissions:\n", "strategy:\n  fail-fast: false\npermissions:\n", "ancestor workflow execution context override"),
        ("  verify:\n    runs-on: ubuntu-latest\n", "  verify:\n    env:\n      BASH_ENV: /tmp/synthetic-env\n    runs-on: ubuntu-latest\n", "ancestor workflow execution context override"),
        ("  verify:\n    runs-on: ubuntu-latest\n", "  verify:\n    defaults:\n      run:\n        shell: sh\n    runs-on: ubuntu-latest\n", "ancestor workflow execution context override"),
        ("  verify:\n    runs-on: ubuntu-latest\n", "  verify:\n    strategy:\n      fail-fast: false\n    runs-on: ubuntu-latest\n", "ancestor workflow execution context override"),
    )
    cases += (
        ("  verify:\n    runs-on: ubuntu-latest\n", "  verify:\n    runs-on: self-hosted\n", "ancestor workflow job execution drift"),
        ("    timeout-minutes: 5\n", "    timeout-minutes: 120\n", "ancestor workflow job execution drift"),
        ("    timeout-minutes: 5\n    steps:\n", "    timeout-minutes: 5\n    container: synthetic/unreviewed:latest\n    steps:\n", "ancestor workflow job execution drift"),
        ("    timeout-minutes: 5\n    steps:\n", "    timeout-minutes: 5\n    services:\n      synthetic:\n        image: synthetic/unreviewed:latest\n    steps:\n", "ancestor workflow job execution drift"),
        ("    timeout-minutes: 5\n    steps:\n", "    timeout-minutes: 5\n    environment: production\n    steps:\n", "ancestor workflow job execution drift"),
    )
    cases += (
        ("permissions:\n", "concurrency:\n  group: synthetic-unreviewed\n  cancel-in-progress: true\npermissions:\n", "ancestor workflow concurrency drift"),
        ("    timeout-minutes: 5\n    steps:\n", "    timeout-minutes: 5\n    concurrency:\n      group: synthetic-unreviewed\n    steps:\n", "ancestor workflow job execution drift"),
    )
    cases += (
        ("  workflow_dispatch:\n", "  pull_request_target:\n  workflow_dispatch:\n", "ancestor workflow event inventory drift"),
        ("  workflow_dispatch:\n", "  schedule:\n    - cron: '0 * * * *'\n  workflow_dispatch:\n", "ancestor workflow event inventory drift"),
    )
    cases += (
        ("  workflow_dispatch:\n", "  workflow_dispatch:\n    inputs:\n      synthetic:\n        type: boolean\n", "ancestor workflow dispatch options drift"),
    )
    cases += (
        ("      - name: Verify read-only postcondition\n",
         "        env:\n          BASH_ENV: /tmp/synthetic\n      - name: Verify read-only postcondition\n",
         "ancestor workflow step authority drift"),
        ("      - name: Verify read-only postcondition\n",
         "        working-directory: /tmp\n      - name: Verify read-only postcondition\n",
         "ancestor workflow step authority drift"),
        ("      - name: Verify read-only postcondition\n",
         "        timeout-minutes: 99\n      - name: Verify read-only postcondition\n",
         "ancestor workflow step authority drift"),
        ("      - name: Verify read-only postcondition\n",
         "        run: echo synthetic-override\n      - name: Verify read-only postcondition\n",
         "ancestor workflow step authority drift"),
    )
    for original, replacement, expected in cases:
        require(workflow_source.count(original) == 1,
                f"workflow negative anchor not unique: {expected}")
        mutated = workflow_source.replace(original, replacement, 1)
        try:
            validate_workflow_runtime_reachability(mutated)
        except GuardFailure as exc:
            require(str(exc) == expected,
                    f"workflow negative rejected at wrong boundary: {exc}")
        else:
            raise GuardFailure(f"workflow runtime negative accepted: {expected}")
    duplicate_root_cases = (
        (workflow_source + "\npermissions:\n  contents: write\n",
         "ancestor workflow duplicate root authority"),
        (workflow_source + "\non:\n  workflow_dispatch:\n",
         "ancestor workflow duplicate root authority"),
    )
    for mutated, expected in duplicate_root_cases:
        try:
            validate_workflow_runtime_reachability(mutated)
        except GuardFailure as exc:
            require(str(exc) == expected,
                    f"ancestor duplicate-root mutation rejected at wrong boundary: {exc}")
        else:
            raise GuardFailure(f"ancestor duplicate-root mutation accepted: {expected}")
    duplicate_job_cases = (
        (workflow_source + "\n    runs-on: self-hosted\n", "ancestor workflow duplicate job authority"),
        (workflow_source + "\n    timeout-minutes: 120\n", "ancestor workflow duplicate job authority"),
        (workflow_source + "\n    steps: []\n", "ancestor workflow duplicate job authority"),
    )
    for mutated, expected in duplicate_job_cases:
        try:
            validate_workflow_runtime_reachability(mutated)
        except GuardFailure as exc:
            require(str(exc) == expected,
                    f"duplicate-job mutation rejected at wrong boundary: {exc}")
        else:
            raise GuardFailure(f"duplicate-job mutation accepted: {expected}")
    return len(cases) + len(duplicate_root_cases) + len(duplicate_job_cases)



def independent_learning_workflow_negative_cases(source: str) -> int:
    validate_independent_learning_workflow(source)
    cases = (
        ("      - \".github/workflows/backup-restore-helper-ancestor-reachability.yml\"\n", "", "independent learning workflow trigger drift"),
        ("    branches: [so]\n", "    branches: [main]\n", "independent learning workflow trigger drift"),
        ("  workflow_dispatch:\n", "  disabled_dispatch:\n", "independent learning workflow trigger drift"),
        ("          python -B scripts/validate-autonomous-learning-system-negative.py\n", "          echo bypass\n", "independent learning workflow learning validation drift"),
        ("          python -B scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py --negative\n", "          echo bypass\n", "independent learning workflow ancestor invocation drift"),
        ("          if not current.startswith(previous):\n", "          if False:\n", "independent learning workflow append-only drift"),
        ("  validate:\n    runs-on: ubuntu-latest\n", "  validate:\n    if: false\n    runs-on: ubuntu-latest\n", "independent learning workflow conditional bypass"),
        ("      - name: Confirm read-only execution\n", "      - name: Confirm read-only execution\n        continue-on-error: true\n", "independent learning workflow conditional bypass"),
        ("          persist-credentials: false\n", "          persist-credentials: true\n", "independent learning workflow checkout/setup drift"),
        ("permissions:\n  contents: read\n", "permissions:\n  contents: write\n", "independent learning workflow job or permissions drift"),
        ("jobs:\n  validate:\n", "jobs:\n  extra:\n    runs-on: ubuntu-latest\n    steps: []\n  validate:\n", "independent learning workflow job or permissions drift"),
        ("      - name: Confirm read-only execution\n", "      - name: Extra command\n        run: echo bypass\n      - name: Confirm read-only execution\n", "independent learning workflow step allowlist drift"),
        ("          test \"$(git rev-parse HEAD)\" = \"${{ github.sha }}\"\n", "          echo bypass\n", "independent learning workflow exact-source drift"),
        ("          git diff --exit-code\n", "          echo bypass\n", "independent learning workflow read-only drift"),
        ("      - \"scripts/validate-memory-os-backup-restore-non-resurrection-load-negative.py\"\n", "", "independent learning workflow target trigger drift"),
        ("      - \"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py\"\n", "", "independent learning workflow target trigger drift"),
        ("      - \"scripts/validate-memory-os-backup-restore-non-resurrection-load-negative.py\"\n", "      - \"scripts/validate-memory-os-backup-restore-non-resurrection-load-negative.py\"\n      - \"scripts/validate-memory-os-backup-restore-synthetic-negative.py\"\n", "independent learning workflow target trigger drift"),
        ("  validate:\n    runs-on: ubuntu-latest\n", "  validate:\n    permissions:\n      contents: write\n    runs-on: ubuntu-latest\n", "independent learning workflow job-level permissions override"),
    )
    cases += (
        ("permissions:\n", "env:\n  BASH_ENV: /tmp/synthetic-env\npermissions:\n", "independent learning workflow execution context override"),
        ("permissions:\n", "defaults:\n  run:\n    shell: sh\npermissions:\n", "independent learning workflow execution context override"),
        ("permissions:\n", "strategy:\n  fail-fast: false\npermissions:\n", "independent learning workflow execution context override"),
        ("  validate:\n    runs-on: ubuntu-latest\n", "  validate:\n    env:\n      BASH_ENV: /tmp/synthetic-env\n    runs-on: ubuntu-latest\n", "independent learning workflow execution context override"),
        ("  validate:\n    runs-on: ubuntu-latest\n", "  validate:\n    defaults:\n      run:\n        shell: sh\n    runs-on: ubuntu-latest\n", "independent learning workflow execution context override"),
        ("  validate:\n    runs-on: ubuntu-latest\n", "  validate:\n    strategy:\n      fail-fast: false\n    runs-on: ubuntu-latest\n", "independent learning workflow execution context override"),
    )
    cases += (
        ("  validate:\n    runs-on: ubuntu-latest\n", "  validate:\n    runs-on: self-hosted\n", "independent learning workflow job execution drift"),
        ("    timeout-minutes: 10\n", "    timeout-minutes: 120\n", "independent learning workflow job execution drift"),
        ("    timeout-minutes: 10\n    steps:\n", "    timeout-minutes: 10\n    container: synthetic/unreviewed:latest\n    steps:\n", "independent learning workflow job execution drift"),
        ("    timeout-minutes: 10\n    steps:\n", "    timeout-minutes: 10\n    services:\n      synthetic:\n        image: synthetic/unreviewed:latest\n    steps:\n", "independent learning workflow job execution drift"),
        ("    timeout-minutes: 10\n    steps:\n", "    timeout-minutes: 10\n    environment: production\n    steps:\n", "independent learning workflow job execution drift"),
    )
    cases += (
        ("  cancel-in-progress: false\n", "  cancel-in-progress: true\n", "independent learning workflow concurrency drift"),
        ("  group: autonomous-learning-guard-${{ github.sha }}\n", "  group: synthetic-unreviewed\n", "independent learning workflow concurrency drift"),
        ("    timeout-minutes: 10\n    steps:\n", "    timeout-minutes: 10\n    concurrency:\n      group: synthetic-unreviewed\n    steps:\n", "independent learning workflow job execution drift"),
    )
    cases += (
        ('      - "scripts/validate-autonomous-learning-system.py"\n', "", "independent learning workflow source trigger drift"),
        ('      - "scripts/validate-autonomous-learning-system-negative.py"\n', "", "independent learning workflow source trigger drift"),
        ('      - "scripts/validate-memory-os-entry-docs.py"\n', "", "independent learning workflow source trigger drift"),
    )
    cases += (
        ("  workflow_dispatch:\n", "  pull_request_target:\n  workflow_dispatch:\n", "independent learning workflow event inventory drift"),
        ("  workflow_dispatch:\n", "  schedule:\n    - cron: '0 * * * *'\n  workflow_dispatch:\n", "independent learning workflow event inventory drift"),
    )
    cases += (
        ("  workflow_dispatch:\n", "    tags: [synthetic]\n  workflow_dispatch:\n", "independent learning workflow push options drift"),
        ("  workflow_dispatch:\n", "    paths: []\n  workflow_dispatch:\n", "independent learning workflow push options drift"),
        ("  workflow_dispatch:\n", "  workflow_dispatch:\n    inputs:\n      synthetic:\n        type: boolean\n", "independent learning workflow dispatch options drift"),
    )
    cases += (
        ("      - name: Confirm read-only execution\n",
         "        env:\n          BASH_ENV: /tmp/synthetic\n      - name: Confirm read-only execution\n",
         "independent learning workflow step authority drift"),
        ("      - name: Confirm read-only execution\n",
         "        working-directory: /tmp\n      - name: Confirm read-only execution\n",
         "independent learning workflow step authority drift"),
        ("      - name: Confirm read-only execution\n",
         "        timeout-minutes: 99\n      - name: Confirm read-only execution\n",
         "independent learning workflow step authority drift"),
        ("      - name: Confirm read-only execution\n",
         "        run: echo synthetic-override\n      - name: Confirm read-only execution\n",
         "independent learning workflow step authority drift"),
    )
    for original, replacement, expected in cases:
        require(source.count(original) == 1,
                f"independent workflow negative anchor not unique: {expected}")
        mutated = source.replace(original, replacement, 1)
        try:
            validate_independent_learning_workflow(mutated)
        except GuardFailure as exc:
            require(str(exc) == expected,
                    f"independent workflow negative rejected at wrong boundary: {exc}")
        else:
            raise GuardFailure(f"independent workflow negative accepted: {expected}")
    duplicate_root_cases = (
        (source + "\npermissions:\n  contents: write\n",
         "independent learning workflow duplicate root authority"),
        (source + "\non:\n  workflow_dispatch:\n",
         "independent learning workflow duplicate root authority"),
    )
    for mutated, expected in duplicate_root_cases:
        try:
            validate_independent_learning_workflow(mutated)
        except GuardFailure as exc:
            require(str(exc) == expected,
                    f"independent duplicate-root mutation rejected at wrong boundary: {exc}")
        else:
            raise GuardFailure(f"independent duplicate-root mutation accepted: {expected}")
    duplicate_job_cases = (
        (source + "\n    runs-on: self-hosted\n", "independent learning workflow duplicate job authority"),
        (source + "\n    timeout-minutes: 120\n", "independent learning workflow duplicate job authority"),
        (source + "\n    steps: []\n", "independent learning workflow duplicate job authority"),
    )
    for mutated, expected in duplicate_job_cases:
        try:
            validate_independent_learning_workflow(mutated)
        except GuardFailure as exc:
            require(str(exc) == expected,
                    f"duplicate-job mutation rejected at wrong boundary: {exc}")
        else:
            raise GuardFailure(f"duplicate-job mutation accepted: {expected}")
    return len(cases) + len(duplicate_root_cases) + len(duplicate_job_cases)


def main() -> int:
    workflow_source = (
        ROOT / ".github/workflows/backup-restore-helper-ancestor-reachability.yml"
    ).read_text(encoding="utf-8")
    validate_target_matrix(TARGETS, workflow_source)
    validate_workflow_runtime_reachability(workflow_source)
    learning_workflow_source = (
        ROOT / ".github/workflows/autonomous-learning-guard.yml"
    ).read_text(encoding="utf-8")
    validate_independent_learning_workflow(learning_workflow_source)
    total = 0
    for filename, diagnostic in TARGETS.items():
        source = (ROOT / "scripts" / filename).read_text(encoding="utf-8")
        validate_source(source, diagnostic)
        if "--negative" in sys.argv[1:]:
            total += negative_cases(source, diagnostic)
    if "--negative" in sys.argv[1:]:
        total += target_matrix_negative_cases(workflow_source)
        total += workflow_runtime_negative_cases(workflow_source)
        total += independent_learning_workflow_negative_cases(learning_workflow_source)
    print(f"Helper ancestor reachability PASS ({len(TARGETS)} canonical harnesses)")
    if "--negative" in sys.argv[1:]:
        require(total == 46 * len(TARGETS) + 116, "ancestor negative count mismatch")
        print(f"Helper ancestor reachability negative PASS ({total} fail-closed mutations)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GuardFailure, SyntaxError, OSError) as exc:
        print(f"HELPER ANCESTOR REACHABILITY FAILED: {exc}")
        raise SystemExit(1)
