#!/usr/bin/env python3
"""Verify typed non-resurrection registry publication preserves file mode and rollback state."""

from __future__ import annotations

import importlib.util
import json
import stat
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_non_resurrection_registry_mode_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load typed non-resurrection writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def main() -> int:
    writer = load_writer()
    original_registry = writer.REGISTRY
    original_validate = writer.validate_registry_for_append

    with tempfile.TemporaryDirectory(prefix="memory-os-non-resurrection-mode-") as tmp:
        registry = Path(tmp) / "typed-registry.json"
        initial = {
            "schemaVersion": "memory-os-backup-restore-non-resurrection-admission-registry.v1",
            "appendOnly": True,
            "registeredRecordCount": 0,
            "completeRecordCount": 0,
            "candidateCoveredCount": 0,
            "records": [],
            "productionEvidence": False,
            "productionReady": False,
        }
        registry.write_text(json.dumps(initial, indent=2) + "\n", encoding="utf-8")
        registry.chmod(0o640)
        writer.REGISTRY = registry

        try:
            writer.validate_registry_for_append = lambda value: []
            success_candidate = dict(initial)
            writer.write_registry_transactionally(success_candidate)
            require(mode(registry) == 0o640, "successful typed registry publication changed permission mode")
            require(not list(registry.parent.glob(".backup-restore-non-resurrection.*.tmp")), "successful publication left temporary files")
            print("PASS preserve: successful typed registry publication preserves 0640 mode and leaves no temp files")

            before = registry.read_bytes()
            before_mode = mode(registry)

            def reject_after_write(value):
                raise writer.Fail("synthetic typed post-write validator failure")

            writer.validate_registry_for_append = reject_after_write
            failed_candidate = dict(initial)
            failed_candidate["productionReady"] = True
            try:
                writer.write_registry_transactionally(failed_candidate)
            except writer.Fail:
                pass
            else:
                raise Fail("synthetic post-write validator failure unexpectedly accepted")

            require(registry.read_bytes() == before, "typed registry rollback did not restore exact bytes")
            require(mode(registry) == before_mode == 0o640, "typed registry rollback did not restore original permission mode")
            require(not list(registry.parent.glob(".backup-restore-non-resurrection.*.tmp")), "rollback left temporary publication files")
            require(not list(registry.parent.glob(".backup-restore-non-resurrection-rollback.*.tmp")), "rollback left temporary restore files")
            print("PASS preserve: rejected typed registry publication restores exact bytes and 0640 mode")
            print("PASS cleanup: typed registry publication and rollback leave no temporary residue")
        finally:
            writer.REGISTRY = original_registry
            writer.validate_registry_for_append = original_validate

    print("canonical registries mutated: false")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
