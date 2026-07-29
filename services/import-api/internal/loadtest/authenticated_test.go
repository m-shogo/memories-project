package loadtest

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	applydomain "github.com/m-shogo/memories-project/services/import-api/internal/apply"
	"github.com/m-shogo/memories-project/services/import-api/internal/httpserver"
	"github.com/m-shogo/memories-project/services/import-api/internal/metrics"
	"github.com/m-shogo/memories-project/services/import-api/internal/obslog"
	"github.com/m-shogo/memories-project/services/import-api/internal/previewread"
	"github.com/m-shogo/memories-project/services/import-api/internal/ratelimit"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
	"github.com/m-shogo/memories-project/services/import-api/internal/servicemetrics"
)

// fixedResolver resolves any non-empty bearer to one verified principal, so the
// authenticated scenarios exercise the session middleware, fence and handlers
// without a live session store (dependencyMode MOCK).
type fixedResolver struct{ principal security.Principal }

func (r fixedResolver) Resolve(_ context.Context, token string) (security.Principal, error) {
	if token == "" {
		return security.Principal{}, context.Canceled
	}
	return r.principal, nil
}

// fakePreviewSvc and fakeApplySvc stand in for the database-backed services. A
// counter records how many times each ran, so a scenario can assert the handler
// executed exactly for admitted requests.
type fakePreviewSvc struct{ view previewread.View }

func (f fakePreviewSvc) GetJobPreview(context.Context, security.Principal, string, int) (previewread.View, error) {
	return f.view, nil
}

type fakeApplySvc struct{ result applydomain.Result }

func (f fakeApplySvc) Apply(context.Context, security.Principal, applydomain.Request) (applydomain.Result, error) {
	return f.result, nil
}

func testPrincipal(t *testing.T) security.Principal {
	t.Helper()
	p, err := security.NewVerifiedPrincipal("acct-load-000000000001", 1, security.AuthorityIOSUser)
	if err != nil {
		t.Fatal(err)
	}
	return p
}

func buildAuthServer(t *testing.T, rec metrics.Recorder, policyRoute string, netCap int64) http.Handler {
	t.Helper()
	policy := ratelimit.RoutePolicy{
		RouteTemplate: policyRoute,
		Class:         ratelimit.ClassPublicAuthenticated,
		Enabled:       true,
		FailureMode:   ratelimit.FailClosed,
		Global:        ratelimit.Policy{ID: "g", Capacity: 1_000_000, RefillPerSec: 1_000_000},
		Network:       ratelimit.Policy{ID: "n", Capacity: netCap, RefillPerSec: 0.001},
	}
	enf, err := ratelimit.NewEnforcer(ratelimit.NewMemoryStore(10_000, time.Minute), ratelimit.NewMemoryStore(10_000, time.Minute), []ratelimit.RoutePolicy{policy})
	if err != nil {
		t.Fatal(err)
	}
	return httpserver.New(httpserver.Config{
		Sessions: fixedResolver{principal: testPrincipal(t)},
		Preview:  servicemetrics.PreviewRead{Inner: fakePreviewSvc{view: previewread.View{PreviewID: "prev-x", JobID: "job-x"}}, Recorder: rec},
		Apply:    servicemetrics.Apply{Inner: fakeApplySvc{result: applydomain.Result{ApplyID: "apply-x", Status: "applied"}}, Recorder: rec},
		Logger:   obslog.New(nil),
		Metrics:  rec,
		RateLimit: httpserver.RateLimitConfig{
			Enforcer: enf,
			Deriver:  ratelimit.KeyDeriver{Secret: []byte("load-secret"), IPv6PrefixBits: 64},
		},
	})
}

func previewFactory(i int) *http.Request {
	r := httptest.NewRequest(http.MethodGet, "/v1/import-jobs/job-x/preview?limit=100", nil)
	r.Header.Set("Authorization", "Bearer loadtest-token")
	return r
}

func applyFactory(i int) *http.Request {
	body := `{"previewSha256":"` + strings.Repeat("a", 64) + `","idempotencyKey":"idem-x","duplicatePolicy":"skip_existing"}`
	r := httptest.NewRequest(http.MethodPost, "/v1/previews/prev-x/apply", strings.NewReader(body))
	r.Header.Set("Authorization", "Bearer loadtest-token")
	r.Header.Set("Content-Type", "application/json")
	return r
}

func TestScenarioAuthenticatedPreview(t *testing.T) {
	reg := metrics.NewRegistry()
	rec := metrics.NewRegistryRecorder(reg, nil)
	server := buildAuthServer(t, rec, "GET /v1/import-jobs/{jobId}/preview", 1_000_000)

	const n = 500
	res := Run(server, Options{Concurrency: 16, TotalRequests: n, Factory: previewFactory}, nil)
	if res.Successes != n {
		t.Fatalf("authenticated preview not all 2xx: %d/%d classes=%+v", res.Successes, n, res.StatusClassCounts)
	}
	if reg.SumCounter(metrics.MetricDBOperationsTotal, map[string]string{"operation": "preview_read", "outcome": "success"}) != n {
		t.Fatalf("preview_read db op count wrong:\n%s", reg.Export())
	}
	if reg.TotalSeries() > 60 {
		t.Fatalf("series inflated: %d", reg.TotalSeries())
	}
	// The job id must never appear as a series label.
	if strings.Contains(reg.Export(), "job-x") {
		t.Fatalf("job id leaked into a metric:\n%s", reg.Export())
	}
	t.Logf("preview: throughput=%.0f/s p95=%.2fms series=%d", res.Throughput, res.LatencyP95Ms, reg.TotalSeries())
}

func TestScenarioConcurrentApply(t *testing.T) {
	reg := metrics.NewRegistry()
	rec := metrics.NewRegistryRecorder(reg, nil)
	server := buildAuthServer(t, rec, "POST /v1/previews/{previewId}/apply", 1_000_000)

	const n = 400
	res := Run(server, Options{Concurrency: 24, TotalRequests: n, Factory: applyFactory}, nil)
	if res.Successes != n {
		t.Fatalf("concurrent apply not all 2xx: %d/%d classes=%+v", res.Successes, n, res.StatusClassCounts)
	}
	if res.StatusClassCounts["5xx"] != 0 {
		t.Fatalf("apply produced 5xx: %+v", res.StatusClassCounts)
	}
	if reg.SumCounter(metrics.MetricDBOperationsTotal, map[string]string{"operation": "apply_transaction", "outcome": "success"}) != n {
		t.Fatalf("apply_transaction db op count wrong:\n%s", reg.Export())
	}
	if reg.TotalSeries() > 60 {
		t.Fatalf("series inflated: %d", reg.TotalSeries())
	}
	t.Logf("apply: throughput=%.0f/s p95=%.2fms series=%d", res.Throughput, res.LatencyP95Ms, reg.TotalSeries())
}
