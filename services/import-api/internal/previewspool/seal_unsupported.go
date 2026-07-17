//go:build !linux

package previewspool

import "context"

type Sealer struct{}

func NewSealer(*StreamWriter) (*Sealer, error) {
	return nil, ErrUnsupportedPlatform
}

func (*Sealer) Seal(context.Context, SealInput) (SealEvidence, error) {
	return SealEvidence{}, ErrUnsupportedPlatform
}
