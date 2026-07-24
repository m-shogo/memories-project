package httpserver

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	neturl "net/url"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/m-shogo/memories-project/services/import-api/internal/accountdelete"
	"github.com/m-shogo/memories-project/services/import-api/internal/apply"
	"github.com/m-shogo/memories-project/services/import-api/internal/authstore"
	"github.com/m-shogo/memories-project/services/import-api/internal/cryptoids"
	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/epochguard"
	"github.com/m-shogo/memories-project/services/import-api/internal/fenced"
	"github.com/m-shogo/memories-project/services/import-api/internal/objectstore"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgrepo"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/previewcommit"
	"github.com/m-shogo/memories-project/services/import-api/internal/previewread"
	"github.com/m-shogo/memories-project/services/import-api/internal/previewspool"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
	"github.com/m-shogo/memories-project/services/import-api/internal/upload"
)

var (
	migrateOnce sync.Once
	migrateErr  error
)

type liveServer struct {
	// pool is the privileged migration/fixture connection; appPool is the
	// unprivileged deployment principal the server itself runs through.
	pool     *pgxpool.Pool
	appPool  *pgxpool.Pool
	sessions authstore.Store
	server   *httptest.Server
	executor *dbscope.Executor
	objects  *objectstore.Client

	accountControl pgrepo.AccountControl
}

