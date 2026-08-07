package httpserver

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"net/url"
	"os"
	"runtime"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

const controlledSaturationScenarioID = "signed-upload-controlled-saturation-ramp-local-dependencies"

type controlledSaturationPoolSnapshot struct {
	MaxConns             int32   `json:"maxConns"`
	TotalConns           int32   `json:"totalConns"`
	AcquiredConns        int32   `json:"acquiredConns"`
	IdleConns            int32   `json:"idleConns"`
	EmptyAcquireCount    int64   `json:"emptyAcquireCount"`
	CanceledAcquireCount int64   `json:"canceledAcquireCount"`
	AcquireDurationMs    float64 `json:"acquireDurationMs"`
}

type controlledSaturationPoolDelta struct {
	EmptyAcquireCount    int64   `json:"emptyAcquireCount"`
	CanceledAcquireCount int64   `json:"canceledAcquireCount"`
	AcquireDurationMs    float64 `json:"acquireDurationMs"`
}

type controlledSaturationStep struct {
	Concurrency int                              `json:"concurrency"`
	Batch       liveBatchResult                  `json:"batch"`
	PoolBefore  controlledSaturationPoolSnapshot `json:"poolBefore"`
	PoolAfter   controlledSaturationPoolSnapshot `json:"poolAfter"`
	PoolDelta   controlledSaturationPoolDelta    `json:"poolDelta"`
}

type controlledSaturationResultsDocument struct {
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
		LoopbackDependenciesOnly         bool   `json:"loopbackDependenciesOnly"`
		ProductionTraffic                bool   `json:"productionTraffic"`
		ProductionCredentials            bool   `json:"productionCredentials"`
		ProductionEvidence               bool   `json:"productionEvidence"`
		ProductionEquivalentDependencies bool   `json:"productionEquivalentDependencies"`
		ContainsSecrets                  bool   `json:"containsSecrets"`
	} `json:"environment"`
	Scenario struct {
		ScenarioID                string                     `json:"scenarioId"`
		WorkloadType              string                     `json:"workloadType"`
		StartedAt                 string                     `json:"startedAt"`
		CompletedAt               string                     `json:"completedAt"`
		RequestsPerStep           int                        `json:"requestsPerStep"`
		Steps                     []controlledSaturationStep `json:"steps"`
		CandidateCleanConcurrency int                        `json:"candidateCleanConcurrency"`
		FirstSaturationSignal     *int                       `json:"firstSaturationSignal"`
		FirstPoolContentionSignal *int                       `json:"firstPoolContentionSignal"`
		Decision                  string                     `json:"decision"`
		RampSuccessfulLifecycles  int                        `json:"rampSuccessfulLifecycles"`
		PostRampRecoveryProbe     liveBatchResult            `json:"postRampRecoveryProbe"`
		FinalDatabaseAssertions   map[string]int             `json:"finalDatabaseAssertions"`
		Assertions                map[string]any             `json:"assertions"`
		Result                    string                     `json:"result"`
		IntegrityResult           string                     `json:"integrityResult"`
	} `json:"scenario"`
	Limitations []string `json:"limitations"`
}

func controlledSaturationLoopback(raw string) bool {
	parsed, err := url.Parse(raw)
	if err != nil {
		return false
	}
	host := parsed.Hostname()
	if host == "localhost" {
		return true
	}
	ip := net.ParseIP(host)
	return ip != nil && ip.IsLoopback()
}

func controlledSaturationSnapshot(pool *pgxpool.Pool) controlledSaturationPoolSnapshot {
	stats := pool.Stat()
	return controlledSaturationPoolSnapshot{
		MaxConns:             stats.MaxConns(),
		TotalConns:           stats.TotalConns(),
		AcquiredConns:        stats.AcquiredConns(),
		IdleConns:            stats.IdleConns(),
		EmptyAcquireCount:    stats.EmptyAcquireCount(),
		CanceledAcquireCount: stats.CanceledAcquireCount(),
		AcquireDurationMs:    float64(stats.AcquireDuration()) / float64(time.Millisecond),
	}
}

func calculateControlledSaturationPoolDelta(before, after controlledSaturationPoolSnapshot) controlledSaturationPoolDelta {
	return controlledSaturationPoolDelta{
		EmptyAcquireCount:    after.EmptyAcquireCount - before.EmptyAcquireCount,
		CanceledAcquireCount: after.CanceledAcquireCount - before.CanceledAcquireCount,
		AcquireDurationMs:    after.AcquireDurationMs - before.AcquireDurationMs,
	}
}

