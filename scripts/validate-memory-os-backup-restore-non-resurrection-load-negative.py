#!/usr/bin/env python3
"""Prove typed non-resurrection authority loading and reconcile rollback fail closed."""

from __future__ import annotations

import ast
import copy
import importlib.util
import os
import shutil
import stat
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


def pin_checked_helper_parent(path: Path) -> int:
    """Walk from a trusted repository/temp anchor, never through a symlinked ancestor."""
    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY"),
            "typed contract path fixture guard no-follow directory open unsupported")
    anchor = ROOT if path.is_relative_to(ROOT) else Path(tempfile.gettempdir())
    try:
        relative = path.parent.relative_to(anchor)
    except ValueError as exc:
        raise Fail("typed contract path fixture guard parent outside trusted roots") from exc
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    require(anchor.is_dir() and not anchor.is_symlink(),
            "typed contract path fixture guard trusted anchor missing or symlinked")
    try:
        fd = os.open(anchor, flags)
    except OSError as exc:
        raise Fail("typed contract path fixture guard anchor open failed") from exc
    try:
        opened = os.fstat(fd)
        entry = anchor.lstat()
        require(
            stat.S_ISDIR(entry.st_mode)
            and (entry.st_dev, entry.st_ino) == (opened.st_dev, opened.st_ino),
            "typed contract path fixture guard trusted anchor identity drift",
        )
        cursor = anchor
        for part in relative.parts:
            cursor = cursor / part
            require(cursor.is_dir() and not cursor.is_symlink(),
                    "typed contract path fixture guard ancestor missing or symlinked")
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
            opened = os.fstat(fd)
            entry = cursor.lstat()
            require(
                stat.S_ISDIR(entry.st_mode)
                and (entry.st_dev, entry.st_ino) == (opened.st_dev, opened.st_ino),
                "typed contract path fixture guard ancestor identity drift",
            )
        return fd
    except OSError as exc:
        os.close(fd)
        raise Fail("typed contract path fixture guard parent open failed") from exc
    except BaseException:
        os.close(fd)
        raise


def load_pinned_fixture_helper(path: Path, name: str):
    """Pin checked ancestors and leaf FDs before executing helper source."""
    parent_fd = pin_checked_helper_parent(path)
    try:
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        except OSError as exc:
            raise Fail("typed contract path fixture guard source open failed") from exc
        try:
            opened = os.fstat(fd)
            entry = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
            require(
                stat.S_ISREG(opened.st_mode) and stat.S_ISREG(entry.st_mode)
                and (opened.st_dev, opened.st_ino) == (entry.st_dev, entry.st_ino),
                "typed contract path fixture guard source identity drift",
            )
            with os.fdopen(os.dup(fd), "rb") as stream:
                source = stream.read()
            spec = importlib.util.spec_from_file_location(name, path)
            require(spec is not None and spec.loader is not None,
                    "typed contract path fixture guard cannot load")
            module = importlib.util.module_from_spec(spec)
            exec(compile(source, str(path), "exec"), module.__dict__)
            return module
        except OSError as exc:
            raise Fail("typed contract path fixture guard pinned source read failed") from exc
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)


def guarded_temporary_directory(prefix: str, parent: Path):
    require(PATH_NEGATIVE.is_file() and not PATH_NEGATIVE.is_symlink(),
            "typed contract path fixture guard missing or symlinked")
    module = load_pinned_fixture_helper(PATH_NEGATIVE, "memory_os_typed_path_fixture_guard_load")
    require(callable(getattr(module, "guarded_temporary_directory", None)),
            "typed contract path fixture guard callable missing")
    try:
        return module.guarded_temporary_directory(prefix, parent)
    except module.Fail as exc:
        raise Fail(str(exc)) from exc



def prove_helper_source_symlink_rejected() -> None:
    # A shared fixture helper must be checked before dynamic import.
    global PATH_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="typed-fixture-helper-source-") as raw:
        sandbox = Path(raw)
        real = sandbox / "real-helper.py"
        real.touch()
        link = sandbox / "helper.py"
        link.symlink_to(real)
        original = PATH_NEGATIVE
        try:
            PATH_NEGATIVE = link
            try:
                guarded_temporary_directory(".tmp-must-not-create-", TMP_PARENT)
            except Fail as exc:
                require(str(exc) == "typed contract path fixture guard missing or symlinked",
                        f"typed fixture helper source rejected at wrong boundary: {exc}")
            else:
                raise Fail("typed symlinked fixture helper accepted")
        finally:
            PATH_NEGATIVE = original
    print("PASS: typed load fixture helper symlink rejected before import")


def prove_helper_source_swap_during_import_is_pinned() -> None:
    # The initial non-symlink check alone is insufficient: a helper pathname
    # can be replaced before importlib's loader opens it.
    global PATH_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="typed-fixture-helper-import-race-") as raw:
        sandbox = Path(raw)
        trusted = sandbox / "helper.py"
        parked = sandbox / "original-helper.py"
        untrusted = sandbox / "untrusted.py"
        trusted.write_text(
            "class Fail(RuntimeError):\n    pass\n\n"
            "def guarded_temporary_directory(prefix, parent):\n"
            "    return ('pinned-source', prefix)\n",
            encoding="utf-8",
        )
        untrusted.write_text("raise RuntimeError('untrusted helper executed')\n", encoding="utf-8")
        original_path = PATH_NEGATIVE
        original_spec = importlib.util.spec_from_file_location
        swapped = False
        try:
            PATH_NEGATIVE = trusted
            require(
                guarded_temporary_directory(".tmp-positive-", TMP_PARENT)
                == ("pinned-source", ".tmp-positive-"),
                "typed helper pinned import positive control failed",
            )

            def swap_before_spec(name, location, *args, **kwargs):
                nonlocal swapped
                if not swapped and Path(location) == trusted:
                    swapped = True
                    trusted.rename(parked)
                    trusted.symlink_to(untrusted)
                return original_spec(name, location, *args, **kwargs)

            importlib.util.spec_from_file_location = swap_before_spec
            require(
                guarded_temporary_directory(".tmp-race-", TMP_PARENT)
                == ("pinned-source", ".tmp-race-"),
                "typed helper import executed substituted source",
            )
            require(swapped and trusted.is_symlink() and parked.is_file(),
                    "typed helper source race probe did not replace the checked pathname")
        finally:
            importlib.util.spec_from_file_location = original_spec
            PATH_NEGATIVE = original_path
    print("PASS: typed load helper import uses pinned source after pathname substitution")


