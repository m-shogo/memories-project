package metrics

import (
	"net/http"
	"net/http/httptest"
	"runtime"
	"strconv"
	"strings"
	"testing"
	"time"
)

func TestPrometheusExpositionIsDeterministicAndPrivate(t *testing.T) {
	registry := NewRegistry()
	recorder := NewRegistryRecorder(registry, nil)

	recorder.RecordHTTPRequest(
		"GET /v1/private/CANARY_JOB_123?token=CANARY_TOKEN",
		RoutePublicAuthenticated,
		MethodGet,
		Status2xx,
		OutcomeSuccess,
		25*time.Millisecond,
	)

	first := registry.Prometheus()
	second := registry.Prometheus()
	if first != second {
		t.Fatal("Prometheus exposition is not deterministic")
	}
	for _, required := range []string{
		"# TYPE memory_os_http_requests_total counter",
		"# TYPE memory_os_http_request_duration_seconds histogram",
		`memory_os_http_request_duration_seconds_bucket{route_template="other",route_class="PUBLIC_AUTHENTICATED",le="+Inf"} 1`,
		`memory_os_http_request_duration_seconds_count{route_template="other",route_class="PUBLIC_AUTHENTICATED"} 1`,
	} {
		// The raw literals above intentionally contain quotes exactly as the
		// Prometheus text format emits them; normalize the source-only escaping
		// so this assertion cannot pass on a backslash-containing output.
		required = strings.ReplaceAll(required, `\"`, `"`)
		if !strings.Contains(first, required) {
			t.Fatalf("Prometheus exposition missing %q:\n%s", required, first)
		}
	}
	if strings.Contains(first, `\"`) {
		t.Fatalf("Prometheus exposition contains escaped source literals:\n%s", first)
	}
	for _, forbidden := range []string{
		"CANARY_JOB_123",
		"CANARY_TOKEN",
		"/v1/private/",
		"?token=",
	} {
		if strings.Contains(first, forbidden) {
			t.Fatalf("Prometheus exposition leaked %q:\n%s", forbidden, first)
		}
	}
}

func TestNewScrapeHandlerFailsClosed(t *testing.T) {
	registry := NewRegistry()
	for name, config := range map[string]ScrapeConfig{
		"missing exporter": {BearerToken: strings.Repeat("a", 32)},
		"short token":      {Exporter: registry, BearerToken: "short"},
		"control token":    {Exporter: registry, BearerToken: strings.Repeat("a", 31) + "\n"},
		"small bound":      {Exporter: registry, BearerToken: strings.Repeat("a", 32), MaxResponseBytes: 100},
		"large bound":      {Exporter: registry, BearerToken: strings.Repeat("a", 32), MaxResponseBytes: 17 << 20},
	} {
		t.Run(name, func(t *testing.T) {
			if _, err := NewScrapeHandler(config); err == nil {
				t.Fatal("invalid scrape configuration was accepted")
			}
		})
	}
}

func TestScrapeHandlerAuthenticationAndHeaders(t *testing.T) {
	registry := NewRegistry()
	recorder := NewRegistryRecorder(registry, nil)
	recorder.RecordSessionIssuance(OutcomeSuccess)
	token := strings.Repeat("m", 40)
	handler, err := NewScrapeHandler(ScrapeConfig{Exporter: registry, BearerToken: token})
	if err != nil {
		t.Fatal(err)
	}

	for name, authorization := range map[string]string{
		"missing": "",
		"wrong":   "Bearer " + strings.Repeat("x", 40),
	} {
		t.Run(name, func(t *testing.T) {
			request := httptest.NewRequest(http.MethodGet, "/metrics", nil)
			if authorization != "" {
				request.Header.Set("Authorization", authorization)
			}
			response := httptest.NewRecorder()
			handler.ServeHTTP(response, request)
			if response.Code != http.StatusUnauthorized {
				t.Fatalf("status=%d", response.Code)
			}
			if strings.Contains(response.Body.String(), "memory_os_") {
				t.Fatal("unauthenticated response exposed metrics")
			}
			if response.Header().Get("Cache-Control") != "no-store" {
				t.Fatal("unauthenticated response is cacheable")
			}
			if response.Header().Get("WWW-Authenticate") == "" {
				t.Fatal("missing bearer challenge")
			}
		})
	}

	request := httptest.NewRequest(http.MethodGet, "/metrics", nil)
	request.Header.Set("Authorization", "Bearer "+token)
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)
	if response.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", response.Code, response.Body.String())
	}
	if response.Header().Get("Content-Type") != prometheusContentType {
		t.Fatalf("content-type=%q", response.Header().Get("Content-Type"))
	}
	if response.Header().Get("Cache-Control") != "no-store" {
		t.Fatal("scrape response is cacheable")
	}
	if response.Header().Get("X-Content-Type-Options") != "nosniff" {
		t.Fatal("nosniff header missing")
	}
	if !strings.Contains(response.Body.String(), "memory_os_session_issuance_total") {
		t.Fatal("authorized scrape omitted registered sample")
	}

	post := httptest.NewRequest(http.MethodPost, "/metrics", nil)
	post.Header.Set("Authorization", "Bearer "+token)
	postResponse := httptest.NewRecorder()
	handler.ServeHTTP(postResponse, post)
	if postResponse.Code != http.StatusMethodNotAllowed || postResponse.Header().Get("Allow") != http.MethodGet {
		t.Fatalf("POST boundary status=%d allow=%q", postResponse.Code, postResponse.Header().Get("Allow"))
	}
}

