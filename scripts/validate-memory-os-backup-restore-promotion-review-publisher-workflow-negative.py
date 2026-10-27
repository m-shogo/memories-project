#!/usr/bin/env python3
"""Authenticate human promotion review CI source without granting promotion authority."""

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
PUBLISHER = ".github/workflows/backup-restore-promotion-review.yml"
INDEPENDENT = ".github/workflows/backup-restore-promotion-review-source-negative.yml"
SELF = "scripts/validate-memory-os-backup-restore-promotion-review-publisher-workflow-negative.py"
REVIEWED_PUBLISHER = "6b572a3c17fa9724b48d62433b764ceb84c8b224"
REVIEWED_INDEPENDENT = "5e92aa51cdfa55ea4a55bff9674d7c7496bc71d7"
D = chr(36)
PR_BASE = 'test "' + D + '{GITHUB_BASE_REF:-}" = "so"'
PUSH_REF = 'test "' + D + '{GITHUB_REF:-}" = "refs/heads/so"'
EVENT = '[[ "' + D + '{GITHUB_EVENT_NAME:-}" == "push" || "' + D + '{GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]'
SHA_FORMAT = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
PUBLISHER_SCOPE = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
CAPTURE = "      - name: Capture exact promotion authority source\n"
MAIN_REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("script trigger", '      - "' + SELF + '"\n', 2),
    ("independent trigger", '      - "' + INDEPENDENT + '"\n', 2),
    ("checkout SHA", CHECKOUT, 2),
    ("setup SHA", SETUP, 2),
    ("PR no credentials", "          persist-credentials: false\n", 1),
    ("writer credentials", "          persist-credentials: true\n", 1),
    ("PR base", PR_BASE, 1),
    ("writer branch", PUSH_REF, 1),
    ("writer event", EVENT, 1),
    ("SHA format", SHA_FORMAT, 2),
    ("publisher scope", PUBLISHER_SCOPE, 1),
    ("PR/writer self execution", "\n          python " + SELF + "\n", 2),
    ("HEAD identity", 'test "$(git rev-parse HEAD)" = "$expected"', 2),
    ("PR SHA source", 'expected="' + D + '{{ github.event.pull_request.head.sha }}"', 1),
    ("writer SHA source", 'expected="' + D + '{GITHUB_SHA:-}"', 1),
    ("capture step", CAPTURE, 1),
    ("root read token", "permissions:\n  contents: read\n", 1),
    ("PR read token", "      contents: read\n", 1),
    ("writer write token", "      contents: write\n", 1),
    ("diagnostic fixed redaction", "              'output': 'REDACTED: promotion review validation failed; consult CI job logs',\n", 1),
    ("raw CI log suppression", '          printf "Promotion review validation exit code: %s (raw validator log suppressed)\\n" "$code"\n', 1),
    ("no raw diagnostic tail", "text[-12000:]", 0),
    ("no raw CI log echo", '          cat "$log"\n', 0),
    ("diagnostic symlink rejection", "          if path.is_symlink():\n", 1),
)
INDEPENDENT_REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("publisher trigger", '      - "' + PUBLISHER + '"\n', 2),
    ("self trigger", '      - "' + INDEPENDENT + '"\n', 2),
    ("script trigger", '      - "' + SELF + '"\n', 2),
    ("checkout SHA", CHECKOUT, 1),
    ("setup SHA", SETUP, 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("PR base", PR_BASE, 1),
    ("push branch", PUSH_REF, 1),
    ("SHA format", SHA_FORMAT, 1),
    ("self execution", "          python " + SELF + "\n", 1),
    ("read token", "  contents: read\n", 2),
    ("event scope", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", 1),
    ("clean source", '          test -z "$(git status --porcelain)"\n', 2),
)


def source(relative: str) -> str:
    path = ROOT / relative
    try:
        if not path.is_file() or path.is_symlink():
            raise ValueError("not regular")
        if path.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != relative:
            raise ValueError("escaped root")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
        raise SystemExit("human promotion CI source missing or substituted: " + relative) from exc


def validate(
    publisher: str, independent: str, *,
    check_publisher_blob: bool = True, check_independent_blob: bool = True,
) -> None:
    for name, content, required, digest in (
        ("publisher", publisher, MAIN_REQUIRED, REVIEWED_PUBLISHER),
        ("independent", independent, INDEPENDENT_REQUIRED, REVIEWED_INDEPENDENT),
    ):
        for label, token, count in required:
            if content.count(token) != count:
                raise SystemExit("human promotion " + name + " source drift: " + label)
        if (name == "publisher" and check_publisher_blob) or (name == "independent" and check_independent_blob):
            data = content.encode("utf-8")
            blob = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
            if hashlib.sha1(blob).hexdigest() != digest:
                raise SystemExit("human promotion " + name + " complete source drift")


def runtime(publisher: str, independent: str) -> None:
    for name, content in (("publisher", publisher), ("independent", independent)):
        for label, command, key, value, allow in (
            ("PR so", PR_BASE, "GITHUB_BASE_REF", "so", True),
            ("PR main", PR_BASE, "GITHUB_BASE_REF", "main", False),
            ("PR absent", PR_BASE, "GITHUB_BASE_REF", "", False),
            ("push so", PUSH_REF, "GITHUB_REF", "refs/heads/so", True),
            ("push main", PUSH_REF, "GITHUB_REF", "refs/heads/main", False),
            ("push tag", PUSH_REF, "GITHUB_REF", "refs/tags/v1", False),
        ):
            if content.count(command) != 1:
                raise SystemExit("human promotion " + name + " runtime command missing: " + label)
            result = subprocess.run(["bash", "-e", "-c", command],
                                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value},
                                    capture_output=True, check=False)
            if (result.returncode == 0) != allow:
                raise SystemExit("human promotion " + name + " runtime branch drift: " + label)
    for event, allow in (("push", True), ("workflow_dispatch", True), ("pull_request", False), ("", False)):
        result = subprocess.run(["bash", "-e", "-c", EVENT],
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GITHUB_EVENT_NAME": event},
                                capture_output=True, check=False)
        if (result.returncode == 0) != allow:
            raise SystemExit("human promotion writer event runtime drift: " + event)
    print("PASS: human promotion publisher/independent PR-push branch runtime (12 cases), writer event runtime (4 cases)")


