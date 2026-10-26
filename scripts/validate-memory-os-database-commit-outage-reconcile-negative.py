#!/usr/bin/env python3
"""Negative proof for database commit outage authority identity and transaction."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-database-commit-outage.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "memory_os_database_outage_reconcile_negative", RECONCILER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load database outage reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_authority_rejection(module, attr: str, replacement: Path) -> None:
    original = getattr(module, attr)
    setattr(module, attr, replacement)
    try:
        try:
            module.enforce_runtime_authorities()
        except module.ReconcileFailure:
            pass
        else:
            raise RuntimeError(f"database outage {attr} substitution must be rejected")
    finally:
        setattr(module, attr, original)


def expect_reconcile_failure(module, expected: str) -> None:
    try:
        module.main()
    except module.ReconcileFailure as exc:
        if expected not in str(exc):
            raise RuntimeError(f"unexpected database outage rejection: {exc}") from exc
    else:
        raise RuntimeError(f"database outage reconcile accepted invalid authority: {expected}")


def stale_status_bytes(module) -> bytes:
    status = {
        "productionDecision": "NO_GO",
        "areas": [
            {
                "id": "OPS-P0-009",
                "status": "PARTIAL",
                "existingEvidence": [],
                "missingEvidence": [
                    module.OLD_MISSING,
                    "mixed-version failure",
                    "production multi-instance",
                    "production-shaped object-store",
                    "production-shaped PostgreSQL",
                    "host or container restart",
                    "expired sessions",
                ],
                "evidenceRefs": [],
            }
        ],
    }
    return json.dumps(status, indent=2).encode("utf-8") + b"\n"



def verify_database_outage_strict_json_and_duration() -> None:
    """Exercise real database outage reader and full-result duration validation."""
    path = ROOT / "scripts/validate-memory-os-database-commit-outage.py"
    spec = importlib.util.spec_from_file_location("database_outage_strict_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("database outage strict validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    canonical = validator.load(validator.RESULT_PATH)
    validator.validate_result(copy.deepcopy(canonical), None)
    for label, duration in (
        ("boolean", True), ("NaN", float("nan")), ("infinity", float("inf")),
        ("negative", -1), ("huge integer", 10 ** 500),
    ):
        mutated = copy.deepcopy(canonical)
        mutated["durationSeconds"] = duration
        try:
            validator.validate_result(mutated, None)
        except validator.ValidationFailure as exc:
            if str(exc) != "database outage duration is invalid":
                raise RuntimeError(f"database outage {label} rejected by wrong gate") from None
        else:
            raise RuntimeError(f"database outage accepted {label} duration")
    with tempfile.TemporaryDirectory(prefix="database-outage-reader-outside-") as outside_temp:
        outside = Path(outside_temp)
        canary = outside / "canary.json"
        canary.write_text('{"synthetic":true}', encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix=".database-outage-reader-", dir=ROOT) as inside_temp:
            inside = Path(inside_temp)
            good = inside / "good.json"
            good.write_text('{"safe":true}', encoding="utf-8")
            if validator.load(good) != {"safe": True}:
                raise RuntimeError("database outage JSON positive read failed")
            malformed = (
                ("nested duplicate", '{"a":{"key":1,"key":2}}'),
                ("nonfinite constant", '{"value":NaN}'),
                ("nonfinite exponent", '{"value":1e999}'),
                ("oversized integer", '{"value":' + "9" * 5000 + '}'),
                ("nonobject root", '["safe"]'),
                ("synthetic secret malformed", '{"SYNTHETIC_OUTAGE_SECRET":'),
            )
            for label, raw in malformed:
                document = inside / (label.replace(" ", "-") + ".json")
                document.write_text(raw, encoding="utf-8")
                try:
                    validator.load(document)
                except validator.ValidationFailure as exc:
                    if "SYNTHETIC_OUTAGE_SECRET" in str(exc):
                        raise RuntimeError("database outage reader reflected synthetic secret") from None
                else:
                    raise RuntimeError(f"database outage reader accepted {label}")
            invalid_utf8 = inside / "invalid-utf8.json"
            invalid_utf8.write_bytes(b'{"value":"\\xff"}'.replace(b'\\xff', bytes([255])))
            try:
                validator.load(invalid_utf8)
            except validator.ValidationFailure:
                pass
            else:
                raise RuntimeError("database outage reader accepted invalid UTF-8")
            linked = inside / "linked.json"
            linked.symlink_to(canary)
            linked_parent = inside / "linked-parent"
            linked_parent.symlink_to(outside, target_is_directory=True)
            directory = inside / "directory.json"
            directory.mkdir()
            for label, unsafe in (
                ("external file", canary), ("direct symlink", linked),
                ("symlinked ancestor", linked_parent / "canary.json"),
                ("directory", directory), ("missing file", inside / "missing.json"),
            ):
                try:
                    validator.load(unsafe)
                except validator.ValidationFailure:
                    pass
                else:
                    raise RuntimeError(f"database outage reader accepted {label}")
        if canary.read_text(encoding="utf-8") != '{"synthetic":true}':
            raise RuntimeError("database outage reader changed external canary")
    print("PASS: database outage JSON/path positive, 12 reader and 5 duration negatives")


def main() -> int:
    verify_database_outage_strict_json_and_duration()
    module = load_module()
    original_status = module.STATUS_PATH.read_bytes()

    expect_authority_rejection(module, "RESULT_PATH", module.STATUS_PATH)
    expect_authority_rejection(module, "STATUS_PATH", module.RESULT_PATH)
    expect_authority_rejection(module, "DATABASE_VALIDATOR", module.OPERABILITY_VALIDATOR)
    expect_authority_rejection(module, "OPERABILITY_VALIDATOR", module.DATABASE_VALIDATOR)
    if module.STATUS_PATH.read_bytes() != original_status:
        raise RuntimeError("database outage authority substitution changed canonical Production Status")

    source_sha = "0" * 40
    with tempfile.TemporaryDirectory(prefix="memory-os-database-outage-negative-") as tmp:
        root = Path(tmp)
        result_path = root / "result.json"
        status_path = root / "status.json"
        result_path.write_text(json.dumps({"commitSha": source_sha}) + "\n", encoding="utf-8")
        original_bytes = stale_status_bytes(module)
        status_path.write_bytes(original_bytes)

        module.RESULT_PATH = result_path
        module.STATUS_PATH = status_path
        module.source_is_ancestor = lambda _sha: True
        # This isolated fixture intentionally replaces canonical data paths so
        # the transaction can be tested without touching repository authority.
        module.enforce_runtime_authorities = lambda: None

        calls: list[str] = []
        atomic_calls: list[tuple[Path, bytes]] = []
        canonical_atomic_write = module.atomic_write_bytes

        def tracked_atomic_write(path: Path, payload: bytes) -> None:
            atomic_calls.append((path, bytes(payload)))
            canonical_atomic_write(path, payload)

        def reject_after_write(validated_sha: str) -> None:
            calls.append(validated_sha)
            if len(calls) == 2:
                raise module.ReconcileFailure("synthetic post-write aggregate rejection")

        module.atomic_write_bytes = tracked_atomic_write
        module.validate_authority_chain = reject_after_write
        expect_reconcile_failure(module, "synthetic post-write aggregate rejection")

        if calls != [source_sha, source_sha]:
            raise RuntimeError(f"database outage validator order drift: {calls}")
        if len(atomic_calls) != 2:
            raise RuntimeError(f"database outage atomic publish/rollback call count drift: {len(atomic_calls)}")
        if any(path != status_path for path, _payload in atomic_calls):
            raise RuntimeError("database outage atomic authority wrote an unexpected path")
        if atomic_calls[-1][1] != original_bytes:
            raise RuntimeError("database outage atomic rollback did not restore original bytes")
        if status_path.read_bytes() != original_bytes:
            raise RuntimeError("database outage reconcile did not roll back Production Status")

    module = load_module()
    with tempfile.TemporaryDirectory(prefix="memory-os-database-outage-replace-") as tmp:
        root = Path(tmp)
        result_path = root / "result.json"
        status_path = root / "status.json"
        result_path.write_text(json.dumps({"commitSha": source_sha}) + "\n", encoding="utf-8")
        original_bytes = stale_status_bytes(module)
        status_path.write_bytes(original_bytes)

        module.RESULT_PATH = result_path
        module.STATUS_PATH = status_path
        module.source_is_ancestor = lambda _sha: True
        module.enforce_runtime_authorities = lambda: None
        module.validate_authority_chain = lambda _sha: None
        canonical_replace = module.os.replace

        def reject_replace(_source, _target) -> None:
            raise OSError("synthetic atomic replacement rejection")

        try:
            module.os.replace = reject_replace
            expect_reconcile_failure(module, "cannot atomically write authority")
        finally:
            module.os.replace = canonical_replace
        if status_path.read_bytes() != original_bytes:
            raise RuntimeError("database outage atomic replacement failure mutated Production Status")
        residues = list(root.glob(f".{status_path.name}.*.tmp"))
        if residues:
            raise RuntimeError(f"database outage atomic replacement failure left temp authority residue: {residues}")

    print("PASS: database outage exact authority, atomic publication, and reconcile rollback are fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
