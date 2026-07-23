package httpserver

import (
	"bytes"
	"context"
	"crypto/sha256"
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

	"github.com/m-shogo/memories-project/services/import-api/internal/authstore"
	"github.com/m-shogo/memories-project/services/import-api/internal/cryptoids"
	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/objectstore"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgrepo"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgscope"
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
