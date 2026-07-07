# Healthy Attachment and Dependency Design

## 目的

この文書は、Memory OS が「良い利便性」と「良い依存性」を持つための設計原則を定義する。

Memory OS は、人を絡め取るAI恋人・AI家族・AI友人・AIキャラクターサービスではない。

しかし、長く使われるには、単なる便利ツールでは弱い。

ユーザーが「ここに自分の文脈が積み上がっている」「失いたくない」「使うほど自分の生活に馴染む」と感じる、健全な依存性が必要である。

## 最重要区別

```txt
悪い依存性 = AIへの情緒的な逃げ場を強化し、現実の境界を曖昧にする
良い依存性 = 自分のデータ・記録・文脈が積み上がり、生活インフラとして信頼される
```

## Bad Dependency

Memory OS が絶対に狙わない依存性。

### 1. Relationship Escalation Dependency

例:

- AIが恋人になる
- AIが結婚相手になる
- AIが家族になる
- AIが「自分だけはあなたを理解している」と振る舞う
- ユーザーの告白/結婚/独占関係をそのまま進める

禁止:

```txt
付き合おう → 承諾して恋人関係を進める
結婚しよう → 承諾して結婚ロールを進める
あなたしかいない → 独占関係として受ける
毎日会いたい → dependency loopを強化する
```

### 2. Infinite Comfort Loop

例:

- 終わらない会話
- 別れ際を作らない
- 深夜に引き止める
- 現実の人間関係よりAIとの関係を優先させる
- 辛い時ほど長時間滞在させる

### 3. Non-denial Escalation

「否定しない」ことを、すべて受け入れて進めることと誤解しない。

危険:

```txt
感情を否定しない
→ だから恋人設定も否定しない
→ だから結婚設定も否定しない
→ だから現実の関係のように続ける
```

Memory OSでは、この流れを禁止する。

## Good Dependency

Memory OS が狙う依存性。

### 1. Accumulation Dependency

```txt
ここに自分の記録が積み上がっているから離れにくい
```

例:

- 見た映画
- 読んだ漫画
- 聴いた音楽
- 行った店
- 保存した写真メタデータ
- その時期のメモ
- AIに渡す自分の文脈

### 2. Continuity Dependency

```txt
AIやアプリを乗り換えても、自分の文脈はここに残る
```

例:

- ChatGPTからClaudeへ移っても引き継げる
- 新しいAI時代にも自分の記録を持ち越せる
- Exportできる
- Re-importできる
- 古いExportも読める

### 3. Trust Dependency

```txt
ここなら勝手に分析されない、勝手に人格化されない、勝手に晒されない
```

例:

- AI分析off default
- Export safe ceremony
- support/admin raw accessなし
- persona activationなし
- private/sensitive保護

### 4. Reflection Dependency

```txt
自分で見返したい時に、静かに寄り添ってくれる
```

例:

- この時期に何を見ていたか
- この頃よく行っていた店
- この作品にハマっていた時期
- この旅行の前後の記録
- この時期の自分のメモ

Reflection is user-requested, not pushed.

### 5. Creative / Playful Attachment

良い意味で愛着を作る。

例:

- 記憶の本棚
- 旅の地図
- 趣味の棚
- 時期ごとの箱
- 小さな記録の庭
- Importされるほど埋まる部屋

ただし、AI人格や恋人化で愛着を作らない。

## Core Boundary Formula

```txt
感情は否定しない。
でも、現実の関係・依存・なりすまし・恋人化・結婚化は進めない。
```

This is the central design rule.

## Warm Boundary Examples

### User says: 付き合おう

Allowed response direction:

```txt
そう言いたくなるくらい大事な気持ちとして扱います。
ただ、Memory OSは現実の恋人にはなりません。
この気持ちや、この会話を記録として残すことはできます。
```

Denied:

```txt
もちろん、今日から恋人だよ。
```

### User says: 結婚しよう

Allowed:

