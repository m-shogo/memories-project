#!/usr/bin/env python3
"""Independent exact-source and event/SHA negative checks for incident control authority."""
from __future__ import annotations
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-incident-control-authority.yml"
INDEPENDENT = ".github/workflows/incident-control-authority-source-negative.yml"
SELF = "scripts/validate-memory-os-incident-control-authority-source-negative.py"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
REVIEWED_PUBLISHER = "ba7f30a04b9c81142a896e3fcab95d2f656cdffb"
REVIEWED_INDEPENDENT = "efbb317ad48d26d5424ae784843cb9462575d564"

PUBLISHER_TRIGGER_PATHS = tuple([".github/workflows/reconcile-incident-control-authority.yml","contracts/operations/incident-control-exercise-contract.v1.json","contracts/operations/production-operability-status.json","docs/fixtures/memory-os-operability/incident-control-exercise-results.sample.v1.json","scripts/reconcile-memory-os-incident-control-authority.py","scripts/validate-memory-os-incident-control-authority-reconcile-negative.py","scripts/validate-memory-os-incident-control-exercise.py","scripts/validate-memory-os-incident-response.py","scripts/validate-memory-os-incident-tabletop.py","scripts/validate-memory-os-operability.py"])
INDEPENDENT_TRIGGER_PATHS = tuple([".github/workflows/reconcile-incident-control-authority.yml",".github/workflows/incident-control-authority-source-negative.yml","scripts/validate-memory-os-incident-control-authority-source-negative.py"])



def validate_trigger_reachability(
    publisher: str, independent: str, *,
    publisher_paths: tuple[str, ...] | None = None,
    independent_paths: tuple[str, ...] | None = None,
) -> None:
    """Pin publisher PR/push/schedule/dispatch and independent PR/push path topology."""
    pub = PUBLISHER_TRIGGER_PATHS if publisher_paths is None else publisher_paths
    ind = INDEPENDENT_TRIGGER_PATHS if independent_paths is None else independent_paths
    if (len(pub) != len(PUBLISHER_TRIGGER_PATHS) or
        len(ind) != len(INDEPENDENT_TRIGGER_PATHS) or
        len(set(pub)) != len(pub) or len(set(ind)) != len(ind)):
        raise AssertionError("incident authority shortened or duplicated trigger inventory")
    pub_paths = "".join('      - "' + path + '"\n' for path in pub)
    ind_paths = "".join('      - "' + path + '"\n' for path in ind)
    expected_pub = (
        "name: Reconcile Incident Control Authority\n\non:\n"
        "  pull_request:\n    branches:\n      - so\n    paths:\n" + pub_paths +
        "  push:\n    branches:\n      - so\n    paths:\n" + pub_paths +
        '  schedule:\n    - cron: "37 22 * * *"\n  workflow_dispatch:\n'
    )
    expected_ind = (
        "name: Incident Control Authority Source Negative\n\non:\n"
        "  pull_request:\n    branches:\n      - so\n    paths:\n" + ind_paths +
        "  push:\n    branches:\n      - so\n    paths:\n" + ind_paths
    )
    for label, value, expected in (
        ("publisher", publisher, expected_pub), ("independent", independent, expected_ind)
    ):
        if value.count("\npermissions:\n") != 1:
            raise AssertionError("incident authority " + label + " permissions boundary drift")
        if value.split("\npermissions:\n", 1)[0] != expected:
            raise AssertionError("incident authority " + label + " exact event trigger drift")
        # Exact event prefixes alone cannot reject a later YAML root key
        # (including quoted or whitespace-colon shadows) that overrides on,
        # permissions or jobs after the reviewed event boundary.
        expected_roots = (
            ["name: Reconcile Incident Control Authority", "on:", "permissions:",
             "concurrency:", "jobs:"]
            if label == "publisher" else
            ["name: Incident Control Authority Source Negative", "on:",
             "permissions:", "jobs:"]
        )
        observed_roots = [
            row for row in value.splitlines()
            if row.strip() and not row[0].isspace()
            and not row.lstrip().startswith("#")
        ]
        if observed_roots != expected_roots:
            raise AssertionError("incident authority " + label + " root YAML key shadow drift")
        # Both reviewed workflow-level permissions are read-only. A later
        # YAML quoted/spaced contents key can shadow a visible read leaf.
        permission_lines = value.split("\npermissions:\n", 1)[1].splitlines()
        permission_rows = []
        for row in permission_lines:
            if row.strip() and not row[0].isspace():
                break
            if row.strip() and not row.lstrip().startswith("#"):
                permission_rows.append(row)
        if permission_rows != ["  contents: read"]:
            raise AssertionError("incident authority " + label + " permission leaf shadow drift")


