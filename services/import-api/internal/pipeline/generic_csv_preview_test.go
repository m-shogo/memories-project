package pipeline

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/m-shogo/memories-project/services/import-api/internal/adapters/genericcsv"
	"github.com/m-shogo/memories-project/services/import-api/internal/preview"
)

func TestGenericCSVPreviewSourcePreservesAcceptedAndRejectedRowOrder(t *testing.T) {
	iterator, err := genericcsv.NewIterator(strings.NewReader("title,note\n\"\",missing\nA,\"=SUM(1,2)\"\n"), genericcsv.Options{
		TitleColumn: "title",
		TextColumn:  "note",
	})
	if err != nil {
		t.Fatal(err)
	}
	source, err := NewGenericCSVPreviewSource(iterator)
	if err != nil {
		t.Fatal(err)
	}

	first, err := source.NextEvent(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if first.Rejection == nil || first.Candidate != nil || first.Rejection.SourceRow != 2 {
		t.Fatalf("unexpected rejection event: %#v", first)
	}
	if len(first.Rejection.Issues) != 1 || first.Rejection.Issues[0] != "IMPORT_CSV_TITLE_REQUIRED" {
		t.Fatalf("unsafe rejection report: %#v", first.Rejection)
	}

	second, err := source.NextEvent(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if second.Candidate == nil || second.Rejection != nil || second.Candidate.SourceRow != 3 || second.Candidate.Title != "A" {
		t.Fatalf("unexpected candidate event: %#v", second)
	}
	if len(second.Candidate.Issues) != 1 || second.Candidate.Issues[0] != "IMPORT_CSV_FORMULA_LIKE_TEXT" {
		t.Fatalf("candidate warning was not preserved: %#v", second.Candidate)
	}

	if _, err := source.NextEvent(context.Background()); !errors.Is(err, preview.ErrEndOfCandidates) {
		t.Fatalf("expected end of candidates, got %v", err)
	}
	if _, err := source.NextEvent(context.Background()); !errors.Is(err, preview.ErrEndOfCandidates) {
		t.Fatalf("end state must remain stable, got %v", err)
	}

	summary := source.Summary()
	if summary.RowsRead != 2 || summary.AcceptedRows != 1 || summary.RejectedRows != 1 || summary.WarningRows != 2 {
		t.Fatalf("unexpected source summary: %#v", summary)
	}
}

func TestGenericCSVPreviewSourcePropagatesCancellationWithoutResume(t *testing.T) {
	iterator, err := genericcsv.NewIterator(strings.NewReader("title\nA\n"), genericcsv.Options{TitleColumn: "title"})
	if err != nil {
		t.Fatal(err)
	}
	source, err := NewGenericCSVPreviewSource(iterator)
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	if _, err := source.NextEvent(ctx); !errors.Is(err, context.Canceled) {
		t.Fatalf("expected cancellation, got %v", err)
	}
	if _, err := source.NextEvent(context.Background()); !errors.Is(err, context.Canceled) {
		t.Fatalf("cancelled source must not resume, got %v", err)
	}
}

func TestGenericCSVPreviewSourceMakesParserFailureSticky(t *testing.T) {
	iterator, err := genericcsv.NewIterator(strings.NewReader("title,note\nA\nB,ok\n"), genericcsv.Options{
		TitleColumn: "title",
		TextColumn:  "note",
	})
	if err != nil {
		t.Fatal(err)
	}
	source, err := NewGenericCSVPreviewSource(iterator)
	if err != nil {
		t.Fatal(err)
	}

	if _, err := source.NextEvent(context.Background()); !errors.Is(err, genericcsv.ErrInconsistentColumns) {
		t.Fatalf("expected parser failure, got %v", err)
	}
	if _, err := source.NextEvent(context.Background()); !errors.Is(err, genericcsv.ErrInconsistentColumns) {
		t.Fatalf("failed source must not resume, got %v", err)
	}
}
