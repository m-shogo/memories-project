package loadtest

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"sync"
	"sync/atomic"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/appleauth"
	"github.com/m-shogo/memories-project/services/import-api/internal/httpapi"
	"github.com/m-shogo/memories-project/services/import-api/internal/metrics"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

// This file assembles a mocked Apple sign-in path that runs through the exact
// same measurement decorators the production server uses. It performs no RSA
// verification and no network or database call — it is a MOCK dependency, and
// every figure a load test derives from it is a local, non-production number.
// Its value is that it exercises the real metric-emission boundary (apple
// exchange, session issuance, replay, and the three database seams) under
// concurrency, deterministically.

// memReplay is an in-memory replay guard. A repeated (nonce, code) pair is a
// replay and is rejected, mirroring the unique-violation the real store raises.
type memReplay struct {
	mu   sync.Mutex
	seen map[string]struct{}
	fail atomic.Bool
	n    atomic.Int64
}

func (m *memReplay) Consume(_ context.Context, nonceClaim, codeSHA256 string) error {
	m.n.Add(1)
	if m.fail.Load() {
		return errors.New("replay store unavailable")
	}
	key := nonceClaim + "|" + codeSHA256
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, ok := m.seen[key]; ok {
		return errors.New("replayed credential")
	}
	m.seen[key] = struct{}{}
	return nil
}

// memAccounts is an in-memory account binding store. One subject maps to one
// stable account, so a steady stream of the same identity does not create
// unbounded accounts.
type memAccounts struct {
	mu       sync.Mutex
	byID     map[string]string
	sequence int64
	fail     atomic.Bool
}

func (m *memAccounts) ResolveOrCreate(_ context.Context, _ /*issuer*/, subject string) (string, int64, error) {
	if m.fail.Load() {
		return "", 0, errors.New("account store unavailable")
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	if id, ok := m.byID[subject]; ok {
		return id, 1, nil
	}
	m.sequence++
	id := fmt.Sprintf("acct-%d", m.sequence)
	m.byID[subject] = id
	return id, 1, nil
}

func (m *memAccounts) count() int {
	m.mu.Lock()
	defer m.mu.Unlock()
	return len(m.byID)
}

// memSessions is an in-memory session issuer. It counts successful issuances.
type memSessions struct {
	issued atomic.Int64
	fail   atomic.Bool
}

func (m *memSessions) Issue(_ context.Context, _ string, _ int64, _ security.Authority, _ time.Duration) (string, error) {
	if m.fail.Load() {
		return "", errors.New("session store unavailable")
	}
	n := m.issued.Add(1)
	return fmt.Sprintf("sess-%d", n), nil
}

// loginCore runs the sign-in sequence through the metered database seams. It is
// the mock stand-in for appleauth.LoginService's composition, without the
// verifier crypto.
type loginCore struct {
	accounts appleauth.AccountBindingStore
	replay   appleauth.ReplayGuard
	sessions appleauth.SessionIssuer
	subject  string
}

func (c loginCore) Login(ctx context.Context, in appleauth.Input) (appleauth.LoginResult, error) {
	accountID, epoch, err := c.accounts.ResolveOrCreate(ctx, appleauth.DefaultIssuer, c.subject)
	if err != nil {
		return appleauth.LoginResult{}, err
	}
	sum := sha256.Sum256([]byte(in.AuthorizationCode))
	if err := c.replay.Consume(ctx, in.ExpectedNonceClaim, hex.EncodeToString(sum[:])); err != nil {
		// A replay (or store fault) fails closed as a rejection, which the outer
		// meter classifies as a replay rejection.
		return appleauth.LoginResult{}, err
	}
	token, err := c.sessions.Issue(ctx, accountID, epoch, security.AuthorityIOSUser, time.Hour)
	if err != nil {
		return appleauth.LoginResult{}, fmt.Errorf("%w: %v", appleauth.ErrSessionIssuance, err)
	}
	return appleauth.LoginResult{SessionToken: token, AccountID: accountID, AccountEpoch: epoch}, nil
}

// AppleWorld bundles the mock stores and the assembled, fully metered login
// service so a scenario can drive the endpoint and then inspect the resulting
// state (accounts created, sessions issued, replay attempts).
type AppleWorld struct {
	Replay   *memReplay
	Accounts *memAccounts
	Sessions *memSessions
	Login    httpapi.AppleLoginService
}

// NewAppleWorld builds a mock Apple world whose login service records through
// the given recorder.
func NewAppleWorld(recorder metrics.Recorder) *AppleWorld {
	replay := &memReplay{seen: map[string]struct{}{}}
	accounts := &memAccounts{byID: map[string]string{}}
	sessions := &memSessions{}
	core := loginCore{
		accounts: appleauth.MeteredAccountBindingStore{Inner: accounts, Recorder: recorder},
		replay:   appleauth.MeteredReplayGuard{Inner: replay, Recorder: recorder},
		sessions: appleauth.MeteredSessionIssuer{Inner: sessions, Recorder: recorder},
		subject:  "mock-subject",
	}
	return &AppleWorld{
		Replay:   replay,
		Accounts: accounts,
		Sessions: sessions,
		Login:    appleauth.MeteredLoginService{Inner: core, Recorder: recorder},
	}
}

// SessionsIssued reports how many sessions the mock issued.
func (w *AppleWorld) SessionsIssued() int { return int(w.Sessions.issued.Load()) }

// AccountsCreated reports how many distinct accounts the mock created.
func (w *AppleWorld) AccountsCreated() int { return w.Accounts.count() }

// ReplayAttempts reports how many times the replay guard was consulted.
func (w *AppleWorld) ReplayAttempts() int { return int(w.Replay.n.Load()) }
