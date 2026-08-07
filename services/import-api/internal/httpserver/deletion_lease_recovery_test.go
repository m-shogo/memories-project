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

	"github.com/m-shogo/memories-project/services/import-api/internal/accountdelete"
)

const deletionLeaseRecoveryAccounts = 2

type deletionLeaseRecoveryResultsDocument struct {
	SchemaVersion string `json:"schemaVersion"`
	CommitSHA     string `json:"commitSha"`
	GeneratedAt   string `json:"generatedAt"`
	Environment   struct {
		OS                               string `json:"os"`
		Arch                             string `json:"arch"`
		GoVersion                        string `json:"goVersion"`
		DependencyMode                   string `json:"dependencyMode"`
		SyntheticDataOnly                bool   `json:"syntheticDataOnly"`
		LeaseAbandonmentSimulation       bool   `json:"leaseAbandonmentSimulation"`
		ProductionTraffic                bool   `json:"productionTraffic"`
		ProductionCredentials            bool   `json:"productionCredentials"`
		ProductionEvidence               bool   `json:"productionEvidence"`
		ProductionEquivalentDependencies bool   `json:"productionEquivalentDependencies"`
		ActualProcessKillCovered         bool   `json:"actualProcessKillCovered"`
		ActualHostFailureCovered         bool   `json:"actualHostFailureCovered"`
		ContainsSecrets                  bool   `json:"containsSecrets"`
	} `json:"environment"`
	Scenario struct {
		ScenarioID                    string         `json:"scenarioId"`
		InitialClaims                 int            `json:"initialClaims"`
		ClaimsAvailableBeforeExpiry   int            `json:"claimsAvailableBeforeExpiry"`
		ReplacementWorkerReceipts     int            `json:"replacementWorkerReceipts"`
		UniqueReplacementReceipts     int            `json:"uniqueReplacementReceipts"`
		ReplacementWorkerErrors       int            `json:"replacementWorkerErrors"`
		FinalDeletionPending          int64          `json:"finalDeletionPending"`
		FinalDeletionStuck            int64          `json:"finalDeletionStuck"`
		FinalOwnedRowCount            int            `json:"finalOwnedRowCount"`
		FinalDeletedTombstonesEpoch2  int            `json:"finalDeletedTombstonesEpoch2"`
		RemainingObjectVersions       int            `json:"remainingObjectVersions"`
		Assertions                    map[string]any `json:"assertions"`
		Result                        string         `json:"result"`
		IntegrityResult               string         `json:"integrityResult"`
	} `json:"scenario"`
	Limitations []string `json:"limitations"`
}

func deleteForLeaseRecovery(t *testing.T, server *liveServer, token string) {
	t.Helper()
	response, body := server.request(t, http.MethodDelete, "/v1/account", token, nil)
	if response.StatusCode != http.StatusAccepted {
		t.Fatalf("delete status=%d body=%s", response.StatusCode, body)
	}
	var result struct {
		Status        string `json:"status"`
		DeletionEpoch int64  `json:"deletionEpoch"`
	}
	if err := json.Unmarshal(body, &result); err != nil {
		t.Fatal(err)
	}
	if result.Status != "deleting" || result.DeletionEpoch != 2 {
		t.Fatalf("unexpected deletion fence: %s", body)
	}
}

func objectKeyForLeaseRecovery(t *testing.T, server *liveServer, owner string) string {
	t.Helper()
	var key string
	if err := server.pool.QueryRow(context.Background(),
		`SELECT object_key FROM memory_os.upload_authorization
		 WHERE owner_account_id = $1 AND object_key IS NOT NULL
		 ORDER BY created_at LIMIT 1`, owner,
	).Scan(&key); err != nil {
		t.Fatal(err)
	}
	if key == "" {
		t.Fatal("empty object key in deletion ledger")
	}
	return key
}

func waitForDeletionLeasesToExpire(t *testing.T, server *liveServer, firstOwner, secondOwner string) {
	t.Helper()
	deadline := time.Now().Add(5 * time.Second)
	for {
		var expired int
		if err := server.pool.QueryRow(context.Background(),
			`SELECT count(*) FROM memory_os.account_control
			 WHERE account_id IN ($1, $2)
			   AND state = 'deleting'
			   AND deletion_lease_until IS NOT NULL
			   AND deletion_lease_until < now()`,
			firstOwner, secondOwner,
		).Scan(&expired); err != nil {
			t.Fatal(err)
		}
		if expired == deletionLeaseRecoveryAccounts {
			return
		}
		if time.Now().After(deadline) {
			t.Fatalf("deletion leases did not expire: expired=%d", expired)
		}
		time.Sleep(25 * time.Millisecond)
	}
}

