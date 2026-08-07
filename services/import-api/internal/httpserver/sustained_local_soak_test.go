package httpserver

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strconv"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/accountdelete"
)

const sustainedLocalSoakScenarioID = "mixed-import-lifecycle-local-long-soak"

const (
	sustainedLocalSoakWindows           = 12
	sustainedPreviewRequestsPerWindow   = 64
	sustainedPreviewConcurrency         = 8
	sustainedUploadLifecyclesPerWindow  = 8
	sustainedUploadConcurrency          = 4
	sustainedDeletionCycleEveryWindows  = 3
	sustainedMaximumScanQueuePending    = 128
	sustainedMinimumEvidenceDurationSec = 3600
	sustainedMaximumRunDurationSec      = 5400
)

type sustainedSoakObservation struct {
	Window                        int                       `json:"window"`
	ObservedAt                    string                    `json:"observedAt"`
	ElapsedSeconds                float64                   `json:"elapsedSeconds"`
	RequestsBySurface             map[string]int            `json:"requestsBySurface"`
	SuccessesBySurface            map[string]int            `json:"successesBySurface"`
	FailuresBySurface             map[string]int            `json:"failuresBySurface"`
	StatusClassCountsBySurface    map[string]map[string]int `json:"statusClassCountsBySurface"`
	LatencyP50MsBySurface         map[string]float64        `json:"latencyP50MsBySurface"`
	LatencyP95MsBySurface         map[string]float64        `json:"latencyP95MsBySurface"`
	LatencyP99MsBySurface         map[string]float64        `json:"latencyP99MsBySurface"`
	HeapAllocBytes                uint64                    `json:"heapAllocBytes"`
	HeapInuseBytes                uint64                    `json:"heapInuseBytes"`
	RSSBytes                      int64                     `json:"rssBytes"`
	Goroutines                    int                       `json:"goroutines"`
	DBPoolMaxConns                int32                     `json:"dbPoolMaxConns"`
	DBPoolTotalConns              int32                     `json:"dbPoolTotalConns"`
	DBPoolAcquiredConns           int32                     `json:"dbPoolAcquiredConns"`
	DBPoolIdleConns               int32                     `json:"dbPoolIdleConns"`
	DBPoolEmptyAcquireCount       int64                     `json:"dbPoolEmptyAcquireCount"`
	DBPoolCanceledAcquireCount    int64                     `json:"dbPoolCanceledAcquireCount"`
	DBPoolAcquireDurationMs       float64                   `json:"dbPoolAcquireDurationMs"`
	ScanQueuePending              int                       `json:"scanQueuePending"`
	ScanQueueOldestPendingSeconds float64                   `json:"scanQueueOldestPendingSeconds"`
	DeletionPending               int                       `json:"deletionPending"`
	DeletionStuck                 int                       `json:"deletionStuck"`
	MinIOLifecycleSuccesses       int                       `json:"minioLifecycleSuccesses"`
	ParserRuns                    int                       `json:"parserRuns"`
	ParserFailures                int                       `json:"parserFailures"`
}

type sustainedSoakResultsDocument struct {
	SchemaVersion string `json:"schemaVersion"`
	CommitSHA     string `json:"commitSha"`
	RunID         string `json:"runId"`
	GeneratedAt   string `json:"generatedAt"`
	Environment   struct {
		OS                               string `json:"os"`
		Arch                             string `json:"arch"`
		NumCPU                           int    `json:"numCpu"`
		GoVersion                        string `json:"goVersion"`
		DependencyMode                   string `json:"dependencyMode"`
		Classification                   string `json:"classification"`
		SyntheticDataOnly                bool   `json:"syntheticDataOnly"`
		LoopbackDependenciesOnly         bool   `json:"loopbackDependenciesOnly"`
		ProductionTraffic                bool   `json:"productionTraffic"`
		ProductionCredentials            bool   `json:"productionCredentials"`
		ProductionEvidence               bool   `json:"productionEvidence"`
		ProductionEquivalentDependencies bool   `json:"productionEquivalentDependencies"`
		ContainsSecrets                  bool   `json:"containsSecrets"`
	} `json:"environment"`
	Scenario struct {
		ScenarioID      string                     `json:"scenarioId"`
		StartedAt       string                     `json:"startedAt"`
		CompletedAt     string                     `json:"completedAt"`
		DurationSeconds float64                    `json:"durationSeconds"`
		WindowCount     int                        `json:"windowCount"`
		Coverage        map[string]bool            `json:"coverage"`
		Observations    []sustainedSoakObservation `json:"observations"`
		Trends          map[string]any             `json:"trends"`
		Assertions      map[string]any             `json:"assertions"`
		Result          string                     `json:"result"`
		IntegrityResult string                     `json:"integrityResult"`
	} `json:"scenario"`
	Limitations []string `json:"limitations"`
}

