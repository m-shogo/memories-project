package metrics

import "time"

// SchemaVersion identifies the metric contract this package emits. The
// validator asserts it equals the machine-readable contract's schemaVersion.
const SchemaVersion = "memory-os-metrics.v1"

// Metric names. Fixed constants — a name is never built from input.
const (
	MetricHTTPRequestsTotal      = "memory_os_http_requests_total"
	MetricHTTPRequestDuration    = "memory_os_http_request_duration_seconds"
	MetricHTTPInFlight           = "memory_os_http_in_flight"
	MetricHTTPBodyRejectedTotal  = "memory_os_http_request_body_rejected_total"
	MetricHTTPPanicsTotal        = "memory_os_http_panics_total"
	MetricAppleExchangeTotal     = "memory_os_apple_exchange_total"
	MetricAppleExchangeDuration  = "memory_os_apple_exchange_duration_seconds"
	MetricAppleReplayRejections  = "memory_os_apple_replay_rejections_total"
	MetricSessionIssuanceTotal   = "memory_os_session_issuance_total"
	MetricRateLimitDecisions     = "memory_os_rate_limit_decisions_total"
	MetricRateLimitDuration      = "memory_os_rate_limit_decision_duration_seconds"
	MetricRateLimitStoreFailures = "memory_os_rate_limit_store_failures_total"
	MetricRateLimitActiveKeys    = "memory_os_rate_limit_active_keys"
	MetricDBOperationsTotal      = "memory_os_db_operations_total"
	MetricDBOperationDuration    = "memory_os_db_operation_duration_seconds"
	MetricDBFailuresTotal        = "memory_os_db_failures_total"
	MetricObjectStoreOpsTotal    = "memory_os_object_store_operations_total"
	MetricObjectStoreOpDuration  = "memory_os_object_store_operation_duration_seconds"
	MetricObjectStoreFailures    = "memory_os_object_store_failures_total"
	MetricImportOpsTotal         = "memory_os_import_operations_total"
	MetricImportOpDuration       = "memory_os_import_operation_duration_seconds"
	MetricImportItemsTotal       = "memory_os_import_items_total"
	MetricImportFailuresTotal    = "memory_os_import_failures_total"
	MetricDeletionJobsTotal      = "memory_os_deletion_jobs_total"
	MetricDeletionJobDuration    = "memory_os_deletion_job_duration_seconds"
	MetricDeletionBacklog        = "memory_os_deletion_backlog"
	MetricDeletionRetriesTotal   = "memory_os_deletion_retries_total"
	MetricDeletionTerminalTotal  = "memory_os_deletion_terminal_failures_total"
)

// Bucket sets. These are PROVISIONAL: chosen before load evidence exists and to
// be re-tuned after OPS-P0-006 load testing. Documented as such in the contract.
var (
	httpBuckets      = []float64{0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10}
	appleBuckets     = []float64{0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10}
	dbBuckets        = []float64{0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5}
	objectBuckets    = []float64{0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10}
	importBuckets    = []float64{0.05, 0.25, 1, 5, 15, 60, 300}
	deletionBuckets  = []float64{0.1, 0.5, 1, 5, 15, 60, 300}
	rateLimitBuckets = []float64{0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05}
)

// Recorder is the typed metrics surface. Every method takes enum-typed
// arguments — there is no generic IncCounter(name, map) exposed to business
// code, so a caller cannot invent a metric name or a label value. A nil
// Recorder is safe: metrics never block or fail the request path.
type Recorder interface {
	RecordHTTPRequest(route string, class RouteClass, method Method, status StatusClass, outcome Outcome, duration time.Duration)
	IncHTTPInFlight(delta int)
	RecordHTTPBodyRejected(route string, class RouteClass)
	RecordHTTPPanic(route string, class RouteClass)
	RecordAppleExchange(provider Provider, outcome Outcome, failure FailureClass, duration time.Duration)
	RecordAppleReplayRejection()
	RecordSessionIssuance(outcome Outcome)
	RecordRateLimitDecision(policyID, route string, class RouteClass, outcome Outcome, failure FailureClass, duration time.Duration)
	RecordRateLimitStoreFailure(policyID, route string)
	SetRateLimitActiveKeys(count int)
	RecordDBOperation(op Operation, outcome Outcome, failure FailureClass, duration time.Duration)
	RecordObjectStoreOperation(op Operation, outcome Outcome, failure FailureClass, duration time.Duration)
	RecordImportOperation(op Operation, outcome Outcome, failure FailureClass, duration time.Duration)
	RecordImportItems(op Operation, count int)
	RecordDeletionJob(worker WorkerName, outcome Outcome, failure FailureClass, duration time.Duration)
	SetDeletionBacklog(count int)
	RecordDeletionRetry(worker WorkerName)
	RecordDeletionTerminalFailure(worker WorkerName)
}