func countOwnedRowsForLeaseRecovery(t *testing.T, server *liveServer, owners ...string) int {
	t.Helper()
	tables := []string{
		"memory_item", "apply_confirmation", "preview_candidate", "preview_rejection",
		"preview_ready", "upload_authorization", "quarantine_object", "import_job",
		"account_session",
	}
	total := 0
	for _, owner := range owners {
		for _, table := range tables {
			var count int
			if err := server.pool.QueryRow(context.Background(),
				"SELECT count(*) FROM memory_os."+table+" WHERE owner_account_id = $1", owner,
			).Scan(&count); err != nil {
				t.Fatal(err)
			}
			total += count
		}
	}
	return total
}

func TestDeletionLeaseExpiryRecoveryLocalDependencies(t *testing.T) {
	if os.Getenv("MEMORY_OS_RUN_DELETION_LEASE_RECOVERY") != "1" {
		t.Skip("set MEMORY_OS_RUN_DELETION_LEASE_RECOVERY=1 to run lease-expiry recovery proof")
	}

	server := newLiveServer(t)
	runID := time.Now().UnixNano()
	owners := []string{
		fmt.Sprintf("acct_lease_recovery_a_%d", runID),
		fmt.Sprintf("acct_lease_recovery_b_%d", runID),
	}
	objectKeys := make(map[string]string, deletionLeaseRecoveryAccounts)

	for index, owner := range owners {
		token := server.issueSession(t, owner)
		jobID := server.createJob(t, owner)
		_ = issueAndPutPrefenceUpload(t, server, token, jobID, index)
		objectKeys[owner] = objectKeyForLeaseRecovery(t, server, owner)
		versions, err := server.objects.ListObjectVersions(context.Background(), objectKeys[owner])
		if err != nil {
			t.Fatal(err)
		}
		if len(versions) == 0 {
			t.Fatalf("owner %d has no real object version before deletion", index)
		}
		deleteForLeaseRecovery(t, server, token)
	}

	claims := make([]accountdelete.Claim, 0, deletionLeaseRecoveryAccounts)
	for range deletionLeaseRecoveryAccounts {
		claim, ok, err := server.accountControl.Claim(context.Background(), 1)
		if err != nil {
			t.Fatal(err)
		}
		if !ok {
			t.Fatal("expected initial deletion claim")
		}
		if claim.Attempts != 1 || claim.DeletionEpoch != 2 {
			t.Fatalf("unexpected initial claim: %+v", claim)
		}
		claims = append(claims, claim)
	}
	claimedOwners := map[string]bool{}
	for _, claim := range claims {
		claimedOwners[claim.AccountID] = true
	}
	for _, owner := range owners {
		if !claimedOwners[owner] {
			t.Fatalf("initial claims did not cover both synthetic accounts")
		}
	}

	claimsBeforeExpiry := 0
	if _, ok, err := server.accountControl.Claim(context.Background(), 1); err != nil {
		t.Fatal(err)
	} else if ok {
		claimsBeforeExpiry++
	}
	if claimsBeforeExpiry != 0 {
		t.Fatal("abandoned lease became claimable before expiry")
	}

	// Simulate a process disappearing after object erasure but before the DB
	// sweep for one claim. The canonical DB ledger is deliberately retained.
	partialOwner := claims[1].AccountID
	partialKey := objectKeys[partialOwner]
	erased, err := server.objects.EraseObject(context.Background(), partialKey)
	if err != nil {
		t.Fatal(err)
	}
	if erased == 0 {
		t.Fatal("partial-erasure case did not erase a real object version")
	}
	partialVersions, err := server.objects.ListObjectVersions(context.Background(), partialKey)
	if err != nil {
		t.Fatal(err)
	}
	if len(partialVersions) != 0 {
		t.Fatalf("partial-erasure object still has %d versions", len(partialVersions))
	}
	var retainedLedgerRows int
	if err := server.pool.QueryRow(context.Background(),
		`SELECT count(*) FROM memory_os.upload_authorization
		 WHERE owner_account_id = $1 AND object_key = $2`, partialOwner, partialKey,
	).Scan(&retainedLedgerRows); err != nil {
		t.Fatal(err)
	}
	if retainedLedgerRows != 1 {
		t.Fatalf("partial-erasure ledger was not retained: rows=%d", retainedLedgerRows)
	}

	untouchedOwner := claims[0].AccountID
	untouchedVersions, err := server.objects.ListObjectVersions(context.Background(), objectKeys[untouchedOwner])
	if err != nil {
		t.Fatal(err)
	}
	if len(untouchedVersions) == 0 {
		t.Fatal("claimed-before-erasure case lost its object before replacement worker")
	}

	// Neither abandoned claim is released or completed. Recovery depends only
	// on the database lease expiry and replacement-worker claim path.
	waitForDeletionLeasesToExpire(t, server, owners[0], owners[1])

	worker := accountdelete.Worker{
		Queue:        server.accountControl,
		Repository:   server.accountControl,
		Objects:      server.objects,
		LeaseSeconds: 30,
	}
	receipts, err := worker.Sweep(context.Background(), deletionLeaseRecoveryAccounts)
	if err != nil {
		t.Fatal(err)
	}
	if len(receipts) != deletionLeaseRecoveryAccounts {
		t.Fatalf("replacement receipt count=%d", len(receipts))
	}
	uniqueReceipts := map[string]bool{}
	for _, receipt := range receipts {
		uniqueReceipts[receipt.AccountID] = true
		if receipt.Attempts != 2 || receipt.DeletionEpoch != 2 {
			t.Fatalf("replacement receipt did not prove expired-lease reclaim: %+v", receipt)
		}
	}
	if len(uniqueReceipts) != deletionLeaseRecoveryAccounts {
		t.Fatalf("replacement worker duplicate receipts=%d", len(uniqueReceipts))
	}

	backlog, err := worker.Backlog(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if backlog.Pending != 0 || backlog.Stuck != 0 {
		t.Fatalf("deletion backlog did not converge: %+v", backlog)
	}

	finalOwnedRows := countOwnedRowsForLeaseRecovery(t, server, owners...)
	if finalOwnedRows != 0 {
		t.Fatalf("owned rows survived recovery: %d", finalOwnedRows)
	}
	var deletedTombstones int
	if err := server.pool.QueryRow(context.Background(),
		`SELECT count(*) FROM memory_os.account_control
		 WHERE account_id IN ($1, $2) AND state = 'deleted' AND account_epoch = 2`,
		owners[0], owners[1],
	).Scan(&deletedTombstones); err != nil {
		t.Fatal(err)
	}
	if deletedTombstones != deletionLeaseRecoveryAccounts {
		t.Fatalf("deleted tombstone count=%d", deletedTombstones)
	}

	remainingVersions := 0
	for _, owner := range owners {
		versions, err := server.objects.ListObjectVersions(context.Background(), objectKeys[owner])
		if err != nil {
			t.Fatal(err)
		}
		remainingVersions += len(versions)
	}
	if remainingVersions != 0 {
		t.Fatalf("object versions survived or resurrected: %d", remainingVersions)
	}

	resultPath := os.Getenv("MEMORY_OS_DELETION_LEASE_RECOVERY_RESULTS_PATH")
	if resultPath == "" {
		return
	}
	commitSHA := os.Getenv("MEMORY_OS_COMMIT_SHA")
	if len(commitSHA) != 40 {
		t.Fatal("full MEMORY_OS_COMMIT_SHA is required when writing lease-recovery evidence")
	}

	document := deletionLeaseRecoveryResultsDocument{
		SchemaVersion: "memory-os-deletion-lease-recovery-results.v1",
		CommitSHA:     commitSHA,
		GeneratedAt:   time.Now().UTC().Format(time.RFC3339),
		Limitations: []string{
			"lease abandonment simulates process interruption; no operating-system process is killed",
			"one-second lease is test-only and not a production recommendation",
			"local PostgreSQL and MinIO are not production-equivalent dependencies",
		},
	}
	document.Environment.OS = runtime.GOOS
	document.Environment.Arch = runtime.GOARCH
	document.Environment.GoVersion = runtime.Version()
	document.Environment.DependencyMode = "LOCAL_POSTGRES_MINIO"
	document.Environment.SyntheticDataOnly = true
	document.Environment.LeaseAbandonmentSimulation = true
	document.Scenario.ScenarioID = "account-deletion-lease-expiry-reclaim-local-dependencies"
	document.Scenario.InitialClaims = len(claims)
	document.Scenario.ClaimsAvailableBeforeExpiry = claimsBeforeExpiry
	document.Scenario.ReplacementWorkerReceipts = len(receipts)
	document.Scenario.UniqueReplacementReceipts = len(uniqueReceipts)
	document.Scenario.ReplacementWorkerErrors = 0
	document.Scenario.FinalDeletionPending = backlog.Pending
	document.Scenario.FinalDeletionStuck = backlog.Stuck
	document.Scenario.FinalOwnedRowCount = finalOwnedRows
	document.Scenario.FinalDeletedTombstonesEpoch2 = deletedTombstones
	document.Scenario.RemainingObjectVersions = remainingVersions
	document.Scenario.Assertions = map[string]any{
		"noClaimBeforeExpiry":                          claimsBeforeExpiry == 0,
		"bothClaimsReclaimedAfterExpiry":               len(receipts) == deletionLeaseRecoveryAccounts,
		"partialObjectErasureRecoveredIdempotently":    retainedLedgerRows == 1 && len(partialVersions) == 0,
		"noResurrection":                               remainingVersions == 0,
		"backlogConverged":                             backlog.Pending == 0 && backlog.Stuck == 0,
		"allOwnedRowsErased":                           finalOwnedRows == 0,
		"actualProcessKillCovered":                     false,
		"actualHostFailureCovered":                     false,
		"productionEvidence":                           false,
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
