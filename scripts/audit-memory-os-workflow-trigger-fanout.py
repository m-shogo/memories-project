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
import subprocess
import sys
import tempfile
import unicodedata
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


def flow_inline_complete(value: str) -> bool:
    """Recognize only a complete single-line YAML flow value.

    Brackets inside quoted scalars and comments are not delimiters.
    Any unknown or multiline form is conservatively treated as a trigger.
    """
    text = value.lstrip()
    if not text.startswith(("[", "{")):
        return True
    stack: list[str] = []
    quote = ""
    index = 0
    while index < len(text):
        char = text[index]
        if quote:
            if quote == '"' and char == "\\":
                index += 2
                continue
            if char == quote:
                if quote == "'" and index + 1 < len(text) and text[index + 1] == "'":
                    index += 2
                    continue
                quote = ""
        elif char in "'\"":
            quote = char
        elif char == "#" and (index == 0 or text[index - 1].isspace()):
            break
        elif char in "[{":
            stack.append(char)
        elif char in "]}":
            if not stack or (stack[-1], char) not in (("[", "]"), ("{", "}")):
                return False
            stack.pop()
            if not stack:
                tail = text[index + 1:].strip()
                return not tail or tail.startswith("#")
        index += 1
    return False


def workflow_matches_path(source: str, relative: str) -> bool:
    """Conservatively match direct push/PR events; ambiguous filters are risky."""
    # UTF-8 BOM is legal at the beginning of a YAML stream. Preserve its
    # semantics instead of silently missing the first root-level "on" key.
    if source.startswith("\ufeff"):
        source = source[1:]
    # A second BOM is not a reviewed event-filter spelling: fail closed.
    if "\ufeff" in source:
        return True
    # Unicode YAML line separators are outside the reviewed newline grammar.
    if any(separator in source for separator in ("\u0085", "\u2028", "\u2029")):
        return True
    # Flow-style YAML document roots can define on/push without a block
    # "on:" key. The block matcher cannot prove a non-match in this grammar.
    for row in source.splitlines():
        first = row.lstrip()
        if not first or first.startswith(("#", "%")):
            continue
        if first.startswith("---"):
            first = first[3:].lstrip()
            if not first or first.startswith("#"):
                continue
        if first.startswith("{"):
            return True
        break
    # YAML double-quoted mapping keys can decode \u escapes into "on".
    # Unknown escaped root keys are not proof of a dispatch-only workflow.
    if re.search(r'(?m)^[ \t]*"[^"\r\n]*\\[^"\r\n]*"[ \t]*:', source):
        return True
    # Root-level YAML merges or tagged/anchored/complex "on" keys may
    # introduce a trigger without a literal root-level on: declaration.
    if re.search(
        r"(?m)^(?:<<[ \t]*:|\?[ \t]+on(?:[ \t]*:|[ \t]*$)"
        r"|(?:!![A-Za-z0-9_-]+|!<[^>\r\n]+>)[ \t]+on[ \t]*:"
        r"|&[A-Za-z_][A-Za-z0-9_-]*[ \t]+on[ \t]*:)",
        source,
    ):
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
    # YAML permits a scalar event name or alias on the next indented
    # line after "on:". A block-map-only matcher would miss these valid
    # trigger spellings, including a comment-only "on:" header.
    if re.search(
        r"""(?m)^on:[ \t]*(?:#.*)?\n(?:(?:[ \t]*#.*|[ \t]*)\n)*[ \t]+(?:['"][^'"\r\n]*['"]|[A-Za-z_][A-Za-z0-9_-]*|\*[A-Za-z_][A-Za-z0-9_-]*)[ \t]*(?:#.*)?$""",
        source,
    ):
        return True

    inline = re.search(r"(?m)^on:[ \t]*([^\r\n]+)", source)
    # A multi-line YAML flow collection can contain an aliased or escaped
    # push/PR event outside the first "on:" row. The narrow block parser
    # cannot prove a non-match for a flow value without a same-line close.
    if inline:
        if not flow_inline_complete(inline.group(1)):
            return True
    # YAML also permits a flow value on a later indented row, after
    # comment-only or blank lines following the root "on:" key.
    if re.search(
        r"(?m)^on:[ \t]*(?:#.*)?\n(?:(?:[ \t]*#.*|[ \t]*)\n)*[ \t]+[\[{]",
        source,
    ):
        return True

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
    # YAML merge, complex, anchored or tagged keys can conceal event names.
    # The narrow literal event parser cannot prove these dispatch-only.
    if re.search(r"(?m)^  (?:<<[ \t]*:|[?&*!])", block):
        return True
    # An escaped quoted mapping key may decode to push/pull_request.
    if re.search(r'(?m)^  "[^"\r\n]*\\[^"\r\n]*"[ \t]*:', block):
        return True
    # YAML mapping/list indentation is not fixed at two spaces. A noncanonical
    # event key must not be mistaken for an absent push/PR trigger.
    for row in block.splitlines():
        event_row = re.match(
            r"""^([ \t]+)(['"]?)(push|pull_request_target|pull_request)\2[ \t]*:""", row
        )
        if event_row and (event_row.group(1) != "  " or event_row.group(2)):
            return True
    # Block YAML sequences are equivalent to inline event arrays. Treat
    # aliases or unreviewed entries as potentially unfiltered push/PR.
    live_rows = [
        row for row in block.splitlines()
        if row.strip() and not row.lstrip().startswith("#")
    ]
    sequence_rows = [
        row for row in live_rows if re.match(r"^[ \t]+-[ \t]+", row)
    ]
    # Only a top-level event sequence starts with a list item. Nested
    # paths/branches lists under an event mapping are not event sequences.
    if live_rows and re.match(r"^[ \t]+-[ \t]+", live_rows[0]):
        if len(sequence_rows) != len(live_rows):
            return True
        return any(
            re.sub(r"^[ \t]+-[ \t]+", "", row).strip() != "workflow_dispatch"
            for row in sequence_rows
        )
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
            # GitHub minimatch bracket negation/POSIX classes are not
            # fully represented by Python fnmatch (notably [^x] and [[:alpha:]]).
            if re.search(r"\[(?:[!^]|\[:)", pattern):
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


