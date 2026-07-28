//go:build linux

package httpserver

import (
	"bytes"
	"context"
	"crypto"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/accountdelete"
	"github.com/m-shogo/memories-project/services/import-api/internal/appleauth"
	"github.com/m-shogo/memories-project/services/import-api/internal/cryptoids"
	"github.com/m-shogo/memories-project/services/import-api/internal/obslog"
	"github.com/m-shogo/memories-project/services/import-api/internal/ratelimit"
)

// fakeApple stands in for Apple: it signs identity tokens with a test RSA key,
// serves a token endpoint that returns a signed id_token, and exposes a
// KeyProvider so the verifier can check signatures without reaching the real
// JWKS host. Only the token endpoint is exercised over real HTTP — that is the
// surface this checkpoint newly implements.
type fakeApple struct {
	key       *rsa.PrivateKey
	kid       string
	issuer    string
	clientID  string
	server    *httptest.Server
	now       func() time.Time
	mu        sync.Mutex
	codeSubs  map[string]string // authorization code -> subject Apple will return
	rejectAll bool
	lookups   int
}

func newFakeApple(t *testing.T, clientID string) *fakeApple {
	t.Helper()
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatal(err)
	}
	fake := &fakeApple{
		key:      key,
		kid:      "fake-apple-key-1",
		issuer:   appleauth.DefaultIssuer,
		clientID: clientID,
		now:      time.Now,
		codeSubs: map[string]string{},
	}
	mux := http.NewServeMux()
	mux.HandleFunc("/auth/token", fake.handleToken)
	fake.server = httptest.NewServer(mux)
	t.Cleanup(fake.server.Close)
	return fake
}

// registerCode tells the fake which subject its token endpoint will report for
// a given authorization code, modelling Apple issuing the code for that user.
func (f *fakeApple) registerCode(code, subject string) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.codeSubs[code] = subject
}

func (f *fakeApple) handleToken(w http.ResponseWriter, r *http.Request) {
	if err := r.ParseForm(); err != nil {
		w.WriteHeader(http.StatusBadRequest)
		return
	}
	f.mu.Lock()
	reject := f.rejectAll
	subject, known := f.codeSubs[r.Form.Get("code")]
	f.mu.Unlock()

	if reject || !known {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		_, _ = w.Write([]byte(`{"error":"invalid_grant"}`))
		return
	}
	idToken := f.signToken(map[string]any{
		"iss": f.issuer,
		"sub": subject,
		"aud": r.Form.Get("client_id"),
		"iat": f.now().UTC().Unix(),
		"exp": f.now().UTC().Add(10 * time.Minute).Unix(),
	})
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]any{
		"access_token": "fake-access", "token_type": "bearer",
		"expires_in": 3600, "refresh_token": "fake-refresh", "id_token": idToken,
	})
}

func (f *fakeApple) signToken(claims map[string]any) string {
	headerBytes, _ := json.Marshal(map[string]any{"alg": "RS256", "kid": f.kid})
	claimsBytes, _ := json.Marshal(claims)
	signingInput := base64.RawURLEncoding.EncodeToString(headerBytes) + "." +
		base64.RawURLEncoding.EncodeToString(claimsBytes)
	digest := sha256.Sum256([]byte(signingInput))
	signature, _ := rsa.SignPKCS1v15(rand.Reader, f.key, crypto.SHA256, digest[:])
	return signingInput + "." + base64.RawURLEncoding.EncodeToString(signature)
}

// identityToken mints the client-supplied identity token for a login attempt.
func (f *fakeApple) identityToken(subject, nonce string) string {
	return f.signToken(map[string]any{
		"iss": f.issuer, "sub": subject, "aud": f.clientID,
		"iat": f.now().UTC().Unix(), "exp": f.now().UTC().Add(10 * time.Minute).Unix(),
		"nonce": nonce,
	})
}