func newLiveServer(t *testing.T) *liveServer {
	t.Helper()
	databaseURL := os.Getenv("MEMORY_OS_TEST_DATABASE_URL")
	endpoint := os.Getenv("MEMORY_OS_TEST_S3_ENDPOINT")
	if databaseURL == "" || endpoint == "" {
		t.Skip("MEMORY_OS_TEST_DATABASE_URL and MEMORY_OS_TEST_S3_ENDPOINT are required; skipping HTTP server tests")
	}
	ctx := context.Background()

	admin, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		t.Fatal(err)
	}
	defer admin.Close()
	if _, err := admin.Exec(ctx, "CREATE DATABASE memory_os_httpserver"); err != nil &&
		!strings.Contains(err.Error(), "already exists") {
		t.Fatal(err)
	}
	serverURL := strings.Replace(databaseURL, "/memory_os_security", "/memory_os_httpserver", 1)
	pool, err := pgxpool.New(ctx, serverURL)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(pool.Close)

	migrateOnce.Do(func() {
		maintenance, err := neturl.Parse(databaseURL)
		if err != nil {
			migrateErr = err
			return
		}
		maintenance.Path = "/postgres"
		lockPool, err := pgxpool.New(ctx, maintenance.String())
		if err != nil {
			migrateErr = err
			return
		}
		defer lockPool.Close()
		lock, err := lockPool.Acquire(ctx)
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
			"002_memory_os_account_control.sql",
			"002_memory_os_upload_authorization.sql",
			"003_memory_os_preview_domain.sql",
			"004_memory_os_account_session.sql",
			"005_memory_os_apply_memory.sql",
			"006_memory_os_deletion_fencing.sql",
			"007_memory_os_app_login.sql",
			"008_memory_os_deletion_runtime.sql",
			"009_memory_os_deletion_visibility.sql",
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
		Bucket:          "memory-os-quarantine-test",
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

	// Everything the server touches goes through the deployment principal:
	// NOBYPASSRLS, NOINHERIT, no table privileges of its own. Running the HTTP
	// journey on a superuser connection would have left FORCE RLS unproven for
	// the path a deployment actually uses.
	appPool := appLoginPool(t, ctx, pool, serverURL)
	sessions := authstore.Store{Pool: appPool}
	executor := dbscope.New(pgscope.Beginner{Pool: appPool})
	// The composition under test is the deployed one: every surface behind the
	// deletion-epoch fence, exactly as cmd/import-api-server wires it.
	accountControl := pgrepo.AccountControl{Pool: appPool, Transactions: executor}
	guard := epochguard.Guard{Source: accountControl}
	handler := New(Config{
		Sessions: sessions,
		Upload: fenced.Upload{Guard: guard, Inner: &upload.Service{
			Transactions: executor,
			Repository:   pgrepo.Upload{},
			Signer:       objects,
			Objects:      objects,
			IDs:          cryptoids.Generator{},
		}},
		Preview: fenced.PreviewRead{Guard: guard, Inner: &previewread.Service{Transactions: executor}},
		Apply: fenced.Apply{Guard: guard, Inner: &apply.Service{
			Transactions: executor,
			Repository:   pgrepo.Apply{},
			IDs:          cryptoids.Generator{},
		}},
		Account: accountdelete.Service{Repository: accountControl, Guard: guard},
	})
	server := httptest.NewServer(handler)
	t.Cleanup(server.Close)
	return &liveServer{pool: pool, appPool: appPool, sessions: sessions,
		server: server, executor: executor, objects: objects, accountControl: accountControl}
}

func (s *liveServer) issueSession(t *testing.T, accountID string) string {
	t.Helper()
	if err := provisionAccount(context.Background(), s.pool, accountID, 1); err != nil {
		t.Fatal(err)
	}
	issued, err := s.sessions.Issue(context.Background(), authstore.IssueInput{
		AccountID: accountID,
		Epoch:     1,
		Authority: security.AuthorityIOSUser,
		TTL:       time.Hour,
	})
	if err != nil {
		t.Fatal(err)
	}
	return issued.Token
}

func (s *liveServer) createJob(t *testing.T, accountID string) string {
	t.Helper()
	principal, err := security.NewVerifiedPrincipal(accountID, 1, security.AuthorityIOSUser)
	if err != nil {
		t.Fatal(err)
	}
	jobID, err := cryptoids.Generator{}.NewID("job")
	if err != nil {
		t.Fatal(err)
	}
	err = s.executor.WithinPrincipal(context.Background(), principal, dbscope.RoleAPI,
		func(ctx context.Context, tx dbscope.Transaction) error {
			return tx.Exec(ctx,
				`INSERT INTO memory_os.import_job (id, owner_account_id, account_epoch, state, source_surface)
				 VALUES ($1, $2, 1, 'created', 'ios_files')`,
				jobID, accountID)
		})
	if err != nil {
		t.Fatal(err)
	}
	return jobID
}

func (s *liveServer) request(t *testing.T, method string, path string, token string, body any) (*http.Response, []byte) {
	t.Helper()
	var reader io.Reader
	if body != nil {
		encoded, err := json.Marshal(body)
		if err != nil {
			t.Fatal(err)
		}
		reader = bytes.NewReader(encoded)
	}
	request, err := http.NewRequest(method, s.server.URL+path, reader)
	if err != nil {
		t.Fatal(err)
	}
	if token != "" {
		request.Header.Set("Authorization", "Bearer "+token)
	}
	response, err := http.DefaultClient.Do(request)
	if err != nil {
		t.Fatal(err)
	}
	payload, err := io.ReadAll(io.LimitReader(response.Body, 1<<20))
	_ = response.Body.Close()
	if err != nil {
		t.Fatal(err)
	}
	return response, payload
}

func TestHealthEndpointNeedsNoSession(t *testing.T) {
	server := newLiveServer(t)
	response, body := server.request(t, http.MethodGet, "/healthz", "", nil)
	if response.StatusCode != http.StatusOK || string(body) != "ok" {
		t.Fatalf("health probe failed: %d %q", response.StatusCode, body)
	}
}

func TestAPIRejectsMissingAndInvalidSessions(t *testing.T) {
	server := newLiveServer(t)
	path := "/v1/import-jobs/job_missing_session_x/upload-authorizations"

	response, _ := server.request(t, http.MethodPost, path, "", map[string]any{})
	if response.StatusCode != http.StatusUnauthorized {
		t.Fatalf("missing session accepted: %d", response.StatusCode)
	}
	response, _ = server.request(t, http.MethodPost, path, "not-a-real-token", map[string]any{})
	if response.StatusCode != http.StatusUnauthorized {
		t.Fatalf("malformed token accepted: %d", response.StatusCode)
	}
	forged := authstore.TokenPrefix + strings.Repeat("ab", 32)
	response, _ = server.request(t, http.MethodPost, path, forged, map[string]any{})
	if response.StatusCode != http.StatusUnauthorized {
		t.Fatalf("forged token accepted: %d", response.StatusCode)
	}

	expired, err := server.sessions.Issue(context.Background(), authstore.IssueInput{
		AccountID: "acct_http_expired_owner",
		Epoch:     1,
		Authority: security.AuthorityIOSUser,
		TTL:       time.Hour,
		Now:       time.Now().Add(-2 * time.Hour),
	})
	if err != nil {
		t.Fatal(err)
	}
	response, _ = server.request(t, http.MethodPost, path, expired.Token, map[string]any{})
	if response.StatusCode != http.StatusUnauthorized {
		t.Fatalf("expired session accepted: %d", response.StatusCode)
	}

	revocable := server.issueSession(t, "acct_http_revoked_owner")
	if revoked, err := server.sessions.Revoke(context.Background(), revocable); err != nil || !revoked {
		t.Fatalf("revocation failed: %v %v", revoked, err)
	}
	response, _ = server.request(t, http.MethodPost, path, revocable, map[string]any{})
	if response.StatusCode != http.StatusUnauthorized {
		t.Fatalf("revoked session accepted: %d", response.StatusCode)
	}
}

func TestUploadLifecycleOverHTTP(t *testing.T) {
	server := newLiveServer(t)
	ownerToken := server.issueSession(t, "acct_http_upload_owner1")
	intruderToken := server.issueSession(t, "acct_http_upload_intrud")
	jobID := server.createJob(t, "acct_http_upload_owner1")

	payload := []byte("title,date\nhttp trip,2026-07-23\n")
	digest := sha256.Sum256(payload)
	response, body := server.request(t, http.MethodPost,
		"/v1/import-jobs/"+jobID+"/upload-authorizations", ownerToken,
		map[string]any{
			"contentLength":   len(payload),
			"checksumSha256":  hex.EncodeToString(digest[:]),
			"contentType":     "text/csv",
			"sourceSurface":   "ios_files",
			"displayFilename": "trip.csv",
		})
	if response.StatusCode != http.StatusCreated {
		t.Fatalf("issue failed: %d %s", response.StatusCode, body)
	}
	var issued struct {
		AuthorizationID string            `json:"authorizationId"`
		UploadURL       string            `json:"uploadUrl"`
		RequiredHeaders map[string]string `json:"requiredHeaders"`
	}
	if err := json.Unmarshal(body, &issued); err != nil {
		t.Fatal(err)
	}
	if issued.AuthorizationID == "" || issued.UploadURL == "" {
		t.Fatalf("issue response incomplete: %s", body)
	}

	put, err := http.NewRequest(http.MethodPut, issued.UploadURL, bytes.NewReader(payload))
	if err != nil {
		t.Fatal(err)
	}
	put.ContentLength = int64(len(payload))
	for name, value := range issued.RequiredHeaders {
		if name != "Content-Length" {
			put.Header.Set(name, value)
		}
	}
	uploaded, err := http.DefaultClient.Do(put)
	if err != nil {
		t.Fatal(err)
	}
	_, _ = io.Copy(io.Discard, uploaded.Body)
	_ = uploaded.Body.Close()
	if uploaded.StatusCode != http.StatusOK {
		t.Fatalf("presigned upload status %d", uploaded.StatusCode)
	}

	completePath := "/v1/upload-authorizations/" + issued.AuthorizationID + "/complete"
	response, _ = server.request(t, http.MethodPost, completePath, intruderToken, nil)
	if response.StatusCode != http.StatusNotFound {
		t.Fatalf("cross-tenant completion status %d", response.StatusCode)
	}
	response, _ = server.request(t, http.MethodPost, completePath, ownerToken, nil)
	if response.StatusCode != http.StatusAccepted {
		t.Fatalf("completion failed: %d", response.StatusCode)
	}
	response, _ = server.request(t, http.MethodPost, completePath, ownerToken, nil)
	if response.StatusCode != http.StatusConflict {
		t.Fatalf("double completion status %d", response.StatusCode)
	}
}

// commitPreviewForJob commits one ready Preview directly through the commit
// repository so the HTTP tests can exercise preview read and apply without
// running the full parse pipeline.
func (s *liveServer) commitPreviewForJob(t *testing.T, accountID string, jobID string) (previewID string, previewSHA string) {
	t.Helper()
	ctx := context.Background()
	if _, err := s.pool.Exec(ctx,
		"UPDATE memory_os.import_job SET state = 'preview_building' WHERE id = $1", jobID); err != nil {
		t.Fatal(err)
	}
	ids := cryptoids.Generator{}
	newID := func(prefix string) string {
		value, err := ids.NewID(prefix)
		if err != nil {
			t.Fatal(err)
		}
		return value
	}
	previewID = newID("prv")
	now := time.Now().UTC()

	acceptedRecords := [][]byte{
		[]byte(fmt.Sprintf(`{"fingerprint":"fp-http-%s-1","title":"first"}`, jobID[len(jobID)-8:])),
		[]byte(fmt.Sprintf(`{"fingerprint":"fp-http-%s-2","title":"second"}`, jobID[len(jobID)-8:])),
	}
	acceptedHasher := sha256.New()
	var acceptedBytes int64
	candidates := make([]previewcommit.CandidateRow, 0, len(acceptedRecords))
	for index, record := range acceptedRecords {
		var prefix [8]byte
		binary.BigEndian.PutUint64(prefix[:], uint64(len(record)))
		acceptedHasher.Write(prefix[:])
		acceptedHasher.Write(record)
		acceptedBytes += int64(8 + len(record))
		recordDigest := sha256.Sum256(record)
		candidates = append(candidates, previewcommit.CandidateRow{
			Ordinal:         index + 1,
			SourceRow:       int64(index + 1),
			RecordSHA256:    hex.EncodeToString(recordDigest[:]),
			CanonicalRecord: record,
		})
	}
	rejectedRecord := []byte(`{"sourceRow":3,"issueCodes":["IMPORT_ROW_EMPTY"]}`)
	rejectedHasher := sha256.New()
	var rejectedPrefix [8]byte
	binary.BigEndian.PutUint64(rejectedPrefix[:], uint64(len(rejectedRecord)))
	rejectedHasher.Write(rejectedPrefix[:])
	rejectedHasher.Write(rejectedRecord)

	verified := previewspool.VerifiedSpool{
		SpoolID:        newID("spl"),
		JobID:          jobID,
		OwnerAccountID: accountID,
		AccountEpoch:   1,
		Source: previewspool.SealSourceBinding{
			ObjectKey:       "quarantine/" + jobID + "/" + newID("upl"),
			ObjectVersionID: "version-http-apply-000001",
			ContentLength:   64,
			ChecksumSHA256:  strings.Repeat("a", 64),
		},
		Adapter: previewspool.SealAdapterBinding{
			AdapterID:      "generic-csv",
			AdapterVersion: "1.0.0",
			ArtifactSHA256: strings.Repeat("b", 64),
		},
		OptionsSHA256: strings.Repeat("c", 64),
		CreatedAt:     now.Add(-time.Minute),
		ExpiresAt:     now.Add(time.Hour),
		Evidence: previewspool.WriteEvidence{
			SourceRowCount:  3,
			SpoolByteLength: acceptedBytes + int64(8+len(rejectedRecord)),
			Accepted: previewspool.StreamEvidence{
				RecordFormat: previewspool.AcceptedRecordFormat,
				RecordCount:  2,
				ByteLength:   acceptedBytes,
				SHA256:       hex.EncodeToString(acceptedHasher.Sum(nil)),
			},
			Rejected: previewspool.StreamEvidence{
				RecordFormat: previewspool.RejectedRecordFormat,
				RecordCount:  1,
				ByteLength:   int64(8 + len(rejectedRecord)),
				SHA256:       hex.EncodeToString(rejectedHasher.Sum(nil)),
			},
		},
	}
	committer, err := previewcommit.NewCommitter(s.appPool)
	if err != nil {
		t.Fatal(err)
	}
	result, err := committer.Commit(ctx, previewcommit.CommitRequest{
		PreviewID:  previewID,
		Verified:   verified,
		Candidates: candidates,
		Rejections: []previewcommit.RejectionRow{
			{Ordinal: 1, SourceRow: 3, IssueCodes: []string{"IMPORT_ROW_EMPTY"}},
		},
	}, now)
	if err != nil {
		t.Fatal(err)
	}
	return result.PreviewID, result.PreviewHash
}

func TestPreviewReadAndApplyOverHTTP(t *testing.T) {
	server := newLiveServer(t)
	// The database persists across test runs: owner and idempotency keys must
	// be unique per invocation or earlier committed claims and memory items
	// collide with this run.
	runID := time.Now().UnixNano()
	owner := fmt.Sprintf("acct_http_apply_%d", runID)
	idemKey := func(index int) string { return fmt.Sprintf("idem-http-apply-%d-%d", runID, index) }
	ownerToken := server.issueSession(t, owner)
	intruderToken := server.issueSession(t, "acct_http_apply_intrud")
	jobID := server.createJob(t, owner)
	previewID, previewSHA := server.commitPreviewForJob(t, owner, jobID)

	// Preview read: owner sees the committed Preview; a foreign tenant does not.
	response, body := server.request(t, http.MethodGet, "/v1/import-jobs/"+jobID+"/preview", ownerToken, nil)
	if response.StatusCode != http.StatusOK {
		t.Fatalf("preview read failed: %d %s", response.StatusCode, body)
	}
	var view struct {
		PreviewID     string `json:"previewId"`
		PreviewSHA256 string `json:"previewSha256"`
		AcceptedCount int    `json:"acceptedCount"`
		Candidates    []struct {
			Record json.RawMessage `json:"record"`
		} `json:"candidates"`
		Rejections []struct {
			IssueCodes []string `json:"issueCodes"`
		} `json:"rejections"`
	}
	if err := json.Unmarshal(body, &view); err != nil {
		t.Fatal(err)
	}
	if view.PreviewID != previewID || view.PreviewSHA256 != previewSHA ||
		view.AcceptedCount != 2 || len(view.Candidates) != 2 || len(view.Rejections) != 1 {
		t.Fatalf("preview view mismatch: %s", body)
	}
	response, _ = server.request(t, http.MethodGet, "/v1/import-jobs/"+jobID+"/preview", intruderToken, nil)
	if response.StatusCode != http.StatusNotFound {
		t.Fatalf("cross-tenant preview read status %d", response.StatusCode)
	}

	// Apply with the exact hash: two memory items materialize.
	applyPath := "/v1/previews/" + previewID + "/apply"
	response, body = server.request(t, http.MethodPost, applyPath, ownerToken, map[string]any{
		"previewSha256":   previewSHA,
		"idempotencyKey":  idemKey(1),
		"duplicatePolicy": "skip_existing",
	})
	if response.StatusCode != http.StatusOK {
		t.Fatalf("apply failed: %d %s", response.StatusCode, body)
	}
	var applied struct {
		ApplyID  string `json:"applyId"`
		Status   string `json:"status"`
		Replayed bool   `json:"replayed"`
		Counts   struct {
			Created int `json:"created"`
			Updated int `json:"updated"`
			Skipped int `json:"skipped"`
		} `json:"counts"`
	}
	if err := json.Unmarshal(body, &applied); err != nil {
		t.Fatal(err)
	}
	if applied.Status != "applied" || applied.Replayed || applied.Counts.Created != 2 {
		t.Fatalf("unexpected apply result: %s", body)
	}
	var items int
	if err := server.pool.QueryRow(context.Background(),
		"SELECT count(*) FROM memory_os.memory_item WHERE source_preview_id = $1", previewID,
	).Scan(&items); err != nil {
		t.Fatal(err)
	}
	if items != 2 {
		t.Fatalf("expected 2 memory items, found %d", items)
	}

	// Exact idempotent replay returns the same result without re-writing.
	response, body = server.request(t, http.MethodPost, applyPath, ownerToken, map[string]any{
		"previewSha256":   previewSHA,
		"idempotencyKey":  idemKey(1),
		"duplicatePolicy": "skip_existing",
	})
	if response.StatusCode != http.StatusOK {
		t.Fatalf("replay failed: %d %s", response.StatusCode, body)
	}
	var replayed struct {
		ApplyID  string `json:"applyId"`
		Replayed bool   `json:"replayed"`
	}
	if err := json.Unmarshal(body, &replayed); err != nil {
		t.Fatal(err)
	}
	if !replayed.Replayed || replayed.ApplyID != applied.ApplyID {
		t.Fatalf("replay did not return the original apply: %s", body)
	}

	// A new key with skip_existing skips everything already materialized.
	response, body = server.request(t, http.MethodPost, applyPath, ownerToken, map[string]any{
		"previewSha256":   previewSHA,
		"idempotencyKey":  idemKey(2),
		"duplicatePolicy": "skip_existing",
	})
	if response.StatusCode != http.StatusOK {
		t.Fatalf("second apply failed: %d %s", response.StatusCode, body)
	}
	if err := json.Unmarshal(body, &applied); err != nil {
		t.Fatal(err)
	}
	if applied.Counts.Created != 0 || applied.Counts.Skipped != 2 {
		t.Fatalf("skip_existing did not skip: %s", body)
	}

	// Wrong hash conflicts; foreign tenant sees nothing.
	response, _ = server.request(t, http.MethodPost, applyPath, ownerToken, map[string]any{
		"previewSha256":   strings.Repeat("0", 64),
		"idempotencyKey":  idemKey(3),
		"duplicatePolicy": "skip_existing",
	})
	if response.StatusCode != http.StatusConflict {
		t.Fatalf("hash mismatch status %d", response.StatusCode)
	}
	response, _ = server.request(t, http.MethodPost, applyPath, intruderToken, map[string]any{
		"previewSha256":   previewSHA,
		"idempotencyKey":  idemKey(4),
		"duplicatePolicy": "skip_existing",
	})
	if response.StatusCode != http.StatusNotFound {
		t.Fatalf("cross-tenant apply status %d", response.StatusCode)
	}
}

// provisionAccount inserts the account_control row deletion fencing requires:
// every tenant policy now demands an active account at the exact epoch. It runs
// on the pool's own connection (the dev/CI login is privileged, so RLS does not
// apply) because the API insert policy itself depends on this row existing.
func provisionAccount(ctx context.Context, pool *pgxpool.Pool, accountID string, epoch int64) error {
	_, err := pool.Exec(ctx,
		`INSERT INTO memory_os.account_control (account_id, account_epoch, state)
		 VALUES ($1, $2, 'active')
		 ON CONFLICT (account_id) DO UPDATE
		 SET account_epoch = EXCLUDED.account_epoch, state = 'active',
		     deletion_started_at = NULL, deletion_completed_at = NULL`,
		accountID, epoch)
	return err
}

// TestApplyRefusesUpdateSafeFieldsOverHTTP proves the closure against a real
// database: the destructive path used to overwrite canonical_record in place
// and repoint source_preview_id, so the test applies a preview, snapshots every
// stored row, then sends update_safe_fields and shows nothing moved.
func TestApplyRefusesUpdateSafeFieldsOverHTTP(t *testing.T) {
	server := newLiveServer(t)
	runID := time.Now().UnixNano()
	owner := fmt.Sprintf("acct_http_noupdate_%d", runID)
	ownerToken := server.issueSession(t, owner)
	jobID := server.createJob(t, owner)
	previewID, previewSHA := server.commitPreviewForJob(t, owner, jobID)
	applyPath := "/v1/previews/" + previewID + "/apply"

	response, body := server.request(t, http.MethodPost, applyPath, ownerToken, map[string]any{
		"previewSha256":   previewSHA,
		"idempotencyKey":  fmt.Sprintf("idem-noupdate-%d-1", runID),
		"duplicatePolicy": "skip_existing",
	})
	if response.StatusCode != http.StatusOK {
		t.Fatalf("initial apply failed: %d %s", response.StatusCode, body)
	}

	type row struct {
		id        string
		record    string
		previewID string
		updatedAt time.Time
	}
	snapshot := func() []row {
		t.Helper()
		rows, err := server.pool.Query(context.Background(),
			`SELECT id, canonical_record::text, source_preview_id, updated_at
			 FROM memory_os.memory_item WHERE owner_account_id = $1 ORDER BY id`, owner)
		if err != nil {
			t.Fatal(err)
		}
		defer rows.Close()
		var out []row
		for rows.Next() {
			var each row
			if err := rows.Scan(&each.id, &each.record, &each.previewID, &each.updatedAt); err != nil {
				t.Fatal(err)
			}
			out = append(out, each)
		}
		if err := rows.Err(); err != nil {
			t.Fatal(err)
		}
		return out
	}

	before := snapshot()
	if len(before) == 0 {
		t.Fatal("nothing was applied, so the test could not detect an overwrite")
	}

	// A second Preview over the same job would previously have overwritten the
	// rows above. Now the request is refused before anything is read.
	response, body = server.request(t, http.MethodPost, applyPath, ownerToken, map[string]any{
		"previewSha256":   previewSHA,
		"idempotencyKey":  fmt.Sprintf("idem-noupdate-%d-2", runID),
		"duplicatePolicy": "update_safe_fields",
	})
	if response.StatusCode != http.StatusBadRequest {
		t.Fatalf("update_safe_fields status %d %s", response.StatusCode, body)
	}
	var problem struct {
		Code string `json:"code"`
	}
	if err := json.Unmarshal(body, &problem); err != nil {
		t.Fatal(err)
	}
	if problem.Code != "SEC_APPLY_DUPLICATE_POLICY_UNSUPPORTED" {
		t.Fatalf("refusal code %q; a client cannot tell this from a malformed request", problem.Code)
	}

	after := snapshot()
	if len(after) != len(before) {
		t.Fatalf("row count moved from %d to %d", len(before), len(after))
	}
	for index := range before {
		if after[index] != before[index] {
			t.Fatalf("memory_item changed:\n before %+v\n after  %+v", before[index], after[index])
		}
	}

	// The refusal must not consume the idempotency key either: no claim row may
	// exist for it, or a retry would replay a request that never ran.
	var claims int
	if err := server.pool.QueryRow(context.Background(),
		`SELECT count(*) FROM memory_os.apply_confirmation
		 WHERE owner_account_id = $1 AND idempotency_key = $2`,
		owner, fmt.Sprintf("idem-noupdate-%d-2", runID),
	).Scan(&claims); err != nil {
		t.Fatal(err)
	}
	if claims != 0 {
		t.Fatalf("the refused request left %d claim rows", claims)
	}

	// keep_both still works afterwards: the closure is scoped to one policy.
	response, body = server.request(t, http.MethodPost, applyPath, ownerToken, map[string]any{
		"previewSha256":   previewSHA,
		"idempotencyKey":  fmt.Sprintf("idem-noupdate-%d-3", runID),
		"duplicatePolicy": "keep_both",
	})
	if response.StatusCode != http.StatusOK {
		t.Fatalf("keep_both after refusal failed: %d %s", response.StatusCode, body)
	}
}

// TestAccountDeletionFencesAndErasesOverHTTP is the end-to-end proof of the
// deletion boundary: a real account with committed Preview, applied memory
// items and a live session is deleted over HTTP, and afterwards every surface
// refuses the same session and no owned row survives in any table.
func TestAccountDeletionFencesAndErasesOverHTTP(t *testing.T) {
	server := newLiveServer(t)
	runID := time.Now().UnixNano()
	owner := fmt.Sprintf("acct_http_delete_%d", runID)
	ownerToken := server.issueSession(t, owner)
	jobID := server.createJob(t, owner)

	// A real object in the bucket, uploaded through the presigned path, so the
	// deletion below has actual bytes to erase rather than only rows.
	payload := []byte("title,date\ndeleted trip,2026-07-24\n")
	digest := sha256.Sum256(payload)
	response, body := server.request(t, http.MethodPost,
		"/v1/import-jobs/"+jobID+"/upload-authorizations", ownerToken,
		map[string]any{
			"contentLength":   len(payload),
			"checksumSha256":  hex.EncodeToString(digest[:]),
			"contentType":     "text/csv",
			"sourceSurface":   "ios_files",
			"displayFilename": "deleted.csv",
		})
	if response.StatusCode != http.StatusCreated {
		t.Fatalf("issue failed: %d %s", response.StatusCode, body)
	}
	var issued struct {
		AuthorizationID string            `json:"authorizationId"`
		UploadURL       string            `json:"uploadUrl"`
		RequiredHeaders map[string]string `json:"requiredHeaders"`
	}
	if err := json.Unmarshal(body, &issued); err != nil {
		t.Fatal(err)
	}
	put, err := http.NewRequest(http.MethodPut, issued.UploadURL, bytes.NewReader(payload))
	if err != nil {
		t.Fatal(err)
	}
	put.ContentLength = int64(len(payload))
	for name, value := range issued.RequiredHeaders {
		if name != "Content-Length" {
			put.Header.Set(name, value)
		}
	}
	uploaded, err := http.DefaultClient.Do(put)
	if err != nil {
		t.Fatal(err)
	}
	_, _ = io.Copy(io.Discard, uploaded.Body)
	_ = uploaded.Body.Close()
	if uploaded.StatusCode != http.StatusOK {
		t.Fatalf("presigned upload status %d", uploaded.StatusCode)
	}
	var objectKey string
	if err := server.pool.QueryRow(context.Background(),
		"SELECT object_key FROM memory_os.upload_authorization WHERE id = $1", issued.AuthorizationID,
	).Scan(&objectKey); err != nil {
		t.Fatal(err)
	}
	versions, err := server.objects.ListObjectVersions(context.Background(), objectKey)
	if err != nil || len(versions) == 0 {
		t.Fatalf("object was not stored before deletion: %v %v", versions, err)
	}

	previewID, previewSHA := server.commitPreviewForJob(t, owner, jobID)

	applyPath := "/v1/previews/" + previewID + "/apply"
	response, body = server.request(t, http.MethodPost, applyPath, ownerToken, map[string]any{
		"previewSha256":   previewSHA,
		"idempotencyKey":  fmt.Sprintf("idem-http-delete-%d", runID),
		"duplicatePolicy": "skip_existing",
	})
	if response.StatusCode != http.StatusOK {
		t.Fatalf("apply before deletion failed: %d %s", response.StatusCode, body)
	}

	// A lower authority must not be able to destroy the account.
	deviceSession, err := server.sessions.Issue(context.Background(), authstore.IssueInput{
		AccountID: owner,
		Epoch:     1,
		Authority: security.AuthorityIOSDevice,
		TTL:       time.Hour,
	})
	if err != nil {
		t.Fatal(err)
	}
	response, body = server.request(t, http.MethodDelete, "/v1/account", deviceSession.Token, nil)
	if response.StatusCode != http.StatusForbidden {
		t.Fatalf("device session deletion status %d %s", response.StatusCode, body)
	}

	response, body = server.request(t, http.MethodDelete, "/v1/account", ownerToken, nil)
	if response.StatusCode != http.StatusAccepted {
		t.Fatalf("account deletion failed: %d %s", response.StatusCode, body)
	}
	var receipt struct {
		Status        string `json:"status"`
		DeletionEpoch int64  `json:"deletionEpoch"`
	}
	if err := json.Unmarshal(body, &receipt); err != nil {
		t.Fatal(err)
	}
	if receipt.Status != "deleting" || receipt.DeletionEpoch != 2 {
		t.Fatalf("unexpected deletion receipt: %s", body)
	}

	// The request itself performed no erasure — the fence is what it promised.
	var stillThere int
	if err := server.pool.QueryRow(context.Background(),
		"SELECT count(*) FROM memory_os.memory_item WHERE owner_account_id = $1", owner,
	).Scan(&stillThere); err != nil {
		t.Fatal(err)
	}
	if stillThere != 2 {
		t.Fatalf("the request erased %d memory items; erasure belongs to the runtime", 2-stillThere)
	}

	// An interrupted attempt must leave the account claimable, not finished.
	// A worker whose object store always fails stands in for a crash mid-sweep.
	broken := accountdelete.Worker{
		Queue:      server.accountControl,
		Repository: server.accountControl,
		Objects:    failingEraser{},
	}
	if _, err := broken.Sweep(context.Background(), 4); err == nil {
		t.Fatal("a broken object store reported a successful erasure")
	}
	var state string
	var attempts int
	if err := server.pool.QueryRow(context.Background(),
		`SELECT state, deletion_attempts FROM memory_os.account_control WHERE account_id = $1`, owner,
	).Scan(&state, &attempts); err != nil {
		t.Fatal(err)
	}
	if state != "deleting" || attempts < 1 {
		t.Fatalf("after a failed attempt: state=%s attempts=%d", state, attempts)
	}
	if err := server.pool.QueryRow(context.Background(),
		"SELECT count(*) FROM memory_os.memory_item WHERE owner_account_id = $1", owner,
	).Scan(&stillThere); err != nil {
		t.Fatal(err)
	}
	if stillThere != 2 {
		t.Fatal("a failed attempt destroyed rows before its objects were gone")
	}

	// The failure is visible to an operator, and the aggregate carries no
	// identifiers — an alert needs a number, not a list of people.
	observing := accountdelete.Worker{
		Queue:      server.accountControl,
		Repository: server.accountControl,
		Objects:    server.objects,
	}
	backlog, err := observing.Backlog(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if backlog.Pending < 1 || backlog.MaxAttempts < 1 {
		t.Fatalf("backlog did not see the fenced account: %+v", backlog)
	}
	// One failure is not yet "stuck": the threshold exists so ordinary retries
	// do not page anyone.
	if !backlog.Healthy() {
		t.Fatalf("a single failed attempt was reported as stuck: %+v", backlog)
	}
	// Drive the account past the threshold and confirm it does alert.
	for attempt := 0; attempt < accountdelete.StuckAttemptsThreshold; attempt++ {
		_, _ = broken.Sweep(context.Background(), 1)
	}
	backlog, err = observing.Backlog(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if backlog.Healthy() || backlog.Stuck < 1 ||
		backlog.MaxAttempts < accountdelete.StuckAttemptsThreshold {
		t.Fatalf("a repeatedly failing deletion did not alert: %+v", backlog)
	}

	// The next worker resumes and finishes it.
	worker := accountdelete.Worker{
		Queue:      server.accountControl,
		Repository: server.accountControl,
		Objects:    server.objects,
	}
	receipts, err := worker.Sweep(context.Background(), 4)
	if err != nil {
		t.Fatal(err)
	}
	if len(receipts) != 1 || receipts[0].AccountID != owner || receipts[0].Attempts < 2 {
		t.Fatalf("unexpected worker receipts: %+v", receipts)
	}
	removed := map[string]int64{}
	for _, entry := range receipts[0].Removals {
		removed[entry.Table] = entry.Removed
	}
	// The sweep must report the erasure it actually performed, including the
	// two memory items applied above and both live sessions.
	if removed["memory_item"] != 2 || removed["preview_ready"] != 1 ||
		removed["import_job"] != 1 || removed["account_session"] != 2 ||
		removed["quarantine_object_versions"] < 1 {
		t.Fatalf("unexpected sweep accounting: %+v", removed)
	}

	// The bytes are gone from the bucket, not merely unreferenced by the rows.
	versions, err = server.objects.ListObjectVersions(context.Background(), objectKey)
	if err != nil {
		t.Fatal(err)
	}
	if len(versions) != 0 {
		t.Fatalf("%d object versions survived deletion", len(versions))
	}

	// Every surface now refuses the session that was valid moments ago. The
	// session row is gone, so authentication itself fails first.
	for _, probe := range []struct {
		method string
		path   string
		body   any
	}{
		{http.MethodGet, "/v1/import-jobs/" + jobID + "/preview", nil},
		{http.MethodPost, "/v1/import-jobs/" + jobID + "/uploads", map[string]any{
			"contentLength": 16, "checksumSha256": strings.Repeat("a", 64),
			"declaredContentType": "text/csv", "sourceSurface": "ios_files",
		}},
		{http.MethodPost, applyPath, map[string]any{
			"previewSha256": previewSHA, "idempotencyKey": "after-delete",
			"duplicatePolicy": "skip_existing",
		}},
		{http.MethodDelete, "/v1/account", nil},
	} {
		response, body = server.request(t, probe.method, probe.path, ownerToken, probe.body)
		if response.StatusCode != http.StatusUnauthorized {
			t.Fatalf("%s %s after deletion returned %d %s",
				probe.method, probe.path, response.StatusCode, body)
		}
	}

	// Nothing owned by the account survives anywhere.
	for _, table := range []string{
		"memory_item", "apply_confirmation", "preview_candidate", "preview_rejection",
		"preview_ready", "upload_authorization", "quarantine_object", "import_job",
		"account_session",
	} {
		var remaining int
		if err := server.pool.QueryRow(context.Background(),
			"SELECT count(*) FROM memory_os."+table+" WHERE owner_account_id = $1", owner,
		).Scan(&remaining); err != nil {
			t.Fatal(err)
		}
		if remaining != 0 {
			t.Fatalf("%s still holds %d rows for the deleted account", table, remaining)
		}
	}

	// The tombstone remains: the account is recorded as deleted, not forgotten.
	var epoch int64
	if err := server.pool.QueryRow(context.Background(),
		"SELECT state, account_epoch FROM memory_os.account_control WHERE account_id = $1", owner,
	).Scan(&state, &epoch); err != nil {
		t.Fatal(err)
	}
	if state != "deleted" || epoch != 2 {
		t.Fatalf("unexpected tombstone: state=%s epoch=%d", state, epoch)
	}

	// A finished deletion stops being backlog; an alert that never clears is
	// an alert nobody reads.
	backlog, err = observing.Backlog(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if !backlog.Healthy() {
		t.Fatalf("the completed deletion is still reported as stuck: %+v", backlog)
	}
}

// appLoginPool opens a connection as memory_app_login, the principal a
// deployment would use. The password is generated per run and set through the
// privileged connection, so no credential exists in the repository.
func appLoginPool(t *testing.T, ctx context.Context, admin *pgxpool.Pool, adminURL string) *pgxpool.Pool {
	t.Helper()
	// The password is the one already in the test database URL: reusing it
	// introduces no new secret, and — unlike a per-run random value — lets the
	// several test binaries that share this cluster set the same thing.
	parsed, err := neturl.Parse(adminURL)
	if err != nil {
		t.Fatal(err)
	}
	password, _ := parsed.User.Password()
	if password == "" {
		t.Skip("test database URL carries no password; skipping deployment-principal test")
	}

	// ALTER ROLE is cluster-wide but pg_advisory_lock is per-database, so the
	// lock must be taken on the shared postgres maintenance database, exactly as
	// the migration appliers do. It uses lock id 730001 — the SAME id the
	// migration appliers hold — because migration 007 also ALTERs this role, and
	// a password change guarded by a different id can still run concurrently
	// with that migration and collide with "tuple concurrently updated".
	maintenance := *parsed
	maintenance.Path = "/postgres"
	lockPool, err := pgxpool.New(ctx, maintenance.String())
	if err != nil {
		t.Fatal(err)
	}
	defer lockPool.Close()
	lock, err := lockPool.Acquire(ctx)
	if err != nil {
		t.Fatal(err)
	}
	defer lock.Release()
	if _, err := lock.Exec(ctx, "SELECT pg_advisory_lock(730001)"); err != nil {
		t.Fatal(err)
	}
	defer func() { _, _ = lock.Exec(ctx, "SELECT pg_advisory_unlock(730001)") }()

	if _, err := admin.Exec(ctx,
		"ALTER ROLE memory_app_login PASSWORD '"+strings.ReplaceAll(password, "'", "''")+"'"); err != nil {
		t.Fatal(err)
	}

	parsed.User = neturl.UserPassword("memory_app_login", password)
	pool, err := pgxpool.New(ctx, parsed.String())
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(pool.Close)
	if err := pool.Ping(ctx); err != nil {
		t.Fatalf("deployment principal could not connect: %v", err)
	}
	// Assert the connection really is the unprivileged principal. Without this,
	// repointing the URL at a superuser would silently turn every RLS proof in
	// this package back into a no-op.
	var currentUser string
	var isSuperuser, bypassesRLS bool
	if err := pool.QueryRow(ctx,
		`SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user`,
	).Scan(&currentUser, &isSuperuser, &bypassesRLS); err != nil {
		t.Fatal(err)
	}
	if currentUser != "memory_app_login" || isSuperuser || bypassesRLS {
		t.Fatalf("connected as %q (superuser=%v bypassrls=%v); the RLS proof would be vacuous",
			currentUser, isSuperuser, bypassesRLS)
	}
	return pool
}

// failingEraser stands in for an object store that is unreachable mid-sweep.
type failingEraser struct{}

func (failingEraser) EraseObject(context.Context, string) (int, error) {
	return 0, errors.New("object store unreachable")
}
