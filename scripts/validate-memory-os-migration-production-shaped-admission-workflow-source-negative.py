#!/usr/bin/env python3
"""Negative and runtime proof for migration production-shaped admission CI source trust."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/migration-production-shaped-admission.yml"
INDEPENDENT = ".github/workflows/migration-production-shaped-admission-source-negative.yml"
SELF = "scripts/validate-memory-os-migration-production-shaped-admission-workflow-source-negative.py"
PUBLISHER_SHA = "80c283c3bf93934f115321d761a349a9b74648cb"
INDEPENDENT_SHA = "11ef68d69908b1f58056b2b36188ae67eb69da9c"
ISOLATION = ".github/workflows/migration-production-shaped-negative-isolation.yml"
ISOLATION_SCRIPT = "scripts/diagnose-memory-os-migration-production-shaped-admission-negative-isolated.py"
NEGATIVE_SCRIPT = "scripts/validate-memory-os-migration-production-shaped-admission-negative.py"
ISOLATION_SHA = "e439088b4ac8ab0fce2a08bfd46f38a2a8b33933"
ISOLATION_SCRIPT_SHA = "00dcd7e95896b7352f682d8d1eeefbd3f8920755"
NEGATIVE_SCRIPT_SHA = "3366455aa1140f464d7442b2b788ed3240ee898b"
D = chr(36)
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
PR_BASE = 'test "' + D + '{GITHUB_BASE_REF:-}" = "so"'
WRITER_REF = 'test "' + D + '{GITHUB_REF:-}" = "refs/heads/so"'
PR_EVENT = 'test "' + D + '{GITHUB_EVENT_NAME:-}" = "pull_request"'
WRITER_EVENT = '[[ "' + D + '{GITHUB_EVENT_NAME:-}" == "push" || "' + D + '{GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]'
SHA_FORMAT = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
PR_SHA_FORMAT = '[[ "$PR_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]'
WRITER_SHA_FORMAT = '[[ "' + D + '{GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]'
REDACTION = "'output': 'REDACTED: migration production-shaped admission failed; raw output withheld',"
SUPPRESS = 'printf "Migration production-shaped admission exit code: %s (raw validator log suppressed)\\n" "$code"'
WRITER_SCOPE = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n"
PR_CHECKOUT = 'ref: ' + D + '{{ github.event.pull_request.head.sha }}'
WRITER_CHECKOUT = 'ref: ' + D + '{{ github.sha }}'

PUBLISHER_REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n", 1),
    ("publisher trigger", '      - "' + PUBLISHER + '"\n', 2),
    ("independent trigger", '      - "' + INDEPENDENT + '"\n', 2),
    ("validator trigger", '      - "' + SELF + '"\n', 2),
    ("permission validator trigger", '      - "scripts/validate-memory-os-migration-production-shaped-admission-permission-negative.py"\n', 2),
    ("checkout pin", CHECKOUT, 2),
    ("setup pin", SETUP, 2),
    ("PR no credentials", "          persist-credentials: false\n", 1),
    ("writer credentials", "          persist-credentials: true\n", 1),
    ("PR base", PR_BASE, 1),
    ("PR event", PR_EVENT, 1),
    ("writer event", WRITER_EVENT, 1),
    ("writer branch", WRITER_REF, 1),
    ("PR SHA format", PR_SHA_FORMAT, 1),
    ("writer SHA format", WRITER_SHA_FORMAT, 1),
    ("source self check", "          python " + SELF + "\n", 2),
    ("writer scope", WRITER_SCOPE, 1),
    ("writer token", "      contents: write\n", 1),
    ("root read token", "permissions:\n  contents: read\n", 1),
    ("PR read token", "      contents: read\n", 1),
    ("checkout PR head", PR_CHECKOUT, 1),
    ("checkout writer head", WRITER_CHECKOUT, 1),
    ("PR HEAD identity", 'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"', 1),
    ("writer HEAD identity", 'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"', 1),
    ("redacted diagnostic", REDACTION, 1),
    ("suppressed CI log", SUPPRESS, 1),
    ("bounded failed stage", 'if [[ "$code" != "0" ]]; then printf "Migration admission failed stage: %s\\n" "$stage"; fi', 1),
    ("compile stage", "          stage=compile\n", 1),
    ("generation authority stage", "            stage=generation-authority\n", 1),
    ("ledger authority stage", "            stage=ledger-authority\n", 1),
    ("admission negative stage", "            stage=admission-negative\n", 1),
    ("rollback stage", "            stage=rollback\n", 1),
    ("reconcile stage", "            stage=reconcile\n", 1),
    ("lifecycle stage", "            stage=lifecycle\n", 1),
    ("operability stage", "            stage=operability\n", 1),
    ("no raw tail", "text[-12000:]", 0),
    ("no raw CI log", '          cat "$log"\n', 0),
)
INDEPENDENT_REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n", 1),
    ("publisher trigger", '      - "' + PUBLISHER + '"\n', 2),
    ("independent trigger", '      - "' + INDEPENDENT + '"\n', 2),
    ("validator trigger", '      - "' + SELF + '"\n', 2),
    ("isolation workflow trigger", '      - "' + ISOLATION + '"\n', 2),
    ("isolation runner trigger", '      - "' + ISOLATION_SCRIPT + '"\n', 2),
    ("migration negative trigger", '      - "' + NEGATIVE_SCRIPT + '"\n', 2),
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
        raise SystemExit("migration production-shaped admission source missing/substituted: " + relative) from exc


def validate(publisher: str, independent: str) -> None:
    for name, source, required, reviewed in (
        ("publisher", publisher, PUBLISHER_REQUIRED, PUBLISHER_SHA),
        ("independent", independent, INDEPENDENT_REQUIRED, INDEPENDENT_SHA),
    ):
        for label, token, count in required:
            if source.count(token) != count:
                raise SystemExit("migration production-shaped admission " + name + " source drift: " + label)
        data = source.encode("utf-8")
        digest = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
        if digest != reviewed:
            raise SystemExit("migration production-shaped admission " + name + " complete source drift")


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
                raise SystemExit("migration production-shaped admission unreachable runtime branch: " + name + " " + label)
            result = subprocess.run(["bash", "-e", "-c", token], env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}, capture_output=True, check=False)
            if (result.returncode == 0) != allow:
                raise SystemExit("migration production-shaped admission branch runtime drift: " + name + " " + label)
    for token, allowed in ((PR_EVENT, ("pull_request",)), (WRITER_EVENT, ("push", "workflow_dispatch"))):
        for event in ("pull_request", "push", "workflow_dispatch", "", "schedule"):
            result = subprocess.run(["bash", "-e", "-c", token], env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GITHUB_EVENT_NAME": event}, capture_output=True, check=False)
            if (result.returncode == 0) != (event in allowed):
                raise SystemExit("migration production-shaped admission event runtime drift: " + event)
    for label, var, predicate in (("PR", "PR_HEAD_SHA", PR_SHA_FORMAT), ("writer", "GITHUB_SHA", WRITER_SHA_FORMAT), ("independent", "expected", SHA_FORMAT)):
        for value, allow in (("a" * 40, True), ("0" * 40, True), ("A" * 40, False), ("g" * 40, False), ("a" * 39, False), ("a" * 41, False), ("", False), ("$(echo bad)", False)):
            prefix = var + '="' + D + '{PROBE_SHA:-}"\n'
            result = subprocess.run(["bash", "-e", "-c", prefix + predicate],
                                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PROBE_SHA": value}, capture_output=True, check=False)
            if (result.returncode == 0) != allow:
                raise SystemExit("migration production-shaped admission SHA runtime drift: " + label + " " + value[:10])
    print("PASS: migration production-shaped admission branch/event/SHA runtime (46 cases)")


def diagnostic_runtime(publisher: str) -> None:
    start, end = "          python - <<'PY'\n", "          PY\n"
    if publisher.count(start) != 1 or publisher.count(end) != 1:
        raise SystemExit("migration production-shaped admission diagnostic writer not unique")
    inline = publisher.split(start, 1)[1].split(end, 1)[0]
    script = "\n".join(line[10:] for line in inline.splitlines()) + "\n"
    with tempfile.TemporaryDirectory(prefix="migration-production-shaped-admission-diagnostic-") as directory:
        env = os.environ.copy()
        env.update({"SOURCE_COMMIT_SHA": "e" * 40, "ADMISSION_EXIT_CODE": "23", "SENSITIVE_CANARY": "CANARY_DO_NOT_PERSIST_MIGRATION"})
        result = subprocess.run([sys.executable, "-c", script], cwd=directory, env=env, capture_output=True, text=True, check=False)
        if result.returncode:
            raise SystemExit("migration production-shaped admission isolated diagnostic failed: " + result.stderr[:500])
        output = Path(directory) / "docs/fixtures/memory-os-operability/migration-production-shaped-admission-diagnostic.last.json"
        raw = output.read_text(encoding="utf-8")
        value = json.loads(raw)
        if value.get("output") != "REDACTED: migration production-shaped admission failed; raw output withheld":
            raise SystemExit("migration production-shaped admission diagnostic persisted raw validator output")
        if value.get("sourceCommitSha") != "e" * 40 or value.get("exitCode") != 23:
            raise SystemExit("migration production-shaped admission diagnostic source/exit binding drift")
        if value.get("containsSecrets") is not False or value.get("productionEvidence") is not False or value.get("productionReady") is not False:
            raise SystemExit("migration production-shaped admission diagnostic evidence/readiness flag drift")
        if value.get("admittedRehearsalCount") != 0 or "CANARY_DO_NOT_PERSIST_MIGRATION" in raw:
            raise SystemExit("migration production-shaped admission diagnostic fabricated evidence or persisted canary")
    print("PASS: migration production-shaped admission isolated diagnostic redaction (1 runtime case)")


def negatives(publisher: str, independent: str) -> None:
    publisher_cases = (
        ("PR branch", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("publisher trigger", '      - "' + PUBLISHER + '"\n', ""),
        ("independent trigger", '      - "' + INDEPENDENT + '"\n', ""),
        ("validator trigger", '      - "' + SELF + '"\n', ""),
        ("permission validator trigger", '      - "scripts/validate-memory-os-migration-production-shaped-admission-permission-negative.py"\n', ""),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("PR credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("writer credentials", "          persist-credentials: true\n", ""),
        ("PR base", PR_BASE, "true"),
        ("writer branch", WRITER_REF, "true"),
        ("writer event", WRITER_EVENT, "true"),
        ("PR event", PR_EVENT, "true"),
        ("PR SHA format", PR_SHA_FORMAT, 'test -n "$PR_HEAD_SHA"'),
        ("writer SHA format", WRITER_SHA_FORMAT, 'test -n "$GITHUB_SHA"'),
        ("broad writer job", WRITER_SCOPE, "    if: github.event_name != 'pull_request'\n"),
        ("self check", "          python " + SELF + "\n", ""),
        ("checkout PR", PR_CHECKOUT, WRITER_CHECKOUT),
        ("checkout writer", WRITER_CHECKOUT, 'ref: ' + D + '{{ github.ref }}'),
        ("raw diagnostic", REDACTION, "'output': Path('/tmp/migration-production-shaped-admission.log').read_text(),"),
        ("raw CI echo", SUPPRESS, 'cat "$log"'),
        ("missing failed stage", 'if [[ "$code" != "0" ]]; then printf "Migration admission failed stage: %s\\n" "$stage"; fi', ""),
        ("skip operability stage", "            stage=operability\n", ""),
        ("skip compile stage", "          stage=compile\n", ""),
        ("unreviewed Action", "      - name: Confirm exact clean authority source\n", "      - uses: unreviewed/action@v1\n      - name: Confirm exact clean authority source\n"),
        ("unreviewed shell", "      - name: Confirm exact clean authority source\n", "      - run: echo unreviewed\n      - name: Confirm exact clean authority source\n"),
    )
    independent_cases = (
        ("PR target", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("publisher trigger", '      - "' + PUBLISHER + '"\n', ""),
        ("independent trigger", '      - "' + INDEPENDENT + '"\n', ""),
        ("validator trigger", '      - "' + SELF + '"\n', ""),
        ("isolation workflow trigger", '      - "' + ISOLATION + '"\n', ""),
        ("isolation runner trigger", '      - "' + ISOLATION_SCRIPT + '"\n', ""),
        ("migration negative trigger", '      - "' + NEGATIVE_SCRIPT + '"\n', ""),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("persist credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("PR base", PR_BASE, "true"),
        ("push branch", WRITER_REF, "true"),
        ("SHA format", SHA_FORMAT, 'test -n "$expected"'),
        ("self execution", "          python " + SELF + "\n", ""),
        ("unreviewed Action", "      - name: Prove migration production-shaped admission publisher source\n", "      - uses: unreviewed/action@v1\n      - name: Prove migration production-shaped admission publisher source\n"),
        ("unreviewed shell", "      - name: Prove migration production-shaped admission publisher source\n", "      - run: echo unreviewed\n      - name: Prove migration production-shaped admission publisher source\n"),
    )
    for name, original, cases in (("publisher", publisher, publisher_cases), ("independent", independent, independent_cases)):
        for label, before, after in cases:
            if before not in original:
                raise SystemExit("migration production-shaped admission negative fixture missing: " + name + " " + label)
            mutated = original.replace(before, after, 1)
            if mutated == original:
                raise SystemExit("migration production-shaped admission negative fixture unchanged: " + name + " " + label)
            try:
                validate(mutated, independent) if name == "publisher" else validate(publisher, mutated)
            except SystemExit:
                continue
            raise SystemExit("migration production-shaped admission accepted source mutation: " + name + " " + label)
    print(f"PASS: migration production-shaped admission source negatives ({len(publisher_cases)} publisher, {len(independent_cases)} independent)")



def prove_failed_stage_runtime(publisher: str) -> None:
    """Prove the bounded stage marker emits no validator output or success noise."""
    token = 'if [[ "$code" != "0" ]]; then printf "Migration admission failed stage: %s\\n" "$stage"; fi'
    if publisher.count(token) != 1:
        raise SystemExit("migration admission bounded failure stage not uniquely reachable")
    for code, stage, expected in (
        ("1", "compile", "Migration admission failed stage: compile\n"),
        ("75", "reconcile", "Migration admission failed stage: reconcile\n"),
        ("0", "operability", ""),
    ):
        result = subprocess.run(["bash", "-e", "-c", token],
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "code": code, "stage": stage},
                                capture_output=True, text=True, check=False)
        if result.returncode != 0 or result.stdout != expected or result.stderr:
            raise SystemExit("migration admission failed-stage runtime drift: " + stage + " code " + code)
    print("PASS: migration admission bounded failed-stage runtime (3 cases)")



def require_isolation_blob(label: str, source: str, expected: str) -> None:
    """Use the same fail-closed check for canonical and mutated source."""
    data = source.encode("utf-8")
    digest = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
    if digest != expected:
        raise SystemExit("migration isolated negative source drift: " + label)


def verify_isolation_blob_bindings() -> None:
    """Prove the production guard rejects each mutated source, not just a different hash."""
    for label, path, expected in (
        ("isolation workflow", ISOLATION, ISOLATION_SHA),
        ("isolation runner", ISOLATION_SCRIPT, ISOLATION_SCRIPT_SHA),
        ("migration negative", NEGATIVE_SCRIPT, NEGATIVE_SCRIPT_SHA),
    ):
        source = read(path)
        require_isolation_blob(label, source, expected)
        for suffix in ("\n# inert source mutation\n", "\n# disabled test\n"):
            try:
                require_isolation_blob(label, source + suffix, expected)
            except SystemExit as exc:
                if str(exc) != "migration isolated negative source drift: " + label:
                    raise
            else:
                raise SystemExit("migration isolated negative mutation accepted: " + label)
    print("PASS: migration isolated workflow/runner/negative source bindings (6 mutations)")


def main() -> int:
    publisher = read(PUBLISHER)
    independent = read(INDEPENDENT)
    validate(publisher, independent)
    verify_isolation_blob_bindings()
    runtime(publisher, independent)
    diagnostic_runtime(publisher)
    prove_failed_stage_runtime(publisher)
    negatives(publisher, independent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
