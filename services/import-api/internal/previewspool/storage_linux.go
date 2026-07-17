//go:build linux

package previewspool

import (
	"context"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sync"
	"syscall"
	"unsafe"
)

const atRemovedir = 0x200

const (
	stageDirectoryCreated = "directory-created"
	stageDirectoryOpened  = "directory-opened"
	stageAcceptedCreated  = "accepted-created"
	stageRejectedCreated  = "rejected-created"
	stageManifestCreated  = "manifest-created"
)

type Manager struct {
	rootFD    int
	rootDev   uint64
	rootIno   uint64
	mu        sync.Mutex
	closed    bool
	afterStep func(string)
}

type Attempt struct {
	manager  *Manager
	id       string
	dirDev   uint64
	dirIno   uint64
	accepted *os.File
	rejected *os.File
	manifest *os.File
	mu       sync.Mutex
	cleaned  bool
}

// OpenManager opens a supervisor-provisioned private root. The path must be
// absolute, canonical, owned by the effective user, and mode 0700 exactly.
func OpenManager(rootPath string) (*Manager, error) {
	if !filepath.IsAbs(rootPath) || filepath.Clean(rootPath) != rootPath {
		return nil, ErrInvalidRoot
	}
	info, err := os.Lstat(rootPath)
	if err != nil {
		return nil, fmt.Errorf("%w: lstat root: %v", ErrInvalidRoot, err)
	}
	if info.Mode()&os.ModeSymlink != 0 || !info.IsDir() || info.Mode().Perm() != AttemptDirMode {
		return nil, ErrUnsafeRoot
	}

	fd, err := syscall.Open(rootPath, syscall.O_RDONLY|syscall.O_DIRECTORY|syscall.O_CLOEXEC|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return nil, fmt.Errorf("%w: open root: %v", ErrUnsafeRoot, err)
	}
	var stat syscall.Stat_t
	if err := syscall.Fstat(fd, &stat); err != nil {
		_ = syscall.Close(fd)
		return nil, fmt.Errorf("%w: fstat root: %v", ErrUnsafeRoot, err)
	}
	if err := verifyDirectoryStat(&stat); err != nil {
		_ = syscall.Close(fd)
		return nil, fmt.Errorf("%w: %v", ErrUnsafeRoot, err)
	}
	return &Manager{rootFD: fd, rootDev: uint64(stat.Dev), rootIno: stat.Ino}, nil
}

