// Package pgscope adapts a pgx connection pool to the dbscope scoped-executor
// contract. Every transaction dbscope opens through this adapter runs SET
// LOCAL ROLE to a fixed NOLOGIN/NOINHERIT/NOBYPASSRLS runtime role before any
// repository statement, so FORCE row-level security binds every query even
// when the login user is privileged. Repositories obtain query capability by
// asserting to *pgscope.Tx; wiring a different executor is a composition
// error surfaced as ErrForeignTransaction, never silent degraded access.
package pgscope

import (
	"context"
	"errors"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
)

var (
	ErrNilPool            = errors.New("pgscope requires a connection pool")
	ErrForeignTransaction = errors.New("repository received a transaction from a different executor")
)

type Beginner struct {
	Pool *pgxpool.Pool
}

func (b Beginner) Begin(ctx context.Context) (dbscope.Transaction, error) {
	if b.Pool == nil {
		return nil, ErrNilPool
	}
	tx, err := b.Pool.BeginTx(ctx, pgx.TxOptions{})
	if err != nil {
		return nil, err
	}
	return &Tx{tx: tx}, nil
}

// Tx satisfies dbscope.Transaction and additionally exposes the query surface
// concrete repositories need. It stays a thin wrapper: role and account
// context are owned by dbscope.Executor, commit/rollback by the executor's
// lifecycle, and repositories only read and write rows.
type Tx struct {
	tx pgx.Tx
}

func (t *Tx) Exec(ctx context.Context, query string, args ...any) error {
	_, err := t.tx.Exec(ctx, query, args...)
	return err
}

func (t *Tx) Commit() error   { return t.tx.Commit(context.Background()) }
func (t *Tx) Rollback() error { return t.tx.Rollback(context.Background()) }

func (t *Tx) ExecTag(ctx context.Context, query string, args ...any) (pgconn.CommandTag, error) {
	return t.tx.Exec(ctx, query, args...)
}

func (t *Tx) Query(ctx context.Context, query string, args ...any) (pgx.Rows, error) {
	return t.tx.Query(ctx, query, args...)
}

func (t *Tx) QueryRow(ctx context.Context, query string, args ...any) pgx.Row {
	return t.tx.QueryRow(ctx, query, args...)
}

// From asserts a dbscope.Transaction back to this adapter's transaction.
func From(tx dbscope.Transaction) (*Tx, error) {
	adapted, ok := tx.(*Tx)
	if !ok || adapted == nil {
		return nil, ErrForeignTransaction
	}
	return adapted, nil
}
