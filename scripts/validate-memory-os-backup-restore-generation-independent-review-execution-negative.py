#!/usr/bin/env python3
"""Focused negative for final-candidate independent-review execution authority."""

from __future__ import annotations

import ast
import copy
import importlib.util
import re
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-independent-review.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator() -> Any:
    require(VALIDATOR.is_file() and not VALIDATOR.is_symlink(), "canonical independent-review validator missing or symlinked")
    require(VALIDATOR.resolve(strict=True).relative_to(ROOT.resolve()) == Path("scripts/validate-memory-os-backup-restore-generation-independent-review.py"), "canonical independent-review validator path drift")
    spec = importlib.util.spec_from_file_location("memory_os_generation_independent_review_execution_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load independent-review validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    mains = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name == "main"]
    require(len(proofs) == 1 and len(mains) == 1,
            "candidate pair negative harness definition drift")
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == "prove_candidate_pair_source_binding"
                   for target in targets):
                raise Fail("candidate pair negative harness proof shadowed")
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
    )
    for label, action, expected in cases:
        mutant = copy.deepcopy(tree)
        main = next(node for node in mutant.body
                    if isinstance(node, ast.FunctionDef) and node.name == "main")
        proof = next(node for node in mutant.body
                     if isinstance(node, ast.FunctionDef)
                     and node.name == "prove_candidate_pair_source_binding")
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
        try:
            require_pair_negative_harness_binding(mutant)
        except Fail as exc:
            require(str(exc) == expected,
                    f"candidate pair harness mutation wrong diagnostic ({label}): {exc}")
        else:
            raise Fail(f"candidate pair harness mutation accepted: {label}")
    print(f"PASS: external candidate pair negative harness reachability rejects {len(cases)} bypasses")


def main() -> int:
    require_source_order_main_negative_proof()
    prove_pair_negative_harness_reachability()
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
