#!/usr/bin/env python3
"""Privacy-safe, canonical atomic diagnostic writer for local database outage drills."""

from __future__ import annotations

import json
import math
import os
import re
import stat
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

RELATIVE_PATH = Path("docs/fixtures/memory-os-operability/database-commit-outage-diagnostic.last.json")
SAFE_OUTPUT = "Database outage drill finished; raw harness output withheld."
RESULT_RELATIVE_PATH = Path("docs/fixtures/memory-os-operability/database-commit-outage-results.sample.v1.json")


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
    require(type(duration) in (int, float), "diagnostic duration invalid")
    try:
        finite_duration = math.isfinite(float(duration))
    except (OverflowError, ValueError):
        finite_duration = False
    require(finite_duration and duration >= 0, "diagnostic duration invalid")
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


def write_local_result(path: Path, value: dict[str, Any], repo_root: Path) -> None:
    """Publish only synthetic, nonproduction local outage results atomically."""
    require(isinstance(path, Path) and isinstance(repo_root, Path), "result paths must be Path")
    require(path == repo_root / RESULT_RELATIVE_PATH, "database outage result authority drift")
    require(isinstance(value, dict), "database outage result must be object")
    required = {
        "schemaVersion", "commitSha", "generatedAt", "environment", "result",
        "integrityResult", "exitCode", "durationSeconds", "assertions", "limitations",
    }
    require(set(value) == required, "database outage result fields drift")
    require(value["schemaVersion"] == "memory-os-database-commit-outage-results.v1",
            "database outage result schema drift")
    require(isinstance(value["commitSha"], str) and
            re.fullmatch(r"[0-9a-f]{40}", value["commitSha"]) is not None,
            "database outage result source SHA invalid")
    require(isinstance(value["generatedAt"], str) and
            re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z",
                         value["generatedAt"]) is not None,
            "database outage result timestamp invalid")
    try:
        datetime.fromisoformat(value["generatedAt"][:-1] + "+00:00")
    except ValueError:
        raise DiagnosticWriteFailure("database outage result timestamp calendar invalid") from None
    require(value["result"] == "PASS" and value["integrityResult"] == "PASS" and
            type(value["exitCode"]) is int and value["exitCode"] == 0,
            "database outage result success claim drift")
    duration = value["durationSeconds"]
    require(type(duration) in (int, float), "database outage result duration invalid")
    try:
        finite_duration = math.isfinite(float(duration))
    except (OverflowError, ValueError):
        finite_duration = False
    require(finite_duration and duration >= 0, "database outage result duration invalid")
    env = value["environment"]
    require(isinstance(env, dict) and env.get("productionEvidence") is False and
            env.get("containsSecrets") is False and env.get("syntheticDataOnly") is True,
            "database outage result cannot contain secrets or production evidence")
    require(isinstance(value["assertions"], dict) and
            isinstance(value["limitations"], list), "database outage result evidence shape drift")
    try:
        serialized = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, OverflowError):
        raise DiagnosticWriteFailure("database outage result JSON invalid") from None
    lowered = serialized.lower()
    for forbidden in (
        "postgres://", "postgresql://", "password=", "minio_root_password",
        "objectversionid", "spoolpath", "secretaccesskey", "user content",
    ):
        require(forbidden not in lowered, "database outage result contains forbidden runtime material")
    for candidate in (path, *path.parents):
        require(not candidate.is_symlink(), "database outage result symlink rejected")
    require(path.parent.is_dir(), "database outage result parent missing")
    require(not path.exists() or path.is_file(), "database outage result nonregular target rejected")
    try:
        path.parent.resolve(strict=True).relative_to(repo_root.resolve(strict=True))
    except (OSError, ValueError):
        raise DiagnosticWriteFailure("database outage result escaped repository") from None
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    payload = (serialized + "\n").encode("utf-8")
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
        raise DiagnosticWriteFailure("database outage result atomic write failed") from None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
