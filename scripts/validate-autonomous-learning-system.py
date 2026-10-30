#!/usr/bin/env python3
"""Fail-closed validator for the autonomous improvement/learning contract."""

from __future__ import annotations

import argparse
from collections import Counter
import ast
import difflib
import hashlib
import json
import math
import os
import stat
import sys
from pathlib import Path
from typing import Any

CONTRACT = Path("contracts/operations/autonomous-learning-system.json")
LEARNING = Path("docs/operations/AUTONOMOUS-OPS-LEARNING.md")
VALIDATOR = Path("scripts/validate-autonomous-learning-system.py")
NEGATIVE_VALIDATOR = Path("scripts/validate-autonomous-learning-system-negative.py")
CI_ENTRYPOINT = Path("scripts/validate-memory-os-entry-docs.py")
EXPECTED_LOOP = [
    "observe", "diagnose", "search_prior_knowledge", "change", "validate",
    "persist_learning", "verify_authority", "continue",
]
FAILURE_FIELDS = {"symptom", "evidence", "rootCauseOrUnknown", "failedApproach", "correction", "recurrenceGuard", "retryCondition"}
SUCCESS_FIELDS = {"outcome", "evidence", "whySafe", "reusableMechanism", "protectedAuthorityCheck"}
TRUE_RULES = {
    "searchBeforeChange", "sameFailedApproachRequiresChangedPrecondition",
    "preferExecutableGuard", "verifyProtectedAuthorityAfterChange",
    "scopedBlockerDoesNotStopIndependentWork", "unchangedBlockerIsNotRetried",
    "historyIsAppendOnly", "learningIsNeverProductionEvidence",
    "learningCannotPromoteReadiness", "ciReachabilityRequired",
}


class ValidationFailure(RuntimeError):
    pass


MAX_LEARNING_CONTRACT_BYTES = 1024 * 1024
MAX_CANONICAL_LEARNING_BYTES = 8 * 1024 * 1024
MAX_CANONICAL_ENTRYPOINT_BYTES = 512 * 1024


