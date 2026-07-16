package httpapi

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/security"
	"github.com/m-shogo/memories-project/services/import-api/internal/upload"
)

const defaultMaxJSONBody int64 = 32 * 1024

type UploadService interface {
	Issue(context.Context, security.Principal, upload.IssueRequest) (upload.IssueResponse, error)
	Complete(context.Context, security.Principal, string) error
}

type UploadHandler struct {
	Service     UploadService
	MaxJSONBody int64
}

func (h UploadHandler) Register(mux *http.ServeMux) {
	mux.HandleFunc("POST /v1/import-jobs/{jobID}/upload-authorizations", h.issue)
	mux.HandleFunc("POST /v1/upload-authorizations/{authorizationID}/complete", h.complete)
}

type issueUploadRequest struct {
	ContentLength   int64  `json:"contentLength"`
	ChecksumSHA256  string `json:"checksumSha256"`
	ContentType     string `json:"contentType"`
	SourceSurface   string `json:"sourceSurface"`
	DisplayFilename string `json:"displayFilename,omitempty"`
}

type issueUploadResponse struct {
	AuthorizationID string            `json:"authorizationId"`
	UploadURL        string            `json:"uploadUrl"`
	RequiredHeaders  map[string]string `json:"requiredHeaders"`
	ExpiresAt        time.Time         `json:"expiresAt"`
}

type problem struct {
	Code string `json:"code"`
}

func (h UploadHandler) issue(writer http.ResponseWriter, request *http.Request) {
	principal, err := security.PrincipalFromContext(request.Context())
	if err != nil {
		writeProblem(writer, http.StatusUnauthorized, "SEC_AUTHENTICATION_REQUIRED")
		return
	}
	if h.Service == nil {
		writeProblem(writer, http.StatusServiceUnavailable, "SEC_SERVICE_UNAVAILABLE")
		return
	}
	var body issueUploadRequest
	if err := decodeStrictJSON(writer, request, h.bodyLimit(), &body); err != nil {
		writeProblem(writer, http.StatusBadRequest, "SEC_UPLOAD_REQUEST_INVALID")
		return
	}
	response, err := h.Service.Issue(request.Context(), principal, upload.IssueRequest{
		JobID:           request.PathValue("jobID"),
		ContentLength:   body.ContentLength,
		ChecksumSHA256:  body.ChecksumSHA256,
		ContentType:     body.ContentType,
		SourceSurface:   body.SourceSurface,
		DisplayFilename: body.DisplayFilename,
	})
	if err != nil {
		writeUploadError(writer, err)
		return
	}
	writeJSON(writer, http.StatusCreated, issueUploadResponse{
		AuthorizationID: response.AuthorizationID,
		UploadURL:        response.UploadURL,
		RequiredHeaders:  response.RequiredHeaders,
		ExpiresAt:        response.ExpiresAt,
	})
}

func (h UploadHandler) complete(writer http.ResponseWriter, request *http.Request) {
	principal, err := security.PrincipalFromContext(request.Context())
	if err != nil {
		writeProblem(writer, http.StatusUnauthorized, "SEC_AUTHENTICATION_REQUIRED")
		return
	}
	if h.Service == nil {
		writeProblem(writer, http.StatusServiceUnavailable, "SEC_SERVICE_UNAVAILABLE")
		return
	}
	if request.Body != nil {
		request.Body = http.MaxBytesReader(writer, request.Body, 1)
		buffer := make([]byte, 1)
		count, readErr := request.Body.Read(buffer)
		if count != 0 || (readErr != nil && !errors.Is(readErr, io.EOF)) {
			writeProblem(writer, http.StatusBadRequest, "SEC_UPLOAD_REQUEST_INVALID")
			return
		}
	}
	if err := h.Service.Complete(request.Context(), principal, request.PathValue("authorizationID")); err != nil {
		writeUploadError(writer, err)
		return
	}
	writer.Header().Set("Cache-Control", "no-store")
	writer.WriteHeader(http.StatusAccepted)
}

func (h UploadHandler) bodyLimit() int64 {
	if h.MaxJSONBody <= 0 || h.MaxJSONBody > 1024*1024 {
		return defaultMaxJSONBody
	}
	return h.MaxJSONBody
}

func decodeStrictJSON(writer http.ResponseWriter, request *http.Request, limit int64, target any) error {
	request.Body = http.MaxBytesReader(writer, request.Body, limit)
	decoder := json.NewDecoder(request.Body)
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(target); err != nil {
		return err
	}
	if err := decoder.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		return errors.New("request contains trailing JSON")
	}
	return nil
}

func writeUploadError(writer http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, upload.ErrInvalidUploadRequest):
		writeProblem(writer, http.StatusBadRequest, "SEC_UPLOAD_REQUEST_INVALID")
	case errors.Is(err, upload.ErrUploadAuthorizationExpired), errors.Is(err, upload.ErrUploadAuthorizationConsumed), errors.Is(err, upload.ErrObjectMetadataMismatch):
		writeProblem(writer, http.StatusConflict, "SEC_UPLOAD_STATE_CONFLICT")
	case errors.Is(err, upload.ErrAuthorityNotAllowed), errors.Is(err, upload.ErrUploadAuthorizationNotFound), errors.Is(err, upload.ErrImportJobNotUploadable):
		writeProblem(writer, http.StatusNotFound, "SEC_RESOURCE_NOT_FOUND")
	default:
		writeProblem(writer, http.StatusInternalServerError, "SEC_INTERNAL_ERROR")
	}
}

func writeProblem(writer http.ResponseWriter, status int, code string) {
	writeJSON(writer, status, problem{Code: code})
}

func writeJSON(writer http.ResponseWriter, status int, value any) {
	writer.Header().Set("Content-Type", "application/json")
	writer.Header().Set("Cache-Control", "no-store")
	writer.Header().Set("Pragma", "no-cache")
	writer.WriteHeader(status)
	_ = json.NewEncoder(writer).Encode(value)
}
