package ratelimit

import (
	"errors"
	"sync"
	"testing"
	"time"
)

// This file states the contract any Store — the in-memory one today, a shared
// atomic store in production — must satisfy. A production distributed store is
// not implemented; these tests define what it must do and verify the in-memory
// store and representative fakes against that contract, so the requirement is
// executable rather than only prose.

// TestStoreContractAtomicConsume: two concurrent takes of the last token must
// not both succeed. Proven against the in-memory store.
func TestStoreContractAtomicConsume(t *testing.T) {
	store := NewMemoryStore(10, time.Minute)
	base := time.Unix(1_800_000_000, 0)
	p := Policy{ID: "p", Capacity: 1, RefillPerSec: 0.0001}

	var allowed int
	var mu sync.Mutex
	var wg sync.WaitGroup
	for i := 0; i < 64; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if d, err := store.Take("k", p, base); err == nil && d.Allowed {
				mu.Lock()
				allowed++
				mu.Unlock()
			}
		}()
	}
	wg.Wait()
	if allowed != 1 {
		t.Fatalf("atomic consume violated: %d takes allowed for a 1-token bucket", allowed)
	}
}

// timeoutStore models a store that times out: it must surface an error the
// enforcer treats as unavailable, never a silent allow.
type timeoutStore struct{}

func (timeoutStore) Take(string, Policy, time.Time) (Decision, error) {
	return Decision{}, ErrStoreUnavailable
}

// TestStoreContractTimeoutIsNotAllow: a store timeout must be an error, and the
// enforcer must fail closed on a public route rather than allow.
func TestStoreContractTimeoutIsNotAllow(t *testing.T) {
	d, err := timeoutStore{}.Take("k", Policy{ID: "p", Capacity: 1, RefillPerSec: 1}, time.Now())
	if err == nil {
		t.Fatal("a timeout must surface as an error, not a decision")
	}
	if d.Allowed {
		t.Fatal("a timeout must never carry an allow")
	}
	if !errors.Is(err, ErrStoreUnavailable) {
		t.Fatalf("timeout should map to ErrStoreUnavailable, got %v", err)
	}

	enf, _ := NewEnforcer(timeoutStore{}, nil, []RoutePolicy{{
		RouteTemplate: "POST /v1/auth/apple", Class: ClassPublicUnauthenticated, Enabled: true,
		FailureMode: FailClosed,
		Global:      Policy{ID: "g", Capacity: 1, RefillPerSec: 1},
		Network:     Policy{ID: "n", Capacity: 1, RefillPerSec: 1},
	}})
	if r := enf.Check("POST /v1/auth/apple", "rk", "nk"); r.Allowed {
		t.Fatal("public route allowed under store timeout")
	}
}

// duplicateConcurrentStore counts concurrent in-flight consumes to prove the
// enforcer issues one consume per guard per check (no accidental double-spend
// amplification) — the store still owns cross-node atomicity.
func TestStoreContractDeterministicConsumeCount(t *testing.T) {
	counter := &countingStore{inner: NewMemoryStore(100, time.Minute)}
	enf, _ := NewEnforcer(counter, nil, []RoutePolicy{{
		RouteTemplate: "POST /v1/auth/apple", Class: ClassPublicUnauthenticated, Enabled: true,
		FailureMode: FailClosed,
		Global:      Policy{ID: "g", Capacity: 100, RefillPerSec: 100},
		Network:     Policy{ID: "n", Capacity: 100, RefillPerSec: 100},
	}})
	enf.Check("POST /v1/auth/apple", "rk", "nk")
	// Exactly two consumes: the global guard then the network guard.
	if counter.count != 2 {
		t.Fatalf("expected exactly 2 store consumes per check, got %d", counter.count)
	}
}

type countingStore struct {
	inner Store
	count int
}

func (c *countingStore) Take(key string, p Policy, now time.Time) (Decision, error) {
	c.count++
	return c.inner.Take(key, p, now)
}

// TestStoreContractExpiryReclaims: a store must not grow without bound; expired
// keys are reclaimable. Proven against the in-memory store.
func TestStoreContractExpiryReclaims(t *testing.T) {
	store := NewMemoryStore(1000, 30*time.Second)
	base := time.Unix(1_800_000_000, 0)
	for i := 0; i < 100; i++ {
		store.Take(string(rune('a'+i%26))+string(rune('0'+i/26)), Policy{ID: "p", Capacity: 1, RefillPerSec: 1}, base)
	}
	before := store.Len()
	store.Cleanup(base.Add(time.Minute))
	if store.Len() != 0 || before == 0 {
		t.Fatalf("expiry did not reclaim keys: before=%d after=%d", before, store.Len())
	}
}
