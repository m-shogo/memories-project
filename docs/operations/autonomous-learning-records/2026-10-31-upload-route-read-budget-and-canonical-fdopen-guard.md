# Supplemental OPS learning — bounded upload-route reads and canonical fdopen ownership (2026-10-31)

Append-only operational learning under `contracts/operations/autonomous-learning-system.json`. This record is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered/eligible environment generation, recovery objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure A — latent unbounded Upload Route authority read

- **symptom:** The pinned regular-file reader could keep accumulating bytes while a concurrently growing authority file supplied more data. The reader checked size/mtime/ctime only after reaching EOF; no bounded allocation or read-count ceiling existed. This is a source-verified latent resource-exhaustion risk, not an observed production outage.
- **evidence:** At exact parent `ccbc92ac9177ce8b5245300aef398ae66712e23b`, `read_regular_bytes` used repeated 1 MiB `os.read` calls and `chunks.append(chunk)` without a maximum byte budget. The repository tree's largest current broad-scan source is below 8 MiB (the canonical learning file is about 4.17 MiB and already excluded from Upload Route rewrite/snapshot scope). The disposable test constructs a sparse 8 MiB+1-byte authority and a 9-chunk synthetic growing read.
- **rootCauseOrUnknown:** Verified missing size preflight and cumulative read budget; whether an adversary can concurrently grow a real authority in the runner is unknown.
- **failedApproach:** Assuming a regular-file type check and final metadata comparison bound memory consumption or guarantee timely EOF.
- **correction:** [`b1dd789f`](https://github.com/m-shogo/memories-project/commit/b1dd789f4d9e2378d91e50f0edbe9351cf9897ee) adds an explicit 8 MiB preflight size ceiling and cumulative streamed-byte ceiling, rejecting oversized authorities before snapshot acceptance or publication.
- **recurrenceGuard:** A disposable negative tests a sparse oversized input and a nine-chunk growing stream, confirms exact fail-closed rejection, unchanged original bytes and recovery on the next valid read. The already CI-reachable entry-document validator AST-requires a single direct proof call, both bound comparisons and the reviewed limit; three source mutations independently remove or inflate those predicates and must be rejected.
- **retryCondition:** Reassess only if the reviewed maximum authority size, read transport, source inventory or actual CI proof topology changes. A legitimate file exceeding 8 MiB requires a separately reviewed budget change and fresh negative/positive CI, not silent acceptance.

## Material failure B — canonical learning validator descriptor acquisition leak

- **symptom:** `read_canonical_authority_bytes` opened a raw descriptor and immediately used `with os.fdopen(fd, "rb")`. If stream construction raised before returning, the raw descriptor had no owner to close it. This was a source-proven latent exceptional-path leak, not an observed production leak.
- **evidence:** The previous `b1dd789f` version lacked cleanup between `os.open` and successful `fdopen`. The existing Upload Route fdopen-ownership learning record documented the same failure mechanism in a distinct writer. The new disposable canonical negative captures the actual descriptor, injects `fdopen` failure, requires the existing exact unreadable-authority diagnostic, then checks `os.fstat` fails with `EBADF`.
- **rootCauseOrUnknown:** Verified descriptor ownership-transfer gap; actual production frequency is unknown.
- **failedApproach:** Assuming a context manager closes a descriptor even when its stream acquisition expression fails.
- **correction:** [`04b4fc46`](https://github.com/m-shogo/memories-project/commit/04b4fc46e5832925068abc2bc8552fea00cbdd18) explicitly closes the untransferred descriptor on acquisition failure, tolerating only an already-closed descriptor error and preserving the original exception.
- **recurrenceGuard:** The existing directly invoked canonical descriptor negative now injects acquisition failure, asserts exactly one captured FD, `EBADF`, unchanged source bytes and a subsequent valid read. It runs inside the 601-case canonical fail-closed CI chain.
- **retryCondition:** Revisit when canonical reader ownership, stream construction, error translation, or negative execution reachability changes. Do not repeat the previously documented unchecked fdopen ownership assumption.

## Material prewrite failure — ambiguous source replacement avoided before publication

- **symptom/evidence:** The first detached patch preparation aborted with `proof names count 2` because a broad literal occurred in both the proof-name tuple and a later transport classification. No Git blob, tree, commit or branch mutation occurred in that attempt.
- **rootCauseOrUnknown:** Verified ambiguous source-span selection, matching the earlier learned class of unscoped literal mutations.
- **failedApproach:** Using an unqualified whole-source replacement marker as a unique proof of the intended AST location.
- **correction:** Replaced it with a context-qualified, uniquely counted tuple span before staging the successful three-file commit.
- **recurrenceGuard:** Exact-occurrence prewrite assertions abort before any Git object creation; the committed AST-bound CI guard requires the new proof and actual transport. This prewrite assembly itself was not installed as a repository CLI.
- **retryCondition:** If the proof tuple topology changes, inspect the current AST and establish a new unique contextual match; do not retry the broad duplicate marker.

## Material safe successes and protected authority

- **outcome:** Both scoped corrections landed on `so` without changing production or learning authorities. The first protects a bounded regular-file read and the second closes the canonical reader's exceptional descriptor ownership gap.
- **evidence:** [Autonomous Learning Guard #41179823162](https://github.com/m-shogo/memories-project/actions/runs/41179823162) **SUCCESS** on exact `b1dd789f`; [Autonomous Learning Guard #41180381585](https://github.com/m-shogo/memories-project/actions/runs/41180381585) **SUCCESS** on exact `04b4fc46`. Both completed append-only, contract, 601 canonical negatives, entry-document validation, independent helper-ancestor negative reachability (1,186 mutations), and clean/read-only checks. The latter log additionally reports 52 source-negative workflows, 63 Python commands, 204 fixtures and 195 fanout synthetics.
- **whySafe:** Only read-only Python authority/negative/entrypoint scripts were modified. The sparse-file, synthetic growth and descriptor-failure fixtures are disposable; no production reconciler, MinIO-dependent HTTP regression, credentials, traffic, recovery evidence or promotion was executed by these fixes.
- **reusableMechanism:** Couple descriptor-pinned reads to a fixed preflight/streaming budget, and make file-descriptor ownership transfer explicit across `fdopen`; test both exceptional boundaries with actual OS descriptors and CI-bound negative transports.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs remained unchanged after each code commit: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/drill-request/recovery-evidence/non-resurrection/promotion registries `bfd1b045`, `f4d74f33`, `acebcd02`, `ae7e57ef`, `26bb1cc7`, `99cb895f`. Learning records are not admission evidence.

## Scoped blockers and next safe targets

[Reconcile Upload Route Authority #41179823147](https://github.com/m-shogo/memories-project/actions/runs/41179823147) failed at the unchanged `Start local MinIO` step before the rollback and focused Go/HTTP tests; those tests are **not** claimed successful. Supplemental-learning-only Push/PR append-only trigger coverage and workflow write permission remain unresolved; no unchanged blocker was retried.

`productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/semantically eligible generations 0/0. Preflight requires unsuperseded semantically eligible generations from distinct environments and a current explicitly human-approved recovery objective. Reviewed drill requests remain planning-only; new generation recovery evidence must bind to a current executable reviewed request. Final production-equivalent candidates additionally require all existing generation/objective gates, complete typed eight-domain non-resurrection coverage and independent review; human promotion is separate and non-automatic.

Next safe targets: directory-fd/no-follow protection of Upload Route publication and rollback races; independent pre-MinIO Focused Go test execution; supplemental-only learning Push/PR append-only guard when workflow authority changes. No exact-source full production-admission SUCCESS is asserted for this learning-only commit.