// Nop is a Recorder that does nothing. It is the default so an unconfigured
// deployment or a test that ignores metrics behaves identically.
type Nop struct{}

func (Nop) RecordHTTPRequest(string, RouteClass, Method, StatusClass, Outcome, time.Duration) {}
func (Nop) IncHTTPInFlight(int)                                                               {}
func (Nop) RecordHTTPBodyRejected(string, RouteClass)                                         {}
func (Nop) RecordHTTPPanic(string, RouteClass)                                                {}
func (Nop) RecordAppleExchange(Provider, Outcome, FailureClass, time.Duration)                {}
func (Nop) RecordAppleReplayRejection()                                                       {}
func (Nop) RecordSessionIssuance(Outcome)                                                     {}
func (Nop) RecordRateLimitDecision(string, string, RouteClass, Outcome, FailureClass, time.Duration) {
}
func (Nop) RecordRateLimitStoreFailure(string, string)                                 {}
func (Nop) SetRateLimitActiveKeys(int)                                                 {}
func (Nop) RecordDBOperation(Operation, Outcome, FailureClass, time.Duration)          {}
func (Nop) RecordObjectStoreOperation(Operation, Outcome, FailureClass, time.Duration) {}
func (Nop) RecordImportOperation(Operation, Outcome, FailureClass, time.Duration)      {}
func (Nop) RecordImportItems(Operation, int)                                           {}
func (Nop) RecordDeletionJob(WorkerName, Outcome, FailureClass, time.Duration)         {}
func (Nop) SetDeletionBacklog(int)                                                     {}
func (Nop) RecordDeletionRetry(WorkerName)                                             {}
func (Nop) RecordDeletionTerminalFailure(WorkerName)                                   {}

// PanicObserver is notified when the recorder recovers an internal panic, so it
// can be surfaced as a single low-information event without recursive logging.
type PanicObserver func()

// registryRecorder is the registry-backed Recorder. Every method recovers any
// internal panic so a metrics fault can never fail a business operation.
type registryRecorder struct {
	reg     *Registry
	onPanic PanicObserver
}

// NewRegistryRecorder registers every metric and returns a Recorder over the
// registry. onPanic may be nil.
func NewRegistryRecorder(reg *Registry, onPanic PanicObserver) Recorder {
	reg.register(spec{name: MetricHTTPRequestsTotal, kind: TypeCounter, labels: []string{"route_template", "route_class", "method", "status_class", "outcome"}, budget: 512})
	reg.register(spec{name: MetricHTTPRequestDuration, kind: TypeHistogram, labels: []string{"route_template", "route_class"}, buckets: httpBuckets, budget: 64})
	reg.register(spec{name: MetricHTTPInFlight, kind: TypeGauge, labels: []string{}, budget: 1})
	reg.register(spec{name: MetricHTTPBodyRejectedTotal, kind: TypeCounter, labels: []string{"route_template", "route_class"}, budget: 64})
	reg.register(spec{name: MetricHTTPPanicsTotal, kind: TypeCounter, labels: []string{"route_template", "route_class"}, budget: 64})
	reg.register(spec{name: MetricAppleExchangeTotal, kind: TypeCounter, labels: []string{"provider", "outcome", "failure_class"}, budget: 64})
	reg.register(spec{name: MetricAppleExchangeDuration, kind: TypeHistogram, labels: []string{"provider"}, buckets: appleBuckets, budget: 4})
	reg.register(spec{name: MetricAppleReplayRejections, kind: TypeCounter, labels: []string{}, budget: 1})
	reg.register(spec{name: MetricSessionIssuanceTotal, kind: TypeCounter, labels: []string{"outcome"}, budget: 8})
	reg.register(spec{name: MetricRateLimitDecisions, kind: TypeCounter, labels: []string{"policy_id", "route_class", "outcome", "failure_class"}, budget: 256})
	reg.register(spec{name: MetricRateLimitDuration, kind: TypeHistogram, labels: []string{"route_class"}, buckets: rateLimitBuckets, budget: 8})
	reg.register(spec{name: MetricRateLimitStoreFailures, kind: TypeCounter, labels: []string{"policy_id"}, budget: 16})
	reg.register(spec{name: MetricRateLimitActiveKeys, kind: TypeGauge, labels: []string{}, budget: 1})
	reg.register(spec{name: MetricDBOperationsTotal, kind: TypeCounter, labels: []string{"operation", "outcome", "failure_class"}, budget: 128})
	reg.register(spec{name: MetricDBOperationDuration, kind: TypeHistogram, labels: []string{"operation"}, buckets: dbBuckets, budget: 32})
	reg.register(spec{name: MetricDBFailuresTotal, kind: TypeCounter, labels: []string{"operation", "failure_class"}, budget: 64})
	reg.register(spec{name: MetricObjectStoreOpsTotal, kind: TypeCounter, labels: []string{"operation", "outcome", "failure_class"}, budget: 64})
	reg.register(spec{name: MetricObjectStoreOpDuration, kind: TypeHistogram, labels: []string{"operation"}, buckets: objectBuckets, budget: 16})
	reg.register(spec{name: MetricObjectStoreFailures, kind: TypeCounter, labels: []string{"operation", "failure_class"}, budget: 32})
	reg.register(spec{name: MetricImportOpsTotal, kind: TypeCounter, labels: []string{"operation", "outcome", "failure_class"}, budget: 64})
	reg.register(spec{name: MetricImportOpDuration, kind: TypeHistogram, labels: []string{"operation"}, buckets: importBuckets, budget: 16})
	reg.register(spec{name: MetricImportItemsTotal, kind: TypeCounter, labels: []string{"operation"}, budget: 16})
	reg.register(spec{name: MetricImportFailuresTotal, kind: TypeCounter, labels: []string{"operation", "failure_class"}, budget: 32})
	reg.register(spec{name: MetricDeletionJobsTotal, kind: TypeCounter, labels: []string{"worker_name", "outcome", "failure_class"}, budget: 32})
	reg.register(spec{name: MetricDeletionJobDuration, kind: TypeHistogram, labels: []string{"worker_name"}, buckets: deletionBuckets, budget: 4})
	reg.register(spec{name: MetricDeletionBacklog, kind: TypeGauge, labels: []string{}, budget: 1})
	reg.register(spec{name: MetricDeletionRetriesTotal, kind: TypeCounter, labels: []string{"worker_name"}, budget: 4})
	reg.register(spec{name: MetricDeletionTerminalTotal, kind: TypeCounter, labels: []string{"worker_name"}, budget: 4})
	return &registryRecorder{reg: reg, onPanic: onPanic}
}

