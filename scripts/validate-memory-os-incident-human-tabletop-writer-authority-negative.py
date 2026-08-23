#!/usr/bin/env python3
"""Prove the human-tabletop CLI cannot substitute canonical evidence authorities."""

from __future__ import annotations

import importlib.util
import inspect
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-incident-human-tabletop.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_incident_human_tabletop_writer_authority_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load human tabletop writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(label: str, action: Callable[[], object], failure_type: type[BaseException]) -> None:
    try:
        action()
    except failure_type:
        print(f"PASS reject: {label}")
        return
    except Exception as exc:
        raise Fail(f"{label} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {label}")


def main() -> int:
    writer = load_writer()
    require(callable(getattr(writer, "require_actual_cli_authorities", None)),
            "human tabletop writer CLI authority guard missing")
    require("require_actual_cli_authorities()" in inspect.getsource(writer.main),
            "human tabletop writer main does not enforce CLI authority guard")
    writer.require_actual_cli_authorities()

    with tempfile.TemporaryDirectory(prefix="memory-os-tabletop-authority-") as temp_dir:
        outside = Path(temp_dir) / "outside-authority.json"
        outside.write_text("{}\n", encoding="utf-8")
        substitutions = (
            ("CANONICAL_VALIDATOR", ROOT / "scripts/validate-memory-os-incident-tabletop.py"),
            ("TABLETOP_CONTRACT", writer.CANONICAL_TABLETOP_CONTRACT),
            ("INCIDENT_POLICY", writer.CANONICAL_INCIDENT_POLICY),
            ("PLAN", writer.CANONICAL_PLAN),
            ("LEDGER", writer.CANONICAL_LEDGER),
        )
        for attribute, canonical in substitutions:
            original = getattr(writer, attribute)
            try:
                setattr(writer, attribute, outside)
                expect_rejected(
                    f"human tabletop writer CLI {attribute} substitution",
                    writer.require_actual_cli_authorities,
                    writer.WriterFailure,
                )
            finally:
                setattr(writer, attribute, original)
            require(getattr(writer, attribute) == canonical,
                    f"human tabletop writer CLI {attribute} canonical authority not restored")

    writer.require_actual_cli_authorities()
    print("Memory OS human tabletop writer authority negative suite PASS")
    print("writer CLI validator/contract/policy/plan/ledger substitution accepted: false")
    print("human tabletop evidence generated: false")
    print("production evidence generated: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"HUMAN TABLETOP WRITER AUTHORITY NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
