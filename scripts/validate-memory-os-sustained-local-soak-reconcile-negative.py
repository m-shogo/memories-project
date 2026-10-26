#!/usr/bin/env python3
"""Prove sustained-soak authority identity and multi-authority rollback are fail-closed."""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-sustained-local-soak-status.py"
AGGREGATE_UPDATER = ROOT / "scripts/update-memory-os-sustained-local-soak-aggregate.py"
TREND_REVIEWER = ROOT / "scripts/review-memory-os-sustained-local-soak-trends.py"
AGGREGATE_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak-aggregate.py"
WORKFLOW = ROOT / ".github/workflows/reconcile-sustained-local-soak-authority.yml"
MAIN_WORKFLOW = ROOT / ".github/workflows/sustained-local-soak.yml"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_reconciler():
    return load_module(RECONCILER, "memory_os_sustained_local_soak_reconciler")


def load_aggregate_updater():
    return load_module(AGGREGATE_UPDATER, "memory_os_sustained_local_soak_aggregate_updater")


def load_trend_reviewer():
    return load_module(TREND_REVIEWER, "memory_os_sustained_local_soak_trend_reviewer")


def file_mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def expect_authority_rejection(module, attr: str, replacement: Path) -> None:
    original = getattr(module, attr)
    setattr(module, attr, replacement)
    try:
        try:
            module.enforce_runtime_authorities()
        except module.Fail:
            pass
        else:
            raise AssertionError(f"{attr} substitution must be rejected")
    finally:
        setattr(module, attr, original)


def extract_workflow_step(text: str, start_marker: str, end_marker: str, label: str) -> str:
    if start_marker not in text:
        raise AssertionError(f"{label} diagnostic step missing")
    section = text.split(start_marker, 1)[1]
    if end_marker not in section:
        raise AssertionError(f"{label} diagnostic step boundary missing")
    return section.split(end_marker, 1)[0]


def validate_atomic_diagnostic_text(
    text: str,
    label: str,
    *,
    require_mode_preservation: bool = False,
) -> None:
    required = [
        "tempfile.mkstemp(",
        "dir=path.parent",
        "handle.flush()",
        "os.fsync(handle.fileno())",
        "os.replace(tmp_name, path)",
        "os.unlink(tmp_name)",
    ]
    if require_mode_preservation:
        required.extend(
            [
                "stat.S_IMODE(path.stat().st_mode)",
                "if path.exists() else None",
                "os.fchmod(fd, existing_mode)",
            ]
        )
    missing = [fragment for fragment in required if fragment not in text]
    if missing:
        raise AssertionError(f"{label} diagnostic is not crash-safe: missing {missing}")
    if "path.write_text(json.dumps(value" in text:
        raise AssertionError(f"{label} diagnostic regressed to direct write_text")


def validate_atomic_diagnostic_workflow(
    path: Path,
    label: str,
    *,
    require_mode_preservation: bool = False,
) -> None:
    if not path.is_file():
        raise AssertionError(f"{label} workflow missing")
    validate_atomic_diagnostic_text(
        path.read_text(encoding="utf-8"),
        label,
        require_mode_preservation=require_mode_preservation,
    )


def validate_atomic_writer(module, path: Path, label: str) -> None:
    original = path.read_bytes()
    original_mode = file_mode(path)
    temp_glob = f".{path.name}.*.tmp"
    before = {candidate.name for candidate in path.parent.glob(temp_glob)}
    real_replace = module.os.replace

    def fail_replace(_source, _destination) -> None:
        raise OSError("synthetic atomic replace failure")

    module.os.replace = fail_replace
    try:
        try:
            module.atomic_replace_bytes(path, original + b"\n")
        except OSError as exc:
            if "synthetic atomic replace failure" not in str(exc):
                raise AssertionError(f"unexpected atomic write failure: {exc}") from exc
        else:
            raise AssertionError(f"{label} atomic writer unexpectedly succeeded after replace failure")
    finally:
        module.os.replace = real_replace

    if path.read_bytes() != original:
        raise AssertionError(f"atomic replace failure changed canonical {label}")
    if file_mode(path) != original_mode:
        raise AssertionError(f"atomic replace failure changed canonical {label} mode")
    after = {candidate.name for candidate in path.parent.glob(temp_glob)}
    if after != before:
        raise AssertionError(f"atomic replace failure leaked temporary {label} authority")


