//go:build !linux

package parsersup

import (
	"context"
	"os"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/previewspool"
)

type Limits struct {
	AddressSpaceBytes uint64
	CPUSeconds        uint64
	OpenFiles         uint64
	OutputBytes       int64
	WallClock         time.Duration
}

type Config struct {
	WorkerPath   string
	WorkerSHA256 string
	WorkerArgs   []string
	WorkerEnv    []string
	Limits       Limits
}

type ParseRequest struct {
	Manager *previewspool.Manager
	SpoolID string
	Source  *os.File
	Seal    previewspool.SealInput
}

type Supervisor struct{}

func NewSupervisor(Config) (*Supervisor, error) {
	return nil, previewspool.ErrUnsupportedPlatform
}

func (*Supervisor) Parse(context.Context, ParseRequest) (previewspool.SealEvidence, error) {
	return previewspool.SealEvidence{}, previewspool.ErrUnsupportedPlatform
}
