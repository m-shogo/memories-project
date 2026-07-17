package pipeline

import (
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"errors"
	"fmt"
	"hash"
	"io"
	"strings"
	"sync"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/adapters/genericcsv"
	"github.com/m-shogo/memories-project/services/import-api/internal/preview"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

const csvCandidateBuffer = 32

var ErrPipelineClosed = errors.New("Generic CSV preview pipeline closed")

type RowReport struct {
	SourceRow int
	Accepted  bool
	Issues    []string
}

type RowReportSink interface {
	Record(context.Context, RowReport) error
}

type GenericCSVPreview struct {
	Parser       genericcsv.Parser
	Materializer *preview.Materializer
	Reports      RowReportSink
}

type GenericCSVRequest struct {
	JobID     string
	Source    preview.SourceBinding
	Adapter   preview.AdapterBinding
	Options   genericcsv.Options
	ExpiresAt time.Time
}

type GenericCSVResult struct {
	Preview preview.Record
	Summary genericcsv.Summary
}

// Materialize owns reader until the call returns. A closable input is required
// so cancellation or a database failure can interrupt a parser blocked in Read.
// Object-storage adapters connected here must honor Close promptly.
func (s GenericCSVPreview) Materialize(ctx context.Context, principal security.Principal, reader io.ReadCloser, request GenericCSVRequest) (GenericCSVResult, error) {
	if s.Materializer == nil || reader == nil {
		return GenericCSVResult{}, errors.New("Generic CSV preview dependencies are incomplete")
	}
	optionsHash, err := hashCSVOptions(request.Options)
	if err != nil {
		_ = reader.Close()
		return GenericCSVResult{}, err
	}
	stream := newCSVSource(ctx, s.Parser, reader, request.Options, s.Reports)
	defer stream.Close()

	record, materializeErr := s.Materializer.Materialize(ctx, principal, preview.Draft{
		JobID:         request.JobID,
		Source:        request.Source,
		Adapter:       request.Adapter,
		OptionsSHA256: optionsHash,
		ExpiresAt:     request.ExpiresAt,
	}, stream)
	if materializeErr != nil {
		stream.Close()
		summary, _ := stream.Wait()
		return GenericCSVResult{Summary: summary}, materializeErr
	}
	summary, parseErr := stream.Wait()
	if parseErr != nil {
		return GenericCSVResult{Summary: summary}, parseErr
	}
	return GenericCSVResult{Preview: record, Summary: summary}, nil
}

type sourceItem struct {
	candidate preview.Candidate
	err       error
}

type csvSource struct {
	ctx       context.Context
	cancel    context.CancelFunc
	reader    io.ReadCloser
	closeOnce sync.Once
	items     chan sourceItem
	done      chan struct{}
	summary   genericcsv.Summary
	err       error
}

func newCSVSource(parent context.Context, parser genericcsv.Parser, reader io.ReadCloser, options genericcsv.Options, reports RowReportSink) *csvSource {
	ctx, cancel := context.WithCancel(parent)
	source := &csvSource{
		ctx:    ctx,
		cancel: cancel,
		reader: reader,
		items:  make(chan sourceItem, csvCandidateBuffer),
		done:   make(chan struct{}),
	}
	go source.run(parser, options, reports)
	return source
}

func (s *csvSource) run(parser genericcsv.Parser, options genericcsv.Options, reports RowReportSink) {
	defer close(s.done)
	defer close(s.items)
	defer s.closeReader()

	summary, err := parser.Parse(s.reader, options, func(result genericcsv.Result) error {
		issues := make([]string, len(result.Issues))
		for index, issue := range result.Issues {
			issues[index] = string(issue)
		}
		if reports != nil {
			if err := reports.Record(s.ctx, RowReport{SourceRow: result.SourceRow, Accepted: result.Accepted, Issues: issues}); err != nil {
				return err
			}
		}
		if !result.Accepted {
			return nil
		}
		candidate := preview.Candidate{
			SourceRow:   result.Candidate.SourceRow,
			Title:       result.Candidate.Title,
			OccurredAt:  result.Candidate.OccurredAt,
			URL:         result.Candidate.URL,
			Text:        result.Candidate.Text,
			Fingerprint: result.Candidate.Fingerprint,
			Issues:      issues,
		}
		select {
		case s.items <- sourceItem{candidate: candidate}:
			return nil
		case <-s.ctx.Done():
			return context.Cause(s.ctx)
		}
	})
	s.summary = summary
	s.err = err
	if err != nil {
		select {
		case s.items <- sourceItem{err: err}:
		case <-s.ctx.Done():
		}
	}
}

func (s *csvSource) Next(ctx context.Context) (preview.Candidate, error) {
	select {
	case item, ok := <-s.items:
		if !ok {
			return preview.Candidate{}, preview.ErrEndOfCandidates
		}
		if item.err != nil {
			return preview.Candidate{}, item.err
		}
		return item.candidate, nil
	case <-ctx.Done():
		return preview.Candidate{}, context.Cause(ctx)
	case <-s.ctx.Done():
		return preview.Candidate{}, ErrPipelineClosed
	}
}

func (s *csvSource) Close() {
	s.cancel()
	s.closeReader()
	<-s.done
}

func (s *csvSource) closeReader() {
	s.closeOnce.Do(func() {
		_ = s.reader.Close()
	})
}

func (s *csvSource) Wait() (genericcsv.Summary, error) {
	<-s.done
	return s.summary, s.err
}

func hashCSVOptions(options genericcsv.Options) (string, error) {
	if strings.TrimSpace(options.TitleColumn) == "" {
		return "", errors.New("CSV title mapping is required")
	}
	delimiter := options.Delimiter
	if delimiter == 0 {
		delimiter = ','
	}
	location := "UTC"
	if options.DateLocation != nil {
		location = options.DateLocation.String()
	}
	maxInput := options.MaxInputBytes
	if maxInput == 0 {
		maxInput = genericcsv.DefaultMaxInputBytes
	}
	maxRows := options.MaxRows
	if maxRows == 0 {
		maxRows = genericcsv.DefaultMaxRows
	}
	maxColumns := options.MaxColumns
	if maxColumns == 0 {
		maxColumns = genericcsv.DefaultMaxColumns
	}
	maxCell := options.MaxCellBytes
	if maxCell == 0 {
		maxCell = genericcsv.DefaultMaxCellBytes
	}
	hasher := sha256.New()
	for _, value := range []string{
		"memory-os-generic-csv-options-v1",
		fmt.Sprintf("%d", delimiter),
		strings.TrimSpace(options.TitleColumn),
		strings.TrimSpace(options.DateColumn),
		options.DateLayout,
		location,
		strings.TrimSpace(options.URLColumn),
		strings.TrimSpace(options.TextColumn),
		fmt.Sprintf("%d", maxInput),
		fmt.Sprintf("%d", maxRows),
		fmt.Sprintf("%d", maxColumns),
		fmt.Sprintf("%d", maxCell),
	} {
		writeLengthPrefixed(hasher, []byte(value))
	}
	return hex.EncodeToString(hasher.Sum(nil)), nil
}

func writeLengthPrefixed(target hash.Hash, value []byte) {
	var size [8]byte
	binary.BigEndian.PutUint64(size[:], uint64(len(value)))
	_, _ = target.Write(size[:])
	_, _ = target.Write(value)
}
