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


def validate_workflow_runtime_reachability(workflow_source: str) -> None:
    """Bind the independent workflow to its real validator and runtime proofs."""
    require(not re.search(r"(?m)^\s*(?:if|continue-on-error):", workflow_source),
            "ancestor workflow conditional bypass")
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
    return len(cases)


def main() -> int:
    workflow_source = (
        ROOT / ".github/workflows/backup-restore-helper-ancestor-reachability.yml"
    ).read_text(encoding="utf-8")
    validate_target_matrix(TARGETS, workflow_source)
    validate_workflow_runtime_reachability(workflow_source)
    total = 0
    for filename, diagnostic in TARGETS.items():
        source = (ROOT / "scripts" / filename).read_text(encoding="utf-8")
        validate_source(source, diagnostic)
        if "--negative" in sys.argv[1:]:
            total += negative_cases(source, diagnostic)
    if "--negative" in sys.argv[1:]:
        total += target_matrix_negative_cases(workflow_source)
        total += workflow_runtime_negative_cases(workflow_source)
    print(f"Helper ancestor reachability PASS ({len(TARGETS)} canonical harnesses)")
    if "--negative" in sys.argv[1:]:
        require(total == 46 * len(TARGETS) + 16, "ancestor negative count mismatch")
        print(f"Helper ancestor reachability negative PASS ({total} fail-closed mutations)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GuardFailure, SyntaxError, OSError) as exc:
        print(f"HELPER ANCESTOR REACHABILITY FAILED: {exc}")
        raise SystemExit(1)
