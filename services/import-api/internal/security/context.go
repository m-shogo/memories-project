package security

import (
	"context"
	"errors"
)

var ErrMissingVerifiedPrincipal = errors.New("verified principal missing from context")

type principalContextKey struct{}

func WithPrincipal(ctx context.Context, principal Principal) (context.Context, error) {
	if err := principal.Validate(); err != nil {
		return nil, err
	}
	return context.WithValue(ctx, principalContextKey{}, principal), nil
}

func PrincipalFromContext(ctx context.Context) (Principal, error) {
	principal, ok := ctx.Value(principalContextKey{}).(Principal)
	if !ok || principal.Validate() != nil {
		return Principal{}, ErrMissingVerifiedPrincipal
	}
	return principal, nil
}
