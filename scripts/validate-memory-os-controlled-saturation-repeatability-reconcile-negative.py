#!/usr/bin/env python3
"""Prove repeatability reconciliation pins authorities and cannot leave partial writes."""

from __future__ import annotations

import contextlib
import copy
import json
import importlib.util
import io
import os
import stat
import sys
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-controlled-saturation-repeatability.py"


def load_module():
    spec = importlib.util.spec_from_file_location("repeatability_reconciler", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load repeatability reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_unchanged(protected, before, label: str) -> None:
    for path in protected:
        if path.read_bytes() != before[path]:
            raise RuntimeError(f"partial authority write after {label}: {path.relative_to(ROOT)}")


def temp_residue(path: Path) -> list[Path]:
    return list(path.parent.glob(f".{path.name}.*.tmp"))


def expect_authority_rejection(module, attr: str, replacement: Path) -> None:
    original = getattr(module, attr)
    setattr(module, attr, replacement)
    try:
        try:
            module.enforce_runtime_authorities()
        except module.Fail:
            pass
        else:
            raise RuntimeError(f"{attr} substitution must be rejected")
    finally:
        setattr(module, attr, original)


def run_authority_substitutions(module) -> None:
    substitutions = {
        "CONTRACT": module.LOAD,
        "RESULT": module.CONTRACT,
        "VALIDATOR": module.LOAD_VALIDATOR,
        "LOAD_VALIDATOR": module.VALIDATOR,
        "OPERABILITY_VALIDATOR": module.LOAD_VALIDATOR,
        "LOAD": module.CONTRACT,
        "STATUS": module.LOAD,
        "WORKFLOW": module.VALIDATOR,
    }
    for attr, replacement in substitutions.items():
        expect_authority_rejection(module, attr, replacement)
    module.enforce_runtime_authorities()


def run_prewrite_failure(module) -> None:
    protected = (module.CONTRACT, module.LOAD, module.STATUS)
    before = {path: path.read_bytes() for path in protected}
    original_load = module.load

    def fail_on_status(path: Path):
        if path == module.STATUS:
            raise module.Fail("synthetic status read failure")
        return original_load(path)

    module.load = fail_on_status
    try:
        module.main()
    except module.Fail as exc:
        if str(exc) != "synthetic status read failure":
            raise
    else:
        raise RuntimeError("reconciler unexpectedly succeeded after synthetic status read failure")
    finally:
        module.load = original_load

    assert_unchanged(protected, before, "rejected pre-write reconcile")


def run_postwrite_failure(module) -> None:
    protected = (module.CONTRACT, module.LOAD, module.STATUS)
    before = {path: path.read_bytes() for path in protected}
    contract = module.load(module.CONTRACT)
    load_contract = module.load(module.LOAD)
    status = module.load(module.STATUS)
    contract["_rollbackNegativeMarker"] = True
    load_contract["_rollbackNegativeMarker"] = True
    status["_rollbackNegativeMarker"] = True
    original_validators = module.run_post_write_validators

    def fail_after_write() -> None:
        raise RuntimeError("synthetic post-write repeatability validation failure")

    module.run_post_write_validators = fail_after_write
    try:
        try:
            module.write_transactionally(contract, load_contract, status)
        except RuntimeError as exc:
            if str(exc) != "synthetic post-write repeatability validation failure":
                raise
        else:
            raise RuntimeError("reconciler unexpectedly accepted post-write validation failure")
    finally:
        module.run_post_write_validators = original_validators

    assert_unchanged(protected, before, "post-write validation rollback")


def run_atomic_replace_failure(module) -> None:
    protected = (module.CONTRACT, module.LOAD, module.STATUS)
    before = {path: path.read_bytes() for path in protected}
    residues_before = set(path for authority in protected for path in temp_residue(authority))
    original_replace = module.os.replace
    calls = 0

    def fail_first_replace(src, dst):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("synthetic repeatability atomic replacement failure")
        original_replace(src, dst)

    module.os.replace = fail_first_replace
    try:
        rejected = False
        try:
            module.write_transactionally(
                module.load(module.CONTRACT),
                module.load(module.LOAD),
                module.load(module.STATUS),
            )
        except BaseException as exc:
            rejected = True
            if "synthetic repeatability atomic replacement failure" not in str(exc):
                raise RuntimeError(f"unexpected atomic rejection: {exc}") from exc
        if not rejected:
            raise RuntimeError("repeatability reconciler accepted synthetic atomic replacement failure")
        assert_unchanged(protected, before, "atomic replacement failure")
        residues_after = set(path for authority in protected for path in temp_residue(authority))
        if residues_after != residues_before:
            raise RuntimeError("repeatability atomic failure left temporary authority residue")
    finally:
        module.os.replace = original_replace
        for path, payload in before.items():
            if path.read_bytes() != payload:
                module.atomic_write_bytes(path, payload)



def run_validator_output_negative(module) -> None:
    marker = "SYNTHETIC_REPEATABILITY_SECRET_MARKER"
    original_run = module.subprocess.run

    def noisy_validator(*args, **kwargs):
        if kwargs.get("stdout") != subprocess.DEVNULL or kwargs.get("stderr") != subprocess.DEVNULL:
            raise RuntimeError("validator streams must be suppressed")
        raise subprocess.CalledProcessError(17, args[0], output=marker, stderr=marker)

    module.subprocess.run = noisy_validator
    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                module.run_validator(module.VALIDATOR)
            except module.Fail as exc:
                if marker in str(exc) or not exc.__suppress_context__ or "exit 17" not in str(exc):
                    raise RuntimeError("validator failure disclosed raw output or lost exit code") from None
            else:
                raise RuntimeError("noisy validator unexpectedly accepted")
    finally:
        module.subprocess.run = original_run
    if marker in stdout.getvalue() + stderr.getvalue():
        raise RuntimeError("validator output reached CI streams")


def run_atomic_path_negative(module) -> None:
    with tempfile.TemporaryDirectory(prefix="repeatability-atomic-negative-") as temp:
        root = Path(temp)
        target = root / "authority.json"
        target.write_bytes(b"original")
        target.chmod(0o640)
        module.atomic_write_bytes(target, b"updated")
        if target.read_bytes() != b"updated" or stat.S_IMODE(target.stat().st_mode) != 0o640:
            raise RuntimeError("existing repeatability authority mode or bytes drifted")
        new = root / "new.json"
        module.atomic_write_bytes(new, b"new")
        if new.read_bytes() != b"new" or stat.S_IMODE(new.stat().st_mode) != 0o644:
            raise RuntimeError("new repeatability authority mode drifted")

        outside = root / "outside-canary"
        outside.write_bytes(b"outside")
        link = root / "link.json"
        link.symlink_to(outside)
        directory = root / "directory"
        directory.mkdir()
        linked_parent = root / "linked-parent"
        linked_parent.symlink_to(directory, target_is_directory=True)
        for unsafe in (link, linked_parent / "inside.json", directory, root / "missing" / "inside.json"):
            try:
                module.atomic_write_bytes(unsafe, b"forbidden")
            except module.Fail:
                pass
            else:
                raise RuntimeError(f"unsafe repeatability path accepted: {unsafe.name}")
        if outside.read_bytes() != b"outside" or list(directory.iterdir()):
            raise RuntimeError("unsafe path changed outside canary or linked directory")

        original_replace = module.os.replace
        def fail_replace(*args):
            raise OSError("SYNTHETIC_REPEATABILITY_REPLACE_SECRET")
        module.os.replace = fail_replace
        try:
            try:
                module.atomic_write_bytes(target, b"forbidden")
            except OSError:
                pass
            else:
                raise RuntimeError("atomic replace failure unexpectedly accepted")
        finally:
            module.os.replace = original_replace
        if target.read_bytes() != b"updated" or list(root.glob(".authority.json.*.tmp")):
            raise RuntimeError("atomic replace failure changed authority or left residue")


def run_rollback_secret_negative(module) -> None:
    marker = "SYNTHETIC_REPEATABILITY_ROLLBACK_SECRET"
    original_write = module.write
    original_atomic = module.atomic_write_bytes
    original_validators = module.run_post_write_validators
    module.write = lambda *args: None
    def noisy_rollback(*args):
        raise OSError(marker)
    def noisy_validation():
        raise RuntimeError(marker)
    module.atomic_write_bytes = noisy_rollback
    module.run_post_write_validators = noisy_validation
    try:
        try:
            module.write_transactionally(
                module.load(module.CONTRACT),
                module.load(module.LOAD),
                module.load(module.STATUS),
            )
        except module.Fail as exc:
            if marker in str(exc) or "OSError" not in str(exc) or not exc.__suppress_context__:
                raise RuntimeError("repeatability rollback disclosed secret or suppressed failure") from None
        else:
            raise RuntimeError("failed repeatability rollback unexpectedly accepted")
    finally:
        module.write = original_write
        module.atomic_write_bytes = original_atomic
        module.run_post_write_validators = original_validators



def run_stronger_readiness_negatives(module) -> None:
    protected = (module.CONTRACT, module.LOAD, module.STATUS)
    before = {path: path.read_bytes() for path in protected}
    originals = {path: module.load(path) for path in (module.CONTRACT, module.LOAD, module.STATUS, module.RESULT)}
    original_load = module.load
    original_validator = module.run_validator
    original_write = module.write_transactionally
    cases = [
        (module.CONTRACT, "capacityBoundaryEstablished"),
        (module.CONTRACT, "operationalThresholdApproved"),
        (module.CONTRACT, "independentReviewCompleted"),
        (module.CONTRACT, "productionReady"),
        (module.LOAD, "capacityBoundaryEstablished"),
        (module.LOAD, "operationalThresholds"),
        (module.LOAD, "productionReady"),
    ]
    for target, field in cases:
        fixture = {path: copy.deepcopy(value) for path, value in originals.items()}
        fixture[target]["readiness"][field] = True
        def fake_load(path):
            return fixture[path]
        def forbidden_write(*args):
            raise RuntimeError("stronger readiness reached write boundary")
        module.load = fake_load
        module.run_validator = lambda *args: None
        module.write_transactionally = forbidden_write
        try:
            try:
                module.main()
            except module.Fail as exc:
                if "refusing to downgrade stronger" not in str(exc):
                    raise RuntimeError(f"unexpected stronger readiness rejection: {field}") from None
            else:
                raise RuntimeError(f"stronger readiness was downgraded: {field}")
        finally:
            module.load = original_load
            module.run_validator = original_validator
            module.write_transactionally = original_write

    for prior in (module.CONTRACT, module.LOAD):
        fixture = {path: copy.deepcopy(value) for path, value in originals.items()}
        fixture[module.RESULT]["repeatableLocalDegradationSignalObserved"] = False
        fixture[module.CONTRACT]["readiness"]["repeatableLocalDegradationSignalObserved"] = prior == module.CONTRACT
        fixture[module.LOAD]["readiness"]["repeatableLocalDegradationSignalObserved"] = prior == module.LOAD
        module.load = lambda path: fixture[path]
        module.run_validator = lambda *args: None
        module.write_transactionally = lambda *args: (_ for _ in ()).throw(RuntimeError("signal downgrade reached write"))
        try:
            try:
                module.main()
            except module.Fail as exc:
                if "refusing to downgrade previously admitted" not in str(exc):
                    raise RuntimeError("unexpected signal regression rejection") from None
            else:
                raise RuntimeError("previously admitted repeatability signal was downgraded")
        finally:
            module.load = original_load
            module.run_validator = original_validator
            module.write_transactionally = original_write
    assert_unchanged(protected, before, "stronger readiness and signal downgrade negatives")



def run_inline_diagnostic_writer_negatives() -> None:
    workflow = (ROOT / ".github/workflows/reconcile-controlled-saturation-repeatability-authority.yml").read_text(encoding="utf-8")
    if '          cat "$log"' in workflow or "text[-12000:]" in workflow:
        raise RuntimeError("repeatability workflow disclosed raw validator log")
    marker = "      - name: Record privacy-safe repeatability diagnostic\\n"
    if workflow.count(marker.replace("\\n", "\n")) != 1:
        raise RuntimeError("repeatability diagnostic step drift")
    step = workflow.index(marker.replace("\\n", "\n"))
    opener = "          python - <<'PY'\\n".replace("\\n", "\n")
    closer = "          PY\\n".replace("\\n", "\n")
    start = workflow.index(opener, step) + len(opener)
    end = workflow.index(closer, start)
    lines = workflow[start:end].splitlines()
    if not lines or any(line and not line.startswith("          ") for line in lines):
        raise RuntimeError("repeatability inline writer indentation drift")
    code = "\n".join(line[10:] for line in lines) + "\n"
    compile(code, "<repeatability-inline-diagnostic>", "exec")
    cases = ("existing", "new", "replace", "fsync", "symlink", "parent", "directory", "missing", "bad-sha")
    target_rel = "docs/fixtures/memory-os-operability/controlled-saturation-repeatability-authority-diagnostic.last.json"
    secret = "SYNTHETIC_REPEATABILITY_DIAGNOSTIC_SECRET"
    for case in cases:
        with tempfile.TemporaryDirectory(prefix="repeatability-diagnostic-negative-") as temp:
            root = Path(temp)
            parent = root / "docs/fixtures/memory-os-operability"
            parent.mkdir(parents=True)
            target = root / target_rel
            outside = root / "outside"
            outside.mkdir()
            canary = outside / "canary"
            canary.write_bytes(secret.encode())
            (root / "untrusted.log").write_text(secret, encoding="utf-8")
            if case in ("existing", "replace", "fsync"):
                target.write_bytes(b"before")
                target.chmod(0o640)
            if case == "symlink":
                target.symlink_to(canary)
            if case == "parent":
                parent.rmdir()
                parent.symlink_to(outside, target_is_directory=True)
            if case == "directory":
                target.mkdir()
            if case == "missing":
                parent.rmdir()
            inject = ""
            if case in ("replace", "fsync"):
                inject = "import os\ndef deny(*args): raise OSError('synthetic atomic failure')\nos." + case + " = deny\n"
            env = dict(os.environ, SOURCE_SHA=("invalid" if case == "bad-sha" else "a" * 40),
                       AUTHORITY_EXIT_CODE="23", FAILURE_STAGE="compile")
            result = subprocess.run(
                [sys.executable, "-c", inject + code], cwd=root, env=env,
                capture_output=True, text=True, timeout=10, check=False,
            )
            accepted = case in ("existing", "new")
            if (result.returncode == 0) != accepted:
                raise RuntimeError(f"repeatability inline diagnostic acceptance drift: {case}")
            if secret in result.stdout + result.stderr or canary.read_bytes() != secret.encode():
                raise RuntimeError("repeatability diagnostic leaked secret or changed canary")
            if accepted:
                value = json.loads(target.read_text(encoding="utf-8"))
                if (value.get("output") != "Repeatability authority validation failed; raw validator output withheld."
                    or value.get("containsSecrets") is not False
                    or value.get("productionEvidence") is not False
                    or value.get("productionReady") is not False
                    or value.get("capacityBoundaryEstablished") is not False
                    or value.get("operationalThresholdApproved") is not False
                    or value.get("sourceCommitSha") != "a" * 40
                    or value.get("exitCode") != 23):
                    raise RuntimeError("repeatability diagnostic evidence boundary drift")
                if stat.S_IMODE(target.stat().st_mode) != (0o640 if case == "existing" else 0o600):
                    raise RuntimeError("repeatability diagnostic mode drift")
                if secret in target.read_text(encoding="utf-8"):
                    raise RuntimeError("repeatability diagnostic persisted synthetic secret")
            if case in ("replace", "fsync"):
                if target.read_bytes() != b"before" or stat.S_IMODE(target.stat().st_mode) != 0o640:
                    raise RuntimeError("repeatability diagnostic rollback drift")
            if parent.is_dir() and list(parent.glob(".*.tmp")):
                raise RuntimeError("repeatability diagnostic temp residue")
    print("PASS: repeatability actual inline diagnostic writer redaction/atomic runtime (9 cases)")



def run_inline_ramp_diagnostic_negatives() -> None:
    workflow = (ROOT / ".github/workflows/controlled-saturation-repeatability.yml").read_text(encoding="utf-8")
    if '          cat "$log"' in workflow or "text[-12000:]" in workflow or "path.write_text(" in workflow:
        raise RuntimeError("repeatability ramp workflow retained raw or non-atomic diagnostics")
    marker = "      - name: Record privacy-safe ramp diagnostic\n"
    if workflow.count(marker) != 1:
        raise RuntimeError("repeatability ramp diagnostic step drift")
    step = workflow.index(marker)
    opener, closer = "          python - <<'PY'\n", "          PY\n"
    start = workflow.index(opener, step) + len(opener)
    end = workflow.index(closer, start)
    lines = workflow[start:end].splitlines()
    if not lines or any(line and not line.startswith("          ") for line in lines):
        raise RuntimeError("repeatability ramp inline writer indentation drift")
    code = "\n".join(line[10:] for line in lines) + "\n"
    compile(code, "<repeatability-ramp-inline-diagnostic>", "exec")
    cases = ("existing", "new", "replace", "fsync", "symlink", "parent", "directory", "missing", "bad-sha", "bad-ordinal")
    secret = "SYNTHETIC_REPEATABILITY_RAMP_SECRET"
    for ordinal in ("a", "b"):
        for case in cases:
            with tempfile.TemporaryDirectory(prefix="repeatability-ramp-diagnostic-negative-") as temp:
                root = Path(temp)
                parent = root / "docs/fixtures/memory-os-operability"
                parent.mkdir(parents=True)
                target = parent / f"controlled-saturation-repeatability-diagnostic.{ordinal}.last.json"
                outside = root / "outside"
                outside.mkdir()
                canary = outside / "canary"
                canary.write_bytes(secret.encode())
                if case in ("existing", "replace", "fsync"):
                    target.write_bytes(b"before")
                    target.chmod(0o640)
                if case == "symlink":
                    target.symlink_to(canary)
                if case == "parent":
                    parent.rmdir()
                    parent.symlink_to(outside, target_is_directory=True)
                if case == "directory":
                    target.mkdir()
                if case == "missing":
                    parent.rmdir()
                inject = ""
                if case in ("replace", "fsync"):
                    inject = "import os\ndef deny(*args): raise OSError('synthetic atomic failure')\nos." + case + " = deny\n"
                env = dict(os.environ, ORDINAL=("c" if case == "bad-ordinal" else ordinal),
                           GITHUB_SHA=("invalid" if case == "bad-sha" else "a" * 40),
                           RAMP_EXIT_CODE="125")
                result = subprocess.run(
                    [sys.executable, "-c", inject + code], cwd=root, env=env,
                    capture_output=True, text=True, timeout=10, check=False,
                )
                accepted = case in ("existing", "new")
                if (result.returncode == 0) != accepted:
                    raise RuntimeError(f"repeatability ramp inline diagnostic acceptance drift: {ordinal}/{case}")
                if secret in result.stdout + result.stderr or canary.read_bytes() != secret.encode():
                    raise RuntimeError("repeatability ramp diagnostic leaked secret or changed canary")
                if accepted:
                    value = json.loads(target.read_text(encoding="utf-8"))
                    if (value.get("output") != "Controlled saturation repeatability ramp failed; raw harness output withheld."
                        or value.get("containsSecrets") is not False
                        or value.get("productionEvidence") is not False
                        or value.get("capacityBoundaryEstablished") is not False
                        or value.get("operationalThresholdApproved") is not False
                        or value.get("sourceCommitSha") != "a" * 40
                        or value.get("ordinal") != ordinal
                        or value.get("exitCode") != 125):
                        raise RuntimeError("repeatability ramp diagnostic evidence boundary drift")
                    if stat.S_IMODE(target.stat().st_mode) != (0o640 if case == "existing" else 0o600):
                        raise RuntimeError("repeatability ramp diagnostic mode drift")
                    if secret in target.read_text(encoding="utf-8"):
                        raise RuntimeError("repeatability ramp diagnostic persisted synthetic secret")
                if case in ("replace", "fsync"):
                    if target.read_bytes() != b"before" or stat.S_IMODE(target.stat().st_mode) != 0o640:
                        raise RuntimeError("repeatability ramp diagnostic rollback drift")
                if parent.is_dir() and list(parent.glob(".*.tmp")):
                    raise RuntimeError("repeatability ramp diagnostic temp residue")
    print("PASS: repeatability ramp actual inline diagnostic writer redaction/atomic runtime (20 cases)")



def run_repeatability_source_identity_negatives() -> None:
    workflow = (ROOT / ".github/workflows/controlled-saturation-repeatability.yml").read_text(encoding="utf-8")
    checkout = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
    setup_python = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
    setup_go = "uses: actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5"
    if (workflow.count(checkout) != 2 or workflow.count(setup_python) != 2
        or workflow.count(setup_go) != 1
        or any(floating in workflow for floating in ("checkout@v4", "setup-python@v5", "setup-go@v5"))):
        raise RuntimeError("repeatability immutable Actions source drift")
    def extract(name: str) -> str:
        marker = "      - name: " + name + "\n"
        if workflow.count(marker) != 1:
            raise RuntimeError("repeatability source gate missing or duplicated")
        start = workflow.index("        run: |\n", workflow.index(marker)) + len("        run: |\n")
        # Stop at every YAML step, including unnamed `uses:` steps.
        end = workflow.find("\n      - ", start)
        if end < 0:
            raise RuntimeError("repeatability source gate next-step boundary missing")
        lines = workflow[start:end].splitlines()
        if not lines or any(line and not line.startswith("          ") for line in lines):
            raise RuntimeError("repeatability source gate indentation drift")
        return "\n".join(line[10:] if line else "" for line in lines) + "\n"
    for name in ("Require trusted repeatability ramp source", "Require trusted repeatability aggregate source"):
        script = extract(name)
        for required in ('set -euo pipefail', 'GITHUB_EVENT_NAME', 'GITHUB_REF', 'refs/heads/so',
                         'GITHUB_SHA', 'git rev-parse HEAD', 'git status --porcelain'):
            if required not in script:
                raise RuntimeError("repeatability source gate missing: " + required)
        with tempfile.TemporaryDirectory(prefix="repeatability-source-identity-") as temp:
            root = Path(temp)
            git = root / "git"
            sha = "a" * 40
            git.write_text(
                "#!/bin/sh\n"
                "if [ \"$1\" = \"rev-parse\" ]; then printf '" + sha + "\\n'; exit 0; fi\n"
                "if [ \"$1\" = \"status\" ]; then if [ \"$DIRTY\" = \"1\" ]; then echo ' M dirty'; fi; exit 0; fi\n"
                "if [ \"$1\" = \"fetch\" ]; then exit 0; fi\n"
                "exit 1\n", encoding="utf-8",
            )
            git.chmod(0o755)
            cases = (
                ("push", "refs/heads/so", sha, "0", True),
                ("workflow_dispatch", "refs/heads/so", sha, "0", True),
                ("push", "refs/heads/main", sha, "0", False),
                ("workflow_dispatch", "refs/heads/main", sha, "0", False),
                ("pull_request", "refs/heads/so", sha, "0", False),
                ("push", "refs/heads/so", "A" * 40, "0", False),
                ("push", "refs/heads/so", "", "0", False),
                ("push", "refs/heads/so", "b" * 40, "0", name.endswith("aggregate source")),
                ("push", "refs/heads/so", sha, "1", False),
            )
            for event, ref, event_sha, dirty, allowed in cases:
                env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                           GITHUB_EVENT_NAME=event, GITHUB_REF=ref, GITHUB_SHA=event_sha, DIRTY=dirty)
                result = subprocess.run(
                    ["bash", "-e", "-u", "-o", "pipefail", "-c", script], cwd=root,
                    env=env, capture_output=True, text=True, timeout=10, check=False,
                )
                if (result.returncode == 0) != allowed:
                    raise RuntimeError(f"repeatability source identity regression: {name}/{event}/{ref}")
    print("PASS: repeatability ramp and aggregate immutable source identity shell runtime (18 cases)")



