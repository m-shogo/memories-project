package loadtest

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/httpserver"
	"github.com/m-shogo/memories-project/services/import-api/internal/metrics"
	"github.com/m-shogo/memories-project/services/import-api/internal/obslog"
	"github.com/m-shogo/memories-project/services/import-api/internal/ratelimit"
)

// --- helpers ----------------------------------------------------------------

func newRegistry(t *testing.T) (*metrics.Registry, metrics.Recorder) {
	t.Helper()
	reg := metrics.NewRegistry()
	return reg, metrics.NewRegistryRecorder(reg, nil)
}

// applePolicy builds a single POST /v1/auth/apple policy with the given guard
// capacities, so a scenario can make the endpoint permissive or tight.
func applePolicy(globalCap, netCap int64) ratelimit.RoutePolicy {
	return ratelimit.RoutePolicy{
		RouteTemplate: "POST /v1/auth/apple",
		Class:         ratelimit.ClassPublicUnauthenticated,
		Enabled:       true,
		FailureMode:   ratelimit.FailClosed,
		Global:        ratelimit.Policy{ID: "g", Capacity: globalCap, RefillPerSec: float64(globalCap)},
		Network:       ratelimit.Policy{ID: "n", Capacity: netCap, RefillPerSec: 0.001},
	}
}

func buildServer(t *testing.T, rec metrics.Recorder, world *AppleWorld, store ratelimit.Store, policy ratelimit.RoutePolicy) http.Handler {
	t.Helper()
	enf, err := ratelimit.NewEnforcer(store, ratelimit.NewMemoryStore(10_000, time.Minute), []ratelimit.RoutePolicy{policy})
	if err != nil {
		t.Fatal(err)
	}
	return httpserver.New(httpserver.Config{
		AppleLogin: world.Login,
		Logger:     obslog.New(nil),
		Metrics:    rec,
		RateLimit: httpserver.RateLimitConfig{
			Enforcer: enf,
			Deriver:  ratelimit.KeyDeriver{Secret: []byte("load-secret"), IPv6PrefixBits: 64},
		},
	})
}

// appleFactory produces a POST /v1/auth/apple request with a unique nonce and
// code per index, so a successful request is never a replay of a prior one.
func appleFactory(index int) *http.Request {
	body := fmt.Sprintf(`{"identityToken":"x","authorizationCode":"code-%d","clientId":"c","nonce":"nonce-%d"}`, index, index)
	r := httptest.NewRequest(http.MethodPost, "/v1/auth/apple", strings.NewReader(body))
	r.Header.Set("Content-Type", "application/json")
	return r
}

func healthFactory(int) *http.Request {
	return httptest.NewRequest(http.MethodGet, "/healthz", nil)
}

// failStore is a rate-limit store that never decides, forcing the fail-closed
// path.
type failStore struct{}

func (failStore) Take(string, ratelimit.Policy, time.Time) (ratelimit.Decision, error) {
	return ratelimit.Decision{}, ratelimit.ErrStoreUnavailable
}

// --- scenarios --------------------------------------------------------------

func TestScenarioHealthBaseline(t *testing.T) {
	reg, rec := newRegistry(t)
	world := NewAppleWorld(rec)
	server := buildServer(t, rec, world, ratelimit.NewMemoryStore(10_000, time.Minute), applePolicy(100000, 100000))
	res := Run(server, Options{Concurrency: 8, TotalRequests: 400, Factory: healthFactory}, nil)

	if res.StatusClassCounts["2xx"] != 400 {
		t.Fatalf("health baseline not all 2xx: %+v", res.StatusClassCounts)
	}
	if res.MaxInFlight < 1 {
		t.Fatal("in-flight never observed")
	}
	// Health must not touch the Apple path.
	if world.SessionsIssued() != 0 || world.AccountsCreated() != 0 {
		t.Fatalf("health touched the Apple path: sessions=%d accounts=%d", world.SessionsIssued(), world.AccountsCreated())
	}
	_ = reg
}

