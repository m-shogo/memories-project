package main

import (
	"context"
	"fmt"
	"os"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/m-shogo/memories-project/services/import-api/internal/accountdelete"
	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/objectstore"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgrepo"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgscope"
)

const testLeaseSeconds = 5

func fail(stage string) {
	_, _ = fmt.Fprintf(os.Stderr, "CONTAINER_DRILL_HELPER_FAILURE:%s\n", stage)
	os.Exit(70)
}

func progress(path string, stage string) {
	if path == "" {
		return
	}
	if err := os.WriteFile(path, []byte(stage+"\n"), 0o600); err != nil {
		fail("progress_signal")
	}
}

func main() {
	ctx := context.Background()
	mode := os.Getenv("MEMORY_OS_CONTAINER_DRILL_MODE")
	databaseURL := os.Getenv("MEMORY_OS_CONTAINER_DRILL_DATABASE_URL")
	endpoint := os.Getenv("MEMORY_OS_TEST_S3_ENDPOINT")
	access := os.Getenv("MEMORY_OS_TEST_S3_ACCESS_KEY")
	secret := os.Getenv("MEMORY_OS_TEST_S3_SECRET_KEY")
	signalPath := os.Getenv("MEMORY_OS_CONTAINER_DRILL_SIGNAL_PATH")
	progressPath := os.Getenv("MEMORY_OS_CONTAINER_DRILL_PROGRESS_PATH")
	if mode == "" || databaseURL == "" || endpoint == "" || access == "" || secret == "" || signalPath == "" {
		fail("missing_configuration")
	}
	progress(progressPath, "configuration-accepted")

	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		fail("database_pool")
	}
	defer pool.Close()
	progress(progressPath, "database-pool-created")

	var currentUser string
	var superuser, bypassRLS bool
	if err := pool.QueryRow(ctx,
		`SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user`,
	).Scan(&currentUser, &superuser, &bypassRLS); err != nil {
		fail("runtime_identity_query")
	}
	if currentUser != "memory_app_login" || superuser || bypassRLS {
		fail("runtime_identity_not_restricted")
	}
	progress(progressPath, "runtime-identity-verified")

	executor := dbscope.New(pgscope.Beginner{Pool: pool})
	control := pgrepo.AccountControl{Pool: pool, Transactions: executor}
	objects, err := objectstore.New(objectstore.Config{
		Endpoint:        endpoint,
		Region:          "us-east-1",
		Bucket:          "memory-os-quarantine-test",
		AccessKeyID:     access,
		SecretAccessKey: secret,
	})
	if err != nil {
		fail("object_store")
	}
	progress(progressPath, "dependencies-ready")

	switch mode {
	case "erase-block":
		claim, ok, err := control.Claim(ctx, testLeaseSeconds)
		if err != nil || !ok || claim.Attempts != 1 || claim.DeletionEpoch != 2 {
			fail("initial_claim")
		}
		progress(progressPath, "claim-acquired")
		keys, err := control.ObjectKeys(ctx, claim.AccountID, claim.DeletionEpoch)
		if err != nil || len(keys) == 0 {
			fail("object_ledger")
		}
		progress(progressPath, "object-ledger-discovered")
		erased, err := objects.EraseObject(ctx, keys[0])
		if err != nil || erased < 1 {
			fail("object_erasure")
		}
		progress(progressPath, "object-erased")
		if err := os.WriteFile(signalPath, []byte("claimed-and-erased\n"), 0o600); err != nil {
			fail("ready_signal")
		}
		progress(progressPath, "interruption-point-ready")
		// Intentionally never Release, Sweep or Complete. The container must be
		// killed externally while this lease remains active.
		for {
			time.Sleep(time.Hour)
		}

	case "recover":
		worker := accountdelete.Worker{
			Queue:        control,
			Repository:   control,
			Objects:      objects,
			LeaseSeconds: 30,
		}
		progress(progressPath, "replacement-worker-ready")
		receipts, err := worker.Sweep(ctx, 1)
		if err != nil || len(receipts) != 1 || receipts[0].DeletionEpoch != 2 || receipts[0].Attempts != 2 {
			fail("replacement_reclaim")
		}
		progress(progressPath, "replacement-attempt-2-complete")
		backlog, err := worker.Backlog(ctx)
		if err != nil || backlog.Pending != 0 || backlog.Stuck != 0 {
			fail("replacement_backlog")
		}
		if err := os.WriteFile(signalPath, []byte("recovered-attempt-2\n"), 0o600); err != nil {
			fail("recovery_signal")
		}
		progress(progressPath, "replacement-recovered")

	default:
		fail("unknown_mode")
	}
}
