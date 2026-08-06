package httpserver

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
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

const liveObjectScenarioID = "signed-upload-lifecycle-local-minio-postgres"

type liveObjectScenarioResult struct {
	ScenarioID            string            `json:"scenarioId"`
	WorkloadType          string            `json:"workloadType"`
	DependencyMode        string            `json:"dependencyMode"`
	StartedAt             string            `json:"startedAt"`
	Batch                 liveBatchResult   `json:"batch"`
	IntegrityResult       string            `json:"integrityResult"`
	DatabaseAssertions    map[string]int    `json:"databaseAssertions"`
	ObjectStoreAssertions map[string]int    `json:"objectStoreAssertions"`
	Result                string            `json:"result"`
}

type liveObjectLoadResultsDocument struct {
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
	Scenarios []liveObjectScenarioResult `json:"scenarios"`
}

type issuedUpload struct {
	AuthorizationID string            `json:"authorizationId"`
	UploadURL       string            `json:"uploadUrl"`
	RequiredHeaders map[string]string `json:"requiredHeaders"`
}

func runUploadLifecycle(
	client *http.Client,
	baseURL string,
	token string,
	jobID string,
	payload []byte,
	index int,
) liveHTTPSample {
	started := time.Now()
	digest := sha256.Sum256(payload)
	issueBody, err := json.Marshal(map[string]any{
		"contentLength":   len(payload),
		"checksumSha256":  hex.EncodeToString(digest[:]),
		"contentType":     "text/csv",
		"sourceSurface":   "ios_files",
		"displayFilename": fmt.Sprintf("load-%03d.csv", index),
	})
	if err != nil {
		return liveHTTPSample{Duration: time.Since(started), Err: err}
	}

	issueRequest, err := liveRequest(
		http.MethodPost,
		baseURL+"/v1/import-jobs/"+jobID+"/upload-authorizations",
		token,
		issueBody,
	)
	if err != nil {
		return liveHTTPSample{Duration: time.Since(started), Err: err}
	}
	issueResponse, err := client.Do(issueRequest)
	if err != nil {
		return liveHTTPSample{Duration: time.Since(started), Err: err}
	}
	issuePayload, readErr := io.ReadAll(io.LimitReader(issueResponse.Body, 1<<20))
	closeErr := issueResponse.Body.Close()
	if readErr != nil {
		return liveHTTPSample{Duration: time.Since(started), Err: readErr}
	}
	if closeErr != nil {
		return liveHTTPSample{Duration: time.Since(started), Err: closeErr}
	}
	if issueResponse.StatusCode != http.StatusCreated {
		return liveHTTPSample{Status: issueResponse.StatusCode, Duration: time.Since(started)}
	}

	var issued issuedUpload
	if err := json.Unmarshal(issuePayload, &issued); err != nil {
		return liveHTTPSample{Duration: time.Since(started), Err: err}
	}
	if issued.AuthorizationID == "" || issued.UploadURL == "" || len(issued.RequiredHeaders) == 0 {
		return liveHTTPSample{Duration: time.Since(started), Err: fmt.Errorf("incomplete upload authorization")}
	}

	putRequest, err := http.NewRequest(http.MethodPut, issued.UploadURL, bytes.NewReader(payload))
	if err != nil {
		return liveHTTPSample{Duration: time.Since(started), Err: err}
	}
	putRequest.ContentLength = int64(len(payload))
	for name, value := range issued.RequiredHeaders {
		if name != "Content-Length" {
			putRequest.Header.Set(name, value)
		}
	}
	putResponse, err := client.Do(putRequest)
	if err != nil {
		return liveHTTPSample{Duration: time.Since(started), Err: err}
	}
	_, readErr = io.Copy(io.Discard, io.LimitReader(putResponse.Body, 1<<20))
	closeErr = putResponse.Body.Close()
	if readErr != nil {
		return liveHTTPSample{Duration: time.Since(started), Err: readErr}
	}
	if closeErr != nil {
		return liveHTTPSample{Duration: time.Since(started), Err: closeErr}
	}
	if putResponse.StatusCode != http.StatusOK {
		return liveHTTPSample{Status: putResponse.StatusCode, Duration: time.Since(started)}
	}

	completeRequest, err := liveRequest(
		http.MethodPost,
		baseURL+"/v1/upload-authorizations/"+issued.AuthorizationID+"/complete",
		token,
		nil,
	)
	if err != nil {
		return liveHTTPSample{Duration: time.Since(started), Err: err}
	}
	completeResponse, err := client.Do(completeRequest)
	if err != nil {
		return liveHTTPSample{Duration: time.Since(started), Err: err}
	}
	_, readErr = io.Copy(io.Discard, io.LimitReader(completeResponse.Body, 1<<20))
	closeErr = completeResponse.Body.Close()
	if readErr != nil {
		return liveHTTPSample{Duration: time.Since(started), Err: readErr}
	}
	if closeErr != nil {
		return liveHTTPSample{Duration: time.Since(started), Err: closeErr}
	}
	return liveHTTPSample{Status: completeResponse.StatusCode, Duration: time.Since(started)}
}

