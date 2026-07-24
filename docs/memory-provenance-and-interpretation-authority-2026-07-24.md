# Memory Provenance and Interpretation — Architecture Checkpoint

最終更新: 2026-07-24

## Verdict

```txt
Memory-domain invariants: FORMALIZED AS MACHINE-READABLE CONTRACT
Rich Memory domain:       NOT IMPLEMENTED, DELIBERATELY
PostgreSQL / Go / HTTP:   UNCHANGED BY THIS CHECKPOINT
Apple code exchange:      STILL THE SOLE nextRequired
production:               NO-GO
```

This checkpoint adds no table, no column, no endpoint and no runtime behaviour.
That is the intended outcome, not a shortfall.

## The finding that reframed this work

The principles this checkpoint was asked to establish were, for the most part,
**already written down**. `docs/formal-invariants.md` has carried them for some
time:

| Principle | Already exists as |
|---|---|
| Memory needs provenance | INV-P0-001 Memory must have SourceRef |
| Interpretation is not fact | INV-P0-002 Interpretation is not fact |
| No life scoring | INV-P0-012 No life ranking fields |
| No persona reconstruction | INV-P0-018 No deceased speak-as |
| Third-party content is not the user's | INV-P0-013 |
| LLM output must be labelled | INV-P1-007 |
| Small records are first-class | INV-P2-001 |

`docs/trust-and-provenance.md` already defines `ProvenanceLevel`,
`SpeakerProvenance`, `InferenceType` and a list of forbidden inferences.

So the gap was never "the philosophy is missing". The gap is that **none of it
gates anything**. It is prose. An implementation can contradict every line and
the entire test suite still passes green — which is exactly what happened, as
the next section shows.

The work of this checkpoint is therefore *enforceability*, not authorship: a
machine-readable invariant set, semantic cases, and a validator that fails.

## Audit findings (Phase 1)

Each finding is a file and symbol, not an impression.

### F1 — `update_safe_fields` destroys both content and provenance (live)

`services/import-api/internal/pgrepo/apply.go`, `ApplyMaterializedPreview`:

```sql
UPDATE memory_os.memory_item m
 SET canonical_record = c.canonical_record,
     source_preview_id = c.preview_id,
     updated_at = now()
 FROM memory_os.preview_candidate c
 WHERE c.preview_id = $1
   AND m.fingerprint = c.canonical_record->>'fingerprint'
```

A re-import overwrites the stored record **in place** and repoints
`source_preview_id` at the new Preview. Nothing retains the previous content,
and nothing retains where the previous content came from. A correction and an
erasure are indistinguishable afterwards.

This violates INV-P0-002 in spirit and INV-MEM-003 explicitly. The policy name
is also misleading: it does not update "safe fields", it replaces the whole
canonical record.

**Not fixed in this checkpoint.** Fixing it changes Apply semantics, which
Architecture Gate condition 3 forbids. It is recorded as `currentlyViolatedBy`
on INV-MEM-003 and as GAP-MEM-005, so it cannot be lost.

### F2 — the canonical record carries no provenance of its own

`docs/schemas/memory-os-security/preview-canonical-record.v1.schema.json`
defines `recordType`, `sourceRow`, `title`, `occurredAt`, `url`, `text`,
`fingerprint`, `issues`. There is no origin, no adapter attribution, no notion
of who authored the content.

Provenance exists one level up, on `preview_ready`: `source_object_key`,
`source_object_version_id`, `source_checksum_sha256`, `adapter_id`,
`adapter_version`, `adapter_artifact_sha256`. So a chain does exist —
`memory_item → source_preview_id → preview_ready → object version` — but it is
**Preview-granular, not item-granular**, and F1 breaks it on update.

### F3 — the existing vocabulary cannot describe what the product already ingests

`ProvenanceLevel` has no value for content extracted from an imported document,
and none for deterministically derived content. The shipped pipeline produces
exactly those two things. Recorded as GAP-MEM-004.

### F4 — duplicate amplification is built into the current contract

`TrustScore.evidenceCount` counts evidence without requiring the pieces to have
distinct origins, and "Trust Decay and Update" raises confidence on repeated
appearance. Re-importing one export three times, or a repost of one original,
therefore reads as corroboration. Recorded as GAP-MEM-002 and GAP-MEM-003.

### F5 — `ProvenanceLevel` mixes two axes

`user_direct` is an origin. `cross_source_confirmed` is a corroboration state.
`ai_summary` is an origin. They are one enum, so a record cannot state where it
came from without also implying how well supported it is. Recorded as
GAP-MEM-001, and the reason this checkpoint introduces **two** axes rather than
extending the existing one.

### F6 — no supersession or correction structure exists anywhere

Neither the SQL migrations nor the Go packages contain any notion of
supersession, correction or revision. `docs/trust-and-provenance.md#source-conflict`
says contradictory records should be *presented* side by side, but nothing
stores the relationship. F1 is the direct consequence.

### F7 — no AI-output storage exists yet, which is the good news

Nothing in the schema stores model output today. The prohibition on promoting
it therefore constrains a greenfield rather than requiring a migration — which
is precisely why writing it down now is worth more than writing it later.

