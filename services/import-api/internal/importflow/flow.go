// Package importflow composes the supervised import pipeline end to end:
// exact-version quarantine fetch → supervised transaction-free parse →
// durable seal → independent verification → decoded rows → one short atomic
// database commit. No HTTP server, session or client wiring lives here.
package importflow

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/canonrecord"
	"github.com/m-shogo/memories-project/services/import-api/internal/objectstore"
	"github.com/m-shogo/memories-project/services/import-api/internal/parsersup"
	"github.com/m-shogo/memories-project/services/import-api/internal/previewcommit"
	"github.com/m-shogo/memories-project/services/import-api/internal/previewspool"
)

var (
	ErrInvalidFlowConfig      = errors.New("invalid import flow configuration")
	ErrInvalidFlowRequest     = errors.New("invalid import flow request")
	ErrSourceBindingMismatch  = errors.New("current object state does not match the bound source")
	ErrCanonicalRecordInvalid = errors.New("record violates the canonical adapter record contract")
	ErrEvidenceDiverged       = errors.New("verification evidence diverged from sealed evidence")
)

// Flow owns the composition only; every security boundary stays inside the
// composed packages. After a successful commit the sealed spool is left for
// the TTL reconciler (its lifetime is bounded by the seal expiry); the
// downloaded source copy is always removed.
type Flow struct {
	Objects    *objectstore.Client
	Supervisor *parsersup.Supervisor
	Spool      *previewspool.Manager
	Committer  *previewcommit.Committer
	ScratchDir string
}

// Request binds one import attempt. Seal carries the full job/owner/epoch/
// source/adapter/options binding plus the spool TTL, exactly as sealed into
// the manifest and later re-verified.
type Request struct {
	SpoolID   string
	PreviewID string
	Seal      previewspool.SealInput
}

type Result struct {
	Verified previewspool.VerifiedSpool
	Commit   previewcommit.CommitResult
}

