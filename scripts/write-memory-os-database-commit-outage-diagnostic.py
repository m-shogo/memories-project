#!/usr/bin/env python3
"""Privacy-safe, canonical atomic diagnostic writer for local database outage drills."""

from __future__ import annotations

import json
import math
import os
import re
import stat
import tempfile
from pathlib import Path
from typing import Any

RELATIVE_PATH = Path("docs/fixtures/memory-os-operability/database-commit-outage-diagnostic.last.json")
SAFE_OUTPUT = "Database outage drill finished; raw harness output withheld."


class DiagnosticWriteFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DiagnosticWriteFailure(message)


def write_diagnostic(path: Path, value: dict[str, Any], repo_root: Path) -> None:
    require(isinstance(repo_root, Path) and isinstance(path, Path), "diagnostic paths must be Path")
    require(path == repo_root / RELATIVE_PATH, "database outage diagnostic authority drift")
    require(isinstance(value, dict), "database outage diagnostic must be object")
    required = {
        "schemaVersion", "workflow", "sourceCommitSha", "result", "exitCode",
        "durationSeconds", "output", "containsSecrets", "productionEvidence",
    }
    require(set(value) == required, "database outage diagnostic fields drift")
    require(value["schemaVersion"] == "memory-os-validator-diagnostic.v1", "diagnostic schema drift")
    require(value["workflow"] == "database-commit-outage-recovery", "diagnostic workflow drift")
    require(isinstance(value["sourceCommitSha"], str) and
            re.fullmatch(r"[0-9a-f]{40}", value["sourceCommitSha"]) is not None,
            "diagnostic source SHA invalid")
    code = value["exitCode"]
    require(type(code) is int and (value["result"] == ("PASS" if code == 0 else "FAIL")),
            "diagnostic result/exit code drift")
    duration = value["durationSeconds"]
    require(type(duration) in (int, float) and math.isfinite(float(duration)) and duration >= 0,
            "diagnostic duration invalid")
    require(value["output"] == SAFE_OUTPUT, "raw diagnostic output forbidden")
    require(value["containsSecrets"] is False and value["productionEvidence"] is False,
            "diagnostic cannot contain secrets or production evidence")
    for candidate in (path, *path.parents):
        require(not candidate.is_symlink(), "database outage diagnostic symlink rejected")
    require(path.parent.is_dir(), "database outage diagnostic parent missing")
    require(not path.exists() or path.is_file(), "database outage diagnostic nonregular target rejected")
    try:
        path.parent.resolve(strict=True).relative_to(repo_root.resolve(strict=True))
    except (OSError, ValueError):
        raise DiagnosticWriteFailure("database outage diagnostic escaped repository") from None
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    payload = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fchmod(handle.fileno(), mode)
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    except OSError:
        raise DiagnosticWriteFailure("database outage diagnostic atomic write failed") from None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
