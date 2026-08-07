package ratelimit

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"sync"
	"testing"
	"time"
)

const sharedStoreChildPrefix = "MEMORY_OS_RL_CHILD"

type sharedStoreWireRequest struct {
	Key    string `json:"key"`
	Policy Policy `json:"policy"`
	NowNS  int64  `json:"nowNs"`
}

type sharedStoreWireResponse struct {
	Allowed      bool   `json:"allowed"`
	RetryAfterNS int64  `json:"retryAfterNs"`
	ErrorClass   string `json:"errorClass,omitempty"`
}

type loopbackSharedStoreClient struct {
	endpoint string
	client   *http.Client
}

func (c *loopbackSharedStoreClient) Take(key string, policy Policy, now time.Time) (Decision, error) {
	payload, err := json.Marshal(sharedStoreWireRequest{Key: key, Policy: policy, NowNS: now.UnixNano()})
	if err != nil {
		return Decision{}, err
	}
	request, err := http.NewRequest(http.MethodPost, c.endpoint, bytes.NewReader(payload))
	if err != nil {
		return Decision{}, err
	}
	request.Header.Set("Content-Type", "application/json")
	response, err := c.client.Do(request)
	if err != nil {
		return Decision{}, ErrStoreUnavailable
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return Decision{}, ErrStoreUnavailable
	}
	var wire sharedStoreWireResponse
	if err := json.NewDecoder(response.Body).Decode(&wire); err != nil {
		return Decision{}, ErrStoreUnavailable
	}
	switch wire.ErrorClass {
	case "":
		return Decision{Allowed: wire.Allowed, RetryAfter: time.Duration(wire.RetryAfterNS)}, nil
	case "key_capacity":
		return Decision{}, ErrKeyCapacity
	default:
		return Decision{}, ErrStoreUnavailable
	}
}

func newLoopbackSharedStoreServer(store Store) *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		defer r.Body.Close()
		var request sharedStoreWireRequest
		if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 4096)).Decode(&request); err != nil {
			http.Error(w, "invalid request", http.StatusBadRequest)
			return
		}
		decision, err := store.Take(request.Key, request.Policy, time.Unix(0, request.NowNS))
		wire := sharedStoreWireResponse{Allowed: decision.Allowed, RetryAfterNS: int64(decision.RetryAfter)}
		if err != nil {
			switch {
			case errors.Is(err, ErrKeyCapacity):
				wire.ErrorClass = "key_capacity"
			default:
				wire.ErrorClass = "store_unavailable"
			}
		}
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Cache-Control", "no-store")
		_ = json.NewEncoder(w).Encode(wire)
	}))
}

type sharedStoreChildResult struct {
	allowed int
	denied  int
	errors  int
	reason  string
}

func runSharedStoreChild(t *testing.T, endpoint, mode, key string, count int, now time.Time) sharedStoreChildResult {
	t.Helper()
	cmd := exec.Command(os.Args[0], "-test.run=^TestRateLimitSharedStoreChild$", "-test.v")
	cmd.Env = append(os.Environ(),
		"MEMORY_OS_RATE_LIMIT_CHILD=1",
		"MEMORY_OS_RATE_LIMIT_ENDPOINT="+endpoint,
		"MEMORY_OS_RATE_LIMIT_MODE="+mode,
		"MEMORY_OS_RATE_LIMIT_KEY="+key,
		"MEMORY_OS_RATE_LIMIT_COUNT="+strconv.Itoa(count),
		"MEMORY_OS_RATE_LIMIT_NOW_NS="+strconv.FormatInt(now.UnixNano(), 10),
	)
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("rate-limit child failed: %v\n%s", err, output)
	}
	for _, line := range strings.Split(string(output), "\n") {
		if !strings.HasPrefix(line, sharedStoreChildPrefix+" ") {
			continue
		}
		var result sharedStoreChildResult
		if _, err := fmt.Sscanf(line, sharedStoreChildPrefix+" allowed=%d denied=%d errors=%d reason=%s", &result.allowed, &result.denied, &result.errors, &result.reason); err != nil {
			t.Fatalf("cannot parse child result %q: %v", line, err)
		}
		return result
	}
	t.Fatalf("child result marker missing:\n%s", output)
	return sharedStoreChildResult{}
}

