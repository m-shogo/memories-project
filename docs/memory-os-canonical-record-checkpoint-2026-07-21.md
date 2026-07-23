# Memory OS Canonical Adapter Record Contract Checkpoint

最終更新: 2026-07-21

## Verdict

```txt
canonical adapter record contract (schema + fixtures + validator):
CREATED AND MACHINE-VALIDATED (cross-language)

real Generic CSV adapter wired through the supervised worker:
CREATED AND LIVE-TESTED END TO END

executable server / clients:
NOT IMPLEMENTED

production:
NO-GO
```

The supervised import flow no longer decodes a placeholder record shape: every
frame a worker emits and every record the commit path decodes is now governed
by one reviewed, machine-validated contract, and the real Generic CSV adapter
runs inside the supervised worker end to end.

"Reviewed" here means what it has meant for every Round 9 contract: a
design-first schema with positive/negative fixtures and validators enforced in
CI. Independent human review remains a global production blocker.

## Implemented files

```txt
docs/schemas/memory-os-security/preview-canonical-record.v1.schema.json
docs/schemas/memory-os-security/preview-canonical-record-case-set.v1.schema.json
docs/fixtures/memory-os-security/preview-canonical-records.round9.v1.json
scripts/validate-memory-os-canonical-records.py
services/import-api/internal/canonrecord/   (encode / strict decode / fingerprint)
services/import-api/internal/csvworker/     (Generic CSV supervised worker)
services/import-api/internal/parsersup/frames.go (exported frame writers)
services/import-api/internal/importflow/flow.go  (contract-bound decode)
.github/workflows/security-contracts.yml    (validator step)
```

## The contract

One frame payload is exactly one JSON record in canonical Go `encoding/json`
serialization (fixed field order, compact separators, HTML escaping); the
payload bytes are authoritative and any other byte serialization is rejected.

```txt
candidate: recordType/recordVersion/sourceRow/title/occurredAt/url/text/fingerprint/issues
rejection: recordType/recordVersion/sourceRow/issueCodes
```

- `fingerprint` = SHA-256 of TrimSpace(title), occurredAt, TrimSpace(url),
  TrimSpace(text) joined by 0x1F — byte-identical to the genericcsv adapter
  formula, and recomputed on both encode and decode;
- `occurredAt` must round-trip through Go's RFC3339Nano UTC formatter (forces
  the `Z` suffix and canonical fractional seconds) or be empty;
- rejection records have no free-text fields: raw user values are structurally
  impossible;
- limits: title ≤ 4096 B, url ≤ 2048 B, text ≤ 1 MiB, ≤ 16 unique
  `IMPORT_[A-Z0-9_]+` codes, source row 1..100000, record ≤ 2 MiB (asserted
  equal to the spool limits by test);
- unknown fields, trailing data, `"issues":null`, reordered keys, added
  whitespace and unescaped HTML characters are all rejected.

## Cross-language enforcement

The shared fixture (4 accept / 12 reject_schema / 2 reject_semantic /
4 reject_encoding cases) is validated by **both** implementations:

- `scripts/validate-memory-os-canonical-records.py` re-derives the canonical
  encoding and fingerprint for every accept case and asserts each reject case
  fails for its declared reason (runs in the Security Contracts workflow);
- `internal/canonrecord`'s tests read the same fixture file: accept cases must
  round-trip DecodeRecord → Encode byte-for-byte, and every reject case must
  fail DecodeRecord.

A contract drift between Go and Python now fails a build instead of silently
diverging.

## Real adapter wiring

`internal/csvworker` is the supervised worker side of the Generic CSV adapter:
staged CSV on stdin → bounded synchronous genericcsv iterator → canonical
record frames on stdout. Options arrive as strict JSON via `MEMORY_OS_CSV_OPTIONS`
(unknown fields rejected; limits are not settable from the wire; date
locations restricted to UTC / Asia/Tokyo by the adapter). EncodeCandidate
recomputes the fingerprint, so any drift between the genericcsv fingerprint
and the contract fails the parse instead of sealing unverifiable records.

`internal/importflow` now decodes commit rows with `canonrecord.DecodeRecord`:
stream/type agreement (a rejection in the accepted stream is terminal),
strictly increasing per-stream source rows and global source-row uniqueness
are enforced on top of the record contract. The interim placeholder decode is
deleted.

The importflow end-to-end tests now push a real CSV file through the real
adapter under supervision — upload → HEAD recheck → version-pinned fetch →
supervised genericcsv parse → seal → independent verify → canonical decode →
atomic commit — with the seal's `optionsSha256` computed by the same
`NormalizeAndDigestOptions` binding production will use.

## Validation language

```txt
local golang:1.23 + postgres:16 + minio (fresh via scripts/dev-up.sh),
exact code HEAD c5bf48fda48e60c802349f6efd0e2ee50e0adea4:
gofmt clean + go vet + go test ./... + go test -race ./... (19 packages,
live DB/object-store/supervision/import-flow suites included)
+ non-race parsersup bounds + both 5s fuzz smokes PASS

scripts/validate-memory-os-canonical-records.py: PASS (22 cases)
scripts/validate-memory-os-security.py: PASS (26 schemas)

remote workflows:
recorded after the push completes
```

## Findings recorded during implementation

- genericcsv numbers physical file rows: the header is row 1, so the first
  data row is `sourceRow` 2 — the contract binds the adapter's numbering, and
  the fixture/tests encode it;
- a nil Go slice re-serializes as JSON `null`, which would have made
  `"issues":null` pass the canonical-equality check — the decoder now rejects
  nil issue arrays explicitly.

## Residual risks

- the worker artifact in tests is the re-executed test binary; a separately
  built, digest-pinned `cmd/` worker binary arrives with the CLI checkpoint;
- independent human review of all Round 9 contracts remains a production
  blocker;
- adapter options wire format is bound by digest but not yet its own reviewed
  JSON-schema contract (single consumer today: the supervisor spawn path).

## Immediate next task

```txt
minimal CLI harness over internal/importflow (first visible end-to-end run)
→ point it at a local CSV file and the scripts/dev-up.sh stack
→ print the committed Preview (candidates/rejections/counts) to the terminal
→ build the worker as a separate digest-pinned binary while doing so
```

Do not add HTTP-server or client wiring in that checkpoint.
