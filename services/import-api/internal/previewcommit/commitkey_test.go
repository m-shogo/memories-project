package previewcommit

import (
	"strings"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/previewspool"
)

const (
	fixtureJobID   = "job_01J000000000000000000000000"
	fixtureOwner   = "acct_01J00000000000000000000000"
	fixtureEpoch   = int64(7)
	fixtureSpoolID = "spl_01J00000000000000000000000"
)

func verifiedFixture() previewspool.VerifiedSpool {
	createdAt := time.Date(2026, 7, 17, 2, 0, 0, 0, time.UTC)
	return previewspool.VerifiedSpool{
		SpoolID:        fixtureSpoolID,
		JobID:          fixtureJobID,
		OwnerAccountID: fixtureOwner,
		AccountEpoch:   fixtureEpoch,
		Source: previewspool.SealSourceBinding{
			ObjectKey:       "quarantine/" + fixtureJobID + "/upl_01J00000000000000000000000",
			ObjectVersionID: "version-01J00000000000000000000000",
			ContentLength:   4096,
			ChecksumSHA256:  strings.Repeat("a", 64),
		},
		Adapter: previewspool.SealAdapterBinding{
			AdapterID:      "generic-csv",
			AdapterVersion: "1.0.0",
			ArtifactSHA256: strings.Repeat("b", 64),
		},
		OptionsSHA256: strings.Repeat("c", 64),
		CreatedAt:     createdAt,
		ExpiresAt:     createdAt.Add(24 * time.Hour),
		Evidence: previewspool.WriteEvidence{
			SourceRowCount:  3,
			SpoolByteLength: 99,
			Accepted: previewspool.StreamEvidence{
				RecordFormat: previewspool.AcceptedRecordFormat,
				RecordCount:  2,
				ByteLength:   66,
				SHA256:       strings.Repeat("d", 64),
			},
			Rejected: previewspool.StreamEvidence{
				RecordFormat: previewspool.RejectedRecordFormat,
				RecordCount:  1,
				ByteLength:   33,
				SHA256:       strings.Repeat("e", 64),
			},
		},
		ManifestByteLength: 1024,
		ManifestSHA256:     strings.Repeat("f", 64),
	}
}

func TestCommitKeyIsDeterministicAndBindsEveryField(t *testing.T) {
	base := verifiedFixture()
	baseKey := DeriveCommitKey(base)
	if baseKey != DeriveCommitKey(base) || len(baseKey) != 64 {
		t.Fatalf("commit key is not deterministic: %q", baseKey)
	}
	if baseKey == DerivePreviewHash(base) {
		t.Fatal("commit key and preview hash are not domain separated")
	}

	mutations := map[string]func(*previewspool.VerifiedSpool){
		"owner": func(v *previewspool.VerifiedSpool) { v.OwnerAccountID = "acct_01J00000000000000000000001" },
		"epoch": func(v *previewspool.VerifiedSpool) { v.AccountEpoch++ },
		"job":   func(v *previewspool.VerifiedSpool) { v.JobID = "job_01J000000000000000000000001" },
		"object-key": func(v *previewspool.VerifiedSpool) {
			v.Source.ObjectKey = "quarantine/" + fixtureJobID + "/upl_01J00000000000000000000001"
		},
		"object-version":   func(v *previewspool.VerifiedSpool) { v.Source.ObjectVersionID = "version-01J00000000000000000000001" },
		"content-length":   func(v *previewspool.VerifiedSpool) { v.Source.ContentLength++ },
		"source-checksum":  func(v *previewspool.VerifiedSpool) { v.Source.ChecksumSHA256 = strings.Repeat("0", 64) },
		"adapter-id":       func(v *previewspool.VerifiedSpool) { v.Adapter.AdapterID = "generic-tsv" },
		"adapter-version":  func(v *previewspool.VerifiedSpool) { v.Adapter.AdapterVersion = "1.0.1" },
		"adapter-artifact": func(v *previewspool.VerifiedSpool) { v.Adapter.ArtifactSHA256 = strings.Repeat("0", 64) },
		"options":          func(v *previewspool.VerifiedSpool) { v.OptionsSHA256 = strings.Repeat("0", 64) },
		"accepted-count":   func(v *previewspool.VerifiedSpool) { v.Evidence.Accepted.RecordCount++ },
		"accepted-hash":    func(v *previewspool.VerifiedSpool) { v.Evidence.Accepted.SHA256 = strings.Repeat("0", 64) },
		"rejected-count":   func(v *previewspool.VerifiedSpool) { v.Evidence.Rejected.RecordCount++ },
		"rejected-hash":    func(v *previewspool.VerifiedSpool) { v.Evidence.Rejected.SHA256 = strings.Repeat("0", 64) },
	}
	for name, mutate := range mutations {
		mutated := verifiedFixture()
		mutate(&mutated)
		if DeriveCommitKey(mutated) == baseKey {
			t.Fatalf("commit key does not bind %s", name)
		}
	}

	retried := verifiedFixture()
	retried.SpoolID = "spl_01J00000000000000000000001"
	if DeriveCommitKey(retried) != baseKey {
		t.Fatal("commit key must not bind the spool attempt ID")
	}
}
