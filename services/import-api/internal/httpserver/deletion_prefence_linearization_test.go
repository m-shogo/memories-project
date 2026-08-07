package httpserver

import (
	"context"
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
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
	"github.com/m-shogo/memories-project/services/import-api/internal/upload"
)

const deletionPrefenceLinearizationRequests = 32

type prefenceBarrierResolver struct {
	inner       PrincipalResolver
	expected    int
	mu          sync.Mutex
	resolved    int
	allResolved chan struct{}
	release     chan struct{}
}

func newPrefenceBarrierResolver(inner PrincipalResolver, expected int) *prefenceBarrierResolver {
	return &prefenceBarrierResolver{
		inner:       inner,
		expected:    expected,
		allResolved: make(chan struct{}),
		release:     make(chan struct{}),
	}
}

func (r *prefenceBarrierResolver) Resolve(ctx context.Context, token string) (security.Principal, error) {
	principal, err := r.inner.Resolve(ctx, token)
	if err != nil {
		return security.Principal{}, err
	}
	r.mu.Lock()
	r.resolved++
	if r.resolved == r.expected {
		close(r.allResolved)
	}
	r.mu.Unlock()
	select {
	case <-r.release:
		return principal, nil
	case <-ctx.Done():
		return security.Principal{}, ctx.Err()
	}
}

func (r *prefenceBarrierResolver) resolvedCount() int {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.resolved
}

