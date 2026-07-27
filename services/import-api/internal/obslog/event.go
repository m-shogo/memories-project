// Package obslog is the structured, privacy-first observability event logger.
//
// Its central design choice is that redaction is structural, not a runtime
// filter: there is no free-form message field, no field that accepts an error
// value, and no map[string]any escape hatch. An event can only be built from a
// fixed set of typed, length-bounded, server-controlled fields, so there is
// physically nowhere to put a bearer token, an Apple credential, raw user
// content, a SQL parameter or an unbounded error string. The canary tests prove
// this holds; the type system is what makes it true in the first place.
//
// Severity, eventCode, component, operation, outcome and failureClass are all
// closed enumerations declared in this package. eventName and route templates
// are stable, low-cardinality identifiers chosen by the caller from a fixed set,
// never derived from user input, so they cannot inflate log cardinality or
// smuggle content through a field key.
package obslog

import (
	"encoding/json"
	"io"
	"sync"
	"time"
)

// SchemaVersion identifies the event contract this logger emits. It is mirrored
// in contracts/operations/observability-event-contract.v1.json and asserted
// equal by the validator, so the code and the machine-readable contract cannot
// drift.
const SchemaVersion = "memory-os-observability-event.v1"

// Field length bounds. Every string that reaches the output is truncated to
// these, so a single event can never emit an unbounded payload even if a caller
// passes an over-long stable identifier by mistake.
const (
	maxIdentifierLen = 128
	maxShortLen      = 64
)

// Severity is the closed set of log levels.
type Severity string

const (
	SeverityDebug Severity = "debug"
	SeverityInfo  Severity = "info"
	SeverityWarn  Severity = "warn"
	SeverityError Severity = "error"
)

func (s Severity) valid() bool {
	switch s {
	case SeverityDebug, SeverityInfo, SeverityWarn, SeverityError:
		return true
	}
	return false
}

// Outcome is the result class of an operation.
type Outcome string

const (
	OutcomeSuccess  Outcome = "success"
	OutcomeFailure  Outcome = "failure"
	OutcomeRejected Outcome = "rejected"
)

func (o Outcome) valid() bool {
	switch o {
	case OutcomeSuccess, OutcomeFailure, OutcomeRejected:
		return true
	}
	return false
}

// FailureClass is the stable, non-secret classification of a failure. It never
// carries a raw error string — a class is all an operator needs to route and
// triage, and it can never contain user content.
type FailureClass string

const (
	FailureNone                FailureClass = ""
	FailureAuthentication      FailureClass = "authentication_failure"
	FailureAuthorization       FailureClass = "authorization_denied"
	FailureInvalidRequest      FailureClass = "invalid_request"
	FailureReplayRejected      FailureClass = "replay_rejected"
	FailureExternalApple       FailureClass = "external_apple_failure"
	FailureDatabaseUnavailable FailureClass = "database_unavailable"
	FailureObjectStore         FailureClass = "object_store_unavailable"
	FailureParser              FailureClass = "parser_failure"
	FailureIntegrity           FailureClass = "integrity_failure"
	FailureRateLimited         FailureClass = "rate_limited"
	FailureDeletionRetry       FailureClass = "deletion_retry"
	FailureDeletionTerminal    FailureClass = "deletion_terminal_failure"
	FailureInternalInvariant   FailureClass = "internal_invariant_violation"
	FailurePanic               FailureClass = "panic_recovered"
)

var failureClasses = map[FailureClass]struct{}{
	FailureAuthentication: {}, FailureAuthorization: {}, FailureInvalidRequest: {},
	FailureReplayRejected: {}, FailureExternalApple: {}, FailureDatabaseUnavailable: {},
	FailureObjectStore: {}, FailureParser: {}, FailureIntegrity: {}, FailureRateLimited: {},
	FailureDeletionRetry: {}, FailureDeletionTerminal: {}, FailureInternalInvariant: {},
	FailurePanic: {},
}

func (f FailureClass) valid() bool {
	if f == FailureNone {
		return true
	}
	_, ok := failureClasses[f]
	return ok
}

// Component is the closed set of subsystems that emit events.
type Component string

const (
	ComponentHTTP           Component = "http"
	ComponentApple          Component = "apple_auth"
	ComponentUpload         Component = "upload"
	ComponentPreview        Component = "preview"
	ComponentApply          Component = "apply"
	ComponentDeletionWorker Component = "deletion_worker"
	ComponentImportFlow     Component = "import_flow"
	ComponentServer         Component = "server"
)