def prove_helper_parent_swap_after_pin_uses_original_source() -> None:
    global PATH_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="typed-load-helper-parent-race-") as raw:
        sandbox = Path(raw)
        trusted_parent = sandbox / "trusted"
        parked_parent = sandbox / "parked"
        untrusted_parent = sandbox / "untrusted"
        trusted_parent.mkdir()
        untrusted_parent.mkdir()
        (trusted_parent / "helper.py").write_text(
            "class Fail(RuntimeError):\n    pass\n\n"
            "def guarded_temporary_directory(prefix, parent):\n"
            "    return ('pinned-parent', prefix)\n",
            encoding="utf-8",
        )
        (untrusted_parent / "helper.py").write_text(
            "raise RuntimeError('untrusted parent helper executed')\n", encoding="utf-8")
        original_path = PATH_NEGATIVE
        original_open = os.open
        swapped = False
        try:
            PATH_NEGATIVE = trusted_parent / "helper.py"
            require(
                guarded_temporary_directory(".tmp-positive-", TMP_PARENT)
                == ("pinned-parent", ".tmp-positive-"),
                "typed-load parent-pinned helper positive control failed",
            )

            def swap_before_leaf_open(target, flags, *args, **kwargs):
                nonlocal swapped
                if not swapped and target == "helper.py" and kwargs.get("dir_fd") is not None:
                    swapped = True
                    trusted_parent.rename(parked_parent)
                    trusted_parent.symlink_to(untrusted_parent, target_is_directory=True)
                return original_open(target, flags, *args, **kwargs)

            os.open = swap_before_leaf_open
            require(
                guarded_temporary_directory(".tmp-parent-race-", TMP_PARENT)
                == ("pinned-parent", ".tmp-parent-race-"),
                "typed-load helper import followed substituted parent",
            )
            require(swapped and trusted_parent.is_symlink() and (parked_parent / "helper.py").is_file(),
                    "typed-load helper parent race did not substitute checked parent")
        finally:
            os.open = original_open
            PATH_NEGATIVE = original_path
    print("PASS: typed-load helper parent swap preserves pinned source")


def prove_helper_ancestor_swap_during_fd_walk_rejected() -> None:
    # A leaf/parent O_NOFOLLOW alone cannot protect a mutable higher ancestor.
    # Swap an owned nonterminal directory after it was pinned, before descent.
    global PATH_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="typed-load-helper-ancestor-race-") as raw:
        sandbox = Path(raw)
        checked_ancestor = sandbox / "checked"
        parked_ancestor = sandbox / "parked"
        redirect_ancestor = sandbox / "redirect"
        checked_parent = checked_ancestor / "nested"
        redirect_parent = redirect_ancestor / "nested"
        checked_parent.mkdir(parents=True)
        redirect_parent.mkdir(parents=True)
        (checked_parent / "helper.py").write_text(
            "class Fail(RuntimeError):\n    pass\n\n"
            "def guarded_temporary_directory(prefix, parent):\n"
            "    return ('pinned-ancestor', prefix)\n",
            encoding="utf-8",
        )
        (redirect_parent / "helper.py").write_text(
            "raise RuntimeError('untrusted ancestor helper executed')\n", encoding="utf-8"
        )
        original_path = PATH_NEGATIVE
        original_open = os.open
        swapped = False
        try:
            PATH_NEGATIVE = checked_parent / "helper.py"
            require(
                guarded_temporary_directory(".tmp-positive-", TMP_PARENT)
                == ("pinned-ancestor", ".tmp-positive-"),
                "typed load ancestor helper positive control failed",
            )

            def swap_before_descend(target, flags, *args, **kwargs):
                nonlocal swapped
                if not swapped and target == "nested" and kwargs.get("dir_fd") is not None:
                    swapped = True
                    checked_ancestor.rename(parked_ancestor)
                    checked_ancestor.symlink_to(redirect_ancestor, target_is_directory=True)
                return original_open(target, flags, *args, **kwargs)

            os.open = swap_before_descend
            try:
                guarded_temporary_directory(".tmp-ancestor-race-", TMP_PARENT)
            except Fail as exc:
                require(
                    str(exc) == "typed contract path fixture guard ancestor identity drift",
                    f"typed helper ancestor swap rejected at wrong boundary: {exc}",
                )
            else:
                raise Fail("typed load helper ancestor swap accepted")
            require(swapped and checked_ancestor.is_symlink()
                    and (parked_ancestor / "nested/helper.py").is_file(),
                    "typed helper ancestor swap did not preserve pinned original")
            require((redirect_parent / "helper.py").read_text(encoding="utf-8")
                    == "raise RuntimeError('untrusted ancestor helper executed')\n",
                    "typed helper ancestor swap modified untrusted source")
        finally:
            os.open = original_open
            PATH_NEGATIVE = original_path
    print("PASS: typed load helper ancestor swap fails closed during FD walk")


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
    snapshot_proofs = [(i, stmt) for i, stmt in enumerate(body)
                       if direct_call(stmt, "exercise_writer_snapshot_transport")]
    require(len(snapshot_proofs) == 1 and snapshot_proofs[0][0] == parent_proofs[0][0] + 1,
            "typed transport negative must execute pinned snapshot proof after parent guard")
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
        ("missing-snapshot-proof", "typed transport negative must execute pinned snapshot proof after parent guard"),
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
        elif label == "missing-snapshot-proof":
            index = next(i for i, stmt in enumerate(body)
                         if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                         and isinstance(stmt.value.func, ast.Name)
                         and stmt.value.func.id == "exercise_writer_snapshot_transport")
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


