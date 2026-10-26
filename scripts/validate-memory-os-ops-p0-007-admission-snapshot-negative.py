#!/usr/bin/env python3
"""Prove OPS-P0-007 snapshot generation and validation reject corrupt authorities."""

from __future__ import annotations

import copy
from contextlib import contextmanager, redirect_stdout
from io import StringIO
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate-memory-os-ops-p0-007-admission-snapshot.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-ops-p0-007-admission-snapshot.py"
SNAPSHOT = ROOT / "contracts/operations/ops-p0-007-admission-snapshot.v1.json"
OBJECTIVES = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
REQUESTS = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
GENERATION = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
TYPED = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
OBJECTIVE_WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"
LOCAL_APPLE_VALIDATOR = ROOT / "scripts/validate-memory-os-local-apple-replay-restore.py"


class Fail(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Fail(f"expected object: {path.relative_to(ROOT)}")
    return value


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


@contextmanager
def temporary_mode(path: Path, temporary: int):
    original = mode(path)
    try:
        path.chmod(temporary)
        yield
    finally:
        path.chmod(original)


def require_material_mutation(before: dict[str, Any], after: dict[str, Any], label: str) -> None:
    # Python equality equates False/0 and True/1; JSON preserves those types.
    if json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True):
        raise Fail(f"{label}: negative fixture mutation was a no-op")


def load_generator_module():
    spec = importlib.util.spec_from_file_location("memory_os_ops_p0_007_snapshot_negative_generator", GENERATOR)
    if spec is None or spec.loader is None:
        raise Fail("cannot load strict snapshot generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_bounded_python(path: Path, label: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [sys.executable, str(path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=90,
        )
    except subprocess.TimeoutExpired as exc:
        raise Fail(f"{label}: canonical Python validation timed out after 90s") from exc


def prove_subprocess_timeout_guard() -> None:
    # An injected timeout must become a controlled failure, not a hang or a
    # generic interpreter traceback that masquerades as an admission rejection.
    with mock.patch.object(
        subprocess,
        "run",
        side_effect=subprocess.TimeoutExpired(cmd=["synthetic"], timeout=90),
    ):
        for path in (VALIDATOR, GENERATOR):
            try:
                run_bounded_python(path, "synthetic timeout")
            except Fail as exc:
                if str(exc) != "synthetic timeout: canonical Python validation timed out after 90s":
                    raise Fail(f"timeout rejected outside intended bounded subprocess guard: {exc}") from exc
            else:
                raise Fail("synthetic subprocess timeout unexpectedly accepted")


# Exact case binding prevents an unrelated canonical failure from satisfying
# the targeted snapshot/production-decision corruption negatives.
CASE_SPECIFIC_VALIDATOR_REJECTIONS = {
    "snapshot unknown production authority field": "snapshot field set drift",
    "snapshot missing production readiness field": "snapshot field set drift",
    "snapshot boolean registered generation count": "snapshot count invalid: registeredEnvironmentGenerationCount",
    "snapshot downstream requirement projection": "snapshot downstream requirement projection drift",
    "snapshot next action projection": "snapshot nextAction projection drift",
    "production decision promotion": "status production decision drift",
    "objective boolean aggregate count": "recovery objective canonical registry authority invalid: approvedObjectiveCount must be a non-boolean integer",
    "objective append-only boundary": "recovery objective canonical registry authority invalid: objectives registry must remain append-only",
    "objective schema boundary": "recovery objective canonical registry authority invalid: registry schema drift",
    "objective production evidence boundary": "recovery objective canonical registry authority invalid: objectives registry productionEvidence must remain false",
    "objective production readiness boundary": "recovery objective canonical registry authority invalid: objectives registry productionReady must remain false",
    "drill boolean aggregate count": "restore drill request canonical registry authority invalid: registeredRequestCount must be a non-boolean integer",
    "drill append-only boundary": "restore drill request canonical registry authority invalid: request registry must remain append-only",
    "drill production evidence boundary": "restore drill request canonical registry authority invalid: request registry productionEvidence must remain false",
    "generation boolean aggregate count": "generation recovery evidence canonical registry authority invalid: registeredEvidenceCount drift",
    "generation append-only boundary": "generation recovery evidence canonical registry authority invalid: registry must remain append-only",
    "generation production readiness boundary": "generation recovery evidence canonical registry authority invalid: registry production boundary drift",
    "typed boolean aggregate count": "typed non-resurrection canonical registry authority invalid: completeRecordCount drift",
    "typed append-only boundary": "typed non-resurrection canonical registry authority invalid: registry must remain append-only",
    "typed production evidence boundary": "typed non-resurrection canonical registry authority invalid: registry production boundary drift",
    "canonical blocker replacement with unchanged count": "OPS-P0-007 missingEvidence must equal the ordered canonical six production blockers",
    "canonical blocker ordering drift": "OPS-P0-007 missingEvidence must equal the ordered canonical six production blockers",
    "objective source symlink escape": "strict snapshot validator recovery objectives authority path drift",
    "objective writer module symlink escape": "strict snapshot validator objective writer authority path drift",
}



def require_known_validator_case(label: str) -> str:
    try:
        return CASE_SPECIFIC_VALIDATOR_REJECTIONS[label]
    except KeyError as exc:
        raise Fail(f"{label}: missing case-specific canonical rejection binding") from exc


def require_negative_validator_stdout(stdout: str, label: str) -> None:
    if stdout.strip():
        raise Fail(f"{label}: canonical negative validator emitted unexpected stdout")


def require_case_specific_validator_rejection(stderr: str, expected: str, label: str) -> None:
    diagnostic = f"OPS-P0-007 ADMISSION SNAPSHOT FAILED: {expected}"
    if stderr.splitlines() != [diagnostic]:
        raise Fail(f"{label}: rejected outside intended canonical snapshot diagnostic: {stderr!r}")