def validate_mode_preserving_success(module, path: Path, label: str) -> None:
    original = path.read_bytes()
    original_mode = file_mode(path)
    test_mode = 0o640
    path.chmod(test_mode)
    try:
        module.atomic_replace_bytes(path, original)
        if path.read_bytes() != original:
            raise AssertionError(f"successful atomic replacement changed canonical {label} bytes")
        if file_mode(path) != test_mode:
            raise AssertionError(f"successful atomic replacement changed canonical {label} mode")
    finally:
        path.chmod(original_mode)
        if path.read_bytes() != original:
            module.atomic_replace_bytes(path, original, original_mode)


def validate_second_replace_transaction_rollback(module, paths: tuple[Path, ...]) -> None:
    original = {
        path: (path.read_bytes(), file_mode(path))
        for path in paths
    }
    temp_before = {
        path: {candidate.name for candidate in path.parent.glob(f".{path.name}.*.tmp")}
        for path in paths
    }
    contract = module.load(module.CONTRACT_PATH)
    load_contract = module.load(module.LOAD_PATH)
    status = module.load(module.STATUS_PATH)
    contract["_syntheticTransactionProbe"] = True

    real_replace = module.os.replace
    replace_count = 0

    def fail_second_replace(source, destination) -> None:
        nonlocal replace_count
        replace_count += 1
        if replace_count == 2:
            raise OSError("synthetic second authority replace failure")
        real_replace(source, destination)

    module.os.replace = fail_second_replace
    try:
        try:
            module.write_and_validate_transactionally(contract, load_contract, status)
        except OSError as exc:
            if "synthetic second authority replace failure" not in str(exc):
                raise AssertionError(f"unexpected multi-authority write failure: {exc}") from exc
        else:
            raise AssertionError("multi-authority transaction unexpectedly succeeded after second replace failure")
    finally:
        module.os.replace = real_replace

    if replace_count < 2:
        raise AssertionError("synthetic second authority replace failure was not reached")
    for path in paths:
        original_bytes, original_mode = original[path]
        if path.read_bytes() != original_bytes:
            raise AssertionError(f"second-replace rollback changed canonical authority: {path.relative_to(ROOT)}")
        if file_mode(path) != original_mode:
            raise AssertionError(f"second-replace rollback changed canonical authority mode: {path.relative_to(ROOT)}")
        temp_after = {candidate.name for candidate in path.parent.glob(f".{path.name}.*.tmp")}
        if temp_after != temp_before[path]:
            raise AssertionError(f"second-replace rollback leaked temporary authority: {path.relative_to(ROOT)}")


def validate_result_json_parser_negatives() -> None:
    """Exercise both canonical local-soak readers against ambiguous JSON."""
    readers = (
        load_module(
            ROOT / "scripts/validate-memory-os-sustained-local-soak-result.py",
            "memory_os_sustained_local_soak_result_json_negative",
        ),
        load_module(
            ROOT / "scripts/validate-memory-os-sustained-local-soak.py",
            "memory_os_sustained_local_soak_contract_json_negative",
        ),
    )
    with tempfile.TemporaryDirectory(prefix=".sustained-local-soak-result-json-", dir=ROOT) as temp:
        path = Path(temp) / "result.json"
        path.write_text('{"outer":{"a":1,"b":2}}', encoding="utf-8")
        for reader in readers:
            if reader.load(path) != {"outer": {"a": 1, "b": 2}}:
                raise AssertionError("sustained local-soak JSON positive control failed")
        cases = (
            b'{"value":Infinity}',
            b'{"value":NaN}',
            b'{"value":1e999}',
            b'{"a":1,"a":2}',
            b'{"outer":{"a":1,"a":2}}',
            b'{"SYNTHETIC_SECRET_CANARY":',
            b'{"huge":' + b"9" * 5000 + b"}",
            b"\xff\xfe",
        )
        for payload in cases:
            path.write_bytes(payload)
            for reader in readers:
                try:
                    reader.load(path)
                except reader.Fail as exc:
                    if "SYNTHETIC_SECRET_CANARY" in str(exc):
                        raise AssertionError("sustained local-soak JSON diagnostic leaked source")
                else:
                    raise AssertionError("sustained local-soak parser accepted malformed JSON")
    print("PASS: sustained local-soak result/contract JSON positives and 16 parser negatives")