func controlledSaturationOwnerCounts(t *testing.T, server *liveServer, owner string) map[string]int {
	t.Helper()
	ctx := context.Background()
	counts := map[string]int{}
	var consumed int
	if err := server.pool.QueryRow(ctx,
		`SELECT count(*) FROM memory_os.upload_authorization
		 WHERE owner_account_id = $1 AND state = 'consumed'`, owner,
	).Scan(&consumed); err != nil {
		t.Fatal(err)
	}
	counts["consumedAuthorizations"] = consumed
	var scanPending, distinctVersions, distinctKeys int
	if err := server.pool.QueryRow(ctx,
		`SELECT count(*),
		        count(DISTINCT safe_metadata->>'objectVersionId'),
		        count(DISTINCT safe_metadata->>'objectKey')
		 FROM memory_os.quarantine_object
		 WHERE owner_account_id = $1 AND state = 'scan_pending'`, owner,
	).Scan(&scanPending, &distinctVersions, &distinctKeys); err != nil {
		t.Fatal(err)
	}
	counts["scanPendingQuarantineRows"] = scanPending
	counts["distinctObjectVersionIds"] = distinctVersions
	counts["distinctObjectKeys"] = distinctKeys
	return counts
}

func requireControlledSaturationAccounting(t *testing.T, counts map[string]int, expected int) {
	t.Helper()
	for _, key := range []string{
		"consumedAuthorizations",
		"scanPendingQuarantineRows",
		"distinctObjectVersionIds",
		"distinctObjectKeys",
	} {
		if counts[key] != expected {
			t.Fatalf("controlled saturation accounting mismatch: %s=%d expected=%d all=%+v", key, counts[key], expected, counts)
		}
	}
}

