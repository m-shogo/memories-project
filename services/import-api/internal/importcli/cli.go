// Package importcli is the development harness behind cmd/importctl: the
// first visible end-to-end run of the supervised import flow. It provisions
// the dev database and bucket, uploads one local CSV through the real
// presigned-PUT binding, runs internal/importflow with a digest-pinned worker
// binary, and prints the committed Preview to the terminal.
//
// It is a local development tool, not a server: it assumes the
// scripts/dev-up.sh stack (or CI service containers), connects as the stack's
// superuser, and must never be pointed at production infrastructure.
package importcli

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/m-shogo/memories-project/services/import-api/internal/adapters/genericcsv"
	"github.com/m-shogo/memories-project/services/import-api/internal/cryptoids"
	"github.com/m-shogo/memories-project/services/import-api/internal/csvworker"
	"github.com/m-shogo/memories-project/services/import-api/internal/importflow"
	"github.com/m-shogo/memories-project/services/import-api/internal/objectstore"
	"github.com/m-shogo/memories-project/services/import-api/internal/parsersup"
	"github.com/m-shogo/memories-project/services/import-api/internal/previewcommit"
	"github.com/m-shogo/memories-project/services/import-api/internal/previewspool"
	"github.com/m-shogo/memories-project/services/import-api/internal/upload"
)

var ErrInvalidConfig = errors.New("invalid importctl configuration")

// maintenanceURL points the connection at the always-present postgres
// database, giving every migration applier one shared advisory-lock scope.
func maintenanceURL(databaseURL string) (string, error) {
	parsed, err := url.Parse(databaseURL)
	if err != nil {
		return "", err
	}
	parsed.Path = "/postgres"
	return parsed.String(), nil
}

// migrationAdvisoryLock serializes cluster-wide role DDL with the test
// suites, which share the same PostgreSQL cluster on the dev stack.
const migrationAdvisoryLock = 730001

type Config struct {
	DatabaseURL string
	S3Endpoint  string
	S3AccessKey string
	S3SecretKey string
	Bucket      string

	CSVPath     string
	OptionsJSON string

	WorkerPath   string
	WorkerSHA256 string // optional: computed and reported when empty

	JobID string // optional: reuse an existing job to demonstrate idempotency

	MigrationsDir string
	Out           io.Writer

	// ExtraWorkerEnv exists for the test harness (worker-mode dispatch); the
	// production CLI leaves it empty.
	ExtraWorkerEnv []string
}

