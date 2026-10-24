#!/usr/bin/env python3
"""Prove typed non-resurrection authority loading and reconcile rollback fail closed."""

from __future__ import annotations

import ast
import copy
import importlib.util
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-non-resurrection-authority.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
TRANSPORT_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-transport-negative.py"
PATH_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-contract-path-negative.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def guarded_temporary_directory(prefix: str, parent: Path):
    require(PATH_NEGATIVE.is_file(), "typed contract path fixture guard missing")
    module = load_module(PATH_NEGATIVE, "memory_os_typed_path_fixture_guard_load")
    require(callable(getattr(module, "guarded_temporary_directory", None)),
            "typed contract path fixture guard callable missing")
    try:
        return module.guarded_temporary_directory(prefix, parent)
    except module.Fail as exc:
        raise Fail(str(exc)) from exc


def expect_domain_fail(name: str, action: Callable[[], object], fail_type: type[BaseException]) -> None:
    try:
        action()
    except fail_type:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def expect_direct_authority_rejected(
    reconciler: object,
    *,
    name: str,
    field: str,
    attribute: str,
    replacement: Path,
    before: dict[Path, bytes],
) -> None:
    original = getattr(reconciler, attribute)
    setattr(reconciler, attribute, replacement)
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require(f"{field} authority drift" in str(exc), f"{name} rejected at wrong boundary: {exc}")
        else:
            raise Fail(f"direct typed reconciler unexpectedly accepted: {name}")
        for path, expected in before.items():
            require(path.read_bytes() == expected, f"canonical authority mutated while rejecting {name}: {path.name}")
    finally:
        setattr(reconciler, attribute, original)


def prove_reconcile_runtime_authorities() -> None:
    require(RECONCILER.is_file(), "typed non-resurrection reconciler missing")
    reconciler = load_module(RECONCILER, "memory_os_typed_non_resurrection_reconcile_authority_negative")
    before = {path: path.read_bytes() for path in (REGISTRY, GEN_REGISTRY, CONTRACT, STATUS)}
    cases = (
        ("typed contract substitution", "typed non-resurrection contract", "CONTRACT", reconciler.STATUS),
        ("typed registry substitution", "typed non-resurrection registry", "REGISTRY", reconciler.GEN_REGISTRY),
        ("generation registry substitution", "generation evidence registry", "GEN_REGISTRY", reconciler.REGISTRY),
        ("typed writer substitution", "typed non-resurrection writer", "TYPED_WRITER", reconciler.GEN_WRITER),
        ("generation writer substitution", "generation evidence writer", "GEN_WRITER", reconciler.TYPED_WRITER),
        ("typed validator substitution", "typed non-resurrection validator", "VALIDATOR", reconciler.OPERABILITY_VALIDATOR),
        ("operability validator substitution", "operability validator", "OPERABILITY_VALIDATOR", reconciler.VALIDATOR),
        ("production status substitution", "production operability status", "STATUS", reconciler.CONTRACT),
    )
    for name, field, attribute, replacement in cases:
        expect_direct_authority_rejected(
            reconciler,
            name=name,
            field=field,
            attribute=attribute,
            replacement=replacement,
            before=before,
        )
    print(f"PASS boundary: direct typed data/writer/validator substitutions rejected: {len(cases)}")


