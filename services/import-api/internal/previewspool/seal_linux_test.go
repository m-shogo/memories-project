//go:build linux

package previewspool

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"syscall"
	"testing"
	"time"
)

func newSealWriter(t *testing.T) (*StreamWriter, string) {
	t.Helper()
	manager, root := newTestManager(t)
	attempt, err := manager.CreateAttempt(context.Background(), testSpoolID)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = attempt.Cleanup() })
	writer, err := NewStreamWriter(attempt)
	if err != nil {
		t.Fatal(err)
	}
	if err := writer.WriteAccepted(context.Background(), []byte("accepted-canonical")); err != nil {
		t.Fatal(err)
	}
	return writer, filepath.Join(root, testSpoolID)
}

func validSealInput() SealInput {
	createdAt := time.Date(2026, 7, 17, 2, 0, 0, 0, time.UTC)
	return SealInput{
		JobID:          "job_01J000000000000000000000000",
		OwnerAccountID: "acct_01J00000000000000000000000",
		AccountEpoch:   7,
		Source: SealSourceBinding{
			ObjectKey:       "quarantine/job_01J000000000000000000000000/upl_01J00000000000000000000000",
			ObjectVersionID: "version-01J00000000000000000000000",
			ContentLength:   4096,
			ChecksumSHA256:  "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
		},
		Adapter: SealAdapterBinding{
			AdapterID:      "generic-csv",
			AdapterVersion: "1.0.0",
			ArtifactSHA256: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
		},
		OptionsSHA256: "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
		CreatedAt:     createdAt,
		ExpiresAt:     createdAt.Add(24 * time.Hour),
	}
}

func TestSealerPublishesNoReplaceDurableManifest(t *testing.T) {
	writer, directory := newSealWriter(t)
	sealer, err := NewSealer(writer)
	if err != nil {
		t.Fatal(err)
	}
	result, err := sealer.Seal(context.Background(), validSealInput())
	if err != nil {
		t.Fatal(err)
	}
	manifest, err := os.ReadFile(filepath.Join(directory, ManifestFileName))
	if err != nil {
		t.Fatal(err)
	}
	if int64(len(manifest)) != result.ManifestByteLength || result.ManifestSHA256 == "" {
		t.Fatalf("unexpected seal evidence: %+v", result)
	}
	var document map[string]any
	if err := json.Unmarshal(manifest, &document); err != nil {
		t.Fatal(err)
	}
	if document["spoolId"] != testSpoolID || document["sourceRowCount"] != float64(1) {
		t.Fatalf("unexpected manifest: %+v", document)
	}
	if _, err := os.Lstat(filepath.Join(directory, ManifestTempFileName)); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("temporary manifest survived publication: %v", err)
	}
	info, err := os.Lstat(filepath.Join(directory, ManifestFileName))
	if err != nil {
		t.Fatal(err)
	}
	stat := info.Sys().(*syscall.Stat_t)
	if info.Mode().Perm() != SpoolFileMode || stat.Nlink != 1 {
		t.Fatalf("unsafe manifest entry: mode=%v links=%d", info.Mode(), stat.Nlink)
	}

	again, err := sealer.Seal(context.Background(), validSealInput())
	if err != nil || again != result {
		t.Fatalf("same seal was not idempotent: %+v %v", again, err)
	}
	changed := validSealInput()
	changed.OptionsSHA256 = "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
	if _, err := sealer.Seal(context.Background(), changed); !errors.Is(err, ErrSealConflict) {
		t.Fatalf("conflicting reseal was allowed: %v", err)
	}
}

func TestSealerRejectsInvalidBindingTerminally(t *testing.T) {
	writer, directory := newSealWriter(t)
	sealer, _ := NewSealer(writer)
	input := validSealInput()
	input.Source.ObjectKey = "quarantine/other-job/upl_01J00000000000000000000000"
	if _, err := sealer.Seal(context.Background(), input); !errors.Is(err, ErrInvalidSealInput) {
		t.Fatalf("expected invalid binding, got %v", err)
	}
	if _, err := sealer.Seal(context.Background(), validSealInput()); !errors.Is(err, ErrInvalidSealInput) {
		t.Fatalf("invalid binding was resumable: %v", err)
	}
	if _, err := os.Lstat(filepath.Join(directory, ManifestFileName)); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("invalid binding published a manifest: %v", err)
	}
}

func TestSealerStreamFsyncFailureIsSticky(t *testing.T) {
	writer, directory := newSealWriter(t)
	sealer, _ := NewSealer(writer)
	sealer.ops.syncFile = func(*os.File) error { return syscall.ENOSPC }
	if _, err := sealer.Seal(context.Background(), validSealInput()); !errors.Is(err, syscall.ENOSPC) {
		t.Fatalf("expected fsync failure, got %v", err)
	}
	if _, err := sealer.Seal(context.Background(), validSealInput()); !errors.Is(err, syscall.ENOSPC) {
		t.Fatalf("fsync failure was not sticky: %v", err)
	}
	if _, err := os.Lstat(filepath.Join(directory, ManifestFileName)); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("fsync failure published a manifest: %v", err)
	}
}

func TestSealerDoesNotOverwriteExistingManifest(t *testing.T) {
	writer, directory := newSealWriter(t)
	sealer, _ := NewSealer(writer)
	path := filepath.Join(directory, ManifestFileName)
	if err := os.WriteFile(path, []byte("sentinel"), SpoolFileMode); err != nil {
		t.Fatal(err)
	}
	if _, err := sealer.Seal(context.Background(), validSealInput()); !errors.Is(err, ErrSealPublicationExists) {
		t.Fatalf("expected no-replace rejection, got %v", err)
	}
	value, err := os.ReadFile(path)
	if err != nil || string(value) != "sentinel" {
		t.Fatalf("existing manifest was overwritten: %q %v", value, err)
	}
}

func TestSealerDirectoryFsyncFailureRollsBackPublication(t *testing.T) {
	writer, directory := newSealWriter(t)
	sealer, _ := NewSealer(writer)
	calls := 0
	sealer.ops.syncDir = func(int) error {
		calls++
		if calls == 1 {
			return syscall.EIO
		}
		return nil
	}
	if _, err := sealer.Seal(context.Background(), validSealInput()); !errors.Is(err, ErrSealPublish) {
		t.Fatalf("expected directory sync failure, got %v", err)
	}
	if _, err := os.Lstat(filepath.Join(directory, ManifestFileName)); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("failed publication was not rolled back: %v", err)
	}
}
