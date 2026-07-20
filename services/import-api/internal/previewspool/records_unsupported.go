//go:build !linux

package previewspool

import "context"

func CollectSealedRecords(context.Context, *Manager, VerifiedSpool) ([][]byte, [][]byte, error) {
	return nil, nil, ErrUnsupportedPlatform
}
