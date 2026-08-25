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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
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
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in allowed_suffixes:
                continue
            relative = path.relative_to(ROOT)
            if relative.parts[:2] == ("docs", "fixtures") or relative.parts[:2] == ("docs", "evidence"):
                continue
            if path == Path(__file__).resolve():
                continue
            files.append(path)
    return files


def snapshot_authority_files() -> None:
    global ROLLBACK_SNAPSHOT
    paths = set(current_authority_files()) | {OBSERVABILITY, SERVER, LIVE_TEST, ROUTE_TEST}
    ROLLBACK_SNAPSHOT = {path: path.read_bytes() if path.exists() else None for path in paths}


def rollback_authority_files() -> None:
    if ROLLBACK_SNAPSHOT is None:
        return
    for path, original in ROLLBACK_SNAPSHOT.items():
        if original is None:
            if path.exists():
                path.unlink()
            continue
        atomic_write_bytes(path, original)


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