func runLiveObjectBatch(
	total int,
	concurrency int,
	baseURL string,
	token string,
	jobIDs []string,
) liveBatchResult {
	started := time.Now()
	client := &http.Client{Timeout: 30 * time.Second}
	samples := make([]liveHTTPSample, total)
	jobs := make(chan int)

	var workers sync.WaitGroup
	for worker := 0; worker < concurrency; worker++ {
		workers.Add(1)
		go func() {
			defer workers.Done()
			for index := range jobs {
				payload := []byte(fmt.Sprintf("title,date\nobject load %03d,2026-08-06\n", index))
				samples[index] = runUploadLifecycle(client, baseURL, token, jobIDs[index], payload, index)
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
		if sample.Status == http.StatusAccepted {
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

func writeLiveObjectLoadResults(t *testing.T, sourceCommit string, scenario liveObjectScenarioResult) {
	t.Helper()
	path := os.Getenv("MEMORY_OS_LIVE_OBJECT_LOAD_RESULTS_PATH")
	if path == "" {
		return
	}
	if sourceCommit == "" {
		sourceCommit = "unknown"
	}
	document := liveObjectLoadResultsDocument{
		SchemaVersion: "memory-os-live-object-load-results.v1",
		CommitSHA:     sourceCommit,
		GeneratedAt:   time.Now().UTC().Format(time.RFC3339),
		Scenarios:     []liveObjectScenarioResult{scenario},
	}
	document.Environment.OS = runtime.GOOS
	document.Environment.Arch = runtime.GOARCH
	document.Environment.NumCPU = runtime.NumCPU()
	document.Environment.GoVersion = runtime.Version()
	document.Environment.DatabaseMode = "LOCAL_POSTGRES"
	document.Environment.ObjectStoreMode = "LOCAL_MINIO_MEASURED"
	document.Environment.ProductionEvidence = false
	document.Environment.Note = "Measures signed authorization issuance, presigned PUT, exact-version metadata verification and scan enqueue against ephemeral PostgreSQL 16 and MinIO. It is not production capacity evidence."

	payload, err := json.MarshalIndent(document, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, append(payload, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestLiveMinIOSignedUploadLifecycleLoad(t *testing.T) {
	if os.Getenv("MEMORY_OS_RUN_LIVE_OBJECT_LOAD") != "1" {
		t.Skip("set MEMORY_OS_RUN_LIVE_OBJECT_LOAD=1 to run the live MinIO load checkpoint")
	}

	server := newLiveServer(t)
	runID := time.Now().UnixNano()
	owner := fmt.Sprintf("acct_live_object_load_%d", runID)
	token := server.issueSession(t, owner)

	const total = 32
	const concurrency = 8
	jobIDs := make([]string, total)
	for index := range jobIDs {
		jobIDs[index] = server.createJob(t, owner)
	}

	startedAt := time.Now().UTC()
	batch := runLiveObjectBatch(total, concurrency, server.server.URL, token, jobIDs)
	if batch.StatusClassCounts["2xx"] != total || batch.StatusClassCounts["5xx"] != 0 || batch.StatusClassCounts["transport_error"] != 0 {
		t.Fatalf("live object load violated status boundary: %+v", batch)
	}

	ctx := context.Background()
	var consumedAuthorizations int
	if err := server.pool.QueryRow(ctx,
		`SELECT count(*) FROM memory_os.upload_authorization
		 WHERE owner_account_id = $1 AND state = 'consumed'`, owner,
	).Scan(&consumedAuthorizations); err != nil {
		t.Fatal(err)
	}
	var scanPending int
	var distinctVersions int
	var distinctKeys int
	if err := server.pool.QueryRow(ctx,
		`SELECT count(*),
		        count(DISTINCT safe_metadata->>'objectVersionId'),
		        count(DISTINCT safe_metadata->>'objectKey')
		 FROM memory_os.quarantine_object
		 WHERE owner_account_id = $1 AND state = 'scan_pending'`, owner,
	).Scan(&scanPending, &distinctVersions, &distinctKeys); err != nil {
		t.Fatal(err)
	}
	if consumedAuthorizations != total || scanPending != total || distinctVersions != total || distinctKeys != total {
		t.Fatalf(
			"post-load upload integrity mismatch: consumed=%d scan_pending=%d versions=%d keys=%d",
			consumedAuthorizations,
			scanPending,
			distinctVersions,
			distinctKeys,
		)
	}

	scenario := liveObjectScenarioResult{
		ScenarioID:      liveObjectScenarioID,
		WorkloadType:    "STEADY",
		DependencyMode:  "LOCAL_POSTGRES_MINIO",
		StartedAt:       startedAt.Format(time.RFC3339),
		Batch:           batch,
		IntegrityResult: "PASS",
		DatabaseAssertions: map[string]int{
			"consumed_upload_authorization_rows": consumedAuthorizations,
			"scan_pending_quarantine_rows":       scanPending,
			"distinct_object_version_ids":        distinctVersions,
			"distinct_object_keys":               distinctKeys,
		},
		ObjectStoreAssertions: map[string]int{
			"presigned_put_successes":       batch.Successes,
			"exact_version_completions":     scanPending,
			"distinct_version_ids_verified": distinctVersions,
		},
		Result: "PASS",
	}
	writeLiveObjectLoadResults(t, os.Getenv("MEMORY_OS_COMMIT_SHA"), scenario)
}
