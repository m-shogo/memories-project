package httpserver

import (
	"net/http"
	"strings"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/metrics"
	"github.com/m-shogo/memories-project/services/import-api/internal/obslog"
	"github.com/m-shogo/memories-project/services/import-api/internal/reqid"
)

// observabilityMiddleware is the outermost wrapper. It assigns a validated,
// non-secret request ID, returns it in the response header, propagates it
// through context, recovers panics into a bounded event plus a 500, and emits
// exactly one structured request event carrying method, a low-cardinality route
// template, status, duration and a failure class — never a token, a path
// containing an account or job ID, a query string or an error string.
func observabilityMiddleware(logger *obslog.Logger, recorder metrics.Recorder, next http.Handler) http.Handler {
	return http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		start := time.Now()
		recorder.IncHTTPInFlight(1)
		defer recorder.IncHTTPInFlight(-1)

		requestID, _ := reqid.FromInbound(request.Header.Get("X-Request-Id"))
		writer.Header().Set("X-Request-Id", requestID)
		ctx := reqid.WithRequestID(request.Context(), requestID)
		request = request.WithContext(ctx)

		rec := &statusRecorder{ResponseWriter: writer, status: http.StatusOK}
		route := routeTemplate(request.Method, request.URL.Path)

		defer func() {
			if recovered := recover(); recovered != nil {
				// A panic never reaches the client as detail: a fixed 500 body
				// and a bounded event with no recovered value, no stack, no
				// request content.
				if !rec.wroteHeader {
					rec.Header().Set("Content-Type", "application/json")
					rec.Header().Set("Cache-Control", "no-store")
					rec.WriteHeader(http.StatusInternalServerError)
					_, _ = rec.Write([]byte(`{"code":"SEC_INTERNAL_ERROR"}`))
				}
				recorder.RecordHTTPPanic(route, metricsRouteClass(route))
				recorder.RecordHTTPRequest(route, metricsRouteClass(route), metrics.MethodFor(request.Method),
					metrics.Status5xx, metrics.OutcomeFailure, time.Since(start))
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

		next.ServeHTTP(rec, request)

		recorder.RecordHTTPRequest(route, metricsRouteClass(route), metrics.MethodFor(request.Method),
			metrics.StatusClassFor(rec.status), metricsOutcomeForStatus(rec.status), time.Since(start))
		logger.Emit(obslog.Event{
			Severity:     severityForStatus(rec.status),
			EventName:    "http.request",
			EventCode:    obslog.EventHTTPRequest,
			Component:    obslog.ComponentHTTP,
			Operation:    "serve",
			Outcome:      outcomeForStatus(rec.status),
			RequestID:    requestID,
			HTTPMethod:   request.Method,
			Route:        route,
			StatusCode:   obslog.IntPtr(rec.status),
			DurationMs:   obslog.Int64Ptr(time.Since(start).Milliseconds()),
			FailureClass: failureClassForStatus(rec.status),
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
	case method == http.MethodGet && path == "/metrics":
		return "GET /metrics"
	case matches(segments, "v1", "auth", "apple"):
		return method + " /v1/auth/apple"
	case matches(segments, "v1", "account"):
		return method + " /v1/account"
	case len(segments) == 4 && segments[0] == "v1" && segments[1] == "import-jobs" && segments[3] == "upload-authorizations":
		return method + " /v1/import-jobs/{jobId}/upload-authorizations"
	case len(segments) == 4 && segments[0] == "v1" &&
		segments[1] == "upload-authorizations" && segments[3] == "complete":
		return method + " /v1/upload-authorizations/{id}/complete"
	case len(segments) == 4 && segments[0] == "v1" && segments[1] == "import-jobs" && segments[3] == "preview":
		return method + " /v1/import-jobs/{jobId}/preview"
	case len(segments) == 4 && segments[0] == "v1" && segments[1] == "previews" && segments[3] == "apply":
		return method + " /v1/previews/{previewId}/apply"
	default:
		return method + " other"
	}
}

// knownAPIRouteShape is the pre-auth route-shape authority. It is deliberately
// separate from routeTemplate: the legacy /uploads tombstone must authenticate
// before returning 404 so a revoked session is still rejected consistently,
// but it remains the low-cardinality "other" metrics label and is not restored
// as a supported API. Every other unknown shape is rejected before session
// lookup to prevent hostile cardinality from becoming dependency load.
func knownAPIRouteShape(path string) bool {
	segments := strings.Split(strings.Trim(path, "/"), "/")
	switch {
	case matches(segments, "v1", "auth", "apple"):
		return true
	case matches(segments, "v1", "account"):
		return true
	case len(segments) == 4 && segments[0] == "v1" &&
		segments[1] == "import-jobs" && segments[3] == "upload-authorizations":
		return true
	case len(segments) == 4 && segments[0] == "v1" &&
		segments[1] == "upload-authorizations" && segments[3] == "complete":
		return true
	case len(segments) == 4 && segments[0] == "v1" &&
		segments[1] == "import-jobs" && segments[3] == "preview":
		return true
	case len(segments) == 4 && segments[0] == "v1" &&
		segments[1] == "previews" && segments[3] == "apply":
		return true
	case len(segments) == 4 && segments[0] == "v1" &&
		segments[1] == "import-jobs" && segments[3] == "uploads":
		// Explicit unsupported legacy tombstone; authentication still runs,
		// then the protected mux returns 404 without issuing an upload.
		return true
	default:
		return false
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

// metricsRouteClass maps a route template to its metrics route class using the
// same fixed table the rate-limit policies use.
func metricsRouteClass(route string) metrics.RouteClass {
	switch {
	case route == "GET /healthz":
		return metrics.RouteHealth
	case route == "GET /metrics":
		return metrics.RouteInternal
	case route == "POST /v1/auth/apple", strings.HasSuffix(route, " other"):
		// The pre-auth Apple exchange and any unmatched route are treated as the
		// public unauthenticated class for metrics purposes.
		return metrics.RoutePublicUnauthenticated
	default:
		return metrics.RoutePublicAuthenticated
	}
}

// metricsOutcomeForStatus maps a status to the metrics outcome enum.
func metricsOutcomeForStatus(status int) metrics.Outcome {
	switch {
	case status >= 500:
		return metrics.OutcomeFailure
	case status >= 400:
		return metrics.OutcomeRejected
	default:
		return metrics.OutcomeSuccess
	}
}
