// Package httpserver composes the executable HTTP surface: a bearer-session
// middleware that turns tokens into verified principals, mounted over the
// existing strict handlers. It adds no business logic of its own.
package httpserver

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/httpapi"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

// PrincipalResolver authenticates one bearer token. Implementations must
// collapse every failure mode into a single not-found error.
type PrincipalResolver interface {
	Resolve(ctx context.Context, token string) (security.Principal, error)
}

type Config struct {
	Sessions PrincipalResolver
	Upload   httpapi.UploadService
	Preview  httpapi.PreviewReadService
	Apply    httpapi.ApplyService
}

// New builds the routing tree: an unauthenticated health probe plus the
// versioned API behind the session middleware.
func New(config Config) http.Handler {
	api := http.NewServeMux()
	httpapi.UploadHandler{Service: config.Upload}.Register(api)
	httpapi.PreviewHandler{Service: config.Preview}.Register(api)
	httpapi.ApplyHandler{Service: config.Apply}.Register(api)

	root := http.NewServeMux()
	root.HandleFunc("GET /healthz", func(writer http.ResponseWriter, _ *http.Request) {
		writer.Header().Set("Cache-Control", "no-store")
		writer.WriteHeader(http.StatusOK)
		_, _ = writer.Write([]byte("ok"))
	})
	root.Handle("/v1/", sessionMiddleware(config.Sessions, api))
	return root
}

// sessionMiddleware authenticates every request under it. The raw token is
// never logged and never stored on the request context — only the resolved
// principal is.
func sessionMiddleware(sessions PrincipalResolver, next http.Handler) http.Handler {
	return http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		if sessions == nil {
			writeAuthProblem(writer, http.StatusServiceUnavailable, "SEC_SERVICE_UNAVAILABLE")
			return
		}
		token, ok := bearerToken(request.Header.Get("Authorization"))
		if !ok {
			writeAuthProblem(writer, http.StatusUnauthorized, "SEC_AUTHENTICATION_REQUIRED")
			return
		}
		principal, err := sessions.Resolve(request.Context(), token)
		if err != nil {
			writeAuthProblem(writer, http.StatusUnauthorized, "SEC_AUTHENTICATION_REQUIRED")
			return
		}
		ctx, err := security.WithPrincipal(request.Context(), principal)
		if err != nil {
			writeAuthProblem(writer, http.StatusUnauthorized, "SEC_AUTHENTICATION_REQUIRED")
			return
		}
		next.ServeHTTP(writer, request.WithContext(ctx))
	})
}

func bearerToken(header string) (string, bool) {
	const scheme = "Bearer "
	if len(header) <= len(scheme) || len(header) > 512 || !strings.HasPrefix(header, scheme) {
		return "", false
	}
	return header[len(scheme):], true
}

func writeAuthProblem(writer http.ResponseWriter, status int, code string) {
	writer.Header().Set("Content-Type", "application/json")
	writer.Header().Set("Cache-Control", "no-store")
	writer.WriteHeader(status)
	_ = json.NewEncoder(writer).Encode(struct {
		Code string `json:"code"`
	}{Code: code})
}

// NewHTTPServer wraps the handler with the timeouts every deployment must
// keep; callers own listening and shutdown.
func NewHTTPServer(address string, handler http.Handler) *http.Server {
	return &http.Server{
		Addr:              address,
		Handler:           handler,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       30 * time.Second,
		WriteTimeout:      30 * time.Second,
		IdleTimeout:       60 * time.Second,
		MaxHeaderBytes:    64 * 1024,
	}
}
