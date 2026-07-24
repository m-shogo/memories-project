package accountdelete

import (
	"context"
	"errors"
	"fmt"
)

// Claim is one leased unit of deletion work. The worker never chooses which
// account to erase — the database hands it one that is already committed to
// deletion, which is what keeps a worker from being pointed at a live account.
type Claim struct {
	AccountID     string
	DeletionEpoch int64
	Attempts      int
}

// WorkQueue is the claim side of the deletion runtime. Claim must lease the
// account so a second worker takes different work, and Release must hand the
// lease back after a failed attempt so a retry does not wait it out.
type WorkQueue interface {
	Claim(ctx context.Context, leaseSeconds int) (Claim, bool, error)
	Release(ctx context.Context, accountID string, deletionEpoch int64) error
}

// Worker drains accounts that a request already fenced. It is safe to run more
// than one: the lease and SKIP LOCKED make concurrent workers take disjoint
// accounts rather than racing over the same one.
type Worker struct {
	Queue        WorkQueue
	Repository   Repository
	Objects      ObjectEraser
	LeaseSeconds int
}

// Sweep processes at most maxAccounts claims and reports the receipts for the
// accounts it finished. A failure on one account is returned immediately
// rather than being swallowed to keep the loop going: an erasure that did not
// happen must be visible, and the account stays fenced and claimable either
// way.
func (w Worker) Sweep(ctx context.Context, maxAccounts int) ([]Receipt, error) {
	if w.Queue == nil || w.Repository == nil || w.Objects == nil {
		return nil, ErrServiceUnavailable
	}
	lease := w.LeaseSeconds
	if lease <= 0 {
		lease = 300
	}
	var receipts []Receipt
	for claimed := 0; claimed < maxAccounts; claimed++ {
		claim, ok, err := w.Queue.Claim(ctx, lease)
		if err != nil {
			return receipts, fmt.Errorf("claim deletion work: %w", err)
		}
		if !ok {
			return receipts, nil
		}
		receipt, err := w.erase(ctx, claim)
		if err != nil {
			// Hand the lease back so the next attempt can start immediately;
			// a release failure is secondary to the erasure failure itself.
			_ = w.Queue.Release(ctx, claim.AccountID, claim.DeletionEpoch)
			return receipts, err
		}
		receipts = append(receipts, receipt)
	}
	return receipts, nil
}

func (w Worker) erase(ctx context.Context, claim Claim) (Receipt, error) {
	// Same order as before, and for the same reason: the rows are the only
	// ledger of what the bucket holds, so they must outlive the objects. This
	// is also what makes a resumed attempt correct rather than merely retried —
	// a partially erased account still lists everything that remains.
	keys, err := w.Repository.ObjectKeys(ctx, claim.AccountID, claim.DeletionEpoch)
	if err != nil {
		return Receipt{}, fmt.Errorf("%w: %v", ErrSweepFailed, err)
	}
	erasedVersions := 0
	for _, key := range keys {
		erased, err := w.Objects.EraseObject(ctx, key)
		erasedVersions += erased
		if err != nil {
			return Receipt{}, fmt.Errorf("%w: %v", ErrObjectEraseFailed, err)
		}
	}

	removals, err := w.Repository.Sweep(ctx, claim.AccountID, claim.DeletionEpoch)
	if err != nil {
		return Receipt{}, fmt.Errorf("%w: %v", ErrSweepFailed, err)
	}
	return Receipt{
		AccountID:     claim.AccountID,
		DeletionEpoch: claim.DeletionEpoch,
		Attempts:      claim.Attempts,
		Removals: append(removals, TableRemoval{
			Table:   "quarantine_object_versions",
			Removed: int64(erasedVersions),
		}),
	}, nil
}

// ErrNoDeletionWork lets a caller distinguish an idle queue from a failure.
var ErrNoDeletionWork = errors.New("no account is pending deletion")
