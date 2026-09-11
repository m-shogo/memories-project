#!/usr/bin/env python3
"""Prove distributed runtime reconcile preserves authority under rollback failure."""

from __future__ import annotations

import importlib.util
import json
import stat
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-rate-limit-distributed-runtime.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "memory_os_rate_limit_distributed_runtime_reconcile_negative", RECONCILER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load distributed runtime reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_module()
    with tempfile.TemporaryDirectory(prefix="memory-os-distributed-runtime-rollback-") as tmp:
        root = Path(tmp)
        contract = root / "contract.json"
        status = root / "status.json"
        contract.write_text('{"before":"contract"}\n', encoding="utf-8")
        status.write_text('{"before":"status"}\n', encoding="utf-8")
        contract.chmod(0o640)
        status.chmod(0o600)
        originals = {contract: contract.read_bytes(), status: status.read_bytes()}
        modes = {
            contract: stat.S_IMODE(contract.stat().st_mode),
            status: stat.S_IMODE(status.stat().st_mode),
        }

        outputs = {
            contract: {"after": "contract"},
            status: {"after": "status"},
        }

        def temp_write(path: Path, value: dict) -> None:
            module.atomic_write_bytes(
                path,
                (json.dumps(value, indent=2) + "\n").encode("utf-8"),
            )

        def reject_validator(command, **_kwargs):
            return subprocess.CompletedProcess(
                command,
                23,
                stdout="",
                stderr="synthetic distributed runtime primary validation failure",
            )

        rollback_calls: list[Path] = []

        def fail_first_rollback(path: Path, payload: bytes) -> None:
            rollback_calls.append(path)
            if len(rollback_calls) == 1:
                raise OSError("synthetic distributed runtime rollback failure")
            module.atomic_write_bytes(path, payload)

        caught: BaseException | None = None
        try:
            module.commit_outputs_transactionally(
                outputs,
                _write=temp_write,
                _atomic_write=fail_first_rollback,
                _enforce=lambda: None,
                _validators=(root / "synthetic-validator.py",),
                _run=reject_validator,
                _root=root,
            )
        except BaseException as exc:
            caught = exc

        if caught is None:
            raise RuntimeError("distributed runtime reconcile accepted rollback failure")
        text = str(caught)
        if "synthetic distributed runtime primary validation failure" not in text:
            raise RuntimeError(f"rollback failure masked primary diagnostic: {text}")
        if "rollback incomplete" not in text:
            raise RuntimeError(f"rollback failure omitted incomplete diagnostic: {text}")
        if "synthetic distributed runtime rollback failure" not in text:
            raise RuntimeError(f"rollback failure omitted rollback diagnostic: {text}")
        if rollback_calls != [contract, status]:
            raise RuntimeError(
                f"rollback stopped before restoring every authority: {rollback_calls!r}"
            )
        if status.read_bytes() != originals[status]:
            raise RuntimeError("first rollback failure prevented later status restore")
        if stat.S_IMODE(status.stat().st_mode) != modes[status]:
            raise RuntimeError("later status restore changed mode")

        module.atomic_write_bytes(contract, originals[contract])
        contract.chmod(modes[contract])
        status.chmod(modes[status])
        for path in originals:
            if list(path.parent.glob(f".{path.name}.*.tmp")):
                raise RuntimeError(f"rollback left temp residue for {path.name}")

    print("PASS: distributed runtime reconciliation preserves primary diagnostics and exhausts rollback")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
