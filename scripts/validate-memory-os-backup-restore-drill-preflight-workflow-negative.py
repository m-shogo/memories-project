#!/usr/bin/env python3
"""Independent fail-closed source and event/ref admission for restore preflight publisher."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ".github/workflows/backup-restore-drill-preflight.yml"
GUARD_PATH = ".github/workflows/backup-restore-drill-preflight-source-negative.yml"
SELF_PATH = "scripts/validate-memory-os-backup-restore-drill-preflight-workflow-negative.py"
MAIN_BLOB = "355bfae32bbe476d604707212b5d48c557c4e81c"
GUARD_BLOB = "cdcfc001168b18173441671f1fe30417984f3bba"
GUARD_TRIGGER_PATHS = (
    ".github/workflows/backup-restore-drill-preflight.yml",
    ".github/workflows/backup-restore-drill-preflight-source-negative.yml",
    "scripts/validate-memory-os-backup-restore-drill-preflight-workflow-negative.py",
)
D = chr(36)
PR_BASE = 'test "' + D + '{GITHUB_BASE_REF:-}" = "so"'
PUSH_REF = 'test "' + D + '{GITHUB_REF:-}" = "refs/heads/so"'
EVENT = '[[ "' + D + '{GITHUB_EVENT_NAME:-}" == "push" || "' + D + '{GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]'
PR_HEAD = 'expected="' + D + '{{ github.event.pull_request.head.sha }}"'
PR_SHA_FORMAT = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
WRITER_SHA_FORMAT = '[[ "' + D + '{GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]'
PUBLISHER_SCOPE = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"

MAIN_REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("self trigger", '      - "' + SELF_PATH + '"\n', 2),
    ("independent trigger", '      - "' + GUARD_PATH + '"\n', 2),
    ("checkout pin", CHECKOUT, 2),
    ("setup pin", SETUP, 2),
    ("PR no credentials", "          persist-credentials: false\n", 1),
    ("publisher credentials", "          persist-credentials: true\n", 1),
    ("PR base", PR_BASE, 1),
    ("PR head source", PR_HEAD, 1),
    ("PR SHA format", PR_SHA_FORMAT, 1),
    ("writer SHA format", WRITER_SHA_FORMAT, 1),
    ("writer event", EVENT, 1),
    ("writer branch", PUSH_REF, 1),
    ("publisher scope", PUBLISHER_SCOPE, 1),
    ("PR and writer self execution", "\n          python " + SELF_PATH + "\n", 2),
    ("retry self execution", "\n            python " + SELF_PATH + "\n", 1),
    ("PR HEAD", 'test "$(git rev-parse HEAD)" = "$expected"', 1),
    ("writer HEAD", 'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"', 1),
    ("bounded latest source", "            git reset --hard origin/so\n", 1),
    ("root read permission", "permissions:\n  contents: read\n", 1),
    ("writer write permission", "      contents: write\n", 1),
    ("success writer job scope", "        if: steps.preflight.outputs.exit_code == '0' && github.ref == 'refs/heads/so'\n", 1),
    ("diagnostic failure-only scope", "        if: steps.preflight.outputs.exit_code != '0' && github.ref == 'refs/heads/so'\n", 1),
    ("bounded source retry", "          for reconcile_attempt in 1 2; do\n", 1),
    ("latest source CAS checks", "if [[ \"$(git rev-parse origin/so)\" != \"$SOURCE_SHA\" ]]; then", 4),
    ("bounded authority staging", "          git add \\\n              contracts/operations/backup-restore-drill-preflight-contract.v1.json \\\n              contracts/operations/production-operability-status.json\n", 1),
    ("nonforce writer push", "            git push origin HEAD:so", 1),
    ("diagnostic source identity", "              'sourceCommitSha': os.environ['SOURCE_SHA'],\n", 1),
    ("diagnostic NO_GO status", "              'productionReady': False,\n", 1),
    ("diagnostic durability", "                  os.fsync(handle.fileno())\n", 1),
    ("diagnostic atomic replacement", "              os.replace(tmp_name, path)\n", 1),
    ("diagnostic bounded staging", "          git add docs/fixtures/memory-os-operability/backup-restore-drill-preflight-diagnostic.last.json\n", 1),
    ("diagnostic fixed redaction", "              'output': 'REDACTED: preflight validator failed; consult CI job logs',\n", 1),
    ("CI raw log suppressed", '          printf "Preflight validation exit code: %s (raw validator log suppressed)\\n" "$code"\n', 1),
    ("no raw diagnostic tail", "text[-12000:]", 0),
    ("no raw CI log echo", '          cat "$log"\n', 0),
    ("PR checkout source", "ref: ${{ github.event.pull_request.head.sha }}", 1),
    ("writer checkout source", "ref: ${{ github.sha }}", 1),
    ("PR job scope", "    if: github.event_name == 'pull_request'\n", 1),
    ("PR job read token", "    permissions:\n      contents: read\n", 1),
    ("push trigger branch", "  push:\n    branches:\n      - so\n", 1),
    ("dispatch trigger", "  workflow_dispatch:\n", 1),
    ("diagnostic secret flag", "              'containsSecrets': False,\n", 1),
)

GUARD_REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("main trigger", '      - "' + MAIN_PATH + '"\n', 2),
    ("self trigger", '      - "' + GUARD_PATH + '"\n', 2),
    ("script trigger", '      - "' + SELF_PATH + '"\n', 2),
    ("checkout pin", CHECKOUT, 1),
    ("setup pin", SETUP, 1),
    ("no checkout credentials", "          persist-credentials: false\n", 1),
    ("PR base", PR_BASE, 1),
    ("push branch", PUSH_REF, 1),
    ("SHA format", PR_SHA_FORMAT, 1),
    ("self execution", "          python " + SELF_PATH + "\n", 1),
    ("root and job read permission", "  contents: read\n", 2),
    ("exact event job", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", 1),
    ("clean source", '          test -z "$(git status --porcelain)"\n', 2),
    ("checkout source", "ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}", 1),
    ("PR head environment", "PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}", 1),
    ("push trigger branch", "  push:\n    branches:\n      - so\n", 1),
    ("push event admission", 'elif [[ "${GITHUB_EVENT_NAME:-}" == "push" ]]; then', 1),
    ("push SHA source", 'expected="${GITHUB_SHA:-}"', 1),
)


def checked_source(relative: str) -> str:
    path = ROOT / relative
    try:
        if path.is_symlink() or not path.is_file():
            raise ValueError("not a regular source file")
        if path.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != relative:
            raise ValueError("source escapes repository")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, RuntimeError, ValueError) as exc:
        raise SystemExit("preflight CI source unavailable or substituted: " + relative) from exc


def validate_guard_trigger_reachability(
    guard: str, *, trigger_paths: tuple[str, ...] = GUARD_TRIGGER_PATHS
) -> None:
    """Pin both independent preflight source CI event path inventories."""
    if len(trigger_paths) != 3 or len(set(trigger_paths)) != 3:
        raise SystemExit("preflight independent CI trigger inventory shortened or duplicated")
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    end_marker = "\npermissions:\n"
    for marker in (pr_marker, push_marker, end_marker):
        if guard.count(marker) != 1:
            raise SystemExit("preflight independent CI event trigger marker drift")
    pr = guard.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push = guard.split(push_marker, 1)[1].split(end_marker, 1)[0]
    for event, block in (("pull_request", pr), ("push", push)):
        # Check every non-comment YAML line, including unquoted paths.
        # Synthetic mutations must fail without the reviewed source digest.
        actual = tuple(
            line for line in block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        approved = tuple('      - "' + item + '"' for item in trigger_paths)
        if actual != approved:
            raise SystemExit("preflight independent CI " + event + " exact trigger inventory drift")


def prove_guard_trigger_negatives(guard: str) -> None:
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    for event in ("pull_request", "push"):
        for item in GUARD_TRIGGER_PATHS:
            token = '      - "' + item + '"' + chr(10)
            if guard.count(token) != 2:
                raise SystemExit("preflight independent CI trigger mutation anchor drift: " + item)
            if event == "pull_request":
                mutated = guard.replace(token, "", 1)
            else:
                prefix, suffix = guard.split(push_marker, 1)
                mutated = prefix + push_marker + suffix.replace(token, "", 1)
            try:
                validate_guard_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("preflight independent CI accepted missing " + event + " trigger: " + item)
    try:
        validate_guard_trigger_reachability(guard, trigger_paths=GUARD_TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("preflight independent CI shortened trigger inventory accepted")
    for event, marker in (
        ("pull_request", "  pull_request:\n    branches:\n      - so\n    paths:\n"),
        ("push", push_marker),
    ):
        for label, injected in (
            ("quoted extra", '      - "unreviewed/**"\n'),
            ("quoted duplicate", '      - "' + GUARD_TRIGGER_PATHS[0] + '"\n'),
            ("unquoted extra", "      - unreviewed/**\n"),
            ("unquoted duplicate", "      - " + GUARD_TRIGGER_PATHS[0] + "\n"),
        ):
            if guard.count(marker) != 1:
                raise SystemExit("preflight independent CI addition marker drift: " + event)
            mutated = guard.replace(marker, marker + injected, 1)
            if mutated == guard:
                raise SystemExit("preflight independent CI addition fixture unchanged")
            try:
                validate_guard_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("preflight independent CI accepted " + event + " addition: " + label)
    print("PASS: preflight independent CI event-specific trigger reachability (6 removals; 8 additions; 1 shortened inventory negative)")


def validate(
    main: str, guard: str, *,
    check_publisher_blob: bool = True, check_independent_blob: bool = True,
) -> None:
    validate_guard_trigger_reachability(guard)
    for label, token, expected in MAIN_REQUIRED:
        if main.count(token) != expected:
            raise SystemExit("preflight publisher source drift: " + label)
    for label, token, expected in GUARD_REQUIRED:
        if guard.count(token) != expected:
            raise SystemExit("preflight independent guard source drift: " + label)
    for label, source, reviewed, check_blob in (
        ("publisher", main, MAIN_BLOB, check_publisher_blob),
        ("independent guard", guard, GUARD_BLOB, check_independent_blob),
    ):
        if check_blob:
            payload = source.encode("utf-8")
            blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
            if hashlib.sha1(blob).hexdigest() != reviewed:
                raise SystemExit("preflight " + label + " complete source drift")


def runtime_branch_proof(main: str, guard: str) -> None:
    for source_label, source in (("publisher", main), ("independent", guard)):
        for label, command, key, value, allowed in (
            ("PR so", PR_BASE, "GITHUB_BASE_REF", "so", True),
            ("PR main", PR_BASE, "GITHUB_BASE_REF", "main", False),
            ("PR missing", PR_BASE, "GITHUB_BASE_REF", "", False),
            ("push so", PUSH_REF, "GITHUB_REF", "refs/heads/so", True),
            ("push main", PUSH_REF, "GITHUB_REF", "refs/heads/main", False),
            ("push tag", PUSH_REF, "GITHUB_REF", "refs/tags/v1", False),
        ):
            if source.count(command) != 1:
                raise SystemExit("preflight runtime guard unreachable: " + source_label + " " + label)
            env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}
            result = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
            if (result.returncode == 0) != allowed:
                raise SystemExit("preflight runtime branch guard drift: " + source_label + " " + label)
    for label, event, allowed in (
        ("push", "push", True),
        ("dispatch", "workflow_dispatch", True),
        ("PR", "pull_request", False),
        ("unknown", "", False),
    ):
        result = subprocess.run(
            ["bash", "-e", "-c", EVENT],
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GITHUB_EVENT_NAME": event},
            capture_output=True,
            check=False,
        )
        if (result.returncode == 0) != allowed:
            raise SystemExit("preflight publisher runtime event drift: " + label)
    print("PASS: preflight publisher/independent PR-push branch runtime (12 cases), publisher event runtime (4 cases)")


def runtime_sha_proof(main: str, guard: str) -> None:
    """Execute the reviewed SHA predicates, including malformed and injection-shaped inputs."""
    cases = (
        ("lowercase hex", "a" * 40, True),
        ("numeric hex", "0" * 40, True),
        ("short SHA", "a" * 39, False),
        ("long SHA", "a" * 41, False),
        ("uppercase SHA", "A" * 40, False),
        ("nonhex SHA", "g" * 40, False),
        ("missing SHA", "", False),
        ("literal shell substitution", "$(echo unexpected)", False),
    )
    for source_label, source, predicate_label, command in (
        ("publisher", main, "PR", PR_SHA_FORMAT),
        ("publisher", main, "writer", WRITER_SHA_FORMAT),
        ("independent", guard, "source", PR_SHA_FORMAT),
    ):
        if source.count(command) != 1:
            raise SystemExit("preflight SHA runtime predicate unreachable: " + source_label + " " + predicate_label)
        script = command if predicate_label == "writer" else 'expected="${PROBE_SHA:-}"\n' + command
        for case_label, value, accepted in cases:
            env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PROBE_SHA": value, "GITHUB_SHA": value}
            result = subprocess.run(["bash", "-e", "-c", script], env=env, capture_output=True, check=False)
            if (result.returncode == 0) != accepted:
                raise SystemExit("preflight SHA runtime predicate drift: " + source_label + " " + predicate_label + " " + case_label)
    print(f"PASS: preflight publisher/independent exact SHA runtime ({len(cases) * 3} cases)")


def runtime_cas_proof(main: str) -> None:
    """Execute the reviewed four-way stale-source predicate with a synthetic git."""
    predicate = 'if [[ "$(git rev-parse origin/so)" != "$SOURCE_SHA" ]]; then'
    if main.count(predicate) != 4:
        raise SystemExit("preflight CAS runtime predicate unreachable or count drift")
    prefix = (
        "git() {\n"
        '  if [[ "$1" == "rev-parse" && "$2" == "origin/so" ]]; then\n'
        '    printf "%s\\n" "$REMOTE_SHA"\n'
        "  else\n"
        "    return 64\n"
        "  fi\n"
        "}\n"
    )
    script = prefix + predicate + "\n  exit 75\nfi\nexit 0\n"
    cases = (
        ("matching source", "a" * 40, "a" * 40, 0),
        ("stale source", "b" * 40, "a" * 40, 75),
        ("missing remote", "", "a" * 40, 75),
        ("missing source", "a" * 40, "", 75),
    )
    for label, remote, source, expected_code in cases:
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "REMOTE_SHA": remote,
            "SOURCE_SHA": source,
        }
        result = subprocess.run(
            ["bash", "-e", "-c", script], env=env, capture_output=True, check=False
        )
        if result.returncode != expected_code:
            raise SystemExit("preflight CAS runtime guard drift: " + label)
    print(f"PASS: preflight reviewed latest-source CAS runtime ({len(cases)} cases)")


def runtime_diagnostic_redaction_proof(main: str) -> None:
    """Execute the actual inline diagnostic writer in an isolated temporary directory."""
    start = "          python - <<'PY'\n"
    end = "          PY\n"
    if main.count(start) != 1 or main.count(end) != 1:
        raise SystemExit("preflight diagnostic inline writer is not uniquely reachable")
    inline = main.split(start, 1)[1].split(end, 1)[0]
    script = "\n".join(line[10:] for line in inline.splitlines()) + "\n"
    marker = "REDACTED: preflight validator failed; consult CI job logs"
    with tempfile.TemporaryDirectory(prefix="preflight-diagnostic-redaction-") as tmpdir:
        env = os.environ.copy()
        env.update({
            "SOURCE_SHA": "a" * 40,
            "PREFLIGHT_EXIT_CODE": "7",
            "SENSITIVE_CANARY": "CANARY_DO_NOT_PERSIST_123",
        })
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=tmpdir, env=env,
            capture_output=True, text=True, check=False,
        )
        if result.returncode:
            raise SystemExit("preflight isolated diagnostic writer failed: " + result.stderr[:500])
        output = Path(tmpdir) / "docs/fixtures/memory-os-operability/backup-restore-drill-preflight-diagnostic.last.json"
        payload = json.loads(output.read_text(encoding="utf-8"))
        if payload.get("output") != marker or payload.get("exitCode") != 7:
            raise SystemExit("preflight diagnostic persisted unreviewed output or exit code")
        if payload.get("sourceCommitSha") != "a" * 40 or payload.get("containsSecrets") is not False:
            raise SystemExit("preflight diagnostic source or secret flag drift")
        if payload.get("productionReady") is not False or payload.get("productionEvidence") is not False:
            raise SystemExit("preflight diagnostic forged readiness/evidence")
        if "CANARY_DO_NOT_PERSIST_123" in output.read_text(encoding="utf-8"):
            raise SystemExit("preflight diagnostic persisted synthetic sensitive content")
        output.chmod(0o640)
        mode_positive = subprocess.run([sys.executable, "-c", script], cwd=tmpdir, env=env,
                                       capture_output=True, text=True, timeout=15, check=False)
        if mode_positive.returncode or stat.S_IMODE(output.stat().st_mode) != 0o640:
            raise SystemExit("preflight diagnostic existing mode was not preserved")
        previous = output.read_bytes()
        for label, source, injected in (
            ("replace", "os.replace(tmp_name, path)", "raise OSError('synthetic preflight diagnostic replace failure')"),
            ("fsync", "os.fsync(handle.fileno())", "raise OSError('synthetic preflight diagnostic fsync failure')"),
        ):
            if script.count(source) != 1:
                raise SystemExit("preflight diagnostic failure anchor drift: " + label)
            failure = subprocess.run([sys.executable, "-c", script.replace(source, injected, 1)],
                                     cwd=tmpdir, env=env, capture_output=True, text=True,
                                     timeout=15, check=False)
            if failure.returncode == 0 or "synthetic preflight diagnostic " + label + " failure" not in failure.stderr:
                raise SystemExit("preflight diagnostic intended failure not reached: " + label)
            if output.read_bytes() != previous or stat.S_IMODE(output.stat().st_mode) != 0o640:
                raise SystemExit("preflight diagnostic failure mutated prior bytes/mode: " + label)
            if list(output.parent.glob(".backup-restore-drill-preflight-diagnostic.last.json.*.tmp")):
                raise SystemExit("preflight diagnostic failure left temporary file: " + label)
        outside = Path(tmpdir) / "external-preflight-diagnostic-canary"
        outside.write_bytes(previous)
        output.unlink()
        output.symlink_to(outside)
        symlink = subprocess.run([sys.executable, "-c", script], cwd=tmpdir, env=env,
                                 capture_output=True, text=True, timeout=15, check=False)
        if symlink.returncode == 0 or "target must not be a symlink" not in symlink.stderr:
            raise SystemExit("preflight diagnostic accepted symlinked output")
        if not output.is_symlink() or outside.read_bytes() != previous:
            raise SystemExit("preflight diagnostic symlink altered external file")
        if list(output.parent.glob(".backup-restore-drill-preflight-diagnostic.last.json.*.tmp")):
            raise SystemExit("preflight diagnostic symlink rejection left temporary file")
    print("PASS: preflight diagnostic redaction and atomic runtime (5 cases)")


def prove_negative_mutations(main: str, guard: str) -> None:
    publisher_cases = (
        ("PR checkout ref", "ref: ${{ github.event.pull_request.head.sha }}", "ref: ${{ github.sha }}"),
        ("writer checkout ref", "ref: ${{ github.sha }}", "ref: ${{ github.ref }}"),
        ("PR validation scope", "    if: github.event_name == 'pull_request'\n", "    if: always()\n"),
        ("PR job write escalation", "    permissions:\n      contents: read\n", "    permissions:\n      contents: write\n"),
        ("push trigger branch", "  push:\n    branches:\n      - so\n", "  push:\n"),
        ("dispatch trigger removed", "  workflow_dispatch:\n", ""),
        ("writer HEAD source", "test \"$(git rev-parse HEAD)\" = \"$GITHUB_SHA\"", "test \"$(git rev-parse HEAD)\" = \"$GITHUB_REF\""),
        ("PR target", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("self trigger", '      - "' + SELF_PATH + '"\n', ""),
        ("independent trigger", '      - "' + GUARD_PATH + '"\n', ""),
        ("checkout floating", CHECKOUT, "uses: actions/checkout@v4"),
        ("setup floating", SETUP, "uses: actions/setup-python@v5"),
        ("PR credential persistence", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("publisher credentials removed", "          persist-credentials: true\n", ""),
        ("PR base removed", PR_BASE, 'test -n "$GITHUB_BASE_REF"'),
        ("PR head source", PR_HEAD, 'expected="$GITHUB_SHA"'),
        ("PR SHA weakened", PR_SHA_FORMAT, 'test -n "$expected"'),
        ("writer SHA weakened", WRITER_SHA_FORMAT, 'test -n "$GITHUB_SHA"'),
        ("publisher event removed", EVENT, ""),
        ("publisher branch removed", PUSH_REF, ""),
        ("publisher broad admission", PUBLISHER_SCOPE, "    if: github.event_name != 'pull_request'\n"),
        ("PR self check removed", "\n          python " + SELF_PATH + "\n", "\n"),
        ("retry self check removed", "\n            python " + SELF_PATH + "\n", "\n"),
        ("PR HEAD removed", 'test "$(git rev-parse HEAD)" = "$expected"', "true"),
        ("writer HEAD removed", 'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"', "true"),
        ("latest reset removed", "            git reset --hard origin/so\n", ""),
        ("root permission widened", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("writer permission weakened", "      contents: write\n", "      contents: read\n"),
        ("injected Action", "      - name: Capture exact preflight authority source\n", "      - uses: unreviewed/action@v1\n      - name: Capture exact preflight authority source\n"),
        ("injected shell step", "      - name: Capture exact preflight authority source\n", "      - run: echo unreviewed\n      - name: Capture exact preflight authority source\n"),
        ("appended command", '          echo "SOURCE_SHA=$(git rev-parse HEAD)" >> "$GITHUB_ENV"\n', '          echo "SOURCE_SHA=$(git rev-parse HEAD)" >> "$GITHUB_ENV"\n          echo unreviewed\n'),
        ("success writer job scope", "        if: steps.preflight.outputs.exit_code == '0' && github.ref == 'refs/heads/so'\n", "        if: always()\n"),
        ("diagnostic failure-only scope", "        if: steps.preflight.outputs.exit_code != '0' && github.ref == 'refs/heads/so'\n", "        if: always()\n"),
        ("bounded source retry", "          for reconcile_attempt in 1 2; do\n", "          while true; do\n"),
        ("latest source CAS checks", "if [[ \"$(git rev-parse origin/so)\" != \"$SOURCE_SHA\" ]]; then", "if false; then"),
        ("bounded authority staging", "          git add \\\n              contracts/operations/backup-restore-drill-preflight-contract.v1.json \\\n              contracts/operations/production-operability-status.json\n", "          git add -A\n"),
        ("nonforce writer push", "            git push origin HEAD:so", "            git push --force origin HEAD:so"),
        ("diagnostic source identity", "              'sourceCommitSha': os.environ['SOURCE_SHA'],\n", "              'sourceCommitSha': 'unknown',\n"),
        ("diagnostic NO_GO status", "              'productionReady': False,\n", "              'productionReady': True,\n"),
        ("diagnostic durability", "                  os.fsync(handle.fileno())\n", "                  handle.flush()\n"),
        ("diagnostic atomic replacement", "              os.replace(tmp_name, path)\n", "              path.write_bytes(payload)\n"),
        ("diagnostic bounded staging", "          git add docs/fixtures/memory-os-operability/backup-restore-drill-preflight-diagnostic.last.json\n", "          git add -A\n"),
        ("diagnostic raw output regression", "              'output': 'REDACTED: preflight validator failed; consult CI job logs',\n", "              'output': Path('/tmp/backup-restore-drill-preflight.log').read_text(),\n"),
        ("CI raw log regression", '          printf "Preflight validation exit code: %s (raw validator log suppressed)\\n" "$code"\n', '          cat "$log"\n'),
        ("diagnostic false secret flag", "              'containsSecrets': False,\n", "              'containsSecrets': True,\n"),
    )
    independent_cases = (
        ("independent checkout source", "ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}", "ref: ${{ github.sha }}"),
        ("independent push branch", "  push:\n    branches:\n      - so\n", "  push:\n"),
        ("independent PR head env", "PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}", "PR_HEAD_SHA: ${{ github.sha }}"),
        ("independent exact HEAD", "test \"$(git rev-parse HEAD)\" = \"$expected\"", "test \"$(git rev-parse HEAD)\" = \"$GITHUB_REF\""),
        ("independent clean checkout", "test \"$(git rev-parse HEAD)\" = \"$expected\"\n          test -z \"$(git status --porcelain)\"", "test \"$(git rev-parse HEAD)\" = \"$expected\"\n          test -n \"$(git status --porcelain)\""),
        ("independent root token", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("independent job token", "    permissions:\n      contents: read\n", "    permissions:\n      contents: write\n"),
        ("independent event admission", "elif [[ \"${GITHUB_EVENT_NAME:-}\" == \"push\" ]]; then", "else"),
        ("independent push SHA source", "expected=\"${GITHUB_SHA:-}\"", "expected=\"${GITHUB_REF:-}\""),
        ("independent shell append", "          python scripts/validate-memory-os-backup-restore-drill-preflight-workflow-negative.py\n", "          python scripts/validate-memory-os-backup-restore-drill-preflight-workflow-negative.py\n          echo unreviewed\n"),
        ("PR target", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("main trigger", '      - "' + MAIN_PATH + '"\n', ""),
        ("self trigger", '      - "' + GUARD_PATH + '"\n', ""),
        ("script trigger", '      - "' + SELF_PATH + '"\n', ""),
        ("checkout floating", CHECKOUT, "uses: actions/checkout@v4"),
        ("setup floating", SETUP, "uses: actions/setup-python@v5"),
        ("credential persistence", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("PR base removed", PR_BASE, ""),
        ("push branch removed", PUSH_REF, ""),
        ("job scope widened", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", "    if: always()\n"),
        ("guard self execution removed", "          python " + SELF_PATH + "\n", ""),
        ("injected Action", "      - name: Prove preflight publisher source admission\n", "      - uses: unreviewed/action@v1\n      - name: Prove preflight publisher source admission\n"),
        ("injected shell", "      - name: Prove preflight publisher source admission\n", "      - run: echo unreviewed\n      - name: Prove preflight publisher source admission\n"),
    )
    semantic_counts = {"publisher": 0, "independent": 0}
    digest_counts = {"publisher": 0, "independent": 0}
    for target, cases in (("publisher", publisher_cases), ("independent", independent_cases)):
        for label, old, new in cases:
            source = main if target == "publisher" else guard
            if old not in source:
                raise SystemExit("preflight source negative fixture missing: " + target + " " + label)
            mutated = source.replace(old, new, 1)
            if mutated == source:
                raise SystemExit("preflight source negative fixture unchanged: " + target + " " + label)
            required = MAIN_REQUIRED if target == "publisher" else GUARD_REQUIRED
            semantic = any(mutated.count(token) != source.count(token) for _, token, _ in required)
            semantic_counts[target] += int(semantic)
            digest_counts[target] += int(not semantic)
            try:
                if target == "publisher":
                    validate(mutated, guard, check_publisher_blob=not semantic)
                else:
                    validate(main, mutated, check_independent_blob=not semantic)
            except SystemExit:
                continue
            raise SystemExit("preflight source negative accepted mutation: " + target + " " + label)
    if (semantic_counts["publisher"], digest_counts["publisher"], semantic_counts["independent"], digest_counts["independent"]) != (42, 3, 19, 4):
        raise SystemExit("preflight source negative semantic/digest population drift")
    print(f"PASS: preflight publisher source admission ({semantic_counts['publisher']} semantic + {digest_counts['publisher']} blob-only negatives), independent source admission ({semantic_counts['independent']} semantic + {digest_counts['independent']} blob-only negatives)")


def main() -> int:
    publisher = checked_source(MAIN_PATH)
    independent = checked_source(GUARD_PATH)
    validate(publisher, independent)
    prove_guard_trigger_negatives(independent)
    runtime_branch_proof(publisher, independent)
    runtime_sha_proof(publisher, independent)
    runtime_cas_proof(publisher)
    runtime_diagnostic_redaction_proof(publisher)
    prove_negative_mutations(publisher, independent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
