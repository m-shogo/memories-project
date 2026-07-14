# Memory-first Capture Motivation Contract — Round 5

最終更新: 2026-07-14

## 目的

Memory Townと箱庭機能が魅力的になるほど、プロダクトが「記憶を残すアプリ」から「町を育てるゲーム」へ反転する危険がある。

本契約は、Memory OSの中心を次へ固定する。

```txt
記憶を残したい
→ 軽く保存できる
→ 自分の棚として整う
→ 後から探せる・続きを更新できる
→ 月や年で再発見できる
→ その副次的な結果として町が育つ
```

```txt
Memory is the product.
Town is the visible side effect.
```

実装はまだ開始しない。

---

# 1. Product priority order

プロダクト判断が衝突した場合、次の順を優先する。

```txt
1. Capture / Import
2. Retrieval / Search / Update
3. Privacy / Safety / Portability
4. Reflection / Resurfacing
5. Town visualization
6. Town customization / editor
```

Rules:

- Town機能を理由にCapture、Search、Exportを遅らせない
- Townを使わなくてもMemory OSの全主要機能へ到達できる
- TownはMemory Domainの正本にならない
- Town editorは記憶保存より強い主目的にならない
- Townだけのためのmandatory inputを追加しない

---

# 2. Correct motivation loop

望ましい動機は、報酬獲得ではなく次の5層で作る。

## 2.1 Capture friction reduction

ユーザーが実際に残したい瞬間を逃さない。

- 一行入力
- URL貼り付け
- Share Extension
- 写真・sourceの明示Import
- 漫画巻数、アニメ話数などの軽い進行更新
- 後から整理できるInbox
- 保存前Preview

Townのためのcategory、tag、建物選択、装飾選択を保存前に要求しない。

## 2.2 Immediate memory acknowledgement

保存直後に最初に見せるのはTown報酬ではなく、保存された記憶そのもの。

```txt
保存した内容
日付
source
入った棚
現在の進行
あとで探すための手掛かり
```

例:

```txt
PERFECT DAYS
映画棚へ保存しました
2026年7月14日
```

ユーザーが「何を、どこへ保存したか」を確認できることを最優先する。

## 2.3 Future utility promise

記憶を入れたい理由は、将来役に立つことでも作る。

- 続きを1タップ更新できる
- 同じ作品・場所・旅行を後から探せる
- 月の箱へまとまる
- 去年の同じ時期を安全に見返せる
- Exportして持ち出せる
- serviceやAIが変わっても残る

## 2.4 Quiet town response

Memory acknowledgementの後にだけ、小さなTown反応を表示できる。

候補:

- 小さな光が対応建物へ入る
- 窓灯りが一度だけ柔らかく点く
- 港の水面に短い反射が出る
- 四季樹の葉が一度だけ揺れる
- 対応地区の看板が静かに更新される

Rules:

- non-blocking
- skip可能
- reduced motion / motion off対応
- 音なしでも成立
- reward explosion禁止
- item、coin、XP、scoreを出さない
- 毎回大きく成長させない
- Memory confirmationより視覚的に強くしない

## 2.5 Delayed ownership

長期の積み重ねは、後から次として見える。

- 棚の厚み
- 建物stage
- Memory Tree
- 月・年の箱
- Private Postcard
- 地区の小さな生活感

これは保存を強制するmeterではなく、過去を持っている実感として使う。

---

# 3. Town must not become the reason to create meaningless records

Townは、ユーザーが本来残したくない情報を水増しさせてはならない。

禁止:

- 「あと3件で映画館が育ちます」
- 「今日1件追加しましょう」
- 「町を育てるために記録」
- 建物stageまでのprogress bar
- streak
- 1件を複数件へ分割する誘導
- 同一内容の連続保存で成長を稼ぐこと
- AI生成の架空記録で成長すること
- 空の記録や意味のない文字列で成長すること
- bulk Importを派手な大量報酬として見せること

許可:

- 実際に見た作品を保存したくなる
- 行った店を後から探すために残したくなる
- 旅行の断片を忘れないために入れたくなる
- 漫画やアニメの続きを簡単に更新したくなる
- 小さな日常も後で見返せると分かる

```txt
Town may make a real memory feel worth preserving.
Town must not make filler data feel worth producing.
```

---

# 4. Growth eligibility without importance scoring

Town成長へ使うのは「価値」ではなく、validで重複していない保存の粗いaggregate。

Eligibilityに使用可能:

- schema valid
- user confirmed
- duplicateでない
- deleted / hidden / sealed / restrictedでない
- source provenanceが必要水準を満たす
- system test dataやAI generated fillerではない

使用禁止:

