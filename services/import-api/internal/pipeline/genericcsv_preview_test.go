package pipeline

import (
	"context"
	"errors"
	"io"
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

type fakePreviewRepository struct {
	candidates    []preview.Candidate
	insertFailure error
}

func (*fakePreviewRepository) InsertDraft(context.Context, dbscope.Transaction, preview.Record) error {
	return nil
}
func (r *fakePreviewRepository) InsertCandidate(_ context.Context, _ dbscope.Transaction, _ string, _ int, candidate preview.Candidate, _ string) error {
	if r.insertFailure != nil {
		return r.insertFailure
	}
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
	result, err := service.Materialize(context.Background(), principal, io.NopCloser(strings.NewReader(input)), validRequest())
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
	input := newBlockingReadCloser()

	finished := make(chan error, 1)
	go func() {
		_, err := service.Materialize(context.Background(), principal, input, validRequest())
		finished <- err
	}()

	select {
	case err := <-finished:
		if !errors.Is(err, preview.ErrAuthorityNotAllowed) {
			t.Fatalf("expected authority rejection, got %v", err)
		}
	case <-time.After(time.Second):
		t.Fatal("pipeline did not interrupt the blocked reader")
	}
	select {
	case <-input.closed:
	default:
		t.Fatal("pipeline did not close its owned input")
	}
}

func TestGenericCSVPipelineClosesInputWhenPreviewInsertFails(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	insertFailure := errors.New("candidate insert failed")
	repository := &fakePreviewRepository{insertFailure: insertFailure}
	materializer := &preview.Materializer{Transactions: fakeExecutor{}, Repository: repository, IDs: fakeIDs{value: "prv_01J00000000000000000000000"}, Now: func() time.Time { return now }}
	service := GenericCSVPreview{Materializer: materializer}
	principal, _ := security.NewVerifiedPrincipal("acct_01J00000000000000000000000", 7, security.AuthorityWorkerLease)

	reader, writer := io.Pipe()
	writerDone := make(chan struct{})
	go func() {
		defer close(writerDone)
		_, _ = io.WriteString(writer, "title,url\nA,https://example.com/a\n")
		_, _ = io.WriteString(writer, strings.Repeat("B,https://example.com/b\n", 1000))
		_ = writer.Close()
	}()

	finished := make(chan error, 1)
	go func() {
		_, err := service.Materialize(context.Background(), principal, reader, validRequest())
		finished <- err
	}()

	select {
	case err := <-finished:
		if !errors.Is(err, insertFailure) {
			t.Fatalf("expected repository failure, got %v", err)
		}
	case <-time.After(time.Second):
		t.Fatal("pipeline deadlocked after Preview insert failure")
	}
	select {
	case <-writerDone:
	case <-time.After(time.Second):
		t.Fatal("closing the pipeline input did not release the writer")
	}
}

type blockingReadCloser struct {
	closed    chan struct{}
	closeOnce sync.Once
}

func newBlockingReadCloser() *blockingReadCloser {
	return &blockingReadCloser{closed: make(chan struct{})}
}

func (r *blockingReadCloser) Read([]byte) (int, error) {
	<-r.closed
	return 0, io.ErrClosedPipe
}

func (r *blockingReadCloser) Close() error {
	r.closeOnce.Do(func() { close(r.closed) })
	return nil
}