type sustainedDeletionCycleResult struct {
	Duration time.Duration
}

func sustainedSoakConfiguredDuration(t *testing.T) time.Duration {
	t.Helper()
	raw := os.Getenv("MEMORY_OS_SOAK_DURATION_SECONDS")
	if raw == "" {
		return sustainedMinimumEvidenceDurationSec * time.Second
	}
	seconds, err := strconv.Atoi(raw)
	if err != nil || seconds <= 0 || seconds > sustainedMaximumRunDurationSec {
		t.Fatalf("MEMORY_OS_SOAK_DURATION_SECONDS must be in [1,%d]", sustainedMaximumRunDurationSec)
	}
	return time.Duration(seconds) * time.Second
}

func sustainedSoakParserRecovery(ctx context.Context) (time.Duration, error) {
	cwd, err := os.Getwd()
	if err != nil {
		return 0, err
	}
	moduleRoot := filepath.Clean(filepath.Join(cwd, "../.."))
	if _, err := os.Stat(filepath.Join(moduleRoot, "go.mod")); err != nil {
		return 0, fmt.Errorf("locate import-api module root: %w", err)
	}
	started := time.Now()
	command := exec.CommandContext(ctx,
		"go", "test", "./internal/parsersup",
		"-run", "^TestSupervisorRestartsSameSpoolAfterFailedAttempt$",
		"-count=1",
	)
	command.Dir = moduleRoot
	output, err := command.CombinedOutput()
	duration := time.Since(started)
	if err != nil {
		return duration, fmt.Errorf("parser recovery drill failed: %w: %s", err, string(output))
	}
	return duration, nil
}

func sustainedSoakQueueStats(t *testing.T, server *liveServer, owner string) (int, float64) {
	t.Helper()
	var pending int
	var oldest float64
	if err := server.pool.QueryRow(context.Background(),
		`SELECT count(*),
		        COALESCE(EXTRACT(EPOCH FROM (now() - min(created_at))), 0)::double precision
		 FROM memory_os.quarantine_object
		 WHERE owner_account_id = $1 AND state = 'scan_pending'`, owner,
	).Scan(&pending, &oldest); err != nil {
		t.Fatalf("read soak scan queue stats: %v", err)
	}
	return pending, oldest
}

func sustainedSoakDeletionBacklog(t *testing.T, server *liveServer) (int, int) {
	t.Helper()
	backlog, err := server.accountControl.Backlog(context.Background(), 3)
	if err != nil {
		t.Fatalf("read soak deletion backlog: %v", err)
	}
	return backlog.Pending, backlog.Stuck
}