func (m *Manager) Close() error {
	if m == nil {
		return nil
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.closed {
		return nil
	}
	m.closed = true
	return syscall.Close(m.rootFD)
}

// CreateAttempt creates one new, non-reusable attempt directory and its three
// fixed files. It owns no goroutines and removes every partial entry on error or
// cancellation.
func (m *Manager) CreateAttempt(ctx context.Context, spoolID string) (_ *Attempt, resultErr error) {
	if m == nil {
		return nil, ErrInvalidRoot
	}
	if ctx == nil {
		return nil, errors.New("Preview spool attempt requires context")
	}
	if !validSpoolID(spoolID) {
		return nil, ErrInvalidSpoolID
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}

	m.mu.Lock()
	defer m.mu.Unlock()
	if m.closed {
		return nil, ErrManagerClosed
	}
	if err := m.verifyRootDescriptor(); err != nil {
		return nil, err
	}

	if err := syscall.Mkdirat(m.rootFD, spoolID, AttemptDirMode); err != nil {
		if errors.Is(err, syscall.EEXIST) {
			return nil, ErrAttemptExists
		}
		return nil, fmt.Errorf("create Preview spool attempt: %w", err)
	}

	attemptFD := -1
	files := make([]*os.File, 0, 3)
	var attemptStat syscall.Stat_t
	cleanup := true
	defer func() {
		if !cleanup {
			return
		}
		cleanupErr := cleanupPartialAttempt(m.rootFD, spoolID, attemptFD, files)
		if cleanupErr == nil {
			return
		}
		if resultErr == nil {
			resultErr = cleanupErr
		} else {
			resultErr = errors.Join(resultErr, cleanupErr)
		}
	}()

	if err := m.after(stageDirectoryCreated, ctx); err != nil {
		return nil, err
	}

	var err error
	attemptFD, err = syscall.Openat(m.rootFD, spoolID, syscall.O_RDONLY|syscall.O_DIRECTORY|syscall.O_CLOEXEC|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return nil, fmt.Errorf("open Preview spool attempt: %w", err)
	}
	if err := syscall.Fchmod(attemptFD, AttemptDirMode); err != nil {
		return nil, fmt.Errorf("chmod Preview spool attempt: %w", err)
	}
	if err := syscall.Fstat(attemptFD, &attemptStat); err != nil {
		return nil, fmt.Errorf("fstat Preview spool attempt: %w", err)
	}
	if err := verifyDirectoryStat(&attemptStat); err != nil {
		return nil, fmt.Errorf("%w: %v", ErrUnsafeEntry, err)
	}
	if err := m.after(stageDirectoryOpened, ctx); err != nil {
		return nil, err
	}

	accepted, err := createExclusiveFile(attemptFD, AcceptedFileName)
	if err != nil {
		return nil, err
	}
	files = append(files, accepted)
	if err := m.after(stageAcceptedCreated, ctx); err != nil {
		return nil, err
	}

	rejected, err := createExclusiveFile(attemptFD, RejectedFileName)
	if err != nil {
		return nil, err
	}
	files = append(files, rejected)
	if err := m.after(stageRejectedCreated, ctx); err != nil {
		return nil, err
	}

	manifest, err := createExclusiveFile(attemptFD, ManifestFileName)
	if err != nil {
		return nil, err
	}
	files = append(files, manifest)
	if err := m.after(stageManifestCreated, ctx); err != nil {
		return nil, err
	}

	if err := syscall.Close(attemptFD); err != nil {
		return nil, fmt.Errorf("close Preview spool attempt directory: %w", err)
	}
	attemptFD = -1
	cleanup = false

	return &Attempt{
		manager:  m,
		id:       spoolID,
		dirDev:   uint64(attemptStat.Dev),
		dirIno:   attemptStat.Ino,
		accepted: accepted,
		rejected: rejected,
		manifest: manifest,
	}, nil
}

func (m *Manager) after(stage string, ctx context.Context) error {
	if m.afterStep != nil {
		m.afterStep(stage)
	}
	return ctx.Err()
}

func (m *Manager) verifyRootDescriptor() error {
	var stat syscall.Stat_t
	if err := syscall.Fstat(m.rootFD, &stat); err != nil {
		return fmt.Errorf("%w: fstat root: %v", ErrUnsafeRoot, err)
	}
	if uint64(stat.Dev) != m.rootDev || stat.Ino != m.rootIno {
		return ErrUnsafeRoot
	}
	if err := verifyDirectoryStat(&stat); err != nil {
		return fmt.Errorf("%w: %v", ErrUnsafeRoot, err)
	}
	return nil
}

func (a *Attempt) ID() string {
	if a == nil {
		return ""
	}
	return a.id
}

func (a *Attempt) AcceptedFile() *os.File {
	if a == nil {
		return nil
	}
	return a.accepted
}

func (a *Attempt) RejectedFile() *os.File {
	if a == nil {
		return nil
	}
	return a.rejected
}

func (a *Attempt) ManifestFile() *os.File {
	if a == nil {
		return nil
	}
	return a.manifest
}

func (a *Attempt) CloseFiles() error {
	if a == nil {
		return nil
	}
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.closeFilesLocked()
}

// Cleanup removes only the exact attempt inode originally created by this
// object. Unknown entries or replacement directories fail closed.
func (a *Attempt) Cleanup() error {
	if a == nil {
		return nil
	}
	a.mu.Lock()
	defer a.mu.Unlock()
	if a.cleaned {
		return nil
	}
	if a.manager == nil {
		return ErrInvalidRoot
	}
	closeErr := a.closeFilesLocked()

	m := a.manager
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.closed {
		return errors.Join(closeErr, ErrManagerClosed)
	}
	if err := m.verifyRootDescriptor(); err != nil {
		return errors.Join(closeErr, err)
	}

	currentFD, err := syscall.Openat(m.rootFD, a.id, syscall.O_RDONLY|syscall.O_DIRECTORY|syscall.O_CLOEXEC|syscall.O_NOFOLLOW, 0)
	if err != nil {
		if errors.Is(err, syscall.ENOENT) {
			return errors.Join(closeErr, ErrAttemptMissing)
		}
		return errors.Join(closeErr, fmt.Errorf("open Preview spool attempt for cleanup: %w", err))
	}
	currentFile := os.NewFile(uintptr(currentFD), a.id)
	if currentFile == nil {
		_ = syscall.Close(currentFD)
		return errors.Join(closeErr, errors.New("wrap Preview spool attempt directory"))
	}
	defer currentFile.Close()

	var stat syscall.Stat_t
	if err := syscall.Fstat(currentFD, &stat); err != nil {
		return errors.Join(closeErr, fmt.Errorf("fstat Preview spool cleanup directory: %w", err))
	}
	if uint64(stat.Dev) != a.dirDev || stat.Ino != a.dirIno {
		return errors.Join(closeErr, ErrAttemptSubstituted)
	}
	if err := verifyDirectoryStat(&stat); err != nil {
		return errors.Join(closeErr, fmt.Errorf("%w: %v", ErrUnsafeEntry, err))
	}

	names, err := currentFile.Readdirnames(-1)
	if err != nil {
		return errors.Join(closeErr, fmt.Errorf("list Preview spool attempt: %w", err))
	}
	allowed := map[string]struct{}{
		AcceptedFileName: {},
		RejectedFileName: {},
		ManifestFileName: {},
	}
	for _, name := range names {
		if _, ok := allowed[name]; !ok {
			return errors.Join(closeErr, fmt.Errorf("%w: %s", ErrUnexpectedEntry, name))
		}
	}
	for _, name := range []string{AcceptedFileName, RejectedFileName, ManifestFileName} {
		if err := syscall.Unlinkat(currentFD, name); err != nil && !errors.Is(err, syscall.ENOENT) {
			return errors.Join(closeErr, fmt.Errorf("remove Preview spool file %s: %w", name, err))
		}
	}
	if err := currentFile.Close(); err != nil {
		return errors.Join(closeErr, fmt.Errorf("close Preview spool cleanup directory: %w", err))
	}
	if err := removeDirectoryAt(m.rootFD, a.id); err != nil {
		return errors.Join(closeErr, fmt.Errorf("remove Preview spool attempt directory: %w", err))
	}
	a.cleaned = true
	return closeErr
}

func (a *Attempt) closeFilesLocked() error {
	var errs []error
	for _, target := range []**os.File{&a.accepted, &a.rejected, &a.manifest} {
		if *target == nil {
			continue
		}
		if err := (*target).Close(); err != nil && !errors.Is(err, fs.ErrClosed) {
			errs = append(errs, err)
		}
		*target = nil
	}
	return errors.Join(errs...)
}

func createExclusiveFile(dirFD int, name string) (*os.File, error) {
	fd, err := syscall.Openat(dirFD, name, syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL|syscall.O_CLOEXEC|syscall.O_NOFOLLOW, SpoolFileMode)
	if err != nil {
		if errors.Is(err, syscall.EEXIST) {
			return nil, fmt.Errorf("%w: %s", ErrAttemptExists, name)
		}
		return nil, fmt.Errorf("create Preview spool file %s: %w", name, err)
	}
	if err := syscall.Fchmod(fd, SpoolFileMode); err != nil {
		_ = syscall.Close(fd)
		return nil, fmt.Errorf("chmod Preview spool file %s: %w", name, err)
	}
	var stat syscall.Stat_t
	if err := syscall.Fstat(fd, &stat); err != nil {
		_ = syscall.Close(fd)
		return nil, fmt.Errorf("fstat Preview spool file %s: %w", name, err)
	}
	if err := verifyRegularFileStat(&stat); err != nil {
		_ = syscall.Close(fd)
		return nil, fmt.Errorf("%w: %s: %v", ErrUnsafeEntry, name, err)
	}
	file := os.NewFile(uintptr(fd), name)
	if file == nil {
		_ = syscall.Close(fd)
		return nil, fmt.Errorf("wrap Preview spool file %s", name)
	}
	return file, nil
}

func verifyDirectoryStat(stat *syscall.Stat_t) error {
	if stat.Mode&syscall.S_IFMT != syscall.S_IFDIR {
		return errors.New("entry is not a directory")
	}
	if stat.Mode&0o777 != AttemptDirMode {
		return fmt.Errorf("directory mode is %04o", stat.Mode&0o777)
	}
	if int(stat.Uid) != os.Geteuid() {
		return errors.New("directory owner does not match effective user")
	}
	return nil
}

func verifyRegularFileStat(stat *syscall.Stat_t) error {
	if stat.Mode&syscall.S_IFMT != syscall.S_IFREG {
		return errors.New("entry is not a regular file")
	}
	if stat.Mode&0o777 != SpoolFileMode {
		return fmt.Errorf("file mode is %04o", stat.Mode&0o777)
	}
	if int(stat.Uid) != os.Geteuid() {
		return errors.New("file owner does not match effective user")
	}
	if stat.Nlink != 1 {
		return fmt.Errorf("file link count is %d", stat.Nlink)
	}
	return nil
}

func cleanupPartialAttempt(rootFD int, spoolID string, attemptFD int, files []*os.File) error {
	var errs []error
	for _, file := range files {
		if file != nil {
			if err := file.Close(); err != nil && !errors.Is(err, fs.ErrClosed) {
				errs = append(errs, err)
			}
		}
	}
	if attemptFD >= 0 {
		for _, name := range []string{AcceptedFileName, RejectedFileName, ManifestFileName} {
			if err := syscall.Unlinkat(attemptFD, name); err != nil && !errors.Is(err, syscall.ENOENT) {
				errs = append(errs, err)
			}
		}
		if err := syscall.Close(attemptFD); err != nil {
			errs = append(errs, err)
		}
	}
	if err := removeDirectoryAt(rootFD, spoolID); err != nil && !errors.Is(err, syscall.ENOENT) {
		errs = append(errs, err)
	}
	return errors.Join(errs...)
}

func removeDirectoryAt(dirFD int, name string) error {
	pointer, err := syscall.BytePtrFromString(name)
	if err != nil {
		return err
	}
	_, _, errno := syscall.Syscall6(
		syscall.SYS_UNLINKAT,
		uintptr(dirFD),
		uintptr(unsafe.Pointer(pointer)),
		uintptr(atRemovedir),
		0,
		0,
		0,
	)
	if errno != 0 {
		return errno
	}
	return nil
}
