// Package previewread serves committed Previews back to their owner: the
// ready summary plus bounded pages of candidates and safe rejections, read
// under the API runtime role so FORCE RLS decides visibility.
package previewread

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"

	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

const (
	DefaultPageSize = 100
	MaxPageSize     = 500
)

var (
	ErrNotFound       = errors.New("no ready preview is visible for this job")
	ErrInvalidRequest = errors.New("invalid preview read request")
)

type ScopedExecutor interface {
	WithinPrincipal(context.Context, security.Principal, dbscope.Role, func(context.Context, dbscope.Transaction) error) error
}

type Candidate struct {
	Ordinal   int             `json:"ordinal"`
	SourceRow int64           `json:"sourceRow"`
	Record    json.RawMessage `json:"record"`
}

type Rejection struct {
	Ordinal    int      `json:"ordinal"`
	SourceRow  int64    `json:"sourceRow"`
	IssueCodes []string `json:"issueCodes"`
}

type View struct {
	PreviewID     string      `json:"previewId"`
	JobID         string      `json:"jobId"`
	PreviewSHA256 string      `json:"previewSha256"`
	AcceptedCount int         `json:"acceptedCount"`
	RejectedCount int         `json:"rejectedCount"`
	ExpiresAt     time.Time   `json:"expiresAt"`
	Candidates    []Candidate `json:"candidates"`
	Rejections    []Rejection `json:"rejections"`
}

type Service struct {
	Transactions ScopedExecutor
}

// GetJobPreview returns the owner's committed Preview for one job with the
// first `limit` candidates/rejections in ordinal order. Interactive
// authorities only; a job another tenant owns is simply not found.
func (s *Service) GetJobPreview(ctx context.Context, principal security.Principal, jobID string, limit int) (View, error) {
	switch principal.Authority() {
	case security.AuthorityIOSUser, security.AuthorityIOSDevice, security.AuthorityBrowserPairing:
	default:
		return View{}, ErrNotFound
	}
	if s == nil || s.Transactions == nil {
		return View{}, errors.New("preview read service dependencies are incomplete")
	}
	if len(jobID) < 16 || len(jobID) > 128 {
		return View{}, ErrInvalidRequest
	}
	if limit <= 0 {
		limit = DefaultPageSize
	}
	if limit > MaxPageSize {
		return View{}, ErrInvalidRequest
	}

	var view View
	err := s.Transactions.WithinPrincipal(ctx, principal, dbscope.RoleAPI,
		func(ctx context.Context, tx dbscope.Transaction) error {
			adapted, err := pgscope.From(tx)
			if err != nil {
				return err
			}
			err = adapted.QueryRow(ctx,
				`SELECT id, job_id, preview_hash_sha256, accepted_count, rejected_count, sealed_expires_at
				 FROM memory_os.preview_ready WHERE job_id = $1 AND state = 'ready'`, jobID,
			).Scan(&view.PreviewID, &view.JobID, &view.PreviewSHA256,
				&view.AcceptedCount, &view.RejectedCount, &view.ExpiresAt)
			if errors.Is(err, pgx.ErrNoRows) {
				return ErrNotFound
			}
			if err != nil {
				return fmt.Errorf("read ready preview: %w", err)
			}

			candidateRows, err := adapted.Query(ctx,
				`SELECT ordinal, source_row, canonical_record
				 FROM memory_os.preview_candidate
				 WHERE preview_id = $1 ORDER BY ordinal LIMIT $2`,
				view.PreviewID, limit)
			if err != nil {
				return fmt.Errorf("read preview candidates: %w", err)
			}
			defer candidateRows.Close()
			for candidateRows.Next() {
				var candidate Candidate
				if err := candidateRows.Scan(&candidate.Ordinal, &candidate.SourceRow, &candidate.Record); err != nil {
					return err
				}
				view.Candidates = append(view.Candidates, candidate)
			}
			if err := candidateRows.Err(); err != nil {
				return err
			}

			rejectionRows, err := adapted.Query(ctx,
				`SELECT ordinal, source_row, issue_codes
				 FROM memory_os.preview_rejection
				 WHERE preview_id = $1 ORDER BY ordinal LIMIT $2`,
				view.PreviewID, limit)
			if err != nil {
				return fmt.Errorf("read preview rejections: %w", err)
			}
			defer rejectionRows.Close()
			for rejectionRows.Next() {
				var rejection Rejection
				if err := rejectionRows.Scan(&rejection.Ordinal, &rejection.SourceRow, &rejection.IssueCodes); err != nil {
					return err
				}
				view.Rejections = append(view.Rejections, rejection)
			}
			return rejectionRows.Err()
		})
	if err != nil {
		return View{}, err
	}
	return view, nil
}
