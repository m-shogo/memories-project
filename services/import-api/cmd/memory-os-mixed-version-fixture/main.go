package main

import (
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/m-shogo/memories-project/services/import-api/internal/previewcommit"
	"github.com/m-shogo/memories-project/services/import-api/internal/previewspool"
)

type output struct {
	PreviewID      string `json:"previewId"`
	PreviewSHA256  string `json:"previewSha256"`
	CandidateCount int    `json:"candidateCount"`
}

func fail(format string, arguments ...any) {
	_, _ = fmt.Fprintf(os.Stderr, format+"\n", arguments...)
	os.Exit(1)
}

func main() {
	var databaseURL string
	var accountID string
	var jobID string
	var previewID string
	var spoolID string
	var uploadID string
	var fingerprint string

	flag.StringVar(&databaseURL, "database-url", "", "PostgreSQL URL")
	flag.StringVar(&accountID, "account-id", "", "synthetic account ID")
	flag.StringVar(&jobID, "job-id", "", "synthetic import job ID")
	flag.StringVar(&previewID, "preview-id", "", "synthetic preview ID")
	flag.StringVar(&spoolID, "spool-id", "", "synthetic spool ID")
	flag.StringVar(&uploadID, "upload-id", "", "synthetic upload ID")
	flag.StringVar(&fingerprint, "fingerprint", "", "synthetic memory fingerprint")
	flag.Parse()

	if databaseURL == "" || accountID == "" || jobID == "" || previewID == "" ||
		spoolID == "" || uploadID == "" || len(fingerprint) < 8 || len(fingerprint) > 128 {
		fail("all fixture arguments are required and fingerprint must be 8..128 bytes")
	}
	if strings.ContainsAny(fingerprint, "\r\n\t") {
		fail("fingerprint contains control characters")
	}

	ctx := context.Background()
	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		fail("open fixture database: %v", err)
	}
	defer pool.Close()

	if _, err := pool.Exec(ctx, `
		INSERT INTO memory_os.account_control (account_id, account_epoch, state)
		VALUES ($1, 1, 'active')
		ON CONFLICT (account_id) DO UPDATE
		SET account_epoch = 1, state = 'active', deletion_started_at = NULL,
		    deletion_completed_at = NULL, updated_at = now()`, accountID); err != nil {
		fail("provision fixture account: %v", err)
	}
	if _, err := pool.Exec(ctx, `
		INSERT INTO memory_os.import_job
			(id, owner_account_id, account_epoch, state, source_surface)
		VALUES ($1, $2, 1, 'preview_building', 'ios_files')`, jobID, accountID); err != nil {
		fail("provision fixture job: %v", err)
	}

	record, err := json.Marshal(struct {
		Fingerprint string `json:"fingerprint"`
		Title       string `json:"title"`
	}{Fingerprint: fingerprint, Title: "mixed-version synthetic fixture"})
	if err != nil {
		fail("encode canonical record: %v", err)
	}
	recordDigest := sha256.Sum256(record)
	acceptedHasher := sha256.New()
	var lengthPrefix [8]byte
	binary.BigEndian.PutUint64(lengthPrefix[:], uint64(len(record)))
	_, _ = acceptedHasher.Write(lengthPrefix[:])
	_, _ = acceptedHasher.Write(record)
	acceptedLength := int64(len(lengthPrefix) + len(record))
	now := time.Now().UTC()

	verified := previewspool.VerifiedSpool{
		SpoolID:        spoolID,
		JobID:          jobID,
		OwnerAccountID: accountID,
		AccountEpoch:   1,
		Source: previewspool.SealSourceBinding{
			ObjectKey:       "quarantine/" + jobID + "/" + uploadID,
			ObjectVersionID: "mixed-version-fixture-v1",
			ContentLength:   int64(len(record)),
			ChecksumSHA256:  hex.EncodeToString(recordDigest[:]),
		},
		Adapter: previewspool.SealAdapterBinding{
			AdapterID:      "generic-csv",
			AdapterVersion: "1.0.0",
			ArtifactSHA256: strings.Repeat("b", 64),
		},
		OptionsSHA256: strings.Repeat("c", 64),
		CreatedAt:     now.Add(-time.Minute),
		ExpiresAt:     now.Add(time.Hour),
		Evidence: previewspool.WriteEvidence{
			SourceRowCount:  1,
			SpoolByteLength: acceptedLength,
			Accepted: previewspool.StreamEvidence{
				RecordFormat: previewspool.AcceptedRecordFormat,
				RecordCount:  1,
				ByteLength:   acceptedLength,
				SHA256:       hex.EncodeToString(acceptedHasher.Sum(nil)),
			},
			Rejected: previewspool.StreamEvidence{
				RecordFormat: previewspool.RejectedRecordFormat,
				RecordCount:  0,
				ByteLength:   0,
				SHA256:       hex.EncodeToString(sha256.New().Sum(nil)),
			},
		},
	}

	committer, err := previewcommit.NewCommitter(pool)
	if err != nil {
		fail("create preview committer: %v", err)
	}
	result, err := committer.Commit(ctx, previewcommit.CommitRequest{
		PreviewID: previewID,
		Verified:  verified,
		Candidates: []previewcommit.CandidateRow{{
			Ordinal:         1,
			SourceRow:       1,
			RecordSHA256:    hex.EncodeToString(recordDigest[:]),
			CanonicalRecord: record,
		}},
	}, now)
	if err != nil {
		fail("commit synthetic preview: %v", err)
	}
	if result.AlreadyCommitted {
		fail("fixture preview unexpectedly already existed")
	}

	if err := json.NewEncoder(os.Stdout).Encode(output{
		PreviewID:      result.PreviewID,
		PreviewSHA256:  result.PreviewHash,
		CandidateCount: 1,
	}); err != nil {
		fail("encode fixture output: %v", err)
	}
}
