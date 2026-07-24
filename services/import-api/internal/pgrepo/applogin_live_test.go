//go:build linux

package pgrepo

import (
	"context"
	"fmt"
	neturl "net/url"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

// appLoginPool opens a real connection as memory_app_login — the principal a
// deployment would use — instead of the migration superuser every other live
// test connects with. The password is generated per run and set through the
// admin connection, so no credential exists in the repository.
func appLoginPool(t *testing.T, ctx context.Context, admin *pgxpool.Pool, adminURL string) *pgxpool.Pool {
	t.Helper()
	// The password is the one already in the test database URL: reusing it
	// introduces no new secret, and — unlike a per-run random value — lets the
	// several test binaries that share this cluster set the same thing.
	parsed, err := neturl.Parse(adminURL)
	if err != nil {
		t.Fatal(err)
	}
	password, _ := parsed.User.Password()
	if password == "" {
		t.Skip("test database URL carries no password; skipping deployment-principal test")
	}

	// ALTER ROLE is cluster-wide, so two packages running in parallel collide
	// with "tuple concurrently updated". Serialize through the same advisory
	// lock discipline the migrations use.
	if _, err := admin.Exec(ctx, "SELECT pg_advisory_lock(730002)"); err != nil {
		t.Fatal(err)
	}
	_, alterErr := admin.Exec(ctx,
		"ALTER ROLE memory_app_login PASSWORD '"+strings.ReplaceAll(password, "'", "''")+"'")
	if _, err := admin.Exec(ctx, "SELECT pg_advisory_unlock(730002)"); err != nil {
		t.Fatal(err)
	}
	if alterErr != nil {
		t.Fatal(alterErr)
	}

	parsed.User = neturl.UserPassword("memory_app_login", password)
	pool, err := pgxpool.New(ctx, parsed.String())
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(pool.Close)
	if err := pool.Ping(ctx); err != nil {
		t.Fatalf("deployment principal could not connect: %v", err)
	}
	// Assert the connection really is the unprivileged principal. Without this,
	// repointing the URL at a superuser would silently turn every RLS proof in
	// this package back into a no-op.
	var currentUser string
	var isSuperuser, bypassesRLS bool
	if err := pool.QueryRow(ctx,
		`SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user`,
	).Scan(&currentUser, &isSuperuser, &bypassesRLS); err != nil {
		t.Fatal(err)
	}
	if currentUser != "memory_app_login" || isSuperuser || bypassesRLS {
		t.Fatalf("connected as %q (superuser=%v bypassrls=%v); the RLS proof would be vacuous",
			currentUser, isSuperuser, bypassesRLS)
	}
	return pool
}

// TestDeploymentLoginIsBoundByForceRLS closes the gap that every previous live
// test left open: FORCE RLS was proven for the NOLOGIN runtime roles, but the
// principal that actually connects was always a superuser, and a superuser
// bypasses row-level security entirely. This test connects as the deployment
// principal and proves the policies bind it.
func TestDeploymentLoginIsBoundByForceRLS(t *testing.T) {
	env := newLiveEnv(t)
	ctx := context.Background()
	repoURL := strings.Replace(os.Getenv("MEMORY_OS_TEST_DATABASE_URL"),
		"/memory_os_security", "/memory_os_pgrepo", 1)
	app := appLoginPool(t, ctx, env.pool, repoURL)
	runID := time.Now().UnixNano()

	ownerA := fmt.Sprintf("acct_login_owner_a_%d", runID)
	ownerB := fmt.Sprintf("acct_login_owner_b_%d", runID)
	for _, owner := range []string{ownerA, ownerB} {
		if err := provisionAccount(ctx, env.pool, owner, 1); err != nil {
			t.Fatal(err)
		}
		if _, err := env.pool.Exec(ctx,
			`INSERT INTO memory_os.import_job (id, owner_account_id, account_epoch, state, source_surface)
			 VALUES ($1, $2, 1, 'created', 'ios_files')`,
			"job-login-"+owner, owner); err != nil {
			t.Fatal(err)
		}
	}

	// Before any SET ROLE the connection is powerless: NOINHERIT means the
	// runtime memberships convey nothing on their own.
	var scratch int
	err := app.QueryRow(ctx, "SELECT count(*) FROM memory_os.import_job").Scan(&scratch)
	if err == nil {
		t.Fatal("the deployment principal read tenant rows without assuming a runtime role")
	}
	if !strings.Contains(err.Error(), "permission denied") {
		t.Fatalf("unexpected pre-SET ROLE error: %v", err)
	}

	// It must never be able to become the owner of the policies constraining it.
	if _, err := app.Exec(ctx, "SET ROLE memory_migration_owner"); err == nil {
		t.Fatal("the deployment principal became the migration owner")
	}

	// Scoped exactly like the runtime path: it sees its own account and nothing
	// else, which is the property a superuser connection could not have shown.
	connection, err := app.Acquire(ctx)
	if err != nil {
		t.Fatal(err)
	}
	defer connection.Release()
	tx, err := connection.Begin(ctx)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = tx.Rollback(ctx) }()

	for _, statement := range []string{
		"SET LOCAL ROLE memory_api_runtime",
		"SELECT set_config('app.current_account_id', '" + ownerA + "', true)",
		"SELECT set_config('app.current_account_epoch', '1', true)",
	} {
		if _, err := tx.Exec(ctx, statement); err != nil {
			t.Fatalf("%s: %v", statement, err)
		}
	}

	var visible int
	if err := tx.QueryRow(ctx,
		"SELECT count(*) FROM memory_os.import_job WHERE owner_account_id = $1", ownerA,
	).Scan(&visible); err != nil {
		t.Fatal(err)
	}
	if visible != 1 {
		t.Fatalf("the deployment principal saw %d of its own rows, expected 1", visible)
	}
	if err := tx.QueryRow(ctx,
		"SELECT count(*) FROM memory_os.import_job WHERE owner_account_id = $1", ownerB,
	).Scan(&visible); err != nil {
		t.Fatal(err)
	}
	if visible != 0 {
		t.Fatalf("the deployment principal saw %d foreign rows; RLS did not bind it", visible)
	}

	// It cannot write into another tenant, and it cannot disarm the policies.
	if _, err := tx.Exec(ctx,
		`INSERT INTO memory_os.import_job (id, owner_account_id, account_epoch, state, source_surface)
		 VALUES ($1, $2, 1, 'created', 'ios_files')`,
		"job-login-intrusion", ownerB); err == nil {
		t.Fatal("the deployment principal wrote into a foreign tenant")
	}
	for _, statement := range []string{
		"ALTER TABLE memory_os.import_job DISABLE ROW LEVEL SECURITY",
		"DROP POLICY import_job_tenant_select ON memory_os.import_job",
		"ALTER ROLE memory_app_login BYPASSRLS",
	} {
		if _, err := tx.Exec(ctx, statement); err == nil {
			t.Fatalf("the deployment principal executed %q", statement)
		}
		// A failed statement aborts the transaction; restart the scope for the
		// next probe rather than reporting cascade failures.
		_ = tx.Rollback(ctx)
		tx, err = connection.Begin(ctx)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := tx.Exec(ctx, "SET LOCAL ROLE memory_api_runtime"); err != nil {
			t.Fatal(err)
		}
	}
}
