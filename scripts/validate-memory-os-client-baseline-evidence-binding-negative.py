#!/usr/bin/env python3
"""Focused negative coverage for reviewed client evidence source binding and reconcile rollback."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-client-baseline.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-client-baseline-registry.py"
EVIDENCE = ROOT / "docs/evidence/clients/README.md"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_writer() -> Any:
    return load_module(WRITER, "memory_os_client_baseline_writer_negative")


def head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    require(completed.returncode == 0, "cannot resolve HEAD")
    return completed.stdout.strip()


def expect_rejected(writer: Any, ref: str, source: str, expected: str) -> None:
    try:
        writer.validate_evidence_ref_at_source(ref, source, "negative")
    except writer.Failure as exc:
        require(expected in str(exc), f"unexpected rejection: {exc}")
        return
    raise RuntimeError(f"client evidence corruption was accepted: {expected}")


def prove_reconcile_rollback() -> None:
    reconciler = load_module(RECONCILER, "memory_os_client_baseline_reconciler_negative")
    paths = (reconciler.CONTRACT, reconciler.SUPPORT, reconciler.STATUS)
    original = {path: path.read_bytes() for path in paths}
    observed_post_write_failure = False

    def controlled_validator(path: Path, label: str) -> None:
        nonlocal observed_post_write_failure
        if label == "post-write operability validator":
            observed_post_write_failure = True
            raise reconciler.Fail("synthetic post-write operability validation failure")

    reconciler.run_validator = controlled_validator
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require(
                "synthetic post-write operability validation failure" in str(exc),
                f"unexpected reconcile failure: {exc}",
            )
        else:
            raise RuntimeError("client baseline reconcile unexpectedly succeeded after synthetic post-write failure")
        require(observed_post_write_failure, "synthetic post-write validator was not reached")
        for path in paths:
            require(
                path.read_bytes() == original[path],
                f"client reconcile rollback changed canonical authority: {path.relative_to(ROOT)}",
            )
    finally:
        for path in paths:
            if path.read_bytes() != original[path]:
                path.write_bytes(original[path])


def main() -> int:
    writer = load_writer()
    source = head()
    ref = str(EVIDENCE.relative_to(ROOT))
    original = EVIDENCE.read_bytes()

    writer.validate_evidence_ref_at_source(ref, source, "positive")

    try:
        EVIDENCE.write_bytes(original + b"\nsource-binding-negative\n")
        expect_rejected(writer, ref, source, "changed after source commit")
    finally:
        EVIDENCE.write_bytes(original)

    temporary = ROOT / "docs/evidence/clients/.client-evidence-post-source-negative.json"
    try:
        temporary.write_text("{}\n", encoding="utf-8")
        expect_rejected(
            writer,
            str(temporary.relative_to(ROOT)),
            source,
            "must be tracked",
        )
    finally:
        temporary.unlink(missing_ok=True)

    prove_reconcile_rollback()

    require(EVIDENCE.read_bytes() == original, "client evidence fixture was not restored")
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    require(status.returncode == 0 and status.stdout.strip() == "",
            "negative suite left working-tree changes")
    print("PASS: client baseline evidence binding and reconcile rollback are fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
