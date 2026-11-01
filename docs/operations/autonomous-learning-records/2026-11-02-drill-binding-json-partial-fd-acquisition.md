# Supplemental OPS learning — partially acquired JSON descriptor cleanup (2026-11-02)

Append-only operational learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure

- **symptom:** The new strict acquired-FD type/range guard had executable negative proof only when the *first* `os.open` returned an invalid value. It did not prove that an invalid intermediate ancestor or leaf result is rejected while previously acquired real FDs are closed exactly once.
- **evidence:** At HEAD `168fc372`, both readers validated every acquired FD before ownership, but the negative suite injected `None`, `True`, `-1`, `1.5` and `"7"` only at the first acquisition. No production FD leak or malformed syscall result was observed.
- **rootCauseOrUnknown:** Verified coverage gap for partial acquisition cleanup; actual runtime occurrence unknown.
- **failedApproach:** Treating initial-acquisition rejection as proof that later failures cannot leak or double-close earlier owned descriptors.
- **correction:** [`f93ed646`](https://github.com/m-shogo/memories-project/commit/f93ed646106c1130afeb7d3c207cf86e7055f8a7) adds intermediate-ancestor `True` and leaf `None` acquisition injections for both independent planning JSON readers, while tracking each successful real FD and each cleanup close.
- **recurrenceGuard:** The existing CI-reached binding negative suite requires the failure to occur at the intended acquisition ordinal, every previously acquired FD to close exactly once, no invalid/unowned/recycled FD close, and an external real-FD canary to survive. Existing invalid-first-open, parent/leaf swap, strict JSON and cleanup double-fault controls remain active.
- **retryCondition:** Revisit only if acquisition ordering, owned-FD cleanup, syscall result semantics or exact-source CI changes. Do not retry unchanged Quay MinIO HTTP 401, workflow permissions, external evidence or human promotion blockers.

## Material success

- **outcome:** Both planning JSON readers now have executable negative proof that partial acquisition failure preserves FD ownership boundaries and does not touch an external descriptor.
- **evidence:** Exact-source [Backup Restore Drill Generation Eligibility Binding #41342873578](https://github.com/m-shogo/memories-project/actions/runs/41342873578) completed **SUCCESS** at code HEAD `f93ed646`. Logs explicitly show `PASS pinned JSON: both readers reject leaf/parent symlink, hardlink, EOF, nonbytes and mutation, parent swap, cleanup double fault, invalid FD and partial acquisition; fragmented positive`, `Drill generation eligibility binding reconcile negative suite PASS` and `production decision: NO_GO`. This is CI validator evidence, not a non-skipped Go test or real restore.
- **whySafe:** Only the existing synthetic negative suite changed. All acquisitions and path mutations occur in disposable fixtures; no protected authority, production traffic, credential, workflow permission or promotion authority changed.
- **reusableMechanism:** Exercise invalid descriptor returns at root, intermediate and leaf acquisition stages; track already-owned real FDs and forbid duplicate or foreign cleanup, using an external canary.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs remain unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, Production Status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, recovery objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain `26bb1cc7`, promotion review `99cb895f`. Registered and semantically eligible unsuperseded generations remain separate; preflight requires distinct eligible environments and an explicitly human-approved current recovery objective; reviewed requests are planning-only; request-bound evidence, complete typed eight-domain non-resurrection, independent review and human promotion remain separate mandatory gates.

## Next safe target

Audit the remaining `run_negative_suite` and `run_post_validator` child execution path acquisition boundaries without changing workflow permissions. Seek an approved, non-skipped pre-MinIO Focused Go Test execution route independently; retain `NO_GO` until separate explicit human promotion authority exists.
