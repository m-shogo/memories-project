#!/usr/bin/env python3
"""Run the canonical end-to-end OPS-P0-007 admission-chain validation sequence.

This runner centralizes the validation order shared by pull-request read-only
validation and non-PR derived-authority publication. It never creates a
production generation, recovery objective, drill request/evidence, credentials,
or traffic. The only reconcile steps are deterministic derived-authority
projections; productionDecision remains NO_GO.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEPS: tuple[tuple[str, str], ...] = (
    ("scripts/validate-memory-os-backup-restore-admission-chain-workflow-permissions.py", "admission-chain workflow permission boundary"),
    ("scripts/validate-memory-os-production-equivalent-environment-generation.py", "environment generation authority"),
    ("scripts/validate-memory-os-production-equivalent-environment-generation-negative.py", "environment generation semantic negative"),
    ("scripts/validate-memory-os-production-equivalent-generation-reconcile-negative.py", "environment generation reconcile negative"),
    ("scripts/validate-memory-os-recovery-objectives.py", "recovery objectives authority"),
    ("scripts/validate-memory-os-recovery-objectives-negative.py", "recovery objectives semantic negative"),
    ("scripts/validate-memory-os-recovery-objectives-reconcile-negative.py", "recovery objectives reconcile negative"),
    ("scripts/validate-memory-os-backup-restore-drill-preflight.py", "restore preflight authority"),
    ("scripts/validate-memory-os-backup-restore-drill-preflight-negative.py", "restore preflight semantic negative"),
    ("scripts/validate-memory-os-backup-restore-drill-preflight-load-negative.py", "restore preflight authority/rollback negative"),
    ("scripts/validate-memory-os-backup-restore-preflight-generation-eligibility-consistency.py", "preflight semantic eligibility consistency"),
    ("scripts/validate-memory-os-backup-restore-preflight-generation-eligibility-consistency-negative.py", "preflight semantic eligibility negative"),
    ("scripts/validate-memory-os-backup-restore-drill-request-negative.py", "reviewed drill request semantic negative"),
    ("scripts/validate-memory-os-backup-restore-drill-request-reconcile-negative.py", "reviewed drill request reconcile negative"),
    ("scripts/validate-memory-os-backup-restore-drill-generation-eligibility-binding-reconcile-negative.py", "reviewed request semantic-generation binding reconcile negative"),
    ("scripts/reconcile-memory-os-backup-restore-drill-generation-eligibility-binding.py", "reviewed request semantic-generation binding reconcile"),
    ("scripts/validate-memory-os-backup-restore-drill-generation-eligibility-binding.py", "reviewed request semantic-generation binding authority"),
    ("scripts/validate-memory-os-backup-restore-generation-evidence-contract-path-negative.py", "generation evidence contract-path negative"),
    ("scripts/validate-memory-os-backup-restore-generation-evidence-negative.py", "generation evidence semantic negative"),
    ("scripts/validate-memory-os-backup-restore-semantic-generation-negative.py", "generation evidence semantic-generation negative"),
    ("scripts/validate-memory-os-backup-restore-generation-evidence-reconcile-negative.py", "generation evidence reconcile negative"),
    ("scripts/validate-memory-os-backup-restore-non-resurrection-contract-path-negative.py", "typed non-resurrection contract-path negative"),
    ("scripts/validate-memory-os-backup-restore-non-resurrection-negative.py", "typed non-resurrection semantic negative"),
    ("scripts/validate-memory-os-backup-non-resurrection-reconcile-negative.py", "typed non-resurrection reconcile negative"),
    ("scripts/validate-memory-os-backup-restore-generation-status-reconcile-negative.py", "generation binding status reconcile negative"),
    ("scripts/reconcile-memory-os-backup-restore-admission-chain.py", "admission-chain deterministic reconcile"),
    ("scripts/validate-memory-os-backup-restore-admission-chain.py", "admission-chain authority"),
    ("scripts/validate-memory-os-backup-restore-admission-chain-negative.py", "admission-chain semantic negative"),
    ("scripts/validate-memory-os-backup-restore-admission-chain-reconcile-negative.py", "admission-chain reconcile negative"),
    ("scripts/validate-memory-os-backup-restore-drill-request.py", "reviewed drill request authority"),
    ("scripts/validate-memory-os-backup-restore-generation-evidence.py", "generation evidence authority"),
    ("scripts/validate-memory-os-backup-restore-generation-candidate-mutation-negative.py", "generation candidate mutation negative"),
    ("scripts/validate-memory-os-backup-restore-generation-candidate-registry-row-mutation-negative.py", "generation candidate registry-row mutation negative"),
    ("scripts/validate-memory-os-backup-restore-generation-binding.py", "generation binding authority"),
    ("scripts/validate-memory-os-backup-restore-generation-binding-negative.py", "generation binding negative"),
    ("scripts/validate-memory-os-backup-restore-non-resurrection-registry-aggregate-negative.py", "typed non-resurrection registry aggregate negative"),
    ("scripts/validate-memory-os-backup-restore-non-resurrection-admission.py", "typed non-resurrection admission"),
    ("scripts/validate-memory-os-operability.py", "aggregate operability"),
)


class Fail(RuntimeError):
    pass


def canonical_script(relative: str) -> Path:
    candidate = ROOT / relative
    expected = Path(relative)
    try:
        lexical = candidate.relative_to(ROOT)
        resolved = candidate.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"validation authority missing or escapes repository: {relative}") from exc
    if lexical != expected or resolved != expected or not candidate.is_file():
        raise Fail(f"validation authority drift: {relative}")
    return candidate


def run_step(relative: str, label: str) -> None:
    script = canonical_script(relative)
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    output = f"{completed.stdout}{completed.stderr}"
    if output:
        print(output, end="" if output.endswith("\n") else "\n")
    if completed.returncode != 0:
        raise Fail(f"{label} failed with exit code {completed.returncode}: {relative}")
    print(f"PASS chain step: {label}")


def main() -> int:
    for relative, label in STEPS:
        run_step(relative, label)
    print("Memory OS end-to-end backup/restore admission-chain validation PASS")
    print(f"canonical validation steps: {len(STEPS)}")
    print("automatic generation/objective/request/evidence creation: false")
    print("production evidence created: false")
    print("production traffic changed: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE ADMISSION CHAIN FULL VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
