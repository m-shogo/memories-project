# Import / Export Eligibility Matrix

## 目的

この文書は、Memory OS に入ってくるデータについて、Importしてよいか、Exportしてよいか、再Importしてよいかを横断的に判定するためのmatrixである。

特に追加で注意する対象:

- 画像
- スクリーンショット
- EXIF/位置情報
- 他の人格
- AIキャラ/ロールプレイ
- 実在人物の文体/会話ログ
- 故人/家族/恋人の人格化材料

## 最上位原則

### 1. Import allowed does not imply Export allowed

Importできるものでも、Exportしてよいとは限らない。

### 2. Export allowed does not imply Re-import allowed as same meaning

Exportしたものを再Importする場合、同じ意味で戻せるとは限らない。

例:

- raw LINE export → 再Import時はsummary-only/default excluded
- persona bundle → 再Import時はsimulationAllowed=false
- image archive → 再Import時はEXIF stripped/default sensitive

### 3. Raw and derived must be separated

Exportする場合、raw本体、safe summary、metadata、thumbnail、sourceRefを分ける。

### 4. The destination matters

ユーザー自身のbackup用Exportと、別AI/別サービスに渡すExportはリスクが違う。

Memory OSは危険なdestination-specific automationをしない。

## Eligibility Modes

```ts
type ImportEligibility =
  | 'allow'
  | 'allow_metadata_only'
  | 'allow_summary_only'
  | 'allow_owner_sensitive'
  | 'allow_restricted'
  | 'preview_only'
  | 'deny';

type ExportEligibility =
  | 'include_default'
  | 'exclude_default'
  | 'requires_explicit_selection'
  | 'requires_reauth_and_review'
  | 'metadata_only'
  | 'summary_only'
  | 'deny';

type ReimportEligibility =
  | 'allow_as_new_source'
  | 'allow_with_tombstone_check'
  | 'allow_metadata_only'
  | 'allow_summary_only'
  | 'allow_restricted_no_activation'
  | 'deny';
```

## Cross-domain Matrix

| Data kind | Import | Export | Re-import | Key condition |
|---|---|---|---|---|
| low-risk manual memory | allow | include_default | allow_with_tombstone_check | source/date/provenance |
| hobby title list | allow | include_default | allow_with_tombstone_check | no private flags |
| streaming watch history | allow_owner_sensitive | exclude_default | allow_with_tombstone_check | shared profile warning |
| music listening history | allow_owner_sensitive | exclude_default | allow_with_tombstone_check | recent/current listening sensitive |
| restaurant saved list | allow_owner_sensitive | exclude_default if location/date present | allow_with_tombstone_check | no relationship inference |
| LINE/chat raw | allow_summary_only | deny/default excluded | allow_summary_only | third-party raw risk |
| private bookmark | allow_owner_sensitive | exclude_default | allow_with_tombstone_check | title redaction/log ban |
| personal photo | allow_owner_sensitive | requires_explicit_selection | allow_with_tombstone_check | EXIF stripped |
| photo with other people | allow_restricted | exclude_default | allow_restricted | faces/consent risk |
| minor photo | allow_restricted | deny/default excluded | allow_restricted | guardian/legal policy |
| chat screenshot | allow_summary_only | deny/default excluded | allow_summary_only | OCR off/raw denied |
| medical/financial document image | allow_restricted | deny/default excluded | allow_restricted | sealed suggestion |
| manga/comic page image | allow_metadata_only | deny | allow_metadata_only | copyright/content rights |
| catalog cover art | allow_metadata_only | metadata_only/reference | allow_metadata_only | use URL/reference |
| fictional character notes | allow | requires_explicit_selection | allow_restricted_no_activation | fiction only |
| roleplay chat logs | allow_owner_sensitive | exclude_default | allow_restricted_no_activation | no dependency loop |
| AI companion logs | allow_restricted | exclude_default | allow_restricted_no_activation | no AI lover continuation |
| character card | allow_owner_sensitive | exclude_default | allow_restricted_no_activation | no agent activation |
| real person writing style | allow_restricted | deny | allow_restricted_no_activation | no imitation |
| deceased person records | allow_restricted | deny/default excluded | allow_restricted_no_activation | no deceased simulation |
| partner/family persona data | allow_restricted | deny/default excluded | allow_restricted_no_activation | no speak-as |
| OAuth token/API key | deny as memory | deny | deny | secret material |
| raw exported archive from another app | preview_only | not applicable | classify before commit | no automatic trust |

## Export Package Classes

```ts
type ExportPackageClass =
  | 'metadata_export'
  | 'standard_memory_export'
  | 'sensitive_summary_export'
  | 'media_archive_export'
  | 'raw_archive_export'
  | 'persona_like_export'
  | 'sealed_export';
```

Rules:

- metadata_export: lowest risk, still source/provenance checked.
- standard_memory_export: no raw/sealed/private by default.
- sensitive_summary_export: explicit selection and review.
- media_archive_export: reauth + EXIF/face/minor checks.
- raw_archive_export: Export Safety ceremony.
- persona_like_export: usually denied or excluded by default.
- sealed_export: requires sealed unlock + export ceremony.

## Re-import Rules

When importing a Memory OS export or another app export:

1. treat export file as hostile input.
2. run Security Gate.
3. detect package class.
4. check export manifest provenance.
5. check deletion tombstones.
6. check persona/media flags.
7. do not restore raw/sealed/private by default.
8. create Import Preview.
9. user confirms scope.

## Re-import Does Not Bypass Policy

Even if a file came from Memory OS, re-import must not bypass policy.

Examples:

- deleted records remain excluded by tombstone.
- sealed records remain sealed/excluded by default.
- persona bundles do not activate agents.
- image EXIF remains stripped by default.
- raw LINE remains summary-only/default excluded.

## Manifest Requirements for Memory OS Exports

A Memory OS export manifest should include:

```ts
interface ExportManifest {
  exportVersion: string;
  createdAt: string;
  packageClass: ExportPackageClass;
  containsRaw: boolean;
  containsMedia: boolean;
  containsSealed: boolean;
  containsThirdPartyRaw: boolean;
  containsPersonaLikeData: boolean;
  containsMinorData: boolean;
  sourcePolicyVersion: string;
  recordCount: number;
  redactionSummary: Record<string, number>;
}
```

The manifest itself must not contain raw private titles or chat text.

## Dangerous Combos

Deny or require strongest review:

- media + minor + raw export
- persona + deceased + raw export
- LINE raw + export package
- private bookmarks + raw URL list export
- AI companion logs + persona export
- sealed records + one-click export
- restore backup without tombstone replay
- export package without TTL

## P0 Tests

1. Import allowed image with EXIF exports without GPS by default.
2. Chat screenshot imports summary-only and raw export denied.
3. Persona-like import cannot be exported as agent bundle.
4. Memory OS export re-import does not bypass tombstones.
5. Sealed records in export are excluded unless explicit sealed flow.
6. Minor media remains excluded from standard export.
7. Character card re-import sets simulationAllowed=false.
8. Raw archive export requires re-auth/review.
9. Export manifest contains flags but not raw private titles.
10. OAuth/API secrets cannot be imported/exported as memory.

## 結論

Memory OSでは、Import/Export/Re-importを同じ許可で扱わない。

画像や人格データは、ImportできてもExportできない、Exportできても再Import時に安全な意味へ落とす必要がある。

特に画像、LINE/DM、未成年、第三者、故人、AIキャラ、他人の文体、Character card は、常に Export default excluded / Re-import reviewed / no activation を基本にする。