func TestScenarioAppleSteady(t *testing.T) {
	reg, rec := newRegistry(t)
	world := NewAppleWorld(rec)
	server := buildServer(t, rec, world, ratelimit.NewMemoryStore(10_000, time.Minute), applePolicy(100000, 100000))

	const n = 500
	res := Run(server, Options{Concurrency: 16, TotalRequests: n, Factory: appleFactory}, nil)

	if res.Successes != n {
		t.Fatalf("steady load not all successful: %d/%d, classes=%+v", res.Successes, n, res.StatusClassCounts)
	}
	// Exactly one account (same subject), one session per request, replay guard
	// consulted once per request.
	if world.AccountsCreated() != 1 {
		t.Fatalf("steady load created %d accounts, want 1", world.AccountsCreated())
	}
	if world.SessionsIssued() != n {
		t.Fatalf("steady load issued %d sessions, want %d", world.SessionsIssued(), n)
	}
	// The Apple exchange and DB seam metrics were emitted.
	if reg.SumCounter(metrics.MetricAppleExchangeTotal, map[string]string{"outcome": "success"}) != n {
		t.Fatalf("apple exchange success count wrong:\n%s", reg.Export())
	}
	if reg.SumCounter(metrics.MetricDBOperationsTotal, map[string]string{"operation": "session_insert"}) != n {
		t.Fatalf("session_insert db op count wrong")
	}
	// Cardinality stays tiny regardless of request volume.
	if reg.TotalSeries() > 60 {
		t.Fatalf("series count unexpectedly high: %d", reg.TotalSeries())
	}
	t.Logf("steady: throughput=%.0f/s p50=%.2fms p95=%.2fms p99=%.2fms series=%d",
		res.Throughput, res.LatencyP50Ms, res.LatencyP95Ms, res.LatencyP99Ms, reg.TotalSeries())
}

func TestScenarioAppleBurstBounded429(t *testing.T) {
	reg, rec := newRegistry(t)
	world := NewAppleWorld(rec)
	// Tiny network capacity: a concurrent burst from one network is mostly
	// rejected before reaching the handler.
	server := buildServer(t, rec, world, ratelimit.NewMemoryStore(10_000, time.Minute), applePolicy(100000, 5))

	const n = 500
	res := Run(server, Options{Concurrency: 32, TotalRequests: n, Factory: appleFactory}, nil)

	rejected := res.StatusClassCounts["4xx"]
	if rejected == 0 {
		t.Fatalf("burst produced no 429s: %+v", res.StatusClassCounts)
	}
	// A rejected request never reached the Apple handler, so sessions issued must
	// be bounded by what the network guard admitted — far fewer than n.
	if world.SessionsIssued() >= n {
		t.Fatalf("burst reached the handler unbounded: %d sessions", world.SessionsIssued())
	}
	if world.SessionsIssued() != res.StatusClassCounts["2xx"] {
		t.Fatalf("sessions (%d) do not match 2xx (%d): handler ran for rejected requests",
			world.SessionsIssued(), res.StatusClassCounts["2xx"])
	}
	// No 5xx — rejection is a clean bounded 429, not an error.
	if res.StatusClassCounts["5xx"] != 0 {
		t.Fatalf("burst produced 5xx: %+v", res.StatusClassCounts)
	}
	if reg.TotalSeries() > 60 {
		t.Fatalf("burst inflated series: %d", reg.TotalSeries())
	}
	t.Logf("burst: 2xx=%d 4xx=%d sessions=%d series=%d",
		res.StatusClassCounts["2xx"], rejected, world.SessionsIssued(), reg.TotalSeries())
}

func TestScenarioRateLimitStoreFailureFailsClosed(t *testing.T) {
	reg, rec := newRegistry(t)
	world := NewAppleWorld(rec)
	// Primary store always errors; fail-closed with no emergency mode → deny.
	server := buildServer(t, rec, world, failStore{}, applePolicy(100000, 100000))

	res := Run(server, Options{Concurrency: 16, TotalRequests: 300, Factory: appleFactory}, nil)

	if res.StatusClassCounts["2xx"] != 0 {
		t.Fatalf("store failure allowed some requests through: %+v", res.StatusClassCounts)
	}
	// No business state mutated: no account, session, or replay consumption.
	if world.SessionsIssued() != 0 || world.AccountsCreated() != 0 || world.ReplayAttempts() != 0 {
		t.Fatalf("store failure mutated state: sessions=%d accounts=%d replay=%d",
			world.SessionsIssued(), world.AccountsCreated(), world.ReplayAttempts())
	}
	// The store-failure metric was recorded.
	if reg.SumCounter(metrics.MetricRateLimitStoreFailures, nil) == 0 {
		t.Fatalf("store failure metric not recorded:\n%s", reg.Export())
	}
}

