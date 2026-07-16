package security

import (
	"errors"
	"testing"
)

func TestNewVerifiedPrincipal(t *testing.T) {
	t.Parallel()

	principal, err := NewVerifiedPrincipal(
		"acct_01J00000000000000000000000",
		7,
		"https://appleid.apple.com",
		"apple-subject-001",
	)
	if err != nil {
		t.Fatalf("NewVerifiedPrincipal() error = %v", err)
	}
	if err := principal.Validate(); err != nil {
		t.Fatalf("Validate() error = %v", err)
	}
	if principal.AccountID() != "acct_01J00000000000000000000000" {
		t.Fatalf("unexpected account id: %q", principal.AccountID())
	}
	if principal.Epoch() != 7 {
		t.Fatalf("unexpected epoch: %d", principal.Epoch())
	}
}

func TestPrincipalRejectsInvalidInput(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		accountID string
		epoch     int64
		issuer    string
		subject   string
		want      error
	}{
		{name: "short account", accountID: "acct", epoch: 1, issuer: "https://appleid.apple.com", subject: "sub", want: ErrInvalidAccountID},
		{name: "negative epoch", accountID: "acct_01J00000000000000000000000", epoch: -1, issuer: "https://appleid.apple.com", subject: "sub", want: ErrInvalidEpoch},
		{name: "missing subject", accountID: "acct_01J00000000000000000000000", epoch: 1, issuer: "https://appleid.apple.com", subject: "", want: ErrInvalidSubject},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			_, err := NewVerifiedPrincipal(tt.accountID, tt.epoch, tt.issuer, tt.subject)
			if !errors.Is(err, tt.want) {
				t.Fatalf("error = %v, want %v", err, tt.want)
			}
		})
	}
}

func TestZeroPrincipalIsRejected(t *testing.T) {
	t.Parallel()

	var principal Principal
	if !errors.Is(principal.Validate(), ErrUnverifiedPrincipal) {
		t.Fatalf("Validate() should reject zero principal")
	}
}
