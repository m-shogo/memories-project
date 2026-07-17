//go:build linux

package previewspool

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"sync"
	"syscall"
	"unsafe"
)

type sealOperations struct {
	writeAll      func(context.Context, *os.File, []byte) error
	syncFile      func(*os.File) error
	syncDir       func(int) error
	linkNoReplace func(int, string, int, string) error
}

type Sealer struct {
	writer     *StreamWriter
	mu         sync.Mutex
	sealed     bool
	sealDigest string
	evidence   SealEvidence
	ops        sealOperations
}

func NewSealer(writer *StreamWriter) (*Sealer, error) {
	if writer == nil || writer.attempt == nil {
		return nil, ErrAttemptMissing
	}
	return &Sealer{writer: writer, ops: defaultSealOperations()}, nil
}
func defaultSealOperations() sealOperations {
	return sealOperations{writeAll: writeAllContext, syncFile: func(f *os.File) error { return f.Sync() }, syncDir: syscall.Fsync, linkNoReplace: linkatNoReplace}
}

func (s *Sealer) Seal(ctx context.Context, input SealInput) (SealEvidence, error) {
	if s == nil || s.writer == nil {
		return SealEvidence{}, ErrAttemptMissing
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	w := s.writer
	w.mu.Lock()
	defer w.mu.Unlock()
	evidence := WriteEvidence{SourceRowCount: w.totalRecords, SpoolByteLength: w.totalBytes, Accepted: evidenceOf(w.accepted), Rejected: evidenceOf(w.rejected)}
	payload, digest, err := buildManifest(w.attempt.id, input, evidence)
	if err != nil {
		if s.sealed {
			return SealEvidence{}, ErrSealConflict
		}
		return SealEvidence{}, w.fail(err)
	}
	if s.sealed {
		if digest != s.sealDigest {
			return SealEvidence{}, ErrSealConflict
		}
		return s.evidence, nil
	}
	if w.terminalErr != nil {
		return SealEvidence{}, w.terminalErr
	}
	if w.closed {
		return SealEvidence{}, ErrStreamWriterClosed
	}
	if ctx == nil {
		return SealEvidence{}, w.fail(errors.New("Preview spool seal requires context"))
	}
	if err := ctx.Err(); err != nil {
		return SealEvidence{}, w.fail(err)
	}
	if w.accepted.recordCount == 0 {
		return SealEvidence{}, w.fail(ErrAcceptedRecordRequired)
	}
	a := w.attempt
	a.mu.Lock()
	defer a.mu.Unlock()
	if a.cleaned {
		return SealEvidence{}, w.failLocked(ErrAttemptMissing)
	}
	if a.accepted == nil || a.rejected == nil {
		return SealEvidence{}, w.failLocked(ErrAttemptMissing)
	}
	if err := s.ops.syncFile(a.accepted); err != nil {
		return SealEvidence{}, w.failLocked(fmt.Errorf("fsync accepted Preview spool stream: %w", err))
	}
	if err := ctx.Err(); err != nil {
		return SealEvidence{}, w.failLocked(err)
	}
	if err := s.ops.syncFile(a.rejected); err != nil {
		return SealEvidence{}, w.failLocked(fmt.Errorf("fsync rejected Preview spool stream: %w", err))
	}
	if err := ctx.Err(); err != nil {
		return SealEvidence{}, w.failLocked(err)
	}
	if err := closeStreamFilesLocked(a); err != nil {
		return SealEvidence{}, w.failLocked(fmt.Errorf("close Preview spool streams before seal: %w", err))
	}
	w.evidence = evidence
	w.closed = true
	if err := publishManifestAtomic(ctx, a, payload, s.ops); err != nil {
		if w.terminalErr == nil {
			w.terminalErr = err
		}
		return SealEvidence{}, w.terminalErr
	}
	sum := sha256.Sum256(payload)
	result := SealEvidence{WriteEvidence: evidence, ManifestByteLength: int64(len(payload)), ManifestSHA256: hex.EncodeToString(sum[:])}
	s.sealed = true
	s.sealDigest = digest
	s.evidence = result
	return result, nil
}

func publishManifestAtomic(ctx context.Context, a *Attempt, payload []byte, ops sealOperations) (resultErr error) {
	m := a.manager
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.closed {
		return ErrManagerClosed
	}
	if err := m.verifyRootDescriptor(); err != nil {
		return err
	}
	d, err := syscall.Openat(m.rootFD, a.id, syscall.O_RDONLY|syscall.O_DIRECTORY|syscall.O_CLOEXEC|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return fmt.Errorf("open Preview spool attempt for seal: %w", err)
	}
	defer syscall.Close(d)
	var st syscall.Stat_t
	if err := syscall.Fstat(d, &st); err != nil {
		return fmt.Errorf("fstat Preview spool attempt for seal: %w", err)
	}
	if uint64(st.Dev) != a.dirDev || st.Ino != a.dirIno {
		return ErrAttemptSubstituted
	}
	if err := verifyDirectoryStat(&st); err != nil {
		return fmt.Errorf("%w: %v", ErrUnsafeEntry, err)
	}
	if entryExistsAt(d, ManifestFileName) || entryExistsAt(d, ManifestTempFileName) {
		return ErrSealPublicationExists
	}
	temp, err := createExclusiveFile(d, ManifestTempFileName)
	if err != nil {
		return fmt.Errorf("%w: create manifest temp: %v", ErrSealPublish, err)
	}
	tempClosed := false
	defer func() {
		if !tempClosed {
			_ = temp.Close()
		}
		_ = syscall.Unlinkat(d, ManifestTempFileName)
	}()
	if err := ops.writeAll(ctx, temp, payload); err != nil {
		return fmt.Errorf("%w: write manifest temp: %v", ErrSealPublish, err)
	}
	if err := ops.syncFile(temp); err != nil {
		return fmt.Errorf("%w: fsync manifest temp: %v", ErrSealPublish, err)
	}
	if err := temp.Close(); err != nil {
		return fmt.Errorf("%w: close manifest temp: %v", ErrSealPublish, err)
	}
	tempClosed = true
	if err := ctx.Err(); err != nil {
		return err
	}
	if err := ops.linkNoReplace(d, ManifestTempFileName, d, ManifestFileName); err != nil {
		if errors.Is(err, syscall.EEXIST) {
			return ErrSealPublicationExists
		}
		return fmt.Errorf("%w: publish manifest: %v", ErrSealPublish, err)
	}
	if err := syscall.Unlinkat(d, ManifestTempFileName); err != nil {
		rollbackErr := syscall.Unlinkat(d, ManifestFileName)
		return errors.Join(fmt.Errorf("%w: remove manifest temp: %v", ErrSealPublish, err), rollbackErr)
	}
	if err := ops.syncDir(d); err != nil {
		unlinkErr := syscall.Unlinkat(d, ManifestFileName)
		rollbackSyncErr := ops.syncDir(d)
		if unlinkErr != nil || rollbackSyncErr != nil {
			return errors.Join(ErrSealDurabilityUncertain, fmt.Errorf("directory fsync after publish: %w", err), unlinkErr, rollbackSyncErr)
		}
		return fmt.Errorf("%w: directory fsync after publish: %v", ErrSealPublish, err)
	}
	return nil
}
func entryExistsAt(d int, name string) bool {
	fd, err := syscall.Openat(d, name, syscall.O_RDONLY|syscall.O_CLOEXEC|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return !errors.Is(err, syscall.ENOENT)
	}
	_ = syscall.Close(fd)
	return true
}
func linkatNoReplace(od int, on string, nd int, nn string) error {
	op, err := syscall.BytePtrFromString(on)
	if err != nil {
		return err
	}
	np, err := syscall.BytePtrFromString(nn)
	if err != nil {
		return err
	}
	_, _, errno := syscall.Syscall6(syscall.SYS_LINKAT, uintptr(od), uintptr(unsafe.Pointer(op)), uintptr(nd), uintptr(unsafe.Pointer(np)), 0, 0)
	if errno != 0 {
		return errno
	}
	return nil
}