func sustainedSoakDeletionCycle(t *testing.T, server *liveServer, window int) sustainedDeletionCycleResult {
	t.Helper()
	started := time.Now()
	owner := fmt.Sprintf("acct_soak_delete_%d_%d", time.Now().UnixNano(), window)
	token := server.issueSession(t, owner)
	jobID := server.createJob(t, owner)
	server.commitPreviewForJob(t, owner, jobID)
	previewPath := server.server.URL + "/v1/import-jobs/" + jobID + "/preview"

	response, body := server.request(t, http.MethodDelete, "/v1/account", token, nil)
	if response.StatusCode != http.StatusAccepted {
		t.Fatalf("soak deletion fence status %d: %s", response.StatusCode, body)
	}
	var fence struct {
		Status        string `json:"status"`
		DeletionEpoch int64  `json:"deletionEpoch"`
	}
	if err := json.Unmarshal(body, &fence); err != nil {
		t.Fatalf("decode soak deletion receipt: %v", err)
	}
	if fence.Status != "deleting" || fence.DeletionEpoch != 2 {
		t.Fatalf("unexpected soak deletion fence: %s", body)
	}

	receipts, err := (accountdelete.Worker{
		Queue:      server.accountControl,
		Repository: server.accountControl,
		Objects:    server.objects,
	}).Sweep(context.Background(), 1)
	if err != nil {
		t.Fatalf("soak deletion worker failed: %v", err)
	}
	if len(receipts) != 1 || receipts[0].AccountID != owner {
		t.Fatalf("unexpected soak deletion receipt count=%d", len(receipts))
	}

	postFence := runDeletionExactHTTPBatch(1, 1, func(int) (*http.Request, error) {
		return liveRequest(http.MethodGet, previewPath, token, nil)
	})
	if postFence.StatusCodeCounts["401"] != 1 || postFence.Summary.StatusClassCounts["5xx"] != 0 || postFence.Summary.StatusClassCounts["transport_error"] != 0 {
		t.Fatalf("former soak session did not remain fenced: %+v", postFence)
	}

	var state string
	var epoch int64
	if err := server.pool.QueryRow(context.Background(),
		"SELECT state, account_epoch FROM memory_os.account_control WHERE account_id = $1", owner,
	).Scan(&state, &epoch); err != nil {
		t.Fatalf("read soak deleted account control: %v", err)
	}
	if state != "deleted" || epoch != 2 {
		t.Fatalf("soak deletion tombstone drift: state=%s epoch=%d", state, epoch)
	}
	return sustainedDeletionCycleResult{Duration: time.Since(started)}
}

func sustainedSoakSlope(observations []sustainedSoakObservation, value func(sustainedSoakObservation) float64) float64 {
	if len(observations) < 2 {
		return 0
	}
	var sumX, sumY, sumXY, sumXX float64
	for _, observation := range observations {
		x := observation.ElapsedSeconds / 60
		y := value(observation)
		sumX += x
		sumY += y
		sumXY += x * y
		sumXX += x * x
	}
	n := float64(len(observations))
	denominator := n*sumXX - sumX*sumX
	if denominator == 0 {
		return 0
	}
	return (n*sumXY - sumX*sumY) / denominator
}

func sustainedSoakSurfaceSlope(observations []sustainedSoakObservation, surface string, source func(sustainedSoakObservation) map[string]float64) float64 {
	return sustainedSoakSlope(observations, func(observation sustainedSoakObservation) float64 {
		return source(observation)[surface]
	})
}

func sustainedSoakErrorRateSlope(observations []sustainedSoakObservation, surface string) float64 {
	return sustainedSoakSlope(observations, func(observation sustainedSoakObservation) float64 {
		requests := observation.RequestsBySurface[surface]
		if requests == 0 {
			return 0
		}
		return float64(observation.FailuresBySurface[surface]) / float64(requests)
	})
}

