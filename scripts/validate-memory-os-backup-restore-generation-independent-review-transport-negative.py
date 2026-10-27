#!/usr/bin/env python3
"""Focused negative for independent-review execution transport authority."""

from __future__ import annotations

import ast
import importlib.util
import tempfile
from pathlib import Path
from typing import Any, Callable

from ops_independent_review_fixture_loader import FixtureImportFail, load_pinned_module, read_pinned_source

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-generation-independent-review.py")
VALIDATOR = ROOT / VALIDATOR_REL


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator() -> Any:
    """Delegate canonical path admission to the pinned loader, never a mutable precheck."""
    try:
        require(VALIDATOR == ROOT / VALIDATOR_REL,
                "canonical independent-review validator lexical path drift")
        return load_pinned_module(ROOT, VALIDATOR, "memory_os_generation_independent_review_transport_negative")
    except (Exception, SystemExit):
        raise Fail("canonical independent-review validator path rejected") from None


def prove_validator_path_failures() -> None:
    """Prove fixed private errors for missing/symlinked paths and loader faults."""
    global ROOT, VALIDATOR, load_pinned_module
    original_root = ROOT
    original_validator = VALIDATOR
    original_loader = load_pinned_module

    def rejected(label: str) -> None:
        try:
            load_validator()
        except Fail as exc:
            require(str(exc) == "canonical independent-review validator path rejected"
                    and exc.__suppress_context__ and exc.__cause__ is None,
                    "independent transport private validator diagnostic drift: " + label)
        else:
            raise Fail("independent transport accepted unsafe validator path: " + label)

    try:
        with tempfile.TemporaryDirectory(prefix=".independent-transport-path-", dir=original_root) as raw:
            ROOT = Path(raw)
            canonical = ROOT / VALIDATOR_REL
            canonical.parent.mkdir(parents=True)
            VALIDATOR = canonical
            rejected("canonical missing")
            canonical.symlink_to(original_validator)
            rejected("canonical symlink")
            canonical.unlink()
            canonical.write_text("VALUE = 7\n", encoding="utf-8")
            require(load_validator().VALUE == 7,
                    "independent transport isolated canonical positive drift")
            substitute = ROOT / "scripts/substitute.py"
            substitute.write_text("VALUE = 9\n", encoding="utf-8")
            VALIDATOR = substitute
            rejected("noncanonical substitute")
        ROOT = original_root
        VALIDATOR = original_validator
        for error in (OSError("PRIVATE_TRANSPORT_OS_CANARY"),
                      RuntimeError("PRIVATE_TRANSPORT_RUNTIME_CANARY"),
                      SystemExit("PRIVATE_TRANSPORT_EXIT_CANARY")):
            def fail_loader(*_args, **_kwargs):
                raise error
            load_pinned_module = fail_loader
            try:
                rejected(type(error).__name__)
            finally:
                load_pinned_module = original_loader
        require(callable(load_validator().candidate_reviews_approved),
                "independent transport canonical validator restoration drift")
    finally:
        ROOT = original_root
        VALIDATOR = original_validator
        load_pinned_module = original_loader
    print("PASS independent transport canonical validator path privacy: isolated missing symlink positive substitute OSError RuntimeError SystemExit")


SOURCE_ORDER_EXECUTION_NEGATIVE = (
    ROOT / "scripts/validate-memory-os-backup-restore-generation-independent-review-execution-negative.py"
)


def require_source_order_pinned_import(source: str) -> None:
    tree = ast.parse(source)
    functions = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name == "prove_source_order_json_reader"]
    require(len(functions) == 1, "source-order negative import function drift")
    fn = functions[0]
    pinned = [node for node in ast.walk(fn)
              if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id == "load_checked_module"]
    unsafe = [node for node in ast.walk(fn)
              if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
              and node.func.attr == "spec_from_file_location"]
    require(len(pinned) == 1 and not unsafe, "source-order negative import must be descriptor-pinned")


def prove_source_order_import_guard() -> None:
    try:
        raw = read_pinned_source(ROOT, SOURCE_ORDER_EXECUTION_NEGATIVE)
        source = raw.decode("utf-8")
    except (FixtureImportFail, UnicodeDecodeError):
        raise Fail("source-order negative source rejected") from None
    require_source_order_pinned_import(source)
    old = 'module = load_checked_module(path_to_validator, "memory_os_source_order_json_negative")'
    require(source.count(old) == 1, "source-order pinned negative mutation anchor drift")
    for label, replacement in (
        ("delete import", "module = None"),
        ("restore unsafe default loader", 'module = importlib.util.spec_from_file_location("unsafe", path_to_validator)'),
    ):
        mutant = source.replace(old, replacement, 1)
        try:
            require_source_order_pinned_import(mutant)
        except Fail:
            continue
        raise Fail("source-order pinned import weakening accepted: " + label)
    print("PASS: independent source-order negative importer rejects 2 source mutations")


WORKFLOW_SOURCE_GUARD = (
    ROOT / "scripts/validate-memory-os-backup-restore-generation-independent-review-workflow-negative.py"
)


