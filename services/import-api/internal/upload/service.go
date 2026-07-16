package upload

import (
	"context"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"errors"
	"fmt"
	"regexp"
	"strings"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

const (
	MaxUploadBytes          int64 = 256 * 1024 * 1024
	DefaultAuthorizationTTL       = 5 * time.Minute
)

var (
	ErrAuthorityNotAllowed         = errors.New("authority may not issue or complete upload")
	ErrInvalidUploadRequest        = errors.New("invalid upload request")
	ErrImportJobNotUploadable      = errors.New("import job is not uploadable")
	ErrUploadAuthorizationNotFound = errors.New("upload authorization not found")
	ErrUploadAuthorizationExpired  = errors.New("upload authorization expired")
	ErrUploadAuthorizationConsumed = errors.New("upload authorization already consumed")
	ErrObjectMetadataMismatch      = errors.New("uploaded object metadata mismatch")
	ErrStorageVersionRequired      = errors.New("object storage version ID required")
)

var sha256HexPattern = regexp.MustCompile(`^[a-f0-9]{64}$`)

type ScopedExecutor interface {
	WithinPrincipal(context.Context, security.Principal, dbscope.Role, func(context.Context, dbscope.Transaction) error) error
}

type ImportJob struct {
	ID             string
	OwnerAccountID string
	AccountEpoch   int64
	Status         string
}

type Authorization struct {
	ID              string
	JobID           string
	OwnerAccountID  string
	AccountEpoch    int64
	ObjectKey       string
	ContentLength   int64
	ChecksumSHA256  string
	ContentType     string
	SourceSurface   string
	DisplayFilename string
	CreatedAt       time.Time
	ExpiresAt       time.Time
	Status          string
}

type ScanTicket struct {
	AuthorizationID string
	JobID           string
	OwnerAccountID  string
	AccountEpoch    int64
	ObjectKey       string
	ObjectVersionID string
	ETag            string
	ContentLength   int64
	ChecksumSHA256  string
	ContentType     string
	CreatedAt       time.Time
}

type Repository interface {
	GetImportJob(context.Context, dbscope.Transaction, string) (ImportJob, error)
	InsertAuthorization(context.Context, dbscope.Transaction, Authorization) error
	GetAuthorization(context.Context, dbscope.Transaction, string) (Authorization, error)
	ConsumeIssuedAuthorization(context.Context, dbscope.Transaction, string, time.Time) (bool, error)
	RevokeAuthorization(context.Context, dbscope.Transaction, string, string) error
	EnqueueScan(context.Context, dbscope.Transaction, ScanTicket) error
}

type PresignRequest struct {
	ObjectKey      string
	ContentLength  int64
	ChecksumSHA256 string
	ContentType    string
	ExpiresAt      time.Time
}

type PresignResult struct {
	URL             string
	RequiredHeaders map[string]string
}

type Signer interface {
	PresignPut(context.Context, PresignRequest) (PresignResult, error)
}

type ObjectMetadata struct {
	ObjectKey      string
	VersionID      string
	ETag           string
	ContentLength  int64
	ChecksumSHA256 string
	ContentType    string
}

type ObjectStore interface {
	HeadObject(context.Context, string) (ObjectMetadata, error)
}

type IDGenerator interface {
	NewID(prefix string) (string, error)
}

type IssueRequest struct {
	JobID           string
	ContentLength   int64
	ChecksumSHA256  string
	ContentType     string
	SourceSurface   string
	DisplayFilename string
}

type IssueResponse struct {
	AuthorizationID string
	ObjectKey       string
	UploadURL       string
	RequiredHeaders map[string]string
	ExpiresAt       time.Time
	CacheControl    string
}

type Service struct {
	Transactions ScopedExecutor
	Repository   Repository
	Signer       Signer
	Objects      ObjectStore
	IDs          IDGenerator
	Now          func() time.Time
	TTL          time.Duration
}

func (s *Service) Issue(ctx context.Context, principal security.Principal, request IssueRequest) (IssueResponse, error) {
	if !canUseUpload(principal.Authority()) {
		return IssueResponse{}, ErrAuthorityNotAllowed
	}
	if err := validateIssueRequest(request); err != nil {
		return IssueResponse{}, err
	}
	if s.Transactions == nil || s.Repository == nil || s.Signer == nil || s.IDs == nil {
		return IssueResponse{}, errors.New("upload service dependencies are incomplete")
	}
	now := s.clock()().UTC()
	ttl := s.TTL
	if ttl == 0 {
		ttl = DefaultAuthorizationTTL
	}
	if ttl <= 0 || ttl > 10*time.Minute {
		return IssueResponse{}, errors.New("invalid upload authorization TTL")
	}
	authorizationID, err := s.IDs.NewID("upl")
	if err != nil {
		return IssueResponse{}, fmt.Errorf("generate upload authorization ID: %w", err)
	}
	objectKey := "quarantine/" + request.JobID + "/" + authorizationID
	expiresAt := now.Add(ttl)

	var response IssueResponse
	err = s.Transactions.WithinPrincipal(ctx, principal, dbscope.RoleAPI, func(ctx context.Context, tx dbscope.Transaction) error {
		job, err := s.Repository.GetImportJob(ctx, tx, request.JobID)
		if err != nil {
			return genericNotFound(err)
		}
		if job.OwnerAccountID != principal.AccountID() || job.AccountEpoch != principal.AccountEpoch() {
			return ErrUploadAuthorizationNotFound
		}
		if job.Status != "created" && job.Status != "awaiting_upload" {
			return ErrImportJobNotUploadable
		}

		authorization := Authorization{
			ID:              authorizationID,
			JobID:           job.ID,
			OwnerAccountID:  principal.AccountID(),
			AccountEpoch:    principal.AccountEpoch(),
			ObjectKey:       objectKey,
			ContentLength:   request.ContentLength,
			ChecksumSHA256:  request.ChecksumSHA256,
			ContentType:     request.ContentType,
			SourceSurface:   request.SourceSurface,
			DisplayFilename: request.DisplayFilename,
			CreatedAt:       now,
			ExpiresAt:       expiresAt,
			Status:          "issued",
		}
		if err := s.Repository.InsertAuthorization(ctx, tx, authorization); err != nil {
			return fmt.Errorf("insert upload authorization: %w", err)
		}
		presigned, err := s.Signer.PresignPut(ctx, PresignRequest{
			ObjectKey:      objectKey,
			ContentLength:  request.ContentLength,
			ChecksumSHA256: request.ChecksumSHA256,
			ContentType:    request.ContentType,
			ExpiresAt:      expiresAt,
		})
		if err != nil {
			return fmt.Errorf("presign quarantine upload: %w", err)
		}
		if presigned.URL == "" {
			return errors.New("presigner returned an empty URL")
		}
		if !requiredHeadersMatch(presigned.RequiredHeaders, request) {
			return errors.New("presigner did not bind required upload headers")
		}
		response = IssueResponse{
			AuthorizationID: authorizationID,
			ObjectKey:       objectKey,
			UploadURL:       presigned.URL,
			RequiredHeaders: cloneHeaders(presigned.RequiredHeaders),
			ExpiresAt:       expiresAt,
			CacheControl:    "no-store",
		}
		return nil
	})
	if err != nil {
		return IssueResponse{}, err
	}
	return response, nil
}

func (s *Service) Complete(ctx context.Context, principal security.Principal, authorizationID string) error {
	if !canUseUpload(principal.Authority()) {
		return ErrAuthorityNotAllowed
	}
	if len(authorizationID) < 16 || len(authorizationID) > 128 {
		return ErrUploadAuthorizationNotFound
	}
	if s.Transactions == nil || s.Repository == nil || s.Objects == nil {
		return errors.New("upload completion dependencies are incomplete")
	}
	now := s.clock()().UTC()

	var snapshot Authorization
	if err := s.Transactions.WithinPrincipal(ctx, principal, dbscope.RoleAPI, func(ctx context.Context, tx dbscope.Transaction) error {
		authorization, err := s.Repository.GetAuthorization(ctx, tx, authorizationID)
		if err != nil {
			return genericNotFound(err)
		}
		if authorization.OwnerAccountID != principal.AccountID() || authorization.AccountEpoch != principal.AccountEpoch() {
			return ErrUploadAuthorizationNotFound
		}
		if authorization.Status == "consumed" {
			return ErrUploadAuthorizationConsumed
		}
		if authorization.Status != "issued" {
			return ErrUploadAuthorizationNotFound
		}
		if !now.Before(authorization.ExpiresAt) {
			return ErrUploadAuthorizationExpired
		}
		snapshot = authorization
		return nil
	}); err != nil {
		return err
	}

	metadata, err := s.Objects.HeadObject(ctx, snapshot.ObjectKey)
	if err != nil {
		return fmt.Errorf("head quarantine object: %w", err)
	}
	if metadata.VersionID == "" {
		return ErrStorageVersionRequired
	}
	if !metadataMatches(snapshot, metadata) {
		if revokeErr := s.revokeMismatch(ctx, principal, snapshot.ID); revokeErr != nil {
			return errors.Join(ErrObjectMetadataMismatch, fmt.Errorf("revoke mismatched upload authorization: %w", revokeErr))
		}
		return ErrObjectMetadataMismatch
	}

	return s.Transactions.WithinPrincipal(ctx, principal, dbscope.RoleAPI, func(ctx context.Context, tx dbscope.Transaction) error {
		current, err := s.Repository.GetAuthorization(ctx, tx, authorizationID)
		if err != nil {
			return genericNotFound(err)
		}
		if current.OwnerAccountID != principal.AccountID() || current.AccountEpoch != principal.AccountEpoch() {
			return ErrUploadAuthorizationNotFound
		}
		if current.Status == "consumed" {
			return ErrUploadAuthorizationConsumed
		}
		if current.Status != "issued" || !now.Before(current.ExpiresAt) {
			return ErrUploadAuthorizationExpired
		}
		if current.ObjectKey != snapshot.ObjectKey || current.ChecksumSHA256 != snapshot.ChecksumSHA256 || current.ContentLength != snapshot.ContentLength || current.ContentType != snapshot.ContentType {
			return ErrObjectMetadataMismatch
		}
		consumed, err := s.Repository.ConsumeIssuedAuthorization(ctx, tx, current.ID, now)
		if err != nil {
			return fmt.Errorf("consume upload authorization: %w", err)
		}
		if !consumed {
			return ErrUploadAuthorizationConsumed
		}
		return s.Repository.EnqueueScan(ctx, tx, ScanTicket{
			AuthorizationID: current.ID,
			JobID:           current.JobID,
			OwnerAccountID:  current.OwnerAccountID,
			AccountEpoch:    current.AccountEpoch,
			ObjectKey:       current.ObjectKey,
			ObjectVersionID: metadata.VersionID,
			ETag:            metadata.ETag,
			ContentLength:   metadata.ContentLength,
			ChecksumSHA256:  metadata.ChecksumSHA256,
			ContentType:     metadata.ContentType,
			CreatedAt:       now,
		})
	})
}

func (s *Service) revokeMismatch(ctx context.Context, principal security.Principal, authorizationID string) error {
	return s.Transactions.WithinPrincipal(ctx, principal, dbscope.RoleAPI, func(ctx context.Context, tx dbscope.Transaction) error {
		return s.Repository.RevokeAuthorization(ctx, tx, authorizationID, "object_metadata_mismatch")
	})
}

func (s *Service) clock() func() time.Time {
	if s.Now != nil {
		return s.Now
	}
	return time.Now
}

func validateIssueRequest(request IssueRequest) error {
	if len(request.JobID) < 16 || len(request.JobID) > 128 {
		return fmt.Errorf("%w: invalid job ID", ErrInvalidUploadRequest)
	}
	if request.ContentLength <= 0 || request.ContentLength > MaxUploadBytes {
		return fmt.Errorf("%w: content length out of range", ErrInvalidUploadRequest)
	}
	if !sha256HexPattern.MatchString(request.ChecksumSHA256) {
		return fmt.Errorf("%w: invalid SHA-256", ErrInvalidUploadRequest)
	}
	if _, ok := allowedContentTypes[request.ContentType]; !ok {
		return fmt.Errorf("%w: content type not allowed", ErrInvalidUploadRequest)
	}
	if _, ok := allowedSourceSurfaces[request.SourceSurface]; !ok {
		return fmt.Errorf("%w: source surface not allowed", ErrInvalidUploadRequest)
	}
	if len(request.DisplayFilename) > 255 || strings.ContainsRune(request.DisplayFilename, '\x00') {
		return fmt.Errorf("%w: unsafe display filename", ErrInvalidUploadRequest)
	}
	return nil
}

var allowedContentTypes = map[string]struct{}{
	"application/zip":           {},
	"application/json":          {},
	"application/octet-stream":  {},
	"text/csv":                  {},
	"text/tab-separated-values": {},
	"text/plain":                {},
}

var allowedSourceSurfaces = map[string]struct{}{
	"ios_files":      {},
	"desktop_portal": {},
}

func canUseUpload(authority security.Authority) bool {
	switch authority {
	case security.AuthorityIOSUser, security.AuthorityIOSDevice, security.AuthorityBrowserPairing:
		return true
	default:
		return false
	}
}

func requiredHeadersMatch(headers map[string]string, request IssueRequest) bool {
	checksumHeader, err := checksumHeaderValue(request.ChecksumSHA256)
	if err != nil {
		return false
	}
	return headers["Content-Type"] == request.ContentType &&
		headers["x-amz-checksum-sha256"] == checksumHeader &&
		headers["Content-Length"] == fmt.Sprintf("%d", request.ContentLength)
}

func checksumHeaderValue(checksumHex string) (string, error) {
	value, err := hex.DecodeString(checksumHex)
	if err != nil || len(value) != sha256.Size {
		return "", ErrInvalidUploadRequest
	}
	return base64.StdEncoding.EncodeToString(value), nil
}

func metadataMatches(authorization Authorization, metadata ObjectMetadata) bool {
	return metadata.ObjectKey == authorization.ObjectKey &&
		metadata.ContentLength == authorization.ContentLength &&
		strings.EqualFold(metadata.ChecksumSHA256, authorization.ChecksumSHA256) &&
		metadata.ContentType == authorization.ContentType
}

func genericNotFound(error) error { return ErrUploadAuthorizationNotFound }

func cloneHeaders(input map[string]string) map[string]string {
	output := make(map[string]string, len(input))
	for key, value := range input {
		output[key] = value
	}
	return output
}
