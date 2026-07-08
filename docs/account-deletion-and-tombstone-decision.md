# Account Deletion and Tombstone Decision

## 目的

「レコード削除」と「アカウント削除」は別物である。

この文書は、削除の各モードでtombstone / raw / token / export package / backupがどうなるかを、実装前に固定する決定メモである。

Status: **draft decision — production前にproduct/legal最終承認が必要(P0-DB-013)**。ただし実装エージェントはこのdraftに反する削除実装をしてはならない。

## Modes

```ts
type AccountDeletionMode =
  | 'delete_records_keep_nonreversible_tombstones'
  | 'full_erasure_with_no_reimport_guard'
  | 'legal_hold_restricted';
```

## Record Deletion (アカウントは残る)

Default behavior:

1. `lifecycle_state = pending_delete` → 即時にsearch/Tip/export/preview候補から除外。
2. 非同期削除がbody/raw/derivedを消し、`deleted` へ。
3. `deletion_tombstone` を作成(HMAC key_hashのみ、`reason_code` は管理語彙)。
4. search_document / embedding_record / Tip cache / export stagingをinvalidate。外部vector storeも削除。
5. raw_object_refの対象objectを削除またはTTL即時化。
6. 再import時、tombstone一致candidateはデフォルト非選択(excluded)。ユーザーが明示的に復活を選ぶことはできる(本人の意思が優先)。

Tombstoneは削除内容を復元・推測できない形でのみ保持する。

## Account Deletion (アカウントごと消す)

Default mode decision (draft): **full_erasure_with_no_reimport_guard**

理由: アカウント削除ユーザーは再importの対象外であり、reimport guardの価値より「復元可能な個人データを残さない」期待が勝つ。

手順:

1. 全connectorのprovider token revoke(可能なもの)。
2. oauth_connection ciphertext削除 + `oauth_token_encryption` 鍵のuser scope分をcrypto-erasure対象に。
3. raw objectsの削除およびraw_object_encryption鍵のcrypto-erasure。
4. domain rows削除(source_ref〜memory系すべて)。
5. tombstone処理: 該当userの `dedupe_hmac` / `tombstone_hmac` 鍵を破棄することでkey_hashを非可逆な無意味データ化(crypto-erasure)した上で、行自体も削除する。匿名集計が必要なら件数のみ別途保存。
6. export packageの失効・削除。アカウント削除後も生きるexport URL/keyを残さない。
7. audit_eventは個人内容を含まない前提(SafeMetadataGuard)なので、法的要件の範囲で保持可。user_idは仮名化IDへ置換するかどうかをlegalで確定する。
8. background job / scheduled syncが削除後に走らないことをテストで保証。

`legal_hold_restricted` は法的保全要求があるときのみ。通常UIからは選べない。

## Backup / Restore Interaction

- backupには削除前データが残りうる。restore後は必ず**tombstone replay + account deletion replay**を行う。
- replay手順: restore → deletion_tombstoneを再適用 → アカウント削除ログ(削除済みuser idの管理リスト)を再適用 → search/embedding再構築はその後。
- replayが定義されていない環境へのrestoreは禁止。
- backupはunwrapped keyを含まない。crypto-erasure済みデータはrestoreしても復号不能であること。

## Restore Drill (production必須)

1. records作成 → 一部削除 → tombstone作成。
2. アカウント1件削除。
3. backup取得 → staging restore。
4. tombstone replay + account deletion replay実行。
5. 削除レコードが検索/export/preview候補に出ないことを検証。
6. 削除アカウントのデータが一切復元されないことを検証。

## Open Questions for Legal/Product (production前に確定)

- audit_eventのuser_id保持期間と仮名化方式。
- 課金記録等、法的保持義務データの分離保管方法。
- 未成年アカウント削除の追加要件(`docs/minor-and-family-policy.md` と整合)。

## 結論

削除は「行を消す」ではなく「復活経路と復元経路をすべて閉じる」こと。

tombstoneはprivacyを守るための道具であり、それ自体が漏えい源にならないよう、HMAC + crypto-erasureで管理する。
