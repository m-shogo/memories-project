package httpauth

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
)

type fakeVerifier struct {
	identity VerifiedIdentity
	err      error
	token    string
}

func (f *fakeVerifier) VerifyBearerToken(_ context.Context, rawToken string) (VerifiedIdentity, error) {
	f.token = rawToken
	return f.identity, f.err
}

type fakeAccounts struct {
	account Account
	err     error
	issuer  string
	subject string
}

func (f *fakeAccounts) ResolveByProviderSubject(_ context.Context, issuer, subject string) (Account, error) {
	f.issuer = issuer
	f.subject = subject
	return f.account, f.err
}

func TestRequirePrincipalUsesVerifiedProviderIdentity(t *testing.T) {
	t.Parallel()

	verifier := &fakeVerifier{identity: VerifiedIdentity{
		Issuer:  "https://appleid.apple.com",
		Subject: "apple-subject-001",
	}}
	accounts := &fakeAccounts{account: Account{
		ID:    "acct_01J00000000000000000000000",
		Epoch: 7,
	}}
	middleware, err := NewMiddleware(verifier, accounts)
	if err != nil {
		t.Fatalf("NewMiddleware() error = %v", err)
	}

	handler := middleware.RequirePrincipal(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		principal, err := PrincipalFromContext(r.Context())
		if err != nil {
			t.Fatalf("PrincipalFromContext() error = %v", err)
		}
		if principal.AccountID() != "acct_01J00000000000000000000000" || principal.Epoch() != 7 {
			t.Fatalf("unexpected principal")
		}
		w.WriteHeader(http.StatusNoContent)
	}))

	request := httptest.NewRequest(http.MethodGet, "/private", nil)
	request.Header.Set("Authorization", "Bearer token_0123456789abcdef")
	request.Header.Set("X-Account-ID", "acct_01J99999999999999999999999")
	response := httptest.NewRecorder()

	handler.ServeHTTP(response, request)

	if response.Code != http.StatusNoContent {
		t.Fatalf("status = %d, body=%s", response.Code, response.Body.String())
	}
	if verifier.token != "token_0123456789abcdef" {
		t.Fatalf("unexpected token passed to verifier")
	}
	if accounts.issuer != "https://appleid.apple.com" || accounts.subject != "apple-subject-001" {
		t.Fatalf("account was not resolved from verified issuer+subject")
	}
}

func TestRequirePrincipalRejectsMissingBearer(t *testing.T) {
	t.Parallel()

	middleware, err := NewMiddleware(&fakeVerifier{}, &fakeAccounts{})
	if err != nil {
		t.Fatalf("NewMiddleware() error = %v", err)
	}
	response := httptest.NewRecorder()
	middleware.RequirePrincipal(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {
		t.Fatalf("next handler must not run")
	})).ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/private", nil))

	if response.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d", response.Code)
	}
	if response.Header().Get("Cache-Control") != "no-store" {
		t.Fatalf("missing no-store header")
	}
}

func TestRequirePrincipalRejectsVerifierFailure(t *testing.T) {
	t.Parallel()

	middleware, err := NewMiddleware(
		&fakeVerifier{err: errors.New("signature invalid")},
		&fakeAccounts{},
	)
	if err != nil {
		t.Fatalf("NewMiddleware() error = %v", err)
	}
	request := httptest.NewRequest(http.MethodGet, "/private", nil)
	request.Header.Set("Authorization", "Bearer token_0123456789abcdef")
	response := httptest.NewRecorder()

	middleware.RequirePrincipal(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {
		t.Fatalf("next handler must not run")
	})).ServeHTTP(response, request)

	if response.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d", response.Code)
	}
}

func TestPrincipalFromContextRejectsMissingPrincipal(t *testing.T) {
	t.Parallel()

	if _, err := PrincipalFromContext(context.Background()); !errors.Is(err, ErrPrincipalMissing) {
		t.Fatalf("error = %v", err)
	}
}