// guard runs fn under a recover so a metrics fault never propagates. It notifies
// onPanic at most once per call and never logs the recovered value.
func (r *registryRecorder) guard(fn func()) {
	defer func() {
		if recover() != nil && r.onPanic != nil {
			r.onPanic()
		}
	}()
	fn()
}

func (r *registryRecorder) RecordHTTPRequest(route string, class RouteClass, method Method, status StatusClass, outcome Outcome, duration time.Duration) {
	r.guard(func() {
		route = NormalizeRoute(route)
		r.reg.incCounter(MetricHTTPRequestsTotal, map[string]string{
			"route_template": route, "route_class": class.normalize(), "method": method.normalize(),
			"status_class": status.normalize(), "outcome": outcome.normalize(),
		}, 1)
		r.reg.observe(MetricHTTPRequestDuration, map[string]string{
			"route_template": route, "route_class": class.normalize(),
		}, duration.Seconds())
	})
}

func (r *registryRecorder) IncHTTPInFlight(delta int) {
	r.guard(func() { r.reg.addGauge(MetricHTTPInFlight, map[string]string{}, float64(delta)) })
}

func (r *registryRecorder) RecordHTTPBodyRejected(route string, class RouteClass) {
	r.guard(func() {
		r.reg.incCounter(MetricHTTPBodyRejectedTotal, map[string]string{"route_template": NormalizeRoute(route), "route_class": class.normalize()}, 1)
	})
}

func (r *registryRecorder) RecordHTTPPanic(route string, class RouteClass) {
	r.guard(func() {
		r.reg.incCounter(MetricHTTPPanicsTotal, map[string]string{"route_template": NormalizeRoute(route), "route_class": class.normalize()}, 1)
	})
}

func (r *registryRecorder) RecordAppleExchange(provider Provider, outcome Outcome, failure FailureClass, duration time.Duration) {
	r.guard(func() {
		r.reg.incCounter(MetricAppleExchangeTotal, map[string]string{"provider": provider.normalize(), "outcome": outcome.normalize(), "failure_class": failure.normalize()}, 1)
		r.reg.observe(MetricAppleExchangeDuration, map[string]string{"provider": provider.normalize()}, duration.Seconds())
	})
}

func (r *registryRecorder) RecordAppleReplayRejection() {
	r.guard(func() { r.reg.incCounter(MetricAppleReplayRejections, map[string]string{}, 1) })
}

