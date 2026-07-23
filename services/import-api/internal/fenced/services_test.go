package fenced

import (
	"context"
	"errors"
	"testing"
	"time"

	applydomain "github.com/m-shogo/memories-project/services/import-api/internal/apply"
	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/epochguard"
	"github.com/m-shogo/memories-project/services/import-api/internal/preview"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
	"github.com/m-shogo/memories-project/services/import-api/internal/upload"
)

type sequenceGuard struct {
	calls  int
	failAt int
}

func (g *sequenceGuard) Check(context.Context, security.Principal) error {
	g.calls++
	if g.calls == g.failAt {
		return epochguard.ErrStaleAccountEpoch
	}
	return nil
}

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

type uploadRepo struct {
	authorization upload.Authorization
	consumed      bool
	scans         int
}

func (r *uploadRepo) GetImportJob(context.Context, dbscope.Transaction, string) (upload.ImportJob, error) {
	return upload.ImportJob{}, errors.New("unused")
}
func (r *uploadRepo) InsertAuthorization(context.Context, dbscope.Transaction, upload.Authorization) error {
	return nil
}
func (r *uploadRepo) GetAuthorization(context.Context, dbscope.Transaction, string) (upload.Authorization, error) {
	return r.authorization, nil
}
func (r *uploadRepo) ConsumeIssuedAuthorization(context.Context, dbscope.Transaction, string, time.Time) (bool, error) {
	r.consumed = true
	return true, nil
}
func (r *uploadRepo) RevokeAuthorization(context.Context, dbscope.Transaction, string, string) error {
	return nil
}
func (r *uploadRepo) EnqueueScan(context.Context, dbscope.Transaction, upload.ScanTicket) error {
	r.scans++
	return nil
}

type objectStore struct{ metadata upload.ObjectMetadata }

func (s objectStore) HeadObject(context.Context, string) (upload.ObjectMetadata, error) {
	return s.metadata, nil
}

func TestUploadCompletionStopsWhenEpochChangesAfterObjectHead(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	principal := mustPrincipal(t, security.AuthorityIOSUser)
	authorization := upload.Authorization{
		ID: "upl_01J00000000000000000000000", JobID: "job_01J00000000000000000000000",
		OwnerAccountID: principal.AccountID(), AccountEpoch: principal.AccountEpoch(),
		ObjectKey: "quarantine/job/object", ContentLength: 1024,
		ChecksumSHA256: repeatHex('a'), ContentType: "application/zip",
		CreatedAt: now.Add(-time.Minute), ExpiresAt: now.Add(time.Minute), Status: "issued",
	}
	repository := &uploadRepo{authorization: authorization}
	guard := &sequenceGuard{failAt: 2}
	inner := &upload.Service{
		Transactions: fakeExecutor{}, Repository: repository,
		Objects: objectStore{metadata: upload.ObjectMetadata{
			ObjectKey: authorization.ObjectKey, VersionID: "version-1", ETag: "etag",
			ContentLength: authorization.ContentLength, ChecksumSHA256: authorization.ChecksumSHA256,
			ContentType: authorization.ContentType,
		}},
		Now: func() time.Time { return now },
	}
	err := (Upload{Guard: guard, Inner: inner}).Complete(context.Background(), principal, authorization.ID)
	if !errors.Is(err, epochguard.ErrStaleAccountEpoch) {
		t.Fatalf("expected stale epoch, got %v", err)
	}
	if repository.consumed || repository.scans != 0 {
		t.Fatalf("stale upload reached irreversible work: consumed=%v scans=%d", repository.consumed, repository.scans)
	}
}

type candidateSource struct {
	done bool
}

func (s *candidateSource) Next(context.Context) (preview.Candidate, error) {
	if s.done {
		return preview.Candidate{}, preview.ErrEndOfCandidates
	}
	s.done = true
	return preview.Candidate{SourceRow: 2, Title: "A", Fingerprint: repeatHex('a')}, nil
}

type previewRepo struct{ finalized bool }

func (*previewRepo) InsertDraft(context.Context, dbscope.Transaction, preview.Record) error {
	return nil
}
func (*previewRepo) InsertCandidate(context.Context, dbscope.Transaction, string, int, preview.Candidate, string) error {
	return nil
}
func (r *previewRepo) Finalize(context.Context, dbscope.Transaction, string, int, string, string) (bool, error) {
	r.finalized = true
	return true, nil
}

