# Supplemental OPS learning — closed post-validator label/path execution authority (2026-11-02)

Append-only operational learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, executable reviewed-request, request-bound recovery, typed eight-domain non-resurrection, independent-review, final-candidate or human-promotion evidence.

## Material failure 1 — generation-evidence post-validator self-consistent unreviewed target

- **symptom:** The generation-evidence reconcile helper could accept a repository-contained unreviewed executable when a caller supplied a self-consistent `path` and `expected_relative` pair.
- **evidence:** At parent `4e14bc11`, `scripts/reconcile-memory-os-backup-restore-generation-evidence.py` passed the caller's pair directly to `require_exact_repo_file` without a reviewed label/path allowlist. Canonical production call sites were unchanged; no actual unreviewed execution was observed.
- **rootCauseOrUnknown:** Verified helper-level self-referential expected-relative trust boundary; external exploitability in the approved workflow is unknown.
- **failedApproach:** Repository containment plus a caller-supplied matching expected-relative path was treated as reviewed child execution authority.
- **correction:** [`33138771`](https://github.com/m-shogo/memories-project/commit/33138771c51c5e8d2443363be5d97bb9bbed625e) closes the binding/evidence/operability validator label, absolute path and relative path triples before subprocess launch.
- **recurrenceGuard:** The existing CI-reachable generation-evidence reconcile negative suite now rejects an unknown label and a known label paired with the canonical contract JSON, with a subprocess canary that must not execute. Canonical positive targets and private bounded child transport remain covered.
- **retryCondition:** Revisit only after an explicitly reviewed child validator target or call-site authority change, or if exact-source CI exposes a regression. Do not repeat unchanged external MinIO/permission/evidence blockers.

## Material success 1 — generation-evidence reviewed target closure

- **outcome:** Generation-evidence child validation rejects self-consistent but unreviewed repository targets before execution.
- **evidence:** Exact-source [Backup Restore Generation Evidence Reconcile Negative #41320055097](https://github.com/m-shogo/memories-project/actions/runs/41320055097) completed **SUCCESS** at `33138771`. Git compare shows only the existing reconciler and negative test changed.
- **whySafe:** No production authority, registry, credential, traffic, reviewed workflow or promotion decision was modified; only executable helper admission and synthetic negative tests changed.
- **reusableMechanism:** Closed reviewed (label, path, expected-relative) allowlist before canonical identity and private subprocess checks.
- **protectedAuthorityCheck:** Ten protected blob SHAs unchanged after this commit. `productionDecision=NO_GO`; OPS-P0-007 remains blocked. Learning cannot satisfy any operational gate.

## Material failure 2 — drill-request post-validator label-only gate

- **symptom:** A known drill-request label could be paired with an arbitrary repository file as the subprocess target.
- **evidence:** At `33138771`, `scripts/reconcile-memory-os-backup-restore-drill-request.py` checked `label in ("drill request", "operability")` but did not constrain `path` in the child helper. Approved main() call sites remained canonical; no actual malicious invocation was observed.
- **rootCauseOrUnknown:** Verified label-only helper admission without canonical target binding. Reachability of an untrusted caller in approved CI is unknown.
- **failedApproach:** Treating a reviewed diagnostic label as sufficient to authorize any supplied child path.
- **correction:** [`fd298ed5`](https://github.com/m-shogo/memories-project/commit/fd298ed505551508b7e731abd6650e6d84173663) binds each label to its exact reviewed validator and verifies canonical lexical/resolved identity.
- **recurrenceGuard:** The existing drill-request reconcile negative suite now rejects an unknown label and a known label with a canonical but unreviewed contract path before any child process; canonical positive and bounded transport cases remain.
- **retryCondition:** Revisit only if reviewed drill/operability child paths or label authority change, or CI proves a regression.

## Material success 2 — drill-request reviewed target closure

- **outcome:** Drill-request post-validator execution now requires both a reviewed label and the corresponding canonical executable.
- **evidence:** Exact-source [Backup Restore Drill Request Reconcile Rollback #41320107953](https://github.com/m-shogo/memories-project/actions/runs/41320107953) completed **SUCCESS** at `fd298ed5`. Git compare shows only the reconciler and existing negative suite changed.
- **whySafe:** Production planning records, approvals, generation evidence and status were not modified; the helper and synthetic negative test are non-production.
- **reusableMechanism:** Strict label-to-target map plus canonical file identity check, rejecting mismatches before private subprocess execution.
- **protectedAuthorityCheck:** Ten protected blob SHAs unchanged. No new reviewed request, executable drill, recovery objective or production promotion was created.

## Material failure 3 — preflight post-validator repository fallback and cross-label substitution

- **symptom:** A non-reviewed repository file could reach the preflight post-validator through its fallback; a reviewed validator path could also be supplied with the wrong label.
- **evidence:** At `fd298ed5`, `scripts/reconcile-memory-os-backup-restore-drill-preflight.py` used `require_repo_file(path,...)` for unknown paths and selected canonical validators by path alone. Canonical main() calls were already reviewed; no real unreviewed execution was observed.
- **rootCauseOrUnknown:** Verified repository-containment fallback and path-only authority without a strict reviewed label/path pair. External caller reachability is unknown.
- **failedApproach:** Treating a repository-contained fallback or an unrelated label as sufficient for a preflight post-validation executable.
- **correction:** [`b0fcd853`](https://github.com/m-shogo/memories-project/commit/b0fcd853faa70642bd560c97a9e23fd3ebebf1ab) restricts execution to exact preflight/operability label-path pairs, retaining canonical source identity verification.
- **recurrenceGuard:** The existing preflight reconcile negative suite now rejects contract-as-validator, cross-swapped canonical labels and unknown labels with a no-subprocess canary. Reviewed preflight/operability positive paths remain in the existing reconciliation tests.
- **retryCondition:** Revisit only after reviewed post-validator topology changes or a reproducible exact-source negative failure.

## Material success 3 — preflight label/path closure

- **outcome:** Preflight reconciliation no longer permits repository-contained fallback or cross-label validator execution.
- **evidence:** Exact-source [Backup Restore Drill Preflight Reconcile Negative #41320182219](https://github.com/m-shogo/memories-project/actions/runs/41320182219) completed **SUCCESS** at `b0fcd853`, including compilation, rollback proof and read-only checks.
- **whySafe:** Only the existing reconciler and its CI-reachable negative suite changed; no workflow, production status, recovery registry, credential, traffic or approval was written.
- **reusableMechanism:** Exact reviewed label/path map with no fallback; negative test proves subprocess is never reached for rejected cases.
- **protectedAuthorityCheck:** Ten protected blob SHAs unchanged after the code commit. `productionDecision=NO_GO`; OPS-P0-007 remains blocked, with registered/eligible generations 0/0, approved objectives 0, executable requests 0, request-bound recovery evidence 0, complete typed eight-domain records 0 and final candidates 0.

## Reused material failure — stale source refused by drill admission publisher

- **symptom:** [Drill Request Admission #41320107970](https://github.com/m-shogo/memories-project/actions/runs/41320107970) finished **FAILED** at `fd298ed5` despite validator exit code 0.
- **evidence:** Job log shows the `Commit bounded drill planning authority` step fetched `origin/so` advancing from `fd298ed5` to `b0fcd853`, then refused publication with exit code 75 and the explicit stale-source diagnostic.
- **rootCauseOrUnknown:** Verified concurrent branch advancement invalidated exact-source authority. This is the previously recorded fail-closed source guard, not a regression in the reviewed post-validator code.
- **failedApproach:** Publishing derived drill authority from an outdated source HEAD would be unsafe.
- **correction:** Reuse the existing exact-HEAD guard and do not bypass it, force-push, or replay an unchanged stale publisher run.
- **recurrenceGuard:** Existing publisher compares current `origin/so` to the captured source SHA before publication; mismatch exits 75.
- **retryCondition:** Only after a fresh source-bound run on a stable HEAD, with reviewed authority and permissions unchanged. Do not retry the stale run or reinterpret its validator exit 0 as publisher SUCCESS.

## Protected authority and next safe target

The canonical learning and learning contract, production operability status, OPS-P0-007 snapshot, environment-generation, recovery-objective, drill-request, generation-evidence, typed eight-domain non-resurrection and promotion-review registries retain their ten pre-run Git blob SHAs. The production decision is **NO_GO** and all separate human production-promotion authority remains unsatisfied. Registered generations are not semantically eligible generations; preflight still requires unsuperseded eligible generations from distinct environments and an explicitly human-approved current objective. Reviewed requests are planning-only until executable, new recovery evidence stays request-bound, and final candidates require complete typed eight-domain coverage and independent review. Learning and CI are not production evidence.

Next audit remaining child-validator helper allowlists and malformed subprocess result handling without modifying reviewed workflows, protected authorities or the separate human promotion gate. Autonomous Learning Guard CI for the last code HEAD was still running at record preparation and is **not** claimed successful.
