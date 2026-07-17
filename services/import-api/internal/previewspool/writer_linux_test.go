//go:build linux

package previewspool

import (
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"errors"
	"io"
	"os"
	"path/filepath"
	"testing"
)

func newWriterAttempt(t *testing.T) (*Attempt, string) {
	t.Helper()
	manager, root := newTestManager(t)
	attempt, err := manager.CreateAttempt(context.Background(), testSpoolID)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = attempt.Cleanup() })
	return attempt, root
}

func lengthPrefixed(value []byte) []byte {
	result := make([]byte, 8+len(value))
	binary.BigEndian.PutUint64(result[:8], uint64(len(value)))
	copy(result[8:], value)
	return result
}

func TestStreamWriterWritesExactBytesAndEvidence(t *testing.T) {
	attempt, root := newWriterAttempt(t)
	writer, err := NewStreamWriter(attempt)
	if err != nil {
		t.Fatal(err)
	}

	acceptedCanonical := []byte("accepted-canonical")
	rejectedCanonical := []byte("12|1|20:IMPORT_TITLE_MISSING")
	if err := writer.WriteAccepted(context.Background(), acceptedCanonical); err != nil {
		t.Fatal(err)
	}
	if err := writer.WriteRejected(context.Background(), rejectedCanonical); err != nil {
		t.Fatal(err)
	}

	evidence, err := writer.Close(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	secondEvidence, err := writer.Close(context.Background())
	if err != nil || secondEvidence != evidence {
		t.Fatalf("close is not idempotent: %+v %v", secondEvidence, err)
	}

	acceptedBytes, err := os.ReadFile(filepath.Join(root, testSpoolID, AcceptedFileName))
	if err != nil {
		t.Fatal(err)
	}
	rejectedBytes, err := os.ReadFile(filepath.Join(root, testSpoolID, RejectedFileName))
	if err != nil {
		t.Fatal(err)
	}
	if string(acceptedBytes) != string(lengthPrefixed(acceptedCanonical)) {
		t.Fatalf("unexpected accepted bytes: %x", acceptedBytes)
	}
	if string(rejectedBytes) != string(lengthPrefixed(rejectedCanonical)) {
		t.Fatalf("unexpected rejected bytes: %x", rejectedBytes)
	}

	acceptedDigest := sha256.Sum256(acceptedBytes)
	rejectedDigest := sha256.Sum256(rejectedBytes)
	if evidence.Accepted != (StreamEvidence{
		RecordFormat: AcceptedRecordFormat,
		RecordCount:  1,
		ByteLength:   int64(len(acceptedBytes)),
		SHA256:       hex.EncodeToString(acceptedDigest[:]),
	}) {
		t.Fatalf("unexpected accepted evidence: %+v", evidence.Accepted)
	}
	if evidence.Rejected != (StreamEvidence{
		RecordFormat: RejectedRecordFormat,
		RecordCount:  1,
		ByteLength:   int64(len(rejectedBytes)),
		SHA256:       hex.EncodeToString(rejectedDigest[:]),
	}) {
		t.Fatalf("unexpected rejected evidence: %+v", evidence.Rejected)
	}
	if evidence.SourceRowCount != 2 || evidence.SpoolByteLength != int64(len(acceptedBytes)+len(rejectedBytes)) {
		t.Fatalf("unexpected totals: %+v", evidence)
	}
	if _, err := os.Lstat(filepath.Join(root, testSpoolID, ManifestFileName)); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("manifest was published before seal: %v", err)
	}
	if err := writer.WriteAccepted(context.Background(), []byte("late")); !errors.Is(err, ErrStreamWriterClosed) {
		t.Fatalf("write after close was not rejected: %v", err)
	}
}