def trigger_negatives(publisher: str, independent: str) -> None:
    """Independent semantic proof: each event path, extras, truncation and event matrix."""
    cases = (
        ("publisher PR", publisher, "  pull_request:\n    branches:\n      - so\n    paths:\n",
         "  push:\n", PUBLISHER_TRIGGER_PATHS, True),
        ("publisher push", publisher, "  push:\n    branches:\n      - so\n    paths:\n",
         "  schedule:\n", PUBLISHER_TRIGGER_PATHS, True),
        ("independent PR", independent, "  pull_request:\n    branches:\n      - so\n    paths:\n",
         "  push:\n", INDEPENDENT_TRIGGER_PATHS, False),
        ("independent push", independent, "  push:\n    branches:\n      - so\n    paths:\n",
         "\npermissions:\n", INDEPENDENT_TRIGGER_PATHS, False),
    )
    omitted = added = 0
    for label, value, start, stop, paths, is_publisher in cases:
        if value.count(start) != 1 or value.count(stop) != 1:
            raise AssertionError("incident authority event negative anchor drift: " + label)
        begin = value.index(start) + len(start)
        end = value.index(stop, begin)
        block = value[begin:end]
        mutations = []
        for path in paths:
            token = '      - "' + path + '"\n'
            if block.count(token) != 1:
                raise AssertionError("incident authority trigger negative anchor missing: " + path)
            mutations.append(("omission " + path, block.replace(token, "", 1), True))
        mutations.extend((
            ("quoted extra", block + '      - "unreviewed/**"\n', False),
            ("quoted duplicate", block + '      - "' + paths[0] + '"\n', False),
            ("unquoted extra", block + "      - unreviewed/**\n", False),
            ("unquoted duplicate", block + "      - " + paths[0] + "\n", False),
        ))
        for name, changed, is_omission in mutations:
            mutated = value[:begin] + changed + value[end:]
            if mutated == value:
                raise AssertionError("incident authority unchanged negative fixture: " + name)
            try:
                if is_publisher:
                    validate_trigger_reachability(mutated, independent)
                else:
                    validate_trigger_reachability(publisher, mutated)
            except AssertionError:
                pass
            else:
                raise AssertionError("incident authority accepted " + label + " " + name)
            omitted += int(is_omission)
            added += int(not is_omission)
    for label, kwargs in (
        ("publisher", {"publisher_paths": PUBLISHER_TRIGGER_PATHS[:-1]}),
        ("independent", {"independent_paths": INDEPENDENT_TRIGGER_PATHS[:-1]}),
    ):
        try:
            validate_trigger_reachability(publisher, independent, **kwargs)
        except AssertionError:
            pass
        else:
            raise AssertionError("incident authority accepted shortened " + label + " inventory")
    for label, value, is_publisher in (
        ("publisher schedule deletion", publisher.replace(
            '  schedule:\n    - cron: "37 22 * * *"\n', "", 1), True),
        ("publisher unreviewed event", publisher.replace(
            "  workflow_dispatch:\n", "  workflow_dispatch:\n  issues:\n", 1), True),
        ("independent dispatch introduction", independent.replace(
            "\npermissions:\n", "  workflow_dispatch:\n\npermissions:\n", 1), False),
    ):
        try:
            if is_publisher:
                validate_trigger_reachability(value, independent)
            else:
                validate_trigger_reachability(publisher, value)
        except AssertionError:
            pass
        else:
            raise AssertionError("incident authority accepted event topology mutation: " + label)
    # These mutations preserve the entire reviewed event prefix. They must
    # fail the semantic root-key guard, not merely a separate Git blob pin.
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
            except AssertionError as exc:
                expected = "incident authority " + label + " root YAML key shadow drift"
                if str(exc) != expected:
                    raise AssertionError(
                        "incident authority root shadow rejected for wrong reason: "
                        + label + " " + name + ": " + str(exc)
                    ) from exc
            else:
                raise AssertionError(
                    "incident authority accepted root YAML shadow: " + label + " " + name
                )
            root_negative_count += 1
    if root_negative_count != 8:
        raise AssertionError("incident authority root shadow fixture count drift")
    permission_negative_count = 0
    for label, original, is_publisher in (
        ("publisher", publisher, True),
        ("independent", independent, False),
    ):
        anchor = "permissions:\n  contents: read\n"
        if original.count(anchor) != 1:
            raise AssertionError("incident authority permission negative anchor drift: " + label)
        for name, extra in (
            ("spaced", "  contents : write\n"),
            ("quoted", "  'contents': write\n"),
        ):
            mutated = original.replace(anchor, anchor + extra, 1)
            try:
                if is_publisher:
                    validate_trigger_reachability(mutated, independent)
                else:
                    validate_trigger_reachability(publisher, mutated)
            except AssertionError as exc:
                expected = "incident authority " + label + " permission leaf shadow drift"
                if str(exc) != expected:
                    raise AssertionError(
                        "incident authority permission shadow rejected for wrong reason: "
                        + label + " " + name + ": " + str(exc)
                    ) from exc
            else:
                raise AssertionError(
                    "incident authority accepted permission leaf shadow: " + label + " " + name
                )
            permission_negative_count += 1
    if permission_negative_count != 4:
        raise AssertionError("incident authority permission leaf fixture count drift")
    print("PASS: incident authority permission leaf shadows (4 exact-diagnostic negatives)")
    if (omitted, added) != (26, 16):
        raise AssertionError("incident authority trigger negative population drift")
    print("PASS: incident authority exact event triggers (26 omissions; 16 additions; "
          "2 shortened inventories; 3 event topology; 8 root shadow negatives)")


