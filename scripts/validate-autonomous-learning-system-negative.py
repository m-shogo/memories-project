#!/usr/bin/env python3
"""Negative suite proving the autonomous learning guard fails closed."""

from __future__ import annotations

import argparse
import hashlib
import stat
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = Path("contracts/operations/autonomous-learning-system.json")
LEARNING = Path("docs/operations/AUTONOMOUS-OPS-LEARNING.md")
VALIDATOR = Path("scripts/validate-autonomous-learning-system.py")
NEGATIVE_VALIDATOR = Path("scripts/validate-autonomous-learning-system-negative.py")
CI_ENTRYPOINT = Path("scripts/validate-memory-os-entry-docs.py")


def seed(source_root: Path, root: Path) -> None:
    # The positive validator verifies both executable guard bindings and their
    # CI reachability. Seed the complete canonical authority set so the
    # positive control proves a real pass before any mutation is applied.
    for rel in (CONTRACT, LEARNING, VALIDATOR, NEGATIVE_VALIDATOR, CI_ENTRYPOINT):
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_root / rel, target)


def fixture_state(root: Path) -> tuple[tuple[str, ...], ...]:
    """Fingerprint canonical fixture bytes, modes, and every path component."""
    observed: dict[str, tuple[str, ...]] = {}
    for relative in (CONTRACT, LEARNING, VALIDATOR, NEGATIVE_VALIDATOR, CI_ENTRYPOINT):
        path = root
        for part in relative.parts:
            path = path / part
            key = path.relative_to(root).as_posix()
            if key in observed:
                continue
            if path.is_symlink():
                observed[key] = ("symlink", str(path.readlink()))
            elif path.is_file():
                observed[key] = (
                    "file", hashlib.sha256(path.read_bytes()).hexdigest(),
                    str(stat.S_IMODE(path.stat().st_mode)),
                )
            elif path.is_dir():
                observed[key] = ("directory", str(stat.S_IMODE(path.stat().st_mode)))
            else:
                observed[key] = ("missing",)
    return tuple(sorted((key, *value) for key, value in observed.items()))


def run(source_root: Path, root: Path) -> subprocess.CompletedProcess[str]:
    # Execute the immutable canonical harness from the checked-out source tree
    # against the isolated fixture. This lets a negative case remove the
    # fixture's bound validator and still prove that the canonical guard rejects
    # the missing executable authority, rather than failing in Python startup.
    try:
        return subprocess.run(
            [sys.executable, str(source_root / VALIDATOR), "--repo-root", str(root)],
            text=True,
            capture_output=True,
            check=False,
            timeout=90,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("autonomous learning canonical negative harness timed out after 90s") from exc


def require_canonical_rejection(name: str, result: subprocess.CompletedProcess[str]) -> None:
    if result.returncode != 1:
        raise RuntimeError(f"negative case did not return canonical exit 1: {name}: {result.returncode}")
    if not result.stderr.startswith("AUTONOMOUS LEARNING VALIDATION FAILED: "):
        raise RuntimeError(f"negative case did not fail through canonical guard: {name}: {result.stderr}")
    if "Traceback (most recent call last)" in result.stderr:
        raise RuntimeError(f"negative case leaked implementation traceback: {name}")


def require_reviewed_learning_negative_stdout(source: str) -> None:
    """Reject extra stdout before the exact downstream PASS classifier runs."""
    import ast
    tree = ast.parse(source)
    mains = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name == "main"]
    stdout_calls = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "print"):
            continue
        stderr = any(kw.arg == "file" and isinstance(kw.value, ast.Attribute)
                     and isinstance(kw.value.value, ast.Name)
                     and kw.value.value.id == "sys" and kw.value.attr == "stderr"
                     for kw in node.keywords)
        if not stderr:
            stdout_calls.append(node)
    if (len(mains) != 1 or len(stdout_calls) != 1 or
            not any(node is stdout_calls[0] for node in ast.walk(mains[0]))):
        raise RuntimeError("unreviewed learning negative stdout")
    call = stdout_calls[0]
    if len(call.args) != 1 or not isinstance(call.args[0], ast.JoinedStr):
        raise RuntimeError("unreviewed learning negative stdout")
    static = "".join(part.value for part in call.args[0].values
                     if isinstance(part, ast.Constant) and isinstance(part.value, str))
    if static != "Autonomous learning negative validation PASS ( fail-closed cases)":
        raise RuntimeError("unreviewed learning negative stdout")


def prove_learning_negative_stdout_negatives() -> None:
    base = 'def main():\n    print(f"Autonomous learning negative validation PASS ({count} fail-closed cases)")\n'
    require_reviewed_learning_negative_stdout(base)
    require_reviewed_learning_negative_stdout(base + 'print("debug", file=sys.stderr)\n')
    for label, candidate in (
        ("extra stdout", base + 'print("extra")\n'),
        ("wrong marker", base.replace("Autonomous learning", "Autonomous learn")),
        ("disguised stdout", base + 'print("extra", file=sys.stdout)\n'),
        ("missing marker", "def main():\n    pass\n"),
        ("helper stdout", base + 'def helper():\n    print("extra")\n'),
    ):
        try:
            require_reviewed_learning_negative_stdout(candidate)
        except RuntimeError as exc:
            if str(exc) != "unreviewed learning negative stdout":
                raise
        else:
            raise RuntimeError("learning negative stdout fixture accepted: " + label)


def prove_failure_classifier() -> None:
    # A validator startup/implementation failure must not count as a
    # successful negative admission rejection.
    invalid = (
        subprocess.CompletedProcess([], 0, "", "AUTONOMOUS LEARNING VALIDATION FAILED: fake"),
        subprocess.CompletedProcess([], 2, "", "AUTONOMOUS LEARNING VALIDATION FAILED WITH UNEXPECTED ERROR: injected"),
        subprocess.CompletedProcess([], 1, "", "AUTONOMOUS LEARNING VALIDATION FAILED WITH UNEXPECTED ERROR: injected"),
        subprocess.CompletedProcess([], 1, "", "Traceback (most recent call last): injected"),
    )
    for index, result in enumerate(invalid):
        try:
            require_canonical_rejection(f"synthetic classifier {index}", result)
        except RuntimeError:
            pass
        else:
            raise RuntimeError(f"negative failure classifier accepted unrelated result: {index}")
    require_canonical_rejection(
        "synthetic canonical rejection",
        subprocess.CompletedProcess([], 1, "", "AUTONOMOUS LEARNING VALIDATION FAILED: injected canonical guard\n"),
    )


def expected_diagnostic(name: str) -> str:
    """Bind each negative to the invariant it intended to violate."""
    fixed = {
        "weaken mandatory rule": "mandatory learning rule must remain true: unchangedBlockerIsNotRetried",
        "disable required CI reachability": "mandatory learning rule must remain true: ciReachabilityRequired",
        "weaken NO_GO default": "learning must not weaken the NO_GO default",
        "allow non-real OPS-P0-007 evidence": "OPS-P0-007 real-evidence boundary must remain true",
        "merge human promotion review into automation": "human promotion review must remain separate",
        "break executable guard binding": "executable learning guard binding changed",
        "break negative guard binding": "negative learning guard binding changed",
        "break CI entrypoint binding": "learning CI entrypoint binding changed",
        "break learning authority binding": "learning authority path changed",
        "duplicate required failure field": "requiredFailureFields contains duplicates",
        "duplicate required success field": "requiredSuccessFields contains duplicates",
        "remove learning authority": "learning authority path missing or escapes root: docs/operations/AUTONOMOUS-OPS-LEARNING.md",
        "remove executable guard": "learning authority path missing or escapes root: scripts/validate-autonomous-learning-system.py",
        "remove negative guard": "learning authority path missing or escapes root: scripts/validate-autonomous-learning-system-negative.py",
        "remove CI entrypoint": "learning authority path missing or escapes root: scripts/validate-memory-os-entry-docs.py",
        "disconnect positive guard from CI entrypoint": "learning CI entrypoint does not invoke bound guard: scripts/validate-autonomous-learning-system.py",
        "disconnect negative guard from CI entrypoint": "learning CI entrypoint does not invoke bound guard: scripts/validate-autonomous-learning-system-negative.py",
        "remove CI guard execution call": "learning CI entrypoint lost executable guard invocation: validate_learning_guards(failures)",
        "drop CI repo-root guard interface": 'learning CI entrypoint lost executable guard invocation: [sys.executable, str(path), "--repo-root", str(REPO_ROOT)]',
        "drop CI guard timeout authority": "learning CI entrypoint lost executable guard invocation: LEARNING_GUARD_TIMEOUT_SECONDS = 120",
        "drop CI guard timeout binding": "learning CI entrypoint lost executable guard invocation: timeout=LEARNING_GUARD_TIMEOUT_SECONDS",
        "remove source-negative CI guard call": "source-negative CI guard must be called directly from main",
        "quote source-negative CI guard call": "source-negative CI guard must be called directly from main",
        "shadow source-negative CI guard": "source-negative CI guard binding changed",
        "remove source-negative CI negative proof": "source-negative CI guard lost executable negative proof",
        "unreachable source-negative CI guard call": "source-negative CI guard call is unreachable",
        "drop CI guard timeout handling": "learning CI entrypoint lost executable guard invocation: except subprocess.TimeoutExpired:",
        "drop anti-regression lesson": "learning authority lost invariant: Repeating a known failed approach without changed preconditions is a regression",
        "invalid contract JSON": "invalid JSON:",
        "duplicate contract JSON key": "duplicate JSON key:",
        "nested duplicate contract JSON key": "duplicate JSON key:",
        "nonfinite contract JSON": "nonfinite JSON number:",
        "overflow float contract JSON": "nonfinite JSON number:",
        "huge integer contract JSON": "oversized JSON integer:",
        "invalid UTF8 contract JSON": "invalid UTF-8:",
        "oversized contract JSON": "oversized JSON authority:",
        "non-object contract root": "root must be an object:",
        "downgrade schema version": "unsupported schemaVersion",
        "reorder closed-loop execution": "closed-loop execution order changed",
        "comment-only learning guard call": "learning CI entrypoint main must directly invoke bound learning guards",
        "quoted learning guard call": "learning CI entrypoint main must directly invoke bound learning guards",
        "dead-branch learning guard call": "learning CI entrypoint main must directly invoke bound learning guards",
        "unreachable learning guard after return": "learning CI entrypoint guard call follows unconditional return or raise",
        "unreachable learning guard after raise": "learning CI entrypoint guard call follows unconditional return or raise",
        "async-only learning guard": "learning CI entrypoint must define one synchronous learning guard",
        "async learning guard shadow": "learning CI entrypoint learning guard binding is shadowed by async definition",
        "assigned learning guard shadow": "learning CI entrypoint learning guard binding is shadowed by assignment",
        "destructured learning guard shadow": "learning CI entrypoint learning guard binding is shadowed by assignment",
        "imported learning guard shadow": "learning CI entrypoint learning guard binding is shadowed by import",
        "async main shadow": "learning CI entrypoint main binding is shadowed by async definition",
        "assigned main shadow": "learning CI entrypoint main binding is shadowed by assignment",
        "destructured main shadow": "learning CI entrypoint main binding is shadowed by assignment",
        "imported main shadow": "learning CI entrypoint main binding is shadowed by import",
        "loop main shadow": "learning CI entrypoint main binding is shadowed by module control flow",
        "loop learning guard shadow": "learning CI entrypoint learning guard binding is shadowed by module control flow",
        "nested imported learning guard shadow": "learning CI entrypoint learning guard binding is shadowed by module control flow",
        "dead module main guard": "learning CI entrypoint must execute main from its live module guard",
        "comment-only module main invocation": "learning CI entrypoint must execute main from its live module guard",
    }
    if name in fixed:
        return fixed[name]
    if name.startswith("module early "):
        return "learning CI entrypoint module terminates before live main guard"
    if name.startswith("early learning guard "):
        return "learning CI entrypoint guard call follows unconditional return or raise"
    if name.startswith("dynamic main "):
        return "learning CI entrypoint main binding is shadowed by module control flow"
    if name.startswith("dynamic learning guard "):
        return "learning CI entrypoint learning guard binding is shadowed by module control flow"
    if name.startswith("disable mandatory "):
        return "mandatory learning rule must remain true: " + name.removeprefix("disable mandatory ")
    if name.startswith("drop required failure "):
        return "requiredFailureFields changed:"
    if name.startswith("drop required success "):
        return "requiredSuccessFields changed:"
    if name.startswith("symlinked ") and name.endswith(" parent directory"):
        return "learning authority path substituted through parent:"
    if name.startswith("symlinked ") and name.endswith(" authority"):
        return "symlinked learning authority forbidden:"
    raise RuntimeError(f"negative case lacks an expected canonical diagnostic: {name}")


def require_expected_rejection(name: str, result: subprocess.CompletedProcess[str]) -> None:
    require_canonical_rejection(name, result)
    expected = "AUTONOMOUS LEARNING VALIDATION FAILED: " + expected_diagnostic(name)
    # A case's diagnostic must be the single canonical failure line, not
    # an expected substring hidden after an unrelated error or traceback.
    observed = result.stderr.removesuffix("\n")
    # Variable canonical diagnostics end with a colon and must include a detail.
    # Every other diagnostic is an exact authority string: a matching prefix
    # with an unrelated same-line suffix is not proof of the intended guard.
    variable_detail = (name in {"invalid contract JSON", "non-object contract root",
                                "duplicate contract JSON key", "nested duplicate contract JSON key",
                                "nonfinite contract JSON", "overflow float contract JSON",
                                "huge integer contract JSON", "invalid UTF8 contract JSON",
                                "oversized contract JSON"}
                       or name.startswith(("drop required failure ", "drop required success ",
                                           "symlinked ")))
    matched = (observed.startswith(expected + " ") and len(observed) > len(expected) + 1
               if variable_detail else observed == expected)
    if "\n" in observed or "\r" in observed or not matched:
        raise RuntimeError(
            f"negative case rejected for the wrong reason: {name}: "
            f"expected {expected!r}; observed {result.stderr!r}"
        )


def require_failure(source_root: Path, name: str, mutate) -> None:
    with tempfile.TemporaryDirectory(prefix="learning-negative-") as tmp:
        root = Path(tmp)
        seed(source_root, root)
        before = fixture_state(root)
        mutate(root)
        if fixture_state(root) == before:
            raise RuntimeError(f"negative fixture did not mutate canonical authority: {name}")
        result = run(source_root, root)
        require_expected_rejection(name, result)


def edit_contract(root: Path, edit) -> None:
    path = root / CONTRACT
    data = json.loads(path.read_text(encoding="utf-8"))
    edit(data)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def drop_from_entrypoint(root: Path, phrase: str) -> None:
    path = root / CI_ENTRYPOINT
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace(f'    "{phrase}",\n', ""), encoding="utf-8")


def replace_in_entrypoint(root: Path, old: str, new: str) -> None:
    path = root / CI_ENTRYPOINT
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"negative fixture missing expected CI fragment: {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def symlink_authority(root: Path, relative: Path) -> None:
    # The alias and target stay inside this disposable fixture; canonical
    # checked-out authorities are never modified by the negative.
    path = root / relative
    target = path.with_name(path.name + ".fixture-target")
    path.rename(target)
    path.symlink_to(target.name)


def symlink_parent_directory(root: Path, relative: Path) -> None:
    # The substituted parent still points only inside the disposable fixture.
    # A canonical leaf is not a canonical path if any parent is an alias.
    directory = root / relative
    target = directory.with_name(directory.name + ".fixture-target")
    directory.rename(target)
    directory.symlink_to(target.name, target_is_directory=True)


def upload_route_local_go_imports(source: str, include_external: bool = False,
                                  include_aliases: bool = False) -> set[str]:
    """Parse reviewed Go import forms conservatively; reject unknown syntax."""
    import re
    module = "github.com/m-shogo/memories-project/services/import-api/"
    # Go accepts "package p; import ..." and "/* note */ import ...".
    # A line-anchored parser would silently omit those legal dependencies.
    if re.search(r"(?:;|\*/)[ \t]*import(?:[ \t]+|[ \t]*\()", source):
        raise RuntimeError("unreviewed Go import placement")
    blocks = list(re.finditer(r"(?m)^[ \t]*import[ \t]*\(([\s\S]*?)^[ \t]*\)", source))
    paths = []
    aliases = []
    for block in blocks:
        for line in block.group(1).splitlines():
            if not line.strip() or line.lstrip().startswith("//"):
                continue
            match = re.fullmatch(r'\s*(?:([A-Za-z_.]\w*)\s+)?"([^"]+)"\s*(?://.*)?', line)
            if match is None:
                raise RuntimeError("unreviewed Go import block entry")
            if match.group(2) == "C":
                raise RuntimeError("unreviewed Go CGo import")
            paths.append(match.group(2))
            if match.group(1):
                aliases.append(match.group(1) + "\t" + match.group(2))
    for block in reversed(blocks):
        source = source[:block.start()] + source[block.end():]
    for line in source.splitlines():
        if re.match(r"^[ \t]*import\b", line):
            match = re.fullmatch(r'[ \t]*import[ \t]+(?:([A-Za-z_.]\w*)[ \t]+)?"([^"]+)"[ \t]*(?://.*)?', line)
            if match is None:
                raise RuntimeError("unreviewed single-line Go import")
            if match.group(2) == "C":
                raise RuntimeError("unreviewed Go CGo import")
            paths.append(match.group(2))
            if match.group(1):
                aliases.append(match.group(1) + "\t" + match.group(2))
    if include_aliases:
        return set(aliases)
    return set(paths) if include_external else {
        path[len(module):] for path in paths if path.startswith(module)
    }


def prove_upload_route_go_import_parser() -> None:
    module = "github.com/m-shogo/memories-project/services/import-api/"
    sample = 'package test\nimport (\n  "fmt"\n  alias "' + module + 'internal/metrics"\n)\n'
    if upload_route_local_go_imports(sample) != {"internal/metrics"}:
        raise RuntimeError("Go import block positive fixture failed")
    if upload_route_local_go_imports(sample, include_external=True) != {
            "fmt", module + "internal/metrics"}:
        raise RuntimeError("Go complete import path positive fixture failed")
    if upload_route_local_go_imports(sample, include_aliases=True) != {
            "alias\t" + module + "internal/metrics"}:
        raise RuntimeError("Go import alias positive fixture failed")
    for alias in ("_", "."):
        if upload_route_local_go_imports('import ' + alias + ' "fmt"\n', include_aliases=True) != {alias + "\tfmt"}:
            raise RuntimeError("Go special import alias positive fixture failed")
    plain, aliased = 'import "fmt"\n', 'import other "fmt"\n'
    if upload_route_local_go_imports(plain, include_external=True) != upload_route_local_go_imports(aliased, include_external=True):
        raise RuntimeError("Go alias mutation changed path-only positive control")
    alias_digest = hashlib.sha256(b"a.go\talias\tfmt\n").hexdigest()
    require_reviewed_upload_route_input_set({"a.go\talias\tfmt"}, 1, alias_digest)
    for candidate in ({"a.go\tother\tfmt"}, {"b.go\talias\tfmt"}, set()):
        try:
            require_reviewed_upload_route_input_set(candidate, 1, alias_digest)
        except RuntimeError as exc:
            if str(exc) != "upload route reviewed input identity changed; review required":
                raise
        else:
            raise RuntimeError("Go import alias identity negative accepted")
    sample_entries = {
        "services/import-api/internal/httpserver/a.go\tfmt",
        "services/import-api/internal/httpserver/a.go\t" + module + "internal/metrics",
    }
    sample_digest = "5af039209052f569a5e26c8aa8ea0caa6fccf5dfd0886ae59cb8afc5168cd55f"
    require_reviewed_upload_route_input_set(sample_entries, 2, sample_digest)
    for label, candidate in (
        ("external import swap", {sorted(sample_entries)[0], "a.go\tother/external"}),
        ("import file move", {entry.replace("/a.go\t", "/b.go\t") for entry in sample_entries}),
    ):
        try:
            require_reviewed_upload_route_input_set(candidate, 2, sample_digest)
        except RuntimeError as exc:
            if str(exc) != "upload route reviewed input identity changed; review required":
                raise
        else:
            raise RuntimeError("Go import identity negative accepted: " + label)
    if upload_route_local_go_imports('import "' + module + 'internal/reqid"\n') != {"internal/reqid"}:
        raise RuntimeError("Go single-line import positive fixture failed")
    for label, candidate in (
        ("semicolon-prefixed import", 'package test; import "' + module + 'internal/reqid"\n'),
        ("comment-prefixed import", 'package test\n/* note */ import "' + module + 'internal/metrics"\n'),
    ):
        try:
            upload_route_local_go_imports(candidate)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Go import placement":
                raise
        else:
            raise RuntimeError("Go import placement negative accepted: " + label)
    for label, candidate in (
        ("tab-separated CGo", 'import\t"C"\n'),
        ("grouped CGo", 'import (\n  "C"\n)\n'),
    ):
        try:
            upload_route_local_go_imports(candidate)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Go CGo import":
                raise
        else:
            raise RuntimeError("Go CGo import negative accepted: " + label)
    try:
        upload_route_local_go_imports('import (\n  not_a_go_import\n)\n')
    except RuntimeError:
        pass
    else:
        raise RuntimeError("Go import parser accepted invalid import fixture")


def require_reviewed_upload_route_go_package(relative: str, source: str) -> None:
    """An unchanged Go import path does not prove the source package identity."""
    import re
    parts = Path(relative).parts
    if len(parts) != 5 or parts[:3] != ("services", "import-api", "internal"):
        raise RuntimeError("unreviewed Go package identity")
    declarations = re.findall(r"(?m)^package[ \t]+([A-Za-z_]\w*)[ \t]*$", source)
    if declarations != [parts[3]]:
        raise RuntimeError("unreviewed Go package identity")


def prove_upload_route_go_package_negatives() -> None:
    path = "services/import-api/internal/httpserver/server.go"
    require_reviewed_upload_route_go_package(path, "package httpserver\n")
    require_reviewed_upload_route_go_package(path, "//go:build linux\n\npackage httpserver\n")
    for label, relative, source in (
        ("renamed package", path, "package changed\n"),
        ("external test package", path, "package httpserver_test\n"),
        ("missing package", path, "import \"fmt\"\n"),
        ("duplicate declaration", path, "package httpserver\npackage httpserver\n"),
        ("relocated package", "services/import-api/internal/metrics/server.go", "package httpserver\n"),
        ("nested path", "services/import-api/internal/httpserver/subdir/server.go", "package httpserver\n"),
    ):
        try:
            require_reviewed_upload_route_go_package(relative, source)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Go package identity":
                raise
        else:
            raise RuntimeError("Go package identity negative accepted: " + label)