def validate_result_numeric_overflow_negatives() -> None:
    """Reject finite inputs that overflow while deriving local-only soak trends."""
    validator = load_module(
        ROOT / "scripts/validate-memory-os-sustained-local-soak-result.py",
        "memory_os_sustained_local_soak_numeric_negative",
    )
    if validator.number(1.5, "positive") != 1.5:
        raise AssertionError("sustained local-soak numeric positive drift")
    observations = [{"elapsedSeconds": 0}, {"elapsedSeconds": 60}]
    if validator.slope(observations, lambda row: row["elapsedSeconds"]) != 60.0:
        raise AssertionError("sustained local-soak slope positive drift")
    validator.close(1.0, 1.0, "positive")
    for label, action in (
        ("huge integer conversion", lambda: validator.number(10 ** 500, "huge")),
        ("nonfinite numeric", lambda: validator.number(float("inf"), "infinite")),
        ("boolean numeric", lambda: validator.number(True, "boolean")),
        ("nonfinite slope", lambda: validator.slope(observations, lambda row: 0.0 if row["elapsedSeconds"] == 0 else 1e308)),
        ("infinite expected slope", lambda: validator.close(1.0, float("inf"), "infinite-expected")),
        ("NaN expected slope", lambda: validator.close(1.0, float("nan"), "nan-expected")),
    ):
        try:
            action()
        except validator.Fail:
            pass
        else:
            raise AssertionError("sustained local-soak numeric validator accepted " + label)
    print("PASS: sustained local-soak numeric/slope positives and 6 overflow negatives")


def validate_cross_run_delta_nonfinite_negatives() -> None:
    """Exercise producer and consumer against finite inputs yielding infinite deltas."""
    producer = load_trend_reviewer()
    consumer = load_module(
        ROOT / "scripts/validate-memory-os-sustained-local-soak-trend-review.py",
        "memory_os_sustained_local_soak_trend_delta_negative",
    )
    if producer.pair_delta({"metric": 2.0}, {"metric": 5.0}, "metric") != 3.0:
        raise AssertionError("sustained local-soak producer delta positive drift")
    if consumer.bounded_delta(2.0, 5.0, "metric") != 3.0:
        raise AssertionError("sustained local-soak consumer delta positive drift")
    for label, left, right in (
        ("derived infinity", -1e308, 1e308),
        ("input infinity", 1.0, float("inf")),
        ("huge integer conversion", 1.0, 10 ** 500),
    ):
        for operation in (
            lambda a=left, b=right: producer.pair_delta({"metric": a}, {"metric": b}, "metric"),
            lambda a=left, b=right: consumer.bounded_delta(a, b, "metric"),
        ):
            try:
                operation()
            except (producer.Fail, consumer.Fail):
                pass
            else:
                raise AssertionError("sustained local-soak cross-run delta accepted " + label)
    print("PASS: sustained local-soak cross-run delta positives and 6 finite negatives")


def validate_trend_json_parser_negatives() -> None:
    """Exercise both real cross-run trend readers on ambiguous JSON inputs."""
    producer = load_trend_reviewer()
    consumer = load_module(
        ROOT / "scripts/validate-memory-os-sustained-local-soak-trend-review.py",
        "memory_os_sustained_local_soak_trend_json_negative",
    )
    with tempfile.TemporaryDirectory(prefix=".sustained-local-soak-trend-json-", dir=ROOT) as temp:
        path = Path(temp) / "trend.json"
        path.write_text('{"outer":{"a":1,"b":2}}', encoding="utf-8")
        for reader in (producer, consumer):
            if reader.load(path) != {"outer": {"a": 1, "b": 2}}:
                raise AssertionError("sustained local-soak trend JSON positive control failed")
        cases = (
            b'{"value":Infinity}',
            b'{"value":NaN}',
            b'{"value":1e999}',
            b'{"a":1,"a":2}',
            b'{"outer":{"a":1,"a":2}}',
            b'{"SYNTHETIC_SECRET_CANARY":',
            b'{"huge":' + b"9" * 5000 + b"}",
            b"\xff\xfe",
        )
        for payload in cases:
            path.write_bytes(payload)
            for reader in (producer, consumer):
                try:
                    reader.load(path)
                except reader.Fail as exc:
                    if "SYNTHETIC_SECRET_CANARY" in str(exc):
                        raise AssertionError("sustained local-soak trend JSON diagnostic leaked source")
                else:
                    raise AssertionError("sustained local-soak trend parser accepted malformed JSON")
    print("PASS: sustained local-soak trend producer/consumer positives and 16 JSON negatives")