def require_workflow_guard_pinning(code: str) -> None:
    """Independently bind the bootstrap reader, its real fault probes and reachability."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        raise Fail("independent workflow guard source syntax drift") from None
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    required = {
        "read_bounded_regular": (
            "checked = path.lstat()",
            'for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY")',
            "directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK",
            "for component in path.parts[1:-1]:",
            "parent_fd = os.open(component, directory_flags, dir_fd=parent_fd)",
            "fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,",
            "opened = os.fstat(fd)",
            "stream.read(limit + 1)",
            "for directory_fd in reversed(directory_fds):",
            "if cleanup_failed:",
            "raise SystemExit(PRIVATE_SOURCE_ERROR) from None",
        ),
        "prove_bounded_reader": (
            "rejected(fifo)",
            "for unsupported in (None, 0):",
            "if not swapped and target == parent.name",
            "if not swapped_after_pin and target == pinned.name",
            "parent.rename(parked)",
            "parent.symlink_to(external",
            "canary.read_bytes()",
            'len(os.listdir("/proc/self/fd"))',
            "os.open = original_open",
        ),
        "main": ("prove_bounded_reader()",),
    }
    for name, tokens in required.items():
        node = functions.get(name)
        require(node is not None, "independent workflow source guard function missing: " + name)
        fragment = ast.get_source_segment(code, node) or ""
        for token in tokens:
            require(token in fragment, "independent workflow source guard weakened: " + name)
    reader = functions["read_bounded_regular"]
    pinned_opens = [
        node for node in ast.walk(reader)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "os"
        and node.func.attr == "open"
        and any(keyword.arg == "dir_fd" for keyword in node.keywords)
    ]
    require(len(pinned_opens) == 2, "independent workflow guard must pin ancestor and leaf")


def prove_workflow_guard_mutations_rejected() -> None:
    try:
        code = read_pinned_source(ROOT, WORKFLOW_SOURCE_GUARD).decode("utf-8")
    except (FixtureImportFail, UnicodeDecodeError):
        raise Fail("independent workflow source guard unreadable") from None
    require_workflow_guard_pinning(code)
    mutations = (
        ("read_bounded_regular", "for component in path.parts[1:-1]:", "for component in ():"),
        ("read_bounded_regular", "parent_fd = os.open(component, directory_flags, dir_fd=parent_fd)",
         "parent_fd = os.open(component, directory_flags)"),
        ("read_bounded_regular", "for directory_fd in reversed(directory_fds):",
         "for directory_fd in ():"),
        ("read_bounded_regular", "stream.read(limit + 1)", "stream.read()"),
        ("read_bounded_regular", "if cleanup_failed:", "if False:"),
        ("prove_bounded_reader", "if not swapped_after_pin and target == pinned.name",
         "if False and target == pinned.name"),
        ("prove_bounded_reader", "for unsupported in (None, 0):", "for unsupported in ():"),
        ("main", "prove_bounded_reader()", "pass"),
    )
    for name, old, new in mutations:
        tree = ast.parse(code)
        nodes = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name == name]
        require(len(nodes) == 1, "independent workflow guard mutation function drift")
        node = nodes[0]
        lines = code.splitlines(keepends=True)
        fragment = "".join(lines[node.lineno - 1:node.end_lineno])
        require(fragment.count(old) == 1, "independent workflow guard mutation anchor drift")
        mutant = "".join(lines[:node.lineno - 1]) + fragment.replace(old, new, 1) + "".join(lines[node.end_lineno:])
        try:
            require_workflow_guard_pinning(mutant)
        except Fail:
            continue
        raise Fail("independent workflow guard mutation accepted: " + name)
    print("PASS independent workflow bootstrap ancestor pin and 8 deletion mutations")


def read_authority(path: Path) -> bytes:
    """Bound and pin canonical authority bytes before and after transport fault probes."""
    try:
        return read_pinned_source(ROOT, path)
    except FixtureImportFail:
        raise Fail("transport authority read rejected") from None


def expect_transport_rejected(module: Any, mutate: Callable[[], None], restore: Callable[[], None], label: str) -> None:
    mutate()
    try:
        try:
            module.candidate_reviews_approved({})
        except module.Fail as exc:
            require("execution transport drift" in str(exc), f"{label} rejected at wrong boundary: {exc}")
            return
        raise Fail(f"transport substitution unexpectedly passed: {label}")
    finally:
        restore()


def main() -> int:
    prove_validator_path_failures()
    prove_workflow_guard_mutations_rejected()
    prove_source_order_import_guard()
    module = load_validator()
    canonical_contract = read_authority(module.CONTRACT)
    canonical_registry = read_authority(module.REGISTRY)

    original_run = module.subprocess.run
    expect_transport_rejected(
        module,
        lambda: setattr(module.subprocess, "run", lambda *_args, **_kwargs: None),
        lambda: setattr(module.subprocess, "run", original_run),
        "subprocess.run substitution",
    )

    original_spec = module.importlib.util.spec_from_file_location
    expect_transport_rejected(
        module,
        lambda: setattr(module.importlib.util, "spec_from_file_location", lambda *_args, **_kwargs: None),
        lambda: setattr(module.importlib.util, "spec_from_file_location", original_spec),
        "spec_from_file_location substitution",
    )

    original_module_from_spec = module.importlib.util.module_from_spec
    expect_transport_rejected(
        module,
        lambda: setattr(module.importlib.util, "module_from_spec", lambda *_args, **_kwargs: object()),
        lambda: setattr(module.importlib.util, "module_from_spec", original_module_from_spec),
        "module_from_spec substitution",
    )

    require(read_authority(module.CONTRACT) == canonical_contract, "transport substitution mutated canonical generation evidence contract")
    require(read_authority(module.REGISTRY) == canonical_registry, "transport substitution mutated canonical generation evidence registry")
    print("Memory OS generation independent-review transport negative PASS")
    print("subprocess transport substitution accepted: false")
    print("module loader transport substitution accepted: false")
    print("canonical authority mutation: false")
    print("human production promotion remains separate: true")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION INDEPENDENT REVIEW TRANSPORT NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