def prove_case_specific_validator_classifier() -> None:
    for label in ("synthetic unmapped corruption", "clean baseline"):
        try:
            require_known_validator_case(label)
        except Fail as exc:
            if str(exc) != f"{label}: missing case-specific canonical rejection binding":
                raise Fail(f"unmapped classifier rejected outside intended guard: {exc}") from exc
        else:
            raise Fail(f"unmapped validator negative unexpectedly accepted: {label}")
    expected = "snapshot field set drift"
    diagnostic = f"OPS-P0-007 ADMISSION SNAPSHOT FAILED: {expected}"
    require_case_specific_validator_rejection(diagnostic + "\n", expected, "synthetic positive")
    require_negative_validator_stdout("", "synthetic clean negative")
    try:
        require_negative_validator_stdout(
            "Memory OS OPS-P0-007 strict admission snapshot validation PASS\n",
            "synthetic mixed positive/negative output",
        )
    except Fail as exc:
        if "canonical negative validator emitted unexpected stdout" not in str(exc):
            raise Fail(f"mixed-output classifier rejected outside intended guard: {exc}") from exc
    else:
        raise Fail("negative classifier accepted a simultaneous success marker")
    for stderr in (
        "OPS-P0-007 ADMISSION SNAPSHOT FAILED: unrelated failure\n",
        "OPS-P0-007 ADMISSION SNAPSHOT FAILED: unrelated failure\n" + diagnostic + "\n",
        diagnostic + "\nOPS-P0-007 ADMISSION SNAPSHOT FAILED: unrelated failure\n",
    ):
        try:
            require_case_specific_validator_rejection(stderr, expected, "synthetic wrong diagnostic")
        except Fail as exc:
            if "rejected outside intended canonical snapshot diagnostic" not in str(exc):
                raise Fail(f"classifier rejected outside intended diagnostic guard: {exc}") from exc
        else:
            raise Fail("snapshot classifier accepted unrelated or multiline rejection")


def require_positive_validator_output(stdout: str, label: str, stderr: str = "") -> None:
    # A zero exit with a hidden canonical error on stderr is not a clean
    # positive control, even if stdout contains the expected PASS markers.
    if stderr.strip():
        raise Fail(f"{label}: canonical positive validator emitted unexpected stderr")
    lines = stdout.splitlines()
    if (
        lines.count("Memory OS OPS-P0-007 strict admission snapshot validation PASS") != 1
        or lines.count("production decision: NO_GO") != 1
    ):
        raise Fail(f"{label}: canonical positive validator success output missing or duplicated")


def prove_positive_validator_classifier() -> None:
    valid = (
        "Memory OS OPS-P0-007 strict admission snapshot validation PASS\n"
        "production decision: NO_GO\n"
    )
    require_positive_validator_output(valid, "synthetic positive")
    try:
        require_positive_validator_output(
            valid, "synthetic stderr", "OPS-P0-007 ADMISSION SNAPSHOT FAILED: unrelated\n"
        )
    except Fail as exc:
        if "canonical positive validator emitted unexpected stderr" not in str(exc):
            raise Fail(f"positive stderr classifier rejected outside intended guard: {exc}") from exc
    else:
        raise Fail("positive classifier accepted canonical failure diagnostic on stderr")
    for stdout in (
        "",
        "generic success\nproduction decision: NO_GO\n",
        "Memory OS OPS-P0-007 strict admission snapshot validation PASS\nproduction decision: GO\n",
        valid + "Memory OS OPS-P0-007 strict admission snapshot validation PASS\n",
        valid + "production decision: NO_GO\n",
        "prefix Memory OS OPS-P0-007 strict admission snapshot validation PASS\nproduction decision: NO_GO\n",
    ):
        try:
            require_positive_validator_output(stdout, "synthetic invalid positive")
        except Fail as exc:
            if "canonical positive validator success output missing or duplicated" not in str(exc):
                raise Fail(f"positive classifier rejected outside intended guard: {exc}") from exc
        else:
            raise Fail("positive classifier accepted missing, unrelated or duplicate success output")


def run_validator(expect_success: bool, label: str) -> None:
    proc = run_bounded_python(VALIDATOR, label)
    if expect_success:
        if proc.returncode != 0:
            raise Fail(f"{label}: baseline validator failed: {proc.stderr or proc.stdout}")
        require_positive_validator_output(proc.stdout, label, proc.stderr)
        return
    if proc.returncode != 1:
        raise Fail(f"{label}: expected fail-closed exit 1, got {proc.returncode}: {proc.stderr or proc.stdout}")
    require_negative_validator_stdout(proc.stdout, label)
    if "OPS-P0-007 ADMISSION SNAPSHOT FAILED:" not in proc.stderr:
        raise Fail(f"{label}: rejection did not come from canonical fail-closed boundary: {proc.stderr or proc.stdout}")
    if "Traceback (most recent call last)" in proc.stderr:
        raise Fail(f"{label}: rejection surfaced an implementation exception instead of a controlled failure")
    expected = require_known_validator_case(label)
    require_case_specific_validator_rejection(proc.stderr, expected, label)


# The typed admission child transport now suppresses raw child stdout/stderr.
# Bind its fixed privacy-safe wrapper to a separate exact child rejection
# observed by this disposable negative harness, never to arbitrary failures.
NESTED_GENERATOR_REJECTIONS = {
    "generator canonical blocker replacement": "LOCAL APPLE REPLAY RESTORE VALIDATION FAILED: OPS-P0-007 missingEvidence must equal the ordered canonical six production blockers",
    "generator canonical blocker ordering drift": "LOCAL APPLE REPLAY RESTORE VALIDATION FAILED: OPS-P0-007 missingEvidence must equal the ordered canonical six production blockers",
    "generator production decision promotion": "LOCAL APPLE REPLAY RESTORE VALIDATION FAILED: local replay restore cannot change production decision",
}

