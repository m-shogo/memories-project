#!/usr/bin/env python3
"""Prove evidence-ownership reconciliation is exact-authority and transactional."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-operability-evidence-ownership.py"
WORKFLOW = ROOT / ".github/workflows/operability-evidence-ownership.yml"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "memory_os_operability_evidence_ownership_reconcile_negative", RECONCILER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load evidence ownership reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_atomic_diagnostic_publication() -> None:
    if not WORKFLOW.is_file():
        raise RuntimeError("evidence ownership workflow missing")
    text = WORKFLOW.read_text(encoding="utf-8")
    required = (
        "tempfile.mkstemp(",
        "dir=path.parent",
        "handle.flush()",
        "os.fsync(handle.fileno())",
        "os.replace(tmp_name, path)",
        "os.unlink(tmp_name)",
    )
    missing = [fragment for fragment in required if fragment not in text]
    if missing:
        raise RuntimeError(
            f"evidence ownership diagnostic publication is not crash-safe: missing {missing}"
        )
    if "path.write_text(json.dumps(value" in text:
        raise RuntimeError("evidence ownership diagnostic publication regressed to direct write_text")


def expect_authority_identity(reconciler) -> None:
    reconciler.enforce_runtime_authorities()
    original_contract = reconciler.CANONICAL_CONTRACT.read_bytes()
    substitutions = (
        (
            "CONTRACT",
            ROOT / "contracts/operations/production-operability-status.json",
            "ownership contract",
        ),
        ("VALIDATOR", reconciler.OPERABILITY_VALIDATOR, "ownership validator"),
        ("OPERABILITY_VALIDATOR", reconciler.VALIDATOR, "operability validator"),
        (
            "WORKFLOW",
            ROOT / ".github/workflows/operability-contracts.yml",
            "ownership workflow",
        ),
    )
    for attribute, substitute, label in substitutions:
        original = getattr(reconciler, attribute)
        try:
            setattr(reconciler, attribute, substitute)
            try:
                reconciler.enforce_runtime_authorities()
            except reconciler.ReconcileFailure as exc:
                if "authority drift" not in str(exc) and "authority missing" not in str(exc):
                    raise RuntimeError(f"{label} rejected for unrelated reason: {exc}") from exc
            else:
                raise RuntimeError(f"reconciler accepted authority substitution: {label}")
        finally:
            setattr(reconciler, attribute, original)

    if reconciler.CANONICAL_CONTRACT.read_bytes() != original_contract:
        raise RuntimeError("ownership contract changed after authority substitution rejection")
    reconciler.enforce_runtime_authorities()


def prove_validator_chain(reconciler) -> None:
    observed: list[Path] = []
    original_run_validator = reconciler.run_validator

    def capture(path: Path, _label: str) -> None:
        observed.append(path.resolve())

    try:
        reconciler.run_validator = capture
        reconciler.validate_written_authority()
    finally:
        reconciler.run_validator = original_run_validator

    expected = [
        reconciler.VALIDATOR.resolve(),
        reconciler.OPERABILITY_VALIDATOR.resolve(),
    ]
    if observed != expected:
        raise RuntimeError(f"validator chain drift: {observed!r} != {expected!r}")


def prove_noop_validation(reconciler) -> None:
    original = reconciler.CANONICAL_CONTRACT.read_bytes()
    observed: list[Path] = []
    original_run_validator = reconciler.run_validator

    def capture(path: Path, _label: str) -> None:
        observed.append(path.resolve())

    try:
        reconciler.run_validator = capture
        code = reconciler.main()
        if code != 0:
            raise RuntimeError(f"no-op reconcile returned {code}")
    finally:
        reconciler.run_validator = original_run_validator

    expected = [
        reconciler.VALIDATOR.resolve(),
        reconciler.VALIDATOR.resolve(),
        reconciler.OPERABILITY_VALIDATOR.resolve(),
    ]
    if observed != expected:
        raise RuntimeError(f"no-op validator chain drift: {observed!r} != {expected!r}")
    if reconciler.CANONICAL_CONTRACT.read_bytes() != original:
        raise RuntimeError("no-op reconcile changed ownership contract bytes")


def prove_transaction_rollback(reconciler) -> None:
    original = reconciler.CANONICAL_CONTRACT.read_bytes()
    contract = copy.deepcopy(load_json(reconciler.CANONICAL_CONTRACT))
    contract["_negativeTransactionalProbe"] = True

    original_validate = reconciler.validate_written_authority
    reconciler.validate_written_authority = lambda: (_ for _ in ()).throw(
        reconciler.ReconcileFailure("synthetic aggregate validation failure")
    )
    try:
        try:
            reconciler.transactional_write(contract)
        except reconciler.ReconcileFailure as exc:
            if "synthetic aggregate validation failure" not in str(exc):
                raise RuntimeError(f"rollback failed for unrelated reason: {exc}") from exc
        else:
            raise RuntimeError("transactional write accepted synthetic aggregate validation failure")
        if reconciler.CANONICAL_CONTRACT.read_bytes() != original:
            raise RuntimeError("ownership contract rollback was not byte-for-byte")
    finally:
        reconciler.validate_written_authority = original_validate
        if reconciler.CANONICAL_CONTRACT.read_bytes() != original:
            reconciler.CANONICAL_CONTRACT.write_bytes(original)


def validate_reconciler_atomic_source() -> None:
    whole = RECONCILER_PATH.read_text(encoding="utf-8")
    if whole.count("def atomic_write(") != 1 or whole.count("\ndef transactional_write(") != 1:
        raise RuntimeError("ownership atomic function scope drift")
    text = whole.split("def atomic_write(", 1)[1].split("\ndef transactional_write(", 1)[0]
    required = (
        "if not path.parent.is_dir():",
        "if candidate.is_symlink():",
        "if path.exists() and not path.is_file():",
        "stat.S_IMODE(path.stat().st_mode)",
        "os.fchmod(fd, existing_mode)",
        "os.fsync(handle.fileno())",
        "os.replace(temporary_path, path)",
        "temporary_path.unlink()",
    )

    def require_source(value: str) -> None:
        for fragment in required:
            if value.count(fragment) != 1:
                raise RuntimeError("ownership reconciler atomic source drift: " + fragment)
        if "path.parent.mkdir(parents=True, exist_ok=True)" in value:
            raise RuntimeError("ownership reconciler atomic parent may be created")

    require_source(text)
    for fragment in required:
        changed = text.replace(fragment, "pass  # synthetic mutation", 1)
        if changed == text:
            raise RuntimeError("ownership reconciler mutation fixture missing: " + fragment)
        try:
            require_source(changed)
        except RuntimeError:
            continue
        raise RuntimeError("ownership reconciler accepted atomic mutation: " + fragment)


def prove_atomic_file_guards(reconciler) -> None:
    import os
    import stat
    import tempfile

    with tempfile.TemporaryDirectory(prefix="ownership-authority-atomic-") as tmp:
        root = Path(tmp)
        parent = root / "inside"
        parent.mkdir()
        target = parent / "authority.json"
        target.write_bytes(b"original\n")
        target.chmod(0o640)
        reconciler.atomic_write(target, b"next\n")
        if target.read_bytes() != b"next\n" or stat.S_IMODE(target.stat().st_mode) != 0o640:
            raise RuntimeError("ownership atomic positive mode/bytes drift")

        for name in ("replace", "fsync"):
            original = getattr(reconciler.os, name)

            def fail(*_args, **_kwargs):
                raise OSError("synthetic " + name + " failure")

            try:
                setattr(reconciler.os, name, fail)
                try:
                    reconciler.atomic_write(target, b"should-not-publish\n")
                except OSError as exc:
                    if "synthetic " + name + " failure" not in str(exc):
                        raise RuntimeError("ownership atomic failure wrong reason") from exc
                else:
                    raise RuntimeError("ownership atomic accepted injected " + name + " failure")
            finally:
                setattr(reconciler.os, name, original)
            if (target.read_bytes() != b"next\n" or
                stat.S_IMODE(target.stat().st_mode) != 0o640 or
                list(parent.glob(".authority.json.*.tmp"))):
                raise RuntimeError("ownership atomic failure corrupted prior bytes/mode/temp")

        canary = root / "external-canary"
        canary.write_bytes(b"external\n")
        target.unlink()
        target.symlink_to(canary)
        try:
            reconciler.atomic_write(target, b"invalid\n")
        except reconciler.ReconcileFailure as exc:
            if "symlink" not in str(exc):
                raise RuntimeError("ownership target symlink rejected for wrong reason") from exc
        else:
            raise RuntimeError("ownership atomic followed target symlink")
        if canary.read_bytes() != b"external\n":
            raise RuntimeError("ownership atomic changed target symlink canary")
        target.unlink()

        outside = root / "outside"
        outside.mkdir()
        (outside / target.name).write_bytes(b"outside\n")
        original_parent = root / "original-parent"
        parent.rename(original_parent)
        parent.symlink_to(outside, target_is_directory=True)
        try:
            reconciler.atomic_write(target, b"invalid\n")
        except reconciler.ReconcileFailure as exc:
            if "symlink" not in str(exc):
                raise RuntimeError("ownership parent symlink rejected for wrong reason") from exc
        else:
            raise RuntimeError("ownership atomic followed parent symlink")
        if (outside / target.name).read_bytes() != b"outside\n":
            raise RuntimeError("ownership atomic changed parent symlink canary")
        parent.unlink()
        original_parent.rename(parent)

        target.mkdir()
        try:
            reconciler.atomic_write(target, b"invalid\n")
        except reconciler.ReconcileFailure as exc:
            if "regular" not in str(exc):
                raise RuntimeError("ownership directory target rejected for wrong reason") from exc
        else:
            raise RuntimeError("ownership atomic accepted directory target")
        target.rmdir()
        parent.rmdir()
        try:
            reconciler.atomic_write(target, b"invalid\n")
        except reconciler.ReconcileFailure as exc:
            if "parent missing" not in str(exc):
                raise RuntimeError("ownership missing parent rejected for wrong reason") from exc
        else:
            raise RuntimeError("ownership atomic created missing parent")
        if parent.exists():
            raise RuntimeError("ownership atomic created missing parent")

    print("PASS: ownership reconciler atomic source (8 mutations)")
    print("PASS: ownership reconciler mode, replace/fsync rollback, symlink and path runtime (7 cases)")


def main() -> int:
    reconciler = load_module()
    validate_atomic_diagnostic_publication()
    validate_reconciler_atomic_source()
    prove_atomic_file_guards(reconciler)
    expect_authority_identity(reconciler)
    prove_validator_chain(reconciler)
    prove_noop_validation(reconciler)
    prove_transaction_rollback(reconciler)

    print("PASS: evidence ownership diagnostic publication is atomic and crash-safe")
    print("PASS: evidence ownership data/executable authorities reject substitution")
    print("PASS: no-op reconciliation still validates ownership and aggregate operability")
    print("PASS: post-write aggregate failure restores ownership contract byte-for-byte")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