func (r *registryRecorder) RecordSessionIssuance(outcome Outcome) {
	r.guard(func() {
		r.reg.incCounter(MetricSessionIssuanceTotal, map[string]string{"outcome": outcome.normalize()}, 1)
	})
}

func (r *registryRecorder) RecordRateLimitDecision(policyID, route string, class RouteClass, outcome Outcome, failure FailureClass, duration time.Duration) {
	r.guard(func() {
		r.reg.incCounter(MetricRateLimitDecisions, map[string]string{"policy_id": NormalizePolicyID(policyID), "route_class": class.normalize(), "outcome": outcome.normalize(), "failure_class": failure.normalize()}, 1)
		r.reg.observe(MetricRateLimitDuration, map[string]string{"route_class": class.normalize()}, duration.Seconds())
	})
}

func (r *registryRecorder) RecordRateLimitStoreFailure(policyID, route string) {
	r.guard(func() {
		r.reg.incCounter(MetricRateLimitStoreFailures, map[string]string{"policy_id": NormalizePolicyID(policyID)}, 1)
	})
}

func (r *registryRecorder) SetRateLimitActiveKeys(count int) {
	r.guard(func() { r.reg.setGauge(MetricRateLimitActiveKeys, map[string]string{}, float64(count)) })
}

func (r *registryRecorder) RecordDBOperation(op Operation, outcome Outcome, failure FailureClass, duration time.Duration) {
	r.guard(func() {
		r.reg.incCounter(MetricDBOperationsTotal, map[string]string{"operation": op.normalize(), "outcome": outcome.normalize(), "failure_class": failure.normalize()}, 1)
		r.reg.observe(MetricDBOperationDuration, map[string]string{"operation": op.normalize()}, duration.Seconds())
		if outcome == OutcomeFailure {
			r.reg.incCounter(MetricDBFailuresTotal, map[string]string{"operation": op.normalize(), "failure_class": failure.normalize()}, 1)
		}
	})
}

func (r *registryRecorder) RecordObjectStoreOperation(op Operation, outcome Outcome, failure FailureClass, duration time.Duration) {
	r.guard(func() {
		r.reg.incCounter(MetricObjectStoreOpsTotal, map[string]string{"operation": op.normalize(), "outcome": outcome.normalize(), "failure_class": failure.normalize()}, 1)
		r.reg.observe(MetricObjectStoreOpDuration, map[string]string{"operation": op.normalize()}, duration.Seconds())
		if outcome == OutcomeFailure {
			r.reg.incCounter(MetricObjectStoreFailures, map[string]string{"operation": op.normalize(), "failure_class": failure.normalize()}, 1)
		}
	})
}

func (r *registryRecorder) RecordImportOperation(op Operation, outcome Outcome, failure FailureClass, duration time.Duration) {
	r.guard(func() {
		r.reg.incCounter(MetricImportOpsTotal, map[string]string{"operation": op.normalize(), "outcome": outcome.normalize(), "failure_class": failure.normalize()}, 1)
		r.reg.observe(MetricImportOpDuration, map[string]string{"operation": op.normalize()}, duration.Seconds())
		if outcome == OutcomeFailure {
			r.reg.incCounter(MetricImportFailuresTotal, map[string]string{"operation": op.normalize(), "failure_class": failure.normalize()}, 1)
		}
	})
}

func (r *registryRecorder) RecordImportItems(op Operation, count int) {
	r.guard(func() {
		if count > 0 {
			r.reg.incCounter(MetricImportItemsTotal, map[string]string{"operation": op.normalize()}, uint64(count))
		}
	})
}

func (r *registryRecorder) RecordDeletionJob(worker WorkerName, outcome Outcome, failure FailureClass, duration time.Duration) {
	r.guard(func() {
		r.reg.incCounter(MetricDeletionJobsTotal, map[string]string{"worker_name": worker.normalize(), "outcome": outcome.normalize(), "failure_class": failure.normalize()}, 1)
		r.reg.observe(MetricDeletionJobDuration, map[string]string{"worker_name": worker.normalize()}, duration.Seconds())
	})
}

func (r *registryRecorder) SetDeletionBacklog(count int) {
	r.guard(func() { r.reg.setGauge(MetricDeletionBacklog, map[string]string{}, float64(count)) })
}

func (r *registryRecorder) RecordDeletionRetry(worker WorkerName) {
	r.guard(func() {
		r.reg.incCounter(MetricDeletionRetriesTotal, map[string]string{"worker_name": worker.normalize()}, 1)
	})
}

func (r *registryRecorder) RecordDeletionTerminalFailure(worker WorkerName) {
	r.guard(func() {
		r.reg.incCounter(MetricDeletionTerminalTotal, map[string]string{"worker_name": worker.normalize()}, 1)
	})
}
