#!/usr/bin/env python3
"""Reject corrupt observability-stack authority before reconcile mutation."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts/operations/observability-stack-deployment-registry.v1.json"
CONTRACT = ROOT / "contracts/operations/observability-stack-deployment-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
WRITER = ROOT / "scripts/register-memory-os-observability-stack-deployment.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-observability-stack-deployment.py"
TEMP_POST_SOURCE = ROOT / "docs/fixtures/memory-os-operability/.observability-stack-post-source-negative.tmp"
TEMP_SYMLINK = ROOT / "docs/fixtures/memory-os-operability/.observability-stack-symlink-negative.tmp"


def load_writer():
    spec = importlib.util.spec_from_file_location("observability_stack_writer", WRITER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load observability stack writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_writer_rejected(writer, registry, label: str) -> None:
    try:
        writer.validate_registry_for_append(registry, validate_rows=False)
    except writer.Fail:
        return
    raise RuntimeError(f"writer accepted corrupt observability stack registry: {label}")


def expect_ref_rejected(writer, ref: str, source: str, label: str) -> None:
    try:
        writer.source_bound_ref(ref, source, "negativeEvidenceRef")
    except writer.Fail:
        return
    raise RuntimeError(f"writer accepted invalid source-bound stack evidence: {label}")


def create_descendant_commit() -> str:
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip()
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "observability-negative",
        "GIT_AUTHOR_EMAIL": "observability-negative@example.invalid",
        "GIT_COMMITTER_NAME": "observability-negative",
        "GIT_COMMITTER_EMAIL": "observability-negative@example.invalid",
    })
    return subprocess.check_output(
        ["git", "commit-tree", tree, "-p", "HEAD", "-m", "observability stack non-ancestor fixture"],
        cwd=ROOT,
        env=env,
        text=True,
    ).strip()


def main() -> int:
    writer = load_writer()
    registry_bytes = REGISTRY.read_bytes()
    contract_bytes = CONTRACT.read_bytes()
    status_bytes = STATUS.read_bytes()
    registry = json.loads(registry_bytes.decode("utf-8"))

    cases = []
    candidate = copy.deepcopy(registry)
    candidate["admittedStackCount"] = True
    cases.append(("boolean admitted count", candidate))
    candidate = copy.deepcopy(registry)
    candidate["appendOnly"] = False
    cases.append(("append-only disabled", candidate))
    candidate = copy.deepcopy(registry)
    candidate["productionReady"] = True
    cases.append(("production ready escalation", candidate))
    candidate = copy.deepcopy(registry)
    candidate["schemaVersion"] = "memory-os-observability-stack-deployment-registry.v999"
    cases.append(("registry schema drift", candidate))

    for label, candidate in cases:
        expect_writer_rejected(writer, candidate, label)

    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if not writer.source_is_ancestor(source):
        raise RuntimeError("current HEAD must be accepted as source ancestor")
    descendant = create_descendant_commit()
    if writer.source_is_ancestor(descendant):
        raise RuntimeError("future descendant commit was accepted as source ancestor")

    try:
        TEMP_POST_SOURCE.write_text("created after source commit\n", encoding="utf-8")
        expect_ref_rejected(
            writer,
            str(TEMP_POST_SOURCE.relative_to(ROOT)),
            source,
            "post-source evidence",
        )
        try:
            TEMP_SYMLINK.symlink_to(ROOT / "README.md")
        except (OSError, NotImplementedError):
            pass
        else:
            expect_ref_rejected(
                writer,
                str(TEMP_SYMLINK.relative_to(ROOT)),
                source,
                "symlink evidence",
            )
    finally:
        TEMP_POST_SOURCE.unlink(missing_ok=True)
        TEMP_SYMLINK.unlink(missing_ok=True)

    try:
        corrupted = copy.deepcopy(registry)
        corrupted["admittedStackCount"] = True
        REGISTRY.write_text(json.dumps(corrupted, indent=2) + "\n", encoding="utf-8")
        completed = subprocess.run(
            ["python", str(RECONCILER)],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if completed.returncode == 0:
            raise RuntimeError("reconciler accepted corrupt observability stack registry")
        if CONTRACT.read_bytes() != contract_bytes:
            raise RuntimeError("rejected reconcile mutated observability stack contract")
        if STATUS.read_bytes() != status_bytes:
            raise RuntimeError("rejected reconcile mutated production operability status")
    finally:
        REGISTRY.write_bytes(registry_bytes)
        CONTRACT.write_bytes(contract_bytes)
        STATUS.write_bytes(status_bytes)

    print("PASS: observability stack registry/source-binding corruption is rejected without mutation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
