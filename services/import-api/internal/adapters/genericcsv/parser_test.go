package genericcsv

import (
	"bytes"
	"errors"
	"strings"
	"testing"
	"time"
)

func TestParserStreamsMappedCandidates(t *testing.T) {
	input := "title,date,url,note\nMovie A,2026-07-01,https://example.com/a,liked it\nMovie B,2026-07-02,https://example.com/b,watch again\n"
	var results []Result
	summary, err := (Parser{}).Parse(strings.NewReader(input), Options{
		TitleColumn: "title",
		DateColumn:  "date",
		DateLayout:  "2006-01-02",
		URLColumn:   "url",
		TextColumn:  "note",
	}, func(result Result) error {
		results = append(results, result)
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if summary.RowsRead != 2 || summary.AcceptedRows != 2 || len(results) != 2 {
		t.Fatalf("unexpected summary/results: %#v %#v", summary, results)
	}
	if results[0].Candidate.Title != "Movie A" || results[0].Candidate.OccurredAt == nil || results[0].Candidate.OccurredAt.Location() != time.UTC {
		t.Fatalf("unexpected candidate: %#v", results[0].Candidate)
	}
	if len(results[0].Candidate.Fingerprint) != 64 {
		t.Fatal("fingerprint missing")
	}
}

func TestParserRejectsDuplicateNormalizedHeader(t *testing.T) {
	input := "Title, title \nA,B\n"
	_, err := (Parser{}).Parse(strings.NewReader(input), Options{TitleColumn: "Title"}, func(Result) error { return nil })
	if !errors.Is(err, ErrDuplicateHeader) {
		t.Fatalf("expected duplicate header, got %v", err)
	}
}

func TestParserRejectsClientLimitExpansion(t *testing.T) {
	_, err := (Parser{}).Parse(strings.NewReader("title\nA\n"), Options{TitleColumn: "title", MaxRows: DefaultMaxRows + 1}, func(Result) error { return nil })
	if err == nil {
		t.Fatal("expected limit rejection")
	}
}

func TestParserRejectsInputByteLimit(t *testing.T) {
	input := "title\n" + strings.Repeat("a", 32) + "\n"
	_, err := (Parser{}).Parse(strings.NewReader(input), Options{TitleColumn: "title", MaxInputBytes: 12}, func(Result) error { return nil })
	if !errors.Is(err, ErrInputTooLarge) {
		t.Fatalf("expected input byte limit, got %v", err)
	}
}

func TestParserRejectsRowLimit(t *testing.T) {
	input := "title\nA\nB\n"
	_, err := (Parser{}).Parse(strings.NewReader(input), Options{TitleColumn: "title", MaxRows: 1}, func(Result) error { return nil })
	if !errors.Is(err, ErrTooManyRows) {
		t.Fatalf("expected row limit, got %v", err)
	}
}

func TestParserRejectsInvalidUTF8(t *testing.T) {
	input := append([]byte("title\n"), []byte{0xff, '\n'}...)
	_, err := (Parser{}).Parse(bytes.NewReader(input), Options{TitleColumn: "title"}, func(Result) error { return nil })
	if !errors.Is(err, ErrInvalidUTF8) {
		t.Fatalf("expected invalid UTF-8, got %v", err)
	}
}

func TestParserRejectsInconsistentColumns(t *testing.T) {
	input := "title,note\nA\n"
	_, err := (Parser{}).Parse(strings.NewReader(input), Options{TitleColumn: "title", TextColumn: "note"}, func(Result) error { return nil })
	if !errors.Is(err, ErrInconsistentColumns) {
		t.Fatalf("expected inconsistent columns, got %v", err)
	}
}

func TestParserRejectsMissingMappedColumn(t *testing.T) {
	input := "name\nA\n"
	_, err := (Parser{}).Parse(strings.NewReader(input), Options{TitleColumn: "title"}, func(Result) error { return nil })
	if !errors.Is(err, ErrMappingColumnMissing) {
		t.Fatalf("expected missing mapping, got %v", err)
	}
}

func TestParserRejectsEmptyTitleAsRowResultWithoutAbortingImport(t *testing.T) {
	input := "title\n\"\"\nB\n"
	var results []Result
	summary, err := (Parser{}).Parse(strings.NewReader(input), Options{TitleColumn: "title"}, func(result Result) error {
		results = append(results, result)
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if summary.RowsRead != 2 || summary.AcceptedRows != 1 || summary.RejectedRows != 1 || len(results) != 2 {
		t.Fatalf("unexpected summary: %#v results=%#v", summary, results)
	}
	if results[0].Accepted || !containsIssue(results[0].Issues, IssueTitleRequired) || !results[1].Accepted {
		t.Fatalf("unexpected row decisions: %#v", results)
	}
}

func TestParserMarksInvalidURLWithoutFetchingIt(t *testing.T) {
	input := "title,url\nA,http://user:pass@example.com/private\n"
	var result Result
	_, err := (Parser{}).Parse(strings.NewReader(input), Options{TitleColumn: "title", URLColumn: "url"}, func(value Result) error {
		result = value
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if !result.Accepted || result.Candidate.URL != "" || !containsIssue(result.Issues, IssueURLInvalid) {
		t.Fatalf("unexpected result: %#v", result)
	}
}

func TestParserKeepsFormulaLikeTextLiteralAndFlagsIt(t *testing.T) {
	input := "title,note\nA,\"=HYPERLINK(\"\"https://example.com\"\")\"\n"
	var result Result
	_, err := (Parser{}).Parse(strings.NewReader(input), Options{TitleColumn: "title", TextColumn: "note"}, func(value Result) error {
		result = value
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if result.Candidate.Text != `=HYPERLINK("https://example.com")` || !containsIssue(result.Issues, IssueFormulaLikeText) {
		t.Fatalf("formula-like text was not safely kept and flagged: %#v", result)
	}
}

func TestParserRejectsOversizedCell(t *testing.T) {
	input := "title\n" + strings.Repeat("a", 11) + "\n"
	_, err := (Parser{}).Parse(strings.NewReader(input), Options{TitleColumn: "title", MaxCellBytes: 10}, func(Result) error { return nil })
	if !errors.Is(err, ErrCellTooLarge) {
		t.Fatalf("expected cell limit, got %v", err)
	}
}

func TestParserFingerprintIsStableAcrossSourceRows(t *testing.T) {
	input := "title,date,url,note\nA,2026-07-01,https://example.com/a,note\nA,2026-07-01,https://example.com/a,note\n"
	var fingerprints []string
	_, err := (Parser{}).Parse(strings.NewReader(input), Options{
		TitleColumn: "title",
		DateColumn:  "date",
		DateLayout:  "2006-01-02",
		URLColumn:   "url",
		TextColumn:  "note",
	}, func(result Result) error {
		fingerprints = append(fingerprints, result.Candidate.Fingerprint)
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(fingerprints) != 2 || fingerprints[0] != fingerprints[1] {
		t.Fatalf("fingerprints must be deterministic: %#v", fingerprints)
	}
}

func TestParserStopsWhenEmitterFails(t *testing.T) {
	expected := errors.New("stop")
	_, err := (Parser{}).Parse(strings.NewReader("title\nA\nB\n"), Options{TitleColumn: "title"}, func(Result) error {
		return expected
	})
	if !errors.Is(err, expected) {
		t.Fatalf("expected emitter error, got %v", err)
	}
}

func containsIssue(values []IssueCode, expected IssueCode) bool {
	for _, value := range values {
		if value == expected {
			return true
		}
	}
	return false
}
