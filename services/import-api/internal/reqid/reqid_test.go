package reqid

import (
	"context"
	"strings"
	"testing"
)

func TestNewIsOpaqueAndPrefixed(t *testing.T) {
	id := New()
	if !strings.HasPrefix(id, "req_") || len(id) != len("req_")+32 {
		t.Fatalf("unexpected id shape: %q", id)
	}
	if id == New() {
		t.Fatal("ids are not unique")
	}
}

func TestFromInboundAcceptsWellFormed(t *testing.T) {
	for _, good := range []string{"abc123", "A.B_C-1", strings.Repeat("a", 64)} {
		id, accepted := FromInbound(good)
		if !accepted || id != good {
			t.Fatalf("well-formed inbound rejected: %q -> %q %v", good, id, accepted)
		}
	}
}

func TestFromInboundRejectsHostileValues(t *testing.T) {
	for _, bad := range []string{
		"",                          // empty
		strings.Repeat("a", 65),     // too long
		"has space",                 // whitespace
		"has\nnewline",              // newline that could reshape a log line
		`{"json":"injection"}`,      // JSON metacharacters
		"quote\"inside",             // quote
		"unicode-☃",                 // non-ascii
		"account:apple-subject-xyz", // colon (and looks like an identity)
	} {
		id, accepted := FromInbound(bad)
		if accepted {
			t.Fatalf("hostile inbound accepted: %q", bad)
		}
		if !strings.HasPrefix(id, "req_") {
			t.Fatalf("replacement id is not a fresh server id: %q", id)
		}
	}
}

func TestContextPropagation(t *testing.T) {
	ctx := context.Background()
	if RequestID(ctx) != "" || CorrelationID(ctx) != "" {
		t.Fatal("empty context should carry no ids")
	}
	ctx = WithRequestID(ctx, "req_abc")
	ctx = WithCorrelationID(ctx, "corr_def")
	if RequestID(ctx) != "req_abc" || CorrelationID(ctx) != "corr_def" {
		t.Fatalf("ids not propagated: %q %q", RequestID(ctx), CorrelationID(ctx))
	}
}

func TestNewCorrelationSanitizesPrefix(t *testing.T) {
	id := NewCorrelation("deletion")
	if !strings.HasPrefix(id, "deletion_") {
		t.Fatalf("prefix not used: %q", id)
	}
	// A hostile prefix is replaced, never echoed.
	hostile := NewCorrelation("bad prefix\nwith newline and way too long to allow")
	if !strings.HasPrefix(hostile, "corr_") {
		t.Fatalf("hostile prefix not sanitized: %q", hostile)
	}
}