def read_canonical_authority_bytes(path: Path, max_bytes: int, *, too_large: str) -> bytes:
    """Read a bounded, descriptor-pinned regular canonical authority snapshot."""
    diagnostic = f"canonical authority changed during read: {path}"
    try:
        # Snapshot the directory chain too: a parent can become a symlink
        # to its old inode while the leaf still resolves to identical bytes.
        parents = [(parent, parent.lstat()) for parent in path.parents]
        preflight = path.lstat()
    except OSError:
        raise ValidationFailure(f"unreadable authority: {path}") from None
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        raise ValidationFailure(f"unreadable authority: {path}") from None
    try:
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                    or before.st_mode & 0o002
                    or (preflight.st_dev, preflight.st_ino) !=
                    (before.st_dev, before.st_ino)
                    # Same-inode mutation between lstat and open is also
                    # unreviewed, even if no bytes change after open.
                    or (preflight.st_size, preflight.st_mtime_ns,
                        preflight.st_ctime_ns) !=
                    (before.st_size, before.st_mtime_ns, before.st_ctime_ns)):
                raise ValidationFailure(diagnostic)
            if before.st_size > max_bytes:
                raise ValidationFailure(too_large)
            raw = stream.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise ValidationFailure(too_large)
            after = os.fstat(stream.fileno())
            live = path.lstat()
            for parent, prior in parents:
                current = parent.lstat()
                if ((current.st_dev, current.st_ino, stat.S_IFMT(current.st_mode)) !=
                        (prior.st_dev, prior.st_ino, stat.S_IFMT(prior.st_mode))):
                    raise ValidationFailure(diagnostic)
            if (not stat.S_ISREG(live.st_mode)
                    or (live.st_dev, live.st_ino) != (before.st_dev, before.st_ino)
                    or after.st_nlink != 1 or live.st_nlink != 1
                    or after.st_mode & 0o002 or live.st_mode & 0o002
                    or (after.st_size, after.st_mtime_ns, after.st_ctime_ns) !=
                    (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                    or live.st_ctime_ns != before.st_ctime_ns):
                raise ValidationFailure(diagnostic)
            return raw
    except OSError:
        raise ValidationFailure(f"unreadable authority: {path}") from None


def load_object(path: Path) -> dict[str, Any]:
    """Read the learning contract with bounded, unambiguous JSON semantics."""
    if not path.is_file():
        raise ValidationFailure(f"missing authority: {path}")
    raw = read_canonical_authority_bytes(
        path, MAX_LEARNING_CONTRACT_BYTES,
        too_large=f"oversized JSON authority: {path}",
    )
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ValidationFailure(f"invalid UTF-8: {path}") from None

    def unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValidationFailure(f"duplicate JSON key: {path}")
            value[key] = item
        return value

    def reject_constant(_value: str) -> None:
        raise ValidationFailure(f"nonfinite JSON number: {path}")

    def finite_float(value: str) -> float:
        number = float(value)
        if not math.isfinite(number):
            raise ValidationFailure(f"nonfinite JSON number: {path}")
        return number

    def bounded_int(value: str) -> int:
        if len(value.lstrip("-")) > 128:
            raise ValidationFailure(f"oversized JSON integer: {path}")
        return int(value)

    try:
        value = json.loads(
            source, object_pairs_hook=unique_keys,
            parse_constant=reject_constant, parse_float=finite_float,
            parse_int=bounded_int,
        )
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON: {path}: {exc}") from None
    except (ValueError, OverflowError, RecursionError):
        raise ValidationFailure(f"invalid JSON: {path}: parser rejected value") from None
    if not isinstance(value, dict):
        raise ValidationFailure(f"root must be an object: {path}")
    return value



def exact_string_set(value: Any, expected: set[str], field: str) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValidationFailure(f"{field} must be a string list")
    if len(value) != len(set(value)):
        raise ValidationFailure(f"{field} contains duplicates")
    if set(value) != expected:
        raise ValidationFailure(f"{field} changed: {value!r}")


def validate(repo_root: Path) -> None:
    # All five bound learning authorities must be actual repository files.
    # Path.is_file() and read_text() follow symlinks, so reject aliases first.
    for relative in (CONTRACT, LEARNING, VALIDATOR, NEGATIVE_VALIDATOR, CI_ENTRYPOINT):
        path = repo_root / relative
        # A writable directory can replace a checked authority's pathname
        # without changing the authority file's own mode or link count.
        # Limit this policy to the checkout root and its in-repo parents:
        # /tmp and other outer runner ancestors are not our authority.
        for depth in range(len(relative.parts)):
            parent = repo_root.joinpath(*relative.parts[:depth])
            try:
                if (not parent.is_symlink() and parent.is_dir()
                        and parent.stat().st_mode & 0o002):
                    raise ValidationFailure(
                        f"world-writable learning authority parent forbidden: "
                        f"{parent.relative_to(repo_root)}"
                    )
            except OSError:
                raise ValidationFailure(
                    f"unreadable learning authority parent: {parent}"
                ) from None
        if path.is_symlink():
            raise ValidationFailure(f"symlinked learning authority forbidden: {relative}")
        # Hardlinks are not symlinks: a second directory entry can mutate a
        # protected authority through an unreviewed path. Require one inode
        # name for every canonical learning/CI authority in this checkout.
        try:
            # A FIFO/socket/directory can resolve inside the checkout and
            # evade symlink checks, yet a subsequent read may block or fail.
            if path.exists() and not path.is_file():
                raise ValidationFailure(f"nonregular learning authority forbidden: {relative}")
            if path.is_file() and path.stat().st_nlink != 1:
                raise ValidationFailure(f"hardlinked learning authority forbidden: {relative}")
            # A world-writable canonical file can be altered by an unrelated
            # local principal even when it is a unique regular inode.
            if path.is_file() and path.stat().st_mode & 0o002:
                raise ValidationFailure(f"world-writable learning authority forbidden: {relative}")
        except OSError:
            raise ValidationFailure(f"unreadable learning authority: {relative}") from None
        try:
            resolved = path.resolve(strict=True).relative_to(repo_root.resolve(strict=True))
        except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
            raise ValidationFailure(f"learning authority path missing or escapes root: {relative}") from exc
        if resolved != relative:
            raise ValidationFailure(f"learning authority path substituted through parent: {relative}")
    contract = load_object(repo_root / CONTRACT)
    expected_keys = {
        "schemaVersion", "purpose", "loop", "requiredFailureFields",
        "requiredSuccessFields", "rules", "protectedInvariants", "authority",
        "validator", "negativeValidator", "ciEntrypoint",
    }
    if set(contract) != expected_keys:
        raise ValidationFailure("learning contract field set changed")
    if contract["purpose"] != (
            "Turn observed execution outcomes into reusable, fail-closed prevention "
            "without treating learning as production evidence."):
        raise ValidationFailure("learning contract purpose changed")
    if contract.get("schemaVersion") != "autonomous-learning-system.0.1":
        raise ValidationFailure("unsupported schemaVersion")
    if contract.get("loop") != EXPECTED_LOOP:
        raise ValidationFailure("closed-loop execution order changed")
    exact_string_set(contract.get("requiredFailureFields"), FAILURE_FIELDS, "requiredFailureFields")
    exact_string_set(contract.get("requiredSuccessFields"), SUCCESS_FIELDS, "requiredSuccessFields")

    rules = contract.get("rules")
    if not isinstance(rules, dict):
        raise ValidationFailure("rules must be an object")
    if set(rules) != TRUE_RULES:
        raise ValidationFailure("learning contract rule set changed")
    for rule in TRUE_RULES:
        if rules.get(rule) is not True:
            raise ValidationFailure(f"mandatory learning rule must remain true: {rule}")

    protected = contract.get("protectedInvariants")
    if not isinstance(protected, dict):
        raise ValidationFailure("protectedInvariants must be an object")
    if set(protected) != {"productionDecisionDefault", "opsP0007EvidenceMustBeReal",
                          "humanPromotionReviewIsSeparate"}:
        raise ValidationFailure("learning contract protected invariant set changed")
    if protected.get("productionDecisionDefault") != "NO_GO":
        raise ValidationFailure("learning must not weaken the NO_GO default")
    if protected.get("opsP0007EvidenceMustBeReal") is not True:
        raise ValidationFailure("OPS-P0-007 real-evidence boundary must remain true")
    if protected.get("humanPromotionReviewIsSeparate") is not True:
        raise ValidationFailure("human promotion review must remain separate")
    if contract.get("authority") != LEARNING.as_posix():
        raise ValidationFailure("learning authority path changed")
    if contract.get("validator") != VALIDATOR.as_posix():
        raise ValidationFailure("executable learning guard binding changed")
    if contract.get("negativeValidator") != NEGATIVE_VALIDATOR.as_posix():
        raise ValidationFailure("negative learning guard binding changed")
    if contract.get("ciEntrypoint") != CI_ENTRYPOINT.as_posix():
        raise ValidationFailure("learning CI entrypoint binding changed")
    if not (repo_root / VALIDATOR).is_file():
        raise ValidationFailure("bound executable learning guard is missing")
    if not (repo_root / NEGATIVE_VALIDATOR).is_file():
        raise ValidationFailure("bound negative learning guard is missing")
    try:
        ci_entrypoint = read_canonical_authority_bytes(
            repo_root / CI_ENTRYPOINT, MAX_CANONICAL_ENTRYPOINT_BYTES,
            too_large=f"oversized learning CI entrypoint: {CI_ENTRYPOINT}",
        ).decode("utf-8")
    except UnicodeDecodeError:
        raise ValidationFailure(f"invalid UTF-8: {CI_ENTRYPOINT}") from None
    for guard in (VALIDATOR.as_posix(), NEGATIVE_VALIDATOR.as_posix()):
        if guard not in ci_entrypoint:
            raise ValidationFailure(f"learning CI entrypoint does not invoke bound guard: {guard}")
    for fragment in (
        "def validate_learning_guards(failures: list[str]) -> None:",
        "[sys.executable, str(path), \"--repo-root\", str(REPO_ROOT)]",
        "LEARNING_GUARD_TIMEOUT_SECONDS = 120",
        "timeout=LEARNING_GUARD_TIMEOUT_SECONDS",
        "except subprocess.TimeoutExpired:",
        "validate_learning_guards(failures)",
    ):
        if fragment not in ci_entrypoint:
            raise ValidationFailure(f"learning CI entrypoint lost executable guard invocation: {fragment}")

    # Source substrings in comments or quoted strings cannot prove that the
    # CI entrypoint actually calls the learning guards from its live main().
    try:
        entry_tree = ast.parse(ci_entrypoint, filename=str(repo_root / CI_ENTRYPOINT))
    except SyntaxError as exc:
        raise ValidationFailure("learning CI entrypoint is not valid Python") from exc
    def module_scope_rebinds(name: str) -> bool:
        # Deferred function bodies and comprehensions do not run at import
        # time. Function decorators/defaults and class bodies DO execute, and
        # can rebind a canonical guard through globals() before main() runs.
        # Ordinary class-local names are not module bindings.
        def binds(node: ast.AST, *, class_local: bool = False) -> bool:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                eager = [*node.args.defaults, *(
                    value for value in node.args.kw_defaults if value is not None
                )]
                if not isinstance(node, ast.Lambda):
                    eager.extend(node.decorator_list)
                    # Eager annotations can rebind a protected CI guard.
                    # Conservatively inspect them even with postponed typing.
                    eager.extend(arg.annotation for arg in
                                 [*node.args.posonlyargs, *node.args.args,
                                  *node.args.kwonlyargs, node.args.vararg, node.args.kwarg]
                                 if arg is not None and arg.annotation is not None)
                    if node.returns is not None:
                        eager.append(node.returns)
                    if any(isinstance(dec, ast.Lambda)
                           and binds(dec.body, class_local=True)
                           for dec in node.decorator_list):
                        return True
                return any(binds(value, class_local=class_local) for value in eager)
            if isinstance(node, ast.ClassDef):
                eager = [*node.decorator_list, *node.bases, *(
                    keyword.value for keyword in node.keywords
                )]
                if any(isinstance(dec, ast.Lambda)
                       and binds(dec.body, class_local=class_local)
                       for dec in node.decorator_list):
                    return True
                return (any(binds(value, class_local=class_local) for value in eager)
                        or any(binds(child, class_local=True) for child in node.body))
            # List/set/dict comprehensions run immediately; their targets
            # are comprehension-local, but elements, iterables and filters
            # can mutate the module namespace. A generator expression defers
            # its body, while its outermost iterable is evaluated eagerly.
            if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)):
                values = ([node.key, node.value] if isinstance(node, ast.DictComp)
                          else [node.elt])
                return (any(binds(value, class_local=class_local) for value in values)
                        or any(
                            binds(generator.iter, class_local=class_local)
                            or any(binds(condition, class_local=class_local)
                                   for condition in generator.ifs)
                            for generator in node.generators
                        ))
            if isinstance(node, ast.GeneratorExp):
                return bool(node.generators) and binds(
                    node.generators[0].iter, class_local=class_local
                )
            if isinstance(node, ast.Global):
                return name in node.names
            if isinstance(node, ast.Name):
                return (not class_local and node.id == name
                        and isinstance(node.ctx, (ast.Store, ast.Del)))
            # Attribute and module-dict stores can mutate the bound guard
            # through aliases without any lexical Name(Store) for it.
            if (isinstance(node, ast.Attribute) and node.attr == name
                    and isinstance(node.ctx, (ast.Store, ast.Del))):
                return True
            if (isinstance(node, ast.Subscript)
                    and isinstance(node.ctx, (ast.Store, ast.Del))
                    and isinstance(node.slice, ast.Constant) and node.slice.value == name
                    and isinstance(node.value, ast.Attribute)
                    and node.value.attr == "__dict__"):
                return True
            if (isinstance(node, ast.Subscript)
                    and isinstance(node.ctx, (ast.Store, ast.Del))
                    and isinstance(node.slice, ast.Constant) and node.slice.value == name
                    and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id in {"globals", "vars", "locals"}
                    and not node.value.args and not node.value.keywords):
                return True
            if isinstance(node, ast.Call):
                # Builtin/module dictionary lookup can hide eager code execution.
                # Conservative lexical rejection; this is not alias closure.
                if isinstance(node.func, ast.Subscript):
                    target = node.func.value
                    module_dict = (isinstance(target, ast.Attribute)
                                   and target.attr == "__dict__"
                                   and isinstance(target.value, ast.Name)
                                   and target.value.id in {"builtins", "__builtins__", "importlib", "runpy", "pkgutil"})
                    vars_dict = (isinstance(target, ast.Call)
                                 and isinstance(target.func, ast.Name)
                                 and target.func.id == "vars" and len(target.args) == 1
                                 and not target.keywords and isinstance(target.args[0], ast.Name)
                                 and target.args[0].id in {"builtins", "__builtins__", "importlib", "runpy", "pkgutil"})
                    builtins_dict = isinstance(target, ast.Name) and target.id == "__builtins__"
                    if (module_dict or vars_dict or builtins_dict) and (
                        not isinstance(node.func.slice, ast.Constant)
                        or node.func.slice.value in {"__import__", "exec", "eval",
                                                     "import_module", "run_module", "run_path",
                                                     "reload", "find_spec", "resolve_name", "exec_module"}
                    ):
                        return True
                # Eager dynamic module execution can mutate either protected
                # binding through imported code without a local Name(Store).
                # This is conservative lexical rejection, not alias closure.
                if (isinstance(node.func, ast.Name)
                        and node.func.id in {"__import__", "import_module", "run_module", "run_path", "reload", "find_spec", "resolve_name"}):
                    return True
                if (isinstance(node.func, ast.Attribute)
                        and node.func.attr in {"import_module", "run_module", "run_path", "exec_module", "reload", "find_spec", "resolve_name", "__import__", "exec", "eval"}):
                    return True
                # Eager reflective lookup of module execution callables is
                # unreviewed even when the function is invoked indirectly.
                # Eager attrgetter/methodcaller construction can hide module
                # execution behind a returned callable; alias closure is unknown.
                if ((isinstance(node.func, ast.Name)
                     and node.func.id in {"attrgetter", "methodcaller"})
                        or (isinstance(node.func, ast.Attribute)
                            and node.func.attr in {"attrgetter", "methodcaller"})):
                    return True
                if (((isinstance(node.func, ast.Name) and node.func.id == "getattr")
                     or (isinstance(node.func, ast.Attribute) and node.func.attr == "getattr"))
                        and len(node.args) >= 2
                        and (not isinstance(node.args[1], ast.Constant)
                             or node.args[1].value in {"__import__", "import_module",
                                                       "run_module", "run_path", "exec_module", "reload",
                                                       "find_spec", "resolve_name", "exec", "eval"})):
                    return True
                # An immediately invoked lambda executes its body now, unlike
                # a bare lambda expression or a deferred generator body.
                if isinstance(node.func, ast.Lambda) and binds(
                    node.func.body, class_local=class_local
                ):
                    return True
                # Even a harmless-looking literal may execute imports or
                # mutate globals indirectly. Eager dynamic code is unreviewed.
                if isinstance(node.func, ast.Name) and node.func.id in {"exec", "eval"}:
                    return True
                if (isinstance(node.func, ast.Name)
                        and node.func.id in {"setattr", "delattr"}
                        and len(node.args) >= 2
                        and (not isinstance(node.args[1], ast.Constant)
                             or node.args[1].value == name)):
                    # A computed attribute name may resolve to either
                    # protected binding; constant unrelated names are safe.
                    return True
                if isinstance(node.func, ast.Attribute) and node.func.attr in {
                    "update", "pop", "popitem", "clear", "setdefault",
                    "__setitem__", "__delitem__"
                }:
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
                            if any(keyword.arg is None or keyword.arg == name
                                   for keyword in node.keywords):
                                return True
                            for argument in node.args:
                                if not isinstance(argument, ast.Dict):
                                    return True
                                if any(not isinstance(key, ast.Constant) or key.value == name
                                       for key in argument.keys):
                                    return True
                        elif not node.args or not isinstance(node.args[0], ast.Constant):
                            return True
                        elif node.args[0].value == name:
                            return True
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                # The exported bindings of a wildcard import are unbounded.
                return not class_local and any(
                    (isinstance(node, ast.ImportFrom) and alias.name == "*")
                    or (alias.asname or (alias.name.split(".")[0]
                                        if isinstance(node, ast.Import) else alias.name))
                    == name for alias in node.names
                )
            if isinstance(node, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar)):
                if not class_local and getattr(node, "name", None) == name:
                    return True
            return any(binds(child, class_local=class_local)
                       for child in ast.iter_child_nodes(node))

        return any(binds(node) for node in entry_tree.body)

    main_definitions = [
        node for node in entry_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    ]
    if len(main_definitions) != 1:
        raise ValidationFailure("learning CI entrypoint must define one main function")
    # An async redefinition or module-level assignment can replace the
    # checked main() binding before the canonical __main__ invocation.
    if any(
        isinstance(node, ast.AsyncFunctionDef) and node.name == "main"
        for node in entry_tree.body
    ):
        raise ValidationFailure("learning CI entrypoint main binding is shadowed by async definition")
    if any(
        (isinstance(node, ast.Assign) and any(
            isinstance(bound, ast.Name)
            and bound.id == "main"
            and isinstance(bound.ctx, ast.Store)
            for target in node.targets for bound in ast.walk(target)
        ))
        or (isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name) and node.target.id == "main")
        for node in entry_tree.body
    ):
        raise ValidationFailure("learning CI entrypoint main binding is shadowed by assignment")
    if any(
        isinstance(node, (ast.Import, ast.ImportFrom))
        and any(
            (alias.asname or (alias.name.split(".")[0] if isinstance(node, ast.Import) else alias.name))
            == "main"
            for alias in node.names
        )
        for node in entry_tree.body
    ):
        raise ValidationFailure("learning CI entrypoint main binding is shadowed by import")
    if module_scope_rebinds("main"):
        raise ValidationFailure("learning CI entrypoint main binding is shadowed by module control flow")
    # The direct main() call must resolve to the bound synchronous guard,
    # not a later async definition or assignment with the same name.
    guard_definitions = [
        node for node in entry_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "validate_learning_guards"
    ]
    if len(guard_definitions) != 1:
        raise ValidationFailure("learning CI entrypoint must define one synchronous learning guard")
    if any(
        isinstance(node, ast.AsyncFunctionDef) and node.name == "validate_learning_guards"
        for node in entry_tree.body
    ):
        raise ValidationFailure("learning CI entrypoint learning guard binding is shadowed by async definition")
    if any(
        (isinstance(node, ast.Assign) and any(
            isinstance(bound, ast.Name)
            and bound.id == "validate_learning_guards"
            and isinstance(bound.ctx, ast.Store)
            for target in node.targets for bound in ast.walk(target)
        ))
        or (isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name) and node.target.id == "validate_learning_guards")
        for node in entry_tree.body
    ):
        raise ValidationFailure("learning CI entrypoint learning guard binding is shadowed by assignment")
    if any(
        isinstance(node, (ast.Import, ast.ImportFrom))
        and any(
            (alias.asname or (alias.name.split(".")[0] if isinstance(node, ast.Import) else alias.name))
            == "validate_learning_guards"
            for alias in node.names
        )
        for node in entry_tree.body
    ):
        raise ValidationFailure("learning CI entrypoint learning guard binding is shadowed by import")
    if module_scope_rebinds("validate_learning_guards"):
        raise ValidationFailure("learning CI entrypoint learning guard binding is shadowed by module control flow")
    live_calls = [
        node for node in main_definitions[0].body
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "validate_learning_guards"
        and len(node.value.args) == 1
        and isinstance(node.value.args[0], ast.Name)
        and node.value.args[0].id == "failures"
        and not node.value.keywords
    ]
    if len(live_calls) != 1:
        raise ValidationFailure("learning CI entrypoint main must directly invoke bound learning guards")
    # A direct AST call after an unconditional top-level terminator is not
    # reachable, even though it remains a statement in main().body.
    call_index = main_definitions[0].body.index(live_calls[0])
    def can_terminate_before_guard(node: ast.AST) -> bool:
        # Nested function bodies are deferred, but their eager decorators
        # and default argument expressions execute before the guard call.
        def partial_factory(value: ast.AST) -> bool:
            return (isinstance(value, ast.Call)
                    and ((isinstance(value.func, ast.Name)
                          and value.func.id == "partial")
                         or (isinstance(value.func, ast.Attribute)
                             and value.func.attr == "partial")))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            eager = [*node.args.defaults,
                     *(value for value in node.args.kw_defaults if value is not None)]
            if not isinstance(node, ast.Lambda):
                eager.extend(node.decorator_list)
                # A lambda decorator is called while the definition is bound;
                # a bare lambda expression remains deferred.
                if (any(isinstance(dec, ast.Lambda)
                        and can_terminate_before_guard(dec.body)
                        for dec in node.decorator_list)
                        or any(partial_factory(dec) for dec in node.decorator_list)):
                    return True
            return any(can_terminate_before_guard(value) for value in eager)
        if isinstance(node, ast.ClassDef):
            if (any(isinstance(dec, ast.Lambda)
                    and can_terminate_before_guard(dec.body)
                    for dec in node.decorator_list)
                    or any(partial_factory(dec) for dec in node.decorator_list)):
                return True
        if isinstance(node, (ast.Return, ast.Raise)):
            return True
        # for-loops and eager comprehensions consume map now, whereas a
        # standalone generator expression does not iterate its map source.
        def mapped_iter(value: ast.AST) -> bool:
            return (isinstance(value, ast.Call)
                    and isinstance(value.func, ast.Name)
                    and value.func.id == "map")
        if isinstance(node, (ast.For, ast.AsyncFor)) and mapped_iter(node.iter):
            return True
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)):
            if any(mapped_iter(gen.iter) for gen in node.generators):
                return True
        if isinstance(node, ast.Call):
            # A mapped callable executes when an eager builtin consumes map.
            # Mere map construction is lazy and remains admissible.
            if (isinstance(node.func, ast.Name)
                    and node.func.id in {"list", "tuple", "set", "any", "all",
                                         "sum", "next"}
                    and any(mapped_iter(arg) or (
                            isinstance(arg, ast.GeneratorExp)
                            and any(mapped_iter(gen.iter) for gen in arg.generators)
                        ) for arg in node.args)):
                return True
            # operator.call invokes its first argument now; an exit target
            # need not appear as the direct AST callee of this expression.
            if ((isinstance(node.func, ast.Name) and node.func.id == "call")
                    or (isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "operator"
                        and node.func.attr == "call")):
                return True
            # An immediately invoked partial is an unreviewed callable
            # wrapper: its target may terminate even without a direct exit AST.
            # Mere construction remains deferred unless applied as a decorator.
            if partial_factory(node.func):
                return True
            # An immediately called lambda executes its body before the
            # guard, unlike a deferred lambda declaration.
            if (isinstance(node.func, ast.Lambda)
                    and can_terminate_before_guard(node.func.body)):
                return True
            if isinstance(node.func, ast.Call):
                # Operator callable factories can invoke a terminating method
                # before the CI guard; factory creation alone is not proof.
                factory = node.func.func
                if ((isinstance(factory, ast.Name) and factory.id == "methodcaller")
                        or (isinstance(factory, ast.Attribute) and factory.attr == "methodcaller")):
                    args = node.func.args
                    if not args or not isinstance(args[0], ast.Constant) or (
                        args[0].value in {"abort", "_exit", "exit", "quit"}
                    ):
                        return True
                if isinstance(factory, ast.Call):
                    maker = factory.func
                    if ((isinstance(maker, ast.Name) and maker.id == "attrgetter")
                            or (isinstance(maker, ast.Attribute) and maker.attr == "attrgetter")):
                        args = factory.args
                        if not args or not isinstance(args[0], ast.Constant) or (
                            args[0].value in {"abort", "_exit", "exit", "quit"}
                        ):
                            return True
            if isinstance(node.func, ast.Call):
                # Reflective lookup can invoke an abort/exit callable before
                # the canonical CI guard even without a direct attribute call.
                lookup = node.func
                reflective = ((isinstance(lookup.func, ast.Name)
                               and lookup.func.id == "getattr")
                              or (isinstance(lookup.func, ast.Attribute)
                                  and lookup.func.attr == "getattr"))
                if (reflective and len(lookup.args) >= 2
                        and isinstance(lookup.args[0], ast.Name)
                        and lookup.args[0].id in {"os", "sys", "builtins"}
                        and (not isinstance(lookup.args[1], ast.Constant)
                             or lookup.args[1].value in {"abort", "_exit", "exit", "quit"})):
                    return True
            if isinstance(node.func, ast.Subscript):
                # An eager module-dictionary call may terminate execution
                # without a visible os.abort()/sys.exit() attribute callee.
                target = node.func.value
                module_dict = (isinstance(target, ast.Attribute)
                               and target.attr == "__dict__"
                               and isinstance(target.value, ast.Name)
                               and target.value.id in {"os", "sys", "builtins", "__builtins__"})
                vars_dict = (isinstance(target, ast.Call)
                             and isinstance(target.func, ast.Name)
                             and target.func.id == "vars" and len(target.args) == 1
                             and not target.keywords and isinstance(target.args[0], ast.Name)
                             and target.args[0].id in {"os", "sys", "builtins", "__builtins__"})
                builtin_dict = isinstance(target, ast.Name) and target.id == "__builtins__"
                if (module_dict or vars_dict or builtin_dict) and (
                    not isinstance(node.func.slice, ast.Constant)
                    or node.func.slice.value in {"abort", "_exit", "exit", "quit"}
                ):
                    return True
            if isinstance(node.func, ast.Name) and node.func.id in {
                "exit", "quit", "exec", "eval"
            }:
                return True
            if (isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and (node.func.value.id, node.func.attr) in {
                        ("sys", "exit"), ("os", "_exit"), ("os", "abort"),
                        ("builtins", "exit"), ("builtins", "quit")
                    }):
                return True
        return any(can_terminate_before_guard(child) for child in ast.iter_child_nodes(node))

    if any(can_terminate_before_guard(node)
           for node in main_definitions[0].body[:call_index]):
        raise ValidationFailure("learning CI entrypoint guard call follows unconditional return or raise")
    expected_entry_guard = ast.dump(
        ast.parse('if __name__ == "__main__":\n    raise SystemExit(main())').body[0],
        include_attributes=False,
    )
    entry_guard_count = sum(
        ast.dump(node, include_attributes=False) == expected_entry_guard
        for node in entry_tree.body
    )
    if entry_guard_count != 1:
        raise ValidationFailure("learning CI entrypoint must execute main from its live module guard")
    # A valid live module guard is not reachable if top-level execution
    # terminates before reaching it. Reuse the same conservative termination
    # detector already applied to statements preceding the guard in main().
    live_entry_guard = next(
        node for node in entry_tree.body
        if ast.dump(node, include_attributes=False) == expected_entry_guard
    )
    if any(can_terminate_before_guard(node)
           for node in entry_tree.body[:entry_tree.body.index(live_entry_guard)]):
        raise ValidationFailure("learning CI entrypoint module terminates before live main guard")

    # A common source-negative workflow audit must remain a live main() call.
    # Merely retaining its definition or a quoted/commented invocation is not CI reachability.
    source_name = "validate_source_negative_ci_reachability"
    source_definitions = [
        node for node in entry_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == source_name
    ]
    if (len(source_definitions) != 1 or module_scope_rebinds(source_name)
            or any(isinstance(node, ast.AsyncFunctionDef) and node.name == source_name
                   for node in entry_tree.body)):
        raise ValidationFailure("source-negative CI guard binding changed")
    source_calls = [
        node for node in main_definitions[0].body
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == source_name
        and len(node.value.args) == 1
        and isinstance(node.value.args[0], ast.Name)
        and node.value.args[0].id == "failures"
        and not node.value.keywords
    ]
    if len(source_calls) != 1:
        raise ValidationFailure("source-negative CI guard must be called directly from main")
    source_index = main_definitions[0].body.index(source_calls[0])
    if (source_index <= call_index or any(
            can_terminate_before_guard(node)
            for node in main_definitions[0].body[call_index + 1:source_index])):
        raise ValidationFailure("source-negative CI guard call is unreachable")
    if not any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "prove_source_negative_reachability_negatives"
        for node in ast.walk(source_definitions[0])
    ):
        raise ValidationFailure("source-negative CI guard lost executable negative proof")

    prove_prewrite_python_negatives()
    try:
        learning = read_canonical_authority_bytes(
            repo_root / LEARNING, MAX_CANONICAL_LEARNING_BYTES,
            too_large=f"oversized learning authority: {LEARNING}",
        ).decode("utf-8")
    except UnicodeDecodeError:
        raise ValidationFailure(f"invalid UTF-8: {LEARNING}") from None
    for phrase in (
        "not production evidence",
        "Do not repeatedly retry an unchanged permission failure",
        "Repeating a known failed approach without changed preconditions is a regression",
        "Prefer executable guards over prose",
        "Human production-promotion review is a separate non-automatic decision",
    ):
        if phrase not in learning:
            raise ValidationFailure(f"learning authority lost invariant: {phrase}")


