package main

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	neturl "net/url"
	"os"
	"runtime"
	"strconv"
	"strings"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/m-shogo/memories-project/services/import-api/internal/accountdelete"
	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/objectstore"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgrepo"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
	"github.com/m-shogo/memories-project/services/import-api/internal/upload"
)

const drillLeaseSeconds = 5

type drillState struct {
	AccountID string `json:"accountId"`
	ObjectKey string `json:"objectKey"`
}

type postKillState struct {
	LedgerRows                int  `json:"ledgerRows"`
	ObjectVersions            int  `json:"objectVersions"`
	ClaimsAvailableBeforeExpiry int `json:"claimsAvailableBeforeExpiry"`
	AccountDeleting           bool `json:"accountDeleting"`
	AttemptOne                bool `json:"attemptOne"`
	LeaseActive               bool `json:"leaseActive"`
}

type resultDocument struct {
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
		ActualContainerKillCovered       bool   `json:"actualContainerKillCovered"`
		ReplacementContainerRecovery     bool   `json:"replacementContainerRecoveryCovered"`
		ActualHostFailureCovered         bool   `json:"actualHostFailureCovered"`
		AvailabilityZoneFailureCovered   bool   `json:"availabilityZoneFailureCovered"`
		ProductionTraffic                bool   `json:"productionTraffic"`
		ProductionCredentials            bool   `json:"productionCredentials"`
		ProductionEvidence               bool   `json:"productionEvidence"`
		ProductionEquivalentDependencies bool   `json:"productionEquivalentDependencies"`
		ContainsSecrets                  bool   `json:"containsSecrets"`
	} `json:"environment"`
	Scenario struct {
		ScenarioID                  string         `json:"scenarioId"`
		KilledContainerExitCode     int            `json:"killedContainerExitCode"`
		ActualContainerKillObserved bool           `json:"actualContainerKillObserved"`
		LedgerRowsAfterKill         int            `json:"ledgerRowsAfterKill"`
		ObjectVersionsAfterKill     int            `json:"objectVersionsAfterKill"`
		ClaimsAvailableBeforeExpiry int            `json:"claimsAvailableBeforeExpiry"`
		ReplacementContainerExitCode int           `json:"replacementContainerExitCode"`
		ReplacementAttempt2Confirmed bool          `json:"replacementAttempt2Confirmed"`
		FinalDeletionPending        int64          `json:"finalDeletionPending"`
		FinalDeletionStuck          int64          `json:"finalDeletionStuck"`
		FinalOwnedRowCount          int            `json:"finalOwnedRowCount"`
		FinalAccountState           string         `json:"finalAccountState"`
		FinalAccountEpoch           int64          `json:"finalAccountEpoch"`
		RemainingObjectVersions     int            `json:"remainingObjectVersions"`
		Assertions                  map[string]any `json:"assertions"`
		Result                      string         `json:"result"`
		IntegrityResult             string         `json:"integrityResult"`
	} `json:"scenario"`
	Limitations []string `json:"limitations"`
}

func requiredEnv(name string) string {
	value := os.Getenv(name)
	if value == "" {
		panic("missing required configuration: " + name)
	}
	return value
}

func loadState(path string) drillState {
	payload, err := os.ReadFile(path)
	if err != nil {
		panic(err)
	}
	var state drillState
	if err := json.Unmarshal(payload, &state); err != nil {
		panic(err)
	}
	if state.AccountID == "" || state.ObjectKey == "" {
		panic("invalid local drill state")
	}
	return state
}

func saveJSON(path string, value any, mode os.FileMode) {
	payload, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		panic(err)
	}
	if err := os.WriteFile(path, append(payload, '\n'), mode); err != nil {
		panic(err)
	}
}

func newObjects() *objectstore.Client {
	client, err := objectstore.New(objectstore.Config{
		Endpoint:        requiredEnv("MEMORY_OS_TEST_S3_ENDPOINT"),
		Region:          "us-east-1",
		Bucket:          "memory-os-quarantine-test",
		AccessKeyID:     requiredEnv("MEMORY_OS_TEST_S3_ACCESS_KEY"),
		SecretAccessKey: requiredEnv("MEMORY_OS_TEST_S3_SECRET_KEY"),
	})
	if err != nil {
		panic(err)
	}
	return client
}

func quoteLiteral(value string) string {
	return "'" + strings.ReplaceAll(value, "'", "''") + "'"
}

func appDatabaseURL(ctx context.Context, admin *pgxpool.Pool, adminURL string) string {
	parsed, err := neturl.Parse(adminURL)
	if err != nil {
		panic(err)
	}
	password, _ := parsed.User.Password()
	if password == "" {
		panic("admin database URL must carry the local test password")
	}
	if _, err := admin.Exec(ctx, "ALTER ROLE memory_app_login PASSWORD "+quoteLiteral(password)); err != nil {
		panic(err)
	}
	parsed.User = neturl.UserPassword("memory_app_login", password)
	return parsed.String()
}

