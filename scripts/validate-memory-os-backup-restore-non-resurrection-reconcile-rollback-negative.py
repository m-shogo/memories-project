#!/usr/bin/env python3
"""Prove typed non-resurrection reconcile rolls back on aggregate failure."""
from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-non-resurrection-authority.py"
TEMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(name: str, action: Callable[[], Any], failure: type[BaseException]) -> None:
    try:
        action()
    except failure:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def main() -> int:
    require(RECONCILER.is_file(), "typed non-resurrection reconciler missing")
    require(TEMP_PARENT.is_dir(), "repo-local temporary fixture parent missing")
    reconciler = load_module(RECONCILER, "memory_os_non_resurrection_reconcile_rollback_negative")

    with tempfile.TemporaryDirectory(prefix=".tmp-nonres-reconcile-rollback-", dir=TEMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        paths = {}
        for attr in ("REGISTRY", "GEN_REGISTRY", "CONTRACT", "STATUS"):
            source = getattr(reconciler, attr)
            target = tmp / source.name
            shutil.copyfile(source, target)
            paths[attr] = target

        pass_validator = tmp / "pass-validator.py"
        pass_validator.write_text("#!/usr/bin/env python3\nraise SystemExit(0)\n", encoding="utf-8")
        fail_validator = tmp / "fail-validator.py"
        fail_validator.write_text("#!/usr/bin/env python3\nraise SystemExit(47)\n", encoding="utf-8")

        originals = {attr: getattr(reconciler, attr) for attr in paths}
        originals["VALIDATOR"] = reconciler.VALIDATOR
        originals["OPERABILITY_VALIDATOR"] = reconciler.OPERABILITY_VALIDATOR
        before = {attr: path.read_bytes() for attr, path in paths.items()}
        try:
            for attr, path in paths.items():
                setattr(reconciler, attr, path)
            reconciler.VALIDATOR = pass_validator
            reconciler.OPERABILITY_VALIDATOR = fail_validator
            expect_rejected(
                "typed recovery operability aggregate failure",
                reconciler.main,
                reconciler.Fail,
            )
            for attr, path in paths.items():
                require(path.read_bytes() == before[attr], f"{attr} drift after operability rollback")
        finally:
            for attr, value in originals.items():
                setattr(reconciler, attr, value)

    print("Memory OS typed non-resurrection reconcile rollback negative PASS")
    print("typed validator succeeds before aggregate failure: true")
    print("operability aggregate failure leaves partial authority: false")
    print("canonical authority mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE NON-RESURRECTION RECONCILE ROLLBACK NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