def run_repeatability_authority_identity_negatives() -> None:
    workflow = (ROOT / ".github/workflows/reconcile-controlled-saturation-repeatability-authority.yml").read_text(encoding="utf-8")
    checkout = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
    setup = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
    if (workflow.count(checkout) != 2 or workflow.count(setup) != 2
        or "checkout@v4" in workflow or "setup-python@v5" in workflow):
        raise RuntimeError("repeatability authority immutable Actions drift")
    def extract(name: str) -> str:
        marker = "      - name: " + name + "\n"
        if workflow.count(marker) != 1:
            raise RuntimeError("repeatability authority source step missing")
        start = workflow.index("        run: |\n", workflow.index(marker)) + len("        run: |\n")
        end = workflow.find("\n      - ", start)
        if end < 0:
            raise RuntimeError("repeatability authority source step boundary missing")
        lines = workflow[start:end].splitlines()
        if not lines or any(line and not line.startswith("          ") for line in lines):
            raise RuntimeError("repeatability authority source step indentation drift")
        return "\n".join(line[10:] if line else "" for line in lines) + "\n"
    writer = extract("Capture exact source")
    pr = extract("Confirm exact clean PR source")
    for required in ('GITHUB_EVENT_NAME', 'GITHUB_REF', 'refs/heads/so', 'GITHUB_SHA',
                     'git rev-parse HEAD', 'git status --porcelain'):
        if required not in writer:
            raise RuntimeError("repeatability authority writer identity missing: " + required)
    if 'GITHUB_BASE_REF' not in pr or 'git rev-parse HEAD' not in pr:
        raise RuntimeError("repeatability authority PR base/head guard missing")
    with tempfile.TemporaryDirectory(prefix="repeatability-authority-identity-") as temp:
        root = Path(temp)
        sha = "a" * 40
        git = root / "git"
        git.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = \"rev-parse\" ]; then printf '" + sha + "\\n'; exit 0; fi\n"
            "if [ \"$1\" = \"status\" ]; then if [ \"$DIRTY\" = \"1\" ]; then echo ' M dirty'; fi; exit 0; fi\n"
            "if [ \"$1\" = \"fetch\" ]; then exit 0; fi\n"
            "exit 1\n", encoding="utf-8",
        )
        git.chmod(0o755)
        cases = (
            ("push", "refs/heads/so", sha, "0", True),
            ("workflow_dispatch", "refs/heads/so", sha, "0", True),
            ("push", "refs/heads/main", sha, "0", False),
            ("workflow_dispatch", "refs/heads/main", sha, "0", False),
            ("pull_request", "refs/heads/so", sha, "0", False),
            ("schedule", "refs/heads/so", sha, "0", False),
            ("push", "refs/heads/so", "A" * 40, "0", False),
            ("push", "refs/heads/so", "", "0", False),
            ("push", "refs/heads/so", "b" * 40, "0", False),
            ("push", "refs/heads/so", sha, "1", False),
        )
        for event, ref, event_sha, dirty, allowed in cases:
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_EVENT_NAME=event, GITHUB_REF=ref, GITHUB_SHA=event_sha,
                       GITHUB_ENV=str(root / "github_env"), DIRTY=dirty)
            result = subprocess.run(
                ["bash", "-e", "-u", "-o", "pipefail", "-c", writer.replace("${{ github.event_name }}", event)],
                cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False,
            )
            if (result.returncode == 0) != allowed:
                raise RuntimeError(f"repeatability authority writer identity drift: {event}/{ref}")
        for base, expected, dirty, allowed in (
            ("so", sha, "0", True),
            ("main", sha, "0", False),
            ("so", "b" * 40, "0", False),
            ("so", "A" * 40, "0", False),
            ("so", sha, "1", False),
        ):
            script = pr.replace("${{ github.event.pull_request.head.sha }}", expected)
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_BASE_REF=base, DIRTY=dirty)
            result = subprocess.run(
                ["bash", "-e", "-u", "-o", "pipefail", "-c", script],
                cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False,
            )
            if (result.returncode == 0) != allowed:
                raise RuntimeError("repeatability authority PR base/head identity drift")
    print("PASS: repeatability authority writer and PR exact-source shell runtime (15 cases)")