REDACTED_TYPED_APPLE_REJECTION = (
    "typed non-resurrection canonical admission authority invalid: "
    "local Apple replay restore validator failed without exposing subprocess output"
)


def require_inner_apple_replay_diagnostic(proc: subprocess.CompletedProcess[str], label: str) -> None:
    expected = NESTED_GENERATOR_REJECTIONS.get(label)
    if expected is None:
        raise Fail(f"{label}: missing inner Apple replay diagnostic binding")
    if proc.returncode != 1 or proc.stdout != "" or proc.stderr != expected + "\n":
        # Never print captured child output; it is used only for exact private comparison.
        raise Fail(f"{label}: inner Apple replay rejection did not match intended mutation")


def require_inner_apple_replay_rejection(label: str) -> None:
    proc = run_bounded_python(LOCAL_APPLE_VALIDATOR, f"{label} inner Apple replay")
    require_inner_apple_replay_diagnostic(proc, label)



EXACT_GENERATOR_REJECTIONS = {
    "generator objective source symlink escape": "strict snapshot authority missing or escapes repository: recovery objective registry",
    "generator objective writer module symlink escape": "strict snapshot authority missing or escapes repository: recovery objective writer",
}



def require_known_generator_case(label: str) -> None:
    if label not in EXACT_GENERATOR_REJECTIONS and label not in NESTED_GENERATOR_REJECTIONS:
        raise Fail(f"{label}: missing exact generator corruption diagnostic binding")


def require_expected_generator_diagnostic(output: str, allowed: tuple[str, ...], label: str) -> None:
    lines = output.strip().splitlines()
    exact = EXACT_GENERATOR_REJECTIONS.get(label)
    if exact is not None:
        if lines != [exact]:
            raise Fail(f"{label}: generator rejection did not use one intended authority diagnostic: {output!r}")
        return
    prefixes = tuple(
        prefix
        for message in allowed
        for prefix in (message, f"generated strict snapshot invalid: {message}")
    )
    nested = NESTED_GENERATOR_REJECTIONS.get(label)
    # The public wrapper is intentionally generic and cannot alone prove the
    # mutation; run_generator_rejects separately checks the exact child cause.
    valid_single = nested is None and len(lines) == 1 and lines[0].startswith(prefixes)
    valid_nested = nested is not None and lines == [REDACTED_TYPED_APPLE_REJECTION]
    if not (valid_single or valid_nested):
        raise Fail(f"{label}: generator rejection did not use one intended authority diagnostic: {output!r}")


def capture_canonical_generator_preflight_stdout() -> str:
    """Observe the read-only canonical validators before any negative mutation."""
    output = StringIO()
    with redirect_stdout(output):
        load_generator_module().run_full_admission_validators()
    baseline = output.getvalue()
    for marker in (
        "Memory OS recovery objectives validation PASS",
        "Memory OS production-equivalent backup/restore drill request validation PASS",
        "Memory OS drill-bound generation backup/restore evidence validation PASS",
        "Memory OS backup/restore typed non-resurrection admission validation PASS",
    ):
        if baseline.splitlines().count(marker) != 1:
            raise Fail(f"canonical generator preflight positive control missing or duplicated: {marker}")
    if "Memory OS OPS-P0-007 strict admission snapshot generated" in baseline:
        raise Fail("canonical preflight baseline includes a generator publication marker")
    return baseline


def require_negative_generator_stdout(stdout: str, baseline: str, label: str) -> None:
    # The generator's four canonical admission validators legitimately print
    # positive diagnostics before a later authority rejects a mutation.
    # Accept only a complete-line prefix of the observed clean preflight,
    # never arbitrary output or the generator's own publication success.
    lines = stdout.splitlines()
    canonical = baseline.splitlines()
    if (
        (stdout and not stdout.endswith("\n"))
        or len(lines) > len(canonical)
        or lines != canonical[:len(lines)]
    ):
        raise Fail(f"{label}: canonical generator rejection emitted unexpected stdout")


