package httpapi

import (
	"context"
	"errors"
	"net/http"

	applydomain "github.com/m-shogo/memories-project/services/import-api/internal/apply"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

type ApplyService interface {
	Apply(context.Context, security.Principal, applydomain.Request) (applydomain.Result, error)
}

type ApplyHandler struct {
	Service     ApplyService
	MaxJSONBody int64
}

func (h ApplyHandler) Register(mux *http.ServeMux) {
	mux.HandleFunc("POST /v1/previews/{previewID}/apply", h.apply)
}

type applyPreviewRequest struct {
	PreviewSHA256   string                      `json:"previewSha256"`
	IdempotencyKey  string                      `json:"idempotencyKey"`
	DuplicatePolicy applydomain.DuplicatePolicy `json:"duplicatePolicy"`
}

type applyPreviewResponse struct {
	ApplyID  string             `json:"applyId"`
	Status   string             `json:"status"`
	Counts   applydomain.Counts `json:"counts"`
	Replayed bool               `json:"replayed"`
}

func (h ApplyHandler) apply(writer http.ResponseWriter, request *http.Request) {
	principal, err := security.PrincipalFromContext(request.Context())
	if err != nil {
		writeProblem(writer, http.StatusUnauthorized, "SEC_AUTHENTICATION_REQUIRED")
		return
	}
	if h.Service == nil {
		writeProblem(writer, http.StatusServiceUnavailable, "SEC_SERVICE_UNAVAILABLE")
		return
	}
	var body applyPreviewRequest
	if err := decodeStrictJSON(writer, request, h.bodyLimit(), &body); err != nil {
		writeProblem(writer, http.StatusBadRequest, "SEC_APPLY_REQUEST_INVALID")
		return
	}
	result, err := h.Service.Apply(request.Context(), principal, applydomain.Request{
		PreviewID:       request.PathValue("previewID"),
		PreviewSHA256:   body.PreviewSHA256,
		IdempotencyKey:  body.IdempotencyKey,
		DuplicatePolicy: body.DuplicatePolicy,
	})
	if err != nil {
		writeApplyError(writer, err)
		return
	}
	writeJSON(writer, http.StatusOK, applyPreviewResponse{
		ApplyID:  result.ApplyID,
		Status:   result.Status,
		Counts:   result.Counts,
		Replayed: result.Replayed,
	})
}

func (h ApplyHandler) bodyLimit() int64 {
	if h.MaxJSONBody <= 0 || h.MaxJSONBody > 1024*1024 {
		return defaultMaxJSONBody
	}
	return h.MaxJSONBody
}

func writeApplyError(writer http.ResponseWriter, err error) {
	switch {
	case isFencedSessionError(err):
		writeProblem(writer, http.StatusUnauthorized, "SEC_AUTHENTICATION_REQUIRED")
	case errors.Is(err, applydomain.ErrDuplicatePolicyUnsupported):
		// Distinct from SEC_APPLY_REQUEST_INVALID on purpose: the value is
		// well-formed and was previously accepted, so the client is told the
		// policy is unsupported rather than that it sent nonsense. Nothing was
		// written, and the request must not be retried as a different policy
		// without the caller deciding to.
		writeProblem(writer, http.StatusBadRequest, "SEC_APPLY_DUPLICATE_POLICY_UNSUPPORTED")
	case errors.Is(err, applydomain.ErrInvalidRequest):
		writeProblem(writer, http.StatusBadRequest, "SEC_APPLY_REQUEST_INVALID")
	case errors.Is(err, applydomain.ErrAuthorityNotAllowed),
		errors.Is(err, applydomain.ErrPreviewNotFound):
		writeProblem(writer, http.StatusNotFound, "SEC_RESOURCE_NOT_FOUND")
	case errors.Is(err, applydomain.ErrPreviewNotReady),
		errors.Is(err, applydomain.ErrPreviewExpired),
		errors.Is(err, applydomain.ErrPreviewHashMismatch),
		errors.Is(err, applydomain.ErrIdempotencyMismatch),
		errors.Is(err, applydomain.ErrApplyInProgress),
		errors.Is(err, applydomain.ErrApplyAccountingMismatch),
		errors.Is(err, applydomain.ErrApplyClaimInvalid):
		writeProblem(writer, http.StatusConflict, "SEC_APPLY_STATE_CONFLICT")
	default:
		writeProblem(writer, http.StatusInternalServerError, "SEC_INTERNAL_ERROR")
	}
}
