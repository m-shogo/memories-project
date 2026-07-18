package previewcommit

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"regexp"
	"strconv"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/m-shogo/memories-project/services/import-api/internal/previewspool"
)

const (
	workerRole       = "memory_worker_runtime"
	requiredJobState = "preview_building"
	readyJobState    = "preview_ready"
)

var (
	ErrInvalidCommitInput  = errors.New("invalid Preview commit input")
	ErrRowEvidenceMismatch = errors.New("Preview commit rows do not match verified evidence")
	ErrSpoolExpired        = errors.New("verified Preview spool is expired")
	ErrJobBindingMismatch  = errors.New("import job does not match the verified binding")
	ErrJobStateInvalid     = errors.New("import job is not awaiting a Preview commit")
	ErrCommitConflict      = errors.New("conflicting Preview commit for this job")
	ErrIncompletePreview   = errors.New("Preview rows are not complete and contiguous")
)

var previewIDPattern = regexp.MustCompile(`^prv_[A-Za-z0-9_-]{12,120}$`)

// CandidateRow is one accepted candidate decoded from the verified spool.
type CandidateRow struct {
	Ordinal         int
	SourceRow       int64
	RecordSHA256    string
	CanonicalRecord []byte
}

// RejectionRow carries only the source row number and stable issue codes; the
// database schema structurally rejects anything else.
type RejectionRow struct {
	Ordinal    int
	SourceRow  int64
	IssueCodes []string
}

// CommitRequest carries evidence returned by previewspool.Verifier.Verify in
// the same flow, plus the decoded rows to bulk-copy. The committer trusts the
// evidence only as far as the database constraints and the completeness gate
// re-prove it inside the transaction.
type CommitRequest struct {
	PreviewID  string
	Verified   previewspool.VerifiedSpool
	Candidates []CandidateRow
	Rejections []RejectionRow
}

type CommitResult struct {
	PreviewID        string
	CommitKey        string
	PreviewHash      string
	AlreadyCommitted bool
}

// Committer executes the single short Preview commit transaction with
// client-side parameterized bulk inserts (PostgreSQL forbids COPY FROM under
// row-level security, and the commit contract allows an equivalent
// parameterized protocol). It never parses source content and holds no
// cross-call state; every failure rolls the whole transaction back.
type Committer struct {
	pool *pgxpool.Pool
}

func NewCommitter(pool *pgxpool.Pool) (*Committer, error) {
	if pool == nil {
		return nil, ErrInvalidCommitInput
	}
	return &Committer{pool: pool}, nil
}

