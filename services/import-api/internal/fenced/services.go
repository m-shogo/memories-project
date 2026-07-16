package fenced

import (
	"context"
	"errors"
	"time"

	applydomain "github.com/m-shogo/memories-project/services/import-api/internal/apply"
	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/preview"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
	"github.com/m-shogo/memories-project/services/import-api/internal/upload"
)

var ErrFenceRequired = errors.New("account epoch fence is required")

type Guard interface {
	Check(context.Context, security.Principal) error
}

// Upload wraps the upload service with deletion-epoch checkpoints at request
// start, after object-storage HEAD, and immediately before consume / scan writes.
type Upload struct {
	Guard Guard
	Inner *upload.Service
}

func (s Upload) Issue(ctx context.Context, principal security.Principal, request upload.IssueRequest) (upload.IssueResponse, error) {
	if s.Guard == nil || s.Inner == nil || s.Inner.Repository == nil {
		return upload.IssueResponse{}, ErrFenceRequired
	}
	if err := s.Guard.Check(ctx, principal); err != nil {
		return upload.IssueResponse{}, err
	}
	inner := *s.Inner
	inner.Repository = uploadRepository{guard: s.Guard, principal: principal, inner: s.Inner.Repository}
	return inner.Issue(ctx, principal, request)
}

func (s Upload) Complete(ctx context.Context, principal security.Principal, authorizationID string) error {
	if s.Guard == nil || s.Inner == nil || s.Inner.Repository == nil || s.Inner.Objects == nil {
		return ErrFenceRequired
	}
	if err := s.Guard.Check(ctx, principal); err != nil {
		return err
	}
	inner := *s.Inner
	inner.Repository = uploadRepository{guard: s.Guard, principal: principal, inner: s.Inner.Repository}
	inner.Objects = guardedObjectStore{guard: s.Guard, principal: principal, inner: s.Inner.Objects}
	return inner.Complete(ctx, principal, authorizationID)
}

type uploadRepository struct {
	guard     Guard
	principal security.Principal
	inner     upload.Repository
}

func (r uploadRepository) GetImportJob(ctx context.Context, tx dbscope.Transaction, id string) (upload.ImportJob, error) {
	return r.inner.GetImportJob(ctx, tx, id)
}
func (r uploadRepository) InsertAuthorization(ctx context.Context, tx dbscope.Transaction, value upload.Authorization) error {
	if err := r.guard.Check(ctx, r.principal); err != nil {
		return err
	}
	return r.inner.InsertAuthorization(ctx, tx, value)
}
func (r uploadRepository) GetAuthorization(ctx context.Context, tx dbscope.Transaction, id string) (upload.Authorization, error) {
	return r.inner.GetAuthorization(ctx, tx, id)
}
func (r uploadRepository) ConsumeIssuedAuthorization(ctx context.Context, tx dbscope.Transaction, id string, at time.Time) (bool, error) {
	if err := r.guard.Check(ctx, r.principal); err != nil {
		return false, err
	}
	return r.inner.ConsumeIssuedAuthorization(ctx, tx, id, at)
}
func (r uploadRepository) RevokeAuthorization(ctx context.Context, tx dbscope.Transaction, id, reason string) error {
	return r.inner.RevokeAuthorization(ctx, tx, id, reason)
}
func (r uploadRepository) EnqueueScan(ctx context.Context, tx dbscope.Transaction, ticket upload.ScanTicket) error {
	if err := r.guard.Check(ctx, r.principal); err != nil {
		return err
	}
	return r.inner.EnqueueScan(ctx, tx, ticket)
}

type guardedObjectStore struct {
	guard     Guard
	principal security.Principal
	inner     upload.ObjectStore
}

func (s guardedObjectStore) HeadObject(ctx context.Context, key string) (upload.ObjectMetadata, error) {
	metadata, err := s.inner.HeadObject(ctx, key)
	if err != nil {
		return upload.ObjectMetadata{}, err
	}
	if err := s.guard.Check(ctx, s.principal); err != nil {
		return upload.ObjectMetadata{}, err
	}
	return metadata, nil
}

