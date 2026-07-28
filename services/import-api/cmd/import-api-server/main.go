// import-api-server is the executable Import API: bearer-session
// authentication over the strict upload handlers, runtime-role PostgreSQL
// access and the S3-compatible quarantine signer.
//
// Session issuance is not exposed over HTTP: production sessions will be
// minted by the Apple code-exchange flow (a later boundary), and local
// development uses the clearly-labeled -dev-issue-session mode, which prints
// one token and exits without serving.
package main

import (
	"context"
	"crypto/rand"
	"errors"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/m-shogo/memories-project/services/import-api/internal/accountdelete"
	"github.com/m-shogo/memories-project/services/import-api/internal/appleauth"
	"github.com/m-shogo/memories-project/services/import-api/internal/apply"
	"github.com/m-shogo/memories-project/services/import-api/internal/authstore"
	"github.com/m-shogo/memories-project/services/import-api/internal/cryptoids"
	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/epochguard"
	"github.com/m-shogo/memories-project/services/import-api/internal/fenced"
	"github.com/m-shogo/memories-project/services/import-api/internal/httpapi"
	"github.com/m-shogo/memories-project/services/import-api/internal/httpserver"
	"github.com/m-shogo/memories-project/services/import-api/internal/metrics"
	"github.com/m-shogo/memories-project/services/import-api/internal/objectstore"
	"github.com/m-shogo/memories-project/services/import-api/internal/obslog"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgrepo"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/previewread"
	"github.com/m-shogo/memories-project/services/import-api/internal/ratelimit"
	"github.com/m-shogo/memories-project/services/import-api/internal/reqid"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
	"github.com/m-shogo/memories-project/services/import-api/internal/upload"
)

func main() {
	listen := flag.String("listen", envOr("MEMORY_OS_LISTEN", "127.0.0.1:8080"), "listen address")
	databaseURL := flag.String("database-url",
		envOr("MEMORY_OS_DATABASE_URL", envOr("MEMORY_OS_TEST_DATABASE_URL", "postgres://postgres:postgres@127.0.0.1:55432/memory_os_security")),
		"PostgreSQL URL")
	s3Endpoint := flag.String("s3-endpoint",
		envOr("MEMORY_OS_S3_ENDPOINT", envOr("MEMORY_OS_TEST_S3_ENDPOINT", "http://127.0.0.1:59000")),
		"S3-compatible endpoint")
	s3Access := flag.String("s3-access-key", envOr("MEMORY_OS_S3_ACCESS_KEY", "minioadmin"), "S3 access key")
	s3Secret := flag.String("s3-secret-key", envOr("MEMORY_OS_S3_SECRET_KEY", "minioadmin"), "S3 secret key")
	bucket := flag.String("bucket", envOr("MEMORY_OS_BUCKET", "memory-os-quarantine-dev"), "quarantine bucket")
	devProvision := flag.Bool("dev-provision", false,
		"DEV ONLY: provision the versioned bucket and a demo import job at startup")
	devIssueSession := flag.String("dev-issue-session", "",
		"DEV ONLY: issue a 1-hour ios_user session for this account ID, print the token, and exit")
	flag.Parse()

	if err := run(*listen, *databaseURL, *s3Endpoint, *s3Access, *s3Secret, *bucket, *devProvision, *devIssueSession); err != nil {
		fmt.Fprintf(os.Stderr, "import-api-server: %v\n", err)
		os.Exit(1)
	}
}

