package appleauth

import (
	"context"
	"crypto"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"testing"
	"time"
)

type fakeKeys struct {
	key            *rsa.PublicKey
	refreshes      int
	missingOnFirst bool
}

func (f *fakeKeys) LookupRSAKey(_ context.Context, _ string, force bool) (*rsa.PublicKey, error) {
	if f.missingOnFirst && !force {
		return nil, ErrKeyNotFound
	}
	if force {
		f.refreshes++
	}
	return f.key, nil
}

type fakeCodes struct {
	result CodeExchangeResult
	err    error
}

func (f fakeCodes) Exchange(context.Context, string, string, *string) (CodeExchangeResult, error) {
	return f.result, f.err
}

type fakeReplay struct {
	consumed bool
	err      error
}

func (f *fakeReplay) Consume(context.Context, string, string) error {
	if f.err != nil {
		return f.err
	}
	if f.consumed {
		return errors.New("replay")
	}
	f.consumed = true
	return nil
}

type fakeAccounts struct {
	accountID string
	epoch     int64
	err       error
}

func (f fakeAccounts) ResolveOrCreate(context.Context, string, string) (string, int64, error) {
	return f.accountID, f.epoch, f.err
}

func TestVerifierAcceptsValidAppleCredentialAndRefreshesUnknownKey(t *testing.T) {
	privateKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatal(err)
	}
	now := time.Unix(1_800_000_000, 0).UTC()
	token := signedToken(t, privateKey, map[string]any{
		"iss":   DefaultIssuer,
		"sub":   "apple-subject-123",
		"aud":   "com.memoryos.app",
		"exp":   now.Add(5 * time.Minute).Unix(),
		"iat":   now.Add(-time.Minute).Unix(),
		"nonce": "nonce-sha256-value",
	})
	keys := &fakeKeys{key: &privateKey.PublicKey, missingOnFirst: true}
	replay := &fakeReplay{}
	verifier := Verifier{
		Audiences:   map[string]struct{}{"com.memoryos.app": {}},
		ClockSkew:   2 * time.Minute,
		MaxTokenAge: 10 * time.Minute,
		Now:         func() time.Time { return now },
		Keys:        keys,
		Codes:       fakeCodes{result: CodeExchangeResult{Subject: "apple-subject-123", ClientID: "com.memoryos.app"}},
		Replay:      replay,
		Accounts:    fakeAccounts{accountID: "acct_01J00000000000000000000000", epoch: 7},
	}
	identity, err := verifier.Verify(context.Background(), Input{IdentityToken: token, AuthorizationCode: "single-use-code", ClientID: "com.memoryos.app", ExpectedNonceClaim: "nonce-sha256-value"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if identity.AccountID != "acct_01J00000000000000000000000" || identity.Subject != "apple-subject-123" {
		t.Fatalf("unexpected identity: %#v", identity)
	}
	if keys.refreshes != 1 || !replay.consumed {
		t.Fatalf("expected one key refresh and replay consumption: refreshes=%d consumed=%v", keys.refreshes, replay.consumed)
	}
}

func TestVerifierRejectsWrongIssuerBeforeAccountBinding(t *testing.T) {
	privateKey, _ := rsa.GenerateKey(rand.Reader, 2048)
	now := time.Unix(1_800_000_000, 0).UTC()
	token := signedToken(t, privateKey, map[string]any{"iss": "https://attacker.example", "sub": "apple-subject-123", "aud": "com.memoryos.app", "exp": now.Add(5 * time.Minute).Unix(), "iat": now.Unix(), "nonce": "nonce"})
	verifier := validVerifier(now, &privateKey.PublicKey)
	_, err := verifier.Verify(context.Background(), Input{IdentityToken: token, AuthorizationCode: "code", ClientID: "com.memoryos.app", ExpectedNonceClaim: "nonce"})
	if !errors.Is(err, ErrIssuerInvalid) {
		t.Fatalf("expected issuer error, got %v", err)
	}
}

func TestVerifierRejectsNonceMismatch(t *testing.T) {
	privateKey, _ := rsa.GenerateKey(rand.Reader, 2048)
	now := time.Unix(1_800_000_000, 0).UTC()
	token := signedToken(t, privateKey, map[string]any{"iss": DefaultIssuer, "sub": "apple-subject-123", "aud": "com.memoryos.app", "exp": now.Add(5 * time.Minute).Unix(), "iat": now.Unix(), "nonce": "actual"})
	verifier := validVerifier(now, &privateKey.PublicKey)
	_, err := verifier.Verify(context.Background(), Input{IdentityToken: token, AuthorizationCode: "code", ClientID: "com.memoryos.app", ExpectedNonceClaim: "expected"})
	if !errors.Is(err, ErrNonceMismatch) {
		t.Fatalf("expected nonce mismatch, got %v", err)
	}
}

func TestVerifierRejectsCodeSubjectMismatch(t *testing.T) {
	privateKey, _ := rsa.GenerateKey(rand.Reader, 2048)
	now := time.Unix(1_800_000_000, 0).UTC()
	token := signedToken(t, privateKey, map[string]any{"iss": DefaultIssuer, "sub": "apple-subject-123", "aud": "com.memoryos.app", "exp": now.Add(5 * time.Minute).Unix(), "iat": now.Unix(), "nonce": "nonce"})
	verifier := validVerifier(now, &privateKey.PublicKey)
	verifier.Codes = fakeCodes{result: CodeExchangeResult{Subject: "different-subject", ClientID: "com.memoryos.app"}}
	_, err := verifier.Verify(context.Background(), Input{IdentityToken: token, AuthorizationCode: "code", ClientID: "com.memoryos.app", ExpectedNonceClaim: "nonce"})
	if !errors.Is(err, ErrCodeBindingMismatch) {
		t.Fatalf("expected code binding mismatch, got %v", err)
	}
}

func TestVerifierRejectsDuplicateClaimKey(t *testing.T) {
	privateKey, _ := rsa.GenerateKey(rand.Reader, 2048)
	now := time.Unix(1_800_000_000, 0).UTC()
	header := []byte(`{"alg":"RS256","kid":"apple-key-1"}`)
	claims := []byte(`{"iss":"https://appleid.apple.com","sub":"subject-a","sub":"subject-b","aud":"com.memoryos.app","exp":1800000300,"iat":1800000000,"nonce":"nonce"}`)
	token := signedRawToken(t, privateKey, header, claims)
	verifier := validVerifier(now, &privateKey.PublicKey)
	_, err := verifier.Verify(context.Background(), Input{IdentityToken: token, AuthorizationCode: "code", ClientID: "com.memoryos.app", ExpectedNonceClaim: "nonce"})
	if !errors.Is(err, ErrDuplicateJSONKey) {
		t.Fatalf("expected duplicate key error, got %v", err)
	}
}

func validVerifier(now time.Time, key *rsa.PublicKey) Verifier {
	return Verifier{Audiences: map[string]struct{}{"com.memoryos.app": {}}, ClockSkew: 2 * time.Minute, MaxTokenAge: 10 * time.Minute, Now: func() time.Time { return now }, Keys: &fakeKeys{key: key}, Codes: fakeCodes{result: CodeExchangeResult{Subject: "apple-subject-123", ClientID: "com.memoryos.app"}}, Replay: &fakeReplay{}, Accounts: fakeAccounts{accountID: "acct_01J00000000000000000000000", epoch: 7}}
}

func signedToken(t *testing.T, privateKey *rsa.PrivateKey, claims map[string]any) string {
	t.Helper()
	headerBytes, _ := json.Marshal(map[string]any{"alg": "RS256", "kid": "apple-key-1"})
	claimsBytes, _ := json.Marshal(claims)
	return signedRawToken(t, privateKey, headerBytes, claimsBytes)
}

func signedRawToken(t *testing.T, privateKey *rsa.PrivateKey, headerBytes, claimsBytes []byte) string {
	t.Helper()
	header := base64.RawURLEncoding.EncodeToString(headerBytes)
	payload := base64.RawURLEncoding.EncodeToString(claimsBytes)
	signingInput := header + "." + payload
	digest := sha256.Sum256([]byte(signingInput))
	signature, err := rsa.SignPKCS1v15(rand.Reader, privateKey, crypto.SHA256, digest[:])
	if err != nil {
		t.Fatal(err)
	}
	return signingInput + "." + base64.RawURLEncoding.EncodeToString(signature)
}
