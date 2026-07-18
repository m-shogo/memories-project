package objectstore

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/upload"
)

const liveBucket = "memory-os-quarantine-test"

func liveClient(t *testing.T, now func() time.Time) *Client {
	t.Helper()
	endpoint := os.Getenv("MEMORY_OS_TEST_S3_ENDPOINT")
	if endpoint == "" {
		t.Skip("MEMORY_OS_TEST_S3_ENDPOINT is not set; skipping live object store tests")
	}
	access := os.Getenv("MEMORY_OS_TEST_S3_ACCESS_KEY")
	if access == "" {
		access = "minioadmin"
	}
	secret := os.Getenv("MEMORY_OS_TEST_S3_SECRET_KEY")
	if secret == "" {
		secret = "minioadmin"
	}
	build := func(clock func() time.Time) *Client {
		client, err := New(Config{
			Endpoint:        endpoint,
			Region:          "us-east-1",
			Bucket:          liveBucket,
			AccessKeyID:     access,
			SecretAccessKey: secret,
			Now:             clock,
		})
		if err != nil {
			t.Fatal(err)
		}
		return client
	}
	// Provisioning always signs with the real clock; a test-injected clock
	// only affects the presign requests under test.
	provisionVersionedBucket(t, build(time.Now))
	return build(now)
}

// provisionVersionedBucket creates the private test bucket and enables
// versioning, retrying while the container starts up.
func provisionVersionedBucket(t *testing.T, client *Client) {
	t.Helper()
	ctx := context.Background()
	deadline := time.Now().Add(30 * time.Second)
	for {
		response, err := client.do(ctx, http.MethodPut, "/"+client.bucket, "", nil, nil, emptyPayloadSHA256)
		if err == nil {
			drainAndClose(response)
			if response.StatusCode == http.StatusOK || response.StatusCode == http.StatusConflict {
				break
			}
			err = fmt.Errorf("create bucket status %d", response.StatusCode)
		}
		if time.Now().After(deadline) {
			t.Fatalf("object store never became ready: %v", err)
		}
		time.Sleep(time.Second)
	}

	versioning := []byte(`<VersioningConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><Status>Enabled</Status></VersioningConfiguration>`)
	digest := sha256.Sum256(versioning)
	response, err := client.do(ctx, http.MethodPut, "/"+client.bucket, "versioning=",
		map[string]string{"content-length": fmt.Sprintf("%d", len(versioning))},
		versioning, hex.EncodeToString(digest[:]))
	if err != nil {
		t.Fatal(err)
	}
	drainAndClose(response)
	if response.StatusCode != http.StatusOK {
		t.Fatalf("enable versioning status %d", response.StatusCode)
	}
}

func uploadWithHeaders(t *testing.T, target string, headers map[string]string, payload []byte) *http.Response {
	t.Helper()
	request, err := http.NewRequest(http.MethodPut, target, bytes.NewReader(payload))
	if err != nil {
		t.Fatal(err)
	}
	request.ContentLength = int64(len(payload))
	for name, value := range headers {
		if name == "Content-Length" {
			continue
		}
		request.Header.Set(name, value)
	}
	response, err := http.DefaultClient.Do(request)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { drainAndClose(response) })
	return response
}

func livePresign(t *testing.T, client *Client, key string, payload []byte, ttl time.Duration) (upload.PresignResult, string) {
	t.Helper()
	digest := sha256.Sum256(payload)
	checksum := hex.EncodeToString(digest[:])
	result, err := client.PresignPut(context.Background(), upload.PresignRequest{
		ObjectKey:      key,
		ContentLength:  int64(len(payload)),
		ChecksumSHA256: checksum,
		ContentType:    "text/csv",
		ExpiresAt:      client.now().Add(ttl),
	})
	if err != nil {
		t.Fatal(err)
	}
	return result, checksum
}

