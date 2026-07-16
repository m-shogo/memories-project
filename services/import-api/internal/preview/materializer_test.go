package preview

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

type sliceSource struct {
	values []Candidate
	index  int
	err    error
}

func (s *sliceSource) Next(context.Context) (Candidate, error) {
	if s.err != nil {
		return Candidate{}, s.err
	}
	if s.index >= len(s.values) {
		return Candidate{}, ErrEndOfCandidates
	}
	value := s.values[s.index]
	s.index++
	return value, nil
}

type fakeRepository struct {
	draft           Record
	candidates      []Candidate
	candidateHashes []string
	finalized       bool
	count           int
	candidatesHash  string
	previewHash     string
}

func (r *fakeRepository) InsertDraft(_ context.Context, _ dbscope.Transaction, record Record) error {
	r.draft = record
	return nil
}
func (r *fakeRepository) InsertCandidate(_ context.Context, _ dbscope.Transaction, _ string, _ int, candidate Candidate, candidateHash string) error {
	r.candidates = append(r.candidates, candidate)
	r.candidateHashes = append(r.candidateHashes, candidateHash)
	return nil
}
func (r *fakeRepository) Finalize(_ context.Context, _ dbscope.Transaction, _ string, count int, candidatesHash, previewHash string) (bool, error) {
	r.finalized = true
	r.count = count
	r.candidatesHash = candidatesHash
	r.previewHash = previewHash
	return true, nil
}

func TestMaterializerCreatesImmutableHashBoundPreview(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	principal := workerPrincipal(t)
	repository := &fakeRepository{}
	occurredAt := now.Add(-time.Hour)
	source := &sliceSource{values: []Candidate{
		{SourceRow: 2, Title: "Movie A", OccurredAt: &occurredAt, URL: "https://example.com/a", Text: "liked", Fingerprint: repeatHex('a'), Issues: []string{"IMPORT_CSV_FORMULA_LIKE_TEXT"}},
		{SourceRow: 3, Title: "Movie B", Fingerprint: repeatHex('b')},
	}}
	materializer := Materializer{Transactions: fakeExecutor{}, Repository: repository, IDs: fakeIDs{value: "prv_01J00000000000000000000000"}, Now: func() time.Time { return now }}
	record, err := materializer.Materialize(context.Background(), principal, validDraft(), source)
	if err != nil {
		t.Fatal(err)
	}
	if record.Status != "ready" || record.CandidateCount != 2 || len(record.PreviewSHA256) != 64 || len(record.CandidatesSHA256) != 64 {
		t.Fatalf("unexpected record: %#v", record)
	}
	if !repository.finalized || repository.count != 2 || repository.previewHash != record.PreviewSHA256 || len(repository.candidates) != 2 {
		t.Fatalf("repository mismatch: %#v", repository)
	}
}

func TestMaterializerHashChangesWhenCandidateChanges(t *testing.T) {
	first := materializeOne(t, "A")
	second := materializeOne(t, "B")
	if first.PreviewSHA256 == second.PreviewSHA256 || first.CandidatesSHA256 == second.CandidatesSHA256 {
		t.Fatal("candidate changes must change preview hashes")
	}
}

func TestMaterializerRejectsNonWorkerAuthority(t *testing.T) {
	principal, _ := security.NewVerifiedPrincipal("acct_01J00000000000000000000000", 7, security.AuthorityIOSUser)
	materializer := Materializer{}
	_, err := materializer.Materialize(context.Background(), principal, validDraft(), &sliceSource{})
	if !errors.Is(err, ErrAuthorityNotAllowed) {
		t.Fatalf("expected authority error, got %v", err)
	}
}

func TestMaterializerRejectsInvalidCandidate(t *testing.T) {
	materializer := Materializer{Transactions: fakeExecutor{}, Repository: &fakeRepository{}, IDs: fakeIDs{value: "prv_01J00000000000000000000000"}, Now: func() time.Time { return time.Unix(1_800_000_000, 0).UTC() }}
	_, err := materializer.Materialize(context.Background(), workerPrincipal(t), validDraft(), &sliceSource{values: []Candidate{{SourceRow: 2, Title: "", Fingerprint: repeatHex('a')}}})
	if !errors.Is(err, ErrInvalidCandidate) {
		t.Fatalf("expected candidate error, got %v", err)
	}
}

func materializeOne(t *testing.T, title string) Record {
	t.Helper()
	now := time.Unix(1_800_000_000, 0).UTC()
	materializer := Materializer{Transactions: fakeExecutor{}, Repository: &fakeRepository{}, IDs: fakeIDs{value: "prv_01J00000000000000000000000"}, Now: func() time.Time { return now }}
	record, err := materializer.Materialize(context.Background(), workerPrincipal(t), validDraft(), &sliceSource{values: []Candidate{{SourceRow: 2, Title: title, Fingerprint: repeatHex('a')}}})
	if err != nil {
		t.Fatal(err)
	}
	return record
}

func validDraft() Draft {
	return Draft{
		JobID:         "job_01J00000000000000000000000",
		Source:        SourceBinding{ObjectKey: "quarantine/job/object", ObjectVersionID: "version-1", ChecksumSHA256: repeatHex('c')},
		Adapter:       AdapterBinding{AdapterID: "generic-csv", AdapterVersion: "1.0.0", ArtifactSHA256: repeatHex('d')},
		OptionsSHA256: repeatHex('e'),
	}
}

func workerPrincipal(t *testing.T) security.Principal {
	t.Helper()
	principal, err := security.NewVerifiedPrincipal("acct_01J00000000000000000000000", 7, security.AuthorityWorkerLease)
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
