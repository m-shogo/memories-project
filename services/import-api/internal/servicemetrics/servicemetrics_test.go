package servicemetrics

import (
	"context"
	"errors"
	"strings"
	"testing"

	applydomain "github.com/m-shogo/memories-project/services/import-api/internal/apply"
	"github.com/m-shogo/memories-project/services/import-api/internal/metrics"
	"github.com/m-shogo/memories-project/services/import-api/internal/previewread"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

func newMeter(t *testing.T) (*metrics.Registry, metrics.Recorder) {
	t.Helper()
	reg := metrics.NewRegistry()
	return reg, metrics.NewRegistryRecorder(reg, nil)
}

type fakePreview struct {
	view previewread.View
	err  error
}

func (f fakePreview) GetJobPreview(context.Context, security.Principal, string, int) (previewread.View, error) {
	return f.view, f.err
}

func TestPreviewReadRecordsOperation(t *testing.T) {
	reg, rec := newMeter(t)
	m := PreviewRead{Inner: fakePreview{view: previewread.View{PreviewID: "prev-secret", JobID: "job-secret"}}, Recorder: rec}
	if _, err := m.GetJobPreview(context.Background(), security.Principal{}, "job-secret", 100); err != nil {
		t.Fatal(err)
	}
	out := reg.Export()
	if !strings.Contains(out, `operation="preview_read",outcome="success",failure_class="none"} 1`) {
		t.Fatalf("preview_read not recorded:\n%s", out)
	}
	for _, secret := range []string{"prev-secret", "job-secret"} {
		if strings.Contains(out, secret) {
			t.Fatalf("preview metric leaked %q:\n%s", secret, out)
		}
	}
}

func TestPreviewReadClassifiesErrors(t *testing.T) {
	cases := []struct {
		err     error
		outcome string
		fclass  string
	}{
		{previewread.ErrNotFound, "rejected", "none"},
		{previewread.ErrInvalidRequest, "rejected", "invalid_request"},
		{errors.New("connection reset"), "failure", "database_unavailable"},
	}
	for _, tc := range cases {
		reg, rec := newMeter(t)
		m := PreviewRead{Inner: fakePreview{err: tc.err}, Recorder: rec}
		_, _ = m.GetJobPreview(context.Background(), security.Principal{}, "job", 100)
		want := `operation="preview_read",outcome="` + tc.outcome + `",failure_class="` + tc.fclass + `"} 1`
		if !strings.Contains(reg.Export(), want) {
			t.Fatalf("want %s:\n%s", want, reg.Export())
		}
	}
}

type fakeApply struct {
	result applydomain.Result
	err    error
}

func (f fakeApply) Apply(context.Context, security.Principal, applydomain.Request) (applydomain.Result, error) {
	return f.result, f.err
}

func TestApplyRecordsOperation(t *testing.T) {
	reg, rec := newMeter(t)
	m := Apply{Inner: fakeApply{result: applydomain.Result{ApplyID: "apply-secret"}}, Recorder: rec}
	if _, err := m.Apply(context.Background(), security.Principal{}, applydomain.Request{PreviewID: "prev-secret"}); err != nil {
		t.Fatal(err)
	}
	out := reg.Export()
	if !strings.Contains(out, `operation="apply_transaction",outcome="success",failure_class="none"} 1`) {
		t.Fatalf("apply_transaction not recorded:\n%s", out)
	}
	for _, secret := range []string{"apply-secret", "prev-secret"} {
		if strings.Contains(out, secret) {
			t.Fatalf("apply metric leaked %q:\n%s", secret, out)
		}
	}
}

func TestApplyClassifiesErrors(t *testing.T) {
	cases := []struct {
		err     error
		outcome string
		fclass  string
	}{
		{applydomain.ErrInvalidRequest, "rejected", "invalid_request"},
		{applydomain.ErrPreviewExpired, "rejected", "none"},
		{applydomain.ErrApplyAccountingMismatch, "failure", "integrity_failure"},
		{errors.New("deadlock"), "failure", "database_unavailable"},
	}
	for _, tc := range cases {
		reg, rec := newMeter(t)
		m := Apply{Inner: fakeApply{err: tc.err}, Recorder: rec}
		_, _ = m.Apply(context.Background(), security.Principal{}, applydomain.Request{})
		want := `operation="apply_transaction",outcome="` + tc.outcome + `",failure_class="` + tc.fclass + `"} 1`
		if !strings.Contains(reg.Export(), want) {
			t.Fatalf("want %s:\n%s", want, reg.Export())
		}
	}
}
