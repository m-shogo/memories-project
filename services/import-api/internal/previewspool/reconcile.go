package previewspool

import "errors"

// ReconcileOutcome classifies what startup reconciliation did with one root
// entry. Quarantined entries were left untouched and require operator review;
// they are never recursively deleted.
type ReconcileOutcome string

const (
	ReconcileSealedKept           ReconcileOutcome = "sealed-kept"
	ReconcilePublicationCompleted ReconcileOutcome = "publication-completed"
	ReconcileUnsealedRemoved      ReconcileOutcome = "unsealed-removed"
	ReconcileExpiredRemoved       ReconcileOutcome = "expired-removed"
	ReconcileQuarantined          ReconcileOutcome = "quarantined"
)

type ReconcileEntry struct {
	Name    string
	Outcome ReconcileOutcome
	Detail  string
}

// ReconcileReport lists every root entry with its classification in
// deterministic name order. A report with only sealed-kept and
// publication-completed outcomes means the root holds nothing but trusted
// unexpired sealed attempts.
type ReconcileReport struct {
	Entries []ReconcileEntry
}

func (r ReconcileReport) Quarantined() []ReconcileEntry {
	var entries []ReconcileEntry
	for _, entry := range r.Entries {
		if entry.Outcome == ReconcileQuarantined {
			entries = append(entries, entry)
		}
	}
	return entries
}

var ErrReconcileInvalidInput = errors.New("invalid Preview spool reconciliation input")