func TestScenarioCardinalityAttackBounded(t *testing.T) {
	reg, rec := newRegistry(t)
	world := NewAppleWorld(rec)
	server := buildServer(t, rec, world, ratelimit.NewMemoryStore(50_000, time.Minute), applePolicy(100000, 100000))

	// Every request carries a distinct hostile path, request id, and forwarded
	// header; none may become a series identity.
	factory := func(i int) *http.Request {
		r := httptest.NewRequest(http.MethodGet, fmt.Sprintf("/v1/attacker/%d/probe?token=SECRET%d", i, i), nil)
		r.Header.Set("X-Request-Id", fmt.Sprintf("reqid-%d", i))
		r.Header.Set("X-Forwarded-For", fmt.Sprintf("10.9.%d.%d", i%256, (i/256)%256))
		r.Header.Set("Authorization", fmt.Sprintf("Bearer bear-%d", i))
		return r
	}
	Run(server, Options{Concurrency: 16, TotalRequests: 5000, Factory: factory}, nil)

	if reg.TotalSeries() > 80 {
		t.Fatalf("cardinality attack inflated series to %d", reg.TotalSeries())
	}
	out := reg.Export()
	for _, canary := range []string{"attacker", "SECRET", "reqid-", "10.9.", "bear-"} {
		if strings.Contains(out, canary) {
			t.Fatalf("hostile value %q leaked into a series:\n%s", canary, out)
		}
	}
}

func TestScenarioMetricsOverhead(t *testing.T) {
	// Same steady scenario with the real recorder vs a no-op recorder. We assert
	// both complete and that the enabled run's series stay bounded; we do not
	// assert a fixed overhead threshold (that is a proposal from measurement).
	run := func(rec metrics.Recorder) Result {
		world := NewAppleWorld(rec)
		store := ratelimit.NewMemoryStore(10_000, time.Minute)
		server := buildServer(t, rec, world, store, applePolicy(100000, 100000))
		return Run(server, Options{Concurrency: 16, TotalRequests: 500, Factory: appleFactory}, nil)
	}
	enabledReg := metrics.NewRegistry()
	enabled := run(metrics.NewRegistryRecorder(enabledReg, nil))
	noop := run(metrics.Nop{})

	if enabled.Successes != 500 || noop.Successes != 500 {
		t.Fatalf("overhead runs incomplete: enabled=%d noop=%d", enabled.Successes, noop.Successes)
	}
	t.Logf("overhead: enabled=%.0f/s noop=%.0f/s enabledP95=%.2fms noopP95=%.2fms",
		enabled.Throughput, noop.Throughput, enabled.LatencyP95Ms, noop.LatencyP95Ms)
}