// Run executes one import end to end and prints the committed Preview.
func Run(ctx context.Context, config Config) error {
	if config.Out == nil {
		config.Out = os.Stdout
	}
	out := config.Out
	if config.DatabaseURL == "" || config.S3Endpoint == "" || config.CSVPath == "" ||
		config.WorkerPath == "" || config.Bucket == "" || config.MigrationsDir == "" {
		return fmt.Errorf("%w: database URL, S3 endpoint, bucket, CSV path, worker path and migrations dir are required", ErrInvalidConfig)
	}
	if config.OptionsJSON == "" {
		return fmt.Errorf("%w: adapter options JSON is required", ErrInvalidConfig)
	}

	// Worker artifact digest. Production pins a reviewed digest; the dev
	// harness computes one when omitted and says so.
	workerDigest, err := fileSHA256(config.WorkerPath)
	if err != nil {
		return fmt.Errorf("hash worker binary: %w", err)
	}
	if config.WorkerSHA256 == "" {
		fmt.Fprintf(out, "worker digest (computed, NOT a reviewed pin): %s\n", workerDigest)
		config.WorkerSHA256 = workerDigest
	} else if config.WorkerSHA256 != workerDigest {
		return fmt.Errorf("worker binary does not match the pinned digest: have %s want %s", workerDigest, config.WorkerSHA256)
	}

	// Adapter options are digest-bound exactly as production binds them.
	parserOptions, err := csvworker.ParserOptions(config.OptionsJSON)
	if err != nil {
		return err
	}
	_, optionsDigest, err := genericcsv.NormalizeAndDigestOptions(parserOptions)
	if err != nil {
		return err
	}

	source, err := os.ReadFile(config.CSVPath)
	if err != nil {
		return fmt.Errorf("read CSV source: %w", err)
	}
	if len(source) == 0 {
		return errors.New("CSV source is empty")
	}
	sourceDigest := sha256.Sum256(source)
	sourceChecksum := hex.EncodeToString(sourceDigest[:])

	pool, err := pgxpool.New(ctx, config.DatabaseURL)
	if err != nil {
		return err
	}
	defer pool.Close()
	if err := applyMigrations(ctx, pool, config.DatabaseURL, config.MigrationsDir); err != nil {
		return err
	}

	ids := cryptoids.Generator{}
	jobID, ownerID, accountEpoch, err := ensureJob(ctx, pool, ids, config.JobID)
	if err != nil {
		return err
	}
	fmt.Fprintf(out, "job: %s (owner %s, epoch %d)\n", jobID, ownerID, accountEpoch)

	objects, err := objectstore.New(objectstore.Config{
		Endpoint:        config.S3Endpoint,
		Region:          "us-east-1",
		Bucket:          config.Bucket,
		AccessKeyID:     config.S3AccessKey,
		SecretAccessKey: config.S3SecretKey,
	})
	if err != nil {
		return err
	}
	if err := objects.ProvisionVersionedBucket(ctx); err != nil {
		return err
	}

	uploadID, err := ids.NewID("upl")
	if err != nil {
		return err
	}
	binding, err := uploadSource(ctx, objects, jobID, uploadID, source, sourceChecksum)
	if err != nil {
		return err
	}
	fmt.Fprintf(out, "uploaded: %s (version %s, %d bytes)\n", binding.ObjectKey, binding.ObjectVersionID, binding.ContentLength)

	supervisor, err := parsersup.NewSupervisor(parsersup.Config{
		WorkerPath:   config.WorkerPath,
		WorkerSHA256: config.WorkerSHA256,
		WorkerEnv: append([]string{
			csvworker.OptionsEnv + "=" + config.OptionsJSON,
		}, config.ExtraWorkerEnv...),
		Limits: parsersup.Limits{
			AddressSpaceBytes: 4 << 30,
			CPUSeconds:        60,
			OpenFiles:         64,
			OutputBytes:       600 * 1024 * 1024,
			WallClock:         10 * time.Minute,
		},
	})
	if err != nil {
		return err
	}

	spoolRoot := filepath.Join(os.TempDir(), "memory-os-spool")
	if err := os.MkdirAll(spoolRoot, 0o700); err != nil {
		return err
	}
	if err := os.Chmod(spoolRoot, 0o700); err != nil {
		return err
	}
	manager, err := previewspool.OpenManager(spoolRoot)
	if err != nil {
		return err
	}
	defer manager.Close()

	committer, err := previewcommit.NewCommitter(pool)
	if err != nil {
		return err
	}

	spoolID, err := ids.NewID("spl")
	if err != nil {
		return err
	}
	previewID, err := ids.NewID("prv")
	if err != nil {
		return err
	}
	now := time.Now().UTC()
	flow := &importflow.Flow{
		Objects:    objects,
		Supervisor: supervisor,
		Spool:      manager,
		Committer:  committer,
		ScratchDir: os.TempDir(),
	}
	result, err := flow.Run(ctx, importflow.Request{
		SpoolID:   spoolID,
		PreviewID: previewID,
		Seal: previewspool.SealInput{
			JobID:          jobID,
			OwnerAccountID: ownerID,
			AccountEpoch:   accountEpoch,
			Source:         binding,
			Adapter: previewspool.SealAdapterBinding{
				AdapterID:      "generic-csv",
				AdapterVersion: "1.0.0",
				ArtifactSHA256: config.WorkerSHA256,
			},
			OptionsSHA256: optionsDigest,
			CreatedAt:     now,
			ExpiresAt:     now.Add(time.Hour),
		},
	}, now)
	if err != nil {
		return err
	}

	return printPreview(ctx, pool, out, result)
}