def validate_aggregate_admission_negatives() -> None:
    """Exercise actual aggregate consumer JSON, arithmetic and child-output boundaries."""
    validator = load_module(AGGREGATE_VALIDATOR, "memory_os_sustained_soak_aggregate_negative")
    with tempfile.TemporaryDirectory(prefix=".sustained-soak-aggregate-json-", dir=ROOT) as temp:
        path = Path(temp) / "aggregate.json"
        path.write_text('{"outer":{"a":1,"b":2}}', encoding="utf-8")
        if validator.load(path) != {"outer": {"a": 1, "b": 2}}:
            raise AssertionError("aggregate JSON positive control failed")
        cases = (
            b'{"value":Infinity}',
            b'{"value":NaN}',
            b'{"value":1e999}',
            b'{"a":1,"a":2}',
            b'{"outer":{"a":1,"a":2}}',
            b'{"SYNTHETIC_SECRET_CANARY":',
            b'{"huge":' + b"9" * 5000 + b"}",
            b"\xff\xfe",
        )
        for payload in cases:
            path.write_bytes(payload)
            try:
                validator.load(path)
            except validator.Fail as exc:
                if "SYNTHETIC_SECRET_CANARY" in str(exc):
                    raise AssertionError("aggregate JSON diagnostic leaked source")
            else:
                raise AssertionError("aggregate accepted ambiguous or invalid JSON")
    if validator.finite_number(2.0, "positive") != 2.0:
        raise AssertionError("aggregate finite numeric positive drift")
    if validator.pair_delta({"metric": 2.0}, {"metric": 5.0}, "metric") != 3.0:
        raise AssertionError("aggregate delta positive drift")
    for label, action in (
        ("huge numeric", lambda: validator.finite_number(10 ** 500, "huge")),
        ("infinite numeric", lambda: validator.finite_number(float("inf"), "infinite")),
        ("boolean numeric", lambda: validator.finite_number(True, "boolean")),
        ("derived infinite delta", lambda: validator.pair_delta({"metric": -1e308}, {"metric": 1e308}, "metric")),
        ("infinite delta input", lambda: validator.pair_delta({"metric": 1.0}, {"metric": float("inf")}, "metric")),
        ("huge delta input", lambda: validator.pair_delta({"metric": 1.0}, {"metric": 10 ** 500}, "metric")),
    ):
        try:
            action()
        except validator.Fail:
            pass
        else:
            raise AssertionError("aggregate numeric boundary accepted " + label)
    original_run = validator.subprocess.run

    class SyntheticChildResult:
        returncode = 17
        stdout = "SYNTHETIC_SECRET_CANARY"
        stderr = "SYNTHETIC_SECRET_CANARY"

    try:
        validator.subprocess.run = lambda *args, **kwargs: SyntheticChildResult()
        try:
            validator.run_validator(["synthetic"], "aggregate child")
        except validator.Fail as exc:
            if "SYNTHETIC_SECRET_CANARY" in str(exc) or "exit 17" not in str(exc):
                raise AssertionError("aggregate child diagnostic leaked or lost exit code")
        else:
            raise AssertionError("aggregate child failure accepted")
    finally:
        validator.subprocess.run = original_run
    print("PASS: aggregate reader 8 JSON, 6 numeric and 1 child-output negatives")


def validate_aggregate_updater_admission_negatives() -> None:
    """Exercise actual aggregate producer's strict input and secret-safe child transport."""
    updater = load_aggregate_updater()
    with tempfile.TemporaryDirectory(prefix=".sustained-soak-updater-json-", dir=ROOT) as temp:
        path = Path(temp) / "updater.json"
        path.write_text('{"outer":{"a":1,"b":2}}', encoding="utf-8")
        if updater.load(path) != {"outer": {"a": 1, "b": 2}}:
            raise AssertionError("aggregate updater JSON positive control failed")
        cases = (
            b'{"value":Infinity}',
            b'{"value":NaN}',
            b'{"value":1e999}',
            b'{"a":1,"a":2}',
            b'{"outer":{"a":1,"a":2}}',
            b'{"SYNTHETIC_SECRET_CANARY":',
            b'{"huge":' + b"9" * 5000 + b"}",
            b"\xff\xfe",
        )
        for payload in cases:
            path.write_bytes(payload)
            try:
                updater.load(path)
            except updater.Fail as exc:
                if "SYNTHETIC_SECRET_CANARY" in str(exc):
                    raise AssertionError("aggregate updater JSON diagnostic leaked source")
            else:
                raise AssertionError("aggregate updater accepted invalid JSON")
        if updater.finite_number(2.0, "positive") != 2.0:
            raise AssertionError("aggregate updater numeric positive drift")
        for label, value in (
            ("huge integer", 10 ** 500),
            ("nonfinite", float("inf")),
            ("boolean", True),
        ):
            try:
                updater.finite_number(value, label)
            except updater.Fail:
                pass
            else:
                raise AssertionError("aggregate updater accepted " + label)
        original_run = updater.subprocess.run

        class SyntheticChildResult:
            returncode = 29
            stdout = "SYNTHETIC_SECRET_CANARY"
            stderr = "SYNTHETIC_SECRET_CANARY"

        try:
            updater.subprocess.run = lambda *args, **kwargs: SyntheticChildResult()
            try:
                updater.validate(path, updater.RESULT_VALIDATOR)
            except updater.Fail as exc:
                if "SYNTHETIC_SECRET_CANARY" in str(exc) or "exit 29" not in str(exc):
                    raise AssertionError("aggregate updater child diagnostic leaked or lost exit code")
            else:
                raise AssertionError("aggregate updater child failure accepted")
        finally:
            updater.subprocess.run = original_run
    print("PASS: aggregate updater 8 JSON, 3 numeric and 1 child-output negatives")