func newPrefenceBarrierServer(t *testing.T, base *liveServer, resolver PrincipalResolver) *httptest.Server {
	t.Helper()
	guard := epochguard.Guard{Source: base.accountControl}
	handler := New(Config{
		Sessions: resolver,
		Upload: fenced.Upload{Guard: guard, Inner: &upload.Service{
			Transactions: base.executor,
			Repository:   pgrepo.Upload{},
			Signer:       base.objects,
			Objects:      base.objects,
			IDs:          cryptoids.Generator{},
		}},
		Preview: fenced.PreviewRead{Guard: guard, Inner: &previewread.Service{Transactions: base.executor}},
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

type deletionPrefenceResult struct {
	Status int
	Err    error
}

type deletionPrefenceResultsDocument struct {
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
		ScenarioID               string         `json:"scenarioId"`
		InFlightRequests         int            `json:"inFlightRequests"`
		AuthenticatedBeforeFence int            `json:"authenticatedBeforeFence"`
		DeletionRequestStatus    int            `json:"deletionRequestStatus"`
		DeletionEpoch            int64          `json:"deletionEpoch"`
		ReleasedAfterFence       int            `json:"releasedAfterFence"`
		UnauthorizedAfterFence   int            `json:"unauthorizedAfterFence"`
		UnexpectedStatusCount    int            `json:"unexpectedStatusCount"`
		TransportErrors          int            `json:"transportErrors"`
		WorkerReceiptCount       int            `json:"workerReceiptCount"`
		FinalOwnedRowCount       int            `json:"finalOwnedRowCount"`
		FinalAccountState        string         `json:"finalAccountState"`
		FinalAccountEpoch        int64          `json:"finalAccountEpoch"`
		Assertions               map[string]any `json:"assertions"`
		Result                   string         `json:"result"`
		IntegrityResult          string         `json:"integrityResult"`
	} `json:"scenario"`
	Limitations []string `json:"limitations"`
}

func TestAccountDeletionPrefenceInFlightLinearizationLocalDependencies(t *testing.T) {
	if os.Getenv("MEMORY_OS_RUN_PREFENCE_LINEARIZATION") != "1" {
		t.Skip("set MEMORY_OS_RUN_PREFENCE_LINEARIZATION=1 to run pre-fence deletion linearization")
	}

	base := newLiveServer(t)
	owner := fmt.Sprintf("acct_prefence_%d", time.Now().UnixNano())
	token := base.issueSession(t, owner)
	jobID := base.createJob(t, owner)
	base.commitPreviewForJob(t, owner, jobID)

	resolver := newPrefenceBarrierResolver(base.sessions, deletionPrefenceLinearizationRequests)
	barrierServer := newPrefenceBarrierServer(t, base, resolver)
	previewURL := barrierServer.URL + "/v1/import-jobs/" + jobID + "/preview"

	client := &http.Client{Timeout: 20 * time.Second}
	results := make(chan deletionPrefenceResult, deletionPrefenceLinearizationRequests)
	start := make(chan struct{})
	for index := 0; index < deletionPrefenceLinearizationRequests; index++ {
		go func() {
			<-start
			request, err := http.NewRequest(http.MethodGet, previewURL, nil)
			if err != nil {
				results <- deletionPrefenceResult{Err: err}
				return
			}
			request.Header.Set("Authorization", "Bearer "+token)
			response, err := client.Do(request)
			if err != nil {
				results <- deletionPrefenceResult{Err: err}
				return
			}
			_, copyErr := io.Copy(io.Discard, response.Body)
			closeErr := response.Body.Close()
			if copyErr != nil {
				results <- deletionPrefenceResult{Err: copyErr}
				return
			}
			if closeErr != nil {
				results <- deletionPrefenceResult{Err: closeErr}
				return
			}
			results <- deletionPrefenceResult{Status: response.StatusCode}
		}()
	}
	close(start)

	select {
	case <-resolver.allResolved:
	case <-time.After(15 * time.Second):
		t.Fatalf("only %d/%d sessions resolved before deletion fence", resolver.resolvedCount(), deletionPrefenceLinearizationRequests)
	}
	if resolver.resolvedCount() != deletionPrefenceLinearizationRequests {
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
	unauthorized := 0
	unexpected := 0
	transportErrors := 0
	for index := 0; index < deletionPrefenceLinearizationRequests; index++ {
		result := <-results
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
	if unauthorized != deletionPrefenceLinearizationRequests || unexpected != 0 || transportErrors != 0 {
		t.Fatalf("pre-fence authenticated requests escaped fence: unauthorized=%d unexpected=%d transport=%d", unauthorized, unexpected, transportErrors)
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

	resultPath := os.Getenv("MEMORY_OS_PREFENCE_LINEARIZATION_RESULTS_PATH")
	if resultPath == "" {
		return
	}
	commitSHA := os.Getenv("MEMORY_OS_COMMIT_SHA")
	if len(commitSHA) != 40 {
		t.Fatal("full MEMORY_OS_COMMIT_SHA is required when writing pre-fence linearization evidence")
	}

	document := deletionPrefenceResultsDocument{
		SchemaVersion: "memory-os-deletion-prefence-linearization-results.v1",
		CommitSHA:     commitSHA,
		GeneratedAt:   time.Now().UTC().Format(time.RFC3339),
		Limitations: []string{
			"Preview read is the in-flight surface exercised",
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
	document.Scenario.ScenarioID = "account-deletion-prefence-inflight-linearization-local-dependencies"
	document.Scenario.InFlightRequests = deletionPrefenceLinearizationRequests
	document.Scenario.AuthenticatedBeforeFence = resolver.resolvedCount()
	document.Scenario.DeletionRequestStatus = response.StatusCode
	document.Scenario.DeletionEpoch = deletion.DeletionEpoch
	document.Scenario.ReleasedAfterFence = deletionPrefenceLinearizationRequests
	document.Scenario.UnauthorizedAfterFence = unauthorized
	document.Scenario.UnexpectedStatusCount = unexpected
	document.Scenario.TransportErrors = transportErrors
	document.Scenario.WorkerReceiptCount = len(receipts)
	document.Scenario.FinalOwnedRowCount = finalOwnedRows
	document.Scenario.FinalAccountState = finalState
	document.Scenario.FinalAccountEpoch = finalEpoch
	document.Scenario.Assertions = map[string]any{
		"allAuthenticatedBeforeFence":       resolver.resolvedCount() == deletionPrefenceLinearizationRequests,
		"allReleasedAfterFenceUnauthorized": unauthorized == deletionPrefenceLinearizationRequests,
		"noUnexpectedStatuses":              unexpected == 0,
		"noTransportErrors":                 transportErrors == 0,
		"deletionWorkerCompleted":           len(receipts) == 1,
		"finalOwnedRowCount":                finalOwnedRows,
		"productionEvidence":                false,
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
