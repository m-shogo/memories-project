package genericcsv

import (
	"bufio"
	"context"
	"encoding/csv"
	"errors"
	"io"
)

// ErrEndOfRows is returned after the iterator has consumed the complete CSV.
var ErrEndOfRows = errors.New("end of CSV rows")

// Iterator reads exactly one CSV data row per Next call. It intentionally uses
// no goroutines or internal queues so cancellation, failure, and backpressure
// stay in one call stack.
type Iterator struct {
	reader      *csv.Reader
	limited     *countingReader
	headerLen   int
	mapping     mapping
	config      normalizedOptions
	summary     Summary
	terminalErr error
	exhausted   bool
}

// NewIterator validates the header and explicit mapping before returning an
// iterator. The supplied reader must be a staged local input, not a network
// stream.
func NewIterator(reader io.Reader, options Options) (*Iterator, error) {
	if reader == nil {
		return nil, errors.New("CSV iterator requires reader")
	}
	config, err := normalizeOptions(options)
	if err != nil {
		return nil, err
	}
	limited := &countingReader{reader: bufio.NewReader(reader), limit: config.MaxInputBytes}
	csvReader := csv.NewReader(limited)
	csvReader.Comma = config.Delimiter
	csvReader.FieldsPerRecord = -1
	csvReader.ReuseRecord = true
	csvReader.LazyQuotes = false
	csvReader.TrimLeadingSpace = false

	header, err := csvReader.Read()
	if errors.Is(err, io.EOF) {
		return nil, ErrMissingHeader
	}
	if err != nil {
		return nil, normalizeReadError(err)
	}
	if err := validateRecordShape(header, config.MaxColumns, config.MaxCellBytes); err != nil {
		return nil, err
	}
	indexes, err := buildHeaderIndex(header)
	if err != nil {
		return nil, err
	}
	resolved, err := resolveMapping(indexes, config)
	if err != nil {
		return nil, err
	}

	return &Iterator{
		reader:    csvReader,
		limited:   limited,
		headerLen: len(header),
		mapping:   resolved,
		config:    config,
	}, nil
}

// Next returns the next accepted or rejected row result. A cancellation or
// parser failure is sticky: callers cannot resume a partially consumed stream
// and accidentally build a Preview from a different row set.
func (i *Iterator) Next(ctx context.Context) (Result, error) {
	if i == nil {
		return Result{}, errors.New("CSV iterator is nil")
	}
	if i.terminalErr != nil {
		return Result{}, i.terminalErr
	}
	if i.exhausted {
		return Result{}, ErrEndOfRows
	}
	if ctx == nil {
		return i.fail(errors.New("CSV iterator requires context"))
	}
	if err := ctx.Err(); err != nil {
		return i.fail(err)
	}

	record, err := i.reader.Read()
	if errors.Is(err, io.EOF) {
		i.exhausted = true
		if i.limited.exceeded {
			return i.fail(ErrInputTooLarge)
		}
		return Result{}, ErrEndOfRows
	}
	if err != nil {
		return i.fail(normalizeReadError(err))
	}
	if err := ctx.Err(); err != nil {
		return i.fail(err)
	}

	i.summary.RowsRead++
	if i.summary.RowsRead > i.config.MaxRows {
		return i.fail(ErrTooManyRows)
	}
	if len(record) != i.headerLen {
		return i.fail(ErrInconsistentColumns)
	}
	if err := validateRecordShape(record, i.config.MaxColumns, i.config.MaxCellBytes); err != nil {
		return i.fail(err)
	}

	result := convertRecord(i.summary.RowsRead+1, record, i.mapping, i.config)
	if result.Accepted {
		i.summary.AcceptedRows++
	} else {
		i.summary.RejectedRows++
	}
	if len(result.Issues) > 0 {
		i.summary.WarningRows++
	}
	return result, nil
}

// Summary returns counters for rows already consumed by this iterator.
func (i *Iterator) Summary() Summary {
	if i == nil {
		return Summary{}
	}
	return i.summary
}

func (i *Iterator) fail(err error) (Result, error) {
	i.terminalErr = err
	return Result{}, err
}
