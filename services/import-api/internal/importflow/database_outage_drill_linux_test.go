//go:build linux

package importflow

import (
	"context"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/m-shogo/memories-project/services/import-api/internal/previewcommit"
)

// TestFlowRecoversAfterDatabaseCommitOutage targets the most dangerous local
// database boundary: source fetch, parse, seal and verification have completed,
// but BEGIN for the atomic Preview commit cannot reach PostgreSQL. The failure
// must leave no durable rows, preserve the sealed attempt for investigation,
// and allow a new spool attempt for the same source and Preview ID to commit
// exactly once after database connectivity returns.
func TestFlowRecoversAfterDatabaseCommitOutage(t *testing.T) {
	env := newFlowEnv(t, "genericcsv")
	now := time.Now().UTC()
	source := env.uploadSource(t, "upl_01J00000000000000000000010", flowSource)
	healthyCommitter := env.flow.Committer

	badConfig, err := pgxpool.ParseConfig(
		"postgres://postgres:postgres@127.0.0.1:1/memory_os_unreachable?sslmode=disable",
	)
	if err != nil {
		t.Fatal(err)
	}
	badConfig.ConnConfig.ConnectTimeout = 250 * time.Millisecond
	badConfig.MaxConns = 1
	badPool, err := pgxpool.NewWithConfig(context.Background(), badConfig)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(badPool.Close)
	unreachableCommitter, err := previewcommit.NewCommitter(badPool)
	if err != nil {
		t.Fatal(err)
	}
	env.flow.Committer = unreachableCommitter

	failedRequest := flowRequest(
		"spl_01J00000000000000000000010",
		"prv_flowdbout001",
		source,
		now,
	)
	if _, err := env.flow.Run(context.Background(), failedRequest, now); err == nil {
		t.Fatal("import unexpectedly committed while PostgreSQL was unreachable")
	}
	assertNothingImported(t, env.pool)
	if _, err := os.Lstat(filepath.Join(env.root, failedRequest.SpoolID)); err != nil {
		t.Fatalf("database failure did not preserve sealed spool evidence: %v", err)
	}

	env.flow.Committer = healthyCommitter
	recoveryRequest := flowRequest(
		"spl_01J00000000000000000000011",
		failedRequest.PreviewID,
		source,
		now,
	)
	result, err := env.flow.Run(context.Background(), recoveryRequest, now)
	if err != nil {
		t.Fatalf("import did not recover after PostgreSQL connectivity returned: %v", err)
	}
	if result.Commit.AlreadyCommitted {
		t.Fatal("first successful recovery commit was mislabeled as a replay")
	}
	if result.Verified.Evidence.Accepted.RecordCount != 2 ||
		result.Verified.Evidence.Rejected.RecordCount != 1 {
		t.Fatalf("unexpected recovered import evidence: %+v", result.Verified.Evidence)
	}

	var previews int
	var candidates int
	var rejections int
	if err := env.pool.QueryRow(
		context.Background(),
		"SELECT count(*) FROM memory_os.preview_ready WHERE id = $1",
		recoveryRequest.PreviewID,
	).Scan(&previews); err != nil {
		t.Fatal(err)
	}
	if err := env.pool.QueryRow(
		context.Background(),
		"SELECT count(*) FROM memory_os.preview_candidate WHERE preview_id = $1",
		recoveryRequest.PreviewID,
	).Scan(&candidates); err != nil {
		t.Fatal(err)
	}
	if err := env.pool.QueryRow(
		context.Background(),
		"SELECT count(*) FROM memory_os.preview_rejection WHERE preview_id = $1",
		recoveryRequest.PreviewID,
	).Scan(&rejections); err != nil {
		t.Fatal(err)
	}
	if previews != 1 || candidates != 2 || rejections != 1 {
		t.Fatalf(
			"database recovery committed inconsistent rows: previews=%d candidates=%d rejections=%d",
			previews, candidates, rejections,
		)
	}
}
