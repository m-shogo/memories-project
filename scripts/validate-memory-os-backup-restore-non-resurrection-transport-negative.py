#!/usr/bin/env python3
"""Prove typed non-resurrection execution, registry and reconcile transport fail closed."""

from __future__ import annotations

import ast
import copy
import importlib.util
import json
import os
import shutil
import subprocess
import stat
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py"
WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-non-resurrection-authority.py"
TEMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_validator():
    return load_module(VALIDATOR, "memory_os_typed_transport_negative")


def expect_rejected(name: str, action: Callable[[], object], fail_type: type[BaseException]) -> None:
    try:
        action()
    except fail_type:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def assert_no_registry_temp_residue(parent: Path) -> None:
    residue = [
        path.name
        for path in parent.iterdir()
        if path.name.startswith(".backup-restore-non-resurrection.")
        or path.name.startswith(".backup-restore-non-resurrection-rollback.")
    ]
    require(not residue, f"typed registry temp residue remained: {residue}")


def exercise_registry_transaction_transport() -> None:
    require(WRITER.is_file() and not WRITER.is_symlink(), "canonical typed writer missing or symlinked")
    require(TEMP_PARENT.is_dir(), "repo-local typed transport temp parent missing")
    writer = load_module(WRITER, "memory_os_typed_writer_transport_negative")
    base = {
        "schemaVersion": "memory-os-backup-restore-non-resurrection-admission-registry.v1",
        "appendOnly": True,
        "registeredRecordCount": 0,
        "completeRecordCount": 0,
        "candidateCoveredCount": 0,
        "records": [],
        "productionEvidence": False,
        "productionReady": False,
    }

    with tempfile.TemporaryDirectory(prefix=".memory-os-nonres-transport-negative-", dir=TEMP_PARENT) as tmp:
        parent = Path(tmp)
        registry = parent / "typed-registry.json"
        registry.write_text(json.dumps(base, indent=2) + "\n", encoding="utf-8")
        registry.chmod(0o640)
        writer.REGISTRY = registry
        original_bytes = registry.read_bytes()
        original_mode = stat.S_IMODE(registry.stat().st_mode)
        require(original_mode == 0o640, "typed registry negative fixture mode setup failed")

        writer.atomic_write(copy.deepcopy(base), original_mode)
        require(stat.S_IMODE(registry.stat().st_mode) == original_mode, "successful typed registry replace changed mode")
        assert_no_registry_temp_residue(parent)

        before_reject = registry.read_bytes()
        original_replace = writer.os.replace

        def reject_replace(*_args: object, **_kwargs: object) -> None:
            raise OSError("controlled typed registry replace rejection")

        writer.os.replace = reject_replace
        try:
            expect_rejected(
                "typed registry atomic replace rejection",
                lambda: writer.atomic_write(copy.deepcopy(base), original_mode),
                OSError,
            )
        finally:
            writer.os.replace = original_replace
        require(registry.read_bytes() == before_reject, "replace rejection mutated typed registry bytes")
        require(stat.S_IMODE(registry.stat().st_mode) == original_mode, "replace rejection mutated typed registry mode")
        assert_no_registry_temp_residue(parent)

        candidate = copy.deepcopy(base)
        candidate["registeredRecordCount"] = 1
        original_guard = writer.validate_registry_for_append

        def reject_post_write(_value: dict[str, object]) -> list[dict[str, object]]:
            raise writer.Fail("controlled typed registry post-write validation failure")

        writer.validate_registry_for_append = reject_post_write
        try:
            expect_rejected(
                "typed registry post-write validation rollback",
                lambda: writer.write_registry_transactionally(candidate),
                writer.Fail,
            )
        finally:
            writer.validate_registry_for_append = original_guard
        require(registry.read_bytes() == original_bytes, "post-write failure did not restore exact typed registry bytes")
        require(stat.S_IMODE(registry.stat().st_mode) == original_mode, "post-write failure did not restore typed registry mode")
        assert_no_registry_temp_residue(parent)


