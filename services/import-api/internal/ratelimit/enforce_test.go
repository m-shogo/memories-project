package ratelimit

import (
	"testing"
	"time"
)

// scriptedStore returns queued decisions/errors, for exercising store failure
// modes deterministically.
type scriptedStore struct {
	err      error
	decision Decision
	takes    int
}

func (s *scriptedStore) Take(string, Policy, time.Time) (Decision, error) {
	s.takes++
	if s.err != nil {
		return Decision{}, s.err
	}
	return s.decision, nil
}

func appleTestPolicy() RoutePolicy {
	return RoutePolicy{
		RouteTemplate: "POST /v1/auth/apple",
		Class:         ClassPublicUnauthenticated,
		Enabled:       true,
		FailureMode:   FailClosed,
		Global:        Policy{ID: "g", Capacity: 10, RefillPerSec: 1},
		Network:       Policy{ID: "n", Capacity: 3, RefillPerSec: 1},
	}
}

func TestEnforcerAllowsUnderBudget(t *testing.T) {
	enf, err := NewEnforcer(NewMemoryStore(100, time.Minute), nil, []RoutePolicy{appleTestPolicy()})
	if err != nil {
		t.Fatal(err)
	}
	r := enf.Check("POST /v1/auth/apple", "route_k", "net_k")
	if !r.Allowed || r.Reason != ReasonAllowed {
		t.Fatalf("under-budget denied: %+v", r)
	}
}

func TestEnforcerDeniesOverNetworkBudget(t *testing.T) {
	enf, _ := NewEnforcer(NewMemoryStore(100, time.Minute), nil, []RoutePolicy{appleTestPolicy()})
	// Network capacity is 3; the fourth from one network is denied even though
	// the global budget (10) is not exhausted.
	for i := 0; i < 3; i++ {
		if r := enf.Check("POST /v1/auth/apple", "route_k", "net_same"); !r.Allowed {
			t.Fatalf("network token %d denied early: %+v", i, r)
		}
	}
	r := enf.Check("POST /v1/auth/apple", "route_k", "net_same")
	if r.Allowed || r.Reason != ReasonRejected {
		t.Fatalf("over-network-budget allowed: %+v", r)
	}
	if r.RetryAfter < time.Second {
		t.Fatalf("Retry-After not bounded: %v", r.RetryAfter)
	}
}

func TestEnforcerGlobalGuardCatchesDistributedSources(t *testing.T) {
	policy := appleTestPolicy()
	policy.Global = Policy{ID: "g", Capacity: 3, RefillPerSec: 1}
	policy.Network = Policy{ID: "n", Capacity: 100, RefillPerSec: 100}
	enf, _ := NewEnforcer(NewMemoryStore(1000, time.Minute), nil, []RoutePolicy{policy})
	// Each request is a distinct network (under the per-network budget), but the
	// global route guard (3) still stops the flood.
	allowed := 0
	for i := 0; i < 10; i++ {
		if r := enf.Check("POST /v1/auth/apple", "route_shared", "net_"+string(rune('a'+i))); r.Allowed {
			allowed++
		}
	}
	if allowed != 3 {
		t.Fatalf("global guard allowed %d, expected 3", allowed)
	}
}

func TestEnforcerFailClosedOnStoreUnavailable(t *testing.T) {
	policy := appleTestPolicy()
	policy.FailureMode = FailClosed
	enf, _ := NewEnforcer(&scriptedStore{err: ErrStoreUnavailable}, nil, []RoutePolicy{policy})
	r := enf.Check("POST /v1/auth/apple", "route_k", "net_k")
	if r.Allowed || r.Reason != ReasonStoreUnavailable {
		t.Fatalf("public route did not fail closed on store outage: %+v", r)
	}
}