def require_reviewed_upload_route_go_build_constraints(relative: str, source: str) -> None:
    """Pin compile-time Go build constraints independently of path/import identity."""
    stems = ("reconcile", "records", "seal", "storage", "verifier", "writer")
    reviewed = {
        "services/import-api/internal/httpserver/apple_live_test.go": "linux",
        "services/import-api/internal/httpserver/deletion_worker_sigkill_recovery_linux_test.go": "linux",
    }
    for stem in stems:
        reviewed[f"services/import-api/internal/previewspool/{stem}_linux.go"] = "linux"
        reviewed[f"services/import-api/internal/previewspool/{stem}_unsupported.go"] = "!linux"
    expected = reviewed.get(relative)
    directives = [line.strip() for line in source.splitlines()
                  if line.lstrip().startswith(("//go:build", "// +build"))]
    if expected is None:
        if directives:
            raise RuntimeError("unreviewed Go build constraint")
    elif (directives != [f"//go:build {expected}"] or
          not source.startswith(f"//go:build {expected}\n\n")):
        raise RuntimeError("unreviewed Go build constraint")


def prove_upload_route_go_build_constraint_negatives() -> None:
    tagged = "services/import-api/internal/previewspool/seal_linux.go"
    untagged = "services/import-api/internal/metrics/labels.go"
    baseline = "//go:build linux\n\npackage previewspool\n"
    require_reviewed_upload_route_go_build_constraints(tagged, baseline)
    require_reviewed_upload_route_go_build_constraints(
        "services/import-api/internal/httpserver/apple_live_test.go",
        "//go:build linux\n\npackage httpserver\n"
    )
    require_reviewed_upload_route_go_build_constraints(untagged, "package metrics\n")
    for label, path, candidate in (
        ("changed expression", tagged, baseline.replace("linux", "windows")),
        ("missing directive", tagged, "package previewspool\n"),
        ("late directive", tagged, "package previewspool\n//go:build linux\n"),
        ("legacy shadow", tagged, "// +build windows\n" + baseline),
        ("new tag on unreviewed file", untagged, baseline),
        ("duplicate directive", tagged, baseline.replace("package", "//go:build linux\npackage")),
        ("whitespace drift", tagged, baseline.replace("//go:build linux", "//go:build  linux")),
    ):
        try:
            require_reviewed_upload_route_go_build_constraints(path, candidate)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Go build constraint":
                raise
        else:
            raise RuntimeError("Go build constraint negative accepted: " + label)


def upload_route_event_paths(source: str, event: str) -> tuple[str, ...]:
    """Require one unshadowed event path list; never infer closure from YAML aliases."""
    import re
    lines = source.splitlines()
    if sum(line in ("on:", '"on":', "'on':") for line in lines) != 1:
        raise RuntimeError("shadowed Upload Route on authority")
    if any(re.match(r"^\s*(?:paths-ignore|branches-ignore):", line) for line in lines):
        raise RuntimeError("unreviewed Upload Route negative event filter")
    event_rows = (f"  {event}:", f'  "{event}":', f"  '{event}':")
    starts = [i for i, line in enumerate(lines) if line in event_rows]
    if len(starts) != 1:
        raise RuntimeError("ambiguous Upload Route event mapping")
    start = starts[0]
    end = next((i for i in range(start + 1, len(lines))
                if re.match(r"^  [a-z_]+:", lines[i]) or
                (lines[i] and not lines[i].startswith((" ", "#")))), len(lines))
    block = lines[start + 1:end]
    positions = [i for i, line in enumerate(block) if line == "    paths:"]
    if len(positions) != 1:
        raise RuntimeError("ambiguous Upload Route event path authority")
    branch_rows = block[:positions[0]]
    if event == "push" and branch_rows != ["    branches:", "      - so"]:
        raise RuntimeError("Upload Route publisher must target only so")
    if event == "pull_request" and branch_rows:
        raise RuntimeError("Upload Route PR branch filter unreviewed")
    patterns = []
    for line in block[positions[0] + 1:]:
        if not line.strip():
            continue
        # Every nonblank row after paths belongs to this reviewed path list.
        # Never silently stop at a shadowing paths/branches/types mapping.
        match = re.fullmatch(r'      - "([^"]+)"', line)
        if match is None or match.group(1).startswith("!"):
            raise RuntimeError("unreviewed Upload Route path pattern")
        patterns.append(match.group(1))
    if not patterns or len(patterns) != len(set(patterns)):
        raise RuntimeError("duplicate/empty Upload Route event paths")
    return tuple(patterns)


def prove_upload_route_event_parser_negatives() -> None:
    base = 'on:\n  push:\n    branches:\n      - so\n    paths:\n      - "a/**"\n'
    if upload_route_event_paths(base, "push") != ("a/**",):
        raise RuntimeError("Upload Route event parser positive fixture failed")
    pr = 'on:\n  pull_request:\n    paths:\n      - "a/**"\n'
    if upload_route_event_paths(pr, "pull_request") != ("a/**",):
        raise RuntimeError("Upload Route PR event parser positive fixture failed")
    mutations = (
        base + "on:\n",
        base.replace("    paths:\n", "    paths-ignore:\n"),
        base.replace('      - "a/**"\n', '      - "a/**"\n      - "a/**"\n'),
        base.replace("  push:\n", "  pull_request:\n"),
        base.replace("    branches:\n", "    branches-ignore:\n"),
        base.replace("      - so\n", "      - main\n"),
        base.replace("    branches:\n      - so\n", ""),
        base.replace("      - so\n", "      - so\n      - main\n"),
        base + "    types:\n      - closed\n",
        base + '    paths:\n      - "b/**"\n',
        base + "    branches:\n      - main\n",
        base + '    "paths":\n      - "b/**"\n',
    )
    try:
        upload_route_event_paths(pr.replace("    paths:\n",
                                           "    branches:\n      - main\n    paths:\n"), "pull_request")
    except RuntimeError:
        pass
    else:
        raise RuntimeError("Upload Route PR branch negative accepted")
    for label, injected in (
        ("PR types", "    types:\n      - closed\n"),
        ("PR duplicate paths", '    paths:\n      - "b/**"\n'),
    ):
        try:
            upload_route_event_paths(pr + injected, "pull_request")
        except RuntimeError:
            pass
        else:
            raise RuntimeError("Upload Route PR trailing filter accepted: " + label)
    for index, source in enumerate(mutations):
        try:
            upload_route_event_paths(source, "push")
        except RuntimeError:
            pass
        else:
            raise RuntimeError(f"Upload Route event parser negative accepted: {index}")


def require_reviewed_upload_route_event_set(source: str, event: str) -> None:
    """Reject added or hidden Upload Route workflow event sources."""
    import re
    if event not in ("push", "pull_request"):
        raise RuntimeError("unreviewed Upload Route event set")
    blocks = re.findall(r"(?ms)^on:\n(.*?)(?=^[A-Za-z_][\w-]*:|\Z)", source)
    if len(blocks) != 1:
        raise RuntimeError("unreviewed Upload Route event set")
    events = [line for line in blocks[0].splitlines()
              if line.startswith("  ") and not line.startswith(("   ", "  #"))]
    expected = ["  push:", "  workflow_dispatch:"] if event == "push" else ["  pull_request:"]
    if events != expected:
        raise RuntimeError("unreviewed Upload Route event set")


def prove_upload_route_event_set_negatives() -> None:
    base = ('on:\n  push:\n    paths:\n      - "a/**"\n  workflow_dispatch:\n\n'
            'permissions:\n  contents: write\n')
    pr = ('on:\n  pull_request:\n    paths:\n      - "a/**"\n\n'
          'permissions:\n  contents: read\n')
    require_reviewed_upload_route_event_set(base, "push")
    require_reviewed_upload_route_event_set(pr, "pull_request")
    for label, source, event in (
        ("schedule", base.replace("  workflow_dispatch:", "  schedule:\n    - cron: '0 0 * * *'\n  workflow_dispatch:"), "push"),
        ("workflow call", base.replace("  workflow_dispatch:", "  workflow_call:\n  workflow_dispatch:"), "push"),
        ("PR target", pr.replace("  pull_request:", "  pull_request_target:\n  pull_request:"), "pull_request"),
        ("extra push", pr.replace("  pull_request:", "  push:\n  pull_request:"), "pull_request"),
        ("PR dispatch", pr.replace("\npermissions:", "  workflow_dispatch:\n\npermissions:"), "pull_request"),
        ("missing dispatch", base.replace("  workflow_dispatch:\n", ""), "push"),
        ("quoted push", base.replace("  push:", "  'push':"), "push"),
        ("duplicate push", base.replace("  push:", "  push:\n  push:"), "push"),
        ("scalar on", base.replace("on:\n", "on: push\n"), "push"),
        ("inline dispatch", base.replace("  workflow_dispatch:", "  workflow_dispatch: {}"), "push"),
    ):
        try:
            require_reviewed_upload_route_event_set(source, event)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Upload Route event set":
                raise
        else:
            raise RuntimeError("Upload Route event set negative accepted: " + label)


def require_reviewed_upload_route_toolchain_environment(source: str) -> None:
    """Reject unreviewed workflow-level Python/Go dependency resolver overrides."""
    import re
    names = (
        "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONINSPECT",
        "PYTHONSAFEPATH", "GOWORK", "GOFLAGS", "GOPATH", "GOMODCACHE",
        "GOTOOLCHAIN", "CGO_ENABLED", "GOENV", "GITHUB_ENV",
        "PYTHONUSERBASE", "PYTHONWARNINGS", "PYTHONNOUSERSITE",
        "PIP_CONFIG_FILE", "PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL",
        "PIP_NO_INDEX", "PIP_TRUSTED_HOST", "GOPROXY", "GOSUMDB",
        "GOPRIVATE", "GONOPROXY", "GONOSUMDB", "GO111MODULE",
        "GOROOT", "GOCACHE", "BASH_ENV", "ENV", "SHELLOPTS",
        "BASHOPTS", "LD_PRELOAD", "LD_LIBRARY_PATH", "GITHUB_PATH", "PATH",
    )
    if re.search(r"(?<![A-Za-z0-9_])(?:" + "|".join(names) +
                 r")(?![A-Za-z0-9_])", source):
        raise RuntimeError("unreviewed Upload Route toolchain environment")


def prove_upload_route_toolchain_environment_negatives() -> None:
    positive = "env:\n  MEMORY_OS_TEST_DATABASE_URL: postgres://local\n"
    require_reviewed_upload_route_toolchain_environment(positive)
    for name in (
        "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONINSPECT",
        "PYTHONSAFEPATH", "GOWORK", "GOFLAGS", "GOPATH", "GOMODCACHE",
        "GOTOOLCHAIN", "CGO_ENABLED", "GOENV", "GITHUB_ENV",
        "PYTHONUSERBASE", "PYTHONWARNINGS", "PYTHONNOUSERSITE",
        "PIP_CONFIG_FILE", "PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL",
        "PIP_NO_INDEX", "PIP_TRUSTED_HOST", "GOPROXY", "GOSUMDB",
        "GOPRIVATE", "GONOPROXY", "GONOSUMDB", "GO111MODULE",
        "GOROOT", "GOCACHE", "BASH_ENV", "ENV", "SHELLOPTS",
        "BASHOPTS", "LD_PRELOAD", "LD_LIBRARY_PATH", "GITHUB_PATH", "PATH",
    ):
        try:
            require_reviewed_upload_route_toolchain_environment(
                positive + "  " + name + ": unreviewed\n"
            )
        except RuntimeError as exc:
            if str(exc) != "unreviewed Upload Route toolchain environment":
                raise
        else:
            raise RuntimeError("Upload Route toolchain env negative accepted: " + name)


def require_reviewed_upload_route_actions(source: str) -> None:
    """Pin reviewed workflow action identities without claiming tags immutable."""
    import re
    observed = re.findall(r"(?m)^\s*(?:-\s*)?uses:\s*(\S+)\s*$", source)
    # YAML also accepts spaced, quoted and flow-mapping keys. Reject any
    # additional uses key that the canonical line parser did not recognize.
    mentions = re.findall(r"""(?m)(?<![A-Za-z0-9_])(?:uses|["']uses["'])\s*:""", source)
    expected = ["actions/checkout@v4", "actions/setup-go@v5",
                "actions/setup-python@v5"]
    if len(mentions) != len(observed) or observed != expected:
        raise RuntimeError("unreviewed Upload Route action identity")


def prove_upload_route_action_negatives() -> None:
    base = ("steps:\n  - uses: actions/checkout@v4\n"
            "  - uses: actions/setup-go@v5\n"
            "  - uses: actions/setup-python@v5\n")
    require_reviewed_upload_route_actions(base)
    for label, candidate in (
        ("new action", base + "  - uses: other/action@v1\n"),
        ("checkout ref change", base.replace("checkout@v4", "checkout@v5")),
        ("mutable main ref", base.replace("setup-go@v5", "setup-go@main")),
        ("missing action", base.replace("  - uses: actions/setup-go@v5\n", "")),
        ("duplicate action", base + "  - uses: actions/checkout@v4\n"),
        ("reordered actions", base.replace(
            "  - uses: actions/setup-go@v5\n  - uses: actions/setup-python@v5\n",
            "  - uses: actions/setup-python@v5\n  - uses: actions/setup-go@v5\n")),
        ("spaced uses shadow", base + "  - uses : other/action@v1\n"),
        ("quoted uses shadow", base + '  - "uses": other/action@v1\n'),
        ("single-quoted uses shadow", base + "  - 'uses': other/action@v1\n"),
        ("flow mapping uses shadow", base + "  - {uses: other/action@v1}\n"),
    ):
        try:
            require_reviewed_upload_route_actions(candidate)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Upload Route action identity":
                raise
        else:
            raise RuntimeError("Upload Route action negative accepted: " + label)


REVIEWED_UPLOAD_ROUTE_RUNTIME_COMMANDS = (
    "python -m pip install --disable-pip-version-check --requirement requirements-security-validation.txt",
    "python -m py_compile scripts/reconcile-memory-os-upload-route-authority.py scripts/validate-memory-os-upload-route-reconcile-rollback.py scripts/validate-memory-os-metrics.py scripts/validate-memory-os-rate-limit.py scripts/validate-memory-os-observability.py scripts/validate-memory-os-operability.py",
    "python scripts/validate-memory-os-upload-route-reconcile-rollback.py",
    "python scripts/reconcile-memory-os-upload-route-authority.py",
    "go test ./internal/httpserver -run '^(TestRouteAuthorityMatchesRegisteredUploadSurface|TestRoutePrefilterPreservesKnownAndRejectsUnknownShapes|TestUploadLifecycleOverHTTP|TestAccountDeletionFencesAndErasesOverHTTP)$' -count=1 -timeout=10m",
    "python scripts/validate-memory-os-metrics.py",
    "python scripts/validate-memory-os-rate-limit.py",
    "python scripts/validate-memory-os-observability.py",
    "python scripts/validate-memory-os-operability.py",
    "python scripts/reconcile-memory-os-upload-route-authority.py",
)


def upload_route_runtime_commands(source: str) -> tuple[str, ...]:
    import re
    lines = source.splitlines()
    observed = []
    for index, line in enumerate(lines):
        match = re.match(r"^\s*(?:run:\s*)?((?:python|go)\s+.*)$", line)
        if match is None:
            continue
        parts, cursor = [match.group(1).strip()], index
        while parts[-1].endswith("\\"):
            parts[-1] = parts[-1][:-1].rstrip()
            cursor += 1
            if cursor >= len(lines):
                raise RuntimeError("unreviewed Upload Route runtime command")
            parts.append(lines[cursor].strip())
        observed.append(" ".join(parts))
    return tuple(observed)


def require_reviewed_upload_route_runtime_commands(source: str) -> None:
    if upload_route_runtime_commands(source) != REVIEWED_UPLOAD_ROUTE_RUNTIME_COMMANDS:
        raise RuntimeError("unreviewed Upload Route runtime command")


def prove_upload_route_runtime_command_negatives() -> None:
    base = "\n".join("run: " + cmd for cmd in REVIEWED_UPLOAD_ROUTE_RUNTIME_COMMANDS) + "\n"
    require_reviewed_upload_route_runtime_commands(base)
    continuation = "python -m py_compile " + chr(92) + "\n  scripts/a.py " + chr(92) + "\n  scripts/b.py\n"
    if upload_route_runtime_commands(continuation) != (
            "python -m py_compile scripts/a.py scripts/b.py",):
        raise RuntimeError("Upload Route command continuation positive failed")
    for label, candidate in (
        ("new command", base + "run: python scripts/new.py\n"),
        ("Go target", base.replace("go test ./internal/httpserver", "go test ./other")),
        ("Python validator", base.replace("python scripts/validate-memory-os-metrics.py",
                                          "python scripts/validate-memory-os-new.py")),
        ("pip arguments", base.replace("python -m pip install", "python -m pip uninstall")),
        ("removed validator", base.replace(
            "run: python scripts/validate-memory-os-observability.py\n", "")),
        ("Go test filter", base.replace("TestUploadLifecycleOverHTTP", "TestOther")),
    ):
        try:
            require_reviewed_upload_route_runtime_commands(candidate)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Upload Route runtime command":
                raise
        else:
            raise RuntimeError("Upload Route command negative accepted: " + label)


def reject_unreviewed_upload_route_shell_dispatch(source: str) -> None:
    """Do not silently omit prefixed/chained Python or Go shell invocations."""
    import re
    patterns = (
        r"(?m)^\s*(?:run:\s*)?(?:env|command|sudo|exec|nohup|time|timeout|nice|stdbuf|setsid|ionice|chrt|xargs|parallel|eval)\b[^\r\n]*(?:python(?:3(?:\.\d+)?)?|go)\b",
        r"(?m)\b(?:bash|sh|dash|zsh)\s+(?:-[A-Za-z]*c[A-Za-z]*|--command)\b",
        r"(?m)(?:&&|;|\|)[ \t]*(?:python(?:3(?:\.\d+)?)?|go)\b",
        r"(?m)^\s*(?:run:\s*)?python3(?:\.\d+)?\b",
        r"\$\(\s*(?:python|go)\b",
        r"(?m)\bfind\b[^\r\n]*\s-exec\s+(?:python(?:3(?:\.\d+)?)?|go)\b",
    )
    if any(re.search(pattern, source) for pattern in patterns):
        raise RuntimeError("unreviewed Upload Route shell dispatch")


def prove_upload_route_shell_dispatch_negatives() -> None:
    reject_unreviewed_upload_route_shell_dispatch(
        "run: python scripts/validate-memory-os-metrics.py\n"
        "run: go test ./internal/httpserver\n"
    )
    # YAML's run: | block scalar is not a shell pipe to the next command.
    reject_unreviewed_upload_route_shell_dispatch(
        "run: |\n  python scripts/validate-memory-os-metrics.py\n"
        "run: |\n  go test ./internal/httpserver\n"
    )
    for label, source in (
        ("env Python", "run: env python scripts/new.py"),
        ("command Python", "run: command python scripts/new.py"),
        ("sudo Go", "run: sudo go test ./x"),
        ("bash shell", "run: bash -c 'python x.py'"),
        ("sh shell", "run: sh -c 'go test ./x'"),
        ("chained Python", "echo ok && python x.py"),
        ("semicolon Go", "echo ok; go test ./x"),
        ("python3", "run: python3 x.py"),
        ("python3 minor", "run: python3.12 x.py"),
        ("piped Python", "echo ok | python x.py"),
        ("substitution", "echo $(python x.py)"),
        ("env with option", "run: env -S python scripts/new.py"),
        ("command with option", "run: command -p python scripts/new.py"),
        ("sudo with option", "run: sudo -n go test ./x"),
        ("exec Python", "run: exec python scripts/new.py"),
        ("nohup Go", "run: nohup go test ./x"),
        ("timeout Python", "run: timeout 10s python scripts/new.py"),
        ("nice Go", "run: nice -n 5 go test ./x"),
        ("bash login command", "run: bash -lc 'python scripts/new.py'"),
        ("sh error command", "run: sh -ec 'go test ./x'"),
        ("dash command", "run: dash -c 'python scripts/new.py'"),
        ("xargs Python", "run: xargs -n1 python scripts/new.py"),
        ("eval Python", "run: eval 'python scripts/new.py'"),
        ("find exec Go", "run: find . -exec go test ./x ;"),
    ):
        try:
            reject_unreviewed_upload_route_shell_dispatch(source)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Upload Route shell dispatch":
                raise
        else:
            raise RuntimeError("Upload Route shell dispatch negative accepted: " + label)


def require_reviewed_upload_route_run_keys(source: str, expected_count: int) -> None:
    """Reject shadowed YAML run keys and unexpected non-Python/Go steps."""
    import re
    if (re.search(r"""(?m)^[ \t]*(?:['"]run['"]|run[ \t]+):""", source)
            or re.search(r"""(?m)^[ \t]*-\s*(?:\{[^\r\n]*\b(?:run|['"]run['"])\s*:|(?:run|['"]run['"])\s*:)""", source)):
        raise RuntimeError("unreviewed Upload Route run key")
    canonical = re.findall(r"(?m)^        run:", source)
    mentions = re.findall(r"(?m)^[ \t]*run:", source)
    if len(canonical) != expected_count or len(mentions) != len(canonical):
        raise RuntimeError("unreviewed Upload Route run key")
    for step in re.split(r"(?m)^      - (?=(?:name|uses|id):)", source)[1:]:
        if len(re.findall(r"(?m)^        run:", step)) > 1:
            raise RuntimeError("unreviewed Upload Route run key")


def prove_upload_route_run_key_negatives() -> None:
    base = ("steps:\n      - name: first\n        run: python scripts/x.py\n"
            "      - name: second\n        run: go test ./x\n")
    require_reviewed_upload_route_run_keys(base, 2)
    require_reviewed_upload_route_run_keys(
        base.replace("run: python scripts/x.py", "run: |\n          python scripts/x.py"), 2
    )
    for label, candidate in (
        ("duplicate run", base.replace("        run: go", "        run: echo hi\n        run: go")),
        ("quoted shadow", base.replace("        run: go", "        'run': echo hi\n        run: go")),
        ("spaced shadow", base.replace("        run: go", "        run : echo hi\n        run: go")),
        ("flow shadow", base.replace("        run: go", "        - {run: echo hi}\n        run: go")),
        ("indented shadow", base.replace("        run: go", "          run: echo hi\n        run: go")),
        ("new run", base + "      - name: third\n        run: echo hi\n"),
        ("removed run", base.replace("        run: go test ./x\n", "")),
        ("inline run step", base + "      - run: echo hi\n"),
    ):
        try:
            require_reviewed_upload_route_run_keys(candidate, 2)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Upload Route run key":
                raise
        else:
            raise RuntimeError("Upload Route run-key negative accepted: " + label)