def prove_generator_diagnostic_classifier() -> None:
    for label in ("synthetic unknown generator corruption", "synthetic positive"):
        try:
            require_known_generator_case(label)
        except Fail as exc:
            if str(exc) != f"{label}: missing exact generator corruption diagnostic binding":
                raise Fail(f"generator case classifier rejected outside intended guard: {exc}") from exc
        else:
            raise Fail(f"unmapped generator negative unexpectedly accepted: {label}")
    for label, expected in EXACT_GENERATOR_REJECTIONS.items():
        require_expected_generator_diagnostic(expected + chr(10), ("strict snapshot authority",), label)
        for wrong in (expected + " unrelated", expected + chr(10) + expected, "unrelated: " + expected):
            try:
                require_expected_generator_diagnostic(wrong, ("strict snapshot authority",), label)
            except Fail as exc:
                if "one intended authority diagnostic" not in str(exc):
                    raise Fail(f"exact generator classifier rejected outside intended guard: {exc}") from exc
            else:
                raise Fail("exact generator classifier accepted unrelated or duplicate diagnostic")
    expected = ("canonical OPS-P0-007 blocker authority invalid",)
    valid = "canonical OPS-P0-007 blocker authority invalid: synthetic detail"
    require_expected_generator_diagnostic(valid + "\n", expected, "synthetic positive")
    baseline = (
        "Memory OS recovery objectives validation PASS\n"
        "production decision: NO_GO\n"
        "Memory OS production-equivalent backup/restore drill request validation PASS\n"
    )
    require_negative_generator_stdout("", baseline, "synthetic clean generator rejection")
    require_negative_generator_stdout(
        "Memory OS recovery objectives validation PASS\n", baseline, "synthetic upstream prefix"
    )
    require_negative_generator_stdout(baseline, baseline, "synthetic full upstream prefix")
    for bad_stdout in (
        "Memory OS OPS-P0-007 strict admission snapshot generated\n",
        "Memory OS recovery objectives validation PASS\nunrelated success\n",
        "production decision: NO_GO\n",
        "Memory OS recovery objectives validation PASS",
        baseline + "Memory OS OPS-P0-007 strict admission snapshot generated\n",
    ):
        try:
            require_negative_generator_stdout(bad_stdout, baseline, "synthetic mixed generator output")
        except Fail as exc:
            if "canonical generator rejection emitted unexpected stdout" not in str(exc):
                raise Fail(f"mixed generator output rejected outside intended guard: {exc}") from exc
        else:
            raise Fail("generator rejection classifier accepted unrelated or publication stdout")
    nested_label = "generator canonical blocker replacement"
    require_expected_generator_diagnostic(
        REDACTED_TYPED_APPLE_REJECTION + "\n",
        ("typed non-resurrection canonical admission authority invalid",),
        nested_label,
    )
    # Generic redacted wrapper is allowed only when the actual mutated child
    # validator separately proves the exact intended corruption.
    for nested_case, expected_inner in NESTED_GENERATOR_REJECTIONS.items():
        good = subprocess.CompletedProcess(
            args=["synthetic"], returncode=1, stdout="", stderr=expected_inner + "\n"
        )
        require_inner_apple_replay_diagnostic(good, nested_case)
        require_expected_generator_diagnostic(
            REDACTED_TYPED_APPLE_REJECTION + "\n",
            ("typed non-resurrection canonical admission authority invalid",),
            nested_case,
        )
        for wrong in (
            subprocess.CompletedProcess(args=["synthetic"], returncode=0, stdout="", stderr=expected_inner + "\n"),
            subprocess.CompletedProcess(args=["synthetic"], returncode=1, stdout="unexpected", stderr=expected_inner + "\n"),
            subprocess.CompletedProcess(args=["synthetic"], returncode=1, stdout="", stderr=expected_inner + " unrelated\n"),
            subprocess.CompletedProcess(args=["synthetic"], returncode=1, stdout="", stderr="unrelated failure\n"),
        ):
            try:
                require_inner_apple_replay_diagnostic(wrong, nested_case)
            except Fail as exc:
                if "inner Apple replay rejection did not match intended mutation" not in str(exc):
                    raise Fail(f"{nested_case}: inner classifier rejected outside intended guard") from exc
            else:
                raise Fail(f"{nested_case}: accepted wrong inner Apple replay rejection")
        for wrong in (
            REDACTED_TYPED_APPLE_REJECTION + " unrelated\n",
            REDACTED_TYPED_APPLE_REJECTION + "\n" + expected_inner + "\n",
            "typed non-resurrection canonical admission authority invalid: unrelated child failure\n",
            REDACTED_TYPED_APPLE_REJECTION + "\n" + REDACTED_TYPED_APPLE_REJECTION + "\n",
        ):
            try:
                require_expected_generator_diagnostic(
                    wrong, ("typed non-resurrection canonical admission authority invalid",), nested_case
                )
            except Fail as exc:
                if "one intended authority diagnostic" not in str(exc):
                    raise Fail(f"{nested_case}: redacted wrapper rejected outside intended guard") from exc
            else:
                raise Fail(f"{nested_case}: accepted unrelated redacted wrapper")
    for output in (
        "unrelated failure: " + valid + "\n",
        "unrelated failure\n" + valid + "\n",
        valid + "\nunrelated failure\n",
        REDACTED_TYPED_APPLE_REJECTION + "\nunrelated failure\n",
        REDACTED_TYPED_APPLE_REJECTION + "\n" + NESTED_GENERATOR_REJECTIONS[nested_label] + "\nunrelated failure\n",
    ):
        try:
            require_expected_generator_diagnostic(output, expected, "synthetic unrelated diagnostic")
        except Fail as exc:
            if "one intended authority diagnostic" not in str(exc):
                raise Fail(f"generator classifier rejected outside intended guard: {exc}") from exc
        else:
            raise Fail("generator classifier accepted unrelated or multiline rejection")


def snapshot_state() -> tuple[bytes, int, bool]:
    return SNAPSHOT.read_bytes(), mode(SNAPSHOT), SNAPSHOT.is_symlink()


def require_snapshot_state_unchanged(
    before: tuple[bytes, int, bool], after: tuple[bytes, int, bool], label: str
) -> None:
    if before[0] != after[0]:
        raise Fail(f"{label}: rejected generator attempt mutated deterministic snapshot")
    if before[1] != after[1]:
        raise Fail(f"{label}: rejected generator attempt changed deterministic snapshot mode")
    if before[2] != after[2]:
        raise Fail(f"{label}: rejected generator attempt changed deterministic snapshot symlink status")


def prove_snapshot_state_classifier() -> None:
    original = (b"canonical snapshot", 0o644, False)
    require_snapshot_state_unchanged(original, original, "synthetic unchanged")
    for mutated, expected in (
        ((b"changed snapshot", 0o644, False), "mutated deterministic snapshot"),
        ((b"canonical snapshot", 0o600, False), "changed deterministic snapshot mode"),
        ((b"canonical snapshot", 0o644, True), "changed deterministic snapshot symlink status"),
    ):
        try:
            require_snapshot_state_unchanged(original, mutated, "synthetic drift")
        except Fail as exc:
            if expected not in str(exc):
                raise Fail(f"snapshot state classifier rejected outside intended guard: {exc}") from exc
        else:
            raise Fail("snapshot state classifier accepted synthetic bytes/mode drift")


