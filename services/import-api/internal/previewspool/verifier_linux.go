//go:build linux

package previewspool

import (
	"bufio"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"os"
	"syscall"
	"time"
)

const streamScanBufferBytes = 64 * 1024

// Verifier independently re-reads one sealed attempt from disk. It shares no
// state with the writer or sealer, keeps no cross-call state and trusts only
// the verified root descriptor, so a cancelled or failed verification is
// retryable and a passed verification reflects the exact on-disk bytes.
type Verifier struct {
	manager *Manager
}

func NewVerifier(manager *Manager) (*Verifier, error) {
	if manager == nil {
		return nil, ErrInvalidRoot
	}
	return &Verifier{manager: manager}, nil
}

// Verify strictly decodes the published manifest, re-opens both streams
// through the attempt directory descriptor, independently re-counts and
// re-hashes their exact bytes and compares every binding. Any mismatch rejects
// the spool before a database transaction can start.
func (v *Verifier) Verify(ctx context.Context, spoolID string, expected VerifyExpectation, now time.Time) (VerifiedSpool, error) {
	if v == nil || v.manager == nil {
		return VerifiedSpool{}, ErrInvalidRoot
	}
	if ctx == nil || now.IsZero() {
		return VerifiedSpool{}, ErrVerifyInvalidInput
	}
	if !validSpoolID(spoolID) {
		return VerifiedSpool{}, ErrInvalidSpoolID
	}
	if err := ctx.Err(); err != nil {
		return VerifiedSpool{}, err
	}

	directory, err := v.openAttemptDirectory(spoolID)
	if err != nil {
		return VerifiedSpool{}, err
	}
	defer directory.Close()

	if err := verifyAttemptEntryNames(directory); err != nil {
		return VerifiedSpool{}, err
	}
	if err := ctx.Err(); err != nil {
		return VerifiedSpool{}, err
	}

	payload, err := readManifestPayload(directory)
	if err != nil {
		return VerifiedSpool{}, err
	}
	doc, input, sealed, err := decodeSealedManifest(payload)
	if err != nil {
		return VerifiedSpool{}, err
	}
	if doc.SpoolID != spoolID {
		return VerifiedSpool{}, fmt.Errorf("%w: manifest spool ID %q", ErrVerifyBindingMismatch, doc.SpoolID)
	}
	if !now.Before(input.ExpiresAt) {
		return VerifiedSpool{}, ErrVerifyExpired
	}
	if !matchExpectation(input, expected) {
		return VerifiedSpool{}, ErrVerifyBindingMismatch
	}

	recomputed := WriteEvidence{}
	streams := []struct {
		name   string
		format string
		sealed StreamEvidence
		target *StreamEvidence
	}{
		{AcceptedFileName, AcceptedRecordFormat, sealed.Accepted, &recomputed.Accepted},
		{RejectedFileName, RejectedRecordFormat, sealed.Rejected, &recomputed.Rejected},
	}
	for _, stream := range streams {
		if err := ctx.Err(); err != nil {
			return VerifiedSpool{}, err
		}
		actual, err := verifyStreamFile(ctx, directory, stream.name, stream.format)
		if err != nil {
			return VerifiedSpool{}, err
		}
		if actual != stream.sealed {
			return VerifiedSpool{}, fmt.Errorf("%w: %s", ErrVerifyStreamMismatch, stream.name)
		}
		*stream.target = actual
	}
	recomputed.SourceRowCount = recomputed.Accepted.RecordCount + recomputed.Rejected.RecordCount
	recomputed.SpoolByteLength = recomputed.Accepted.ByteLength + recomputed.Rejected.ByteLength

	sum := sha256.Sum256(payload)
	return VerifiedSpool{
		SpoolID:            doc.SpoolID,
		JobID:              input.JobID,
		OwnerAccountID:     input.OwnerAccountID,
		AccountEpoch:       input.AccountEpoch,
		Source:             input.Source,
		Adapter:            input.Adapter,
		OptionsSHA256:      input.OptionsSHA256,
		CreatedAt:          input.CreatedAt,
		ExpiresAt:          input.ExpiresAt,
		Evidence:           recomputed,
		ManifestByteLength: int64(len(payload)),
		ManifestSHA256:     hex.EncodeToString(sum[:]),
	}, nil
}

