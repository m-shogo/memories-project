//go:build linux

package previewspool

import (
	"context"
	"errors"
	"io"
	"os"
	"path/filepath"
	"syscall"
	"testing"
)

func TestSealerCancellationBetweenStreamSyncsIsSticky(t *testing.T) {
	writer, directory := newSealWriter(t)
	sealer, _ := NewSealer(writer)
	ctx, cancel := context.WithCancel(context.Background())
	calls := 0
	sealer.ops.syncFile = func(*os.File) error {
		calls++
		if calls == 1 {
			cancel()
		}
		return nil
	}
	if _, err := sealer.Seal(ctx, validSealInput()); !errors.Is(err, context.Canceled) {
		t.Fatalf("expected cancellation, got %v", err)
	}
	if calls != 1 {
		t.Fatalf("rejected stream was synced after cancellation: %d", calls)
	}
	if _, err := sealer.Seal(context.Background(), validSealInput()); !errors.Is(err, context.Canceled) {
		t.Fatalf("seal cancellation was resumable: %v", err)
	}
	assertNoSealNames(t, directory)
}

func TestSealerManifestWriteFailureRemovesTemp(t *testing.T) {
	writer, directory := newSealWriter(t)
	sealer, _ := NewSealer(writer)
	sealer.ops.writeAll = func(_ context.Context, file *os.File, value []byte) error {
		if len(value) > 0 {
			_, _ = file.Write(value[:1])
		}
		return io.ErrShortWrite
	}
	if _, err := sealer.Seal(context.Background(), validSealInput()); !errors.Is(err, io.ErrShortWrite) {
		t.Fatalf("expected short manifest write, got %v", err)
	}
	assertNoSealNames(t, directory)
}

func TestSealerManifestSyncFailureRemovesTemp(t *testing.T) {
	writer, directory := newSealWriter(t)
	sealer, _ := NewSealer(writer)
	calls := 0
	sealer.ops.syncFile = func(*os.File) error {
		calls++
		if calls == 3 {
			return syscall.ENOSPC
		}
		return nil
	}
	if _, err := sealer.Seal(context.Background(), validSealInput()); !errors.Is(err, syscall.ENOSPC) {
		t.Fatalf("expected manifest fsync failure, got %v", err)
	}
	assertNoSealNames(t, directory)
}

func TestSealerRejectsManifestTempSymlinkWithoutFollowing(t *testing.T) {
	writer, directory := newSealWriter(t)
	sealer, _ := NewSealer(writer)
	outside := filepath.Join(filepath.Dir(directory), "outside-manifest")
	if err := os.WriteFile(outside, []byte("sentinel"), SpoolFileMode); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(directory, ManifestTempFileName)); err != nil {
		t.Fatal(err)
	}
	if _, err := sealer.Seal(context.Background(), validSealInput()); !errors.Is(err, ErrSealPublicationExists) {
		t.Fatalf("expected temp-name rejection, got %v", err)
	}
	value, err := os.ReadFile(outside)
	if err != nil || string(value) != "sentinel" {
		t.Fatalf("seal followed or changed temp symlink target: %q %v", value, err)
	}
	if _, err := os.Lstat(filepath.Join(directory, ManifestFileName)); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("temp symlink attack published final manifest: %v", err)
	}
}

func TestSealerReportsDurabilityUncertainWhenRollbackCannotSync(t *testing.T) {
	writer, directory := newSealWriter(t)
	sealer, _ := NewSealer(writer)
	sealer.ops.syncDir = func(int) error { return syscall.EIO }
	if _, err := sealer.Seal(context.Background(), validSealInput()); !errors.Is(err, ErrSealDurabilityUncertain) {
		t.Fatalf("expected uncertain durability, got %v", err)
	}
	if _, err := os.Lstat(filepath.Join(directory, ManifestFileName)); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("rollback left final name visible: %v", err)
	}
}

func assertNoSealNames(t *testing.T, directory string) {
	t.Helper()
	for _, name := range []string{ManifestTempFileName, ManifestFileName} {
		if _, err := os.Lstat(filepath.Join(directory, name)); !errors.Is(err, os.ErrNotExist) {
			t.Fatalf("seal artifact %s survived failure: %v", name, err)
		}
	}
}