def exercise_reconciler_transaction_transport() -> None:
    require(RECONCILER.is_file() and not RECONCILER.is_symlink(), "canonical typed reconciler missing or symlinked")
    reconciler = load_module(RECONCILER, "memory_os_typed_reconcile_transport_negative")
    output_names = ("REGISTRY", "GEN_REGISTRY", "CONTRACT", "STATUS")

    for fail_index in (2, 3, 4):
        with tempfile.TemporaryDirectory(prefix=f".memory-os-nonres-reconcile-transaction-{fail_index}-", dir=TEMP_PARENT) as tmp:
            parent = Path(tmp)
            originals = {name: getattr(reconciler, name) for name in output_names}
            copies: dict[str, Path] = {}
            expected: dict[str, bytes] = {}
            for name, source in originals.items():
                target = parent / source.name
                shutil.copy2(source, target)
                target.chmod(0o640)
                copies[name] = target
                expected[name] = target.read_bytes()

            original_enforcer = reconciler.enforce_runtime_authorities
            original_replace = reconciler.os.replace
            replace_calls = 0

            def fail_nth_replace(source: str | Path, destination: str | Path) -> None:
                nonlocal replace_calls
                replace_calls += 1
                if replace_calls == fail_index:
                    raise OSError(f"controlled typed reconcile replace failure #{fail_index}")
                original_replace(source, destination)

            for name, target in copies.items():
                setattr(reconciler, name, target)
            reconciler.enforce_runtime_authorities = lambda: None
            reconciler.os.replace = fail_nth_replace
            try:
                expect_rejected(
                    f"typed reconcile transaction replace #{fail_index}",
                    reconciler.main,
                    reconciler.Fail,
                )
            finally:
                reconciler.os.replace = original_replace
                reconciler.enforce_runtime_authorities = original_enforcer
                for name, source in originals.items():
                    setattr(reconciler, name, source)

            require(
                replace_calls >= fail_index + len(output_names),
                f"typed reconcile rollback did not restore all authorities after replace #{fail_index}: {replace_calls}",
            )
            for name, target in copies.items():
                require(target.read_bytes() == expected[name], f"typed reconcile {name} bytes changed after replace #{fail_index} rollback")
                require(stat.S_IMODE(target.stat().st_mode) == 0o640, f"typed reconcile {name} mode changed after replace #{fail_index} rollback")
            residue = list(parent.glob(".*.tmp"))
            require(not residue, f"typed reconcile replace #{fail_index} left temporary files: {residue}")

    print("PASS rollback: typed 4-authority reconcile restores exact bytes+mode after middle/last replace failures")






def require_typed_admission_cli_dispatch(tree: ast.Module) -> None:
    """Require the executable typed admission to invoke main and exit on Fail."""
    guards = [node for node in tree.body
              if isinstance(node, ast.If)
              and isinstance(node.test, ast.Compare)
              and isinstance(node.test.left, ast.Name)
              and node.test.left.id == "__name__"
              and len(node.test.ops) == 1
              and isinstance(node.test.ops[0], ast.Eq)
              and len(node.test.comparators) == 1
              and isinstance(node.test.comparators[0], ast.Constant)
              and node.test.comparators[0].value == "__main__"]
    require(len(guards) == 1 and guards[0] is tree.body[-1],
            "typed admission CLI dispatch guard missing or duplicated")
    guard = guards[0]
    require(not guard.orelse and len(guard.body) == 1
            and isinstance(guard.body[0], ast.Try),
            "typed admission CLI dispatch must be direct try")
    dispatch = guard.body[0]
    require(len(dispatch.body) == 1 and isinstance(dispatch.body[0], ast.Raise),
            "typed admission CLI dispatch must raise main exit status")
    raised = dispatch.body[0].exc
    require(isinstance(raised, ast.Call) and isinstance(raised.func, ast.Name)
            and raised.func.id == "SystemExit" and len(raised.args) == 1
            and not raised.keywords
            and isinstance(raised.args[0], ast.Call)
            and isinstance(raised.args[0].func, ast.Name)
            and raised.args[0].func.id == "main"
            and not raised.args[0].args and not raised.args[0].keywords,
            "typed admission CLI dispatch must call guarded main")
    require(not dispatch.orelse and not dispatch.finalbody
            and len(dispatch.handlers) == 1
            and isinstance(dispatch.handlers[0].type, ast.Name)
            and dispatch.handlers[0].type.id == "Fail",
            "typed admission CLI dispatch must catch only Fail")
    handler = dispatch.handlers[0]
    require(bool(handler.body) and isinstance(handler.body[-1], ast.Raise)
            and isinstance(handler.body[-1].exc, ast.Call)
            and isinstance(handler.body[-1].exc.func, ast.Name)
            and handler.body[-1].exc.func.id == "SystemExit"
            and len(handler.body[-1].exc.args) == 1
            and isinstance(handler.body[-1].exc.args[0], ast.Constant)
            and type(handler.body[-1].exc.args[0].value) is int
            and handler.body[-1].exc.args[0].value != 0,
            "typed admission CLI Fail handler must exit nonzero")


