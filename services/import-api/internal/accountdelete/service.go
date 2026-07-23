// Package accountdelete owns the account erasure boundary: it turns a verified
// user request into an epoch bump that fences every other surface, then an
// authorized sweep that erases the account's rows.
//
// The package deliberately holds no account identifier of its own. The account
// erased is always the one carried by the verified principal, so a request body
// can never redirect a deletion at somebody else's data.
package accountdelete

import (
	"context"
	"errors"
	"fmt"

	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

var (
	ErrServiceUnavailable  = errors.New("account deletion service is unavailable")
	ErrAuthorityNotAllowed = errors.New("authority may not delete an account")
	ErrBeginDeletion       = errors.New("account deletion could not start")
	ErrSweepFailed         = errors.New("account deletion sweep failed")
	ErrObjectEraseFailed   = errors.New("quarantine object erasure failed")
)

// TableRemoval reports how many rows the sweep erased from one table. It is a
// receipt for the caller and for operational audit, never an input.
type TableRemoval struct {
	Table   string `json:"table"`
	Removed int64  `json:"removed"`
}

type Receipt struct {
	AccountID     string
	DeletionEpoch int64
	Removals      []TableRemoval
}

// Repository is the narrow database surface deletion needs. BeginDeletion runs
// under the API runtime role with the caller's own context; Sweep runs under
// the deletion runtime role at the bumped epoch and also records completion.
type Repository interface {
	BeginDeletion(ctx context.Context, principal security.Principal) (int64, error)
	// ObjectKeys lists the quarantine keys the account owns, read from its own
	// RLS-scoped rows. It is the ledger that makes object erasure retryable:
	// the rows are deleted only after the objects are gone.
	ObjectKeys(ctx context.Context, accountID string, deletionEpoch int64) ([]string, error)
	Sweep(ctx context.Context, accountID string, deletionEpoch int64) ([]TableRemoval, error)
}

// ObjectEraser removes every stored version of one quarantine key and reports
// how many versions it removed. It must be idempotent so a retried deletion
// converges instead of failing on already-erased objects.
type ObjectEraser interface {
	EraseObject(ctx context.Context, objectKey string) (int, error)
}

// Guard is the same epoch fence every other service uses. Deletion checks it
// first so a stale or already-deleting session cannot restart erasure.
type Guard interface {
	Check(context.Context, security.Principal) error
}

type Service struct {
	Repository Repository
	Objects    ObjectEraser
	Guard      Guard
}

// Delete erases the principal's own account. Only a full user access token may
// do so: device sessions, browser pairings and worker leases are lower
// authorities that must not be able to destroy an account.
func (s Service) Delete(ctx context.Context, principal security.Principal) (Receipt, error) {
	if s.Repository == nil || s.Guard == nil || s.Objects == nil {
		return Receipt{}, ErrServiceUnavailable
	}
	if err := principal.Validate(); err != nil {
		return Receipt{}, fmt.Errorf("invalid verified principal: %w", err)
	}
	if principal.Authority() != security.AuthorityIOSUser {
		return Receipt{}, ErrAuthorityNotAllowed
	}
	if err := s.Guard.Check(ctx, principal); err != nil {
		return Receipt{}, err
	}

	deletionEpoch, err := s.Repository.BeginDeletion(ctx, principal)
	if err != nil {
		return Receipt{}, fmt.Errorf("%w: %v", ErrBeginDeletion, err)
	}
	if deletionEpoch <= principal.AccountEpoch() {
		// The bump is what fences every other session. A non-increasing epoch
		// means the fence did not close, so erasure must not proceed.
		return Receipt{}, fmt.Errorf("%w: deletion epoch did not advance", ErrBeginDeletion)
	}

	// Objects are erased before the rows that point at them. The rows are the
	// only ledger of what exists in the bucket, so dropping them first would
	// strand the objects permanently; this order means a failed attempt can
	// simply be retried, and version deletes are idempotent.
	keys, err := s.Repository.ObjectKeys(ctx, principal.AccountID(), deletionEpoch)
	if err != nil {
		return Receipt{}, fmt.Errorf("%w: %v", ErrSweepFailed, err)
	}
	erasedVersions := 0
	for _, key := range keys {
		erased, err := s.Objects.EraseObject(ctx, key)
		erasedVersions += erased
		if err != nil {
			// The account stays fenced in 'deleting' with its ledger intact.
			return Receipt{}, fmt.Errorf("%w: %v", ErrObjectEraseFailed, err)
		}
	}

	removals, err := s.Repository.Sweep(ctx, principal.AccountID(), deletionEpoch)
	if err != nil {
		// The account stays fenced in 'deleting' state: no surface can reach it
		// and a retry can resume the sweep. Reporting failure is required —
		// silently returning success would claim an erasure that did not happen.
		return Receipt{}, fmt.Errorf("%w: %v", ErrSweepFailed, err)
	}
	return Receipt{
		AccountID:     principal.AccountID(),
		DeletionEpoch: deletionEpoch,
		Removals: append(removals, TableRemoval{
			Table:   "quarantine_object_versions",
			Removed: int64(erasedVersions),
		}),
	}, nil
}
