//go:build linux

package previewspool

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"
)

const testSpoolID = "spl_01J00000000000000000000000"

func newTestManager(t *testing.T) (*Manager, string) {
	t.Helper()
	root := filepath.Join(t.TempDir(), "spool")
	if err := os.Mkdir(root, AttemptDirMode); err != nil {
		t.Fatal(err)
	}
	manager, err := OpenManager(root)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = manager.Close() })
	return manager, root
}

func TestCreateAttemptUsesPrivateFixedEntriesAndCleanupIsIdempotent(t *testing.T) {
	manager, root := newTestManager(t)
	attempt, err := manager.CreateAttempt(context.Background(), testSpoolID)
	if err != nil {
		t.Fatal(err)
	}
	if attempt.ID() != testSpoolID {
		t.Fatalf("unexpected ID: %q", attempt.ID())
	}
	for _, file := range []*os.File{attempt.AcceptedFile(), attempt.RejectedFile(), attempt.ManifestFile()} {
		if file == nil {
			t.Fatal("missing spool file")
		}
		info, err := file.Stat()
		if err != nil {
			t.Fatal(err)
		}
		if info.Mode().Perm() != SpoolFileMode || !info.Mode().IsRegular() {
			t.Fatalf("unsafe file mode: %v", info.Mode())
		}
	}
	info, err := os.Lstat(filepath.Join(root, testSpoolID))
	if err != nil {
		t.Fatal(err)
	}
	if !info.IsDir() || info.Mode().Perm() != AttemptDirMode {
		t.Fatalf("unsafe directory: %v", info.Mode())
	}

	if err := attempt.Cleanup(); err != nil {
		t.Fatal(err)
	}
	if err := attempt.Cleanup(); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Lstat(filepath.Join(root, testSpoolID)); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("attempt survived cleanup: %v", err)
	}
}

func TestCreateAttemptDoesNotReuseExistingDirectory(t *testing.T) {
	manager, root := newTestManager(t)
	existing := filepath.Join(root, testSpoolID)
	if err := os.Mkdir(existing, AttemptDirMode); err != nil {
		t.Fatal(err)
	}
	sentinel := filepath.Join(existing, "sentinel")
	if err := os.WriteFile(sentinel, []byte("keep"), SpoolFileMode); err != nil {
		t.Fatal(err)
	}

	_, err := manager.CreateAttempt(context.Background(), testSpoolID)
	if !errors.Is(err, ErrAttemptExists) {
		t.Fatalf("expected existing rejection, got %v", err)
	}
	value, err := os.ReadFile(sentinel)
	if err != nil || string(value) != "keep" {
		t.Fatalf("existing attempt changed: %q %v", value, err)
	}
}

func TestCreateAttemptRejectsInjectedSymlinkWithoutFollowingIt(t *testing.T) {
	manager, root := newTestManager(t)
	target := filepath.Join(root, "outside")
	if err := os.WriteFile(target, []byte("outside"), SpoolFileMode); err != nil {
		t.Fatal(err)
	}
	manager.afterStep = func(stage string) {
		if stage != stageDirectoryOpened {
			return
		}
		if err := os.Symlink(target, filepath.Join(root, testSpoolID, AcceptedFileName)); err != nil {
			t.Fatal(err)
		}
	}

	_, err := manager.CreateAttempt(context.Background(), testSpoolID)
	if !errors.Is(err, ErrAttemptExists) {
		t.Fatalf("expected injected entry rejection, got %v", err)
	}
	value, readErr := os.ReadFile(target)
	if readErr != nil || string(value) != "outside" {
		t.Fatalf("create followed injected symlink: %q %v", value, readErr)
	}
	if _, statErr := os.Lstat(filepath.Join(root, testSpoolID)); !errors.Is(statErr, os.ErrNotExist) {
		t.Fatalf("failed attempt survived cleanup: %v", statErr)
	}
}

func TestCreateAttemptCleansEveryCancelledPartialStage(t *testing.T) {
	stages := []string{
		stageDirectoryCreated,
		stageDirectoryOpened,
		stageAcceptedCreated,
		stageRejectedCreated,
		stageManifestCreated,
	}
	for index, stage := range stages {
		t.Run(stage, func(t *testing.T) {
			manager, root := newTestManager(t)
			ctx, cancel := context.WithCancel(context.Background())
			manager.afterStep = func(current string) {
				if current == stage {
					cancel()
				}
			}
			id := testSpoolID + string(rune('A'+index))
			_, err := manager.CreateAttempt(ctx, id)
			if !errors.Is(err, context.Canceled) {
				t.Fatalf("expected cancellation, got %v", err)
			}
			if _, err := os.Lstat(filepath.Join(root, id)); !errors.Is(err, os.ErrNotExist) {
				t.Fatalf("partial attempt survived: %v", err)
			}
		})
	}
}

