#!/usr/bin/env python3
"""Fail-closed source and event admission for human-approved recovery objective CI."""

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
PUBLISHER = ".github/workflows/recovery-objectives-admission.yml"
INDEPENDENT = ".github/workflows/recovery-objectives-admission-source-negative.yml"
SELF = "scripts/validate-memory-os-recovery-objectives-admission-workflow-negative.py"
REVIEWED_PUBLISHER = "dadbedca0f7464489638781118b993e571b50648"
REVIEWED_INDEPENDENT = "16c74a57a5e8b0f983a95e36aa3055c0ab96adae"
D = chr(36)
PR_BASE = 'test "' + D + '{GITHUB_BASE_REF:-}" = "so"'
PUSH_REF = 'test "' + D + '{GITHUB_REF:-}" = "refs/heads/so"'
EVENT = '[[ "' + D + '{GITHUB_EVENT_NAME:-}" == "push" || "' + D + '{GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]'
SHA_FORMAT = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
PUBLISHER_SCOPE = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
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
    ("root read token", "permissions:\n  contents: read\n", 1),
    ("writer write token", "      contents: write\n", 1),
    ("diagnostic fixed redaction", "              'output': 'REDACTED: recovery objective validation failed; consult CI job logs',\n", 1),
    ("raw CI log suppression", '          printf "Recovery objective validation exit code: %s (raw validator log suppressed)\\n" "$code"\n', 1),
    ("fixed stage output", '          echo "failure_stage=$stage" >> "$GITHUB_OUTPUT"\n', 1),
    ("fixed stage diagnostic", '          printf "Recovery objective validation stage: %s (fixed class; raw validator log suppressed)\\n" "$stage"\n', 1),
    ("no raw diagnostic tail", "text[-12000:]", 0),
    ("no raw CI log echo", '          cat "$log"\n', 0),
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
        raise SystemExit("recovery objective CI source missing or substituted: " + relative) from exc


def validate(publisher: str, independent: str) -> None:
    for name, content, required, digest in (
        ("publisher", publisher, MAIN_REQUIRED, REVIEWED_PUBLISHER),
        ("independent", independent, INDEPENDENT_REQUIRED, REVIEWED_INDEPENDENT),
    ):
        for label, token, count in required:
            if content.count(token) != count:
                raise SystemExit("recovery objective " + name + " source drift: " + label)
        data = content.encode("utf-8")
        blob = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        if hashlib.sha1(blob).hexdigest() != digest:
            raise SystemExit("recovery objective " + name + " complete source drift")


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
                raise SystemExit("recovery objective " + name + " runtime command missing: " + label)
            result = subprocess.run(["bash", "-e", "-c", command],
                                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value},
                                    capture_output=True, check=False)
            if (result.returncode == 0) != allow:
                raise SystemExit("recovery objective " + name + " runtime branch drift: " + label)
    for event, allow in (("push", True), ("workflow_dispatch", True), ("pull_request", False), ("", False)):
        result = subprocess.run(["bash", "-e", "-c", EVENT],
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GITHUB_EVENT_NAME": event},
                                capture_output=True, check=False)
        if (result.returncode == 0) != allow:
            raise SystemExit("recovery objective writer event runtime drift: " + event)
    print("PASS: recovery objective publisher/independent PR-push branch runtime (12 cases), writer event runtime (4 cases)")


def runtime_sha_proof(publisher: str, independent: str) -> None:
    """Exercise the exact reviewed 40-hex source SHA predicate with safe/unsafe inputs."""
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
            raise SystemExit("recovery objective SHA predicate unreachable: " + source_label)
        for label, value, allowed in cases:
            command = 'expected="${PROBE_SHA:-}"\n' + SHA_FORMAT
            env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PROBE_SHA": value}
            result = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
            if (result.returncode == 0) != allowed:
                raise SystemExit("recovery objective SHA predicate drift: " + source_label + " " + label)
    print(f"PASS: recovery objective publisher/independent SHA runtime ({len(cases) * 2} cases)")

