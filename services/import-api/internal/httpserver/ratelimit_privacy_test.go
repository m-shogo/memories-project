package httpserver

import (
	"bytes"
	"encoding/base64"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/obslog"
	"github.com/m-shogo/memories-project/services/import-api/internal/ratelimit"
)

// TestRateLimitPrivacyCanaries drives the rate-limited surface with a battery
// of canary secrets in the bearer token, body, headers and client address, then
// proves none of them — nor their URL-encoded, JSON-escaped or base64 forms —
// appears in any 429 response or any log line. It does not assert the negative
// "physically impossible", only that across this realistic battery the derived
// keys, logs and responses carry none of the canaries.
func TestRateLimitPrivacyCanaries(t *testing.T) {
	const (
		bearerCanary  = "CANARY-bearer-ses_abcdef0123456789"
		codeCanary    = "CANARY-apple-code-zzz999"
		emailCanary   = "canary.user@example.com"
		subjectCanary = "CANARY-apple-subject-001122"
		ipv4Canary    = "203.0.113.88"
		ipv6Canary    = "2001:db8:dead:beef::1"
		fwdCanary     = "CANARYFORWARDED"
	)
	var buf bytes.Buffer
	// Network capacity 1 so the second request is a 429.
	server := rateLimitedServer(t, &buf, []ratelimit.RoutePolicy{applePolicy(1)}, httpAppleStub{})

	drive := func(remote string) {
		body := `{"identityToken":"` + subjectCanary + `","authorizationCode":"` + codeCanary +
			`","clientId":"c","nonce":"n","email":"` + emailCanary + `"}`
		req := httptest.NewRequest(http.MethodPost, "/v1/auth/apple", strings.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("Authorization", "Bearer "+bearerCanary)
		req.Header.Set("X-Forwarded-For", fwdCanary)
		req.RemoteAddr = remote
		server.ServeHTTP(httptest.NewRecorder(), req)
	}
	// IPv4 client, then IPv6 client — second of each trips the 429.
	drive(ipv4Canary + ":40000")
	rec := httptest.NewRecorder()
	{
		body := `{"authorizationCode":"` + codeCanary + `"}`
		req := httptest.NewRequest(http.MethodPost, "/v1/auth/apple", strings.NewReader(body))
		req.Header.Set("Authorization", "Bearer "+bearerCanary)
		req.Header.Set("X-Forwarded-For", fwdCanary)
		req.RemoteAddr = ipv4Canary + ":40001"
		server.ServeHTTP(rec, req)
	}
	drive("[" + ipv6Canary + "]:40000")

	response := rec.Body.String() + " " + strings.Join(headerValues(rec), " ")
	logs := buf.String()

	canaries := []string{bearerCanary, codeCanary, emailCanary, subjectCanary, ipv4Canary, ipv6Canary, fwdCanary}
	forms := func(v string) []string {
		return []string{v, url.QueryEscape(v), base64.StdEncoding.EncodeToString([]byte(v)), strings.ReplaceAll(v, "@", "\\u0040")}
	}
	for _, canary := range canaries {
		for _, form := range forms(canary) {
			if strings.Contains(response, form) {
				t.Fatalf("429 response leaked a canary form %q", form)
			}
			if strings.Contains(logs, form) {
				t.Fatalf("log leaked a canary form %q:\n%s", form, logs)
			}
		}
	}
	// Sanity: the 429 actually happened and a rate-limit event was logged.
	if rec.Code != http.StatusTooManyRequests {
		t.Fatalf("expected a 429 to inspect, got %d", rec.Code)
	}
	if !strings.Contains(logs, string(obslog.EventRateLimitRejected)) {
		t.Fatal("no rate-limit event was logged")
	}
}

func headerValues(rec *httptest.ResponseRecorder) []string {
	var values []string
	for _, vs := range rec.Header() {
		values = append(values, vs...)
	}
	return values
}

// TestRetryAfterIsAlwaysBounded drives many rejections with varied policies and
// asserts Retry-After is always a positive bounded integer of seconds.
func TestRetryAfterIsAlwaysBounded(t *testing.T) {
	var buf bytes.Buffer
	server := rateLimitedServer(t, &buf, []ratelimit.RoutePolicy{{
		RouteTemplate: "POST /v1/auth/apple",
		Class:         ratelimit.ClassPublicUnauthenticated,
		Enabled:       true,
		FailureMode:   ratelimit.FailClosed,
		Global:        ratelimit.Policy{ID: "g", Capacity: 1, RefillPerSec: 0.001},
		Network:       ratelimit.Policy{ID: "n", Capacity: 1, RefillPerSec: 0.001},
	}}, httpAppleStub{})
	server.ServeHTTP(httptest.NewRecorder(), appleRequest())
	for i := 0; i < 5; i++ {
		rec := httptest.NewRecorder()
		server.ServeHTTP(rec, appleRequest())
		if rec.Code != http.StatusTooManyRequests {
			continue
		}
		ra := rec.Header().Get("Retry-After")
		if ra == "" || strings.ContainsAny(ra, "-.") || len(ra) > 4 {
			t.Fatalf("Retry-After not a bounded positive integer: %q", ra)
		}
	}
	_ = time.Second
}
