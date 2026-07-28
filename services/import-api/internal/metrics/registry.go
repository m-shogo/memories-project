package metrics

import (
	"math"
	"sort"
	"strings"
	"sync"
)

// MetricType is the closed set of metric kinds.
type MetricType string

const (
	TypeCounter   MetricType = "counter"
	TypeGauge     MetricType = "gauge"
	TypeHistogram MetricType = "histogram"
)

// spec describes a registered metric: its type, its ordered label names, its
// histogram buckets (for histograms) and its per-metric series budget. Specs
// are fixed at construction, so a metric's shape cannot change at runtime.
type spec struct {
	name    string
	kind    MetricType
	labels  []string
	buckets []float64
	budget  int
}

// series is one label-combination's accumulated value.
type series struct {
	labels       map[string]string
	count        uint64  // counter total, or histogram observation count
	gauge        float64 // gauge current value
	sum          float64 // histogram sum
	bucketCounts []uint64
}

// Registry holds all metric series with bounded cardinality. It is safe for
// concurrent use. When a metric's series budget is reached, further new label
// combinations are dropped and counted, never admitted — cardinality is bounded
// even under a hostile label stream (which the typed API already prevents, this
// is defence in depth).
type Registry struct {
	mu        sync.Mutex
	specs     map[string]spec
	seriesMap map[string]map[string]*series // metric name -> series key -> series
	dropped   map[string]uint64             // metric name -> dropped-series count
}

// NewRegistry builds an empty registry.
func NewRegistry() *Registry {
	return &Registry{
		specs:     map[string]spec{},
		seriesMap: map[string]map[string]*series{},
		dropped:   map[string]uint64{},
	}
}

// register declares a metric. Re-registering the same name with the same shape
// is idempotent; a conflicting re-registration is rejected (returns false) so a
// duplicate registration cannot silently change a metric's meaning.
func (r *Registry) register(s spec) bool {
	r.mu.Lock()
	defer r.mu.Unlock()
	if existing, ok := r.specs[s.name]; ok {
		return existing.kind == s.kind && equalStrings(existing.labels, s.labels) &&
			equalFloats(existing.buckets, s.buckets) && existing.budget == s.budget
	}
	if s.budget <= 0 {
		s.budget = 256
	}
	if s.kind == TypeHistogram && !validBuckets(s.buckets) {
		// A malformed bucket set is a programming error surfaced at startup:
		// refuse the registration rather than silently accept bad buckets.
		return false
	}
	r.specs[s.name] = s
	r.seriesMap[s.name] = map[string]*series{}
	return true
}

// getOrCreate returns the series for a label set, creating it if the budget
// allows. Returns nil when the budget is exhausted (the observation is dropped).
func (r *Registry) getOrCreate(name string, labels map[string]string) (*series, spec, bool) {
	s := r.specs[name]
	key := seriesKey(s.labels, labels)
	bucket := r.seriesMap[name]
	if existing, ok := bucket[key]; ok {
		return existing, s, true
	}
	if len(bucket) >= s.budget {
		r.dropped[name]++
		return nil, s, false
	}
	created := &series{labels: labels}
	if s.kind == TypeHistogram {
		created.bucketCounts = make([]uint64, len(s.buckets))
	}
	bucket[key] = created
	return created, s, true
}

func (r *Registry) incCounter(name string, labels map[string]string, delta uint64) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if series, _, ok := r.getOrCreate(name, labels); ok {
		series.count += delta
	}
}

func (r *Registry) addGauge(name string, labels map[string]string, delta float64) {
	if isBadFloat(delta) {
		return
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if series, _, ok := r.getOrCreate(name, labels); ok {
		series.gauge += delta
	}
}

func (r *Registry) setGauge(name string, labels map[string]string, value float64) {
	if isBadFloat(value) {
		return
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if series, _, ok := r.getOrCreate(name, labels); ok {
		series.gauge = value
	}
}

// observe records a histogram sample. A negative, NaN or Inf value is rejected
// (dropped) rather than corrupting the sum or bucket counts.
func (r *Registry) observe(name string, labels map[string]string, value float64) {
	if isBadFloat(value) || value < 0 {
		return
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	series, s, ok := r.getOrCreate(name, labels)
	if !ok {
		return
	}
	series.count++
	series.sum += value
	for i, upper := range s.buckets {
		if value <= upper {
			series.bucketCounts[i]++
		}
	}
}

// SeriesCount returns the number of live series for a metric, for tests.
func (r *Registry) SeriesCount(name string) int {
	r.mu.Lock()
	defer r.mu.Unlock()
	return len(r.seriesMap[name])
}

// DroppedSeries returns how many new series were refused for a metric because
// its budget was exhausted, for tests and self-monitoring.
func (r *Registry) DroppedSeries(name string) uint64 {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.dropped[name]
}

func isBadFloat(v float64) bool { return math.IsNaN(v) || math.IsInf(v, 0) }

func seriesKey(labelOrder []string, labels map[string]string) string {
	var b strings.Builder
	for _, name := range labelOrder {
		b.WriteString(name)
		b.WriteByte('=')
		b.WriteString(labels[name])
		b.WriteByte('\x1f')
	}
	return b.String()
}

func equalStrings(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func equalFloats(a, b []float64) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

// validBuckets checks a histogram bucket set: ascending, unique, positive,
// bounded count. Used at registration; a bad bucket set fails registration.
func validBuckets(buckets []float64) bool {
	if len(buckets) == 0 || len(buckets) > 20 {
		return false
	}
	prev := math.Inf(-1)
	for _, b := range buckets {
		if isBadFloat(b) || b <= 0 || b <= prev {
			return false
		}
		prev = b
	}
	return true
}

// sortedSeries returns a metric's series in a deterministic order, for export.
func (r *Registry) sortedSeries(name string) []*series {
	r.mu.Lock()
	defer r.mu.Unlock()
	bucket := r.seriesMap[name]
	keys := make([]string, 0, len(bucket))
	for k := range bucket {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	out := make([]*series, 0, len(keys))
	for _, k := range keys {
		out = append(out, bucket[k])
	}
	return out
}
