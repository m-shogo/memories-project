package httpserver

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"runtime"
	"strconv"
	"sync"
	"testing"
	"time"

	"memory-os-import-api/internal/accountdelete"
)

const deletionUnderLoadScenarioID = "account-deletion-post-fence-load-local-dependencies"

type deletionExactBatch struct {
	Summary          liveBatchResult `json:"summary"`
	StatusCodeCounts map[string]int  `json:"statusCodeCounts"`
}

type deletionWorkerResult struct {
	Receipts []accountdelete.Receipt
	Err      error
	Duration time.Duration
}

type deletionUnderLoadResultsDocument struct {
	SchemaVersion string `json:"schemaVersion"`
	CommitSHA     string `json:"commitSha"`
	GeneratedAt   string `json:"generatedAt"`
	Environment   struct {
		OS                               string `json:"os"`
		Arch                             string `json:"arch"`
		NumCPU                           int    `json:"numCpu"`
		GoVersion                        string `json:"goVersion"`
		DependencyMode                   string `json:"dependencyMode"`
		SyntheticDataOnly                bool   `json:"syntheticDataOnly"`
		ProductionTraffic                bool   `json:"productionTraffic"`
		ProductionCredentials            bool   `json:"productionCredentials"`
		ProductionEvidence               bool   `json:"productionEvidence"`
		ProductionEquivalentDependencies bool   `json:"productionEquivalentDependencies"`
		ContainsSecrets                  bool   `json:"containsSecrets"`
	} `json:"environment"`
	Scenario struct {
		ScenarioID            string             `json:"scenarioId"`
		StartedAt             string             `json:"startedAt"`
		CompletedAt           string             `json:"completedAt"`
		PreFence              deletionExactBatch `json:"preFence"`
		DeletionRequestStatus int                `json:"deletionRequestStatus"`
		DeletionEpoch         int64              `json:"deletionEpoch"`
		PostFence             deletionExactBatch `json:"postFence"`
		WorkerDurationSeconds float64            `json:"workerDurationSeconds"`
		WorkerReceiptCount    int                `json:"workerReceiptCount"`
		FinalOwnedRowCount    int                `json:"finalOwnedRowCount"`
		FinalAccountState     string             `json:"finalAccountState"`
		FinalAccountEpoch     int64              `json:"finalAccountEpoch"`
		Assertions            map[string]any     `json:"assertions"`
		Result                string             `json:"result"`
		IntegrityResult       string             `json:"integrityResult"`
	} `json:"scenario"`
	Limitations []string `json:"limitations"`
}

func runDeletionExactHTTPBatch(requests, concurrency int, factory func(int) (*http.Request, error)) deletionExactBatch {
	client := liveHTTPClient()
	samples := make([]liveHTTPSample, requests)
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
				started := time.Now()
				response, err := client.Do(request)
				if err != nil {
					samples[index] = liveHTTPSample{Duration: time.Since(started), Err: err}
					continue
				}
				_ = response.Body.Close()
				samples[index] = liveHTTPSample{Status: response.StatusCode, Duration: time.Since(started)}
			}
		}()
	}
	started := time.Now()
	for index := range samples {
		jobs <- index
	}
	close(jobs)
	workers.Wait()

	exact := map[string]int{}
	for _, sample := range samples {
		if sample.Err != nil {
			exact["transport_error"]++
			continue
		}
		exact[strconv.Itoa(sample.Status)]++
	}
	return deletionExactBatch{
		Summary:          summarizeLiveHTTPSamples(samples, concurrency, time.Since(started)),
		StatusCodeCounts: exact,
	}
}

