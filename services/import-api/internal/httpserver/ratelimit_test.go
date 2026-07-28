package httpserver

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/appleauth"
	"github.com/m-shogo/memories-project/services/import-api/internal/obslog"
	"github.com/m-shogo/memories-project/services/import-api/internal/ratelimit"
)

func rateLimitedServer(t *testing.T, buf *bytes.Buffer, policies []ratelimit.RoutePolicy, apple httpAppleStub) http.Handler {
	t.Helper()
	enforcer, err := ratelimit.NewEnforcer(ratelimit.NewMemoryStore(1000, time.Minute), ratelimit.NewMemoryStore(1000, time.Minute), policies)
	if err != nil {
		t.Fatal(err)
	}
	return New(Config{
		Logger:     obslog.New(buf),
		AppleLogin: apple,
		RateLimit: RateLimitConfig{
			Enforcer: enforcer,
			Deriver:  ratelimit.KeyDeriver{Secret: []byte("test-secret"), IPv6PrefixBits: 64},
		},
	})
}

// httpAppleStub records whether Login was ever called, so a test can prove a
// 429 never reaches the Apple exchange.
type httpAppleStub struct{ called *bool }

func (s httpAppleStub) Login(context.Context, appleauth.Input) (appleauth.LoginResult, error) {
	if s.called != nil {
		*s.called = true
	}
	return appleauth.LoginResult{SessionToken: "ses_stub", AccountID: "acct_stub_0000000000"}, nil
}

func applePolicy(capacity int64) ratelimit.RoutePolicy {
	return ratelimit.RoutePolicy{
		RouteTemplate: "POST /v1/auth/apple",
		Class:         ratelimit.ClassPublicUnauthenticated,
		Enabled:       true,
		FailureMode:   ratelimit.FailClosed,
		Global:        ratelimit.Policy{ID: "g", Capacity: 1000, RefillPerSec: 1000},
		Network:       ratelimit.Policy{ID: "n", Capacity: capacity, RefillPerSec: 0.001},
	}
}

func appleRequest() *http.Request {
	r := httptest.NewRequest(http.MethodPost, "/v1/auth/apple", strings.NewReader(`{"identityToken":"x","authorizationCode":"y","clientId":"c","nonce":"n"}`))
	r.Header.Set("Content-Type", "application/json")
	r.RemoteAddr = "203.0.113.77:5000"
	return r
}

