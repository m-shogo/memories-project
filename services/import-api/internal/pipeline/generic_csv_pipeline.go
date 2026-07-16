package pipeline

import (
	"context"
	"errors"
	"io"

	"github.com/m-shogo/memories-project/services/import-api/internal/adapters/genericcsv"
	"github.com/m-shogo/memories-project/services/import-api/internal/preview"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

var (
	ErrGenericCSVAdapterMismatch       = errors.New("Generic CSV adapter binding mismatch")
	ErrGenericCSVOptionsDigestMismatch = errors.New("Generic CSV options digest mismatch")
)

type GenericCSVPreviewResult struct {
	Preview       preview.AtomicRecord
	Summary       genericcsv.Summary
	OptionsSHA256 string
}

type GenericCSVPreviewPipeline struct {
	Materializer *preview.AtomicMaterializer
}

// Run is the canonical P0 path from a staged CSV reader to an immutable
// Preview. It is synchronous and performs no hidden parsing, persistence, or
// goroutine work outside the AtomicMaterializer transaction.
func (p *GenericCSVPreviewPipeline) Run(
	ctx context.Context,
	principal security.Principal,
	reader io.Reader,
	options genericcsv.Options,
	draft preview.Draft,
) (GenericCSVPreviewResult, error) {
	if p == nil || p.Materializer == nil || reader == nil {
		return GenericCSVPreviewResult{}, errors.New("Generic CSV Preview pipeline dependencies are incomplete")
	}
	if draft.Adapter.AdapterID != "generic-csv" {
		return GenericCSVPreviewResult{}, ErrGenericCSVAdapterMismatch
	}

	normalizedOptions, optionsDigest, err := genericcsv.NormalizeAndDigestOptions(options)
	if err != nil {
		return GenericCSVPreviewResult{}, err
	}
	if draft.OptionsSHA256 != "" && draft.OptionsSHA256 != optionsDigest {
		return GenericCSVPreviewResult{OptionsSHA256: optionsDigest}, ErrGenericCSVOptionsDigestMismatch
	}
	draft.OptionsSHA256 = optionsDigest

	iterator, err := genericcsv.NewIterator(reader, normalizedOptions)
	if err != nil {
		return GenericCSVPreviewResult{OptionsSHA256: optionsDigest}, err
	}
	source, err := NewGenericCSVPreviewSource(iterator)
	if err != nil {
		return GenericCSVPreviewResult{OptionsSHA256: optionsDigest}, err
	}
	record, err := p.Materializer.Materialize(ctx, principal, draft, source)
	result := GenericCSVPreviewResult{
		Preview:       record,
		Summary:       source.Summary(),
		OptionsSHA256: optionsDigest,
	}
	if err != nil {
		return result, err
	}
	return result, nil
}
