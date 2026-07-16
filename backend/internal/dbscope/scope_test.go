package dbscope

import (
	"context"
	"database/sql"
	"database/sql/driver"
	"errors"
	"fmt"
	"io"
	"strings"
	"sync"
	"sync/atomic"
	"testing"

	"github.com/m-shogo/memories-project/backend/internal/security"
)

var fakeDriverCounter atomic.Int64

type recorder struct {
	mu     sync.Mutex
	events []string
}

func (r *recorder) add(event string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.events = append(r.events, event)
}

func (r *recorder) snapshot() []string {
	r.mu.Lock()
	defer r.mu.Unlock()
	return append([]string(nil), r.events...)
}

type recordingDriver struct{ recorder *recorder }

func (d recordingDriver) Open(string) (driver.Conn, error) {
	return &recordingConn{recorder: d.recorder}, nil
}

type recordingConn struct{ recorder *recorder }

func (c *recordingConn) Prepare(string) (driver.Stmt, error) { return nil, errors.New("prepare not supported") }
func (c *recordingConn) Close() error                        { return nil }
func (c *recordingConn) Begin() (driver.Tx, error)           { return c.BeginTx(context.Background(), driver.TxOptions{}) }

func (c *recordingConn) BeginTx(_ context.Context, _ driver.TxOptions) (driver.Tx, error) {
	c.recorder.add("BEGIN")
	return &recordingTx{recorder: c.recorder}, nil
}

func (c *recordingConn) ExecContext(_ context.Context, query string, args []driver.NamedValue) (driver.Result, error) {
	normalized := strings.Join(strings.Fields(query), " ")
	if len(args) > 0 {
		normalized += fmt.Sprintf(" args=%v", args)
	}
	c.recorder.add(normalized)
	return driver.RowsAffected(1), nil
}

func (c *recordingConn) Query(string, []driver.Value) (driver.Rows, error) {
	return nil, io.EOF
}

type recordingTx struct{ recorder *recorder }

func (tx *recordingTx) Commit() error {
	tx.recorder.add("COMMIT")
	return nil
}

func (tx *recordingTx) Rollback() error {
	tx.recorder.add("ROLLBACK")
	return nil
}

func openRecordingDB(t *testing.T) (*sql.DB, *recorder) {
	t.Helper()
	rec := &recorder{}
	name := fmt.Sprintf("memory-os-recording-%d", fakeDriverCounter.Add(1))
	sql.Register(name, recordingDriver{recorder: rec})
	db, err := sql.Open(name, "")
	if err != nil {
		t.Fatalf("sql.Open() error = %v", err)
	}
	t.Cleanup(func() { _ = db.Close() })
	return db, rec
}

func verifiedPrincipal(t *testing.T) security.Principal {
	t.Helper()
	principal, err := security.NewVerifiedPrincipal(
		"acct_01J00000000000000000000000",
		7,
		"https://appleid.apple.com",
		"apple-subject-001",
	)
	if err != nil {
		t.Fatalf("NewVerifiedPrincipal() error = %v", err)
	}
	return principal
}

func TestWithinTenantSetsContextAndRoleBeforeHandler(t *testing.T) {
	t.Parallel()

	db, rec := openRecordingDB(t)
	runner, err := New(db)
	if err != nil {
		t.Fatalf("New() error = %v", err)
	}

	err = runner.WithinTenant(context.Background(), verifiedPrincipal(t), RoleAPI, func(ctx context.Context, tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, "SELECT tenant_visible_row")
		return err
	})
	if err != nil {
		t.Fatalf("WithinTenant() error = %v", err)
	}

	events := rec.snapshot()
	if len(events) != 5 {
		t.Fatalf("events = %#v", events)
	}
	if events[0] != "BEGIN" {
		t.Fatalf("first event = %q", events[0])
	}
	if !strings.HasPrefix(events[1], "SELECT set_config('app.current_account_id'") {
		t.Fatalf("tenant context was not set first: %#v", events)
	}
	if events[2] != "SET LOCAL ROLE memory_api_runtime" {
		t.Fatalf("role event = %q", events[2])
	}
	if events[3] != "SELECT tenant_visible_row" || events[4] != "COMMIT" {
		t.Fatalf("unexpected handler/commit order: %#v", events)
	}
}

func TestWithinTenantRollsBackOnHandlerFailure(t *testing.T) {
	t.Parallel()

	db, rec := openRecordingDB(t)
	runner, err := New(db)
	if err != nil {
		t.Fatalf("New() error = %v", err)
	}
	want := errors.New("handler failed")

	err = runner.WithinTenant(context.Background(), verifiedPrincipal(t), RoleWorker, func(context.Context, *sql.Tx) error {
		return want
	})
	if !errors.Is(err, want) {
		t.Fatalf("WithinTenant() error = %v, want %v", err, want)
	}

	events := rec.snapshot()
	if events[len(events)-1] != "ROLLBACK" {
		t.Fatalf("last event = %q, events=%#v", events[len(events)-1], events)
	}
}

func TestWithinTenantRejectsUnverifiedPrincipalBeforeBegin(t *testing.T) {
	t.Parallel()

	db, rec := openRecordingDB(t)
	runner, err := New(db)
	if err != nil {
		t.Fatalf("New() error = %v", err)
	}

	err = runner.WithinTenant(context.Background(), security.Principal{}, RoleAPI, func(context.Context, *sql.Tx) error {
		return nil
	})
	if !errors.Is(err, security.ErrUnverifiedPrincipal) {
		t.Fatalf("WithinTenant() error = %v", err)
	}
	if events := rec.snapshot(); len(events) != 0 {
		t.Fatalf("database was touched for unverified principal: %#v", events)
	}
}

func TestWithinTenantRejectsUnknownRole(t *testing.T) {
	t.Parallel()

	db, rec := openRecordingDB(t)
	runner, err := New(db)
	if err != nil {
		t.Fatalf("New() error = %v", err)
	}

	err = runner.WithinTenant(context.Background(), verifiedPrincipal(t), Role("memory_superuser"), func(context.Context, *sql.Tx) error {
		return nil
	})
	if !errors.Is(err, ErrInvalidRole) {
		t.Fatalf("WithinTenant() error = %v", err)
	}
	if events := rec.snapshot(); len(events) != 0 {
		t.Fatalf("database was touched for invalid role: %#v", events)
	}
}
