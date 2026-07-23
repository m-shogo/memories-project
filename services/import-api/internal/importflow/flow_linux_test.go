//go:build linux

package importflow

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/m-shogo/memories-project/services/import-api/internal/adapters/genericcsv"
	"github.com/m-shogo/memories-project/services/import-api/internal/csvworker"
	"github.com/m-shogo/memories-project/services/import-api/internal/objectstore"
	"github.com/m-shogo/memories-project/services/import-api/internal/parsersup"
	"github.com/m-shogo/memories-project/services/import-api/internal/previewcommit"
	"github.com/m-shogo/memories-project/services/import-api/internal/previewspool"
	"github.com/m-shogo/memories-project/services/import-api/internal/upload"
)

const (
	flowJobID  = "job_01J000000000000000000000000"
	flowOwner  = "acct_01J00000000000000000000000"
	flowEpoch  = int64(7)
	flowBucket = "memory-os-quarantine-test"
)

func TestMain(m *testing.M) {
	if mode := os.Getenv(parsersup.WorkerModeEnv); mode != "" {
		if mode == "genericcsv" {
			os.Exit(csvworker.Run(os.Getenv(csvworker.OptionsEnv), os.Stdin, os.Stdout, os.Stderr))
		}
		os.Exit(parsersup.RunWorker(mode, os.Stdin, os.Stdout))
	}
	os.Exit(m.Run())
}

var (
	migrateOnce sync.Once
	migrateErr  error
)

type flowEnv struct {
	pool    *pgxpool.Pool
	objects *objectstore.Client
	flow    *Flow
	root    string
}

