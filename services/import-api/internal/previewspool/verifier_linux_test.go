//go:build linux

package previewspool

import (
	"bytes"
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func newSealedSpool(t *testing.T) (*Manager, string, SealInput, SealEvidence) {
	t.Helper()
	manager, root := newTestManager(t)
	attempt, err := manager.CreateAttempt(context.Background(), testSpoolID)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = attempt.Cleanup() })
	writer, err := NewStreamWriter(attempt)
	if err != nil {
		t.Fatal(err)
	}
	if err := writer.WriteAccepted(context.Background(), []byte("accepted-canonical-record")); err != nil {
		t.Fatal(err)
	}
	if err := writer.WriteRejected(context.Background(), []byte("rejected-canonical-record")); err != nil {
		t.Fatal(err)
	}
	sealer, err := NewSealer(writer)
	if err != nil {
		t.Fatal(err)
	}
	input := validSealInput()
	evidence, err := sealer.Seal(context.Background(), input)
	if err != nil {
		t.Fatal(err)
	}
	return manager, filepath.Join(root, testSpoolID), input, evidence
}

func expectationOf(input SealInput) VerifyExpectation {
	return VerifyExpectation{
		JobID:          input.JobID,
		OwnerAccountID: input.OwnerAccountID,
		AccountEpoch:   input.AccountEpoch,
		Source:         input.Source,
		Adapter:        input.Adapter,
		OptionsSHA256:  input.OptionsSHA256,
	}
}

func verifyNow() time.Time {
	return validSealInput().CreatedAt.Add(time.Hour)
}

func TestVerifierAcceptsSealedSpoolAndIsRepeatable(t *testing.T) {
	manager, _, input, sealed := newSealedSpool(t)
	verifier, err := NewVerifier(manager)
	if err != nil {
		t.Fatal(err)
	}
	result, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), verifyNow())
	if err != nil {
		t.Fatal(err)
	}
	if result.Evidence != sealed.WriteEvidence {
		t.Fatalf("recomputed evidence mismatch: %+v", result.Evidence)
	}
	if result.ManifestByteLength != sealed.ManifestByteLength || result.ManifestSHA256 != sealed.ManifestSHA256 {
		t.Fatalf("manifest evidence mismatch: %+v", result)
	}
	if result.SpoolID != testSpoolID || result.JobID != input.JobID || result.OwnerAccountID != input.OwnerAccountID || result.AccountEpoch != input.AccountEpoch {
		t.Fatalf("identity binding mismatch: %+v", result)
	}
	if result.Source != input.Source || result.Adapter != input.Adapter || result.OptionsSHA256 != input.OptionsSHA256 {
		t.Fatalf("source binding mismatch: %+v", result)
	}
	if !result.CreatedAt.Equal(input.CreatedAt) || !result.ExpiresAt.Equal(input.ExpiresAt) {
		t.Fatalf("timestamp binding mismatch: %+v", result)
	}
	again, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), verifyNow())
	if err != nil || again != result {
		t.Fatalf("verification was not repeatable: %+v %v", again, err)
	}
}

func TestVerifierValidatesInputs(t *testing.T) {
	manager, _, input, _ := newSealedSpool(t)
	verifier, err := NewVerifier(manager)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := NewVerifier(nil); !errors.Is(err, ErrInvalidRoot) {
		t.Fatalf("nil manager was accepted: %v", err)
	}
	var missingCtx context.Context
	if _, err := verifier.Verify(missingCtx, testSpoolID, expectationOf(input), verifyNow()); !errors.Is(err, ErrVerifyInvalidInput) {
		t.Fatalf("nil context was accepted: %v", err)
	}
	if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), time.Time{}); !errors.Is(err, ErrVerifyInvalidInput) {
		t.Fatalf("zero clock was accepted: %v", err)
	}
	if _, err := verifier.Verify(context.Background(), "../escape", expectationOf(input), verifyNow()); !errors.Is(err, ErrInvalidSpoolID) {
		t.Fatalf("invalid spool ID was accepted: %v", err)
	}
	if _, err := verifier.Verify(context.Background(), "spl_01J00000000000000000000001", expectationOf(input), verifyNow()); !errors.Is(err, ErrAttemptMissing) {
		t.Fatalf("unknown attempt was accepted: %v", err)
	}
	if err := manager.Close(); err != nil {
		t.Fatal(err)
	}
	if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), verifyNow()); !errors.Is(err, ErrManagerClosed) {
		t.Fatalf("closed manager was usable: %v", err)
	}
}

