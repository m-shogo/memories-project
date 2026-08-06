//go:build linux

package parsersup

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/previewspool"
)

// TestSupervisorRestartRecoveryMatrix proves that distinct worker-failure
// classes do not poison the manager or reserve the spool ID. Every failure is
// followed by an exact same-spool recovery attempt and independent verification.
func TestSupervisorRestartRecoveryMatrix(t *testing.T) {
	tests := []struct {
		name     string
		mode     string
		mutate   func(*Config)
		context  func() context.Context
		expected error
	}{
		{
			name:     "protocol_truncation",
			mode:     "partial",
			expected: ErrFrameProtocolViolation,
		},
		{
			name: "wall_clock_timeout",
			mode: "sleep",
			mutate: func(config *Config) {
				config.Limits.WallClock = 2 * time.Second
			},
			expected: ErrParseTimeout,
		},
		{
			name: "cpu_limit_kill",
			mode: "spin",
			mutate: func(config *Config) {
				config.Limits.CPUSeconds = 1
			},
			expected: ErrWorkerFailed,
		},
		{
			name: "memory_limit_kill",
			mode: "hog",
			mutate: func(config *Config) {
				config.Limits.AddressSpaceBytes = 512 << 20
			},
			expected: ErrWorkerFailed,
		},
		{
			name: "pre_start_cancellation",
			mode: "sleep",
			context: func() context.Context {
				ctx, cancel := context.WithCancel(context.Background())
				cancel()
				return ctx
			},
			expected: context.Canceled,
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			manager, root := newSpoolManager(t)
			failedConfig := testConfig(t, test.mode)
			if test.mutate != nil {
				test.mutate(&failedConfig)
			}
			failedSupervisor, err := NewSupervisor(failedConfig)
			if err != nil {
				t.Fatal(err)
			}
			ctx := context.Background()
			if test.context != nil {
				ctx = test.context()
			}
			_, err = failedSupervisor.Parse(ctx, ParseRequest{
				Manager: manager,
				SpoolID: testSpoolID,
				Source:  sourceFile(t, "a:{\"title\":\"failed\"}\n"),
				Seal:    testSealInput(),
			})
			if !errors.Is(err, test.expected) {
				t.Fatalf("failure class drift: got %v want %v", err, test.expected)
			}
			assertRootEmpty(t, root)

			replacementConfig := testConfig(t, "parse")
			replacementSupervisor, err := NewSupervisor(replacementConfig)
			if err != nil {
				t.Fatal(err)
			}
			evidence, err := replacementSupervisor.Parse(context.Background(), ParseRequest{
				Manager: manager,
				SpoolID: testSpoolID,
				Source:  sourceFile(t, "a:{\"title\":\"recovered\"}\n"),
				Seal:    testSealInput(),
			})
			if err != nil {
				t.Fatalf("replacement worker could not recover the same spool: %v", err)
			}
			if evidence.WriteEvidence.Accepted.RecordCount != 1 ||
				evidence.WriteEvidence.Rejected.RecordCount != 0 {
				t.Fatalf("unexpected recovered evidence: %+v", evidence.WriteEvidence)
			}

			seal := testSealInput()
			verifier, err := previewspool.NewVerifier(manager)
			if err != nil {
				t.Fatal(err)
			}
			verified, err := verifier.Verify(context.Background(), testSpoolID, previewspool.VerifyExpectation{
				JobID:          seal.JobID,
				OwnerAccountID: seal.OwnerAccountID,
				AccountEpoch:   seal.AccountEpoch,
				Source:         seal.Source,
				Adapter:        seal.Adapter,
				OptionsSHA256:  seal.OptionsSHA256,
			}, seal.CreatedAt.Add(time.Second))
			if err != nil {
				t.Fatalf("recovered spool failed independent verification: %v", err)
			}
			if verified.Evidence != evidence.WriteEvidence {
				t.Fatalf("recovered verification drift: got %+v want %+v", verified.Evidence, evidence.WriteEvidence)
			}
		})
	}
}
