package pipeline

import (
	"context"
	"errors"
	"fmt"

	"github.com/m-shogo/memories-project/services/import-api/internal/adapters/genericcsv"
	"github.com/m-shogo/memories-project/services/import-api/internal/preview"
)

var ErrInvalidCSVRowResult = errors.New("invalid Generic CSV row result")

// GenericCSVPreviewSource converts one synchronous CSV iterator result into one
// atomic Preview row event. It owns no goroutines, queues, or persistence.
type GenericCSVPreviewSource struct {
	iterator    *genericcsv.Iterator
	terminalErr error
	exhausted   bool
}

func NewGenericCSVPreviewSource(iterator *genericcsv.Iterator) (*GenericCSVPreviewSource, error) {
	if iterator == nil {
		return nil, errors.New("Generic CSV Preview source requires iterator")
	}
	return &GenericCSVPreviewSource{iterator: iterator}, nil
}

func (s *GenericCSVPreviewSource) NextEvent(ctx context.Context) (preview.RowEvent, error) {
	if s == nil || s.iterator == nil {
		return preview.RowEvent{}, errors.New("Generic CSV Preview source is not initialized")
	}
	if s.terminalErr != nil {
		return preview.RowEvent{}, s.terminalErr
	}
	if s.exhausted {
		return preview.RowEvent{}, preview.ErrEndOfCandidates
	}

	result, err := s.iterator.Next(ctx)
	if errors.Is(err, genericcsv.ErrEndOfRows) {
		s.exhausted = true
		return preview.RowEvent{}, preview.ErrEndOfCandidates
	}
	if err != nil {
		return s.fail(fmt.Errorf("read Generic CSV row: %w", err))
	}
	if result.SourceRow < 1 {
		return s.fail(ErrInvalidCSVRowResult)
	}

	issues := make([]string, len(result.Issues))
	for index, issue := range result.Issues {
		issues[index] = string(issue)
	}

	if !result.Accepted {
		if len(issues) == 0 {
			return s.fail(ErrInvalidCSVRowResult)
		}
		rejection := preview.Rejection{SourceRow: result.SourceRow, Issues: issues}
		return preview.RowEvent{Rejection: &rejection}, nil
	}

	candidate := result.Candidate
	if candidate.SourceRow != result.SourceRow || candidate.Title == "" || candidate.Fingerprint == "" {
		return s.fail(ErrInvalidCSVRowResult)
	}
	converted := preview.Candidate{
		SourceRow:   candidate.SourceRow,
		Title:       candidate.Title,
		OccurredAt:  candidate.OccurredAt,
		URL:         candidate.URL,
		Text:        candidate.Text,
		Fingerprint: candidate.Fingerprint,
		Issues:      issues,
	}
	return preview.RowEvent{Candidate: &converted}, nil
}

func (s *GenericCSVPreviewSource) Summary() genericcsv.Summary {
	if s == nil || s.iterator == nil {
		return genericcsv.Summary{}
	}
	return s.iterator.Summary()
}

func (s *GenericCSVPreviewSource) fail(err error) (preview.RowEvent, error) {
	s.terminalErr = err
	return preview.RowEvent{}, err
}
