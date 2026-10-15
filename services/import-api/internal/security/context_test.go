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
