package previewspool

import "errors"

const (
	AcceptedRecordFormat = "memory-os-preview-candidate-v1-length-prefixed"
	RejectedRecordFormat = "memory-os-preview-rejection-v1-length-prefixed"

	MaxSpoolRecords             = 100_000
	MaxSpoolBytes         int64 = 512 * 1024 * 1024
	MaxCanonicalRecordBytes     = 2 * 1024 * 1024
)

var (
	ErrStreamWriterClaimed      = errors.New("Preview spool stream writer already claimed")
	ErrStreamWriterClosed       = errors.New("Preview spool stream writer is closed")
	ErrStreamModified           = errors.New("Preview spool stream was modified before writer claim")
	ErrInvalidCanonicalRecord   = errors.New("invalid canonical Preview spool record")
	ErrCanonicalRecordTooLarge  = errors.New("canonical Preview spool record exceeds limit")
	ErrSpoolRecordLimit         = errors.New("Preview spool record limit exceeded")
	ErrSpoolByteLimit           = errors.New("Preview spool byte limit exceeded")
	ErrAcceptedRecordRequired   = errors.New("Preview spool requires at least one accepted record")
)

// StreamEvidence is calculated from the exact length-prefixed bytes written to
// one stream. It is not a sealed manifest and must be independently re-hashed
// before any database transaction starts.
type StreamEvidence struct {
	RecordFormat string
	RecordCount  int
	ByteLength   int64
	SHA256       string
}

// WriteEvidence contains the exact stream totals needed by the later manifest
// writer. SourceRowCount is accepted + rejected because each source row must
// produce exactly one decision.
type WriteEvidence struct {
	SourceRowCount  int
	SpoolByteLength int64
	Accepted        StreamEvidence
	Rejected        StreamEvidence
}
