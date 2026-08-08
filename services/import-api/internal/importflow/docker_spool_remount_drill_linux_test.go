//go:build linux

package importflow

import (
	"context"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/m-shogo/memories-project/services/import-api/internal/previewcommit"
	"github.com/m-shogo/memories-project/services/import-api/internal/previewspool"
)

const (
	dockerSpoolRemountGate = "MEMORY_OS_RUN_DOCKER_SPOOL_REMOUNT"
	dockerResumeHelperGate = "MEMORY_OS_DOCKER_RESUME_HELPER"
)

type dockerResumeInput struct {
	Request Request   `json:"request"`
	Now     time.Time `json:"now"`
}

// TestFlowResumesSealedSpoolInFreshContainer proves the sealed Preview spool is
// durable across the original manager lifetime and can be mounted into a fresh
// container that has neither object-store nor parser access. The producer is
// still the host test process, so this is intentionally narrower than a full
// producer-container or host restart drill.
func TestFlowResumesSealedSpoolInFreshContainer(t *testing.T) {
	if os.Getenv(dockerSpoolRemountGate) != "1" {
		t.Skip("fresh-container spool remount drill is explicitly gated")
	}
	if _, err := exec.LookPath("docker"); err != nil {
		t.Fatalf("docker is required when %s=1: %v", dockerSpoolRemountGate, err)
	}
	databaseURL := os.Getenv("MEMORY_OS_TEST_DATABASE_URL")
	if databaseURL == "" {
		t.Fatal("MEMORY_OS_TEST_DATABASE_URL is required")
	}

	env := newFlowEnv(t, "genericcsv")
	now := time.Now().UTC()
	source := env.uploadSource(t, "upl_01J00000000000000000000012", flowSource)

	badConfig, err := pgxpool.ParseConfig(
		"postgres://postgres:postgres@127.0.0.1:1/memory_os_unreachable?sslmode=disable",
	)
	if err != nil {
		t.Fatal(err)
	}
	badConfig.ConnConfig.ConnectTimeout = 250 * time.Millisecond
	badConfig.MaxConns = 1
	badPool, err := pgxpool.NewWithConfig(context.Background(), badConfig)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(badPool.Close)
	unreachableCommitter, err := previewcommit.NewCommitter(badPool)
	if err != nil {
		t.Fatal(err)
	}
	env.flow.Committer = unreachableCommitter

	request := flowRequest(
		"spl_01J00000000000000000000012",
		"prv_flowdock001",
		source,
		now,
	)
	if _, err := env.flow.Run(context.Background(), request, now); err == nil {
		t.Fatal("import unexpectedly committed while PostgreSQL was unreachable")
	}
	assertNothingImported(t, env.pool)
	if _, err := os.Lstat(filepath.Join(env.root, request.SpoolID)); err != nil {
		t.Fatalf("failed commit did not preserve sealed spool: %v", err)
	}

	// End the original spool-manager lifetime before the recovery container is
	// started. The helper must reopen the bind-mounted durable directory itself.
	if err := env.flow.Spool.Close(); err != nil {
		t.Fatalf("close original spool manager: %v", err)
	}
	env.flow.Spool = nil

	inputDir := t.TempDir()
	inputPath := filepath.Join(inputDir, "resume-input.json")
	payload, err := json.Marshal(dockerResumeInput{Request: request, Now: now})
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(inputPath, payload, 0o600); err != nil {
		t.Fatal(err)
	}

	testBinary, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	containerDatabaseURL := strings.Replace(databaseURL, "127.0.0.1", "host.docker.internal", 1)
	containerDatabaseURL = strings.Replace(containerDatabaseURL, "localhost", "host.docker.internal", 1)

	command := exec.Command(
		"docker", "run", "--rm",
		"--add-host=host.docker.internal:host-gateway",
		"-v", testBinary+":/helper/importflow.test:ro",
		"-v", env.root+":/recovery-spool",
		"-v", inputPath+":/request/resume-input.json:ro",
		"-e", dockerResumeHelperGate+"=1",
		"-e", "MEMORY_OS_DOCKER_SPOOL_ROOT=/recovery-spool",
		"-e", "MEMORY_OS_DOCKER_RESUME_INPUT=/request/resume-input.json",
		"-e", "MEMORY_OS_DOCKER_DATABASE_URL="+containerDatabaseURL,
		"--entrypoint", "/helper/importflow.test",
		"postgres:16-alpine",
		"-test.run", "^TestDockerResumeCommitHelper$", "-test.v",
	)
	output, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("fresh-container ResumeCommit failed: %v\n%s", err, sanitizeDockerResumeOutput(string(output), databaseURL, containerDatabaseURL))
	}
	if !strings.Contains(string(output), "MEMORY_OS_DOCKER_RESUME_COMMIT=PASS") {
		t.Fatalf("fresh-container ResumeCommit success marker missing: %s", sanitizeDockerResumeOutput(string(output), databaseURL, containerDatabaseURL))
	}
	t.Log("MEMORY_OS_FRESH_CONTAINER_SPOOL_REMOUNT=PASS")

	var previews int
	var candidates int
	var rejections int
	if err := env.pool.QueryRow(
		context.Background(),
		"SELECT count(*) FROM memory_os.preview_ready WHERE id = $1",
		request.PreviewID,
	).Scan(&previews); err != nil {
		t.Fatal(err)
	}
	if err := env.pool.QueryRow(
		context.Background(),
		"SELECT count(*) FROM memory_os.preview_candidate WHERE preview_id = $1",
		request.PreviewID,
	).Scan(&candidates); err != nil {
		t.Fatal(err)
	}
	if err := env.pool.QueryRow(
		context.Background(),
		"SELECT count(*) FROM memory_os.preview_rejection WHERE preview_id = $1",
		request.PreviewID,
	).Scan(&rejections); err != nil {
		t.Fatal(err)
	}
	if previews != 1 || candidates != 2 || rejections != 1 {
		t.Fatalf(
			"fresh-container recovery committed inconsistent rows: previews=%d candidates=%d rejections=%d",
			previews, candidates, rejections,
		)
	}
}

