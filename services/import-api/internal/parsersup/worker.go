package parsersup

import (
	"bufio"
	"io"
	"os"
	"strings"
	"time"
)

// WorkerModeEnv selects the harness behavior when the test binary is
// re-executed as a supervised worker.
const WorkerModeEnv = "MEMORY_OS_PARSER_WORKER_MODE"

// RunWorker is the supervised side of the frame protocol used by the targeted
// isolation tests. A production deployment replaces this harness with a
// reviewed digest-pinned adapter artifact; the supervisor treats any worker
// binary as untrusted either way.
func RunWorker(mode string, input io.Reader, output io.Writer) int {
	switch mode {
	case "parse":
		scanner := bufio.NewScanner(input)
		for scanner.Scan() {
			line := scanner.Text()
			switch {
			case strings.HasPrefix(line, "a:"):
				if err := writeFrame(output, frameTagAccepted, []byte(line[2:])); err != nil {
					return 4
				}
			case strings.HasPrefix(line, "r:"):
				if err := writeFrame(output, frameTagRejected, []byte(line[2:])); err != nil {
					return 4
				}
			case line == "":
			default:
				return 3
			}
		}
		if scanner.Err() != nil {
			return 5
		}
		return 0
	case "hog":
		hoard := make([][]byte, 0, 96)
		for i := 0; i < 96; i++ {
			block := make([]byte, 64<<20)
			for j := 0; j < len(block); j += 4096 {
				block[j] = 1
			}
			hoard = append(hoard, block)
		}
		_ = hoard
		return 0
	case "spin":
		for {
			_ = time.Now()
		}
	case "sleep":
		time.Sleep(time.Hour)
		return 0
	case "garbage":
		junk := make([]byte, 1<<20)
		for i := range junk {
			junk[i] = 0xFF
		}
		_, _ = output.Write(junk)
		return 0
	case "oversize":
		oversized := make([]byte, 8)
		oversized = append([]byte{frameTagAccepted, 0, 0, 0, 0, 0, 48, 0, 0}, oversized...)
		_, _ = output.Write(oversized)
		return 0
	case "partial":
		_, _ = output.Write([]byte{frameTagAccepted, 0, 0, 0, 0})
		return 0
	case "env":
		environ := os.Environ()
		if len(environ) != 1 || !strings.HasPrefix(environ[0], WorkerModeEnv+"=") {
			return 9
		}
		if err := writeFrame(output, frameTagAccepted, []byte(`{"title":"env-clean"}`)); err != nil {
			return 4
		}
		return 0
	case "file":
		if err := os.WriteFile("/tmp/memory-os-parser-escape", []byte{1}, 0o600); err != nil {
			return 7
		}
		if err := writeFrame(output, frameTagAccepted, []byte(`{"title":"escaped"}`)); err != nil {
			return 4
		}
		return 0
	default:
		return 8
	}
}
