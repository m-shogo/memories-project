#!/usr/bin/env python3
"""Negative proof for mixed-version session authority identity and transaction."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-mixed-version-session.py"


def load_module():
    spec = importlib.util.spec_from_file_location("memory_os_mixed_version_session_reconcile_negative", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load mixed-version session reconciler")
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
            raise RuntimeError(f"mixed-version session {attr} substitution must be rejected")
    finally:
        setattr(module, attr, original)


def fixture_status() -> dict:
    return {
        "productionDecision": "NO_GO",
        "areas": [
            {
                "id": "OPS-P0-008",
                "status": "PARTIAL",
                "existingEvidence": [],
                "missingEvidence": [
                    "old/current backend mixed-version executable tests against an expanded schema",
                    "persisted-state compatibility evidence",
                    "parser artifact compatibility evidence",
                    "client/server compatibility evidence",
                    "PostgreSQL compatibility evidence",
                ],
                "evidenceRefs": [],
            }
        ],
    }


def prepare_fixture(module, root: Path, source_sha: str) -> tuple[Path, bytes]:
    result_path = root / "result.json"
    contract_path = root / "contract.json"
    status_path = root / "status.json"
    result_path.write_text(json.dumps({"commitSha": source_sha}) + "\n", encoding="utf-8")
    contract_path.write_text("{}\n", encoding="utf-8")
    original_bytes = json.dumps(fixture_status(), indent=2).encode("utf-8") + b"\n"
    status_path.write_bytes(original_bytes)
    os.chmod(status_path, 0o640)

    module.RESULT = result_path
    module.CONTRACT = contract_path
    module.STATUS = status_path
    module.source_is_ancestor = lambda _sha: True
    module.enforce_runtime_authorities = lambda: None
    return status_path, original_bytes


def main() -> int:
    module = load_module()
    original_status = module.STATUS.read_bytes()
    expect_authority_rejection(module, "RESULT", module.STATUS)
    expect_authority_rejection(module, "CONTRACT", module.RESULT)
    expect_authority_rejection(module, "STATUS", module.CONTRACT)
    expect_authority_rejection(module, "SESSION_VALIDATOR", module.VERSION_VALIDATOR)
    expect_authority_rejection(module, "VERSION_VALIDATOR", module.OPERABILITY_VALIDATOR)
    expect_authority_rejection(module, "OPERABILITY_VALIDATOR", module.SESSION_VALIDATOR)
    if module.STATUS.read_bytes() != original_status:
        raise RuntimeError("mixed-version session substitution changed canonical Production Status")

    source_sha = "0" * 40
    with tempfile.TemporaryDirectory(prefix="memory-os-mixed-version-session-negative-") as tmp:
        root = Path(tmp)
        status_path, original_bytes = prepare_fixture(module, root, source_sha)

        calls: list[str] = []

        def reject_after_write(validated_sha: str) -> None:
            calls.append(validated_sha)
            if len(calls) == 2:
                raise module.ReconcileFailure("synthetic post-write aggregate rejection")

        module.validate_authority_chain = reject_after_write
        try:
            module.main()
        except module.ReconcileFailure as exc:
            if "synthetic post-write aggregate rejection" not in str(exc):
                raise RuntimeError(f"unexpected mixed-version session rejection: {exc}") from exc
        else:
            raise RuntimeError("mixed-version session reconcile accepted post-write aggregate rejection")

        if calls != [source_sha, source_sha]:
            raise RuntimeError(f"mixed-version session validator order drift: {calls}")
        if status_path.read_bytes() != original_bytes:
            raise RuntimeError("mixed-version session reconcile did not roll back Production Status")
        if status_path.stat().st_mode & 0o777 != 0o640:
            raise RuntimeError("mixed-version session rollback changed Production Status mode")
        if list(root.glob(f".{status_path.name}.*.tmp")):
            raise RuntimeError("mixed-version session rollback leaked temporary status files")

    with tempfile.TemporaryDirectory(prefix="memory-os-mixed-version-session-atomic-negative-") as tmp:
        root = Path(tmp)
        status_path, original_bytes = prepare_fixture(module, root, source_sha)
        module.validate_authority_chain = lambda _sha: None
        real_replace = module.os.replace

        def reject_replace(src, dst) -> None:
            if Path(dst) == status_path:
                raise OSError("synthetic atomic replacement rejection")
            real_replace(src, dst)

        module.os.replace = reject_replace
        try:
            try:
                module.main()
            except module.ReconcileFailure as exc:
                if "synthetic atomic replacement rejection" not in str(exc):
                    raise RuntimeError(f"unexpected atomic replacement rejection: {exc}") from exc
            else:
                raise RuntimeError("mixed-version session reconcile accepted failed atomic replacement")
        finally:
            module.os.replace = real_replace

        if status_path.read_bytes() != original_bytes:
            raise RuntimeError("failed atomic replacement mutated Production Status")
        if status_path.stat().st_mode & 0o777 != 0o640:
            raise RuntimeError("failed atomic replacement changed Production Status mode")
        if list(root.glob(f".{status_path.name}.*.tmp")):
            raise RuntimeError("failed atomic replacement leaked temporary status files")

    with tempfile.TemporaryDirectory(prefix="memory-os-mixed-version-session-rollback-diagnostic-") as tmp:
        root = Path(tmp)
        status_path, original_bytes = prepare_fixture(module, root, source_sha)
        calls: list[str] = []

        def reject_post_write(validated_sha: str) -> None:
            calls.append(validated_sha)
            if len(calls) == 2:
                raise module.ReconcileFailure("synthetic post-write primary rejection")

        module.validate_authority_chain = reject_post_write
        real_replace = module.os.replace
        replacements = 0

        def reject_rollback_replace(src, dst) -> None:
            nonlocal replacements
            if Path(dst) == status_path:
                replacements += 1
                if replacements == 2:
                    raise OSError("synthetic rollback replacement rejection")
            real_replace(src, dst)

        module.os.replace = reject_rollback_replace
        try:
            try:
                module.main()
            except module.ReconcileFailure as exc:
                message = str(exc)
                for expected in (
                    "synthetic post-write primary rejection",
                    "rollback incomplete",
                    "synthetic rollback replacement rejection",
                ):
                    if expected not in message:
                        raise RuntimeError(f"rollback diagnostic lost {expected!r}: {message}") from exc
            else:
                raise RuntimeError("mixed-version session reconcile accepted failed rollback")
        finally:
            module.os.replace = real_replace

        if replacements != 2:
            raise RuntimeError(f"mixed-version session rollback replacement count drift: {replacements}")
        if status_path.read_bytes() == original_bytes:
            raise RuntimeError("rollback failure fixture did not preserve the published candidate state")
        if status_path.stat().st_mode & 0o777 != 0o640:
            raise RuntimeError("rollback failure changed Production Status mode")
        if list(root.glob(f".{status_path.name}.*.tmp")):
            raise RuntimeError("failed rollback leaked temporary status files")

    print("PASS: mixed-version session exact authority, atomic replacement, rollback, and rollback diagnostics are fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