PREWRITE_MAX_SOURCE_BYTES = 512 * 1024
PREWRITE_MAX_SOURCE_LINES = 4096
PREWRITE_MAX_MATCH_PAIRS = 500_000
PREWRITE_MAX_ADDED_LINES = 80
PREWRITE_MAX_REMOVED_LINES = 40


def validate_prewrite_python(baseline: str, candidate: str, *,
                             expected_sha256: str, max_added: int = 40,
                             max_removed: int = 20) -> tuple[int, int]:
    """Fail closed before proposing a bounded, main-bearing Python source edit."""
    if not (1 <= max_added <= PREWRITE_MAX_ADDED_LINES
            and 0 <= max_removed <= PREWRITE_MAX_REMOVED_LINES):
        raise ValidationFailure("prewrite diff budget outside reviewed bounds")
    if len(baseline.encode("utf-8")) > PREWRITE_MAX_SOURCE_BYTES or (
            len(candidate.encode("utf-8")) > PREWRITE_MAX_SOURCE_BYTES):
        raise ValidationFailure("prewrite Python source exceeds byte limit")
    if hashlib.sha256(baseline.encode("utf-8")).hexdigest() != expected_sha256:
        raise ValidationFailure("prewrite baseline SHA-256 mismatch")
    if baseline == candidate:
        raise ValidationFailure("prewrite candidate has no changes")
    for label, source in (("baseline", baseline), ("candidate", candidate)):
        # Bound SequenceMatcher's potentially quadratic line comparisons.
        # Keep the checked-in 3,566-line negative validator admissible.
        if len(source.splitlines()) > PREWRITE_MAX_SOURCE_LINES:
            raise ValidationFailure("prewrite " + label + " Python line count exceeds reviewed bound")
        try:
            tree = ast.parse(source)
        except (SyntaxError, ValueError, RecursionError) as exc:
            raise ValidationFailure("prewrite " + label + " Python syntax invalid") from exc
        # ast.parse alone accepts some unexecutable constructs, including
        # a module-level return/break/nonlocal. Compile without executing.
        try:
            compile(tree, "<prewrite-" + label + ">", "exec", dont_inherit=True)
        except (SyntaxError, ValueError, TypeError) as exc:
            raise ValidationFailure("prewrite " + label + " Python compilation invalid") from exc
        mains = [node for node in tree.body
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and node.name == "main"]
        if len(mains) != 1 or not isinstance(mains[0], ast.FunctionDef):
            raise ValidationFailure("prewrite " + label + " must have one sync main")
        # A unique main definition can still be shadowed by eager module
        # control flow. Ignore deferred function/lambda bodies and class-local
        # assignments; this is not a reflective-mutation proof.
        def module_shadows_main(node: ast.AST, *, top_level: bool, class_local: bool = False) -> bool:
            # Decorator lambdas are invoked when applied, unlike ordinary
            # deferred lambdas. Their lexical bindings remain lambda-local.
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if any(isinstance(dec, ast.Lambda)
                       and module_shadows_main(dec.body, top_level=False,
                                               class_local=True)
                       for dec in node.decorator_list):
                    return True
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Function bodies are deferred; decorators and default
                # argument expressions run immediately at definition time.
                eager = [*node.decorator_list, *node.args.defaults,
                         *(value for value in node.args.kw_defaults
                           if value is not None)]
                # Without postponed annotations these expressions also
                # execute at definition time. Conservatively inspect them
                # even when a future import postpones their evaluation.
                eager.extend(arg.annotation for arg in
                             [*node.args.posonlyargs, *node.args.args,
                              *node.args.kwonlyargs, node.args.vararg, node.args.kwarg]
                             if arg is not None and arg.annotation is not None)
                if node.returns is not None:
                    eager.append(node.returns)
                return ((not top_level and not class_local and node.name == "main")
                        or any(module_shadows_main(value, top_level=False, class_local=class_local)
                               for value in eager))
            if isinstance(node, ast.ClassDef):
                # Class decorators/bases execute in the enclosing scope;
                # class body control flow is eager but its names are local
                # unless a global declaration explicitly redirects them.
                eager = [*node.decorator_list, *node.bases,
                         *(kw.value for kw in node.keywords)]
                return ((not class_local and node.name == "main")
                        or any(module_shadows_main(value, top_level=False,
                                                   class_local=class_local)
                               for value in eager)
                        or any(module_shadows_main(stmt, top_level=False,
                                                   class_local=True)
                               for stmt in node.body))
            if isinstance(node, ast.Lambda):
                return False
            if isinstance(node, ast.Global):
                return "main" in node.names
            # A for-loop or eager comprehension consumes a mapped callable;
            # generator expressions alone defer that iteration.
            def mapped_iter(value: ast.AST) -> bool:
                return (isinstance(value, ast.Call)
                        and isinstance(value.func, ast.Name)
                        and value.func.id == "map")
            if isinstance(node, (ast.For, ast.AsyncFor)) and mapped_iter(node.iter):
                return True
            if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)):
                if any(mapped_iter(gen.iter) for gen in node.generators):
                    return True
            # List/set/dict comprehensions evaluate their elements and filters
            # now, but keep iteration targets local. Generator expressions
            # defer their body and evaluate only the first iterable eagerly.
            if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)):
                values = ([node.key, node.value] if isinstance(node, ast.DictComp)
                          else [node.elt])
                return (any(module_shadows_main(value, top_level=False, class_local=class_local)
                            for value in values)
                        or any(module_shadows_main(gen.iter, top_level=False, class_local=class_local)
                               or any(module_shadows_main(cond, top_level=False, class_local=class_local)
                                      for cond in gen.ifs)
                               for gen in node.generators))
            if isinstance(node, ast.GeneratorExp):
                return bool(node.generators) and module_shadows_main(
                    node.generators[0].iter, top_level=False, class_local=class_local
                )
            if (isinstance(node, ast.Name) and node.id == "main"
                    and isinstance(node.ctx, (ast.Store, ast.Del))):
                return not class_local
            if isinstance(node, (ast.MatchAs, ast.MatchStar, ast.ExceptHandler)):
                if node.name == "main":
                    return not class_local
            # A module-level reflective namespace call or immediately invoked
            # lambda can rebind main without a lexical Store/Del node.
            if (isinstance(node, ast.Attribute) and node.attr == "main"
                    and isinstance(node.ctx, (ast.Store, ast.Del))):
                return True
            if (isinstance(node, ast.Subscript) and
                    isinstance(node.ctx, (ast.Store, ast.Del)) and
                    isinstance(node.slice, ast.Constant) and node.slice.value == "main"):
                return True
            if isinstance(node, ast.Call):
                # map is lazy alone, but these consumers iterate it eagerly.
                # A mapped exec/import callable may rebind main on iteration.
                if (isinstance(node.func, ast.Name)
                        and node.func.id in {"list", "tuple", "set", "any", "all",
                                             "sum", "next"}
                        and any(mapped_iter(arg) or (
                                isinstance(arg, ast.GeneratorExp)
                                and any(mapped_iter(gen.iter) for gen in arg.generators)
                            ) for arg in node.args)):
                    return True
                # operator.call dispatches a callable immediately; the
                # target may be exec/import or a reflective main rebinder.
                if ((isinstance(node.func, ast.Name) and node.func.id == "call")
                        or (isinstance(node.func, ast.Attribute)
                            and isinstance(node.func.value, ast.Name)
                            and node.func.value.id == "operator"
                            and node.func.attr == "call")):
                    return True
                # Builtin/module dictionary lookup can hide eager code execution.
                # Conservative lexical rejection; this is not alias closure.
                if isinstance(node.func, ast.Subscript):
                    target = node.func.value
                    module_dict = (isinstance(target, ast.Attribute)
                                   and target.attr == "__dict__"
                                   and isinstance(target.value, ast.Name)
                                   and target.value.id in {"builtins", "__builtins__", "importlib", "runpy", "pkgutil"})
                    vars_dict = (isinstance(target, ast.Call)
                                 and isinstance(target.func, ast.Name)
                                 and target.func.id == "vars" and len(target.args) == 1
                                 and not target.keywords and isinstance(target.args[0], ast.Name)
                                 and target.args[0].id in {"builtins", "__builtins__", "importlib", "runpy", "pkgutil"})
                    builtins_dict = isinstance(target, ast.Name) and target.id == "__builtins__"
                    if (module_dict or vars_dict or builtins_dict) and (
                        not isinstance(node.func.slice, ast.Constant)
                        or node.func.slice.value in {"__import__", "exec", "eval",
                                                     "import_module", "run_module", "run_path",
                                                     "reload", "find_spec", "resolve_name", "exec_module"}
                    ):
                        return True
                # Mutation of an arbitrary module __dict__ may replace main
                # even without a direct Name(Store) or subscript assignment.
                if (isinstance(node.func, ast.Attribute)
                        and node.func.attr in {"update", "pop", "popitem", "clear",
                                               "setdefault", "__setitem__", "__delitem__"}
                        and isinstance(node.func.value, ast.Attribute)
                        and node.func.value.attr == "__dict__"):
                    method = node.func.attr
                    if method in {"clear", "popitem"}:
                        return True
                    if method == "update":
                        if any(kw.arg is None or kw.arg == "main"
                               for kw in node.keywords):
                            return True
                        for arg in node.args:
                            if not isinstance(arg, ast.Dict):
                                return True
                            if any(not isinstance(key, ast.Constant)
                                   or key.value == "main" for key in arg.keys):
                                return True
                    elif (not node.args or not isinstance(node.args[0], ast.Constant)
                          or node.args[0].value == "main"):
                        return True
                if isinstance(node.func, ast.Lambda):
                    return True
                # Eager dynamic imports or runpy can execute unreviewed module
                # code with namespace side effects. This is a bounded lexical
                # rejection, not a complete alias or import-graph proof.
                if (isinstance(node.func, ast.Name) and
                        node.func.id in {"__import__", "import_module", "run_module", "run_path", "reload", "find_spec", "resolve_name"}):
                    return True
                if (isinstance(node.func, ast.Attribute) and
                        node.func.attr in {"import_module", "run_module", "run_path", "exec_module", "reload", "find_spec", "resolve_name", "__import__", "exec", "eval"}):
                    return True
                # Eager attrgetter/methodcaller construction can hide module
                # execution behind a returned callable; alias closure is unknown.
                if ((isinstance(node.func, ast.Name)
                     and node.func.id in {"attrgetter", "methodcaller"})
                        or (isinstance(node.func, ast.Attribute)
                            and node.func.attr in {"attrgetter", "methodcaller"})):
                    return True
                if (((isinstance(node.func, ast.Name) and node.func.id == "getattr")
                     or (isinstance(node.func, ast.Attribute) and node.func.attr == "getattr"))
                        and len(node.args) >= 2
                        and (not isinstance(node.args[1], ast.Constant)
                             or node.args[1].value in {"__import__", "import_module",
                                                       "run_module", "run_path", "exec_module", "reload",
                                                       "find_spec", "resolve_name", "exec", "eval"})):
                    return True
                if (isinstance(node.func, ast.Name) and
                        node.func.id in {"globals", "vars", "locals", "exec", "eval"}):
                    return True
                if (isinstance(node.func, ast.Name) and
                        node.func.id in {"setattr", "delattr"} and
                        len(node.args) >= 2 and
                        (not isinstance(node.args[1], ast.Constant)
                         or node.args[1].value == "main")):
                    return True
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                # A module-level star import may bind main without naming it
                # in the import AST; its export surface is not statically bound.
                return not class_local and any(
                    (isinstance(node, ast.ImportFrom) and alias.name == "*")
                    or (alias.asname or (alias.name.split(".")[0]
                                        if isinstance(node, ast.Import) else alias.name)) == "main"
                    for alias in node.names
                )
            return any(module_shadows_main(child, top_level=False, class_local=class_local)
                       for child in ast.iter_child_nodes(node))

        if any(module_shadows_main(node, top_level=True) for node in tree.body):
            raise ValidationFailure("prewrite " + label + " main binding shadowed")
        entry_guard = ast.dump(ast.parse(
            'if __name__ == "__main__":\n    raise SystemExit(main())\n'
        ).body[0], include_attributes=False)
        if sum(ast.dump(node, include_attributes=False) == entry_guard
               for node in tree.body) != 1:
            raise ValidationFailure("prewrite " + label + " must have one live main guard")
    left_lines, right_lines = baseline.splitlines(), candidate.splitlines()
    left_counts, right_counts = Counter(left_lines), Counter(right_lines)
    # Bound the number of equal-token comparisons available to the matcher,
    # independently of the byte/line limits and post-match diff budget.
    match_pairs = sum(count * right_counts.get(line, 0)
                      for line, count in left_counts.items())
    if match_pairs > PREWRITE_MAX_MATCH_PAIRS:
        raise ValidationFailure("prewrite line match density exceeds reviewed bound")
    added = removed = 0
    matcher = difflib.SequenceMatcher(
        None, left_lines, right_lines, autojunk=False
    )
    for op, a, b, c, d in matcher.get_opcodes():
        if op in ("replace", "delete"):
            removed += b - a
        if op in ("replace", "insert"):
            added += d - c
        if added > max_added or removed > max_removed:
            raise ValidationFailure("prewrite diff exceeds reviewed line budget")
    return added, removed


