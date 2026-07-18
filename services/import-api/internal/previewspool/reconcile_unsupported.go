//go:build !linux

package previewspool

import (
	"context"
	"time"
)

type Reconciler struct{}

func NewReconciler(*Manager) (*Reconciler, error) {
	return nil, ErrUnsupportedPlatform
}

func (*Reconciler) Reconcile(context.Context, time.Time) (ReconcileReport, error) {
	return ReconcileReport{}, ErrUnsupportedPlatform
}
