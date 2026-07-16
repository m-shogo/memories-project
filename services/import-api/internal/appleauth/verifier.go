package appleauth

import (
	"bytes"
	"context"
	"crypto"
	"crypto/rsa"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"strings"
	"time"
)

var (
	ErrMalformedToken         = errors.New("malformed Apple identity token")
	ErrCredentialTooLarge     = errors.New("Apple credential exceeds size limit")
	ErrDuplicateJSONKey       = errors.New("Apple identity token contains duplicate JSON key")
	ErrAlgorithmForbidden     = errors.New("Apple identity token algorithm forbidden")
	ErrKeyNotFound            = errors.New("Apple signing key not found")
	ErrSignatureInvalid       = errors.New("Apple identity token signature invalid")
	ErrIssuerInvalid          = errors.New("Apple identity token issuer invalid")
	ErrAudienceInvalid        = errors.New("Apple identity token audience invalid")
	ErrTokenExpired           = errors.New("Apple identity token expired")
	ErrIssuedAtInvalid        = errors.New("Apple identity token issued-at invalid")
	ErrNonceRequired          = errors.New("Apple identity token nonce required")
	ErrNonceMismatch          = errors.New("Apple identity token nonce mismatch")
	ErrSubjectRequired        = errors.New("Apple identity token subject required")
	ErrCodeBindingMismatch    = errors.New("Apple authorization code binding mismatch")
	ErrAccountBindingConflict = errors.New("Apple account binding conflict")
)

const (
	DefaultIssuer         = "https://appleid.apple.com"
	MaxIdentityTokenBytes = 16 * 1024
	maxJWTHeaderBytes     = 2 * 1024
	maxJWTClaimsBytes     = 12 * 1024
	maxJWTSignatureBytes  = 1024
)

type KeyProvider interface {
	LookupRSAKey(ctx context.Context, kid string, forceRefresh bool) (*rsa.PublicKey, error)
}

type CodeExchangeResult struct {
	Subject     string
	ClientID    string
	RedirectURI *string
}

type CodeExchanger interface {
	Exchange(ctx context.Context, code, clientID string, redirectURI *string) (CodeExchangeResult, error)
}

// ReplayGuard must atomically reject a previously consumed nonce or code digest.
type ReplayGuard interface {
	Consume(ctx context.Context, nonceClaim, authorizationCodeSHA256 string) error
}

type AccountBindingStore interface {
	ResolveOrCreate(ctx context.Context, issuer, subject string) (accountID string, accountEpoch int64, err error)
}

type Input struct {
	IdentityToken       string
	AuthorizationCode   string
	ClientID            string
	ExpectedNonceClaim  string
	OriginalRedirectURI *string
}

type VerifiedIdentity struct {
	Issuer       string
	Subject      string
	Audience     string
	AccountID    string
	AccountEpoch int64
}

type Verifier struct {
	Issuer      string
	Audiences   map[string]struct{}
	ClockSkew   time.Duration
	MaxTokenAge time.Duration
	Now         func() time.Time
	Keys        KeyProvider
	Codes       CodeExchanger
	Replay      ReplayGuard
	Accounts    AccountBindingStore
}

type tokenHeader struct {
	Algorithm string `json:"alg"`
	KeyID     string `json:"kid"`
}

type tokenClaims struct {
	Issuer   string          `json:"iss"`
	Subject  string          `json:"sub"`
	Audience json.RawMessage `json:"aud"`
	Expires  int64           `json:"exp"`
	IssuedAt int64           `json:"iat"`
	Nonce    string          `json:"nonce"`
}