func run(listen, databaseURL, s3Endpoint, s3Access, s3Secret, bucket string, devProvision bool, devIssueSession string) error {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		return err
	}
	defer pool.Close()

	sessions := authstore.Store{Pool: pool}

	if devIssueSession != "" {
		issued, err := sessions.Issue(ctx, authstore.IssueInput{
			AccountID: devIssueSession,
			Epoch:     1,
			Authority: security.AuthorityIOSUser,
			TTL:       time.Hour,
		})
		if err != nil {
			return err
		}
		fmt.Printf("DEV session for %s (expires %s):\n%s\n",
			devIssueSession, issued.ExpiresAt.Format(time.RFC3339), issued.Token)
		return nil
	}

	objects, err := objectstore.New(objectstore.Config{
		Endpoint:        s3Endpoint,
		Region:          "us-east-1",
		Bucket:          bucket,
		AccessKeyID:     s3Access,
		SecretAccessKey: s3Secret,
	})
	if err != nil {
		return err
	}
	if devProvision {
		if err := objects.ProvisionVersionedBucket(ctx); err != nil {
			return err
		}
	}

	logger := obslog.New(os.Stdout)
	// A metrics registry with a panic observer that surfaces a metrics fault as
	// a single low-information event, never recursively.
	registry := metrics.NewRegistry()
	recorder := metrics.NewRegistryRecorder(registry, func() {
		logger.Emit(obslog.Event{
			Severity: obslog.SeverityError, EventName: "metrics.recorder_panic",
			EventCode: obslog.EventInternalInvariant, Component: obslog.ComponentServer,
			Operation: "metrics", Outcome: obslog.OutcomeFailure, FailureClass: obslog.FailureInternalInvariant,
		})
	})
	executor := dbscope.New(pgscope.Beginner{Pool: pool})
	// Every request surface runs behind the deletion-epoch fence. The guard
	// reads the canonical account_control row, so a session issued before an
	// epoch bump stops working the moment deletion starts.
	accountControl := pgrepo.AccountControl{Pool: pool, Transactions: executor}
	guard := epochguard.Guard{Source: accountControl}
	uploadService := &upload.Service{
		Transactions: executor,
		Repository:   pgrepo.Upload{},
		Signer:       objects,
		Objects:      objects,
		IDs:          cryptoids.Generator{},
	}
	previewService := &previewread.Service{Transactions: executor}
	applyService := &apply.Service{
		Transactions: executor,
		Repository:   pgrepo.Apply{},
		IDs:          cryptoids.Generator{},
	}

	// Sign in with Apple is wired only when the developer credentials are
	// present in the environment. Without them the endpoint returns 503 rather
	// than failing to start, so the binary runs in dev and CI unchanged. The
	// private key path is read here; its bytes never leave this function.
	appleLogin, err := buildAppleLogin(sessions, pool)
	if err != nil {
		return err
	}

	rateLimit, err := buildRateLimit()
	if err != nil {
		return err
	}

	server := httpserver.NewHTTPServer(listen, httpserver.New(httpserver.Config{
		Sessions:   sessions,
		Upload:     fenced.Upload{Guard: guard, Inner: uploadService},
		Preview:    fenced.PreviewRead{Guard: guard, Inner: previewService},
		Apply:      fenced.Apply{Guard: guard, Inner: applyService},
		Account:    accountdelete.Service{Repository: accountControl, Guard: guard},
		AppleLogin: appleLogin,
		Logger:     logger,
		RateLimit:  rateLimit,
		Metrics:    recorder,
	}))

	// The deletion runtime drains accounts the API already fenced. It runs in
	// the same process for now, but it claims through the database lease, so
	// moving it to its own deployment later changes nothing about correctness.
	deletionWorker := accountdelete.Worker{
		Queue:      accountControl,
		Repository: accountControl,
		Objects:    objects,
	}
	go runDeletionRuntime(ctx, deletionWorker, logger, recorder)

	errs := make(chan error, 1)
	go func() {
		logger.Emit(obslog.Event{
			Severity: obslog.SeverityInfo, EventName: "server.started",
			EventCode: obslog.EventServerStarted, Component: obslog.ComponentServer,
			Operation: "listen", Outcome: obslog.OutcomeSuccess,
		})
		errs <- server.ListenAndServe()
	}()

	select {
	case <-ctx.Done():
		logger.Emit(obslog.Event{
			Severity: obslog.SeverityInfo, EventName: "server.stopping",
			EventCode: obslog.EventServerStopping, Component: obslog.ComponentServer,
			Operation: "shutdown", Outcome: obslog.OutcomeSuccess,
		})
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		return server.Shutdown(shutdownCtx)
	case err := <-errs:
		if errors.Is(err, http.ErrServerClosed) {
			return nil
		}
		return err
	}
}