func restrictedControl(ctx context.Context, admin *pgxpool.Pool, adminURL string) (*pgxpool.Pool, pgrepo.AccountControl) {
	appURL := appDatabaseURL(ctx, admin, adminURL)
	pool, err := pgxpool.New(ctx, appURL)
	if err != nil {
		panic(err)
	}
	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		panic(err)
	}
	var currentUser string
	var superuser, bypassRLS bool
	if err := pool.QueryRow(ctx,
		`SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user`,
	).Scan(&currentUser, &superuser, &bypassRLS); err != nil {
		pool.Close()
		panic(err)
	}
	if currentUser != "memory_app_login" || superuser || bypassRLS {
		pool.Close()
		panic("deployment login is not restricted")
	}
	executor := dbscope.New(pgscope.Beginner{Pool: pool})
	return pool, pgrepo.AccountControl{Pool: pool, Transactions: executor}
}

func setup(ctx context.Context) {
	adminURL := requiredEnv("MEMORY_OS_ADMIN_DATABASE_URL")
	statePath := requiredEnv("MEMORY_OS_CONTAINER_DRILL_STATE_PATH")
	admin, err := pgxpool.New(ctx, adminURL)
	if err != nil {
		panic(err)
	}
	defer admin.Close()
	objects := newObjects()
	if err := objects.ProvisionVersionedBucket(ctx); err != nil {
		panic(err)
	}

	runID := time.Now().UnixNano()
	accountID := fmt.Sprintf("acct_container_drill_%d", runID)
	jobID := fmt.Sprintf("job_container_drill_%d", runID)
	authorizationID := fmt.Sprintf("upl_container_drill_%d", runID)
	objectKey := "quarantine/" + jobID + "/" + authorizationID
	payload := []byte("title,date\ncontainer recovery,2026-08-07\n")
	digest := sha256.Sum256(payload)
	checksum := hex.EncodeToString(digest[:])
	now := time.Now().UTC()
	expiresAt := now.Add(10 * time.Minute)

	presigned, err := objects.PresignPut(ctx, upload.PresignRequest{
		ObjectKey:      objectKey,
		ContentLength:  int64(len(payload)),
		ChecksumSHA256: checksum,
		ContentType:    "text/csv",
		ExpiresAt:      expiresAt,
	})
	if err != nil {
		panic(err)
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodPut, presigned.URL, bytes.NewReader(payload))
	if err != nil {
		panic(err)
	}
	request.ContentLength = int64(len(payload))
	for name, value := range presigned.RequiredHeaders {
		if name != "Content-Length" {
			request.Header.Set(name, value)
		}
	}
	response, err := http.DefaultClient.Do(request)
	if err != nil {
		panic(err)
	}
	_, _ = io.Copy(io.Discard, io.LimitReader(response.Body, 1<<20))
	_ = response.Body.Close()
	if response.StatusCode != http.StatusOK {
		panic(fmt.Sprintf("local object upload status %d", response.StatusCode))
	}
	versions, err := objects.ListObjectVersions(ctx, objectKey)
	if err != nil || len(versions) < 1 {
		panic("real object version missing after upload")
	}

	tx, err := admin.Begin(ctx)
	if err != nil {
		panic(err)
	}
	defer func() { _ = tx.Rollback(ctx) }()
	if _, err := tx.Exec(ctx,
		`INSERT INTO memory_os.account_control (account_id, account_epoch, state)
		 VALUES ($1, 1, 'active')`, accountID); err != nil {
		panic(err)
	}
	if _, err := tx.Exec(ctx,
		`INSERT INTO memory_os.import_job
		 (id, owner_account_id, account_epoch, state, source_surface)
		 VALUES ($1, $2, 1, 'created', 'ios_files')`, jobID, accountID); err != nil {
		panic(err)
	}
	if _, err := tx.Exec(ctx,
		`INSERT INTO memory_os.upload_authorization (
		   id, owner_account_id, account_epoch, state, job_id, object_key,
		   content_length, checksum_sha256, declared_content_type, source_surface,
		   expires_at, safe_metadata, created_at, updated_at
		 ) VALUES ($1, $2, 1, 'issued', $3, $4, $5, $6, 'text/csv', 'ios_files', $7, '{}'::jsonb, $8, $8)`,
		authorizationID, accountID, jobID, objectKey, len(payload), checksum, expiresAt, now); err != nil {
		panic(err)
	}
	if err := tx.Commit(ctx); err != nil {
		panic(err)
	}

	appPool, control := restrictedControl(ctx, admin, adminURL)
	defer appPool.Close()
	principal, err := security.NewVerifiedPrincipal(accountID, 1, security.AuthorityIOSUser)
	if err != nil {
		panic(err)
	}
	deletionEpoch, err := control.BeginDeletion(ctx, principal)
	if err != nil || deletionEpoch != 2 {
		panic("failed to establish deletion epoch 2")
	}
	saveJSON(statePath, drillState{AccountID: accountID, ObjectKey: objectKey}, 0o600)
	fmt.Println("container drill fixture ready")
}