func (v *Verifier) Verify(ctx context.Context, input Input) (VerifiedIdentity, error) {
	if v.Keys == nil || v.Codes == nil || v.Replay == nil || v.Accounts == nil {
		return VerifiedIdentity{}, errors.New("Apple verifier dependencies are incomplete")
	}
	issuer := v.Issuer
	if issuer == "" {
		issuer = DefaultIssuer
	}
	now := time.Now
	if v.Now != nil {
		now = v.Now
	}
	clockSkew := v.ClockSkew
	if clockSkew < 0 || clockSkew > 5*time.Minute {
		return VerifiedIdentity{}, errors.New("invalid Apple verifier clock skew")
	}
	maxAge := v.MaxTokenAge
	if maxAge <= 0 || maxAge > time.Hour {
		return VerifiedIdentity{}, errors.New("invalid Apple verifier max token age")
	}
	if len(input.IdentityToken) > MaxIdentityTokenBytes || len(input.AuthorizationCode) > 4096 || len(input.ClientID) > 255 || len(input.ExpectedNonceClaim) > 256 {
		return VerifiedIdentity{}, ErrCredentialTooLarge
	}
	if input.OriginalRedirectURI != nil && len(*input.OriginalRedirectURI) > 2048 {
		return VerifiedIdentity{}, ErrCredentialTooLarge
	}
	if input.ExpectedNonceClaim == "" {
		return VerifiedIdentity{}, ErrNonceRequired
	}
	if input.AuthorizationCode == "" || input.ClientID == "" {
		return VerifiedIdentity{}, ErrCodeBindingMismatch
	}

	header, claims, signingInput, signature, err := parseCompactToken(input.IdentityToken)
	if err != nil {
		return VerifiedIdentity{}, err
	}
	if header.Algorithm != "RS256" {
		return VerifiedIdentity{}, ErrAlgorithmForbidden
	}
	if header.KeyID == "" {
		return VerifiedIdentity{}, ErrKeyNotFound
	}
	key, err := v.Keys.LookupRSAKey(ctx, header.KeyID, false)
	if errors.Is(err, ErrKeyNotFound) {
		key, err = v.Keys.LookupRSAKey(ctx, header.KeyID, true)
	}
	if err != nil {
		return VerifiedIdentity{}, fmt.Errorf("lookup Apple key: %w", err)
	}
	if err := verifyRS256(key, signingInput, signature); err != nil {
		return VerifiedIdentity{}, err
	}

	if claims.Issuer != issuer {
		return VerifiedIdentity{}, ErrIssuerInvalid
	}
	audiences, err := parseAudience(claims.Audience)
	if err != nil {
		return VerifiedIdentity{}, ErrAudienceInvalid
	}
	matchedAudience := ""
	for _, audience := range audiences {
		if _, ok := v.Audiences[audience]; ok {
			matchedAudience = audience
			break
		}
	}
	if matchedAudience == "" || matchedAudience != input.ClientID {
		return VerifiedIdentity{}, ErrAudienceInvalid
	}
	if claims.Subject == "" {
		return VerifiedIdentity{}, ErrSubjectRequired
	}
	if claims.Nonce == "" {
		return VerifiedIdentity{}, ErrNonceRequired
	}
	if claims.Nonce != input.ExpectedNonceClaim {
		return VerifiedIdentity{}, ErrNonceMismatch
	}

	current := now().UTC()
	expiresAt := time.Unix(claims.Expires, 0)
	issuedAt := time.Unix(claims.IssuedAt, 0)
	if claims.Expires == 0 || current.After(expiresAt.Add(clockSkew)) {
		return VerifiedIdentity{}, ErrTokenExpired
	}
	if claims.IssuedAt == 0 || issuedAt.After(current.Add(clockSkew)) || current.Sub(issuedAt) > maxAge+clockSkew {
		return VerifiedIdentity{}, ErrIssuedAtInvalid
	}

	exchange, err := v.Codes.Exchange(ctx, input.AuthorizationCode, input.ClientID, input.OriginalRedirectURI)
	if err != nil {
		return VerifiedIdentity{}, fmt.Errorf("exchange Apple authorization code: %w", err)
	}
	if exchange.Subject != claims.Subject || exchange.ClientID != input.ClientID {
		return VerifiedIdentity{}, ErrCodeBindingMismatch
	}
	if input.OriginalRedirectURI != nil {
		if exchange.RedirectURI == nil || *exchange.RedirectURI != *input.OriginalRedirectURI {
			return VerifiedIdentity{}, ErrCodeBindingMismatch
		}
	}

	codeDigest := sha256.Sum256([]byte(input.AuthorizationCode))
	if err := v.Replay.Consume(ctx, claims.Nonce, hex.EncodeToString(codeDigest[:])); err != nil {
		return VerifiedIdentity{}, fmt.Errorf("consume Apple nonce/code replay guard: %w", err)
	}
	accountID, accountEpoch, err := v.Accounts.ResolveOrCreate(ctx, claims.Issuer, claims.Subject)
	if err != nil {
		return VerifiedIdentity{}, fmt.Errorf("bind Apple identity: %w", err)
	}
	if accountID == "" || accountEpoch < 0 {
		return VerifiedIdentity{}, ErrAccountBindingConflict
	}

	return VerifiedIdentity{
		Issuer:       claims.Issuer,
		Subject:      claims.Subject,
		Audience:     matchedAudience,
		AccountID:    accountID,
		AccountEpoch: accountEpoch,
	}, nil
}

