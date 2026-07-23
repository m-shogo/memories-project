package httpserver

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
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

	"github.com/m-shogo/memories-project/services/import-api/internal/apply"
	"github.com/m-shogo/memories-project/services/import-api/internal/authstore"
	"github.com/m-shogo/memories-project/services/import-api/internal/cryptoids"
	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
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
	pool     *pgxpool.Pool
	sessions authstore.Store
	server   *httptest.Server
	executor *dbscope.Executor
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
			"002_memory_os_upload_authorization.sql",
			"003_memory_os_preview_domain.sql",
			"004_memory_os_account_session.sql",
			"005_memory_os_apply_memory.sql",
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

	sessions := authstore.Store{Pool: pool}
	executor := dbscope.New(pgscope.Beginner{Pool: pool})
	handler := New(Config{
		Sessions: sessions,
		Upload: &upload.Service{
			Transactions: executor,
			Repository:   pgrepo.Upload{},
			Signer:       objects,
			Objects:      objects,
			IDs:          cryptoids.Generator{},
		},
		Preview: &previewread.Service{Transactions: executor},
		Apply: &apply.Service{
			Transactions: executor,
			Repository:   pgrepo.Apply{},
			IDs:          cryptoids.Generator{},
		},
	})
	server := httptest.NewServer(handler)
	t.Cleanup(server.Close)
	return &liveServer{pool: pool, sessions: sessions, server: server, executor: executor}
}

func (s *liveServer) issueSession(t *testing.T, accountID string) string {
	t.Helper()
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
	committer, err := previewcommit.NewCommitter(s.pool)
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
