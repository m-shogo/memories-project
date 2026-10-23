#!/usr/bin/env python3
"""Negative suite proving the autonomous learning guard fails closed."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = Path("contracts/operations/autonomous-learning-system.json")
LEARNING = Path("docs/operations/AUTONOMOUS-OPS-LEARNING.md")
VALIDATOR = Path("scripts/validate-autonomous-learning-system.py")
NEGATIVE_VALIDATOR = Path("scripts/validate-autonomous-learning-system-negative.py")
CI_ENTRYPOINT = Path("scripts/validate-memory-os-entry-docs.py")


def seed(source_root: Path, root: Path) -> None:
    # The positive validator verifies both executable guard bindings and their
    # CI reachability. Seed the complete canonical authority set so the
    # positive control proves a real pass before any mutation is applied.
    for rel in (CONTRACT, LEARNING, VALIDATOR, NEGATIVE_VALIDATOR, CI_ENTRYPOINT):
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_root / rel, target)


def run(source_root: Path, root: Path) -> subprocess.CompletedProcess[str]:
    # Execute the immutable canonical harness from the checked-out source tree
    # against the isolated fixture. This lets a negative case remove the
    # fixture's bound validator and still prove that the canonical guard rejects
    # the missing executable authority, rather than failing in Python startup.
    try:
        return subprocess.run(
            [sys.executable, str(source_root / VALIDATOR), "--repo-root", str(root)],
            text=True,
            capture_output=True,
            check=False,
            timeout=90,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("autonomous learning canonical negative harness timed out after 90s") from exc


def require_canonical_rejection(name: str, result: subprocess.CompletedProcess[str]) -> None:
    if result.returncode != 1:
        raise RuntimeError(f"negative case did not return canonical exit 1: {name}: {result.returncode}")
    if not result.stderr.startswith("AUTONOMOUS LEARNING VALIDATION FAILED: "):
        raise RuntimeError(f"negative case did not fail through canonical guard: {name}: {result.stderr}")
    if "Traceback (most recent call last)" in result.stderr:
        raise RuntimeError(f"negative case leaked implementation traceback: {name}")


def prove_failure_classifier() -> None:
    # A validator startup/implementation failure must not count as a
    # successful negative admission rejection.
    invalid = (
        subprocess.CompletedProcess([], 0, "", "AUTONOMOUS LEARNING VALIDATION FAILED: fake"),
        subprocess.CompletedProcess([], 2, "", "AUTONOMOUS LEARNING VALIDATION FAILED WITH UNEXPECTED ERROR: injected"),
        subprocess.CompletedProcess([], 1, "", "AUTONOMOUS LEARNING VALIDATION FAILED WITH UNEXPECTED ERROR: injected"),
        subprocess.CompletedProcess([], 1, "", "Traceback (most recent call last): injected"),
    )
    for index, result in enumerate(invalid):
        try:
            require_canonical_rejection(f"synthetic classifier {index}", result)
        except RuntimeError:
            pass
        else:
            raise RuntimeError(f"negative failure classifier accepted unrelated result: {index}")
    require_canonical_rejection(
        "synthetic canonical rejection",
        subprocess.CompletedProcess([], 1, "", "AUTONOMOUS LEARNING VALIDATION FAILED: injected canonical guard\n"),
    )


def expected_diagnostic(name: str) -> str:
    """Bind each negative to the invariant it intended to violate."""
    fixed = {
        "weaken mandatory rule": "mandatory learning rule must remain true: unchangedBlockerIsNotRetried",
        "disable required CI reachability": "mandatory learning rule must remain true: ciReachabilityRequired",
        "weaken NO_GO default": "learning must not weaken the NO_GO default",
        "allow non-real OPS-P0-007 evidence": "OPS-P0-007 real-evidence boundary must remain true",
        "merge human promotion review into automation": "human promotion review must remain separate",
        "break executable guard binding": "executable learning guard binding changed",
        "break negative guard binding": "negative learning guard binding changed",
        "break CI entrypoint binding": "learning CI entrypoint binding changed",
        "break learning authority binding": "learning authority path changed",
        "duplicate required failure field": "requiredFailureFields contains duplicates",
        "duplicate required success field": "requiredSuccessFields contains duplicates",
        "remove learning authority": "learning authority path missing or escapes root: docs/operations/AUTONOMOUS-OPS-LEARNING.md",
        "remove executable guard": "learning authority path missing or escapes root: scripts/validate-autonomous-learning-system.py",
        "remove negative guard": "learning authority path missing or escapes root: scripts/validate-autonomous-learning-system-negative.py",
        "remove CI entrypoint": "learning authority path missing or escapes root: scripts/validate-memory-os-entry-docs.py",
        "disconnect positive guard from CI entrypoint": "learning CI entrypoint does not invoke bound guard: scripts/validate-autonomous-learning-system.py",
        "disconnect negative guard from CI entrypoint": "learning CI entrypoint does not invoke bound guard: scripts/validate-autonomous-learning-system-negative.py",
        "remove CI guard execution call": "learning CI entrypoint lost executable guard invocation: validate_learning_guards(failures)",
        "drop CI repo-root guard interface": "learning CI entrypoint lost executable guard invocation: [sys.executable",
        "drop CI guard timeout authority": "learning CI entrypoint lost executable guard invocation: LEARNING_GUARD_TIMEOUT_SECONDS = 120",
        "drop CI guard timeout binding": "learning CI entrypoint lost executable guard invocation: timeout=LEARNING_GUARD_TIMEOUT_SECONDS",
        "drop CI guard timeout handling": "learning CI entrypoint lost executable guard invocation: except subprocess.TimeoutExpired:",
        "drop anti-regression lesson": "learning authority lost invariant: Repeating a known failed approach",
        "downgrade schema version": "unsupported schemaVersion",
        "reorder closed-loop execution": "closed-loop execution order changed",
        "comment-only learning guard call": "learning CI entrypoint main must directly invoke bound learning guards",
        "quoted learning guard call": "learning CI entrypoint main must directly invoke bound learning guards",
        "dead-branch learning guard call": "learning CI entrypoint main must directly invoke bound learning guards",
        "dead module main guard": "learning CI entrypoint must execute main from its live module guard",
        "comment-only module main invocation": "learning CI entrypoint must execute main from its live module guard",
    }
    if name in fixed:
        return fixed[name]
    if name.startswith("disable mandatory "):
        return "mandatory learning rule must remain true: " + name.removeprefix("disable mandatory ")
    if name.startswith("drop required failure "):
        return "requiredFailureFields changed:"
    if name.startswith("drop required success "):
        return "requiredSuccessFields changed:"
    if name.startswith("symlinked ") and name.endswith(" parent directory"):
        return "learning authority path substituted through parent:"
    if name.startswith("symlinked ") and name.endswith(" authority"):
        return "symlinked learning authority forbidden:"
    raise RuntimeError(f"negative case lacks an expected canonical diagnostic: {name}")


def require_expected_rejection(name: str, result: subprocess.CompletedProcess[str]) -> None:
    require_canonical_rejection(name, result)
    expected = "AUTONOMOUS LEARNING VALIDATION FAILED: " + expected_diagnostic(name)
    if expected not in result.stderr:
        raise RuntimeError(
            f"negative case rejected for the wrong reason: {name}: "
            f"expected {expected!r}; observed {result.stderr!r}"
        )


def require_failure(source_root: Path, name: str, mutate) -> None:
    with tempfile.TemporaryDirectory(prefix="learning-negative-") as tmp:
        root = Path(tmp)
        seed(source_root, root)
        mutate(root)
        result = run(source_root, root)
        require_expected_rejection(name, result)


def edit_contract(root: Path, edit) -> None:
    path = root / CONTRACT
    data = json.loads(path.read_text(encoding="utf-8"))
    edit(data)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def drop_from_entrypoint(root: Path, phrase: str) -> None:
    path = root / CI_ENTRYPOINT
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace(f'    "{phrase}",\n', ""), encoding="utf-8")


def replace_in_entrypoint(root: Path, old: str, new: str) -> None:
    path = root / CI_ENTRYPOINT
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"negative fixture missing expected CI fragment: {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def symlink_authority(root: Path, relative: Path) -> None:
    # The alias and target stay inside this disposable fixture; canonical
    # checked-out authorities are never modified by the negative.
    path = root / relative
    target = path.with_name(path.name + ".fixture-target")
    path.rename(target)
    path.symlink_to(target.name)


def symlink_parent_directory(root: Path, relative: Path) -> None:
    # The substituted parent still points only inside the disposable fixture.
    # A canonical leaf is not a canonical path if any parent is an alias.
    directory = root / relative
    target = directory.with_name(directory.name + ".fixture-target")
    directory.rename(target)
    directory.symlink_to(target.name, target_is_directory=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    source_root = args.repo_root.resolve()

    prove_failure_classifier()

    with tempfile.TemporaryDirectory(prefix="learning-positive-") as tmp:
        root = Path(tmp)
        seed(source_root, root)
        result = run(source_root, root)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            return 1

    cases = [
        ("weaken mandatory rule", lambda root: edit_contract(root, lambda d: d["rules"].__setitem__("unchangedBlockerIsNotRetried", False))),
        ("disable required CI reachability", lambda root: edit_contract(root, lambda d: d["rules"].__setitem__("ciReachabilityRequired", False))),
        ("weaken NO_GO default", lambda root: edit_contract(root, lambda d: d["protectedInvariants"].__setitem__("productionDecisionDefault", "GO"))),
        ("allow non-real OPS-P0-007 evidence", lambda root: edit_contract(root, lambda d: d["protectedInvariants"].__setitem__("opsP0007EvidenceMustBeReal", False))),
        ("merge human promotion review into automation", lambda root: edit_contract(root, lambda d: d["protectedInvariants"].__setitem__("humanPromotionReviewIsSeparate", False))),
        ("drop required failure retry condition", lambda root: edit_contract(root, lambda d: d["requiredFailureFields"].remove("retryCondition"))),
        ("drop required success authority check", lambda root: edit_contract(root, lambda d: d["requiredSuccessFields"].remove("protectedAuthorityCheck"))),
        ("break executable guard binding", lambda root: edit_contract(root, lambda d: d.__setitem__("validator", "scripts/other.py"))),
        ("break negative guard binding", lambda root: edit_contract(root, lambda d: d.__setitem__("negativeValidator", "scripts/other-negative.py"))),
        ("break CI entrypoint binding", lambda root: edit_contract(root, lambda d: d.__setitem__("ciEntrypoint", "scripts/other-entrypoint.py"))),
        ("break learning authority binding", lambda root: edit_contract(root, lambda d: d.__setitem__("authority", "docs/operations/other-learning.md"))),
        ("duplicate required failure field", lambda root: edit_contract(root, lambda d: d["requiredFailureFields"].append("symptom"))),
        ("duplicate required success field", lambda root: edit_contract(root, lambda d: d["requiredSuccessFields"].append("outcome"))),
        ("remove learning authority", lambda root: (root / LEARNING).unlink()),
        ("remove executable guard", lambda root: (root / VALIDATOR).unlink()),
        ("remove negative guard", lambda root: (root / NEGATIVE_VALIDATOR).unlink()),
        ("remove CI entrypoint", lambda root: (root / CI_ENTRYPOINT).unlink()),
        ("disconnect positive guard from CI entrypoint", lambda root: drop_from_entrypoint(root, VALIDATOR.as_posix())),
        ("disconnect negative guard from CI entrypoint", lambda root: drop_from_entrypoint(root, NEGATIVE_VALIDATOR.as_posix())),
        ("remove CI guard execution call", lambda root: replace_in_entrypoint(root, "    validate_learning_guards(failures)\n", "    # learning guard execution removed\n")),
        ("drop CI repo-root guard interface", lambda root: replace_in_entrypoint(root, '[sys.executable, str(path), "--repo-root", str(REPO_ROOT)]', '[sys.executable, str(path)]')),
        ("drop CI guard timeout authority", lambda root: replace_in_entrypoint(root, "LEARNING_GUARD_TIMEOUT_SECONDS = 120", "LEARNING_GUARD_TIMEOUT_SECONDS = None")),
        ("drop CI guard timeout binding", lambda root: replace_in_entrypoint(root, "                timeout=LEARNING_GUARD_TIMEOUT_SECONDS,\n", "")),
        ("drop CI guard timeout handling", lambda root: replace_in_entrypoint(root, "        except subprocess.TimeoutExpired:\n", "        except RuntimeError:\n")),
        ("drop anti-regression lesson", lambda root: (root / LEARNING).write_text((root / LEARNING).read_text(encoding="utf-8").replace("Repeating a known failed approach without changed preconditions is a regression", "known failures may be retried"), encoding="utf-8")),
    ]
    # Exercise every mandatory contract rule independently. A positive
    # validator check without its own mutation proof is not negative coverage.
    for rule in (
        "searchBeforeChange",
        "sameFailedApproachRequiresChangedPrecondition",
        "preferExecutableGuard",
        "verifyProtectedAuthorityAfterChange",
        "scopedBlockerDoesNotStopIndependentWork",
        "historyIsAppendOnly",
        "learningIsNeverProductionEvidence",
        "learningCannotPromoteReadiness",
    ):
        cases.append((
            f"disable mandatory {rule}",
            lambda root, key=rule: edit_contract(
                root, lambda data: data["rules"].__setitem__(key, False)
            ),
        ))
    cases.extend((
        ("downgrade schema version", lambda root: edit_contract(
            root, lambda data: data.__setitem__("schemaVersion", "autonomous-learning-system.0.0")
        )),
        ("reorder closed-loop execution", lambda root: edit_contract(
            root, lambda data: data["loop"].reverse()
        )),
    ))
    # Field completeness is contractual: each required failure/success field
    # must have its own isolated missing-field negative, not just one example.
    for field in (
        "symptom", "evidence", "rootCauseOrUnknown",
        "failedApproach", "correction", "recurrenceGuard",
    ):
        cases.append((
            f"drop required failure {field}",
            lambda root, key=field: edit_contract(
                root, lambda data: data["requiredFailureFields"].remove(key)
            ),
        ))
    for field in ("outcome", "evidence", "whySafe", "reusableMechanism"):
        cases.append((
            f"drop required success {field}",
            lambda root, key=field: edit_contract(
                root, lambda data: data["requiredSuccessFields"].remove(key)
            ),
        ))
    # A textual invocation fragment in a comment, literal, or dead branch
    # must not satisfy the live CI call-site binding.
    cases.extend((
        ("comment-only learning guard call", lambda root: replace_in_entrypoint(
            root, "    validate_learning_guards(failures)\n",
            "    # validate_learning_guards(failures)\n",
        )),
        ("quoted learning guard call", lambda root: replace_in_entrypoint(
            root, "    validate_learning_guards(failures)\n",
            '    "validate_learning_guards(failures)"\n',
        )),
        ("dead-branch learning guard call", lambda root: replace_in_entrypoint(
            root, "    validate_learning_guards(failures)\n",
            "    if False:\n        validate_learning_guards(failures)\n",
        )),
    ))
    cases.extend((
        ("dead module main guard", lambda root: replace_in_entrypoint(
            root, 'if __name__ == "__main__":\n    raise SystemExit(main())\n',
            "if False:\n    raise SystemExit(main())\n",
        )),
        ("comment-only module main invocation", lambda root: replace_in_entrypoint(
            root, 'if __name__ == "__main__":\n    raise SystemExit(main())\n',
            'if __name__ == "__main__":\n    pass  # raise SystemExit(main())\n',
        )),
    ))
    for label, relative in (
        ("contract", CONTRACT),
        ("learning history", LEARNING),
        ("positive guard", VALIDATOR),
        ("negative guard", NEGATIVE_VALIDATOR),
        ("CI entrypoint", CI_ENTRYPOINT),
    ):
        cases.append((
            f"symlinked {label} authority",
            lambda root, path=relative: symlink_authority(root, path),
        ))
    for label, relative in (
        ("scripts", Path("scripts")),
        ("contracts operations", Path("contracts/operations")),
        ("docs operations", Path("docs/operations")),
    ):
        cases.append((
            f"symlinked {label} parent directory",
            lambda root, path=relative: symlink_parent_directory(root, path),
        ))
    for name, mutate in cases:
        require_failure(source_root, name, mutate)

    print(f"Autonomous learning negative validation PASS ({len(cases)} fail-closed cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
