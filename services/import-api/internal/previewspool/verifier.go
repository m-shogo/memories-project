package previewspool

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"time"
)

const MaxManifestBytes int64 = 64 * 1024

var (
	ErrVerifyInvalidInput      = errors.New("invalid Preview spool verification input")
	ErrVerifyManifestMissing   = errors.New("Preview spool manifest is missing")
	ErrVerifyTempResidue       = errors.New("Preview spool attempt holds manifest temp residue")
	ErrVerifyManifestMalformed = errors.New("Preview spool manifest is malformed")
	ErrVerifyStreamMissing     = errors.New("Preview spool stream file is missing")
	ErrVerifyStreamMalformed   = errors.New("Preview spool stream framing is malformed")
	ErrVerifyStreamMismatch    = errors.New("Preview spool stream does not match sealed manifest")
	ErrVerifyBindingMismatch   = errors.New("Preview spool manifest does not match expected binding")
	ErrVerifyExpired           = errors.New("Preview spool manifest is expired")
)

// VerifyExpectation is the caller-side binding one sealed spool must match
// before any database transaction may consume it. Every field is compared
// exactly against the strictly decoded manifest.
type VerifyExpectation struct {
	JobID          string
	OwnerAccountID string
	AccountEpoch   int64
	Source         SealSourceBinding
	Adapter        SealAdapterBinding
	OptionsSHA256  string
}

// VerifiedSpool is returned only after the manifest was strictly decoded and
// both streams were independently re-read, re-counted and re-hashed from the
// exact on-disk bytes. Evidence carries the recomputed totals, never the
// manifest copy.
type VerifiedSpool struct {
	SpoolID            string
	JobID              string
	OwnerAccountID     string
	AccountEpoch       int64
	Source             SealSourceBinding
	Adapter            SealAdapterBinding
	OptionsSHA256      string
	CreatedAt          time.Time
	ExpiresAt          time.Time
	Evidence           WriteEvidence
	ManifestByteLength int64
	ManifestSHA256     string
}

// decodeSealedManifest strictly decodes exactly one manifest JSON value and
// then re-serializes the decoded fields through buildManifest. The rebuilt
// payload must reproduce the input byte for byte, so unknown fields, duplicate
// keys, non-canonical encoding, non-UTC timestamps, altered security constants
// and every seal-time validation failure are all rejected.
func decodeSealedManifest(payload []byte) (manifestDocument, SealInput, WriteEvidence, error) {
	if int64(len(payload)) < 1 || int64(len(payload)) > MaxManifestBytes {
		return manifestDocument{}, SealInput{}, WriteEvidence{}, fmt.Errorf("%w: manifest length %d", ErrVerifyManifestMalformed, len(payload))
	}
	decoder := json.NewDecoder(bytes.NewReader(payload))
	decoder.DisallowUnknownFields()
	var doc manifestDocument
	if err := decoder.Decode(&doc); err != nil {
		return manifestDocument{}, SealInput{}, WriteEvidence{}, fmt.Errorf("%w: %v", ErrVerifyManifestMalformed, err)
	}
	if err := decoder.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		return manifestDocument{}, SealInput{}, WriteEvidence{}, fmt.Errorf("%w: trailing manifest data", ErrVerifyManifestMalformed)
	}
	createdAt, err := time.Parse(time.RFC3339Nano, doc.CreatedAt)
	if err != nil {
		return manifestDocument{}, SealInput{}, WriteEvidence{}, fmt.Errorf("%w: createdAt: %v", ErrVerifyManifestMalformed, err)
	}
	expiresAt, err := time.Parse(time.RFC3339Nano, doc.ExpiresAt)
	if err != nil {
		return manifestDocument{}, SealInput{}, WriteEvidence{}, fmt.Errorf("%w: expiresAt: %v", ErrVerifyManifestMalformed, err)
	}
	input := SealInput{
		JobID:          doc.JobID,
		OwnerAccountID: doc.OwnerAccountID,
		AccountEpoch:   doc.AccountEpoch,
		Source: SealSourceBinding{
			ObjectKey:       doc.Source.ObjectKey,
			ObjectVersionID: doc.Source.ObjectVersionID,
			ContentLength:   doc.Source.ContentLength,
			ChecksumSHA256:  doc.Source.ChecksumSHA256,
		},
		Adapter: SealAdapterBinding{
			AdapterID:      doc.Adapter.AdapterID,
			AdapterVersion: doc.Adapter.AdapterVersion,
			ArtifactSHA256: doc.Adapter.ArtifactSHA256,
		},
		OptionsSHA256: doc.OptionsSHA256,
		CreatedAt:     createdAt,
		ExpiresAt:     expiresAt,
	}
	evidence := WriteEvidence{
		SourceRowCount:  doc.SourceRowCount,
		SpoolByteLength: doc.SpoolByteLength,
		Accepted: StreamEvidence{
			RecordFormat: doc.Streams.Accepted.RecordFormat,
			RecordCount:  doc.Streams.Accepted.RecordCount,
			ByteLength:   doc.Streams.Accepted.ByteLength,
			SHA256:       doc.Streams.Accepted.SHA256,
		},
		Rejected: StreamEvidence{
			RecordFormat: doc.Streams.Rejected.RecordFormat,
			RecordCount:  doc.Streams.Rejected.RecordCount,
			ByteLength:   doc.Streams.Rejected.ByteLength,
			SHA256:       doc.Streams.Rejected.SHA256,
		},
	}
	rebuilt, _, err := buildManifest(doc.SpoolID, input, evidence)
	if err != nil {
		return manifestDocument{}, SealInput{}, WriteEvidence{}, fmt.Errorf("%w: %v", ErrVerifyManifestMalformed, err)
	}
	if !bytes.Equal(rebuilt, payload) {
		return manifestDocument{}, SealInput{}, WriteEvidence{}, fmt.Errorf("%w: manifest is not canonical", ErrVerifyManifestMalformed)
	}
	return doc, input, evidence, nil
}

