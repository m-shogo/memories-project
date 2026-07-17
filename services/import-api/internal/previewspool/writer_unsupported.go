//go:build !linux

package previewspool

import "context"

type StreamWriter struct{}

func NewStreamWriter(*Attempt) (*StreamWriter, error) {
	return nil, ErrUnsupportedPlatform
}

func (*StreamWriter) WriteAccepted(context.Context, []byte) error {
	return ErrUnsupportedPlatform
}

func (*StreamWriter) WriteRejected(context.Context, []byte) error {
	return ErrUnsupportedPlatform
}

func (*StreamWriter) Close(context.Context) (WriteEvidence, error) {
	return WriteEvidence{}, ErrUnsupportedPlatform
}
