# MemoryDiorama Research Implications for Memory Town — Round 6

最終更新: 2026-07-14

## Source

```txt
MemoryDiorama: Generating Dynamic 3D Diorama from Everyday Photos for Memory Recall
Keiichi Ihara, Tianle Li, Yasuhisa Shiino, Ryo Suzuki
arXiv:2604.06773v1
submitted: 2026-04-08
```

本稿は現時点でarXiv preprintとして扱う。本文にはplaceholderのconference metadataが残っているため、査読済み完成版として断定しない。

---

# 1. Research question

写真だけを見る場合と比べて、写真を基に作った静的3Dジオラマ、さらに動き・光・粒子・人・地形を加えた動的ジオラマは、自伝的記憶の想起を豊かにするかを検証した研究。

中心概念:

```txt
augmented memory cues
```

撮影済みの個人メディアを土台にしつつ、AIで周辺文脈を拡張し、想起cueの種類を増やす。

---

# 2. System

入力:

- 一つの出来事・一つの場所に対応する写真5枚
- EXIF位置情報
- 写真中の人・物・環境

生成する5layer:

1. geographical
2. object
3. human
4. lighting
5. particle

Pipeline:

```txt
photo analysis
→ element generation
→ placement / route generation
→ mixed-reality dynamic diorama
```

利用技術として本文はGemini、SAM 3 / SAM 3D、生成画像model、Cesium、Google Photorealistic 3D Tiles、OpenCV、Unityを挙げている。

技術評価では、25 photo setsに対し平均end-to-end処理時間は15.70分。成功率はphoto analysis 100%、element generation 92.58%、placement / route generation 75.25%。誤配置、向き違い、複数objectの融合などが報告されている。

---

# 3. Formative study

本実験前に8人へ、1イベントあたり5〜10枚の写真を見ながら周辺状況を詳しく想起してもらった。

そこから5つのcue patternを抽出した。

- object-related
- human-related
- geographical
- lighting-related
- particle-related

想起は静的な物体名だけではなく、次を含んでいた。

- 配置や距離などの空間情報
- 動きや時間変化
- 音、温度、触覚などの非視覚情報

海、川、雪、日差し、雲、風、鳥などが、別の感覚や出来事を思い出す入口になっていた。

---

# 4. Main user study

Participants:

- 18人
- 9 male / 9 female
- 21〜36歳
- 平均26.17歳
- local university community
- 1 session約40分

Design:

```txt
within-subject
```

全員が以下3条件を体験した。

1. Photo-Only
2. Static Diorama
3. MemoryDiorama

MR自体の新奇性を揃えるため、全条件をQuest 3上で実施した。

各participantは異なる3イベントを各条件へ割り当てた。イベントは写真5枚で、低significance・低remembered評価のものを除外し、memory age差を小さくするよう選択した。条件順はcounterbalanceされた。

Recall procedure:

- 写真collectionから出来事を自由想起
- 最初は追加promptなし
- その後general probe
- 音声を記録・transcribe
- detail単位へ分解

Detail categories:

- internal: 特定イベントのepisodic re-experiencing
- external: semantic情報、反復、別イベント、脱線
- in-cue: 提示されたcue自体についての説明

Codingのinter-rater reliabilityは3categoryすべてICC 0.90超。

Subjective measures:

- visual details
- location clarity
- time clarity
- positive emotion
- negative emotion
- doubt about accuracy
- NASA-TLX workload
- enjoyment

---

# 5. Main results

## Internal details

```txt
Photo-Only      M = 29.61
Static Diorama  M = 31.44
MemoryDiorama   M = 38.28
```

MemoryDioramaはPhoto-OnlyとStatic Dioramaの両方より有意に多かった。

## In-cue details

```txt
Photo-Only      M = 2.67
Static Diorama  M = 4.11
MemoryDiorama   M = 7.39
```

MemoryDioramaは両baselineより有意に多かった。

## Perceptual internal details

```txt
Photo-Only      M = 4.11
Static Diorama  M = 4.33
MemoryDiorama   M = 7.22
```

動く海、粒子、日差しなどが、寒さ、風、熱さといった感覚的想起へ結びついた例が報告された。

## Subjective visual detail

```txt
Photo-Only      M = 5.17 / 7
Static Diorama  M = 5.22 / 7
MemoryDiorama   M = 6.06 / 7
```

