package obslog

// EventCode is a stable, low-cardinality identifier for an event kind. Codes
// are the join key between the running system and the machine-readable contract
// in contracts/operations/observability-event-contract.v1.json: the validator
// asserts this set and the contract's set are identical, so a new event kind
// cannot ship without being declared, and a declared code cannot be silently
// removed.
//
// Codes are internal event identifiers. They are deliberately distinct from the
// public HTTP problem codes (SEC_*): a client never sees an EventCode, and an
// operator never triages on a public SEC_ code. Mixing the two is what leaks
// internal detail to clients or hides internal state from operators.
type EventCode string

const (
	// Server lifecycle.
	EventServerStarted     EventCode = "OBS_SERVER_STARTED"
	EventServerStopping    EventCode = "OBS_SERVER_STOPPING"
	EventPanicRecovered    EventCode = "OBS_PANIC_RECOVERED"
	EventInternalInvariant EventCode = "OBS_INTERNAL_INVARIANT"

	// HTTP request lifecycle.
	EventHTTPRequest EventCode = "OBS_HTTP_REQUEST"

	// Apple sign-in.
	EventAppleLogin EventCode = "OBS_APPLE_LOGIN"

	// Upload.
	EventUploadIssue    EventCode = "OBS_UPLOAD_ISSUE"
	EventUploadComplete EventCode = "OBS_UPLOAD_COMPLETE"

	// Preview and apply.
	EventPreviewRead EventCode = "OBS_PREVIEW_READ"
	EventApply       EventCode = "OBS_APPLY"

	// Import flow boundary.
	EventImportFlow EventCode = "OBS_IMPORT_FLOW"

	// Rate limiting.
	EventRateLimitAllowed           EventCode = "OBS_RATE_LIMIT_ALLOWED"
	EventRateLimitRejected          EventCode = "OBS_RATE_LIMIT_REJECTED"
	EventRateLimitStoreUnavailable  EventCode = "OBS_RATE_LIMIT_STORE_UNAVAILABLE"
	EventRateLimitEmergencyFallback EventCode = "OBS_RATE_LIMIT_EMERGENCY_FALLBACK"
	EventRateLimitPolicyInvalid     EventCode = "OBS_RATE_LIMIT_POLICY_INVALID"
	EventRateLimitKeyCapacity       EventCode = "OBS_RATE_LIMIT_KEY_CAPACITY_REJECTED"

	// Account deletion request and background worker.
	EventDeletionRequested EventCode = "OBS_DELETION_REQUESTED"
	EventDeletionClaimed   EventCode = "OBS_DELETION_CLAIMED"
	EventDeletionCompleted EventCode = "OBS_DELETION_COMPLETED"
	EventDeletionRetry     EventCode = "OBS_DELETION_RETRY"
	EventDeletionBacklog   EventCode = "OBS_DELETION_BACKLOG"
)

// AllEventCodes is the authoritative set. Order is fixed for deterministic
// contract comparison.
var AllEventCodes = []EventCode{
	EventServerStarted,
	EventServerStopping,
	EventPanicRecovered,
	EventInternalInvariant,
	EventHTTPRequest,
	EventRateLimitAllowed,
	EventRateLimitRejected,
	EventRateLimitStoreUnavailable,
	EventRateLimitEmergencyFallback,
	EventRateLimitPolicyInvalid,
	EventRateLimitKeyCapacity,
	EventAppleLogin,
	EventUploadIssue,
	EventUploadComplete,
	EventPreviewRead,
	EventApply,
	EventImportFlow,
	EventDeletionRequested,
	EventDeletionClaimed,
	EventDeletionCompleted,
	EventDeletionRetry,
	EventDeletionBacklog,
}

var eventCodeSet = func() map[EventCode]struct{} {
	set := make(map[EventCode]struct{}, len(AllEventCodes))
	for _, code := range AllEventCodes {
		set[code] = struct{}{}
	}
	return set
}()

func knownEventCode(code EventCode) bool {
	_, ok := eventCodeSet[code]
	return ok
}
