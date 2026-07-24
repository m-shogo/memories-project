package appleauth

import (
	"context"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func tokenClientECKey(t *testing.T) *ecdsa.PrivateKey {
	t.Helper()
	key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	return key
}

func idTokenWith(sub, aud string) string {
	header := base64.RawURLEncoding.EncodeToString([]byte(`{"alg":"RS256","kid":"k"}`))
	claims, _ := json.Marshal(map[string]any{"sub": sub, "aud": aud})
	return header + "." + base64.RawURLEncoding.EncodeToString(claims) + ".sig"
}

func newTokenClient(t *testing.T, handler http.HandlerFunc) (TokenClient, *httptest.Server) {
	server := httptest.NewServer(handler)
	t.Cleanup(server.Close)
	return TokenClient{
		Endpoint: server.URL,
		Issuer:   DefaultIssuer,
		ClientSecret: ClientSecretConfig{
			TeamID: "t", KeyID: "k", ClientID: "com.memoryos.app", PrivateKey: tokenClientECKey(t),
		},
		HTTPClient: server.Client(),
		Now:        func() time.Time { return time.Unix(1_800_000_000, 0) },
	}, server
}

func TestTokenClientReturnsSubjectAndAudience(t *testing.T) {
	client, _ := newTokenClient(t, func(w http.ResponseWriter, r *http.Request) {
		if r.FormValue("grant_type") != "authorization_code" || r.FormValue("client_secret") == "" {
			w.WriteHeader(http.StatusBadRequest)
			return
		}
		_ = json.NewEncoder(w).Encode(map[string]any{"id_token": idTokenWith("apple-sub-1", "com.memoryos.app")})
	})
	result, err := client.Exchange(context.Background(), "code-1", "com.memoryos.app", nil)
	if err != nil {
		t.Fatal(err)
	}
	if result.Subject != "apple-sub-1" || result.ClientID != "com.memoryos.app" {
		t.Fatalf("unexpected result: %+v", result)
	}
}

func TestTokenClientMapsAppleRejection(t *testing.T) {
	client, _ := newTokenClient(t, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusBadRequest)
		_, _ = w.Write([]byte(`{"error":"invalid_grant"}`))
	})
	_, err := client.Exchange(context.Background(), "code-1", "com.memoryos.app", nil)
	if !errors.Is(err, ErrTokenEndpointRejected) {
		t.Fatalf("error = %v, want ErrTokenEndpointRejected", err)
	}
}

func TestTokenClientRejectsMalformedResponse(t *testing.T) {
	client, _ := newTokenClient(t, func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte("not json"))
	})
	_, err := client.Exchange(context.Background(), "code-1", "com.memoryos.app", nil)
	if !errors.Is(err, ErrTokenResponseMalformed) {
		t.Fatalf("error = %v, want ErrTokenResponseMalformed", err)
	}
}

func TestTokenClientRejectsAudienceMismatch(t *testing.T) {
	client, _ := newTokenClient(t, func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(map[string]any{"id_token": idTokenWith("apple-sub-1", "com.someone.else")})
	})
	_, err := client.Exchange(context.Background(), "code-1", "com.memoryos.app", nil)
	if !errors.Is(err, ErrCodeBindingMismatch) {
		t.Fatalf("error = %v, want ErrCodeBindingMismatch", err)
	}
}

func TestTokenClientEchoesRedirectURI(t *testing.T) {
	client, _ := newTokenClient(t, func(w http.ResponseWriter, r *http.Request) {
		if r.FormValue("redirect_uri") != "https://app.example/cb" {
			w.WriteHeader(http.StatusBadRequest)
			return
		}
		_ = json.NewEncoder(w).Encode(map[string]any{"id_token": idTokenWith("apple-sub-1", "com.memoryos.app")})
	})
	redirect := "https://app.example/cb"
	result, err := client.Exchange(context.Background(), "code-1", "com.memoryos.app", &redirect)
	if err != nil {
		t.Fatal(err)
	}
	if result.RedirectURI == nil || *result.RedirectURI != redirect {
		t.Fatalf("redirect not echoed: %+v", result.RedirectURI)
	}
}
