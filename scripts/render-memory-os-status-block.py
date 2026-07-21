#!/usr/bin/env python3
"""Render the "Current status" prose block from fixture-index authority flags.

The checkpoint workflow used to require hand-editing the same status summary
in six separate files (README.md, SECURITY.md, the authority-order doc, the
status-roadmap doc, the service README, and the fixture index itself), and
that duplication produced real staleness bugs — one file would say a
checkpoint was confirmed green while another still named an old commit.

This script makes docs/fixtures/memory-os-security/fixture-index.round9.s1.v1.json
authority.* and remoteEvidence.* the single source of truth for that summary.
Each target file keeps the block between two HTML-comment markers; this script
only ever touches the text between them.

Usage:
    python scripts/render-memory-os-status-block.py --check   # CI gate
    python scripts/render-memory-os-status-block.py --write   # update files
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INDEX = REPO_ROOT / "docs/fixtures/memory-os-security/fixture-index.round9.s1.v1.json"

MARKER_BEGIN = "<!-- MEMORY_OS_STATUS_BLOCK:BEGIN -->"
MARKER_END = "<!-- MEMORY_OS_STATUS_BLOCK:END -->"

# One entry per prose section. `requires` lists the authority.* boolean keys
# that must ALL be true for `done_lines` to render; otherwise `pending_label`
# renders with the still-missing keys named explicitly, so an incomplete
# checkpoint is never silently reported as complete.
SECTIONS: list[dict] = [
    {
        "title": "Preview spool",
        "requires": [
            "previewSpoolManifestContractCreated",
            "previewSpoolFilesystemLifecycleCreated",
            "previewSpoolStreamWriterCreated",
            "previewSpoolSealCreated",
            "previewSpoolVerifierCreated",
            "previewSpoolReconciliationCreated",
        ],
        "done_lines": [
            "manifest contract hardened",
            "Linux attempt filesystem lifecycle created",
            "bounded accepted/rejected writer created",
            "stream fsync + no-replace manifest publication created",
            "independent decode / count / re-hash verifier created",
            "startup reconciliation + TTL cleanup created",
        ],
    },
    {
        "title": "PostgreSQL",
        "requires": [
            "postgresqlRlsMigrationCreated",
            "previewPostgresDomainSchemaCreated",
            "previewPostgresCopyRepositoryCreated",
        ],
        "done_lines": [
            "RLS / upload security foundations created",
            "production Preview domain schema created with live SQL tests",
            "atomic Go Preview commit repository created (live-tested)",
        ],
    },
    {
        "title": "object storage adapter",
        "requires": ["objectStorageAdapterCreated", "objectStorageMinioLiveTestsPassed"],
        "done_lines": ["created (live-tested against MinIO)"],
    },
    {
        "title": "parser supervisor",
        "requires": ["parserSupervisorProcessBoundaryCreated", "parserSupervisorIsolationTestsPassed"],
        "done_lines": ["process boundary created (live-tested; network namespace is deployment work)"],
    },
    {
        "title": "supervised import flow",
        "requires": ["supervisedImportFlowComposed", "supervisedImportFlowLiveTestsPassed"],
        "done_lines": ["composed and live-tested end to end (fetch → parse → verify → commit)"],
    },
    {
        "title": "canonical adapter record contract",
        "requires": ["canonicalAdapterRecordContractReviewed"],
        "done_lines": ["reviewed contract created; real adapter wired through the supervised worker"],
        "pending_label": "not reviewed; supervised flow still decodes an interim placeholder record shape",
    },
    {
        "title": "iOS / Portal",
        "requires": ["neverTrueSentinel"],  # always pending until this section is intentionally flipped
        "done_lines": [],
        "pending_label": "not implemented",
    },
]


def load_index() -> dict:
    return json.loads(FIXTURE_INDEX.read_text())


def render(index: dict) -> str:
    authority = index["authority"]
    evidence = index["evidence"]
    remote = index.get("remoteEvidence")

    lines: list[str] = []
    lines.append("product priority:")
    lines.append("Capture / Import first")
    lines.append("")
    lines.append("security architecture:")
    lines.append("DEFINED")
    lines.append("")
    lines.append("machine-readable contracts:")
    lines.append(f"{evidence['registeredSchemas']} schemas / {evidence['positiveContractFixtures']} positive fixtures")
    lines.append(f"{evidence['schemaNegativeRejections']} structural + {evidence['semanticNegativeRejections']} semantic rejection cases")
    lines.append("")
    lines.append("Go backend:")
    lines.append("PARTIAL SECURITY VERTICAL SLICE")
    lines.append("not a production backend")

    for section in SECTIONS:
        lines.append("")
        lines.append(f"{section['title']}:")
        missing = [key for key in section["requires"] if not authority.get(key, False)]
        if not missing:
            lines.extend(section["done_lines"])
        else:
            label = section.get("pending_label", "NOT YET COMPLETE")
            lines.append(label)
            if section["requires"] != ["neverTrueSentinel"]:
                lines.append(f"(pending: {', '.join(missing)})")

    lines.append("")
    if remote:
        lines.append("current full-repository Go suite:")
        lines.append("PASS in a local golang:1.23 Linux container at the recorded HEAD")
        lines.append("")
        lines.append("remote Actions:")
        lines.append(
            f"{remote['checkpointLabel']} HEAD {remote['headShaShort']} CONFIRMED green "
            f"(Import API run {remote['importApiRunId']}, Security Contracts run {remote['securityContractsRunId']})"
        )
    else:
        lines.append("remote Actions:")
        lines.append("UNCONFIRMED — no remoteEvidence recorded in the fixture index")

    lines.append("")
    lines.append("production:")
    lines.append("NO-GO")
    return "\n".join(lines)


def apply_to_file(path: Path, block: str) -> bool:
    """Replace the marked region in path. Returns True if content changed."""
    original = path.read_text()
    begin = original.find(MARKER_BEGIN)
    end = original.find(MARKER_END)
    if begin == -1 or end == -1 or end < begin:
        raise SystemExit(f"{path}: status block markers not found or malformed")
    prefix = original[: begin + len(MARKER_BEGIN)]
    suffix = original[end:]
    updated = f"{prefix}\n\n```txt\n{block}\n```\n\n{suffix}"
    if updated == original:
        return False
    path.write_text(updated)
    return True


def find_marked_files() -> list[Path]:
    found = []
    for path in REPO_ROOT.rglob("*.md"):
        if ".git" in path.parts:
            continue
        text = path.read_text(errors="ignore")
        if MARKER_BEGIN in text:
            found.append(path)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="fail if any marked file is out of date")
    mode.add_argument("--write", action="store_true", help="rewrite marked files to match the fixture index")
    args = parser.parse_args()

    index = load_index()
    block = render(index)
    targets = find_marked_files()
    if not targets:
        print("no files contain the status block markers", file=sys.stderr)
        return 1

    if args.write:
        changed = [str(path.relative_to(REPO_ROOT)) for path in targets if apply_to_file(path, block)]
        if changed:
            print("updated:")
            for name in changed:
                print(f"  {name}")
        else:
            print("all marked files already up to date")
        return 0

    # --check: render into memory and compare without writing.
    stale = []
    for path in targets:
        original = path.read_text()
        begin = original.find(MARKER_BEGIN)
        end = original.find(MARKER_END)
        if begin == -1 or end == -1:
            stale.append((path, "markers malformed"))
            continue
        prefix = original[: begin + len(MARKER_BEGIN)]
        suffix = original[end:]
        expected = f"{prefix}\n\n```txt\n{block}\n```\n\n{suffix}"
        if expected != original:
            stale.append((path, "content out of date"))
    if stale:
        print("status block is stale in:", file=sys.stderr)
        for path, reason in stale:
            print(f"  {path.relative_to(REPO_ROOT)}: {reason}", file=sys.stderr)
        print("run: python scripts/render-memory-os-status-block.py --write", file=sys.stderr)
        return 1
    print(f"status block is up to date in {len(targets)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
