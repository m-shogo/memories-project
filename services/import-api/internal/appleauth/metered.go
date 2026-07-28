package appleauth

import (
	"context"
	"errors"
	"time"

	"github.com/m-shogo/memories-project/services/import-api/internal/metrics"
	"github.com/m-shogo/memories-project/services/import-api/internal/security"
)

// This file adds the load-critical measurement boundaries on the Apple sign-in
// path. Each decorator wraps an existing collaborator and records a bounded,
// privacy-preserving metric: it never sees, and never records, an Apple
// subject, an authorization code, an identity token or a raw provider error —
// only a fixed outcome and failure-class enum. The mock and production paths
// pass through the same decorators, so a load test drives the real emission
// boundary even when Apple and the database are faked.

// loginPort is the LoginService surface the meter wraps. A separate interface
// keeps the meter usable over any equivalent login implementation.
type loginPort interface {
	Login(context.Context, Input) (LoginResult, error)
}

// MeteredLoginService records the Apple exchange outcome, its duration, session
// issuance and replay rejections around an inner login service. A nil recorder
// is tolerated by the metrics package (its methods are no-ops), so wrapping is
// always safe.
type MeteredLoginService struct {
	Inner    loginPort
	Recorder metrics.Recorder
}

func (m MeteredLoginService) Login(ctx context.Context, input Input) (LoginResult, error) {
	start := time.Now()
	result, err := m.Inner.Login(ctx, input)
	duration := time.Since(start)

	outcome := appleOutcome(err)
	failure := appleFailureClass(err)
	m.Recorder.RecordAppleExchange(metrics.ProviderApple, outcome, failure, duration)

	switch {
	case err == nil:
		m.Recorder.RecordSessionIssuance(metrics.OutcomeSuccess)
	case errors.Is(err, ErrSessionIssuance):
		// The identity verified but the session insert failed; that is a session
		// issuance failure, distinct from an auth rejection.
		m.Recorder.RecordSessionIssuance(metrics.OutcomeFailure)
	}
	if failure == metrics.FailReplay {
		m.Recorder.RecordAppleReplayRejection()
	}
	return result, err
}

// appleOutcome collapses a login error into the coarse metrics outcome. A
// rejected credential (bad token, replay, binding conflict, invalid request) is
// "rejected"; an unavailable dependency (Apple, the session store) is
// "failure"; success is success.
func appleOutcome(err error) metrics.Outcome {
	if err == nil {
		return metrics.OutcomeSuccess
	}
	switch appleFailureClass(err) {
	case metrics.FailExternalApple, metrics.FailDatabase, metrics.FailInternal:
		return metrics.OutcomeFailure
	default:
		return metrics.OutcomeRejected
	}
}

// appleFailureClass maps a login error to a fixed failure-class token. The
// residual (unclassified) case is treated as a replay rejection, mirroring the
// handler's fail-closed default where an unexpected error becomes a rejection
// rather than a retryable 500.
func appleFailureClass(err error) metrics.FailureClass {
	switch {
	case err == nil:
		return metrics.FailNone
	case errors.Is(err, ErrCredentialTooLarge),
		errors.Is(err, ErrMalformedToken),
		errors.Is(err, ErrDuplicateJSONKey),
		errors.Is(err, ErrNonceRequired),
		errors.Is(err, ErrSubjectRequired):
		return metrics.FailInvalidRequest
	case errors.Is(err, ErrAlgorithmForbidden),
		errors.Is(err, ErrKeyNotFound),
		errors.Is(err, ErrSignatureInvalid),
		errors.Is(err, ErrIssuerInvalid),
		errors.Is(err, ErrAudienceInvalid),
		errors.Is(err, ErrTokenExpired),
		errors.Is(err, ErrIssuedAtInvalid),
		errors.Is(err, ErrNonceMismatch),
		errors.Is(err, ErrCodeBindingMismatch),
		errors.Is(err, ErrTokenEndpointRejected),
		errors.Is(err, ErrTokenResponseMalformed):
		return metrics.FailAuthentication
	case errors.Is(err, ErrAccountBindingConflict):
		return metrics.FailAuthorization
	case errors.Is(err, ErrTokenEndpointUnavailable):
		return metrics.FailExternalApple
	case errors.Is(err, ErrSessionIssuance):
		return metrics.FailDatabase
	case errors.Is(err, ErrLoginUnavailable):
		return metrics.FailInternal
	default:
		return metrics.FailReplay
	}
}

// MeteredReplayGuard records the replay-consume database operation. The metric
// distinguishes only success from error; the semantic replay classification is
// carried by the Apple exchange metric, so no user material is needed here.
type MeteredReplayGuard struct {
	Inner    ReplayGuard
	Recorder metrics.Recorder
}

func (m MeteredReplayGuard) Consume(ctx context.Context, nonceClaim, authorizationCodeSHA256 string) error {
	start := time.Now()
	err := m.Inner.Consume(ctx, nonceClaim, authorizationCodeSHA256)
	m.record(err, time.Since(start))
	return err
}

func (m MeteredReplayGuard) record(err error, d time.Duration) {
	outcome, failure := metrics.OutcomeSuccess, metrics.FailNone
	if err != nil {
		outcome, failure = metrics.OutcomeFailure, metrics.FailDatabase
	}
	m.Recorder.RecordDBOperation(metrics.OpDBAppleReplayConsume, outcome, failure, d)
}

// MeteredAccountBindingStore records the account resolve-or-create database
// operation. A binding conflict is a rejection, any other error is a failure.
type MeteredAccountBindingStore struct {
	Inner    AccountBindingStore
	Recorder metrics.Recorder
}

func (m MeteredAccountBindingStore) ResolveOrCreate(ctx context.Context, issuer, subject string) (string, int64, error) {
	start := time.Now()
	accountID, epoch, err := m.Inner.ResolveOrCreate(ctx, issuer, subject)
	outcome, failure := metrics.OutcomeSuccess, metrics.FailNone
	switch {
	case errors.Is(err, ErrAccountBindingConflict):
		outcome, failure = metrics.OutcomeRejected, metrics.FailIntegrity
	case err != nil:
		outcome, failure = metrics.OutcomeFailure, metrics.FailDatabase
	}
	m.Recorder.RecordDBOperation(metrics.OpDBAppleIdentityUpsert, outcome, failure, time.Since(start))
	return accountID, epoch, err
}

// MeteredSessionIssuer records the session-insert database operation around an
// inner SessionIssuer.
type MeteredSessionIssuer struct {
	Inner    SessionIssuer
	Recorder metrics.Recorder
}

func (m MeteredSessionIssuer) Issue(ctx context.Context, accountID string, accountEpoch int64, authority security.Authority, ttl time.Duration) (string, error) {
	start := time.Now()
	token, err := m.Inner.Issue(ctx, accountID, accountEpoch, authority, ttl)
	outcome, failure := metrics.OutcomeSuccess, metrics.FailNone
	if err != nil {
		outcome, failure = metrics.OutcomeFailure, metrics.FailDatabase
	}
	m.Recorder.RecordDBOperation(metrics.OpDBSessionInsert, outcome, failure, time.Since(start))
	return token, err
}
