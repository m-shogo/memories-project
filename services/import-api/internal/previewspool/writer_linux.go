//go:build linux

package previewspool

import (
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"errors"
	"fmt"
	"hash"
	"io"
	"os"
	"sync"
	"syscall"
)

type streamCounters struct {
	recordFormat string
	recordCount  int
	byteLength   int64
	hasher       hash.Hash
}

// StreamWriter serializes accepted and rejected canonical records directly to
// separate private files. It owns no goroutines or channels. The first
// cancellation, limit, short-write, filesystem, or lifecycle error is sticky
// and permanently prevents further output from this writer.
type StreamWriter struct {
	attempt *Attempt
	mu      sync.Mutex

	accepted streamCounters
	rejected streamCounters

	totalRecords int
	totalBytes   int64
	terminalErr  error
	closed       bool
	evidence     WriteEvidence

	maxRecords     int
	maxBytes       int64
	maxRecordBytes int
	writeAll       func(context.Context, *os.File, []byte) error
}

// NewStreamWriter claims the two empty stream files exactly once. The empty
// manifest placeholder created by the filesystem checkpoint is removed through
// the verified attempt directory descriptor. A final manifest must not exist
// until the later seal/publish phase succeeds.
func NewStreamWriter(attempt *Attempt) (*StreamWriter, error) {
	if attempt == nil {
		return nil, ErrAttemptMissing
	}

	attempt.mu.Lock()
	defer attempt.mu.Unlock()

	if attempt.cleaned {
		return nil, ErrAttemptMissing
	}
	if attempt.manifest == nil {
		return nil, ErrStreamWriterClaimed
	}
	if attempt.accepted == nil || attempt.rejected == nil || attempt.manager == nil {
		return nil, ErrAttemptMissing
	}
	if err := verifyEmptyStreamFile(attempt.accepted); err != nil {
		return nil, err
	}
	if err := verifyEmptyStreamFile(attempt.rejected); err != nil {
		return nil, err
	}
	if err := removeManifestPlaceholderLocked(attempt); err != nil {
		return nil, err
	}

	return &StreamWriter{
		attempt: attempt,
		accepted: streamCounters{
			recordFormat: AcceptedRecordFormat,
			hasher:       sha256.New(),
		},
		rejected: streamCounters{
			recordFormat: RejectedRecordFormat,
			hasher:       sha256.New(),
		},
		maxRecords:     MaxSpoolRecords,
		maxBytes:       MaxSpoolBytes,
		maxRecordBytes: MaxCanonicalRecordBytes,
		writeAll:       writeAllContext,
	}, nil
}

func (w *StreamWriter) WriteAccepted(ctx context.Context, canonical []byte) error {
	return w.writeRecord(ctx, canonical, true)
}

func (w *StreamWriter) WriteRejected(ctx context.Context, canonical []byte) error {
	return w.writeRecord(ctx, canonical, false)
}

func (w *StreamWriter) writeRecord(ctx context.Context, canonical []byte, accepted bool) error {
	if w == nil {
		return ErrAttemptMissing
	}

	w.mu.Lock()
	defer w.mu.Unlock()

	if w.terminalErr != nil {
		return w.terminalErr
	}
	if w.closed {
		return ErrStreamWriterClosed
	}
	if ctx == nil {
		return w.fail(errors.New("Preview spool stream write requires context"))
	}
	if err := ctx.Err(); err != nil {
		return w.fail(err)
	}
	if len(canonical) == 0 {
		return w.fail(ErrInvalidCanonicalRecord)
	}
	if len(canonical) > w.maxRecordBytes {
		return w.fail(ErrCanonicalRecordTooLarge)
	}

	recordBytes := int64(8 + len(canonical))
	if w.totalRecords >= w.maxRecords {
		return w.fail(ErrSpoolRecordLimit)
	}
	if recordBytes > w.maxBytes-w.totalBytes {
		return w.fail(ErrSpoolByteLimit)
	}

	attempt := w.attempt
	attempt.mu.Lock()
	defer attempt.mu.Unlock()

	if attempt.cleaned {
		return w.failLocked(ErrAttemptMissing)
	}

	var file *os.File
	var stream *streamCounters
	if accepted {
		file = attempt.accepted
		stream = &w.accepted
	} else {
		file = attempt.rejected
		stream = &w.rejected
	}
	if file == nil {
		return w.failLocked(ErrAttemptMissing)
	}

	var prefix [8]byte
	binary.BigEndian.PutUint64(prefix[:], uint64(len(canonical)))
	if err := w.writeAll(ctx, file, prefix[:]); err != nil {
		return w.failLocked(fmt.Errorf("write Preview spool length prefix: %w", err))
	}
	if err := w.writeAll(ctx, file, canonical); err != nil {
		return w.failLocked(fmt.Errorf("write Preview spool canonical record: %w", err))
	}

	_, _ = stream.hasher.Write(prefix[:])
	_, _ = stream.hasher.Write(canonical)
	stream.recordCount++
	stream.byteLength += recordBytes
	w.totalRecords++
	w.totalBytes += recordBytes
	return nil
}