def prove_typed_writer_json_reader(writer: Any) -> None:
    """Exercise the real writer reader on disposable data, never production evidence."""
    protected = (CONTRACT.read_bytes(), REGISTRY.read_bytes(), GEN_REGISTRY.read_bytes(), STATUS.read_bytes())
    with guarded_temporary_directory(".tmp-typed-writer-json-", TMP_PARENT) as directory:
        path = Path(directory) / "writer-candidate.json"
        positive = b'{"safe":true,"nested":{"count":1}}'
        path.write_bytes(positive)
        require(writer.load(path) == {"safe": True, "nested": {"count": 1}},
                "typed writer JSON positive control failed")
        cases = (
            ("duplicate root", b'{"safe":true,"safe":false}', "typed writer JSON duplicate key refused"),
            ("duplicate nested", b'{"nested":{"a":1,"a":2}}', "typed writer JSON duplicate key refused"),
            ("NaN", b'{"number":NaN}', "typed writer JSON nonfinite number refused"),
            ("Infinity", b'{"number":Infinity}', "typed writer JSON nonfinite number refused"),
            ("negative Infinity", b'{"number":-Infinity}', "typed writer JSON nonfinite number refused"),
            ("float overflow", b'{"number":1e999}', "typed writer JSON nonfinite number refused"),
            ("huge integer", b'{"number":' + b"9" * 5000 + b"}", "typed writer JSON integer too large"),
            ("oversized", b'{"data":"' + b"x" * writer.MAX_JSON_BYTES + b'"}',
             "typed writer JSON size limit exceeded"),
            ("invalid UTF-8", b'{"private":"\xff"}', "typed writer JSON unreadable or invalid"),
            ("malformed private", b'{"private":"synthetic-secret",',
             "typed writer JSON unreadable or invalid"),
            ("nonobject root", b"[]", "typed writer JSON root must be object"),
        )

        def rejected(candidate: Any, expected: str, label: str) -> None:
            try:
                writer.load(candidate)
            except writer.Fail as exc:
                require(str(exc) == expected, f"{label}: wrong typed writer JSON failure class")
                require("synthetic-secret" not in str(exc), f"{label}: private input disclosed")
            else:
                raise Fail(f"{label}: unsafe typed writer JSON accepted")

        for label, payload, expected in cases:
            path.write_bytes(payload)
            rejected(path, expected, label)
        path.write_bytes(positive)
        alias = Path(directory) / "alias.json"
        alias.symlink_to(path)
        rejected(alias, "typed writer JSON unreadable or invalid", "symlink")
        fifo = Path(directory) / "fifo.json"
        os.mkfifo(fifo)
        rejected(fifo, "typed writer JSON path unsafe", "FIFO")
        rejected(Path(directory), "typed writer JSON path unsafe", "directory")
        rejected("writer-candidate.json", "typed writer JSON path invalid", "non-Path")
        require(writer.load(path) == {"safe": True, "nested": {"count": 1}},
                "typed writer JSON positive control changed after negative cases")
        require(path.read_bytes() == positive, "typed writer JSON positive fixture changed")
    require((CONTRACT.read_bytes(), REGISTRY.read_bytes(), GEN_REGISTRY.read_bytes(), STATUS.read_bytes()) == protected,
            "typed writer JSON negative changed protected authorities")
    print("PASS reject: typed writer strict bounded JSON, symlink, FIFO and private diagnostic negatives")


def prove_typed_json_reader(validator: Any) -> None:
    """Exercise the real typed admission reader without changing reviewed authorities."""
    protected = (CONTRACT.read_bytes(), REGISTRY.read_bytes(), GEN_REGISTRY.read_bytes(), STATUS.read_bytes())
    with guarded_temporary_directory(".tmp-typed-json-reader-", TMP_PARENT) as directory:
        path = Path(directory) / "candidate.json"
        positive = b'{"safe":true,"nested":{"count":1}}'
        path.write_bytes(positive)
        require(validator.load(path) == {"safe": True, "nested": {"count": 1}}, "typed JSON positive control failed")
        cases = (
            ("duplicate root", b'{"safe":true,"safe":false}', "typed admission JSON duplicate key refused"),
            ("duplicate nested", b'{"nested":{"a":1,"a":2}}', "typed admission JSON duplicate key refused"),
            ("NaN", b'{"number":NaN}', "typed admission JSON nonfinite number refused"),
            ("Infinity", b'{"number":Infinity}', "typed admission JSON nonfinite number refused"),
            ("negative Infinity", b'{"number":-Infinity}', "typed admission JSON nonfinite number refused"),
            ("float overflow", b'{"number":1e999}', "typed admission JSON nonfinite number refused"),
            ("large integer", b'{"number":' + b"9" * 5000 + b"}", "typed admission JSON integer too large"),
            ("oversized JSON", b'{"data":"' + b"x" * validator.MAX_JSON_BYTES + b'"}', "typed admission JSON size limit exceeded"),
            ("invalid UTF-8", b'{"private":"\xff"}', "typed admission JSON unreadable or invalid"),
            ("malformed private", b'{"private":"synthetic-secret",', "typed admission JSON unreadable or invalid"),
            ("nonobject root", b"[]", "typed admission JSON root must be object"),
        )
        def rejected(candidate: Any, expected: str, label: str) -> None:
            try:
                validator.load(candidate)
            except validator.Fail as exc:
                require(str(exc) == expected, f"{label}: wrong typed JSON rejection boundary")
                require("synthetic-secret" not in str(exc), f"{label}: private marker disclosed")
            else:
                raise Fail(f"{label}: unsafe typed JSON accepted")
        for label, payload, expected in cases:
            path.write_bytes(payload)
            rejected(path, expected, label)
        path.write_bytes(positive)
        alias = Path(directory) / "alias.json"
        alias.symlink_to(path)
        rejected(alias, "typed admission JSON path unsafe", "symlink")
        rejected(Path(directory), "typed admission JSON path unsafe", "directory")
        rejected(Path(directory) / "missing.json", "typed admission JSON path missing or outside repository", "missing")
        rejected("candidate.json", "typed admission JSON path invalid", "non-Path")
        with tempfile.TemporaryDirectory(prefix="memory-os-typed-json-canary-") as outside:
            canary = Path(outside) / "canary.json"
            canary.write_bytes(positive)
            escaped = Path(directory) / "escaped.json"
            escaped.symlink_to(canary)
            rejected(escaped, "typed admission JSON path missing or outside repository", "external symlink")
            require(canary.read_bytes() == positive, "typed JSON reader mutated external canary")
        require(path.read_bytes() == positive, "typed JSON reader mutated positive fixture")
    require((CONTRACT.read_bytes(), REGISTRY.read_bytes(), GEN_REGISTRY.read_bytes(), STATUS.read_bytes()) == protected,
            "typed JSON reader negative mutated protected authorities")
    print("PASS: actual typed admission JSON reader positive and 16 fail-closed negatives")


