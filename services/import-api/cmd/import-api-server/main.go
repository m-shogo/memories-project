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
	"github.com/m-shogo/memories-project/services/import-api/internal/objectstore"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgrepo"
	"github.com/m-shogo/memories-project/services/import-api/internal/pgscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/previewread"
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

	server := httpserver.NewHTTPServer(listen, httpserver.New(httpserver.Config{
		Sessions:   sessions,
		Upload:     fenced.Upload{Guard: guard, Inner: uploadService},
		Preview:    fenced.PreviewRead{Guard: guard, Inner: previewService},
		Apply:      fenced.Apply{Guard: guard, Inner: applyService},
		Account:    accountdelete.Service{Repository: accountControl, Guard: guard},
		AppleLogin: appleLogin,
	}))

	// The deletion runtime drains accounts the API already fenced. It runs in
	// the same process for now, but it claims through the database lease, so
	// moving it to its own deployment later changes nothing about correctness.
	deletionWorker := accountdelete.Worker{
		Queue:      accountControl,
		Repository: accountControl,
		Objects:    objects,
	}
	go runDeletionRuntime(ctx, deletionWorker)

	errs := make(chan error, 1)
	go func() {
		fmt.Printf("import-api-server listening on %s\n", listen)
		errs <- server.ListenAndServe()
	}()

	select {
	case <-ctx.Done():
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
func runDeletionRuntime(ctx context.Context, worker accountdelete.Worker) {
	const interval = 30 * time.Second
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			receipts, err := worker.Sweep(ctx, 8)
			for _, receipt := range receipts {
				fmt.Printf("deletion runtime erased account at epoch %d (attempt %d)\n",
					receipt.DeletionEpoch, receipt.Attempts)
			}
			if err != nil && ctx.Err() == nil {
				fmt.Printf("deletion runtime sweep failed; account remains fenced and claimable\n")
			}
			// Counting retries was pointless while nobody read the count. A
			// stuck account means a user asked to be deleted and is not being,
			// so it is reported every cycle until it clears.
			backlog, backlogErr := worker.Backlog(ctx)
			switch {
			case backlogErr != nil && ctx.Err() == nil:
				fmt.Printf("deletion runtime could not read its backlog\n")
			case backlogErr == nil && !backlog.Healthy():
				fmt.Printf("ALERT deletion backlog: %d pending, %d stuck at >=%d attempts "+
					"(worst %d attempts, oldest pending %s)\n",
					backlog.Pending, backlog.Stuck, accountdelete.StuckAttemptsThreshold,
					backlog.MaxAttempts, backlog.OldestPending.Round(time.Second))
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
