// Package reqid mints and validates request and correlation identifiers and
// carries them through context.
//
// An inbound request ID is never trusted as-is: a client-supplied value is only
// echoed when it fits a strict charset and length, and any other value is
// replaced with a freshly generated server ID. This keeps the identifier useful
// for correlation while denying a client the ability to inject log-shaping
// content, overlong values or another request's ID.
//
// Identifiers are non-secret, server-scoped and short-lived. An account ID, an
// Apple subject or any user value must never be used as a correlation ID — the
// generators here produce opaque random IDs precisely so nothing identifying is
// reused for correlation.
package reqid

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"regexp"
)

// MaxLen bounds an accepted inbound request ID. Long enough for a UUID or a
// short trace token, short enough that it can never carry a payload.
const MaxLen = 64

// acceptedInbound is intentionally narrow: URL-safe identifier characters only.
// It excludes whitespace, quotes, control characters and anything that could
// alter a JSON log line, so an echoed inbound ID cannot reshape output.
var acceptedInbound = regexp.MustCompile(`^[A-Za-z0-9._-]{1,64}$`)

type contextKey int

const (
	requestIDKey contextKey = iota
	correlationIDKey
)

// New generates a fresh opaque request ID. It is 128 bits of randomness, hex
// encoded, prefixed so it is recognizable in logs as server-minted.
func New() string {
	return "req_" + randomHex(16)
}

// NewCorrelation generates a correlation ID for a boundary that is not an HTTP
// request — a background deletion sweep, an import job — so worker events form
// their own correlation scope rather than borrowing a request's.
func NewCorrelation(prefix string) string {
	if !acceptedInbound.MatchString(prefix) || len(prefix) > 16 {
		prefix = "corr"
	}
	return prefix + "_" + randomHex(16)
}

// FromInbound returns a usable request ID for an inbound header value: the
// value itself when it is well-formed, otherwise a fresh server ID. The bool
// reports whether the inbound value was accepted, so a caller can record that a
// client's ID was replaced.
func FromInbound(headerValue string) (string, bool) {
	if acceptedInbound.MatchString(headerValue) {
		return headerValue, true
	}
	return New(), false
}

// WithRequestID stores the request ID in context.
func WithRequestID(ctx context.Context, id string) context.Context {
	return context.WithValue(ctx, requestIDKey, id)
}

// RequestID reads the request ID from context; empty when absent.
func RequestID(ctx context.Context) string {
	if value, ok := ctx.Value(requestIDKey).(string); ok {
		return value
	}
	return ""
}

// WithCorrelationID stores a correlation ID in context.
func WithCorrelationID(ctx context.Context, id string) context.Context {
	return context.WithValue(ctx, correlationIDKey, id)
}

// CorrelationID reads the correlation ID from context; empty when absent.
func CorrelationID(ctx context.Context) string {
	if value, ok := ctx.Value(correlationIDKey).(string); ok {
		return value
	}
	return ""
}

func randomHex(byteLen int) string {
	buffer := make([]byte, byteLen)
	if _, err := rand.Read(buffer); err != nil {
		// A failure of the CSPRNG is catastrophic elsewhere; here a fixed
		// non-secret marker keeps correlation total without inventing entropy.
		return "00000000000000000000000000000000"[:byteLen*2]
	}
	return hex.EncodeToString(buffer)
}
