package httpserver

import (
	"bytes"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/metrics"
	"github.com/m-shogo/memories-project/services/import-api/internal/obslog"
	"github.com/m-shogo/memories-project/services/import-api/internal/ratelimit"
)

func meteredServer(t *testing.T, reg *metrics.Registry, sessions PrincipalResolver, apple httpAppleStub, limited bool) http.Handler {
	t.Helper()
	config := Config{
		Sessions:   sessions,
		AppleLogin: apple,
		Logger:     obslog.New(nil),
		Metrics:    metrics.NewRegistryRecorder(reg, nil),
	}
	if limited {
		enf, err := ratelimit.NewEnforcer(ratelimit.NewMemoryStore(1000, time.Minute), nil, []ratelimit.RoutePolicy{applePolicy(1)})
		if err != nil {
			t.Fatal(err)
		}
		config.RateLimit = RateLimitConfig{Enforcer: enf, Deriver: ratelimit.KeyDeriver{Secret: []byte("s"), IPv6PrefixBits: 64}}
	}
	return New(config)
}

func TestHTTPMetricsRecordStatusClasses(t *testing.T) {
	reg := metrics.NewRegistry()
	server := meteredServer(t, reg, denyResolver{}, httpAppleStub{}, false)

	// 401 (deny resolver) on an authenticated route -> 4xx.
	req := httptest.NewRequest(http.MethodGet, "/v1/import-jobs/job-x/preview", nil)
	req.Header.Set("Authorization", "Bearer x")
	req.RemoteAddr = "203.0.113.1:5000"
	server.ServeHTTP(httptest.NewRecorder(), req)

	// 200 on health -> 2xx.
	h := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	h.RemoteAddr = "203.0.113.1:5000"
	server.ServeHTTP(httptest.NewRecorder(), h)

	// 404 unmatched -> collapses to "other".
	nf := httptest.NewRequest(http.MethodGet, "/v1/nope/12345", nil)
	nf.RemoteAddr = "203.0.113.1:5000"
	server.ServeHTTP(httptest.NewRecorder(), nf)

	out := reg.Export()
	if !strings.Contains(out, `status_class="4xx"`) || !strings.Contains(out, `status_class="2xx"`) {
		t.Fatalf("status classes not recorded:\n%s", out)
	}
	if !strings.Contains(out, `route_template="other"`) {
		t.Fatalf("unmatched route not collapsed to other:\n%s", out)
	}
	// No individual status code appears as a label.
	if strings.Contains(out, `status_class="401"`) || strings.Contains(out, `status_class="404"`) {
		t.Fatalf("raw status code used as a label:\n%s", out)
	}
	// The in-flight gauge returned to zero after all requests completed.
	if !strings.Contains(out, "memory_os_http_in_flight 0") {
		t.Fatalf("in-flight gauge did not return to zero:\n%s", out)
	}
}

func TestHTTPMetrics429Recorded(t *testing.T) {
	reg := metrics.NewRegistry()
	server := meteredServer(t, reg, nil, httpAppleStub{}, true)
	// First allowed, second 429.
	server.ServeHTTP(httptest.NewRecorder(), appleRequest())
	server.ServeHTTP(httptest.NewRecorder(), appleRequest())
	out := reg.Export()
	if !strings.Contains(out, "memory_os_rate_limit_decisions_total") {
		t.Fatalf("rate-limit decision metric missing:\n%s", out)
	}
	// A 429 is recorded as a 4xx HTTP request too.
	if !strings.Contains(out, `status_class="4xx"`) {
		t.Fatalf("429 not recorded as 4xx:\n%s", out)
	}
}

func TestHTTPMetricsPanicRecordedAs5xx(t *testing.T) {
	reg := metrics.NewRegistry()
	server := New(Config{
		Logger:     obslog.New(nil),
		Metrics:    metrics.NewRegistryRecorder(reg, nil),
		AppleLogin: panicAppleService{secret: "PANIC"},
	})
	req := httptest.NewRequest(http.MethodPost, "/v1/auth/apple", strings.NewReader(`{}`))
	req.Header.Set("Content-Type", "application/json")
	server.ServeHTTP(httptest.NewRecorder(), req)
	out := reg.Export()
	if !strings.Contains(out, "memory_os_http_panics_total") || !strings.Contains(out, `status_class="5xx"`) {
		t.Fatalf("panic not recorded as 5xx panic metric:\n%s", out)
	}
	if !strings.Contains(out, "memory_os_http_in_flight 0") {
		t.Fatalf("in-flight gauge did not return to zero after panic:\n%s", out)
	}
}

// TestMetricsExportCarriesNoRequestIDOrRawValue drives requests with hostile
// content and proves the export contains no request id, raw path, address,
// token or account-shaped value — only fixed metric names and allowlisted
// label values.
func TestMetricsExportCarriesNoRequestIDOrRawValue(t *testing.T) {
	reg := metrics.NewRegistry()
	server := meteredServer(t, reg, denyResolver{}, httpAppleStub{}, false)

	req := httptest.NewRequest(http.MethodGet, "/v1/import-jobs/JOBSECRET12345/preview?token=BEARERSECRET", nil)
	req.Header.Set("Authorization", "Bearer BEARERSECRET")
	req.Header.Set("X-Request-Id", "reqid-canary-123")
	req.RemoteAddr = "203.0.113.99:5000"
	server.ServeHTTP(httptest.NewRecorder(), req)

	out := reg.Export()
	for _, canary := range []string{"JOBSECRET12345", "BEARERSECRET", "reqid-canary-123", "203.0.113.99", "?token", "requestId", "request_id"} {
		if strings.Contains(out, canary) {
			t.Fatalf("metrics export leaked %q:\n%s", canary, out)
		}
	}
	// The concrete job id is normalized to a template.
	if !strings.Contains(out, `route_template="GET /v1/import-jobs/{jobId}/preview"`) {
		t.Fatalf("route template not normalized:\n%s", out)
	}
	_ = bytes.NewBuffer(nil)
}
