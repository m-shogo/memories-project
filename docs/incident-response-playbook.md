# Incident Response Playbook

## 目的

Incident Response Playbook は、Memory OS で漏洩・誤保存・誤Export・削除復活・LLM送信事故・管理者権限濫用・コスト攻撃が起きた時に、迅速に止血し、ユーザーの信頼を守るための運用設計である。

Memory OS は人生文脈を扱う。

事故時に「後で考える」では遅い。

## 最上位原則

### 1. Stop exposure first

原因究明より先に、漏洩・表示・LLM送信・Export・検索露出を止める。

### 2. Preserve evidence without raw spreading

調査に必要な証跡は残すが、raw private text や secrets をさらにコピーしない。

### 3. Respect deletion during incident

事故調査中でも、削除・封印・アクセス停止を尊重する。

### 4. Be honest with users

影響範囲・起きたこと・止めたこと・ユーザーが取れる行動を明確にする。

### 5. Add regression tests

事故は必ずテスト化し、再発防止する。

## Incident Categories

```ts
type IncidentKind =
  | 'secret_stored_or_exposed'
  | 'third_party_data_leak'
  | 'corporate_data_leak'
  | 'minor_data_exposure'
  | 'deleted_memory_resurrected'
  | 'hidden_or_sealed_memory_exposed'
  | 'wrong_export_content'
  | 'llm_policy_bypass'
  | 'embedding_visibility_bug'
  | 'admin_access_violation'
  | 'backup_restore_error'
  | 'cost_attack'
  | 'prompt_injection_policy_bypass'
  | 'raw_log_leak';
```

## Severity

```ts
type IncidentSeverity = 'low' | 'medium' | 'high' | 'critical';
```

### Critical

- secrets exposed
- raw third-party data exported/shared
- deleted/sealed data broadly exposed
- corporate confidential data sent to LLM/exported
- minor sensitive data exposed
- admin raw access abuse

### High

- hidden data surfaced to owner unintentionally
- raw logs captured internally
- LLM received data that should be masked
- export included restricted summary

### Medium

- cost attack contained
- incorrect warning missing
- wrong policy reason shown

### Low

- safe metadata display bug
- non-sensitive copy issue

## Incident Record

```ts
type IncidentRecord = {
  id: string;
  kind: IncidentKind;
  severity: IncidentSeverity;
  detectedAt: string;
  detectedBy: 'system' | 'user' | 'admin' | 'test' | 'vendor';
  affectedUsersEstimate: number;
  affectedEntityTypes: string[];
  containmentActions: string[];
  status: 'open' | 'contained' | 'investigating' | 'resolved' | 'postmortem_done';
};
```

IncidentRecord must not contain raw memory text.

## Immediate Response Checklist

### Universal first 15 minutes

1. Disable affected surface if needed.
2. Stop relevant jobs/queues.
3. Revoke export URLs if export involved.
4. Disable affected embeddings if search/vector involved.
5. Block LLM calls if policy bypass involved.
6. Snapshot safe metadata for investigation.
7. Create IncidentRecord without raw content.
8. Assign owner.

### Do not

- paste raw user content into issue tracker
- forward raw logs in Slack/email
- run ad-hoc LLM analysis on incident data
- restore from backup before tombstone review
- tell users “no issue” before confirmed

## Playbooks

## 1. Secret Stored or Exposed

Examples:

- API key stored in RawRecord
- secret appeared in search
- secret included in export

Containment:

```txt
block search/export for affected records
run secret scan on affected import job
redact or raw-delete secret records
create tombstones if needed
disable embeddings
revoke export URLs
rotate internal keys if internal secret
```

User communication:

- tell user secret-like data may have been stored/exposed
- recommend rotating affected external credentials if value may have been visible
- do not repeat secret value

Regression tests:

- add fixture with same pattern
- ensure store_raw/export/embedding deny

## 2. Third-party Data Leak

Examples:

- LINE other person's raw message exported
- family share included private detail

Containment:

```txt
revoke export/share links
block affected export mode
identify affected sourceRefs
redact third-party raw
switch memories to summary-only
notify affected user
```

Regression tests:

- third_party_private raw export deny
- show_raw_quote deny
- family share exclude

## 3. Corporate Data Leak

Examples:

- Slack raw embedded
- private repo code exported
- customer info stored

Containment:

