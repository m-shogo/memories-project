#!/usr/bin/env python3
"""Focused negative for final-candidate independent-review execution authority."""

from __future__ import annotations

import ast
import copy
import errno
import importlib.machinery
import importlib.util
import os
import stat
import re
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-independent-review.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


MAX_REVIEW_MODULE_BYTES = 1024 * 1024


def load_checked_module(path: Path, name: str) -> Any:
    """Import only bounded FD-captured repository source bytes."""
    try:
        relative = path.relative_to(ROOT)
        require(path.resolve(strict=True) == ROOT.resolve() / relative,
                "independent review negative source rejected")
        checked = path.lstat()
        require(stat.S_ISREG(checked.st_mode), "independent review negative source rejected")
        require(all(type(getattr(os, flag, None)) is int and getattr(os, flag) > 0
                    for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY")),
                "independent review negative source rejected")
        directory_fds = []
        source_fd = -1
        try:
            directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK
            parent_fd = os.open(ROOT, directory_flags)
            directory_fds.append(parent_fd)
            for component in relative.parts[:-1]:
                parent_fd = os.open(component, directory_flags, dir_fd=parent_fd)
                directory_fds.append(parent_fd)
            source_fd = os.open(relative.name,
                                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
            opened = os.fstat(source_fd)
            require(stat.S_ISREG(opened.st_mode)
                    and (opened.st_dev, opened.st_ino) == (checked.st_dev, checked.st_ino),
                    "independent review negative source rejected")
            with os.fdopen(source_fd, "rb") as stream:
                source_fd = -1
                source = stream.read(MAX_REVIEW_MODULE_BYTES + 1)
        finally:
            cleanup_failed = False
            if source_fd >= 0:
                try:
                    os.close(source_fd)
                except OSError:
                    cleanup_failed = True
            for directory_fd in reversed(directory_fds):
                try:
                    os.close(directory_fd)
                except OSError:
                    cleanup_failed = True
            require(not cleanup_failed, "independent review negative source rejected")
        require(len(source) <= MAX_REVIEW_MODULE_BYTES,
                "independent review negative source rejected")

        class PinnedSourceLoader(importlib.machinery.SourceFileLoader):
            def get_code(self, fullname):
                require(fullname == name, "independent review negative source rejected")
                return compile(source, str(path), "exec")

        spec = importlib.util.spec_from_file_location(
            name, path, loader=PinnedSourceLoader(name, str(path)))
        require(spec is not None and spec.loader is not None,
                "independent review negative source rejected")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:
        raise Fail("independent review negative source rejected") from None
    return module


def load_validator() -> Any:
    return load_checked_module(VALIDATOR, "memory_os_generation_independent_review_execution_negative")


def prove_pinned_validator_import() -> None:
    """After-capture parent substitution must not redirect imported code."""
    original_spec = importlib.util.spec_from_file_location
    with tempfile.TemporaryDirectory(prefix=".independent-review-execution-import-", dir=ROOT) as raw:
        sandbox = Path(raw)
        parent = sandbox / "trusted"
        parent.mkdir()
        source = parent / "module.py"
        parked = sandbox / "parked"
        redirected = sandbox / "redirected"
        redirected.mkdir()
        canary = redirected / "module.py"
        source.write_text("VALUE = 'pinned'\n", encoding="utf-8")
        canary.write_text("raise RuntimeError('PRIVATE_INDEPENDENT_REVIEW_IMPORT_CANARY')\n",
                          encoding="utf-8")
        swapped = False
        try:
            require(load_checked_module(source, "independent_review_import_positive").VALUE == "pinned",
                    "independent review pinned import positive failed")

            def swap_after_read(name, location, *args, **kwargs):
                nonlocal swapped
                if not swapped and Path(location) == source:
                    swapped = True
                    parent.rename(parked)
                    parent.symlink_to(redirected, target_is_directory=True)
                return original_spec(name, location, *args, **kwargs)

            importlib.util.spec_from_file_location = swap_after_read
            loaded = load_checked_module(source, "independent_review_import_parent_swap")
            require(swapped and loaded.VALUE == "pinned",
                    "independent review executed redirected source")
            require(canary.read_text(encoding="utf-8") ==
                    "raise RuntimeError('PRIVATE_INDEPENDENT_REVIEW_IMPORT_CANARY')\n",
                    "independent review changed external canary")
        finally:
            importlib.util.spec_from_file_location = original_spec
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)
    require(callable(getattr(load_validator(), "main", None)),
            "independent review canonical import restoration failed")
    print("PASS: independent review execution negative import pins source across parent swap")

def prove_review_import_unsafe_sources() -> None:
    """Oversized source, symlink, FIFO and unsupported flags are fail-closed."""
    with tempfile.TemporaryDirectory(prefix=".generation-binding-target-unsafe-", dir=ROOT) as raw:
        sandbox = Path(raw)
        good = sandbox / "good.py"
        good.write_text("VALUE = 'safe'\n", encoding="utf-8")
        oversized = sandbox / "oversized.py"
        oversized.write_bytes(b"x" * (MAX_REVIEW_MODULE_BYTES + 1))
        linked = sandbox / "linked.py"
        linked.symlink_to(good.name)
        fifo = sandbox / "pipe.py"
        os.mkfifo(fifo)
        for candidate in (oversized, linked, fifo):
            try:
                load_checked_module(candidate, "independent_review_unsafe")
            except Fail as exc:
                require(str(exc) == "independent review negative source rejected"
                        and exc.__suppress_context__,
                        "independent review execution unsafe source leaked private diagnostics")
            else:
                raise Fail("independent review execution accepted unsafe source")
        original_flag = os.O_NONBLOCK
        try:
            os.O_NONBLOCK = 0
            try:
                load_checked_module(good, "independent_review_unsupported_flag")
            except Fail as exc:
                require(str(exc) == "independent review negative source rejected"
                        and exc.__suppress_context__,
                        "independent review execution missing flag leaked private diagnostics")
            else:
                raise Fail("independent review execution accepted unsupported platform flag")
        finally:
            os.O_NONBLOCK = original_flag
        require(load_checked_module(good, "independent_review_unsafe_restored").VALUE == "safe",
                "independent review execution unsafe fixture restoration failed")
    print("PASS: independent review execution unsafe sources and missing flag rejected")


def prove_review_import_fd_cleanup() -> None:
    """Failed fdopen/close must not leak any descriptor owned by the loader."""
    for fault in ("fdopen", "close"):
        original_open, original_fdopen, original_close = os.open, os.fdopen, os.close
        opened = []
        injected = False

        def tracked_open(*args, **kwargs):
            descriptor = original_open(*args, **kwargs)
            opened.append(descriptor)
            return descriptor

        def broken_fdopen(descriptor, *args, **kwargs):
            nonlocal injected
            if fault == "fdopen" and not injected:
                injected = True
                raise OSError(errno.EIO, "PRIVATE_REVIEW_EXECUTION_FDOPEN_CANARY")
            return original_fdopen(descriptor, *args, **kwargs)

        def broken_close(descriptor):
            nonlocal injected
            if fault == "close" and descriptor in opened and not injected:
                injected = True
                original_close(descriptor)
                raise OSError(errno.EIO, "PRIVATE_REVIEW_EXECUTION_CLOSE_CANARY")
            return original_close(descriptor)

        try:
            os.open, os.fdopen, os.close = tracked_open, broken_fdopen, broken_close
            try:
                load_checked_module(VALIDATOR, "independent_review_fd_fault")
            except Fail as exc:
                require(str(exc) == "independent review negative source rejected"
                        and exc.__suppress_context__ and exc.__cause__ is None,
                        "independent review execution " + fault + " leaked private exception")
            else:
                raise Fail("independent review execution " + fault + " fault accepted")
        finally:
            os.open, os.fdopen, os.close = original_open, original_fdopen, original_close
        require(injected and len(opened) >= 3,
                "independent review execution " + fault + " injection not reached")
        for descriptor in opened:
            try:
                os.fstat(descriptor)
            except OSError as exc:
                require(exc.errno == errno.EBADF,
                        "independent review execution " + fault + " unexpected descriptor error")
            else:
                raise Fail("independent review execution " + fault + " leaked descriptor")
    require(callable(getattr(load_checked_module(VALIDATOR, "independent_review_fd_restored"), "main", None)),
            "independent review execution FD fault canonical restoration failed")
    print("PASS: independent review execution pinned loader fdopen/close faults clean owned descriptors")


def expect_candidate_rejected(module: Any, field: str, replacement: Any) -> None:
    original = getattr(module, field)
    setattr(module, field, replacement)
    try:
        try:
            module.candidate_reviews_approved({})
        except module.Fail:
            return
        raise Fail(f"candidate execution substitution unexpectedly passed: {field}")
    finally:
        setattr(module, field, original)


def expect_candidate_mutation_rejected(module: Any, mutate: Callable[[], None], restore: Callable[[], None], label: str) -> None:
    mutate()
    try:
        try:
            module.candidate_reviews_approved({})
        except module.Fail as exc:
            require("semantic authority drift" in str(exc), f"{label} rejected at wrong boundary: {exc}")
            return
        raise Fail(f"candidate semantic authority substitution unexpectedly passed: {label}")
    finally:
        restore()


def expect_main_rejected(module: Any, mutate: Callable[[], None], restore: Callable[[], None], label: str, expected: str) -> None:
    mutate()
    try:
        try:
            module.main()
        except module.Fail as exc:
            require(expected in str(exc), f"{label} rejected at wrong boundary: {exc}")
            return
        raise Fail(f"main execution substitution unexpectedly passed: {label}")
    finally:
        restore()


SOURCE_ORDER_REL = Path("scripts/validate-memory-os-backup-restore-review-source-order.py")


def source_order_main_body(tree: ast.Module) -> list[ast.stmt]:
    mains = [node for node in tree.body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main"]
    require(len(mains) == 1 and isinstance(mains[0], ast.FunctionDef),
            "source-order canonical main definition drift")
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "main" for target in node.targets
        ):
            raise Fail("source-order canonical main shadowed")
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "main":
            raise Fail("source-order canonical main shadowed")
    return mains[0].body


def source_order_review_loop(body: list[ast.stmt]) -> tuple[int, ast.For]:
    loops = [(index, node) for index, node in enumerate(body) if isinstance(node, ast.For)]
    require(len(loops) == 1, "source-order main review loop drift")
    index, loop = loops[0]
    expected_iter = ast.parse("enumerate(rows)", mode="eval").body
    require(ast.dump(loop.iter) == ast.dump(expected_iter),
            "source-order main review iterator drift")
    require(
        isinstance(loop.target, ast.Tuple)
        and len(loop.target.elts) == 2
        and all(isinstance(item, ast.Name) for item in loop.target.elts)
        and [item.id for item in loop.target.elts] == ["index", "row"],
        "source-order main review target drift",
    )
    expected_call = ast.parse("validate_row(row, index)").body[0]
    require(len(loop.body) == 1 and ast.dump(loop.body[0]) == ast.dump(expected_call)
            and not loop.orelse, "source-order main row validator call drift")
    return index, loop


def require_source_order_main_binding(tree: ast.Module) -> None:
    body = source_order_main_body(tree)
    require(len(body) >= 10, "source-order main body unexpectedly truncated")
    self_test_branch = body[0]
    expected_gate = ast.parse(
        "len(sys.argv) == 2 and sys.argv[1] == '--self-test'", mode="eval"
    ).body
    expected_test = ast.parse("self_test()").body[0]
    expected_return = ast.parse("return 0").body[0]
    require(
        isinstance(self_test_branch, ast.If)
        and ast.dump(self_test_branch.test) == ast.dump(expected_gate)
        and len(self_test_branch.body) == 2
        and ast.dump(self_test_branch.body[0]) == ast.dump(expected_test)
        and ast.dump(self_test_branch.body[1]) == ast.dump(expected_return)
        and not self_test_branch.orelse,
        "source-order main self-test gate drift",
    )
    loop_index, _loop = source_order_review_loop(body)
    expected_contract = ast.parse("validate_contract(contract)").body[0]
    contract_positions = [
        index for index, node in enumerate(body)
        if ast.dump(node) == ast.dump(expected_contract)
    ]
    require(len(contract_positions) == 1 and contract_positions[0] < loop_index,
            "source-order main contract validation reachability drift")
    expected_rows = ast.parse('rows = registry.get("records")').body[0]
    row_positions = [
        index for index, node in enumerate(body)
        if ast.dump(node) == ast.dump(expected_rows)
    ]
    require(len(row_positions) == 1 and contract_positions[0] < row_positions[0] < loop_index,
            "source-order main canonical row source drift")
    require(not any(isinstance(node, (ast.Return, ast.Raise, ast.Break, ast.Continue))
                    for node in body[1:loop_index]),
            "source-order main early termination before review validation")
    require(ast.dump(body[-1]) == ast.dump(expected_return) and loop_index < len(body) - 1,
            "source-order main terminal success boundary drift")


def require_source_order_main_negative_proof() -> None:
    source_path = ROOT / SOURCE_ORDER_REL
    require(source_path.is_file() and not source_path.is_symlink(),
            "canonical source-order validator missing or symlinked")
    require(source_path.resolve(strict=True) == ROOT.resolve(strict=True) / SOURCE_ORDER_REL,
            "canonical source-order validator path drift")
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    require_source_order_main_binding(tree)

    cases = (
        ("remove review loop", "source-order main review loop drift"),
        ("dead-branch review loop", "source-order main review loop drift"),
        ("empty review iterator", "source-order main review iterator drift"),
        ("swapped review target", "source-order main review target drift"),
        ("skip row validator", "source-order main row validator call drift"),
        ("early successful return", "source-order main early termination before review validation"),
        ("unbound row source", "source-order main canonical row source drift"),
        ("omit contract validation", "source-order main contract validation reachability drift"),
        ("unconditional self-test exit", "source-order main self-test gate drift"),
        ("shadow main", "source-order canonical main shadowed"),
        ("duplicate main", "source-order canonical main definition drift"),
    )
    for label, expected in cases:
        mutant = copy.deepcopy(tree)
        body = source_order_main_body(mutant)
        index, loop = source_order_review_loop(body)
        if label == "remove review loop":
            body.pop(index)
        elif label == "dead-branch review loop":
            body[index] = ast.If(test=ast.Constant(False), body=[loop], orelse=[])
        elif label == "empty review iterator":
            loop.iter.args[0] = ast.List(elts=[], ctx=ast.Load())
        elif label == "swapped review target":
            loop.target.elts[0].id = "row"
        elif label == "skip row validator":
            loop.body[0].value.func.id = "print"
        elif label == "early successful return":
            body.insert(index, ast.Return(value=ast.Constant(0)))
        elif label == "unbound row source":
            row_assign = next(node for node in body
                              if isinstance(node, ast.Assign)
                              and any(isinstance(t, ast.Name) and t.id == "rows" for t in node.targets))
            row_assign.value = ast.List(elts=[], ctx=ast.Load())
        elif label == "omit contract validation":
            body[:] = [node for node in body if not (
                isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "validate_contract"
            )]
        elif label == "unconditional self-test exit":
            body[0].test = ast.Constant(True)
        elif label == "shadow main":
            mutant.body.append(ast.Assign(targets=[ast.Name(id="main", ctx=ast.Store())],
                                          value=ast.Constant(None)))
        elif label == "duplicate main":
            original_main = next(node for node in mutant.body
                                 if isinstance(node, ast.FunctionDef) and node.name == "main")
            mutant.body.append(copy.deepcopy(original_main))
        try:
            require_source_order_main_binding(mutant)
        except Fail as exc:
            require(str(exc) == expected,
                    f"source-order main mutation rejected at wrong boundary ({label}): {exc}")
        else:
            raise Fail(f"source-order main guard accepted mutation: {label}")
    print(f"PASS: source-order main AST execution binding rejects {len(cases)} review bypass mutations")



PAIR_NEGATIVE_REL = Path("scripts/validate-memory-os-backup-restore-generation-independent-review-negative.py")


def require_pair_negative_harness_binding(tree: ast.Module) -> None:
    """A passing pair mutation helper is useless if the CI-invoked negative main skips it."""
    proofs = [node for node in tree.body if isinstance(node, ast.FunctionDef)
              and node.name == "prove_candidate_pair_source_binding"]
    runtime_proofs = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                      and node.name == "prove_runtime_review_pair_controls"]
    mains = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name == "main"]
    require(len(proofs) == 1 and len(mains) == 1,
            "candidate pair negative harness definition drift")
    require(len(runtime_proofs) == 1,
            "candidate pair runtime negative harness definition drift")
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == "prove_candidate_pair_source_binding"
                   for target in targets):
                raise Fail("candidate pair negative harness proof shadowed")
            if any(isinstance(target, ast.Name) and target.id == "prove_runtime_review_pair_controls"
                   for target in targets):
                raise Fail("candidate pair runtime negative harness proof shadowed")
    body = mains[0].body
    expected = ast.parse("prove_candidate_pair_source_binding()").body[0]
    calls = [index for index, node in enumerate(body)
             if ast.dump(node, include_attributes=False) ==
             ast.dump(expected, include_attributes=False)]
    require(len(calls) == 1 and calls[0] == 1,
            "candidate pair negative harness proof not second direct main step")
    require(len(body) > 2 and isinstance(body[2], ast.Assign)
            and isinstance(body[2].value, ast.Call)
            and isinstance(body[2].value.func, ast.Name)
            and body[2].value.func.id == "load_validator",
            "candidate pair negative harness proof must precede validator loading")
    runtime_call = ast.parse("prove_runtime_review_pair_controls()").body[0]
    runtime_indices = [index for index, node in enumerate(body)
                       if ast.dump(node, include_attributes=False) ==
                       ast.dump(runtime_call, include_attributes=False)]
    require(len(runtime_indices) == 1 and runtime_indices[0] == 3,
            "candidate pair runtime negative proof not fourth direct main step")


