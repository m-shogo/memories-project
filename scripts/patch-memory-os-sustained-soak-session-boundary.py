#!/usr/bin/env python3
"""Patch the LOCAL_LONG_SOAK post-run recovery boundary without changing session TTL."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "services/import-api/internal/httpserver/sustained_local_soak_test.go"
MARKER = "long-soak original session did not expire cleanly"
OLD = '''\t// Recovery proves the same long-lived server and parser boundary still
\t// accept new work after the final observation window.
\trecoveryPreview := runLiveHTTPBatch(1, 1, func(int) (*http.Request, error) {
\t\treturn liveRequest(http.MethodGet, previewPath, token, nil)
\t})
\trecoveryJob := server.createJob(t, owner)
\trecoveryUpload := runLiveObjectBatch(1, 1, server.server.URL, token, []string{recoveryJob})
\t_, recoveryParserErr := sustainedSoakParserRecovery(context.Background())
\trecoveryPassed := recoveryPreview.Successes == 1 && recoveryPreview.Failures == 0 &&
\t\trecoveryUpload.Successes == 1 && recoveryUpload.Failures == 0 && recoveryParserErr == nil
\tif !recoveryPassed {
\t\tt.Fatalf("long-soak recovery probe failed: preview=%+v upload=%+v parser=%v", recoveryPreview, recoveryUpload, recoveryParserErr)
\t}
'''
NEW = '''\t// The production session TTL is one hour, exactly the minimum evidence
\t// duration. Prove the original session expires normally, then re-authenticate
\t// the same still-active account and verify the long-lived server/parser can
\t// accept fresh work. Extending the original token would hide a real boundary.
\texpiredSession := runDeletionExactHTTPBatch(1, 1, func(int) (*http.Request, error) {
\t\treturn liveRequest(http.MethodGet, previewPath, token, nil)
\t})
\tif expiredSession.StatusCodeCounts["401"] != 1 ||
\t\texpiredSession.Summary.StatusClassCounts["5xx"] != 0 ||
\t\texpiredSession.Summary.StatusClassCounts["transport_error"] != 0 {
\t\tt.Fatalf("long-soak original session did not expire cleanly: %+v", expiredSession)
\t}
\trecoveryToken := sustainedSoakRenewSession(t, server, owner)
\trecoveryPreview := runLiveHTTPBatch(1, 1, func(int) (*http.Request, error) {
\t\treturn liveRequest(http.MethodGet, previewPath, recoveryToken, nil)
\t})
\trecoveryJob := server.createJob(t, owner)
\trecoveryUpload := runLiveObjectBatch(1, 1, server.server.URL, recoveryToken, []string{recoveryJob})
\t_, recoveryParserErr := sustainedSoakParserRecovery(context.Background())
\trecoveryPassed := recoveryPreview.Successes == 1 && recoveryPreview.Failures == 0 &&
\t\trecoveryUpload.Successes == 1 && recoveryUpload.Failures == 0 && recoveryParserErr == nil
\tif !recoveryPassed {
\t\tt.Fatalf("long-soak post-reauth recovery probe failed: preview=%+v upload=%+v parser=%v", recoveryPreview, recoveryUpload, recoveryParserErr)
\t}
'''


def main() -> int:
    text = PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("Memory OS sustained-soak session boundary already patched")
        return 0
    count = text.count(OLD)
    if count != 1:
        raise SystemExit(f"expected one old recovery block, found {count}")
    PATH.write_text(text.replace(OLD, NEW), encoding="utf-8")
    print("Memory OS sustained-soak session boundary patch applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