def runtime_sha_proof(publisher: str, independent: str) -> None:
    """Execute human-promotion review SHA admission; tests never authorize promotion."""
    cases = (
        ("lowercase hex", "a" * 40, True),
        ("numeric hex", "0" * 40, True),
        ("short SHA", "a" * 39, False),
        ("long SHA", "a" * 41, False),
        ("uppercase SHA", "A" * 40, False),
        ("nonhex SHA", "g" * 40, False),
        ("empty SHA", "", False),
        ("literal shell substitution", "$(echo unexpected)", False),
    )
    for source_label, source_text, count in (
        ("publisher", publisher, 2),
        ("independent", independent, 1),
    ):
        if source_text.count(SHA_FORMAT) != count:
            raise SystemExit("human promotion SHA predicate unreachable: " + source_label)
        for label, value, allowed in cases:
            command = 'expected="${PROBE_SHA:-}"\n' + SHA_FORMAT
            env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PROBE_SHA": value}
            result = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
            if (result.returncode == 0) != allowed:
                raise SystemExit("human promotion SHA predicate drift: " + source_label + " " + label)
    print(f"PASS: human promotion publisher/independent SHA runtime ({len(cases) * 2} cases)")

def runtime_diagnostic_redaction(publisher: str) -> None:
    """Execute the exact human-promotion diagnostic writer in isolation."""
    start = "          python - <<'PY'\n"
    end = "          PY\n"
    if publisher.count(start) != 1 or publisher.count(end) != 1:
        raise SystemExit("human promotion diagnostic writer not uniquely reachable")
    inline = publisher.split(start, 1)[1].split(end, 1)[0]
    script = "\n".join(line[10:] for line in inline.splitlines()) + "\n"
    with tempfile.TemporaryDirectory(prefix="human-promotion-diagnostic-") as tmpdir:
        env = os.environ.copy()
        env.update({
            "SOURCE_SHA": "f" * 40,
            "VALIDATION_EXIT_CODE": "29",
            "SENSITIVE_CANARY": "CANARY_DO_NOT_PERSIST_GHI",
        })
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=tmpdir, env=env,
            capture_output=True, text=True, check=False,
        )
        if result.returncode:
            raise SystemExit("human promotion isolated diagnostic failed: " + result.stderr[:500])
        output = Path(tmpdir) / "docs/fixtures/memory-os-operability/backup-restore-promotion-review-diagnostic.last.json"
        payload = json.loads(output.read_text(encoding="utf-8"))
        if payload.get("output") != "REDACTED: promotion review validation failed; consult CI job logs":
            raise SystemExit("human promotion diagnostic persisted raw validator output")
        if payload.get("sourceCommitSha") != "f" * 40 or payload.get("exitCode") != 29:
            raise SystemExit("human promotion diagnostic source/exit binding drift")
        if payload.get("containsSecrets") is not False or payload.get("reviewCreated") is not False:
            raise SystemExit("human promotion diagnostic secret/review flags drift")
        if payload.get("trafficChanged") is not False or payload.get("productionReady") is not False:
            raise SystemExit("human promotion diagnostic traffic/readiness flags drift")
        if payload.get("productionEvidence") is not False:
            raise SystemExit("human promotion diagnostic production evidence drift")
        if "CANARY_DO_NOT_PERSIST_GHI" in output.read_text(encoding="utf-8"):
            raise SystemExit("human promotion diagnostic persisted synthetic canary")

        output.chmod(0o640)
        second = subprocess.run([sys.executable, "-c", script], cwd=tmpdir, env=env,
                                capture_output=True, text=True, check=False, timeout=15)
        if second.returncode or stat.S_IMODE(output.stat().st_mode) != 0o640:
            raise SystemExit("human promotion diagnostic failed to preserve existing mode")
        previous = output.read_bytes()
        for label, anchor in (("replace", "os.replace(tmp_name, path)"),
                              ("fsync", "os.fsync(handle.fileno())")):
            if script.count(anchor) != 1:
                raise SystemExit("human promotion diagnostic fault anchor drift: " + label)
            mutated = script.replace(anchor, "raise OSError('synthetic promotion " + label + " failure')", 1)
            outcome = subprocess.run([sys.executable, "-c", mutated], cwd=tmpdir, env=env,
                                     capture_output=True, text=True, check=False, timeout=15)
            if outcome.returncode == 0 or "synthetic promotion " + label + " failure" not in outcome.stderr:
                raise SystemExit("human promotion diagnostic intended fault not reached: " + label)
            if output.read_bytes() != previous or stat.S_IMODE(output.stat().st_mode) != 0o640:
                raise SystemExit("human promotion diagnostic failure altered previous bytes/mode: " + label)
            if list(output.parent.glob(".backup-restore-promotion-review-diagnostic.last.json.*.tmp")):
                raise SystemExit("human promotion diagnostic failure leaked temporary file: " + label)
        outside = Path(tmpdir) / "external-promotion-canary"
        outside.write_bytes(b"EXTERNAL_PROMOTION_CANARY")
        output.unlink()
        output.symlink_to(outside)
        outcome = subprocess.run([sys.executable, "-c", script], cwd=tmpdir, env=env,
                                 capture_output=True, text=True, check=False, timeout=15)
        if outcome.returncode == 0 or "target must not be a symlink" not in outcome.stderr:
            raise SystemExit("human promotion diagnostic accepted symlink destination")
        if not output.is_symlink() or outside.read_bytes() != b"EXTERNAL_PROMOTION_CANARY":
            raise SystemExit("human promotion diagnostic followed external symlink")
        if list(output.parent.glob(".backup-restore-promotion-review-diagnostic.last.json.*.tmp")):
            raise SystemExit("human promotion diagnostic symlink failure leaked temporary file")
    print("PASS: human promotion diagnostic redaction/atomic runtime (5 cases)")


