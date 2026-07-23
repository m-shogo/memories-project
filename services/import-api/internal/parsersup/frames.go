package parsersup

import (
	"encoding/binary"
	"errors"
	"fmt"
	"io"

	"github.com/m-shogo/memories-project/services/import-api/internal/previewspool"
)

// The worker emits canonical records to the supervisor as synchronous frames:
//
//	1-byte stream tag ('A' accepted / 'R' rejected)
//	8-byte unsigned big-endian record length
//	exact canonical record bytes
//
// Anything else — unknown tags, zero or oversized lengths, torn frames or
// trailing bytes — is a terminal protocol violation. The worker never talks to
// the filesystem, database or network; the supervisor owns the spool.
const (
	frameTagAccepted byte = 'A'
	frameTagRejected byte = 'R'

	frameHeaderBytes = 9
)

var (
	ErrFrameProtocolViolation = errors.New("parser worker frame protocol violation")
	ErrWorkerOutputLimit      = errors.New("parser worker output limit exceeded")
)

// readFrame reads exactly one frame. io.EOF at a frame boundary means the
// worker finished; any partial header or body is a torn frame.
func readFrame(reader io.Reader, payload []byte) (byte, []byte, error) {
	var header [frameHeaderBytes]byte
	if _, err := io.ReadFull(reader, header[:1]); err != nil {
		if err == io.EOF {
			return 0, nil, io.EOF
		}
		return 0, nil, fmt.Errorf("%w: torn frame tag: %w", ErrFrameProtocolViolation, err)
	}
	tag := header[0]
	if tag != frameTagAccepted && tag != frameTagRejected {
		return 0, nil, fmt.Errorf("%w: unknown tag 0x%02x", ErrFrameProtocolViolation, tag)
	}
	if _, err := io.ReadFull(reader, header[1:]); err != nil {
		return 0, nil, fmt.Errorf("%w: torn frame length: %w", ErrFrameProtocolViolation, err)
	}
	length := binary.BigEndian.Uint64(header[1:])
	if length < 1 || length > uint64(previewspool.MaxCanonicalRecordBytes) {
		return 0, nil, fmt.Errorf("%w: record length %d", ErrFrameProtocolViolation, length)
	}
	if uint64(cap(payload)) < length {
		payload = make([]byte, length)
	}
	payload = payload[:length]
	if _, err := io.ReadFull(reader, payload); err != nil {
		return 0, nil, fmt.Errorf("%w: torn frame body: %w", ErrFrameProtocolViolation, err)
	}
	return tag, payload, nil
}

// WriteAcceptedFrame serializes one accepted canonical record for the worker
// side of the protocol. Real adapter workers (internal/csvworker) and the test
// harness share this encoder so the framing cannot drift.
func WriteAcceptedFrame(writer io.Writer, payload []byte) error {
	return writeFrame(writer, frameTagAccepted, payload)
}

// WriteRejectedFrame serializes one rejected canonical record for the worker
// side of the protocol.
func WriteRejectedFrame(writer io.Writer, payload []byte) error {
	return writeFrame(writer, frameTagRejected, payload)
}

// writeFrame is used by the worker side of the protocol.
func writeFrame(writer io.Writer, tag byte, payload []byte) error {
	var header [frameHeaderBytes]byte
	header[0] = tag
	binary.BigEndian.PutUint64(header[1:], uint64(len(payload)))
	if _, err := writer.Write(header[:]); err != nil {
		return err
	}
	_, err := writer.Write(payload)
	return err
}
