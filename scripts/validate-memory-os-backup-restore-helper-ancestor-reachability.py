#!/usr/bin/env python3
"""Read-only external reachability proof for helper ancestor race negatives."""

from __future__ import annotations

import ast
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
    count = 0
    for original, mutation, expected in replacements:
        require(original in source, f"negative mutation anchor absent: {expected}")
        if expected == "ancestor proof missing exact diagnostic":
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


def main() -> int:
    total = 0
    for filename, diagnostic in TARGETS.items():
        source = (ROOT / "scripts" / filename).read_text(encoding="utf-8")
        validate_source(source, diagnostic)
        if "--negative" in sys.argv[1:]:
            total += negative_cases(source, diagnostic)
    print(f"Helper ancestor reachability PASS ({len(TARGETS)} canonical harnesses)")
    if "--negative" in sys.argv[1:]:
        require(total == 13 * len(TARGETS), "ancestor negative count mismatch")
        print(f"Helper ancestor reachability negative PASS ({total} fail-closed mutations)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GuardFailure, SyntaxError, OSError) as exc:
        print(f"HELPER ANCESTOR REACHABILITY FAILED: {exc}")
        raise SystemExit(1)
