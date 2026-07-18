//go:build linux

package previewspool

import (
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"sort"
	"syscall"
	"time"
)

// Reconciler classifies and repairs crash residue in one supervisor root. It
// must run once at startup, before any attempt is created on the root: it
// holds the manager lock for the whole pass and treats every unsealed attempt
// as abandoned. It removes only the fixed attempt entry names, never recurses
// into unknown entries and never deletes a sealed unexpired attempt.
type Reconciler struct {
	manager    *Manager
	afterEntry func(string)
}

func NewReconciler(manager *Manager) (*Reconciler, error) {
	if manager == nil {
		return nil, ErrInvalidRoot
	}
	return &Reconciler{manager: manager}, nil
}

// Reconcile walks the root in deterministic name order. Crash residue is
// repaired (a completed publication keeps its manifest; everything else
// unsealed is removed), sealed attempts past their TTL are removed, and
// anything that cannot be classified is quarantined in place. A cancelled or
// failed pass is safe to re-run.
func (r *Reconciler) Reconcile(ctx context.Context, now time.Time) (ReconcileReport, error) {
	if r == nil || r.manager == nil {
		return ReconcileReport{}, ErrInvalidRoot
	}
	if ctx == nil || now.IsZero() {
		return ReconcileReport{}, ErrReconcileInvalidInput
	}
	if err := ctx.Err(); err != nil {
		return ReconcileReport{}, err
	}

	m := r.manager
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.closed {
		return ReconcileReport{}, ErrManagerClosed
	}
	if err := m.verifyRootDescriptor(); err != nil {
		return ReconcileReport{}, err
	}

	names, err := listRootNames(m)
	if err != nil {
		return ReconcileReport{}, err
	}
	sort.Strings(names)

	report := ReconcileReport{}
	mutated := false
	for _, name := range names {
		if err := ctx.Err(); err != nil {
			return report, err
		}
		entry, changed, err := r.reconcileEntry(name, now)
		if err != nil {
			return report, err
		}
		report.Entries = append(report.Entries, entry)
		mutated = mutated || changed
		if r.afterEntry != nil {
			r.afterEntry(name)
		}
	}
	if mutated {
		if err := syscall.Fsync(m.rootFD); err != nil {
			return report, fmt.Errorf("fsync Preview spool root after reconciliation: %w", err)
		}
	}
	return report, nil
}

func listRootNames(m *Manager) ([]string, error) {
	fd, err := syscall.Openat(m.rootFD, ".", syscall.O_RDONLY|syscall.O_DIRECTORY|syscall.O_CLOEXEC, 0)
	if err != nil {
		return nil, fmt.Errorf("%w: reopen root for reconciliation: %v", ErrUnsafeRoot, err)
	}
	var stat syscall.Stat_t
	if err := syscall.Fstat(fd, &stat); err != nil {
		_ = syscall.Close(fd)
		return nil, fmt.Errorf("%w: fstat root for reconciliation: %v", ErrUnsafeRoot, err)
	}
	if uint64(stat.Dev) != m.rootDev || stat.Ino != m.rootIno {
		_ = syscall.Close(fd)
		return nil, ErrUnsafeRoot
	}
	file := os.NewFile(uintptr(fd), ".")
	if file == nil {
		_ = syscall.Close(fd)
		return nil, errors.New("wrap Preview spool root directory")
	}
	defer file.Close()
	names, err := file.Readdirnames(-1)
	if err != nil {
		return nil, fmt.Errorf("list Preview spool root for reconciliation: %w", err)
	}
	return names, nil
}

