package httpserver

import (
	"net/http"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/metrics"
	"github.com/m-shogo/memories-project/services/import-api/internal/obslog"
	"github.com/m-shogo/memories-project/services/import-api/internal/ratelimit"
	"github.com/m-shogo/memories-project/services/import-api/internal/reqid"
)

// RateLimitConfig carries the enforcer and key deriver into the middleware. A
// nil enforcer disables rate limiting (the limiter never blocks the path when
// unconfigured), which keeps dev and tests that do not exercise it unchanged.
type RateLimitConfig struct {
	Enforcer *ratelimit.Enforcer
	Deriver  ratelimit.KeyDeriver
}

// rateLimitMiddleware enforces per-route policies before the request reaches any
// handler, so a rejected request creates no account, session, replay row,
// upload, deletion state or background work — it never gets that far. It sits
// inside the observability middleware (so a 429 still carries a request ID and
// is logged) and outside the router (so the decision precedes body decode and
// the Apple exchange).
func rateLimitMiddleware(config RateLimitConfig, logger *obslog.Logger, recorder metrics.Recorder, next http.Handler) http.Handler {
	if config.Enforcer == nil {
		return next
	}
	return http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		start := time.Now()
		route := routeTemplate(request.Method, request.URL.Path)
		requestID := reqid.RequestID(request.Context())

		routeKey := config.Deriver.RouteKey(route)
		networkKey := config.Deriver.NetworkKey(request.RemoteAddr, request.Header.Get("X-Forwarded-For"))

		result := config.Enforcer.Check(route, routeKey, networkKey)
		recorder.RecordRateLimitDecision(route, route, metricsRouteClass(route),
			metricsRateLimitOutcome(result), metricsRateLimitFailure(result), time.Since(start))
		if result.Reason == ratelimit.ReasonStoreUnavailable {
			recorder.RecordRateLimitStoreFailure(route, route)
		}
		if result.Allowed {
			// Exempt routes (health) are logged at debug only when a policy
			// applied; a plain exempt is not logged to avoid noise.
			if result.Reason != ratelimit.ReasonExempt {
				logger.Emit(rateLimitEvent(obslog.EventRateLimitAllowed, obslog.SeverityDebug,
					obslog.OutcomeSuccess, route, result.PolicyID, requestID, nil))
			}
			next.ServeHTTP(writer, request)
			return
		}

		code, severity := rateLimitEventCode(result.Reason)
		logger.Emit(rateLimitEvent(code, severity, obslog.OutcomeRejected, route, result.PolicyID, requestID,
			obslog.BoolPtr(true)))

		retryAfter := boundedRetryAfterSeconds(result.RetryAfter)
		writer.Header().Set("Content-Type", "application/json")
		writer.Header().Set("Cache-Control", "no-store")
		writer.Header().Set("Retry-After", retryAfter)
		writer.WriteHeader(http.StatusTooManyRequests)
		// A generic body: a stable public code and nothing about the policy, the
		// key, the network, remaining tokens or which guard tripped.
		_, _ = writer.Write([]byte(`{"code":"SEC_RATE_LIMITED"}`))
	})
}

// rateLimitEvent builds a rate-limit obslog event. It carries only the route
// template, the policy id, the outcome, the request id and retryability —
// never a raw key, an address, a token or an error string.
func rateLimitEvent(code obslog.EventCode, severity obslog.Severity, outcome obslog.Outcome,
	route, policyID, requestID string, retryable *bool) obslog.Event {
	return obslog.Event{
		Severity:     severity,
		EventName:    "rate_limit",
		EventCode:    code,
		Component:    obslog.ComponentRateLimit,
		Operation:    policyID,
		Outcome:      outcome,
		RequestID:    requestID,
		Route:        route,
		Retryable:    retryable,
		FailureClass: rateLimitFailureClass(code),
	}
}

func rateLimitEventCode(reason ratelimit.Reason) (obslog.EventCode, obslog.Severity) {
	switch reason {
	case ratelimit.ReasonStoreUnavailable:
		return obslog.EventRateLimitStoreUnavailable, obslog.SeverityError
	case ratelimit.ReasonEmergencyFallback:
		return obslog.EventRateLimitEmergencyFallback, obslog.SeverityWarn
	case ratelimit.ReasonKeyCapacity:
		return obslog.EventRateLimitKeyCapacity, obslog.SeverityWarn
	case ratelimit.ReasonPolicyInvalid:
		return obslog.EventRateLimitPolicyInvalid, obslog.SeverityError
	default:
		return obslog.EventRateLimitRejected, obslog.SeverityWarn
	}
}

func rateLimitFailureClass(code obslog.EventCode) obslog.FailureClass {
	if code == obslog.EventRateLimitPolicyInvalid {
		return obslog.FailureInternalInvariant
	}
	return obslog.FailureRateLimited
}

// boundedRetryAfterSeconds renders a Retry-After in whole seconds, clamped to a
// sane range so no negative, zero or overflowing value is ever emitted.
func boundedRetryAfterSeconds(d time.Duration) string {
	seconds := int64(d / time.Second)
	if d%time.Second != 0 {
		seconds++
	}
	if seconds < 1 {
		seconds = 1
	}
	if seconds > 3600 {
		seconds = 3600
	}
	return itoa(seconds)
}

func itoa(v int64) string {
	if v == 0 {
		return "0"
	}
	var buf [20]byte
	i := len(buf)
	for v > 0 {
		i--
		buf[i] = byte('0' + v%10)
		v /= 10
	}
	return string(buf[i:])
}

func metricsRateLimitOutcome(result ratelimit.Result) metrics.Outcome {
	switch {
	case result.Allowed:
		return metrics.OutcomeSuccess
	case result.Reason == ratelimit.ReasonRejected:
		return metrics.OutcomeRejected
	default:
		return metrics.OutcomeFailure
	}
}

func metricsRateLimitFailure(result ratelimit.Result) metrics.FailureClass {
	switch result.Reason {
	case ratelimit.ReasonRejected:
		return metrics.FailRateLimited
	case ratelimit.ReasonStoreUnavailable:
		return metrics.FailStoreUnavail
	case ratelimit.ReasonPolicyInvalid:
		return metrics.FailInternal
	default:
		return metrics.FailNone
	}
}
