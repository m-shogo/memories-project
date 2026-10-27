#!/usr/bin/env python3
"""Prove the typed non-resurrection writer CLI cannot substitute production authorities."""
from __future__ import annotations

import ast
import importlib.util
import inspect
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
TRANSPORT_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-transport-negative.py"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_writer() -> Any:
    spec = importlib.util.spec_from_file_location("memory_os_typed_non_resurrection_writer_authority", WRITER_PATH)
    require(spec is not None and spec.loader is not None, "cannot load typed non-resurrection writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(writer: Any, field: str, substitute: Path) -> None:
    original = getattr(writer, field)
    try:
        setattr(writer, field, substitute)
        try:
            writer.require_cli_authorities()
        except writer.Fail:
            return
        raise NegativeFailure(f"typed non-resurrection writer accepted {field} CLI authority substitution")
    finally:
        setattr(writer, field, original)


def require_canonical_lock_parent(parent: Path, root: Path = ROOT) -> tuple[int, int]:
    try:
        relative = parent.relative_to(root)
    except ValueError as exc:
        raise NegativeFailure("typed negative lock parent escapes fixture root") from exc
    require(root.is_dir() and not root.is_symlink(),
            "typed negative lock fixture root missing or symlinked")
    cursor = root
    for component in relative.parts:
        cursor = cursor / component
        require(cursor.is_dir() and not cursor.is_symlink(),
                "typed negative lock parent missing or symlinked")
    require(parent.resolve(strict=True) == root.resolve(strict=True) / relative,
            "typed negative lock parent canonical resolution drift")
    parent_stat = parent.stat()
    return parent_stat.st_dev, parent_stat.st_ino


def require_owned_lock_symlink(lock: Path, target: Path, leaf_identity: tuple[int, int],
                               parent_identity: tuple[int, int], root: Path = ROOT) -> None:
    require(require_canonical_lock_parent(lock.parent, root) == parent_identity,
            "typed negative lock parent identity drift")
    require(lock.is_symlink() and lock.resolve() == target.resolve(),
            "typed negative lock symlink target drift")
    leaf_stat = lock.lstat()
    require((leaf_stat.st_dev, leaf_stat.st_ino) == leaf_identity,
            "typed negative lock symlink identity drift")


def prove_materialized_lock_symlink_fails_closed(writer: Any) -> None:
    lock = writer.LOCK
    require(lock == ROOT / "contracts/operations/.backup-restore-non-resurrection-admission.lock",
            "typed non-resurrection canonical lock path drift")
    require(not lock.exists() and not lock.is_symlink(),
            "typed non-resurrection canonical lock must be absent before symlink negative")
    with tempfile.TemporaryDirectory(prefix="memory-os-typed-lock-negative-") as temp_dir:
        target = Path(temp_dir) / "outside.lock"
        target.write_bytes(b"outside-lock-target\n")
        before = target.read_bytes()
        parent_identity = require_canonical_lock_parent(lock.parent)
        lock.symlink_to(target)
        leaf_stat = lock.lstat()
        leaf_identity = (leaf_stat.st_dev, leaf_stat.st_ino)
        try:
            try:
                writer.os.open(lock, writer.os.O_WRONLY | writer.os.O_CREAT | writer.os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                raise NegativeFailure("typed non-resurrection writer lock flags followed a materialized symlink")
            require_owned_lock_symlink(lock, target, leaf_identity, parent_identity)
            require(target.read_bytes() == before,
                    "typed non-resurrection lock symlink rejection mutated external target")
        finally:
            # Never delete a lock path whose parent or symlink inode was replaced.
            require_owned_lock_symlink(lock, target, leaf_identity, parent_identity)
            lock.unlink()

        # A symlinked ancestor must not redirect even a still-vacant lock leaf.
        isolated_root = Path(temp_dir) / "isolated-root"
        isolated_root.mkdir()
        external_parent = Path(temp_dir) / "external-lock-parent"
        external_parent.mkdir()
        alias_parent = isolated_root / "alias"
        alias_parent.symlink_to(external_parent, target_is_directory=True)
        try:
            try:
                require_canonical_lock_parent(alias_parent, isolated_root)
            except NegativeFailure as exc:
                require(str(exc) == "typed negative lock parent missing or symlinked",
                        "typed lock parent-alias diagnostic drift")
                require(alias_parent.is_symlink() and alias_parent.resolve() == external_parent.resolve(),
                        "isolated lock parent alias changed")
                print("PASS reject: typed lock fixture symlinked parent")
            else:
                raise NegativeFailure("typed lock fixture symlinked parent unexpectedly accepted")
        finally:
            alias_parent.unlink()

        # A same-target replacement must not count as ownership of the original inode.
        isolated_link = Path(temp_dir) / "isolated-owned-link"
        isolated_replacement = Path(temp_dir) / "isolated-replacement-link"
        isolated_parent_stat = isolated_link.parent.stat()
        isolated_parent_identity = (isolated_parent_stat.st_dev, isolated_parent_stat.st_ino)
        isolated_link.symlink_to(target)
        original = isolated_link.lstat()
        isolated_replacement.symlink_to(target)
        isolated_replacement.replace(isolated_link)
        try:
            require_owned_lock_symlink(isolated_link, target,
                                      (original.st_dev, original.st_ino), isolated_parent_identity,
                                      root=Path(temp_dir))
        except NegativeFailure as exc:
            require(str(exc) == "typed negative lock symlink identity drift",
                    "typed lock replacement diagnostic drift")
            print("PASS reject: same-target symlink replacement is not fixture ownership")
        else:
            raise NegativeFailure("same-target symlink replacement unexpectedly accepted")
        finally:
            isolated_link.unlink()
    require(not lock.exists() and not lock.is_symlink(),
            "typed non-resurrection lock symlink negative left canonical lock materialized")


def require_direct_first_guard(source: str) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise NegativeFailure("writer main source syntax invalid") from exc
    require(len(tree.body) == 1 and isinstance(tree.body[0], ast.FunctionDef)
            and tree.body[0].name == "main",
            "writer main must be one synchronous definition")
    statements = tree.body[0].body
    require(bool(statements) and isinstance(statements[0], ast.Expr)
            and isinstance(statements[0].value, ast.Call)
            and isinstance(statements[0].value.func, ast.Name)
            and statements[0].value.func.id == "require_cli_authorities"
            and not statements[0].value.args and not statements[0].value.keywords,
            "writer main must begin with direct CLI authority guard")


def require_unique_writer_main_binding(source: str) -> None:
    """Reject module-level replacement of the guarded CLI entrypoint."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise NegativeFailure("writer module source syntax invalid") from exc
    definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                   and node.name == "main"]
    require(len(definitions) == 1, "writer module must define exactly one synchronous main")
    definition = definitions[0]
    args = definition.args
    require(not definition.decorator_list and not args.posonlyargs and not args.args
            and not args.vararg and not args.kwonlyargs and not args.kwarg
            and not args.defaults and not args.kw_defaults,
            "writer module main signature or decorators drift")

    def rebinds_main(node: ast.AST) -> bool:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return node.name == "main"
        if isinstance(node, ast.alias):
            return (node.asname or node.name.split(".")[0]) == "main"
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            return node.id == "main"
        if (isinstance(node, ast.Subscript)
                and isinstance(node.ctx, (ast.Store, ast.Del))
                and isinstance(node.slice, ast.Constant)
                and node.slice.value == "main"):
            target = node.value
            if (isinstance(target, ast.Call)
                    and isinstance(target.func, ast.Name)
                    and target.func.id in {"globals", "vars", "locals"}
                    and not target.args and not target.keywords):
                return True
            if isinstance(target, ast.Attribute) and target.attr == "__dict__":
                return True
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"update", "pop", "popitem", "clear",
                                       "setdefault", "__setitem__", "__delitem__"}):
            target = node.func.value
            if (isinstance(target, ast.Call)
                    and isinstance(target.func, ast.Name)
                    and target.func.id in {"globals", "vars", "locals"}
                    and not target.args and not target.keywords):
                return True
            if isinstance(target, ast.Attribute) and target.attr == "__dict__":
                return True
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "setattr" and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value == "main"):
            return True
        return any(rebinds_main(child) for child in ast.iter_child_nodes(node))

    for statement in tree.body:
        if statement is not definition:
            require(not rebinds_main(statement), "writer module main binding drift")


def prove_main_binding_classifier() -> None:
    positive = "\n".join((
        "def main():",
        "    require_cli_authorities()",
        "if __name__ == '__main__':",
        "    main()",
        "",
    ))
    require_unique_writer_main_binding(positive)
    mutations = (
        ("duplicate", positive + "def main(): pass\n", "writer module must define exactly one synchronous main"),
        ("assignment", positive + "main = lambda: 0\n", "writer module main binding drift"),
        ("tuple", positive + "main, other = (lambda: 0), 1\n", "writer module main binding drift"),
        ("import-alias", positive + "from random import randint as main\n", "writer module main binding drift"),
        ("dead-branch", positive + "if False:\n    main = lambda: 0\n", "writer module main binding drift"),
        ("loop", positive + "for main in ():\n    pass\n", "writer module main binding drift"),
        ("globals", positive + "globals()['main'] = lambda: 0\n", "writer module main binding drift"),
        ("setattr", positive + "setattr(sys.modules[__name__], 'main', lambda: 0)\n", "writer module main binding drift"),
        ("decorator", "@wrapper\n" + positive, "writer module main signature or decorators drift"),
        ("async", positive.replace("def main():", "async def main():", 1),
         "writer module must define exactly one synchronous main"),
        ("globals-update", positive + "globals().update({'main': lambda: 0})\n",
         "writer module main binding drift"),
        ("globals-keyword", positive + "globals().update(main=lambda: 0)\n",
         "writer module main binding drift"),
        ("globals-pop", positive + "globals().pop('main')\n",
         "writer module main binding drift"),
        ("vars-subscript", positive + "vars()['main'] = lambda: 0\n",
         "writer module main binding drift"),
        ("locals-subscript", positive + "locals()['main'] = lambda: 0\n",
         "writer module main binding drift"),
        ("globals-setitem", positive + "globals().__setitem__('main', lambda: 0)\n",
         "writer module main binding drift"),
        ("module-dict", positive + "sys.modules[__name__].__dict__['main'] = lambda: 0\n",
         "writer module main binding drift"),
        ("module-dict-update", positive + "sys.modules[__name__].__dict__.update({'main': lambda: 0})\n",
         "writer module main binding drift"),
        ("dead-dynamic", positive + "if False:\n    globals().update({'main': lambda: 0})\n",
         "writer module main binding drift"),
    )
    for label, mutated, expected in mutations:
        try:
            require_unique_writer_main_binding(mutated)
        except NegativeFailure as exc:
            require(str(exc) == expected, f"writer module {label} diagnostic drift")
        else:
            raise NegativeFailure(f"writer module {label} shadowing unexpectedly accepted")
    print("PASS reject: nineteen module-level writer main binding/decorator/dynamic substitutes")


def require_parser_lock_reachability(source: str) -> None:
    """Bind input parser and exclusive lock to reachable CLI statements, not text."""
    require_direct_first_guard(source)
    definition = ast.parse(source).body[0]
    body = definition.body

    def direct_call(statement: ast.stmt, namespace: str, method: str) -> bool:
        return (isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Call)
                and isinstance(statement.value.func, ast.Name if not namespace else ast.Attribute)
                and ((statement.value.func.id == method) if not namespace else
                     (statement.value.func.attr == method
                      and isinstance(statement.value.func.value, ast.Name)
                      and statement.value.func.value.id == namespace)))

    parser = body[1] if len(body) > 1 else None
    require(isinstance(parser, ast.Assign) and len(parser.targets) == 1
            and isinstance(parser.targets[0], ast.Name) and parser.targets[0].id == "parser"
            and isinstance(parser.value, ast.Call)
            and isinstance(parser.value.func, ast.Attribute)
            and isinstance(parser.value.func.value, ast.Name)
            and parser.value.func.value.id == "argparse"
            and parser.value.func.attr == "ArgumentParser"
            and not parser.value.args and not parser.value.keywords,
            "writer parser must be direct second statement")

    validation = [index for index, statement in enumerate(body)
                  if direct_call(statement, "", "validate_record")
                  and len(statement.value.args) == 1
                  and isinstance(statement.value.args[0], ast.Name)
                  and statement.value.args[0].id == "record"
                  and not statement.value.keywords]
    require(len(validation) == 1, "writer direct record validation missing")

    lock_tries = [(index, statement) for index, statement in enumerate(body)
                  if isinstance(statement, ast.Try) and statement.body
                  and isinstance(statement.body[0], ast.Assign)
                  and len(statement.body[0].targets) == 1
                  and isinstance(statement.body[0].targets[0], ast.Name)
                  and statement.body[0].targets[0].id == "lock_fd"]
    require(len(lock_tries) == 1, "writer exclusive lock must be direct top-level try")
    lock_index, lock_try = lock_tries[0]
    require(validation[0] < lock_index, "writer record validation must precede lock")
    require(not any(isinstance(statement, (ast.Return, ast.Break, ast.Continue, ast.Raise))
                    for statement in body[:lock_index]),
            "writer main cannot exit directly before lock")

    call = lock_try.body[0].value
    expected_flags = ast.parse("os.O_WRONLY | os.O_CREAT | os.O_EXCL", mode="eval").body
    require(isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == "os" and call.func.attr == "open"
            and len(call.args) == 3 and not call.keywords
            and isinstance(call.args[0], ast.Name) and call.args[0].id == "LOCK"
            and ast.dump(call.args[1]) == ast.dump(expected_flags)
            and isinstance(call.args[2], ast.Constant) and call.args[2].value == 0o600,
            "writer lock must use canonical exclusive-create path flags and mode")
    require(any(isinstance(handler.type, ast.Name)
                and handler.type.id == "FileExistsError"
                and any(isinstance(statement, ast.Raise) for statement in handler.body)
                for handler in lock_try.handlers),
            "writer existing lock must fail closed")


def prove_parser_lock_classifier() -> None:
    positive = "\n".join((
        "def main():",
        "    require_cli_authorities()",
        "    parser = argparse.ArgumentParser()",
        "    validate_record(record)",
        "    try:",
        "        lock_fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)",
        "    except FileExistsError:",
        "        raise Fail('locked')",
        "",
    ))
    require_parser_lock_reachability(positive)
    parser_line = "    parser = argparse.ArgumentParser()"
    lock_line = "        lock_fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)"
    mutations = (
        ("parser-comment", positive.replace(parser_line, "    # " + parser_line.strip()),
         "writer parser must be direct second statement"),
        ("parser-string", positive.replace(parser_line, "    'parser = argparse.ArgumentParser()'"),
         "writer parser must be direct second statement"),
        ("parser-dead", positive.replace(parser_line, "    if False:\n" + "    " + parser_line),
         "writer parser must be direct second statement"),
        ("early-return", positive.replace("    validate_record(record)",
                                           "    return 0\n    validate_record(record)"),
         "writer main cannot exit directly before lock"),
        ("lock-missing", positive.replace(lock_line, "        lock_fd = None"),
         "writer lock must use canonical exclusive-create path flags and mode"),
        ("lock-dead", positive.replace("    try:\n" + lock_line,
                                       "    if False:\n        try:\n" + "    " + lock_line)
         .replace("    except FileExistsError:\n        raise Fail('locked')",
                  "        except FileExistsError:\n            raise Fail('locked')"),
         "writer exclusive lock must be direct top-level try"),
        ("lock-path", positive.replace("os.open(LOCK,", "os.open(ALTERNATE_LOCK,"),
         "writer lock must use canonical exclusive-create path flags and mode"),
        ("lock-flags", positive.replace("os.O_EXCL", "os.O_TRUNC"),
         "writer lock must use canonical exclusive-create path flags and mode"),
        ("lock-mode", positive.replace("0o600", "0o644"),
         "writer lock must use canonical exclusive-create path flags and mode"),
        ("lock-handler", positive.replace("except FileExistsError:", "except PermissionError:"),
         "writer existing lock must fail closed"),
        ("validation-after-lock", positive.replace("    validate_record(record)\n", "")
         + "    validate_record(record)\n",
         "writer record validation must precede lock"),
    )
    for label, mutated, expected in mutations:
        try:
            require_parser_lock_reachability(mutated)
        except NegativeFailure as exc:
            require(str(exc) == expected, f"writer parser/lock {label} diagnostic drift")
        else:
            raise NegativeFailure(f"writer parser/lock {label} bypass unexpectedly accepted")
    print("PASS reject: eleven parser/lock reachability and fail-closed substitutes")


def require_writer_cli_dispatch(source: str) -> None:
    """Require a live CLI invocation and a nonzero Fail exception boundary."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise NegativeFailure("writer dispatch source syntax invalid") from exc
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
            "writer canonical CLI dispatch guard missing or duplicated")
    guard = guards[0]
    require(not guard.orelse and len(guard.body) == 1
            and isinstance(guard.body[0], ast.Try),
            "writer CLI dispatch must be a direct try")
    dispatch = guard.body[0]
    require(len(dispatch.body) == 1 and isinstance(dispatch.body[0], ast.Raise),
            "writer CLI dispatch must raise main exit status")
    raised = dispatch.body[0].exc
    require(isinstance(raised, ast.Call) and isinstance(raised.func, ast.Name)
            and raised.func.id == "SystemExit" and len(raised.args) == 1
            and not raised.keywords
            and isinstance(raised.args[0], ast.Call)
            and isinstance(raised.args[0].func, ast.Name)
            and raised.args[0].func.id == "main"
            and not raised.args[0].args and not raised.args[0].keywords,
            "writer CLI dispatch must call guarded main")
    require(not dispatch.orelse and not dispatch.finalbody
            and len(dispatch.handlers) == 1
            and isinstance(dispatch.handlers[0].type, ast.Name)
            and dispatch.handlers[0].type.id == "Fail",
            "writer CLI dispatch must catch only writer Fail")
    handler = dispatch.handlers[0]
    require(bool(handler.body) and isinstance(handler.body[-1], ast.Raise)
            and isinstance(handler.body[-1].exc, ast.Call)
            and isinstance(handler.body[-1].exc.func, ast.Name)
            and handler.body[-1].exc.func.id == "SystemExit"
            and len(handler.body[-1].exc.args) == 1
            and isinstance(handler.body[-1].exc.args[0], ast.Constant)
            and type(handler.body[-1].exc.args[0].value) is int
            and handler.body[-1].exc.args[0].value != 0,
            "writer CLI Fail handler must exit nonzero")


def prove_writer_cli_dispatch_classifier() -> None:
    positive = "\n".join((
        "def main():",
        "    require_cli_authorities()",
        "if __name__ == '__main__':",
        "    try:",
        "        raise SystemExit(main())",
        "    except Fail as exc:",
        "        print(str(exc))",
        "        raise SystemExit(1)",
        "",
    ))
    require_writer_cli_dispatch(positive)
    mutations = (
        ("guard-removed", positive.replace("if __name__ == '__main__':", "if False:"),
         "writer canonical CLI dispatch guard missing or duplicated"),
        ("guard-name", positive.replace("'__main__'", "'__other__'"),
         "writer canonical CLI dispatch guard missing or duplicated"),
        ("guard-duplicate", positive + "if __name__ == '__main__':\n    pass\n",
         "writer canonical CLI dispatch guard missing or duplicated"),
        ("dispatch-call-only", positive.replace("raise SystemExit(main())", "main()"),
         "writer CLI dispatch must raise main exit status"),
        ("dispatch-success", positive.replace("raise SystemExit(main())", "raise SystemExit(0)"),
         "writer CLI dispatch must call guarded main"),
        ("dispatch-string", positive.replace("raise SystemExit(main())", "'raise SystemExit(main())'"),
         "writer CLI dispatch must raise main exit status"),
        ("dispatch-dead", positive.replace("        raise SystemExit(main())",
                                           "        if False:\n            raise SystemExit(main())"),
         "writer CLI dispatch must raise main exit status"),
        ("handler-type", positive.replace("except Fail as exc:", "except Exception as exc:"),
         "writer CLI dispatch must catch only writer Fail"),
        ("handler-swallow", positive.replace("        raise SystemExit(1)", "        pass"),
         "writer CLI Fail handler must exit nonzero"),
        ("handler-zero", positive.replace("raise SystemExit(1)", "raise SystemExit(0)"),
         "writer CLI Fail handler must exit nonzero"),
    )
    for label, mutated, expected in mutations:
        try:
            require_writer_cli_dispatch(mutated)
        except NegativeFailure as exc:
            require(str(exc) == expected, f"writer CLI dispatch {label} diagnostic drift")
        else:
            raise NegativeFailure(f"writer CLI dispatch {label} bypass unexpectedly accepted")
    print("PASS reject: ten writer CLI dispatch and failure-status substitutes")


def require_no_pre_dispatch_exit(source: str) -> None:
    """Reject explicit module-scope termination before the guarded CLI dispatch."""
    require_writer_cli_dispatch(source)
    tree = ast.parse(source)

    def exits_before_dispatch(node: ast.AST) -> bool:
        # Function bodies are deferred, but decorators and defaults execute at definition.
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            eager = [*node.decorator_list, *node.args.defaults,
                     *(value for value in node.args.kw_defaults if value is not None)]
            return any(exits_before_dispatch(value) for value in eager)
        if isinstance(node, ast.Lambda):
            eager = [*node.args.defaults,
                     *(value for value in node.args.kw_defaults if value is not None)]
            return any(exits_before_dispatch(value) for value in eager)
        # Class bodies, bases, keywords and decorators execute during module import.
        if isinstance(node, ast.ClassDef):
            eager = [*node.decorator_list, *node.bases,
                     *(keyword.value for keyword in node.keywords), *node.body]
            return any(exits_before_dispatch(value) for value in eager)
        if isinstance(node, ast.Raise):
            return True
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {"exit", "quit", "exec", "eval"}:
                return True
            if (isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and (node.func.value.id, node.func.attr) in
                    {("sys", "exit"), ("os", "_exit")}):
                return True
        return any(exits_before_dispatch(child) for child in ast.iter_child_nodes(node))

    require(not any(exits_before_dispatch(statement) for statement in tree.body[:-1]),
            "writer module can terminate before CLI dispatch")


def prove_pre_dispatch_exit_classifier() -> None:
    positive = "\n".join((
        "def main():",
        "    require_cli_authorities()",
        "if __name__ == '__main__':",
        "    try:",
        "        raise SystemExit(main())",
        "    except Fail as exc:",
        "        print(str(exc))",
        "        raise SystemExit(1)",
        "",
    ))
    require_no_pre_dispatch_exit(positive)
    guard = "if __name__ == '__main__':"
    mutations = (
        ("raise", "raise SystemExit(0)\n"),
        ("sys-exit", "sys.exit(0)\n"),
        ("os-exit", "os._exit(0)\n"),
        ("exit", "exit(0)\n"),
        ("quit", "quit()\n"),
        ("branch", "if True:\n    raise SystemExit(0)\n"),
        ("try", "try:\n    sys.exit(0)\nexcept Exception:\n    pass\n"),
        ("exec", "exec('raise SystemExit(0)')\n"),
        ("eval", "eval('exit(0)')\n"),
        ("class-exit", "class Early:\n    sys.exit(0)\n"),
        ("class-raise", "class Early:\n    raise SystemExit(0)\n"),
        ("decorator-exit", "@exit(0)\ndef helper():\n    pass\n"),
        ("default-exit", "def helper(value=exit(0)):\n    pass\n"),
        ("class-base-exit", "class Early(exit(0)):\n    pass\n"),
        ("lambda-default-exit", "helper = lambda value=exit(0): value\n"),
    )
    for label, prelude in mutations:
        mutated = positive.replace(guard, prelude + guard, 1)
        try:
            require_no_pre_dispatch_exit(mutated)
        except NegativeFailure as exc:
            require(str(exc) == "writer module can terminate before CLI dispatch",
                    f"writer pre-dispatch {label} diagnostic drift")
        else:
            raise NegativeFailure(f"writer pre-dispatch {label} exit unexpectedly accepted")
    print("PASS reject: fifteen module-scope and eager-definition termination substitutes")


def prove_guard_source_classifier() -> None:
    valid = "def main():\n    require_cli_authorities()\n    parser = argparse.ArgumentParser()\n"
    require_direct_first_guard(valid)
    negatives = (
        ("comment", "def main():\n    # require_cli_authorities()\n    parser = argparse.ArgumentParser()\n"),
        ("string", "def main():\n    'require_cli_authorities()'\n    parser = argparse.ArgumentParser()\n"),
        ("dead", "def main():\n    if False:\n        require_cli_authorities()\n    parser = argparse.ArgumentParser()\n"),
        ("early-return", "def main():\n    return 0\n    require_cli_authorities()\n"),
        ("async", "async def main():\n    require_cli_authorities()\n"),
    )
    for label, source in negatives:
        try:
            require_direct_first_guard(source)
        except NegativeFailure as exc:
            expected = ("writer main must be one synchronous definition" if label == "async"
                        else "writer main must begin with direct CLI authority guard")
            require(str(exc) == expected, f"writer entrypoint {label} diagnostic drift")
        else:
            raise NegativeFailure(f"writer entrypoint {label} bypass unexpectedly accepted")
    print("PASS reject: comment/string/dead/early-return/async CLI guard substitutes")


def require_lock_probe_reachable(source: str) -> None:
    """Require the existing transport CI suite to invoke the actual lock lifecycle negative."""
    tree = ast.parse(source)
    mains = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name == "main"]
    require(len(mains) == 1, "typed transport negative main missing")
    calls = [node for node in mains[0].body if isinstance(node, ast.Expr)
             and isinstance(node.value, ast.Call)
             and isinstance(node.value.func, ast.Name)
             and node.value.func.id == "exercise_writer_lock_lifecycle_negative"
             and not node.value.args and not node.value.keywords]
    require(len(calls) == 1, "typed lock lifecycle negative not invoked directly by CI")
    child_calls = [node for node in mains[0].body if isinstance(node, ast.Expr)
                   and isinstance(node.value, ast.Call)
                   and isinstance(node.value.func, ast.Name)
                   and node.value.func.id == "prove_child_validator_symlink_rejected"
                   and len(node.value.args) == 1
                   and isinstance(node.value.args[0], ast.Name)
                   and node.value.args[0].id == "validator"
                   and not node.value.keywords]
    require(len(child_calls) == 1,
            "typed child validator symlink negative not invoked directly by CI")