def prove_typed_json_reader_fd_races(validator: Any) -> None:
    """Real typed admission reader must use pinned original bytes after path swaps."""
    protected = (CONTRACT.read_bytes(), REGISTRY.read_bytes(), GEN_REGISTRY.read_bytes(), STATUS.read_bytes())
    with guarded_temporary_directory(".tmp-typed-json-fd-race-", TMP_PARENT) as raw:
        sandbox = Path(raw)
        for case in ("parent", "ancestor"):
            checked = sandbox / (case + "-checked")
            parked = sandbox / (case + "-parked")
            redirect = sandbox / (case + "-redirect")
            checked.mkdir()
            redirect.mkdir()
            if case == "ancestor":
                (checked / "nested").mkdir()
                (redirect / "nested").mkdir()
                checked_leaf = checked / "nested/candidate.json"
                redirect_leaf = redirect / "nested/candidate.json"
                trigger = "nested"
            else:
                checked_leaf = checked / "candidate.json"
                redirect_leaf = redirect / "candidate.json"
                trigger = "candidate.json"
            checked_leaf.write_bytes(b'{"source":"pinned"}')
            redirect_leaf.write_bytes(b'{"source":"redirected","secret":"SYNTHETIC_EXTERNAL_CANARY"}')
            original_open = os.open
            swapped = False

            def swap_during_walk(target, flags, *args, **kwargs):
                nonlocal swapped
                if not swapped and target == trigger and kwargs.get("dir_fd") is not None:
                    swapped = True
                    checked.rename(parked)
                    checked.symlink_to(redirect, target_is_directory=True)
                return original_open(target, flags, *args, **kwargs)

            try:
                require(validator.load(checked_leaf) == {"source": "pinned"},
                        f"typed JSON {case} positive control failed")
                os.open = swap_during_walk
                result = validator.load(checked_leaf)
                require(swapped, f"typed JSON {case} race injection not reached")
                require(result == {"source": "pinned"},
                        f"typed JSON {case} race read redirected source")
                require(redirect_leaf.read_bytes() == b'{"source":"redirected","secret":"SYNTHETIC_EXTERNAL_CANARY"}',
                        f"typed JSON {case} race changed external canary")
            finally:
                os.open = original_open
    require((CONTRACT.read_bytes(), REGISTRY.read_bytes(), GEN_REGISTRY.read_bytes(), STATUS.read_bytes()) == protected,
            "typed JSON race negative mutated protected authorities")
    print("PASS: actual typed admission JSON reader parent and ancestor swap retain pinned original source")


def prove_typed_json_reader_descriptor_faults(validator: Any) -> None:
    """Real typed JSON reader must close all FDs after private close/fdopen faults."""
    with guarded_temporary_directory(".tmp-typed-json-fd-fault-", TMP_PARENT) as raw:
        path = Path(raw) / "positive.json"
        path.write_bytes(b'{"safe":true}')
        for fault, expected in (
            ("close", "typed admission JSON cleanup failed"),
            ("fdopen", "typed admission JSON unreadable or invalid"),
        ):
            original_open, original_close, original_fdopen = os.open, os.close, os.fdopen
            opened: list[int] = []
            faulted = False

            def capture_open(*args, **kwargs):
                descriptor = original_open(*args, **kwargs)
                opened.append(descriptor)
                return descriptor

            def close_then_fail(descriptor):
                nonlocal faulted
                original_close(descriptor)
                if not faulted:
                    faulted = True
                    raise OSError("SYNTHETIC_PRIVATE_FD_CLOSE_CANARY")

            def fdopen_then_fail(descriptor, *args, **kwargs):
                nonlocal faulted
                faulted = True
                raise OSError("SYNTHETIC_PRIVATE_FDOPEN_CANARY")

            try:
                os.open = capture_open
                if fault == "close":
                    os.close = close_then_fail
                else:
                    os.fdopen = fdopen_then_fail
                try:
                    validator.load(path)
                except validator.Fail as exc:
                    require(str(exc) == expected and exc.__suppress_context__ and exc.__cause__ is None,
                            f"typed JSON {fault} fault leaked or misclassified")
                    require("SYNTHETIC_PRIVATE_" not in str(exc),
                            f"typed JSON {fault} private diagnostic leaked")
                else:
                    raise Fail(f"typed JSON {fault} fault unexpectedly accepted")
            finally:
                os.open, os.close, os.fdopen = original_open, original_close, original_fdopen
            require(faulted and opened, f"typed JSON {fault} injection not reached")
            for descriptor in opened:
                try:
                    os.fstat(descriptor)
                except OSError:
                    pass
                else:
                    raise Fail(f"typed JSON {fault} leaked descriptor")
            require(validator.load(path) == {"safe": True},
                    f"typed JSON {fault} recovery positive failed")
    print("PASS: actual typed admission JSON reader close/fdopen private faults clean all descriptors")


def prove_typed_json_reader_platform_flags(validator: Any) -> None:
    """Missing and ineffective directory/nofollow flags cannot admit typed JSON."""
    with guarded_temporary_directory(".tmp-typed-json-flags-", TMP_PARENT) as raw:
        path = Path(raw) / "positive.json"
        path.write_bytes(b'{"safe":true}')
        for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY"):
            original = getattr(os, flag)
            try:
                for invalid in (None, 0):
                    setattr(os, flag, invalid)
                    try:
                        validator.load(path)
                    except validator.Fail as exc:
                        require(str(exc) == "typed admission JSON nofollow support required"
                                and exc.__suppress_context__ and exc.__cause__ is None,
                                f"typed JSON {flag} unsafe platform failure class drift")
                    else:
                        raise Fail(f"typed JSON accepted unsafe {flag}")
            finally:
                setattr(os, flag, original)
        require(validator.load(path) == {"safe": True},
                "typed JSON reader failed after platform flag restoration")
    print("PASS: typed JSON missing/zero nofollow, nonblock and directory flags rejected")


