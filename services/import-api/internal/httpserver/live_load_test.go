package httpserver

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"runtime"
	"sort"
	"sync"
	"testing"
	"time"
)

const (
	livePreviewScenarioID = "authenticated-preview-local-postgres"
	liveApplyScenarioID   = "concurrent-idempotent-apply-local-postgres"
)

type liveHTTPSample struct {
	Status   int
	Duration time.Duration
	Err      error
}

type liveBatchResult struct {
	Requests          int            `json:"requests"`
	Concurrency       int            `json:"concurrency"`
	Successes         int            `json:"successes"`
	Failures          int            `json:"failures"`
	StatusClassCounts map[string]int `json:"statusClassCounts"`
	DurationSeconds   float64        `json:"durationSeconds"`
	Throughput        float64        `json:"throughput"`
	LatencyP50Ms      float64        `json:"latencyP50Ms"`
	LatencyP95Ms      float64        `json:"latencyP95Ms"`
	LatencyP99Ms      float64        `json:"latencyP99Ms"`
}

type liveScenarioResult struct {
	ScenarioID         string          `json:"scenarioId"`
	WorkloadType       string          `json:"workloadType"`
	DependencyMode     string          `json:"dependencyMode"`
	StartedAt          string          `json:"startedAt"`
	Batch              liveBatchResult `json:"batch"`
	IntegrityResult    string          `json:"integrityResult"`
	DatabaseAssertions map[string]int  `json:"databaseAssertions"`
	Result             string          `json:"result"`
}

type liveLoadResultsDocument struct {
	SchemaVersion string `json:"schemaVersion"`
	CommitSHA     string `json:"commitSha"`
	GeneratedAt   string `json:"generatedAt"`
	Environment   struct {
		OS                 string `json:"os"`
		Arch               string `json:"arch"`
		NumCPU             int    `json:"numCpu"`
		GoVersion          string `json:"goVersion"`
		DatabaseMode       string `json:"databaseMode"`
		ObjectStoreMode    string `json:"objectStoreMode"`
		ProductionEvidence bool   `json:"productionEvidence"`
		Note               string `json:"note"`
	} `json:"environment"`
	Scenarios []liveScenarioResult `json:"scenarios"`
}

func runLiveHTTPBatch(total, concurrency int, factory func(int) (*http.Request, error)) liveBatchResult {
	started := time.Now()
	client := &http.Client{Timeout: 15 * time.Second}
	samples := make([]liveHTTPSample, total)
	jobs := make(chan int)

	var workers sync.WaitGroup
	for worker := 0; worker < concurrency; worker++ {
		workers.Add(1)
		go func() {
			defer workers.Done()
			for index := range jobs {
				request, err := factory(index)
				if err != nil {
					samples[index] = liveHTTPSample{Err: err}
					continue
				}
				requestStarted := time.Now()
				response, err := client.Do(request)
				duration := time.Since(requestStarted)
				if err != nil {
					samples[index] = liveHTTPSample{Duration: duration, Err: err}
					continue
				}
				_, readErr := io.Copy(io.Discard, io.LimitReader(response.Body, 1<<20))
				closeErr := response.Body.Close()
				if readErr != nil {
					err = readErr
				} else if closeErr != nil {
					err = closeErr
				}
				samples[index] = liveHTTPSample{Status: response.StatusCode, Duration: duration, Err: err}
			}
		}()
	}

	for index := 0; index < total; index++ {
		jobs <- index
	}
	close(jobs)
	workers.Wait()

	elapsed := time.Since(started)
	result := liveBatchResult{
		Requests:          total,
		Concurrency:       concurrency,
		StatusClassCounts: map[string]int{},
		DurationSeconds:   elapsed.Seconds(),
	}
	if elapsed > 0 {
		result.Throughput = float64(total) / elapsed.Seconds()
	}

	latencies := make([]time.Duration, 0, total)
	for _, sample := range samples {
		if sample.Err != nil {
			result.Failures++
			result.StatusClassCounts["transport_error"]++
			continue
		}
		class := fmt.Sprintf("%dxx", sample.Status/100)
		result.StatusClassCounts[class]++
		if sample.Status >= 200 && sample.Status < 300 {
			result.Successes++
		} else {
			result.Failures++
		}
		latencies = append(latencies, sample.Duration)
	}
	sort.Slice(latencies, func(i, j int) bool { return latencies[i] < latencies[j] })
	result.LatencyP50Ms = livePercentileMillis(latencies, 0.50)
	result.LatencyP95Ms = livePercentileMillis(latencies, 0.95)
	result.LatencyP99Ms = livePercentileMillis(latencies, 0.99)
	return result
}