def run_generator_rejects(label: str, expected_messages: str | tuple[str, ...], preflight_stdout: str) -> None:
    require_known_generator_case(label)
    before = snapshot_state()
    if label in NESTED_GENERATOR_REJECTIONS:
        require_inner_apple_replay_rejection(label)
    proc = run_bounded_python(GENERATOR, label)
    if proc.returncode != 1:
        raise Fail(f"{label}: expected generator fail-closed exit 1, got {proc.returncode}: {proc.stderr or proc.stdout}")
    require_negative_generator_stdout(proc.stdout, preflight_stdout, label)
    output = proc.stderr or proc.stdout
    allowed = (expected_messages,) if isinstance(expected_messages, str) else expected_messages
    require_expected_generator_diagnostic(output, allowed, label)
    if "Traceback (most recent call last)" in output:
        raise Fail(f"{label}: generator rejection surfaced an implementation exception")
    require_snapshot_state_unchanged(before, snapshot_state(), label)


def run_generator_post_write_validator_substitution_rejected() -> None:
    before = snapshot_state()
    module = load_generator_module()
    original_validator = module.validate_generated_snapshot

    def reject_after_write() -> None:
        raise RuntimeError("synthetic post-write snapshot validation failure")

    module.validate_generated_snapshot = reject_after_write
    try:
        try:
            module.main()
        except SystemExit as exc:
            if "strict snapshot generator execution helper drift" not in str(exc):
                raise Fail(f"post-write validator substitution rejected at unexpected boundary: {exc}") from exc
        else:
            raise Fail("post-write validator substitution unexpectedly bypassed execution authority")
    finally:
        module.validate_generated_snapshot = original_validator

    require_snapshot_state_unchanged(before, snapshot_state(), "post-write validator substitution")


def run_generator_full_admission_chain_required() -> None:
    before = snapshot_state()
    module = load_generator_module()
    original_validators = module.run_full_admission_validators

    def reject_full_admission() -> None:
        raise RuntimeError("synthetic full admission validation rejection")

    module.run_full_admission_validators = reject_full_admission
    try:
        try:
            module.main()
        except SystemExit as exc:
            if "strict snapshot generator execution helper drift" not in str(exc):
                raise Fail(f"full admission helper substitution rejected at unexpected boundary: {exc}") from exc
        else:
            raise Fail("strict snapshot generator accepted substituted full admission validator chain")
    finally:
        module.run_full_admission_validators = original_validators

    require_snapshot_state_unchanged(before, snapshot_state(), "full admission helper substitution")


def run_generator_atomic_write_mode_preservation() -> None:
    snapshot_before = snapshot_state()
    status_before = (STATUS.read_bytes(), mode(STATUS), STATUS.is_symlink())
    temporary_before = set(SNAPSHOT.parent.glob(f".{SNAPSHOT.name}.*.tmp"))
    module = load_generator_module()
    with temporary_mode(SNAPSHOT, 0o640):
        module.atomic_write_text(SNAPSHOT, snapshot_before[0].decode("utf-8"))
        if SNAPSHOT.read_bytes() != snapshot_before[0]:
            raise Fail("successful atomic strict snapshot rewrite changed canonical bytes")
        if mode(SNAPSHOT) != 0o640:
            raise Fail(f"successful atomic strict snapshot rewrite changed mode: {oct(mode(SNAPSHOT))}")
        if SNAPSHOT.is_symlink() != snapshot_before[2]:
            raise Fail("successful atomic strict snapshot rewrite changed symlink identity")
    require_snapshot_state_unchanged(snapshot_before, snapshot_state(), "successful atomic rewrite")
    if (STATUS.read_bytes(), mode(STATUS), STATUS.is_symlink()) != status_before:
        raise Fail("successful atomic strict snapshot rewrite changed canonical Production Status")
    temporary_after = set(SNAPSHOT.parent.glob(f".{SNAPSHOT.name}.*.tmp"))
    if temporary_after != temporary_before:
        raise Fail("successful atomic strict snapshot rewrite left or changed temporary authority files")


def prove_temporary_mode_cleanup() -> None:
    # Exception-path restoration is proven in an isolated fixture, not by
    # deliberately failing halfway through a canonical snapshot mutation.
    with tempfile.TemporaryDirectory(prefix="ops-p0-007-mode-cleanup-negative-") as tmp:
        fixture = Path(tmp) / "mode-fixture"
        fixture.write_text("unchanged", encoding="utf-8")
        fixture.chmod(0o600)
        try:
            with temporary_mode(fixture, 0o640):
                if mode(fixture) != 0o640:
                    raise Fail("temporary mode guard did not apply the requested mode")
                raise RuntimeError("synthetic interrupted negative")
        except RuntimeError as exc:
            if str(exc) != "synthetic interrupted negative":
                raise Fail(f"temporary mode cleanup test failed outside injected exception: {exc}") from exc
        else:
            raise Fail("temporary mode cleanup fixture did not raise")
        if mode(fixture) != 0o600 or fixture.read_text(encoding="utf-8") != "unchanged":
            raise Fail("temporary mode cleanup did not restore isolated fixture mode/bytes")


def require_atomic_replace_probe(calls: list[tuple[Path, Path]]) -> None:
    if len(calls) != 1:
        raise Fail(f"atomic replacement injection must reach exactly one replace call, got {len(calls)}")
    source, destination = calls[0]
    if (
        destination != SNAPSHOT
        or source.parent != SNAPSHOT.parent
        or not source.name.startswith(f".{SNAPSHOT.name}.")
        or not source.name.endswith(".tmp")
    ):
        raise Fail("atomic replacement injection did not reach canonical snapshot temporary-file target")


