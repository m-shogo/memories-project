#!/usr/bin/env python3
"""Read-only exact-source and runtime negative proof for local migration recovery CI."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/local-migration-recovery-artifact.yml"
INDEPENDENT = ".github/workflows/local-migration-recovery-source-negative.yml"
SELF = "scripts/validate-memory-os-local-migration-recovery-workflow-source-negative.py"
PUBLISHER_SHA = "c28a2f7cc363bf8c787c7f1670d484e569dbc1b3"
INDEPENDENT_SHA = "094d794db2d11846a4a174ac7ab976b4f81e304a"

PUBLISHER_TRIGGER_PATHS = (
    ".github/workflows/local-migration-recovery-artifact.yml",
    ".github/workflows/local-migration-recovery-source-negative.yml",
    "scripts/validate-memory-os-local-migration-recovery-workflow-source-negative.py",
    "contracts/operations/local-migration-recovery-artifact-contract.v1.json",
    "contracts/operations/migration-evidence-registry-contract.v1.json",
    "contracts/operations/migration-lifecycle-contract.v1.json",
    "infra/postgresql/security/**",
    "scripts/run-memory-os-local-migration-recovery-artifact.sh",
    "scripts/validate-memory-os-local-migration-recovery-artifact.py",
    "scripts/reconcile-memory-os-local-migration-recovery-artifact.py",
    "scripts/memory_os_migration_recovery_point.py",
    "scripts/register-memory-os-migration-rehearsal-evidence.py",
    "scripts/validate-memory-os-migration-evidence-registry.py",
    "scripts/reconcile-memory-os-migration-evidence-registry.py",
)
INDEPENDENT_TRIGGER_PATHS = (
    ".github/workflows/local-migration-recovery-artifact.yml",
    ".github/workflows/local-migration-recovery-source-negative.yml",
    "scripts/validate-memory-os-local-migration-recovery-workflow-source-negative.py",
    "scripts/validate-memory-os-local-migration-recovery-artifact-reconcile-negative.py",
    "scripts/reconcile-memory-os-local-migration-recovery-artifact.py",
)
LOCAL_NEGATIVE = "scripts/validate-memory-os-local-migration-recovery-artifact-reconcile-negative.py"
LOCAL_NEGATIVE_SHA = "1e5dccbbf21c0f4dcf8888f6a0e6cf7fa84aebcd"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
WRITER_SCOPE = "    if: >-\n      (github.event_name == 'push' || github.event_name == 'workflow_dispatch') &&\n      github.ref == 'refs/heads/so' &&\n      (github.event_name != 'push' ||\n       (!contains(github.event.head_commit.message, 'test(migration): record local recovery artifact rehearsal') &&\n        !contains(github.event.head_commit.message, 'docs(migration): register local recovery artifact rehearsal')))"
PR_BASE = 'test "${GITHUB_BASE_REF:-}" = "so"'
WRITER_REF = 'test "${GITHUB_REF:-}" = "refs/heads/so"'
PR_SHA = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
WRITER_SHA = '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]'



def validate_trigger_reachability(
    source: str, *, publisher: bool, trigger_paths: tuple[str, ...] | None = None
) -> None:
    """Require complete reviewed PR/push path inventories independently of Git blob SHA."""
    expected = PUBLISHER_TRIGGER_PATHS if publisher else INDEPENDENT_TRIGGER_PATHS
    paths = expected if trigger_paths is None else trigger_paths
    if len(paths) != len(expected) or len(set(paths)) != len(expected):
        raise SystemExit("local recovery CI trigger inventory shortened or duplicated")
    pr = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    end = "  workflow_dispatch:\n" if publisher else "\npermissions:\n"
    first, second = (push, pr) if publisher else (pr, push)
    if any(source.count(marker) != 1 for marker in (first, second, end)):
        raise SystemExit("local recovery CI trigger marker drift")
    if not (source.index(first) < source.index(second) < source.index(end)):
        raise SystemExit("local recovery CI trigger event order drift")
    for event, start, stop in (("first", first, second), ("second", second, end)):
        block = source.split(start, 1)[1].split(stop, 1)[0]
        actual = tuple(line for line in block.splitlines()
                       if line.strip() and not line.lstrip().startswith("#"))
        approved = tuple('      - "' + path + '"' for path in paths)
        if actual != approved:
            raise SystemExit("local recovery CI " + event + " exact trigger inventory drift")


def prove_trigger_reachability_negatives(publisher: str, independent: str) -> None:
    """Exercise all single-event omissions, additions and shortened inventories."""
    pr = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    for label, source, paths, is_publisher in (
        ("publisher", publisher, PUBLISHER_TRIGGER_PATHS, True),
        ("independent", independent, INDEPENDENT_TRIGGER_PATHS, False),
    ):
        first, second = (push, pr) if is_publisher else (pr, push)
        end = "  workflow_dispatch:\n" if is_publisher else "\npermissions:\n"
        for event, start, stop in (("first", first, second), ("second", second, end)):
            start_index = source.index(start) + len(start)
            end_index = source.index(stop, start_index)
            block = source[start_index:end_index]
            for path in paths:
                token = '      - "' + path + '"\n'
                if block.count(token) != 1:
                    raise SystemExit("local recovery CI trigger mutation anchor drift: " + path)
                mutated = source[:start_index] + block.replace(token, "", 1) + source[end_index:]
                try:
                    validate_trigger_reachability(mutated, publisher=is_publisher)
                except SystemExit:
                    pass
                else:
                    raise SystemExit("local recovery CI accepted missing " + label + " " + event + " trigger: " + path)
            for name, injection in (
                ("quoted extra", '      - "unreviewed/**"\n'),
                ("quoted duplicate", '      - "' + paths[0] + '"\n'),
                ("unquoted extra", "      - unreviewed/**\n"),
                ("unquoted duplicate", "      - " + paths[0] + "\n"),
            ):
                mutated = source[:start_index] + injection + source[start_index:]
                try:
                    validate_trigger_reachability(mutated, publisher=is_publisher)
                except SystemExit:
                    pass
                else:
                    raise SystemExit("local recovery CI accepted " + label + " " + event + " " + name)
        try:
            validate_trigger_reachability(source, publisher=is_publisher, trigger_paths=paths[:-1])
        except SystemExit:
            pass
        else:
            raise SystemExit("local recovery CI accepted shortened " + label + " inventory")
    print("PASS: local recovery CI event triggers (38 removals; 16 additions; 2 shortened inventory negatives)")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("local migration recovery CI source guard: " + message)


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
    ("ref: so", 1),
    ("'output': 'REDACTED: local migration recovery failed; raw output withheld'", 1),
    ("raw log suppressed", 1),
    ("os.replace(temp_name, path)", 1),
    ("os.fsync(handle.fileno())", 1),
    ("os.fchmod(handle.fileno(), existing_mode)", 1),
    ("os.unlink(temp_name)", 1),
    ('cat "$log"', 0),
    ("text[-10000:]", 0),
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
    ('      - "' + LOCAL_NEGATIVE + '"\n', 2),
    ('      - "scripts/reconcile-memory-os-local-migration-recovery-artifact.py"\n', 2),
    (CHECKOUT, 1),
    (SETUP, 1),
    ("persist-credentials: false", 1),
    (PR_BASE, 1),
    (WRITER_REF, 1),
    (PR_SHA, 1),
    ("python " + SELF, 1),
    ("python " + LOCAL_NEGATIVE, 1),
    ('git clone --no-hardlinks --no-checkout . "$temp/repo"', 1),
    ('git -C "$temp/repo" checkout --detach "$(git rev-parse HEAD)"', 1),
    ('test -z "$(git -C "$temp/repo" status --porcelain)"', 2),
    ("permissions:\n  contents: read\n", 1),
    ("      contents: read\n", 1),
)



def validate_yaml_authority(content: str, *, publisher: bool) -> None:
    """Bind effective event, root and read-only permission YAML authority."""
    label = "publisher" if publisher else "independent"
    name = ("Local Migration Recovery Artifact Rehearsal" if publisher
            else "Local Migration Recovery Source Negative")
    paths = PUBLISHER_TRIGGER_PATHS if publisher else INDEPENDENT_TRIGGER_PATHS

    def event(key: str) -> str:
        return ("  " + key + ":\n    branches:\n      - so\n    paths:\n"
                + "".join('      - "' + item + '"\n' for item in paths))

    expected_events = (
        event("push") + event("pull_request") + "  workflow_dispatch:\n"
        if publisher else event("pull_request") + event("push")
    )
    expected_header = "name: " + name + "\n\non:\n" + expected_events
    if (content.count("\npermissions:\n") != 1
            or content.split("\npermissions:\n", 1)[0] != expected_header):
        raise SystemExit("local recovery " + label + " exact event header drift")
    roots = [
        line for line in content.splitlines()
        if line.strip() and not line[0].isspace()
        and not line.lstrip().startswith("#")
    ]
    expected_roots = ["name: " + name, "on:", "permissions:"]
    if publisher:
        expected_roots.append("concurrency:")
    expected_roots.append("jobs:")
    if roots != expected_roots:
        raise SystemExit("local recovery " + label + " root YAML key shadow drift")
    permission_rows = []
    for line in content.split("\npermissions:\n", 1)[1].splitlines():
        if line.strip() and not line[0].isspace():
            break
        if line.strip() and not line.lstrip().startswith("#"):
            permission_rows.append(line)
    if permission_rows != ["  contents: read"]:
        raise SystemExit("local recovery " + label + " permission leaf shadow drift")


def prove_yaml_authority_negatives(publisher: str, independent: str) -> None:
    total = 0
    for label, content, is_publisher in (
        ("publisher", publisher, True), ("independent", independent, False),
    ):
        validate_yaml_authority(content, publisher=is_publisher)
        cases = [
            ("extra event", content.replace("on:\n", "on:\n  issues:\n", 1),
             "exact event header drift"),
        ]
        for name, suffix in (
            ("spaced on", "on :\n  issues:\n"),
            ("quoted on", "'on':\n  issues:\n"),
            ("spaced permissions", "permissions :\n  contents: write\n"),
            ("spaced jobs", "jobs : {}\n"),
        ):
            cases.append((name, content + "\n" + suffix, "root YAML key shadow drift"))
        anchor = "permissions:\n  contents: read\n"
        if content.count(anchor) != 1:
            raise SystemExit("local recovery " + label + " permission mutation anchor drift")
        for name, extra in (
            ("spaced contents", "  contents : write\n"),
            ("quoted contents", "  'contents': write\n"),
        ):
            cases.append((name, content.replace(anchor, anchor + extra, 1),
                          "permission leaf shadow drift"))
        for name, altered, diagnostic in cases:
            if altered == content:
                raise SystemExit("local recovery YAML fixture unchanged: " + name)
            try:
                validate_yaml_authority(altered, publisher=is_publisher)
            except SystemExit as exc:
                expected = "local recovery " + label + " " + diagnostic
                if str(exc) != expected:
                    raise SystemExit(
                        "local recovery YAML wrong diagnostic: " + label + "/"
                        + name + ": " + str(exc)
                    ) from exc
            else:
                raise SystemExit("local recovery accepted YAML shadow: " + label + "/" + name)
            total += 1
    if total != 14:
        raise SystemExit("local recovery YAML fixture count drift")
    print("PASS: local recovery publisher/independent YAML event/root/permission (14 exact-diagnostic negatives)")



def validate_job_authority(publisher: str, independent: str) -> None:
    """Bind reviewed job identities, multi-line writer scope and nested permissions."""
    reviewed = (
        ("publisher", publisher, (
            ("validate-pr", "    if: github.event_name == 'pull_request'\n",
             "read", 10, ("if", "permissions", "runs-on", "timeout-minutes", "steps")),
            ("rehearse", WRITER_SCOPE + "\n",
             "write", 20, ("if", "permissions", "runs-on", "timeout-minutes",
                           "services", "env", "steps")),
        )),
        ("independent", independent, (
            ("source-negative",
             "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n",
             "read", 5, ("if", "permissions", "runs-on", "timeout-minutes", "steps")),
        )),
    )
    for label, content, jobs in reviewed:
        prefix = "local recovery " + label + " "
        if content.count("\njobs:\n") != 1:
            raise SystemExit(prefix + "job mapping shadow drift")
        body = content.split("\njobs:\n", 1)[1]
        sections: dict[str, list[str]] = {}
        mappings: list[str] = []
        current: str | None = None
        for line in body.splitlines():
            if (line.startswith("  ") and len(line) > 2 and line[2] != " "
                    and not line.lstrip().startswith("#")):
                current = line
                mappings.append(line)
                sections[current] = []
            elif current is not None:
                sections[current].append(line)
        if mappings != ["  " + name + ":" for name, *_ in jobs]:
            raise SystemExit(prefix + "job mapping shadow drift")
        for name, condition, scope, timeout, keys in jobs:
            lines = sections["  " + name + ":"]
            actual_keys = [
                line for line in lines
                if line.startswith("    ") and len(line) > 4 and line[4] != " "
                and not line.lstrip().startswith("#")
            ]
            expected_keys = [
                "    " + key + ":"
                + ((" >-" if name == "rehearse" else
                    " " + condition.splitlines()[0].split(": ", 1)[1]) if key == "if" else
                   (" ubuntu-latest" if key == "runs-on" else
                    " " + str(timeout) if key == "timeout-minutes" else ""))
                for key in keys
            ]
            if actual_keys != expected_keys:
                raise SystemExit(prefix + name + " job key shadow drift")
            section = "\n".join(lines) + "\n"
            if section.split("    permissions:\n", 1)[0] != condition:
                raise SystemExit(prefix + name + " job condition drift")
            leaves = []
            for line in section.split("    permissions:\n", 1)[1].splitlines():
                if line.startswith("    ") and len(line) > 4 and line[4] != " ":
                    break
                if line.strip() and not line.lstrip().startswith("#"):
                    leaves.append(line)
            if leaves != ["      contents: " + scope]:
                raise SystemExit(prefix + name + " job permission leaf shadow drift")


def prove_job_authority_negatives(publisher: str, independent: str) -> None:
    """Reject 38 job shadows with exact diagnostics, independently of Git blob checks."""
    validate_job_authority(publisher, independent)
    reviewed = (
        ("publisher", publisher, independent, (
            ("validate-pr", "    if: github.event_name == 'pull_request'\n", "read", 10),
            ("rehearse", WRITER_SCOPE + "\n", "write", 20),
        ), True),
        ("independent", independent, publisher, (
            ("source-negative",
             "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n",
             "read", 5),
        ), False),
    )
    total = 0
    for label, content, other, jobs, is_publisher in reviewed:
        for name, condition, scope, timeout in jobs:
            header = "  " + name + ":\n"
            if content.count(header) != 1:
                raise SystemExit("local recovery job mutation header drift: " + label + "/" + name)

            def in_job(before: str, after: str) -> str:
                prefix, suffix = content.split(header, 1)
                if before not in suffix:
                    raise SystemExit("local recovery job mutation anchor drift: " + name)
                return prefix + header + suffix.replace(before, after, 1)

            permission = "    permissions:\n      contents: " + scope + "\n"
            runner = "    runs-on: ubuntu-latest\n"
            time_limit = "    timeout-minutes: " + str(timeout) + "\n"
            steps = "    steps:\n"
            cases = [
                ("duplicate mapping", content + "\n" + header + "    runs-on: ubuntu-latest\n",
                 "job mapping shadow drift"),
                ("quoted mapping", content.replace(header, "  '" + name + "':\n", 1),
                 "job mapping shadow drift"),
                ("spaced mapping", content.replace(header, "  " + name + " :\n", 1),
                 "job mapping shadow drift"),
                ("condition shadow", in_job(condition, condition + "    if : true\n"),
                 name + " job key shadow drift"),
                ("permission shadow", in_job(permission, permission + "    permissions :\n      contents: write\n"),
                 name + " job key shadow drift"),
                ("runner shadow", in_job(runner, runner + "    runs-on : ubuntu-latest\n"),
                 name + " job key shadow drift"),
                ("timeout shadow", in_job(time_limit, time_limit + "    timeout-minutes : 1\n"),
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
            if name == "rehearse":
                cases.extend([
                    ("services shadow", in_job("    services:\n",
                                               "    services : {}\n    services:\n"),
                     name + " job key shadow drift"),
                    ("env shadow", in_job("    env:\n", "    env : {}\n    env:\n"),
                     name + " job key shadow drift"),
                ])
            for mutation, changed, diagnostic in cases:
                if changed == content:
                    raise SystemExit("local recovery unchanged job mutation: " + mutation)
                try:
                    if is_publisher:
                        validate_job_authority(changed, other)
                    else:
                        validate_job_authority(other, changed)
                except SystemExit as exc:
                    expected = "local recovery " + label + " " + diagnostic
                    if str(exc) != expected:
                        raise SystemExit("local recovery wrong job diagnostic: "
                                         + label + "/" + name + "/" + mutation + ": " + str(exc)) from exc
                else:
                    raise SystemExit("local recovery accepted job shadow: "
                                     + label + "/" + name + "/" + mutation)
                total += 1
    if total != 38:
        raise SystemExit("local recovery job negative inventory drift")
    print("PASS: local recovery publisher/independent nested job authority (38 exact-diagnostic negatives)")


def validate(publisher: str, independent: str) -> None:
    validate_trigger_reachability(publisher, publisher=True)
    validate_trigger_reachability(independent, publisher=False)
    validate_yaml_authority(publisher, publisher=True)
    validate_yaml_authority(independent, publisher=False)
    validate_job_authority(publisher, independent)
    check_source("publisher", publisher, PUBLISHER_SHA, PUBLISHER_REQUIRED)
    check_source("independent", independent, INDEPENDENT_SHA, INDEPENDENT_REQUIRED)
    check_source("local reconcile negative", read(LOCAL_NEGATIVE), LOCAL_NEGATIVE_SHA, ())


def negative_proofs(publisher: str, independent: str) -> None:
    cases = (
        ("publisher PR base", True, PR_BASE, "true"),
        ("publisher writer ref", True, WRITER_REF, "true"),
        ("publisher writer scope", True, WRITER_SCOPE, "    if: always()"),
        ("publisher PR SHA", True, PR_SHA, 'test -n "$expected"'),
        ("publisher writer SHA", True, WRITER_SHA, 'test -n "$GITHUB_SHA"'),
        ("publisher checkout pin", True, CHECKOUT, "uses: actions/checkout@v4"),
        ("publisher setup pin", True, SETUP, "uses: actions/setup-python@v5"),
        ("publisher event scope", True, "  workflow_dispatch:\n", "  pull_request_target:\n"),
        ("publisher digest-only drift", True, "\n", "\n# unauthorized publisher source drift\n"),
        ("publisher credentials", True, "persist-credentials: false", "persist-credentials: true"),
        ("publisher self guard", True, "python " + SELF, "echo skip"),
        ("publisher checkout ref", True, "ref: so", "ref: main"),
        ("publisher redaction", True, "'output': 'REDACTED: local migration recovery failed; raw output withheld'", "'output': text[-10000:]"),
        ("publisher log suppression", True, "raw log suppressed", "raw log exposed"),
        ("publisher atomic diagnostic replace", True, "os.replace(temp_name, path)", "path.write_text('unsafe')"),
        ("publisher diagnostic fsync", True, "os.fsync(handle.fileno())", "pass"),
        ("publisher diagnostic mode", True, "os.fchmod(handle.fileno(), existing_mode)", "pass"),
        ("independent PR base", False, PR_BASE, "true"),
        ("independent writer ref", False, WRITER_REF, "true"),
        ("independent SHA", False, PR_SHA, 'test -n "$expected"'),
        ("independent checkout pin", False, CHECKOUT, "uses: actions/checkout@v4"),
        ("independent setup pin", False, SETUP, "uses: actions/setup-python@v5"),
        ("independent event scope", False, "  push:\n    branches:\n      - so\n", "  workflow_dispatch:\n"),
        ("independent digest-only drift", False, "\n", "\n# unauthorized independent source drift\n"),
        ("independent credentials", False, "persist-credentials: false", "persist-credentials: true"),
        ("independent self guard", False, "python " + SELF, "echo skip"),
        ("independent local negative invocation", False, "python " + LOCAL_NEGATIVE, "echo skip"),
        ("independent clone exact checkout", False, 'git -C "$temp/repo" checkout --detach "$(git rev-parse HEAD)"', 'git -C "$temp/repo" checkout so'),
        ("independent clone cleanliness", False, 'test -z "$(git -C "$temp/repo" status --porcelain)"', "true"),
    )
    for label, publisher_case, before, after in cases:
        original = publisher if publisher_case else independent
        require(before in original, "mutation anchor missing: " + label)
        # Digest-only fixtures must preserve effective YAML semantics so
        # the Git blob guard, not the event/root guard, owns their rejection.
        changed = (original + after if "digest-only" in label
                   else original.replace(before, after, 1))
        require(changed != original, "mutation unchanged: " + label)
        try:
            validate(changed, independent) if publisher_case else validate(publisher, changed)
        except SystemExit as exc:
            # Require the actual source guard to reject for the expected reason.
            expected = ("local recovery CI trigger marker drift"
                        if label in {"publisher event scope", "independent event scope"}
                        else "complete Git blob drift" if "digest-only" in label
                        else "required source inventory drift")
            reason = str(exc)
            if label in {"publisher event scope", "independent event scope"}:
                require(reason == expected,
                        "negative rejected for wrong trigger reason: " + label + ": " + reason)
            elif label == "publisher writer scope":
                require(reason == "local recovery publisher rehearse job key shadow drift",
                        "negative rejected for wrong writer job reason: " + label + ": " + reason)
            else:
                require(reason.startswith("local migration recovery CI source guard: ")
                        and expected in reason,
                        "negative rejected for wrong reason: " + label + ": " + reason)
            continue
        raise SystemExit("local migration recovery source negative accepted: " + label)
    suite = read(LOCAL_NEGATIVE)
    try:
        check_source("local reconcile negative", suite + "\n# unauthorized local negative suite drift\n",
                     LOCAL_NEGATIVE_SHA, ())
    except SystemExit as exc:
        require("local reconcile negative complete Git blob drift" in str(exc),
                "local negative suite mutation rejected for wrong reason")
    else:
        raise SystemExit("local negative suite complete source drift accepted")
    print(f"PASS: local migration recovery CI source negatives ({len(cases) + 1} cases)")


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
    print("PASS: local migration recovery branch/SHA runtime (18 cases)")



def require_diagnostic_payload(raw: str) -> None:
    require("CANARY_DO_NOT_PERSIST_LOCAL_RECOVERY" not in raw,
            "local recovery diagnostic persisted sensitive canary")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit("local migration recovery CI source guard: diagnostic invalid JSON") from exc
    require(isinstance(value, dict), "local recovery diagnostic root must be object")
    require(set(value) == {
        "schemaVersion", "workflow", "sourceCommitSha", "failureStage",
        "result", "exitCode", "output", "containsSecrets", "productionTraffic",
        "productionCredentials", "productionEvidence", "productionReady",
    }, "local recovery diagnostic field inventory drift")
    require(value.get("schemaVersion") == "memory-os-validator-diagnostic.v1",
            "local recovery diagnostic schema drift")
    require(value.get("workflow") == "local-migration-recovery-artifact"
            and value.get("result") == "FAIL",
            "local recovery diagnostic identity drift")
    require(value.get("sourceCommitSha") == "e" * 40
            and value.get("failureStage") == "actual-recovery-artifact"
            and value.get("exitCode") == 23,
            "local recovery diagnostic source/stage/exit drift")
    require(value.get("output") == "REDACTED: local migration recovery failed; raw output withheld",
            "local recovery diagnostic raw output not redacted")
    for field in ("containsSecrets", "productionTraffic", "productionCredentials",
                  "productionEvidence", "productionReady"):
        require(value.get(field) is False, "local recovery diagnostic unsafe flag: " + field)


def diagnostic_runtime(publisher: str) -> None:
    marker = "      - name: Record privacy-safe diagnostic\n"
    require(publisher.count(marker) == 1, "local recovery diagnostic step not unique")
    section = publisher.split(marker, 1)[1]
    start, end = "          python - <<'PY'\n", "          PY\n"
    require(section.count(start) == 1 and section.count(end) >= 1,
            "local recovery inline diagnostic writer not unique")
    inline = section.split(start, 1)[1].split(end, 1)[0]
    script = "\n".join(line[10:] for line in inline.splitlines()) + "\n"
    redacted = "'REDACTED: local migration recovery failed; raw output withheld'"
    require(script.count(redacted) == 1, "local recovery diagnostic redaction marker not unique")
    require(script.count("'productionReady': False") == 1,
            "local recovery diagnostic readiness marker not unique")
    with tempfile.TemporaryDirectory(prefix="local-recovery-diagnostic-proof-") as temp:
        root = Path(temp)
        env = os.environ.copy()
        env.update({
            "SOURCE_SHA": "e" * 40,
            "EXIT_CODE": "23",
            "FAILURE_STAGE": "actual-recovery-artifact",
            "SENSITIVE_CANARY": "CANARY_DO_NOT_PERSIST_LOCAL_RECOVERY",
        })
        variants = (
            ("reviewed", script, True, None),
            ("secrets flag promotion", script.replace("'containsSecrets': False", "'containsSecrets': True", 1),
             False, "unsafe flag: containsSecrets"),
            ("schema version", script.replace("'schemaVersion': 'memory-os-validator-diagnostic.v1'",
                 "'schemaVersion': 'unreviewed.v1'", 1), False, "diagnostic schema drift"),
            ("workflow identity", script.replace("'workflow': 'local-migration-recovery-artifact'",
                 "'workflow': 'unreviewed-writer'", 1), False, "diagnostic identity drift"),
            ("result identity", script.replace("'result': 'FAIL'", "'result': 'PASS'", 1),
             False, "diagnostic identity drift"),
            ("source identity", script.replace("'sourceCommitSha': os.environ.get('SOURCE_SHA', '')",
                 "'sourceCommitSha': '0' * 40", 1), False, "diagnostic source/stage/exit drift"),
            ("stage identity", script.replace("'failureStage': os.environ.get('FAILURE_STAGE', 'unknown')",
                 "'failureStage': 'unreviewed'", 1), False, "diagnostic source/stage/exit drift"),
            ("exit code identity", script.replace("'exitCode': int(os.environ['EXIT_CODE'])",
                 "'exitCode': 0", 1), False, "diagnostic source/stage/exit drift"),
            ("output redaction", script.replace(redacted, "'unreviewed output'", 1),
             False, "raw output not redacted"),
            ("raw canary", script.replace(redacted, "os.environ['SENSITIVE_CANARY']", 1),
             False, "persisted sensitive canary"),
            ("readiness promotion", script.replace("'productionReady': False", "'productionReady': True", 1),
             False, "unsafe flag: productionReady"),
            ("traffic promotion", script.replace("'productionTraffic': False", "'productionTraffic': True", 1),
             False, "unsafe flag: productionTraffic"),
            ("credential promotion", script.replace("'productionCredentials': False", "'productionCredentials': True", 1),
             False, "unsafe flag: productionCredentials"),
            ("evidence promotion", script.replace("'productionEvidence': False", "'productionEvidence': True", 1),
             False, "unsafe flag: productionEvidence"),
            ("unreviewed field", script.replace("'productionReady': False,",
                "'productionReady': False,\n    'rawSql': 'SELECT 1',", 1),
             False, "diagnostic field inventory drift"),
            ("array root", script.replace("json.dump(value, handle, indent=2)",
                "json.dump([value], handle, indent=2)", 1),
             False, "diagnostic root must be object"),
            ("invalid JSON", script.replace("json.dump(value, handle, indent=2)",
                "handle.write('{invalid json')", 1),
             False, "diagnostic invalid JSON"),
        )
        for name, program, allowed, expected_failure in variants:
            require(allowed or program != script,
                    "local recovery diagnostic negative mutation anchor missing: " + name)
            directory = root / name.replace(" ", "-")
            directory.mkdir()
            result = subprocess.run([sys.executable, "-c", program], cwd=directory, env=env,
                                    capture_output=True, text=True, timeout=15, check=False)
            require(result.returncode == 0, "local recovery diagnostic writer failed in isolation: " + name)
            require("CANARY_DO_NOT_PERSIST_LOCAL_RECOVERY" not in result.stdout + result.stderr,
                    "local recovery diagnostic leaked canary to process output")
            path = directory / "docs/fixtures/memory-os-operability/local-migration-recovery-artifact-diagnostic.last.json"
            require(path.is_file() and not path.is_symlink(), "local recovery diagnostic output missing")
            try:
                require_diagnostic_payload(path.read_text(encoding="utf-8"))
            except SystemExit as exc:
                require(not allowed, "local recovery reviewed diagnostic rejected")
                require(expected_failure is not None and expected_failure in str(exc),
                        "local recovery diagnostic rejected for wrong reason: " + name + ": " + str(exc))
            else:
                require(allowed, "local recovery diagnostic accepted unsafe mutation: " + name)
    require(script.count("os.replace(temp_name, path)") == 1,
            "local recovery diagnostic atomic replace marker not unique")
    require(script.count("json.dump(value, handle, indent=2)") == 1,
            "local recovery diagnostic JSON writer marker not unique")
    with tempfile.TemporaryDirectory(prefix="local-recovery-diagnostic-atomic-") as temp:
        directory = Path(temp)
        target = directory / "docs/fixtures/memory-os-operability/local-migration-recovery-artifact-diagnostic.last.json"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"existing diagnostic\n")
        target.chmod(0o640)
        normal = subprocess.run([sys.executable, "-c", script], cwd=directory, env=env,
                                capture_output=True, text=True, timeout=15, check=False)
        require(normal.returncode == 0, "local recovery atomic diagnostic positive writer failed")
        require_diagnostic_payload(target.read_text(encoding="utf-8"))
        require(target.stat().st_mode & 0o7777 == 0o640,
                "local recovery atomic diagnostic changed existing mode")
        original = target.read_bytes()
        failed = script.replace("os.replace(temp_name, path)",
                                "raise OSError('synthetic local diagnostic replace failure')", 1)
        result = subprocess.run([sys.executable, "-c", failed], cwd=directory, env=env,
                                capture_output=True, text=True, timeout=15, check=False)
        require(result.returncode != 0 and "synthetic local diagnostic replace failure" in result.stderr,
                "local recovery atomic diagnostic replace failure did not execute")
        require(target.read_bytes() == original and target.stat().st_mode & 0o7777 == 0o640,
                "local recovery atomic diagnostic failure mutated existing output")
        require(not list(target.parent.glob(".local-migration-recovery-diagnostic.*.tmp")),
                "local recovery atomic diagnostic failure left temporary files")
        fsync_failed = script.replace("os.fsync(handle.fileno())",
                                      "raise OSError('synthetic local diagnostic fsync failure')", 1)
        require(fsync_failed != script, "local recovery fsync mutation anchor missing")
        fsync_result = subprocess.run([sys.executable, "-c", fsync_failed], cwd=directory, env=env,
                                      capture_output=True, text=True, timeout=15, check=False)
        require(fsync_result.returncode != 0 and "synthetic local diagnostic fsync failure" in fsync_result.stderr,
                "local recovery diagnostic fsync failure did not execute")
        require(target.read_bytes() == original and target.stat().st_mode & 0o7777 == 0o640,
                "local recovery diagnostic fsync failure mutated existing output")
        require(not list(target.parent.glob(".local-migration-recovery-diagnostic.*.tmp")),
                "local recovery diagnostic fsync failure left temporary files")
        outside = directory / "external-local-diagnostic-canary"
        outside.write_bytes(original)
        target.unlink()
        target.symlink_to(outside)
        symlink_result = subprocess.run([sys.executable, "-c", script], cwd=directory, env=env,
                                        capture_output=True, text=True, timeout=15, check=False)
        require(symlink_result.returncode != 0 and "target must not be a symlink" in symlink_result.stderr,
                "local recovery diagnostic accepted symlinked output")
        require(target.is_symlink() and outside.read_bytes() == original,
                "local recovery diagnostic symlink mutated external output")
        require(not list(target.parent.glob(".local-migration-recovery-diagnostic.*.tmp")),
                "local recovery diagnostic symlink failure left temporary files")
    print("PASS: local recovery actual diagnostic writer (1 positive, 16 negative runtime cases)")
    print("PASS: local recovery atomic diagnostic mode, replace/fsync failure and symlink guard (4 cases)")


def main() -> int:
    publisher, independent = read(PUBLISHER), read(INDEPENDENT)
    validate(publisher, independent)
    prove_trigger_reachability_negatives(publisher, independent)
    prove_yaml_authority_negatives(publisher, independent)
    prove_job_authority_negatives(publisher, independent)
    negative_proofs(publisher, independent)
    runtime_proofs()
    diagnostic_runtime(publisher)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
