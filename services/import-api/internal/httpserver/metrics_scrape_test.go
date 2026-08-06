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

func TestMetricsScrapeIsUnmountedByDefault(t *testing.T) {
	registry := metrics.NewRegistry()
	server := New(Config{
		Logger:  obslog.New(nil),
		Metrics: metrics.NewRegistryRecorder(registry, nil),
	})
	request := httptest.NewRequest(http.MethodGet, "/metrics", nil)
	response := httptest.NewRecorder()
	server.ServeHTTP(response, request)
	if response.Code != http.StatusNotFound {
		t.Fatalf("unconfigured scrape status=%d", response.Code)
	}
}

func TestMetricsScrapeMountIsAuthenticatedAndOutsidePublicRateLimit(t *testing.T) {
	registry := metrics.NewRegistry()
	recorder := metrics.NewRegistryRecorder(registry, nil)
	token := strings.Repeat("s", 40)
	scrape, err := metrics.NewScrapeHandler(metrics.ScrapeConfig{
		Exporter:    registry,
		BearerToken: token,
	})
	if err != nil {
		t.Fatal(err)
	}

	enforcer, err := ratelimit.NewEnforcer(
		ratelimit.NewMemoryStore(1000, time.Minute),
		nil,
		[]ratelimit.RoutePolicy{applePolicy(1)},
	)
	if err != nil {
		t.Fatal(err)
	}
	var logs bytes.Buffer
	server := New(Config{
		Logger:        obslog.New(&logs),
		Metrics:       recorder,
		MetricsScrape: scrape,
		RateLimit: RateLimitConfig{
			Enforcer: enforcer,
			Deriver: ratelimit.KeyDeriver{
				Secret:         []byte("metrics-scrape-test-secret"),
				IPv6PrefixBits: 64,
			},
		},
	})

	unauthorized := httptest.NewRequest(http.MethodGet, "/metrics", nil)
	unauthorized.RemoteAddr = "203.0.113.10:1234"
	unauthorizedResponse := httptest.NewRecorder()
	server.ServeHTTP(unauthorizedResponse, unauthorized)
	if unauthorizedResponse.Code != http.StatusUnauthorized {
		t.Fatalf("unauthorized status=%d", unauthorizedResponse.Code)
	}

	for attempt := 0; attempt < 2; attempt++ {
		request := httptest.NewRequest(http.MethodGet, "/metrics", nil)
		request.Header.Set("Authorization", "Bearer "+token)
		request.Header.Set("X-Request-Id", "metrics-scrape-request")
		request.RemoteAddr = "203.0.113.10:1234"
		response := httptest.NewRecorder()
		server.ServeHTTP(response, request)
		if response.Code != http.StatusOK {
			t.Fatalf("attempt=%d status=%d body=%s", attempt, response.Code, response.Body.String())
		}
		if !strings.Contains(response.Body.String(), "# TYPE memory_os_http_requests_total counter") {
			t.Fatalf("attempt=%d missing Prometheus output", attempt)
		}
	}

	// The public limiter has a one-request Apple policy, but repeated scrapes
	// remain available because the operational boundary does not consume a
	// public rate-limit bucket.
	if got := registry.SumCounter(metrics.MetricRateLimitDecisions, nil); got != 0 {
		t.Fatalf("scrape mutated public rate-limit decisions: %d", got)
	}

	for _, output := range []string{registry.Prometheus(), logs.String()} {
		if strings.Contains(output, token) || strings.Contains(output, "203.0.113.10") {
			t.Fatalf("scrape secret or address leaked:\n%s", output)
		}
	}
	expectedInternal := "route_class=" + string('"') + "INTERNAL" + string('"')
	if !strings.Contains(registry.Prometheus(), expectedInternal) {
		t.Fatalf("scrape requests were not classified as internal:\n%s", registry.Prometheus())
	}
}