def prove_typed_admission_cli_dispatch() -> None:
    try:
        canonical = ast.parse(VALIDATOR.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise Fail("typed admission CLI dispatch source unavailable") from exc
    require_typed_admission_cli_dispatch(canonical)
    cases = (
        ("guard-removed", "typed admission CLI dispatch guard missing or duplicated"),
        ("guard-duplicate", "typed admission CLI dispatch guard missing or duplicated"),
        ("guard-not-last", "typed admission CLI dispatch guard missing or duplicated"),
        ("guard-else", "typed admission CLI dispatch must be direct try"),
        ("dispatch-call-only", "typed admission CLI dispatch must raise main exit status"),
        ("dispatch-dead", "typed admission CLI dispatch must raise main exit status"),
        ("dispatch-zero", "typed admission CLI dispatch must call guarded main"),
        ("dispatch-argument", "typed admission CLI dispatch must call guarded main"),
        ("handler-type", "typed admission CLI dispatch must catch only Fail"),
        ("handler-extra", "typed admission CLI dispatch must catch only Fail"),
        ("handler-finally", "typed admission CLI dispatch must catch only Fail"),
        ("handler-swallow", "typed admission CLI Fail handler must exit nonzero"),
        ("handler-zero", "typed admission CLI Fail handler must exit nonzero"),
    )
    for label, expected in cases:
        mutated = copy.deepcopy(canonical)
        guard = mutated.body[-1]
        dispatch = guard.body[0]
        handler = dispatch.handlers[0]
        if label == "guard-removed":
            guard.test = ast.Constant(value=False)
        elif label == "guard-duplicate":
            mutated.body.append(copy.deepcopy(guard))
        elif label == "guard-not-last":
            mutated.body.append(ast.Pass())
        elif label == "guard-else":
            guard.orelse = [ast.Pass()]
        elif label == "dispatch-call-only":
            dispatch.body = [ast.Expr(value=ast.Call(func=ast.Name(id="main", ctx=ast.Load()),
                                                      args=[], keywords=[]))]
        elif label == "dispatch-dead":
            dispatch.body = [ast.If(test=ast.Constant(value=False),
                                    body=dispatch.body, orelse=[])]
        elif label == "dispatch-zero":
            dispatch.body[0].exc.args = [ast.Constant(value=0)]
        elif label == "dispatch-argument":
            dispatch.body[0].exc.args[0].args = [ast.Constant(value=None)]
        elif label == "handler-type":
            handler.type = ast.Name(id="Exception", ctx=ast.Load())
        elif label == "handler-extra":
            dispatch.handlers.append(copy.deepcopy(handler))
        elif label == "handler-finally":
            dispatch.finalbody = [ast.Pass()]
        elif label == "handler-swallow":
            handler.body[-1] = ast.Pass()
        elif label == "handler-zero":
            handler.body[-1].exc.args = [ast.Constant(value=0)]
        try:
            require_typed_admission_cli_dispatch(mutated)
        except Fail as exc:
            require(str(exc) == expected,
                    f"typed admission CLI {label} rejection diagnostic drift")
        else:
            raise Fail(f"typed admission CLI {label} bypass unexpectedly accepted")
    print("PASS reject: thirteen typed admission CLI dispatch/failure-exit substitutions")


def require_typed_admission_main_binding(tree: ast.Module) -> None:
    """Reject rebinding the actual typed admission CLI entrypoint."""
    definitions = [node for node in tree.body
                   if isinstance(node, ast.FunctionDef) and node.name == "main"]
    require(len(definitions) == 1,
            "typed admission must define exactly one synchronous main")
    definition = definitions[0]
    args = definition.args
    require(not definition.decorator_list and not args.posonlyargs
            and [arg.arg for arg in args.args] == ["canonical_execution_guard"]
            and len(args.defaults) == 1 and not args.vararg
            and not args.kwonlyargs and not args.kwarg and not args.kw_defaults,
            "typed admission main signature/decorator drift")

    def rebinds(node: ast.AST) -> bool:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == "main":
                return True
        if isinstance(node, ast.arg) and node.arg == "main":
            return True
        if isinstance(node, ast.alias) and (node.asname or node.name.split(".")[0]) == "main":
            return True
        if isinstance(node, ast.Name) and node.id == "main" and isinstance(node.ctx, (ast.Store, ast.Del)):
            return True
        if (isinstance(node, ast.Subscript)
                and isinstance(node.ctx, (ast.Store, ast.Del))
                and isinstance(node.slice, ast.Constant) and node.slice.value == "main"):
            target = node.value
            if (isinstance(target, ast.Call) and isinstance(target.func, ast.Name)
                    and target.func.id in {"globals", "vars", "locals"}
                    and not target.args and not target.keywords):
                return True
            if isinstance(target, ast.Attribute) and target.attr == "__dict__":
                return True
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {"exec", "eval"}:
                return True
            if (isinstance(node.func, ast.Name) and node.func.id in {"setattr", "delattr"}
                    and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant)
                    and node.args[1].value == "main"):
                return True
            if (isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"update", "pop", "popitem", "clear",
                                           "setdefault", "__setitem__", "__delitem__"}):
                target = node.func.value
                if (isinstance(target, ast.Call) and isinstance(target.func, ast.Name)
                        and target.func.id in {"globals", "vars", "locals"}
                        and not target.args and not target.keywords):
                    return True
                if isinstance(target, ast.Attribute) and target.attr == "__dict__":
                    return True
        return any(rebinds(child) for child in ast.iter_child_nodes(node))

    for statement in tree.body:
        if statement is not definition:
            require(not rebinds(statement), "typed admission main binding drift")


