package cryptoids

import (
	"bytes"
	"strings"
	"testing"
)

func TestGeneratorCreatesOpaqueStableLengthID(t *testing.T) {
	generator := Generator{Random: bytes.NewReader(bytes.Repeat([]byte{0xAB}, 20))}
	value, err := generator.NewID("upl")
	if err != nil {
		t.Fatal(err)
	}
	if !strings.HasPrefix(value, "upl_") || len(value) != 36 {
		t.Fatalf("unexpected ID: %q len=%d", value, len(value))
	}
}

func TestGeneratorRejectsUnsafePrefix(t *testing.T) {
	if _, err := (Generator{}).NewID("Upload;DROP"); err == nil {
		t.Fatal("expected invalid prefix error")
	}
}
