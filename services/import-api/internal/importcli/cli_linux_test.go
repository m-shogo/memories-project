//go:build linux

package importcli

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/m-shogo/memories-project/services/import-api/internal/csvworker"
	"github.com/m-shogo/memories-project/services/import-api/internal/parsersup"
	"github.com/m-shogo/memories-project/services/import-api/internal/previewcommit"
)

func TestMain(m *testing.M) {
	if mode := os.Getenv(parsersup.WorkerModeEnv); mode != "" {
		if mode == "genericcsv" {
			os.Exit(csvworker.Run(os.Getenv(csvworker.OptionsEnv), os.Stdin, os.Stdout, os.Stderr))
		}
		os.Exit(3)
	}
	os.Exit(m.Run())
}

const testCSV = `title,date,url,text
summer trip,2026-07-21,https://example.com/trip,three temples
,,,missing title row
ramen log,,,
`

func testConfig(t *testing.T) (Config, *pgxpool.Pool) {
	t.Helper()
	databaseURL := os.Getenv("MEMORY_OS_TEST_DATABASE_URL")
	endpoint := os.Getenv("MEMORY_OS_TEST_S3_ENDPOINT")
	if databaseURL == "" || endpoint == "" {
		t.Skip("MEMORY_OS_TEST_DATABASE_URL and MEMORY_OS_TEST_S3_ENDPOINT are required; skipping importcli tests")
	}
	ctx := context.Background()

	// Own database: the shared test database is truncated by parallel suites.
	admin, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		t.Fatal(err)
	}
	defer admin.Close()
	if _, err := admin.Exec(ctx, "CREATE DATABASE memory_os_importcli"); err != nil &&
		!strings.Contains(err.Error(), "already exists") {
		t.Fatal(err)
	}
	cliURL := strings.Replace(databaseURL, "/memory_os_security", "/memory_os_importcli", 1)
	pool, err := pgxpool.New(ctx, cliURL)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(pool.Close)

	csvPath := filepath.Join(t.TempDir(), "source.csv")
	if err := os.WriteFile(csvPath, []byte(testCSV), 0o600); err != nil {
		t.Fatal(err)
	}
	workerPath, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	access := os.Getenv("MEMORY_OS_TEST_S3_ACCESS_KEY")
	if access == "" {
		access = "minioadmin"
	}
	secret := os.Getenv("MEMORY_OS_TEST_S3_SECRET_KEY")
	if secret == "" {
		secret = "minioadmin"
	}
	return Config{
		DatabaseURL:   cliURL,
		S3Endpoint:    endpoint,
		S3AccessKey:   access,
		S3SecretKey:   secret,
		Bucket:        "memory-os-quarantine-test",
		CSVPath:       csvPath,
		OptionsJSON:   `{"titleColumn":"title","dateColumn":"date","dateLayout":"2006-01-02","urlColumn":"url","textColumn":"text"}`,
		WorkerPath:    workerPath,
		MigrationsDir: filepath.Join("..", "..", "..", "..", "infra", "postgresql", "security"),
		ExtraWorkerEnv: []string{
			parsersup.WorkerModeEnv + "=genericcsv",
		},
	}, pool
}

func TestRunImportsAndPrintsCommittedPreview(t *testing.T) {
	config, pool := testConfig(t)
	var out bytes.Buffer
	config.Out = &out
	if err := Run(context.Background(), config); err != nil {
		t.Fatalf("importcli run failed: %v\noutput:\n%s", err, out.String())
	}

	rendered := out.String()
	for _, expected := range []string{
		"worker digest (computed, NOT a reviewed pin):",
		"uploaded: quarantine/",
		"preview:     prv_",
		"accepted:    2 records",
		"rejected:    1 records",
		"summer trip",
		"IMPORT_CSV_TITLE_REQUIRED",
		"job state:   preview_ready",
	} {
		if !strings.Contains(rendered, expected) {
			t.Fatalf("output is missing %q:\n%s", expected, rendered)
		}
	}

	var previews int
	if err := pool.QueryRow(context.Background(),
		"SELECT count(*) FROM memory_os.preview_ready").Scan(&previews); err != nil {
		t.Fatal(err)
	}
	if previews < 1 {
		t.Fatalf("no committed preview found")
	}
}

func TestRunRejectsSecondImportForOneJob(t *testing.T) {
	config, _ := testConfig(t)
	var out bytes.Buffer
	config.Out = &out
	// The database persists across test runs, so the job ID must be unique
	// per invocation or an older committed Preview makes the first run
	// conflict immediately.
	config.JobID = fmt.Sprintf("job_importcli_conflict_%d", time.Now().UnixNano())
	if err := Run(context.Background(), config); err != nil {
		t.Fatalf("first run failed: %v\noutput:\n%s", err, out.String())
	}
	// A second import for the same job uploads a new object version, so its
	// deterministic commit key differs and the one-preview-per-job rule must
	// reject it rather than silently replacing the committed Preview.
	if err := Run(context.Background(), config); !errors.Is(err, previewcommit.ErrCommitConflict) {
		t.Fatalf("second differing import for one job was not rejected: %v", err)
	}
}

func TestRunValidatesConfiguration(t *testing.T) {
	if err := Run(context.Background(), Config{Out: &bytes.Buffer{}}); !errors.Is(err, ErrInvalidConfig) {
		t.Fatalf("empty configuration was accepted: %v", err)
	}
}

func TestRunRejectsMismatchedWorkerPin(t *testing.T) {
	config, _ := testConfig(t)
	var out bytes.Buffer
	config.Out = &out
	config.WorkerSHA256 = strings.Repeat("0", 64)
	err := Run(context.Background(), config)
	if err == nil || !strings.Contains(err.Error(), "pinned digest") {
		t.Fatalf("mismatched worker pin was accepted: %v", err)
	}
}