def negatives(publisher: str, independent: str) -> None:
    publisher_cases = (
        ("PR target", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("script trigger", '      - "' + SELF + '"\n', ""),
        ("independent trigger", '      - "' + INDEPENDENT + '"\n', ""),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("PR credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("writer credentials", "          persist-credentials: true\n", ""),
        ("PR base", PR_BASE, ""),
        ("writer branch", PUSH_REF, ""),
        ("writer event", EVENT, ""),
        ("SHA format", SHA_FORMAT, 'test -n "$expected"'),
        ("broad publisher scope", PUBLISHER_SCOPE, "    if: github.event_name != 'pull_request'\n"),
        ("PR self guard", "\n          python " + SELF + "\n", ""),
        ("HEAD identity", 'test "$(git rev-parse HEAD)" = "$expected"', "true"),
        ("PR SHA source", 'expected="' + D + '{{ github.event.pull_request.head.sha }}"', 'expected="$GITHUB_SHA"'),
        ("writer SHA source", 'expected="' + D + '{GITHUB_SHA:-}"', 'expected="$PR_HEAD_SHA"'),
        ("root write token", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("PR write token", "      contents: read\n", "      contents: write\n"),
        ("writer token removed", "      contents: write\n", "      contents: read\n"),
        ("capture step removed", CAPTURE, ""),
        ("unreviewed Action", CAPTURE, "      - uses: unreviewed/action@v1\n" + CAPTURE),
        ("unreviewed shell", CAPTURE, "      - run: echo unreviewed\n" + CAPTURE),
        ("raw diagnostic", "              'output': 'REDACTED: promotion review validation failed; consult CI job logs',\n", "              'output': Path('/tmp/backup-restore-promotion-review.log').read_text(),\n"),
        ("raw CI log", '          printf "Promotion review validation exit code: %s (raw validator log suppressed)\\n" "$code"\n', '          cat "$log"\n'),
        ("missing redaction", "              'output': 'REDACTED: promotion review validation failed; consult CI job logs',\n", ""),
        ("diagnostic symlink guard", "          if path.is_symlink():\n", ""),
    )
    independent_cases = (
        ("PR target", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("publisher trigger", '      - "' + PUBLISHER + '"\n', ""),
        ("self trigger", '      - "' + INDEPENDENT + '"\n', ""),
        ("script trigger", '      - "' + SELF + '"\n', ""),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("persist credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("PR base", PR_BASE, ""),
        ("push branch", PUSH_REF, ""),
        ("event scope", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", "    if: always()\n"),
        ("self execution", "          python " + SELF + "\n", ""),
        ("injected Action", "      - name: Prove human promotion source admission\n", "      - uses: unreviewed/action@v1\n      - name: Prove human promotion source admission\n"),
        ("injected shell", "      - name: Prove human promotion source admission\n", "      - run: echo unreviewed\n      - name: Prove human promotion source admission\n"),
    )
    publisher_blob_only = {"unreviewed Action", "unreviewed shell"}
    independent_blob_only = {"injected Action", "injected shell"}
    if (len(publisher_cases), len(independent_cases)) != (26, 13):
        raise SystemExit("human promotion source negative population drift")
    if sum(label in publisher_blob_only for label, _, _ in publisher_cases) != 2 or sum(label in independent_blob_only for label, _, _ in independent_cases) != 2:
        raise SystemExit("human promotion source digest-only population drift")
    for target, cases in (("publisher", publisher_cases), ("independent", independent_cases)):
        for label, old, new in cases:
            original = publisher if target == "publisher" else independent
            if old not in original:
                raise SystemExit("human promotion negative fixture missing: " + target + " " + label)
            mutated = original.replace(old, new, 1)
            if mutated == original:
                raise SystemExit("human promotion negative fixture unchanged: " + target + " " + label)
            try:
                if target == "publisher":
                    validate(mutated, independent, check_publisher_blob=label in publisher_blob_only)
                else:
                    validate(publisher, mutated, check_independent_blob=label in independent_blob_only)
            except SystemExit:
                continue
            raise SystemExit("human promotion accepted source mutation: " + target + " " + label)
    print(f"PASS: human promotion publisher source admission ({len(publisher_cases) - 2} semantic + 2 blob-only negatives), independent source admission ({len(independent_cases) - 2} semantic + 2 blob-only negatives)")


def main() -> int:
    publisher = source(PUBLISHER)
    independent = source(INDEPENDENT)
    validate(publisher, independent)
    runtime(publisher, independent)
    runtime_sha_proof(publisher, independent)
    runtime_diagnostic_redaction(publisher)
    negatives(publisher, independent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
