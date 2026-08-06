package loadtest

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/ratelimit"
)

// TestCardinalityAttackReturnsOnlyExpected4xx locks the scenario contract to
// observable HTTP behaviour. Unknown hostile API shapes must be rejected as
// client errors before session resolution; a missing session backend must not
// turn the attack stream into a misleading 5xx result.
func TestCardinalityAttackReturnsOnlyExpected4xx(t *testing.T) {
	_, rec := newRegistry(t)
	world := NewAppleWorld(rec)
	server := buildServer(t, rec, world, ratelimit.NewMemoryStore(2_000, time.Minute), applePolicy(100_000, 100_000))

	factory := func(i int) *http.Request {
		req := httptest.NewRequest(http.MethodGet, fmt.Sprintf("/v1/attacker/%d/probe?token=SECRET%d", i, i), nil)
		req.Header.Set("X-Request-Id", fmt.Sprintf("reqid-%d", i))
		req.Header.Set("X-Forwarded-For", fmt.Sprintf("10.9.%d.%d", i%256, (i/256)%256))
		req.Header.Set("Authorization", fmt.Sprintf("Bearer bear-%d", i))
		return req
	}

	const requests = 256
	result := Run(server, Options{Concurrency: 16, TotalRequests: requests, Factory: factory}, nil)
	if result.StatusClassCounts["4xx"] != requests {
		t.Fatalf("cardinality stream not fully rejected as 4xx: %+v", result.StatusClassCounts)
	}
	if result.StatusClassCounts["5xx"] != 0 {
		t.Fatalf("cardinality stream produced 5xx: %+v", result.StatusClassCounts)
	}
	if world.SessionsIssued() != 0 || world.AccountsCreated() != 0 || world.ReplayAttempts() != 0 {
		t.Fatalf("unknown routes reached business state: sessions=%d accounts=%d replay=%d",
			world.SessionsIssued(), world.AccountsCreated(), world.ReplayAttempts())
	}
}
