package objectstore

import (
	"context"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/upload"
)

const (
	// MaxPresignTTL caps how long a quarantine upload URL can stay valid. The
	// upload service issues 5–10 minute authorizations; anything longer is a
	// configuration error.
	MaxPresignTTL = 15 * time.Minute
)

var (
	ErrInvalidStoreConfig      = errors.New("invalid object store configuration")
	ErrInvalidPresignInput     = errors.New("invalid presign input")
	ErrInvalidObjectKey        = errors.New("invalid quarantine object key")
	ErrInvalidObjectVersion    = errors.New("invalid quarantine object version ID")
	ErrObjectNotFound          = errors.New("quarantine object not found")
	ErrObjectIntegrityMismatch = errors.New("quarantine object content does not match its binding")
	ErrUnexpectedStoreReply    = errors.New("unexpected object store reply")
)

var objectKeyPattern = regexp.MustCompile(`^quarantine/[A-Za-z0-9._:-]+/[A-Za-z0-9._:-]+$`)
var bucketPattern = regexp.MustCompile(`^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$`)
var versionIDPattern = regexp.MustCompile(`^[A-Za-z0-9._~:+/=-]{1,256}$`)

// validObjectKey requires the exact quarantine shape and rejects dot segments,
// which the character class alone would admit and URL normalization could
// otherwise fold into a different path.
func validObjectKey(objectKey string) bool {
	if !objectKeyPattern.MatchString(objectKey) {
		return false
	}
	for _, segment := range strings.Split(objectKey, "/") {
		if segment == "." || segment == ".." {
			return false
		}
	}
	return true
}

// Config binds one private versioned quarantine bucket. Endpoint must be the
// bare scheme://host[:port] of an S3-compatible service; requests use
// path-style addressing. Production deployments must use https; http is
// tolerated so tests can run against a local container.
type Config struct {
	Endpoint        string
	Region          string
	Bucket          string
	AccessKeyID     string
	SecretAccessKey string
	HTTPClient      *http.Client
	Now             func() time.Time
}

// Client implements upload.Signer and upload.ObjectStore against an
// S3-compatible endpoint with AWS Signature V4 and no SDK dependency.
type Client struct {
	endpoint *url.URL
	region   string
	bucket   string
	creds    credentials
	http     *http.Client
	now      func() time.Time
}

func New(config Config) (*Client, error) {
	endpoint, err := url.Parse(config.Endpoint)
	if err != nil || endpoint.Host == "" || (endpoint.Scheme != "https" && endpoint.Scheme != "http") ||
		endpoint.Path != "" || endpoint.RawQuery != "" || endpoint.Fragment != "" {
		return nil, fmt.Errorf("%w: endpoint", ErrInvalidStoreConfig)
	}
	if config.Region == "" || !bucketPattern.MatchString(config.Bucket) || strings.Contains(config.Bucket, "..") {
		return nil, fmt.Errorf("%w: region or bucket", ErrInvalidStoreConfig)
	}
	if config.AccessKeyID == "" || config.SecretAccessKey == "" {
		return nil, fmt.Errorf("%w: credentials", ErrInvalidStoreConfig)
	}
	client := config.HTTPClient
	if client == nil {
		client = &http.Client{Timeout: 30 * time.Second}
	}
	now := config.Now
	if now == nil {
		now = time.Now
	}
	return &Client{
		endpoint: endpoint,
		region:   config.Region,
		bucket:   config.Bucket,
		creds:    credentials{accessKeyID: config.AccessKeyID, secretAccessKey: config.SecretAccessKey},
		http:     client,
		now:      now,
	}, nil
}

