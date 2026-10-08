# Found / Memory OS — 競合・需要・統合仮説（2026-10-08）

> 調査メモ。公開情報に基づく机上調査であり、実機比較・ユーザーインタビュー・支払実験は未実施。競合の実装状態、価格、API/規約は継続検証する。製品仕様の確定や実装着手を許可する文書ではない。

## 1. 今回の結論と前回仮説の修正

- **保存→自動タグ→見やすいカード→意味検索**は競争上の基本機能（table stakes）。Foundの独自性として売らない。
- **iPhone対応そのものも独自性ではない**。mymind、Raindrop、KarakeepにiOS/Androidアプリがある。Stashrのnative Save captureは強いが、2026-10-08時点でモバイルアプリ/Share Extensionはない。
- **Saved→Did→Likedは魅力的だが、独自性・需要・継続率は未証明**。Google Maps等の訪問履歴や分野別トラッカーは一部を既に解く。差別化候補は「媒体をまたいだ保存根拠」と「本人が確認した実行・評価」を同じentityに紐付け、後の意思決定で有用にする点。
- **Found単独 / Memoriesと一体のどちらも未決**。共有するのはevidence/provenance/entity/検索・プライバシー基盤。UI統合は行動データで判断する。
- **Buildより先にbenchmark**。Karakeep/Raindrop/mymindを実際に試し、既存サービス＋薄いoutcome layerで十分ならフルBookmark Managerを作らない。

## 2. 主要4社の比較

| 軸 | mymind | Stashr | Raindrop.io | Karakeep |
|---|---|---|---|---|
| 主な強み | visual card / intelligent bookmark / Smart Spaces | デスクトップでSNS標準Save操作をミラー＋bulk import | 成熟したbookmark管理、無料枠、検索、連携 | OSS / self-host / AI tags / archive / API |
| 保存 | Web/ブラウザ拡張、iOS/Android share | Chrome系extension、対応SNSの通常Save、右クリックWeb clip、既存Save import | Web、Safari含む拡張、iOS/Android、Share | Web、iOS/Android、Chrome/Firefox/Safari拡張 |
| Native Save同期 | 確認できず | 対応デスクトップWebであり。X/Reddit/Instagram/TikTok、GitHub Star | 対応するSNS内Saveの自動同期は確認できず | 基本は明示Save。外部連携・community syncは別物 |
| 自動整理/検索 | AI画像タグ、OCR、Smart Spaces、自然語検索 | AI tags（Pro）、意味検索（textはHobby、image/videoはPro）、platform/date/author filter | collection/tag、AI suggestions、Stella意味検索/対話 | AI tagging/summaries、full-text、experimental semantic/hybrid（0.33系） |
| サムネ/カード | 非常に強い。article/product/book/recipeを描き分け | Mosaic、元画像・動画cover・notes | カバー画像、複数表示形式 | カード/リスト、元画像、SNS埋込 |
| API/MCP | Entities APIは**開発中・仕様不安定**。公開安定APIの機能範囲は別途確認 | REST API、CLI、MCP（Pro） | 公開API、MCP | REST API、CLI、MCP（0.33で29 tools） |
| Export | Chrome/Edge desktopのみ。images/PDFとcards.csv。**再import非対応**（公式Help 2026-07-16） | Export可能と説明。ただし解約後は閲覧/API停止、事前export推奨 | Import/Export、Proでbackup | Export/backup、self-hostならデータ主権 |
| 動画保存 | プラン別動画アップロードあり | 動画**本体は保存せず**coverと元URLのみ | YouTube transcriptの検索・Stella対話 | 動画/SNS埋込、crawler・archive機能あり。全動画の永久保存は保証しない |
| 価格（公開ページ） | Guest無料100 cards、Bookmarker $4.99/月、Student $7.99/月、Mastermind $12.99/月 | 14日trial。Hobby $6/月（年払換算$4.50）、Pro $10/月（年払換算$7.50） | Freeはbookmarks/collections/devices無制限。Pro有料、公式価格表示が動的なため決済画面で再確認 | Cloud Free 10件/20MB、Pro $4/月または$40/年、self-host無料（運用費別） |
| 注意点 | import不可、exportブラウザ制限、Entities API未確定 | デスクトップ依存、サイト変更でcapture破損、YouTubeはcoming soon、動画本体なし | 2026-07/08に検索index不整合の利用者報告・開発者修正回答 | semantic/hybridはexperimental、運用負担、AI/スクレイプ費用、SSRF等セキュリティ保守 |

### 重要な更新
- Karakeep 0.32（2026-05）でSafari拡張、0.33.1（2026-08-01）でsemantic/hybrid search・offline mobile・MCP拡充、0.33.2（2026-08-11）で修正。**「モバイル対応が競合の穴」と一般化しない**。
- Raindrop Stella（2026-02-05）とYouTube transcript対応（2026-06-15）は、「AIで保存物に質問」「動画内検索」も既存機能にした。
- mymind Entity APIはBook/Product/Recipe/Restaurant/Place/TikTokPost/YouTubeVideo等を型として列挙するが**Work in progress**。稼働中のentity resolutionと同一視しない。
- Stashrは対応サイトの標準Saveを監視するが**iOSアプリ内のSaveをリアルタイムで吸い上げるわけではない**。スマホ保存分はPCから再importする。
- Stashrの「削除後も保存」は主にtext/image/cover。動画再生は元投稿に依存する。
- **終了リスクは実在**：SaveDayは2026-05-31終了とAppSumoが告知。全件exportと移行容易性は信頼機能。

