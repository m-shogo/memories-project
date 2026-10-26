#!/usr/bin/env python3
"""Prove the strict OPS-P0-007 snapshot generator cannot bypass canonical execution helpers."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate-memory-os-ops-p0-007-admission-snapshot.py"
SNAPSHOT = ROOT / "contracts/operations/ops-p0-007-admission-snapshot.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"

# Failure-injection probes must preserve every OPS-P0-007 recovery authority,
# not just the generated projection and its production-status input.
PROTECTED_AUTHORITIES = (
    SNAPSHOT,
    STATUS,
    GENERATOR,
    ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    ROOT / "contracts/operations/recovery-objectives-registry.v1.json",
    ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json",
    ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
    ROOT / "contracts/operations/backup-restore-promotion-review-registry.v1.json",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module():
    require(GENERATOR.is_file() and not GENERATOR.is_symlink(), "canonical strict snapshot generator missing or symlinked")
    require(GENERATOR.resolve(strict=True).relative_to(ROOT.resolve()) == GENERATOR.relative_to(ROOT), "strict snapshot generator path drift")
    spec = importlib.util.spec_from_file_location("memory_os_ops_p0_007_snapshot_generator_execution_authority_negative", GENERATOR)
    require(spec is not None and spec.loader is not None, "cannot load strict snapshot generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def protected_state(path: Path) -> tuple[Any, ...]:
    """Capture bytes plus file and parent identity; following a symlink is not enough."""
    entry = path.lstat()
    parent = path.parent.lstat()
    return (
        path.read_bytes(),
        (entry.st_mode, entry.st_dev, entry.st_ino),
        (parent.st_mode, parent.st_dev, parent.st_ino),
        path.resolve(strict=True),
    )


def prove_symlink_identity_rejected() -> None:
    # Only mutate a temporary authority fixture, never the canonical checkout.
    with tempfile.TemporaryDirectory(prefix="ops-p0-007-generator-identity-") as tmp:
        root = Path(tmp)
        parent = root / "authority"
        parent.mkdir()
        path = parent / "snapshot.json"
        path.write_text('{"productionDecision":"NO_GO"}\n', encoding="utf-8")
        original_state = protected_state(path)
        original = parent / "original.json"
        path.rename(original)
        path.symlink_to(original.name)
        require(path.read_bytes() == original.read_bytes(), "symlink fixture content drift")
        require(
            protected_state(path) != original_state,
            "symlink alias with identical bytes bypassed protected identity",
        )
        path.unlink()
        original.rename(path)
        require(protected_state(path) == original_state, "identity fixture restoration drift")

        actual_parent = root / "actual"
        parent.rename(actual_parent)
        parent.symlink_to(actual_parent.name, target_is_directory=True)
        require(path.read_bytes() == original_state[0], "parent symlink fixture content drift")
        require(
            protected_state(path) != original_state,
            "parent symlink alias with identical bytes bypassed protected identity",
        )


def require_clean_rejection_stdout(output: str, label: str) -> None:
    require(
        not output.strip(),
        f"{label} rejection emitted unexpected success stdout",
    )


def prove_rejection_stdout_classifier() -> None:
    require_clean_rejection_stdout("", "synthetic clean")
    for output in (
        "Memory OS OPS-P0-007 strict admission snapshot generated\n",
        "production decision: GO\n",
        "Memory OS recovery objectives validation PASS\n",
    ):
        try:
            require_clean_rejection_stdout(output, "synthetic mixed")
        except Fail as exc:
            require(
                str(exc) == "synthetic mixed rejection emitted unexpected success stdout",
                f"mixed generator output rejected outside intended classifier: {exc}",
            )
        else:
            raise Fail("generator execution rejection accepted mixed success output")


def expect_rejected(module: Any, field: str, replacement: Any, expected_diagnostic: str | None = None) -> None:
    expected = expected_diagnostic or (
        "strict snapshot generator execution guard drift"
        if field == "enforce_execution_authority"
        else "strict snapshot generator runtime authority guard drift"
        if field == "enforce_runtime_authorities"
        else "strict snapshot generator execution helper drift"
    )
    original = getattr(module, field)
    protected_before = {path: protected_state(path) for path in PROTECTED_AUTHORITIES}
    setattr(module, field, replacement)
    rejected = False
    output = StringIO()
    try:
        with redirect_stdout(output):
            module.main()
    except SystemExit as exc:
        require(
            isinstance(exc.code, str) and exc.code == expected,
            f"{field} rejected outside intended strict snapshot guard: {exc}",
        )
        rejected = True
    finally:
        setattr(module, field, original)
    require(rejected, f"strict snapshot generator accepted substituted execution authority: {field}")
    require_clean_rejection_stdout(output.getvalue(), field)
    for path, state in protected_before.items():
        require(protected_state(path) == state, f"{field} rejection changed protected authority identity: {path.relative_to(ROOT)}")


def prove_json_reader_negative(module: Any) -> None:
    """Prove generator admission with disposable JSON and no authority writes."""
    with tempfile.TemporaryDirectory(prefix="ops-p0-007-generator-json-", dir=ROOT) as directory:
        path = Path(directory) / "candidate.json"
        positive = b'{"safe":true,"nested":{"count":1}}'
        path.write_bytes(positive)
        require(
            module.load(path) == {"safe": True, "nested": {"count": 1}},
            "generator JSON reader positive control failed",
        )
        cases = (
            ("duplicate root", b'{"safe":true,"safe":false}', "generated strict snapshot invalid: duplicate JSON key"),
            ("duplicate nested", b'{"nested":{"a":1,"a":2}}', "generated strict snapshot invalid: duplicate JSON key"),
            ("NaN", b'{"number":NaN}', "generated strict snapshot invalid: nonfinite JSON number"),
            ("Infinity", b'{"number":Infinity}', "generated strict snapshot invalid: nonfinite JSON number"),
            ("negative Infinity", b'{"number":-Infinity}', "generated strict snapshot invalid: nonfinite JSON number"),
            ("float overflow", b'{"number":1e999}', "generated strict snapshot invalid: nonfinite JSON number"),
            ("oversized integer", b'{"number":' + b"9" * 5000 + b"}", "generated strict snapshot invalid: JSON integer too large"),
            ("oversized JSON", b'{"payload":"' + b"x" * module.MAX_JSON_BYTES + b'"}', "generated strict snapshot invalid: JSON exceeds 1 MiB"),
            ("invalid UTF-8", b'{"private":"\\xff"}'.replace(b"\\xff", bytes([255])), "generated strict snapshot invalid: JSON unreadable or malformed"),
            ("malformed private input", b'{"private":"synthetic-secret",', "generated strict snapshot invalid: JSON unreadable or malformed"),
            ("non-object root", b"[]", "generated strict snapshot invalid: JSON root not object"),
        )

        def rejected(candidate: Any, expected: str, label: str) -> None:
            try:
                module.load(candidate)
            except SystemExit as exc:
                require(exc.code == expected, f"{label}: rejected outside exact generator JSON guard")
            else:
                raise Fail(f"{label}: unsafe generator JSON accepted")

        for label, payload, expected in cases:
            path.write_bytes(payload)
            rejected(path, expected, label)

        path.write_bytes(positive)
        alias = Path(directory) / "alias.json"
        alias.symlink_to(path)
        rejected(alias, "generated strict snapshot invalid: JSON path unsafe", "symlink")
        alias_dir = Path(directory) / "alias-dir"
        alias_dir.symlink_to(Path(directory), target_is_directory=True)
        rejected(alias_dir / path.name, "generated strict snapshot invalid: JSON path unsafe", "symlink ancestor")
        rejected(Path(directory), "generated strict snapshot invalid: JSON path unsafe", "directory")
        rejected("candidate.json", "generated strict snapshot invalid: JSON path invalid", "non-Path")
        with tempfile.TemporaryDirectory(prefix="ops-p0-007-generator-external-") as outside:
            canary = Path(outside) / "canary.json"
            canary.write_bytes(positive)
            rejected(canary, "generated strict snapshot invalid: JSON path missing or outside repository", "external path")
            require(canary.read_bytes() == positive, "generator JSON reader modified external canary")
        path.unlink()
        rejected(path, "generated strict snapshot invalid: JSON path missing or outside repository", "missing path")


def main() -> int:
    module = load_module()
    prove_json_reader_negative(module)
    prove_rejection_stdout_classifier()
    prove_symlink_identity_rejected()
    # A byte-identical symlink is not a canonical protected authority.
    for path in PROTECTED_AUTHORITIES:
        require(path.is_file() and not path.is_symlink() and not path.parent.is_symlink()
                and path.resolve(strict=True) == path,
                f"generator execution protected authority path drift: {path.relative_to(ROOT)}")
    baseline_state = {path: protected_state(path) for path in PROTECTED_AUTHORITIES}

    substitutions = (
        ("enforce_execution_authority", lambda: None),
        ("require_exact_repo_file", lambda *_args: None),
        ("enforce_runtime_authorities", lambda: None),
        ("atomic_write_text", lambda *_args: None),
        ("load", lambda _path: {}),
        ("load_module", lambda *_args: object()),
        ("validate_registry", lambda *_args: []),
        ("run_canonical_validator", lambda *_args: None),
        ("run_full_admission_validators", lambda: None),
        ("validate_generated_snapshot", lambda: None),
        ("load_helper", lambda: object()),
    )
    # Canonical guard must pass before any substitution can count as a rejection.
    module.enforce_execution_authority()
    for field, replacement in substitutions:
        expect_rejected(module, field, replacement)

    # Runtime path constants must be bound to their canonical repository files.
    # A same-type existing but wrong file is not a valid authority alias.
    path_substitutions = (
        ("OUTPUT", module.STATUS, "snapshot output"),
        ("STATUS", module.OBJECTIVES, "production operability status"),
        ("ELIGIBILITY_HELPER", module.BLOCKER_HELPER, "environment generation eligibility helper"),
        ("BLOCKER_HELPER", module.ELIGIBILITY_HELPER, "backup/restore blocker helper"),
        ("SNAPSHOT_VALIDATOR", module.RECOVERY_OBJECTIVE_VALIDATOR, "snapshot validator"),
        ("RECOVERY_OBJECTIVE_VALIDATOR", module.SNAPSHOT_VALIDATOR, "recovery objective admission validator"),
        ("DRILL_REQUEST_VALIDATOR", module.GEN_EVIDENCE_VALIDATOR, "reviewed drill request admission validator"),
        ("GEN_EVIDENCE_VALIDATOR", module.TYPED_VALIDATOR, "generation recovery evidence admission validator"),
        ("TYPED_VALIDATOR", module.GEN_EVIDENCE_VALIDATOR, "typed non-resurrection admission validator"),
        ("OBJECTIVES", module.DRILL_REQUESTS, "recovery objective registry"),
        ("DRILL_REQUESTS", module.OBJECTIVES, "restore drill request registry"),
        ("GEN_EVIDENCE", module.TYPED, "generation recovery evidence registry"),
        ("TYPED", module.GEN_EVIDENCE, "typed non-resurrection registry"),
        ("OBJECTIVE_WRITER", module.DRILL_REQUEST_WRITER, "recovery objective writer"),
        ("DRILL_REQUEST_WRITER", module.OBJECTIVE_WRITER, "restore drill request writer"),
        ("GEN_EVIDENCE_WRITER", module.TYPED_WRITER, "generation recovery evidence writer"),
        ("TYPED_WRITER", module.GEN_EVIDENCE_WRITER, "typed non-resurrection writer"),
    )
    for field, replacement, label in path_substitutions:
        require(getattr(module, field) != replacement, f"generator path mutation was a no-op: {field}")
        expect_rejected(module, field, replacement, f"strict snapshot authority drift: {label}")

    module.enforce_execution_authority()
    for path, state in baseline_state.items():
        require(protected_state(path) == state, f"generator execution authority probes changed protected identity: {path.relative_to(ROOT)}")
    json.loads(baseline_state[SNAPSHOT][0].decode("utf-8"))
    json.loads(baseline_state[STATUS][0].decode("utf-8"))

    print("Memory OS OPS-P0-007 strict snapshot generator execution authority negative PASS")
    print(f"execution helper substitutions rejected: {len(substitutions)}")
    print(f"canonical runtime path substitutions rejected: {len(path_substitutions)}")
    print("full admission validator no-op substitution accepted: false")
    print("post-write validator no-op substitution accepted: false")
    print("atomic publication helper substitution accepted: false")
    print("rejected probes changed OPS-P0-007 snapshot/status/generator/recovery-registry identity: false")
    print("isolated file and parent symlink identity bypass accepted: false")
    print("production evidence created: false")
    print("production ready: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, OSError, json.JSONDecodeError) as exc:
        print(f"OPS-P0-007 SNAPSHOT GENERATOR EXECUTION AUTHORITY NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
