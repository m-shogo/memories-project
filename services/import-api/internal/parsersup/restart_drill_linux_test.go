//go:build linux

package parsersup

import (
	"context"
	"errors"
	"testing"

	"github.com/m-shogo/memories-project/services/import-api/internal/previewspool"
)

// TestSupervisorRestartsSameSpoolAfterFailedAttempt proves the recovery path,
// not only the initial fail-closed path. A worker that emits a truncated frame
// must leave no spool residue, the same manager and spool ID must remain usable,
// and a clean replacement worker must be independently verifiable.
func TestSupervisorRestartsSameSpoolAfterFailedAttempt(t *testing.T) {
	manager, root := newSpoolManager(t)

	failedConfig := testConfig(t, "partial")
	failedSupervisor, err := NewSupervisor(failedConfig)
	if err != nil {
		t.Fatal(err)
	}
	_, err = failedSupervisor.Parse(context.Background(), ParseRequest{
		Manager: manager,
		SpoolID: testSpoolID,
		Source:  sourceFile(t, "a:{\"title\":\"partial\"}\n"),
		Seal:    testSealInput(),
	})
	if !errors.Is(err, ErrFrameProtocolViolation) {
		t.Fatalf("truncated worker output was not rejected: %v", err)
	}
	assertRootEmpty(t, root)

	replacementConfig := testConfig(t, "parse")
	replacementSupervisor, err := NewSupervisor(replacementConfig)
	if err != nil {
		t.Fatal(err)
	}
	evidence, err := replacementSupervisor.Parse(context.Background(), ParseRequest{
		Manager: manager,
		SpoolID: testSpoolID,
		Source:  sourceFile(t, "a:{\"title\":\"recovered\"}\n"),
		Seal:    testSealInput(),
	})
	if err != nil {
		t.Fatalf("replacement worker could not reuse the cleaned spool ID: %v", err)
	}
	if evidence.WriteEvidence.Accepted.RecordCount != 1 || evidence.WriteEvidence.Rejected.RecordCount != 0 {
		t.Fatalf("unexpected recovered evidence: %+v", evidence.WriteEvidence)
	}

	seal := testSealInput()
	verifier, err := previewspool.NewVerifier(manager)
	if err != nil {
		t.Fatal(err)
	}
	verified, err := verifier.Verify(context.Background(), testSpoolID, previewspool.VerifyExpectation{
		JobID:          seal.JobID,
		OwnerAccountID: seal.OwnerAccountID,
		AccountEpoch:   seal.AccountEpoch,
		Source:         seal.Source,
		Adapter:        seal.Adapter,
		OptionsSHA256:  seal.OptionsSHA256,
	}, seal.CreatedAt.Add(1))
	if err != nil {
		t.Fatalf("recovered spool failed independent verification: %v", err)
	}
	if verified.Evidence != evidence.WriteEvidence {
		t.Fatalf("recovered verification drift: got %+v want %+v", verified.Evidence, evidence.WriteEvidence)
	}
}
