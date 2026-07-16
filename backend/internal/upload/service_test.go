package upload

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/backend/internal/security"
)

type fixedClock struct{ value time.Time }

func (c fixedClock) Now() time.Time { return c.value }

type fakeJobs struct {
	job       Job
	err       error
	principal security.Principal
}

func (f *fakeJobs) FindOwnedJob(_ context.Context, principal security.Principal, _ string) (Job, error) {
	f.principal = principal
	return f.job, f.err
}

type fakeStore struct {
	created       []Authorization
	issued        []string
	failed        map[string]string
	createErr     error
	issuedErr     error
	lastPrincipal security.Principal
}

func (f *fakeStore) CreatePending(_ context.Context, principal security.Principal, authorization Authorization) error {
	f.lastPrincipal = principal
	if f.createErr != nil {
		return f.createErr
	}
	f.created = append(f.created, authorization)
	return nil
}

func (f *fakeStore) MarkIssued(_ context.Context, principal security.Principal, authorizationID string) error {
	f.lastPrincipal = principal
	if f.issuedErr != nil {
		return f.issuedErr
	}
	f.issued = append(f.issued, authorizationID)
	return nil
}

func (f *fakeStore) MarkFailed(_ context.Context, principal security.Principal, authorizationID, safeReason string) error {
	f.lastPrincipal = principal
	if f.failed == nil {
		f.failed = map[string]string{}
	}
	f.failed[authorizationID] = safeReason
	return nil
}

type fakeSigner struct {
	request SignRequest
	result  SignedPUT
	err     error
}

func (f *fakeSigner) SignPrivatePUT(_ context.Context, request SignRequest) (SignedPUT, error) {
	f.request = request
	return f.result, f.err
}

func validPrincipal(t *testing.T) security.Principal {
	t.Helper()
	principal, err := security.NewVerifiedPrincipal(
		"acct_01J00000000000000000000000",
		7,
		"https://appleid.apple.com",
		"apple-subject-001",
	)
	if err != nil {
		t.Fatalf("NewVerifiedPrincipal() error = %v", err)
	}
	return principal
}

func validRequest() Request {
	return Request{
		JobID:            "job_01J00000000000000000000000",
		ContentLength:    1024,
		ChecksumSHA256:   strings.Repeat("a", 64),
		ContentType:      "application/zip",
		SourceSurface:    "ios_files",
		DisplayFilename: "private-life-export.zip",
	}
}

func TestIssueCreatesServerBoundAuthorization(t *testing.T) {
	t.Parallel()

	store := &fakeStore{}
	jobs := &fakeJobs{job: Job{
		ID:             "job_01J00000000000000000000000",
		OwnerAccountID: "acct_01J00000000000000000000000",
		AccountEpoch:   7,
		State:          "awaiting_upload",
	}}
	signer := &fakeSigner{result: SignedPUT{
		URL: "https://storage.invalid/private-signed-put",
		RequiredHeaders: map[string]string{
			"content-type":      "application/zip",
			"x-checksum-sha256": strings.Repeat("a", 64),
		},
	}}
	service, err := NewService(jobs, store, signer)
	if err != nil {
		t.Fatalf("NewService() error = %v", err)
	}
	service.clock = fixedClock{value: time.Date(2026, 7, 16, 4, 0, 0, 0, time.UTC)}

	response, err := service.Issue(context.Background(), validPrincipal(t), validRequest())
	if err != nil {
		t.Fatalf("Issue() error = %v", err)
	}
	if len(store.created) != 1 || len(store.issued) != 1 {
		t.Fatalf("unexpected store transitions: created=%d issued=%d", len(store.created), len(store.issued))
	}
	created := store.created[0]
	if created.Status != "issuing" || response.Authorization.Status != "issued" {
		t.Fatalf("unexpected states: stored=%q response=%q", created.Status, response.Authorization.Status)
	}
	if created.OwnerAccountID != "acct_01J00000000000000000000000" || created.AccountEpoch != 7 {
		t.Fatalf("authorization was not bound to verified principal")
	}
	if jobs.principal.AccountID() != created.OwnerAccountID || store.lastPrincipal.AccountID() != created.OwnerAccountID {
		t.Fatalf("verified principal was not propagated to repositories")
	}
	if !strings.HasPrefix(created.ObjectKey, "quarantine/job_01J00000000000000000000000/obj_") {
		t.Fatalf("unexpected object key: %q", created.ObjectKey)
	}
	if strings.Contains(created.ObjectKey, "private-life-export") {
		t.Fatalf("raw display filename leaked into object key")
	}
	if signer.request.ObjectKey != created.ObjectKey || signer.request.ContentLength != 1024 {
		t.Fatalf("signer request does not match persisted authorization")
	}
	if !created.ExpiresAt.Equal(created.CreatedAt.Add(10 * time.Minute)) {
		t.Fatalf("unexpected expiry: %s", created.ExpiresAt)
	}
}

func TestIssueRejectsCrossOwnerJob(t *testing.T) {
	t.Parallel()

	jobs := &fakeJobs{job: Job{
		ID:             "job_01J00000000000000000000000",
		OwnerAccountID: "acct_01J99999999999999999999999",
		AccountEpoch:   7,
		State:          "awaiting_upload",
	}}
	service, err := NewService(jobs, &fakeStore{}, &fakeSigner{})
	if err != nil {
		t.Fatalf("NewService() error = %v", err)
	}

	_, err = service.Issue(context.Background(), validPrincipal(t), validRequest())
	if !errors.Is(err, ErrJobUnavailable) {
		t.Fatalf("Issue() error = %v, want ErrJobUnavailable", err)
	}
}

func TestIssueMarksPendingAuthorizationFailedWhenSigningFails(t *testing.T) {
	t.Parallel()

	store := &fakeStore{}
	signer := &fakeSigner{err: errors.New("signer unavailable")}
	service, err := NewService(&fakeJobs{job: Job{
		ID:             "job_01J00000000000000000000000",
		OwnerAccountID: "acct_01J00000000000000000000000",
		AccountEpoch:   7,
		State:          "awaiting_upload",
	}}, store, signer)
	if err != nil {
		t.Fatalf("NewService() error = %v", err)
	}

	_, err = service.Issue(context.Background(), validPrincipal(t), validRequest())
	if err == nil {
		t.Fatalf("Issue() expected error")
	}
	if len(store.created) != 1 {
		t.Fatalf("pending authorization was not recorded")
	}
	if got := store.failed[store.created[0].ID]; got != "signing_failed" {
		t.Fatalf("failure state = %q", got)
	}
}

func TestIssueRejectsOversizedUpload(t *testing.T) {
	t.Parallel()

	service, err := NewService(&fakeJobs{}, &fakeStore{}, &fakeSigner{})
	if err != nil {
		t.Fatalf("NewService() error = %v", err)
	}
	request := validRequest()
	request.ContentLength = DefaultMaxUploadBytes + 1

	_, err = service.Issue(context.Background(), validPrincipal(t), request)
	if !errors.Is(err, ErrInvalidLength) {
		t.Fatalf("Issue() error = %v, want ErrInvalidLength", err)
	}
}
