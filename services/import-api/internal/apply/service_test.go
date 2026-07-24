package apply

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

type fakeExecutor struct{}

func (fakeExecutor) WithinPrincipal(ctx context.Context, _ security.Principal, _ dbscope.Role, fn func(context.Context, dbscope.Transaction) error) error {
	return fn(ctx, fakeTx{})
}

type fakeTx struct{}

func (fakeTx) Exec(context.Context, string, ...any) error { return nil }
func (fakeTx) Commit() error                              { return nil }
func (fakeTx) Rollback() error                            { return nil }

type fakeIDs struct{ value string }

func (f fakeIDs) NewID(string) (string, error) { return f.value, nil }

type fakeRepository struct {
	preview     Preview
	claimResult ClaimResult
	claim       Claim
	counts      Counts
	applyCalls  int
	claimCalls  int
	previewGets int
	completed   bool
}

func (r *fakeRepository) GetPreview(context.Context, dbscope.Transaction, string) (Preview, error) {
	r.previewGets++
	return r.preview, nil
}
func (r *fakeRepository) ClaimIdempotency(_ context.Context, _ dbscope.Transaction, claim Claim) (ClaimResult, error) {
	r.claimCalls++
	r.claim = claim
	return r.claimResult, nil
}
func (r *fakeRepository) ApplyMaterializedPreview(context.Context, dbscope.Transaction, string, string, DuplicatePolicy) (Counts, error) {
	r.applyCalls++
	return r.counts, nil
}
func (r *fakeRepository) CompleteApply(context.Context, dbscope.Transaction, string, Counts, time.Time) error {
	r.completed = true
	return nil
}

func TestApplyUsesExactPreviewAndCompletesAtomically(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	principal := iosPrincipal(t)
	repository := &fakeRepository{
		preview:     validPreview(now, principal),
		claimResult: ClaimResult{Disposition: ClaimNew, ApplyID: "apl_01J00000000000000000000000"},
		counts:      Counts{Created: 2, Skipped: 1},
	}
	service := Service{Transactions: fakeExecutor{}, Repository: repository, IDs: fakeIDs{value: "apl_01J00000000000000000000000"}, Now: func() time.Time { return now }}
	result, err := service.Apply(context.Background(), principal, validRequest())
	if err != nil {
		t.Fatal(err)
	}
	if result.Status != "applied" || result.Counts.Created != 2 || result.Counts.Skipped != 1 || repository.applyCalls != 1 || !repository.completed {
		t.Fatalf("unexpected apply result: %#v repository=%#v", result, repository)
	}
	if repository.claim.PreviewSHA256 != repeatHex('a') || len(repository.claim.RequestSHA256) != 64 {
		t.Fatalf("claim was not hash-bound: %#v", repository.claim)
	}
}

func TestApplyReturnsCompletedReplayWithoutApplyingAgain(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	principal := iosPrincipal(t)
	request := validRequest()
	requestHash := computeRequestHash(principal, request)
	repository := &fakeRepository{
		preview:     validPreview(now, principal),
		claimResult: ClaimResult{Disposition: ClaimReplay, RequestSHA256: requestHash, Existing: Result{ApplyID: "apl_existing_000000000000", Status: "applied", Counts: Counts{Created: 3}}},
	}
	service := Service{Transactions: fakeExecutor{}, Repository: repository, IDs: fakeIDs{value: "apl_new_0000000000000000"}, Now: func() time.Time { return now }}
	result, err := service.Apply(context.Background(), principal, request)
	if err != nil {
		t.Fatal(err)
	}
	if !result.Replayed || result.ApplyID != "apl_existing_000000000000" || repository.applyCalls != 0 {
		t.Fatalf("unexpected replay result: %#v", result)
	}
}