def prove_typed_reconcile_pinned_reader() -> None:
    """Actual typed reconcile snapshots reject oversized and substituted JSON."""
    reconciler = load_module(RECONCILER, "memory_os_typed_reconcile_pinned_reader_negative")
    protected = (CONTRACT.read_bytes(), REGISTRY.read_bytes(), GEN_REGISTRY.read_bytes(), STATUS.read_bytes())
    with guarded_temporary_directory(".tmp-typed-reconcile-fd-race-", TMP_PARENT) as raw:
        sandbox = Path(raw)
        oversized = sandbox / "oversized.json"
        oversized.write_bytes(b"x" * (reconciler.MAX_AUTHORITY_BYTES + 1))
        try:
            reconciler.read_text(oversized)
        except reconciler.Fail as exc:
            require(str(exc) == "typed reconcile authority exceeds 1 MiB",
                    "typed reconcile oversized read rejected at wrong boundary")
        else:
            raise Fail("typed reconcile accepted oversized snapshot")
        for case in ("parent", "ancestor"):
            checked = sandbox / (case + "-checked")
            parked = sandbox / (case + "-parked")
            redirect = sandbox / (case + "-redirect")
            checked.mkdir()
            redirect.mkdir()
            if case == "ancestor":
                (checked / "nested").mkdir()
                (redirect / "nested").mkdir()
                checked_leaf = checked / "nested/candidate.json"
                redirect_leaf = redirect / "nested/candidate.json"
                trigger = "nested"
            else:
                checked_leaf = checked / "candidate.json"
                redirect_leaf = redirect / "candidate.json"
                trigger = "candidate.json"
            checked_leaf.write_bytes(b'{"source":"pinned"}')
            redirect_leaf.write_bytes(b'{"source":"redirected","secret":"SYNTHETIC_PRIVATE_CANARY"}')
            original_open = os.open
            swapped = False

            def swap_during_walk(target, flags, *args, **kwargs):
                nonlocal swapped
                if not swapped and target == trigger and kwargs.get("dir_fd") is not None:
                    swapped = True
                    checked.rename(parked)
                    checked.symlink_to(redirect, target_is_directory=True)
                return original_open(target, flags, *args, **kwargs)

            try:
                require(reconciler.read_text(checked_leaf) == '{"source":"pinned"}',
                        f"typed reconcile {case} positive control failed")
                os.open = swap_during_walk
                value = reconciler.read_text(checked_leaf)
                require(swapped and value == '{"source":"pinned"}',
                        f"typed reconcile {case} read substituted authority")
                require(redirect_leaf.read_bytes() == b'{"source":"redirected","secret":"SYNTHETIC_PRIVATE_CANARY"}',
                        f"typed reconcile {case} changed canary")
            finally:
                os.open = original_open
    require((CONTRACT.read_bytes(), REGISTRY.read_bytes(), GEN_REGISTRY.read_bytes(), STATUS.read_bytes()) == protected,
            "typed reconcile pinned reader changed protected authorities")
    print("PASS: typed reconcile bounded JSON snapshot and parent/ancestor FD race negatives")


def prove_typed_reconcile_strict_json() -> None:
    reconciler = load_module(RECONCILER, "memory_os_typed_reconcile_strict_json_negative")
    protected = (CONTRACT.read_bytes(), REGISTRY.read_bytes(), GEN_REGISTRY.read_bytes(), STATUS.read_bytes())
    with guarded_temporary_directory(".tmp-typed-reconcile-json-", TMP_PARENT) as raw:
        path = Path(raw) / "candidate.json"
        path.write_bytes(b'{"nested":{"count":1}}')
        require(reconciler.load(path) == {"nested": {"count": 1}},
                "typed reconcile JSON positive failed")
        for label, payload, expected in (
            ("duplicate", b'{"nested":{"key":1,"key":2}}',
             "typed reconcile JSON duplicate key refused"),
            ("NaN", b'{"value":NaN}', "typed reconcile JSON nonfinite number refused"),
            ("Infinity", b'{"value":Infinity}', "typed reconcile JSON nonfinite number refused"),
            ("float overflow", b'{"value":1e999}', "typed reconcile JSON nonfinite number refused"),
            ("129 digit integer", b'{"value":' + b"9" * 129 + b"}",
             "typed reconcile JSON integer too large"),
            ("invalid UTF-8", b'{"value":"\xff"}', "typed reconcile authority invalid UTF-8"),
            ("nonobject root", b"[]", "typed reconcile JSON root must be object"),
        ):
            path.write_bytes(payload)
            try:
                reconciler.load(path)
            except reconciler.Fail as exc:
                require(str(exc) == expected and "SYNTHETIC_PRIVATE_" not in str(exc),
                        f"typed reconcile JSON {label} wrong rejection")
            else:
                raise Fail(f"typed reconcile JSON {label} accepted")
    require((CONTRACT.read_bytes(), REGISTRY.read_bytes(), GEN_REGISTRY.read_bytes(), STATUS.read_bytes()) == protected,
            "typed reconcile strict JSON changed protected authorities")
    print("PASS: typed reconciler strict JSON positive and seven ambiguity negatives")


def prove_typed_reconcile_descriptor_faults() -> None:
    reconciler = load_module(RECONCILER, "memory_os_typed_reconcile_fd_fault_negative")
    with guarded_temporary_directory(".tmp-typed-reconcile-fd-fault-", TMP_PARENT) as raw:
        path = Path(raw) / "positive.json"
        path.write_bytes(b'{"safe":true}')
        for fault, expected in (
            ("close", "typed reconcile authority cleanup failed"),
            ("fdopen", "typed reconcile authority unreadable"),
        ):
            original_open, original_close, original_fdopen = os.open, os.close, os.fdopen
            opened: list[int] = []
            faulted = False

            def capture_open(*args, **kwargs):
                descriptor = original_open(*args, **kwargs)
                opened.append(descriptor)
                return descriptor

            def close_then_fail(descriptor):
                nonlocal faulted
                original_close(descriptor)
                if not faulted:
                    faulted = True
                    raise OSError("SYNTHETIC_PRIVATE_CLOSE_CANARY")

            def fdopen_then_fail(descriptor, *args, **kwargs):
                nonlocal faulted
                faulted = True
                raise OSError("SYNTHETIC_PRIVATE_FDOPEN_CANARY")

            try:
                os.open = capture_open
                if fault == "close":
                    os.close = close_then_fail
                else:
                    os.fdopen = fdopen_then_fail
                try:
                    reconciler.read_text(path)
                except reconciler.Fail as exc:
                    require(str(exc) == expected and exc.__suppress_context__ and exc.__cause__ is None,
                            f"typed reconcile {fault} leaked private descriptor fault")
                else:
                    raise Fail(f"typed reconcile {fault} fault unexpectedly accepted")
            finally:
                os.open, os.close, os.fdopen = original_open, original_close, original_fdopen
            require(faulted and opened, f"typed reconcile {fault} fault injection not reached")
            for descriptor in opened:
                try:
                    os.fstat(descriptor)
                except OSError:
                    pass
                else:
                    raise Fail(f"typed reconcile {fault} leaked descriptor")
            require(reconciler.read_text(path) == '{"safe":true}',
                    f"typed reconcile {fault} recovery positive failed")
    print("PASS: typed reconcile close/fdopen private faults close all descriptors")