func (v *Verifier) openAttemptDirectory(spoolID string) (*os.File, error) {
	m := v.manager
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.closed {
		return nil, ErrManagerClosed
	}
	if err := m.verifyRootDescriptor(); err != nil {
		return nil, err
	}
	fd, err := syscall.Openat(m.rootFD, spoolID, syscall.O_RDONLY|syscall.O_DIRECTORY|syscall.O_CLOEXEC|syscall.O_NOFOLLOW, 0)
	if err != nil {
		if errors.Is(err, syscall.ENOENT) {
			return nil, ErrAttemptMissing
		}
		if errors.Is(err, syscall.ELOOP) || errors.Is(err, syscall.ENOTDIR) {
			return nil, fmt.Errorf("%w: %s: %v", ErrUnsafeEntry, spoolID, err)
		}
		return nil, fmt.Errorf("open Preview spool attempt for verification: %w", err)
	}
	var stat syscall.Stat_t
	if err := syscall.Fstat(fd, &stat); err != nil {
		_ = syscall.Close(fd)
		return nil, fmt.Errorf("fstat Preview spool attempt for verification: %w", err)
	}
	if err := verifyDirectoryStat(&stat); err != nil {
		_ = syscall.Close(fd)
		return nil, fmt.Errorf("%w: %v", ErrUnsafeEntry, err)
	}
	file := os.NewFile(uintptr(fd), spoolID)
	if file == nil {
		_ = syscall.Close(fd)
		return nil, errors.New("wrap Preview spool attempt directory")
	}
	return file, nil
}

func verifyAttemptEntryNames(directory *os.File) error {
	names, err := directory.Readdirnames(-1)
	if err != nil {
		return fmt.Errorf("list Preview spool attempt for verification: %w", err)
	}
	seen := make(map[string]bool, 3)
	unknown := ""
	tempResidue := false
	for _, name := range names {
		switch name {
		case AcceptedFileName, RejectedFileName, ManifestFileName:
			seen[name] = true
		case ManifestTempFileName:
			tempResidue = true
		default:
			if unknown == "" {
				unknown = name
			}
		}
	}
	if tempResidue {
		return ErrVerifyTempResidue
	}
	if unknown != "" {
		return fmt.Errorf("%w: %s", ErrUnexpectedEntry, unknown)
	}
	if !seen[ManifestFileName] {
		return ErrVerifyManifestMissing
	}
	if !seen[AcceptedFileName] || !seen[RejectedFileName] {
		return ErrVerifyStreamMissing
	}
	return nil
}

func readManifestPayload(directory *os.File) ([]byte, error) {
	file, size, err := openVerifyRegularFile(directory, ManifestFileName, ErrVerifyManifestMissing)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	if size < 1 || size > MaxManifestBytes {
		return nil, fmt.Errorf("%w: manifest length %d", ErrVerifyManifestMalformed, size)
	}
	payload := make([]byte, size)
	if _, err := io.ReadFull(file, payload); err != nil {
		return nil, fmt.Errorf("%w: manifest read: %v", ErrVerifyManifestMalformed, err)
	}
	var extra [1]byte
	if n, err := file.Read(extra[:]); n != 0 || !errors.Is(err, io.EOF) {
		return nil, fmt.Errorf("%w: manifest changed during verification", ErrVerifyManifestMalformed)
	}
	return payload, nil
}

func verifyStreamFile(ctx context.Context, directory *os.File, name string, recordFormat string) (StreamEvidence, error) {
	file, _, err := openVerifyRegularFile(directory, name, ErrVerifyStreamMissing)
	if err != nil {
		return StreamEvidence{}, err
	}
	defer file.Close()
	evidence, err := scanLengthPrefixedStream(ctx, bufio.NewReaderSize(file, streamScanBufferBytes), recordFormat)
	if err != nil {
		if errors.Is(err, ErrVerifyStreamMalformed) {
			return StreamEvidence{}, fmt.Errorf("%s: %w", name, err)
		}
		return StreamEvidence{}, err
	}
	return evidence, nil
}

func openVerifyRegularFile(directory *os.File, name string, missing error) (*os.File, int64, error) {
	fd, err := syscall.Openat(int(directory.Fd()), name, syscall.O_RDONLY|syscall.O_CLOEXEC|syscall.O_NOFOLLOW, 0)
	if err != nil {
		if errors.Is(err, syscall.ENOENT) {
			return nil, 0, missing
		}
		if errors.Is(err, syscall.ELOOP) {
			return nil, 0, fmt.Errorf("%w: %s: %v", ErrUnsafeEntry, name, err)
		}
		return nil, 0, fmt.Errorf("open Preview spool %s for verification: %w", name, err)
	}
	var stat syscall.Stat_t
	if err := syscall.Fstat(fd, &stat); err != nil {
		_ = syscall.Close(fd)
		return nil, 0, fmt.Errorf("fstat Preview spool %s for verification: %w", name, err)
	}
	if err := verifyRegularFileStat(&stat); err != nil {
		_ = syscall.Close(fd)
		return nil, 0, fmt.Errorf("%w: %s: %v", ErrUnsafeEntry, name, err)
	}
	file := os.NewFile(uintptr(fd), name)
	if file == nil {
		_ = syscall.Close(fd)
		return nil, 0, fmt.Errorf("wrap Preview spool file %s", name)
	}
	return file, stat.Size, nil
}