func fileSHA256(path string) (string, error) {
	file, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer file.Close()
	hasher := sha256.New()
	if _, err := io.Copy(hasher, file); err != nil {
		return "", err
	}
	return hex.EncodeToString(hasher.Sum(nil)), nil
}

// applyMigrations serializes on an advisory lock held in the cluster's
// maintenance database: role and grant DDL touches shared catalogs, and
// PostgreSQL advisory locks are scoped per database, so appliers targeting
// different databases would otherwise race each other.
func applyMigrations(ctx context.Context, pool *pgxpool.Pool, databaseURL string, dir string) error {
	lockURL, err := maintenanceURL(databaseURL)
	if err != nil {
		return err
	}
	lock, err := pgx.Connect(ctx, lockURL)
	if err != nil {
		return fmt.Errorf("connect for migration lock: %w", err)
	}
	defer lock.Close(ctx)
	if _, err := lock.Exec(ctx, "SELECT pg_advisory_lock($1)", migrationAdvisoryLock); err != nil {
		return err
	}
	defer func() { _, _ = lock.Exec(ctx, "SELECT pg_advisory_unlock($1)", migrationAdvisoryLock) }()
	for _, name := range []string{
		"001_memory_os_import_rls.sql",
		"002_memory_os_upload_authorization.sql",
		"003_memory_os_preview_domain.sql",
	} {
		payload, err := os.ReadFile(filepath.Join(dir, name))
		if err != nil {
			return err
		}
		if _, err := pool.Exec(ctx, string(payload)); err != nil {
			return fmt.Errorf("apply %s: %w", name, err)
		}
	}
	return nil
}

func ensureJob(ctx context.Context, pool *pgxpool.Pool, ids cryptoids.Generator, jobID string) (string, string, int64, error) {
	if jobID != "" {
		var owner string
		var epoch int64
		err := pool.QueryRow(ctx,
			"SELECT owner_account_id, account_epoch FROM memory_os.import_job WHERE id = $1", jobID,
		).Scan(&owner, &epoch)
		if err == nil {
			return jobID, owner, epoch, nil
		}
		if !errors.Is(err, pgx.ErrNoRows) {
			return "", "", 0, err
		}
	} else {
		generated, err := ids.NewID("job")
		if err != nil {
			return "", "", 0, err
		}
		jobID = generated
	}
	ownerID, err := ids.NewID("acct")
	if err != nil {
		return "", "", 0, err
	}
	const epoch = int64(1)
	if _, err := pool.Exec(ctx,
		`INSERT INTO memory_os.import_job (id, owner_account_id, account_epoch, state, source_surface)
		 VALUES ($1, $2, $3, 'preview_building', 'ios_files')`,
		jobID, ownerID, epoch); err != nil {
		return "", "", 0, err
	}
	return jobID, ownerID, epoch, nil
}

func uploadSource(ctx context.Context, objects *objectstore.Client, jobID string, uploadID string, source []byte, checksum string) (previewspool.SealSourceBinding, error) {
	key := "quarantine/" + jobID + "/" + uploadID
	presigned, err := objects.PresignPut(ctx, upload.PresignRequest{
		ObjectKey:      key,
		ContentLength:  int64(len(source)),
		ChecksumSHA256: checksum,
		ContentType:    "text/csv",
		ExpiresAt:      time.Now().Add(5 * time.Minute),
	})
	if err != nil {
		return previewspool.SealSourceBinding{}, err
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodPut, presigned.URL, bytes.NewReader(source))
	if err != nil {
		return previewspool.SealSourceBinding{}, err
	}
	request.ContentLength = int64(len(source))
	for name, value := range presigned.RequiredHeaders {
		if name != "Content-Length" {
			request.Header.Set(name, value)
		}
	}
	response, err := http.DefaultClient.Do(request)
	if err != nil {
		return previewspool.SealSourceBinding{}, err
	}
	_, _ = io.Copy(io.Discard, response.Body)
	_ = response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return previewspool.SealSourceBinding{}, fmt.Errorf("presigned upload status %d", response.StatusCode)
	}
	metadata, err := objects.HeadObject(ctx, key)
	if err != nil {
		return previewspool.SealSourceBinding{}, err
	}
	return previewspool.SealSourceBinding{
		ObjectKey:       key,
		ObjectVersionID: metadata.VersionID,
		ContentLength:   int64(len(source)),
		ChecksumSHA256:  checksum,
	}, nil
}