// scanLengthPrefixedStream re-derives one stream's evidence from exact bytes.
// It never trusts the sealed manifest for framing and aborts on the first
// bound, framing or cancellation failure. Trailing bytes that do not form a
// complete record are torn framing, not padding.
func scanLengthPrefixedStream(ctx context.Context, reader io.Reader, recordFormat string) (StreamEvidence, error) {
	hasher := sha256.New()
	recordCount := 0
	var byteLength int64
	var prefix [8]byte
	for {
		if err := ctx.Err(); err != nil {
			return StreamEvidence{}, err
		}
		if _, err := io.ReadFull(reader, prefix[:]); err != nil {
			if errors.Is(err, io.EOF) {
				break
			}
			return StreamEvidence{}, fmt.Errorf("%w: torn length prefix", ErrVerifyStreamMalformed)
		}
		length := binary.BigEndian.Uint64(prefix[:])
		if length < 1 || length > uint64(MaxCanonicalRecordBytes) {
			return StreamEvidence{}, fmt.Errorf("%w: record length %d", ErrVerifyStreamMalformed, length)
		}
		if recordCount >= MaxSpoolRecords {
			return StreamEvidence{}, fmt.Errorf("%w: record limit exceeded", ErrVerifyStreamMalformed)
		}
		recordBytes := int64(8 + length)
		if recordBytes > MaxSpoolBytes-byteLength {
			return StreamEvidence{}, fmt.Errorf("%w: byte limit exceeded", ErrVerifyStreamMalformed)
		}
		_, _ = hasher.Write(prefix[:])
		if _, err := io.CopyN(hasher, reader, int64(length)); err != nil {
			return StreamEvidence{}, fmt.Errorf("%w: torn record body", ErrVerifyStreamMalformed)
		}
		recordCount++
		byteLength += recordBytes
	}
	return StreamEvidence{
		RecordFormat: recordFormat,
		RecordCount:  recordCount,
		ByteLength:   byteLength,
		SHA256:       hex.EncodeToString(hasher.Sum(nil)),
	}, nil
}

func matchExpectation(input SealInput, expected VerifyExpectation) bool {
	return input.JobID == expected.JobID &&
		input.OwnerAccountID == expected.OwnerAccountID &&
		input.AccountEpoch == expected.AccountEpoch &&
		input.Source == expected.Source &&
		input.Adapter == expected.Adapter &&
		input.OptionsSHA256 == expected.OptionsSHA256
}
