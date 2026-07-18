package objectstore

import (
	"context"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"errors"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/upload"
)

func testClient(t *testing.T) *Client {
	t.Helper()
	client, err := New(Config{
		Endpoint:        "https://quarantine.example:9000",
		Region:          "us-east-1",
		Bucket:          "memory-os-quarantine",
		AccessKeyID:     "test-access",
		SecretAccessKey: "test-secret",
		Now:             func() time.Time { return time.Date(2026, 7, 19, 2, 0, 0, 0, time.UTC) },
	})
	if err != nil {
		t.Fatal(err)
	}
	return client
}

func presignFixture() upload.PresignRequest {
	payload := []byte("quarantine-body")
	digest := sha256.Sum256(payload)
	return upload.PresignRequest{
		ObjectKey:      "quarantine/job_01J000000000000000000000000/upl_01J00000000000000000000000",
		ContentLength:  int64(len(payload)),
		ChecksumSHA256: hex.EncodeToString(digest[:]),
		ContentType:    "text/csv",
		ExpiresAt:      time.Date(2026, 7, 19, 2, 5, 0, 0, time.UTC),
	}
}

func TestPresignPutBindsExactRequiredHeaders(t *testing.T) {
	client := testClient(t)
	request := presignFixture()
	result, err := client.PresignPut(context.Background(), request)
	if err != nil {
		t.Fatal(err)
	}
	checksum, _ := hex.DecodeString(request.ChecksumSHA256)
	wantHeaders := map[string]string{
		"Content-Type":          request.ContentType,
		"Content-Length":        strconv.FormatInt(request.ContentLength, 10),
		"x-amz-checksum-sha256": base64.StdEncoding.EncodeToString(checksum),
	}
	if len(result.RequiredHeaders) != len(wantHeaders) {
		t.Fatalf("unexpected header set: %+v", result.RequiredHeaders)
	}
	for name, want := range wantHeaders {
		if result.RequiredHeaders[name] != want {
			t.Fatalf("header %s = %q, want %q", name, result.RequiredHeaders[name], want)
		}
	}
	if !strings.Contains(result.URL, "/memory-os-quarantine/quarantine/") ||
		!strings.Contains(result.URL, "X-Amz-SignedHeaders=content-length%3Bcontent-type%3Bhost%3Bx-amz-checksum-sha256") ||
		!strings.Contains(result.URL, "X-Amz-Expires=300") {
		t.Fatalf("presigned URL does not bind the upload: %s", result.URL)
	}
}

func TestPresignPutValidatesInput(t *testing.T) {
	client := testClient(t)
	cases := map[string]func(*upload.PresignRequest){
		"traversal-key":  func(r *upload.PresignRequest) { r.ObjectKey = "quarantine/../secrets" },
		"foreign-prefix": func(r *upload.PresignRequest) { r.ObjectKey = "public/job/upl" },
		"zero-length":    func(r *upload.PresignRequest) { r.ContentLength = 0 },
		"oversized":      func(r *upload.PresignRequest) { r.ContentLength = upload.MaxUploadBytes + 1 },
		"bad-checksum":   func(r *upload.PresignRequest) { r.ChecksumSHA256 = "zz" },
		"empty-type":     func(r *upload.PresignRequest) { r.ContentType = "" },
		"past-expiry":    func(r *upload.PresignRequest) { r.ExpiresAt = time.Date(2026, 7, 19, 1, 0, 0, 0, time.UTC) },
		"long-expiry":    func(r *upload.PresignRequest) { r.ExpiresAt = time.Date(2026, 7, 19, 3, 0, 0, 0, time.UTC) },
	}
	for name, mutate := range cases {
		request := presignFixture()
		mutate(&request)
		if _, err := client.PresignPut(context.Background(), request); err == nil {
			t.Fatalf("%s was accepted", name)
		}
	}
}

func TestNewValidatesConfiguration(t *testing.T) {
	base := Config{
		Endpoint:        "https://quarantine.example",
		Region:          "us-east-1",
		Bucket:          "memory-os-quarantine",
		AccessKeyID:     "a",
		SecretAccessKey: "s",
	}
	cases := map[string]func(*Config){
		"scheme":       func(c *Config) { c.Endpoint = "ftp://quarantine.example" },
		"path":         func(c *Config) { c.Endpoint = "https://quarantine.example/base" },
		"empty-region": func(c *Config) { c.Region = "" },
		"bad-bucket":   func(c *Config) { c.Bucket = "Bad_Bucket" },
		"no-secret":    func(c *Config) { c.SecretAccessKey = "" },
	}
	for name, mutate := range cases {
		config := base
		mutate(&config)
		if _, err := New(config); !errors.Is(err, ErrInvalidStoreConfig) {
			t.Fatalf("%s was accepted: %v", name, err)
		}
	}
	if _, err := New(base); err != nil {
		t.Fatalf("valid configuration rejected: %v", err)
	}
}

func TestHeadObjectValidatesKey(t *testing.T) {
	client := testClient(t)
	if _, err := client.HeadObject(context.Background(), "quarantine/../etc/passwd"); !errors.Is(err, ErrInvalidObjectKey) {
		t.Fatalf("traversal key was accepted: %v", err)
	}
}
