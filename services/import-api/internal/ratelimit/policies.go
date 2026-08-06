package ratelimit

// DefaultPolicies is the shipped route policy set. The numbers are conservative
// starting points, not load-calibrated production limits — OPS-P0-005 stays
// PARTIAL precisely because these are assumptions, not measurements. They are
// bundled here as a single source so the middleware, the tests and the
// machine-readable contract stay aligned.
//
// The pre-authentication Apple exchange is the strictest: it is public, it does
// expensive work (RSA verify, an outbound Apple call, DB writes), and it can
// create accounts, so it carries both a whole-route global guard and a strict
// per-network guard, and fails closed with a strict local emergency fallback.
func DefaultPolicies() []RoutePolicy {
	return []RoutePolicy{
		{
			RouteTemplate: "POST /v1/auth/apple",
			Class:         ClassPublicUnauthenticated,
			Enabled:       true,
			FailureMode:   FailClosedEmergencyLocal,
			Global:        Policy{ID: "apple-global", Capacity: 100, RefillPerSec: 20},
			Network:       Policy{ID: "apple-network", Capacity: 5, RefillPerSec: 0.2},
		},
		{
			RouteTemplate: "DELETE /v1/account",
			Class:         ClassPublicAuthenticated,
			Enabled:       true,
			FailureMode:   FailClosed,
			Global:        Policy{ID: "delete-global", Capacity: 50, RefillPerSec: 10},
			Network:       Policy{ID: "delete-network", Capacity: 5, RefillPerSec: 0.5},
		},
		{
			RouteTemplate: "POST /v1/import-jobs/{jobId}/upload-authorizations",
			Class:         ClassPublicAuthenticated,
			Enabled:       true,
			FailureMode:   FailClosed,
			Global:        Policy{ID: "upload-issue-global", Capacity: 200, RefillPerSec: 50},
			Network:       Policy{ID: "upload-issue-network", Capacity: 20, RefillPerSec: 2},
		},
		{
			RouteTemplate: "POST /v1/upload-authorizations/{id}/complete",
			Class:         ClassPublicAuthenticated,
			Enabled:       true,
			FailureMode:   FailClosed,
			Global:        Policy{ID: "upload-complete-global", Capacity: 200, RefillPerSec: 50},
			Network:       Policy{ID: "upload-complete-network", Capacity: 20, RefillPerSec: 2},
		},
		{
			RouteTemplate: "GET /v1/import-jobs/{jobId}/preview",
			Class:         ClassPublicAuthenticated,
			Enabled:       true,
			FailureMode:   FailClosed,
			Global:        Policy{ID: "preview-global", Capacity: 400, RefillPerSec: 100},
			Network:       Policy{ID: "preview-network", Capacity: 40, RefillPerSec: 5},
		},
		{
			RouteTemplate: "POST /v1/previews/{previewId}/apply",
			Class:         ClassPublicAuthenticated,
			Enabled:       true,
			FailureMode:   FailClosed,
			Global:        Policy{ID: "apply-global", Capacity: 100, RefillPerSec: 20},
			Network:       Policy{ID: "apply-network", Capacity: 10, RefillPerSec: 1},
		},
		{
			// Unmatched routes get a global-only guard so a flood of 404s is
			// still bounded; there is no meaningful per-network budget for
			// requests that match no route, so it reuses the global key.
			RouteTemplate: "other",
			Class:         ClassPublicUnauthenticated,
			Enabled:       true,
			FailureMode:   FailClosed,
			Global:        Policy{ID: "other-global", Capacity: 100, RefillPerSec: 20},
			Network:       Policy{ID: "other-network", Capacity: 20, RefillPerSec: 5},
		},
		{
			// Health is never coupled to the rate-limit store.
			RouteTemplate: "GET /healthz",
			Class:         ClassHealth,
			Enabled:       false,
			FailureMode:   HealthExempt,
		},
	}
}
