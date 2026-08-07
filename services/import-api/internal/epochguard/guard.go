package epochguard

import (
	"context"
	"errors"
	"fmt"

	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

var (
	ErrAccountUnavailable = errors.New("account security state unavailable")
	ErrStaleAccountEpoch  = errors.New("account epoch is stale")
	ErrAccountDeleting    = errors.New("account deletion is in progress")
	ErrAccountDeleted     = errors.New("account is deleted")
	ErrAccountSuspended   = errors.New("account is suspended")
)

type State string

const (
	StateActive    State = "active"
	StateDeleting  State = "deleting"
	StateDeleted   State = "deleted"
	StateSuspended State = "suspended"
)

type Snapshot struct {
	AccountID string
	Epoch     int64
	State     State
}

// Source must read the canonical account-control row through a narrowly scoped
// server-side repository. It must not accept an account ID from an HTTP body.
type Source interface {
	Current(context.Context, string) (Snapshot, error)
}

// TransactionSource is the same authority read performed on an already-open
// dbscope transaction. Write-boundary fence checks must use this path instead
// of borrowing a second connection while the caller holds the first one.
// Otherwise enough concurrent writes can exhaust the pool with every request
// waiting for another connection it cannot obtain.
type TransactionSource interface {
	CurrentWithin(context.Context, dbscope.Transaction, string) (Snapshot, error)
}

type Guard struct {
	Source Source
}

// Check is a fast-fail checkpoint for long-running work. PostgreSQL owner/epoch
// policies and write predicates remain authoritative against races after this
// check; callers must checkpoint again immediately before irreversible writes.
func (g Guard) Check(ctx context.Context, principal security.Principal) error {
	if err := principal.Validate(); err != nil {
		return fmt.Errorf("invalid verified principal: %w", err)
	}
	if g.Source == nil {
		return ErrAccountUnavailable
	}
	snapshot, err := g.Source.Current(ctx, principal.AccountID())
	if err != nil {
		return fmt.Errorf("read account security state: %w", ErrAccountUnavailable)
	}
	return validateSnapshot(principal, snapshot)
}

// CheckWithin performs the write-boundary checkpoint on the transaction the
// caller already owns. PostgreSQL READ COMMITTED gives each statement a fresh
// snapshot, and the subsequent RLS/write predicate remains the final authority
// if deletion races the check. A source without this capability fails closed;
// silently opening another transaction here can deadlock a bounded pool.
func (g Guard) CheckWithin(ctx context.Context, principal security.Principal, tx dbscope.Transaction) error {
	if err := principal.Validate(); err != nil {
		return fmt.Errorf("invalid verified principal: %w", err)
	}
	if g.Source == nil || tx == nil {
		return ErrAccountUnavailable
	}
	source, ok := g.Source.(TransactionSource)
	if !ok {
		return ErrAccountUnavailable
	}
	snapshot, err := source.CurrentWithin(ctx, tx, principal.AccountID())
	if err != nil {
		return fmt.Errorf("read account security state in transaction: %w", ErrAccountUnavailable)
	}
	return validateSnapshot(principal, snapshot)
}

func validateSnapshot(principal security.Principal, snapshot Snapshot) error {
	if snapshot.AccountID != principal.AccountID() || snapshot.Epoch < 0 {
		return ErrAccountUnavailable
	}
	if snapshot.Epoch != principal.AccountEpoch() {
		return ErrStaleAccountEpoch
	}
	switch snapshot.State {
	case StateActive:
		return nil
	case StateDeleting:
		return ErrAccountDeleting
	case StateDeleted:
		return ErrAccountDeleted
	case StateSuspended:
		return ErrAccountSuspended
	default:
		return ErrAccountUnavailable
	}
}