// LookupRSAKey satisfies appleauth.KeyProvider. It counts lookups so a test can
// assert the unknown-kid single refresh behaviour.
func (f *fakeApple) LookupRSAKey(_ context.Context, kid string, _ bool) (*rsa.PublicKey, error) {
	f.mu.Lock()
	f.lookups++
	f.mu.Unlock()
	if kid != f.kid {
		return nil, appleauth.ErrKeyNotFound
	}
	return &f.key.PublicKey, nil
}

func (f *fakeApple) loginService(s *liveServer) appleauth.LoginService {
	verifier := &appleauth.Verifier{
		Issuer:      f.issuer,
		Audiences:   map[string]struct{}{f.clientID: {}},
		ClockSkew:   2 * time.Minute,
		MaxTokenAge: 10 * time.Minute,
		Keys:        f,
		Codes: appleauth.TokenClient{
			Endpoint: f.server.URL + "/auth/token",
			Issuer:   f.issuer,
			ClientSecret: appleauth.ClientSecretConfig{
				TeamID: "TESTTEAMID", KeyID: "TESTKEYID", ClientID: f.clientID,
				PrivateKey: testECKey(),
			},
			HTTPClient: f.server.Client(),
		},
		Replay:   appleauth.PostgresReplayGuard{Pool: s.appPool},
		Accounts: appleauth.PostgresAccountBindingStore{Pool: s.appPool, IDs: cryptoids.Generator{}},
	}
	return appleauth.LoginService{
		Verifier: verifier,
		Sessions: appleSessionAdapter{store: s.sessions},
	}
}

// TestAppleLoginJourneyOverHTTP is the end-to-end proof: a fake Apple, a real
// PostgreSQL, and the real HTTP endpoint. It covers first login, returning
// login resolving the same account, a second subject as a distinct account,
// replay rejection, nonce mismatch, Apple rejection, malformed token, and that
// the issued session actually authenticates a subsequent request.
func uniq(base string, runID int64) string { return fmt.Sprintf("%s-%d", base, runID) }

