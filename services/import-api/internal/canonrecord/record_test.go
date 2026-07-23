package canonrecord

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/m-shogo/memories-project/services/import-api/internal/previewspool"
)

const fixturePath = "../../../../docs/fixtures/memory-os-security/preview-canonical-records.round9.v1.json"

type fixtureCase struct {
	CaseID            string          `json:"caseId"`
	Expected          string          `json:"expected"`
	Record            json.RawMessage `json:"record"`
	CanonicalEncoding string          `json:"canonicalEncoding"`
}

type fixtureCaseSet struct {
	CaseSetID string        `json:"caseSetId"`
	Cases     []fixtureCase `json:"cases"`
}

func loadFixture(t *testing.T) fixtureCaseSet {
	t.Helper()
	payload, err := os.ReadFile(filepath.Clean(fixturePath))
	if err != nil {
		t.Fatalf("shared canonical-record fixture is missing: %v", err)
	}
	var caseSet fixtureCaseSet
	if err := json.Unmarshal(payload, &caseSet); err != nil {
		t.Fatal(err)
	}
	if len(caseSet.Cases) < 10 {
		t.Fatalf("fixture case coverage is too thin: %d", len(caseSet.Cases))
	}
	return caseSet
}

// TestFixtureCrossValidation proves the Go implementation and the Python
// validator enforce one contract: every accept case round-trips through
// DecodeRecord/Encode byte-for-byte, and every reject case fails DecodeRecord.
// (Python differentiates the rejection reasons; Go asserts rejection.)
func TestFixtureCrossValidation(t *testing.T) {
	caseSet := loadFixture(t)
	accepts, rejects := 0, 0
	for _, fixture := range caseSet.Cases {
		switch {
		case fixture.Expected == "accept":
			accepts++
			candidate, rejection, err := DecodeRecord([]byte(fixture.CanonicalEncoding))
			if err != nil {
				t.Fatalf("%s: accept case was rejected: %v", fixture.CaseID, err)
			}
			var reencoded []byte
			if candidate != nil {
				reencoded, err = EncodeCandidate(*candidate)
			} else {
				reencoded, err = EncodeRejection(*rejection)
			}
			if err != nil {
				t.Fatalf("%s: re-encode failed: %v", fixture.CaseID, err)
			}
			if string(reencoded) != fixture.CanonicalEncoding {
				t.Fatalf("%s: canonical round-trip mismatch:\n got %s\nwant %s",
					fixture.CaseID, reencoded, fixture.CanonicalEncoding)
			}
		case fixture.CanonicalEncoding != "":
			rejects++
			if _, _, err := DecodeRecord([]byte(fixture.CanonicalEncoding)); err == nil {
				t.Fatalf("%s: non-canonical payload was accepted", fixture.CaseID)
			}
		default:
			rejects++
			// Reject cases carry record objects; serialize them through Go's
			// map marshalling (sorted keys) — DecodeRecord must reject the
			// payload regardless of which rule it violates first.
			var generic map[string]any
			if err := json.Unmarshal(fixture.Record, &generic); err != nil {
				t.Fatal(err)
			}
			payload, err := json.Marshal(generic)
			if err != nil {
				t.Fatal(err)
			}
			if _, _, err := DecodeRecord(payload); err == nil {
				t.Fatalf("%s: invalid record was accepted", fixture.CaseID)
			}
		}
	}
	if accepts < 3 || rejects < 10 {
		t.Fatalf("fixture coverage mismatch: accepts=%d rejects=%d", accepts, rejects)
	}
}

func validCandidate() Candidate {
	title := "weekend ramen"
	occurredAt := "2026-07-21T09:30:00Z"
	url := "https://example.com/log"
	text := "shoyu at the corner shop"
	return Candidate{
		RecordType:    "candidate",
		RecordVersion: 1,
		SourceRow:     7,
		Title:         title,
		OccurredAt:    occurredAt,
		URL:           url,
		Text:          text,
		Fingerprint:   Fingerprint(title, occurredAt, url, text),
		Issues:        []string{},
	}
}

