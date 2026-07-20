//go:build race

package parsersup

// raceDetectorEnabled widens the worker address-space limit in tests: the
// race runtime reserves very large shadow address ranges, so RLIMIT_AS cannot
// be meaningfully enforced on race-instrumented worker binaries.
const raceDetectorEnabled = true
