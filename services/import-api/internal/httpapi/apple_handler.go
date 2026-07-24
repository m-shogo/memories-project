package httpapi

import (
	"context"
	"errors"
	"net/http"

	"github.com/m-shogo/memories-project/services/import-api/internal/appleauth"
)

// AppleLoginService turns a Sign in with Apple request into a Memory OS session.
type AppleLoginService interface {
	Login(context.Context, appleauth.Input) (appleauth.LoginResult, error)
}

type AppleHandler struct {
	Service     AppleLoginService
	MaxJSONBody int64
}

func (h AppleHandler) Register(mux *http.ServeMux) {
	mux.HandleFunc("POST /v1/auth/apple", h.login)
}

// appleLoginRequest is the client-supplied material. None of it is trusted as
// authority: the account id and email are deliberately absent, and every value
// here is validated by the verifier against Apple's signed token before it can
// influence anything.
type appleLoginRequest struct {
	IdentityToken     string  `json:"identityToken"`
	AuthorizationCode string  `json:"authorizationCode"`
	ClientID          string  `json:"clientId"`
	ExpectedNonce     string  `json:"nonce"`
	RedirectURI       *string `json:"redirectUri,omitempty"`
}

// appleLoginResponse returns only the session token and the resolved account.
// No Apple material, no token internals.
type appleLoginResponse struct {
	SessionToken string `json:"sessionToken"`
	AccountID    string `json:"accountId"`
}

func (h AppleHandler) login(writer http.ResponseWriter, request *http.Request) {
	if h.Service == nil {
		writeProblem(writer, http.StatusServiceUnavailable, "SEC_SERVICE_UNAVAILABLE")
		return
	}
	var body appleLoginRequest
	if err := decodeStrictJSON(writer, request, h.bodyLimit(), &body); err != nil {
		writeProblem(writer, http.StatusBadRequest, "SEC_APPLE_LOGIN_REQUEST_INVALID")
		return
	}
	result, err := h.Service.Login(request.Context(), appleauth.Input{
		IdentityToken:       body.IdentityToken,
		AuthorizationCode:   body.AuthorizationCode,
		ClientID:            body.ClientID,
		ExpectedNonceClaim:  body.ExpectedNonce,
		OriginalRedirectURI: body.RedirectURI,
	})
	if err != nil {
		writeAppleLoginError(writer, err)
		return
	}
	writeJSON(writer, http.StatusOK, appleLoginResponse{
		SessionToken: result.SessionToken,
		AccountID:    result.AccountID,
	})
}

func (h AppleHandler) bodyLimit() int64 {
	if h.MaxJSONBody <= 0 || h.MaxJSONBody > 1024*1024 {
		return defaultMaxJSONBody
	}
	return h.MaxJSONBody
}

// writeAppleLoginError maps verifier and login errors to stable problem codes.
// The distinctions matter: a malformed request, a rejected token, a replayed
// credential and an account conflict each need a different client response, but
// none of them ever leaks which Apple check failed beyond the category.
func writeAppleLoginError(writer http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, appleauth.ErrCredentialTooLarge),
		errors.Is(err, appleauth.ErrMalformedToken),
		errors.Is(err, appleauth.ErrDuplicateJSONKey),
		errors.Is(err, appleauth.ErrNonceRequired),
		errors.Is(err, appleauth.ErrSubjectRequired):
		writeProblem(writer, http.StatusBadRequest, "SEC_APPLE_LOGIN_REQUEST_INVALID")
	case errors.Is(err, appleauth.ErrAlgorithmForbidden),
		errors.Is(err, appleauth.ErrKeyNotFound),
		errors.Is(err, appleauth.ErrSignatureInvalid),
		errors.Is(err, appleauth.ErrIssuerInvalid),
		errors.Is(err, appleauth.ErrAudienceInvalid),
		errors.Is(err, appleauth.ErrTokenExpired),
		errors.Is(err, appleauth.ErrIssuedAtInvalid),
		errors.Is(err, appleauth.ErrNonceMismatch),
		errors.Is(err, appleauth.ErrCodeBindingMismatch),
		errors.Is(err, appleauth.ErrTokenEndpointRejected),
		errors.Is(err, appleauth.ErrTokenResponseMalformed):
		// The identity or the code did not check out. One code, so a caller
		// cannot probe which specific check failed.
		writeProblem(writer, http.StatusUnauthorized, "SEC_APPLE_LOGIN_REJECTED")
	case errors.Is(err, appleauth.ErrAccountBindingConflict):
		writeProblem(writer, http.StatusConflict, "SEC_APPLE_ACCOUNT_CONFLICT")
	case errors.Is(err, appleauth.ErrTokenEndpointUnavailable),
		errors.Is(err, appleauth.ErrSessionIssuance),
		errors.Is(err, appleauth.ErrLoginUnavailable):
		// Nothing the client did is wrong; Apple or our own dependency was
		// unavailable, and the request is safe to retry.
		writeProblem(writer, http.StatusServiceUnavailable, "SEC_SERVICE_UNAVAILABLE")
	default:
		// A replay (Postgres unique violation surfaced through Consume) and any
		// other unclassified failure fail closed as a rejection rather than a
		// 500, so a replayed credential never looks like a transient error the
		// client should retry.
		writeProblem(writer, http.StatusUnauthorized, "SEC_APPLE_LOGIN_REJECTED")
	}
}