func TestPreviewDoesNotFinalizeAfterEpochChange(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	principal := mustPrincipal(t, security.AuthorityWorkerLease)
	repository := &previewRepo{}
	guard := &sequenceGuard{failAt: 2}
	inner := &preview.Materializer{Transactions: fakeExecutor{}, Repository: repository, IDs: fakeIDs{value: "prv_01J00000000000000000000000"}, Now: func() time.Time { return now }}
	_, err := (Preview{Guard: guard, Inner: inner}).Materialize(context.Background(), principal, preview.Draft{
		JobID:         "job_01J00000000000000000000000",
		Source:        preview.SourceBinding{ObjectKey: "quarantine/job/object", ObjectVersionID: "version-1", ChecksumSHA256: repeatHex('b')},
		Adapter:       preview.AdapterBinding{AdapterID: "generic-csv", AdapterVersion: "1.0.0", ArtifactSHA256: repeatHex('c')},
		OptionsSHA256: repeatHex('d'),
	}, &candidateSource{})
	if !errors.Is(err, epochguard.ErrStaleAccountEpoch) {
		t.Fatalf("expected stale epoch, got %v", err)
	}
	if repository.finalized {
		t.Fatal("stale Preview was finalized")
	}
}

type applyRepo struct {
	preview    applydomain.Preview
	claimCalls int
	applyCalls int
	completed  bool
}

func (r *applyRepo) GetPreview(context.Context, dbscope.Transaction, string) (applydomain.Preview, error) {
	return r.preview, nil
}
func (r *applyRepo) ClaimIdempotency(_ context.Context, _ dbscope.Transaction, claim applydomain.Claim) (applydomain.ClaimResult, error) {
	r.claimCalls++
	return applydomain.ClaimResult{Disposition: applydomain.ClaimNew, ApplyID: claim.ApplyID}, nil
}
func (r *applyRepo) ApplyMaterializedPreview(context.Context, dbscope.Transaction, string, string, applydomain.DuplicatePolicy) (applydomain.Counts, error) {
	r.applyCalls++
	return applydomain.Counts{Created: 1}, nil
}
func (r *applyRepo) CompleteApply(context.Context, dbscope.Transaction, string, applydomain.Counts, time.Time) error {
	r.completed = true
	return nil
}

func TestApplyStopsBeforeMemoryWriteWhenEpochChanges(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	principal := mustPrincipal(t, security.AuthorityIOSUser)
	repository := &applyRepo{preview: applydomain.Preview{
		ID: "prv_01J00000000000000000000000", OwnerAccountID: principal.AccountID(),
		AccountEpoch: principal.AccountEpoch(), PreviewSHA256: repeatHex('a'), CandidateCount: 1,
		Status: "ready", ExpiresAt: now.Add(time.Hour),
	}}
	guard := &sequenceGuard{failAt: 3}
	inner := &applydomain.Service{Transactions: fakeExecutor{}, Repository: repository, IDs: fakeIDs{value: "apl_01J00000000000000000000000"}, Now: func() time.Time { return now }}
	_, err := (Apply{Guard: guard, Inner: inner}).Apply(context.Background(), principal, applydomain.Request{
		PreviewID: repository.preview.ID, PreviewSHA256: repository.preview.PreviewSHA256,
		IdempotencyKey: "idem_01J0000000000000000000000", DuplicatePolicy: applydomain.DuplicateSkipExisting,
	})
	if !errors.Is(err, epochguard.ErrStaleAccountEpoch) {
		t.Fatalf("expected stale epoch, got %v", err)
	}
	if repository.claimCalls != 1 || repository.applyCalls != 0 || repository.completed {
		t.Fatalf("stale Apply reached Memory write: claim=%d apply=%d completed=%v", repository.claimCalls, repository.applyCalls, repository.completed)
	}
}

func TestFencedServicesRequireGuard(t *testing.T) {
	principal := mustPrincipal(t, security.AuthorityIOSUser)
	if _, err := (Apply{}).Apply(context.Background(), principal, applydomain.Request{}); !errors.Is(err, ErrFenceRequired) {
		t.Fatalf("expected required fence, got %v", err)
	}
}

func mustPrincipal(t *testing.T, authority security.Authority) security.Principal {
	t.Helper()
	principal, err := security.NewVerifiedPrincipal("acct_01J00000000000000000000000", 7, authority)
	if err != nil {
		t.Fatal(err)
	}
	return principal
}

func repeatHex(value byte) string {
	result := make([]byte, 64)
	for index := range result {
		result[index] = value
	}
	return string(result)
}
