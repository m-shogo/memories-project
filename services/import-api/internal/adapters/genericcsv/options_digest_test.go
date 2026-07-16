package genericcsv

import (
	"errors"
	"testing"
	"time"
)

func TestNormalizeAndDigestOptionsCanonicalizesEquivalentMappings(t *testing.T) {
	first, firstHash, err := NormalizeAndDigestOptions(Options{
		TitleColumn: " Title ",
		URLColumn:   "URL",
	})
	if err != nil {
		t.Fatal(err)
	}
	second, secondHash, err := NormalizeAndDigestOptions(Options{
		TitleColumn: "title",
		URLColumn:   "url",
		Delimiter:   ',',
		DateLocation: time.UTC,
	})
	if err != nil {
		t.Fatal(err)
	}
	if firstHash != secondHash {
		t.Fatalf("equivalent options produced different hashes: %s %s", firstHash, secondHash)
	}
	if first.TitleColumn != "title" || first.URLColumn != "url" || first.DateLocation != time.UTC {
		t.Fatalf("options were not canonicalized: %#v", first)
	}
	if first.MaxRows != DefaultMaxRows || second.MaxInputBytes != DefaultMaxInputBytes {
		t.Fatalf("approved defaults missing: first=%#v second=%#v", first, second)
	}
}

func TestNormalizeAndDigestOptionsBindsMappingChanges(t *testing.T) {
	_, firstHash, err := NormalizeAndDigestOptions(Options{TitleColumn: "title", TextColumn: "note"})
	if err != nil {
		t.Fatal(err)
	}
	_, secondHash, err := NormalizeAndDigestOptions(Options{TitleColumn: "title", TextColumn: "description"})
	if err != nil {
		t.Fatal(err)
	}
	if firstHash == secondHash {
		t.Fatal("material mapping changes must change options digest")
	}
}

func TestNormalizeAndDigestOptionsUsesCanonicalAsiaTokyoRules(t *testing.T) {
	spoofed := time.FixedZone("Asia/Tokyo", 60*60)
	normalized, digest, err := NormalizeAndDigestOptions(Options{
		TitleColumn:  "title",
		DateColumn:   "date",
		DateLayout:   "2006-01-02 15:04",
		DateLocation: spoofed,
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(digest) != 64 || normalized.DateLocation.String() != "Asia/Tokyo" {
		t.Fatalf("unexpected canonical location result: %#v %q", normalized.DateLocation, digest)
	}
	_, offset := time.Date(2026, 7, 1, 0, 0, 0, 0, normalized.DateLocation).Zone()
	if offset != 9*60*60 {
		t.Fatalf("spoofed location rules were not replaced: offset=%d", offset)
	}
}

func TestNormalizeAndDigestOptionsRejectsUnapprovedLocation(t *testing.T) {
	_, _, err := NormalizeAndDigestOptions(Options{
		TitleColumn:  "title",
		DateColumn:   "date",
		DateLayout:   "2006-01-02",
		DateLocation: time.FixedZone("Untrusted/Zone", 1234),
	})
	if !errors.Is(err, ErrUnsupportedDateLocation) {
		t.Fatalf("expected date-location rejection, got %v", err)
	}
}