func TestAppleLoginJourneyOverHTTP(t *testing.T) {
	server := newLiveServer(t)
	runID := time.Now().UnixNano()
	clientID := "com.memoryos.app"
	apple := newFakeApple(t, clientID)
	server.rewireApple(apple.loginService(server))

	subjectA := fmt.Sprintf("apple-subject-a-%d", runID)
	login := func(subject, nonce, code string, redirect *string) (*http.Response, []byte) {
		body := map[string]any{
			"identityToken":     apple.identityToken(subject, nonce),
			"authorizationCode": code,
			"clientId":          clientID,
			"nonce":             nonce,
		}
		if redirect != nil {
			body["redirectUri"] = *redirect
		}
		return server.request(t, http.MethodPost, "/v1/auth/apple", "", body)
	}

	// First login creates the account and returns a working session.
	apple.registerCode(uniq("code-a-1", runID), subjectA)
	response, payload := login(subjectA, uniq("nonce-a-1", runID), uniq("code-a-1", runID), nil)
	if response.StatusCode != http.StatusOK {
		t.Fatalf("first login: %d %s", response.StatusCode, payload)
	}
	var first struct {
		SessionToken string `json:"sessionToken"`
		AccountID    string `json:"accountId"`
	}
	if err := json.Unmarshal(payload, &first); err != nil {
		t.Fatal(err)
	}
	if first.SessionToken == "" || first.AccountID == "" {
		t.Fatalf("first login response incomplete: %s", payload)
	}

	// The session authenticates a real request.
	response, _ = server.request(t, http.MethodGet,
		"/v1/import-jobs/job-does-not-exist/preview", first.SessionToken, nil)
	if response.StatusCode == http.StatusUnauthorized {
		t.Fatal("the Apple-issued session did not authenticate")
	}

	// Returning login (new nonce and code) resolves the SAME account.
	apple.registerCode(uniq("code-a-2", runID), subjectA)
	response, payload = login(subjectA, uniq("nonce-a-2", runID), uniq("code-a-2", runID), nil)
	if response.StatusCode != http.StatusOK {
		t.Fatalf("returning login: %d %s", response.StatusCode, payload)
	}
	var second struct {
		AccountID string `json:"accountId"`
	}
	_ = json.Unmarshal(payload, &second)
	if second.AccountID != first.AccountID {
		t.Fatalf("returning login gave a different account: %s vs %s", second.AccountID, first.AccountID)
	}

	// A different Apple subject is a different account.
	subjectB := fmt.Sprintf("apple-subject-b-%d", runID)
	apple.registerCode(uniq("code-b-1", runID), subjectB)
	response, payload = login(subjectB, uniq("nonce-b-1", runID), uniq("code-b-1", runID), nil)
	if response.StatusCode != http.StatusOK {
		t.Fatalf("second subject login: %d %s", response.StatusCode, payload)
	}
	var third struct {
		AccountID string `json:"accountId"`
	}
	_ = json.Unmarshal(payload, &third)
	if third.AccountID == first.AccountID {
		t.Fatal("a different Apple subject resolved to the same account")
	}

	// Replaying a consumed code is rejected.
	response, payload = login(subjectA, uniq("nonce-a-1", runID), uniq("code-a-1", runID), nil)
	if response.StatusCode != http.StatusUnauthorized {
		t.Fatalf("replayed code accepted: %d %s", response.StatusCode, payload)
	}

	// A nonce that does not match the identity token is rejected.
	apple.registerCode(uniq("code-a-3", runID), subjectA)
	body := map[string]any{
		"identityToken":     apple.identityToken(subjectA, uniq("nonce-in-token", runID)),
		"authorizationCode": uniq("code-a-3", runID),
		"clientId":          clientID,
		"nonce":             uniq("different-expected-nonce", runID),
	}
	response, payload = server.request(t, http.MethodPost, "/v1/auth/apple", "", body)
	if response.StatusCode != http.StatusUnauthorized {
		t.Fatalf("nonce mismatch accepted: %d %s", response.StatusCode, payload)
	}

	// Apple rejecting the code (unknown/expired) is a rejection, not a 500.
	response, payload = login(subjectA, uniq("nonce-a-4", runID), uniq("code-never-registered", runID), nil)
	if response.StatusCode != http.StatusUnauthorized {
		t.Fatalf("unregistered code status: %d %s", response.StatusCode, payload)
	}

	// A malformed identity token is a bad request.
	response, _ = server.request(t, http.MethodPost, "/v1/auth/apple", "", map[string]any{
		"identityToken": "not-a-jwt", "authorizationCode": uniq("code-x", runID),
		"clientId": clientID, "nonce": "n",
	})
	if response.StatusCode != http.StatusBadRequest {
		t.Fatalf("malformed token status: %d", response.StatusCode)
	}
}

// TestAppleLoginUnconfiguredIsUnavailable proves that without an Apple login
// service wired the public endpoint reports 503 and provisions nothing — the
// binary must run in this state (no credentials) without opening a half-built
// account-creation surface.
func TestAppleLoginUnconfiguredIsUnavailable(t *testing.T) {
	server := newLiveServer(t)
	// Deliberately do NOT rewire Apple: the holder's inner stays nil.
	before := appleIdentityCount(t, server)
	response, body := server.request(t, http.MethodPost, "/v1/auth/apple", "", map[string]any{
		"identityToken": "x", "authorizationCode": "y", "clientId": "com.memoryos.app", "nonce": "n",
	})
	if response.StatusCode != http.StatusServiceUnavailable {
		t.Fatalf("unconfigured Apple login status: %d %s", response.StatusCode, body)
	}
	if after := appleIdentityCount(t, server); after != before {
		t.Fatalf("unconfigured Apple login created %d identity rows", after-before)
	}
}

func appleIdentityCount(t *testing.T, s *liveServer) int {
	t.Helper()
	var count int
	if err := s.pool.QueryRow(context.Background(),
		"SELECT count(*) FROM memory_os.apple_identity").Scan(&count); err != nil {
		t.Fatal(err)
	}
	return count
}

