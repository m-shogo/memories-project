package metrics

import (
	"math"
	"strings"
	"sync"
	"testing"
	"time"
)

func newRecorder(t *testing.T) (*Registry, Recorder) {
	t.Helper()
	reg := NewRegistry()
	return reg, NewRegistryRecorder(reg, nil)
}

func TestCounterAndHistogramRecorded(t *testing.T) {
	reg, rec := newRecorder(t)
	rec.RecordHTTPRequest("POST /v1/auth/apple", RoutePublicUnauthenticated, MethodPost, Status2xx, OutcomeSuccess, 50*time.Millisecond)
	out := reg.Export()
	if !strings.Contains(out, `memory_os_http_requests_total{route_template="POST /v1/auth/apple",route_class="PUBLIC_UNAUTHENTICATED",method="POST",status_class="2xx",outcome="success"} 1`) {
		t.Fatalf("counter not recorded:\n%s", out)
	}
	if !strings.Contains(out, "memory_os_http_request_duration_seconds_count") {
		t.Fatalf("histogram not recorded:\n%s", out)
	}
}

func TestGaugeInFlightReturnsToZero(t *testing.T) {
	reg, rec := newRecorder(t)
	rec.IncHTTPInFlight(1)
	rec.IncHTTPInFlight(1)
	rec.IncHTTPInFlight(-1)
	rec.IncHTTPInFlight(-1)
	if !strings.Contains(reg.Export(), "memory_os_http_in_flight 0") {
		t.Fatalf("in-flight gauge did not return to zero:\n%s", reg.Export())
	}
}

func TestHistogramRejectsBadValues(t *testing.T) {
	reg := NewRegistry()
	reg.register(spec{name: "m", kind: TypeHistogram, labels: []string{}, buckets: []float64{1, 2, 3}, budget: 1})
	reg.observe("m", map[string]string{}, math.NaN())
	reg.observe("m", map[string]string{}, math.Inf(1))
	reg.observe("m", map[string]string{}, -5)
	if strings.Contains(reg.Export(), "m_count{} 1") || reg.SeriesCount("m") != 0 {
		t.Fatalf("bad histogram values were recorded:\n%s", reg.Export())
	}
	reg.observe("m", map[string]string{}, 1.5)
	if !strings.Contains(reg.Export(), "m_count") {
		t.Fatalf("valid value not recorded after bad ones:\n%s", reg.Export())
	}
}

func TestInvalidBucketsFailRegistration(t *testing.T) {
	reg := NewRegistry()
	for _, bad := range [][]float64{
		{},                  // empty
		{1, 1, 2},           // duplicate
		{3, 2, 1},           // descending
		{-1, 2},             // non-positive
		{1, math.Inf(1)},    // inf
		make([]float64, 21), // too many
	} {
		if reg.register(spec{name: "h", kind: TypeHistogram, labels: []string{}, buckets: bad, budget: 1}) {
			t.Fatalf("invalid buckets accepted: %v", bad)
		}
	}
}

func TestUnknownLabelValuesNormalizeToFixedToken(t *testing.T) {
	reg, rec := newRecorder(t)
	// A caller passing an out-of-enum value must not create a new label value.
	rec.RecordHTTPRequest("POST /v1/attacker/path/with/id-12345", RouteClass("SPOOFED"), Method("TRACE"), StatusClass("799"), Outcome("weird"), time.Millisecond)
	out := reg.Export()
	if strings.Contains(out, "attacker") || strings.Contains(out, "SPOOFED") || strings.Contains(out, "TRACE") || strings.Contains(out, "799") || strings.Contains(out, "weird") {
		t.Fatalf("out-of-enum values leaked into a label:\n%s", out)
	}
	if !strings.Contains(out, `route_template="other"`) || !strings.Contains(out, `route_class="unknown"`) ||
		!strings.Contains(out, `method="other"`) || !strings.Contains(out, `status_class="unknown"`) ||
		!strings.Contains(out, `outcome="unknown"`) {
		t.Fatalf("out-of-enum values not normalized to fixed tokens:\n%s", out)
	}
}

