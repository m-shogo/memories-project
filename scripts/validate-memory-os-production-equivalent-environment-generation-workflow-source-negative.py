#!/usr/bin/env python3
"""Negative and runtime proof for environment generation CI source trust."""

from __future__ import annotations

import ast
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

PUBLISHER_TRIGGER_PATHS = (
    ".github/workflows/production-equivalent-environment-generation.yml",
    ".github/workflows/production-equivalent-environment-generation-source-negative.yml",
    "scripts/validate-memory-os-production-equivalent-environment-generation-workflow-source-negative.py",
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/production-equivalent-environment-record.v1.schema.json",
    "contracts/operations/production-equivalent-environment-generation-record.v1.schema.json",
    "contracts/operations/production-operability-status.json",
    "scripts/memory_os_environment_generation_eligibility.py",
    "scripts/validate-memory-os-environment-generation-eligibility-negative.py",
    "scripts/validate-memory-os-production-equivalent-environment-record.py",
    "scripts/register-memory-os-production-equivalent-environment-generation.py",
    "scripts/validate-memory-os-production-equivalent-environment-generation.py",
    "scripts/validate-memory-os-production-equivalent-environment-generation-negative.py",
    "scripts/validate-memory-os-production-equivalent-environment-generation-source-binding-negative.py",
    "scripts/validate-memory-os-production-equivalent-environment-generation-lineage-negative.py",
    "scripts/validate-memory-os-production-equivalent-environment-generation-authority-path-negative.py",
    "scripts/validate-memory-os-production-equivalent-environment-generation-append-rollback-negative.py",
    "scripts/validate-memory-os-production-equivalent-generation-reconcile-negative.py",
    "scripts/reconcile-memory-os-production-equivalent-generation-status.py",
    "scripts/validate-memory-os-operability.py",
)
INDEPENDENT_TRIGGER_PATHS = (
    ".github/workflows/production-equivalent-environment-generation.yml",
    ".github/workflows/production-equivalent-environment-generation-source-negative.yml",
    "scripts/validate-memory-os-production-equivalent-environment-generation-workflow-source-negative.py",
)
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
    ("diagnostic symlink rejection", "          if path.is_symlink():\n              raise SystemExit('environment generation diagnostic target must not be a symlink')\n", 1),
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