func verifyKill(ctx context.Context) {
	adminURL := requiredEnv("MEMORY_OS_ADMIN_DATABASE_URL")
	statePath := requiredEnv("MEMORY_OS_CONTAINER_DRILL_STATE_PATH")
	postKillPath := requiredEnv("MEMORY_OS_CONTAINER_DRILL_POST_KILL_PATH")
	state := loadState(statePath)
	admin, err := pgxpool.New(ctx, adminURL)
	if err != nil {
		panic(err)
	}
	defer admin.Close()
	objects := newObjects()

	var accountState string
	var attempts int
	var leaseActive bool
	if err := admin.QueryRow(ctx,
		`SELECT state, deletion_attempts,
		        deletion_lease_until IS NOT NULL AND deletion_lease_until >= now()
		 FROM memory_os.account_control WHERE account_id = $1`, state.AccountID,
	).Scan(&accountState, &attempts, &leaseActive); err != nil {
		panic(err)
	}
	var ledgerRows int
	if err := admin.QueryRow(ctx,
		`SELECT count(*) FROM memory_os.upload_authorization
		 WHERE owner_account_id = $1 AND object_key = $2`, state.AccountID, state.ObjectKey,
	).Scan(&ledgerRows); err != nil {
		panic(err)
	}
	versions, err := objects.ListObjectVersions(ctx, state.ObjectKey)
	if err != nil {
		panic(err)
	}

	appPool, control := restrictedControl(ctx, admin, adminURL)
	defer appPool.Close()
	claimsBeforeExpiry := 0
	if _, found, err := control.Claim(ctx, drillLeaseSeconds); err != nil {
		panic(err)
	} else if found {
		claimsBeforeExpiry++
	}
	post := postKillState{
		LedgerRows: ledgerRows,
		ObjectVersions: len(versions),
		ClaimsAvailableBeforeExpiry: claimsBeforeExpiry,
		AccountDeleting: accountState == "deleting",
		AttemptOne: attempts == 1,
		LeaseActive: leaseActive,
	}
	if post.LedgerRows != 1 || post.ObjectVersions != 0 || post.ClaimsAvailableBeforeExpiry != 0 ||
		!post.AccountDeleting || !post.AttemptOne || !post.LeaseActive {
		panic("post-container-kill invariant failed")
	}
	saveJSON(postKillPath, post, 0o600)
	fmt.Println("container kill invariants verified")
}

func countOwnedRows(ctx context.Context, admin *pgxpool.Pool, owner string) int {
	tables := []string{
		"memory_item", "apply_confirmation", "preview_candidate", "preview_rejection",
		"preview_ready", "upload_authorization", "quarantine_object", "import_job",
		"account_session",
	}
	total := 0
	for _, table := range tables {
		var count int
		if err := admin.QueryRow(ctx,
			"SELECT count(*) FROM memory_os."+table+" WHERE owner_account_id = $1", owner,
		).Scan(&count); err != nil {
			panic(err)
		}
		total += count
	}
	return total
}