def prove_typed_reconcile_platform_flags() -> None:
    reconciler = load_module(RECONCILER, "memory_os_typed_reconcile_flags_negative")
    with guarded_temporary_directory(".tmp-typed-reconcile-flags-", TMP_PARENT) as raw:
        path = Path(raw) / "positive.json"
        path.write_bytes(b'{"safe":true}')
        for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY"):
            original = getattr(os, flag)
            try:
                for invalid in (None, 0):
                    setattr(os, flag, invalid)
                    try:
                        reconciler.read_text(path)
                    except reconciler.Fail as exc:
                        require(str(exc) == "typed reconcile authority nofollow support required"
                                and exc.__suppress_context__ and exc.__cause__ is None,
                                f"typed reconcile {flag} unsafe platform class drift")
                    else:
                        raise Fail(f"typed reconcile accepted unsafe {flag}")
            finally:
                setattr(os, flag, original)
        require(reconciler.read_text(path) == '{"safe":true}',
                "typed reconcile platform flag restoration positive failed")
    print("PASS: typed reconcile None/zero safety flags rejected")


def prove_typed_reconcile_writer_ownership() -> None:
    reconciler = load_module(RECONCILER, "memory_os_typed_reconcile_writer_ownership_negative")
    protected = (CONTRACT.read_bytes(), REGISTRY.read_bytes(), GEN_REGISTRY.read_bytes(), STATUS.read_bytes())
    with guarded_temporary_directory(".tmp-typed-write-ownership-", TMP_PARENT) as raw:
        sandbox = Path(raw)
        path = sandbox / "candidate.json"
        positive = b'{"safe":true}'
        path.write_bytes(positive)
        path.chmod(0o640)
        for label, value, expected in (
            ("oversized", "x" * (reconciler.MAX_AUTHORITY_BYTES + 1),
             "typed reconcile write size limit exceeded"),
            ("nonstring", None, "typed reconcile write payload invalid"),
        ):
            try:
                reconciler.write_text(path, value)
            except reconciler.Fail as exc:
                require(str(exc) == expected, f"typed reconcile write {label} wrong rejection")
            else:
                raise Fail(f"typed reconcile write {label} accepted")
        with tempfile.TemporaryDirectory(prefix="typed-write-outside-") as outside:
            canary = Path(outside) / "canary.json"
            canary.write_bytes(positive)
            link = sandbox / "alias.json"
            link.symlink_to(canary)
            try:
                reconciler.write_text(link, '{"unsafe":true}')
            except reconciler.Fail as exc:
                require(str(exc) == "typed reconcile write path unsafe",
                        "typed reconcile write symlink rejected at wrong boundary")
            else:
                raise Fail("typed reconcile write followed symlink")
            require(canary.read_bytes() == positive, "typed reconcile write changed external canary")

        original_fdopen = os.fdopen
        original_mkstemp = tempfile.mkstemp
        opened: list[int] = []

        def capture_mkstemp(*args, **kwargs):
            descriptor, name = original_mkstemp(*args, **kwargs)
            opened.append(descriptor)
            return descriptor, name

        class ShortStream:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return self.stream.__exit__(*args)

            def write(self, value):
                return len(value) - 1

            def flush(self):
                self.stream.flush()

            def fileno(self):
                return self.stream.fileno()

        for fault, expected in (
            ("fdopen", "typed reconcile atomic write failed"),
            ("short", "typed reconcile write short buffered write refused"),
        ):
            opened.clear()

            def fault_fdopen(descriptor, *args, **kwargs):
                if fault == "fdopen":
                    raise OSError("SYNTHETIC_PRIVATE_FDOPEN_CANARY")
                return ShortStream(original_fdopen(descriptor, *args, **kwargs))

            try:
                tempfile.mkstemp = capture_mkstemp
                os.fdopen = fault_fdopen
                try:
                    reconciler.write_text(path, '{"safe":false}')
                except reconciler.Fail as exc:
                    require(str(exc) == expected and "SYNTHETIC_PRIVATE_" not in str(exc),
                            f"typed reconcile write {fault} leaked or misclassified")
                else:
                    raise Fail(f"typed reconcile write {fault} fault accepted")
            finally:
                os.fdopen = original_fdopen
                tempfile.mkstemp = original_mkstemp
            require(len(opened) == 1, f"typed reconcile write {fault} descriptor injection not reached")
            try:
                os.fstat(opened[0])
            except OSError:
                pass
            else:
                raise Fail(f"typed reconcile write {fault} leaked descriptor")
            require(path.read_bytes() == positive and (path.stat().st_mode & 0o7777) == 0o640,
                    f"typed reconcile write {fault} changed fixture bytes or mode")
            require(not list(sandbox.glob(".candidate.json.*.tmp")),
                    f"typed reconcile write {fault} left temporary file")
    require((CONTRACT.read_bytes(), REGISTRY.read_bytes(), GEN_REGISTRY.read_bytes(), STATUS.read_bytes()) == protected,
            "typed reconcile writer negative mutated protected authorities")
    print("PASS: typed reconcile writer oversized/symlink/fdopen/short-write private ownership negatives")


def prove_typed_reconcile_child_validator() -> None:
    """Child stdout/stderr, timeout and abnormal return codes never leak private data."""
    reconciler = load_module(RECONCILER, "memory_os_typed_reconcile_child_validator_negative")
    original_run = reconciler.subprocess.run
    observed: list[str] = []
    mode = "success"

    def fake_run(args, **kwargs):
        observed.append(mode)
        require(args == [reconciler.sys.executable, str(reconciler.VALIDATOR)],
                "typed reconcile child validator command drift")
        require(kwargs.get("cwd") == ROOT
                and kwargs.get("stdout") == reconciler.subprocess.DEVNULL
                and kwargs.get("stderr") == reconciler.subprocess.DEVNULL
                and kwargs.get("timeout") == 180
                and kwargs.get("check") is False,
                "typed reconcile child output privacy/timeout drift")
        if mode == "timeout":
            raise reconciler.subprocess.TimeoutExpired(args, 180)
        if mode == "oserror":
            raise OSError("SYNTHETIC_PRIVATE_CHILD_CANARY")
        from types import SimpleNamespace
        return SimpleNamespace(returncode={"success": 0, "nonzero": 1,
                                           "bool": True, "string": "0"}[mode])

    try:
        reconciler.subprocess.run = fake_run
        reconciler.run_post_validator(reconciler.VALIDATOR, reconciler.VALIDATOR_REL,
                                      "typed non-resurrection validator")
        for mode, expected in (
            ("nonzero", "typed reconcile post-validator failed"),
            ("bool", "typed reconcile post-validator failed"),
            ("string", "typed reconcile post-validator failed"),
            ("timeout", "typed reconcile post-validator unavailable"),
            ("oserror", "typed reconcile post-validator unavailable"),
        ):
            try:
                reconciler.run_post_validator(reconciler.VALIDATOR, reconciler.VALIDATOR_REL,
                                              "typed non-resurrection validator")
            except reconciler.Fail as exc:
                require(str(exc) == expected and "SYNTHETIC_PRIVATE_" not in str(exc),
                        f"typed reconcile child {mode} leaked or misclassified")
                if mode in ("timeout", "oserror"):
                    require(exc.__suppress_context__ and exc.__cause__ is None,
                            f"typed reconcile child {mode} leaked exception context")
            else:
                raise Fail(f"typed reconcile child {mode} unexpectedly accepted")
    finally:
        reconciler.subprocess.run = original_run
    require(observed == ["success", "nonzero", "bool", "string", "timeout", "oserror"],
            "typed reconcile child failure matrix incomplete")
    print("PASS: typed reconcile child validator bounded private subprocess and five negatives")


