package pgrepo

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"io"
	"net/http"
	neturl "net/url"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/m-shogo/memories-project/services/import-api/internal/cryptoids"
	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/objectstore"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
	"github.com/m-shogo/memories-project/services/import-api/internal/upload"
)

var (
	migrateOnce sync.Once
	migrateErr  error
)

type liveEnv struct {
	pool     *pgxpool.Pool
	executor *dbscope.Executor
	objects  *objectstore.Client
}

func newLiveEnv(t *testing.T) *liveEnv {
	t.Helper()
	databaseURL := os.Getenv("MEMORY_OS_TEST_DATABASE_URL")
	endpoint := os.Getenv("MEMORY_OS_TEST_S3_ENDPOINT")
	if databaseURL == "" || endpoint == "" {
		t.Skip("MEMORY_OS_TEST_DATABASE_URL and MEMORY_OS_TEST_S3_ENDPOINT are required; skipping runtime-role repository tests")
	}
	ctx := context.Background()

	admin, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		t.Fatal(err)
	}
	defer admin.Close()
	if _, err := admin.Exec(ctx, "CREATE DATABASE memory_os_pgrepo"); err != nil &&
		!strings.Contains(err.Error(), "already exists") {
		t.Fatal(err)
	}
	repoURL := strings.Replace(databaseURL, "/memory_os_security", "/memory_os_pgrepo", 1)
	pool, err := pgxpool.New(ctx, repoURL)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(pool.Close)

	migrateOnce.Do(func() {
		// Role DDL is cluster-wide while advisory locks are per-database, so
		// every migration applier serializes in the maintenance database.
		maintenance, err := neturl.Parse(databaseURL)
		if err != nil {
			migrateErr = err
			return
		}
		maintenance.Path = "/postgres"
		lockPool, err := pgxpool.New(ctx, maintenance.String())
		if err != nil {
			migrateErr = err
			return
		}
		defer lockPool.Close()
		lock, err := lockPool.Acquire(ctx)
		if err != nil {
			migrateErr = err
			return
		}
		defer lock.Release()
		if _, err := lock.Exec(ctx, "SELECT pg_advisory_lock(730001)"); err != nil {
			migrateErr = err
			return
		}
		defer func() { _, _ = lock.Exec(ctx, "SELECT pg_advisory_unlock(730001)") }()
		for _, name := range []string{
			"001_memory_os_import_rls.sql",
			"002_memory_os_account_control.sql",
			"002_memory_os_upload_authorization.sql",
			"003_memory_os_preview_domain.sql",
			"004_memory_os_account_session.sql",
			"005_memory_os_apply_memory.sql",
			"006_memory_os_deletion_fencing.sql",
			"007_memory_os_app_login.sql",
		} {
			payload, err := os.ReadFile(filepath.Join("..", "..", "..", "..", "infra", "postgresql", "security", name))
			if err == nil {
				_, err = pool.Exec(ctx, string(payload))
			}
			if err != nil {
				migrateErr = err
				return
			}
		}
	})
	if migrateErr != nil {
		t.Fatal(migrateErr)
	}

	access := os.Getenv("MEMORY_OS_TEST_S3_ACCESS_KEY")
	if access == "" {
		access = "minioadmin"
	}
	secret := os.Getenv("MEMORY_OS_TEST_S3_SECRET_KEY")
	if secret == "" {
		secret = "minioadmin"
	}
	objects, err := objectstore.New(objectstore.Config{
		Endpoint:        endpoint,
		Region:          "us-east-1",
		Bucket:          "memory-os-quarantine-test",
		AccessKeyID:     access,
		SecretAccessKey: secret,
	})
	if err != nil {
		t.Fatal(err)
	}
	deadline := time.Now().Add(30 * time.Second)
	for {
		if err = objects.ProvisionVersionedBucket(ctx); err == nil {
			break
		}
		if time.Now().After(deadline) {
			t.Fatalf("object store never became ready: %v", err)
		}
		time.Sleep(time.Second)
	}

	return &liveEnv{
		pool:     pool,
		executor: dbscope.New(pgscope.Beginner{Pool: pool}),
		objects:  objects,
	}
}

