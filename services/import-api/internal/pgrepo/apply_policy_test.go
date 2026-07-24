package pgrepo

import (
	"context"
	"errors"
	"testing"

	"github.com/m-shogo/memories-project/services/import-api/internal/apply"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgscope"
)

// The service refuses update_safe_fields before opening a transaction, so this
// guard only matters if that check is ever bypassed. It is tested with a nil
// transaction on purpose: the refusal must come before the repository touches
// anything at all, and a nil transaction would panic if it did not.
func TestApplyRepositoryRefusesUpdateSafeFieldsBeforeUsingTheTransaction(t *testing.T) {
	counts, err := Apply{}.ApplyMaterializedPreview(
		context.Background(), nil, "prv_000000000000", "", apply.DuplicateUpdateSafe)
	if !errors.Is(err, apply.ErrDuplicatePolicyUnsupported) {
		t.Fatalf("error = %v, want ErrDuplicatePolicyUnsupported", err)
	}
	if counts != (apply.Counts{}) {
		t.Fatalf("refusal reported counts: %#v", counts)
	}
}

// Any other policy must still reach the transaction, or the guard above would
// be silently disabling the whole repository.
func TestApplyRepositoryPassesSupportedPoliciesThrough(t *testing.T) {
	for _, policy := range []apply.DuplicatePolicy{apply.DuplicateSkipExisting, apply.DuplicateKeepBoth} {
		_, err := Apply{}.ApplyMaterializedPreview(
			context.Background(), nil, "prv_000000000000", "", policy)
		if errors.Is(err, apply.ErrDuplicatePolicyUnsupported) {
			t.Fatalf("%s was refused as unsupported", policy)
		}
		// It fails for a different reason — the nil transaction — which is
		// exactly the proof that it got past the policy guard.
		if !errors.Is(err, pgscope.ErrForeignTransaction) {
			t.Fatalf("%s: expected the nil transaction to be rejected, got nil", policy)
		}
	}
}
