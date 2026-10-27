#!/usr/bin/env python3
"""Fail closed if generation-evidence validation transport is substituted."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator() -> Any:
    require(VALIDATOR.is_file() and not VALIDATOR.is_symlink(), "canonical generation-evidence validator missing or symlinked")
    require(
        VALIDATOR.resolve(strict=True) == VALIDATOR,
        "canonical generation-evidence validator resolved path drift",
    )
    spec = importlib.util.spec_from_file_location("memory_os_generation_evidence_transport_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load generation-evidence validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(module: Any, label: str, mutate: Callable[[], None], restore: Callable[[], None], expected: str) -> None:
    mutate()
    try:
        try:
            module.main()
        except module.Fail as exc:
            require(expected in str(exc), f"{label} rejected at wrong boundary: {exc}")
            return
        raise Fail(f"generation-evidence transport substitution unexpectedly passed: {label}")
    finally:
        restore()



def prove_private_bounded_child_execution(module: Any) -> None:
    """Exercise the real child runner with synthetic secret-bearing failures."""
    original_run = module.subprocess.run
    canary = "private-generation-evidence-child-canary"
    cases = ("success", "nonzero", "timeout", "oserror", "missing-result", "boolean-code")
    try:
        for case in cases:
            def fake_run(argv: list[str], **kwargs: Any) -> Any:
                require(argv == [module.sys.executable, str(module.INDEPENDENT_REVIEW_VALIDATOR)],
                        "generation evidence child source identity drift")
                require(kwargs.get("cwd") == module.ROOT, "generation evidence child cwd drift")
                require(kwargs.get("stdout") == module.subprocess.DEVNULL and
                        kwargs.get("stderr") == module.subprocess.DEVNULL,
                        "generation evidence child output not private")
                require(kwargs.get("timeout") == 90 and kwargs.get("check") is False,
                        "generation evidence child execution not bounded")
                if case == "timeout":
                    raise module.subprocess.TimeoutExpired(argv, 90, output=canary, stderr=canary)
                if case == "oserror":
                    raise OSError(canary)
                if case == "missing-result":
                    return None
                if case == "boolean-code":
                    return module.subprocess.CompletedProcess(argv, False)
                return module.subprocess.CompletedProcess(argv, 0 if case == "success" else 1,
                                                          stdout=canary, stderr=canary)

            module.subprocess.run = fake_run
            if case == "success":
                module.run_validator(module.INDEPENDENT_REVIEW_VALIDATOR,
                                     module.INDEPENDENT_REVIEW_VALIDATOR_REL, "independent review")
                continue
            try:
                module.run_validator(module.INDEPENDENT_REVIEW_VALIDATOR,
                                     module.INDEPENDENT_REVIEW_VALIDATOR_REL, "independent review")
            except module.Fail as exc:
                require(str(exc) == "generation evidence child validator failed",
                        "generation evidence child exposed non-private diagnostic")
                require(canary not in str(exc), "generation evidence child leaked canary")
                require(exc.__suppress_context__, "generation evidence child exception context exposed")
            else:
                raise Fail("generation evidence child accepted invalid outcome: " + case)
    finally:
        module.subprocess.run = original_run




def prove_private_writer_import_failures(module: Any) -> None:
    """Reject private filesystem errors in the actual generation evidence writer loader."""
    original_spec = module.importlib.util.spec_from_file_location
    original_module = module.importlib.util.module_from_spec
    canary = "private-generation-evidence-writer-import-canary"

    def fail_private(*_args: Any, **_kwargs: Any) -> Any:
        raise OSError(canary)

    try:
        for target in ("spec", "module"):
            if target == "spec":
                module.importlib.util.spec_from_file_location = fail_private
            else:
                module.importlib.util.spec_from_file_location = original_spec
                module.importlib.util.module_from_spec = fail_private
            try:
                module.load_writer()
            except module.Fail as exc:
                require(str(exc) == "generation evidence writer import unavailable",
                        "generation evidence writer import disclosed private error")
                require(canary not in str(exc) and exc.__suppress_context__,
                        "generation evidence writer import exposed exception context")
            else:
                raise Fail("generation evidence writer import accepted private failure: " + target)
    finally:
        module.importlib.util.spec_from_file_location = original_spec
        module.importlib.util.module_from_spec = original_module
    require(callable(getattr(module.load_writer(), "validate_record", None)),
            "generation evidence writer import positive control failed")
    print("PASS: generation evidence writer import private failures and real positive")



def main() -> int:
    module = load_validator()
    prove_private_bounded_child_execution(module)
    prove_private_writer_import_failures(module)

    original_guard = module.enforce_execution_transport
    expect_rejected(
        module,
        "execution guard",
        lambda: setattr(module, "enforce_execution_transport", lambda: None),
        lambda: setattr(module, "enforce_execution_transport", original_guard),
        "execution guard drift",
    )

    original_run = module.subprocess.run
    expect_rejected(
        module,
        "subprocess.run",
        lambda: setattr(module.subprocess, "run", lambda *_args, **_kwargs: None),
        lambda: setattr(module.subprocess, "run", original_run),
        "subprocess execution transport drift",
    )

    original_spec = module.importlib.util.spec_from_file_location
    expect_rejected(
        module,
        "importlib spec loader",
        lambda: setattr(module.importlib.util, "spec_from_file_location", lambda *_args, **_kwargs: None),
        lambda: setattr(module.importlib.util, "spec_from_file_location", original_spec),
        "import spec transport drift",
    )

    original_module_from_spec = module.importlib.util.module_from_spec
    expect_rejected(
        module,
        "importlib module loader",
        lambda: setattr(module.importlib.util, "module_from_spec", lambda *_args, **_kwargs: None),
        lambda: setattr(module.importlib.util, "module_from_spec", original_module_from_spec),
        "module loader transport drift",
    )

    original_run_validator = module.run_validator
    invoked: list[Path] = []

    def observe_validator(path: Path, expected_relative: Path, label: str) -> None:
        invoked.append(expected_relative)
        original_run_validator(path, expected_relative, label)

    module.run_validator = observe_validator
    try:
        module.main()
    finally:
        module.run_validator = original_run_validator
    require(
        module.INDEPENDENT_REVIEW_VALIDATOR_REL in invoked,
        "canonical generation-evidence validation did not execute independent-review authority",
    )

    print("Memory OS generation-evidence execution transport negative PASS")
    print("execution guard substitution accepted: false")
    print("subprocess validation transport substitution accepted: false")
    print("import spec transport substitution accepted: false")
    print("module loader transport substitution accepted: false")
    print("central independent-review execution observed: true")
    print("generation evidence created: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION EVIDENCE TRANSPORT NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
