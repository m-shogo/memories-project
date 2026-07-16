package upload

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"regexp"
	"strings"
	"time"

	"github.com/m-shogo/memories-project/backend/internal/security"
)

const DefaultMaxUploadBytes int64 = 256 * 1024 * 1024

var (
	ErrInvalidJobID       = errors.New("invalid import job id")
	ErrInvalidLength      = errors.New("invalid content length")
	ErrInvalidChecksum    = errors.New("invalid sha256 checksum")
	ErrInvalidContentType = errors.New("invalid content type")
	ErrJobUnavailable     = errors.New("import job is unavailable")
)

var (
	sha256Pattern      = regexp.MustCompile(`^[a-f0-9]{64}$`)
	contentTypePattern = regexp.MustCompile(`^[a-z0-9.+-]+/[a-z0-9.+-]+$`)
)

type Clock interface {
	Now() time.Time
}

type systemClock struct{}

func (systemClock) Now() time.Time { return time.Now().UTC() }

type Job struct {
	ID             string
	OwnerAccountID string
	AccountEpoch   int64
	State          string
}

type JobRepository interface {
	FindOwnedJob(ctx context.Context, principal security.Principal, jobID string) (Job, error)
}

type SignRequest struct {
	ObjectKey      string
	ContentLength  int64
	ChecksumSHA256 string
	ContentType    string
	ExpiresAt      time.Time
}

type SignedPUT struct {
	URL             string
	RequiredHeaders map[string]string
}

type Signer interface {
	SignPrivatePUT(ctx context.Context, request SignRequest) (SignedPUT, error)
}

type AuthorizationStore interface {
	CreatePending(ctx context.Context, principal security.Principal, authorization Authorization) error
	MarkIssued(ctx context.Context, principal security.Principal, authorizationID string) error
	MarkFailed(ctx context.Context, principal security.Principal, authorizationID, safeReason string) error
}

type Request struct {
	JobID            string
	ContentLength    int64
	ChecksumSHA256   string
	ContentType      string
	SourceSurface    string
	DisplayFilename string
}

type Authorization struct {
	ID             string
	JobID          string
	OwnerAccountID string
	AccountEpoch   int64
	ObjectKey      string
	ContentLength  int64
	ChecksumSHA256 string
	ContentType    string
	SourceSurface  string
	CreatedAt      time.Time
	ExpiresAt      time.Time
	Status         string
}

type Response struct {
	Authorization Authorization
	SignedPUT      SignedPUT
}

type Service struct {
	jobs           JobRepository
	authorizations AuthorizationStore
	signer         Signer
	clock          Clock
	maxBytes       int64
	ttl            time.Duration
}

func NewService(jobs JobRepository, authorizations AuthorizationStore, signer Signer) (*Service, error) {
	if jobs == nil || authorizations == nil || signer == nil {
		return nil, errors.New("upload service dependencies must not be nil")
	}
	return &Service{
		jobs:           jobs,
		authorizations: authorizations,
		signer:         signer,
		clock:          systemClock{},
		maxBytes:       DefaultMaxUploadBytes,
		ttl:            10 * time.Minute,
	}, nil
}

func (s *Service) Issue(ctx context.Context, principal security.Principal, request Request) (Response, error) {
	if err := principal.Validate(); err != nil {
		return Response{}, fmt.Errorf("validate principal: %w", err)
	}
	if err := s.validateRequest(request); err != nil {
		return Response{}, err
	}

	job, err := s.jobs.FindOwnedJob(ctx, principal, request.JobID)
	if err != nil {
		return Response{}, fmt.Errorf("find owned import job: %w", err)
	}
	if job.OwnerAccountID != principal.AccountID() || job.AccountEpoch != principal.Epoch() {
		return Response{}, ErrJobUnavailable
	}
	if job.State != "awaiting_upload" {
		return Response{}, ErrJobUnavailable
	}

	now := s.clock.Now().UTC()
	authorizationID, err := randomID("upa", 16)
	if err != nil {
		return Response{}, fmt.Errorf("generate authorization id: %w", err)
	}
	objectNonce, err := randomID("obj", 18)
	if err != nil {
		return Response{}, fmt.Errorf("generate object key: %w", err)
	}
	objectKey := fmt.Sprintf("quarantine/%s/%s", request.JobID, objectNonce)
	expiresAt := now.Add(s.ttl)

	authorization := Authorization{
		ID:             authorizationID,
		JobID:          request.JobID,
		OwnerAccountID: principal.AccountID(),
		AccountEpoch:   principal.Epoch(),
		ObjectKey:      objectKey,
		ContentLength:  request.ContentLength,
		ChecksumSHA256: request.ChecksumSHA256,
		ContentType:    request.ContentType,
		SourceSurface:  request.SourceSurface,
		CreatedAt:      now,
		ExpiresAt:      expiresAt,
		Status:         "issuing",
	}

	if err := s.authorizations.CreatePending(ctx, principal, authorization); err != nil {
		return Response{}, fmt.Errorf("persist pending upload authorization: %w", err)
	}

	signed, err := s.signer.SignPrivatePUT(ctx, SignRequest{
		ObjectKey:      objectKey,
		ContentLength:  request.ContentLength,
		ChecksumSHA256: request.ChecksumSHA256,
		ContentType:    request.ContentType,
		ExpiresAt:      expiresAt,
	})
	if err != nil {
		_ = s.authorizations.MarkFailed(ctx, principal, authorizationID, "signing_failed")
		return Response{}, fmt.Errorf("sign private upload: %w", err)
	}
	if strings.TrimSpace(signed.URL) == "" {
		_ = s.authorizations.MarkFailed(ctx, principal, authorizationID, "empty_signed_url")
		return Response{}, errors.New("signer returned empty URL")
	}
	if err := s.authorizations.MarkIssued(ctx, principal, authorizationID); err != nil {
		_ = s.authorizations.MarkFailed(ctx, principal, authorizationID, "activation_failed")
		return Response{}, fmt.Errorf("activate upload authorization: %w", err)
	}

	authorization.Status = "issued"
	return Response{Authorization: authorization, SignedPUT: signed}, nil
}

func (s *Service) validateRequest(request Request) error {
	if len(request.JobID) < 16 || len(request.JobID) > 128 {
		return ErrInvalidJobID
	}
	if request.ContentLength <= 0 || request.ContentLength > s.maxBytes {
		return ErrInvalidLength
	}
	if !sha256Pattern.MatchString(request.ChecksumSHA256) {
		return ErrInvalidChecksum
	}
	if !contentTypePattern.MatchString(request.ContentType) {
		return ErrInvalidContentType
	}
	return nil
}

func randomID(prefix string, byteCount int) (string, error) {
	buffer := make([]byte, byteCount)
	if _, err := rand.Read(buffer); err != nil {
		return "", err
	}
	return prefix + "_" + hex.EncodeToString(buffer), nil
}
