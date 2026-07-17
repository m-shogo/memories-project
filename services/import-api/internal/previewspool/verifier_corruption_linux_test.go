//go:build linux

package previewspool

import (
	"bytes"
	"context"
	"encoding/binary"
	"errors"
	"os"
	"path/filepath"
	"testing"
)

func corruptFile(t *testing.T, path string, mutate func([]byte) []byte) {
	t.Helper()
	value, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	mutated := mutate(value)
	if bytes.Equal(mutated, value) {
		t.Fatal("mutation did not change the stream")
	}
	if err := os.WriteFile(path, mutated, SpoolFileMode); err != nil {
		t.Fatal(err)
	}
}

func TestVerifierRejectsTruncatedStream(t *testing.T) {
	manager, directory, input, _ := newSealedSpool(t)
	corruptFile(t, filepath.Join(directory, AcceptedFileName), func(value []byte) []byte {
		return value[:len(value)-1]
	})
	verifier, _ := NewVerifier(manager)
	if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), verifyNow()); !errors.Is(err, ErrVerifyStreamMalformed) {
		t.Fatalf("truncated stream was accepted: %v", err)
	}
}

func TestVerifierRejectsAppendedRecord(t *testing.T) {
	manager, directory, input, _ := newSealedSpool(t)
	corruptFile(t, filepath.Join(directory, AcceptedFileName), func(value []byte) []byte {
		extra := []byte("appended-canonical-record")
		var prefix [8]byte
		binary.BigEndian.PutUint64(prefix[:], uint64(len(extra)))
		grown := append(append([]byte{}, value...), prefix[:]...)
		return append(grown, extra...)
	})
	verifier, _ := NewVerifier(manager)
	if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), verifyNow()); !errors.Is(err, ErrVerifyStreamMismatch) {
		t.Fatalf("appended record was accepted: %v", err)
	}
}

func TestVerifierRejectsTornAppend(t *testing.T) {
	manager, directory, input, _ := newSealedSpool(t)
	corruptFile(t, filepath.Join(directory, AcceptedFileName), func(value []byte) []byte {
		return append(append([]byte{}, value...), 0x00, 0x00, 0x01)
	})
	verifier, _ := NewVerifier(manager)
	if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), verifyNow()); !errors.Is(err, ErrVerifyStreamMalformed) {
		t.Fatalf("torn append was accepted: %v", err)
	}
}

func TestVerifierRejectsMalformedLengthPrefix(t *testing.T) {
	cases := map[string]uint64{
		"zero-length":      0,
		"oversized-length": uint64(MaxCanonicalRecordBytes) + 1,
	}
	for name, length := range cases {
		t.Run(name, func(t *testing.T) {
			manager, directory, input, _ := newSealedSpool(t)
			corruptFile(t, filepath.Join(directory, AcceptedFileName), func(value []byte) []byte {
				mutated := append([]byte{}, value...)
				binary.BigEndian.PutUint64(mutated[:8], length)
				return mutated
			})
			verifier, _ := NewVerifier(manager)
			if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), verifyNow()); !errors.Is(err, ErrVerifyStreamMalformed) {
				t.Fatalf("malformed length prefix was accepted: %v", err)
			}
		})
	}
}

func TestVerifierRejectsContentSubstitution(t *testing.T) {
	for name, file := range map[string]string{
		"accepted": AcceptedFileName,
		"rejected": RejectedFileName,
	} {
		t.Run(name, func(t *testing.T) {
			manager, directory, input, _ := newSealedSpool(t)
			corruptFile(t, filepath.Join(directory, file), func(value []byte) []byte {
				mutated := append([]byte{}, value...)
				mutated[8] ^= 0x01
				return mutated
			})
			verifier, _ := NewVerifier(manager)
			if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), verifyNow()); !errors.Is(err, ErrVerifyStreamMismatch) {
				t.Fatalf("substituted %s content was accepted: %v", name, err)
			}
		})
	}
}