def require_reviewed_upload_route_working_directories(source: str) -> None:
    """Bind Go test and formatting working directories to their named steps."""
    import re
    observed = re.findall(r"(?m)^        working-directory: ([^\r\n]+)$", source)
    mentions = re.findall(
        r"""(?m)(?<![A-Za-z0-9_-])(?:working-directory|['"]working-directory['"])\s*:""",
        source,
    )
    if observed != ["services/import-api"] * 2 or len(mentions) != len(observed):
        raise RuntimeError("unreviewed Upload Route working directory")
    names = []
    for section in re.split(r"(?m)^      - (?=name:)", source)[1:]:
        name = section.splitlines()[0].split(":", 1)[1].strip()
        if re.search(r"(?m)^        working-directory:", section):
            names.append(name)
    if names != ["Format and verify source diff", "Run focused route and live upload regressions"]:
        raise RuntimeError("unreviewed Upload Route working directory")


def prove_upload_route_working_directory_negatives() -> None:
    base = ("steps:\n      - name: Format and verify source diff\n"
            "        working-directory: services/import-api\n"
            "      - name: Run focused route and live upload regressions\n"
            "        working-directory: services/import-api\n")
    require_reviewed_upload_route_working_directories(base)
    for label, candidate in (
        ("changed root", base.replace("working-directory: services/import-api",
                                      "working-directory: .", 1)),
        ("missing", base.replace("        working-directory: services/import-api\n", "", 1)),
        ("duplicate", base.replace("        working-directory: services/import-api\n",
                                   "        working-directory: services/import-api\n"
                                   "        working-directory: .\n", 1)),
        ("spaced shadow", base.replace("working-directory: services/import-api",
                                       "working-directory : services/import-api", 1)),
        ("quoted shadow", base.replace("working-directory: services/import-api",
                                       '"working-directory": services/import-api', 1)),
        ("wrong step", base.replace("Format and verify source diff", "Another step")),
        ("global default", base + "defaults:\n  run:\n    working-directory: .\n"),
    ):
        try:
            require_reviewed_upload_route_working_directories(candidate)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Upload Route working directory":
                raise
        else:
            raise RuntimeError("Upload Route working-directory negative accepted: " + label)


def require_reviewed_upload_route_action_inputs(source: str, event: str) -> None:
    """Bind checkout source SHA and setup action inputs, not just uses refs."""
    import re
    if event not in ("push", "pull_request"):
        raise RuntimeError("unreviewed Upload Route action inputs")
    ref = chr(36) + ("{{ github.sha }}" if event == "push"
                     else "{{ github.event.pull_request.head.sha }}")
    expected = (
        ("actions/checkout@v4", (f"ref: {ref}", "fetch-depth: 0")),
        ("actions/setup-go@v5", ('go-version: "1.23.x"',
                                 "cache-dependency-path: services/import-api/go.sum")),
        ("actions/setup-python@v5", ('python-version: "3.12"', "cache: pip",
                                     "cache-dependency-path: requirements-security-validation.txt")),
    )
    observed = []
    for section in re.split(r"(?m)^      - (?=name:)", source)[1:]:
        action = re.search(r"(?m)^        uses: (\S+)$", section)
        if action:
            observed.append((action.group(1), tuple(
                re.findall(r"(?m)^          ([^\r\n]+)$", section)
            )))
    mentions = re.findall(r"""(?m)^[ \t]*(?:with|['"]with['"])\s*:""", source)
    if (len(mentions) != 3 or tuple(observed) != expected
            or re.search(r"(?m)^[ \t]*-\s*\{[^\r\n]*\bwith\s*:", source)):
        raise RuntimeError("unreviewed Upload Route action inputs")


def prove_upload_route_action_input_negatives() -> None:
    base = ("steps:\n      - name: Checkout\n        uses: actions/checkout@v4\n"
            "        with:\n          ref: " + chr(36) + "{{ github.sha }}\n"
            "          fetch-depth: 0\n"
            "      - name: Set up Go\n        uses: actions/setup-go@v5\n"
            '        with:\n          go-version: "1.23.x"\n'
            "          cache-dependency-path: services/import-api/go.sum\n"
            "      - name: Set up Python\n        uses: actions/setup-python@v5\n"
            '        with:\n          python-version: "3.12"\n'
            "          cache: pip\n"
            "          cache-dependency-path: requirements-security-validation.txt\n")
    require_reviewed_upload_route_action_inputs(base, "push")
    require_reviewed_upload_route_action_inputs(
        base.replace("github.sha", "github.event.pull_request.head.sha"), "pull_request"
    )
    for label, candidate in (
        ("checkout ref", base.replace("github.sha", "github.ref")),
        ("Go version", base.replace('go-version: "1.23.x"', 'go-version: "1.24.x"')),
        ("Python cache removed", base.replace("          cache: pip\n", "")),
        ("checkout depth", base.replace("fetch-depth: 0", "fetch-depth: 1")),
        ("duplicate with", base.replace("        with:\n", "        with:\n        with:\n", 1)),
        ("quoted with", base.replace("        with:\n", "        'with':\n        with:\n", 1)),
        ("extra cache", base.replace("          cache: pip\n",
                                      "          cache: pip\n          cache: none\n")),
        ("spaced with", base.replace("        with:\n", "        with :\n        with:\n", 1)),
    ):
        try:
            require_reviewed_upload_route_action_inputs(candidate, "push")
        except RuntimeError as exc:
            if str(exc) != "unreviewed Upload Route action inputs":
                raise
        else:
            raise RuntimeError("Upload Route action-input negative accepted: " + label)


REVIEWED_UPLOAD_ROUTE_MINIO_RUN = "\n".join((
    f"          docker run -d --name memory-os-upload-route-minio {chr(92)}",
    f"            -p 9000:9000 {chr(92)}",
    f"            -e MINIO_ROOT_USER=minioadmin {chr(92)}",
    f"            -e MINIO_ROOT_PASSWORD=minioadmin {chr(92)}",
    "            quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z server /data",
))


def require_reviewed_upload_route_container_images(source: str) -> None:
    """Pin reviewed container source references and local MinIO launch syntax."""
    import re
    images = re.findall(
        r"""(?m)^[ \t]*(?:image|['"]image['"])\s*:\s*([^\r\n]+)$""", source
    )
    if (images != ["postgres:16-alpine"]
            or source.count("      postgres:\n        image: postgres:16-alpine") != 1
            or source.count(REVIEWED_UPLOAD_ROUTE_MINIO_RUN) != 1
            or len(re.findall(r"\bdocker\s+run\b", source)) != 1):
        raise RuntimeError("unreviewed Upload Route container image or launch")


def prove_upload_route_container_image_negatives() -> None:
    base = ("services:\n      postgres:\n        image: postgres:16-alpine\n"
            "steps:\n      - name: Start local MinIO\n        run: |\n"
            + REVIEWED_UPLOAD_ROUTE_MINIO_RUN + "\n")
    require_reviewed_upload_route_container_images(base)
    for label, candidate in (
        ("Postgres image", base.replace("postgres:16-alpine", "postgres:17-alpine")),
        ("MinIO tag", base.replace("RELEASE.2025-09-07T16-13-09Z", "latest")),
        ("MinIO port", base.replace("-p 9000:9000", "-p 9001:9000")),
        ("MinIO password", base.replace("MINIO_ROOT_PASSWORD=minioadmin",
                                         "MINIO_ROOT_PASSWORD=changed")),
        ("MinIO extra flag", base.replace("docker run -d", "docker run --privileged -d")),
        ("extra docker run", base + "          docker run alpine\n"),
        ("duplicate image", base.replace("        image: postgres:16-alpine",
                                          "        image: postgres:16-alpine\n"
                                          "        image: alpine")),
        ("quoted image shadow", base.replace("        image: postgres:16-alpine",
                                             "        'image': postgres:16-alpine\n"
                                             "        image: postgres:16-alpine")),
    ):
        try:
            require_reviewed_upload_route_container_images(candidate)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Upload Route container image or launch":
                raise
        else:
            raise RuntimeError("Upload Route container-image negative accepted: " + label)


def require_reviewed_upload_route_permissions(source: str, event: str) -> None:
    """Reject privilege expansion and shadowed Publisher/PR permissions."""
    import re
    if event not in ("push", "pull_request"):
        raise RuntimeError("unreviewed Upload Route permissions")
    expected = "write" if event == "push" else "read"
    block = re.search(r"(?ms)^permissions:\n(.*?)(?=^[A-Za-z_][\w-]*:|\Z)", source)
    mentions = re.findall(r"""(?m)^[ \t]*(?:permissions|['"]permissions['"])\s*:""", source)
    if (len(mentions) != 1 or block is None
            or block.group(1).strip() != f"contents: {expected}"):
        raise RuntimeError("unreviewed Upload Route permissions")


def prove_upload_route_permission_negatives() -> None:
    base = "permissions:\n  contents: write\n\nconcurrency:\n  group: example\n"
    require_reviewed_upload_route_permissions(base, "push")
    require_reviewed_upload_route_permissions(
        base.replace("contents: write", "contents: read"), "pull_request"
    )
    for label, candidate, event in (
        ("Publisher read", base.replace("contents: write", "contents: read"), "push"),
        ("PR write", base, "pull_request"),
        ("id token escalation", base.replace("contents: write",
                                              "contents: write\n  id-token: write"), "push"),
        ("duplicate contents", base.replace("permissions:\n",
                                             "permissions:\n  contents: write\n", 1), "push"),
        ("quoted shadow", base.replace("permissions:\n",
                                       "'permissions':\npermissions:\n", 1), "push"),
        ("spaced shadow", base.replace("permissions:\n",
                                       "permissions :\npermissions:\n", 1), "push"),
        ("write-all scalar", base.replace("permissions:\n",
                                          "permissions: write-all\n", 1), "push"),
        ("job override", base + "jobs:\n  a:\n    permissions:\n      contents: write\n", "push"),
        ("spaced contents", base.replace("contents: write", "contents : write"), "push"),
    ):
        try:
            require_reviewed_upload_route_permissions(candidate, event)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Upload Route permissions":
                raise
        else:
            raise RuntimeError("Upload Route permissions negative accepted: " + label)


def require_reviewed_upload_route_job_execution(source: str, event: str) -> None:
    """Bind Upload Route runner, skip, shell, and concurrency authority."""
    import re
    if event not in ("push", "pull_request"):
        raise RuntimeError("unreviewed Upload Route job execution controls")
    job = "reconcile" if event == "push" else "validate"
    group = ("reconcile-upload-route-authority-so" if event == "push"
             else "validate-upload-route-authority-pr-${{ github.event.pull_request.number }}")
    forbidden = ("shell", "defaults", "continue-on-error", "strategy",
                 "container", "needs", "environment")
    if any(re.search(r"(?m)^[ \t]*(?:" + key + r"|['\"]" + key + r"['\"])\s*:", source)
           for key in forbidden):
        raise RuntimeError("unreviewed Upload Route job execution controls")
    for key, value in (("runs-on", "ubuntu-latest"), ("timeout-minutes", "20")):
        if (re.findall(r"(?m)^    " + key + r": ([^\r\n]+)$", source) != [value]
                or len(re.findall(r"(?m)^[ \t]*(?:" + key + r"|['\"]" + key + r"['\"])\s*:", source)) != 1):
            raise RuntimeError("unreviewed Upload Route job execution controls")
    blocks = re.findall(r"(?ms)^concurrency:\n(.*?)(?=^[A-Za-z_][\w-]*:|\Z)", source)
    if (blocks != [f"  group: {group}\n  cancel-in-progress: true\n\n"]
            or len(re.findall(r"""(?m)^[ \t]*(?:concurrency|['"]concurrency['"])\s*:""", source)) != 1):
        raise RuntimeError("unreviewed Upload Route job execution controls")
    sections = source.split("\njobs:\n")
    if (len(sections) != 2 or
            re.findall(r"(?m)^  ([A-Za-z_][\w-]*):[ \t]*$", sections[1]) != [job]):
        raise RuntimeError("unreviewed Upload Route job execution controls")
    conditions = re.findall(r"(?ms)^    if: >-\n(.*?)(?=^    [A-Za-z_][\w-]*:|\Z)", source)
    expected_if = ("      github.event_name != 'push' ||\n"
                   "      !contains(github.event.head_commit.message, 'fix(http): reconcile upload route authority')\n")
    if (conditions != ([expected_if] if event == "push" else [])
            or len(re.findall(r"""(?m)^[ \t]*(?:if|['"]if['"])\s*:""", source)) != (1 if event == "push" else 0)):
        raise RuntimeError("unreviewed Upload Route job execution controls")


def prove_upload_route_job_execution_negatives() -> None:
    base = ("concurrency:\n  group: reconcile-upload-route-authority-so\n  cancel-in-progress: true\n\n"
            "jobs:\n  reconcile:\n    if: >-\n      github.event_name != 'push' ||\n"
            "      !contains(github.event.head_commit.message, 'fix(http): reconcile upload route authority')\n"
            "    runs-on: ubuntu-latest\n    timeout-minutes: 20\n")
    pr = (base.replace("reconcile-upload-route-authority-so",
                       "validate-upload-route-authority-pr-${{ github.event.pull_request.number }}")
          .replace("  reconcile:\n", "  validate:\n")
          .replace("    if: >-\n      github.event_name != 'push' ||\n"
                   "      !contains(github.event.head_commit.message, 'fix(http): reconcile upload route authority')\n", ""))
    require_reviewed_upload_route_job_execution(base, "push")
    require_reviewed_upload_route_job_execution(pr, "pull_request")
    for label, candidate, event in (
        ("runner", base.replace("ubuntu-latest", "windows-latest"), "push"),
        ("timeout", base.replace("timeout-minutes: 20", "timeout-minutes: 1"), "push"),
        ("shell", base + "    shell: python\n", "push"),
        ("defaults", base + "defaults:\n  run:\n    shell: bash\n", "push"),
        ("continue on error", base + "    continue-on-error: true\n", "push"),
        ("strategy", base + "    strategy:\n      matrix: {}\n", "push"),
        ("container", base + "    container: ubuntu:latest\n", "push"),
        ("needs", base + "    needs: other\n", "push"),
        ("environment", base + "    environment: production\n", "push"),
        ("skip expression", base.replace("github.event_name != 'push' ||",
                                         "false && github.event_name != 'push' ||"), "push"),
        ("PR skip", pr + "    if: false\n", "pull_request"),
        ("concurrency group", base.replace("reconcile-upload-route-authority-so", "different"), "push"),
        ("cancel flag", base.replace("cancel-in-progress: true", "cancel-in-progress: false"), "push"),
        ("extra concurrency", base + "concurrency:\n  group: wrong\n", "push"),
        ("extra job", base + "  other:\n    runs-on: ubuntu-latest\n", "push"),
        ("renamed job", base.replace("  reconcile:\n", "  changed:\n"), "push"),
        ("quoted if", base + "    'if': false\n", "push"),
        ("quoted shell", base + "    'shell': bash\n", "push"),
    ):
        try:
            require_reviewed_upload_route_job_execution(candidate, event)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Upload Route job execution controls":
                raise
        else:
            raise RuntimeError("Upload Route job execution negative accepted: " + label)


COMMON_UPLOAD_ROUTE_STEPS = (
    "Set up Go", "Set up Python", "Install validation dependencies",
    "Start local MinIO", "Confirm exact clean source",
    "Validate reconcile rollback boundary",
    "Reconcile registered routes and authority contracts",
    "Format and verify source diff", "Run focused route and live upload regressions",
    "Validate metrics, rate-limit and observability contracts",
    "Confirm reconcile is idempotent",
)


def reviewed_upload_route_steps(event: str) -> tuple[str, ...]:
    return (("Checkout exact authority source", "Capture validation source", *COMMON_UPLOAD_ROUTE_STEPS,
             "Commit reconciled route authority") if event == "push" else
            ("Checkout exact PR head", *COMMON_UPLOAD_ROUTE_STEPS,
             "Require deterministic whole-worktree authority"))


def require_reviewed_upload_route_step_order(source: str, event: str) -> None:
    """Bind step order and source-output id to the reviewed workflow."""
    import re
    if event not in ("push", "pull_request"):
        raise RuntimeError("unreviewed Upload Route step order")
    names = re.findall(r"(?m)^      - name: ([^\r\n]+)$", source)
    mentions = re.findall(r"""(?m)^[ \t]*-\s*(?:name|['"]name['"])\s*:""", source)
    step_keys = re.findall(r"""(?m)^[ \t]*(?:steps|['"]steps['"])\s*:""", source)
    if (tuple(names) != reviewed_upload_route_steps(event) or len(mentions) != len(names)
            or len(step_keys) != 1 or source.count("    steps:\n") != 1
            or re.search(r"""(?m)^[ \t]*-\s*\{[^\r\n]*(?:name|['"]name['"])\s*:""", source)):
        raise RuntimeError("unreviewed Upload Route step order")
    id_steps = []
    for section in re.split(r"(?m)^      - name: ", source)[1:]:
        if re.search(r"(?m)^        id:", section):
            id_steps.append(section.splitlines()[0])
    ids = re.findall(r"(?m)^        id: ([^\r\n]+)$", source)
    id_mentions = re.findall(r"""(?m)^[ \t]*(?:id|['"]id['"])\s*:""", source)
    if (ids != (["source"] if event == "push" else [])
            or id_steps != (["Capture validation source"] if event == "push" else [])
            or len(id_mentions) != len(ids)):
        raise RuntimeError("unreviewed Upload Route step order")


def prove_upload_route_step_order_negatives() -> None:
    def fixture(event: str) -> str:
        return "    steps:\n" + "".join(
            "      - name: " + name + "\n" +
            ("        id: source\n" if name == "Capture validation source" else "")
            for name in reviewed_upload_route_steps(event))
    base, pr = fixture("push"), fixture("pull_request")
    require_reviewed_upload_route_step_order(base, "push")
    require_reviewed_upload_route_step_order(pr, "pull_request")
    for label, source, event in (
        ("rename", base.replace("Start local MinIO", "Start MinIO"), "push"),
        ("swap", base.replace("      - name: Set up Go\n      - name: Set up Python\n",
                               "      - name: Set up Python\n      - name: Set up Go\n"), "push"),
        ("remove", base.replace("      - name: Start local MinIO\n", ""), "push"),
        ("add", base + "      - name: Extra\n", "push"),
        ("duplicate", base.replace("      - name: Start local MinIO\n",
                                    "      - name: Start local MinIO\n      - name: Start local MinIO\n"), "push"),
        ("quoted name", base.replace("      - name: Start local MinIO", "      - 'name': Start local MinIO"), "push"),
        ("flow name", base + "      - {name: Extra}\n", "push"),
        ("source id", base.replace("id: source", "id: other"), "push"),
        ("moved id", base.replace("        id: source\n", "").replace(
            "      - name: Set up Go\n", "      - name: Set up Go\n        id: source\n"), "push"),
        ("PR id", pr + "        id: source\n", "pull_request"),
        ("duplicate steps", base + "    steps:\n", "push"),
        ("quoted steps", base.replace("    steps:\n", "    'steps':\n"), "push"),
    ):
        try:
            require_reviewed_upload_route_step_order(source, event)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Upload Route step order":
                raise
        else:
            raise RuntimeError("Upload Route step-order negative accepted: " + label)


REVIEWED_UPLOAD_ROUTE_ENV_DIGESTS = {
    "push": "b8be75551ac269930a24024724251ad10456d50c876bebb4349ebf62a1b2db4c",
    "pull_request": "a7185d987d322b52e5e3de7bb1597ef4eb9495ed89a7d1e65b382bb368e1cf29",
}


def require_reviewed_upload_route_test_environment(source: str, event: str) -> None:
    """Pin localhost-only test service and job/step environment identity."""
    import re
    if event not in REVIEWED_UPLOAD_ROUTE_ENV_DIGESTS:
        raise RuntimeError("unreviewed Upload Route test environment")
    service = re.findall(r"(?ms)^    services:\n(.*?)(?=^    [a-z-]+:|\Z)", source)
    job_env = re.findall(r"(?ms)^    env:\n(.*?)(?=^    [a-z-]+:|\Z)", source)
    step_env = re.findall(r"(?m)^        env:\n((?:          [^\r\n]+\n)+)", source)
    if (len(service) != 1 or len(job_env) != 1 or len(step_env) != 2
            or len(re.findall(r"""(?m)^[ \t]*(?:services|['"]services['"])\s*:""", source)) != 1
            or len(re.findall(r"""(?m)^[ \t]*(?:env|['"]env['"])\s*:""", source)) != 3):
        raise RuntimeError("unreviewed Upload Route test environment")
    digest = hashlib.sha256("\0".join([service[0], job_env[0], *step_env]).encode()).hexdigest()
    if digest != REVIEWED_UPLOAD_ROUTE_ENV_DIGESTS[event]:
        raise RuntimeError("unreviewed Upload Route test environment")


def prove_upload_route_test_environment_negatives(source_root: Path) -> None:
    for workflow, event in (
        ("reconcile-upload-route-authority.yml", "push"),
        ("reconcile-upload-route-authority-pr.yml", "pull_request"),
    ):
        source = (source_root / ".github/workflows" / workflow).read_text(encoding="utf-8")
        require_reviewed_upload_route_test_environment(source, event)
        cases = [
            ("database endpoint", "127.0.0.1:5432", "db.example.invalid:5432"),
            ("S3 endpoint", "MEMORY_OS_TEST_S3_ENDPOINT: http://127.0.0.1:9000",
             "MEMORY_OS_TEST_S3_ENDPOINT: https://s3.example.invalid"),
            ("S3 secret", "MEMORY_OS_TEST_S3_SECRET_KEY: minioadmin", "MEMORY_OS_TEST_S3_SECRET_KEY: other"),
            ("Postgres port", "5432:5432", "5433:5432"),
            ("Postgres DB", "POSTGRES_DB: memory_os_security", "POSTGRES_DB: other"),
            ("health retries", "--health-retries 30", "--health-retries 1"),
            ("extra job env", "      MEMORY_OS_TEST_S3_SECRET_KEY: minioadmin\n",
             "      MEMORY_OS_TEST_S3_SECRET_KEY: minioadmin\n      EXTRA: unsafe\n"),
            ("quoted job env", "    env:\n      MEMORY_OS_TEST_DATABASE_URL",
             "    'env':\n      MEMORY_OS_TEST_DATABASE_URL"),
            ("quoted services", "    services:\n      postgres:",
             "    'services':\n      postgres:"),
            ("extra service", "    services:\n      postgres:",
             "    services:\n      extra:\n      postgres:"),
            ("Postgres image", "postgres:16-alpine", "postgres:17-alpine"),
            ("service env", "        env:\n          POSTGRES_PASSWORD",
             "        'env':\n          POSTGRES_PASSWORD"),
        ]
        if event == "push":
            cases.append(("source SHA binding", "          SOURCE_SHA: ${{ steps.source.outputs.sha }}",
                          "          SOURCE_SHA: unsafe"))
        else:
            cases.append(("PR head SHA binding", "          PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}",
                          "          PR_HEAD_SHA: unsafe"))
        for label, before, after in cases:
            if source.count(before) != 1:
                raise RuntimeError("Upload Route test environment fixture anchor changed: " + label)
            try:
                require_reviewed_upload_route_test_environment(source.replace(before, after, 1), event)
            except RuntimeError as exc:
                if str(exc) != "unreviewed Upload Route test environment":
                    raise
            else:
                raise RuntimeError("Upload Route test environment negative accepted: " + label)


