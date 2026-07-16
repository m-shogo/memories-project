package dbscope

import (
	"context"
	"errors"
	"reflect"
	"testing"

	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

type recordedCommand struct {
	query string
	args  []any
}

type fakeTx struct {
	commands   []recordedCommand
	committed  bool
	rolledBack bool
	execError  error
}

func (t *fakeTx) Exec(_ context.Context, query string, args ...any) error {
	t.commands = append(t.commands, recordedCommand{query: query, args: args})
	return t.execError
}
func (t *fakeTx) Commit() error   { t.committed = true; return nil }
func (t *fakeTx) Rollback() error { t.rolledBack = true; return nil }

type fakeBeginner struct{ tx *fakeTx }

func (b fakeBeginner) Begin(context.Context) (Transaction, error) { return b.tx, nil }

func TestWithinPrincipalSetsRoleAndTransactionLocalContext(t *testing.T) {
	principal, err := security.NewVerifiedPrincipal("acct_01J00000000000000000000000", 7, security.AuthorityIOSUser)
	if err != nil {
		t.Fatal(err)
	}
	tx := &fakeTx{}
	executor := New(fakeBeginner{tx: tx})
	called := false
	if err := executor.WithinPrincipal(context.Background(), principal, RoleAPI, func(_ context.Context, _ Transaction) error {
		called = true
		return nil
	}); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !called || !tx.committed || tx.rolledBack {
		t.Fatalf("unexpected transaction state: called=%v committed=%v rolledBack=%v", called, tx.committed, tx.rolledBack)
	}
	got := tx.commands
	want := []recordedCommand{
		{query: "SET LOCAL ROLE memory_api_runtime"},
		{query: "SELECT set_config('app.current_account_id', $1, true)", args: []any{"acct_01J00000000000000000000000"}},
		{query: "SELECT set_config('app.current_account_epoch', $1, true)", args: []any{"7"}},
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("commands mismatch\n got: %#v\nwant: %#v", got, want)
	}
}

func TestWithinPrincipalRollsBackCallbackFailure(t *testing.T) {
	principal, _ := security.NewVerifiedPrincipal("acct_01J00000000000000000000000", 7, security.AuthorityIOSUser)
	tx := &fakeTx{}
	expected := errors.New("boom")
	err := New(fakeBeginner{tx: tx}).WithinPrincipal(context.Background(), principal, RoleAPI, func(context.Context, Transaction) error {
		return expected
	})
	if !errors.Is(err, expected) || !tx.rolledBack || tx.committed {
		t.Fatalf("unexpected result: err=%v committed=%v rolledBack=%v", err, tx.committed, tx.rolledBack)
	}
}

func TestWithinPrincipalRejectsUnknownRoleBeforeBegin(t *testing.T) {
	principal, _ := security.NewVerifiedPrincipal("acct_01J00000000000000000000000", 7, security.AuthorityIOSUser)
	tx := &fakeTx{}
	err := New(fakeBeginner{tx: tx}).WithinPrincipal(context.Background(), principal, Role("user_supplied_role"), func(context.Context, Transaction) error { return nil })
	if !errors.Is(err, ErrInvalidRole) {
		t.Fatalf("expected invalid role, got %v", err)
	}
	if len(tx.commands) != 0 {
		t.Fatalf("unexpected commands: %#v", tx.commands)
	}
}