// Commit runs:
//
//	BEGIN → SET LOCAL ROLE worker → SET LOCAL owner/epoch context
//	→ idempotent-retry check on the deterministic commit key
//	→ verify job binding and state under RLS
//	→ insert preview_ready (claims the commit key; parent row first because
//	  the composite tenant FK requires it — visibility stays atomic)
//	→ bulk-insert preview_candidate and preview_rejection under FORCE RLS
//	→ assert_preview_complete
//	→ mark the job preview_ready → COMMIT
//
// Any error produces a full ROLLBACK with no durable Preview state.
func (c *Committer) Commit(ctx context.Context, request CommitRequest, now time.Time) (_ CommitResult, resultErr error) {
	if c == nil || c.pool == nil || ctx == nil || now.IsZero() {
		return CommitResult{}, ErrInvalidCommitInput
	}
	if !previewIDPattern.MatchString(request.PreviewID) {
		return CommitResult{}, ErrInvalidCommitInput
	}
	verified := request.Verified
	if len(request.Candidates) != verified.Evidence.Accepted.RecordCount ||
		len(request.Rejections) != verified.Evidence.Rejected.RecordCount {
		return CommitResult{}, ErrRowEvidenceMismatch
	}
	if !now.Before(verified.ExpiresAt) {
		return CommitResult{}, ErrSpoolExpired
	}
	commitKey := DeriveCommitKey(verified)
	previewHash := DerivePreviewHash(verified)

	tx, err := c.pool.BeginTx(ctx, pgx.TxOptions{})
	if err != nil {
		return CommitResult{}, fmt.Errorf("begin Preview commit transaction: %w", err)
	}
	defer func() {
		if rollbackErr := tx.Rollback(ctx); rollbackErr != nil && !errors.Is(rollbackErr, pgx.ErrTxClosed) {
			resultErr = errors.Join(resultErr, rollbackErr)
		}
	}()

	if _, err := tx.Exec(ctx, "SET LOCAL ROLE "+workerRole); err != nil {
		return CommitResult{}, fmt.Errorf("assume Preview commit role: %w", err)
	}
	if _, err := tx.Exec(ctx, "SELECT set_config('app.current_account_id', $1, true)", verified.OwnerAccountID); err != nil {
		return CommitResult{}, fmt.Errorf("bind Preview commit account: %w", err)
	}
	if _, err := tx.Exec(ctx, "SELECT set_config('app.current_account_epoch', $1, true)", strconv.FormatInt(verified.AccountEpoch, 10)); err != nil {
		return CommitResult{}, fmt.Errorf("bind Preview commit epoch: %w", err)
	}

	var existingID, existingKey, existingHash string
	err = tx.QueryRow(ctx,
		"SELECT id, commit_key, preview_hash_sha256 FROM memory_os.preview_ready WHERE job_id = $1",
		verified.JobID,
	).Scan(&existingID, &existingKey, &existingHash)
	switch {
	case err == nil:
		if existingKey == commitKey {
			return CommitResult{PreviewID: existingID, CommitKey: existingKey, PreviewHash: existingHash, AlreadyCommitted: true}, nil
		}
		return CommitResult{}, ErrCommitConflict
	case errors.Is(err, pgx.ErrNoRows):
	default:
		return CommitResult{}, fmt.Errorf("check existing Preview commit: %w", err)
	}

	var jobState string
	err = tx.QueryRow(ctx, "SELECT state FROM memory_os.import_job WHERE id = $1", verified.JobID).Scan(&jobState)
	if errors.Is(err, pgx.ErrNoRows) {
		return CommitResult{}, ErrJobBindingMismatch
	}
	if err != nil {
		return CommitResult{}, fmt.Errorf("verify import job binding: %w", err)
	}
	if jobState != requiredJobState {
		return CommitResult{}, fmt.Errorf("%w: state %q", ErrJobStateInvalid, jobState)
	}

	if _, err := tx.Exec(ctx, `
		INSERT INTO memory_os.preview_ready (
			id, owner_account_id, account_epoch, job_id, spool_id, commit_key,
			source_object_key, source_object_version_id, source_content_length,
			source_checksum_sha256, adapter_id, adapter_version, adapter_artifact_sha256,
			options_sha256, source_row_count, spool_byte_length,
			accepted_record_format, accepted_count, accepted_byte_length, accepted_sha256,
			rejected_record_format, rejected_count, rejected_byte_length, rejected_sha256,
			preview_hash_sha256, sealed_created_at, sealed_expires_at
		) VALUES (
			$1, $2, $3, $4, $5, $6,
			$7, $8, $9,
			$10, $11, $12, $13,
			$14, $15, $16,
			$17, $18, $19, $20,
			$21, $22, $23, $24,
			$25, $26, $27
		)`,
		request.PreviewID, verified.OwnerAccountID, verified.AccountEpoch, verified.JobID, verified.SpoolID, commitKey,
		verified.Source.ObjectKey, verified.Source.ObjectVersionID, verified.Source.ContentLength,
		verified.Source.ChecksumSHA256, verified.Adapter.AdapterID, verified.Adapter.AdapterVersion, verified.Adapter.ArtifactSHA256,
		verified.OptionsSHA256, verified.Evidence.SourceRowCount, verified.Evidence.SpoolByteLength,
		verified.Evidence.Accepted.RecordFormat, verified.Evidence.Accepted.RecordCount, verified.Evidence.Accepted.ByteLength, verified.Evidence.Accepted.SHA256,
		verified.Evidence.Rejected.RecordFormat, verified.Evidence.Rejected.RecordCount, verified.Evidence.Rejected.ByteLength, verified.Evidence.Rejected.SHA256,
		previewHash, verified.CreatedAt, verified.ExpiresAt,
	); err != nil {
		return CommitResult{}, mapCommitError("insert ready Preview", err)
	}

	if err := bulkInsertCandidates(ctx, tx, request, verified); err != nil {
		return CommitResult{}, err
	}
	if err := bulkInsertRejections(ctx, tx, request, verified); err != nil {
		return CommitResult{}, err
	}

	if _, err := tx.Exec(ctx, "SELECT memory_os.assert_preview_complete($1)", request.PreviewID); err != nil {
		return CommitResult{}, mapCommitError("assert Preview completeness", err)
	}

	tag, err := tx.Exec(ctx,
		"UPDATE memory_os.import_job SET state = $2, updated_at = now() WHERE id = $1 AND state = $3",
		verified.JobID, readyJobState, requiredJobState,
	)
	if err != nil {
		return CommitResult{}, mapCommitError("mark import job preview_ready", err)
	}
	if tag.RowsAffected() != 1 {
		return CommitResult{}, fmt.Errorf("%w: job state changed during commit", ErrJobStateInvalid)
	}

	if err := tx.Commit(ctx); err != nil {
		return CommitResult{}, fmt.Errorf("commit Preview transaction: %w", err)
	}
	return CommitResult{PreviewID: request.PreviewID, CommitKey: commitKey, PreviewHash: previewHash}, nil
}