// Preview wraps materialization so a stale worker cannot finalize a Preview.
// Candidate rows may be staged inside the transaction, but a failed checkpoint
// before Finalize causes the transaction to roll back.
type Preview struct {
	Guard Guard
	Inner *preview.Materializer
}

func (s Preview) Materialize(ctx context.Context, principal security.Principal, draft preview.Draft, source preview.Source) (preview.Record, error) {
	if s.Guard == nil || s.Inner == nil || s.Inner.Repository == nil {
		return preview.Record{}, ErrFenceRequired
	}
	if err := s.Guard.Check(ctx, principal); err != nil {
		return preview.Record{}, err
	}
	inner := *s.Inner
	inner.Repository = previewRepository{guard: s.Guard, principal: principal, inner: s.Inner.Repository}
	return inner.Materialize(ctx, principal, draft, source)
}

type previewRepository struct {
	guard     Guard
	principal security.Principal
	inner     preview.Repository
}

func (r previewRepository) InsertDraft(ctx context.Context, tx dbscope.Transaction, record preview.Record) error {
	return r.inner.InsertDraft(ctx, tx, record)
}
func (r previewRepository) InsertCandidate(ctx context.Context, tx dbscope.Transaction, previewID string, ordinal int, candidate preview.Candidate, candidateHash string) error {
	return r.inner.InsertCandidate(ctx, tx, previewID, ordinal, candidate, candidateHash)
}
func (r previewRepository) Finalize(ctx context.Context, tx dbscope.Transaction, previewID string, count int, candidatesHash, previewHash string) (bool, error) {
	if err := r.guard.Check(ctx, r.principal); err != nil {
		return false, err
	}
	return r.inner.Finalize(ctx, tx, previewID, count, candidatesHash, previewHash)
}

// Apply wraps the iOS-only Apply service with checkpoints immediately before
// idempotency claim, Memory writes and completion.
type Apply struct {
	Guard Guard
	Inner *applydomain.Service
}

func (s Apply) Execute(ctx context.Context, principal security.Principal, request applydomain.Request) (applydomain.Result, error) {
	if s.Guard == nil || s.Inner == nil || s.Inner.Repository == nil {
		return applydomain.Result{}, ErrFenceRequired
	}
	if err := s.Guard.Check(ctx, principal); err != nil {
		return applydomain.Result{}, err
	}
	inner := *s.Inner
	inner.Repository = applyRepository{guard: s.Guard, principal: principal, inner: s.Inner.Repository}
	return inner.Apply(ctx, principal, request)
}

type applyRepository struct {
	guard     Guard
	principal security.Principal
	inner     applydomain.Repository
}

func (r applyRepository) GetPreview(ctx context.Context, tx dbscope.Transaction, id string) (applydomain.Preview, error) {
	return r.inner.GetPreview(ctx, tx, id)
}
func (r applyRepository) ClaimIdempotency(ctx context.Context, tx dbscope.Transaction, claim applydomain.Claim) (applydomain.ClaimResult, error) {
	if err := r.guard.Check(ctx, r.principal); err != nil {
		return applydomain.ClaimResult{}, err
	}
	return r.inner.ClaimIdempotency(ctx, tx, claim)
}
func (r applyRepository) ApplyMaterializedPreview(ctx context.Context, tx dbscope.Transaction, previewID, previewHash string, policy applydomain.DuplicatePolicy) (applydomain.Counts, error) {
	if err := r.guard.Check(ctx, r.principal); err != nil {
		return applydomain.Counts{}, err
	}
	return r.inner.ApplyMaterializedPreview(ctx, tx, previewID, previewHash, policy)
}
func (r applyRepository) CompleteApply(ctx context.Context, tx dbscope.Transaction, applyID string, counts applydomain.Counts, at time.Time) error {
	if err := r.guard.Check(ctx, r.principal); err != nil {
		return err
	}
	return r.inner.CompleteApply(ctx, tx, applyID, counts, at)
}
