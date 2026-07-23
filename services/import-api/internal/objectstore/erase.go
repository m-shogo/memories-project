package objectstore

import (
	"context"
	"encoding/xml"
	"fmt"
	"io"
	"net/http"
	"net/url"
)

// maxObjectVersionsPerKey bounds how many versions one key may accumulate
// before erasure gives up rather than looping. A presigned PUT is single-use
// and consumed on completion, so a key normally holds one version; a client
// that raced the same URL could add a few more. A number far beyond that means
// something is wrong, and silently iterating forever would be worse than
// failing loudly.
const maxObjectVersionsPerKey = 1000

// ObjectVersion identifies one immutable version of one key, including delete
// markers — erasure must remove those too, or the key's history survives.
type ObjectVersion struct {
	Key       string
	VersionID string
}

type listVersionsResult struct {
	XMLName             xml.Name `xml:"ListVersionsResult"`
	IsTruncated         bool     `xml:"IsTruncated"`
	NextKeyMarker       string   `xml:"NextKeyMarker"`
	NextVersionIDMarker string   `xml:"NextVersionIdMarker"`
	Versions            []struct {
		Key       string `xml:"Key"`
		VersionID string `xml:"VersionId"`
	} `xml:"Version"`
	DeleteMarkers []struct {
		Key       string `xml:"Key"`
		VersionID string `xml:"VersionId"`
	} `xml:"DeleteMarker"`
}

// ListObjectVersions returns every version and delete marker stored under one
// exact quarantine key. It takes a full key rather than a free prefix on
// purpose: quarantine keys are not account-scoped, so a prefix listing could
// return another tenant's objects. The caller supplies keys it has already
// read from that account's own RLS-scoped rows.
func (c *Client) ListObjectVersions(ctx context.Context, objectKey string) ([]ObjectVersion, error) {
	if c == nil {
		return nil, ErrInvalidStoreConfig
	}
	if !validObjectKey(objectKey) {
		return nil, ErrInvalidObjectKey
	}

	var versions []ObjectVersion
	keyMarker, versionMarker := "", ""
	for {
		query := "versions=&prefix=" + url.QueryEscape(objectKey)
		if keyMarker != "" {
			query += "&key-marker=" + url.QueryEscape(keyMarker)
		}
		if versionMarker != "" {
			query += "&version-id-marker=" + url.QueryEscape(versionMarker)
		}
		response, err := c.do(ctx, http.MethodGet, "/"+c.bucket, query, nil, nil, emptyPayloadSHA256)
		if err != nil {
			return nil, err
		}
		if response.StatusCode != http.StatusOK {
			drainAndClose(response)
			return nil, fmt.Errorf("%w: list versions status %d", ErrUnexpectedStoreReply, response.StatusCode)
		}
		payload, err := io.ReadAll(io.LimitReader(response.Body, 1<<20))
		drainAndClose(response)
		if err != nil {
			return nil, fmt.Errorf("read version listing: %w", err)
		}
		var listed listVersionsResult
		if err := xml.Unmarshal(payload, &listed); err != nil {
			return nil, fmt.Errorf("%w: version listing is not valid XML", ErrUnexpectedStoreReply)
		}

		for _, entry := range listed.Versions {
			// A prefix listing can return neighbouring keys; keep only the
			// exact key the caller is entitled to erase.
			if entry.Key == objectKey && entry.VersionID != "" {
				versions = append(versions, ObjectVersion{Key: entry.Key, VersionID: entry.VersionID})
			}
		}
		for _, entry := range listed.DeleteMarkers {
			if entry.Key == objectKey && entry.VersionID != "" {
				versions = append(versions, ObjectVersion{Key: entry.Key, VersionID: entry.VersionID})
			}
		}
		if len(versions) > maxObjectVersionsPerKey {
			return nil, fmt.Errorf("%w: more than %d versions for one key",
				ErrUnexpectedStoreReply, maxObjectVersionsPerKey)
		}
		if !listed.IsTruncated || listed.NextKeyMarker == "" {
			return versions, nil
		}
		keyMarker, versionMarker = listed.NextKeyMarker, listed.NextVersionIDMarker
	}
}

// DeleteObjectVersion permanently removes one version. Deleting a specific
// version in a versioned bucket erases that version rather than adding a
// delete marker, which is what account erasure requires. It is idempotent: a
// version that is already gone is not an error, so a retried sweep converges.
func (c *Client) DeleteObjectVersion(ctx context.Context, objectKey string, versionID string) error {
	if c == nil {
		return ErrInvalidStoreConfig
	}
	if !validObjectKey(objectKey) {
		return ErrInvalidObjectKey
	}
	if !versionIDPattern.MatchString(versionID) {
		return ErrInvalidObjectVersion
	}
	response, err := c.do(ctx, http.MethodDelete, "/"+c.bucket+"/"+objectKey,
		"versionId="+url.QueryEscape(versionID), nil, nil, emptyPayloadSHA256)
	if err != nil {
		return err
	}
	drainAndClose(response)
	switch response.StatusCode {
	case http.StatusNoContent, http.StatusOK, http.StatusNotFound:
		return nil
	default:
		return fmt.Errorf("%w: DELETE status %d", ErrUnexpectedStoreReply, response.StatusCode)
	}
}

// EraseObject removes every version of one key. It reports how many versions
// it deleted so the caller's erasure receipt reflects what actually happened.
func (c *Client) EraseObject(ctx context.Context, objectKey string) (int, error) {
	versions, err := c.ListObjectVersions(ctx, objectKey)
	if err != nil {
		return 0, err
	}
	for index, version := range versions {
		if err := c.DeleteObjectVersion(ctx, version.Key, version.VersionID); err != nil {
			return index, err
		}
	}
	return len(versions), nil
}
