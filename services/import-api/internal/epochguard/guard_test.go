package epochguard

import (
	"context"
	"errors"
	"testing"

	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

type fakeSource struct {
	snapshot Snapshot
	err      error
	account  string
}

func (s *fakeSource) Current(_ context.Context, accountID string) (Snapshot, error) {
	s.account = accountID
	return s.snapshot, s.err
}

func TestGuardAllowsCurrentActiveEpoch(t *testing.T) {
	principal := mustPrincipal(t, 7)
	source := &fakeSource{snapshot: Snapshot{AccountID: principal.AccountID(), Epoch: 7, State: StateActive}}
	if err := (Guard{Source: source}).Check(context.Background(), principal); err != nil {
		t.Fatal(err)
	}
	if source.account != principal.AccountID() {
		t.Fatal("guard did not derive account ID from verified principal")
	}
}

func TestGuardRejectsStaleEpoch(t *testing.T) {
	principal := mustPrincipal(t, 7)
	source := &fakeSource{snapshot: Snapshot{AccountID: principal.AccountID(), Epoch: 8, State: StateActive}}
	if err := (Guard{Source: source}).Check(context.Background(), principal); !errors.Is(err, ErrStaleAccountEpoch) {
		t.Fatalf("expected stale epoch, got %v", err)
	}
}

func TestGuardRejectsDeletionStates(t *testing.T) {
	principal := mustPrincipal(t, 7)
	for _, tc := range []struct {
		state State
		err   error
	}{{StateDeleting, ErrAccountDeleting}, {StateDeleted, ErrAccountDeleted}, {StateSuspended, ErrAccountSuspended}} {
		t.Run(string(tc.state), func(t *testing.T) {
			source := &fakeSource{snapshot: Snapshot{AccountID: principal.AccountID(), Epoch: 7, State: tc.state}}
			if err := (Guard{Source: source}).Check(context.Background(), principal); !errors.Is(err, tc.err) {
				t.Fatalf("expected %v, got %v", tc.err, err)
			}
		})
	}
}

func TestGuardRejectsMismatchedAccountSnapshot(t *testing.T) {
	principal := mustPrincipal(t, 7)
	source := &fakeSource{snapshot: Snapshot{AccountID: "acct_01J99999999999999999999999", Epoch: 7, State: StateActive}}
	if err := (Guard{Source: source}).Check(context.Background(), principal); !errors.Is(err, ErrAccountUnavailable) {
		t.Fatalf("expected unavailable, got %v", err)
	}
}

func mustPrincipal(t *testing.T, epoch int64) security.Principal {
	t.Helper()
	principal, err := security.NewVerifiedPrincipal("acct_01J00000000000000000000000", epoch, security.AuthorityWorkerLease)
	if err != nil {
		t.Fatal(err)
	}
	return principal
}
