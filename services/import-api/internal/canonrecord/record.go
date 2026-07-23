// Package canonrecord implements the reviewed canonical adapter record
// contract (docs/schemas/memory-os-security/preview-canonical-record.v1.schema.json).
// The frame payload bytes are authoritative: EncodeCandidate/EncodeRejection
// produce the one canonical serialization, and DecodeRecord accepts a payload
// only when strict decoding, canonical re-serialization equality, and
// fingerprint recomputation all pass. The shared fixture
// docs/fixtures/memory-os-security/preview-canonical-records.round9.v1.json is
// cross-validated by both this package's tests and
// scripts/validate-memory-os-canonical-records.py.
package canonrecord

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"regexp"
	"strings"
	"time"
)

const (
	RecordVersion = 1

	MaxSourceRow       = 100_000
	MaxTitleBytes      = 4096
	MaxURLBytes        = 2048
	MaxTextBytes       = 1024 * 1024
	MaxIssueCodes      = 16
	MaxIssueCodeLength = 64
	// MaxRecordBytes mirrors previewspool.MaxCanonicalRecordBytes; a test
	// asserts the two constants stay equal.
	MaxRecordBytes = 2 * 1024 * 1024

	recordTypeCandidate = "candidate"
	recordTypeRejection = "rejection"
)

var (
	ErrInvalidRecord     = errors.New("canonical adapter record is invalid")
	ErrNonCanonicalBytes = errors.New("payload is not the canonical record serialization")
)

var issueCodePattern = regexp.MustCompile(`^IMPORT_[A-Z0-9_]+$`)

// Candidate is one accepted source row. Field order is the contract's
// canonical serialization order and must not be reordered.
type Candidate struct {
	RecordType    string   `json:"recordType"`
	RecordVersion int      `json:"recordVersion"`
	SourceRow     int64    `json:"sourceRow"`
	Title         string   `json:"title"`
	OccurredAt    string   `json:"occurredAt"`
	URL           string   `json:"url"`
	Text          string   `json:"text"`
	Fingerprint   string   `json:"fingerprint"`
	Issues        []string `json:"issues"`
}

// Rejection is one rejected source row. It has no free-text fields, so raw
// user values are structurally impossible.
type Rejection struct {
	RecordType    string   `json:"recordType"`
	RecordVersion int      `json:"recordVersion"`
	SourceRow     int64    `json:"sourceRow"`
	IssueCodes    []string `json:"issueCodes"`
}

// Fingerprint computes the contract fingerprint exactly as the genericcsv
// adapter does: TrimSpace(title), occurredAt verbatim, TrimSpace(url) and
// TrimSpace(text) joined by 0x1F, hashed with SHA-256.
func Fingerprint(title string, occurredAt string, url string, text string) string {
	canonical := strings.Join([]string{
		strings.TrimSpace(title),
		occurredAt,
		strings.TrimSpace(url),
		strings.TrimSpace(text),
	}, "\x1f")
	digest := sha256.Sum256([]byte(canonical))
	return hex.EncodeToString(digest[:])
}

func validSourceRow(sourceRow int64) bool {
	return sourceRow >= 1 && sourceRow <= MaxSourceRow
}

func validIssueCodes(codes []string, minimum int) bool {
	if len(codes) < minimum || len(codes) > MaxIssueCodes {
		return false
	}
	seen := make(map[string]struct{}, len(codes))
	for _, code := range codes {
		if len(code) > MaxIssueCodeLength || !issueCodePattern.MatchString(code) {
			return false
		}
		if _, duplicate := seen[code]; duplicate {
			return false
		}
		seen[code] = struct{}{}
	}
	return true
}

// validOccurredAt accepts the empty string or an RFC3339Nano UTC timestamp
// that round-trips through Go's own formatter, which forces the "Z" suffix
// and canonical fractional-second formatting.
func validOccurredAt(value string) bool {
	if value == "" {
		return true
	}
	parsed, err := time.Parse(time.RFC3339Nano, value)
	if err != nil {
		return false
	}
	return parsed.UTC().Format(time.RFC3339Nano) == value
}

