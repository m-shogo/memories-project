package loadtest

import "testing"

func TestDependencyModeForScenario(t *testing.T) {
	tests := map[string]string{
		"apple-steady-mock":              "MOCK",
		"apple-burst-mock":               "MOCK",
		"cardinality-attack-mock":         "MOCK",
		"authenticated-preview-mock":      "MOCK",
		"concurrent-apply-mock":           "MOCK",
		"ratelimit-store-failure-mock":    "FAILURE_INJECTED",
		"future-unclassified-local-scenario": "MOCK",
	}
	for scenarioID, want := range tests {
		if got := dependencyModeForScenario(scenarioID); got != want {
			t.Fatalf("dependencyModeForScenario(%q)=%q, want %q", scenarioID, got, want)
		}
	}
}
