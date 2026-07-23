package accountdelete

import (
	"context"
	"errors"
	"testing"

	"github.com/m-shogo/memories-project/services/import-api/internal/epochguard"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

type stubRepository struct {
	epoch      int64
	beginErr   error
	sweepErr   error
	removals   []TableRemoval
	sweptEpoch int64
	sweptID    string
	swept      bool
}

func (r *stubRepository) BeginDeletion(context.Context, security.Principal) (int64, error) {
	return r.epoch, r.beginErr
}

func (r *stubRepository) Sweep(_ context.Context, accountID string, epoch int64) ([]TableRemoval, error) {
	r.swept = true
	r.sweptID = accountID
	r.sweptEpoch = epoch
	return r.removals, r.sweepErr
}

type stubGuard struct{ err error }

func (g stubGuard) Check(context.Context, security.Principal) error { return g.err }

func userPrincipal(t *testing.T) security.Principal {
	t.Helper()
	principal, err := security.NewVerifiedPrincipal("acct-delete-subject-01", 4, security.AuthorityIOSUser)
	if err != nil {
		t.Fatal(err)
	}
	return principal
}

func TestDeleteBumpsEpochThenSweeps(t *testing.T) {
	repository := &stubRepository{epoch: 5, removals: []TableRemoval{{Table: "memory_item", Removed: 3}}}
	service := Service{Repository: repository, Guard: stubGuard{}}

	receipt, err := service.Delete(context.Background(), userPrincipal(t))
	if err != nil {
		t.Fatal(err)
	}
	if receipt.DeletionEpoch != 5 || receipt.AccountID != "acct-delete-subject-01" {
		t.Fatalf("unexpected receipt: %+v", receipt)
	}
	// The sweep must target the principal's own account at the bumped epoch.
	if repository.sweptID != "acct-delete-subject-01" || repository.sweptEpoch != 5 {
		t.Fatalf("sweep ran against %s at epoch %d", repository.sweptID, repository.sweptEpoch)
	}
	if len(receipt.Removals) != 1 || receipt.Removals[0].Removed != 3 {
		t.Fatalf("unexpected removals: %+v", receipt.Removals)
	}
}

func TestDeleteRejectsLowerAuthorities(t *testing.T) {
	for _, authority := range []security.Authority{
		security.AuthorityIOSDevice,
		security.AuthorityBrowserPairing,
		security.AuthorityWorkerLease,
		security.AuthorityDeletionWorker,
	} {
		principal, err := security.NewVerifiedPrincipal("acct-delete-subject-01", 4, authority)
		if err != nil {
			t.Fatal(err)
		}
		repository := &stubRepository{epoch: 5}
		service := Service{Repository: repository, Guard: stubGuard{}}
		if _, err := service.Delete(context.Background(), principal); !errors.Is(err, ErrAuthorityNotAllowed) {
			t.Fatalf("%s deletion error = %v", authority, err)
		}
		if repository.swept {
			t.Fatalf("%s reached the sweep", authority)
		}
	}
}

func TestDeleteStopsOnFencedAccount(t *testing.T) {
	repository := &stubRepository{epoch: 5}
	service := Service{Repository: repository, Guard: stubGuard{err: epochguard.ErrAccountDeleting}}
	if _, err := service.Delete(context.Background(), userPrincipal(t)); !errors.Is(err, epochguard.ErrAccountDeleting) {
		t.Fatalf("fenced deletion error = %v", err)
	}
	if repository.swept {
		t.Fatal("a fenced account reached the sweep")
	}
}

// A sweep must never run at an epoch that did not advance: the bump is what
// closes the fence, so without it other sessions would still be live.
func TestDeleteRefusesToSweepWithoutAnEpochBump(t *testing.T) {
	for _, epoch := range []int64{4, 3, 0} {
		repository := &stubRepository{epoch: epoch}
		service := Service{Repository: repository, Guard: stubGuard{}}
		if _, err := service.Delete(context.Background(), userPrincipal(t)); !errors.Is(err, ErrBeginDeletion) {
			t.Fatalf("epoch %d error = %v", epoch, err)
		}
		if repository.swept {
			t.Fatalf("epoch %d reached the sweep", epoch)
		}
	}
}

// A failed sweep is reported as a failure; claiming success would assert an
// erasure that did not happen.
func TestDeleteReportsSweepFailure(t *testing.T) {
	repository := &stubRepository{epoch: 5, sweepErr: errors.New("connection lost")}
	service := Service{Repository: repository, Guard: stubGuard{}}
	if _, err := service.Delete(context.Background(), userPrincipal(t)); !errors.Is(err, ErrSweepFailed) {
		t.Fatalf("sweep failure error = %v", err)
	}
}

func TestDeleteRequiresComposition(t *testing.T) {
	if _, err := (Service{}).Delete(context.Background(), userPrincipal(t)); !errors.Is(err, ErrServiceUnavailable) {
		t.Fatalf("uncomposed service error = %v", err)
	}
}
