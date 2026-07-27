// Package ratelimit is a bounded, fail-closed token-bucket rate limiter for the
// HTTP boundary, with the public pre-authentication Apple exchange as its
// primary target.
//
// Token bucket was chosen over fixed/sliding window and leaky bucket because it
// expresses the two properties the endpoints need directly — a sustained rate
// (refill) and a short burst allowance (capacity) — with bounded per-key memory,
// deterministic behaviour and a cheap concurrency-safe update. A fixed window
// allows a 2x burst at the boundary; a sliding-window approximation costs more
// state; a leaky bucket does not model burst as naturally. The trade-off is
// recorded in the checkpoint.
//
// The limiter is deliberately behind a Store interface. The in-memory store is
// single-instance only and is never presented as distributed production
// protection: a multi-instance deployment needs a shared atomic store, whose
// contract is defined and fake-tested here but not implemented.
package ratelimit

import (
	"errors"
	"sync"
	"time"
)

// ErrStoreUnavailable is what a Store returns when it cannot make a decision.
// The middleware maps it to a route-class-specific failure mode, never to a
// silent allow.
var ErrStoreUnavailable = errors.New("rate limit store unavailable")

// Policy is one immutable rate-limit rule. Capacity is the burst; RefillPerSec
// is the sustained rate. All values are validated on construction so a
// zero/negative/overflowing policy can never be enforced.
type Policy struct {
	ID           string
	Capacity     int64
	RefillPerSec float64
}

// Validate rejects nonsensical policies. An invalid policy must fail closed at
// wiring time, not silently disable a limit.
func (p Policy) Validate() error {
	if p.ID == "" {
		return errors.New("policy id required")
	}
	if p.Capacity <= 0 || p.Capacity > 1_000_000 {
		return errors.New("policy capacity out of range")
	}
	if p.RefillPerSec <= 0 || p.RefillPerSec > 1_000_000 {
		return errors.New("policy refill rate out of range")
	}
	return nil
}

// Decision is the outcome of one Take.
type Decision struct {
	Allowed bool
	// RetryAfter is a bounded, non-negative hint. It is only meaningful when
	// Allowed is false, and is clamped so a caller can never emit a negative or
	// overflowing Retry-After.
	RetryAfter time.Duration
}

// Store consumes one token for a key under a policy. Implementations must make
// the consume atomic per key so two concurrent requests cannot both take the
// last token. A store that cannot decide returns ErrStoreUnavailable rather
// than guessing.
type Store interface {
	Take(key string, policy Policy, now time.Time) (Decision, error)
}

// bucket is one key's token state. tokens is fractional so a sub-1/sec refill
// still makes progress. lastRefill is a wall+monotonic time; elapsed is clamped
// to >= 0 so a backward clock jump never mints tokens.
type bucket struct {
	tokens     float64
	lastRefill time.Time
	lastSeen   time.Time
}

// MemoryStore is an in-memory token-bucket store. Single instance only: it is
// not shared across processes and must never be treated as distributed
// production enforcement.
//
// Cardinality is bounded: at most MaxKeys distinct keys are tracked. When full,
// a new key is refused (ErrKeyCapacity) rather than evicting a live limit or
// growing without bound, so an attacker cannot exhaust memory by minting keys.
type MemoryStore struct {
	mu      sync.Mutex
	buckets map[string]*bucket
	maxKeys int
	idleTTL time.Duration
	now     func() time.Time
}

// ErrKeyCapacity is returned when the key table is full. The middleware treats
// it as a rejection (fail-closed), not an allow.
var ErrKeyCapacity = errors.New("rate limit key capacity reached")

// NewMemoryStore builds an in-memory store. maxKeys bounds cardinality; idleTTL
// is how long an untouched bucket survives before cleanup reclaims it.
func NewMemoryStore(maxKeys int, idleTTL time.Duration) *MemoryStore {
	if maxKeys <= 0 {
		maxKeys = 100_000
	}
	if idleTTL <= 0 {
		idleTTL = 10 * time.Minute
	}
	return &MemoryStore{
		buckets: make(map[string]*bucket),
		maxKeys: maxKeys,
		idleTTL: idleTTL,
		now:     time.Now,
	}
}

func (s *MemoryStore) Take(key string, policy Policy, now time.Time) (Decision, error) {
	if err := policy.Validate(); err != nil {
		return Decision{}, err
	}
	s.mu.Lock()
	defer s.mu.Unlock()

	existing, ok := s.buckets[key]
	if !ok {
		if len(s.buckets) >= s.maxKeys {
			// Opportunistic cleanup before refusing: reclaim idle keys so a
			// steady legitimate population is not permanently capped by churn.
			s.cleanupLocked(now)
		}
		if len(s.buckets) >= s.maxKeys {
			return Decision{}, ErrKeyCapacity
		}
		existing = &bucket{tokens: float64(policy.Capacity), lastRefill: now, lastSeen: now}
		s.buckets[key] = existing
	}

	// Refill: add tokens for elapsed time, clamped to [0, capacity]. A backward
	// clock jump yields zero elapsed rather than negative tokens.
	elapsed := now.Sub(existing.lastRefill)
	if elapsed < 0 {
		elapsed = 0
	}
	existing.tokens += elapsed.Seconds() * policy.RefillPerSec
	if existing.tokens > float64(policy.Capacity) {
		existing.tokens = float64(policy.Capacity)
	}
	existing.lastRefill = now
	existing.lastSeen = now

	if existing.tokens >= 1 {
		existing.tokens -= 1
		return Decision{Allowed: true}, nil
	}
	// Not enough for one token: report a bounded time until one is available.
	deficit := 1 - existing.tokens
	retry := time.Duration(deficit/policy.RefillPerSec*float64(time.Second)) + time.Second
	if retry < time.Second {
		retry = time.Second
	}
	if retry > time.Hour {
		retry = time.Hour
	}
	return Decision{Allowed: false, RetryAfter: retry}, nil
}

// Cleanup removes buckets untouched for longer than idleTTL. Callers run it on a
// timer so the table size tracks the active key population, not the historical
// one.
func (s *MemoryStore) Cleanup(now time.Time) int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.cleanupLocked(now)
}

func (s *MemoryStore) cleanupLocked(now time.Time) int {
	removed := 0
	for key, b := range s.buckets {
		if now.Sub(b.lastSeen) > s.idleTTL {
			delete(s.buckets, key)
			removed++
		}
	}
	return removed
}

// Len reports the current key count, for tests and metrics.
func (s *MemoryStore) Len() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return len(s.buckets)
}