def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def require_reviewed_source(content: str, expected: str, label: str) -> None:
    if blob(content) != expected:
        raise AssertionError("incident authority " + label + " complete Git blob drift")

def reviewed_blob_negatives(publisher: str, independent: str) -> None:
    require_reviewed_source(publisher, REVIEWED_PUBLISHER, "publisher")
    require_reviewed_source(independent, REVIEWED_INDEPENDENT, "independent CI")
    for label, original, expected in (
        ("publisher", publisher, REVIEWED_PUBLISHER),
        ("independent CI", independent, REVIEWED_INDEPENDENT),
    ):
        try:
            require_reviewed_source(original + "\n# synthetic source drift\n", expected, label)
        except AssertionError:
            continue
        raise AssertionError("incident authority reviewed Git blob accepted synthetic source drift: " + label)
    print("PASS: incident authority publisher and independent CI complete Git blob source negatives (2 cases)")

def read(path: str) -> str:
    p = ROOT / path
    if p.is_symlink() or not p.is_file() or p.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise AssertionError("incident authority source missing/substituted: " + path)
    return p.read_text(encoding="utf-8")

def step(source: str, title: str) -> str:
    marker = "      - name: " + title + "\n"
    if source.count(marker) != 1:
        raise AssertionError("incident authority source step missing: " + title)
    start = source.index("        run: |\n", source.index(marker)) + len("        run: |\n")
    end = source.find("\n      - name:", start)
    lines = source[start:end if end >= 0 else len(source)].splitlines()
    if any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("incident authority step indentation drift")
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"