REVIEWED_UPLOAD_ROUTE_MINIO_STEP_SHA256 = "5f1334748c3ac7088d02a976fd4dfa781a08a6ad6a6e34a035dd98da339472fb"
REVIEWED_UPLOAD_ROUTE_SHARED_CRITICAL_STEPS = {
    "Install validation dependencies": "f6e4c89f14f774cd64c6c6b626f457a54448e9fe5cdcd4c194c82e4d7a44c15a",
    "Run focused route and live upload regressions": "e473f70c921f0c6490d3a4d445957c70fd06f5d3d3a00bca1a59b8b95cc89208",
    "Format and verify source diff": "0df62db20de9cdd9fc079ec3212a2afdb85fba17939bacf10e5017775427d52c",
    "Confirm reconcile is idempotent": "4c1fe3a742bdc8a99cb34fb2e882b10cc2d139927671118a7bd0bd463ce32e75",
    "Validate reconcile rollback boundary": "4b627dcae963062ebf4f7bb1abae852e4646696df58696502df1b0653e89a59f",
    "Reconcile registered routes and authority contracts": "940537c1b9fcde7243db49446c7a2817c98b355edf4e6eb4de3fb7ae09c26a91",
    "Validate metrics, rate-limit and observability contracts": "1f69d1450219c350f12fdf449d112303a1683fbfc92c988a8a4398143cf92afc",
}


REVIEWED_UPLOAD_ROUTE_CRITICAL_STEPS = {
    "push": {
        **REVIEWED_UPLOAD_ROUTE_SHARED_CRITICAL_STEPS,
        "Capture validation source": "a9d41a746b8e008141a77b43ce5bfa19552849910e7ecaa543576ecbb864c374",
        "Start local MinIO": REVIEWED_UPLOAD_ROUTE_MINIO_STEP_SHA256,
        "Confirm exact clean source": "ef005ca7e8a13416a66b7101565a9cd738cca2b2b3a40d1340ec4c4da09bbed1",
        "Commit reconciled route authority": "eff8b093bc5e626f2005493cd37cf71c36969ecfdcd45e4e5a753dac3a30658e",
    },
    "pull_request": {
        **REVIEWED_UPLOAD_ROUTE_SHARED_CRITICAL_STEPS,
        "Start local MinIO": REVIEWED_UPLOAD_ROUTE_MINIO_STEP_SHA256,
        "Confirm exact clean source": "67b258528a940f3905da352cd42172d2e45be14c789799c047d9cf77d455921e",
        "Require deterministic whole-worktree authority": "631e27fa9ac80db93efa83ac15d75621752365311c172233edd1fc7e3d835e85",
    },
}


def require_reviewed_upload_route_critical_coverage(
    event: str, step_names: list[str], covered_names: list[str],
) -> None:
    """Prove all and only executable steps have reviewed shell-body fingerprints."""
    if event not in ("push", "pull_request"):
        raise RuntimeError("unreviewed Upload Route critical step coverage")
    actions = {"Set up Go", "Set up Python",
               "Checkout exact authority source" if event == "push" else "Checkout exact PR head"}
    if (len(step_names) != len(set(step_names))
            or len(covered_names) != len(set(covered_names))
            or not actions.issubset(set(step_names))
            or set(covered_names) != set(step_names) - actions):
        raise RuntimeError("unreviewed Upload Route critical step coverage")


def prove_upload_route_critical_coverage_negatives() -> None:
    for event in ("push", "pull_request"):
        names = list(reviewed_upload_route_steps(event))
        covered = list(REVIEWED_UPLOAD_ROUTE_CRITICAL_STEPS[event])
        require_reviewed_upload_route_critical_coverage(event, names, covered)
        for label, changed_names, changed_covered in (
            ("missing body", names, covered[:-1]),
            ("extra body", names, covered + ["Extra"]),
            ("duplicate body", names, covered + [covered[0]]),
            ("missing action", names[1:], covered),
            ("duplicate step", names + [names[0]], covered),
            ("extra step", names + ["Extra"], covered),
        ):
            try:
                require_reviewed_upload_route_critical_coverage(event, changed_names, changed_covered)
            except RuntimeError as exc:
                if str(exc) != "unreviewed Upload Route critical step coverage":
                    raise
            else:
                raise RuntimeError("Upload Route critical coverage negative accepted: " + label)


def require_reviewed_upload_route_critical_steps(source: str, event: str) -> None:
    """Pin exact MinIO readiness, source integrity and writer CAS shell bodies."""
    if event not in REVIEWED_UPLOAD_ROUTE_CRITICAL_STEPS:
        raise RuntimeError("unreviewed Upload Route critical shell step")
    import re
    names = re.findall(r"(?m)^      - name: ([^\r\n]+)$", source)
    require_reviewed_upload_route_critical_coverage(event, names, list(REVIEWED_UPLOAD_ROUTE_CRITICAL_STEPS[event]))
    for name, expected in REVIEWED_UPLOAD_ROUTE_CRITICAL_STEPS[event].items():
        marker = "      - name: " + name + "\n"
        if source.count(marker) != 1:
            raise RuntimeError("unreviewed Upload Route critical shell step")
        start = source.index(marker)
        end = source.find("\n      - name: ", start + len(marker))
        block = source[start:end if end >= 0 else len(source)]
        if hashlib.sha256(block.encode()).hexdigest() != expected:
            raise RuntimeError("unreviewed Upload Route critical shell step")


def prove_upload_route_critical_step_negatives(source_root: Path) -> None:
    for workflow, event in (
        ("reconcile-upload-route-authority.yml", "push"),
        ("reconcile-upload-route-authority-pr.yml", "pull_request"),
    ):
        source = (source_root / ".github/workflows" / workflow).read_text(encoding="utf-8")
        require_reviewed_upload_route_critical_steps(source, event)
        cases = [
            ("MinIO wait", "for attempt in $(seq 1 60)", "for attempt in $(seq 1 1)"),
            ("MinIO endpoint", "/minio/health/live", "/other"),
            ("MinIO failure exit", "          exit 1\n", "          exit 0\n"),
            ("pip installation", "pip install --disable-pip-version-check", "pip uninstall --disable-pip-version-check"),
            ("Go regression timeout", "-timeout=10m", "-timeout=1m"),
            ("format write", "gofmt -w internal/httpserver/observability.go", "gofmt -w other.go"),
            ("format check", 'test -z "$(gofmt -l internal/httpserver/observability.go',
             'test -z "$(echo internal/httpserver/observability.go'),
            ("idempotence check", 'test -z "$(gofmt -l services/import-api/internal/httpserver/observability.go',
             'test -z "$(echo services/import-api/internal/httpserver/observability.go'),
            ("rollback validation", "run: python scripts/validate-memory-os-upload-route-reconcile-rollback.py",
             "run: echo skipped"),
            ("reconcile authority", "run: python scripts/reconcile-memory-os-upload-route-authority.py",
             "run: echo skipped"),
            ("observability", "python scripts/validate-memory-os-observability.py", "echo skipped"),
        ]
        if event == "push":
            cases += [
                ("clean source SHA", 'test "$(git rev-parse HEAD)" = "${{ github.sha }}"', "test true"),
                ("writer CAS fetch", "git fetch origin so", "git fetch origin main"),
                ("writer destination", "git push origin HEAD:so", "git push origin HEAD:main"),
                ("stale CAS exit", "exit 75", "exit 0"),
                ("source capture", 'run: echo "sha=$(git rev-parse HEAD)" >> "$GITHUB_OUTPUT"',
                 'run: echo "sha=wrong" >> "$GITHUB_OUTPUT"'),
            ]
        else:
            cases += [
                ("PR clean source", 'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"', "test true"),
                ("PR clean diff", "git diff --exit-code", "git diff --stat"),
                ("PR final check", "          git diff --check\n          git diff --exit-code",
                 "          git diff --exit-code"),
            ]
        for label, before, after in cases:
            if source.count(before) != 1:
                raise RuntimeError("Upload Route critical step fixture anchor changed: " + label)
            try:
                require_reviewed_upload_route_critical_steps(source.replace(before, after, 1), event)
            except RuntimeError as exc:
                if str(exc) != "unreviewed Upload Route critical shell step":
                    raise
            else:
                raise RuntimeError("Upload Route critical shell step negative accepted: " + label)


def require_reviewed_go_workspace(source_root: Path) -> None:
    """Workspace/vendor changes invalidate the reviewed module-only closure."""
    unsupported = (
        "go.work", "go.work.sum", "services/import-api/go.work",
        "services/import-api/go.work.sum", "services/import-api/vendor",
    )
    for relative in unsupported:
        path = source_root / relative
        if path.exists() or path.is_symlink():
            raise RuntimeError("unreviewed Go workspace/vendor input: " + relative)


def prove_upload_route_go_workspace_negatives() -> None:
    unsupported = (
        "go.work", "go.work.sum", "services/import-api/go.work",
        "services/import-api/go.work.sum", "services/import-api/vendor",
    )
    with tempfile.TemporaryDirectory(prefix="upload-go-workspace-positive-") as tmp:
        require_reviewed_go_workspace(Path(tmp))
    for relative in unsupported:
        with tempfile.TemporaryDirectory(prefix="upload-go-workspace-negative-") as tmp:
            root = Path(tmp)
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if relative.endswith("/vendor"):
                path.mkdir()
            else:
                path.write_text("unreviewed", encoding="utf-8")
            try:
                require_reviewed_go_workspace(root)
            except RuntimeError as exc:
                if str(exc) != "unreviewed Go workspace/vendor input: " + relative:
                    raise
            else:
                raise RuntimeError("Go workspace/vendor negative accepted: " + relative)
    with tempfile.TemporaryDirectory(prefix="upload-go-workspace-link-") as tmp:
        root = Path(tmp)
        (root / "go.work").symlink_to("missing-workspace")
        try:
            require_reviewed_go_workspace(root)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Go workspace/vendor input: go.work":
                raise
        else:
            raise RuntimeError("broken Go workspace symlink accepted")


def require_unaliased_go_path(source_root: Path, path: Path) -> None:
    """Reject source aliases, missing paths and symlinked parent directories."""
    try:
        relative = path.relative_to(source_root)
        resolved = path.resolve(strict=True).relative_to(source_root.resolve(strict=True))
    except (OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError("unreviewed Go source path alias/missing") from exc
    if path.is_symlink() or resolved != relative:
        raise RuntimeError("unreviewed Go source path alias/missing")


def prove_unaliased_go_path_negatives() -> None:
    with tempfile.TemporaryDirectory(prefix="upload-go-path-negative-") as tmp:
        root = Path(tmp)
        directory = root / "pkg"
        directory.mkdir()
        path = directory / "file.go"
        path.write_text("package pkg\n", encoding="utf-8")
        require_unaliased_go_path(root, path)
        path.unlink()
        for label in ("missing", "symlink"):
            if label == "symlink":
                path.symlink_to("missing.go")
            try:
                require_unaliased_go_path(root, path)
            except RuntimeError as exc:
                if str(exc) != "unreviewed Go source path alias/missing":
                    raise
            else:
                raise RuntimeError("Go source alias negative accepted: " + label)
            if path.is_symlink():
                path.unlink()
        directory.rmdir()
        other = root / "other"
        other.mkdir()
        (other / "file.go").write_text("package pkg\n", encoding="utf-8")
        directory.symlink_to(other, target_is_directory=True)
        try:
            require_unaliased_go_path(root, directory / "file.go")
        except RuntimeError as exc:
            if str(exc) != "unreviewed Go source path alias/missing":
                raise
        else:
            raise RuntimeError("Go symlinked parent negative accepted")
        data = root / "data.json"
        data.write_text("{}\n", encoding="utf-8")
        alias = root / "linked.json"
        alias.symlink_to(data.name)
        try:
            require_unaliased_go_path(root, alias)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Go source path alias/missing":
                raise
        else:
            raise RuntimeError("JSON data alias negative accepted")


def reject_unreviewed_go_embeds(source: str) -> None:
    """Go embed assets are extra compile inputs absent from the import graph."""
    import re
    if re.search(r"(?m)^[ \t]*//go:embed(?:[ \t]|$)", source):
        raise RuntimeError("unreviewed Go embedded asset input")


def prove_go_embed_negatives() -> None:
    reject_unreviewed_go_embeds("// go:embed is not a directive\n")
    for label, source in (
        ("direct", "//go:embed static/*\nvar assets embed.FS\n"),
        ("indented", "    //go:embed assets/config.json\n"),
        ("empty", "//go:embed\n"),
        ("tab separator", "//go:embed\tassets/config.json\n"),
        ("tab indent", "\t//go:embed assets/config.json\n"),
    ):
        try:
            reject_unreviewed_go_embeds(source)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Go embedded asset input":
                raise
        else:
            raise RuntimeError("Go embed negative accepted: " + label)


def reject_unreviewed_go_linknames(source: str) -> None:
    """Go linkname can bind unimported symbols outside the static import graph."""
    import re
    if re.search(r"(?m)^[ \t]*//go:linkname(?:[ \t]|$)", source):
        raise RuntimeError("unreviewed Go linkname symbol dependency")


def prove_go_linkname_negatives() -> None:
    reject_unreviewed_go_linknames("// go:linkname is only documentation\n")
    for label, source in (
        ("direct", "//go:linkname local external/pkg.symbol\n"),
        ("indented", "    //go:linkname local external/pkg.symbol\n"),
        ("tab indent", "\t//go:linkname local external/pkg.symbol\n"),
        ("tab separator", "//go:linkname\tlocal external/pkg.symbol\n"),
        ("empty", "//go:linkname\n"),
    ):
        try:
            reject_unreviewed_go_linknames(source)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Go linkname symbol dependency":
                raise
        else:
            raise RuntimeError("Go linkname negative accepted: " + label)


def require_upload_route_event_path_parity(publisher: tuple[str, ...],
                                          pr: tuple[str, ...]) -> None:
    if publisher != pr:
        raise RuntimeError("Upload Route publisher/PR trigger path drift")


def prove_upload_route_path_parity_negatives() -> None:
    baseline = ("a/**", "b/**")
    require_upload_route_event_path_parity(baseline, baseline)
    for candidate in (("a/**", "c/**"), ("b/**", "a/**")):
        try:
            require_upload_route_event_path_parity(baseline, candidate)
        except RuntimeError as exc:
            if str(exc) != "Upload Route publisher/PR trigger path drift":
                raise
        else:
            raise RuntimeError("Upload Route equal-count path drift accepted")


def require_reviewed_upload_route_input_set(observed: set[str], count: int,
                                             expected_sha256: str) -> None:
    """Pin actual path identity, not just the number of Go/Python inputs."""
    canonical = "".join(path + "\n" for path in sorted(observed))
    if (len(observed) != count or
            hashlib.sha256(canonical.encode("utf-8")).hexdigest() != expected_sha256):
        raise RuntimeError("upload route reviewed input identity changed; review required")


def prove_upload_route_input_set_negatives() -> None:
    baseline = {"alpha/a.go", "beta/b.go"}
    digest = hashlib.sha256(b"alpha/a.go\nbeta/b.go\n").hexdigest()
    require_reviewed_upload_route_input_set(baseline, 2, digest)
    require_reviewed_upload_route_input_set(set(reversed(sorted(baseline))), 2, digest)
    for label, candidate in (
        ("same count, different path", {"alpha/a.go", "beta/c.go"}),
        ("missing path", {"alpha/a.go"}),
        ("extra path", baseline | {"gamma/c.go"}),
    ):
        try:
            require_reviewed_upload_route_input_set(candidate, 2, digest)
        except RuntimeError as exc:
            if str(exc) != "upload route reviewed input identity changed; review required":
                raise
        else:
            raise RuntimeError("Upload Route input identity negative accepted: " + label)


def require_reviewed_upload_route_python_imports(source: str, count: int,
                                                 expected_sha256: str) -> None:
    """Pin imported module names, aliases and relative levels, not just path literals."""
    import ast
    entries = []
    tree = ast.parse(source)
    top_level_imports = {id(node) for node in tree.body
                         if isinstance(node, (ast.Import, ast.ImportFrom))}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)) and id(node) not in top_level_imports:
            raise RuntimeError("unreviewed Upload Route Python nested import")
        if isinstance(node, ast.Import):
            entries.extend(f"import:{alias.name}:{alias.asname or ''}" for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            entries.extend(f"from:{node.level}:{node.module or ''}:{alias.name}:{alias.asname or ''}"
                           for alias in node.names)
    if len(entries) != len(set(entries)):
        raise RuntimeError("unreviewed Upload Route Python duplicate import")
    # Import identity is insufficient if a later assignment, parameter, or
    # declaration shadows the imported runtime binding without a new import.
    bindings = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            bindings.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            bindings.update(alias.asname or alias.name for alias in node.names)
    for node in ast.walk(tree):
        shadow = (
            isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del))
            and node.id in bindings
        ) or (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node.name in bindings
        ) or (
            isinstance(node, ast.arg) and node.arg in bindings
        ) or (
            isinstance(node, ast.ExceptHandler) and node.name in bindings
        ) or (
            isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name in bindings
        ) or (
            isinstance(node, ast.MatchMapping) and node.rest in bindings
        )
        if shadow:
            raise RuntimeError("unreviewed Upload Route Python import binding shadow")
    require_reviewed_upload_route_input_set(set(entries), count, expected_sha256)


def prove_upload_route_python_import_negatives() -> None:
    base = "from pathlib import Path\nimport json\n"
    digest = "ee6d40ba2610714dbaad1dec375a82cad8405e8358959b1dabd45a97a413e900"
    require_reviewed_upload_route_python_imports(base, 2, digest)
    require_reviewed_upload_route_python_imports("import json\nfrom pathlib import Path\n", 2, digest)
    require_reviewed_upload_route_python_imports(
        base + "match value:\n    case local_capture:\n        pass\n", 2, digest
    )
    for label, candidate in (
        ("added local module", base + "import scripts.helper\n"),
        ("same-count replacement", base.replace("import json", "import scripts.helper")),
        ("import alias", base.replace("import json", "import json as j")),
        ("relative import", base + "from . import helper\n"),
        ("wildcard import", base.replace("from pathlib import Path", "from pathlib import *")),
        ("duplicate import", base + "import json\n"),
        ("nested if import", base.replace("import json\n", "if False:\n    import json\n")),
        ("nested function import", base.replace("import json\n", "def helper():\n    import json\n")),
        ("nested class import", base.replace("import json\n", "class Helper:\n    import json\n")),
        ("nested try import", base.replace("import json\n", "try:\n    import json\nexcept ImportError:\n    pass\n")),
        ("nested from import", base.replace("from pathlib import Path\n", "def helper():\n    from pathlib import Path\n")),
        ("assigned imported Path", base + "Path = lambda value: value\n"),
        ("function shadows Path", base + "def Path():\n    pass\n"),
        ("class shadows Path", base + "class Path:\n    pass\n"),
        ("async function shadows json", base + "async def json():\n    pass\n"),
        ("parameter shadows Path", base + "def helper(Path):\n    return Path\n"),
        ("local assignment shadows json", base + "def helper():\n    json = None\n"),
        ("delete imported json", base + "del json\n"),
        ("loop target shadows Path", base + "for Path in (1,):\n    pass\n"),
        ("exception alias shadows json", base + "try:\n    raise RuntimeError()\nexcept RuntimeError as json:\n    pass\n"),
        ("match capture shadows Path", base + "match value:\n    case Path:\n        pass\n"),
        ("match as capture shadows Path", base + "match value:\n    case [1] as Path:\n        pass\n"),
        ("match star shadows json", base + "match value:\n    case [*json]:\n        pass\n"),
        ("match mapping rest shadows Path", base + "match value:\n    case {**Path}:\n        pass\n"),
    ):
        try:
            require_reviewed_upload_route_python_imports(candidate, 2, digest)
        except RuntimeError as exc:
            if str(exc) not in {"unreviewed Upload Route Python duplicate import",
                                "unreviewed Upload Route Python nested import",
                                "unreviewed Upload Route Python import binding shadow",
                                "upload route reviewed input identity changed; review required"}:
                raise
        else:
            raise RuntimeError("Upload Route Python import negative accepted: " + label)


