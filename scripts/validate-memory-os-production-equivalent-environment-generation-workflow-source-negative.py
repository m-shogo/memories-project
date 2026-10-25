#!/usr/bin/env python3
"""Negative and runtime proof for environment generation CI source trust."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/production-equivalent-environment-generation.yml"
INDEPENDENT = ".github/workflows/production-equivalent-environment-generation-source-negative.yml"
SELF = "scripts/validate-memory-os-production-equivalent-environment-generation-workflow-source-negative.py"
PUBLISHER_SHA = "0f3afcb9eddab9f8d5c8cce44c58ae5266ac2af4"
INDEPENDENT_SHA = "8622b888b020e075df415c91f144e9eef7939c62"
D = chr(36)
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
PR_BASE = 'test "' + D + '{GITHUB_BASE_REF:-}" = "so"'
WRITER_REF = 'test "' + D + '{GITHUB_REF:-}" = "refs/heads/so"'
PR_EVENT = 'test "' + D + '{GITHUB_EVENT_NAME:-}" = "pull_request"'
WRITER_EVENT = '[[ "' + D + '{GITHUB_EVENT_NAME:-}" == "push" || "' + D + '{GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]'
SHA_FORMAT = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
REDACTION = "'output': 'REDACTED: environment generation validation failed; raw output withheld',"
SUPPRESS = 'printf "Environment generation validation exit code: %s (raw validator log suppressed)\\n" "$code"'
WRITER_SCOPE = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n"
PR_CHECKOUT = 'ref: ' + D + '{{ github.event.pull_request.head.sha }}'
WRITER_CHECKOUT = 'ref: ' + D + '{{ github.sha }}'

PUBLISHER_REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n", 1),
    ("publisher trigger", '      - "' + PUBLISHER + '"\n', 2),
    ("independent trigger", '      - "' + INDEPENDENT + '"\n', 2),
    ("validator trigger", '      - "' + SELF + '"\n', 2),
    ("checkout pin", CHECKOUT, 2),
    ("setup pin", SETUP, 2),
    ("PR no credentials", "          persist-credentials: false\n", 1),
    ("writer credentials", "          persist-credentials: true\n", 1),
    ("PR base", PR_BASE, 1),
    ("PR event", PR_EVENT, 1),
    ("writer event", WRITER_EVENT, 1),
    ("writer branch", WRITER_REF, 1),
    ("SHA format", SHA_FORMAT, 2),
    ("source self check", "          python " + SELF + "\n", 2),
    ("writer scope", WRITER_SCOPE, 1),
    ("writer token", "      contents: write\n", 1),
    ("root read token", "permissions:\n  contents: read\n", 1),
    ("PR read token", "      contents: read\n", 1),
    ("checkout PR head", PR_CHECKOUT, 1),
    ("checkout writer head", WRITER_CHECKOUT, 1),
    ("HEAD identity", 'test "$(git rev-parse HEAD)" = "$expected"', 2),
    ("redacted diagnostic", REDACTION, 1),
    ("suppressed CI log", SUPPRESS, 1),
    ("no raw tail", "text[-12000:]", 0),
    ("no raw CI log", '          cat "$log"\n', 0),
)
INDEPENDENT_REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n", 1),
    ("publisher trigger", '      - "' + PUBLISHER + '"\n', 2),
    ("independent trigger", '      - "' + INDEPENDENT + '"\n', 2),
    ("validator trigger", '      - "' + SELF + '"\n', 2),
    ("checkout pin", CHECKOUT, 1),
    ("setup pin", SETUP, 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("PR base", PR_BASE, 1),
    ("push branch", WRITER_REF, 1),
    ("SHA format", SHA_FORMAT, 1),
    ("self execution", "          python " + SELF + "\n", 1),
    ("read permissions", "  contents: read\n", 2),
    ("source job scope", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", 1),
    ("clean source", '          test -z "$(git status --porcelain)"\n', 2),
)


def read(relative: str) -> str:
    path = ROOT / relative
    try:
        if not path.is_file() or path.is_symlink():
            raise ValueError("not a regular file")
        if path.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != relative:
            raise ValueError("escaped repository root")
        return path.read_text(encoding="utf-8")
    except (OSError, ValueError, RuntimeError, UnicodeError) as exc:
        raise SystemExit("environment generation source missing/substituted: " + relative) from exc


def validate(publisher: str, independent: str) -> None:
    for name, source, required, reviewed in (
        ("publisher", publisher, PUBLISHER_REQUIRED, PUBLISHER_SHA),
        ("independent", independent, INDEPENDENT_REQUIRED, INDEPENDENT_SHA),
    ):
        for label, token, count in required:
            if source.count(token) != count:
                raise SystemExit("environment generation " + name + " source drift: " + label)
        data = source.encode("utf-8")
        digest = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
        if digest != reviewed:
            raise SystemExit("environment generation " + name + " complete source drift")


def runtime(publisher: str, independent: str) -> None:
    for name, source in (("publisher", publisher), ("independent", independent)):
        for label, token, key, value, allow in (
            ("base so", PR_BASE, "GITHUB_BASE_REF", "so", True),
            ("base main", PR_BASE, "GITHUB_BASE_REF", "main", False),
            ("base empty", PR_BASE, "GITHUB_BASE_REF", "", False),
            ("ref so", WRITER_REF, "GITHUB_REF", "refs/heads/so", True),
            ("ref main", WRITER_REF, "GITHUB_REF", "refs/heads/main", False),
            ("ref tag", WRITER_REF, "GITHUB_REF", "refs/tags/v1", False),
        ):
            if source.count(token) != 1:
                raise SystemExit("environment generation unreachable runtime branch: " + name + " " + label)
            result = subprocess.run(["bash", "-e", "-c", token], env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}, capture_output=True, check=False)
            if (result.returncode == 0) != allow:
                raise SystemExit("environment generation branch runtime drift: " + name + " " + label)
    for token, allowed in ((PR_EVENT, ("pull_request",)), (WRITER_EVENT, ("push", "workflow_dispatch"))):
        for event in ("pull_request", "push", "workflow_dispatch", "", "schedule"):
            result = subprocess.run(["bash", "-e", "-c", token], env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GITHUB_EVENT_NAME": event}, capture_output=True, check=False)
            if (result.returncode == 0) != (event in allowed):
                raise SystemExit("environment generation event runtime drift: " + event)
    for value, allow in (("a" * 40, True), ("0" * 40, True), ("A" * 40, False), ("g" * 40, False), ("a" * 39, False), ("a" * 41, False), ("", False), ("$(echo bad)", False)):
        result = subprocess.run(["bash", "-e", "-c", 'expected="' + D + '{PROBE_SHA:-}"\n' + SHA_FORMAT],
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PROBE_SHA": value}, capture_output=True, check=False)
        if (result.returncode == 0) != allow:
            raise SystemExit("environment generation SHA runtime drift: " + value[:10])
    print("PASS: environment generation branch/event/SHA runtime (30 cases)")


def diagnostic_runtime(publisher: str) -> None:
    start, end = "          python - <<'PY'\n", "          PY\n"
    if publisher.count(start) != 1 or publisher.count(end) != 1:
        raise SystemExit("environment generation diagnostic writer not unique")
    inline = publisher.split(start, 1)[1].split(end, 1)[0]
    script = "\n".join(line[10:] for line in inline.splitlines()) + "\n"
    with tempfile.TemporaryDirectory(prefix="environment-generation-diagnostic-") as directory:
        env = os.environ.copy()
        env.update({"SOURCE_SHA": "e" * 40, "VALIDATION_EXIT_CODE": "23", "SENSITIVE_CANARY": "CANARY_DO_NOT_PERSIST_ENVIRONMENT"})
        result = subprocess.run([sys.executable, "-c", script], cwd=directory, env=env, capture_output=True, text=True, check=False)
        if result.returncode:
            raise SystemExit("environment generation isolated diagnostic failed: " + result.stderr[:500])
        output = Path(directory) / "docs/fixtures/memory-os-operability/production-equivalent-environment-generation-diagnostic.last.json"
        raw = output.read_text(encoding="utf-8")
        value = json.loads(raw)
        if value.get("output") != "REDACTED: environment generation validation failed; raw output withheld":
            raise SystemExit("environment generation diagnostic persisted raw validator output")
        if value.get("sourceCommitSha") != "e" * 40 or value.get("exitCode") != 23:
            raise SystemExit("environment generation diagnostic source/exit binding drift")
        if value.get("containsSecrets") is not False or value.get("productionEvidence") is not False or value.get("productionReady") is not False:
            raise SystemExit("environment generation diagnostic evidence/readiness flag drift")
        if value.get("generationCreated") is not False or value.get("preflightEligibilityFabricated") is not False or "CANARY_DO_NOT_PERSIST_ENVIRONMENT" in raw:
            raise SystemExit("environment generation diagnostic fabricated evidence or persisted canary")
        output.chmod(0o640)
        positive = subprocess.run([sys.executable, "-c", script], cwd=directory, env=env,
                                  capture_output=True, text=True, timeout=15, check=False)
        if positive.returncode or stat.S_IMODE(output.stat().st_mode) != 0o640:
            raise SystemExit("environment generation diagnostic failed to preserve existing file mode")
        previous = output.read_bytes()
        for label, before in (("replace", "os.replace(tmp_name, path)"),
                              ("fsync", "os.fsync(handle.fileno())")):
            if script.count(before) != 1:
                raise SystemExit("environment generation diagnostic failure fixture anchor drift: " + label)
            failure = subprocess.run([sys.executable, "-c", script.replace(
                before, "raise OSError('synthetic environment diagnostic " + label + " failure')", 1)],
                cwd=directory, env=env, capture_output=True, text=True, timeout=15, check=False)
            if failure.returncode == 0 or "synthetic environment diagnostic " + label + " failure" not in failure.stderr:
                raise SystemExit("environment generation diagnostic intended failure not reached: " + label)
            if output.read_bytes() != previous or stat.S_IMODE(output.stat().st_mode) != 0o640:
                raise SystemExit("environment generation diagnostic failed atomic rollback: " + label)
            if list(output.parent.glob(".production-equivalent-environment-generation-diagnostic.last.json.*.tmp")):
                raise SystemExit("environment generation diagnostic left temporary file: " + label)
        outside = Path(directory) / "external-environment-diagnostic-canary"
        outside.write_bytes(previous)
        output.unlink()
        output.symlink_to(outside)
        symlink = subprocess.run([sys.executable, "-c", script], cwd=directory, env=env,
                                 capture_output=True, text=True, timeout=15, check=False)
        if symlink.returncode == 0 or "target must not be a symlink" not in symlink.stderr:
            raise SystemExit("environment generation diagnostic followed symlink destination")
        if not output.is_symlink() or outside.read_bytes() != previous:
            raise SystemExit("environment generation diagnostic altered external symlink canary")
        if list(output.parent.glob(".production-equivalent-environment-generation-diagnostic.last.json.*.tmp")):
            raise SystemExit("environment generation diagnostic symlink rejection left temporary file")
    print("PASS: environment generation diagnostic redaction/atomic runtime (5 cases)")


def negatives(publisher: str, independent: str) -> None:
    publisher_cases = (
        ("PR branch", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("publisher trigger", '      - "' + PUBLISHER + '"\n', ""),
        ("independent trigger", '      - "' + INDEPENDENT + '"\n', ""),
        ("validator trigger", '      - "' + SELF + '"\n', ""),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("PR credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("writer credentials", "          persist-credentials: true\n", ""),
        ("PR base", PR_BASE, "true"),
        ("writer branch", WRITER_REF, "true"),
        ("writer event", WRITER_EVENT, "true"),
        ("PR event", PR_EVENT, "true"),
        ("SHA format", SHA_FORMAT, 'test -n "$expected"'),
        ("broad writer job", WRITER_SCOPE, "    if: github.event_name != 'pull_request'\n"),
        ("self check", "          python " + SELF + "\n", ""),
        ("checkout PR", PR_CHECKOUT, WRITER_CHECKOUT),
        ("checkout writer", WRITER_CHECKOUT, 'ref: ' + D + '{{ github.ref }}'),
        ("raw diagnostic", REDACTION, "'output': Path('/tmp/production-equivalent-environment-generation.log').read_text(),"),
        ("raw CI echo", SUPPRESS, 'cat "$log"'),
        ("symlink guard", "          if path.is_symlink():\n              raise SystemExit('environment generation diagnostic target must not be a symlink')\n", ""),
        ("unreviewed Action", "      - name: Capture exact generation authority source\n", "      - uses: unreviewed/action@v1\n      - name: Capture exact generation authority source\n"),
        ("unreviewed shell", "      - name: Capture exact generation authority source\n", "      - run: echo unreviewed\n      - name: Capture exact generation authority source\n"),
    )
    independent_cases = (
        ("PR target", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("publisher trigger", '      - "' + PUBLISHER + '"\n', ""),
        ("independent trigger", '      - "' + INDEPENDENT + '"\n', ""),
        ("validator trigger", '      - "' + SELF + '"\n', ""),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("persist credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("PR base", PR_BASE, "true"),
        ("push branch", WRITER_REF, "true"),
        ("SHA format", SHA_FORMAT, 'test -n "$expected"'),
        ("self execution", "          python " + SELF + "\n", ""),
        ("unreviewed Action", "      - name: Prove environment generation publisher source\n", "      - uses: unreviewed/action@v1\n      - name: Prove environment generation publisher source\n"),
        ("unreviewed shell", "      - name: Prove environment generation publisher source\n", "      - run: echo unreviewed\n      - name: Prove environment generation publisher source\n"),
    )
    for name, original, cases in (("publisher", publisher, publisher_cases), ("independent", independent, independent_cases)):
        for label, before, after in cases:
            if before not in original:
                raise SystemExit("environment generation negative fixture missing: " + name + " " + label)
            mutated = original.replace(before, after, 1)
            if mutated == original:
                raise SystemExit("environment generation negative fixture unchanged: " + name + " " + label)
            try:
                validate(mutated, independent) if name == "publisher" else validate(publisher, mutated)
            except SystemExit:
                continue
            raise SystemExit("environment generation accepted source mutation: " + name + " " + label)
    print(f"PASS: environment generation source negatives ({len(publisher_cases)} publisher, {len(independent_cases)} independent)")


def main() -> int:
    publisher = read(PUBLISHER)
    independent = read(INDEPENDENT)
    validate(publisher, independent)
    runtime(publisher, independent)
    diagnostic_runtime(publisher)
    negatives(publisher, independent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
