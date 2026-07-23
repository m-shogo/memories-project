// Package csvworker is the supervised worker side of the Generic CSV adapter:
// it reads staged CSV bytes from stdin, parses them with the bounded
// synchronous genericcsv iterator, and emits canonical adapter records
// (internal/canonrecord) as tagged frames on stdout. It never touches the
// spool, database, object storage or credentials — the supervisor owns all of
// those — and any internal failure is a nonzero exit, which the supervisor
// treats as a terminal fail-closed parse failure.
package csvworker

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/adapters/genericcsv"
	"github.com/m-shogo/memories-project/services/import-api/internal/canonrecord"
	"github.com/m-shogo/memories-project/services/import-api/internal/parsersup"
)

// OptionsEnv carries the wire options JSON into the supervised worker. The
// name must stay outside the supervisor's credential-shaped rejection lists.
const OptionsEnv = "MEMORY_OS_CSV_OPTIONS"

// WireOptions is the strict JSON form of genericcsv.Options accepted by the
// worker. Limits are intentionally not settable from the wire: the worker
// always runs with the adapter's reviewed default bounds.
type WireOptions struct {
	Delimiter    string `json:"delimiter"`
	TitleColumn  string `json:"titleColumn"`
	DateColumn   string `json:"dateColumn"`
	DateLayout   string `json:"dateLayout"`
	DateLocation string `json:"dateLocation"`
	URLColumn    string `json:"urlColumn"`
	TextColumn   string `json:"textColumn"`
}

// ParserOptions converts the wire form into adapter options. The genericcsv
// normalizer applies defaults and rejects unsupported locations.
func ParserOptions(optionsJSON string) (genericcsv.Options, error) {
	decoder := json.NewDecoder(bytes.NewReader([]byte(optionsJSON)))
	decoder.DisallowUnknownFields()
	var wire WireOptions
	if err := decoder.Decode(&wire); err != nil {
		return genericcsv.Options{}, fmt.Errorf("decode CSV worker options: %w", err)
	}
	if err := decoder.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		return genericcsv.Options{}, errors.New("trailing CSV worker options data")
	}

	options := genericcsv.Options{
		TitleColumn: wire.TitleColumn,
		DateColumn:  wire.DateColumn,
		DateLayout:  wire.DateLayout,
		URLColumn:   wire.URLColumn,
		TextColumn:  wire.TextColumn,
	}
	switch runes := []rune(wire.Delimiter); {
	case len(runes) == 0:
	case len(runes) == 1:
		options.Delimiter = runes[0]
	default:
		return genericcsv.Options{}, fmt.Errorf("CSV delimiter must be one rune: %q", wire.Delimiter)
	}
	switch wire.DateLocation {
	case "", "UTC":
	case "Asia/Tokyo":
		location, err := time.LoadLocation("Asia/Tokyo")
		if err != nil {
			return genericcsv.Options{}, err
		}
		options.DateLocation = location
	default:
		return genericcsv.Options{}, genericcsv.ErrUnsupportedDateLocation
	}
	return options, nil
}

// Run parses one staged CSV source to completion. Exit codes: 0 on success,
// 1 on any options, parse or encoding failure (details on errOutput).
func Run(optionsJSON string, input io.Reader, output io.Writer, errOutput io.Writer) int {
	if err := run(optionsJSON, input, output); err != nil {
		fmt.Fprintf(errOutput, "csv worker: %v\n", err)
		return 1
	}
	return 0
}

func run(optionsJSON string, input io.Reader, output io.Writer) error {
	options, err := ParserOptions(optionsJSON)
	if err != nil {
		return err
	}
	iterator, err := genericcsv.NewIterator(input, options)
	if err != nil {
		return err
	}

	ctx := context.Background()
	for {
		result, err := iterator.Next(ctx)
		if errors.Is(err, genericcsv.ErrEndOfRows) {
			return nil
		}
		if err != nil {
			return err
		}

		issues := make([]string, len(result.Issues))
		for index, issue := range result.Issues {
			issues[index] = string(issue)
		}

		if result.Accepted {
			candidate := result.Candidate
			occurredAt := ""
			if candidate.OccurredAt != nil {
				occurredAt = candidate.OccurredAt.UTC().Format(time.RFC3339Nano)
			}
			// EncodeCandidate recomputes the fingerprint from the record
			// fields, so any drift between the genericcsv fingerprint and the
			// canonical-record contract fails the parse instead of sealing
			// unverifiable records.
			payload, err := canonrecord.EncodeCandidate(canonrecord.Candidate{
				RecordType:    "candidate",
				RecordVersion: canonrecord.RecordVersion,
				SourceRow:     int64(candidate.SourceRow),
				Title:         candidate.Title,
				OccurredAt:    occurredAt,
				URL:           candidate.URL,
				Text:          candidate.Text,
				Fingerprint:   candidate.Fingerprint,
				Issues:        issues,
			})
			if err != nil {
				return err
			}
			if err := parsersup.WriteAcceptedFrame(output, payload); err != nil {
				return err
			}
			continue
		}

		payload, err := canonrecord.EncodeRejection(canonrecord.Rejection{
			RecordType:    "rejection",
			RecordVersion: canonrecord.RecordVersion,
			SourceRow:     int64(result.SourceRow),
			IssueCodes:    issues,
		})
		if err != nil {
			return err
		}
		if err := parsersup.WriteRejectedFrame(output, payload); err != nil {
			return err
		}
	}
}
