package security

import "testing"

func TestNewVerifiedPrincipal(t *testing.T) {
	p, err := NewVerifiedPrincipal("acct_01J00000000000000000000000", 7, AuthorityIOSUser)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if p.AccountID() != "acct_01J00000000000000000000000" || p.AccountEpoch() != 7 {
		t.Fatalf("unexpected principal: %#v", p)
	}
}

func TestNewVerifiedPrincipalRejectsInvalidInput(t *testing.T) {
	tests := []struct {
		name      string
		accountID string
		epoch     int64
		authority Authority
	}{
		{"short account", "acct", 1, AuthorityIOSUser},
		{"negative epoch", "acct_01J00000000000000000000000", -1, AuthorityIOSUser},
		{"unknown authority", "acct_01J00000000000000000000000", 1, Authority("admin")},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if _, err := NewVerifiedPrincipal(tc.accountID, tc.epoch, tc.authority); err == nil {
				t.Fatal("expected error")
			}
		})
	}
}
