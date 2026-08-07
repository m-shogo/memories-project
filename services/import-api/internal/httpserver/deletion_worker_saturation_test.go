package httpserver

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"runtime"
	"sync"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/accountdelete"
)

const (
	deletionWorkerSaturationAccounts        = 24
	deletionWorkerSaturationWorkers         = 4
	deletionWorkerSaturationPerWorker       = 6
	deletionWorkerControlPreviewRequests    = 400
	deletionWorkerControlPreviewConcurrency = 16
)

type deletionWorkerSweepResult struct {
	Receipts []accountdelete.Receipt
	Err      error
	Duration time.Duration
}

type deletionWorkerSaturationResultsDocument struct {
	SchemaVersion string `json:"schemaVersion"`
	CommitSHA     string `json:"commitSha"`
	GeneratedAt   string `json:"generatedAt"`
	Environment   struct {
		OS                               string `json:"os"`
		Arch                             string `json:"arch"`
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
		ScenarioID                    string         `json:"scenarioId"`
		DeletingAccounts              int            `json:"deletingAccounts"`
		WorkerCount                   int            `json:"workerCount"`
		MaxAccountsPerWorker          int            `json:"maxAccountsPerWorker"`
		AllDeletionRequestsAccepted   bool           `json:"allDeletionRequestsAccepted"`
		DeletionEpoch                 int64          `json:"deletionEpoch"`
		WorkerErrors                  int            `json:"workerErrors"`
		WorkerReceiptCount            int            `json:"workerReceiptCount"`
		UniqueWorkerReceiptCount      int            `json:"uniqueWorkerReceiptCount"`
		DuplicateWorkerReceiptCount   int            `json:"duplicateWorkerReceiptCount"`
		ControlPreviewRequests        int            `json:"controlPreviewRequests"`
		ControlPreviewConcurrency     int            `json:"controlPreviewConcurrency"`
		ControlPreview2xx             int            `json:"controlPreview2xx"`
		ControlPreview5xx             int            `json:"controlPreview5xx"`
		ControlPreviewTransportErrors int            `json:"controlPreviewTransportErrors"`
		FinalDeletionPending          int64          `json:"finalDeletionPending"`
		FinalDeletionStuck            int64          `json:"finalDeletionStuck"`
		FinalOwnedRowCount            int            `json:"finalOwnedRowCount"`
		AllDeletionTombstonesEpoch2   bool           `json:"allDeletionTombstonesEpoch2"`
		Assertions                    map[string]any `json:"assertions"`
		Result                        string         `json:"result"`
		IntegrityResult               string         `json:"integrityResult"`
	} `json:"scenario"`
	Limitations []string `json:"limitations"`
}

