package dbscope

import (
	"context"
	"database/sql"
)

// SQLBeginner adapts database/sql without selecting a concrete PostgreSQL
// driver. The executable service will provide the driver at composition time.
type SQLBeginner struct {
	DB *sql.DB
}

func (b SQLBeginner) Begin(ctx context.Context) (Transaction, error) {
	tx, err := b.DB.BeginTx(ctx, &sql.TxOptions{})
	if err != nil {
		return nil, err
	}
	return &sqlTransaction{tx: tx}, nil
}

type sqlTransaction struct {
	tx *sql.Tx
}

func (t *sqlTransaction) Exec(ctx context.Context, query string, args ...any) error {
	_, err := t.tx.ExecContext(ctx, query, args...)
	return err
}

func (t *sqlTransaction) Commit() error   { return t.tx.Commit() }
func (t *sqlTransaction) Rollback() error { return t.tx.Rollback() }
