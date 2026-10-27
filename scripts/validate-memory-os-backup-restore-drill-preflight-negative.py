#!/usr/bin/env python3
"""Prove restore drill preflight rejects stale or semantically weakened authority."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-preflight.py"
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-preflight-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
OBJECTIVES = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
DRILL_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
TEMP_PARENT = ROOT / "contracts/operations"
NEGATIVE_REF = "scripts/validate-memory-os-backup-restore-drill-preflight-negative.py"
SEMANTIC_HELPER_REF = "scripts/memory_os_environment_generation_eligibility.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_restore_drill_preflight_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load preflight validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(validator: Any, canonical: dict[str, Any], name: str, mutate: Callable[[dict[str, Any]], None]) -> None:
    bad = copy.deepcopy(canonical)
    mutate(bad)
    with tempfile.TemporaryDirectory(prefix=".memory-os-preflight-negative-", dir=TEMP_PARENT) as tmp:
        path = Path(tmp) / "contract.json"
        path.write_text(json.dumps(bad, indent=2) + "\n", encoding="utf-8")
        original = validator.CONTRACT
        validator.CONTRACT = path
        try:
            validator.main()
        except validator.Fail:
            print(f"PASS reject: {name}")
            return
        finally:
            validator.CONTRACT = original
    raise Fail(f"negative case unexpectedly accepted: {name}")


def expect_path_rejected(validator: Any, name: str, path: Path) -> None:
    try:
        validator.load(path)
    except validator.Fail:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"escaped path unexpectedly accepted: {name}")



def prove_private_preflight_path_errors(validator: Any) -> None:
    """Reject filesystem path failures without disclosing private exception context."""
    private = "SYNTHETIC_PRIVATE_PREFLIGHT_PATH_CANARY"
    original_resolve = Path.resolve

    def private_resolve(_path, *args, **kwargs):
        raise OSError(private)

    def reject(label: str, operation: Callable[[], object], expected: str) -> None:
        try:
            operation()
        except validator.Fail as exc:
            require(str(exc) == expected and exc.__cause__ is None and exc.__suppress_context__,
                    f"preflight {label} private exception context escaped")
            require(private not in str(exc), f"preflight {label} leaked private path")
        else:
            raise Fail(f"preflight {label} accepted private path failure")

    try:
        Path.resolve = private_resolve
        reject("repo_relative OSError", lambda: validator.repo_relative(CONTRACT),
               "preflight artifact path missing or escapes repository")
        reject("exact executable OSError",
               lambda: validator.require_exact_executable(VALIDATOR, VALIDATOR.relative_to(ROOT),
                                                          "synthetic executable"),
               "synthetic executable missing or escapes repository")
    finally:
        Path.resolve = original_resolve
    reject("outside path canary",
           lambda: validator.repo_relative(Path(tempfile.gettempdir()) / private),
           "preflight artifact path missing or escapes repository")
    original_is_file = Path.is_file

    def private_is_file(_path):
        raise OSError(private)

    try:
        Path.is_file = private_is_file
        reject("exact executable stat", lambda: validator.require_exact_executable(
            VALIDATOR, VALIDATOR.relative_to(ROOT), "synthetic executable"),
            "synthetic executable authority drift")
    finally:
        Path.is_file = original_is_file
    require(validator.repo_relative(CONTRACT) == CONTRACT.relative_to(ROOT),
            "preflight repo_relative positive failed after private fault")
    validator.require_exact_executable(VALIDATOR, VALIDATOR.relative_to(ROOT), "synthetic executable")
    print("PASS: preflight private path errors and exception contexts suppressed")



def prove_private_preflight_import_errors(validator: Any) -> None:
    """Real eligibility helper import must hide private implementation exceptions."""
    original = importlib.util.module_from_spec
    private = "SYNTHETIC_PRIVATE_PREFLIGHT_IMPORT_CANARY"
    for error_type in (OSError, RuntimeError, TypeError):
        def private_import(_spec):
            raise error_type(private)

        try:
            importlib.util.module_from_spec = private_import
            try:
                validator.load_eligibility_helper()
            except validator.Fail as exc:
                require(str(exc) == "preflight eligibility helper import unavailable"
                        and exc.__suppress_context__ and exc.__cause__ is None
                        and private not in str(exc),
                        "preflight helper import leaked private exception")
            else:
                raise Fail("preflight helper private import fault accepted")
        finally:
            importlib.util.module_from_spec = original
    helper = validator.load_eligibility_helper()
    require(callable(getattr(helper, "derive_registry", None)),
            "preflight helper canonical import positive failed")
    print("PASS: preflight helper private import faults and canonical positive")


def prove_pinned_preflight_helper_import(validator: Any) -> None:
    """Checked helper bytes remain authoritative after source or parent replacement."""
    original_path = validator.ELIGIBILITY_HELPER
    original_rel = validator.ELIGIBILITY_HELPER_REL
    original_spec = importlib.util.spec_from_file_location
    with tempfile.TemporaryDirectory(prefix=".preflight-helper-source-", dir=ROOT) as raw:
        sandbox = Path(raw)
        parent = sandbox / "trusted"
        parent.mkdir()
        helper = parent / "helper.py"
        parked = sandbox / "parked"
        redirected = sandbox / "redirected"
        redirected.mkdir()
        canary = redirected / "helper.py"
        source = ("class Fail(RuntimeError):\n    pass\n"
                  "def derive_registry(_registry):\n    return {'origin': 'pinned'}\n")
        helper.write_text(source, encoding="utf-8")
        canary.write_text("raise RuntimeError('PRIVATE_HELPER_SWAP_CANARY')\n", encoding="utf-8")
        try:
            validator.ELIGIBILITY_HELPER = helper
            validator.ELIGIBILITY_HELPER_REL = helper.relative_to(ROOT)
            require(validator.load_eligibility_helper().derive_registry({}) == {"origin": "pinned"},
                    "preflight pinned helper canonical positive failed")
            swapped = False

            def swap_after_read(name, location, *args, **kwargs):
                nonlocal swapped
                if not swapped and Path(location) == helper:
                    swapped = True
                    parent.rename(parked)
                    parent.symlink_to(redirected, target_is_directory=True)
                return original_spec(name, location, *args, **kwargs)

            importlib.util.spec_from_file_location = swap_after_read
            loaded = validator.load_eligibility_helper()
            require(swapped and loaded.derive_registry({}) == {"origin": "pinned"},
                    "preflight helper executed replaced parent source")
            require(canary.read_text(encoding="utf-8") ==
                    "raise RuntimeError('PRIVATE_HELPER_SWAP_CANARY')\n",
                    "preflight helper redirected canary mutated")
        finally:
            importlib.util.spec_from_file_location = original_spec
            validator.ELIGIBILITY_HELPER = original_path
            validator.ELIGIBILITY_HELPER_REL = original_rel
    require(callable(getattr(validator.load_eligibility_helper(), "derive_registry", None)),
            "preflight pinned helper canonical restoration failed")
    print("PASS: preflight eligibility helper uses descriptor-pinned bytes after parent swap")


def expect_strict_preflight_json_reader(validator: Any) -> None:
    """Actual preflight reader rejects noncanonical, unsafe or oversized JSON evidence."""
    require(isinstance(validator.load(CONTRACT), dict), "preflight JSON canonical positive failed")
    with (
        tempfile.TemporaryDirectory(prefix=".preflight-json-negative-", dir=ROOT) as inside_tmp,
        tempfile.TemporaryDirectory(prefix="preflight-json-outside-") as outside_tmp,
    ):
        inside, outside = Path(inside_tmp), Path(outside_tmp)
        canary = outside / "canary.json"
        canary.write_bytes(b'{"SYNTHETIC_EXTERNAL_CANARY":true}')
        regular = inside / "regular.json"
        regular.write_text('{"safe":true}', encoding="utf-8")
        require(validator.load(regular) == {"safe": True}, "preflight JSON regular positive failed")
        bounded_integer = inside / "bounded-integer.json"
        bounded_integer.write_bytes(b'{"value":' + b"9" * 128 + b"}")
        require(validator.load(bounded_integer)["value"] == int("9" * 128),
                "preflight JSON 128-digit integer positive failed")
        bounded = inside / "bounded.json"
        bounded.write_bytes(b'{"padding":"' + b"x" * (validator.MAX_JSON_BYTES - 14) + b'"}')
        require(validator.load(bounded)["padding"], "preflight JSON bounded positive failed")

        def reject(label: str, path: object, expected: str) -> None:
            try:
                validator.load(path)
            except validator.Fail as exc:
                require(expected in str(exc) and "SYNTHETIC_EXTERNAL_CANARY" not in str(exc),
                        f"preflight JSON wrong rejection: {label}")
            else:
                raise Fail(f"preflight JSON accepted {label}")

        oversized = inside / "oversized.json"
        oversized.write_bytes(b'{"padding":"' + b"x" * validator.MAX_JSON_BYTES + b'"}')
        reject("oversized", oversized, "exceeds reviewed read limit")
        reject("outside", canary, "escaped repository")
        for label, raw, expected in (
            ("nested duplicate", b'{"outer":{"key":1,"key":2}}', "duplicate"),
            ("NaN", b'{"value":NaN}', "nonfinite"),
            ("Infinity", b'{"value":Infinity}', "nonfinite"),
            ("negative Infinity", b'{"value":-Infinity}', "nonfinite"),
            ("float overflow", b'{"value":1e999}', "nonfinite"),
            ("invalid UTF-8", b'{"value":"' + bytes([255]) + b'"}', "unreadable or invalid"),
            ("129-digit integer", b'{"value":' + b"9" * 129 + b"}", "integer too large"),
            ("huge integer", b'{"value":' + b"9" * 5000 + b"}", "integer too large"),
        ):
            path = inside / (label.replace(" ", "-") + ".json")
            path.write_bytes(raw)
            reject(label, path, expected)
        direct = inside / "direct-link.json"
        direct.symlink_to(canary)
        reject("direct symlink", direct, "symlink refused")
        alias = inside / "alias"
        alias.symlink_to(outside, target_is_directory=True)
        reject("ancestor symlink", alias / "canary.json", "symlink refused")
        directory = inside / "directory.json"
        directory.mkdir()
        reject("directory", directory, "missing or unsafe")
        fifo = inside / "fifo.json"
        os.mkfifo(fifo)
        reject("FIFO", fifo, "missing or unsafe")
        reject("missing", inside / "missing.json", "missing or unsafe")
        reject("non-Path", "contracts/operations/backup-restore-drill-preflight-contract.v1.json",
               "absolute Path")
        require(canary.read_bytes() == b'{"SYNTHETIC_EXTERNAL_CANARY":true}',
                "preflight JSON reader changed outside canary")
    print("PASS: preflight strict JSON 4 positives and 16 unsafe/nonfinite negatives")


def expect_pinned_preflight_json_reader(validator: Any) -> None:
    """Real-reader parent and ancestor swaps must never redirect JSON reads."""
    protected = (CONTRACT.read_bytes(), GEN_REGISTRY.read_bytes(), OBJECTIVES.read_bytes(), DRILL_REGISTRY.read_bytes())
    with tempfile.TemporaryDirectory(prefix=".preflight-json-fd-race-", dir=ROOT) as raw:
        sandbox = Path(raw)
        for case in ("parent", "ancestor"):
            checked = sandbox / (case + "-checked")
            parked = sandbox / (case + "-parked")
            redirect = sandbox / (case + "-redirect")
            checked.mkdir()
            redirect.mkdir()
            if case == "ancestor":
                (checked / "nested").mkdir()
                (redirect / "nested").mkdir()
                checked_leaf = checked / "nested/candidate.json"
                redirect_leaf = redirect / "nested/candidate.json"
                trigger = "nested"
            else:
                checked_leaf = checked / "candidate.json"
                redirect_leaf = redirect / "candidate.json"
                trigger = "candidate.json"
            checked_leaf.write_bytes(b'{"source":"pinned"}')
            redirect_leaf.write_bytes(b'{"source":"redirected","secret":"SYNTHETIC_EXTERNAL_CANARY"}')
            original_open = os.open
            swapped = False

            def swap_during_walk(target, flags, *args, **kwargs):
                nonlocal swapped
                if not swapped and target == trigger and kwargs.get("dir_fd") is not None:
                    swapped = True
                    checked.rename(parked)
                    checked.symlink_to(redirect, target_is_directory=True)
                return original_open(target, flags, *args, **kwargs)

            try:
                require(validator.load(checked_leaf) == {"source": "pinned"},
                        f"preflight {case} reader positive control failed")
                os.open = swap_during_walk
                result = validator.load(checked_leaf)
                require(swapped, f"preflight {case} race injection not reached")
                require(result == {"source": "pinned"},
                        f"preflight {case} race read redirected JSON")
                require(redirect_leaf.read_bytes() == b'{"source":"redirected","secret":"SYNTHETIC_EXTERNAL_CANARY"}',
                        f"preflight {case} race changed external canary")
            finally:
                os.open = original_open
    require(
        (CONTRACT.read_bytes(), GEN_REGISTRY.read_bytes(), OBJECTIVES.read_bytes(), DRILL_REGISTRY.read_bytes()) == protected,
        "preflight JSON race negative mutated protected authorities",
    )
    print("PASS: actual preflight JSON reader parent and ancestor swap retain pinned original source")


def expect_preflight_json_descriptor_faults(validator: Any) -> None:
    """Exercise real-reader cleanup and ownership under private synthetic failures."""
    with tempfile.TemporaryDirectory(prefix=".preflight-json-fd-fault-", dir=ROOT) as raw:
        path = Path(raw) / "positive.json"
        path.write_bytes(b'{"safe":true}')
        for fault, expected in (
            ("close", "preflight JSON cleanup failed"),
            ("fdopen", "preflight JSON unreadable or invalid"),
        ):
            original_open, original_close, original_fdopen = os.open, os.close, os.fdopen
            opened: list[int] = []
            faulted = False

            def capture_open(*args, **kwargs):
                descriptor = original_open(*args, **kwargs)
                opened.append(descriptor)
                return descriptor

            def close_then_fail(descriptor):
                nonlocal faulted
                original_close(descriptor)
                if not faulted:
                    faulted = True
                    raise OSError("SYNTHETIC_PRIVATE_FD_CLOSE_CANARY")

            def fdopen_then_fail(descriptor, *args, **kwargs):
                nonlocal faulted
                faulted = True
                raise OSError("SYNTHETIC_PRIVATE_FDOPEN_CANARY")

            try:
                os.open = capture_open
                if fault == "close":
                    os.close = close_then_fail
                else:
                    os.fdopen = fdopen_then_fail
                try:
                    validator.load(path)
                except validator.Fail as exc:
                    require(str(exc) == expected and exc.__suppress_context__ and exc.__cause__ is None,
                            f"preflight JSON {fault} fault leaked or misclassified")
                    require("SYNTHETIC_PRIVATE_" not in str(exc),
                            f"preflight JSON {fault} private diagnostic leaked")
                else:
                    raise Fail(f"preflight JSON {fault} fault unexpectedly accepted")
            finally:
                os.open, os.close, os.fdopen = original_open, original_close, original_fdopen
            require(faulted and opened, f"preflight JSON {fault} injection not reached")
            for descriptor in opened:
                try:
                    os.fstat(descriptor)
                except OSError:
                    pass
                else:
                    raise Fail(f"preflight JSON {fault} leaked descriptor")
            require(validator.load(path) == {"safe": True},
                    f"preflight JSON {fault} recovery positive failed")
    print("PASS: actual preflight JSON reader close/fdopen private faults clean all descriptors")


def expect_preflight_json_platform_flags(validator: Any) -> None:
    """Missing and ineffective nofollow flags must fail before any JSON open."""
    with tempfile.TemporaryDirectory(prefix=".preflight-json-flags-", dir=ROOT) as raw:
        path = Path(raw) / "positive.json"
        path.write_bytes(b'{"safe":true}')
        for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY"):
            original = getattr(os, flag)
            try:
                for invalid in (None, 0):
                    setattr(os, flag, invalid)
                    try:
                        validator.load(path)
                    except validator.Fail as exc:
                        require(str(exc) == "preflight JSON nofollow support required"
                                and exc.__suppress_context__ and exc.__cause__ is None,
                                f"preflight JSON {flag} unsafe platform failure class drift")
                    else:
                        raise Fail(f"preflight JSON accepted unsafe {flag}")
            finally:
                setattr(os, flag, original)
        require(validator.load(path) == {"safe": True},
                "preflight JSON reader failed after platform flag restoration")
    print("PASS: preflight JSON missing/zero nofollow, nonblock and directory flags rejected")


def expect_state_rejected(
    validator: Any,
    generations: dict[str, Any],
    objectives: dict[str, Any],
    drill_registry: dict[str, Any],
    name: str,
    mutate: Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], None],
) -> None:
    bad_generations = copy.deepcopy(generations)
    bad_objectives = copy.deepcopy(objectives)
    bad_drill_registry = copy.deepcopy(drill_registry)
    mutate(bad_generations, bad_objectives, bad_drill_registry)
    try:
        validator.derive_state(bad_generations, bad_objectives, bad_drill_registry)
    except validator.Fail:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative state case unexpectedly accepted: {name}")


def expect_helper_authority_substitution_rejected(
    validator: Any,
    generations: dict[str, Any],
    objectives: dict[str, Any],
    drill_registry: dict[str, Any],
) -> None:
    original = validator.ELIGIBILITY_HELPER
    validator.ELIGIBILITY_HELPER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
    try:
        validator.derive_state(copy.deepcopy(generations), copy.deepcopy(objectives), copy.deepcopy(drill_registry))
    except validator.Fail as exc:
        require("eligibility authority" in str(exc), "runtime semantic helper substitution rejected for unexpected reason")
        print("PASS reject: runtime semantic eligibility helper substitution")
        return
    finally:
        validator.ELIGIBILITY_HELPER = original
    raise Fail("runtime semantic eligibility helper substitution unexpectedly accepted")


def expect_upstream_validator_substitutions_rejected(validator: Any) -> None:
    substitute = ROOT / "scripts/validate-memory-os-backup-restore-drill-preflight.py"
    for attribute, label in (
        ("GEN_VALIDATOR", "environment generation"),
        ("OBJECTIVE_VALIDATOR", "recovery objectives"),
        ("DRILL_VALIDATOR", "restore drill request"),
    ):
        original = getattr(validator, attribute)
        setattr(validator, attribute, substitute)
        try:
            validator.run_validator(getattr(validator, attribute), label)
        except validator.Fail as exc:
            require("authority drift" in str(exc), f"{label} validator substitution rejected for unexpected reason")
            print(f"PASS reject: runtime {label} validator substitution")
        else:
            raise Fail(f"runtime {label} validator substitution unexpectedly accepted")
        finally:
            setattr(validator, attribute, original)


def expect_upstream_validator_output_redacted(validator: Any) -> None:
    """Upstream validator failures cannot expose their raw stdout/stderr or exception text."""
    original_run = validator.subprocess.run
    calls: list[list[str]] = []

    def reviewed_run(command: list[str], **kwargs: Any) -> SimpleNamespace:
        calls.append(command)
        require(command == [validator.sys.executable, str(validator.GEN_VALIDATOR)],
                "preflight upstream executable drift")
        require(kwargs.get("cwd") == validator.ROOT and
                kwargs.get("stdout") == validator.subprocess.DEVNULL and
                kwargs.get("stderr") == validator.subprocess.DEVNULL and
                kwargs.get("check") is False and kwargs.get("timeout") == 180,
                "preflight upstream output/timeout boundary drift")
        return SimpleNamespace(returncode=0)

    try:
        validator.subprocess.run = reviewed_run
        validator.run_validator(validator.GEN_VALIDATOR, "environment generation")
        require(len(calls) == 1, "preflight reviewed upstream positive not executed")

        validator.subprocess.run = lambda *args, **kwargs: SimpleNamespace(
            returncode=1, stdout="SYNTHETIC_SECRET_STDOUT_DO_NOT_LOG",
            stderr="SYNTHETIC_SECRET_STDERR_DO_NOT_LOG",
        )
        try:
            validator.run_validator(validator.GEN_VALIDATOR, "environment generation")
        except validator.Fail as exc:
            require("validator failed" in str(exc) and
                    "SYNTHETIC_SECRET" not in str(exc),
                    "preflight upstream raw failure output exposed")
        else:
            raise Fail("preflight upstream failed exit accepted")

        validator.subprocess.run = lambda *args, **kwargs: SimpleNamespace(returncode=True)
        try:
            validator.run_validator(validator.GEN_VALIDATOR, "environment generation")
        except validator.Fail:
            pass
        else:
            raise Fail("preflight upstream boolean exit accepted")

        def timed_out(*args: Any, **kwargs: Any) -> None:
            raise validator.subprocess.TimeoutExpired("SYNTHETIC_SECRET_COMMAND", 180)
        validator.subprocess.run = timed_out
        try:
            validator.run_validator(validator.GEN_VALIDATOR, "environment generation")
        except validator.Fail as exc:
            require("TimeoutExpired" in str(exc) and "SYNTHETIC_SECRET" not in str(exc),
                    "preflight upstream timeout exposed command")
        else:
            raise Fail("preflight upstream timeout accepted")

        def failed_os(*args: Any, **kwargs: Any) -> None:
            raise OSError("SYNTHETIC_SECRET_OSERROR_DO_NOT_LOG")
        validator.subprocess.run = failed_os
        try:
            validator.run_validator(validator.GEN_VALIDATOR, "environment generation")
        except validator.Fail as exc:
            require("OSError" in str(exc) and "SYNTHETIC_SECRET" not in str(exc),
                    "preflight upstream OS failure exposed secret")
        else:
            raise Fail("preflight upstream OS failure accepted")
    finally:
        validator.subprocess.run = original_run
    print("PASS: preflight upstream bounded output-suppressed positive and 4 negatives")


def expect_unexpected_helper_exception_preserved(
    validator: Any,
    generations: dict[str, Any],
    objectives: dict[str, Any],
    drill_registry: dict[str, Any],
) -> None:
    class BrokenHelper:
        class Fail(RuntimeError):
            pass

        @staticmethod
        def derive_registry(_registry: dict[str, Any]) -> dict[str, Any]:
            raise TypeError("synthetic unexpected semantic helper failure")

    original = validator.load_eligibility_helper
    validator.load_eligibility_helper = lambda: BrokenHelper
    try:
        validator.derive_state(copy.deepcopy(generations), copy.deepcopy(objectives), copy.deepcopy(drill_registry))
    except TypeError as exc:
        require(str(exc) == "synthetic unexpected semantic helper failure", "unexpected helper exception identity drift")
        print("PASS preserve: unexpected semantic helper TypeError")
        return
    except validator.Fail as exc:
        raise Fail(f"unexpected helper exception was normalized as domain rejection: {exc}") from exc
    finally:
        validator.load_eligibility_helper = original
    raise Fail("unexpected helper exception was silently accepted")



def prove_private_semantic_helper_domain_failure(validator: Any) -> None:
    """Helper domain rejection must not disclose private message or chained cause."""
    private = "SYNTHETIC_PRIVATE_SEMANTIC_HELPER_CANARY"

    class SyntheticHelper:
        class Fail(RuntimeError):
            pass

        @staticmethod
        def derive_registry(_generations):
            raise SyntheticHelper.Fail(private)

    original = validator.load_eligibility_helper
    try:
        validator.load_eligibility_helper = lambda: SyntheticHelper
        try:
            validator.derive_state({}, {}, {})
        except validator.Fail as exc:
            require(str(exc) == "shared generation semantic derivation failed"
                    and exc.__suppress_context__ and exc.__cause__ is None
                    and private not in str(exc),
                    "preflight semantic helper domain failure leaked private details")
        else:
            raise Fail("preflight private semantic helper domain failure accepted")
    finally:
        validator.load_eligibility_helper = original
    require(callable(getattr(validator.load_eligibility_helper(), "derive_registry", None)),
            "preflight semantic helper canonical positive unavailable")
    print("PASS: preflight semantic helper domain errors private; unexpected failures remain distinct")


def main() -> int:
    require(
        VALIDATOR.is_file()
        and CONTRACT.is_file()
        and GEN_REGISTRY.is_file()
        and OBJECTIVES.is_file()
        and DRILL_REGISTRY.is_file()
        and TEMP_PARENT.is_dir(),
        "preflight negative foundation missing",
    )
    validator = load_validator()
    prove_private_preflight_path_errors(validator)
    prove_private_preflight_import_errors(validator)
    prove_pinned_preflight_helper_import(validator)
    prove_private_semantic_helper_domain_failure(validator)
    canonical = load(CONTRACT)
    generations = load(GEN_REGISTRY)
    objectives = load(OBJECTIVES)
    drill_registry = load(DRILL_REGISTRY)
    require(canonical.get("negativeAdmissionValidator") == NEGATIVE_REF, "preflight contract negativeAdmissionValidator drift")
    require((ROOT / NEGATIVE_REF).is_file(), "preflight negativeAdmissionValidator artifact missing")
    require(canonical.get("semanticEligibilityHelper") == SEMANTIC_HELPER_REF, "preflight semanticEligibilityHelper drift")
    require((ROOT / SEMANTIC_HELPER_REF).is_file(), "preflight semanticEligibilityHelper artifact missing")
    current_state = canonical.get("currentState")
    readiness = canonical.get("readiness")
    require(isinstance(current_state, dict) and set(current_state) == validator.STATE_FIELDS, "canonical preflight currentState is not exact")
    require(isinstance(readiness, dict) and set(readiness) == validator.READINESS_FIELDS, "canonical preflight readiness is not exact")
    print("PASS baseline: canonical preflight negative authority and field sets are exact")

    expect_path_rejected(
        validator,
        "preflight contract path escapes repository root",
        Path(tempfile.gettempdir()) / "memory-os-preflight-outside-root.json",
    )
    expect_rejected(
        validator,
        canonical,
        "semantic eligibility helper authority drift",
        lambda value: value.__setitem__("semanticEligibilityHelper", "scripts/register-memory-os-production-equivalent-environment-generation.py"),
    )
    expect_rejected(
        validator,
        canonical,
        "legacy distinct unsuperseded environment alias",
        lambda value: value["currentState"].__setitem__("distinctUnsupersededEnvironmentCount", 0),
    )
    expect_rejected(
        validator,
        canonical,
        "legacy two-generation readiness alias",
        lambda value: value["readiness"].__setitem__("twoDistinctUnsupersededEnvironmentGenerationsAvailable", False),
    )
    expect_rejected(
        validator,
        canonical,
        "unexpected future currentState field",
        lambda value: value["currentState"].__setitem__("unexpectedAuthorityAlias", False),
    )
    expect_rejected(
        validator,
        canonical,
        "boolean canonical registered generation count",
        lambda value: value["currentState"].__setitem__("registeredGenerationCount", False),
    )
    expect_rejected(
        validator,
        canonical,
        "boolean canonical approved objective count",
        lambda value: value["currentState"].__setitem__("approvedRecoveryObjectiveCount", False),
    )
    expect_rejected(
        validator,
        canonical,
        "unexpected future readiness field",
        lambda value: value["readiness"].__setitem__("unexpectedReadinessAlias", False),
    )
    expect_rejected(
        validator,
        canonical,
        "generation blocker without semantic preflight eligibility",
        lambda value: value["blockingPrerequisiteSemantics"][validator.GEN_BLOCKER].__setitem__("requiresSemanticPreflightEligibility", False),
    )
    expect_rejected(
        validator,
        canonical,
        "generation blocker without distinct environment binding",
        lambda value: value["blockingPrerequisiteSemantics"][validator.GEN_BLOCKER].__setitem__("requiresDistinctEnvironmentId", False),
    )
    expect_rejected(
        validator,
        canonical,
        "generation blocker weakened to one generation",
        lambda value: value["blockingPrerequisiteSemantics"][validator.GEN_BLOCKER].__setitem__("minimumEnvironmentGenerationCount", 1),
    )
    expect_rejected(
        validator,
        canonical,
        "objective blocker without current approved objective binding",
        lambda value: value["blockingPrerequisiteSemantics"][validator.OBJECTIVE_BLOCKER].__setitem__("requiresCurrentApprovedRecoveryObjective", False),
    )
    expect_state_rejected(
        validator,
        generations,
        objectives,
        drill_registry,
        "generation registry schema drift",
        lambda g, _o, _d: g.__setitem__("schemaVersion", "memory-os-production-equivalent-environment-generation-registry.v0"),
    )
    expect_state_rejected(
        validator,
        generations,
        objectives,
        drill_registry,
        "boolean approved recovery objective count",
        lambda _g, o, _d: o.__setitem__("approvedObjectiveCount", False),
    )
    expect_state_rejected(
        validator,
        generations,
        objectives,
        drill_registry,
        "boolean registered drill request count",
        lambda _g, _o, d: d.__setitem__("registeredRequestCount", False),
    )
    expect_state_rejected(
        validator,
        generations,
        objectives,
        drill_registry,
        "boolean current executable drill request count",
        lambda _g, _o, d: d.__setitem__("currentExecutableRequestCount", False),
    )
    expect_helper_authority_substitution_rejected(validator, generations, objectives, drill_registry)
    expect_strict_preflight_json_reader(validator)
    expect_pinned_preflight_json_reader(validator)
    expect_preflight_json_descriptor_faults(validator)
    expect_preflight_json_platform_flags(validator)
    expect_upstream_validator_substitutions_rejected(validator)
    expect_upstream_validator_output_redacted(validator)
    expect_unexpected_helper_exception_preserved(validator, generations, objectives, drill_registry)

    print("Memory OS restore drill preflight negative authority-shape suite PASS")
    print("escaped artifact path accepted: false")
    print("negative validator contract binding: true")
    print("shared semantic eligibility helper contract binding: true")
    print("runtime semantic eligibility helper substitution accepted: false")
    print("runtime upstream validator substitution accepted: false")
    print("generation registry schema drift accepted: false")
    print("stable blocker ids require semantic preflight gates: true")
    print("registered generation count alone satisfies blocker: false")
    print("boolean registry/current-state counts accepted: false")
    print("unexpected semantic helper exceptions normalized as domain rejection: false")
    print("stale state aliases accepted: false")
    print("unexpected readiness aliases accepted: false")
    print("canonical authority mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE DRILL PREFLIGHT NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