func TestMixedImportLifecycleLocalLongSoak(t *testing.T) {
	if os.Getenv("MEMORY_OS_RUN_SUSTAINED_LOCAL_SOAK") != "1" {
		t.Skip("set MEMORY_OS_RUN_SUSTAINED_LOCAL_SOAK=1 to run the local long soak")
	}
	databaseURL := os.Getenv("MEMORY_OS_TEST_DATABASE_URL")
	objectEndpoint := os.Getenv("MEMORY_OS_TEST_S3_ENDPOINT")
	if !controlledSaturationLoopback(databaseURL) || !controlledSaturationLoopback(objectEndpoint) {
		t.Fatal("refusing local long soak against non-loopback dependencies")
	}

	configuredDuration := sustainedSoakConfiguredDuration(t)
	resultPath := os.Getenv("MEMORY_OS_SUSTAINED_LOCAL_SOAK_RESULTS_PATH")
	if resultPath != "" && configuredDuration < sustainedMinimumEvidenceDurationSec*time.Second {
		t.Fatal("refusing to write long-soak evidence for a run configured below 3600 seconds")
	}

	server := newLiveServer(t)
	owner := fmt.Sprintf("acct_soak_active_%d", time.Now().UnixNano())
	token := server.issueSession(t, owner)
	previewJobID := server.createJob(t, owner)
	server.commitPreviewForJob(t, owner, previewJobID)
	previewPath := server.server.URL + "/v1/import-jobs/" + previewJobID + "/preview"

	startedAt := time.Now().UTC()
	started := time.Now()
	windowSpacing := configuredDuration / sustainedLocalSoakWindows
	observations := make([]sustainedSoakObservation, 0, sustainedLocalSoakWindows)
	deletionCycles := 0
	totalPreviewSuccesses := 0
	totalUploadSuccesses := 0
	totalParserRuns := 0
	totalParserFailures := 0

	for window := 1; window <= sustainedLocalSoakWindows; window++ {
		previewBatch := runLiveHTTPBatch(sustainedPreviewRequestsPerWindow, sustainedPreviewConcurrency, func(int) (*http.Request, error) {
			return liveRequest(http.MethodGet, previewPath, token, nil)
		})
		if previewBatch.Successes != sustainedPreviewRequestsPerWindow || previewBatch.Failures != 0 ||
			previewBatch.StatusClassCounts["2xx"] != sustainedPreviewRequestsPerWindow ||
			previewBatch.StatusClassCounts["5xx"] != 0 || previewBatch.StatusClassCounts["transport_error"] != 0 {
			t.Fatalf("soak preview window %d crossed success boundary: %+v", window, previewBatch)
		}
		totalPreviewSuccesses += previewBatch.Successes

		uploadJobs := make([]string, sustainedUploadLifecyclesPerWindow)
		for index := range uploadJobs {
			uploadJobs[index] = server.createJob(t, owner)
		}
		uploadBatch := runLiveObjectBatch(sustainedUploadLifecyclesPerWindow, sustainedUploadConcurrency, server.server.URL, token, uploadJobs)
		if uploadBatch.Successes != sustainedUploadLifecyclesPerWindow || uploadBatch.Failures != 0 ||
			uploadBatch.StatusClassCounts["2xx"] != sustainedUploadLifecyclesPerWindow ||
			uploadBatch.StatusClassCounts["3xx"] != 0 || uploadBatch.StatusClassCounts["4xx"] != 0 ||
			uploadBatch.StatusClassCounts["5xx"] != 0 || uploadBatch.StatusClassCounts["transport_error"] != 0 {
			t.Fatalf("soak signed-upload window %d crossed success boundary: %+v", window, uploadBatch)
		}
		totalUploadSuccesses += uploadBatch.Successes

		parserDuration, parserErr := sustainedSoakParserRecovery(context.Background())
		totalParserRuns++
		parserFailures := 0
		if parserErr != nil {
			totalParserFailures++
			parserFailures = 1
			t.Fatalf("soak parser recovery window %d failed: %v", window, parserErr)
		}

		deletionRequests := 0
		deletionSuccesses := 0
		deletionFailures := 0
		deletionDuration := time.Duration(0)
		if window%sustainedDeletionCycleEveryWindows == 0 {
			deletionRequests = 1
			cycle := sustainedSoakDeletionCycle(t, server, window)
			deletionDuration = cycle.Duration
			deletionSuccesses = 1
			deletionCycles++
		}

		target := started.Add(time.Duration(window) * windowSpacing)
		if sleep := time.Until(target); sleep > 0 {
			time.Sleep(sleep)
		}

		memory, rss, goroutines, err := shortStabilityMemObservation()
		if err != nil {
			t.Fatalf("soak window %d RSS observation unavailable: %v", window, err)
		}
		pool := controlledSaturationSnapshot(server.appPool)
		queuePending, queueOldest := sustainedSoakQueueStats(t, server, owner)
		if queuePending > sustainedMaximumScanQueuePending {
			t.Fatalf("soak scan queue exceeded bound: pending=%d max=%d", queuePending, sustainedMaximumScanQueuePending)
		}
		deletionPending, deletionStuck := sustainedSoakDeletionBacklog(t, server)
		if deletionPending != 0 || deletionStuck != 0 {
			t.Fatalf("soak deletion backlog did not converge after window %d: pending=%d stuck=%d", window, deletionPending, deletionStuck)
		}

		observations = append(observations, sustainedSoakObservation{
			Window:         window,
			ObservedAt:     time.Now().UTC().Format(time.RFC3339),
			ElapsedSeconds: time.Since(started).Seconds(),
			RequestsBySurface: map[string]int{
				"previewRead":           sustainedPreviewRequestsPerWindow,
				"signedUploadLifecycle": sustainedUploadLifecyclesPerWindow,
				"parserSupervisor":      1,
				"deletionWorker":        deletionRequests,
			},
			SuccessesBySurface: map[string]int{
				"previewRead":           previewBatch.Successes,
				"signedUploadLifecycle": uploadBatch.Successes,
				"parserSupervisor":      1 - parserFailures,
				"deletionWorker":        deletionSuccesses,
			},
			FailuresBySurface: map[string]int{
				"previewRead":           previewBatch.Failures,
				"signedUploadLifecycle": uploadBatch.Failures,
				"parserSupervisor":      parserFailures,
				"deletionWorker":        deletionFailures,
			},
			StatusClassCountsBySurface: map[string]map[string]int{
				"previewRead":           previewBatch.StatusClassCounts,
				"signedUploadLifecycle": uploadBatch.StatusClassCounts,
				"parserSupervisor":      {"pass": 1 - parserFailures, "fail": parserFailures},
				"deletionWorker":        {"pass": deletionSuccesses, "fail": deletionFailures},
			},
			LatencyP50MsBySurface: map[string]float64{
				"previewRead":           previewBatch.LatencyP50Ms,
				"signedUploadLifecycle": uploadBatch.LatencyP50Ms,
				"parserSupervisor":      float64(parserDuration) / float64(time.Millisecond),
				"deletionWorker":        float64(deletionDuration) / float64(time.Millisecond),
			},
			LatencyP95MsBySurface: map[string]float64{
				"previewRead":           previewBatch.LatencyP95Ms,
				"signedUploadLifecycle": uploadBatch.LatencyP95Ms,
				"parserSupervisor":      float64(parserDuration) / float64(time.Millisecond),
				"deletionWorker":        float64(deletionDuration) / float64(time.Millisecond),
			},
			LatencyP99MsBySurface: map[string]float64{
				"previewRead":           previewBatch.LatencyP99Ms,
				"signedUploadLifecycle": uploadBatch.LatencyP99Ms,
				"parserSupervisor":      float64(parserDuration) / float64(time.Millisecond),
				"deletionWorker":        float64(deletionDuration) / float64(time.Millisecond),
			},
			HeapAllocBytes:                memory.HeapAlloc,
			HeapInuseBytes:                memory.HeapInuse,
			RSSBytes:                      rss,
			Goroutines:                    goroutines,
			DBPoolMaxConns:                pool.MaxConns,
			DBPoolTotalConns:              pool.TotalConns,
			DBPoolAcquiredConns:           pool.AcquiredConns,
			DBPoolIdleConns:               pool.IdleConns,
			DBPoolEmptyAcquireCount:       pool.EmptyAcquireCount,
			DBPoolCanceledAcquireCount:    pool.CanceledAcquireCount,
			DBPoolAcquireDurationMs:       pool.AcquireDurationMs,
			ScanQueuePending:              queuePending,
			ScanQueueOldestPendingSeconds: queueOldest,
			DeletionPending:               deletionPending,
			DeletionStuck:                 deletionStuck,
			MinIOLifecycleSuccesses:       uploadBatch.Successes,
			ParserRuns:                    1,
			ParserFailures:                parserFailures,
		})
	}

	actualDuration := time.Since(started)
	if configuredDuration >= sustainedMinimumEvidenceDurationSec*time.Second && actualDuration < sustainedMinimumEvidenceDurationSec*time.Second {
		t.Fatalf("long-soak evidence duration too short: %s", actualDuration)
	}

	// Recovery proves the same long-lived server and parser boundary still
	// accept new work after the final observation window.
	recoveryPreview := runLiveHTTPBatch(1, 1, func(int) (*http.Request, error) {
		return liveRequest(http.MethodGet, previewPath, token, nil)
	})
	recoveryJob := server.createJob(t, owner)
	recoveryUpload := runLiveObjectBatch(1, 1, server.server.URL, token, []string{recoveryJob})
	_, recoveryParserErr := sustainedSoakParserRecovery(context.Background())
	recoveryPassed := recoveryPreview.Successes == 1 && recoveryPreview.Failures == 0 &&
		recoveryUpload.Successes == 1 && recoveryUpload.Failures == 0 && recoveryParserErr == nil
	if !recoveryPassed {
		t.Fatalf("long-soak recovery probe failed: preview=%+v upload=%+v parser=%v", recoveryPreview, recoveryUpload, recoveryParserErr)
	}

	finalQueuePending, _ := sustainedSoakQueueStats(t, server, owner)
	if finalQueuePending > sustainedMaximumScanQueuePending {
		t.Fatalf("recovery probe exceeded scan queue bound: %d", finalQueuePending)
	}
	finalDeletionPending, finalDeletionStuck := sustainedSoakDeletionBacklog(t, server)
	if finalDeletionPending != 0 || finalDeletionStuck != 0 {
		t.Fatalf("deletion backlog non-zero after recovery: pending=%d stuck=%d", finalDeletionPending, finalDeletionStuck)
	}

	if resultPath == "" {
		return
	}
	commitSHA := os.Getenv("MEMORY_OS_COMMIT_SHA")
	runID := os.Getenv("MEMORY_OS_SOAK_RUN_ID")
	if len(commitSHA) != 40 || runID == "" {
		t.Fatal("full MEMORY_OS_COMMIT_SHA and MEMORY_OS_SOAK_RUN_ID are required when writing long-soak evidence")
	}

	surfaces := []string{"previewRead", "signedUploadLifecycle", "parserSupervisor", "deletionWorker"}
	latencyTrend := map[string]map[string]float64{}
	errorTrend := map[string]float64{}
	for _, surface := range surfaces {
		latencyTrend[surface] = map[string]float64{
			"p95MsPerMinute": sustainedSoakSurfaceSlope(observations, surface, func(o sustainedSoakObservation) map[string]float64 { return o.LatencyP95MsBySurface }),
			"p99MsPerMinute": sustainedSoakSurfaceSlope(observations, surface, func(o sustainedSoakObservation) map[string]float64 { return o.LatencyP99MsBySurface }),
		}
		errorTrend[surface] = sustainedSoakErrorRateSlope(observations, surface)
	}
	trends := map[string]any{
		"rssSlopeBytesPerMinute":       sustainedSoakSlope(observations, func(o sustainedSoakObservation) float64 { return float64(o.RSSBytes) }),
		"heapAllocSlopeBytesPerMinute": sustainedSoakSlope(observations, func(o sustainedSoakObservation) float64 { return float64(o.HeapAllocBytes) }),
		"heapInuseSlopeBytesPerMinute": sustainedSoakSlope(observations, func(o sustainedSoakObservation) float64 { return float64(o.HeapInuseBytes) }),
		"goroutineSlopePerMinute":      sustainedSoakSlope(observations, func(o sustainedSoakObservation) float64 { return float64(o.Goroutines) }),
		"latencyTrendBySurface":        latencyTrend,
		"errorRateTrendBySurface":      errorTrend,
		"dbConnectionTrend": map[string]float64{
			"totalConnsPerMinute":        sustainedSoakSlope(observations, func(o sustainedSoakObservation) float64 { return float64(o.DBPoolTotalConns) }),
			"acquiredConnsPerMinute":     sustainedSoakSlope(observations, func(o sustainedSoakObservation) float64 { return float64(o.DBPoolAcquiredConns) }),
			"emptyAcquireCountPerMinute": sustainedSoakSlope(observations, func(o sustainedSoakObservation) float64 { return float64(o.DBPoolEmptyAcquireCount) }),
			"acquireDurationMsPerMinute": sustainedSoakSlope(observations, func(o sustainedSoakObservation) float64 { return o.DBPoolAcquireDurationMs }),
		},
		"scanQueueTrend": map[string]float64{
			"pendingPerMinute":              sustainedSoakSlope(observations, func(o sustainedSoakObservation) float64 { return float64(o.ScanQueuePending) }),
			"oldestPendingSecondsPerMinute": sustainedSoakSlope(observations, func(o sustainedSoakObservation) float64 { return o.ScanQueueOldestPendingSeconds }),
		},
		"deletionBacklogTrend": map[string]float64{
			"pendingPerMinute": sustainedSoakSlope(observations, func(o sustainedSoakObservation) float64 { return float64(o.DeletionPending) }),
			"stuckPerMinute":   sustainedSoakSlope(observations, func(o sustainedSoakObservation) float64 { return float64(o.DeletionStuck) }),
		},
	}

	coverage := map[string]bool{
		"authenticatedPreviewRead": totalPreviewSuccesses == sustainedLocalSoakWindows*sustainedPreviewRequestsPerWindow,
		"signedUploadLifecycle":    totalUploadSuccesses == sustainedLocalSoakWindows*sustainedUploadLifecyclesPerWindow,
		"parserSupervisor":         totalParserRuns == sustainedLocalSoakWindows && totalParserFailures == 0,
		"scanQueue":                finalQueuePending > 0 && finalQueuePending <= sustainedMaximumScanQueuePending,
		"deletionWorker":           deletionCycles == sustainedLocalSoakWindows/sustainedDeletionCycleEveryWindows,
		"postgresql":               true,
		"minio":                    true,
	}
	allCoverage := true
	for _, covered := range coverage {
		allCoverage = allCoverage && covered
	}
	if !allCoverage {
		t.Fatalf("long-soak coverage incomplete: %+v", coverage)
	}

	document := sustainedSoakResultsDocument{
		SchemaVersion: "memory-os-sustained-local-soak-results.v1",
		CommitSHA:     commitSHA,
		RunID:         runID,
		GeneratedAt:   time.Now().UTC().Format(time.RFC3339),
		Limitations: []string{
			"local PostgreSQL 16 and MinIO on one GitHub-hosted runner",
			"parser recovery runs in a bounded Linux child test while API RSS/heap measure the long-lived HTTP test process",
			"scan queue is observed but intentionally not drained by a production scan-worker topology",
			"one account drives Preview/upload workload; separate synthetic accounts exercise deletion worker convergence",
			"one passing run is not repeated sustained-soak evidence and never proves absence of leaks",
			"not production or production-equivalent evidence",
		},
	}
	document.Environment.OS = runtime.GOOS
	document.Environment.Arch = runtime.GOARCH
	document.Environment.NumCPU = runtime.NumCPU()
	document.Environment.GoVersion = runtime.Version()
	document.Environment.DependencyMode = "LOCAL_POSTGRES_MINIO"
	document.Environment.Classification = "LOCAL_LONG_SOAK"
	document.Environment.SyntheticDataOnly = true
	document.Environment.LoopbackDependenciesOnly = true
	document.Environment.ProductionTraffic = false
	document.Environment.ProductionCredentials = false
	document.Environment.ProductionEvidence = false
	document.Environment.ProductionEquivalentDependencies = false
	document.Environment.ContainsSecrets = false
	document.Scenario.ScenarioID = sustainedLocalSoakScenarioID
	document.Scenario.StartedAt = startedAt.Format(time.RFC3339)
	document.Scenario.CompletedAt = time.Now().UTC().Format(time.RFC3339)
	document.Scenario.DurationSeconds = actualDuration.Seconds()
	document.Scenario.WindowCount = len(observations)
	document.Scenario.Coverage = coverage
	document.Scenario.Observations = observations
	document.Scenario.Trends = trends
	document.Scenario.Assertions = map[string]any{
		"allRequiredCoverageExecuted":      allCoverage,
		"postRunRecoveryProbePassed":       recoveryPassed,
		"scanQueueRemainsWithinBound":      finalQueuePending <= sustainedMaximumScanQueuePending,
		"deletionBacklogConverged":         finalDeletionPending == 0 && finalDeletionStuck == 0,
		"productionEvidence":               false,
		"productionEquivalentDependencies": false,
		"leakProof":                        false,
		"capacityBoundaryEstablished":      false,
		"operationalThresholdApproved":     false,
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

func init() {
	// Keep deterministic JSON map ordering expectations out of the test logic;
	// this only prevents the imported sort package from being optimized away in
	// future edits that add percentile diagnostics alongside liveBatchResult.
	_ = sort.Ints
}
