package appleauth

import (
	"crypto/ecdsa"
	"crypto/rand"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"errors"
	"fmt"
	"time"
)

// ClientSecretConfig is the developer-account material Apple requires to sign a
// client secret. The private key is an EC P-256 key from an Apple .p8 file; it
// is held only in memory, never logged, and never serialized anywhere.
type ClientSecretConfig struct {
	TeamID   string
	KeyID    string
	ClientID string
	// PrivateKey is the parsed .p8 key. Callers parse it with ParseP8PrivateKey
	// and keep the PEM bytes out of every other structure.
	PrivateKey *ecdsa.PrivateKey
}

var (
	ErrInvalidClientSecretConfig = errors.New("invalid Apple client secret configuration")
	ErrInvalidP8Key              = errors.New("invalid Apple .p8 private key")
)

// ParseP8PrivateKey parses the PKCS#8 EC private key from an Apple .p8 file.
// The raw bytes are the sole responsibility of the caller and must never be
// logged; this function returns only the parsed key.
func ParseP8PrivateKey(pemBytes []byte) (*ecdsa.PrivateKey, error) {
	block, _ := pem.Decode(pemBytes)
	if block == nil {
		return nil, fmt.Errorf("%w: not PEM", ErrInvalidP8Key)
	}
	parsed, err := x509.ParsePKCS8PrivateKey(block.Bytes)
	if err != nil {
		return nil, fmt.Errorf("%w: %v", ErrInvalidP8Key, err)
	}
	key, ok := parsed.(*ecdsa.PrivateKey)
	if !ok {
		return nil, fmt.Errorf("%w: not an EC key", ErrInvalidP8Key)
	}
	if key.Curve.Params().BitSize != 256 {
		return nil, fmt.Errorf("%w: curve is not P-256", ErrInvalidP8Key)
	}
	return key, nil
}

// clientSecretTTL is how long a generated secret is valid. Apple caps client
// secrets at six months; a short life limits exposure if one ever leaks, and it
// is regenerated per exchange, so nothing depends on reuse.
const clientSecretTTL = 30 * time.Minute

// GenerateClientSecret builds the ES256-signed JWT Apple's token endpoint
// requires: header {alg:ES256, kid:KeyID}, claims {iss:TeamID, iat, exp,
// aud:issuer, sub:ClientID}. `now` is injected for deterministic tests.
func (c ClientSecretConfig) GenerateClientSecret(issuer string, now time.Time) (string, error) {
	if c.TeamID == "" || len(c.TeamID) > 64 || c.KeyID == "" || len(c.KeyID) > 64 ||
		c.ClientID == "" || len(c.ClientID) > 255 || c.PrivateKey == nil {
		return "", ErrInvalidClientSecretConfig
	}
	if issuer == "" {
		issuer = DefaultIssuer
	}
	issuedAt := now.UTC()
	header := map[string]string{"alg": "ES256", "kid": c.KeyID, "typ": "JWT"}
	claims := map[string]any{
		"iss": c.TeamID,
		"iat": issuedAt.Unix(),
		"exp": issuedAt.Add(clientSecretTTL).Unix(),
		"aud": issuer,
		"sub": c.ClientID,
	}
	headerJSON, err := json.Marshal(header)
	if err != nil {
		return "", err
	}
	claimsJSON, err := json.Marshal(claims)
	if err != nil {
		return "", err
	}
	signingInput := base64.RawURLEncoding.EncodeToString(headerJSON) + "." +
		base64.RawURLEncoding.EncodeToString(claimsJSON)

	digest := sha256.Sum256([]byte(signingInput))
	r, s, err := ecdsa.Sign(rand.Reader, c.PrivateKey, digest[:])
	if err != nil {
		return "", fmt.Errorf("sign Apple client secret: %w", err)
	}
	// ES256 signatures are the fixed-width big-endian R||S concatenation, not
	// the ASN.1 form ecdsa.Sign returns as (r, s) integers.
	signature := make([]byte, 64)
	r.FillBytes(signature[:32])
	s.FillBytes(signature[32:])
	return signingInput + "." + base64.RawURLEncoding.EncodeToString(signature), nil
}
