// Package pgrepo provides the concrete PostgreSQL repositories behind the
// service interfaces. Every method runs inside a dbscope transaction that
// already holds a runtime role and transaction-local owner/epoch context, so
// FORCE row-level security — not repository code — decides row visibility;
// a row another tenant owns is simply absent, never filtered here.
package pgrepo

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"

	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/upload"
)

var ErrNotFound = errors.New("row is not visible in this scope")

// Upload implements upload.Repository over the security migrations'
// import_job / upload_authorization / quarantine_object tables.
type Upload struct{}

// authorizationMetadata is the safe_metadata payload for one authorization.
// Only the display filename lives here; every security-relevant binding has
// its own constrained column.
type authorizationMetadata struct {
	DisplayFilename string `json:"displayFilename,omitempty"`
}

// scanMetadata is the safe_metadata payload for one enqueued quarantine scan.
// It carries exact object bindings and no user file content.
type scanMetadata struct {
	JobID           string    `json:"jobId"`
	AuthorizationID string    `json:"authorizationId"`
	ObjectKey       string    `json:"objectKey"`
	ObjectVersionID string    `json:"objectVersionId"`
	ETag            string    `json:"etag"`
	ContentLength   int64     `json:"contentLength"`
	ChecksumSHA256  string    `json:"checksumSha256"`
	ContentType     string    `json:"contentType"`
	EnqueuedAt      time.Time `json:"enqueuedAt"`
}

func (Upload) GetImportJob(ctx context.Context, tx dbscope.Transaction, jobID string) (upload.ImportJob, error) {
	adapted, err := pgscope.From(tx)
	if err != nil {
		return upload.ImportJob{}, err
	}
	var job upload.ImportJob
	err = adapted.QueryRow(ctx,
		`SELECT id, owner_account_id, account_epoch, state
		 FROM memory_os.import_job WHERE id = $1`, jobID,
	).Scan(&job.ID, &job.OwnerAccountID, &job.AccountEpoch, &job.Status)
	if errors.Is(err, pgx.ErrNoRows) {
		return upload.ImportJob{}, ErrNotFound
	}
	if err != nil {
		return upload.ImportJob{}, fmt.Errorf("read import job: %w", err)
	}
	return job, nil
}

func (Upload) InsertAuthorization(ctx context.Context, tx dbscope.Transaction, authorization upload.Authorization) error {
	adapted, err := pgscope.From(tx)
	if err != nil {
		return err
	}
	metadata, err := json.Marshal(authorizationMetadata{DisplayFilename: authorization.DisplayFilename})
	if err != nil {
		return fmt.Errorf("encode authorization metadata: %w", err)
	}
	return adapted.Exec(ctx,
		`INSERT INTO memory_os.upload_authorization (
			id, owner_account_id, account_epoch, state, job_id, object_key,
			content_length, checksum_sha256, declared_content_type, source_surface,
			expires_at, safe_metadata, created_at, updated_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $13)`,
		authorization.ID, authorization.OwnerAccountID, authorization.AccountEpoch,
		authorization.Status, authorization.JobID, authorization.ObjectKey,
		authorization.ContentLength, authorization.ChecksumSHA256, authorization.ContentType,
		authorization.SourceSurface, authorization.ExpiresAt, metadata, authorization.CreatedAt,
	)
}

func (Upload) GetAuthorization(ctx context.Context, tx dbscope.Transaction, authorizationID string) (upload.Authorization, error) {
	adapted, err := pgscope.From(tx)
	if err != nil {
		return upload.Authorization{}, err
	}
	var authorization upload.Authorization
	var metadataPayload []byte
	err = adapted.QueryRow(ctx,
		`SELECT id, job_id, owner_account_id, account_epoch, object_key,
		        content_length, checksum_sha256, declared_content_type, source_surface,
		        state, expires_at, created_at, safe_metadata
		 FROM memory_os.upload_authorization WHERE id = $1`, authorizationID,
	).Scan(
		&authorization.ID, &authorization.JobID, &authorization.OwnerAccountID,
		&authorization.AccountEpoch, &authorization.ObjectKey, &authorization.ContentLength,
		&authorization.ChecksumSHA256, &authorization.ContentType, &authorization.SourceSurface,
		&authorization.Status, &authorization.ExpiresAt, &authorization.CreatedAt, &metadataPayload,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return upload.Authorization{}, ErrNotFound
	}
	if err != nil {
		return upload.Authorization{}, fmt.Errorf("read upload authorization: %w", err)
	}
	var metadata authorizationMetadata
	if len(metadataPayload) > 0 {
		if err := json.Unmarshal(metadataPayload, &metadata); err != nil {
			return upload.Authorization{}, fmt.Errorf("decode authorization metadata: %w", err)
		}
	}
	authorization.DisplayFilename = metadata.DisplayFilename
	return authorization, nil
}

func (Upload) ConsumeIssuedAuthorization(ctx context.Context, tx dbscope.Transaction, authorizationID string, now time.Time) (bool, error) {
	adapted, err := pgscope.From(tx)
	if err != nil {
		return false, err
	}
	tag, err := adapted.ExecTag(ctx,
		`UPDATE memory_os.upload_authorization
		 SET state = 'consumed', updated_at = $2
		 WHERE id = $1 AND state = 'issued'`,
		authorizationID, now,
	)
	if err != nil {
		return false, fmt.Errorf("consume upload authorization: %w", err)
	}
	return tag.RowsAffected() == 1, nil
}

func (Upload) RevokeAuthorization(ctx context.Context, tx dbscope.Transaction, authorizationID string, reason string) error {
	adapted, err := pgscope.From(tx)
	if err != nil {
		return err
	}
	return adapted.Exec(ctx,
		`UPDATE memory_os.upload_authorization
		 SET state = 'revoked', failure_reason = $2, updated_at = now()
		 WHERE id = $1`,
		authorizationID, reason,
	)
}

// EnqueueScan records the verified object version as a pending quarantine
// scan in memory_os.quarantine_object. The scan worker later claims rows in
// state scan_pending under its own runtime role.
func (Upload) EnqueueScan(ctx context.Context, tx dbscope.Transaction, ticket upload.ScanTicket) error {
	adapted, err := pgscope.From(tx)
	if err != nil {
		return err
	}
	metadata, err := json.Marshal(scanMetadata{
		JobID:           ticket.JobID,
		AuthorizationID: ticket.AuthorizationID,
		ObjectKey:       ticket.ObjectKey,
		ObjectVersionID: ticket.ObjectVersionID,
		ETag:            ticket.ETag,
		ContentLength:   ticket.ContentLength,
		ChecksumSHA256:  ticket.ChecksumSHA256,
		ContentType:     ticket.ContentType,
		EnqueuedAt:      ticket.CreatedAt,
	})
	if err != nil {
		return fmt.Errorf("encode scan ticket: %w", err)
	}
	return adapted.Exec(ctx,
		`INSERT INTO memory_os.quarantine_object (
			id, owner_account_id, account_epoch, state, safe_metadata, created_at, updated_at
		) VALUES ($1, $2, $3, 'scan_pending', $4, $5, $5)`,
		ticket.AuthorizationID, ticket.OwnerAccountID, ticket.AccountEpoch, metadata, ticket.CreatedAt,
	)
}
