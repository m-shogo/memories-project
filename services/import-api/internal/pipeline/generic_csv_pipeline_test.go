package pipeline

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/adapters/genericcsv"
	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/preview"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

type pipelineTx struct{}

func (pipelineTx) Exec(context.Context, string, ...any) error { return nil }
func (pipelineTx) Commit() error                              { return nil }
func (pipelineTx) Rollback() error                            { return nil }

type pipelineExecutor struct {
	calls int
}

func (e *pipelineExecutor) WithinPrincipal(ctx context.Context, _ security.Principal, _ dbscope.Role, fn func(context.Context, dbscope.Transaction) error) error {
	e.calls++
	return fn(ctx, pipelineTx{})
}

type pipelineIDs struct{}

func (pipelineIDs) NewID(string) (string, error) {
	return "prv_01J00000000000000000000000", nil
}

type pipelineRepository struct {
	draft          preview.Record
	candidates     []preview.Candidate
	rejections     []preview.Rejection
	finalized      bool
	acceptedCount  int
	rejectedCount  int
	previewSHA256  string
	optionsSHA256  string
}

func (r *pipelineRepository) InsertDraft(_ context.Context, _ dbscope.Transaction, record preview.Record) error {
	r.draft = record
	r.optionsSHA256 = record.OptionsSHA256
	return nil
}

func (r *pipelineRepository) InsertCandidate(_ context.Context, _ dbscope.Transaction, _ string, _ int, candidate preview.Candidate, _ string) error {
	r.candidates = append(r.candidates, candidate)
	return nil
}

func (r *pipelineRepository) InsertRejection(_ context.Context, _ dbscope.Transaction, _ string, _ int, rejection preview.Rejection, _ string) error {
	r.rejections = append(r.rejections, rejection)
	return nil
}

func (r *pipelineRepository) FinalizeWithReport(_ context.Context, _ dbscope.Transaction, _ string, accepted, rejected int, _, _, previewHash string) (bool, error) {
	r.finalized = true
	r.acceptedCount = accepted
	r.rejectedCount = rejected
	r.previewSHA256 = previewHash
	return true, nil
}

func TestGenericCSVPreviewPipelineBindsActualOptionsAndPersistsAllRowDecisions(t *testing.T) {
	executor := &pipelineExecutor{}
	repository := &pipelineRepository{}
	materializer := &preview.AtomicMaterializer{
		Transactions: executor,
		Repository:   repository,
		IDs:          pipelineIDs{},
		Now:          func() time.Time { return time.Unix(1_800_000_000, 0).UTC() },
	}
	pipeline := GenericCSVPreviewPipeline{Materializer: materializer}
	principal := pipelineWorkerPrincipal(t)
	draft := pipelineDraft()
	draft.OptionsSHA256 = ""

	result, err := pipeline.Run(
		context.Background(),
		principal,
		strings.NewReader("title,note\n\"\",missing\nA,ok\n"),
		genericcsv.Options{TitleColumn: " Title ", TextColumn: "Note"},
		draft,
	)
	if err != nil {
		t.Fatal(err)
	}
	if executor.calls != 1 {
		t.Fatalf("expected exactly one transaction boundary, got %d", executor.calls)
	}
	if !repository.finalized || repository.acceptedCount != 1 || repository.rejectedCount != 1 {
		t.Fatalf("unexpected repository state: %#v", repository)
	}
	if len(repository.candidates) != 1 || len(repository.rejections) != 1 {
		t.Fatalf("row decisions were not persisted together: candidates=%#v rejections=%#v", repository.candidates, repository.rejections)
	}
	if len(result.OptionsSHA256) != 64 || result.OptionsSHA256 != repository.optionsSHA256 {
		t.Fatalf("actual options were not bound to Preview: result=%q repository=%q", result.OptionsSHA256, repository.optionsSHA256)
	}
	if result.Preview.CandidateCount != 1 || result.Preview.RejectedCount != 1 || result.Preview.PreviewSHA256 != repository.previewSHA256 {
		t.Fatalf("unexpected Preview result: %#v", result.Preview)
	}
	if result.Summary.RowsRead != 2 || result.Summary.AcceptedRows != 1 || result.Summary.RejectedRows != 1 {
		t.Fatalf("summary does not account for source rows: %#v", result.Summary)
	}
}

func TestGenericCSVPreviewPipelineRejectsCallerOptionsDigestMismatchBeforeDatabaseWork(t *testing.T) {
	executor := &pipelineExecutor{}
	pipeline := GenericCSVPreviewPipeline{Materializer: &preview.AtomicMaterializer{Transactions: executor}}
	draft := pipelineDraft()
	draft.OptionsSHA256 = strings.Repeat("a", 64)

	result, err := pipeline.Run(
		context.Background(),
		pipelineWorkerPrincipal(t),
		strings.NewReader("title\nA\n"),
		genericcsv.Options{TitleColumn: "title"},
		draft,
	)
	if !errors.Is(err, ErrGenericCSVOptionsDigestMismatch) {
		t.Fatalf("expected options mismatch, got %v", err)
	}
	if executor.calls != 0 {
		t.Fatalf("options mismatch reached database transaction: %d calls", executor.calls)
	}
	if len(result.OptionsSHA256) != 64 || result.OptionsSHA256 == draft.OptionsSHA256 {
		t.Fatalf("computed digest evidence missing: %#v", result)
	}
}

func TestGenericCSVPreviewPipelineRejectsWrongAdapterBeforeParsing(t *testing.T) {
	executor := &pipelineExecutor{}
	pipeline := GenericCSVPreviewPipeline{Materializer: &preview.AtomicMaterializer{Transactions: executor}}
	draft := pipelineDraft()
	draft.Adapter.AdapterID = "generic-json"

	_, err := pipeline.Run(
		context.Background(),
		pipelineWorkerPrincipal(t),
		strings.NewReader("not,a,valid,mapping"),
		genericcsv.Options{TitleColumn: "missing"},
		draft,
	)
	if !errors.Is(err, ErrGenericCSVAdapterMismatch) {
		t.Fatalf("expected adapter mismatch, got %v", err)
	}
	if executor.calls != 0 {
		t.Fatalf("adapter mismatch reached database transaction: %d calls", executor.calls)
	}
}

func pipelineWorkerPrincipal(t *testing.T) security.Principal {
	t.Helper()
	principal, err := security.NewVerifiedPrincipal(
		"acct_01J00000000000000000000000",
		7,
		security.AuthorityWorkerLease,
	)
	if err != nil {
		t.Fatal(err)
	}
	return principal
}

func pipelineDraft() preview.Draft {
	return preview.Draft{
		JobID: "job_01J00000000000000000000000",
		Source: preview.SourceBinding{
			ObjectKey:       "quarantine/job/object",
			ObjectVersionID: "version-1",
			ChecksumSHA256:  strings.Repeat("c", 64),
		},
		Adapter: preview.AdapterBinding{
			AdapterID:      "generic-csv",
			AdapterVersion: "1.0.0",
			ArtifactSHA256: strings.Repeat("d", 64),
		},
	}
}
