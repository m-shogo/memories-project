package httpapi

import (
	"context"
	"errors"
	"net/http"
	"strconv"

	"github.com/m-shogo/memories-project/services/import-api/internal/previewread"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

type PreviewReadService interface {
	GetJobPreview(context.Context, security.Principal, string, int) (previewread.View, error)
}

type PreviewHandler struct {
	Service PreviewReadService
}

func (h PreviewHandler) Register(mux *http.ServeMux) {
	mux.HandleFunc("GET /v1/import-jobs/{jobID}/preview", h.get)
}

func (h PreviewHandler) get(writer http.ResponseWriter, request *http.Request) {
	principal, err := security.PrincipalFromContext(request.Context())
	if err != nil {
		writeProblem(writer, http.StatusUnauthorized, "SEC_AUTHENTICATION_REQUIRED")
		return
	}
	if h.Service == nil {
		writeProblem(writer, http.StatusServiceUnavailable, "SEC_SERVICE_UNAVAILABLE")
		return
	}
	limit := 0
	if raw := request.URL.Query().Get("limit"); raw != "" {
		parsed, err := strconv.Atoi(raw)
		if err != nil {
			writeProblem(writer, http.StatusBadRequest, "SEC_PREVIEW_REQUEST_INVALID")
			return
		}
		limit = parsed
	}
	view, err := h.Service.GetJobPreview(request.Context(), principal, request.PathValue("jobID"), limit)
	switch {
	case err == nil:
		writeJSON(writer, http.StatusOK, view)
	case errors.Is(err, previewread.ErrInvalidRequest):
		writeProblem(writer, http.StatusBadRequest, "SEC_PREVIEW_REQUEST_INVALID")
	case errors.Is(err, previewread.ErrNotFound):
		writeProblem(writer, http.StatusNotFound, "SEC_RESOURCE_NOT_FOUND")
	default:
		writeProblem(writer, http.StatusInternalServerError, "SEC_INTERNAL_ERROR")
	}
}