func TestApplyRejectsIdempotencyKeyWithDifferentRequest(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	principal := iosPrincipal(t)
	repository := &fakeRepository{preview: validPreview(now, principal), claimResult: ClaimResult{Disposition: ClaimConflict, RequestSHA256: repeatHex('f')}}
	service := Service{Transactions: fakeExecutor{}, Repository: repository, IDs: fakeIDs{value: "apl_01J00000000000000000000000"}, Now: func() time.Time { return now }}
	_, err := service.Apply(context.Background(), principal, validRequest())
	if !errors.Is(err, ErrIdempotencyMismatch) {
		t.Fatalf("expected idempotency mismatch, got %v", err)
	}
}

func TestApplyRejectsBrowserAuthority(t *testing.T) {
	principal, _ := security.NewVerifiedPrincipal("acct_01J00000000000000000000000", 7, security.AuthorityBrowserPairing)
	_, err := (&Service{}).Apply(context.Background(), principal, validRequest())
	if !errors.Is(err, ErrAuthorityNotAllowed) {
		t.Fatalf("expected authority error, got %v", err)
	}
}

func TestApplyRejectsPreviewHashMismatch(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	principal := iosPrincipal(t)
	preview := validPreview(now, principal)
	preview.PreviewSHA256 = repeatHex('b')
	repository := &fakeRepository{preview: preview}
	service := Service{Transactions: fakeExecutor{}, Repository: repository, IDs: fakeIDs{value: "apl_01J00000000000000000000000"}, Now: func() time.Time { return now }}
	_, err := service.Apply(context.Background(), principal, validRequest())
	if !errors.Is(err, ErrPreviewHashMismatch) {
		t.Fatalf("expected hash mismatch, got %v", err)
	}
}

func TestApplyRejectsPartialAccounting(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	principal := iosPrincipal(t)
	repository := &fakeRepository{preview: validPreview(now, principal), claimResult: ClaimResult{Disposition: ClaimNew}, counts: Counts{Created: 1}}
	service := Service{Transactions: fakeExecutor{}, Repository: repository, IDs: fakeIDs{value: "apl_01J00000000000000000000000"}, Now: func() time.Time { return now }}
	_, err := service.Apply(context.Background(), principal, validRequest())
	if !errors.Is(err, ErrApplyAccountingMismatch) || repository.completed {
		t.Fatalf("expected accounting rollback, got %v", err)
	}
}

func validPreview(now time.Time, principal security.Principal) Preview {
	return Preview{ID: "prv_01J00000000000000000000000", OwnerAccountID: principal.AccountID(), AccountEpoch: principal.AccountEpoch(), PreviewSHA256: repeatHex('a'), CandidateCount: 3, Status: "ready", ExpiresAt: now.Add(time.Hour)}
}
func validRequest() Request {
	return Request{PreviewID: "prv_01J00000000000000000000000", PreviewSHA256: repeatHex('a'), IdempotencyKey: "idem_01J0000000000000000000000", DuplicatePolicy: DuplicateSkipExisting}
}
func iosPrincipal(t *testing.T) security.Principal {
	t.Helper()
	p, err := security.NewVerifiedPrincipal("acct_01J00000000000000000000000", 7, security.AuthorityIOSUser)
	if err != nil {
		t.Fatal(err)
	}
	return p
}
func repeatHex(value byte) string {
	result := make([]byte, 64)
	for index := range result {
		result[index] = value
	}
	return string(result)
}

