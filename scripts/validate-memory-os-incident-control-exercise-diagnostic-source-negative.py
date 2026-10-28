#!/usr/bin/env python3
"""Read-only exact-source and fault-injection proof for both incident-control diagnostic writers."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/incident-control-exercise.yml"
INDEPENDENT = ".github/workflows/incident-control-exercise-diagnostic-source-negative.yml"
SELF = "scripts/validate-memory-os-incident-control-exercise-diagnostic-source-negative.py"
REVIEWED_PUBLISHER = "de440f0fb34a48742397482150aae36397da7f4a"
REVIEWED_INDEPENDENT = "7498034f740e5b6e807a053d457026995b719955"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
PR_BASE = 'test "${GITHUB_BASE_REF:-}" = "so"'
PUSH_REF = 'test "${GITHUB_REF:-}" = "refs/heads/so"'
SHA_FORMAT = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'


PUBLISHER_PUSH_TRIGGER_PATHS = tuple([".github/workflows/incident-control-exercise.yml","contracts/operations/incident-control-exercise-contract.v1.json","contracts/operations/backup-restore-contract.v1.json","scripts/run-memory-os-incident-control-exercise.py","scripts/validate-memory-os-incident-control-exercise.py","scripts/validate-memory-os-incident-control-exercise-reconcile-negative.py","scripts/reconcile-memory-os-incident-control-exercise.py","scripts/reconcile-memory-os-backup-restore.py","scripts/validate-memory-os-incident-response.py","scripts/validate-memory-os-incident-tabletop.py","scripts/validate-memory-os-operability.py","scripts/validate-memory-os-authorization.py","scripts/validate-memory-os-postgresql-rls.py","scripts/validate-memory-os-database-commit-outage.py","scripts/validate-memory-os-local-logical-restore.py","scripts/validate-memory-os-chaos-failure-drills-v2.py","scripts/validate-memory-os-local-object-version-restore.py","scripts/validate-memory-os-migration-lifecycle.py","scripts/validate-memory-os-version-compatibility.py","scripts/validate-memory-os-mixed-version-candidate.py","scripts/validate-memory-os-backup-local-foundations.py","scripts/validate-memory-os-backup-restore.py","scripts/validate-memory-os-parser-security.py","scripts/validate-memory-os-parser-restart-matrix.py","scripts/validate-memory-os-parser-inflight-cancellation.py","requirements-security-validation.txt"])
INDEPENDENT_TRIGGER_PATHS = tuple([".github/workflows/incident-control-exercise.yml",".github/workflows/incident-control-exercise-diagnostic-source-negative.yml","scripts/validate-memory-os-incident-control-exercise-diagnostic-source-negative.py"])



def validate_trigger_reachability(
    publisher: str, independent: str, *,
    publisher_paths: tuple[str, ...] | None = None,
    independent_paths: tuple[str, ...] | None = None,
) -> None:
    """Bind reviewed publisher push/schedule/dispatch and independent PR/push events."""
    pub = PUBLISHER_PUSH_TRIGGER_PATHS if publisher_paths is None else publisher_paths
    ind = INDEPENDENT_TRIGGER_PATHS if independent_paths is None else independent_paths
    if (len(pub) != len(PUBLISHER_PUSH_TRIGGER_PATHS) or
        len(ind) != len(INDEPENDENT_TRIGGER_PATHS) or
        len(set(pub)) != len(pub) or len(set(ind)) != len(ind)):
        raise SystemExit("incident control event-specific trigger inventory shortened/duplicated")
    pub_paths = "".join('      - "' + path + '"\n' for path in pub)
    ind_paths = "".join('      - "' + path + '"\n' for path in ind)
    expected_pub = (
        "name: Incident Control Exercise\n\non:\n"
        "  push:\n    branches:\n      - so\n    paths:\n" + pub_paths +
        '  schedule:\n    - cron: "11 22 * * *"\n  workflow_dispatch:\n'
    )
    expected_ind = (
        "name: Incident Control Exercise Diagnostic Source Negative\n\non:\n"
        "  pull_request:\n    branches:\n      - so\n    paths:\n" + ind_paths +
        "  push:\n    branches:\n      - so\n    paths:\n" + ind_paths
    )
    for label, value, expected in (
        ("publisher", publisher, expected_pub), ("independent", independent, expected_ind)
    ):
        if value.count("\npermissions:\n") != 1:
            raise SystemExit("incident control " + label + " permissions boundary drift")
        header = value.split("\npermissions:\n", 1)[0]
        if header != expected:
            raise SystemExit("incident control " + label + " exact event trigger drift")
        # The exact event prefix does not prove a later YAML root mapping
        # cannot shadow on, permissions or jobs after that boundary.
        expected_roots = (
            ["name: Incident Control Exercise", "on:", "permissions:",
             "concurrency:", "jobs:"]
            if label == "publisher" else
            ["name: Incident Control Exercise Diagnostic Source Negative",
             "on:", "permissions:", "jobs:"]
        )
        observed_roots = [
            row for row in value.splitlines()
            if row.strip() and not row[0].isspace()
            and not row.lstrip().startswith("#")
        ]
        if observed_roots != expected_roots:
            raise SystemExit("incident control " + label + " root YAML key shadow drift")
        # Preserve the publisher's reviewed write authority and the
        # independent CI's read-only authority against YAML leaf shadows.
        permission_lines = value.split("\npermissions:\n", 1)[1].splitlines()
        permission_rows = []
        for row in permission_lines:
            if row.strip() and not row[0].isspace():
                break
            if row.strip() and not row.lstrip().startswith("#"):
                permission_rows.append(row)
        expected_permission = "  contents: write" if label == "publisher" else "  contents: read"
        if permission_rows != [expected_permission]:
            raise SystemExit("incident control " + label + " permission leaf shadow drift")


def prove_trigger_reachability_negatives(publisher: str, independent: str) -> None:
    """Exercise omissions, additions, duplicates, inventory truncation and event topology."""
    cases = (
        ("publisher push", publisher, "  push:\n    branches:\n      - so\n    paths:\n",
         "  schedule:\n", PUBLISHER_PUSH_TRIGGER_PATHS, True),
        ("independent PR", independent, "  pull_request:\n    branches:\n      - so\n    paths:\n",
         "  push:\n", INDEPENDENT_TRIGGER_PATHS, False),
        ("independent push", independent, "  push:\n    branches:\n      - so\n    paths:\n",
         "\npermissions:\n", INDEPENDENT_TRIGGER_PATHS, False),
    )
    omitted = added = 0
    for label, value, start, end, paths, is_publisher in cases:
        if value.count(start) != 1 or value.count(end) != 1:
            raise SystemExit("incident control trigger negative anchor drift: " + label)
        begin = value.index(start) + len(start)
        finish = value.index(end, begin)
        block = value[begin:finish]
        mutations = []
        for path in paths:
            token = '      - "' + path + '"\n'
            if block.count(token) != 1:
                raise SystemExit("incident control trigger omission anchor drift: " + path)
            mutations.append(("omission " + path, block.replace(token, "", 1), True))
        mutations.extend((
            ("quoted extra", block + '      - "unreviewed/**"\n', False),
            ("quoted duplicate", block + '      - "' + paths[0] + '"\n', False),
            ("unquoted extra", block + "      - unreviewed/**\n", False),
            ("unquoted duplicate", block + "      - " + paths[0] + "\n", False),
        ))
        for name, replacement, is_omission in mutations:
            mutated = value[:begin] + replacement + value[finish:]
            if mutated == value:
                raise SystemExit("incident control unchanged trigger negative: " + name)
            try:
                if is_publisher:
                    validate_trigger_reachability(mutated, independent)
                else:
                    validate_trigger_reachability(publisher, mutated)
            except SystemExit:
                pass
            else:
                raise SystemExit("incident control accepted " + label + " " + name)
            omitted += int(is_omission)
            added += int(not is_omission)
    for label, kwargs in (
        ("publisher", {"publisher_paths": PUBLISHER_PUSH_TRIGGER_PATHS[:-1]}),
        ("independent", {"independent_paths": INDEPENDENT_TRIGGER_PATHS[:-1]}),
    ):
        try:
            validate_trigger_reachability(publisher, independent, **kwargs)
        except SystemExit:
            pass
        else:
            raise SystemExit("incident control accepted shortened " + label + " inventory")
    for label, mutated in (
        ("publisher PR introduction", publisher.replace(
            "  schedule:\n", "  pull_request:\n    branches:\n      - so\n  schedule:\n", 1)),
        ("publisher schedule deletion", publisher.replace(
            '  schedule:\n    - cron: "11 22 * * *"\n', "", 1)),
        ("independent dispatch introduction", independent.replace(
            "\npermissions:\n", "  workflow_dispatch:\n\npermissions:\n", 1)),
    ):
        try:
            if label.startswith("publisher"):
                validate_trigger_reachability(mutated, independent)
            else:
                validate_trigger_reachability(publisher, mutated)
        except SystemExit:
            pass
        else:
            raise SystemExit("incident control accepted unreviewed event topology: " + label)
    # All reviewed event-prefix bytes remain intact in these mutations.
    # Require the intended semantic root-shadow diagnostic, not a blob failure.
    root_shadows = (
        ("spaced on", "on :\n  workflow_dispatch:\n"),
        ("quoted on", "'on':\n  workflow_dispatch:\n"),
        ("spaced permissions", "permissions :\n  contents: write\n"),
        ("spaced jobs", "jobs : {}\n"),
    )
    root_negative_count = 0
    for label, original, is_publisher in (
        ("publisher", publisher, True),
        ("independent", independent, False),
    ):
        for name, suffix in root_shadows:
            mutated = original + suffix
            try:
                if is_publisher:
                    validate_trigger_reachability(mutated, independent)
                else:
                    validate_trigger_reachability(publisher, mutated)
            except SystemExit as exc:
                expected = "incident control " + label + " root YAML key shadow drift"
                if str(exc) != expected:
                    raise SystemExit(
                        "incident control root shadow rejected for wrong reason: "
                        + label + " " + name + ": " + str(exc)
                    ) from exc
            else:
                raise SystemExit(
                    "incident control accepted root YAML shadow: " + label + " " + name
                )
            root_negative_count += 1
    if root_negative_count != 8:
        raise SystemExit("incident control root shadow fixture count drift")
    permission_negative_count = 0
    for label, original, is_publisher in (
        ("publisher", publisher, True),
        ("independent", independent, False),
    ):
        reviewed_leaf = "write" if is_publisher else "read"
        shadow_leaf = "read" if is_publisher else "write"
        anchor = "permissions:\n  contents: " + reviewed_leaf + "\n"
        if original.count(anchor) != 1:
            raise SystemExit("incident control permission negative anchor drift: " + label)
        for name, extra in (
            ("spaced", "  contents : " + shadow_leaf + "\n"),
            ("quoted", "  'contents': " + shadow_leaf + "\n"),
        ):
            mutated = original.replace(anchor, anchor + extra, 1)
            try:
                if is_publisher:
                    validate_trigger_reachability(mutated, independent)
                else:
                    validate_trigger_reachability(publisher, mutated)
            except SystemExit as exc:
                expected = "incident control " + label + " permission leaf shadow drift"
                if str(exc) != expected:
                    raise SystemExit(
                        "incident control permission shadow rejected for wrong reason: "
                        + label + " " + name + ": " + str(exc)
                    ) from exc
            else:
                raise SystemExit(
                    "incident control accepted permission leaf shadow: " + label + " " + name
                )
            permission_negative_count += 1
    if permission_negative_count != 4:
        raise SystemExit("incident control permission leaf fixture count drift")
    print("PASS: incident control permission leaf shadows (4 exact-diagnostic negatives)")
    if (omitted, added) != (32, 12):
        raise SystemExit("incident control trigger negative coverage drift")
    print("PASS: incident control exact event triggers (32 omissions; 12 additions; "
          "2 shortened inventories; 3 event topology; 8 root shadow negatives)")


def source(relative: str) -> str:
    path = ROOT / relative
    try:
        if path.is_symlink() or not path.is_file():
            raise ValueError("not regular")
        if path.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != relative:
            raise ValueError("escaped root")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        raise SystemExit("incident control source missing/substituted: " + relative) from exc


def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def validate(publisher: str, independent: str) -> None:
    validate_trigger_reachability(publisher, independent)
    publisher_required = (
        ("  schedule:\n", 1),
        ("  workflow_dispatch:\n", 1),
        ("permissions:\n  contents: write\n", 1),
        ("uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262", 1),
        ("uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", 1),
        ("persist-credentials: true", 1),
        ("github.ref == 'refs/heads/so'", 1),
        ('test "${GITHUB_REF:-}" = "refs/heads/so"', 1),
        ('[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]', 1),
        ('test "$(git rev-parse HEAD)" = "${GITHUB_SHA}"', 1),
        ("def guarded_target(path: Path) -> Path:", 2),
        ("def atomic_write_text(path: Path, text: str) -> None:", 2),
        ("if candidate.is_symlink():", 2),
        ("if not target.parent.is_dir():", 2),
        ("if target.exists() and not target.is_file():", 2),
        ("os.fchmod(fd, existing_mode)", 2),
        ("os.fsync(handle.fileno())", 2),
        ("os.replace(temporary, target)", 2),
        ("temporary.unlink()", 2),
        ("guarded_target(path).read_text(encoding='utf-8')", 1),
        ("'Incident control exercise completed; raw output withheld.'", 1),
        ("'Incident control exercise and validation completed; raw output withheld.'", 1),
    )
    independent_required = (
        "  pull_request:\n    branches:\n      - so\n",
        "  push:\n    branches:\n      - so\n",
        '      - "' + PUBLISHER + '"', '      - "' + INDEPENDENT + '"',
        '      - "' + SELF + '"', CHECKOUT, SETUP,
        "          persist-credentials: false\n", PR_BASE, PUSH_REF, SHA_FORMAT,
        "          python " + SELF, "permissions:\n  contents: read\n",
        "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')",
        'test "$(git rev-parse HEAD)" = "$expected"',
        'test -z "$(git status --porcelain)"',
    )
    for token, count in publisher_required:
        if publisher.count(token) != count:
            raise SystemExit("incident control publisher source drift: " + token)
    for token in independent_required:
        if token not in independent:
            raise SystemExit("incident control independent source drift: " + token)
    if blob(publisher) != REVIEWED_PUBLISHER or blob(independent) != REVIEWED_INDEPENDENT:
        raise SystemExit("incident control complete Git blob source drift")
    if ("Path('/tmp/incident-control-exercise.log').read_text" in publisher or
        "Path('/tmp/incident-control-validation.log').read_text" in publisher or
        "path.parent.mkdir(parents=True, exist_ok=True)" in publisher):
        raise SystemExit("incident control raw diagnostic or unchecked parent regression")


def inline_writers(publisher: str) -> tuple[str, str]:
    markers = (
        "          EXERCISE_EXIT_CODE=\"$code\" python - <<'PY'\n",
        "          VALIDATION_EXIT_CODE=\"$code\" python - <<'PY'\n",
    )
    if any(publisher.count(marker) != 1 for marker in markers):
        raise SystemExit("incident control inline diagnostic writers missing/ambiguous")
    scripts = []
    for marker in markers:
        start = publisher.index(marker) + len(marker)
        end = publisher.index("\n          PY\n", start)
        lines = publisher[start:end].splitlines()
        if not lines or any(line and not line.startswith("          ") for line in lines):
            raise SystemExit("incident control inline writer indentation drift")
        scripts.append("\n".join(line[10:] if line else "" for line in lines) + "\n")
    return scripts[0], scripts[1]


def run_writer(code: str, root: Path, success: bool, fault: str = "") -> None:
    injection = """
