//go:build linux

package importflow

import (
	"context"
	"net/http"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/objectstore"
)

// TestFlowRecoversAfterObjectStoreOutage proves the import composition fails
// before parsing or database commit when the object store is unreachable, then
// safely reuses the exact same request after connectivity is restored.
func TestFlowRecoversAfterObjectStoreOutage(t *testing.T) {
	env := newFlowEnv(t, "genericcsv")
	now := time.Now().UTC()
	source := env.uploadSource(t, "upl_01J00000000000000000000009", flowSource)
	request := flowRequest(
		"spl_01J00000000000000000000009",
		"prv_flowoutage01",
		source,
		now,
	)

	unreachable, err := objectstore.New(objectstore.Config{
		Endpoint:        "http://127.0.0.1:1",
		Region:          "us-east-1",
		Bucket:          flowBucket,
		AccessKeyID:     "synthetic-outage-access",
		SecretAccessKey: "synthetic-outage-secret",
		HTTPClient:      &http.Client{Timeout: 250 * time.Millisecond},
	})
	if err != nil {
		t.Fatal(err)
	}
	env.flow.Objects = unreachable
	if _, err := env.flow.Run(context.Background(), request, now); err == nil {
		t.Fatal("import unexpectedly succeeded while the object store was unreachable")
	}
	assertNothingImported(t, env.pool)
	assertNoSpoolEntry(t, env.root, request.SpoolID)

	env.flow.Objects = env.objects
	result, err := env.flow.Run(context.Background(), request, now)
	if err != nil {
		t.Fatalf("import did not recover after object-store connectivity returned: %v", err)
	}
	if result.Commit.AlreadyCommitted {
		t.Fatal("recovered import was mislabeled as a replay")
	}
	if result.Verified.Evidence.Accepted.RecordCount != 2 ||
		result.Verified.Evidence.Rejected.RecordCount != 1 {
		t.Fatalf("unexpected recovered import evidence: %+v", result.Verified.Evidence)
	}

	var previews int
	if err := env.pool.QueryRow(
		context.Background(),
		"SELECT count(*) FROM memory_os.preview_ready WHERE id = $1",
		request.PreviewID,
	).Scan(&previews); err != nil {
		t.Fatal(err)
	}
	if previews != 1 {
		t.Fatalf("recovered import committed %d preview rows", previews)
	}
}