// TestAppleLoginRefusesDeletedAccountRevival proves a signed-in identity whose
// account is deleting is refused rather than revived.
func TestAppleLoginRefusesDeletedAccountRevival(t *testing.T) {
	server := newLiveServer(t)
	runID := time.Now().UnixNano()
	clientID := "com.memoryos.app"
	apple := newFakeApple(t, clientID)
	server.rewireApple(apple.loginService(server))

	subject := fmt.Sprintf("apple-subject-del-%d", runID)
	apple.registerCode(uniq("code-del-1", runID), subject)
	response, payload := server.request(t, http.MethodPost, "/v1/auth/apple", "", map[string]any{
		"identityToken":     apple.identityToken(subject, uniq("nonce-del-1", runID)),
		"authorizationCode": uniq("code-del-1", runID),
		"clientId":          clientID,
		"nonce":             uniq("nonce-del-1", runID),
	})
	if response.StatusCode != http.StatusOK {
		t.Fatalf("initial login: %d %s", response.StatusCode, payload)
	}
	var created struct {
		AccountID string `json:"accountId"`
	}
	_ = json.Unmarshal(payload, &created)

	// Begin deletion of that account through the real API path.
	bumpAccountToDeleting(t, server, created.AccountID)

	// A returning login is refused with a conflict, not resurrected.
	apple.registerCode(uniq("code-del-2", runID), subject)
	response, payload = server.request(t, http.MethodPost, "/v1/auth/apple", "", map[string]any{
		"identityToken":     apple.identityToken(subject, uniq("nonce-del-2", runID)),
		"authorizationCode": uniq("code-del-2", runID),
		"clientId":          clientID,
		"nonce":             uniq("nonce-del-2", runID),
	})
	if response.StatusCode != http.StatusConflict {
		t.Fatalf("deleting-account login status: %d %s", response.StatusCode, payload)
	}

	// Drain the fenced account so it does not linger as claimable deletion work
	// for other tests sharing this database — the shared cluster is why several
	// live tests already use run-unique identifiers.
	drainDeletion(t, server)
}

// drainDeletion runs the real deletion worker until no account remains
// claimable, turning any lingering deleting account into a completed tombstone.
func drainDeletion(t *testing.T, s *liveServer) {
	t.Helper()
	worker := accountdelete.Worker{
		Queue:      s.accountControl,
		Repository: s.accountControl,
		Objects:    s.objects,
	}
	if _, err := worker.Sweep(context.Background(), 16); err != nil {
		t.Fatalf("drain deletion: %v", err)
	}
}

// testECKey is a P-256 key for the client-secret signer. The fake Apple never
// checks the client secret, but the TokenClient generates one on every
// exchange, so a valid key must exist.
var testECKeyOnce sync.Once
var testECKeyValue *ecdsa.PrivateKey

func testECKey() *ecdsa.PrivateKey {
	testECKeyOnce.Do(func() {
		key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
		if err != nil {
			panic(err)
		}
		testECKeyValue = key
	})
	return testECKeyValue
}

