#!/usr/bin/env python3
"""Prove distributed runtime reconciliation keeps atomic transport and validator authority fail-closed."""

from __future__ import annotations

import importlib.util
import inspect
import os
import stat
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-rate-limit-distributed-runtime.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_rate_limit_runtime_reconcile_atomic_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load distributed runtime reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_reconciler()
    atomic_defaults = module.atomic_write_bytes.__kwdefaults__ or {}
    write_defaults = module.write.__kwdefaults__ or {}
    tx_defaults = module.commit_outputs_transactionally.__kwdefaults__ or {}
    main_defaults = module.main.__kwdefaults__ or {}
    validator_defaults = module.run_validator.__kwdefaults__ or {}

    require(atomic_defaults.get("_replace") is module.os.replace, "atomic replace transport is not definition-time bound")
    require(write_defaults.get("_atomic_write") is module.atomic_write_bytes, "JSON writer is not bound to canonical atomic writer")
    require(tx_defaults.get("_write") is module.write, "transaction writer is not definition-time bound")
    require(tx_defaults.get("_atomic_write") is module.atomic_write_bytes, "rollback writer is not canonical atomic writer")
    require(tx_defaults.get("_enforce") is module.enforce_runtime_authorities, "transaction authority guard is not bound")
    require(tx_defaults.get("_validators") == module.POST_WRITE_VALIDATORS, "post-write validator chain is not bound")
    require(tx_defaults.get("_run") is module.subprocess.run, "post-write execution transport is not bound")
    require(main_defaults.get("_enforce") is module.enforce_runtime_authorities, "main authority guard is not bound")
    require(main_defaults.get("_run_validator") is module.run_validator, "main preflight validator runner is not bound")
    require(validator_defaults.get("_run") is module.subprocess.run, "preflight validator execution transport is not bound")
    require(validator_defaults.get("_validator") == module.VALIDATOR, "preflight validator path is not bound")

    with tempfile.TemporaryDirectory(prefix="memory-os-rate-limit-runtime-atomic-") as temp_dir:
        path = Path(temp_dir) / "authority.json"
        path.write_bytes(b"before\n")
        path.chmod(0o640)
        before_mode = stat.S_IMODE(path.stat().st_mode)
        module.atomic_write_bytes(path, b"after\n")
        require(path.read_bytes() == b"after\n", "atomic writer did not publish payload")
        require(stat.S_IMODE(path.stat().st_mode) == before_mode, "atomic writer changed existing authority mode")
        require(not list(path.parent.glob(f".{path.name}.*.tmp")), "atomic writer left temporary residue")

        path.write_bytes(b"stable\n")
        before = path.read_bytes()

        def reject_replace(_source, _target):
            raise OSError("synthetic atomic replacement failure")

        try:
            module.atomic_write_bytes(path, b"forbidden\n", _replace=reject_replace)
        except OSError:
            pass
        else:
            raise Fail("synthetic atomic replacement failure unexpectedly succeeded")
        require(path.read_bytes() == before, "failed atomic replacement mutated canonical bytes")
        require(not list(path.parent.glob(f".{path.name}.*.tmp")), "failed atomic replacement left temporary residue")

    original_replace = module.os.replace
    original_validators = module.POST_WRITE_VALIDATORS
    try:
        module.os.replace = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("mutable replace transport used"))
        module.POST_WRITE_VALIDATORS = ()
        require((module.atomic_write_bytes.__kwdefaults__ or {}).get("_replace") is original_replace,
                "atomic writer followed mutable os.replace substitution")
        require((module.commit_outputs_transactionally.__kwdefaults__ or {}).get("_validators") == original_validators,
                "transaction followed mutable validator-chain substitution")
    finally:
        module.os.replace = original_replace
        module.POST_WRITE_VALIDATORS = original_validators

    source = inspect.getsource(module.commit_outputs_transactionally)
    require("path.write_bytes" not in source, "transaction rollback regressed to direct write_bytes")
    require("_atomic_write(path, data)" in source, "transaction rollback does not use bound atomic writer")

    print("Memory OS distributed rate-limit runtime reconcile atomic negative suite PASS")
    print("atomic replacement transport substitution accepted: false")
    print("post-write validator-chain substitution accepted: false")
    print("direct rollback write_bytes used: false")
    print("production evidence generated: false")
    print("production readiness changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DISTRIBUTED RATE LIMIT RUNTIME RECONCILE ATOMIC NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