func (e *liveEnv) livePrincipal(t *testing.T, accountID string) security.Principal {
	t.Helper()
	principal, err := security.NewVerifiedPrincipal(accountID, 1, security.AuthorityIOSUser)
	if err != nil {
		t.Fatal(err)
	}
	if err := provisionAccount(context.Background(), e.pool, accountID, 1); err != nil {
		t.Fatal(err)
	}
	return principal
}

// provisionAccount inserts the account_control row deletion fencing requires:
// every tenant policy now demands an active account at the exact epoch. It runs
// on the pool's own connection (the dev/CI login is privileged, so RLS does not
// apply) because the API insert policy itself depends on this row existing.
func provisionAccount(ctx context.Context, pool *pgxpool.Pool, accountID string, epoch int64) error {
	_, err := pool.Exec(ctx,
		`INSERT INTO memory_os.account_control (account_id, account_epoch, state)
		 VALUES ($1, $2, 'active')
		 ON CONFLICT (account_id) DO UPDATE
		 SET account_epoch = EXCLUDED.account_epoch, state = 'active',
		     deletion_started_at = NULL, deletion_completed_at = NULL`,
		accountID, epoch)
	return err
}

func (e *liveEnv) createJob(t *testing.T, principal security.Principal) string {
	t.Helper()
	jobID, err := cryptoids.Generator{}.NewID("job")
	if err != nil {
		t.Fatal(err)
	}
	err = e.executor.WithinPrincipal(context.Background(), principal, dbscope.RoleAPI,
		func(ctx context.Context, tx dbscope.Transaction) error {
			return tx.Exec(ctx,
				`INSERT INTO memory_os.import_job (id, owner_account_id, account_epoch, state, source_surface)
				 VALUES ($1, $2, $3, 'created', 'ios_files')`,
				jobID, principal.AccountID(), principal.AccountEpoch())
		})
	if err != nil {
		t.Fatal(err)
	}
	return jobID
}

func (e *liveEnv) uploadService() upload.Service {
	return upload.Service{
		Transactions: e.executor,
		Repository:   Upload{},
		Signer:       e.objects,
		Objects:      e.objects,
		IDs:          cryptoids.Generator{},
	}
}

func TestRuntimeRoleDropsPrivilegeInsideScopedTransactions(t *testing.T) {
	env := newLiveEnv(t)
	principal := env.livePrincipal(t, "acct_pgrepo_priv_owner_a")

	err := env.executor.WithinPrincipal(context.Background(), principal, dbscope.RoleAPI,
		func(ctx context.Context, tx dbscope.Transaction) error {
			adapted, err := pgscope.From(tx)
			if err != nil {
				return err
			}
			var current string
			if err := adapted.QueryRow(ctx, "SELECT current_user").Scan(&current); err != nil {
				return err
			}
			if current != "memory_api_runtime" {
				t.Fatalf("scoped transaction runs as %q, not the runtime role", current)
			}
			// The API role has no INSERT grant on preview_ready; a privileged
			// login leaking through SET LOCAL ROLE would succeed here.
			return tx.Exec(ctx,
				`INSERT INTO memory_os.preview_ready (id) VALUES ('prv_privilege_probe')`)
		})
	var pgErr *pgconn.PgError
	if !errors.As(err, &pgErr) || pgErr.Code != "42501" {
		t.Fatalf("runtime role retained privilege: %v", err)
	}
}

func TestExecutorEnforcesTenantIsolation(t *testing.T) {
	env := newLiveEnv(t)
	ownerA := env.livePrincipal(t, "acct_pgrepo_tenant_a_01")
	ownerB := env.livePrincipal(t, "acct_pgrepo_tenant_b_01")
	jobID := env.createJob(t, ownerA)

	err := env.executor.WithinPrincipal(context.Background(), ownerA, dbscope.RoleAPI,
		func(ctx context.Context, tx dbscope.Transaction) error {
			job, err := Upload{}.GetImportJob(ctx, tx, jobID)
			if err != nil {
				return err
			}
			if job.OwnerAccountID != ownerA.AccountID() || job.Status != "created" {
				t.Fatalf("unexpected job for its owner: %+v", job)
			}
			return nil
		})
	if err != nil {
		t.Fatal(err)
	}

	err = env.executor.WithinPrincipal(context.Background(), ownerB, dbscope.RoleAPI,
		func(ctx context.Context, tx dbscope.Transaction) error {
			_, err := Upload{}.GetImportJob(ctx, tx, jobID)
			return err
		})
	if !errors.Is(err, ErrNotFound) {
		t.Fatalf("cross-tenant job was visible: %v", err)
	}
}