func livePercentileMillis(sorted []time.Duration, percentile float64) float64 {
	if len(sorted) == 0 {
		return 0
	}
	index := int(float64(len(sorted)-1) * percentile)
	return float64(sorted[index].Microseconds()) / 1000
}

func liveRequest(method, url, token string, body []byte) (*http.Request, error) {
	request, err := http.NewRequest(method, url, bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	request.Header.Set("Authorization", "Bearer "+token)
	if len(body) > 0 {
		request.Header.Set("Content-Type", "application/json")
	}
	return request, nil
}

func writeLiveLoadResults(t *testing.T, sourceCommit string, preview, applyResult liveScenarioResult) {
	t.Helper()
	path := os.Getenv("MEMORY_OS_LIVE_LOAD_RESULTS_PATH")
	if path == "" {
		return
	}
	if sourceCommit == "" {
		sourceCommit = "unknown"
	}
	document := liveLoadResultsDocument{
		SchemaVersion: "memory-os-live-load-results.v1",
		CommitSHA:     sourceCommit,
		GeneratedAt:   time.Now().UTC().Format(time.RFC3339),
		Scenarios:     []liveScenarioResult{preview, applyResult},
	}
	document.Environment.OS = runtime.GOOS
	document.Environment.Arch = runtime.GOARCH
	document.Environment.NumCPU = runtime.NumCPU()
	document.Environment.GoVersion = runtime.Version()
	document.Environment.DatabaseMode = "LOCAL_POSTGRES"
	document.Environment.ObjectStoreMode = "LOCAL_MINIO_HARNESS_ONLY_NOT_MEASURED"
	document.Environment.ProductionEvidence = false
	document.Environment.Note = "Live HTTP boundary over the deployment PostgreSQL principal and FORCE RLS. MinIO is provisioned because the shared live server harness requires it, but these two scenarios do not measure object-store operations."

	payload, err := json.MarshalIndent(document, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, append(payload, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}

// TestLivePostgresPreviewReadAndIdempotentApplyLoad drives the real HTTP
// handlers, bearer-session store, deployment PostgreSQL principal, FORCE RLS
// transaction scope, Preview repository and Apply repository. It is a local
// dependency checkpoint, not production capacity evidence.
func TestLivePostgresPreviewReadAndIdempotentApplyLoad(t *testing.T) {
	if os.Getenv("MEMORY_OS_RUN_LIVE_LOAD") != "1" {
		t.Skip("set MEMORY_OS_RUN_LIVE_LOAD=1 to run the live PostgreSQL load checkpoint")
	}

	server := newLiveServer(t)
	runID := time.Now().UnixNano()
	owner := fmt.Sprintf("acct_live_load_%d", runID)
	token := server.issueSession(t, owner)
	jobID := server.createJob(t, owner)
	previewID, previewSHA := server.commitPreviewForJob(t, owner, jobID)

	previewStarted := time.Now().UTC()
	previewPath := server.server.URL + "/v1/import-jobs/" + jobID + "/preview"
	previewBatch := runLiveHTTPBatch(500, 24, func(int) (*http.Request, error) {
		return liveRequest(http.MethodGet, previewPath, token, nil)
	})
	if previewBatch.StatusClassCounts["2xx"] != previewBatch.Requests ||
		previewBatch.StatusClassCounts["5xx"] != 0 ||
		previewBatch.StatusClassCounts["transport_error"] != 0 {
		t.Fatalf("live preview load violated its status boundary: %+v", previewBatch)
	}

	idempotencyKey := fmt.Sprintf("idem-live-load-%d", runID)
	applyBody, err := json.Marshal(map[string]any{
		"previewSha256":   previewSHA,
		"idempotencyKey":  idempotencyKey,
		"duplicatePolicy": "skip_existing",
	})
	if err != nil {
		t.Fatal(err)
	}
	// Establish the first durable claim synchronously. The dedicated mixed-version
	// compatibility drill owns first-writer claim races and process-death recovery.
	// This load checkpoint measures the stable replay path without manufacturing a
	// PostgreSQL lock storm that outlives the HTTP clients.
	firstResponse, firstPayload := server.request(t, http.MethodPost,
		"/v1/previews/"+previewID+"/apply", token, map[string]any{
			"previewSha256":   previewSHA,
			"idempotencyKey":  idempotencyKey,
			"duplicatePolicy": "skip_existing",
		})
	if firstResponse.StatusCode != http.StatusOK {
		t.Fatalf("initial live Apply failed: %d %s", firstResponse.StatusCode, firstPayload)
	}
	var firstApply struct {
		Replayed bool `json:"replayed"`
	}
	if err := json.Unmarshal(firstPayload, &firstApply); err != nil {
		t.Fatal(err)
	}
	if firstApply.Replayed {
		t.Fatalf("initial live Apply unexpectedly replayed: %s", firstPayload)
	}

	applyStarted := time.Now().UTC()
	applyPath := server.server.URL + "/v1/previews/" + previewID + "/apply"
	applyBatch := runLiveHTTPBatch(96, 24, func(int) (*http.Request, error) {
		return liveRequest(http.MethodPost, applyPath, token, applyBody)
	})
	if applyBatch.StatusClassCounts["2xx"] != applyBatch.Requests ||
		applyBatch.StatusClassCounts["5xx"] != 0 ||
		applyBatch.StatusClassCounts["transport_error"] != 0 {
		t.Fatalf("live replay load violated its status boundary: %+v", applyBatch)
	}

	response, payload := server.request(t, http.MethodPost, "/v1/previews/"+previewID+"/apply", token, map[string]any{
		"previewSha256":   previewSHA,
		"idempotencyKey":  idempotencyKey,
		"duplicatePolicy": "skip_existing",
	})
	if response.StatusCode != http.StatusOK {
		t.Fatalf("post-load idempotent replay failed: %d %s", response.StatusCode, payload)
	}
	var replay struct {
		Replayed bool `json:"replayed"`
	}
	if err := json.Unmarshal(payload, &replay); err != nil {
		t.Fatal(err)
	}
	if !replay.Replayed {
		t.Fatalf("post-load request was not an exact replay: %s", payload)
	}

	assertionCounts := map[string]int{}
	queries := map[string]struct {
		SQL  string
		Args []any
	}{
		"preview_ready_rows": {
			SQL:  `SELECT count(*) FROM memory_os.preview_ready WHERE id = $1`,
			Args: []any{previewID},
		},
		"preview_candidate_rows": {
			SQL:  `SELECT count(*) FROM memory_os.preview_candidate WHERE preview_id = $1`,
			Args: []any{previewID},
		},
		"preview_rejection_rows": {
			SQL:  `SELECT count(*) FROM memory_os.preview_rejection WHERE preview_id = $1`,
			Args: []any{previewID},
		},
		"memory_item_rows": {
			SQL: `SELECT count(*) FROM memory_os.memory_item
			      WHERE owner_account_id = $1 AND source_preview_id = $2`,
			Args: []any{owner, previewID},
		},
		"apply_confirmation_rows": {
			SQL: `SELECT count(*) FROM memory_os.apply_confirmation
			      WHERE owner_account_id = $1 AND idempotency_key = $2`,
			Args: []any{owner, idempotencyKey},
		},
	}
	for name, query := range queries {
		var count int
		if err := server.pool.QueryRow(context.Background(), query.SQL, query.Args...).Scan(&count); err != nil {
			t.Fatal(err)
		}
		assertionCounts[name] = count
	}
	if assertionCounts["preview_ready_rows"] != 1 ||
		assertionCounts["preview_candidate_rows"] != 2 ||
		assertionCounts["preview_rejection_rows"] != 1 ||
		assertionCounts["memory_item_rows"] != 2 ||
		assertionCounts["apply_confirmation_rows"] != 1 {
		t.Fatalf("post-load database integrity mismatch: %+v", assertionCounts)
	}

	previewResult := liveScenarioResult{
		ScenarioID:      livePreviewScenarioID,
		WorkloadType:    "STEADY",
		DependencyMode:  "LOCAL_POSTGRES",
		StartedAt:       previewStarted.Format(time.RFC3339),
		Batch:           previewBatch,
		IntegrityResult: "PASS",
		DatabaseAssertions: map[string]int{
			"preview_ready_rows":     assertionCounts["preview_ready_rows"],
			"preview_candidate_rows": assertionCounts["preview_candidate_rows"],
			"preview_rejection_rows": assertionCounts["preview_rejection_rows"],
		},
		Result: "PASS",
	}
	applyResult := liveScenarioResult{
		ScenarioID:      liveApplyScenarioID,
		WorkloadType:    "BURST",
		DependencyMode:  "LOCAL_POSTGRES",
		StartedAt:       applyStarted.Format(time.RFC3339),
		Batch:           applyBatch,
		IntegrityResult: "PASS",
		DatabaseAssertions: map[string]int{
			"memory_item_rows":        assertionCounts["memory_item_rows"],
			"apply_confirmation_rows": assertionCounts["apply_confirmation_rows"],
		},
		Result: "PASS",
	}
	writeLiveLoadResults(t, os.Getenv("MEMORY_OS_COMMIT_SHA"), previewResult, applyResult)
}
