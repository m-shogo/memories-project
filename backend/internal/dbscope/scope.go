package dbscope

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	"github.com/m-shogo/memories-project/backend/internal/security"
)

var (
	ErrInvalidRole = errors.New("invalid database privilege role")
	ErrNilHandler  = errors.New("tenant transaction handler is nil")
)

type Role string

const (
	RoleAPI      Role = "memory_api_runtime"
	RoleWorker   Role = "memory_worker_runtime"
	RoleDeletion Role = "memory_deletion_runtime"
)

func (r Role) validate() error {
	switch r {
	case RoleAPI, RoleWorker, RoleDeletion:
		return nil
	default:
		return ErrInvalidRole
	}
}

// Beginner is satisfied by *sql.DB and enables deterministic transaction tests.
type Beginner interface {
	BeginTx(ctx context.Context, opts *sql.TxOptions) (*sql.Tx, error)
}

type Runner struct {
	db Beginner
}

func New(db Beginner) (*Runner, error) {
	if db == nil {
		return nil, errors.New("database beginner is nil")
	}
	return &Runner{db: db}, nil
}

// WithinTenant starts a transaction, installs verified tenant context using
// transaction-local PostgreSQL settings, switches to a fixed privilege role,
// executes fn, and commits only on success.
func (r *Runner) WithinTenant(
	ctx context.Context,
	principal security.Principal,
	role Role,
	fn func(context.Context, *sql.Tx) error,
) error {
	if err := principal.Validate(); err != nil {
		return fmt.Errorf("validate principal: %w", err)
	}
	if err := role.validate(); err != nil {
		return err
	}
	if fn == nil {
		return ErrNilHandler
	}

	tx, err := r.db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelReadCommitted})
	if err != nil {
		return fmt.Errorf("begin tenant transaction: %w", err)
	}
	committed := false
	defer func() {
		if !committed {
			_ = tx.Rollback()
		}
	}()

	if _, err := tx.ExecContext(
		ctx,
		`SELECT set_config('app.current_account_id', $1, true), set_config('app.current_account_epoch', $2, true)`,
		principal.AccountID(),
		fmt.Sprintf("%d", principal.Epoch()),
	); err != nil {
		return fmt.Errorf("set tenant context: %w", err)
	}

	// Role cannot be a bind parameter. The value is safe because Role.validate
	// accepts only compile-time constants.
	if _, err := tx.ExecContext(ctx, "SET LOCAL ROLE "+string(role)); err != nil {
		return fmt.Errorf("set tenant role: %w", err)
	}

	if err := fn(ctx, tx); err != nil {
		return err
	}
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit tenant transaction: %w", err)
	}
	committed = true
	return nil
}