REQUIRED = (
    "  pull_request:\n    branches:\n      - so\n",
    "if: github.event_name == 'pull_request' && github.base_ref == 'so'",
    "github.ref == 'refs/heads/so'",
    "persist-credentials: false",
    "persist-credentials: true",
    'test "${GITHUB_EVENT_NAME:-}" = "pull_request"',
    'test "${GITHUB_BASE_REF:-}" = "so"',
    '[[ "$PR_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]',
    'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"',
    'test "${GITHUB_REF:-}" = "refs/heads/so"',
    '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
    'remote_sha="$(git ls-remote origin refs/heads/so',
)
def policy(source: str) -> None:
    for marker in REQUIRED:
        if marker not in source:
            raise AssertionError("incident authority policy missing: " + marker[:65])
    if source.count(CHECKOUT) != 2 or source.count(SETUP) != 2:
        raise AssertionError("incident authority immutable Actions drift")
    if source.count('test -z "$(git status --porcelain)"') != 3:
        raise AssertionError("incident authority all three clean-worktree boundaries required")
    for forbidden in ("actions/checkout@v4", "actions/setup-python@v5"):
        if forbidden in source:
            raise AssertionError("incident authority floating Actions regression")

def mutations(source: str) -> None:
    for index, marker in enumerate(REQUIRED):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE_TEST", 1)
        if changed == source:
            raise AssertionError("incident authority mutation unreachable: " + str(index))
        try:
            policy(changed)
        except AssertionError:
            continue
        raise AssertionError("incident authority mutation accepted: " + str(index))
    print(f"PASS: incident authority source mutations ({len(REQUIRED)} cases)")

def identity(source: str, title: str, writer: bool) -> None:
    shell = step(source, title)
    head = "a" * 40
    if writer:
        cases = (("push", "", "refs/heads/so", "", head, True),
                 ("schedule", "", "refs/heads/so", "", head, True),
                 ("workflow_dispatch", "", "refs/heads/so", "", head, True),
                 ("pull_request", "", "refs/heads/so", "", head, False),
                 ("push", "", "refs/heads/main", "", head, False),
                 ("push", "", "refs/heads/so", "", "b" * 40, False),
                 ("push", "", "refs/heads/so", "", "A" * 40, False),
                 ("push", "", "refs/heads/so", "", "a" * 39, False))
    else:
        cases = (("pull_request", "so", "", head, "", True),
                 ("pull_request", "main", "", head, "", False),
                 ("push", "so", "", head, "", False),
                 ("pull_request", "so", "", "b" * 40, "", False),
                 ("pull_request", "so", "", "A" * 40, "", False),
                 ("pull_request", "so", "", "a" * 39, "", False))
    with tempfile.TemporaryDirectory(prefix="incident-authority-source-") as temp:
        root = Path(temp)
        stub = root / "git"
        stub.write_text("#!/bin/sh\n"
                        "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"HEAD\" ]; then printf '" + head + "\\n'; exit 0; fi\n"
                        "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then exit 0; fi\n"
                        "exit 1\n", encoding="utf-8")
        stub.chmod(0o755)
        for event, base, ref, pr_sha, sha, allowed in cases:
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_EVENT_NAME=event, GITHUB_BASE_REF=base, GITHUB_REF=ref,
                       PR_HEAD_SHA=pr_sha, GITHUB_SHA=sha)
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != allowed:
                raise AssertionError("incident authority event/base/ref/SHA shell drift: " + str((title, event, ref, result.returncode)))
    print(f"PASS: incident authority {title} event/ref/SHA shell runtime ({len(cases)} cases)")

def main() -> None:
    publisher = read(PUBLISHER)
    independent = read(INDEPENDENT)
    for marker in (PUBLISHER, INDEPENDENT, SELF, CHECKOUT, SETUP,
                   "persist-credentials: false", "contents: read",
                   'test "$(git rev-parse HEAD)" = "$expected"',
                   'test -z "$(git status --porcelain)"'):
        if marker not in independent:
            raise AssertionError("incident authority independent CI reachability drift: " + marker)
    reviewed_blob_negatives(publisher, independent)
    validate_trigger_reachability(publisher, independent)
    trigger_negatives(publisher, independent)
    policy(publisher)
    mutations(publisher)
    identity(publisher, "Confirm exact clean PR authority source", False)
    identity(publisher, "Confirm exact clean authority source", True)
    print("PASS: incident control authority exact-source read-only proof; production evidence generated: false")

if __name__ == "__main__":
    main()
