#!/usr/bin/env python3
"""Negative proof for the canonical OPS-P0-007 admission-chain full runner.

This test mutates only the imported in-memory runner or an isolated temporary
fixture. It never changes repository files or creates operational evidence.
"""

from __future__ import annotations

import importlib.util
import io
import subprocess
from contextlib import redirect_stdout
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts/validate-memory-os-backup-restore-admission-chain-full.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_target():
    spec = importlib.util.spec_from_file_location("admission_chain_full_negative_target", TARGET)
    if spec is None or spec.loader is None:
        raise Fail("cannot load canonical admission-chain full runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_fixture_target(path: Path):
    spec = importlib.util.spec_from_file_location("admission_chain_full_negative_fixture_target", path)
    if spec is None or spec.loader is None:
        raise Fail("cannot load isolated admission-chain full runner fixture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_fail(label: str, mutation, invoke, expected: str) -> None:
    module = load_target()
    original_subprocess_run = module.subprocess.run
    original_sys_executable = module.sys.executable
    try:
        mutation(module)
        try:
            invoke(module)
        except module.Fail as exc:
            if expected not in str(exc):
                raise Fail(f"{label}: wrong fail-closed diagnostic: {exc}") from exc
            print(f"PASS negative: {label}")
            return
        raise Fail(f"{label}: weakened runner was accepted")
    finally:
        # subprocess and sys are shared imported modules; never leak transport or
        # interpreter mutations into a later case or its freshly imported target.
        module.subprocess.run = original_subprocess_run
        module.sys.executable = original_sys_executable


def expect_symlink_fail(label: str, target: str, expected: str) -> None:
    module = load_target()
    with tempfile.TemporaryDirectory(prefix="admission-chain-symlink-") as tmp:
        fixture_root = Path(tmp)
        scripts = fixture_root / "scripts"
        scripts.mkdir()
        real = scripts / "real-validator.py"
        real.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        linked = scripts / "validator.py"
        try:
            linked.symlink_to(target)
        except (NotImplementedError, OSError) as exc:
            raise Fail(f"{label}: script symlink fixture unavailable: {exc}") from exc
        module.ROOT = fixture_root
        try:
            module.canonical_script("scripts/validator.py")
        except module.Fail as exc:
            if expected not in str(exc):
                raise Fail(f"{label}: wrong fail-closed diagnostic: {exc}") from exc
            print(f"PASS negative: {label}")
            return
        raise Fail(f"{label}: symlinked validator was accepted")


def expect_self_symlink_fail(label: str, target: str, expected: str) -> None:
    with tempfile.TemporaryDirectory(prefix="admission-chain-self-symlink-") as tmp:
        fixture_root = Path(tmp)
        scripts = fixture_root / "scripts"
        scripts.mkdir()
        real = scripts / "runner-real.py"
        real.write_text(TARGET.read_text(encoding="utf-8"), encoding="utf-8")
        canonical = scripts / "validate-memory-os-backup-restore-admission-chain-full.py"
        outside = fixture_root.parent / f"{fixture_root.name}-outside-runner.py"
        if target == "../outside-runner.py":
            outside.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
            link_target = f"../../{outside.name}"
        else:
            link_target = target
        try:
            canonical.symlink_to(link_target)
        except (NotImplementedError, OSError) as exc:
            outside.unlink(missing_ok=True)
            raise Fail(f"{label}: self symlink fixture unavailable: {exc}") from exc
        try:
            module = load_fixture_target(real)
            module.enforce_runtime_authority()
        except module.Fail as exc:
            if expected not in str(exc):
                raise Fail(f"{label}: wrong fail-closed diagnostic: {exc}") from exc
            print(f"PASS negative: {label}")
            return
        finally:
            outside.unlink(missing_ok=True)
        raise Fail(f"{label}: symlinked runner identity was accepted")



def prove_full_step_exit_propagation() -> None:
    """Prove the full-chain parent cannot promote a failed child with PASS stdout."""
    module = load_target()
    original_run = module.subprocess.run
    original_guard = module.enforce_execution_transport
    relative = "scripts/validate-memory-os-backup-restore-admission-chain-full.py"
    label = "controlled full-chain child"

    def fixture_transport_guard() -> None:
        # Only this isolated in-memory test replaces the transport guard.
        pass

    module.enforce_execution_transport = fixture_transport_guard
    try:
        for code, child_stdout, child_stderr in (
            (0, "child success\n", ""),
            (7, "child PASS-looking output\n", "controlled child failure\n"),
            (-9, "", "controlled child signal\n"),
        ):
            calls = []

            def controlled_run(argv, **kwargs):
                calls.append((argv, kwargs))
                return subprocess.CompletedProcess(argv, code, child_stdout, child_stderr)

            module.subprocess.run = controlled_run
            output = io.StringIO()
            with redirect_stdout(output):
                try:
                    module.run_step(relative, label,
                                    canonical_transport_guard=fixture_transport_guard)
                except module.Fail as exc:
                    if code == 0:
                        raise Fail("full-chain successful child was rejected") from exc
                    require(str(exc) == f"{label} failed with exit code {code}: {relative}",
                            "full-chain child nonzero exit diagnostic drift")
                else:
                    require(code == 0, "full-chain child nonzero exit was accepted")
            require(len(calls) == 1, "full-chain child subprocess invocation count drift")
            argv, kwargs = calls[0]
            require(argv == [module.sys.executable, str(ROOT / relative)],
                    "full-chain child interpreter/path binding drift")
            require(kwargs == {
                "cwd": ROOT, "text": True, "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE, "check": False,
            }, "full-chain child subprocess capture or execution mode drift")
            parent_pass = f"PASS chain step: {label}"
            require((parent_pass in output.getvalue()) is (code == 0),
                    "full-chain child parent PASS output contradicts exit status")
    finally:
        module.subprocess.run = original_run
        module.enforce_execution_transport = original_guard
    print("PASS boundary: full-chain child nonzero/signal exits cannot become parent PASS")


def main() -> int:
    prove_full_step_exit_propagation()
    expect_fail(
        "repository root substitution",
        lambda m: setattr(m, "ROOT", ROOT / "scripts"),
        lambda m: m.enforce_runtime_authority(),
        "repository root drift",
    )
    expect_fail(
        "self path substitution",
        lambda m: setattr(m, "SELF_REL", Path("scripts/validate-memory-os-backup-restore-admission-chain.py")),
        lambda m: m.enforce_runtime_authority(),
        "self path drift",
    )
    expect_self_symlink_fail("self symlink substitution", "runner-real.py", "identity drift")
    expect_self_symlink_fail("broken self symlink", "missing-runner.py", "missing or escapes repository")
    expect_self_symlink_fail("escaping self symlink", "../outside-runner.py", "missing or escapes repository")
    expect_fail(
        "script repository escape",
        lambda m: None,
        lambda m: m.canonical_script("../outside-validator.py"),
        "validation authority missing or escapes repository",
    )
    expect_fail(
        "script lexical alias",
        lambda m: None,
        lambda m: m.canonical_script("scripts/../scripts/validate-memory-os-backup-restore-admission-chain-full.py"),
        "validation authority drift",
    )
    expect_symlink_fail("script symlink substitution", "real-validator.py", "validation authority drift")
    expect_symlink_fail("broken script symlink", "missing-validator.py", "validation authority missing or escapes repository")
    expect_symlink_fail("escaping script symlink", "../../outside-validator.py", "validation authority missing or escapes repository")
    expect_fail(
        "validation sequence removal",
        lambda m: setattr(m, "STEPS", m.STEPS[:-1]),
        lambda m: m.enforce_runtime_authority(),
        "validation sequence drift",
    )
    expect_fail(
        "subprocess transport substitution",
        lambda m: setattr(m.subprocess, "run", lambda *args, **kwargs: None),
        lambda m: m.enforce_execution_transport(),
        "subprocess transport drift",
    )
    expect_fail(
        "Python executable substitution",
        lambda m: setattr(m.sys, "executable", str(ROOT)),
        lambda m: m.enforce_execution_transport(),
        "Python executable drift",
    )
    expect_fail(
        "transport guard substitution",
        lambda m: setattr(m, "enforce_execution_transport", lambda: None),
        lambda m: m.enforce_runtime_authority(),
        "transport guard drift",
    )
    expect_fail(
        "script resolver substitution",
        lambda m: setattr(m, "canonical_script", lambda relative: ROOT / relative),
        lambda m: m.run_step(m.STEPS[0][0], m.STEPS[0][1]),
        "script resolver drift",
    )
    expect_fail(
        "authority guard substitution",
        lambda m: setattr(m, "enforce_runtime_authority", lambda: None),
        lambda m: m.main(),
        "authority guard drift",
    )
    expect_fail(
        "execution function substitution",
        lambda m: setattr(m, "run_step", lambda *args, **kwargs: None),
        lambda m: m.main(),
        "execution function drift",
    )
    print("Admission-chain full runner negative validation PASS")
    print("repository mutation: false")
    print("production evidence created: false")
    print("production traffic changed: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ADMISSION CHAIN FULL RUNNER NEGATIVE VALIDATION FAILED: {exc}")
        raise SystemExit(1)
