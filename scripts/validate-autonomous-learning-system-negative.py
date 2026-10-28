#!/usr/bin/env python3
"""Negative suite proving the autonomous learning guard fails closed."""

from __future__ import annotations

import argparse
import hashlib
import stat
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


def fixture_state(root: Path) -> tuple[tuple[str, ...], ...]:
    """Fingerprint canonical fixture bytes, modes, and every path component."""
    observed: dict[str, tuple[str, ...]] = {}
    for relative in (CONTRACT, LEARNING, VALIDATOR, NEGATIVE_VALIDATOR, CI_ENTRYPOINT):
        path = root
        for part in relative.parts:
            path = path / part
            key = path.relative_to(root).as_posix()
            if key in observed:
                continue
            if path.is_symlink():
                observed[key] = ("symlink", str(path.readlink()))
            elif path.is_file():
                observed[key] = (
                    "file", hashlib.sha256(path.read_bytes()).hexdigest(),
                    str(stat.S_IMODE(path.stat().st_mode)),
                )
            elif path.is_dir():
                observed[key] = ("directory", str(stat.S_IMODE(path.stat().st_mode)))
            else:
                observed[key] = ("missing",)
    return tuple(sorted((key, *value) for key, value in observed.items()))


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
        "drop CI repo-root guard interface": 'learning CI entrypoint lost executable guard invocation: [sys.executable, str(path), "--repo-root", str(REPO_ROOT)]',
        "drop CI guard timeout authority": "learning CI entrypoint lost executable guard invocation: LEARNING_GUARD_TIMEOUT_SECONDS = 120",
        "drop CI guard timeout binding": "learning CI entrypoint lost executable guard invocation: timeout=LEARNING_GUARD_TIMEOUT_SECONDS",
        "remove source-negative CI guard call": "source-negative CI guard must be called directly from main",
        "quote source-negative CI guard call": "source-negative CI guard must be called directly from main",
        "shadow source-negative CI guard": "source-negative CI guard binding changed",
        "remove source-negative CI negative proof": "source-negative CI guard lost executable negative proof",
        "unreachable source-negative CI guard call": "source-negative CI guard call is unreachable",
        "drop CI guard timeout handling": "learning CI entrypoint lost executable guard invocation: except subprocess.TimeoutExpired:",
        "drop anti-regression lesson": "learning authority lost invariant: Repeating a known failed approach without changed preconditions is a regression",
        "invalid contract JSON": "invalid JSON:",
        "non-object contract root": "root must be an object:",
        "downgrade schema version": "unsupported schemaVersion",
        "reorder closed-loop execution": "closed-loop execution order changed",
        "comment-only learning guard call": "learning CI entrypoint main must directly invoke bound learning guards",
        "quoted learning guard call": "learning CI entrypoint main must directly invoke bound learning guards",
        "dead-branch learning guard call": "learning CI entrypoint main must directly invoke bound learning guards",
        "unreachable learning guard after return": "learning CI entrypoint guard call follows unconditional return or raise",
        "unreachable learning guard after raise": "learning CI entrypoint guard call follows unconditional return or raise",
        "async-only learning guard": "learning CI entrypoint must define one synchronous learning guard",
        "async learning guard shadow": "learning CI entrypoint learning guard binding is shadowed by async definition",
        "assigned learning guard shadow": "learning CI entrypoint learning guard binding is shadowed by assignment",
        "destructured learning guard shadow": "learning CI entrypoint learning guard binding is shadowed by assignment",
        "imported learning guard shadow": "learning CI entrypoint learning guard binding is shadowed by import",
        "async main shadow": "learning CI entrypoint main binding is shadowed by async definition",
        "assigned main shadow": "learning CI entrypoint main binding is shadowed by assignment",
        "destructured main shadow": "learning CI entrypoint main binding is shadowed by assignment",
        "imported main shadow": "learning CI entrypoint main binding is shadowed by import",
        "loop main shadow": "learning CI entrypoint main binding is shadowed by module control flow",
        "loop learning guard shadow": "learning CI entrypoint learning guard binding is shadowed by module control flow",
        "nested imported learning guard shadow": "learning CI entrypoint learning guard binding is shadowed by module control flow",
        "dead module main guard": "learning CI entrypoint must execute main from its live module guard",
        "comment-only module main invocation": "learning CI entrypoint must execute main from its live module guard",
    }
    if name in fixed:
        return fixed[name]
    if name.startswith("module early "):
        return "learning CI entrypoint module terminates before live main guard"
    if name.startswith("early learning guard "):
        return "learning CI entrypoint guard call follows unconditional return or raise"
    if name.startswith("dynamic main "):
        return "learning CI entrypoint main binding is shadowed by module control flow"
    if name.startswith("dynamic learning guard "):
        return "learning CI entrypoint learning guard binding is shadowed by module control flow"
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
    # A case's diagnostic must be the single canonical failure line, not
    # an expected substring hidden after an unrelated error or traceback.
    observed = result.stderr.removesuffix("\n")
    # Variable canonical diagnostics end with a colon and must include a detail.
    # Every other diagnostic is an exact authority string: a matching prefix
    # with an unrelated same-line suffix is not proof of the intended guard.
    variable_detail = (name in {"invalid contract JSON", "non-object contract root"}
                       or name.startswith(("drop required failure ", "drop required success ",
                                           "symlinked ")))
    matched = (observed.startswith(expected + " ") and len(observed) > len(expected) + 1
               if variable_detail else observed == expected)
    if "\n" in observed or "\r" in observed or not matched:
        raise RuntimeError(
            f"negative case rejected for the wrong reason: {name}: "
            f"expected {expected!r}; observed {result.stderr!r}"
        )