def prove_reconcile_operability_rollback() -> None:
    require(RECONCILER.is_file(), "typed non-resurrection reconciler missing")
    reconciler = load_module(RECONCILER, "memory_os_typed_non_resurrection_reconcile_rollback_negative")
    with guarded_temporary_directory(".tmp-typed-reconcile-rollback-", TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        paths: dict[str, Path] = {}
        for attr in ("REGISTRY", "GEN_REGISTRY", "CONTRACT", "STATUS"):
            source = getattr(reconciler, attr)
            target = tmp / source.name
            shutil.copyfile(source, target)
            target.chmod(source.stat().st_mode & 0o7777)
            paths[attr] = target

        originals: dict[str, Any] = {attr: getattr(reconciler, attr) for attr in paths}
        originals["enforce_runtime_authorities"] = reconciler.enforce_runtime_authorities
        originals["run_post_validator"] = reconciler.run_post_validator
        before = {attr: path.read_bytes() for attr, path in paths.items()}
        before_modes = {attr: path.stat().st_mode & 0o7777 for attr, path in paths.items()}
        observed: list[str] = []

        def fail_only_aggregate_post_reconcile(path: Path, expected_relative: Path, label: str) -> None:
            observed.append(label)
            if len(observed) == 1:
                require(label == "typed non-resurrection validator", "typed validator was not first post-write validator")
                return
            require(len(observed) == 2, "unexpected extra typed post-write validator invocation")
            require(label == "operability validator", "operability validator was not second post-write validator")
            raise reconciler.Fail("synthetic typed aggregate operability rejection")

        try:
            # Production direct invocation is canonical-only. Fixture substitution
            # is enabled solely inside this harness to prove transactional rollback.
            reconciler.enforce_runtime_authorities = lambda: None
            for attr, path in paths.items():
                setattr(reconciler, attr, path)
            reconciler.run_post_validator = fail_only_aggregate_post_reconcile
            expect_domain_fail(
                "typed recovery operability aggregate failure",
                reconciler.main,
                reconciler.Fail,
            )
            require(observed == ["typed non-resurrection validator", "operability validator"], "typed post-write validator order drift")
            for attr, path in paths.items():
                require(path.read_bytes() == before[attr], f"{attr} bytes drift after operability rollback")
                require((path.stat().st_mode & 0o7777) == before_modes[attr], f"{attr} mode drift after operability rollback")
        finally:
            for attr, value in originals.items():
                setattr(reconciler, attr, value)

    print("PASS rollback: typed recovery authority restored exact bytes+mode after operability failure")



def require_typed_transport_guard_reachability(tree: ast.Module) -> None:
    """External proof that the typed transport negative suite executes its guards."""
    mains = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"]
    require(len(mains) == 1 and not mains[0].decorator_list,
            "typed transport negative must have one undecorated main")
    body = mains[0].body
    guards = (
        "prove_typed_admission_main_reachability",
        "prove_typed_admission_child_reachability",
        "prove_typed_admission_candidate_derivation",
        "prove_typed_admission_registry_validation",
        "prove_typed_pre_dispatch_exit",
        "prove_typed_admission_cli_dispatch",
        "prove_typed_admission_main_binding",
        "prove_validator_runner_binding",
    )
    def direct_call(stmt: ast.stmt, name: str, arguments: tuple[str, ...] = ()) -> bool:
        return (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                and isinstance(stmt.value.func, ast.Name) and stmt.value.func.id == name
                and len(stmt.value.args) == len(arguments) and not stmt.value.keywords
                and all(isinstance(arg, ast.Name) and arg.id == expected
                        for arg, expected in zip(stmt.value.args, arguments)))

    first = ast.parse('require(VALIDATOR.is_file() and not VALIDATOR.is_symlink(), "canonical typed validator missing or symlinked")').body[0]
    require(len(body) >= 13 and ast.dump(body[0]) == ast.dump(first),
            "typed transport negative must validate canonical validator before guards")
    for index, name in enumerate(guards, start=1):
        require(direct_call(body[index], name),
                f"typed transport negative must invoke {name} in canonical order")
    load = ast.parse("validator = load_validator()").body[0]
    require(ast.dump(body[9]) == ast.dump(load),
            "typed transport negative must load canonical validator after guards")
    require(direct_call(body[10], "exercise_validator_child_exit_propagation", ("validator",)),
            "typed transport negative must prove child exit propagation")
    calls = [(i, stmt) for i, stmt in enumerate(body)
             if direct_call(stmt, "exercise_registry_transaction_transport")
             or direct_call(stmt, "exercise_reconciler_transaction_transport")]
    require(len(calls) == 2 and direct_call(calls[0][1], "exercise_registry_transaction_transport")
            and direct_call(calls[1][1], "exercise_reconciler_transaction_transport")
            and calls[0][0] > 10 and calls[1][0] == calls[0][0] + 1,
            "typed transport negative must execute registry and reconcile transaction probes")
    parent_proofs = [(i, stmt) for i, stmt in enumerate(body)
                     if direct_call(stmt, "prove_typed_transport_fixture_parent_guard")]
    require(len(parent_proofs) == 1 and parent_proofs[0][0] == calls[1][0] + 1,
            "typed transport negative must execute checked fixture parent proof after transactions")
    require(isinstance(body[-1], ast.Return) and isinstance(body[-1].value, ast.Constant)
            and type(body[-1].value.value) is int and body[-1].value.value == 0,
            "typed transport negative must return only after its guards")
    for stmt in body[:-1]:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Return):
                raise Fail("typed transport negative cannot return before its guards")