// Event is the sole shape the logger emits. Required fields (SchemaVersion,
// Timestamp, Severity, EventName, EventCode, Component, Outcome) are always
// present; every other field is a pointer or empty-omitted, so an unused field
// never appears as an empty string or zero. There is deliberately no message,
// error, detail or attributes field.
type Event struct {
	SchemaVersion string    `json:"schemaVersion"`
	Timestamp     string    `json:"timestamp"`
	Severity      Severity  `json:"severity"`
	EventName     string    `json:"eventName"`
	EventCode     EventCode `json:"eventCode"`
	Component     Component `json:"component"`
	Operation     string    `json:"operation,omitempty"`
	Outcome       Outcome   `json:"outcome"`

	RequestID     string `json:"requestId,omitempty"`
	CorrelationID string `json:"correlationId,omitempty"`
	JobID         string `json:"jobId,omitempty"`
	AttemptID     string `json:"attemptId,omitempty"`
	ActorType     string `json:"actorType,omitempty"`

	HTTPMethod string `json:"httpMethod,omitempty"`
	Route      string `json:"route,omitempty"`
	StatusCode *int   `json:"statusCode,omitempty"`
	DurationMs *int64 `json:"durationMs,omitempty"`

	Retryable    *bool        `json:"retryable,omitempty"`
	FailureClass FailureClass `json:"failureClass,omitempty"`

	// Count is a single bounded numeric — used for backlog counts, removed-row
	// counts and similar. It is never a user-controlled cardinality.
	Count *int64 `json:"count,omitempty"`
}

// Logger writes one JSON event per line to an io.Writer. It is safe for
// concurrent use: a mutex serializes writes so lines never interleave.
type Logger struct {
	mu  sync.Mutex
	out io.Writer
	now func() time.Time
}

// New returns a Logger writing to out. A nil writer means the logger discards,
// which keeps callers total: observability never fails the request path.
func New(out io.Writer) *Logger {
	return &Logger{out: out, now: time.Now}
}

// withClock is used by tests for deterministic timestamps.
func (l *Logger) withClock(now func() time.Time) *Logger {
	l.now = now
	return l
}

// Emit finalizes and writes an event. The caller supplies the semantic fields;
// Emit fills SchemaVersion and Timestamp, bounds every string, and drops the
// event entirely if a closed-enum field is invalid — an invalid event is never
// emitted half-formed, and a bad enum can never leak an unexpected value.
func (l *Logger) Emit(event Event) {
	if l == nil || l.out == nil {
		return
	}
	event.SchemaVersion = SchemaVersion
	event.Timestamp = l.now().UTC().Format(time.RFC3339Nano)

	if !event.Severity.valid() || !event.Outcome.valid() || !event.FailureClass.valid() ||
		!knownEventCode(event.EventCode) || event.EventName == "" {
		// Fail closed: rather than emit a malformed or unclassified event,
		// emit a single fixed internal-invariant marker with no caller strings.
		event = Event{
			Severity:     SeverityError,
			EventName:    "obslog.invalid_event",
			EventCode:    EventInternalInvariant,
			Component:    ComponentServer,
			Outcome:      OutcomeFailure,
			FailureClass: FailureInternalInvariant,
		}
		event.SchemaVersion = SchemaVersion
		event.Timestamp = l.now().UTC().Format(time.RFC3339Nano)
	}

	event.Operation = clip(event.Operation, maxShortLen)
	event.RequestID = clip(event.RequestID, maxIdentifierLen)
	event.CorrelationID = clip(event.CorrelationID, maxIdentifierLen)
	event.JobID = clip(event.JobID, maxIdentifierLen)
	event.AttemptID = clip(event.AttemptID, maxShortLen)
	event.ActorType = clip(event.ActorType, maxShortLen)
	event.HTTPMethod = clip(event.HTTPMethod, maxShortLen)
	event.Route = clip(event.Route, maxIdentifierLen)

	encoded, err := json.Marshal(event)
	if err != nil {
		return
	}
	l.mu.Lock()
	defer l.mu.Unlock()
	_, _ = l.out.Write(append(encoded, '\n'))
}

func clip(value string, limit int) string {
	if len(value) <= limit {
		return value
	}
	return value[:limit]
}

// intPtr, int64Ptr and boolPtr build the optional numeric/bool fields.
func IntPtr(v int) *int       { return &v }
func Int64Ptr(v int64) *int64 { return &v }
func BoolPtr(v bool) *bool    { return &v }
