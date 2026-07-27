package httpserver

import (
	"net/http"
	"strings"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/obslog"
	"github.com/m-shogo/memories-project/services/import-api/internal/reqid"
)

// observabilityMiddleware is the outermost wrapper. It assigns a validated,
// non-secret request ID, returns it in the response header, propagates it
// through context, recovers panics into a bounded event plus a 500, and emits
// exactly one structured request event carrying method, a low-cardinality route
// template, status, duration and a failure class — never a token, a path
// containing an account or job ID, a query string or an error string.
func observabilityMiddleware(logger *obslog.Logger, next http.Handler) http.Handler {
	return http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		start := time.Now()

		requestID, _ := reqid.FromInbound(request.Header.Get("X-Request-Id"))
		writer.Header().Set("X-Request-Id", requestID)
		ctx := reqid.WithRequestID(request.Context(), requestID)
		request = request.WithContext(ctx)

		recorder := &statusRecorder{ResponseWriter: writer, status: http.StatusOK}
		route := routeTemplate(request.Method, request.URL.Path)

		defer func() {
			if recovered := recover(); recovered != nil {
				// A panic never reaches the client as detail: a fixed 500 body
				// and a bounded event with no recovered value, no stack, no
				// request content.
				if !recorder.wroteHeader {
					recorder.Header().Set("Content-Type", "application/json")
					recorder.Header().Set("Cache-Control", "no-store")
					recorder.WriteHeader(http.StatusInternalServerError)
					_, _ = recorder.Write([]byte(`{"code":"SEC_INTERNAL_ERROR"}`))
				}
				logger.Emit(obslog.Event{
					Severity:     obslog.SeverityError,
					EventName:    "http.panic",
					EventCode:    obslog.EventPanicRecovered,
					Component:    obslog.ComponentHTTP,
					Operation:    "serve",
					Outcome:      obslog.OutcomeFailure,
					RequestID:    requestID,
					HTTPMethod:   request.Method,
					Route:        route,
					StatusCode:   obslog.IntPtr(http.StatusInternalServerError),
					DurationMs:   obslog.Int64Ptr(time.Since(start).Milliseconds()),
					FailureClass: obslog.FailurePanic,
				})
			}
		}()

		next.ServeHTTP(recorder, request)

		logger.Emit(obslog.Event{
			Severity:     severityForStatus(recorder.status),
			EventName:    "http.request",
			EventCode:    obslog.EventHTTPRequest,
			Component:    obslog.ComponentHTTP,
			Operation:    "serve",
			Outcome:      outcomeForStatus(recorder.status),
			RequestID:    requestID,
			HTTPMethod:   request.Method,
			Route:        route,
			StatusCode:   obslog.IntPtr(recorder.status),
			DurationMs:   obslog.Int64Ptr(time.Since(start).Milliseconds()),
			FailureClass: failureClassForStatus(recorder.status),
		})
	})
}

// statusRecorder captures the response status without buffering the body, so
// nothing the handler writes is retained or logged.
type statusRecorder struct {
	http.ResponseWriter
	status      int
	wroteHeader bool
}

func (r *statusRecorder) WriteHeader(status int) {
	if !r.wroteHeader {
		r.status = status
		r.wroteHeader = true
		r.ResponseWriter.WriteHeader(status)
	}
}

func (r *statusRecorder) Write(b []byte) (int, error) {
	if !r.wroteHeader {
		r.wroteHeader = true
	}
	return r.ResponseWriter.Write(b)
}

// routeTemplate maps a request to a stable, low-cardinality label. Variable
// segments (account IDs, job IDs, preview IDs, upload IDs) are collapsed to
// placeholders, and anything unrecognized collapses to "other" so an attacker
// cannot inflate cardinality or embed content through the path.
func routeTemplate(method, path string) string {
	segments := strings.Split(strings.Trim(path, "/"), "/")
	switch {
	case path == "/healthz":
		return method + " /healthz"
	case matches(segments, "v1", "auth", "apple"):
		return method + " /v1/auth/apple"
	case matches(segments, "v1", "account"):
		return method + " /v1/account"
	case len(segments) == 4 && segments[0] == "v1" && segments[1] == "import-jobs" && segments[3] == "upload-authorizations":
		return method + " /v1/import-jobs/{jobId}/upload-authorizations"
	case len(segments) == 6 && segments[0] == "v1" && segments[1] == "import-jobs" &&
		segments[3] == "upload-authorizations" && segments[5] == "complete":
		return method + " /v1/import-jobs/{jobId}/upload-authorizations/{id}/complete"
	case len(segments) == 5 && segments[0] == "v1" && segments[1] == "import-jobs" &&
		segments[3] == "upload-authorizations":
		return method + " /v1/import-jobs/{jobId}/upload-authorizations/{id}"
	case len(segments) == 4 && segments[0] == "v1" && segments[1] == "import-jobs" && segments[3] == "preview":
		return method + " /v1/import-jobs/{jobId}/preview"
	case len(segments) == 4 && segments[0] == "v1" && segments[1] == "previews" && segments[3] == "apply":
		return method + " /v1/previews/{previewId}/apply"
	default:
		return method + " other"
	}
}

func matches(segments []string, expected ...string) bool {
	if len(segments) != len(expected) {
		return false
	}
	for i := range expected {
		if segments[i] != expected[i] {
			return false
		}
	}
	return true
}

func severityForStatus(status int) obslog.Severity {
	switch {
	case status >= 500:
		return obslog.SeverityError
	case status >= 400:
		return obslog.SeverityWarn
	default:
		return obslog.SeverityInfo
	}
}

func outcomeForStatus(status int) obslog.Outcome {
	switch {
	case status >= 500:
		return obslog.OutcomeFailure
	case status >= 400:
		return obslog.OutcomeRejected
	default:
		return obslog.OutcomeSuccess
	}
}

// failureClassForStatus maps a status range to a coarse failure class. It is
// deliberately coarse: the middleware sees only the status, not why, so it does
// not invent a specific class it cannot know. 401 is authentication, 403 is
// authorization, 429 is rate limiting, other 4xx is invalid request, 5xx is an
// internal invariant unless a more specific handler recorded otherwise.
func failureClassForStatus(status int) obslog.FailureClass {
	switch {
	case status == http.StatusUnauthorized:
		return obslog.FailureAuthentication
	case status == http.StatusForbidden:
		return obslog.FailureAuthorization
	case status == http.StatusTooManyRequests:
		return obslog.FailureRateLimited
	case status >= 500:
		return obslog.FailureInternalInvariant
	case status >= 400:
		return obslog.FailureInvalidRequest
	default:
		return obslog.FailureNone
	}
}