func envOr(name string, fallback string) string {
	if value := os.Getenv(name); value != "" {
		return value
	}
	return fallback
}

// runDeletionRuntime polls for fenced accounts until the process shuts down. A
// failed sweep is logged without a reason string: the account stays fenced and
// claimable, and this log line must never carry a fragment of user content.
func runDeletionRuntime(ctx context.Context, worker accountdelete.Worker, logger *obslog.Logger, recorder metrics.Recorder) {
	const interval = 30 * time.Second
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			// Each sweep cycle is its own correlation boundary: worker events
			// form their own scope rather than borrowing a request's.
			correlationID := reqid.NewCorrelation("deletion")
			sweepStart := time.Now()
			receipts, err := worker.Sweep(ctx, 8)
			for _, receipt := range receipts {
				recorder.RecordDeletionJob(metrics.WorkerDeletion, metrics.OutcomeSuccess, metrics.FailNone, time.Since(sweepStart))
				logger.Emit(obslog.Event{
					Severity: obslog.SeverityInfo, EventName: "deletion.completed",
					EventCode: obslog.EventDeletionCompleted, Component: obslog.ComponentDeletionWorker,
					Operation: "sweep", Outcome: obslog.OutcomeSuccess, CorrelationID: correlationID,
					Count: obslog.Int64Ptr(int64(receipt.DeletionEpoch)),
				})
			}
			if err != nil && ctx.Err() == nil {
				recorder.RecordDeletionRetry(metrics.WorkerDeletion)
				recorder.RecordDeletionJob(metrics.WorkerDeletion, metrics.OutcomeFailure, metrics.FailDeletionRetry, time.Since(sweepStart))
				logger.Emit(obslog.Event{
					Severity: obslog.SeverityWarn, EventName: "deletion.retry",
					EventCode: obslog.EventDeletionRetry, Component: obslog.ComponentDeletionWorker,
					Operation: "sweep", Outcome: obslog.OutcomeFailure, CorrelationID: correlationID,
					Retryable: obslog.BoolPtr(true), FailureClass: obslog.FailureDeletionRetry,
				})
			}
			// A stuck account means a user asked to be deleted and is not being,
			// so it is reported as counts every cycle until it clears. The
			// counts carry no identifier.
			backlog, backlogErr := worker.Backlog(ctx)
			switch {
			case backlogErr != nil && ctx.Err() == nil:
				logger.Emit(obslog.Event{
					Severity: obslog.SeverityWarn, EventName: "deletion.backlog_unreadable",
					EventCode: obslog.EventDeletionBacklog, Component: obslog.ComponentDeletionWorker,
					Operation: "backlog", Outcome: obslog.OutcomeFailure, CorrelationID: correlationID,
					FailureClass: obslog.FailureDatabaseUnavailable,
				})
			case backlogErr == nil && !backlog.Healthy():
				recorder.SetDeletionBacklog(int(backlog.Stuck))
				recorder.RecordDeletionTerminalFailure(metrics.WorkerDeletion)
				logger.Emit(obslog.Event{
					Severity: obslog.SeverityError, EventName: "deletion.backlog_stuck",
					EventCode: obslog.EventDeletionBacklog, Component: obslog.ComponentDeletionWorker,
					Operation: "backlog", Outcome: obslog.OutcomeFailure, CorrelationID: correlationID,
					Count: obslog.Int64Ptr(backlog.Stuck), FailureClass: obslog.FailureDeletionTerminal,
				})
			}
		}
	}
}

// appleSessionIssuer adapts authstore.Store to appleauth.SessionIssuer.
type appleSessionIssuer struct{ store authstore.Store }

func (a appleSessionIssuer) Issue(ctx context.Context, accountID string, accountEpoch int64, authority security.Authority, ttl time.Duration) (string, error) {
	return a.store.IssueForApple(ctx, accountID, accountEpoch, authority, ttl)
}

