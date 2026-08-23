#!/usr/bin/env python3
"""Pin deterministic OPS-P0-007 generation-binding status ordering."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-generation-status.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("memory_os_generation_status_ordering_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load generation status reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    reconciler = load_reconciler()
    prefix = reconciler.EVIDENCE_PREFIX
    old = prefix + " old"
    new = reconciler.EVIDENCE

    values = ["before", old, "after"]
    reconciler.replace_single_prefixed(values, prefix, new)
    require(values == ["before", new, "after"], "generation binding status moved during replacement")
    print("PASS preserve: generation binding status replaced at the same index")

    values = ["before", "after"]
    reconciler.replace_single_prefixed(values, prefix, new)
    require(values == ["before", "after", new], "missing generation binding status was not appended exactly once")
    print("PASS append: missing generation binding status appended once")

    values = [old, prefix + " duplicate"]
    try:
        reconciler.replace_single_prefixed(values, prefix, new)
    except reconciler.Fail:
        require(values == [old, prefix + " duplicate"], "duplicate-prefix rejection mutated generation binding status")
        print("PASS reject: duplicate generation binding prefixes fail closed without mutation")
    else:
        raise Fail("duplicate generation binding status prefixes unexpectedly accepted")

    values = ["stable", new, "tail"]
    reconciler.replace_single_prefixed(values, prefix, new)
    require(values == ["stable", new, "tail"], "no-op generation binding reconcile changed ordering")
    print("PASS preserve: no-op generation binding reconcile is order stable")

    print("Memory OS generation binding status ordering negative suite PASS")
    print("human production promotion authorized: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION STATUS ORDERING NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
