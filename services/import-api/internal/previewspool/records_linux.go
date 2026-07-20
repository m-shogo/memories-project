//go:build linux

package previewspool

import (
	"bufio"
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"os"
)

// CollectSealedRecords re-opens both sealed streams with the verifier's
// descriptor-relative safety checks and returns every canonical record in
// stream order. The recomputed counts, byte totals and hashes must equal the
// already-verified evidence, so the returned records are exactly the bytes
// that independent verification hashed. Memory is bounded by the spool limits;
// callers hold the decoded records exactly like the commit path does.
func CollectSealedRecords(ctx context.Context, manager *Manager, verified VerifiedSpool) ([][]byte, [][]byte, error) {
	verifier, err := NewVerifier(manager)
	if err != nil {
		return nil, nil, err
	}
	if ctx == nil {
		return nil, nil, ErrVerifyInvalidInput
	}
	if !validSpoolID(verified.SpoolID) {
		return nil, nil, ErrInvalidSpoolID
	}
	if err := ctx.Err(); err != nil {
		return nil, nil, err
	}
	directory, err := verifier.openAttemptDirectory(verified.SpoolID)
	if err != nil {
		return nil, nil, err
	}
	defer directory.Close()
	if err := verifyAttemptEntryNames(directory); err != nil {
		return nil, nil, err
	}
	accepted, err := collectStreamRecords(ctx, directory, AcceptedFileName, AcceptedRecordFormat, verified.Evidence.Accepted)
	if err != nil {
		return nil, nil, err
	}
	rejected, err := collectStreamRecords(ctx, directory, RejectedFileName, RejectedRecordFormat, verified.Evidence.Rejected)
	if err != nil {
		return nil, nil, err
	}
	return accepted, rejected, nil
}

func collectStreamRecords(ctx context.Context, directory *os.File, name string, recordFormat string, sealed StreamEvidence) ([][]byte, error) {
	file, _, err := openVerifyRegularFile(directory, name, ErrVerifyStreamMissing)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	reader := bufio.NewReaderSize(file, streamScanBufferBytes)
	hasher := sha256.New()
	records := make([][]byte, 0, sealed.RecordCount)
	recordCount := 0
	var byteLength int64
	var prefix [8]byte
	for {
		if err := ctx.Err(); err != nil {
			return nil, err
		}
		if _, err := io.ReadFull(reader, prefix[:]); err != nil {
			if errors.Is(err, io.EOF) {
				break
			}
			return nil, fmt.Errorf("%w: torn length prefix", ErrVerifyStreamMalformed)
		}
		length := binary.BigEndian.Uint64(prefix[:])
		if length < 1 || length > uint64(MaxCanonicalRecordBytes) {
			return nil, fmt.Errorf("%w: record length %d", ErrVerifyStreamMalformed, length)
		}
		if recordCount >= MaxSpoolRecords {
			return nil, fmt.Errorf("%w: record limit exceeded", ErrVerifyStreamMalformed)
		}
		recordBytes := int64(8 + length)
		if recordBytes > MaxSpoolBytes-byteLength {
			return nil, fmt.Errorf("%w: byte limit exceeded", ErrVerifyStreamMalformed)
		}
		payload := make([]byte, length)
		if _, err := io.ReadFull(reader, payload); err != nil {
			return nil, fmt.Errorf("%w: torn record body", ErrVerifyStreamMalformed)
		}
		_, _ = hasher.Write(prefix[:])
		_, _ = hasher.Write(payload)
		records = append(records, payload)
		recordCount++
		byteLength += recordBytes
	}
	actual := StreamEvidence{
		RecordFormat: recordFormat,
		RecordCount:  recordCount,
		ByteLength:   byteLength,
		SHA256:       hex.EncodeToString(hasher.Sum(nil)),
	}
	if actual != sealed {
		return nil, fmt.Errorf("%w: %s", ErrVerifyStreamMismatch, name)
	}
	return records, nil
}
