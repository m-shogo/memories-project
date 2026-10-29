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


def upload_route_local_go_imports(source: str) -> set[str]:
    """Parse reviewed Go import forms conservatively; reject unknown syntax."""
    import re
    module = "github.com/m-shogo/memories-project/services/import-api/"
    blocks = list(re.finditer(r"(?m)^[ \t]*import[ \t]*\(([\s\S]*?)^[ \t]*\)", source))
    paths = []
    for block in blocks:
        for line in block.group(1).splitlines():
            if not line.strip() or line.lstrip().startswith("//"):
                continue
            match = re.fullmatch(r'\s*(?:[A-Za-z_.]\w*\s+)?"([^"]+)"\s*(?://.*)?', line)
            if match is None:
                raise RuntimeError("unreviewed Go import block entry")
            paths.append(match.group(1))
    for block in reversed(blocks):
        source = source[:block.start()] + source[block.end():]
    for line in source.splitlines():
        if re.match(r"^[ \t]*import\b", line):
            match = re.fullmatch(r'[ \t]*import[ \t]+(?:[A-Za-z_.]\w*[ \t]+)?"([^"]+)"[ \t]*(?://.*)?', line)
            if match is None:
                raise RuntimeError("unreviewed single-line Go import")
            paths.append(match.group(1))
    return {path[len(module):] for path in paths if path.startswith(module)}


def prove_upload_route_go_import_parser() -> None:
    module = "github.com/m-shogo/memories-project/services/import-api/"
    sample = 'package test\nimport (\n  "fmt"\n  alias "' + module + 'internal/metrics"\n)\n'
    if upload_route_local_go_imports(sample) != {"internal/metrics"}:
        raise RuntimeError("Go import block positive fixture failed")
    if upload_route_local_go_imports('import "' + module + 'internal/reqid"\n') != {"internal/reqid"}:
        raise RuntimeError("Go single-line import positive fixture failed")
    try:
        upload_route_local_go_imports('import (\n  not_a_go_import\n)\n')
    except RuntimeError:
        pass
    else:
        raise RuntimeError("Go import parser accepted invalid import fixture")


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
        if any(module in {"importlib", "subprocess"} for module in modules):
            raise RuntimeError("unreviewed Upload Route Python dynamic dependency")
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in {"__import__", "eval", "exec"}):
            raise RuntimeError("unreviewed Upload Route Python dynamic dependency")
    literals = set(re.findall(r"""["']((?:contracts|docs|scripts|services)/[^"'\s]+)["']""", source))
    require_reviewed_upload_route_input_set(literals, count, expected_sha256)


def prove_upload_route_python_source_negatives() -> None:
    base = 'from pathlib import Path\nX = "contracts/operations/a.json"\n'
    digest = hashlib.sha256(b"contracts/operations/a.json\n").hexdigest()
    require_reviewed_upload_route_python_source(base, 1, digest)
    for label, candidate in (
        ("same-count literal swap", base.replace("a.json", "b.json")),
        ("added path literal", base + 'Y = "docs/b.md"\n'),
        ("dynamic import", base + "import importlib\n"),
        ("subprocess import", base + "from subprocess import run\n"),
        ("builtin loader", base + 'Y = __import__("os")\n'),
        ("builtin eval", base + 'Y = eval("1")\n'),
    ):
        try:
            require_reviewed_upload_route_python_source(candidate, 1, digest)
        except RuntimeError as exc:
            if str(exc) not in {
                "unreviewed Upload Route Python dynamic dependency",
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


def prove_upload_route_go_direct_inputs(source_root: Path) -> None:
    """Report a compile-input lower bound; never claim transitive trigger closure."""
    import re
    require_reviewed_go_workspace(source_root)
    prove_upload_route_go_workspace_negatives()
    prove_unaliased_go_path_negatives()
    prove_go_embed_negatives()
    prove_upload_route_path_parity_negatives()
    prove_upload_route_input_set_negatives()
    prove_upload_route_python_source_negatives()
    prove_upload_route_event_sequence_negatives()
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
    target = source_root / "services/import-api/internal/httpserver"
    require_unaliased_go_path(source_root, target)
    native_suffixes = {".c", ".h", ".s", ".cc", ".cpp", ".syso", ".swig", ".swigcxx"}
    def reject_native(directory: Path) -> None:
        if any(p.suffix.lower() in native_suffixes for p in directory.iterdir()):
            raise RuntimeError("unreviewed Go native build input: " + str(directory))
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
    for file in go_files:
        require_unaliased_go_path(source_root, file)
        source = file.read_text(encoding="utf-8")
        reject_unreviewed_go_embeds(source)
        if 'import "C"' in source:
            raise RuntimeError("unreviewed Go CGo import")
        packages.update(upload_route_local_go_imports(source))
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
            reject_unreviewed_go_embeds(source)
            if 'import "C"' in source:
                raise RuntimeError("unreviewed Go CGo import")
            for dependency in upload_route_local_go_imports(source):
                if dependency not in visited:
                    pending.append(dependency)
                    packages.add(dependency)
        if len(inputs) > 512:
            raise RuntimeError("Go local import closure exceeds reviewed file budget")
    if len(visited) < 22:
        raise RuntimeError("reviewed transitive Go package missing from closure")
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
        if not (source_root / path).is_file():
            raise RuntimeError("missing direct Python validator input: " + path)
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
        if not (source_root / path).is_file():
            raise RuntimeError("missing direct operability validator input: " + path)
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
    uncovered_sets = []
    reviewed_paths = []
    for workflow, event in (
        ("reconcile-upload-route-authority.yml", "push"),
        ("reconcile-upload-route-authority-pr.yml", "pull_request"),
    ):
        source = (source_root / ".github/workflows" / workflow).read_text(encoding="utf-8")
        patterns = upload_route_event_paths(source, event)
        reviewed_paths.append(patterns)
        uncovered_sets.append({path for path in inputs
                               if not any(matches(path, pat) for pat in patterns)})
    require_upload_route_event_path_parity(*reviewed_paths)
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
    prewrite_cli_cases = prove_prewrite_cli_end_to_end(source_root)
    print(f"Autonomous learning negative validation PASS ({len(cases) + prewrite_cli_cases} fail-closed cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
