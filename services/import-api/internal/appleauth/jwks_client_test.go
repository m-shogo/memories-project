package appleauth

import (
	"context"
	"crypto/rand"
	"crypto/rsa"
	"encoding/base64"
	"encoding/json"
	"math/big"
	"net/http"
	"strings"
	"sync/atomic"
	"testing"
	"time"
)

type roundTripFunc func(*http.Request) (*http.Response, error)

func (f roundTripFunc) RoundTrip(r *http.Request) (*http.Response, error) { return f(r) }

func TestJWKSClientFetchesAndCachesAppleSigningKey(t *testing.T) {
	privateKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatal(err)
	}
	body := jwksBody(t, "kid-1", &privateKey.PublicKey)
	var requests atomic.Int32
	client := &http.Client{Transport: roundTripFunc(func(request *http.Request) (*http.Response, error) {
		requests.Add(1)
		if request.URL.String() != appleJWKSURL {
			t.Fatalf("unexpected URL: %s", request.URL)
		}
		return &http.Response{StatusCode: http.StatusOK, Header: http.Header{"Cache-Control": []string{"max-age=3600"}}, Body: ioNopCloser{strings.NewReader(body)}}, nil
	})}
	jwks := NewAppleJWKSClient(client)
	jwks.now = func() time.Time { return time.Unix(1_800_000_000, 0).UTC() }
	first, err := jwks.LookupRSAKey(context.Background(), "kid-1", false)
	if err != nil {
		t.Fatal(err)
	}
	second, err := jwks.LookupRSAKey(context.Background(), "kid-1", false)
	if err != nil {
		t.Fatal(err)
	}
	if first.N.Cmp(privateKey.N) != 0 || second.N.Cmp(privateKey.N) != 0 {
		t.Fatal("key mismatch")
	}
	if requests.Load() != 1 {
		t.Fatalf("expected one request, got %d", requests.Load())
	}
}

func TestJWKSClientForceRefreshesUnknownKey(t *testing.T) {
	privateKey, _ := rsa.GenerateKey(rand.Reader, 2048)
	body := jwksBody(t, "known-kid", &privateKey.PublicKey)
	var requests atomic.Int32
	client := &http.Client{Transport: roundTripFunc(func(*http.Request) (*http.Response, error) {
		requests.Add(1)
		return &http.Response{StatusCode: http.StatusOK, Header: make(http.Header), Body: ioNopCloser{strings.NewReader(body)}}, nil
	})}
	jwks := NewAppleJWKSClient(client)
	jwks.now = func() time.Time { return time.Unix(1_800_000_000, 0).UTC() }
	if _, err := jwks.LookupRSAKey(context.Background(), "unknown", false); err == nil {
		t.Fatal("expected unknown key")
	}
	if _, err := jwks.LookupRSAKey(context.Background(), "unknown", true); err == nil {
		t.Fatal("expected unknown key after refresh")
	}
	if requests.Load() != 2 {
		t.Fatalf("expected two requests, got %d", requests.Load())
	}
}

func jwksBody(t *testing.T, kid string, key *rsa.PublicKey) string {
	t.Helper()
	exponent := big.NewInt(int64(key.E)).Bytes()
	document := map[string]any{"keys": []map[string]any{{"kty": "RSA", "kid": kid, "use": "sig", "alg": "RS256", "n": base64.RawURLEncoding.EncodeToString(key.N.Bytes()), "e": base64.RawURLEncoding.EncodeToString(exponent)}}}
	value, err := json.Marshal(document)
	if err != nil {
		t.Fatal(err)
	}
	return string(value)
}

type ioNopCloser struct{ *strings.Reader }

func (ioNopCloser) Close() error { return nil }