func TestStreamWriterEmptyRejectedStreamUsesSHA256OfEmptyBytes(t *testing.T) {
	attempt, _ := newWriterAttempt(t)
	writer, err := NewStreamWriter(attempt)
	if err != nil {
		t.Fatal(err)
	}
	if err := writer.WriteAccepted(context.Background(), []byte("accepted")); err != nil {
		t.Fatal(err)
	}
	evidence, err := writer.Close(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	emptyDigest := sha256.Sum256(nil)
	if evidence.Rejected.RecordCount != 0 || evidence.Rejected.ByteLength != 0 || evidence.Rejected.SHA256 != hex.EncodeToString(emptyDigest[:]) {
		t.Fatalf("unexpected empty rejection evidence: %+v", evidence.Rejected)
	}
}

func TestStreamWriterCancellationIsSticky(t *testing.T) {
	attempt, _ := newWriterAttempt(t)
	writer, err := NewStreamWriter(attempt)
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	firstErr := writer.WriteAccepted(ctx, []byte("accepted"))
	if !errors.Is(firstErr, context.Canceled) {
		t.Fatalf("expected cancellation, got %v", firstErr)
	}
	if err := writer.WriteAccepted(context.Background(), []byte("retry")); !errors.Is(err, context.Canceled) {
		t.Fatalf("terminal cancellation was resumable: %v", err)
	}
	if _, err := writer.Close(context.Background()); !errors.Is(err, context.Canceled) {
		t.Fatalf("close did not preserve terminal cancellation: %v", err)
	}
	if attempt.accepted != nil || attempt.rejected != nil {
		t.Fatal("terminal cancellation left writable stream handles")
	}
}

func TestStreamWriterLimitsAreTerminalAndCheckedBeforeRecordWrite(t *testing.T) {
	t.Run("record bytes", func(t *testing.T) {
		attempt, root := newWriterAttempt(t)
		writer, err := NewStreamWriter(attempt)
		if err != nil {
			t.Fatal(err)
		}
		writer.maxRecordBytes = 2
		if err := writer.WriteAccepted(context.Background(), []byte("123")); !errors.Is(err, ErrCanonicalRecordTooLarge) {
			t.Fatalf("expected record limit, got %v", err)
		}
		value, err := os.ReadFile(filepath.Join(root, testSpoolID, AcceptedFileName))
		if err != nil {
			t.Fatal(err)
		}
		if len(value) != 0 {
			t.Fatalf("oversized record wrote bytes: %x", value)
		}
	})

	t.Run("aggregate records", func(t *testing.T) {
		attempt, _ := newWriterAttempt(t)
		writer, err := NewStreamWriter(attempt)
		if err != nil {
			t.Fatal(err)
		}
		writer.maxRecords = 1
		if err := writer.WriteAccepted(context.Background(), []byte("accepted")); err != nil {
			t.Fatal(err)
		}
		if err := writer.WriteRejected(context.Background(), []byte("rejected")); !errors.Is(err, ErrSpoolRecordLimit) {
			t.Fatalf("expected aggregate record limit, got %v", err)
		}
		if err := writer.WriteAccepted(context.Background(), []byte("retry")); !errors.Is(err, ErrSpoolRecordLimit) {
			t.Fatalf("record limit failure was not sticky: %v", err)
		}
	})

	t.Run("aggregate bytes", func(t *testing.T) {
		attempt, root := newWriterAttempt(t)
		writer, err := NewStreamWriter(attempt)
		if err != nil {
			t.Fatal(err)
		}
		writer.maxBytes = 9
		if err := writer.WriteAccepted(context.Background(), []byte("12")); !errors.Is(err, ErrSpoolByteLimit) {
			t.Fatalf("expected aggregate byte limit, got %v", err)
		}
		value, err := os.ReadFile(filepath.Join(root, testSpoolID, AcceptedFileName))
		if err != nil {
			t.Fatal(err)
		}
		if len(value) != 0 {
			t.Fatalf("byte-limit failure wrote bytes: %x", value)
		}
	})
}

func TestStreamWriterShortWriteIsSticky(t *testing.T) {
	attempt, _ := newWriterAttempt(t)
	writer, err := NewStreamWriter(attempt)
	if err != nil {
		t.Fatal(err)
	}
	writer.writeAll = func(_ context.Context, file *os.File, value []byte) error {
		if len(value) > 0 {
			_, _ = file.Write(value[:1])
		}
		return io.ErrShortWrite
	}

	if err := writer.WriteAccepted(context.Background(), []byte("accepted")); !errors.Is(err, io.ErrShortWrite) {
		t.Fatalf("expected short write, got %v", err)
	}
	if err := writer.WriteRejected(context.Background(), []byte("retry")); !errors.Is(err, io.ErrShortWrite) {
		t.Fatalf("short write was not sticky: %v", err)
	}
	if _, err := writer.Close(context.Background()); !errors.Is(err, io.ErrShortWrite) {
		t.Fatalf("close did not preserve short write: %v", err)
	}
}

func TestStreamWriterRequiresAcceptedRecordAndSingleClaim(t *testing.T) {
	attempt, _ := newWriterAttempt(t)
	writer, err := NewStreamWriter(attempt)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := NewStreamWriter(attempt); !errors.Is(err, ErrStreamWriterClaimed) {
		t.Fatalf("second writer claim was allowed: %v", err)
	}
	if err := writer.WriteRejected(context.Background(), []byte("rejected")); err != nil {
		t.Fatal(err)
	}
	if _, err := writer.Close(context.Background()); !errors.Is(err, ErrAcceptedRecordRequired) {
		t.Fatalf("accepted-record requirement missing: %v", err)
	}
	if err := writer.WriteAccepted(context.Background(), []byte("late accepted")); !errors.Is(err, ErrAcceptedRecordRequired) {
		t.Fatalf("accepted-record failure was resumable: %v", err)
	}
}

func TestNewStreamWriterRejectsPrewrittenStream(t *testing.T) {
	attempt, _ := newWriterAttempt(t)
	if _, err := attempt.accepted.Write([]byte("bypass")); err != nil {
		t.Fatal(err)
	}
	if _, err := NewStreamWriter(attempt); !errors.Is(err, ErrStreamModified) {
		t.Fatalf("prewritten stream was accepted: %v", err)
	}
}