def prove_typed_transport_guard_reachability() -> None:
    require(TRANSPORT_NEGATIVE.is_file() and not TRANSPORT_NEGATIVE.is_symlink(),
            "canonical typed transport negative source missing or symlinked")
    try:
        canonical = ast.parse(TRANSPORT_NEGATIVE.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise Fail("typed transport negative source unavailable") from exc
    require_typed_transport_guard_reachability(canonical)
    cases = (
        ("missing-main-guard", "typed transport negative must invoke prove_typed_admission_main_reachability in canonical order"),
        ("missing-child-guard", "typed transport negative must invoke prove_typed_admission_child_reachability in canonical order"),
        ("missing-candidate-guard", "typed transport negative must invoke prove_typed_admission_candidate_derivation in canonical order"),
        ("missing-registry-guard", "typed transport negative must invoke prove_typed_admission_registry_validation in canonical order"),
        ("swap-candidate-registry", "typed transport negative must invoke prove_typed_admission_candidate_derivation in canonical order"),
        ("dead-child-guard", "typed transport negative must invoke prove_typed_admission_child_reachability in canonical order"),
        ("missing-source-check", "typed transport negative must validate canonical validator before guards"),
        ("early-return", "typed transport negative must invoke prove_typed_admission_child_reachability in canonical order"),
        ("wrong-loader", "typed transport negative must load canonical validator after guards"),
        ("missing-child-exit", "typed transport negative must prove child exit propagation"),
        ("missing-registry-transport", "typed transport negative must execute registry and reconcile transaction probes"),
        ("missing-reconcile-transport", "typed transport negative must execute registry and reconcile transaction probes"),
        ("missing-parent-proof", "typed transport negative must execute checked fixture parent proof after transactions"),
        ("early-parent-proof", "typed transport negative must execute checked fixture parent proof after transactions"),
        ("wrong-final-return", "typed transport negative must return only after its guards"),
        ("nested-early-return", "typed transport negative cannot return before its guards"),
    )
    for label, expected in cases:
        mutated = copy.deepcopy(canonical)
        main = next(node for node in mutated.body
                    if isinstance(node, ast.FunctionDef) and node.name == "main")
        body = main.body
        if label.startswith("missing-") and label.endswith("-guard"):
            index = {"missing-main-guard": 1, "missing-child-guard": 2,
                     "missing-candidate-guard": 3, "missing-registry-guard": 4}[label]
            body[index] = ast.Pass()
        elif label == "swap-candidate-registry":
            body[3], body[4] = body[4], body[3]
        elif label == "dead-child-guard":
            body[2] = ast.If(test=ast.Constant(value=False), body=[body[2]], orelse=[])
        elif label == "missing-source-check":
            body[0] = ast.Pass()
        elif label == "early-return":
            body[2] = ast.Return(value=ast.Constant(value=0))
        elif label == "wrong-loader":
            body[9] = ast.parse("validator = None").body[0]
        elif label == "missing-child-exit":
            body[10] = ast.Pass()
        elif label in ("missing-registry-transport", "missing-reconcile-transport"):
            name = ("exercise_registry_transaction_transport" if label == "missing-registry-transport"
                    else "exercise_reconciler_transaction_transport")
            index = next(i for i, stmt in enumerate(body)
                         if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                         and isinstance(stmt.value.func, ast.Name) and stmt.value.func.id == name)
            body[index] = ast.Pass()
        elif label in ("missing-parent-proof", "early-parent-proof"):
            index = next(i for i, stmt in enumerate(body)
                         if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                         and isinstance(stmt.value.func, ast.Name)
                         and stmt.value.func.id == "prove_typed_transport_fixture_parent_guard")
            if label == "missing-parent-proof":
                body[index] = ast.Pass()
            else:
                # Keep the two transaction probes contiguous: only the parent
                # proof is moved, so the intended parent-order guard must reject.
                body.insert(index - 2, body.pop(index))
        elif label == "wrong-final-return":
            body[-1].value = ast.Constant(value=1)
        elif label == "nested-early-return":
            body.insert(11, ast.If(test=ast.Constant(value=True),
                        body=[ast.Return(value=ast.Constant(value=0))], orelse=[]))
        try:
            require_typed_transport_guard_reachability(mutated)
        except Fail as exc:
            require(str(exc) == expected,
                    f"typed transport guard {label} diagnostic drift: {exc}")
        else:
            raise Fail(f"typed transport guard {label} bypass unexpectedly accepted")
    print("PASS reject: sixteen external typed transport guard reachability substitutions")


def main() -> int:
    require(WRITER.is_file(), "typed evidence writer missing")
    require(VALIDATOR.is_file(), "typed admission validator missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    with guarded_temporary_directory(".tmp-typed-load-parent-negative-", TMP_PARENT) as raw:
        sandbox = Path(raw)
        link = sandbox / "redirect"
        link.symlink_to(sandbox, target_is_directory=True)
        before = sorted(p.name for p in sandbox.iterdir())
        try:
            with guarded_temporary_directory(".tmp-must-not-create-", link):
                raise Fail("typed load symlinked temp parent accepted")
        except Fail as exc:
            require(str(exc) == "typed contract path temp ancestor missing or symlinked",
                    f"typed load symlinked parent rejected at wrong boundary: {exc}")
        else:
            raise Fail("typed load symlinked temp parent accepted")
        require(sorted(p.name for p in sandbox.iterdir()) == before,
                "typed load symlinked temp parent published a child")
    print("PASS: typed load fixtures reuse contract path parent guard")
    prove_typed_transport_guard_reachability()
    writer = load_module(WRITER, "memory_os_typed_non_resurrection_writer_load_negative")
    validator = load_module(VALIDATOR, "memory_os_typed_non_resurrection_load_negative")
    require(writer.canonical_repo_file(WRITER, "typed evidence writer") == WRITER, "canonical typed writer path rejected")

    prove_reconcile_runtime_authorities()

    original_lock = writer.LOCK
    original_validator_loader = validator.load_module
    try:
        writer.LOCK = ROOT / "contracts/operations/.backup-restore-generation-evidence.lock"
        def substituted_loader(path: Path, name: str):
            if path == WRITER:
                return writer
            return original_validator_loader(path, name)
        validator.load_module = substituted_loader
        expect_domain_fail("typed writer append lock authority substitution", validator.main, validator.Fail)
    finally:
        writer.LOCK = original_lock
        validator.load_module = original_validator_loader

    with guarded_temporary_directory(".tmp-typed-load-", TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)

        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_domain_fail("invalid UTF-8 typed authority JSON", lambda: validator.load(invalid_utf8), validator.Fail)
        expect_domain_fail("invalid UTF-8 typed writer input", lambda: writer.load(invalid_utf8), writer.Fail)

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_domain_fail("typed authority path is unreadable directory", lambda: validator.load(directory_authority), validator.Fail)
        expect_domain_fail("typed writer input path is unreadable directory", lambda: writer.load(directory_authority), writer.Fail)

        ref_loop = tmp / "loop-evidence-ref.json"
        ref_loop.symlink_to(ref_loop.name)
        ref_loop_relative = ref_loop.relative_to(ROOT).as_posix()
        expect_domain_fail(
            "typed evidence repository ref symlink loop",
            lambda: writer.repo_ref(ref_loop_relative, "negativeEvidenceRef"),
            writer.Fail,
        )

        with tempfile.TemporaryDirectory(prefix="memory-os-typed-writer-outside-") as outside_dirname:
            outside_dir = Path(outside_dirname)
            outside_writer = outside_dir / "outside-generation-writer.py"
            outside_writer.write_text("VALUE = 1\n", encoding="utf-8")
            escaped_link = tmp / "escaped-generation-writer.py"
            escaped_link.symlink_to(outside_writer)
            loop_link = tmp / "loop-generation-writer.py"
            loop_link.symlink_to(loop_link.name)

            original_generation_writer = writer.GEN_WRITER
            try:
                writer.GEN_WRITER = outside_writer
                expect_domain_fail("generation writer absolute path escapes repository", writer.load_generation_writer, writer.Fail)
                writer.GEN_WRITER = escaped_link
                expect_domain_fail("generation writer repository symlink escapes repository", writer.load_generation_writer, writer.Fail)
                writer.GEN_WRITER = loop_link
                expect_domain_fail("generation writer repository symlink loop", writer.load_generation_writer, writer.Fail)
            finally:
                writer.GEN_WRITER = original_generation_writer

            outside_json = outside_dir / "outside-authority.json"
            outside_json.write_text("{}\n", encoding="utf-8")
            escaped_authority = tmp / "escaped-canonical-authority.json"
            escaped_authority.symlink_to(outside_json)
            loop_authority = tmp / "loop-canonical-authority.json"
            loop_authority.symlink_to(loop_authority.name)

            for field in (
                "typed non-resurrection contract",
                "typed non-resurrection registry",
                "generation evidence registry",
            ):
                expect_domain_fail(
                    f"{field} repository symlink escapes repository",
                    lambda field=field: writer.require_canonical_runtime_authority(escaped_authority, escaped_authority, field),
                    writer.Fail,
                )
                expect_domain_fail(
                    f"{field} repository symlink loop",
                    lambda field=field: writer.require_canonical_runtime_authority(loop_authority, loop_authority, field),
                    writer.Fail,
                )

    prove_reconcile_operability_rollback()

    print("Typed unreadable/escaped-authority negative suite PASS")
    print("canonical typed contract/registry/generation registry containment: enforced")
    print("direct typed data/writer/validator substitutions accepted: false")
    print("typed append lock authority substitution accepted: false")
    print("typed operability failure leaves partial authority: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"TYPED LOAD NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