func newFlowEnv(t *testing.T, workerMode string) *flowEnv {
	t.Helper()
	databaseURL := os.Getenv("MEMORY_OS_TEST_DATABASE_URL")
	endpoint := os.Getenv("MEMORY_OS_TEST_S3_ENDPOINT")
	if databaseURL == "" || endpoint == "" {
		t.Skip("MEMORY_OS_TEST_DATABASE_URL and MEMORY_OS_TEST_S3_ENDPOINT are required; skipping import flow tests")
	}
	ctx := context.Background()

	// The commit-repository package truncates the shared test database while
	// packages run in parallel, so this package provisions and uses its own
	// database. Role DDL in migration 001 is cluster-wide, so migration
	// application serializes with the other package on one advisory lock held
	// in the shared database.
	admin, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(admin.Close)
	var flowDatabaseExists bool
	if err := admin.QueryRow(ctx, "SELECT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'memory_os_importflow')").Scan(&flowDatabaseExists); err != nil {
		t.Fatal(err)
	}
	if !flowDatabaseExists {
		if _, err := admin.Exec(ctx, "CREATE DATABASE memory_os_importflow"); err != nil && !strings.Contains(err.Error(), "already exists") {
			t.Fatal(err)
		}
	}
	flowURL, err := url.Parse(databaseURL)
	if err != nil {
		t.Fatal(err)
	}
	flowURL.Path = "/memory_os_importflow"

	pool, err := pgxpool.New(ctx, flowURL.String())
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(pool.Close)
	migrateOnce.Do(func() {
		lock, err := admin.Acquire(ctx)
		if err != nil {
			migrateErr = err
			return
		}
		defer lock.Release()
		if _, err := lock.Exec(ctx, "SELECT pg_advisory_lock(730001)"); err != nil {
			migrateErr = err
			return
		}
		defer func() { _, _ = lock.Exec(ctx, "SELECT pg_advisory_unlock(730001)") }()
		for _, name := range []string{
			"001_memory_os_import_rls.sql",
			"002_memory_os_upload_authorization.sql",
			"003_memory_os_preview_domain.sql",
		} {
			payload, err := os.ReadFile(filepath.Join("..", "..", "..", "..", "infra", "postgresql", "security", name))
			if err == nil {
				_, err = pool.Exec(ctx, string(payload))
			}
			if err != nil {
				migrateErr = fmt.Errorf("apply %s: %w", name, err)
				return
			}
		}
	})
	if migrateErr != nil {
		t.Fatal(migrateErr)
	}
	if _, err := pool.Exec(ctx, `TRUNCATE TABLE
		memory_os.preview_candidate, memory_os.preview_rejection, memory_os.preview_ready,
		memory_os.upload_authorization, memory_os.import_job`); err != nil {
		t.Fatal(err)
	}
	if _, err := pool.Exec(ctx,
		`INSERT INTO memory_os.import_job (id, owner_account_id, account_epoch, state, source_surface)
		 VALUES ($1, $2, $3, 'preview_building', 'ios_files')`,
		flowJobID, flowOwner, flowEpoch); err != nil {
		t.Fatal(err)
	}

	access := os.Getenv("MEMORY_OS_TEST_S3_ACCESS_KEY")
	if access == "" {
		access = "minioadmin"
	}
	secret := os.Getenv("MEMORY_OS_TEST_S3_SECRET_KEY")
	if secret == "" {
		secret = "minioadmin"
	}
	objects, err := objectstore.New(objectstore.Config{
		Endpoint:        endpoint,
		Region:          "us-east-1",
		Bucket:          flowBucket,
		AccessKeyID:     access,
		SecretAccessKey: secret,
	})
	if err != nil {
		t.Fatal(err)
	}
	deadline := time.Now().Add(30 * time.Second)
	for {
		if err = objects.ProvisionVersionedBucket(ctx); err == nil {
			break
		}
		if time.Now().After(deadline) {
			t.Fatalf("object store never became ready: %v", err)
		}
		time.Sleep(time.Second)
	}

	workerPath, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	workerFile, err := os.Open(workerPath)
	if err != nil {
		t.Fatal(err)
	}
	defer workerFile.Close()
	hasher := sha256.New()
	if _, err := io.Copy(hasher, workerFile); err != nil {
		t.Fatal(err)
	}
	supervisor, err := parsersup.NewSupervisor(parsersup.Config{
		WorkerPath:   workerPath,
		WorkerSHA256: hex.EncodeToString(hasher.Sum(nil)),
		WorkerEnv: []string{
			parsersup.WorkerModeEnv + "=" + workerMode,
			csvworker.OptionsEnv + "=" + flowCSVOptions,
		},
		Limits: parsersup.Limits{
			AddressSpaceBytes: 1 << 46,
			CPUSeconds:        5,
			OpenFiles:         64,
			OutputBytes:       1 << 20,
			WallClock:         30 * time.Second,
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	root := filepath.Join(t.TempDir(), "spool")
	if err := os.Mkdir(root, 0o700); err != nil {
		t.Fatal(err)
	}
	manager, err := previewspool.OpenManager(root)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = manager.Close() })

	committer, err := previewcommit.NewCommitter(pool)
	if err != nil {
		t.Fatal(err)
	}
	return &flowEnv{
		pool:    pool,
		objects: objects,
		flow: &Flow{
			Objects:    objects,
			Supervisor: supervisor,
			Spool:      manager,
			Committer:  committer,
			ScratchDir: t.TempDir(),
		},
		root: root,
	}
}

func (e *flowEnv) uploadSource(t *testing.T, uploadID string, content []byte) previewspool.SealSourceBinding {
	t.Helper()
	key := "quarantine/" + flowJobID + "/" + uploadID
	digest := sha256.Sum256(content)
	checksum := hex.EncodeToString(digest[:])
	presigned, err := e.objects.PresignPut(context.Background(), upload.PresignRequest{
		ObjectKey:      key,
		ContentLength:  int64(len(content)),
		ChecksumSHA256: checksum,
		ContentType:    "text/csv",
		ExpiresAt:      time.Now().Add(5 * time.Minute),
	})
	if err != nil {
		t.Fatal(err)
	}
	request, err := http.NewRequest(http.MethodPut, presigned.URL, bytes.NewReader(content))
	if err != nil {
		t.Fatal(err)
	}
	request.ContentLength = int64(len(content))
	for name, value := range presigned.RequiredHeaders {
		if name != "Content-Length" {
			request.Header.Set(name, value)
		}
	}
	response, err := http.DefaultClient.Do(request)
	if err != nil {
		t.Fatal(err)
	}
	_, _ = io.Copy(io.Discard, response.Body)
	_ = response.Body.Close()
	if response.StatusCode != http.StatusOK {
		t.Fatalf("source upload status %d", response.StatusCode)
	}
	metadata, err := e.objects.HeadObject(context.Background(), key)
	if err != nil {
		t.Fatal(err)
	}
	return previewspool.SealSourceBinding{
		ObjectKey:       key,
		ObjectVersionID: metadata.VersionID,
		ContentLength:   int64(len(content)),
		ChecksumSHA256:  checksum,
	}
}

func flowRequest(spoolID string, previewID string, source previewspool.SealSourceBinding, now time.Time) Request {
	return Request{
		SpoolID:   spoolID,
		PreviewID: previewID,
		Seal: previewspool.SealInput{
			JobID:          flowJobID,
			OwnerAccountID: flowOwner,
			AccountEpoch:   flowEpoch,
			Source:         source,
			Adapter: previewspool.SealAdapterBinding{
				AdapterID:      "generic-csv",
				AdapterVersion: "1.0.0",
				ArtifactSHA256: strings.Repeat("b", 64),
			},
			OptionsSHA256: flowOptionsSHA256(),
			CreatedAt:     now.Add(-time.Minute),
			ExpiresAt:     now.Add(time.Hour),
		},
	}
}

const flowCSVOptions = `{"titleColumn":"title","dateColumn":"date","dateLayout":"2006-01-02","urlColumn":"url","textColumn":"text"}`

// flowSource is a real Generic CSV source: the header is physical row 1, rows
// 2 and 4 become candidates, and row 3 (empty title) becomes a rejection.
var flowSource = []byte(`title,date,url,text
summer trip,2026-07-21,https://example.com/trip,three temples
,,,missing title row
ramen log,,,
`)

// flowOptionsSHA256 binds the seal to the exact normalized adapter options the
// worker will run with, via the same digest the production binding uses.
func flowOptionsSHA256() string {
	options, err := csvworker.ParserOptions(flowCSVOptions)
	if err != nil {
		panic(err)
	}
	_, digest, err := genericcsv.NormalizeAndDigestOptions(options)
	if err != nil {
		panic(err)
	}
	return digest
}

func assertNothingImported(t *testing.T, pool *pgxpool.Pool) {
	t.Helper()
	var previews int
	var jobState string
	if err := pool.QueryRow(context.Background(), "SELECT count(*) FROM memory_os.preview_ready").Scan(&previews); err != nil {
		t.Fatal(err)
	}
	if err := pool.QueryRow(context.Background(), "SELECT state FROM memory_os.import_job WHERE id = $1", flowJobID).Scan(&jobState); err != nil {
		t.Fatal(err)
	}
	if previews != 0 || jobState != "preview_building" {
		t.Fatalf("failed flow left durable state: previews=%d job=%s", previews, jobState)
	}
}

func TestFlowImportsEndToEnd(t *testing.T) {
	env := newFlowEnv(t, "genericcsv")
	now := time.Now().UTC()
	source := env.uploadSource(t, "upl_01J00000000000000000000000", flowSource)
	result, err := env.flow.Run(context.Background(), flowRequest("spl_01J00000000000000000000000", "prv_flowhappy001", source, now), now)
	if err != nil {
		t.Fatal(err)
	}
	if result.Commit.AlreadyCommitted || result.Verified.Evidence.Accepted.RecordCount != 2 || result.Verified.Evidence.Rejected.RecordCount != 1 {
		t.Fatalf("unexpected flow result: %+v", result)
	}

	ctx := context.Background()
	var jobState, versionID string
	var candidates, rejections int
	if err := env.pool.QueryRow(ctx, "SELECT state FROM memory_os.import_job WHERE id = $1", flowJobID).Scan(&jobState); err != nil {
		t.Fatal(err)
	}
	if err := env.pool.QueryRow(ctx,
		"SELECT source_object_version_id FROM memory_os.preview_ready WHERE id = $1", "prv_flowhappy001").Scan(&versionID); err != nil {
		t.Fatal(err)
	}
	if err := env.pool.QueryRow(ctx, "SELECT count(*) FROM memory_os.preview_candidate").Scan(&candidates); err != nil {
		t.Fatal(err)
	}
	if err := env.pool.QueryRow(ctx, "SELECT count(*) FROM memory_os.preview_rejection").Scan(&rejections); err != nil {
		t.Fatal(err)
	}
	if jobState != "preview_ready" || versionID != source.ObjectVersionID || candidates != 2 || rejections != 1 {
		t.Fatalf("committed state mismatch: job=%s version=%s candidates=%d rejections=%d", jobState, versionID, candidates, rejections)
	}
}

func TestFlowIsIdempotentAcrossReparses(t *testing.T) {
	env := newFlowEnv(t, "genericcsv")
	now := time.Now().UTC()
	source := env.uploadSource(t, "upl_01J00000000000000000000001", flowSource)
	first, err := env.flow.Run(context.Background(), flowRequest("spl_01J00000000000000000000001", "prv_flowfirst001", source, now), now)
	if err != nil {
		t.Fatal(err)
	}
	again, err := env.flow.Run(context.Background(), flowRequest("spl_01J00000000000000000000002", "prv_flowsecond01", source, now), now)
	if err != nil {
		t.Fatal(err)
	}
	if !again.Commit.AlreadyCommitted || again.Commit.PreviewID != first.Commit.PreviewID {
		t.Fatalf("re-parse was not idempotent: %+v", again.Commit)
	}
	var previews int
	if err := env.pool.QueryRow(context.Background(), "SELECT count(*) FROM memory_os.preview_ready").Scan(&previews); err != nil {
		t.Fatal(err)
	}
	if previews != 1 {
		t.Fatalf("idempotent retry duplicated Previews: %d", previews)
	}
}

func TestFlowRejectsCurrentVersionDrift(t *testing.T) {
	env := newFlowEnv(t, "genericcsv")
	now := time.Now().UTC()
	source := env.uploadSource(t, "upl_01J00000000000000000000002", flowSource)
	_ = env.uploadSource(t, "upl_01J00000000000000000000002", append([]byte("a:{\"sourceRow\":1,\"title\":\"changed\"}\n"), nil...))
	_, err := env.flow.Run(context.Background(), flowRequest("spl_01J00000000000000000000003", "prv_flowdrift001", source, now), now)
	if !errors.Is(err, ErrSourceBindingMismatch) {
		t.Fatalf("drifted object was imported: %v", err)
	}
	assertNothingImported(t, env.pool)
	assertNoSpoolEntry(t, env.root, "spl_01J00000000000000000000003")
}

func TestFlowRejectsChecksumMismatch(t *testing.T) {
	env := newFlowEnv(t, "genericcsv")
	now := time.Now().UTC()
	source := env.uploadSource(t, "upl_01J00000000000000000000003", flowSource)
	source.ChecksumSHA256 = strings.Repeat("0", 64)
	_, err := env.flow.Run(context.Background(), flowRequest("spl_01J00000000000000000000004", "prv_flowsum00001", source, now), now)
	if !errors.Is(err, ErrSourceBindingMismatch) {
		t.Fatalf("checksum mismatch was imported: %v", err)
	}
	assertNothingImported(t, env.pool)
}

func TestFlowCleansUpWorkerFailure(t *testing.T) {
	env := newFlowEnv(t, "spin")
	now := time.Now().UTC()
	source := env.uploadSource(t, "upl_01J00000000000000000000004", flowSource)
	_, err := env.flow.Run(context.Background(), flowRequest("spl_01J00000000000000000000005", "prv_flowspin0001", source, now), now)
	if !errors.Is(err, parsersup.ErrWorkerFailed) {
		t.Fatalf("worker failure did not fail the flow: %v", err)
	}
	assertNothingImported(t, env.pool)
	assertNoSpoolEntry(t, env.root, "spl_01J00000000000000000000005")
}

func TestFlowRejectsInvalidCanonicalRecords(t *testing.T) {
	env := newFlowEnv(t, "parse")
	now := time.Now().UTC()
	badSource := []byte(`a:{"title":"not-a-canonical-record"}
`)
	source := env.uploadSource(t, "upl_01J00000000000000000000005", badSource)
	_, err := env.flow.Run(context.Background(), flowRequest("spl_01J00000000000000000000006", "prv_flowbadrec01", source, now), now)
	if !errors.Is(err, ErrCanonicalRecordInvalid) {
		t.Fatalf("invalid canonical record was committed: %v", err)
	}
	assertNothingImported(t, env.pool)
}

func assertNoSpoolEntry(t *testing.T, root string, spoolID string) {
	t.Helper()
	if _, err := os.Lstat(filepath.Join(root, spoolID)); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("failed flow left spool residue for %s: %v", spoolID, err)
	}
}
