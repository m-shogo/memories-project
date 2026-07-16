package preview

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"sort"
	"strings"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

const MaxPreviewRows = 100_000

var (
	ErrInvalidRowEvent  = errors.New("invalid preview row event")
	ErrInvalidRejection = errors.New("invalid preview rejection")
	ErrTooManyRows      = errors.New("preview row limit exceeded")
)

// Rejection contains only safe structural information. Raw row values,
// filenames, URLs, and user text must never be copied into this record.
type Rejection struct {
	SourceRow int
	Issues    []string
}

// RowEvent represents exactly one source-row decision.
type RowEvent struct {
	Candidate *Candidate
	Rejection *Rejection
}

// RowEventSource is a synchronous pull source. Implementations must not spawn
// hidden goroutines or continue after a terminal parsing failure.
type RowEventSource interface {
	NextEvent(context.Context) (RowEvent, error)
}

// AtomicRepository persists the Preview, accepted candidates, and safe
// rejection report in the same database transaction.
type AtomicRepository interface {
	InsertDraft(context.Context, dbscope.Transaction, Record) error
	InsertCandidate(context.Context, dbscope.Transaction, string, int, Candidate, string) error
	InsertRejection(context.Context, dbscope.Transaction, string, int, Rejection, string) error
	FinalizeWithReport(context.Context, dbscope.Transaction, string, int, int, string, string, string) (bool, error)
}

type AtomicRecord struct {
	Record
	RejectedCount    int
	RejectionsSHA256 string
}

type AtomicMaterializer struct {
	Transactions ScopedExecutor
	Repository   AtomicRepository
	IDs          IDGenerator
	Now          func() time.Time
	TTL          time.Duration
}

func (m *AtomicMaterializer) Materialize(ctx context.Context, principal security.Principal, draft Draft, source RowEventSource) (AtomicRecord, error) {
	if principal.Authority() != security.AuthorityWorkerLease {
		return AtomicRecord{}, ErrAuthorityNotAllowed
	}
	if m.Transactions == nil || m.Repository == nil || m.IDs == nil || source == nil {
		return AtomicRecord{}, errors.New("atomic preview materializer dependencies are incomplete")
	}
	if err := validateDraft(draft); err != nil {
		return AtomicRecord{}, err
	}

	now := time.Now().UTC()
	if m.Now != nil {
		now = m.Now().UTC()
	}
	ttl := m.TTL
	if ttl == 0 {
		ttl = DefaultPreviewTTL
	}
	if ttl < time.Hour || ttl > 7*24*time.Hour {
		return AtomicRecord{}, fmt.Errorf("%w: preview TTL outside approved range", ErrInvalidDraft)
	}
	if draft.ExpiresAt.IsZero() {
		draft.ExpiresAt = now.Add(ttl)
	}
	if !draft.ExpiresAt.After(now) || draft.ExpiresAt.After(now.Add(7*24*time.Hour)) {
		return AtomicRecord{}, fmt.Errorf("%w: invalid preview expiry", ErrInvalidDraft)
	}

	previewID, err := m.IDs.NewID("prv")
	if err != nil {
		return AtomicRecord{}, fmt.Errorf("generate preview ID: %w", err)
	}
	record := Record{
		ID:             previewID,
		JobID:          draft.JobID,
		OwnerAccountID: principal.AccountID(),
		AccountEpoch:   principal.AccountEpoch(),
		Source:         draft.Source,
		Adapter:        draft.Adapter,
		OptionsSHA256:  draft.OptionsSHA256,
		Status:         "building",
		CreatedAt:      now,
		ExpiresAt:      draft.ExpiresAt,
	}
	result := AtomicRecord{Record: record}

	err = m.Transactions.WithinPrincipal(ctx, principal, dbscope.RoleWorker, func(ctx context.Context, tx dbscope.Transaction) error {
		if err := m.Repository.InsertDraft(ctx, tx, record); err != nil {
			return fmt.Errorf("insert preview draft: %w", err)
		}

		candidateHasher := sha256.New()
		rejectionHasher := sha256.New()
		acceptedCount := 0
		rejectedCount := 0
		rowCount := 0
		lastSourceRow := 0

		for {
			event, err := source.NextEvent(ctx)
			if errors.Is(err, ErrEndOfCandidates) {
				break
			}
			if err != nil {
				return fmt.Errorf("read preview row event: %w", err)
			}
			rowCount++
			if rowCount > MaxPreviewRows {
				return ErrTooManyRows
			}
			if (event.Candidate == nil) == (event.Rejection == nil) {
				return ErrInvalidRowEvent
			}

			sourceRow := 0
			if event.Candidate != nil {
				sourceRow = event.Candidate.SourceRow
			} else {
				sourceRow = event.Rejection.SourceRow
			}
			if sourceRow <= lastSourceRow {
				return ErrInvalidRowEvent
			}
			lastSourceRow = sourceRow

			if event.Candidate != nil {
				acceptedCount++
				candidate := *event.Candidate
				issues, err := normalizeImportIssues(candidate.Issues, ErrInvalidCandidate)
				if err != nil {
					return err
				}
				candidate.Issues = issues
				normalized, canonical, candidateHash, err := canonicalCandidate(candidate)
				if err != nil {
					return err
				}
				writeLengthPrefixed(candidateHasher, canonical)
				if err := m.Repository.InsertCandidate(ctx, tx, previewID, acceptedCount, normalized, candidateHash); err != nil {
					return fmt.Errorf("insert preview candidate: %w", err)
				}
				continue
			}

			rejectedCount++
			normalized, canonical, rejectionHash, err := canonicalRejection(*event.Rejection)
			if err != nil {
				return err
			}
			writeLengthPrefixed(rejectionHasher, canonical)
			if err := m.Repository.InsertRejection(ctx, tx, previewID, rejectedCount, normalized, rejectionHash); err != nil {
				return fmt.Errorf("insert preview rejection: %w", err)
			}
		}

		if acceptedCount == 0 {
			return fmt.Errorf("%w: no accepted candidates", ErrInvalidDraft)
		}
		candidatesHash := hex.EncodeToString(candidateHasher.Sum(nil))
		rejectionsHash := hex.EncodeToString(rejectionHasher.Sum(nil))
		previewHash := computeAtomicPreviewHash(record, candidatesHash, rejectionsHash, acceptedCount, rejectedCount)
		finalized, err := m.Repository.FinalizeWithReport(ctx, tx, previewID, acceptedCount, rejectedCount, candidatesHash, rejectionsHash, previewHash)
		if err != nil {
			return fmt.Errorf("finalize preview with report: %w", err)
		}
		if !finalized {
			return ErrPreviewNotCreated
		}

		result.Record.CandidateCount = acceptedCount
		result.Record.CandidatesSHA256 = candidatesHash
		result.Record.PreviewSHA256 = previewHash
		result.Record.Status = "ready"
		result.RejectedCount = rejectedCount
		result.RejectionsSHA256 = rejectionsHash
		return nil
	})
	if err != nil {
		return AtomicRecord{}, err
	}
	return result, nil
}

