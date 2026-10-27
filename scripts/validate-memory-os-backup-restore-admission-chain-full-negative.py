#!/usr/bin/env python3
"""Negative proof for the canonical OPS-P0-007 admission-chain full runner.

This test mutates only the imported in-memory runner or an isolated temporary
fixture. It never changes repository files or creates operational evidence.
"""

from __future__ import annotations

import ast
import copy
import importlib.util
import io
import subprocess
from contextlib import redirect_stdout
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts/validate-memory-os-backup-restore-admission-chain-full.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_target():
    spec = importlib.util.spec_from_file_location("admission_chain_full_negative_target", TARGET)
    if spec is None or spec.loader is None:
        raise Fail("cannot load canonical admission-chain full runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_fixture_target(path: Path):
    spec = importlib.util.spec_from_file_location("admission_chain_full_negative_fixture_target", path)
    if spec is None or spec.loader is None:
        raise Fail("cannot load isolated admission-chain full runner fixture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_fail(label: str, mutation, invoke, expected: str) -> None:
    module = load_target()
    original_subprocess_run = module.subprocess.run
    original_sys_executable = module.sys.executable
    try:
        mutation(module)
        try:
            invoke(module)
        except module.Fail as exc:
            if expected not in str(exc):
                raise Fail(f"{label}: wrong fail-closed diagnostic: {exc}") from exc
            print(f"PASS negative: {label}")
            return
        raise Fail(f"{label}: weakened runner was accepted")
    finally:
        # subprocess and sys are shared imported modules; never leak transport or
        # interpreter mutations into a later case or its freshly imported target.
        module.subprocess.run = original_subprocess_run
        module.sys.executable = original_sys_executable


def expect_symlink_fail(label: str, target: str, expected: str) -> None:
    module = load_target()
    with tempfile.TemporaryDirectory(prefix="admission-chain-symlink-") as tmp:
        fixture_root = Path(tmp)
        scripts = fixture_root / "scripts"
        scripts.mkdir()
        real = scripts / "real-validator.py"
        real.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        linked = scripts / "validator.py"
        try:
            linked.symlink_to(target)
        except (NotImplementedError, OSError) as exc:
            raise Fail(f"{label}: script symlink fixture unavailable: {exc}") from exc
        module.ROOT = fixture_root
        try:
            module.canonical_script("scripts/validator.py")
        except module.Fail as exc:
            if expected not in str(exc):
                raise Fail(f"{label}: wrong fail-closed diagnostic: {exc}") from exc
            print(f"PASS negative: {label}")
            return
        raise Fail(f"{label}: symlinked validator was accepted")


def expect_self_symlink_fail(label: str, target: str, expected: str) -> None:
    with tempfile.TemporaryDirectory(prefix="admission-chain-self-symlink-") as tmp:
        fixture_root = Path(tmp)
        scripts = fixture_root / "scripts"
        scripts.mkdir()
        real = scripts / "runner-real.py"
        real.write_text(TARGET.read_text(encoding="utf-8"), encoding="utf-8")
        canonical = scripts / "validate-memory-os-backup-restore-admission-chain-full.py"

        # Never derive an unowned sibling path and overwrite/unlink it.
        # NamedTemporaryFile creates the external fixture with exclusive ownership.
        outside: Path | None = None
        outside_identity: tuple[int, int] | None = None
        if target == "../outside-runner.py":
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", dir=fixture_root.parent,
                    prefix=f"{fixture_root.name}-outside-", suffix=".py", delete=False,
                ) as owned:
                    owned.write("#!/usr/bin/env python3\n")
                    outside = Path(owned.name)
                outside_stat = outside.stat()
                outside_identity = (outside_stat.st_dev, outside_stat.st_ino)
            except OSError as exc:
                raise Fail(f"{label}: external self symlink fixture unavailable: {exc}") from exc
            link_target = f"../../{outside.name}"
        else:
            link_target = target

        try:
            try:
                canonical.symlink_to(link_target)
            except (NotImplementedError, OSError) as exc:
                raise Fail(f"{label}: self symlink fixture unavailable: {exc}") from exc
            module = load_fixture_target(real)
            try:
                module.enforce_runtime_authority()
            except module.Fail as exc:
                if expected not in str(exc):
                    raise Fail(f"{label}: wrong fail-closed diagnostic: {exc}") from exc
                print(f"PASS negative: {label}")
                return
            raise Fail(f"{label}: symlinked runner identity was accepted")
        finally:
            if outside is not None:
                require(outside_identity is not None, "external self symlink fixture identity missing")
                require(outside.is_file() and not outside.is_symlink(),
                        "external self symlink fixture replaced before cleanup")
                current_stat = outside.stat()
                require((current_stat.st_dev, current_stat.st_ino) == outside_identity,
                        "external self symlink fixture inode drift before cleanup")
                outside.unlink()


def require_full_runner_helper_bindings(tree: ast.Module) -> None:
    """Protect default-captured guard and resolver helpers before run_step/main."""
    signatures = {
        "enforce_execution_transport": (["canonical_subprocess_run",
                                          "canonical_python_executable"], 2),
        "enforce_runtime_authority": (["canonical_self_rel", "canonical_steps",
                                       "canonical_transport_guard"], 3),
        "canonical_script": (["relative"], 0),
    }

    for symbol, (names, default_count) in signatures.items():
        definitions = [node for node in tree.body
                       if isinstance(node, ast.FunctionDef) and node.name == symbol]
        require(len(definitions) == 1,
                f"full-chain helper {symbol} must have one synchronous definition")
        definition = definitions[0]
        args = definition.args
        require(not definition.decorator_list and not args.posonlyargs
                and [arg.arg for arg in args.args] == names
                and len(args.defaults) == default_count and not args.vararg
                and not args.kwonlyargs and not args.kwarg and not args.kw_defaults,
                f"full-chain helper {symbol} signature/decorator drift")

        def rebinds(node: ast.AST) -> bool:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name == symbol:
                    return True
            if isinstance(node, ast.arg) and node.arg == symbol:
                return True
            if isinstance(node, ast.alias) and (node.asname or node.name.split(".")[0]) == symbol:
                return True
            if isinstance(node, ast.Name) and node.id == symbol and isinstance(node.ctx, (ast.Store, ast.Del)):
                return True
            if (isinstance(node, ast.Subscript)
                    and isinstance(node.ctx, (ast.Store, ast.Del))
                    and isinstance(node.slice, ast.Constant) and node.slice.value == symbol):
                target = node.value
                if (isinstance(target, ast.Call) and isinstance(target.func, ast.Name)
                        and target.func.id in {"globals", "vars", "locals"}
                        and not target.args and not target.keywords):
                    return True
                if isinstance(target, ast.Attribute) and target.attr == "__dict__":
                    return True
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in {"exec", "eval"}:
                    if not node.args or not isinstance(node.args[0], ast.Constant):
                        return True
                    if not isinstance(node.args[0].value, str):
                        return True
                    return symbol in node.args[0].value
                if (isinstance(node.func, ast.Name) and node.func.id in {"setattr", "delattr"}
                        and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant)
                        and node.args[1].value == symbol):
                    return True
                if (isinstance(node.func, ast.Attribute)
                        and node.func.attr in {"update", "pop", "popitem", "clear",
                                               "setdefault", "__setitem__", "__delitem__"}):
                    target = node.func.value
                    namespace = (isinstance(target, ast.Call)
                                 and isinstance(target.func, ast.Name)
                                 and target.func.id in {"globals", "vars", "locals"}
                                 and not target.args and not target.keywords)
                    module_dict = isinstance(target, ast.Attribute) and target.attr == "__dict__"
                    if namespace or module_dict:
                        method = node.func.attr
                        if method in {"clear", "popitem"}:
                            return True
                        if method == "update":
                            if any(keyword.arg is None or keyword.arg == symbol
                                   for keyword in node.keywords):
                                return True
                            for argument in node.args:
                                if not isinstance(argument, ast.Dict):
                                    return True
                                if any(not isinstance(key, ast.Constant) or key.value == symbol
                                       for key in argument.keys):
                                    return True
                            return False
                        if not node.args or not isinstance(node.args[0], ast.Constant):
                            return True
                        return node.args[0].value == symbol
            return any(rebinds(child) for child in ast.iter_child_nodes(node))

        for statement in tree.body:
            if statement is not definition:
                require(not rebinds(statement),
                        f"full-chain helper {symbol} binding drift")


