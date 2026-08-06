//go:build linux

package parsersup

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"
	"unsafe"

	"github.com/m-shogo/memories-project/services/import-api/internal/previewspool"
)

var (
	ErrInvalidSupervisorConfig = errors.New("invalid parser supervisor configuration")
	ErrInvalidParseRequest     = errors.New("invalid parser supervision request")
	ErrWorkerArtifactMismatch  = errors.New("parser worker artifact digest mismatch")
	ErrWorkerFailed            = errors.New("parser worker failed")
	ErrParseTimeout            = errors.New("parser worker exceeded the wall-clock limit")
)

// Limits bound one parser worker. Address space, CPU time, descriptor count,
// file size (fixed at zero: the worker may not create file content) and core
// dumps are enforced by the kernel via prlimit; output bytes and wall clock
// are enforced by the supervisor while streaming frames.
type Limits struct {
	AddressSpaceBytes uint64
	CPUSeconds        uint64
	OpenFiles         uint64
	OutputBytes       int64
	WallClock         time.Duration
}

// Config pins one reviewed worker artifact. The environment must be minimal
// and credential-free; anything credential-shaped is rejected up front.
type Config struct {
	WorkerPath   string
	WorkerSHA256 string
	WorkerArgs   []string
	WorkerEnv    []string
	Limits       Limits
}

type Supervisor struct {
	config Config
}

var forbiddenEnvMarkers = []string{
	"SECRET", "TOKEN", "PASSWORD", "CREDENTIAL", "ACCESS_KEY", "PRIVATE_KEY", "API_KEY",
}

var forbiddenEnvPrefixes = []string{"AWS_", "PG", "DATABASE", "MINIO_"}

func NewSupervisor(config Config) (*Supervisor, error) {
	if !filepath.IsAbs(config.WorkerPath) || filepath.Clean(config.WorkerPath) != config.WorkerPath {
		return nil, fmt.Errorf("%w: worker path", ErrInvalidSupervisorConfig)
	}
	digest, err := hex.DecodeString(config.WorkerSHA256)
	if err != nil || len(digest) != sha256.Size {
		return nil, fmt.Errorf("%w: worker digest", ErrInvalidSupervisorConfig)
	}
	limits := config.Limits
	if limits.AddressSpaceBytes < 1<<28 || limits.CPUSeconds < 1 || limits.OpenFiles < 3 ||
		limits.OutputBytes < 1 || limits.WallClock < time.Second || limits.WallClock > time.Hour {
		return nil, fmt.Errorf("%w: limits", ErrInvalidSupervisorConfig)
	}
	for _, entry := range config.WorkerEnv {
		name, _, found := strings.Cut(entry, "=")
		upper := strings.ToUpper(name)
		if !found || name == "" {
			return nil, fmt.Errorf("%w: malformed environment entry", ErrInvalidSupervisorConfig)
		}
		for _, prefix := range forbiddenEnvPrefixes {
			if strings.HasPrefix(upper, prefix) {
				return nil, fmt.Errorf("%w: forbidden environment %s", ErrInvalidSupervisorConfig, name)
			}
		}
		for _, marker := range forbiddenEnvMarkers {
			if strings.Contains(upper, marker) {
				return nil, fmt.Errorf("%w: forbidden environment %s", ErrInvalidSupervisorConfig, name)
			}
		}
	}
	return &Supervisor{config: config}, nil
}

// ParseRequest supervises exactly one attempt: the version-bound source
// content is handed to the worker read-only on stdin, and the worker can reach
// nothing else — the spool, database and credentials stay in the supervisor.
type ParseRequest struct {
	Manager *previewspool.Manager
	SpoolID string
	Source  *os.File
	Seal    previewspool.SealInput
}

