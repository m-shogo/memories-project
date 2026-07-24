package appleauth

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"math/big"
	"strings"
	"testing"
	"time"
)

func testP8(t *testing.T) ([]byte, *ecdsa.PrivateKey) {
	t.Helper()
	key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	der, err := x509.MarshalPKCS8PrivateKey(key)
	if err != nil {
		t.Fatal(err)
	}
	return pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: der}), key
}

func TestParseP8RejectsNonECAndBadPEM(t *testing.T) {
	if _, err := ParseP8PrivateKey([]byte("not pem")); err == nil {
		t.Fatal("non-PEM accepted")
	}
	rsaPem := pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: []byte("garbage")})
	if _, err := ParseP8PrivateKey(rsaPem); err == nil {
		t.Fatal("garbage PKCS8 accepted")
	}
}

func TestGenerateClientSecretIsVerifiableES256(t *testing.T) {
	pemBytes, key := testP8(t)
	parsed, err := ParseP8PrivateKey(pemBytes)
	if err != nil {
		t.Fatal(err)
	}
	config := ClientSecretConfig{TeamID: "TEAM123456", KeyID: "KEY1234567", ClientID: "com.memoryos.app", PrivateKey: parsed}
	now := time.Unix(1_800_000_000, 0)
	secret, err := config.GenerateClientSecret(DefaultIssuer, now)
	if err != nil {
		t.Fatal(err)
	}

	parts := strings.Split(secret, ".")
	if len(parts) != 3 {
		t.Fatalf("client secret is not a compact JWT: %q", secret)
	}
	headerBytes, _ := base64.RawURLEncoding.DecodeString(parts[0])
	var header map[string]string
	_ = json.Unmarshal(headerBytes, &header)
	if header["alg"] != "ES256" || header["kid"] != "KEY1234567" {
		t.Fatalf("unexpected header: %v", header)
	}
	claimsBytes, _ := base64.RawURLEncoding.DecodeString(parts[1])
	var claims map[string]any
	_ = json.Unmarshal(claimsBytes, &claims)
	if claims["iss"] != "TEAM123456" || claims["sub"] != "com.memoryos.app" || claims["aud"] != DefaultIssuer {
		t.Fatalf("unexpected claims: %v", claims)
	}

	// The signature must verify against the key's public half, in fixed-width
	// R||S form.
	sig, _ := base64.RawURLEncoding.DecodeString(parts[2])
	if len(sig) != 64 {
		t.Fatalf("signature is not 64 bytes: %d", len(sig))
	}
	r := new(big.Int).SetBytes(sig[:32])
	s := new(big.Int).SetBytes(sig[32:])
	digest := sha256.Sum256([]byte(parts[0] + "." + parts[1]))
	if !ecdsa.Verify(&key.PublicKey, digest[:], r, s) {
		t.Fatal("client secret signature did not verify")
	}
}

func TestGenerateClientSecretRejectsIncompleteConfig(t *testing.T) {
	_, key := testP8(t)
	for _, config := range []ClientSecretConfig{
		{KeyID: "k", ClientID: "c", PrivateKey: key},
		{TeamID: "t", ClientID: "c", PrivateKey: key},
		{TeamID: "t", KeyID: "k", PrivateKey: key},
		{TeamID: "t", KeyID: "k", ClientID: "c"},
	} {
		if _, err := config.GenerateClientSecret(DefaultIssuer, time.Now()); err == nil {
			t.Fatalf("incomplete config accepted: %+v", config)
		}
	}
}
