package httpauth

import (
	"context"
	"errors"
	"net/http"
	"strings"

	"github.com/m-shogo/memories-project/backend/internal/security"
)

var (
	ErrMissingBearerToken = errors.New("missing bearer token")
	ErrInvalidBearerToken = errors.New("invalid bearer token")
	ErrPrincipalMissing   = errors.New("verified principal missing from context")
)

type VerifiedIdentity struct {
	Issuer  string
	Subject string
}

type TokenVerifier interface {
	VerifyBearerToken(ctx context.Context, rawToken string) (VerifiedIdentity, error)
}

type Account struct {
	ID    string
	Epoch int64
}

type AccountResolver interface {
	ResolveByProviderSubject(ctx context.Context, issuer, subject string) (Account, error)
}

type principalContextKey struct{}

type Middleware struct {
	verifier TokenVerifier
	accounts AccountResolver
}

func NewMiddleware(verifier TokenVerifier, accounts AccountResolver) (*Middleware, error) {
	if verifier == nil || accounts == nil {
		return nil, errors.New("authentication dependencies must not be nil")
	}
	return &Middleware{verifier: verifier, accounts: accounts}, nil
}

func (m *Middleware) RequirePrincipal(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-store")
		rawToken, err := bearerToken(r.Header.Get("Authorization"))
		if err != nil {
			writeUnauthorized(w)
			return
		}

		identity, err := m.verifier.VerifyBearerToken(r.Context(), rawToken)
		if err != nil || strings.TrimSpace(identity.Issuer) == "" || strings.TrimSpace(identity.Subject) == "" {
			writeUnauthorized(w)
			return
		}
		account, err := m.accounts.ResolveByProviderSubject(r.Context(), identity.Issuer, identity.Subject)
		if err != nil {
			writeUnauthorized(w)
			return
		}
		principal, err := security.NewVerifiedPrincipal(account.ID, account.Epoch, identity.Issuer, identity.Subject)
		if err != nil {
			writeUnauthorized(w)
			return
		}

		ctx := context.WithValue(r.Context(), principalContextKey{}, principal)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

func PrincipalFromContext(ctx context.Context) (security.Principal, error) {
	principal, ok := ctx.Value(principalContextKey{}).(security.Principal)
	if !ok {
		return security.Principal{}, ErrPrincipalMissing
	}
	if err := principal.Validate(); err != nil {
		return security.Principal{}, ErrPrincipalMissing
	}
	return principal, nil
}

func bearerToken(header string) (string, error) {
	parts := strings.Fields(header)
	if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") {
		return "", ErrMissingBearerToken
	}
	if len(parts[1]) < 16 || len(parts[1]) > 8192 {
		return "", ErrInvalidBearerToken
	}
	return parts[1], nil
}

func writeUnauthorized(w http.ResponseWriter) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("WWW-Authenticate", `Bearer realm="memory-os"`)
	w.WriteHeader(http.StatusUnauthorized)
	_, _ = w.Write([]byte(`{"code":"unauthorized"}`))
}