func parseCompactToken(raw string) (tokenHeader, tokenClaims, []byte, []byte, error) {
	parts := strings.Split(raw, ".")
	if len(parts) != 3 || parts[0] == "" || parts[1] == "" || parts[2] == "" {
		return tokenHeader{}, tokenClaims{}, nil, nil, ErrMalformedToken
	}
	headerBytes, err := base64.RawURLEncoding.DecodeString(parts[0])
	if err != nil {
		return tokenHeader{}, tokenClaims{}, nil, nil, ErrMalformedToken
	}
	if len(headerBytes) > maxJWTHeaderBytes {
		return tokenHeader{}, tokenClaims{}, nil, nil, ErrCredentialTooLarge
	}
	claimsBytes, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return tokenHeader{}, tokenClaims{}, nil, nil, ErrMalformedToken
	}
	if len(claimsBytes) > maxJWTClaimsBytes {
		return tokenHeader{}, tokenClaims{}, nil, nil, ErrCredentialTooLarge
	}
	signature, err := base64.RawURLEncoding.DecodeString(parts[2])
	if err != nil {
		return tokenHeader{}, tokenClaims{}, nil, nil, ErrMalformedToken
	}
	if len(signature) > maxJWTSignatureBytes {
		return tokenHeader{}, tokenClaims{}, nil, nil, ErrCredentialTooLarge
	}
	if err := rejectDuplicateJSONKeys(headerBytes); err != nil {
		return tokenHeader{}, tokenClaims{}, nil, nil, err
	}
	if err := rejectDuplicateJSONKeys(claimsBytes); err != nil {
		return tokenHeader{}, tokenClaims{}, nil, nil, err
	}
	var header tokenHeader
	if err := json.Unmarshal(headerBytes, &header); err != nil {
		return tokenHeader{}, tokenClaims{}, nil, nil, ErrMalformedToken
	}
	var claims tokenClaims
	if err := json.Unmarshal(claimsBytes, &claims); err != nil {
		return tokenHeader{}, tokenClaims{}, nil, nil, ErrMalformedToken
	}
	return header, claims, []byte(parts[0] + "." + parts[1]), signature, nil
}

func rejectDuplicateJSONKeys(data []byte) error {
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.UseNumber()
	if err := consumeJSONValue(decoder); err != nil {
		return err
	}
	if _, err := decoder.Token(); !errors.Is(err, io.EOF) {
		if err == nil {
			return ErrMalformedToken
		}
		return ErrMalformedToken
	}
	return nil
}

func consumeJSONValue(decoder *json.Decoder) error {
	token, err := decoder.Token()
	if err != nil {
		return ErrMalformedToken
	}
	delimiter, isDelimiter := token.(json.Delim)
	if !isDelimiter {
		return nil
	}
	switch delimiter {
	case '{':
		seen := map[string]struct{}{}
		for decoder.More() {
			keyToken, err := decoder.Token()
			if err != nil {
				return ErrMalformedToken
			}
			key, ok := keyToken.(string)
			if !ok {
				return ErrMalformedToken
			}
			if _, exists := seen[key]; exists {
				return fmt.Errorf("%w: %s", ErrDuplicateJSONKey, key)
			}
			seen[key] = struct{}{}
			if err := consumeJSONValue(decoder); err != nil {
				return err
			}
		}
		end, err := decoder.Token()
		if err != nil || end != json.Delim('}') {
			return ErrMalformedToken
		}
	case '[':
		for decoder.More() {
			if err := consumeJSONValue(decoder); err != nil {
				return err
			}
		}
		end, err := decoder.Token()
		if err != nil || end != json.Delim(']') {
			return ErrMalformedToken
		}
	default:
		return ErrMalformedToken
	}
	return nil
}

func verifyRS256(key *rsa.PublicKey, signingInput, signature []byte) error {
	if key == nil || key.N == nil || key.E < 3 {
		return ErrKeyNotFound
	}
	digest := sha256.Sum256(signingInput)
	if err := rsa.VerifyPKCS1v15(key, crypto.SHA256, digest[:], signature); err != nil {
		return ErrSignatureInvalid
	}
	return nil
}

func parseAudience(raw json.RawMessage) ([]string, error) {
	var single string
	if err := json.Unmarshal(raw, &single); err == nil && single != "" {
		return []string{single}, nil
	}
	var multiple []string
	if err := json.Unmarshal(raw, &multiple); err != nil || len(multiple) == 0 {
		return nil, ErrAudienceInvalid
	}
	for _, value := range multiple {
		if value == "" {
			return nil, ErrAudienceInvalid
		}
	}
	return multiple, nil
}
