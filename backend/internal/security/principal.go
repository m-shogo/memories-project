package security

import (
	"errors"
	"fmt"
	"strings"
)

var (
	ErrUnverifiedPrincipal = errors.New("principal is not verified")
	ErrInvalidAccountID    = errors.New("invalid account id")
	ErrInvalidSubject      = errors.New("invalid identity subject")
	ErrInvalidEpoch        = errors.New("invalid account epoch")
)

// Principal is the only identity type allowed to enter tenant-scoped services.
// It must be created from a server-verified identity token, never from request
// body identity fields.
type Principal struct {
	accountID string
	epoch     int64
	issuer    string
	subject   string
	verified  bool
}

// NewVerifiedPrincipal is intentionally narrow: callers must first complete
// provider signature, issuer, audience, time, nonce and code-replay checks.
func NewVerifiedPrincipal(accountID string, epoch int64, issuer, subject string) (Principal, error) {
	accountID = strings.TrimSpace(accountID)
	issuer = strings.TrimSpace(issuer)
	subject = strings.TrimSpace(subject)

	if len(accountID) < 16 || len(accountID) > 128 {
		return Principal{}, ErrInvalidAccountID
	}
	if epoch < 0 {
		return Principal{}, ErrInvalidEpoch
	}
	if issuer == "" || subject == "" || len(subject) > 255 {
		return Principal{}, ErrInvalidSubject
	}

	return Principal{
		accountID: accountID,
		epoch:     epoch,
		issuer:    issuer,
		subject:   subject,
		verified:  true,
	}, nil
}

func (p Principal) Validate() error {
	if !p.verified {
		return ErrUnverifiedPrincipal
	}
	if p.accountID == "" || p.issuer == "" || p.subject == "" || p.epoch < 0 {
		return fmt.Errorf("%w: incomplete verified principal", ErrUnverifiedPrincipal)
	}
	return nil
}

func (p Principal) AccountID() string { return p.accountID }
func (p Principal) Epoch() int64       { return p.epoch }
func (p Principal) Issuer() string     { return p.issuer }
func (p Principal) Subject() string    { return p.subject }
