package pgrepo

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"

	"github.com/m-shogo/memories-project/services/import-api/internal/apply"
	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgscope"
)

// Apply implements apply.Repository over the Preview domain, the extended
// apply_confirmation claim table and the minimal memory_item persistence.
// Every method runs under the API runtime role, so FORCE RLS scopes each
// statement to the principal's owner/epoch context.
type Apply struct{}

func (Apply) GetPreview(ctx context.Context, tx dbscope.Transaction, previewID string) (apply.Preview, error) {
	adapted, err := pgscope.From(tx)
	if err != nil {
		return apply.Preview{}, err
	}
	var preview apply.Preview
	err = adapted.QueryRow(ctx,
		`SELECT id, owner_account_id, account_epoch, preview_hash_sha256,
		        accepted_count, state, sealed_expires_at
		 FROM memory_os.preview_ready WHERE id = $1`, previewID,
	).Scan(&preview.ID, &preview.OwnerAccountID, &preview.AccountEpoch,
		&preview.PreviewSHA256, &preview.CandidateCount, &preview.Status, &preview.ExpiresAt)
	if errors.Is(err, pgx.ErrNoRows) {
		return apply.Preview{}, ErrNotFound
	}
	if err != nil {
		return apply.Preview{}, fmt.Errorf("read ready preview: %w", err)
	}
	return preview, nil
}

// ClaimIdempotency inserts the in_progress claim row; on an idempotency-key
// collision it reports the existing claim so the service can replay or
// reject. The partial unique index (owner, idempotency_key) is the arbiter.
func (Apply) ClaimIdempotency(ctx context.Context, tx dbscope.Transaction, claim apply.Claim) (apply.ClaimResult, error) {
	adapted, err := pgscope.From(tx)
	if err != nil {
		return apply.ClaimResult{}, err
	}
	tag, err := adapted.ExecTag(ctx,
		`INSERT INTO memory_os.apply_confirmation (
			id, owner_account_id, account_epoch, state, preview_id, preview_sha256,
			idempotency_key, request_sha256, duplicate_policy, created_at, updated_at
		) VALUES ($1, $2, $3, 'in_progress', $4, $5, $6, $7, $8, $9, $9)
		ON CONFLICT (owner_account_id, idempotency_key) WHERE idempotency_key IS NOT NULL
		DO NOTHING`,
		claim.ApplyID, claim.OwnerAccountID, claim.AccountEpoch, claim.PreviewID,
		claim.PreviewSHA256, claim.IdempotencyKey, claim.RequestSHA256,
		string(claim.DuplicatePolicy), claim.CreatedAt,
	)
	if err != nil {
		return apply.ClaimResult{}, fmt.Errorf("insert apply claim: %w", err)
	}
	if tag.RowsAffected() == 1 {
		return apply.ClaimResult{Disposition: apply.ClaimNew, ApplyID: claim.ApplyID}, nil
	}

	var existingID, state, requestSHA string
	var created, updated, skipped *int
	err = adapted.QueryRow(ctx,
		`SELECT id, state, request_sha256, created_count, updated_count, skipped_count
		 FROM memory_os.apply_confirmation WHERE idempotency_key = $1`,
		claim.IdempotencyKey,
	).Scan(&existingID, &state, &requestSHA, &created, &updated, &skipped)
	if errors.Is(err, pgx.ErrNoRows) {
		// The key exists for a different tenant; under RLS that row is
		// invisible, and the claim must not proceed.
		return apply.ClaimResult{Disposition: apply.ClaimConflict}, nil
	}
	if err != nil {
		return apply.ClaimResult{}, fmt.Errorf("read existing apply claim: %w", err)
	}
	switch state {
	case "applied":
		counts := apply.Counts{}
		if created != nil && updated != nil && skipped != nil {
			counts = apply.Counts{Created: *created, Updated: *updated, Skipped: *skipped}
		}
		return apply.ClaimResult{
			Disposition:   apply.ClaimReplay,
			ApplyID:       existingID,
			RequestSHA256: requestSHA,
			Existing:      apply.Result{ApplyID: existingID, Status: "applied", Counts: counts},
		}, nil
	case "in_progress":
		return apply.ClaimResult{Disposition: apply.ClaimInProgress, ApplyID: existingID, RequestSHA256: requestSHA}, nil
	default:
		return apply.ClaimResult{Disposition: apply.ClaimConflict}, nil
	}
}