// Parse runs one worker to completion:
//
//	verify pinned worker artifact digest
//	→ create one spool attempt and claim its stream writer
//	→ spawn the worker in its own process group with the minimal environment
//	→ apply kernel resource limits via prlimit before consuming output
//	→ stream tagged frames synchronously into the bounded spool writer
//	→ on clean EOF and exit 0: fsync/seal/publish and return sealed evidence
//	→ on any violation, crash, timeout or cancellation: kill the process
//	  group and remove the attempt fail-closed
//
// Kernel limits are applied immediately after spawn; the microseconds before
// they land are bounded by the wall clock and output caps and are accepted
// because the artifact digest pins reviewed worker code. Network isolation is
// a deployment property (namespace/container) and is not claimed here.
func (s *Supervisor) Parse(ctx context.Context, request ParseRequest) (previewspool.SealEvidence, error) {
	if s == nil {
		return previewspool.SealEvidence{}, ErrInvalidSupervisorConfig
	}
	if ctx == nil || request.Manager == nil || request.Source == nil {
		return previewspool.SealEvidence{}, ErrInvalidParseRequest
	}
	if err := ctx.Err(); err != nil {
		return previewspool.SealEvidence{}, err
	}
	if err := s.verifyWorkerArtifact(); err != nil {
		return previewspool.SealEvidence{}, err
	}
	info, err := request.Source.Stat()
	if err != nil || !info.Mode().IsRegular() {
		return previewspool.SealEvidence{}, fmt.Errorf("%w: source must be a regular file", ErrInvalidParseRequest)
	}
	if _, err := request.Source.Seek(0, io.SeekStart); err != nil {
		return previewspool.SealEvidence{}, fmt.Errorf("rewind parse source: %w", err)
	}

	attempt, err := request.Manager.CreateAttempt(ctx, request.SpoolID)
	if err != nil {
		return previewspool.SealEvidence{}, err
	}
	writer, err := previewspool.NewStreamWriter(attempt)
	if err != nil {
		_ = attempt.Cleanup()
		return previewspool.SealEvidence{}, err
	}

	evidence, err := s.runWorker(ctx, request, writer)
	if err != nil {
		_ = attempt.Cleanup()
		return previewspool.SealEvidence{}, err
	}
	return evidence, nil
}

func (s *Supervisor) verifyWorkerArtifact() error {
	fd, err := syscall.Open(s.config.WorkerPath, syscall.O_RDONLY|syscall.O_CLOEXEC|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return fmt.Errorf("%w: open worker: %v", ErrWorkerArtifactMismatch, err)
	}
	file := os.NewFile(uintptr(fd), s.config.WorkerPath)
	defer file.Close()
	info, err := file.Stat()
	if err != nil || !info.Mode().IsRegular() {
		return fmt.Errorf("%w: worker is not a regular file", ErrWorkerArtifactMismatch)
	}
	hasher := sha256.New()
	if _, err := io.Copy(hasher, file); err != nil {
		return fmt.Errorf("%w: hash worker: %v", ErrWorkerArtifactMismatch, err)
	}
	if hex.EncodeToString(hasher.Sum(nil)) != s.config.WorkerSHA256 {
		return ErrWorkerArtifactMismatch
	}
	return nil
}

