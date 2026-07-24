package appleauth

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

var (
	ErrTokenEndpointUnavailable = errors.New("Apple token endpoint unavailable")
	ErrTokenEndpointRejected    = errors.New("Apple token endpoint rejected the code")
	ErrTokenResponseMalformed   = errors.New("Apple token endpoint response malformed")
)

// TokenClient exchanges an authorization code at Apple's token endpoint. It
// satisfies CodeExchanger. The client secret is regenerated per exchange from
// in-memory developer material and is never stored or logged.
type TokenClient struct {
	Endpoint     string
	Issuer       string
	ClientSecret ClientSecretConfig
	HTTPClient   *http.Client
	Now          func() time.Time
}

// tokenEndpointResponse is the subset of Apple's response we consume. Apple's
// token endpoint is reached directly over TLS, so its id_token is trusted by
// channel; its subject and audience are read from the token's claims and
// cross-checked by the verifier against the client-supplied identity token.
type tokenEndpointResponse struct {
	IDToken string `json:"id_token"`
	Error   string `json:"error"`
}

func (t TokenClient) Exchange(ctx context.Context, code, clientID string, redirectURI *string) (CodeExchangeResult, error) {
	if t.Endpoint == "" || code == "" || clientID == "" {
		return CodeExchangeResult{}, ErrTokenEndpointUnavailable
	}
	if len(code) > 4096 || len(clientID) > 255 {
		return CodeExchangeResult{}, ErrCredentialTooLarge
	}
	now := time.Now
	if t.Now != nil {
		now = t.Now
	}
	issuer := t.Issuer
	if issuer == "" {
		issuer = DefaultIssuer
	}
	secret, err := t.ClientSecret.GenerateClientSecret(issuer, now())
	if err != nil {
		return CodeExchangeResult{}, err
	}

	form := url.Values{}
	form.Set("grant_type", "authorization_code")
	form.Set("code", code)
	form.Set("client_id", clientID)
	form.Set("client_secret", secret)
	if redirectURI != nil {
		form.Set("redirect_uri", *redirectURI)
	}

	httpClient := t.HTTPClient
	if httpClient == nil {
		httpClient = &http.Client{Timeout: 5 * time.Second}
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, t.Endpoint, strings.NewReader(form.Encode()))
	if err != nil {
		return CodeExchangeResult{}, err
	}
	request.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	request.Header.Set("Accept", "application/json")

	response, err := httpClient.Do(request)
	if err != nil {
		// The error may embed the request URL but never the form body, so the
		// secret and code are not exposed by wrapping it.
		return CodeExchangeResult{}, fmt.Errorf("%w: %v", ErrTokenEndpointUnavailable, err)
	}
	defer func() {
		_, _ = io.Copy(io.Discard, io.LimitReader(response.Body, 1<<16))
		_ = response.Body.Close()
	}()

	payload, err := io.ReadAll(io.LimitReader(response.Body, 1<<16))
	if err != nil {
		return CodeExchangeResult{}, fmt.Errorf("%w: %v", ErrTokenEndpointUnavailable, err)
	}
	if response.StatusCode != http.StatusOK {
		// Apple returns 400 with an error code for a bad or reused code. The
		// error code is Apple's own token (e.g. "invalid_grant"), not user data.
		return CodeExchangeResult{}, ErrTokenEndpointRejected
	}

	var decoded tokenEndpointResponse
	if err := json.Unmarshal(payload, &decoded); err != nil {
		return CodeExchangeResult{}, ErrTokenResponseMalformed
	}
	if decoded.Error != "" || decoded.IDToken == "" {
		return CodeExchangeResult{}, ErrTokenEndpointRejected
	}

	subject, audience, err := subjectAndAudienceFromIDToken(decoded.IDToken)
	if err != nil {
		return CodeExchangeResult{}, err
	}
	if audience != clientID {
		// The token Apple issued for this exchange must be for the client we
		// authenticated as, or the binding is wrong.
		return CodeExchangeResult{}, ErrCodeBindingMismatch
	}
	return CodeExchangeResult{
		Subject:  subject,
		ClientID: clientID,
		// Apple does not echo redirect_uri; a successful exchange means Apple
		// accepted the one we sent (or none), so we report it back for the
		// verifier's equality check. Apple's own validation is the real gate.
		RedirectURI: redirectURI,
	}, nil
}

// subjectAndAudienceFromIDToken reads sub and aud from the token-endpoint
// id_token claims. The token arrived directly from Apple over TLS, so its claims
// are trusted by channel; this only decodes, it does not re-verify a signature.
func subjectAndAudienceFromIDToken(idToken string) (subject, audience string, err error) {
	if len(idToken) > MaxIdentityTokenBytes {
		return "", "", ErrCredentialTooLarge
	}
	parts := strings.Split(idToken, ".")
	if len(parts) != 3 {
		return "", "", ErrTokenResponseMalformed
	}
	claimsBytes, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return "", "", ErrTokenResponseMalformed
	}
	var claims struct {
		Subject  string          `json:"sub"`
		Audience json.RawMessage `json:"aud"`
	}
	if err := json.Unmarshal(claimsBytes, &claims); err != nil {
		return "", "", ErrTokenResponseMalformed
	}
	if claims.Subject == "" {
		return "", "", ErrSubjectRequired
	}
	audiences, err := parseAudience(claims.Audience)
	if err != nil || len(audiences) == 0 {
		return "", "", ErrAudienceInvalid
	}
	return claims.Subject, audiences[0], nil
}
