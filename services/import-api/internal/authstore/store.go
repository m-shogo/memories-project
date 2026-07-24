// Package authstore turns bearer session tokens into verified principals.
// The database stores only SHA-256 token digests, reachable exclusively
// through SECURITY DEFINER functions executed as the dedicated
// memory_auth_runtime role — no table privilege exists anywhere. Raw tokens
// live only in the client and in the one request being authenticated.
package authstore

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/m-shogo/memories-project/services/import-api/internal/cryptoids"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

const (
	// TokenPrefix marks Memory OS session tokens; the rest is 32 random
	// bytes in hex. The prefix carries no secret and only aids log scrubbing
	// and early rejection of foreign credentials.
	TokenPrefix = "mos_session_"

	tokenRandomBytes = 32
	tokenLength      = len(TokenPrefix) + tokenRandomBytes*2

	MaxSessionTTL = 30 * 24 * time.Hour
)

var (
	ErrSessionNotFound = errors.New("session token does not resolve to an active session")
	ErrInvalidIssue    = errors.New("invalid session issuance input")
	ErrNilPool         = errors.New("authstore requires a connection pool")
)

// interactiveAuthorities are the only authorities a bearer session may carry;
// worker and deletion leases are never session-backed.
var interactiveAuthorities = map[security.Authority]bool{
	security.AuthorityIOSUser:        true,
	security.AuthorityIOSDevice:      true,
	security.AuthorityBrowserPairing: true,
}

type Store struct {
	Pool *pgxpool.Pool
}

type IssueInput struct {
	AccountID string
	Epoch     int64
	Authority security.Authority
	TTL       time.Duration
	Now       time.Time
}

type IssuedSession struct {
	SessionID string
	Token     string
	ExpiresAt time.Time
}

// Issue creates one session and returns the raw token exactly once. Callers
// are the authenticated login flow (later: Apple code exchange) and the
// clearly-labeled development bootstrap; nothing else may mint sessions.
func (s Store) Issue(ctx context.Context, input IssueInput) (IssuedSession, error) {
	if s.Pool == nil {
		return IssuedSession{}, ErrNilPool
	}
	if !interactiveAuthorities[input.Authority] {
		return IssuedSession{}, fmt.Errorf("%w: authority", ErrInvalidIssue)
	}
	if input.TTL <= 0 || input.TTL > MaxSessionTTL {
		return IssuedSession{}, fmt.Errorf("%w: TTL", ErrInvalidIssue)
	}
	if _, err := security.NewVerifiedPrincipal(input.AccountID, input.Epoch, input.Authority); err != nil {
		return IssuedSession{}, fmt.Errorf("%w: %v", ErrInvalidIssue, err)
	}
	now := input.Now
	if now.IsZero() {
		now = time.Now()
	}
	now = now.UTC()

	sessionID, err := cryptoids.Generator{}.NewID("ses")
	if err != nil {
		return IssuedSession{}, err
	}
	randomness := make([]byte, tokenRandomBytes)
	if _, err := rand.Read(randomness); err != nil {
		return IssuedSession{}, fmt.Errorf("read session randomness: %w", err)
	}
	token := TokenPrefix + hex.EncodeToString(randomness)
	digest := sha256.Sum256([]byte(token))
	expiresAt := now.Add(input.TTL)

	err = s.withAuthRole(ctx, func(tx pgx.Tx) error {
		_, err := tx.Exec(ctx,
			"SELECT memory_os.issue_account_session($1, $2, $3, $4, $5, $6, $7)",
			sessionID, hex.EncodeToString(digest[:]), input.AccountID, input.Epoch,
			string(input.Authority), now, expiresAt)
		return err
	})
	if err != nil {
		return IssuedSession{}, fmt.Errorf("issue account session: %w", err)
	}
	return IssuedSession{SessionID: sessionID, Token: token, ExpiresAt: expiresAt}, nil
}

// Resolve authenticates one bearer token. Every failure — wrong shape,
// unknown digest, expired, revoked — collapses into ErrSessionNotFound so
// responses cannot distinguish token states.
func (s Store) Resolve(ctx context.Context, token string) (security.Principal, error) {
	if s.Pool == nil {
		return security.Principal{}, ErrNilPool
	}
	if len(token) != tokenLength || !strings.HasPrefix(token, TokenPrefix) {
		return security.Principal{}, ErrSessionNotFound
	}
	digest := sha256.Sum256([]byte(token))

	var accountID, authority string
	var epoch int64
	err := s.withAuthRole(ctx, func(tx pgx.Tx) error {
		return tx.QueryRow(ctx,
			"SELECT owner_account_id, account_epoch, authority FROM memory_os.resolve_account_session($1)",
			hex.EncodeToString(digest[:]),
		).Scan(&accountID, &epoch, &authority)
	})
	if errors.Is(err, pgx.ErrNoRows) {
		return security.Principal{}, ErrSessionNotFound
	}
	if err != nil {
		return security.Principal{}, fmt.Errorf("resolve account session: %w", err)
	}
	principal, err := security.NewVerifiedPrincipal(accountID, epoch, security.Authority(authority))
	if err != nil {
		return security.Principal{}, fmt.Errorf("stored session carries an invalid identity: %w", err)
	}
	if !interactiveAuthorities[principal.Authority()] {
		return security.Principal{}, ErrSessionNotFound
	}
	return principal, nil
}

// Revoke invalidates one session by its raw token.
func (s Store) Revoke(ctx context.Context, token string) (bool, error) {
	if s.Pool == nil {
		return false, ErrNilPool
	}
	if len(token) != tokenLength || !strings.HasPrefix(token, TokenPrefix) {
		return false, nil
	}
	digest := sha256.Sum256([]byte(token))
	var revoked bool
	err := s.withAuthRole(ctx, func(tx pgx.Tx) error {
		return tx.QueryRow(ctx,
			"SELECT memory_os.revoke_account_session($1)", hex.EncodeToString(digest[:]),
		).Scan(&revoked)
	})
	if err != nil {
		return false, fmt.Errorf("revoke account session: %w", err)
	}
	return revoked, nil
}

// withAuthRole runs one short transaction as the auth runtime role, which
// holds EXECUTE on the session definer functions and nothing else.
func (s Store) withAuthRole(ctx context.Context, fn func(pgx.Tx) error) error {
	tx, err := s.Pool.BeginTx(ctx, pgx.TxOptions{})
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback(ctx) }()
	if _, err := tx.Exec(ctx, "SET LOCAL ROLE memory_auth_runtime"); err != nil {
		return err
	}
	if err := fn(tx); err != nil {
		return err
	}
	return tx.Commit(ctx)
}

// IssueForApple adapts Issue to the appleauth.SessionIssuer signature, so the
// Apple login service can mint a session without depending on IssueInput. It
// applies no policy of its own — Issue owns the validation.
func (s Store) IssueForApple(ctx context.Context, accountID string, accountEpoch int64, authority security.Authority, ttl time.Duration) (string, error) {
	issued, err := s.Issue(ctx, IssueInput{
		AccountID: accountID,
		Epoch:     accountEpoch,
		Authority: authority,
		TTL:       ttl,
	})
	if err != nil {
		return "", err
	}
	return issued.Token, nil
}
