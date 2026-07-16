package genericcsv

import (
	"bufio"
	"crypto/sha256"
	"encoding/csv"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"net/url"
	"strings"
	"time"
	"unicode/utf8"
)

const (
	DefaultMaxInputBytes int64 = 256 * 1024 * 1024
	DefaultMaxRows             = 100_000
	DefaultMaxColumns          = 256
	DefaultMaxCellBytes        = 1024 * 1024
)

var (
	ErrInputTooLarge        = errors.New("CSV input exceeds byte limit")
	ErrTooManyRows          = errors.New("CSV row limit exceeded")
	ErrTooManyColumns       = errors.New("CSV column limit exceeded")
	ErrCellTooLarge         = errors.New("CSV cell limit exceeded")
	ErrInvalidUTF8          = errors.New("CSV contains invalid UTF-8")
	ErrDuplicateHeader      = errors.New("CSV contains duplicate normalized header")
	ErrMissingHeader        = errors.New("CSV header is required")
	ErrMappingColumnMissing = errors.New("CSV mapping references a missing column")
	ErrInconsistentColumns  = errors.New("CSV row has inconsistent column count")
)

type IssueCode string

const (
	IssueTitleRequired   IssueCode = "IMPORT_CSV_TITLE_REQUIRED"
	IssueDateInvalid     IssueCode = "IMPORT_CSV_DATE_INVALID"
	IssueURLInvalid      IssueCode = "IMPORT_CSV_URL_INVALID"
	IssueFormulaLikeText IssueCode = "IMPORT_CSV_FORMULA_LIKE_TEXT"
)

type Options struct {
	Delimiter     rune
	TitleColumn   string
	DateColumn    string
	DateLayout    string
	DateLocation  *time.Location
	URLColumn     string
	TextColumn    string
	MaxInputBytes int64
	MaxRows       int
	MaxColumns    int
	MaxCellBytes  int
}

type Candidate struct {
	SourceRow   int
	Title       string
	OccurredAt  *time.Time
	URL         string
	Text        string
	Fingerprint string
}

type Result struct {
	SourceRow int
	Accepted  bool
	Candidate Candidate
	Issues    []IssueCode
}

type Summary struct {
	RowsRead     int
	AcceptedRows int
	RejectedRows int
	WarningRows  int
}

type Emitter func(Result) error

type Parser struct{}

func (Parser) Parse(reader io.Reader, options Options, emit Emitter) (Summary, error) {
	if reader == nil || emit == nil {
		return Summary{}, errors.New("CSV parser requires reader and emitter")
	}
	config, err := normalizeOptions(options)
	if err != nil {
		return Summary{}, err
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
		return Summary{}, ErrMissingHeader
	}
	if err != nil {
		return Summary{}, normalizeReadError(err)
	}
	if err := validateRecordShape(header, config.MaxColumns, config.MaxCellBytes); err != nil {
		return Summary{}, err
	}
	indexes, err := buildHeaderIndex(header)
	if err != nil {
		return Summary{}, err
	}
	mapping, err := resolveMapping(indexes, config)
	if err != nil {
		return Summary{}, err
	}

	summary := Summary{}
	for {
		record, err := csvReader.Read()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			return summary, normalizeReadError(err)
		}
		summary.RowsRead++
		if summary.RowsRead > config.MaxRows {
			return summary, ErrTooManyRows
		}
		if len(record) != len(header) {
			return summary, ErrInconsistentColumns
		}
		if err := validateRecordShape(record, config.MaxColumns, config.MaxCellBytes); err != nil {
			return summary, err
		}
		result := convertRecord(summary.RowsRead+1, record, mapping, config)
		if result.Accepted {
			summary.AcceptedRows++
		} else {
			summary.RejectedRows++
		}
		if len(result.Issues) > 0 {
			summary.WarningRows++
		}
		if err := emit(result); err != nil {
			return summary, err
		}
	}
	if limited.exceeded {
		return summary, ErrInputTooLarge
	}
	return summary, nil
}

type normalizedOptions struct {
	Options
}

func normalizeOptions(options Options) (normalizedOptions, error) {
	if options.Delimiter == 0 {
		options.Delimiter = ','
	}
	if options.Delimiter != ',' && options.Delimiter != '\t' {
		return normalizedOptions{}, errors.New("unsupported CSV delimiter")
	}
	if strings.TrimSpace(options.TitleColumn) == "" {
		return normalizedOptions{}, errors.New("title column mapping is required")
	}
	if options.DateColumn != "" && options.DateLayout == "" {
		return normalizedOptions{}, errors.New("date layout is required when date column is mapped")
	}
	if options.DateLocation == nil {
		options.DateLocation = time.UTC
	}
	if options.MaxInputBytes == 0 {
		options.MaxInputBytes = DefaultMaxInputBytes
	}
	if options.MaxRows == 0 {
		options.MaxRows = DefaultMaxRows
	}
	if options.MaxColumns == 0 {
		options.MaxColumns = DefaultMaxColumns
	}
	if options.MaxCellBytes == 0 {
		options.MaxCellBytes = DefaultMaxCellBytes
	}
	if options.MaxInputBytes <= 0 || options.MaxInputBytes > DefaultMaxInputBytes ||
		options.MaxRows <= 0 || options.MaxRows > DefaultMaxRows ||
		options.MaxColumns <= 0 || options.MaxColumns > DefaultMaxColumns ||
		options.MaxCellBytes <= 0 || options.MaxCellBytes > DefaultMaxCellBytes {
		return normalizedOptions{}, errors.New("CSV limits exceed the approved P0 profile")
	}
	return normalizedOptions{Options: options}, nil
}

