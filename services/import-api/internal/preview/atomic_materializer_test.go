package preview

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
)

type atomicSliceSource struct {
	events []RowEvent
	index  int
	err    error
}

func (s *atomicSliceSource) NextEvent(context.Context) (RowEvent, error) {
	if s.err != nil {
		return RowEvent{}, s.err
	}
	if s.index >= len(s.events) {
		return RowEvent{}, ErrEndOfCandidates
	}
	event := s.events[s.index]
	s.index++
	return event, nil
}

type atomicFakeRepository struct {
	draft              Record
	candidates         []Candidate
	candidateHashes    []string
	rejections         []Rejection
	rejectionHashes    []string
	finalized          bool
	acceptedCount      int
	rejectedCount      int
	candidatesSHA256   string
	rejectionsSHA256   string
	previewSHA256      string
	insertRejectionErr error
}

func (r *atomicFakeRepository) InsertDraft(_ context.Context, _ dbscope.Transaction, record Record) error {
	r.draft = record
	return nil
}

func (r *atomicFakeRepository) InsertCandidate(_ context.Context, _ dbscope.Transaction, _ string, _ int, candidate Candidate, candidateHash string) error {
	r.candidates = append(r.candidates, candidate)
	r.candidateHashes = append(r.candidateHashes, candidateHash)
	return nil
}

func (r *atomicFakeRepository) InsertRejection(_ context.Context, _ dbscope.Transaction, _ string, _ int, rejection Rejection, rejectionHash string) error {
	if r.insertRejectionErr != nil {
		return r.insertRejectionErr
	}
	r.rejections = append(r.rejections, rejection)
	r.rejectionHashes = append(r.rejectionHashes, rejectionHash)
	return nil
}

func (r *atomicFakeRepository) FinalizeWithReport(_ context.Context, _ dbscope.Transaction, _ string, accepted, rejected int, candidatesHash, rejectionsHash, previewHash string) (bool, error) {
	r.finalized = true
	r.acceptedCount = accepted
	r.rejectedCount = rejected
	r.candidatesSHA256 = candidatesHash
	r.rejectionsSHA256 = rejectionsHash
	r.previewSHA256 = previewHash
	return true, nil
}

func TestAtomicMaterializerPersistsCandidateAndSafeRejectionInOneBoundary(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	repository := &atomicFakeRepository{}
	materializer := AtomicMaterializer{
		Transactions: fakeExecutor{},
		Repository:   repository,
		IDs:          fakeIDs{value: "prv_01J00000000000000000000000"},
		Now:          func() time.Time { return now },
	}
	source := &atomicSliceSource{events: []RowEvent{
		{Candidate: &Candidate{SourceRow: 2, Title: "Movie A", Fingerprint: repeatHex('a')}},
		{Rejection: &Rejection{SourceRow: 3, Issues: []string{"IMPORT_CSV_TITLE_REQUIRED"}}},
	}}

	record, err := materializer.Materialize(context.Background(), workerPrincipal(t), validDraft(), source)
	if err != nil {
		t.Fatal(err)
	}
	if record.Status != "ready" || record.CandidateCount != 1 || record.RejectedCount != 1 {
		t.Fatalf("unexpected record: %#v", record)
	}
	if len(record.PreviewSHA256) != 64 || len(record.CandidatesSHA256) != 64 || len(record.RejectionsSHA256) != 64 {
		t.Fatalf("missing hashes: %#v", record)
	}
	if !repository.finalized || repository.acceptedCount != 1 || repository.rejectedCount != 1 {
		t.Fatalf("repository was not finalized atomically: %#v", repository)
	}
	if len(repository.candidates) != 1 || len(repository.rejections) != 1 {
		t.Fatalf("unexpected persisted rows: candidates=%#v rejections=%#v", repository.candidates, repository.rejections)
	}
	if repository.rejections[0].SourceRow != 3 || len(repository.rejections[0].Issues) != 1 {
		t.Fatalf("unsafe or incomplete rejection record: %#v", repository.rejections[0])
	}
}

func TestAtomicMaterializerPreviewHashChangesWhenRejectionChanges(t *testing.T) {
	first := materializeAtomicWithIssue(t, "IMPORT_CSV_TITLE_REQUIRED")
	second := materializeAtomicWithIssue(t, "IMPORT_CSV_URL_INVALID")
	if first.RejectionsSHA256 == second.RejectionsSHA256 || first.PreviewSHA256 == second.PreviewSHA256 {
		t.Fatal("rejection changes must change rejection and Preview hashes")
	}
	if first.CandidatesSHA256 != second.CandidatesSHA256 {
		t.Fatal("unchanged candidates must keep the same candidate hash")
	}
}

