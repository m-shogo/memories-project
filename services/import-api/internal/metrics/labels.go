// Package metrics is a bounded, privacy-preserving, typed runtime metrics
// registry. It is a separate responsibility from obslog: there is no path that
// turns a log event into a metric label, and business code can never pass an
// arbitrary metric name or an arbitrary label map. Every label is a typed
// enumeration whose value is normalized to a fixed allowlisted token before it
// reaches a series, so a request ID, an account ID, a raw URL, an IP, a token
// or an error string can never become a label value and can never inflate
// series cardinality.
//
// The registry is stdlib-only. The Recorder interface is the adapter boundary
// where a Prometheus or OpenTelemetry exporter would plug in; none is wired
// here, and no production scrape endpoint is exposed, which is why OPS-P0-004
// is not READY.
package metrics

// Every label type below is a closed enumeration. Its normalize method maps any
// value not in the set to a fixed "unknown"/"other" token, so cardinality is
// bounded by the enum, never by the caller's input.

// Component names the subsystem a metric belongs to.
type Component string

const (
	ComponentHTTP        Component = "http"
	ComponentApple       Component = "apple_auth"
	ComponentRateLimit   Component = "rate_limit"
	ComponentDB          Component = "db"
	ComponentObjectStore Component = "object_store"
	ComponentImport      Component = "import"
	ComponentDeletion    Component = "deletion_worker"
)

// Outcome is the coarse result class shared across metrics.
type Outcome string

const (
	OutcomeSuccess  Outcome = "success"
	OutcomeFailure  Outcome = "failure"
	OutcomeRejected Outcome = "rejected"
)

func (o Outcome) normalize() string {
	switch o {
	case OutcomeSuccess, OutcomeFailure, OutcomeRejected:
		return string(o)
	}
	return "unknown"
}

// FailureClass is the bounded failure taxonomy. It mirrors the concepts obslog
// uses but is an independent enum so metrics stay decoupled from logging.
type FailureClass string

const (
	FailNone           FailureClass = "none"
	FailAuthentication FailureClass = "authentication_failure"
	FailAuthorization  FailureClass = "authorization_denied"
	FailInvalidRequest FailureClass = "invalid_request"
	FailReplay         FailureClass = "replay_rejected"
	FailExternalApple  FailureClass = "external_apple_failure"
	FailDatabase       FailureClass = "database_unavailable"
	FailObjectStore    FailureClass = "object_store_unavailable"
	FailParser         FailureClass = "parser_failure"
	FailIntegrity      FailureClass = "integrity_failure"
	FailRateLimited    FailureClass = "rate_limited"
	FailStoreUnavail   FailureClass = "store_unavailable"
	FailDeletionRetry  FailureClass = "deletion_retry"
	FailDeletionTerm   FailureClass = "deletion_terminal_failure"
	FailInternal       FailureClass = "internal_invariant_violation"
	FailPanic          FailureClass = "panic_recovered"
)

var failureClasses = map[FailureClass]struct{}{
	FailNone: {}, FailAuthentication: {}, FailAuthorization: {}, FailInvalidRequest: {},
	FailReplay: {}, FailExternalApple: {}, FailDatabase: {}, FailObjectStore: {},
	FailParser: {}, FailIntegrity: {}, FailRateLimited: {}, FailStoreUnavail: {},
	FailDeletionRetry: {}, FailDeletionTerm: {}, FailInternal: {}, FailPanic: {},
}

func (f FailureClass) normalize() string {
	if _, ok := failureClasses[f]; ok {
		return string(f)
	}
	return "unknown"
}

// StatusClass is the coarse HTTP status bucket. Individual status codes are
// never used as a label — that would be a per-code cardinality risk with no
// budget.
type StatusClass string

const (
	Status1xx StatusClass = "1xx"
	Status2xx StatusClass = "2xx"
	Status3xx StatusClass = "3xx"
	Status4xx StatusClass = "4xx"
	Status5xx StatusClass = "5xx"
)

// StatusClassFor maps a numeric status to its class.
func StatusClassFor(code int) StatusClass {
	switch {
	case code >= 500:
		return Status5xx
	case code >= 400:
		return Status4xx
	case code >= 300:
		return Status3xx
	case code >= 200:
		return Status2xx
	default:
		return Status1xx
	}
}

func (s StatusClass) normalize() string {
	switch s {
	case Status1xx, Status2xx, Status3xx, Status4xx, Status5xx:
		return string(s)
	}
	return "unknown"
}

// Method is the bounded HTTP method set; anything else is "other".
type Method string

const (
	MethodGet    Method = "GET"
	MethodPost   Method = "POST"
	MethodDelete Method = "DELETE"
	MethodOther  Method = "other"
)

