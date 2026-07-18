package objectstore

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"net/url"
	"sort"
	"strconv"
	"strings"
	"time"
)

const (
	signingAlgorithm = "AWS4-HMAC-SHA256"
	serviceS3        = "s3"
	unsignedPayload  = "UNSIGNED-PAYLOAD"
	// emptyPayloadSHA256 is SHA-256 of zero bytes, used for bodyless signed
	// requests such as HEAD.
	emptyPayloadSHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
)

type credentials struct {
	accessKeyID     string
	secretAccessKey string
}

// presignURL builds an AWS Signature V4 presigned URL. Every header in
// signedHeaders becomes part of the signature, so the storage service rejects
// any request that omits or alters those exact header values.
func presignURL(method string, endpoint *url.URL, path string, region string, creds credentials, signedHeaders map[string]string, signedAt time.Time, expires time.Duration) string {
	signedAt = signedAt.UTC()
	amzDate := signedAt.Format("20060102T150405Z")
	scopeDate := signedAt.Format("20060102")
	scope := scopeDate + "/" + region + "/" + serviceS3 + "/aws4_request"

	headers := map[string]string{"host": endpoint.Host}
	for name, value := range signedHeaders {
		headers[strings.ToLower(name)] = value
	}
	headerNames := make([]string, 0, len(headers))
	for name := range headers {
		headerNames = append(headerNames, name)
	}
	sort.Strings(headerNames)
	signedHeaderList := strings.Join(headerNames, ";")

	query := url.Values{}
	query.Set("X-Amz-Algorithm", signingAlgorithm)
	query.Set("X-Amz-Credential", creds.accessKeyID+"/"+scope)
	query.Set("X-Amz-Date", amzDate)
	query.Set("X-Amz-Expires", strconv.FormatInt(int64(expires/time.Second), 10))
	query.Set("X-Amz-SignedHeaders", signedHeaderList)
	canonicalQuery := canonicalQueryString(query)

	var canonicalHeaders strings.Builder
	for _, name := range headerNames {
		canonicalHeaders.WriteString(name)
		canonicalHeaders.WriteString(":")
		canonicalHeaders.WriteString(strings.TrimSpace(headers[name]))
		canonicalHeaders.WriteString("\n")
	}

	canonicalRequest := strings.Join([]string{
		method,
		canonicalURIPath(path),
		canonicalQuery,
		canonicalHeaders.String(),
		signedHeaderList,
		unsignedPayload,
	}, "\n")

	signature := signStringToSign(stringToSign(amzDate, scope, canonicalRequest), creds, scopeDate, region)
	final := *endpoint
	final.Path = path
	final.RawPath = canonicalURIPath(path)
	final.RawQuery = canonicalQuery + "&X-Amz-Signature=" + signature
	return final.String()
}

// signAuthorizationHeader signs a bodyless-or-known-payload request with a
// normal Authorization header (used for HEAD and test-only bucket setup).
func signAuthorizationHeader(method string, endpoint *url.URL, path string, rawQuery string, region string, creds credentials, extraHeaders map[string]string, payloadSHA256 string, signedAt time.Time) (map[string]string, string) {
	signedAt = signedAt.UTC()
	amzDate := signedAt.Format("20060102T150405Z")
	scopeDate := signedAt.Format("20060102")
	scope := scopeDate + "/" + region + "/" + serviceS3 + "/aws4_request"

	headers := map[string]string{
		"host":                 endpoint.Host,
		"x-amz-content-sha256": payloadSHA256,
		"x-amz-date":           amzDate,
	}
	for name, value := range extraHeaders {
		headers[strings.ToLower(name)] = value
	}
	headerNames := make([]string, 0, len(headers))
	for name := range headers {
		headerNames = append(headerNames, name)
	}
	sort.Strings(headerNames)
	signedHeaderList := strings.Join(headerNames, ";")

	parsedQuery, _ := url.ParseQuery(rawQuery)
	canonicalQuery := canonicalQueryString(parsedQuery)

	var canonicalHeaders strings.Builder
	for _, name := range headerNames {
		canonicalHeaders.WriteString(name)
		canonicalHeaders.WriteString(":")
		canonicalHeaders.WriteString(strings.TrimSpace(headers[name]))
		canonicalHeaders.WriteString("\n")
	}

	canonicalRequest := strings.Join([]string{
		method,
		canonicalURIPath(path),
		canonicalQuery,
		canonicalHeaders.String(),
		signedHeaderList,
		payloadSHA256,
	}, "\n")

	signature := signStringToSign(stringToSign(amzDate, scope, canonicalRequest), creds, scopeDate, region)
	authorization := signingAlgorithm +
		" Credential=" + creds.accessKeyID + "/" + scope +
		", SignedHeaders=" + signedHeaderList +
		", Signature=" + signature
	sendHeaders := make(map[string]string, len(headers))
	for name, value := range headers {
		if name == "host" {
			continue
		}
		sendHeaders[name] = value
	}
	return sendHeaders, authorization
}

func stringToSign(amzDate string, scope string, canonicalRequest string) string {
	digest := sha256.Sum256([]byte(canonicalRequest))
	return strings.Join([]string{
		signingAlgorithm,
		amzDate,
		scope,
		hex.EncodeToString(digest[:]),
	}, "\n")
}

func signStringToSign(payload string, creds credentials, scopeDate string, region string) string {
	dateKey := hmacSHA256([]byte("AWS4"+creds.secretAccessKey), scopeDate)
	regionKey := hmacSHA256(dateKey, region)
	serviceKey := hmacSHA256(regionKey, serviceS3)
	signingKey := hmacSHA256(serviceKey, "aws4_request")
	return hex.EncodeToString(hmacSHA256(signingKey, payload))
}

func hmacSHA256(key []byte, value string) []byte {
	mac := hmac.New(sha256.New, key)
	mac.Write([]byte(value))
	return mac.Sum(nil)
}

// canonicalQueryString applies exact AWS URI encoding to every key and value
// and sorts by encoded key.
func canonicalQueryString(query url.Values) string {
	type pair struct{ key, value string }
	pairs := make([]pair, 0, len(query))
	for key, values := range query {
		for _, value := range values {
			pairs = append(pairs, pair{awsURIEncode(key, true), awsURIEncode(value, true)})
		}
	}
	sort.Slice(pairs, func(i, j int) bool {
		if pairs[i].key != pairs[j].key {
			return pairs[i].key < pairs[j].key
		}
		return pairs[i].value < pairs[j].value
	})
	parts := make([]string, len(pairs))
	for i, entry := range pairs {
		parts[i] = entry.key + "=" + entry.value
	}
	return strings.Join(parts, "&")
}

func canonicalURIPath(path string) string {
	if path == "" {
		return "/"
	}
	segments := strings.Split(path, "/")
	for i, segment := range segments {
		segments[i] = awsURIEncode(segment, false)
	}
	return strings.Join(segments, "/")
}

// awsURIEncode implements the AWS SigV4 encoding rules: unreserved characters
// stay literal, everything else becomes uppercase percent escapes, and '/' is
// escaped only inside query components.
func awsURIEncode(value string, encodeSlash bool) string {
	var out strings.Builder
	for _, b := range []byte(value) {
		switch {
		case b >= 'A' && b <= 'Z', b >= 'a' && b <= 'z', b >= '0' && b <= '9', b == '-', b == '.', b == '_', b == '~':
			out.WriteByte(b)
		case b == '/' && !encodeSlash:
			out.WriteByte(b)
		default:
			out.WriteString("%")
			out.WriteString(strings.ToUpper(hex.EncodeToString([]byte{b})))
		}
	}
	return out.String()
}
