package previewcommit

import (
	"context"
	"errors"
	"fmt"
	neturl "net/url"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

var (
	migrateOnce sync.Once
	migrateErr  error
)

func testPool(t *testing.T) *pgxpool.Pool {
	t.Helper()
	url := os.Getenv("MEMORY_OS_TEST_DATABASE_URL")
	if url == "" {
		t.Skip("MEMORY_OS_TEST_DATABASE_URL is not set; skipping live PostgreSQL commit tests")
	}
	pool, err := pgxpool.New(context.Background(), url)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(pool.Close)
	migrateOnce.Do(func() { migrateErr = applyMigrations(pool) })
	if migrateErr != nil {
		t.Fatal(migrateErr)
	}
	resetFixtures(t, pool)
	return pool
}

func applyMigrations(pool *pgxpool.Pool) error {
	ctx := context.Background()
	// Migration DDL touches cluster-wide role catalogs while advisory locks
	// are scoped per database, so every applier (this suite, importflow,
	// importcli) serializes on one lock held in the maintenance database.
	lockURL, err := neturl.Parse(os.Getenv("MEMORY_OS_TEST_DATABASE_URL"))
	if err != nil {
		return err
	}
	lockURL.Path = "/postgres"
	lockPool, err := pgxpool.New(ctx, lockURL.String())
	if err != nil {
		return err
	}
	defer lockPool.Close()
	lock, err := lockPool.Acquire(ctx)
	if err != nil {
		return err
	}
	defer lock.Release()
	if _, err := lock.Exec(ctx, "SELECT pg_advisory_lock(730001)"); err != nil {
		return err
	}
	defer func() { _, _ = lock.Exec(ctx, "SELECT pg_advisory_unlock(730001)") }()
	for _, name := range []string{
		"001_memory_os_import_rls.sql",
		"002_memory_os_account_control.sql",
		"002_memory_os_upload_authorization.sql",
		"003_memory_os_preview_domain.sql",
		"004_memory_os_account_session.sql",
		"005_memory_os_apply_memory.sql",
		"006_memory_os_deletion_fencing.sql",
		"007_memory_os_app_login.sql",
		"008_memory_os_deletion_runtime.sql",
		"009_memory_os_deletion_visibility.sql",
		"010_memory_os_apple_identity.sql",
	} {
		payload, err := os.ReadFile(filepath.Join("..", "..", "..", "..", "infra", "postgresql", "security", name))
		if err != nil {
			return err
		}
		if _, err := pool.Exec(ctx, string(payload)); err != nil {
			return fmt.Errorf("apply %s: %w", name, err)
		}
	}
	return nil
}

func resetFixtures(t *testing.T, pool *pgxpool.Pool) {
	t.Helper()
	ctx := context.Background()
	if _, err := pool.Exec(ctx, `TRUNCATE TABLE
		memory_os.preview_candidate,
		memory_os.preview_rejection,
		memory_os.preview_ready,
		memory_os.upload_authorization,
		memory_os.import_job`); err != nil {
		t.Fatal(err)
	}
	// Deletion fencing requires an active account_control row at this epoch.
	if _, err := pool.Exec(ctx,
		`INSERT INTO memory_os.account_control (account_id, account_epoch, state)
		 VALUES ($1, $2, 'active')
		 ON CONFLICT (account_id) DO UPDATE
		 SET account_epoch = EXCLUDED.account_epoch, state = 'active',
		     deletion_started_at = NULL, deletion_completed_at = NULL`,
		fixtureOwner, fixtureEpoch); err != nil {
		t.Fatal(err)
	}
	if _, err := pool.Exec(ctx,
		`INSERT INTO memory_os.import_job (id, owner_account_id, account_epoch, state, source_surface)
		 VALUES ($1, $2, $3, $4, $5)`,
		fixtureJobID, fixtureOwner, fixtureEpoch, requiredJobState, "ios_files",
	); err != nil {
		t.Fatal(err)
	}
}

func commitNow() time.Time {
	return verifiedFixture().CreatedAt.Add(time.Hour)
}

func commitRequestFixture(previewID string) CommitRequest {
	return CommitRequest{
		PreviewID: previewID,
		Verified:  verifiedFixture(),
		Candidates: []CandidateRow{
			{Ordinal: 1, SourceRow: 1, RecordSHA256: strings.Repeat("1", 64), CanonicalRecord: []byte(`{"title":"one"}`)},
			{Ordinal: 2, SourceRow: 3, RecordSHA256: strings.Repeat("2", 64), CanonicalRecord: []byte(`{"title":"two"}`)},
		},
		Rejections: []RejectionRow{
			{Ordinal: 1, SourceRow: 2, IssueCodes: []string{"IMPORT_ROW_EMPTY"}},
		},
	}
}

func assertNothingCommitted(t *testing.T, pool *pgxpool.Pool) {
	t.Helper()
	ctx := context.Background()
	var previews, candidates, rejections int
	var jobState string
	if err := pool.QueryRow(ctx, "SELECT count(*) FROM memory_os.preview_ready").Scan(&previews); err != nil {
		t.Fatal(err)
	}
	if err := pool.QueryRow(ctx, "SELECT count(*) FROM memory_os.preview_candidate").Scan(&candidates); err != nil {
		t.Fatal(err)
	}
	if err := pool.QueryRow(ctx, "SELECT count(*) FROM memory_os.preview_rejection").Scan(&rejections); err != nil {
		t.Fatal(err)
	}
	if err := pool.QueryRow(ctx, "SELECT state FROM memory_os.import_job WHERE id = $1", fixtureJobID).Scan(&jobState); err != nil {
		t.Fatal(err)
	}
	if previews != 0 || candidates != 0 || rejections != 0 || jobState != requiredJobState {
		t.Fatalf("transaction was not fully rolled back: previews=%d candidates=%d rejections=%d job=%s", previews, candidates, rejections, jobState)
	}
}

func TestCommitPersistsCompletePreviewAtomically(t *testing.T) {
	pool := testPool(t)
	committer, err := NewCommitter(pool)
	if err != nil {
		t.Fatal(err)
	}
	request := commitRequestFixture("prv_commitok0001")
	result, err := committer.Commit(context.Background(), request, commitNow())
	if err != nil {
		t.Fatal(err)
	}
	if result.AlreadyCommitted || result.PreviewID != "prv_commitok0001" || result.CommitKey != DeriveCommitKey(request.Verified) {
		t.Fatalf("unexpected commit result: %+v", result)
	}
	ctx := context.Background()
	var jobState, commitKey, previewHash string
	var candidates, rejections int
	if err := pool.QueryRow(ctx, "SELECT state FROM memory_os.import_job WHERE id = $1", fixtureJobID).Scan(&jobState); err != nil {
		t.Fatal(err)
	}
	if err := pool.QueryRow(ctx, "SELECT commit_key, preview_hash_sha256 FROM memory_os.preview_ready WHERE id = $1", result.PreviewID).Scan(&commitKey, &previewHash); err != nil {
		t.Fatal(err)
	}
	if err := pool.QueryRow(ctx, "SELECT count(*) FROM memory_os.preview_candidate WHERE preview_id = $1", result.PreviewID).Scan(&candidates); err != nil {
		t.Fatal(err)
	}
	if err := pool.QueryRow(ctx, "SELECT count(*) FROM memory_os.preview_rejection WHERE preview_id = $1", result.PreviewID).Scan(&rejections); err != nil {
		t.Fatal(err)
	}
	if jobState != readyJobState || commitKey != result.CommitKey || previewHash != result.PreviewHash || candidates != 2 || rejections != 1 {
		t.Fatalf("committed state mismatch: job=%s candidates=%d rejections=%d", jobState, candidates, rejections)
	}
}

func TestCommitDuplicateRetryReturnsExistingPreview(t *testing.T) {
	pool := testPool(t)
	committer, _ := NewCommitter(pool)
	first, err := committer.Commit(context.Background(), commitRequestFixture("prv_retryfirst01"), commitNow())
	if err != nil {
		t.Fatal(err)
	}

	retry := commitRequestFixture("prv_retrysecond1")
	retry.Verified.SpoolID = "spl_01J00000000000000000000001"
	again, err := committer.Commit(context.Background(), retry, commitNow())
	if err != nil {
		t.Fatal(err)
	}
	if !again.AlreadyCommitted || again.PreviewID != first.PreviewID || again.CommitKey != first.CommitKey || again.PreviewHash != first.PreviewHash {
		t.Fatalf("retry did not return the committed Preview: %+v", again)
	}
	var previews int
	if err := pool.QueryRow(context.Background(), "SELECT count(*) FROM memory_os.preview_ready").Scan(&previews); err != nil {
		t.Fatal(err)
	}
	if previews != 1 {
		t.Fatalf("retry duplicated the Preview: %d rows", previews)
	}
}

func TestCommitConflictingRetryRejects(t *testing.T) {
	pool := testPool(t)
	committer, _ := NewCommitter(pool)
	if _, err := committer.Commit(context.Background(), commitRequestFixture("prv_conflict0001"), commitNow()); err != nil {
		t.Fatal(err)
	}
	conflicting := commitRequestFixture("prv_conflict0002")
	conflicting.Verified.OptionsSHA256 = strings.Repeat("0", 64)
	if _, err := committer.Commit(context.Background(), conflicting, commitNow()); !errors.Is(err, ErrCommitConflict) {
		t.Fatalf("conflicting retry was accepted: %v", err)
	}
}

func TestCommitRollsBackOnUnsafeRejectionRows(t *testing.T) {
	pool := testPool(t)
	committer, _ := NewCommitter(pool)
	request := commitRequestFixture("prv_unsafecode01")
	request.Rejections[0].IssueCodes = []string{"user@example.com"}
	if _, err := committer.Commit(context.Background(), request, commitNow()); err == nil {
		t.Fatal("free-form rejection code was committed")
	}
	assertNothingCommitted(t, pool)
}

func TestCommitRollsBackOnOrdinalGap(t *testing.T) {
	pool := testPool(t)
	committer, _ := NewCommitter(pool)
	request := commitRequestFixture("prv_ordinalgap01")
	request.Candidates[1].Ordinal = 3
	if _, err := committer.Commit(context.Background(), request, commitNow()); !errors.Is(err, ErrIncompletePreview) {
		t.Fatalf("ordinal gap was committed: %v", err)
	}
	assertNothingCommitted(t, pool)
}

func TestCommitRejectsStaleBindings(t *testing.T) {
	pool := testPool(t)
	committer, _ := NewCommitter(pool)
	ctx := context.Background()

	missing := commitRequestFixture("prv_missingjob01")
	missing.Verified.JobID = "job_01J000000000000000000000001"
	missing.Verified.Source.ObjectKey = "quarantine/job_01J000000000000000000000001/upl_01J00000000000000000000000"
	if _, err := committer.Commit(ctx, missing, commitNow()); !errors.Is(err, ErrJobBindingMismatch) {
		t.Fatalf("missing job was accepted: %v", err)
	}

	if _, err := pool.Exec(ctx, "UPDATE memory_os.import_job SET account_epoch = 8 WHERE id = $1", fixtureJobID); err != nil {
		t.Fatal(err)
	}
	if _, err := committer.Commit(ctx, commitRequestFixture("prv_staleepoch01"), commitNow()); !errors.Is(err, ErrJobBindingMismatch) {
		t.Fatalf("stale-epoch job was accepted: %v", err)
	}

	if _, err := pool.Exec(ctx, "UPDATE memory_os.import_job SET account_epoch = 7, state = 'created' WHERE id = $1", fixtureJobID); err != nil {
		t.Fatal(err)
	}
	if _, err := committer.Commit(ctx, commitRequestFixture("prv_wrongstate01"), commitNow()); !errors.Is(err, ErrJobStateInvalid) {
		t.Fatalf("wrong job state was accepted: %v", err)
	}
}

func TestCommitValidatesInput(t *testing.T) {
	pool := testPool(t)
	if _, err := NewCommitter(nil); !errors.Is(err, ErrInvalidCommitInput) {
		t.Fatalf("nil pool was accepted: %v", err)
	}
	committer, _ := NewCommitter(pool)

	badID := commitRequestFixture("not-a-preview-id")
	if _, err := committer.Commit(context.Background(), badID, commitNow()); !errors.Is(err, ErrInvalidCommitInput) {
		t.Fatalf("invalid preview ID was accepted: %v", err)
	}

	if _, err := committer.Commit(context.Background(), commitRequestFixture("prv_zeroclock001"), time.Time{}); !errors.Is(err, ErrInvalidCommitInput) {
		t.Fatalf("zero clock was accepted: %v", err)
	}

	short := commitRequestFixture("prv_shortrows001")
	short.Candidates = short.Candidates[:1]
	if _, err := committer.Commit(context.Background(), short, commitNow()); !errors.Is(err, ErrRowEvidenceMismatch) {
		t.Fatalf("row/evidence mismatch was accepted: %v", err)
	}

	expired := commitRequestFixture("prv_expired00001")
	if _, err := committer.Commit(context.Background(), expired, expired.Verified.ExpiresAt); !errors.Is(err, ErrSpoolExpired) {
		t.Fatalf("expired spool was accepted: %v", err)
	}
	assertNothingCommitted(t, pool)
}