func TestRateLimitRejectsOverBudgetWithStable429(t *testing.T) {
	var buf bytes.Buffer
	called := false
	server := rateLimitedServer(t, &buf, []ratelimit.RoutePolicy{applePolicy(2)}, httpAppleStub{called: &called})

	// First two allowed (reach the Apple stub, which returns 200).
	for i := 0; i < 2; i++ {
		rec := httptest.NewRecorder()
		server.ServeHTTP(rec, appleRequest())
		if rec.Code != http.StatusOK {
			t.Fatalf("request %d not allowed: %d", i, rec.Code)
		}
	}
	// Third is rate limited before reaching the handler.
	called = false
	rec := httptest.NewRecorder()
	server.ServeHTTP(rec, appleRequest())
	if rec.Code != http.StatusTooManyRequests {
		t.Fatalf("over-budget not 429: %d", rec.Code)
	}
	if called {
		t.Fatal("Apple exchange was called on a rate-limited request")
	}
	// Stable public code, no internal detail.
	var body struct {
		Code string `json:"code"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body.Code != "SEC_RATE_LIMITED" {
		t.Fatalf("unexpected public code: %s", rec.Body.String())
	}
	// Bounded Retry-After.
	ra := rec.Header().Get("Retry-After")
	seconds, err := strconv.Atoi(ra)
	if err != nil || seconds < 1 || seconds > 3600 {
		t.Fatalf("Retry-After not bounded integer: %q", ra)
	}
	// Response carries a request ID.
	if !strings.HasPrefix(rec.Header().Get("X-Request-Id"), "req_") {
		t.Fatalf("no request id on 429: %q", rec.Header().Get("X-Request-Id"))
	}
	// The response body reveals no policy id, key, address, network or bucket
	// state.
	for _, forbidden := range []string{"apple-network", "203.0.113.77", "capacity", "token", "bucket", "net_", "route_"} {
		if strings.Contains(rec.Body.String(), forbidden) {
			t.Fatalf("429 body leaked internal detail %q: %s", forbidden, rec.Body.String())
		}
	}
}

func TestRateLimitLogsCarryNoRawKeyOrAddress(t *testing.T) {
	var buf bytes.Buffer
	server := rateLimitedServer(t, &buf, []ratelimit.RoutePolicy{applePolicy(1)}, httpAppleStub{})
	// One allowed then one rejected, so both event kinds are emitted.
	server.ServeHTTP(httptest.NewRecorder(), appleRequest())
	server.ServeHTTP(httptest.NewRecorder(), appleRequest())

	output := buf.String()
	for _, forbidden := range []string{"203.0.113.77", "net_", "route_", "203.0.113"} {
		if strings.Contains(output, forbidden) {
			t.Fatalf("log leaked a raw key or address %q:\n%s", forbidden, output)
		}
	}
	// A rate-limit event exists, with only allowed fields.
	if !strings.Contains(output, string(obslog.EventRateLimitRejected)) {
		t.Fatalf("no rate-limit rejected event:\n%s", output)
	}
	for _, line := range strings.Split(strings.TrimRight(output, "\n"), "\n") {
		var event map[string]any
		if err := json.Unmarshal([]byte(line), &event); err != nil {
			t.Fatalf("log line not JSON: %v", err)
		}
	}
}

func TestRateLimitStoreFailureFailsClosedForPublicRoute(t *testing.T) {
	var buf bytes.Buffer
	// A primary store that always errors, no fallback: public route must 429.
	enforcer, err := ratelimit.NewEnforcer(failingStore{}, nil, []ratelimit.RoutePolicy{applePolicy(5)})
	if err != nil {
		t.Fatal(err)
	}
	called := false
	server := New(Config{
		Logger:     obslog.New(&buf),
		AppleLogin: httpAppleStub{called: &called},
		RateLimit:  RateLimitConfig{Enforcer: enforcer, Deriver: ratelimit.KeyDeriver{Secret: []byte("s")}},
	})
	rec := httptest.NewRecorder()
	server.ServeHTTP(rec, appleRequest())
	if rec.Code != http.StatusTooManyRequests {
		t.Fatalf("store outage did not fail closed on public route: %d", rec.Code)
	}
	if called {
		t.Fatal("Apple exchange reached during store outage")
	}
	if !strings.Contains(buf.String(), string(obslog.EventRateLimitStoreUnavailable)) {
		t.Fatalf("no store-unavailable event:\n%s", buf.String())
	}
}

func TestHealthIsNeverRateLimited(t *testing.T) {
	var buf bytes.Buffer
	// Even with a failing store, health must answer: it is exempt and never
	// consults the limiter.
	enforcer, _ := ratelimit.NewEnforcer(failingStore{}, nil, ratelimit.DefaultPolicies())
	server := New(Config{
		Logger:    obslog.New(&buf),
		RateLimit: RateLimitConfig{Enforcer: enforcer, Deriver: ratelimit.KeyDeriver{Secret: []byte("s")}},
	})
	for i := 0; i < 20; i++ {
		rec := httptest.NewRecorder()
		req := httptest.NewRequest(http.MethodGet, "/healthz", nil)
		req.RemoteAddr = "203.0.113.9:1"
		server.ServeHTTP(rec, req)
		if rec.Code != http.StatusOK {
			t.Fatalf("health rate limited on request %d: %d", i, rec.Code)
		}
	}
}

type failingStore struct{}

func (failingStore) Take(string, ratelimit.Policy, time.Time) (ratelimit.Decision, error) {
	return ratelimit.Decision{}, ratelimit.ErrStoreUnavailable
}