```txt
disable source adapter
block search/export/LLM for sourceType
raw-delete affected records
create source tombstones
review logs for raw content
```

Regression tests:

- corporate raw store/LLM/export deny
- GitHub metadata-only
- Slack/Gmail blocked default

## 4. Deleted Memory Resurrected

Examples:

- re-import restored deleted content
- backup restore brought memory back

Containment:

```txt
set affected records pending_deletion
disable search/vector/export
replay tombstones
fix re-import guard
rebuild indexes
```

Regression tests:

- contentHash tombstone skip
- backup restore replay
- pending_deletion access block

## 5. Hidden / Sealed Memory Exposed

Examples:

- sealed memory in search result
- hidden memory in Tip
- sealed sent to LLM

Containment:

```txt
disable affected surface
mark embeddings disabled_by_visibility
rebuild search filters
review lifecycle helper
```

Regression tests:

- sealed search deny
- hidden tip deny
- sealed LLM deny

## 6. Wrong Export Content

Examples:

- hidden included in markdown
- redaction missing
- raw included by default

Containment:

```txt
revoke all affected export URLs
expire export jobs
patch export policy gate
regenerate safe package if needed
notify users who downloaded
```

Regression tests:

- hidden/sealed/deleted export exclude
- redaction report required
- raw default off

## 7. LLM Policy Bypass

Examples:

- corporate raw sent to LLM
- third-party secret sent unmasked
- prompt injection bypassed policy

Containment:

```txt
disable LLM worker
stop queued jobs
review payload logs without raw
notify vendor if required
update prompt boundary
add policy preflight check
```

Regression tests:

- send_to_llm policy preflight mandatory
- imported text treated as untrusted
- prompt injection fixture

## 8. Admin Access Violation

Examples:

- support admin viewed raw memory
- break-glass without approval

Containment:

```txt
revoke admin session
freeze admin access logs
notify security owner
identify accessed entity ids
notify affected users if required
rotate credentials if needed
```

Regression tests:

- support_admin metadata_only
- break_glass requires reason/scope/expiry/audit

## 9. Cost Attack

Examples:

- huge ZIP repeated
- repeated re-import to trigger LLM
- export generation spam

Containment:

```txt
rate-limit user/action
pause import/export jobs
require confirmation or credit
add dedupe/contentHash guard
```

Regression tests:

- huge archive partial
- repeated re-import dedupe
- medium+ confirmation

## Notification Policy

Notify users when:

- raw private data exposed outside intended boundary
- export included restricted data and may have been downloaded
- secret may have been visible
- deleted/sealed data was surfaced
- admin accessed raw unexpectedly
- LLM/vendor received policy-denied data

Do not notify for:

- fully contained low-risk metadata bug with no exposure
- false positive secret scan with no storage/exposure

## User Message Template

```txt
件名: Memory OS のデータ保護に関するお知らせ

何が起きたか:
<short factual explanation>

影響した可能性がある範囲:
<source/category/date range, no raw content>

すでに行った対応:
<revoked exports / disabled search / deleted raw / patched rule>

あなたが取れる対応:
<review export / rotate credentials / delete affected records>

再発防止:
<test added / policy fixed / monitoring added>
```

## Postmortem Template

```md
# Incident Postmortem: <id>

## Summary

## Timeline

## Impact

## Root Cause

## What Worked

## What Failed

## Containment

## User Communication

## Regression Tests Added

## Product/Policy Changes

## Open Follow-ups
```

Postmortem must not include raw user content.

## Monitoring Signals

- export job with unexpected raw count
- LLM job with denied riskClass
- search result containing sealed/deleted target
- embedding row active for hidden/sealed/deleted
- admin raw access attempt
- repeated huge imports
- secret scan positive after storage
- export URL used after expiry

## Acceptance Criteria

- Incident categories defined.
- Critical first actions documented.
- Each high-risk failure has containment steps.
- User notification template exists.
- Postmortem template exists.
- Regression test requirement explicit.
- Raw content prohibited in incident records.

## Non-goals

- Legal advice automation.
- Hiding incidents to protect metrics.
- Perfect prevention of user-side screenshots.
- Using incident data for product analytics.

## 結論

Memory OS は事故が起きない前提で作らない。

起きた時に、すぐ止める、rawを広げない、ユーザーに正直に伝える、必ずテストに戻す。

それが長期で信頼されるMemory OSの条件である。
