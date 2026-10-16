package security

import (
	"context"
	"errors"
	"testing"
)

func TestPrincipalContextRoundTrip(t *testing.T) {
	principal, _ := NewVerifiedPrincipal("acct_01J00000000000000000000000", 7, AuthorityIOSUser)
	ctx, err := WithPrincipal(context.Background(), principal)
	if err != nil {
		t.Fatal(err)
	}
	got, err := PrincipalFromContext(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if got.AccountID() != principal.AccountID() || got.AccountEpoch() != principal.AccountEpoch() {
		t.Fatal("principal mismatch")
	}
}

func TestPrincipalFromContextRejectsMissingValue(t *testing.T) {
	if _, err := PrincipalFromContext(context.Background()); !errors.Is(err, ErrMissingVerifiedPrincipal) {
		t.Fatalf("expected missing principal, got %v", err)
	}
}

func TestNilPrincipalContextFailsClosed(t *testing.T) {
	principal, err := NewVerifiedPrincipal("acct_01J00000000000000000000000", 7, AuthorityIOSUser)
	if err != nil {
		t.Fatal(err)
	}
	ctx, err := WithPrincipal(nil, principal)
	if ctx != nil || !errors.Is(err, ErrMissingVerifiedPrincipal) {
		t.Fatalf("nil context write must fail closed: ctx=%v err=%v", ctx, err)
	}
	if _, err := PrincipalFromContext(nil); !errors.Is(err, ErrMissingVerifiedPrincipal) {
		t.Fatalf("nil context read must fail closed: %v", err)
	}
}

// Even callers inside the security package cannot place unverified principal
// values into the context via the public constructor.
func TestWithPrincipalRejectsUnverifiedValues(t *testing.T) {
	const account = "acct_01J00000000000000000000000"
	tests := []struct {
		name      string
		principal Principal
		want      error
	}{
		{"zero principal", Principal{}, ErrInvalidAccountID},
		{"negative epoch", Principal{accountID: account, epoch: -1, authority: AuthorityIOSUser}, ErrInvalidAccountEpoch},
		{"unknown authority", Principal{accountID: account, epoch: 1, authority: Authority("unverified")}, ErrInvalidAuthority},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			ctx, err := WithPrincipal(context.Background(), tc.principal)
			if ctx != nil || !errors.Is(err, tc.want) {
				t.Fatalf("unverified principal was admitted: context=%v error=%v", ctx, err)
			}
		})
	}
}

// A package-internal caller could accidentally overwrite the private context
// key. Such a value must never be returned as an authenticated principal.
func TestPrincipalFromContextRejectsForgedOrCorruptValues(t *testing.T) {
	const account = "acct_01J00000000000000000000000"
	tests := []struct {
		name  string
		value any
	}{
		{"wrong type", account},
		{"nil value", nil},
		{"zero principal", Principal{}},
		{"negative epoch", Principal{accountID: account, epoch: -1, authority: AuthorityIOSUser}},
		{"unknown authority", Principal{accountID: account, epoch: 1, authority: Authority("admin")}},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			ctx := context.WithValue(context.Background(), principalContextKey{}, tc.value)
			got, err := PrincipalFromContext(ctx)
			if !errors.Is(err, ErrMissingVerifiedPrincipal) || got != (Principal{}) {
				t.Fatalf("corrupt principal was returned: principal=%#v error=%v", got, err)
			}
		})
	}
}