def require_failure(source_root: Path, name: str, mutate) -> None:
    with tempfile.TemporaryDirectory(prefix="learning-negative-") as tmp:
        root = Path(tmp)
        seed(source_root, root)
        before = fixture_state(root)
        mutate(root)
        if fixture_state(root) == before:
            raise RuntimeError(f"negative fixture did not mutate canonical authority: {name}")
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

    # A negative must reject for its own intended invariant, not merely for
    # an unrelated canonical failure elsewhere in the fixture.
    wrong_reason = subprocess.CompletedProcess(
        [], 1, "",
        "AUTONOMOUS LEARNING VALIDATION FAILED: unrelated injected failure\n",
    )
    try:
        require_expected_rejection("weaken mandatory rule", wrong_reason)
    except RuntimeError:
        pass
    else:
        raise RuntimeError("negative diagnostic classifier accepted an unrelated rejection")
    # The intended diagnostic on a second line (or accompanied by a second
    # error) must not be mistaken for a case-specific rejection.
    intended = "AUTONOMOUS LEARNING VALIDATION FAILED: " + expected_diagnostic("weaken mandatory rule")
    for index, stderr in enumerate((
        "AUTONOMOUS LEARNING VALIDATION FAILED: unrelated failure\n" + intended + "\n",
        intended + "\nunrelated additional failure\n",
    )):
        try:
            require_expected_rejection(
                "weaken mandatory rule", subprocess.CompletedProcess([], 1, "", stderr)
            )
        except RuntimeError:
            pass
        else:
            raise RuntimeError(f"negative diagnostic classifier accepted multiple errors: {index}")

    # A same-line suffix previously passed startswith(expected), making a
    # different diagnostic look like proof of the intended negative boundary.
    for label, name, suffix in (
        ("same-line suffix", "weaken mandatory rule", " injected"),
        ("same-line prefix collision", "weaken mandatory rule", "Extra"),
        ("anti-regression prefix collision", "drop anti-regression lesson", " changed"),
        ("fixed-colon diagnostic suffix", "drop CI guard timeout handling", " injected"),
    ):
        forged = "AUTONOMOUS LEARNING VALIDATION FAILED: " + expected_diagnostic(name) + suffix + "\n"
        try:
            require_expected_rejection(name, subprocess.CompletedProcess([], 1, "", forged))
        except RuntimeError:
            pass
        else:
            raise RuntimeError(f"negative diagnostic classifier accepted {label}")

    # A fixed diagnostic may itself end with a colon; it must still match exactly.
    require_expected_rejection(
        "drop CI guard timeout handling",
        subprocess.CompletedProcess([], 1, "",
            "AUTONOMOUS LEARNING VALIDATION FAILED: "
            + expected_diagnostic("drop CI guard timeout handling") + "\n"),
    )

    # Canonical variable-detail diagnostics still require a nonempty detail.
    require_expected_rejection(
        "invalid contract JSON",
        subprocess.CompletedProcess([], 1, "",
            "AUTONOMOUS LEARNING VALIDATION FAILED: invalid JSON: fixture: malformed JSON\n"),
    )
    for malformed in ("", " "):
        try:
            require_expected_rejection(
                "invalid contract JSON",
                subprocess.CompletedProcess([], 1, "",
                    "AUTONOMOUS LEARNING VALIDATION FAILED: invalid JSON:" + malformed + "\n"),
            )
        except RuntimeError:
            pass
        else:
            raise RuntimeError("negative diagnostic classifier accepted empty variable detail")

    require_expected_rejection(
        "weaken mandatory rule",
        subprocess.CompletedProcess(
            [], 1, "",
            "AUTONOMOUS LEARNING VALIDATION FAILED: "
            "mandatory learning rule must remain true: unchangedBlockerIsNotRetried\n",
        ),
    )

    with tempfile.TemporaryDirectory(prefix="learning-positive-") as tmp:
        root = Path(tmp)
        seed(source_root, root)
        result = run(source_root, root)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            return 1

    # Generator bodies are deferred and comprehension targets are local.
    # Prove the eager-effects guard does not reject these safe controls.
    for label, snippet in (
        ("deferred generator body", "(globals().__setitem__('main', None) for _ in (0,))\n"),
        ("comprehension-local target", "[0 for main in (0,)]\n"),
        ("deferred lambda body", "(lambda: globals().__setitem__('main', None))\n"),
    ):
        with tempfile.TemporaryDirectory(prefix="learning-comprehension-positive-") as tmp:
            root = Path(tmp)
            seed(source_root, root)
            module_guard = 'if __name__ == "__main__":' + chr(10) + "    raise SystemExit(main())" + chr(10)
            replace_in_entrypoint(root, module_guard, snippet + module_guard)
            result = run(source_root, root)
            if result.returncode != 0:
                raise RuntimeError(
                    f"learning eager-expression positive control rejected {label}: {result.stderr}"
                )

    # A no-op mutation must be rejected before running the canonical guard;
    # otherwise a broken positive fixture could masquerade as negative proof.
    try:
        require_failure(source_root, "weaken mandatory rule", lambda root: None)
    except RuntimeError as exc:
        if "negative fixture did not mutate canonical authority" not in str(exc):
            raise
    else:
        raise RuntimeError("negative mutation fingerprint accepted a no-op")

    cases = [
        ("invalid contract JSON", lambda root: (root / CONTRACT).write_text("{", encoding="utf-8")),
        ("non-object contract root", lambda root: (root / CONTRACT).write_text("[]", encoding="utf-8")),
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
        ("remove source-negative CI guard call", lambda root: replace_in_entrypoint(
            root, "    validate_source_negative_ci_reachability(failures)\n",
            "    # source-negative CI guard removed\n",
        )),
        ("quote source-negative CI guard call", lambda root: replace_in_entrypoint(
            root, "    validate_source_negative_ci_reachability(failures)\n",
            '    "validate_source_negative_ci_reachability(failures)"\n',
        )),
        ("shadow source-negative CI guard", lambda root: replace_in_entrypoint(
            root, "def main() -> int:\n",
            "validate_source_negative_ci_reachability = lambda failures: None\n\ndef main() -> int:\n",
        )),
        ("remove source-negative CI negative proof", lambda root: replace_in_entrypoint(
            root, "    prove_source_negative_reachability_negatives(failures)\n",
            "    pass\n",
        )),
        ("unreachable source-negative CI guard call", lambda root: replace_in_entrypoint(
            root, "    validate_source_negative_ci_reachability(failures)\n",
            "    return 0\n    validate_source_negative_ci_reachability(failures)\n",
        )),
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
        ("unreachable learning guard after return", lambda root: replace_in_entrypoint(
            root, "    validate_learning_guards(failures)\n",
            "    return 0\n    validate_learning_guards(failures)\n",
        )),
        ("unreachable learning guard after raise", lambda root: replace_in_entrypoint(
            root, "    validate_learning_guards(failures)\n",
            "    raise RuntimeError('unreachable')\n    validate_learning_guards(failures)\n",
        )),
    ))
    cases.extend((
        ("async-only learning guard", lambda root: replace_in_entrypoint(
            root, "def validate_learning_guards(failures: list[str]) -> None:",
            "async def validate_learning_guards(failures: list[str]) -> None:",
        )),
        ("async learning guard shadow", lambda root: replace_in_entrypoint(
            root, "def main() -> int:\n",
            "async def validate_learning_guards(failures):\n    return None\n\ndef main() -> int:\n",
        )),
        ("destructured learning guard shadow", lambda root: replace_in_entrypoint(
            root, "def main() -> int:\n",
            "validate_learning_guards, = (lambda failures: None,)\n\ndef main() -> int:\n",
        )),
        ("imported learning guard shadow", lambda root: replace_in_entrypoint(
            root, "def main() -> int:\n",
            "from unittest.mock import Mock as validate_learning_guards\n\ndef main() -> int:\n",
        )),
        ("assigned learning guard shadow", lambda root: replace_in_entrypoint(
            root, "def main() -> int:\n",
            "validate_learning_guards = lambda failures: None\n\ndef main() -> int:\n",
        )),
        ("async main shadow", lambda root: replace_in_entrypoint(
            root, 'if __name__ == "__main__":\n    raise SystemExit(main())\n',
            'async def main():\n    return 0\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n',
        )),
        ("loop main shadow", lambda root: replace_in_entrypoint(
            root, 'if __name__ == "__main__":\n    raise SystemExit(main())\n',
            'for main in (lambda: 0,):\n    pass\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n',
        )),
        ("loop learning guard shadow", lambda root: replace_in_entrypoint(
            root, "def main() -> int:\n",
            "for validate_learning_guards in (lambda failures: None,):\n    pass\n\ndef main() -> int:\n",
        )),
        ("nested imported learning guard shadow", lambda root: replace_in_entrypoint(
            root, "def main() -> int:\n",
            "if True:\n    from unittest.mock import Mock as validate_learning_guards\n\ndef main() -> int:\n",
        )),
        ("destructured main shadow", lambda root: replace_in_entrypoint(
            root, 'if __name__ == "__main__":\n    raise SystemExit(main())\n',
            'main, = (lambda: 0,)\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n',
        )),
        ("imported main shadow", lambda root: replace_in_entrypoint(
            root, 'if __name__ == "__main__":\n    raise SystemExit(main())\n',
            'from unittest.mock import Mock as main\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n',
        )),
        ("assigned main shadow", lambda root: replace_in_entrypoint(
            root, 'if __name__ == "__main__":\n    raise SystemExit(main())\n',
            'main = lambda: 0\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n',
        )),
        ("dead module main guard", lambda root: replace_in_entrypoint(
            root, 'if __name__ == "__main__":\n    raise SystemExit(main())\n',
            "if False:\n    raise SystemExit(main())\n",
        )),
        ("comment-only module main invocation", lambda root: replace_in_entrypoint(
            root, 'if __name__ == "__main__":\n    raise SystemExit(main())\n',
            'if __name__ == "__main__":\n    pass  # raise SystemExit(main())\n',
        )),
    ))
    # A canonical module guard is not execution proof if module startup
    # terminates before the guarded main() call. Every mutation retains the
    # canonical guard text and AST so only reachability can reject it.
    module_guard = 'if __name__ == "__main__":' + chr(10) + "    raise SystemExit(main())" + chr(10)
    for label, prefix in (
        ("sys-exit", "sys.exit(0)" + chr(10) + chr(10)),
        ("raise", "raise SystemExit(0)" + chr(10) + chr(10)),
        ("nested-sys-exit", "if True:" + chr(10) + "    sys.exit(0)" + chr(10) + chr(10)),
        ("eager-default", "def eager(value=sys.exit(0)):" + chr(10)
         + "    pass" + chr(10) + chr(10)),
    ):
        cases.append((
            f"module early {label}",
            lambda root, injected=prefix: replace_in_entrypoint(
                root, module_guard, injected + module_guard
            ),
        ))
    # The guard must remain reachable through nested branches, eager
    # definitions and termination calls, not just direct Return/Raise nodes.
    newline = chr(10)
    guard_call = "    validate_learning_guards(failures)" + newline
    for label, prefix in (
        ("if-return", "    if True:" + newline + "        return 0" + newline),
        ("if-raise", "    if True:" + newline + "        raise SystemExit(0)" + newline),
        ("sys-exit", "    sys.exit(0)" + newline),
        ("os-exit", "    os._exit(0)" + newline),
        ("exit", "    exit(0)" + newline),
        ("quit", "    quit()" + newline),
        ("dead-return", "    if False:" + newline + "        return 0" + newline),
        ("try-return", "    try:" + newline + "        return 0" + newline
         + "    finally:" + newline + "        pass" + newline),
        ("exec-exit", "    exec('sys.exit(0)')" + newline),
        ("eager-default", "    def helper(value=exit(0)):" + newline
         + "        pass" + newline),
        ("eager-class", "    class Early:" + newline + "        sys.exit(0)" + newline),
    ):
        cases.append((
            f"early learning guard {label}",
            lambda root, injected=prefix, before=guard_call: replace_in_entrypoint(
                root, before, injected + before
            ),
        ))
    # Dynamic module namespace mutation must not replace a verified guard
    # after the AST sees its original function definition.
    for label, symbol, anchor in (
        ("main", "main",
         'if __name__ == "__main__":' + chr(10) + "    raise SystemExit(main())" + chr(10)),
        ("learning guard", "validate_learning_guards", "def main() -> int:" + chr(10)),
    ):
        for kind, mutation in (
            ("globals-subscript", f"globals()['{symbol}'] = None"),
            ("globals-keyword", f"globals().update({symbol}=None)"),
            ("globals-dict", f"globals().update({{'{symbol}': None}})"),
            ("setattr", f"setattr(sys.modules[__name__], '{symbol}', None)"),
            ("exec", f"exec('{symbol} = None')"),
            # Class bodies, function defaults and decorators execute eagerly.
            # Their module-namespace side effects must not bypass a live call.
            ("class-body", f"class Eager:\n    globals()['{symbol}'] = None"),
            ("class-global", f"class Eager:\n    global {symbol}\n    {symbol} = None"),
            ("function-default", f"def eager(value=globals().__setitem__('{symbol}', None)):\n    pass"),
            ("function-decorator", f"@lambda fn: (globals().__setitem__('{symbol}', None), fn)[1]\ndef eager():\n    pass"),
            ("class-base", f"class Eager(globals().__setitem__('{symbol}', None) or object):\n    pass"),
            ("class-decorator", f"@lambda cls: (globals().__setitem__('{symbol}', None), cls)[1]\nclass Eager:\n    pass"),
            # Eager comprehension effects and the first generator iterable
            # run before the canonical main() dispatch.
            ("list-comprehension", f"[globals().__setitem__('{symbol}', None) for _ in (0,)]"),
            ("set-comprehension", f"{{globals().__setitem__('{symbol}', None) for _ in (0,)}}"),
            ("dict-comprehension", f"{{_: globals().__setitem__('{symbol}', None) for _ in (0,)}}"),
            ("generator-iterable", f"(None for _ in (globals().__setitem__('{symbol}', None) or (0,)))"),
            ("immediate-lambda", f"(lambda: globals().__setitem__('{symbol}', None))()"),
            ("lambda-in-comprehension", f"[(lambda: globals().__setitem__('{symbol}', None))() for _ in (0,)]"),
        ):
            cases.append((
                f"dynamic {label} {kind}",
                lambda root, before=anchor, injected=mutation: replace_in_entrypoint(
                    root, before, injected + chr(10) + before
                ),
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
