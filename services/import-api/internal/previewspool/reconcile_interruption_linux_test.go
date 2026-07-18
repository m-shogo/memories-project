//go:build linux

package previewspool

import (
	"bytes"
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestReconcileQuarantinesUnclassifiableEntries(t *testing.T) {
	t.Run("foreign-root-name", func(t *testing.T) {
		manager, root := newTestManager(t)
		if err := os.WriteFile(filepath.Join(root, "stray.txt"), []byte("stray"), SpoolFileMode); err != nil {
			t.Fatal(err)
		}
		report := reconcileAll(t, manager, verifyNow())
		singleOutcome(t, report, "stray.txt", ReconcileQuarantined)
		if _, err := os.Lstat(filepath.Join(root, "stray.txt")); err != nil {
			t.Fatalf("quarantined root entry was deleted: %v", err)
		}
	})
	t.Run("root-symlink", func(t *testing.T) {
		manager, root := newTestManager(t)
		outside := t.TempDir()
		if err := os.Symlink(outside, filepath.Join(root, testSpoolID)); err != nil {
			t.Fatal(err)
		}
		report := reconcileAll(t, manager, verifyNow())
		singleOutcome(t, report, testSpoolID, ReconcileQuarantined)
		if _, err := os.Lstat(filepath.Join(root, testSpoolID)); err != nil {
			t.Fatalf("quarantined symlink was deleted: %v", err)
		}
	})
	t.Run("unknown-attempt-entry", func(t *testing.T) {
		manager, root := newTestManager(t)
		sealAttemptAt(t, manager, testSpoolID)
		if err := os.WriteFile(filepath.Join(root, testSpoolID, "extra.bin"), []byte("extra"), SpoolFileMode); err != nil {
			t.Fatal(err)
		}
		report := reconcileAll(t, manager, verifyNow())
		singleOutcome(t, report, testSpoolID, ReconcileQuarantined)
		if _, err := os.Lstat(filepath.Join(root, testSpoolID, ManifestFileName)); err != nil {
			t.Fatalf("quarantined attempt was disturbed: %v", err)
		}
	})
	t.Run("non-canonical-manifest", func(t *testing.T) {
		manager, root := newTestManager(t)
		sealAttemptAt(t, manager, testSpoolID)
		path := filepath.Join(root, testSpoolID, ManifestFileName)
		payload, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, append(payload, '\n'), SpoolFileMode); err != nil {
			t.Fatal(err)
		}
		report := reconcileAll(t, manager, verifyNow())
		singleOutcome(t, report, testSpoolID, ReconcileQuarantined)
		if _, err := os.Lstat(path); err != nil {
			t.Fatalf("quarantined manifest was deleted: %v", err)
		}
	})
	t.Run("conflicting-temp-inode", func(t *testing.T) {
		manager, root := newTestManager(t)
		sealAttemptAt(t, manager, testSpoolID)
		temp := filepath.Join(root, testSpoolID, ManifestTempFileName)
		if err := os.WriteFile(temp, []byte("imposter"), SpoolFileMode); err != nil {
			t.Fatal(err)
		}
		report := reconcileAll(t, manager, verifyNow())
		singleOutcome(t, report, testSpoolID, ReconcileQuarantined)
		if _, err := os.Lstat(temp); err != nil {
			t.Fatalf("conflicting temp was deleted without classification: %v", err)
		}
		if _, err := os.Lstat(filepath.Join(root, testSpoolID, ManifestFileName)); err != nil {
			t.Fatalf("published manifest was disturbed: %v", err)
		}
	})
	t.Run("foreign-spool-manifest", func(t *testing.T) {
		manager, root := newTestManager(t)
		sealAttemptAt(t, manager, testSpoolID)
		path := filepath.Join(root, testSpoolID, ManifestFileName)
		payload, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		spoofed := bytes.Replace(payload, []byte(testSpoolID), []byte("spl_01J00000000000000000000001"), 1)
		if err := os.WriteFile(path, spoofed, SpoolFileMode); err != nil {
			t.Fatal(err)
		}
		report := reconcileAll(t, manager, verifyNow())
		singleOutcome(t, report, testSpoolID, ReconcileQuarantined)
	})
}

func TestReconcileCancellationIsResumable(t *testing.T) {
	manager, root := newTestManager(t)
	sealAttemptAt(t, manager, "spl_01J0000000000000000000000A")
	unsealedAttemptAt(t, manager, "spl_01J0000000000000000000000B", true)
	sealAttemptAt(t, manager, "spl_01J0000000000000000000000C")

	reconciler, err := NewReconciler(manager)
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	calls := 0
	reconciler.afterEntry = func(string) {
		calls++
		if calls == 1 {
			cancel()
		}
	}
	report, err := reconciler.Reconcile(ctx, verifyNow())
	if !errors.Is(err, context.Canceled) {
		t.Fatalf("expected cancellation, got %v", err)
	}
	if len(report.Entries) != 1 || report.Entries[0].Name != "spl_01J0000000000000000000000A" {
		t.Fatalf("unexpected partial report: %+v", report.Entries)
	}

	reconciler.afterEntry = nil
	resumed, err := reconciler.Reconcile(context.Background(), verifyNow())
	if err != nil {
		t.Fatal(err)
	}
	if len(resumed.Entries) != 3 {
		t.Fatalf("resumed pass did not cover the root: %+v", resumed.Entries)
	}
	if _, err := os.Lstat(filepath.Join(root, "spl_01J0000000000000000000000B")); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("unsealed attempt survived resumed pass: %v", err)
	}
	for _, name := range []string{"spl_01J0000000000000000000000A", "spl_01J0000000000000000000000C"} {
		if _, err := os.Lstat(filepath.Join(root, name, ManifestFileName)); err != nil {
			t.Fatalf("sealed attempt %s was disturbed: %v", name, err)
		}
	}
	if report.Quarantined() != nil || resumed.Quarantined() != nil {
		t.Fatalf("unexpected quarantine entries: %+v %+v", report.Entries, resumed.Entries)
	}
}

func TestReconcileValidatesInputs(t *testing.T) {
	manager, _ := newTestManager(t)
	if _, err := NewReconciler(nil); !errors.Is(err, ErrInvalidRoot) {
		t.Fatalf("nil manager was accepted: %v", err)
	}
	reconciler, err := NewReconciler(manager)
	if err != nil {
		t.Fatal(err)
	}
	var missingCtx context.Context
	if _, err := reconciler.Reconcile(missingCtx, verifyNow()); !errors.Is(err, ErrReconcileInvalidInput) {
		t.Fatalf("nil context was accepted: %v", err)
	}
	if _, err := reconciler.Reconcile(context.Background(), time.Time{}); !errors.Is(err, ErrReconcileInvalidInput) {
		t.Fatalf("zero clock was accepted: %v", err)
	}
	if err := manager.Close(); err != nil {
		t.Fatal(err)
	}
	if _, err := reconciler.Reconcile(context.Background(), verifyNow()); !errors.Is(err, ErrManagerClosed) {
		t.Fatalf("closed manager was usable: %v", err)
	}
}