def prove_pair_negative_harness_reachability() -> None:
    path = ROOT / PAIR_NEGATIVE_REL
    require(path.is_file() and not path.is_symlink()
            and path.resolve(strict=True) == ROOT.resolve(strict=True) / PAIR_NEGATIVE_REL,
            "candidate pair negative harness executable missing or substituted")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    require_pair_negative_harness_binding(tree)
    cases = (
        ("omit proof call", "remove", "candidate pair negative harness proof not second direct main step"),
        ("move proof after loader", "move", "candidate pair negative harness proof not second direct main step"),
        ("dead proof branch", "dead", "candidate pair negative harness proof not second direct main step"),
        ("duplicate proof call", "duplicate", "candidate pair negative harness proof not second direct main step"),
        ("remove proof definition", "remove_def", "candidate pair negative harness definition drift"),
        ("shadow proof helper", "shadow", "candidate pair negative harness proof shadowed"),
        ("remove runtime proof", "remove_runtime", "candidate pair runtime negative proof not fourth direct main step"),
        ("dead runtime proof", "dead_runtime", "candidate pair runtime negative proof not fourth direct main step"),
        ("duplicate runtime proof", "duplicate_runtime", "candidate pair runtime negative proof not fourth direct main step"),
        ("remove runtime definition", "remove_runtime_def", "candidate pair runtime negative harness definition drift"),
        ("shadow runtime proof", "shadow_runtime", "candidate pair runtime negative harness proof shadowed"),
    )
    for label, action, expected in cases:
        mutant = copy.deepcopy(tree)
        main = next(node for node in mutant.body
                    if isinstance(node, ast.FunctionDef) and node.name == "main")
        proof = next(node for node in mutant.body
                     if isinstance(node, ast.FunctionDef)
                     and node.name == "prove_candidate_pair_source_binding")
        runtime_proof = next(node for node in mutant.body
                             if isinstance(node, ast.FunctionDef)
                             and node.name == "prove_runtime_review_pair_controls")
        if action == "remove":
            main.body.pop(1)
        elif action == "move":
            main.body.insert(3, main.body.pop(1))
        elif action == "dead":
            main.body[1] = ast.If(test=ast.Constant(False), body=[main.body[1]], orelse=[])
        elif action == "duplicate":
            main.body.insert(2, copy.deepcopy(main.body[1]))
        elif action == "remove_def":
            mutant.body.remove(proof)
        elif action == "shadow":
            mutant.body.append(ast.Assign(targets=[ast.Name(id="prove_candidate_pair_source_binding",
                                                              ctx=ast.Store())],
                                          value=ast.Constant(None)))
        elif action == "remove_runtime":
            main.body.pop(3)
        elif action == "dead_runtime":
            main.body[3] = ast.If(test=ast.Constant(False), body=[main.body[3]], orelse=[])
        elif action == "duplicate_runtime":
            main.body.insert(4, copy.deepcopy(main.body[3]))
        elif action == "remove_runtime_def":
            mutant.body.remove(runtime_proof)
        elif action == "shadow_runtime":
            mutant.body.append(ast.Assign(targets=[ast.Name(id="prove_runtime_review_pair_controls",
                                                              ctx=ast.Store())],
                                          value=ast.Constant(None)))
        try:
            require_pair_negative_harness_binding(mutant)
        except Fail as exc:
            require(str(exc) == expected,
                    f"candidate pair harness mutation wrong diagnostic ({label}): {exc}")
        else:
            raise Fail(f"candidate pair harness mutation accepted: {label}")
    print(f"PASS: external candidate pair negative harness reachability rejects {len(cases)} bypasses")