func (s *Supervisor) runWorker(ctx context.Context, request ParseRequest, writer *previewspool.StreamWriter) (previewspool.SealEvidence, error) {
	outputRead, outputWrite, err := os.Pipe()
	if err != nil {
		return previewspool.SealEvidence{}, fmt.Errorf("create worker output pipe: %w", err)
	}
	defer outputRead.Close()

	var stderr bytes.Buffer
	command := exec.Command(s.config.WorkerPath, s.config.WorkerArgs...)
	command.Stdin = request.Source
	command.Stdout = outputWrite
	command.Stderr = &limitedWriter{limit: 4096, buffer: &stderr}
	command.Env = append([]string{}, s.config.WorkerEnv...)
	command.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}

	if err := command.Start(); err != nil {
		_ = outputWrite.Close()
		return previewspool.SealEvidence{}, fmt.Errorf("start parser worker: %w", err)
	}
	_ = outputWrite.Close()
	pid := command.Process.Pid
	reaped := false
	reap := func() {
		if !reaped {
			_ = syscall.Kill(-pid, syscall.SIGKILL)
			_ = command.Wait()
			reaped = true
		}
	}
	defer reap()

	if err := applyWorkerLimits(pid, s.config.Limits); err != nil {
		return previewspool.SealEvidence{}, fmt.Errorf("apply parser worker limits: %w", err)
	}

	deadline := time.Now().Add(s.config.Limits.WallClock)
	if err := outputRead.SetReadDeadline(deadline); err != nil {
		return previewspool.SealEvidence{}, fmt.Errorf("bind parser wall clock: %w", err)
	}
	stopCancellationWatch := make(chan struct{})
	go func() {
		select {
		case <-ctx.Done():
			_ = outputRead.SetReadDeadline(time.Now())
		case <-stopCancellationWatch:
		}
	}()
	defer close(stopCancellationWatch)

	var outputBytes int64
	payload := make([]byte, 0, 64*1024)
	for {
		if err := ctx.Err(); err != nil {
			return previewspool.SealEvidence{}, err
		}
		tag, record, err := readFrame(outputRead, payload)
		if ctxErr := ctx.Err(); ctxErr != nil {
			return previewspool.SealEvidence{}, ctxErr
		}
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			if errors.Is(err, os.ErrDeadlineExceeded) {
				return previewspool.SealEvidence{}, ErrParseTimeout
			}
			return previewspool.SealEvidence{}, err
		}
		outputBytes += int64(frameHeaderBytes + len(record))
		if outputBytes > s.config.Limits.OutputBytes {
			return previewspool.SealEvidence{}, ErrWorkerOutputLimit
		}
		if tag == frameTagAccepted {
			err = writer.WriteAccepted(ctx, record)
		} else {
			err = writer.WriteRejected(ctx, record)
		}
		if err != nil {
			return previewspool.SealEvidence{}, err
		}
	}

	waitErr := command.Wait()
	reaped = true
	if waitErr != nil {
		return previewspool.SealEvidence{}, fmt.Errorf("%w: %v: %s", ErrWorkerFailed, waitErr, strings.TrimSpace(stderr.String()))
	}

	sealer, err := previewspool.NewSealer(writer)
	if err != nil {
		return previewspool.SealEvidence{}, err
	}
	return sealer.Seal(ctx, request.Seal)
}

func applyWorkerLimits(pid int, limits Limits) error {
	entries := []struct {
		resource int
		value    uint64
	}{
		{syscall.RLIMIT_AS, limits.AddressSpaceBytes},
		{syscall.RLIMIT_CPU, limits.CPUSeconds},
		{syscall.RLIMIT_NOFILE, limits.OpenFiles},
		{syscall.RLIMIT_FSIZE, 0},
		{syscall.RLIMIT_CORE, 0},
	}
	for _, entry := range entries {
		limit := syscall.Rlimit{Cur: entry.value, Max: entry.value}
		if err := prlimit(pid, entry.resource, &limit); err != nil {
			return fmt.Errorf("resource %d: %w", entry.resource, err)
		}
	}
	return nil
}

func prlimit(pid int, resource int, limit *syscall.Rlimit) error {
	_, _, errno := syscall.RawSyscall6(
		syscall.SYS_PRLIMIT64,
		uintptr(pid),
		uintptr(resource),
		uintptr(unsafe.Pointer(limit)),
		0, 0, 0,
	)
	if errno != 0 {
		return errno
	}
	return nil
}

type limitedWriter struct {
	limit  int
	buffer *bytes.Buffer
}

func (w *limitedWriter) Write(value []byte) (int, error) {
	remaining := w.limit - w.buffer.Len()
	if remaining > 0 {
		if len(value) > remaining {
			w.buffer.Write(value[:remaining])
		} else {
			w.buffer.Write(value)
		}
	}
	return len(value), nil
}
