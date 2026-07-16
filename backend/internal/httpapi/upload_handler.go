package httpapi

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"time"

	"github.com/m-shogo/memories-project/backend/internal/httpauth"
	"github.com/m-shogo/memories-project/backend/internal/security"
	"github.com/m-shogo/memories-project/backend/internal/upload"
)

const maxUploadAuthorizationRequestBytes int64 = 16 << 10

type UploadIssuer interface {
	Issue(context.Context, security.Principal, upload.Request) (upload.Response, error)
}

type UploadHandler struct {
	issuer UploadIssuer
}

func NewUploadHandler(issuer UploadIssuer) (*UploadHandler, error) {
	if issuer == nil {
		return nil, errors.New("upload issuer is nil")
	}
	return &UploadHandler{issuer: issuer}, nil
}

type issueUploadRequest struct {
	ContentLength    int64  `json:"contentLength"`
	ChecksumSHA256   string `json:"checksumSha256"`
	ContentType      string `json:"contentType"`
	SourceSurface    string `json:"sourceSurface"`
	DisplayFilename string `json:"displayFilename,omitempty"`
}

type issueUploadResponse struct {
	UploadAuthorizationID string            `json:"uploadAuthorizationId"`
	UploadURL              string            `json:"uploadUrl"`
	RequiredHeaders        map[string]string `json:"requiredHeaders"`
	ExpiresAt              time.Time         `json:"expiresAt"`
}

func (h *UploadHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("Content-Type", "application/json")
	if r.Method != http.MethodPost {
		w.Header().Set("Allow", http.MethodPost)
		writeError(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}

	principal, err := httpauth.PrincipalFromContext(r.Context())
	if err != nil {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	jobID := r.PathValue("jobId")
	if jobID == "" {
		writeError(w, http.StatusNotFound, "not_found")
		return
	}

	r.Body = http.MaxBytesReader(w, r.Body, maxUploadAuthorizationRequestBytes)
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	var body issueUploadRequest
	if err := decoder.Decode(&body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_request")
		return
	}
	if err := decoder.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "invalid_request")
		return
	}

	response, err := h.issuer.Issue(r.Context(), principal, upload.Request{
		JobID:            jobID,
		ContentLength:    body.ContentLength,
		ChecksumSHA256:   body.ChecksumSHA256,
		ContentType:      body.ContentType,
		SourceSurface:    body.SourceSurface,
		DisplayFilename: body.DisplayFilename,
	})
	if err != nil {
		switch {
		case errors.Is(err, upload.ErrJobUnavailable):
			writeError(w, http.StatusNotFound, "not_found")
		case errors.Is(err, upload.ErrInvalidJobID),
			errors.Is(err, upload.ErrInvalidLength),
			errors.Is(err, upload.ErrInvalidChecksum),
			errors.Is(err, upload.ErrInvalidContentType):
			writeError(w, http.StatusBadRequest, "invalid_request")
		default:
			writeError(w, http.StatusInternalServerError, "internal_error")
		}
		return
	}

	w.WriteHeader(http.StatusCreated)
	_ = json.NewEncoder(w).Encode(issueUploadResponse{
		UploadAuthorizationID: response.Authorization.ID,
		UploadURL:              response.SignedPUT.URL,
		RequiredHeaders:        response.SignedPUT.RequiredHeaders,
		ExpiresAt:              response.Authorization.ExpiresAt,
	})
}

func writeError(w http.ResponseWriter, status int, code string) {
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]string{"code": code})
}