// ApplyMaterializedPreview turns every candidate of one committed Preview
// into memory_item rows under the requested duplicate policy, entirely
// set-based inside the claim transaction. Dedupe matches on the canonical
// record's fingerprint within the owner scope RLS provides.
func (Apply) ApplyMaterializedPreview(ctx context.Context, tx dbscope.Transaction, previewID string, previewSHA256 string, policy apply.DuplicatePolicy) (apply.Counts, error) {
	adapted, err := pgscope.From(tx)
	if err != nil {
		return apply.Counts{}, err
	}

	var total int
	err = adapted.QueryRow(ctx,
		`SELECT accepted_count FROM memory_os.preview_ready
		 WHERE id = $1 AND preview_hash_sha256 = $2 AND state = 'ready'`,
		previewID, previewSHA256,
	).Scan(&total)
	if errors.Is(err, pgx.ErrNoRows) {
		return apply.Counts{}, ErrNotFound
	}
	if err != nil {
		return apply.Counts{}, fmt.Errorf("re-read preview binding: %w", err)
	}

	// matched counts candidates whose fingerprint already exists for this
	// owner; each candidate is counted exactly once, so the policy counts
	// always account for the full candidate set.
	var matched int
	if err := adapted.QueryRow(ctx,
		`SELECT count(*) FROM memory_os.preview_candidate c
		 WHERE c.preview_id = $1
		   AND EXISTS (
		     SELECT 1 FROM memory_os.memory_item m
		     WHERE m.fingerprint = c.canonical_record->>'fingerprint'
		   )`, previewID,
	).Scan(&matched); err != nil {
		return apply.Counts{}, fmt.Errorf("count matching fingerprints: %w", err)
	}

	insertFilter := ""
	switch policy {
	case apply.DuplicateSkipExisting, apply.DuplicateUpdateSafe:
		insertFilter = `AND NOT EXISTS (
			SELECT 1 FROM memory_os.memory_item m
			WHERE m.fingerprint = c.canonical_record->>'fingerprint')`
	case apply.DuplicateKeepBoth:
	default:
		return apply.Counts{}, fmt.Errorf("unsupported duplicate policy %q", policy)
	}

	if policy == apply.DuplicateUpdateSafe && matched > 0 {
		if _, err := adapted.ExecTag(ctx,
			`UPDATE memory_os.memory_item m
			 SET canonical_record = c.canonical_record,
			     source_preview_id = c.preview_id,
			     updated_at = now()
			 FROM memory_os.preview_candidate c
			 WHERE c.preview_id = $1
			   AND m.fingerprint = c.canonical_record->>'fingerprint'`,
			previewID,
		); err != nil {
			return apply.Counts{}, fmt.Errorf("update matching memory items: %w", err)
		}
	}

	tag, err := adapted.ExecTag(ctx, fmt.Sprintf(
		`INSERT INTO memory_os.memory_item
			(id, owner_account_id, account_epoch, fingerprint, source_preview_id, canonical_record)
		 SELECT 'mem_' || replace(gen_random_uuid()::text, '-', ''),
		        c.owner_account_id, c.account_epoch,
		        c.canonical_record->>'fingerprint', c.preview_id, c.canonical_record
		 FROM memory_os.preview_candidate c
		 WHERE c.preview_id = $1 %s`, insertFilter),
		previewID,
	)
	if err != nil {
		return apply.Counts{}, fmt.Errorf("insert memory items: %w", err)
	}
	inserted := int(tag.RowsAffected())

	switch policy {
	case apply.DuplicateSkipExisting:
		return apply.Counts{Created: inserted, Skipped: total - inserted}, nil
	case apply.DuplicateUpdateSafe:
		return apply.Counts{Created: inserted, Updated: total - inserted}, nil
	default: // keep_both
		return apply.Counts{Created: inserted}, nil
	}
}

func (Apply) CompleteApply(ctx context.Context, tx dbscope.Transaction, applyID string, counts apply.Counts, completedAt time.Time) error {
	adapted, err := pgscope.From(tx)
	if err != nil {
		return err
	}
	tag, err := adapted.ExecTag(ctx,
		`UPDATE memory_os.apply_confirmation
		 SET state = 'applied', created_count = $2, updated_count = $3,
		     skipped_count = $4, completed_at = $5, updated_at = $5
		 WHERE id = $1 AND state = 'in_progress'`,
		applyID, counts.Created, counts.Updated, counts.Skipped, completedAt,
	)
	if err != nil {
		return fmt.Errorf("complete apply confirmation: %w", err)
	}
	if tag.RowsAffected() != 1 {
		return fmt.Errorf("apply confirmation %s was not in progress", applyID)
	}
	return nil
}