type oversizedPrometheusExporter struct{}

func (oversizedPrometheusExporter) Prometheus() string { return strings.Repeat("x", 1025) }

func TestScrapeHandlerRejectsOversizedSnapshot(t *testing.T) {
	token := strings.Repeat("z", 32)
	handler, err := NewScrapeHandler(ScrapeConfig{
		Exporter:         oversizedPrometheusExporter{},
		BearerToken:      token,
		MaxResponseBytes: 1024,
	})
	if err != nil {
		t.Fatal(err)
	}
	request := httptest.NewRequest(http.MethodGet, "/metrics", nil)
	request.Header.Set("Authorization", "Bearer "+token)
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)
	if response.Code != http.StatusServiceUnavailable {
		t.Fatalf("status=%d", response.Code)
	}
	if strings.Contains(response.Body.String(), strings.Repeat("x", 16)) {
		t.Fatal("oversized snapshot leaked into error response")
	}
}

// An observation updates the histogram count and all bucket counts under one
// registry lock. A scrape must never expose a torn snapshot of those fields.
func TestPrometheusHistogramSnapshotIsCoherentDuringUpdates(t *testing.T) {
	registry := NewRegistry()
	NewRegistryRecorder(registry, nil)
	labels := map[string]string{"route_template": "other", "route_class": "HEALTH"}
	const observations = 200
	const countPrefix = "memory_os_http_request_duration_seconds_count{route_template=\"other\",route_class=\"HEALTH\"} "
	const infinityPrefix = "memory_os_http_request_duration_seconds_bucket{route_template=\"other\",route_class=\"HEALTH\",le=\"+Inf\"} "

	checkSnapshot := func(snapshot string) (uint64, bool) {
		var count, infinity uint64
		var hasCount, hasInfinity bool
		for _, line := range strings.Split(snapshot, "\n") {
			switch {
			case strings.HasPrefix(line, countPrefix):
				if hasCount {
					t.Fatal("duplicate histogram count in one scrape")
				}
				var err error
				count, err = strconv.ParseUint(strings.TrimPrefix(line, countPrefix), 10, 64)
				if err != nil {
					t.Fatalf("invalid histogram count: %v", err)
				}
				hasCount = true
			case strings.HasPrefix(line, infinityPrefix):
				if hasInfinity {
					t.Fatal("duplicate infinity bucket in one scrape")
				}
				var err error
				infinity, err = strconv.ParseUint(strings.TrimPrefix(line, infinityPrefix), 10, 64)
				if err != nil {
					t.Fatalf("invalid infinity bucket: %v", err)
				}
				hasInfinity = true
			}
		}
		if hasCount != hasInfinity {
			t.Fatal("histogram count and infinity bucket must appear together")
		}
		if hasCount && count != infinity {
			t.Fatalf("torn histogram scrape: count=%d infinity=%d", count, infinity)
		}
		return count, hasCount
	}

	done := make(chan struct{})
	go func() {
		defer close(done)
		for i := 0; i < observations; i++ {
			registry.observe(MetricHTTPRequestDuration, labels, 0.01)
			runtime.Gosched()
		}
	}()
	for i := 0; i < observations; i++ {
		checkSnapshot(registry.Prometheus())
		runtime.Gosched()
	}
	<-done
	count, present := checkSnapshot(registry.Prometheus())
	if !present || count != observations {
		t.Fatalf("final histogram count=%d present=%t, want %d", count, present, observations)
	}
}

// Escaping must prevent a future allowlisted label value containing punctuation
// from injecting a new Prometheus sample or changing the label boundary.
func TestPrometheusLabelsEscapeInjectionTokens(t *testing.T) {
	raw := "safe\"}\nINJECTED{\\tail"
	got := prometheusLabels([]string{"route_template"}, map[string]string{"route_template": raw}, "", "")
	want := "{route_template=" + strconv.Quote(raw) + "}"
	if got != want {
		t.Fatalf("escaped label=%q, want %q", got, want)
	}
	if strings.Contains(got, "\n") {
		t.Fatal("unescaped newline in Prometheus label")
	}
}
