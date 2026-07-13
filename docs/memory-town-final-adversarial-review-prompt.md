# Memory Town Final Adversarial Review Prompt

以下を一つのpromptとして外部reviewerへ渡す。

```txt
Repository:
https://github.com/m-shogo/memories-project.git

Branch:
so

Task:
Memory Townの設計を、実装せずに最終adversarial reviewしてください。

重要:
- コード実装を開始しない
- 文書量を品質の証明とみなさない
- 「良さそう」で終わらせない
- 矛盾、欠落、二重正本、migration事故、privacy leakを具体的に探す
- 問題がなければ、確認した証拠と残る不確実性を書く
- 修正が必要なら、対象file、問題、再現scenario、修正案、priorityを示す

最初に読む正本:
1. docs/memory-town-architecture-hardening-contract.md
2. docs/current-product-direction.md
3. docs/memory-town-long-term-spatial-model.md
4. docs/memory-town-webgl-architecture.md
5. docs/memory-town-concrete-data-contract.md
6. docs/memory-town-growth-envelope-and-access-contract.md
7. docs/memory-town-persistence-rls-and-recovery-contract.md
8. docs/memory-town-fixture-validation-harness-plan.md
9. docs/memory-town-prototype-metric-matrix.md
10. docs/memory-town-design-readiness-gate.md
11. docs/memory-town-design-audit-and-risk-register.md

Schema / fixture:
- docs/schemas/memory-town/schema-registry.v1.json
- docs/schemas/memory-town/*.schema.json
- docs/fixtures/memory-town/fixture-index.v1.json
- docs/fixtures/memory-town/*.json

前提:
- Memory TownはMemory OSの感情的menu
- 棚、検索、Import、Exportが実用本体
- fixed-view 2.5D
- PixiJS / WebGL
- React / DOM UI
- MVPは固定layout
-内部はlogical grid
-将来は装飾、道路、植栽、建物移動を段階解放可能
- Minecraft型1block建築ではない
- どうぶつの森のような愛着を参考にするが、UI・art・game economyは複製しない
- 実装はまだNo-Go

必須review観点:

A. Sources of truth
- Memory Domain / Feature Progress / Layout / Environment / Renderが本当に分離されているか
-同じ意味を複数fixture / tableが正本として持っていないか
- reservedGrowthCellsとGrowth Envelopeが矛盾していないか
- routeやfeature meaningがvisual instanceへ再結合していないか

B. Stable identity / versioning
- stable IDが表示名やassetへ依存していないか
- deterministic ID vectorsが曖昧でないか
- versionを上げる条件が抜けていないか
- in-place mutationで既存layoutが変わる余地がないか

C. Spatial correctness
- coordinate axes / orientation / pivot / rotationが一意か
- footprint、entrance、clearance、access path、visual overflowが混ざっていないか
- parcel / terrain / layer coexistenceに抜けがないか
- path maskが導出になっているか
- central squareやportなど特殊objectが一般validatorで破綻しないか

D. Growth
- non-shrinking growthがprivacy erasureと両立するか
- candidateStage / maxUnlockedStage / resetEpochにraceがないか
- stage追加でuser objectを退避させない契約になっているか
- overlay slotがstage変更で失われないか

E. Migration
- old template + user layout + new templateのthree-way mergeが十分か
- deletion / rename / split / merge / parcel変更に未対応でないか
- stored fallbackがデータ墓場にならないか
- rollback snapshotのretention / ownership / deletionが抜けていないか

F. Commands / concurrency
- batch idempotencyとrequest hash
- stale revision
- multi-device conflict
- partial failure
- undo / redo
- resetとの競合
- migration実行中のedit

G. Persistence / RLS
-全user tableにuser_id
- composite ownership FK
- table owner問題
- support / worker role
- missing context fail closed
- cross-user ID oracle
- account deletion
- backup / snapshot leakage

H. Privacy
- scene / audit / exportへprivate contentが入る余地
- arbitrary extension bag
- object custom labelの将来リスク
- GPS / weather誤認
- asset URL / screenshot leakage

I. JSON Schema / fixtures
- schema IDが全てregistryにあるか
- fixtureの$schemaが解決できるか
- closed schemaになっているか
- oneOf / if-then / notが意図通りか
- null policy違反
- positive fixtureがschema上invalidでないか
- negative mutationの期待codeが実際のvalidation順と一致するか
- issue code registryに不足codeがないか
- canonical vectorが再現可能か

J. Assets
- texture key / fallback / provenance / license / hash
- stage family footprint compatibility
- anchor / hit polygon
- visual overflow
- missing asset behavior
- atlas / memory budget

K. Accessibility
- WebGL-only操作にならないか
- DOM alternative
- keyboard / switch / screen reader
- reduced motion
- high contrast
- text zoom
- static fallback

L. Product scope
- editorがMemory OS本体を食わないか
- Townが記録量競争にならないか
-放置で荒れる表現が混ざらないか
-課金で成長加速する余地がないか
- generic residentsが人格・故人simulationへ寄らないか

M. Prototype gates
- tile metric
- map寸法
- 6 mobile viewport
- Stage 0〜2
- performance
- battery / heat
- context loss
- user comprehension
- non-shrinking visual mismatch

最低限検討するfailure scenario:
1. 映画100件でStage 2後、全件削除
2. Feature resetと別端末layout保存が同時
3. Template v2で新建物がuser benchと衝突
4. Object definition廃止
5. Growth Envelope縮小
6. Primary binding先objectがstored
7. Asset missing / CDN failure
8. WebGL context loss
9. Account deletion中にsnapshot worker実行
10. Export packageを別versionへre-import
11.同じbatch IDでpayloadが違う
12. Support roleがopaque IDを総当たり
13. Path削除で港が孤立
14. Stage追加でposter slot消滅
15. Theme変更でhit areaが変化
16. RLS contextなしworker
17. fixture schemaのoneOfが両方match /両方fail
18. map expansionで既存parcel ID再利用
19. stored objectが大量化
20. Town data破損時のMemory OS起動

Output format:

# Verdict
ready / ready_with_known_risks / not_ready

# P0 Findings
各項目:
- ID
- file / section
- failure scenario
- why it matters
- exact correction
- required test / fixture

# P1 Findings
同形式

# Contract Contradictions
二重正本・矛盾を列挙

# Missing Fixtures / Tests
具体file名候補まで

# Prototype-only Decisions
文書で確定してはいけない値

# False Confidence Risks
設計書が揃っていても証明できていないこと

# Final Gate Recommendation
実装開始前に必須な順序

最後に、見つからなかった場合も「完璧」と書かず、未検証領域を明示してください。
```
