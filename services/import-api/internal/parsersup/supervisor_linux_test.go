//go:build linux

package parsersup

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/previewspool"
)

const testSpoolID = "spl_01J00000000000000000000000"

func TestMain(m *testing.M) {
	if mode := os.Getenv(WorkerModeEnv); mode != "" {
		os.Exit(RunWorker(mode, os.Stdin, os.Stdout))
	}
	os.Exit(m.Run())
}

func workerBinary(t *testing.T) (string, string) {
	t.Helper()
	path, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	file, err := os.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	defer file.Close()
	hasher := sha256.New()
	if _, err := io.Copy(hasher, file); err != nil {
		t.Fatal(err)
	}
	return path, hex.EncodeToString(hasher.Sum(nil))
}

func testConfig(t *testing.T, mode string) Config {
	t.Helper()
	path, digest := workerBinary(t)
	addressSpace := uint64(4 << 30)
	if raceDetectorEnabled {
		addressSpace = 1 << 46
	}
	return Config{
		WorkerPath:   path,
		WorkerSHA256: digest,
		WorkerEnv:    []string{WorkerModeEnv + "=" + mode},
		Limits: Limits{
			AddressSpaceBytes: addressSpace,
			CPUSeconds:        2,
			OpenFiles:         64,
			OutputBytes:       1 << 20,
			WallClock:         30 * time.Second,
		},
	}
}

func newSpoolManager(t *testing.T) (*previewspool.Manager, string) {
	t.Helper()
	root := filepath.Join(t.TempDir(), "spool")
	if err := os.Mkdir(root, 0o700); err != nil {
		t.Fatal(err)
	}
	manager, err := previewspool.OpenManager(root)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = manager.Close() })
	return manager, root
}

func sourceFile(t *testing.T, content string) *os.File {
	t.Helper()
	path := filepath.Join(t.TempDir(), "source.csv")
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}
	file, err := os.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = file.Close() })
	return file
}

func testSealInput() previewspool.SealInput {
	createdAt := time.Now().UTC().Add(-time.Minute)
	return previewspool.SealInput{
		JobID:          "job_01J000000000000000000000000",
		OwnerAccountID: "acct_01J00000000000000000000000",
		AccountEpoch:   7,
		Source: previewspool.SealSourceBinding{
			ObjectKey:       "quarantine/job_01J000000000000000000000000/upl_01J00000000000000000000000",
			ObjectVersionID: "version-01J00000000000000000000000",
			ContentLength:   4096,
			ChecksumSHA256:  strings.Repeat("a", 64),
		},
		Adapter: previewspool.SealAdapterBinding{
			AdapterID:      "generic-csv",
			AdapterVersion: "1.0.0",
			ArtifactSHA256: strings.Repeat("b", 64),
		},
		OptionsSHA256: strings.Repeat("c", 64),
		CreatedAt:     createdAt,
		ExpiresAt:     createdAt.Add(time.Hour),
	}
}

func runParse(t *testing.T, mode string, source string, mutate func(*Config)) (previewspool.SealEvidence, *previewspool.Manager, string, error) {
	t.Helper()
	config := testConfig(t, mode)
	if mutate != nil {
		mutate(&config)
	}
	supervisor, err := NewSupervisor(config)
	if err != nil {
		t.Fatal(err)
	}
	manager, root := newSpoolManager(t)
	evidence, err := supervisor.Parse(context.Background(), ParseRequest{
		Manager: manager,
		SpoolID: testSpoolID,
		Source:  sourceFile(t, source),
		Seal:    testSealInput(),
	})
	return evidence, manager, root, err
}

func assertRootEmpty(t *testing.T, root string) {
	t.Helper()
	entries, err := os.ReadDir(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 0 {
		t.Fatalf("failed supervision left spool residue: %v", entries)
	}
}

func TestSupervisorParsesSealsAndVerifies(t *testing.T) {
	evidence, manager, _, err := runParse(t, "parse", "a:{\"title\":\"one\"}\nr:{\"sourceRow\":2}\na:{\"title\":\"three\"}\n", nil)
	if err != nil {
		t.Fatal(err)
	}
	if evidence.WriteEvidence.Accepted.RecordCount != 2 || evidence.WriteEvidence.Rejected.RecordCount != 1 {
		t.Fatalf("unexpected sealed evidence: %+v", evidence.WriteEvidence)
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
	}, seal.CreatedAt.Add(time.Minute))
	if err != nil {
		t.Fatal(err)
	}
	if verified.Evidence != evidence.WriteEvidence {
		t.Fatalf("independent verification does not match supervision evidence: %+v", verified.Evidence)
	}
}

