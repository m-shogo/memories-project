package preview

import (
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"errors"
	"fmt"
	"hash"
	"net/url"
	"sort"
	"strings"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

const (
	DefaultPreviewTTL = 24 * time.Hour
	MaxCandidates     = 100_000
	MaxCandidateText  = 1024 * 1024
)

var (
	ErrAuthorityNotAllowed = errors.New("authority may not materialize preview")
	ErrInvalidDraft        = errors.New("invalid preview draft")
	ErrInvalidCandidate    = errors.New("invalid preview candidate")
	ErrTooManyCandidates   = errors.New("preview candidate limit exceeded")
	ErrPreviewNotCreated   = errors.New("preview was not created")
)

type ScopedExecutor interface {
	WithinPrincipal(context.Context, security.Principal, dbscope.Role, func(context.Context, dbscope.Transaction) error) error
}

type IDGenerator interface {
	NewID(prefix string) (string, error)
}

type Candidate struct {
	SourceRow   int
	Title       string
	OccurredAt  *time.Time
	URL         string
	Text        string
	Fingerprint string
	Issues      []string
}

type SourceBinding struct {
	ObjectKey       string
	ObjectVersionID string
	ChecksumSHA256  string
}

type AdapterBinding struct {
	AdapterID      string
	AdapterVersion string
	ArtifactSHA256 string
}

type Draft struct {
	JobID         string
	Source        SourceBinding
	Adapter       AdapterBinding
	OptionsSHA256 string
	ExpiresAt     time.Time
}

type Record struct {
	ID               string
	JobID            string
	OwnerAccountID   string
	AccountEpoch     int64
	Source           SourceBinding
	Adapter          AdapterBinding
	OptionsSHA256    string
	CandidatesSHA256 string
	PreviewSHA256    string
	CandidateCount   int
	Status           string
	CreatedAt        time.Time
	ExpiresAt        time.Time
}

type Repository interface {
	InsertDraft(context.Context, dbscope.Transaction, Record) error
	InsertCandidate(context.Context, dbscope.Transaction, string, int, Candidate, string) error
	Finalize(context.Context, dbscope.Transaction, string, int, string, string) (bool, error)
}

type Source interface {
	Next(context.Context) (Candidate, error)
}

var ErrEndOfCandidates = errors.New("end of candidates")

type Materializer struct {
	Transactions ScopedExecutor
	Repository   Repository
	IDs          IDGenerator
	Now          func() time.Time
	TTL          time.Duration
}

func (m *Materializer) Materialize(ctx context.Context, principal security.Principal, draft Draft, source Source) (Record, error) {
	if principal.Authority() != security.AuthorityWorkerLease {
		return Record{}, ErrAuthorityNotAllowed
	}
	if m.Transactions == nil || m.Repository == nil || m.IDs == nil || source == nil {
		return Record{}, errors.New("preview materializer dependencies are incomplete")
	}
	if err := validateDraft(draft); err != nil {
		return Record{}, err
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
		return Record{}, fmt.Errorf("%w: preview TTL outside approved range", ErrInvalidDraft)
	}
	if draft.ExpiresAt.IsZero() {
		draft.ExpiresAt = now.Add(ttl)
	}
	if !draft.ExpiresAt.After(now) || draft.ExpiresAt.After(now.Add(7*24*time.Hour)) {
		return Record{}, fmt.Errorf("%w: invalid preview expiry", ErrInvalidDraft)
	}
	previewID, err := m.IDs.NewID("prv")
	if err != nil {
		return Record{}, fmt.Errorf("generate preview ID: %w", err)
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

	err = m.Transactions.WithinPrincipal(ctx, principal, dbscope.RoleWorker, func(ctx context.Context, tx dbscope.Transaction) error {
		if err := m.Repository.InsertDraft(ctx, tx, record); err != nil {
			return fmt.Errorf("insert preview draft: %w", err)
		}
		candidateHasher := sha256.New()
		count := 0
		for {
			candidate, err := source.Next(ctx)
			if errors.Is(err, ErrEndOfCandidates) {
				break
			}
			if err != nil {
				return fmt.Errorf("read preview candidate: %w", err)
			}
			count++
			if count > MaxCandidates {
				return ErrTooManyCandidates
			}
			normalizedCandidate, canonical, candidateHash, err := canonicalCandidate(candidate)
			if err != nil {
				return err
			}
			writeLengthPrefixed(candidateHasher, canonical)
			if err := m.Repository.InsertCandidate(ctx, tx, previewID, count, normalizedCandidate, candidateHash); err != nil {
				return fmt.Errorf("insert preview candidate: %w", err)
			}
		}
		if count == 0 {
			return fmt.Errorf("%w: no accepted candidates", ErrInvalidDraft)
		}
		candidatesHash := hex.EncodeToString(candidateHasher.Sum(nil))
		previewHash := computePreviewHash(record, candidatesHash, count)
		finalized, err := m.Repository.Finalize(ctx, tx, previewID, count, candidatesHash, previewHash)
		if err != nil {
			return fmt.Errorf("finalize preview: %w", err)
		}
		if !finalized {
			return ErrPreviewNotCreated
		}
		record.CandidateCount = count
		record.CandidatesSHA256 = candidatesHash
		record.PreviewSHA256 = previewHash
		record.Status = "ready"
		return nil
	})
	if err != nil {
		return Record{}, err
	}
	return record, nil
}

func validateDraft(draft Draft) error {
	if !validOpaqueID(draft.JobID) || draft.Source.ObjectKey == "" || draft.Source.ObjectVersionID == "" ||
		!validSHA256(draft.Source.ChecksumSHA256) || draft.Adapter.AdapterID == "" || draft.Adapter.AdapterVersion == "" ||
		!validSHA256(draft.Adapter.ArtifactSHA256) || !validSHA256(draft.OptionsSHA256) {
		return ErrInvalidDraft
	}
	if !strings.HasPrefix(draft.Source.ObjectKey, "quarantine/") || len(draft.Source.ObjectKey) > 256 || len(draft.Source.ObjectVersionID) > 256 {
		return ErrInvalidDraft
	}
	return nil
}

func canonicalCandidate(candidate Candidate) (Candidate, []byte, string, error) {
	candidate.Title = strings.TrimSpace(candidate.Title)
	candidate.URL = strings.TrimSpace(candidate.URL)
	candidate.Text = strings.TrimSpace(candidate.Text)
	if candidate.SourceRow < 1 || candidate.Title == "" || len(candidate.Title) > 4096 || len(candidate.Text) > MaxCandidateText || !validSHA256(candidate.Fingerprint) {
		return Candidate{}, nil, "", ErrInvalidCandidate
	}
	if candidate.URL != "" {
		parsed, err := url.Parse(candidate.URL)
		if err != nil || (parsed.Scheme != "http" && parsed.Scheme != "https") || parsed.Host == "" || parsed.User != nil || len(candidate.URL) > 4096 {
			return Candidate{}, nil, "", ErrInvalidCandidate
		}
		candidate.URL = parsed.String()
	}
	occurredAt := ""
	if candidate.OccurredAt != nil {
		value := candidate.OccurredAt.UTC()
		occurredAt = value.Format(time.RFC3339Nano)
		candidate.OccurredAt = &value
	}
	issues := append([]string(nil), candidate.Issues...)
	sort.Strings(issues)
	for _, issue := range issues {
		if issue == "" || len(issue) > 128 || !strings.HasPrefix(issue, "IMPORT_") {
			return Candidate{}, nil, "", ErrInvalidCandidate
		}
	}
	fields := []string{
		fmt.Sprintf("%d", candidate.SourceRow),
		candidate.Title,
		occurredAt,
		candidate.URL,
		candidate.Text,
		candidate.Fingerprint,
		strings.Join(issues, "\x1e"),
	}
	var builder strings.Builder
	for _, field := range fields {
		builder.WriteString(fmt.Sprintf("%d:", len(field)))
		builder.WriteString(field)
	}
	canonical := []byte(builder.String())
	digest := sha256.Sum256(canonical)
	candidate.Issues = issues
	return candidate, canonical, hex.EncodeToString(digest[:]), nil
}

func computePreviewHash(record Record, candidatesHash string, count int) string {
	hasher := sha256.New()
	for _, value := range []string{
		"memory-os-preview-v1",
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
		fmt.Sprintf("%d", count),
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
	if len(value) != sha256.Size*2 {
		return false
	}
	_, err := hex.DecodeString(value)
	return err == nil && strings.ToLower(value) == value
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