def require_reviewed_upload_route_python_source(source: str, count: int,
                                                expected_sha256: str) -> None:
    """Fail closed on changed static path literals or dynamic loader mechanisms."""
    import ast
    import re
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [(node.module or "").split(".")[0]]
        else:
            modules = []
        # These reflective namespace primitives can resolve hidden importers,
        # process launchers, or replace reviewed Path/json bindings at runtime.
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in {"globals", "locals", "vars", "getattr",
                                     "setattr", "delattr"}):
            raise RuntimeError("unreviewed Upload Route Python dynamic dependency")
        if isinstance(node, ast.Name) and node.id in {"__builtins__", "__loader__"}:
            raise RuntimeError("unreviewed Upload Route Python dynamic dependency")
        if any(module in {"importlib", "subprocess", "runpy", "ctypes", "builtins",
                          "posixpath", "ntpath"} for module in modules):
            raise RuntimeError("unreviewed Upload Route Python dynamic dependency")
        # os.path module aliases evade direct os.path.join(...) call matching.
        if (isinstance(node, ast.Import) and
                any(alias.name.startswith("os.path") for alias in node.names)):
            raise RuntimeError("unreviewed Upload Route Python dynamic dependency")
        if (isinstance(node, ast.ImportFrom) and node.module == "os" and
                any(alias.name == "path" for alias in node.names)):
            raise RuntimeError("unreviewed Upload Route Python dynamic dependency")
        # Reviewed validators import Path directly. Module/constructor aliases
        # can assemble split-root paths without the tracked Path(...) call AST.
        if (isinstance(node, ast.Import) and
                any(alias.name.split(".")[0] == "pathlib" for alias in node.names)):
            raise RuntimeError("unreviewed Upload Route Python dynamic dependency")
        if (isinstance(node, ast.ImportFrom) and node.module == "pathlib" and
                any(alias.name not in {"Path", "PurePath"} or
                    alias.asname not in (None, alias.name) for alias in node.names)):
            raise RuntimeError("unreviewed Upload Route Python dynamic dependency")
        # An os alias bypasses the direct os.system/popen/spawn/exec call check.
        if (isinstance(node, ast.Import) and
                any(alias.name == "os" and alias.asname not in (None, "os")
                    for alias in node.names)):
            raise RuntimeError("unreviewed Upload Route Python dynamic dependency")
        # Reflective access can retrieve a process launcher without an
        # os.system call node. Treat it as an unreviewed dependency mechanism.
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in {"getattr", "vars"} and node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "os"):
            raise RuntimeError("unreviewed Upload Route Python dynamic dependency")
        if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                and ((node.value.id == "os" and
                      node.attr in {"__dict__", "__getattribute__", "__class__"}) or
                     (node.value.id == "sys" and
                      node.attr in {"modules", "path", "meta_path",
                                    "path_hooks", "path_importer_cache"}))):
            raise RuntimeError("unreviewed Upload Route Python dynamic dependency")
        if (isinstance(node, ast.ImportFrom) and node.module == "os"
                and any(alias.name in {"system", "popen"} or
                        alias.name.startswith(("spawn", "exec")) for alias in node.names)):
            raise RuntimeError("unreviewed Upload Route Python dynamic dependency")
        if (isinstance(node, ast.ImportFrom) and node.module == "os" and
                any(alias.name in {"*", "__dict__", "__getattribute__", "__class__"}
                    for alias in node.names)):
            raise RuntimeError("unreviewed Upload Route Python dynamic dependency")
        if (isinstance(node, ast.ImportFrom) and node.module == "sys" and
                any(alias.name in {"modules", "path", "meta_path",
                                   "path_hooks", "path_importer_cache"}
                    for alias in node.names)):
            raise RuntimeError("unreviewed Upload Route Python dynamic dependency")
        if (isinstance(node, ast.Import) and
                any(alias.name == "sys" and alias.asname not in (None, "sys")
                    for alias in node.names)):
            raise RuntimeError("unreviewed Upload Route Python dynamic dependency")
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
                and (node.func.attr in {"system", "popen"} or
                     node.func.attr.startswith(("spawn", "exec")))):
            raise RuntimeError("unreviewed Upload Route Python dynamic dependency")
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in {"__import__", "eval", "exec"}):
            raise RuntimeError("unreviewed Upload Route Python dynamic dependency")
        # F-strings and format calls can assemble runtime inputs without
        # introducing a complete static repository-relative path literal.
        if isinstance(node, ast.JoinedStr):
            pieces = "".join(part.value for part in node.values
                             if isinstance(part, ast.Constant) and isinstance(part.value, str))
            if re.search(r"(?:^|[/\\])(?:contracts|docs|scripts|services)(?:[/\\]|$)", pieces):
                raise RuntimeError("unreviewed Upload Route Python composed input path")
        if (isinstance(node, ast.Call) and
                ((isinstance(node.func, ast.Name) and node.func.id in {"Path", "PurePath", "open"}) or
                 (isinstance(node.func, ast.Attribute) and node.func.attr in {"joinpath", "open"})) and
                any(isinstance(arg, ast.JoinedStr) for arg in node.args)):
            raise RuntimeError("unreviewed Upload Route Python composed input path")
        if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)
                and isinstance(node.right, ast.JoinedStr)):
            raise RuntimeError("unreviewed Upload Route Python composed input path")
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "format"
                and isinstance(node.func.value, ast.Constant)
                and isinstance(node.func.value.value, str)
                and re.search(r"(?:^|[/\\])(?:contracts|docs|scripts|services)(?:[/\\]|$)", node.func.value.value)):
            raise RuntimeError("unreviewed Upload Route Python composed input path")
        # Concatenation/format inside a path constructor can hide a new
        # repository input while leaving the full-literal digest unchanged.
        path_call = (isinstance(node, ast.Call) and
                     ((isinstance(node.func, ast.Name) and node.func.id in {"Path", "PurePath", "open"}) or
                      (isinstance(node.func, ast.Attribute) and node.func.attr == "joinpath") or
                      (isinstance(node.func, ast.Attribute) and node.func.attr == "join" and
                       isinstance(node.func.value, ast.Attribute) and node.func.value.attr == "path" and
                       isinstance(node.func.value.value, ast.Name) and node.func.value.value.id == "os")))
        if path_call and any(
                (isinstance(part, ast.BinOp) and isinstance(part.op, ast.Add)) or
                (isinstance(part, ast.Call) and isinstance(part.func, ast.Attribute) and
                 part.func.attr == "format")
                for arg in node.args for part in ast.walk(arg)):
            raise RuntimeError("unreviewed Upload Route Python composed input path")
        if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) and
                ((isinstance(node.right, ast.BinOp) and isinstance(node.right.op, ast.Add)) or
                 (isinstance(node.right, ast.Call) and isinstance(node.right.func, ast.Attribute) and
                  node.right.func.attr == "format"))):
            raise RuntimeError("unreviewed Upload Route Python composed input path")
        # Traversal through an already reviewed Path import can discover
        # untracked inputs without changing any static path or import digest.
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"glob", "rglob", "iterdir", "walk"}):
            raise RuntimeError("unreviewed Upload Route Python dynamic dependency")
        # A split repository root bypasses the fingerprint of complete
        # "contracts/..." / "docs/..." literals. Refuse unreviewed joins.
        roots = {"contracts", "docs", "scripts", "services"}
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in {"Path", "PurePath"} and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value in roots):
            raise RuntimeError("unreviewed Upload Route Python composed input path")
        if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)
                and isinstance(node.right, ast.Constant)
                and node.right.value in roots):
            raise RuntimeError("unreviewed Upload Route Python composed input path")
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "joinpath"
                and any(isinstance(arg, ast.Constant) and arg.value in roots
                        for arg in node.args)):
            raise RuntimeError("unreviewed Upload Route Python composed input path")
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "join"
                and isinstance(node.func.value, ast.Attribute)
                and node.func.value.attr == "path"
                and isinstance(node.func.value.value, ast.Name)
                and node.func.value.value.id == "os"
                and any(isinstance(arg, ast.Constant) and arg.value in roots
                        for arg in node.args)):
            raise RuntimeError("unreviewed Upload Route Python composed input path")
    literals = set(re.findall(r"""["']((?:contracts|docs|scripts|services)/[^"'\s]+)["']""", source))
    # Python merges adjacent string tokens and decodes escapes before a path
    # reaches Path/open. Compare AST values against the reviewed raw literals.
    ast_paths = {
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and re.match(r"^(?:contracts|docs|scripts|services)/", node.value)
    }
    if not ast_paths.issubset(literals):
        raise RuntimeError("unreviewed Upload Route Python composed input path")
    require_reviewed_upload_route_input_set(literals, count, expected_sha256)


def prove_upload_route_python_source_negatives() -> None:
    base = 'from pathlib import Path\nX = "contracts/operations/a.json"\n'
    digest = hashlib.sha256(b"contracts/operations/a.json\n").hexdigest()
    require_reviewed_upload_route_python_source(base, 1, digest)
    require_reviewed_upload_route_python_source(
        base + 'import os\nY = os.path.basename("x")\n', 1, digest
    )
    require_reviewed_upload_route_python_source(
        base + 'import sys\nY = sys.stderr\n', 1, digest
    )
    require_reviewed_upload_route_python_source(
        base + 'from pathlib import Path\nY = Path("tmp") / "local.txt"\n',
        1, digest,
    )
    require_reviewed_upload_route_python_source(
        base + 'Y = f"missing file: {path}"\n', 1, digest
    )
    require_reviewed_upload_route_python_source(
        base + 'Y = "a" + "b"\n', 1, digest
    )
    require_reviewed_upload_route_python_source(
        base + 'Y = Path("tmp").read_text()\n', 1, digest
    )
    for label, candidate in (
        ("same-count literal swap", base.replace("a.json", "b.json")),
        ("added path literal", base + 'Y = "docs/b.md"\n'),
        ("dynamic import", base + "import importlib\n"),
        ("subprocess import", base + "from subprocess import run\n"),
        ("builtin loader", base + 'Y = __import__("os")\n'),
        ("builtin eval", base + 'Y = eval("1")\n'),
        ("globals builtins lookup", base + 'Y = globals()["__builtins__"]\n'),
        ("locals imported Path lookup", base + 'Y = locals()["Path"]\n'),
        ("vars builtins lookup", base + 'Y = vars(__builtins__)\n'),
        ("getattr builtins importer", base + 'Y = getattr(__builtins__, "__import__")\n'),
        ("setattr builtins importer", base + 'Y = setattr(__builtins__, "x", 1)\n'),
        ("delattr builtins importer", base + 'Y = delattr(__builtins__, "x")\n'),
        ("direct builtins namespace", base + 'Y = __builtins__["__import__"]\n'),
        ("module loader namespace", base + 'Y = __loader__.load_module("os")\n'),
        ("os system", base + 'import os\nY = os.system("echo")\n'),
        ("os alias launcher", base + 'import os as shell\nY = shell.system("echo")\n'),
        ("os getattr launcher", base + 'import os\nY = getattr(os, "system")("echo")\n'),
        ("os vars launcher", base + 'import os\nY = vars(os)["system"]("echo")\n'),
        ("os dict launcher", base + 'import os\nY = os.__dict__["system"]("echo")\n'),
        ("os wildcard launcher", base + 'from os import *\nY = system("echo")\n'),
        ("os imported dict launcher", base + 'from os import __dict__ as d\nY = d["system"]("echo")\n'),
        ("os getattribute launcher", base + 'import os\nY = os.__getattribute__("system")("echo")\n'),
        ("os class launcher", base + 'import os\nY = os.__class__.__getattribute__(os, "system")("echo")\n'),
        ("sys modules launcher", base + 'import sys\nY = sys.modules["os"].system("echo")\n'),
        ("sys modules from import", base + 'from sys import modules\nY = modules["os"].system("echo")\n'),
        ("sys path insertion", base + 'import sys\nsys.path.insert(0, "other")\n'),
        ("sys meta path replacement", base + 'import sys\nsys.meta_path = []\n'),
        ("sys path hooks append", base + 'import sys\nsys.path_hooks.append(None)\n'),
        ("sys importer cache clear", base + 'import sys\nsys.path_importer_cache.clear()\n'),
        ("from sys path", base + 'from sys import path\nY = path\n'),
        ("from sys meta path", base + 'from sys import meta_path\nY = meta_path\n'),
        ("from sys path hooks", base + 'from sys import path_hooks\nY = path_hooks\n'),
        ("from sys importer cache", base + 'from sys import path_importer_cache\nY = path_importer_cache\n'),
        ("sys alias modules", base + 'import sys as s\nY = s.modules["os"].system("echo")\n'),
        ("Path root join", base + 'from pathlib import Path\nY = Path("contracts") / "operations/new.json"\n'),
        ("operator root join", base + 'Y = ROOT / "docs" / "fixtures/new.json"\n'),
        ("joinpath root", base + 'Y = ROOT.joinpath("services", "import-api")\n'),
        ("os.path root join", base + 'import os\nY = os.path.join("scripts", "new.py")\n'),
        ("f-string absolute root", base + 'Y = Path(f"{ROOT}/contracts/operations/new.json")\n'),
        ("f-string root segment", base + 'Y = f"{ROOT}/services/import-api/go.mod"\n'),
        ("f-string dynamic Path", base + 'Y = Path(f"{ROOT}/{kind}/{name}")\n'),
        ("f-string path division", base + 'Y = ROOT / f"{name}.json"\n'),
        ("f-string joinpath", base + 'Y = ROOT.joinpath(f"{kind}.json")\n'),
        ("format root segment", base + 'Y = "{}/docs/fixtures/new.json".format(ROOT)\n'),
        ("Path concatenated root", base + 'Y = Path("con" + "tracts/operations/new.json")\n'),
        ("adjacent string Path", base + 'Y = Path("con" "tracts/operations/new.json")\n'),
        ("adjacent string division", base + 'Y = ROOT / ("do" "cs/fixtures/new.json")\n'),
        ("escaped Unicode root", base + 'Y = Path("\\u0063ontracts/operations/new.json")\n'),
        ("escaped hex root", base + 'Y = Path("\\x63ontracts/operations/new.json")\n'),
        ("division concatenated root", base + 'Y = ROOT / ("con" + "tracts") / "operations/new.json"\n'),
        ("Path indirect format", base + 'Y = Path("{}/{}".format(ROOT, name))\n'),
        ("division indirect format", base + 'Y = ROOT / "{}".format(name)\n'),
        ("os.path concatenated root", base + 'import os\nY = os.path.join("scr" + "ipts", "new.py")\n'),
        ("glob discovery", base + 'Y = Path.cwd().glob("*.json")\n'),
        ("recursive glob discovery", base + 'Y = Path(".").rglob("*.py")\n'),
        ("directory iterator discovery", base + 'Y = Path(".").iterdir()\n'),
        ("directory walk discovery", base + 'Y = Path(".").walk()\n'),
        ("Path alias", base + 'from pathlib import Path as P\nY = P("contracts") / "operations/new.json"\n'),
        ("pathlib module alias", base + 'import pathlib as pl\nY = pl.Path("docs") / "new.md"\n'),
        ("unreviewed pathlib constructor", base + 'from pathlib import PosixPath\nY = PosixPath("services")\n'),
        ("wildcard pathlib import", base + 'from pathlib import *\nY = Path("scripts")\n'),
        ("os.path module alias", base + 'import os.path as p\nY = p.join("contracts", "new.json")\n'),
        ("os.path from-import alias", base + 'from os import path as p\nY = p.join("docs", "new.md")\n'),
        ("posixpath direct import", base + 'from posixpath import join\nY = join("services", "new")\n'),
        ("from os system", base + 'from os import system\nY = system("echo")\n'),
        ("runpy loader", base + "import runpy\n"),
        ("ctypes loader", base + "import ctypes\n"),
        ("builtins loader", base + 'import builtins\nY = builtins.eval("1")\n'),
    ):
        try:
            require_reviewed_upload_route_python_source(candidate, 1, digest)
        except RuntimeError as exc:
            if str(exc) not in {
                "unreviewed Upload Route Python dynamic dependency",
                "unreviewed Upload Route Python composed input path",
                "upload route reviewed input identity changed; review required",
            }:
                raise
        else:
            raise RuntimeError("Upload Route Python source negative accepted: " + label)


def require_reviewed_upload_route_event_sequence(paths: tuple[str, ...],
                                                 count: int, expected_sha256: str) -> None:
    """Pin the ordered event filter, including patterns matching no current inputs."""
    canonical = "".join(path + "\n" for path in paths)
    if (len(paths) != count or
            hashlib.sha256(canonical.encode("utf-8")).hexdigest() != expected_sha256):
        raise RuntimeError("Upload Route event path sequence changed; review required")


def prove_upload_route_event_sequence_negatives() -> None:
    baseline = ("a/**", "b/**")
    digest = hashlib.sha256(b"a/**\nb/**\n").hexdigest()
    require_reviewed_upload_route_event_sequence(baseline, 2, digest)
    for label, candidate in (
        ("same count different pattern", ("a/**", "c/**")),
        ("same set reordered", ("b/**", "a/**")),
        ("added no-match pattern", baseline + ("unused/**",)),
        ("removed pattern", ("a/**",)),
    ):
        try:
            require_reviewed_upload_route_event_sequence(candidate, 2, digest)
        except RuntimeError as exc:
            if str(exc) != "Upload Route event path sequence changed; review required":
                raise
        else:
            raise RuntimeError("Upload Route event sequence negative accepted: " + label)


def require_reviewed_upload_route_snapshot_functions(
    source: str, expected: dict[str, str]
) -> None:
    """Reject changed recursive authority snapshot/read scope before trigger claims."""
    for name, digest in expected.items():
        marker = "def " + name + "("
        if source.count(marker) != 1:
            raise RuntimeError("Upload Route reconciler snapshot function changed: " + name)
        start = source.index(marker)
        end = source.find("\ndef ", start + len(marker))
        if end < 0:
            raise RuntimeError("Upload Route reconciler snapshot function changed: " + name)
        fragment = source[start:end + 1]
        if hashlib.sha256(fragment.encode("utf-8")).hexdigest() != digest:
            raise RuntimeError("Upload Route reconciler snapshot function changed: " + name)


def prove_upload_route_snapshot_function_negatives() -> None:
    base = ("def current_authority_files() -> list[Path]:\n    return []\n\n\n"
            "def snapshot_authority_files() -> None:\n    pass\n\n\n"
            "def later():\n    pass\n")
    expected = {}
    for name in ("current_authority_files", "snapshot_authority_files"):
        start = base.index("def " + name + "(")
        end = base.index("\ndef ", start + 1)
        expected[name] = hashlib.sha256(base[start:end + 1].encode("utf-8")).hexdigest()
    require_reviewed_upload_route_snapshot_functions(base, expected)
    for label, mutated in (
        ("changed scanner", base.replace("return []", "return [Path('.')]")),
        ("changed snapshot", base.replace("    pass\n", "    return None\n", 1)),
        ("removed snapshot", base.replace("def snapshot_authority_files()", "def renamed()")),
        ("shadowed scanner", base + "def current_authority_files():\n    pass\n"),
    ):
        try:
            require_reviewed_upload_route_snapshot_functions(mutated, expected)
        except RuntimeError as exc:
            if not str(exc).startswith("Upload Route reconciler snapshot function changed: "):
                raise
        else:
            raise RuntimeError("Upload Route snapshot function negative accepted: " + label)


def upload_route_snapshot_inventory(source_root: Path) -> set[str]:
    """Mirror the reviewed recursive snapshot *paths* without reading their bytes."""
    roots = ("contracts", "scripts", "services/import-api", ".github/workflows", "docs")
    suffixes = {".go", ".json", ".py", ".yml", ".yaml", ".md"}
    result: set[str] = set()
    for relative_root in roots:
        directory = source_root / relative_root
        if not directory.is_dir() or directory.is_symlink():
            raise RuntimeError("Upload Route snapshot root missing/aliased: " + relative_root)
        for path in directory.rglob("*"):
            if path.is_symlink():
                raise RuntimeError("unreviewed Upload Route snapshot symlink: " +
                                   path.relative_to(source_root).as_posix())
            if not path.is_file() or path.suffix not in suffixes:
                continue
            relative = path.relative_to(source_root)
            if relative.parts[:2] in {("docs", "fixtures"), ("docs", "evidence")}:
                continue
            if relative.as_posix() == "scripts/reconcile-memory-os-upload-route-authority.py":
                continue
            result.add(relative.as_posix())
    return result


def require_upload_route_snapshot_gap(paths: set[str], patterns: tuple[str, ...],
                                      matches, min_count: int, min_uncovered: int) -> None:
    uncovered = {path for path in paths
                 if not any(matches(path, pattern) for pattern in patterns)}
    if len(paths) < min_count or len(uncovered) < min_uncovered:
        raise RuntimeError("Upload Route broad snapshot trigger gap changed; review required")


def prove_upload_route_snapshot_inventory_negatives() -> None:
    with tempfile.TemporaryDirectory(prefix="upload-snapshot-inventory-") as tmp:
        root = Path(tmp)
        included = (
            "contracts/a.json", "scripts/other.py", "services/import-api/a.go",
            ".github/workflows/a.yml", "docs/a.md",
        )
        excluded = (
            "docs/fixtures/ignored.md", "docs/evidence/ignored.md",
            "scripts/reconcile-memory-os-upload-route-authority.py",
        )
        for relative in included + excluded:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture", encoding="utf-8")
        observed = upload_route_snapshot_inventory(root)
        if observed != set(included):
            raise RuntimeError("Upload Route snapshot inventory positive/exclusion fixture failed")
        for label, relative, target in (
            ("file alias", "docs/alias.md", "a.md"),
            ("directory alias", "docs/linked", "../contracts"),
            ("broken alias", "docs/broken.md", "missing.md"),
        ):
            alias = root / relative
            alias.symlink_to(target, target_is_directory=(label == "directory alias"))
            try:
                upload_route_snapshot_inventory(root)
            except RuntimeError as exc:
                if not str(exc).startswith("unreviewed Upload Route snapshot symlink: "):
                    raise
            else:
                raise RuntimeError("Upload Route snapshot symlink negative accepted: " + label)
            finally:
                alias.unlink()
        matcher = lambda path, pattern: path == pattern
        require_upload_route_snapshot_gap(observed, ("contracts/a.json",), matcher, 5, 4)
        for label, paths, patterns in (
            ("missing path", observed - {"docs/a.md"}, ("contracts/a.json",)),
            ("covered extra path", observed, ("contracts/a.json", "docs/a.md")),
        ):
            try:
                require_upload_route_snapshot_gap(paths, patterns, matcher, 5, 4)
            except RuntimeError as exc:
                if str(exc) != "Upload Route broad snapshot trigger gap changed; review required":
                    raise
            else:
                raise RuntimeError("Upload Route snapshot gap negative accepted: " + label)


def require_reviewed_upload_route_dependency_blob(raw: bytes, expected: str) -> None:
    """Pin exact dependency bytes with the repository's Git blob SHA-1."""
    header = b"blob " + str(len(raw)).encode("ascii") + b"\0"
    if hashlib.sha1(header + raw).hexdigest() != expected:
        raise RuntimeError("Upload Route dependency manifest changed; review required")


def prove_upload_route_dependency_blob_negatives() -> None:
    original = b"module example.com/test\n"
    header = b"blob " + str(len(original)).encode("ascii") + b"\0"
    digest = hashlib.sha1(header + original).hexdigest()
    require_reviewed_upload_route_dependency_blob(original, digest)
    for label, candidate in (
        ("same-length mutation", original.replace(b"test", b"risk")),
        ("truncated manifest", original[:-1]),
        ("extra dependency", original + b"require example.com/x v1.0.0\n"),
    ):
        try:
            require_reviewed_upload_route_dependency_blob(candidate, digest)
        except RuntimeError as exc:
            if str(exc) != "Upload Route dependency manifest changed; review required":
                raise
        else:
            raise RuntimeError("Upload Route dependency manifest negative accepted: " + label)


def autonomous_learning_guard_event_paths(source: str, event: str,
                                          expected_count: int) -> tuple[str, ...]:
    """Parse only the reviewed literal trigger grammar; never infer wildcard reach."""
    lines = source.splitlines()
    on_keys = ("on:", '"on":', "'on':")
    event_keys = ("  " + event + ":", '  "' + event + '":', "  '" + event + "':")
    if (sum(line in on_keys for line in lines) != 1 or
            sum(line in event_keys for line in lines) != 1 or
            lines.count("on:") != 1 or lines.count("  " + event + ":") != 1):
        raise RuntimeError("Autonomous Learning Guard event trigger authority changed")
    start = lines.index("  " + event + ":")
    end = next((i for i in range(start + 1, len(lines))
                if lines[i] and (not lines[i].startswith(" ") or
                                 (lines[i].startswith("  ") and not lines[i].startswith("   ")))), len(lines))
    block = lines[start + 1:end]
    if (block.count("    paths:") != 1 or
            block[:block.index("    paths:")] != ["    branches: [so]"]):
        raise RuntimeError("Autonomous Learning Guard event trigger authority changed")
    paths = block[block.index("    paths:") + 1:]
    if (len(paths) != expected_count or
            any(not row.startswith('      - "') or not row.endswith('"') for row in paths)):
        raise RuntimeError("Autonomous Learning Guard event trigger authority changed")
    parsed = tuple(row[9:-1] for row in paths)
    if len(set(parsed)) != len(parsed) or any("*" in path or "!" in path for path in parsed):
        raise RuntimeError("Autonomous Learning Guard event trigger authority changed")
    return parsed