def runtime_diagnostic_redaction(publisher: str) -> None:
    """Run the exact inline diagnostic writer in an isolated directory."""
    start = "          python - <<'PY'\n"
    end = "          PY\n"
    if publisher.count(start) != 1 or publisher.count(end) != 1:
        raise SystemExit("recovery objective diagnostic writer is not uniquely reachable")
    inline = publisher.split(start, 1)[1].split(end, 1)[0]
    script = "\n".join(line[10:] for line in inline.splitlines()) + "\n"
    with tempfile.TemporaryDirectory(prefix="recovery-objective-diagnostic-") as tmpdir:
        env = os.environ.copy()
        env.update({
            "SOURCE_SHA": "c" * 40,
            "VALIDATION_EXIT_CODE": "17",
            "SENSITIVE_CANARY": "CANARY_DO_NOT_PERSIST_789",
        })
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=tmpdir, env=env,
            capture_output=True, text=True, check=False,
        )
        if result.returncode:
            raise SystemExit("recovery objective isolated diagnostic failed: " + result.stderr[:500])
        output = Path(tmpdir) / "docs/fixtures/memory-os-operability/recovery-objectives-admission-diagnostic.last.json"
        payload = json.loads(output.read_text(encoding="utf-8"))
        if payload.get("output") != "REDACTED: recovery objective validation failed; consult CI job logs":
            raise SystemExit("recovery objective diagnostic persisted raw validator output")
        if payload.get("sourceCommitSha") != "c" * 40 or payload.get("exitCode") != 17:
            raise SystemExit("recovery objective diagnostic source/exit drift")
        if payload.get("containsSecrets") is not False or payload.get("objectiveCreated") is not False:
            raise SystemExit("recovery objective diagnostic secret/objective flags drift")
        if payload.get("productionEvidence") is not False or payload.get("productionReady") is not False:
            raise SystemExit("recovery objective diagnostic evidence/readiness flags drift")
        if "CANARY_DO_NOT_PERSIST_789" in output.read_text(encoding="utf-8"):
            raise SystemExit("recovery objective diagnostic leaked synthetic canary")
        output.chmod(0o640)
        positive = subprocess.run([sys.executable, "-c", script], cwd=tmpdir, env=env,
                                  capture_output=True, text=True, timeout=15, check=False)
        if positive.returncode or stat.S_IMODE(output.stat().st_mode) != 0o640:
            raise SystemExit("recovery objective diagnostic failed to preserve existing mode")
        previous = output.read_bytes()
        for label, before in (("replace", "os.replace(tmp_name, path)"),
                              ("fsync", "os.fsync(handle.fileno())")):
            if script.count(before) != 1:
                raise SystemExit("recovery objective diagnostic fault anchor drift: " + label)
            failure = subprocess.run([sys.executable, "-c", script.replace(
                before, "raise OSError('synthetic recovery objective diagnostic " + label + " failure')", 1)],
                cwd=tmpdir, env=env, capture_output=True, text=True, timeout=15, check=False)
            if failure.returncode == 0 or "synthetic recovery objective diagnostic " + label + " failure" not in failure.stderr:
                raise SystemExit("recovery objective diagnostic intended fault not reached: " + label)
            if output.read_bytes() != previous or stat.S_IMODE(output.stat().st_mode) != 0o640:
                raise SystemExit("recovery objective diagnostic fault altered prior bytes/mode: " + label)
            if list(output.parent.glob(".recovery-objectives-admission-diagnostic.last.json.*.tmp")):
                raise SystemExit("recovery objective diagnostic fault left temporary file: " + label)
        outside = Path(tmpdir) / "external-recovery-objective-canary"
        outside.write_bytes(previous)
        output.unlink()
        output.symlink_to(outside)
        symlink = subprocess.run([sys.executable, "-c", script], cwd=tmpdir, env=env,
                                 capture_output=True, text=True, timeout=15, check=False)
        if symlink.returncode == 0 or "target must not be a symlink" not in symlink.stderr:
            raise SystemExit("recovery objective diagnostic accepted symlink destination")
        if not output.is_symlink() or outside.read_bytes() != previous:
            raise SystemExit("recovery objective diagnostic altered external symlink canary")
        if list(output.parent.glob(".recovery-objectives-admission-diagnostic.last.json.*.tmp")):
            raise SystemExit("recovery objective diagnostic symlink rejection left temporary file")
    print("PASS: recovery objective diagnostic redaction/atomic runtime (5 cases)")