func TestEncodeDecodeRoundTrip(t *testing.T) {
	candidate := validCandidate()
	payload, err := EncodeCandidate(candidate)
	if err != nil {
		t.Fatal(err)
	}
	decoded, _, err := DecodeRecord(payload)
	if err != nil {
		t.Fatal(err)
	}
	if decoded.Title != candidate.Title || decoded.Fingerprint != candidate.Fingerprint {
		t.Fatalf("round-trip mutated the record: %+v", decoded)
	}

	rejection := Rejection{RecordType: "rejection", RecordVersion: 1, SourceRow: 9,
		IssueCodes: []string{"IMPORT_CSV_TITLE_REQUIRED"}}
	payload, err = EncodeRejection(rejection)
	if err != nil {
		t.Fatal(err)
	}
	if _, decodedRejection, err := DecodeRecord(payload); err != nil || decodedRejection.SourceRow != 9 {
		t.Fatalf("rejection round-trip failed: %+v %v", decodedRejection, err)
	}
}

func TestValidationRejectsContractViolations(t *testing.T) {
	mutations := map[string]func(*Candidate){
		"wrong-type":        func(c *Candidate) { c.RecordType = "rejection" },
		"future-version":    func(c *Candidate) { c.RecordVersion = 2 },
		"zero-row":          func(c *Candidate) { c.SourceRow = 0 },
		"row-overflow":      func(c *Candidate) { c.SourceRow = MaxSourceRow + 1 },
		"empty-title":       func(c *Candidate) { c.Title = "" },
		"oversized-title":   func(c *Candidate) { c.Title = strings.Repeat("x", MaxTitleBytes+1) },
		"non-utc-date":      func(c *Candidate) { c.OccurredAt = "2026-07-21T18:30:00+09:00" },
		"garbage-date":      func(c *Candidate) { c.OccurredAt = "yesterday" },
		"fingerprint-drift": func(c *Candidate) { c.Text = "edited after fingerprinting" },
		"bad-issue-code":    func(c *Candidate) { c.Issues = []string{"NOT_IMPORT"} },
		"duplicate-issues":  func(c *Candidate) { c.Issues = []string{"IMPORT_A", "IMPORT_A"} },
		"lowercase-issue":   func(c *Candidate) { c.Issues = []string{"IMPORT_csv"} },
		"too-many-issues":   func(c *Candidate) { c.Issues = make([]string, MaxIssueCodes+1) },
		"wrong-fingerprint": func(c *Candidate) { c.Fingerprint = strings.Repeat("0", 64) },
		"upper-fingerprint": func(c *Candidate) { c.Fingerprint = strings.ToUpper(c.Fingerprint) },
	}
	for name, mutate := range mutations {
		candidate := validCandidate()
		mutate(&candidate)
		if _, err := EncodeCandidate(candidate); !errors.Is(err, ErrInvalidRecord) {
			t.Fatalf("%s was encodable: %v", name, err)
		}
	}

	if _, err := EncodeRejection(Rejection{RecordType: "rejection", RecordVersion: 1,
		SourceRow: 1, IssueCodes: []string{}}); !errors.Is(err, ErrInvalidRecord) {
		t.Fatalf("empty rejection codes were encodable: %v", err)
	}
}

func TestDecodeRejectsNonCanonicalPayloads(t *testing.T) {
	payload, err := EncodeCandidate(validCandidate())
	if err != nil {
		t.Fatal(err)
	}
	cases := map[string][]byte{
		"trailing-newline": append(append([]byte{}, payload...), '\n'),
		"leading-space":    append([]byte(" "), payload...),
		"null-issues": []byte(strings.Replace(string(payload),
			`"issues":[]`, `"issues":null`, 1)),
		"unknown-field": []byte(strings.Replace(string(payload),
			`"issues":[]`, `"issues":[],"note":"x"`, 1)),
		"empty": {},
	}
	for name, mutated := range cases {
		if _, _, err := DecodeRecord(mutated); err == nil {
			t.Fatalf("%s payload was accepted", name)
		}
	}
}

func TestRecordLimitMatchesSpoolContract(t *testing.T) {
	if MaxRecordBytes != previewspool.MaxCanonicalRecordBytes {
		t.Fatalf("record byte limit diverged from the spool contract: %d != %d",
			MaxRecordBytes, previewspool.MaxCanonicalRecordBytes)
	}
	if MaxSourceRow != previewspool.MaxSpoolRecords {
		t.Fatalf("source row limit diverged from the spool contract: %d != %d",
			MaxSourceRow, previewspool.MaxSpoolRecords)
	}
}
