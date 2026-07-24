package appleauth

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

// SessionIssuer issues a Memory OS session for a verified account. It is
// satisfied by authstore.Store; the interface keeps this package free of a
// dependency on the concrete store.
type SessionIssuer interface {
	Issue(ctx context.Context, accountID string, accountEpoch int64, authority security.Authority, ttl time.Duration) (token string, err error)
}

// LoginService turns a verified Apple identity into a Memory OS session. It owns
// no policy of its own beyond composition: the Verifier enforces every token
// and binding rule, and the SessionIssuer owns session semantics.
type LoginService struct {
	Verifier   *Verifier
	Sessions   SessionIssuer
	SessionTTL time.Duration
	Authority  security.Authority
}

var (
	ErrLoginUnavailable = errors.New("apple login service is unavailable")
	ErrSessionIssuance  = errors.New("apple login could not issue a session")
)

// LoginResult is what the account holder needs after a successful sign-in: a
// session token and whether this created their account. It carries no token
// internals and no Apple material.
type LoginResult struct {
	SessionToken string
	AccountID    string
	AccountEpoch int64
}

func (s LoginService) Login(ctx context.Context, input Input) (LoginResult, error) {
	if s.Verifier == nil || s.Sessions == nil {
		return LoginResult{}, ErrLoginUnavailable
	}
	authority := s.Authority
	if authority == "" {
		authority = security.AuthorityIOSUser
	}
	ttl := s.SessionTTL
	if ttl <= 0 {
		ttl = 24 * time.Hour
	}

	identity, err := s.Verifier.Verify(ctx, input)
	if err != nil {
		return LoginResult{}, err
	}

	token, err := s.Sessions.Issue(ctx, identity.AccountID, identity.AccountEpoch, authority, ttl)
	if err != nil {
		// The identity is verified and the account exists; only session
		// issuance failed. Report it distinctly so the handler can return a
		// retryable error rather than an auth failure. The account is not left
		// half-provisioned: provisioning committed before this point, and a
		// retry resolves the same account.
		return LoginResult{}, fmt.Errorf("%w: %v", ErrSessionIssuance, err)
	}
	return LoginResult{
		SessionToken: token,
		AccountID:    identity.AccountID,
		AccountEpoch: identity.AccountEpoch,
	}, nil
}
