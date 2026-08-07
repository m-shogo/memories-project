//go:build linux

package httpserver

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"syscall"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/m-shogo/memories-project/services/import-api/internal/accountdelete"
	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/objectstore"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgrepo"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgscope"
)

const deletionWorkerSIGKILLLeaseSeconds = 5

func sigkillHelperAbort(stage string) {
	_, _ = fmt.Fprintf(os.Stderr, "SIGKILL_HELPER_FAILURE:%s\n", stage)
	os.Exit(70)
}

// TestDeletionWorkerSIGKILLHelper runs only as a child copy of the Go test
// binary. The parent does not pass an account id or object key: this process
// must claim already-fenced work from PostgreSQL and discover the object ledger
// through the deletion runtime exactly as a real worker would.
func TestDeletionWorkerSIGKILLHelper(t *testing.T) {
	if os.Getenv("MEMORY_OS_SIGKILL_HELPER") != "1" {
		t.Skip("SIGKILL helper subprocess only")
	}

	ctx := context.Background()
	databaseURL := os.Getenv("MEMORY_OS_SIGKILL_HELPER_DATABASE_URL")
	endpoint := os.Getenv("MEMORY_OS_TEST_S3_ENDPOINT")
	access := os.Getenv("MEMORY_OS_TEST_S3_ACCESS_KEY")
	secret := os.Getenv("MEMORY_OS_TEST_S3_SECRET_KEY")
	signalPath := os.Getenv("MEMORY_OS_SIGKILL_HELPER_SIGNAL_PATH")
	if databaseURL == "" || endpoint == "" || access == "" || secret == "" || signalPath == "" {
		sigkillHelperAbort("missing_configuration")
	}

	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		sigkillHelperAbort("database_pool")
	}
	defer pool.Close()
	executor := dbscope.New(pgscope.Beginner{Pool: pool})
	control := pgrepo.AccountControl{Pool: pool, Transactions: executor}
	objects, err := objectstore.New(objectstore.Config{
		Endpoint:        endpoint,
		Region:          "us-east-1",
		Bucket:          "memory-os-quarantine-test",
		AccessKeyID:     access,
		SecretAccessKey: secret,
	})
	if err != nil {
		sigkillHelperAbort("object_store")
	}

	claim, ok, err := control.Claim(ctx, deletionWorkerSIGKILLLeaseSeconds)
	if err != nil || !ok || claim.Attempts != 1 || claim.DeletionEpoch != 2 {
		sigkillHelperAbort("claim")
	}
	keys, err := control.ObjectKeys(ctx, claim.AccountID, claim.DeletionEpoch)
	if err != nil || len(keys) == 0 {
		sigkillHelperAbort("object_ledger")
	}
	erased, err := objects.EraseObject(ctx, keys[0])
	if err != nil || erased < 1 {
		sigkillHelperAbort("object_erasure")
	}

	// This is the only success signal the parent receives. No account id,
	// object key, token or credential crosses the process boundary as evidence.
	if err := os.WriteFile(signalPath, []byte("claimed-and-erased\n"), 0o600); err != nil {
		sigkillHelperAbort("signal")
	}

	// The parent must terminate this process with SIGKILL. Reaching normal test
	// completion would invalidate the proof because defer would close resources
	// and a future refactor might accidentally release work.
	select {}
}

