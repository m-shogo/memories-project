//go:build !linux

package previewspool

import (
	"context"
	"time"
)

type Verifier struct{}

func NewVerifier(*Manager) (*Verifier, error) {
	return nil, ErrUnsupportedPlatform
}

func (*Verifier) Verify(context.Context, string, VerifyExpectation, time.Time) (VerifiedSpool, error) {
	return VerifiedSpool{}, ErrUnsupportedPlatform
}
