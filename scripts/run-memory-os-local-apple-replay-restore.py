#!/usr/bin/env python3
"""Run a local logical restore drill proving Apple replay guards survive restore."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_CONTRACT = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
MIGRATION_DIR = ROOT / "infra/postgresql/security"
RESULT_PATH = Path(os.environ.get(
    "MEMORY_OS_LOCAL_APPLE_REPLAY_RESTORE_RESULTS_PATH",
    ROOT / "docs/fixtures/memory-os-operability/local-apple-replay-restore-results.sample.v1.json",
))
SHA40 = re.compile(r"^[0-9a-f]{40}$")
NONCE_DIGEST = "ab" * 32
CODE_DIGEST = "cd" * 32


class DrillFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DrillFailure(message)


def execute(command: list[str], *, env: dict[str, str], capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
    )


def require_ok(completed: subprocess.CompletedProcess[str], message: str) -> None:
    require(completed.returncode == 0, message)


def psql(db: str, sql: str, env: dict[str, str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    command = ["psql", "--dbname", db, "--set", "ON_ERROR_STOP=1", "--quiet"]
    if capture:
        command.extend(["--tuples-only", "--no-align"])
    command.extend(["--command", sql])
    return execute(command, env=env, capture=capture)


def scalar(db: str, sql: str, env: dict[str, str]) -> str:
    completed = psql(db, sql, env, capture=True)
    require_ok(completed, "scalar query failed")
    return completed.stdout.strip()


def main() -> int:
    source_sha = os.environ.get("MEMORY_OS_COMMIT_SHA", "")
    require(SHA40.fullmatch(source_sha) is not None, "MEMORY_OS_COMMIT_SHA must be a full SHA")
    require(os.environ.get("MEMORY_OS_ALLOW_EPHEMERAL_DATABASE_DROP") == "1", "ephemeral database drop permission required")
    host = os.environ.get("PGHOST", "127.0.0.1")
    port = os.environ.get("PGPORT", "5432")
    user = os.environ.get("PGUSER", "postgres")
    require(host in {"127.0.0.1", "localhost", "::1"}, "PostgreSQL host must be local")
    pg_env = os.environ.copy()
    pg_env.update({"PGHOST": host, "PGPORT": port, "PGUSER": user})

    migration_contract = json.loads(MIGRATION_CONTRACT.read_text(encoding="utf-8"))
    migrations = migration_contract.get("migrationSequence")
    require(isinstance(migrations, list) and migrations, "canonical migration sequence missing")
    for migration in migrations:
        require((MIGRATION_DIR / migration).is_file(), f"migration missing: {migration}")

    suffix = source_sha[:8]
    source_db = f"memory_os_replay_source_{suffix}"
    target_db = f"memory_os_replay_target_{suffix}"
    fd, dump_name = tempfile.mkstemp(prefix="memory-os-replay-", suffix=".dump")
    os.close(fd)
    dump_path = Path(dump_name)
    started_at = dt.datetime.now(dt.timezone.utc)
    started_monotonic = time.monotonic()

    try:
        for db in (source_db, target_db):
            require_ok(psql("postgres", f'DROP DATABASE IF EXISTS "{db}";', pg_env), "database cleanup failed")
            require_ok(psql("postgres", f'CREATE DATABASE "{db}";', pg_env), "database create failed")

        for migration in migrations:
            completed = execute(
                ["psql", "--dbname", source_db, "--set", "ON_ERROR_STOP=1", "--file", str(MIGRATION_DIR / migration)],
                env=pg_env,
            )
            require_ok(completed, f"migration failed: {migration}")

        consume_sql = (
            "SET ROLE memory_auth_runtime; "
            f"SELECT memory_os.consume_apple_replay('{NONCE_DIGEST}', '{CODE_DIGEST}', 3600); "
            "RESET ROLE;"
        )
        require_ok(psql(source_db, consume_sql, pg_env), "initial replay consumption failed")
        source_count = int(scalar(
            source_db,
            f"SELECT count(*) FROM memory_os.apple_replay WHERE digest IN ('{NONCE_DIGEST}', '{CODE_DIGEST}') AND expires_at > now();",
            pg_env,
        ))
        require(source_count == 2, "source live replay row count must be two")

        dump = execute(
            ["pg_dump", "--format=custom", "--compress=6", "--no-comments", "--file", str(dump_path), source_db],
            env=pg_env,
        )
        require_ok(dump, "pg_dump failed")
        require(dump_path.stat().st_size > 0, "logical dump is empty")

        require_ok(psql("postgres", f'DROP DATABASE "{source_db}";', pg_env), "source database destruction failed")
        restore = execute(["pg_restore", "--exit-on-error", "--dbname", target_db, str(dump_path)], env=pg_env)
        require_ok(restore, "pg_restore failed")

        restored_count = int(scalar(
            target_db,
            f"SELECT count(*) FROM memory_os.apple_replay WHERE digest IN ('{NONCE_DIGEST}', '{CODE_DIGEST}') AND expires_at > now();",
            pg_env,
        ))
        require(restored_count == 2, "restored live replay row count must be two")

        retry = psql(target_db, consume_sql, pg_env)
        replay_reuse_rejected = retry.returncode != 0
        require(replay_reuse_rejected, "identical nonce/code pair was accepted after restore")
        final_count = int(scalar(
            target_db,
            f"SELECT count(*) FROM memory_os.apple_replay WHERE digest IN ('{NONCE_DIGEST}', '{CODE_DIGEST}') AND expires_at > now();",
            pg_env,
        ))
        require(final_count == 2, "failed replay retry changed durable replay rows")

        completed_at = dt.datetime.now(dt.timezone.utc)
        result = {
            "schemaVersion": "memory-os-local-apple-replay-restore-results.v1",
            "commitSha": source_sha,
            "generatedAt": completed_at.isoformat().replace("+00:00", "Z"),
            "environment": {
                "databaseMode": "EPHEMERAL_POSTGRESQL_16_SAME_CLUSTER_LOGICAL_RESTORE",
                "databaseIdentityDigest": hashlib.sha256(f"{host}:{port}:{source_db}:{target_db}".encode()).hexdigest(),
                "productionTraffic": False,
                "productionCredentials": False,
                "productionEvidence": False,
                "containsSecrets": False,
            },
            "scenario": {
                "scenarioId": "apple-live-replay-guard-logical-restore",
                "startedAt": started_at.isoformat().replace("+00:00", "Z"),
                "completedAt": completed_at.isoformat().replace("+00:00", "Z"),
                "durationSeconds": max(0, int(time.monotonic() - started_monotonic)),
                "migrationFilesApplied": len(migrations),
                "databaseDumpBytes": dump_path.stat().st_size,
                "assertions": {
                    "sourceReplayRowsBeforeBackup": source_count,
                    "restoredReplayRows": restored_count,
                    "identicalReplayPairRejectedAfterRestore": replay_reuse_rejected,
                    "replayRowsUnchangedAfterRejectedReuse": final_count == 2,
                },
                "integrityResult": "PASS",
                "result": "PASS",
            },
            "limitations": [
                "same PostgreSQL cluster logical dump and restore",
                "synthetic nonce and authorization-code digests only",
                "not PostgreSQL WAL/PITR or cross-cluster restore evidence",
                "not real Sign in with Apple traffic evidence",
                "not production or production-equivalent recovery evidence",
            ],
        }
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Memory OS local Apple replay restore PASS")
        print("live replay rows restored: 2  identical replay pair rejected: true")
        print(f"result: {RESULT_PATH}")
        return 0
    finally:
        try:
            dump_path.unlink()
        except FileNotFoundError:
            pass
        if os.environ.get("MEMORY_OS_KEEP_REPLAY_RESTORE_DATABASES", "0") != "1":
            for db in (source_db, target_db):
                psql("postgres", f'DROP DATABASE IF EXISTS "{db}";', pg_env)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DrillFailure as exc:
        print(f"LOCAL APPLE REPLAY RESTORE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"LOCAL APPLE REPLAY RESTORE FAILED: unexpected {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(2)
