package genericcsv

import (
	"context"
	"errors"
	"reflect"
	"strings"
	"testing"
)

func TestIteratorStreamsOneRowPerCallAndTracksSummary(t *testing.T) {
	iterator, err := NewIterator(strings.NewReader("title,note\nA,=SUM(1,2)\n\"\",missing\n"), Options{
		TitleColumn: "title",
		TextColumn:  "note",
	})
	if err != nil {
		t.Fatal(err)
	}

	first, err := iterator.Next(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if !first.Accepted || first.Candidate.Title != "A" || !containsIssue(first.Issues, IssueFormulaLikeText) {
		t.Fatalf("unexpected first row: %#v", first)
	}

	second, err := iterator.Next(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if second.Accepted || !containsIssue(second.Issues, IssueTitleRequired) {
		t.Fatalf("unexpected second row: %#v", second)
	}

	if _, err := iterator.Next(context.Background()); !errors.Is(err, ErrEndOfRows) {
		t.Fatalf("expected end of rows, got %v", err)
	}
	if _, err := iterator.Next(context.Background()); !errors.Is(err, ErrEndOfRows) {
		t.Fatalf("end of rows must remain stable, got %v", err)
	}

	summary := iterator.Summary()
	if summary.RowsRead != 2 || summary.AcceptedRows != 1 || summary.RejectedRows != 1 || summary.WarningRows != 2 {
		t.Fatalf("unexpected summary: %#v", summary)
	}
}

func TestIteratorCancellationIsSticky(t *testing.T) {
	iterator, err := NewIterator(strings.NewReader("title\nA\n"), Options{TitleColumn: "title"})
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	if _, err := iterator.Next(ctx); !errors.Is(err, context.Canceled) {
		t.Fatalf("expected cancellation, got %v", err)
	}
	if _, err := iterator.Next(context.Background()); !errors.Is(err, context.Canceled) {
		t.Fatalf("partially cancelled iterator must not resume, got %v", err)
	}
	if iterator.Summary().RowsRead != 0 {
		t.Fatal("cancelled iterator consumed a row")
	}
}

func TestIteratorFatalParserFailureIsSticky(t *testing.T) {
	iterator, err := NewIterator(strings.NewReader("title,note\nA\nB,ok\n"), Options{
		TitleColumn: "title",
		TextColumn:  "note",
	})
	if err != nil {
		t.Fatal(err)
	}

	if _, err := iterator.Next(context.Background()); !errors.Is(err, ErrInconsistentColumns) {
		t.Fatalf("expected inconsistent columns, got %v", err)
	}
	if _, err := iterator.Next(context.Background()); !errors.Is(err, ErrInconsistentColumns) {
		t.Fatalf("failed iterator must not continue, got %v", err)
	}
	if iterator.Summary().RowsRead != 1 {
		t.Fatalf("unexpected summary after failure: %#v", iterator.Summary())
	}
}

func TestIteratorMatchesParserForValidInput(t *testing.T) {
	input := "title,date,url,note\nA,2026-07-01,https://example.com/a,note\nB,bad,http://user:pass@example.com/private,=1+1\n"
	options := Options{
		TitleColumn: "title",
		DateColumn:  "date",
		DateLayout:  "2006-01-02",
		URLColumn:   "url",
		TextColumn:  "note",
	}

	var parserResults []Result
	parserSummary, err := (Parser{}).Parse(strings.NewReader(input), options, func(result Result) error {
		parserResults = append(parserResults, result)
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}

	iterator, err := NewIterator(strings.NewReader(input), options)
	if err != nil {
		t.Fatal(err)
	}
	var iteratorResults []Result
	for {
		result, err := iterator.Next(context.Background())
		if errors.Is(err, ErrEndOfRows) {
			break
		}
		if err != nil {
			t.Fatal(err)
		}
		iteratorResults = append(iteratorResults, result)
	}

	if !reflect.DeepEqual(parserResults, iteratorResults) {
		t.Fatalf("iterator diverged from parser:\nparser=%#v\niterator=%#v", parserResults, iteratorResults)
	}
	if !reflect.DeepEqual(parserSummary, iterator.Summary()) {
		t.Fatalf("summary mismatch: parser=%#v iterator=%#v", parserSummary, iterator.Summary())
	}
}
