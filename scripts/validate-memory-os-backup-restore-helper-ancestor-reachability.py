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
    require(direct_call_count(main, PROOF) == 1, "main missing direct ancestor proof")
    require(
        any(isinstance(node, ast.Constant) and node.value == expected_diagnostic for node in ast.walk(proof)),
        "ancestor proof missing exact diagnostic",
    )
    require(has_call(loaders[0], PIN), "loader missing pinned parent call")
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
        require(total == 4 * len(TARGETS), "ancestor negative count mismatch")
        print(f"Helper ancestor reachability negative PASS ({total} fail-closed mutations)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GuardFailure, SyntaxError, OSError) as exc:
        print(f"HELPER ANCESTOR REACHABILITY FAILED: {exc}")
        raise SystemExit(1)
