#!/usr/bin/env python3
"""Reconcile the registered upload routes with HTTP prefilter and contracts.

The completion handler is registered at the direct authorization path. A stale
nested template in the low-cardinality route table caused the pre-auth hostile
path filter to reject the real handler with 404. This script performs bounded,
idempotent exact replacements and preserves historical fixture evidence.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OBSERVABILITY = ROOT / "services/import-api/internal/httpserver/observability.go"
SERVER = ROOT / "services/import-api/internal/httpserver/server.go"
LIVE_TEST = ROOT / "services/import-api/internal/httpserver/server_live_test.go"
ROUTE_TEST = ROOT / "services/import-api/internal/httpserver/route_authority_test.go"
METRICS_VALIDATOR = ROOT / "scripts/validate-memory-os-metrics.py"
RATE_LIMIT_VALIDATOR = ROOT / "scripts/validate-memory-os-rate-limit.py"
OBSERVABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-observability.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"

OLD_LABEL = "POST /v1/import-jobs/{jobId}/upload-authorizations/{id}/complete"
NEW_LABEL = "POST /v1/upload-authorizations/{id}/complete"

OLD_ROUTE_BLOCK = '''\tcase len(segments) == 6 && segments[0] == "v1" && segments[1] == "import-jobs" &&
\t\tsegments[3] == "upload-authorizations" && segments[5] == "complete":
\t\treturn method + " /v1/import-jobs/{jobId}/upload-authorizations/{id}/complete"
\tcase len(segments) == 5 && segments[0] == "v1" && segments[1] == "import-jobs" &&
\t\tsegments[3] == "upload-authorizations":
\t\treturn method + " /v1/import-jobs/{jobId}/upload-authorizations/{id}"
'''
NEW_ROUTE_BLOCK = '''\tcase len(segments) == 4 && segments[0] == "v1" &&
\t\tsegments[1] == "upload-authorizations" && segments[3] == "complete":
\t\treturn method + " /v1/upload-authorizations/{id}/complete"
'''

KNOWN_SHAPE_FUNCTION = '''
// knownAPIRouteShape is the pre-auth route-shape authority. It is deliberately
// separate from routeTemplate: the legacy /uploads tombstone must authenticate
// before returning 404 so a revoked session is still rejected consistently,
// but it remains the low-cardinality "other" metrics label and is not restored
// as a supported API. Every other unknown shape is rejected before session
// lookup to prevent hostile cardinality from becoming dependency load.
func knownAPIRouteShape(path string) bool {
\tsegments := strings.Split(strings.Trim(path, "/"), "/")
\tswitch {
\tcase matches(segments, "v1", "auth", "apple"):
\t\treturn true
\tcase matches(segments, "v1", "account"):
\t\treturn true
\tcase len(segments) == 4 && segments[0] == "v1" &&
\t\tsegments[1] == "import-jobs" && segments[3] == "upload-authorizations":
\t\treturn true
\tcase len(segments) == 4 && segments[0] == "v1" &&
\t\tsegments[1] == "upload-authorizations" && segments[3] == "complete":
\t\treturn true
\tcase len(segments) == 4 && segments[0] == "v1" &&
\t\tsegments[1] == "import-jobs" && segments[3] == "preview":
\t\treturn true
\tcase len(segments) == 4 && segments[0] == "v1" &&
\t\tsegments[1] == "previews" && segments[3] == "apply":
\t\treturn true
\tcase len(segments) == 4 && segments[0] == "v1" &&
\t\tsegments[1] == "import-jobs" && segments[3] == "uploads":
\t\treturn true
\tdefault:
\t\treturn false
\t}
}

'''

ROUTE_TEST_CONTENT = '''package httpserver

import (
\t"net/http"
\t"net/http/httptest"
\t"testing"
)

func TestRouteAuthorityMatchesRegisteredUploadSurface(t *testing.T) {
\ttests := []struct {
\t\tname     string
\t\tmethod   string
\t\tpath     string
\t\ttemplate string
\t\tknown    bool
\t}{
\t\t{"issue", http.MethodPost, "/v1/import-jobs/job_123/upload-authorizations", "POST /v1/import-jobs/{jobId}/upload-authorizations", true},
\t\t{"complete", http.MethodPost, "/v1/upload-authorizations/upl_123/complete", "POST /v1/upload-authorizations/{id}/complete", true},
\t\t{"preview", http.MethodGet, "/v1/import-jobs/job_123/preview", "GET /v1/import-jobs/{jobId}/preview", true},
\t\t{"apply", http.MethodPost, "/v1/previews/prv_123/apply", "POST /v1/previews/{previewId}/apply", true},
\t\t{"legacy tombstone", http.MethodPost, "/v1/import-jobs/job_123/uploads", "POST other", true},
\t\t{"obsolete nested completion", http.MethodPost, "/v1/import-jobs/job_123/upload-authorizations/upl_123/complete", "POST other", false},
\t\t{"hostile cardinality", http.MethodGet, "/v1/random/attacker-controlled/value", "GET other", false},
\t}
\tfor _, test := range tests {
\t\tt.Run(test.name, func(t *testing.T) {
\t\t\tif got := routeTemplate(test.method, test.path); got != test.template {
\t\t\t\tt.Fatalf("routeTemplate(%q, %q) = %q, want %q", test.method, test.path, got, test.template)
\t\t\t}
\t\t\tif got := knownAPIRouteShape(test.path); got != test.known {
\t\t\t\tt.Fatalf("knownAPIRouteShape(%q) = %v, want %v", test.path, got, test.known)
\t\t\t}
\t\t})
\t}
}

func TestRoutePrefilterPreservesKnownAndRejectsUnknownShapes(t *testing.T) {
\thandler := New(Config{})
\tfor _, test := range []struct {
\t\tpath string
\t\twant int
\t}{
\t\t{"/v1/upload-authorizations/upl_123/complete", http.StatusServiceUnavailable},
\t\t{"/v1/import-jobs/job_123/uploads", http.StatusServiceUnavailable},
\t\t{"/v1/random/attacker-controlled/value", http.StatusNotFound},
\t} {
\t\trequest := httptest.NewRequest(http.MethodPost, test.path, nil)
\t\tresponse := httptest.NewRecorder()
\t\thandler.ServeHTTP(response, request)
\t\tif response.Code != test.want {
\t\t\tt.Fatalf("POST %s returned %d, want %d", test.path, response.Code, test.want)
\t\t}
\t}
}
'''


class ReconcileFailure(RuntimeError):
    pass


ROLLBACK_SNAPSHOT: dict[Path, bytes | None] | None = None
ROLLBACK_WRITTEN: dict[Path, bytes] = {}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc


def read_regular_bytes(path: Path) -> bytes | None:
    """Read only a pinned regular file; never block on a FIFO or follow a leaf link."""
    for ancestor in (path, *path.parents):
        require(not ancestor.is_symlink(), f"symlink rollback/write path: {path}")
    try:
        before = path.lstat()
    except FileNotFoundError:
        return None
    require(stat.S_ISREG(before.st_mode), f"nonregular rollback/write path: {path}")
    for flag in ("O_NOFOLLOW", "O_NONBLOCK"):
        value = getattr(os, flag, None)
        require(type(value) is int and value > 0,
                f"unsupported safe authority read flag: {flag}")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        pinned = os.fstat(descriptor)
        require(
            stat.S_ISREG(pinned.st_mode)
            and (pinned.st_dev, pinned.st_ino) == (before.st_dev, before.st_ino),
            f"concurrent authority drift during read: {path}",
        )
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        require(
            (pinned.st_size, pinned.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
            f"concurrent authority drift during read: {path}",
        )
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    # Reject path aliases before staging bytes; parent symlinks can redirect
    # temporary-file creation outside the reviewed authority scope.
    for ancestor in (path, *path.parents):
        require(not ancestor.is_symlink(), f"symlink rollback/write path: {path}")
    if ROLLBACK_SNAPSHOT is not None:
        require(path in ROLLBACK_SNAPSHOT, f"untracked rollback/write path: {path}")
        expected = ROLLBACK_WRITTEN.get(path, ROLLBACK_SNAPSHOT[path])
        current = read_regular_bytes(path)
        require(current == expected, f"concurrent authority drift before write: {path}")
    # mkstemp defaults to 0600; retain the reviewed mode of existing files.
    # Bind publication to the exact target observed before staging. Atomic
    # rename alone does not prevent a concurrent local writer's lost update.
    try:
        initial_stat = path.lstat()
    except FileNotFoundError:
        initial_stat = None
    if initial_stat is not None:
        require(stat.S_ISREG(initial_stat.st_mode),
                f"nonregular rollback/write path: {path}")
    initial_bytes = read_regular_bytes(path)
    original_mode = stat.S_IMODE(initial_stat.st_mode) if initial_stat is not None else None
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        # fdopen owns the descriptor only after it returns successfully.
        # Close an untransferred descriptor if stream construction fails.
        try:
            handle = os.fdopen(descriptor, "wb")
        except BaseException:
            try:
                os.close(descriptor)
            except OSError:
                pass  # fdopen may have closed it before raising.
            raise
        with handle:
            written = handle.write(payload)
            require(type(written) is int and written == len(payload),
                    f"short atomic authority write: {path}")
            handle.flush()
            if original_mode is not None:
                os.fchmod(handle.fileno(), original_mode)
            os.fsync(handle.fileno())
        # A bounded final compare rejects edits, inode swaps, mode changes,
        # symlink swaps and new-file races during temporary-file staging.
        # This is not a dir_fd transaction or protection against a later swap.
        for ancestor in (path, *path.parents):
            require(not ancestor.is_symlink(), f"symlink rollback/write path: {path}")
        try:
            current_stat = path.lstat()
        except FileNotFoundError:
            current_stat = None
        if initial_stat is None:
            require(current_stat is None,
                    f"concurrent authority drift before publication: {path}")
        else:
            require(
                current_stat is not None
                and stat.S_ISREG(current_stat.st_mode)
                and (current_stat.st_dev, current_stat.st_ino, current_stat.st_mode)
                == (initial_stat.st_dev, initial_stat.st_ino, initial_stat.st_mode)
                and read_regular_bytes(path) == initial_bytes,
                f"concurrent authority drift before publication: {path}",
            )
        os.replace(temporary, path)
        if ROLLBACK_SNAPSHOT is not None:
            ROLLBACK_WRITTEN[path] = payload
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_text(path: Path, value: str) -> None:
    atomic_write_bytes(path, value.encode("utf-8"))


def write_if_changed(path: Path, value: str) -> bool:
    current = read(path) if path.exists() else ""
    if current == value:
        return False
    atomic_write_text(path, value)
    return True


def replace_once(value: str, old: str, new: str, label: str) -> tuple[str, bool]:
    count = value.count(old)
    if count == 0:
        require(new in value, f"{label}: neither old nor reconciled form is present")
        return value, False
    require(count == 1, f"{label}: expected one old form, found {count}")
    return value.replace(old, new), True


def current_authority_files() -> list[Path]:
    roots = [ROOT / "contracts", ROOT / "scripts", ROOT / "services/import-api", ROOT / ".github/workflows", ROOT / "docs"]
    allowed_suffixes = {".go", ".json", ".py", ".yml", ".yaml", ".md"}
    protected_learning = Path("docs/operations/AUTONOMOUS-OPS-LEARNING.md")
    protected_learning_scopes = {
        ("docs", "operations", "autonomous-learning-records"),
        ("docs", "operations", "autonomous-learning-addenda"),
        ("docs", "operations", "learning"),
    }
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix not in allowed_suffixes:
                continue
            relative = path.relative_to(ROOT)
            if relative.parts[:2] in (("docs", "fixtures"), ("docs", "evidence")):
                continue
            # Operational learning is append-only, never a route-label rewrite target.
            if relative == protected_learning or relative.parts[:3] in protected_learning_scopes:
                continue
            # A candidate symlink could redirect an otherwise scoped replacement
            # into protected learning or another authority outside the scan.
            if path.is_symlink():
                raise ReconcileFailure(f"symlink authority candidate: {relative}")
            if not path.is_file() or path == Path(__file__).resolve():
                continue
            files.append(path)
    return files


def snapshot_authority_files() -> None:
    global ROLLBACK_SNAPSHOT
    paths = set(current_authority_files()) | {OBSERVABILITY, SERVER, LIVE_TEST, ROUTE_TEST}
    ROLLBACK_SNAPSHOT = {path: read_regular_bytes(path) for path in paths}


def rollback_authority_files() -> None:
    if ROLLBACK_SNAPSHOT is None:
        return
    # Validate the entire snapshot before restoring anything, so a symlink
    # introduced after capture cannot cause a partial unsafe rollback.
    for path in ROLLBACK_SNAPSHOT:
        for ancestor in (path, *path.parents):
            require(not ancestor.is_symlink(), f"symlink rollback/write path: {path}")
    # Refuse a concurrent edit to any file actually written by this run.
    # Unchanged snapshot entries belong to their current owners, not rollback.
    for path, expected in ROLLBACK_WRITTEN.items():
        require(path in ROLLBACK_SNAPSHOT, f"untracked rollback path: {path}")
        current = read_regular_bytes(path)
        require(current == expected, f"concurrent authority drift before rollback: {path}")
    for path, original in ROLLBACK_SNAPSHOT.items():
        if path not in ROLLBACK_WRITTEN:
            continue
        if original is None:
            if path.exists():
                path.unlink()
            ROLLBACK_WRITTEN.pop(path, None)
            continue
        atomic_write_bytes(path, original)
        ROLLBACK_WRITTEN.pop(path, None)


def validate_canonical_authorities() -> None:
    for validator in (METRICS_VALIDATOR, RATE_LIMIT_VALIDATOR, OBSERVABILITY_VALIDATOR, OPERABILITY_VALIDATOR):
        require(validator.is_file() and not validator.is_symlink(), f"invalid canonical validator: {validator.relative_to(ROOT)}")
        result = subprocess.run([sys.executable, str(validator)], cwd=ROOT, check=False)
        require(type(result.returncode) is int and result.returncode == 0,
                f"canonical validator failed: {validator.relative_to(ROOT)}")


_CANONICAL_ROOT = ROOT
_CANONICAL_OBSERVABILITY = OBSERVABILITY
_CANONICAL_SERVER = SERVER
_CANONICAL_LIVE_TEST = LIVE_TEST
_CANONICAL_ROUTE_TEST = ROUTE_TEST
_CANONICAL_METRICS_VALIDATOR = METRICS_VALIDATOR
_CANONICAL_RATE_LIMIT_VALIDATOR = RATE_LIMIT_VALIDATOR
_CANONICAL_OBSERVABILITY_VALIDATOR = OBSERVABILITY_VALIDATOR
_CANONICAL_OPERABILITY_VALIDATOR = OPERABILITY_VALIDATOR
_CANONICAL_OLD_LABEL = OLD_LABEL
_CANONICAL_NEW_LABEL = NEW_LABEL
_CANONICAL_OLD_ROUTE_BLOCK = OLD_ROUTE_BLOCK
_CANONICAL_NEW_ROUTE_BLOCK = NEW_ROUTE_BLOCK
_CANONICAL_KNOWN_SHAPE_FUNCTION = KNOWN_SHAPE_FUNCTION
_CANONICAL_ROUTE_TEST_CONTENT = ROUTE_TEST_CONTENT
_CANONICAL_REQUIRE = require
_CANONICAL_READ = read
_CANONICAL_READ_REGULAR_BYTES = read_regular_bytes
_CANONICAL_ATOMIC_WRITE_BYTES = atomic_write_bytes
_CANONICAL_ATOMIC_WRITE_TEXT = atomic_write_text
_CANONICAL_WRITE_IF_CHANGED = write_if_changed
_CANONICAL_REPLACE_ONCE = replace_once
_CANONICAL_CURRENT_AUTHORITY_FILES = current_authority_files
_CANONICAL_SNAPSHOT_AUTHORITY_FILES = snapshot_authority_files
_CANONICAL_ROLLBACK_AUTHORITY_FILES = rollback_authority_files
_CANONICAL_VALIDATE_AUTHORITIES = validate_canonical_authorities
_CANONICAL_SUBPROCESS_RUN = subprocess.run
_CANONICAL_OS_REPLACE = os.replace
_CANONICAL_MKSTEMP = tempfile.mkstemp


def enforce_execution_authorities() -> None:
    if ROOT != _CANONICAL_ROOT:
        raise ReconcileFailure("upload route repository execution authority drift")
    for current, canonical, label in (
        (OBSERVABILITY, _CANONICAL_OBSERVABILITY, "observability source"),
        (SERVER, _CANONICAL_SERVER, "server source"),
        (LIVE_TEST, _CANONICAL_LIVE_TEST, "live test source"),
        (ROUTE_TEST, _CANONICAL_ROUTE_TEST, "route test source"),
        (METRICS_VALIDATOR, _CANONICAL_METRICS_VALIDATOR, "metrics validator"),
        (RATE_LIMIT_VALIDATOR, _CANONICAL_RATE_LIMIT_VALIDATOR, "rate-limit validator"),
        (OBSERVABILITY_VALIDATOR, _CANONICAL_OBSERVABILITY_VALIDATOR, "observability validator"),
        (OPERABILITY_VALIDATOR, _CANONICAL_OPERABILITY_VALIDATOR, "operability validator"),
    ):
        if current != canonical or current.is_symlink() or not current.is_file():
            raise ReconcileFailure(f"upload route {label} authority drift")
        try:
            if current.resolve(strict=True) != canonical.resolve(strict=True):
                raise ReconcileFailure(f"upload route {label} authority drift")
        except (FileNotFoundError, OSError, RuntimeError) as exc:
            raise ReconcileFailure(f"upload route {label} authority drift") from exc
    constants = (
        (OLD_LABEL, _CANONICAL_OLD_LABEL, "old label"),
        (NEW_LABEL, _CANONICAL_NEW_LABEL, "new label"),
        (OLD_ROUTE_BLOCK, _CANONICAL_OLD_ROUTE_BLOCK, "old route block"),
        (NEW_ROUTE_BLOCK, _CANONICAL_NEW_ROUTE_BLOCK, "new route block"),
        (KNOWN_SHAPE_FUNCTION, _CANONICAL_KNOWN_SHAPE_FUNCTION, "known route shape"),
        (ROUTE_TEST_CONTENT, _CANONICAL_ROUTE_TEST_CONTENT, "route test template"),
    )
    for current, canonical, label in constants:
        if current != canonical:
            raise ReconcileFailure(f"upload route {label} semantic authority drift")
    helpers = (
        (require, _CANONICAL_REQUIRE, "require"),
        (read, _CANONICAL_READ, "reader"),
        (read_regular_bytes, _CANONICAL_READ_REGULAR_BYTES, "pinned regular reader"),
        (atomic_write_bytes, _CANONICAL_ATOMIC_WRITE_BYTES, "atomic byte writer"),
        (atomic_write_text, _CANONICAL_ATOMIC_WRITE_TEXT, "atomic text writer"),
        (write_if_changed, _CANONICAL_WRITE_IF_CHANGED, "conditional writer"),
        (replace_once, _CANONICAL_REPLACE_ONCE, "replacement helper"),
        (current_authority_files, _CANONICAL_CURRENT_AUTHORITY_FILES, "authority scanner"),
        (snapshot_authority_files, _CANONICAL_SNAPSHOT_AUTHORITY_FILES, "snapshot helper"),
        (rollback_authority_files, _CANONICAL_ROLLBACK_AUTHORITY_FILES, "rollback helper"),
        (validate_canonical_authorities, _CANONICAL_VALIDATE_AUTHORITIES, "validator chain"),
        (subprocess.run, _CANONICAL_SUBPROCESS_RUN, "subprocess transport"),
        (os.replace, _CANONICAL_OS_REPLACE, "atomic replace transport"),
        (tempfile.mkstemp, _CANONICAL_MKSTEMP, "temporary file transport"),
    )
    for current, canonical, label in helpers:
        if current is not canonical:
            raise ReconcileFailure(f"upload route {label} execution authority drift")


_CANONICAL_ENFORCE_EXECUTION_AUTHORITIES = enforce_execution_authorities


def main() -> int:
    if enforce_execution_authorities is not _CANONICAL_ENFORCE_EXECUTION_AUTHORITIES:
        raise ReconcileFailure("upload route execution guard authority drift")
    enforce_execution_authorities()
    ROLLBACK_WRITTEN.clear()
    snapshot_authority_files()
    changed: list[str] = []

    observability = read(OBSERVABILITY)
    observability, did_change = replace_once(observability, OLD_ROUTE_BLOCK, NEW_ROUTE_BLOCK, "routeTemplate completion authority")
    if did_change:
        changed.append(str(OBSERVABILITY.relative_to(ROOT)))
    if "func knownAPIRouteShape(path string) bool" not in observability:
        marker = "func matches(segments []string, expected ...string) bool {"
        require(marker in observability, "known route-shape insertion marker missing")
        observability = observability.replace(marker, KNOWN_SHAPE_FUNCTION + marker, 1)
        if str(OBSERVABILITY.relative_to(ROOT)) not in changed:
            changed.append(str(OBSERVABILITY.relative_to(ROOT)))
    write_if_changed(OBSERVABILITY, observability)

    server = read(SERVER)
    old_condition = 'if strings.HasSuffix(routeTemplate(request.Method, request.URL.Path), " other") {'
    new_condition = "if !knownAPIRouteShape(request.URL.Path) {"
    server, did_change = replace_once(server, old_condition, new_condition, "pre-auth route filter")
    if did_change:
        server = server.replace(
            "known route shapes still pass through authentication and preserve 405.",
            "known route shapes and the explicit legacy tombstone still pass through authentication; unknown shapes remain pre-auth 404.",
        )
        changed.append(str(SERVER.relative_to(ROOT)))
    write_if_changed(SERVER, server)

    live_test = read(LIVE_TEST)
    replacements = {
        '"/v1/import-jobs/" + jobID + "/uploads"': '"/v1/import-jobs/" + jobID + "/upload-authorizations"',
        '"declaredContentType": "text/csv"': '"contentType": "text/csv"',
    }
    live_changed = False
    for old, new in replacements.items():
        if old in live_test:
            live_test = live_test.replace(old, new)
            live_changed = True
    require('"/v1/import-jobs/" + jobID + "/uploads"' not in live_test, "stale deletion probe remains")
    if live_changed:
        changed.append(str(LIVE_TEST.relative_to(ROOT)))
    write_if_changed(LIVE_TEST, live_test)

    if write_if_changed(ROUTE_TEST, ROUTE_TEST_CONTENT):
        changed.append(str(ROUTE_TEST.relative_to(ROOT)))

    for path in current_authority_files():
        value = read(path)
        if OLD_LABEL not in value:
            continue
        value = value.replace(OLD_LABEL, NEW_LABEL)
        atomic_write_text(path, value)
        relative = str(path.relative_to(ROOT))
        if relative not in changed:
            changed.append(relative)

    require(NEW_ROUTE_BLOCK in read(OBSERVABILITY), "direct completion route template missing")
    require("func knownAPIRouteShape(path string) bool" in read(OBSERVABILITY), "route-shape authority missing")
    require("if !knownAPIRouteShape(request.URL.Path)" in read(SERVER), "server does not use route-shape authority")
    require(NEW_LABEL in read(ROOT / "contracts/operations/metrics-contract.v1.json"), "metrics route authority was not updated")

    validate_canonical_authorities()

    print("Memory OS upload route authority reconcile PASS")
    if changed:
        print("changed:")
        for item in sorted(changed):
            print(f"- {item}")
    else:
        print("already current")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        rollback_authority_files()
        print(f"UPLOAD ROUTE AUTHORITY RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except Exception:
        rollback_authority_files()
        raise
