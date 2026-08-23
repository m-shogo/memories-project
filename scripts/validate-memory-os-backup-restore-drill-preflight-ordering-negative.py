#!/usr/bin/env python3
"""Pin deterministic OPS-P0-007 restore-preflight status ordering."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-preflight.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("memory_os_preflight_ordering_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load preflight reconciler")
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
    require(values == ["before", new, "after"], "preflight evidence moved during replacement")
    print("PASS preserve: preflight evidence replaced at the same index")

    values = ["before", "after"]
    reconciler.replace_single_prefixed(values, prefix, new)
    require(values == ["before", "after", new], "missing preflight evidence was not appended exactly once")
    print("PASS append: missing preflight evidence appended once")

    values = [old, prefix + " duplicate"]
    try:
        reconciler.replace_single_prefixed(values, prefix, new)
    except reconciler.Fail:
        require(values == [old, prefix + " duplicate"], "duplicate-prefix rejection mutated preflight evidence")
        print("PASS reject: duplicate preflight prefixes fail closed without mutation")
    else:
        raise Fail("duplicate preflight evidence prefixes unexpectedly accepted")

    values = ["stable", old, "tail"]
    reconciler.replace_single_prefixed(values, prefix, old)
    require(values == ["stable", old, "tail"], "no-op preflight reconcile changed ordering")
    print("PASS preserve: no-op preflight reconcile is order stable")

    print("Memory OS restore preflight ordering negative suite PASS")
    print("automatic prerequisite/request creation: false")
    print("restore executed: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RESTORE PREFLIGHT ORDERING NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
