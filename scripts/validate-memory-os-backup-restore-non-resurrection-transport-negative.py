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








def require_typed_admission_main_reachability(tree: ast.Module) -> None:
    """Bind typed admission's first live guards and canonical registry loads."""
    require_typed_admission_main_binding(tree)
    main = next(node for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name == "main")
    body = main.body
    require(len(body) >= 7, "typed admission main authority sequence missing")
    first = body[0]
    require(isinstance(first, ast.If) and not first.orelse
            and isinstance(first.test, ast.Compare)
            and isinstance(first.test.left, ast.Name)
            and first.test.left.id == "enforce_execution_transport"
            and len(first.test.ops) == 1 and isinstance(first.test.ops[0], ast.IsNot)
            and len(first.test.comparators) == 1
            and isinstance(first.test.comparators[0], ast.Name)
            and first.test.comparators[0].id == "canonical_execution_guard"
            and len(first.body) == 1 and isinstance(first.body[0], ast.Raise)
            and isinstance(first.body[0].exc, ast.Call)
            and isinstance(first.body[0].exc.func, ast.Name)
            and first.body[0].exc.func.id == "Fail",
            "typed admission main must reject execution guard drift first")

    def direct_call(node: ast.AST, name: str) -> bool:
        return (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == name
                and not node.value.args and not node.value.keywords)

    require(direct_call(body[1], "enforce_execution_transport"),
            "typed admission main must execute transport guard second")
    require(direct_call(body[2], "enforce_runtime_authorities"),
            "typed admission main must execute runtime authorities third")

    def direct_load(node: ast.AST, target: str, source: str) -> bool:
        return (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == target
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "load"
                and len(node.value.args) == 1
                and isinstance(node.value.args[0], ast.Name)
                and node.value.args[0].id == source
                and not node.value.keywords)

    for index, target, source in (
        (3, "contract", "CONTRACT"),
        (4, "registry", "REGISTRY"),
        (5, "generation_contract", "GEN_CONTRACT"),
        (6, "generation_registry", "GEN_REGISTRY"),
    ):
        require(direct_load(body[index], target, source),
                f"typed admission main must directly load {source} in canonical order")


