package dbscope

import (
	"context"
	"errors"
	"fmt"
	"strconv"

	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

// Role is a fixed PostgreSQL privilege role. It must never be built from a
// request string because SET ROLE cannot safely use ordinary query parameters.
type Role string

const (
	RoleAPI      Role = "memory_api_runtime"
	RoleWorker   Role = "memory_worker_runtime"
	RoleDeletion Role = "memory_deletion_runtime"
)

var ErrInvalidRole = errors.New("invalid PostgreSQL scoped role")

// Transaction is the minimum capability needed by scoped repositories.
// Application handlers should receive domain repositories, not raw SQL access.
type Transaction interface {
	Exec(context.Context, string, ...any) error
	Commit() error
	Rollback() error
}

type Beginner interface {
	Begin(context.Context) (Transaction, error)
}

type Executor struct {
	beginner Beginner
}

func New(beginner Beginner) *Executor {
	return &Executor{beginner: beginner}
}

func (e *Executor) WithinPrincipal(
	ctx context.Context,
	principal security.Principal,
	role Role,
	fn func(context.Context, Transaction) error,
) (err error) {
	if err := principal.Validate(); err != nil {
		return fmt.Errorf("invalid verified principal: %w", err)
	}
	roleSQL, err := roleStatement(role)
	if err != nil {
		return err
	}

	tx, err := e.beginner.Begin(ctx)
	if err != nil {
		return fmt.Errorf("begin scoped transaction: %w", err)
	}
	committed := false
	defer func() {
		if recovered := recover(); recovered != nil {
			_ = tx.Rollback()
			panic(recovered)
		}
		if !committed {
			_ = tx.Rollback()
		}
	}()

	// Role names are selected only from the fixed allowlist above. Account
	// values use set_config parameters and are transaction-local.
	if err := tx.Exec(ctx, roleSQL); err != nil {
		return fmt.Errorf("set scoped role: %w", err)
	}
	if err := tx.Exec(ctx,
		"SELECT set_config('app.current_account_id', $1, true)",
		principal.AccountID(),
	); err != nil {
		return fmt.Errorf("set account context: %w", err)
	}
	if err := tx.Exec(ctx,
		"SELECT set_config('app.current_account_epoch', $1, true)",
		strconv.FormatInt(principal.AccountEpoch(), 10),
	); err != nil {
		return fmt.Errorf("set account epoch context: %w", err)
	}

	if err := fn(ctx, tx); err != nil {
		return err
	}
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit scoped transaction: %w", err)
	}
	committed = true
	return nil
}

func roleStatement(role Role) (string, error) {
	switch role {
	case RoleAPI:
		return "SET LOCAL ROLE memory_api_runtime", nil
	case RoleWorker:
		return "SET LOCAL ROLE memory_worker_runtime", nil
	case RoleDeletion:
		return "SET LOCAL ROLE memory_deletion_runtime", nil
	default:
		return "", fmt.Errorf("%w: %q", ErrInvalidRole, role)
	}
}