def require_autonomous_learning_trigger_claims(paths: tuple[str, ...],
                                               claims: dict[str, bool]) -> None:
    for relative, claimed_covered in claims.items():
        if (relative in paths) is not claimed_covered:
            raise RuntimeError("Autonomous Learning Guard trigger coverage claim changed: " + relative)


def prove_autonomous_learning_trigger_negatives() -> None:
    sample = ('on:\n  push:\n    branches: [so]\n    paths:\n      - "scripts/guard.py"\n'
              '      - "docs/authority.md"\n  pull_request:\n    branches: [so]\n    paths:\n'
              '      - "scripts/guard.py"\n      - "docs/authority.md"\n')
    paths = autonomous_learning_guard_event_paths(sample, "push", 2)
    require_autonomous_learning_trigger_claims(paths, {"scripts/guard.py": True, "go.mod": False})
    for label, claims in (
        ("false coverage", {"go.mod": True}),
        ("hidden coverage", {"scripts/guard.py": False}),
    ):
        try:
            require_autonomous_learning_trigger_claims(paths, claims)
        except RuntimeError as exc:
            if not str(exc).startswith("Autonomous Learning Guard trigger coverage claim changed: "):
                raise
        else:
            raise RuntimeError("Autonomous Learning Guard coverage negative accepted: " + label)
    for label, changed, event in (
        ("missing PR event", sample.replace("  pull_request:", "  other:"), "pull_request"),
        ("wildcard path", sample.replace('"docs/authority.md"', '"docs/*.md"'), "push"),
        ("quoted on shadow", sample + "'on':\n  push:\n", "push"),
        ("double-quoted on shadow", sample + '"on":\n  push:\n', "push"),
        ("quoted push shadow", sample + "  'push':\n    paths:\n      - \"scripts/evil.py\"\n", "push"),
        ("quoted PR shadow", sample + '  "pull_request":\n    paths:\n      - "scripts/evil.py"\n', "pull_request"),
        ("wrong push branch", sample.replace("    branches: [so]", "    branches: [main]", 1), "push"),
        ("missing PR branch", sample.replace("  pull_request:\n    branches: [so]\n",
                                              "  pull_request:\n"), "pull_request"),
        ("shadowed branch", sample.replace("    paths:\n", "    branches: [main]\n    paths:\n", 1), "push"),
    ):
        try:
            autonomous_learning_guard_event_paths(changed, event, 2)
        except RuntimeError as exc:
            if str(exc) != "Autonomous Learning Guard event trigger authority changed":
                raise
        else:
            raise RuntimeError("Autonomous Learning Guard event negative accepted: " + label)


REVIEWED_UPLOAD_ROUTE_FOCUSED_GO_TESTS = {
    "services/import-api/internal/httpserver/route_authority_test.go": (
        "TestRouteAuthorityMatchesRegisteredUploadSurface",
        "TestRoutePrefilterPreservesKnownAndRejectsUnknownShapes",
    ),
    "services/import-api/internal/httpserver/server_live_test.go": (
        "TestUploadLifecycleOverHTTP",
        "TestAccountDeletionFencesAndErasesOverHTTP",
    ),
}

def require_reviewed_upload_route_focused_go_tests(sources: dict[str, str]) -> None:
    import re
    failure = "unreviewed Upload Route focused Go test target"
    if set(sources) != set(REVIEWED_UPLOAD_ROUTE_FOCUSED_GO_TESTS):
        raise RuntimeError(failure)
    command = [value for value in REVIEWED_UPLOAD_ROUTE_RUNTIME_COMMANDS
               if value.startswith("go test ./internal/httpserver ")]
    if len(command) != 1:
        raise RuntimeError(failure)
    selectors = re.findall(r"-run '\^\(([^']+)\)\$'", command[0])
    expected = tuple(name for names in REVIEWED_UPLOAD_ROUTE_FOCUSED_GO_TESTS.values()
                     for name in names)
    if len(selectors) != 1 or tuple(selectors[0].split("|")) != expected:
        raise RuntimeError(failure)
    for path, names in REVIEWED_UPLOAD_ROUTE_FOCUSED_GO_TESTS.items():
        source = sources[path]
        declarations = re.findall(r"(?m)^func[ \t]+(Test[A-Za-z0-9_]+)[ \t]*\(", source)
        if tuple(name for name in declarations if name in expected) != names:
            raise RuntimeError(failure)
        for name in names:
            signature = rf"(?m)^func[ \t]+{re.escape(name)}\(t \*testing\.T\)[ \t]*\{{"
            matches = list(re.finditer(signature, source))
            if len(matches) != 1:
                raise RuntimeError(failure)
            following = re.search(r"(?m)^func[ \t]+", source[matches[0].end():])
            body = source[matches[0].end():(
                matches[0].end() + following.start() if following else len(source))]
            if (re.search(r"\bt\.Skip(?:f|Now)?[ \t]*\(", body) or
                    not re.search(r"\bt\.(?:Fatal|Fatalf|Error|Errorf|Fail|FailNow)[ \t]*\(", body)):
                raise RuntimeError(failure)

def prove_upload_route_focused_go_test_negatives(source_root: Path) -> None:
    files = {path: (source_root / path).read_text(encoding="utf-8")
             for path in REVIEWED_UPLOAD_ROUTE_FOCUSED_GO_TESTS}
    require_reviewed_upload_route_focused_go_tests(files)
    route, live = tuple(REVIEWED_UPLOAD_ROUTE_FOCUSED_GO_TESTS)
    def reject(label: str, path: str, old: str, new: str) -> None:
        if files[path].count(old) != 1:
            raise RuntimeError("focused Go test fixture anchor drift: " + label)
        changed = dict(files)
        changed[path] = files[path].replace(old, new, 1)
        try:
            require_reviewed_upload_route_focused_go_tests(changed)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Upload Route focused Go test target":
                raise
        else:
            raise RuntimeError("focused Go test negative accepted: " + label)
    reject("renamed route test", route,
           "func TestRouteAuthorityMatchesRegisteredUploadSurface(t *testing.T) {",
           "func TestRenamedRouteAuthority(t *testing.T) {")
    reject("duplicate route test", route,
           "func TestRoutePrefilterPreservesKnownAndRejectsUnknownShapes(t *testing.T) {",
           "func TestRoutePrefilterPreservesKnownAndRejectsUnknownShapes(t *testing.T) {\n"
           "func TestRoutePrefilterPreservesKnownAndRejectsUnknownShapes(t *testing.T) {")
    reject("wrong live test signature", live,
           "func TestUploadLifecycleOverHTTP(t *testing.T) {",
           "func TestUploadLifecycleOverHTTP(t *testing.B) {")
    reject("skipped live test", live,
           "func TestUploadLifecycleOverHTTP(t *testing.T) {",
           "func TestUploadLifecycleOverHTTP(t *testing.T) {\n\tt.Skip(\"disabled\")")
    reject("no route assertion", route,
           't.Fatalf("POST %s returned', 't.Logf("POST %s returned')


def require_reviewed_upload_route_live_skip_boundary(source: str) -> None:
    """Bind the live helper's conditional skip to the two required CI inputs."""
    import re
    failure = "unreviewed Upload Route live test skip boundary"
    prefix = (
        'func newLiveServer(t *testing.T) *liveServer {\n'
        '\tt.Helper()\n'
        '\tdatabaseURL := os.Getenv("MEMORY_OS_TEST_DATABASE_URL")\n'
        '\tendpoint := os.Getenv("MEMORY_OS_TEST_S3_ENDPOINT")\n'
        '\tif databaseURL == "" || endpoint == "" {\n'
        '\t\tt.Skip("MEMORY_OS_TEST_DATABASE_URL and MEMORY_OS_TEST_S3_ENDPOINT are required; skipping HTTP server tests")\n'
        '\t}\n'
        '\tctx := context.Background()\n'
    )
    if source.count(prefix) != 1:
        raise RuntimeError(failure)
    start = source.index(prefix)
    end = source.find("\nfunc ", start + len(prefix))
    helper = source[start:end if end >= 0 else len(source)]
    if len(re.findall(r"\bt\.Skip(?:f|Now)?[ \t]*\(", helper)) != 1:
        raise RuntimeError(failure)
    for name in ("TestUploadLifecycleOverHTTP", "TestAccountDeletionFencesAndErasesOverHTTP"):
        match = re.search(rf"(?m)^func {name}\(t \*testing\.T\) \{{", source)
        if match is None:
            raise RuntimeError(failure)
        following = re.search(r"(?m)^func[ \t]+", source[match.end():])
        body = source[match.end():(
            match.end() + following.start() if following else len(source))]
        if body.count("server := newLiveServer(t)") != 1:
            raise RuntimeError(failure)


def prove_upload_route_live_skip_boundary_negatives(source_root: Path) -> None:
    path = source_root / "services/import-api/internal/httpserver/server_live_test.go"
    source = path.read_text(encoding="utf-8")
    require_reviewed_upload_route_live_skip_boundary(source)
    for label, old, new in (
        ("unconditional skip", 'if databaseURL == "" || endpoint == "" {', 'if true {'),
        ("skip erased", '\t\tt.Skip("MEMORY_OS_TEST_DATABASE_URL', '\t\tt.Log("MEMORY_OS_TEST_DATABASE_URL'),
        ("wrong env", 'os.Getenv("MEMORY_OS_TEST_S3_ENDPOINT")', 'os.Getenv("OTHER_S3_ENDPOINT")'),
        ("extra skip", '\t}\n\tctx := context.Background()', '\t}\n\tt.SkipNow()\n\tctx := context.Background()'),
        ("missing upload setup", 'func TestUploadLifecycleOverHTTP(t *testing.T) {\n\tserver := newLiveServer(t)', 'func TestUploadLifecycleOverHTTP(t *testing.T) {\n\tserver := &liveServer{}'),
    ):
        if source.count(old) != 1:
            raise RuntimeError("live skip boundary fixture anchor drift: " + label)
        changed = source.replace(old, new, 1)
        try:
            require_reviewed_upload_route_live_skip_boundary(changed)
        except RuntimeError as exc:
            if str(exc) != "unreviewed Upload Route live test skip boundary":
                raise
        else:
            raise RuntimeError("live skip boundary negative accepted: " + label)


def prove_upload_route_go_direct_inputs(source_root: Path) -> None:
    """Report a compile-input lower bound; never claim transitive trigger closure."""
    import re
    require_reviewed_go_workspace(source_root)
    prove_upload_route_go_workspace_negatives()
    prove_upload_route_focused_go_test_negatives(source_root)
    prove_upload_route_live_skip_boundary_negatives(source_root)
    prove_upload_route_toolchain_environment_negatives()
    prove_upload_route_action_negatives()
    prove_upload_route_runtime_command_negatives()
    prove_upload_route_shell_dispatch_negatives()
    prove_upload_route_run_key_negatives()
    prove_upload_route_working_directory_negatives()
    prove_upload_route_action_input_negatives()
    prove_upload_route_container_image_negatives()
    prove_upload_route_permission_negatives()
    prove_upload_route_job_execution_negatives()
    prove_upload_route_step_order_negatives()
    prove_upload_route_test_environment_negatives(source_root)
    prove_upload_route_critical_step_negatives(source_root)
    prove_upload_route_critical_coverage_negatives()
    prove_upload_route_go_build_constraint_negatives()
    prove_upload_route_go_package_negatives()
    prove_unaliased_go_path_negatives()
    prove_go_embed_negatives()
    prove_go_linkname_negatives()
    prove_upload_route_path_parity_negatives()
    prove_upload_route_input_set_negatives()
    prove_upload_route_python_source_negatives()
    prove_upload_route_python_import_negatives()
    prove_upload_route_event_sequence_negatives()
    prove_upload_route_snapshot_function_negatives()
    prove_upload_route_snapshot_inventory_negatives()
    prove_upload_route_dependency_blob_negatives()
    prove_autonomous_learning_trigger_negatives()
    for relative, expected in (
        ("requirements-security-validation.txt", "8790ebe281089c679686d0689ecd59080899c3cb"),
        ("services/import-api/go.mod", "ae1c51f23619581ac073fbb9c512c5f71f8f030c"),
        ("services/import-api/go.sum", "7600ae8d6d9cb772cba6b733c77ef95152bc1cf0"),
    ):
        path = source_root / relative
        require_unaliased_go_path(source_root, path)
        require_reviewed_upload_route_dependency_blob(path.read_bytes(), expected)
    reconciler = source_root / "scripts/reconcile-memory-os-upload-route-authority.py"
    require_unaliased_go_path(source_root, reconciler)
    require_reviewed_upload_route_snapshot_functions(
        reconciler.read_text(encoding="utf-8"),
        {
            "current_authority_files": "5f61d86e5e8b3e97a61a84682e7790725897ce161f26888d7c6604801669882c",
            "snapshot_authority_files": "6a11c9e680ca9f9499cd145b10ee81d90f9f59ffb2385ef068c36a8e81c7515d",
        },
    )
    reviewed_imports = {
        "scripts/validate-memory-os-metrics.py": (6, "a403f426fc984eafa9d76d30e179da7b162cadc55292e5f273ab87807bc1a1af"),
        "scripts/validate-memory-os-rate-limit.py": (6, "a403f426fc984eafa9d76d30e179da7b162cadc55292e5f273ab87807bc1a1af"),
        "scripts/validate-memory-os-observability.py": (5, "d95b254a5b523994df03223a178867922566bf3d3d34755b29466cf693a0360a"),
        "scripts/validate-memory-os-operability.py": (9, "faa8cb7cc62bfa675d883b30492e5993b5c48146c920a43e7e66cb6c569bbd5f"),
    }
    for relative, count, digest in (
        ("scripts/validate-memory-os-metrics.py", 4,
         "28b4778ad36ea2548201518eae8e53483bf2a1165bafea185b3dc03519ea277f"),
        ("scripts/validate-memory-os-rate-limit.py", 5,
         "201afd7d79854a23e62fefea5c0032f2d8668c928f54e18e8ac210037e57740f"),
        ("scripts/validate-memory-os-observability.py", 6,
         "e075e8466606397fc9f373fb45e74793c1e2d55564bdeb48b3ebbfde368ad6a9"),
        ("scripts/validate-memory-os-operability.py", 11,
         "e6b898667d7b8210a2087fa45a75ba5b3640690444d8992e20b947c15dd66259"),
    ):
        require_unaliased_go_path(source_root, source_root / relative)
        require_reviewed_upload_route_python_source(
            (source_root / relative).read_text(encoding="utf-8"), count, digest
        )
        require_reviewed_upload_route_python_imports(
            (source_root / relative).read_text(encoding="utf-8"), *reviewed_imports[relative]
        )
    target = source_root / "services/import-api/internal/httpserver"
    require_unaliased_go_path(source_root, target)
    # Go list classifies these additional C++/header/Fortran/ObjC inputs.
    native_suffixes = {".c", ".h", ".s", ".cc", ".cpp", ".cxx", ".hh", ".hpp",
                       ".hxx", ".f", ".for", ".f90", ".m", ".syso", ".swig", ".swigcxx"}
    def reject_native(directory: Path) -> None:
        if any(p.suffix.lower() in native_suffixes for p in directory.iterdir()):
            raise RuntimeError("unreviewed Go native build input: " + str(directory))
    with tempfile.TemporaryDirectory(prefix="upload-go-native-suffix-") as tmp:
        fixture_root = Path(tmp)
        for suffix in (".cxx", ".hh", ".hpp", ".hxx", ".f", ".for", ".f90", ".m"):
            fixture = fixture_root / ("native" + suffix)
            fixture.write_text("fixture\n", encoding="utf-8")
            try:
                reject_native(fixture_root)
            except RuntimeError as exc:
                if not str(exc).startswith("unreviewed Go native build input: "):
                    raise
            else:
                raise RuntimeError("unreviewed Go native suffix accepted: " + suffix)
            fixture.unlink()
        reject_native(fixture_root)
    reject_native(target)
    require_unaliased_go_path(source_root, source_root / "services/import-api/go.mod")
    module_text = (source_root / "services/import-api/go.mod").read_text(encoding="utf-8")
    module_name = "module github.com/m-shogo/memories-project/services/import-api\n"
    if (not module_text.startswith(module_name) or
            re.search(r"(?m)^\s*replace\b", module_text)):
        raise RuntimeError("unreviewed Go module path or replace directive")
    # A local replacement or CGo input would invalidate a Go-only import closure.
    if not re.search(r"(?m)^\s*replace\b", "replace example.com/x => ../x"):
        raise RuntimeError("Go module replace negative fixture failed")
    go_files = sorted(target.glob("*.go"))
    if len(go_files) < 27 or not any(p.name.endswith("_test.go") for p in go_files):
        raise RuntimeError("upload route Go compilation surface shrank without review")
    packages: set[str] = set()
    import_entries: set[str] = set()
    alias_entries: set[str] = set()
    for file in go_files:
        require_unaliased_go_path(source_root, file)
        source = file.read_text(encoding="utf-8")
        require_reviewed_upload_route_go_package(file.relative_to(source_root).as_posix(), source)
        require_reviewed_upload_route_go_build_constraints(file.relative_to(source_root).as_posix(), source)
        reject_unreviewed_go_embeds(source)
        reject_unreviewed_go_linknames(source)
        if 'import "C"' in source:
            raise RuntimeError("unreviewed Go CGo import")
        packages.update(upload_route_local_go_imports(source))
        import_entries.update(file.relative_to(source_root).as_posix() + "\t" + dependency
                              for dependency in upload_route_local_go_imports(source, include_external=True))
        alias_entries.update(file.relative_to(source_root).as_posix() + "\t" + binding
                             for binding in upload_route_local_go_imports(source, include_aliases=True))
    if len(packages) < 21:
        raise RuntimeError("upload route local Go package inventory shrank without review")
    inputs = {p.relative_to(source_root).as_posix() for p in go_files}
    pending = list(packages)
    visited: set[str] = set()
    while pending:
        package = pending.pop()
        if package in visited:
            continue
        if len(visited) >= 64 or not package.startswith("internal/"):
            raise RuntimeError("unreviewed Go local import closure")
        visited.add(package)
        directory = source_root / "services/import-api" / package
        if directory.exists() or directory.is_symlink():
            require_unaliased_go_path(source_root, directory)
        files = list(directory.glob("*.go")) if directory.is_dir() else []
        files = [p for p in files if not p.name.endswith("_test.go")]
        if not files:
            raise RuntimeError("missing Go import closure package: " + package)
        reject_native(directory)
        for file in files:
            require_unaliased_go_path(source_root, file)
            inputs.add(file.relative_to(source_root).as_posix())
            source = file.read_text(encoding="utf-8")
            require_reviewed_upload_route_go_package(file.relative_to(source_root).as_posix(), source)
            require_reviewed_upload_route_go_build_constraints(file.relative_to(source_root).as_posix(), source)
            reject_unreviewed_go_embeds(source)
            reject_unreviewed_go_linknames(source)
            if 'import "C"' in source:
                raise RuntimeError("unreviewed Go CGo import")
            import_entries.update(file.relative_to(source_root).as_posix() + "\t" + dependency
                                  for dependency in upload_route_local_go_imports(source, include_external=True))
            alias_entries.update(file.relative_to(source_root).as_posix() + "\t" + binding
                                 for binding in upload_route_local_go_imports(source, include_aliases=True))
            for dependency in upload_route_local_go_imports(source):
                if dependency not in visited:
                    pending.append(dependency)
                    packages.add(dependency)
        if len(inputs) > 512:
            raise RuntimeError("Go local import closure exceeds reviewed file budget")
    if len(visited) < 22:
        raise RuntimeError("reviewed transitive Go package missing from closure")
    # Pin exact per-file Go imports, including external modules. The CI
    # baseline was independently observed before this enforcement change.
    require_reviewed_upload_route_input_set(
        import_entries, 722, "66a22b030f30e6a127445fbd63f659c9f1ca89c0a85b9cb5988ff7829e029da6"
    )
    # Explicit Go import bindings can drift without changing imported paths.
    require_reviewed_upload_route_input_set(
        alias_entries, 3, "eeead3493d6bc1d40354fe2de6d1db6a07a202ce4d9d7dd19c8bb9c1436dfb25"
    )
    for path in ("services/import-api/go.mod", "services/import-api/go.sum",
                 "requirements-security-validation.txt"):
        if not (source_root / path).is_file():
            raise RuntimeError("missing upload route setup input: " + path)
        require_unaliased_go_path(source_root, source_root / path)
        inputs.add(path)
    if not {"services/import-api/internal/metrics/recorder.go",
            "services/import-api/internal/reqid/reqid.go",
            "services/import-api/internal/preview/atomic_materializer.go"}.issubset(inputs):
        raise RuntimeError("known direct Go compile inputs vanished from inventory")
    # These six additional runtime inputs are read by the invoked Python
    # metrics, rate-limit, and observability validators, not by Go compilation.
    for path in (
        "contracts/operations/production-operability-status.json",
        "docs/fixtures/memory-os-operability/metrics.negative.v1.json",
        "docs/fixtures/memory-os-operability/rate-limit-policies.negative.v1.json",
        "contracts/operations/observability-event-contract.v1.json",
        "docs/fixtures/memory-os-operability/observability-events.valid.v1.json",
        "docs/fixtures/memory-os-operability/observability-events.negative.v1.json",
    ):
        input_path = source_root / path
        if not input_path.is_file():
            raise RuntimeError("missing direct Python validator input: " + path)
        require_unaliased_go_path(source_root, input_path)
        inputs.add(path)
    # Directly loaded by validate-memory-os-operability.py during Upload Route.
    for path in (
        "docs/memory-os-production-operability-audit-2026-07-24.md",
        "docs/memory-os-current-authority-order-round-10-operability.md",
        "contracts/operations/live-postgres-load-scenario-contract.v1.json",
        "contracts/operations/live-object-load-scenario-contract.v1.json",
        "contracts/operations/sustained-local-soak-contract.v1.json",
        "docs/fixtures/memory-os-operability/sustained-local-soak-trend-review.v1.json",
    ):
        input_path = source_root / path
        if not input_path.is_file():
            raise RuntimeError("missing direct operability validator input: " + path)
        require_unaliased_go_path(source_root, input_path)
        inputs.add(path)

    require_reviewed_upload_route_input_set(
        inputs, 109, "e91d5755313f84ffb1326d693d099c02ee840ae250e699dcea6169046fc76604"
    )

    def matches(path: str, pattern: str) -> bool:
        if pattern.startswith("!") or any(c in pattern for c in "?[]{}"):
            raise RuntimeError("unsupported upload route path filter")
        if pattern.endswith("/**") and pattern.count("*") == 2:
            return path.startswith(pattern[:-2])
        if "**" in pattern:
            raise RuntimeError("unreviewed recursive path filter")
        return re.fullmatch(re.escape(pattern).replace(r"\*", "[^/]*"), path) is not None

    if not matches("services/import-api/internal/httpserver/server.go",
                   "services/import-api/internal/httpserver/**"):
        raise RuntimeError("upload route recursive positive fixture failed")
    if matches("services/import-api/internal/metrics/recorder.go",
               "services/import-api/internal/httpserver/**") or matches(
            "scripts/validate-memory-os-rate-limit/nested.py",
            "scripts/validate-memory-os-rate-limit*.py"):
        raise RuntimeError("upload route path-negative fixture failed")
    prove_upload_route_event_parser_negatives()
    prove_upload_route_event_set_negatives()
    uncovered_sets = []
    reviewed_paths = []
    for workflow, event in (
        ("reconcile-upload-route-authority.yml", "push"),
        ("reconcile-upload-route-authority-pr.yml", "pull_request"),
    ):
        workflow_path = source_root / ".github/workflows" / workflow
        require_unaliased_go_path(source_root, workflow_path)
        source = workflow_path.read_text(encoding="utf-8")
        require_reviewed_upload_route_toolchain_environment(source)
        require_reviewed_upload_route_actions(source)
        require_reviewed_upload_route_runtime_commands(source)
        reject_unreviewed_upload_route_shell_dispatch(source)
        require_reviewed_upload_route_run_keys(source, 11 if event == "push" else 10)
        require_reviewed_upload_route_working_directories(source)
        require_reviewed_upload_route_action_inputs(source, event)
        require_reviewed_upload_route_container_images(source)
        require_reviewed_upload_route_permissions(source, event)
        require_reviewed_upload_route_job_execution(source, event)
        require_reviewed_upload_route_step_order(source, event)
        require_reviewed_upload_route_test_environment(source, event)
        require_reviewed_upload_route_critical_steps(source, event)
        require_reviewed_upload_route_event_set(source, event)
        patterns = upload_route_event_paths(source, event)
        reviewed_paths.append(patterns)
        uncovered_sets.append({path for path in inputs
                               if not any(matches(path, pat) for pat in patterns)})
    require_upload_route_event_path_parity(*reviewed_paths)
    snapshot_paths = upload_route_snapshot_inventory(source_root)
    require_upload_route_snapshot_gap(snapshot_paths, reviewed_paths[0], matches, 1687, 1620)
    guard_path = source_root / ".github/workflows/autonomous-learning-guard.yml"
    require_unaliased_go_path(source_root, guard_path)
    guard_source = guard_path.read_text(encoding="utf-8")
    critical = {
        ".github/workflows/reconcile-upload-route-authority.yml": False,
        ".github/workflows/reconcile-upload-route-authority-pr.yml": False,
        "scripts/validate-memory-os-metrics.py": False,
        "scripts/validate-memory-os-rate-limit.py": False,
        "scripts/validate-memory-os-observability.py": False,
        "scripts/validate-memory-os-operability.py": False,
        "requirements-security-validation.txt": False,
        "services/import-api/go.mod": False,
        "services/import-api/go.sum": False,
        "scripts/validate-autonomous-learning-system-negative.py": True,
    }
    for event in ("push", "pull_request"):
        guard_paths = autonomous_learning_guard_event_paths(guard_source, event, 15)
        require_autonomous_learning_trigger_claims(guard_paths, critical)
        if len(snapshot_paths.intersection(guard_paths)) != 15:
            raise RuntimeError("Autonomous Learning Guard reviewed snapshot trigger reach changed")
    for patterns in reviewed_paths:
        require_reviewed_upload_route_event_sequence(
            patterns, 12, "c8ee443d21a468393cec2d4104c9b47da60f38173edacba213c74f16df478fd8"
        )
    for missing in uncovered_sets:
        require_reviewed_upload_route_input_set(
            missing, 81, "ecdb964e00dc346c1e8fefe730c18f01996c3512fe4c0dc3339387ef8f73024c"
        )
    if len(inputs) < 109 or any(len(missing) < 81 for missing in uncovered_sets):
        raise RuntimeError("upload route direct input trigger gap changed; review required")


