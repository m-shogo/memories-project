package postgres

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	"github.com/m-shogo/memories-project/backend/internal/dbscope"
	"github.com/m-shogo/memories-project/backend/internal/security"
	"github.com/m-shogo/memories-project/backend/internal/upload"
)

var ErrUnexpectedRowCount = errors.New("unexpected affected row count")

type UploadRepository struct {
	scope *dbscope.Runner
}

func NewUploadRepository(scope *dbscope.Runner) (*UploadRepository, error) {
	if scope == nil {
		return nil, errors.New("database scope runner is nil")
	}
	return &UploadRepository{scope: scope}, nil
}

func (r *UploadRepository) FindOwnedJob(
	ctx context.Context,
	principal security.Principal,
	jobID string,
) (upload.Job, error) {
	var job upload.Job
	err := r.scope.WithinTenant(ctx, principal, dbscope.RoleAPI, func(ctx context.Context, tx *sql.Tx) error {
		row := tx.QueryRowContext(ctx, `
			SELECT id, owner_account_id, account_epoch, state
			FROM memory_os.import_job
			WHERE id = $1
		`, jobID)
		if err := row.Scan(&job.ID, &job.OwnerAccountID, &job.AccountEpoch, &job.State); err != nil {
			if errors.Is(err, sql.ErrNoRows) {
				return upload.ErrJobUnavailable
			}
			return fmt.Errorf("scan import job: %w", err)
		}
		return nil
	})
	if err != nil {
		return upload.Job{}, err
	}
	return job, nil
}

func (r *UploadRepository) CreatePending(
	ctx context.Context,
	principal security.Principal,
	authorization upload.Authorization,
) error {
	if authorization.OwnerAccountID != principal.AccountID() || authorization.AccountEpoch != principal.Epoch() {
		return upload.ErrJobUnavailable
	}
	return r.scope.WithinTenant(ctx, principal, dbscope.RoleAPI, func(ctx context.Context, tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `
			INSERT INTO memory_os.upload_authorization (
				id,
				owner_account_id,
				account_epoch,
				state,
				job_id,
				object_key,
				content_length,
				checksum_sha256,
				declared_content_type,
				source_surface,
				expires_at
			)
			VALUES ($1, $2, $3, 'issuing', $4, $5, $6, $7, $8, $9, $10)
		`,
			authorization.ID,
			authorization.OwnerAccountID,
			authorization.AccountEpoch,
			authorization.JobID,
			authorization.ObjectKey,
			authorization.ContentLength,
			authorization.ChecksumSHA256,
			authorization.ContentType,
			authorization.SourceSurface,
			authorization.ExpiresAt,
		)
		if err != nil {
			return fmt.Errorf("insert pending upload authorization: %w", err)
		}
		return nil
	})
}

func (r *UploadRepository) MarkIssued(
	ctx context.Context,
	principal security.Principal,
	authorizationID string,
) error {
	return r.transition(ctx, principal, authorizationID, "issued", "")
}

func (r *UploadRepository) MarkFailed(
	ctx context.Context,
	principal security.Principal,
	authorizationID,
	safeReason string,
) error {
	switch safeReason {
	case "signing_failed", "empty_signed_url", "activation_failed":
	default:
		return errors.New("unsupported safe failure reason")
	}
	return r.transition(ctx, principal, authorizationID, "failed", safeReason)
}

func (r *UploadRepository) transition(
	ctx context.Context,
	principal security.Principal,
	authorizationID,
	nextState,
	failureReason string,
) error {
	return r.scope.WithinTenant(ctx, principal, dbscope.RoleAPI, func(ctx context.Context, tx *sql.Tx) error {
		result, err := tx.ExecContext(ctx, `
			UPDATE memory_os.upload_authorization
			SET state = $2,
				failure_reason = NULLIF($3, ''),
				updated_at = now()
			WHERE id = $1
			  AND state = 'issuing'
		`, authorizationID, nextState, failureReason)
		if err != nil {
			return fmt.Errorf("transition upload authorization: %w", err)
		}
		count, err := result.RowsAffected()
		if err != nil {
			return fmt.Errorf("read transition row count: %w", err)
		}
		if count == 0 {
			return upload.ErrJobUnavailable
		}
		if count != 1 {
			return ErrUnexpectedRowCount
		}
		return nil
	})
}
