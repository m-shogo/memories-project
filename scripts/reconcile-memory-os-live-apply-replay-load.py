#!/usr/bin/env python3
"""Convert the live Apply load from a first-claim lock storm to replay load."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "services/import-api/internal/httpserver/live_load_test.go"

OLD = '''\tapplyStarted := time.Now().UTC()
\tapplyPath := server.server.URL + "/v1/previews/" + previewID + "/apply"
\tapplyBatch := runLiveHTTPBatch(96, 24, func(int) (*http.Request, error) {
\t\treturn liveRequest(http.MethodPost, applyPath, token, applyBody)
\t})
\tif applyBatch.StatusClassCounts["5xx"] != 0 || applyBatch.StatusClassCounts["transport_error"] != 0 {
\t\tt.Fatalf("live apply load produced infrastructure/internal failures: %+v", applyBatch)
\t}
\tif applyBatch.StatusClassCounts["2xx"] == 0 {
\t\tt.Fatalf("live apply load never completed one transaction: %+v", applyBatch)
\t}
\tfor class, count := range applyBatch.StatusClassCounts {
\t\tif count > 0 && class != "2xx" && class != "4xx" {
\t\t\tt.Fatalf("live apply load produced unexpected status class %s: %+v", class, applyBatch)
\t\t}
\t}
'''

NEW = '''\t// Establish the first durable claim synchronously. The dedicated mixed-version
\t// compatibility drill owns first-writer claim races and process-death recovery.
\t// This load checkpoint measures the stable replay path without manufacturing a
\t// PostgreSQL lock storm that outlives the HTTP clients.
\tfirstResponse, firstPayload := server.request(t, http.MethodPost,
\t\t"/v1/previews/"+previewID+"/apply", token, map[string]any{
\t\t\t"previewSha256":   previewSHA,
\t\t\t"idempotencyKey":  idempotencyKey,
\t\t\t"duplicatePolicy": "skip_existing",
\t\t})
\tif firstResponse.StatusCode != http.StatusOK {
\t\tt.Fatalf("initial live Apply failed: %d %s", firstResponse.StatusCode, firstPayload)
\t}
\tvar firstApply struct {
\t\tReplayed bool `json:"replayed"`
\t}
\tif err := json.Unmarshal(firstPayload, &firstApply); err != nil {
\t\tt.Fatal(err)
\t}
\tif firstApply.Replayed {
\t\tt.Fatalf("initial live Apply unexpectedly replayed: %s", firstPayload)
\t}

\tapplyStarted := time.Now().UTC()
\tapplyPath := server.server.URL + "/v1/previews/" + previewID + "/apply"
\tapplyBatch := runLiveHTTPBatch(96, 24, func(int) (*http.Request, error) {
\t\treturn liveRequest(http.MethodPost, applyPath, token, applyBody)
\t})
\tif applyBatch.StatusClassCounts["2xx"] != applyBatch.Requests ||
\t\tapplyBatch.StatusClassCounts["5xx"] != 0 ||
\t\tapplyBatch.StatusClassCounts["transport_error"] != 0 {
\t\tt.Fatalf("live replay load violated its status boundary: %+v", applyBatch)
\t}
'''


def main() -> int:
    text = PATH.read_text(encoding="utf-8")
    if NEW in text:
        print("Live Apply replay load is already reconciled")
        return 0
    if text.count(OLD) != 1:
        print("LIVE APPLY LOAD RECONCILE FAILED: source authority drift", file=sys.stderr)
        return 1
    PATH.write_text(text.replace(OLD, NEW), encoding="utf-8")
    print("Separated initial Apply claim from concurrent replay load")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