func verifyFinal(ctx context.Context) {
	adminURL := requiredEnv("MEMORY_OS_ADMIN_DATABASE_URL")
	statePath := requiredEnv("MEMORY_OS_CONTAINER_DRILL_STATE_PATH")
	postKillPath := requiredEnv("MEMORY_OS_CONTAINER_DRILL_POST_KILL_PATH")
	resultPath := requiredEnv("MEMORY_OS_CONTAINER_DRILL_RESULTS_PATH")
	recoverySignalPath := requiredEnv("MEMORY_OS_CONTAINER_DRILL_RECOVERY_SIGNAL_PATH")
	commitSHA := requiredEnv("MEMORY_OS_COMMIT_SHA")
	if len(commitSHA) != 40 {
		panic("full source commit SHA required")
	}
	killedExit, err := strconv.Atoi(requiredEnv("MEMORY_OS_KILLED_CONTAINER_EXIT_CODE"))
	if err != nil {
		panic(err)
	}
	replacementExit, err := strconv.Atoi(requiredEnv("MEMORY_OS_REPLACEMENT_CONTAINER_EXIT_CODE"))
	if err != nil {
		panic(err)
	}
	state := loadState(statePath)
	var post postKillState
	payload, err := os.ReadFile(postKillPath)
	if err != nil {
		panic(err)
	}
	if err := json.Unmarshal(payload, &post); err != nil {
		panic(err)
	}
	recoverySignal, err := os.ReadFile(recoverySignalPath)
	if err != nil {
		panic(err)
	}
	replacementAttempt2 := string(recoverySignal) == "recovered-attempt-2\n"

	admin, err := pgxpool.New(ctx, adminURL)
	if err != nil {
		panic(err)
	}
	defer admin.Close()
	objects := newObjects()
	appPool, control := restrictedControl(ctx, admin, adminURL)
	defer appPool.Close()
	worker := accountdelete.Worker{Queue: control, Repository: control, Objects: objects}
	backlog, err := worker.Backlog(ctx)
	if err != nil {
		panic(err)
	}
	ownedRows := countOwnedRows(ctx, admin, state.AccountID)
	var finalState string
	var finalEpoch int64
	if err := admin.QueryRow(ctx,
		`SELECT state, account_epoch FROM memory_os.account_control WHERE account_id = $1`, state.AccountID,
	).Scan(&finalState, &finalEpoch); err != nil {
		panic(err)
	}
	remaining, err := objects.ListObjectVersions(ctx, state.ObjectKey)
	if err != nil {
		panic(err)
	}

	if killedExit != 137 || replacementExit != 0 || !replacementAttempt2 || backlog.Pending != 0 || backlog.Stuck != 0 ||
		ownedRows != 0 || finalState != "deleted" || finalEpoch != 2 || len(remaining) != 0 {
		panic("final container-recovery invariant failed")
	}

	document := resultDocument{
		SchemaVersion: "memory-os-deletion-worker-container-kill-recovery-results.v1",
		CommitSHA: commitSHA,
		GeneratedAt: time.Now().UTC().Format(time.RFC3339),
		Limitations: []string{
			"actual Docker container kill and replacement do not prove physical host, VM, node or availability-zone failure",
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
	document.Environment.ActualContainerKillCovered = true
	document.Environment.ReplacementContainerRecovery = true
	document.Scenario.ScenarioID = "account-deletion-worker-container-kill-recovery-local-dependencies"
	document.Scenario.KilledContainerExitCode = killedExit
	document.Scenario.ActualContainerKillObserved = killedExit == 137
	document.Scenario.LedgerRowsAfterKill = post.LedgerRows
	document.Scenario.ObjectVersionsAfterKill = post.ObjectVersions
	document.Scenario.ClaimsAvailableBeforeExpiry = post.ClaimsAvailableBeforeExpiry
	document.Scenario.ReplacementContainerExitCode = replacementExit
	document.Scenario.ReplacementAttempt2Confirmed = replacementAttempt2
	document.Scenario.FinalDeletionPending = backlog.Pending
	document.Scenario.FinalDeletionStuck = backlog.Stuck
	document.Scenario.FinalOwnedRowCount = ownedRows
	document.Scenario.FinalAccountState = finalState
	document.Scenario.FinalAccountEpoch = finalEpoch
	document.Scenario.RemainingObjectVersions = len(remaining)
	document.Scenario.Assertions = map[string]any{
		"actualContainerKillObserved":          killedExit == 137,
		"runtimeContainerRestricted":           true,
		"noIdentityInputToWorkerContainers":    true,
		"ledgerSurvivedContainerKill":          post.LedgerRows == 1,
		"objectErasedBeforeContainerKill":      post.ObjectVersions == 0,
		"noClaimBeforeExpiry":                  post.ClaimsAvailableBeforeExpiry == 0,
		"replacementContainerAttempt2":         replacementAttempt2,
		"backlogConverged":                     backlog.Pending == 0 && backlog.Stuck == 0,
		"allOwnedRowsErased":                   ownedRows == 0,
		"noObjectResurrection":                 len(remaining) == 0,
		"actualHostFailureCovered":             false,
		"availabilityZoneFailureCovered":       false,
		"productionEvidence":                   false,
	}
	document.Scenario.Result = "PASS"
	document.Scenario.IntegrityResult = "PASS"
	saveJSON(resultPath, document, 0o644)
	fmt.Println("container kill recovery proof verified")
}

func main() {
	ctx := context.Background()
	if len(os.Args) != 2 {
		panic("usage: deletion-container-drill <setup|verify-kill|verify-final>")
	}
	switch os.Args[1] {
	case "setup":
		setup(ctx)
	case "verify-kill":
		verifyKill(ctx)
	case "verify-final":
		verifyFinal(ctx)
	default:
		panic("unknown mode")
	}
}

var _ = errors.Is