def prove_full_runner_helper_bindings() -> None:
    try:
        canonical = ast.parse(TARGET.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise Fail("full-chain helper binding source unavailable") from exc
    require_full_runner_helper_bindings(canonical)
    symbols = ("enforce_execution_transport", "enforce_runtime_authority",
               "canonical_script")
    cases = (
        ("assignment", lambda name: f"{name} = lambda *args: None"),
        ("import-alias", lambda name: f"from random import randint as {name}"),
        ("dead-branch", lambda name: f"if False: {name} = None"),
        ("globals", lambda name: f"globals()['{name}'] = None"),
        ("globals-update", lambda name: f"globals().update({name}=None)"),
        ("module-dict", lambda name: f"sys.modules[__name__].__dict__['{name}'] = None"),
        ("setattr", lambda name: f"setattr(sys.modules[__name__], '{name}', None)"),
        ("exec", lambda name: f"exec('{name} = None')"),
        ("duplicate", lambda name: f"def {name}(): pass"),
    )
    for symbol in symbols:
        for label, source in cases:
            mutated = copy.deepcopy(canonical)
            definition_index = next(i for i, node in enumerate(mutated.body)
                                    if isinstance(node, ast.FunctionDef) and node.name == symbol)
            mutated.body[definition_index + 1:definition_index + 1] = ast.parse(source(symbol)).body
            try:
                require_full_runner_helper_bindings(mutated)
            except Fail as exc:
                expected = (f"full-chain helper {symbol} must have one synchronous definition"
                            if label == "duplicate" else
                            f"full-chain helper {symbol} binding drift")
                require(str(exc) == expected,
                        f"full-chain helper {symbol}/{label} diagnostic drift")
            else:
                raise Fail(f"full-chain helper {symbol}/{label} rebinding unexpectedly accepted")
        decorated = copy.deepcopy(canonical)
        definition = next(node for node in decorated.body
                          if isinstance(node, ast.FunctionDef) and node.name == symbol)
        definition.decorator_list.append(ast.Name(id="wrapper", ctx=ast.Load()))
        try:
            require_full_runner_helper_bindings(decorated)
        except Fail as exc:
            require(str(exc) == f"full-chain helper {symbol} signature/decorator drift",
                    f"full-chain helper {symbol} decorator diagnostic drift")
        else:
            raise Fail(f"full-chain helper {symbol} decorator unexpectedly accepted")
    print("PASS reject: thirty full-chain guard/resolver helper binding substitutions")


def require_full_runner_main_reachability(tree: ast.Module) -> None:
    """Require live, ordered identity guards and the canonical validation loop."""
    require_full_runner_main_binding(tree)
    main = next(node for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name == "main")
    body = main.body
    require(len(body) >= 4, "full-chain main direct authority sequence missing")

    def identity_guard(node: ast.AST, left: str, right: str) -> bool:
        if not isinstance(node, ast.If) or node.orelse or len(node.body) != 1:
            return False
        test = node.test
        if not (isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Name) and test.left.id == left
                and len(test.ops) == 1 and isinstance(test.ops[0], ast.IsNot)
                and len(test.comparators) == 1
                and isinstance(test.comparators[0], ast.Name)
                and test.comparators[0].id == right):
            return False
        rejection = node.body[0]
        return (isinstance(rejection, ast.Raise)
                and isinstance(rejection.exc, ast.Call)
                and isinstance(rejection.exc.func, ast.Name)
                and rejection.exc.func.id == "Fail"
                and len(rejection.exc.args) == 1
                and isinstance(rejection.exc.args[0], ast.Constant)
                and isinstance(rejection.exc.args[0].value, str))

    def direct_call(node: ast.AST, name: str, arguments: tuple[str, ...]) -> bool:
        return (isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == name
                and not node.value.keywords
                and len(node.value.args) == len(arguments)
                and all(isinstance(arg, ast.Name) and arg.id == expected
                        for arg, expected in zip(node.value.args, arguments)))

    require(identity_guard(body[0], "enforce_runtime_authority",
                           "canonical_authority_guard"),
            "full-chain main must reject authority identity drift first")
    require(direct_call(body[1], "enforce_runtime_authority", ()),
            "full-chain main must execute direct runtime authority guard second")
    require(identity_guard(body[2], "run_step", "canonical_run_step"),
            "full-chain main must reject step identity drift before execution")
    loop = body[3]
    require(isinstance(loop, ast.For) and not loop.orelse
            and isinstance(loop.target, ast.Tuple)
            and [node.id for node in loop.target.elts if isinstance(node, ast.Name)]
            == ["relative", "label"]
            and len(loop.target.elts) == 2
            and isinstance(loop.iter, ast.Name) and loop.iter.id == "STEPS"
            and len(loop.body) == 1
            and direct_call(loop.body[0], "run_step", ("relative", "label")),
            "full-chain main must directly execute every canonical step")