# Windows Win32 device stems (also reserved with extensions), including the
# documented superscript digits. This prewrite path is intentionally portable.
WINDOWS_RESERVED_DEVICE_STEMS = (
    {"con", "prn", "aux", "nul", "conin$", "conout$"}
    | {"com" + digit for digit in "123456789¹²³"}
    | {"lpt" + digit for digit in "123456789¹²³"}
)


def windows_component_ambiguous(part: str) -> bool:
    # Win32 strips terminal dots/spaces and treats device stems as devices,
    # even with a normal-looking extension (e.g. NUL.txt or COM¹.log).
    stem = part.split(".", 1)[0].rstrip(" ").casefold()
    return (
        part != part.rstrip(" .")
        or stem in WINDOWS_RESERVED_DEVICE_STEMS
        # Win32 8.3 short-name aliases can resolve to a different long-name
        # file when 8dot3 generation is enabled; do not infer safe identity.
        or re.fullmatch(r"[^.~ /]{1,6}~[1-9][0-9]*(?:\.[^.]{0,3})?", part) is not None
    )


def validate_relative_path(relative: str) -> None:
    if (not relative or relative.startswith("/") or "\\" in relative
            or ":" in relative
            # Concrete cross-platform source paths cannot contain Win32
            # wildcard or reserved filename metacharacters.
            or any(char in '<>"|?*' for char in relative)
            or any(part in ("", ".", "..") or part.rstrip(" .").casefold() == ".git"
                   or windows_component_ambiguous(part)
                   for part in relative.split("/"))
            or any(ord(char) < 32 or 127 <= ord(char) < 160 for char in relative)
            or any(unicodedata.category(char) in {"Cf", "Cs", "Zl", "Zp"}
                   for char in relative)
            # Canonically equivalent Unicode spellings can name the same
            # checkout entry on normalization-aware filesystems.
            or unicodedata.normalize("NFC", relative) != relative):
        raise AuditFailure("prewrite path must be a safe repository-relative path")


def require_workflow_git_index_identity(
        repo_root: Path, workflow_sources: list[Path]) -> None:
    """Optional read-only proof of checkout root and clean tracked workflow tree.

    Does not establish transitive CI reachability or permission to write.
    """
    if not (repo_root / ".git").is_dir():
        raise AuditFailure("prewrite Git index checkout identity unavailable")

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                ["git", "-C", str(repo_root), *args],
                capture_output=True, text=True, check=False, timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AuditFailure("prewrite Git index checkout identity unavailable") from exc

    root = git("rev-parse", "--show-toplevel")
    if (root.returncode != 0 or
            Path(root.stdout.strip()).resolve() != repo_root.resolve()):
        raise AuditFailure("prewrite Git index checkout root mismatch")
    index = git("ls-files", "--stage", "-z", "--", ".github/workflows")
    if index.returncode != 0:
        raise AuditFailure("prewrite Git index checkout identity unavailable")
    tracked: set[str] = set()
    for item in index.stdout.split("\0"):
        if not item:
            continue
        if "\t" not in item:
            raise AuditFailure("prewrite workflow Git index mode or stage drift")
        meta, relative = item.split("\t", 1)
        fields = meta.split()
        if (len(fields) != 3 or fields[0] not in ("100644", "100755")
                or fields[2] != "0" or len(fields[1]) not in (40, 64)
                or not re.fullmatch(r"[0-9a-f]+", fields[1])
                or relative in tracked):
            raise AuditFailure("prewrite workflow Git index mode or stage drift")
        tracked.add(relative)
    observed = {path.relative_to(repo_root).as_posix() for path in workflow_sources}
    if tracked != observed:
        raise AuditFailure("prewrite workflow Git index inventory drift")
    for args in (
        ("diff", "--quiet", "HEAD", "--", ".github/workflows"),
        ("diff", "--cached", "--quiet", "HEAD", "--", ".github/workflows"),
    ):
        if git(*args).returncode != 0:
            raise AuditFailure("prewrite workflow Git index content drift")