def validate_trigger_reachability(
    content: str, kind: str, *, trigger_paths: tuple[str, ...] | None = None
) -> None:
    """Require exact ordered event trigger paths without the whole-workflow digest."""
    if kind == "publisher":
        canonical = PUBLISHER_TRIGGER_PATHS
        end_marker = "  workflow_dispatch:\n"
    elif kind == "independent":
        canonical = INDEPENDENT_TRIGGER_PATHS
        end_marker = "\npermissions:\n"
    else:
        raise SystemExit("environment generation unrecognized CI trigger kind")
    if trigger_paths is None:
        trigger_paths = canonical
    if len(trigger_paths) != len(canonical) or len(set(trigger_paths)) != len(canonical):
        raise SystemExit("environment generation " + kind + " trigger inventory shortened or duplicated")
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    for marker in (pr_marker, push_marker, end_marker):
        if content.count(marker) != 1:
            raise SystemExit("environment generation " + kind + " event marker drift")
    pr = content.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push = content.split(push_marker, 1)[1].split(end_marker, 1)[0]
    approved = tuple('      - "' + path + '"' for path in trigger_paths)
    for event, block in (("pull_request", pr), ("push", push)):
        actual = tuple(
            line for line in block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        if actual != approved:
            raise SystemExit("environment generation " + kind + " " + event + " exact trigger inventory drift")
    # Distinguish registered generations from preflight eligibility by
    # protecting the actual CI event and permission authority, not just
    # individual path lists or the reviewed full-source digest.
    expected_header = (
        ("name: Production Equivalent Environment Generation" if kind == "publisher"
         else "name: Production Equivalent Environment Generation Source Negative")
        + "\n\non:\n"
        + pr_marker + "".join('      - "' + path + '"\n' for path in trigger_paths)
        + push_marker + "".join('      - "' + path + '"\n' for path in trigger_paths)
        + ("  workflow_dispatch:\n" if kind == "publisher" else "")
    )
    if (content.count("\npermissions:\n") != 1
            or content.split("\npermissions:\n", 1)[0] != expected_header):
        raise SystemExit("environment generation " + kind + " exact event header drift")
    expected_roots = (
        ["name: Production Equivalent Environment Generation", "on:",
         "permissions:", "concurrency:", "jobs:"]
        if kind == "publisher" else
        ["name: Production Equivalent Environment Generation Source Negative",
         "on:", "permissions:", "jobs:"]
    )
    observed_roots = [
        row for row in content.splitlines()
        if row.strip() and not row[0].isspace()
        and not row.lstrip().startswith("#")
    ]
    if observed_roots != expected_roots:
        raise SystemExit("environment generation " + kind + " root YAML key shadow drift")
    permission_lines = content.split("\npermissions:\n", 1)[1].splitlines()
    permission_rows = []
    for row in permission_lines:
        if row.strip() and not row[0].isspace():
            break
        if row.strip() and not row.lstrip().startswith("#"):
            permission_rows.append(row)
    if permission_rows != ["  contents: read"]:
        raise SystemExit("environment generation " + kind + " permission leaf shadow drift")


def prove_trigger_reachability_negatives(publisher: str, independent: str) -> None:
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    for kind, content, paths in (
        ("publisher", publisher, PUBLISHER_TRIGGER_PATHS),
        ("independent", independent, INDEPENDENT_TRIGGER_PATHS),
    ):
        validate_trigger_reachability(content, kind)
        for event in ("pull_request", "push"):
            for path in paths:
                token = '      - "' + path + '"\n'
                if content.count(token) != 2:
                    raise SystemExit("environment generation " + kind + " mutation anchor drift: " + path)
                if event == "pull_request":
                    mutated = content.replace(token, "", 1)
                else:
                    prefix, suffix = content.split(push_marker, 1)
                    mutated = prefix + push_marker + suffix.replace(token, "", 1)
                try:
                    validate_trigger_reachability(mutated, kind)
                except SystemExit:
                    continue
                raise SystemExit("environment generation " + kind + " accepted missing " + event + " trigger: " + path)
            marker = pr_marker if event == "pull_request" else push_marker
            for label, injected in (
                ("quoted extra", '      - "unreviewed/**"\n'),
                ("quoted duplicate", '      - "' + paths[0] + '"\n'),
                ("unquoted extra", "      - unreviewed/**\n"),
                ("unquoted duplicate", "      - " + paths[0] + "\n"),
            ):
                if content.count(marker) != 1:
                    raise SystemExit("environment generation " + kind + " addition marker drift: " + event)
                mutated = content.replace(marker, marker + injected, 1)
                if mutated == content:
                    raise SystemExit("environment generation " + kind + " addition fixture unchanged")
                try:
                    validate_trigger_reachability(mutated, kind)
                except SystemExit:
                    continue
                raise SystemExit("environment generation " + kind + " accepted " + event + " addition: " + label)
        try:
            validate_trigger_reachability(content, kind, trigger_paths=paths[:-1])
        except SystemExit:
            pass
        else:
            raise SystemExit("environment generation " + kind + " shortened trigger inventory accepted")
    # These mutations leave both reviewed PR/push path lists intact.
    # Require the intended event, root or permission semantic diagnostic.
    for kind, content in (("publisher", publisher), ("independent", independent)):
        mutated = content.replace("on:\n", "on:\n  issues:\n", 1)
        if mutated == content:
            raise SystemExit("environment generation header negative anchor drift: " + kind)
        try:
            validate_trigger_reachability(mutated, kind)
        except SystemExit as exc:
            expected = "environment generation " + kind + " exact event header drift"
            if str(exc) != expected:
                raise SystemExit(
                    "environment generation header rejected for wrong reason: "
                    + kind + ": " + str(exc)
                ) from exc
        else:
            raise SystemExit("environment generation accepted extra event: " + kind)
    root_negative_count = 0
    for kind, content in (("publisher", publisher), ("independent", independent)):
        for name, suffix in (
            ("spaced on", "on :\n  issues:\n"),
            ("quoted on", "'on':\n  issues:\n"),
            ("spaced permissions", "permissions :\n  contents: write\n"),
            ("spaced jobs", "jobs : {}\n"),
        ):
            try:
                validate_trigger_reachability(content + suffix, kind)
            except SystemExit as exc:
                expected = "environment generation " + kind + " root YAML key shadow drift"
                if str(exc) != expected:
                    raise SystemExit(
                        "environment generation root shadow rejected for wrong reason: "
                        + kind + " " + name + ": " + str(exc)
                    ) from exc
            else:
                raise SystemExit(
                    "environment generation accepted root shadow: " + kind + " " + name
                )
            root_negative_count += 1
    if root_negative_count != 8:
        raise SystemExit("environment generation root shadow fixture count drift")
    permission_negative_count = 0
    for kind, content in (("publisher", publisher), ("independent", independent)):
        anchor = "permissions:\n  contents: read\n"
        if content.count(anchor) != 1:
            raise SystemExit("environment generation permission negative anchor drift: " + kind)
        for name, extra in (
            ("spaced", "  contents : write\n"),
            ("quoted", "  'contents': write\n"),
        ):
            mutated = content.replace(anchor, anchor + extra, 1)
            try:
                validate_trigger_reachability(mutated, kind)
            except SystemExit as exc:
                expected = "environment generation " + kind + " permission leaf shadow drift"
                if str(exc) != expected:
                    raise SystemExit(
                        "environment generation permission shadow rejected for wrong reason: "
                        + kind + " " + name + ": " + str(exc)
                    ) from exc
            else:
                raise SystemExit(
                    "environment generation accepted permission shadow: " + kind + " " + name
                )
            permission_negative_count += 1
    if permission_negative_count != 4:
        raise SystemExit("environment generation permission leaf fixture count drift")
    print("PASS: environment generation CI semantic YAML negatives "
          "(2 extra-event, 8 root, 4 permission exact-diagnostic cases)")
    print("PASS: environment generation publisher/independent CI event-specific triggers (48 removals; 16 additions; 2 shortened inventory negatives)")


def validate(
    publisher: str, independent: str, *,
    check_publisher_blob: bool = True, check_independent_blob: bool = True,
) -> None:
    validate_trigger_reachability(publisher, "publisher")
    validate_trigger_reachability(independent, "independent")
    validate_job_authority(publisher, independent)
    for name, source, required, reviewed in (
        ("publisher", publisher, PUBLISHER_REQUIRED, PUBLISHER_SHA),
        ("independent", independent, INDEPENDENT_REQUIRED, INDEPENDENT_SHA),
    ):
        for label, token, count in required:
            if source.count(token) != count:
                raise SystemExit("environment generation " + name + " source drift: " + label)
        data = source.encode("utf-8")
        digest = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
        if ((name == "publisher" and check_publisher_blob) or
                (name == "independent" and check_independent_blob)) and digest != reviewed:
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
    publisher_blob_only = {"unreviewed Action", "unreviewed shell"}
    independent_blob_only = {"unreviewed Action", "unreviewed shell"}
    for name, original, cases, required, blob_only in (
        ("publisher", publisher, publisher_cases, PUBLISHER_REQUIRED, publisher_blob_only),
        ("independent", independent, independent_cases, INDEPENDENT_REQUIRED, independent_blob_only),
    ):
        semantic_count = 0
        digest_only_count = 0
        for label, before, after in cases:
            if before not in original:
                raise SystemExit("environment generation negative fixture missing: " + name + " " + label)
            mutated = original.replace(before, after, 1)
            if mutated == original:
                raise SystemExit("environment generation negative fixture unchanged: " + name + " " + label)
            semantic = any(mutated.count(token) != original.count(token)
                           for _, token, _ in required)
            if semantic != (label not in blob_only):
                raise SystemExit("environment generation " + name + " semantic/digest negative classification drift: " + label)
            semantic_count += int(semantic)
            digest_only_count += int(not semantic)
            try:
                if name == "publisher":
                    validate(mutated, independent, check_publisher_blob=not semantic)
                else:
                    validate(publisher, mutated, check_independent_blob=not semantic)
            except SystemExit:
                continue
            raise SystemExit("environment generation accepted source mutation: " + name + " " + label)
        if (semantic_count, digest_only_count) != (len(cases) - 2, 2):
            raise SystemExit("environment generation " + name + " semantic/digest negative coverage drift")
        print(f"PASS: environment generation {name} source negatives ({semantic_count} semantic; {digest_only_count} blob-only)")
    print(f"PASS: environment generation source negatives ({len(publisher_cases)} publisher, {len(independent_cases)} independent)")


NEGATIVE_REACHABILITY = {
    "scripts/validate-memory-os-production-equivalent-environment-generation-negative.py": (
        "prove_private_generation_suite_transport",
    ),
    "scripts/validate-memory-os-production-equivalent-environment-generation-source-binding-negative.py": (
        "prove_bounded_digest_reader",
        "prove_bounded_source_binding",
    ),
    "scripts/validate-memory-os-production-equivalent-environment-generation-lineage-negative.py": (
        "prove_bounded_writer_git_authority",
    ),
    "scripts/validate-memory-os-production-equivalent-environment-generation-append-rollback-negative.py": (
        "prove_atomic_io_failure_privacy_and_cleanup",
    ),
}


def check_negative_reachability(tree: ast.Module, path: str, expected: tuple[str, ...]) -> None:
    mains = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name == "main"]
    if len(mains) != 1:
        raise SystemExit("environment generation negative main authority drift: " + path)
    for function in expected:
        definitions = [node for node in tree.body
                       if isinstance(node, ast.FunctionDef) and node.name == function]
        calls = [node for node in mains[0].body
                 if isinstance(node, ast.Expr)
                 and isinstance(node.value, ast.Call)
                 and isinstance(node.value.func, ast.Name)
                 and node.value.func.id == function
                 and (
                     (node.value.args
                      and isinstance(node.value.args[0], ast.Name)
                      and node.value.args[0].id == "writer")
                     or (function == "prove_private_generation_suite_transport"
                         and not node.value.args)
                 )
                 and not node.value.keywords]
        if len(definitions) != 1 or len(calls) != 1:
            raise SystemExit("environment generation negative executable guard missing: "
                             + path + " " + function)