## 3. ユーザーの声・需要・WTP

### 観測
- Raindropは無制限無料枠があり、mymind/Stashr/Karakeepには有料プランが存在。これは供給と価格帯の証拠であり、Foundへの**支払意思を直接証明しない**。
- Karakeep開発者は2026-01の投稿で、2025年末時点のmobile約7,500 MAU、Chrome extension約29,000 WAUを自己申告。サービス需要の方向性は示すが、有料転換率は不明。
- Raindropの2026-07/08 Redditでは「sidebar件数と検索結果の不一致」の報告があり、開発者がindex同期問題を認めた。**見つけられることへの信頼**は差別化候補。ただし単発不具合を恒常的欠陥と断定しない。
- Karakeepの2026-01 RedditではAIタグの表記ゆれやSmart List条件の扱いに不満が見られる。AI分類だけでなく**分類の一貫性・説明可能性・修正負荷**が重要。
- Redditの声は選択バイアスが大きく、市場規模や継続率の代用にしない。

### WTP仮説（未検証）
- 月額の一般保存アプリはFree/低価格強者と競合するため、高額課金の根拠が弱い。
- 有料化候補は「複数媒体から失わず取り込む」「必要時に確実に発見」「個人の行動・評価に基づく選択支援」。単なるAIタグは課金理由にしない。
- **価格を先に決めず**、競合を実際に使った人の移行意思と、実際の支払/予約/デポジットで検証する。

## 4. 未解決の穴（可能性であり、独占領域ではない）

1. **既存Saveのモバイル横断取得**：iOS Share Extensionはユーザーが共有したものしか受け取れない。他社アプリ内の保存一覧を無断・汎用的に読めない。公式API/エクスポートがある媒体のみimportを検討。無理なスクレイプ前提にしない。
2. **日本の混合ジャンル**：食べログ、楽天/ヨドバシ等、Qiita/Zenn、国内レシピとSNSを、同じUIで高品質に見せられるか。単に日本語UIでは不十分。
3. **Source Item ↔ Entityの正確な関係**：SNS動画と商品/店/作品を誤って同一化しない。1動画が複数商品を紹介することもある。
4. **「保存理由」の復元**：user_noteとsource_captionとAI_summaryは分離。保存だけで「欲しい」「買うつもり」と断定しない。
5. **確証のあるoutcome**：購入・訪問・調理・視聴を、明示入力や同意された情報から検証可能な形で記録し、過去の保存と結びつける。推定を事実に昇格しない。
6. **データ可搬性・復旧**：元URL、source id、raw metadata、ユーザーメモ、タグ、関連entity、outcome、添付を可能な限りexportできる。検索index障害でもraw savesは見える。

## 5. Memoriesとの統合候補

```text
Capture / Import
    ↓
SourceSave（元URL・媒体・保存時刻・original metadata・user note）
    ↓
EntityCandidate（店・商品・映画・レシピ等、0..N）
    ↓
Confirmed Entity（重複統合はreversible）
    ├─ prospective state: saved / considering / want_to_visit...
    └─ experience/outcome: bought / visited / cooked / watched / liked...
           ↓
Personal Preference / Decision Memory（evidence + confidence + time）
```

- **共有基盤**：provenance、identity/entity、検索、権限、export/deletion、audit trail。
- **UIは当面分離可能**：Foundは「後で使う」、Memoriesは「経験した」。共通Entityの詳細画面で横断表示を試す。
- **学習の原則**：保存数・閲覧数は嗜好の確証ではない。明示の評価と観測事実を優先。誤推定は訂正・削除可能。
- **プライバシー**：位置・購買・写真・メール等からのoutcome推定は別途同意・最小権限・透明性を要する。最初から常時監視しない。
- **反証条件**：利用者が実行後の記録をほぼ残さず、リマインダーも望まないならSaved→Did→Likedは中心価値にならない。保存検索単体に戻すか、既存サービス上の小さな補助にする。

## 6. Build / Buy / Integrate判断

| 領域 | 推奨 |
|---|---|
| URL保存、タグ、一般検索、Reader、アーカイブ、MCP | **既存製品を先に評価**。フル再実装しない |
| Share Sheet / 主要媒体のcapture品質 | 必須だが差別化ではない。アプリ別の可否・規約・信頼性を実機検証 |
| entity graphと保存→実行→評価の接続 | **薄い試作で価値を検証**。独自性は未証明 |
| 画像/動画全件永久保存 | MVP対象外。著作権・容量・規約・リンク切れを評価 |
| MemoriesとFoundの一体化UI | **保留**。基盤共通、UIはABプロトタイプで判断 |
| モデル/embedding/AIタグ基盤 | 既製API/OSS活用、検索・修正・信頼性のUXへ投資 |

