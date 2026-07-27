package httpserver

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/m-shogo/memories-project/services/import-api/internal/appleauth"
	"github.com/m-shogo/memories-project/services/import-api/internal/obslog"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

// captureServer builds a real routing tree with a logger writing into buf, so a
// test can drive HTTP requests and inspect exactly what the server logged.
func captureServer(t *testing.T, buf *bytes.Buffer, sessions PrincipalResolver) http.Handler {
	t.Helper()
	return New(Config{
		Sessions: sessions,
		Logger:   obslog.New(buf),
	})
}

type denyResolver struct{}

func (denyResolver) Resolve(context.Context, string) (security.Principal, error) {
	return security.Principal{}, context.Canceled
}

// TestRequestLoggingNeverLeaksBearerTokenOrHostileID drives an authenticated
// route with a secret bearer token and a hostile inbound request ID, then
// proves the captured server output contains neither, echoes a fresh server ID,
// and emits exactly one structured request event.
func TestRequestLoggingNeverLeaksBearerTokenOrHostileID(t *testing.T) {
	const secretToken = "ses_CANARYtokenDEADBEEF0123456789abcdef"
	const hostileID = "hostile id\nwith newline and \"quotes\""
	var buf bytes.Buffer
	handler := captureServer(t, &buf, denyResolver{})

	request := httptest.NewRequest(http.MethodGet, "/v1/import-jobs/job-xyz/preview", nil)
	request.Header.Set("Authorization", "Bearer "+secretToken)
	request.Header.Set("X-Request-Id", hostileID)
	recorder := httptest.NewRecorder()
	handler.ServeHTTP(recorder, request)

	// The auth fails (deny resolver) so the status is 401 — the point is the log.
	if recorder.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401, got %d", recorder.Code)
	}
	// The response echoes a server-minted request ID, never the hostile inbound.
	echoed := recorder.Header().Get("X-Request-Id")
	if !strings.HasPrefix(echoed, "req_") {
		t.Fatalf("response did not echo a server request id: %q", echoed)
	}
	if strings.Contains(echoed, "hostile") || strings.Contains(echoed, "\n") {
		t.Fatalf("hostile inbound id was echoed: %q", echoed)
	}

	output := buf.String()
	if strings.Contains(output, secretToken) {
		t.Fatalf("bearer token leaked into log output:\n%s", output)
	}
	if strings.Contains(output, "hostile") || strings.Contains(output, "newline") {
		t.Fatalf("hostile inbound id leaked into log output:\n%s", output)
	}
	// Exactly one request event, well-formed, with the expected shape.
	lines := strings.Split(strings.TrimRight(output, "\n"), "\n")
	if len(lines) != 1 {
		t.Fatalf("expected exactly one event, got %d:\n%s", len(lines), output)
	}
	var event map[string]any
	if err := json.Unmarshal([]byte(lines[0]), &event); err != nil {
		t.Fatalf("event is not valid JSON: %v", err)
	}
	if event["eventCode"] != string(obslog.EventHTTPRequest) ||
		event["route"] != "GET /v1/import-jobs/{jobId}/preview" ||
		event["failureClass"] != string(obslog.FailureAuthentication) {
		t.Fatalf("unexpected request event: %v", event)
	}
	// The route template must not contain the concrete job id.
	if strings.Contains(event["route"].(string), "job-xyz") {
		t.Fatalf("route template leaked a concrete id: %v", event["route"])
	}
}

// TestPanicRecoveryEmitsBoundedEventWithoutLeak drives a route whose handler
// panics with a secret-shaped value and proves the client gets a fixed 500, the
// panic value never reaches the response or the log, and a bounded panic event
// is emitted.
func TestPanicRecoveryEmitsBoundedEventWithoutLeak(t *testing.T) {
	const panicSecret = "PANIC-CANARY-bearer-secret-0123456789"
	var buf bytes.Buffer

	// A stub Apple service whose handler path panics. We mount it through the
	// real router so the outermost observability middleware recovers it.
	panicking := New(Config{
		Logger:     obslog.New(&buf),
		AppleLogin: panicAppleService{secret: panicSecret},
	})
	request := httptest.NewRequest(http.MethodPost, "/v1/auth/apple", strings.NewReader(`{}`))
	request.Header.Set("Content-Type", "application/json")
	recorder := httptest.NewRecorder()
	panicking.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusInternalServerError {
		t.Fatalf("expected 500 from panic recovery, got %d", recorder.Code)
	}
	body := recorder.Body.String()
	if strings.Contains(body, panicSecret) || strings.Contains(body, "PANIC-CANARY") {
		t.Fatalf("panic value reached the response body: %s", body)
	}
	if !strings.Contains(body, "SEC_INTERNAL_ERROR") {
		t.Fatalf("panic response is not the fixed internal error: %s", body)
	}
	output := buf.String()
	if strings.Contains(output, panicSecret) || strings.Contains(output, "PANIC-CANARY") {
		t.Fatalf("panic value leaked into the log:\n%s", output)
	}
	if !strings.Contains(output, string(obslog.EventPanicRecovered)) {
		t.Fatalf("no panic event emitted:\n%s", output)
	}
}

type panicAppleService struct{ secret string }

func (p panicAppleService) Login(context.Context, appleauth.Input) (appleauth.LoginResult, error) {
	panic(p.secret)
}