def prove_lock_probe_reachability() -> None:
    require(TRANSPORT_NEGATIVE.is_file() and not TRANSPORT_NEGATIVE.is_symlink(),
            "typed transport negative source missing or symlinked")
    require(TRANSPORT_NEGATIVE.stat().st_size <= 1024 * 1024,
            "typed transport negative source too large")
    source = TRANSPORT_NEGATIVE.read_text(encoding="utf-8")
    require_lock_probe_reachable(source)
    removed = source.replace("    exercise_writer_lock_lifecycle_negative()\n", "", 1)
    require(removed != source, "typed lock negative mutation did not apply")
    try:
        require_lock_probe_reachable(removed)
    except NegativeFailure as exc:
        require(str(exc) == "typed lock lifecycle negative not invoked directly by CI",
                "typed lock negative removal rejected at wrong boundary")
    else:
        raise NegativeFailure("typed lock negative removal unexpectedly accepted")
    removed_child = source.replace("    prove_child_validator_symlink_rejected(validator)\n", "", 1)
    require(removed_child != source, "typed child symlink negative mutation did not apply")
    try:
        require_lock_probe_reachable(removed_child)
    except NegativeFailure as exc:
        require(str(exc) == "typed child validator symlink negative not invoked directly by CI",
                "typed child symlink negative removal rejected at wrong boundary")
    else:
        raise NegativeFailure("typed child symlink negative removal unexpectedly accepted")
    print("PASS: typed lock and child-symlink negatives remain directly reachable from CI")


