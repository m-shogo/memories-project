#!/usr/bin/env python3
"""Prove generation-evidence reconcile preserves primary failure when rollback also fails."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-generation-evidence.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CANONICAL = {
    "CONTRACT": ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
    "REGISTRY": ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "GEN_REGISTRY": ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "OBJECTIVES_REGISTRY": ROOT / "contracts/operations/recovery-objectives-registry.v1.json",
    "DRILL_REGISTRY": ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json",
    "BINDING": ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json",
    "STATUS": ROOT / "contracts/operations/production-operability-status.json",
}
MUTATED = ("REGISTRY", "CONTRACT", "BINDING", "STATUS")


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_generation_evidence_rollback_diagnostics_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load generation evidence reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def main() -> int:
    require(RECONCILER.is_file(), "generation evidence reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    reconciler = load_reconciler()

    original_enforcer = reconciler.enforce_runtime_authorities
    original_post_validator = reconciler.run_post_validator
    original_replace = reconciler.os.replace
    original_paths = {attr: getattr(reconciler, attr) for attr in CANONICAL}
    try:
        reconciler.enforce_runtime_authorities = lambda: None
        with tempfile.TemporaryDirectory(prefix=".tmp-generation-evidence-rollback-diagnostics-", dir=TMP_PARENT) as tmpdir:
            tmp = Path(tmpdir)
            originals: dict[Path, bytes] = {}
            original_modes: dict[Path, int] = {}
            targets: dict[str, Path] = {}
            for attr, source in CANONICAL.items():
                target = tmp / source.name
                shutil.copyfile(source, target)
                if attr in MUTATED:
                    target.chmod(0o640)
                setattr(reconciler, attr, target)
                originals[target] = target.read_bytes()
                original_modes[target] = mode(target)
                targets[attr] = target

            observed_validators: list[str] = []

            def fail_final_validator(path: Path, expected_relative: Path, label: str) -> None:
                observed_validators.append(label)
                if label == "operability validator":
                    raise reconciler.Fail("synthetic generation evidence aggregate operability rejection")

            reconciler.run_post_validator = fail_final_validator
            replace_calls = 0

            def fail_first_rollback_replace(source: str | Path, destination: str | Path) -> None:
                nonlocal replace_calls
                replace_calls += 1
                # Four successful candidate publications happen before post-validation.
                # Fail only the first rollback replacement; later rollback attempts must continue.
                if replace_calls == 5:
                    raise OSError("synthetic first generation-evidence rollback replace rejection")
                original_replace(source, destination)

            reconciler.os.replace = fail_first_rollback_replace
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                diagnostic = str(exc)
                require(
                    "synthetic generation evidence aggregate operability rejection" in diagnostic,
                    f"primary generation-evidence failure was masked: {diagnostic}",
                )
                require("rollback incomplete" in diagnostic, f"rollback incompleteness missing from diagnostic: {diagnostic}")
                require(
                    "synthetic first generation-evidence rollback replace rejection" in diagnostic,
                    f"rollback failure missing from diagnostic: {diagnostic}",
                )
            else:
                raise Fail("compound generation-evidence post-validation/rollback failure unexpectedly accepted")

            require(
                observed_validators == ["generation binding validator", "generation evidence validator", "operability validator"],
                f"generation-evidence post-validator order drift: {observed_validators}",
            )
            require(replace_calls == 8, f"rollback failure skipped later authority restores: replace calls={replace_calls}")

            first_failed = targets["REGISTRY"]
            require(
                first_failed.read_bytes() != originals[first_failed],
                "synthetically failed first rollback unexpectedly restored generation evidence registry",
            )
            for attr in ("CONTRACT", "BINDING", "STATUS"):
                path = targets[attr]
                require(path.read_bytes() == originals[path], f"later rollback restore skipped authority bytes: {path.name}")
                require(mode(path) == original_modes[path], f"later rollback restore drifted authority mode: {path.name}")

            leftovers: list[Path] = []
            for attr in MUTATED:
                path = targets[attr]
                leftovers.extend(path.parent.glob(f".{path.name}.*.tmp"))
            require(not leftovers, f"compound rollback failure left temporary authority files: {leftovers}")
    finally:
        reconciler.enforce_runtime_authorities = original_enforcer
        reconciler.run_post_validator = original_post_validator
        reconciler.os.replace = original_replace
        for attr, value in original_paths.items():
            setattr(reconciler, attr, value)

    print("PASS rollback: generation-evidence primary failure remains visible when first rollback write fails")
    print("PASS rollback: generation-evidence rollback continues restoring later authorities after first rollback failure")
    print("production-equivalent generation or recovery evidence created: false")
    print("productionDecision promotion attempted: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION EVIDENCE ROLLBACK DIAGNOSTICS NEGATIVE FAILED: {exc}", file=__import__("sys").stderr)
        raise SystemExit(1)
