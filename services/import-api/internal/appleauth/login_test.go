package appleauth

import (
	"context"
	"crypto/rand"
	"crypto/rsa"
	"errors"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

type fakeSessions struct {
	token     string
	err       error
	accountID string
	epoch     int64
	authority security.Authority
}

func (f *fakeSessions) Issue(_ context.Context, accountID string, epoch int64, authority security.Authority, _ time.Duration) (string, error) {
	f.accountID = accountID
	f.epoch = epoch
	f.authority = authority
	return f.token, f.err
}

// loginFixture builds a verifier and a matching valid input, both using one
// freshly generated key, mirroring the verifier package's own test setup.
func loginFixture(t *testing.T, now time.Time) (*Verifier, Input) {
	t.Helper()
	privateKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatal(err)
	}
	token := signedToken(t, privateKey, map[string]any{
		"iss":   DefaultIssuer,
		"sub":   "apple-subject-123",
		"aud":   "com.memoryos.app",
		"exp":   now.Add(5 * time.Minute).Unix(),
		"iat":   now.Add(-time.Minute).Unix(),
		"nonce": "nonce-login-value",
	})
	verifier := validVerifier(now, &privateKey.PublicKey)
	input := Input{
		IdentityToken:      token,
		AuthorizationCode:  "single-use-login-code",
		ClientID:           "com.memoryos.app",
		ExpectedNonceClaim: "nonce-login-value",
	}
	return &verifier, input
}

func TestLoginIssuesSessionForVerifiedIdentity(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	verifier, input := loginFixture(t, now)
	sessions := &fakeSessions{token: "ses_live_token"}
	service := LoginService{Verifier: verifier, Sessions: sessions}

	result, err := service.Login(context.Background(), input)
	if err != nil {
		t.Fatal(err)
	}
	if result.SessionToken != "ses_live_token" || result.AccountID == "" {
		t.Fatalf("unexpected result: %+v", result)
	}
	// The session is issued for the resolved account, as a full user, never a
	// lower authority.
	if sessions.accountID != result.AccountID || sessions.authority != security.AuthorityIOSUser {
		t.Fatalf("session issued with wrong identity: %+v", sessions)
	}
}

func TestLoginPropagatesVerifierRejection(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	verifier, input := loginFixture(t, now)
	sessions := &fakeSessions{token: "ses"}
	service := LoginService{Verifier: verifier, Sessions: sessions}

	input.ExpectedNonceClaim = "a-different-nonce-than-the-token"
	if _, err := service.Login(context.Background(), input); !errors.Is(err, ErrNonceMismatch) {
		t.Fatalf("error = %v, want ErrNonceMismatch", err)
	}
	if sessions.accountID != "" {
		t.Fatal("a session was issued for a rejected login")
	}
}

// A session-issuance failure must be distinct from an auth rejection: the
// identity was verified, only the session store failed, and the client should
// retry rather than treat it as bad credentials.
func TestLoginSessionIssuanceFailureIsRetryable(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	verifier, input := loginFixture(t, now)
	sessions := &fakeSessions{err: errors.New("session store unavailable")}
	service := LoginService{Verifier: verifier, Sessions: sessions}

	_, err := service.Login(context.Background(), input)
	if !errors.Is(err, ErrSessionIssuance) {
		t.Fatalf("error = %v, want ErrSessionIssuance", err)
	}
	if errors.Is(err, ErrNonceMismatch) || errors.Is(err, ErrSignatureInvalid) {
		t.Fatal("session failure masqueraded as an auth rejection")
	}
}

func TestLoginRequiresComposition(t *testing.T) {
	if _, err := (LoginService{}).Login(context.Background(), Input{}); !errors.Is(err, ErrLoginUnavailable) {
		t.Fatalf("error = %v, want ErrLoginUnavailable", err)
	}
}