// PresignPut returns one PUT URL whose signature covers the exact
// content-length, content-type and full-object SHA-256 checksum headers, so
// the storage service itself rejects any upload that changes any of them.
func (c *Client) PresignPut(_ context.Context, request upload.PresignRequest) (upload.PresignResult, error) {
	if c == nil {
		return upload.PresignResult{}, ErrInvalidStoreConfig
	}
	if !validObjectKey(request.ObjectKey) {
		return upload.PresignResult{}, ErrInvalidObjectKey
	}
	if request.ContentLength <= 0 || request.ContentLength > upload.MaxUploadBytes || request.ContentType == "" {
		return upload.PresignResult{}, ErrInvalidPresignInput
	}
	checksum, err := hex.DecodeString(request.ChecksumSHA256)
	if err != nil || len(checksum) != sha256.Size {
		return upload.PresignResult{}, ErrInvalidPresignInput
	}
	now := c.now().UTC()
	ttl := request.ExpiresAt.Sub(now)
	if request.ExpiresAt.IsZero() || ttl <= 0 || ttl > MaxPresignTTL {
		return upload.PresignResult{}, fmt.Errorf("%w: expiry", ErrInvalidPresignInput)
	}

	requiredHeaders := map[string]string{
		"Content-Type":          request.ContentType,
		"Content-Length":        strconv.FormatInt(request.ContentLength, 10),
		"x-amz-checksum-sha256": base64.StdEncoding.EncodeToString(checksum),
	}
	signed := presignURL(
		http.MethodPut,
		c.endpoint,
		"/"+c.bucket+"/"+request.ObjectKey,
		c.region,
		c.creds,
		requiredHeaders,
		now,
		ttl,
	)
	return upload.PresignResult{URL: signed, RequiredHeaders: requiredHeaders}, nil
}

// HeadObject verifies real server-side object state: it returns the exact
// version ID, ETag, length, content type and (when the object was uploaded
// with the bound checksum header) the full-object SHA-256 as lowercase hex.
func (c *Client) HeadObject(ctx context.Context, objectKey string) (upload.ObjectMetadata, error) {
	if c == nil {
		return upload.ObjectMetadata{}, ErrInvalidStoreConfig
	}
	if !validObjectKey(objectKey) {
		return upload.ObjectMetadata{}, ErrInvalidObjectKey
	}
	response, err := c.do(ctx, http.MethodHead, "/"+c.bucket+"/"+objectKey, "",
		map[string]string{"x-amz-checksum-mode": "ENABLED"}, nil, emptyPayloadSHA256)
	if err != nil {
		return upload.ObjectMetadata{}, err
	}
	defer drainAndClose(response)
	switch response.StatusCode {
	case http.StatusOK:
	case http.StatusNotFound:
		return upload.ObjectMetadata{}, ErrObjectNotFound
	default:
		return upload.ObjectMetadata{}, fmt.Errorf("%w: HEAD status %d", ErrUnexpectedStoreReply, response.StatusCode)
	}

	length, err := strconv.ParseInt(response.Header.Get("Content-Length"), 10, 64)
	if err != nil || length < 0 {
		return upload.ObjectMetadata{}, fmt.Errorf("%w: content length", ErrUnexpectedStoreReply)
	}
	checksumHex := ""
	if encoded := response.Header.Get("x-amz-checksum-sha256"); encoded != "" {
		decoded, err := base64.StdEncoding.DecodeString(encoded)
		if err != nil || len(decoded) != sha256.Size {
			return upload.ObjectMetadata{}, fmt.Errorf("%w: checksum header", ErrUnexpectedStoreReply)
		}
		checksumHex = hex.EncodeToString(decoded)
	}
	return upload.ObjectMetadata{
		ObjectKey:      objectKey,
		VersionID:      response.Header.Get("x-amz-version-id"),
		ETag:           strings.Trim(response.Header.Get("ETag"), `"`),
		ContentLength:  length,
		ChecksumSHA256: checksumHex,
		ContentType:    response.Header.Get("Content-Type"),
	}, nil
}