func TestAtomicMaterializerRejectsNonMonotonicSourceRows(t *testing.T) {
	materializer := AtomicMaterializer{
		Transactions: fakeExecutor{},
		Repository:   &atomicFakeRepository{},
		IDs:          fakeIDs{value: "prv_01J00000000000000000000000"},
		Now:          func() time.Time { return time.Unix(1_800_000_000, 0).UTC() },
	}
	source := &atomicSliceSource{events: []RowEvent{
		{Candidate: &Candidate{SourceRow: 3, Title: "A", Fingerprint: repeatHex('a')}},
		{Rejection: &Rejection{SourceRow: 3, Issues: []string{"IMPORT_CSV_TITLE_REQUIRED"}}},
	}}
	_, err := materializer.Materialize(context.Background(), workerPrincipal(t), validDraft(), source)
	if !errors.Is(err, ErrInvalidRowEvent) {
		t.Fatalf("expected non-monotonic row rejection, got %v", err)
	}
}

func TestAtomicMaterializerRejectsUnsafeIssueCode(t *testing.T) {
	materializer := AtomicMaterializer{
		Transactions: fakeExecutor{},
		Repository:   &atomicFakeRepository{},
		IDs:          fakeIDs{value: "prv_01J00000000000000000000000"},
		Now:          func() time.Time { return time.Unix(1_800_000_000, 0).UTC() },
	}
	source := &atomicSliceSource{events: []RowEvent{
		{Candidate: &Candidate{SourceRow: 2, Title: "A", Fingerprint: repeatHex('a')}},
		{Rejection: &Rejection{SourceRow: 3, Issues: []string{"IMPORT_CSV_TITLE_REQUIRED\nprivate-value"}}},
	}}
	_, err := materializer.Materialize(context.Background(), workerPrincipal(t), validDraft(), source)
	if !errors.Is(err, ErrInvalidRejection) {
		t.Fatalf("expected unsafe issue-code rejection, got %v", err)
	}
}

func TestAtomicMaterializerRejectsPreviewWithNoAcceptedCandidates(t *testing.T) {
	repository := &atomicFakeRepository{}
	materializer := AtomicMaterializer{
		Transactions: fakeExecutor{},
		Repository:   repository,
		IDs:          fakeIDs{value: "prv_01J00000000000000000000000"},
		Now:          func() time.Time { return time.Unix(1_800_000_000, 0).UTC() },
	}
	source := &atomicSliceSource{events: []RowEvent{
		{Rejection: &Rejection{SourceRow: 2, Issues: []string{"IMPORT_CSV_TITLE_REQUIRED"}}},
	}}
	_, err := materializer.Materialize(context.Background(), workerPrincipal(t), validDraft(), source)
	if !errors.Is(err, ErrInvalidDraft) {
		t.Fatalf("expected empty Preview rejection, got %v", err)
	}
	if repository.finalized {
		t.Fatal("rejection-only Preview must not finalize")
	}
}

func TestAtomicMaterializerStopsWhenRejectionPersistenceFails(t *testing.T) {
	expected := errors.New("write rejection failed")
	repository := &atomicFakeRepository{insertRejectionErr: expected}
	materializer := AtomicMaterializer{
		Transactions: fakeExecutor{},
		Repository:   repository,
		IDs:          fakeIDs{value: "prv_01J00000000000000000000000"},
		Now:          func() time.Time { return time.Unix(1_800_000_000, 0).UTC() },
	}
	source := &atomicSliceSource{events: []RowEvent{
		{Candidate: &Candidate{SourceRow: 2, Title: "A", Fingerprint: repeatHex('a')}},
		{Rejection: &Rejection{SourceRow: 3, Issues: []string{"IMPORT_CSV_TITLE_REQUIRED"}}},
	}}
	_, err := materializer.Materialize(context.Background(), workerPrincipal(t), validDraft(), source)
	if !errors.Is(err, expected) {
		t.Fatalf("expected persistence error, got %v", err)
	}
	if repository.finalized {
		t.Fatal("failed rejection persistence must not finalize Preview")
	}
}

func materializeAtomicWithIssue(t *testing.T, issue string) AtomicRecord {
	t.Helper()
	now := time.Unix(1_800_000_000, 0).UTC()
	materializer := AtomicMaterializer{
		Transactions: fakeExecutor{},
		Repository:   &atomicFakeRepository{},
		IDs:          fakeIDs{value: "prv_01J00000000000000000000000"},
		Now:          func() time.Time { return now },
	}
	source := &atomicSliceSource{events: []RowEvent{
		{Candidate: &Candidate{SourceRow: 2, Title: "A", Fingerprint: repeatHex('a')}},
		{Rejection: &Rejection{SourceRow: 3, Issues: []string{issue}}},
	}}
	record, err := materializer.Materialize(context.Background(), workerPrincipal(t), validDraft(), source)
	if err != nil {
		t.Fatal(err)
	}
	return record
}
