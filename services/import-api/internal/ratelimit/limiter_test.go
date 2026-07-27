package ratelimit

import (
	"errors"
	"fmt"
	"sync"
	"testing"
	"time"
)

func policy() Policy { return Policy{ID: "p", Capacity: 3, RefillPerSec: 1} }

func TestBurstThenRefill(t *testing.T) {
	store := NewMemoryStore(100, time.Minute)
	base := time.Unix(1_800_000_000, 0)

	// Capacity is 3: the first three are allowed instantly (the burst).
	for i := 0; i < 3; i++ {
		d, err := store.Take("k", policy(), base)
		if err != nil || !d.Allowed {
			t.Fatalf("burst token %d denied: %v %v", i, d, err)
		}
	}
	// The fourth in the same instant is denied with a bounded Retry-After.
	d, err := store.Take("k", policy(), base)
	if err != nil || d.Allowed {
		t.Fatalf("over-burst allowed: %v %v", d, err)
	}
	if d.RetryAfter < time.Second || d.RetryAfter > time.Hour {
		t.Fatalf("Retry-After not bounded: %v", d.RetryAfter)
	}
	// After one second, exactly one token has refilled.
	d, err = store.Take("k", policy(), base.Add(time.Second))
	if err != nil || !d.Allowed {
		t.Fatalf("refilled token denied: %v %v", d, err)
	}
	d, _ = store.Take("k", policy(), base.Add(time.Second))
	if d.Allowed {
		t.Fatal("a second token appeared within one second")
	}
}

func TestRefillIsCappedAtCapacity(t *testing.T) {
	store := NewMemoryStore(100, time.Minute)
	base := time.Unix(1_800_000_000, 0)
	store.Take("k", policy(), base) // create bucket, consume 1
	// A very long idle must not accumulate more than capacity tokens.
	for i := 0; i < 3; i++ {
		if d, _ := store.Take("k", policy(), base.Add(time.Hour)); !d.Allowed {
			t.Fatalf("token %d after long idle denied", i)
		}
	}
	if d, _ := store.Take("k", policy(), base.Add(time.Hour)); d.Allowed {
		t.Fatal("idle accumulated more than capacity")
	}
}

func TestBackwardClockDoesNotMintTokens(t *testing.T) {
	store := NewMemoryStore(100, time.Minute)
	base := time.Unix(1_800_000_000, 0)
	for i := 0; i < 3; i++ {
		store.Take("k", policy(), base)
	}
	// A clock jump backward must not refill.
	if d, _ := store.Take("k", policy(), base.Add(-time.Hour)); d.Allowed {
		t.Fatal("a backward clock jump minted a token")
	}
}

func TestInvalidPolicyIsRejected(t *testing.T) {
	store := NewMemoryStore(100, time.Minute)
	base := time.Unix(1_800_000_000, 0)
	for _, bad := range []Policy{
		{ID: "", Capacity: 1, RefillPerSec: 1},
		{ID: "p", Capacity: 0, RefillPerSec: 1},
		{ID: "p", Capacity: -1, RefillPerSec: 1},
		{ID: "p", Capacity: 1, RefillPerSec: 0},
		{ID: "p", Capacity: 1, RefillPerSec: -1},
		{ID: "p", Capacity: 2_000_000, RefillPerSec: 1},
		{ID: "p", Capacity: 1, RefillPerSec: 2_000_000},
	} {
		if _, err := store.Take("k", bad, base); err == nil {
			t.Fatalf("invalid policy accepted: %+v", bad)
		}
	}
}

func TestKeyCardinalityIsBounded(t *testing.T) {
	store := NewMemoryStore(2, time.Minute)
	base := time.Unix(1_800_000_000, 0)
	// Two distinct keys fit.
	for i := 0; i < 2; i++ {
		if _, err := store.Take(fmt.Sprintf("k%d", i), policy(), base); err != nil {
			t.Fatalf("key %d rejected under cap: %v", i, err)
		}
	}
	// A third fresh key is refused (fail-closed), not admitted by growing memory.
	if _, err := store.Take("k-overflow", policy(), base); !errors.Is(err, ErrKeyCapacity) {
		t.Fatalf("cardinality cap not enforced: %v", err)
	}
}

func TestCleanupReclaimsIdleKeys(t *testing.T) {
	store := NewMemoryStore(100, time.Minute)
	base := time.Unix(1_800_000_000, 0)
	store.Take("k", policy(), base)
	if store.Len() != 1 {
		t.Fatalf("expected 1 key, got %d", store.Len())
	}
	// After the idle TTL, cleanup reclaims it.
	if store.Cleanup(base.Add(2 * time.Minute)); store.Len() != 0 {
		t.Fatalf("idle key not reclaimed: %d", store.Len())
	}
	// A capacity-full store reclaims idle keys to admit a new one.
	small := NewMemoryStore(1, time.Minute)
	small.Take("old", policy(), base)
	if _, err := small.Take("new", policy(), base.Add(2*time.Minute)); err != nil {
		t.Fatalf("full store did not reclaim idle key for a new one: %v", err)
	}
}

// TestConcurrentTakeIsRaceSafeAndDoesNotOverAllow runs many goroutines against
// one key at a fixed instant; the total allowed must never exceed capacity.
func TestConcurrentTakeIsRaceSafeAndDoesNotOverAllow(t *testing.T) {
	store := NewMemoryStore(100, time.Minute)
	base := time.Unix(1_800_000_000, 0)
	const capacity = 5
	p := Policy{ID: "p", Capacity: capacity, RefillPerSec: 0.001}

	var allowed int64
	var mu sync.Mutex
	var wg sync.WaitGroup
	for i := 0; i < 200; i++ {
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
	if allowed != capacity {
		t.Fatalf("concurrent takes allowed %d, expected exactly %d", allowed, capacity)
	}
}
