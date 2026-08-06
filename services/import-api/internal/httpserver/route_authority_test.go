package httpserver

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestRouteAuthorityMatchesRegisteredUploadSurface(t *testing.T) {
	tests := []struct {
		name     string
		method   string
		path     string
		template string
		known    bool
	}{
		{"issue", http.MethodPost, "/v1/import-jobs/job_123/upload-authorizations", "POST /v1/import-jobs/{jobId}/upload-authorizations", true},
		{"complete", http.MethodPost, "/v1/upload-authorizations/upl_123/complete", "POST /v1/upload-authorizations/{id}/complete", true},
		{"preview", http.MethodGet, "/v1/import-jobs/job_123/preview", "GET /v1/import-jobs/{jobId}/preview", true},
		{"apply", http.MethodPost, "/v1/previews/prv_123/apply", "POST /v1/previews/{previewId}/apply", true},
		{"legacy tombstone", http.MethodPost, "/v1/import-jobs/job_123/uploads", "POST other", true},
		{"obsolete nested completion", http.MethodPost, "/v1/import-jobs/job_123/upload-authorizations/upl_123/complete", "POST other", false},
		{"hostile cardinality", http.MethodGet, "/v1/random/attacker-controlled/value", "GET other", false},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			if got := routeTemplate(test.method, test.path); got != test.template {
				t.Fatalf("routeTemplate(%q, %q) = %q, want %q", test.method, test.path, got, test.template)
			}
			if got := knownAPIRouteShape(test.path); got != test.known {
				t.Fatalf("knownAPIRouteShape(%q) = %v, want %v", test.path, got, test.known)
			}
		})
	}
}

func TestRoutePrefilterPreservesKnownAndRejectsUnknownShapes(t *testing.T) {
	handler := New(Config{})
	for _, test := range []struct {
		path string
		want int
	}{
		{"/v1/upload-authorizations/upl_123/complete", http.StatusServiceUnavailable},
		{"/v1/import-jobs/job_123/uploads", http.StatusServiceUnavailable},
		{"/v1/random/attacker-controlled/value", http.StatusNotFound},
	} {
		request := httptest.NewRequest(http.MethodPost, test.path, nil)
		response := httptest.NewRecorder()
		handler.ServeHTTP(response, request)
		if response.Code != test.want {
			t.Fatalf("POST %s returned %d, want %d", test.path, response.Code, test.want)
		}
	}
}
