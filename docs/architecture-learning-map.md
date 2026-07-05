# Architecture Learning Map

## 目的

このドキュメントは、Memory OS の設計に入れた業界標準の考え方を、学習用に整理した地図である。

単なる用語集ではなく、**なぜMemory OSに必要なのか**を軸に説明する。

## 全体像

Memory OS は、ただのAIアプリではない。

扱うもの:

- 人生文脈
- 原文
- 出典
- 第三者情報
- 未成年情報
- 故人情報
- 会社情報
- AI解釈
- Export
- Backup
- 削除

そのため、以下の業界知識を組み合わせている。

```txt
RFC
DDD
Clean / Hexagonal Architecture
Event-driven Design
AuthN / AuthZ
Storage Architecture
Observability
Incident Response
Local-first / Open Format
Policy / Guardrails
```

## 1. RFC

### 何か

仕様変更を議論・記録する設計文化。

インターネット技術、OSS、大規模プロダクトで使われる。

### Memory OSでの役割

便利そうな機能を思いつきで入れない。

必ず見る:

- 憲章違反しないか
- third-party risk
- minor/family risk
- deceased simulation risk
- company data risk
- cost risk
- deletion/export impact

### 学ぶポイント

RFCは「何を作るか」より「なぜそう決めたか」を残す。

## 2. Domain-driven Design

### 何か

業務や思想の本質に合わせて、言葉と境界を決める設計。

### Memory OSでの役割

RawRecord / Memory / Interpretation / Evidence / SourceRef を混ぜない。

### 学ぶポイント

雑に `Memo` で全部扱うと、AIが作った解釈と事実が混ざる。

DDDはそれを防ぐ。

## 3. Clean / Hexagonal Architecture

### 何か

中心にドメインルールを置き、DB・UI・外部API・LLMを外側に置く設計。

### Memory OSでの役割

OpenAIを変えても、DBを変えても、Policyのルールが変わらないようにする。

### 学ぶポイント

PolicyEvaluator はDB/LLM/UIに依存しない pure domain service にする。

## 4. Event-driven Design

### 何か

重要な出来事を event として扱い、別処理を連動させる設計。

### Memory OSでの役割

Delete時に Search / Vector / Export / Backup / Audit を安全に連動させる。

### 学ぶポイント

完全なEvent SourcingはMVPでは不要。

まずは raw-free Domain Events + Outbox Pattern で十分。

## 5. AuthN / AuthZ

### 何か

AuthN: あなたは誰か。

AuthZ: あなたはそれをしてよいか。

### Memory OSでの役割

owner / admin / ai_worker / system_worker を分ける。

Adminはownerではない。

### 学ぶポイント

OwnerでもPolicy denyは越えられない。

例: ownerが自分のExportを要求しても、third-party raw exportはdeny。

## 6. Storage Architecture

### 何か

DB、Object Storage、Search Index、Vector Index、Audit Log、Backupを分ける設計。

### Memory OSでの役割

rawは危険、metadataはdurable、vectorはderived。

### 学ぶポイント

全部DBに入れるのは簡単だが、削除・検索・Export・安全性で破綻しやすい。

## 7. Observability

### 何か

ログ・メトリクス・トレースでシステム状態を見る仕組み。

### Memory OSでの役割

ユーザー内容を見ずに、Policy deny、Export redaction、Deletion lag、LLM blockを観測する。

### 学ぶポイント

Observabilityにraw textを入れると、ログが第二の漏洩源になる。

## 8. Incident Response

### 何か

事故が起きた時の対応手順。

### Memory OSでの役割

秘密漏洩、誤Export、削除復活、LLM送信事故を想定する。

### 学ぶポイント

最初に原因調査ではなく、まず止血。

```txt
stop exposure -> preserve safe evidence -> notify if needed -> regression test
```

## 9. Local-first / Open Format

### 何か

クラウドに依存しすぎず、ユーザーがデータを手元に持てる思想。

### Memory OSでの役割

サービス終了しても、JSONL / Markdown / SQLite snapshot で人生文脈を残せる。

### 学ぶポイント

Exportは単発。Backupは継続。Emergency Exitはサービス終了時の出口。

## 10. Policy / Guardrails

### 何か

AIにやらせることより、やらせないことを先に固定する設計。

### Memory OSでの役割

- 人生ランキング禁止
- 故人再現禁止
- 家族/恋人診断禁止
- 他人の秘密の記憶化禁止
- 会社検索禁止
- パスワード管理禁止

### 学ぶポイント

GuardrailsはUX・Policy・Test・Schema・Architecture全部に入れる。

## Memory OSでの対応表

| 業界概念 | Memory OSでの具体物 |
|---|---|
| RFC | `docs/rfcs/0001〜0008` |
| DDD | `RawRecord`, `Memory`, `Evidence`, `Interpretation` の分離 |
| Clean Architecture | PolicyEvaluator / UseCase / Port / Infrastructure |
| Event-driven | MemoryDeleted, ExportExpired, PolicyDenied |
| AuthZ | owner/admin/ai_worker/resource/action |
| Storage | relational/object/search/vector/audit/backup |
| Observability | raw-free logs, safety metrics |
| Incident Response | leak/delete/export/LLM事故playbook |
| Local-first | JSONL/Markdown/SQLite/emergency exit |
| Guardrails | forbidden fields/copy/policy tests |

## 学ぶ順番

おすすめ順:

1. RFC
2. DDD
3. Clean Architecture
4. Policy / Guardrails
5. Storage Architecture
6. Deletion / Tombstone
7. AuthZ
8. Event-driven Design
9. Observability
10. Incident Response
11. Local-first / Open Format

## Memory OSで一番大事な理解

```txt
AIアプリを作るのではなく、人生文脈を失わないための情報インフラを作っている。
```

だから、普通のAIアプリより設計が重い。

でもこの重さが、長く使われるサービスになる条件である。

## 結論

Memory OS に入れた設計ルールは、全部「かっこいい設計用語」ではない。

それぞれが、実際の事故や長期運用の失敗から生まれた業界の知恵である。

それをMemory OSの思想に合わせて変換している。
