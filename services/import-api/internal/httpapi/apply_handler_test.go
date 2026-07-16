package httpapi

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	applydomain "github.com/m-shogo/memories-project/services/import-api/internal/apply"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

type fakeApplyService struct {
	request   applydomain.Request
	principal security.Principal
	calls     int
	result    applydomain.Result
	err       error
}

func (f *fakeApplyService) Apply(_ context.Context, principal security.Principal, request applydomain.Request) (applydomain.Result, error) {
	f.calls++
	f.principal = principal
	f.request = request
	return f.result, f.err
}

func TestApplyHandlerUsesPathPreviewAndContextPrincipal(t *testing.T) {
	service := &fakeApplyService{result: applydomain.Result{ApplyID: "apl_01J00000000000000000000000", Status: "applied", Counts: applydomain.Counts{Created: 2, Skipped: 1}}}
	mux := http.NewServeMux()
	ApplyHandler{Service: service}.Register(mux)
	body := `{"previewSha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","idempotencyKey":"idem_01J0000000000000000000000","duplicatePolicy":"skip_existing"}`
	request := httptest.NewRequest(http.MethodPost, "/v1/previews/prv_01J00000000000000000000000/apply", strings.NewReader(body))
	request = request.WithContext(contextWithPrincipal(t, request.Context()))
	response := httptest.NewRecorder()
	mux.ServeHTTP(response, request)
	if response.Code != http.StatusOK || service.calls != 1 {
		t.Fatalf("unexpected apply response: status=%d body=%s calls=%d", response.Code, response.Body.String(), service.calls)
	}
	if service.request.PreviewID != "prv_01J00000000000000000000000" || service.principal.AccountID() != "acct_01J00000000000000000000000" {
		t.Fatalf("unsafe request forwarding: request=%#v principal=%#v", service.request, service.principal)
	}
	if response.Header().Get("Cache-Control") != "no-store" {
		t.Fatal("apply response must be no-store")
	}
}

func TestApplyHandlerRejectsClientOwnerInjection(t *testing.T) {
	service := &fakeApplyService{}
	mux := http.NewServeMux()
	ApplyHandler{Service: service}.Register(mux)
	body := `{"previewSha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","idempotencyKey":"idem_01J0000000000000000000000","duplicatePolicy":"skip_existing","ownerAccountId":"acct_attacker_000000000"}`
	request := httptest.NewRequest(http.MethodPost, "/v1/previews/prv_01J00000000000000000000000/apply", strings.NewReader(body))
	request = request.WithContext(contextWithPrincipal(t, request.Context()))
	response := httptest.NewRecorder()
	mux.ServeHTTP(response, request)
	if response.Code != http.StatusBadRequest || service.calls != 0 {
		t.Fatalf("owner injection was not rejected: status=%d calls=%d", response.Code, service.calls)
	}
}

func TestApplyHandlerRequiresVerifiedPrincipal(t *testing.T) {
	service := &fakeApplyService{}
	mux := http.NewServeMux()
	ApplyHandler{Service: service}.Register(mux)
	request := httptest.NewRequest(http.MethodPost, "/v1/previews/prv_01J00000000000000000000000/apply", strings.NewReader(`{}`))
	response := httptest.NewRecorder()
	mux.ServeHTTP(response, request)
	if response.Code != http.StatusUnauthorized || service.calls != 0 {
		t.Fatalf("unexpected unauthenticated response: status=%d calls=%d", response.Code, service.calls)
	}
}