def main() -> int:
    prove_guard_source_classifier()
    prove_main_binding_classifier()
    prove_parser_lock_classifier()
    prove_lock_probe_reachability()
    prove_writer_cli_dispatch_classifier()
    prove_pre_dispatch_exit_classifier()
    writer_source = WRITER_PATH.read_text(encoding="utf-8")
    require_unique_writer_main_binding(writer_source)
    require_writer_cli_dispatch(writer_source)
    require_no_pre_dispatch_exit(writer_source)
    writer = load_writer()
    guard = getattr(writer, "require_cli_authorities", None)
    require(callable(guard), "typed non-resurrection writer CLI authority guard missing")

    main_source = inspect.getsource(writer.main)
    require_parser_lock_reachability(main_source)

    writer.require_cli_authorities()
    contract_before = writer.CANONICAL_CONTRACT.read_bytes()
    registry_before = writer.CANONICAL_REGISTRY.read_bytes()
    generation_before = writer.CANONICAL_GEN_EVIDENCE_REGISTRY.read_bytes()

    substitutions = (
        ("CONTRACT", writer.CANONICAL_REGISTRY),
        ("REGISTRY", writer.CANONICAL_CONTRACT),
        ("GEN_EVIDENCE_REGISTRY", writer.CANONICAL_REGISTRY),
        ("GEN_WRITER", ROOT / "scripts/request-memory-os-backup-restore-drill.py"),
        ("LOCK", ROOT / "contracts/operations/.backup-restore-non-resurrection-admission-alternate.lock"),
    )
    for field, substitute in substitutions:
        expect_rejected(writer, field, substitute)

    prove_materialized_lock_symlink_fails_closed(writer)
    writer.require_cli_authorities()
    require(writer.CANONICAL_CONTRACT.read_bytes() == contract_before,
            "typed writer CLI authority rejection mutated canonical contract")
    require(writer.CANONICAL_REGISTRY.read_bytes() == registry_before,
            "typed writer CLI authority rejection mutated canonical registry")
    require(writer.CANONICAL_GEN_EVIDENCE_REGISTRY.read_bytes() == generation_before,
            "typed writer CLI authority rejection mutated generation evidence registry")

    print("Memory OS typed non-resurrection writer CLI authority negative PASS")
    print("canonical typed evidence authorities substitution-rejected: true")
    print("CLI authority guard executes before input parsing: true")
    print("materialized lock symlink rejected by exclusive-create semantics: true")
    print("external lock target mutated: false")
    print("canonical registries mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"TYPED NON-RESURRECTION WRITER AUTHORITY NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