def run_repeatability_rebase_cas_negatives() -> None:
    workflow = (ROOT / ".github/workflows/controlled-saturation-repeatability.yml").read_text(encoding="utf-8")
    marker = "      - name: Publish append-only repeatability run\n"
    if workflow.count(marker) != 1:
        raise RuntimeError("repeatability CAS publisher missing")
    start = workflow.index("        run: |\n", workflow.index(marker)) + len("        run: |\n")
    end = workflow.find("\n      - ", start)
    if end < 0:
        raise RuntimeError("repeatability CAS publisher boundary missing")
    lines = workflow[start:end].splitlines()
    if not lines or any(line and not line.startswith("          ") for line in lines):
        raise RuntimeError("repeatability CAS publisher indentation drift")
    script = "\n".join(line[10:] if line else "" for line in lines) + "\n"
    def policy(value: str) -> None:
        if value.count("verify_critical_source") != 3:
            raise RuntimeError("repeatability CAS verification multiplicity drift")
        first = value.index("\nverify_critical_source\n")
        rebase = value.index("git pull --rebase origin so")
        second = value.index("\n  verify_critical_source\n", rebase)
        push = value.index("git push origin HEAD:so", rebase)
        if not (first < value.index("git reset --hard origin/so") < rebase < second < push):
            raise RuntimeError("repeatability CAS verification order drift")
        for critical in ("controlled_saturation_ramp_test.go", "live_object_load_test.go",
                         "services/import-api/internal/pgrepo", "services/import-api/internal/upload",
                         "services/import-api/internal/objectstore", "infra/postgresql/security",
                         "controlled-saturation-ramp-contract.v1.json"):
            if critical not in value:
                raise RuntimeError("repeatability critical source coverage drift")
    policy(script)
    for marker in ("\nverify_critical_source\n", "\n  verify_critical_source\n"):
        mutated = script.replace(marker, "\n# removed CAS guard\n", 1)
        try:
            policy(mutated)
        except RuntimeError:
            pass
        else:
            raise RuntimeError("repeatability CAS mutation unexpectedly accepted")
    function_start = script.index("verify_critical_source() {")
    function_end = script.index("\n}", function_start) + 2
    function = script[function_start:function_end]
    with tempfile.TemporaryDirectory(prefix="repeatability-cas-negative-") as temp:
        root = Path(temp)
        git = root / "git"
        git.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = \"fetch\" ]; then exit \"$FETCH_CODE\"; fi\n"
            "if [ \"$1\" = \"diff\" ]; then exit \"$DIFF_CODE\"; fi\n"
            "exit 1\n", encoding="utf-8",
        )
        git.chmod(0o755)
        code = "set -euo pipefail\nsource_sha=" + ("a" * 40) + "\ncritical=(test)\n" + function + "\nverify_critical_source\n"
        for fetch_code, diff_code, allowed in (("0", "0", True), ("0", "1", False), ("23", "0", False)):
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       FETCH_CODE=fetch_code, DIFF_CODE=diff_code)
            result = subprocess.run(
                ["bash", "-e", "-u", "-o", "pipefail", "-c", code], cwd=root, env=env,
                capture_output=True, text=True, timeout=10, check=False,
            )
            if (result.returncode == 0) != allowed:
                raise RuntimeError("repeatability critical-source CAS runtime drift")
    print("PASS: repeatability post-rebase critical source CAS and negative mutations (5 cases)")