def prove_prewrite_python_negatives() -> None:
    baseline = ('def main() -> int:\n    return 0\n\n'
                'if __name__ == "__main__":\n    raise SystemExit(main())\n')
    sha = hashlib.sha256(baseline.encode("utf-8")).hexdigest()
    candidate = baseline.replace('    return 0\n', '    # bounded change\n    return 0\n')
    if validate_prewrite_python(baseline, candidate, expected_sha256=sha,
                                max_added=1, max_removed=0) != (1, 0):
        raise ValidationFailure("prewrite positive control failed")
    with_comment = baseline.replace('    return 0\n', '    # removable\n    return 0\n')
    overlong = "# bounded fixture\n" * (PREWRITE_MAX_SOURCE_LINES + 1) + baseline
    dense_baseline = "# repeated\n" * 800 + baseline
    unexecutable = baseline.replace('if __name__', 'return 1\nif __name__')
    # Module-scope checks must not reject deferred or local main bindings.
    local_controls = (
        ("function default benign", 'def helper(x=1):\n    pass\n', (2, 0)),
        ("function annotations benign", 'def helper(x: int) -> str:\n    return str(x)\n', (2, 0)),
        ("function local", 'def helper():\n    main = 1\n', (2, 0)),
        ("class method deferred reflection", 'class Helper:\n    def method(self):\n        globals()["main"] = 1\n', (3, 0)),
        ("safe explicit import", 'from math import sqrt\n', (1, 0)),
        ("unrelated constant setattr", 'setattr(module, "other", 1)\n', (1, 0)),
        ("unrelated module dict update", 'module.__dict__.update({"other": 1})\n', (1, 0)),
        ("unrelated module dict pop", 'module.__dict__.pop("other")\n', (1, 0)),
        ("class local", 'class Helper:\n    main = 1\n', (2, 0)),
        ("class conditional local", 'class Helper:\n    if True:\n        main = 1\n', (3, 0)),
        ("class method named main", 'class Helper:\n    def main(self):\n        pass\n', (3, 0)),
        ("nested class named main", 'class Helper:\n    class main:\n        pass\n', (3, 0)),
        ("lambda local", 'helper = lambda main: main\n', (1, 0)),
        ("comprehension local", 'items = [main for main in (1,)]\n', (1, 0)),
        ("deferred generator reflection", 'items = (globals().__setitem__("main", None) for _ in (1,))\n', (1, 0)),
        ("function-local attribute", 'def helper():\n    module.main = 1\n', (2, 0)),
        ("function-local reflection", 'def helper():\n    globals()["other"] = 1\n', (2, 0)),
        ("deferred lambda reflection", 'helper = lambda: globals()["other"]\n', (1, 0)),
        ("deferred lambda main reflection", 'helper = lambda: globals().__setitem__("main", None)\n', (1, 0)),
        ("deferred dynamic import", 'def helper():\n    importlib.import_module("math")\n', (2, 0)),
        ("deferred direct-name import", 'def helper():\n    import_module("math")\n', (2, 0)),
        ("deferred direct-name runpy", 'def helper():\n    run_module("math")\n', (2, 0)),
        ("deferred builtins exec", 'def helper():\n    builtins.exec("pass")\n', (2, 0)),
        ("deferred builtins eval", 'def helper():\n    builtins.eval("1")\n', (2, 0)),
        ("deferred module dict exec", 'def helper():\n    builtins.__dict__["exec"]("pass")\n', (2, 0)),
        ("deferred module dict import", 'def helper():\n    importlib.__dict__["import_module"]("math")\n', (2, 0)),
        ("deferred find_spec", 'def helper():\n    importlib.util.find_spec("samplepkg.child")\n', (2, 0)),
        ("deferred resolve_name", 'def helper():\n    pkgutil.resolve_name("samplepkg")\n', (2, 0)),
        ("deferred direct reload", 'def helper():\n    reload(importlib)\n', (2, 0)),
        ("deferred importlib reload", 'def helper():\n    importlib.reload(importlib)\n', (2, 0)),
        ("deferred loader execution", 'def helper():\n    loader.exec_module(None)\n', (2, 0)),
        ("deferred reflective import", 'def helper():\n    getattr(importlib, "import_module")("math")\n', (2, 0)),
        ("deferred computed reflective import", 'def helper():\n    getattr(importlib, "import_" + "module")("math")\n', (2, 0)),
        ("deferred qualified reflective import", 'def helper():\n    builtins.getattr(importlib, "import_module")("math")\n', (2, 0)),
        ("deferred attrgetter execution", 'def helper():\n    operator.attrgetter("import_module")(importlib)("math")\n', (2, 0)),
        ("deferred methodcaller execution", 'def helper():\n    operator.methodcaller("import_module", "math")(importlib)\n', (2, 0)),
        ("deferred operator call", 'def helper():\n    operator.call(exec, "main = None")\n', (2, 0)),
        ("lazy map construction", 'pending = map(exec, ["main = None"])\n', (1, 0)),
        ("deferred map consumption", 'def helper():\n    list(map(exec, ["main = None"]))\n', (2, 0)),
        ("deferred map generator", 'pending = (x for x in map(exec, ["main = None"]))\n', (1, 0)),
        ("deferred nested generator consumer", 'def helper():\n    list(x for x in map(exec, ["main = None"]))\n', (2, 0)),
        ("decorator lambda local main", '@(lambda fn: (main := fn))\ndef helper():\n    pass\n', (3, 0)),
    )
    for label, insertion, expected in local_controls:
        scoped = baseline.replace('if __name__', insertion + 'if __name__')
        observed = validate_prewrite_python(
            baseline, scoped, expected_sha256=sha, max_added=4, max_removed=0
        )
        if observed != expected:
            raise ValidationFailure("prewrite scope positive control failed: " + label)
    cases = (
        ("dense repeated lines", dense_baseline.replace(
            '    return 0\n', '    # edit\n    return 0\n'),
         hashlib.sha256(dense_baseline.encode("utf-8")).hexdigest(), 40, 20,
         "line match density exceeds reviewed bound", dense_baseline),
        ("module return", unexecutable, sha, 40, 20,
         "candidate Python compilation invalid", baseline),
        ("module break", baseline.replace(
            'if __name__', 'break\nif __name__'), sha, 40, 20,
         "candidate Python compilation invalid", baseline),
        ("module nonlocal", baseline.replace(
            'if __name__', 'nonlocal x\nif __name__'), sha, 40, 20,
         "candidate Python compilation invalid", baseline),
        ("unexecutable baseline", unexecutable.replace(
            '    return 0\n', '    # edit\n    return 0\n'),
         hashlib.sha256(unexecutable.encode("utf-8")).hexdigest(), 40, 20,
         "baseline Python compilation invalid", unexecutable),
        ("overlong candidate", overlong, sha, 40, 20,
         "candidate Python line count exceeds reviewed bound", baseline),
        ("overlong baseline", overlong.replace("    return 0\n", "    # edit\n    return 0\n"),
         hashlib.sha256(overlong.encode("utf-8")).hexdigest(), 40, 20,
         "baseline Python line count exceeds reviewed bound", overlong),
        ("unchanged", baseline, sha, 40, 20, "no changes", baseline),
        ("bad baseline hash", candidate, "0" * 64, 40, 20, "SHA-256 mismatch", baseline),
        ("syntax", baseline + 'def broken(:\n', sha, 40, 20, "syntax invalid", baseline),
        ("duplicate main", baseline + '\ndef main():\n    pass\n', sha, 40, 20, "one sync main", baseline),
        ("removed guard", baseline.replace('    raise SystemExit(main())\n',
                                           '    pass\n'), sha, 40, 20, "live main guard", baseline),
        ("added overflow", baseline.replace('    return 0\n',
              '    # a\n    # b\n    return 0\n'), sha, 1, 20, "diff exceeds", baseline),
        ("removed overflow", baseline, hashlib.sha256(with_comment.encode("utf-8")).hexdigest(),
         40, 0, "diff exceeds", with_comment),
        ("budget too large", candidate, sha, 81, 20, "outside reviewed bounds", baseline),
        ("eager builtin dynamic import", baseline.replace(
            'if __name__', '__import__("math")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager importlib dynamic import", baseline.replace(
            'if __name__', 'importlib.import_module("math")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager runpy path", baseline.replace(
            'if __name__', 'runpy.run_path("fixture.py")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager runpy module", baseline.replace(
            'if __name__', 'runpy.run_module("math")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager direct-name import", baseline.replace(
            'if __name__', 'import_module("math")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager direct-name runpy module", baseline.replace(
            'if __name__', 'run_module("math")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager direct-name runpy path", baseline.replace(
            'if __name__', 'run_path("fixture.py")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("qualified import", baseline.replace(
            'if __name__', 'builtins.__import__("math")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("qualified exec", baseline.replace(
            'if __name__', 'builtins.exec("pass")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("qualified eval", baseline.replace(
            'if __name__', 'builtins.eval("1")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("module dict exec execution", baseline.replace(
            'if __name__', "builtins.__dict__[\"exec\"](\"pass\")\nif __name__"),
         sha, 40, 20, "main binding shadowed", baseline),
        ("module dict import execution", baseline.replace(
            'if __name__', "importlib.__dict__[\"import_module\"](\"math\")\nif __name__"),
         sha, 40, 20, "main binding shadowed", baseline),
        ("vars dict eval execution", baseline.replace(
            'if __name__', "vars(builtins)[\"eval\"](\"1\")\nif __name__"),
         sha, 40, 20, "main binding shadowed", baseline),
        ("dunder builtins import execution", baseline.replace(
            'if __name__', "__builtins__[\"__import__\"](\"math\")\nif __name__"),
         sha, 40, 20, "main binding shadowed", baseline),
        ("direct exec", baseline.replace(
            'if __name__', 'exec("pass")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("direct eval", baseline.replace(
            'if __name__', 'eval("1")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("reflective exec", baseline.replace(
            'if __name__', 'getattr(builtins, "exec")("pass")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("reflective eval", baseline.replace(
            'if __name__', 'getattr(builtins, "eval")("1")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager direct find_spec", baseline.replace(
            'if __name__', 'find_spec("samplepkg.child")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager attribute find_spec", baseline.replace(
            'if __name__', 'importlib.util.find_spec("samplepkg.child")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager reflective find_spec", baseline.replace(
            'if __name__', 'getattr(importlib.util, "find_spec")("samplepkg.child")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager direct resolve_name", baseline.replace(
            'if __name__', 'resolve_name("samplepkg")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager attribute resolve_name", baseline.replace(
            'if __name__', 'pkgutil.resolve_name("samplepkg")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager reflective resolve_name", baseline.replace(
            'if __name__', 'getattr(pkgutil, "resolve_name")("samplepkg")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager direct reload", baseline.replace(
            'if __name__', 'reload(importlib)\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager importlib reload", baseline.replace(
            'if __name__', 'importlib.reload(importlib)\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager reflective reload", baseline.replace(
            'if __name__', 'getattr(importlib, "reload")(importlib)\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager loader exec_module", baseline.replace(
            'if __name__', 'loader.exec_module(None)\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager reflective import_module", baseline.replace(
            'if __name__', 'getattr(importlib, "import_module")("math")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager reflective builtin import", baseline.replace(
            'if __name__', 'getattr(builtins, "__import__")("math")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager computed reflective import", baseline.replace(
            'if __name__', 'getattr(importlib, "import_" + "module")("math")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager dynamic reflective loader", baseline.replace(
            'if __name__', 'getattr(loader, method)(None)\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager qualified reflective import", baseline.replace(
            'if __name__', 'builtins.getattr(importlib, "import_module")("math")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager qualified computed reflection", baseline.replace(
            'if __name__', 'builtins.getattr(loader, method)(None)\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager operator attrgetter execution", baseline.replace(
            'if __name__', 'operator.attrgetter("import_module")(importlib)("math")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager direct attrgetter execution", baseline.replace(
            'if __name__', 'attrgetter("import_module")(importlib)("math")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager operator methodcaller execution", baseline.replace(
            'if __name__', 'operator.methodcaller("import_module", "math")(importlib)\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager operator call exec", baseline.replace(
            'if __name__', 'operator.call(exec, "main = None")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager direct call exec", baseline.replace(
            'if __name__', 'call(exec, "main = None")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager mapped exec list", baseline.replace(
            'if __name__', 'list(map(exec, ["main = None"]))\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager mapped exec next", baseline.replace(
            'if __name__', 'next(map(exec, ["main = None"]))\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager mapped exec for", baseline.replace(
            'if __name__', 'for _ in map(exec, ["main = None"]):\n    pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager mapped exec comprehension", baseline.replace(
            'if __name__', '[x for x in map(exec, ["main = None"])]\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager nested mapped exec list", baseline.replace(
            'if __name__', 'list(x for x in map(exec, ["main = None"]))\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager nested mapped exec next", baseline.replace(
            'if __name__', 'next(x for x in map(exec, ["main = None"]))\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("eager direct methodcaller execution", baseline.replace(
            'if __name__', 'methodcaller("import_module", "math")(importlib)\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("module wildcard import", baseline.replace(
            'if __name__', 'from math import *\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("class conditional reflection", baseline.replace(
            'if __name__', 'class Helper:\n    if True:\n        globals().__setitem__("main", None)\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("class for reflection", baseline.replace(
            'if __name__', 'class Helper:\n    for _ in (1,):\n        globals().__setitem__("main", None)\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("class try reflection", baseline.replace(
            'if __name__', 'class Helper:\n    try:\n        globals().__setitem__("main", None)\n    except Exception:\n        pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("class global declaration", baseline.replace(
            'if __name__', 'class Helper:\n    global main\n    main = None\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("class method decorator reflection", baseline.replace(
            'if __name__', 'class Helper:\n    @globals().__setitem__("main", None)\n    def method(self):\n        pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("function parameter annotation reflection", baseline.replace(
            'if __name__', 'def helper(x: globals().__setitem__("main", None)):\n    pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("function return annotation reflection", baseline.replace(
            'if __name__', 'def helper() -> globals().__setitem__("main", None):\n    pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("function kwonly annotation reflection", baseline.replace(
            'if __name__', 'def helper(*, x: globals().__setitem__("main", None)):\n    pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("async parameter annotation reflection", baseline.replace(
            'if __name__', 'async def helper(x: globals().__setitem__("main", None)):\n    pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("function lambda decorator reflection", baseline.replace(
            'if __name__', '@(lambda fn: globals().__setitem__("main", None))\ndef helper():\n    pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("class lambda decorator reflection", baseline.replace(
            'if __name__', '@(lambda cls: globals().__setitem__("main", None))\nclass Helper:\n    pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("class method lambda decorator reflection", baseline.replace(
            'if __name__', 'class Helper:\n    @(lambda fn: globals().__setitem__("main", None))\n    def method(self):\n        pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("class decorator reflection", baseline.replace(
            'if __name__', '@globals().__setitem__("main", None)\nclass Helper:\n    pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("class base reflection", baseline.replace(
            'if __name__', 'class Helper(globals().__setitem__("main", None) or object):\n    pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("class assignment value reflection", baseline.replace(
            'if __name__', 'class Helper:\n    main = globals().__setitem__("main", None)\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("class expression reflection", baseline.replace(
            'if __name__', 'class Helper:\n    globals().__setitem__("main", None)\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("function decorator reflection", baseline.replace(
            'if __name__', '@globals().__setitem__("main", None)\ndef helper():\n    pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("function positional default reflection", baseline.replace(
            'if __name__', 'def helper(x=globals().__setitem__("main", None)):\n    pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("function keyword default reflection", baseline.replace(
            'if __name__', 'def helper(*, x=vars().__setitem__("main", None)):\n    pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("async function default reflection", baseline.replace(
            'if __name__', 'async def helper(x=globals().__setitem__("main", None)):\n    pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("list comprehension reflection", baseline.replace(
            'if __name__', 'items = [globals().__setitem__("main", None) for _ in (1,)]\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("set comprehension reflection", baseline.replace(
            'if __name__', 'items = {vars().__setitem__("main", None) for _ in (1,)}\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("dict comprehension reflection", baseline.replace(
            'if __name__', 'items = {x: globals().__setitem__("main", None) for x in (1,)}\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("generator eager iterable reflection", baseline.replace(
            'if __name__', 'items = (x for x in globals().__setitem__("main", None) or (1,))\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("module attribute main shadow", baseline.replace(
            'if __name__', 'module.main = lambda: 1\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("module subscript main shadow", baseline.replace(
            'if __name__', 'namespace["main"] = lambda: 1\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("module setattr main shadow", baseline.replace(
            'if __name__', 'setattr(module, "main", lambda: 1)\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("dynamic setattr main shadow", baseline.replace(
            'if __name__', 'attribute = "main"\nsetattr(module, attribute, None)\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("dynamic delattr main shadow", baseline.replace(
            'if __name__', 'attribute = "main"\ndelattr(module, attribute)\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("module dict update main", baseline.replace(
            'if __name__', 'module.__dict__.update({"main": None})\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("module dict update computed", baseline.replace(
            'if __name__', 'module.__dict__.update({attribute: None})\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("module dict pop main", baseline.replace(
            'if __name__', 'module.__dict__.pop("main")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("module dict clear", baseline.replace(
            'if __name__', 'module.__dict__.clear()\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("module dict setdefault main", baseline.replace(
            'if __name__', 'module.__dict__.setdefault("main", None)\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("module dict setitem dynamic", baseline.replace(
            'if __name__', 'module.__dict__.__setitem__(attribute, None)\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("module delattr main shadow", baseline.replace(
            'if __name__', 'delattr(module, "main")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("reflective globals shadow", baseline.replace(
            'if __name__', 'globals()["main"] = lambda: 1\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("reflective vars shadow", baseline.replace(
            'if __name__', 'vars()["main"] = lambda: 1\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("reflective exec shadow", baseline.replace(
            'if __name__', 'exec("main = lambda: 1")\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("immediate lambda shadow", baseline.replace(
            'if __name__', '(lambda: globals().__setitem__("main", None))()\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("conditional main shadow", baseline.replace(
            'if __name__', 'if True:\n    main = lambda: 1\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("for-loop main shadow", baseline.replace(
            'if __name__', 'for main in (1,):\n    pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("with-as main shadow", baseline.replace(
            'if __name__', 'with open(__file__) as main:\n    pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("except-as main shadow", baseline.replace(
            'if __name__', 'try:\n    raise ValueError()\nexcept ValueError as main:\n    pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("match-capture main shadow", baseline.replace(
            'if __name__', 'match 1:\n    case main:\n        pass\nif __name__'),
         sha, 40, 20, "main binding shadowed", baseline),
        ("assigned main shadow", baseline.replace(
            'if __name__', 'main = lambda: 1\nif __name__'), sha, 40, 20,
         "main binding shadowed", baseline),
        ("destructured main shadow", baseline.replace(
            'if __name__', '(other, main) = (1, 2)\nif __name__'), sha, 40, 20,
         "main binding shadowed", baseline),
        ("imported main shadow", baseline.replace(
            'if __name__', 'import os as main\nif __name__'), sha, 40, 20,
         "main binding shadowed", baseline),
        ("class main shadow", baseline.replace(
            'if __name__', 'class main: pass\nif __name__'), sha, 40, 20,
         "main binding shadowed", baseline),
        ("deleted main shadow", baseline.replace(
            'if __name__', 'del main\nif __name__'), sha, 40, 20,
         "main binding shadowed", baseline),
    )
    for label, changed, expected, add, remove, diagnostic, original in cases:
        try:
            validate_prewrite_python(original, changed, expected_sha256=expected,
                                     max_added=add, max_removed=remove)
        except ValidationFailure as exc:
            if diagnostic not in str(exc):
                raise ValidationFailure("prewrite wrong diagnostic: " + label) from exc
        else:
            raise ValidationFailure("prewrite negative accepted: " + label)


