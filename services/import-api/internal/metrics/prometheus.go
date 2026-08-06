package metrics

import (
	"fmt"
	"sort"
	"strconv"
	"strings"
)

// Prometheus renders a concurrency-safe snapshot in the Prometheus text
// exposition format 0.0.4. Metric names, label names and label values all come
// from the closed registry contract; caller-controlled values cannot reach the
// output. Histogram buckets include the mandatory +Inf bucket.
func (r *Registry) Prometheus() string {
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
		fmt.Fprintf(&b, "# TYPE %s %s\n", name, prometheusType(s.kind))

		seriesKeys := make([]string, 0, len(r.seriesMap[name]))
		for key := range r.seriesMap[name] {
			seriesKeys = append(seriesKeys, key)
		}
		sort.Strings(seriesKeys)

		for _, key := range seriesKeys {
			series := r.seriesMap[name][key]
			labels := prometheusLabels(s.labels, series.labels, "", "")
			switch s.kind {
			case TypeCounter:
				fmt.Fprintf(&b, "%s%s %d\n", name, labels, series.count)
			case TypeGauge:
				fmt.Fprintf(&b, "%s%s %s\n", name, labels, prometheusFloat(series.gauge))
			case TypeHistogram:
				for index, upper := range s.buckets {
					bucketLabels := prometheusLabels(s.labels, series.labels, "le", prometheusFloat(upper))
					fmt.Fprintf(&b, "%s_bucket%s %d\n", name, bucketLabels, series.bucketCounts[index])
				}
				infinityLabels := prometheusLabels(s.labels, series.labels, "le", "+Inf")
				fmt.Fprintf(&b, "%s_bucket%s %d\n", name, infinityLabels, series.count)
				fmt.Fprintf(&b, "%s_sum%s %s\n", name, labels, prometheusFloat(series.sum))
				fmt.Fprintf(&b, "%s_count%s %d\n", name, labels, series.count)
			}
		}
	}
	return b.String()
}

func prometheusType(kind MetricType) string {
	switch kind {
	case TypeCounter:
		return "counter"
	case TypeGauge:
		return "gauge"
	case TypeHistogram:
		return "histogram"
	default:
		return "untyped"
	}
}

func prometheusFloat(value float64) string {
	return strconv.FormatFloat(value, 'g', -1, 64)
}

func prometheusLabels(order []string, labels map[string]string, extraName, extraValue string) string {
	count := len(order)
	if extraName != "" {
		count++
	}
	if count == 0 {
		return ""
	}

	parts := make([]string, 0, count)
	for _, name := range order {
		parts = append(parts, fmt.Sprintf(`%s="%s"`, name, prometheusEscape(labels[name])))
	}
	if extraName != "" {
		parts = append(parts, fmt.Sprintf(`%s="%s"`, extraName, prometheusEscape(extraValue)))
	}
	return "{" + strings.Join(parts, ",") + "}"
}

func prometheusEscape(value string) string {
	value = strings.ReplaceAll(value, `\`, `\\`)
	value = strings.ReplaceAll(value, "\n", `\n`)
	value = strings.ReplaceAll(value, `"`, `\"`)
	return value
}