// Run executes one supervised import attempt end to end. Any failure before
// COMMIT leaves no durable database state; parse failures additionally leave
// no spool attempt.
func (f *Flow) Run(ctx context.Context, request Request, now time.Time) (Result, error) {
	if f == nil || f.Objects == nil || f.Supervisor == nil || f.Spool == nil || f.Committer == nil {
		return Result{}, ErrInvalidFlowConfig
	}
	if !filepath.IsAbs(f.ScratchDir) || filepath.Clean(f.ScratchDir) != f.ScratchDir {
		return Result{}, fmt.Errorf("%w: scratch directory", ErrInvalidFlowConfig)
	}
	if ctx == nil || now.IsZero() || request.SpoolID == "" || request.PreviewID == "" {
		return Result{}, ErrInvalidFlowRequest
	}
	seal := request.Seal

	// 1. Server-side recheck: the current object must still be exactly the
	// bound version. A newer version means the quarantine object changed
	// after scanning and the attempt fails closed.
	metadata, err := f.Objects.HeadObject(ctx, seal.Source.ObjectKey)
	if err != nil {
		return Result{}, err
	}
	if metadata.VersionID != seal.Source.ObjectVersionID ||
		metadata.ContentLength != seal.Source.ContentLength ||
		!strings.EqualFold(metadata.ChecksumSHA256, seal.Source.ChecksumSHA256) {
		return Result{}, ErrSourceBindingMismatch
	}

	// 2. Version-pinned download into a private exclusive scratch file with
	// streaming length/checksum verification.
	sourcePath := filepath.Join(f.ScratchDir, "source-"+request.SpoolID)
	source, err := os.OpenFile(sourcePath, os.O_RDWR|os.O_CREATE|os.O_EXCL, 0o600)
	if err != nil {
		return Result{}, fmt.Errorf("create import source scratch file: %w", err)
	}
	defer func() {
		_ = source.Close()
		_ = os.Remove(sourcePath)
	}()
	if err := f.Objects.GetObjectVersion(ctx, seal.Source.ObjectKey, seal.Source.ObjectVersionID,
		seal.Source.ContentLength, seal.Source.ChecksumSHA256, source); err != nil {
		return Result{}, err
	}

	// 3. Supervised transaction-free parse into a sealed spool.
	sealed, err := f.Supervisor.Parse(ctx, parsersup.ParseRequest{
		Manager: f.Spool,
		SpoolID: request.SpoolID,
		Source:  source,
		Seal:    seal,
	})
	if err != nil {
		return Result{}, err
	}

	// 4. Independent verification of the sealed spool.
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
	if verified.Evidence != sealed.WriteEvidence {
		return Result{}, ErrEvidenceDiverged
	}

	// 5. Re-read the verified streams and decode commit rows under the
	// reviewed canonical adapter record contract (internal/canonrecord).
	acceptedRecords, rejectedRecords, err := previewspool.CollectSealedRecords(ctx, f.Spool, verified)
	if err != nil {
		return Result{}, err
	}
	candidates, rejections, err := decodeCommitRows(acceptedRecords, rejectedRecords)
	if err != nil {
		return Result{}, err
	}

	// 6. One short atomic commit transaction.
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

func decodeCommitRows(acceptedRecords [][]byte, rejectedRecords [][]byte) ([]previewcommit.CandidateRow, []previewcommit.RejectionRow, error) {
	seenSourceRows := make(map[int64]struct{}, len(acceptedRecords)+len(rejectedRecords))
	claimSourceRow := func(sourceRow int64, previous int64) error {
		if sourceRow <= previous {
			return fmt.Errorf("%w: source rows must strictly increase within a stream", ErrCanonicalRecordInvalid)
		}
		if _, exists := seenSourceRows[sourceRow]; exists {
			return fmt.Errorf("%w: duplicate source row %d", ErrCanonicalRecordInvalid, sourceRow)
		}
		seenSourceRows[sourceRow] = struct{}{}
		return nil
	}

	candidates := make([]previewcommit.CandidateRow, 0, len(acceptedRecords))
	previous := int64(0)
	for index, record := range acceptedRecords {
		candidate, _, err := canonrecord.DecodeRecord(record)
		if err != nil {
			return nil, nil, fmt.Errorf("%w: accepted record %d: %v", ErrCanonicalRecordInvalid, index+1, err)
		}
		if candidate == nil {
			return nil, nil, fmt.Errorf("%w: accepted stream carries a rejection record at %d", ErrCanonicalRecordInvalid, index+1)
		}
		if err := claimSourceRow(candidate.SourceRow, previous); err != nil {
			return nil, nil, err
		}
		previous = candidate.SourceRow
		digest := sha256.Sum256(record)
		candidates = append(candidates, previewcommit.CandidateRow{
			Ordinal:         index + 1,
			SourceRow:       candidate.SourceRow,
			RecordSHA256:    hex.EncodeToString(digest[:]),
			CanonicalRecord: record,
		})
	}

	rejections := make([]previewcommit.RejectionRow, 0, len(rejectedRecords))
	previous = 0
	for index, record := range rejectedRecords {
		_, rejection, err := canonrecord.DecodeRecord(record)
		if err != nil {
			return nil, nil, fmt.Errorf("%w: rejected record %d: %v", ErrCanonicalRecordInvalid, index+1, err)
		}
		if rejection == nil {
			return nil, nil, fmt.Errorf("%w: rejected stream carries a candidate record at %d", ErrCanonicalRecordInvalid, index+1)
		}
		if err := claimSourceRow(rejection.SourceRow, previous); err != nil {
			return nil, nil, err
		}
		previous = rejection.SourceRow
		rejections = append(rejections, previewcommit.RejectionRow{
			Ordinal:    index + 1,
			SourceRow:  rejection.SourceRow,
			IssueCodes: rejection.IssueCodes,
		})
	}
	return candidates, rejections, nil
}
