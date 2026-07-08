# SafeMetadataGuard Spec

## 目的

`audit_event.metadata`、`outbox_event.payload`、`import_job.counts`、application log、queue message、admin/support UIは、raw private contentの漏えい経路になりやすい。

この文書は、これらの経路に書いてよいデータの契約(SafeMetadataGuard)を固定する。

これは仕様であり、実装(バリデータコード)はDB実装フェーズで行う。

## Invariant

```txt
Any JSONB / log / queue / admin-visible field must pass SafeMetadataGuard
before it is written.
```

Guardを通らない書き込み経路を作ってはならない。「開発中だけ生ログ」も禁止。

## Allowed (allowlist)

- UUID / 内部ID / target_table + target_id
- counts(件数、サイズ、duration)
- 管理された語彙のenum / reason code / error code class / status
- policy_version / parser_id / parser_version / adapter_version / key_version
- confidenceランク(high/medium/low)
- provider名(spotify等のサービス識別子)
- hash値(HMAC済み・algorithm/version明示のもの)
- timestamp / latency

## Forbidden (denylist)

- raw本文・snippet・quote(LINE/DM/Gmail/bookmark/メモ本文)
- private/restricted importのtitle・URL
- token / refresh token / API key / secretの断片
- query stringにtokenや個人識別子を含むURL
- 生filename(hash化前)
- EXIF / GPS raw
- ユーザー入力の自由記述テキスト全文
- tombstoneが指す削除済みコンテンツを推測できる値
- shared profileの他人の視聴/行動内容
- LLM生成のユーザー解釈文(人格・関係・感情の推定)

Titleの扱い:

- `privacy_level = owner_only` かつ export_default included のcatalog的title(公開作品名)でも、log/audit/outboxには原則入れない。preview UI表示とlog記録は別経路。

## Enforcement Points

1. audit_event書き込みヘルパー(唯一の書き込み口にする)
2. outbox_event publish関数
3. logger(structured loggingのfield filter)
4. queue producer
5. admin/support API response serializer
6. error message / exception message(DB制約違反メッセージ含む)

DB unique violation等のエラーをそのままユーザー/ログへ返すと存在漏えいになる。エラーはgeneric messageへ変換する。

## Test Cases

- SMG-001: private bookmark titleをauditへ書こうとすると拒否される。
- SMG-002: outbox payloadにraw textを含めるとpublishが失敗する。
- SMG-003: OAuth token文字列を含むlog fieldがマスクされる。
- SMG-004: dedupe conflictエラーが対象titleを含まない。
- SMG-005: support roleのAPI responseにtitle/body/rawフィールドが存在しない。
- SMG-006: import_job.countsに数値/enum以外の自由記述が入らない。
- SMG-007: 例外スタックトレースにdecrypted tokenが出ない。

## 結論

SafeMetadataGuardは「気をつける」ではなく、単一の書き込み口 + allowlist + テストで強制する。

これが存在しない限り、audit/outbox/logを書くコードを実装してはならない。
