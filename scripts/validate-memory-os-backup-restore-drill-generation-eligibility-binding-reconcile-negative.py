#!/usr/bin/env python3
"""Prove drill-generation binding reconcile is canonical and transactionally fail-closed."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-generation-eligibility-binding.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-generation-eligibility-binding.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-generation-eligibility-binding-contract.v1.json"
DRILL_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load: {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_reconciler():
    return load_module(RECONCILER, "memory_os_drill_generation_binding_reconcile_negative")


def canonical_bytes() -> tuple[bytes, bytes]:
    return CONTRACT.read_bytes(), DRILL_REGISTRY.read_bytes()


def assert_canonical_unchanged(contract_bytes: bytes, registry_bytes: bytes, label: str) -> None:
    require(CONTRACT.read_bytes() == contract_bytes, f"canonical binding contract mutated while rejecting {label}")
    require(DRILL_REGISTRY.read_bytes() == registry_bytes, f"canonical drill registry mutated while rejecting {label}")


def expect_validator_substitution_rejected(validator: Any, attribute: str, replacement: Any) -> None:
    contract_bytes, registry_bytes = canonical_bytes()
    original = getattr(validator, attribute)
    setattr(validator, attribute, replacement)
    try:
        try:
            validator.main()
        except validator.Fail:
            pass
        else:
            raise Fail(f"binding validator unexpectedly accepted substitution: {attribute}")
        assert_canonical_unchanged(contract_bytes, registry_bytes, attribute)
    finally:
        setattr(validator, attribute, original)


def prove_validator_pinned_module_import(module_path: Path = VALIDATOR) -> None:
    """A post-check symlink swap must not execute external module bytes."""
    with tempfile.TemporaryDirectory(prefix="binding-module-source-") as temporary:
        root = Path(temporary) / "repo"
        package = root / "pkg"
        package.mkdir(parents=True)
        approved = package / "approved.py"
        approved.write_text("VALUE = 42\n", encoding="utf-8")
        outside = Path(temporary) / "outside.py"
        marker = Path(temporary) / "untrusted-executed"
        outside.write_text(
            "from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('unsafe')\n",
            encoding="utf-8",
        )
        validator = load_module(module_path, "memory_os_binding_pinned_module_negative")
        original_root = validator.ROOT
        original_check = validator.require_exact_repo_file
        validator.ROOT = root
        try:
            module = validator.load_module(
                approved, Path("pkg/approved.py"), "binding_safe_fixture", "fixture"
            )
            require(module.VALUE == 42, "pinned source positive control did not execute")

            def swapped_leaf(path: Path, expected: Path, field: str) -> Path:
                result = original_check(path, expected, field)
                if not approved.is_symlink():
                    approved.rename(package / "original.py")
                    approved.symlink_to(outside)
                return result

            validator.require_exact_repo_file = swapped_leaf
            try:
                validator.load_module(
                    approved, Path("pkg/approved.py"), "binding_leaf_swap", "fixture"
                )
            except validator.Fail:
                pass
            else:
                raise Fail("post-check symlinked module leaf was executed")
            require(not marker.exists(), "untrusted symlinked leaf module executed")

            approved.unlink()
            (package / "original.py").rename(approved)
            outside_package = Path(temporary) / "outside-pkg"
            outside_package.mkdir()
            (outside_package / "approved.py").write_text(
                outside.read_text(encoding="utf-8"), encoding="utf-8"
            )

            swapped = False
            def swapped_parent(path: Path, expected: Path, field: str) -> Path:
                nonlocal swapped
                result = original_check(path, expected, field)
                if not swapped:
                    swapped = True
                    package.rename(root / "pkg-original")
                    package.symlink_to(outside_package, target_is_directory=True)
                return result

            validator.require_exact_repo_file = swapped_parent
            try:
                validator.load_module(
                    approved, Path("pkg/approved.py"), "binding_parent_swap", "fixture"
                )
            except validator.Fail:
                pass
            else:
                raise Fail("post-check symlinked module parent was executed")
            require(not marker.exists(), "untrusted symlinked parent module executed")
        finally:
            validator.require_exact_repo_file = original_check
            validator.ROOT = original_root
    print("PASS pinned module import: " + module_path.name + " positive control, post-check leaf and parent swaps")


def prove_validator_execution_identity() -> None:
    validator = load_module(VALIDATOR, "memory_os_drill_generation_binding_validator_negative")
    path_cases = (
        ("CONTRACT", validator.DRILL_REGISTRY),
        ("DRILL_CONTRACT", validator.CONTRACT),
        ("DRILL_REGISTRY", validator.CONTRACT),
        ("DRILL_WRITER", validator.VALIDATOR),
        ("DRILL_VALIDATOR", validator.DRILL_NEGATIVE),
        ("DRILL_NEGATIVE", validator.VALIDATOR),
        ("ELIGIBILITY_CONTRACT", validator.CONTRACT),
        ("ELIGIBILITY_HELPER", validator.DRILL_WRITER),
        ("VALIDATOR", validator.DRILL_NEGATIVE),
        ("WORKFLOW", validator.CONTRACT),
    )
    for attribute, replacement in path_cases:
        expect_validator_substitution_rejected(validator, attribute, replacement)

    helper_cases = (
        ("require", lambda condition, message: None),
        ("exact_success", lambda result, label: None),
        ("require_exact_repo_file", lambda path, expected, field: path),
        ("enforce_runtime_authorities", lambda: None),
        ("load", lambda path: {}),
        ("load_module", lambda path, expected, name, field: object()),
        ("run_negative_suite", lambda: None),
        ("enforce_execution_identity", lambda: None),
    )
    for attribute, replacement in helper_cases:
        expect_validator_substitution_rejected(validator, attribute, replacement)

    original_run = validator.subprocess.run
    validator.subprocess.run = lambda *args, **kwargs: subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    try:
        contract_bytes, registry_bytes = canonical_bytes()
        try:
            validator.main()
        except validator.Fail:
            pass
        else:
            raise Fail("binding validator unexpectedly accepted subprocess transport substitution")
        assert_canonical_unchanged(contract_bytes, registry_bytes, "subprocess.run")
    finally:
        validator.subprocess.run = original_run

    print(f"PASS boundary: drill binding validator data/executable substitutions rejected: {len(path_cases)}")
    print(f"PASS boundary: drill binding validator execution helper substitutions rejected: {len(helper_cases) + 1}")


def expect_direct_authority_rejected(
    reconciler: Any,
    *,
    name: str,
    field: str,
    attribute: str,
    replacement: Path,
    canonical_contract: bytes,
    canonical_registry: bytes,
) -> None:
    original = getattr(reconciler, attribute)
    setattr(reconciler, attribute, replacement)
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require(f"{field} authority drift" in str(exc), f"{name} rejected at wrong boundary: {exc}")
        else:
            raise Fail(f"direct reconciler unexpectedly accepted: {name}")
        require(CONTRACT.read_bytes() == canonical_contract, f"canonical binding contract mutated while rejecting {name}")
        require(DRILL_REGISTRY.read_bytes() == canonical_registry, f"canonical drill registry mutated while rejecting {name}")
    finally:
        setattr(reconciler, attribute, original)


def prove_direct_authority_identity(reconciler: Any) -> None:
    canonical_contract = CONTRACT.read_bytes()
    canonical_registry = DRILL_REGISTRY.read_bytes()
    cases = (
        ("binding contract substitution", "drill generation binding contract", "CONTRACT", reconciler.DRILL_REGISTRY),
        ("drill registry substitution", "drill request registry", "DRILL_REGISTRY", reconciler.CONTRACT),
        ("drill writer substitution", "drill request writer", "DRILL_WRITER", reconciler.VALIDATOR),
        ("semantic helper substitution", "semantic generation eligibility helper", "ELIGIBILITY_HELPER", reconciler.DRILL_WRITER),
        ("binding validator substitution", "drill generation binding validator", "VALIDATOR", reconciler.OPERABILITY_VALIDATOR),
        ("operability validator substitution", "operability validator", "OPERABILITY_VALIDATOR", reconciler.VALIDATOR),
    )
    for name, field, attribute, replacement in cases:
        expect_direct_authority_rejected(
            reconciler,
            name=name,
            field=field,
            attribute=attribute,
            replacement=replacement,
            canonical_contract=canonical_contract,
            canonical_registry=canonical_registry,
        )
    print(f"PASS boundary: direct semantic-binding data/executable substitutions rejected: {len(cases)}")


def expect_reconcile_helper_substitution_rejected(reconciler: Any, field: str, replacement: Any) -> None:
    contract_bytes, registry_bytes = canonical_bytes()
    original = getattr(reconciler, field)
    setattr(reconciler, field, replacement)
    try:
        try:
            reconciler.main()
        except reconciler.Fail:
            pass
        else:
            raise Fail(f"semantic-binding reconciler unexpectedly accepted execution helper substitution: {field}")
        assert_canonical_unchanged(contract_bytes, registry_bytes, f"reconciler {field}")
    finally:
        setattr(reconciler, field, original)


def prove_reconciler_execution_identity(reconciler: Any) -> None:
    helper_cases = (
        ("require", lambda condition, message: None),
        ("require_exact_repo_file", lambda path, expected, field: path),
        ("enforce_runtime_authorities", lambda: None),
        ("load", lambda path: {}),
        ("load_module", lambda path, expected, name, field: object()),
        ("run_post_validator", lambda path, expected, field: None),
        ("atomic_write_text", lambda path, text: None),
        ("enforce_execution_identity", lambda: None),
    )
    for field, replacement in helper_cases:
        expect_reconcile_helper_substitution_rejected(reconciler, field, replacement)
    print(f"PASS boundary: direct semantic-binding reconcile execution helper substitutions rejected: {len(helper_cases)}")



def prove_post_validator_private_transport(reconciler: Any) -> None:
    """Pin both canonical child validators to isolated, bounded, private execution."""
    original_run = reconciler.subprocess.run
    marker = "synthetic-private-drill-generation-binding-post-validator-output"
    poisoned = {
        "PYTHONPATH": "SYNTHETIC_UNTRUSTED_IMPORT",
        "PYTHONHOME": "SYNTHETIC_UNTRUSTED_HOME",
        "PYTHONWARNINGS": "SYNTHETIC_UNTRUSTED_WARNINGS",
        "LD_PRELOAD": "SYNTHETIC_UNTRUSTED_LOADER",
        "DYLD_INSERT_LIBRARIES": "SYNTHETIC_UNTRUSTED_DYLD",
        "GIT_CONFIG_GLOBAL": "SYNTHETIC_UNTRUSTED_GIT_CONFIG",
        "SAFE_BINDING_POST_VALIDATOR_ENV": "preserved",
    }
    targets = (
        (reconciler.VALIDATOR, reconciler.VALIDATOR_REL, "drill generation binding validator"),
        (reconciler.OPERABILITY_VALIDATOR, reconciler.OPERABILITY_VALIDATOR_REL, "operability validator"),
    )
    seen: list[int | bool | None] = []

    def fake_run(exit_code):
        def run(argv, **kwargs):
            require(argv[0] == reconciler.sys.executable
                    and argv[1] in [str(path) for path, _, _ in targets],
                    "drill generation binding post-validator child target drift")
            require(kwargs.get("cwd") == reconciler.ROOT,
                    "drill generation binding post-validator cwd drift")
            require(kwargs.get("stdout") == reconciler.subprocess.DEVNULL
                    and kwargs.get("stderr") == reconciler.subprocess.DEVNULL,
                    "drill generation binding post-validator raw diagnostics captured")
            require(kwargs.get("timeout") == 120 and kwargs.get("check") is False,
                    "drill generation binding post-validator runtime budget drift")
            child_env = kwargs.get("env")
            require(isinstance(child_env, dict), "drill generation binding child environment missing")
            require(child_env.get("SAFE_BINDING_POST_VALIDATOR_ENV") == "preserved",
                    "drill generation binding benign environment lost")
            for key in ("PYTHONPATH", "PYTHONHOME", "PYTHONWARNINGS",
                        "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "GIT_CONFIG_GLOBAL"):
                require(key not in child_env, "drill generation binding inherited override: " + key)
            require(child_env == {
                key: value for key, value in reconciler.os.environ.items()
                if not key.startswith(("PYTHON", "LD_", "DYLD_", "GIT_"))
            }, "drill generation binding post-validator child environment drift")
            seen.append(exit_code)
            return subprocess.CompletedProcess(argv, exit_code, stdout=marker, stderr=marker)
        return run

    with patch.dict(reconciler.os.environ, poisoned):
        try:
            for path, relative, field in targets:
                reconciler.subprocess.run = fake_run(0)
                reconciler.run_post_validator(path, relative, field)
                for code in (1, False, None):
                    reconciler.subprocess.run = fake_run(code)
                    try:
                        reconciler.run_post_validator(path, relative, field)
                    except reconciler.Fail as exc:
                        require(str(exc) == f"post-reconcile {field} failed (raw output withheld)",
                                "drill generation binding post-validator failure class drift")
                        require(marker not in str(exc), "drill generation binding private output leaked")
                    else:
                        raise Fail("drill generation binding post-validator invalid return accepted")
                for failure in (OSError(marker), ValueError(marker), TypeError(marker),
                                subprocess.TimeoutExpired(["synthetic"], 120, output=marker, stderr=marker)):
                    def raise_failure(*_args, **_kwargs):
                        raise failure
                    reconciler.subprocess.run = raise_failure
                    try:
                        reconciler.run_post_validator(path, relative, field)
                    except reconciler.Fail as exc:
                        require(str(exc) == f"post-reconcile {field} unavailable or timed out (raw output withheld)",
                                "drill generation binding unavailable class drift")
                        require(marker not in str(exc), "drill generation binding exception details leaked")
                    else:
                        raise Fail("drill generation binding post-validator unavailable accepted")
        finally:
            reconciler.subprocess.run = original_run
    require(seen == [0, 1, False, None] * 2,
            "drill generation binding post-validator positive/negative controls incomplete")
    try:
        reconciler.run_post_validator(reconciler.CONTRACT, reconciler.CONTRACT_REL, "synthetic unreviewed validator")
    except reconciler.Fail as exc:
        require(str(exc) == "unreviewed drill generation binding post-validator",
                "drill generation binding unreviewed validator rejected at wrong boundary")
    else:
        raise Fail("drill generation binding unreviewed repository validator accepted")
    print("PASS: drill generation binding post-validators use isolated bounded private transport and closed targets")


def prove_atomic_writer_double_fault_and_fd_ownership(reconciler: Any) -> None:
    canonical_contract, canonical_registry = canonical_bytes()
    with tempfile.TemporaryDirectory(prefix=".tmp-drill-generation-binding-fd-", dir=TMP_PARENT) as raw:
        target = Path(raw) / "binding-atomic.json"
        target.write_text("{}\\n", encoding="utf-8")
        target.chmod(0o640)
        original = target.read_bytes()
        original_mode = stat.S_IMODE(target.stat().st_mode)
        original_mkstemp = reconciler.tempfile.mkstemp
        original_fdopen = reconciler.os.fdopen
        captured = []

        def capture_mkstemp(*args, **kwargs):
            fd, name = original_mkstemp(*args, **kwargs)
            captured.append((fd, Path(name)))
            return fd, name

        def reject_fdopen(*_args, **_kwargs):
            raise OSError("synthetic private binding fdopen failure")

        try:
            reconciler.tempfile.mkstemp = capture_mkstemp
            reconciler.os.fdopen = reject_fdopen
            try:
                reconciler.atomic_write_text(target, "{}")
            except reconciler.Fail as exc:
                require(str(exc) == "drill generation binding atomic write failed"
                        and exc.__suppress_context__ and exc.__cause__ is None,
                        f"binding fdopen failure leaked or changed diagnostic: {exc}")
            else:
                raise Fail("binding fdopen failure unexpectedly accepted")
        finally:
            reconciler.tempfile.mkstemp = original_mkstemp
            reconciler.os.fdopen = original_fdopen

        require(len(captured) == 1, "binding fdopen fixture did not acquire exactly one FD")
        fd, temp_path = captured[0]
        try:
            os.fstat(fd)
        except OSError:
            pass
        else:
            raise Fail("binding fdopen failure leaked raw FD")
        require(not temp_path.exists() and target.read_bytes() == original,
                "binding fdopen failure left temp or changed isolated authority")

        original_replace, original_unlink = reconciler.os.replace, reconciler.os.unlink
        seen = []

        def reject_replace(_source, _destination):
            raise OSError("synthetic private primary binding replace failure")

        def reject_unlink(path, *args, **kwargs):
            require(Path(path).parent == target.parent
                    and Path(path).name.startswith(f".{target.name}."),
                    "binding cleanup targeted unexpected authority")
            seen.append(Path(path))
            raise ValueError("synthetic private secondary binding cleanup failure")

        try:
            reconciler.os.replace = reject_replace
            reconciler.os.unlink = reject_unlink
            try:
                reconciler.atomic_write_text(target, "{} ")
            except reconciler.Fail as exc:
                require(str(exc) == "drill generation binding atomic write failed"
                        and exc.__suppress_context__ and exc.__cause__ is None,
                        f"binding cleanup masked primary failure: {exc}")
            else:
                raise Fail("binding atomic double-fault unexpectedly accepted")
        finally:
            reconciler.os.replace = original_replace
            reconciler.os.unlink = original_unlink
            for path in target.parent.glob(f".{target.name}.*.tmp"):
                original_unlink(path)

        require(len(seen) == 1 and target.read_bytes() == original
                and stat.S_IMODE(target.stat().st_mode) == original_mode,
                "binding atomic double-fault mutated isolated authority or missed cleanup")
        require(not list(target.parent.glob(f".{target.name}.*.tmp")),
                "binding atomic double-fault left temporary authority")
    assert_canonical_unchanged(canonical_contract, canonical_registry, "binding atomic FD/cleanup faults")
    print("PASS: drill generation binding fdopen ownership and primary atomic failure precedence")


def prove_rollback_double_fault_diagnostic(reconciler: Any) -> None:
    """A failed restore must retain the primary validator rejection."""
    canonical_contract, canonical_registry = canonical_bytes()
    with tempfile.TemporaryDirectory(prefix=".tmp-drill-generation-binding-rollback-", dir=TMP_PARENT) as raw:
        contract_copy = Path(raw) / CONTRACT.name
        registry_copy = Path(raw) / DRILL_REGISTRY.name
        shutil.copyfile(CONTRACT, contract_copy)
        shutil.copyfile(DRILL_REGISTRY, registry_copy)
        contract_copy.chmod(0o640)
        before = contract_copy.read_bytes()
        before_mode = stat.S_IMODE(contract_copy.stat().st_mode)
        original_contract = reconciler.CONTRACT
        original_registry = reconciler.DRILL_REGISTRY
        original_write = reconciler.atomic_write_text
        original_validator = reconciler.run_post_validator
        writes = []

        def fail_rollback(path: Path, text: str) -> None:
            require(path == contract_copy, "binding rollback targeted unexpected authority")
            writes.append(text)
            if len(writes) == 2:
                raise reconciler.Fail("synthetic private secondary binding rollback failure")
            original_write(path, text)

        def reject_post_validator(_path, _expected_relative, _field):
            raise reconciler.Fail("synthetic private primary binding validator failure")

        try:
            reconciler.CONTRACT = contract_copy
            reconciler.DRILL_REGISTRY = registry_copy
            reconciler.atomic_write_text = fail_rollback
            reconciler.run_post_validator = reject_post_validator
            try:
                reconciler._reconcile()
            except reconciler.Fail as exc:
                require(str(exc) == "drill generation binding reconcile failed (Fail); rollback incomplete (Fail)",
                        f"binding rollback double-fault diagnostic drift: {exc}")
                require(isinstance(exc.__cause__, reconciler.Fail)
                        and "synthetic private primary" in str(exc.__cause__),
                        "binding rollback double-fault lost primary exception chain")
                require("synthetic private" not in str(exc),
                        "binding rollback double-fault leaked private details")
            else:
                raise Fail("binding rollback double-fault unexpectedly accepted")
        finally:
            reconciler.CONTRACT = original_contract
            reconciler.DRILL_REGISTRY = original_registry
            reconciler.atomic_write_text = original_write
            reconciler.run_post_validator = original_validator
            # This fixture deliberately rejects rollback; restore only its
            # isolated authority after all fault injections are removed.
            original_write(contract_copy, before.decode("utf-8"))

        require(len(writes) == 2, "binding rollback double-fault did not attempt both writes")
        require(contract_copy.read_bytes() == before
                and stat.S_IMODE(contract_copy.stat().st_mode) == before_mode,
                "binding rollback double-fault fixture restoration drift")
        require(not list(contract_copy.parent.glob(f".{contract_copy.name}.*.tmp")),
                "binding rollback double-fault left temporary authority")
    assert_canonical_unchanged(canonical_contract, canonical_registry, "binding rollback double fault")
    print("PASS: binding rollback failure preserves primary exception and private-safe incomplete marker")


def prove_reconciler_strict_json_loader(reconciler: Any) -> None:
    canonical_contract, canonical_registry = canonical_bytes()
    with tempfile.TemporaryDirectory(prefix=".tmp-drill-generation-binding-json-", dir=TMP_PARENT) as raw:
        authority = Path(raw) / "binding-json.json"
        authority.write_bytes(b'{"safe":true}')
        require(reconciler.load(authority) == {"safe": True},
                "binding strict JSON positive control rejected")
        cases = (
            ("duplicate", b'{"safe":true,"safe":false}',
             "drill generation binding JSON duplicate key refused"),
            ("nonfinite", b'{"safe":NaN}',
             "drill generation binding JSON nonfinite number refused"),
            ("overflow float", b'{"safe":1e9999}',
             "drill generation binding JSON nonfinite number refused"),
            ("oversized integer", b'{"safe":' + b'9' * 129 + b'}',
             "drill generation binding JSON oversized integer refused"),
            ("oversized bytes", b'x' * (reconciler.MAX_BINDING_AUTHORITY_BYTES + 1),
             "drill generation binding JSON oversized authority refused"),
        )
        for label, payload, expected in cases:
            authority.write_bytes(payload)
            try:
                reconciler.load(authority)
            except reconciler.Fail as exc:
                require(str(exc) == expected,
                        f"binding JSON {label} rejected at wrong boundary: {exc}")
            else:
                raise Fail(f"binding JSON {label} ambiguity unexpectedly accepted")
    assert_canonical_unchanged(canonical_contract, canonical_registry, "binding strict JSON loader")
    print("PASS: binding reconciler strict JSON positive and five ambiguity/size negatives")


def prove_validator_strict_json_loader() -> None:
    validator = load_module(VALIDATOR, "memory_os_binding_strict_json_negative")
    canonical_contract, canonical_registry = canonical_bytes()
    with tempfile.TemporaryDirectory(prefix=".tmp-drill-generation-validator-json-", dir=TMP_PARENT) as raw:
        authority = Path(raw) / "validator-json.json"
        authority.write_bytes(b'{"safe":true}')
        require(validator.load(authority) == {"safe": True},
                "binding validator strict JSON positive control rejected")
        cases = (
            ("duplicate", b'{"safe":true,"safe":false}',
             "drill generation binding validator JSON duplicate key refused"),
            ("nonfinite", b'{"safe":Infinity}',
             "drill generation binding validator JSON nonfinite number refused"),
            ("overflow float", b'{"safe":1e9999}',
             "drill generation binding validator JSON nonfinite number refused"),
            ("oversized integer", b'{"safe":' + b'9' * 129 + b'}',
             "drill generation binding validator JSON oversized integer refused"),
            ("oversized bytes", b'x' * (validator.MAX_BINDING_AUTHORITY_BYTES + 1),
             "drill generation binding validator JSON oversized authority refused"),
        )
        for label, payload, expected in cases:
            authority.write_bytes(payload)
            try:
                validator.load(authority)
            except validator.Fail as exc:
                require(str(exc) == expected,
                        f"binding validator JSON {label} rejected at wrong boundary: {exc}")
            else:
                raise Fail(f"binding validator JSON {label} ambiguity unexpectedly accepted")
    assert_canonical_unchanged(canonical_contract, canonical_registry, "binding validator strict JSON")
    print("PASS: binding validator strict JSON positive and five ambiguity/size negatives")


def prove_validator_negative_suite_private_transport() -> None:
    validator = load_module(VALIDATOR, "memory_os_binding_negative_transport")
    canonical_contract, canonical_registry = canonical_bytes()
    original_run = validator.subprocess.run
    marker = "synthetic-private-binding-negative-suite-output"
    poisoned = {
        "PYTHONPATH": "SYNTHETIC_UNTRUSTED_IMPORT",
        "PYTHONHOME": "SYNTHETIC_UNTRUSTED_HOME",
        "LD_PRELOAD": "SYNTHETIC_UNTRUSTED_LOADER",
        "DYLD_INSERT_LIBRARIES": "SYNTHETIC_UNTRUSTED_DYLD",
        "GIT_CONFIG_GLOBAL": "SYNTHETIC_UNTRUSTED_GIT",
        "SAFE_BINDING_NEGATIVE_ENV": "preserved",
    }
    seen = []

    def fake_run(exit_code):
        def run(argv, **kwargs):
            require(argv == [validator.sys.executable, str(validator.DRILL_NEGATIVE)],
                    "binding negative suite child target drift")
            require(kwargs.get("cwd") == validator.ROOT
                    and kwargs.get("stdout") == validator.subprocess.DEVNULL
                    and kwargs.get("stderr") == validator.subprocess.DEVNULL
                    and kwargs.get("check") is False
                    and kwargs.get("timeout") == 120,
                    "binding negative suite private bounded transport drift")
            env = kwargs.get("env")
            require(isinstance(env, dict)
                    and env.get("SAFE_BINDING_NEGATIVE_ENV") == "preserved"
                    and all(key not in env for key in poisoned if key != "SAFE_BINDING_NEGATIVE_ENV"),
                    "binding negative suite inherited unreviewed loader environment")
            seen.append(exit_code)
            return subprocess.CompletedProcess(argv, exit_code)
        return run

    try:
        with patch.dict(os.environ, poisoned):
            validator.subprocess.run = fake_run(0)
            validator.run_negative_suite()
            for code in (1, False, None):
                validator.subprocess.run = fake_run(code)
                try:
                    validator.run_negative_suite()
                except validator.Fail as exc:
                    require(str(exc) == "drill request negative suite failed (raw output withheld)"
                            and marker not in str(exc),
                            f"binding negative suite invalid exit class drift: {exc}")
                else:
                    raise Fail("binding negative suite invalid exit unexpectedly accepted")
            for failure in (
                OSError(marker), ValueError(marker), TypeError(marker),
                subprocess.TimeoutExpired(["synthetic"], 120, output=marker, stderr=marker),
            ):
                def raise_failure(*_args, **_kwargs):
                    raise failure
                validator.subprocess.run = raise_failure
                try:
                    validator.run_negative_suite()
                except validator.Fail as exc:
                    require(str(exc) == "drill request negative suite unavailable or timed out (raw output withheld)"
                            and marker not in str(exc),
                            f"binding negative suite exception leaked private output: {exc}")
                else:
                    raise Fail("binding negative suite transport failure unexpectedly accepted")
    finally:
        validator.subprocess.run = original_run
    require(seen == [0, 1, False, None],
            "binding negative suite transport controls incomplete")
    assert_canonical_unchanged(canonical_contract, canonical_registry, "binding negative suite transport")
    print("PASS: binding negative suite isolated bounded private transport and strict typed exit")


def main() -> int:
    require(VALIDATOR.is_file(), "drill generation binding validator missing")
    require(RECONCILER.is_file(), "drill generation binding reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    prove_validator_execution_identity()
    prove_validator_pinned_module_import()
    prove_validator_pinned_module_import(RECONCILER)
    prove_validator_strict_json_loader()
    prove_validator_negative_suite_private_transport()
    reconciler = load_reconciler()
    prove_post_validator_private_transport(reconciler)
    prove_direct_authority_identity(reconciler)
    prove_reconciler_execution_identity(reconciler)
    prove_reconciler_strict_json_loader(reconciler)
    prove_atomic_writer_double_fault_and_fd_ownership(reconciler)
    prove_rollback_double_fault_diagnostic(reconciler)

    original_contract_path = reconciler.CONTRACT
    original_registry_path = reconciler.DRILL_REGISTRY
    original_post_validator = reconciler.run_post_validator
    original_os_replace = reconciler.os.replace

    # Fixture mutation is deliberately below the production CLI authority boundary:
    # direct main() remains canonical-only, while the internal reconcile core proves
    # append-only corruption rejection and transactional rollback.
    try:
        with tempfile.TemporaryDirectory(prefix=".tmp-drill-generation-binding-reconcile-", dir=TMP_PARENT) as tmpdir:
            tmp = Path(tmpdir)
            contract_copy = tmp / CONTRACT.name
            registry_copy = tmp / DRILL_REGISTRY.name
            shutil.copyfile(CONTRACT, contract_copy)
            shutil.copyfile(DRILL_REGISTRY, registry_copy)
            contract_copy.chmod(0o640)
            registry_copy.chmod(0o640)
            original_contract = contract_copy.read_bytes()
            original_contract_mode = stat.S_IMODE(contract_copy.stat().st_mode)
            canonical_registry: dict[str, Any] = json.loads(registry_copy.read_text(encoding="utf-8"))

            reconciler.CONTRACT = contract_copy
            reconciler.DRILL_REGISTRY = registry_copy

            corruption_cases: tuple[tuple[str, Callable[[dict[str, Any]], None]], ...] = (
                ("request registry schema drift", lambda value: value.__setitem__("schemaVersion", "broken")),
                ("request registry class drift", lambda value: value.__setitem__("registryClass", "BROKEN")),
                ("request registry append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
                ("request registry production evidence promoted", lambda value: value.__setitem__("productionEvidence", True)),
                ("request registry production ready promoted", lambda value: value.__setitem__("productionReady", True)),
                ("registered request boolean count", lambda value: value.__setitem__("registeredRequestCount", True)),
                ("current executable boolean count", lambda value: value.__setitem__("currentExecutableRequestCount", True)),
                ("registered request count drift", lambda value: value.__setitem__("registeredRequestCount", len(value.get("requests", [])) + 1)),
                ("current executable count drift", lambda value: value.__setitem__("currentExecutableRequestCount", len(value.get("requests", [])) + 1)),
            )
            for name, mutate in corruption_cases:
                corrupted = json.loads(json.dumps(canonical_registry))
                mutate(corrupted)
                registry_copy.write_text(json.dumps(corrupted, indent=2) + "\n", encoding="utf-8")
                try:
                    reconciler._reconcile()
                except reconciler.Fail as exc:
                    require("drill request append-only authority invalid" in str(exc), f"{name} rejected at wrong boundary: {exc}")
                except Exception as exc:
                    raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
                else:
                    raise Fail(f"corrupt drill request authority unexpectedly reconciled: {name}")
                require(contract_copy.read_bytes() == original_contract, f"{name} mutated semantic binding contract")
                require(
                    stat.S_IMODE(contract_copy.stat().st_mode) == original_contract_mode,
                    f"{name} mutated semantic binding contract mode",
                )
                print(f"PASS reject before reconcile: {name}")
            registry_copy.write_text(json.dumps(canonical_registry, indent=2) + "\n", encoding="utf-8")

            atomic_original = contract_copy.read_bytes()
            atomic_original_mode = stat.S_IMODE(contract_copy.stat().st_mode)
            replace_calls = 0

            def fail_first_replace(source: str | Path, destination: str | Path) -> None:
                nonlocal replace_calls
                replace_calls += 1
                if replace_calls == 1:
                    raise OSError("synthetic atomic replacement failure")
                original_os_replace(source, destination)

            reconciler.os.replace = fail_first_replace
            try:
                try:
                    reconciler._reconcile()
                except reconciler.Fail as exc:
                    require(str(exc) == "drill generation binding atomic write failed",
                            f"atomic replacement failed at wrong boundary: {exc}")
                except Exception as exc:
                    raise Fail(f"atomic replacement failure leaked unexpected exception: {type(exc).__name__}: {exc}") from exc
                else:
                    raise Fail("synthetic atomic replacement failure unexpectedly accepted")
                require(replace_calls == 2, f"atomic replacement failure did not perform exactly one rollback replace: {replace_calls}")
                require(contract_copy.read_bytes() == atomic_original, "failed atomic replacement mutated semantic binding contract")
                require(
                    stat.S_IMODE(contract_copy.stat().st_mode) == atomic_original_mode,
                    "failed atomic replacement mutated semantic binding contract mode",
                )
                require(
                    not list(contract_copy.parent.glob(f".{contract_copy.name}.*.tmp")),
                    "failed atomic replacement left temporary binding authority behind",
                )
            finally:
                reconciler.os.replace = original_os_replace
            print("PASS atomic replacement failure: contract bytes+mode preserved and temp cleaned")

            parsed_contract = json.loads(contract_copy.read_text(encoding="utf-8"))
            contract_copy.write_text(json.dumps(parsed_contract, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
            contract_copy.chmod(0o640)
            rollback_original = contract_copy.read_bytes()
            rollback_original_mode = stat.S_IMODE(contract_copy.stat().st_mode)
            observed: list[str] = []

            def aggregate_failure_after_binding_success(path: Path, expected_relative: Path, field: str) -> None:
                require(contract_copy.read_bytes() != rollback_original, "post-validator invoked before semantic binding write")
                require(
                    stat.S_IMODE(contract_copy.stat().st_mode) == rollback_original_mode,
                    "semantic binding candidate publication changed canonical authority mode",
                )
                observed.append(field)
                if len(observed) == 1:
                    require(field == "drill generation binding validator", "binding validator was not first post-write validator")
                    return
                require(len(observed) == 2, "unexpected extra post-write validator invocation")
                require(field == "operability validator", "operability validator was not second post-write validator")
                raise reconciler.Fail("synthetic aggregate operability rejection")

            reconciler.run_post_validator = aggregate_failure_after_binding_success
            try:
                reconciler._reconcile()
            except reconciler.Fail as exc:
                require("synthetic aggregate operability rejection" in str(exc), f"post-validation failure rejected at wrong boundary: {exc}")
            except Exception as exc:
                raise Fail(f"post-validation failure leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
            else:
                raise Fail("forced aggregate semantic binding post-validation failure unexpectedly accepted")
            require(observed == ["drill generation binding validator", "operability validator"], "canonical post-write validator order drift")
            require(contract_copy.read_bytes() == rollback_original, "failed aggregate validation left binding contract mutation")
            require(
                stat.S_IMODE(contract_copy.stat().st_mode) == rollback_original_mode,
                "failed aggregate validation changed semantic binding contract mode",
            )
            require(
                not list(contract_copy.parent.glob(f".{contract_copy.name}.*.tmp")),
                "failed aggregate validation left temporary binding authority behind",
            )
    finally:
        reconciler.CONTRACT = original_contract_path
        reconciler.DRILL_REGISTRY = original_registry_path
        reconciler.run_post_validator = original_post_validator
        reconciler.os.replace = original_os_replace

    print("Drill generation eligibility binding reconcile negative suite PASS")
    print("binding validator direct authority substitutions accepted: false")
    print("binding validator execution helper substitutions accepted: false")
    print("binding validator subprocess transport substitution accepted: false")
    print("direct reconciler data/executable authority substitutions accepted: false")
    print("direct reconciler execution helper substitutions accepted: false")
    print("production CLI authority weakened for fixtures: false")
    print("corrupt planning authority can be auto-healed: false")
    print("candidate publication preserves canonical authority mode: true")
    print("atomic replacement failure preserves canonical authority bytes+mode: true")
    print("atomic replacement temp cleanup: true")
    print("aggregate operability failure rolls back binding authority bytes+mode: true")
    print("aggregate operability rollback temp cleanup: true")
    print("failed post-validation leaves binding authority mutation behind: false")
    print("request created: false")
    print("production evidence: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DRILL GENERATION BINDING RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