// printPreview reads the committed Preview back with the dev stack's
// superuser connection (RLS does not apply to superusers) and renders it.
func printPreview(ctx context.Context, pool *pgxpool.Pool, out io.Writer, result importflow.Result) error {
	commit := result.Commit
	if commit.AlreadyCommitted {
		fmt.Fprintf(out, "\nidempotent retry: this source was already committed as %s\n", commit.PreviewID)
	}
	fmt.Fprintf(out, "\npreview:     %s\n", commit.PreviewID)
	fmt.Fprintf(out, "commit key:  %s\n", commit.CommitKey)
	fmt.Fprintf(out, "accepted:    %d records (%d bytes, sha256 %s)\n",
		result.Verified.Evidence.Accepted.RecordCount,
		result.Verified.Evidence.Accepted.ByteLength,
		result.Verified.Evidence.Accepted.SHA256[:16]+"…")
	fmt.Fprintf(out, "rejected:    %d records\n", result.Verified.Evidence.Rejected.RecordCount)

	rows, err := pool.Query(ctx, `
		SELECT ordinal, source_row, canonical_record->>'title',
		       COALESCE(canonical_record->>'occurredAt',''), COALESCE(canonical_record->>'url','')
		FROM memory_os.preview_candidate WHERE preview_id = $1 ORDER BY ordinal`, commit.PreviewID)
	if err != nil {
		return err
	}
	defer rows.Close()
	fmt.Fprintf(out, "\ncandidates:\n")
	for rows.Next() {
		var ordinal, sourceRow int64
		var title, occurredAt, url string
		if err := rows.Scan(&ordinal, &sourceRow, &title, &occurredAt, &url); err != nil {
			return err
		}
		fmt.Fprintf(out, "  %3d (row %d)  %-30s %-22s %s\n", ordinal, sourceRow, clip(title, 30), occurredAt, clip(url, 40))
	}
	if err := rows.Err(); err != nil {
		return err
	}

	rejectionRows, err := pool.Query(ctx, `
		SELECT ordinal, source_row, array_to_string(issue_codes, ',')
		FROM memory_os.preview_rejection WHERE preview_id = $1 ORDER BY ordinal`, commit.PreviewID)
	if err != nil {
		return err
	}
	defer rejectionRows.Close()
	fmt.Fprintf(out, "rejections:\n")
	for rejectionRows.Next() {
		var ordinal, sourceRow int64
		var codes string
		if err := rejectionRows.Scan(&ordinal, &sourceRow, &codes); err != nil {
			return err
		}
		fmt.Fprintf(out, "  %3d (row %d)  %s\n", ordinal, sourceRow, codes)
	}
	if err := rejectionRows.Err(); err != nil {
		return err
	}

	var jobState string
	if err := pool.QueryRow(ctx,
		"SELECT state FROM memory_os.import_job WHERE id = (SELECT job_id FROM memory_os.preview_ready WHERE id = $1)",
		commit.PreviewID).Scan(&jobState); err != nil {
		return err
	}
	fmt.Fprintf(out, "\njob state:   %s\n", jobState)
	return nil
}

func clip(value string, limit int) string {
	runes := []rune(value)
	if len(runes) <= limit {
		return value
	}
	return string(runes[:limit-1]) + "…"
}