func TestCardinalityBudgetIsEnforced(t *testing.T) {
	reg := NewRegistry()
	reg.register(spec{name: "c", kind: TypeCounter, labels: []string{"k"}, budget: 3})
	for i := 0; i < 100; i++ {
		reg.incCounter("c", map[string]string{"k": string(rune('a' + i%26))}, 1)
	}
	if reg.SeriesCount("c") > 3 {
		t.Fatalf("series budget exceeded: %d", reg.SeriesCount("c"))
	}
	if reg.DroppedSeries("c") == 0 {
		t.Fatal("dropped series not counted")
	}
}

// TestFloodedRouteDoesNotInflateSeries proves that many distinct raw paths
// (as an attacker would send) do not create many series: they all normalize to
// "other".
func TestFloodedRouteDoesNotInflateSeries(t *testing.T) {
	reg, rec := newRecorder(t)
	for i := 0; i < 10_000; i++ {
		rec.RecordHTTPRequest("GET /v1/unknown/"+string(rune(i)), RoutePublicAuthenticated, MethodGet, Status4xx, OutcomeRejected, time.Millisecond)
	}
	// route_template collapses to "other" (one value) x one class x method x
	// status x outcome — a tiny bounded number, never 10k.
	if reg.SeriesCount(MetricHTTPRequestsTotal) > 4 {
		t.Fatalf("flooded raw paths inflated series to %d", reg.SeriesCount(MetricHTTPRequestsTotal))
	}
}

func TestConcurrentRecordingIsRaceSafe(t *testing.T) {
	reg, rec := newRecorder(t)
	var wg sync.WaitGroup
	for i := 0; i < 200; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			rec.RecordHTTPRequest("POST /v1/auth/apple", RoutePublicUnauthenticated, MethodPost, Status2xx, OutcomeSuccess, time.Millisecond)
			rec.IncHTTPInFlight(1)
			rec.IncHTTPInFlight(-1)
		}()
	}
	wg.Wait()
	if !strings.Contains(reg.Export(), "memory_os_http_requests_total") {
		t.Fatal("concurrent recording lost data")
	}
}

// TestRecorderPanicDoesNotPropagate: a panicking registry operation is recovered
// inside the recorder so a metrics fault never fails the caller.
func TestRecorderPanicIsIsolated(t *testing.T) {
	panicked := false
	rec := &registryRecorder{reg: nil, onPanic: func() { panicked = true }}
	// reg is nil, so the underlying registry access would panic; the guard must
	// recover it and the caller must not see a panic.
	func() {
		defer func() {
			if recover() != nil {
				t.Fatal("recorder panic propagated to the caller")
			}
		}()
		rec.RecordHTTPRequest("POST /v1/auth/apple", RoutePublicUnauthenticated, MethodPost, Status2xx, OutcomeSuccess, time.Millisecond)
	}()
	if !panicked {
		t.Fatal("panic observer was not notified")
	}
}

func TestNopRecorderIsSafe(t *testing.T) {
	var rec Recorder = Nop{}
	rec.RecordHTTPRequest("POST /v1/auth/apple", RoutePublicUnauthenticated, MethodPost, Status2xx, OutcomeSuccess, time.Millisecond)
	rec.RecordDeletionJob(WorkerDeletion, OutcomeSuccess, FailNone, time.Second)
	rec.SetDeletionBacklog(0)
}

func TestDuplicateRegistrationSameShapeIsIdempotent(t *testing.T) {
	reg := NewRegistry()
	s := spec{name: "d", kind: TypeCounter, labels: []string{"k"}, budget: 8}
	if !reg.register(s) || !reg.register(s) {
		t.Fatal("idempotent re-registration rejected")
	}
	// A conflicting re-registration is refused.
	if reg.register(spec{name: "d", kind: TypeGauge, labels: []string{"k"}, budget: 8}) {
		t.Fatal("conflicting re-registration accepted")
	}
}