def prove_negative_reachability() -> None:
    """Reject deletion of a real-writer fault-injection call from live main()."""
    for path, functions in NEGATIVE_REACHABILITY.items():
        source = read(path)
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError:
            raise SystemExit("environment generation negative source invalid: " + path) from None
        check_negative_reachability(tree, path, functions)
        for function in functions:
            mutated = ast.parse(source, filename=path)
            main = next(node for node in mutated.body
                        if isinstance(node, ast.FunctionDef) and node.name == "main")
            main.body = [node for node in main.body
                         if not (isinstance(node, ast.Expr)
                                 and isinstance(node.value, ast.Call)
                                 and isinstance(node.value.func, ast.Name)
                                 and node.value.func.id == function)]
            try:
                check_negative_reachability(mutated, path, functions)
            except SystemExit:
                continue
            raise SystemExit("environment generation negative removal mutation accepted: "
                             + path + " " + function)
    print("PASS: environment generation real-writer negative reachability and removal mutations (5 cases)")


def validate_job_authority(publisher: str, independent: str) -> None:
    """Pin effective job mappings, scope and job keys before blob-only checks."""
    reviewed = (
        ("publisher", publisher, (
            ("validate-pr", "github.event_name == 'pull_request'", "read", 8),
            ("validate-and-publish",
             "(github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'",
             "write", 8),
        )),
        ("independent", independent, (
            ("source-negative",
             "github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')",
             "read", 5),
        )),
    )
    for label, content, jobs in reviewed:
        prefix = "environment generation " + label + " "
        if content.count("\njobs:\n") != 1:
            raise SystemExit(prefix + "job mapping shadow drift")
        body = content.split("\njobs:\n", 1)[1]
        sections: dict[str, list[str]] = {}
        current: str | None = None
        actual: list[str] = []
        for line in body.splitlines():
            if (line.startswith("  ") and len(line) > 2 and line[2] != " "
                    and not line.lstrip().startswith("#")):
                current = line
                actual.append(line)
                sections[current] = []
            elif current is not None:
                sections[current].append(line)
        expected = ["  " + name + ":" for name, _, _, _ in jobs]
        if actual != expected:
            raise SystemExit(prefix + "job mapping shadow drift")
        for name, condition, scope, timeout in jobs:
            lines = sections["  " + name + ":"]
            keys = [
                line for line in lines
                if line.startswith("    ") and len(line) > 4 and line[4] != " "
                and not line.lstrip().startswith("#")
            ]
            if keys != [
                "    if: " + condition,
                "    permissions:",
                "    runs-on: ubuntu-latest",
                "    timeout-minutes: " + str(timeout),
                "    steps:",
            ]:
                raise SystemExit(prefix + name + " job key shadow drift")
            leaves: list[str] = []
            for line in lines[lines.index("    permissions:") + 1:]:
                if line.startswith("    ") and len(line) > 4 and line[4] != " ":
                    break
                if line.strip() and not line.lstrip().startswith("#"):
                    leaves.append(line)
            if leaves != ["      contents: " + scope]:
                raise SystemExit(prefix + name + " job permission leaf shadow drift")


