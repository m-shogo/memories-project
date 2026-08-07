package httpapi

import (
	"errors"

	"github.com/m-shogo/memories-project/services/import-api/internal/epochguard"
)

// isFencedSessionError identifies a principal that was valid when the bearer
// session was issued but is no longer authorized by the canonical account
// epoch/state. HTTP surfaces deliberately collapse these states to the same 401
// as any other invalid session: callers must not learn whether an account is
// deleting, deleted, suspended, or merely carrying a stale epoch.
//
// ErrAccountUnavailable is intentionally excluded. A failure to read canonical
// account state is a dependency/service failure and must not be disguised as an
// authentication failure.
func isFencedSessionError(err error) bool {
	return errors.Is(err, epochguard.ErrStaleAccountEpoch) ||
		errors.Is(err, epochguard.ErrAccountDeleting) ||
		errors.Is(err, epochguard.ErrAccountDeleted) ||
		errors.Is(err, epochguard.ErrAccountSuspended)
}