## Enjoyment

```txt
Photo-Only      M = 4.89 / 7
Static Diorama  M = 5.61 / 7
MemoryDiorama   M = 6.33 / 7
```

## Workload

NASA-TLXには有意差がなかった。

重要な非結果:

```txt
internal details / total details ratio
```

には有意差がなかった。

したがって、研究は「記憶の正確さやepisodic specificityだけが選択的に高まった」とは示していない。提示情報が増えたことで、全体として話すdetailが増えた可能性も残る。

---

# 6. Major risks and limitations

## False memory

AIが写真外の人、動き、地形、光、粒子を推測生成するため、実際には存在しなかった内容をもっともらしいcueとして提示する危険がある。

研究はmemory accuracyやfalse-memory formationを測定していない。

## Event confound

同一participant内比較だが、各条件には異なる自伝的eventを使った。そのため、条件効果とevent固有の思い出しやすさを完全には分離できない。

## Layer contribution unknown

人、光、海、粒子などをまとめたfull system比較であり、どのlayerがどの程度効いたかは分からない。

## MR generalizability

全条件をQuest 3で揃えているが、日常的なスマホの振り返りとは利用姿勢が違う。

## Small and narrow sample

18人、21〜36歳、大学community中心。長期利用、高齢者、悲しい記憶、敏感な写真、文化差は未検証。

## Technical reliability

生成と配置は完全ではなく、processingも現状約16分。productionで自動適用できる成熟度ではない。

---

# 7. What Memory Town should adopt

## Adopt the cue-layer insight

愛着ある景色や動きは、単なる装飾ではなく、記憶を思い出す入口になり得る。

Memory Townで使える安全なcue:

- 保存済みの日付
- user-confirmed season / trip
- 実在するsource type
- user-selected photo
- 実際に保存されたlocation category
- 町の海、川、光、風などのgeneric ambient cue

## Adopt slow, multi-layer scenery

研究で感覚的想起と結びついたのは、動く海、粒子、日差しなどだった。

Memory Townでも次を重視する。

- water motion
- lighting
- sky
- wind-consistent vegetation
- subtle season particles

ただし、これらは出来事を再現したとは主張しない。

## Adopt glanceable diorama structure

ジオラマは複数cueを一つの空間へまとめ、全体の空気を一目で感じさせる。

Memory Townの固定視点2.5Dと、bounded panによる複数角度ではない複数area観察は、この利点と相性がよい。

## Adopt explicit grounding

生成cueを使う場合、必ず元sourceへ戻れるようにする。

```txt
source photo / record
→ derived cue
→ user-visible provenance
```

---

# 8. What Memory Town must not copy directly

- 写真の外側を事実として自動生成
- 人物の動きや会話を本人の記憶として提示
- EXIFなしで推定した場所を確定情報として保存
- AI生成sceneをMemory Domainの正本にする
- false-memory riskの説明なしに自動再表示
- 本人・家族・故人のsimulation
- sensitive photoのdefault processing

Memory Townは、MemoryDioramaの「cue diversity」の利点は参考にするが、「生成された再現」を記憶そのものへ昇格させない。

---

# 9. Safe product interpretation

最初に採用するのは個別事件の3D再現ではない。

```txt
record-grounded generic atmosphere
```

例:

- 旅行箱を開くと港の水面が静かに光る
- 春の箱を見ると四季樹の桜cueが少し強くなる
- 海辺の写真を明示選択した時だけ、generic wave ambienceを添える

禁止:

```txt
この日にこの人がここを歩いた
この時こう話していた
写真外にはこの建物があった
```

のような未確認事実の生成。

---

# 10. Memory Window Gate

On-demand Memory Windowを将来実装する場合:

- userがsourceを明示選択
- default OFF
- generated / inferredを明示
- person animationなし
- original sourceへ戻れる
- prompt / output / asset削除可能
- local / private processing preference
- exact scene reconstructionと主張しない
- user correction可能
- false-memory warning
- sensitive source exclusion

---

# Verdict

```txt
research relevance:
high

evidence strength:
promising but preliminary

safe adoption:
ambient cue diversity + grounded diorama structure

unsafe direct adoption:
automatic personal-event reconstruction

Memory Window:
adopted future feature, strict gate required

implementation:
NO-GO
```