def prove_prewrite_fanout_cli(source_root: Path) -> int:
    """Require the actual fanout CLI to conservatively count ambiguous events."""
    guard = source_root / "scripts/audit-memory-os-workflow-trigger-fanout.py"
    cases = (
        ("BOM filtered match", '\ufeffon:\n  push:\n    paths:\n      - "scripts/a.py"\n', 1),
        ("BOM unrelated", '\ufeffon:\n  push:\n    paths:\n      - "docs/**"\n', 0),
        ("BOM unfiltered", '\ufeffon: push\n', 1),
        ("BOM midstream ambiguity", 'on:\n  push:\n    paths:\n      - "docs/**"\n# \ufeff\n', 1),
        ("duplicate on", 'on:\n  push:\n    paths:\n      - "docs/**"\non: push\n', 1),
        ("duplicate event", 'on:\n  push:\n    paths:\n      - "docs/**"\n  push:\n    paths:\n      - "scripts/a.py"\n', 1),
        ("event alias", 'on: *events\n', 1),
        ("quoted comment", 'on:\n  push:\n    paths:\n      - "scripts/a.py" # note\n', 1),
        ("plain comment", 'on:\n  push:\n    paths:\n      - scripts/a.py # note\n', 1),
        ("brace glob", 'on:\n  push:\n    paths:\n      - "scripts/{a,b}.py"\n', 1),
        ("optional suffix quantifier", 'on:\n  push:\n    paths:\n      - "scripts/a.py?"\n', 1),
        ("repeat char quantifier", 'on:\n  push:\n    paths:\n      - "scripts/a+.py"\n', 1),
        ("optional preceding char", 'on:\n  push:\n    paths:\n      - "scripts/aa?.py"\n', 1),
        ("globstar root zero", 'on:\n  push:\n    paths:\n      - "**/scripts/a.py"\n', 1),
        ("globstar nested zero", 'on:\n  push:\n    paths:\n      - "scripts/**/a.py"\n', 1),
        ("globstar double zero", 'on:\n  push:\n    paths:\n      - "**/scripts/**/a.py"\n', 1),
        ("globstar unrelated", 'on:\n  push:\n    paths:\n      - "**/docs/a.py"\n', 0),
        ("block push sequence", 'on:\n  - push\n', 1),
        ("block target sequence", 'on:\n  - pull_request_target\n', 1),
        ("block dispatch only", 'on:\n  - workflow_dispatch\n', 0),
        ("block aliased sequence", 'name: &trigger push\non:\n  - *trigger\n', 1),
        ("inline aliased sequence", 'name: &trigger push\non: [*trigger]\n', 1),
        ("inline dispatch list", 'on: [workflow_dispatch]\n', 0),
        ("root escaped on key", '"o\\u006e": push\n', 1),
        ("inline escaped event", 'on: "p\\u0075sh"\n', 1),
        ("inline escaped event array", 'on: ["p\\u0075sh"]\n', 1),
        ("nested escaped event key", 'on:\n  "p\\u0075sh":\n    paths:\n      - "docs/**"\n', 1),
        ("plain quoted unrelated root", '"name": workflow_dispatch\n', 0),
        ("one-space event map", 'on:\n push:\n  paths:\n   - "docs/**"\n', 1),
        ("four-space event map", 'on:\n    push:\n      paths:\n        - "docs/**"\n', 1),
        ("four-space quoted event map", 'on:\n    "pull_request":\n      paths:\n        - "docs/**"\n', 1),
        ("one-space event list", 'on:\n - push\n', 1),
        ("three-space event list", 'on:\n   - pull_request_target\n', 1),
        ("four-space dispatch only", 'on:\n    workflow_dispatch:\n', 0),
        ("nested paths list regression", 'on:\n  push:\n    branches: [so]\n    paths:\n      - "docs/**"\n', 0),
        ("plain escaped literal", 'on:\n  push:\n    paths:\n      - scripts/\\a.py\n', 1),
        ("plain escaped bracket", 'on:\n  push:\n    paths:\n      - scripts/\\[a].py\n', 1),

        ("unrelated", 'on:\n  push:\n    paths:\n      - "docs/**"\n', 0),
        ("dispatch only", 'on: workflow_dispatch\n', 0),
        ("spaced on key", 'on : push\n', 1),
        ("quoted spaced on key", '"on" : [push]\n', 1),
        ("indented on key", ' on:\n  push:\n    paths:\n      - "docs/**"\n', 1),
        ("blank unrelated", 'on:\n  push:\n    paths:\n      - "docs/**"\n\n', 0),
        ("blank then matching", 'on:\n  push:\n    paths:\n      - "docs/**"\n\n      - "scripts/a.py"\n', 1),
        ("target filtered", 'on:\n  pull_request_target:\n    paths:\n      - "scripts/a.py"\n', 1),
        ("target unrelated", 'on:\n  pull_request_target:\n    paths:\n      - "docs/**"\n', 0),
        ("target unfiltered", 'on:\n  pull_request_target:\n', 1),
    )
    # A generated fixture edit may replace rather than append a prior case.
    # Pin exact ordered labels, not only the total number of tests.
    if (len(cases) != 47 or hashlib.sha256(
            "\n".join(case[0] for case in cases).encode("utf-8")
    ).hexdigest() != "f0ebdf3ee0ca7048771168cbffaa5739655e452c07ee7bc92cec21f634c8b088"):
        raise RuntimeError("prewrite fanout CLI fixture identity drift")
    def require_exact_count(result: subprocess.CompletedProcess[str],
                            count: int, label: str) -> None:
        expected = "risk: BOUNDED_DIRECT_MATCH_ONLY; matched workflow count: " + str(count)
        if (result.returncode != 0 or result.stderr or
                expected not in result.stdout.splitlines()):
            raise RuntimeError("prewrite fanout CLI undercount/misclassification: "
                               + label + ": " + result.stderr)

    # A substring assertion could accept count 10 as proof of count 1.
    try:
        require_exact_count(
            subprocess.CompletedProcess([], 0,
                "risk: BOUNDED_DIRECT_MATCH_ONLY; matched workflow count: 10\n", ""),
            1, "prefix collision",
        )
    except RuntimeError:
        pass
    else:
        raise RuntimeError("prewrite fanout CLI count prefix collision accepted")
    with tempfile.TemporaryDirectory(prefix="learning-fanout-cli-") as tmp:
        root = Path(tmp)
        directory = root / ".github/workflows"
        directory.mkdir(parents=True)
        workflow = directory / "fixture.yml"
        for label, content, count in cases:
            workflow.write_text(content, encoding="utf-8")
            try:
                result = subprocess.run(
                    [sys.executable, str(guard), "--repo-root", str(root),
                     "--path", "scripts/a.py"],
                    capture_output=True, text=True, check=False, timeout=10,
                )
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError("prewrite fanout CLI timed out: " + label) from exc
            require_exact_count(result, count, label)
            if count == 1 and "- .github/workflows/fixture.yml" not in result.stdout.splitlines():
                raise RuntimeError("prewrite fanout CLI matched identity missing: " + label)
    # An actual writer-named workflow must block even with one direct match.
    with tempfile.TemporaryDirectory(prefix="learning-fanout-writer-cas-") as tmp:
        root = Path(tmp)
        directory = root / ".github/workflows"
        directory.mkdir(parents=True)
        (directory / "reconcile-metrics-scrape-status.yml").write_text(
            'on:\n  push:\n    paths:\n      - "scripts/a.py"\n', encoding="utf-8"
        )
        writer = subprocess.run(
            [sys.executable, str(guard), "--repo-root", str(root),
             "--path", "scripts/a.py"],
            capture_output=True, text=True, check=False, timeout=10,
        )
        if (writer.returncode != 2 or writer.stderr or
                "risk: BLOCKED_KNOWN_WRITER_CAS; matched workflow count: 1"
                not in writer.stdout.splitlines() or
                "- .github/workflows/reconcile-metrics-scrape-status.yml"
                not in writer.stdout.splitlines()):
            raise RuntimeError("prewrite writer CAS CLI negative failed")
    # Check a real known-risk path, including exact reported count versus
    # emitted workflow identities. The sample is diagnostic, not a trigger proof.
    import re
    try:
        risk = subprocess.run(
            [sys.executable, str(guard), "--repo-root", str(source_root),
             "--path", "scripts/validate-memory-os-rate-limit-operations-source-negative.py"],
            capture_output=True, text=True, check=False, timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("prewrite fanout known-risk CLI timed out") from exc
    lines = risk.stdout.splitlines()
    reports = [re.fullmatch(
        r"risk: BLOCKED_KNOWN_EXTERNAL_DEPENDENCY; matched workflow count: ([0-9]+)",
        line,
    ) for line in lines]
    counts = [int(match.group(1)) for match in reports if match is not None]
    workflows = [line[2:] for line in lines if line.startswith("- .github/workflows/")]
    if (risk.returncode != 2 or risk.stderr or len(counts) != 1 or
            counts[0] != len(workflows) or not workflows or
            ".github/workflows/reconcile-upload-route-authority.yml" not in workflows):
        raise RuntimeError("prewrite fanout known-risk CLI count/identity mismatch")
    # Audit the shared entrypoint on the real checked-out workflow tree.
    # Reconcile exact count, identity, risk and CLI exit status; never infer
    # a safe write from a partial connector/code-search workflow inventory.
    try:
        entry = subprocess.run(
            [sys.executable, str(guard), "--repo-root", str(source_root),
             "--path", "scripts/validate-memory-os-entry-docs.py"],
            capture_output=True, text=True, check=False, timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("prewrite entrypoint fanout CLI timed out") from exc
    entry_lines = entry.stdout.splitlines()
    entry_reports = [
        re.fullmatch(
            r"risk: (BOUNDED_DIRECT_MATCH_ONLY|BLOCKED_HIGH_FANOUT|BLOCKED_KNOWN_EXTERNAL_DEPENDENCY|BLOCKED_KNOWN_WRITER_CAS); matched workflow count: ([0-9]+)",
            line,
        ) for line in entry_lines
    ]
    entry_reports = [match for match in entry_reports if match is not None]
    entry_workflows = [line[2:] for line in entry_lines
                       if line.startswith("- .github/workflows/")]
    reviewed_entry_workflows = {
        ".github/workflows/autonomous-learning-guard.yml",
        ".github/workflows/diagnose-metrics-alerting.yml",
        ".github/workflows/operability-contracts.yml",
        ".github/workflows/rate-limit-operation-evidence.yml",
        ".github/workflows/reconcile-backup-restore.yml",
        ".github/workflows/reconcile-metrics-scrape-status-pr.yml",
        ".github/workflows/reconcile-metrics-scrape-status.yml",
        ".github/workflows/reconcile-observability-access.yml",
        ".github/workflows/reconcile-rate-limit-operations.yml",
    }
    if set(entry_workflows) != reviewed_entry_workflows:
        raise RuntimeError("prewrite entrypoint fanout reviewed identities changed")
    if (entry.stderr or len(entry_reports) != 1 or
            int(entry_reports[0].group(2)) != len(entry_workflows) or
            len(entry_workflows) != len(set(entry_workflows)) or
            entry_workflows != sorted(entry_workflows) or
            ".github/workflows/autonomous-learning-guard.yml" not in entry_workflows):
        raise RuntimeError("prewrite entrypoint fanout CLI count/identity mismatch")
    entry_risk = entry_reports[0].group(1)
    if ((entry_risk == "BOUNDED_DIRECT_MATCH_ONLY" and
         (entry.returncode != 0 or len(entry_workflows) > 12)) or
            (entry_risk == "BLOCKED_HIGH_FANOUT" and
             (entry.returncode != 2 or len(entry_workflows) <= 12)) or
            (entry_risk == "BLOCKED_KNOWN_EXTERNAL_DEPENDENCY" and
             (entry.returncode != 2 or not
              set(entry_workflows) & {
                  ".github/workflows/reconcile-upload-route-authority.yml",
                  ".github/workflows/reconcile-upload-route-authority-pr.yml",
              })) or
            (entry_risk == "BLOCKED_KNOWN_WRITER_CAS" and
             (entry.returncode != 2 or not
              set(entry_workflows) & {
                  ".github/workflows/diagnose-metrics-alerting.yml",
                  ".github/workflows/reconcile-metrics-scrape-status.yml",
              }))):
        raise RuntimeError("prewrite entrypoint fanout CLI risk/exit mismatch")
    # Preserve the single-line stdout contract required by the entrypoint verifier.
    with tempfile.TemporaryDirectory(prefix="learning-fanout-parent-alias-") as tmp:
        root = Path(tmp) / "repo"
        root.mkdir()
        external = Path(tmp) / "external"
        (external / "workflows").mkdir(parents=True)
        (external / "workflows" / "fixture.yml").write_text("on: push\n", encoding="utf-8")
        (root / ".github").symlink_to(external, target_is_directory=True)
        result = subprocess.run(
            [sys.executable, str(guard), "--repo-root", str(root),
             "--path", "scripts/a.py"],
            capture_output=True, text=True, check=False, timeout=10,
        )
        if (result.returncode != 1 or result.stdout or
                result.stderr != "PREWRITE TRIGGER AUDIT FAILED: workflow directory missing or symlinked\n"):
            raise RuntimeError("prewrite fanout CLI accepted symlinked workflow parent")
    for label, unsafe in (
        ("newline", "scripts/a\nb.py"),
        ("tab", "scripts/a\tb.py"),
        ("DEL", "scripts/a\x7fb.py"),
    ):
        result = subprocess.run(
            [sys.executable, str(guard), "--repo-root", str(source_root),
             "--path", unsafe],
            capture_output=True, text=True, check=False, timeout=10,
        )
        if (result.returncode != 1 or result.stdout or
                result.stderr != "PREWRITE TRIGGER AUDIT FAILED: prewrite path must be a safe repository-relative path\n"):
            raise RuntimeError("prewrite fanout CLI accepted control-character path: " + label)
    with tempfile.TemporaryDirectory(prefix="learning-fanout-source-bytes-") as tmp:
        root = Path(tmp)
        directory = root / ".github/workflows"
        directory.mkdir(parents=True)
        workflow = directory / "fixture.yml"
        for label, payload, diagnostic in (
            ("oversized", b"#" * (256 * 1024 + 1),
             "workflow source exceeds reviewed byte limit"),
            ("invalid UTF-8", b"\xff", "workflow source invalid UTF-8"),
        ):
            workflow.write_bytes(payload)
            result = subprocess.run(
                [sys.executable, str(guard), "--repo-root", str(root),
                 "--path", "scripts/a.py"],
                capture_output=True, text=True, check=False, timeout=10,
            )
            if (result.returncode != 1 or result.stdout or
                    result.stderr != "PREWRITE TRIGGER AUDIT FAILED: " + diagnostic + "\n"):
                raise RuntimeError("prewrite fanout CLI source-byte negative failed: " + label)
    return len(cases) + 8


def prove_prewrite_cli_end_to_end(source_root: Path) -> int:
    """Exercise the real prewrite CLI, not just its in-process validator."""
    baseline = ('def main() -> int:\n    return 0\n\n'
                'if __name__ == "__main__":\n    raise SystemExit(main())\n')
    candidate = baseline.replace('    return 0\n', '    # safe edit\n    return 0\n')
    with tempfile.TemporaryDirectory(prefix="learning-prewrite-cli-") as tmp:
        before = Path(tmp) / "before.py"
        after = Path(tmp) / "after.py"
        before.write_text(baseline, encoding="utf-8")
        after.write_text(candidate, encoding="utf-8")
        sha = hashlib.sha256(before.read_bytes()).hexdigest()
        args = [sys.executable, str(source_root / VALIDATOR),
                "--prewrite-baseline", str(before),
                "--prewrite-candidate", str(after),
                "--prewrite-baseline-sha256", sha]

        def execute(arguments: list[str]) -> subprocess.CompletedProcess[str]:
            try:
                return subprocess.run(arguments, capture_output=True, text=True,
                                      check=False, timeout=15)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError("prewrite CLI fixture timed out") from exc

        def accept(label: str, arguments: list[str], expected: str) -> None:
            result = execute(arguments)
            if (result.returncode != 1 or result.stdout or
                    result.stderr != "AUTONOMOUS LEARNING VALIDATION FAILED: " + expected + "\n"):
                raise RuntimeError(f"prewrite CLI negative misclassified: {label}: "
                                   f"exit={result.returncode} stderr={result.stderr!r}")

        positive = execute(args)
        if (positive.returncode != 0 or positive.stderr or
                positive.stdout != "Prewrite Python AST and diff-budget validation PASS: +1 -0\n"):
            raise RuntimeError("prewrite CLI positive control failed")
        # Real large entrypoint positive: check CLI parsing, full AST, and diff budget.
        actual = (source_root / CI_ENTRYPOINT).read_bytes()
        before.write_bytes(actual)
        after.write_bytes(actual + (b"" if actual.endswith(b"\n") else b"\n") +
                          b"# isolated prewrite CLI fixture\n")
        large_args = args[:-1] + [hashlib.sha256(actual).hexdigest()]
        large = execute(large_args)
        if (large.returncode != 0 or large.stderr or
                large.stdout != "Prewrite Python AST and diff-budget validation PASS: +1 -0\n"):
            raise RuntimeError("prewrite CLI real-entrypoint positive control failed")
        before.write_text(baseline, encoding="utf-8")
        cases = (
            ("invalid syntax", b"def main(:\n", "prewrite candidate Python syntax invalid", []),
            ("duplicate main", (baseline + "\ndef main():\n    pass\n").encode(),
             "prewrite candidate must have one sync main", []),
            ("unchanged", baseline.encode(), "prewrite candidate has no changes", []),
            ("invalid UTF-8", b"\xff", "prewrite input unreadable or invalid UTF-8", []),
            ("diff budget", candidate.replace("    # safe edit\n", "    # a\n    # b\n").encode(),
             "prewrite diff exceeds reviewed line budget", ["--max-added-lines", "1"]),
        )
        for label, payload, diagnostic, extra in cases:
            after.write_bytes(payload)
            accept(label, args + extra, diagnostic)
        after.write_text(candidate, encoding="utf-8")
        accept("stale baseline digest", args[:-1] + ["0" * 64],
               "prewrite baseline SHA-256 mismatch")
        after.unlink()
        after.symlink_to(before.name)
        accept("symlink", args, "prewrite input missing or symlinked")
        after.unlink()
        accept("missing candidate", args, "prewrite input missing or symlinked")
        after.write_text(candidate, encoding="utf-8")
        alias = Path(tmp) / "aliased-parent"
        alias.symlink_to(Path(tmp), target_is_directory=True)
        candidate_args = args.copy()
        candidate_args[5] = str(alias / after.name)
        accept("symlinked candidate parent", candidate_args, "prewrite input missing or symlinked")
        baseline_args = args.copy()
        baseline_args[3] = str(alias / before.name)
        accept("symlinked baseline parent", baseline_args, "prewrite input missing or symlinked")
        accept("incomplete CLI arguments", args[:4],
               "prewrite requires baseline, candidate and SHA-256")
    return len(cases) + 6


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    source_root = args.repo_root.resolve()

    negative_source = source_root / "scripts/validate-autonomous-learning-system-negative.py"
    if negative_source.is_symlink() or not negative_source.is_file():
        raise RuntimeError("unreviewed learning negative stdout source alias")
    require_reviewed_learning_negative_stdout(negative_source.read_text(encoding="utf-8"))
    prove_learning_negative_stdout_negatives()
    prove_failure_classifier()

    # A negative must reject for its own intended invariant, not merely for
    # an unrelated canonical failure elsewhere in the fixture.
    wrong_reason = subprocess.CompletedProcess(
        [], 1, "",
        "AUTONOMOUS LEARNING VALIDATION FAILED: unrelated injected failure\n",
    )
    try:
        require_expected_rejection("weaken mandatory rule", wrong_reason)
    except RuntimeError:
        pass
    else:
        raise RuntimeError("negative diagnostic classifier accepted an unrelated rejection")
    # The intended diagnostic on a second line (or accompanied by a second
    # error) must not be mistaken for a case-specific rejection.
    intended = "AUTONOMOUS LEARNING VALIDATION FAILED: " + expected_diagnostic("weaken mandatory rule")
    for index, stderr in enumerate((
        "AUTONOMOUS LEARNING VALIDATION FAILED: unrelated failure\n" + intended + "\n",
        intended + "\nunrelated additional failure\n",
    )):
        try:
            require_expected_rejection(
                "weaken mandatory rule", subprocess.CompletedProcess([], 1, "", stderr)
            )
        except RuntimeError:
            pass
        else:
            raise RuntimeError(f"negative diagnostic classifier accepted multiple errors: {index}")

    # A same-line suffix previously passed startswith(expected), making a
    # different diagnostic look like proof of the intended negative boundary.
    for label, name, suffix in (
        ("same-line suffix", "weaken mandatory rule", " injected"),
        ("same-line prefix collision", "weaken mandatory rule", "Extra"),
        ("anti-regression prefix collision", "drop anti-regression lesson", " changed"),
        ("fixed-colon diagnostic suffix", "drop CI guard timeout handling", " injected"),
    ):
        forged = "AUTONOMOUS LEARNING VALIDATION FAILED: " + expected_diagnostic(name) + suffix + "\n"
        try:
            require_expected_rejection(name, subprocess.CompletedProcess([], 1, "", forged))
        except RuntimeError:
            pass
        else:
            raise RuntimeError(f"negative diagnostic classifier accepted {label}")

    # A fixed diagnostic may itself end with a colon; it must still match exactly.
    require_expected_rejection(
        "drop CI guard timeout handling",
        subprocess.CompletedProcess([], 1, "",
            "AUTONOMOUS LEARNING VALIDATION FAILED: "
            + expected_diagnostic("drop CI guard timeout handling") + "\n"),
    )

    # Canonical variable-detail diagnostics still require a nonempty detail.
    require_expected_rejection(
        "invalid contract JSON",
        subprocess.CompletedProcess([], 1, "",
            "AUTONOMOUS LEARNING VALIDATION FAILED: invalid JSON: fixture: malformed JSON\n"),
    )
    for malformed in ("", " "):
        try:
            require_expected_rejection(
                "invalid contract JSON",
                subprocess.CompletedProcess([], 1, "",
                    "AUTONOMOUS LEARNING VALIDATION FAILED: invalid JSON:" + malformed + "\n"),
            )
        except RuntimeError:
            pass
        else:
            raise RuntimeError("negative diagnostic classifier accepted empty variable detail")

    require_expected_rejection(
        "weaken mandatory rule",
        subprocess.CompletedProcess(
            [], 1, "",
            "AUTONOMOUS LEARNING VALIDATION FAILED: "
            "mandatory learning rule must remain true: unchangedBlockerIsNotRetried\n",
        ),
    )

    with tempfile.TemporaryDirectory(prefix="learning-positive-") as tmp:
        root = Path(tmp)
        seed(source_root, root)
        result = run(source_root, root)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            return 1

    # Generator bodies are deferred and comprehension targets are local.
    # Prove the eager-effects guard does not reject these safe controls.
    for label, snippet in (
        ("deferred generator body", "(globals().__setitem__('main', None) for _ in (0,))\n"),
        ("comprehension-local target", "[0 for main in (0,)]\n"),
        ("deferred lambda body", "(lambda: globals().__setitem__('main', None))\n"),
    ):
        with tempfile.TemporaryDirectory(prefix="learning-comprehension-positive-") as tmp:
            root = Path(tmp)
            seed(source_root, root)
            module_guard = 'if __name__ == "__main__":' + chr(10) + "    raise SystemExit(main())" + chr(10)
            replace_in_entrypoint(root, module_guard, snippet + module_guard)
            result = run(source_root, root)
            if result.returncode != 0:
                raise RuntimeError(
                    f"learning eager-expression positive control rejected {label}: {result.stderr}"
                )

    # A no-op mutation must be rejected before running the canonical guard;
    # otherwise a broken positive fixture could masquerade as negative proof.
    try:
        require_failure(source_root, "weaken mandatory rule", lambda root: None)
    except RuntimeError as exc:
        if "negative fixture did not mutate canonical authority" not in str(exc):
            raise
    else:
        raise RuntimeError("negative mutation fingerprint accepted a no-op")

    cases = [
        ("invalid contract JSON", lambda root: (root / CONTRACT).write_text("{", encoding="utf-8")),
        ("duplicate contract JSON key", lambda root: (root / CONTRACT).write_text(
            '{"schemaVersion":"a","schemaVersion":"b"}', encoding="utf-8")),
        ("nested duplicate contract JSON key", lambda root: (root / CONTRACT).write_text(
            '{"rules":{"ciReachabilityRequired":true,"ciReachabilityRequired":false}}', encoding="utf-8")),
        ("nonfinite contract JSON", lambda root: (root / CONTRACT).write_text(
            '{"value":NaN}', encoding="utf-8")),
        ("overflow float contract JSON", lambda root: (root / CONTRACT).write_text(
            '{"value":1e9999}', encoding="utf-8")),
        ("huge integer contract JSON", lambda root: (root / CONTRACT).write_text(
            '{"value":' + "9" * 129 + '}', encoding="utf-8")),
        ("invalid UTF8 contract JSON", lambda root: (root / CONTRACT).write_bytes(
            bytes([255]))),
        ("oversized contract JSON", lambda root: (root / CONTRACT).write_bytes(
            b" " * (1024 * 1024 + 1))),
        ("non-object contract root", lambda root: (root / CONTRACT).write_text("[]", encoding="utf-8")),
        ("weaken mandatory rule", lambda root: edit_contract(root, lambda d: d["rules"].__setitem__("unchangedBlockerIsNotRetried", False))),
        ("disable required CI reachability", lambda root: edit_contract(root, lambda d: d["rules"].__setitem__("ciReachabilityRequired", False))),
        ("weaken NO_GO default", lambda root: edit_contract(root, lambda d: d["protectedInvariants"].__setitem__("productionDecisionDefault", "GO"))),
        ("allow non-real OPS-P0-007 evidence", lambda root: edit_contract(root, lambda d: d["protectedInvariants"].__setitem__("opsP0007EvidenceMustBeReal", False))),
        ("merge human promotion review into automation", lambda root: edit_contract(root, lambda d: d["protectedInvariants"].__setitem__("humanPromotionReviewIsSeparate", False))),
        ("drop required failure retry condition", lambda root: edit_contract(root, lambda d: d["requiredFailureFields"].remove("retryCondition"))),
        ("drop required success authority check", lambda root: edit_contract(root, lambda d: d["requiredSuccessFields"].remove("protectedAuthorityCheck"))),
        ("break executable guard binding", lambda root: edit_contract(root, lambda d: d.__setitem__("validator", "scripts/other.py"))),
        ("break negative guard binding", lambda root: edit_contract(root, lambda d: d.__setitem__("negativeValidator", "scripts/other-negative.py"))),
        ("break CI entrypoint binding", lambda root: edit_contract(root, lambda d: d.__setitem__("ciEntrypoint", "scripts/other-entrypoint.py"))),
        ("break learning authority binding", lambda root: edit_contract(root, lambda d: d.__setitem__("authority", "docs/operations/other-learning.md"))),
        ("duplicate required failure field", lambda root: edit_contract(root, lambda d: d["requiredFailureFields"].append("symptom"))),
        ("duplicate required success field", lambda root: edit_contract(root, lambda d: d["requiredSuccessFields"].append("outcome"))),
        ("remove learning authority", lambda root: (root / LEARNING).unlink()),
        ("remove executable guard", lambda root: (root / VALIDATOR).unlink()),
        ("remove negative guard", lambda root: (root / NEGATIVE_VALIDATOR).unlink()),
        ("remove CI entrypoint", lambda root: (root / CI_ENTRYPOINT).unlink()),
        ("disconnect positive guard from CI entrypoint", lambda root: drop_from_entrypoint(root, VALIDATOR.as_posix())),
        ("disconnect negative guard from CI entrypoint", lambda root: drop_from_entrypoint(root, NEGATIVE_VALIDATOR.as_posix())),
        ("remove CI guard execution call", lambda root: replace_in_entrypoint(root, "    validate_learning_guards(failures)\n", "    # learning guard execution removed\n")),
        ("remove source-negative CI guard call", lambda root: replace_in_entrypoint(
            root, "    validate_source_negative_ci_reachability(failures)\n",
            "    # source-negative CI guard removed\n",
        )),
        ("quote source-negative CI guard call", lambda root: replace_in_entrypoint(
            root, "    validate_source_negative_ci_reachability(failures)\n",
            '    "validate_source_negative_ci_reachability(failures)"\n',
        )),
        ("shadow source-negative CI guard", lambda root: replace_in_entrypoint(
            root, "def main() -> int:\n",
            "validate_source_negative_ci_reachability = lambda failures: None\n\ndef main() -> int:\n",
        )),
        ("remove source-negative CI negative proof", lambda root: replace_in_entrypoint(
            root, "    prove_source_negative_reachability_negatives(failures)\n",
            "    pass\n",
        )),
        ("unreachable source-negative CI guard call", lambda root: replace_in_entrypoint(
            root, "    validate_source_negative_ci_reachability(failures)\n",
            "    return 0\n    validate_source_negative_ci_reachability(failures)\n",
        )),
        ("drop CI repo-root guard interface", lambda root: replace_in_entrypoint(root, '[sys.executable, str(path), "--repo-root", str(REPO_ROOT)]', '[sys.executable, str(path)]')),
        ("drop CI guard timeout authority", lambda root: replace_in_entrypoint(root, "LEARNING_GUARD_TIMEOUT_SECONDS = 120", "LEARNING_GUARD_TIMEOUT_SECONDS = None")),
        ("drop CI guard timeout binding", lambda root: replace_in_entrypoint(root, "                timeout=LEARNING_GUARD_TIMEOUT_SECONDS,\n", "")),
        ("drop CI guard timeout handling", lambda root: replace_in_entrypoint(root, "        except subprocess.TimeoutExpired:\n", "        except RuntimeError:\n")),
        ("drop anti-regression lesson", lambda root: (root / LEARNING).write_text((root / LEARNING).read_text(encoding="utf-8").replace("Repeating a known failed approach without changed preconditions is a regression", "known failures may be retried"), encoding="utf-8")),
    ]
    # Exercise every mandatory contract rule independently. A positive
    # validator check without its own mutation proof is not negative coverage.
    for rule in (
        "searchBeforeChange",
        "sameFailedApproachRequiresChangedPrecondition",
        "preferExecutableGuard",
        "verifyProtectedAuthorityAfterChange",
        "scopedBlockerDoesNotStopIndependentWork",
        "historyIsAppendOnly",
        "learningIsNeverProductionEvidence",
        "learningCannotPromoteReadiness",
    ):
        cases.append((
            f"disable mandatory {rule}",
            lambda root, key=rule: edit_contract(
                root, lambda data: data["rules"].__setitem__(key, False)
            ),
        ))
    cases.extend((
        ("downgrade schema version", lambda root: edit_contract(
            root, lambda data: data.__setitem__("schemaVersion", "autonomous-learning-system.0.0")
        )),
        ("reorder closed-loop execution", lambda root: edit_contract(
            root, lambda data: data["loop"].reverse()
        )),
    ))
    # Field completeness is contractual: each required failure/success field
    # must have its own isolated missing-field negative, not just one example.
    for field in (
        "symptom", "evidence", "rootCauseOrUnknown",
        "failedApproach", "correction", "recurrenceGuard",
    ):
        cases.append((
            f"drop required failure {field}",
            lambda root, key=field: edit_contract(
                root, lambda data: data["requiredFailureFields"].remove(key)
            ),
        ))
    for field in ("outcome", "evidence", "whySafe", "reusableMechanism"):
        cases.append((
            f"drop required success {field}",
            lambda root, key=field: edit_contract(
                root, lambda data: data["requiredSuccessFields"].remove(key)
            ),
        ))
    # A textual invocation fragment in a comment, literal, or dead branch
    # must not satisfy the live CI call-site binding.
    cases.extend((
        ("comment-only learning guard call", lambda root: replace_in_entrypoint(
            root, "    validate_learning_guards(failures)\n",
            "    # validate_learning_guards(failures)\n",
        )),
        ("quoted learning guard call", lambda root: replace_in_entrypoint(
            root, "    validate_learning_guards(failures)\n",
            '    "validate_learning_guards(failures)"\n',
        )),
        ("dead-branch learning guard call", lambda root: replace_in_entrypoint(
            root, "    validate_learning_guards(failures)\n",
            "    if False:\n        validate_learning_guards(failures)\n",
        )),
        ("unreachable learning guard after return", lambda root: replace_in_entrypoint(
            root, "    validate_learning_guards(failures)\n",
            "    return 0\n    validate_learning_guards(failures)\n",
        )),
        ("unreachable learning guard after raise", lambda root: replace_in_entrypoint(
            root, "    validate_learning_guards(failures)\n",
            "    raise RuntimeError('unreachable')\n    validate_learning_guards(failures)\n",
        )),
    ))
    cases.extend((
        ("async-only learning guard", lambda root: replace_in_entrypoint(
            root, "def validate_learning_guards(failures: list[str]) -> None:",
            "async def validate_learning_guards(failures: list[str]) -> None:",
        )),
        ("async learning guard shadow", lambda root: replace_in_entrypoint(
            root, "def main() -> int:\n",
            "async def validate_learning_guards(failures):\n    return None\n\ndef main() -> int:\n",
        )),
        ("destructured learning guard shadow", lambda root: replace_in_entrypoint(
            root, "def main() -> int:\n",
            "validate_learning_guards, = (lambda failures: None,)\n\ndef main() -> int:\n",
        )),
        ("imported learning guard shadow", lambda root: replace_in_entrypoint(
            root, "def main() -> int:\n",
            "from unittest.mock import Mock as validate_learning_guards\n\ndef main() -> int:\n",
        )),
        ("assigned learning guard shadow", lambda root: replace_in_entrypoint(
            root, "def main() -> int:\n",
            "validate_learning_guards = lambda failures: None\n\ndef main() -> int:\n",
        )),
        ("async main shadow", lambda root: replace_in_entrypoint(
            root, 'if __name__ == "__main__":\n    raise SystemExit(main())\n',
            'async def main():\n    return 0\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n',
        )),
        ("loop main shadow", lambda root: replace_in_entrypoint(
            root, 'if __name__ == "__main__":\n    raise SystemExit(main())\n',
            'for main in (lambda: 0,):\n    pass\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n',
        )),
        ("loop learning guard shadow", lambda root: replace_in_entrypoint(
            root, "def main() -> int:\n",
            "for validate_learning_guards in (lambda failures: None,):\n    pass\n\ndef main() -> int:\n",
        )),
        ("nested imported learning guard shadow", lambda root: replace_in_entrypoint(
            root, "def main() -> int:\n",
            "if True:\n    from unittest.mock import Mock as validate_learning_guards\n\ndef main() -> int:\n",
        )),
        ("destructured main shadow", lambda root: replace_in_entrypoint(
            root, 'if __name__ == "__main__":\n    raise SystemExit(main())\n',
            'main, = (lambda: 0,)\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n',
        )),
        ("imported main shadow", lambda root: replace_in_entrypoint(
            root, 'if __name__ == "__main__":\n    raise SystemExit(main())\n',
            'from unittest.mock import Mock as main\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n',
        )),
        ("assigned main shadow", lambda root: replace_in_entrypoint(
            root, 'if __name__ == "__main__":\n    raise SystemExit(main())\n',
            'main = lambda: 0\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n',
        )),
        ("dead module main guard", lambda root: replace_in_entrypoint(
            root, 'if __name__ == "__main__":\n    raise SystemExit(main())\n',
            "if False:\n    raise SystemExit(main())\n",
        )),
        ("comment-only module main invocation", lambda root: replace_in_entrypoint(
            root, 'if __name__ == "__main__":\n    raise SystemExit(main())\n',
            'if __name__ == "__main__":\n    pass  # raise SystemExit(main())\n',
        )),
    ))
    # A canonical module guard is not execution proof if module startup
    # terminates before the guarded main() call. Every mutation retains the
    # canonical guard text and AST so only reachability can reject it.
    module_guard = 'if __name__ == "__main__":' + chr(10) + "    raise SystemExit(main())" + chr(10)
    for label, prefix in (
        ("sys-exit", "sys.exit(0)" + chr(10) + chr(10)),
        ("raise", "raise SystemExit(0)" + chr(10) + chr(10)),
        ("nested-sys-exit", "if True:" + chr(10) + "    sys.exit(0)" + chr(10) + chr(10)),
        ("eager-default", "def eager(value=sys.exit(0)):" + chr(10)
         + "    pass" + chr(10) + chr(10)),
    ):
        cases.append((
            f"module early {label}",
            lambda root, injected=prefix: replace_in_entrypoint(
                root, module_guard, injected + module_guard
            ),
        ))
    # The guard must remain reachable through nested branches, eager
    # definitions and termination calls, not just direct Return/Raise nodes.
    newline = chr(10)
    guard_call = "    validate_learning_guards(failures)" + newline
    for label, prefix in (
        ("if-return", "    if True:" + newline + "        return 0" + newline),
        ("if-raise", "    if True:" + newline + "        raise SystemExit(0)" + newline),
        ("sys-exit", "    sys.exit(0)" + newline),
        ("os-exit", "    os._exit(0)" + newline),
        ("exit", "    exit(0)" + newline),
        ("quit", "    quit()" + newline),
        ("dead-return", "    if False:" + newline + "        return 0" + newline),
        ("try-return", "    try:" + newline + "        return 0" + newline
         + "    finally:" + newline + "        pass" + newline),
        ("exec-exit", "    exec('sys.exit(0)')" + newline),
        ("eager-default", "    def helper(value=exit(0)):" + newline
         + "        pass" + newline),
        ("eager-class", "    class Early:" + newline + "        sys.exit(0)" + newline),
    ):
        cases.append((
            f"early learning guard {label}",
            lambda root, injected=prefix, before=guard_call: replace_in_entrypoint(
                root, before, injected + before
            ),
        ))
    # Dynamic module namespace mutation must not replace a verified guard
    # after the AST sees its original function definition.
    for label, symbol, anchor in (
        ("main", "main",
         'if __name__ == "__main__":' + chr(10) + "    raise SystemExit(main())" + chr(10)),
        ("learning guard", "validate_learning_guards", "def main() -> int:" + chr(10)),
    ):
        for kind, mutation in (
            ("globals-subscript", f"globals()['{symbol}'] = None"),
            ("globals-keyword", f"globals().update({symbol}=None)"),
            ("globals-dict", f"globals().update({{'{symbol}': None}})"),
            ("setattr", f"setattr(sys.modules[__name__], '{symbol}', None)"),
            ("exec", f"exec('{symbol} = None')"),
            # Class bodies, function defaults and decorators execute eagerly.
            # Their module-namespace side effects must not bypass a live call.
            ("class-body", f"class Eager:\n    globals()['{symbol}'] = None"),
            ("class-global", f"class Eager:\n    global {symbol}\n    {symbol} = None"),
            ("function-default", f"def eager(value=globals().__setitem__('{symbol}', None)):\n    pass"),
            ("function-decorator", f"@lambda fn: (globals().__setitem__('{symbol}', None), fn)[1]\ndef eager():\n    pass"),
            ("class-base", f"class Eager(globals().__setitem__('{symbol}', None) or object):\n    pass"),
            ("class-decorator", f"@lambda cls: (globals().__setitem__('{symbol}', None), cls)[1]\nclass Eager:\n    pass"),
            # Eager comprehension effects and the first generator iterable
            # run before the canonical main() dispatch.
            ("list-comprehension", f"[globals().__setitem__('{symbol}', None) for _ in (0,)]"),
            ("set-comprehension", f"{{globals().__setitem__('{symbol}', None) for _ in (0,)}}"),
            ("dict-comprehension", f"{{_: globals().__setitem__('{symbol}', None) for _ in (0,)}}"),
            ("generator-iterable", f"(None for _ in (globals().__setitem__('{symbol}', None) or (0,)))"),
            ("immediate-lambda", f"(lambda: globals().__setitem__('{symbol}', None))()"),
            ("lambda-in-comprehension", f"[(lambda: globals().__setitem__('{symbol}', None))() for _ in (0,)]"),
        ):
            cases.append((
                f"dynamic {label} {kind}",
                lambda root, before=anchor, injected=mutation: replace_in_entrypoint(
                    root, before, injected + chr(10) + before
                ),
            ))
    for label, relative in (
        ("contract", CONTRACT),
        ("learning history", LEARNING),
        ("positive guard", VALIDATOR),
        ("negative guard", NEGATIVE_VALIDATOR),
        ("CI entrypoint", CI_ENTRYPOINT),
    ):
        cases.append((
            f"symlinked {label} authority",
            lambda root, path=relative: symlink_authority(root, path),
        ))
    for label, relative in (
        ("scripts", Path("scripts")),
        ("contracts operations", Path("contracts/operations")),
        ("docs operations", Path("docs/operations")),
    ):
        cases.append((
            f"symlinked {label} parent directory",
            lambda root, path=relative: symlink_parent_directory(root, path),
        ))
    for name, mutate in cases:
        require_failure(source_root, name, mutate)

    prove_upload_route_go_import_parser()
    prove_upload_route_go_direct_inputs(source_root)
    fanout_cli_cases = prove_prewrite_fanout_cli(source_root)
    prewrite_cli_cases = prove_prewrite_cli_end_to_end(source_root)
    print(f"Autonomous learning negative validation PASS ({len(cases) + prewrite_cli_cases + fanout_cli_cases} fail-closed cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