def prove_typed_reconcile_private_path_diagnostics() -> None:
    reconciler = load_module(RECONCILER, "memory_os_typed_reconcile_private_path_negative")
    original_resolve = Path.resolve
    original_module_from_spec = reconciler.importlib.util.module_from_spec
    private = "SYNTHETIC_PRIVATE_PATH_CANARY"

    def fail_private_resolve(self, *args, **kwargs):
        if self == CONTRACT:
            raise OSError(private)
        return original_resolve(self, *args, **kwargs)

    def require_private_fail(action, expected):
        try:
            action()
        except reconciler.Fail as exc:
            require(str(exc) == expected and exc.__suppress_context__ and exc.__cause__ is None
                    and private not in str(exc),
                    "typed reconcile path/import leaked private exception")
        else:
            raise Fail("typed reconcile private path/import exception accepted")

    try:
        Path.resolve = fail_private_resolve
        require_private_fail(lambda: reconciler.repo_relative(CONTRACT),
                             "typed reconcile authority path unsafe")
        require_private_fail(
            lambda: reconciler.require_exact_repo_file(
                CONTRACT, reconciler.CONTRACT_REL, "typed non-resurrection contract"),
            "typed non-resurrection contract missing or escapes repository")
    finally:
        Path.resolve = original_resolve

    def fail_private_import(_spec):
        raise OSError(private)

    def fail_private_runtime(_spec):
        raise RuntimeError(private)

    try:
        reconciler.importlib.util.module_from_spec = fail_private_import
        require_private_fail(
            lambda: reconciler.load_module(reconciler.TYPED_WRITER, "synthetic_typed_import"),
            "typed reconcile validator module import unavailable")
        reconciler.importlib.util.module_from_spec = fail_private_runtime
        require_private_fail(
            lambda: reconciler.load_module(reconciler.TYPED_WRITER, "synthetic_typed_import"),
            "typed reconcile validator module import unavailable")
    finally:
        reconciler.importlib.util.module_from_spec = original_module_from_spec
    print("PASS: typed reconcile private path and module import errors suppressed")


def prove_typed_reconcile_repo_refs() -> None:
    reconciler = load_module(RECONCILER, "memory_os_typed_reconcile_repo_ref_negative")
    protected = (CONTRACT.read_bytes(), REGISTRY.read_bytes(), GEN_REGISTRY.read_bytes(), STATUS.read_bytes())
    with guarded_temporary_directory(".tmp-typed-ref-alias-", TMP_PARENT) as raw:
        sandbox = Path(raw)
        real = sandbox / "real"
        real.mkdir()
        file = real / "evidence.json"
        file.write_bytes(b'{"safe":true}')
        require(reconciler.require_repo_file(file, "synthetic ref unsafe") == file.relative_to(ROOT),
                "typed reconcile canonical evidence ref rejected")
        alias = sandbox / "alias.json"
        alias.symlink_to(file)
        parent_alias = sandbox / "parent-alias"
        parent_alias.symlink_to(real, target_is_directory=True)
        loop = sandbox / "loop.json"
        loop.symlink_to(loop.name)
        for label, candidate, expected in (
            ("leaf alias", alias, "synthetic ref unsafe"),
            ("ancestor alias", parent_alias / file.name, "synthetic ref unsafe"),
            ("symlink loop", loop, "typed reconcile repository file unsafe"),
            ("missing", sandbox / "missing.json", "typed reconcile repository file unsafe"),
        ):
            try:
                reconciler.require_repo_file(candidate, "synthetic ref unsafe")
            except reconciler.Fail as exc:
                require(str(exc) == expected, f"typed reconcile {label} wrong ref rejection")
            else:
                raise Fail(f"typed reconcile {label} ref accepted")
        with tempfile.TemporaryDirectory(prefix="typed-ref-outside-") as outside:
            canary = Path(outside) / "canary.json"
            canary.write_bytes(b'{"private":"SYNTHETIC_PRIVATE_CANARY"}')
            escaped = sandbox / "escaped.json"
            escaped.symlink_to(canary)
            try:
                reconciler.require_repo_file(escaped, "synthetic ref unsafe")
            except reconciler.Fail as exc:
                require(str(exc) == "typed reconcile repository file unsafe",
                        "typed reconcile escaped ref leaked private path")
            else:
                raise Fail("typed reconcile escaped ref accepted")
            require(canary.read_bytes() == b'{"private":"SYNTHETIC_PRIVATE_CANARY"}',
                    "typed reconcile ref negative changed external canary")
    require((CONTRACT.read_bytes(), REGISTRY.read_bytes(), GEN_REGISTRY.read_bytes(), STATUS.read_bytes()) == protected,
            "typed reconcile ref negative changed protected authorities")
    print("PASS: typed reconcile canonical evidence ref and five symlink/alias negatives")


