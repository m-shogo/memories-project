package pipeline

import (
	"context"
	"errors"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/adapters/genericcsv"
	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/preview"
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

type fakePreviewRepository struct{ candidates []preview.Candidate }

func (*fakePreviewRepository) InsertDraft(context.Context, dbscope.Transaction, preview.Record) error {
	return nil
}
func (r *fakePreviewRepository) InsertCandidate(_ context.Context, _ dbscope.Transaction, _ string, _ int, candidate preview.Candidate, _ string) error {
	r.candidates = append(r.candidates, candidate)
	return nil
}
func (*fakePreviewRepository) Finalize(context.Context, dbscope.Transaction, string, int, string, string) (bool, error) {
	return true, nil
}

type reportSink struct {
	mu      sync.Mutex
	reports []RowReport
}

func (s *reportSink) Record(_ context.Context, report RowReport) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.reports = append(s.reports, report)
	return nil
}

func TestGenericCSVPipelineStreamsAcceptedCandidatesAndReportsRejectedRows(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	repository := &fakePreviewRepository{}
	reports := &reportSink{}
	materializer := &preview.Materializer{Transactions: fakeExecutor{}, Repository: repository, IDs: fakeIDs{value: "prv_01J00000000000000000000000"}, Now: func() time.Time { return now }}
	service := GenericCSVPreview{Materializer: materializer, Reports: reports}
	principal, _ := security.NewVerifiedPrincipal("acct_01J00000000000000000000000", 7, security.AuthorityWorkerLease)
	input := "title,url\n\"\",https://example.com/rejected\nA,https://example.com/a\n"
	result, err := service.Materialize(context.Background(), principal, strings.NewReader(input), validRequest())
	if err != nil {
		t.Fatal(err)
	}
	if result.Summary.RowsRead != 2 || result.Summary.AcceptedRows != 1 || result.Summary.RejectedRows != 1 || result.Preview.CandidateCount != 1 {
		t.Fatalf("unexpected result: %#v", result)
	}
	if len(repository.candidates) != 1 || repository.candidates[0].Title != "A" {
		t.Fatalf("unexpected candidates: %#v", repository.candidates)
	}
	if len(reports.reports) != 2 || reports.reports[0].Accepted || !reports.reports[1].Accepted {
		t.Fatalf("unexpected reports: %#v", reports.reports)
	}
}

func TestCSVOptionsHashChangesWithMapping(t *testing.T) {
	first, err := hashCSVOptions(genericcsv.Options{TitleColumn: "title", URLColumn: "url"})
	if err != nil {
		t.Fatal(err)
	}
	second, err := hashCSVOptions(genericcsv.Options{TitleColumn: "name", URLColumn: "url"})
	if err != nil {
		t.Fatal(err)
	}
	if first == second || len(first) != 64 || len(second) != 64 {
		t.Fatalf("mapping hash did not change: %q %q", first, second)
	}
}

func validRequest() GenericCSVRequest {
	return GenericCSVRequest{
		JobID:   "job_01J00000000000000000000000",
		Source:  preview.SourceBinding{ObjectKey: "quarantine/job/object", ObjectVersionID: "version-1", ChecksumSHA256: repeatHex('a')},
		Adapter: preview.AdapterBinding{AdapterID: "generic-csv", AdapterVersion: "1.0.0", ArtifactSHA256: repeatHex('b')},
		Options: genericcsv.Options{TitleColumn: "title", URLColumn: "url"},
	}
}
func repeatHex(value byte) string {
	result := make([]byte, 64)
	for index := range result {
		result[index] = value
	}
	return string(result)
}

func TestGenericCSVPipelineCancelsParserWhenMaterializerRejectsAuthority(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	materializer := &preview.Materializer{Transactions: fakeExecutor{}, Repository: &fakePreviewRepository{}, IDs: fakeIDs{value: "prv_01J00000000000000000000000"}, Now: func() time.Time { return now }}
	service := GenericCSVPreview{Materializer: materializer}
	principal, _ := security.NewVerifiedPrincipal("acct_01J00000000000000000000000", 7, security.AuthorityIOSUser)
	input := "title\n" + strings.Repeat("A\n", 1000)
	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()
	_, err := service.Materialize(ctx, principal, strings.NewReader(input), validRequest())
	if !errors.Is(err, preview.ErrAuthorityNotAllowed) {
		t.Fatalf("expected authority rejection, got %v", err)
	}
}