def prove_typed_admission_main_binding() -> None:
    try:
        canonical = ast.parse(VALIDATOR.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise Fail("typed admission main source unavailable") from exc
    require_typed_admission_main_binding(canonical)
    cases = (
        ("assignment", "main = lambda: 0"),
        ("tuple", "main, unused = (lambda: 0), None"),
        ("import-alias", "from random import randint as main"),
        ("dead-branch", "if False: main = None"),
        ("globals", "globals()['main'] = None"),
        ("globals-update", "globals().update(main=None)"),
        ("module-dict", "sys.modules[__name__].__dict__['main'] = None"),
        ("setattr", "setattr(sys.modules[__name__], 'main', None)"),
        ("exec", "exec('main = None')"),
        ("class", "class main: pass"),
        ("duplicate", "def main(): pass"),
        ("async", "async def main(): pass"),
    )
    for label, source in cases:
        mutated = copy.deepcopy(canonical)
        mutated.body[-1:-1] = ast.parse(source).body
        try:
            require_typed_admission_main_binding(mutated)
        except Fail as exc:
            expected = ("typed admission must define exactly one synchronous main"
                        if label == "duplicate" else "typed admission main binding drift")
            require(str(exc) == expected,
                    f"typed admission main {label} rejection diagnostic drift")
        else:
            raise Fail(f"typed admission main {label} replacement unexpectedly accepted")
    decorated = copy.deepcopy(canonical)
    main = next(node for node in decorated.body
                if isinstance(node, ast.FunctionDef) and node.name == "main")
    main.decorator_list.append(ast.Name(id="wrapper", ctx=ast.Load()))
    try:
        require_typed_admission_main_binding(decorated)
    except Fail as exc:
        require(str(exc) == "typed admission main signature/decorator drift",
                "typed admission main decorator diagnostic drift")
    else:
        raise Fail("typed admission main decorator unexpectedly accepted")
    print("PASS reject: thirteen typed admission main rebinding/decorator substitutions")


def require_unique_validator_runner_binding(tree: ast.Module) -> None:
    """Reject module-level or deferred rebinding of the admission child runner."""
    definitions = [node for node in tree.body
                   if isinstance(node, ast.FunctionDef) and node.name == "run_validator"]
    require(len(definitions) == 1,
            "typed admission must define exactly one synchronous child runner")
    definition = definitions[0]
    args = definition.args
    require(not definition.decorator_list and not args.posonlyargs
            and [arg.arg for arg in args.args] == ["path", "label"]
            and not args.vararg and not args.kwonlyargs and not args.kwarg
            and not args.defaults and not args.kw_defaults,
            "typed admission child runner signature/decorator drift")

    def rebinds_runner(node: ast.AST) -> bool:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == "run_validator":
                return True
        if isinstance(node, ast.arg) and node.arg == "run_validator":
            return True
        if isinstance(node, ast.alias) and (node.asname or node.name.split(".")[0]) == "run_validator":
            return True
        if isinstance(node, ast.Name) and node.id == "run_validator" and isinstance(node.ctx, (ast.Store, ast.Del)):
            return True
        if (isinstance(node, ast.Subscript)
                and isinstance(node.ctx, (ast.Store, ast.Del))
                and isinstance(node.slice, ast.Constant)
                and node.slice.value == "run_validator"):
            target = node.value
            if (isinstance(target, ast.Call) and isinstance(target.func, ast.Name)
                    and target.func.id in {"globals", "vars", "locals"}
                    and not target.args and not target.keywords):
                return True
            if isinstance(target, ast.Attribute) and target.attr == "__dict__":
                return True
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {"exec", "eval"}:
                return True
            if (isinstance(node.func, ast.Name) and node.func.id in {"setattr", "delattr"}
                    and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant)
                    and node.args[1].value == "run_validator"):
                return True
            if (isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"update", "pop", "popitem", "clear",
                                           "setdefault", "__setitem__", "__delitem__"}):
                target = node.func.value
                if (isinstance(target, ast.Call) and isinstance(target.func, ast.Name)
                        and target.func.id in {"globals", "vars", "locals"}
                        and not target.args and not target.keywords):
                    return True
                if isinstance(target, ast.Attribute) and target.attr == "__dict__":
                    return True
        return any(rebinds_runner(child) for child in ast.iter_child_nodes(node))

    for statement in tree.body:
        if statement is not definition:
            require(not rebinds_runner(statement),
                    "typed admission child runner binding drift")


