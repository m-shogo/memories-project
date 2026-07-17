//go:build linux

package previewspool

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"syscall"
	"testing"
)

func TestStreamWriterCancellationAfterLengthPrefixIsTerminal(t *testing.T) {
	attempt, root := newWriterAttempt(t)
	writer, err := NewStreamWriter(attempt)
	if err != nil {
		t.Fatal(err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	calls := 0
	writer.writeAll = func(ctx context.Context, file *os.File, value []byte) error {
		calls++
		if err := writeAllContext(ctx, file, value); err != nil {
			return err
		}
		if calls == 1 {
			cancel()
		}
		return nil
	}

	if err := writer.WriteAccepted(ctx, []byte("accepted")); !errors.Is(err, context.Canceled) {
		t.Fatalf("expected cancellation after prefix, got %v", err)
	}
	value, err := os.ReadFile(filepath.Join(root, testSpoolID, AcceptedFileName))
	if err != nil {
		t.Fatal(err)
	}
	if len(value) != 8 {
		t.Fatalf("expected only an incomplete length prefix, got %d bytes", len(value))
	}
	if writer.accepted.recordCount != 0 || writer.accepted.byteLength != 0 || writer.totalRecords != 0 || writer.totalBytes != 0 {
		t.Fatalf("partial record entered evidence: %+v", writer)
	}
	if err := writer.WriteAccepted(context.Background(), []byte("retry")); !errors.Is(err, context.Canceled) {
		t.Fatalf("partial cancelled record was resumable: %v", err)
	}
}

func TestStreamWriterDiskFullFailureIsSticky(t *testing.T) {
	attempt, _ := newWriterAttempt(t)
	writer, err := NewStreamWriter(attempt)
	if err != nil {
		t.Fatal(err)
	}
	writer.writeAll = func(context.Context, *os.File, []byte) error {
		return syscall.ENOSPC
	}

	if err := writer.WriteAccepted(context.Background(), []byte("accepted")); !errors.Is(err, syscall.ENOSPC) {
		t.Fatalf("expected ENOSPC, got %v", err)
	}
	if err := writer.WriteRejected(context.Background(), []byte("retry")); !errors.Is(err, syscall.ENOSPC) {
		t.Fatalf("disk-full failure was not sticky: %v", err)
	}
	if _, err := writer.Close(context.Background()); !errors.Is(err, syscall.ENOSPC) {
		t.Fatalf("close did not preserve ENOSPC: %v", err)
	}
}