// Close closes only the accepted/rejected streams and returns their exact-byte
// evidence. It deliberately does not fsync, seal, publish a manifest, or make
// the attempt eligible for database commit.
func (w *StreamWriter) Close(ctx context.Context) (WriteEvidence, error) {
	if w == nil {
		return WriteEvidence{}, ErrAttemptMissing
	}

	w.mu.Lock()
	defer w.mu.Unlock()

	if w.terminalErr != nil {
		return WriteEvidence{}, w.terminalErr
	}
	if w.closed {
		return w.evidence, nil
	}
	if ctx == nil {
		return WriteEvidence{}, w.fail(errors.New("Preview spool stream close requires context"))
	}
	if err := ctx.Err(); err != nil {
		return WriteEvidence{}, w.fail(err)
	}
	if w.accepted.recordCount == 0 {
		return WriteEvidence{}, w.fail(ErrAcceptedRecordRequired)
	}

	attempt := w.attempt
	attempt.mu.Lock()
	defer attempt.mu.Unlock()

	if attempt.cleaned {
		return WriteEvidence{}, w.failLocked(ErrAttemptMissing)
	}
	if err := closeStreamFilesLocked(attempt); err != nil {
		return WriteEvidence{}, w.failLocked(err)
	}

	w.evidence = WriteEvidence{
		SourceRowCount:  w.totalRecords,
		SpoolByteLength: w.totalBytes,
		Accepted:        evidenceOf(w.accepted),
		Rejected:        evidenceOf(w.rejected),
	}
	w.closed = true
	return w.evidence, nil
}

func evidenceOf(stream streamCounters) StreamEvidence {
	return StreamEvidence{
		RecordFormat: stream.recordFormat,
		RecordCount:  stream.recordCount,
		ByteLength:   stream.byteLength,
		SHA256:       hex.EncodeToString(stream.hasher.Sum(nil)),
	}
}

func (w *StreamWriter) fail(err error) error {
	if w.terminalErr == nil {
		w.terminalErr = err
	}
	if w.attempt != nil {
		w.attempt.mu.Lock()
		defer w.attempt.mu.Unlock()
		_ = closeStreamFilesLocked(w.attempt)
	}
	return w.terminalErr
}

func (w *StreamWriter) failLocked(err error) error {
	if w.terminalErr == nil {
		w.terminalErr = err
	}
	_ = closeStreamFilesLocked(w.attempt)
	return w.terminalErr
}

func closeStreamFilesLocked(attempt *Attempt) error {
	var errs []error
	for _, target := range []**os.File{&attempt.accepted, &attempt.rejected} {
		if *target == nil {
			continue
		}
		if err := (*target).Close(); err != nil && !errors.Is(err, os.ErrClosed) {
			errs = append(errs, err)
		}
		*target = nil
	}
	return errors.Join(errs...)
}

func verifyEmptyStreamFile(file *os.File) error {
	if file == nil {
		return ErrAttemptMissing
	}
	info, err := file.Stat()
	if err != nil {
		return fmt.Errorf("stat Preview spool stream: %w", err)
	}
	stat, ok := info.Sys().(*syscall.Stat_t)
	if !ok {
		return ErrUnsafeEntry
	}
	if err := verifyRegularFileStat(stat); err != nil {
		return fmt.Errorf("%w: %v", ErrUnsafeEntry, err)
	}
	position, err := file.Seek(0, io.SeekCurrent)
	if err != nil {
		return fmt.Errorf("seek Preview spool stream: %w", err)
	}
	if info.Size() != 0 || position != 0 {
		return ErrStreamModified
	}
	return nil
}

func removeManifestPlaceholderLocked(attempt *Attempt) error {
	manager := attempt.manager
	manager.mu.Lock()
	defer manager.mu.Unlock()

	if manager.closed {
		return ErrManagerClosed
	}
	if err := manager.verifyRootDescriptor(); err != nil {
		return err
	}

	dirFD, err := syscall.Openat(
		manager.rootFD,
		attempt.id,
		syscall.O_RDONLY|syscall.O_DIRECTORY|syscall.O_CLOEXEC|syscall.O_NOFOLLOW,
		0,
	)
	if err != nil {
		return fmt.Errorf("open Preview spool attempt for stream claim: %w", err)
	}
	defer syscall.Close(dirFD)

	var stat syscall.Stat_t
	if err := syscall.Fstat(dirFD, &stat); err != nil {
		return fmt.Errorf("fstat Preview spool attempt for stream claim: %w", err)
	}
	if uint64(stat.Dev) != attempt.dirDev || stat.Ino != attempt.dirIno {
		return ErrAttemptSubstituted
	}
	if err := verifyDirectoryStat(&stat); err != nil {
		return fmt.Errorf("%w: %v", ErrUnsafeEntry, err)
	}

	manifest := attempt.manifest
	attempt.manifest = nil
	if err := manifest.Close(); err != nil && !errors.Is(err, os.ErrClosed) {
		return fmt.Errorf("close Preview spool manifest placeholder: %w", err)
	}
	if err := syscall.Unlinkat(dirFD, ManifestFileName); err != nil && !errors.Is(err, syscall.ENOENT) {
		return fmt.Errorf("remove Preview spool manifest placeholder: %w", err)
	}
	return nil
}

func writeAllContext(ctx context.Context, file *os.File, value []byte) error {
	for len(value) > 0 {
		if err := ctx.Err(); err != nil {
			return err
		}
		written, err := file.Write(value)
		if written > 0 {
			value = value[written:]
		}
		if err != nil {
			return err
		}
		if written == 0 {
			return io.ErrShortWrite
		}
	}
	return nil
}