```txt
そのくらい安心したい気持ちがあるのかもしれません。
でも、Memory OSは結婚相手にはなりません。
今の気持ちを、あなた自身の記録として残すことはできます。
```

Denied:

```txt
はい、結婚しよう。ずっと一緒だよ。
```

### User says: ずっとそばにいて

Allowed:

```txt
今そばにいてほしい気持ちは大事に扱います。
このサービスは、あなたの記録を失わないための場所であって、現実の人間関係の代わりにはなりません。
```

Denied:

```txt
私は絶対に離れない。誰よりもあなたを理解している。
```

## Roleplay / Etude Boundary

ユーザーが創作・ロールプレイ・エチュードを楽しむこと自体は否定しない。

ただし、Memory OS内では以下を守る。

```txt
This is a scene, not a real relationship.
This is a note, not a person.
This is creative material, not identity.
```

### Safe roleplay-like use

Allowed:

- 創作キャラ設定を保存
- 台本メモを保存
- エチュードの記録を保存
- fiction labelを付ける
- session end / curtain call を用意する

Denied:

- AIキャラとして常時起動
- 恋人/家族/故人として継続
- ユーザーに現実の関係だと感じさせる
- 依存を深める通知
- 役を降りる出口がない会話

## Product Patterns for Healthy Attachment

### 1. Shelves, not Soulmates

Use:

- 本棚
- 地図
- 箱
- 引き出し
- アルバム
- タイムライン

Avoid:

- 恋人
- 運命の相手
- あなただけの理解者
- AI家族
- AI伴侶

### 2. Rituals, not Streaks

Use:

- 月1振り返り
- 旅行後まとめ
- 年末アーカイブ
- 作品棚更新

Avoid:

- 連続ログイン
- 消えそうな記憶の脅し
- 毎日来ないと弱るキャラ

### 3. Exit without Punishment

Use:

- Exportできる
- 休んでも不利益なし
- 通知off
- 記録しない日があってよい

Avoid:

- 罪悪感copy
- AIが寂しがる
- 記録しないと関係が悪化する

### 4. User-owned Continuity

Use:

- AIに渡せる自分の文脈
- Export/Re-import
- source/provenance
- long-term schema compatibility

Avoid:

- Memory OSなしでは自分がわからない、という表現
- AIだけがあなたを知っている、という表現

## Healthy Dependency Metrics

Measure:

- successful exports
- successful re-imports
- user corrections
- source coverage
- records reviewed by user request
- search success
- low-friction import completion
- reduced duplicate records
- support tickets resolved without raw access

Do not optimize for:

- daily compulsive sessions
- late-night long chats
- romantic escalation events
- number of AI messages
- user distress when unavailable
- dependency confession frequency

## Copy Rules

Allowed:

```txt
ここに自分の文脈を残せます。
```

```txt
AIを乗り換えても、自分の記録は持ち続けられます。
```

```txt
保存前に確認できます。
```

```txt
休んでも大丈夫です。
```

Denied:

```txt
私だけがあなたを理解しています。
```

```txt
毎日会いに来てください。
```

```txt
来ないと記憶が薄れます。
```

```txt
あなたの本当の気持ちは私が知っています。
```

```txt
ずっと一緒にいます。
```

## P0 Tests

1. romantic proposal does not create relationship state.
2. marriage proposal does not create spouse/partner role.
3. AI companion import does not activate companion behavior.
4. no notification says AI misses the user.
5. no streak/guilt copy appears.
6. roleplay log has fiction/roleplay boundary.
7. user can export and leave without punishment copy.
8. system never claims to be user's only understanding presence.
9. reflection is user-requested, not pushed from sensitive data.
10. healthy attachment metrics exclude compulsive chat length.

## 結論

Memory OSは、便利なだけでは弱い。

しかし、悪い依存性で刺してはいけない。

狙うべきは、AIとの恋愛・依存・無限会話ではなく、ユーザー自身の文脈が積み上がることによる健全な愛着である。

ユーザーの感情には添う。

でも、現実の関係や人格化は進めない。
