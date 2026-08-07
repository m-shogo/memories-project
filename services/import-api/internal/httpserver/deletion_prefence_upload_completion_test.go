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
	"net/http/httptest"
	"os"
	"runtime"
	"sync"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/accountdelete"
	"github.com/m-shogo/memories-project/services/import-api/internal/apply"
	"github.com/m-shogo/memories-project/services/import-api/internal/cryptoids"
	"github.com/m-shogo/memories-project/services/import-api/internal/epochguard"
	"github.com/m-shogo/memories-project/services/import-api/internal/fenced"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgrepo"
	"github.com/m-shogo/memories-project/services/import-api/internal/previewread"
	"github.com/m-shogo/memories-project/services/import-api/internal/upload"
)

const deletionPrefenceUploadCompletionRequests = 16

type postHeadBarrierStore struct {
	inner       upload.ObjectStore
	expected    int
	mu          sync.Mutex
	reached     int
	allReached  chan struct{}
	release     chan struct{}
}

func newPostHeadBarrierStore(inner upload.ObjectStore, expected int) *postHeadBarrierStore {
	return &postHeadBarrierStore{
		inner:      inner,
		expected:   expected,
		allReached: make(chan struct{}),
		release:    make(chan struct{}),
	}
}

func (s *postHeadBarrierStore) HeadObject(ctx context.Context, key string) (upload.ObjectMetadata, error) {
	metadata, err := s.inner.HeadObject(ctx, key)
	if err != nil {
		return upload.ObjectMetadata{}, err
	}
	s.mu.Lock()
	s.reached++
	if s.reached == s.expected {
		close(s.allReached)
	}
	s.mu.Unlock()
	select {
	case <-s.release:
		return metadata, nil
	case <-ctx.Done():
		return upload.ObjectMetadata{}, ctx.Err()
	}
}

func (s *postHeadBarrierStore) reachedCount() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.reached
}

func newPrefenceUploadCompletionServer(t *testing.T, base *liveServer, objects upload.ObjectStore) *httptest.Server {
	t.Helper()
	guard := epochguard.Guard{Source: base.accountControl}
	uploadService := &upload.Service{
		Transactions: base.executor,
		Repository:   pgrepo.Upload{},
		Signer:       base.objects,
		Objects:      objects,
		IDs:          cryptoids.Generator{},
	}
	handler := New(Config{
		Sessions: base.sessions,
		Upload:   fenced.Upload{Guard: guard, Inner: uploadService},
		Preview:  fenced.PreviewRead{Guard: guard, Inner: &previewread.Service{Transactions: base.executor}},
		Apply: fenced.Apply{Guard: guard, Inner: &apply.Service{
			Transactions: base.executor,
			Repository:   pgrepo.Apply{},
			IDs:          cryptoids.Generator{},
		}},
		Account:    accountdelete.Service{Repository: base.accountControl, Guard: guard},
		AppleLogin: base.apple,
	})
	server := httptest.NewServer(handler)
	t.Cleanup(server.Close)
	return server
}

type prefenceUploadCompletionHTTPResult struct {
	Status int
	Err    error
}

type deletionPrefenceUploadCompletionResultsDocument struct {
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
		ScenarioID                       string         `json:"scenarioId"`
		IssuedAndUploadedBeforeFence     int            `json:"issuedAndUploadedBeforeFence"`
		RealHeadCompletedBeforeFence     int            `json:"realHeadCompletedBeforeFence"`
		DeletionRequestStatus            int            `json:"deletionRequestStatus"`
		DeletionEpoch                    int64          `json:"deletionEpoch"`
		CompletionUnauthorizedAfterFence int            `json:"completionUnauthorizedAfterFence"`
		UnexpectedStatusCount            int            `json:"unexpectedStatusCount"`
		TransportErrors                  int            `json:"transportErrors"`
		PreWorkerIssuedAuthorizationRows int            `json:"preWorkerIssuedAuthorizationRows"`
		PreWorkerConsumedAuthorizationRows int          `json:"preWorkerConsumedAuthorizationRows"`
		PreWorkerQuarantineRows          int            `json:"preWorkerQuarantineRows"`
		WorkerReceiptCount               int            `json:"workerReceiptCount"`
		ErasedObjectVersions             int64          `json:"erasedObjectVersions"`
		FinalOwnedRowCount               int            `json:"finalOwnedRowCount"`
		FinalAccountState                string         `json:"finalAccountState"`
		FinalAccountEpoch                int64          `json:"finalAccountEpoch"`
		Assertions                       map[string]any `json:"assertions"`
		Result                           string         `json:"result"`
		IntegrityResult                  string         `json:"integrityResult"`
	} `json:"scenario"`
	Limitations []string `json:"limitations"`
}