func TestSupervisorRefusesArtifactMismatch(t *testing.T) {
	_, _, root, err := runParse(t, "parse", "a:x\n", func(config *Config) {
		config.WorkerSHA256 = strings.Repeat("0", 64)
	})
	if !errors.Is(err, ErrWorkerArtifactMismatch) {
		t.Fatalf("tampered worker artifact was executed: %v", err)
	}
	assertRootEmpty(t, root)
}

func TestSupervisorRejectsCredentialEnvironment(t *testing.T) {
	cases := [][]string{
		{"AWS_SECRET_ACCESS_KEY=leak"},
		{"PGPASSWORD=leak"},
		{"DATABASE_URL=leak"},
		{"SERVICE_API_KEY=leak"},
		{"broken-entry"},
	}
	base := testConfig(t, "parse")
	for _, environment := range cases {
		config := base
		config.WorkerEnv = environment
		if _, err := NewSupervisor(config); !errors.Is(err, ErrInvalidSupervisorConfig) {
			t.Fatalf("credential environment %v was accepted: %v", environment, err)
		}
	}
}

func TestWorkerEnvironmentIsMinimal(t *testing.T) {
	evidence, _, _, err := runParse(t, "env", "", nil)
	if err != nil {
		t.Fatalf("worker saw a non-minimal environment: %v", err)
	}
	if evidence.WriteEvidence.Accepted.RecordCount != 1 {
		t.Fatalf("unexpected evidence: %+v", evidence.WriteEvidence)
	}
}

func TestSupervisorKillsMemoryHog(t *testing.T) {
	if raceDetectorEnabled {
		t.Skip("RLIMIT_AS cannot be enforced on race-instrumented workers; covered by the non-race suite")
	}
	_, _, root, err := runParse(t, "hog", "", nil)
	if !errors.Is(err, ErrWorkerFailed) {
		t.Fatalf("memory hog was not terminated: %v", err)
	}
	assertRootEmpty(t, root)
}

func TestSupervisorKillsCPUSpin(t *testing.T) {
	_, _, root, err := runParse(t, "spin", "", nil)
	if !errors.Is(err, ErrWorkerFailed) {
		t.Fatalf("CPU spin was not terminated: %v", err)
	}
	assertRootEmpty(t, root)
}

func TestSupervisorTimesOutStalledWorker(t *testing.T) {
	_, _, root, err := runParse(t, "sleep", "", func(config *Config) {
		config.Limits.WallClock = 2 * time.Second
	})
	if !errors.Is(err, ErrParseTimeout) {
		t.Fatalf("stalled worker was not timed out: %v", err)
	}
	assertRootEmpty(t, root)
}

func TestSupervisorRejectsProtocolViolations(t *testing.T) {
	for _, mode := range []string{"garbage", "oversize", "partial"} {
		t.Run(mode, func(t *testing.T) {
			_, _, root, err := runParse(t, mode, "", nil)
			if !errors.Is(err, ErrFrameProtocolViolation) {
				t.Fatalf("%s output was accepted: %v", mode, err)
			}
			assertRootEmpty(t, root)
		})
	}
}

func TestSupervisorEnforcesOutputLimit(t *testing.T) {
	source := strings.Repeat("a:0123456789012345678901234567890123456789\n", 64)
	_, _, root, err := runParse(t, "parse", source, func(config *Config) {
		config.Limits.OutputBytes = 256
	})
	if !errors.Is(err, ErrWorkerOutputLimit) {
		t.Fatalf("output flood was accepted: %v", err)
	}
	assertRootEmpty(t, root)
}

func TestSupervisorBlocksWorkerFileWrites(t *testing.T) {
	_, _, root, err := runParse(t, "file", "", nil)
	if !errors.Is(err, ErrWorkerFailed) {
		t.Fatalf("worker file write escaped RLIMIT_FSIZE: %v", err)
	}
	assertRootEmpty(t, root)
	if _, statErr := os.Stat("/tmp/memory-os-parser-escape"); statErr == nil {
		content, _ := os.ReadFile("/tmp/memory-os-parser-escape")
		_ = os.Remove("/tmp/memory-os-parser-escape")
		if len(content) > 0 {
			t.Fatalf("worker wrote %d bytes despite RLIMIT_FSIZE 0", len(content))
		}
	}
}

func TestSupervisorRejectsEmptyParse(t *testing.T) {
	_, _, root, err := runParse(t, "parse", "", nil)
	if !errors.Is(err, previewspool.ErrInvalidSealInput) {
		t.Fatalf("empty parse was sealed: %v", err)
	}
	assertRootEmpty(t, root)
}
