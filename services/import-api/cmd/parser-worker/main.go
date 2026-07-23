//go:build linux

// parser-worker is the separately built Generic CSV worker artifact the
// supervisor digest-pins and spawns. It reads staged CSV bytes on stdin,
// takes strict options JSON from MEMORY_OS_CSV_OPTIONS, and emits canonical
// adapter record frames on stdout. It never opens the spool, database, object
// storage or any credential; the supervisor owns all of those and treats any
// nonzero exit as a terminal fail-closed parse failure.
package main

import (
	"os"

	"github.com/m-shogo/memories-project/services/import-api/internal/csvworker"
)

func main() {
	os.Exit(csvworker.Run(os.Getenv(csvworker.OptionsEnv), os.Stdin, os.Stdout, os.Stderr))
}
