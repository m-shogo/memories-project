package httpserver

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"runtime"
	"strconv"
	"strings"
	"testing"
	"time"
)

const shortStabilityScenarioID = "authenticated-preview-short-ci-stability-local-postgres"

type shortStabilityObservation struct {
	Window          int             `json:"window"`
	ObservedAt      string          `json:"observedAt"`
	Batch           liveBatchResult `json:"batch"`
	HeapAllocBytes  uint64          `json:"heapAllocBytes"`
	HeapInuseBytes  uint64          `json:"heapInuseBytes"`
	RSSBytes        int64           `json:"rssBytes"`
	Goroutines      int             `json:"goroutines"`
}

type shortStabilityResultsDocument struct {
	SchemaVersion string `json:"schemaVersion"`
	CommitSHA     string `json:"commitSha"`
	GeneratedAt   string `json:"generatedAt"`
	Environment   struct {
		OS                               string `json:"os"`
		Arch                             string `json:"arch"`
		NumCPU                           int    `json:"numCpu"`
		GoVersion                        string `json:"goVersion"`
		DependencyMode                   string `json:"dependencyMode"`
		Classification                   string `json:"classification"`
		SyntheticDataOnly                bool   `json:"syntheticDataOnly"`
		ProductionTraffic                bool   `json:"productionTraffic"`
		ProductionCredentials            bool   `json:"productionCredentials"`
		ProductionEvidence               bool   `json:"productionEvidence"`
		ProductionEquivalentDependencies bool   `json:"productionEquivalentDependencies"`
		ContainsSecrets                  bool   `json:"containsSecrets"`
	} `json:"environment"`
	Scenario struct {
		ScenarioID                    string                      `json:"scenarioId"`
		StartedAt                     string                      `json:"startedAt"`
		CompletedAt                   string                      `json:"completedAt"`
		WindowCount                   int                         `json:"windowCount"`
		RequestsPerWindow             int                         `json:"requestsPerWindow"`
		Concurrency                   int                         `json:"concurrency"`
		BaselineHeapAllocBytes        uint64                      `json:"baselineHeapAllocBytes"`
		BaselineHeapInuseBytes        uint64                      `json:"baselineHeapInuseBytes"`
		BaselineRSSBytes              int64                       `json:"baselineRssBytes"`
		BaselineGoroutines            int                         `json:"baselineGoroutines"`
		Observations                  []shortStabilityObservation `json:"observations"`
		FinalMinusBaselineHeapAlloc   int64                       `json:"finalMinusBaselineHeapAllocBytes"`
		FinalMinusBaselineHeapInuse   int64                       `json:"finalMinusBaselineHeapInuseBytes"`
		FinalMinusBaselineRSS         int64                       `json:"finalMinusBaselineRssBytes"`
		FinalMinusBaselineGoroutines  int                         `json:"finalMinusBaselineGoroutines"`
		HeapAllocSlopeBytesPerWindow  float64                     `json:"heapAllocSlopeBytesPerWindow"`
		HeapInuseSlopeBytesPerWindow  float64                     `json:"heapInuseSlopeBytesPerWindow"`
		RSSSlopeBytesPerWindow        float64                     `json:"rssSlopeBytesPerWindow"`
		GoroutineSlopePerWindow       float64                     `json:"goroutineSlopePerWindow"`
		Decision                      string                      `json:"decision"`
		Assertions                    map[string]any              `json:"assertions"`
		Result                        string                      `json:"result"`
		IntegrityResult               string                      `json:"integrityResult"`
	} `json:"scenario"`
	Limitations []string `json:"limitations"`
}

func shortStabilityRSSBytes() (int64, error) {
	payload, err := os.ReadFile("/proc/self/statm")
	if err != nil {
		return 0, err
	}
	fields := strings.Fields(string(payload))
	if len(fields) < 2 {
		return 0, fmt.Errorf("statm has %d fields", len(fields))
	}
	residentPages, err := strconv.ParseInt(fields[1], 10, 64)
	if err != nil {
		return 0, err
	}
	return residentPages * int64(os.Getpagesize()), nil
}

func shortStabilitySlope(values []float64) float64 {
	if len(values) < 2 {
		return 0
	}
	var sumX float64
	var sumY float64
	var sumXY float64
	var sumXX float64
	for index, value := range values {
		x := float64(index)
		sumX += x
		sumY += value
		sumXY += x * value
		sumXX += x * x
	}
	n := float64(len(values))
	denominator := n*sumXX - sumX*sumX
	if denominator == 0 {
		return 0
	}
	return (n*sumXY - sumX*sumY) / denominator
}

