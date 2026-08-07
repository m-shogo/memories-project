package httpserver

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"runtime"
	"sync"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/accountdelete"
)

const (
	deletionPrefenceMutationApplyRequests  = 16
	deletionPrefenceMutationUploadRequests = 16
	deletionPrefenceMutationTotalRequests  = 32
)

type prefenceMutationResult struct {
	Surface string
	Status  int
	Err     error
}

type deletionPrefenceMutationResultsDocument struct {
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
		ScenarioID                             string         `json:"scenarioId"`
		ApplyRequests                          int            `json:"applyRequests"`
		UploadAuthorizationRequests            int            `json:"uploadAuthorizationRequests"`
		AuthenticatedBeforeFence               int            `json:"authenticatedBeforeFence"`
		DeletionRequestStatus                  int            `json:"deletionRequestStatus"`
		DeletionEpoch                          int64          `json:"deletionEpoch"`
		ApplyUnauthorizedAfterFence            int            `json:"applyUnauthorizedAfterFence"`
		UploadAuthorizationUnauthorizedAfterFence int         `json:"uploadAuthorizationUnauthorizedAfterFence"`
		UnexpectedStatusCount                  int            `json:"unexpectedStatusCount"`
		TransportErrors                        int            `json:"transportErrors"`
		PreWorkerApplyConfirmationRows         int            `json:"preWorkerApplyConfirmationRows"`
		PreWorkerMemoryItemRows                int            `json:"preWorkerMemoryItemRows"`
		PreWorkerUploadAuthorizationRows       int            `json:"preWorkerUploadAuthorizationRows"`
		PreWorkerQuarantineRows                int            `json:"preWorkerQuarantineRows"`
		WorkerReceiptCount                     int            `json:"workerReceiptCount"`
		FinalOwnedRowCount                     int            `json:"finalOwnedRowCount"`
		FinalAccountState                      string         `json:"finalAccountState"`
		FinalAccountEpoch                      int64          `json:"finalAccountEpoch"`
		Assertions                             map[string]any `json:"assertions"`
		Result                                 string         `json:"result"`
		IntegrityResult                        string         `json:"integrityResult"`
	} `json:"scenario"`
	Limitations []string `json:"limitations"`
}