def validate_reconcile_diagnostic_runtime() -> None:
    """Run the actual workflow inline writer only inside disposable synthetic directories."""
    workflow = WORKFLOW.read_text(encoding="utf-8")
    section = extract_workflow_step(
        workflow,
        "      - name: Record privacy-safe diagnostic\n",
        "      - name: Enforce authority success\n",
        "sustained soak reconciliation",
    )
    for fragment in (
        "'output': 'Validation failed; consult the exact-source workflow run.'",
        "failure_stage not in allowed_stages",
        "any(candidate.is_symlink() for candidate in (path, *path.parents))",
        "path.parent.resolve(strict=True) != repo / 'docs/fixtures/memory-os-operability'",
        "path.exists() and not path.is_file()",
        "os.replace(tmp_name, path)",
    ):
        if fragment not in section:
            raise AssertionError("sustained soak diagnostic guard missing: " + fragment)
    for forbidden in ("text[-12000:]", "re.sub(", "authority.log').read_text", "path.parent.mkdir("):
        if forbidden in section:
            raise AssertionError("sustained soak diagnostic raw-log/path regression: " + forbidden)
    marker = "          python - <<'PY'\n"
    if section.count(marker) != 1 or section.count("\n          PY\n") != 1:
        raise AssertionError("sustained soak inline diagnostic Python boundary drift")
    code = textwrap.dedent(section.split(marker, 1)[1].split("\n          PY\n", 1)[0]) + "\n"
    with tempfile.TemporaryDirectory(prefix=".sustained-soak-diagnostic-runtime-", dir=ROOT) as temp:
        root = Path(temp)
        target = root / "docs/fixtures/memory-os-operability/sustained-local-soak-authority-diagnostic.last.json"
        target.parent.mkdir(parents=True)
        env = dict(os.environ, SOURCE_SHA="a" * 40, EXIT_CODE="17", FAILURE_STAGE="SYNTHETIC_SECRET_CANARY")

        def execute(script: str):
            return subprocess.run(
                [sys.executable, "-c", script], cwd=root, env=env,
                capture_output=True, text=True, check=False,
            )

        success = execute(code)
        if success.returncode != 0:
            raise AssertionError("synthetic diagnostic writer failed: " + success.stderr[-300:])
        document = json.loads(target.read_text(encoding="utf-8"))
        if (document.get("output") != "Validation failed; consult the exact-source workflow run."
                or document.get("failureStage") != "unknown"
                or document.get("exitCode") != 17
                or document.get("containsSecrets") is not False
                or document.get("productionEvidence") is not False
                or "SYNTHETIC_SECRET_CANARY" in target.read_text(encoding="utf-8")):
            raise AssertionError("synthetic diagnostic payload is unsafe")
        target.chmod(0o640)
        success = execute(code)
        if success.returncode != 0 or stat.S_IMODE(target.stat().st_mode) != 0o640:
            raise AssertionError("diagnostic writer failed mode-preserving success")
        original = target.read_bytes()
        before = list(target.parent.glob(f".{target.name}.*.tmp"))
        failing_code = (
            "import os\n"
            "def fail_replace(*args): raise OSError('synthetic replace failure')\n"
            "os.replace = fail_replace\n" + code
        )
        failed = execute(failing_code)
        if (failed.returncode == 0 or target.read_bytes() != original
                or stat.S_IMODE(target.stat().st_mode) != 0o640
                or list(target.parent.glob(f".{target.name}.*.tmp")) != before):
            raise AssertionError("diagnostic atomic replace rollback failed")
        target.unlink()
        external = root / "external-canary.txt"
        external.write_text("EXTERNAL_CANARY", encoding="utf-8")
        target.symlink_to(external)
        rejected = execute(code)
        if rejected.returncode == 0 or external.read_text(encoding="utf-8") != "EXTERNAL_CANARY":
            raise AssertionError("diagnostic writer followed symlink target")
        target.unlink()
        target.parent.rmdir()
        outside = root / "outside"
        outside.mkdir()
        target.parent.symlink_to(outside, target_is_directory=True)
        rejected = execute(code)
        if rejected.returncode == 0 or list(outside.iterdir()):
            raise AssertionError("diagnostic writer followed symlink ancestor")
    print("PASS: sustained soak diagnostic fixed-output, mode, rollback and symlink runtime negatives")