def prove_full_runner_main_reachability() -> None:
    try:
        canonical = ast.parse(TARGET.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise Fail("full-chain main reachability source unavailable") from exc
    require_full_runner_main_reachability(canonical)
    cases = (
        ("authority-removed", "full-chain main must reject authority identity drift first"),
        ("authority-inverted", "full-chain main must reject authority identity drift first"),
        ("authority-dead", "full-chain main must reject authority identity drift first"),
        ("authority-swallowed", "full-chain main must reject authority identity drift first"),
        ("guard-removed", "full-chain main must execute direct runtime authority guard second"),
        ("guard-dead", "full-chain main must execute direct runtime authority guard second"),
        ("step-identity-removed", "full-chain main must reject step identity drift before execution"),
        ("step-identity-inverted", "full-chain main must reject step identity drift before execution"),
        ("loop-removed", "full-chain main must directly execute every canonical step"),
        ("loop-empty", "full-chain main must directly execute every canonical step"),
        ("loop-swapped", "full-chain main must directly execute every canonical step"),
        ("loop-dead", "full-chain main must directly execute every canonical step"),
        ("loop-noop", "full-chain main must directly execute every canonical step"),
        ("loop-wrapped", "full-chain main must directly execute every canonical step"),
        ("early-return", "full-chain main must reject authority identity drift first"),
    )
    for label, expected in cases:
        mutated = copy.deepcopy(canonical)
        main = next(node for node in mutated.body
                    if isinstance(node, ast.FunctionDef) and node.name == "main")
        body = main.body
        if label == "authority-removed":
            body[0] = ast.Pass()
        elif label == "authority-inverted":
            body[0].test.ops = [ast.Is()]
        elif label == "authority-dead":
            body[0].test = ast.Constant(value=False)
        elif label == "authority-swallowed":
            body[0].body = [ast.Pass()]
        elif label == "guard-removed":
            body[1] = ast.Pass()
        elif label == "guard-dead":
            body[1] = ast.If(test=ast.Constant(value=False), body=[body[1]], orelse=[])
        elif label == "step-identity-removed":
            body[2] = ast.Pass()
        elif label == "step-identity-inverted":
            body[2].test.ops = [ast.Is()]
        elif label == "loop-removed":
            body[3] = ast.Pass()
        elif label == "loop-empty":
            body[3].iter = ast.Tuple(elts=[], ctx=ast.Load())
        elif label == "loop-swapped":
            body[3].body[0].value.args.reverse()
        elif label == "loop-dead":
            body[3] = ast.If(test=ast.Constant(value=False), body=[body[3]], orelse=[])
        elif label == "loop-noop":
            body[3].body = [ast.Pass()]
        elif label == "loop-wrapped":
            body[3] = ast.Try(body=[body[3]], handlers=[], orelse=[],
                              finalbody=[ast.Pass()])
        elif label == "early-return":
            body.insert(0, ast.Return(value=ast.Constant(value=0)))
        try:
            require_full_runner_main_reachability(mutated)
        except Fail as exc:
            require(str(exc) == expected,
                    f"full-chain main {label} reachability diagnostic drift")
        else:
            raise Fail(f"full-chain main {label} guard bypass unexpectedly accepted")
    print("PASS reject: fifteen full-chain main guard/step reachability substitutions")


def require_no_full_runner_pre_dispatch_exit(tree: ast.Module) -> None:
    """Reject eager module termination before the canonical CLI entrypoint."""
    require_full_runner_cli_dispatch(tree)

    def terminates_during_import(node: ast.AST) -> bool:
        # Deferred function bodies are not executed during module initialization.
        # Their decorators and default expressions are executed eagerly.
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            eager = [*node.decorator_list, *node.args.defaults,
                     *(value for value in node.args.kw_defaults if value is not None)]
            return any(terminates_during_import(value) for value in eager)
        if isinstance(node, ast.Lambda):
            eager = [*node.args.defaults,
                     *(value for value in node.args.kw_defaults if value is not None)]
            return any(terminates_during_import(value) for value in eager)
        # Class bases, decorators and bodies execute during definition.
        if isinstance(node, ast.ClassDef):
            eager = [*node.decorator_list, *node.bases,
                     *(keyword.value for keyword in node.keywords), *node.body]
            return any(terminates_during_import(value) for value in eager)
        if isinstance(node, ast.Raise):
            return True
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {
                "exit", "quit", "exec", "eval"
            }:
                return True
            if (isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and (node.func.value.id, node.func.attr) in {
                        ("sys", "exit"), ("os", "_exit")
                    }):
                return True
        return any(terminates_during_import(child) for child in ast.iter_child_nodes(node))

    require(not any(terminates_during_import(node) for node in tree.body[:-1]),
            "full-chain module can terminate before CLI dispatch")



def parse_checked_negative_fixture(source: str) -> list[ast.stmt]:
    """Do not let a malformed synthetic fixture masquerade as guard rejection."""
    require(chr(92) + "n" not in source,
            "full-chain negative fixture contains double-escaped newline")
    try:
        return ast.parse(source).body
    except SyntaxError as exc:
        raise Fail("full-chain negative fixture is invalid Python") from exc


def prove_negative_fixture_syntax() -> None:
    parse_checked_negative_fixture("if True:" + chr(10) + "    pass")
    for label, source, expected in (
        ("double-escaped", "if True:" + chr(92) + "n    pass",
         "full-chain negative fixture contains double-escaped newline"),
        ("malformed", "if True:",
         "full-chain negative fixture is invalid Python"),
    ):
        try:
            parse_checked_negative_fixture(source)
        except Fail as exc:
            require(str(exc) == expected,
                    f"full-chain {label} fixture diagnostic drift")
        else:
            raise Fail(f"full-chain {label} fixture unexpectedly accepted")
    print("PASS reject: two malformed full-chain negative fixture syntax controls")


def prove_full_runner_pre_dispatch_exit() -> None:
    try:
        canonical = ast.parse(TARGET.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise Fail("full-chain pre-dispatch source unavailable") from exc
    require_no_full_runner_pre_dispatch_exit(canonical)
    mutations = (
        ("raise", "raise SystemExit(0)"),
        ("sys-exit", "sys.exit(0)"),
        ("os-exit", "os._exit(0)"),
        ("exit", "exit(0)"),
        ("quit", "quit()"),
        ("branch", "if True:\n    raise SystemExit(0)"),
        ("try", "try:\n    sys.exit(0)\nexcept Exception:\n    pass"),
        ("exec", "exec('raise SystemExit(0)')"),
        ("eval", "eval('exit(0)')"),
        ("class-exit", "class Early:\n    sys.exit(0)"),
        ("class-raise", "class Early:\n    raise SystemExit(0)"),
        ("decorator-exit", "@exit(0)\ndef helper():\n    pass"),
        ("default-exit", "def helper(value=exit(0)):\n    pass"),
        ("class-base-exit", "class Early(exit(0)):\n    pass"),
        ("lambda-default-exit", "helper = lambda value=exit(0): value"),
    )
    for label, source in mutations:
        mutated = copy.deepcopy(canonical)
        mutated.body[-1:-1] = parse_checked_negative_fixture(source)
        try:
            require_no_full_runner_pre_dispatch_exit(mutated)
        except Fail as exc:
            require(str(exc) == "full-chain module can terminate before CLI dispatch",
                    f"full-chain pre-dispatch {label} rejection diagnostic drift")
        else:
            raise Fail(f"full-chain pre-dispatch {label} termination unexpectedly accepted")
    print("PASS reject: fifteen full-chain pre-dispatch eager termination substitutions")


def require_full_runner_cli_dispatch(tree: ast.Module) -> None:
    """Prove the actual script entrypoint calls main and propagates Fail."""
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
            "full-chain CLI dispatch guard missing or duplicated")
    guard = guards[0]
    require(not guard.orelse and len(guard.body) == 1
            and isinstance(guard.body[0], ast.Try),
            "full-chain CLI dispatch must be direct try")
    dispatch = guard.body[0]
    require(len(dispatch.body) == 1 and isinstance(dispatch.body[0], ast.Raise),
            "full-chain CLI dispatch must raise main exit status")
    raised = dispatch.body[0].exc
    require(isinstance(raised, ast.Call) and isinstance(raised.func, ast.Name)
            and raised.func.id == "SystemExit" and len(raised.args) == 1
            and not raised.keywords
            and isinstance(raised.args[0], ast.Call)
            and isinstance(raised.args[0].func, ast.Name)
            and raised.args[0].func.id == "main"
            and not raised.args[0].args and not raised.args[0].keywords,
            "full-chain CLI dispatch must call guarded main")
    require(not dispatch.orelse and not dispatch.finalbody
            and len(dispatch.handlers) == 1
            and isinstance(dispatch.handlers[0].type, ast.Name)
            and dispatch.handlers[0].type.id == "Fail",
            "full-chain CLI dispatch must catch only Fail")
    handler = dispatch.handlers[0]
    require(bool(handler.body) and isinstance(handler.body[-1], ast.Raise)
            and isinstance(handler.body[-1].exc, ast.Call)
            and isinstance(handler.body[-1].exc.func, ast.Name)
            and handler.body[-1].exc.func.id == "SystemExit"
            and len(handler.body[-1].exc.args) == 1
            and isinstance(handler.body[-1].exc.args[0], ast.Constant)
            and type(handler.body[-1].exc.args[0].value) is int
            and handler.body[-1].exc.args[0].value != 0,
            "full-chain CLI Fail handler must exit nonzero")


def prove_full_runner_cli_dispatch() -> None:
    try:
        canonical = ast.parse(TARGET.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise Fail("full-chain CLI dispatch source unavailable") from exc
    require_full_runner_cli_dispatch(canonical)
    cases = (
        ("guard-removed", "full-chain CLI dispatch guard missing or duplicated"),
        ("guard-duplicate", "full-chain CLI dispatch guard missing or duplicated"),
        ("guard-not-last", "full-chain CLI dispatch guard missing or duplicated"),
        ("guard-else", "full-chain CLI dispatch must be direct try"),
        ("dispatch-call-only", "full-chain CLI dispatch must raise main exit status"),
        ("dispatch-dead", "full-chain CLI dispatch must raise main exit status"),
        ("dispatch-zero", "full-chain CLI dispatch must call guarded main"),
        ("dispatch-argument", "full-chain CLI dispatch must call guarded main"),
        ("handler-type", "full-chain CLI dispatch must catch only Fail"),
        ("handler-extra", "full-chain CLI dispatch must catch only Fail"),
        ("handler-finally", "full-chain CLI dispatch must catch only Fail"),
        ("handler-swallow", "full-chain CLI Fail handler must exit nonzero"),
        ("handler-zero", "full-chain CLI Fail handler must exit nonzero"),
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
            require_full_runner_cli_dispatch(mutated)
        except Fail as exc:
            require(str(exc) == expected,
                    f"full-chain CLI {label} rejection diagnostic drift")
        else:
            raise Fail(f"full-chain CLI {label} bypass unexpectedly accepted")
    print("PASS reject: thirteen full-chain CLI dispatch/failure-exit substitutions")


def require_full_runner_main_binding(tree: ast.Module) -> None:
    """Bind the CLI entrypoint before its runtime identity defaults are captured."""
    definitions = [node for node in tree.body
                   if isinstance(node, ast.FunctionDef) and node.name == "main"]
    require(len(definitions) == 1,
            "full-chain runner must define exactly one synchronous main")
    definition = definitions[0]
    args = definition.args
    require(not definition.decorator_list and not args.posonlyargs
            and [arg.arg for arg in args.args] ==
            ["canonical_authority_guard", "canonical_run_step"]
            and len(args.defaults) == 2 and not args.vararg
            and not args.kwonlyargs and not args.kwarg and not args.kw_defaults,
            "full-chain runner main signature/decorator drift")

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
            require(not rebinds(statement), "full-chain runner main binding drift")


def prove_full_runner_main_binding() -> None:
    try:
        canonical = ast.parse(TARGET.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise Fail("full-chain runner main source unavailable") from exc
    require_full_runner_main_binding(canonical)
    cases = (
        ("assignment", "main = lambda: 0"),
        ("tuple", "main, unused = (lambda: 0), None"),
        ("import-alias", "from random import randint as main"),
        ("dead-branch", "if False: main = None"),
        ("globals", "globals()['main'] = None"),
        ("globals-update", "globals().update(main=None)"),
        ("globals-pop", "globals().pop('main')"),
        ("module-dict", "sys.modules[__name__].__dict__['main'] = None"),
        ("setattr", "setattr(sys.modules[__name__], 'main', None)"),
        ("exec", "exec('main = None')"),
        ("class", "class main: pass"),
        ("duplicate", "def main(): pass"),
        ("async", "async def main(): pass"),
    )
    for label, mutation in cases:
        mutated = copy.deepcopy(canonical)
        main_index = next(i for i, node in enumerate(mutated.body)
                          if isinstance(node, ast.FunctionDef) and node.name == "main")
        mutated.body[main_index:main_index] = ast.parse(mutation).body
        try:
            require_full_runner_main_binding(mutated)
        except Fail as exc:
            expected = ("full-chain runner must define exactly one synchronous main"
                        if label == "duplicate" else "full-chain runner main binding drift")
            require(str(exc) == expected,
                    f"full-chain main {label} rejection diagnostic drift")
        else:
            raise Fail(f"full-chain main {label} pre-dispatch replacement unexpectedly accepted")
    decorated = copy.deepcopy(canonical)
    main = next(node for node in decorated.body
                if isinstance(node, ast.FunctionDef) and node.name == "main")
    main.decorator_list.append(ast.Name(id="wrapper", ctx=ast.Load()))
    try:
        require_full_runner_main_binding(decorated)
    except Fail as exc:
        require(str(exc) == "full-chain runner main signature/decorator drift",
                "full-chain main decorator rejection diagnostic drift")
    else:
        raise Fail("full-chain main decorator unexpectedly accepted")
    print("PASS reject: fourteen full-chain main rebinding/decorator substitutions")


def require_full_runner_step_binding(tree: ast.Module) -> None:
    """Reject rebinding the step function before main captures its default."""
    definitions = [node for node in tree.body
                   if isinstance(node, ast.FunctionDef) and node.name == "run_step"]
    require(len(definitions) == 1,
            "full-chain runner must define exactly one synchronous step")
    definition = definitions[0]
    args = definition.args
    require(not definition.decorator_list and not args.posonlyargs
            and [arg.arg for arg in args.args] ==
            ["relative", "label", "canonical_transport_guard", "canonical_script_resolver"]
            and len(args.defaults) == 2 and not args.vararg
            and not args.kwonlyargs and not args.kwarg and not args.kw_defaults,
            "full-chain runner step signature/decorator drift")

    def rebinds(node: ast.AST) -> bool:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == "run_step":
                return True
        if isinstance(node, ast.arg) and node.arg == "run_step":
            return True
        if isinstance(node, ast.alias) and (node.asname or node.name.split(".")[0]) == "run_step":
            return True
        if isinstance(node, ast.Name) and node.id == "run_step" and isinstance(node.ctx, (ast.Store, ast.Del)):
            return True
        if (isinstance(node, ast.Subscript)
                and isinstance(node.ctx, (ast.Store, ast.Del))
                and isinstance(node.slice, ast.Constant)
                and node.slice.value == "run_step"):
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
                    and node.args[1].value == "run_step"):
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
            require(not rebinds(statement), "full-chain runner step binding drift")


def prove_full_runner_step_binding() -> None:
    try:
        canonical = ast.parse(TARGET.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise Fail("full-chain runner step source unavailable") from exc
    require_full_runner_step_binding(canonical)
    cases = (
        ("assignment", "run_step = lambda *args: None"),
        ("import-alias", "from random import randint as run_step"),
        ("dead-branch", "if False: run_step = None"),
        ("globals", "globals()['run_step'] = None"),
        ("globals-update", "globals().update(run_step=None)"),
        ("globals-pop", "globals().pop('run_step')"),
        ("module-dict", "sys.modules[__name__].__dict__['run_step'] = None"),
        ("setattr", "setattr(sys.modules[__name__], 'run_step', None)"),
        ("exec", "exec('run_step = None')"),
        ("duplicate", "def run_step(relative, label): pass"),
    )
    for label, mutation in cases:
        mutated = copy.deepcopy(canonical)
        main_index = next(i for i, node in enumerate(mutated.body)
                          if isinstance(node, ast.FunctionDef) and node.name == "main")
        mutated.body[main_index:main_index] = ast.parse(mutation).body
        try:
            require_full_runner_step_binding(mutated)
        except Fail as exc:
            expected = ("full-chain runner must define exactly one synchronous step"
                        if label == "duplicate" else "full-chain runner step binding drift")
            require(str(exc) == expected, f"full-chain step {label} rejection diagnostic drift")
        else:
            raise Fail(f"full-chain step {label} pre-main rebinding unexpectedly accepted")
    decorated = copy.deepcopy(canonical)
    step = next(node for node in decorated.body
                if isinstance(node, ast.FunctionDef) and node.name == "run_step")
    step.decorator_list.append(ast.Name(id="wrapper", ctx=ast.Load()))
    try:
        require_full_runner_step_binding(decorated)
    except Fail as exc:
        require(str(exc) == "full-chain runner step signature/decorator drift",
                "full-chain step decorator rejection diagnostic drift")
    else:
        raise Fail("full-chain step decorator bypass unexpectedly accepted")
    print("PASS reject: eleven full-chain pre-main step rebinding/decorator substitutions")


def prove_full_step_exit_propagation() -> None:
    """Prove the full-chain parent cannot promote a failed child with PASS stdout."""
    module = load_target()
    original_run = module.subprocess.run
    original_guard = module.enforce_execution_transport
    relative = "scripts/validate-memory-os-backup-restore-admission-chain-full.py"
    label = "controlled full-chain child"

    def fixture_transport_guard() -> None:
        # Only this isolated in-memory test replaces the transport guard.
        pass

    module.enforce_execution_transport = fixture_transport_guard
    try:
        marker = "synthetic-secret-full-chain-child"
        for code, child_stdout, child_stderr in (
            (0, marker, ""),
            (7, f"child PASS-looking output {marker}", marker),
            (-9, "", marker),
            (False, marker, marker),
        ):
            calls = []

            def controlled_run(argv, **kwargs):
                calls.append((argv, kwargs))
                return subprocess.CompletedProcess(argv, code, child_stdout, child_stderr)

            module.subprocess.run = controlled_run
            output = io.StringIO()
            success = type(code) is int and code == 0
            with redirect_stdout(output):
                try:
                    module.run_step(relative, label,
                                    canonical_transport_guard=fixture_transport_guard)
                except module.Fail as exc:
                    require(not success, "full-chain successful child was rejected")
                    require(str(exc) == f"{label} failed (raw child output withheld): {relative}",
                            "full-chain child fixed failure class drift")
                    require(marker not in str(exc), "full-chain private child output leaked")
                else:
                    require(success, "full-chain nonzero/boolean child status accepted")
            require(len(calls) == 1, "full-chain child subprocess invocation count drift")
            argv, kwargs = calls[0]
            require(argv == [module.sys.executable, str(ROOT / relative)],
                    "full-chain child interpreter/path binding drift")
            require(kwargs == {
                "cwd": ROOT, "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL, "check": False, "timeout": 120,
            }, "full-chain child private subprocess or execution budget drift")
            parent_pass = f"PASS chain step: {label}"
            require((parent_pass in output.getvalue()) is success,
                    "full-chain child parent PASS output contradicts exit status")
            require(marker not in output.getvalue(), "full-chain child output leaked to parent")

        for failure in (OSError(marker), subprocess.TimeoutExpired(["synthetic"], 120)):
            def raise_failure(*_args, **_kwargs):
                raise failure
            module.subprocess.run = raise_failure
            try:
                module.run_step(relative, label, canonical_transport_guard=fixture_transport_guard)
            except module.Fail as exc:
                require(str(exc) == f"{label} unavailable or timed out (raw child output withheld): {relative}",
                        "full-chain unavailable/timeout failure class drift")
                require(marker not in str(exc), "full-chain private exception leaked")
            else:
                raise Fail("full-chain unavailable/timeout child accepted")
    finally:
        module.subprocess.run = original_run
        module.enforce_execution_transport = original_guard
    print("PASS boundary: full-chain child nonzero/signal exits cannot become parent PASS")


def main() -> int:
    prove_full_runner_helper_bindings()
    prove_full_runner_main_reachability()
    prove_negative_fixture_syntax()
    prove_full_runner_pre_dispatch_exit()
    prove_full_runner_cli_dispatch()
    prove_full_runner_main_binding()
    prove_full_runner_step_binding()
    prove_full_step_exit_propagation()
    expect_fail(
        "repository root substitution",
        lambda m: setattr(m, "ROOT", ROOT / "scripts"),
        lambda m: m.enforce_runtime_authority(),
        "repository root drift",
    )
    expect_fail(
        "self path substitution",
        lambda m: setattr(m, "SELF_REL", Path("scripts/validate-memory-os-backup-restore-admission-chain.py")),
        lambda m: m.enforce_runtime_authority(),
        "self path drift",
    )
    expect_self_symlink_fail("self symlink substitution", "runner-real.py", "identity drift")
    expect_self_symlink_fail("broken self symlink", "missing-runner.py", "missing or escapes repository")
    expect_self_symlink_fail("escaping self symlink", "../outside-runner.py", "missing or escapes repository")
    expect_fail(
        "script repository escape",
        lambda m: None,
        lambda m: m.canonical_script("../outside-validator.py"),
        "validation authority missing or escapes repository",
    )
    expect_fail(
        "script lexical alias",
        lambda m: None,
        lambda m: m.canonical_script("scripts/../scripts/validate-memory-os-backup-restore-admission-chain-full.py"),
        "validation authority drift",
    )
    expect_symlink_fail("script symlink substitution", "real-validator.py", "validation authority drift")
    expect_symlink_fail("broken script symlink", "missing-validator.py", "validation authority missing or escapes repository")
    expect_symlink_fail("escaping script symlink", "../../outside-validator.py", "validation authority missing or escapes repository")
    expect_fail(
        "validation sequence removal",
        lambda m: setattr(m, "STEPS", m.STEPS[:-1]),
        lambda m: m.enforce_runtime_authority(),
        "validation sequence drift",
    )
    expect_fail(
        "subprocess transport substitution",
        lambda m: setattr(m.subprocess, "run", lambda *args, **kwargs: None),
        lambda m: m.enforce_execution_transport(),
        "subprocess transport drift",
    )
    expect_fail(
        "Python executable substitution",
        lambda m: setattr(m.sys, "executable", str(ROOT)),
        lambda m: m.enforce_execution_transport(),
        "Python executable drift",
    )
    expect_fail(
        "transport guard substitution",
        lambda m: setattr(m, "enforce_execution_transport", lambda: None),
        lambda m: m.enforce_runtime_authority(),
        "transport guard drift",
    )
    expect_fail(
        "script resolver substitution",
        lambda m: setattr(m, "canonical_script", lambda relative: ROOT / relative),
        lambda m: m.run_step(m.STEPS[0][0], m.STEPS[0][1]),
        "script resolver drift",
    )
    expect_fail(
        "authority guard substitution",
        lambda m: setattr(m, "enforce_runtime_authority", lambda: None),
        lambda m: m.main(),
        "authority guard drift",
    )
    expect_fail(
        "execution function substitution",
        lambda m: setattr(m, "run_step", lambda *args, **kwargs: None),
        lambda m: m.main(),
        "execution function drift",
    )
    print("Admission-chain full runner negative validation PASS")
    print("repository mutation: false")
    print("production evidence created: false")
    print("production traffic changed: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ADMISSION CHAIN FULL RUNNER NEGATIVE VALIDATION FAILED: {exc}")
        raise SystemExit(1)
