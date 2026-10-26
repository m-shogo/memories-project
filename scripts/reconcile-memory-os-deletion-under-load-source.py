#!/usr/bin/env python3
"""Apply deterministic source corrections for deletion-under-load."""

from __future__ import annotations

import os
import stat
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "services/import-api/internal/httpserver/deletion_under_load_test.go"


MAX_SOURCE_BYTES = 1024 * 1024


def require_safe_source(path: Path) -> None:
    if not isinstance(path, Path) or not path.is_absolute():
        raise RuntimeError("deletion load source path must be absolute")
    if any(candidate.is_symlink() for candidate in (path, *path.parents)):
        raise RuntimeError("deletion load source symlink refused")
    if not path.is_file():
        raise RuntimeError("deletion load source missing or unsafe")
    try:
        path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (OSError, ValueError):
        raise RuntimeError("deletion load source escaped repository") from None


def read_source(path: Path) -> str:
    require_safe_source(path)
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_SOURCE_BYTES + 1)
        if len(raw) > MAX_SOURCE_BYTES:
            raise RuntimeError("deletion load source exceeds reviewed read limit")
        return raw.decode("utf-8")
    except (OSError, UnicodeError):
        raise RuntimeError("deletion load source unreadable or invalid") from None


def write_source(path: Path, text: str) -> None:
    require_safe_source(path)
    if type(text) is not str:
        raise RuntimeError("deletion load source payload must be text")
    try:
        payload = text.encode("utf-8")
    except UnicodeError:
        raise RuntimeError("deletion load source payload invalid UTF-8") from None
    if len(payload) > MAX_SOURCE_BYTES:
        raise RuntimeError("deletion load source payload exceeds reviewed write limit")
    temporary: Path | None = None
    try:
        existing_mode = stat.S_IMODE(path.stat().st_mode)
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, existing_mode)
        os.replace(temporary, path)
        temporary = None
    except (OSError, UnicodeError) as exc:
        raise RuntimeError(f"deletion load source atomic write failed ({type(exc).__name__})") from None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                pass


def replace_once(text: str, old: str, new: str, label: str) -> tuple[str, bool]:
    if new in text:
        if text.count(new) != 1 or old in text.replace(new, "", 1):
            raise RuntimeError(f"{label} mixed or duplicate source authority drift")
        return text, False
    if text.count(old) != 1:
        raise RuntimeError(f"{label} authority drift")
    return text.replace(old, new), True


def main() -> int:
    if PATH != ROOT / "services/import-api/internal/httpserver/deletion_under_load_test.go":
        raise RuntimeError("unreviewed deletion load source target refused")
    text = read_source(PATH)
    changed = False

    text, replaced = replace_once(
        text,
        '"memory-os-import-api/internal/accountdelete"',
        '"github.com/m-shogo/memories-project/services/import-api/internal/accountdelete"',
        "accountdelete import",
    )
    changed = changed or replaced

    text, replaced = replace_once(
        text,
        '\t"fmt"\n\t"net/http"',
        '\t"fmt"\n\t"io"\n\t"net/http"',
        "io import",
    )
    changed = changed or replaced

    text, replaced = replace_once(
        text,
        '\t"runtime"\n\t"strconv"',
        '\t"runtime"\n\t"sort"\n\t"strconv"',
        "sort import",
    )
    changed = changed or replaced

    text, replaced = replace_once(
        text,
        '''\t\t\t\t_ = response.Body.Close()
\t\t\t\tsamples[index] = liveHTTPSample{Status: response.StatusCode, Duration: time.Since(started)}
''',
        '''\t\t\t\t_, copyErr := io.Copy(io.Discard, response.Body)
\t\t\t\tcloseErr := response.Body.Close()
\t\t\t\tif copyErr != nil {
\t\t\t\t\tsamples[index] = liveHTTPSample{Duration: time.Since(started), Err: copyErr}
\t\t\t\t\tcontinue
\t\t\t\t}
\t\t\t\tif closeErr != nil {
\t\t\t\t\tsamples[index] = liveHTTPSample{Duration: time.Since(started), Err: closeErr}
\t\t\t\t\tcontinue
\t\t\t\t}
\t\t\t\tsamples[index] = liveHTTPSample{Status: response.StatusCode, Duration: time.Since(started)}
''',
        "response drain",
    )
    changed = changed or replaced

    text, replaced = replace_once(
        text,
        'client := liveHTTPClient()',
        'client := &http.Client{Timeout: 15 * time.Second}',
        "HTTP client",
    )
    changed = changed or replaced

    helper_anchor = '''type deletionWorkerResult struct {
\tReceipts []accountdelete.Receipt
\tErr      error
\tDuration time.Duration
}
'''
    helper = helper_anchor + '''
func summarizeDeletionHTTPSamples(samples []liveHTTPSample, concurrency int, elapsed time.Duration) liveBatchResult {
\tresult := liveBatchResult{
\t\tRequests:          len(samples),
\t\tConcurrency:       concurrency,
\t\tStatusClassCounts: map[string]int{},
\t\tDurationSeconds:   elapsed.Seconds(),
\t}
\tif elapsed > 0 {
\t\tresult.Throughput = float64(len(samples)) / elapsed.Seconds()
\t}
\tlatencies := make([]time.Duration, 0, len(samples))
\tfor _, sample := range samples {
\t\tif sample.Err != nil {
\t\t\tresult.Failures++
\t\t\tresult.StatusClassCounts["transport_error"]++
\t\t\tcontinue
\t\t}
\t\tclass := fmt.Sprintf("%dxx", sample.Status/100)
\t\tresult.StatusClassCounts[class]++
\t\tif sample.Status >= 200 && sample.Status < 300 {
\t\t\tresult.Successes++
\t\t} else {
\t\t\tresult.Failures++
\t\t}
\t\tlatencies = append(latencies, sample.Duration)
\t}
\tsort.Slice(latencies, func(i, j int) bool { return latencies[i] < latencies[j] })
\tresult.LatencyP50Ms = livePercentileMillis(latencies, 0.50)
\tresult.LatencyP95Ms = livePercentileMillis(latencies, 0.95)
\tresult.LatencyP99Ms = livePercentileMillis(latencies, 0.99)
\treturn result
}
'''
    text, replaced = replace_once(text, helper_anchor, helper, "summary helper")
    changed = changed or replaced

    text, replaced = replace_once(
        text,
        'Summary:          summarizeLiveHTTPSamples(samples, concurrency, time.Since(started)),',
        'Summary:          summarizeDeletionHTTPSamples(samples, concurrency, time.Since(started)),',
        "summary call",
    )
    changed = changed or replaced

    if not changed:
        print("Deletion-under-load source already reconciled")
        return 0
    write_source(PATH, text)
    print("Reconciled deletion-under-load source, HTTP reuse and local aggregation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"DELETION LOAD SOURCE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
