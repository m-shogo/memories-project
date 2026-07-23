package pgrepo

import (
	"context"
	"errors"
	"fmt"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/m-shogo/memories-project/services/import-api/internal/accountdelete"
	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/epochguard"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

// AccountControl is the canonical server-side reader of memory_os.account_control
// and the executor of the two deletion steps. It satisfies epochguard.Source and
// accountdelete.Repository.
//
// Current takes the connection pool directly rather than going through
// dbscope.Executor: the executor requires a fully verified principal including
// an epoch, and the whole point of this read is to learn the canonical epoch
// when the caller's claimed one may already be stale. The account_control SELECT
// policy filters on account_id alone, so the read stays RLS-scoped to exactly
// one account either way.
type AccountControl struct {
	Pool         *pgxpool.Pool
	Transactions ScopedExecutor
}

// ScopedExecutor mirrors the interface the domain services take, so deletion
// runs through the same role-scoping path as every other write.
type ScopedExecutor interface {
	WithinPrincipal(context.Context, security.Principal, dbscope.Role, func(context.Context, dbscope.Transaction) error) error
}

var errNoPool = errors.New("pgrepo: account control requires a connection pool")

func (a AccountControl) Current(ctx context.Context, accountID string) (epochguard.Snapshot, error) {
	if a.Pool == nil {
		return epochguard.Snapshot{}, errNoPool
	}
	tx, err := a.Pool.BeginTx(ctx, pgx.TxOptions{AccessMode: pgx.ReadOnly})
	if err != nil {
		return epochguard.Snapshot{}, fmt.Errorf("begin account control read: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()

	// The role name is a compile-time constant from the dbscope allowlist; only
	// the account identifier is parameterized.
	if _, err := tx.Exec(ctx, "SET LOCAL ROLE "+string(dbscope.RoleAPI)); err != nil {
		return epochguard.Snapshot{}, fmt.Errorf("set account control role: %w", err)
	}
	if _, err := tx.Exec(ctx,
		"SELECT set_config('app.current_account_id', $1, true)", accountID); err != nil {
		return epochguard.Snapshot{}, fmt.Errorf("set account control context: %w", err)
	}

	snapshot := epochguard.Snapshot{AccountID: accountID}
	var state string
	err = tx.QueryRow(ctx,
		`SELECT account_epoch, state FROM memory_os.account_control WHERE account_id = $1`,
		accountID).Scan(&snapshot.Epoch, &state)
	if errors.Is(err, pgx.ErrNoRows) {
		return epochguard.Snapshot{}, ErrNotFound
	}
	if err != nil {
		return epochguard.Snapshot{}, fmt.Errorf("read account control: %w", err)
	}
	snapshot.State = epochguard.State(state)
	return snapshot, nil
}

// BeginDeletion bumps the account epoch under the caller's own API-role context.
// The account identifier is never sent: begin_account_deletion() reads it from
// the transaction-local verified context, so no request field can redirect it.
func (a AccountControl) BeginDeletion(ctx context.Context, principal security.Principal) (int64, error) {
	if a.Transactions == nil {
		return 0, errNoPool
	}
	var deletionEpoch int64
	err := a.Transactions.WithinPrincipal(ctx, principal, dbscope.RoleAPI,
		func(ctx context.Context, tx dbscope.Transaction) error {
			adapted, err := pgscope.From(tx)
			if err != nil {
				return err
			}
			return adapted.QueryRow(ctx, "SELECT memory_os.begin_account_deletion()").Scan(&deletionEpoch)
		})
	if err != nil {
		return 0, err
	}
	return deletionEpoch, nil
}

// ObjectKeys reads every quarantine key the account owns. Both surfaces that
// can name an object are read: the authorization that minted the key and the
// committed Preview that consumed it, because either may exist without the
// other. The read runs under the deletion runtime's sweep policies, so it is
// scoped to this owner across all epochs the account ever wrote.
func (a AccountControl) ObjectKeys(ctx context.Context, accountID string, deletionEpoch int64) ([]string, error) {
	if a.Transactions == nil {
		return nil, errNoPool
	}
	principal, err := security.NewVerifiedPrincipal(accountID, deletionEpoch, security.AuthorityDeletionWorker)
	if err != nil {
		return nil, fmt.Errorf("build deletion principal: %w", err)
	}
	var keys []string
	err = a.Transactions.WithinPrincipal(ctx, principal, dbscope.RoleDeletion,
		func(ctx context.Context, tx dbscope.Transaction) error {
			adapted, err := pgscope.From(tx)
			if err != nil {
				return err
			}
			rows, err := adapted.Query(ctx,
				`SELECT object_key FROM memory_os.upload_authorization WHERE object_key IS NOT NULL
				 UNION
				 SELECT source_object_key FROM memory_os.preview_ready WHERE source_object_key IS NOT NULL`)
			if err != nil {
				return fmt.Errorf("list quarantine object keys: %w", err)
			}
			defer rows.Close()
			for rows.Next() {
				var key string
				if err := rows.Scan(&key); err != nil {
					return fmt.Errorf("scan quarantine object key: %w", err)
				}
				keys = append(keys, key)
			}
			return rows.Err()
		})
	if err != nil {
		return nil, err
	}
	return keys, nil
}

// Sweep erases the account's rows and records completion in one transaction
// under the deletion runtime role. Keeping both in a single transaction means
// the account can never be marked 'deleted' while rows survive: a failure
// rolls both back and leaves the account fenced in 'deleting' for a retry.
func (a AccountControl) Sweep(ctx context.Context, accountID string, deletionEpoch int64) ([]accountdelete.TableRemoval, error) {
	if a.Transactions == nil {
		return nil, errNoPool
	}
	// The deletion runtime is its own authority; it is not the user's session.
	principal, err := security.NewVerifiedPrincipal(accountID, deletionEpoch, security.AuthorityDeletionWorker)
	if err != nil {
		return nil, fmt.Errorf("build deletion principal: %w", err)
	}

	var removals []accountdelete.TableRemoval
	err = a.Transactions.WithinPrincipal(ctx, principal, dbscope.RoleDeletion,
		func(ctx context.Context, tx dbscope.Transaction) error {
			adapted, err := pgscope.From(tx)
			if err != nil {
				return err
			}
			rows, err := adapted.Query(ctx, "SELECT table_name, removed FROM memory_os.sweep_deleted_account()")
			if err != nil {
				return fmt.Errorf("sweep deleted account: %w", err)
			}
			removals = removals[:0]
			for rows.Next() {
				var removal accountdelete.TableRemoval
				if err := rows.Scan(&removal.Table, &removal.Removed); err != nil {
					rows.Close()
					return fmt.Errorf("scan sweep result: %w", err)
				}
				removals = append(removals, removal)
			}
			rows.Close()
			if err := rows.Err(); err != nil {
				return fmt.Errorf("read sweep result: %w", err)
			}
			if len(removals) == 0 {
				return errors.New("sweep returned no accounting rows")
			}
			return adapted.Exec(ctx, "SELECT memory_os.complete_account_deletion()")
		})
	if err != nil {
		return nil, err
	}
	return removals, nil
}
