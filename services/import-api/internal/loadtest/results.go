package loadtest

import (
	"runtime"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/metrics"
)

// ResultsSchemaVersion identifies the machine-readable load-results shape. The
// validator asserts a results document declares this version.
const ResultsSchemaVersion = "memory-os-load-results.v1"

// Environment captures where the numbers came from. Without it, a figure is not
// interpretable and must not be treated as capacity.
type Environment struct {
	OS             string `json:"os"`
	Arch           string `json:"arch"`
	NumCPU         int    `json:"numCpu"`
	GoVersion      string `json:"goVersion"`
	DependencyMode string `json:"dependencyMode"`
	Note           string `json:"note"`
}

// CurrentEnvironment reads the runtime environment. DependencyMode is always
// MOCK here: this harness never drives production-equivalent dependencies.
func CurrentEnvironment() Environment {
	return Environment{
		OS:             runtime.GOOS,
		Arch:           runtime.GOARCH,
		NumCPU:         runtime.NumCPU(),
		GoVersion:      runtime.Version(),
		DependencyMode: "MOCK",
		Note:           "in-process httptest server over mocked Apple and in-memory stores; local non-production figures only.",
	}
}

// ScenarioResult is one scenario's machine-readable outcome.
type ScenarioResult struct {
	ScenarioID           string         `json:"scenarioId"`
	WorkloadType         string         `json:"workloadType"`
	DependencyMode       string         `json:"dependencyMode"`
	StartedAt            string         `json:"startedAt"`
	DurationSeconds      float64        `json:"durationSeconds"`
	Concurrency          int            `json:"concurrency"`
	Requests             int            `json:"requests"`
	Successes            int            `json:"successes"`
	Failures             int            `json:"failures"`
	StatusClassCounts    map[string]int `json:"statusClassCounts"`
	Throughput           float64        `json:"throughput"`
	LatencyP50Ms         float64        `json:"latencyP50Ms"`
	LatencyP95Ms         float64        `json:"latencyP95Ms"`
	LatencyP99Ms         float64        `json:"latencyP99Ms"`
	MaxInFlight          int            `json:"maxInFlight"`
	RateLimitAllowed     uint64         `json:"rateLimitAllowed"`
	RateLimitRejected    uint64         `json:"rateLimitRejected"`
	GoroutinesBefore     int            `json:"goroutinesBefore"`
	GoroutinesAfter      int            `json:"goroutinesAfter"`
	HeapAllocBeforeBytes uint64         `json:"heapAllocBeforeBytes"`
	HeapAllocAfterBytes  uint64         `json:"heapAllocAfterBytes"`
	MetricsSeriesBefore  int            `json:"metricsSeriesBefore"`
	MetricsSeriesAfter   int            `json:"metricsSeriesAfter"`
	IntegrityResult      string         `json:"integrityResult"`
	AbortReason          string         `json:"abortReason"`
	Result               string         `json:"result"`
}

// ResultsDocument is the top-level machine-readable results artifact.
type ResultsDocument struct {
	SchemaVersion string           `json:"schemaVersion"`
	CommitSHA     string           `json:"commitSha"`
	GeneratedAt   string           `json:"generatedAt"`
	Environment   Environment      `json:"environment"`
	Scenarios     []ScenarioResult `json:"scenarios"`
}

// Summarize turns a harness Result plus registry-derived counters into a
// ScenarioResult. seriesBefore is captured by the caller before the run.
func Summarize(scenarioID, workloadType string, res Result, reg *metrics.Registry, seriesBefore int, integrity, result string) ScenarioResult {
	total := reg.SumCounter(metrics.MetricRateLimitDecisions, nil)
	allowed := reg.SumCounter(metrics.MetricRateLimitDecisions, map[string]string{"outcome": "success"})
	rejected := uint64(0)
	if total > allowed {
		rejected = total - allowed
	}
	return ScenarioResult{
		ScenarioID:           scenarioID,
		WorkloadType:         workloadType,
		DependencyMode:       "MOCK",
		StartedAt:            time.Now().UTC().Format(time.RFC3339),
		DurationSeconds:      res.DurationSeconds,
		Concurrency:          0, // set by caller when known
		Requests:             res.Requests,
		Successes:            res.Successes,
		Failures:             res.Failures,
		StatusClassCounts:    res.StatusClassCounts,
		Throughput:           res.Throughput,
		LatencyP50Ms:         res.LatencyP50Ms,
		LatencyP95Ms:         res.LatencyP95Ms,
		LatencyP99Ms:         res.LatencyP99Ms,
		MaxInFlight:          res.MaxInFlight,
		RateLimitAllowed:     allowed,
		RateLimitRejected:    rejected,
		GoroutinesBefore:     res.GoroutinesBefore,
		GoroutinesAfter:      res.GoroutinesAfter,
		HeapAllocBeforeBytes: res.HeapAllocBeforeByte,
		HeapAllocAfterBytes:  res.HeapAllocAfterByte,
		MetricsSeriesBefore:  seriesBefore,
		MetricsSeriesAfter:   reg.TotalSeries(),
		IntegrityResult:      integrity,
		AbortReason:          res.AbortReason,
		Result:               result,
	}
}