func issueAndPutPrefenceUpload(t *testing.T, server *liveServer, ownerToken, jobID string, index int) string {
	t.Helper()
	payload := []byte(fmt.Sprintf("title,date\nprefence completion %02d,2026-08-07\n", index))
	digest := sha256.Sum256(payload)
	body, err := json.Marshal(map[string]any{
		"contentLength":   len(payload),
		"checksumSha256":  hex.EncodeToString(digest[:]),
		"contentType":     "text/csv",
		"sourceSurface":   "ios_files",
		"displayFilename": fmt.Sprintf("prefence-complete-%02d.csv", index),
	})
	if err != nil {
		t.Fatal(err)
	}
	response, responseBody := server.request(t, http.MethodPost, "/v1/import-jobs/"+jobID+"/upload-authorizations", ownerToken, body)
	if response.StatusCode != http.StatusCreated {
		t.Fatalf("issue upload authorization %d status=%d body=%s", index, response.StatusCode, responseBody)
	}
	var issued issuedUpload
	if err := json.Unmarshal(responseBody, &issued); err != nil {
		t.Fatal(err)
	}
	if issued.AuthorizationID == "" || issued.UploadURL == "" || len(issued.RequiredHeaders) == 0 {
		t.Fatalf("issue upload authorization %d returned incomplete contract", index)
	}

	request, err := http.NewRequest(http.MethodPut, issued.UploadURL, bytes.NewReader(payload))
	if err != nil {
		t.Fatal(err)
	}
	request.ContentLength = int64(len(payload))
	for name, value := range issued.RequiredHeaders {
		if name != "Content-Length" {
			request.Header.Set(name, value)
		}
	}
	putResponse, err := (&http.Client{Timeout: 20 * time.Second}).Do(request)
	if err != nil {
		t.Fatalf("put upload %d: %v", index, err)
	}
	_, readErr := io.Copy(io.Discard, io.LimitReader(putResponse.Body, 1<<20))
	closeErr := putResponse.Body.Close()
	if readErr != nil {
		t.Fatal(readErr)
	}
	if closeErr != nil {
		t.Fatal(closeErr)
	}
	if putResponse.StatusCode != http.StatusOK {
		t.Fatalf("put upload %d status=%d", index, putResponse.StatusCode)
	}
	return issued.AuthorizationID
}