func validateCandidate(candidate Candidate) error {
	switch {
	case candidate.RecordType != recordTypeCandidate:
		return fmt.Errorf("%w: record type %q", ErrInvalidRecord, candidate.RecordType)
	case candidate.RecordVersion != RecordVersion:
		return fmt.Errorf("%w: record version %d", ErrInvalidRecord, candidate.RecordVersion)
	case !validSourceRow(candidate.SourceRow):
		return fmt.Errorf("%w: source row %d", ErrInvalidRecord, candidate.SourceRow)
	case candidate.Title == "" || len(candidate.Title) > MaxTitleBytes:
		return fmt.Errorf("%w: title length %d", ErrInvalidRecord, len(candidate.Title))
	case !validOccurredAt(candidate.OccurredAt):
		return fmt.Errorf("%w: occurredAt %q", ErrInvalidRecord, candidate.OccurredAt)
	case len(candidate.URL) > MaxURLBytes:
		return fmt.Errorf("%w: url length %d", ErrInvalidRecord, len(candidate.URL))
	case len(candidate.Text) > MaxTextBytes:
		return fmt.Errorf("%w: text length %d", ErrInvalidRecord, len(candidate.Text))
	case candidate.Issues == nil:
		// A nil slice re-serializes as JSON null, which would otherwise pass
		// the canonical-equality check for a `"issues":null` payload.
		return fmt.Errorf("%w: issues must be an array", ErrInvalidRecord)
	case !validIssueCodes(candidate.Issues, 0):
		return fmt.Errorf("%w: issues", ErrInvalidRecord)
	}
	expected := Fingerprint(candidate.Title, candidate.OccurredAt, candidate.URL, candidate.Text)
	if candidate.Fingerprint != expected {
		return fmt.Errorf("%w: fingerprint mismatch", ErrInvalidRecord)
	}
	return nil
}

func validateRejection(rejection Rejection) error {
	switch {
	case rejection.RecordType != recordTypeRejection:
		return fmt.Errorf("%w: record type %q", ErrInvalidRecord, rejection.RecordType)
	case rejection.RecordVersion != RecordVersion:
		return fmt.Errorf("%w: record version %d", ErrInvalidRecord, rejection.RecordVersion)
	case !validSourceRow(rejection.SourceRow):
		return fmt.Errorf("%w: source row %d", ErrInvalidRecord, rejection.SourceRow)
	case !validIssueCodes(rejection.IssueCodes, 1):
		return fmt.Errorf("%w: issue codes", ErrInvalidRecord)
	}
	return nil
}

// EncodeCandidate validates and serializes one candidate into its canonical
// frame payload. Nil issue slices serialize as the canonical empty array.
func EncodeCandidate(candidate Candidate) ([]byte, error) {
	if candidate.Issues == nil {
		candidate.Issues = []string{}
	}
	if err := validateCandidate(candidate); err != nil {
		return nil, err
	}
	payload, err := json.Marshal(candidate)
	if err != nil {
		return nil, err
	}
	if len(payload) > MaxRecordBytes {
		return nil, fmt.Errorf("%w: encoded length %d", ErrInvalidRecord, len(payload))
	}
	return payload, nil
}

// EncodeRejection validates and serializes one rejection into its canonical
// frame payload.
func EncodeRejection(rejection Rejection) ([]byte, error) {
	if err := validateRejection(rejection); err != nil {
		return nil, err
	}
	return json.Marshal(rejection)
}

// DecodeRecord strictly decodes one frame payload. Exactly one of the returned
// records is non-nil on success. Unknown fields, trailing data, non-canonical
// byte serializations and every schema or fingerprint violation are rejected.
func DecodeRecord(payload []byte) (*Candidate, *Rejection, error) {
	if len(payload) < 2 || len(payload) > MaxRecordBytes {
		return nil, nil, fmt.Errorf("%w: payload length %d", ErrInvalidRecord, len(payload))
	}
	var probe struct {
		RecordType string `json:"recordType"`
	}
	if err := json.Unmarshal(payload, &probe); err != nil {
		return nil, nil, fmt.Errorf("%w: %v", ErrInvalidRecord, err)
	}

	switch probe.RecordType {
	case recordTypeCandidate:
		var candidate Candidate
		if err := strictDecode(payload, &candidate); err != nil {
			return nil, nil, err
		}
		if err := validateCandidate(candidate); err != nil {
			return nil, nil, err
		}
		canonical, err := json.Marshal(candidate)
		if err != nil {
			return nil, nil, err
		}
		if !bytes.Equal(canonical, payload) {
			return nil, nil, ErrNonCanonicalBytes
		}
		return &candidate, nil, nil
	case recordTypeRejection:
		var rejection Rejection
		if err := strictDecode(payload, &rejection); err != nil {
			return nil, nil, err
		}
		if err := validateRejection(rejection); err != nil {
			return nil, nil, err
		}
		canonical, err := json.Marshal(rejection)
		if err != nil {
			return nil, nil, err
		}
		if !bytes.Equal(canonical, payload) {
			return nil, nil, ErrNonCanonicalBytes
		}
		return nil, &rejection, nil
	default:
		return nil, nil, fmt.Errorf("%w: record type %q", ErrInvalidRecord, probe.RecordType)
	}
}

func strictDecode(payload []byte, target any) error {
	decoder := json.NewDecoder(bytes.NewReader(payload))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(target); err != nil {
		return fmt.Errorf("%w: %v", ErrInvalidRecord, err)
	}
	if err := decoder.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		return fmt.Errorf("%w: trailing record data", ErrInvalidRecord)
	}
	return nil
}
