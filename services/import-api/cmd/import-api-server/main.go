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
	"github.com/m-shogo/memories-project/services/import-api/internal/apply"
	"github.com/m-shogo/memories-project/services/import-api/internal/authstore"
	"github.com/m-shogo/memories-project/services/import-api/internal/cryptoids"
	"github.com/m-shogo/memories-project/services/import-api/internal/dbscope"
	"github.com/m-shogo/memories-project/services/import-api/internal/epochguard"
	"github.com/m-shogo/memories-project/services/import-api/internal/fenced"
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

	server := httpserver.NewHTTPServer(listen, httpserver.New(httpserver.Config{
		Sessions: sessions,
		Upload:   fenced.Upload{Guard: guard, Inner: uploadService},
		Preview:  fenced.PreviewRead{Guard: guard, Inner: previewService},
		Apply:    fenced.Apply{Guard: guard, Inner: applyService},
		Account:  accountdelete.Service{Repository: accountControl, Objects: objects, Guard: guard},
	}))

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
