package appleauth

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"strings"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// IDGenerator mirrors cryptoids.Generator without importing it, so the store
// can mint a candidate account id while staying decoupled from that package.
type IDGenerator interface {
	NewID(prefix string) (string, error)
}

// replayTTLSeconds bounds how long a consumed nonce/code digest is remembered.
// It only needs to outlast an Apple authorization code's own short validity;
// beyond that the code cannot be exchanged anyway, so the guard row is moot.
const replayTTLSeconds = 900

// PostgresReplayGuard consumes the nonce and code digests through the
// definer-only consume_apple_replay function under the auth runtime role. It
// satisfies ReplayGuard.
type PostgresReplayGuard struct {
	Pool *pgxpool.Pool
}

func (g PostgresReplayGuard) Consume(ctx context.Context, nonceClaim, authorizationCodeSHA256 string) error {
	if g.Pool == nil {
		return errors.New("appleauth replay guard requires a connection pool")
	}
	if !isHexSHA256(authorizationCodeSHA256) {
		return errors.New("authorization code digest must be hex sha-256")
	}
	// The nonce claim is hashed rather than stored raw, so the guard table never
	// holds the claim value itself.
	nonceDigest := sha256.Sum256([]byte(nonceClaim))

	return withAuthRole(ctx, g.Pool, func(tx pgx.Tx) error {
		_, err := tx.Exec(ctx,
			"SELECT memory_os.consume_apple_replay($1, $2, $3)",
			hex.EncodeToString(nonceDigest[:]), authorizationCodeSHA256, replayTTLSeconds)
		if err != nil {
			// A unique-violation here is a replay; the verifier maps this to a
			// fail-closed rejection. The error text is Postgres's own and
			// carries no user data.
			return fmt.Errorf("consume apple replay: %w", err)
		}
		return nil
	})
}

// PostgresAccountBindingStore resolves or creates the account for an Apple
// identity through the definer-only provision_apple_identity function. It
// satisfies AccountBindingStore.
type PostgresAccountBindingStore struct {
	Pool *pgxpool.Pool
	IDs  IDGenerator
}

func (s PostgresAccountBindingStore) ResolveOrCreate(ctx context.Context, issuer, subject string) (string, int64, error) {
	if s.Pool == nil || s.IDs == nil {
		return "", 0, errors.New("apple account binding store dependencies are incomplete")
	}
	// The candidate id is used only if this is a first login; a returning
	// identity keeps its existing account and the candidate is discarded.
	candidate, err := s.IDs.NewID("acct")
	if err != nil {
		return "", 0, fmt.Errorf("generate candidate account id: %w", err)
	}

	var accountID string
	var accountEpoch int64
	var created bool
	err = withAuthRole(ctx, s.Pool, func(tx pgx.Tx) error {
		return tx.QueryRow(ctx,
			"SELECT account_id, account_epoch, created FROM memory_os.provision_apple_identity($1, $2, $3)",
			issuer, subject, candidate,
		).Scan(&accountID, &accountEpoch, &created)
	})
	if err != nil {
		// A non-active account (deleting/deleted/suspended) raises inside the
		// function; surface it as a binding conflict so the verifier fails
		// closed rather than creating a duplicate.
		if isAccountNotActive(err) {
			return "", 0, ErrAccountBindingConflict
		}
		return "", 0, fmt.Errorf("provision apple identity: %w", err)
	}
	return accountID, accountEpoch, nil
}

// withAuthRole runs fn in a transaction scoped to memory_auth_runtime, the same
// NOLOGIN role authstore uses, so the definer functions are reached only from
// their intended caller.
func withAuthRole(ctx context.Context, pool *pgxpool.Pool, fn func(pgx.Tx) error) error {
	tx, err := pool.BeginTx(ctx, pgx.TxOptions{})
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

func isAccountNotActive(err error) bool {
	return err != nil && strings.Contains(err.Error(), "will not be revived by sign-in")
}

func isHexSHA256(value string) bool {
	if len(value) != 64 {
		return false
	}
	_, err := hex.DecodeString(value)
	return err == nil
}