**二案比較**：
- A: Karakeep/Raindropの既存libraryにimport/APIで薄い「Did/Liked」レイヤーを追加する。
- B: 最小限のiOS Share + source-aware card + search + outcomeを自前で試作する。

Aが十分ならBの大規模開発はしない。AのAPI/ライセンス/データ制限は先に確認する。

## 7. 検証計画（実施前、目標値は仮置き）

### Sprint 0 — 競合の実機基準（2〜3日）
- 同じ30〜50件のサンプル（TikTok、YouTube、Instagram、食べログ、Qiita、Zenn、楽天、記事、商品）を、mymind/Raindrop/Karakeepに投入。Stashrはデスクトップ対応分だけ。
- 成功/失敗を記録：Share成功、保存完了までのタップ数、thumbnail/title、元URL、source filter、カテゴリ、備考、検索、export、削除。
- 「保存できた」の定義はraw URLとtimestampのdurable ack。リッチ抽出失敗を別計測。
- 検索課題20問を作成し、Success@3とtime-to-findを同一データで比較。

### Sprint 1 — 需要インタビュー（10〜15人、7日）
- 過去1週間にどの媒体で何件保存したか、3件を後から実際に探してもらう。
- 誘導せず「現在の回避策」「困った具体例」「過去に使ってやめたサービス」「月額に払ったこと」を聞く。
- **保存しっぱなしで困っていない層**も含め、無理に需要ありと判定しない。

### Sprint 2 — プロトタイプ（2週間）
- A: 既存bookmark基盤 + outcome記録。B: 最小Share library。どちらも手動分類なし。
- 目標例：保存確認成功率≥98%、Search Success@3≥85%、既存競合よりtime-to-find≥30%短縮、誤entity merge<1%、明示的にoutcomeを付ける人≥30%。**検証前の仮置き閾値であり実績ではない**。
- 通知や毎日の整理を要求しない。Did/Likedは1〜2タップ、後日任意。
- 2〜4週後に「実際の購入/訪問/視聴/調理が検索結果を改善したか」を確認。

### Go / Pivot / Stop
- **Go**：既存比で定量的に検索・再利用改善、継続使用、支払/乗換の行動証拠が出る。
- **Pivot**：検索だけでは既存同等だがoutcomeが役立つ→Memory OSの小さなintegrationへ。
- **Stop**：既存製品で困らず、outcomeの記録負荷が価値を上回る→Found独立製品は作らない。

## 8. 一次資料と反証資料（確認日2026-10-08）

- mymind pricing: https://access.mymind.com/pricing
- mymind guest 100 cards: https://mymind.helpscoutdocs.com/article/72-free-plan
- mymind export制限（2026-07-16更新）: https://mymind.helpscoutdocs.com/article/18-can-i-export
- mymind Entities API（WIP）: https://access.mymind.com/api/entities
- mymind mobile: https://mymind.com/%CB%97%CB%8F%CB%8B-the-brand-new-android-app-%CB%8E%CB%97
- Stashr homepage / price / platform: https://stashr.me/
- Stashr docs/import: https://stashr.me/docs/importing-your-saves
- Stashr media preservation: https://stashr.me/docs/what-gets-saved
- Stashr troubleshooting: https://stashr.me/docs/troubleshooting
- Stashr privacy: https://stashr.me/privacy
- Raindrop pricing: https://raindrop.io/pro/buy
- Raindrop Stella（2026-02-05）: https://blog.raindrop.io/meet-stella-your-ai-powered-second-brain-b34482fb003f/
- Raindrop YouTube（2026-06-15）: https://blog.raindrop.io/
- Karakeep pricing: https://karakeep.app/pricing/
- Karakeep apps: https://karakeep.app/apps/
- Karakeep releases（0.32〜0.33.2）: https://github.com/karakeep-app/karakeep/releases
- Karakeep privacy: https://karakeep.app/privacy/
- Apple app-extension制約: https://developer.apple.com/library/archive/documentation/General/Conceptual/ExtensibilityPG/ExtensionScenarios.html
- Recall隣接競合: https://www.recall.it/about
- Fabric隣接競合: https://fabric.so/features/quick-capture
- SaveDay終了告知（2026-04-30、終了2026-05-31）: https://appsumo.com/products/saveday/
- Raindrop検索不具合と開発者回答（2026-08）: https://www.reddit.com/r/raindropio/comments/1vf3vy6/search_inconsistencies_and_errors/
- Karakeep AIタグ不満（2026-01）: https://www.reddit.com/r/selfhosted/comments/1qe2uvl/karakeep_ai_auto_tagging_problems/

## 9. 次回更新時の重点

1. 競合4社の最新changelog、価格/制限、API、mobile、native Save、exportの変化を**前回との差分だけ**追う。
2. 新しい証拠がなければ結論を水増ししない。実機・インタビュー未実施の事実を維持する。
3. StashrのYouTube/mobile進展、Karakeep semantic安定化、mymind Entity API正式化、Raindropの検索品質をwatch。
4. 机上調査の次の実行は**実機ベンチマークと顧客調査**。競合サイトを読むだけではWTPやPMFを確定できない。