func TestAccountDeletionPrefenceUploadCompletionLocalDependencies(t *testing.T) {
	if os.Getenv("MEMORY_OS_RUN_PREFENCE_UPLOAD_COMPLETION") != "1" {
		t.Skip("set MEMORY_OS_RUN_PREFENCE_UPLOAD_COMPLETION=1 to run in-flight upload completion fencing")
	}

	base := newLiveServer(t)
	owner := fmt.Sprintf("acct_prefence_complete_%d", time.Now().UnixNano())
	token := base.issueSession(t, owner)
	authorizationIDs := make([]string, deletionPrefenceUploadCompletionRequests)
	for index := range authorizationIDs {
		jobID := base.createJob(t, owner)
		authorizationIDs[index] = issueAndPutPrefenceUpload(t, base, token, jobID, index)
	}

	barrierStore := newPostHeadBarrierStore(base.objects, deletionPrefenceUploadCompletionRequests)
	completionServer := newPrefenceUploadCompletionServer(t, base, barrierStore)
	client := &http.Client{Timeout: 30 * time.Second}
	results := make(chan prefenceUploadCompletionHTTPResult, deletionPrefenceUploadCompletionRequests)
	start := make(chan struct{})
	var requests sync.WaitGroup
	for _, authorizationID := range authorizationIDs {
		authorizationID := authorizationID
		requests.Add(1)
		go func() {
			defer requests.Done()
			<-start
			request, err := liveRequest(
				http.MethodPost,
				completionServer.URL+"/v1/upload-authorizations/"+authorizationID+"/complete",
				token,
				nil,
			)
			if err != nil {
				results <- prefenceUploadCompletionHTTPResult{Err: err}
				return
			}
			response, err := client.Do(request)
			if err != nil {
				results <- prefenceUploadCompletionHTTPResult{Err: err}
				return
			}
			_, readErr := io.Copy(io.Discard, io.LimitReader(response.Body, 1<<20))
			closeErr := response.Body.Close()
			if readErr != nil {
				results <- prefenceUploadCompletionHTTPResult{Err: readErr}
				return
			}
			if closeErr != nil {
				results <- prefenceUploadCompletionHTTPResult{Err: closeErr}
				return
			}
			results <- prefenceUploadCompletionHTTPResult{Status: response.StatusCode}
		}()
	}
	close(start)

	select {
	case <-barrierStore.allReached:
	case <-time.After(20 * time.Second):
		t.Fatalf("only %d/%d completion requests reached real MinIO HEAD", barrierStore.reachedCount(), deletionPrefenceUploadCompletionRequests)
	}
	if barrierStore.reachedCount() != deletionPrefenceUploadCompletionRequests {
		t.Fatalf("real HEAD barrier drift: %d", barrierStore.reachedCount())
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

	close(barrierStore.release)
	requests.Wait()
	close(results)
	unauthorized := 0
	unexpected := 0
	transportErrors := 0
	for result := range results {
		if result.Err != nil {
			transportErrors++
			continue
		}
		if result.Status == http.StatusUnauthorized {
			unauthorized++
		} else {
			unexpected++
		}
	}
	if unauthorized != deletionPrefenceUploadCompletionRequests || unexpected != 0 || transportErrors != 0 {
		t.Fatalf("in-flight completion requests escaped post-HEAD fence: unauthorized=%d unexpected=%d transport=%d", unauthorized, unexpected, transportErrors)
	}

	var issuedRows int
	var consumedRows int
	var quarantineRows int
	if err := base.pool.QueryRow(context.Background(),
		`SELECT count(*) FILTER (WHERE state = 'issued'), count(*) FILTER (WHERE state = 'consumed')
		 FROM memory_os.upload_authorization WHERE owner_account_id = $1`, owner,
	).Scan(&issuedRows, &consumedRows); err != nil {
		t.Fatal(err)
	}
	if err := base.pool.QueryRow(context.Background(),
		`SELECT count(*) FROM memory_os.quarantine_object WHERE owner_account_id = $1`, owner,
	).Scan(&quarantineRows); err != nil {
		t.Fatal(err)
	}
	if issuedRows != deletionPrefenceUploadCompletionRequests || consumedRows != 0 || quarantineRows != 0 {
		t.Fatalf("post-fence completion mutated durable state before worker: issued=%d consumed=%d quarantine=%d", issuedRows, consumedRows, quarantineRows)
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
	erasedVersions := int64(0)
	for _, removal := range receipts[0].Removals {
		if removal.Table == "quarantine_object_versions" {
			erasedVersions += removal.Removed
		}
	}
	if erasedVersions != deletionPrefenceUploadCompletionRequests {
		t.Fatalf("deleted object-version accounting mismatch: got=%d want=%d", erasedVersions, deletionPrefenceUploadCompletionRequests)
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

	resultPath := os.Getenv("MEMORY_OS_PREFENCE_UPLOAD_COMPLETION_RESULTS_PATH")
	if resultPath == "" {
		return
	}
	commitSHA := os.Getenv("MEMORY_OS_COMMIT_SHA")
	if len(commitSHA) != 40 {
		t.Fatal("full MEMORY_OS_COMMIT_SHA is required when writing upload-completion evidence")
	}

	document := deletionPrefenceUploadCompletionResultsDocument{
		SchemaVersion: "memory-os-deletion-prefence-upload-completion-results.v1",
		CommitSHA:     commitSHA,
		GeneratedAt:   time.Now().UTC().Format(time.RFC3339),
		Limitations: []string{
			"one synthetic account and 16 in-flight upload-completion requests",
			"local PostgreSQL 16 and versioned MinIO on a GitHub-hosted runner",
			"does not prove process or host failure during deletion-worker erasure",
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
	document.Scenario.ScenarioID = "account-deletion-prefence-upload-completion-local-dependencies"
	document.Scenario.IssuedAndUploadedBeforeFence = deletionPrefenceUploadCompletionRequests
	document.Scenario.RealHeadCompletedBeforeFence = barrierStore.reachedCount()
	document.Scenario.DeletionRequestStatus = response.StatusCode
	document.Scenario.DeletionEpoch = deletion.DeletionEpoch
	document.Scenario.CompletionUnauthorizedAfterFence = unauthorized
	document.Scenario.UnexpectedStatusCount = unexpected
	document.Scenario.TransportErrors = transportErrors
	document.Scenario.PreWorkerIssuedAuthorizationRows = issuedRows
	document.Scenario.PreWorkerConsumedAuthorizationRows = consumedRows
	document.Scenario.PreWorkerQuarantineRows = quarantineRows
	document.Scenario.WorkerReceiptCount = len(receipts)
	document.Scenario.ErasedObjectVersions = erasedVersions
	document.Scenario.FinalOwnedRowCount = finalOwnedRows
	document.Scenario.FinalAccountState = finalState
	document.Scenario.FinalAccountEpoch = finalEpoch
	document.Scenario.Assertions = map[string]any{
		"allRealHeadsCompletedBeforeFence": barrierStore.reachedCount() == deletionPrefenceUploadCompletionRequests,
		"allCompletionRequestsUnauthorizedAfterFence": unauthorized == deletionPrefenceUploadCompletionRequests,
		"noUnexpectedStatuses": unexpected == 0,
		"noTransportErrors": transportErrors == 0,
		"noCompletionMutationBeforeWorker": issuedRows == deletionPrefenceUploadCompletionRequests && consumedRows == 0 && quarantineRows == 0,
		"allUploadedObjectVersionsErased": erasedVersions == deletionPrefenceUploadCompletionRequests,
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
