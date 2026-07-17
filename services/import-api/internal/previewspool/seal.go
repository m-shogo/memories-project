package previewspool

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"regexp"
	"strings"
	"time"
)

const (
	ManifestSchemaURI           = "https://memory-os.example/schemas/security/preview-spool-manifest.v1.schema.json"
	ManifestSchemaVersion       = 1
	MaxSourceBytes        int64 = 256 * 1024 * 1024
	MaxSealTTL                  = 24 * time.Hour
)

var (
	ErrInvalidSealInput        = errors.New("invalid Preview spool seal input")
	ErrSealConflict            = errors.New("Preview spool seal input conflicts with published manifest")
	ErrSealPublicationExists   = errors.New("Preview spool manifest already exists")
	ErrSealPublish             = errors.New("Preview spool manifest publication failed")
	ErrSealDurabilityUncertain = errors.New("Preview spool manifest durability is uncertain")
)

type SealSourceBinding struct {
	ObjectKey       string
	ObjectVersionID string
	ContentLength   int64
	ChecksumSHA256  string
}

type SealAdapterBinding struct {
	AdapterID      string
	AdapterVersion string
	ArtifactSHA256 string
}

type SealInput struct {
	JobID          string
	OwnerAccountID string
	AccountEpoch   int64
	Source         SealSourceBinding
	Adapter        SealAdapterBinding
	OptionsSHA256  string
	CreatedAt      time.Time
	ExpiresAt      time.Time
}
type SealEvidence struct {
	WriteEvidence      WriteEvidence
	ManifestByteLength int64
	ManifestSHA256     string
}

type manifestDocument struct {
	Schema          string           `json:"$schema"`
	SchemaVersion   int              `json:"schemaVersion"`
	SpoolID         string           `json:"spoolId"`
	JobID           string           `json:"jobId"`
	OwnerAccountID  string           `json:"ownerAccountId"`
	AccountEpoch    int64            `json:"accountEpoch"`
	Source          manifestSource   `json:"source"`
	Adapter         manifestAdapter  `json:"adapter"`
	OptionsSHA256   string           `json:"optionsSha256"`
	SourceRowCount  int              `json:"sourceRowCount"`
	SpoolByteLength int64            `json:"spoolByteLength"`
	Streams         manifestStreams  `json:"streams"`
	CreatedAt       string           `json:"createdAt"`
	ExpiresAt       string           `json:"expiresAt"`
	Security        manifestSecurity `json:"security"`
}
type manifestSource struct {
	ObjectKey       string `json:"objectKey"`
	ObjectVersionID string `json:"objectVersionId"`
	ContentLength   int64  `json:"contentLength"`
	ChecksumSHA256  string `json:"checksumSha256"`
}
type manifestAdapter struct {
	AdapterID      string `json:"adapterId"`
	AdapterVersion string `json:"adapterVersion"`
	ArtifactSHA256 string `json:"artifactSha256"`
}
type manifestStreams struct {
	Accepted manifestStream `json:"accepted"`
	Rejected manifestStream `json:"rejected"`
}
type manifestStream struct {
	RecordFormat string `json:"recordFormat"`
	RecordCount  int    `json:"recordCount"`
	ByteLength   int64  `json:"byteLength"`
	SHA256       string `json:"sha256"`
}
type manifestSecurity struct {
	SupervisorOwned                       bool `json:"supervisorOwned"`
	SealedBeforeVerification              bool `json:"sealedBeforeVerification"`
	RehashRequiredBeforeCommit            bool `json:"rehashRequiredBeforeCommit"`
	DatabaseTransactionDuringParseAllowed bool `json:"databaseTransactionDuringParseAllowed"`
	RawRejectedValuesAllowed              bool `json:"rawRejectedValuesAllowed"`
	ManifestPathFieldsAllowed             bool `json:"manifestPathFieldsAllowed"`
	SymlinkFollowingAllowed               bool `json:"symlinkFollowingAllowed"`
	CrossAttemptReuseAllowed              bool `json:"crossAttemptReuseAllowed"`
	BackupEligible                        bool `json:"backupEligible"`
}

var opaqueIDPattern = regexp.MustCompile(`^[A-Za-z0-9._:-]{16,128}$`)
var stableIDPattern = regexp.MustCompile(`^[a-z][a-z0-9]*(?:[._:-][a-z0-9]+)*$`)
var semverPattern = regexp.MustCompile(`^[0-9]+\.[0-9]+\.[0-9]+$`)
var versionIDPattern = regexp.MustCompile(`^[A-Za-z0-9._~:+/=-]{1,256}$`)
var objectKeyPattern = regexp.MustCompile(`^quarantine/[A-Za-z0-9._:-]+/[A-Za-z0-9._:-]+$`)
var shaPattern = regexp.MustCompile(`^[a-f0-9]{64}$`)

