#!/usr/bin/env python3
"""Fail-closed validator for the autonomous improvement/learning contract."""

from __future__ import annotations

import argparse
import ast
import json
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


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing authority: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON: {path}: {exc}") from exc
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
        if path.is_symlink():
            raise ValidationFailure(f"symlinked learning authority forbidden: {relative}")
        try:
            resolved = path.resolve(strict=True).relative_to(repo_root.resolve(strict=True))
        except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
            raise ValidationFailure(f"learning authority path missing or escapes root: {relative}") from exc
        if resolved != relative:
            raise ValidationFailure(f"learning authority path substituted through parent: {relative}")
    contract = load_object(repo_root / CONTRACT)
    if contract.get("schemaVersion") != "autonomous-learning-system.0.1":
        raise ValidationFailure("unsupported schemaVersion")
    if contract.get("loop") != EXPECTED_LOOP:
        raise ValidationFailure("closed-loop execution order changed")
    exact_string_set(contract.get("requiredFailureFields"), FAILURE_FIELDS, "requiredFailureFields")
    exact_string_set(contract.get("requiredSuccessFields"), SUCCESS_FIELDS, "requiredSuccessFields")

    rules = contract.get("rules")
    if not isinstance(rules, dict):
        raise ValidationFailure("rules must be an object")
    for rule in TRUE_RULES:
        if rules.get(rule) is not True:
            raise ValidationFailure(f"mandatory learning rule must remain true: {rule}")

    protected = contract.get("protectedInvariants")
    if not isinstance(protected, dict):
        raise ValidationFailure("protectedInvariants must be an object")
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
        ci_entrypoint = (repo_root / CI_ENTRYPOINT).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationFailure(f"bound learning CI entrypoint is missing: {CI_ENTRYPOINT}") from exc
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
                    if any(isinstance(dec, ast.Lambda)
                           and binds(dec.body, class_local=class_local)
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
            if (isinstance(node, ast.Subscript)
                    and isinstance(node.ctx, (ast.Store, ast.Del))
                    and isinstance(node.slice, ast.Constant) and node.slice.value == name
                    and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id in {"globals", "vars", "locals"}
                    and not node.value.args and not node.value.keywords):
                return True
            if isinstance(node, ast.Call):
                # An immediately invoked lambda executes its body now, unlike
                # a bare lambda expression or a deferred generator body.
                if isinstance(node.func, ast.Lambda) and binds(
                    node.func.body, class_local=class_local
                ):
                    return True
                if isinstance(node.func, ast.Name) and node.func.id in {"exec", "eval"}:
                    if not node.args or not isinstance(node.args[0], ast.Constant):
                        return True
                    if not isinstance(node.args[0].value, str) or name in node.args[0].value:
                        return True
                if (isinstance(node.func, ast.Name)
                        and node.func.id in {"setattr", "delattr"}
                        and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant)
                        and node.args[1].value == name):
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
                return not class_local and any(
                    (alias.asname or (alias.name.split(".")[0] if isinstance(node, ast.Import) else alias.name))
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
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            eager = [*node.args.defaults,
                     *(value for value in node.args.kw_defaults if value is not None)]
            if not isinstance(node, ast.Lambda):
                eager.extend(node.decorator_list)
            return any(can_terminate_before_guard(value) for value in eager)
        if isinstance(node, (ast.Return, ast.Raise)):
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

    try:
        learning = (repo_root / LEARNING).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing learning authority: {LEARNING}") from exc
    for phrase in (
        "not production evidence",
        "Do not repeatedly retry an unchanged permission failure",
        "Repeating a known failed approach without changed preconditions is a regression",
        "Prefer executable guards over prose",
        "Human production-promotion review is a separate non-automatic decision",
    ):
        if phrase not in learning:
            raise ValidationFailure(f"learning authority lost invariant: {phrase}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        validate(args.repo_root.resolve())
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