import os
if os.environ.get('INJECT_FAULT') == 'replace':
    def fail_replace(*args, **kwargs):
        raise OSError('synthetic replace failure')
    os.replace = fail_replace
if os.environ.get('INJECT_FAULT') == 'fsync':
    def fail_fsync(*args, **kwargs):
        raise OSError('synthetic fsync failure')
    os.fsync = fail_fsync
"""
    env = dict(os.environ, SOURCE_SHA="a" * 40, EXERCISE_EXIT_CODE="0",
               VALIDATION_EXIT_CODE="0", INJECT_FAULT=fault)
    result = subprocess.run([sys.executable, "-c", injection + code],
                            cwd=root, env=env, capture_output=True, text=True,
                            timeout=10, check=False)
    if (result.returncode == 0) != success:
        raise SystemExit("incident control diagnostic runtime exit drift: " + (fault or "path"))


def diagnostic_runtime(publisher: str) -> None:
    first, second = inline_writers(publisher)
    with tempfile.TemporaryDirectory(prefix="incident-control-diagnostic-") as tmp:
        root = Path(tmp)
        parent = root / "docs/fixtures/memory-os-operability"
        parent.mkdir(parents=True)
        path = parent / "incident-control-exercise-diagnostic.last.json"
        leftovers = lambda: list(parent.glob("." + path.name + ".*.tmp"))

        run_writer(first, root, True)
        value = json.loads(path.read_text(encoding="utf-8"))
        if (value.get("output") != "Incident control exercise completed; raw output withheld." or
            value.get("sourceCommitSha") != "a" * 40 or
            value.get("productionEvidence") is not False or
            value.get("humanTabletopCompleted") is not False or
            value.get("containsSecrets") is not False or leftovers()):
            raise SystemExit("incident control first diagnostic output drift")
        path.chmod(0o640)
        run_writer(first, root, True)
        if stat.S_IMODE(path.stat().st_mode) != 0o640:
            raise SystemExit("incident control first writer mode drift")
        run_writer(second, root, True)
        value = json.loads(path.read_text(encoding="utf-8"))
        if (value.get("validationResult") != "PASS" or
            value.get("output") != "Incident control exercise and validation completed; raw output withheld." or
            stat.S_IMODE(path.stat().st_mode) != 0o640 or leftovers()):
            raise SystemExit("incident control second diagnostic output/mode drift")

        original = path.read_bytes()
        for writer in (first, second):
            for fault in ("replace", "fsync"):
                run_writer(writer, root, False, fault)
                if (path.read_bytes() != original or
                    stat.S_IMODE(path.stat().st_mode) != 0o640 or leftovers()):
                    raise SystemExit("incident control atomic failure changed prior bytes/mode/temp")

        external = root / "external-canary"
        external.write_bytes(b"external\n")
        path.unlink()
        path.symlink_to(external)
        for writer in (first, second):
            run_writer(writer, root, False)
        if external.read_bytes() != b"external\n" or leftovers():
            raise SystemExit("incident control followed target symlink")
        path.unlink()

        outside = root / "outside"
        outside.mkdir()
        (outside / path.name).write_bytes(b"outside\n")
        old_parent = root / "old-parent"
        parent.rename(old_parent)
        parent.symlink_to(outside, target_is_directory=True)
        for writer in (first, second):
            run_writer(writer, root, False)
        if (outside / path.name).read_bytes() != b"outside\n":
            raise SystemExit("incident control followed parent symlink")
        parent.unlink()
        old_parent.rename(parent)

        shutil.rmtree(parent)
        for writer in (first, second):
            run_writer(writer, root, False)
        if parent.exists():
            raise SystemExit("incident control created missing parent")
        parent.mkdir()
        path.mkdir()
        for writer in (first, second):
            run_writer(writer, root, False)
        if not path.is_dir() or leftovers():
            raise SystemExit("incident control accepted nonregular target")
    print("PASS: incident control two-writer diagnostic redaction/atomic/symlink runtime (15 cases)")


def predicate_runtime(independent: str) -> None:
    for cmd in (PR_BASE, PUSH_REF, SHA_FORMAT):
        if independent.count(cmd) != 1:
            raise SystemExit("incident control source predicate missing/ambiguous")
    for cmd, key, value, allow in (
        (PR_BASE, "GITHUB_BASE_REF", "so", True),
        (PR_BASE, "GITHUB_BASE_REF", "main", False),
        (PR_BASE, "GITHUB_BASE_REF", "", False),
        (PUSH_REF, "GITHUB_REF", "refs/heads/so", True),
        (PUSH_REF, "GITHUB_REF", "refs/heads/main", False),
        (PUSH_REF, "GITHUB_REF", "refs/tags/v1", False),
    ):
        r = subprocess.run(["bash", "-e", "-c", cmd],
                           env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value},
                           capture_output=True, check=False)
        if (r.returncode == 0) != allow:
            raise SystemExit("incident control branch/base runtime drift")
    for value, allow in (("a" * 40, True), ("0" * 40, True), ("a" * 39, False),
                         ("A" * 40, False), ("g" * 40, False), ("", False)):
        r = subprocess.run(["bash", "-e", "-c", SHA_FORMAT],
                           env=dict(os.environ, expected=value), capture_output=True, check=False)
        if (r.returncode == 0) != allow:
            raise SystemExit("incident control SHA runtime drift")
    print("PASS: incident control branch/base (6) and SHA (6) runtime cases")


def mutation_negatives(publisher: str, independent: str) -> None:
    p_cases = (
        ("raw exercise", "'Incident control exercise completed; raw output withheld.'", "Path('/tmp/incident-control-exercise.log').read_text()"),
        ("raw validation", "'Incident control exercise and validation completed; raw output withheld.'", "Path('/tmp/incident-control-validation.log').read_text()"),
        ("symlink", "if candidate.is_symlink():", "if False:"),
        ("missing parent", "if not target.parent.is_dir():", "if False:"),
        ("regular", "if target.exists() and not target.is_file():", "if False:"),
        ("mode", "os.fchmod(fd, existing_mode)", "pass"),
        ("fsync", "os.fsync(handle.fileno())", "pass"),
        ("atomic", "os.replace(temporary, target)", "target.write_text(text)"),
        ("cleanup", "temporary.unlink()", "pass"),
        ("guarded read", "guarded_target(path).read_text(encoding='utf-8')", "path.read_text(encoding='utf-8')"),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("persist writer credentials", "persist-credentials: true", "persist-credentials: false"),
        ("writer job ref", "github.ref == 'refs/heads/so'", "github.ref != 'refs/heads/so'"),
        ("writer source ref", 'test "${GITHUB_REF:-}" = "refs/heads/so"', "true"),
        ("writer source SHA", '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]', "true"),
        ("writer source HEAD", 'test "$(git rev-parse HEAD)" = "${GITHUB_SHA}"', "true"),
    )
    i_cases = (
        ("PR base", PR_BASE, "true"), ("push branch", PUSH_REF, "true"),
        ("SHA format", SHA_FORMAT, 'test -n "$expected"'),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("self trigger", '      - "' + SELF + '"', ""),
        ("publisher trigger", '      - "' + PUBLISHER + '"', ""),
        ("root write", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("job scope", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')", "    if: always()"),
    )
    for name, original, cases in (("publisher", publisher, p_cases), ("independent", independent, i_cases)):
        for label, old, new in cases:
            if old not in original:
                raise SystemExit("incident control mutation fixture missing: " + name + "/" + label)
            altered = original.replace(old, new, 1)
            if altered == original:
                raise SystemExit("incident control mutation fixture unchanged: " + name + "/" + label)
            try:
                validate(altered, independent) if name == "publisher" else validate(publisher, altered)
            except SystemExit:
                continue
            raise SystemExit("incident control accepted mutation: " + name + "/" + label)
    print("PASS: incident control publisher (17) and independent (10) source mutations")


def writer_identity_runtime(publisher: str) -> None:
    marker = "      - name: Confirm exact clean source\n        run: |\n"
    if publisher.count(marker) != 1:
        raise SystemExit("incident control writer identity step missing")
    start = publisher.index(marker) + len(marker)
    end = publisher.find("\n      - name:", start)
    lines = publisher[start:end if end >= 0 else len(publisher)].splitlines()
    if any(line and not line.startswith("          ") for line in lines):
        raise SystemExit("incident control writer identity indentation drift")
    code = "\n".join(line[10:] if line else "" for line in lines) + "\n"
    if 'echo "SOURCE_SHA=' not in code:
        raise SystemExit("incident control writer identity source capture missing")
    code = code.split('echo "SOURCE_SHA=', 1)[0]
    head = "a" * 40
    cases = (
        ("push", "refs/heads/so", head, True),
        ("schedule", "refs/heads/so", head, True),
        ("workflow_dispatch", "refs/heads/so", head, True),
        ("pull_request", "refs/heads/so", head, False),
        ("push", "refs/heads/main", head, False),
        ("push", "refs/tags/v1", head, False),
        ("push", "refs/heads/so", "A" * 40, False),
        ("push", "refs/heads/so", "a" * 39, False),
        ("push", "refs/heads/so", "b" * 40, False),
        ("schedule", "", head, False),
    )
    with tempfile.TemporaryDirectory(prefix="incident-control-writer-source-") as temp:
        root = Path(temp)
        stub = root / "git"
        stub.write_text("#!/bin/sh\n"
                        "if [ \"$1\" = \"status\" ]; then exit 0; fi\n"
                        "if [ \"$1\" = \"fetch\" ]; then exit 0; fi\n"
                        "if [ \"$1\" = \"rev-parse\" ]; then printf '%s\\n' \"$STUB_HEAD\"; exit 0; fi\n"
                        "exit 1\n", encoding="utf-8")
        stub.chmod(0o755)
        for event, ref, sha, accepted in cases:
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_EVENT_NAME=event, GITHUB_REF=ref, GITHUB_SHA=sha, STUB_HEAD=head)
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", code],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != accepted:
                raise AssertionError("incident control writer event/ref/SHA shell drift: " + str((event, ref, sha, result.returncode)))
    print("PASS: incident control writer actual event/ref/SHA shell runtime (10 cases)")

def main() -> int:
    publisher, independent = source(PUBLISHER), source(INDEPENDENT)
    validate(publisher, independent)
    prove_trigger_reachability_negatives(publisher, independent)
    predicate_runtime(independent)
    writer_identity_runtime(publisher)
    mutation_negatives(publisher, independent)
    diagnostic_runtime(publisher)
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