// TestRateLimitedAppleLoginCreatesNoStateOn429 proves against a real database
// that a rate-limited Apple request creates no account, session, Apple identity
// or replay row: the enforcer denies before the handler, so nothing downstream
// runs. It builds a dedicated rate-limited server over the live server's pool.
func TestRateLimitedAppleLoginCreatesNoStateOn429(t *testing.T) {
	base := newLiveServer(t)
	runID := time.Now().UnixNano()
	clientID := "com.memoryos.app"
	apple := newFakeApple(t, clientID)

	// Network capacity 1 so the second request from one network is a 429.
	policy := ratelimit.RoutePolicy{
		RouteTemplate: "POST /v1/auth/apple",
		Class:         ratelimit.ClassPublicUnauthenticated,
		Enabled:       true,
		FailureMode:   ratelimit.FailClosed,
		Global:        ratelimit.Policy{ID: "g", Capacity: 1000, RefillPerSec: 1000},
		Network:       ratelimit.Policy{ID: "n", Capacity: 1, RefillPerSec: 0.001},
	}
	enforcer, err := ratelimit.NewEnforcer(ratelimit.NewMemoryStore(1000, time.Minute), nil, []ratelimit.RoutePolicy{policy})
	if err != nil {
		t.Fatal(err)
	}
	handler := New(Config{
		Logger:     obslog.New(nil),
		AppleLogin: apple.loginService(base),
		RateLimit: RateLimitConfig{
			Enforcer: enforcer,
			Deriver:  ratelimit.KeyDeriver{Secret: []byte("live-rl-secret"), IPv6PrefixBits: 64},
		},
	})
	srv := httptest.NewServer(handler)
	t.Cleanup(srv.Close)

	subject := fmt.Sprintf("apple-subject-rl-%d", runID)
	post := func(nonce, code string) int {
		apple.registerCode(code, subject)
		body, _ := json.Marshal(map[string]any{
			"identityToken":     apple.identityToken(subject, nonce),
			"authorizationCode": code, "clientId": clientID, "nonce": nonce,
		})
		request, err := http.NewRequest(http.MethodPost, srv.URL+"/v1/auth/apple", bytes.NewReader(body))
		if err != nil {
			t.Fatal(err)
		}
		request.RemoteAddr = "203.0.113.200:5000"
		request.Header.Set("Content-Type", "application/json")
		response, err := http.DefaultClient.Do(request)
		if err != nil {
			t.Fatal(err)
		}
		_ = response.Body.Close()
		return response.StatusCode
	}

	// First request from a fresh subject would normally create the account; use
	// a DISTINCT subject so the 429 case below has provably created nothing for
	// its own subject.
	blockedSubject := fmt.Sprintf("apple-subject-rl-blocked-%d", runID)
	// Consume the single network token with the first subject.
	if code := post(uniq("nonce-rl-1", runID), uniq("code-rl-1", runID)); code != http.StatusOK {
		t.Fatalf("first (allowed) login status %d", code)
	}
	// Second request, different subject, same network -> 429 before the handler.
	apple.registerCode(uniq("code-rl-blocked", runID), blockedSubject)
	body, _ := json.Marshal(map[string]any{
		"identityToken":     apple.identityToken(blockedSubject, uniq("nonce-rl-blocked", runID)),
		"authorizationCode": uniq("code-rl-blocked", runID), "clientId": clientID, "nonce": uniq("nonce-rl-blocked", runID),
	})
	request, _ := http.NewRequest(http.MethodPost, srv.URL+"/v1/auth/apple", bytes.NewReader(body))
	request.RemoteAddr = "203.0.113.200:5001"
	request.Header.Set("Content-Type", "application/json")
	response, err := http.DefaultClient.Do(request)
	if err != nil {
		t.Fatal(err)
	}
	_ = response.Body.Close()
	if response.StatusCode != http.StatusTooManyRequests {
		t.Fatalf("second login not rate limited: %d", response.StatusCode)
	}

	// The blocked subject created no identity, and therefore no account.
	var identities int
	if err := base.pool.QueryRow(context.Background(),
		"SELECT count(*) FROM memory_os.apple_identity WHERE subject = $1", blockedSubject,
	).Scan(&identities); err != nil {
		t.Fatal(err)
	}
	if identities != 0 {
		t.Fatalf("rate-limited login created %d apple_identity rows", identities)
	}
	// And no replay row was consumed for the blocked attempt's code digest.
	blockedCodeDigest := sha256.Sum256([]byte(uniq("code-rl-blocked", runID)))
	var replays int
	if err := base.pool.QueryRow(context.Background(),
		"SELECT count(*) FROM memory_os.apple_replay WHERE scope = 'code' AND digest = $1",
		hex.EncodeToString(blockedCodeDigest[:]),
	).Scan(&replays); err != nil {
		t.Fatal(err)
	}
	if replays != 0 {
		t.Fatalf("rate-limited login consumed %d replay rows", replays)
	}
}