// GetObjectVersion downloads exactly one immutable object version into
// destination, verifying the bound content length and full-object SHA-256
// while streaming. Any divergence — wrong length, wrong hash, growth beyond
// the bound — is ErrObjectIntegrityMismatch and the caller must discard the
// destination.
func (c *Client) GetObjectVersion(ctx context.Context, objectKey string, versionID string, expectedLength int64, expectedSHA256 string, destination io.Writer) error {
	if c == nil || destination == nil {
		return ErrInvalidStoreConfig
	}
	if !validObjectKey(objectKey) {
		return ErrInvalidObjectKey
	}
	if !versionIDPattern.MatchString(versionID) {
		return ErrInvalidObjectVersion
	}
	expected, err := hex.DecodeString(expectedSHA256)
	if err != nil || len(expected) != sha256.Size || expectedLength < 1 || expectedLength > upload.MaxUploadBytes {
		return fmt.Errorf("%w: content binding", ErrInvalidObjectVersion)
	}
	response, err := c.do(ctx, http.MethodGet, "/"+c.bucket+"/"+objectKey,
		"versionId="+url.QueryEscape(versionID), nil, nil, emptyPayloadSHA256)
	if err != nil {
		return err
	}
	defer drainAndClose(response)
	switch response.StatusCode {
	case http.StatusOK:
	case http.StatusNotFound:
		return ErrObjectNotFound
	default:
		return fmt.Errorf("%w: GET status %d", ErrUnexpectedStoreReply, response.StatusCode)
	}

	hasher := sha256.New()
	copied, err := io.Copy(io.MultiWriter(destination, hasher), io.LimitReader(response.Body, expectedLength))
	if err != nil {
		return fmt.Errorf("stream quarantine object: %w", err)
	}
	if n, err := io.CopyN(io.Discard, response.Body, 1); n != 0 || !errors.Is(err, io.EOF) {
		return fmt.Errorf("%w: content exceeds bound length", ErrObjectIntegrityMismatch)
	}
	if copied != expectedLength || hex.EncodeToString(hasher.Sum(nil)) != expectedSHA256 {
		return fmt.Errorf("%w: length or checksum", ErrObjectIntegrityMismatch)
	}
	return nil
}

// ProvisionVersionedBucket creates the private quarantine bucket if missing
// and enables versioning. It exists for deployment provisioning and test
// containers; runtime request paths never call it.
func (c *Client) ProvisionVersionedBucket(ctx context.Context) error {
	if c == nil {
		return ErrInvalidStoreConfig
	}
	response, err := c.do(ctx, http.MethodPut, "/"+c.bucket, "", nil, nil, emptyPayloadSHA256)
	if err != nil {
		return err
	}
	drainAndClose(response)
	if response.StatusCode != http.StatusOK && response.StatusCode != http.StatusConflict {
		return fmt.Errorf("%w: create bucket status %d", ErrUnexpectedStoreReply, response.StatusCode)
	}

	versioning := []byte(`<VersioningConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><Status>Enabled</Status></VersioningConfiguration>`)
	digest := sha256.Sum256(versioning)
	response, err = c.do(ctx, http.MethodPut, "/"+c.bucket, "versioning=",
		map[string]string{"content-length": strconv.Itoa(len(versioning))},
		versioning, hex.EncodeToString(digest[:]))
	if err != nil {
		return err
	}
	drainAndClose(response)
	if response.StatusCode != http.StatusOK {
		return fmt.Errorf("%w: enable versioning status %d", ErrUnexpectedStoreReply, response.StatusCode)
	}
	return nil
}

// do sends one Signature V4 header-signed request. It exists for HEAD/GET and
// for provisioning; it never streams user payloads outward.
func (c *Client) do(ctx context.Context, method string, path string, rawQuery string, extraHeaders map[string]string, body []byte, payloadSHA256 string) (*http.Response, error) {
	if ctx == nil {
		return nil, ErrInvalidStoreConfig
	}
	headers, authorization := signAuthorizationHeader(method, c.endpoint, path, rawQuery, c.region, c.creds, extraHeaders, payloadSHA256, c.now())
	target := *c.endpoint
	target.Path = path
	target.RawPath = canonicalURIPath(path)
	target.RawQuery = rawQuery
	request, err := http.NewRequestWithContext(ctx, method, target.String(), strings.NewReader(string(body)))
	if err != nil {
		return nil, err
	}
	for name, value := range headers {
		request.Header.Set(name, value)
	}
	request.Header.Set("Authorization", authorization)
	response, err := c.http.Do(request)
	if err != nil {
		return nil, fmt.Errorf("object store request: %w", err)
	}
	return response, nil
}

func drainAndClose(response *http.Response) {
	_, _ = io.Copy(io.Discard, io.LimitReader(response.Body, 1<<20))
	_ = response.Body.Close()
}
