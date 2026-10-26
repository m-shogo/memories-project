#!/usr/bin/env python3
"""Independent typed local reason convergence proof; never production evidence."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF = "scripts/validate-memory-os-deletion-deferred-reason-cross-publisher-negative.py"
INDEPENDENT = ".github/workflows/deletion-deferred-reason-cross-publisher-negative.yml"
REVIEWED_INDEPENDENT = "1df630c6cb93013d0d0592b46ec2c49374e92882"
SOURCES = {
    "scripts/reconcile-memory-os-deletion-mutation-evidence.py": "97e1409aabc1742b3418819e1d4c1c9d086cf023",
    "scripts/reconcile-memory-os-deletion-advanced-evidence.py": "edf3a505c993405ba0830d3c2e90f7b5ceff3ba2",
    "scripts/reconcile-memory-os-deletion-lease-recovery-authority.py": "1359e7c0ae28418a56d35bc5d1a1b55e3c121b4b",
    "scripts/reconcile-memory-os-load-readiness-note.py": "219e1f1630c7fb9a7ee5cfa40ec4452d861d3945",
}

def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def read(path: str) -> str:
    file = ROOT / path
    if file.is_symlink() or not file.is_file():
        raise AssertionError("deletion reason source missing/substituted: " + path)
    if file.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise AssertionError("deletion reason source escaped canonical path: " + path)
    return file.read_text(encoding="utf-8")

def module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    if spec is None or spec.loader is None:
        raise AssertionError("deletion reason module unavailable: " + path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def main() -> None:
    ci = read(INDEPENDENT)
    if blob(ci) != REVIEWED_INDEPENDENT or blob(ci + "\n# synthetic drift\n") == REVIEWED_INDEPENDENT:
        raise AssertionError("deletion reason independent CI complete source drift")
    for marker in (SELF, INDEPENDENT, "contents: read", "persist-credentials: false",
                   "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
                   "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
                   'test "$(git rev-parse HEAD)" = "$expected"'):
        if marker not in ci:
            raise AssertionError("deletion reason CI reachability drift: " + marker)
    for path, expected in SOURCES.items():
        source = read(path)
        if blob(source) != expected or blob(source + "\n# synthetic drift\n") == expected:
            raise AssertionError("deletion reason reviewed publisher source drift: " + path)
        if path not in ci:
            raise AssertionError("deletion reason source not in CI triggers: " + path)

    mutation = module("scripts/reconcile-memory-os-deletion-mutation-evidence.py", "deletion_reason_mutation")
    advanced = module("scripts/reconcile-memory-os-deletion-advanced-evidence.py", "deletion_reason_advanced")
    lease = module("scripts/reconcile-memory-os-deletion-lease-recovery-authority.py", "deletion_reason_lease")
    normalizer = module("scripts/reconcile-memory-os-load-readiness-note.py", "deletion_reason_normalizer")
    expected = mutation.NORMALIZED_CANONICAL_REASON
    if expected != advanced.NORMALIZED_CANONICAL_REASON or expected != lease.NORMALIZED_CANONICAL_REASON:
        raise AssertionError("deletion reason canonical normalized authority diverged")
    flags = tuple(normalizer.REQUIRED_TRUE)
    if flags != tuple(mutation.NORMALIZED_REQUIRED_TRUE) or flags != tuple(advanced.NORMALIZED_REQUIRED_TRUE) or flags != tuple(lease.NORMALIZED_REQUIRED_TRUE):
        raise AssertionError("deletion reason typed required-flag set drift")
    ready = {key: True for key in flags}
    for label, func, failure in (
        ("advanced", advanced.preserve_stronger_deferred_reason, advanced.Fail),
        ("lease", lease.preserve_container_deferred_reason, SystemExit),
    ):
        if func(expected, ready) is not True:
            raise AssertionError("deletion reason normalized coverage demoted: " + label)
        for key in flags:
            invalid = dict(ready)
            invalid[key] = False
            try:
                func(expected, invalid)
            except failure:
                continue
            raise AssertionError("deletion reason accepted unsupported normalized claim: " + label + "/" + key)
    if "existing_deferred_reason == NORMALIZED_CANONICAL_REASON" not in read("scripts/reconcile-memory-os-deletion-mutation-evidence.py"):
        raise AssertionError("mutation main-path normalized authority check unreachable")
    print("PASS: deletion deferred reason 4 reviewed source bindings, canonical equality and 22 typed flag negatives")
    print("PASS: cross-publisher guard is local-only; production evidence generated: false")

if __name__ == "__main__":
    main()
