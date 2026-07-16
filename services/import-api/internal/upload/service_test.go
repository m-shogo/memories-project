package upload

import (
	"context"
	"encoding/base64"
	"encoding/hex"
	"errors"
	"fmt"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

type fakeScopedExecutor struct{}

func (fakeScopedExecutor) WithinPrincipal(ctx context.Context, _ security.Principal, _ dbscope.Role, fn func(context.Context, dbscope.Transaction) error) error {
	return fn(ctx, noOpTx{})
}

type noOpTx struct{}

func (noOpTx) Exec(context.Context, string, ...any) error { return nil }
func (noOpTx) Commit() error                              { return nil }
func (noOpTx) Rollback() error                            { return nil }

type fakeRepository struct {
	job            ImportJob
	authorizations map[string]Authorization
	scans          []ScanTicket
	revoked        []string
}

func (r *fakeRepository) GetImportJob(context.Context, dbscope.Transaction, string) (ImportJob, error) {
	return r.job, nil
}
func (r *fakeRepository) InsertAuthorization(_ context.Context, _ dbscope.Transaction, authorization Authorization) error {
	if r.authorizations == nil {
		r.authorizations = map[string]Authorization{}
	}
	r.authorizations[authorization.ID] = authorization
	return nil
}
func (r *fakeRepository) GetAuthorization(_ context.Context, _ dbscope.Transaction, id string) (Authorization, error) {
	authorization, ok := r.authorizations[id]
	if !ok {
		return Authorization{}, errors.New("not found")
	}
	return authorization, nil
}
func (r *fakeRepository) ConsumeIssuedAuthorization(_ context.Context, _ dbscope.Transaction, id string, _ time.Time) (bool, error) {
	authorization := r.authorizations[id]
	if authorization.Status != "issued" {
		return false, nil
	}
	authorization.Status = "consumed"
	r.authorizations[id] = authorization
	return true, nil
}
func (r *fakeRepository) RevokeAuthorization(_ context.Context, _ dbscope.Transaction, id, reason string) error {
	authorization := r.authorizations[id]
	authorization.Status = "revoked"
	r.authorizations[id] = authorization
	r.revoked = append(r.revoked, id+":"+reason)
	return nil
}
func (r *fakeRepository) EnqueueScan(_ context.Context, _ dbscope.Transaction, ticket ScanTicket) error {
	r.scans = append(r.scans, ticket)
	return nil
}

type fakeSigner struct{ request PresignRequest }

func (s *fakeSigner) PresignPut(_ context.Context, request PresignRequest) (PresignResult, error) {
	s.request = request
	return PresignResult{URL: "https://storage.example/signed", RequiredHeaders: map[string]string{
		"Content-Type":          request.ContentType,
		"Content-Length":        fmt.Sprintf("%d", request.ContentLength),
		"x-amz-checksum-sha256": mustChecksumHeader(request.ChecksumSHA256),
	}}, nil
}

type fakeObjects struct {
	metadata ObjectMetadata
	err      error
}

func (o fakeObjects) HeadObject(context.Context, string) (ObjectMetadata, error) {
	return o.metadata, o.err
}

type fakeIDs struct{ value string }

func (i fakeIDs) NewID(string) (string, error) { return i.value, nil }

func TestIssueDerivesOwnerAndObjectKeyFromVerifiedContext(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	principal := mustPrincipal(t, security.AuthorityIOSUser)
	repository := &fakeRepository{job: ImportJob{ID: "job_01J00000000000000000000000", OwnerAccountID: principal.AccountID(), AccountEpoch: 7, Status: "created"}}
	signer := &fakeSigner{}
	service := Service{Transactions: fakeScopedExecutor{}, Repository: repository, Signer: signer, IDs: fakeIDs{value: "upl_01J00000000000000000000000"}, Now: func() time.Time { return now }}
	response, err := service.Issue(context.Background(), principal, validIssueRequest())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	stored := repository.authorizations[response.AuthorizationID]
	if stored.OwnerAccountID != principal.AccountID() || stored.AccountEpoch != 7 {
		t.Fatalf("authorization did not derive verified ownership: %#v", stored)
	}
	wantKey := "quarantine/job_01J00000000000000000000000/upl_01J00000000000000000000000"
	if response.ObjectKey != wantKey || signer.request.ObjectKey != wantKey {
		t.Fatalf("unexpected object key response=%q signer=%q", response.ObjectKey, signer.request.ObjectKey)
	}
	if response.CacheControl != "no-store" || response.ExpiresAt.Sub(now) != DefaultAuthorizationTTL {
		t.Fatalf("unexpected response security fields: %#v", response)
	}
}

func TestIssueRejectsWorkerAuthority(t *testing.T) {
	principal := mustPrincipal(t, security.AuthorityWorkerLease)
	_, err := (Service{}).Issue(context.Background(), principal, validIssueRequest())
	if !errors.Is(err, ErrAuthorityNotAllowed) {
		t.Fatalf("expected authority rejection, got %v", err)
	}
}

func TestCompleteBindsScanToExactObjectVersion(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	principal := mustPrincipal(t, security.AuthorityBrowserPairing)
	authorization := validAuthorization(now, principal)
	repository := &fakeRepository{authorizations: map[string]Authorization{authorization.ID: authorization}}
	metadata := ObjectMetadata{ObjectKey: authorization.ObjectKey, VersionID: "version-123", ETag: "etag-123", ContentLength: authorization.ContentLength, ChecksumSHA256: authorization.ChecksumSHA256, ContentType: authorization.ContentType}
	service := Service{Transactions: fakeScopedExecutor{}, Repository: repository, Objects: fakeObjects{metadata: metadata}, Now: func() time.Time { return now }}
	if err := service.Complete(context.Background(), principal, authorization.ID); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(repository.scans) != 1 {
		t.Fatalf("expected one scan ticket, got %d", len(repository.scans))
	}
	ticket := repository.scans[0]
	if ticket.ObjectVersionID != "version-123" || ticket.ObjectKey != authorization.ObjectKey || ticket.ChecksumSHA256 != authorization.ChecksumSHA256 {
		t.Fatalf("scan ticket not bound to immutable object version: %#v", ticket)
	}
	if repository.authorizations[authorization.ID].Status != "consumed" {
		t.Fatal("authorization was not consumed")
	}
}

func TestCompleteRevokesMetadataMismatch(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	principal := mustPrincipal(t, security.AuthorityIOSUser)
	authorization := validAuthorization(now, principal)
	repository := &fakeRepository{authorizations: map[string]Authorization{authorization.ID: authorization}}
	metadata := ObjectMetadata{ObjectKey: authorization.ObjectKey, VersionID: "version-123", ContentLength: authorization.ContentLength + 1, ChecksumSHA256: authorization.ChecksumSHA256, ContentType: authorization.ContentType}
	service := Service{Transactions: fakeScopedExecutor{}, Repository: repository, Objects: fakeObjects{metadata: metadata}, Now: func() time.Time { return now }}
	err := service.Complete(context.Background(), principal, authorization.ID)
	if !errors.Is(err, ErrObjectMetadataMismatch) {
		t.Fatalf("expected metadata mismatch, got %v", err)
	}
	if len(repository.revoked) != 1 || len(repository.scans) != 0 {
		t.Fatalf("unexpected revoke/scan state: revoked=%v scans=%v", repository.revoked, repository.scans)
	}
}

func TestCompleteRejectsReplay(t *testing.T) {
	now := time.Unix(1_800_000_000, 0).UTC()
	principal := mustPrincipal(t, security.AuthorityIOSUser)
	authorization := validAuthorization(now, principal)
	authorization.Status = "consumed"
	repository := &fakeRepository{authorizations: map[string]Authorization{authorization.ID: authorization}}
	service := Service{Transactions: fakeScopedExecutor{}, Repository: repository, Objects: fakeObjects{}, Now: func() time.Time { return now }}
	err := service.Complete(context.Background(), principal, authorization.ID)
	if !errors.Is(err, ErrUploadAuthorizationConsumed) {
		t.Fatalf("expected consumed error, got %v", err)
	}
}

func mustPrincipal(t *testing.T, authority security.Authority) security.Principal {
	t.Helper()
	principal, err := security.NewVerifiedPrincipal("acct_01J00000000000000000000000", 7, authority)
	if err != nil {
		t.Fatal(err)
	}
	return principal
}

func validIssueRequest() IssueRequest {
	return IssueRequest{JobID: "job_01J00000000000000000000000", ContentLength: 1024, ChecksumSHA256: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", ContentType: "application/zip", SourceSurface: "desktop_portal", DisplayFilename: "export.zip"}
}

func validAuthorization(now time.Time, principal security.Principal) Authorization {
	return Authorization{ID: "upl_01J00000000000000000000000", JobID: "job_01J00000000000000000000000", OwnerAccountID: principal.AccountID(), AccountEpoch: principal.AccountEpoch(), ObjectKey: "quarantine/job_01J00000000000000000000000/upl_01J00000000000000000000000", ContentLength: 1024, ChecksumSHA256: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", ContentType: "application/zip", SourceSurface: "desktop_portal", CreatedAt: now.Add(-time.Minute), ExpiresAt: now.Add(4 * time.Minute), Status: "issued"}
}

func mustChecksumHeader(value string) string {
	decoded, err := hex.DecodeString(value)
	if err != nil {
		panic(err)
	}
	return base64.StdEncoding.EncodeToString(decoded)
}