type deletionWorkerSIGKILLResultsDocument struct {
	SchemaVersion string `json:"schemaVersion"`
	CommitSHA     string `json:"commitSha"`
	GeneratedAt   string `json:"generatedAt"`
	Environment   struct {
		OS                               string `json:"os"`
		Arch                             string `json:"arch"`
		GoVersion                        string `json:"goVersion"`
		DependencyMode                   string `json:"dependencyMode"`
		SyntheticDataOnly                bool   `json:"syntheticDataOnly"`
		ActualProcessKillCovered         bool   `json:"actualProcessKillCovered"`
		ActualHostFailureCovered         bool   `json:"actualHostFailureCovered"`
		ContainerRestartCovered          bool   `json:"containerRestartCovered"`
		ProductionTraffic                bool   `json:"productionTraffic"`
		ProductionCredentials            bool   `json:"productionCredentials"`
		ProductionEvidence               bool   `json:"productionEvidence"`
		ProductionEquivalentDependencies bool   `json:"productionEquivalentDependencies"`
		ContainsSecrets                  bool   `json:"containsSecrets"`
	} `json:"environment"`
	Scenario struct {
		ScenarioID                   string         `json:"scenarioId"`
		ChildClaimAttempts           int            `json:"childClaimAttempts"`
		ActualSIGKILLObserved        bool           `json:"actualSIGKILLObserved"`
		LedgerRowsAfterKill          int            `json:"ledgerRowsAfterKill"`
		ObjectVersionsAfterKill      int            `json:"objectVersionsAfterKill"`
		ClaimsAvailableBeforeExpiry  int            `json:"claimsAvailableBeforeExpiry"`
		ReplacementWorkerReceipts    int            `json:"replacementWorkerReceipts"`
		ReplacementReceiptAttempts   int            `json:"replacementReceiptAttempts"`
		FinalDeletionPending         int64          `json:"finalDeletionPending"`
		FinalDeletionStuck           int64          `json:"finalDeletionStuck"`
		FinalOwnedRowCount           int            `json:"finalOwnedRowCount"`
		FinalAccountState            string         `json:"finalAccountState"`
		FinalAccountEpoch            int64          `json:"finalAccountEpoch"`
		RemainingObjectVersions      int            `json:"remainingObjectVersions"`
		Assertions                   map[string]any `json:"assertions"`
		Result                       string         `json:"result"`
		IntegrityResult              string         `json:"integrityResult"`
	} `json:"scenario"`
	Limitations []string `json:"limitations"`
}

func waitForSIGKILLHelperSignal(t *testing.T, signalPath string, waitCh <-chan error, output *bytes.Buffer) {
	t.Helper()
	deadline := time.NewTimer(15 * time.Second)
	defer deadline.Stop()
	ticker := time.NewTicker(20 * time.Millisecond)
	defer ticker.Stop()
	for {
		if payload, err := os.ReadFile(signalPath); err == nil && string(payload) == "claimed-and-erased\n" {
			return
		}
		select {
		case err := <-waitCh:
			t.Fatalf("SIGKILL helper exited before interruption point: err=%v output_bytes=%d", err, output.Len())
		case <-deadline.C:
			t.Fatalf("SIGKILL helper did not reach interruption point; output_bytes=%d", output.Len())
		case <-ticker.C:
		}
	}
}

func waitForSingleDeletionLeaseExpiry(t *testing.T, server *liveServer, owner string) {
	t.Helper()
	deadline := time.Now().Add(10 * time.Second)
	for {
		var expired bool
		if err := server.pool.QueryRow(context.Background(),
			`SELECT deletion_lease_until IS NOT NULL AND deletion_lease_until < now()
			 FROM memory_os.account_control WHERE account_id = $1`, owner,
		).Scan(&expired); err != nil {
			t.Fatal(err)
		}
		if expired {
			return
		}
		if time.Now().After(deadline) {
			t.Fatal("SIGKILL deletion lease did not expire")
		}
		time.Sleep(25 * time.Millisecond)
	}
}