def run_authority_path_negatives(module) -> None:
    module.require_exact_authority(module.CONTRACT, module.CONTRACT, "repeatability contract")
    with tempfile.TemporaryDirectory(prefix="repeatability-authority-path-") as temp:
        root = Path(temp)
        outside = root / "outside"
        outside.mkdir()
        canary = outside / "canary.json"
        canary.write_bytes(b"SYNTHETIC_AUTHORITY_CANARY")
        linked = root / "linked"
        linked.symlink_to(outside, target_is_directory=True)
        for candidate in (linked / "canary.json", canary, root / "missing.json"):
            try:
                module.require_exact_authority(candidate, candidate, "synthetic")
            except module.Fail:
                pass
            else:
                raise RuntimeError("repeatability authority accepted symlink/escape/missing path")
        if canary.read_bytes() != b"SYNTHETIC_AUTHORITY_CANARY":
            raise RuntimeError("repeatability authority path negative changed canary")
    print("PASS: repeatability authority ancestor symlink/repository escape negatives (3 cases)")



def run_repeatability_runref_path_negatives() -> None:
    validator_path = ROOT / "scripts/validate-memory-os-controlled-saturation-repeatability.py"
    source = validator_path.read_text(encoding="utf-8")
    if 'run_path = safe_repo_ref(ref, "runRef")' not in source or 'run = load(run_path)' not in source:
        raise RuntimeError("repeatability runRef did not use canonical safe path resolver")
    spec = importlib.util.spec_from_file_location("repeatability_validator_path_negative", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("repeatability validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    good = "contracts/operations/controlled-saturation-repeatability-contract.v1.json"
    if validator.safe_repo_ref(good, "test") != ROOT / good:
        raise RuntimeError("canonical repeatability reference rejected")
    with tempfile.TemporaryDirectory(prefix="repeatability-external-ref-") as outside_temp:
        outside = Path(outside_temp)
        canary = outside / "canary.json"
        canary.write_bytes(b"SYNTHETIC_REPEATABILITY_REF_CANARY")
        with tempfile.TemporaryDirectory(prefix=".repeatability-ref-negative-", dir=ROOT) as inside_temp:
            inside = Path(inside_temp)
            linked_file = inside / "linked.json"
            linked_file.symlink_to(canary)
            linked_parent = inside / "linked-parent"
            linked_parent.symlink_to(outside, target_is_directory=True)
            refs = (
                linked_file.relative_to(ROOT).as_posix(),
                (linked_parent / "canary.json").relative_to(ROOT).as_posix(),
                "../external.json",
                str(canary),
                (inside / "missing.json").relative_to(ROOT).as_posix(),
            )
            for ref in refs:
                try:
                    validator.safe_repo_ref(ref, "runRef")
                except validator.Fail:
                    pass
                else:
                    raise RuntimeError("repeatability unsafe runRef accepted")
        if canary.read_bytes() != b"SYNTHETIC_REPEATABILITY_REF_CANARY":
            raise RuntimeError("repeatability runRef negative changed external canary")
    print("PASS: repeatability runRef symlink/ancestor/traversal/absolute/missing negatives (5 cases)")



def run_repeatability_matrix_boundary_negatives() -> None:
    validator_path = ROOT / "scripts/validate-memory-os-controlled-saturation-repeatability.py"
    spec = importlib.util.spec_from_file_location("repeatability_matrix_negative", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("repeatability matrix validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    original_load = validator.load
    result = original_load(validator.RESULT)
    a_ref, b_ref = result["runRefs"]
    run_a = original_load(ROOT / a_ref)
    run_b = original_load(ROOT / b_ref)
    with contextlib.redirect_stdout(io.StringIO()):
        if validator.main() != 0:
            raise RuntimeError("canonical repeatability matrix positive control failed")
    cases = (
        ("swapped ordinals", {"runRefs": [b_ref, a_ref]}, None),
        ("different run id", {"runRefs": [a_ref, b_ref.replace("repeat-31157504019-", "repeat-999999-")]}, None),
        ("different attempt", {"runRefs": [a_ref, b_ref.replace("-1-b.v1.json", "-2-b.v1.json")]}, None),
        ("invalid path", {"runRefs": [a_ref, "docs/fixtures/memory-os-operability/invalid.json"]}, None),
        ("non-string ref", {"runRefs": [a_ref, {"path": b_ref}]}, None),
        ("non-synthetic run", {}, ("environment", "syntheticDataOnly", False)),
        ("non-loopback run", {}, ("environment", "loopbackDependenciesOnly", False)),
        ("secret-bearing run", {}, ("environment", "containsSecrets", True)),
        ("run schema drift", {}, ("schemaVersion", None, "invalid")),
        ("run result failure", {}, ("scenario", "result", "FAIL")),
        ("run integrity failure", {}, ("scenario", "integrityResult", "FAIL")),
    )
    for label, result_override, run_override in cases:
        fixture_result = copy.deepcopy(result)
        fixture_result.update(result_override)
        fixture_b = copy.deepcopy(run_b)
        if run_override is not None:
            section, field, value = run_override
            if field is None:
                fixture_b[section] = value
            else:
                fixture_b[section][field] = value
        def fake_load(path):
            if path == validator.RESULT:
                return fixture_result
            if path == ROOT / a_ref:
                return copy.deepcopy(run_a)
            if path == ROOT / b_ref:
                return fixture_b
            return original_load(path)
        validator.load = fake_load
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    validator.main()
                except validator.Fail:
                    pass
                else:
                    raise RuntimeError(f"repeatability matrix boundary accepted: {label}")
        finally:
            validator.load = original_load
    for label, field, value in (
        ("a", "kind", "ACTUAL_FAILURE_SIGNAL"),
        ("a", "throughputGainFromPrevious", 0.0),
        ("b", "p95LatencyRatioFromPrevious", 9.0),
    ):
        fixture = copy.deepcopy(result)
        fixture["signals"][label][field] = value
        validator.load = lambda path: fixture if path == validator.RESULT else original_load(path)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    validator.main()
                except validator.Fail:
                    pass
                else:
                    raise RuntimeError("repeatability validator accepted tampered analyzer signal")
        finally:
            validator.load = original_load
    print("PASS: repeatability matrix provenance/integrity and signal recomputation negatives (14 cases)")



def run_repeatability_nonfinite_negatives() -> None:
    workflow = (ROOT / ".github/workflows/reconcile-controlled-saturation-repeatability-authority.yml").read_text(encoding="utf-8")
    for path in ("scripts/analyze-memory-os-controlled-saturation-repeatability.py",
                 "scripts/validate-memory-os-controlled-saturation-repeatability.py",
                 "scripts/validate-memory-os-controlled-saturation-repeatability-reconcile-negative.py"):
        trigger = '      - "' + path + '"'
        if workflow.count(trigger) != 2:
            raise RuntimeError("repeatability numeric source CI trigger drift: " + path)
        if workflow.replace(trigger, "# removed numeric trigger", 1).count(trigger) == 2:
            raise RuntimeError("repeatability numeric source trigger negative failed")
    def imported(name, path):
        spec = importlib.util.spec_from_file_location(name, ROOT / path)
        if spec is None or spec.loader is None:
            raise RuntimeError("repeatability numeric source import failed")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    analyzer = imported("repeatability_numeric_analyzer", "scripts/analyze-memory-os-controlled-saturation-repeatability.py")
    validator = imported("repeatability_numeric_validator", "scripts/validate-memory-os-controlled-saturation-repeatability.py")
    result = validator.load(validator.RESULT)
    run = analyzer.load(ROOT / result["runRefs"][0])
    if analyzer.signal_for(run)["concurrency"] is None:
        raise RuntimeError("repeatability numeric analyzer positive control failed")
    for field in ("result", "integrityResult"):
        fixture = copy.deepcopy(run)
        fixture["scenario"][field] = "FAIL"
        try:
            analyzer.signal_for(fixture)
        except analyzer.Fail:
            pass
        else:
            raise RuntimeError("repeatability analyzer accepted failed run or integrity")
    with contextlib.redirect_stdout(io.StringIO()):
        if validator.main() != 0:
            raise RuntimeError("repeatability numeric validator positive control failed")
    for section, field, value in (
        ("batch", "throughput", float("inf")),
        ("batch", "latencyP95Ms", float("inf")),
        ("batch", "throughput", 10 ** 500),
        ("poolDelta", "emptyAcquireCount", True),
    ):
        fixture = copy.deepcopy(run)
        fixture["scenario"]["steps"][1][section][field] = value
        try:
            analyzer.signal_for(fixture)
        except analyzer.Fail:
            pass
        else:
            raise RuntimeError("repeatability analyzer accepted nonfinite/invalid metric")
    with tempfile.TemporaryDirectory(prefix="repeatability-nonfinite-json-", dir=ROOT) as temp:
        path = Path(temp) / "numeric.json"
        for raw in ('{"value": Infinity}', '{"value": 1e999}'):
            path.write_text(raw, encoding="utf-8")
            for module in (analyzer, validator):
                try:
                    module.load(path)
                except module.Fail:
                    pass
                else:
                    raise RuntimeError("repeatability parser accepted nonfinite JSON")
    original_load = validator.load
    for label, mutate in (
        ("infinite throughput gain", lambda doc: doc["signals"]["a"].update({"throughputGainFromPrevious": float("inf")})),
        ("infinite p95 ratio", lambda doc: doc["signals"]["b"].update({"p95LatencyRatioFromPrevious": float("inf")})),
        ("signal kind mismatch", lambda doc: doc["signals"]["a"].update({"kind": "NO_SIGNAL"})),
    ):
        fixture = copy.deepcopy(result)
        mutate(fixture)
        validator.load = lambda path: fixture if path == validator.RESULT else original_load(path)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    validator.main()
                except validator.Fail:
                    pass
                else:
                    raise RuntimeError(f"repeatability validator accepted {label}")
        finally:
            validator.load = original_load
    print("PASS: repeatability analyzer/validator nonfinite, integrity and signal negatives (13 cases)")



def run_repeatability_analyzer_matrix_producer_negatives() -> None:
    analyzer_path = ROOT / "scripts/analyze-memory-os-controlled-saturation-repeatability.py"
    spec = importlib.util.spec_from_file_location("repeatability_matrix_producer_negative", analyzer_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("repeatability matrix producer import failed")
    analyzer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analyzer)
    result = json.loads(analyzer.OUTPUT.read_text(encoding="utf-8"))
    a_ref, b_ref = result["runRefs"]
    a_path, b_path = ROOT / a_ref, ROOT / b_ref
    analyzer.require_matrix_pair(a_path, b_path)
    for label, first, second in (
        ("reversed ordinals", b_path, a_path),
        ("same ordinal", a_path, a_path),
        ("different run", a_path, ROOT / b_ref.replace("repeat-31157504019-", "repeat-999999-")),
        ("different attempt", a_path, ROOT / b_ref.replace("-1-b.v1.json", "-2-b.v1.json")),
        ("arbitrary filename", a_path, ROOT / "docs/fixtures/memory-os-operability/unrelated.json"),
    ):
        try:
            analyzer.require_matrix_pair(first, second)
        except analyzer.Fail:
            pass
        else:
            raise RuntimeError(f"repeatability analyzer accepted {label}")
    original_load = analyzer.load
    original_write = analyzer.atomic_write_bytes
    original_argv = sys.argv
    run_a, run_b = original_load(a_path), original_load(b_path)
    captured = []
    current = {"a": run_a, "b": run_b}

    def fixture_load(path):
        if path == a_path:
            return copy.deepcopy(current["a"])
        if path == b_path:
            return copy.deepcopy(current["b"])
        return original_load(path)

    analyzer.load = fixture_load
    analyzer.atomic_write_bytes = lambda path, payload: captured.append((path, payload))
    sys.argv = [str(analyzer_path), "--run-a", a_ref, "--run-b", b_ref]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            if analyzer.main() != 0:
                raise RuntimeError("repeatability analyzer matrix positive control failed")
        if len(captured) != 1 or captured[0][0] != analyzer.CANONICAL_OUTPUT:
            raise RuntimeError("repeatability analyzer positive output binding drift")
        for label, bad_sha in (
            ("nonhex SHA", "g" * 40),
            ("uppercase SHA", "A" * 40),
            ("short SHA", "a" * 39),
            ("nonstring SHA", True),
        ):
            current["a"] = copy.deepcopy(run_a)
            current["b"] = copy.deepcopy(run_b)
            current["a"]["commitSha"] = bad_sha
            current["b"]["commitSha"] = bad_sha
            captured.clear()
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    analyzer.main()
                except analyzer.Fail:
                    pass
                else:
                    raise RuntimeError(f"repeatability analyzer accepted {label}")
            if captured:
                raise RuntimeError("repeatability analyzer wrote result after invalid source SHA")
    finally:
        analyzer.load = original_load
        analyzer.atomic_write_bytes = original_write
        sys.argv = original_argv
    print("PASS: repeatability analyzer matrix producer and source SHA negatives (9 cases)")


def run_repeatability_analyzer_path_atomic_negatives() -> None:
    analyzer_path = ROOT / "scripts/analyze-memory-os-controlled-saturation-repeatability.py"
    spec = importlib.util.spec_from_file_location("repeatability_analyzer_atomic_negative", analyzer_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("repeatability analyzer atomic import failed")
    analyzer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analyzer)
    result = json.loads(analyzer.OUTPUT.read_text(encoding="utf-8"))
    a_ref, b_ref = result["runRefs"]
    if analyzer.safe_run_path(a_ref) != ROOT / a_ref:
        raise RuntimeError("repeatability analyzer rejected canonical run")
    with tempfile.TemporaryDirectory(prefix="repeatability-analyzer-outside-") as outside_temp:
        outside = Path(outside_temp)
        canary = outside / "canary.json"
        canary.write_bytes(b"SYNTHETIC_ANALYZER_CANARY")
        with tempfile.TemporaryDirectory(prefix=".repeatability-analyzer-negative-", dir=ROOT) as inside_temp:
            inside = Path(inside_temp)
            linked = inside / "linked.json"
            linked.symlink_to(canary)
            parent_link = inside / "parent-link"
            parent_link.symlink_to(outside, target_is_directory=True)
            for ref in (
                linked.relative_to(ROOT).as_posix(),
                (parent_link / "canary.json").relative_to(ROOT).as_posix(),
                str(canary),
                "../outside.json",
                (inside / "missing.json").relative_to(ROOT).as_posix(),
            ):
                try:
                    analyzer.safe_run_path(ref)
                except analyzer.Fail:
                    pass
                else:
                    raise RuntimeError("repeatability analyzer accepted unsafe run path")
            target = inside / "result.json"
            target.write_bytes(b"original")
            target.chmod(0o640)
            analyzer.atomic_write_bytes(target, b"updated")
            if target.read_bytes() != b"updated" or stat.S_IMODE(target.stat().st_mode) != 0o640:
                raise RuntimeError("repeatability analyzer existing atomic mode drift")
            new = inside / "new.json"
            analyzer.atomic_write_bytes(new, b"new")
            if new.read_bytes() != b"new" or stat.S_IMODE(new.stat().st_mode) != 0o644:
                raise RuntimeError("repeatability analyzer new atomic mode drift")
            directory = inside / "directory"
            directory.mkdir()
            for unsafe in (linked, parent_link / "write.json", directory, inside / "missing" / "write.json", canary):
                try:
                    analyzer.atomic_write_bytes(unsafe, b"forbidden")
                except analyzer.Fail:
                    pass
                else:
                    raise RuntimeError("repeatability analyzer accepted unsafe atomic path")
            for operation in ("replace", "fsync"):
                original = getattr(analyzer.os, operation)
                setattr(analyzer.os, operation, lambda *args: (_ for _ in ()).throw(OSError("synthetic failure")))
                try:
                    try:
                        analyzer.atomic_write_bytes(target, b"forbidden")
                    except OSError:
                        pass
                    else:
                        raise RuntimeError("repeatability analyzer accepted atomic failure")
                finally:
                    setattr(analyzer.os, operation, original)
                if target.read_bytes() != b"updated" or list(inside.glob(".result.json.*.tmp")):
                    raise RuntimeError("repeatability analyzer atomic rollback/residue drift")
            original_output = analyzer.OUTPUT
            original_argv = sys.argv
            analyzer.OUTPUT = canary
            sys.argv = [str(analyzer_path), "--run-a", a_ref, "--run-b", b_ref]
            try:
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        analyzer.main()
                except analyzer.Fail:
                    pass
                else:
                    raise RuntimeError("repeatability analyzer accepted output authority substitution")
            finally:
                analyzer.OUTPUT = original_output
                sys.argv = original_argv
        if canary.read_bytes() != b"SYNTHETIC_ANALYZER_CANARY":
            raise RuntimeError("repeatability analyzer changed outside canary")
    print("PASS: repeatability analyzer run-path/atomic/output authority negatives (14 cases)")



def run_repeatability_contract_policy_negatives() -> None:
    validator_path = ROOT / "scripts/validate-memory-os-controlled-saturation-repeatability.py"
    spec = importlib.util.spec_from_file_location("repeatability_contract_policy_negative", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("repeatability policy validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    original_load = validator.load
    contract = original_load(validator.CONTRACT)
    with contextlib.redirect_stdout(io.StringIO()):
        if validator.main() != 0:
            raise RuntimeError("repeatability policy positive control failed")
    cases = []
    for field in ("independentGitHubHostedRunner", "independentPostgreSQLService", "independentMinIOService",
                  "sameExactSourceCommit", "syntheticDataOnly"):
        cases.append(("requiredRunBoundaries", field, False))
    for field in ("productionTraffic", "productionCredentials", "productionEvidence", "productionEquivalentDependencies"):
        cases.append(("requiredRunBoundaries", field, True))
    for field in ("actualFailureSignalTakesPrecedence", "degradationKneeRequiresPoolContention",
                  "singleRunPromotionForbidden", "missingSignalFailsClosed"):
        cases.append(("signalPolicy", field, False))
    cases.append(("signalPolicy", "poolContentionAloneIsSignal", True))
    cases.append(("promotionBoundary", "repeatableLocalDegradationSignalMayBecomeTrue", False))
    for field in ("capacityBoundaryEstablished", "operationalThresholdApproved",
                  "independentReviewCompleted", "productionReady"):
        cases.append(("readiness", field, True))
    for section, field, value in cases:
        fixture = copy.deepcopy(contract)
        fixture[section][field] = value
        validator.load = lambda path: fixture if path == validator.CONTRACT else original_load(path)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    validator.main()
                except validator.Fail:
                    pass
                else:
                    raise RuntimeError(f"repeatability policy weakening accepted: {section}.{field}")
        finally:
            validator.load = original_load
    print(f"PASS: repeatability required run-boundary/signal-policy/readiness negatives ({len(cases)} cases)")


def main() -> int:
    module = load_module()
    run_authority_substitutions(module)
    run_authority_path_negatives(module)
    run_repeatability_runref_path_negatives()
    run_repeatability_matrix_boundary_negatives()
    run_repeatability_contract_policy_negatives()
    run_repeatability_nonfinite_negatives()
    run_repeatability_analyzer_matrix_producer_negatives()
    run_repeatability_analyzer_path_atomic_negatives()
    run_prewrite_failure(module)
    run_postwrite_failure(module)
    run_atomic_replace_failure(module)
    run_validator_output_negative(module)
    run_atomic_path_negative(module)
    run_rollback_secret_negative(module)
    run_stronger_readiness_negatives(module)
    run_inline_diagnostic_writer_negatives()
    run_inline_ramp_diagnostic_negatives()
    run_repeatability_source_identity_negatives()
    run_repeatability_authority_identity_negatives()
    run_repeatability_rebase_cas_negatives()
    print("Memory OS controlled saturation repeatability reconcile negative PASS")
    print("authority substitution plus pre-write/post-write/atomic failures are fail-closed")
    print("temporary authority residue: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
