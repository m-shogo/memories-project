package httpserver

import (
	"context"
	"testing"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/authstore"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

// sustainedSoakRenewSession issues a fresh one-hour session for the already
// provisioned active soak account. It deliberately does not extend or mutate
// the original session: the long-soak recovery checkpoint must prove that the
// production one-hour TTL still expires and that the same long-lived server can
// accept new authenticated work after a normal re-authentication boundary.
func sustainedSoakRenewSession(t *testing.T, server *liveServer, owner string) string {
	t.Helper()
	issued, err := server.sessions.Issue(context.Background(), authstore.IssueInput{
		AccountID: owner,
		Epoch:     1,
		Authority: security.AuthorityIOSUser,
		TTL:       time.Hour,
	})
	if err != nil {
		t.Fatalf("renew sustained-soak session: %v", err)
	}
	return issued.Token
}
