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
	return sealOperations{
		writeAll: writeAllContext,
		syncFile: func(file *os.File) error { return file.Sync() },
		syncDir:  syscall.Fsync,
		linkNoReplace: linkatNoReplace,
	}
}

// Seal is the only successful stream-to-manifest transition. It fsyncs both
// stream files before closing them, writes and fsyncs an exclusive temp
// manifest, publishes without replacing an existing final name, removes the
// temp name, and fsyncs the attempt directory. The published manifest is still
// untrusted until an independent reader decodes and re-hashes both streams.
func (s *Sealer) Seal(ctx context.Context, input SealInput) (SealEvidence, error) {
	if s == nil || s.writer == nil {
		return SealEvidence{}, ErrAttemptMissing
	}
	s.mu.Lock()
	defer s.mu.Unlock()

	writer := s.writer
	writer.mu.Lock()
	defer writer.mu.Unlock()

	evidence := WriteEvidence{
		SourceRowCount:  writer.totalRecords,
		SpoolByteLength: writer.totalBytes,
		Accepted:        evidenceOf(writer.accepted),
		Rejected:        evidenceOf(writer.rejected),
	}
	payload, digest, err := buildManifest(writer.attempt.id, input, evidence)
	if err != nil {
		if s.sealed {
			return SealEvidence{}, ErrSealConflict
		}
		return SealEvidence{}, writer.fail(err)
	}
	if s.sealed {
		if digest != s.sealDigest {
			return SealEvidence{}, ErrSealConflict
		}
		return s.evidence, nil
	}
	if writer.terminalErr != nil {
		return SealEvidence{}, writer.terminalErr
	}
	if writer.closed {
		return SealEvidence{}, ErrStreamWriterClosed
	}
	if ctx == nil {
		return SealEvidence{}, writer.fail(errors.New("Preview spool seal requires context"))
	}
	if err := ctx.Err(); err != nil {
		return SealEvidence{}, writer.fail(err)
	}
	if writer.accepted.recordCount == 0 {
		return SealEvidence{}, writer.fail(ErrAcceptedRecordRequired)
	}

	attempt := writer.attempt
	attempt.mu.Lock()
	defer attempt.mu.Unlock()
	if attempt.cleaned {
		return SealEvidence{}, writer.failLocked(ErrAttemptMissing)
	}
	if attempt.accepted == nil || attempt.rejected == nil {
		return SealEvidence{}, writer.failLocked(ErrAttemptMissing)
	}
	if err := s.ops.syncFile(attempt.accepted); err != nil {
		return SealEvidence{}, writer.failLocked(fmt.Errorf("fsync accepted Preview spool stream: %w", err))
	}
	if err := ctx.Err(); err != nil {
		return SealEvidence{}, writer.failLocked(err)
	}
	if err := s.ops.syncFile(attempt.rejected); err != nil {
		return SealEvidence{}, writer.failLocked(fmt.Errorf("fsync rejected Preview spool stream: %w", err))
	}
	if err := ctx.Err(); err != nil {
		return SealEvidence{}, writer.failLocked(err)
	}
	if err := closeStreamFilesLocked(attempt); err != nil {
		return SealEvidence{}, writer.failLocked(fmt.Errorf("close Preview spool streams before seal: %w", err))
	}

	writer.evidence = evidence
	writer.closed = true
	if err := publishManifestAtomic(ctx, attempt, payload, s.ops); err != nil {
		if writer.terminalErr == nil {
			writer.terminalErr = err
		}
		return SealEvidence{}, writer.terminalErr
	}

	sum := sha256.Sum256(payload)
	result := SealEvidence{
		WriteEvidence:      evidence,
		ManifestByteLength: int64(len(payload)),
		ManifestSHA256:     hex.EncodeToString(sum[:]),
	}
	s.sealed = true
	s.sealDigest = digest
	s.evidence = result
	return result, nil
}

func publishManifestAtomic(ctx context.Context, attempt *Attempt, payload []byte, ops sealOperations) error {
	manager := attempt.manager
	manager.mu.Lock()
	defer manager.mu.Unlock()
	if manager.closed {
		return ErrManagerClosed
	}
	if err := manager.verifyRootDescriptor(); err != nil {
		return err
	}

	dirFD, err := syscall.Openat(manager.rootFD, attempt.id, syscall.O_RDONLY|syscall.O_DIRECTORY|syscall.O_CLOEXEC|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return fmt.Errorf("open Preview spool attempt for seal: %w", err)
	}
	defer syscall.Close(dirFD)

	var stat syscall.Stat_t
	if err := syscall.Fstat(dirFD, &stat); err != nil {
		return fmt.Errorf("fstat Preview spool attempt for seal: %w", err)
	}
	if uint64(stat.Dev) != attempt.dirDev || stat.Ino != attempt.dirIno {
		return ErrAttemptSubstituted
	}
	if err := verifyDirectoryStat(&stat); err != nil {
		return fmt.Errorf("%w: %v", ErrUnsafeEntry, err)
	}
	if entryExistsAt(dirFD, ManifestFileName) || entryExistsAt(dirFD, ManifestTempFileName) {
		return ErrSealPublicationExists
	}

	temp, err := createExclusiveFile(dirFD, ManifestTempFileName)
	if err != nil {
		return fmt.Errorf("%w: create manifest temp: %v", ErrSealPublish, err)
	}
	tempClosed := false
	defer func() {
		if !tempClosed {
			_ = temp.Close()
		}
		_ = syscall.Unlinkat(dirFD, ManifestTempFileName)
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

	if err := ops.linkNoReplace(dirFD, ManifestTempFileName, dirFD, ManifestFileName); err != nil {
		if errors.Is(err, syscall.EEXIST) {
			return ErrSealPublicationExists
		}
		return fmt.Errorf("%w: publish manifest: %v", ErrSealPublish, err)
	}
	if err := syscall.Unlinkat(dirFD, ManifestTempFileName); err != nil {
		rollbackErr := syscall.Unlinkat(dirFD, ManifestFileName)
		return errors.Join(fmt.Errorf("%w: remove manifest temp: %v", ErrSealPublish, err), rollbackErr)
	}
	if err := ops.syncDir(dirFD); err != nil {
		unlinkErr := syscall.Unlinkat(dirFD, ManifestFileName)
		rollbackSyncErr := ops.syncDir(dirFD)
		if unlinkErr != nil || rollbackSyncErr != nil {
			return errors.Join(ErrSealDurabilityUncertain, fmt.Errorf("directory fsync after publish: %w", err), unlinkErr, rollbackSyncErr)
		}
		return fmt.Errorf("%w: directory fsync after publish: %v", ErrSealPublish, err)
	}
	return nil
}

func entryExistsAt(dirFD int, name string) bool {
	fd, err := syscall.Openat(dirFD, name, syscall.O_RDONLY|syscall.O_CLOEXEC|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return !errors.Is(err, syscall.ENOENT)
	}
	_ = syscall.Close(fd)
	return true
}

func linkatNoReplace(oldDirFD int, oldName string, newDirFD int, newName string) error {
	oldPointer, err := syscall.BytePtrFromString(oldName)
	if err != nil {
		return err
	}
	newPointer, err := syscall.BytePtrFromString(newName)
	if err != nil {
		return err
	}
	_, _, errno := syscall.Syscall6(
		syscall.SYS_LINKAT,
		uintptr(oldDirFD),
		uintptr(unsafe.Pointer(oldPointer)),
		uintptr(newDirFD),
		uintptr(unsafe.Pointer(newPointer)),
		0,
		0,
	)
	if errno != 0 {
		return errno
	}
	return nil
}