def prove_typed_reconcile_writer_preopen_faults() -> None:
    reconciler = load_module(RECONCILER, "memory_os_typed_reconcile_writer_preopen_negative")
    with guarded_temporary_directory(".tmp-typed-write-preopen-", TMP_PARENT) as raw:
        path = Path(raw) / "candidate.json"
        positive = b'{"safe":true}'
        path.write_bytes(positive)
        path.chmod(0o640)
        original_mkstemp, original_fchmod = tempfile.mkstemp, os.fchmod
        for fault in ("mkstemp", "fchmod"):
            opened: list[int] = []
            injected = False

            def fault_mkstemp(*args, **kwargs):
                nonlocal injected
                if fault == "mkstemp":
                    injected = True
                    raise OSError("SYNTHETIC_PRIVATE_MKSTEMP_CANARY")
                descriptor, name = original_mkstemp(*args, **kwargs)
                opened.append(descriptor)
                return descriptor, name

            def fault_fchmod(descriptor, value):
                nonlocal injected
                injected = True
                raise OSError("SYNTHETIC_PRIVATE_FCHMOD_CANARY")

            try:
                tempfile.mkstemp = fault_mkstemp
                if fault == "fchmod":
                    os.fchmod = fault_fchmod
                try:
                    reconciler.write_text(path, '{"safe":false}')
                except reconciler.Fail as exc:
                    require(str(exc) == "typed reconcile atomic write failed"
                            and exc.__suppress_context__ and exc.__cause__ is None,
                            f"typed writer {fault} leaked private preopen exception")
                else:
                    raise Fail(f"typed writer {fault} preopen fault accepted")
            finally:
                tempfile.mkstemp, os.fchmod = original_mkstemp, original_fchmod
            require(injected and len(opened) == (1 if fault == "fchmod" else 0),
                    f"typed writer {fault} fault injection not reached")
            for descriptor in opened:
                try:
                    os.fstat(descriptor)
                except OSError:
                    pass
                else:
                    raise Fail(f"typed writer {fault} leaked descriptor")
            require(path.read_bytes() == positive and (path.stat().st_mode & 0o7777) == 0o640,
                    f"typed writer {fault} changed fixture bytes/mode")
            require(not list(path.parent.glob(".candidate.json.*.tmp")),
                    f"typed writer {fault} left temporary file")
    print("PASS: typed reconcile mkstemp/fchmod private preopen faults clean FD/temp")



def prove_typed_private_path_negative_reachability() -> None:
    """Independently reject removal of the real private-path fault injection."""
    source = PATH_NEGATIVE.read_text(encoding="utf-8")

    def verify(candidate: str) -> None:
        try:
            tree = ast.parse(candidate)
        except SyntaxError:
            raise Fail("typed admission private path negative syntax invalid") from None
        functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
        target = functions.get("prove_private_typed_admission_paths")
        main = functions.get("main")
        require(target is not None and main is not None,
                "typed admission private path negative function/main missing")
        calls = [node for node in ast.walk(main) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == "prove_private_typed_admission_paths"]
        require(len(calls) == 1, "typed admission private path negative not executed exactly once")
        body = ast.get_source_segment(candidate, target)
        require(isinstance(body, str), "typed admission private path negative body unavailable")
        for token in ['SYNTHETIC_PRIVATE_TYPED_ADMISSION_CANARY','validator.repo_relative','validator.canonical_repo_file_ref','Path.resolve = private_resolve','Path.is_file = private_is_file','exc.__suppress_context__']:
            require(token in body, "typed admission private path negative guard removed")

        import_target = functions.get("prove_private_typed_admission_import_errors")
        require(import_target is not None, "typed admission private import negative missing")
        import_calls = [node for node in ast.walk(main) if isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name) and node.func.id == "prove_private_typed_admission_import_errors"]
        require(len(import_calls) == 1, "typed admission private import negative not executed exactly once")
        import_body = ast.get_source_segment(candidate, import_target)
        require(isinstance(import_body, str), "typed admission private import negative body unavailable")
        for token in ("SYNTHETIC_PRIVATE_TYPED_IMPORT_CANARY", "importlib.util.module_from_spec = private_import",
                      "exc.__suppress_context__", "typed admission module import unavailable"):
            require(token in import_body, "typed admission private import negative guard removed")

    verify(source)
    for label, scope, old, replacement in (
        ("invocation", "main", "    prove_private_typed_admission_paths(validator)\n", "    pass\n"),
        ("fault injection", "prove_private_typed_admission_paths", "        Path.resolve = private_resolve\n", "        pass\n"),
        ("context assertion", "prove_private_typed_admission_paths", "exc.__suppress_context__", "False"),
        ("stat fault injection", "prove_private_typed_admission_paths", "        Path.is_file = private_is_file\n", "        pass\n"),
        ("import invocation", "main", "    prove_private_typed_admission_import_errors(validator)\n", "    pass\n"),
        ("import fault injection", "prove_private_typed_admission_import_errors", "            importlib.util.module_from_spec = private_import\n", "            pass\n"),
        ("import context assertion", "prove_private_typed_admission_import_errors", "exc.__suppress_context__", "False"),
    ):
        # A source-wide anchor can repeat in unrelated tests; mutate only the named AST function.
        parsed = ast.parse(source)
        functions = {node.name: node for node in parsed.body if isinstance(node, ast.FunctionDef)}
        function = functions.get(scope)
        require(function is not None, "typed admission private path mutation scope missing")
        lines = source.splitlines(keepends=True)
        span = "".join(lines[function.lineno - 1:function.end_lineno])
        require(span.count(old) == 1, "typed admission private path scoped deletion anchor drift: " + label)
        lines[function.lineno - 1:function.end_lineno] = [span.replace(old, replacement, 1)]
        try:
            verify("".join(lines))
        except Fail:
            continue
        raise Fail("typed admission private path negative deletion accepted: " + label)
    print("PASS: typed admission private path/import fault, context and invocation deletion rejected")


def main() -> int:
    require(WRITER.is_file(), "typed evidence writer missing")
    require(VALIDATOR.is_file(), "typed admission validator missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    prove_helper_source_symlink_rejected()
    prove_helper_source_swap_during_import_is_pinned()
    prove_helper_parent_swap_after_pin_uses_original_source()
    prove_helper_ancestor_swap_during_fd_walk_rejected()
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
    prove_typed_private_path_negative_reachability()
    writer = load_module(WRITER, "memory_os_typed_non_resurrection_writer_load_negative")
    validator = load_module(VALIDATOR, "memory_os_typed_non_resurrection_load_negative")
    prove_typed_writer_json_reader(writer)
    prove_typed_json_reader(validator)
    prove_typed_json_reader_fd_races(validator)
    prove_typed_json_reader_descriptor_faults(validator)
    prove_typed_json_reader_platform_flags(validator)
    require(writer.canonical_repo_file(WRITER, "typed evidence writer") == WRITER, "canonical typed writer path rejected")

    prove_reconcile_runtime_authorities()
    prove_typed_reconcile_pinned_reader()
    prove_typed_reconcile_strict_json()
    prove_typed_reconcile_descriptor_faults()
    prove_typed_reconcile_platform_flags()
    prove_typed_reconcile_writer_ownership()
    prove_typed_reconcile_child_validator()
    prove_typed_reconcile_private_path_diagnostics()
    prove_typed_reconcile_repo_refs()
    prove_typed_reconcile_writer_preopen_faults()

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
