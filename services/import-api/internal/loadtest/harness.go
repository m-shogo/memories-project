// Package loadtest is a small, dependency-free, in-process load driver for the
// Import API. It exists to make the HTTP, rate-limit and Apple-dependency
// boundaries diagnosable under concurrency, not to prove production capacity:
// it drives an http.Handler in the same process over mocked dependencies, so
// every figure it produces is a local, non-production measurement.
//
// The harness is deterministic when driven by a fixed request count, which is
// what the CI load smoke uses. Duration-driven runs (soak) are available for
// local use but are not required to be deterministic.
package loadtest

import (
	"context"
	"net/http"
	"net/http/httptest"
	"runtime"
	"sort"
	"sync"
	"sync/atomic"
	"time"
)

// RequestFactory builds one request to issue. It must return a fresh request
// each call (bodies are consumed). The index lets a factory vary a request
// safely within a bounded, non-cardinality-inflating space.
type RequestFactory func(index int) *http.Request

// Options configures a run. Exactly one of TotalRequests or Duration drives the
// stop condition; if both are set, TotalRequests wins (determinism first).
type Options struct {
	Concurrency   int
	TotalRequests int           // deterministic stop after N requests
	Duration      time.Duration // wall-clock stop (soak); ignored if TotalRequests > 0
	Factory       RequestFactory
}

// Result is the machine-readable outcome of a run. It maps to the load-test
// results schema. Latencies are milliseconds. Memory is Go heap-allocated
// bytes, not process RSS (RSS is platform-specific and deliberately not
// claimed here).
type Result struct {
	Requests            int
	Successes           int
	Failures            int
	StatusClassCounts   map[string]int
	Non2xx              int
	Throughput          float64 // requests per second
	LatencyP50Ms        float64
	LatencyP95Ms        float64
	LatencyP99Ms        float64
	MaxInFlight         int
	GoroutinesBefore    int
	GoroutinesAfter     int
	HeapAllocBeforeByte uint64
	HeapAllocAfterByte  uint64
	DurationSeconds     float64
	AbortReason         string
}

// Abort is an optional guard checked between requests. Returning a non-empty
// reason stops the run and marks it aborted, so a run has a safe stop condition
// rather than pushing until the process dies.
type Abort func(inFlight int) string

// Run drives handler under load and returns a Result. It never panics out: a
// handler panic is recovered by the server's own middleware in the real server,
// and here a transport error is counted as a failure.
func Run(handler http.Handler, opts Options, abort Abort) Result {
	if opts.Concurrency < 1 {
		opts.Concurrency = 1
	}
	server := httptest.NewServer(handler)
	defer server.Close()
	client := &http.Client{Timeout: 30 * time.Second}

	runtime.GC()
	var msBefore runtime.MemStats
	runtime.ReadMemStats(&msBefore)
	goroutinesBefore := runtime.NumGoroutine()

	var (
		mu        sync.Mutex
		latencies []time.Duration
		statusCls = map[string]int{}
		successes int
		failures  int
		issued    int64
		inFlight  int64
		maxFlight int64
		aborted   atomic.Value // string
	)
	aborted.Store("")

	shouldStop := func() bool {
		if r := aborted.Load().(string); r != "" {
			return true
		}
		if opts.TotalRequests > 0 {
			return atomic.LoadInt64(&issued) >= int64(opts.TotalRequests)
		}
		return false
	}

	start := time.Now()
	deadline := time.Time{}
	if opts.TotalRequests <= 0 && opts.Duration > 0 {
		deadline = start.Add(opts.Duration)
	}

	var wg sync.WaitGroup
	for w := 0; w < opts.Concurrency; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for {
				if shouldStop() {
					return
				}
				if !deadline.IsZero() && time.Now().After(deadline) {
					return
				}
				idx := int(atomic.AddInt64(&issued, 1)) - 1
				if opts.TotalRequests > 0 && idx >= opts.TotalRequests {
					return
				}

				cur := atomic.AddInt64(&inFlight, 1)
				for {
					m := atomic.LoadInt64(&maxFlight)
					if cur <= m || atomic.CompareAndSwapInt64(&maxFlight, m, cur) {
						break
					}
				}
				if abort != nil {
					if reason := abort(int(cur)); reason != "" {
						aborted.Store(reason)
					}
				}

				req := opts.Factory(idx)
				reqStart := time.Now()
				resp, err := client.Do(rebase(server.URL, req))
				elapsed := time.Since(reqStart)
				atomic.AddInt64(&inFlight, -1)

				mu.Lock()
				latencies = append(latencies, elapsed)
				if err != nil {
					failures++
				} else {
					cls := statusClass(resp.StatusCode)
					statusCls[cls]++
					if resp.StatusCode >= 200 && resp.StatusCode < 300 {
						successes++
					} else {
						failures++
					}
					resp.Body.Close()
				}
				mu.Unlock()
			}
		}()
	}
	wg.Wait()
	elapsed := time.Since(start)

	runtime.GC()
	var msAfter runtime.MemStats
	runtime.ReadMemStats(&msAfter)

	non2xx := 0
	for cls, n := range statusCls {
		if cls != "2xx" {
			non2xx += n
		}
	}
	total := successes + failures
	throughput := 0.0
	if elapsed.Seconds() > 0 {
		throughput = float64(total) / elapsed.Seconds()
	}
	p50, p95, p99 := percentiles(latencies)
	return Result{
		Requests:            total,
		Successes:           successes,
		Failures:            failures,
		StatusClassCounts:   statusCls,
		Non2xx:              non2xx,
		Throughput:          throughput,
		LatencyP50Ms:        p50,
		LatencyP95Ms:        p95,
		LatencyP99Ms:        p99,
		MaxInFlight:         int(maxFlight),
		GoroutinesBefore:    goroutinesBefore,
		GoroutinesAfter:     runtime.NumGoroutine(),
		HeapAllocBeforeByte: msBefore.HeapAlloc,
		HeapAllocAfterByte:  msAfter.HeapAlloc,
		DurationSeconds:     elapsed.Seconds(),
		AbortReason:         aborted.Load().(string),
	}
}

// rebase points a template request (built with any URL) at the test server,
// preserving method, path, query, headers and body.
func rebase(base string, req *http.Request) *http.Request {
	u, _ := http.NewRequestWithContext(context.Background(), req.Method, base+req.URL.RequestURI(), req.Body)
	u.Header = req.Header
	return u
}

func statusClass(code int) string {
	switch {
	case code >= 500:
		return "5xx"
	case code >= 400:
		return "4xx"
	case code >= 300:
		return "3xx"
	case code >= 200:
		return "2xx"
	default:
		return "1xx"
	}
}

func percentiles(latencies []time.Duration) (p50, p95, p99 float64) {
	if len(latencies) == 0 {
		return 0, 0, 0
	}
	sort.Slice(latencies, func(i, j int) bool { return latencies[i] < latencies[j] })
	pick := func(q float64) float64 {
		idx := int(q * float64(len(latencies)-1))
		return float64(latencies[idx].Microseconds()) / 1000.0
	}
	return pick(0.50), pick(0.95), pick(0.99)
}