// MethodFor normalizes a raw method string to the enum.
func MethodFor(raw string) Method {
	switch raw {
	case "GET":
		return MethodGet
	case "POST":
		return MethodPost
	case "DELETE":
		return MethodDelete
	default:
		return MethodOther
	}
}

func (m Method) normalize() string {
	switch m {
	case MethodGet, MethodPost, MethodDelete:
		return string(m)
	}
	return "other"
}

// RouteClass mirrors the rate-limit route classes.
type RouteClass string

const (
	RoutePublicUnauthenticated RouteClass = "PUBLIC_UNAUTHENTICATED"
	RoutePublicAuthenticated   RouteClass = "PUBLIC_AUTHENTICATED"
	RouteHealth                RouteClass = "HEALTH"
	RouteInternal              RouteClass = "INTERNAL"
)

func (r RouteClass) normalize() string {
	switch r {
	case RoutePublicUnauthenticated, RoutePublicAuthenticated, RouteHealth, RouteInternal:
		return string(r)
	}
	return "unknown"
}

// allowedRouteTemplates is the fixed set of route templates any metric may
// carry. A raw path is never used; an unrecognized template collapses to
// "other", so a user-controlled path cannot mint a new series.
var allowedRouteTemplates = map[string]struct{}{
	"GET /healthz":        {},
	"POST /v1/auth/apple": {},
	"DELETE /v1/account":  {},
	"POST /v1/import-jobs/{jobId}/upload-authorizations":               {},
	"POST /v1/import-jobs/{jobId}/upload-authorizations/{id}/complete": {},
	"GET /v1/import-jobs/{jobId}/preview":                              {},
	"POST /v1/previews/{previewId}/apply":                              {},
	"other":                                                            {},
}

// NormalizeRoute collapses any unrecognized template to "other".
func NormalizeRoute(template string) string {
	if _, ok := allowedRouteTemplates[template]; ok {
		return template
	}
	return "other"
}

// Operation enumerates the bounded operation labels per component. Each is a
// fixed token; a caller cannot introduce a new one.
type Operation string

const (
	// Apple.
	OpAppleExchange   Operation = "apple_exchange"
	OpSessionIssuance Operation = "session_issuance"
	// DB.
	OpDBBeginDeletion Operation = "begin_deletion"
	OpDBSweep         Operation = "sweep"
	OpDBResolve       Operation = "resolve_session"
	OpDBProvision     Operation = "provision_identity"
	// Object store.
	OpObjPresign Operation = "presign"
	OpObjHead    Operation = "head"
	OpObjErase   Operation = "erase"
	// Import.
	OpImportParse  Operation = "parse"
	OpImportVerify Operation = "verify"
	OpImportCommit Operation = "commit"
	// Deletion.
	OpDeletionSweep Operation = "deletion_sweep"
)

var operations = map[Operation]struct{}{
	OpAppleExchange: {}, OpSessionIssuance: {}, OpDBBeginDeletion: {}, OpDBSweep: {},
	OpDBResolve: {}, OpDBProvision: {}, OpObjPresign: {}, OpObjHead: {}, OpObjErase: {},
	OpImportParse: {}, OpImportVerify: {}, OpImportCommit: {}, OpDeletionSweep: {},
}

func (o Operation) normalize() string {
	if _, ok := operations[o]; ok {
		return string(o)
	}
	return "unknown"
}

// PolicyID is the bounded set of rate-limit policy identifiers used as a label.
// It matches the shipped policy contract; an unrecognized id is "unknown".
var allowedPolicyIDs = map[string]struct{}{
	"POST /v1/auth/apple": {},
	"DELETE /v1/account":  {},
	"POST /v1/import-jobs/{jobId}/upload-authorizations":               {},
	"POST /v1/import-jobs/{jobId}/upload-authorizations/{id}/complete": {},
	"GET /v1/import-jobs/{jobId}/preview":                              {},
	"POST /v1/previews/{previewId}/apply":                              {},
	"other":                                                            {},
}

// NormalizePolicyID collapses an unrecognized policy id to "unknown". Policy ids
// are route templates in the shipped set, so this reuses the route allowlist.
func NormalizePolicyID(id string) string {
	if _, ok := allowedPolicyIDs[id]; ok {
		return id
	}
	return "unknown"
}

// WorkerName is the bounded set of background worker identities.
type WorkerName string

const WorkerDeletion WorkerName = "deletion_runtime"

func (w WorkerName) normalize() string {
	if w == WorkerDeletion {
		return string(w)
	}
	return "unknown"
}

// Provider names the external identity provider for auth metrics.
type Provider string

const ProviderApple Provider = "apple"

func (p Provider) normalize() string {
	if p == ProviderApple {
		return string(p)
	}
	return "unknown"
}
