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


def load_object(path: Path) -> dict[str, Any]:
    """Read the learning contract with bounded, unambiguous JSON semantics."""
    if not path.is_file():
        raise ValidationFailure(f"missing authority: {path}")
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_LEARNING_CONTRACT_BYTES + 1)
    except OSError:
        raise ValidationFailure(f"unreadable authority: {path}") from None
    if len(raw) > MAX_LEARNING_CONTRACT_BYTES:
        raise ValidationFailure(f"oversized JSON authority: {path}")
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
        if path.is_symlink():
            raise ValidationFailure(f"symlinked learning authority forbidden: {relative}")
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

    prove_prewrite_python_negatives()
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
        def module_shadows_main(node: ast.AST, *, top_level: bool) -> bool:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return not top_level and node.name == "main"
            if isinstance(node, ast.ClassDef):
                return node.name == "main"
            if isinstance(node, (ast.Lambda, ast.ListComp, ast.SetComp,
                                 ast.DictComp, ast.GeneratorExp)):
                return False
            if (isinstance(node, ast.Name) and node.id == "main"
                    and isinstance(node.ctx, (ast.Store, ast.Del))):
                return True
            if isinstance(node, (ast.MatchAs, ast.MatchStar, ast.ExceptHandler)):
                if node.name == "main":
                    return True
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                return any(
                    (alias.asname or (alias.name.split(".")[0]
                                      if isinstance(node, ast.Import) else alias.name)) == "main"
                    for alias in node.names
                )
            return any(module_shadows_main(child, top_level=False)
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
        ("function local", 'def helper():\n    main = 1\n', (2, 0)),
        ("class local", 'class Helper:\n    main = 1\n', (2, 0)),
        ("lambda local", 'helper = lambda main: main\n', (1, 0)),
        ("comprehension local", 'items = [main for main in (1,)]\n', (1, 0)),
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
            sources.append(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as exc:
            raise ValidationFailure("prewrite input unreadable or invalid UTF-8") from exc
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