func TestAccountDeletionPrefenceMutationLinearizationLocalDependencies(t *testing.T) {
	if os.Getenv("MEMORY_OS_RUN_PREFENCE_MUTATION_LINEARIZATION") != "1" {
		t.Skip("set MEMORY_OS_RUN_PREFENCE_MUTATION_LINEARIZATION=1 to run pre-fence mutation linearization")
	}

	base := newLiveServer(t)
	owner := fmt.Sprintf("acct_prefence_mutation_%d", time.Now().UnixNano())
	token := base.issueSession(t, owner)
	previewJobID := base.createJob(t, owner)
	previewID, previewSHA := base.commitPreviewForJob(t, owner, previewJobID)

	uploadJobIDs := make([]string, deletionPrefenceMutationUploadRequests)
	for index := range uploadJobIDs {
		uploadJobIDs[index] = base.createJob(t, owner)
	}

	resolver := newPrefenceBarrierResolver(base.sessions, deletionPrefenceMutationTotalRequests)
	barrierServer := newPrefenceBarrierServer(t, base, resolver)
	client := &http.Client{Timeout: 20 * time.Second}
	results := make(chan prefenceMutationResult, deletionPrefenceMutationTotalRequests)
	start := make(chan struct{})
	var requests sync.WaitGroup

	for index := 0; index < deletionPrefenceMutationApplyRequests; index++ {
		requests.Add(1)
		go func(index int) {
			defer requests.Done()
			<-start
			body, err := json.Marshal(map[string]any{
				"previewSha256":   previewSHA,
				"idempotencyKey":  fmt.Sprintf("idem-prefence-mutation-%02d", index),
				"duplicatePolicy": "skip_existing",
			})
			if err != nil {
				results <- prefenceMutationResult{Surface: "apply", Err: err}
				return
			}
			request, err := liveRequest(
				http.MethodPost,
				barrierServer.URL+"/v1/previews/"+previewID+"/apply",
				token,
				body,
			)
			if err != nil {
				results <- prefenceMutationResult{Surface: "apply", Err: err}
				return
			}
			response, err := client.Do(request)
			if err != nil {
				results <- prefenceMutationResult{Surface: "apply", Err: err}
				return
			}
			_, readErr := io.Copy(io.Discard, io.LimitReader(response.Body, 1<<20))
			closeErr := response.Body.Close()
			if readErr != nil {
				results <- prefenceMutationResult{Surface: "apply", Err: readErr}
				return
			}
			if closeErr != nil {
				results <- prefenceMutationResult{Surface: "apply", Err: closeErr}
				return
			}
			results <- prefenceMutationResult{Surface: "apply", Status: response.StatusCode}
		}(index)
	}

	for index := 0; index < deletionPrefenceMutationUploadRequests; index++ {
		requests.Add(1)
		go func(index int) {
			defer requests.Done()
			<-start
			payload := []byte(fmt.Sprintf("title,date\nprefence mutation %02d,2026-08-07\n", index))
			digest := sha256.Sum256(payload)
			body, err := json.Marshal(map[string]any{
				"contentLength":   len(payload),
				"checksumSha256":  hex.EncodeToString(digest[:]),
				"contentType":     "text/csv",
				"sourceSurface":   "ios_files",
				"displayFilename": fmt.Sprintf("prefence-%02d.csv", index),
			})
			if err != nil {
				results <- prefenceMutationResult{Surface: "upload_authorization", Err: err}
				return
			}
			request, err := liveRequest(
				http.MethodPost,
				barrierServer.URL+"/v1/import-jobs/"+uploadJobIDs[index]+"/upload-authorizations",
				token,
				body,
			)
			if err != nil {
				results <- prefenceMutationResult{Surface: "upload_authorization", Err: err}
				return
			}
			response, err := client.Do(request)
			if err != nil {
				results <- prefenceMutationResult{Surface: "upload_authorization", Err: err}
				return
			}
			_, readErr := io.Copy(io.Discard, io.LimitReader(response.Body, 1<<20))
			closeErr := response.Body.Close()
			if readErr != nil {
				results <- prefenceMutationResult{Surface: "upload_authorization", Err: readErr}
				return
			}
			if closeErr != nil {
				results <- prefenceMutationResult{Surface: "upload_authorization", Err: closeErr}
				return
			}
			results <- prefenceMutationResult{Surface: "upload_authorization", Status: response.StatusCode}
		}(index)
	}

	close(start)
	select {
	case <-resolver.allResolved:
	case <-time.After(15 * time.Second):
		t.Fatalf("only %d/%d sessions resolved before deletion fence", resolver.resolvedCount(), deletionPrefenceMutationTotalRequests)
	}
	if resolver.resolvedCount() != deletionPrefenceMutationTotalRequests {
		t.Fatalf("old-epoch authentication barrier drift: %d", resolver.resolvedCount())
	}

	response, body := base.request(t, http.MethodDelete, "/v1/account", token, nil)
	if response.StatusCode != http.StatusAccepted {
		t.Fatalf("deletion request status %d: %s", response.StatusCode, body)
	}
	var deletion struct {
		Status        string `json:"status"`
		DeletionEpoch int64  `json:"deletionEpoch"`
	}
	if err := json.Unmarshal(body, &deletion); err != nil {
		t.Fatal(err)
	}
	if deletion.Status != "deleting" || deletion.DeletionEpoch != 2 {
		t.Fatalf("unexpected durable deletion fence: %s", body)
	}

	close(resolver.release)
	requests.Wait()
	close(results)
	applyUnauthorized := 0
	uploadUnauthorized := 0
	unexpected := 0
	transportErrors := 0
	for result := range results {
		if result.Err != nil {
			transportErrors++
			continue
		}
		if result.Status != http.StatusUnauthorized {
			unexpected++
			continue
		}
		switch result.Surface {
		case "apply":
			applyUnauthorized++
		case "upload_authorization":
			uploadUnauthorized++
		default:
			unexpected++
		}
	}
	if applyUnauthorized != deletionPrefenceMutationApplyRequests ||
		uploadUnauthorized != deletionPrefenceMutationUploadRequests ||
		unexpected != 0 || transportErrors != 0 {
		t.Fatalf(
			"pre-fence mutation requests escaped fence: apply401=%d upload401=%d unexpected=%d transport=%d",
			applyUnauthorized, uploadUnauthorized, unexpected, transportErrors,
		)
	}

	preWorkerCounts := map[string]int{}
	queries := map[string]string{
		"apply_confirmation": `SELECT count(*) FROM memory_os.apply_confirmation WHERE owner_account_id = $1`,
		"memory_item":         `SELECT count(*) FROM memory_os.memory_item WHERE owner_account_id = $1`,
		"upload_authorization": `SELECT count(*) FROM memory_os.upload_authorization WHERE owner_account_id = $1`,
		"quarantine_object":   `SELECT count(*) FROM memory_os.quarantine_object WHERE owner_account_id = $1`,
	}
	for name, query := range queries {
		var count int
		if err := base.pool.QueryRow(context.Background(), query, owner).Scan(&count); err != nil {
			t.Fatal(err)
		}
		preWorkerCounts[name] = count
	}
	if preWorkerCounts["apply_confirmation"] != 0 ||
		preWorkerCounts["memory_item"] != 0 ||
		preWorkerCounts["upload_authorization"] != 0 ||
		preWorkerCounts["quarantine_object"] != 0 {
		t.Fatalf("old-epoch requests created durable mutation before worker erasure: %+v", preWorkerCounts)
	}

	receipts, err := (accountdelete.Worker{
		Queue:      base.accountControl,
		Repository: base.accountControl,
		Objects:    base.objects,
	}).Sweep(context.Background(), 1)
	if err != nil {
		t.Fatal(err)
	}
	if len(receipts) != 1 || receipts[0].AccountID != owner {
		t.Fatalf("unexpected deletion worker receipts: %+v", receipts)
	}

	ownedTables := []string{
		"memory_item", "apply_confirmation", "preview_candidate", "preview_rejection",
		"preview_ready", "upload_authorization", "quarantine_object", "import_job",
		"account_session",
	}
	finalOwnedRows := 0
	for _, table := range ownedTables {
		var count int
		if err := base.pool.QueryRow(context.Background(),
			"SELECT count(*) FROM memory_os."+table+" WHERE owner_account_id = $1", owner,
		).Scan(&count); err != nil {
			t.Fatal(err)
		}
		finalOwnedRows += count
	}
	var finalState string
	var finalEpoch int64
	if err := base.pool.QueryRow(context.Background(),
		"SELECT state, account_epoch FROM memory_os.account_control WHERE account_id = $1", owner,
	).Scan(&finalState, &finalEpoch); err != nil {
		t.Fatal(err)
	}
	if finalOwnedRows != 0 || finalState != "deleted" || finalEpoch != 2 {
		t.Fatalf("deletion integrity failed: rows=%d state=%s epoch=%d", finalOwnedRows, finalState, finalEpoch)
	}

	resultPath := os.Getenv("MEMORY_OS_PREFENCE_MUTATION_LINEARIZATION_RESULTS_PATH")
	if resultPath == "" {
		return
	}
	commitSHA := os.Getenv("MEMORY_OS_COMMIT_SHA")
	if len(commitSHA) != 40 {
		t.Fatal("full MEMORY_OS_COMMIT_SHA is required when writing pre-fence mutation linearization evidence")
	}

	document := deletionPrefenceMutationResultsDocument{
		SchemaVersion: "memory-os-deletion-prefence-mutation-linearization-results.v1",
		CommitSHA:     commitSHA,
		GeneratedAt:   time.Now().UTC().Format(time.RFC3339),
		Limitations: []string{
			"covers Apply and upload authorization but not upload completion already in flight",
			"one synthetic account and one deletion worker",
			"local PostgreSQL 16 and MinIO on a GitHub-hosted runner",
			"not production deletion-capacity evidence",
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
	document.Scenario.ScenarioID = "account-deletion-prefence-mutation-linearization-local-dependencies"
	document.Scenario.ApplyRequests = deletionPrefenceMutationApplyRequests
	document.Scenario.UploadAuthorizationRequests = deletionPrefenceMutationUploadRequests
	document.Scenario.AuthenticatedBeforeFence = resolver.resolvedCount()
	document.Scenario.DeletionRequestStatus = response.StatusCode
	document.Scenario.DeletionEpoch = deletion.DeletionEpoch
	document.Scenario.ApplyUnauthorizedAfterFence = applyUnauthorized
	document.Scenario.UploadAuthorizationUnauthorizedAfterFence = uploadUnauthorized
	document.Scenario.UnexpectedStatusCount = unexpected
	document.Scenario.TransportErrors = transportErrors
	document.Scenario.PreWorkerApplyConfirmationRows = preWorkerCounts["apply_confirmation"]
	document.Scenario.PreWorkerMemoryItemRows = preWorkerCounts["memory_item"]
	document.Scenario.PreWorkerUploadAuthorizationRows = preWorkerCounts["upload_authorization"]
	document.Scenario.PreWorkerQuarantineRows = preWorkerCounts["quarantine_object"]
	document.Scenario.WorkerReceiptCount = len(receipts)
	document.Scenario.FinalOwnedRowCount = finalOwnedRows
	document.Scenario.FinalAccountState = finalState
	document.Scenario.FinalAccountEpoch = finalEpoch
	document.Scenario.Assertions = map[string]any{
		"allAuthenticatedBeforeFence": resolver.resolvedCount() == deletionPrefenceMutationTotalRequests,
		"allApplyUnauthorizedAfterFence": applyUnauthorized == deletionPrefenceMutationApplyRequests,
		"allUploadAuthorizationUnauthorizedAfterFence": uploadUnauthorized == deletionPrefenceMutationUploadRequests,
		"noUnexpectedStatuses": unexpected == 0,
		"noTransportErrors": transportErrors == 0,
		"noPreWorkerMutation": preWorkerCounts["apply_confirmation"] == 0 &&
			preWorkerCounts["memory_item"] == 0 &&
			preWorkerCounts["upload_authorization"] == 0 &&
			preWorkerCounts["quarantine_object"] == 0,
		"deletionWorkerCompleted": len(receipts) == 1,
		"finalOwnedRowCount": finalOwnedRows,
		"productionEvidence": false,
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
