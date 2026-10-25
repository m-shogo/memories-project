#!/usr/bin/env python3
"""Read-only exact-source, runtime and diagnostic privacy proof for migration evidence CI."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/migration-evidence-registry.yml"
INDEPENDENT = ".github/workflows/migration-evidence-registry-source-negative.yml"
SELF = "scripts/validate-memory-os-migration-evidence-registry-workflow-source-negative.py"
PUBLISHER_SHA = "44cbad2f07c77bd76a2d3982a666806a340f3912"
INDEPENDENT_SHA = "878f920daaa183087dceb1dc8c24dde0b47e2180"
AUTHORITY_NEGATIVE = "scripts/validate-memory-os-migration-evidence-registry-reconcile-authority-negative.py"
AUTHORITY_NEGATIVE_SHA = "e9eebd43c2ed84340db9ba94560a6959ca0438c2"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
WRITER_SCOPE = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'"
PR_BASE = 'test "${GITHUB_BASE_REF:-}" = "so"'
WRITER_REF = 'test "${GITHUB_REF:-}" = "refs/heads/so"'
PR_SHA = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
WRITER_SHA = '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]'


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("migration evidence CI source guard: " + message)


def read(path: str) -> str:
    file = ROOT / path
    require(file.is_file() and not file.is_symlink(), "missing or symlinked source: " + path)
    require(file.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() == path,
            "source escaped root: " + path)
    return file.read_text(encoding="utf-8")


def check_source(name: str, source: str, expected: str, required: tuple[tuple[str, int], ...]) -> None:
    for token, count in required:
        require(source.count(token) == count, name + " required source inventory drift: " + token[:55])
    for forbidden in ("pull_request_target:", "secrets.", "actions/checkout@v4", "actions/setup-python@v5"):
        require(forbidden not in source, name + " unreviewed source")
    data = source.encode("utf-8")
    digest = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
    require(digest == expected, name + " complete Git blob drift")


PUBLISHER_REQUIRED = (
    ("  pull_request:\n    branches:\n      - so\n", 1),
    ("  push:\n    branches:\n      - so\n", 1),
    ("  workflow_dispatch:\n", 1),
    ('      - "' + PUBLISHER + '"\n', 2),
    ('      - "' + INDEPENDENT + '"\n', 2),
    ('      - "' + SELF + '"\n', 2),
    (CHECKOUT, 2),
    (SETUP, 2),
    ("persist-credentials: false", 1),
    ("persist-credentials: true", 1),
    (WRITER_SCOPE, 1),
    (PR_BASE, 1),
    (WRITER_REF, 1),
    (PR_SHA, 1),
    (WRITER_SHA, 1),
    ("'output': 'REDACTED: migration evidence registry failed; raw output withheld'", 1),
    ("raw validator log suppressed", 1),
    ('cat "$log"', 0),
    ("text[-12000:]", 0),
    ("python " + SELF, 2),
    ("permissions:\n  contents: read\n", 1),
    ("      contents: write\n", 1),
    ("      contents: read\n", 1),
)
INDEPENDENT_REQUIRED = (
    ("  pull_request:\n    branches:\n      - so\n", 1),
    ("  push:\n    branches:\n      - so\n", 1),
    ('      - "' + PUBLISHER + '"\n', 2),
    ('      - "' + INDEPENDENT + '"\n', 2),
    ('      - "' + SELF + '"\n', 2),
    (CHECKOUT, 1),
    (SETUP, 1),
    ("persist-credentials: false", 1),
    (PR_BASE, 1),
    (WRITER_REF, 1),
    (PR_SHA, 1),
    ("python " + SELF, 1),
    ('      - "' + AUTHORITY_NEGATIVE + '"\n', 2),
    ('      - "' + "scripts/reconcile-memory-os-migration-evidence-registry.py" + '"\n', 2),
    ("python " + AUTHORITY_NEGATIVE, 1),
    ("git clone --quiet --no-hardlinks --no-checkout .", 1),
    ("permissions:\n  contents: read\n", 1),
    ("      contents: read\n", 1),
)


def validate(publisher: str, independent: str, authority_negative: str | None = None) -> None:
    check_source("publisher", publisher, PUBLISHER_SHA, PUBLISHER_REQUIRED)
    check_source("independent", independent, INDEPENDENT_SHA, INDEPENDENT_REQUIRED)
    check_source("lifecycle negative", read(AUTHORITY_NEGATIVE) if authority_negative is None else authority_negative,
                 AUTHORITY_NEGATIVE_SHA, ())


def negative_proofs(publisher: str, independent: str) -> None:
    cases = (
        ("publisher PR base", True, PR_BASE, "true"),
        ("publisher writer ref", True, WRITER_REF, "true"),
        ("publisher writer scope", True, WRITER_SCOPE, "    if: always()"),
        ("publisher PR SHA", True, PR_SHA, 'test -n "$expected"'),
        ("publisher writer SHA", True, WRITER_SHA, 'test -n "$GITHUB_SHA"'),
        ("publisher checkout pin", True, CHECKOUT, "uses: actions/checkout@v4"),
        ("publisher credentials", True, "persist-credentials: false", "persist-credentials: true"),
        ("publisher self guard", True, "python " + SELF, "echo skip"),
        ("publisher redaction", True, "'output': 'REDACTED: migration evidence registry failed; raw output withheld'", "'output': text[-12000:]"),
        ("publisher log suppression", True, "raw validator log suppressed", "raw validator log exposed"),
        ("independent PR base", False, PR_BASE, "true"),
        ("independent writer ref", False, WRITER_REF, "true"),
        ("independent SHA", False, PR_SHA, 'test -n "$expected"'),
        ("independent checkout pin", False, CHECKOUT, "uses: actions/checkout@v4"),
        ("independent credentials", False, "persist-credentials: false", "persist-credentials: true"),
        ("independent self guard", False, "python " + SELF, "echo skip"),
        ("independent lifecycle guard", False, "python " + AUTHORITY_NEGATIVE, "echo skip"),
        ("independent isolated clone", False, "git clone --quiet --no-hardlinks --no-checkout .", "echo skip"),
    )
    for label, publisher_case, before, after in cases:
        original = publisher if publisher_case else independent
        require(before in original, "mutation anchor missing: " + label)
        changed = original.replace(before, after, 1)
        require(changed != original, "mutation unchanged: " + label)
        try:
            validate(changed, independent) if publisher_case else validate(publisher, changed)
        except SystemExit:
            continue
        raise SystemExit("migration evidence source negative accepted: " + label)
    suite = read(AUTHORITY_NEGATIVE)
    require("def prove_stronger_lifecycle_authority_cannot_be_downgraded" in suite,
            "lifecycle downgrade negative entrypoint missing")
    try:
        validate(publisher, independent, suite.replace(
            "def prove_stronger_lifecycle_authority_cannot_be_downgraded",
            "def disabled_stronger_lifecycle_authority_cannot_be_downgraded", 1))
    except SystemExit:
        pass
    else:
        raise SystemExit("migration evidence source negative accepted: lifecycle suite digest drift")
    print("PASS: migration evidence CI source negatives (19 cases)")


def runtime_proofs() -> None:
    for label, script, key, value, expected in (
        ("PR so", PR_BASE, "GITHUB_BASE_REF", "so", True),
        ("PR main", PR_BASE, "GITHUB_BASE_REF", "main", False),
        ("writer so", WRITER_REF, "GITHUB_REF", "refs/heads/so", True),
        ("writer main", WRITER_REF, "GITHUB_REF", "refs/heads/main", False),
    ):
        result = subprocess.run(["bash", "-e", "-c", script],
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value},
                                capture_output=True, check=False)
        require((result.returncode == 0) == expected, "runtime branch drift: " + label)
    for predicate, variable in ((PR_SHA, "expected"), (WRITER_SHA, "GITHUB_SHA")):
        for value, allowed in (("a" * 40, True), ("0" * 40, True), ("A" * 40, False),
                               ("g" * 40, False), ("a" * 39, False), ("a" * 41, False), ("", False)):
            result = subprocess.run(["bash", "-e", "-c", predicate],
                                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), variable: value},
                                    capture_output=True, check=False)
            require((result.returncode == 0) == allowed, "runtime SHA drift")
    print("PASS: migration evidence branch/SHA runtime (18 cases)")


def require_diagnostic_payload(raw: str) -> None:
    """Reject secret-bearing or promotion-shaped diagnostic JSON."""
    require("CANARY_DO_NOT_PERSIST_MIGRATION_EVIDENCE" not in raw,
            "migration evidence diagnostic persisted sensitive canary")
    value = json.loads(raw)
    require(value.get("schemaVersion") == "memory-os-validator-diagnostic.v1",
            "migration evidence diagnostic schema drift")
    require(value.get("workflow") == "migration-evidence-registry" and value.get("result") == "FAIL",
            "migration evidence diagnostic identity drift")
    require(value.get("sourceCommitSha") == "e" * 40 and value.get("exitCode") == 23,
            "migration evidence diagnostic source/exit drift")
    require(value.get("output") == "REDACTED: migration evidence registry failed; raw output withheld",
            "migration evidence diagnostic raw output not redacted")
    require(value.get("containsSecrets") is False and value.get("productionEvidence") is False
            and value.get("productionReady") is False,
            "migration evidence diagnostic asserted secrets/evidence/readiness")


def diagnostic_runtime(publisher: str) -> None:
    """Execute the actual reviewed inline writer with a canary in an isolated directory."""
    marker = "      - name: Record privacy-safe diagnostic\n"
    require(publisher.count(marker) == 1, "migration evidence diagnostic step not unique")
    section = publisher.split(marker, 1)[1]
    start, end = "          python - <<'PY'\n", "          PY\n"
    require(section.count(start) == 1 and section.count(end) >= 1,
            "migration evidence inline diagnostic writer not unique")
    inline = section.split(start, 1)[1].split(end, 1)[0]
    script = "\n".join(line[10:] for line in inline.splitlines()) + "\n"
    marker_text = "'REDACTED: migration evidence registry failed; raw output withheld'"
    require(script.count(marker_text) == 1, "migration evidence diagnostic marker not unique")
    require(script.count("'productionReady': False") == 1, "migration evidence diagnostic readiness guard not unique")
    with tempfile.TemporaryDirectory(prefix="migration-evidence-diagnostic-proof-") as temp:
        root = Path(temp)
        env = os.environ.copy()
        env.update({"SOURCE_COMMIT_SHA": "e" * 40, "MIGRATION_EXIT_CODE": "23",
                    "SENSITIVE_CANARY": "CANARY_DO_NOT_PERSIST_MIGRATION_EVIDENCE"})
        variants = (
            ("reviewed", script, True),
            ("raw canary", script.replace(marker_text, "os.environ['SENSITIVE_CANARY']", 1), False),
            ("readiness promotion", script.replace("'productionReady': False", "'productionReady': True", 1), False),
        )
        for name, program, allowed in variants:
            directory = root / name.replace(" ", "-")
            directory.mkdir()
            result = subprocess.run([sys.executable, "-c", program], cwd=directory, env=env,
                                    capture_output=True, text=True, timeout=15, check=False)
            require(result.returncode == 0, "migration evidence diagnostic writer failed in isolation: " + name)
            require("CANARY_DO_NOT_PERSIST_MIGRATION_EVIDENCE" not in result.stdout + result.stderr,
                    "migration evidence diagnostic leaked canary to process output")
            path = directory / "docs/fixtures/memory-os-operability/migration-evidence-registry-diagnostic.last.json"
            require(path.is_file() and not path.is_symlink(), "migration evidence diagnostic output missing")
            raw = path.read_text(encoding="utf-8")
            try:
                require_diagnostic_payload(raw)
            except SystemExit:
                require(not allowed, "migration evidence reviewed diagnostic rejected")
            else:
                require(allowed, "migration evidence diagnostic accepted unsafe mutation: " + name)
    print("PASS: migration evidence actual diagnostic writer (1 positive, 2 negative runtime cases)")


def main() -> int:
    publisher, independent = read(PUBLISHER), read(INDEPENDENT)
    validate(publisher, independent)
    negative_proofs(publisher, independent)
    runtime_proofs()
    diagnostic_runtime(publisher)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
