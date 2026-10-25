#!/usr/bin/env python3
"""Add privacy-safe lifecycle stage accounting to the live MinIO checkpoint."""

from __future__ import annotations

import os
import stat
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "services/import-api/internal/httpserver/live_object_load_test.go"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if text.count(old) != 1:
        raise RuntimeError(f"{label} authority drift")
    return text.replace(old, new)



def validate_target() -> None:
    if PATH.is_symlink():
        raise RuntimeError("live object stage target symlink refused")
    if not PATH.is_file():
        raise RuntimeError("live object stage target is not a regular file")
    try:
        relative = PATH.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except ValueError as exc:
        raise RuntimeError("live object stage target escaped checkout") from exc
    if relative.as_posix() != "services/import-api/internal/httpserver/live_object_load_test.go":
        raise RuntimeError("live object stage target identity drift")


def atomic_write_text(path: Path, content: str) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    fd, temp_name = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, mode)
        os.replace(temp_name, path)
    finally:
        if os.path.lexists(temp_name):
            os.unlink(temp_name)


def main() -> int:
    validate_target()
    text = PATH.read_text(encoding="utf-8")
    changed = False

    updated = replace_once(
        text,
        '"sort"\n\t"sync"',
        '"sort"\n\t"strings"\n\t"sync"',
        "strings import",
    )
    changed = changed or updated != text
    text = updated

    helper_anchor = '''type issuedUpload struct {
\tAuthorizationID string            `json:"authorizationId"`
\tUploadURL       string            `json:"uploadUrl"`
\tRequiredHeaders map[string]string `json:"requiredHeaders"`
}
'''
    helper = helper_anchor + '''
func liveObjectStageError(stage string, err error) error {
\tif err == nil {
\t\terr = fmt.Errorf("unspecified failure")
\t}
\treturn fmt.Errorf("%s: %w", stage, err)
}
'''
    updated = replace_once(text, helper_anchor, helper, "stage helper")
    changed = changed or updated != text
    text = updated

    label_helper = helper + '''\nfunc liveObjectStageLabel(err error) string {
	if err == nil {
		return "unknown"
	}
	prefix, _, found := strings.Cut(err.Error(), ":")
	if !found {
		return "unknown"
	}
	switch prefix {
	case "issue", "issue_read", "issue_close", "issue_decode", "issue_contract", "put", "put_read", "put_close", "complete", "complete_read", "complete_close":
		return prefix
	}
	return "unknown"
}
'''
    updated = replace_once(text, helper, label_helper, "closed stage labels")
    changed = changed or updated != text
    text = updated

    replacements = [
        (
            '''\tissueResponse, err := client.Do(issueRequest)
\tif err != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: err}
\t}
''',
            '''\tissueResponse, err := client.Do(issueRequest)
\tif err != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: liveObjectStageError("issue", err)}
\t}
''',
            "issue transport",
        ),
        (
            '''\tif readErr != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: readErr}
\t}
\tif closeErr != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: closeErr}
\t}
\tif issueResponse.StatusCode != http.StatusCreated {
''',
            '''\tif readErr != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: liveObjectStageError("issue_read", readErr)}
\t}
\tif closeErr != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: liveObjectStageError("issue_close", closeErr)}
\t}
\tif issueResponse.StatusCode != http.StatusCreated {
''',
            "issue read",
        ),
        (
            '''\tif err := json.Unmarshal(issuePayload, &issued); err != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: err}
\t}
\tif issued.AuthorizationID == "" || issued.UploadURL == "" || len(issued.RequiredHeaders) == 0 {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: fmt.Errorf("incomplete upload authorization")}
\t}
''',
            '''\tif err := json.Unmarshal(issuePayload, &issued); err != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: liveObjectStageError("issue_decode", err)}
\t}
\tif issued.AuthorizationID == "" || issued.UploadURL == "" || len(issued.RequiredHeaders) == 0 {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: liveObjectStageError("issue_contract", fmt.Errorf("incomplete upload authorization"))}
\t}
''',
            "issue decode",
        ),
        (
            '''\tputResponse, err := client.Do(putRequest)
\tif err != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: err}
\t}
''',
            '''\tputResponse, err := client.Do(putRequest)
\tif err != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: liveObjectStageError("put", err)}
\t}
''',
            "put transport",
        ),
        (
            '''\tif readErr != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: readErr}
\t}
\tif closeErr != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: closeErr}
\t}
\tif putResponse.StatusCode != http.StatusOK {
''',
            '''\tif readErr != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: liveObjectStageError("put_read", readErr)}
\t}
\tif closeErr != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: liveObjectStageError("put_close", closeErr)}
\t}
\tif putResponse.StatusCode != http.StatusOK {
''',
            "put read",
        ),
        (
            '''\tcompleteResponse, err := client.Do(completeRequest)
\tif err != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: err}
\t}
''',
            '''\tcompleteResponse, err := client.Do(completeRequest)
\tif err != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: liveObjectStageError("complete", err)}
\t}
''',
            "complete transport",
        ),
        (
            '''\tif readErr != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: readErr}
\t}
\tif closeErr != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: closeErr}
\t}
\treturn liveHTTPSample{Status: completeResponse.StatusCode, Duration: time.Since(started)}
''',
            '''\tif readErr != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: liveObjectStageError("complete_read", readErr)}
\t}
\tif closeErr != nil {
\t\treturn liveHTTPSample{Duration: time.Since(started), Err: liveObjectStageError("complete_close", closeErr)}
\t}
\treturn liveHTTPSample{Status: completeResponse.StatusCode, Duration: time.Since(started)}
''',
            "complete read",
        ),
        (
            '''			stage := "unknown"
			if value := sample.Err.Error(); value != "" {
				if prefix, _, found := strings.Cut(value, ":"); found && prefix != "" {
					stage = prefix
				}
			}
			result.StatusClassCounts["transport_error_"+stage]++''',
            '''			stage := liveObjectStageLabel(sample.Err)
			result.StatusClassCounts["transport_error_"+stage]++''',
            "bounded stage accounting",
        ),
    ]

    for old, new, label in replacements:
        updated = replace_once(text, old, new, label)
        changed = changed or updated != text
        text = updated

    if not changed:
        print("Live object stage diagnostics already reconciled")
        return 0
    validate_target()
    atomic_write_text(PATH, text)
    print("Added privacy-safe live object lifecycle stage diagnostics")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"LIVE OBJECT STAGE DIAGNOSTIC RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
