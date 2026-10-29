#!/usr/bin/env python3
"""Conservative read-only pre-write workflow trigger blast-radius audit.

This is an over-approximation of direct push/PR path matching, NOT an
authorization to write or proof of transitive workflow-call reachability.
A risky result must block autonomous unreviewed writes until scoped.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import re
import sys
import tempfile
from pathlib import Path

MAX_REVIEWED_DIRECT_FANOUT = 12
MAX_WORKFLOW_SOURCE_BYTES = 256 * 1024
KNOWN_EXTERNAL_BLOCKED_WORKFLOWS = {
    ".github/workflows/reconcile-upload-route-authority.yml",
    ".github/workflows/reconcile-upload-route-authority-pr.yml",
}
# These publisher workflows have reviewed contents:write and source-SHA CAS
# commit/push paths. Even a bounded fanout can invalidate a running writer.
KNOWN_WRITER_CAS_WORKFLOWS = {
    ".github/workflows/diagnose-metrics-alerting.yml",
    ".github/workflows/rate-limit-operation-evidence.yml",
    ".github/workflows/reconcile-backup-restore.yml",
    ".github/workflows/reconcile-metrics-scrape-status.yml",
    ".github/workflows/reconcile-observability-access.yml",
    ".github/workflows/reconcile-rate-limit-operations.yml",
}


class AuditFailure(RuntimeError):
    pass


def conservative_glob_match(relative: str, pattern: str) -> bool:
    """Over-approximate GitHub **/ including zero intervening directories."""
    if fnmatch.fnmatchcase(relative, pattern):
        return True
    if "**/" not in pattern:
        return False
    chunks = pattern.split("**/")
    if len(chunks) > 5:
        return True  # Bounded expansion: unreviewed complexity is risky.
    candidates = {chunks[0]}
    for chunk in chunks[1:]:
        candidates = {
            prefix + separator + chunk
            for prefix in candidates
            for separator in ("", "**/")
        }
    return any(fnmatch.fnmatchcase(relative, candidate) for candidate in candidates)


def workflow_matches_path(source: str, relative: str) -> bool:
    """Conservatively match direct push/PR events; ambiguous filters are risky."""
    # UTF-8 BOM is legal at the beginning of a YAML stream. Preserve its
    # semantics instead of silently missing the first root-level "on" key.
    if source.startswith("\ufeff"):
        source = source[1:]
    # A second BOM is not a reviewed event-filter spelling: fail closed.
    if "\ufeff" in source:
        return True
    # YAML double-quoted mapping keys can decode \u escapes into "on".
    # Unknown escaped root keys are not proof of a dispatch-only workflow.
    if re.search(r'(?m)^"[^"\r\n]*\\[^"\r\n]*"[ \t]*:', source):
        return True
    # GitHub accepts quoted YAML event keys and inline scalar/map triggers.
    # Missing these forms would undercount prewrite fanout, not just overestimate.
    source = re.sub(r"""(?m)^(['"])on\1:""", "on:", source)
    source = re.sub(r"""(?m)^  (['"])(push|pull_request_target|pull_request)\1:""", r"  \2:", source)
    # YAML accepts whitespace before a mapping colon and indentation of
    # root keys. The strict direct-filter parser below does not model these
    # spellings, so treat them as potentially unfiltered rather than miss
    # a push/PR trigger (including quoted variants).
    if (re.search(r"""(?m)^[ \t]*(?:on|['"]on['"])[ \t]+:""", source) or
            re.search(r"""(?m)^[ \t]+(?:on|['"]on['"]):""", source)):
        return True
    # Duplicate YAML mappings and unresolved event aliases can replace a
    # reviewed path filter. Treat ambiguity as potentially unfiltered.
    if len(re.findall(r"(?m)^on:", source)) > 1:
        return True
    if re.search(r"(?m)^on:[ \t]*[&*|>!]", source):
        return True
    if any(len(re.findall(r"(?m)^  " + event + ":", source)) > 1
           for event in ("push", "pull_request_target", "pull_request")):
        return True
    inline = re.search(r"(?m)^on:[ \t]*([^\r\n]+)", source)
    # YAML double-quoted values may decode an escaped event name.
    if inline and "\\" in inline.group(1):
        return True
    # GitHub Actions supports YAML aliases; an inline sequence may expand to
    # a push/PR event without spelling that event in the on: value.
    if inline and re.search(r"\*[A-Za-z_][A-Za-z0-9_-]*", inline.group(1)):
        return True
    if inline and re.search(r"\b(?:push|pull_request_target|pull_request)\b", inline.group(1)):
        return True
    if re.search(r"(?m)^on:\s*\[[^\]]*\b(?:push|pull_request_target|pull_request)\b", source):
        return True
    section = re.search(
        r"(?ms)^on:\s*\n(.*?)(?=^[A-Za-z_][\w-]*:|\Z)", source
    )
    if section is None:
        return bool(re.search(r"(?m)^  (?:push|pull_request_target|pull_request):", source))
    block = section.group(1)
    # An escaped quoted mapping key may decode to push/pull_request.
    if re.search(r'(?m)^  "[^"\r\n]*\\[^"\r\n]*"[ \t]*:', block):
        return True
    # Block YAML sequences are equivalent to inline event arrays. Treat
    # aliases or unreviewed entries as potentially unfiltered push/PR.
    live_rows = [
        row for row in block.splitlines()
        if row.strip() and not row.lstrip().startswith("#")
    ]
    if any(row.startswith("  - ") for row in live_rows):
        if any(not row.startswith("  - ") for row in live_rows):
            return True
        return any(row[4:].strip() != "workflow_dispatch" for row in live_rows)
    for event in ("push", "pull_request_target", "pull_request"):
        match = re.search(
            r"(?ms)^  " + event + r":\s*\n(.*?)(?=^  [A-Za-z_][\w-]*:|\Z)",
            block,
        )
        if match is None:
            if re.search(r"(?m)^  " + event + r":", block):
                return True
            continue
        event_body = match.group(1)
        if "    paths-ignore:" in event_body or "    paths:" not in event_body:
            return True
        if len(re.findall(r"""(?m)^    (?:paths|['"]paths['"]):""", event_body)) > 1:
            return True
        # DOTALL .* can consume blank lines after the list. Do not treat
        # those blank lines as an empty path or silently stop before a later
        # path entry. Scan the complete bounded event tail instead.
        path_rows = event_body.splitlines()
        if path_rows.count("    paths:") != 1:
            return True
        entries = []
        for row in path_rows[path_rows.index("    paths:") + 1:]:
            if not row.strip() or row.lstrip().startswith("#"):
                continue
            if not row.startswith("      - "):
                return True  # Unreviewed trailing event mapping.
            entries.append(row)
        if not entries:
            return True
        for row in entries:
            raw = row[len("      - "):].strip()
            if raw.startswith(("'", '"')):
                quote = raw[0]
                quoted = re.fullmatch(
                    re.escape(quote) + r"([^" + re.escape(quote) + r"]*)"
                    + re.escape(quote) + r"(?:[ \t]+#.*)?", raw
                )
                if quoted is None:
                    return True
                pattern = quoted.group(1)
                if "\\" in pattern:
                    return True  # YAML escapes may change the actual pattern.
            else:
                pattern = re.split(r"[ \t]+#", raw, maxsplit=1)[0].strip()
                if pattern.startswith(("*", "&", "|", ">")):
                    return True  # Unquoted YAML alias/scalar ambiguity.
            if not pattern:
                return True
            # Plain YAML scalars preserve backslashes, while GitHub minimatch
            # may interpret them as escapes. fnmatch would undercount.
            if "\\" in pattern:
                return True
            # GitHub Actions treats ? and + as quantifiers on the preceding
            # character, unlike Python fnmatch's ? wildcard and literal +.
            # Do not claim a non-match without a compatible minimatch engine.
            if "?" in pattern or "+" in pattern:
                return True
            # GitHub minimatch supports constructs fnmatch does not; never
            # mistake unsupported grammar for a proven non-match.
            if any(char in pattern for char in "{}") or re.search(r"[@+?!]\(", pattern):
                return True
            if pattern.startswith("!"):
                # Ignoring ordinary exclusions overestimates direct fanout.
                continue
            if conservative_glob_match(relative, pattern):
                return True
    return False


def validate_relative_path(relative: str) -> None:
    if (not relative or relative.startswith("/") or "\\" in relative
            or any(part in ("", ".", "..") for part in relative.split("/"))
            or any(ord(char) < 32 or 127 <= ord(char) < 160 for char in relative)):
        raise AuditFailure("prewrite path must be a safe repository-relative path")


def matching_workflows(repo_root: Path, relative: str) -> list[str]:
    validate_relative_path(relative)
    directory = repo_root / ".github/workflows"
    # A normal workflow leaf beneath a symlinked .github ancestor is still
    # an alias outside the reviewed repository tree.
    if any(part.is_symlink() for part in (directory, *directory.parents)) or not directory.is_dir():
        raise AuditFailure("workflow directory missing or symlinked")
    matches: list[str] = []
    for workflow in sorted((*directory.glob("*.yml"), *directory.glob("*.yaml"))):
        if workflow.is_symlink() or not workflow.is_file():
            raise AuditFailure("workflow path missing or symlinked")
        if workflow.stat().st_size > MAX_WORKFLOW_SOURCE_BYTES:
            raise AuditFailure("workflow source exceeds reviewed byte limit")
        try:
            source = workflow.read_text(encoding="utf-8")
        except UnicodeError as exc:
            raise AuditFailure("workflow source invalid UTF-8") from exc
        if workflow_matches_path(source, relative):
            matches.append(workflow.relative_to(repo_root).as_posix())
    return matches


def classify(matches: list[str]) -> str:
    if set(matches) & KNOWN_EXTERNAL_BLOCKED_WORKFLOWS:
        return "BLOCKED_KNOWN_EXTERNAL_DEPENDENCY"
    if len(matches) > MAX_REVIEWED_DIRECT_FANOUT:
        return "BLOCKED_HIGH_FANOUT"
    if set(matches) & KNOWN_WRITER_CAS_WORKFLOWS:
        return "BLOCKED_KNOWN_WRITER_CAS"
    return "BOUNDED_DIRECT_MATCH_ONLY"


def self_test(repo_root: Path) -> None:
    for label, path in (
        ("newline", "scripts/a\nb.py"),
        ("tab", "scripts/a\tb.py"),
        ("NUL", "scripts/a\x00b.py"),
        ("DEL", "scripts/a\x7fb.py"),
        ("C1 control", "scripts/a\u0085b.py"),
    ):
        try:
            validate_relative_path(path)
        except AuditFailure as exc:
            if str(exc) != "prewrite path must be a safe repository-relative path":
                raise
        else:
            raise AuditFailure("prewrite control-character path negative accepted: " + label)
    cases = (
        ("BOM filtered match", '\ufeffon:\n  push:\n    paths:\n      - "scripts/a.py"\n', "scripts/a.py", True),
        ("BOM unrelated", '\ufeffon:\n  push:\n    paths:\n      - "docs/**"\n', "scripts/a.py", False),
        ("BOM unfiltered", '\ufeffon: push\n', "scripts/a.py", True),
        ("BOM midstream ambiguity", 'on:\n  push:\n    paths:\n      - "docs/**"\n# \ufeff\n', "scripts/a.py", True),
        ("exact", 'on:\n  push:\n    paths:\n      - "scripts/a.py"\n', "scripts/a.py", True),
        ("glob", 'on:\n  pull_request:\n    paths:\n      - "scripts/validate-memory-os-rate-limit*.py"\n',
         "scripts/validate-memory-os-rate-limit-operations.py", True),
        ("unrelated", 'on:\n  push:\n    paths:\n      - "docs/**"\n', "scripts/a.py", False),
        ("unfiltered", 'on:\n  push:\n    branches:\n      - so\n', "scripts/a.py", True),
        ("paths-ignore", 'on:\n  push:\n    paths-ignore:\n      - "docs/**"\n', "scripts/a.py", True),
        ("dispatch", 'on:\n  workflow_dispatch:\n', "scripts/a.py", False),
        ("inline", 'on: [push, workflow_dispatch]\n', "scripts/a.py", True),
        ("quoted-on-block", "'on':\n  push:\n    paths:\n      - 'scripts/a.py'\n",
         "scripts/a.py", True),
        ("quoted-on-inline", '"on": [push, workflow_dispatch]\n',
         "scripts/a.py", True),
        ("scalar-push", "on: push\n", "scripts/a.py", True),
        ("spaced on key", "on : push\n", "scripts/a.py", True),
        ("quoted spaced on key", '"on" : [push]\n', "scripts/a.py", True),
        ("indented on key", ' on:\n  push:\n    paths:\n      - "docs/**"\n',
         "scripts/a.py", True),
        ("inline-map", "on: {pull_request: {paths: ['scripts/a.py']}}\n",
         "scripts/a.py", True),
        ("scalar-dispatch", "on: workflow_dispatch\n", "scripts/a.py", False),
        ("quoted-push-event", "on:\n  'push':\n    paths:\n      - scripts/a.py\n",
         "scripts/a.py", True),
        ("quoted-pr-event", 'on:\n  "pull_request":\n    paths:\n      - scripts/a.py\n',
         "scripts/a.py", True),
        ("duplicate on", 'on:\n  push:\n    paths:\n      - "docs/**"\non: push\n',
         "scripts/a.py", True),
        ("duplicate push", 'on:\n  push:\n    paths:\n      - "docs/**"\n  push:\n    paths:\n      - "scripts/a.py"\n',
         "scripts/a.py", True),
        ("event alias", 'on: *events\n', "scripts/a.py", True),
        ("quoted inline comment", 'on:\n  push:\n    paths:\n      - "scripts/a.py" # note\n',
         "scripts/a.py", True),
        ("plain inline comment", 'on:\n  push:\n    paths:\n      - scripts/a.py # note\n',
         "scripts/a.py", True),
        ("brace glob", 'on:\n  push:\n    paths:\n      - "scripts/{a,b}.py"\n',
         "scripts/a.py", True),
        ("optional suffix quantifier", 'on:\n  push:\n    paths:\n      - "scripts/a.py?"\n',
         "scripts/a.py", True),
        ("repeat char quantifier", 'on:\n  push:\n    paths:\n      - "scripts/a+.py"\n',
         "scripts/a.py", True),
        ("optional preceding char", 'on:\n  push:\n    paths:\n      - "scripts/aa?.py"\n',
         "scripts/a.py", True),
        ("globstar root zero", 'on:\n  push:\n    paths:\n      - "**/scripts/a.py"\n',
         "scripts/a.py", True),
        ("globstar nested zero", 'on:\n  push:\n    paths:\n      - "scripts/**/a.py"\n',
         "scripts/a.py", True),
        ("globstar double zero", 'on:\n  push:\n    paths:\n      - "**/scripts/**/a.py"\n',
         "scripts/a.py", True),
        ("globstar unrelated", 'on:\n  push:\n    paths:\n      - "**/docs/a.py"\n',
         "scripts/a.py", False),
        ("block push sequence", 'on:\n  - push\n', "scripts/a.py", True),
        ("block target sequence", 'on:\n  - pull_request_target\n', "scripts/a.py", True),
        ("block dispatch only", 'on:\n  - workflow_dispatch\n', "scripts/a.py", False),
        ("block aliased sequence", 'name: &trigger push\non:\n  - *trigger\n', "scripts/a.py", True),
        ("inline aliased sequence", 'name: &trigger push\non: [*trigger]\n', "scripts/a.py", True),
        ("inline dispatch list", 'on: [workflow_dispatch]\n', "scripts/a.py", False),
        ("root escaped on key", '"o\\u006e": push\n', "scripts/a.py", True),
        ("inline escaped event", 'on: "p\\u0075sh"\n', "scripts/a.py", True),
        ("inline escaped event array", 'on: ["p\\u0075sh"]\n', "scripts/a.py", True),
        ("nested escaped event key", 'on:\n  "p\\u0075sh":\n    paths:\n      - "docs/**"\n',
         "scripts/a.py", True),
        ("plain quoted unrelated root", '"name": workflow_dispatch\n', "scripts/a.py", False),
        ("plain escaped literal", 'on:\n  push:\n    paths:\n      - scripts/\\a.py\n',
         "scripts/a.py", True),
        ("plain escaped bracket", 'on:\n  push:\n    paths:\n      - scripts/\\[a].py\n',
         "scripts/[a].py", True),

        ("duplicate paths", 'on:\n  push:\n    paths:\n      - "docs/**"\n    paths:\n      - "scripts/a.py"\n',
         "scripts/a.py", True),
        ("extglob", 'on:\n  push:\n    paths:\n      - "scripts/!(b).py"\n',
         "scripts/a.py", True),
        ("blank after unrelated list", 'on:\n  push:\n    paths:\n      - "docs/**"\n\n',
         "scripts/a.py", False),
        ("blank inside matching list", 'on:\n  push:\n    paths:\n      - "docs/**"\n\n      - "scripts/a.py"\n',
         "scripts/a.py", True),
        ("unreviewed trailing mapping", 'on:\n  push:\n    paths:\n      - "docs/**"\n    types:\n      - opened\n',
         "scripts/a.py", True),
        ("target filtered", 'on:\n  pull_request_target:\n    paths:\n      - "scripts/a.py"\n',
         "scripts/a.py", True),
        ("target unrelated", 'on:\n  pull_request_target:\n    paths:\n      - "docs/**"\n',
         "scripts/a.py", False),
        ("target unfiltered", 'on:\n  pull_request_target:\n',
         "scripts/a.py", True),
        ("target quoted", 'on:\n  "pull_request_target":\n    paths:\n      - "scripts/a.py"\n',
         "scripts/a.py", True),
        ("target duplicate", 'on:\n  pull_request_target:\n    paths:\n      - "docs/**"\n  pull_request_target:\n    paths:\n      - "scripts/a.py"\n',
         "scripts/a.py", True),
    )
    # Pin the ordered fixture identities: an equal-count substitution must
    # not silently remove a previously reviewed negative.
    if (len(cases) != 57 or hashlib.sha256(
            "\n".join(case[0] for case in cases).encode("utf-8")
    ).hexdigest() != "3fdb90e2ec80278eb0ac49738367850c7c0665a6a74c4b06b3aac6090507286e"):
        raise AuditFailure("prewrite fanout synthetic fixture identity drift")
    for name, source, path, expected in cases:
        if workflow_matches_path(source, path) is not expected:
            raise AuditFailure("prewrite fanout negative/positive failed: " + name)
    if classify([".github/workflows/w" + str(i) + ".yml"
                 for i in range(MAX_REVIEWED_DIRECT_FANOUT + 1)]) != "BLOCKED_HIGH_FANOUT":
        raise AuditFailure("high-fanout threshold negative failed")
    if classify([".github/workflows/reconcile-upload-route-authority.yml"]) != (
            "BLOCKED_KNOWN_EXTERNAL_DEPENDENCY"):
        raise AuditFailure("known MinIO-coupled trigger negative failed")
    if classify([".github/workflows/reconcile-metrics-scrape-status.yml"]) != (
            "BLOCKED_KNOWN_WRITER_CAS"):
        raise AuditFailure("known source-SHA writer CAS trigger negative failed")
    high = matching_workflows(repo_root, "scripts/validate-memory-os-operability.py")
    rate = matching_workflows(
        repo_root, "scripts/validate-memory-os-rate-limit-operations-source-negative.py"
    )
    # A high-fanout path can also match the known MinIO-blocked workflow.
    # Preserve the higher-priority external blocker without hiding fanout.
    if len(high) <= MAX_REVIEWED_DIRECT_FANOUT:
        raise AuditFailure("known operability validator fanout not detected")
    if classify(high) not in ("BLOCKED_HIGH_FANOUT", "BLOCKED_KNOWN_EXTERNAL_DEPENDENCY"):
        raise AuditFailure("known operability validator risk classification missing")
    if not (set(rate) & KNOWN_EXTERNAL_BLOCKED_WORKFLOWS):
        raise AuditFailure("known upload-route MinIO trigger coupling not detected")
    entry_docs = matching_workflows(
        repo_root, "scripts/validate-memory-os-entry-docs.py"
    )
    reviewed_entry_docs = {
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
    if (set(entry_docs) != reviewed_entry_docs or
            len(entry_docs) != len(reviewed_entry_docs)):
        raise AuditFailure("shared entrypoint direct workflow identity changed; review required")
    entry_risk = classify(entry_docs)
    if (entry_risk != "BLOCKED_KNOWN_WRITER_CAS" or
            set(entry_docs) & KNOWN_WRITER_CAS_WORKFLOWS != KNOWN_WRITER_CAS_WORKFLOWS):
        raise AuditFailure("shared entrypoint writer CAS risk changed; review required")
    with tempfile.TemporaryDirectory(prefix="ops-fanout-parent-alias-") as tmp:
        root = Path(tmp) / "repo"
        root.mkdir()
        external = Path(tmp) / "external"
        (external / "workflows").mkdir(parents=True)
        (external / "workflows" / "w.yml").write_text("on: push\n", encoding="utf-8")
        (root / ".github").symlink_to(external, target_is_directory=True)
        try:
            matching_workflows(root, "scripts/a.py")
        except AuditFailure as exc:
            if str(exc) != "workflow directory missing or symlinked":
                raise
        else:
            raise AuditFailure("symlinked workflow parent negative accepted")
    with tempfile.TemporaryDirectory(prefix="ops-fanout-source-bytes-") as tmp:
        root = Path(tmp)
        directory = root / ".github/workflows"
        directory.mkdir(parents=True)
        workflow = directory / "w.yml"
        for label, payload, diagnostic in (
            ("oversized", b"#" * (MAX_WORKFLOW_SOURCE_BYTES + 1),
             "workflow source exceeds reviewed byte limit"),
            ("invalid UTF-8", b"\xff", "workflow source invalid UTF-8"),
        ):
            workflow.write_bytes(payload)
            try:
                matching_workflows(root, "scripts/a.py")
            except AuditFailure as exc:
                if str(exc) != diagnostic:
                    raise
            else:
                raise AuditFailure("workflow source byte negative accepted: " + label)
    print(
        "prewrite fanout audit PASS: " + str(len(cases) + 10)
        + " synthetic cases; operability direct matches="
        + str(len(high)) + "; rate-limit direct matches=" + str(len(rate))
        + "; entry-docs direct matches=" + str(len(entry_docs))
        + "; entry-docs risk=" + entry_risk
        + "; entry-docs workflows=" + ",".join(entry_docs)
        + "; known MinIO coupling flagged; no workflow executed"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--path")
    group.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test(args.repo_root)
            return 0
        matches = matching_workflows(args.repo_root, args.path)
        risk = classify(matches)
        print("prewrite direct path audit: " + args.path)
        print("risk: " + risk + "; matched workflow count: " + str(len(matches)))
        for workflow in matches:
            print("- " + workflow)
        if risk != "BOUNDED_DIRECT_MATCH_ONLY":
            print("Do not write until independent scoped review changes the precondition.")
            return 2
        print("Direct matching alone is not permission or transitive closure proof.")
        return 0
    except (OSError, UnicodeError, AuditFailure) as exc:
        print("PREWRITE TRIGGER AUDIT FAILED: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
