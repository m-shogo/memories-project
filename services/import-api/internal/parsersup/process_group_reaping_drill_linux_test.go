//go:build linux

package parsersup

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"testing"
	"time"
)

const orphanMarkerEnv = "MEMORY_OS_PARSER_ORPHAN_MARKER"

// TestSupervisorReapsChildProcessGroupAfterCancellation proves that the Linux
// supervisor does not merely reap the direct worker. The harness starts one
// child that inherits the worker process group; the test captures both /proc
// identities before cancellation, then requires every captured process entry to
// disappear after Parse returns. Raw process identifiers are never logged or
// persisted as evidence.
func TestSupervisorReapsChildProcessGroupAfterCancellation(t *testing.T) {
	manager, root := newSpoolManager(t)
	marker := fmt.Sprintf("reaping-%d", time.Now().UnixNano())
	config := testConfig(t, "frame_child_then_sleep")
	config.WorkerEnv = append(config.WorkerEnv, orphanMarkerEnv+"="+marker)
	config.Limits.WallClock = 10 * time.Second
	supervisor, err := NewSupervisor(config)
	if err != nil {
		t.Fatal(err)
	}
	source := sourceFile(t, "a:{\"title\":\"source\"}\n")
	seal := testSealInput()

	ctx, cancel := context.WithCancel(context.Background())
	result := make(chan error, 1)
	go func() {
		_, parseErr := supervisor.Parse(ctx, ParseRequest{
			Manager: manager,
			SpoolID: testSpoolID,
			Source:  source,
			Seal:    seal,
		})
		result <- parseErr
	}()

	deadline := time.Now().Add(3 * time.Second)
	for !spoolAttemptContainsData(root, testSpoolID) {
		if time.Now().After(deadline) {
			cancel()
			t.Fatal("worker did not emit a frame before process-group scan")
		}
		time.Sleep(10 * time.Millisecond)
	}

	var tracked []int
	for {
		tracked = markedProcessIDs(marker)
		if len(tracked) >= 2 {
			break
		}
		if time.Now().After(deadline) {
			cancel()
			t.Fatalf("expected worker plus child before cancellation, observed %d marked process(es)", len(tracked))
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Logf("MEMORY_OS_TRACKED_PROCESS_COUNT_BEFORE_CANCEL=%d", len(tracked))

	cancelStarted := time.Now()
	cancel()
	select {
	case parseErr := <-result:
		if !errors.Is(parseErr, context.Canceled) {
			t.Fatalf("process-group cancellation error drift: %v", parseErr)
		}
		elapsed := time.Since(cancelStarted)
		if elapsed >= time.Second {
			t.Fatalf("process-group cancellation was not prompt: %s", elapsed)
		}
		t.Logf("MEMORY_OS_REAP_CANCELLATION_LATENCY_MS=%d", elapsed.Milliseconds())
	case <-time.After(time.Second):
		t.Fatal("process-group cancellation waited for the wall-clock limit")
	}
	assertRootEmpty(t, root)

	reapDeadline := time.Now().Add(3 * time.Second)
	for !allProcEntriesGone(tracked) {
		if time.Now().After(reapDeadline) {
			t.Fatal("captured worker process-group members remained in /proc after Parse returned")
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Log("MEMORY_OS_TRACKED_PROCESS_COUNT_AFTER_CANCEL=0")
}

func markedProcessIDs(marker string) []int {
	entries, err := os.ReadDir("/proc")
	if err != nil {
		return nil
	}
	needle := []byte(orphanMarkerEnv + "=" + marker + "\x00")
	pids := make([]int, 0, 2)
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		pid, err := strconv.Atoi(entry.Name())
		if err != nil {
			continue
		}
		environment, err := os.ReadFile(filepath.Join("/proc", entry.Name(), "environ"))
		if err != nil {
			continue
		}
		if bytes.Contains(environment, needle) {
			pids = append(pids, pid)
		}
	}
	return pids
}

func allProcEntriesGone(pids []int) bool {
	for _, pid := range pids {
		_, err := os.Stat(filepath.Join("/proc", strconv.Itoa(pid)))
		if err == nil || !os.IsNotExist(err) {
			return false
		}
	}
	return true
}