func TestVerifierRejectsUnsealedAttempt(t *testing.T) {
	t.Run("manifest-placeholder", func(t *testing.T) {
		manager, _ := newTestManager(t)
		attempt, err := manager.CreateAttempt(context.Background(), testSpoolID)
		if err != nil {
			t.Fatal(err)
		}
		t.Cleanup(func() { _ = attempt.Cleanup() })
		verifier, _ := NewVerifier(manager)
		if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(validSealInput()), verifyNow()); !errors.Is(err, ErrVerifyManifestMalformed) {
			t.Fatalf("empty placeholder manifest was accepted: %v", err)
		}
	})
	t.Run("claimed-not-sealed", func(t *testing.T) {
		manager, _ := newTestManager(t)
		attempt, err := manager.CreateAttempt(context.Background(), testSpoolID)
		if err != nil {
			t.Fatal(err)
		}
		t.Cleanup(func() { _ = attempt.Cleanup() })
		writer, err := NewStreamWriter(attempt)
		if err != nil {
			t.Fatal(err)
		}
		if err := writer.WriteAccepted(context.Background(), []byte("accepted-canonical-record")); err != nil {
			t.Fatal(err)
		}
		verifier, _ := NewVerifier(manager)
		if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(validSealInput()), verifyNow()); !errors.Is(err, ErrVerifyManifestMissing) {
			t.Fatalf("unsealed attempt was accepted: %v", err)
		}
	})
}

func TestVerifierRejectsManifestTempResidue(t *testing.T) {
	manager, directory, input, _ := newSealedSpool(t)
	if err := os.WriteFile(filepath.Join(directory, ManifestTempFileName), []byte("residue"), SpoolFileMode); err != nil {
		t.Fatal(err)
	}
	verifier, _ := NewVerifier(manager)
	if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), verifyNow()); !errors.Is(err, ErrVerifyTempResidue) {
		t.Fatalf("temp residue was accepted: %v", err)
	}
}

func TestVerifierRejectsUnexpectedEntry(t *testing.T) {
	manager, directory, input, _ := newSealedSpool(t)
	if err := os.WriteFile(filepath.Join(directory, "extra.bin"), []byte("extra"), SpoolFileMode); err != nil {
		t.Fatal(err)
	}
	verifier, _ := NewVerifier(manager)
	if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), verifyNow()); !errors.Is(err, ErrUnexpectedEntry) {
		t.Fatalf("unexpected entry was accepted: %v", err)
	}
}

func TestVerifierRejectsBindingMismatch(t *testing.T) {
	manager, directory, input, _ := newSealedSpool(t)
	verifier, _ := NewVerifier(manager)
	mutations := map[string]func(*VerifyExpectation){
		"job-id":        func(e *VerifyExpectation) { e.JobID = "job_01J000000000000000000000001" },
		"owner-account": func(e *VerifyExpectation) { e.OwnerAccountID = "acct_01J00000000000000000000001" },
		"account-epoch": func(e *VerifyExpectation) { e.AccountEpoch++ },
		"object-key": func(e *VerifyExpectation) {
			e.Source.ObjectKey = "quarantine/job_01J000000000000000000000000/upl_01J00000000000000000000001"
		},
		"object-version": func(e *VerifyExpectation) { e.Source.ObjectVersionID = "version-01J00000000000000000000001" },
		"content-length": func(e *VerifyExpectation) { e.Source.ContentLength++ },
		"source-checksum": func(e *VerifyExpectation) {
			e.Source.ChecksumSHA256 = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
		},
		"adapter-id":      func(e *VerifyExpectation) { e.Adapter.AdapterID = "generic-tsv" },
		"adapter-version": func(e *VerifyExpectation) { e.Adapter.AdapterVersion = "1.0.1" },
		"adapter-artifact": func(e *VerifyExpectation) {
			e.Adapter.ArtifactSHA256 = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
		},
		"options-digest": func(e *VerifyExpectation) {
			e.OptionsSHA256 = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
		},
	}
	for name, mutate := range mutations {
		expectation := expectationOf(input)
		mutate(&expectation)
		if _, err := verifier.Verify(context.Background(), testSpoolID, expectation, verifyNow()); !errors.Is(err, ErrVerifyBindingMismatch) {
			t.Fatalf("%s mismatch was accepted: %v", name, err)
		}
	}

	path := filepath.Join(directory, ManifestFileName)
	payload, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	spoofed := bytes.Replace(payload, []byte(testSpoolID), []byte("spl_01J00000000000000000000001"), 1)
	if err := os.WriteFile(path, spoofed, SpoolFileMode); err != nil {
		t.Fatal(err)
	}
	if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), verifyNow()); !errors.Is(err, ErrVerifyBindingMismatch) {
		t.Fatalf("spoofed spool ID was accepted: %v", err)
	}
}