// PostgreSQL rejects COPY FROM on row-level-security tables, so bulk loading
// uses the contract's allowed equivalent: one parameterized INSERT ... SELECT
// over unnested arrays, executed as the worker role with FORCE RLS in force.
func bulkInsertCandidates(ctx context.Context, tx pgx.Tx, request CommitRequest, verified previewspool.VerifiedSpool) error {
	total := len(request.Candidates)
	ordinals := make([]int32, total)
	sourceRows := make([]int64, total)
	recordHashes := make([]string, total)
	records := make([]string, total)
	for i, row := range request.Candidates {
		ordinals[i] = int32(row.Ordinal)
		sourceRows[i] = row.SourceRow
		recordHashes[i] = row.RecordSHA256
		records[i] = string(row.CanonicalRecord)
	}
	tag, err := tx.Exec(ctx, `
		INSERT INTO memory_os.preview_candidate
			(preview_id, owner_account_id, account_epoch, ordinal, source_row, record_sha256, canonical_record)
		SELECT $1, $2, $3, entry.ordinal, entry.source_row, entry.record_sha256, entry.canonical_record::jsonb
		FROM unnest($4::int[], $5::bigint[], $6::text[], $7::text[])
			AS entry(ordinal, source_row, record_sha256, canonical_record)`,
		request.PreviewID, verified.OwnerAccountID, verified.AccountEpoch,
		ordinals, sourceRows, recordHashes, records,
	)
	if err != nil {
		return mapCommitError("bulk insert Preview candidates", err)
	}
	if tag.RowsAffected() != int64(total) {
		return fmt.Errorf("%w: inserted %d of %d candidates", ErrIncompletePreview, tag.RowsAffected(), total)
	}
	return nil
}

func bulkInsertRejections(ctx context.Context, tx pgx.Tx, request CommitRequest, verified previewspool.VerifiedSpool) error {
	total := len(request.Rejections)
	if total == 0 {
		return nil
	}
	ordinals := make([]int32, total)
	sourceRows := make([]int64, total)
	codeSets := make([]string, total)
	for i, row := range request.Rejections {
		ordinals[i] = int32(row.Ordinal)
		sourceRows[i] = row.SourceRow
		encoded, err := json.Marshal(row.IssueCodes)
		if err != nil {
			return fmt.Errorf("%w: encode issue codes: %v", ErrInvalidCommitInput, err)
		}
		codeSets[i] = string(encoded)
	}
	tag, err := tx.Exec(ctx, `
		INSERT INTO memory_os.preview_rejection
			(preview_id, owner_account_id, account_epoch, ordinal, source_row, issue_codes)
		SELECT $1, $2, $3, entry.ordinal, entry.source_row,
			ARRAY(SELECT jsonb_array_elements_text(entry.codes::jsonb))
		FROM unnest($4::int[], $5::bigint[], $6::text[])
			AS entry(ordinal, source_row, codes)`,
		request.PreviewID, verified.OwnerAccountID, verified.AccountEpoch,
		ordinals, sourceRows, codeSets,
	)
	if err != nil {
		return mapCommitError("bulk insert Preview rejections", err)
	}
	if tag.RowsAffected() != int64(total) {
		return fmt.Errorf("%w: inserted %d of %d rejections", ErrIncompletePreview, tag.RowsAffected(), total)
	}
	return nil
}

func mapCommitError(step string, err error) error {
	var pgErr *pgconn.PgError
	if errors.As(err, &pgErr) {
		switch pgErr.Code {
		case "23505":
			return fmt.Errorf("%w: %s: %s", ErrCommitConflict, step, pgErr.ConstraintName)
		case "P0002":
			return fmt.Errorf("%w: %s", ErrIncompletePreview, pgErr.Message)
		}
	}
	return fmt.Errorf("%s: %w", step, err)
}