type mapping struct {
	title int
	date  int
	url   int
	text  int
}

func buildHeaderIndex(header []string) (map[string]int, error) {
	indexes := make(map[string]int, len(header))
	for index, value := range header {
		if !utf8.ValidString(value) {
			return nil, ErrInvalidUTF8
		}
		normalized := normalizeHeader(value)
		if normalized == "" {
			return nil, ErrMissingHeader
		}
		if _, exists := indexes[normalized]; exists {
			return nil, ErrDuplicateHeader
		}
		indexes[normalized] = index
	}
	return indexes, nil
}

func resolveMapping(indexes map[string]int, options normalizedOptions) (mapping, error) {
	result := mapping{date: -1, url: -1, text: -1}
	var ok bool
	result.title, ok = indexes[normalizeHeader(options.TitleColumn)]
	if !ok {
		return mapping{}, ErrMappingColumnMissing
	}
	for name, target := range map[string]*int{
		options.DateColumn: &result.date,
		options.URLColumn:  &result.url,
		options.TextColumn: &result.text,
	} {
		if name == "" {
			continue
		}
		index, exists := indexes[normalizeHeader(name)]
		if !exists {
			return mapping{}, ErrMappingColumnMissing
		}
		*target = index
	}
	return result, nil
}

func convertRecord(sourceRow int, record []string, fields mapping, options normalizedOptions) Result {
	result := Result{SourceRow: sourceRow}
	title := strings.TrimSpace(record[fields.title])
	if title == "" {
		result.Issues = append(result.Issues, IssueTitleRequired)
		return result
	}
	candidate := Candidate{SourceRow: sourceRow, Title: title}
	if fields.date >= 0 {
		value := strings.TrimSpace(record[fields.date])
		if value != "" {
			parsed, err := time.ParseInLocation(options.DateLayout, value, options.DateLocation)
			if err != nil {
				result.Issues = append(result.Issues, IssueDateInvalid)
			} else {
				parsed = parsed.UTC()
				candidate.OccurredAt = &parsed
			}
		}
	}
	if fields.url >= 0 {
		value := strings.TrimSpace(record[fields.url])
		if value != "" {
			parsed, err := url.Parse(value)
			if err != nil || (parsed.Scheme != "https" && parsed.Scheme != "http") || parsed.Host == "" || parsed.User != nil || len(value) > 4096 {
				result.Issues = append(result.Issues, IssueURLInvalid)
			} else {
				candidate.URL = parsed.String()
			}
		}
	}
	if fields.text >= 0 {
		candidate.Text = strings.TrimSpace(record[fields.text])
	}
	for _, value := range record {
		if looksLikeSpreadsheetFormula(value) {
			result.Issues = appendUnique(result.Issues, IssueFormulaLikeText)
			break
		}
	}
	candidate.Fingerprint = fingerprint(candidate)
	result.Accepted = true
	result.Candidate = candidate
	return result
}

func validateRecordShape(record []string, maxColumns, maxCellBytes int) error {
	if len(record) == 0 {
		return ErrMissingHeader
	}
	if len(record) > maxColumns {
		return ErrTooManyColumns
	}
	for _, value := range record {
		if !utf8.ValidString(value) {
			return ErrInvalidUTF8
		}
		if len(value) > maxCellBytes {
			return ErrCellTooLarge
		}
	}
	return nil
}

func normalizeHeader(value string) string {
	return strings.ToLower(strings.TrimSpace(value))
}

func looksLikeSpreadsheetFormula(value string) bool {
	trimmed := strings.TrimLeft(value, " \t\r\n")
	if trimmed == "" {
		return false
	}
	switch trimmed[0] {
	case '=', '+', '-', '@':
		return true
	default:
		return false
	}
}

func fingerprint(candidate Candidate) string {
	occurredAt := ""
	if candidate.OccurredAt != nil {
		occurredAt = candidate.OccurredAt.UTC().Format(time.RFC3339Nano)
	}
	canonical := strings.Join([]string{
		strings.TrimSpace(candidate.Title),
		occurredAt,
		strings.TrimSpace(candidate.URL),
		strings.TrimSpace(candidate.Text),
	}, "\x1f")
	digest := sha256.Sum256([]byte(canonical))
	return hex.EncodeToString(digest[:])
}

func appendUnique(values []IssueCode, value IssueCode) []IssueCode {
	for _, existing := range values {
		if existing == value {
			return values
		}
	}
	return append(values, value)
}

type countingReader struct {
	reader   io.Reader
	limit    int64
	read     int64
	exceeded bool
}

func (r *countingReader) Read(buffer []byte) (int, error) {
	remaining := r.limit - r.read
	if remaining <= 0 {
		r.exceeded = true
		return 0, ErrInputTooLarge
	}
	if int64(len(buffer)) > remaining+1 {
		buffer = buffer[:remaining+1]
	}
	count, err := r.reader.Read(buffer)
	r.read += int64(count)
	if r.read > r.limit {
		r.exceeded = true
		allowed := count - int(r.read-r.limit)
		if allowed < 0 {
			allowed = 0
		}
		return allowed, ErrInputTooLarge
	}
	return count, err
}

func normalizeReadError(err error) error {
	if errors.Is(err, ErrInputTooLarge) {
		return ErrInputTooLarge
	}
	var parseError *csv.ParseError
	if errors.As(err, &parseError) {
		return fmt.Errorf("CSV parse failure at safe row %d: %w", parseError.Line, errors.New("malformed CSV"))
	}
	return err
}
