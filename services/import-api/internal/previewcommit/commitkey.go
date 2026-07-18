package previewcommit

import (
	"crypto/sha256"
	"encoding/hex"
	"strconv"
	"strings"

	"github.com/m-shogo/memories-project/services/import-api/internal/previewspool"
)

const (
	commitKeyFormat   = "memory-os-preview-commit-key-v1"
	previewHashFormat = "memory-os-preview-ready-hash-v1"
)

// DeriveCommitKey binds the deterministic commit identity from independently
// verified evidence. The spool attempt ID is deliberately excluded: a retried
// parse of identical content in a new attempt produces the same key and must
// return the already committed Preview instead of a duplicate.
func DeriveCommitKey(verified previewspool.VerifiedSpool) string {
	return deriveDigest(commitKeyFormat, verified)
}

// DerivePreviewHash is the final Preview hash stored on the ready row. It
// includes both stream hashes and both counts as required by the commit
// contract.
func DerivePreviewHash(verified previewspool.VerifiedSpool) string {
	return deriveDigest(previewHashFormat, verified)
}

func deriveDigest(format string, verified previewspool.VerifiedSpool) string {
	payload := strings.Join([]string{
		format,
		verified.OwnerAccountID,
		strconv.FormatInt(verified.AccountEpoch, 10),
		verified.JobID,
		verified.Source.ObjectKey,
		verified.Source.ObjectVersionID,
		strconv.FormatInt(verified.Source.ContentLength, 10),
		verified.Source.ChecksumSHA256,
		verified.Adapter.AdapterID,
		verified.Adapter.AdapterVersion,
		verified.Adapter.ArtifactSHA256,
		verified.OptionsSHA256,
		strconv.Itoa(verified.Evidence.Accepted.RecordCount),
		verified.Evidence.Accepted.SHA256,
		strconv.Itoa(verified.Evidence.Rejected.RecordCount),
		verified.Evidence.Rejected.SHA256,
	}, "\n")
	sum := sha256.Sum256([]byte(payload))
	return hex.EncodeToString(sum[:])
}
