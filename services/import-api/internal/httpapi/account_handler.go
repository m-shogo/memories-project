package httpapi

import (
	"context"
	"errors"
	"net/http"

	"github.com/m-shogo/memories-project/services/import-api/internal/accountdelete"
	"github.com/m-shogo/memories-project/services/import-api/internal/epochguard"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

type AccountDeleteService interface {
	Delete(context.Context, security.Principal) (accountdelete.Receipt, error)
}

type AccountHandler struct {
	Service AccountDeleteService
}

func (h AccountHandler) Register(mux *http.ServeMux) {
	mux.HandleFunc("DELETE /v1/account", h.deleteAccount)
}

// accountDeleteResponse reports the erasure that actually happened. The counts
// are the sweep's own accounting, not an estimate.
type accountDeleteResponse struct {
	Status        string                       `json:"status"`
	DeletionEpoch int64                        `json:"deletionEpoch"`
	Removed       []accountdelete.TableRemoval `json:"removed"`
}

func (h AccountHandler) deleteAccount(writer http.ResponseWriter, request *http.Request) {
	principal, err := security.PrincipalFromContext(request.Context())
	if err != nil {
		writeProblem(writer, http.StatusUnauthorized, "SEC_AUTHENTICATION_REQUIRED")
		return
	}
	if h.Service == nil {
		writeProblem(writer, http.StatusServiceUnavailable, "SEC_SERVICE_UNAVAILABLE")
		return
	}
	// The account erased is the principal's own; the request carries no body
	// and no account identifier at all, so there is nothing to redirect.
	receipt, err := h.Service.Delete(request.Context(), principal)
	if err != nil {
		writeAccountDeleteError(writer, err)
		return
	}
	writeJSON(writer, http.StatusOK, accountDeleteResponse{
		Status:        "deleted",
		DeletionEpoch: receipt.DeletionEpoch,
		Removed:       receipt.Removals,
	})
}

func writeAccountDeleteError(writer http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, accountdelete.ErrAuthorityNotAllowed):
		writeProblem(writer, http.StatusForbidden, "SEC_AUTHORITY_NOT_ALLOWED")
	case errors.Is(err, epochguard.ErrStaleAccountEpoch),
		errors.Is(err, epochguard.ErrAccountDeleting),
		errors.Is(err, epochguard.ErrAccountDeleted),
		errors.Is(err, epochguard.ErrAccountSuspended):
		writeProblem(writer, http.StatusConflict, "SEC_ACCOUNT_FENCED")
	case errors.Is(err, epochguard.ErrAccountUnavailable),
		errors.Is(err, accountdelete.ErrServiceUnavailable):
		writeProblem(writer, http.StatusServiceUnavailable, "SEC_SERVICE_UNAVAILABLE")
	default:
		// Deletion failures are never reported as success. The account stays
		// fenced, so a retry is safe and the client is told to retry.
		writeProblem(writer, http.StatusInternalServerError, "SEC_ACCOUNT_DELETION_FAILED")
	}
}
