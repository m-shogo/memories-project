package appleauth

import (
	"context"
	"crypto/rsa"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math/big"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"
)

const (
	appleJWKSURL         = "https://appleid.apple.com/auth/keys"
	maxJWKSResponse      = 256 * 1024
	defaultJWKSMaxAge    = time.Hour
	maxAllowedJWKSMaxAge = 24 * time.Hour
)

type JWKSClient struct {
	httpClient *http.Client
	now        func() time.Time

	mu        sync.Mutex
	keys      map[string]*rsaPublicKeyAlias
	expiresAt time.Time
}

type rsaPublicKeyAlias struct {
	N *big.Int
	E int
}

type jwksDocument struct {
	Keys []jwk `json:"keys"`
}

type jwk struct {
	KeyType   string `json:"kty"`
	KeyID     string `json:"kid"`
	Use       string `json:"use"`
	Algorithm string `json:"alg"`
	Modulus   string `json:"n"`
	Exponent  string `json:"e"`
}

func NewAppleJWKSClient(client *http.Client) *JWKSClient {
	if client == nil {
		client = &http.Client{Timeout: 5 * time.Second}
	} else {
		copyClient := *client
		client = &copyClient
		if client.Timeout <= 0 || client.Timeout > 10*time.Second {
			client.Timeout = 5 * time.Second
		}
	}
	previousRedirect := client.CheckRedirect
	client.CheckRedirect = func(request *http.Request, via []*http.Request) error {
		if request.URL.Scheme != "https" || request.URL.Host != "appleid.apple.com" {
			return errors.New("Apple JWKS redirect left the allowed origin")
		}
		if len(via) > 2 {
			return errors.New("too many Apple JWKS redirects")
		}
		if previousRedirect != nil {
			return previousRedirect(request, via)
		}
		return nil
	}
	return &JWKSClient{httpClient: client, now: time.Now, keys: map[string]*rsaPublicKeyAlias{}}
}

func (c *JWKSClient) LookupRSAKey(ctx context.Context, kid string, forceRefresh bool) (*rsa.PublicKey, error) {
	if kid == "" || len(kid) > 128 {
		return nil, ErrKeyNotFound
	}
	c.mu.Lock()
	defer c.mu.Unlock()

	now := c.now().UTC()
	if !forceRefresh && now.Before(c.expiresAt) {
		if key := c.keys[kid]; key != nil {
			return &rsa.PublicKey{N: new(big.Int).Set(key.N), E: key.E}, nil
		}
		return nil, ErrKeyNotFound
	}
	if err := c.refreshLocked(ctx, now); err != nil {
		return nil, err
	}
	key := c.keys[kid]
	if key == nil {
		return nil, ErrKeyNotFound
	}
	return &rsa.PublicKey{N: new(big.Int).Set(key.N), E: key.E}, nil
}

func (c *JWKSClient) refreshLocked(ctx context.Context, now time.Time) error {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, appleJWKSURL, nil)
	if err != nil {
		return fmt.Errorf("create Apple JWKS request: %w", err)
	}
	request.Header.Set("Accept", "application/json")
	response, err := c.httpClient.Do(request)
	if err != nil {
		return fmt.Errorf("fetch Apple JWKS: %w", err)
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		_, _ = io.Copy(io.Discard, io.LimitReader(response.Body, 4096))
		return fmt.Errorf("fetch Apple JWKS: unexpected status %d", response.StatusCode)
	}
	body, err := io.ReadAll(io.LimitReader(response.Body, maxJWKSResponse+1))
	if err != nil {
		return fmt.Errorf("read Apple JWKS: %w", err)
	}
	if len(body) > maxJWKSResponse {
		return errors.New("Apple JWKS response exceeds size limit")
	}
	var document jwksDocument
	decoder := json.NewDecoder(strings.NewReader(string(body)))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&document); err != nil {
		return fmt.Errorf("decode Apple JWKS: %w", err)
	}
	if len(document.Keys) == 0 || len(document.Keys) > 32 {
		return errors.New("Apple JWKS key count is invalid")
	}
	keys := make(map[string]*rsaPublicKeyAlias, len(document.Keys))
	for _, item := range document.Keys {
		if item.KeyType != "RSA" || item.Algorithm != "RS256" || item.Use != "sig" || item.KeyID == "" {
			continue
		}
		key, err := decodeRSAJWK(item)
		if err != nil {
			continue
		}
		if _, duplicate := keys[item.KeyID]; duplicate {
			return errors.New("Apple JWKS contains a duplicate key ID")
		}
		keys[item.KeyID] = &rsaPublicKeyAlias{N: key.N, E: key.E}
	}
	if len(keys) == 0 {
		return errors.New("Apple JWKS contained no usable signing keys")
	}
	c.keys = keys
	c.expiresAt = now.Add(cacheMaxAge(response.Header.Get("Cache-Control")))
	return nil
}

func decodeRSAJWK(item jwk) (*rsa.PublicKey, error) {
	modulusBytes, err := base64.RawURLEncoding.DecodeString(item.Modulus)
	if err != nil || len(modulusBytes) == 0 {
		return nil, errors.New("invalid RSA modulus")
	}
	exponentBytes, err := base64.RawURLEncoding.DecodeString(item.Exponent)
	if err != nil || len(exponentBytes) == 0 || len(exponentBytes) > 4 {
		return nil, errors.New("invalid RSA exponent")
	}
	exponent := 0
	for _, value := range exponentBytes {
		exponent = exponent<<8 | int(value)
	}
	modulus := new(big.Int).SetBytes(modulusBytes)
	if modulus.BitLen() < 2048 || exponent < 3 || exponent%2 == 0 {
		return nil, errors.New("weak RSA signing key")
	}
	return &rsa.PublicKey{N: modulus, E: exponent}, nil
}

func cacheMaxAge(cacheControl string) time.Duration {
	for _, directive := range strings.Split(cacheControl, ",") {
		parts := strings.SplitN(strings.TrimSpace(directive), "=", 2)
		if len(parts) != 2 || strings.ToLower(parts[0]) != "max-age" {
			continue
		}
		seconds, err := strconv.ParseInt(strings.Trim(parts[1], `"`), 10, 64)
		if err != nil || seconds <= 0 {
			continue
		}
		value := time.Duration(seconds) * time.Second
		if value > maxAllowedJWKSMaxAge {
			return maxAllowedJWKSMaxAge
		}
		return value
	}
	return defaultJWKSMaxAge
}