def prove_validator_runner_binding() -> None:
    try:
        source = VALIDATOR.read_text(encoding="utf-8")
        canonical = ast.parse(source)
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise Fail("typed admission child runner source unavailable") from exc
    require_unique_validator_runner_binding(canonical)
    cases = (
        ("assignment", "run_validator = lambda path, label: None"),
        ("import-alias", "from random import randint as run_validator"),
        ("dead-branch", "if False: run_validator = None"),
        ("globals", "globals()['run_validator'] = None"),
        ("globals-update", "globals().update(run_validator=None)"),
        ("globals-pop", "globals().pop('run_validator')"),
        ("module-dict", "sys.modules[__name__].__dict__['run_validator'] = None"),
        ("setattr", "setattr(sys.modules[__name__], 'run_validator', None)"),
        ("exec", "exec('run_validator = None')"),
        ("duplicate", "def run_validator(path, label): pass"),
    )
    for label, source_mutation in cases:
        mutated = copy.deepcopy(canonical)
        mutated.body.extend(ast.parse(source_mutation).body)
        try:
            require_unique_validator_runner_binding(mutated)
        except Fail as exc:
            expected = ("typed admission must define exactly one synchronous child runner"
                        if label == "duplicate" else
                        "typed admission child runner binding drift")
            require(str(exc) == expected,
                    f"typed admission child runner {label} rejection diagnostic drift")
        else:
            raise Fail(f"typed admission child runner {label} bypass unexpectedly accepted")
    decorated = copy.deepcopy(canonical)
    runner = next(node for node in decorated.body
                  if isinstance(node, ast.FunctionDef) and node.name == "run_validator")
    runner.decorator_list.append(ast.Name(id="wrapper", ctx=ast.Load()))
    try:
        require_unique_validator_runner_binding(decorated)
    except Fail as exc:
        require(str(exc) == "typed admission child runner signature/decorator drift",
                "typed admission child runner decorator rejection diagnostic drift")
    else:
        raise Fail("typed admission child runner decorator bypass unexpectedly accepted")
    print("PASS reject: eleven typed admission child runner binding/decorator substitutions")