func TestCleanupRejectsUnexpectedEntry(t *testing.T) {
	manager, root := newTestManager(t)
	attempt, err := manager.CreateAttempt(context.Background(), testSpoolID)
	if err != nil {
		t.Fatal(err)
	}
	unexpected := filepath.Join(root, testSpoolID, "unexpected")
	if err := os.WriteFile(unexpected, []byte("x"), SpoolFileMode); err != nil {
		t.Fatal(err)
	}

	err = attempt.Cleanup()
	if !errors.Is(err, ErrUnexpectedEntry) {
		t.Fatalf("expected unexpected entry error, got %v", err)
	}
	if _, statErr := os.Lstat(unexpected); statErr != nil {
		t.Fatalf("unexpected entry was removed: %v", statErr)
	}
}

func TestCleanupRejectsAttemptSubstitution(t *testing.T) {
	manager, root := newTestManager(t)
	attempt, err := manager.CreateAttempt(context.Background(), testSpoolID)
	if err != nil {
		t.Fatal(err)
	}
	original := filepath.Join(root, testSpoolID)
	moved := original + "-moved"
	if err := os.Rename(original, moved); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(original, AttemptDirMode); err != nil {
		t.Fatal(err)
	}

	err = attempt.Cleanup()
	if !errors.Is(err, ErrAttemptSubstituted) {
		t.Fatalf("expected substitution rejection, got %v", err)
	}
	if _, statErr := os.Lstat(original); statErr != nil {
		t.Fatalf("replacement was removed: %v", statErr)
	}
}

func TestCleanupUnlinksSymlinkWithoutFollowingIt(t *testing.T) {
	manager, root := newTestManager(t)
	attempt, err := manager.CreateAttempt(context.Background(), testSpoolID)
	if err != nil {
		t.Fatal(err)
	}
	if err := attempt.AcceptedFile().Close(); err != nil {
		t.Fatal(err)
	}
	target := filepath.Join(root, "outside")
	if err := os.WriteFile(target, []byte("outside"), SpoolFileMode); err != nil {
		t.Fatal(err)
	}
	accepted := filepath.Join(root, testSpoolID, AcceptedFileName)
	if err := os.Remove(accepted); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(target, accepted); err != nil {
		t.Fatal(err)
	}

	if err := attempt.Cleanup(); err != nil {
		t.Fatal(err)
	}
	value, err := os.ReadFile(target)
	if err != nil || string(value) != "outside" {
		t.Fatalf("cleanup followed symlink: %q %v", value, err)
	}
}

func TestOpenManagerRejectsUnsafeRoot(t *testing.T) {
	parent := t.TempDir()
	permissive := filepath.Join(parent, "permissive")
	if err := os.Mkdir(permissive, 0o755); err != nil {
		t.Fatal(err)
	}
	if _, err := OpenManager(permissive); !errors.Is(err, ErrUnsafeRoot) {
		t.Fatalf("expected unsafe mode rejection, got %v", err)
	}

	target := filepath.Join(parent, "target")
	if err := os.Mkdir(target, AttemptDirMode); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(parent, "link")
	if err := os.Symlink(target, link); err != nil {
		t.Fatal(err)
	}
	if _, err := OpenManager(link); !errors.Is(err, ErrUnsafeRoot) {
		t.Fatalf("expected symlink rejection, got %v", err)
	}
}

func TestCreateAttemptRejectsInvalidIDAndClosedManager(t *testing.T) {
	manager, _ := newTestManager(t)
	if _, err := manager.CreateAttempt(context.Background(), "../escape"); !errors.Is(err, ErrInvalidSpoolID) {
		t.Fatalf("expected invalid ID, got %v", err)
	}
	if err := manager.Close(); err != nil {
		t.Fatal(err)
	}
	if _, err := manager.CreateAttempt(context.Background(), testSpoolID); !errors.Is(err, ErrManagerClosed) {
		t.Fatalf("expected closed manager, got %v", err)
	}
}