def prove_job_authority_negatives(publisher: str, independent: str) -> None:
    """Exercise 36 exact-diagnostic nested YAML mutations, not just blob mismatch."""
    validate_job_authority(publisher, independent)
    count = 0
    reviewed = (
        ("publisher", publisher, independent, (
            ("validate-pr", "github.event_name == 'pull_request'", "read", 8),
            ("validate-and-publish",
             "(github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'",
             "write", 8),
        ), True),
        ("independent", independent, publisher, (
            ("source-negative",
             "github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')",
             "read", 5),
        ), False),
    )
    for label, content, other, jobs, is_publisher in reviewed:
        for name, condition, scope, timeout in jobs:
            header = "  " + name + ":\n"
            if content.count(header) != 1:
                raise SystemExit("environment generation job fixture header drift: " + label + " " + name)

            def in_job(before: str, after: str) -> str:
                prefix, suffix = content.split(header, 1)
                if before not in suffix:
                    raise SystemExit("environment generation job fixture anchor drift: " + name)
                return prefix + header + suffix.replace(before, after, 1)

            condition_anchor = "    if: " + condition + "\n"
            permission = "    permissions:\n      contents: " + scope + "\n"
            runner = "    runs-on: ubuntu-latest\n"
            timeout_anchor = "    timeout-minutes: " + str(timeout) + "\n"
            steps = "    steps:\n"
            cases = [
                ("duplicate mapping", content + "\n" + header + "    runs-on: ubuntu-latest\n",
                 "job mapping shadow drift"),
                ("quoted mapping", content.replace(header, "  '" + name + "':\n", 1),
                 "job mapping shadow drift"),
                ("spaced mapping", content.replace(header, "  " + name + " :\n", 1),
                 "job mapping shadow drift"),
                ("condition shadow", in_job(condition_anchor, condition_anchor + "    if : true\n"),
                 name + " job key shadow drift"),
                ("permission shadow", in_job(permission, permission + "    permissions :\n      contents: write\n"),
                 name + " job key shadow drift"),
                ("runner shadow", in_job(runner, runner + "    runs-on : ubuntu-latest\n"),
                 name + " job key shadow drift"),
                ("timeout shadow", in_job(timeout_anchor, timeout_anchor + "    timeout-minutes : 1\n"),
                 name + " job key shadow drift"),
                ("steps shadow", in_job(steps, "    steps : []\n" + steps),
                 name + " job key shadow drift"),
                ("continuation override", in_job(steps, "    continue-on-error: true\n" + steps),
                 name + " job key shadow drift"),
                ("direct permission change", in_job(permission, permission.replace(
                    "contents: " + scope, "contents: " + ("read" if scope == "write" else "write"))),
                 name + " job permission leaf shadow drift"),
                ("spaced permission leaf", in_job(permission, permission + "      contents : write\n"),
                 name + " job permission leaf shadow drift"),
                ("quoted permission leaf", in_job(permission, permission + "      'contents': write\n"),
                 name + " job permission leaf shadow drift"),
            ]
            for mutation, changed, diagnostic in cases:
                if changed == content:
                    raise SystemExit("environment generation unchanged job fixture: " + mutation)
                try:
                    if is_publisher:
                        validate_job_authority(changed, other)
                    else:
                        validate_job_authority(other, changed)
                except SystemExit as exc:
                    expected = "environment generation " + label + " " + diagnostic
                    if str(exc) != expected:
                        raise SystemExit("environment generation wrong job diagnostic: "
                                         + label + " " + name + " " + mutation + ": " + str(exc)) from exc
                else:
                    raise SystemExit("environment generation accepted job shadow: "
                                     + label + " " + name + " " + mutation)
                count += 1
    if count != 36:
        raise SystemExit("environment generation job negative inventory drift")
    print("PASS: environment generation publisher/independent job authority (36 exact-diagnostic negatives)")


def main() -> int:
    publisher = read(PUBLISHER)
    independent = read(INDEPENDENT)
    validate(publisher, independent)
    prove_job_authority_negatives(publisher, independent)
    prove_trigger_reachability_negatives(publisher, independent)
    runtime(publisher, independent)
    diagnostic_runtime(publisher)
    negatives(publisher, independent)
    prove_negative_reachability()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
