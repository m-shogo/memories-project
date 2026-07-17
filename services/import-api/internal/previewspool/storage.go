package previewspool

import (
	"errors"
	"regexp"
)

const (
	AttemptDirMode = 0o700
	SpoolFileMode  = 0o600

	AcceptedFileName     = "accepted.spool"
	RejectedFileName     = "rejected.spool"
	ManifestFileName     = "manifest.json"
	ManifestTempFileName = "manifest.tmp"
)

var (
	ErrUnsupportedPlatform = errors.New("Preview spool filesystem is unsupported on this platform")
	ErrInvalidRoot         = errors.New("invalid Preview spool root")
	ErrUnsafeRoot          = errors.New("unsafe Preview spool root")
	ErrInvalidSpoolID      = errors.New("invalid Preview spool ID")
	ErrAttemptExists       = errors.New("Preview spool attempt already exists")
	ErrAttemptMissing      = errors.New("Preview spool attempt is missing")
	ErrAttemptSubstituted  = errors.New("Preview spool attempt was substituted")
	ErrUnsafeEntry         = errors.New("unsafe Preview spool filesystem entry")
	ErrUnexpectedEntry     = errors.New("unexpected Preview spool filesystem entry")
	ErrManagerClosed       = errors.New("Preview spool manager is closed")
)

var spoolIDPattern = regexp.MustCompile(`^spl_[A-Za-z0-9_-]{12,120}$`)

func validSpoolID(value string) bool {
	return spoolIDPattern.MatchString(value)
}
