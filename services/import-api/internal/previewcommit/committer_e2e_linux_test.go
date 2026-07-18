//go:build linux

package previewcommit

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"os"
	"path/filepath"
	"testing"

	"github.com/m-shogo/memories-project/services/import-api/internal/previewspool"
)

// TestCommitAfterRealSpoolVerificationFlow proves the full required flow with
// no shortcuts: bounded spool write → fsync/no-replace seal → independent
// decode/count/re-hash verification → one short CopyFrom transaction.
func TestCommitAfterRealSpoolVerificationFlow(t *testing.T) {
	pool := testPool(t)
	ctx := context.Background()

	root := filepath.Join(t.TempDir(), "spool")
	if err := os.Mkdir(root, 0o700); err != nil {
		t.Fatal(err)
	}
	manager, err := previewspool.OpenManager(root)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = manager.Close() })

	attempt, err := manager.CreateAttempt(ctx, fixtureSpoolID)
	if err != nil {
		t.Fatal(err)
	}
	writer, err := previewspool.NewStreamWriter(attempt)
	if err != nil {
		t.Fatal(err)
	}
	acceptedRecord := []byte(`{"title":"one"}`)
	if err := writer.WriteAccepted(ctx, acceptedRecord); err != nil {
		t.Fatal(err)
	}
	rejectedRecord := []byte(`{"sourceRow":2,"issueCodes":["IMPORT_ROW_EMPTY"]}`)
	if err := writer.WriteRejected(ctx, rejectedRecord); err != nil {
		t.Fatal(err)
	}

	sealer, err := previewspool.NewSealer(writer)
	if err != nil {
		t.Fatal(err)
	}
	base := verifiedFixture()
	input := previewspool.SealInput{
		JobID:          base.JobID,
		OwnerAccountID: base.OwnerAccountID,
		AccountEpoch:   base.AccountEpoch,
		Source:         base.Source,
		Adapter:        base.Adapter,
		OptionsSHA256:  base.OptionsSHA256,
		CreatedAt:      base.CreatedAt,
		ExpiresAt:      base.ExpiresAt,
	}
	if _, err := sealer.Seal(ctx, input); err != nil {
		t.Fatal(err)
	}

	verifier, err := previewspool.NewVerifier(manager)
	if err != nil {
		t.Fatal(err)
	}
	verified, err := verifier.Verify(ctx, fixtureSpoolID, previewspool.VerifyExpectation{
		JobID:          input.JobID,
		OwnerAccountID: input.OwnerAccountID,
		AccountEpoch:   input.AccountEpoch,
		Source:         input.Source,
		Adapter:        input.Adapter,
		OptionsSHA256:  input.OptionsSHA256,
	}, commitNow())
	if err != nil {
		t.Fatal(err)
	}

	acceptedSum := sha256.Sum256(acceptedRecord)
	committer, err := NewCommitter(pool)
	if err != nil {
		t.Fatal(err)
	}
	result, err := committer.Commit(ctx, CommitRequest{
		PreviewID: "prv_endtoend0001",
		Verified:  verified,
		Candidates: []CandidateRow{
			{Ordinal: 1, SourceRow: 1, RecordSHA256: hex.EncodeToString(acceptedSum[:]), CanonicalRecord: acceptedRecord},
		},
		Rejections: []RejectionRow{
			{Ordinal: 1, SourceRow: 2, IssueCodes: []string{"IMPORT_ROW_EMPTY"}},
		},
	}, commitNow())
	if err != nil {
		t.Fatal(err)
	}
	if result.AlreadyCommitted || result.CommitKey != DeriveCommitKey(verified) {
		t.Fatalf("unexpected end-to-end commit result: %+v", result)
	}

	var spoolID, acceptedSHA string
	var acceptedCount int
	if err := pool.QueryRow(ctx,
		"SELECT spool_id, accepted_sha256, accepted_count FROM memory_os.preview_ready WHERE id = $1",
		result.PreviewID,
	).Scan(&spoolID, &acceptedSHA, &acceptedCount); err != nil {
		t.Fatal(err)
	}
	if spoolID != fixtureSpoolID || acceptedSHA != verified.Evidence.Accepted.SHA256 || acceptedCount != 1 {
		t.Fatalf("committed row does not carry recomputed evidence: %s %s %d", spoolID, acceptedSHA, acceptedCount)
	}
}
