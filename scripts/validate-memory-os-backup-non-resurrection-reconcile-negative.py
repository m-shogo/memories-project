#!/usr/bin/env python3
"""Prove typed non-resurrection reconciliation load boundaries and transactional rollback."""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-non-resurrection-authority.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CANONICAL = {
    "CONTRACT": ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json",
    "REGISTRY": ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
    "GEN_REGISTRY": ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "STATUS": ROOT / "contracts/operations/production-operability-status.json",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_typed_non_resurrection_reconcile_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load typed non-resurrection reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_domain_fail(name: str, action: Callable[[], object], fail_type: type[BaseException]) -> None:
    try:
        action()
    except fail_type:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def main() -> int:
    require(RECONCILER.is_file(), "typed non-resurrection reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    reconciler = load_reconciler()

    with tempfile.TemporaryDirectory(prefix=".tmp-typed-reconcile-negative-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_domain_fail("typed reconciler invalid UTF-8 authority", lambda: reconciler.load(invalid_utf8), reconciler.Fail)

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_domain_fail("typed reconciler unreadable directory authority", lambda: reconciler.load(directory_authority), reconciler.Fail)

        with tempfile.TemporaryDirectory(prefix="memory-os-typed-outside-") as outside_dir:
            outside = Path(outside_dir) / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            expect_domain_fail("typed reconciler authority escapes repository", lambda: reconciler.load(outside), reconciler.Fail)

        originals: dict[Path, bytes] = {}
        targets: dict[str, Path] = {}
        for attr, source in CANONICAL.items():
            target = tmp / source.name
            shutil.copyfile(source, target)
            setattr(reconciler, attr, target)
            originals[target] = target.read_bytes()
            targets[attr] = target

        # Reconcile may project valid append-only authority into derived contract
        # status, but corrupt registry authority must remain corrupt and be
        # rejected rather than silently normalized by the next reconcile.
        corruption_cases = (
            ("typed registeredRecordCount drift", "REGISTRY", "registeredRecordCount", 1),
            ("typed boolean completeRecordCount", "REGISTRY", "completeRecordCount", True),
            ("typed productionEvidence boundary drift", "REGISTRY", "productionEvidence", True),
            ("generation registeredEvidenceCount drift", "GEN_REGISTRY", "registeredEvidenceCount", 1),
            ("generation boolean candidate count", "GEN_REGISTRY", "productionEquivalentRecoveryCandidateCount", True),
            ("generation productionReady boundary drift", "GEN_REGISTRY", "productionReady", True),
        )
        for name, attr, field, invalid_value in corruption_cases:
            for path, expected in originals.items():
                path.write_bytes(expected)
            target = targets[attr]
            payload = json.loads(target.read_text(encoding="utf-8"))
            payload[field] = invalid_value
            target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            before = {path: path.read_bytes() for path in originals}
            expect_domain_fail(name, reconciler.main, reconciler.Fail)
            for path, expected in before.items():
                require(path.read_bytes() == expected, f"reconcile auto-healed corrupt authority: {path.name} during {name}")

        for path, expected in originals.items():
            path.write_bytes(expected)

        failing_validator = tmp / "forced-validator-failure.py"
        failing_validator.write_text("#!/usr/bin/env python3\nraise SystemExit(29)\n", encoding="utf-8")
        reconciler.VALIDATOR = failing_validator

        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require("typed non-resurrection validator failed" in str(exc), f"unexpected reconcile failure: {exc}")
        else:
            raise Fail("forced typed post-validation failure unexpectedly accepted")

        for path, expected in originals.items():
            require(path.read_bytes() == expected, f"rollback drifted typed authority: {path.name}")

    print("PASS reject: corrupt typed/generation append-only authority is never auto-healed by reconcile")
    print("PASS rollback: typed reconcile restores typed registry/generation registry/contract/status byte-for-byte")
    print("Typed non-resurrection reconcile negative suite PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"TYPED NON-RESURRECTION RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