// buildAppleLogin assembles the Apple login service from environment
// credentials. It returns (nil, nil) when unconfigured, which leaves the
// endpoint unavailable rather than blocking startup. The .p8 bytes are read,
// parsed, and dropped inside this function; only the parsed key is retained.
func buildAppleLogin(sessions authstore.Store, pool *pgxpool.Pool) (httpapi.AppleLoginService, error) {
	teamID := os.Getenv("MEMORY_OS_APPLE_TEAM_ID")
	keyID := os.Getenv("MEMORY_OS_APPLE_KEY_ID")
	clientID := os.Getenv("MEMORY_OS_APPLE_CLIENT_ID")
	keyPath := os.Getenv("MEMORY_OS_APPLE_PRIVATE_KEY_PATH")
	if teamID == "" || keyID == "" || clientID == "" || keyPath == "" {
		return nil, nil
	}
	keyBytes, err := os.ReadFile(keyPath)
	if err != nil {
		return nil, fmt.Errorf("read Apple private key: %w", err)
	}
	privateKey, err := appleauth.ParseP8PrivateKey(keyBytes)
	for i := range keyBytes {
		keyBytes[i] = 0
	}
	if err != nil {
		return nil, err
	}

	issuer := appleauth.DefaultIssuer
	verifier := &appleauth.Verifier{
		Issuer:      issuer,
		Audiences:   map[string]struct{}{clientID: {}},
		ClockSkew:   2 * time.Minute,
		MaxTokenAge: 10 * time.Minute,
		Keys:        appleauth.NewAppleJWKSClient(nil),
		Codes: appleauth.TokenClient{
			Endpoint: "https://appleid.apple.com/auth/token",
			Issuer:   issuer,
			ClientSecret: appleauth.ClientSecretConfig{
				TeamID: teamID, KeyID: keyID, ClientID: clientID, PrivateKey: privateKey,
			},
		},
		Replay:   appleauth.PostgresReplayGuard{Pool: pool},
		Accounts: appleauth.PostgresAccountBindingStore{Pool: pool, IDs: cryptoids.Generator{}},
	}
	return appleauth.LoginService{
		Verifier:   verifier,
		Sessions:   appleSessionIssuer{store: sessions},
		SessionTTL: 24 * time.Hour,
		Authority:  security.AuthorityIOSUser,
	}, nil
}

// buildRateLimit assembles the rate-limit enforcer from environment
// configuration. The trusted-proxy list defaults to empty (trust no proxy, use
// the transport peer); a deployment behind a proxy sets it explicitly. The
// HMAC secret keys the derived network keys; without one set, a per-process
// random secret is used so keys are still unlinkable across restarts. The
// in-memory store is single-instance only and is not distributed enforcement.
func buildRateLimit() (httpserver.RateLimitConfig, error) {
	trusted, err := ratelimit.ParseTrustedProxies(os.Getenv("MEMORY_OS_TRUSTED_PROXIES"))
	if err != nil {
		return httpserver.RateLimitConfig{}, fmt.Errorf("parse trusted proxies: %w", err)
	}
	secret := []byte(os.Getenv("MEMORY_OS_RATELIMIT_SECRET"))
	if len(secret) == 0 {
		secret = make([]byte, 32)
		if _, err := rand.Read(secret); err != nil {
			return httpserver.RateLimitConfig{}, fmt.Errorf("generate rate-limit secret: %w", err)
		}
	}
	primary := ratelimit.NewMemoryStore(200_000, 10*time.Minute)
	fallback := ratelimit.NewMemoryStore(50_000, 10*time.Minute)
	enforcer, err := ratelimit.NewEnforcer(primary, fallback, ratelimit.DefaultPolicies())
	if err != nil {
		return httpserver.RateLimitConfig{}, fmt.Errorf("build rate-limit enforcer: %w", err)
	}
	return httpserver.RateLimitConfig{
		Enforcer: enforcer,
		Deriver:  ratelimit.KeyDeriver{Secret: secret, TrustedProxies: trusted, IPv6PrefixBits: 64},
	}, nil
}