def validate_trend_child_output_privacy() -> None:
    """Reject secret-bearing child output and malformed timestamps at both trend boundaries."""
    producer = load_trend_reviewer()
    consumer = load_module(
        ROOT / "scripts/validate-memory-os-sustained-local-soak-trend-review.py",
        "memory_os_sustained_local_soak_trend_privacy_negative",
    )

    class SyntheticChildResult:
        returncode = 19
        stdout = "SYNTHETIC_SECRET_CANARY"
        stderr = "SYNTHETIC_SECRET_CANARY"

    for module, method in (
        (producer, producer.summarize_run),
        (consumer, consumer.validate_run),
    ):
        original_run = module.subprocess.run
        original_path_guard = module.require_local_run_path
        try:
            module.require_local_run_path = lambda path: None  # Isolate child-output failure.
            module.subprocess.run = lambda *args, **kwargs: SyntheticChildResult()
            try:
                method(ROOT / "docs/fixtures/memory-os-operability/synthetic-run.json")
            except module.Fail as exc:
                if "SYNTHETIC_SECRET_CANARY" in str(exc) or "exit 19" not in str(exc):
                    raise AssertionError("trend child output leaked or lost exit code")
            else:
                raise AssertionError("trend child failure accepted")
        finally:
            module.subprocess.run = original_run
            module.require_local_run_path = original_path_guard
        for valid in ("2026-10-26T11:00:00Z", "2026-10-26T11:00:00.123456789Z"):
            positive = module.utc_timestamp(valid, "positive")
            if positive.year != 2026:
                raise AssertionError("trend UTC timestamp positive control failed")
        for invalid in (
            "2026-10-26 11:00:00Z",
            "2026-10-26T11:00Z",
            "2026-W44-1T11:00:00Z",
            "2026-02-30T11:00:00Z",
            "2026-10-26T11:00:00+00:00",
            "2026-10-26T11:00:00.1234567890Z",
            "SYNTHETIC_SECRET_CANARYZ",
        ):
            try:
                module.utc_timestamp(invalid, "synthetic")
            except module.Fail as exc:
                if "SYNTHETIC_SECRET_CANARY" in str(exc):
                    raise AssertionError("trend timestamp diagnostic leaked raw value")
            else:
                raise AssertionError("trend malformed timestamp accepted")
    print("PASS: trend producer/consumer child-output and 14 strict timestamp negatives")


def validate_status_reconciler_admission_negatives() -> None:
    """Test actual status reconciler JSON, child transport and serialization boundaries."""
    module = load_reconciler()
    with tempfile.TemporaryDirectory(prefix=".sustained-soak-status-json-", dir=ROOT) as temp:
        path = Path(temp) / "status.json"
        path.write_text('{"outer":{"a":1,"b":2}}', encoding="utf-8")
        if module.load(path) != {"outer": {"a": 1, "b": 2}}:
            raise AssertionError("status JSON positive control failed")
        cases = (
            b'{"value":Infinity}',
            b'{"value":NaN}',
            b'{"value":1e999}',
            b'{"a":1,"a":2}',
            b'{"outer":{"a":1,"a":2}}',
            b'{"SYNTHETIC_SECRET_CANARY":',
            b'{"huge":' + b"9" * 5000 + b"}",
            b"\xff\xfe",
        )
        for payload in cases:
            path.write_bytes(payload)
            try:
                module.load(path)
            except module.Fail as exc:
                if "SYNTHETIC_SECRET_CANARY" in str(exc):
                    raise AssertionError("status JSON diagnostic leaked source")
            else:
                raise AssertionError("status reconciler accepted ambiguous JSON")
        original_run = module.subprocess.run

        class SyntheticChildResult:
            returncode = 31
            stdout = "SYNTHETIC_SECRET_CANARY"
            stderr = "SYNTHETIC_SECRET_CANARY"

        try:
            module.subprocess.run = lambda *args, **kwargs: SyntheticChildResult()
            try:
                module.run_validator(module.SOAK_VALIDATOR, "synthetic child")
            except module.Fail as exc:
                if "SYNTHETIC_SECRET_CANARY" in str(exc) or "exit 31" not in str(exc):
                    raise AssertionError("status child failure leaked or lost exit code")
            else:
                raise AssertionError("status child failure accepted")
        finally:
            module.subprocess.run = original_run
        try:
            module.write(path, {"nonfinite": float("inf")})
        except ValueError:
            if path.read_bytes() != cases[-1]:
                raise AssertionError("nonfinite status serialization mutated target")
        else:
            raise AssertionError("status writer serialized nonfinite JSON")
    print("PASS: status reconciler 8 JSON, 1 child-output and 1 serialization negatives")