func canonicalRejection(rejection Rejection) (Rejection, []byte, string, error) {
	if rejection.SourceRow < 1 {
		return Rejection{}, nil, "", ErrInvalidRejection
	}
	issues, err := normalizeImportIssues(rejection.Issues, ErrInvalidRejection)
	if err != nil {
		return Rejection{}, nil, "", err
	}
	normalized := Rejection{SourceRow: rejection.SourceRow, Issues: issues}
	var builder strings.Builder
	builder.WriteString(fmt.Sprintf("%d|%d|", normalized.SourceRow, len(issues)))
	for _, issue := range issues {
		builder.WriteString(fmt.Sprintf("%d:", len(issue)))
		builder.WriteString(issue)
	}
	canonical := []byte(builder.String())
	digest := sha256.Sum256(canonical)
	return normalized, canonical, hex.EncodeToString(digest[:]), nil
}

func normalizeImportIssues(values []string, invalid error) ([]string, error) {
	if len(values) == 0 || len(values) > 32 {
		return nil, invalid
	}
	issues := append([]string(nil), values...)
	sort.Strings(issues)
	for index, issue := range issues {
		if len(issue) > 128 || !strings.HasPrefix(issue, "IMPORT_") {
			return nil, invalid
		}
		for _, character := range issue {
			if (character >= 'A' && character <= 'Z') ||
				(character >= '0' && character <= '9') || character == '_' {
				continue
			}
			return nil, invalid
		}
		if index > 0 && issues[index-1] == issue {
			return nil, invalid
		}
	}
	return issues, nil
}

func computeAtomicPreviewHash(record Record, candidatesHash, rejectionsHash string, acceptedCount, rejectedCount int) string {
	hasher := sha256.New()
	for _, value := range []string{
		"memory-os-preview-v2",
		record.JobID,
		record.OwnerAccountID,
		fmt.Sprintf("%d", record.AccountEpoch),
		record.Source.ObjectKey,
		record.Source.ObjectVersionID,
		record.Source.ChecksumSHA256,
		record.Adapter.AdapterID,
		record.Adapter.AdapterVersion,
		record.Adapter.ArtifactSHA256,
		record.OptionsSHA256,
		candidatesHash,
		fmt.Sprintf("%d", acceptedCount),
		rejectionsHash,
		fmt.Sprintf("%d", rejectedCount),
	} {
		writeLengthPrefixed(hasher, []byte(value))
	}
	return hex.EncodeToString(hasher.Sum(nil))
}