def prove_atomic_replace_probe_classifier() -> None:
    canonical_tmp = SNAPSHOT.parent / f".{SNAPSHOT.name}.synthetic.tmp"
    require_atomic_replace_probe([(canonical_tmp, SNAPSHOT)])
    for calls in (
        [],
        [(canonical_tmp, SNAPSHOT), (canonical_tmp, SNAPSHOT)],
        [(canonical_tmp, STATUS)],
        [(SNAPSHOT.parent / "unrelated.tmp", SNAPSHOT)],
    ):
        try:
            require_atomic_replace_probe(calls)
        except Fail as exc:
            if "atomic replacement injection" not in str(exc):
                raise Fail(f"atomic replacement probe rejected outside intended guard: {exc}") from exc
        else:
            raise Fail("atomic replacement probe accepted missing, duplicated or wrong-target call")


def run_generator_atomic_write_failure() -> None:
    snapshot_before = SNAPSHOT.read_bytes()
    status_before = STATUS.read_bytes()
    module = load_generator_module()
    original_replace = module.os.replace
    replace_calls: list[tuple[Path, Path]] = []

    def reject_replace(source: str | Path, destination: str | Path) -> None:
        replace_calls.append((Path(source), Path(destination)))
        raise OSError("synthetic strict snapshot atomic replace rejection")

    # Restore the canonical mode on *every* exit, including an unexpected
    # exception or a failed assertion before the ordinary cleanup checks.
    with temporary_mode(SNAPSHOT, 0o640):
        module.os.replace = reject_replace
        try:
            try:
                module.atomic_write_text(SNAPSHOT, snapshot_before.decode("utf-8") + " ")
            except SystemExit as exc:
                expected = (
                    "cannot atomically write contracts/operations/ops-p0-007-admission-snapshot.v1.json: "
                    "synthetic strict snapshot atomic replace rejection"
                )
                if str(exc) != expected:
                    raise Fail(f"atomic strict snapshot write rejected at wrong boundary: {exc}") from exc
            else:
                raise Fail("synthetic strict snapshot atomic replace failure unexpectedly accepted")
        finally:
            module.os.replace = original_replace

        require_atomic_replace_probe(replace_calls)
        if SNAPSHOT.read_bytes() != snapshot_before:
            raise Fail("atomic replace rejection mutated canonical strict snapshot")
        if mode(SNAPSHOT) != 0o640:
            raise Fail(f"atomic replace rejection changed canonical strict snapshot mode: {oct(mode(SNAPSHOT))}")

    if STATUS.read_bytes() != status_before:
        raise Fail("atomic replace rejection mutated canonical production status")
    leftovers = list(SNAPSHOT.parent.glob(f".{SNAPSHOT.name}.*.tmp"))
    if leftovers:
        raise Fail(f"atomic replace rejection left temporary strict snapshot authority files: {leftovers}")


def require_authority_substitution_diagnostic(code: object, label: str) -> None:
    expected = f"strict snapshot authority drift: {label}"
    if not isinstance(code, str) or code != expected:
        raise Fail(f"{label}: substitution rejected outside exact canonical authority path guard: {code!r}")


def prove_authority_substitution_classifier() -> None:
    label = "snapshot output"
    expected = f"strict snapshot authority drift: {label}"
    require_authority_substitution_diagnostic(expected, label)
    for wrong in (
        expected + " unrelated",
        "unrelated " + expected,
        "strict snapshot authority drift: recovery objective registry",
        1,
    ):
        try:
            require_authority_substitution_diagnostic(wrong, label)
        except Fail as exc:
            if "outside exact canonical authority path guard" not in str(exc):
                raise Fail(f"authority substitution classifier rejected outside intended guard: {exc}") from exc
        else:
            raise Fail("authority substitution classifier accepted unrelated or wrong-path rejection")


def run_generator_authority_substitution() -> None:
    before = snapshot_state()
    module = load_generator_module()
    substitutions = (
        ("OUTPUT", module.OBJECTIVES, "snapshot output"),
        ("ELIGIBILITY_HELPER", module.OBJECTIVE_WRITER, "environment generation eligibility helper"),
        ("BLOCKER_HELPER", module.OBJECTIVE_WRITER, "backup/restore blocker helper"),
        ("SNAPSHOT_VALIDATOR", module.OBJECTIVE_WRITER, "snapshot validator"),
        ("RECOVERY_OBJECTIVE_VALIDATOR", module.OBJECTIVE_WRITER, "recovery objective admission validator"),
        ("DRILL_REQUEST_VALIDATOR", module.OBJECTIVE_WRITER, "reviewed drill request admission validator"),
        ("GEN_EVIDENCE_VALIDATOR", module.OBJECTIVE_WRITER, "generation recovery evidence admission validator"),
        ("TYPED_VALIDATOR", module.OBJECTIVE_WRITER, "typed non-resurrection admission validator"),
        ("OBJECTIVES", module.DRILL_REQUESTS, "recovery objective registry"),
        ("DRILL_REQUESTS", module.OBJECTIVES, "restore drill request registry"),
        ("GEN_EVIDENCE", module.TYPED, "generation recovery evidence registry"),
        ("TYPED", module.GEN_EVIDENCE, "typed non-resurrection registry"),
        ("STATUS", module.OBJECTIVES, "production operability status"),
        ("OBJECTIVE_WRITER", module.DRILL_REQUEST_WRITER, "recovery objective writer"),
        ("DRILL_REQUEST_WRITER", module.OBJECTIVE_WRITER, "restore drill request writer"),
        ("GEN_EVIDENCE_WRITER", module.TYPED_WRITER, "generation recovery evidence writer"),
        ("TYPED_WRITER", module.GEN_EVIDENCE_WRITER, "typed non-resurrection writer"),
    )
    for field, substitute, label in substitutions:
        original = getattr(module, field)
        try:
            setattr(module, field, substitute)
            try:
                module.enforce_runtime_authorities()
            except SystemExit as exc:
                require_authority_substitution_diagnostic(exc.code, label)
            else:
                raise Fail(f"strict snapshot generator accepted {field} authority substitution")
        finally:
            setattr(module, field, original)
    module.enforce_runtime_authorities()
    require_snapshot_state_unchanged(before, snapshot_state(), "generator authority substitution")