func shortStabilityMemObservation() (runtime.MemStats, int64, int, error) {
	runtime.GC()
	time.Sleep(100 * time.Millisecond)
	var memory runtime.MemStats
	runtime.ReadMemStats(&memory)
	rss, err := shortStabilityRSSBytes()
	return memory, rss, runtime.NumGoroutine(), err
}

func TestAuthenticatedPreviewShortCIStabilityLocalPostgres(t *testing.T) {
	if os.Getenv("MEMORY_OS_RUN_SHORT_STABILITY_SAMPLE") != "1" {
		t.Skip("set MEMORY_OS_RUN_SHORT_STABILITY_SAMPLE=1 to run the short CI stability sample")
	}

	server := newLiveServer(t)
	runID := time.Now().UnixNano()
	owner := fmt.Sprintf("acct_short_stability_%d", runID)
	token := server.issueSession(t, owner)
	jobID := server.createJob(t, owner)
	previewID, _ := server.commitPreviewForJob(t, owner, jobID)
	previewPath := server.server.URL + "/v1/import-jobs/" + jobID + "/preview"

	const windowCount = 6
	const requestsPerWindow = 300
	const concurrency = 16

	baselineMemory, baselineRSS, baselineGoroutines, err := shortStabilityMemObservation()
	if err != nil {
		t.Fatalf("RSS observation unavailable: %v", err)
	}
	startedAt := time.Now().UTC()
	observations := make([]shortStabilityObservation, 0, windowCount)
	all2xx := true
	allNo5xx := true
	allNoTransport := true

	for window := 1; window <= windowCount; window++ {
		batch := runLiveHTTPBatch(requestsPerWindow, concurrency, func(int) (*http.Request, error) {
			return liveRequest(http.MethodGet, previewPath, token, nil)
		})
		stepAll2xx := batch.StatusClassCounts["2xx"] == requestsPerWindow && batch.Successes == requestsPerWindow
		stepNo5xx := batch.StatusClassCounts["5xx"] == 0
		stepNoTransport := batch.StatusClassCounts["transport_error"] == 0
		all2xx = all2xx && stepAll2xx
		allNo5xx = allNo5xx && stepNo5xx
		allNoTransport = allNoTransport && stepNoTransport
		if !stepAll2xx || !stepNo5xx || !stepNoTransport {
			t.Fatalf("short stability window %d crossed status boundary: %+v", window, batch)
		}

		memory, rss, goroutines, err := shortStabilityMemObservation()
		if err != nil {
			t.Fatalf("window %d RSS observation unavailable: %v", window, err)
		}
		observations = append(observations, shortStabilityObservation{
			Window:         window,
			ObservedAt:     time.Now().UTC().Format(time.RFC3339),
			Batch:          batch,
			HeapAllocBytes: memory.HeapAlloc,
			HeapInuseBytes: memory.HeapInuse,
			RSSBytes:       rss,
			Goroutines:     goroutines,
		})
	}

	counts := map[string]int{}
	queries := map[string]string{
		"previewReadyRowsAfterSample":     `SELECT count(*) FROM memory_os.preview_ready WHERE id = $1`,
		"previewCandidateRowsAfterSample": `SELECT count(*) FROM memory_os.preview_candidate WHERE preview_id = $1`,
		"previewRejectionRowsAfterSample": `SELECT count(*) FROM memory_os.preview_rejection WHERE preview_id = $1`,
	}
	for name, query := range queries {
		var count int
		if err := server.pool.QueryRow(context.Background(), query, previewID).Scan(&count); err != nil {
			t.Fatal(err)
		}
		counts[name] = count
	}
	if counts["previewReadyRowsAfterSample"] != 1 ||
		counts["previewCandidateRowsAfterSample"] != 2 ||
		counts["previewRejectionRowsAfterSample"] != 1 {
		t.Fatalf("short stability sample mutated Preview integrity rows: %+v", counts)
	}

	path := os.Getenv("MEMORY_OS_SHORT_STABILITY_RESULTS_PATH")
	if path == "" {
		return
	}
	sourceCommit := os.Getenv("MEMORY_OS_COMMIT_SHA")
	if sourceCommit == "" {
		t.Fatal("MEMORY_OS_COMMIT_SHA is required when writing short stability results")
	}

	last := observations[len(observations)-1]
	heapAllocValues := make([]float64, 0, len(observations)+1)
	heapInuseValues := make([]float64, 0, len(observations)+1)
	rssValues := make([]float64, 0, len(observations)+1)
	goroutineValues := make([]float64, 0, len(observations)+1)
	heapAllocValues = append(heapAllocValues, float64(baselineMemory.HeapAlloc))
	heapInuseValues = append(heapInuseValues, float64(baselineMemory.HeapInuse))
	rssValues = append(rssValues, float64(baselineRSS))
	goroutineValues = append(goroutineValues, float64(baselineGoroutines))
	for _, observation := range observations {
		heapAllocValues = append(heapAllocValues, float64(observation.HeapAllocBytes))
		heapInuseValues = append(heapInuseValues, float64(observation.HeapInuseBytes))
		rssValues = append(rssValues, float64(observation.RSSBytes))
		goroutineValues = append(goroutineValues, float64(observation.Goroutines))
	}

	document := shortStabilityResultsDocument{
		SchemaVersion: "memory-os-short-stability-sample-results.v1",
		CommitSHA:     sourceCommit,
		GeneratedAt:   time.Now().UTC().Format(time.RFC3339),
		Limitations: []string{
			"six bounded windows rather than a 60-minute or longer soak",
			"single authenticated Preview read route",
			"local PostgreSQL and an ephemeral GitHub-hosted runner",
			"runtime.GC is invoked before observations to reduce transient noise",
			"no leak or production capacity conclusion is permitted",
		},
	}
	document.Environment.OS = runtime.GOOS
	document.Environment.Arch = runtime.GOARCH
	document.Environment.NumCPU = runtime.NumCPU()
	document.Environment.GoVersion = runtime.Version()
	document.Environment.DependencyMode = "LOCAL_POSTGRES"
	document.Environment.Classification = "SHORT_CI_STABILITY_SAMPLE"
	document.Environment.SyntheticDataOnly = true
	document.Environment.ProductionTraffic = false
	document.Environment.ProductionCredentials = false
	document.Environment.ProductionEvidence = false
	document.Environment.ProductionEquivalentDependencies = false
	document.Environment.ContainsSecrets = false

	document.Scenario.ScenarioID = shortStabilityScenarioID
	document.Scenario.StartedAt = startedAt.Format(time.RFC3339)
	document.Scenario.CompletedAt = time.Now().UTC().Format(time.RFC3339)
	document.Scenario.WindowCount = windowCount
	document.Scenario.RequestsPerWindow = requestsPerWindow
	document.Scenario.Concurrency = concurrency
	document.Scenario.BaselineHeapAllocBytes = baselineMemory.HeapAlloc
	document.Scenario.BaselineHeapInuseBytes = baselineMemory.HeapInuse
	document.Scenario.BaselineRSSBytes = baselineRSS
	document.Scenario.BaselineGoroutines = baselineGoroutines
	document.Scenario.Observations = observations
	document.Scenario.FinalMinusBaselineHeapAlloc = int64(last.HeapAllocBytes) - int64(baselineMemory.HeapAlloc)
	document.Scenario.FinalMinusBaselineHeapInuse = int64(last.HeapInuseBytes) - int64(baselineMemory.HeapInuse)
	document.Scenario.FinalMinusBaselineRSS = last.RSSBytes - baselineRSS
	document.Scenario.FinalMinusBaselineGoroutines = last.Goroutines - baselineGoroutines
	document.Scenario.HeapAllocSlopeBytesPerWindow = shortStabilitySlope(heapAllocValues)
	document.Scenario.HeapInuseSlopeBytesPerWindow = shortStabilitySlope(heapInuseValues)
	document.Scenario.RSSSlopeBytesPerWindow = shortStabilitySlope(rssValues)
	document.Scenario.GoroutineSlopePerWindow = shortStabilitySlope(goroutineValues)
	document.Scenario.Decision = "SHORT_SAMPLE_ONLY"
	document.Scenario.Assertions = map[string]any{
		"allWindowsExecuted":               len(observations) == windowCount,
		"allWindowsAll2xx":                 all2xx,
		"allWindowsNo5xx":                  allNo5xx,
		"allWindowsNoTransportErrors":      allNoTransport,
		"rssAvailable":                     baselineRSS > 0,
		"previewReadyRowsAfterSample":      counts["previewReadyRowsAfterSample"],
		"previewCandidateRowsAfterSample":  counts["previewCandidateRowsAfterSample"],
		"previewRejectionRowsAfterSample":  counts["previewRejectionRowsAfterSample"],
		"sustainedSoakEvidence":            false,
		"leakProof":                        false,
		"capacityBoundaryEstablished":      false,
		"operationalThresholdApproved":     false,
		"productionEvidence":               false,
	}
	document.Scenario.Result = "PASS"
	document.Scenario.IntegrityResult = "PASS"

	payload, err := json.MarshalIndent(document, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, append(payload, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}
