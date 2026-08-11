#!/usr/bin/env python3
"""Prove generation-evidence authority loading fails closed on unreadable repo-local inputs."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_generation_evidence_validator_load_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load generation evidence validator")
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
    require(VALIDATOR.is_file(), "generation evidence validator missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    validator = load_validator()

    with tempfile.TemporaryDirectory(prefix=".tmp-generation-evidence-load-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)

        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_domain_fail("invalid UTF-8 authority JSON", lambda: validator.load(invalid_utf8), validator.Fail)

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_domain_fail("authority path is unreadable directory", lambda: validator.load(directory_authority), validator.Fail)

    print("Generation evidence unreadable-authority negative suite PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION EVIDENCE LOAD NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