func TestAccountDeletionPostFenceLoadLocalDependencies(t *testing.T) {
	if os.Getenv("MEMORY_OS_RUN_DELETION_UNDER_LOAD") != "1" {
		t.Skip("set MEMORY_OS_RUN_DELETION_UNDER_LOAD=1 to run deletion under load")
	}

	server := newLiveServer(t)
	runID := time.Now().UnixNano()
	owner := fmt.Sprintf("acct_delete_load_%d", runID)
	token := server.issueSession(t, owner)
	jobID := server.createJob(t, owner)
	server.commitPreviewForJob(t, owner, jobID)
	previewURL := server.server.URL + "/v1/import-jobs/" + jobID + "/preview"
	startedAt := time.Now().UTC()

	preFence := runDeletionExactHTTPBatch(120, 16, func(int) (*http.Request, error) {
		return liveRequest(http.MethodGet, previewURL, token, nil)
	})
	if preFence.StatusCodeCounts["200"] != 120 || preFence.Summary.Failures != 0 {
		t.Fatalf("pre-fence load did not remain all-200: %+v", preFence)
	}

	response, body := server.request(t, http.MethodDelete, "/v1/account", token, nil)
	if response.StatusCode != http.StatusAccepted {
		t.Fatalf("deletion request status %d: %s", response.StatusCode, body)
	}
	var receipt struct {
		Status        string `json:"status"`
		DeletionEpoch int64  `json:"deletionEpoch"`
	}
	if err := json.Unmarshal(body, &receipt); err != nil {
		t.Fatal(err)
	}
	if receipt.Status != "deleting" || receipt.DeletionEpoch != 2 {
		t.Fatalf("unexpected deletion fence receipt: %s", body)
	}

	start := make(chan struct{})
	postFenceCh := make(chan deletionExactBatch, 1)
	workerCh := make(chan deletionWorkerResult, 1)
	go func() {
		<-start
		postFenceCh <- runDeletionExactHTTPBatch(400, 32, func(int) (*http.Request, error) {
			return liveRequest(http.MethodGet, previewURL, token, nil)
		})
	}()
	go func() {
		<-start
		started := time.Now()
		receipts, err := (accountdelete.Worker{
			Queue:      server.accountControl,
			Repository: server.accountControl,
			Objects:    server.objects,
		}).Sweep(context.Background(), 1)
		workerCh <- deletionWorkerResult{Receipts: receipts, Err: err, Duration: time.Since(started)}
	}()
	close(start)
	postFence := <-postFenceCh
	workerResult := <-workerCh

	if postFence.StatusCodeCounts["401"] != 400 ||
		postFence.Summary.StatusClassCounts["4xx"] != 400 ||
		postFence.Summary.StatusClassCounts["5xx"] != 0 ||
		postFence.Summary.StatusClassCounts["transport_error"] != 0 ||
		postFence.Summary.Failures != 400 {
		t.Fatalf("post-fence requests were not uniformly unauthorized: %+v", postFence)
	}
	if workerResult.Err != nil {
		t.Fatal(workerResult.Err)
	}
	if len(workerResult.Receipts) != 1 || workerResult.Receipts[0].AccountID != owner {
		t.Fatalf("unexpected deletion worker receipts: %+v", workerResult.Receipts)
	}

	ownedTables := []string{
		"memory_item", "apply_confirmation", "preview_candidate", "preview_rejection",
		"preview_ready", "upload_authorization", "quarantine_object", "import_job",
		"account_session",
	}
	finalOwnedRows := 0
	for _, table := range ownedTables {
		var count int
		if err := server.pool.QueryRow(context.Background(),
			"SELECT count(*) FROM memory_os."+table+" WHERE owner_account_id = $1", owner,
		).Scan(&count); err != nil {
			t.Fatal(err)
		}
		finalOwnedRows += count
	}
	var state string
	var epoch int64
	if err := server.pool.QueryRow(context.Background(),
		"SELECT state, account_epoch FROM memory_os.account_control WHERE account_id = $1", owner,
	).Scan(&state, &epoch); err != nil {
		t.Fatal(err)
	}
	if finalOwnedRows != 0 || state != "deleted" || epoch != 2 {
		t.Fatalf("deletion integrity failed: rows=%d state=%s epoch=%d", finalOwnedRows, state, epoch)
	}

	path := os.Getenv("MEMORY_OS_DELETION_UNDER_LOAD_RESULTS_PATH")
	if path == "" {
		return
	}
	sourceCommit := os.Getenv("MEMORY_OS_COMMIT_SHA")
	if sourceCommit == "" {
		t.Fatal("MEMORY_OS_COMMIT_SHA is required when writing deletion-under-load results")
	}

	document := deletionUnderLoadResultsDocument{
		SchemaVersion: "memory-os-deletion-under-load-results.v1",
		CommitSHA:     sourceCommit,
		GeneratedAt:   time.Now().UTC().Format(time.RFC3339),
		Limitations: []string{
			"only requests started after the durable 202 fence are asserted",
			"one account and one deletion worker",
			"authenticated Preview read path only",
			"local PostgreSQL 16 and MinIO on a GitHub-hosted runner",
			"not production deletion capacity evidence",
		},
	}
	document.Environment.OS = runtime.GOOS
	document.Environment.Arch = runtime.GOARCH
	document.Environment.NumCPU = runtime.NumCPU()
	document.Environment.GoVersion = runtime.Version()
	document.Environment.DependencyMode = "LOCAL_POSTGRES_MINIO"
	document.Environment.SyntheticDataOnly = true
	document.Environment.ProductionTraffic = false
	document.Environment.ProductionCredentials = false
	document.Environment.ProductionEvidence = false
	document.Environment.ProductionEquivalentDependencies = false
	document.Environment.ContainsSecrets = false
	document.Scenario.ScenarioID = deletionUnderLoadScenarioID
	document.Scenario.StartedAt = startedAt.Format(time.RFC3339)
	document.Scenario.CompletedAt = time.Now().UTC().Format(time.RFC3339)
	document.Scenario.PreFence = preFence
	document.Scenario.DeletionRequestStatus = response.StatusCode
	document.Scenario.DeletionEpoch = receipt.DeletionEpoch
	document.Scenario.PostFence = postFence
	document.Scenario.WorkerDurationSeconds = workerResult.Duration.Seconds()
	document.Scenario.WorkerReceiptCount = len(workerResult.Receipts)
	document.Scenario.FinalOwnedRowCount = finalOwnedRows
	document.Scenario.FinalAccountState = state
	document.Scenario.FinalAccountEpoch = epoch
	document.Scenario.Assertions = map[string]any{
		"preFenceAll2xx":              preFence.StatusCodeCounts["200"] == 120,
		"deletionRequestStatus":       response.StatusCode,
		"deletionEpoch":               receipt.DeletionEpoch,
		"postFenceAllUnauthorized":    postFence.StatusCodeCounts["401"] == 400,
		"postFenceUnauthorizedCount":  postFence.StatusCodeCounts["401"],
		"postFenceNo5xx":              postFence.Summary.StatusClassCounts["5xx"] == 0,
		"postFenceNoTransportErrors":  postFence.Summary.StatusClassCounts["transport_error"] == 0,
		"workerCompleted":             workerResult.Err == nil,
		"workerReceiptCount":          len(workerResult.Receipts),
		"finalOwnedRowCount":          finalOwnedRows,
		"finalAccountState":           state,
		"finalAccountEpoch":           epoch,
		"productionEvidence":          false,
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