func TestEnforcerEmergencyFallbackOnStoreUnavailable(t *testing.T) {
	policy := appleTestPolicy()
	policy.FailureMode = FailClosedEmergencyLocal
	// Primary always unavailable; a strict local fallback still bounds requests.
	fallback := NewMemoryStore(100, time.Minute)
	enf, _ := NewEnforcer(&scriptedStore{err: ErrStoreUnavailable}, fallback, []RoutePolicy{policy})

	// Fallback network capacity is 3 (from the policy); first 3 pass via
	// fallback, then it denies — an outage degrades to strict local limiting,
	// never to an open door.
	allowed := 0
	for i := 0; i < 6; i++ {
		r := enf.Check("POST /v1/auth/apple", "route_k", "net_k")
		if r.Allowed {
			if r.Reason != ReasonEmergencyFallback {
				t.Fatalf("fallback allow not marked: %+v", r)
			}
			allowed++
		}
	}
	if allowed != 3 {
		t.Fatalf("emergency fallback allowed %d, expected the strict local budget of 3", allowed)
	}
}

func TestEnforcerFailsClosedWhenFallbackAlsoUnavailable(t *testing.T) {
	policy := appleTestPolicy()
	policy.FailureMode = FailClosedEmergencyLocal
	enf, _ := NewEnforcer(&scriptedStore{err: ErrStoreUnavailable}, &scriptedStore{err: ErrStoreUnavailable}, []RoutePolicy{policy})
	if r := enf.Check("POST /v1/auth/apple", "route_k", "net_k"); r.Allowed {
		t.Fatalf("both stores down but request allowed: %+v", r)
	}
}

func TestEnforcerKeyCapacityDenies(t *testing.T) {
	policy := appleTestPolicy()
	enf, _ := NewEnforcer(&scriptedStore{err: ErrKeyCapacity}, nil, []RoutePolicy{policy})
	r := enf.Check("POST /v1/auth/apple", "route_k", "net_k")
	if r.Allowed || r.Reason != ReasonKeyCapacity {
		t.Fatalf("key capacity did not deny: %+v", r)
	}
}

func TestEnforcerHealthIsExemptAndNeverTouchesStore(t *testing.T) {
	store := &scriptedStore{err: ErrStoreUnavailable}
	enf, _ := NewEnforcer(store, nil, DefaultPolicies())
	r := enf.Check("GET /healthz", "route_k", "net_k")
	if !r.Allowed || r.Reason != ReasonExempt {
		t.Fatalf("health was not exempt: %+v", r)
	}
	if store.takes != 0 {
		t.Fatal("health consulted the rate-limit store")
	}
}

func TestUnknownRouteIsAllowedWhenNoPolicy(t *testing.T) {
	enf, _ := NewEnforcer(NewMemoryStore(100, time.Minute), nil, []RoutePolicy{appleTestPolicy()})
	// A route with no policy in the set is allowed (the "other" default policy is
	// what bounds unmatched routes in the shipped set; here it is absent).
	if r := enf.Check("GET /v1/something-else", "route_k", "net_k"); !r.Allowed || r.Reason != ReasonExempt {
		t.Fatalf("unknown route not allowed as exempt: %+v", r)
	}
}

func TestInvalidPolicySetFailsConstruction(t *testing.T) {
	bad := appleTestPolicy()
	bad.Network = Policy{ID: "n", Capacity: 0, RefillPerSec: 1} // invalid
	if _, err := NewEnforcer(NewMemoryStore(100, time.Minute), nil, []RoutePolicy{bad}); err == nil {
		t.Fatal("invalid policy accepted at construction")
	}
	// Duplicate route templates are refused.
	dup := appleTestPolicy()
	if _, err := NewEnforcer(NewMemoryStore(100, time.Minute), nil, []RoutePolicy{appleTestPolicy(), dup}); err == nil {
		t.Fatal("duplicate route template accepted")
	}
}

func TestDefaultPoliciesConstruct(t *testing.T) {
	if _, err := NewEnforcer(NewMemoryStore(100, time.Minute), NewMemoryStore(100, time.Minute), DefaultPolicies()); err != nil {
		t.Fatalf("default policies failed to construct: %v", err)
	}
}
