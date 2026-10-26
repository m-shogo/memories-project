#!/usr/bin/env python3
"""Independent typed local reason convergence proof; never production evidence."""
from __future__ import annotations

import hashlib
import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF = "scripts/validate-memory-os-deletion-deferred-reason-cross-publisher-negative.py"
INDEPENDENT = ".github/workflows/deletion-deferred-reason-cross-publisher-negative.yml"
REVIEWED_INDEPENDENT = "1df630c6cb93013d0d0592b46ec2c49374e92882"
SOURCES = {
    "scripts/reconcile-memory-os-deletion-mutation-evidence.py": "9c54f24dce5049c4a383c90179c30da48aeeb3f5",
    "scripts/reconcile-memory-os-deletion-advanced-evidence.py": "4a1358636f0b4e199d37155dfd2ee1c47fba03cd",
    "scripts/reconcile-memory-os-deletion-lease-recovery-authority.py": "0d04c6728c0d208d9334cb57ca8e5539f93e74a2",
    "scripts/reconcile-memory-os-load-readiness-note.py": "8012804fe785223250921e5fcf0b8657489caf59",
    "scripts/reconcile-memory-os-deletion-container-kill-authority.py": "8ebb43ea9b39bfbb5c287d0e61b87e2334ab6867",
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

def atomic_path_runtime(label: str, writer, failure: type[BaseException]) -> None:
    with tempfile.TemporaryDirectory(prefix="deletion-cross-writer-atomic-") as temp_dir:
        root = Path(temp_dir)
        outside = root / "outside"
        outside.mkdir()
        canary = outside / "authority.json"
        canary.write_bytes(b"SYNTHETIC_CROSS_WRITER_CANARY")
        direct = root / "direct.json"
        direct.symlink_to(canary)
        ancestor = root / "linked"
        ancestor.symlink_to(outside, target_is_directory=True)
        directory = root / "directory.json"
        directory.mkdir()
        for target in (direct, ancestor / "authority.json", directory):
            try:
                writer(target, b"synthetic overwrite")
            except failure:
                pass
            else:
                raise AssertionError("deletion cross-writer accepted substituted atomic path: " + label)
            if canary.read_bytes() != b"SYNTHETIC_CROSS_WRITER_CANARY":
                raise AssertionError("deletion cross-writer modified external canary: " + label)
        if not direct.is_symlink() or not ancestor.is_symlink() or not directory.is_dir():
            raise AssertionError("deletion cross-writer replaced substituted path: " + label)
        positive = root / "valid.json"
        writer(positive, b"synthetic valid local payload")
        if positive.read_bytes() != b"synthetic valid local payload":
            raise AssertionError("deletion cross-writer rejected legitimate local atomic path: " + label)
        if list(root.rglob(".*.tmp")):
            raise AssertionError("deletion cross-writer left atomic temporary residue: " + label)


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
            # Fifth publisher is reached through its full exact-source workflow;
            # that workflow executes the reconcile-negative invoking this guard.
            if path != "scripts/reconcile-memory-os-deletion-container-kill-authority.py":
                raise AssertionError("deletion reason source not in CI triggers: " + path)
            full = read(".github/workflows/reconcile-deletion-container-kill-authority.yml")
            container_test = read("scripts/validate-memory-os-deletion-container-kill-authority-reconcile-negative.py")
            if path not in full or "scripts/validate-memory-os-deletion-container-kill-authority-reconcile-negative.py" not in full:
                raise AssertionError("deletion reason container-kill full CI trigger missing")
            if SELF not in container_test:
                raise AssertionError("deletion reason container-kill full CI cross-guard invocation missing")

    mutation = module("scripts/reconcile-memory-os-deletion-mutation-evidence.py", "deletion_reason_mutation")
    advanced = module("scripts/reconcile-memory-os-deletion-advanced-evidence.py", "deletion_reason_advanced")
    lease = module("scripts/reconcile-memory-os-deletion-lease-recovery-authority.py", "deletion_reason_lease")
    normalizer = module("scripts/reconcile-memory-os-load-readiness-note.py", "deletion_reason_normalizer")
    container = module("scripts/reconcile-memory-os-deletion-container-kill-authority.py", "deletion_reason_container_kill")
    expected = mutation.NORMALIZED_CANONICAL_REASON
    if expected != advanced.NORMALIZED_CANONICAL_REASON or expected != lease.NORMALIZED_CANONICAL_REASON or expected != container.NORMALIZED_CANONICAL_REASON:
        raise AssertionError("deletion reason canonical normalized authority diverged")
    flags = tuple(normalizer.REQUIRED_TRUE)
    if flags != tuple(mutation.NORMALIZED_REQUIRED_TRUE) or flags != tuple(advanced.NORMALIZED_REQUIRED_TRUE) or flags != tuple(lease.NORMALIZED_REQUIRED_TRUE) or flags != tuple(container.NORMALIZED_REQUIRED_TRUE):
        raise AssertionError("deletion reason typed required-flag set drift")
    ready = {key: True for key in flags}
    for label, func, failure in (
        ("advanced", advanced.preserve_stronger_deferred_reason, advanced.Fail),
        ("lease", lease.preserve_container_deferred_reason, SystemExit),
        ("container-kill", container.preserve_stronger_deferred_reason, container.ReconcileFailure),
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
    for label, writer, failure in (
        ("mutation", mutation.atomic_write_bytes, mutation.Fail),
        ("advanced", advanced.atomic_write_bytes, advanced.Fail),
        ("lease", lease.atomic_write_bytes, SystemExit),
        ("normalizer", normalizer.atomic_write_bytes, RuntimeError),
        ("container-kill", container.atomic_write_bytes, container.ReconcileFailure),
    ):
        atomic_path_runtime(label, writer, failure)
    print("PASS: five actual local atomic writers, 15 substituted-path negatives and five positive cases")
    print("PASS: deletion deferred reason 5 reviewed source bindings, canonical equality and 33 typed flag negatives")
    print("PASS: cross-publisher guard is local-only; production evidence generated: false")

if __name__ == "__main__":
    main()
