package appleauth

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/metrics"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

type mtrLogin struct {
	result LoginResult
	err    error
}

func (f mtrLogin) Login(context.Context, Input) (LoginResult, error) { return f.result, f.err }

func newMeter(t *testing.T) (*metrics.Registry, metrics.Recorder) {
	t.Helper()
	reg := metrics.NewRegistry()
	return reg, metrics.NewRegistryRecorder(reg, nil)
}

func TestMeteredLoginSuccessRecordsExchangeAndSession(t *testing.T) {
	reg, rec := newMeter(t)
	m := MeteredLoginService{Inner: mtrLogin{result: LoginResult{AccountID: "acct-secret", SessionToken: "tok-secret"}}, Recorder: rec}
	if _, err := m.Login(context.Background(), Input{}); err != nil {
		t.Fatal(err)
	}
	out := reg.Export()
	if !strings.Contains(out, `memory_os_apple_exchange_total{provider="apple",outcome="success",failure_class="none"} 1`) {
		t.Fatalf("exchange success not recorded:\n%s", out)
	}
	if !strings.Contains(out, `memory_os_session_issuance_total{outcome="success"} 1`) {
		t.Fatalf("session issuance not recorded:\n%s", out)
	}
	// The account id and token must never appear in a metric.
	for _, secret := range []string{"acct-secret", "tok-secret"} {
		if strings.Contains(out, secret) {
			t.Fatalf("metric leaked %q:\n%s", secret, out)
		}
	}
}

func TestMeteredLoginClassifiesFailures(t *testing.T) {
	cases := []struct {
		name    string
		err     error
		outcome string
		fclass  string
		replay  bool
	}{
		{"rejected token", ErrSignatureInvalid, "rejected", "authentication_failure", false},
		{"invalid request", ErrMalformedToken, "rejected", "invalid_request", false},
		{"binding conflict", ErrAccountBindingConflict, "rejected", "authorization_denied", false},
		{"apple unavailable", ErrTokenEndpointUnavailable, "failure", "external_apple_failure", false},
		{"session issuance", ErrSessionIssuance, "failure", "database_unavailable", false},
		{"replay residual", errors.New("pq: duplicate key"), "rejected", "replay_rejected", true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			reg, rec := newMeter(t)
			m := MeteredLoginService{Inner: mtrLogin{err: tc.err}, Recorder: rec}
			_, _ = m.Login(context.Background(), Input{})
			out := reg.Export()
			want := `memory_os_apple_exchange_total{provider="apple",outcome="` + tc.outcome + `",failure_class="` + tc.fclass + `"} 1`
			if !strings.Contains(out, want) {
				t.Fatalf("want %s in:\n%s", want, out)
			}
			hasReplay := strings.Contains(out, "memory_os_apple_replay_rejections_total 1")
			if hasReplay != tc.replay {
				t.Fatalf("replay rejection recorded=%v want %v:\n%s", hasReplay, tc.replay, out)
			}
		})
	}
}

type mtrReplay struct{ err error }

func (f mtrReplay) Consume(context.Context, string, string) error { return f.err }

type mtrAccounts struct {
	id  string
	ep  int64
	err error
}

func (f mtrAccounts) ResolveOrCreate(context.Context, string, string) (string, int64, error) {
	return f.id, f.ep, f.err
}

type mtrIssuer struct {
	tok string
	err error
}

func (f mtrIssuer) Issue(context.Context, string, int64, security.Authority, time.Duration) (string, error) {
	return f.tok, f.err
}

func TestMeteredDBSeamsRecordOperations(t *testing.T) {
	reg, rec := newMeter(t)

	rg := MeteredReplayGuard{Inner: mtrReplay{}, Recorder: rec}
	if err := rg.Consume(context.Background(), "nonce-secret", strings.Repeat("a", 64)); err != nil {
		t.Fatal(err)
	}
	ab := MeteredAccountBindingStore{Inner: mtrAccounts{id: "acct-x", ep: 1}, Recorder: rec}
	if _, _, err := ab.ResolveOrCreate(context.Background(), "iss", "subject-secret"); err != nil {
		t.Fatal(err)
	}
	si := MeteredSessionIssuer{Inner: mtrIssuer{tok: "tok-x"}, Recorder: rec}
	if _, err := si.Issue(context.Background(), "acct-x", 1, security.AuthorityIOSUser, time.Hour); err != nil {
		t.Fatal(err)
	}

	out := reg.Export()
	for _, op := range []string{"apple_replay_consume", "apple_identity_upsert", "session_insert"} {
		if !strings.Contains(out, `operation="`+op+`",outcome="success",failure_class="none"} 1`) {
			t.Fatalf("db op %q not recorded:\n%s", op, out)
		}
	}
	// No nonce, subject, account id or token may appear as a label.
	for _, secret := range []string{"nonce-secret", "subject-secret", "acct-x", "tok-x"} {
		if strings.Contains(out, secret) {
			t.Fatalf("db metric leaked %q:\n%s", secret, out)
		}
	}
}

func TestMeteredAccountBindingConflictIsRejected(t *testing.T) {
	reg, rec := newMeter(t)
	ab := MeteredAccountBindingStore{Inner: mtrAccounts{err: ErrAccountBindingConflict}, Recorder: rec}
	_, _, _ = ab.ResolveOrCreate(context.Background(), "iss", "sub")
	if !strings.Contains(reg.Export(), `operation="apple_identity_upsert",outcome="rejected",failure_class="integrity_failure"} 1`) {
		t.Fatalf("binding conflict not recorded as rejected:\n%s", reg.Export())
	}
}
