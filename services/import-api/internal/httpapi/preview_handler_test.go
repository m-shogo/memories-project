package httpapi

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/m-shogo/memories-project/services/import-api/internal/previewread"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

type recordingPreviewReadService struct {
	calls     int
	jobID     string
	limit     int
	principal security.Principal
}

func (f *recordingPreviewReadService) GetJobPreview(_ context.Context, principal security.Principal, jobID string, limit int) (previewread.View, error) {
	f.calls++
	f.jobID, f.limit, f.principal = jobID, limit, principal
	return previewread.View{PreviewID: "prv_01J00000000000000000000000"}, nil
}

func TestPreviewHandlerRejectsUnauthenticatedRequestBeforeRead(t *testing.T) {
	service := &recordingPreviewReadService{}
	mux := http.NewServeMux()
	PreviewHandler{Service: service}.Register(mux)
	request := httptest.NewRequest(http.MethodGet, "/v1/import-jobs/job_01J00000000000000000000000/preview", nil)
	response := httptest.NewRecorder()
	mux.ServeHTTP(response, request)
	if response.Code != http.StatusUnauthorized || service.calls != 0 {
		t.Fatalf("unauthenticated preview read: status=%d calls=%d", response.Code, service.calls)
	}
	if response.Header().Get("Cache-Control") != "no-store" {
		t.Fatal("unauthenticated response must not be cached")
	}
}

func TestPreviewHandlerRejectsMalformedLimitBeforeRead(t *testing.T) {
	service := &recordingPreviewReadService{}
	mux := http.NewServeMux()
	PreviewHandler{Service: service}.Register(mux)
	request := httptest.NewRequest(http.MethodGet, "/v1/import-jobs/job_01J00000000000000000000000/preview?limit=invalid", nil)
	request = request.WithContext(contextWithPrincipal(t, request.Context()))
	response := httptest.NewRecorder()
	mux.ServeHTTP(response, request)
	if response.Code != http.StatusBadRequest || service.calls != 0 {
		t.Fatalf("malformed limit reached preview read: status=%d calls=%d", response.Code, service.calls)
	}
}

func TestPreviewHandlerForwardsVerifiedPrincipalAndBoundedPageRequest(t *testing.T) {
	service := &recordingPreviewReadService{}
	mux := http.NewServeMux()
	PreviewHandler{Service: service}.Register(mux)
	request := httptest.NewRequest(http.MethodGet, "/v1/import-jobs/job_01J00000000000000000000000/preview?limit=50", nil)
	request = request.WithContext(contextWithPrincipal(t, request.Context()))
	response := httptest.NewRecorder()
	mux.ServeHTTP(response, request)
	if response.Code != http.StatusOK || service.calls != 1 {
		t.Fatalf("preview read: status=%d calls=%d body=%s", response.Code, service.calls, response.Body.String())
	}
	if service.jobID != "job_01J00000000000000000000000" || service.limit != 50 || service.principal.AccountID() != "acct_01J00000000000000000000000" {
		t.Fatalf("preview read lost request binding: job=%q limit=%d account=%q", service.jobID, service.limit, service.principal.AccountID())
	}
	if response.Header().Get("Cache-Control") != "no-store" {
		t.Fatal("preview response must not be cached")
	}
}