func TestMultiAccountDeletionWorkerSaturationLocalDependencies(t *testing.T) {
	if os.Getenv("MEMORY_OS_RUN_DELETION_WORKER_SATURATION") != "1" {
		t.Skip("set MEMORY_OS_RUN_DELETION_WORKER_SATURATION=1 to run multi-account deletion-worker saturation")
	}

	server := newLiveServer(t)
	deletingAccounts := make([]string, 0, deletionWorkerSaturationAccounts)
	allDeletionRequestsAccepted := true
	for index := 0; index < deletionWorkerSaturationAccounts; index++ {
		owner := fmt.Sprintf("acct_worker_sat_%d_%02d", time.Now().UnixNano(), index)
		token := server.issueSession(t, owner)
		jobID := server.createJob(t, owner)
		server.commitPreviewForJob(t, owner, jobID)
		response, body := server.request(t, http.MethodDelete, "/v1/account", token, nil)
		if response.StatusCode != http.StatusAccepted {
			allDeletionRequestsAccepted = false
			t.Fatalf("deletion request %d status %d: %s", index, response.StatusCode, body)
		}
		var deletion struct {
			Status        string `json:"status"`
			DeletionEpoch int64  `json:"deletionEpoch"`
		}
		if err := json.Unmarshal(body, &deletion); err != nil {
			t.Fatal(err)
		}
		if deletion.Status != "deleting" || deletion.DeletionEpoch != 2 {
			allDeletionRequestsAccepted = false
			t.Fatalf("deletion request %d fence drift: %s", index, body)
		}
		deletingAccounts = append(deletingAccounts, owner)
	}

	controlOwner := fmt.Sprintf("acct_worker_control_%d", time.Now().UnixNano())
	controlToken := server.issueSession(t, controlOwner)
	controlJobID := server.createJob(t, controlOwner)
	server.commitPreviewForJob(t, controlOwner, controlJobID)
	controlPreviewURL := server.server.URL + "/v1/import-jobs/" + controlJobID + "/preview"

	start := make(chan struct{})
	workerResults := make(chan deletionWorkerSweepResult, deletionWorkerSaturationWorkers)
	var workerWG sync.WaitGroup
	for workerIndex := 0; workerIndex < deletionWorkerSaturationWorkers; workerIndex++ {
		workerWG.Add(1)
		go func() {
			defer workerWG.Done()
			<-start
			started := time.Now()
			receipts, err := (accountdelete.Worker{
				Queue:      server.accountControl,
				Repository: server.accountControl,
				Objects:    server.objects,
			}).Sweep(context.Background(), deletionWorkerSaturationPerWorker)
			workerResults <- deletionWorkerSweepResult{Receipts: receipts, Err: err, Duration: time.Since(started)}
		}()
	}

	controlResults := make(chan liveBatchResult, 1)
	go func() {
		<-start
		controlResults <- runLiveHTTPBatch(
			deletionWorkerControlPreviewRequests,
			deletionWorkerControlPreviewConcurrency,
			func(int) (*http.Request, error) {
				return liveRequest(http.MethodGet, controlPreviewURL, controlToken, nil)
			},
		)
	}()
	close(start)
	workerWG.Wait()
	close(workerResults)
	control := <-controlResults

	workerErrors := 0
	receiptCount := 0
	seen := make(map[string]struct{}, deletionWorkerSaturationAccounts)
	duplicateReceipts := 0
	for result := range workerResults {
		if result.Err != nil {
			workerErrors++
			continue
		}
		for _, receipt := range result.Receipts {
			receiptCount++
			if _, exists := seen[receipt.AccountID]; exists {
				duplicateReceipts++
				continue
			}
			seen[receipt.AccountID] = struct{}{}
		}
	}
	if workerErrors != 0 || receiptCount != deletionWorkerSaturationAccounts || len(seen) != deletionWorkerSaturationAccounts || duplicateReceipts != 0 {
		t.Fatalf("worker saturation accounting drift: errors=%d receipts=%d unique=%d duplicates=%d", workerErrors, receiptCount, len(seen), duplicateReceipts)
	}
	if control.Successes != deletionWorkerControlPreviewRequests || control.Failures != 0 ||
		control.StatusClassCounts["2xx"] != deletionWorkerControlPreviewRequests ||
		control.StatusClassCounts["5xx"] != 0 || control.StatusClassCounts["transport_error"] != 0 {
		t.Fatalf("unrelated Preview traffic degraded during deletion saturation: %+v", control)
	}

	backlog, err := server.accountControl.Backlog(context.Background(), accountdelete.StuckAttemptsThreshold)
	if err != nil {
		t.Fatal(err)
	}
	if backlog.Pending != 0 || backlog.Stuck != 0 {
		t.Fatalf("deletion backlog did not converge: pending=%d stuck=%d", backlog.Pending, backlog.Stuck)
	}

	ownedTables := []string{
		"memory_item", "apply_confirmation", "preview_candidate", "preview_rejection",
		"preview_ready", "upload_authorization", "quarantine_object", "import_job",
		"account_session",
	}
	finalOwnedRows := 0
	allTombstonesEpoch2 := true
	for _, owner := range deletingAccounts {
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
		if state != "deleted" || epoch != 2 {
			allTombstonesEpoch2 = false
		}
	}
	if finalOwnedRows != 0 || !allTombstonesEpoch2 {
		t.Fatalf("multi-account deletion integrity failed: rows=%d tombstonesEpoch2=%v", finalOwnedRows, allTombstonesEpoch2)
	}

	resultPath := os.Getenv("MEMORY_OS_DELETION_WORKER_SATURATION_RESULTS_PATH")
	if resultPath == "" {
		return
	}
	commitSHA := os.Getenv("MEMORY_OS_COMMIT_SHA")
	if len(commitSHA) != 40 {
		t.Fatal("full MEMORY_OS_COMMIT_SHA is required when writing deletion-worker saturation evidence")
	}

	document := deletionWorkerSaturationResultsDocument{
		SchemaVersion: "memory-os-deletion-worker-saturation-results.v1",
		CommitSHA:     commitSHA,
		GeneratedAt:   time.Now().UTC().Format(time.RFC3339),
		Limitations: []string{
			"bounded local workload with 24 synthetic deleting accounts and four workers",
			"control traffic is authenticated Preview read only",
			"local PostgreSQL 16 and MinIO on a GitHub-hosted runner",
			"not a production capacity or operating-threshold claim",
		},
	}
	document.Environment.OS = runtime.GOOS
	document.Environment.Arch = runtime.GOARCH
	document.Environment.GoVersion = runtime.Version()
	document.Environment.DependencyMode = "LOCAL_POSTGRES_MINIO"
	document.Environment.SyntheticDataOnly = true
	document.Environment.ProductionTraffic = false
	document.Environment.ProductionCredentials = false
	document.Environment.ProductionEvidence = false
	document.Environment.ProductionEquivalentDependencies = false
	document.Environment.ContainsSecrets = false
	document.Scenario.ScenarioID = "multi-account-deletion-worker-saturation-local-dependencies"
	document.Scenario.DeletingAccounts = deletionWorkerSaturationAccounts
	document.Scenario.WorkerCount = deletionWorkerSaturationWorkers
	document.Scenario.MaxAccountsPerWorker = deletionWorkerSaturationPerWorker
	document.Scenario.AllDeletionRequestsAccepted = allDeletionRequestsAccepted
	document.Scenario.DeletionEpoch = 2
	document.Scenario.WorkerErrors = workerErrors
	document.Scenario.WorkerReceiptCount = receiptCount
	document.Scenario.UniqueWorkerReceiptCount = len(seen)
	document.Scenario.DuplicateWorkerReceiptCount = duplicateReceipts
	document.Scenario.ControlPreviewRequests = deletionWorkerControlPreviewRequests
	document.Scenario.ControlPreviewConcurrency = deletionWorkerControlPreviewConcurrency
	document.Scenario.ControlPreview2xx = control.StatusClassCounts["2xx"]
	document.Scenario.ControlPreview5xx = control.StatusClassCounts["5xx"]
	document.Scenario.ControlPreviewTransportErrors = control.StatusClassCounts["transport_error"]
	document.Scenario.FinalDeletionPending = backlog.Pending
	document.Scenario.FinalDeletionStuck = backlog.Stuck
	document.Scenario.FinalOwnedRowCount = finalOwnedRows
	document.Scenario.AllDeletionTombstonesEpoch2 = allTombstonesEpoch2
	document.Scenario.Assertions = map[string]any{
		"allDeletionRequestsAccepted":  allDeletionRequestsAccepted,
		"workerReceiptsUnique":         len(seen) == deletionWorkerSaturationAccounts && duplicateReceipts == 0,
		"controlPreviewAll2xx":         control.StatusClassCounts["2xx"] == deletionWorkerControlPreviewRequests,
		"deletionBacklogConverged":     backlog.Pending == 0 && backlog.Stuck == 0,
		"finalOwnedRowsZero":           finalOwnedRows == 0,
		"allDeletionTombstonesEpoch2":  allTombstonesEpoch2,
		"capacityBoundaryEstablished":  false,
		"operationalThresholdApproved": false,
		"productionEvidence":           false,
	}
	document.Scenario.Result = "PASS"
	document.Scenario.IntegrityResult = "PASS"

	payload, err := json.MarshalIndent(document, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(resultPath, append(payload, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}
