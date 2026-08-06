package importflow

import (
	"context"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/previewcommit"
	"github.com/m-shogo/memories-project/services/import-api/internal/previewspool"
)

// ResumeCommit resumes only the durable-verification and atomic database
// portion of an import attempt. It is the recovery path after parse/seal
// succeeded but Preview commit could not reach PostgreSQL.
//
// The method deliberately does not touch object storage or launch a parser
// worker. It reopens and independently verifies the existing sealed spool
// against the full request binding, re-decodes its canonical records, then
// invokes the same atomic committer used by Run. A missing, expired, corrupted
// or differently bound spool fails closed before any database transaction.
func (f *Flow) ResumeCommit(ctx context.Context, request Request, now time.Time) (Result, error) {
	if f == nil || f.Spool == nil || f.Committer == nil {
		return Result{}, ErrInvalidFlowConfig
	}
	if ctx == nil || now.IsZero() || request.SpoolID == "" || request.PreviewID == "" {
		return Result{}, ErrInvalidFlowRequest
	}
	seal := request.Seal
	verifier, err := previewspool.NewVerifier(f.Spool)
	if err != nil {
		return Result{}, err
	}
	verified, err := verifier.Verify(ctx, request.SpoolID, previewspool.VerifyExpectation{
		JobID:          seal.JobID,
		OwnerAccountID: seal.OwnerAccountID,
		AccountEpoch:   seal.AccountEpoch,
		Source:         seal.Source,
		Adapter:        seal.Adapter,
		OptionsSHA256:  seal.OptionsSHA256,
	}, now)
	if err != nil {
		return Result{}, err
	}

	acceptedRecords, rejectedRecords, err := previewspool.CollectSealedRecords(ctx, f.Spool, verified)
	if err != nil {
		return Result{}, err
	}
	candidates, rejections, err := decodeCommitRows(acceptedRecords, rejectedRecords)
	if err != nil {
		return Result{}, err
	}
	commit, err := f.Committer.Commit(ctx, previewcommit.CommitRequest{
		PreviewID:  request.PreviewID,
		Verified:   verified,
		Candidates: candidates,
		Rejections: rejections,
	}, now)
	if err != nil {
		return Result{}, err
	}
	return Result{Verified: verified, Commit: commit}, nil
}
