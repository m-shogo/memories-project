package httpserver

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"runtime"
	"testing"
	"time"
)

const capacityRampScenarioID = "authenticated-preview-capacity-ramp-local-postgres"

type capacityRampStep struct {
	Concurrency int             `json:"concurrency"`
	Batch       liveBatchResult `json:"batch"`
}

type capacityRampResultsDocument struct {
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
		ScenarioID               string             `json:"scenarioId"`
		WorkloadType             string             `json:"workloadType"`
		StartedAt                string             `json:"startedAt"`
		CompletedAt              string             `json:"completedAt"`
		RequestsPerStep          int                `json:"requestsPerStep"`
		Steps                    []capacityRampStep `json:"steps"`
		CandidateSafeConcurrency int                `json:"candidateSafeConcurrency"`
		FirstSaturationSignal    *int               `json:"firstSaturationSignal"`
		Decision                 string             `json:"decision"`
		Assertions               map[string]any     `json:"assertions"`
		Result                   string             `json:"result"`
		IntegrityResult          string             `json:"integrityResult"`
	} `json:"scenario"`
	Limitations []string `json:"limitations"`
}

func TestAuthenticatedPreviewCapacityRampLocalPostgres(t *testing.T) {
	if os.Getenv("MEMORY_OS_RUN_CAPACITY_RAMP") != "1" {
		t.Skip("set MEMORY_OS_RUN_CAPACITY_RAMP=1 to run the local capacity ramp")
	}

	server := newLiveServer(t)
	runID := time.Now().UnixNano()
	owner := fmt.Sprintf("acct_capacity_ramp_%d", runID)
	token := server.issueSession(t, owner)
	jobID := server.createJob(t, owner)
	previewID, _ := server.commitPreviewForJob(t, owner, jobID)
	previewPath := server.server.URL + "/v1/import-jobs/" + jobID + "/preview"

	concurrencySteps := []int{4, 8, 16, 24, 32, 48}
	const requestsPerStep = 240
	steps := make([]capacityRampStep, 0, len(concurrencySteps))
	startedAt := time.Now().UTC()
	candidateSafeConcurrency := 0
	var firstSaturationSignal *int
	all2xx := true
	allNo5xx := true
	allNoTransport := true

	for _, concurrency := range concurrencySteps {
		batch := runLiveHTTPBatch(requestsPerStep, concurrency, func(int) (*http.Request, error) {
			return liveRequest(http.MethodGet, previewPath, token, nil)
		})
		steps = append(steps, capacityRampStep{Concurrency: concurrency, Batch: batch})

		stepAll2xx := batch.StatusClassCounts["2xx"] == requestsPerStep && batch.Successes == requestsPerStep
		stepNo5xx := batch.StatusClassCounts["5xx"] == 0
		stepNoTransport := batch.StatusClassCounts["transport_error"] == 0
		all2xx = all2xx && stepAll2xx
		allNo5xx = allNo5xx && stepNo5xx
		allNoTransport = allNoTransport && stepNoTransport
		if stepAll2xx && stepNo5xx && stepNoTransport {
			candidateSafeConcurrency = concurrency
		} else if firstSaturationSignal == nil {
			value := concurrency
			firstSaturationSignal = &value
		}
	}

	counts := map[string]int{}
	queries := map[string]string{
		"previewReadyRowsAfterRamp":     `SELECT count(*) FROM memory_os.preview_ready WHERE id = $1`,
		"previewCandidateRowsAfterRamp": `SELECT count(*) FROM memory_os.preview_candidate WHERE preview_id = $1`,
		"previewRejectionRowsAfterRamp": `SELECT count(*) FROM memory_os.preview_rejection WHERE preview_id = $1`,
	}
	for name, query := range queries {
		var count int
		if err := server.pool.QueryRow(context.Background(), query, previewID).Scan(&count); err != nil {
			t.Fatal(err)
		}
		counts[name] = count
	}

	integrityPassed := counts["previewReadyRowsAfterRamp"] == 1 &&
		counts["previewCandidateRowsAfterRamp"] == 2 &&
		counts["previewRejectionRowsAfterRamp"] == 1
	if !integrityPassed {
		t.Fatalf("capacity ramp mutated Preview integrity rows: %+v", counts)
	}
	if !all2xx || !allNo5xx || !allNoTransport {
		t.Fatalf("capacity ramp crossed a failure boundary: steps=%+v", steps)
	}

	path := os.Getenv("MEMORY_OS_CAPACITY_RAMP_RESULTS_PATH")
	if path == "" {
		return
	}
	sourceCommit := os.Getenv("MEMORY_OS_COMMIT_SHA")
	if sourceCommit == "" {
		t.Fatal("MEMORY_OS_COMMIT_SHA is required when writing capacity ramp results")
	}

	document := capacityRampResultsDocument{
		SchemaVersion: "memory-os-capacity-ramp-results.v1",
		CommitSHA:     sourceCommit,
		GeneratedAt:   time.Now().UTC().Format(time.RFC3339),
		Limitations: []string{
			"single authenticated Preview read route only",
			"ephemeral GitHub-hosted runner and local PostgreSQL 16",
			"fixed request counts rather than sustained arrival rate",
			"no deliberate overload beyond the bounded concurrency steps",
			"not production capacity evidence",
		},
	}
	document.Environment.OS = runtime.GOOS
	document.Environment.Arch = runtime.GOARCH
	document.Environment.NumCPU = runtime.NumCPU()
	document.Environment.GoVersion = runtime.Version()
	document.Environment.DependencyMode = "LOCAL_POSTGRES"
	document.Environment.SyntheticDataOnly = true
	document.Environment.ProductionTraffic = false
	document.Environment.ProductionCredentials = false
	document.Environment.ProductionEvidence = false
	document.Environment.ProductionEquivalentDependencies = false
	document.Environment.ContainsSecrets = false
	document.Scenario.ScenarioID = capacityRampScenarioID
	document.Scenario.WorkloadType = "RAMP"
	document.Scenario.StartedAt = startedAt.Format(time.RFC3339)
	document.Scenario.CompletedAt = time.Now().UTC().Format(time.RFC3339)
	document.Scenario.RequestsPerStep = requestsPerStep
	document.Scenario.Steps = steps
	document.Scenario.CandidateSafeConcurrency = candidateSafeConcurrency
	document.Scenario.FirstSaturationSignal = firstSaturationSignal
	document.Scenario.Decision = "BOUNDARY_NOT_ESTABLISHED"
	document.Scenario.Assertions = map[string]any{
		"allStepsExecuted":                 len(steps) == len(concurrencySteps),
		"allStepsNo5xx":                    allNo5xx,
		"allStepsNoTransportErrors":        allNoTransport,
		"allStepsAll2xx":                   all2xx,
		"previewReadyRowsAfterRamp":        counts["previewReadyRowsAfterRamp"],
		"previewCandidateRowsAfterRamp":    counts["previewCandidateRowsAfterRamp"],
		"previewRejectionRowsAfterRamp":    counts["previewRejectionRowsAfterRamp"],
		"productionEvidence":               false,
		"productionEquivalentDependencies": false,
		"capacityBoundaryEstablished":      false,
		"operationalThresholdApproved":     false,
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