def matching_workflows(repo_root: Path, relative: str, *, require_git_index: bool = False) -> list[str]:
    validate_relative_path(relative)
    # A symlinked Git metadata root can point outside the reviewed checkout.
    if (repo_root / ".git").is_symlink():
        raise AuditFailure("prewrite checkout Git metadata symlinked")
    # A worktree gitdir file can redirect checkout identity outside this root.
    if (repo_root / ".git").is_file():
        raise AuditFailure("prewrite checkout Git metadata file requires review")
    # A caller-supplied repository root inside another checkout can inspect
    # a copied .github/workflows tree instead of the parent checkout authority.
    # The root's own .git marker is legitimate; an ancestor's is ambiguous.
    for ancestor in repo_root.parents:
        marker = ancestor / ".git"
        if marker.exists() or marker.is_symlink():
            raise AuditFailure("prewrite repository root nested under Git checkout")
    # Auditing a symlink alias is not proof about the underlying target.
    # Missing prospective files remain allowed; only existing aliases fail.
    target = repo_root / relative
    if any(part.is_symlink() for part in (target, *target.parents)):
        raise AuditFailure("prewrite target path symlinked")
    # A regular file with multiple directory entries can alias a writer
    # outside the requested path; do not audit it as an independent target.
    if target.is_file() and target.stat().st_nlink != 1:
        raise AuditFailure("prewrite target hardlink alias")
    # A checked-out Gitlink can hide nested source authority. This direct
    # matcher has no reviewed Git index/submodule closure, so refuse bounded
    # claims if any submodule configuration is present (even unrelated paths).
    gitmodules = repo_root / ".gitmodules"
    if gitmodules.exists() or gitmodules.is_symlink():
        raise AuditFailure("prewrite Git submodule inventory requires review")
    # Nested .git directories and worktree gitdir files are distinct checkouts.
    # The repository root's own .git is expected and is deliberately excluded.
    for component in (target, *target.parents):
        if component == repo_root:
            break
        marker = component / ".git"
        if marker.exists() or marker.is_symlink():
            raise AuditFailure("prewrite nested Git checkout requires review")
    directory = repo_root / ".github/workflows"
    # A normal workflow leaf beneath a symlinked .github ancestor is still
    # an alias outside the reviewed repository tree.
    if any(part.is_symlink() for part in (directory, *directory.parents)) or not directory.is_dir():
        raise AuditFailure("workflow directory missing or symlinked")
    # A nested Git checkout under .github can substitute a workflow tree
    # without using a symlink or hardlink. The repository root .git is normal.
    for component in (directory, directory.parent):
        marker = component / ".git"
        if marker.exists() or marker.is_symlink():
            raise AuditFailure("workflow directory nested Git checkout")
    # A case-insensitive checkout can collapse distinct workflow source
    # filenames, while an uppercase extension or trailing dot/space may
    # alias a reviewed YAML leaf without matching the glob on this host.
    # Enumerate all leaves before trusting direct trigger fanout.
    workflow_sources: list[Path] = []
    seen_workflow_names: set[str] = set()
    for entry in sorted(directory.iterdir()):
        normalized = entry.name.rstrip(" .")
        # An NTFS alternate-stream suffix can shadow an otherwise normal
        # YAML filename even though its complete spelling lacks .yml.
        if not normalized.casefold().split(":", 1)[0].endswith((".yml", ".yaml")):
            continue
        try:
            validate_relative_path(entry.name)
        except AuditFailure as exc:
            raise AuditFailure("workflow source filename alias") from exc
        if entry.name != normalized or not entry.name.endswith((".yml", ".yaml")):
            raise AuditFailure("workflow source filename alias")
        folded = entry.name.casefold()
        if folded in seen_workflow_names:
            raise AuditFailure("workflow source casefold alias")
        seen_workflow_names.add(folded)
        workflow_sources.append(entry)
    if require_git_index:
        require_workflow_git_index_identity(repo_root, workflow_sources)
    matches: list[str] = []
    for workflow in workflow_sources:
        if workflow.is_symlink() or not workflow.is_file():
            raise AuditFailure("workflow path missing or symlinked")
        if workflow.stat().st_nlink != 1:
            raise AuditFailure("workflow source hardlink alias")
        if workflow.stat().st_size > MAX_WORKFLOW_SOURCE_BYTES:
            raise AuditFailure("workflow source exceeds reviewed byte limit")
        try:
            source = workflow.read_text(encoding="utf-8")
        except UnicodeError as exc:
            raise AuditFailure("workflow source invalid UTF-8") from exc
        if workflow_matches_path(source, relative):
            matches.append(workflow.relative_to(repo_root).as_posix())
    return matches