def validate_prewrite_files(baseline_path: Path, candidate_path: Path,
                            expected_sha256: str, max_added: int,
                            max_removed: int) -> tuple[int, int]:
    sources = []
    for path in (baseline_path, candidate_path):
        # A non-symlink leaf below a symlinked parent is still an alias.
        if any(part.is_symlink() for part in (path, *path.parents)) or not path.is_file():
            raise ValidationFailure("prewrite input missing or symlinked")
        if path.stat().st_size > PREWRITE_MAX_SOURCE_BYTES:
            raise ValidationFailure("prewrite input exceeds byte limit")
        try:
            raw = read_canonical_authority_bytes(
                path, PREWRITE_MAX_SOURCE_BYTES,
                too_large="prewrite input exceeds byte limit",
            )
            sources.append(raw.decode("utf-8"))
        except ValidationFailure as exc:
            if str(exc) == "prewrite input exceeds byte limit":
                raise
            raise ValidationFailure("prewrite input source identity unsafe") from None
        except UnicodeError:
            raise ValidationFailure("prewrite input unreadable or invalid UTF-8") from None
    return validate_prewrite_python(
        sources[0], sources[1], expected_sha256=expected_sha256,
        max_added=max_added, max_removed=max_removed,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--prewrite-baseline", type=Path)
    parser.add_argument("--prewrite-candidate", type=Path)
    parser.add_argument("--prewrite-baseline-sha256")
    parser.add_argument("--max-added-lines", type=int, default=40)
    parser.add_argument("--max-removed-lines", type=int, default=20)
    args = parser.parse_args()
    try:
        prewrite = (args.prewrite_baseline, args.prewrite_candidate,
                    args.prewrite_baseline_sha256)
        if any(value is not None for value in prewrite):
            if not all(value is not None for value in prewrite):
                raise ValidationFailure("prewrite requires baseline, candidate and SHA-256")
            added, removed = validate_prewrite_files(
                args.prewrite_baseline, args.prewrite_candidate,
                args.prewrite_baseline_sha256, args.max_added_lines,
                args.max_removed_lines,
            )
            print(f"Prewrite Python AST and diff-budget validation PASS: +{added} -{removed}")
            return 0
        # Resolving an explicit checkout alias before validation discards the
        # original path identity. Reject root and ancestor symlink aliases.
        root = args.repo_root.absolute()
        if root != args.repo_root.resolve():
            raise ValidationFailure("learning repository root alias forbidden")
        validate(root)
    except ValidationFailure as exc:
        print(f"AUTONOMOUS LEARNING VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"AUTONOMOUS LEARNING VALIDATION FAILED WITH UNEXPECTED ERROR: {exc}", file=sys.stderr)
        return 2
    print("Autonomous improvement/learning contract validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
