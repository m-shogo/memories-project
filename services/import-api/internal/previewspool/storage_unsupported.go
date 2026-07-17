//go:build !linux

package previewspool

import (
	"context"
	"os"
)

type Manager struct{}
type Attempt struct{}

func OpenManager(string) (*Manager, error) {
	return nil, ErrUnsupportedPlatform
}

func (*Manager) Close() error {
	return nil
}

func (*Manager) CreateAttempt(context.Context, string) (*Attempt, error) {
	return nil, ErrUnsupportedPlatform
}

func (*Attempt) ID() string {
	return ""
}

func (*Attempt) AcceptedFile() *os.File {
	return nil
}

func (*Attempt) RejectedFile() *os.File {
	return nil
}

func (*Attempt) ManifestFile() *os.File {
	return nil
}

func (*Attempt) CloseFiles() error {
	return nil
}

func (*Attempt) Cleanup() error {
	return nil
}