def classify(matches: list[str], *, require_direct_match: bool = False) -> str:
    # Direct push/PR matching is necessary but not sufficient for CI reachability.
    # In strict prewrite mode, zero matching workflows cannot authorize a write.
    if require_direct_match and not matches:
        return "BLOCKED_NO_DIRECT_PUSH_PR_MATCH"
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
        ("bidi override", "scripts/a\u202eb.py"),
        ("zero-width joiner", "scripts/a\u200db.py"),
        ("Unicode line separator", "scripts/a\u2028b.py"),
        ("Git metadata root", ".git/config"),
        ("nested Git metadata", "scripts/.git/hooks/pre-commit"),
        ("Git metadata leaf", ".git"),
        ("casefold Git metadata root", ".GIT/config"),
        ("casefold nested Git metadata", "scripts/.GiT/hooks/pre-commit"),
        ("trailing-dot Git metadata", ".git./config"),
        ("trailing-space Git metadata", "scripts/.git /hooks"),
        ("Windows drive-relative path", "C:config"),
        ("Windows drive-prefixed path", "D:/outside/config"),
        ("NTFS alternate stream", "scripts/a.py:stream"),
        ("Windows reserved CON", "docs/CON"),
        ("Windows reserved NUL extension", "assets/nul.txt"),
        ("Windows reserved COM9", "COM9"),
        ("Windows reserved LPT1 extension", "docs/lpt1.log"),
        ("Windows reserved superscript COM", "docs/COM¹.txt"),
        ("Windows reserved superscript LPT", "docs/LPT²"),
        ("Windows reserved CONIN$", "docs/CONIN$.log"),
        ("Windows reserved CONOUT$", "docs/conout$"),
        ("Windows trailing dot", "docs/notes."),
        ("Windows trailing space", "docs/notes /readme.md"),
        ("decomposed Latin NFC alias", "docs/cafe\u0301.md"),
        ("decomposed Japanese NFC alias", "docs/ハ\u309aス.md"),
        ("Windows 8dot3 long-name alias", "docs/LONGFI~1.TXT"),
        ("Windows 8dot3 nested alias", "scripts/PROGRA~2/config"),
        ("Windows 8dot3 no-extension alias", "DOCUME~1"),
        ("Windows 8dot3 lowercase alias", "docs/longfi~9.txt"),
        ("Windows invalid left angle", "docs/<draft>.md"),
        ("Windows invalid right angle", "docs/report>.md"),
        ("Windows invalid quote", 'docs/report"draft.md'),
        ("Windows invalid pipe", "docs/report|final.md"),
        ("Windows invalid question", "docs/report?.md"),
        ("Windows invalid star", "docs/report*.md"),
    ):
        try:
            validate_relative_path(path)
        except AuditFailure as exc:
            if str(exc) != "prewrite path must be a safe repository-relative path":
                raise
        else:
            raise AuditFailure("prewrite control-character path negative accepted: " + label)
    # Ordinary Japanese filename characters remain valid repository paths.
    validate_relative_path("docs/日本語.md")
    validate_relative_path(".gitignore")
    validate_relative_path("docs/conifer.md")
    validate_relative_path("docs/company.txt")
    validate_relative_path("docs/café.md")
    validate_relative_path("docs/パス.md")
    validate_relative_path("docs/notes~draft.md")
    validate_relative_path("docs/longfi~0.txt")
    validate_relative_path("docs/report-final.md")
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
        ("one-space event map", 'on:\n push:\n  paths:\n   - "docs/**"\n', "scripts/a.py", True),
        ("four-space event map", 'on:\n    push:\n      paths:\n        - "docs/**"\n', "scripts/a.py", True),
        ("four-space quoted event map", 'on:\n    "pull_request":\n      paths:\n        - "docs/**"\n',
         "scripts/a.py", True),
        ("one-space event list", 'on:\n - push\n', "scripts/a.py", True),
        ("three-space event list", 'on:\n   - pull_request_target\n', "scripts/a.py", True),
        ("four-space dispatch only", 'on:\n    workflow_dispatch:\n', "scripts/a.py", False),
        ("nested paths list regression", 'on:\n  push:\n    branches: [so]\n    paths:\n      - "docs/**"\n',
         "scripts/a.py", False),
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
    if (len(cases) != 64 or hashlib.sha256(
            "\n".join(case[0] for case in cases).encode("utf-8")
    ).hexdigest() != "aa6b16cdb74560b4f64c6ace89735406d4b86711542d9ed0fc495cba357301df"):
        raise AuditFailure("prewrite fanout synthetic fixture identity drift")
    for name, source, path, expected in cases:
        if workflow_matches_path(source, path) is not expected:
            raise AuditFailure("prewrite fanout negative/positive failed: " + name)
    complex_event_cases = (
        ("merged event alias", "name: &events\n  push:\n    paths:\n      - \"scripts/a.py\"\non:\n  <<: *events\n", "scripts/a.py", True),
        ("spaced merge key", "name: &events push\non:\n  << : *events\n", "scripts/a.py", True),
        ("complex push key", "on:\n  ? push\n  :\n    paths:\n      - \"scripts/a.py\"\n", "scripts/a.py", True),
        ("anchored push key", "on:\n  &event push:\n    paths:\n      - \"scripts/a.py\"\n", "scripts/a.py", True),
        ("tagged push key", "on:\n  !!str push:\n    paths:\n      - \"scripts/a.py\"\n", "scripts/a.py", True),
        ("unrelated root anchor", "name: &events push\non:\n  workflow_dispatch:\n", "scripts/a.py", False),
    )
    if tuple(case[0] for case in complex_event_cases) != ("merged event alias","spaced merge key","complex push key","anchored push key","tagged push key","unrelated root anchor",):
        raise AuditFailure("prewrite complex-event fixture identity drift")
    for label, source, path, expected in complex_event_cases:
        if workflow_matches_path(source, path) is not expected:
            raise AuditFailure("prewrite complex-event negative/positive failed: " + label)
    root_event_cases = (
        ("root merged trigger", "events: &e {on: [push]}\n<<: *e\n", "scripts/a.py", True),
        ("root spaced merge", "events: &e {on: [push]}\n<< : *e\n", "scripts/a.py", True),
        ("root tagged on", "!!str on:\n    push:\n      paths:\n        - scripts/a.py\n", "scripts/a.py", True),
        ("root verbatim tag on", "!<tag:yaml.org,2002:str> on:\n    push:\n", "scripts/a.py", True),
        ("root anchored on", "&key on:\n    push:\n", "scripts/a.py", True),
        ("root complex on", "? on\n:\n    push:\n", "scripts/a.py", True),
        ("root unrelated anchor", "name: &e push\non: workflow_dispatch\n", "scripts/a.py", False),
        ("root flow push", "{\"on\": {\"push\": {\"paths\": [\"scripts/a.py\"]}}}\n", "scripts/a.py", True),
        ("root flow target", "{\"on\": [\"pull_request_target\"]}\n", "scripts/a.py", True),
        ("root flow document marker", "--- {\"on\": [\"push\"]}\n", "scripts/a.py", True),
        ("root flow dispatch conservative", "# header\n\n{\"on\": {\"workflow_dispatch\": {}}}\n", "scripts/a.py", True),
        ("nested JSON block is not root flow", "on:\n  workflow_dispatch:\njobs:\n  demo:\n    runs-on: ubuntu-latest\n    steps:\n      - run: |\n          {\"on\": {\"push\": {}}}\n", "scripts/a.py", False),
        ("indented escaped root on", "  \"o\\u006e\": push\n", "scripts/a.py", True),
        ("document indented escaped root on", "---\n  \"o\\u006e\": [pull_request]\n", "scripts/a.py", True),
        ("indented plain unrelated root", "  \"name\": workflow_dispatch\n", "scripts/a.py", False),
    )
    if tuple(case[0] for case in root_event_cases) != ("root merged trigger","root spaced merge","root tagged on","root verbatim tag on","root anchored on","root complex on","root unrelated anchor","root flow push","root flow target","root flow document marker","root flow dispatch conservative","nested JSON block is not root flow","indented escaped root on","document indented escaped root on","indented plain unrelated root",):
        raise AuditFailure("prewrite root-event fixture identity drift")
    for label, source, path, expected in root_event_cases:
        if workflow_matches_path(source, path) is not expected:
            raise AuditFailure("prewrite root-event negative/positive failed: " + label)
    multiline_flow_cases = (
        ("multiline flow alias", "on: [\n  *events\n]\n", "scripts/a.py", True),
        ("multiline flow escaped", "on: [\n  \"p\\u0075sh\"\n]\n", "scripts/a.py", True),
        ("multiline flow map merge", "on: {\n  <<: *events\n}\n", "scripts/a.py", True),
        ("multiline flow dispatch conservative", "on: [\n  workflow_dispatch\n]\n", "scripts/a.py", True),
        ("comment flow alias", "on: # events\n  # note\n  [\n    *events\n  ]\n", "scripts/a.py", True),
        ("inline dispatch comment", "on: [workflow_dispatch] # note\n", "scripts/a.py", False),
        ("inline dispatch map", "on: {workflow_dispatch: null}\n", "scripts/a.py", False),
        ("nested flow literal conservative", "on:\n  workflow_dispatch:\njobs:\n  demo:\n    steps:\n      - run: |\n          on: [\n            push\n          ]\n", "scripts/a.py", True),
    )
    if tuple(case[0] for case in multiline_flow_cases) != (
        "multiline flow alias",
        "multiline flow escaped",
        "multiline flow map merge",
        "multiline flow dispatch conservative",
        "comment flow alias",
        "inline dispatch comment",
        "inline dispatch map",
        "nested flow literal conservative",
    ):
        raise AuditFailure("prewrite multiline-flow fixture identity drift")
    for label, source, path, expected in multiline_flow_cases:
        if workflow_matches_path(source, path) is not expected:
            raise AuditFailure("prewrite multiline-flow negative/positive failed: " + label)

    block_scalar_cases = (
        ("block scalar push", "on:\n  push\n", "scripts/a.py", True),
        ("block quoted escaped scalar", "on:\n  \"p\\u0075sh\"\n", "scripts/a.py", True),
        ("block aliased scalar", "name: &events push\non:\n  *events\n", "scripts/a.py", True),
        ("commented block scalar", "on: # events\n  # note\n  push\n", "scripts/a.py", True),
        ("block dispatch scalar conservative", "on:\n  workflow_dispatch\n", "scripts/a.py", True),
        ("dispatch mapping unaffected", "on:\n  workflow_dispatch:\n", "scripts/a.py", False),
        ("dispatch list unaffected", "on:\n  - workflow_dispatch\n", "scripts/a.py", False),
        ("unrelated scalar outside on", "name:\n  push\non:\n  workflow_dispatch:\n", "scripts/a.py", False),
        ("block alias after blank", "name: &events [pull_request]\non:\n\n  *events\n", "scripts/a.py", True),
        ("quoted dispatch scalar conservative", "on:\n  \"workflow_dispatch\"\n", "scripts/a.py", True),
    )
    if tuple(case[0] for case in block_scalar_cases) != (
        "block scalar push",
        "block quoted escaped scalar",
        "block aliased scalar",
        "commented block scalar",
        "block dispatch scalar conservative",
        "dispatch mapping unaffected",
        "dispatch list unaffected",
        "unrelated scalar outside on",
        "block alias after blank",
        "quoted dispatch scalar conservative",
    ):
        raise AuditFailure("prewrite block-scalar fixture identity drift")
    for label, source, path, expected in block_scalar_cases:
        if workflow_matches_path(source, path) is not expected:
            raise AuditFailure("prewrite block-scalar negative/positive failed: " + label)

    flow_lexical_cases = (
        ("quoted bracket masks continuation", "on: [\"fake] # text\",\n  *events]\n", "scripts/a.py", True),
        ("quoted brace masks continuation", "on: {\"fake} # text\": {},\n  push: null}\n", "scripts/a.py", True),
        ("nested flow map incomplete", "on: [{workflow_dispatch: null}\n, *events]\n", "scripts/a.py", True),
        ("single-line quoted dispatch", "on: [\"workflow_dispatch\"]\n", "scripts/a.py", False),
        ("single-line nested dispatch map", "on: {workflow_dispatch: {}}\n", "scripts/a.py", False),
        ("quoted bracket complete", "on: [\"fake] # text\"]\n", "scripts/a.py", False),
        ("comment after complete", "on: [workflow_dispatch] # note\n", "scripts/a.py", False),
        ("single doubled quote complete", "on: ['work''flow_dispatch']\n", "scripts/a.py", False),
        ("invalid mismatched closer conservative", "on: [workflow_dispatch}\n", "scripts/a.py", True),
        ("trailing flow data conservative", "on: [workflow_dispatch] junk\n", "scripts/a.py", True),
    )
    if tuple(case[0] for case in flow_lexical_cases) != (
        "quoted bracket masks continuation",
        "quoted brace masks continuation",
        "nested flow map incomplete",
        "single-line quoted dispatch",
        "single-line nested dispatch map",
        "quoted bracket complete",
        "comment after complete",
        "single doubled quote complete",
        "invalid mismatched closer conservative",
        "trailing flow data conservative",
    ):
        raise AuditFailure("prewrite flow-lexer fixture identity drift")
    for label, source, path, expected in flow_lexical_cases:
        if workflow_matches_path(source, path) is not expected:
            raise AuditFailure("prewrite flow-lexer negative/positive failed: " + label)

    bracket_cases = (
        ("caret bracket negation", "on:\n  push:\n    paths:\n      - \"scripts/[^b].py\"\n", "scripts/a.py", True),
        ("bang bracket negation", "on:\n  push:\n    paths:\n      - \"scripts/[!b].py\"\n", "scripts/a.py", True),
        ("POSIX bracket class", "on:\n  push:\n    paths:\n      - \"scripts/[[:alpha:]].py\"\n", "scripts/a.py", True),
        ("ordinary bracket match", "on:\n  push:\n    paths:\n      - \"scripts/[ab].py\"\n", "scripts/a.py", True),
        ("ordinary bracket miss", "on:\n  push:\n    paths:\n      - \"scripts/[cd].py\"\n", "scripts/a.py", False),
    )
    if tuple(case[0] for case in bracket_cases) != ("caret bracket negation","bang bracket negation","POSIX bracket class","ordinary bracket match","ordinary bracket miss",):
        raise AuditFailure("prewrite bracket fixture identity drift")
    for label, source, path, expected in bracket_cases:
        if workflow_matches_path(source, path) is not expected:
            raise AuditFailure("prewrite bracket negative/positive failed: " + label)
    unicode_source_cases = (
        ("NEL event separator", "on:  push:    paths:      - scripts/a.py", "scripts/a.py", True),
        ("LS event separator", "on:   push:     paths:       - scripts/a.py", "scripts/a.py", True),
        ("PS event separator", "on:   push:     paths:       - scripts/a.py", "scripts/a.py", True),
        ("Japanese comment control", "name: テスト\non:\n  workflow_dispatch:\n", "scripts/a.py", False),
    )
    if tuple(case[0] for case in unicode_source_cases) != ("NEL event separator","LS event separator","PS event separator","Japanese comment control",):
        raise AuditFailure("prewrite Unicode source fixture identity drift")
    for label, source, path, expected in unicode_source_cases:
        if workflow_matches_path(source, path) is not expected:
            raise AuditFailure("prewrite Unicode source negative/positive failed: " + label)
    if classify([".github/workflows/w" + str(i) + ".yml"
                 for i in range(MAX_REVIEWED_DIRECT_FANOUT + 1)]) != "BLOCKED_HIGH_FANOUT":
        raise AuditFailure("high-fanout threshold negative failed")
    if classify([".github/workflows/reconcile-upload-route-authority.yml"]) != (
            "BLOCKED_KNOWN_EXTERNAL_DEPENDENCY"):
        raise AuditFailure("known MinIO-coupled trigger negative failed")
    if classify([".github/workflows/reconcile-metrics-scrape-status.yml"]) != (
            "BLOCKED_KNOWN_WRITER_CAS"):
        raise AuditFailure("known source-SHA writer CAS trigger negative failed")
    if classify([]) != "BOUNDED_DIRECT_MATCH_ONLY":
        raise AuditFailure("legacy diagnostic empty-fanout classification changed")
    if classify([], require_direct_match=True) != "BLOCKED_NO_DIRECT_PUSH_PR_MATCH":
        raise AuditFailure("strict prewrite empty-fanout negative accepted")
    if classify([".github/workflows/fixture.yml"], require_direct_match=True) != "BOUNDED_DIRECT_MATCH_ONLY":
        raise AuditFailure("strict prewrite direct-match positive failed")
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
    with tempfile.TemporaryDirectory(prefix="ops-fanout-git-index-") as tmp:
        root = Path(tmp) / "repo"
        directory = root / ".github/workflows"
        directory.mkdir(parents=True)
        workflow = directory / "w.yml"
        original = 'on: push\n'
        workflow.write_text(original, encoding="utf-8")
        def fixture_git(*args: str) -> None:
            result = subprocess.run(
                ["git", *args], capture_output=True, text=True,
                check=False, timeout=10,
            )
            if result.returncode != 0:
                raise AuditFailure("Git index fixture setup failed")
        fixture_git("init", "-q", str(root))
        fixture_git("-C", str(root), "add", ".github/workflows/w.yml")
        fixture_git("-C", str(root), "-c", "user.name=Fixture",
                    "-c", "user.email=fixture@example.invalid",
                    "commit", "-qm", "baseline")
        if matching_workflows(root, "scripts/a.py", require_git_index=True) != [
                ".github/workflows/w.yml"]:
            raise AuditFailure("tracked clean Git workflow positive failed")
        workflow.write_text('on: workflow_dispatch\n', encoding="utf-8")
        try:
            matching_workflows(root, "scripts/a.py", require_git_index=True)
        except AuditFailure as exc:
            if str(exc) != "prewrite workflow Git index content drift":
                raise
        else:
            raise AuditFailure("dirty Git workflow negative accepted")
        workflow.write_text(original, encoding="utf-8")
        extra = directory / "untracked.yml"
        extra.write_text(original, encoding="utf-8")
        try:
            matching_workflows(root, "scripts/a.py", require_git_index=True)
        except AuditFailure as exc:
            if str(exc) != "prewrite workflow Git index inventory drift":
                raise
        else:
            raise AuditFailure("untracked Git workflow negative accepted")
        extra.unlink()
        (root / ".git").rename(Path(tmp) / "detached-git")
        try:
            matching_workflows(root, "scripts/a.py", require_git_index=True)
        except AuditFailure as exc:
            if str(exc) != "prewrite Git index checkout identity unavailable":
                raise
        else:
            raise AuditFailure("missing Git index negative accepted")
    with tempfile.TemporaryDirectory(prefix="ops-fanout-target-alias-") as tmp:
        root = Path(tmp) / "repo"
        workflow_dir = root / ".github/workflows"
        workflow_dir.mkdir(parents=True)
        (workflow_dir / "w.yml").write_text(
            'on:\n  push:\n    paths:\n      - "scripts/a.py"\n', encoding="utf-8"
        )
        (root / "scripts").mkdir()
        if matching_workflows(root, "scripts/a.py") != [".github/workflows/w.yml"]:
            raise AuditFailure("missing prospective target positive failed")
        external = Path(tmp) / "external"
        external.write_text("fixture", encoding="utf-8")
        leaf = root / "scripts/a.py"
        leaf.symlink_to(external)
        for label in ("leaf", "parent"):
            try:
                matching_workflows(root, "scripts/a.py")
            except AuditFailure as exc:
                if str(exc) != "prewrite target path symlinked":
                    raise
            else:
                raise AuditFailure("symlinked prewrite target negative accepted: " + label)
            if label == "leaf":
                leaf.unlink()
                (root / "scripts").rmdir()
                outside = Path(tmp) / "outside"
                outside.mkdir()
                (root / "scripts").symlink_to(outside, target_is_directory=True)
    with tempfile.TemporaryDirectory(prefix="ops-fanout-target-hardlink-") as tmp:
        root = Path(tmp) / "repo"
        workflow_dir = root / ".github/workflows"
        workflow_dir.mkdir(parents=True)
        (workflow_dir / "w.yml").write_text(
            'on:\n  push:\n    paths:\n      - "scripts/a.py"\n', encoding="utf-8"
        )
        (root / "scripts").mkdir()
        external = Path(tmp) / "external"
        external.write_text("fixture", encoding="utf-8")
        (root / "scripts/a.py").hardlink_to(external)
        try:
            matching_workflows(root, "scripts/a.py")
        except AuditFailure as exc:
            if str(exc) != "prewrite target hardlink alias":
                raise
        else:
            raise AuditFailure("hardlinked prewrite target negative accepted")
    with tempfile.TemporaryDirectory(prefix="ops-fanout-workflow-hardlink-") as tmp:
        root = Path(tmp) / "repo"
        directory = root / ".github/workflows"
        directory.mkdir(parents=True)
        external = Path(tmp) / "external.yml"
        external.write_text('on: push\n', encoding="utf-8")
        (directory / "w.yml").hardlink_to(external)
        try:
            matching_workflows(root, "scripts/a.py")
        except AuditFailure as exc:
            if str(exc) != "workflow source hardlink alias":
                raise
        else:
            raise AuditFailure("hardlinked workflow source negative accepted")
    with tempfile.TemporaryDirectory(prefix="ops-fanout-workflow-name-alias-") as tmp:
        root = Path(tmp)
        directory = root / ".github/workflows"
        directory.mkdir(parents=True)
        source = 'on: push\n'
        (directory / "alpha.yml").write_text(source, encoding="utf-8")
        (directory / "beta.yaml").write_text(source, encoding="utf-8")
        if matching_workflows(root, "scripts/a.py") != [
                ".github/workflows/alpha.yml", ".github/workflows/beta.yaml"]:
            raise AuditFailure("distinct workflow filenames positive failed")
        (directory / "beta.yaml").unlink()
        for label, alias, diagnostic in (
            ("casefold collision", "ALPHA.yml", "workflow source casefold alias"),
            ("uppercase extension", "alpha.YML", "workflow source filename alias"),
            ("trailing dot", "alpha.yml.", "workflow source filename alias"),
            ("trailing space", "alpha.yml ", "workflow source filename alias"),
            ("reserved device", "NUL.yml", "workflow source filename alias"),
            ("superscript device", "COM¹.yml", "workflow source filename alias"),
            ("wildcard filename", "audit?.yml", "workflow source filename alias"),
            ("decomposed Unicode filename", "cafe\u0301.yml", "workflow source filename alias"),
            ("DOS short-name filename", "LONGFI~1.yml", "workflow source filename alias"),
            ("NTFS alternate-stream filename", "audit.yml:stream", "workflow source filename alias"),
        ):
            leaf = directory / alias
            leaf.write_text(source, encoding="utf-8")
            try:
                matching_workflows(root, "scripts/a.py")
            except AuditFailure as exc:
                if str(exc) != diagnostic:
                    raise
            else:
                raise AuditFailure("workflow filename alias negative accepted: " + label)
            leaf.unlink()
    with tempfile.TemporaryDirectory(prefix="ops-fanout-submodule-identity-") as tmp:
        root = Path(tmp) / "repo"
        directory = root / ".github/workflows"
        directory.mkdir(parents=True)
        (directory / "w.yml").write_text('on: push\n', encoding="utf-8")
        (root / "scripts").mkdir()
        (root / ".git").mkdir()
        if matching_workflows(root, "scripts/a.py") != [".github/workflows/w.yml"]:
            raise AuditFailure("normal checkout root Git metadata positive failed")
        (root / ".git").rmdir()
        external_git = Path(tmp) / "external-git"
        external_git.mkdir()
        (root / ".git").symlink_to(external_git, target_is_directory=True)
        try:
            matching_workflows(root, "scripts/a.py")
        except AuditFailure as exc:
            if str(exc) != "prewrite checkout Git metadata symlinked":
                raise
        else:
            raise AuditFailure("symlinked checkout Git metadata negative accepted")
        (root / ".git").unlink()
        (root / ".git").write_text("gitdir: ../external-git\n", encoding="utf-8")
        try:
            matching_workflows(root, "scripts/a.py")
        except AuditFailure as exc:
            if str(exc) != "prewrite checkout Git metadata file requires review":
                raise
        else:
            raise AuditFailure("gitdir-file checkout root negative accepted")
        (root / ".git").unlink()
        (root / ".git").mkdir()
        outer_git = Path(tmp) / ".git"
        outer_git.mkdir()
        try:
            matching_workflows(root, "scripts/a.py")
        except AuditFailure as exc:
            if str(exc) != "prewrite repository root nested under Git checkout":
                raise
        else:
            raise AuditFailure("nested repository root prewrite negative accepted")
        outer_git.rmdir()
        gitmodules = root / ".gitmodules"
        gitmodules.write_text('[submodule "x"]\npath = vendor/x\n', encoding="utf-8")
        try:
            matching_workflows(root, "scripts/a.py")
        except AuditFailure as exc:
            if str(exc) != "prewrite Git submodule inventory requires review":
                raise
        else:
            raise AuditFailure("submodule inventory prewrite negative accepted")
        gitmodules.unlink()
        (root / "scripts/.git").write_text("gitdir: ../external\n", encoding="utf-8")
        try:
            matching_workflows(root, "scripts/a.py")
        except AuditFailure as exc:
            if str(exc) != "prewrite nested Git checkout requires review":
                raise
        else:
            raise AuditFailure("nested Git checkout prewrite negative accepted")
    with tempfile.TemporaryDirectory(prefix="ops-fanout-workflow-git-boundary-") as tmp:
        root = Path(tmp) / "repo"
        directory = root / ".github/workflows"
        directory.mkdir(parents=True)
        (directory / "w.yml").write_text('on: push\n', encoding="utf-8")
        (root / ".git").mkdir()
        if matching_workflows(root, "scripts/a.py") != [".github/workflows/w.yml"]:
            raise AuditFailure("workflow root Git metadata positive failed")
        for label, component in (("github parent", directory.parent),
                                 ("workflow directory", directory)):
            marker = component / ".git"
            marker.write_text("gitdir: ../external\n", encoding="utf-8")
            try:
                matching_workflows(root, "scripts/a.py")
            except AuditFailure as exc:
                if str(exc) != "workflow directory nested Git checkout":
                    raise
            else:
                raise AuditFailure("nested workflow Git checkout negative accepted: " + label)
            marker.unlink()
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
        "prewrite fanout audit PASS: " + str(len(cases) + 67 + len(complex_event_cases) + len(root_event_cases) + len(bracket_cases) + len(unicode_source_cases) + len(multiline_flow_cases) + len(block_scalar_cases) + len(flow_lexical_cases))
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
    parser.add_argument("--require-git-index-identity", action="store_true",
                        help="require clean tracked workflow sources in the exact Git checkout")
    parser.add_argument("--require-direct-push-pr-match", action="store_true",
                        help="fail closed when no push/PR workflow directly matches; not a CI closure proof")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--path")
    group.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test(args.repo_root)
            return 0
        matches = matching_workflows(args.repo_root, args.path,
                                     require_git_index=args.require_git_index_identity)
        risk = classify(matches, require_direct_match=args.require_direct_push_pr_match)
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
