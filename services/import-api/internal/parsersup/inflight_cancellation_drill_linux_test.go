//go:build linux

package parsersup

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/previewspool"
)

// TestSupervisorCancelsStartedWorkerPromptly proves cancellation after the
// worker has emitted a complete frame. The blocked pipe read must be interrupted
// promptly, the process group must be reaped before Parse returns, the partial
// attempt must be removed, and the same spool ID must remain reusable.
func TestSupervisorCancelsStartedWorkerPromptly(t *testing.T) {
	manager, root := newSpoolManager(t)
	config := testConfig(t, "frame_then_sleep")
	config.Limits.WallClock = 10 * time.Second
	supervisor, err := NewSupervisor(config)
	if err != nil {
		t.Fatal(err)
	}

	source := sourceFile(t, "a:{\"title\":\"source\"}\n")
	seal := testSealInput()
	ctx, cancel := context.WithCancel(context.Background())
	result := make(chan error, 1)
	go func() {
		_, parseErr := supervisor.Parse(ctx, ParseRequest{
			Manager: manager,
			SpoolID: testSpoolID,
			Source:  source,
			Seal:    seal,
		})
		result <- parseErr
	}()

	deadline := time.Now().Add(3 * time.Second)
	for !spoolAttemptContainsData(root, testSpoolID) {
		if time.Now().After(deadline) {
			cancel()
			t.Fatal("worker did not emit a frame into the spool before cancellation")
		}
		time.Sleep(10 * time.Millisecond)
	}

	cancelStarted := time.Now()
	cancel()
	select {
	case parseErr := <-result:
		if !errors.Is(parseErr, context.Canceled) {
			t.Fatalf("in-flight cancellation error drift: %v", parseErr)
		}
		if elapsed := time.Since(cancelStarted); elapsed >= time.Second {
			t.Fatalf("in-flight cancellation was not prompt: %s", elapsed)
		}
	case <-time.After(time.Second):
		t.Fatal("in-flight cancellation waited for the wall-clock limit")
	}
	assertRootEmpty(t, root)

	replacementConfig := testConfig(t, "parse")
	replacement, err := NewSupervisor(replacementConfig)
	if err != nil {
		t.Fatal(err)
	}
	evidence, err := replacement.Parse(context.Background(), ParseRequest{
		Manager: manager,
		SpoolID: testSpoolID,
		Source:  sourceFile(t, "a:{\"title\":\"recovered\"}\n"),
		Seal:    testSealInput(),
	})
	if err != nil {
		t.Fatalf("same-spool recovery failed after in-flight cancellation: %v", err)
	}
	if evidence.WriteEvidence.Accepted.RecordCount != 1 ||
		evidence.WriteEvidence.Rejected.RecordCount != 0 {
		t.Fatalf("unexpected recovery evidence: %+v", evidence.WriteEvidence)
	}

	verificationSeal := testSealInput()
	verifier, err := previewspool.NewVerifier(manager)
	if err != nil {
		t.Fatal(err)
	}
	verified, err := verifier.Verify(context.Background(), testSpoolID, previewspool.VerifyExpectation{
		JobID:          verificationSeal.JobID,
		OwnerAccountID: verificationSeal.OwnerAccountID,
		AccountEpoch:   verificationSeal.AccountEpoch,
		Source:         verificationSeal.Source,
		Adapter:        verificationSeal.Adapter,
		OptionsSHA256:  verificationSeal.OptionsSHA256,
	}, verificationSeal.CreatedAt.Add(time.Second))
	if err != nil {
		t.Fatalf("recovered spool failed independent verification: %v", err)
	}
	if verified.Evidence != evidence.WriteEvidence {
		t.Fatalf("recovered verification drift: got %+v want %+v", verified.Evidence, evidence.WriteEvidence)
	}
}

func spoolAttemptContainsData(root string, spoolID string) bool {
	entries, err := os.ReadDir(filepath.Join(root, spoolID))
	if err != nil {
		return false
	}
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		info, err := entry.Info()
		if err == nil && info.Mode().IsRegular() && info.Size() > 0 {
			return true
		}
	}
	return false
}
