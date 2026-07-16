package security

import (
	"errors"
	"fmt"
)

// Authority is the verified server-side authority attached to a request or job.
type Authority string

const (
	AuthorityIOSUser        Authority = "ios_user_access_token"
	AuthorityIOSDevice      Authority = "ios_device_session"
	AuthorityBrowserPairing Authority = "browser_pairing_token"
	AuthorityWorkerLease    Authority = "worker_lease"
	AuthorityDeletionWorker Authority = "deletion_worker"
)

var (
	ErrInvalidAccountID    = errors.New("invalid account ID")
	ErrInvalidAccountEpoch = errors.New("invalid account epoch")
	ErrInvalidAuthority    = errors.New("invalid authority")
)

// Principal can only be constructed after server-side authentication or a
// verified internal lease. Its fields are intentionally private so callers
// cannot replace account identity with request-body values.
type Principal struct {
	accountID string
	epoch     int64
	authority Authority
}

func NewVerifiedPrincipal(accountID string, epoch int64, authority Authority) (Principal, error) {
	if len(accountID) < 16 || len(accountID) > 128 {
		return Principal{}, ErrInvalidAccountID
	}
	if epoch < 0 {
		return Principal{}, ErrInvalidAccountEpoch
	}
	switch authority {
	case AuthorityIOSUser, AuthorityIOSDevice, AuthorityBrowserPairing, AuthorityWorkerLease, AuthorityDeletionWorker:
	default:
		return Principal{}, fmt.Errorf("%w: %q", ErrInvalidAuthority, authority)
	}
	return Principal{accountID: accountID, epoch: epoch, authority: authority}, nil
}

func (p Principal) AccountID() string    { return p.accountID }
func (p Principal) AccountEpoch() int64  { return p.epoch }
func (p Principal) Authority() Authority { return p.authority }

func (p Principal) Validate() error {
	_, err := NewVerifiedPrincipal(p.accountID, p.epoch, p.authority)
	return err
}
