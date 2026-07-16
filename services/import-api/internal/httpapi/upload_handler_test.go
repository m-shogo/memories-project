package httpapi

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/security"
	"github.com/m-shogo/memories-project/services/import-api/internal/upload"
)

type fakeUploadService struct {
	issuedRequest   upload.IssueRequest
	issuedPrincipal security.Principal
	issueCalls      int
	completeCalls   int
}

func (f *fakeUploadService) Issue(_ context.Context, principal security.Principal, request upload.IssueRequest) (upload.IssueResponse, error) {
	f.issueCalls++
	f.issuedPrincipal = principal
	f.issuedRequest = request
	return upload.IssueResponse{AuthorizationID: "upl_01J00000000000000000000000", UploadURL: "https://storage.example/signed", RequiredHeaders: map[string]string{"Content-Type": "application/zip"}, ExpiresAt: time.Unix(1_800_000_300, 0).UTC()}, nil
}
func (f *fakeUploadService) Complete(context.Context, security.Principal, string) error {
	f.completeCalls++
	return nil
}

func TestIssueUploadUsesContextPrincipalAndPathJobID(t *testing.T) {
	service := &fakeUploadService{}
	mux := http.NewServeMux()
	UploadHandler{Service: service}.Register(mux)
	body := `{"contentLength":1024,"checksumSha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","contentType":"application/zip","sourceSurface":"desktop_portal","displayFilename":"export.zip"}`
	request := httptest.NewRequest(http.MethodPost, "/v1/import-jobs/job_01J00000000000000000000000/upload-authorizations", strings.NewReader(body))
	request = request.WithContext(contextWithPrincipal(t, request.Context()))
	response := httptest.NewRecorder()
	mux.ServeHTTP(response, request)
	if response.Code != http.StatusCreated {
		t.Fatalf("unexpected status %d: %s", response.Code, response.Body.String())
	}
	if service.issueCalls != 1 || service.issuedRequest.JobID != "job_01J00000000000000000000000" {
		t.Fatalf("request not forwarded safely: %#v", service.issuedRequest)
	}
	if service.issuedPrincipal.AccountID() != "acct_01J00000000000000000000000" {
		t.Fatal("verified principal missing")
	}
	if response.Header().Get("Cache-Control") != "no-store" {
		t.Fatal("response must be no-store")
	}
}

func TestIssueUploadRejectsClientSuppliedOwnerField(t *testing.T) {
	service := &fakeUploadService{}
	mux := http.NewServeMux()
	UploadHandler{Service: service}.Register(mux)
	body := `{"contentLength":1024,"checksumSha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","contentType":"application/zip","sourceSurface":"desktop_portal","ownerAccountId":"acct_attacker_000000000"}`
	request := httptest.NewRequest(http.MethodPost, "/v1/import-jobs/job_01J00000000000000000000000/upload-authorizations", strings.NewReader(body))
	request = request.WithContext(contextWithPrincipal(t, request.Context()))
	response := httptest.NewRecorder()
	mux.ServeHTTP(response, request)
	if response.Code != http.StatusBadRequest || service.issueCalls != 0 {
		t.Fatalf("owner injection was not rejected: status=%d calls=%d", response.Code, service.issueCalls)
	}
}

func TestIssueUploadRequiresVerifiedPrincipal(t *testing.T) {
	service := &fakeUploadService{}
	mux := http.NewServeMux()
	UploadHandler{Service: service}.Register(mux)
	request := httptest.NewRequest(http.MethodPost, "/v1/import-jobs/job_01J00000000000000000000000/upload-authorizations", strings.NewReader(`{}`))
	response := httptest.NewRecorder()
	mux.ServeHTTP(response, request)
	if response.Code != http.StatusUnauthorized || service.issueCalls != 0 {
		t.Fatalf("unexpected unauthenticated result: %d", response.Code)
	}
}

func TestCompleteUploadQueuesAcceptedResponse(t *testing.T) {
	service := &fakeUploadService{}
	mux := http.NewServeMux()
	UploadHandler{Service: service}.Register(mux)
	request := httptest.NewRequest(http.MethodPost, "/v1/upload-authorizations/upl_01J00000000000000000000000/complete", nil)
	request = request.WithContext(contextWithPrincipal(t, request.Context()))
	response := httptest.NewRecorder()
	mux.ServeHTTP(response, request)
	if response.Code != http.StatusAccepted || service.completeCalls != 1 {
		t.Fatalf("unexpected completion result: status=%d calls=%d", response.Code, service.completeCalls)
	}
}

func TestCompleteUploadRejectsUnexpectedBody(t *testing.T) {
	service := &fakeUploadService{}
	mux := http.NewServeMux()
	UploadHandler{Service: service}.Register(mux)
	request := httptest.NewRequest(http.MethodPost, "/v1/upload-authorizations/upl_01J00000000000000000000000/complete", strings.NewReader(`{"clientMetadata":"untrusted"}`))
	request = request.WithContext(contextWithPrincipal(t, request.Context()))
	response := httptest.NewRecorder()
	mux.ServeHTTP(response, request)
	if response.Code != http.StatusBadRequest || service.completeCalls != 0 {
		t.Fatalf("unexpected completion body was not rejected: status=%d calls=%d", response.Code, service.completeCalls)
	}
}

func contextWithPrincipal(t *testing.T, ctx context.Context) context.Context {
	t.Helper()
	principal, err := security.NewVerifiedPrincipal("acct_01J00000000000000000000000", 7, security.AuthorityIOSUser)
	if err != nil {
		t.Fatal(err)
	}
	result, err := security.WithPrincipal(ctx, principal)
	if err != nil {
		t.Fatal(err)
	}
	return result
}

func decodeProblem(t *testing.T, recorder *httptest.ResponseRecorder) problem {
	t.Helper()
	var value problem
	if err := json.NewDecoder(recorder.Body).Decode(&value); err != nil {
		t.Fatal(err)
	}
	return value
}