func buildManifest(spoolID string, input SealInput, evidence WriteEvidence) ([]byte, string, error) {
	if !validSpoolID(spoolID) || !opaqueIDPattern.MatchString(input.JobID) || !opaqueIDPattern.MatchString(input.OwnerAccountID) || input.AccountEpoch < 0 || input.AccountEpoch > 2147483647 {
		return nil, "", ErrInvalidSealInput
	}
	expectedPrefix := "quarantine/" + input.JobID + "/"
	if !objectKeyPattern.MatchString(input.Source.ObjectKey) || !strings.HasPrefix(input.Source.ObjectKey, expectedPrefix) || !versionIDPattern.MatchString(input.Source.ObjectVersionID) || input.Source.ContentLength < 1 || input.Source.ContentLength > MaxSourceBytes || !shaPattern.MatchString(input.Source.ChecksumSHA256) {
		return nil, "", ErrInvalidSealInput
	}
	if !stableIDPattern.MatchString(input.Adapter.AdapterID) || len(input.Adapter.AdapterID) > 160 || !semverPattern.MatchString(input.Adapter.AdapterVersion) || len(input.Adapter.AdapterVersion) > 32 || !shaPattern.MatchString(input.Adapter.ArtifactSHA256) || !shaPattern.MatchString(input.OptionsSHA256) {
		return nil, "", ErrInvalidSealInput
	}
	created := input.CreatedAt.UTC()
	expires := input.ExpiresAt.UTC()
	if input.CreatedAt.IsZero() || input.ExpiresAt.IsZero() || !expires.After(created) || expires.Sub(created) > MaxSealTTL {
		return nil, "", ErrInvalidSealInput
	}
	if err := validateWriteEvidence(evidence); err != nil {
		return nil, "", err
	}
	doc := manifestDocument{
		Schema:         ManifestSchemaURI,
		SchemaVersion:  ManifestSchemaVersion,
		SpoolID:        spoolID,
		JobID:          input.JobID,
		OwnerAccountID: input.OwnerAccountID,
		AccountEpoch:   input.AccountEpoch,
		Source: manifestSource{
			ObjectKey:       input.Source.ObjectKey,
			ObjectVersionID: input.Source.ObjectVersionID,
			ContentLength:   input.Source.ContentLength,
			ChecksumSHA256:  input.Source.ChecksumSHA256,
		},
		Adapter: manifestAdapter{
			AdapterID:      input.Adapter.AdapterID,
			AdapterVersion: input.Adapter.AdapterVersion,
			ArtifactSHA256: input.Adapter.ArtifactSHA256,
		},
		OptionsSHA256:   input.OptionsSHA256,
		SourceRowCount:  evidence.SourceRowCount,
		SpoolByteLength: evidence.SpoolByteLength,
		Streams: manifestStreams{
			Accepted: manifestStream{
				RecordFormat: evidence.Accepted.RecordFormat,
				RecordCount:  evidence.Accepted.RecordCount,
				ByteLength:   evidence.Accepted.ByteLength,
				SHA256:       evidence.Accepted.SHA256,
			},
			Rejected: manifestStream{
				RecordFormat: evidence.Rejected.RecordFormat,
				RecordCount:  evidence.Rejected.RecordCount,
				ByteLength:   evidence.Rejected.ByteLength,
				SHA256:       evidence.Rejected.SHA256,
			},
		},
		CreatedAt: created.Format(time.RFC3339Nano),
		ExpiresAt: expires.Format(time.RFC3339Nano),
		Security: manifestSecurity{
			SupervisorOwned:                       true,
			SealedBeforeVerification:              true,
			RehashRequiredBeforeCommit:            true,
			DatabaseTransactionDuringParseAllowed: false,
			RawRejectedValuesAllowed:              false,
			ManifestPathFieldsAllowed:             false,
			SymlinkFollowingAllowed:               false,
			CrossAttemptReuseAllowed:              false,
			BackupEligible:                        false,
		},
	}
	payload, err := json.Marshal(doc)
	if err != nil {
		return nil, "", err
	}
	sum := sha256.Sum256(payload)
	return payload, hex.EncodeToString(sum[:]), nil
}
func validateWriteEvidence(e WriteEvidence) error {
	if e.Accepted.RecordFormat != AcceptedRecordFormat || e.Rejected.RecordFormat != RejectedRecordFormat || e.Accepted.RecordCount < 1 || e.Accepted.RecordCount > MaxSpoolRecords || e.Rejected.RecordCount < 0 || e.Rejected.RecordCount >= MaxSpoolRecords {
		return ErrInvalidSealInput
	}
	if e.SourceRowCount != e.Accepted.RecordCount+e.Rejected.RecordCount || e.SourceRowCount < 1 || e.SourceRowCount > MaxSpoolRecords {
		return ErrInvalidSealInput
	}
	if e.Accepted.ByteLength < 1 || e.Rejected.ByteLength < 0 || e.SpoolByteLength != e.Accepted.ByteLength+e.Rejected.ByteLength || e.SpoolByteLength < 1 || e.SpoolByteLength > MaxSpoolBytes {
		return ErrInvalidSealInput
	}
	if !shaPattern.MatchString(e.Accepted.SHA256) || !shaPattern.MatchString(e.Rejected.SHA256) {
		return ErrInvalidSealInput
	}
	empty := sha256.Sum256(nil)
	emptyHex := hex.EncodeToString(empty[:])
	if e.Rejected.RecordCount == 0 && (e.Rejected.ByteLength != 0 || e.Rejected.SHA256 != emptyHex) {
		return ErrInvalidSealInput
	}
	if e.Rejected.RecordCount > 0 && e.Rejected.ByteLength == 0 {
		return ErrInvalidSealInput
	}
	return nil
}
