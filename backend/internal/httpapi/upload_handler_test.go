package httpapi

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/backend/internal/httpauth"
	"github.com/m-shogo/memories-project/backend/internal/security"
	"github.com/m-shogo/memories-project/backend/internal/upload"
)

type handlerVerifier struct{}

func (handlerVerifier) VerifyBearerToken(context.Context, string) (httpauth.VerifiedIdentity, error) {
	return httpauth.VerifiedIdentity{
		Issuer:  "https://appleid.apple.com",
		Subject: "apple-subject-001",
	}, nil
}

type handlerAccounts struct{}

func (handlerAccounts) ResolveByProviderSubject(context.Context, string, string) (httpauth.Account, error) {
	return httpauth.Account{
		ID:    "acct_01J00000000000000000000000",
		Epoch: 7,
	}, nil
}

type fakeUploadIssuer struct {
	request   upload.Request
	principal security.Principal
	response  upload.Response
	err       error
	calls     int
}

func (f *fakeUploadIssuer) Issue(_ context.Context, principal security.Principal, request upload.Request) (upload.Response, error) {
	f.calls++
	f.principal = principal
	f.request = request
	return f.response, f.err
}

func authenticatedUploadMux(t *testing.T, issuer UploadIssuer) http.Handler {
	t.Helper()
	handler, err := NewUploadHandler(issuer)
	if err != nil {
		t.Fatalf("NewUploadHandler() error = %v", err)
	}
	auth, err := httpauth.NewMiddleware(handlerVerifier{}, handlerAccounts{})
	if err != nil {
		t.Fatalf("NewMiddleware() error = %v", err)
	}
	mux := http.NewServeMux()
	mux.Handle("POST /v1/import-jobs/{jobId}/upload-authorization", auth.RequirePrincipal(handler))
	return mux
}

func validUploadBody() string {
	return `{"contentLength":1024,"checksumSha256":"` + strings.Repeat("a", 64) + `","contentType":"application/zip","sourceSurface":"ios_files","displayFilename":"private-export.zip"}`
}

func TestUploadHandlerIssuesNoStoreResponse(t *testing.T) {
	t.Parallel()

	expiresAt := time.Date(2026, 7, 16, 5, 10, 0, 0, time.UTC)
	issuer := &fakeUploadIssuer{response: upload.Response{
		Authorization: upload.Authorization{
			ID:        "upa_0123456789abcdef0123456789abcdef",
			ExpiresAt: expiresAt,
		},
		SignedPUT: upload.SignedPUT{
			URL: "https://storage.invalid/private-put",
			RequiredHeaders: map[string]string{
				"content-type": "application/zip",
			},
		},
	}}
	request := httptest.NewRequest(
		http.MethodPost,
		"/v1/import-jobs/job_01J00000000000000000000000/upload-authorization",
		strings.NewReader(validUploadBody()),
	)
	request.Header.Set("Authorization", "Bearer token_0123456789abcdef")
	response := httptest.NewRecorder()

	authenticatedUploadMux(t, issuer).ServeHTTP(response, request)

	if response.Code != http.StatusCreated {
		t.Fatalf("status = %d, body=%s", response.Code, response.Body.String())
	}
	if response.Header().Get("Cache-Control") != "no-store" {
		t.Fatalf("missing no-store")
	}
	if issuer.calls != 1 {
		t.Fatalf("issuer calls = %d", issuer.calls)
	}
	if issuer.request.JobID != "job_01J00000000000000000000000" {
		t.Fatalf("job id = %q", issuer.request.JobID)
	}
	if issuer.principal.AccountID() != "acct_01J00000000000000000000000" {
		t.Fatalf("issuer did not receive verified principal")
	}
	if !strings.Contains(response.Body.String(), "private-put") {
		t.Fatalf("response missing signed URL: %s", response.Body.String())
	}
}

func TestUploadHandlerRejectsUnknownIdentityFields(t *testing.T) {
	t.Parallel()

	issuer := &fakeUploadIssuer{}
	body := `{"contentLength":1024,"checksumSha256":"` + strings.Repeat("a", 64) + `","contentType":"application/zip","sourceSurface":"ios_files","ownerAccountId":"acct_01J99999999999999999999999"}`
	request := httptest.NewRequest(
		http.MethodPost,
		"/v1/import-jobs/job_01J00000000000000000000000/upload-authorization",
		strings.NewReader(body),
	)
	request.Header.Set("Authorization", "Bearer token_0123456789abcdef")
	response := httptest.NewRecorder()

	authenticatedUploadMux(t, issuer).ServeHTTP(response, request)

	if response.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, body=%s", response.Code, response.Body.String())
	}
	if issuer.calls != 0 {
		t.Fatalf("issuer must not run for unknown identity field")
	}
}

func TestUploadHandlerHidesUnavailableJob(t *testing.T) {
	t.Parallel()

	issuer := &fakeUploadIssuer{err: ErrWrappedJobUnavailable{}}
	request := httptest.NewRequest(
		http.MethodPost,
		"/v1/import-jobs/job_01J99999999999999999999999/upload-authorization",
		strings.NewReader(validUploadBody()),
	)
	request.Header.Set("Authorization", "Bearer token_0123456789abcdef")
	response := httptest.NewRecorder()

	authenticatedUploadMux(t, issuer).ServeHTTP(response, request)

	if response.Code != http.StatusNotFound {
		t.Fatalf("status = %d, body=%s", response.Code, response.Body.String())
	}
	if response.Body.String() != "{\"code\":\"not_found\"}\n" {
		t.Fatalf("unexpected disclosure body: %q", response.Body.String())
	}
}

type ErrWrappedJobUnavailable struct{}

func (ErrWrappedJobUnavailable) Error() string { return "resource unavailable" }
func (ErrWrappedJobUnavailable) Unwrap() error { return upload.ErrJobUnavailable }

func TestUploadHandlerRejectsUnauthenticatedRequest(t *testing.T) {
	t.Parallel()

	issuer := &fakeUploadIssuer{err: errors.New("must not run")}
	request := httptest.NewRequest(
		http.MethodPost,
		"/v1/import-jobs/job_01J00000000000000000000000/upload-authorization",
		strings.NewReader(validUploadBody()),
	)
	response := httptest.NewRecorder()

	authenticatedUploadMux(t, issuer).ServeHTTP(response, request)

	if response.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d", response.Code)
	}
	if issuer.calls != 0 {
		t.Fatalf("issuer must not run without authentication")
	}
}
