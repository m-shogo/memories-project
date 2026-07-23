package csvworker

import (
	"bytes"
	"encoding/binary"
	"io"
	"strings"
	"testing"

	"github.com/m-shogo/memories-project/services/import-api/internal/canonrecord"
)

const testOptions = `{"titleColumn":"title","dateColumn":"date","dateLayout":"2006-01-02","urlColumn":"url","textColumn":"text"}`

type frame struct {
	tag     byte
	payload []byte
}

func readFrames(t *testing.T, encoded []byte) []frame {
	t.Helper()
	reader := bytes.NewReader(encoded)
	var frames []frame
	for {
		var header [9]byte
		if _, err := io.ReadFull(reader, header[:1]); err == io.EOF {
			return frames
		} else if err != nil {
			t.Fatal(err)
		}
		if _, err := io.ReadFull(reader, header[1:]); err != nil {
			t.Fatal(err)
		}
		payload := make([]byte, binary.BigEndian.Uint64(header[1:]))
		if _, err := io.ReadFull(reader, payload); err != nil {
			t.Fatal(err)
		}
		frames = append(frames, frame{tag: header[0], payload: payload})
	}
}

func TestRunEmitsCanonicalFrames(t *testing.T) {
	source := strings.Join([]string{
		"title,date,url,text",
		`summer trip,2026-07-21,https://example.com/trip,"three temples"`,
		",,,missing title row",
		"ramen log,,,",
	}, "\n") + "\n"

	var output, errOutput bytes.Buffer
	if code := Run(testOptions, strings.NewReader(source), &output, &errOutput); code != 0 {
		t.Fatalf("worker failed (%d): %s", code, errOutput.String())
	}

	frames := readFrames(t, output.Bytes())
	if len(frames) != 3 {
		t.Fatalf("expected 3 frames, got %d", len(frames))
	}
	if frames[0].tag != 'A' || frames[1].tag != 'R' || frames[2].tag != 'A' {
		t.Fatalf("unexpected frame tags: %c %c %c", frames[0].tag, frames[1].tag, frames[2].tag)
	}

	first, _, err := canonrecord.DecodeRecord(frames[0].payload)
	if err != nil {
		t.Fatalf("first frame is not a canonical record: %v", err)
	}
	// genericcsv numbers physical file rows, so the header is row 1 and
	// the first data row is sourceRow 2.
	if first.SourceRow != 2 || first.Title != "summer trip" ||
		first.OccurredAt != "2026-07-21T00:00:00Z" || first.URL != "https://example.com/trip" {
		t.Fatalf("unexpected first candidate: %+v", first)
	}

	_, rejected, err := canonrecord.DecodeRecord(frames[1].payload)
	if err != nil {
		t.Fatalf("second frame is not a canonical record: %v", err)
	}
	if rejected.SourceRow != 3 || len(rejected.IssueCodes) == 0 ||
		rejected.IssueCodes[0] != "IMPORT_CSV_TITLE_REQUIRED" {
		t.Fatalf("unexpected rejection: %+v", rejected)
	}

	third, _, err := canonrecord.DecodeRecord(frames[2].payload)
	if err != nil || third.SourceRow != 4 || third.OccurredAt != "" {
		t.Fatalf("unexpected third candidate: %+v %v", third, err)
	}
}

func TestRunFailsClosed(t *testing.T) {
	cases := map[string]struct {
		options string
		source  string
	}{
		"malformed-options":    {options: `{"titleColumn":`, source: "title\nx\n"},
		"unknown-option":       {options: `{"titleColumn":"title","allowNetwork":true}`, source: "title\nx\n"},
		"multi-rune-delimiter": {options: `{"titleColumn":"title","delimiter":"||"}`, source: "title\nx\n"},
		"bad-date-location":    {options: `{"titleColumn":"title","dateLocation":"America/New_York"}`, source: "title\nx\n"},
		"missing-header":       {options: testOptions, source: ""},
		"unknown-title-column": {options: `{"titleColumn":"missing"}`, source: "title\nx\n"},
	}
	for name, testCase := range cases {
		var output, errOutput bytes.Buffer
		if code := Run(testCase.options, strings.NewReader(testCase.source), &output, &errOutput); code == 0 {
			t.Fatalf("%s: worker succeeded unexpectedly", name)
		}
		if output.Len() != 0 {
			t.Fatalf("%s: failed worker emitted %d frame bytes", name, output.Len())
		}
	}
}