func TestUploadServiceEndToEndThroughRuntimeRoles(t *testing.T) {
	env := newLiveEnv(t)
	owner := env.livePrincipal(t, "acct_pgrepo_upload_a_01")
	intruder := env.livePrincipal(t, "acct_pgrepo_upload_b_01")
	jobID := env.createJob(t, owner)
	service := env.uploadService()
	ctx := context.Background()

	payload := []byte("title,date\nkyoto trip,2026-07-21\n")
	digest := sha256.Sum256(payload)
	response, err := service.Issue(ctx, owner, upload.IssueRequest{
		JobID:           jobID,
		ContentLength:   int64(len(payload)),
		ChecksumSHA256:  hex.EncodeToString(digest[:]),
		ContentType:     "text/csv",
		SourceSurface:   "ios_files",
		DisplayFilename: "trip.csv",
	})
	if err != nil {
		t.Fatal(err)
	}

	request, err := http.NewRequest(http.MethodPut, response.UploadURL, bytes.NewReader(payload))
	if err != nil {
		t.Fatal(err)
	}
	request.ContentLength = int64(len(payload))
	for name, value := range response.RequiredHeaders {
		if name != "Content-Length" {
			request.Header.Set(name, value)
		}
	}
	put, err := http.DefaultClient.Do(request)
	if err != nil {
		t.Fatal(err)
	}
	_, _ = io.Copy(io.Discard, put.Body)
	_ = put.Body.Close()
	if put.StatusCode != http.StatusOK {
		t.Fatalf("presigned upload status %d", put.StatusCode)
	}

	// A foreign tenant cannot complete the authorization: under FORCE RLS it
	// simply does not exist for them.
	if err := service.Complete(ctx, intruder, response.AuthorizationID); !errors.Is(err, upload.ErrUploadAuthorizationNotFound) {
		t.Fatalf("cross-tenant completion was accepted: %v", err)
	}

	if err := service.Complete(ctx, owner, response.AuthorizationID); err != nil {
		t.Fatal(err)
	}

	// The authorization is consumed and the scan ticket is enqueued with the
	// exact verified object version, all visible only inside the owner scope.
	err = env.executor.WithinPrincipal(ctx, owner, dbscope.RoleAPI,
		func(ctx context.Context, tx dbscope.Transaction) error {
			authorization, err := Upload{}.GetAuthorization(ctx, tx, response.AuthorizationID)
			if err != nil {
				return err
			}
			if authorization.Status != "consumed" || authorization.DisplayFilename != "trip.csv" {
				t.Fatalf("authorization not consumed with metadata intact: %+v", authorization)
			}
			adapted, err := pgscope.From(tx)
			if err != nil {
				return err
			}
			var state string
			var versionID string
			if err := adapted.QueryRow(ctx,
				`SELECT state, safe_metadata->>'objectVersionId'
				 FROM memory_os.quarantine_object WHERE id = $1`,
				response.AuthorizationID).Scan(&state, &versionID); err != nil {
				return err
			}
			if state != "scan_pending" || versionID == "" {
				t.Fatalf("scan ticket not enqueued with an object version: state=%s version=%q", state, versionID)
			}
			return nil
		})
	if err != nil {
		t.Fatal(err)
	}

	if err := service.Complete(ctx, owner, response.AuthorizationID); !errors.Is(err, upload.ErrUploadAuthorizationConsumed) {
		t.Fatalf("second completion was accepted: %v", err)
	}
}

func TestRepositoriesRejectForeignTransactions(t *testing.T) {
	if _, err := (Upload{}).GetImportJob(context.Background(), foreignTransaction{}, "job_x"); !errors.Is(err, pgscope.ErrForeignTransaction) {
		t.Fatalf("foreign transaction was accepted: %v", err)
	}
}

type foreignTransaction struct{}

func (foreignTransaction) Exec(context.Context, string, ...any) error { return nil }
func (foreignTransaction) Commit() error                              { return nil }
func (foreignTransaction) Rollback() error                            { return nil }
