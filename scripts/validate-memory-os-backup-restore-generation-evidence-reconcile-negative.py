#!/usr/bin/env python3
"""Prove generation-evidence reconciliation rolls back every derived authority on post-validation failure."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-generation-evidence.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CANONICAL = {
    "CONTRACT": ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
    "REGISTRY": ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "BINDING": ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json",
    "STATUS": ROOT / "contracts/operations/production-operability-status.json",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_generation_evidence_reconcile_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load generation evidence reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    require(RECONCILER.is_file(), "generation evidence reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    reconciler = load_reconciler()

    with tempfile.TemporaryDirectory(prefix=".tmp-generation-evidence-reconcile-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        originals: dict[Path, bytes] = {}
        for attr, source in CANONICAL.items():
            target = tmp / source.name
            shutil.copyfile(source, target)
            setattr(reconciler, attr, target)
            originals[target] = target.read_bytes()

        failing_validator = tmp / "forced-validator-failure.py"
        failing_validator.write_text("#!/usr/bin/env python3\nraise SystemExit(23)\n", encoding="utf-8")
        reconciler.BINDING_VALIDATOR = failing_validator
        reconciler.VALIDATOR = failing_validator

        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require("generation binding validator failed" in str(exc), f"unexpected reconcile failure: {exc}")
        else:
            raise Fail("forced post-validation failure unexpectedly accepted")

        for path, expected in originals.items():
            require(path.read_bytes() == expected, f"rollback drifted derived authority: {path.name}")

    print("PASS rollback: generation evidence reconcile restores registry/contract/binding/status byte-for-byte")
    print("Generation evidence reconcile negative suite PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION EVIDENCE RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