def validate_trend_run_path_negatives() -> None:
    """Prove both real trend consumers reject symlink, missing and escaped run files."""
    producer = load_trend_reviewer()
    consumer = load_module(
        ROOT / "scripts/validate-memory-os-sustained-local-soak-trend-review.py",
        "memory_os_sustained_local_soak_run_path_negative",
    )
    for module in (producer, consumer):
        with tempfile.TemporaryDirectory(prefix=".sustained-soak-run-path-", dir=ROOT) as temp:
            directory = Path(temp) / "runs"
            directory.mkdir()
            outside = Path(temp) / "external-canary.json"
            outside.write_text("EXTERNAL_CANARY", encoding="utf-8")
            good = directory / "good.json"
            good.write_text("{}", encoding="utf-8")
            original_dir = module.RESULT_DIR
            module.RESULT_DIR = directory
            try:
                module.require_local_run_path(good)
                bad_link = directory / "link.json"
                bad_link.symlink_to(outside)
                for label, path in (
                    ("symlink target", bad_link),
                    ("wrong parent", outside),
                    ("missing", directory / "missing.json"),
                    ("directory target", directory),
                ):
                    try:
                        module.require_local_run_path(path)
                    except module.Fail:
                        pass
                    else:
                        raise AssertionError("trend run path accepted " + label)
                if outside.read_text(encoding="utf-8") != "EXTERNAL_CANARY":
                    raise AssertionError("trend run path changed external canary")
            finally:
                module.RESULT_DIR = original_dir
    print("PASS: trend producer/consumer canonical run path positives and 8 path negatives")