def prove_source_order_json_reader() -> None:
    """Exercise the actual review chronology reader without modifying review evidence."""
    path_to_validator = ROOT / SOURCE_ORDER_REL
    spec = importlib.util.spec_from_file_location("memory_os_source_order_json_negative", path_to_validator)
    require(spec is not None and spec.loader is not None, "source-order JSON validator unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix="memory-os-source-order-json-", dir=ROOT) as directory:
        path = Path(directory) / "candidate.json"
        positive = b'{"safe":true,"nested":{"count":1}}'
        path.write_bytes(positive)
        require(module.load_json(path, "synthetic") == {"safe": True, "nested": {"count": 1}}, "source-order JSON positive control failed")
        cases = (
            ("duplicate root", b'{"safe":true,"safe":false}', "review source-order JSON duplicate key refused"),
            ("duplicate nested", b'{"nested":{"a":1,"a":2}}', "review source-order JSON duplicate key refused"),
            ("NaN", b'{"number":NaN}', "review source-order JSON nonfinite number refused"),
            ("Infinity", b'{"number":Infinity}', "review source-order JSON nonfinite number refused"),
            ("negative Infinity", b'{"number":-Infinity}', "review source-order JSON nonfinite number refused"),
            ("float overflow", b'{"number":1e999}', "review source-order JSON nonfinite number refused"),
            ("large integer", b'{"number":' + b"9" * 5000 + b"}", "review source-order JSON integer too large"),
            ("oversized JSON", b'{"data":"' + b"x" * module.MAX_JSON_BYTES + b'"}', "review source-order JSON size limit exceeded"),
            ("invalid UTF-8", b'{"private":"\xff"}', "review source-order JSON unreadable or invalid"),
            ("malformed private", b'{"private":"synthetic-secret",', "review source-order JSON unreadable or invalid"),
            ("nonobject root", b"[]", "review source-order JSON root must be object"),
        )
        def rejected(candidate: Any, expected: str, label: str) -> None:
            try:
                module.load_json(candidate, "synthetic-secret")
            except module.Fail as exc:
                require(str(exc) == expected, f"{label}: wrong source-order JSON rejection boundary")
                require("synthetic-secret" not in str(exc), f"{label}: private marker disclosed")
            else:
                raise Fail(f"{label}: unsafe source-order JSON accepted")
        for label, payload, expected in cases:
            path.write_bytes(payload)
            rejected(path, expected, label)
        path.write_bytes(positive)
        alias = Path(directory) / "alias.json"
        alias.symlink_to(path)
        rejected(alias, "review source-order JSON path missing or unsafe", "symlink")
        rejected(Path(directory), "review source-order JSON path missing or unsafe", "directory")
        rejected(Path(directory) / "missing.json", "review source-order JSON path missing or unsafe", "missing")
        rejected("candidate.json", "review source-order JSON path invalid", "non-Path")
        with tempfile.TemporaryDirectory(prefix="memory-os-source-order-canary-") as outside:
            canary = Path(outside) / "canary.json"
            canary.write_bytes(positive)
            escaped = Path(directory) / "escaped.json"
            escaped.symlink_to(canary)
            rejected(escaped, "review source-order JSON path missing or unsafe", "external symlink")
            require(canary.read_bytes() == positive, "source-order JSON reader modified external canary")
        require(path.read_bytes() == positive, "source-order JSON reader mutated positive fixture")
    print("PASS: actual source-order JSON reader positive and 16 fail-closed negatives")


def require_pair_pinned_import_source(code: str) -> None:
    """Require the pair-negative's executable pinned loader and parent-swap proof."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        raise Fail("independent review pair pinned source syntax invalid") from None
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    required = {
        "load_checked_pair_module": (
            "stream.read(MAX_PAIR_MODULE_BYTES + 1)",
            "require(len(source) <= MAX_PAIR_MODULE_BYTES",
            "os.open(component, directory_flags, dir_fd=parent_fd)",
            "os.open(relative.name,",
            "os.O_NOFOLLOW | os.O_NONBLOCK",
            "for directory_fd in reversed(directory_fds):",
            "class PinnedSourceLoader(importlib.machinery.SourceFileLoader):",
            'return compile(source, str(path), "exec")',
            "spec.loader.exec_module(module)",
            'raise Fail("independent review pair module rejected") from None',
        ),
        "prove_pinned_pair_validator_import": (
            'load_checked_pair_module(source, "review_pair_import_positive")',
            'load_checked_pair_module(source, "review_pair_import_parent_swap")',
            "parent.rename(parked)",
            "parent.symlink_to(redirected",
            'loaded.VALUE == "pinned"',
            'require(canary.read_text(encoding="utf-8") ==',
            "PRIVATE_INDEPENDENT_REVIEW_PAIR_CANARY",
            "importlib.util.spec_from_file_location = original_spec",
        ),
        "load_validator": ("return load_checked_pair_module(",),
        "prove_pair_import_unsafe_sources": (
            "oversized.write_bytes(b\"x\" * (MAX_PAIR_MODULE_BYTES + 1))",
            "linked.symlink_to(good.name)",
            "os.mkfifo(fifo)",
            "os.O_NONBLOCK = 0",
            'load_checked_pair_module(good, "review_pair_unsafe_restored")',
        ),
        "prove_pair_import_fd_cleanup": (
            "def tracked_open(",
            "def broken_fdopen(",
            "def broken_close(",
            'load_checked_pair_module(VALIDATOR, "review_pair_fd_fault")',
            "os.fstat(descriptor)",
            "errno.EBADF",
            "os.open, os.fdopen, os.close = original_open, original_fdopen, original_close",
            "PASS: independent review pair pinned loader fdopen/close faults clean owned descriptors",
        ),
        "main": (
            "prove_runtime_review_pair_controls()",
            "prove_pinned_pair_validator_import()",
            "prove_pair_import_unsafe_sources()",
            "prove_pair_import_fd_cleanup()",
            "prove_source_order_bounded_git_output(module)",
        ),
    }
    for name, tokens in required.items():
        node = functions.get(name)
        require(node is not None, "independent review pair pinned function missing: " + name)
        fragment = ast.get_source_segment(code, node) or ""
        for token in tokens:
            require(token in fragment, "independent review pair pinned source drift: " + name)
    main = ast.get_source_segment(code, functions["main"]) or ""
    require(main.index("prove_runtime_review_pair_controls()")
            < main.index("prove_pinned_pair_validator_import()")
            < main.index("prove_pair_import_unsafe_sources()")
            < main.index("prove_pair_import_fd_cleanup()")
            < main.index("prove_source_order_bounded_git_output(module)"),
            "independent review pair pinned proof unreachable after canonical main steps")


def prove_pair_pinned_import_mutations_rejected() -> None:
    code = (ROOT / PAIR_NEGATIVE_REL).read_text(encoding="utf-8")
    require_pair_pinned_import_source(code)
    mutations = (
        ("load_checked_pair_module", "stream.read(MAX_PAIR_MODULE_BYTES + 1)", "stream.read()"),
        ("load_checked_pair_module", "os.open(component, directory_flags, dir_fd=parent_fd)",
         "os.open(path.parent, directory_flags)"),
        ("load_checked_pair_module", 'return compile(source, str(path), "exec")',
         'return compile(path.read_bytes(), str(path), "exec")'),
        ("load_checked_pair_module", "for directory_fd in reversed(directory_fds):",
         "for directory_fd in ():"),
        ("load_checked_pair_module", 'raise Fail("independent review pair module rejected") from None',
         'raise Fail("independent review pair module rejected")'),
        ("prove_pinned_pair_validator_import", "parent.symlink_to(redirected",
         "parent.symlink_to(parked"),
        ("prove_pinned_pair_validator_import", 'loaded.VALUE == "pinned"',
         'loaded.VALUE == "redirected"'),
        ("prove_pinned_pair_validator_import", 'require(canary.read_text(encoding="utf-8") ==',
         'require(False and canary.read_text(encoding="utf-8") =='),
        ("load_validator", "return load_checked_pair_module(",
         "return load_unpinned_pair_module("),
        ("prove_pair_import_unsafe_sources", "os.mkfifo(fifo)",
         "pass  # synthetic FIFO proof removed"),
        ("prove_pair_import_unsafe_sources", "os.O_NONBLOCK = 0",
         "os.O_NONBLOCK = original_flag"),
        ("main", "prove_pinned_pair_validator_import()",
         "pass  # synthetic pinned proof removed"),
        ("prove_pair_import_fd_cleanup", "os.fstat(descriptor)", "os.fstat(-1)"),
        ("prove_pair_import_fd_cleanup", "errno.EBADF", "errno.EIO"),
        ("prove_pair_import_fd_cleanup",
         "PASS: independent review pair pinned loader fdopen/close faults clean owned descriptors",
         "PASS: drill request pinned loader fdopen/close faults clean owned descriptors"),
        ("main", "prove_pair_import_unsafe_sources()",
         "pass  # synthetic unsafe proof removed"),
        ("main", "prove_pair_import_fd_cleanup()",
         "pass  # synthetic FD cleanup proof removed"),
    )
    for name, original, replacement in mutations:
        tree = ast.parse(code)
        nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
        require(len(nodes) == 1, "independent review pair pinned mutation function drift")
        lines = code.splitlines(keepends=True)
        node = nodes[0]
        fragment = "".join(lines[node.lineno - 1:node.end_lineno])
        require(fragment.count(original) == 1,
                "independent review pair pinned mutation anchor drift: " + name)
        mutated = ("".join(lines[:node.lineno - 1]) + fragment.replace(original, replacement, 1)
                   + "".join(lines[node.end_lineno:]))
        ast.parse(mutated)
        try:
            require_pair_pinned_import_source(mutated)
        except Fail:
            continue
        raise Fail("independent review pair pinned source weakening accepted: " + name)
    print(f"PASS: independent review pair negative pinned import {len(mutations)} mutations rejected")


def main() -> int:
    require_source_order_main_negative_proof()
    prove_source_order_json_reader()
    prove_pair_negative_harness_reachability()
    prove_pair_pinned_import_mutations_rejected()
    prove_pinned_validator_import()
    prove_review_import_unsafe_sources()
    prove_review_import_fd_cleanup()
    module = load_validator()
    canonical_contract = module.CONTRACT.read_bytes()
    canonical_registry = module.REGISTRY.read_bytes()

    for field, replacement in (
        ("enforce_execution_authority", lambda: None),
        ("enforce_runtime_authorities", lambda: None),
        ("require", lambda *_args: None),
        ("require_exact_repo_file", lambda path, *_args: path),
        ("load_json", lambda *_args: {}),
        ("validate_contract_authority", lambda: None),
        ("canonical_ref", lambda *_args: ("docs/evidence/backup-restore/fake.json", Path("/tmp/fake-review.json"))),
        ("git_history", lambda *_args: ["a" * 40]),
        ("require_append_only_review", lambda *_args: None),
        ("require_utc_rfc3339", lambda value, _field: value),
        ("validate_review", lambda *_args: ("docs/evidence/backup-restore/fake.json", "reviewer-fake")),
        ("load_material_delta_validator", lambda: object()),
    ):
        expect_candidate_rejected(module, field, replacement)

    original_contract = module.CONTRACT
    original_contract_rel = module.CONTRACT_REL
    expect_candidate_mutation_rejected(
        module,
        lambda: (setattr(module, "CONTRACT", module.REGISTRY), setattr(module, "CONTRACT_REL", module.REGISTRY_REL)),
        lambda: (setattr(module, "CONTRACT", original_contract), setattr(module, "CONTRACT_REL", original_contract_rel)),
        "paired contract path authority substitution",
    )

    original_registry = module.REGISTRY
    original_registry_rel = module.REGISTRY_REL
    expect_candidate_mutation_rejected(
        module,
        lambda: (setattr(module, "REGISTRY", module.CONTRACT), setattr(module, "REGISTRY_REL", module.CONTRACT_REL)),
        lambda: (setattr(module, "REGISTRY", original_registry), setattr(module, "REGISTRY_REL", original_registry_rel)),
        "paired registry path authority substitution",
    )

    original_material = module.MATERIAL_DELTA_VALIDATOR
    original_material_rel = module.MATERIAL_DELTA_VALIDATOR_REL
    expect_candidate_mutation_rejected(
        module,
        lambda: (setattr(module, "MATERIAL_DELTA_VALIDATOR", module.VALIDATOR), setattr(module, "MATERIAL_DELTA_VALIDATOR_REL", module.VALIDATOR_REL)),
        lambda: (setattr(module, "MATERIAL_DELTA_VALIDATOR", original_material), setattr(module, "MATERIAL_DELTA_VALIDATOR_REL", original_material_rel)),
        "paired material-delta validator authority substitution",
    )

    original_evidence_root = module.EVIDENCE_ROOT
    expect_candidate_mutation_rejected(
        module,
        lambda: setattr(module, "EVIDENCE_ROOT", Path("docs/evidence")),
        lambda: setattr(module, "EVIDENCE_ROOT", original_evidence_root),
        "review evidence root widening",
    )

    original_schema = module.REVIEW_SCHEMA
    expect_candidate_mutation_rejected(
        module,
        lambda: setattr(module, "REVIEW_SCHEMA", "memory-os-backup-restore-generation-review-evidence.v0"),
        lambda: setattr(module, "REVIEW_SCHEMA", original_schema),
        "review schema substitution",
    )

    original_fields = module.REQUIRED_FIELDS
    expect_candidate_mutation_rejected(
        module,
        lambda: setattr(module, "REQUIRED_FIELDS", set(original_fields) - {"drillRequestId"}),
        lambda: setattr(module, "REQUIRED_FIELDS", original_fields),
        "required review field removal",
    )

    original_bound_fields = module.BOUND_FIELDS
    expect_candidate_mutation_rejected(
        module,
        lambda: setattr(module, "BOUND_FIELDS", tuple(field for field in original_bound_fields if field != "recoveryObjectivesId")),
        lambda: setattr(module, "BOUND_FIELDS", original_bound_fields),
        "review binding field removal",
    )

    original_roles = module.ROLE_BY_REF
    expect_candidate_mutation_rejected(
        module,
        lambda: setattr(module, "ROLE_BY_REF", {"securityReviewRef": "OPERABILITY", "operabilityReviewRef": "SECURITY"}),
        lambda: setattr(module, "ROLE_BY_REF", original_roles),
        "review role map substitution",
    )

    original_bound_rules = module.BOUND_RULE_BY_FIELD
    weakened_rules = dict(original_bound_rules)
    weakened_rules["recoveryObjectivesId"] = "independentReviewMustBindEvidenceId"
    expect_candidate_mutation_rejected(
        module,
        lambda: setattr(module, "BOUND_RULE_BY_FIELD", weakened_rules),
        lambda: setattr(module, "BOUND_RULE_BY_FIELD", original_bound_rules),
        "review binding rule map substitution",
    )

    original_reviewer = module.REVIEWER_ID
    expect_candidate_mutation_rejected(
        module,
        lambda: setattr(module, "REVIEWER_ID", re.compile(r"^.*$")),
        lambda: setattr(module, "REVIEWER_ID", original_reviewer),
        "reviewer identity rule widening",
    )

    original_guard = module.enforce_execution_authority
    expect_main_rejected(
        module,
        lambda: setattr(module, "enforce_execution_authority", lambda: None),
        lambda: setattr(module, "enforce_execution_authority", original_guard),
        "main execution guard substitution",
        "main execution guard drift",
    )

    original_candidate = module.candidate_reviews_approved
    expect_main_rejected(
        module,
        lambda: setattr(module, "candidate_reviews_approved", lambda _row: True),
        lambda: setattr(module, "candidate_reviews_approved", original_candidate),
        "main candidate helper substitution",
        "candidate authority drift",
    )

    original_guard = module.enforce_execution_authority
    original_candidate = module.candidate_reviews_approved
    def mutate_both() -> None:
        module.enforce_execution_authority = lambda: None
        module.candidate_reviews_approved = lambda _row: True
    def restore_both() -> None:
        module.enforce_execution_authority = original_guard
        module.candidate_reviews_approved = original_candidate
    expect_main_rejected(
        module,
        mutate_both,
        restore_both,
        "main guard and candidate double substitution",
        "main execution guard drift",
    )

    require(module.CONTRACT.read_bytes() == canonical_contract, "execution substitution mutated canonical generation evidence contract")
    require(module.REGISTRY.read_bytes() == canonical_registry, "execution substitution mutated canonical generation evidence registry")
    print("Memory OS generation independent-review execution authority negative PASS")
    print("candidate execution helper substitution accepted: false")
    print("paired semantic authority substitution accepted: false")
    print("review binding semantic substitution accepted: false")
    print("main execution guard substitution accepted: false")
    print("main candidate helper substitution accepted: false")
    print("main double substitution accepted: false")
    print("canonical authority mutation: false")
    print("human production promotion remains separate: true")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION INDEPENDENT REVIEW EXECUTION NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