// TestDockerResumeCommitHelper is invoked only inside the fresh recovery
// container. It intentionally constructs a Flow with Spool + Committer only.
func TestDockerResumeCommitHelper(t *testing.T) {
	if os.Getenv(dockerResumeHelperGate) != "1" {
		t.Skip("Docker ResumeCommit helper is internal to the remount drill")
	}
	spoolRoot := os.Getenv("MEMORY_OS_DOCKER_SPOOL_ROOT")
	inputPath := os.Getenv("MEMORY_OS_DOCKER_RESUME_INPUT")
	databaseURL := os.Getenv("MEMORY_OS_DOCKER_DATABASE_URL")
	if spoolRoot == "" || inputPath == "" || databaseURL == "" {
		t.Fatal("Docker ResumeCommit helper environment incomplete")
	}

	payload, err := os.ReadFile(inputPath)
	if err != nil {
		t.Fatal(err)
	}
	var input dockerResumeInput
	if err := json.Unmarshal(payload, &input); err != nil {
		t.Fatal(err)
	}
	manager, err := previewspool.OpenManager(spoolRoot)
	if err != nil {
		t.Fatalf("reopen mounted spool: %v", err)
	}
	defer manager.Close()

	pool, err := pgxpool.New(context.Background(), databaseURL)
	if err != nil {
		t.Fatalf("connect recovery database: %v", err)
	}
	defer pool.Close()
	committer, err := previewcommit.NewCommitter(pool)
	if err != nil {
		t.Fatal(err)
	}
	recoveryFlow := &Flow{Spool: manager, Committer: committer}
	result, err := recoveryFlow.ResumeCommit(context.Background(), input.Request, input.Now)
	if err != nil {
		t.Fatalf("ResumeCommit from mounted spool: %v", err)
	}
	if result.Commit.AlreadyCommitted {
		t.Fatal("first successful fresh-container recovery was mislabeled as replay")
	}
	if result.Verified.SpoolID != input.Request.SpoolID {
		t.Fatalf("fresh-container recovery used different spool: got %s want %s", result.Verified.SpoolID, input.Request.SpoolID)
	}
	if result.Verified.Evidence.Accepted.RecordCount != 2 ||
		result.Verified.Evidence.Rejected.RecordCount != 1 {
		t.Fatalf("fresh-container recovery evidence drift: %+v", result.Verified.Evidence)
	}
	t.Log("MEMORY_OS_DOCKER_RESUME_COMMIT=PASS")
}

func sanitizeDockerResumeOutput(value string, secrets ...string) string {
	clean := value
	for _, secret := range secrets {
		if secret != "" {
			clean = strings.ReplaceAll(clean, secret, "[redacted-database-url]")
		}
	}
	return clean
}
