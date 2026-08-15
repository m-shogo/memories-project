#!/usr/bin/env python3
"""Fail closed on mutable or generic material-delta review references.

Cross-generation recovery evidence must reference one committed, append-only file under
`docs/evidence/backup-restore/material-delta/`. Same-generation evidence must keep the
reference null. This validator does not create review evidence or production authority.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
MATERIAL_DELTA_ROOT = Path("docs/evidence/backup-restore/material-delta")


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_json(path: Path, field: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Fail(f"{field} unreadable or invalid JSON: {exc}") from exc
    require(isinstance(value, dict), f"{field} root must be object")
    return value


def canonical_material_delta_ref(value: Any, field: str) -> tuple[str, Path]:
    require(isinstance(value, str) and value, f"{field} required")
    relative = Path(value)
    require(
        not relative.is_absolute()
        and ".." not in relative.parts
        and relative.as_posix() == value,
        f"{field} must be canonical repository-relative path",
    )
    require(
        relative.parts[: len(MATERIAL_DELTA_ROOT.parts)] == MATERIAL_DELTA_ROOT.parts
        and len(relative.parts) > len(MATERIAL_DELTA_ROOT.parts),
        f"{field} must remain inside {MATERIAL_DELTA_ROOT.as_posix()}/",
    )
    path = ROOT / relative
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(resolved == relative and path.is_file(), f"{field} must resolve to canonical repository file")
    return value, path


def git_history(ref: str, field: str) -> list[str]:
    completed = subprocess.run(
        ["git", "log", "--format=%H", "--follow", "--", ref],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(completed.returncode == 0, f"cannot inspect {field} Git history")
    commits = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    require(commits, f"{field} must be committed material-delta review evidence")
    return commits


def require_append_only_review(ref: str, path: Path, field: str) -> None:
    commits = git_history(ref, field)
    require(len(commits) == 1, f"{field} must remain append-only after its first committed version")
    completed = subprocess.run(
        ["git", "show", f"{commits[0]}:{ref}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(completed.returncode == 0, f"cannot read initial committed bytes for {field}")
    require(path.read_bytes() == completed.stdout, f"{field} bytes drift from initial committed material-delta review evidence")


def validate_row(row: dict[str, Any], index: int) -> None:
    source = row.get("sourceEnvironmentGenerationId")
    target = row.get("restoreTargetGenerationId")
    require(isinstance(source, str) and source, f"records[{index}] sourceEnvironmentGenerationId required")
    require(isinstance(target, str) and target, f"records[{index}] restoreTargetGenerationId required")
    value = row.get("materialDeltaReviewRef")
    if source == target:
        require(value is None, f"records[{index}] same-generation restore must not declare materialDeltaReviewRef")
        return
    ref, path = canonical_material_delta_ref(value, f"records[{index}].materialDeltaReviewRef")
    require_append_only_review(ref, path, f"records[{index}].materialDeltaReviewRef")


def main() -> int:
    registry = load_json(REGISTRY, "generation evidence registry")
    require(registry.get("schemaVersion") == "memory-os-backup-restore-generation-evidence-registry.v1", "generation evidence registry schema drift")
    require(registry.get("appendOnly") is True, "generation evidence registry must remain append-only")
    require(registry.get("productionEvidence") is False and registry.get("productionReady") is False, "generation evidence registry production boundary drift")
    rows = registry.get("records")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "generation evidence registry records invalid")
    for index, row in enumerate(rows):
        validate_row(row, index)
    print(f"PASS: generation material-delta review authority records={len(rows)} productionEvidence=false productionReady=false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
