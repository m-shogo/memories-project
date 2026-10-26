#!/usr/bin/env python3
"""Negative coverage for Apple replay restore repository authority containment."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-local-apple-replay-restore.py"
WORKFLOW = ROOT / ".github/workflows/local-apple-replay-restore.yml"


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_local_apple_replay_restore_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Apple replay restore validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_fail(call: Callable[[], object], needle: str) -> None:
    try:
        call()
    except Exception as exc:  # domain-specific Fail is loaded dynamically
        if needle not in str(exc):
            raise AssertionError(f"unexpected rejection: {exc}") from exc
        return
    raise AssertionError(f"expected rejection containing {needle!r}")


def require_workflow_source(source: str) -> None:
    """Enforce least-privilege source and a fixed-output diagnostic boundary."""
    def require(condition: bool, message: str) -> None:
        if not condition:
            raise AssertionError(message)

    require("permissions:\n  contents: read\n" in source, "Apple workflow global write permission drift")
    require(
        "  replay-restore:\n    if: github.event_name != 'pull_request' && github.ref == 'refs/heads/so'\n    permissions:\n      contents: write\n" in source,
        "Apple workflow write job not restricted to so",
    )
    uses = re.findall(r"^\\s+uses: (actions/(?:checkout|setup-python))@([^\\s]+)$", source, re.MULTILINE)
    require(
        uses.count(("actions/checkout", "11d5960a326750d5838078e36cf38b85af677262")) == 2
        and uses.count(("actions/setup-python", "a26af69be951a213d495a4c3e4e4022e16d87065")) == 2
        and len(uses) == 4,
        "Apple workflow floating or substituted action",
    )
    require(
        "output = 'REDACTED: local Apple replay restore output withheld'" in source,
        "Apple workflow fixed diagnostic output missing",
    )
    require(
        "read_text(encoding='utf-8', errors='replace')" not in source
        and "cat /tmp/replay-validation.log" not in source,
        "Apple workflow raw private output disclosure",
    )
    require(
        "trap 'rm -f /tmp/local-apple-replay-restore.log' EXIT" in source
        and "trap 'rm -f /tmp/replay-validation.log' EXIT" in source,
        "Apple workflow private log cleanup missing",
    )
    require(
        "echo 'REDACTED: local Apple replay validation output withheld'" in source,
        "Apple workflow validation output not redacted",
    )


def prove_workflow_diagnostic_negative() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    require_workflow_source(source)
    mutations = (
        ("permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("&& github.ref == 'refs/heads/so'", ""),
        ("actions/checkout@11d5960a326750d5838078e36cf38b85af677262", "actions/checkout@v4"),
        ("output = 'REDACTED: local Apple replay restore output withheld'", "output = Path('/tmp/local-apple-replay-restore.log').read_text(encoding='utf-8', errors='replace')"),
        ("echo 'REDACTED: local Apple replay validation output withheld'", "cat /tmp/replay-validation.log"),
        ("trap 'rm -f /tmp/replay-validation.log' EXIT", "# private log cleanup removed"),
    )
    for original, replacement in mutations:
        if original not in source:
            raise AssertionError("Apple workflow diagnostic mutation anchor missing")
        mutated = source.replace(original, replacement)
        try:
            require_workflow_source(mutated)
        except AssertionError:
            pass
        else:
            raise AssertionError("Apple workflow unsafe source mutation accepted")

    match = re.search(r"DRILL_EXIT_CODE=\\\"\\$code\\\" python - <<'PY'\\n(?P<body>.*?)\\n          PY", source, re.DOTALL)
    if match is None:
        raise AssertionError("Apple workflow diagnostic Python body missing")
    body = textwrap.dedent(match.group("body"))
    if "read_text" in body or "subprocess" in body or "eval(" in body:
        raise AssertionError("Apple workflow diagnostic body can read private output")
    with tempfile.TemporaryDirectory(prefix="memory-os-apple-diagnostic-negative-") as tmp:
        for code, result in ((0, "PASS"), (7, "FAIL")):
            env = {**os.environ, "SOURCE_SHA": "a" * 40, "DRILL_EXIT_CODE": str(code)}
            proc = subprocess.run(
                [sys.executable, "-c", body],
                cwd=tmp, env=env, capture_output=True, text=True, timeout=10, check=False,
            )
            if proc.returncode != 0 or proc.stdout or proc.stderr:
                raise AssertionError("Apple workflow diagnostic did not execute privately")
            output = json.loads(
                (Path(tmp) / "docs/fixtures/memory-os-operability/local-apple-replay-restore-diagnostic.last.json")
                .read_text(encoding="utf-8")
            )
            expected = {
                "schemaVersion": "memory-os-validator-diagnostic.v1",
                "workflow": "local-apple-replay-restore",
                "sourceCommitSha": "a" * 40,
                "result": result,
                "exitCode": code,
                "output": "REDACTED: local Apple replay restore output withheld",
                "containsSecrets": False,
                "productionEvidence": False,
            }
            if output != expected:
                raise AssertionError("Apple workflow diagnostic payload drift")


def main() -> int:
    validator = load_validator()
    prove_workflow_diagnostic_negative()
    result_path: Path = validator.RESULT
    original_exists = result_path.exists() or result_path.is_symlink()
    original_bytes = result_path.read_bytes() if result_path.is_file() and not result_path.is_symlink() else None

    temp_root = Path(tempfile.mkdtemp(prefix="memory-os-apple-replay-authority-negative-"))
    external_result = temp_root / "result.json"
    external_result.write_bytes(original_bytes if original_bytes is not None else b"{}\n")
    parent_link = ROOT / "docs/fixtures/memory-os-operability/.apple-replay-parent-symlink-negative"
    external_parent = temp_root / "parent"
    external_parent.mkdir()
    (external_parent / "evidence.json").write_text("{}\n", encoding="utf-8")

    try:
        if result_path.exists() or result_path.is_symlink():
            result_path.unlink()
        result_path.symlink_to(external_result)
        expect_fail(validator.main, "symlink component")

        parent_link.symlink_to(external_parent, target_is_directory=True)
        expect_fail(
            lambda: validator.require_repo_regular_file(
                parent_link / "evidence.json", "synthetic parent-symlink authority"
            ),
            "symlink component",
        )
    finally:
        if result_path.exists() or result_path.is_symlink():
            result_path.unlink()
        if original_exists and original_bytes is not None:
            result_path.write_bytes(original_bytes)
        if parent_link.exists() or parent_link.is_symlink():
            parent_link.unlink()
        shutil.rmtree(temp_root, ignore_errors=True)

    print("PASS: Apple replay restore authorities reject symlink aliases and parent escapes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