- 重要度
- 感情の強さ
- 幸福度
- 人間関係の深さ
- 金額
- 写真の人物数
- 文章量
- AIが判断する「良い思い出」

Town UIでは、次stageまでの正確な必要件数を表示しない。

Bulk Importでは、記憶は正しく全件保存してよいが、Town反応は一つの穏やかなsummaryへ圧縮できる。

例:

```txt
映画棚に過去の記録が加わりました
町にも静かに反映されています
```

---

# 5. No orphan Town feature rule

すべてのTown機能は、Memory OS上の価値へ説明可能でなければならない。

各Town機能は最低一つに紐づく。

```txt
Capture
Organize
Retrieve
Update
Reflect
Understand
Own / Export
```

判定例:

| Town feature | Memory value |
|---|---|
| 建物 | 棚への入口と蓄積の可視化 |
| Memory Tree | 全体蓄積の粗い長期表現 |
| Private Postcard | 過去の町・保存時期の私的振り返り |
| District Identity | 棚の種類を空間的に理解しやすくする |
| Quiet Surprise | 既存の保存状態を穏やかに再発見する |
| Draft Town | 長期配置を本番破壊なしで試す |
| One-tap Beautify | 編集負荷を減らす |
| Memory Window | 明示選択した記憶の振り返り補助 |

次だけを目的にする機能は不採用。

- Town滞在時間を伸ばすだけ
- 広告表示回数を増やすだけ
- daily activeを強制するだけ
- decoration販売だけ
- social comparisonだけ

---

# 6. Capture screen hierarchy

保存体験の表示順を固定する。

```txt
1. Memory Preview / Confirmation
2. Shelf placement / progress update
3. Optional quiet Town response
4. Next useful action
```

Next useful actionの例:

- 棚を見る
- 進行を更新する
- メモを1行追加する
- 関連する記録を見る
- 閉じる

Townを見ることをmandatory next actionにしない。

---

# 7. Home and navigation principle

Townを視覚的に大きく見せることは可能だが、workflow gateにしない。

Home候補:

```txt
Quick Add
最近の棚 / 続き
今月の箱
小さなTown viewport
Search
```

Rules:

- Quick AddをTownの奥へ隠さない
- Searchを建物tapだけに依存させない
- Shelfへ直接到達できる
- TownをOFF / static / list modeにしてもCapture能力は同じ
- Town tabを採用するかはprototypeで検証する
- TownがHome heroの場合も、主要CTAは記憶追加・検索・続き更新

---

# 8. Memory-first test for every new proposal

新機能は以下へ回答する。

1. 何を保存・整理・検索・更新・振り返りやすくするか
2. Townを完全に非表示にしても、そのMemory機能は価値があるか
3. 保存までの操作を増やさないか
4. 無意味な記録の水増しを誘導しないか
5. 不在や少ない記録を罰しないか
6. ユーザーがTownを無視しても成立するか
7. Memory DomainとTown stateを混ぜないか
8. private dataをTown visualへ漏らさないか
9. Export / deletion時に分離して扱えるか
10. 実装優先度がCapture / Search / Portabilityを追い越していないか

一つでも重大な不合格があれば、Town機能として採用済みでも実装を延期または再設計する。

---

# 9. Prototype acceptance gates

## MF-1 Capture remains primary

- 保存完了画面で記憶内容が最初に理解できる
- Town animationなしでも満足できる
- Town animationがMemory confirmationを隠さない

## MF-2 No quantity pressure

- next stage件数を表示しない
- progress barを表示しない
- daily promptを表示しない
- 0件・少件数でも失敗感がない

## MF-3 Useful future value

- 保存後に棚から見つけられる
- 進行更新できる
- source / dateが確認できる
- Export対象になる

## MF-4 Optional side effect

- motion offで保存体験が欠けない
- Town OFFでも同じMemory機能が使える
- Town reactionをskipできる

## MF-5 Spam resistance

- duplicateは成長寄与しない
- invalid fillerは成長寄与しない
- bulk Importで報酬爆発しない
- importance scoringは使わない

---

# 10. Stop conditions

次の場合、Town設計を止めてMemory-firstへ戻る。

- 町のために何を保存させるか考え始める
- 保存内容よりunlock演出が主役になる
- capture flowへTown設定を追加する
- next stageまでの件数を見せる
- Town DAUをMemory utilityより優先する
- editor milestoneがSearch / Exportを追い越す
- userが町を維持する作業を持つ
- Town限定の記録形式を作る

---

# Decision

```txt
Memory Town is not the destination of capture.
It is the long-term visual residue of capture.

ユーザーは町を育てるために人生を記録しない。
人生を忘れたくないから記録し、
その積み重ねが後から町として見える。
```