func (r *Reconciler) reconcileEntry(name string, now time.Time) (ReconcileEntry, bool, error) {
	quarantine := func(detail string) (ReconcileEntry, bool, error) {
		return ReconcileEntry{Name: name, Outcome: ReconcileQuarantined, Detail: detail}, false, nil
	}
	if !validSpoolID(name) {
		return quarantine("entry name is not a Preview spool attempt")
	}

	m := r.manager
	fd, err := syscall.Openat(m.rootFD, name, syscall.O_RDONLY|syscall.O_DIRECTORY|syscall.O_CLOEXEC|syscall.O_NOFOLLOW, 0)
	if err != nil {
		if errors.Is(err, syscall.ENOENT) {
			return quarantine("entry disappeared during reconciliation")
		}
		if errors.Is(err, syscall.ELOOP) || errors.Is(err, syscall.ENOTDIR) {
			return quarantine("entry is not a plain directory")
		}
		return ReconcileEntry{}, false, fmt.Errorf("open Preview spool attempt for reconciliation: %w", err)
	}
	directory := os.NewFile(uintptr(fd), name)
	if directory == nil {
		_ = syscall.Close(fd)
		return ReconcileEntry{}, false, errors.New("wrap Preview spool attempt directory")
	}
	defer directory.Close()

	var stat syscall.Stat_t
	if err := syscall.Fstat(fd, &stat); err != nil {
		return ReconcileEntry{}, false, fmt.Errorf("fstat Preview spool attempt for reconciliation: %w", err)
	}
	if err := verifyDirectoryStat(&stat); err != nil {
		return quarantine(fmt.Sprintf("unsafe attempt directory: %v", err))
	}

	entryNames, err := directory.Readdirnames(-1)
	if err != nil {
		return ReconcileEntry{}, false, fmt.Errorf("list Preview spool attempt for reconciliation: %w", err)
	}
	present := make(map[string]bool, 4)
	for _, entryName := range entryNames {
		switch entryName {
		case AcceptedFileName, RejectedFileName, ManifestFileName, ManifestTempFileName:
			present[entryName] = true
		default:
			return quarantine(fmt.Sprintf("unknown entry %s", entryName))
		}
	}

	completedPublication := false
	if present[ManifestTempFileName] {
		if !present[ManifestFileName] {
			return r.removeAttempt(directory, name, ReconcileUnsealedRemoved, "manifest temp residue without publication")
		}
		matched, detail := bothNamesShareOneInode(fd)
		if !matched {
			return quarantine(detail)
		}
		if err := syscall.Unlinkat(fd, ManifestTempFileName); err != nil {
			return ReconcileEntry{}, false, fmt.Errorf("remove Preview spool manifest temp residue: %w", err)
		}
		if err := syscall.Fsync(fd); err != nil {
			return ReconcileEntry{}, false, fmt.Errorf("fsync Preview spool attempt after temp removal: %w", err)
		}
		completedPublication = true
	}

	if !present[ManifestFileName] {
		return r.removeAttempt(directory, name, ReconcileUnsealedRemoved, "no published manifest")
	}

	manifestFile, manifestSize, err := openVerifyRegularFile(directory, ManifestFileName, ErrVerifyManifestMissing)
	if err != nil {
		if errors.Is(err, ErrVerifyManifestMissing) {
			return quarantine("manifest disappeared during reconciliation")
		}
		if errors.Is(err, ErrUnsafeEntry) {
			return quarantine(fmt.Sprintf("unsafe manifest entry: %v", err))
		}
		return ReconcileEntry{}, false, err
	}
	if manifestSize == 0 {
		_ = manifestFile.Close()
		entry, mutated, err := r.removeAttempt(directory, name, ReconcileUnsealedRemoved, "empty manifest placeholder")
		return entry, mutated || completedPublication, err
	}
	if manifestSize > MaxManifestBytes {
		_ = manifestFile.Close()
		return quarantine(fmt.Sprintf("manifest length %d exceeds bound", manifestSize))
	}
	payload := make([]byte, manifestSize)
	_, readErr := io.ReadFull(manifestFile, payload)
	closeErr := manifestFile.Close()
	if readErr != nil || closeErr != nil {
		return ReconcileEntry{}, completedPublication, fmt.Errorf("read Preview spool manifest for reconciliation: %w", errors.Join(readErr, closeErr))
	}
	doc, input, _, err := decodeSealedManifest(payload)
	if err != nil {
		return quarantine("manifest is not canonical")
	}
	if doc.SpoolID != name {
		return quarantine(fmt.Sprintf("manifest names foreign spool %s", doc.SpoolID))
	}

	if !now.Before(input.ExpiresAt) {
		entry, mutated, err := r.removeAttempt(directory, name, ReconcileExpiredRemoved, "sealed attempt past TTL")
		return entry, mutated || completedPublication, err
	}
	if completedPublication {
		return ReconcileEntry{Name: name, Outcome: ReconcilePublicationCompleted, Detail: "removed temp name of completed publication"}, true, nil
	}
	return ReconcileEntry{Name: name, Outcome: ReconcileSealedKept, Detail: "sealed and unexpired"}, false, nil
}

// bothNamesShareOneInode accepts only the exact crash window between linkat
// publication and temp unlink: both fixed names are regular 0600 files owned
// by the effective user, refer to one inode and carry exactly the two links.
func bothNamesShareOneInode(dirFD int) (bool, string) {
	stats := make([]syscall.Stat_t, 2)
	for i, name := range []string{ManifestFileName, ManifestTempFileName} {
		fd, err := syscall.Openat(dirFD, name, syscall.O_RDONLY|syscall.O_CLOEXEC|syscall.O_NOFOLLOW, 0)
		if err != nil {
			return false, fmt.Sprintf("conflicting manifest temp residue: open %s: %v", name, err)
		}
		err = syscall.Fstat(fd, &stats[i])
		_ = syscall.Close(fd)
		if err != nil {
			return false, fmt.Sprintf("conflicting manifest temp residue: fstat %s: %v", name, err)
		}
		stat := &stats[i]
		if stat.Mode&syscall.S_IFMT != syscall.S_IFREG || stat.Mode&0o777 != SpoolFileMode || int(stat.Uid) != os.Geteuid() || stat.Nlink != 2 {
			return false, fmt.Sprintf("conflicting manifest temp residue: %s is not the linked publication inode", name)
		}
	}
	if uint64(stats[0].Dev) != uint64(stats[1].Dev) || stats[0].Ino != stats[1].Ino {
		return false, "conflicting manifest temp residue: names refer to different inodes"
	}
	return true, ""
}

func (r *Reconciler) removeAttempt(directory *os.File, name string, outcome ReconcileOutcome, detail string) (ReconcileEntry, bool, error) {
	fd := int(directory.Fd())
	for _, entryName := range []string{AcceptedFileName, RejectedFileName, ManifestFileName, ManifestTempFileName} {
		if err := syscall.Unlinkat(fd, entryName); err != nil && !errors.Is(err, syscall.ENOENT) {
			return ReconcileEntry{}, true, fmt.Errorf("remove Preview spool file %s during reconciliation: %w", entryName, err)
		}
	}
	if err := removeDirectoryAt(r.manager.rootFD, name); err != nil {
		return ReconcileEntry{}, true, fmt.Errorf("remove Preview spool attempt %s during reconciliation: %w", name, err)
	}
	return ReconcileEntry{Name: name, Outcome: outcome, Detail: detail}, true, nil
}
