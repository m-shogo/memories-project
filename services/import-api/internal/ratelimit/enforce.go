package ratelimit

import (
	"errors"
	"time"
)

// RouteClass classifies a route for limiting and failure-mode purposes. It
// mirrors the machine-readable rate-limit policy contract.
type RouteClass string

const (
	ClassPublicUnauthenticated RouteClass = "PUBLIC_UNAUTHENTICATED"
	ClassPublicAuthenticated   RouteClass = "PUBLIC_AUTHENTICATED"
	ClassHealth                RouteClass = "HEALTH"
	ClassInternal              RouteClass = "INTERNAL"
)

// FailureMode decides what happens when the store cannot make a decision. It is
// per route class so a store outage does not uniformly break health checks or
// uniformly fail open on the pre-auth surface.
type FailureMode string

const (
	// FailClosed denies the request when the store errors. Used for the public
	// pre-auth surface: an outage must not become an open door.
	FailClosed FailureMode = "fail_closed"
	// FailClosedEmergencyLocal tries a strict local fallback limiter when the
	// primary (distributed) store errors, and denies only if that also fails —
	// so a distributed-store blip degrades to strict local limiting rather than
	// either an open door or a total outage.
	FailClosedEmergencyLocal FailureMode = "fail_closed_emergency_local"
	// HealthExempt never consults the store, so health/readiness is never
	// coupled to the rate-limit store's availability.
	HealthExempt FailureMode = "health_exempt"
)

// RoutePolicy is the enforcement rule for one route template. Global bounds the
// whole route regardless of source; Network bounds a single derived network.
// Both are consulted; either exhausting denies.
type RoutePolicy struct {
	RouteTemplate string
	Class         RouteClass
	Enabled       bool
	FailureMode   FailureMode
	Global        Policy
	Network       Policy
}

// Reason is the classified outcome of an enforcement check, mapped by the
// caller to an obslog event code. It never carries a raw key or address.
type Reason string

const (
	ReasonAllowed           Reason = "allowed"
	ReasonRejected          Reason = "rejected"
	ReasonStoreUnavailable  Reason = "store_unavailable"
	ReasonEmergencyFallback Reason = "emergency_fallback"
	ReasonKeyCapacity       Reason = "key_capacity"
	ReasonPolicyInvalid     Reason = "policy_invalid"
	ReasonExempt            Reason = "exempt"
)

// Result is the enforcement decision. RetryAfter is bounded and only set on a
// denial. PolicyID identifies which policy decided, for observability.
type Result struct {
	Allowed    bool
	Reason     Reason
	RetryAfter time.Duration
	PolicyID   string
}

// Enforcer applies route policies using a primary store and, for the emergency
// fallback mode, a strict local store. It holds no per-request state.
type Enforcer struct {
	primary  Store
	fallback Store
	policies map[string]RoutePolicy
	now      func() time.Time
}

// NewEnforcer validates every policy up front so an invalid configuration fails
// closed at construction rather than at the first request.
func NewEnforcer(primary, fallback Store, policies []RoutePolicy) (*Enforcer, error) {
	if primary == nil {
		return nil, errors.New("enforcer requires a primary store")
	}
	byRoute := make(map[string]RoutePolicy, len(policies))
	for _, policy := range policies {
		if policy.RouteTemplate == "" {
			return nil, errors.New("route policy requires a route template")
		}
		if _, dup := byRoute[policy.RouteTemplate]; dup {
			return nil, errors.New("duplicate route policy: " + policy.RouteTemplate)
		}
		if policy.Enabled && policy.FailureMode != HealthExempt {
			if err := policy.Global.Validate(); err != nil {
				return nil, errors.New(policy.RouteTemplate + " global: " + err.Error())
			}
			if err := policy.Network.Validate(); err != nil {
				return nil, errors.New(policy.RouteTemplate + " network: " + err.Error())
			}
		}
		byRoute[policy.RouteTemplate] = policy
	}
	return &Enforcer{primary: primary, fallback: fallback, policies: byRoute, now: time.Now}, nil
}

// Policy returns the policy for a route template and whether one exists.
func (e *Enforcer) Policy(routeTemplate string) (RoutePolicy, bool) {
	policy, ok := e.policies[routeTemplate]
	return policy, ok
}

// Check enforces the policy for a route. routeKey is the route-wide global key
// and networkKey is the per-network key; both are pre-derived opaque digests.
// A route with no policy, disabled, or health-exempt is allowed without
// touching the store.
func (e *Enforcer) Check(routeTemplate, routeKey, networkKey string) Result {
	policy, ok := e.policies[routeTemplate]
	if !ok || !policy.Enabled || policy.FailureMode == HealthExempt {
		return Result{Allowed: true, Reason: ReasonExempt}
	}
	now := e.now()

	// Global guard first: a route can be flooded from many sources each under
	// the per-network threshold, so the whole-route bound must also hold.
	if result := e.consume(policy, routeKey, policy.Global, now); !result.Allowed {
		return result
	}
	return e.consume(policy, networkKey, policy.Network, now)
}

func (e *Enforcer) consume(policy RoutePolicy, key string, tokenPolicy Policy, now time.Time) Result {
	decision, err := e.primary.Take(key, tokenPolicy, now)
	if err == nil {
		if decision.Allowed {
			return Result{Allowed: true, Reason: ReasonAllowed, PolicyID: policy.RouteTemplate}
		}
		return Result{Allowed: false, Reason: ReasonRejected, RetryAfter: decision.RetryAfter, PolicyID: policy.RouteTemplate}
	}

	// A policy-invalid error is a configuration fault, always fail closed.
	if !errors.Is(err, ErrStoreUnavailable) && !errors.Is(err, ErrKeyCapacity) {
		return Result{Allowed: false, Reason: ReasonPolicyInvalid, RetryAfter: time.Second, PolicyID: policy.RouteTemplate}
	}
	if errors.Is(err, ErrKeyCapacity) {
		// The key table is full: deny rather than admit an unbounded key.
		return Result{Allowed: false, Reason: ReasonKeyCapacity, RetryAfter: time.Second, PolicyID: policy.RouteTemplate}
	}

	// Store unavailable: apply the route's failure mode.
	switch policy.FailureMode {
	case FailClosedEmergencyLocal:
		if e.fallback != nil {
			if decision, ferr := e.fallback.Take(key, tokenPolicy, now); ferr == nil {
				if decision.Allowed {
					return Result{Allowed: true, Reason: ReasonEmergencyFallback, PolicyID: policy.RouteTemplate}
				}
				return Result{Allowed: false, Reason: ReasonRejected, RetryAfter: decision.RetryAfter, PolicyID: policy.RouteTemplate}
			}
		}
		return Result{Allowed: false, Reason: ReasonStoreUnavailable, RetryAfter: time.Second, PolicyID: policy.RouteTemplate}
	default: // FailClosed
		return Result{Allowed: false, Reason: ReasonStoreUnavailable, RetryAfter: time.Second, PolicyID: policy.RouteTemplate}
	}
}
