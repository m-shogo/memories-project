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
	objectKeys []string
	keysErr    error
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

func (r *stubRepository) ObjectKeys(context.Context, string, int64) ([]string, error) {
	return r.objectKeys, r.keysErr
}

type stubEraser struct {
	erased  []string
	perKey  int
	failOn  string
	failErr error
}

func (e *stubEraser) EraseObject(_ context.Context, key string) (int, error) {
	e.erased = append(e.erased, key)
	if key == e.failOn {
		return 0, e.failErr
	}
	return e.perKey, nil
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

type stubQueue struct {
	claims     []Claim
	index      int
	claimErr   error
	released   []string
	releaseOk  bool
	backlog    Backlog
	backlogErr error
}

func (q *stubQueue) Claim(context.Context, int) (Claim, bool, error) {
	if q.claimErr != nil {
		return Claim{}, false, q.claimErr
	}
	if q.index >= len(q.claims) {
		return Claim{}, false, nil
	}
	claim := q.claims[q.index]
	q.index++
	return claim, true, nil
}

func (q *stubQueue) Backlog(context.Context, int) (Backlog, error) {
	return q.backlog, q.backlogErr
}

func (q *stubQueue) Release(_ context.Context, accountID string, _ int64) error {
	q.released = append(q.released, accountID)
	q.releaseOk = true
	return nil
}

// Delete is now a fence, not an erasure. Claiming otherwise in the response
// would tell the user their data was gone before anything had touched it.
func TestDeleteFencesWithoutSweeping(t *testing.T) {
	repository := &stubRepository{epoch: 5}
	service := Service{Repository: repository, Guard: stubGuard{}}

	receipt, err := service.Delete(context.Background(), userPrincipal(t))
	if err != nil {
		t.Fatal(err)
	}
	if receipt.DeletionEpoch != 5 || receipt.AccountID != "acct-delete-subject-01" {
		t.Fatalf("unexpected receipt: %+v", receipt)
	}
	if repository.swept || len(receipt.Removals) != 0 {
		t.Fatalf("the request performed erasure: swept=%v removals=%+v",
			repository.swept, receipt.Removals)
	}
}

func TestWorkerErasesClaimedAccounts(t *testing.T) {
	repository := &stubRepository{
		removals:   []TableRemoval{{Table: "memory_item", Removed: 3}},
		objectKeys: []string{"quarantine/job-1/upl-1", "quarantine/job-1/upl-2"},
	}
	eraser := &stubEraser{perKey: 2}
	queue := &stubQueue{claims: []Claim{{AccountID: "acct-delete-subject-01", DeletionEpoch: 5, Attempts: 1}}}
	worker := Worker{Queue: queue, Repository: repository, Objects: eraser}

	receipts, err := worker.Sweep(context.Background(), 4)
	if err != nil {
		t.Fatal(err)
	}
	if len(receipts) != 1 || receipts[0].DeletionEpoch != 5 || receipts[0].Attempts != 1 {
		t.Fatalf("unexpected receipts: %+v", receipts)
	}
	if repository.sweptID != "acct-delete-subject-01" || repository.sweptEpoch != 5 {
		t.Fatalf("swept %s at epoch %d", repository.sweptID, repository.sweptEpoch)
	}
	if len(eraser.erased) != 2 {
		t.Fatalf("erased %v", eraser.erased)
	}
	if len(receipts[0].Removals) != 2 ||
		receipts[0].Removals[1].Table != "quarantine_object_versions" ||
		receipts[0].Removals[1].Removed != 4 {
		t.Fatalf("unexpected removals: %+v", receipts[0].Removals)
	}
	if queue.releaseOk {
		t.Fatal("a successful sweep released its lease")
	}
}

// A resumed attempt must be able to start immediately, so a failure hands the
// lease back rather than making the account wait the lease out.
func TestWorkerReleasesTheLeaseWhenErasureFails(t *testing.T) {
	repository := &stubRepository{objectKeys: []string{"quarantine/job-1/upl-1"}}
	eraser := &stubEraser{failOn: "quarantine/job-1/upl-1", failErr: errors.New("bucket unreachable")}
	queue := &stubQueue{claims: []Claim{{AccountID: "acct-delete-subject-01", DeletionEpoch: 5}}}
	worker := Worker{Queue: queue, Repository: repository, Objects: eraser}

	if _, err := worker.Sweep(context.Background(), 4); !errors.Is(err, ErrObjectEraseFailed) {
		t.Fatalf("worker error = %v", err)
	}
	if repository.swept {
		t.Fatal("rows were swept even though objects survived")
	}
	if len(queue.released) != 1 {
		t.Fatalf("lease releases: %v", queue.released)
	}
}

func TestWorkerStopsWhenNothingIsPending(t *testing.T) {
	worker := Worker{Queue: &stubQueue{}, Repository: &stubRepository{}, Objects: &stubEraser{}}
	receipts, err := worker.Sweep(context.Background(), 4)
	if err != nil || len(receipts) != 0 {
		t.Fatalf("idle sweep returned %v, %v", receipts, err)
	}
}

func TestWorkerRequiresComposition(t *testing.T) {
	if _, err := (Worker{}).Sweep(context.Background(), 1); !errors.Is(err, ErrServiceUnavailable) {
		t.Fatalf("uncomposed worker error = %v", err)
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

func TestDeleteRequiresComposition(t *testing.T) {
	if _, err := (Service{}).Delete(context.Background(), userPrincipal(t)); !errors.Is(err, ErrServiceUnavailable) {
		t.Fatalf("uncomposed service error = %v", err)
	}
}

// A backlog with stuck accounts is not healthy: someone asked to be deleted
// and is not being, which is the whole reason the count exists.
func TestBacklogHealthReflectsStuckAccounts(t *testing.T) {
	for _, testCase := range []struct {
		name    string
		backlog Backlog
		healthy bool
	}{
		{"idle", Backlog{}, true},
		{"pending but progressing", Backlog{Pending: 4}, true},
		{"one stuck", Backlog{Pending: 4, Stuck: 1, MaxAttempts: 7}, false},
	} {
		queue := &stubQueue{backlog: testCase.backlog}
		worker := Worker{Queue: queue, Repository: &stubRepository{}, Objects: &stubEraser{}}
		backlog, err := worker.Backlog(context.Background())
		if err != nil {
			t.Fatal(err)
		}
		if backlog.Healthy() != testCase.healthy {
			t.Fatalf("%s: healthy = %v, want %v", testCase.name, backlog.Healthy(), testCase.healthy)
		}
	}
}

func TestBacklogRequiresAQueue(t *testing.T) {
	if _, err := (Worker{}).Backlog(context.Background()); !errors.Is(err, ErrServiceUnavailable) {
		t.Fatalf("uncomposed backlog error = %v", err)
	}
}
