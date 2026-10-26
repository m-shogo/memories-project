#!/usr/bin/env python3
"""Run repeatability reconciliation negatives in a disposable exact-source checkout."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEGATIVE = "scripts/validate-memory-os-controlled-saturation-repeatability-reconcile-negative.py"
RECONCILER = "scripts/reconcile-memory-os-controlled-saturation-repeatability.py"


class Fail(RuntimeError):
    pass


def run() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reconcile-only", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="memory-os-repeatability-disposable-") as temp:
        root = Path(temp)
        archive = root / "source.tar"
        checkout = root / "checkout"
        checkout.mkdir()
        subprocess.run(
            ["git", "archive", "--format=tar", f"--output={archive}", "HEAD"],
            cwd=ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        with tarfile.open(archive, mode="r") as source:
            source.extractall(path=checkout, filter="data")
        target = RECONCILER if args.reconcile_only else NEGATIVE
        result = subprocess.run(
            [sys.executable, target], cwd=checkout,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0:
            raise Fail(f"disposable repeatability {Path(target).name} failed (exit {result.returncode})")
    print("Memory OS repeatability disposable reconcile runtime PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except (Fail, OSError, subprocess.SubprocessError, tarfile.TarError) as exc:
        print(f"REPEATABILITY DISPOSABLE RUNTIME FAILED: {type(exc).__name__}")
        raise SystemExit(1)