### F8 — deletion coverage is currently complete, and fragile

`sweep_deleted_account()` in migration 006 erases nine tables plus sessions.
No derived, index or interpretation table exists to be missed. Any table the
Memory domain adds must join that function in the same change; INV-MEM-010
states this and the existing deletion test is the place to prove it.

### F9 — export has prose requirements and no machine-readable contract

`docs/trust-and-provenance.md#export-requirements` requires provenance and trust
in exports. There is no export schema in `docs/schemas/memory-os-security/`.
Out of scope here; noted so it is not mistaken for done.

### F10 — nothing in this checkpoint touches the Apple path

No file under `services/import-api/internal/appleauth/`, no Apple fixture and no
`nextRequired` entry is modified. `nextRequired` remains
`["implement_apple_code_exchange"]`.

## What was formalized (Phase 2)

Two axes, deliberately separate — see F5.

**Origin** (where content came from): `firsthand`, `service_record`,
`secondhand`, `imported_document`, `derived`, `ai_summary`, `ai_inferred`.
Each carries `canBecomeUserFact` and `requiresSourceRef`, and each maps onto the
existing `ProvenanceLevel` where one exists, with the gaps named where none does.

**Assertion** (what kind of claim it makes): `record`, `later_interpretation`,
`correction`, `ai_view`. Each carries `supersedable` and
`coexistsWithContradiction`, so "a life is allowed to disagree with itself
across years" is a property of the contract rather than a hope.

Twelve invariants, `INV-MEM-001` … `INV-MEM-012`, each naming the existing
invariant it derives from. An invariant with no ancestor would be a new product
decision smuggled in as a restatement, and the validator rejects an empty
ancestor list.

### Deliberately not named

`MemorySource`, `SourceArtifact`, `MemoryAssertion`, `MemoryInterpretation`,
`MemoryRelation`, `PresentationPreference` were all offered as candidate nouns.
None is adopted here. `MemoryInterpretation` and `SourceRef` **already exist**
in `docs/formal-invariants.md`, and inventing parallel nouns before the domain
is built is how a vocabulary forks. Naming is deferred to the migration that
actually needs it.

Likewise INV-MEM-007 states that storage, search, analysis, resurfacing and
Town display are separate permissions, and explicitly refuses to say what
structure represents them — while denying the one shape already known to be
wrong (a single boolean, MEMCASE-017).

## Architecture Gate assessment

Ten conditions had to hold before any implementation. Condition 10 —
*implementation must be needed by the current vertical slice, not merely
possible* — **does not hold**. The current slice is Capture/Import, its blocker
is Apple code exchange, and nothing in it requires a rich Memory domain today.

Conditions 8 and 9 also weigh against implementing: the boundaries between
source, event, assertion, interpretation and relation are genuinely unsettled,
and fixing them in DDL now would be the most expensive kind of guess.

**Therefore Commit B is not created.** Design-only is the correct completion of
this scope, not a partial one.

## Future migration plan

When the Memory domain is built — after Apple code exchange and the iOS
vertical slice, not before — it should proceed in this order:

1. **Provenance envelope first.** An append-only artifact/source table with
   origin, carrying the chain `item → source → artifact → object version` at
   item granularity, closing F2. No behaviour change to Apply.
2. **Assertion kind second.** Adding assertion to stored items makes INV-MEM-001
   testable in SQL rather than by review.
3. **Supersession third.** A link table, which lets F1 be fixed properly:
   `update_safe_fields` becomes a new item superseding the old, and stops being
   a destructive UPDATE.
4. **Presentation policy last**, once real resurfacing surfaces exist to say
   what the permissions actually are.

Every step adds its tables to `sweep_deleted_account()` and extends
`test_memory_os_deletion_fencing.sql` in the same change (INV-MEM-010), and
carries owner and epoch under the same FORCE RLS predicates as every existing
table (INV-MEM-012).

## Verification actually run

- `scripts/validate-memory-os-memory-provenance.py`: 12 invariants, 5 gaps,
  18 semantic cases (6 allow / 12 deny) — PASS.
- The validator was **proved to fail**: flipping MEMCASE-002 to allow an AI
  summary stored as a record produced
  `FAIL MEMCASE-002: expected allow, denied with MEM_AI_ORIGIN_CANNOT_BE_RECORD`,
  exit 1. The mutation was reverted.
- Every deny reason is required to be exercised by at least one case, so the
  vocabulary cannot drift into aspiration.
- Existing suites re-run unchanged; results recorded in the checkpoint commit.

## Not done, and not claimed

- No migration, no Go type, no HTTP surface, no iOS, no Town.
- No AI summary generation, emotion analysis, importance scoring, clustering,
  relation inference or persona simulation. This checkpoint adds the boundary
  those features may not cross; it does not bring them closer.
- F1 remains unfixed in shipped code, by gate decision, and is recorded rather
  than resolved.
- Export provenance (F9) has no machine-readable contract.
- Apple code exchange remains untouched and remains the sole `nextRequired`.