func TestRateLimitSharedStoreChild(t *testing.T) {
	if os.Getenv("MEMORY_OS_RATE_LIMIT_CHILD") != "1" {
		return
	}
	endpoint := os.Getenv("MEMORY_OS_RATE_LIMIT_ENDPOINT")
	mode := os.Getenv("MEMORY_OS_RATE_LIMIT_MODE")
	key := os.Getenv("MEMORY_OS_RATE_LIMIT_KEY")
	count, err := strconv.Atoi(os.Getenv("MEMORY_OS_RATE_LIMIT_COUNT"))
	if err != nil || count < 0 || count > 1000 {
		t.Fatalf("invalid child count")
	}
	nowNS, err := strconv.ParseInt(os.Getenv("MEMORY_OS_RATE_LIMIT_NOW_NS"), 10, 64)
	if err != nil {
		t.Fatalf("invalid child time")
	}
	now := time.Unix(0, nowNS)
	client := &loopbackSharedStoreClient{endpoint: endpoint, client: &http.Client{Timeout: time.Second}}
	policy := Policy{ID: "local-shared-store", Capacity: 5, RefillPerSec: 0.000001}

	result := sharedStoreChildResult{reason: "none"}
	switch mode {
	case "take":
		for i := 0; i < count; i++ {
			decision, err := client.Take(key, policy, now)
			if err != nil {
				result.errors++
				continue
			}
			if decision.Allowed {
				result.allowed++
			} else {
				result.denied++
			}
		}
	case "enforcer":
		enforcer, err := NewEnforcer(client, nil, []RoutePolicy{{
			RouteTemplate: "/v1/local-shared-store",
			Class:         ClassPublicAuthenticated,
			Enabled:       true,
			FailureMode:   FailClosed,
			Global:        policy,
			Network:       policy,
		}})
		if err != nil {
			t.Fatal(err)
		}
		decision := enforcer.Check("/v1/local-shared-store", "route_key", "network_key")
		if decision.Allowed {
			result.allowed = 1
		} else {
			result.denied = 1
		}
		result.reason = string(decision.Reason)
	default:
		t.Fatalf("unknown child mode")
	}
	fmt.Printf(sharedStoreChildPrefix+" allowed=%d denied=%d errors=%d reason=%s\n", result.allowed, result.denied, result.errors, result.reason)
}

func TestLocalSharedStoreCrossProcessBudgetRestartAndOutage(t *testing.T) {
	backend := NewMemoryStore(128, time.Hour)
	server := newLoopbackSharedStoreServer(backend)
	now := time.Unix(1_800_000_000, 0)
	key := "shared_budget_key"

	var first, second sharedStoreChildResult
	var wg sync.WaitGroup
	wg.Add(2)
	go func() {
		defer wg.Done()
		first = runSharedStoreChild(t, server.URL, "take", key, 8, now)
	}()
	go func() {
		defer wg.Done()
		second = runSharedStoreChild(t, server.URL, "take", key, 8, now)
	}()
	wg.Wait()
	if first.errors != 0 || second.errors != 0 {
		t.Fatalf("shared-store children had transport/store errors: first=%+v second=%+v", first, second)
	}
	if got := first.allowed + second.allowed; got != 5 {
		t.Fatalf("cross-process shared budget allowed %d, expected exactly 5", got)
	}
	if got := first.denied + second.denied; got != 11 {
		t.Fatalf("cross-process shared budget denied %d, expected exactly 11", got)
	}

	// A fresh OS process represents a restarted runtime client. The shared
	// backend survives it, so the already-exhausted budget must remain exhausted.
	restarted := runSharedStoreChild(t, server.URL, "take", key, 1, now)
	if restarted.allowed != 0 || restarted.denied != 1 || restarted.errors != 0 {
		t.Fatalf("client restart reset shared state: %+v", restarted)
	}

	// Once the shared store is unavailable, a protected route must fail closed.
	// This is deliberately a local loopback outage, not production failover proof.
	endpoint := server.URL
	server.Close()
	outage := runSharedStoreChild(t, endpoint, "enforcer", "unused", 1, now)
	if outage.allowed != 0 || outage.denied != 1 || outage.reason != string(ReasonStoreUnavailable) {
		t.Fatalf("shared-store outage did not fail closed: %+v", outage)
	}
}
