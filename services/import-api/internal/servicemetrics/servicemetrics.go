// Package servicemetrics adds the load-critical measurement boundaries on the
// authenticated request handlers (preview read and apply) without changing the
// services themselves. Each decorator wraps a handler-facing service and records
// a bounded, privacy-preserving database-operation metric: it records only a
// fixed operation, outcome and failure-class enum and a duration — never a job
// id, preview id, account id, principal, request body or raw error.
package servicemetrics

import (
	"context"
	"errors"
	"time"

	applydomain "github.com/m-shogo/memories-project/services/import-api/internal/apply"
	"github.com/m-shogo/memories-project/services/import-api/internal/metrics"
	"github.com/m-shogo/memories-project/services/import-api/internal/previewread"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

// previewPort is the preview-read surface the meter wraps (httpapi.PreviewReadService).
type previewPort interface {
	GetJobPreview(context.Context, security.Principal, string, int) (previewread.View, error)
}

// PreviewRead records the preview-read database operation around an inner
// preview service. A nil recorder is safe (metrics methods are no-ops).
type PreviewRead struct {
	Inner    previewPort
	Recorder metrics.Recorder
}

func (m PreviewRead) GetJobPreview(ctx context.Context, principal security.Principal, jobID string, pageSize int) (previewread.View, error) {
	start := time.Now()
	view, err := m.Inner.GetJobPreview(ctx, principal, jobID, pageSize)
	outcome, failure := previewResult(err)
	m.Recorder.RecordDBOperation(metrics.OpDBPreviewRead, outcome, failure, time.Since(start))
	return view, err
}

func previewResult(err error) (metrics.Outcome, metrics.FailureClass) {
	switch {
	case err == nil:
		return metrics.OutcomeSuccess, metrics.FailNone
	case errors.Is(err, previewread.ErrNotFound):
		// A not-found is a normal empty visibility result, not a fault.
		return metrics.OutcomeRejected, metrics.FailNone
	case errors.Is(err, previewread.ErrInvalidRequest):
		return metrics.OutcomeRejected, metrics.FailInvalidRequest
	default:
		return metrics.OutcomeFailure, metrics.FailDatabase
	}
}

// applyPort is the apply surface the meter wraps (httpapi.ApplyService).
type applyPort interface {
	Apply(context.Context, security.Principal, applydomain.Request) (applydomain.Result, error)
}

// Apply records the apply-transaction database operation around an inner apply
// service.
type Apply struct {
	Inner    applyPort
	Recorder metrics.Recorder
}

func (m Apply) Apply(ctx context.Context, principal security.Principal, request applydomain.Request) (applydomain.Result, error) {
	start := time.Now()
	result, err := m.Inner.Apply(ctx, principal, request)
	outcome, failure := applyResult(err)
	m.Recorder.RecordDBOperation(metrics.OpDBApplyTransaction, outcome, failure, time.Since(start))
	return result, err
}

func applyResult(err error) (metrics.Outcome, metrics.FailureClass) {
	switch {
	case err == nil:
		return metrics.OutcomeSuccess, metrics.FailNone
	case errors.Is(err, applydomain.ErrInvalidRequest),
		errors.Is(err, applydomain.ErrDuplicatePolicyUnsupported),
		errors.Is(err, applydomain.ErrAuthorityNotAllowed):
		return metrics.OutcomeRejected, metrics.FailInvalidRequest
	case errors.Is(err, applydomain.ErrPreviewNotFound),
		errors.Is(err, applydomain.ErrPreviewNotReady),
		errors.Is(err, applydomain.ErrPreviewExpired),
		errors.Is(err, applydomain.ErrPreviewHashMismatch),
		errors.Is(err, applydomain.ErrIdempotencyMismatch),
		errors.Is(err, applydomain.ErrApplyInProgress):
		return metrics.OutcomeRejected, metrics.FailNone
	case errors.Is(err, applydomain.ErrApplyAccountingMismatch),
		errors.Is(err, applydomain.ErrApplyClaimInvalid):
		// An accounting or claim invariant broke; that is an integrity failure.
		return metrics.OutcomeFailure, metrics.FailIntegrity
	default:
		return metrics.OutcomeFailure, metrics.FailDatabase
	}
}
