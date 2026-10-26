#!/usr/bin/env python3
"""Disposable runtime negatives for database outage diagnostic writer and workflow binding."""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/write-memory-os-database-commit-outage-diagnostic.py"
WORKFLOW = ROOT / ".github/workflows/database-commit-outage.yml"


def load_helper():
    spec = importlib.util.spec_from_file_location("database_outage_diagnostic_writer", HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError("database outage diagnostic writer loader missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(module):
    return {
        "schemaVersion": "memory-os-validator-diagnostic.v1",
        "workflow": "database-commit-outage-recovery",
        "sourceCommitSha": "a" * 40,
        "result": "FAIL",
        "exitCode": 125,
        "durationSeconds": 1.25,
        "output": module.SAFE_OUTPUT,
        "containsSecrets": False,
        "productionEvidence": False,
    }


def rejected(module, path, value, root, label):
    try:
        module.write_diagnostic(path, value, root)
    except module.DiagnosticWriteFailure as exc:
        if "SYNTHETIC_SECRET" in str(exc):
            raise RuntimeError(f"{label} leaked synthetic exception material") from None
    else:
        raise RuntimeError(f"database outage diagnostic accepted {label}")


def main() -> int:
    module = load_helper()
    source = WORKFLOW.read_text(encoding="utf-8")
    required = (
        "runpy.run_path(", "write_diagnostic", "stdout=subprocess.DEVNULL",
        "stderr=subprocess.DEVNULL", module.SAFE_OUTPUT,
        "scripts/write-memory-os-database-commit-outage-diagnostic.py",
    )
    for marker in required:
        if marker not in source:
            raise RuntimeError("database outage workflow diagnostic source binding missing")
    if "completed.stdout[-4000:]" in source or "diagnostic_path.write_text(" in source:
        raise RuntimeError("database outage workflow persists raw or non-atomic diagnostic")
    pr_source = source.split("  validate-pr:", 1)[1].split("  execute:", 1)[0]
    execute_source = source.split("  execute:", 1)[1]
    if "permissions:\n      contents: read" not in pr_source or "persist-credentials: false" not in pr_source:
        raise RuntimeError("database outage PR job write-permission boundary drift")
    if "permissions:\n      contents: write" not in execute_source:
        raise RuntimeError("database outage publisher write-permission boundary drift")
    if "github.ref == 'refs/heads/so'" not in execute_source or 'test "${GITHUB_REF:-}" = "refs/heads/so"' not in execute_source:
        raise RuntimeError("database outage execute source-branch admission missing")
    for action, expected in (
        ("actions/checkout@", "actions/checkout@11d5960a326750d5838078e36cf38b85af677262"),
        ("actions/setup-go@", "actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5"),
        ("actions/setup-python@", "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"),
    ):
        if source.count(action) != 2 or source.count(expected) != 2:
            raise RuntimeError("database outage immutable action source binding drift")

    with tempfile.TemporaryDirectory(prefix="database-outage-diagnostic-", dir=ROOT) as temp:
        root = Path(temp)
        path = root / module.RELATIVE_PATH
        path.parent.mkdir(parents=True)
        value = fixture(module)
        module.write_diagnostic(path, value, root)
        if json.loads(path.read_text(encoding="utf-8")) != value:
            raise RuntimeError("database outage diagnostic positive bytes mismatch")
        if stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise RuntimeError("database outage diagnostic new mode drift")
        path.chmod(0o640)
        original = path.read_bytes()
        module.write_diagnostic(path, value, root)
        if path.read_bytes() != original or stat.S_IMODE(path.stat().st_mode) != 0o640:
            raise RuntimeError("database outage diagnostic existing mode drift")
        for label, patch in (
            ("raw output", {"output": "SYNTHETIC_SECRET"}),
            ("secret flag", {"containsSecrets": True}),
            ("production flag", {"productionEvidence": True}),
            ("extra field", {"unexpected": "SYNTHETIC_SECRET"}),
        ):
            rejected(module, path, dict(value, **patch), root, label)
        for label, duration in (
            ("boolean duration", True),
            ("NaN duration", float("nan")),
            ("infinite duration", float("inf")),
            ("negative duration", -1),
            ("oversized duration", 10 ** 500),
        ):
            rejected(module, path, dict(value, durationSeconds=duration), root, label)
        if path.read_bytes() != original:
            raise RuntimeError("database outage diagnostic rejected payload changed bytes")
        original_replace = module.os.replace
        try:
            def fail_replace(*args):
                raise OSError("SYNTHETIC_SECRET")
            module.os.replace = fail_replace
            rejected(module, path, value, root, "atomic replace failure")
        finally:
            module.os.replace = original_replace
        if path.read_bytes() != original or stat.S_IMODE(path.stat().st_mode) != 0o640:
            raise RuntimeError("database outage diagnostic atomic rollback drift")
        if list(path.parent.glob(f".{path.name}.*.tmp")):
            raise RuntimeError("database outage diagnostic left temporary files")
        path.unlink()
        directory = path
        directory.mkdir()
        rejected(module, path, value, root, "directory target")
        directory.rmdir()
        if hasattr(os, "mkfifo"):
            os.mkfifo(path)
            rejected(module, path, value, root, "FIFO target")
            path.unlink()
        rejected(module, root / "outside.json", value, root, "noncanonical path")
    with tempfile.TemporaryDirectory(prefix="database-outage-diagnostic-outside-") as outside_temp:
        outside = Path(outside_temp)
        canary = outside / "canary"
        canary.write_bytes(b"SYNTHETIC_SECRET")
        with tempfile.TemporaryDirectory(prefix="database-outage-diagnostic-link-", dir=ROOT) as temp:
            root = Path(temp)
            path = root / module.RELATIVE_PATH
            path.parent.mkdir(parents=True)
            path.symlink_to(canary)
            rejected(module, path, fixture(module), root, "symlink target")
            path.unlink()
            path.parent.rmdir()
            path.parent.symlink_to(outside, target_is_directory=True)
            rejected(module, path, fixture(module), root, "symlink ancestor")
        if canary.read_bytes() != b"SYNTHETIC_SECRET":
            raise RuntimeError("database outage diagnostic changed external canary")
    with tempfile.TemporaryDirectory(prefix="database-outage-diagnostic-parent-", dir=ROOT) as temp:
        root = Path(temp)
        rejected(module, root / module.RELATIVE_PATH, fixture(module), root, "missing parent")
    print("PASS: database outage diagnostic fixed output, atomic path/mode/rollback and workflow binding")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