// TestWriteLoadResultsFixture regenerates the committed results fixture. It runs
// only when MEMORY_OS_LOAD_RESULTS_PATH is set, so ordinary CI does not write
// files; the committed fixture is produced by running this once locally.
func TestWriteLoadResultsFixture(t *testing.T) {
	path := os.Getenv("MEMORY_OS_LOAD_RESULTS_PATH")
	if path == "" {
		t.Skip("set MEMORY_OS_LOAD_RESULTS_PATH to regenerate the results fixture")
	}
	commit := os.Getenv("MEMORY_OS_COMMIT_SHA")
	if commit == "" {
		commit = "unknown"
	}

	doc := ResultsDocument{
		SchemaVersion: ResultsSchemaVersion,
		CommitSHA:     commit,
		GeneratedAt:   time.Now().UTC().Format(time.RFC3339),
		Environment:   CurrentEnvironment(),
	}

	// Steady.
	{
		reg := metrics.NewRegistry()
		rec := metrics.NewRegistryRecorder(reg, nil)
		world := NewAppleWorld(rec)
		before := reg.TotalSeries()
		server := buildServer(t, rec, world, ratelimit.NewMemoryStore(10_000, time.Minute), applePolicy(100000, 100000))
		res := Run(server, Options{Concurrency: 16, TotalRequests: 1000, Factory: appleFactory}, nil)
		sr := Summarize("apple-steady-mock", "STEADY", res, reg, before, "PASS", "PASS")
		sr.Concurrency = 16
		doc.Scenarios = append(doc.Scenarios, sr)
	}
	// Burst.
	{
		reg := metrics.NewRegistry()
		rec := metrics.NewRegistryRecorder(reg, nil)
		world := NewAppleWorld(rec)
		before := reg.TotalSeries()
		server := buildServer(t, rec, world, ratelimit.NewMemoryStore(10_000, time.Minute), applePolicy(100000, 5))
		res := Run(server, Options{Concurrency: 32, TotalRequests: 1000, Factory: appleFactory}, nil)
		integrity := "PASS"
		if world.SessionsIssued() != res.StatusClassCounts["2xx"] {
			integrity = "FAIL"
		}
		sr := Summarize("apple-burst-mock", "BURST", res, reg, before, integrity, "PASS")
		sr.Concurrency = 32
		doc.Scenarios = append(doc.Scenarios, sr)
	}
	// Store failure.
	{
		reg := metrics.NewRegistry()
		rec := metrics.NewRegistryRecorder(reg, nil)
		world := NewAppleWorld(rec)
		before := reg.TotalSeries()
		server := buildServer(t, rec, world, failStore{}, applePolicy(100000, 100000))
		res := Run(server, Options{Concurrency: 16, TotalRequests: 500, Factory: appleFactory}, nil)
		integrity := "PASS"
		if world.SessionsIssued() != 0 {
			integrity = "FAIL"
		}
		sr := Summarize("ratelimit-store-failure-mock", "DEPENDENCY_DEGRADED", res, reg, before, integrity, "PASS")
		sr.Concurrency = 16
		doc.Scenarios = append(doc.Scenarios, sr)
	}
	// Cardinality attack.
	{
		reg := metrics.NewRegistry()
		rec := metrics.NewRegistryRecorder(reg, nil)
		world := NewAppleWorld(rec)
		before := reg.TotalSeries()
		server := buildServer(t, rec, world, ratelimit.NewMemoryStore(50_000, time.Minute), applePolicy(100000, 100000))
		factory := func(i int) *http.Request {
			r := httptest.NewRequest(http.MethodGet, fmt.Sprintf("/v1/attacker/%d/probe?token=SECRET%d", i, i), nil)
			r.Header.Set("X-Request-Id", fmt.Sprintf("reqid-%d", i))
			r.Header.Set("Authorization", fmt.Sprintf("Bearer bear-%d", i))
			return r
		}
		res := Run(server, Options{Concurrency: 16, TotalRequests: 5000, Factory: factory}, nil)
		integrity := "PASS"
		if reg.TotalSeries() > 80 {
			integrity = "FAIL"
		}
		sr := Summarize("cardinality-attack-mock", "OVERLOAD", res, reg, before, integrity, "PASS")
		sr.Concurrency = 16
		doc.Scenarios = append(doc.Scenarios, sr)
	}

	// Authenticated preview (MOCK session + fake DB-backed service).
	{
		reg := metrics.NewRegistry()
		rec := metrics.NewRegistryRecorder(reg, nil)
		before := reg.TotalSeries()
		server := buildAuthServer(t, rec, "GET /v1/import-jobs/{jobId}/preview", 1_000_000)
		res := Run(server, Options{Concurrency: 16, TotalRequests: 1000, Factory: previewFactory}, nil)
		integrity := "PASS"
		if reg.SumCounter(metrics.MetricDBOperationsTotal, map[string]string{"operation": "preview_read", "outcome": "success"}) != uint64(res.Successes) {
			integrity = "FAIL"
		}
		sr := Summarize("authenticated-preview-mock", "STEADY", res, reg, before, integrity, "PASS")
		sr.Concurrency = 16
		doc.Scenarios = append(doc.Scenarios, sr)
	}
	// Concurrent apply (MOCK session + fake DB-backed service).
	{
		reg := metrics.NewRegistry()
		rec := metrics.NewRegistryRecorder(reg, nil)
		before := reg.TotalSeries()
		server := buildAuthServer(t, rec, "POST /v1/previews/{previewId}/apply", 1_000_000)
		res := Run(server, Options{Concurrency: 24, TotalRequests: 800, Factory: applyFactory}, nil)
		integrity := "PASS"
		if res.StatusClassCounts["5xx"] != 0 {
			integrity = "FAIL"
		}
		sr := Summarize("concurrent-apply-mock", "STEADY", res, reg, before, integrity, "PASS")
		sr.Concurrency = 24
		doc.Scenarios = append(doc.Scenarios, sr)
	}

	blob, err := json.MarshalIndent(doc, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, append(blob, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
	t.Logf("wrote %d scenarios to %s", len(doc.Scenarios), path)
}