def main() -> int:
    validate_trend_run_path_negatives()
    validate_status_reconciler_admission_negatives()
    validate_trend_child_output_privacy()
    validate_reconcile_diagnostic_runtime()
    validate_aggregate_updater_admission_negatives()
    validate_aggregate_admission_negatives()
    validate_trend_json_parser_negatives()
    validate_cross_run_delta_nonfinite_negatives()
    validate_result_json_parser_negatives()
    validate_result_numeric_overflow_negatives()
    module = load_reconciler()
    updater = load_aggregate_updater()
    reviewer = load_trend_reviewer()
    validate_atomic_diagnostic_workflow(
        WORKFLOW,
        "sustained soak authority",
        require_mode_preservation=True,
    )

    if not MAIN_WORKFLOW.is_file():
        raise AssertionError("sustained soak execution workflow missing")
    main_workflow = MAIN_WORKFLOW.read_text(encoding="utf-8")
    smoke_diagnostic = extract_workflow_step(
        main_workflow,
        "      - name: Record privacy-safe smoke diagnostic\n",
        "      - name: Enforce foundation smoke\n",
        "sustained soak smoke",
    )
    long_run_diagnostic = extract_workflow_step(
        main_workflow,
        "      - name: Record privacy-safe long-run diagnostic\n",
        "      - name: Enforce long-run success\n",
        "sustained soak long-run",
    )
    validate_atomic_diagnostic_text(
        smoke_diagnostic,
        "sustained soak smoke",
        require_mode_preservation=True,
    )
    validate_atomic_diagnostic_text(
        long_run_diagnostic,
        "sustained soak long-run",
        require_mode_preservation=True,
    )

    validate_atomic_writer(module, module.CONTRACT_PATH, "sustained-soak contract")
    validate_mode_preserving_success(module, module.CONTRACT_PATH, "sustained-soak contract")
    validate_atomic_writer(updater, updater.AGGREGATE_PATH, "sustained-soak aggregate")
    validate_mode_preserving_success(updater, updater.AGGREGATE_PATH, "sustained-soak aggregate")
    validate_atomic_writer(reviewer, reviewer.REVIEW_PATH, "sustained-soak trend review")
    validate_mode_preserving_success(reviewer, reviewer.REVIEW_PATH, "sustained-soak trend review")

    expect_authority_rejection(updater, "RESULT_DIR", updater.ROOT / "docs")
    expect_authority_rejection(updater, "AGGREGATE_PATH", updater.CONTRACT_PATH)
    expect_authority_rejection(updater, "REVIEW_PATH", updater.CONTRACT_PATH)
    expect_authority_rejection(updater, "CONTRACT_PATH", updater.AGGREGATE_PATH)
    expect_authority_rejection(updater, "RESULT_VALIDATOR", updater.REVIEW_VALIDATOR)
    expect_authority_rejection(updater, "REVIEW_VALIDATOR", updater.RESULT_VALIDATOR)

    expect_authority_rejection(reviewer, "RESULT_DIR", reviewer.ROOT / "docs")
    expect_authority_rejection(reviewer, "CONTRACT_PATH", reviewer.REVIEW_PATH)
    expect_authority_rejection(reviewer, "RESULT_VALIDATOR", reviewer.CONTRACT_PATH)
    expect_authority_rejection(reviewer, "REVIEW_PATH", reviewer.CONTRACT_PATH)

    paths = (module.CONTRACT_PATH, module.LOAD_PATH, module.STATUS_PATH)
    original = {
        path: (path.read_bytes(), file_mode(path))
        for path in paths
    }

    expect_authority_rejection(module, "CONTRACT_PATH", module.LOAD_PATH)
    expect_authority_rejection(module, "LOAD_PATH", module.STATUS_PATH)
    expect_authority_rejection(module, "STATUS_PATH", module.CONTRACT_PATH)
    expect_authority_rejection(module, "RESULT_DIR", module.ROOT / "docs")
    expect_authority_rejection(module, "AGGREGATE_PATH", module.CONTRACT_PATH)
    expect_authority_rejection(module, "REVIEW_PATH", module.LOAD_PATH)
    expect_authority_rejection(module, "AGGREGATE_VALIDATOR", module.SOAK_VALIDATOR)
    expect_authority_rejection(module, "INDEPENDENT_REVIEW_VALIDATOR", module.LOAD_VALIDATOR)
    expect_authority_rejection(module, "SOAK_VALIDATOR", module.LOAD_VALIDATOR)
    expect_authority_rejection(module, "LOAD_VALIDATOR", module.SOAK_VALIDATOR)
    expect_authority_rejection(module, "OPERABILITY_VALIDATOR", module.SOAK_VALIDATOR)

    for path in paths:
        original_bytes, original_mode = original[path]
        if path.read_bytes() != original_bytes:
            raise AssertionError(f"authority substitution changed canonical bytes: {path.relative_to(ROOT)}")
        if file_mode(path) != original_mode:
            raise AssertionError(f"authority substitution changed canonical mode: {path.relative_to(ROOT)}")

    validate_second_replace_transaction_rollback(module, paths)

    observed_post_write_failure = False
    real_run_validator = module.run_validator

    def controlled_validator(path: Path, label: str, *args: str) -> None:
        nonlocal observed_post_write_failure
        if label == "post-write operability validator":
            observed_post_write_failure = True
            raise module.Fail("synthetic post-write operability validation failure")
        real_run_validator(path, label, *args)

    module.run_validator = controlled_validator
    try:
        try:
            module.main()
        except module.Fail as exc:
            if "synthetic post-write operability validation failure" not in str(exc):
                raise AssertionError(f"unexpected reconcile failure: {exc}") from exc
        else:
            raise AssertionError("reconcile unexpectedly succeeded after synthetic post-write failure")

        if not observed_post_write_failure:
            raise AssertionError("synthetic post-write validator was not reached")
        for path in paths:
            original_bytes, original_mode = original[path]
            if path.read_bytes() != original_bytes:
                raise AssertionError(f"reconcile rollback changed canonical authority: {path.relative_to(ROOT)}")
            if file_mode(path) != original_mode:
                raise AssertionError(f"reconcile rollback changed canonical authority mode: {path.relative_to(ROOT)}")
    finally:
        module.run_validator = real_run_validator
        for path in paths:
            original_bytes, original_mode = original[path]
            if path.read_bytes() != original_bytes or file_mode(path) != original_mode:
                module.atomic_replace_bytes(path, original_bytes, original_mode)

    print("PASS: sustained local soak authority, smoke, and long-run diagnostics are independently atomic and mode-preserving")
    print("PASS: sustained local soak reconciler, aggregate updater and trend reviewer reject authority substitution")
    print("PASS: sustained local soak atomic replacement failure preserves canonical authority bytes and mode")
    print("PASS: sustained local soak derived authority writers preserve existing mode")
    print("PASS: sustained local soak second-replace failure rolls back all canonical authority bytes and modes")
    print("PASS: sustained local soak reconcile rollback preserves canonical authority bytes and mode")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
