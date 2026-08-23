#!/usr/bin/env python3
"""Pin deterministic OPS-P0-007 generation evidence status ordering."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-generation-evidence.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("memory_os_generation_evidence_ordering_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load generation evidence reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    reconciler = load_reconciler()
    prefix = reconciler.EVIDENCE_PREFIX
    old = prefix + " old"
    new = prefix + " new"

    values = ["before", old, "after"]
    reconciler.replace_single_prefixed(values, prefix, new)
    require(values == ["before", new, "after"], "generation evidence moved during replacement")
    print("PASS preserve: generation evidence replaced at the same index")

    values = ["before", "after"]
    reconciler.replace_single_prefixed(values, prefix, new)
    require(values == ["before", "after", new], "missing generation evidence was not appended exactly once")
    print("PASS append: missing generation evidence appended once")

    values = [old, prefix + " duplicate"]
    try:
        reconciler.replace_single_prefixed(values, prefix, new)
    except reconciler.Fail:
        require(values == [old, prefix + " duplicate"], "duplicate-prefix rejection mutated generation evidence")
        print("PASS reject: duplicate generation evidence prefixes fail closed without mutation")
    else:
        raise Fail("duplicate generation evidence prefixes unexpectedly accepted")

    values = ["stable", old, "tail"]
    reconciler.replace_single_prefixed(values, prefix, old)
    require(values == ["stable", old, "tail"], "no-op generation evidence reconcile changed ordering")
    print("PASS preserve: no-op generation evidence reconcile is order stable")

    print("Memory OS generation evidence ordering negative suite PASS")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION EVIDENCE ORDERING NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