def runtime_failure_stage(publisher: str) -> None:
    """Execute the actual validation shell with synthetic private failures."""
    heading = "      - name: Validate explicit recovery objectives authority\n"
    following = "      - name: Commit bounded objective authority\n"
    if publisher.count(heading) != 1 or publisher.count(following) != 1:
        raise SystemExit("recovery objective class-only validation step missing")
    block = publisher.split(heading, 1)[1].split(following, 1)[0]
    if block.count("        run: |\n") != 1:
        raise SystemExit("recovery objective class-only shell source missing")
    run = block.split("        run: |\n", 1)[1]
    lines = run.splitlines()
    if any(not line.startswith("          ") for line in lines):
        raise SystemExit("recovery objective class-only shell indentation drift")
    body = "\n".join(line[10:] for line in lines) + "\n"
    expected_stages = (
        "PY_COMPILE", "ADMISSION_NEGATIVE", "DIGEST_NEGATIVE",
        "APPEND_ROLLBACK_NEGATIVE", "RECONCILE_NEGATIVE", "RECONCILE",
        "OBJECTIVE_VALIDATOR", "OPERABILITY_VALIDATOR",
    )
    marker = "PRIVATE_RECOVERY_OBJECTIVE_STAGE_CANARY"
    with tempfile.TemporaryDirectory(prefix="recovery-objective-stage-") as tmp:
        root = Path(tmp)
        log = root / "private.log"
        if body.count("log=/tmp/recovery-objectives-admission.log") != 1:
            raise SystemExit("recovery objective private log source drift")
        body = body.replace("log=/tmp/recovery-objectives-admission.log", "log=" + str(log))
        shell = (
            "CALLS=0\n"
            "python() {\n"
            "  CALLS=$((CALLS+1))\n"
            "  if [[ \"$CALLS\" == \"$FAIL_AT\" ]]; then\n"
            "    printf 'PRIVATE_RECOVERY_OBJECTIVE_STAGE_CANARY\\n' >&2\n"
            "    return 17\n"
            "  fi\n"
            "  return 0\n"
            "}\n" + body
        )
        for fail_at in range(9):
            output = root / "output"
            output.write_text("", encoding="utf-8")
            env = {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "GITHUB_OUTPUT": str(output),
                "FAIL_AT": str(fail_at),
            }
            completed = subprocess.run(
                ["bash", "-c", shell], cwd=root, env=env,
                capture_output=True, text=True, check=False, timeout=15,
            )
            expected = "PASS" if fail_at == 0 else expected_stages[fail_at - 1]
            code = 0 if fail_at == 0 else 17
            observed = output.read_text(encoding="utf-8")
            if completed.returncode != 0 or observed != (
                f"exit_code={code}\nfailure_stage={expected}\n"
            ):
                raise SystemExit("recovery objective class-only stage output drift")
            if (f"Recovery objective validation stage: {expected} "
                    not in completed.stdout or marker in completed.stdout
                    or marker in completed.stderr):
                raise SystemExit("recovery objective class-only stage diagnostic private/output drift")
            if fail_at and marker not in log.read_text(encoding="utf-8"):
                raise SystemExit("recovery objective synthetic failure was not exercised")
    print("PASS: recovery objective class-only validation stage runtime (9 cases)")


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
        ("writer token removed", "      contents: write\n", "      contents: read\n"),
        ("unreviewed Action", "      - name: Capture exact recovery objective authority source\n", "      - uses: unreviewed/action@v1\n      - name: Capture exact recovery objective authority source\n"),
        ("unreviewed shell", "      - name: Capture exact recovery objective authority source\n", "      - run: echo unreviewed\n      - name: Capture exact recovery objective authority source\n"),
        ("appended command", '          echo "SOURCE_SHA=$expected" >> "$GITHUB_ENV"\n', '          echo "SOURCE_SHA=$expected" >> "$GITHUB_ENV"\n          echo unreviewed\n'),
        ("raw diagnostic", "              'output': 'REDACTED: recovery objective validation failed; consult CI job logs',\n", "              'output': Path('/tmp/recovery-objectives-admission.log').read_text(),\n"),
        ("raw CI log", '          printf "Recovery objective validation exit code: %s (raw validator log suppressed)\\n" "$code"\n', '          cat "$log"\n'),
        ("missing redaction", "              'output': 'REDACTED: recovery objective validation failed; consult CI job logs',\n", ""),
        ("symlink guard", "          if path.is_symlink():\n              raise SystemExit('recovery objective diagnostic target must not be a symlink')\n", ""),
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
        ("injected Action", "      - name: Prove recovery objective source admission\n", "      - uses: unreviewed/action@v1\n      - name: Prove recovery objective source admission\n"),
        ("injected shell", "      - name: Prove recovery objective source admission\n", "      - run: echo unreviewed\n      - name: Prove recovery objective source admission\n"),
    )
    for target, cases in (("publisher", publisher_cases), ("independent", independent_cases)):
        for label, old, new in cases:
            original = publisher if target == "publisher" else independent
            if old not in original:
                raise SystemExit("recovery objective negative fixture missing: " + target + " " + label)
            mutated = original.replace(old, new, 1)
            if mutated == original:
                raise SystemExit("recovery objective negative fixture unchanged: " + target + " " + label)
            try:
                validate(mutated, independent) if target == "publisher" else validate(publisher, mutated)
            except SystemExit:
                continue
            raise SystemExit("recovery objective accepted source mutation: " + target + " " + label)
    print(f"PASS: recovery objective publisher source admission ({len(publisher_cases)} negatives), independent source admission ({len(independent_cases)} negatives)")


def main() -> int:
    publisher = source(PUBLISHER)
    independent = source(INDEPENDENT)
    validate(publisher, independent)
    runtime(publisher, independent)
    runtime_sha_proof(publisher, independent)
    runtime_diagnostic_redaction(publisher)
    runtime_failure_stage(publisher)
    negatives(publisher, independent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
