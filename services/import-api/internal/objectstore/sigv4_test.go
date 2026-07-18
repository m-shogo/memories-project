package objectstore

import (
	"net/url"
	"strings"
	"testing"
	"time"
)

// TestPresignMatchesAWSDocumentedVector reproduces the presigned-GET example
// from the AWS Signature Version 4 documentation ("Authenticating Requests:
// Using Query Parameters"), which pins the exact canonicalization, key
// derivation and signature for known credentials and a fixed clock.
func TestPresignMatchesAWSDocumentedVector(t *testing.T) {
	endpoint, err := url.Parse("https://examplebucket.s3.amazonaws.com")
	if err != nil {
		t.Fatal(err)
	}
	signedAt := time.Date(2013, 5, 24, 0, 0, 0, 0, time.UTC)
	presigned := presignURL(
		"GET",
		endpoint,
		"/test.txt",
		"us-east-1",
		credentials{accessKeyID: "AKIAIOSFODNN7EXAMPLE", secretAccessKey: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"},
		nil,
		signedAt,
		86400*time.Second,
	)
	parsed, err := url.Parse(presigned)
	if err != nil {
		t.Fatal(err)
	}
	query := parsed.Query()
	if query.Get("X-Amz-SignedHeaders") != "host" || query.Get("X-Amz-Expires") != "86400" {
		t.Fatalf("unexpected presign parameters: %s", presigned)
	}
	const expected = "aeeed9bbccd4d02ee5c0109b86d86835f995330da4c265957d157751f604d404"
	if signature := query.Get("X-Amz-Signature"); signature != expected {
		t.Fatalf("signature mismatch:\n got %s\nwant %s", signature, expected)
	}
}

func TestAWSURIEncoding(t *testing.T) {
	if encoded := awsURIEncode("quarantine/job_1:a/upl-2", false); encoded != "quarantine/job_1%3Aa/upl-2" {
		t.Fatalf("path encoding mismatch: %s", encoded)
	}
	if encoded := awsURIEncode("a/b c+d", true); encoded != "a%2Fb%20c%2Bd" {
		t.Fatalf("query encoding mismatch: %s", encoded)
	}
	if path := canonicalURIPath("/bucket/quarantine/job:1/u"); !strings.Contains(path, "job%3A1") {
		t.Fatalf("canonical path mismatch: %s", path)
	}
}