func TestVerifierRejectsExpiredManifest(t *testing.T) {
	manager, _, input, _ := newSealedSpool(t)
	verifier, _ := NewVerifier(manager)
	if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), input.ExpiresAt); !errors.Is(err, ErrVerifyExpired) {
		t.Fatalf("expiry boundary was accepted: %v", err)
	}
	if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), input.ExpiresAt.Add(time.Hour)); !errors.Is(err, ErrVerifyExpired) {
		t.Fatalf("expired manifest was accepted: %v", err)
	}
	if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), input.ExpiresAt.Add(-time.Nanosecond)); err != nil {
		t.Fatalf("unexpired manifest was rejected: %v", err)
	}
}

func TestVerifierRejectsNonCanonicalManifest(t *testing.T) {
	cases := map[string]func([]byte) []byte{
		"trailing-whitespace": func(payload []byte) []byte {
			return append(append([]byte{}, payload...), '\n')
		},
		"unknown-field": func(payload []byte) []byte {
			body := append([]byte{}, payload[:len(payload)-1]...)
			return append(body, []byte(`,"extra":true}`)...)
		},
		"inflated-row-count": func(payload []byte) []byte {
			return bytes.Replace(payload, []byte(`"sourceRowCount":2`), []byte(`"sourceRowCount":3`), 1)
		},
		"disabled-rehash-constant": func(payload []byte) []byte {
			return bytes.Replace(payload, []byte(`"rehashRequiredBeforeCommit":true`), []byte(`"rehashRequiredBeforeCommit":false`), 1)
		},
	}
	for name, mutate := range cases {
		t.Run(name, func(t *testing.T) {
			manager, directory, input, _ := newSealedSpool(t)
			path := filepath.Join(directory, ManifestFileName)
			payload, err := os.ReadFile(path)
			if err != nil {
				t.Fatal(err)
			}
			mutated := mutate(payload)
			if bytes.Equal(mutated, payload) {
				t.Fatal("mutation did not change the manifest")
			}
			if err := os.WriteFile(path, mutated, SpoolFileMode); err != nil {
				t.Fatal(err)
			}
			verifier, _ := NewVerifier(manager)
			if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), verifyNow()); !errors.Is(err, ErrVerifyManifestMalformed) {
				t.Fatalf("non-canonical manifest was accepted: %v", err)
			}
		})
	}
}

func TestVerifierRejectsUnsafeEntries(t *testing.T) {
	t.Run("manifest-hard-link", func(t *testing.T) {
		manager, directory, input, _ := newSealedSpool(t)
		if err := os.Link(filepath.Join(directory, ManifestFileName), filepath.Join(filepath.Dir(directory), "stolen-manifest")); err != nil {
			t.Fatal(err)
		}
		verifier, _ := NewVerifier(manager)
		if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), verifyNow()); !errors.Is(err, ErrUnsafeEntry) {
			t.Fatalf("hard-linked manifest was accepted: %v", err)
		}
	})
	t.Run("stream-symlink", func(t *testing.T) {
		manager, directory, input, _ := newSealedSpool(t)
		outside := filepath.Join(filepath.Dir(directory), "outside-stream")
		if err := os.Rename(filepath.Join(directory, RejectedFileName), outside); err != nil {
			t.Fatal(err)
		}
		if err := os.Symlink(outside, filepath.Join(directory, RejectedFileName)); err != nil {
			t.Fatal(err)
		}
		verifier, _ := NewVerifier(manager)
		if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), verifyNow()); !errors.Is(err, ErrUnsafeEntry) {
			t.Fatalf("stream symlink was followed: %v", err)
		}
	})
	t.Run("stream-mode", func(t *testing.T) {
		manager, directory, input, _ := newSealedSpool(t)
		if err := os.Chmod(filepath.Join(directory, AcceptedFileName), 0o644); err != nil {
			t.Fatal(err)
		}
		verifier, _ := NewVerifier(manager)
		if _, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), verifyNow()); !errors.Is(err, ErrUnsafeEntry) {
			t.Fatalf("world-readable stream was accepted: %v", err)
		}
	})
}

func TestVerifierCancellationIsRetryable(t *testing.T) {
	manager, _, input, sealed := newSealedSpool(t)
	verifier, _ := NewVerifier(manager)
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := verifier.Verify(ctx, testSpoolID, expectationOf(input), verifyNow()); !errors.Is(err, context.Canceled) {
		t.Fatalf("expected cancellation, got %v", err)
	}
	result, err := verifier.Verify(context.Background(), testSpoolID, expectationOf(input), verifyNow())
	if err != nil {
		t.Fatalf("cancelled verification was sticky: %v", err)
	}
	if result.Evidence != sealed.WriteEvidence {
		t.Fatalf("retried evidence mismatch: %+v", result.Evidence)
	}
}
