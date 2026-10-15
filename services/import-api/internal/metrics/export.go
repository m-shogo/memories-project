package metrics

import (
	"fmt"
	"sort"
	"strings"
)

// Export renders the registry as a stable, human/machine-readable text form for
// inspection and tests. It is NOT a production scrape endpoint — no such
// endpoint is exposed, which is one reason OPS-P0-004 is not READY. The output
// contains only fixed metric names, the registered label names and their
// normalized (allowlisted) values, and numeric samples; no free-form string
// from a caller can reach it.
func (r *Registry) Export() string {
	// Keep the registry locked while formatting: each series pointer contains
	// mutable counts, gauges and histogram buckets updated by concurrent writers.
	r.mu.Lock()
	defer r.mu.Unlock()
	names := make([]string, 0, len(r.specs))
	for name := range r.specs {
		names = append(names, name)
	}
	sort.Strings(names)

	var b strings.Builder
	for _, name := range names {
		s := r.specs[name]
		seriesKeys := make([]string, 0, len(r.seriesMap[name]))
		for key := range r.seriesMap[name] {
			seriesKeys = append(seriesKeys, key)
		}
		sort.Strings(seriesKeys)
		for _, key := range seriesKeys {
			series := r.seriesMap[name][key]
			labels := renderLabels(s.labels, series.labels)
			switch s.kind {
			case TypeCounter:
				fmt.Fprintf(&b, "%s%s %d\n", name, labels, series.count)
			case TypeGauge:
				fmt.Fprintf(&b, "%s%s %g\n", name, labels, series.gauge)
			case TypeHistogram:
				for i, upper := range s.buckets {
					fmt.Fprintf(&b, "%s_bucket%s %d\n", name, withLE(labels, upper), series.bucketCounts[i])
				}
				fmt.Fprintf(&b, "%s_count%s %d\n", name, labels, series.count)
				fmt.Fprintf(&b, "%s_sum%s %g\n", name, labels, series.sum)
			}
		}
	}
	return b.String()
}

func renderLabels(order []string, labels map[string]string) string {
	if len(order) == 0 {
		return ""
	}
	parts := make([]string, 0, len(order))
	for _, name := range order {
		parts = append(parts, fmt.Sprintf(`%s="%s"`, name, labels[name]))
	}
	return "{" + strings.Join(parts, ",") + "}"
}

func withLE(labels string, upper float64) string {
	le := fmt.Sprintf(`le="%g"`, upper)
	if labels == "" {
		return "{" + le + "}"
	}
	return labels[:len(labels)-1] + "," + le + "}"
}