func TestDeletionWorkerSIGKILLRecoveryLocalDependencies(t *testing.T) {
	if os.Getenv("MEMORY_OS_RUN_DELETION_SIGKILL_RECOVERY") != "1" {
		t.Skip("set MEMORY_OS_RUN_DELETION_SIGKILL_RECOVERY=1 to run actual SIGKILL recovery proof")
	}

	server := newLiveServer(t)
	owner := fmt.Sprintf("acct_sigkill_recovery_%d", time.Now().UnixNano())
	token := server.issueSession(t, owner)
	jobID := server.createJob(t, owner)
	_ = issueAndPutPrefenceUpload(t, server, token, jobID, 0)
	objectKey := objectKeyForLeaseRecovery(t, server, owner)
	before, err := server.objects.ListObjectVersions(context.Background(), objectKey)
	if err != nil {
		t.Fatal(err)
	}
	if len(before) == 0 {
		t.Fatal("SIGKILL proof requires a real object version")
	}
	deleteForLeaseRecovery(t, server, token)

	signalPath := filepath.Join(t.TempDir(), "sigkill-worker-ready")
	cmd := exec.Command(os.Args[0], "-test.run=^TestDeletionWorkerSIGKILLHelper$", "-test.v")
	var childOutput bytes.Buffer
	cmd.Stdout = &childOutput
	cmd.Stderr = &childOutput
	cmd.Env = append(os.Environ(),
		"MEMORY_OS_SIGKILL_HELPER=1",
		"MEMORY_OS_SIGKILL_HELPER_DATABASE_URL="+server.appPool.Config().ConnString(),
		"MEMORY_OS_SIGKILL_HELPER_SIGNAL_PATH="+signalPath,
	)
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	}
	waitCh := make(chan error, 1)
	go func() { waitCh <- cmd.Wait() }()
	waitForSIGKILLHelperSignal(t, signalPath, waitCh, &childOutput)

	if err := syscall.Kill(cmd.Process.Pid, syscall.SIGKILL); err != nil {
		t.Fatal(err)
	}
	waitErr := <-waitCh
	if waitErr == nil {
		t.Fatal("SIGKILL helper exited successfully instead of being killed")
	}
	waitStatus, ok := cmd.ProcessState.Sys().(syscall.WaitStatus)
	if !ok || !waitStatus.Signaled() || waitStatus.Signal() != syscall.SIGKILL {
		t.Fatalf("child termination was not SIGKILL: status=%v", cmd.ProcessState.Sys())
	}
	actualSIGKILLObserved := true

	var ledgerRows int
	if err := server.pool.QueryRow(context.Background(),
		`SELECT count(*) FROM memory_os.upload_authorization
		 WHERE owner_account_id = $1 AND object_key = $2`, owner, objectKey,
	).Scan(&ledgerRows); err != nil {
		t.Fatal(err)
	}
	if ledgerRows != 1 {
		t.Fatalf("database ledger did not survive SIGKILL: rows=%d", ledgerRows)
	}
	afterKillVersions, err := server.objects.ListObjectVersions(context.Background(), objectKey)
	if err != nil {
		t.Fatal(err)
	}
	if len(afterKillVersions) != 0 {
		t.Fatalf("object versions survived child erasure: %d", len(afterKillVersions))
	}

	var state string
	var attempts int
	var leaseActive bool
	if err := server.pool.QueryRow(context.Background(),
		`SELECT state, deletion_attempts,
		        deletion_lease_until IS NOT NULL AND deletion_lease_until >= now()
		 FROM memory_os.account_control WHERE account_id = $1`, owner,
	).Scan(&state, &attempts, &leaseActive); err != nil {
		t.Fatal(err)
	}
	if state != "deleting" || attempts != 1 || !leaseActive {
		t.Fatalf("unexpected post-SIGKILL deletion state: state=%s attempts=%d lease_active=%v", state, attempts, leaseActive)
	}

	claimsBeforeExpiry := 0
	if _, found, err := server.accountControl.Claim(context.Background(), deletionWorkerSIGKILLLeaseSeconds); err != nil {
		t.Fatal(err)
	} else if found {
		claimsBeforeExpiry++
	}
	if claimsBeforeExpiry != 0 {
		t.Fatal("replacement claim became available before killed worker lease expired")
	}

	waitForSingleDeletionLeaseExpiry(t, server, owner)
	worker := accountdelete.Worker{
		Queue:        server.accountControl,
		Repository:   server.accountControl,
		Objects:      server.objects,
		LeaseSeconds: 30,
	}
	receipts, err := worker.Sweep(context.Background(), 1)
	if err != nil {
		t.Fatal(err)
	}
	if len(receipts) != 1 || receipts[0].AccountID != owner || receipts[0].DeletionEpoch != 2 || receipts[0].Attempts != 2 {
		t.Fatalf("replacement worker did not prove attempt-2 reclaim: %+v", receipts)
	}

	backlog, err := worker.Backlog(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if backlog.Pending != 0 || backlog.Stuck != 0 {
		t.Fatalf("SIGKILL recovery backlog did not converge: %+v", backlog)
	}
	finalOwnedRows := countOwnedRowsForLeaseRecovery(t, server, owner)
	if finalOwnedRows != 0 {
		t.Fatalf("owned rows survived SIGKILL recovery: %d", finalOwnedRows)
	}
	var finalState string
	var finalEpoch int64
	if err := server.pool.QueryRow(context.Background(),
		`SELECT state, account_epoch FROM memory_os.account_control WHERE account_id = $1`, owner,
	).Scan(&finalState, &finalEpoch); err != nil {
		t.Fatal(err)
	}
	if finalState != "deleted" || finalEpoch != 2 {
		t.Fatalf("unexpected final tombstone: state=%s epoch=%d", finalState, finalEpoch)
	}
	remaining, err := server.objects.ListObjectVersions(context.Background(), objectKey)
	if err != nil {
		t.Fatal(err)
	}
	if len(remaining) != 0 {
		t.Fatalf("object version resurrected after SIGKILL recovery: %d", len(remaining))
	}

	resultPath := os.Getenv("MEMORY_OS_DELETION_SIGKILL_RECOVERY_RESULTS_PATH")
	if resultPath == "" {
		return
	}
	commitSHA := os.Getenv("MEMORY_OS_COMMIT_SHA")
	if len(commitSHA) != 40 {
		t.Fatal("full MEMORY_OS_COMMIT_SHA is required when writing SIGKILL recovery evidence")
	}
	document := deletionWorkerSIGKILLResultsDocument{
		SchemaVersion: "memory-os-deletion-worker-sigkill-recovery-results.v1",
		CommitSHA:     commitSHA,
		GeneratedAt:   time.Now().UTC().Format(time.RFC3339),
		Limitations: []string{
			"one Linux child process is killed with SIGKILL; host and container restart are not covered",
			"five-second lease is test-only and not a production recommendation",
			"local PostgreSQL and MinIO are not production-equivalent dependencies",
		},
	}
	document.Environment.OS = runtime.GOOS
	document.Environment.Arch = runtime.GOARCH
	document.Environment.GoVersion = runtime.Version()
	document.Environment.DependencyMode = "LOCAL_POSTGRES_MINIO"
	document.Environment.SyntheticDataOnly = true
	document.Environment.ActualProcessKillCovered = true
	document.Scenario.ScenarioID = "account-deletion-worker-sigkill-recovery-local-dependencies"
	document.Scenario.ChildClaimAttempts = attempts
	document.Scenario.ActualSIGKILLObserved = actualSIGKILLObserved
	document.Scenario.LedgerRowsAfterKill = ledgerRows
	document.Scenario.ObjectVersionsAfterKill = len(afterKillVersions)
	document.Scenario.ClaimsAvailableBeforeExpiry = claimsBeforeExpiry
	document.Scenario.ReplacementWorkerReceipts = len(receipts)
	document.Scenario.ReplacementReceiptAttempts = receipts[0].Attempts
	document.Scenario.FinalDeletionPending = backlog.Pending
	document.Scenario.FinalDeletionStuck = backlog.Stuck
	document.Scenario.FinalOwnedRowCount = finalOwnedRows
	document.Scenario.FinalAccountState = finalState
	document.Scenario.FinalAccountEpoch = finalEpoch
	document.Scenario.RemainingObjectVersions = len(remaining)
	document.Scenario.Assertions = map[string]any{
		"childDiscoveredClaimWithoutAccountInput": true,
		"actualSIGKILLObserved":                  actualSIGKILLObserved,
		"ledgerSurvivedSIGKILL":                 ledgerRows == 1,
		"objectErasedBeforeSIGKILL":             len(afterKillVersions) == 0,
		"noClaimBeforeExpiry":                   claimsBeforeExpiry == 0,
		"replacementClaimWasAttempt2":           receipts[0].Attempts == 2,
		"idempotentObjectRecovery":              len(remaining) == 0,
		"backlogConverged":                      backlog.Pending == 0 && backlog.Stuck == 0,
		"allOwnedRowsErased":                    finalOwnedRows == 0,
		"actualHostFailureCovered":              false,
		"containerRestartCovered":               false,
		"productionEvidence":                    false,
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