func TestLivePresignedUploadRoundTripWithVersioning(t *testing.T) {
	client := liveClient(t, time.Now)
	payload := []byte("source-row-1,source-row-2\n")
	key := "quarantine/job-live-roundtrip/upl-1"

	presigned, checksum := livePresign(t, client, key, payload, 5*time.Minute)
	response := uploadWithHeaders(t, presigned.URL, presigned.RequiredHeaders, payload)
	if response.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(io.LimitReader(response.Body, 2048))
		t.Fatalf("presigned upload status %d: %s", response.StatusCode, body)
	}

	metadata, err := client.HeadObject(context.Background(), key)
	if err != nil {
		t.Fatal(err)
	}
	if metadata.VersionID == "" || metadata.ContentLength != int64(len(payload)) ||
		metadata.ChecksumSHA256 != checksum || metadata.ContentType != "text/csv" {
		t.Fatalf("metadata does not reflect the bound upload: %+v", metadata)
	}

	again, _ := livePresign(t, client, key, payload, 5*time.Minute)
	response = uploadWithHeaders(t, again.URL, again.RequiredHeaders, payload)
	if response.StatusCode != http.StatusOK {
		t.Fatalf("second presigned upload status %d", response.StatusCode)
	}
	updated, err := client.HeadObject(context.Background(), key)
	if err != nil {
		t.Fatal(err)
	}
	if updated.VersionID == "" || updated.VersionID == metadata.VersionID {
		t.Fatalf("bucket versioning is not binding object versions: %q then %q", metadata.VersionID, updated.VersionID)
	}
}

func TestLivePresignedUploadRejectsTampering(t *testing.T) {
	client := liveClient(t, time.Now)
	payload := []byte("bound-content\n")
	key := "quarantine/job-live-tamper/upl-1"
	presigned, _ := livePresign(t, client, key, payload, 5*time.Minute)

	tamperedChecksum := map[string]string{}
	for name, value := range presigned.RequiredHeaders {
		tamperedChecksum[name] = value
	}
	other := sha256.Sum256([]byte("other-content"))
	tamperedChecksum["x-amz-checksum-sha256"] = hexToBase64(t, hex.EncodeToString(other[:]))
	if response := uploadWithHeaders(t, presigned.URL, tamperedChecksum, payload); response.StatusCode == http.StatusOK {
		t.Fatal("upload with tampered checksum header was accepted")
	}

	missingType := map[string]string{"x-amz-checksum-sha256": presigned.RequiredHeaders["x-amz-checksum-sha256"]}
	if response := uploadWithHeaders(t, presigned.URL, missingType, payload); response.StatusCode == http.StatusOK {
		t.Fatal("upload without the bound content type was accepted")
	}

	if response := uploadWithHeaders(t, presigned.URL, presigned.RequiredHeaders, []byte("other-content")); response.StatusCode == http.StatusOK {
		t.Fatal("upload with substituted content was accepted")
	}

	if _, err := client.HeadObject(context.Background(), key); !errors.Is(err, ErrObjectNotFound) {
		t.Fatalf("tampered uploads left an object behind: %v", err)
	}
}

func TestLivePresignExpiryIsEnforced(t *testing.T) {
	past := time.Now().Add(-time.Hour)
	client := liveClient(t, func() time.Time { return past })
	payload := []byte("expired\n")
	presigned, _ := livePresign(t, client, "quarantine/job-live-expired/upl-1", payload, 5*time.Minute)
	if response := uploadWithHeaders(t, presigned.URL, presigned.RequiredHeaders, payload); response.StatusCode == http.StatusOK {
		t.Fatal("expired presigned URL was accepted")
	}
}

func TestLiveHeadMissingObject(t *testing.T) {
	client := liveClient(t, time.Now)
	if _, err := client.HeadObject(context.Background(), "quarantine/job-live-missing/upl-none"); !errors.Is(err, ErrObjectNotFound) {
		t.Fatalf("missing object did not report not-found: %v", err)
	}
}

func hexToBase64(t *testing.T, value string) string {
	t.Helper()
	decoded, err := hex.DecodeString(value)
	if err != nil {
		t.Fatal(err)
	}
	return base64.StdEncoding.EncodeToString(decoded)
}
