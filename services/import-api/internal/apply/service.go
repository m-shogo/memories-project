package apply

import (
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"errors"
	"fmt"
	"hash"
	"strings"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

var (
	ErrAuthorityNotAllowed     = errors.New("authority may not apply preview")
	ErrInvalidRequest          = errors.New("invalid apply request")
	ErrPreviewNotFound         = errors.New("preview not found")
	ErrPreviewNotReady         = errors.New("preview is not ready")
	ErrPreviewExpired          = errors.New("preview expired")
	ErrPreviewHashMismatch     = errors.New("preview hash mismatch")
	ErrIdempotencyMismatch     = errors.New("idempotency key reused for a different request")
	ErrApplyInProgress         = errors.New("apply request is already in progress")
	ErrApplyAccountingMismatch = errors.New("apply result does not account for every preview candidate")
	ErrApplyClaimInvalid       = errors.New("invalid apply claim result")
	// ErrDuplicatePolicyUnsupported is deliberately distinct from
	// ErrInvalidRequest: update_safe_fields is a value this API used to accept,
	// so a client that sends it deserves to be told it is no longer supported
	// rather than that its request was malformed.
	ErrDuplicatePolicyUnsupported = errors.New("duplicate policy is not supported")
)

type ScopedExecutor interface {
	WithinPrincipal(context.Context, security.Principal, dbscope.Role, func(context.Context, dbscope.Transaction) error) error
}

type IDGenerator interface {
	NewID(prefix string) (string, error)
}

type DuplicatePolicy string

const (
	DuplicateSkipExisting DuplicatePolicy = "skip_existing"
	DuplicateKeepBoth     DuplicatePolicy = "keep_both"

	// DuplicateUpdateSafe is recognised and refused. It is kept as a named
	// constant rather than deleted so the refusal is explicit everywhere the
	// value can still arrive — from an older client, a stored claim row, or the
	// migration 005 CHECK constraint that still lists it.
	//
	// Its implementation overwrote memory_item.canonical_record in place and
	// repointed source_preview_id, destroying both the earlier content and the
	// record of where it came from. Append-only supersession is the correct
	// replacement and is future work; until it exists the path is closed rather
	// than left open, because a caller cannot tell a destructive update from a
	// safe one by looking at the response.
	//
	// It is never silently mapped onto skip_existing or keep_both: a client
	// that asked to update must not be told its update succeeded.
	DuplicateUpdateSafe DuplicatePolicy = "update_safe_fields"
)

type Request struct {
	PreviewID       string
	PreviewSHA256   string
	IdempotencyKey  string
	DuplicatePolicy DuplicatePolicy
}

type Preview struct {
	ID             string
	OwnerAccountID string
	AccountEpoch   int64
	PreviewSHA256  string
	CandidateCount int
	Status         string
	ExpiresAt      time.Time
}

type Counts struct {
	Created int
	Updated int
	Skipped int
}

type Result struct {
	ApplyID  string
	Status   string
	Counts   Counts
	Replayed bool
}

type Claim struct {
	ApplyID         string
	OwnerAccountID  string
	AccountEpoch    int64
	PreviewID       string
	PreviewSHA256   string
	IdempotencyKey  string
	RequestSHA256   string
	DuplicatePolicy DuplicatePolicy
	CreatedAt       time.Time
}

type ClaimDisposition string

const (
	ClaimNew        ClaimDisposition = "new"
	ClaimReplay     ClaimDisposition = "replay"
	ClaimInProgress ClaimDisposition = "in_progress"
	ClaimConflict   ClaimDisposition = "conflict"
)

type ClaimResult struct {
	Disposition   ClaimDisposition
	ApplyID       string
	RequestSHA256 string
	Existing      Result
}

type Repository interface {
	GetPreview(context.Context, dbscope.Transaction, string) (Preview, error)
	ClaimIdempotency(context.Context, dbscope.Transaction, Claim) (ClaimResult, error)
	ApplyMaterializedPreview(context.Context, dbscope.Transaction, string, string, DuplicatePolicy) (Counts, error)
	CompleteApply(context.Context, dbscope.Transaction, string, Counts, time.Time) error
}

type Service struct {
	Transactions ScopedExecutor
	Repository   Repository
	IDs          IDGenerator
	Now          func() time.Time
}

func (s *Service) Apply(ctx context.Context, principal security.Principal, request Request) (Result, error) {
	if principal.Authority() != security.AuthorityIOSUser {
		return Result{}, ErrAuthorityNotAllowed
	}
	if err := validateRequest(request); err != nil {
		return Result{}, err
	}
	if s.Transactions == nil || s.Repository == nil || s.IDs == nil {
		return Result{}, errors.New("apply service dependencies are incomplete")
	}
	now := time.Now().UTC()
	if s.Now != nil {
		now = s.Now().UTC()
	}
	applyID, err := s.IDs.NewID("apl")
	if err != nil {
		return Result{}, fmt.Errorf("generate apply ID: %w", err)
	}
	requestHash := computeRequestHash(principal, request)
	var result Result

	err = s.Transactions.WithinPrincipal(ctx, principal, dbscope.RoleAPI, func(ctx context.Context, tx dbscope.Transaction) error {
		preview, err := s.Repository.GetPreview(ctx, tx, request.PreviewID)
		if err != nil {
			return ErrPreviewNotFound
		}
		if preview.OwnerAccountID != principal.AccountID() || preview.AccountEpoch != principal.AccountEpoch() {
			return ErrPreviewNotFound
		}
		if preview.Status != "ready" {
			return ErrPreviewNotReady
		}
		if !now.Before(preview.ExpiresAt) {
			return ErrPreviewExpired
		}
		if preview.PreviewSHA256 != request.PreviewSHA256 {
			return ErrPreviewHashMismatch
		}
		if preview.CandidateCount < 1 || preview.CandidateCount > 100_000 {
			return ErrPreviewNotReady
		}

		claim := Claim{
			ApplyID:         applyID,
			OwnerAccountID:  principal.AccountID(),
			AccountEpoch:    principal.AccountEpoch(),
			PreviewID:       request.PreviewID,
			PreviewSHA256:   request.PreviewSHA256,
			IdempotencyKey:  request.IdempotencyKey,
			RequestSHA256:   requestHash,
			DuplicatePolicy: request.DuplicatePolicy,
			CreatedAt:       now,
		}
		claimResult, err := s.Repository.ClaimIdempotency(ctx, tx, claim)
		if err != nil {
			return fmt.Errorf("claim apply idempotency: %w", err)
		}
		switch claimResult.Disposition {
		case ClaimReplay:
			if claimResult.RequestSHA256 != requestHash || claimResult.Existing.ApplyID == "" || claimResult.Existing.Status != "applied" {
				return ErrIdempotencyMismatch
			}
			result = claimResult.Existing
			result.Replayed = true
			return nil
		case ClaimInProgress:
			if claimResult.RequestSHA256 != requestHash {
				return ErrIdempotencyMismatch
			}
			return ErrApplyInProgress
		case ClaimConflict:
			return ErrIdempotencyMismatch
		case ClaimNew:
			if claimResult.ApplyID != "" && claimResult.ApplyID != applyID {
				return ErrApplyClaimInvalid
			}
		default:
			return ErrApplyClaimInvalid
		}

		counts, err := s.Repository.ApplyMaterializedPreview(ctx, tx, preview.ID, preview.PreviewSHA256, request.DuplicatePolicy)
		if err != nil {
			return fmt.Errorf("apply materialized preview: %w", err)
		}
		if counts.Created < 0 || counts.Updated < 0 || counts.Skipped < 0 || counts.Created+counts.Updated+counts.Skipped != preview.CandidateCount {
			return ErrApplyAccountingMismatch
		}
		if err := s.Repository.CompleteApply(ctx, tx, applyID, counts, now); err != nil {
			return fmt.Errorf("complete apply: %w", err)
		}
		result = Result{ApplyID: applyID, Status: "applied", Counts: counts}
		return nil
	})
	if err != nil {
		return Result{}, err
	}
	return result, nil
}

func validateRequest(request Request) error {
	if !validOpaqueID(request.PreviewID) || !validSHA256(request.PreviewSHA256) || !validOpaqueID(request.IdempotencyKey) {
		return ErrInvalidRequest
	}
	switch request.DuplicatePolicy {
	case DuplicateSkipExisting, DuplicateKeepBoth:
		return nil
	case DuplicateUpdateSafe:
		// Refused here, before any transaction is opened, so no idempotency
		// claim row is written and no candidate is ever read for this request.
		return ErrDuplicatePolicyUnsupported
	default:
		return ErrInvalidRequest
	}
}

func computeRequestHash(principal security.Principal, request Request) string {
	hasher := sha256.New()
	for _, value := range []string{
		"memory-os-apply-v1",
		principal.AccountID(),
		fmt.Sprintf("%d", principal.AccountEpoch()),
		request.PreviewID,
		request.PreviewSHA256,
		string(request.DuplicatePolicy),
	} {
		writeLengthPrefixed(hasher, []byte(value))
	}
	return hex.EncodeToString(hasher.Sum(nil))
}

func writeLengthPrefixed(target hash.Hash, value []byte) {
	var size [8]byte
	binary.BigEndian.PutUint64(size[:], uint64(len(value)))
	_, _ = target.Write(size[:])
	_, _ = target.Write(value)
}

func validSHA256(value string) bool {
	if len(value) != sha256.Size*2 || strings.ToLower(value) != value {
		return false
	}
	_, err := hex.DecodeString(value)
	return err == nil
}

func validOpaqueID(value string) bool {
	if len(value) < 16 || len(value) > 128 {
		return false
	}
	for _, character := range value {
		if (character >= 'a' && character <= 'z') ||
			(character >= 'A' && character <= 'Z') ||
			(character >= '0' && character <= '9') ||
			strings.ContainsRune("._:-", character) {
			continue
		}
		return false
	}
	return true
}
