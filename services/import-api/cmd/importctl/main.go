// importctl is a local development harness: the first visible end-to-end run
// of the supervised import flow. It uploads one local CSV through the real
// presigned binding, parses it in a digest-pinned worker under supervision,
// verifies and commits atomically, and prints the committed Preview.
//
// It targets the scripts/dev-up.sh stack by default and must never be pointed
// at production infrastructure.
package main

import (
	"context"
	"flag"
	"fmt"
	"os"

	"github.com/m-shogo/memories-project/services/import-api/internal/importcli"
)

func main() {
	databaseURL := flag.String("database-url",
		envOr("MEMORY_OS_TEST_DATABASE_URL", "postgres://postgres:postgres@127.0.0.1:55432/memory_os_security"),
		"PostgreSQL URL of the dev stack")
	s3Endpoint := flag.String("s3-endpoint",
		envOr("MEMORY_OS_TEST_S3_ENDPOINT", "http://127.0.0.1:59000"),
		"S3-compatible endpoint of the dev stack")
	s3Access := flag.String("s3-access-key", envOr("MEMORY_OS_TEST_S3_ACCESS_KEY", "minioadmin"), "S3 access key")
	s3Secret := flag.String("s3-secret-key", envOr("MEMORY_OS_TEST_S3_SECRET_KEY", "minioadmin"), "S3 secret key")
	bucket := flag.String("bucket", "memory-os-quarantine-dev", "quarantine bucket name")
	csvPath := flag.String("csv", "", "path to the CSV source file (required)")
	optionsJSON := flag.String("options",
		`{"titleColumn":"title","dateColumn":"date","dateLayout":"2006-01-02","urlColumn":"url","textColumn":"text"}`,
		"Generic CSV adapter options JSON")
	workerPath := flag.String("worker", "", "path to the parser-worker binary (required)")
	workerSHA := flag.String("worker-sha256", "", "reviewed worker digest to pin (computed and reported when empty)")
	jobID := flag.String("job", "", "reuse an existing job ID; a second differing import for one job is rejected by design")
	migrationsDir := flag.String("migrations",
		defaultMigrationsDir(), "directory containing the security SQL migrations")
	flag.Parse()

	if *csvPath == "" || *workerPath == "" {
		fmt.Fprintln(os.Stderr, "importctl: -csv and -worker are required")
		flag.Usage()
		os.Exit(2)
	}

	err := importcli.Run(context.Background(), importcli.Config{
		DatabaseURL:   *databaseURL,
		S3Endpoint:    *s3Endpoint,
		S3AccessKey:   *s3Access,
		S3SecretKey:   *s3Secret,
		Bucket:        *bucket,
		CSVPath:       *csvPath,
		OptionsJSON:   *optionsJSON,
		WorkerPath:    *workerPath,
		WorkerSHA256:  *workerSHA,
		JobID:         *jobID,
		MigrationsDir: *migrationsDir,
		Out:           os.Stdout,
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "importctl: %v\n", err)
		os.Exit(1)
	}
}

func envOr(name string, fallback string) string {
	if value := os.Getenv(name); value != "" {
		return value
	}
	return fallback
}

func defaultMigrationsDir() string {
	if value := os.Getenv("MEMORY_OS_MIGRATIONS_DIR"); value != "" {
		return value
	}
	return "../../infra/postgresql/security"
}