def exercise_validator_child_exit_propagation(validator) -> None:
    """Prove child exit status, not a PASS-looking stdout, controls admission."""
    original_run = validator.subprocess.run

    def check_case(code: int, stdout: str, stderr: str) -> None:
        calls = []

        def controlled_run(argv, **kwargs):
            calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, code, stdout, stderr)

        validator.subprocess.run = controlled_run
        try:
            label = "controlled typed child"
            if code == 0:
                require(validator.run_validator(VALIDATOR, label) is None,
                        "typed child success result drift")
            else:
                try:
                    validator.run_validator(VALIDATOR, label)
                except validator.Fail as exc:
                    expected = f"{label} failed:\n{stdout[-3000:]}{stderr[-3000:]}"
                    require(str(exc) == expected,
                            "typed child nonzero exit diagnostic drift")
                else:
                    raise Fail("typed child nonzero exit was accepted")
            require(len(calls) == 1, "typed child subprocess invocation count drift")
            argv, kwargs = calls[0]
            require(argv == [validator.sys.executable, str(VALIDATOR)],
                    "typed child executable/argument binding drift")
            require(kwargs == {
                "cwd": ROOT, "text": True, "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE, "check": False,
            }, "typed child subprocess capture or execution mode drift")
        finally:
            validator.subprocess.run = original_run

    check_case(0, "canonical child PASS\n", "")
    check_case(7, "canonical child PASS\n", "controlled failure\n")
    check_case(-9, "", "controlled signal termination\n")
    print("PASS boundary: typed child nonzero/signal exits reject even with PASS stdout")

def main() -> int:
    require(VALIDATOR.is_file() and not VALIDATOR.is_symlink(), "canonical typed validator missing or symlinked")
    prove_typed_admission_cli_dispatch()
    prove_typed_admission_main_binding()
    prove_validator_runner_binding()
    validator = load_validator()
    exercise_validator_child_exit_propagation(validator)

    original_subprocess_run = validator.subprocess.run
    original_spec_from_file_location = validator.importlib.util.spec_from_file_location
    original_module_from_spec = validator.importlib.util.module_from_spec
    original_guard = validator.enforce_execution_transport

    try:
        validator.subprocess.run = lambda *args, **kwargs: None
        expect_rejected("typed subprocess transport substitution", validator.main, validator.Fail)
    finally:
        validator.subprocess.run = original_subprocess_run

    try:
        validator.importlib.util.spec_from_file_location = lambda *args, **kwargs: None
        expect_rejected("typed import spec transport substitution", validator.main, validator.Fail)
    finally:
        validator.importlib.util.spec_from_file_location = original_spec_from_file_location

    try:
        validator.importlib.util.module_from_spec = lambda *args, **kwargs: None
        expect_rejected("typed module loader transport substitution", validator.main, validator.Fail)
    finally:
        validator.importlib.util.module_from_spec = original_module_from_spec

    try:
        validator.enforce_execution_transport = lambda: None
        expect_rejected("typed execution guard substitution", validator.main, validator.Fail)
    finally:
        validator.enforce_execution_transport = original_guard

    exercise_registry_transaction_transport()
    exercise_reconciler_transaction_transport()

    print("Typed non-resurrection execution/registry/reconcile transport negative suite PASS")
    print("subprocess/import loader/guard substitution accepted: false")
    print("registry mode preserved across atomic replacement: true")
    print("replace rejection mutates canonical bytes or mode: false")
    print("post-write validation failure restores exact bytes and mode: true")
    print("typed partial 4-authority reconcile transaction accepted: false")
    print("typed reconcile rollback preserves exact bytes+mode and no temp residue: true")
    print("registry temp residue remains: false")
    print("typed evidence created: false")
    print("production evidence: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"TYPED TRANSPORT NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