def prove_typed_admission_main_reachability() -> None:
    try:
        canonical = ast.parse(VALIDATOR.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise Fail("typed admission main reachability source unavailable") from exc
    require_typed_admission_main_reachability(canonical)
    cases = (
        ("guard-removed", "typed admission main must reject execution guard drift first"),
        ("guard-inverted", "typed admission main must reject execution guard drift first"),
        ("guard-dead", "typed admission main must reject execution guard drift first"),
        ("guard-swallowed", "typed admission main must reject execution guard drift first"),
        ("transport-removed", "typed admission main must execute transport guard second"),
        ("transport-dead", "typed admission main must execute transport guard second"),
        ("runtime-removed", "typed admission main must execute runtime authorities third"),
        ("runtime-dead", "typed admission main must execute runtime authorities third"),
        ("contract-removed", "typed admission main must directly load CONTRACT in canonical order"),
        ("registry-removed", "typed admission main must directly load REGISTRY in canonical order"),
        ("generation-contract-removed",
         "typed admission main must directly load GEN_CONTRACT in canonical order"),
        ("generation-registry-removed",
         "typed admission main must directly load GEN_REGISTRY in canonical order"),
        ("early-return", "typed admission main must reject execution guard drift first"),
        ("early-exit", "typed admission main must reject execution guard drift first"),
    )
    for label, expected in cases:
        mutated = copy.deepcopy(canonical)
        main = next(node for node in mutated.body
                    if isinstance(node, ast.FunctionDef) and node.name == "main")
        body = main.body
        if label == "guard-removed":
            body[0] = ast.Pass()
        elif label == "guard-inverted":
            body[0].test.ops = [ast.Is()]
        elif label == "guard-dead":
            body[0].test = ast.Constant(value=False)
        elif label == "guard-swallowed":
            body[0].body = [ast.Pass()]
        elif label == "transport-removed":
            body[1] = ast.Pass()
        elif label == "transport-dead":
            body[1] = ast.If(test=ast.Constant(value=False), body=[body[1]], orelse=[])
        elif label == "runtime-removed":
            body[2] = ast.Pass()
        elif label == "runtime-dead":
            body[2] = ast.If(test=ast.Constant(value=False), body=[body[2]], orelse=[])
        elif label == "contract-removed":
            body[3] = ast.Pass()
        elif label == "registry-removed":
            body[4] = ast.Pass()
        elif label == "generation-contract-removed":
            body[5] = ast.Pass()
        elif label == "generation-registry-removed":
            body[6] = ast.Pass()
        elif label == "early-return":
            body.insert(0, ast.Return(value=ast.Constant(value=0)))
        elif label == "early-exit":
            body.insert(0, ast.Expr(value=ast.Call(
                func=ast.Attribute(value=ast.Name(id="sys", ctx=ast.Load()),
                                   attr="exit", ctx=ast.Load()),
                args=[ast.Constant(value=0)], keywords=[])))
        try:
            require_typed_admission_main_reachability(mutated)
        except Fail as exc:
            require(str(exc) == expected,
                    f"typed admission main {label} reachability diagnostic drift")
        else:
            raise Fail(f"typed admission main {label} bypass unexpectedly accepted")
    print("PASS reject: fourteen typed admission main guard/registry reachability substitutions")



def require_typed_admission_child_reachability(tree: ast.Module) -> None:
    """Bind all five child validators after the typed registry/candidate gates."""
    require_typed_admission_main_reachability(tree)
    main = next(node for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name == "main")
    body = main.body
    expected = (
        ("LOCAL_APPLE_VALIDATOR", "local Apple replay restore validator"),
        ("LOCAL_COHERENT_VALIDATOR", "local coherent recovery-set validator"),
        ("NEGATIVE", "non-resurrection negative admission suite"),
        ("WRITER_AUTHORITY_NEGATIVE", "non-resurrection writer CLI authority negative suite"),
        ("PATH_NEGATIVE", "non-resurrection contract path negative suite"),
    )
    observed = []
    for index, stmt in enumerate(body):
        if (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                and isinstance(stmt.value.func, ast.Name)
                and stmt.value.func.id == "run_validator"):
            call = stmt.value
            require(len(call.args) == 2 and not call.keywords
                    and isinstance(call.args[0], ast.Name)
                    and isinstance(call.args[1], ast.Constant)
                    and isinstance(call.args[1].value, str),
                    "typed admission child invocation binding drift")
            observed.append((index, call.args[0].id, call.args[1].value))
    require(tuple((path, label) for _, path, label in observed) == expected,
            "typed admission must invoke five canonical child validators in order")

    registry_check_index = next((index for index, stmt in enumerate(body)
        if isinstance(stmt, ast.Try) and any(
            isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "validate_registry_for_append"
            for node in ast.walk(stmt))), -1)
    boundary_index = next((index for index, stmt in enumerate(body)
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
        and isinstance(stmt.targets[0], ast.Name)
        and stmt.targets[0].id == "boundary"), -1)
    indices = [item[0] for item in observed]
    require(0 <= registry_check_index < indices[0] < indices[1]
            < boundary_index < indices[2] < indices[3] < indices[4],
            "typed admission child validation must follow canonical gate order")
    require(indices[1] == indices[0] + 1
            and indices[3] == indices[2] + 1
            and indices[4] == indices[3] + 1,
            "typed admission child validator calls must remain consecutive")
    require(isinstance(body[-1], ast.Return)
            and isinstance(body[-1].value, ast.Constant)
            and type(body[-1].value.value) is int and body[-1].value.value == 0,
            "typed admission main must terminate after child validators")
    for stmt in body[:-1]:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Return):
                raise Fail("typed admission main cannot return before child validators")
            if isinstance(node, ast.Call):
                func = node.func
                if (isinstance(func, ast.Name)
                        and func.id in ("exit", "quit", "exec", "eval", "SystemExit")):
                    raise Fail("typed admission main cannot terminate before child validators")
                if (isinstance(func, ast.Attribute)
                        and isinstance(func.value, ast.Name)
                        and (func.value.id, func.attr) in (("sys", "exit"), ("os", "_exit"))):
                    raise Fail("typed admission main cannot terminate before child validators")


