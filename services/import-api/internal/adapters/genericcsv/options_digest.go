package genericcsv

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"errors"
	"fmt"
	"hash"
	"time"
)

var ErrUnsupportedDateLocation = errors.New("unsupported CSV date location")

// NormalizeAndDigestOptions returns the exact options used by the parser and a
// deterministic digest suitable for Preview binding. P0 intentionally limits
// date interpretation to UTC and Asia/Tokyo.
func NormalizeAndDigestOptions(options Options) (Options, string, error) {
	config, err := normalizeOptions(options)
	if err != nil {
		return Options{}, "", err
	}
	locationID, location, err := approvedDateLocation(config.DateLocation)
	if err != nil {
		return Options{}, "", err
	}
	normalized := config.Options
	normalized.TitleColumn = normalizeHeader(normalized.TitleColumn)
	normalized.DateColumn = normalizeHeader(normalized.DateColumn)
	normalized.URLColumn = normalizeHeader(normalized.URLColumn)
	normalized.TextColumn = normalizeHeader(normalized.TextColumn)
	normalized.DateLocation = location

	hasher := sha256.New()
	for _, value := range []string{
		"memory-os-generic-csv-options-v1",
		fmt.Sprintf("%d", normalized.Delimiter),
		normalized.TitleColumn,
		normalized.DateColumn,
		normalized.DateLayout,
		locationID,
		normalized.URLColumn,
		normalized.TextColumn,
		fmt.Sprintf("%d", normalized.MaxInputBytes),
		fmt.Sprintf("%d", normalized.MaxRows),
		fmt.Sprintf("%d", normalized.MaxColumns),
		fmt.Sprintf("%d", normalized.MaxCellBytes),
	} {
		writeDigestField(hasher, []byte(value))
	}
	return normalized, hex.EncodeToString(hasher.Sum(nil)), nil
}

func approvedDateLocation(location *time.Location) (string, *time.Location, error) {
	if location == nil || location.String() == "UTC" {
		return "UTC", time.UTC, nil
	}
	if location.String() != "Asia/Tokyo" {
		return "", nil, ErrUnsupportedDateLocation
	}
	canonical, err := time.LoadLocation("Asia/Tokyo")
	if err != nil {
		return "", nil, fmt.Errorf("load canonical Asia/Tokyo location: %w", err)
	}
	return "Asia/Tokyo", canonical, nil
}

func writeDigestField(target hash.Hash, value []byte) {
	var size [8]byte
	binary.BigEndian.PutUint64(size[:], uint64(len(value)))
	_, _ = target.Write(size[:])
	_, _ = target.Write(value)
}