// update_safe_fields overwrote a stored record and its provenance in place. The
// path is closed until append-only supersession exists, and closed means the
// request never reaches the database at all — not that it quietly becomes a
// different policy.
func TestApplyRefusesUpdateSafeFieldsWithoutTouchingAnything(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	principal := iosPrincipal(t)
	repository := &fakeRepository{
		preview:     validPreview(now, principal),
		claimResult: ClaimResult{Disposition: ClaimNew, ApplyID: "apl_01J00000000000000000000000"},
		counts:      Counts{Created: 2},
	}
	service := Service{Transactions: fakeExecutor{}, Repository: repository, IDs: fakeIDs{value: "apl_01J00000000000000000000000"}, Now: func() time.Time { return now }}

	request := validRequest()
	request.DuplicatePolicy = DuplicateUpdateSafe
	result, err := service.Apply(context.Background(), principal, request)

	if !errors.Is(err, ErrDuplicatePolicyUnsupported) {
		t.Fatalf("update_safe_fields error = %v, want ErrDuplicatePolicyUnsupported", err)
	}
	// Distinct from a malformed request: the client sent a value this API used
	// to accept, and must be able to tell the difference.
	if errors.Is(err, ErrInvalidRequest) {
		t.Fatal("refusal is indistinguishable from a malformed request")
	}
	if result.Status != "" || result.Counts != (Counts{}) {
		t.Fatalf("refusal returned a result: %#v", result)
	}
	// No preview read, no idempotency claim, no materialization, no completion.
	// A claim row would make the refusal look like a consumed attempt.
	if repository.previewGets != 0 || repository.claimCalls != 0 ||
		repository.applyCalls != 0 || repository.completed {
		t.Fatalf("the refused request reached the repository: %#v", repository)
	}
}

// A refusal must never be laundered into a policy the caller did not ask for:
// a client told "applied" would believe its update landed.
func TestApplyDoesNotFallBackToAnotherPolicy(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	principal := iosPrincipal(t)
	repository := &fakeRepository{
		preview:     validPreview(now, principal),
		claimResult: ClaimResult{Disposition: ClaimNew, ApplyID: "apl_01J00000000000000000000000"},
		counts:      Counts{Created: 2},
	}
	service := Service{Transactions: fakeExecutor{}, Repository: repository, IDs: fakeIDs{value: "apl_01J00000000000000000000000"}, Now: func() time.Time { return now }}

	request := validRequest()
	request.DuplicatePolicy = DuplicateUpdateSafe
	if _, err := service.Apply(context.Background(), principal, request); err == nil {
		t.Fatal("update_safe_fields succeeded")
	}
	if repository.claim.DuplicatePolicy == DuplicateSkipExisting ||
		repository.claim.DuplicatePolicy == DuplicateKeepBoth {
		t.Fatalf("the refused policy was rewritten to %q", repository.claim.DuplicatePolicy)
	}
}

// The supported policies keep their existing behaviour, including the counts a
// client reconciles against.
func TestSupportedDuplicatePoliciesStillApply(t *testing.T) {
	for _, testCase := range []struct {
		policy DuplicatePolicy
		counts Counts
	}{
		{DuplicateSkipExisting, Counts{Created: 2, Skipped: 1}},
		{DuplicateKeepBoth, Counts{Created: 3}},
	} {
		now := time.Unix(1_800_000_000, 0).UTC()
		principal := iosPrincipal(t)
		repository := &fakeRepository{
			preview:     validPreview(now, principal),
			claimResult: ClaimResult{Disposition: ClaimNew, ApplyID: "apl_01J00000000000000000000000"},
			counts:      testCase.counts,
		}
		service := Service{Transactions: fakeExecutor{}, Repository: repository, IDs: fakeIDs{value: "apl_01J00000000000000000000000"}, Now: func() time.Time { return now }}

		request := validRequest()
		request.DuplicatePolicy = testCase.policy
		result, err := service.Apply(context.Background(), principal, request)
		if err != nil {
			t.Fatalf("%s: %v", testCase.policy, err)
		}
		if result.Status != "applied" || result.Counts != testCase.counts ||
			repository.applyCalls != 1 || !repository.completed {
			t.Fatalf("%s: unexpected result %#v repository=%#v", testCase.policy, result, repository)
		}
		if repository.claim.DuplicatePolicy != testCase.policy {
			t.Fatalf("%s: claim recorded policy %q", testCase.policy, repository.claim.DuplicatePolicy)
		}
	}
}