def prove_typed_admission_child_reachability() -> None:
    try:
        canonical = ast.parse(VALIDATOR.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise Fail("typed admission child reachability source unavailable") from exc
    require_typed_admission_child_reachability(canonical)
    cases = (
        ("missing-apple", "typed admission must invoke five canonical child validators in order"),
        ("missing-coherent", "typed admission must invoke five canonical child validators in order"),
        ("missing-negative", "typed admission must invoke five canonical child validators in order"),
        ("missing-writer", "typed admission must invoke five canonical child validators in order"),
        ("missing-path", "typed admission must invoke five canonical child validators in order"),
        ("swap-local", "typed admission must invoke five canonical child validators in order"),
        ("swap-negative", "typed admission must invoke five canonical child validators in order"),
        ("dead-negative", "typed admission must invoke five canonical child validators in order"),
        ("wrong-label", "typed admission must invoke five canonical child validators in order"),
        ("wrong-path", "typed admission must invoke five canonical child validators in order"),
        ("extra-child", "typed admission must invoke five canonical child validators in order"),
        ("early-negative", "typed admission child validation must follow canonical gate order"),
        ("nonconsecutive-local", "typed admission child validator calls must remain consecutive"),
        ("early-return", "typed admission main cannot return before child validators"),
        ("nested-return", "typed admission main cannot return before child validators"),
        ("early-sys-exit", "typed admission main cannot terminate before child validators"),
        ("early-os-exit", "typed admission main cannot terminate before child validators"),
        ("early-exec", "typed admission main cannot terminate before child validators"),
        ("early-system-exit", "typed admission main cannot terminate before child validators"),
        ("wrong-final-return", "typed admission main must terminate after child validators"),
    )
    for label, expected in cases:
        mutated = copy.deepcopy(canonical)
        main = next(node for node in mutated.body
                    if isinstance(node, ast.FunctionDef) and node.name == "main")
        body = main.body
        call_indices = [index for index, stmt in enumerate(body)
                        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                        and isinstance(stmt.value.func, ast.Name)
                        and stmt.value.func.id == "run_validator"]
        if label.startswith("missing-"):
            target = {"missing-apple": 0, "missing-coherent": 1,
                      "missing-negative": 2, "missing-writer": 3, "missing-path": 4}[label]
            body[call_indices[target]] = ast.Pass()
        elif label == "swap-local":
            i, j = call_indices[:2]; body[i], body[j] = body[j], body[i]
        elif label == "swap-negative":
            i, j = call_indices[2:4]; body[i], body[j] = body[j], body[i]
        elif label == "dead-negative":
            i = call_indices[2]
            body[i] = ast.If(test=ast.Constant(value=False), body=[body[i]], orelse=[])
        elif label == "wrong-label":
            body[call_indices[0]].value.args[1] = ast.Constant(value="not canonical")
        elif label == "wrong-path":
            body[call_indices[4]].value.args[0] = ast.Name(id="NEGATIVE", ctx=ast.Load())
        elif label == "extra-child":
            body.insert(call_indices[4] + 1, copy.deepcopy(body[call_indices[4]]))
        elif label == "early-negative":
            block = [body[i] for i in call_indices[2:]]
            for i in reversed(call_indices[2:]):
                body.pop(i)
            body[call_indices[1] + 1:call_indices[1] + 1] = block
        elif label == "nonconsecutive-local":
            body.insert(call_indices[1], ast.Pass())
        elif label == "early-return":
            body.insert(call_indices[2], ast.Return(value=ast.Constant(value=0)))
        elif label == "nested-return":
            body.insert(call_indices[2], ast.If(test=ast.Constant(value=True),
                        body=[ast.Return(value=ast.Constant(value=0))], orelse=[]))
        elif label in ("early-sys-exit", "early-os-exit", "early-exec", "early-system-exit"):
            source = {
                "early-sys-exit": "sys.exit(0)",
                "early-os-exit": "os._exit(0)",
                "early-exec": "exec('exit(0)')",
                "early-system-exit": "raise SystemExit(0)",
            }[label]
            body.insert(call_indices[2], ast.parse(source).body[0])
        elif label == "wrong-final-return":
            body[-1].value = ast.Constant(value=1)
        try:
            require_typed_admission_child_reachability(mutated)
        except Fail as exc:
            require(str(exc) == expected,
                    f"typed admission child {label} diagnostic drift: {exc}")
        else:
            raise Fail(f"typed admission child {label} bypass unexpectedly accepted")
    print("PASS reject: twenty typed admission child validation reachability substitutions")



def require_typed_admission_candidate_derivation(tree: ast.Module) -> None:
    """Bind final recovery candidates to base eligibility AND complete typed coverage."""
    main = next(node for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name == "main")
    body = main.body
    expressions = (
        ("base_candidate_ids", '{row.get("evidenceId") for row in generation_rows if generation_writer.base_candidate(row)}'),
        ("final_candidate_ids", '{row.get("evidenceId") for row in generation_rows if generation_writer.candidate(row)}'),
        ("complete_typed_ids", '{row.get("generationEvidenceId") for row in rows if row.get("evidenceComplete") is True}'),
        ("covered_base_ids", 'base_candidate_ids & complete_typed_ids'),
        ("pending_typed_ids", 'base_candidate_ids - complete_typed_ids'),
        ("generation_candidate_count", 'generation_registry.get("productionEquivalentRecoveryCandidateCount")'),
    )
    gate_expressions = (
        ("final candidate derivation bypasses typed non-resurrection coverage", "final_candidate_ids == covered_base_ids"),
        ("candidateCoveredCount drift", "covered_count == len(covered_base_ids)"),
        ("generation registry final candidate count drift", "generation_candidate_count == len(final_candidate_ids)"),
    )
    locations = {}
    for name, source in expressions:
        matches = [(index, stmt) for index, stmt in enumerate(body)
                   if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                   and isinstance(stmt.targets[0], ast.Name)
                   and stmt.targets[0].id == name]
        require(len(matches) == 1 and ast.dump(matches[0][1].value) == ast.dump(ast.parse(source, mode="eval").body),
                f"typed candidate derivation {name} drift")
        locations[name] = matches[0][0]
    for message, source in gate_expressions:
        matches = [(index, stmt) for index, stmt in enumerate(body)
                   if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                   and isinstance(stmt.value.func, ast.Name) and stmt.value.func.id == "require"
                   and len(stmt.value.args) == 2 and isinstance(stmt.value.args[1], ast.Constant)
                   and stmt.value.args[1].value == message]
        require(len(matches) == 1 and not matches[0][1].value.keywords
                and ast.dump(matches[0][1].value.args[0]) == ast.dump(ast.parse(source, mode="eval").body),
                f"typed candidate gate {message} drift")
        locations[message] = matches[0][0]
    ordered = (
        "base_candidate_ids", "final_candidate_ids", "complete_typed_ids",
        "covered_base_ids", "pending_typed_ids",
        "final candidate derivation bypasses typed non-resurrection coverage",
        "candidateCoveredCount drift", "generation_candidate_count",
        "generation registry final candidate count drift",
    )
    require(all(locations[a] < locations[b] for a, b in zip(ordered, ordered[1:])),
            "typed candidate derivation and coverage gates must retain canonical order")


def prove_typed_admission_candidate_derivation() -> None:
    try:
        canonical = ast.parse(VALIDATOR.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise Fail("typed candidate derivation source unavailable") from exc
    require_typed_admission_candidate_derivation(canonical)
    cases = (
        ("base-bypass", "typed candidate derivation base_candidate_ids drift"),
        ("final-bypass", "typed candidate derivation final_candidate_ids drift"),
        ("typed-completeness-bypass", "typed candidate derivation complete_typed_ids drift"),
        ("coverage-union", "typed candidate derivation covered_base_ids drift"),
        ("pending-coverage-bypass", "typed candidate derivation pending_typed_ids drift"),
        ("candidate-count-bypass", "typed candidate derivation generation_candidate_count drift"),
        ("missing-final-gate", "typed candidate gate final candidate derivation bypasses typed non-resurrection coverage drift"),
        ("weakened-final-gate", "typed candidate gate final candidate derivation bypasses typed non-resurrection coverage drift"),
        ("missing-coverage-count-gate", "typed candidate gate candidateCoveredCount drift drift"),
        ("weakened-coverage-count-gate", "typed candidate gate candidateCoveredCount drift drift"),
        ("missing-generation-count-gate", "typed candidate gate generation registry final candidate count drift drift"),
        ("weakened-generation-count-gate", "typed candidate gate generation registry final candidate count drift drift"),
        ("duplicate-final-gate", "typed candidate gate final candidate derivation bypasses typed non-resurrection coverage drift"),
        ("late-final-gate", "typed candidate derivation and coverage gates must retain canonical order"),
    )
    for label, expected in cases:
        mutated = copy.deepcopy(canonical)
        main = next(node for node in mutated.body
                    if isinstance(node, ast.FunctionDef) and node.name == "main")
        body = main.body
        assignments = {stmt.targets[0].id: (i, stmt)
                       for i, stmt in enumerate(body)
                       if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                       and isinstance(stmt.targets[0], ast.Name)}
        gates = {stmt.value.args[1].value: (i, stmt)
                 for i, stmt in enumerate(body)
                 if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                 and isinstance(stmt.value.func, ast.Name) and stmt.value.func.id == "require"
                 and len(stmt.value.args) == 2 and isinstance(stmt.value.args[1], ast.Constant)
                 and isinstance(stmt.value.args[1].value, str)}
        assignment_targets = {
            "base-bypass": "base_candidate_ids", "final-bypass": "final_candidate_ids",
            "typed-completeness-bypass": "complete_typed_ids", "coverage-union": "covered_base_ids",
            "pending-coverage-bypass": "pending_typed_ids", "candidate-count-bypass": "generation_candidate_count",
        }
        gate_targets = {
            "final": "final candidate derivation bypasses typed non-resurrection coverage",
            "coverage": "candidateCoveredCount drift",
            "generation": "generation registry final candidate count drift",
        }
        if label in assignment_targets:
            assignments[assignment_targets[label]][1].value = ast.Constant(value=0)
        elif label.startswith("missing-") or label.startswith("weakened-"):
            key = "final" if "final-gate" in label else "coverage" if "coverage-count" in label else "generation"
            i, stmt = gates[gate_targets[key]]
            if label.startswith("missing-"):
                body[i] = ast.Pass()
            else:
                stmt.value.args[0] = ast.Constant(value=True)
        elif label == "duplicate-final-gate":
            i, stmt = gates[gate_targets["final"]]
            body.insert(i + 1, copy.deepcopy(stmt))
        elif label == "late-final-gate":
            i, stmt = gates[gate_targets["final"]]
            body.pop(i)
            after = next(j for j, n in enumerate(body)
                         if isinstance(n, ast.Assign) and len(n.targets) == 1
                         and isinstance(n.targets[0], ast.Name)
                         and n.targets[0].id == "generation_candidate_count")
            body.insert(after + 1, stmt)
        try:
            require_typed_admission_candidate_derivation(mutated)
        except Fail as exc:
            require(str(exc) == expected,
                    f"typed candidate {label} diagnostic drift: {exc}")
        else:
            raise Fail(f"typed candidate {label} bypass unexpectedly accepted")
    print("PASS reject: fourteen typed candidate derivation and coverage-gate substitutions")


def require_no_typed_pre_dispatch_exit(tree: ast.Module) -> None:
    """Reject eager termination before the typed admission CLI dispatch."""
    require_typed_admission_cli_dispatch(tree)

    def terminates_during_import(node: ast.AST) -> bool:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            eager = [*node.decorator_list, *node.args.defaults,
                     *(value for value in node.args.kw_defaults if value is not None)]
            return any(terminates_during_import(value) for value in eager)
        if isinstance(node, ast.Lambda):
            eager = [*node.args.defaults,
                     *(value for value in node.args.kw_defaults if value is not None)]
            return any(terminates_during_import(value) for value in eager)
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
            "typed admission module can terminate before CLI dispatch")


def prove_typed_pre_dispatch_exit() -> None:
    try:
        canonical = ast.parse(VALIDATOR.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise Fail("typed admission pre-dispatch source unavailable") from exc
    require_no_typed_pre_dispatch_exit(canonical)
    nl = chr(10)
    mutations = (
        ("raise", "raise SystemExit(0)"),
        ("sys-exit", "sys.exit(0)"),
        ("os-exit", "os._exit(0)"),
        ("exit", "exit(0)"),
        ("quit", "quit()"),
        ("branch", "if True:" + nl + "    raise SystemExit(0)"),
        ("try", "try:" + nl + "    sys.exit(0)" + nl
         + "except Exception:" + nl + "    pass"),
        ("exec", "exec('raise SystemExit(0)')"),
        ("eval", "eval('exit(0)')"),
        ("class-exit", "class Early:" + nl + "    sys.exit(0)"),
        ("class-raise", "class Early:" + nl + "    raise SystemExit(0)"),
        ("decorator-exit", "@exit(0)" + nl + "def helper():" + nl + "    pass"),
        ("default-exit", "def helper(value=exit(0)):" + nl + "    pass"),
        ("class-base-exit", "class Early(exit(0)):" + nl + "    pass"),
        ("lambda-default-exit", "helper = lambda value=exit(0): value"),
    )
    for label, source in mutations:
        require(chr(92) + "n" not in source,
                f"typed pre-dispatch {label} fixture double-escaped newline")
        mutated = copy.deepcopy(canonical)
        try:
            mutated.body[-1:-1] = ast.parse(source).body
        except SyntaxError as exc:
            raise Fail(f"typed pre-dispatch {label} fixture invalid Python") from exc
        try:
            require_no_typed_pre_dispatch_exit(mutated)
        except Fail as exc:
            require(str(exc) == "typed admission module can terminate before CLI dispatch",
                    f"typed pre-dispatch {label} rejection diagnostic drift")
        else:
            raise Fail(f"typed pre-dispatch {label} termination unexpectedly accepted")
    print("PASS reject: fifteen typed admission pre-dispatch eager termination substitutions")


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
    prove_typed_admission_main_reachability()
    prove_typed_admission_child_reachability()
    prove_typed_admission_candidate_derivation()
    prove_typed_pre_dispatch_exit()
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
