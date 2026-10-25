package httpserver

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

// writeAtomicLocalLoadResult writes local test evidence only. It refuses symlink
// targets, preserves an existing regular file's mode, and never publishes a
// partial target if the final rename fails.
func writeAtomicLocalLoadResult(path string, payload []byte, rename func(string, string) error) error {
	if rename == nil {
		return fmt.Errorf("local load result rename authority missing")
	}
	mode := os.FileMode(0o644)
	info, err := os.Lstat(path)
	if err == nil {
		if !info.Mode().IsRegular() {
			return fmt.Errorf("local load result target is not a regular file")
		}
		mode = info.Mode().Perm()
	} else if !errors.Is(err, os.ErrNotExist) {
		return err
	}
	dir := filepath.Dir(path)
	file, err := os.CreateTemp(dir, "."+filepath.Base(path)+".*.tmp")
	if err != nil {
		return err
	}
	tempName := file.Name()
	defer os.Remove(tempName)
	if err := file.Chmod(mode); err != nil {
		file.Close()
		return err
	}
	if _, err := file.Write(payload); err != nil {
		file.Close()
		return err
	}
	if err := file.Sync(); err != nil {
		file.Close()
		return err
	}
	if err := file.Close(); err != nil {
		return err
	}
	return rename(tempName, path)
}

func TestAtomicLocalLoadResultWriter(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "result.json")
	if err := os.WriteFile(path, []byte("before\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := writeAtomicLocalLoadResult(path, []byte("after\n"), os.Rename); err != nil {
		t.Fatal(err)
	}
	if data, err := os.ReadFile(path); err != nil || string(data) != "after\n" {
		t.Fatalf("atomic write content mismatch: %q, %v", data, err)
	}
	if info, err := os.Stat(path); err != nil || info.Mode().Perm() != 0o600 {
		t.Fatalf("atomic write mode mismatch: %v, %v", info, err)
	}
	before, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	denied := errors.New("synthetic rename denial")
	if err := writeAtomicLocalLoadResult(path, []byte("forbidden\n"), func(string, string) error { return denied }); !errors.Is(err, denied) {
		t.Fatalf("atomic rename denial was not propagated: %v", err)
	}
	if after, err := os.ReadFile(path); err != nil || string(after) != string(before) {
		t.Fatalf("failed rename modified target: %q, %v", after, err)
	}
	if temps, err := filepath.Glob(filepath.Join(dir, ".result.json.*.tmp")); err != nil || len(temps) != 0 {
		t.Fatalf("atomic temp leaked: %v, %v", temps, err)
	}
	outside := filepath.Join(dir, "outside.json")
	if err := os.WriteFile(outside, []byte("external sentinel\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(dir, "symlink.json")
	if err := os.Symlink(outside, link); err != nil {
		t.Fatal(err)
	}
	if err := writeAtomicLocalLoadResult(link, []byte("forbidden\n"), os.Rename); err == nil {
		t.Fatal("symlink result target was accepted")
	}
	if data, err := os.ReadFile(outside); err != nil || string(data) != "external sentinel\n" {
		t.Fatalf("symlink changed external sentinel: %q, %v", data, err)
	}
	fresh := filepath.Join(dir, "fresh.json")
	if err := writeAtomicLocalLoadResult(fresh, []byte("fresh\n"), os.Rename); err != nil {
		t.Fatal(err)
	}
	if info, err := os.Stat(fresh); err != nil || info.Mode().Perm() != 0o644 {
		t.Fatalf("new atomic target mode mismatch: %v, %v", info, err)
	}
}