def mutate_field(field: str, value: Any) -> Callable[[dict[str, Any]], None]:
    def apply(registry: dict[str, Any]) -> None:
        registry[field] = value
    return apply


def remove_field(field: str) -> Callable[[dict[str, Any]], None]:
    def apply(registry: dict[str, Any]) -> None:
        registry.pop(field, None)
    return apply


def mutate_snapshot_requirement(snapshot: dict[str, Any]) -> None:
    requirements = snapshot.get("downstreamRequirements")
    if not isinstance(requirements, list) or not requirements:
        raise Fail("snapshot downstreamRequirements missing")
    replacement = list(requirements)
    replacement[0] = "automatically promote production after local restore validation"
    snapshot["downstreamRequirements"] = replacement


def mutate_ops7_missing(reorder: bool) -> Callable[[dict[str, Any]], None]:
    def apply(status: dict[str, Any]) -> None:
        areas = status.get("areas")
        if not isinstance(areas, list):
            raise Fail("status areas missing")
        ops7 = next((row for row in areas if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
        if not isinstance(ops7, dict) or not isinstance(ops7.get("missingEvidence"), list):
            raise Fail("OPS-P0-007 missingEvidence missing")
        if reorder:
            ops7["missingEvidence"] = list(reversed(ops7["missingEvidence"]))
        else:
            replacement = list(ops7["missingEvidence"])
            replacement[0] = "fabricated replacement blocker with unchanged list length"
            ops7["missingEvidence"] = replacement
    return apply


def restore_all(originals: dict[Path, bytes]) -> None:
    for path, payload in originals.items():
        if path.is_symlink():
            path.unlink()
        path.write_bytes(payload)


def run_source_symlink_escape(originals: dict[Path, bytes], preflight_stdout: str) -> None:
    # Never overwrite a fixed /tmp pathname: another process may own it or
    # replace it with a symlink to an unrelated file.
    with tempfile.TemporaryDirectory(prefix="memory-os-ops-p0-007-objective-negative-") as tmp:
        external = Path(tmp) / "objective-authority.json"
        external.write_bytes(originals[OBJECTIVES])
        original_mode = mode(OBJECTIVES)
        restore_all(originals)
        OBJECTIVES.unlink()
        try:
            OBJECTIVES.symlink_to(external)
            run_validator(False, "objective source symlink escape")
            run_generator_rejects("generator objective source symlink escape", "strict snapshot authority", preflight_stdout)
        finally:
            if OBJECTIVES.is_symlink():
                OBJECTIVES.unlink()
            OBJECTIVES.write_bytes(originals[OBJECTIVES])
            OBJECTIVES.chmod(original_mode)


def run_module_symlink_escape(originals: dict[Path, bytes], preflight_stdout: str) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-ops-p0-007-writer-negative-") as tmp:
        external = Path(tmp) / "objective-writer.py"
        external.write_bytes(originals[OBJECTIVE_WRITER])
        original_mode = mode(OBJECTIVE_WRITER)
        restore_all(originals)
        OBJECTIVE_WRITER.unlink()
        try:
            OBJECTIVE_WRITER.symlink_to(external)
            run_validator(False, "objective writer module symlink escape")
            run_generator_rejects(
                "generator objective writer module symlink escape",
                "strict snapshot authority",
                preflight_stdout,
            )
        finally:
            if OBJECTIVE_WRITER.is_symlink():
                OBJECTIVE_WRITER.unlink()
            OBJECTIVE_WRITER.write_bytes(originals[OBJECTIVE_WRITER])
            OBJECTIVE_WRITER.chmod(original_mode)


def main() -> int:
    originals = {
        SNAPSHOT: SNAPSHOT.read_bytes(),
        OBJECTIVES: OBJECTIVES.read_bytes(),
        REQUESTS: REQUESTS.read_bytes(),
        GENERATION: GENERATION.read_bytes(),
        TYPED: TYPED.read_bytes(),
        STATUS: STATUS.read_bytes(),
        OBJECTIVE_WRITER: OBJECTIVE_WRITER.read_bytes(),
    }
    original_modes = {path: mode(path) for path in originals}
    require_material_mutation({"count": 0}, {"count": False}, "boolean/zero mutation guard")
    require_material_mutation({"count": 1}, {"count": True}, "boolean/one mutation guard")
    cases: list[tuple[str, Path, Callable[[dict[str, Any]], None]]] = [
        ("snapshot unknown production authority field", SNAPSHOT, mutate_field("productionAuthorization", True)),
        ("snapshot missing production readiness field", SNAPSHOT, remove_field("productionReady")),
        ("snapshot boolean registered generation count", SNAPSHOT, mutate_field("registeredEnvironmentGenerationCount", False)),
        ("snapshot downstream requirement projection", SNAPSHOT, mutate_snapshot_requirement),
        ("snapshot next action projection", SNAPSHOT, mutate_field("nextAction", "automatically promote production")),
        ("objective boolean aggregate count", OBJECTIVES, mutate_field("approvedObjectiveCount", True)),
        ("objective append-only boundary", OBJECTIVES, mutate_field("appendOnly", False)),
        ("objective schema boundary", OBJECTIVES, mutate_field("schemaVersion", "memory-os-recovery-objectives-registry.corrupt")),
        ("objective production evidence boundary", OBJECTIVES, mutate_field("productionEvidence", True)),
        ("objective production readiness boundary", OBJECTIVES, mutate_field("productionReady", True)),
        ("drill boolean aggregate count", REQUESTS, mutate_field("registeredRequestCount", True)),
        ("drill append-only boundary", REQUESTS, mutate_field("appendOnly", False)),
        ("drill production evidence boundary", REQUESTS, mutate_field("productionEvidence", True)),
        ("generation boolean aggregate count", GENERATION, mutate_field("registeredEvidenceCount", True)),
        ("generation append-only boundary", GENERATION, mutate_field("appendOnly", False)),
        ("generation production readiness boundary", GENERATION, mutate_field("productionReady", True)),
        ("typed boolean aggregate count", TYPED, mutate_field("completeRecordCount", True)),
        ("typed append-only boundary", TYPED, mutate_field("appendOnly", False)),
        ("typed production evidence boundary", TYPED, mutate_field("productionEvidence", True)),
        ("canonical blocker replacement with unchanged count", STATUS, mutate_ops7_missing(False)),
        ("canonical blocker ordering drift", STATUS, mutate_ops7_missing(True)),
        ("production decision promotion", STATUS, mutate_field("productionDecision", "GO")),
    ]
    required_case_labels = {label for label, _, _ in cases} | {
        "objective source symlink escape",
        "objective writer module symlink escape",
    }
    if set(CASE_SPECIFIC_VALIDATOR_REJECTIONS) != required_case_labels:
        raise Fail("strict snapshot case-specific diagnostic mapping drift")

    generator_cases: list[tuple[str, Callable[[dict[str, Any]], None], str | tuple[str, ...]]] = [
        (
            "generator canonical blocker replacement",
            mutate_ops7_missing(False),
            (
                "typed non-resurrection canonical admission authority invalid",
                "canonical OPS-P0-007 blocker authority invalid",
            ),
        ),
        (
            "generator canonical blocker ordering drift",
            mutate_ops7_missing(True),
            (
                "typed non-resurrection canonical admission authority invalid",
                "canonical OPS-P0-007 blocker authority invalid",
            ),
        ),
        (
            "generator production decision promotion",
            mutate_field("productionDecision", "GO"),
            (
                "typed non-resurrection canonical admission authority invalid",
                "production decision must remain NO_GO",
            ),
        ),
    ]

    generator_labels = {label for label, _, _ in generator_cases} | {
        "generator objective source symlink escape",
        "generator objective writer module symlink escape",
    }
    if set(EXACT_GENERATOR_REJECTIONS) | set(NESTED_GENERATOR_REJECTIONS) != generator_labels:
        raise Fail("strict snapshot generator diagnostic mapping drift")
    if set(EXACT_GENERATOR_REJECTIONS) & set(NESTED_GENERATOR_REJECTIONS):
        raise Fail("strict snapshot generator diagnostic mappings overlap")

    try:
        prove_snapshot_state_classifier()
        prove_authority_substitution_classifier()
        prove_temporary_mode_cleanup()
        prove_atomic_replace_probe_classifier()
        prove_positive_validator_classifier()
        prove_case_specific_validator_classifier()
        prove_generator_diagnostic_classifier()
        prove_subprocess_timeout_guard()
        run_validator(True, "clean baseline")
        preflight_stdout = capture_canonical_generator_preflight_stdout()
        run_generator_atomic_write_mode_preservation()
        run_generator_atomic_write_failure()
        run_generator_full_admission_chain_required()
        run_generator_post_write_validator_substitution_rejected()
        run_generator_authority_substitution()
        run_source_symlink_escape(originals, preflight_stdout)
        run_module_symlink_escape(originals, preflight_stdout)
        for label, path, mutate in cases:
            restore_all(originals)
            canonical = load(path)
            authority = copy.deepcopy(canonical)
            mutate(authority)
            require_material_mutation(canonical, authority, label)
            write(path, authority)
            run_validator(False, label)

        for label, mutate, expected_messages in generator_cases:
            restore_all(originals)
            canonical = load(STATUS)
            status = copy.deepcopy(canonical)
            mutate(status)
            require_material_mutation(canonical, status, label)
            write(STATUS, status)
            run_generator_rejects(label, expected_messages, preflight_stdout)

        restore_all(originals)
        run_validator(True, "restored baseline")
    finally:
        restore_all(originals)

    for path, payload in originals.items():
        if path.is_symlink():
            raise Fail(f"negative suite left canonical authority as symlink: {path.relative_to(ROOT)}")
        if path.read_bytes() != payload:
            raise Fail(f"negative suite mutated canonical authority: {path.relative_to(ROOT)}")
        if mode(path) != original_modes[path]:
            raise Fail(f"negative suite changed canonical authority file mode: {path.relative_to(ROOT)}")

    print("Memory OS OPS-P0-007 strict admission snapshot negative validation PASS")
    print(f"controlled validator corruption cases rejected: {len(cases)}")
    print(f"controlled generator corruption cases rejected: {len(generator_cases)}")
    print("strict snapshot generator data/executable authority substitutions rejected: true")
    print("strict snapshot generator full admission helper substitution rejected before publication: true")
    print("strict snapshot generator post-write validator substitution rejected before publication: true")
    print("snapshot source symlink escape rejected by validator and generator: true")
    print("snapshot executable module symlink escape rejected by validator and generator: true")
    print("snapshot unknown/missing field drift rejected: true")
    print("snapshot boolean count drift rejected: true")
    print("snapshot downstream requirement/next-action drift rejected: true")
    print("successful atomic snapshot rewrite preserves canonical mode: true")
    print("failed atomic snapshot replace preserves canonical bytes/mode and removes temporary files: true")
    print("canonical authority files preserved byte-for-byte: true")
    print("rejected generator attempts leave snapshot byte-for-byte unchanged: true")
    print("canonical six-blocker content and ordering preserved: true")
    print("production evidence/readiness/decision promotion rejected: true")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, json.JSONDecodeError, OSError) as exc:
        print(f"OPS-P0-007 ADMISSION SNAPSHOT NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