func TestControlledSignedUploadSaturationRampLocalDependencies(t *testing.T) {
	if os.Getenv("MEMORY_OS_RUN_CONTROLLED_SATURATION_RAMP") != "1" {
		t.Skip("set MEMORY_OS_RUN_CONTROLLED_SATURATION_RAMP=1 to run the bounded local dependency ramp")
	}
	databaseURL := os.Getenv("MEMORY_OS_TEST_DATABASE_URL")
	objectEndpoint := os.Getenv("MEMORY_OS_TEST_S3_ENDPOINT")
	if !controlledSaturationLoopback(databaseURL) || !controlledSaturationLoopback(objectEndpoint) {
		t.Fatal("refusing controlled saturation ramp against non-loopback dependencies")
	}

	server := newLiveServer(t)
	runID := time.Now().UnixNano()
	owner := fmt.Sprintf("acct_controlled_saturation_%d", runID)
	token := server.issueSession(t, owner)

	concurrencySteps := []int{4, 8, 16, 24, 32, 48}
	const requestsPerStep = 64
	steps := make([]controlledSaturationStep, 0, len(concurrencySteps))
	startedAt := time.Now().UTC()
	candidateCleanConcurrency := 0
	var firstSaturationSignal *int
	var firstPoolContentionSignal *int
	rampSuccesses := 0

	for stepIndex, concurrency := range concurrencySteps {
		jobIDs := make([]string, requestsPerStep)
		for index := range jobIDs {
			jobIDs[index] = server.createJob(t, owner)
		}
		before := controlledSaturationSnapshot(server.appPool)
		batch := runLiveObjectBatch(requestsPerStep, concurrency, server.server.URL, token, jobIDs)
		after := controlledSaturationSnapshot(server.appPool)
		delta := calculateControlledSaturationPoolDelta(before, after)
		steps = append(steps, controlledSaturationStep{
			Concurrency: concurrency,
			Batch:       batch,
			PoolBefore:  before,
			PoolAfter:   after,
			PoolDelta:   delta,
		})

		if batch.StatusClassCounts["3xx"] != 0 || batch.StatusClassCounts["4xx"] != 0 {
			t.Fatalf("controlled saturation produced an authorization/request-class failure at step %d: %+v", stepIndex, batch)
		}
		rampSuccesses += batch.Successes
		counts := controlledSaturationOwnerCounts(t, server, owner)
		requireControlledSaturationAccounting(t, counts, rampSuccesses)

		clean := batch.Successes == requestsPerStep && batch.Failures == 0 &&
			batch.StatusClassCounts["2xx"] == requestsPerStep &&
			batch.StatusClassCounts["5xx"] == 0 &&
			batch.StatusClassCounts["transport_error"] == 0
		if clean {
			candidateCleanConcurrency = concurrency
		} else if firstSaturationSignal == nil {
			value := concurrency
			firstSaturationSignal = &value
		}
		if delta.EmptyAcquireCount > 0 && firstPoolContentionSignal == nil {
			value := concurrency
			firstPoolContentionSignal = &value
		}
	}

	// A bounded overload experiment must leave the service able to accept new
	// work immediately afterward. This is a recovery probe, not evidence that a
	// failed lifecycle itself is automatically safe to retry.
	recoveryJob := server.createJob(t, owner)
	recovery := runLiveObjectBatch(1, 1, server.server.URL, token, []string{recoveryJob})
	if recovery.Successes != 1 || recovery.Failures != 0 || recovery.StatusClassCounts["2xx"] != 1 {
		t.Fatalf("post-ramp recovery probe failed: %+v", recovery)
	}
	finalCounts := controlledSaturationOwnerCounts(t, server, owner)
	requireControlledSaturationAccounting(t, finalCounts, rampSuccesses+1)

	path := os.Getenv("MEMORY_OS_CONTROLLED_SATURATION_RESULTS_PATH")
	if path == "" {
		return
	}
	sourceCommit := os.Getenv("MEMORY_OS_COMMIT_SHA")
	if len(sourceCommit) != 40 {
		t.Fatal("MEMORY_OS_COMMIT_SHA must be a full commit SHA when writing controlled saturation results")
	}

	decision := "BOUNDARY_NOT_ESTABLISHED"
	if firstSaturationSignal != nil {
		decision = "LOCAL_SATURATION_SIGNAL_REQUIRES_REPEATABILITY_REVIEW"
	}
	document := controlledSaturationResultsDocument{
		SchemaVersion: "memory-os-controlled-saturation-ramp-results.v1",
		CommitSHA:     sourceCommit,
		GeneratedAt:   time.Now().UTC().Format(time.RFC3339),
		Limitations: []string{
			"ephemeral GitHub-hosted runner with loopback PostgreSQL 16 and MinIO",
			"single synthetic account and one API process",
			"bounded batches rather than sustained arrival rate",
			"pool contention is not by itself a capacity boundary",
			"one run cannot establish repeatability or an operating threshold",
			"not production or production-equivalent capacity evidence",
		},
	}
	document.Environment.OS = runtime.GOOS
	document.Environment.Arch = runtime.GOARCH
	document.Environment.NumCPU = runtime.NumCPU()
	document.Environment.GoVersion = runtime.Version()
	document.Environment.DependencyMode = "LOCAL_POSTGRES_MINIO"
	document.Environment.SyntheticDataOnly = true
	document.Environment.LoopbackDependenciesOnly = true
	document.Environment.ProductionTraffic = false
	document.Environment.ProductionCredentials = false
	document.Environment.ProductionEvidence = false
	document.Environment.ProductionEquivalentDependencies = false
	document.Environment.ContainsSecrets = false
	document.Scenario.ScenarioID = controlledSaturationScenarioID
	document.Scenario.WorkloadType = "CONTROLLED_RAMP"
	document.Scenario.StartedAt = startedAt.Format(time.RFC3339)
	document.Scenario.CompletedAt = time.Now().UTC().Format(time.RFC3339)
	document.Scenario.RequestsPerStep = requestsPerStep
	document.Scenario.Steps = steps
	document.Scenario.CandidateCleanConcurrency = candidateCleanConcurrency
	document.Scenario.FirstSaturationSignal = firstSaturationSignal
	document.Scenario.FirstPoolContentionSignal = firstPoolContentionSignal
	document.Scenario.Decision = decision
	document.Scenario.RampSuccessfulLifecycles = rampSuccesses
	document.Scenario.PostRampRecoveryProbe = recovery
	document.Scenario.FinalDatabaseAssertions = finalCounts
	document.Scenario.Assertions = map[string]any{
		"allStepsExecuted":                 len(steps) == len(concurrencySteps),
		"boundedMaximumConcurrency":        48,
		"boundedRequestsPerStep":           requestsPerStep,
		"postRampRecoveryProbePassed":      true,
		"productionEvidence":               false,
		"productionEquivalentDependencies": false,
		"capacityBoundaryEstablished":      false,
		"operationalThresholdApproved":     false,
		"repeatabilityEstablished":         false,
		"independentReviewCompleted":       false,
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
