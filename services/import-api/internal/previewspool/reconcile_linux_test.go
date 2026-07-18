//go:build linux

package previewspool

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func sealAttemptAt(t *testing.T, manager *Manager, spoolID string) {
	t.Helper()
	attempt, err := manager.CreateAttempt(context.Background(), spoolID)
	if err != nil {
		t.Fatal(err)
	}
	writer, err := NewStreamWriter(attempt)
	if err != nil {
		t.Fatal(err)
	}
	if err := writer.WriteAccepted(context.Background(), []byte("accepted-canonical-record")); err != nil {
		t.Fatal(err)
	}
	if err := writer.WriteRejected(context.Background(), []byte("rejected-canonical-record")); err != nil {
		t.Fatal(err)
	}
	sealer, err := NewSealer(writer)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := sealer.Seal(context.Background(), validSealInput()); err != nil {
		t.Fatal(err)
	}
}

func unsealedAttemptAt(t *testing.T, manager *Manager, spoolID string, claim bool) {
	t.Helper()
	attempt, err := manager.CreateAttempt(context.Background(), spoolID)
	if err != nil {
		t.Fatal(err)
	}
	if claim {
		writer, err := NewStreamWriter(attempt)
		if err != nil {
			t.Fatal(err)
		}
		if err := writer.WriteAccepted(context.Background(), []byte("accepted-canonical-record")); err != nil {
			t.Fatal(err)
		}
	}
	if err := attempt.CloseFiles(); err != nil {
		t.Fatal(err)
	}
}

func reconcileAll(t *testing.T, manager *Manager, now time.Time) ReconcileReport {
	t.Helper()
	reconciler, err := NewReconciler(manager)
	if err != nil {
		t.Fatal(err)
	}
	report, err := reconciler.Reconcile(context.Background(), now)
	if err != nil {
		t.Fatal(err)
	}
	return report
}

func singleOutcome(t *testing.T, report ReconcileReport, name string, outcome ReconcileOutcome) {
	t.Helper()
	if len(report.Entries) != 1 || report.Entries[0].Name != name || report.Entries[0].Outcome != outcome {
		t.Fatalf("unexpected reconciliation report: %+v", report.Entries)
	}
}

func TestReconcileKeepsSealedUnexpiredAndIsIdempotent(t *testing.T) {
	manager, root := newTestManager(t)
	sealAttemptAt(t, manager, testSpoolID)
	report := reconcileAll(t, manager, verifyNow())
	singleOutcome(t, report, testSpoolID, ReconcileSealedKept)
	again := reconcileAll(t, manager, verifyNow())
	singleOutcome(t, again, testSpoolID, ReconcileSealedKept)
	if _, err := os.Lstat(filepath.Join(root, testSpoolID, ManifestFileName)); err != nil {
		t.Fatalf("sealed manifest was disturbed: %v", err)
	}
	verifier, _ := NewVerifier(manager)
	if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(validSealInput()), verifyNow()); err != nil {
		t.Fatalf("kept attempt no longer verifies: %v", err)
	}
}

func TestReconcileRemovesExpiredSealedAttempt(t *testing.T) {
	manager, root := newTestManager(t)
	sealAttemptAt(t, manager, testSpoolID)
	report := reconcileAll(t, manager, validSealInput().ExpiresAt)
	singleOutcome(t, report, testSpoolID, ReconcileExpiredRemoved)
	if _, err := os.Lstat(filepath.Join(root, testSpoolID)); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("expired attempt survived: %v", err)
	}
}

func TestReconcileRemovesUnsealedAttempts(t *testing.T) {
	for name, claim := range map[string]bool{"manifest-placeholder": false, "claimed-not-sealed": true} {
		t.Run(name, func(t *testing.T) {
			manager, root := newTestManager(t)
			unsealedAttemptAt(t, manager, testSpoolID, claim)
			report := reconcileAll(t, manager, verifyNow())
			singleOutcome(t, report, testSpoolID, ReconcileUnsealedRemoved)
			if _, err := os.Lstat(filepath.Join(root, testSpoolID)); !errors.Is(err, os.ErrNotExist) {
				t.Fatalf("unsealed attempt survived: %v", err)
			}
		})
	}
}

func TestReconcileCompletesCrashedPublication(t *testing.T) {
	manager, root := newTestManager(t)
	sealAttemptAt(t, manager, testSpoolID)
	directory := filepath.Join(root, testSpoolID)
	if err := os.Link(filepath.Join(directory, ManifestFileName), filepath.Join(directory, ManifestTempFileName)); err != nil {
		t.Fatal(err)
	}
	report := reconcileAll(t, manager, verifyNow())
	singleOutcome(t, report, testSpoolID, ReconcilePublicationCompleted)
	if _, err := os.Lstat(filepath.Join(directory, ManifestTempFileName)); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("temp residue survived completion: %v", err)
	}
	verifier, _ := NewVerifier(manager)
	if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(validSealInput()), verifyNow()); err != nil {
		t.Fatalf("completed publication does not verify: %v", err)
	}
}

func TestReconcileRemovesTempOnlyResidue(t *testing.T) {
	manager, root := newTestManager(t)
	unsealedAttemptAt(t, manager, testSpoolID, true)
	directory := filepath.Join(root, testSpoolID)
	if err := os.WriteFile(filepath.Join(directory, ManifestTempFileName), []byte("residue"), SpoolFileMode); err != nil {
		t.Fatal(err)
	}
	report := reconcileAll(t, manager, verifyNow())
	singleOutcome(t, report, testSpoolID, ReconcileUnsealedRemoved)
	if _, err := os.Lstat(directory); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("temp-only residue survived: %v", err)
	}
}
